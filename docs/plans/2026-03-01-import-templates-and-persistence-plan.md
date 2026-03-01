# Import Templates + Last Upload Persistence — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add downloadable CSV templates to the upload page and remember the last uploaded file so users can reload it after a server restart.

**Architecture:** Two independent features. Feature 1 adds static CSV files and a download route. Feature 2 writes a JSON metadata file on upload and reads it on the dashboard to offer a reload prompt.

**Tech Stack:** Python/Flask, Jinja2 templates, CSV files, JSON for metadata.

---

### Task 1: Create the blank CSV template

**Files:**
- Create: `sample_data/template_blank.csv`

**Step 1: Create the file**

```csv
Title,Author,ISBN,Call Number,Publication Year,Subject,Format,Location,Barcode,Checkouts,Last Checkout Date,Date Added,Status,Price,Collection,Copies
```

One line, just the headers. Use the human-readable names that map to the canonical columns in `importer.py` (these are all recognized by `COLUMN_ALIASES`).

**Step 2: Verify the importer recognizes the headers**

Run from project root:
```bash
source venv/bin/activate && python3 -c "
from importer import import_catalog
df = import_catalog('sample_data/template_blank.csv')
print(f'Columns: {list(df.columns)}')
print(f'Rows: {len(df)}')
"
```
Expected: All 16 canonical columns listed, 0 rows.

**Step 3: Commit**

```bash
git add sample_data/template_blank.csv
git commit -m "feat: add blank CSV template for catalog import"
```

---

### Task 2: Create the example CSV template

**Files:**
- Create: `sample_data/template_example.csv`

**Step 1: Create the file**

```csv
Title,Author,ISBN,Call Number,Publication Year,Subject,Format,Location,Barcode,Checkouts,Last Checkout Date,Date Added,Status,Price,Collection,Copies
The Great Gatsby,"Fitzgerald, F. Scott",9780743273565,PS3511.I9 G7,1925,American Fiction,Book,Main,30112345678901,47,2026-01-15,2010-03-01,Available,15.99,Adult Fiction,2
Coding for Kids,"Martinez, Ana",9781234567890,QA76.73.P98,2022,Computer Science,Book,Children,30112345678902,12,2025-11-20,2022-06-15,Available,24.95,Juvenile Non-Fiction,1
Jazz Standards Collection,Various Artists,,M1630.18,2019,Music,CD,Main,30112345678903,8,2025-08-03,2019-09-10,Available,18.99,Adult Non-Fiction,1
National Geographic World Atlas,,9780792275428,G1021.N38,2015,Geography,DVD,Reference,30112345678904,0,,2015-04-22,Available,29.95,Reference,1
Becoming,"Obama, Michelle",9781524763138,E909.O24,2018,Biography,Audiobook,Main,30112345678905,31,2026-02-10,2019-01-08,Checked Out,39.99,Adult Non-Fiction,3
```

