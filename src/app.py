"""
Medical Device Requirements Extractor - Local Web App
Rallis-Daw Consulting | RegCheck Tool
------------------------------------------------------
Supports PDF, Word (.docx), and Excel (.xlsx) files.

SETUP:
    pip3 install flask google-generativeai pdfplumber python-docx openpyxl python-dotenv

CREATE A .env FILE in this same folder containing:
    GEMINI_API_KEY=your_api_key_here

RUN:
    python3 app.py

Then open your browser to: http://localhost:5000
"""

import os
import tempfile
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Services
from services.text_extraction import extract_text
from services.ai_integration import process_with_ai
from services.database_maintenance import init_database
from utils.logging import log_activity, log_error

load_dotenv()

# Initialize app
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, origins=["http://localhost:5000"])

# Initialize database connections
init_database()

# Routes
@app.route("/")
def index():
  log_activity('anonymous', 'page_view', {'page': 'index'})
  return render_template("index.html")

@app.route("/extract", methods=["POST"])
def extract():
  from config.settings import GEMINI_API_KEY
  
  if not GEMINI_API_KEY:
    return jsonify({"error": "No API key found. Make sure your .env file exists with GEMINI_API_KEY set."})

  uploaded = request.files.get("file")
  if not uploaded:
    return jsonify({"error": "No file received."})

  filename = uploaded.filename
  ext = filename.rsplit(".", 1)[-1].lower()

  if ext not in ("pdf", "docx", "xlsx"):
    return jsonify({"error": f"Unsupported file type: .{ext}. Please upload a PDF, DOCX, or XLSX file."})

  with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
    uploaded.save(tmp.name)
    tmp_path = tmp.name

  try:
    text = extract_text(tmp_path, filename)

    if not text.strip():
      return jsonify({"error": "Could not extract text from the file."})

    requirements = process_with_ai(text)

    for i, req in enumerate(requirements):
      req["id"] = i + 1

    log_activity('anonymous', 'extraction_complete', {
      'filename': filename,
      'requirements_count': len(requirements)
    })

    return jsonify({
      "requirements": requirements,
      "filename": filename
    })

  except json.JSONDecodeError:
    log_error('JSON decode error from Gemini', {'filename': filename})
    return jsonify({"error": "Gemini returned an invalid response. Try running again."})
  
  except Exception as e:
    log_error(str(e), {'filename': filename})
    return jsonify({"error": str(e)})
  
  finally:
    os.unlink(tmp_path)

if __name__ == "__main__":
  print("\n" + "=" * 50)
  print("  RegCheck — Rallis-Daw Consulting")
  print("  Supports: PDF, DOCX, XLSX")
  print("=" * 50)
  app.run(debug=False, port=5000)