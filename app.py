"""Library Collection Analyzer — Flask web application with multi-user sessions."""

import csv
import io
import os
import json
import time
import uuid
import threading
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash, Response,
    send_file, session,
)
import pandas as pd

from importer import import_catalog, LC_CLASS_LABELS
from analyzer import (
    collection_summary,
    data_quality_check,
    report_availability,
    age_distribution,
    subject_balance,
    dewey_subject_balance,
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
    diversity_audit,
    generate_recommendations,
)
from mustie import get_default_thresholds, apply_mustie, mustie_summary

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Stable secret key — persists across restarts
# ---------------------------------------------------------------------------
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_SECRET_KEY_PATH = os.path.join(UPLOAD_DIR, ".secret_key")
if os.path.exists(_SECRET_KEY_PATH):
    with open(_SECRET_KEY_PATH, "rb") as f:
        app.secret_key = f.read()
else:
    app.secret_key = os.urandom(32)
    with open(_SECRET_KEY_PATH, "wb") as f:
        f.write(app.secret_key)

# ---------------------------------------------------------------------------
# Session-based in-memory storage
# ---------------------------------------------------------------------------
_sessions: dict[str, dict] = {}
_sessions_lock = threading.Lock()
_last_cleanup = 0.0
SESSION_TTL = 3600  # 1 hour


def _ensure_sid() -> str:
    """Return the current session ID, creating one if needed."""
    sid = session.get("sid")
    if sid is None or sid not in _sessions:
        sid = uuid.uuid4().hex[:16]
        session["sid"] = sid
        with _sessions_lock:
            _sessions[sid] = {
                "df": None,
                "filename": None,
                "data_quality": None,
                "custom_thresholds": None,
                "is_demo": False,
                "ts": time.time(),
            }
    return sid


def _touch() -> None:
    sid = session.get("sid")
    if sid and sid in _sessions:
        _sessions[sid]["ts"] = time.time()


def get_df() -> pd.DataFrame | None:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid]["df"]
    return None


def get_filename() -> str | None:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid]["filename"]
    return None


def get_data_quality() -> dict | None:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid]["data_quality"]
    return None


def get_custom_thresholds() -> dict | None:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid]["custom_thresholds"]
    return None


def get_is_demo() -> bool:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid].get("is_demo", False)
    return False


def _set_session(key: str, value) -> None:
    sid = _ensure_sid()
    _sessions[sid][key] = value
    _sessions[sid]["ts"] = time.time()


@app.before_request
def _cleanup_and_init():
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup > 60:
        _last_cleanup = now
        expired = [
            sid for sid, data in _sessions.items()
            if now - data["ts"] > SESSION_TTL
        ]
        if expired:
            with _sessions_lock:
                for sid in expired:
                    _sessions.pop(sid, None)
    _ensure_sid()
    _touch()


