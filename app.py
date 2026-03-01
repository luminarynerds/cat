"""Library Collection Analyzer — local Flask web application."""

import os
import json

from flask import Flask, render_template, request, redirect, url_for, flash
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


if __name__ == "__main__":
    print("\n  Library Collection Analyzer")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
