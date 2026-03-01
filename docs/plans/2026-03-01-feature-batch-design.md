# CAT Feature Batch Design

## Overview

11 features for the Library Collection Analyzer, grouped into data features, new analysis pages, and UX improvements. All features use the existing stack (Python/Flask, Jinja2, vanilla JS, CSS). No new dependencies.

This document covers everything agreed upon in the brainstorming session. The earlier design for Import Templates + Last Upload Persistence (in `2026-03-01-import-templates-and-persistence-design.md`) is included here as Features 1-2 for completeness.

---

## Feature 1: Import Templates

### Files
- Create: `sample_data/template_blank.csv`
- Create: `sample_data/template_example.csv`
- Modify: `app.py` (add `/download-template/<name>` route)
- Modify: `templates/upload.html` (add download buttons)

### Details
- `template_blank.csv`: header row only, all 16 canonical columns using human-readable names (Title, Author, ISBN, Call Number, Publication Year, Subject, Format, Location, Barcode, Checkouts, Last Checkout Date, Date Added, Status, Price, Collection, Copies)
- `template_example.csv`: same headers + 5 rows covering Book, CD, DVD, Audiobook across different subjects, locations, and circulation levels
- Route serves files from `sample_data/` via `send_file` with allowlist validation (only the two template files)
- Upload page gets a "Templates" card between the help box and upload form with two download buttons

---

## Feature 2: Last Upload Persistence

### Files
- Modify: `app.py` (add `_save_last_upload()`, `_check_last_upload()`, `POST /reload` route)
- Modify: `templates/index.html` (add reload banner)
- Modify: `.gitignore` (add `uploads/.last_upload.json`)

### Details
- On successful upload, write `uploads/.last_upload.json` with `{"filename", "uploaded_at", "row_count"}`
- On dashboard load with no data, check if JSON exists and referenced file is still on disk
- If yes, show banner: "Your last dataset (filename, N items) is still available. [Reload it]"
- `POST /reload` re-imports the file through existing `import_catalog()` pipeline
- Edge cases: JSON exists but file deleted = no banner. New upload overwrites JSON.

---

## Feature 3: MUSTIE Settings -- Full Flexibility

### Files
- Modify: `mustie.py` (add `circ_floor` to `DEFAULT_CREW_THRESHOLDS`, update `apply_mustie()`)
- Modify: `app.py` (update `mustie_settings` POST handler)
- Modify: `templates/mustie_settings.html` (add columns for max_no_circ_years and circ_floor)

### Details
- Add `circ_floor` field to `DEFAULT_CREW_THRESHOLDS` with per-subject defaults (2 for most, 1 for Literature/Arts/History)
- Expose `max_no_circ_years` (already in data structure, not in UI) as an editable column in settings
- Expose per-subject `circ_floor` as an editable column
- Update `apply_mustie()` to read per-subject `circ_floor` and `max_no_circ_years` from thresholds instead of using global values
- Settings form POST handler reads `no_circ_years_X` and `circ_floor_X` fields

---

## Feature 4: Digital Format Support

### Files
- Modify: `importer.py` (add `DIGITAL_FORMATS` set, add `is_digital` column)
- Modify: `mustie.py` (filter out digital items)
- Modify: `analyzer.py` (filter out digital from `weeding_candidates()`)
- Modify: `templates/formats.html` (add digital vs physical summary)

