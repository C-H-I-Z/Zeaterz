"""
Sota — Regulatory Requirement Management System
Rallis-Daw Consulting LLC
Routes only. All logic lives in parser.py, checker.py, comparator.py.
SETUP:
    pip install -r requirements.txt
    Create .env with GEMINI_API_KEY=your_key
    python app.py  →  http://localhost:5000
"""

import os
import json
import csv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client
import tempfile
import google.generativeai as genai

# Services
from .services.text_extraction import extract_text
from .services.database_maintenance import enrich_requirement, insert_to_supabase
from .services.reg_web_scraper import parse_date, check_compliance_date

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"

# Initialize app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'), 
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

CORS(app, origins=[
  "http://localhost:5000",
  "https://sota-regulatory-requirements-manager.onrender.com/"
  ])

# Initialize Supabase client
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"  WARNING: Supabase connection failed: {e}")


@app.route("/")
def index():
    return render_template("index.html")


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
        return jsonify({"error": "Unsupported file type: ." + ext + ". Please upload a PDF, DOCX, or XLSX."})

    with tempfile.NamedTemporaryFile(suffix="." + ext, delete=False) as tmp:
        uploaded.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path, filename)
        if not text.strip():
            return jsonify({"error": "Could not extract text from the file."})

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        prompt = (
            "You are a regulatory document parser for medical devices.\n\n"
            "Extract every standard, regulation, or guidance document from the text below.\n"
            "Return ONLY a valid JSON array with no preamble, explanation, or markdown fences.\n\n"
            "Each object must have exactly these fields:\n"
            "- standard_id: the identifier e.g. ISO 13485, 21 CFR Part 820, FDA Guidance 1677\n"
            "- date: the revision or issue date as written. If marked with ** use the word Current\n"
            "- category: the section this belongs to e.g. Quality System Management\n"
            "- region: US or International based on context\n"
            "- description: a brief description of what this standard covers\n\n"
            "Document text:\n" + text
        )

        response = model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        requirements = json.loads(raw)
        enriched = [enrich_requirement(req, filename) for req in requirements]

        # Include update detection logic
        doc_dates = {}
        for i, req in enumerate(enriched):
            req["id"] = i + 1
            doc_dates[req["standard_id"]] = req["date"]

        # Gather updated issue dates from CSV
        ref_dates = {}
        ref_csv_path = os.path.join(os.path.dirname(__file__), "reference_requirements.csv")
        if os.path.exists(ref_csv_path):
            with open(ref_csv_path, "r") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    key = row["standard_id"].strip()       
                    ref_dates[key] = row["new_date"].strip()

        for req in enriched:
            sid = req["standard_id"].strip()
            doc_date = req.get("date", "")
            ref_date = ref_dates.get(sid)

            print(f"sid: {sid}")
            print(f"doc_date raw: '{doc_date}'")
            print(f"ref_date raw: '{ref_date}' | type: {type(ref_date)}")
            print(f"doc_dt parsed: {parse_date(doc_date)}")
            print(f"ref_dt parsed: {parse_date(ref_date)}")
            print("---")

            req["status"] = check_compliance_date(ref_date, doc_date)

        # End update detection test

        db_success        = False
        db_error          = None
        db_count          = 0
        db_not_configured = False

        if not supabase_client:
            db_not_configured = True
        else:
            rows_to_insert = [{k: v for k, v in r.items() if k != "id"} for r in enriched]
            db_count, db_error = insert_to_supabase(rows_to_insert, supabase_client)
            db_success = db_error is None

        return jsonify({
            "requirements":      enriched,
            "filename":          filename,
            "db_success":        db_success,
            "db_count":          db_count,
            "db_error":          db_error,
            "db_not_configured": db_not_configured,
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Gemini returned an invalid response. Try running again."})
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        os.unlink(tmp_path)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/help")
def help():
    return render_template("help.html")

# if __name__ == "__main__":
#   print("\n" + "=" * 50)
#   print("  RegCheck -- Rallis-Daw Consulting")
#   print("  Supports: PDF, DOCX, XLSX")
#   print("=" * 50)

#   if not GEMINI_API_KEY:
#       print("\n  WARNING: No Gemini API key found!")
#       print("  Add GEMINI_API_KEY to your .env file\n")
#   else:
#       print("  OK: Gemini API key loaded")

#   if not SUPABASE_URL or not SUPABASE_KEY:
#       print("  WARNING: Supabase not configured!")
#       print("  Add SUPABASE_URL and SUPABASE_KEY to your .env file")
#   else:
#       print("  OK: Supabase configured")

#   print("\n  Open your browser to: http://localhost:5000")
#   print("  Press Ctrl+C to stop the server")
#   print("=" * 50 + "\n")

# app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))