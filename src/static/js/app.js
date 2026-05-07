var dropZone    = document.getElementById('dropZone');
var fileInput   = document.getElementById('fileInput');
var filePreview = document.getElementById('filePreview');
var fileName    = document.getElementById('fileName');
var submitWrap  = document.getElementById('submitWrap');
var submitBtn   = document.getElementById('submitBtn');
var statusBox   = document.getElementById('status');
var results     = document.getElementById('results');
var errorBox    = document.getElementById('errorBox');
var disclaimer  = document.getElementById('disclaimer');
var dbSuccess   = document.getElementById('dbSuccess');
var dbError     = document.getElementById('dbError');
var dbWarning   = document.getElementById('dbWarning');

var selectedFile = null;

var ALLOWED = ['pdf', 'docx', 'xlsx'];
var FILE_ICONS = { pdf: '&#128212;', docx: '&#128216;', xlsx: '&#128218;' };

function getExt(filename) {
  return filename.split('.').pop().toLowerCase();
}

dropZone.addEventListener('dragover', function(e) {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', function() {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', function(e) {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  var file = e.dataTransfer.files[0];
  if (file && ALLOWED.indexOf(getExt(file.name)) !== -1) {
    setFile(file);
  } else {
    showError('Please drop a PDF, DOCX, or XLSX file.');
  }
});

fileInput.addEventListener('change', function() {
  if (fileInput.files[0]) {
    setFile(fileInput.files[0]);
  }
});

function setFile(file) {
  selectedFile = file;
  var ext = getExt(file.name);
  dropZone.classList.add('has-file');
  document.getElementById('dropIcon').textContent = '';
  document.getElementById('dropIcon').innerHTML = '&#10003;';
  document.getElementById('dropTitle').textContent = 'File ready';
  document.getElementById('dropSub').textContent = 'Drop a different file to replace it';
  document.getElementById('fileTypeIcon').innerHTML = FILE_ICONS[ext] || '&#128196;';
  fileName.textContent = file.name;
  filePreview.classList.add('visible');
  submitWrap.classList.add('visible');
  errorBox.style.display = 'none';
  results.style.display = 'none';
  disclaimer.style.display = 'none';
  hideDbBanners();
}

function clearFile() {
  selectedFile = null;
  fileInput.value = '';
  dropZone.classList.remove('has-file');
  document.getElementById('dropIcon').innerHTML = '&#9729;';
  document.getElementById('dropTitle').textContent = 'Drag & Drop or Upload a File';
  document.getElementById('dropSub').textContent = 'Click anywhere in this box to browse';
  filePreview.classList.remove('visible');
  submitWrap.classList.remove('visible');
  errorBox.style.display = 'none';
  hideDbBanners();
}

function hideDbBanners() {
  dbSuccess.classList.remove('visible');
  dbError.classList.remove('visible');
  dbWarning.classList.remove('visible');
}

function submitFile() {
  if (!selectedFile) return;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Processing...';
  errorBox.style.display = 'none';
  results.style.display = 'none';
  disclaimer.style.display = 'none';
  hideDbBanners();
  statusBox.classList.add('visible');

  var formData = new FormData();
  formData.append('file', selectedFile);

  fetch('/extract', { method: 'POST', body: formData })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      statusBox.classList.remove('visible');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Extract Requirements';

      if (data.error) {
        showError(data.error);
        return;
      }

      if (data.db_success) {
        document.getElementById('dbSuccessMsg').textContent =
          data.db_count + ' standards saved to database successfully.';
        dbSuccess.classList.add('visible');
      } else if (data.db_error) {
        document.getElementById('dbErrorMsg').textContent =
          'Could not save to database: ' + data.db_error;
        dbError.classList.add('visible');
      } else if (data.db_not_configured) {
        dbWarning.classList.add('visible');
      }

      disclaimer.style.display = 'block';
      renderResults(data.requirements, data.filename);
    })
    .catch(function(err) {
      statusBox.classList.remove('visible');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Extract Requirements';
      showError('Server error: ' + err.message);
    });
}

