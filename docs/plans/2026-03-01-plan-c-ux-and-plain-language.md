# Plan C: Mobile + ND-Friendly UX & Plain Language Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every page mobile-friendly, neurodivergent-accessible, and written in plain language so a brand-new librarian can use the tool without training.

**Architecture:** CSS-first responsive design with progressive enhancement JS for hamburger sidebar and collapsible help boxes. All help text rewritten with jargon tooltips and "Why this matters" lines.

**Tech Stack:** Vanilla CSS (media queries, CSS variables), vanilla JS (DOM manipulation, localStorage), Jinja2 templates

---

## Feature 10: Mobile + Neurodivergent-Friendly UX

### Task 1: Responsive CSS Breakpoints & Touch Targets

**Files:**
- Modify: `static/css/style.css`

**Step 1: Add responsive breakpoints and touch-friendly styles**

Add before the existing `@media print` block at the end of `style.css`:

```css
/* ── Responsive ─────────────────────────────────── */

/* Hamburger button (hidden on desktop) */
.hamburger {
    display: none;
    position: fixed;
    top: 0.75rem;
    left: 0.75rem;
    z-index: 1100;
    background: var(--gray-800);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 0.65rem;
    font-size: 1.25rem;
    cursor: pointer;
    line-height: 1;
}

/* Sidebar overlay backdrop */
.sidebar-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    z-index: 999;
}
.sidebar-overlay.active { display: block; }

/* Table horizontal scroll wrapper */
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

/* Tablet: 768px */
@media (max-width: 768px) {
    .hamburger { display: block; }

    .sidebar {
        position: fixed;
        left: -260px;
        top: 0;
        bottom: 0;
        z-index: 1000;
        transition: left 0.25s ease;
        width: 240px;
    }
    .sidebar.open { left: 0; }

    .main-content {
        margin-left: 0;
        padding: 1rem;
        padding-top: 3.5rem;   /* room for hamburger */
    }

    .stat-grid {
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
    }
}

/* Phone: 480px */
@media (max-width: 480px) {
    .stat-grid { grid-template-columns: 1fr; }
    .stat-card { padding: 0.75rem; }
    .page-header h2 { font-size: 1.25rem; }
    .card { padding: 0.75rem; }
    table { font-size: 0.85rem; }
    th, td { padding: 0.35rem 0.5rem; }
}

/* Touch targets: minimum 44px */
@media (pointer: coarse) {
    nav a, .btn-export, .hamburger, button, select, input[type="file"] {
        min-height: 44px;
        display: inline-flex;
        align-items: center;
    }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

**Step 2: Run the app and verify responsive styles**

Run: `cd /Users/sam/Projects/cat && python app.py`
Expected: App starts, resize browser to check breakpoints

**Step 3: Commit**

```bash
git add static/css/style.css
git commit -m "feat: add responsive breakpoints, touch targets, reduced motion CSS"
```

---

### Task 2: Hamburger Toggle + Sidebar Overlay

**Files:**
- Create: `static/js/sidebar.js`
- Modify: `templates/base.html`

**Step 1: Create sidebar.js**

```javascript
document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('.hamburger');
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.sidebar-overlay');
    if (!btn || !sidebar) return;

    function open() {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
        btn.setAttribute('aria-expanded', 'true');
    }
    function close() {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', function () {
        sidebar.classList.contains('open') ? close() : open();
    });
    if (overlay) overlay.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') close();
    });
});
```

**Step 2: Add hamburger button, overlay, and script to base.html**

In `templates/base.html`, add the hamburger button and overlay just inside `<div class="app-container">`:

```html
<div class="app-container">
    <button class="hamburger" aria-label="Toggle navigation" aria-expanded="false">&#9776;</button>
    <div class="sidebar-overlay"></div>
    <aside class="sidebar">