@app.context_processor
def _inject_globals():
    return {
        "filename": get_filename(),
        "is_demo": get_is_demo(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_audience_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    audience = request.args.get("audience")
    if audience and "audience" in df.columns:
        filtered = df[df["audience"] == audience]
        if len(filtered) > 0:
            return filtered, audience
    return df, None



# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    df = get_df()
    summary = None
    audience_filter = None
    reports = None
    if df is not None:
        df, audience_filter = _apply_audience_filter(df)
        summary = collection_summary(df)
        reports = report_availability(df)
    return render_template(
        "index.html",
        summary=summary,
        audience_filter=audience_filter,
        data_quality=get_data_quality(),
        reports=reports,
    )


@app.route("/summary")
def executive_summary():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    summary = collection_summary(df)
    gap_data = find_gaps(df)
    recommendations = generate_recommendations(df, summary, gap_data)

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
        now=datetime.now().strftime("%B %d, %Y"),
    )



@app.route("/load-demo", methods=["POST"])
def load_demo():
    demo_path = os.path.join(os.path.dirname(__file__), "sample_data", "demo_catalog.csv")
    if not os.path.exists(demo_path):
        flash("Demo data not available.", "error")
        return redirect(url_for("index"))
    try:
        df = import_catalog(demo_path)
        _set_session("df", df)
        _set_session("filename", "demo_catalog.csv")
        _set_session("data_quality", data_quality_check(df))
        _set_session("is_demo", True)
        flash(f"Loaded demo dataset with {len(df)} sample items.", "success")
    except Exception as e:
        flash(f"Error loading demo data: {e}", "error")
    return redirect(url_for("index"))


@app.route("/edit-item", methods=["POST"])
def edit_item():
    df = get_df()
    if df is None:
        return {"ok": False, "error": "No data loaded"}, 400
    data = request.get_json()
    if not data:
        return {"ok": False, "error": "No data"}, 400
    idx = data.get("index")
    field = data.get("field")
    value = data.get("value")
    if field != "price":
        return {"ok": False, "error": "Only price is editable"}, 400
    if idx is None or idx < 0 or idx >= len(df):
        return {"ok": False, "error": "Invalid index"}, 400
    try:
        df.at[idx, "price"] = float(value) if value is not None else pd.NA
        return {"ok": True}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}, 400


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Please select a file to upload.", "error")
            return redirect(url_for("upload"))

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".csv", ".xlsx", ".xls"):
            flash("Unsupported file type. Please upload a CSV or Excel file.", "error")
            return redirect(url_for("upload"))

        filepath = os.path.join(UPLOAD_DIR, file.filename)
        file.save(filepath)

        try:
            df = import_catalog(filepath)
            _set_session("df", df)
            _set_session("filename", file.filename)
            _set_session("is_demo", False)
            dq = data_quality_check(df)
            _set_session("data_quality", dq)
            flash(
                f"Imported {len(df)} items from {file.filename}.",
                "success",
            )
            if dq["has_issues"]:
                for issue in dq["issues"]:
                    flash(issue, "warning")
        except Exception as e:
            flash(f"Error importing file: {e}", "error")
            return redirect(url_for("upload"))
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

        return redirect(url_for("index"))

    return render_template("upload.html")


TEMPLATE_ALLOWLIST = {"template_blank.csv", "template_example.csv"}


@app.route("/download-template/<name>")
def download_template(name):
    if name not in TEMPLATE_ALLOWLIST:
        flash("Template not found.", "error")
        return redirect(url_for("upload"))
    filepath = os.path.join(os.path.dirname(__file__), "sample_data", name)
    return send_file(filepath, as_attachment=True, download_name=name)


@app.route("/column-mapping", methods=["GET"])
def column_mapping():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    mapping_info = []
    for col in df.columns:
        non_null = df[col].notna().sum()
        mapping_info.append({
            "column": col,
            "populated": int(non_null),
            "total": len(df),
            "percentage": round(non_null / len(df) * 100, 1) if len(df) > 0 else 0,
        })
    return render_template(
        "column_mapping.html",
        mapping=mapping_info,
    )


@app.route("/gaps")
def gaps():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    gap_data = find_gaps(df)

    class_system = "LC"
    if "classification_system" in df.columns:
        lc = int((df["classification_system"] == "LC").sum())
        dw = int((df["classification_system"] == "Dewey").sum())
        if dw > lc:
            class_system = "Dewey"

    return render_template("gaps.html", gaps=gap_data,
                           audience_filter=audience_filter, class_system=class_system)


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
        chart_data=json.dumps(balance),
        audience_filter=audience_filter,
    )


@app.route("/age")
def age():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    dist = age_distribution(df)
    return render_template(
        "age.html",
        distribution=dist,
        chart_data=json.dumps(dist),
        audience_filter=audience_filter,
    )


@app.route("/formats")
def formats():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    data = format_breakdown(df)
    digital = digital_physical_split(df)
    return render_template(
        "formats.html",
        formats=data,
        digital=digital,
        chart_data=json.dumps(data),
        audience_filter=audience_filter,
    )


@app.route("/circulation")
def circulation():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    data = circulation_analysis(df)
    return render_template(
        "circulation.html",
        circ=data,
        audience_filter=audience_filter,
    )


@app.route("/weeding")
def weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    age_thresh = request.args.get("age", 15, type=int)
    circ_thresh = request.args.get("circ", 2, type=int)

    candidates = weeding_candidates(df, age_thresh, circ_thresh)
    return render_template(
        "weeding.html",
        candidates=candidates.head(200).fillna("").to_dict("records"),
        total_candidates=len(candidates),
        total_items=len(df),
        age_threshold=age_thresh,
        circ_threshold=circ_thresh,
        audience_filter=audience_filter,
    )


