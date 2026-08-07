/* Навигация по сайту для самостоятельных страниц (learn, course, mathkit, reference, lecture,
   discoveries, hypotheses, frontier, course-thermodynamics).
   Зачем: у этих страниц своя минимальная шапка (логотип + тема + языки) и они НЕ подключают
   search.js, который на остальном сайте строит меню и кнопку ☰. Из-за этого с урока некуда
   уйти — тупик: нашли страницу поиском, а на сайт не попасть (находка тестирования 2026-07-29,
   в отчёте она звучала как «не открывается мобильное меню-гамбургер» — на самом деле его там
   нет вовсе).
   Что делает: вставляет в .top-bar кнопку ☰ с полным меню сайта. Разметка и классы те же,
   что у search.js (.nav-more / .nav-more-btn / .nav-more-panel), поэтому стили и RTL уже
   работают из css/style.css, свои стили не нужны. */
(function () {
    var bar = document.querySelector('.top-bar');
    if (!bar) return;
    // Страница уже с меню (search.js успел отработать или разметка своя) — второе не нужно.
    if (bar.querySelector('.nav-more') || bar.querySelector('.nav-links')) return;

    function lang() {
        try {
            var q = new URLSearchParams(location.search).get('lang');
            if (q) return q;
        } catch (e) {}
        return window.B42_LANG || document.documentElement.getAttribute('lang') || 'ru';
    }

    var L = lang();
    var items = [
        // Гид стоит ПЕРВЫМ (владелец 2026-08-06: «about во-первых в меню, на самый верх»).
        // Он объясняет, что здесь есть и как этим пользоваться, — человеку, попавшему сюда
        // впервые, это нужнее ленты, а тот, кто уже читает, в меню и не заглядывает.
        ['about', '/lang/' + L + '/about.html'],
        ['main', '/lang/' + L + '/index.html'],
        ['tags', '/lang/' + L + '/tags/'],
        ['laws', '/lang/' + L + '/laws/'],
        ['scientists', '/lang/' + L + '/scientists/'],
        ['sections', '/lang/' + L + '/sections/'],
        // Авторы собраны только по-английски (решение: имена не переводятся, −600МБ),
        // раздел работает — ведём читателя любого языка в en, а не прячем пункт.
        ['authors', '/lang/en/authors/'],
        ['graph', '/lang/' + L + '/graph/'],
        // theory — старый раздел, удалён решением владельца (2026-07-23 «старая часть
        // в архив», подтверждено 2026-07-29): пункт вёл в 404 на всех языках.
        ['learn', '/learn.html'],
        ['analytics', '/lang/' + L + '/analytics/'],
        // Авторские работы — последними, как и в главном меню: раздел неприметный
        // по решению владельца, но найти его должно быть можно.
        ['community', '/lang/' + L + '/community/']
    ];

    var wrap = document.createElement('div');
    wrap.className = 'nav-more';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-more-btn';
    btn.setAttribute('aria-label', 'Menu');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>';

    var panel = document.createElement('div');
    panel.className = 'nav-more-panel';

    var here = location.pathname;
    items.forEach(function (it) {
        var a = document.createElement('a');
        a.href = it[1];
        a.textContent = it[0];
        if (here === it[1] || (it[1].length > 1 && here.indexOf(it[1]) === 0)) {
            a.classList.add('active');
            btn.classList.add('active');
        }
        panel.appendChild(a);
    });

    wrap.appendChild(btn);
    wrap.appendChild(panel);

    // Место кнопки — сразу после названия, как на всём сайте (там ☰ стоит вплотную к логотипу,
    // см. `.brand-row > .nav-more` в css/style.css). У .top-bar здесь justify-content:space-between,
    // поэтому мало вставить кнопку — надо ещё оттолкнуть вправо всё, что идёт следом, иначе
    // элементы распределятся поровну и ☰ повиснет посреди шапки.
    var logo = bar.querySelector('.logo');
    if (logo && logo.parentNode === bar) {
        bar.insertBefore(wrap, logo.nextSibling);
        var after = wrap.nextElementSibling;
        if (after) after.style.marginInlineStart = 'auto';
    } else {
        bar.appendChild(wrap);
    }

    /* Языки — отдельной строкой под шапкой, как на всём сайте. На этих страницах переключатель
       языков исторически стоит внутри .top-bar, а стандарт сайта — блок .langs в строке
       .langs-row под шапкой (см. templates/index.html и `.langs-row` в css/style.css).
       Из-за этого шапка учебных страниц выглядела иначе, чем везде. */
    var langsRow = null;

    function ensureLangsRow() {
        if (langsRow || document.querySelector('.langs-row')) return true;
        var langs = bar.querySelector('.langs');
        if (!langs) return false;
        langsRow = document.createElement('div');
        langsRow.className = 'langs-row';
        langsRow.appendChild(langs);
        if (bar.nextSibling) bar.parentNode.insertBefore(langsRow, bar.nextSibling);
        else bar.parentNode.appendChild(langsRow);
        return true;
    }

    /* Переключатель языков на этих страницах рисует их собственный скрипт, и он отрабатывает
       ПОЗЖЕ нашего — поэтому просто найти .langs при старте не выходит, ждём появления. */
    if (!ensureLangsRow()) {
        var mo = new MutationObserver(function () {
            if (ensureLangsRow()) {
                mo.disconnect();
                alignToContent();
            }
        });
        mo.observe(document.body, { childList: true, subtree: true });
        setTimeout(function () { mo.disconnect(); }, 8000);
    }

    function setOpen(v) {
        wrap.classList.toggle('open', v);
        btn.setAttribute('aria-expanded', v ? 'true' : 'false');
    }
    btn.addEventListener('click', function (e) {
        e.stopPropagation();
        setOpen(!wrap.classList.contains('open'));
    });
    document.addEventListener('click', function (e) {
        if (wrap.classList.contains('open') && !wrap.contains(e.target)) setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') setOpen(false);
    });

    /* Ширина шапки = ширина страницы. Наше правило, и оно тут нарушалось: в общем CSS у .top-bar
       стоит max-width 620px (это колонка статьи), а учебные страницы шире — 900-1060px. На 1280px
       контент начинался с 198-го пикселя, а шапка с 446-го: меню уезжало от текста на 248px.
       Ширина у этих девяти страниц разная, поэтому не прописываем число, а равняемся на реальный
       контентный блок страницы. */
    function alignToContent() {
        // Эталон ширины — САМЫЙ ШИРОКИЙ из именованных кандидатов И прямых детей body.
        // Просто первый кандидат не годится: в mathkit #root — правая колонка грида,
        // и равнение по нему уводило шапку на 224px от текста (QA 2026-07-29). Дети body
        // в переборе обязательны: страничный контейнер грида может не носить ни одного
        // из ожидаемых имён.
        var cand = null;
        function consider(el) {
            if (!el || el === bar || el === langsRow || !el.getBoundingClientRect) return;
            var w = el.getBoundingClientRect().width;
            if (w > 0 && (!cand || w > cand.getBoundingClientRect().width)) cand = el;
        }
        [].forEach.call(document.querySelectorAll('#root, main, .wrap, .container'), consider);
        [].forEach.call(document.body.children, consider);
        if (!cand) return;
        var target = cand.getBoundingClientRect();
        // .langs-row в общем CSS тоже ограничена (680px) — равняем её по тому же контенту,
        // иначе строка языков разъедется с текстом ровно так же, как разъезжалась шапка.
        [bar, langsRow].forEach(function (el) {
            if (!el) return;
            el.style.maxWidth = 'none';
            el.style.width = Math.round(target.width) + 'px';
            var delta = Math.round(target.left - el.getBoundingClientRect().left);
            if (Math.abs(delta) > 1) {
                var cs = getComputedStyle(el);
                var cur = parseFloat(cs.marginInlineStart) || 0;
                // delta посчитан в ФИЗИЧЕСКИХ левых координатах, а margin-inline-start в RTL
                // — это правое поле: рост поля двигает блок ВЛЕВО. Без учёта направления
                // поправка удваивала ошибку и с каждым resize уводила шапку за край (QA).
                var sign = cs.direction === 'rtl' ? -1 : 1;
                el.style.marginInlineStart = (cur + delta * sign) + 'px';
            }
        });
    }

    alignToContent();
    var t = null;
    window.addEventListener('resize', function () {
        clearTimeout(t);
        t = setTimeout(alignToContent, 120);
    });
})();
