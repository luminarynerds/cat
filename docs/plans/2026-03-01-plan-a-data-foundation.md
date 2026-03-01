# Plan A: Data Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add import templates, last-upload persistence, full MUSTIE settings, digital format support, and cost-per-circ with inline price editing.

**Architecture:** Five independent features layered onto the existing Flask app. Features 1-2 add download routes and a JSON metadata file. Feature 3 expands the MUSTIE settings form. Feature 4 adds a digital format classifier in the importer. Feature 5 adds a cost-per-circ column and a small inline-edit JS module.

**Tech Stack:** Python 3.10+, Flask 3.1, pandas 2.2, Jinja2, vanilla JavaScript, CSS.

---

### Task 1: Create blank CSV template

**Files:**
- Create: `sample_data/template_blank.csv`

**Step 1: Create the file**

Create `sample_data/template_blank.csv` with exactly this content (one line, no trailing newline):

```csv
Title,Author,ISBN,Call Number,Publication Year,Subject,Format,Location,Barcode,Checkouts,Last Checkout Date,Date Added,Status,Price,Collection,Copies
```

**Step 2: Verify the importer recognizes the headers**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
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

### Task 2: Create example CSV template

**Files:**
- Create: `sample_data/template_example.csv`

**Step 1: Create the file**

Create `sample_data/template_example.csv`:

```csv
Title,Author,ISBN,Call Number,Publication Year,Subject,Format,Location,Barcode,Checkouts,Last Checkout Date,Date Added,Status,Price,Collection,Copies
The Great Gatsby,"Fitzgerald, F. Scott",9780743273565,PS3511.I9 G7,1925,American Fiction,Book,Main,30112345678901,47,2026-01-15,2010-03-01,Available,15.99,Adult Fiction,2
Coding for Kids,"Martinez, Ana",9781234567890,QA76.73.P98,2022,Computer Science,Book,Children,30112345678902,12,2025-11-20,2022-06-15,Available,24.95,Juvenile Non-Fiction,1
Jazz Standards Collection,Various Artists,,M1630.18,2019,Music,CD,Main,30112345678903,8,2025-08-03,2019-09-10,Available,18.99,Adult Non-Fiction,1
National Geographic World Atlas,,9780792275428,G1021.N38,2015,Geography,DVD,Reference,30112345678904,0,,2015-04-22,Available,29.95,Reference,1
Becoming,"Obama, Michelle",9781524763138,E909.O24,2018,Biography,Audiobook,Main,30112345678905,31,2026-02-10,2019-01-08,Checked Out,39.99,Adult Non-Fiction,3
```

**Step 2: Verify the importer handles it**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
df = import_catalog('sample_data/template_example.csv')
print(f'Rows: {len(df)}')
print(f'Formats: {df[\"format\"].unique().tolist()}')
print(f'LC classes: {df[\"lc_class\"].unique().tolist()}')
"
```

Expected: 5 rows. Formats include Book, CD, DVD, Audiobook. LC classes include P, Q, M, G, E.

**Step 3: Commit**

```bash
git add sample_data/template_example.csv
git commit -m "feat: add example CSV template with 5 sample records"
```

---

### Task 3: Add download-template route

**Files:**
- Modify: `app.py:8-10` (add `send_file` import)
- Modify: `app.py:88` (add route after `upload()`)

**Step 1: Add `send_file` to Flask imports**

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

After line 88 (`return render_template("upload.html")`), add:

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

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
resp = client.get('/download-template/template_blank.csv')
print(f'Blank status: {resp.status_code}')
print(f'Content-Disposition: {resp.headers.get(\"Content-Disposition\")}')
resp = client.get('/download-template/../../etc/passwd')
print(f'Path traversal status: {resp.status_code}')
"
```

