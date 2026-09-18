/* ПРИЗНАК НАПРАВЛЕНИЯ НА СТРАНИЦЕ СТАТЬИ И АНОНС НА ГЛАВНОЙ.
   Направление — не тег и не понятие: те рождаются из текста, а это решение человека —
   «эти работы мы собираем вместе, потому что так сейчас идёт наука» (владелец 18.09:
   «как я их найду, мне надо отдельный признак на эту тему»). Список номеров лежит в
   data/directions.json; тело статьи статично и о направлении не знает, поэтому плашку
   ставит этот скрипт: одна загрузка маленького файла, ни одной пересборки.
   На главной (владелец 18.09: «на главной странице тоже ссылку, анонс») — полоска
   с самым свежим направлением над лентой, тем же путём, без правки шаблона.
   Подключается из js/search.js рядом с metrics.js — то есть на всех собранных
   страницах архива; на чужих страницах молча выходит. */
(function () {
    if (window.b42Directions) return;
    window.b42Directions = true;

    var path = location.pathname;
    var art = path.match(/^[/]lang[/]([a-z]{2})[/]archive[/][0-9]{4}-[0-9]{2}-[0-9]{2}[/]([^/]+)[/]/);
    var idx = path.match(/^[/]lang[/]([a-z]{2})[/](index[.]html)?$/) || (path === '/' ? ['/', 'ru'] : null);
    if (!art && !idx) return;
    var L = art ? art[1] : idx[1];

    var T = {
        ru: { word: 'Направление', neu: 'Новое направление', works: 'работ', open: 'Открыть' },
        en: { word: 'Direction', neu: 'New direction', works: 'works', open: 'Open' },
        es: { word: 'Dirección', neu: 'Nueva dirección', works: 'trabajos', open: 'Abrir' },
        ar: { word: 'اتجاه', neu: 'اتجاه جديد', works: 'أعمال', open: 'افتح' },
        fr: { word: 'Direction', neu: 'Nouvelle direction', works: 'travaux', open: 'Ouvrir' },
        zh: { word: '方向', neu: '新方向', works: '篇', open: '打开' }
    }[L] || { word: 'Direction', neu: 'New direction', works: 'works', open: 'Open' };

    function css() {
        if (document.getElementById('b42-dir-css')) return;
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
            '.dir-shelf{background:transparent;color:var(--muted)}' +
            // Анонс на главной: одна полоска над лентой, в цветах бренда, не баннер.
            '.dir-ann{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin:10px auto 14px;padding:10px 14px;' +
            'max-width:var(--col-wide, 1100px);border-radius:12px;' +
            'border:1px solid color-mix(in srgb, var(--ochre, #c8842a) 40%, var(--hair, #ddd));' +
            'background:color-mix(in srgb, var(--ochre, #c8842a) 7%, var(--surface, transparent));text-decoration:none;color:var(--text)}' +
            '.dir-ann:hover{border-color:var(--ochre, #c8842a)}' +
            '.dir-ann .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ochre, #c8842a)}' +
            '.dir-ann .t{font-family:var(--font-display);font-size:16px;font-weight:600;line-height:1.3}' +
            '.dir-ann .n{font-family:var(--mono);font-size:11.5px;color:var(--soft);margin-inline-start:auto;white-space:nowrap}' +
            '.dir-ann .n b{font-weight:600;color:var(--text)}';
        document.head.appendChild(st);
    }

    fetch('/data/directions.json?v=' + Math.floor(Date.now() / 600000))
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (D) {
            if (!D) return;
            if (art) article(D, art[2].replace(/v[0-9]+$/, ''));
            else announce(D);
        })
        .catch(function () {});

    function article(D, id) {
        var h1 = document.getElementById('article-top') || document.querySelector('.article-title-top');
        if (!h1) return;
        var hits = [];
        Object.keys(D).forEach(function (k) {
            var d = D[k];
            (d.groups || []).forEach(function (g) {
                if (g.ids.indexOf(id) >= 0) hits.push({ key: k, title: d.title, shelf: g.title });
            });
        });
        if (!hits.length) return;
        css();
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
            a.innerHTML = '<i>' + T.word + '</i><b></b>';
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
    }

    function announce(D) {
        // Самое свежее направление по дате открытия; полоска над разделами и лентой.
        var keys = Object.keys(D).sort(function (a, b) { return (D[b].opened || '').localeCompare(D[a].opened || ''); });
        if (!keys.length) return;
        var k = keys[0], d = D[k];
        var slot = document.getElementById('category-bar') || document.getElementById('search-results');
        if (!slot) return;
        var n = (d.groups || []).reduce(function (s, g) { return s + g.ids.length; }, 0);
        css();
        var a = document.createElement('a');
        a.className = 'dir-ann';
        a.href = '/directions.html?lang=' + L + '&d=' + encodeURIComponent(k);
        a.innerHTML = '<span class="k"></span><span class="t"></span><span class="n"><b></b> ' + T.works + ' · ' + T.open + ' →</span>';
        a.querySelector('.k').textContent = T.neu;
        a.querySelector('.t').textContent = (d.title && (d.title[L] || d.title.en)) || k;
        a.querySelector('.n b').textContent = n;
        slot.parentNode.insertBefore(a, slot);
    }
})();