# ---------------------------------------------------------------------------
# MUSTIE / CREW weeding
# ---------------------------------------------------------------------------

@app.route("/mustie", methods=["GET"])
def mustie_weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    thresholds = get_custom_thresholds() or get_default_thresholds()

    flagged = apply_mustie(df, thresholds=thresholds)
    summary = mustie_summary(flagged)

    return render_template(
        "mustie.html",
        candidates=flagged.head(200).fillna("").to_dict("records"),
        total_candidates=len(flagged),
        total_items=len(df),
        summary=summary,
        thresholds=thresholds,
        audience_filter=audience_filter,
    )


@app.route("/mustie/settings", methods=["GET", "POST"])
def mustie_settings():
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
        _set_session("custom_thresholds", thresholds)
        flash("MUSTIE thresholds updated.", "success")
        return redirect(url_for("mustie_weeding"))

    thresholds = get_custom_thresholds() or get_default_thresholds()
    return render_template(
        "mustie_settings.html",
        thresholds=thresholds,
    )


@app.route("/mustie/reset", methods=["POST"])
def mustie_reset():
    _set_session("custom_thresholds", None)
    flash("MUSTIE thresholds reset to CREW defaults.", "success")
    return redirect(url_for("mustie_settings"))


@app.route("/export/mustie")
def export_mustie():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, _ = _apply_audience_filter(df)

    thresholds = get_custom_thresholds() or get_default_thresholds()
    flagged = apply_mustie(df, thresholds=thresholds)
    return _csv_response(
        flagged.fillna("").to_dict("records"),
        "mustie_weeding_candidates.csv",
    )


# ---------------------------------------------------------------------------
# Dormant items, duplicates, cost analysis, freshness
# ---------------------------------------------------------------------------

@app.route("/dormant")
def dormant():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    years = request.args.get("years", 3, type=int)
    data = dormant_items(df, dormant_years=years)
    return render_template(
        "dormant.html", data=data, dormant_years=years,
        total_items=len(df),
        audience_filter=audience_filter,
    )


@app.route("/duplicates")
def duplicates():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    data = find_duplicates(df)
    return render_template(
        "duplicates.html", dupes=data,
        total_items=len(df),
        audience_filter=audience_filter,
    )


@app.route("/cost")
def cost():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    data = cost_analysis(df)
    return render_template(
        "cost.html", cost=data,
        audience_filter=audience_filter,
    )


@app.route("/freshness")
def freshness():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, audience_filter = _apply_audience_filter(df)

    data = collection_freshness(df)

    class_system = "LC"
    if "classification_system" in df.columns:
        lc = int((df["classification_system"] == "LC").sum())
        dw = int((df["classification_system"] == "Dewey").sum())
        if dw > lc:
            class_system = "Dewey"

    return render_template(
        "freshness.html", freshness=data,
        chart_data=json.dumps(data),
        audience_filter=audience_filter, class_system=class_system,
    )


@app.route("/export/dormant")
def export_dormant():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    years = request.args.get("years", 3, type=int)
    data = dormant_items(df, dormant_years=years)
    return _csv_response(data.get("item_list", []), "dormant_items.csv")


@app.route("/export/duplicates")
def export_duplicates():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    data = find_duplicates(df)
    rows = []
    for g in data.get("isbn_groups", []):
        for item in g["copies"]:
            item["dupe_type"] = "ISBN"
            item["dupe_isbn"] = g["isbn"]
            rows.append(item)
    for g in data.get("title_author_groups", []):
        for item in g["copies"]:
            item["dupe_type"] = "Title+Author"
            item["dupe_isbn"] = ""
            rows.append(item)
    return _csv_response(rows, "duplicates.csv")


@app.route("/export/cost")
def export_cost():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    data = cost_analysis(df)
    return _csv_response(data.get("by_subject", []), "cost_by_subject.csv")


@app.route("/export/freshness")
def export_freshness():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    return _csv_response(collection_freshness(df), "collection_freshness.csv")


