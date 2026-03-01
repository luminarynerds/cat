# Plan B: New Analysis Pages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add audience segmentation, banned books flagging, diversity audit, and Dewey classification support to the Library Collection Analyzer.

**Architecture:** Four features layered onto the existing Flask app. Feature 7 adds an `audience` column to the importer and a global filter. Features 8-9 add new report pages with their own analysis functions. Feature 6 extends the importer's classification system and adds Dewey lookup tables. Reordered from the design doc so that audience (a dependency for 8-9) comes first, and Dewey (the largest refactor) comes last.

**Tech Stack:** Python 3.10+, Flask 3.1, pandas 2.2, Jinja2, vanilla JavaScript, CSS.

---

### Task 1: Add audience column derivation to importer

**Files:**
- Modify: `importer.py:241-250` (add audience derivation in `import_catalog`)

**Step 1: Add the derivation function**

In `importer.py`, before `import_catalog()` (before line 241), add:

```python

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
```

**Step 2: Call it in import_catalog**

In `import_catalog()`, after the `is_digital` line, add:

```python
    df["audience"] = df.apply(_derive_audience, axis=1)
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
df = import_catalog('sample_data/sample_catalog.csv')
print(f'audience column: {\"audience\" in df.columns}')
print(f'Distribution: {df[\"audience\"].value_counts().to_dict()}')
"
```

Expected: audience column exists with Adult, YA, Juvenile, and possibly Unknown values.

**Step 4: Commit**

```bash
git add importer.py
git commit -m "feat: derive audience column from collection/location fields"
```

---

### Task 2: Add audience breakdown to dashboard

**Files:**
- Modify: `analyzer.py:10-35` (add audience stats to `collection_summary`)
- Modify: `templates/index.html:65-81` (add audience stat cards)

**Step 1: Add audience stats to collection_summary**

In `analyzer.py`, in `collection_summary()`, add this entry to the returned dict (after `items_never_circulated`):

```python
        "audience_breakdown": (
            df["audience"].value_counts().to_dict()
            if "audience" in df.columns
            else {}
        ),
```

**Step 2: Add audience cards to dashboard**

In `templates/index.html`, after the second stat-grid (after line 65), add:

```html

{% if summary.audience_breakdown %}
<div class="stat-grid">
    {% for aud, count in summary.audience_breakdown.items() %}
    <div class="stat-card">
        <div class="label">{{ aud }}</div>
        <div class="value">{{ "{:,}".format(count) }}</div>
        <div class="detail">{{ (count / summary.total_items * 100) | round(1) }}% of collection</div>
    </div>
    {% endfor %}
</div>
{% endif %}
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from analyzer import collection_summary
df = import_catalog('sample_data/sample_catalog.csv')
s = collection_summary(df)
print(f'Audience breakdown: {s[\"audience_breakdown\"]}')
"
```

**Step 4: Commit**

```bash
git add analyzer.py templates/index.html
git commit -m "feat: add audience breakdown to dashboard stats"
```

---

### Task 3: Add audience filter to all report routes

**Files:**
- Modify: `app.py` (add `_apply_audience_filter` helper, update all report routes)

**Step 1: Add the filter helper**

In `app.py`, after the `get_df()` function (after line 42), add:

```python

def _apply_audience_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Filter DataFrame by audience query param if present."""
    audience = request.args.get("audience")
    if audience and "audience" in df.columns:
        filtered = df[df["audience"] == audience]
        if len(filtered) > 0:
            return filtered, audience
    return df, None
```

**Step 2: Update report routes to use the filter**

Update each of these routes to apply the filter right after the `get_df()` check and pass `audience_filter` to the template. The pattern for each route is:

```python
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)
```

Then add `audience_filter=audience_filter` to each `render_template()` call.

Apply this to these routes: `index`, `subjects`, `gaps`, `formats`, `circulation`, `weeding`, `mustie_weeding`, `dormant`, `freshness`, `age`, `duplicates`, `cost`.

Also update export routes to filter: `export_mustie`, `export_weeding` (add `df, _ = _apply_audience_filter(df)` after the df check).

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
with open('sample_data/sample_catalog.csv', 'rb') as f:
    client.post('/upload', data={'file': (f, 'sample_catalog.csv')}, content_type='multipart/form-data')
# Without filter
resp = client.get('/subjects')
print(f'Unfiltered subjects: {resp.status_code}')
# With filter
resp = client.get('/subjects?audience=YA')
print(f'YA filtered: {resp.status_code}')
resp = client.get('/subjects?audience=Juvenile')
print(f'Juvenile filtered: {resp.status_code}')
"
```

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add audience filter to all report routes"
```

---

### Task 4: Add audience filter dropdown to report templates

**Files:**
- Create: `templates/partials/audience_filter.html`
- Modify: `templates/base.html` or all report templates (include the partial)

**Step 1: Create the filter partial**

Create `templates/partials/audience_filter.html`:

```html
{% if audience_filter is defined %}
<div style="margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
    <label style="font-size: 13px; color: var(--gray-600); font-weight: 500;">Filter by audience:</label>
    <select onchange="if(this.value){location.search='?audience='+this.value}else{location.search=''}" style="padding: 4px 8px; border: 1px solid var(--gray-300); border-radius: 4px; font-size: 13px;">
        <option value="">All audiences</option>
        <option value="Adult" {% if audience_filter == 'Adult' %}selected{% endif %}>Adult</option>
        <option value="YA" {% if audience_filter == 'YA' %}selected{% endif %}>YA</option>
        <option value="Juvenile" {% if audience_filter == 'Juvenile' %}selected{% endif %}>Juvenile</option>
    </select>
    {% if audience_filter %}
    <span style="font-size: 12px; color: var(--primary); font-weight: 500;">Showing: {{ audience_filter }} only</span>
    {% endif %}
</div>
{% endif %}
```

**Step 2: Include in report templates**

Add `{% include "partials/audience_filter.html" %}` at the top of the `{% block content %}` section (after the page-header div) in these templates:
- `templates/subjects.html` (after line 8)
- `templates/gaps.html` (after line 8)
- `templates/freshness.html` (after line 8)
- `templates/formats.html` (after line 8)
- `templates/circulation.html` (after page-header)
- `templates/weeding.html` (after line 8)
- `templates/mustie.html` (after line 8)
- `templates/dormant.html` (after page-header)
- `templates/age.html` (after page-header)
- `templates/cost.html` (after page-header)

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
with open('sample_data/sample_catalog.csv', 'rb') as f:
    client.post('/upload', data={'file': (f, 'sample_catalog.csv')}, content_type='multipart/form-data')
