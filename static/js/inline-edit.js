/**
 * Inline editing for price cells.
 * Click a cell with class "editable-price" to edit.
 * On blur or Enter, POST the new value to /edit-item.
 */
document.addEventListener('click', function(e) {
    var cell = e.target.closest('.editable-price');
    if (!cell || cell.querySelector('input')) return;

    var original = cell.textContent.trim().replace('$', '').replace(',', '');
    var idx = cell.dataset.idx;
    var field = cell.dataset.field || 'price';

    var input = document.createElement('input');
    input.type = 'number';
    input.step = '0.01';
    input.min = '0';
    input.value = original || '';
    input.style.cssText = 'width: 80px; padding: 2px 6px; font-size: 13px; border: 1px solid var(--primary); border-radius: 4px;';

    cell.textContent = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    function save() {
        var val = input.value.trim();
        if (val === original || val === '') {
            cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
            return;
        }
        fetch('/edit-item', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({index: parseInt(idx), field: field, value: parseFloat(val)})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.ok) {
                cell.textContent = '$' + parseFloat(val).toFixed(2);
            } else {
                cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
                cell.style.outline = '2px solid #e53e3e';
                cell.title = 'Save failed - please try again';
                setTimeout(function() { cell.style.outline = ''; cell.title = ''; }, 3000);
            }
        })
        .catch(function() {
            cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
            cell.style.outline = '2px solid #e53e3e';
            cell.title = 'Save failed - please try again';
            setTimeout(function() { cell.style.outline = ''; cell.title = ''; }, 3000);
        });
    }

    input.addEventListener('blur', save);
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); save(); }
        if (e.key === 'Escape') {
            cell.textContent = original ? '$' + parseFloat(original).toFixed(2) : '';
        }
    });
});
