// ── STATE ─────────────────────────────────────────────────────────────────────

var currentData  = [];
var editingIndex = null;
var currentFilename = '';

// ── INIT ──────────────────────────────────────────────────────────────────────

(function init() {
    var raw = sessionStorage.getItem('sota_requirements');
    if (!raw) { window.location.href = '/upload'; return; }

    currentData     = JSON.parse(raw);
    currentFilename = sessionStorage.getItem('sota_filename') || '';

    var tokens = JSON.parse(sessionStorage.getItem('sota_extract_tokens') || '{"total":0}');
    var cost   = sessionStorage.getItem('sota_extract_cost') || '$0.0000';

    if (tokens.total > 0) {
        document.getElementById('tokenText').textContent =
        tokens.total.toLocaleString() + ' tokens (extraction) · ' + cost;
        document.getElementById('tokenCounter').classList.add('visible');
    }

    renderTable();
})();

// ── RENDER ────────────────────────────────────────────────────────────────────

function renderTable() {
    var manualCount = currentData.filter(function(r) { return r.needs_manual_review; }).length;
    var banner = document.getElementById('manualReviewBanner');
    if (manualCount > 0) banner.classList.add('visible');
    else banner.classList.remove('visible');

    var usCount   = currentData.filter(function(r) { return r.region === 'US'; }).length;
    var intlCount = currentData.filter(function(r) { return r.region === 'International'; }).length;
    var cats      = {};
    currentData.forEach(function(r) { cats[r.category || 'Uncategorized'] = true; });
    var catCount  = Object.keys(cats).length;

    var warnClass = manualCount > 0 ? ' warning-card' : '';
    var warnNum   = manualCount > 0 ? ' warning' : '';

    document.getElementById('statsRow').innerHTML =
        '<div class="stat-card"><div class="stat-number">' + currentData.length + '</div><div class="stat-label">Total Requirements</div></div>' +
        '<div class="stat-card"><div class="stat-number">' + catCount + '</div><div class="stat-label">Categories</div></div>' +
        '<div class="stat-card"><div class="stat-number">' + usCount + '</div><div class="stat-label">US Standards</div></div>' +
        '<div class="stat-card' + warnClass + '"><div class="stat-number' + warnNum + '">' + manualCount + '</div><div class="stat-label">Verify Manually</div></div>';

    var tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    for (var i = 0; i < currentData.length; i++) {
        (function(idx) {
        var item      = currentData[idx];
        var isManual  = item.needs_manual_review;
        var dateClass = isManual ? 'date-chip manual' : 'date-chip';
        var dateDisp  = (item.date || '') + (isManual ? ' *' : '');
        var regionCls = item.region === 'US' ? 'badge-us' : 'badge-intl';
        var flag      = isManual ? '<span class="review-flag">Verify Manually</span>' : '';
        var desc      = (item.description || '').length > 120
                        ? item.description.substring(0, 120) + '...'
                        : (item.description || '');

        var tr = document.createElement('tr');
        tr.className = isManual ? 'needs-review' : '';
        tr.onclick   = function() { openModal(idx); };
        tr.innerHTML =
            '<td style="color:var(--muted);font-size:11px">' + (idx + 1) + '</td>' +
            '<td><span class="std-id">' + escHtml(item.standard_id || '') + '</span></td>' +
            '<td><span class="' + dateClass + '">' + escHtml(dateDisp) + '</span></td>' +
            '<td style="font-size:11px">' + escHtml(item.category || '') + '</td>' +
            '<td><span class="badge ' + regionCls + '">' + escHtml(item.region || '') + '</span></td>' +
            '<td style="font-size:11px;color:#4a5568;min-width:280px;max-width:480px">' + escHtml(desc) + '</td>' +
            '<td>' + flag + '</td>';
        tbody.appendChild(tr);
        })(i);
    }
}

// ── MODAL ─────────────────────────────────────────────────────────────────────

