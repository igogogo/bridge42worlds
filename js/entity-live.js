/* Страницы сущностей на живых данных: тег, закон, учёный, раздел — одна логика.
 *
 * Владелец 25 августа: «всю динамику реализовать, потому что автор просто частный случай —
 * так сразу решишь задачу в целом». Ровно это здесь и сделано: модуль один, вид сущности
 * приходит из разметки, различий в коде между тегом и разделом нет вовсе.
 *
 * ЧТО МЕНЯЕТСЯ ДЛЯ ЧИТАТЕЛЯ. Раньше страница тега ждала полный индекс ленты (3.7 МБ по
 * сети) и фильтровала его на месте; теперь список приходит из D1 страницами по 7 КБ.
 * Плюс сводка, которой не было: сколько работ, каких, годы, столбики по годам.
 *
 * ЧТО МЕНЯЕТСЯ ДЛЯ НАС. Правка связей (тег переехал, закон переименован) — это заливка
 * строк в базу, а не пересборка страниц. Полная пересборка, как выяснилось 25 августа,
 * стоит ещё и живых денег: ~$1.30 операций записи R2 за прогон.
 *
 * Вшитый при сборке список остаётся в HTML как содержимое для поисковиков и как запасной
 * вариант: если облако не ответило, страница выглядит ровно как до этого модуля.
 */
