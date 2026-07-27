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
        }
    };

    global.B42Icons = I;
})(window);