function renderResults(requirements, filename) {
  results.style.display = 'block';

  var manualCount = requirements.filter(function(r) { return r.needs_manual_review; }).length;

  var banner = document.getElementById('manualReviewBanner');
  if (manualCount > 0) {
    banner.classList.add('visible');
  } else {
    banner.classList.remove('visible');
  }

  var categories = {};
  requirements.forEach(function(r) {
    var cat = r.category || 'Uncategorized';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(r);
  });

  var usCount   = requirements.filter(function(r) { return r.region === 'US'; }).length;
  var intlCount = requirements.filter(function(r) { return r.region === 'International'; }).length;

  var warnClass  = manualCount > 0 ? ' warning-card' : '';
  var warnNum    = manualCount > 0 ? ' warning' : '';

  document.getElementById('statsRow').innerHTML =
    '<div class="stat-card"><div class="stat-number">' + requirements.length + '</div><div class="stat-label">Total Standards</div></div>' +
    '<div class="stat-card"><div class="stat-number">' + Object.keys(categories).length + '</div><div class="stat-label">Categories</div></div>' +
    '<div class="stat-card"><div class="stat-number">' + usCount + '</div><div class="stat-label">US Standards</div></div>' +
    '<div class="stat-card' + warnClass + '"><div class="stat-number' + warnNum + '">' + manualCount + '</div><div class="stat-label">Verify Manually</div></div>';

  var jsonBlob = new Blob([JSON.stringify(requirements, null, 2)], { type: 'application/json' });
  var jsonBtn  = document.getElementById('downloadJson');
  jsonBtn.href = URL.createObjectURL(jsonBlob);
  jsonBtn.download = filename.replace(/[.](pdf|docx|xlsx)$/i, '_requirements.json');

  var csvBtn = document.getElementById('downloadCsv');
  csvBtn.onclick = function(e) {
    e.preventDefault();
    var rows = [['ID','Standard ID','Date','Date Year','Category','Region','Description','Needs Manual Review']];
    requirements.forEach(function(r) {
      rows.push([
        r.id,
        r.standard_id,
        r.date,
        r.date_year || '',
        r.category,
        r.region,
        r.description,
        r.needs_manual_review ? 'Yes' : 'No'
      ]);
    });
    var csv = rows.map(function(row) {
      return row.map(function(v) {
        return '"' + String(v).replace(/"/g, '""') + '"';
      }).join(',');
    }).join('\n');
    var blob = new Blob([csv], { type: 'text/csv' });
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement('a');
    a.href   = url;
    a.download = filename.replace(/[.](pdf|docx|xlsx)$/i, '_requirements.csv');
    a.click();
  };

  var container = document.getElementById('categorySections');
  container.innerHTML = '';

  Object.keys(categories).forEach(function(cat) {
    var items = categories[cat];
    var rows  = items.map(function(item) {
      var isManual    = item.needs_manual_review;
      var dateClass   = isManual ? 'date-chip manual' : 'date-chip';
      var dateDisplay = isManual ? item.date + ' *' : item.date;
      var reviewFlag  = isManual ? '<span class="review-flag">Verify Manually</span>' : '';
      var regionClass = item.region === 'US' ? 'badge-us' : 'badge-intl';
      return '<tr class="' + (isManual ? 'needs-review' : '') + '">' +
        '<td><span class="std-id">' + (item.standard_id || '') + '</span></td>' +
        '<td><span class="' + dateClass + '">' + dateDisplay + '</span></td>' +
        '<td><span class="badge ' + regionClass + '">' + (item.region || '') + '</span></td>' +
        '<td style="font-size:12px;color:#4a5568">' + (item.description || '') + '</td>' +
        '<td>' + reviewFlag + '</td>' +
        '</tr>';
    }).join('');

    var section = document.createElement('div');
    section.className = 'category-section';
    section.innerHTML =
      '<div class="category-header" onclick="this.parentElement.classList.toggle(\'collapsed\')">' +
        '<span>' + cat + '</span>' +
        '<span class="cat-count">' + items.length + '</span>' +
        '<span class="cat-toggle">&#9660;</span>' +
      '</div>' +
      '<div class="cat-body">' +
        '<table>' +
          '<thead><tr><th>Standard ID</th><th>Date</th><th>Region</th><th>Description</th><th>Status</th></tr></thead>' +
          '<tbody>' + rows + '</tbody>' +
        '</table>' +
      '</div>';
    container.appendChild(section);
  });

  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(msg) {
  errorBox.textContent = 'Error: ' + msg;
  errorBox.style.display = 'block';
}