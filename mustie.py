"""MUSTIE / CREW weeding criteria engine.

Implements the MUSTIE framework used by the CREW method (Continuous Review,
Evaluation, and Weeding):

  M - Misleading: factually inaccurate or obsolete information
  U - Ugly: worn, damaged, or unattractive (can't detect from data alone,
      but we approximate by flagging high-circ + old items likely to be worn)
  S - Superseded: a newer edition or replacement may exist (flagged when
      multiple items share the same title/author with different pub years)
  T - Trivial: of no discernible literary or scientific merit (can't detect
      from data; users can flag manually)
  I - Irrelevant: doesn't match community needs (approximated by zero or
      very low circulation)
  E - Elsewhere: available from other sources (can't detect from data;
      users can flag manually)

The CREW method also recommends different age thresholds by subject area.
This module provides those defaults and lets users customize them.
"""

from datetime import datetime

import pandas as pd

from importer import LC_CLASS_LABELS


# CREW-recommended age thresholds by LC broad class.
# These are general public library guidelines — users can override per subject.
DEFAULT_CREW_THRESHOLDS: dict[str, dict] = {
    "A": {"label": "General Works",              "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "B": {"label": "Philosophy & Psychology",     "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "C": {"label": "Auxiliary Sciences of History","max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "D": {"label": "World History",               "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "E": {"label": "American History",            "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "F": {"label": "Local American History",      "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "G": {"label": "Geography & Recreation",      "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "H": {"label": "Social Sciences",            "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "J": {"label": "Political Science",           "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "K": {"label": "Law",                         "max_age": 5,  "max_no_circ_years": 2, "circ_floor": 2},
    "L": {"label": "Education",                   "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "M": {"label": "Music",                       "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "N": {"label": "Fine Arts",                   "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "P": {"label": "Language & Literature",        "max_age": 20, "max_no_circ_years": 3, "circ_floor": 1},
    "Q": {"label": "Science",                     "max_age": 5,  "max_no_circ_years": 2, "circ_floor": 2},
    "R": {"label": "Medicine",                    "max_age": 5,  "max_no_circ_years": 2, "circ_floor": 2},
    "S": {"label": "Agriculture",                 "max_age": 10, "max_no_circ_years": 3, "circ_floor": 2},
    "T": {"label": "Technology",                  "max_age": 5,  "max_no_circ_years": 2, "circ_floor": 2},
    "U": {"label": "Military Science",            "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "V": {"label": "Naval Science",               "max_age": 15, "max_no_circ_years": 5, "circ_floor": 1},
    "Z": {"label": "Bibliography & Library Science","max_age": 5, "max_no_circ_years": 2, "circ_floor": 2},
}

# Subjects where outdated information is especially dangerous/misleading
FAST_CHANGING_SUBJECTS = {"K", "Q", "R", "T", "Z"}


def get_default_thresholds() -> dict[str, dict]:
    """Return a copy of the default CREW thresholds."""
    import copy
    return copy.deepcopy(DEFAULT_CREW_THRESHOLDS)


def apply_mustie(df: pd.DataFrame,
                 thresholds: dict[str, dict] | None = None,
                 circ_floor: int = 2) -> pd.DataFrame:
    """Evaluate every item against MUSTIE criteria.

    Args:
        df: The catalog DataFrame (must have lc_class, pub_year, checkouts, etc.)
        thresholds: Per-subject age/circ thresholds (defaults to CREW guidelines)
        circ_floor: Global minimum checkout count below which an item is
                    considered low-circulation. Defaults to 2.

    Returns:
        A DataFrame of flagged items with MUSTIE columns added.
    """
    if thresholds is None:
        thresholds = DEFAULT_CREW_THRESHOLDS

    current_year = datetime.now().year
    result = df.copy()

    # Compute derived columns
    result["age"] = current_year - result["pub_year"]
    result["broad_class"] = result["lc_class"].str[0] if result["lc_class"].notna().any() else pd.NA
    result["circ"] = result["checkouts"].fillna(0)

    # Look up per-subject threshold for each row
    result["subject_max_age"] = result["broad_class"].map(
        lambda c: thresholds.get(c, {}).get("max_age", 15) if pd.notna(c) else 15
    )

    # --- M: Misleading ---
    # Flagged when item is in a fast-changing subject AND exceeds that subject's
    # recommended age threshold.
    result["flag_m"] = (
        result["broad_class"].isin(FAST_CHANGING_SUBJECTS)
        & result["pub_year"].notna()
        & (result["age"] > result["subject_max_age"])
    )

    # --- U: Ugly (worn) ---
    # Approximation: high circulation + old = likely physically worn.
    # We flag items with above-median checkouts that are also old.
    circ_median = result["circ"].median() if result["circ"].notna().any() else 0
    wear_circ_threshold = max(circ_median * 1.5, 5)
    result["flag_u"] = (
        result["pub_year"].notna()
        & (result["age"] > 10)
        & (result["circ"] >= wear_circ_threshold)
    )

    # --- S: Superseded ---
    # Flag items where another item with the same title+author exists with a
    # newer publication year (possible newer edition).
    result["flag_s"] = False
    if result["title"].notna().any() and result["author"].notna().any():
        # Normalize for matching
        result["_title_norm"] = result["title"].str.lower().str.strip()
        result["_author_norm"] = result["author"].str.lower().str.strip()

        # For each title+author group, find the max pub year
        grouped_max = (
            result[result["pub_year"].notna()]
            .groupby(["_title_norm", "_author_norm"])["pub_year"]
            .transform("max")
        )
        result.loc[grouped_max.index, "_max_year"] = grouped_max
        result["flag_s"] = (
            result["pub_year"].notna()
            & result["_max_year"].notna()
            & (result["pub_year"] < result["_max_year"])
        )
        result.drop(columns=["_title_norm", "_author_norm", "_max_year"],
                     inplace=True, errors="ignore")

    # --- T: Trivial ---
    # Can't be reliably detected from catalog data. Left as False;
    # users can manually review.
    result["flag_t"] = False

    # --- I: Irrelevant (no community interest) ---
    # Flagged when an item has very low or zero circulation.
    result["flag_i"] = (result["circ"] <= circ_floor)

    # --- E: Elsewhere ---
    # Can't be detected from catalog data. Left as False; users can
    # manually review.
    result["flag_e"] = False

    # Count how many MUSTIE flags each item has
    flag_cols = ["flag_m", "flag_u", "flag_s", "flag_t", "flag_i", "flag_e"]
    result["mustie_count"] = result[flag_cols].sum(axis=1)

    # Build a human-readable MUSTIE string (e.g. "M-I" or "M-S-I")
    def _mustie_str(row):
        parts = []
        for col, letter in zip(flag_cols, "MUSTIE"):
            if row[col]:
                parts.append(letter)
        return "-".join(parts) if parts else ""

    result["mustie_flags"] = result.apply(_mustie_str, axis=1)

    # Only return items with at least one flag
    flagged = result[result["mustie_count"] > 0].copy()

    # Select output columns
    output_cols = [
        "title", "author", "call_number", "pub_year", "age",
        "checkouts", "format", "broad_class", "subject_max_age",
        "mustie_flags", "mustie_count",
        "flag_m", "flag_u", "flag_s", "flag_t", "flag_i", "flag_e",
    ]
    # Only include columns that exist
    output_cols = [c for c in output_cols if c in flagged.columns]

    return flagged[output_cols].sort_values(
        ["mustie_count", "age"], ascending=[False, False]
    )


def mustie_summary(flagged_df: pd.DataFrame) -> dict:
    """Summarize MUSTIE results for display."""
    total = len(flagged_df)
    if total == 0:
        return {"total": 0, "by_flag": {}, "by_subject": []}

    by_flag = {}
    for col, letter, label in [
        ("flag_m", "M", "Misleading (outdated info)"),
        ("flag_u", "U", "Ugly (likely worn)"),
        ("flag_s", "S", "Superseded (newer edition exists)"),
        ("flag_t", "T", "Trivial"),
        ("flag_i", "I", "Irrelevant (low/no circulation)"),
        ("flag_e", "E", "Elsewhere (available elsewhere)"),
    ]:
        if col in flagged_df.columns:
            count = int(flagged_df[col].sum())
            by_flag[letter] = {"label": label, "count": count}

    # Breakdown by subject
    by_subject = []
    if "broad_class" in flagged_df.columns and flagged_df["broad_class"].notna().any():
        grouped = (
            flagged_df.groupby("broad_class")
            .agg(count=("title", "size"), avg_flags=("mustie_count", "mean"))
            .reset_index()
        )
        grouped["avg_flags"] = grouped["avg_flags"].round(1)
        grouped["label"] = grouped["broad_class"].map(
            lambda x: LC_CLASS_LABELS.get(x, "Unknown")
        )
        by_subject = grouped.sort_values("count", ascending=False).to_dict("records")

    return {
        "total": total,
        "by_flag": by_flag,
        "by_subject": by_subject,
    }
