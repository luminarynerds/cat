# Plan D: Librarian Panel Feedback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the highest-impact feedback from a simulated panel of 6 librarian reviewers — covering data quality visibility, persistence warnings, board-ready reports, and weeding workflow improvements.

**Architecture:** Mostly template + CSS changes with a few new analyzer functions. One new route (`/summary`). New JS for checkbox selection on weeding pages. All vanilla — no new dependencies.

**Tech Stack:** Flask/Jinja2, pandas, vanilla JS, vanilla CSS

---

## Feature 12: Quick Wins

### Task 1: Persistence Warning on Dashboard

**Files:**
- Modify: `templates/index.html`

**Step 1: Add a dismissible warning below the stat grid**

In `templates/index.html`, add this immediately after the second `.stat-grid` block (the audience breakdown grid), before the "Where to Start" card:

```html
<div class="alert alert-info persistence-warning" id="persistence-warning">
    <strong>Heads up:</strong> Your data is stored in memory only for this session.
    If you close the browser or restart the app, you will need to reload your file.
    {% if filename %}
    The app remembers your last file (<em>{{ filename }}</em>) so you can reload it
    with one click from this page.
    {% endif %}
    <button type="button" class="dismiss-btn" onclick="this.parentElement.style.display='none';sessionStorage.setItem('hidePersistenceWarning','1')" aria-label="Dismiss">&times;</button>
</div>
```

**Step 2: Add dismiss button CSS to style.css**

Add after the existing `.alert` styles:

```css
.dismiss-btn {
    float: right;
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    color: inherit;
    padding: 0 0.25rem;
    line-height: 1;
    opacity: 0.6;
}
.dismiss-btn:hover { opacity: 1; }
```

**Step 3: Add script to hide warning if previously dismissed**

In `templates/index.html`, add a `{% block scripts %}` section:

```html
{% block scripts %}
<script>
if (sessionStorage.getItem('hidePersistenceWarning') === '1') {
    var w = document.getElementById('persistence-warning');
    if (w) w.style.display = 'none';
}
</script>
{% endblock %}
```

**Step 4: Commit**

```bash
git add templates/index.html static/css/style.css
git commit -m "feat: add dismissible persistence warning on dashboard"
```

---

### Task 2: Weeding Reassurance Text

**Files:**
- Modify: `templates/weeding.html`
- Modify: `templates/mustie.html`

**Step 1: Add reassurance callout to weeding.html**

In `templates/weeding.html`, add immediately after the `.help-box` and before the `.card` with the threshold form:

```html
<div class="alert alert-info" style="border-left: 4px solid var(--blue-500, #3b82f6);">
    <strong>Remember:</strong> These are suggestions, not orders. Always check the
    item on the shelf before removing it. Your professional judgment matters more
    than any algorithm. When in doubt, keep it.
</div>
```

**Step 2: Add reassurance callout to mustie.html**

In `templates/mustie.html`, add immediately after the `.help-box` and before the `{% if summary.total > 0 %}` block:

```html
<div class="alert alert-info" style="border-left: 4px solid var(--blue-500, #3b82f6);">
    <strong>Remember:</strong> MUSTIE flags are starting points for review, not
    automatic removals. Always check the physical item. A well-loved book with
    high flags may just need rebinding, not removal. Trust your judgment.
</div>
```

**Step 3: Commit**

```bash
git add templates/weeding.html templates/mustie.html
git commit -m "feat: add reassurance text on weeding pages"
```

---

### Task 3: Dewey-Only Label Detection

**Files:**
- Modify: `templates/gaps.html`
- Modify: `templates/freshness.html`
- Modify: `app.py` (gaps route, freshness route)

**Step 1: Pass classification system to gaps template**

In `app.py`, update the `gaps()` route (around line 222) to detect the dominant classification system and pass it:

```python
@app.route("/gaps")
def gaps():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    gap_data = find_gaps(df)
    # Detect dominant classification system
    class_system = "LC"
    if "classification_system" in df.columns:
        lc = int((df["classification_system"] == "LC").sum())
        dw = int((df["classification_system"] == "Dewey").sum())
        if dw > lc:
            class_system = "Dewey"
    return render_template("gaps.html", gaps=gap_data, filename=_current_filename,
                           audience_filter=audience_filter, class_system=class_system)
```