function openModal(index) {
    editingIndex = index;
    var item  = currentData[index];
    var isNew = item._isNew || false;

    document.getElementById('modalTitle').textContent            = isNew ? 'Add New Standard' : 'Edit Standard';
    document.getElementById('editStandardId').value             = item.standard_id  || '';
    document.getElementById('editDate').value                   = item.date         || '';
    document.getElementById('editCategory').value               = item.category     || '';
    document.getElementById('editRegion').value                 = item.region       || 'US';
    document.getElementById('editDescription').value            = item.description  || '';
    document.getElementById('modalDeleteBtn').style.display     = isNew ? 'none' : '';
    document.getElementById('modalOverlay').classList.add('visible');
}

function closeModal() {
    if (editingIndex !== null && currentData[editingIndex] && currentData[editingIndex]._isNew) {
        currentData.splice(editingIndex, 1);
        renderTable();
    }

    editingIndex = null;
    document.getElementById('modalOverlay').classList.remove('visible');
}

function saveModal() {
    if (editingIndex === null) return;

    var stdId   = document.getElementById('editStandardId').value.trim();
    var dateVal = document.getElementById('editDate').value.trim();
    var cat     = document.getElementById('editCategory').value.trim();
    var region  = document.getElementById('editRegion').value;
    var desc    = document.getElementById('editDescription').value.trim();

    if (!stdId) { alert('Standard ID is required.'); return; }

    var isCurrent = dateVal.toLowerCase() === 'current' || dateVal === '**' || dateVal === '';
    var yearMatch = dateVal.match(/\b(19|20)\d{2}\b/);
    var dateYear  = yearMatch ? parseInt(yearMatch[0]) : null;

    currentData[editingIndex] = {
        id:                  currentData[editingIndex].id || (currentData.length + 1),
        standard_id:         stdId,
        date:                dateVal,
        date_year:           dateYear,
        category:            cat,
        region:              region,
        description:         desc,
        needs_manual_review: isCurrent,
        source_filename:     currentFilename,
        uploaded_at:         currentData[editingIndex].uploaded_at || new Date().toISOString(),
        status:              null,
        current_version:     null,
        source_url:          null,
    };

    editingIndex = null;
    document.getElementById('modalOverlay').classList.remove('visible');
    renderTable();
}

function deleteRow() {
    if (editingIndex === null) return;
    if (!confirm('Delete this row? This cannot be undone.')) return;
    currentData.splice(editingIndex, 1);
    editingIndex = null;
    document.getElementById('modalOverlay').classList.remove('visible');
    renderTable();
}

// ── ADD ROW ───────────────────────────────────────────────────────────────────

function addRow() {
    currentData.push({
        id: currentData.length + 1,
        standard_id: '', date: '', date_year: null, category: '',
        region: 'US', description: '', needs_manual_review: false,
        source_filename: currentFilename, uploaded_at: new Date().toISOString(),
        status: null, current_version: null, source_url: null, _isNew: true,
    });

    renderTable();
    setTimeout(function() { openModal(currentData.length - 1); }, 80);
}

// ── APPROVE ───────────────────────────────────────────────────────────────────

function approve() {
    if (currentData.length === 0) { alert('No requirements to check.'); return; }

    // Strip _isNew flags before saving
    var clean = currentData.map(function(r) {
        var c = {};
        for (var k in r) { if (k !== '_isNew') c[k] = r[k]; }
        return c;
    });

    sessionStorage.setItem('sota_requirements', JSON.stringify(clean));
    window.location.href = '/results';
}

// ── UTILITIES ─────────────────────────────────────────────────────────────────

function escHtml(s) {
    return String(s)
        .replace(/&/g,  '&amp;')
        .replace(/</g,  '&lt;')
        .replace(/>/g,  '&gt;')
        .replace(/"/g,  '&quot;');
}

document.getElementById('modalOverlay').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});