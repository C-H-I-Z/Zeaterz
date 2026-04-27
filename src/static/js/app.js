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

dropZone.addEventListener('dragover', e => { 
    e.preventDefault(); dropZone.classList.add('dragover'); 
});

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

function getExt(filename) {
    return filename.split('.').pop().toLowerCase();
}

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
        }
    );
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