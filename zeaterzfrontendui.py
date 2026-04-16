"""
Medical Device Requirements Extractor - Local Web App
------------------------------------------------------
Runs a local web server with a drag-and-drop interface.

SETUP:
    pip install flask google-generativeai pdfplumber

RUN:
    python app.py

You will be asked to paste your Gemini API key when the app starts.
Then open your browser to: http://localhost:5000
"""

import json
import os
import tempfile
import pdfplumber
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template_string

GEMINI_MODEL = "gemini-2.5-flash"

app = Flask(__name__)

# Will be set at startup
GEMINI_API_KEY = None


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SOTA — Requirements Extractor</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-top: #edf4ff;
    --bg-bottom: #d6dcff;
    --panel: #2f4da8;
    --panel-dark: #27449a;
    --panel-soft: #39c3e6;
    --panel-soft-2: #5bd3eb;
    --card: #f6f8ff;
    --line: rgba(10, 37, 98, 0.14);
    --text: #173164;
    --muted: #6e84b1;
    --white: #ffffff;
    --upload-bg: linear-gradient(180deg, #35c4e4 0%, #2caed5 100%);
    --success: #16c25f;
    --warning: #f59e0b;
    --danger: #ef4444;
    --shadow-xl: 0 22px 50px rgba(40, 54, 120, 0.22);
    --shadow-md: 0 10px 24px rgba(40, 54, 120, 0.16);
    --radius-xl: 24px;
    --radius-lg: 18px;
    --radius-md: 14px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    min-height: 100vh;
    font-family: 'Inter', sans-serif;
    color: var(--text);
    background:
      radial-gradient(circle at 0% 100%, rgba(119,177,255,0.2), transparent 28%),
      radial-gradient(circle at 100% 80%, rgba(84,132,255,0.22), transparent 32%),
      linear-gradient(180deg, var(--bg-top) 0%, #e8f1ff 35%, var(--bg-bottom) 100%);
    padding: 28px;
  }

  .shell {
    max-width: 1280px;
    margin: 0 auto;
    background: rgba(255,255,255,0.32);
    backdrop-filter: blur(4px);
    border-radius: 18px;
    box-shadow: 0 16px 42px rgba(35, 44, 99, 0.18);
    padding: 20px 22px 28px;
  }

  .browser-bar {
    height: 26px;
    border-radius: 12px 12px 0 0;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #9aa8c7;
    font-size: 12px;
    margin-bottom: 16px;
  }

  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  .dot.red { background: #ff5f57; }
  .dot.yellow { background: #febc2e; }
  .dot.green { background: #28c840; }

  .frame {
    position: relative;
    border-radius: 16px;
    overflow: hidden;
    min-height: 760px;
    background:
      linear-gradient(135deg, rgba(255,255,255,0.55), rgba(255,255,255,0.18)),
      linear-gradient(180deg, #eef5ff 0%, #dde6ff 100%);
    border: 1px solid rgba(255,255,255,0.35);
    padding: 28px;
  }

  .frame::before {
    content: '';
    position: absolute;
    left: -40px;
    bottom: 90px;
    width: 250px;
    height: 250px;
    background: radial-gradient(circle, rgba(63, 184, 255, 0.28), transparent 68%);
    pointer-events: none;
  }

  .frame::after {
    content: '';
    position: absolute;
    right: -70px;
    top: 260px;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(82, 119, 255, 0.24), transparent 68%);
    pointer-events: none;
  }
 
   .right-column {
  margin-top: 82px;
  }


  .layout {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
    align-items: stretch;
  }

  .brand-column {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding-top: 22px;
  }

  .brand-box {
    background: transparent;
    min-height: 92px;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 8px 10px;
  }

  .brand-mark {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: conic-gradient(from 200deg, #6f85ff, #2f4da8 40%, #57d7ef 75%, #ffffff 76%, #ffffff 100%);
    position: relative;
    box-shadow: inset 0 0 0 8px #ffffff;
  }

  .brand-mark::after {
    content: '';
    position: absolute;
    inset: 16px;
    border-radius: 50%;
    background: linear-gradient(180deg, #ffffff, #e8efff);
  }

  .brand-text {
    font-weight: 800;
    font-size: 17px;
    line-height: 1.05;
    color: #264587;
    letter-spacing: 0.02em;
  }

  .control-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
  }

  .pill-btn {
    border: none;
    border-radius: 12px;
    background: linear-gradient(180deg, #43c8e8, #2fb5d9);
    color: white;
    font-weight: 700;
    font-size: 18px;
    padding: 12px 10px;
    box-shadow: var(--shadow-md);
    cursor: pointer;
  }

  .card {
    background: linear-gradient(180deg, var(--panel) 0%, var(--panel-dark) 100%);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xl);
  }

  .upload-card {
    padding: 20px;
    height: 100%;
  }

  .section-title {
    display: block;
    background: linear-gradient(180deg, #39c4e6, #2eb6d9);
    color: white;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 18px;
    text-align: center;
    border-radius: 12px;
    padding: 5px 15px;
    width: fit-content;
    margin: 0 auto;
    margin-top: -15px;
    letter-spacing: 0.01em;
  }

  .upload-inner {
    background: var(--upload-bg);
    border-radius: 18px;
    padding: 22px 20px 26px;
    min-height: 360px;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
  }

  .upload-copy {
    color: rgba(255,255,255,0.85);
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 16px;
  }

  .drop-zone {
    width: 100%;
    max-width: 500px;
    min-height: 360px;
    border: 2px dashed rgba(255,255,255,0.35);
    border-radius: 12px;
    background: rgba(255,255,255,0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px 18px;
    position: relative;
    transition: transform 0.18s, border-color 0.18s, background 0.18s;
    cursor: pointer;
  }

  .drop-zone:hover {
    transform: translateY(-1px);
    background: rgba(255,255,255,0.12);
  }

  .drop-zone.dragover {
    border-color: rgba(255,255,255,0.8);
    background: rgba(255,255,255,0.16);
  }

  .drop-zone.has-file {
    border-color: rgba(255,255,255,0.92);
    background: rgba(255,255,255,0.18);
  }

  .drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
  }

  .drop-icon {
    font-size: 28px;
    margin-bottom: 10px;
    color: white;
  }

  .drop-title {
    color: white;
    font-weight: 800;
    font-size: 26px;
    margin-bottom: 8px;
  }

  .drop-sub {
    color: rgba(255,255,255,0.82);
    font-size: 16px;
    line-height: 1.45;
  }

  .file-preview {
    width: 100%;
    display: none;
    margin-top: 16px;
    background: rgba(255,255,255,0.16);
    border: 1px solid rgba(255,255,255,0.28);
    border-radius: 12px;
    padding: 10px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    color: white;
  }

  .file-preview.visible { display: flex; }

  .file-info { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .file-icon { font-size: 18px; }
  .file-name {
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 145px;
  }

  .file-clear {
    border: none;
    background: rgba(255,255,255,0.9);
    color: #29518d;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }

  .submit-wrap {
    display: none;
    margin-top: 14px;
    width: 100%;
    justify-content: center;
  }

  .submit-wrap.visible { display: flex; }

  .btn-submit {
    border: none;
    background: linear-gradient(180deg, #ffffff 0%, #f3f6fb 100%);
    color: #4e6a98;
    border-radius: 9px;
    font-weight: 700;
    font-size: 13px;
    min-width: 122px;
    padding: 10px 18px;
    box-shadow: 0 7px 12px rgba(27, 48, 96, 0.18);
    cursor: pointer;
  }

  .btn-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .right-column {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .top-panel {
    display: flex;
    justify-content:flex-start;
  }

  .key-card {
    background: linear-gradient(180deg, #ffffff 0%, #f4f7ff 100%);
    border-radius: 18px;
    width: 60%;
    margin-left: 105px;
    padding: 16px 18px 14px;
    box-shadow: 0 14px 26px rgba(42, 65, 136, 0.16);
    border: 1px solid rgba(36, 67, 136, 0.1);
  }

  .key-title {
    font-size: 13px;
    font-weight: 800;
    color: #2f3c66;
    margin-bottom: 12px;
  }

  .key-grid {
    display: flex;
    justify-content: space-between;
  }

  .key-label {
    font-size: 10px;
    font-weight: 700;
    color: #384b7a;
    margin-bottom: 7px;
  }

  .key-pill {
    width: 42px;
    height: 16px;
    border-radius: 999px;
    margin: 0 auto;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 5px 10px rgba(0,0,0,0.08);
  }

  .green { background: #21df29; }
  .orange { background: #ff9315; }
  .red { background: #ff2323; }

  .status-shell {
  height: 100%;
    background: linear-gradient(180deg, var(--panel) 0%, var(--panel-dark) 100%);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xl);
    padding: 28px 26px 34px;
    min-height: 340px;
    display: flex;
    align-items: center;
    justify-content:center;
  }

  .status-board {
    width: 100%;
    max-width: 460px;
    min-height: 460px;
    background: linear-gradient(180deg, #ffffff 0%, #edf3ff 100%);
    border-radius: 14px;
    padding: 18px 18px 20px;
    box-shadow: inset 0 0 0 1px rgba(58, 83, 153, 0.12);
      display: flex;
      flex-direction: column;
  }

  .status-logo {
    font-family: 'Syne', sans-serif;
    font-size: 40px;
    line-height: 1;
    font-weight: 800;
    text-align: center;
    margin-bottom: 16px;
    color: #1f78ff;
    text-shadow: 0 8px 18px rgba(31, 120, 255, 0.22);
    letter-spacing: 0.03em;
  }

  .status-panel {
    border-radius: 12px;
    background: linear-gradient(180deg, #bdd5ff 0%, #9fbeff 100%);
    padding: 16px 16px 10px;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.34);
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 7px;
    color: rgba(255,255,255,0.92);
    font-size: 15px;
    font-weight: 350;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    opacity: 0.7;
  }

  .status-item:last-child { border-bottom: none; }

  .status-bullet {
    width: 13px;
    height: 13px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.25);
    color: white;
    font-size: 10px;
    flex-shrink: 0;
  }

  .status-item.active {
    opacity: 1;
    font-weight: 700;
  }

  .status-item.active .status-bullet {
    background: rgba(255,255,255,0.36);
    box-shadow: 0 0 0 4px rgba(255,255,255,0.08);
  }

  .status-item.done {
    opacity: 1;
  }

  .status-item.done .status-bullet {
    background: rgba(22, 194, 95, 0.95);
  }

  .status-line {
    margin-top: 12px;
    color: rgba(255,255,255,0.88);
    font-size: 14px;
    min-height: 16px;
  }

  .error-box {
    display: none;
    margin-top: 18px;
    background: rgba(255,255,255,0.94);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 12px;
    padding: 14px 16px;
    color: #bd2e2e;
    font-size: 13px;
    font-weight: 600;
    box-shadow: 0 8px 18px rgba(50, 60, 110, 0.1);
  }

  .disclaimer {
    display: none;
    margin-top: 22px;
    background: rgba(255,255,255,0.88);
    border: 1px solid rgba(245,158,11,0.25);
    border-radius: 14px;
    padding: 14px 16px;
    color: #926017;
    font-size: 12px;
    line-height: 1.55;
  }

  #results {
    margin-top: 26px;
    display: none;
    background: rgba(255,255,255,0.74);
    border-radius: 22px;
    padding: 22px;
    box-shadow: 0 18px 36px rgba(38, 58, 130, 0.14);
  }

  .results-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }

  .results-title {
    font-family: 'Syne', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: #29498f;
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: linear-gradient(180deg, #ffffff 0%, #f2f6ff 100%);
    border: 1px solid rgba(41, 73, 143, 0.09);
    border-radius: 16px;
    padding: 16px 18px;
    text-align: center;
    box-shadow: 0 10px 18px rgba(56, 79, 156, 0.08);
  }

  .stat-number {
    font-size: 30px;
    font-weight: 800;
    color: #2d59b7;
    line-height: 1;
  }

  .stat-label {
    font-size: 11px;
    color: #7389b0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 6px;
    font-weight: 700;
  }

  .download-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(180deg, #39c4e6, #2fb6d8);
    color: white;
    text-decoration: none;
    border-radius: 11px;
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
    box-shadow: 0 10px 18px rgba(47, 182, 216, 0.22);
  }

  .category-section {
    background: linear-gradient(180deg, #ffffff 0%, #f7f9ff 100%);
    border: 1px solid rgba(41,73,143,0.08);
    border-radius: 16px;
    margin-bottom: 14px;
    overflow: hidden;
  }

  .category-header {
    padding: 15px 18px;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    color: #2e4f94;
    font-weight: 800;
    font-size: 14px;
    background: rgba(78, 142, 255, 0.04);
  }

  .category-header:hover {
    background: rgba(78, 142, 255, 0.07);
  }

  .cat-count {
    margin-left: 2px;
    background: rgba(47, 182, 216, 0.12);
    color: #2588a2;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
  }

  .cat-toggle {
    margin-left: auto;
    color: #7a8fb9;
    transition: transform 0.18s ease;
  }

  .category-section.collapsed .cat-toggle { transform: rotate(-90deg); }
  .category-section.collapsed .cat-body { display: none; }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th {
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7286ad;
    padding: 12px 16px;
    background: rgba(234, 241, 255, 0.9);
  }

  td {
    padding: 12px 16px;
    font-size: 13px;
    color: #314d82;
    border-top: 1px solid rgba(41,73,143,0.08);
    vertical-align: top;
  }

  .std-id {
    font-weight: 800;
    color: #2b63d0;
  }

  .date-chip {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 999px;
    background: rgba(103, 85, 215, 0.12);
    color: #614eb8;
    font-size: 11px;
    font-weight: 700;
  }

  .badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.05em;
  }

  .badge-us {
    background: rgba(45, 99, 208, 0.12);
    color: #2d63d0;
  }

  .badge-intl {
    background: rgba(22, 194, 95, 0.12);
    color: #14974b;
  }

  @media (max-width: 1100px) {
    .layout { grid-template-columns: 1fr; }
    .brand-column { order: 1; }
    .right-column { order: 2; }
    .top-panel { grid-template-columns: 1fr; }
  }

  @media (max-width: 760px) {
    body { padding: 12px; }
    .frame { padding: 16px; }
    .control-row { grid-template-columns: 1fr; }
    .stats-row { grid-template-columns: 1fr 1fr; }
  }

  @media (max-width: 560px) {
    .stats-row { grid-template-columns: 1fr; }
    th:nth-child(2), td:nth-child(2),
    th:nth-child(3), td:nth-child(3) { display: none; }
  }
</style>
</head>
<body>
  <div class="shell">
    <div class="browser-bar">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>

    <div class="frame">
      <div class="layout">
        <div class="brand-column">
          <div class="brand-box">
            <div class="brand-mark"></div>
            <div class="brand-text">RALLIS-DAW<br>CONSULTING</div>
          </div>

          <div class="control-row">
            <button class="pill-btn" type="button">About</button>
            <button class="pill-btn" type="button">Help ⓘ</button>
          </div>

          <div class="card upload-card">
            <div class="section-title">Document Upload</div>

            <div class="upload-inner">
              <div class="upload-copy">Drag & Drop OR Upload a PDF</div>

              <div class="drop-zone" id="dropZone">
                <input type="file" id="fileInput" accept=".pdf">
                <div class="drop-icon" id="dropIcon">📄</div>
                <div class="drop-title" id="dropTitle">Drop your PDF here</div>
                <div class="drop-sub" id="dropSub">Click to browse or drag a file into this box.</div>
              </div>

              <div class="file-preview" id="filePreview">
                <div class="file-info">
                  <span class="file-icon">📎</span>
                  <span class="file-name" id="fileName"></span>
                </div>
                <button class="file-clear" onclick="clearFile()">Remove</button>
              </div>

              <div class="submit-wrap" id="submitWrap">
                <button class="btn-submit" id="submitBtn" onclick="submitFile()">Upload PDF</button>
              </div>
            </div>

            <div class="error-box" id="errorBox"></div>
          </div>
        </div>

        <div class="right-column">
          <div class="top-panel">
            <div></div>

            <div class="key-card">
              <div class="key-title">Change Key</div>
              <div class="key-grid">
                <div>
                  <div class="key-label">Unchanged</div>
                  <div class="key-pill green"></div>
                </div>
                <div>
                  <div class="key-label">Revised</div>
                  <div class="key-pill orange"></div>
                </div>
                <div>
                  <div class="key-label">New</div>
                  <div class="key-pill red"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="status-shell">
            <div class="status-board">
              <div class="status-logo">SOTA</div>
              <div class="status-panel">
                <div class="status-item" id="stepUpload">
                  <span class="status-bullet">⌛</span>
                  <span>Uploading document...</span>
                </div>
                <div class="status-item" id="stepExtract">
                  <span class="status-bullet">⌛</span>
                  <span>Extracting regulatory references...</span>
                </div>
                <div class="status-item" id="stepCompare">
                  <span class="status-bullet">⌛</span>
                  <span>Comparing with regulatory database...</span>
                </div>
                <div class="status-item" id="stepNotify">
                  <span class="status-bullet">⌛</span>
                  <span>Generating change notifications...</span>
                </div>
                <div class="status-line" id="statusText">Waiting for document upload.</div>
              </div>
            </div>
          </div>

          <div class="disclaimer" id="disclaimer">
            ⚠ AI DISCLAIMER: This extraction was performed by an AI model and is intended to assist regulatory review only.
            All results should be independently verified by a qualified regulatory professional before any compliance or submission use.
          </div>

          <div id="results">
            <div class="results-head">
              <div class="results-title">Extracted Requirements</div>
              <a class="download-btn" id="downloadBtn" href="#">⬇ Download JSON</a>
            </div>
            <div class="stats-row" id="statsRow"></div>
            <div id="categorySections"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
  const dropZone    = document.getElementById('dropZone');
  const fileInput   = document.getElementById('fileInput');
  const filePreview = document.getElementById('filePreview');
  const fileName    = document.getElementById('fileName');
  const submitWrap  = document.getElementById('submitWrap');
  const submitBtn   = document.getElementById('submitBtn');
  const results     = document.getElementById('results');
  const errorBox    = document.getElementById('errorBox');
  const disclaimer  = document.getElementById('disclaimer');
  const statusText  = document.getElementById('statusText');

  const stepUpload  = document.getElementById('stepUpload');
  const stepExtract = document.getElementById('stepExtract');
  const stepCompare = document.getElementById('stepCompare');
  const stepNotify  = document.getElementById('stepNotify');

  let selectedFile = null;

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      setFile(file);
    } else {
      showError('Please drop a PDF file.');
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function resetSteps() {
    [stepUpload, stepExtract, stepCompare, stepNotify].forEach(step => {
      step.classList.remove('active', 'done');
      step.querySelector('.status-bullet').textContent = '⌛';
    });
  }

  function markActive(step, message) {
    step.classList.add('active');
    step.querySelector('.status-bullet').textContent = '⌛';
    statusText.textContent = message;
  }

  function markDone(step) {
    step.classList.remove('active');
    step.classList.add('done');
    step.querySelector('.status-bullet').textContent = '✓';
  }

  function setFile(file) {
    selectedFile = file;
    dropZone.classList.add('has-file');
    document.getElementById('dropIcon').textContent = '✓';
    document.getElementById('dropTitle').textContent = 'File ready';
    document.getElementById('dropSub').textContent = 'Your PDF is ready to upload.';
    fileName.textContent = file.name;
    filePreview.classList.add('visible');
    submitWrap.classList.add('visible');
    errorBox.style.display = 'none';
    results.style.display = 'none';
    disclaimer.style.display = 'none';

    resetSteps();
    markDone(stepUpload);
    statusText.textContent = 'Document loaded. Ready to begin extraction.';
  }

  function clearFile() {
    selectedFile = null;
    fileInput.value = '';
    dropZone.classList.remove('has-file');
    document.getElementById('dropIcon').textContent = '📄';
    document.getElementById('dropTitle').textContent = 'Drop your PDF here';
    document.getElementById('dropSub').textContent = 'Click to browse or drag a file into this box.';
    filePreview.classList.remove('visible');
    submitWrap.classList.remove('visible');
    errorBox.style.display = 'none';
    results.style.display = 'none';
    disclaimer.style.display = 'none';
    resetSteps();
    statusText.textContent = 'Waiting for document upload.';
  }

  function submitFile() {
    if (!selectedFile) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    errorBox.style.display = 'none';
    results.style.display = 'none';
    disclaimer.style.display = 'none';

    resetSteps();
    markDone(stepUpload);
    markActive(stepExtract, 'Extracting regulatory references...');

    const formData = new FormData();
    formData.append('pdf', selectedFile);

    fetch('/extract', { method: 'POST', body: formData })
      .then(r => r.json())
      .then(data => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload PDF';

        if (data.error) {
          showError(data.error);
          resetSteps();
          markDone(stepUpload);
          statusText.textContent = 'Upload completed, but extraction failed.';
          return;
        }

        markDone(stepExtract);
        markActive(stepCompare, 'Comparing extracted requirements...');
        setTimeout(() => {
          markDone(stepCompare);
          markActive(stepNotify, 'Generating change notifications...');
          setTimeout(() => {
            markDone(stepNotify);
            statusText.textContent = 'Processing complete.';
            renderResults(data.requirements, data.filename);
          }, 450);
        }, 450);
      })
      .catch(err => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload PDF';
        showError('Server error: ' + err.message);
        resetSteps();
        markDone(stepUpload);
        statusText.textContent = 'Upload completed, but processing failed.';
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
    dlBtn.download = filename.replace('.pdf', '_requirements.json');

    const container = document.getElementById('categorySections');
    container.innerHTML = '';

    Object.entries(categories).forEach(([cat, items]) => {
      const rows = items.map(item => `
        <tr>
          <td><span class="std-id">${item.standard_id || ''}</span></td>
          <td><span class="date-chip">${item.date || ''}</span></td>
          <td><span class="badge ${item.region === 'US' ? 'badge-us' : 'badge-intl'}">${item.region || ''}</span></td>
          <td>${item.description || ''}</td>
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
            <thead>
              <tr>
                <th>Standard ID</th>
                <th>Date</th>
                <th>Region</th>
                <th>Description</th>
              </tr>
            </thead>
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
        return jsonify({"error": "No API key set. Restart the app and paste your key when prompted."})

    pdf_file = request.files.get("pdf")
    if not pdf_file:
        return jsonify({"error": "No PDF file received."})

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return jsonify({"error": "Could not extract text from PDF."})

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
            "filename": pdf_file.filename
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
    print("=" * 50)

    GEMINI_API_KEY = input("\n  Paste your Gemini API key: ").strip()

    if not GEMINI_API_KEY:
        print("\n  ⚠ No API key entered. Extractions will fail.")
    else:
        print("  ✓ API key set")

    print("\n  Open your browser to: http://localhost:5000")
    print("  Press Ctrl+C to stop the server")
    print("=" * 50 + "\n")

    app.run(debug=False, port=5000)