Expected: Blank returns 200 with attachment header. Path traversal returns 302 redirect.

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add download-template route with allowlist validation"
```

---

### Task 4: Add template download buttons to upload page

**Files:**
- Modify: `templates/upload.html:22-23` (insert between help-box and upload card)

**Step 1: Add the template section**

In `templates/upload.html`, after line 22 (`</div>` closing the help-box) and before line 24 (`<div class="card">`), insert:

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

Open http://127.0.0.1:5000/upload. Confirm:
- Templates card appears between the help text and the upload form
- Both download links work

**Step 3: Commit**

```bash
git add templates/upload.html
git commit -m "feat: add template download buttons to upload page"
```

---

### Task 5: Save last-upload metadata on successful upload

**Files:**
- Modify: `app.py:40-41` (add helpers after `get_df()`)
- Modify: `app.py:77` (call helper after successful import)
- Modify: `.gitignore` (add metadata file)

**Step 1: Add the helper and constant**

After line 41 (`return _current_df`) in `app.py`, add:

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

**Step 2: Call helper in upload route**

In the `upload()` route, after `_current_filename = file.filename` (line 77) and before the `flash()` call, add:

```python
            _save_last_upload(file.filename, len(_current_df))
```

**Step 3: Add to .gitignore**

Append to `.gitignore`:

```
uploads/.last_upload.json
```

**Step 4: Verify**

Upload `sample_data/sample_catalog.csv` via the browser, then:

```bash
cat /Users/sam/Projects/cat/uploads/.last_upload.json
```

Expected: JSON with filename, uploaded_at, row_count of 500.

**Step 5: Commit**

```bash
git add app.py .gitignore
git commit -m "feat: save last-upload metadata on successful import"
```

---

### Task 6: Add reload banner and route to dashboard

**Files:**
- Modify: `app.py:44-54` (update `index()` route to pass `last_upload`)
- Modify: `app.py` (add `POST /reload` route after `index()`)
- Modify: `templates/index.html:83-95` (add reload banner in empty-state)

**Step 1: Update the index route**

In `app.py`, change the `index()` route:

```python
@app.route("/")
def index():
    df = get_df()
    summary = None
    if df is not None:
        summary = collection_summary(df)
    return render_template(
        "index.html",
        summary=summary,
        filename=_current_filename,
    )
```

to:

```python
@app.route("/")
def index():
    df = get_df()
    summary = None
    if df is not None:
        summary = collection_summary(df)
    last_upload = _check_last_upload() if df is None else None
    return render_template(
        "index.html",
        summary=summary,
        filename=_current_filename,
        last_upload=last_upload,
    )
```

**Step 2: Add the reload route**

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

**Step 3: Update the dashboard template**

In `templates/index.html`, replace lines 83-95 (the `{% else %}` empty-state block):

```html
{% else %}

{% if last_upload %}
<div class="help-box" style="border-left: 4px solid var(--accent, var(--primary));">
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

**Step 4: Test the full flow**

1. Upload `sample_data/sample_catalog.csv` via browser
2. Stop the Flask server (Ctrl+C in the background task) and restart it
3. Open http://127.0.0.1:5000 -- should see the reload banner
4. Click "Reload it" -- should redirect to dashboard with data loaded
5. Banner should be gone once data is loaded

**Step 5: Commit**

```bash
git add app.py templates/index.html
git commit -m "feat: add reload-last-upload banner and route on dashboard"
```

---

### Task 7: Add circ_floor to MUSTIE default thresholds

**Files:**
- Modify: `mustie.py:31-53` (add `circ_floor` to each entry in `DEFAULT_CREW_THRESHOLDS`)

**Step 1: Update the thresholds dict**

In `mustie.py`, replace lines 31-53 (`DEFAULT_CREW_THRESHOLDS`) with:

```python
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
```

**Step 2: Verify defaults load correctly**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from mustie import get_default_thresholds
t = get_default_thresholds()
print(f'P circ_floor: {t[\"P\"][\"circ_floor\"]}')
print(f'Q circ_floor: {t[\"Q\"][\"circ_floor\"]}')
print(f'All keys in A: {list(t[\"A\"].keys())}')
"
```

Expected: P circ_floor=1, Q circ_floor=2, keys include label/max_age/max_no_circ_years/circ_floor.

**Step 3: Commit**

```bash
git add mustie.py
git commit -m "feat: add per-subject circ_floor to CREW default thresholds"
```

---

### Task 8: Update apply_mustie to use per-subject thresholds

**Files:**
- Modify: `mustie.py:65-67` (change function signature)
- Modify: `mustie.py:88-93` (add per-subject circ_floor lookup)
- Modify: `mustie.py:144-146` (use per-subject circ_floor for I flag)

**Step 1: Remove the global circ_floor parameter**

In `mustie.py`, change the function signature at line 65-67:

```python
def apply_mustie(df: pd.DataFrame,
                 thresholds: dict[str, dict] | None = None,
                 circ_floor: int = 2) -> pd.DataFrame:
