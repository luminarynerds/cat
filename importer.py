"""Import and normalize library catalog data from CSV/Excel exports."""

import pandas as pd

# Common column name variations from ILS exports, mapped to our canonical names.
COLUMN_ALIASES = {
    "title": "title",
    "btitle": "title",
    "item title": "title",
    "bib title": "title",

    "author": "author",
    "primary author": "author",
    "main author": "author",
    "bib author": "author",

    "isbn": "isbn",
    "isbn13": "isbn",
    "isbn-13": "isbn",

    "call number": "call_number",
    "call #": "call_number",
    "call no": "call_number",
    "call_number": "call_number",
    "callnumber": "call_number",
    "local call number": "call_number",
    "lc call number": "call_number",

    "pub year": "pub_year",
    "publication year": "pub_year",
    "pub_year": "pub_year",
    "pubyear": "pub_year",
    "year": "pub_year",
    "date": "pub_year",
    "publication date": "pub_year",
    "pub date": "pub_year",

    "subject": "subject",
    "subjects": "subject",
    "primary subject": "subject",
    "subject heading": "subject",
    "topical subject": "subject",

    "format": "format",
    "material type": "format",
    "mat type": "format",
    "item type": "format",
    "itype": "format",
    "type": "format",

    "location": "location",
    "branch": "location",
    "library": "location",
    "sublocation": "location",

    "barcode": "barcode",
    "item barcode": "barcode",

    "checkouts": "checkouts",
    "total checkouts": "checkouts",
    "total circs": "checkouts",
    "ytd circ": "checkouts",
    "circ count": "checkouts",
    "circs": "checkouts",

    "last checkout": "last_checkout",
    "last checkout date": "last_checkout",
    "last circ date": "last_checkout",
    "last activity": "last_checkout",

    "created date": "date_added",
    "date added": "date_added",
    "creation date": "date_added",
    "cataloged date": "date_added",
    "cat date": "date_added",

    "status": "status",
    "item status": "status",

    "price": "price",
    "cost": "price",
    "replacement cost": "price",
    "list price": "price",

    "collection": "collection",
    "collection code": "collection",
    "ccode": "collection",

    "copies": "copies",
    "copy count": "copies",
    "number of copies": "copies",
}

CANONICAL_COLUMNS = [
    "title",
    "author",
    "isbn",
    "call_number",
    "pub_year",
    "subject",
    "format",
    "location",
    "barcode",
    "checkouts",
    "last_checkout",
    "date_added",
    "status",
    "price",
    "collection",
    "copies",
]