**Step 2: Update gaps.html to use class_system variable**

Replace hardcoded "LC class" references in `templates/gaps.html`:

In the help-box, change:
```
<span class="jargon" data-tip="Library of Congress classification - a system that organizes books by subject using letter codes">LC class</span>
```
to:
```
<span class="jargon" data-tip="A system that organizes books by subject using {{ 'number codes (000-999)' if class_system == 'Dewey' else 'letter codes (A-Z)' }}">{{ 'Dewey range' if class_system == 'Dewey' else 'LC class' }}</span>
```

In the table headers, change all instances of `<th>Class</th>` to:
```html
<th>{{ 'Range' if class_system == 'Dewey' else 'Class' }}</th>
```

**Step 3: Do the same for freshness.html**

In `app.py`, update the `freshness()` route to pass `class_system` the same way.

In `templates/freshness.html`, replace any "LC class" references with `{{ 'Dewey range' if class_system == 'Dewey' else 'LC class' }}`.

**Step 4: Commit**

```bash
git add app.py templates/gaps.html templates/freshness.html
git commit -m "feat: detect Dewey-only collections and adjust classification labels"
```

---

### Task 4: Data Quality Summary Post-Upload

**Files:**
- Modify: `analyzer.py`
- Modify: `app.py`
- Modify: `templates/index.html`

**Step 1: Add data_quality_check function to analyzer.py**

Add after `collection_summary()`:

```python
def data_quality_check(df: pd.DataFrame) -> dict:
    """Check for common data quality issues after import."""
    current_year = datetime.now().year
    issues = []

    # Future pub years
    if df["pub_year"].notna().any():
        future = int((df["pub_year"] > current_year).sum())
        if future > 0:
            issues.append(f"{future} items have future publication years (after {current_year})")

    # Missing call numbers
    missing_cn = int(df["call_number"].isna().sum())
    total = len(df)
    if missing_cn > 0:
        pct = round(missing_cn / total * 100, 1)
        issues.append(f"{missing_cn} items ({pct}%) have no call number")

    # Missing checkouts
    if "checkouts" in df.columns:
        missing_circ = int(df["checkouts"].isna().sum())
        if missing_circ > 0:
            pct = round(missing_circ / total * 100, 1)
            issues.append(f"{missing_circ} items ({pct}%) have no checkout data")

    # No pub year
    missing_year = int(df["pub_year"].isna().sum())
    if missing_year > 0:
        pct = round(missing_year / total * 100, 1)
        issues.append(f"{missing_year} items ({pct}%) have no publication year")

    # Negative checkouts
    if "checkouts" in df.columns and df["checkouts"].notna().any():
        neg = int((df["checkouts"] < 0).sum())
        if neg > 0:
            issues.append(f"{neg} items have negative checkout counts")

    return {
        "total_items": total,
        "issues": issues,
        "has_issues": len(issues) > 0,
    }
```

**Step 2: Store quality report after upload and pass to dashboard**

In `app.py`, after a successful import (around line 168-170), add:

```python
from analyzer import data_quality_check

# After _current_df = import_catalog(filepath)
_data_quality = data_quality_check(_current_df)
```

Add `_data_quality = None` near the top of app.py with the other globals.

In the upload route, after setting `_current_df`, set `_data_quality`:

```python
global _current_df, _current_filename, _data_quality
# ... existing import code ...
_current_df = import_catalog(filepath)
_current_filename = file.filename
_data_quality = data_quality_check(_current_df)
```

In the `index()` route, pass it to the template:

```python
return render_template(
    "index.html",
    summary=summary,
    filename=_current_filename,
    last_upload=last_upload,
    audience_filter=audience_filter,
    data_quality=_data_quality,
)
```

**Step 3: Show quality report on dashboard**

In `templates/index.html`, add after the persistence warning and before the stat grid:

```html
{% if data_quality and data_quality.has_issues %}
<div class="card" style="border-left: 4px solid var(--amber-500, #f59e0b); margin-bottom: 1.5rem;">
    <h3 style="margin-top: 0;">Data Quality Notes</h3>
    <p style="color: var(--gray-600); font-size: 0.9rem;">
        These issues were found in your uploaded data. Items are still included in reports,
        but some results may be affected.
    </p>
    <ul style="margin: 0.5rem 0; padding-left: 1.25rem;">
        {% for issue in data_quality.issues %}
        <li style="margin-bottom: 0.35rem;">{{ issue }}</li>
        {% endfor %}
    </ul>
</div>
{% endif %}
```

**Step 4: Commit**

```bash
git add analyzer.py app.py templates/index.html
git commit -m "feat: add data quality check with post-upload issue report on dashboard"
```

---

## Feature 13: Board Reports

### Task 5: Executive Summary Page

**Files:**
- Create: `templates/summary.html`
- Modify: `app.py`
- Modify: `templates/base.html`
- Modify: `analyzer.py`

**Step 1: Add generate_recommendations function to analyzer.py**

Add after `data_quality_check()`:

```python
def generate_recommendations(df: pd.DataFrame, summary: dict, gaps: dict) -> list[dict]:
    """Generate top 3 actionable recommendations based on collection data."""
    recs = []
    current_year = datetime.now().year

    # Check for aging subjects
    if gaps.get("aging_areas"):
        worst = gaps["aging_areas"][0]
        recs.append({
            "priority": 1,
            "title": f"Update {worst['label']} collection",
            "detail": f"The {worst['label']} section has a median publication year of "
                      f"{int(worst['pub_year'])} ({int(worst['median_age'])} years old). "
                      f"Consider purchasing newer titles in this area.",
            "type": "purchase",
        })

    # Check never-circulated percentage
    if summary.get("items_never_circulated") is not None:
        pct = round(summary["items_never_circulated"] / summary["total_items"] * 100, 1)
        if pct > 20:
            recs.append({
                "priority": 2,
                "title": f"Review {summary['items_never_circulated']:,} never-circulated items",
                "detail": f"{pct}% of your collection has never been checked out. "
                          f"Review these items for possible weeding or repositioning.",
                "type": "weed",
            })

    # Check for underrepresented subjects
    if gaps.get("underrepresented_subjects"):
        count = len(gaps["underrepresented_subjects"])
        recs.append({
            "priority": 3,
            "title": f"Fill gaps in {count} thin subject areas",
            "detail": f"{count} subject areas each represent less than 3% of your "
                      f"collection. Review whether your community needs better "
                      f"coverage in these areas.",
            "type": "purchase",
        })

    # Check median age
    if summary.get("median_age") and summary["median_age"] > 15:
        recs.append({
            "priority": 4,
            "title": "Collection is aging overall",
            "detail": f"Your median item age is {summary['median_age']} years. "
                      f"A typical public library aims for 10-12 years. "
                      f"Consider accelerating weeding and new acquisitions.",
            "type": "weed",
        })

    # Check duplicates
    from analyzer import find_duplicates
    dupes = find_duplicates(df)
    if dupes.get("isbn_groups"):
        dupe_count = len(dupes["isbn_groups"])
        if dupe_count > 20:
            recs.append({
                "priority": 5,
                "title": f"Investigate {dupe_count} duplicate groups",
                "detail": f"Found {dupe_count} groups of items sharing the same ISBN. "
                          f"Some may be intentional copies; others may be accidental.",
                "type": "review",
            })

    # Sort by priority and return top 3
    recs.sort(key=lambda r: r["priority"])
    return recs[:3]
```

**Step 2: Add /summary route to app.py**

Add after the `index()` route:

```python
@app.route("/summary")
def executive_summary():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    summary = collection_summary(df)
    gap_data = find_gaps(df)
    recommendations = generate_recommendations(df, summary, gap_data)

    # Classification system
    class_system = "LC"
    if "classification_system" in df.columns:
        lc = int((df["classification_system"] == "LC").sum())
        dw = int((df["classification_system"] == "Dewey").sum())
        if dw > lc:
            class_system = "Dewey"

    return render_template(
        "summary.html",
        summary=summary,
        gaps=gap_data,
        recommendations=recommendations,
        class_system=class_system,
        filename=_current_filename,
    )
```

