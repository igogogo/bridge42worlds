// bridge42worlds · структурированное раскрывающееся представление облака тегов/законов —
// ДЕФОЛТНЫЙ вид (юзер-фидбек 2026-07-20: плашки-treemap не зашли, нужно «более структурировано,
// раздел выбранный раскрывается»). Разделы (области науки / типы законов) — строки-аккордеон;
// клик по разделу раскрывает его элементы. Данные — те же window.__TREEMAP, что и у treemap.js.
(function () {
    var host = document.getElementById('treeview');
    var data = window.__TREEMAP;
    if (!host || !data || !data.groups) return;

    function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }

    host.innerHTML = data.groups.map(function (g) {
        var items = g.children.map(function (c) {
            return '<a class="tv-item" href="' + c.url + '"><span>' + esc(c.name) + '</span>' +
                (c.count ? '<b class="tv-n">' + c.count + '</b>' : '') + '</a>';
        }).join('');
        return '<div class="tv-group">' +
            '<button type="button" class="tv-head" aria-expanded="false">' +
            '<span class="tv-dot" style="background:' + g.color + '"></span>' +
            '<span class="tv-label">' + esc(g.label) + '</span>' +
            '<span class="tv-count">' + (g.children ? g.children.length : 0) + '</span>' +
            '<span class="tv-chev" aria-hidden="true">▸</span>' +
            '</button>' +
            '<div class="tv-body">' + items + '</div>' +
            '</div>';
    }).join('');

    host.querySelectorAll('.tv-head').forEach(function (h) {
        h.addEventListener('click', function () {
            var open = h.parentElement.classList.toggle('open');
            h.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    });
    window.__treeviewRender = function () { };  // CSS-аккордеон, пересчёт не нужен
})();
