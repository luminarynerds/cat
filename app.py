"""Library Collection Analyzer — local Flask web application."""

import csv
import io
import os
import json

from flask import (
    Flask, render_template, request, redirect, url_for, flash, Response,
)
import pandas as pd

from importer import import_catalog, LC_CLASS_LABELS
from analyzer import (
    collection_summary,
    age_distribution,
    subject_balance,
    find_gaps,
    format_breakdown,
    circulation_analysis,
    weeding_candidates,
)
from mustie import get_default_thresholds, apply_mustie, mustie_summary

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory store for the current dataset (local single-user app).
_current_df: pd.DataFrame | None = None
_current_filename: str | None = None


def get_df() -> pd.DataFrame | None:
    return _current_df


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


@app.route("/upload", methods=["GET", "POST"])
def upload():
    global _current_df, _current_filename

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
            _current_df = import_catalog(filepath)
            _current_filename = file.filename
            flash(
                f"Imported {len(_current_df)} items from {file.filename}.",
                "success",
            )
        except Exception as e:
            flash(f"Error importing file: {e}", "error")
            return redirect(url_for("upload"))

        return redirect(url_for("index"))

    return render_template("upload.html")


@app.route("/column-mapping", methods=["GET"])
def column_mapping():
    """Show what columns were detected and how they were mapped."""
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    # Show which canonical columns have data
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
        filename=_current_filename,
    )


@app.route("/gaps")
def gaps():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    gap_data = find_gaps(df)
    return render_template("gaps.html", gaps=gap_data, filename=_current_filename)


@app.route("/subjects")
def subjects():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    balance = subject_balance(df)
    return render_template(
        "subjects.html",
        subjects=balance,
        chart_data=json.dumps(balance),
        filename=_current_filename,
    )


@app.route("/age")
def age():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    dist = age_distribution(df)
    return render_template(
        "age.html",
        distribution=dist,
        chart_data=json.dumps(dist),
        filename=_current_filename,
    )


@app.route("/formats")
def formats():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    data = format_breakdown(df)
    return render_template(
        "formats.html",
        formats=data,
        chart_data=json.dumps(data),
        filename=_current_filename,
    )


@app.route("/circulation")
def circulation():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    data = circulation_analysis(df)
    return render_template(
        "circulation.html",
        circ=data,
        filename=_current_filename,
    )


@app.route("/weeding")
def weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    age_thresh = request.args.get("age", 15, type=int)
    circ_thresh = request.args.get("circ", 2, type=int)

    candidates = weeding_candidates(df, age_thresh, circ_thresh)
    return render_template(
        "weeding.html",
        candidates=candidates.head(200).to_dict("records"),
        total_candidates=len(candidates),
        total_items=len(df),
        age_threshold=age_thresh,
        circ_threshold=circ_thresh,
        filename=_current_filename,
    )


# ---------------------------------------------------------------------------
# MUSTIE / CREW weeding
# ---------------------------------------------------------------------------

# Session-scoped custom thresholds (survives across page loads)
_custom_thresholds: dict[str, dict] | None = None


@app.route("/mustie", methods=["GET"])
def mustie_weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    thresholds = _custom_thresholds or get_default_thresholds()
    circ_floor = request.args.get("circ", 2, type=int)

    flagged = apply_mustie(df, thresholds=thresholds, circ_floor=circ_floor)
    summary = mustie_summary(flagged)

    return render_template(
        "mustie.html",
        candidates=flagged.head(200).fillna("").to_dict("records"),
        total_candidates=len(flagged),
        total_items=len(df),
        summary=summary,
        thresholds=thresholds,
        circ_floor=circ_floor,
        filename=_current_filename,
    )


@app.route("/mustie/settings", methods=["GET", "POST"])
def mustie_settings():
    global _custom_thresholds

    if request.method == "POST":
        thresholds = get_default_thresholds()
        for cls in thresholds:
            age_key = f"age_{cls}"
            if age_key in request.form:
                try:
                    thresholds[cls]["max_age"] = int(request.form[age_key])
                except ValueError:
                    pass
        _custom_thresholds = thresholds
        flash("MUSTIE thresholds updated.", "success")
        return redirect(url_for("mustie_weeding"))

    thresholds = _custom_thresholds or get_default_thresholds()
    return render_template(
        "mustie_settings.html",
        thresholds=thresholds,
        filename=_current_filename,
    )


@app.route("/mustie/reset", methods=["POST"])
def mustie_reset():
    global _custom_thresholds
    _custom_thresholds = None
    flash("MUSTIE thresholds reset to CREW defaults.", "success")
    return redirect(url_for("mustie_settings"))


@app.route("/export/mustie")
def export_mustie():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    thresholds = _custom_thresholds or get_default_thresholds()
    circ_floor = request.args.get("circ", 2, type=int)
    flagged = apply_mustie(df, thresholds=thresholds, circ_floor=circ_floor)
    return _csv_response(
        flagged.fillna("").to_dict("records"),
        "mustie_weeding_candidates.csv",
    )


@app.route("/getting-started")
def getting_started():
    return render_template(
        "getting_started.html",
        has_data=get_df() is not None,
        filename=_current_filename,
    )


# ---------------------------------------------------------------------------
# CSV Export routes
# ---------------------------------------------------------------------------

def _csv_response(rows: list[dict], filename: str) -> Response:
    """Build a CSV download response from a list of dicts."""
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
    # Export the top items list (most useful for sharing)
    return _csv_response(data.get("top_items", []), "top_circulating_items.csv")


@app.route("/export/weeding")
def export_weeding():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))
    age_thresh = request.args.get("age", 15, type=int)
    circ_thresh = request.args.get("circ", 2, type=int)
    candidates = weeding_candidates(df, age_thresh, circ_thresh)
    return _csv_response(candidates.fillna("").to_dict("records"), "weeding_candidates.csv")


@app.route("/export/gaps")
def export_gaps():
    df = get_df()
    if df is None:
        flash("Please upload a file first.", "error")
        return redirect(url_for("upload"))

    gap_data = find_gaps(df)
    # Combine all gap types into one export with a "gap_type" column
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


if __name__ == "__main__":
    print("\n  Library Collection Analyzer")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