**Step 3: Create templates/summary.html**

```html
{% extends "base.html" %}
{% block title %}Executive Summary — Collection Analyzer{% endblock %}

{% block content %}
<div class="page-header">
    <h2>Executive Summary</h2>
    <p>Collection health overview for administrators and board members</p>
</div>

<div class="help-box">
    <strong>What is this page?</strong>
    A one-page summary of your collection's health, designed to share with your
    library board or administration. Use Ctrl+P (Cmd+P on Mac) to print a clean copy.
</div>

<div class="summary-print-header" style="display: none;">
    <h1>Collection Health Report</h1>
    <p>{{ filename }} &mdash; Generated {{ now }}</p>
</div>

<div class="card" style="margin-bottom: 1.5rem;">
    <h3 style="margin-top: 0;">Collection Snapshot</h3>
    <div class="stat-grid">
        <div class="stat-card">
            <div class="label">Total Items</div>
            <div class="value">{{ "{:,}".format(summary.total_items) }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Unique Titles</div>
            <div class="value">{{ "{:,}".format(summary.unique_titles) }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Median Age</div>
            <div class="value">{{ summary.median_age or 'N/A' }} years</div>
        </div>
        <div class="stat-card">
            <div class="label">Total Checkouts</div>
            <div class="value">{{ "{:,}".format(summary.total_checkouts) }}</div>
        </div>
    </div>
</div>

{% if recommendations %}
<div class="card" style="margin-bottom: 1.5rem;">
    <h3 style="margin-top: 0;">Top Priorities</h3>
    <p style="color: var(--gray-600); font-size: 0.9rem; margin-bottom: 1rem;">
        Based on your collection data, here are the most important actions to consider:
    </p>
    {% for rec in recommendations %}
    <div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--gray-50, #f9fafb); border-radius: 6px; border-left: 4px solid {% if rec.type == 'weed' %}var(--red-500, #ef4444){% elif rec.type == 'purchase' %}var(--blue-500, #3b82f6){% else %}var(--amber-500, #f59e0b){% endif %};">
        <strong>{{ loop.index }}. {{ rec.title }}</strong>
        <p style="margin: 0.25rem 0 0; color: var(--gray-600); font-size: 0.9rem;">{{ rec.detail }}</p>
    </div>
    {% endfor %}
</div>
{% endif %}

{% if gaps.get("aging_areas") %}
<div class="card" style="margin-bottom: 1.5rem;">
    <h3 style="margin-top: 0;">Aging Subject Areas</h3>
    <p style="color: var(--gray-600); font-size: 0.9rem;">
        Subjects where the typical item is more than 15 years old:
    </p>
    <div class="table-scroll">
    <table>
        <thead>
            <tr>
                <th>{{ 'Range' if class_system == 'Dewey' else 'Class' }}</th>
                <th>Subject</th>
                <th>Median Age</th>
            </tr>
        </thead>
        <tbody>
            {% for s in gaps.aging_areas[:10] %}
            <tr>
                <td>{{ s.broad_class }}</td>
                <td>{{ s.label }}</td>
                <td>{{ s.median_age | int }} years</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </div>
</div>
{% endif %}

{% if summary.items_never_circulated is not none %}
<div class="card" style="margin-bottom: 1.5rem;">
    <h3 style="margin-top: 0;">Circulation Overview</h3>
    <div class="stat-grid">
        <div class="stat-card">
            <div class="label">Items Circulating</div>
            <div class="value">{{ "{:,}".format(summary.total_items - summary.items_never_circulated) }}</div>
            <div class="detail">{{ ((summary.total_items - summary.items_never_circulated) / summary.total_items * 100) | round(1) }}% of collection</div>
        </div>
        <div class="stat-card">
            <div class="label">Never Checked Out</div>
            <div class="value">{{ "{:,}".format(summary.items_never_circulated) }}</div>
            <div class="detail">{{ (summary.items_never_circulated / summary.total_items * 100) | round(1) }}% of collection</div>
        </div>
    </div>
</div>
{% endif %}

<p style="color: var(--gray-500); font-size: 0.8rem; margin-top: 2rem;">
    Generated by Collection Analyzer Tool from <em>{{ filename }}</em>.
    For detailed reports, visit the full application.
</p>
{% endblock %}
```