resp = client.get('/subjects')
print(f'Has filter dropdown: {b\"Filter by audience\" in resp.data}')
resp = client.get('/gaps')
print(f'Gaps has filter: {b\"Filter by audience\" in resp.data}')
"
```

**Step 4: Commit**

```bash
git add templates/partials/audience_filter.html templates/*.html
git commit -m "feat: add audience filter dropdown to all report pages"
```

---

### Task 5: Create banned books built-in list

**Files:**
- Create: `data/banned_books.json`

**Step 1: Create the data file**

Create `data/banned_books.json` with a representative set from ALA's frequently challenged/banned books lists:

```json
[
    {"title": "Gender Queer: A Memoir", "author": "Maia Kobabe", "source": "ALA Top 10 Most Challenged 2021-2023"},
    {"title": "All Boys Aren't Blue", "author": "George M. Johnson", "source": "ALA Top 10 Most Challenged 2021-2023"},
    {"title": "The Bluest Eye", "author": "Toni Morrison", "source": "ALA Top 10 Most Challenged 2021-2023"},
    {"title": "Flamer", "author": "Mike Curato", "source": "ALA Top 10 Most Challenged 2022"},
    {"title": "Looking for Alaska", "author": "John Green", "source": "ALA Top 10 Most Challenged 2012-2016"},
    {"title": "The Absolutely True Diary of a Part-Time Indian", "author": "Sherman Alexie", "source": "ALA Top 10 Most Challenged 2010-2014"},
    {"title": "Thirteen Reasons Why", "author": "Jay Asher", "source": "ALA Top 10 Most Challenged 2011-2017"},
    {"title": "The Hate U Give", "author": "Angie Thomas", "source": "ALA Top 10 Most Challenged 2017-2020"},
    {"title": "Drama", "author": "Raina Telgemeier", "source": "ALA Top 10 Most Challenged 2014-2018"},
    {"title": "George", "author": "Alex Gino", "source": "ALA Top 10 Most Challenged 2016-2020"},
    {"title": "Lawn Boy", "author": "Jonathan Evison", "source": "ALA Top 10 Most Challenged 2021-2022"},
    {"title": "The Perks of Being a Wallflower", "author": "Stephen Chbosky", "source": "ALA Top 10 Most Challenged 2004-2016"},
    {"title": "To Kill a Mockingbird", "author": "Harper Lee", "source": "ALA Frequently Challenged Classic"},
    {"title": "Of Mice and Men", "author": "John Steinbeck", "source": "ALA Frequently Challenged Classic"},
    {"title": "The Catcher in the Rye", "author": "J.D. Salinger", "source": "ALA Frequently Challenged Classic"},
    {"title": "The Color Purple", "author": "Alice Walker", "source": "ALA Frequently Challenged Classic"},
    {"title": "Beloved", "author": "Toni Morrison", "source": "ALA Frequently Challenged Classic"},
    {"title": "I Know Why the Caged Bird Sings", "author": "Maya Angelou", "source": "ALA Frequently Challenged Classic"},
    {"title": "Brave New World", "author": "Aldous Huxley", "source": "ALA Frequently Challenged Classic"},
    {"title": "1984", "author": "George Orwell", "source": "ALA Frequently Challenged Classic"},
    {"title": "The Handmaid's Tale", "author": "Margaret Atwood", "source": "ALA Frequently Challenged Classic"},
    {"title": "Slaughterhouse-Five", "author": "Kurt Vonnegut", "source": "ALA Frequently Challenged Classic"},
    {"title": "A Wrinkle in Time", "author": "Madeleine L'Engle", "source": "ALA Frequently Challenged Classic"},
    {"title": "Bridge to Terabithia", "author": "Katherine Paterson", "source": "ALA Frequently Challenged Classic"},
    {"title": "Captain Underpants", "author": "Dav Pilkey", "source": "ALA Top 10 Most Challenged 2012-2014"},
    {"title": "Harry Potter", "author": "J.K. Rowling", "source": "ALA Top 10 Most Challenged 1999-2003"},
    {"title": "The Kite Runner", "author": "Khaled Hosseini", "source": "ALA Top 10 Most Challenged 2008-2014"},
    {"title": "Speak", "author": "Laurie Halse Anderson", "source": "ALA Top 10 Most Challenged 2009-2014"},
    {"title": "The Giver", "author": "Lois Lowry", "source": "ALA Top 10 Most Challenged 1990-2001"},
    {"title": "Go Ask Alice", "author": "Anonymous", "source": "ALA Frequently Challenged Classic"},
    {"title": "A Court of Mist and Fury", "author": "Sarah J. Maas", "source": "ALA Top 10 Most Challenged 2023"},
    {"title": "Tricks", "author": "Ellen Hopkins", "source": "ALA Top 10 Most Challenged 2010-2013"},
    {"title": "It's Perfectly Normal", "author": "Robie Harris", "source": "ALA Top 10 Most Challenged 2005-2014"},
    {"title": "And Tango Makes Three", "author": "Justin Richardson", "source": "ALA Top 10 Most Challenged 2006-2010"},
    {"title": "The Bluest Eye", "author": "Toni Morrison", "source": "ALA Top 10 Most Challenged 2006-2013"},
    {"title": "Stamped: Racism, Antiracism, and You", "author": "Jason Reynolds", "source": "ALA Top 10 Most Challenged 2020-2022"},
    {"title": "Out of Darkness", "author": "Ashley Hope Perez", "source": "ALA Top 10 Most Challenged 2021-2022"},
    {"title": "A Court of Thorns and Roses", "author": "Sarah J. Maas", "source": "ALA Top 10 Most Challenged 2023"},
    {"title": "Crank", "author": "Ellen Hopkins", "source": "ALA Top 10 Most Challenged 2010"},
    {"title": "Me and Earl and the Dying Girl", "author": "Jesse Andrews", "source": "ALA Top 10 Most Challenged 2015"},
    {"title": "This Book Is Gay", "author": "Juno Dawson", "source": "ALA Top 10 Most Challenged 2015-2019"},
    {"title": "Beyond Magenta", "author": "Susan Kuklin", "source": "ALA Top 10 Most Challenged 2015"},
    {"title": "Two Boys Kissing", "author": "David Levithan", "source": "ALA Top 10 Most Challenged 2015"},
    {"title": "I Am Jazz", "author": "Jessica Herthel", "source": "ALA Top 10 Most Challenged 2015-2020"},
    {"title": "Fun Home", "author": "Alison Bechdel", "source": "ALA Top 10 Most Challenged 2006-2015"},
    {"title": "Nineteen Minutes", "author": "Jodi Picoult", "source": "ALA Top 10 Most Challenged 2009"},
    {"title": "My Mom's Having a Baby!", "author": "Dori Hillestad Butler", "source": "ALA Top 10 Most Challenged 2006"},
    {"title": "The Glass Castle", "author": "Jeannette Walls", "source": "ALA Top 10 Most Challenged 2012"},
    {"title": "Sold", "author": "Patricia McCormick", "source": "ALA Top 10 Most Challenged 2014"},
    {"title": "Nasreen's Secret School", "author": "Jeanette Winter", "source": "ALA Top 10 Most Challenged 2013"}
]
```

**Step 2: Verify JSON is valid**

```bash
cd /Users/sam/Projects/cat && python3 -c "
import json
with open('data/banned_books.json') as f:
    data = json.load(f)
print(f'Entries: {len(data)}')
print(f'First: {data[0][\"title\"]} by {data[0][\"author\"]}')
"
```

Expected: 50 entries, valid JSON.

**Step 3: Commit**

```bash
git add data/banned_books.json
git commit -m "feat: add built-in banned/challenged books list from ALA data"
```

---

### Task 6: Add banned books matching function

**Files:**
- Modify: `analyzer.py` (add `flag_banned_books()`)

**Step 1: Add the matching function**

At the end of `analyzer.py`, add:

```python

import json
import os
import re


def _normalize_title(title: str) -> str:
    """Normalize a title for fuzzy matching."""
    if pd.isna(title):
        return ""
    s = str(title).lower().strip()
    # Remove leading articles
    s = re.sub(r"^(the|a|an)\s+", "", s)
    # Remove punctuation
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip()


def _normalize_author(author: str) -> str:
    """Normalize an author name for matching."""
    if pd.isna(author):
        return ""
    s = str(author).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip()


def _load_banned_list() -> list[dict]:
    """Load the built-in banned books list."""
    path = os.path.join(os.path.dirname(__file__), "data", "banned_books.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _load_custom_banned_list() -> list[dict]:
    """Load user-uploaded custom banned list if it exists."""
    path = os.path.join(os.path.dirname(__file__), "uploads", "banned_books_custom.csv")
    if not os.path.exists(path):
        return []
    custom_df = pd.read_csv(path)
    entries = []
    for _, row in custom_df.iterrows():
        entry = {"title": str(row.get("Title", row.get("title", ""))), "source": "Custom upload"}
        if "Author" in custom_df.columns or "author" in custom_df.columns:
            entry["author"] = str(row.get("Author", row.get("author", "")))
        entries.append(entry)
    return entries


def flag_banned_books(df: pd.DataFrame) -> pd.DataFrame:
    """Match catalog items against banned/challenged book lists.

    Returns a DataFrame of matched items with a 'banned_match' column
    containing the source list name.
    """
    banned = _load_banned_list() + _load_custom_banned_list()
    if not banned:
        return pd.DataFrame()

    # Build lookup: normalized_title -> list of {author, source}
    lookup: dict[str, list[dict]] = {}
    for entry in banned:
        norm_title = _normalize_title(entry.get("title", ""))
        if not norm_title:
            continue
        lookup.setdefault(norm_title, []).append({
            "author": _normalize_author(entry.get("author", "")),
            "source": entry.get("source", "Unknown"),
        })

    # Match each catalog item
    results = []
    for idx, row in df.iterrows():
        norm_title = _normalize_title(row.get("title", ""))
        if norm_title not in lookup:
            continue
        for match in lookup[norm_title]:
            # If banned list has author, require author match (substring)
            if match["author"]:
                cat_author = _normalize_author(row.get("author", ""))
                # Check if any part of the banned author appears in catalog author
                author_parts = match["author"].split()
                if not any(part in cat_author for part in author_parts if len(part) > 2):
                    continue
            results.append({**row.to_dict(), "_idx": idx, "banned_match": match["source"]})
            break  # One match per catalog item

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results)
```

**Step 2: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from analyzer import flag_banned_books
df = import_catalog('sample_data/sample_catalog.csv')
matches = flag_banned_books(df)
print(f'Matched: {len(matches)} items')
if len(matches) > 0:
    print(matches[['title', 'author', 'banned_match']].head(10).to_string())
"
```

**Step 3: Commit**

```bash
git add analyzer.py
git commit -m "feat: add banned books matching with normalized title/author comparison"
```

---

### Task 7: Add banned books route and template

**Files:**
- Modify: `app.py` (add `/banned-books` GET route, `POST /banned-books/upload`)
- Create: `templates/banned_books.html`

**Step 1: Add routes to app.py**

In `app.py`, add `flag_banned_books` to the analyzer import:

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
    flag_banned_books,
)
```

Then add routes (after the cost/freshness routes, before the `if __name__` block):

```python

# ---------------------------------------------------------------------------
# Banned / Challenged Books
# ---------------------------------------------------------------------------

@app.route("/banned-books")
def banned_books():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)
    matches = flag_banned_books(df)
    # Audience breakdown of matches
    audience_breakdown = {}
    if len(matches) > 0 and "audience" in matches.columns:
        audience_breakdown = matches["audience"].value_counts().to_dict()
    return render_template(
        "banned_books.html",
        matches=matches.head(500).fillna("").to_dict("records") if len(matches) > 0 else [],
        total_matches=len(matches),
        total_items=len(df),
        audience_breakdown=audience_breakdown,
        audience_filter=audience_filter,
        filename=_current_filename,
    )


@app.route("/banned-books/upload", methods=["POST"])
def upload_banned_list():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Please select a file.", "error")
        return redirect(url_for("banned_books"))
    filepath = os.path.join(UPLOAD_DIR, "banned_books_custom.csv")
    file.save(filepath)
    flash(f"Custom banned books list uploaded from {file.filename}.", "success")
    return redirect(url_for("banned_books"))


@app.route("/export/banned-books")
def export_banned_books():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, _ = _apply_audience_filter(df)
    matches = flag_banned_books(df)
    if len(matches) == 0:
        flash("No banned book matches to export.", "error")
        return redirect(url_for("banned_books"))
    export_cols = ["title", "author", "call_number", "format", "banned_match"]
    if "audience" in matches.columns:
        export_cols.insert(4, "audience")
    if "location" in matches.columns:
        export_cols.insert(5, "location")
    cols = [c for c in export_cols if c in matches.columns]
    return _csv_response(matches[cols].fillna("").to_dict("records"), "banned_challenged_books.csv")
```

**Step 2: Create the template**

Create `templates/banned_books.html`:

```html
{% extends "base.html" %}
{% block title %}Banned/Challenged Books — Collection Analyzer{% endblock %}

{% block content %}
<div class="page-header">
    <h2>Banned &amp; Challenged Books</h2>
    <p>Items in your collection that appear on frequently challenged lists</p>
</div>

{% include "partials/audience_filter.html" %}

<div class="help-box">
    <strong>What is this report for?</strong>
    This report identifies titles in your collection that appear on publicly available
    lists of frequently challenged or banned books (primarily from the American Library
    Association). This is <strong>not a removal list</strong>. It helps you:
    <ul>
        <li>Know what challenged titles you have so you can be prepared if a patron raises concerns</li>
        <li>Support your library's intellectual freedom and collection development policies</li>
        <li>Ensure you have the context to respond to challenges with data</li>
    </ul>
</div>

{% if matches %}
<div class="export-bar">
    <a href="{{ url_for('export_banned_books', audience=audience_filter or '') }}" class="btn-export">Download CSV</a>
</div>

<div class="stat-grid">
    <div class="stat-card">
        <div class="label">Matched Titles</div>
        <div class="value">{{ "{:,}".format(total_matches) }}</div>
        <div class="detail">out of {{ "{:,}".format(total_items) }} items</div>
    </div>
    {% for aud, count in audience_breakdown.items() %}
    <div class="stat-card">
        <div class="label">{{ aud }}</div>
        <div class="value">{{ count }}</div>
        <div class="detail">matched titles</div>
    </div>
    {% endfor %}
</div>

<div class="card">
    <h3>Matched Items</h3>
    <div style="overflow-x: auto;">
    <table>
        <thead>
            <tr>
                <th>Title</th>
                <th>Author</th>
                <th>Call Number</th>
                <th>Format</th>
                {% if matches[0].get('audience') is defined %}<th>Audience</th>{% endif %}
                <th>Source List</th>
            </tr>
        </thead>
        <tbody>
            {% for item in matches %}
            <tr>
                <td>{{ item.title }}</td>
                <td>{{ item.author }}</td>
                <td>{{ item.call_number }}</td>
                <td>{{ item.format }}</td>
                {% if item.get('audience') is defined %}<td>{{ item.audience }}</td>{% endif %}
                <td style="font-size: 12px; color: var(--gray-600);">{{ item.banned_match }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </div>
</div>

{% else %}
<div class="alert alert-info">
    No items in your collection matched the banned/challenged books lists.
    This could mean your collection doesn't include these titles, or the
    matching couldn't find them (matching works on normalized titles).
</div>
{% endif %}

<div class="card">
    <h3>Upload Custom List</h3>
    <p style="color: var(--gray-600); font-size: 14px; margin-bottom: 12px;">
        Have your own list of challenged titles? Upload a CSV with a <strong>Title</strong>
        column (and optionally <strong>Author</strong>). It will be merged with the built-in list.
    </p>
    <form method="POST" action="{{ url_for('upload_banned_list') }}" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv">
        <button type="submit" class="btn btn-sm" style="margin-left: 8px;">Upload</button>
    </form>
</div>
{% endblock %}
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
with open('sample_data/sample_catalog.csv', 'rb') as f:
    client.post('/upload', data={'file': (f, 'sample_catalog.csv')}, content_type='multipart/form-data')
resp = client.get('/banned-books')
print(f'Banned books page: {resp.status_code}')
print(f'Has help box: {b\"intellectual freedom\" in resp.data}')
print(f'Has upload form: {b\"Upload Custom List\" in resp.data}')
"
```

**Step 4: Commit**

```bash
git add app.py templates/banned_books.html
git commit -m "feat: add banned/challenged books report page with custom upload"
```

---

### Task 8: Add banned books to sidebar nav

**Files:**
- Modify: `templates/base.html:36-38` (add nav entry)

**Step 1: Add the nav link**

In `templates/base.html`, after the MUSTIE nav link (line 35), add a new section:

```html

            <div class="section-label">Special</div>
            <a href="{{ url_for('banned_books') }}" class="{% if request.endpoint == 'banned_books' %}active{% endif %}">Banned/Challenged Books</a>
```

**Step 2: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
resp = client.get('/')
print(f'Has Banned nav: {b\"Banned/Challenged\" in resp.data}')
print(f'Has Special section: {b\"Special\" in resp.data}')
"
```

**Step 3: Commit**

```bash
git add templates/base.html
git commit -m "feat: add banned/challenged books to sidebar navigation"
```

---

### Task 9: Add diversity audit analysis function

**Files:**
- Modify: `analyzer.py` (add `diversity_audit()`)

**Step 1: Add the function**

At the end of `analyzer.py`, add:

```python

# Representation keyword categories for diversity audit.
DIVERSITY_CATEGORIES: dict[str, dict] = {
    "LGBTQ+": {
        "keywords": ["gay", "lesbian", "transgender", "queer", "nonbinary",
                     "sexual minorities", "gender identity", "bisexual",
                     "lgbtq", "same-sex", "homosexual"],
        "description": "LGBTQ+ representation",
    },
    "Disability": {
        "keywords": ["disabilities", "deaf", "blind", "autism", "neurodivergent",
                     "accessibility", "mental health", "wheelchair", "adhd",
                     "dyslexia", "chronic illness", "disability"],
        "description": "Disability representation",
    },
    "Cultural/Ethnic": {
        "keywords": ["african american", "latino", "latina", "latinx", "indigenous",
                     "native american", "asian american", "immigration", "multicultural",
                     "hispanic", "black american", "chicano", "pacific islander",
                     "middle eastern", "arab american"],
        "description": "Cultural and ethnic diversity",
    },
    "Languages": {
        "keywords": ["spanish language", "bilingual", "french language",
                     "chinese language", "arabic language", "multilingual",
                     "esl", "english as a second"],
        "description": "Non-English and multilingual materials",
    },
    "Religion": {
        "keywords": ["christianity", "islam", "judaism", "buddhism", "hinduism",
                     "religion", "spiritual", "atheism", "secular", "muslim",
                     "jewish", "christian", "sikh"],
        "description": "Religious and worldview diversity",
    },
}


def diversity_audit(df: pd.DataFrame) -> dict:
    """Audit collection for representation across diversity categories.

    Scans subject headings for representation keywords. This is an
    approximation -- not all diverse books have obvious subject headings.
    """
    if "subject" not in df.columns or df["subject"].isna().all():
        return {"has_data": False, "categories": [], "gaps": []}

    total = len(df)
    categories = []
    gaps = []

    for cat_name, cat_info in DIVERSITY_CATEGORIES.items():
        # Find items matching any keyword in subject field
        pattern = "|".join(re.escape(kw) for kw in cat_info["keywords"])
        mask = df["subject"].fillna("").str.lower().str.contains(pattern, regex=True)
        matched = df[mask]
        count = len(matched)
        pct = round(count / total * 100, 2) if total else 0

        cat_result = {
            "name": cat_name,
            "description": cat_info["description"],
            "count": count,
            "percentage": pct,
            "items": matched.head(50)[
                ["title", "author", "subject", "pub_year", "format"]
                + (["audience"] if "audience" in df.columns else [])
            ].fillna("").to_dict("records"),
        }

        # Audience breakdown if available
        if "audience" in matched.columns and len(matched) > 0:
            cat_result["by_audience"] = matched["audience"].value_counts().to_dict()

        # Freshness: avg pub year
        if matched["pub_year"].notna().any():
            cat_result["avg_pub_year"] = int(matched["pub_year"].mean())

        categories.append(cat_result)

        # Gap detection
        if count == 0:
            gaps.append({"category": cat_name, "description": cat_info["description"],
                         "severity": "none", "message": f"No items found with {cat_name}-related subjects."})
        elif pct < 0.5:
            gaps.append({"category": cat_name, "description": cat_info["description"],
                         "severity": "low", "message": f"Very few items ({count}) with {cat_name}-related subjects."})

        # Per-audience gaps
        if "audience" in df.columns:
            for aud in ["Adult", "YA", "Juvenile"]:
                aud_df = df[df["audience"] == aud]
                if len(aud_df) == 0:
                    continue
                aud_matched = aud_df[aud_df["subject"].fillna("").str.lower().str.contains(pattern, regex=True)]
                if len(aud_matched) == 0:
                    gaps.append({
                        "category": cat_name,
                        "severity": "audience_gap",
                        "message": f"Your {aud} collection has 0 items with {cat_name}-related subjects.",
                    })

    return {
        "has_data": True,
        "total_items": total,
        "categories": categories,
        "gaps": gaps,
    }
```

**Step 2: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from analyzer import diversity_audit
df = import_catalog('sample_data/sample_catalog.csv')
result = diversity_audit(df)
print(f'Has data: {result[\"has_data\"]}')
for cat in result['categories']:
    print(f'{cat[\"name\"]}: {cat[\"count\"]} items ({cat[\"percentage\"]}%)')
print(f'Gaps: {len(result[\"gaps\"])}')
for gap in result['gaps'][:5]:
    print(f'  - {gap[\"message\"]}')
"
```

**Step 3: Commit**

```bash
git add analyzer.py
git commit -m "feat: add diversity audit with subject heading analysis and gap detection"
```

---

### Task 10: Add diversity audit route and template

**Files:**
- Modify: `app.py` (add `/diversity` GET route, export route)
- Create: `templates/diversity.html`

**Step 1: Add routes**

In `app.py`, add `diversity_audit` to the analyzer import:

```python
from analyzer import (
    ...,
    flag_banned_books,
    diversity_audit,
)
```

Add routes:

```python

# ---------------------------------------------------------------------------
# Diversity Audit
# ---------------------------------------------------------------------------

@app.route("/diversity")
def diversity():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)
    result = diversity_audit(df)
    return render_template(
        "diversity.html",
        audit=result,
        audience_filter=audience_filter,
        filename=_current_filename,
    )


@app.route("/export/diversity")
def export_diversity():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, _ = _apply_audience_filter(df)
    result = diversity_audit(df)
    # Flatten all category items into one CSV
    rows = []
    for cat in result.get("categories", []):
        for item in cat.get("items", []):
            rows.append({**item, "diversity_category": cat["name"]})
    if not rows:
        flash("No diversity data to export.", "error")
        return redirect(url_for("diversity"))
    return _csv_response(rows, "diversity_audit.csv")
```

**Step 2: Create the template**

Create `templates/diversity.html`:

```html
{% extends "base.html" %}
{% block title %}Diversity Audit — Collection Analyzer{% endblock %}

{% block content %}
<div class="page-header">
    <h2>Diversity Audit</h2>
    <p>Representation analysis based on subject headings</p>
</div>

{% include "partials/audience_filter.html" %}

<div class="help-box">
    <strong>About this report:</strong>
    This audit scans your catalog's <strong>subject headings</strong> for keywords related
    to diverse representation. It is an <em>approximation</em>, not a definitive count.
    Cataloging practices vary widely, and many books with diverse themes may not have
    obvious subject headings. We recommend supplementing this with curated lists
    (e.g., from We Need Diverse Books or your state library).
    <br><br>
    This report does <strong>not</strong> guess author demographics from names.
</div>

{% if audit.has_data %}

<div class="export-bar">
    <a href="{{ url_for('export_diversity', audience=audience_filter or '') }}" class="btn-export">Download CSV</a>
</div>

{% if audit.gaps %}
<div class="card">
    <h3>Representation Gaps</h3>
    {% for gap in audit.gaps %}
    <div style="padding: 6px 12px; margin-bottom: 6px; border-left: 3px solid {% if gap.severity == 'none' %}#fc8181{% elif gap.severity == 'low' %}#ecc94b{% else %}#4299e1{% endif %}; background: var(--gray-50); border-radius: 0 4px 4px 0; font-size: 13px;">
        {{ gap.message }}
    </div>
    {% endfor %}
</div>
{% endif %}

<div class="stat-grid">
    {% for cat in audit.categories %}
    <div class="stat-card">
        <div class="label">{{ cat.name }}</div>
        <div class="value">{{ cat.count }}</div>
        <div class="detail">
            {{ cat.percentage }}% of collection
            {% if cat.avg_pub_year %} &middot; avg year {{ cat.avg_pub_year }}{% endif %}
        </div>
    </div>
    {% endfor %}
</div>

{% for cat in audit.categories %}
{% if cat.items %}
<div class="card">
    <h3>{{ cat.name }}: {{ cat.description }} ({{ cat.count }} items)</h3>
    {% if cat.by_audience %}
    <p style="font-size: 13px; color: var(--gray-600); margin-bottom: 8px;">
        {% for aud, cnt in cat.by_audience.items() %}{{ aud }}: {{ cnt }}{% if not loop.last %}, {% endif %}{% endfor %}
    </p>
    {% endif %}
    <div style="overflow-x: auto;">
    <table>
        <thead>
            <tr>
                <th>Title</th>
                <th>Author</th>
                <th>Subject</th>
                <th>Year</th>
                <th>Format</th>
            </tr>
        </thead>
        <tbody>
            {% for item in cat.items[:20] %}
            <tr>
                <td>{{ item.title }}</td>
                <td>{{ item.author }}</td>
                <td style="font-size: 12px; max-width: 300px; overflow: hidden; text-overflow: ellipsis;">{{ item.subject }}</td>
                <td>{{ item.pub_year | int if item.pub_year else "" }}</td>
                <td>{{ item.format }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </div>
    {% if cat.count > 20 %}
    <p style="font-size: 12px; color: var(--gray-600); margin-top: 8px;">Showing 20 of {{ cat.count }}. Download CSV for the full list.</p>
    {% endif %}
</div>
{% endif %}
{% endfor %}

{% else %}
<div class="alert alert-info">
    No subject heading data found. The diversity audit requires a <strong>Subject</strong>
    column in your catalog export.
</div>
{% endif %}
{% endblock %}
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
with open('sample_data/sample_catalog.csv', 'rb') as f:
    client.post('/upload', data={'file': (f, 'sample_catalog.csv')}, content_type='multipart/form-data')
resp = client.get('/diversity')
print(f'Diversity page: {resp.status_code}')
print(f'Has help box: {b\"approximation\" in resp.data}')
print(f'Has categories: {b\"LGBTQ\" in resp.data or b\"Disability\" in resp.data}')
"
```

**Step 4: Commit**

```bash
git add app.py templates/diversity.html
git commit -m "feat: add diversity audit report page with gap detection"
```

---

### Task 11: Add diversity audit to sidebar nav

**Files:**
- Modify: `templates/base.html` (add nav entry in Analysis section)

**Step 1: Add the nav link**

In `templates/base.html`, after the "Cost & ROI" nav link (line 29), add:

```html
            <a href="{{ url_for('diversity') }}" class="{% if request.endpoint == 'diversity' %}active{% endif %}">Diversity Audit</a>
```

**Step 2: Verify and commit**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
resp = client.get('/')
print(f'Has Diversity nav: {b\"Diversity Audit\" in resp.data}')
"
```

```bash
git add templates/base.html
git commit -m "feat: add diversity audit to sidebar navigation"
```

---

### Task 12: Add Dewey tens and hundreds lookup tables

**Files:**
- Create: `dewey_tables.py`

**Step 1: Create the lookup tables**

Create `dewey_tables.py` with tens-level (~100 entries) and hundreds-level labels:

```python
"""Dewey Decimal Classification lookup tables."""

# Tens-level labels (divisions, ~100 entries)
DEWEY_TENS_LABELS: dict[str, str] = {
    "000": "Computer Science & Information",
    "010": "Bibliographies",
    "020": "Library & Information Science",
    "030": "Encyclopedias & General Reference",
    "040": "Unassigned",
    "050": "Magazines, Journals & Serials",
    "060": "Associations, Organizations & Museums",
    "070": "News Media, Journalism & Publishing",
    "080": "General Collections & Anthologies",
    "090": "Manuscripts & Rare Books",
    "100": "Philosophy",
    "110": "Metaphysics",
    "120": "Epistemology & Causation",
    "130": "Parapsychology & Occultism",
    "140": "Philosophical Schools of Thought",
    "150": "Psychology",
    "160": "Logic",
    "170": "Ethics",
    "180": "Ancient, Medieval & Eastern Philosophy",
    "190": "Modern Western Philosophy",
    "200": "Religion",
    "210": "Philosophy of Religion",
    "220": "The Bible",
    "230": "Christianity & Christian Theology",
    "240": "Christian Practice & Observance",
    "250": "Christian Pastoral Practice",
    "260": "Christian Organization & Social Work",
    "270": "History of Christianity",
    "280": "Christian Denominations",
    "290": "Other Religions",
    "300": "Social Sciences",
    "310": "Statistics",
    "320": "Political Science",
    "330": "Economics",
    "340": "Law",
    "350": "Public Administration & Military",
    "360": "Social Problems & Services",
    "370": "Education",
    "380": "Commerce, Communications & Transportation",
    "390": "Customs, Etiquette & Folklore",
    "400": "Language",
    "410": "Linguistics",
    "420": "English & Old English",
    "430": "German & Related Languages",
    "440": "French & Related Languages",
    "450": "Italian, Romanian & Related",
    "460": "Spanish & Portuguese",
    "470": "Latin",
    "480": "Classical Greek",
    "490": "Other Languages",
    "500": "Science",
    "510": "Mathematics",
    "520": "Astronomy",
    "530": "Physics",
    "540": "Chemistry",
    "550": "Earth Sciences & Geology",
    "560": "Fossils & Prehistoric Life",
    "570": "Biology & Life Sciences",
    "580": "Plants (Botany)",
    "590": "Animals (Zoology)",
    "600": "Technology",
    "610": "Medicine & Health",
    "620": "Engineering",
    "630": "Agriculture",
    "640": "Home & Family Management",
    "650": "Management & Public Relations",
    "660": "Chemical Engineering",
    "670": "Manufacturing",
    "680": "Specific Manufactured Products",
    "690": "Building & Construction",
    "700": "Arts & Recreation",
    "710": "Landscape & Area Planning",
    "720": "Architecture",
    "730": "Sculpture, Ceramics & Metalwork",
    "740": "Drawing & Decorative Arts",
    "750": "Painting",
    "760": "Printmaking & Graphic Arts",
    "770": "Photography & Computer Art",
    "780": "Music",
    "790": "Sports, Games & Entertainment",
    "800": "Literature",
    "810": "American Literature in English",
    "820": "English & Old English Literature",
    "830": "German Literature",
    "840": "French Literature",
    "850": "Italian Literature",
    "860": "Spanish & Portuguese Literature",
    "870": "Latin Literature",
    "880": "Classical Greek Literature",
    "890": "Other Literatures",
    "900": "History & Geography",
    "910": "Geography & Travel",
    "920": "Biography & Genealogy",
    "930": "Ancient World History",
    "940": "European History",
    "950": "Asian History",
    "960": "African History",
    "970": "North American History",
    "980": "South American History",
    "990": "History of Other Areas",
}

# Hundreds-level labels (sections, subset of most common)
DEWEY_HUNDREDS_LABELS: dict[str, str] = {
    "001": "Knowledge",
    "004": "Computer Science",
    "005": "Computer Programming",
    "006": "Special Computer Methods",
    "011": "Bibliographies & Catalogs",
    "016": "Bibliographies of Specific Subjects",
    "020": "Library & Information Science",
    "025": "Library Operations",
    "027": "General Libraries",
    "030": "Encyclopedias",
    "070": "News Media & Journalism",
    "100": "Philosophy",
    "150": "Psychology",
    "152": "Perception & Emotions",
    "153": "Mental Processes & Intelligence",
    "155": "Differential Psychology",
    "158": "Applied Psychology",
    "170": "Ethics",
    "200": "Religion",
    "220": "The Bible",
    "230": "Christian Theology",
    "290": "Other Religions",
    "291": "Comparative Religion",
    "296": "Judaism",
    "297": "Islam",
    "300": "Social Sciences",
    "301": "Sociology & Anthropology",
    "302": "Social Interaction",
    "305": "Social Groups",
    "306": "Culture & Institutions",
    "320": "Political Science",
    "323": "Civil & Political Rights",
    "327": "International Relations",
    "330": "Economics",
    "331": "Labor Economics",
    "332": "Financial Economics",
    "338": "Production",
    "340": "Law",
    "345": "Criminal Law",
    "347": "Civil Procedure & Courts",
    "355": "Military Science",
    "360": "Social Problems & Services",
    "361": "Social Problems & Social Welfare",
    "362": "Social Welfare & Social Work",
    "363": "Other Social Problems",
    "364": "Criminology",
    "370": "Education",
    "371": "Schools & Teaching",
    "372": "Elementary Education",
    "373": "Secondary Education",
    "380": "Commerce & Communications",
    "384": "Communications & Telecommunication",
    "390": "Customs & Folklore",
    "398": "Folklore",
    "400": "Language",
    "410": "Linguistics",
    "420": "English",
    "428": "Standard English Usage",
    "460": "Spanish",
    "500": "Science",
    "510": "Mathematics",
    "512": "Algebra",
    "516": "Geometry",
    "520": "Astronomy",
    "530": "Physics",
    "540": "Chemistry",
    "550": "Earth Sciences",
    "560": "Paleontology",
    "570": "Biology",
    "571": "Physiology",
    "572": "Biochemistry",
    "573": "Specific Physiological Systems",
    "576": "Genetics",
    "577": "Ecology",
    "580": "Botany",
    "590": "Zoology",
    "591": "Zoology (Specific Topics)",
    "599": "Mammals",
    "600": "Technology",
    "610": "Medicine & Health",
    "611": "Human Anatomy",
    "612": "Human Physiology",
    "613": "Personal Health & Safety",
    "614": "Public Health",
    "615": "Pharmacology & Therapeutics",
    "616": "Diseases",
    "617": "Surgery",
    "618": "Gynecology, Obstetrics & Pediatrics",
    "620": "Engineering",
    "621": "Applied Physics",
    "623": "Military Engineering",
    "624": "Civil Engineering",
    "625": "Railroads & Roads",
    "629": "Automotive & Aeronautical Engineering",
    "630": "Agriculture",
    "635": "Garden Crops (Horticulture)",
    "636": "Animal Husbandry",
    "640": "Home & Family Management",
    "641": "Food & Drink",
    "646": "Sewing & Clothing",
    "649": "Child Rearing",
    "650": "Management & Business",
    "658": "General Management",
    "660": "Chemical Engineering",
    "670": "Manufacturing",
    "690": "Building & Construction",
    "700": "Arts",
    "709": "Art History",
    "720": "Architecture",
    "730": "Sculpture",
    "740": "Drawing & Decorative Arts",
    "741": "Drawing & Illustration",
    "745": "Decorative Arts",
    "746": "Textile Arts & Handicrafts",
    "750": "Painting",
    "770": "Photography",
    "780": "Music",
    "784": "Instruments & Ensembles",
    "790": "Recreation & Performing Arts",
    "791": "Public Performances",
    "792": "Stage Presentations & Theater",
    "793": "Indoor Games & Amusements",
    "796": "Athletic & Outdoor Sports",
    "800": "Literature",
    "808": "Rhetoric & Writing",
    "810": "American Literature",
    "811": "American Poetry",
    "812": "American Drama",
    "813": "American Fiction",
    "814": "American Essays",
    "820": "English Literature",
    "821": "English Poetry",
    "822": "English Drama",
    "823": "English Fiction",
    "839": "Germanic Literatures",
    "860": "Spanish Literature",
    "870": "Latin Literature",
    "880": "Greek Literature",
    "900": "History & Geography",
    "910": "Geography & Travel",
    "914": "Europe (Geography)",
    "917": "North America (Geography)",
    "920": "Biography",
    "930": "Ancient World History",
    "940": "European History",
    "941": "British Isles History",
    "943": "German History",
    "944": "French History",
    "945": "Italian History",
    "950": "Asian History",
    "951": "Chinese History",
    "952": "Japanese History",
    "960": "African History",
    "970": "North American History",
    "971": "Canadian History",
    "972": "Mexican & Central American History",
    "973": "United States History",
    "974": "Northeastern US History",
    "975": "Southeastern US History",
    "976": "South Central US History",
    "977": "North Central US History",
    "978": "Western US History",
    "979": "Great Basin & Pacific Coast US History",
    "980": "South American History",
    "990": "History of Other Areas",
    "994": "Australian History",
}
```

**Step 2: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from dewey_tables import DEWEY_TENS_LABELS, DEWEY_HUNDREDS_LABELS
print(f'Tens entries: {len(DEWEY_TENS_LABELS)}')
print(f'Hundreds entries: {len(DEWEY_HUNDREDS_LABELS)}')
print(f'510 = {DEWEY_TENS_LABELS[\"510\"]}')
print(f'512 = {DEWEY_HUNDREDS_LABELS[\"512\"]}')
print(f'973 = {DEWEY_HUNDREDS_LABELS[\"973\"]}')
"
```

**Step 3: Commit**

```bash
git add dewey_tables.py
git commit -m "feat: add Dewey Decimal tens and hundreds level lookup tables"
```

---

### Task 13: Refactor importer to detect classification system and extract Dewey fields

**Files:**
- Modify: `importer.py:163-202` (refactor `extract_lc_class` to also return Dewey data)
- Modify: `importer.py:241-250` (add new columns in `import_catalog`)

**Step 1: Add new extraction function**

In `importer.py`, after the existing `extract_lc_class` function, add:

```python

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
        # Extract digits before any dot or space
        digits = ""
        for ch in s:
            if ch.isdigit():
                digits += ch
            elif ch == ".":
                break
            elif ch == " ":
                break
            else:
                break
        if len(digits) >= 3:
            dewey_class = digits[:3]
            dewey_tens = digits[:2] + "0"
            # Also provide LC crosswalk for backward compatibility
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
```

**Step 2: Update import_catalog to use new function**

In `import_catalog()`, replace the single `lc_class` line:

```python
    df["lc_class"] = df["call_number"].apply(extract_lc_class)
```

with:

```python
    # Extract classification system and all class fields
    classification = df["call_number"].apply(extract_classification)
    class_df = pd.DataFrame(classification.tolist(), index=df.index)
    df["classification_system"] = class_df["classification_system"]
    df["lc_class"] = class_df["lc_class"]
    df["dewey_class"] = class_df["dewey_class"]
    df["dewey_tens"] = class_df["dewey_tens"]
```

**Step 3: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
df = import_catalog('sample_data/sample_catalog.csv')
print(f'Columns: classification_system={\"classification_system\" in df.columns}, dewey_class={\"dewey_class\" in df.columns}, dewey_tens={\"dewey_tens\" in df.columns}')
print(f'Classification systems: {df[\"classification_system\"].value_counts().to_dict()}')
# Check that LC items still work
lc_items = df[df[\"classification_system\"] == \"LC\"]
if len(lc_items) > 0:
    print(f'LC sample: {lc_items[[\"call_number\", \"lc_class\"]].head(3).to_string()}')
dewey_items = df[df[\"classification_system\"] == \"Dewey\"]
if len(dewey_items) > 0:
    print(f'Dewey sample: {dewey_items[[\"call_number\", \"dewey_class\", \"dewey_tens\"]].head(3).to_string()}')
# Verify all existing analyses still work
from analyzer import collection_summary, subject_balance, find_gaps, collection_freshness
s = collection_summary(df)
print(f'Summary works: total_items={s[\"total_items\"]}')
bal = subject_balance(df)
print(f'Subject balance works: {len(bal)} classes')
gaps = find_gaps(df)
print(f'Gaps works: {len(gaps)} gap types')
fresh = collection_freshness(df)
print(f'Freshness works: {len(fresh)} classes')
"
```

This is CRITICAL: all existing analyses must still work since they use `lc_class` which is still populated (via the Dewey-to-LC crosswalk).

**Step 4: Commit**

```bash
git add importer.py
git commit -m "feat: add Dewey classification detection with dewey_class and dewey_tens columns"
```

---

### Task 14: Add Dewey subject grouping to analyzer

**Files:**
- Modify: `analyzer.py` (add `dewey_subject_balance` function)

**Step 1: Add the function**

In `analyzer.py`, add the import at the top:

```python
from dewey_tables import DEWEY_TENS_LABELS, DEWEY_HUNDREDS_LABELS
```

Then add after `subject_balance()`:

```python

def dewey_subject_balance(df: pd.DataFrame) -> dict:
    """Subject balance for Dewey-classified items at tens and hundreds level.

    Returns a dict with:
        dominant_system: "LC", "Dewey", or "Mixed"
        dewey_tens: list of dicts (tens-level grouping)
        dewey_hundreds: dict mapping tens_code -> list of hundreds-level dicts
    """
    result = {"dominant_system": "LC", "dewey_tens": [], "dewey_hundreds": {}}

    if "classification_system" not in df.columns:
        return result

    lc_count = int((df["classification_system"] == "LC").sum())
    dewey_count = int((df["classification_system"] == "Dewey").sum())
    total = lc_count + dewey_count

    if total == 0:
        return result

    if dewey_count > lc_count:
        result["dominant_system"] = "Dewey"
    elif dewey_count > 0 and lc_count > 0:
        result["dominant_system"] = "Mixed"

    if dewey_count == 0:
        return result

    # Tens-level grouping
    dewey_df = df[df["dewey_tens"].notna()].copy()
    if len(dewey_df) == 0:
        return result

    tens_grouped = (
        dewey_df.groupby("dewey_tens")
        .agg(count=("title", "size"), avg_checkouts=("checkouts", "mean"))
        .reset_index()
    )
    tens_total = len(dewey_df)
    tens_grouped["percentage"] = (tens_grouped["count"] / tens_total * 100).round(1)
    tens_grouped["avg_checkouts"] = tens_grouped["avg_checkouts"].round(1)
    tens_grouped["label"] = tens_grouped["dewey_tens"].map(
        lambda x: DEWEY_TENS_LABELS.get(x, "Unknown")
    )
    result["dewey_tens"] = tens_grouped.sort_values("count", ascending=False).to_dict("records")

    # Hundreds-level detail per tens group
    hundreds_df = dewey_df[dewey_df["dewey_class"].notna()].copy()
    if len(hundreds_df) > 0:
        for tens_code in tens_grouped["dewey_tens"]:
            subset = hundreds_df[hundreds_df["dewey_tens"] == tens_code]
            if len(subset) == 0:
                continue
            h_grouped = (
                subset.groupby("dewey_class")
                .agg(count=("title", "size"), avg_checkouts=("checkouts", "mean"))
                .reset_index()
            )
            h_grouped["avg_checkouts"] = h_grouped["avg_checkouts"].round(1)
            h_grouped["label"] = h_grouped["dewey_class"].map(
                lambda x: DEWEY_HUNDREDS_LABELS.get(x, DEWEY_TENS_LABELS.get(x, "Unknown"))
            )
            result["dewey_hundreds"][tens_code] = h_grouped.sort_values("count", ascending=False).to_dict("records")

    return result
```

**Step 2: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from importer import import_catalog
from analyzer import dewey_subject_balance
df = import_catalog('sample_data/sample_catalog.csv')
result = dewey_subject_balance(df)
print(f'Dominant system: {result[\"dominant_system\"]}')
print(f'Dewey tens groups: {len(result[\"dewey_tens\"])}')
if result['dewey_tens']:
    print(f'Top tens: {result[\"dewey_tens\"][:3]}')
print(f'Hundreds detail groups: {len(result[\"dewey_hundreds\"])}')
"
```

**Step 3: Commit**

```bash
git add analyzer.py
git commit -m "feat: add Dewey subject balance with tens/hundreds grouping"
```

---

### Task 15: Display Dewey groupings on subject balance page

**Files:**
- Modify: `app.py` (update subjects route to pass Dewey data)
- Modify: `templates/subjects.html` (add Dewey section with drill-down)
- Create: `static/js/drilldown.js`

**Step 1: Update the subjects route**

In `app.py`, add `dewey_subject_balance` to the analyzer import and update the `subjects()` route:

```python
@app.route("/subjects")
def subjects():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)
    balance = subject_balance(df)
    dewey = dewey_subject_balance(df)
    return render_template(
        "subjects.html",
        subjects=balance,
        dewey=dewey,
        audience_filter=audience_filter,
        filename=_current_filename,
    )
```

**Step 2: Create drilldown.js**

Create `static/js/drilldown.js`:

```javascript
/**
 * Expand/collapse Dewey hundreds-level drill-down rows.
 */