```

to:

```python
def apply_mustie(df: pd.DataFrame,
                 thresholds: dict[str, dict] | None = None,
                 circ_floor: int | None = None) -> pd.DataFrame:
```

**Step 2: Add per-subject circ_floor and max_no_circ_years lookups**

After line 93 (the `subject_max_age` map), add:

```python
    # Look up per-subject circ floor (falls back to global circ_floor or 2)
    global_circ_floor = circ_floor if circ_floor is not None else 2
    result["subject_circ_floor"] = result["broad_class"].map(
        lambda c: thresholds.get(c, {}).get("circ_floor", global_circ_floor)
        if pd.notna(c) else global_circ_floor
    )

    # Look up per-subject max no-circ years
    result["subject_max_no_circ"] = result["broad_class"].map(
        lambda c: thresholds.get(c, {}).get("max_no_circ_years", 3)
        if pd.notna(c) else 3
    )
```

**Step 3: Update the I flag to use per-subject circ_floor**

Change line 146:

```python
    result["flag_i"] = (result["circ"] <= circ_floor)
```

to:

```python
    result["flag_i"] = (result["circ"] <= result["subject_circ_floor"])
```

**Step 4: Add subject_circ_floor to output columns**

In the `output_cols` list at line 171-176, add `"subject_circ_floor"` and `"subject_max_no_circ"` after `"subject_max_age"`:

```python
    output_cols = [
        "title", "author", "call_number", "pub_year", "age",
        "checkouts", "format", "broad_class", "subject_max_age",
        "subject_circ_floor", "subject_max_no_circ",
        "mustie_flags", "mustie_count",
        "flag_m", "flag_u", "flag_s", "flag_t", "flag_i", "flag_e",
    ]
```

**Step 5: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from mustie import apply_mustie, get_default_thresholds
df = import_catalog('sample_data/sample_catalog.csv')
thresholds = get_default_thresholds()
flagged = apply_mustie(df, thresholds=thresholds)
print(f'Flagged: {len(flagged)}')
print(f'Columns: {list(flagged.columns)}')
if len(flagged) > 0:
    print(f'Sample circ_floor values: {flagged[\"subject_circ_floor\"].unique().tolist()[:5]}')
"
```

Expected: Flagged items have `subject_circ_floor` and `subject_max_no_circ` columns with varying values per subject.

**Step 6: Commit**

```bash
git add mustie.py
git commit -m "feat: use per-subject circ_floor and max_no_circ_years in MUSTIE"
```

---

### Task 9: Update MUSTIE settings UI for all threshold fields

**Files:**
- Modify: `templates/mustie_settings.html:28-63` (add columns)
- Modify: `app.py:245-267` (update POST handler to read new fields)

**Step 1: Update the settings table**

In `templates/mustie_settings.html`, replace lines 28-63 (the entire card with table) with:

```html
    <div class="card">
        <h3>Thresholds by Subject</h3>
        <p style="color: var(--gray-600); font-size: 13px; margin-bottom: 12px;">
            <strong>Max Age</strong> controls the M (Misleading) flag.
            <strong>Max Dormant</strong> controls how many years with no checkouts before the I flag triggers.
            <strong>Min Checkouts</strong> is the minimum checkout count below which an item is considered low-circulation.
        </p>
        <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th>Class</th>
                    <th>Subject</th>
                    <th>Max Age (yrs)</th>
                    <th>Max Dormant (yrs)</th>
                    <th>Min Checkouts</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
                {% for cls in thresholds | sort %}
                {% set t = thresholds[cls] %}
                <tr>
                    <td><strong>{{ cls }}</strong></td>
                    <td>{{ t.label }}</td>
                    <td>
                        <input type="number" name="age_{{ cls }}"
                               value="{{ t.max_age }}" min="1" max="100"
                               style="width: 70px; padding: 4px 8px; border: 1px solid var(--gray-300); border-radius: 4px; font-size: 14px;">
                    </td>
                    <td>
                        <input type="number" name="no_circ_years_{{ cls }}"
                               value="{{ t.max_no_circ_years }}" min="1" max="50"
                               style="width: 70px; padding: 4px 8px; border: 1px solid var(--gray-300); border-radius: 4px; font-size: 14px;">
                    </td>
                    <td>
                        <input type="number" name="circ_floor_{{ cls }}"
                               value="{{ t.circ_floor }}" min="0" max="100"
                               style="width: 70px; padding: 4px 8px; border: 1px solid var(--gray-300); border-radius: 4px; font-size: 14px;">
                    </td>
                    <td style="font-size: 13px; color: var(--gray-600);">
                        {% if cls in ['K', 'Q', 'R', 'T', 'Z'] %}
                        Fast-changing field &mdash; shorter shelf life recommended
                        {% elif cls in ['D', 'E', 'F', 'M', 'N', 'U', 'V'] %}
                        Slower-changing &mdash; longer shelf life is typical
                        {% elif cls == 'P' %}
                        Literature ages slowly &mdash; classics may stay indefinitely
                        {% else %}
                        Standard shelf life
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
    </div>
```

**Step 2: Update the POST handler in app.py**

In `app.py`, replace the `mustie_settings` POST handling (lines 249-257):

```python
    if request.method == "POST":
        thresholds = get_default_thresholds()
        for cls in thresholds:
            age_key = f"age_{cls}"
            if age_key in request.form:
                try:
                    thresholds[cls]["max_age"] = int(request.form[age_key])
                except ValueError:
                    pass
```

with:

```python
    if request.method == "POST":
        thresholds = get_default_thresholds()
        for cls in thresholds:
            for field, form_prefix in [
                ("max_age", "age"),
                ("max_no_circ_years", "no_circ_years"),
                ("circ_floor", "circ_floor"),
            ]:
                key = f"{form_prefix}_{cls}"
                if key in request.form:
                    try:
                        thresholds[cls][field] = int(request.form[key])
                    except ValueError:
                        pass
```

**Step 3: Verify in browser**

Open http://127.0.0.1:5000/mustie/settings. Confirm:
- Three editable columns: Max Age, Max Dormant, Min Checkouts
- Changing a value and clicking Save redirects to MUSTIE results
- Reset to Defaults restores original values

**Step 4: Commit**

```bash
git add templates/mustie_settings.html app.py
git commit -m "feat: expose all MUSTIE threshold fields in settings UI"
```

---

### Task 10: Remove global circ_floor from MUSTIE route

**Files:**
- Modify: `app.py:228` (remove circ query param from mustie route)
- Modify: `templates/mustie.html` (remove circ param references)

**Step 1: Update the mustie route**

In `app.py`, change the `mustie_weeding()` route (lines 220-242). Remove the `circ_floor` query param since it's now per-subject:

```python
@app.route("/mustie", methods=["GET"])
def mustie_weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    thresholds = _custom_thresholds or get_default_thresholds()

    flagged = apply_mustie(df, thresholds=thresholds)
    summary = mustie_summary(flagged)

    return render_template(
        "mustie.html",
        candidates=flagged.head(200).fillna("").to_dict("records"),
        total_candidates=len(flagged),
        total_items=len(df),
        summary=summary,
        thresholds=thresholds,
        filename=_current_filename,
    )
```

**Step 2: Update the export route**

In `app.py`, update the `export_mustie()` route (lines 278-291). Remove the circ_floor param:

```python
@app.route("/export/mustie")
def export_mustie():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    thresholds = _custom_thresholds or get_default_thresholds()
    flagged = apply_mustie(df, thresholds=thresholds)
    return _csv_response(
        flagged.fillna("").to_dict("records"),
        "mustie_weeding_candidates.csv",
    )
```

**Step 3: Update mustie.html export link**

In `templates/mustie.html`, change line 39:

