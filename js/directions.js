/* ПРИЗНАК НАПРАВЛЕНИЯ НА СТРАНИЦЕ СТАТЬИ.
   Направление — не тег и не понятие: те рождаются из текста, а это решение человека —
   «эти работы мы собираем вместе, потому что так сейчас идёт наука» (владелец 18.09:
   «как я их найду, мне надо отдельный признак на эту тему»). Список номеров лежит в
   data/directions.json; тело статьи статично и о направлении не знает, поэтому плашку
   ставит этот скрипт: одна загрузка маленького файла, ни одной пересборки.
   Подключается из js/search.js рядом с metrics.js — то есть на всех собранных
   страницах архива; на чужих страницах молча выходит. */
(function () {
    if (window.b42Directions) return;
    window.b42Directions = true;

    var m = location.pathname.match(/^[/]lang[/]([a-z]{2})[/]archive[/][0-9]{4}-[0-9]{2}-[0-9]{2}[/]([^/]+)[/]/);
    if (!m) return;
    var L = m[1], id = m[2].replace(/v[0-9]+$/, '');
    var h1 = document.getElementById('article-top') || document.querySelector('.article-title-top');
    if (!h1) return;

    var WORD = { ru: 'Направление', en: 'Direction', es: 'Dirección', ar: 'اتجاه', fr: 'Direction', zh: '方向' }[L] || 'Direction';

    fetch('/data/directions.json?v=' + Math.floor(Date.now() / 600000))
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (D) {
            if (!D) return;
            var hits = [];
            Object.keys(D).forEach(function (k) {
                var d = D[k];
                (d.groups || []).forEach(function (g) {
                    if (g.ids.indexOf(id) >= 0) hits.push({ key: k, title: d.title, shelf: g.title });
                });
            });
            if (!hits.length) return;
            // Стиль — один раз, отсюда: плашка стоит на 32 тысячах страниц, а правка css
            // означала бы ждать пересборку ради кеш-хвоста в адресе.
            if (!document.getElementById('b42-dir-css')) {
                var st = document.createElement('style');
                st.id = 'b42-dir-css';
                st.textContent =
                    '.dir-row{display:block;margin:6px 0 14px}' +
                    // !important — не от хорошей жизни: у статьи есть общее правило на ссылки
                    // в теле, которое растягивает <a> во всю ширину и ставит детям display:block
                    // (замер 18.09: a — 600px, каждый span — блоком). Плашка обязана остаться
                    // плашкой на 32 тысячах страниц, не трогая их css.
                    '.dir-pill{display:inline-block!important;width:auto!important;max-width:100%;padding:5px 12px;margin:0 8px 6px 0;border-radius:16px;' +
                    'line-height:1.4;white-space:normal;' +
                    'border:1px solid color-mix(in srgb, var(--ochre, #c8842a) 45%, var(--hair, #ddd));' +
                    'background:color-mix(in srgb, var(--ochre, #c8842a) 8%, transparent);' +
                    'font-family:var(--mono);font-size:11.5px;letter-spacing:.04em;color:var(--text);text-decoration:none}' +
                    '.dir-pill:hover{border-color:var(--ochre, #c8842a);color:var(--ochre, #c8842a)}' +
                    '.dir-pill>*{display:inline!important;width:auto!important;margin:0 3px}' +
                    '.dir-pill b{font-weight:600}' +
                    '.dir-pill i{font-style:normal;color:var(--soft)}' +
                    '.dir-shelf{background:transparent;color:var(--muted)}';
                document.head.appendChild(st);
            }
            var row = document.createElement('div');
            row.className = 'dir-row';
            hits.forEach(function (h) {
                var a = document.createElement('a');
                a.className = 'dir-pill';
                a.href = '/directions.html?lang=' + L + '&d=' + encodeURIComponent(h.key);
                var t = (h.title && (h.title[L] || h.title.en)) || h.key;
                var s = (h.shelf && (h.shelf[L] || h.shelf.en)) || '';
                // Две плашки, а не одна длинная: название направления и его полка вместе
                // тянут на 80 знаков моно и в одной коробке ломались на две строки во всю
                // ширину колонки. Порознь они переносятся как слова.
                a.innerHTML = '<i>' + WORD + '</i><b></b>';
                a.querySelector('b').textContent = t;
                row.appendChild(a);
                if (s) {
                    var sh = document.createElement('a');
                    sh.className = 'dir-pill dir-shelf';
                    sh.href = a.href;
                    sh.textContent = s;
                    row.appendChild(sh);
                }
            });
            // Заголовок лежит в .title-row (flex-ряд с пружиной масштаба): вставка сразу
            // после h1 ставила плашку В ряд, сбоку от названия, коробкой в четыре строки.
            // Ставим строкой ПОД рядом заголовка, перед «Original: …».
            var anchor = (h1.closest && h1.closest('.title-row')) || h1;
            anchor.parentNode.insertBefore(row, anchor.nextSibling);
        })
        .catch(function () {});
})();
