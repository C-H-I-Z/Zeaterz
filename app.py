"""
Medical Device Requirements Extractor - Local Web App
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

import json
import os
import tempfile
import pdfplumber
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template_string
from docx import Document
from dotenv import load_dotenv
import openpyxl

# Load API key from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"

app = Flask(__name__)


# ── TEXT EXTRACTION ────────────────────────────────────────────────────────────

def extract_from_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_from_docx(path):
    doc = Document(path)
    text = ""
    for para in doc.paragraphs:
        if para.text.strip():
            text += para.text + "\n"
    for table in doc.tables:
        for row in table.rows:
            row_text = "\t".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text += row_text + "\n"
    return text


def extract_from_xlsx(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    text = ""
    for sheet in wb.worksheets:
        text += f"\n--- Sheet: {sheet.title} ---\n"
        for row in sheet.iter_rows(values_only=True):
            row_text = "\t".join(str(cell) for cell in row if cell is not None)
            if row_text.strip():
                text += row_text + "\n"
    return text


def extract_text(path, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_from_pdf(path)
    elif ext == "docx":
        return extract_from_docx(path)
    elif ext == "xlsx":
        return extract_from_xlsx(path)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")


# ── HTML ───────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RegCheck — Requirements Extractor</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0e1a;
    --surface: #111827;
    --border: #1e2d45;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --success: #10b981;
    --warning: #f59e0b;
    --text: #e2e8f0;
    --muted: #64748b;
    --font: 'Syne', sans-serif;
    --mono: 'DM Mono', monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    background-image:
      radial-gradient(ellipse at 20% 20%, rgba(0,212,255,0.05) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 80%, rgba(124,58,237,0.05) 0%, transparent 50%);
  }

  header {
    padding: 28px 48px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .logo {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .logo-badge {
    font-size: 10px;
    font-weight: 600;
    font-family: var(--mono);
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.1em;
    opacity: 0.7;
  }

  .main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 40px 48px;
  }

  .drop-zone {
    border: 2px dashed var(--border);
    border-radius: 16px;
    padding: 64px 40px;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s;
    background: var(--surface);
    position: relative;
    overflow: hidden;
  }

  .drop-zone::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(0,212,255,0.03), rgba(124,58,237,0.03));
    opacity: 0;
    transition: opacity 0.25s;
  }

  .drop-zone.dragover { border-color: var(--accent); background: rgba(0,212,255,0.04); }
  .drop-zone.dragover::before { opacity: 1; }
  .drop-zone.has-file { border-color: var(--success); border-style: solid; }

  .drop-icon { font-size: 48px; margin-bottom: 16px; display: block; }
  .drop-title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
  .drop-sub { font-size: 13px; color: var(--muted); font-family: var(--mono); }

  .file-types {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-top: 16px;
  }

  .type-badge {
    font-size: 11px;
    font-family: var(--mono);
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 4px;
    letter-spacing: 0.05em;
  }

  .type-pdf  { background: rgba(239,68,68,0.15); color: #fca5a5; }
  .type-docx { background: rgba(59,130,246,0.15); color: #93c5fd; }
  .type-xlsx { background: rgba(16,185,129,0.15); color: #6ee7b7; }

  .drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }

  .file-preview {
    display: none;
    margin-top: 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 20px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .file-preview.visible { display: flex; }
  .file-info { display: flex; align-items: center; gap: 12px; }
  .file-icon { font-size: 22px; }
  .file-name { font-family: var(--mono); font-size: 13px; color: var(--text); }

  .file-clear {
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--muted);
    cursor: pointer;
    font-size: 12px;
    font-family: var(--mono);
    padding: 4px 10px;
    transition: all 0.2s;
  }
  .file-clear:hover { border-color: #ef4444; color: #ef4444; }

  .submit-wrap { display: none; margin-top: 20px; text-align: center; }
  .submit-wrap.visible { display: block; }

  .btn-submit {
    background: linear-gradient(135deg, var(--accent), #0099cc);
    border: none;
    border-radius: 10px;
    color: #0a0e1a;
    cursor: pointer;
    font-family: var(--font);
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.03em;
    padding: 14px 48px;
    transition: opacity 0.2s, transform 0.15s;
  }
  .btn-submit:hover { opacity: 0.9; transform: translateY(-2px); }
  .btn-submit:active { transform: translateY(0); }
  .btn-submit:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

  .status {
    display: none;
    margin-top: 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    align-items: center;
    gap: 16px;
  }
  .status.visible { display: flex; }

  .spinner {
    width: 22px; height: 22px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status-text { font-size: 14px; color: var(--muted); font-family: var(--mono); }

  .disclaimer {
    display: none;
    margin-top: 20px;
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.25);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 12px;
    color: #fbbf24;
    font-family: var(--mono);
    line-height: 1.6;
  }

  .error-box {
    display: none;
    margin-top: 16px;
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 13px;
    color: #fca5a5;
    font-family: var(--mono);
  }

  #results { margin-top: 32px; display: none; }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 28px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .stat-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }

  .stat-number {
    font-size: 32px;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
  }
  .stat-label {
    font-size: 11px;
    color: var(--muted);
    font-family: var(--mono);
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .download-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: transparent;
    border: 1px solid var(--accent);
    border-radius: 8px;
    color: var(--accent);
    cursor: pointer;
    font-family: var(--font);
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
    margin-bottom: 24px;
    transition: all 0.2s;
    text-decoration: none;
  }
  .download-btn:hover { background: rgba(0,212,255,0.08); }

  .category-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 16px;
    overflow: hidden;
  }

  .category-header {
    padding: 14px 20px;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid var(--border);
  }
  .category-header:hover { background: rgba(255,255,255,0.02); }

  .cat-count {
    font-size: 11px;
    background: rgba(0,212,255,0.15);
    color: var(--accent);
    border-radius: 20px;
    padding: 2px 10px;
    font-family: var(--mono);
  }

  .cat-toggle { margin-left: auto; color: var(--muted); transition: transform 0.2s; }
  .category-section.collapsed .cat-toggle { transform: rotate(-90deg); }
  .category-section.collapsed .cat-body { display: none; }

  table { width: 100%; border-collapse: collapse; }

  th {
    text-align: left;
    padding: 10px 16px;
    font-size: 10px;
    font-family: var(--mono);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid var(--border);
  }

  td {
    padding: 11px 16px;
    font-size: 13px;
    border-bottom: 1px solid rgba(30,45,69,0.5);
    vertical-align: top;
    line-height: 1.5;
  }

  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.015); }

  .std-id { font-family: var(--mono); font-size: 12px; font-weight: 500; color: var(--accent); }
  .date-chip {
    font-family: var(--mono);
    font-size: 11px;
    background: rgba(124,58,237,0.15);
    color: #a78bfa;
    padding: 3px 8px;
    border-radius: 4px;
    white-space: nowrap;
  }

  .badge { font-size: 10px; font-family: var(--mono); font-weight: 600; padding: 3px 8px; border-radius: 4px; letter-spacing: 0.05em; }
  .badge-us   { background: rgba(0,212,255,0.12); color: var(--accent); }
  .badge-intl { background: rgba(16,185,129,0.12); color: var(--success); }
</style>
</head>
<body>

<header>
  <div class="logo">SOTA</div>
  <div class="logo-badge">PROTOTYPE v0.1</div>
</header>

<div class="main">

  <div class="drop-zone" id="dropZone">
    <input type="file" id="fileInput" accept=".pdf,.docx,.xlsx">
    <span class="drop-icon" id="dropIcon">📋</span>
    <div class="drop-title" id="dropTitle">Drop your requirements file here</div>
    <div class="drop-sub" id="dropSub">or click to browse</div>
    <div class="file-types">
      <span class="type-badge type-pdf">PDF</span>
      <span class="type-badge type-docx">DOCX</span>
      <span class="type-badge type-xlsx">XLSX</span>
    </div>
  </div>

  <div class="file-preview" id="filePreview">
    <div class="file-info">
      <span class="file-icon" id="fileTypeIcon">📄</span>
      <span class="file-name" id="fileName"></span>
    </div>
    <button class="file-clear" onclick="clearFile()">✕ Remove</button>
  </div>

  <div class="submit-wrap" id="submitWrap">
    <button class="btn-submit" id="submitBtn" onclick="submitFile()">
      Extract Requirements →
    </button>
  </div>

  <div class="status" id="status">
    <div class="spinner"></div>
    <div class="status-text" id="statusText">Sending to Gemini AI...</div>
  </div>

  <div class="error-box" id="errorBox"></div>

  <div class="disclaimer" id="disclaimer">
    ⚠ AI DISCLAIMER: This extraction was performed by an AI model and is intended as a tool to assist
    regulatory review only. All results should be independently verified by a qualified regulatory
    professional before use in any compliance or regulatory submission.
  </div>

  <div id="results">
    <div class="stats-row" id="statsRow"></div>
    <a class="download-btn" id="downloadBtn" href="#">⬇ Download JSON</a>
    <div id="categorySections"></div>
  </div>

</div>

<script>
  const dropZone    = document.getElementById('dropZone');
  const fileInput   = document.getElementById('fileInput');
  const filePreview = document.getElementById('filePreview');
  const fileName    = document.getElementById('fileName');
  const submitWrap  = document.getElementById('submitWrap');
  const submitBtn   = document.getElementById('submitBtn');
  const status      = document.getElementById('status');
  const statusText  = document.getElementById('statusText');
  const results     = document.getElementById('results');
  const errorBox    = document.getElementById('errorBox');
  const disclaimer  = document.getElementById('disclaimer');

  let selectedFile = null;

  const ALLOWED = ['pdf', 'docx', 'xlsx'];
  const FILE_ICONS = { pdf: '📕', docx: '📘', xlsx: '📗' };

  function getExt(filename) {
    return filename.split('.').pop().toLowerCase();
  }

  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && ALLOWED.includes(getExt(file.name))) setFile(file);
    else showError('Please drop a PDF, DOCX, or XLSX file.');
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function setFile(file) {
    selectedFile = file;
    const ext = getExt(file.name);
    dropZone.classList.add('has-file');
    document.getElementById('dropIcon').textContent = '✅';
    document.getElementById('dropTitle').textContent = 'File ready';
    document.getElementById('dropSub').textContent = 'Drop a different file to replace it';
    document.getElementById('fileTypeIcon').textContent = FILE_ICONS[ext] || '📄';
    fileName.textContent = file.name;
    filePreview.classList.add('visible');
    submitWrap.classList.add('visible');
    errorBox.style.display = 'none';
    results.style.display = 'none';
    disclaimer.style.display = 'none';
  }

  function clearFile() {
    selectedFile = null;
    fileInput.value = '';
    dropZone.classList.remove('has-file');
    document.getElementById('dropIcon').textContent = '📋';
    document.getElementById('dropTitle').textContent = 'Drop your requirements file here';
    document.getElementById('dropSub').textContent = 'or click to browse';
    filePreview.classList.remove('visible');
    submitWrap.classList.remove('visible');
    errorBox.style.display = 'none';
  }

  function submitFile() {
    if (!selectedFile) return;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    errorBox.style.display = 'none';
    results.style.display = 'none';
    disclaimer.style.display = 'none';
    status.classList.add('visible');

    const formData = new FormData();
    formData.append('file', selectedFile);

    fetch('/extract', { method: 'POST', body: formData })
      .then(r => r.json())
      .then(data => {
        status.classList.remove('visible');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Extract Requirements →';
        if (data.error) { showError(data.error); return; }
        renderResults(data.requirements, data.filename);
      })
      .catch(err => {
        status.classList.remove('visible');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Extract Requirements →';
        showError('Server error: ' + err.message);
      });
  }

  function renderResults(requirements, filename) {
    disclaimer.style.display = 'block';
    results.style.display = 'block';

    const categories = {};
    requirements.forEach(r => {
      const cat = r.category || 'Uncategorized';
      categories[cat] = categories[cat] || [];
      categories[cat].push(r);
    });

    const usCount   = requirements.filter(r => r.region === 'US').length;
    const intlCount = requirements.filter(r => r.region === 'International').length;

    document.getElementById('statsRow').innerHTML = `
      <div class="stat-card"><div class="stat-number">${requirements.length}</div><div class="stat-label">Total Standards</div></div>
      <div class="stat-card"><div class="stat-number">${Object.keys(categories).length}</div><div class="stat-label">Categories</div></div>
      <div class="stat-card"><div class="stat-number">${usCount}</div><div class="stat-label">US Standards</div></div>
      <div class="stat-card"><div class="stat-number">${intlCount}</div><div class="stat-label">International</div></div>
    `;

    const blob = new Blob([JSON.stringify(requirements, null, 2)], { type: 'application/json' });
    const dlBtn = document.getElementById('downloadBtn');
    dlBtn.href = URL.createObjectURL(blob);
    dlBtn.download = filename.replace(/[.](pdf|docx|xlsx)$/i, '_requirements.json');

    const container = document.getElementById('categorySections');
    container.innerHTML = '';

    Object.entries(categories).forEach(([cat, items]) => {
      const rows = items.map(item => `
        <tr>
          <td><span class="std-id">${item.standard_id || ''}</span></td>
          <td><span class="date-chip">${item.date || ''}</span></td>
          <td><span class="badge ${item.region === 'US' ? 'badge-us' : 'badge-intl'}">${item.region || ''}</span></td>
          <td style="color:#94a3b8;font-size:12px">${item.description || ''}</td>
        </tr>`).join('');

      const section = document.createElement('div');
      section.className = 'category-section';
      section.innerHTML = `
        <div class="category-header" onclick="this.parentElement.classList.toggle('collapsed')">
          <span>📁 ${cat}</span>
          <span class="cat-count">${items.length}</span>
          <span class="cat-toggle">▾</span>
        </div>
        <div class="cat-body">
          <table>
            <thead><tr><th>Standard ID</th><th>Date</th><th>Region</th><th>Description</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
      container.appendChild(section);
    });

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function showError(msg) {
    errorBox.textContent = '❌ ' + msg;
    errorBox.style.display = 'block';
  }
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/extract", methods=["POST"])
def extract():
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

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        prompt = f"""
You are a regulatory document parser for medical devices.