(function () {
    'use strict';

    var box = document.getElementById('search-results');
    if (!box || !box.dataset) return;

    // Вид сущности — из той же разметки, которой пользуется search.js. Отдельного атрибута
    // не заводим: два источника правды разъезжаются, а этот уже проверен временем.
    var kind = null, key = null;
    if (box.dataset.contextTag) { kind = 'tag'; key = box.dataset.contextTag; }
    else if (box.dataset.contextScientist) { kind = 'sci'; key = box.dataset.contextScientist; }
    else if (box.dataset.contextCategory) { kind = 'cat'; key = box.dataset.contextCategory; }
    // Закон: контейнер размечен как data-context-tag с ОСНОВНЫМ тегом закона, и у части
    // законов он пуст (закон родился не из тега). Идентификатор закона надёжнее взять из
    // адреса — /laws/<id>.html, он и есть ключ в card_links kind='law'.
    if ((!key || kind === null) && location.pathname.indexOf('/laws/') !== -1) {
        var lm = location.pathname.match(/\/laws\/([^/]+)\.html/);
        if (lm) { kind = 'law'; key = decodeURIComponent(lm[1]); }
    }
    if (!kind || !key || box.dataset.akey) return;   // автор живёт своим модулем

    // Страница закона размечена как data-context-tag=основной тег закона — так же её
    // понимает и search.js; для нас это просто тег.

    var PAGE = 20;
    var L = (document.documentElement.lang || 'en').slice(0, 2);
    var T = {
        ru: { more: 'Показать ещё', loading: 'Загружаю…',
              works: ['работа', 'работы', 'работ'], express: 'экспресс', full: 'полных',
              km: 'с разбором' },
        en: { more: 'Show more', loading: 'Loading…',
              works: ['paper', 'papers'], express: 'express', full: 'full', km: 'with our notes' },
        es: { more: 'Ver más', loading: 'Cargando…',
              works: ['trabajo', 'trabajos'], express: 'exprés', full: 'completos', km: 'con notas' },
        ar: { more: 'عرض المزيد', loading: 'جارٍ التحميل…',
              works: ['بحث', 'أبحاث'], express: 'موجزة', full: 'كاملة', km: 'مع ملاحظاتنا' },
        fr: { more: 'Voir plus', loading: 'Chargement…',
              works: ['travail', 'travaux'], express: 'express', full: 'complets', km: 'avec notes' }
    }[L];
    if (!T) return;

    var API = (typeof window.B42_API === 'string' ? window.B42_API : '');

    function ver() { return (typeof effVersion === 'function' ? effVersion() : 'popular'); }

    function nWorks(n) {
        var f = T.works;
        if (f.length === 3) {
            var d = n % 10, h = n % 100;
            return n + ' ' + (d === 1 && h !== 11 ? f[0]
                : (d >= 2 && d <= 4 && (h < 12 || h > 14)) ? f[1] : f[2]);
        }
        return n + ' ' + (n === 1 ? f[0] : f[1]);
    }

    function cards(items) {
        var v = ver();
        return items.map(function (a) {
            a.version = v;
            return (typeof cardHTML === 'function') ? cardHTML(a) : '';
        }).join('');
    }

    var page = 0, busy = false, done = false;

    function fetchPage(p) {
        return fetch(API + '/api/list?kind=' + kind + '&key=' + encodeURIComponent(key) +
                     '&lang=' + L + '&version=' + ver() + '&limit=' + PAGE + '&page=' + p)
            .then(function (r) { return r.ok ? r.json() : null; });
    }

    function mountMore() {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'agroup-more';
        b.textContent = T.more;
        b.addEventListener('click', function () {
            if (busy) return;
            busy = true;
            b.disabled = true; b.textContent = T.loading;
            fetchPage(page + 1).then(function (d) {
                busy = false;
                if (!d || !d.items || !d.items.length) { b.remove(); done = true; return; }
                page += 1;
                b.insertAdjacentHTML('beforebegin', cards(d.items));
                if (d.more) { b.disabled = false; b.textContent = T.more; }
                else { b.remove(); done = true; }
                if (typeof initAllTooltips === 'function') initAllTooltips();
                if (typeof initReveal === 'function') initReveal();
            }).catch(function () { busy = false; b.disabled = false; b.textContent = T.more; });
        });
        box.appendChild(b);
    }

    function drawStats() {
        fetch(API + '/api/entity?kind=' + kind + '&key=' + encodeURIComponent(key))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (s) {
                if (!s || !s.found || !s.total) return;
                var top = document.querySelector('.tag-stats');
                if (!top) return;
                var bits = [nWorks(s.total)];
                if (s.express) bits.push(s.express + ' ' + T.express);
                if (s.full) bits.push(s.full + ' ' + T.full);
                if (s.km) bits.push(s.km + ' ' + T.km);
                var y = (s.first || '').slice(0, 4);
                if (y && (s.last || '').slice(0, 4) !== y) y += '–' + (s.last || '').slice(0, 4);
                if (y) bits.push(y);
                var ico = top.querySelector('svg');
                top.innerHTML = (ico ? ico.outerHTML + ' ' : '') + bits.join(' · ')
                    .replace(/&/g, '&amp;').replace(/</g, '&lt;');
                // Столбики по годам — маленький дашборд сущности, как у автора.
                var ys = Object.keys(s.byYear || {}).sort();
                if (ys.length > 1) {
                    var mx = Math.max.apply(null, ys.map(function (k) { return s.byYear[k]; }));
                    var bars = ys.slice(-14).map(function (k) {
                        var h = Math.max(3, Math.round(s.byYear[k] * 34 / mx));
                        return '<span class="ebar" title="' + k + ': ' + s.byYear[k] + '"' +
                               ' style="height:' + h + 'px"></span>';
                    }).join('');
                    // перерисовка не должна плодить второй ряд столбиков
                    var old = document.querySelector('.ebars');
                    if (old) old.remove();
                    top.insertAdjacentHTML('afterend',
                        '<div class="ebars" aria-hidden="true">' + bars + '</div>');
                }
            }).catch(function () {});
    }

    /* Страница /laws/ бывает двух пород: настоящий закон (hawking_radiation) и понятие —
       бывший тег, влитый в облако законов при слиянии (black_hole). Внешне они одинаковы,
       а в связях живут под разными видами. Спрашиваем как закон; пусто — спрашиваем как
       тег. Один лишний запрос на 2 КБ у части страниц дешевле, чем таскать различие пород
       через разметку. */
    var lawFallback = (kind === 'law');

    function boot() {
        if (window.B42Live) B42Live.pending(box);
        fetchPage(0).then(function (d) {
            if ((!d || !d.items || !d.items.length) && lawFallback) {
                lawFallback = false;
                kind = 'tag';
                boot();
                return;
            }
            // Облако молчит — страница остаётся такой, какой её собрала статика.
            if (!d || !d.items || !d.items.length) {
                if (window.B42Live) B42Live.fail(box);
                return;
            }
            if (window.B42Live) B42Live.swap(box, cards(d.items));
            else box.innerHTML = cards(d.items);
            if (d.more) mountMore();
            box.dataset.live = '1';
            if (typeof initAllTooltips === 'function') initAllTooltips();
            if (typeof initReveal === 'function') initReveal();
        }).catch(function () { if (window.B42Live) B42Live.fail(box); });
        drawStats();
    }

    // Перерисовка по требованию — search.js зовёт при смене уровня или сбросе поиска.
    window.B42EntityLive = function () { page = 0; done = false; boot(); };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
