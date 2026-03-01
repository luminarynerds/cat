# Library Collection Analyzer

A web application for analyzing library catalog data without needing a direct
connection to your ILS. Upload a CSV or Excel export and get actionable insights
about collection gaps, subject balance, aging materials, circulation patterns,
weeding candidates, and more.

## Quick Start

```bash
pip install -r requirements.txt
python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Features

- **Collection gaps** -- underrepresented subjects, areas lacking recent titles,
  aging sections that need updating
- **Subject balance** -- breakdown across LC or Dewey classification areas with
  circulation stats per subject
- **Age distribution** -- collection by publication decade, areas dominated by
  outdated materials
- **Format breakdown** -- books, DVDs, audiobooks, digital items, etc. with usage
  stats for each format
- **Circulation analysis** -- top-circulating items, usage by format, dormant items
- **Weeding candidates** -- old + rarely circulated items using CREW/MUSTIE criteria
  with adjustable thresholds and per-subject overrides
- **MUSTIE analysis** -- flag items as Misleading, Ugly, Superseded, Trivial,
  Irrelevant, or Elsewhere-available
- **Duplicate detection** -- find duplicate titles and editions in your collection
- **Banned books check** -- flag items appearing on common challenged-books lists
- **Board summary** -- one-page executive summary with recommendations, designed
  for sharing with administrators
- **Flag & pull lists** -- checkbox items for review and download sorted pull lists
- **Audience segmentation** -- separate analysis for juvenile, YA, and adult materials
- **Digital format support** -- identifies and segments electronic resources

## Data Import

The tool recognizes common ILS column names from Sierra, Polaris, Koha, Evergreen,
and other systems. It handles both LC and Dewey call numbers automatically.

Your file doesn't need all columns -- the analyzer adapts its reports based on
whatever data is available.

A sample CSV with 500 records is included at `sample_data/sample_catalog.csv`.

## Running with Docker

```bash
docker build -t cat-app .
docker run -p 5000:5000 cat-app
```

## Standalone Executable (macOS)

```bash
python3 build.py
```

Creates a distributable app in `dist/CollectionAnalyzer/` that runs without
Python installed.

## Requirements

- Python 3.10+
- Flask, pandas, openpyxl (installed via requirements.txt)
