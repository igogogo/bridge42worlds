/* icons.js — свой набор иконок для учебных материалов.
   Вместо эмодзи (которые выглядят по-разному в каждой ОС и ломают строгий вид страницы) —
   единый штриховой набор в стиле наших theory-статей: тонкая линия, никакой заливки,
   цвет наследуется от текста (currentColor), поэтому иконка живёт в любой теме.

   Использование:  B42Icons.lamp()  →  строка со <svg>;  B42Icons.lamp(20) — размер в px. */
(function (global) {
    'use strict';

    function wrap(size, body) {
        var s = size || 18;
        return '<svg class="b42-ic" width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" ' +
            'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" ' +
            'aria-hidden="true">' + body + '</svg>';
    }

    var I = {
        // мнемоника — узелок на память
        mnemo: function (s) {
            return wrap(s, '<path d="M5 8c3.5 0 3.5 8 7 8s3.5-8 7-8"/>' +
                '<path d="M5 16c3.5 0 3.5-8 7-8s3.5 8 7 8"/><circle cx="12" cy="12" r="1.6"/>');
        },
        // занимательный факт — восклицательный знак в круге, «а вы знали»
        fact: function (s) {
            return wrap(s, '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.4h.01"/>');
        },
        // формула — как в тетради, за скобками
        formula: function (s) {
            return wrap(s, '<path d="M6 4c-1.6 0-2.4 1-2.4 2.6v3.2c0 1.2-.6 2.2-1.6 2.2 1 0 1.6 1 1.6 2.2v3.2C3.6 19 4.4 20 6 20"/>' +
                '<path d="M18 4c1.6 0 2.4 1 2.4 2.6v3.2c0 1.2.6 2.2 1.6 2.2-1 0-1.6 1-1.6 2.2v3.2c0 1.6-.8 2.6-2.4 2.6"/>' +
                '<path d="M9 9.5h6"/><path d="M9 14.5h6"/>');
        },
        // опыт дома по Перельману — кухонный стакан и ложка
        kitchen: function (s) {
            return wrap(s, '<path d="M7 4h8l-1 15a2 2 0 0 1-2 1.8h-2A2 2 0 0 1 8 19z"/>' +
                '<path d="M7.4 11h7.2"/><path d="M19 4v7a2 2 0 0 1-2 2"/>');
        },
        // парадокс / вопрос на подумать
        paradox: function (s) {
            return wrap(s, '<circle cx="12" cy="12" r="9"/>' +
                '<path d="M9.2 9.4a2.9 2.9 0 0 1 5.6 1c0 1.9-2.8 2.3-2.8 4"/><path d="M12 17.4h.01"/>');
        },
        // граница применимости — знак «дальше не работает»
        edge: function (s) {
            return wrap(s, '<path d="M3 12h7"/><path d="M14 12h7" stroke-dasharray="2.4 2.6"/>' +
                '<path d="M12 4.5v15"/>');
        },
        // порядок величины — прикидка на глаз
        estimate: function (s) {
            return wrap(s, '<path d="M3 17h4l3-9 3 13 3-11 2 7h3"/>');
        },
        // внимание / важная мысль
        lamp: function (s) {
            return wrap(s, '<path d="M9 18h6"/><path d="M10 21h4"/>' +
                '<path d="M12 3a6 6 0 0 0-3.5 10.9c.6.4.9 1 .9 1.7v.4h5.2v-.4c0-.7.3-1.3.9-1.7A6 6 0 0 0 12 3z"/>');
        },
        // домашний опыт
        flask: function (s) {
            return wrap(s, '<path d="M9.5 3h5"/><path d="M10.5 3v6.2L5.6 17.4A2 2 0 0 0 7.3 20.5h9.4a2 2 0 0 0 1.7-3.1L13.5 9.2V3"/>' +
                '<path d="M8 15h8"/>');
        },
        // строгий вывод
        sigma: function (s) {
            return wrap(s, '<path d="M17 5H7l6 7-6 7h10"/>');
        },
        // закон / равновесие
        scale: function (s) {
            return wrap(s, '<path d="M12 4v16"/><path d="M7 20h10"/><path d="M4 8h16"/>' +
                '<path d="M4 8l-2 5a3 3 0 0 0 6 0z"/><path d="M20 8l-2 5a3 3 0 0 0 6 0z" transform="translate(-2)"/>');
        },
        // учёный / человек
        person: function (s) {
            return wrap(s, '<circle cx="12" cy="8" r="3.4"/><path d="M5 20a7 7 0 0 1 14 0"/>');
        },
        // тема / тег
        tag: function (s) {
            return wrap(s, '<path d="M3 11.5V4.5A1.5 1.5 0 0 1 4.5 3h7l9.5 9.5a1.5 1.5 0 0 1 0 2.1l-6.4 6.4a1.5 1.5 0 0 1-2.1 0z"/>' +
                '<circle cx="7.5" cy="7.5" r="1.4"/>');
        },
        // проверка знаний
        check: function (s) {
            return wrap(s, '<path d="M20 6L9 17l-5-5"/>');
        },
        // время / бюджет
        clock: function (s) {
            return wrap(s, '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.5l3.5 2"/>');
        },
        // шпаргалка / печать
        printer: function (s) {
            return wrap(s, '<path d="M7 9V3h10v6"/><path d="M7 19H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"/>' +
                '<path d="M7 15h10v6H7z"/>');
        },
        // единицы измерения
        ruler: function (s) {
            return wrap(s, '<path d="M3 14.5L14.5 3l6.5 6.5L9.5 21z"/><path d="M7.5 10l2 2"/><path d="M10.5 7l2 2"/><path d="M13.5 4.5l2 2"/>');
        },
        // пример / расчёт
        pencil: function (s) {
            return wrap(s, '<path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3z"/><path d="M14.5 6.5l3 3"/>');
        },
        // константа / число
        hash: function (s) {
            return wrap(s, '<path d="M9 3L7 21"/><path d="M17 3l-2 18"/><path d="M4 9h17"/><path d="M3 15h17"/>');
        },
        // книга / методичка
        book: function (s) {
            return wrap(s, '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h13"/>');
        },
        // где встречается в жизни
        home: function (s) {
            return wrap(s, '<path d="M4 11l8-7 8 7"/><path d="M6 10v10h12V10"/><path d="M10 20v-6h4v6"/>');
        },
        // факт / звезда
        star: function (s) {
            return wrap(s, '<path d="M12 3.5l2.6 5.6 6 .8-4.4 4.2 1.1 6.1L12 17.3 6.7 20.2l1.1-6.1L3.4 9.9l6-.8z"/>');
        },
        // предупреждение / частая ошибка
        warn: function (s) {
            return wrap(s, '<path d="M12 4L2.5 20h19z"/><path d="M12 10v4.5"/><path d="M12 17.5v.01"/>');
        },
        // тьютор / диалог
        chat: function (s) {
            return wrap(s, '<path d="M20 15a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/>' +
                '<path d="M8 9h8"/><path d="M8 12.5h5"/>');
        },
        // история / прошлое
        history: function (s) {
            return wrap(s, '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4.5V9h4.5"/><path d="M12 7.5V12l3 1.8"/>');
        },

        /* ── Интерфейсные знаки (2026-07-29) ───────────────────────────────
           Раньше эти места закрывались эмодзи и текстовыми глифами: ☀ ☾ 👍 👎
           📅 ⛶ ☰ 🔑 🔍. Эмодзи рисует система, поэтому на каждой ОС они разного
           веса и цвета — рядом со штриховым набором это читается как случайность.
           Теперь они здесь, в одном штрихе со всеми остальными. */

        // светлая тема
        sun: function (s) {
            return wrap(s, '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.6v2.2"/><path d="M12 19.2v2.2"/>' +
                '<path d="M4.4 4.4l1.6 1.6"/><path d="M18 18l1.6 1.6"/><path d="M2.6 12h2.2"/>' +
                '<path d="M19.2 12h2.2"/><path d="M4.4 19.6L6 18"/><path d="M18 6l1.6-1.6"/>');
        },
        // тёмная тема
        moon: function (s) {
            return wrap(s, '<path d="M20 14.2A8.4 8.4 0 0 1 9.8 4a8.4 8.4 0 1 0 10.2 10.2z"/>');
        },
        // нравится
        like: function (s) {
            return wrap(s, '<path d="M7 21V10.5l4.2-7a2 2 0 0 1 2.9 2.4L13 10h5.6a2.2 2.2 0 0 1 2.1 2.7l-1.6 6.6A2.2 2.2 0 0 1 17 21z"/>' +
                '<path d="M7 10.5H4.4A1.4 1.4 0 0 0 3 12v7.6A1.4 1.4 0 0 0 4.4 21H7"/>');
        },
        // не нравится
        dislike: function (s) {
            return wrap(s, '<path d="M17 3v10.5l-4.2 7a2 2 0 0 1-2.9-2.4L11 14H5.4a2.2 2.2 0 0 1-2.1-2.7l1.6-6.6A2.2 2.2 0 0 1 7 3z"/>' +
                '<path d="M17 13.5h2.6A1.4 1.4 0 0 0 21 12V4.4A1.4 1.4 0 0 0 19.6 3H17"/>');
        },
        // календарь / выбор даты
        calendar: function (s) {
            return wrap(s, '<rect x="3.2" y="5" width="17.6" height="16" rx="2.2"/><path d="M3.2 10h17.6"/>' +
                '<path d="M8 3v4"/><path d="M16 3v4"/><path d="M8 14h.01"/><path d="M12 14h.01"/>' +
                '<path d="M16 14h.01"/><path d="M8 17.6h.01"/><path d="M12 17.6h.01"/>');
        },
        // поиск
        search: function (s) {
            return wrap(s, '<circle cx="10.8" cy="10.8" r="6.8"/><path d="M15.8 15.8L21 21"/>');
        },
        // во весь экран
        expand: function (s) {
            return wrap(s, '<path d="M9 3.6H3.6V9"/><path d="M15 3.6h5.4V9"/><path d="M20.4 15v5.4H15"/><path d="M9 20.4H3.6V15"/>');
        },
        // меню / свернуть панель
        menu: function (s) {
            return wrap(s, '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>');
        },
        // ключ доступа
        key: function (s) {
            return wrap(s, '<circle cx="7.6" cy="12" r="4.4"/><path d="M12 12h9"/><path d="M17.6 12v3.4"/><path d="M20.4 12v2.4"/>');
        },
        // экспресс — быстро, коротко
        bolt: function (s) {
            return wrap(s, '<path d="M13.2 2.5L4.5 13.4h6.2l-.9 8.1 8.7-10.9h-6.2z"/>');
        },

        /* ── Группы разделов arXiv ────────────────────────────────────────────
           Владелец 2026-08-05: «разделы закодировать иконками, хотя бы на группу —
           чтобы в списке на главной сразу визуальное разделение, а то их много».

           Знак говорит о предмете, а не о слове: в ленте на пяти языках название
           раздела читается по-разному, а рисунок одинаков — в том числе в арабской
           версии, где на длину слова ориентироваться нельзя. */

        // астрономия — планета с кольцом
        secAstro: function (s) {
            return wrap(s, '<circle cx="12" cy="11.4" r="5.4"/>' +
                '<path d="M4.2 15.6c4.6 2.4 11 2.4 15.6 0"/><path d="M3.4 14.2c5.2 3.4 12 3.4 17.2 0"/>');
        },
        // физика — ядро и орбита
        secPhysics: function (s) {
            return wrap(s, '<circle cx="12" cy="12" r="2.2"/>' +
                '<ellipse cx="12" cy="12" rx="9.4" ry="4"/>' +
                '<ellipse cx="12" cy="12" rx="9.4" ry="4" transform="rotate(60 12 12)"/>');
        },
        // математика — циркуль
        secMath: function (s) {
            return wrap(s, '<circle cx="12" cy="4.4" r="1.7"/>' +
                '<path d="M11 6L5.4 20.2"/><path d="M13 6l5.6 14.2"/><path d="M8.4 14.4c2.4 1.4 4.8 1.4 7.2 0"/>');
        },
        // информатика — кристалл с выводами
        secCs: function (s) {
            return wrap(s, '<rect x="7.4" y="7.4" width="9.2" height="9.2" rx="1.4"/>' +
                '<path d="M10.4 3.6v3.8M13.6 3.6v3.8M10.4 16.6v3.8M13.6 16.6v3.8"/>' +
                '<path d="M3.6 10.4h3.8M3.6 13.6h3.8M16.6 10.4h3.8M16.6 13.6h3.8"/>');
        },
        // биология — двойная спираль
        secBio: function (s) {
            return wrap(s, '<path d="M8 3c0 6 8 12 8 18"/><path d="M16 3c0 6-8 12-8 18"/>' +
                '<path d="M9.2 7.4h5.6"/><path d="M9.2 16.6h5.6"/>');
        },
        // статистика — колокол распределения
        secStat: function (s) {
            return wrap(s, '<path d="M3 18c3.6 0 3.6-11 9-11s5.4 11 9 11"/><path d="M3 20.6h18"/>');
        },
        // экономика — монета
        secEcon: function (s) {
            return wrap(s, '<circle cx="12" cy="12" r="8.4"/>' +
                '<path d="M12 7.2v9.6"/><path d="M14.4 9.6c-.6-.9-1.5-1.3-2.6-1.3-1.5 0-2.6.8-2.6 2s1 1.7 2.6 2.1c1.7.4 2.7 1 2.7 2.2 0 1.3-1.2 2.1-2.7 2.1-1.2 0-2.1-.4-2.7-1.3"/>');
        },
        // инженерия — сигнал в системе
        secEng: function (s) {
            return wrap(s, '<path d="M2.6 12h3.2c1.6 0 1.6-5 3.2-5s1.6 10 3.2 10 1.6-5 3.2-5h5"/>' +
                '<circle cx="20.4" cy="12" r="1.4"/>');
        }
    };

    /* Раздел → группа → иконка. Единственный источник соответствия: карточка ленты и
       панель разделов берут знак отсюда, чтобы одна работа не оказалась в ленте под
       одним знаком, а в панели под другим. Ключ — то, что стоит до точки: arXiv так и
       устроен (astro-ph.GA, cond-mat.stat-mech), а неизвестный префикс знака не получает
       вовсе — лучше ничего, чем неверный намёк. */
    var SECTION_GROUP = {
        'astro-ph': 'secAstro',
        'cond-mat': 'secPhysics', 'gr-qc': 'secPhysics', 'hep-th': 'secPhysics',
        'hep-ph': 'secPhysics', 'hep-ex': 'secPhysics', 'hep-lat': 'secPhysics',
        'nucl-th': 'secPhysics', 'nucl-ex': 'secPhysics', 'quant-ph': 'secPhysics',
        'physics': 'secPhysics',
        // нелинейная динамика — хаос, солитоны, самоорганизация: по предмету это физика,
        // отдельной группы владелец не называл, а без знака раздел выпадал из ряда
        'nlin': 'secPhysics',
        'math': 'secMath', 'math-ph': 'secMath',
        'cs': 'secCs',
        'q-bio': 'secBio',
        'stat': 'secStat',
        'econ': 'secEcon', 'q-fin': 'secEcon',
        'eess': 'secEng'
    };

    I.sectionGroup = function (cat) {
        if (!cat) return '';
        return SECTION_GROUP[String(cat).split('.')[0]] || '';
    };

    /* Знак группы для раздела: строка со <svg> или пустая строка. */
    I.sectionIcon = function (cat, size) {
        var name = I.sectionGroup(cat);
        return name ? I[name](size) : '';
    };

    global.B42Icons = I;
})(window);

