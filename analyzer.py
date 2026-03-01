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
        "audience_breakdown": (
            df["audience"].value_counts().to_dict()
            if "audience" in df.columns
            else {}
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


def digital_physical_split(df: pd.DataFrame) -> dict:
    """Summarize digital vs physical items."""
    if "is_digital" not in df.columns:
        return {"has_data": False}

    total = len(df)
    digital = int(df["is_digital"].sum())
    physical = total - digital

    result = {
        "has_data": True,
        "digital_count": digital,
        "digital_pct": round(digital / total * 100, 1) if total else 0,
        "physical_count": physical,
        "physical_pct": round(physical / total * 100, 1) if total else 0,
    }

    # Avg checkouts per group
    if df["checkouts"].notna().any():
        dig_df = df[df["is_digital"]]
        phy_df = df[~df["is_digital"]]
        result["digital_avg_circ"] = round(float(dig_df["checkouts"].mean()), 1) if len(dig_df) else 0
        result["physical_avg_circ"] = round(float(phy_df["checkouts"].mean()), 1) if len(phy_df) else 0

    return result


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

    # Exclude digital items — they can't be physically weeded
    if "is_digital" in df.columns:
        df = df[~df["is_digital"]].copy()

    candidates = df[
        (df["pub_year"].notna())
        & (df["pub_year"] <= current_year - age_threshold)
        & (df["checkouts"].fillna(0) <= circ_threshold)
    ].copy()
    candidates["age"] = current_year - candidates["pub_year"]
    candidates["cost_per_circ"] = candidates.apply(
        lambda r: round(r["price"] / r["checkouts"], 2)
        if pd.notna(r["price"]) and r["price"] > 0 and pd.notna(r["checkouts"]) and r["checkouts"] > 0
        else None,
        axis=1,
    )
    return candidates.sort_values(
        ["checkouts", "age"], ascending=[True, False]
    )[["title", "author", "call_number", "pub_year", "age", "checkouts", "format", "price", "cost_per_circ"]]


def dormant_items(df: pd.DataFrame, dormant_years: int = 3) -> dict:
    """Identify items that once circulated but have gone dormant.

    An item is dormant if it has checkouts > 0 but its last checkout date
    is more than dormant_years ago.  Also reports items with no last_checkout
    date at all (unknown dormancy).
    """
    result = {"has_data": False, "dormant_years": dormant_years}

    if "last_checkout" not in df.columns or df["last_checkout"].isna().all():
        return result

    result["has_data"] = True
    now = pd.Timestamp.now()
    cutoff = now - pd.DateOffset(years=dormant_years)

    has_circ = df[df["checkouts"].fillna(0) > 0].copy()

    dormant = has_circ[
        has_circ["last_checkout"].notna()
        & (has_circ["last_checkout"] < cutoff)
    ].copy()
    dormant["years_dormant"] = (
        (now - dormant["last_checkout"]).dt.days / 365.25
    ).round(1)

    result["total_dormant"] = len(dormant)
    result["total_with_circ"] = len(has_circ)

    # Dormant items table (sorted by longest dormant first)
    cols = ["title", "author", "call_number", "checkouts",
            "last_checkout", "years_dormant", "format"]
    cols = [c for c in cols if c in dormant.columns]
    sorted_dormant = dormant.sort_values("years_dormant", ascending=False)
    items_df = sorted_dormant[cols].head(200).copy()
    # Format the date for display
    if "last_checkout" in items_df.columns:
        items_df["last_checkout"] = (
            items_df["last_checkout"].dt.strftime("%Y-%m-%d")
        )
    result["item_list"] = items_df.fillna("").to_dict("records")

    # Breakdown by dormancy period
    bins = []
    for years in [1, 2, 3, 5, 10]:
        cut = now - pd.DateOffset(years=years)
        count = int(has_circ[
            has_circ["last_checkout"].notna()
            & (has_circ["last_checkout"] < cut)
        ].shape[0])
        bins.append({"years": years, "count": count})
    result["bins"] = bins

    return result


def find_duplicates(df: pd.DataFrame) -> dict:
    """Detect duplicate items by ISBN and by title+author.

    Returns two lists:
    - isbn_dupes: groups of items sharing the same ISBN
    - title_author_dupes: groups sharing normalized title+author
    """
    result = {"isbn_groups": [], "title_author_groups": [],
              "total_isbn_dupes": 0, "total_ta_dupes": 0}

    # --- ISBN duplicates ---
    if "isbn" in df.columns and df["isbn"].notna().any():
        isbn_df = df[df["isbn"].notna()].copy()
        isbn_df["isbn_norm"] = isbn_df["isbn"].astype(str).str.strip().str.replace("-", "", regex=False)
        isbn_df = isbn_df[isbn_df["isbn_norm"].str.len() > 0]

        isbn_counts = isbn_df.groupby("isbn_norm").size()
        dupe_isbns = isbn_counts[isbn_counts > 1].index

        groups = []
        for isbn in dupe_isbns:
            items = isbn_df[isbn_df["isbn_norm"] == isbn]
            cols = ["title", "author", "call_number", "isbn", "pub_year",
                    "checkouts", "format", "location"]
            cols = [c for c in cols if c in items.columns]
            groups.append({
                "isbn": isbn,
                "count": len(items),
                "copies": items[cols].fillna("").to_dict("records"),
            })
        result["isbn_groups"] = sorted(groups, key=lambda g: g["count"], reverse=True)
        result["total_isbn_dupes"] = sum(g["count"] for g in groups)

    # --- Title+Author duplicates ---
    if df["title"].notna().any() and df["author"].notna().any():
        ta_df = df[df["title"].notna() & df["author"].notna()].copy()
        ta_df["_t"] = ta_df["title"].str.lower().str.strip()
        ta_df["_a"] = ta_df["author"].str.lower().str.strip()
        ta_df["_key"] = ta_df["_t"] + "|||" + ta_df["_a"]

        ta_counts = ta_df.groupby("_key").size()
        dupe_keys = ta_counts[ta_counts > 1].index

        groups = []
        for key in dupe_keys:
            items = ta_df[ta_df["_key"] == key]
            cols = ["title", "author", "call_number", "isbn", "pub_year",
                    "checkouts", "format", "location"]
            cols = [c for c in cols if c in items.columns]
            groups.append({
                "title": items.iloc[0]["title"],
                "author": items.iloc[0]["author"],
                "count": len(items),
                "copies": items[cols].fillna("").to_dict("records"),
            })
        result["title_author_groups"] = sorted(
            groups, key=lambda g: g["count"], reverse=True
        )
        result["total_ta_dupes"] = sum(g["count"] for g in groups)

    return result


def cost_analysis(df: pd.DataFrame) -> dict:
    """Analyze collection investment and ROI by subject area."""
    result = {"has_data": False}

    if "price" not in df.columns or df["price"].isna().all():
        return result

    priced = df[df["price"].notna() & (df["price"] > 0)].copy()
    if len(priced) == 0:
        return result

    result["has_data"] = True
    result["total_investment"] = round(float(priced["price"].sum()), 2)
    result["avg_price"] = round(float(priced["price"].mean()), 2)
    result["median_price"] = round(float(priced["price"].median()), 2)
    result["items_with_price"] = len(priced)
    result["items_total"] = len(df)

    # By subject area
    if priced["lc_class"].notna().any():
        priced["broad_class"] = priced["lc_class"].str[0]
        by_subject = (
            priced.groupby("broad_class")
            .agg(
                count=("title", "size"),
                total_cost=("price", "sum"),
                avg_cost=("price", "mean"),
                total_checkouts=("checkouts", "sum"),
            )
            .reset_index()
        )
        by_subject["total_cost"] = by_subject["total_cost"].round(2)
        by_subject["avg_cost"] = by_subject["avg_cost"].round(2)
        by_subject["total_checkouts"] = by_subject["total_checkouts"].fillna(0)
        # Cost per checkout (ROI proxy) — lower is better
        by_subject["cost_per_checkout"] = by_subject.apply(
            lambda r: round(r["total_cost"] / r["total_checkouts"], 2)
            if r["total_checkouts"] > 0 else None,
            axis=1,
        )
        by_subject["label"] = by_subject["broad_class"].map(
            lambda x: LC_CLASS_LABELS.get(x, "Unknown")
        )
        result["by_subject"] = by_subject.sort_values(
            "total_cost", ascending=False
        ).to_dict("records")

    # By format
    if priced["format"].notna().any():
        by_format = (
            priced.groupby("format")
            .agg(
                count=("title", "size"),
                total_cost=("price", "sum"),
                avg_cost=("price", "mean"),
                total_checkouts=("checkouts", "sum"),
            )
            .reset_index()
        )
        by_format["total_cost"] = by_format["total_cost"].round(2)
        by_format["avg_cost"] = by_format["avg_cost"].round(2)
        by_format["total_checkouts"] = by_format["total_checkouts"].fillna(0)
        by_format["cost_per_checkout"] = by_format.apply(
            lambda r: round(r["total_cost"] / r["total_checkouts"], 2)
            if r["total_checkouts"] > 0 else None,
            axis=1,
        )
        result["by_format"] = by_format.sort_values(
            "total_cost", ascending=False
        ).to_dict("records")

    return result


def collection_freshness(df: pd.DataFrame) -> list[dict]:
    """Freshness matrix: for each subject, what % is from the last 5, 10, and 10+ years."""
    current_year = datetime.now().year

    if df["lc_class"].isna().all() or df["pub_year"].isna().all():
        return []

    valid = df[df["lc_class"].notna() & df["pub_year"].notna()].copy()
    valid["broad_class"] = valid["lc_class"].str[0]
    valid["age"] = current_year - valid["pub_year"]

    rows = []
    for cls, group in valid.groupby("broad_class"):
        total = len(group)
        fresh = int((group["age"] <= 5).sum())
        mid = int(((group["age"] > 5) & (group["age"] <= 10)).sum())
        aging = int(((group["age"] > 10) & (group["age"] <= 20)).sum())
        old = int((group["age"] > 20).sum())

        rows.append({
            "broad_class": cls,
            "label": LC_CLASS_LABELS.get(cls, "Unknown"),
            "total": total,
            "fresh_count": fresh,
            "fresh_pct": round(fresh / total * 100, 1) if total else 0,
            "mid_count": mid,
            "mid_pct": round(mid / total * 100, 1) if total else 0,
            "aging_count": aging,
            "aging_pct": round(aging / total * 100, 1) if total else 0,
            "old_count": old,
            "old_pct": round(old / total * 100, 1) if total else 0,
            "median_age": round(float(group["age"].median()), 1),
        })

    return sorted(rows, key=lambda r: r["fresh_pct"])
