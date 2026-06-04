"""
SOTA — Regulatory Requirement Management System
Rallis-Daw Consulting LLC

app.py — Flask server for Sota | Regulatory Requirement Management System.
Rallis-Daw Consulting LLC | Senior Design Project

This file is routes only — all business logic lives in the services layer:
  - parser.py    Text extraction + Gemini document parsing
  - checker.py   Per-requirement Gemini web search
  - comparator.py  Date comparison and CURRENT/OUTDATED/UNVERIFIED assignment

Data flow per session (nothing persists between sessions):
  POST /extract        → parser.py → JSON list of requirements → sessionStorage
  POST /check/start    → registers job, returns job_id
  GET  /check/stream   → streams SSE events as each requirement is checked
  POST /export         → builds and returns an .xlsx workbook

SETUP:
    pip install -r requirements.txt
    Create .env with GEMINI_API_KEY=your_key
    python app.py  →  http://localhost:5000
"""

import io
import json
import os
import sys
import httpx
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv
from flask import (Flask, Response, jsonify, render_template, request, send_file, stream_with_context)
from flask_cors import CORS

# Services
# Add src/ to path so `from services.X import ...` resolves to src/services/
# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
# _SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

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

CORS(app, origins=[
  "http://localhost:5000",
  "https://sota-regulatory-requirements-manager.onrender.com/"
  ])

# In-memory job store: {job_id: [requirement_dicts]}
# Each job is popped immediately when the stream starts, so memory stays clean.
_check_jobs: dict = {}

def _estimate_cost(total_tokens: int) -> str:
    """Rough cost estimate using the average of input and output token prices."""
    avg_price = (_PRICE_PER_M_INPUT + _PRICE_PER_M_OUTPUT) / 2
    return f"${total_tokens / 1_000_000 * avg_price:.4f}"


# ── PAGE ROUTES ────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/upload")
def upload():
    """File upload page — user drops a PDF/DOCX/XLSX here to start a session."""
    return render_template("upload.html")


@app.route("/review")
def review():
    """Review page — user inspects, edits, and approves Gemini's parsed output."""
    return render_template("review.html")


@app.route("/results")
def results():
    """Results dashboard — shows compliance check outcomes with status indicators."""
    return render_template("results.html")

@app.route("/about")
def about():
    """About page."""
    return render_template("about.html")

@app.route("/help")
def help():
    """Help / FAQ page."""
    return render_template("help.html")


# ── API ROUTES ─────────────────────────────────────────────────────────────────


