/* Свой счётчик: кто зашёл, куда ходил, что нажимал. Без сторонних сервисов.
 *
 * Владелец 2026-07-31: «больше информации в статистику — кто зашёл, сколько, лайки,
 * отзывы; отделять себя от реальных пользователей; уходить от Supabase; куда ходили,
 * что нажимали, ретеншн, уникальные».
 *
 * Что собираем — и чего НЕ собираем:
 *   • обезличенный id устройства (случайное число в localStorage, ни к чему личному
 *     не привязано) — по нему считаются уникальные и возвраты;
 *   • id визита (sessionStorage) — сколько страниц за один заход;
 *   • путь страницы, язык, ширина экрана, домен реферера (домен, не адрес);
 *   • нажатия по нашим элементам: лайк, избранное, уровень чтения, сортировка, поиск,
 *     заказ перевода, отзыв, плашки сущностей;
 *   • глубину чтения (25/50/90%) — «зашёл и ушёл» и «дочитал» это разные читатели.
 *   НЕ собираем: тексты запросов и отзывов, вообще ничего вводимого руками, полный
 *   реферер с параметрами, IP (клиент его не знает, а Worker не пишет).
 *
 * Свои визиты помечаются: b42Metrics.markDev() ставит метку в этом браузере, и события
 * уходят с признаком d=1 — статистика читателей от них не портится (требование
 * владельца «отделять себя от реальных пользователей»).
 *
 * Файл подключается из js/search.js, то есть появляется без пересборки сайта.
 */
(function () {
    'use strict';
    if (window.b42Metrics) return;
    var EP = '/api/ev';
    var UID = 'b42_uid', SID = 'b42_sid', FIRST = 'b42_first', DEV = 'b42_dev';

    function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

    function uid() {
        var v = store(UID);
        if (!v) {
            v = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
            store(UID, v);
            store(FIRST, new Date().toISOString().slice(0, 10));
        }
        return v;
    }
    function sid() {
        try {
            var v = sessionStorage.getItem(SID);
            if (!v) { v = Math.random().toString(36).slice(2, 10); sessionStorage.setItem(SID, v); }
            return v;
        } catch (e) { return 'nosess'; }
    }
    function refHost() {
        try { return document.referrer ? new URL(document.referrer).hostname : ''; } catch (e) { return ''; }
    }

    function send(type, extra) {
        var ev = {
            t: type, p: location.pathname, l: document.documentElement.lang || '',
            u: uid(), s: sid(), f: store(FIRST) || '', r: refHost(),
            d: store(DEV) === '1' ? 1 : 0, w: window.innerWidth
        };
        if (extra) ev.x = String(extra).slice(0, 60);
        var body = JSON.stringify({ events: [ev] });
        // sendBeacon переживает уход со страницы — иначе последний просмотр теряется
        try {
            if (navigator.sendBeacon && navigator.sendBeacon(EP, new Blob([body], { type: 'application/json' }))) return;
        } catch (e) {}
        fetch(EP, { method: 'POST', headers: { 'content-type': 'application/json' },
                    body: body, keepalive: true }).catch(function () {});
    }

    send('view');

    document.addEventListener('click', function (e) {
        var el = e.target.closest && e.target.closest(
            '.fav-btn, .react-btn, .lv-btn, .feed-sort-btn, .translate-btn, .beta-send, ' +
            '.beta-mark, .ss-mode, .cat-chip, .side-tag, .side-law, .side-sci, .related-tags a');
        if (!el) return;
        var c = el.classList;
        var kind = c.contains('fav-btn') ? 'fav'
                 : c.contains('react-btn') ? (el.dataset.react || 'react')
                 : c.contains('lv-btn') ? 'level'
                 : c.contains('feed-sort-btn') ? 'sort'
                 : c.contains('translate-btn') ? 'order_translate'
                 : c.contains('beta-send') ? 'feedback'
                 : c.contains('beta-mark') ? 'beta_open'
                 : c.contains('ss-mode') ? 'search_mode'
                 : c.contains('cat-chip') ? 'category'
                 : 'entity';
        send('click', kind);
    }, true);

    var marks = { 25: false, 50: false, 90: false };
    window.addEventListener('scroll', function () {
        var h = document.documentElement.scrollHeight - window.innerHeight;
        if (h < 400) return;
        var pct = (window.scrollY / h) * 100;
        Object.keys(marks).forEach(function (m) {
            if (!marks[m] && pct >= Number(m)) { marks[m] = true; send('depth', m); }
        });
    }, { passive: true });

    window.b42Metrics = {
        send: send, uid: uid,
        markDev: function () { store(DEV, '1'); return 'устройство помечено тестовым: события идут с меткой d=1 и не портят статистику читателей'; },
        unmarkDev: function () { try { localStorage.removeItem(DEV); } catch (e) {} return 'метка снята'; }
    };
})();
