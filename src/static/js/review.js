/**
 * review.js — Parsed-requirements review page for Sota.
 *
 * Responsibilities:
 *   1. Load the requirements list from sessionStorage (set by upload.js after /extract).
 *   2. Render a summary stats row and an editable table.
 *   3. Let the user open any row in an edit modal to correct Gemini's output.
 *   4. Let the user add new rows or delete existing ones.
 *   5. When satisfied, the user clicks "Approve & Run Check" — requirements are
 *      written back to sessionStorage and the browser navigates to /results.
 */

// ── STATE ─────────────────────────────────────────────────────────────────────

var currentData  = [];
var filteredData = [];
var editingIndex = null;
var currentFilename = '';
var sortOrder    = null; // null = original | 'asc' = A→Z | 'desc' = Z→A

// ── INIT ──────────────────────────────────────────────────────────────────────

/**
 * Bootstrap the review page: load requirements and token metadata from
 * sessionStorage, render the table, and show the parse-elapsed badge.
 * Redirects to /upload if sessionStorage is empty (e.g. direct navigation).
 */
(function init() {
    var raw = sessionStorage.getItem('sota_requirements');
    if (!raw) { window.location.href = '/upload'; return; }

    currentData     = JSON.parse(raw);
    currentFilename = sessionStorage.getItem('sota_filename') || '';

    var tokens  = JSON.parse(sessionStorage.getItem('sota_extract_tokens') || '{"total":0}');
    var cost    = sessionStorage.getItem('sota_extract_cost') || '$0.0000';
    var elapsed = parseInt(sessionStorage.getItem('sota_parse_elapsed') || '0', 10);

    var parts = [];
    if (tokens.total > 0) parts.push(tokens.total.toLocaleString() + ' tokens · ' + cost);
    if (elapsed > 0)       parts.push('parsed in ' + _fmtMs(elapsed));
    if (parts.length > 0) {
        document.getElementById('tokenText').textContent = parts.join(' · ');
        document.getElementById('tokenCounter').classList.add('visible');
    }

    renderTable();
})();

function _fmtMs(ms) {
    var s = Math.floor(ms / 1000), m = Math.floor(s / 60);
    return m > 0
        ? m + 'm ' + (s % 60) + 's'
        : s + 's';
}

// ── RENDER ────────────────────────────────────────────────────────────────────

/**
 * Rebuild the entire stats row and table body.
 * Called after every edit, add, or delete operation.
 *
 * @param {Array} [rows] - Optional subset to display; defaults to currentData.
 */
