# Import Templates + Last Upload Persistence

## Problem

1. Users don't have a clear reference for how to structure their data before uploading. The upload page lists recognized column names, but there's no downloadable file they can open in Excel to compare against or paste into.

2. Data lives only in a Python variable. Restarting the Flask server loses the imported dataset, even though the raw file is still on disk. Users get no indication that this happened or how to recover.

## Feature 1: Import Templates

### Files

- `sample_data/template_blank.csv` -- header row only, all 16 canonical columns (Title, Author, ISBN, Call Number, Publication Year, Subject, Format, Location, Barcode, Checkouts, Last Checkout Date, Date Added, Status, Price, Collection, Copies)
- `sample_data/template_example.csv` -- same headers + 5 rows of realistic library data across different formats

### Backend

- New route `GET /download-template/<name>` in `app.py`
- Serves files from `sample_data/` via `send_file`
- Allowlist validation: only serves `template_blank.csv` and `template_example.csv`

### UI

- New section on `templates/upload.html` between the help box and the upload form
- Two download buttons: "Download Blank Template" and "Download Example File"
- One line of context explaining what they're for

## Feature 2: Remember Last Upload

### Metadata file

- Path: `uploads/.last_upload.json`
- Written on every successful upload
- Contents: `{"filename": "...", "uploaded_at": "...", "row_count": 123}`
- Gitignored (runtime state, not source)

### Startup behavior

- Helper function `_check_last_upload()` reads the JSON and validates the referenced file still exists on disk
- Does NOT auto-import; only makes metadata available to templates

### Dashboard UI

- When no data is loaded but a previous upload is detected, `templates/index.html` shows a banner: "Your last dataset (filename.csv, N items) is still available. [Reload it]"
- Banner is hidden once data is loaded

### Reload route

- `POST /reload` reads filename from `.last_upload.json`, runs `import_catalog()`, sets `_current_df`/`_current_filename`, redirects to dashboard
- POST method because it mutates server state

### Edge cases

- JSON exists but file deleted: no banner shown
- New upload overwrites JSON
- `uploads/.last_upload.json` added to `.gitignore`

## Files to create/modify

| File | Action |
|------|--------|
| `sample_data/template_blank.csv` | Create |
| `sample_data/template_example.csv` | Create |
| `app.py` | Add `/download-template/<name>` and `POST /reload` routes, add `_check_last_upload()`, write JSON on upload |
| `templates/upload.html` | Add template download section |
| `templates/index.html` | Add reload banner |
| `.gitignore` | Add `uploads/.last_upload.json` |
