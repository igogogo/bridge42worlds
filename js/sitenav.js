/* Навигация по сайту для самостоятельных страниц (learn, course, mathkit, reference, lecture,
   discoveries, hypotheses, frontier, course-thermodynamics).
   Зачем: у этих страниц своя минимальная шапка (логотип + тема + языки) и они НЕ подключают
   search.js, который на остальном сайте строит меню и кнопку ☰. Из-за этого с урока некуда
   уйти — тупик: нашли страницу поиском, а на сайт не попасть (находка тестирования 2026-07-29,
   в отчёте она звучала как «не открывается мобильное меню-гамбургер» — на самом деле его там
   нет вовсе).
   Что делает: вставляет в .top-bar кнопку ☰ с полным меню сайта — с названиями пунктов
   на языке страницы (словарь NAV_I18N ниже). Разметка и классы те же, что у search.js
   (.nav-more / .nav-more-btn / .nav-more-panel), поэтому стили и RTL уже работают
   из css/style.css, свои стили не нужны. */
(function () {
    var bar = document.querySelector('.top-bar');
    if (!bar) return;
    // Страница уже с меню (search.js успел отработать или разметка своя) — второе не нужно.
    if (bar.querySelector('.nav-more') || bar.querySelector('.nav-links')) return;

    var LANGS = ['ru', 'en', 'es', 'ar', 'fr'];

    /* Язык меню = язык страницы, и решает его САМА страница.
       Раньше здесь первым читался ?lang= из адреса, и на этом мы расходились с хозяином
       страницы: у всех двенадцати страниц со шторкой свой разбор языка (?lang= → сохранённый
       b42_lang → ru), результат которого лежит в window.B42_LANG. Открой /research.html?lang=de
       с сохранённым французским — страница честно показывала французский, а меню строило
       русские подписи и ссылки /lang/ru/…; вдобавок course-i18n.js, переводящий по точному
       русскому тексту узла, начинал править отдельные пункты, и в одном столбце оказывались
       «Теги», «Lois» и «Разделы» (поймано при проверке). Спрашиваем страницу, а не адрес. */
    function lang() {
        var v = window.B42_LANG || document.documentElement.getAttribute('lang');
        if (!v) {
            try { v = new URLSearchParams(location.search).get('lang'); } catch (e) {}
        }
        // Чужое значение (?lang=de от переводчика, забытый lang="en-US" в разметке) раньше
        // проходило насквозь и собирало ссылки вида /lang/de/tags/ — то есть меню молча
        // вело в 404. Сводим к пяти языкам, которые у нас реально есть.
        v = String(v || '').slice(0, 2).toLowerCase();
        return LANGS.indexOf(v) >= 0 ? v : 'ru';
    }

    var L = lang();

    /* ── Названия пунктов на пяти языках ──────────────────────────────────────────────
       До этого в шторке стояли сырые ключи латиницей — about, tags, laws… — одинаково
       на русском, испанском и арабском. Читатель-араб видел латинский столбик и не мог
       понять, куда какая строка ведёт (аудит, п. 6.1).
       Словарь ЛОКАЛЬНЫЙ и намеренно: js/course-i18n.js переводит содержимое курса и бьётся
       по русскому тексту узла, а здесь переводятся 12 постоянных ярлыков навигации —
       разные жизни, общий словарь связал бы шторку с курсом без нужды.
       Формулировки взяты не из головы, а с самих страниц назначения (их <title> на нужном
       языке), чтобы пункт меню и заголовок раздела назывались одинаково: «Граф знаний» →
       «Граф знаний», «Карта проекта» → «Карта проекта». Где заголовок раздела ещё
       по-английски (Tags, Scientists), пункт всё равно переведён — меню читают чаще.
       Арабские подписи — существительные («اتجاهات البحث», а не вопрос «что исследовать»):
       в арабском меню вопросительный оборот читается как обращение к читателю, а не как
       имя раздела. */
    var NAV_I18N = {
        about:      { ru: 'Гид',               en: 'Guide',           es: 'Guía',                 ar: 'الدليل',        fr: 'Guide' },
        main:       { ru: 'Главная',           en: 'Home',            es: 'Inicio',               ar: 'الرئيسية',      fr: 'Accueil' },
        laws:       { ru: 'Понятия',           en: 'Concepts',        es: 'Conceptos',            ar: 'المفاهيم',      fr: 'Concepts' },
        comments:   { ru: 'Комментарии',       en: 'Comments',        es: 'Comentarios',          ar: 'التعليقات',     fr: 'Commentaires' },
        scientists: { ru: 'Учёные',            en: 'Scientists',      es: 'Científicos',          ar: 'العلماء',       fr: 'Scientifiques' },
        sections:   { ru: 'Разделы',           en: 'Sections',        es: 'Secciones',            ar: 'الأقسام',       fr: 'Sections' },
        authors:    { ru: 'Авторы',            en: 'Authors',         es: 'Autores',              ar: 'المؤلفون',      fr: 'Auteurs' },
        graph:      { ru: 'Граф знаний',       en: 'Knowledge graph', es: 'Red de conocimiento',  ar: 'شبكة المعرفة',  fr: 'Graphe des savoirs' },
        learn:      { ru: 'Учебник',           en: 'Learn',           es: 'Curso',                ar: 'تعلّم',          fr: 'Cours' },
        analytics:  { ru: 'Карта проекта',     en: 'Project map',     es: 'Mapa del proyecto',    ar: 'خريطة المشروع', fr: 'Carte du projet' },
        research:   { ru: 'Что исследовать',   en: 'What to explore', es: 'Qué investigar',       ar: 'اتجاهات البحث', fr: 'Quoi explorer' },
        community:  { ru: 'Авторские работы',  en: 'Author works',    es: 'Trabajos de autor',    ar: 'أعمال المؤلفين', fr: 'Travaux d’auteurs' }
    };
    var MENU_I18N = { ru: 'Меню', en: 'Menu', es: 'Menú', ar: 'القائمة', fr: 'Menu' };

    function label(key) {
        var t = NAV_I18N[key];
        // Пункт без перевода лучше показать ключом, чем спрятать: раздел останется
        // достижимым, а пропуск сразу видно глазом.
        return (t && (t[L] || t.en)) || key;
    }

    /* Знак учебника — та же книга, что стоит иконкой в шапке основного сайта
       (templates/index.html, ссылка /learn.html). Рисунок повторён здесь, а не взят из
       B42Icons, потому что icons.js подключён не на всех страницах со шторкой
       (research.html, ask.html его не грузят) — иначе знак появлялся бы через раз. */
    var BOOK_SVG = '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ' +
        'width="15" height="15"><path d="M4 6.5A2 2 0 0 1 6 5h5v14H6a2 2 0 0 0-2 1.5z"/>' +
        '<path d="M20 6.5A2 2 0 0 0 18 5h-5v14h5a2 2 0 0 1 2 1.5z"/></svg>';

    var items = [
        // Гид стоит ПЕРВЫМ (владелец 2026-08-06: «about во-первых в меню, на самый верх»).
        // Он объясняет, что здесь есть и как этим пользоваться, — человеку, попавшему сюда
        // впервые, это нужнее ленты, а тот, кто уже читает, в меню и не заглядывает.
        ['about', '/lang/' + L + '/about.html'],
        // ── Учебник — ВТОРЫМ, сразу за гидом ─────────────────────────────────────────
        // Аудит, п. 6.1: «вход в раздел почти невидим». Раньше пункт стоял девятым, звался
        // «learn» и на телефоне оказывался ниже сгиба — раздел находили случайно.
        // Договорённость владельца («about на самый верх») не тронута: гид остался первым,
        // подвинулись пункты ПОСЛЕ него. Порядок теперь читается как вход: сначала «что
        // это такое», потом «с чего начать читать», и только потом справочные разделы
        // (теги, законы, учёные), в которые идут за конкретным именем, а не осматриваться.
        // Второй знак — иконка книги: единственная картинка в столбце слов ловит глаз без
        // всякого «НОВОЕ!», не устаревает и повторяет знак учебника из шапки сайта, так что
        // читатель узнаёт его, а не разгадывает.
        ['learn', '/learn.html', 'mark'],
        ['main', '/lang/' + L + '/index.html'],
        // ПОНЯТИЯ — главный раздел знания, и в шторке его не было вовсе. Стоял
        // 'laws' — витрина, которая с 24 августа только переадресует в понятия:
        // читатель, искавший в меню «понятия», не находил ничего, а найдя
        // «laws», попадал через прыжок (владелец 28.08: «где в меню ссылка на
        // понятия»). Ставим сразу за лентой: это второе, куда идут.
        ['concepts', '/lang/' + L + '/concepts/'],
        ['comments', '/lang/' + L + '/comments.html'],
        ['scientists', '/lang/' + L + '/scientists/'],
        ['sections', '/lang/' + L + '/sections/'],
        // Авторы собраны только по-английски (решение: имена не переводятся, −600МБ),
        // раздел работает — ведём читателя любого языка в en, а не прячем пункт.
        ['authors', '/lang/en/authors/'],
        // Граф ведёт в НОВЫЙ, живой: /lang/{L}/graph/ — прежнее полотно по тегам
        // и законам, оно осталось от старого устройства. Сегодняшний граф живёт
        // внутри раздела понятий и собирается запросом из облака.
        ['graph', '/lang/' + L + '/concepts/graph.html'],
        // theory — старый раздел, удалён решением владельца (2026-07-23 «старая часть
        // в архив», подтверждено 2026-07-29): пункт вёл в 404 на всех языках.
        ['analytics', '/lang/' + L + '/analytics/'],
        // «Что исследовать» — раздел с направлениями и планами работы. Владелец
        // 12 августа: «отдельным разделом в меню; возможно, потом это будет вход
        // для чат-бота-исследователя». Страница одна на все языки, поэтому язык
        // передаём параметром, как учебным материалам.
        ['research', '/research.html?lang=' + L],
        // Авторские работы — последними, как и в главном меню: раздел неприметный
        // по решению владельца, но найти его должно быть можно.
        ['community', '/lang/' + L + '/community/']
    ];

    /* Страницы учебника, кроме самой /learn.html: с них пункт «Учебник» должен светиться
       как текущий раздел — иначе в шторке не видно, где ты стоишь (на /course.html активным
       не был ни один пункт, и шторка выглядела одинаково везде). */
    var LEARN_PAGES = ['/learn.html', '/course.html', '/course-thermodynamics.html',
        '/lecture.html', '/mathkit.html', '/reference.html', '/memo.html'];

    var wrap = document.createElement('div');
    wrap.className = 'nav-more';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-more-btn';
    btn.setAttribute('aria-label', MENU_I18N[L] || MENU_I18N.en);
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>';

    var panel = document.createElement('div');
    panel.className = 'nav-more-panel';
    /* Пока пункты звались «tags» и «graph», в шторку шириной 140px (min-width из css/style.css)
       влезало любое слово. Человеческие названия длиннее — «Что исследовать», «Graphe des
       savoirs», — и на десктопе они переносились на вторую строку: столбик получался рваный,
       из двенадцати пунктов три в два этажа. Запрещаем перенос: шторка позиционирована
       абсолютно и просто становится шире самого длинного названия. На телефоне она и так
       во всю ширину экрана (375px против ~150px самой длинной подписи) — там ничего не меняется. */
    panel.style.whiteSpace = 'nowrap';

    var here = location.pathname;
    items.forEach(function (it) {
        var a = document.createElement('a');
        a.href = it[1];
        // Сравнивать надо путь с путём: у «Что исследовать» в адресе висит ?lang=,
        // и сравнение целой строки не совпадало никогда — пункт не подсвечивался
        // даже на своей же странице.
        var path = it[1].split('?')[0];
        var mine = (here === path) || (path.length > 1 && here.indexOf(path) === 0);
        if (it[0] === 'learn') mine = LEARN_PAGES.indexOf(here) >= 0;

        if (it[2] === 'mark') {
            // Класс .nav-moved уже описан в css/style.css именно как «значок слева, подпись
            // рядом» внутри шторки (flex, gap, RTL через направление документа) — берём
            // готовое правило, а не заводим своё.
            a.className = 'nav-moved';
            a.innerHTML = BOOK_SVG;
            var t = document.createElement('span');
            t.textContent = label(it[0]);
            a.appendChild(t);
        } else {
            a.textContent = label(it[0]);
        }

        // Пункты шторки набраны моноширинным (css/style.css, .nav-more-panel a) — под латиницу,
        // которая тут стояла раньше. В моноширинных наборах арабских букв нет, и браузер
        // подставляет их по одной: связки рвутся, слово расползается «ا ل د ل ي ل». Для
        // арабского берём тот же гротеск, что и в тексте страницы. Проверено на 375px:
        // с моно буквы стояли враскоряку, с var(--sans) слово выглядит словом.
        if (L === 'ar') a.style.fontFamily = 'var(--sans)';

        if (mine) {
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
