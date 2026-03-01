document.addEventListener('DOMContentLoaded', function () {
    var boxes = document.querySelectorAll('.help-box');
    var PAGE_KEY = 'helpCollapsed:' + location.pathname;
    var collapsed = localStorage.getItem(PAGE_KEY) === '1';

    boxes.forEach(function (box) {
        var toggle = document.createElement('button');
        toggle.className = 'help-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        toggle.textContent = collapsed ? 'Show help' : 'Hide help';

        var wrapper = document.createElement('div');
        wrapper.className = 'help-body';
        if (collapsed) wrapper.classList.add('collapsed');

        while (box.firstChild) {
            wrapper.appendChild(box.firstChild);
        }

        box.appendChild(toggle);
        box.appendChild(wrapper);

        toggle.addEventListener('click', function () {
            var isCollapsed = wrapper.classList.toggle('collapsed');
            toggle.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
            toggle.textContent = isCollapsed ? 'Show help' : 'Hide help';
            localStorage.setItem(PAGE_KEY, isCollapsed ? '1' : '0');
        });
    });
});