```html
    <a href="{{ url_for('export_mustie', circ=circ_floor) }}" class="btn-export">Download Full List CSV</a>
```

to:

```html
    <a href="{{ url_for('export_mustie') }}" class="btn-export">Download Full List CSV</a>
```

**Step 4: Verify in browser**

Open http://127.0.0.1:5000/mustie (with data loaded). Confirm the page loads without errors and the CSV export link works.

**Step 5: Commit**

```bash
git add app.py templates/mustie.html
git commit -m "refactor: remove global circ_floor, now per-subject in thresholds"
```

---

### Task 11: Add digital format detection to importer

**Files:**
- Modify: `importer.py:230-238` (add `DIGITAL_FORMATS` set and `is_digital` column in `import_catalog`)

**Step 1: Add the DIGITAL_FORMATS set**

In `importer.py`, after `LC_CLASS_LABELS` (after line 229), add:

```python

# Format values that indicate digital/electronic items.
# Matched case-insensitively against the 'format' column.
DIGITAL_FORMATS = {
    "ebook", "e-book", "digital", "online resource",
    "eaudiobook", "e-audiobook", "streaming video", "streaming audio",
    "database", "electronic", "hoopla", "libby", "kanopy",
    "axis 360", "cloudlibrary",
}
```

**Step 2: Add is_digital column to import_catalog**

In `import_catalog()` (line 232-238), add the `is_digital` column after the `lc_class` line:

```python
def import_catalog(filepath: str) -> pd.DataFrame:
    """Full pipeline: load, normalize, type-coerce, and enrich catalog data."""
    df = load_file(filepath)
    df = normalize_columns(df)
    df = coerce_types(df)
    df["lc_class"] = df["call_number"].apply(extract_lc_class)
    df["is_digital"] = (
        df["format"]
        .fillna("")
        .str.strip()
        .str.lower()
        .isin(DIGITAL_FORMATS)
    )
    return df
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
df = import_catalog('sample_data/sample_catalog.csv')
print(f'is_digital column exists: {\"is_digital\" in df.columns}')
print(f'Digital items: {df[\"is_digital\"].sum()}')
print(f'Formats in sample: {df[\"format\"].unique().tolist()}')
"
```

Expected: is_digital exists. Digital items may be 0 in sample data (the sample uses Book/DVD/CD formats). That's correct.

**Step 4: Commit**

```bash
git add importer.py
git commit -m "feat: add digital format detection with is_digital column"
```

---

### Task 12: Exclude digital items from weeding and MUSTIE

**Files:**
- Modify: `mustie.py:82-83` (filter out digital items at start of apply_mustie)
- Modify: `analyzer.py:210-221` (filter out digital items in weeding_candidates)

**Step 1: Filter digital items in apply_mustie**

In `mustie.py`, after line 83 (`result = df.copy()`), add:

```python
    # Exclude digital items — they can't be physically weeded
    if "is_digital" in result.columns:
        result = result[~result["is_digital"]].copy()
    if len(result) == 0:
        return pd.DataFrame()
```

**Step 2: Filter digital items in weeding_candidates**

In `analyzer.py`, in the `weeding_candidates()` function, after line 216 (`current_year = datetime.now().year`), add:

```python
    # Exclude digital items — they can't be physically weeded
    if "is_digital" in df.columns:
        df = df[~df["is_digital"]].copy()
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from mustie import apply_mustie
from analyzer import weeding_candidates
import pandas as pd

df = import_catalog('sample_data/sample_catalog.csv')
# Manually set some items as digital to test filtering
df.loc[df.index[:5], 'is_digital'] = True
print(f'Total items: {len(df)}')
print(f'Digital items: {df[\"is_digital\"].sum()}')

flagged = apply_mustie(df)
weed = weeding_candidates(df)
print(f'MUSTIE flagged: {len(flagged)}')
print(f'Weeding candidates: {len(weed)}')
# Verify no digital items in results
if len(flagged) > 0 and 'is_digital' in df.columns:
    flagged_indices = flagged.index
    digital_in_flagged = df.loc[df.index.isin(flagged_indices), 'is_digital'].sum()
    print(f'Digital items in MUSTIE results: {digital_in_flagged}')
"
```