function renderTable(rows) {
    rows = rows || currentData;
    var manualCount = currentData.filter(function(r) { 
        return r.needs_manual_review; 
    }).length;
    var banner = document.getElementById('manualReviewBanner');

    if (manualCount > 0) banner.classList.add('visible');
    else banner.classList.remove('visible');

    var usCount   = currentData.filter(function(r) { return r.region === 'US'; }).length;
    var intlCount = currentData.filter(function(r) { return r.region === 'International'; }).length;
    var cats      = {};

    currentData.forEach(function(r) { 
        cats[r.category || 'Uncategorized'] = true; 
    });

    var catCount  = Object.keys(cats).length;

    var warnClass = manualCount > 0 ? ' warning-card' : '';
    var warnNum   = manualCount > 0 ? ' warning' : '';

    document.getElementById('statsRow').innerHTML =
        '<div class="stat-card"><div class="stat-number">' + currentData.length + '</div><div class="stat-label">Total Requirements</div></div>' +
        '<div class="stat-card"><div class="stat-number">' + catCount + '</div><div class="stat-label">Categories</div></div>' +
        '<div class="stat-card"><div class="stat-number">' + usCount + '</div><div class="stat-label">US Standards</div></div>' +
        '<div class="stat-card"><div class="stat-number">' + intlCount + '</div><div class="stat-label">International Standards</div></div>' +
        '<div class="stat-card' + warnClass + '"><div class="stat-number' + warnNum + '">' + manualCount + '</div><div class="stat-label">Verify Manually</div></div>';

    var tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    for (var i = 0; i < rows.length; i++) {
        (function(idx) {
        var item      = rows[idx];
        var realIdx   = currentData.indexOf(item);
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
        tr.onclick   = function() { openModal(realIdx); };
        tr.innerHTML =
            '<td style="color:var(--muted);font-size:11px">' + (realIdx + 1) + '</td>' +
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

/**
 * Open the edit modal pre-populated with data from the given row.
 * New rows (added via addRow) show "Add New Standard" title and hide Delete.
 *
 * @param {number} index - Index into currentData.
 */
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

/**
 * Close the modal without saving.
 * If the row was newly added (has _isNew flag) and not yet saved, remove it
 * from the array so the table stays clean.
 */
function closeModal() {
    if (editingIndex !== null && currentData[editingIndex] && currentData[editingIndex]._isNew) {
        currentData.splice(editingIndex, 1);
        renderTable();
    }

    editingIndex = null;
    document.getElementById('modalOverlay').classList.remove('visible');
}

/**
 * Validate the form, write the edited values back to currentData, and re-render.
 * Derives date_year and needs_manual_review from the date field to keep the
 * data model consistent with what parser.py produces.
 */
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

/** Prompt for confirmation, then permanently remove the row from currentData. */
function deleteRow() {
    if (editingIndex === null) return;
    if (!confirm('Delete this row? This cannot be undone.')) return;
    currentData.splice(editingIndex, 1);
    editingIndex = null;
    document.getElementById('modalOverlay').classList.remove('visible');
    renderTable();
}

// ── ADD ROW ───────────────────────────────────────────────────────────────────

/**
 * Append a blank placeholder row to currentData, re-render the table,
 * then open the edit modal after a short delay so the new row is visible.
 * The _isNew flag ensures closeModal() discards the row if the user cancels.
 */
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

/**
 * Persist the final requirements list to sessionStorage and navigate to /results,
 * which immediately starts the compliance check.
 * Strips internal _isNew flags before saving so they don't pollute the data model.
 */
function approve() {
    if (currentData.length === 0) { alert('No requirements to check.'); return; }

    // Strip _isNew flags before saving — they are UI-only state
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

// ── FILTERS & SORT ────────────────────────────────────────────────────────────

/** Apply the active sort on top of the active filter set, then re-render. */
function applyDisplay() {
    var base = filteredData.length > 0 ? filteredData : currentData;

    if (!sortOrder) {
        renderTable(base);
    } else {
        var sorted = base.slice().sort(function(a, b) {
            var sa = (a.standard_id || '').toLowerCase();
            var sb = (b.standard_id || '').toLowerCase();
            return sortOrder === 'asc' ? sa.localeCompare(sb) : sb.localeCompare(sa);
        });
        renderTable(sorted);
    }
}

function applyFilters() {
    var regionVal   = document.getElementById('filter-region').value;
    var standardVal = document.getElementById('filter-standard').value.toLowerCase().trim();

    filteredData = currentData.filter(function(row) {
        var matchesRegion   = !regionVal   || row.region === regionVal;
        var matchesStandard = !standardVal || (row.standard_id || '').toLowerCase().includes(standardVal);
        return matchesRegion && matchesStandard;
    });

    applyDisplay();
}

function resetFilters() {
    document.getElementById('filter-region').value   = '';
    document.getElementById('filter-standard').value = '';
    filteredData = [];
    applyDisplay();
}

function toggleSort() {
    sortOrder = sortOrder === 'asc' ? null : 'asc';

    var btn = document.getElementById('sortBtn');
    btn.innerHTML = sortOrder === 'asc'
        ? '&#8593; Sorted: A &rarr; Z'
        : '&#8597; Sort A &rarr; Z';

    applyDisplay();
}

document.getElementById('filter-region').addEventListener('change', applyFilters);
document.getElementById('filter-standard').addEventListener('change', applyFilters);

document.getElementById('modalOverlay').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});