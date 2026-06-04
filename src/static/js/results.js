/**
 * results.js — Compliance check dashboard for the Sota results page.
 *
 * Responsibilities:
 *   1. On load, immediately POST the requirements list to /check/start and open
 *      an EventSource to /check/stream — results stream in one by one via SSE.
 *   2. Render and update the results table as each requirement completes.
 *   3. Show a color-coded progress bar and live tally (Current / Outdated / Unverified).
 *   4. Enable filters and sort after all results arrive.
 *   5. Trigger the /export endpoint when the user clicks "Export to Excel".
 *   6. Handle the AI Summary modal — fetches /summarize per row and caches the
 *      result in sessionStorage so repeat clicks don't cost extra tokens.
 */

// ── STATE ─────────────────────────────────────────────────────────────────────

var currentData      = [];
var filteredData     = [];
var totalTokens      = 0;
var checkDone        = false;
var sortOrder        = null; // null = original | 'asc' = A→Z | 'desc' = Z→A
var streamCurrent    = 0;    // running tally updated as SSE events arrive
var streamOutdated   = 0;
var streamUnverified = 0;
var _checkStartTime  = 0;    // Date.now() snapshot when the SSE stream opens
var _elapsedTimer    = null; // setInterval handle for the progress elapsed clock

var STATUS_HTML = {
'CURRENT':    '<span class="status-badge status-current">&#10003; Current</span>',
'OUTDATED':   '<span class="status-badge status-outdated">&#10007; Outdated</span>',
'UNVERIFIED': '<span class="status-badge status-unverified">&#9888; Unverified</span>',
'CHECKING':   '<span class="status-badge status-checking">&bull;&bull;&bull;</span>',
};

// ── INIT ──────────────────────────────────────────────────────────────────────

/**
 * Bootstrap the page: load requirements from sessionStorage, seed the table
 * with "Checking…" placeholders, then immediately start the SSE compliance check.
 * If sessionStorage is empty (e.g. direct navigation), redirect to /upload.
 */
(function init() {
    var raw = sessionStorage.getItem('sota_requirements');
    if (!raw) { window.location.href = '/upload'; return; }

    currentData = JSON.parse(raw);

    // Include parse tokens from the earlier /extract call in the running total
    var extractTokens = JSON.parse(sessionStorage.getItem('sota_extract_tokens') || '{"total":0}');
    totalTokens = extractTokens.total || 0;

    renderInitialTable();
    updateStats();
    startCheck();
})();

// ── INITIAL TABLE RENDER (all rows as "Checking") ─────────────────────────────

/** Fill the table with placeholder rows before any SSE results arrive. */
function renderInitialTable() {
    var tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    for (var i = 0; i < currentData.length; i++) {
        var row = buildRow(i, currentData[i], true);
        tbody.appendChild(row);
    }
}

/**
 * Build one <tr> element for the results table.
 *
 * @param {number}  idx      - Index into currentData (also used as DOM row ID).
 * @param {object}  item     - Requirement dict.
 * @param {boolean} checking - True while the SSE stream is still running;
 *                             shows "···" status and hides the Summary button.
 * @returns {HTMLTableRowElement}
 */
function buildRow(idx, item, checking) {
    var isManual  = item.needs_manual_review;
    var dateClass = isManual ? 'date-chip manual' : 'date-chip';
    var dateDisp  = isManual ? '**' : (item.date || '');
    var regionCls = item.region === 'US' ? 'badge-us' : 'badge-intl';

    var statusHtml     = checking ? STATUS_HTML['CHECKING'] : statusBadge(item.status);
    var currentVerHtml = item.current_version
        ? escHtml(item.current_version)
        : '<span class="cell-empty">—</span>';

    var sourceHtml;
    if (item.source_url) {
        var summBtn = checking
            ? ''
            : ' <button class="btn-summarize" onclick="event.stopPropagation();summarizeReq(' + idx + ')">&#10024; Summary</button>';
        sourceHtml = '<a class="source-link" href="' + escAttr(item.source_url) + '" target="_blank" rel="noopener">View &#8599;</a>' + summBtn;
    } else {
        sourceHtml = '<span class="cell-empty">—</span>';
    }

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

/**
 * Replace one placeholder row with its completed result.
 * Rebuilds the entire <tr> so status badge and source URL appear correctly.
 *
 * @param {number} idx - Index into currentData.
 * @param {object} req - Updated requirement dict from the SSE event.
 */
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

    var PAYWALL_ORGS = ['ISO', 'ASTM', 'ANSI', 'ASQ'];
    var hasPaywalled = currentData.some(function(r) {
        var sid = (r.standard_id || '').toUpperCase().trim();
        return PAYWALL_ORGS.some(function(org) { return sid.startsWith(org); });
    });
    var paywallEl = document.getElementById('paywallBanner');
    if (paywallEl) {
        if (hasPaywalled) paywallEl.classList.add('visible');
        else paywallEl.classList.remove('visible');
    }

    document.getElementById('statsRow').innerHTML =
        '<div class="stat-card"><div class="stat-number">' + total + '</div><div class="stat-label">Total Requirements</div></div>' +
        '<div class="stat-card success-card"><div class="stat-number success">' + current + '</div><div class="stat-label">Current</div></div>' +
        '<div class="stat-card danger-card"><div class="stat-number danger">' + outdated + '</div><div class="stat-label">Outdated</div></div>' +
        '<div class="stat-card warning-card"><div class="stat-number warning">' + unverified + '</div><div class="stat-label">Unverified</div></div>';
}

