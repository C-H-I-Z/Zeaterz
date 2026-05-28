var dropZone   = document.getElementById('dropZone');
var fileInput  = document.getElementById('fileInput');
var filePreview = document.getElementById('filePreview');
var submitWrap = document.getElementById('submitWrap');
var submitBtn  = document.getElementById('submitBtn');
var statusBox  = document.getElementById('statusBox');
var errorBox   = document.getElementById('errorBox');
var disclaimer = document.getElementById('disclaimer');

var selectedFile = null;
var ALLOWED    = ['pdf', 'docx', 'xlsx'];
var FILE_ICONS = { pdf: '&#128212;', docx: '&#128216;', xlsx: '&#128218;' };

function getExt(name) { return name.split('.').pop().toLowerCase(); }

dropZone.addEventListener('dragover', function(e) { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', function()  { dropZone.classList.remove('dragover'); });
dropZone.addEventListener('drop', function(e) {
    e.preventDefault(); dropZone.classList.remove('dragover');
    var f = e.dataTransfer.files[0];
    if (f && ALLOWED.indexOf(getExt(f.name)) !== -1) setFile(f);
    else showError('Please drop a PDF, DOCX, or XLSX file.');
    });

    fileInput.addEventListener('change', function() {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
    selectedFile = file;
    var ext = getExt(file.name);
    dropZone.classList.add('has-file');

    document.getElementById('dropIcon').innerHTML  = '&#10003;';
    document.getElementById('dropTitle').textContent = 'File ready';
    document.getElementById('dropSub').textContent   = 'Drop a different file to replace it';
    document.getElementById('fileTypeIcon').innerHTML = FILE_ICONS[ext] || '&#128196;';
    document.getElementById('fileName').textContent   = file.name;

    filePreview.classList.add('visible');
    submitWrap.classList.add('visible');
    errorBox.style.display = 'none';
    disclaimer.style.display = 'none';
}

function clearFile() {
    selectedFile = null;
    fileInput.value = '';
    dropZone.classList.remove('has-file');

    document.getElementById('dropIcon').innerHTML    = '&#9729;';
    document.getElementById('dropTitle').textContent = 'Drag & Drop or Upload a File';
    document.getElementById('dropSub').textContent   = 'Click anywhere in this box to browse';

    filePreview.classList.remove('visible');
    submitWrap.classList.remove('visible');
    errorBox.style.display = 'none';
}

function submitFile() {
    if (!selectedFile) return;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing…';
    errorBox.style.display = 'none';
    statusBox.classList.add('visible');

    var formData = new FormData();
    formData.append('file', selectedFile);

    fetch('/extract', { method: 'POST', body: formData })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            statusBox.classList.remove('visible');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Extract Requirements';

            if (data.error) { showError(data.error); return; }

            // Store in sessionStorage and navigate to review page
            sessionStorage.setItem('sota_requirements',    JSON.stringify(data.requirements));
            sessionStorage.setItem('sota_filename',         data.filename);
            sessionStorage.setItem('sota_extract_tokens',  JSON.stringify(data.tokens));
            sessionStorage.setItem('sota_extract_cost',    data.cost);

            disclaimer.style.display = 'block';
            window.location.href = '/review';
        })
        .catch(function(err) {
            statusBox.classList.remove('visible');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Extract Requirements';
            showError('Server error: ' + err.message);
        });
}

function showError(msg) {
    errorBox.textContent = 'Error: ' + msg;
    errorBox.style.display = 'block';
}