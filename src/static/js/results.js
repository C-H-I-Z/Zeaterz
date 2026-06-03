// ── STATE ─────────────────────────────────────────────────────────────────────

var currentData  = [];
var filteredData = [];
var totalTokens  = 0;
var checkDone    = false;

var STATUS_HTML = {
'CURRENT':    '<span class="status-badge status-current">&#10003; Current</span>',
'OUTDATED':   '<span class="status-badge status-outdated">&#10007; Outdated</span>',
'UNVERIFIED': '<span class="status-badge status-unverified">&#9888; Unverified</span>',
'CHECKING':   '<span class="status-badge status-checking">&bull;&bull;&bull;</span>',
};

// ── INIT ──────────────────────────────────────────────────────────────────────

(function init() {
    var raw = sessionStorage.getItem('sota_requirements');
    if (!raw) { window.location.href = '/upload'; return; }

    currentData = JSON.parse(raw);

    // Add extract tokens to running total
    var extractTokens = JSON.parse(sessionStorage.getItem('sota_extract_tokens') || '{"total":0}');
    totalTokens = extractTokens.total || 0;

    renderInitialTable();
    updateStats();
    startCheck();
})();

// ── INITIAL TABLE RENDER (all rows as "Checking") ─────────────────────────────

function renderInitialTable() {
    var tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    for (var i = 0; i < currentData.length; i++) {
        var row = buildRow(i, currentData[i], true);
        tbody.appendChild(row);
    }
}

function buildRow(idx, item, checking) {
    var isManual  = item.needs_manual_review;
    var dateClass = isManual ? 'date-chip manual' : 'date-chip';
    var dateDisp  = (item.date || '') + (isManual ? ' *' : '');
    var regionCls = item.region === 'US' ? 'badge-us' : 'badge-intl';

    var statusHtml     = checking ? STATUS_HTML['CHECKING'] : statusBadge(item.status);
    var currentVerHtml = item.current_version
        ? escHtml(item.current_version)
        : '<span style="color:var(--muted);font-size:11px">—</span>';
    var sourceHtml = item.source_url
        ? '<a class="source-link" href="' + escAttr(item.source_url) + '" target="_blank" rel="noopener">View &#8599;</a>'
        : '<span style="color:var(--muted);font-size:11px">—</span>';

    var desc = (item.description || '').length > 100
        ? item.description.substring(0, 100) + '...'
        : (item.description || '');

    var rowClass = '';
    if (!checking && item.status === 'CURRENT')  rowClass = 'row-current';
    if (!checking && item.status === 'OUTDATED')  rowClass = 'row-outdated';
    if (isManual) rowClass += ' needs-review';

    var tr = document.createElement('tr');
    tr.className       = rowClass.trim();
    tr.id              = 'row-' + idx;
    tr.innerHTML =
        '<td style="color:var(--muted);font-size:11px">' + (idx + 1) + '</td>' +
        '<td><span class="std-id">' + escHtml(item.standard_id || '') + '</span></td>' +
        '<td><span class="' + dateClass + '">' + escHtml(dateDisp) + '</span></td>' +
        '<td style="font-size:12px;font-weight:600;color:var(--navy)">' + currentVerHtml + '</td>' +
        '<td>' + statusHtml + '</td>' +
        '<td>' + sourceHtml + '</td>' +
        '<td style="font-size:11px">' + escHtml(item.category || '') + '</td>' +
        '<td><span class="badge ' + regionCls + '">' + escHtml(item.region || '') + '</span></td>' +
        '<td style="font-size:11px;color:#4a5568;min-width:280px;max-width:480px">' + escHtml(desc) + '</td>';

    return tr;
}

function statusBadge(status) {
    return STATUS_HTML[status] || STATUS_HTML['UNVERIFIED'];
}

// ── UPDATE A SINGLE ROW AFTER SSE RESULT ──────────────────────────────────────

function updateRow(idx, req) {
    currentData[idx] = req;
    var oldRow = document.getElementById('row-' + idx);
    if (!oldRow) return;
    var newRow = buildRow(idx, req, false);
    oldRow.parentNode.replaceChild(newRow, oldRow);
}

// ── STATS ─────────────────────────────────────────────────────────────────────

function updateStats() {
    var total      = currentData.length;
    var current    = currentData.filter(function(r) { return r.status === 'CURRENT';    }).length;
    var outdated   = currentData.filter(function(r) { return r.status === 'OUTDATED';   }).length;
    var unverified = currentData.filter(function(r) { return !r.status || r.status === 'UNVERIFIED'; }).length;

    var manualCount = currentData.filter(function(r) { return r.needs_manual_review; }).length;
    var banner = document.getElementById('manualReviewBanner');
    if (manualCount > 0 || unverified > 0) banner.classList.add('visible');
    else banner.classList.remove('visible');

    document.getElementById('statsRow').innerHTML =
        '<div class="stat-card"><div class="stat-number">' + total + '</div><div class="stat-label">Total Requirements</div></div>' +
        '<div class="stat-card success-card"><div class="stat-number success">' + current + '</div><div class="stat-label">Current</div></div>' +
        '<div class="stat-card danger-card"><div class="stat-number danger">' + outdated + '</div><div class="stat-label">Outdated</div></div>' +
        '<div class="stat-card warning-card"><div class="stat-number warning">' + unverified + '</div><div class="stat-label">Unverified</div></div>';
}