### Details
- `DIGITAL_FORMATS` set (case-insensitive matching): eBook, E-Book, Digital, Online Resource, eAudiobook, E-Audiobook, Streaming Video, Streaming Audio, Database, Electronic, Hoopla, Libby, Kanopy, Axis 360, cloudLibrary
- Add `is_digital` boolean column during `import_catalog()`
- Exclude `is_digital=True` from MUSTIE and weeding analysis (can't physically weed digital items)
- Format breakdown page gets a digital vs physical summary section at top: count, percentage, avg checkouts for each

---

## Feature 5: Cost-per-circ + In-app Price Editing

### Files
- Modify: `analyzer.py` (add `cost_per_circ` to weeding/MUSTIE output)
- Modify: `app.py` (add `POST /edit-item` route)
- Create: `static/js/inline-edit.js`
- Modify: `templates/mustie.html`, `templates/weeding.html`, `templates/dormant.html` (add cost-per-circ column, inline edit)
- Modify: `templates/base.html` (include inline-edit.js)

### Details

**Cost-per-circ:** `price / checkouts`, null if no price or zero checkouts. Added as a computed column in weeding, MUSTIE, and dormant item outputs. Displayed in those tables.

**Inline price editing:**
- `POST /edit-item` accepts `{index, field, value}`, updates in-memory DataFrame. Field restricted to `price` only.
- `inline-edit.js`: clicking a price cell turns it into an `<input>`. On blur/enter, POSTs to `/edit-item`, updates cell display.
- Edits live in memory only. Included in CSV exports ("Download Full Catalog CSV"). Not persisted to original file.
- UI note on pages with editable prices: "Price edits are included in CSV exports but not saved to the original file."

---

## Feature 6: Nonfiction Dewey Ranges (Hundreds Level with Drill-down)

### Files
- Modify: `importer.py` (add `DEWEY_TENS_LABELS`, `DEWEY_HUNDREDS_LABELS`, add `dewey_class`/`dewey_tens`/`classification_system` columns, refactor `extract_lc_class()`)
- Modify: `analyzer.py` (update all grouping functions to handle dual classification)
- Modify: all report templates that show subject groupings (subjects, gaps, freshness, MUSTIE summary)
- Create: `static/js/drilldown.js`

### Details

**Data model:**
- `classification_system`: `"LC"`, `"Dewey"`, or `None`
- `lc_class`: existing column, populated only for LC items
- `dewey_class`: 3-digit Dewey class (e.g., "512"), populated only for Dewey items
- `dewey_tens`: tens grouping (e.g., "510"), for collapsed view
- Keep existing Dewey-to-LC crosswalk as fallback

**Lookup tables:**
- `DEWEY_TENS_LABELS`: ~100 entries ("510": "Mathematics")
- `DEWEY_HUNDREDS_LABELS`: ~1000 entries ("512": "Algebra", "516": "Geometry")

**Display:** Reports auto-detect which system dominates the collection. Primary grouping uses the dominant system. If both are present, show both sections. Dewey sections show tens-level by default with expandable drill-down to hundreds level via toggle arrow (JS + CSS, no server round-trip).

**CSV exports:** Include full hundreds-level detail.

---

## Feature 7: Kids vs Adult Segmentation

### Files
- Modify: `importer.py` (add `audience` column derivation)
- Modify: `app.py` (add audience filter param to all report routes)
- Modify: `templates/index.html` (add audience breakdown stats)
- Modify: all report templates (add audience filter dropdown)
- Modify: `templates/base.html` or create partial (reusable filter bar)

### Details

**Derived column:** `audience` with values `Adult`, `YA`, `Juvenile`, `Unknown`. Fallback chain:
1. `collection` field keywords (case-insensitive, substring): "juvenile"/"children"/"kids"/"j "/"juv" -> Juvenile. "ya"/"young adult"/"teen" -> YA. "adult" -> Adult.
2. If no match, check `location` field with same keywords.
3. No match -> Unknown.

**Filter:** Every report route accepts `?audience=YA` (or Adult, Juvenile). When present, filters the DataFrame before analysis. Dashboard shows audience breakdown stats. All report pages get a filter dropdown at top that reloads with the query param.

---

## Feature 8: Banned Books Flagging

### Files
- Create: `data/banned_books.json` (built-in ALA list, ~200-300 entries)
- Modify: `analyzer.py` (add `flag_banned_books()`)
- Modify: `app.py` (add `/banned-books` GET route, `POST /banned-books/upload` route)
- Create: `templates/banned_books.html`

### Details

**Built-in list:** JSON array of `{"title", "author", "source"}` from ALA's publicly available frequently challenged lists.

**Custom upload:** `POST /banned-books/upload` accepts CSV with Title column (Author optional). Saved to `uploads/banned_books_custom.csv`. Merged with built-in list; custom entries take priority on duplicates.

**Matching:** Fuzzy normalized comparison -- lowercase, strip punctuation, remove leading articles ("the", "a", "an"). If author available in banned list, require both title + author match. Returns DataFrame with `banned_match` column (source string or null).

**Report page:**
- Summary: X items in your collection appear on challenged/banned lists
- Table: Title, Author, Call Number, Format, Audience, Location, Source List
- Audience breakdown (ties into Feature 7)
- Export CSV

**Framing:** Help box explicitly states this report helps libraries know what they have, prepare for challenges, and support intellectual freedom policies. NOT a removal list.

---

## Feature 9: Diversity Audit

### Files
- Modify: `analyzer.py` (add `diversity_audit()`)
- Modify: `app.py` (add `/diversity` GET route)
- Create: `templates/diversity.html`

### Details

**Subject heading analysis:** Scan `subject` field for representation keywords across categories:
- **LGBTQ+:** gay, lesbian, transgender, queer, nonbinary, sexual minorities, gender identity
- **Disability:** disabilities, deaf, blind, autism, neurodivergent, accessibility, mental health
- **Cultural/ethnic:** African American, Latino, Indigenous, Native American, Asian American, immigration, multicultural
- **Languages:** non-English materials detected from subject headings ("Spanish language", "bilingual") or language column if present
- **Religion/worldview:** coverage across major religions and secular perspectives

Each category returns: item count, percentage of collection, breakdown by audience (from Feature 7), freshness (avg pub year).

**Representation gaps:** Flag categories with zero or very few items, broken down by audience. "Your Juvenile collection has 0 items with disability-related subjects."

**Report page:** Summary cards per category, gap alerts, item table per category, CSV export.

**Framing:** Help box notes this is an approximation based on subject headings. Cataloging practices vary. Not all diverse books have obvious subject headings. Recommend supplementing with curated lists. No author demographic guessing.

---

## Feature 10: Mobile + Neurodivergent-Friendly UX

### Files
- Modify: `static/css/style.css` (responsive breakpoints, touch targets, reduced motion)
- Modify: `templates/base.html` (hamburger toggle, sidebar overlay)
- Create: `static/js/sidebar.js`
- Modify: all templates with help boxes (add collapsible pattern)
- Create: `static/js/help-toggle.js`

### Details

**Responsive layout:**
- `@media (max-width: 768px)`: sidebar hidden by default, hamburger toggle in top bar, main-content full-width with 16px padding, stat-grid single column, tables get `overflow-x: auto` with sticky first column
- `@media (max-width: 480px)`: stat values shrink to 22px, upload area padding reduces

**Touch targets:** All nav links, buttons, form inputs minimum 44px height on mobile.

**Reduced motion:**
```css
@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
}
```

**Collapsible help boxes:** Show first sentence + "Read more" toggle. Expanded on first visit, collapsed on repeat visits (localStorage). Small JS in `help-toggle.js`.

**Color-only indicators:** Add text labels next to column status dots ("Full", "Partial", "Empty"). Gap badges and MUSTIE badges already have text.

**Sidebar toggle:** `sidebar.js` -- hamburger button visible on mobile, toggles `.sidebar-open` class, overlay behind sidebar, tap overlay to close.

---

## Feature 11: Plain Language + New Librarian Friendly

### Files
- Modify: `static/css/style.css` (tooltip styles)
- Modify: all report templates (rewrite help boxes, add tooltips, add "why this matters")

### Details

**Jargon tooltips:** CSS `.tooltip` class with dotted underline + hover/tap popup. First occurrence per page of: LC Classification, CREW method, MUSTIE, weeding, circ/circulation, ILS, call number, Dewey Decimal, deselection.

**Help box rewrites:** Replace library-jargon explanations with plain language versions understandable by a first-semester MLIS student. Example:
- Before: "MUSTIE is a framework from the CREW method (Continuous Review, Evaluation, and Weeding) used by libraries nationwide"
- After: "MUSTIE is a checklist for deciding which items to remove from your shelves. Each letter stands for a different reason a book might need to go. Most public libraries use some version of this."

**"Why does this matter?" lines:** Each report help box gets a one-sentence plain-language purpose:
- Collection Gaps: "Shows you where your shelves are thin so you know what to buy next."
- Weeding: "Helps you find items taking up shelf space that nobody's using."
- Freshness: "Tells you which subject areas are getting stale and need newer materials."
- Diversity: "Checks whether your collection represents the community you serve."
- Banned Books: "Shows which frequently challenged titles are in your collection so you can be prepared."
- Subject Balance: "Tells you if your collection leans too heavily toward one subject and has gaps in others."
- Usage Analysis: "Shows what your community is actually reading and using."
- Cost & ROI: "Helps you see where your budget is going and what's getting the most use per dollar."

**Step numbers:** Extend the existing step-number pattern from Getting Started to MUSTIE settings, upload, and banned books upload pages.

---

## Implementation Order

Recommended sequence (dependencies flow downward):

1. **Import Templates** (no dependencies)
2. **Last Upload Persistence** (no dependencies)
3. **Digital Format Support** (modifies importer -- do before Dewey changes)
4. **Dewey Ranges** (major importer refactor)
5. **Kids vs Adult Segmentation** (needs importer done)
6. **MUSTIE Settings** (independent but benefits from digital exclusion)
7. **Cost-per-circ + Price Editing** (needs stable data model)
8. **Banned Books Flagging** (needs audience column from #5)
9. **Diversity Audit** (needs audience column from #5)
10. **Mobile + ND-Friendly UX** (can happen anytime, but better after all pages exist)
11. **Plain Language** (last -- rewrite help text after all features are built)

## Nav Structure

Updated sidebar with new pages:

```
Dashboard
Getting Started
Import Data

-- Analysis --
Collection Gaps
Subject Balance
Freshness
Age Distribution
Format Breakdown
Duplicates
Cost & ROI
Diversity Audit        [NEW]

-- Circulation --
Usage Analysis
Dormant Items
Weeding (Simple)
Weeding (MUSTIE)

-- Special --
Banned/Challenged Books [NEW]

-- Data --
Column Mapping
```