Expected: Digital items = 5. No digital items in MUSTIE or weeding results.

**Step 4: Commit**

```bash
git add mustie.py analyzer.py
git commit -m "feat: exclude digital items from weeding and MUSTIE analysis"
```

---

### Task 13: Add digital vs physical summary to format breakdown page

**Files:**
- Modify: `analyzer.py:164-176` (update `format_breakdown` to include digital summary)
- Modify: `app.py:159-172` (pass digital summary to template)
- Modify: `templates/formats.html` (add digital/physical summary section)

**Step 1: Add digital summary function to analyzer**

In `analyzer.py`, after `format_breakdown()` (after line 176), add:

```python

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
```

**Step 2: Update the formats route in app.py**

In `app.py`, add `digital_physical_split` to the import from analyzer (line 14-26):

```python
from analyzer import (
    collection_summary,
    age_distribution,
    subject_balance,
    find_gaps,
    format_breakdown,
    digital_physical_split,
    circulation_analysis,
    weeding_candidates,
    dormant_items,
    find_duplicates,
    cost_analysis,
    collection_freshness,
)
```

Then update the `formats()` route to pass the digital summary:

```python
@app.route("/formats")
def formats():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    data = format_breakdown(df)
    digital = digital_physical_split(df)
    return render_template(
        "formats.html",
        formats=data,
        digital=digital,
        chart_data=json.dumps(data),
        filename=_current_filename,
    )
```

**Step 3: Add digital summary section to formats.html**

In `templates/formats.html`, after the export-bar (after line 22) and before the Format Distribution card, add:

```html

{% if digital.has_data and digital.digital_count > 0 %}
<div class="stat-grid">
    <div class="stat-card">
        <div class="label">Physical Items</div>
        <div class="value">{{ "{:,}".format(digital.physical_count) }}</div>
        <div class="detail">{{ digital.physical_pct }}% of collection{% if digital.physical_avg_circ is defined %} &middot; {{ digital.physical_avg_circ }} avg checkouts{% endif %}</div>
    </div>
    <div class="stat-card">
        <div class="label">Digital Items</div>
        <div class="value">{{ "{:,}".format(digital.digital_count) }}</div>
        <div class="detail">{{ digital.digital_pct }}% of collection{% if digital.digital_avg_circ is defined %} &middot; {{ digital.digital_avg_circ }} avg checkouts{% endif %}</div>
    </div>
</div>
{% endif %}
```

**Step 4: Verify in browser**

Open http://127.0.0.1:5000/formats with data loaded. The digital/physical section only appears if there are digital items in the collection. With the sample data (no digital formats), it won't show -- that's correct.

**Step 5: Commit**

```bash
git add analyzer.py app.py templates/formats.html
git commit -m "feat: add digital vs physical summary to format breakdown page"
```

---

### Task 14: Add cost-per-circ to weeding and MUSTIE outputs

**Files:**
- Modify: `analyzer.py:210-225` (add `cost_per_circ` to weeding output)
- Modify: `mustie.py:171-176` (add `cost_per_circ` to MUSTIE output)

**Step 1: Add cost_per_circ to weeding_candidates**

In `analyzer.py`, in `weeding_candidates()`, before the final return statement (line 223-225), add the computed column:

Change:

```python
    candidates["age"] = current_year - candidates["pub_year"]
    return candidates.sort_values(
        ["checkouts", "age"], ascending=[True, False]
    )[["title", "author", "call_number", "pub_year", "age", "checkouts", "format"]]
```

to:

```python
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
```

**Step 2: Add cost_per_circ to MUSTIE output**

In `mustie.py`, add `"price"` and `"cost_per_circ"` computation before the output_cols list. After line 165 (`result["mustie_flags"] = ...`) and before line 168 (`flagged = result[...]`), add:

```python
    result["cost_per_circ"] = result.apply(
        lambda r: round(r["price"] / r["checkouts"], 2)
        if "price" in result.columns
        and pd.notna(r.get("price")) and r.get("price", 0) > 0
        and pd.notna(r.get("checkouts")) and r.get("checkouts", 0) > 0
        else None,
        axis=1,
    )
```

