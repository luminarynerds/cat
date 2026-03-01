# Library Collection Analyzer

A local web application for analyzing your library's catalog data without needing
a direct connection to your ILS (Integrated Library System). Upload a CSV or Excel
export from your catalog system and get actionable insights about collection gaps,
subject balance, aging materials, circulation patterns, and weeding candidates.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## What It Does

Upload a catalog export (CSV or Excel) from your ILS and the analyzer will:

- **Find collection gaps** — underrepresented subject areas, subjects lacking recent
  publications, and aging areas that need updating
- **Subject balance** — visual breakdown of your collection across LC classification
  areas with circulation stats per subject
- **Age distribution** — see how your collection breaks down by publication decade
  and identify areas dominated by outdated materials
- **Format breakdown** — distribution across books, DVDs, audiobooks, etc. with
  usage stats for each format
- **Circulation analysis** — top-circulating items, usage by format, and overall
  circulation patterns
- **Weeding candidates** — items that are old AND rarely circulated, with
  adjustable thresholds for age and checkout count

## Data Import

The tool automatically recognizes common ILS column names including variations from
Sierra, Polaris, Koha, Evergreen, and other systems. It handles:

| Field | Recognized Names |
|-------|-----------------|
| Title | Title, BTitle, Item Title, Bib Title |
| Author | Author, Primary Author, Main Author |
| Call Number | Call Number, Call #, Call No, Local Call Number |
| Pub Year | Pub Year, Publication Year, Year, Date, Pub Date |
| Subject | Subject, Subjects, Primary Subject, Subject Heading |
| Format | Format, Material Type, Item Type, IType |
| Checkouts | Checkouts, Total Checkouts, Total Circs, YTD Circ |
| ... | and many more (see the Import Data page in the app) |

Your file doesn't need all of these columns — the analyzer works with whatever
data is available and adapts its reports accordingly.

## Sample Data

A sample CSV with 500 records is included for testing:

```bash
python3 generate_sample_data.py  # regenerate if desired
```

Upload `sample_data/sample_catalog.csv` through the app to see it in action.

## How It Works

- **No ILS connection needed** — works entirely with exported files
- **Runs locally** — your data stays on your machine
- **Call number classification** — handles both LC and Dewey call numbers,
  mapping them to broad subject areas for gap analysis
- **Flexible import** — normalizes column names from various ILS systems
  automatically

## Requirements

- Python 3.10+
- Flask, pandas, openpyxl (installed via requirements.txt)
