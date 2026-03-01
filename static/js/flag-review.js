document.addEventListener('DOMContentLoaded', function () {
    var tables = document.querySelectorAll('table[data-flaggable]');
    if (!tables.length) return;

    tables.forEach(function (table) {
        var pageKey = 'flagged:' + location.pathname + location.search;

        // Load saved flags
        var saved = {};
        try { saved = JSON.parse(sessionStorage.getItem(pageKey) || '{}'); } catch (e) { saved = {}; }

        // Add header checkbox
        var headerRow = table.querySelector('thead tr');
        if (!headerRow) return;
        var th = document.createElement('th');
        th.style.width = '40px';
        var selectAll = document.createElement('input');
        selectAll.type = 'checkbox';
        selectAll.title = 'Select all';
        selectAll.setAttribute('aria-label', 'Select all rows');
        th.appendChild(selectAll);
        headerRow.insertBefore(th, headerRow.firstChild);

        // Add row checkboxes
        var rows = table.querySelectorAll('tbody tr');
        rows.forEach(function (row, idx) {
            var td = document.createElement('td');
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'flag-checkbox';
            cb.dataset.idx = idx;
            cb.setAttribute('aria-label', 'Flag row ' + (idx + 1) + ' for review');
            if (saved[idx]) cb.checked = true;
            td.appendChild(cb);
            row.insertBefore(td, row.firstChild);

            cb.addEventListener('change', function () {
                if (cb.checked) { saved[idx] = true; }
                else { delete saved[idx]; }
                sessionStorage.setItem(pageKey, JSON.stringify(saved));
                updateCount();
            });
        });

        // Select all handler
        selectAll.addEventListener('change', function () {
            rows.forEach(function (row, idx) {
                var cb = row.querySelector('.flag-checkbox');
                if (cb) {
                    cb.checked = selectAll.checked;
                    if (selectAll.checked) { saved[idx] = true; }
                    else { delete saved[idx]; }
                }
            });
            sessionStorage.setItem(pageKey, JSON.stringify(saved));
            updateCount();
        });

        // Flagged count display + download button
        var controls = document.createElement('div');
        controls.className = 'flag-controls';
        controls.style.display = 'none';

        var countSpan = document.createElement('span');
        countSpan.className = 'flag-count';
        controls.appendChild(countSpan);

        var dlBtn = document.createElement('button');
        dlBtn.type = 'button';
        dlBtn.className = 'btn btn-sm';
        dlBtn.textContent = 'Download Flagged CSV';
        dlBtn.addEventListener('click', function () { downloadFlagged(table, saved); });
        controls.appendChild(dlBtn);

        var clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn btn-sm';
        clearBtn.style.marginLeft = '0.5rem';
        clearBtn.textContent = 'Clear Selection';
        clearBtn.addEventListener('click', function () {
            saved = {};
            sessionStorage.setItem(pageKey, JSON.stringify(saved));
            rows.forEach(function (row) {
                var cb = row.querySelector('.flag-checkbox');
                if (cb) cb.checked = false;
            });
            selectAll.checked = false;
            updateCount();
        });
        controls.appendChild(clearBtn);

        table.parentElement.insertBefore(controls, table);

        function updateCount() {
            var n = Object.keys(saved).length;
            if (n > 0) {
                controls.style.display = 'flex';
                countSpan.textContent = n + ' item' + (n === 1 ? '' : 's') + ' flagged for review';
            } else {
                controls.style.display = 'none';
            }
        }
        updateCount();
    });

    function downloadFlagged(table, saved) {
        var headers = [];
        var headerCells = table.querySelectorAll('thead th');
        // Skip first column (checkbox)
        for (var i = 1; i < headerCells.length; i++) {
            headers.push(headerCells[i].textContent.trim());
        }

        var csvRows = [headers.join(',')];
        var bodyRows = table.querySelectorAll('tbody tr');
        bodyRows.forEach(function (row, idx) {
            if (!saved[idx]) return;
            var cells = row.querySelectorAll('td');
            var values = [];
            // Skip first cell (checkbox)
            for (var i = 1; i < cells.length; i++) {
                var text = cells[i].textContent.trim().replace(/"/g, '""');
                values.push('"' + text + '"');
            }
            csvRows.push(values.join(','));
        });

        var blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'flagged-for-review.csv';
        a.click();
        URL.revokeObjectURL(url);
    }
});