**Step 4: Add nav link in base.html**

In `templates/base.html`, add after the Dashboard link and before Getting Started:

```html
<a href="{{ url_for('executive_summary') }}" class="{% if request.endpoint == 'executive_summary' %}active{% endif %}">Board Summary</a>
```

**Step 5: Pass `now` to the template in the route**

In the `executive_summary()` route, add:

```python
from datetime import datetime
# ... in the render_template call:
now=datetime.now().strftime("%B %d, %Y"),
```

**Step 6: Commit**

```bash
git add analyzer.py app.py templates/summary.html templates/base.html
git commit -m "feat: add executive summary page with auto-generated recommendations"
```

---

### Task 6: Print-Optimized Styles

**Files:**
- Modify: `static/css/style.css`

**Step 1: Enhance the @media print block**

Replace the existing `@media print` block (around line 643) with:

```css
@media print {
    .sidebar, .hamburger, .sidebar-overlay { display: none !important; }
    .main-content { margin-left: 0; padding: 16px; max-width: 100%; }
    .export-bar, .btn, .btn-export, .btn-sm { display: none; }
    .help-box { break-inside: avoid; border: 1px solid #ccc; }
    .help-toggle { display: none; }
    .help-body.collapsed { display: block !important; }
    .card { break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }
    .stat-grid { grid-template-columns: 1fr 1fr; gap: 0.5rem; }
    .stat-card { box-shadow: none; border: 1px solid #ddd; }
    table { font-size: 0.8rem; width: 100%; }
    th, td { padding: 0.25rem 0.5rem; }
    .persistence-warning, .dismiss-btn { display: none; }
    .alert { border: 1px solid #ccc; background: #f9f9f9 !important; }
    .page-header { margin-bottom: 0.5rem; }
    .summary-print-header { display: block !important; text-align: center; margin-bottom: 1rem; }
    a { color: inherit; text-decoration: none; }
    @page { margin: 0.75in; }
}
```

**Step 2: Commit**

```bash
git add static/css/style.css
git commit -m "feat: enhance print styles for letter paper output"
```

---

## Feature 14: Weeding Workflow

### Task 7: Flag-for-Review Checkboxes on Weeding Pages

**Files:**
- Create: `static/js/flag-review.js`
- Modify: `templates/weeding.html`
- Modify: `templates/mustie.html`
- Modify: `static/css/style.css`

**Step 1: Create flag-review.js using safe DOM methods**

