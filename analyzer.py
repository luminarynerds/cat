"""Collection analysis engine for library catalog data."""

from datetime import datetime

import pandas as pd

from importer import LC_CLASS_LABELS


def collection_summary(df: pd.DataFrame) -> dict:
    """High-level summary statistics for the collection."""
    current_year = datetime.now().year
    return {
        "total_items": len(df),
        "unique_titles": df["title"].nunique(),
        "unique_authors": df["author"].nunique(),
        "formats": df["format"].dropna().nunique(),
        "year_range": (
            int(df["pub_year"].min()) if df["pub_year"].notna().any() else None,
            int(df["pub_year"].max()) if df["pub_year"].notna().any() else None,
        ),
        "median_age": (
            int(current_year - df["pub_year"].median())
            if df["pub_year"].notna().any()
            else None
        ),
        "total_checkouts": (
            int(df["checkouts"].sum()) if df["checkouts"].notna().any() else 0
        ),
        "items_never_circulated": (
            int((df["checkouts"].fillna(0) == 0).sum())
            if "checkouts" in df.columns
            else None
        ),
    }


def age_distribution(df: pd.DataFrame) -> list[dict]:
    """Break down collection by publication decade."""
    if df["pub_year"].isna().all():
        return []

    current_year = datetime.now().year
    df_valid = df[df["pub_year"].notna()].copy()
    df_valid["decade"] = (df_valid["pub_year"] // 10 * 10).astype(int)
    grouped = (
        df_valid.groupby("decade")
        .agg(
            count=("title", "size"),
            avg_checkouts=("checkouts", "mean"),
        )
        .reset_index()
    )
    grouped["avg_checkouts"] = grouped["avg_checkouts"].round(1)
    grouped["age_years"] = current_year - grouped["decade"]
    return grouped.sort_values("decade", ascending=False).to_dict("records")


def subject_balance(df: pd.DataFrame) -> list[dict]:
    """Analyze distribution across LC classification areas.

    Returns each class with count, percentage, and average checkouts.
    """
    if df["lc_class"].isna().all():
        return []

    df_valid = df[df["lc_class"].notna()].copy()
    # Use only the first letter for broad class grouping
    df_valid["broad_class"] = df_valid["lc_class"].str[0]
    total = len(df_valid)

    grouped = (
        df_valid.groupby("broad_class")
        .agg(
            count=("title", "size"),
            avg_checkouts=("checkouts", "mean"),
        )
        .reset_index()
    )
    grouped["percentage"] = (grouped["count"] / total * 100).round(1)
    grouped["avg_checkouts"] = grouped["avg_checkouts"].round(1)
    grouped["label"] = grouped["broad_class"].map(
        lambda x: LC_CLASS_LABELS.get(x, "Unknown")
    )
    return grouped.sort_values("count", ascending=False).to_dict("records")


def find_gaps(df: pd.DataFrame) -> dict:
    """Identify potential holes in the collection.

    Returns a dict with different categories of gaps:
    - underrepresented_subjects: LC classes with < 3% of collection
    - aging_areas: subjects where median pub year is very old
    - low_circulation: items with zero or very low checkouts
    - missing_recent: subjects with few items from the last 5 years
    """
    current_year = datetime.now().year
    gaps = {}

    # --- Underrepresented subjects ---
    balance = subject_balance(df)
    if balance:
        gaps["underrepresented_subjects"] = [
            s for s in balance if s["percentage"] < 3.0
        ]

    # --- Aging areas: subjects where median year is 15+ years old ---
    if not df["lc_class"].isna().all() and not df["pub_year"].isna().all():
        df_valid = df[df["lc_class"].notna() & df["pub_year"].notna()].copy()
        df_valid["broad_class"] = df_valid["lc_class"].str[0]
        median_years = (
            df_valid.groupby("broad_class")["pub_year"]
            .median()
            .reset_index()
        )
        median_years["median_age"] = current_year - median_years["pub_year"]
        aging = median_years[median_years["median_age"] > 15].copy()
        aging["label"] = aging["broad_class"].map(
            lambda x: LC_CLASS_LABELS.get(x, "Unknown")
        )
        gaps["aging_areas"] = aging.to_dict("records")

    # --- Low-circulation items ---
    if df["checkouts"].notna().any():
        never_circ = df[df["checkouts"].fillna(0) == 0]
        low_circ_count = len(never_circ)
        pct = round(low_circ_count / len(df) * 100, 1) if len(df) > 0 else 0
        gaps["low_circulation"] = {
            "count": low_circ_count,
            "percentage": pct,
            "sample": never_circ.head(20)[
                ["title", "author", "call_number", "pub_year", "format"]
            ]
            .fillna("")
            .to_dict("records"),
        }

    # --- Missing recent: subjects with fewer than 5 items from last 5 years ---
    if not df["lc_class"].isna().all() and not df["pub_year"].isna().all():
        recent = df[
            (df["pub_year"] >= current_year - 5)
            & df["lc_class"].notna()
        ].copy()
        recent["broad_class"] = recent["lc_class"].str[0]
        recent_counts = recent.groupby("broad_class").size().reset_index(name="count")

        # Compare against all subjects present in the collection
        all_classes = df[df["lc_class"].notna()]["lc_class"].str[0].unique()
        missing = []
        for cls in all_classes:
            match = recent_counts[recent_counts["broad_class"] == cls]
            cnt = int(match["count"].iloc[0]) if len(match) > 0 else 0
            if cnt < 5:
                missing.append({
                    "broad_class": cls,
                    "label": LC_CLASS_LABELS.get(cls, "Unknown"),
                    "recent_count": cnt,
                })
        gaps["missing_recent"] = sorted(missing, key=lambda x: x["recent_count"])

    return gaps


def format_breakdown(df: pd.DataFrame) -> list[dict]:
    """Distribution of items by material format."""
    if df["format"].isna().all():
        return []
    grouped = (
        df.groupby("format")
        .agg(count=("title", "size"), avg_checkouts=("checkouts", "mean"))
        .reset_index()
    )
    total = len(df)
    grouped["percentage"] = (grouped["count"] / total * 100).round(1)
    grouped["avg_checkouts"] = grouped["avg_checkouts"].round(1)
    return grouped.sort_values("count", ascending=False).to_dict("records")


def circulation_analysis(df: pd.DataFrame) -> dict:
    """Circulation patterns and usage analysis."""
    result = {}

    if df["checkouts"].notna().any():
        result["total_checkouts"] = int(df["checkouts"].sum())
        result["avg_checkouts_per_item"] = round(df["checkouts"].mean(), 1)
        result["median_checkouts"] = int(df["checkouts"].median())

        # Top circulating items
        top = df.nlargest(20, "checkouts")[
            ["title", "author", "call_number", "checkouts", "format"]
        ].fillna("")
        result["top_items"] = top.to_dict("records")

        # Circulation by format
        if df["format"].notna().any():
            by_format = (
                df.groupby("format")["checkouts"]
                .agg(["sum", "mean", "median"])
                .reset_index()
            )
            by_format.columns = ["format", "total", "average", "median"]
            by_format["average"] = by_format["average"].round(1)
            result["by_format"] = by_format.sort_values(
                "total", ascending=False
            ).to_dict("records")

    return result


def weeding_candidates(df: pd.DataFrame, age_threshold: int = 15,
                        circ_threshold: int = 2) -> pd.DataFrame:
    """Identify items that may be candidates for weeding/deselection.

    Criteria: older than age_threshold years AND fewer than circ_threshold checkouts.
    """
    current_year = datetime.now().year
    candidates = df[
        (df["pub_year"].notna())
        & (df["pub_year"] <= current_year - age_threshold)
        & (df["checkouts"].fillna(0) <= circ_threshold)
    ].copy()
    candidates["age"] = current_year - candidates["pub_year"]
    return candidates.sort_values(
        ["checkouts", "age"], ascending=[True, False]
    )[["title", "author", "call_number", "pub_year", "age", "checkouts", "format"]]