/* ── Мостик к js/typography.js ──────────────────────────────────────────────────
   Иконкам это чужое, и здесь оно временно. Причина: подключить новый скрипт как
   положено, тегом в шаблоне, значит пересобрать сорок тысяч страниц — а правка
   ради того и делается, чтобы пересборки НЕ было (владелец 29.08: «хочу избежать
   пересборок, перегенерации и перепубликации»). Этот файл уже подключён на всех
   типах страниц — статья, лента, автор, понятие, учёный, — поэтому мост стоит тут.
   Когда страницы будут собираться в следующий раз, тег встанет в шаблон, а эти
   строки уйдут. */
(function () {
    if (window.__b42Typo) return;
    window.__b42Typo = 1;
    add('/js/typography.js');
    /* Всплывающая карточка понятия — на ВСЕХ страницах, а не только у статьи и
       понятия. В ленте её не было, и понятие на карточке статьи не объяснялось
       ничем (владелец 30.08: «почему у них нет тултипа, а только у учёных»).
       Если тег уже стоит в разметке страницы — второй раз не подключаем: скрипт
       вешает слушатели на документ, и от двойного подключения карточка мигала бы. */
    if (!document.querySelector('script[src*="b42-card"]')) add('/js/b42-card.js');

    function add(src) {
        var s = document.createElement('script');
        s.src = src;
        s.defer = true;
        (document.head || document.documentElement).appendChild(s);
    }
})();