Then update the output_cols to include `"price"` and `"cost_per_circ"`:

```python
    output_cols = [
        "title", "author", "call_number", "pub_year", "age",
        "checkouts", "price", "cost_per_circ",
        "format", "broad_class", "subject_max_age",
        "subject_circ_floor", "subject_max_no_circ",
        "mustie_flags", "mustie_count",
        "flag_m", "flag_u", "flag_s", "flag_t", "flag_i", "flag_e",
    ]
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from mustie import apply_mustie
from analyzer import weeding_candidates

df = import_catalog('sample_data/sample_catalog.csv')
weed = weeding_candidates(df)
print(f'Weeding columns: {list(weed.columns)}')
if len(weed) > 0:
    sample = weed[weed['cost_per_circ'].notna()].head(3)
    if len(sample) > 0:
        print(sample[['title', 'price', 'checkouts', 'cost_per_circ']].to_string())
    else:
        print('No items with both price and checkouts (expected for some datasets)')

flagged = apply_mustie(df)
print(f'MUSTIE columns: {list(flagged.columns)}')
"
```

Expected: Both outputs include `price` and `cost_per_circ` columns.

**Step 4: Commit**

```bash
git add analyzer.py mustie.py
git commit -m "feat: add cost-per-circ column to weeding and MUSTIE outputs"
```

---

### Task 15: Display cost-per-circ in weeding and MUSTIE templates

**Files:**
- Modify: `templates/weeding.html:51-76` (add Price and $/Circ columns)
- Modify: `templates/mustie.html:100-136` (add Price and $/Circ columns)

**Step 1: Update weeding table**

In `templates/weeding.html`, add two columns to the table header (after the Checkouts `<th>` at line 59):

```html
                <th>Price</th>
                <th>$/Circ</th>
```

And add the corresponding cells in the tbody (after the checkouts `<td>` at line 71):

```html
                <td>{{ "${:,.2f}".format(item.price) if item.price else "" }}</td>
                <td>{{ "${:,.2f}".format(item.cost_per_circ) if item.cost_per_circ else "" }}</td>
```

**Step 2: Update MUSTIE table**

In `templates/mustie.html`, add two columns to the table header (after the Circ `<th>` at line 109):

```html
                <th>Price</th>
                <th>$/Circ</th>
```

And add the corresponding cells in the tbody (after the checkouts/circ `<td>` at line 129):

```html
                <td>{{ "${:,.2f}".format(item.price|float) if item.price else "" }}</td>
                <td>{{ "${:,.2f}".format(item.cost_per_circ|float) if item.cost_per_circ else "" }}</td>
```

**Step 3: Verify in browser**

Upload data and check both /weeding and /mustie pages. Confirm Price and $/Circ columns appear. Items without price data show blank cells.

**Step 4: Commit**

```bash
git add templates/weeding.html templates/mustie.html
git commit -m "feat: display cost-per-circ in weeding and MUSTIE tables"
```

---

### Task 16: Add inline price editing

**Files:**
- Create: `static/js/inline-edit.js`
- Modify: `app.py` (add `POST /edit-item` route)
- Modify: `templates/base.html` (include the JS file)
- Modify: `templates/weeding.html` (make price cells editable)
- Modify: `templates/mustie.html` (make price cells editable)

**Step 1: Create the inline-edit JavaScript**

Create `static/js/inline-edit.js`:

```javascript
/**
 * Inline editing for price cells.
 * Click a cell with class "editable-price" to edit.
 * On blur or Enter, POST the new value to /edit-item.
 */
document.addEventListener('click', function(e) {
    var cell = e.target.closest('.editable-price');
    if (!cell || cell.querySelector('input')) return;

    var original = cell.textContent.trim().replace('$', '').replace(',', '');
    var idx = cell.dataset.idx;
    var field = cell.dataset.field || 'price';

    var input = document.createElement('input');
    input.type = 'number';
    input.step = '0.01';
    input.min = '0';
    input.value = original || '';
    input.style.cssText = 'width: 80px; padding: 2px 6px; font-size: 13px; border: 1px solid var(--primary); border-radius: 4px;';

    cell.textContent = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    function save() {
        var val = input.value.trim();
        if (val === original || val === '') {
            cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
            return;
        }
        fetch('/edit-item', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({index: parseInt(idx), field: field, value: parseFloat(val)})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.ok) {
                cell.textContent = '$' + parseFloat(val).toFixed(2);
            } else {
                cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
            }
        })
        .catch(function() {
            cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
        });
    }

    input.addEventListener('blur', save);
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); save(); }
        if (e.key === 'Escape') {
            cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
        }
    });
});
```