def load_file(filepath: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    lower = filepath.lower()
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return pd.read_excel(filepath, dtype=str)
    return pd.read_csv(filepath, dtype=str)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map whatever column names the ILS export uses to our canonical names."""
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[key]
    df = df.rename(columns=rename_map)

    # Keep only recognized columns, add missing ones as empty
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[CANONICAL_COLUMNS]


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert string-loaded columns to appropriate types."""
    # Publication year: extract 4-digit year
    if "pub_year" in df.columns:
        df["pub_year"] = (
            df["pub_year"]
            .astype(str)
            .str.extract(r"(\d{4})", expand=False)
        )
        df["pub_year"] = pd.to_numeric(df["pub_year"], errors="coerce")

    # Numeric columns
    for col in ["checkouts", "price", "copies"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date columns
    for col in ["last_checkout", "date_added"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")

    return df


def extract_lc_class(call_number: str) -> str | None:
    """Extract the LC classification letter(s) from a call number.

    Works for both LC-style (e.g. 'QA76.73') and basic Dewey
    (returns a mapped broad category).
    """
    if pd.isna(call_number):
        return None
    s = str(call_number).strip()
    if not s:
        return None

    # LC-style: starts with 1-3 uppercase letters
    if s[0].isalpha():
        letters = ""
        for ch in s:
            if ch.isalpha():
                letters += ch.upper()
            else:
                break
        if letters:
            return letters

    # Dewey-style: starts with digits — map first digit to broad LC area
    if s[0].isdigit():
        dewey_to_broad = {
            "0": "Z",   # Computer science, info, general works
            "1": "B",   # Philosophy & psychology
            "2": "BL",  # Religion
            "3": "H",   # Social sciences
            "4": "P",   # Language
            "5": "Q",   # Science
            "6": "T",   # Technology
            "7": "N",   # Arts & recreation
            "8": "P",   # Literature
            "9": "D",   # History & geography
        }
        return dewey_to_broad.get(s[0])

    return None


def extract_classification(call_number: str) -> dict:
    """Extract classification system, LC class, and Dewey fields from a call number.

    Returns a dict with:
        classification_system: "LC", "Dewey", or None
        lc_class: LC letter(s) or None
        dewey_class: 3-digit Dewey string (e.g. "512") or None
        dewey_tens: tens grouping (e.g. "510") or None
    """
    if pd.isna(call_number):
        return {"classification_system": None, "lc_class": None,
                "dewey_class": None, "dewey_tens": None}
    s = str(call_number).strip()
    if not s:
        return {"classification_system": None, "lc_class": None,
                "dewey_class": None, "dewey_tens": None}

    # LC-style: starts with 1-3 uppercase letters followed by digit
    if s[0].isalpha() and len(s) > 1:
        letters = ""
        for ch in s:
            if ch.isalpha():
                letters += ch.upper()
            else:
                break
        if letters and len(s) > len(letters) and s[len(letters)].isdigit():
            return {"classification_system": "LC", "lc_class": letters,
                    "dewey_class": None, "dewey_tens": None}

    # Dewey-style: starts with digits
    if s[0].isdigit():
        digits = ""
        for ch in s:
            if ch.isdigit():
                digits += ch
            elif ch in (".", " "):
                break
            else:
                break
        if len(digits) >= 3:
            dewey_class = digits[:3]
            dewey_tens = digits[:2] + "0"
            dewey_to_broad = {
                "0": "Z", "1": "B", "2": "BL", "3": "H", "4": "P",
                "5": "Q", "6": "T", "7": "N", "8": "P", "9": "D",
            }
            lc_class = dewey_to_broad.get(digits[0])
            return {"classification_system": "Dewey", "lc_class": lc_class,
                    "dewey_class": dewey_class, "dewey_tens": dewey_tens}
        elif len(digits) >= 1:
            dewey_to_broad = {
                "0": "Z", "1": "B", "2": "BL", "3": "H", "4": "P",
                "5": "Q", "6": "T", "7": "N", "8": "P", "9": "D",
            }
            return {"classification_system": "Dewey", "lc_class": dewey_to_broad.get(digits[0]),
                    "dewey_class": None, "dewey_tens": None}

    # Fallback: try original LC extraction
    if s[0].isalpha():
        letters = ""
        for ch in s:
            if ch.isalpha():
                letters += ch.upper()
            else:
                break
        if letters:
            return {"classification_system": "LC", "lc_class": letters,
                    "dewey_class": None, "dewey_tens": None}

    return {"classification_system": None, "lc_class": None,
            "dewey_class": None, "dewey_tens": None}


# Human-readable LC class labels
LC_CLASS_LABELS = {
    "A": "General Works",
    "B": "Philosophy & Psychology",
    "BL": "Religion",
    "C": "Auxiliary Sciences of History",
    "D": "World History",
    "E": "American History",
    "F": "Local American History",
    "G": "Geography & Recreation",
    "H": "Social Sciences",
    "J": "Political Science",
    "K": "Law",
    "L": "Education",
    "M": "Music",
    "N": "Fine Arts",
    "P": "Language & Literature",
    "Q": "Science",
    "R": "Medicine",
    "S": "Agriculture",
    "T": "Technology",
    "U": "Military Science",
    "V": "Naval Science",
    "Z": "Bibliography & Library Science",
}

# Format values that indicate digital/electronic items.
# Matched case-insensitively against the 'format' column.
DIGITAL_FORMATS = {
    "ebook", "e-book", "digital", "online resource",
    "eaudiobook", "e-audiobook", "streaming video", "streaming audio",
    "database", "electronic", "hoopla", "libby", "kanopy",
    "axis 360", "cloudlibrary",
}


def _derive_audience(row) -> str:
    """Derive audience from collection or location fields."""
    for field in ["collection", "location"]:
        val = str(row.get(field, "")).lower()
        if not val or val == "nan":
            continue
        if any(kw in val for kw in ["juvenile", "children", "kids", "j ", "juv"]):
            return "Juvenile"
        if any(kw in val for kw in ["ya", "young adult", "teen"]):
            return "YA"
        if "adult" in val:
            return "Adult"
    return "Unknown"


def import_catalog(filepath: str) -> pd.DataFrame:
    """Full pipeline: load, normalize, type-coerce, and enrich catalog data."""
    df = load_file(filepath)
    df = normalize_columns(df)
    df = coerce_types(df)
    # Extract classification system and all class fields
    classification = df["call_number"].apply(extract_classification)
    class_df = pd.DataFrame(classification.tolist(), index=df.index)
    df["classification_system"] = class_df["classification_system"]
    df["lc_class"] = class_df["lc_class"]
    df["dewey_class"] = class_df["dewey_class"]
    df["dewey_tens"] = class_df["dewey_tens"]
    df["is_digital"] = (
        df["format"]
        .fillna("")
        .str.strip()
        .str.lower()
        .isin(DIGITAL_FORMATS)
    )
    df["audience"] = df.apply(_derive_audience, axis=1)
    return df
