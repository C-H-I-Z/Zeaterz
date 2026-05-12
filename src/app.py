"""
Medical Device Requirements Extractor - Local Web App
Rallis-Daw Consulting | RegCheck Tool
------------------------------------------------------
Supports PDF, Word (.docx), and Excel (.xlsx) files.
Extracts regulatory standards using Gemini AI and stores
results in Supabase.

SETUP:
    pip3 install flask google-generativeai pdfplumber python-docx openpyxl python-dotenv supabase

CREATE A .env FILE in this same folder containing:
    GEMINI_API_KEY=your_gemini_api_key
    SUPABASE_URL=your_supabase_project_url
    SUPABASE_KEY=your_supabase_anon_key

RUN:
    python3 app.py

Then open your browser to: http://localhost:5000
"""

import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client
import tempfile
import google.generativeai as genai

# Services
from .services.text_extraction import extract_text
from .services.database_maintenance import enrich_requirement, insert_to_supabase

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"

# Initialize app
app = Flask(__name__, template_folder='templates', static_folder='static')

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

      for i, req in enumerate(enriched):
          req["id"] = i + 1

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


if __name__ == "__main__":
  print("\n" + "=" * 50)
  print("  RegCheck -- Rallis-Daw Consulting")
  print("  Supports: PDF, DOCX, XLSX")
  print("=" * 50)

  if not GEMINI_API_KEY:
      print("\n  WARNING: No Gemini API key found!")
      print("  Add GEMINI_API_KEY to your .env file\n")
  else:
      print("  OK: Gemini API key loaded")

  if not SUPABASE_URL or not SUPABASE_KEY:
      print("  WARNING: Supabase not configured!")
      print("  Add SUPABASE_URL and SUPABASE_KEY to your .env file")
  else:
      print("  OK: Supabase configured")

  print("\n  Open your browser to: http://localhost:5000")
  print("  Press Ctrl+C to stop the server")
  print("=" * 50 + "\n")

app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))