```javascript
document.addEventListener('DOMContentLoaded', function () {
    var tables = document.querySelectorAll('table[data-flaggable]');
    if (!tables.length) return;

    tables.forEach(function (table) {
        var pageKey = 'flagged:' + location.pathname + location.search;

        // Load saved flags
        var saved = {};
        try { saved = JSON.parse(sessionStorage.getItem(pageKey) || '{}'); } catch (e) { saved = {}; }

        // Add header checkbox
        var headerRow = table.querySelector('thead tr');
        if (!headerRow) return;
        var th = document.createElement('th');
        th.style.width = '40px';
        var selectAll = document.createElement('input');
        selectAll.type = 'checkbox';
        selectAll.title = 'Select all';
        selectAll.setAttribute('aria-label', 'Select all rows');
        th.appendChild(selectAll);
        headerRow.insertBefore(th, headerRow.firstChild);

        // Add row checkboxes
        var rows = table.querySelectorAll('tbody tr');
        rows.forEach(function (row, idx) {
            var td = document.createElement('td');
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'flag-checkbox';
            cb.dataset.idx = idx;
            cb.setAttribute('aria-label', 'Flag row ' + (idx + 1) + ' for review');
            if (saved[idx]) cb.checked = true;
            td.appendChild(cb);
            row.insertBefore(td, row.firstChild);

            cb.addEventListener('change', function () {
                if (cb.checked) { saved[idx] = true; }
                else { delete saved[idx]; }
                sessionStorage.setItem(pageKey, JSON.stringify(saved));
                updateCount();
            });
        });

        // Select all handler
        selectAll.addEventListener('change', function () {
            rows.forEach(function (row, idx) {
                var cb = row.querySelector('.flag-checkbox');
                if (cb) {
                    cb.checked = selectAll.checked;
                    if (selectAll.checked) { saved[idx] = true; }
                    else { delete saved[idx]; }
                }
            });
            sessionStorage.setItem(pageKey, JSON.stringify(saved));
            updateCount();
        });

        // Flagged count display + download button
        var controls = document.createElement('div');
        controls.className = 'flag-controls';
        controls.style.display = 'none';

        var countSpan = document.createElement('span');
        countSpan.className = 'flag-count';
        controls.appendChild(countSpan);

        var dlBtn = document.createElement('button');
        dlBtn.type = 'button';
        dlBtn.className = 'btn btn-sm';
        dlBtn.textContent = 'Download Flagged CSV';
        dlBtn.addEventListener('click', function () { downloadFlagged(table, saved); });
        controls.appendChild(dlBtn);

        var clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn btn-sm';
        clearBtn.style.marginLeft = '0.5rem';
        clearBtn.textContent = 'Clear Selection';
        clearBtn.addEventListener('click', function () {
            saved = {};
            sessionStorage.setItem(pageKey, JSON.stringify(saved));
            rows.forEach(function (row) {
                var cb = row.querySelector('.flag-checkbox');
                if (cb) cb.checked = false;
            });
            selectAll.checked = false;
            updateCount();
        });
        controls.appendChild(clearBtn);

        table.parentElement.insertBefore(controls, table);

        function updateCount() {
            var n = Object.keys(saved).length;
            if (n > 0) {
                controls.style.display = 'flex';
                countSpan.textContent = n + ' item' + (n === 1 ? '' : 's') + ' flagged for review';
            } else {
                controls.style.display = 'none';
            }
        }
        updateCount();
    });

    function downloadFlagged(table, saved) {
        var headers = [];
        var headerCells = table.querySelectorAll('thead th');
        // Skip first column (checkbox)
        for (var i = 1; i < headerCells.length; i++) {
            headers.push(headerCells[i].textContent.trim());
        }

        var csvRows = [headers.join(',')];
        var rows = table.querySelectorAll('tbody tr');
        rows.forEach(function (row, idx) {
            if (!saved[idx]) return;
            var cells = row.querySelectorAll('td');
            var values = [];
            // Skip first cell (checkbox)
            for (var i = 1; i < cells.length; i++) {
                var text = cells[i].textContent.trim().replace(/"/g, '""');
                values.push('"' + text + '"');
            }
            csvRows.push(values.join(','));
        });

        var blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'flagged-for-review.csv';
        a.click();
        URL.revokeObjectURL(url);
    }
});
```

**Step 2: Add data-flaggable attribute to weeding tables**

In `templates/weeding.html`, find the `<table>` tag in the candidates section and add `data-flaggable`:

```html
<table data-flaggable>
```

In `templates/mustie.html`, find the flagged items `<table>` (the one with 11 columns, not the subject breakdown table) and add `data-flaggable`:

```html
<table data-flaggable>
```

**Step 3: Add script tag to base.html**

In `templates/base.html`, add after the help-toggle.js script:

```html
<script src="{{ url_for('static', filename='js/flag-review.js') }}" defer></script>
```

**Step 4: Add flag-controls CSS**

Add to `static/css/style.css` after the `.help-body.collapsed` styles:

```css
.flag-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    background: var(--blue-50, #eff6ff);
    border: 1px solid var(--blue-200, #bfdbfe);
    border-radius: 6px;
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
}
.flag-count { font-weight: 600; color: var(--blue-700, #1d4ed8); }
.flag-checkbox { cursor: pointer; width: 18px; height: 18px; }
```

**Step 5: Commit**

```bash
git add static/js/flag-review.js templates/weeding.html templates/mustie.html templates/base.html static/css/style.css
git commit -m "feat: add flag-for-review checkboxes with CSV download on weeding pages"
```

---

### Task 8: Call-Number-Sorted Pull List Export

**Files:**
- Modify: `app.py`
- Modify: `templates/weeding.html`
- Modify: `templates/mustie.html`

