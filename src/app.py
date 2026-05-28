"""
Sota — Regulatory Requirement Management System
Rallis-Daw Consulting LLC

Routes only. All logic lives in parser.py, checker.py, comparator.py.

SETUP:
    pip install -r requirements.txt
    Create .env with GEMINI_API_KEY=your_key
    python app.py  →  http://localhost:5000
"""

import io
import json
import os
import tempfile
import uuid
from datetime import datetime
from dotenv import load_dotenv
from flask import (Flask, Response, jsonify, render_template, request, send_file, stream_with_context)
from flask_cors import CORS

# Services
from .services.checker import check_requirement
from .services.comparator import compare_requirement
from .services.parser import enrich_requirement, extract_text, parse_with_gemini

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini 2.5 Flash pricing per 1 million tokens — update if pricing changes
_PRICE_PER_M_INPUT  = 0.075
_PRICE_PER_M_OUTPUT = 0.300

# Initialize app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'), 
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# In-memory job store: {job_id: [requirement_dicts]}
# Each job is popped immediately when the stream starts, so memory stays clean.
_check_jobs: dict = {}

def _estimate_cost(total_tokens: int) -> str:
    avg_price = (_PRICE_PER_M_INPUT + _PRICE_PER_M_OUTPUT) / 2
    return f"${total_tokens / 1_000_000 * avg_price:.4f}"

CORS(app, origins=[
  "http://localhost:5000",
  "https://sota-regulatory-requirements-manager.onrender.com/"
  ])


# ── PAGE ROUTES ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload")
def upload():
    return render_template("upload.html")


@app.route("/review")
def review():
    return render_template("review.html")


@app.route("/results")
def results():
    return render_template("results.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/help")
def help():
    return render_template("help.html")


# ── API ROUTES ─────────────────────────────────────────────────────────────────

@app.route("/extract", methods=["POST"])
def extract():
    if not GEMINI_API_KEY:
        return jsonify({"error": "No Gemini API key found. Check your .env file."})

    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "No file received."})

    filename = uploaded.filename
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "docx", "xlsx"):
        return jsonify({"error": "Unsupported file type: ." + ext})

    with tempfile.NamedTemporaryFile(suffix="." + ext, delete=False) as tmp:
        uploaded.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path, filename)
        if not text.strip():
            return jsonify({"error": "Could not extract text from the file."})

        raw_reqs, tokens = parse_with_gemini(text, GEMINI_API_KEY)
        enriched = [enrich_requirement(r, filename) for r in raw_reqs]
        for i, req in enumerate(enriched):
            req["id"] = i + 1

        return jsonify({
            "requirements": enriched,
            "filename":     filename,
            "tokens":       tokens,
            "cost":         _estimate_cost(tokens["total"]),
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Gemini returned an invalid response. Try again."})
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        os.unlink(tmp_path)


@app.route("/check/start", methods=["POST"])
def check_start():
    data = request.get_json()
    requirements = data.get("requirements", [])
    if not requirements:
        return jsonify({"error": "No requirements to check."})
    job_id = str(uuid.uuid4())
    _check_jobs[job_id] = requirements
    return jsonify({"job_id": job_id})


@app.route("/check/stream")
def check_stream():
    job_id = request.args.get("job_id", "")
    requirements = _check_jobs.pop(job_id, None)

    if requirements is None:
        def _err():
            yield f'data: {json.dumps({"error": "Job not found or expired."})}\n\n'
        return Response(_err(), mimetype="text/event-stream")

    def generate():
        total        = len(requirements)
        total_tokens = 0

        for i, req in enumerate(requirements):
            checked  = check_requirement(req, GEMINI_API_KEY)
            compared = compare_requirement(checked)
            tokens   = compared.pop("_tokens", 0) or 0
            total_tokens += tokens

            yield "data: " + json.dumps({
                "index":       i,
                "progress":    i + 1,
                "total":       total,
                "requirement": compared,
                "tokens":      total_tokens,
                "cost":        _estimate_cost(total_tokens),
            }) + "\n\n"

        yield "data: " + json.dumps({
            "done":         True,
            "total_tokens": total_tokens,
            "cost":         _estimate_cost(total_tokens),
        }) + "\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/export", methods=["POST"])
def export():
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    data         = request.get_json()
    requirements = data.get("requirements", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compliance Report"

    columns = [
        "#", "Standard ID", "Date on File", "Current Version",
        "Status", "Source URL", "Category", "Region", "Description",
    ]

    hdr_fill = PatternFill(start_color="2E6DB4", end_color="2E6DB4", fill_type="solid")
    hdr_font = Font(bold=True, color="FFFFFF")

    for col, name in enumerate(columns, 1):
        c = ws.cell(row=1, column=col, value=name)
        c.fill = hdr_fill
        c.font = hdr_font
        c.alignment = Alignment(horizontal="center")

    status_fills = {
        "CURRENT":    PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid"),
        "OUTDATED":   PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid"),
        "UNVERIFIED": PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid"),
    }

    for r, req in enumerate(requirements, 2):
        status = req.get("status") or "UNVERIFIED"
        row_data = [
            r - 1,
            req.get("standard_id", ""),
            req.get("date", ""),
            req.get("current_version") or "",
            status,
            req.get("source_url") or "",
            req.get("category", ""),
            req.get("region", ""),
            req.get("description", ""),
        ]
        fill = status_fills.get(status)
        for col, val in enumerate(row_data, 1):
            c = ws.cell(row=r, column=col, value=val)
            if fill:
                c.fill = fill

    for col in range(1, len(columns) + 1):
        max_len = max(
            (len(str(c.value)) for row in ws.iter_rows(min_col=col, max_col=col)
             for c in row if c.value),
            default=10,
        )
        ws.column_dimensions[get_column_letter(col)].width = min(max_len + 4, 60)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    fname = f"sota_report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=fname,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── STARTUP ────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     print("\n" + "=" * 52)
#     print("  Sota  —  Rallis-Daw Consulting")
#     print("  Regulatory Requirement Management System")
#     print("=" * 52)

#     if not GEMINI_API_KEY:
#         print("\n  WARNING: No Gemini API key found!")
#         print("  Add GEMINI_API_KEY to your .env file\n")

#     else:
#         print("  OK: Gemini API key loaded")
        
#     print("\n  Open your browser to: http://localhost:5000")
#     print("  Press Ctrl+C to stop the server")
#     print("=" * 52 + "\n")

#     app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))