document.addEventListener('click', function(e) {
    var toggle = e.target.closest('.dewey-toggle');
    if (!toggle) return;
    var tens = toggle.dataset.tens;
    var rows = document.querySelectorAll('.dewey-hundreds-' + tens);
    var expanded = toggle.classList.toggle('expanded');
    rows.forEach(function(row) {
        row.style.display = expanded ? '' : 'none';
    });
    toggle.querySelector('.toggle-arrow').textContent = expanded ? '\u25BC' : '\u25B6';
});
```

**Step 3: Add Dewey section to subjects template**

In `templates/subjects.html`, after the existing detail table card (after line 68, before `{% else %}`), add:

```html

{% if dewey and dewey.dewey_tens %}
<div class="card">
    <h3>Dewey Decimal Breakdown</h3>
    <p style="color: var(--gray-600); font-size: 13px; margin-bottom: 12px;">
        {% if dewey.dominant_system == 'Dewey' %}Your collection primarily uses Dewey Decimal classification.
        {% elif dewey.dominant_system == 'Mixed' %}Your collection uses both LC and Dewey classification. Dewey items shown below.
        {% else %}Most items use LC classification. Dewey items shown below.{% endif %}
        Click a row to see hundreds-level detail.
    </p>
    <div style="overflow-x: auto;">
    <table>
        <thead>
            <tr>
                <th></th>
                <th>Class</th>
                <th>Subject</th>
                <th>Items</th>
                <th>% of Dewey</th>
                <th>Avg Checkouts</th>
            </tr>
        </thead>
        <tbody>
            {% for t in dewey.dewey_tens %}
            <tr class="dewey-toggle" data-tens="{{ t.dewey_tens }}" style="cursor: pointer;">
                <td><span class="toggle-arrow" style="font-size: 11px; color: var(--gray-600);">&#9654;</span></td>
                <td><strong>{{ t.dewey_tens }}</strong></td>
                <td>{{ t.label }}</td>
                <td>{{ t.count }}</td>
                <td>{{ t.percentage }}%</td>
                <td>{{ t.avg_checkouts }}</td>
            </tr>
            {% if dewey.dewey_hundreds.get(t.dewey_tens) %}
            {% for h in dewey.dewey_hundreds[t.dewey_tens] %}
            <tr class="dewey-hundreds-{{ t.dewey_tens }}" style="display: none; background: var(--gray-50);">
                <td></td>
                <td style="padding-left: 24px; font-size: 13px;">{{ h.dewey_class }}</td>
                <td style="font-size: 13px;">{{ h.label }}</td>
                <td style="font-size: 13px;">{{ h.count }}</td>
                <td style="font-size: 13px;"></td>
                <td style="font-size: 13px;">{{ h.avg_checkouts }}</td>
            </tr>
            {% endfor %}
            {% endif %}
            {% endfor %}
        </tbody>
    </table>
    </div>
</div>
{% endif %}
```

**Step 4: Include drilldown.js in base.html**

In `templates/base.html`, after the inline-edit.js script tag, add:

```html
    <script src="{{ url_for('static', filename='js/drilldown.js') }}" defer></script>
```

**Step 5: Verify**

```bash
cd /Users/sam/Projects/cat && source venv/bin/activate && python3 -c "
from app import app
client = app.test_client()
with open('sample_data/sample_catalog.csv', 'rb') as f:
    client.post('/upload', data={'file': (f, 'sample_catalog.csv')}, content_type='multipart/form-data')
resp = client.get('/subjects')
print(f'Subjects page: {resp.status_code}')
print(f'Has Dewey section: {b\"Dewey Decimal Breakdown\" in resp.data}')
print(f'Has drilldown JS: {b\"drilldown.js\" in resp.data}')
"
```

**Step 6: Commit**

```bash
git add app.py templates/subjects.html static/js/drilldown.js templates/base.html
git commit -m "feat: add Dewey classification drill-down to subject balance page"
```

---