@app.route("/getting-started")
def getting_started():
    return render_template(
        "getting_started.html",
        has_data=get_df() is not None,
    )


# ---------------------------------------------------------------------------
# CSV Export routes
# ---------------------------------------------------------------------------

def _csv_response(rows: list[dict], filename: str) -> Response:
    if not rows:
        return Response("No data to export.\n", mimetype="text/plain")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/export/subjects")
def export_subjects():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    return _csv_response(subject_balance(df), "subject_balance.csv")


@app.route("/export/age")
def export_age():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    return _csv_response(age_distribution(df), "age_distribution.csv")


@app.route("/export/formats")
def export_formats():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    return _csv_response(format_breakdown(df), "format_breakdown.csv")


@app.route("/export/circulation")
def export_circulation():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    data = circulation_analysis(df)
    return _csv_response(data.get("top_items", []), "top_circulating_items.csv")


@app.route("/export/weeding")
def export_weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, _ = _apply_audience_filter(df)
    age_thresh = request.args.get("age", 15, type=int)
    circ_thresh = request.args.get("circ", 2, type=int)
    candidates = weeding_candidates(df, age_thresh, circ_thresh)
    return _csv_response(candidates.fillna("").to_dict("records"), "weeding_candidates.csv")


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
        thresholds = get_custom_thresholds() or get_default_thresholds()
        candidates = apply_mustie(df, thresholds)
    else:
        age_thresh = request.args.get("age", 15, type=int)
        circ_thresh = request.args.get("circ", 2, type=int)
        candidates = weeding_candidates(df, age_thresh, circ_thresh)

    if candidates is None or len(candidates) == 0:
        return "No candidates to export.", 400

    cols = ["call_number", "title", "author"]
    if "location" in candidates.columns:
        cols.insert(1, "location")

    pull = candidates[cols].copy()
    pull = pull.sort_values("call_number", na_position="last")
    rows = pull.fillna("").to_dict("records")
    return _csv_response(rows, "pull-list.csv")


@app.route("/export/gaps")
def export_gaps():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    gap_data = find_gaps(df)
    rows = []
    for item in gap_data.get("underrepresented_subjects", []):
        rows.append({
            "gap_type": "Underrepresented Subject",
            "subject_class": item.get("broad_class", ""),
            "subject_label": item.get("label", ""),
            "detail": f"{item.get('count', '')} items ({item.get('percentage', '')}%)",
            "avg_checkouts": item.get("avg_checkouts", ""),
        })
    for item in gap_data.get("missing_recent", []):
        rows.append({
            "gap_type": "Missing Recent Material",
            "subject_class": item.get("broad_class", ""),
            "subject_label": item.get("label", ""),
            "detail": f"{item.get('recent_count', '')} items in last 5 years",
            "avg_checkouts": "",
        })
    for item in gap_data.get("aging_areas", []):
        rows.append({
            "gap_type": "Aging Area",
            "subject_class": item.get("broad_class", ""),
            "subject_label": item.get("label", ""),
            "detail": f"Median pub year {int(item.get('pub_year', 0))}, "
                       f"median age {int(item.get('median_age', 0))} yrs",
            "avg_checkouts": "",
        })
    if gap_data.get("low_circulation"):
        lc = gap_data["low_circulation"]
        rows.append({
            "gap_type": "Low Circulation Summary",
            "subject_class": "",
            "subject_label": "",
            "detail": f"{lc['count']} items never circulated ({lc['percentage']}%)",
            "avg_checkouts": "",
        })
    return _csv_response(rows, "collection_gaps.csv")


@app.route("/export/full-catalog")
def export_full_catalog():
    """Export the full imported dataset back as CSV."""
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=full_catalog_export.csv"},
    )


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
    )


@app.route("/export/diversity")
def export_diversity():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    df, _ = _apply_audience_filter(df)
    result = diversity_audit(df)
    rows = []
    for cat in result.get("categories", []):
        for item in cat.get("items", []):
            rows.append({**item, "diversity_category": cat["name"]})
    if not rows:
        flash("No diversity data to export.", "error")
        return redirect(url_for("diversity"))
    return _csv_response(rows, "diversity_audit.csv")


if __name__ == "__main__":
    print("\n  Library Collection Analyzer")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
