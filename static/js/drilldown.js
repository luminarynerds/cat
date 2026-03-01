/**
 * Expand/collapse Dewey hundreds-level drill-down rows.
 */
document.addEventListener('click', function(e) {
    var toggle = e.target.closest('.dewey-toggle');
    if (!toggle) return;
    var tens = toggle.dataset.tens;
    var rows = document.querySelectorAll('.dewey-hundreds-' + tens);
    var expanded = toggle.classList.toggle('expanded');
    rows.forEach(function(row) {
        row.style.display = expanded ? '' : 'none';
    });
    toggle.querySelector('.toggle-arrow').textContent = expanded ? '\u25BC' : '\u25B6';
});
