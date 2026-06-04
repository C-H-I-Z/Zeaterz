/**
 * upload.js — File upload page interactions for Sota.
 *
 * Responsibilities:
 *   1. On load, probe /api/status to show whether Gemini is reachable and
 *      which features (parsing, web search) are available.
 *   2. Show the disclaimer overlay on first visit; gate further interaction
 *      until the user acknowledges it.
 *   3. Handle drag-and-drop and click-to-browse file selection.
 *   4. On submit, POST the file to /extract, display a live parse timer,
 *      then store the returned requirements in sessionStorage and navigate
 *      to /review.
 */

// ── AI STATUS CHECK ───────────────────────────────────────────────────────────

/**
 * Probe /api/status and render the AI readiness bar at the top of the upload card.
 * Three visual states: green dot (ready), red dot (not configured), orange dot (error).
 * Runs immediately on page load so the user knows if the API key is valid
 * before they spend time selecting a file.
 */
(function checkAiStatus() {
    var dot   = document.getElementById('aiStatusDot');
    var label = document.getElementById('aiStatusLabel');
    var meta  = document.getElementById('aiStatusMeta');

    dot.className   = 'ai-status-dot dot-checking';
    label.textContent = 'Checking AI status…';

    fetch('/api/status')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'ready') {
                dot.className   = 'ai-status-dot dot-ready';
                label.innerHTML = '<strong>' + data.model + '</strong>';
                meta.innerHTML  = data.features.map(function(f) {
                    return '<span class="ai-status-chip">'
                         + '<span class="chip-check">&#10003;</span>'
                         + f
                         + '<span class="chip-ready">Ready</span>'
                         + '</span>';
                }).join('');
            } else if (data.status === 'not_configured') {
                dot.className     = 'ai-status-dot dot-error';
                label.innerHTML   = '<strong>Not Configured</strong> &mdash; ' + data.message;
                meta.innerHTML    = '<span class="ai-status-chip chip-warn">Add GEMINI_API_KEY to .env</span>';
            } else {
                dot.className     = 'ai-status-dot dot-warn';
                label.innerHTML   = '<strong>Cannot Connect</strong> &mdash; ' + data.message;
                meta.innerHTML    = '<span class="ai-status-chip chip-warn">Check network or API key</span>';
            }
        })
        .catch(function() {
            dot.className   = 'ai-status-dot dot-warn';
            label.textContent = 'Status check failed — server may be starting up';
        });
})();

// ── DISCLAIMER ────────────────────────────────────────────────────────────────

/**
 * Show the AI disclaimer overlay on first visit.
 * Once the user accepts, the flag is stored in sessionStorage so it won't
 * reappear on the same browser tab during the session.
 */
(function initDisclaimer() {
    if (!sessionStorage.getItem('sota_disclaimer_accepted')) {
        document.getElementById('disclaimerOverlay').classList.add('visible');
    }
})();

/** Enable/disable the Proceed button based on whether the checkbox is ticked. */
function onDisclaimerCheck() {
    var checked = document.getElementById('disclaimerCheck').checked;
    document.getElementById('disclaimerProceedBtn').disabled = !checked;
}

/** Record disclaimer acceptance and dismiss the overlay. */
function acceptDisclaimer() {
    sessionStorage.setItem('sota_disclaimer_accepted', 'true');
    document.getElementById('disclaimerOverlay').classList.remove('visible');
}

// ── UPLOAD ────────────────────────────────────────────────────────────────────

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

/**
 * Accept a validated File object, update the drop-zone UI to show the filename,
 * and reveal the submit button.
 *
 * @param {File} file - The selected file (already validated as PDF/DOCX/XLSX).
 */
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

/** Reset the drop zone to its empty state so the user can pick a different file. */
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

/**
 * Upload the selected file to /extract, run a live parse timer while waiting,
 * then store the results in sessionStorage and navigate to /review.
 * Elapsed time is also stored so the review page can display "parsed in Xs".
 */
function submitFile() {
    if (!selectedFile) return;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing…';
    errorBox.style.display = 'none';
    statusBox.classList.add('visible');

    var parseStart   = Date.now();
    var timerEl      = document.getElementById('parseTimer');
    // Live clock so the user can see the parse is still running
    var parseTimerInterval = setInterval(function() {
        var s = Math.floor((Date.now() - parseStart) / 1000);
        var m = Math.floor(s / 60);
        timerEl.textContent = m + ':' + (s % 60 < 10 ? '0' : '') + (s % 60);
    }, 1000);

    var formData = new FormData();
    formData.append('file', selectedFile);

    fetch('/extract', { method: 'POST', body: formData })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            clearInterval(parseTimerInterval);
            statusBox.classList.remove('visible');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Extract Requirements';

            if (data.error) { showError(data.error); return; }

            // Store in sessionStorage and navigate to review page
            var parseElapsed = Date.now() - parseStart;
            sessionStorage.setItem('sota_requirements',    JSON.stringify(data.requirements));
            sessionStorage.setItem('sota_filename',         data.filename);
            sessionStorage.setItem('sota_extract_tokens',  JSON.stringify(data.tokens));
            sessionStorage.setItem('sota_extract_cost',    data.cost);
            sessionStorage.setItem('sota_parse_elapsed',   parseElapsed);

            disclaimer.style.display = 'block';
            window.location.href = '/review';
        })
        .catch(function(err) {
            clearInterval(parseTimerInterval);
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