Five rows covering: Book (fiction), Book (children's nonfiction), CD, DVD, Audiobook. Mix of high/low circulation, different subject areas, different locations.

**Step 2: Verify the importer handles it**

```bash
source venv/bin/activate && python3 -c "
from importer import import_catalog
df = import_catalog('sample_data/template_example.csv')
print(f'Rows: {len(df)}')
print(f'Formats: {df[\"format\"].unique().tolist()}')
print(f'LC classes: {df[\"lc_class\"].unique().tolist()}')
"
```
Expected: 5 rows, formats include Book/CD/DVD/Audiobook, LC classes include P/Q/M/G/E.

**Step 3: Commit**

```bash
git add sample_data/template_example.csv
git commit -m "feat: add example CSV template with 5 sample records"
```

---

### Task 3: Add the download-template route

**Files:**
- Modify: `app.py` (add import for `send_file`, add route after the `upload` route around line 88)

**Step 1: Add `send_file` to the Flask imports**

In `app.py:8-10`, change:
```python
from flask import (
    Flask, render_template, request, redirect, url_for, flash, Response,
)
```
to:
```python
from flask import (
    Flask, render_template, request, redirect, url_for, flash, Response,
    send_file,
)
```

**Step 2: Add the route**

After the `upload()` route (after line 88), add:

```python
TEMPLATE_ALLOWLIST = {"template_blank.csv", "template_example.csv"}

@app.route("/download-template/<name>")
def download_template(name):
    if name not in TEMPLATE_ALLOWLIST:
        flash("Template not found.", "error")
        return redirect(url_for("upload"))
    filepath = os.path.join(os.path.dirname(__file__), "sample_data", name)
    return send_file(filepath, as_attachment=True, download_name=name)
```

**Step 3: Verify the route works**

```bash
source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
# Valid template
resp = client.get('/download-template/template_blank.csv')
print(f'Blank status: {resp.status_code}')
print(f'Blank content-disposition: {resp.headers.get(\"Content-Disposition\")}')
# Invalid name (path traversal attempt)
resp = client.get('/download-template/../../etc/passwd')
print(f'Invalid status: {resp.status_code}')
"
```
Expected: Blank returns 200 with attachment header. Invalid returns 302 redirect.

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add download-template route with allowlist"
```

---

### Task 4: Add template download buttons to upload page

**Files:**
- Modify: `templates/upload.html` (insert new section between the help-box div and the upload card, around line 22-23)

**Step 1: Add the template download section**

After the closing `</div>` of the `help-box` (line 22) and before the upload `<div class="card">` (line 24), insert:

```html
<div class="card">
    <h3>Templates</h3>
    <p style="color: var(--gray-600); font-size: 14px; margin-bottom: 12px;">
        Not sure if your file will work? Download a template to see the expected format,
        or compare it against the example file.
    </p>
    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <a href="{{ url_for('download_template', name='template_blank.csv') }}" class="btn-export">Download Blank Template</a>
        <a href="{{ url_for('download_template', name='template_example.csv') }}" class="btn-export">Download Example File</a>
    </div>
</div>
```

**Step 2: Verify in browser**

Open http://127.0.0.1:5000/upload and confirm:
- Templates section appears between the help text and the upload form
- Both download links work and download CSV files

**Step 3: Commit**

```bash
git add templates/upload.html
git commit -m "feat: add template download buttons to upload page"
```

---

### Task 5: Write last-upload metadata on successful upload

**Files:**
- Modify: `app.py` (add JSON write inside the `upload()` route's success path, around line 78-86)
- Modify: `.gitignore` (add uploads/.last_upload.json)

**Step 1: Add the `_save_last_upload` helper**

After the `get_df()` function (around line 42), add:

```python
LAST_UPLOAD_PATH = os.path.join(UPLOAD_DIR, ".last_upload.json")


def _save_last_upload(filename: str, row_count: int) -> None:
    """Record the last successful upload for reload-on-restart."""
    from datetime import datetime
    meta = {
        "filename": filename,
        "uploaded_at": datetime.now().isoformat(),
        "row_count": row_count,
    }
    with open(LAST_UPLOAD_PATH, "w") as f:
        json.dump(meta, f)
```

**Step 2: Call it from the upload route**

In the `upload()` route, after `_current_filename = file.filename` (line 79) and before the `flash()` call (line 80), add:

```python
            _save_last_upload(file.filename, len(_current_df))
```

**Step 3: Add to .gitignore**

Append to `.gitignore`:
```
uploads/.last_upload.json
```

**Step 4: Verify by uploading the sample data**

Open http://127.0.0.1:5000/upload, upload `sample_data/sample_catalog.csv`, then check:

```bash
cat /Users/sam/Projects/cat/uploads/.last_upload.json
```
Expected: JSON with filename, uploaded_at timestamp, and row_count of 500.

**Step 5: Commit**

```bash
git add app.py .gitignore
git commit -m "feat: save last-upload metadata to JSON on successful import"
```

---

### Task 6: Add the reload banner and route

**Files:**
- Modify: `app.py` (add `_check_last_upload()` helper and `POST /reload` route)
- Modify: `templates/index.html` (add reload banner in the empty-state block)

**Step 1: Add the `_check_last_upload` helper**

After `_save_last_upload` in `app.py`, add:

```python
def _check_last_upload() -> dict | None:
    """Check if a previous upload is available for reloading."""
    if not os.path.exists(LAST_UPLOAD_PATH):
        return None
    try:
        with open(LAST_UPLOAD_PATH) as f:
            meta = json.load(f)
        filepath = os.path.join(UPLOAD_DIR, meta["filename"])
        if not os.path.exists(filepath):
            return None
        return meta
    except (json.JSONDecodeError, KeyError):
        return None
```

**Step 2: Pass last-upload info to the dashboard template**

In the `index()` route, change:

```python
    return render_template(
        "index.html",
        summary=summary,
        filename=_current_filename,
    )
```

to:

```python
    last_upload = _check_last_upload() if df is None else None
    return render_template(
        "index.html",
        summary=summary,
        filename=_current_filename,
        last_upload=last_upload,
    )
```

**Step 3: Add the reload route**

After the `index()` route, add:

```python
@app.route("/reload", methods=["POST"])
def reload_last():
    global _current_df, _current_filename
    meta = _check_last_upload()
    if meta is None:
        flash("No previous upload found.", "error")
        return redirect(url_for("upload"))
    filepath = os.path.join(UPLOAD_DIR, meta["filename"])
    try:
        _current_df = import_catalog(filepath)
        _current_filename = meta["filename"]
        flash(
            f"Reloaded {len(_current_df)} items from {meta['filename']}.",
            "success",
        )
    except Exception as e:
        flash(f"Error reloading file: {e}", "error")
    return redirect(url_for("index"))
```

**Step 4: Add the reload banner to index.html**

In `templates/index.html`, replace the `{% else %}` empty-state block (lines 83-95):

```html
{% else %}

{% if last_upload %}
<div class="help-box" style="border-left: 4px solid var(--accent);">
    <strong>Welcome back!</strong> Your last dataset
    (<strong>{{ last_upload.filename }}</strong>, {{ "{:,}".format(last_upload.row_count) }} items)
    is still available.
    <form method="POST" action="{{ url_for('reload_last') }}" style="display: inline;">
        <button type="submit" class="btn" style="margin-left: 8px; padding: 4px 12px; font-size: 13px;">Reload it</button>
    </form>
</div>
{% endif %}

<div class="empty-state">
    <div class="icon">&#128218;</div>
    <h3>No data loaded yet</h3>
    <p>Upload a CSV or Excel export from your ILS to get started.</p>
    <p style="margin-top: 8px; font-size: 13px;">
        First time? Check the <a href="{{ url_for('getting_started') }}"><strong>Getting Started</strong></a>
        guide for a full walkthrough.
    </p>
    <br>
    <a href="{{ url_for('upload') }}" class="btn">Import Data</a>
</div>
{% endif %}
```

**Step 5: Test the full flow**

1. Upload `sample_data/sample_catalog.csv` via the UI
2. Stop the Flask server (Ctrl+C) and restart it
3. Open http://127.0.0.1:5000 -- should see the reload banner
4. Click "Reload it" -- should redirect to dashboard with data loaded
5. Verify the banner is gone once data is loaded

**Step 6: Commit**

```bash
git add app.py templates/index.html
git commit -m "feat: add reload-last-upload banner and route on dashboard"
```