@app.route("/extract", methods=["POST"])
def extract():
    """Receive an uploaded file and return a JSON list of parsed requirements.

    Steps:
      1. Save the upload to a temporary file (deleted in the finally block).
      2. Call parser.extract_text() to get plain text from PDF/DOCX/XLSX.
      3. Call parser.parse_with_gemini() to get raw requirement dicts.
      4. Call parser.enrich_requirement() on each result to add derived fields.
      5. Return the enriched list + token usage + estimated cost.

    Returns JSON:
        {"requirements": [...], "filename": str, "tokens": dict, "cost": str}
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "No Gemini API key found. Check your .env file."})

    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "No file received."})

    filename = uploaded.filename
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "docx", "xlsx"):
        return jsonify({"error": "Unsupported file type: ." + ext})

    # Write to a temp file because pdfplumber and openpyxl need a real path, not a stream.
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
            req["id"] = i + 1       # 1-based row number for display

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
        os.unlink(tmp_path)     # Always remove the temp file, even on error.


@app.route("/check/start", methods=["POST"])
def check_start():
    """Register a compliance check job and return a job_id.

    The two-step start/stream split avoids SSE connection issues in some browsers
    when the request body must also be sent: the client POSTs the requirements list
    here, gets a job_id, then opens an EventSource to /check/stream?job_id=...

    Returns JSON: {"job_id": str}
    """
    data = request.get_json()
    requirements = data.get("requirements", [])

    if not requirements:
        return jsonify({"error": "No requirements to check."})
    
    job_id = str(uuid.uuid4())
    _check_jobs[job_id] = requirements

    return jsonify({"job_id": job_id})


@app.route("/check/stream")
def check_stream():
    """Stream compliance check results as Server-Sent Events.

    Uses ThreadPoolExecutor to run checker.check_requirement() in parallel,
    then yields one SSE event per completed requirement so the browser can
    update the progress bar and table in real time.

    Each SSE data payload is JSON:
        {index, progress, total, requirement, tokens, cost}
    Final event adds:
        {done: true, total_tokens, cost}

    The job is popped from _check_jobs on entry — it cannot be replayed.
    """
    job_id = request.args.get("job_id", "")
    requirements = _check_jobs.pop(job_id, None)

    if requirements is None:
        def _err():
            yield f'data: {json.dumps({"error": "Job not found or expired."})}\n\n'
        return Response(_err(), mimetype="text/event-stream")

    def generate():
        total        = len(requirements)
        total_tokens = 0
        completed    = 0

        # How many requests to run in parallel — tune via .env (default: 5)
        max_workers = int(os.getenv("SOTA_MAX_WORKERS", "5"))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to = {
                executor.submit(check_requirement, req, GEMINI_API_KEY): (i, req)
                for i, req in enumerate(requirements)
            }

            for future in as_completed(future_to):
                i, req = future_to[future]

                try:
                    checked = future.result()
                except Exception as e:
                    # checker.py already retried _MAX_RETRIES times before raising —
                    # this is a true unrecoverable crash, not a transient error.
                    print(f"[stream] UNRECOVERABLE {req.get('standard_id', '?')}: {e}", flush=True)
                    checked = {**req, "current_version": None, "source_url": None, "_tokens": 0}

                compared = compare_requirement(checked)
                tokens   = compared.pop("_tokens", 0) or 0  # _tokens is internal, strip before sending
                total_tokens += tokens
                completed    += 1

                yield "data: " + json.dumps({
                    "index":       i,
                    "progress":    completed,
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

        # Cache-Control prevents proxies from buffering the stream.
        # X-Accel-Buffering disables nginx's response buffering on Render.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/export", methods=["POST"])
def export():
    """Build and return a formatted .xlsx compliance report.

    Receives the final requirements list (post-check) as JSON.
    Returns the Excel file as an attachment download.

    Formatting:
      - Header row: bold white text on blue (#2E6DB4) background.
      - CURRENT rows: light green; OUTDATED: light red; UNVERIFIED: light yellow.
      - Column widths auto-sized (capped at 60 characters to avoid huge columns).
    """
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

@app.route("/api/status")
def api_status():
    """Probe the Gemini API and report readiness to the upload page status bar.

    Hits the models list endpoint — a zero-token call that still validates the key
    and connectivity without starting a generation request.

    Returns JSON:
        {"status": "ready"|"not_configured"|"error", "model": str, "features": [...]}
    """
    if not GEMINI_API_KEY:
        return jsonify({"status": "not_configured", "message": "No API key found in .env"})
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": GEMINI_API_KEY},
            )

        if resp.status_code == 200:
            return jsonify({
                "status":  "ready",
                "message": "Connected",
                "model":   "SOTA",
                "features": ["Document Parsing", "Web Search Grounding", "Google Search"],
            })
        
        return jsonify({"status": "error", "message": f"API returned HTTP {resp.status_code}"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": "Cannot reach Gemini API"})


@app.route("/summarize", methods=["POST"])
def summarize():
    """Generate a plain-language AI summary for one requirement on the results page.

    Called when the user clicks the '✦ Summary' button next to a requirement.
    Uses Google Search grounding so Gemini can look up the current page, but
    degrades gracefully when content is paywalled (falls back to training knowledge).

    Request JSON: {"standard_id": str, "description": str, "source_url": str}
    Returns JSON:  {"summary": str, "tokens": int}  or  {"error": str}
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "No Gemini API key found."})

    data        = request.get_json()
    standard_id = (data.get("standard_id") or "").strip()
    description = (data.get("description") or "").strip()
    source_url  = (data.get("source_url")  or "").strip()

    if not standard_id:
        return jsonify({"error": "No standard ID provided."})

    _URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash:generateContent"
    )

    url_clause = f"Reference: {source_url}\n" if source_url else ""
    prompt = (
        f"Provide a concise, practical summary of this regulatory standard "
        f"for a medical device compliance professional.\n\n"
        f"Standard: {standard_id}\n"
        + (f"Description: {description}\n" if description else "")
        + url_clause
        + "\nIf the document is paywalled or not fully accessible online, summarize "
        f"from publicly available information and your training knowledge — do not "
        f"mention the paywall, just provide the best summary you can.\n\n"
        f"Format your response as 4-5 bullet points covering: what the standard "
        f"covers and its scope, who it applies to, key requirements or obligations, "
        f"the regulatory body and jurisdiction, and any notable recent changes "
        f"relevant to medical device compliance."
    )

    payload = {
        "system_instruction": {"parts": [{"text": "You are a medical device regulatory expert. Summarize regulatory standards accurately and concisely."}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{_URL}?key={GEMINI_API_KEY}", json=payload)
        
        resp.raise_for_status()
        result = resp.json()
        parts  = result["candidates"][0]["content"]["parts"]
        text   = " ".join(p.get("text", "") for p in parts if "text" in p).strip()
        tokens = result.get("usageMetadata", {}).get("totalTokenCount", 0)

        return jsonify({"summary": text, "tokens": tokens})
    
    except Exception as e:
        return jsonify({"error": str(e)})


# ── STARTUP ────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     print("\n" + "=" * 52)
#     print("  SOTA  —  Rallis-Daw Consulting")
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