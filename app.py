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

import json
import os
import tempfile
import pdfplumber
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template_string
from docx import Document
from dotenv import load_dotenv
import openpyxl

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
<title>RegCheck — Rallis-Daw Consulting</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  :root {
    --navy:    #1a2f5e;
    --navy2:   #223570;
    --blue:    #2e6db4;
    --lblue:   #5ba3d9;
    --cyan:    #4dc8e8;
    --bg:      #eaf3fb;
    --white:   #ffffff;
    --text:    #1a2f5e;
    --muted:   #6b82a8;
    --border:  #c5d8ed;
    --success: #2d7a4f;
    --danger:  #c0392b;
    --font:    'Montserrat', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── PAGE WRAPPER ── */
  .page {
    min-height: 100vh;
    position: relative;
    display: flex;
    flex-direction: column;
  }

  /* ── WAVE BACKGROUND ── */
  .wave-bg {
    position: fixed;
    top: 0; right: 0;
    width: 55%;
    height: 100vh;
    pointer-events: none;
    z-index: 0;
  }

  /* ── HEADER ── */
  header {
    position: relative;
    z-index: 10;
    background: var(--white);
    padding: 16px 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    box-shadow: 0 2px 12px rgba(26,47,94,0.08);
  }

  .logo-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .logo-img {
    height: 52px;
    width: auto;
  }

  .tool-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 3px 10px;
    border: 1px solid var(--border);
    border-radius: 3px;
  }

  /* ── CONTENT AREA ── */
  .content {
    position: relative;
    z-index: 5;
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 48px 56px 60px;
    max-width: 780px;
  }

  /* ── PAGE TITLE ── */
  .page-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--blue);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .page-heading {
    font-size: 36px;
    font-weight: 800;
    color: var(--navy);
    line-height: 1.15;
    margin-bottom: 8px;
    letter-spacing: -0.01em;
  }

  .page-sub {
    font-size: 13px;
    color: var(--muted);
    font-weight: 500;
    margin-bottom: 36px;
    letter-spacing: 0.02em;
  }

  /* ── UPLOAD CARD ── */
  .upload-card {
    background: var(--navy);
    border-radius: 12px;
    padding: 28px;
    box-shadow: 0 8px 40px rgba(26,47,94,0.25);
    max-width: 460px;
  }

  .card-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--cyan);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .card-title-icon {
    width: 28px;
    height: 28px;
    background: rgba(77,200,232,0.15);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }

  /* ── DROP ZONE ── */
  .drop-zone {
    border: 2px dashed rgba(77,200,232,0.4);
    border-radius: 8px;
    padding: 40px 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    background: rgba(255,255,255,0.04);
    position: relative;
    overflow: hidden;
    margin-bottom: 16px;
  }

  .drop-zone.dragover {
    border-color: var(--cyan);
    background: rgba(77,200,232,0.08);
  }

  .drop-zone.has-file {
    border-color: var(--cyan);
    border-style: solid;
    background: rgba(77,200,232,0.06);
  }

  .drop-icon { font-size: 36px; margin-bottom: 12px; display: block; }

  .drop-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--white);
    margin-bottom: 4px;
  }

  .drop-sub {
    font-size: 11px;
    color: var(--muted);
    font-weight: 500;
    letter-spacing: 0.04em;
  }

  .file-types {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin-top: 12px;
  }

  .type-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 3px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .type-pdf  { background: rgba(192,57,43,0.2); color: #e8a09a; border: 1px solid rgba(192,57,43,0.3); }
  .type-docx { background: rgba(77,200,232,0.15); color: var(--cyan); border: 1px solid rgba(77,200,232,0.3); }
  .type-xlsx { background: rgba(45,122,79,0.2); color: #7fd4a0; border: 1px solid rgba(45,122,79,0.3); }

  .drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }

  /* ── FILE PREVIEW ── */
  .file-preview {
    display: none;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(77,200,232,0.25);
    border-radius: 6px;
    padding: 10px 14px;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 14px;
  }
  .file-preview.visible { display: flex; }
  .file-info { display: flex; align-items: center; gap: 10px; }
  .file-icon { font-size: 18px; }
  .file-name { font-size: 12px; color: var(--white); font-weight: 500; }

  .file-clear {
    background: none;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 4px;
    color: var(--muted);
    cursor: pointer;
    font-size: 11px;
    font-family: var(--font);
    padding: 3px 8px;
    transition: all 0.2s;
    font-weight: 600;
  }
  .file-clear:hover { border-color: var(--danger); color: #e8a09a; }

  /* ── SUBMIT BUTTON ── */
  .submit-wrap { display: none; }
  .submit-wrap.visible { display: block; }

  .btn-submit {
    width: 100%;
    background: var(--blue);
    border: none;
    border-radius: 6px;
    color: var(--white);
    cursor: pointer;
    font-family: var(--font);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 14px 24px;
    transition: all 0.2s;
    text-transform: uppercase;
  }
  .btn-submit:hover { background: var(--lblue); }
  .btn-submit:active { opacity: 0.9; }
  .btn-submit:disabled { opacity: 0.4; cursor: not-allowed; }

  /* ── STATUS ── */
  .status {
    display: none;
    margin-top: 14px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(77,200,232,0.2);
    border-radius: 6px;
    padding: 14px 18px;
    align-items: center;
    gap: 12px;
  }
  .status.visible { display: flex; }

  .spinner {
    width: 18px; height: 18px;
    border: 2px solid rgba(255,255,255,0.15);
    border-top-color: var(--cyan);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status-text { font-size: 12px; color: var(--muted); font-weight: 500; letter-spacing: 0.04em; }

  /* ── ERROR ── */
  .error-box {
    display: none;
    margin-top: 14px;
    background: rgba(192,57,43,0.12);
    border: 1px solid rgba(192,57,43,0.3);
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 12px;
    color: #e8a09a;
    font-weight: 500;
  }

  /* ── DISCLAIMER ── */
  .disclaimer {
    display: none;
    margin-top: 20px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(77,200,232,0.15);
    border-left: 3px solid var(--cyan);
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 10px;
    color: var(--muted);
    line-height: 1.7;
    letter-spacing: 0.03em;
    font-weight: 500;
  }

  /* ── RESULTS ── */
  #results {
    margin-top: 40px;
    display: none;
    max-width: 1100px;
  }

  .results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }

  .results-heading {
    font-size: 22px;
    font-weight: 800;
    color: var(--navy);
    letter-spacing: -0.01em;
  }

  .download-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--navy);
    border: none;
    border-radius: 6px;
    color: var(--white);
    cursor: pointer;
    font-family: var(--font);
    font-size: 11px;
    font-weight: 700;
    padding: 10px 20px;
    transition: all 0.2s;
    text-decoration: none;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .download-btn:hover { background: var(--blue); }

  /* ── STATS ── */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(26,47,94,0.06);
  }

  .stat-number {
    font-size: 34px;
    font-weight: 900;
    color: var(--navy);
    line-height: 1;
    letter-spacing: -0.02em;
  }

  .stat-label {
    font-size: 10px;
    color: var(--muted);
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
  }

  /* ── CATEGORY SECTIONS ── */
  .category-section {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(26,47,94,0.05);
  }

  .category-header {
    padding: 14px 20px;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid var(--border);
    background: #f0f6fb;
    color: var(--navy);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    transition: background 0.15s;
  }
  .category-header:hover { background: #e2eef8; }

  .cat-count {
    font-size: 10px;
    background: var(--navy);
    color: var(--white);
    border-radius: 3px;
    padding: 2px 8px;
    font-weight: 700;
    letter-spacing: 0.06em;
  }

  .cat-toggle { margin-left: auto; color: var(--muted); transition: transform 0.2s; }
  .category-section.collapsed .cat-toggle { transform: rotate(-90deg); }
  .category-section.collapsed .cat-body { display: none; }

  table { width: 100%; border-collapse: collapse; }

  th {
    text-align: left;
    padding: 10px 16px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    background: #f7fafd;
    border-bottom: 1px solid var(--border);
    font-weight: 700;
  }

  td {
    padding: 12px 16px;
    font-size: 12px;
    border-bottom: 1px solid #edf3f8;
    vertical-align: top;
    line-height: 1.5;
    color: var(--text);
  }

  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f7fafd; }

  .std-id { font-weight: 700; color: var(--navy); font-size: 12px; }

  .date-chip {
    font-size: 11px;
    background: #e8f1fa;
    color: var(--blue);
    padding: 3px 8px;
    border-radius: 3px;
    white-space: nowrap;
    font-weight: 600;
    border: 1px solid var(--border);
  }

  .badge {
    font-size: 10px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 3px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .badge-us   { background: rgba(26,47,94,0.08); color: var(--navy); border: 1px solid rgba(26,47,94,0.15); }
  .badge-intl { background: rgba(45,122,79,0.08); color: var(--success); border: 1px solid rgba(45,122,79,0.2); }

  /* ── FOOTER ── */
  footer {
    position: relative;
    z-index: 5;
    background: var(--navy);
    padding: 14px 56px;
    text-align: center;
    font-size: 10px;
    color: rgba(255,255,255,0.4);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500;
    margin-top: auto;
  }
</style>
</head>
<body>
<div class="page">

  <!-- WAVE BACKGROUND SVG -->
  <svg class="wave-bg" viewBox="0 0 600 900" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="wave1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#5ba3d9;stop-opacity:0.5"/>
        <stop offset="100%" style="stop-color:#2e6db4;stop-opacity:0.3"/>
      </linearGradient>
      <linearGradient id="wave2" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#4dc8e8;stop-opacity:0.4"/>
        <stop offset="100%" style="stop-color:#5ba3d9;stop-opacity:0.2"/>
      </linearGradient>
      <linearGradient id="wave3" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#7b68ee;stop-opacity:0.3"/>
        <stop offset="100%" style="stop-color:#2e6db4;stop-opacity:0.15"/>
      </linearGradient>
    </defs>
    <!-- Back wave -->
    <path d="M600,0 L600,900 L0,900 Q150,700 300,600 Q450,500 600,300 Z" fill="url(#wave3)" opacity="0.5"/>
    <!-- Mid wave -->
    <path d="M600,0 L600,900 L100,900 Q200,750 350,650 Q500,550 600,350 Z" fill="url(#wave1)" opacity="0.6"/>
    <!-- Front wave -->
    <path d="M600,200 Q500,350 400,450 Q300,550 250,700 Q200,800 300,900 L600,900 Z" fill="url(#wave2)" opacity="0.7"/>
    <!-- Small accent blob -->
    <ellipse cx="500" cy="200" rx="120" ry="80" fill="#4dc8e8" opacity="0.15" transform="rotate(-20 500 200)"/>
  </svg>

  <!-- HEADER -->
  <header>
    <div class="logo-wrap">
      <img
        class="logo-img"
        src="https://static.wixstatic.com/media/9f2dc8_980147f3f25a4e50a2220ab0bd98dba8~mv2.png/v1/fill/w_129,h_128,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Sig%20logo.png"
        alt="Rallis-Daw Consulting"
      >
    </div>
    <div class="tool-label">RegCheck — Prototype v0.1</div>
  </header>

  <!-- CONTENT -->
  <div class="content">

    <div class="page-title">Regulatory Standards</div>
    <div class="page-heading">External Documents<br>Checker</div>
    <div class="page-sub">Upload a device requirements file to extract and review all regulatory standards</div>

    <!-- UPLOAD CARD -->
    <div class="upload-card">

      <div class="card-title">
        <div class="card-title-icon">📋</div>
        Document Upload
      </div>

      <div class="drop-zone" id="dropZone">
        <input type="file" id="fileInput" accept=".pdf,.docx,.xlsx">
        <span class="drop-icon" id="dropIcon">☁️</span>
        <div class="drop-title" id="dropTitle">Drag & Drop or Upload a File</div>
        <div class="drop-sub" id="dropSub">Click anywhere in this box to browse</div>
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
          Extract Requirements
        </button>
      </div>

      <div class="status" id="status">
        <div class="spinner"></div>
        <div class="status-text" id="statusText">Sending to Gemini AI — this may take 15–30 seconds...</div>
      </div>

      <div class="error-box" id="errorBox"></div>

      <div class="disclaimer" id="disclaimer">
        ⚠ AI DISCLAIMER — This extraction is intended solely to assist regulatory review.
        All results must be verified by a qualified professional before use in any compliance submission.
      </div>

    </div>
    <!-- END UPLOAD CARD -->

    <!-- RESULTS -->
    <div id="results">
      <div class="results-header">
        <div class="results-heading">Extraction Results</div>
        <a class="download-btn" id="downloadBtn" href="#">⬇ Download JSON</a>
      </div>
      <div class="stats-row" id="statsRow"></div>
      <div id="categorySections"></div>
    </div>

  </div>
  <!-- END CONTENT -->

  <!-- FOOTER -->
  <footer>
    © Rallis-Daw Consulting LLC &nbsp;·&nbsp; RegCheck Tool &nbsp;·&nbsp; For internal use only
  </footer>

</div>

<script>
  const dropZone    = document.getElementById('dropZone');
  const fileInput   = document.getElementById('fileInput');
  const filePreview = document.getElementById('filePreview');
  const fileName    = document.getElementById('fileName');
  const submitWrap  = document.getElementById('submitWrap');
  const submitBtn   = document.getElementById('submitBtn');
  const status      = document.getElementById('status');
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
    document.getElementById('dropIcon').textContent = '☁️';
    document.getElementById('dropTitle').textContent = 'Drag & Drop or Upload a File';
    document.getElementById('dropSub').textContent = 'Click anywhere in this box to browse';
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
        submitBtn.textContent = 'Extract Requirements';
        if (data.error) { showError(data.error); return; }
        renderResults(data.requirements, data.filename);
      })
      .catch(err => {
        status.classList.remove('visible');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Extract Requirements';
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
          <td style="font-size:12px;color:#4a5568">${item.description || ''}</td>
        </tr>`).join('');

      const section = document.createElement('div');
      section.className = 'category-section';
      section.innerHTML = `
        <div class="category-header" onclick="this.parentElement.classList.toggle('collapsed')">
          <span>${cat}</span>
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
    print("  RegCheck — Rallis-Daw Consulting")
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