# Collection Analyzer Tool (CAT)

A free, open-source collection analysis tool for librarians. Upload a CSV or Excel export from your ILS and get instant reports on weeding candidates, collection gaps, age analysis, circulation stats, MUSTIE/CREW scoring, diversity audits, and more.

**Live at [librarians.cloud](https://librarians.cloud)**

## What it does

- **Dashboard** — total items, unique titles/authors, median age, circulation overview
- **Board Summary** — one-page executive summary ready to print for your board
- **Collection Gaps** — subjects that are underrepresented based on LC or Dewey classification
- **Subject Balance** — distribution of items across subject areas
- **Freshness & Age** — how old your collection is, broken down by subject
- **Formats** — physical vs. digital, format breakdown
- **Duplicates** — items with multiple copies that may be candidates for deselection
- **Cost & ROI** — cost per circulation, replacement value estimates
- **Circulation / Usage** — checkout distribution, high and low performers
- **Dormant Items** — items with no checkouts in X years
- **Weeding (Simple)** — basic age + circulation weeding candidates
- **Weeding (MUSTIE/CREW)** — full MUSTIE scoring with customizable per-subject thresholds
- **Banned/Challenged Books** — matches your collection against ALA challenged book lists
- **Diversity Audit** — representation analysis across subject areas

Every report can be exported to CSV. The MUSTIE thresholds are editable per subject area. There's a built-in demo mode with sample data so you can try it without uploading anything.

## Quick start

### With Docker (recommended)

```bash
docker build -t cat-app .
docker run -d -p 5000:5000 --name cat-app cat-app
```

Then open `http://localhost:5000`.

### Without Docker

```bash
pip install -r requirements.txt gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 app:app
```

## Your data stays private

- Data is analyzed in memory only — nothing is written to disk or stored permanently
- Uploaded files are deleted immediately after parsing
- Each user gets an isolated session
- No accounts, no tracking, no analytics

## What file do I need?

Export a CSV or Excel file from your ILS (Sierra, Polaris, Koha, Evergreen, etc.). The tool auto-detects column names. At minimum you need **Title**, **Call Number**, and **Publication Year**. For circulation reports, add a **Checkouts** column.

See the [upload page](https://librarians.cloud/upload) for the full list of recognized column names and downloadable templates.

## Tech stack

- Python 3.12 / Flask
- pandas for data analysis
- Gunicorn (1 worker, 4 threads)
- Vanilla HTML/CSS/JS (no build step, no frameworks)
- Docker for deployment

## Accessibility

- Dark mode (auto-detects OS preference, manual toggle in sidebar)
- Skip-to-content link for keyboard navigation
- ARIA labels on navigation and landmarks
- Responsive down to mobile
- Reduced motion support
- Print-friendly stylesheets

## License

[MIT](LICENSE)

---

Built with [Claude Code](https://claude.ai/code) | Inspired by [r/librarians](https://www.reddit.com/r/librarians/comments/1rgdjzc/software_recommendation_for_collection_development/)