**Step 2: Add the edit-item route**

In `app.py`, add this route (after the `reload_last` route or anywhere convenient):

```python

@app.route("/edit-item", methods=["POST"])
def edit_item():
    global _current_df
    if _current_df is None:
        return {"ok": False, "error": "No data loaded"}, 400
    data = request.get_json()
    if not data:
        return {"ok": False, "error": "No data"}, 400
    idx = data.get("index")
    field = data.get("field")
    value = data.get("value")
    if field != "price":
        return {"ok": False, "error": "Only price is editable"}, 400
    if idx is None or idx < 0 or idx >= len(_current_df):
        return {"ok": False, "error": "Invalid index"}, 400
    try:
        _current_df.at[idx, "price"] = float(value) if value is not None else pd.NA
        return {"ok": True}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}, 400
```

**Step 3: Include the JS in base.html**

In `templates/base.html`, after line 7 (the CSS link), add:

```html
    <script src="{{ url_for('static', filename='js/inline-edit.js') }}" defer></script>
```

**Step 4: Make price cells editable in weeding.html**

In `templates/weeding.html`, change the price `<td>` you added in Task 15 to:

```html
                <td class="editable-price" data-idx="{{ loop.index0 }}" data-field="price" style="cursor: pointer;" title="Click to edit">{{ "${:,.2f}".format(item.price) if item.price else "—" }}</td>
```

**Step 5: Make price cells editable in mustie.html**

Same change in `templates/mustie.html` for the price cell:

```html
                <td class="editable-price" data-idx="{{ loop.index0 }}" data-field="price" style="cursor: pointer;" title="Click to edit">{{ "${:,.2f}".format(item.price|float) if item.price else "—" }}</td>
```

**Step 6: Verify in browser**

1. Open /weeding or /mustie with data loaded
2. Click a price cell -- should turn into an input
3. Enter a new value and press Enter or click away
4. Cell should update with the new price
5. Export Full Catalog CSV and verify the edited price is included

**Step 7: Commit**

```bash
git add static/js/inline-edit.js app.py templates/base.html templates/weeding.html templates/mustie.html
git commit -m "feat: add inline price editing on weeding and MUSTIE pages"
```

---

### Task 17: Add edit-notice to pages with editable prices

**Files:**
- Modify: `templates/weeding.html` (add notice)
- Modify: `templates/mustie.html` (add notice)

**Step 1: Add notice to weeding page**

In `templates/weeding.html`, after the export-bar div and before the alert-warning div, add:

```html

<div style="font-size: 12px; color: var(--gray-600); margin-bottom: 8px;">
    <em>Click any price cell to edit it. Edits are included in CSV exports but not saved to the original file.</em>
</div>
```

**Step 2: Add notice to MUSTIE page**

In `templates/mustie.html`, after the export-bar div (after line 40), add the same notice:

```html

<div style="font-size: 12px; color: var(--gray-600); margin-bottom: 8px;">
    <em>Click any price cell to edit it. Edits are included in CSV exports but not saved to the original file.</em>
</div>
```

**Step 3: Verify in browser**

Check both pages show the italic notice text above the data tables.

**Step 4: Commit**

```bash
git add templates/weeding.html templates/mustie.html
git commit -m "feat: add edit-notice for inline price editing"
```

---

Plan complete and saved to `docs/plans/2026-03-01-plan-a-data-foundation.md`. 17 tasks covering all 5 features in Plan A.

**Two execution options:**

**1. Subagent-Driven (this session)** -- I dispatch a fresh agent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** -- Open a new session with executing-plans, batch execution with checkpoints

Which approach?