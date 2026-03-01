document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('.hamburger');
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.sidebar-overlay');
    if (!btn || !sidebar) return;

    function open() {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
        btn.setAttribute('aria-expanded', 'true');
    }
    function close() {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', function () {
        sidebar.classList.contains('open') ? close() : open();
    });
    if (overlay) overlay.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') close();
    });
});