// ── FILTERS & SORT ────────────────────────────────────────────────────────────

/**
 * Re-render the table body from an arbitrary rows array.
 * Used by applyDisplay() after filtering or sorting; row IDs are looked up
 * via indexOf so buildRow always receives the canonical currentData index.
 *
 * @param {Array} rows - Subset (or reorder) of currentData to display.
 */
function renderTable(rows) {
    var tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    rows.forEach(function(item) {
        var realIdx = currentData.indexOf(item);
        var row = buildRow(realIdx, item, false);
        tbody.appendChild(row);
    });
}

/** Apply the active sort order on top of the active filter set, then re-render. */
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

    updateStats();
}

function applyFilters() {
    var regionVal   = document.getElementById('filter-region').value;
    var standardVal = document.getElementById('filter-standard').value;
    var statusVal   = document.getElementById('filter-status').value;

    filteredData = currentData.filter(function(row) {
        var matchesRegion    = !regionVal   || row.region === regionVal;
        var matchesStandard  = !standardVal || (row.standard_id || '').toLowerCase().includes(standardVal.toLowerCase());
        var matchesStatus    = !statusVal   || (row.status || '').toUpperCase().trim() === statusVal.toUpperCase().trim();
        return matchesRegion && matchesStandard && matchesStatus;
    });

    applyDisplay();
}

function resetFilters() {
    document.getElementById('filter-region').value   = '';
    document.getElementById('filter-standard').value = '';
    document.getElementById('filter-status').value   = '';
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

function enableFilters() {
    document.getElementById('filter-bar').classList.remove('hidden');
    document.getElementById('sortBtn').disabled = false;

    document.getElementById('filter-region').addEventListener('change', applyFilters);
    document.getElementById('filter-standard').addEventListener('change', applyFilters);
    document.getElementById('filter-status').addEventListener('change', applyFilters);
}

// ── PROGRESS BAR COLOR ────────────────────────────────────────────────────────


/** Update the live tally chips (Current / Outdated / Unverified) shown above the bar. */
function updateProgressTally() {
    var el = document.getElementById('progressTally');
    if (!el) return;
    el.classList.remove('hidden');
    document.getElementById('tallyCurrent').textContent    = streamCurrent;
    document.getElementById('tallyOutdated').textContent   = streamOutdated;
    document.getElementById('tallyUnverified').textContent = streamUnverified;
}

// ── SSE COMPLIANCE CHECK ──────────────────────────────────────────────────────

/**
 * Format a millisecond duration as M:SS.
 * @param {number} ms
 * @returns {string} e.g. "1:07"
 */
function _formatElapsed(ms) {
    var s   = Math.floor(ms / 1000);
    var min = Math.floor(s / 60);
    var sec = s % 60;
    return min + ':' + (sec < 10 ? '0' : '') + sec;
}

/** Start the elapsed-time clock shown in the progress header. */
function _startElapsedTimer() {
    _checkStartTime = Date.now();
    var el = document.getElementById('progressElapsed');
    _elapsedTimer = setInterval(function() {
        if (el) el.textContent = _formatElapsed(Date.now() - _checkStartTime);
    }, 1000);
}

/** Stop the elapsed-time clock (called when all results arrive). */
function _stopElapsedTimer() {
    clearInterval(_elapsedTimer);
    _elapsedTimer = null;
}

/**
 * POST the requirements to /check/start to register the job, then open an
 * EventSource to /check/stream with the returned job_id.
 * The two-step approach avoids passing a large request body to a GET endpoint.
 */
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

/**
 * Open an EventSource to /check/stream and handle incoming SSE events.
 * Each event carries one completed requirement; the final event sets done=true.
 *
 * @param {string} jobId - UUID returned by /check/start.
 */
function streamResults(jobId) {
    _startElapsedTimer();
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

        var s = data.requirement ? data.requirement.status : null;
        if (s === 'CURRENT')         streamCurrent++;
        else if (s === 'OUTDATED')   streamOutdated++;
        else                         streamUnverified++;
        updateProgressTally();
    };

    es.onerror = function() {
        es.close();
        if (!checkDone) showError('Connection to server lost. Please refresh and try again.');
    };
}