```

And add the script tag in `<head>` after the existing scripts:

```html
<script src="{{ url_for('static', filename='js/sidebar.js') }}" defer></script>
```

**Step 3: Test hamburger on narrow viewport**

Run: Resize browser to < 768px, tap hamburger, verify sidebar slides in, tap overlay to close, press Escape to close.

**Step 4: Commit**

```bash
git add static/js/sidebar.js templates/base.html
git commit -m "feat: add hamburger sidebar toggle with overlay and keyboard close"
```

---

### Task 3: Collapsible Help Boxes with localStorage

**Files:**
- Create: `static/js/help-toggle.js`
- Modify: `static/css/style.css`

**Step 1: Create help-toggle.js using safe DOM methods**

```javascript
document.addEventListener('DOMContentLoaded', function () {
    var boxes = document.querySelectorAll('.help-box');
    var PAGE_KEY = 'helpCollapsed:' + location.pathname;
    var collapsed = localStorage.getItem(PAGE_KEY) === '1';

    boxes.forEach(function (box) {
        var content = box.cloneNode(true);

        // Build toggle button
        var toggle = document.createElement('button');
        toggle.className = 'help-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        toggle.textContent = collapsed ? 'Show help' : 'Hide help';

        // Build wrapper for collapsible content
        var wrapper = document.createElement('div');
        wrapper.className = 'help-body';
        if (collapsed) wrapper.classList.add('collapsed');

        // Move all original children into wrapper
        while (box.firstChild) {
            wrapper.appendChild(box.firstChild);
        }

        // Re-assemble: toggle button first, then wrapper
        box.appendChild(toggle);
        box.appendChild(wrapper);

        toggle.addEventListener('click', function () {
            var isCollapsed = wrapper.classList.toggle('collapsed');
            toggle.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
            toggle.textContent = isCollapsed ? 'Show help' : 'Hide help';
            localStorage.setItem(PAGE_KEY, isCollapsed ? '1' : '0');
        });
    });
});
```

**Step 2: Add help-toggle CSS to style.css**

Add after the existing `.help-box` styles:

```css
.help-toggle {
    background: none;
    border: 1px solid var(--gray-300);
    border-radius: 4px;
    padding: 0.25rem 0.6rem;
    font-size: 0.8rem;
    cursor: pointer;
    color: var(--gray-600);
    float: right;
    margin: -0.25rem 0 0.5rem 0.5rem;
}
.help-toggle:hover { background: var(--gray-100); }
.help-body.collapsed { display: none; }
```

**Step 3: Add script to base.html**

```html
<script src="{{ url_for('static', filename='js/help-toggle.js') }}" defer></script>
```

**Step 4: Test collapsible help boxes**

Run: Open any page with a help box (e.g., /age), click "Hide help", refresh page, verify it stays collapsed. Click "Show help", refresh, verify it stays open.

**Step 5: Commit**

```bash
git add static/js/help-toggle.js static/css/style.css templates/base.html
git commit -m "feat: add collapsible help boxes with localStorage persistence"
```

---

### Task 4: Accessible Text Labels for Column Status Dots

**Files:**
- Modify: `templates/column_mapping.html`
- Modify: `static/css/style.css`

**Step 1: Add text labels next to status dots**

In `column_mapping.html`, update each status dot `<span>` to also include a text label. Replace the existing dot-only markup pattern:

Current pattern:
```html
<span class="col-status {{ 'mapped' if ... else 'unmapped' }}"></span>
```

New pattern:
```html
<span class="col-status {{ 'mapped' if ... else 'unmapped' }}"></span>
<span class="status-label">{{ 'Mapped' if ... else 'Not found' }}</span>
```

**Step 2: Add status-label CSS**

```css
.status-label {
    font-size: 0.8rem;
    color: var(--gray-600);
    margin-left: 0.35rem;
}
.col-status.mapped + .status-label { color: var(--green-700, #15803d); }
```

**Step 3: Commit**

```bash
git add templates/column_mapping.html static/css/style.css
git commit -m "feat: add text labels next to column mapping status dots"
```

---

### Task 5: Wrap All Tables in Scrollable Container

**Files:**
- Modify: 14 report templates (every template with a `<table>`)

**Step 1: Find all templates with bare `<table>` tags not already wrapped**

Wrap each `<table>...</table>` in `<div class="table-scroll">...</div>`. Templates to update:

- `templates/age.html`
- `templates/circulation.html`
- `templates/column_mapping.html`
- `templates/dormant.html`
- `templates/duplicates.html`
- `templates/formats.html`
- `templates/freshness.html`
- `templates/gaps.html`
- `templates/mustie.html`
- `templates/subjects.html`
- `templates/weeding.html`
- `templates/banned_books.html`
- `templates/diversity.html`

Note: `cost.html` already has `<div style="overflow-x: auto;">` wrappers — replace those with `<div class="table-scroll">` for consistency.

**Step 2: Verify tables scroll horizontally on narrow viewport**

Run: Open each page at 375px width, verify tables scroll horizontally without breaking layout.

**Step 3: Commit**

```bash
git add templates/*.html
git commit -m "feat: wrap all tables in scrollable containers for mobile"
```

---

## Feature 11: Plain Language + New Librarian Friendly

### Task 6: Jargon Tooltip CSS

**Files:**
- Modify: `static/css/style.css`

**Step 1: Add tooltip styles**

```css
/* Jargon tooltips */
.jargon {
    text-decoration: underline dotted var(--gray-400);
    cursor: help;
    position: relative;
}
.jargon:hover::after,
.jargon:focus::after {
    content: attr(data-tip);
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: var(--gray-800);
    color: #fff;
    padding: 0.4rem 0.6rem;
    border-radius: 4px;
    font-size: 0.8rem;
    white-space: nowrap;
    max-width: 260px;
    white-space: normal;
    z-index: 100;
    pointer-events: none;
}
```

**Step 2: Commit**

```bash
git add static/css/style.css
git commit -m "feat: add jargon tooltip CSS for plain-language help text"
```

---

### Task 7: Rewrite All Report Help Boxes with Plain Language

**Files:**
- Modify: `templates/age.html`
- Modify: `templates/circulation.html`
- Modify: `templates/cost.html`
- Modify: `templates/dormant.html`
- Modify: `templates/duplicates.html`
- Modify: `templates/formats.html`
- Modify: `templates/freshness.html`
- Modify: `templates/gaps.html`
- Modify: `templates/mustie.html`
- Modify: `templates/subjects.html`
- Modify: `templates/weeding.html`
- Modify: `templates/banned_books.html`
- Modify: `templates/diversity.html`
- Modify: `templates/index.html`

**Step 1: Rewrite each help box**

Each help box should follow this pattern:
1. **Bold question header** — plain-language question ("What does this page show?")
2. **1-2 sentence answer** — no jargon, or jargon wrapped in `<span class="jargon" data-tip="definition">term</span>`
3. **"Why this matters:"** line — connects the data to a real librarian decision

Example for Age Distribution (`age.html`):

```html
<div class="help-box">
    <strong>What does this page show?</strong>
    This chart shows how many items you have from each decade. A healthy collection
    usually has more recent items and fewer older ones, but this depends on your
    library's focus.
    <br><br>
    Look at the <strong>Avg Checkouts</strong> column: if older decades have very
    low numbers, those items may be sitting on shelves unused.
    <br><br>
    <strong>Why this matters:</strong> Helps you spot decades where you may need to
    buy new material or remove outdated stock.
</div>
```

Full rewrites for all 14 templates are provided to the implementer subagent. Key principles:
- Replace "ROI proxy" with "simple measure of value"
- Replace "reallocation candidates" with "areas where you might shift spending"
- Replace "circulation" with `<span class="jargon" data-tip="How often items are checked out">circulation</span>` on first use per page
- Replace "weeding" with `<span class="jargon" data-tip="Removing outdated or unused items from shelves">weeding</span>` on first use
- Replace "MUSTIE" with `<span class="jargon" data-tip="Misleading, Ugly, Superseded, Trivial, Irrelevant, Elsewhere — criteria for removing items">MUSTIE</span>`
- Always end with "Why this matters:" connecting to a real decision

**Step 2: Verify tooltips render correctly**

Run: Open each page, hover over jargon terms, verify tooltip appears with definition.

**Step 3: Commit**

```bash
git add templates/*.html
git commit -m "feat: rewrite all report help boxes with plain language and jargon tooltips"
```

---

### Task 8: Rewrite Upload, Getting Started, and Column Mapping Help

**Files:**
- Modify: `templates/upload.html`
- Modify: `templates/getting_started.html`
- Modify: `templates/column_mapping.html`

**Step 1: Rewrite help/instruction text**

These three pages are the onboarding flow. Rewrite all instructional text to:
- Use short sentences (< 20 words each)
- Start with action verbs ("Export your catalog...", "Upload the file...", "Check that columns match...")
- Avoid library science jargon, or wrap it in `<span class="jargon" data-tip="...">` tooltips
- Add numbered steps where possible
- Include "What if..." troubleshooting tips inline

For `getting_started.html`:
- Rewrite the steps to be more explicit about what "catalog export" means
- Add: "Your <span class="jargon" data-tip="The software your library uses to manage books and checkouts">ILS</span> (library system) can export data as a CSV or Excel file."

For `upload.html`:
- Simplify the file format requirements
- Add a "What if my file doesn't work?" help box

For `column_mapping.html`:
- Explain what "mapping" means in plain language
- Add tooltip for each field explaining why it matters

**Step 2: Commit**

```bash
git add templates/upload.html templates/getting_started.html templates/column_mapping.html
git commit -m "feat: rewrite onboarding pages with plain language and troubleshooting tips"
```

---

## Verification

After all 8 tasks:

1. Resize browser to 375px — sidebar hidden, hamburger visible, tables scroll
2. Resize to 768px — same behavior
3. Resize to 1200px+ — full sidebar, no hamburger
4. Click hamburger — sidebar slides in with overlay
5. Press Escape — sidebar closes
6. Click "Hide help" — help box collapses, persists across refresh
7. Hover jargon terms — tooltips appear
8. All 14+ pages have rewritten help boxes
9. Column mapping page shows text labels next to dots