Extract every standard, regulation, or guidance document from the text below.
Return ONLY a valid JSON array with no preamble, explanation, or markdown fences.

Each object must have exactly these fields:
- "standard_id": the identifier (e.g. "ISO 13485", "21 CFR Part 820", "FDA Guidance 1677")
- "date": the revision or issue date as written. If marked with ** it means check website for current version — use "Current"
- "category": the section this belongs to (e.g. "Quality System Management", "Biocompatibility")
- "region": "US" or "International" based on context
- "description": a brief description of what this standard covers

Document text:
{text}
"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        requirements = json.loads(raw)

        for i, req in enumerate(requirements):
            req["id"] = i + 1

        return jsonify({
            "requirements": requirements,
            "filename": filename
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Gemini returned an invalid response. Try running again."})
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  RegCheck — Requirements Extractor")
    print("  Supports: PDF, DOCX, XLSX")
    print("=" * 50)

    if not GEMINI_API_KEY:
        print("\n  ⚠ WARNING: No API key found!")
        print("  Create a .env file with: GEMINI_API_KEY=your_key_here\n")
    else:
        print("  ✓ API key loaded from .env")

    print("\n  Open your browser to: http://localhost:5000")
    print("  Press Ctrl+C to stop the server")
    print("=" * 50 + "\n")

    app.run(debug=False, port=5000)