**Step 1: Add pull list export route to app.py**

Add after the existing `export_weeding` route:

```python
@app.route("/export/pull-list")
def export_pull_list():
    """Export a shelf-walk pull list sorted by call number."""
    df = get_df()
    if df is None:
        return "No data loaded.", 400
    df, _ = _apply_audience_filter(df)

    source = request.args.get("source", "weeding")
    if source == "mustie":
        from mustie import apply_mustie, get_default_thresholds
        thresholds = _custom_thresholds if _custom_thresholds else get_default_thresholds()
        candidates = apply_mustie(df, thresholds)
    else:
        age_thresh = request.args.get("age", 15, type=int)
        circ_thresh = request.args.get("circ", 2, type=int)
        candidates = weeding_candidates(df, age_thresh, circ_thresh)

    if candidates is None or len(candidates) == 0:
        return "No candidates to export.", 400

    # Select pull-list columns and sort by call number
    cols = ["call_number", "title", "author"]
    if "location" in candidates.columns:
        cols.insert(1, "location")

    pull = candidates[cols].copy()
    pull = pull.sort_values("call_number", na_position="last")
    rows = pull.fillna("").to_dict("records")
    return _csv_response(rows, "pull-list.csv")
```

**Step 2: Add pull list download button to weeding.html**

In `templates/weeding.html`, in the `.export-bar`, add after the existing CSV download link:

```html
<a href="{{ url_for('export_pull_list', source='weeding', age=age_threshold, circ=circ_threshold) }}" class="btn-export">Download Pull List</a>
```

**Step 3: Add pull list download button to mustie.html**

In `templates/mustie.html`, in the `.export-bar`, add after the existing CSV download link:

```html
<a href="{{ url_for('export_pull_list', source='mustie') }}" class="btn-export">Download Pull List</a>
```

**Step 4: Commit**

```bash
git add app.py templates/weeding.html templates/mustie.html
git commit -m "feat: add call-number-sorted pull list export for shelf walks"
```

---

## Feature 15: Report Availability

### Task 9: Report Availability Indicator on Dashboard

**Files:**
- Modify: `analyzer.py`
- Modify: `app.py`
- Modify: `templates/index.html`
- Modify: `static/css/style.css`

**Step 1: Add report_availability function to analyzer.py**

Add after `data_quality_check()`:

```python
def report_availability(df: pd.DataFrame) -> list[dict]:
    """Check which reports have enough data to be useful."""
    reports = [
        {
            "name": "Collection Gaps",
            "url": "gaps",
            "requires": "Call Number + Publication Year",
            "available": df["call_number"].notna().any() and df["pub_year"].notna().any(),
        },
        {
            "name": "Subject Balance",
            "url": "subjects",
            "requires": "Call Number",
            "available": df["call_number"].notna().any(),
        },
        {
            "name": "Freshness",
            "url": "freshness",
            "requires": "Call Number + Publication Year",
            "available": df["call_number"].notna().any() and df["pub_year"].notna().any(),
        },
        {
            "name": "Age Distribution",
            "url": "age",
            "requires": "Publication Year",
            "available": df["pub_year"].notna().any(),
        },
        {
            "name": "Format Breakdown",
            "url": "formats",
            "requires": "Format",
            "available": df["format"].notna().any(),
        },
        {
            "name": "Duplicates",
            "url": "duplicates",
            "requires": "ISBN or Title + Author",
            "available": df["isbn"].notna().any() or (df["title"].notna().any() and df["author"].notna().any()),
        },
        {
            "name": "Cost & ROI",
            "url": "cost",
            "requires": "Price",
            "available": df["price"].notna().any(),
        },
        {
            "name": "Usage Analysis",
            "url": "circulation",
            "requires": "Checkouts",
            "available": df["checkouts"].notna().any(),
        },
        {
            "name": "Dormant Items",
            "url": "dormant",
            "requires": "Last Checkout Date",
            "available": df["last_checkout"].notna().any(),
        },
        {
            "name": "Weeding (Simple)",
            "url": "weeding",
            "requires": "Publication Year + Checkouts",
            "available": df["pub_year"].notna().any() and df["checkouts"].notna().any(),
        },
        {
            "name": "Weeding (MUSTIE)",
            "url": "mustie_weeding",
            "requires": "Publication Year + Checkouts",
            "available": df["pub_year"].notna().any() and df["checkouts"].notna().any(),
        },
        {
            "name": "Banned/Challenged Books",
            "url": "banned_books",
            "requires": "Title",
            "available": df["title"].notna().any(),
        },
        {
            "name": "Diversity Audit",
            "url": "diversity",
            "requires": "Subject",
            "available": df["subject"].notna().any(),
        },
    ]
    return reports
```