/**
 * Called when the SSE stream sends {done: true}.
 * Stops the timer, swaps the progress bar for a completion banner,
 * unlocks the Export button, persists results, and enables filters.
 *
 * @param {object} data - Final SSE payload with {done, total_tokens, cost}.
 */
function onCheckComplete(data) {
    checkDone = true;
    _stopElapsedTimer();

    var elapsed = _formatElapsed(Date.now() - _checkStartTime);

    // Swap the animated progress section for a compact green completion bar
    var section = document.getElementById('progressSection');
    section.innerHTML =
        '<div class="check-complete-bar">'
      + '<span class="check-complete-icon">&#10003;</span>'
      + '<span class="check-complete-label">Compliance check complete</span>'
      + '<span class="check-complete-time">Completed in ' + elapsed + '</span>'
      + '</div>';

    document.getElementById('exportBtn').disabled = false;

    totalTokens = data.total_tokens || totalTokens;
    updateTokenDisplay(totalTokens, data.cost);
    updateStats();

    // Persist updated data so the user can refresh without losing results
    sessionStorage.setItem('sota_requirements', JSON.stringify(currentData));

    enableFilters();
}

// ── EXPORT ────────────────────────────────────────────────────────────────────

/**
 * POST current requirements to /export and trigger a browser file download.
 * The server returns a binary .xlsx blob; we create an object URL and click
 * a synthetic <a> element to save it — no page navigation occurs.
 */
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

// ── AI SUMMARY MODAL ──────────────────────────────────────────────────────────

/**
 * Request an AI summary for one requirement and show it in the summary modal.
 * Results are cached in sessionStorage by standard_id so repeat clicks
 * don't incur additional Gemini API calls during the same session.
 *
 * @param {number} idx - Index into currentData.
 */
function summarizeReq(idx) {
    var req      = currentData[idx];
    var cacheKey = 'sota_summary_' + (req.standard_id || String(idx)).replace(/\s+/g, '_');

    var cached = sessionStorage.getItem(cacheKey);
    if (cached) {
        openSummaryModal(req.standard_id, cached, false);
        return;
    }

    // Show spinner immediately, then populate when the fetch resolves
    openSummaryModal(req.standard_id, null, true);

    fetch('/summarize', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({
            standard_id: req.standard_id || '',
            description: req.description || '',
            source_url:  req.source_url  || '',
        }),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            openSummaryModal(req.standard_id, 'Unable to generate summary: ' + data.error, false);
            return;
        }
        sessionStorage.setItem(cacheKey, data.summary);
        openSummaryModal(req.standard_id, data.summary, false);
    })
    .catch(function(err) {
        openSummaryModal(req.standard_id, 'Request failed: ' + err.message, false);
    });
}

/**
 * Render the summary modal. When loading=true shows a spinner instead of text.
 * Converts Gemini's markdown-lite response (- bullets and **bold**) to HTML.
 *
 * @param {string}  title   - Standard ID used as the modal heading.
 * @param {string}  text    - Raw summary text from Gemini (may contain - bullets).
 * @param {boolean} loading - If true, show spinner instead of text.
 */
function openSummaryModal(title, text, loading) {
    document.getElementById('summaryModalTitle').textContent = title || 'Standard Summary';
    var body = document.getElementById('summaryModalBody');

    if (loading) {
        body.innerHTML = '<div class="summary-loading"><div class="spinner-dark"></div><p>Generating summary with Gemini AI&hellip;</p></div>';
    } else {
        var lines  = (text || '').split('\n');
        var html   = '';
        var inList = false;

        lines.forEach(function(line) {
            var trimmed = line.trim();
            if (!trimmed) {
                if (inList) { html += '</ul>'; inList = false; }
                return;
            }
            var isBullet = /^[-*•]/.test(trimmed);
            var content  = escHtml(isBullet ? trimmed.replace(/^[-*•]\s*/, '') : trimmed);
            // Convert **bold** markers to <strong> after HTML-escaping
            content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

            if (isBullet) {
                if (!inList) { html += '<ul class="summary-list">'; inList = true; }
                html += '<li>' + content + '</li>';
            } else {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<p class="summary-para">' + content + '</p>';
            }
        });
        if (inList) html += '</ul>';
        body.innerHTML = '<div class="summary-text">' + html + '</div>';
    }

    document.getElementById('summaryModalOverlay').classList.add('visible');
}

/** Close the AI summary modal. */
function closeSummaryModal() {
    document.getElementById('summaryModalOverlay').classList.remove('visible');
}

document.getElementById('summaryModalOverlay').addEventListener('click', function(e) {
    if (e.target === this) closeSummaryModal();
});