// ── FILTERS ───────────────────────────────────────────────────────────────────

function renderTable(rows) {
    var tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    rows.forEach(function(item, i) {
        var realIdx = currentData.indexOf(item);
        var row = buildRow(realIdx, item, false);
        tbody.appendChild(row);
    });
}

function applyFilters() {
    var regionVal     = document.getElementById('filter-region').value;
    var standardVal   = document.getElementById('filter-standard').value;
    var statusVal     = document.getElementById('filter-status').value;

    filteredData = currentData.filter(function(row) {
        var matchesRegion = !regionVal || row.region === regionVal;

        var matchesStandard = !standardVal || (row.standard_id || '').toLowerCase().includes(standardVal.toLowerCase());

        var matchesStatus = !statusVal || (row.status || '').toUpperCase().trim() === statusVal.toUpperCase().trim();

        return matchesRegion && matchesStandard && matchesStatus;
    });

    renderTable(filteredData);
    updateStats();
}

function resetFilters() {
    document.getElementById('filter-region').value    = '';
    document.getElementById('filter-standard').value  = '';
    document.getElementById('filter-status').value    = '';
    filteredData = [];
    renderTable(currentData);
    updateStats();
}

function enableFilters() {
    // Reveal the filter bar (keep it hidden while check is running)
    document.getElementById('filter-bar').style.display = 'flex';

    // Wire up event listeners (only once check is complete)
    document.getElementById('filter-region').addEventListener('change', applyFilters);
    document.getElementById('filter-standard').addEventListener('change', applyFilters);
    document.getElementById('filter-status').addEventListener('change', applyFilters);
}

// ── SSE COMPLIANCE CHECK ──────────────────────────────────────────────────────

function startCheck() {
    fetch('/check/start', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({requirements: currentData}),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) { showError(data.error); return; }
        streamResults(data.job_id);
    })
    .catch(function(err) { showError('Could not start check: ' + err.message); });
}

function streamResults(jobId) {
    var es = new EventSource('/check/stream?job_id=' + encodeURIComponent(jobId));

    es.onmessage = function(event) {
        var data = JSON.parse(event.data);

        if (data.error) {
        es.close();
        showError(data.error);
        return;
        }

        if (data.done) {
        es.close();
        onCheckComplete(data);
        return;
        }

        // Update progress
        var pct = Math.round((data.progress / data.total) * 100);
        document.getElementById('progressBarFill').style.width = pct + '%';
        document.getElementById('progressLabel').textContent   =
        'Checking requirement ' + data.progress + ' of ' + data.total + '…';
        document.getElementById('progressCount').textContent   = data.progress + ' / ' + data.total;
        document.getElementById('progressSub').textContent     =
        (data.requirement ? data.requirement.standard_id : '') + ' — ' + (data.cost || '');

        // Update token counter
        totalTokens = data.tokens;
        updateTokenDisplay(data.tokens, data.cost);

        // Update the row
        updateRow(data.index, data.requirement);
        updateStats();
    };

    es.onerror = function() {
        es.close();
        if (!checkDone) showError('Connection to server lost. Please refresh and try again.');
    };
}

function onCheckComplete(data) {
    checkDone = true;

    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('exportBtn').disabled = false;

    totalTokens = data.total_tokens || totalTokens;
    updateTokenDisplay(totalTokens, data.cost);
    updateStats();

    // Save final state to sessionStorage
    sessionStorage.setItem('sota_requirements', JSON.stringify(currentData));

    enableFilters();
}

// ── EXPORT ────────────────────────────────────────────────────────────────────

function downloadExcel() {
    var btn = document.getElementById('exportBtn');
    btn.disabled = true;
    btn.textContent = 'Generating…';

    fetch('/export', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({requirements: currentData}),
    })
    .then(function(r) {
        if (!r.ok) throw new Error('Export failed');
        return r.blob();
    })
    .then(function(blob) {
        var url = URL.createObjectURL(blob);
        var a   = document.createElement('a');
        a.href  = url;
        a.download = 'sota_report_' + new Date().toISOString().slice(0,10) + '.xlsx';
        a.click();
        URL.revokeObjectURL(url);
        btn.disabled = false;
        btn.innerHTML = '&#8595; Export to Excel';
    })
    .catch(function(err) {
        btn.disabled = false;
        btn.innerHTML = '&#8595; Export to Excel';
        showError('Export failed: ' + err.message);
    });
}

// ── UTILITIES ─────────────────────────────────────────────────────────────────

function updateTokenDisplay(tokens, cost) {
    document.getElementById('tokenText').textContent =
        (tokens || 0).toLocaleString() + ' tokens · ' + (cost || '$0.0000');
    document.getElementById('tokenCounter').classList.add('visible');
}

function showError(msg) {
    var box = document.getElementById('errorBox');
    box.textContent = 'Error: ' + msg;
    box.style.display = 'block';
    document.getElementById('progressSection').style.display = 'none';
}

function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escAttr(s) { return escHtml(s); }