**Step 2: Pass report availability to dashboard**

In `app.py`, in the `index()` route, after computing `summary`:

```python
from analyzer import report_availability

# Inside the if df is not None block:
reports = report_availability(df)
```

Pass `reports=reports` to `render_template`. Set `reports=None` in the else case.

**Step 3: Add report availability section to index.html**

In `templates/index.html`, replace the existing "Where to Start" card with:

```html
<div class="card" style="grid-column: 1 / -1;">
    <h3>Your Reports</h3>
    <p style="color: var(--gray-600); font-size: 0.9rem; margin-bottom: 1rem;">
        Based on your uploaded data, here is what each report can show you:
    </p>
    <div class="report-grid">
        {% for r in reports %}
        <a href="{{ url_for(r.url) }}" class="report-link {{ 'available' if r.available else 'unavailable' }}">
            <span class="report-dot {{ 'green' if r.available else 'gray' }}"></span>
            <span class="report-name">{{ r.name }}</span>
            {% if not r.available %}
            <span class="report-missing">Needs: {{ r.requires }}</span>
            {% endif %}
        </a>
        {% endfor %}
    </div>
</div>
```

**Step 4: Add report-grid CSS**

Add to `static/css/style.css`:

```css
.report-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.5rem;
}
.report-link {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    text-decoration: none;
    color: inherit;
    border: 1px solid var(--gray-200);
    font-size: 0.9rem;
    flex-wrap: wrap;
}
.report-link.available:hover { background: var(--gray-50); }
.report-link.unavailable { opacity: 0.55; }
.report-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 0.3rem;
    flex-shrink: 0;
}
.report-dot.green { background: var(--green-500, #22c55e); }
.report-dot.gray { background: var(--gray-300); }
.report-name { font-weight: 500; }
.report-missing {
    font-size: 0.75rem;
    color: var(--gray-500);
    width: 100%;
    padding-left: 1.25rem;
}
```

**Step 5: Commit**

```bash
git add analyzer.py app.py templates/index.html static/css/style.css
git commit -m "feat: add report availability indicator on dashboard showing which reports have data"
```

---

### Task 10: Upload Redirect to Data Quality Page

**Files:**
- Modify: `app.py`

**Step 1: Update upload route to flash quality issues**

In `app.py`, update the upload POST handler. After the import succeeds and `_data_quality` is computed, if there are issues, flash them individually:

```python
_data_quality = data_quality_check(_current_df)
flash(f"Imported {len(_current_df)} items from {file.filename}.", "success")
if _data_quality["has_issues"]:
    for issue in _data_quality["issues"]:
        flash(issue, "warning")
```

This way the dashboard shows both the success message and any quality warnings as separate flash alerts without needing a new route.

**Step 2: Commit**

```bash
git add app.py
git commit -m "feat: flash data quality warnings after upload"
```

---

## Verification

After all 10 tasks:

1. Dashboard shows persistence warning (dismissible, stays dismissed for session)
2. Dashboard shows data quality issues if any (e.g., missing call numbers)
3. Dashboard shows report availability grid with green/gray dots
4. Weeding pages show reassurance text
5. Weeding tables have checkboxes, select-all, flagged count, download flagged CSV
6. Both weeding pages have "Download Pull List" button (sorted by call number)
7. `/summary` page shows executive summary with top 3 recommendations
8. `Board Summary` link appears in sidebar navigation
9. Gaps/freshness pages show "Dewey range" instead of "LC class" when Dewey-dominant
10. Ctrl+P on any page gives clean print output with no sidebar, no buttons
11. Print on summary page shows a centered header with report title and date
