/* Правило проверки числовых прикидок — одно на весь проект.
 *
 * Зачем отдельный файл. Раньше правило жило внутри js/tutor.js, и проверить его можно было
 * только глазами в браузере. При этом оно молча расходилось с данными: грейдер понимал
 * `tolerance` как ОТНОШЕНИЕ (ответ засчитан, если val/answer ≤ tolerance), а авторы половины
 * тем писали в это поле АБСОЛЮТНУЮ погрешность. Итог был хуже, чем просто «неудобно»:
 *   · девять вопросов не проходились никогда — даже точный авторский ответ считался неверным,
 *     потому что при tolerance < 1 условие отношения невыполнимо в принципе;
 *   · вопрос с отрицательным ответом (−10) не проходился из-за guard `val > 0`;
 *   · а там, где автор писал ±200 к ответу 5000, грейдер принимал всё от 25 до миллиона.
 *
 * Теперь семантика задаётся В ДАННЫХ явно, а файл подключается и страницей, и проверочным
 * скриптом (tools/quiz_check.js) — то есть проверка гоняет ровно тот код, который работает
 * у читателя, а не его копию.
 *
 *   tolAbs    — абсолютная погрешность: |ответ − эталон| ≤ tolAbs
 *   tolFactor — множитель: max(ответ/эталон, эталон/ответ) ≤ tolFactor
 *   tolerance — старое поле, понимается как множитель; если оно меньше единицы, то как
 *               множитель оно бессмысленно, и мы читаем его как абсолютную погрешность.
 *               Так старые данные перестают быть непроходимыми сами по себе.
 */
(function (global) {
    'use strict';

    // Надстрочные цифры — обычная запись степени в тексте уроков («10⁻³⁴ Дж·с»).
    var SUP = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        '⁻': '-', '⁺': '+'
    };

    /**
     * Один десятичный разделитель, остальные точки и запятые — разделители тысяч.
     * «1,234,567» это миллион с хвостиком, а не 1,234: читателю негде узнать, что поле
     * понимает только одну запись, поэтому понимать должны мы.
     */
    function fixSeparators(s) {
        var lastC = s.lastIndexOf(','), lastD = s.lastIndexOf('.');
        var nC = (s.match(/,/g) || []).length, nD = (s.match(/\./g) || []).length;
        var dec = null;
        if (lastC >= 0 && lastD >= 0) dec = lastC > lastD ? ',' : '.';   // десятичный — последний
        else if (nC === 1) dec = ',';
        else if (nD === 1) dec = '.';
        var decPos = dec ? s.lastIndexOf(dec) : -1;
        var out = '';
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i);
            if (c === ',' || c === '.') { if (i === decPos) out += '.'; }
            else out += c;
        }
        return out;
    }

    /* Разбор того, что ввёл читатель.
     *
     * Уроки пишут числа как учебник: «5·10³²», «10⁻³⁴», «−10», «3,2». Читатель повторяет эту
     * запись — и до 2026-08 получал за неё «неверно»: разбор понимал только `5e32` и `3,2`,
     * а «5·10^3» читал как 5, «10^5» как 10, «−10» с минусом U+2212 не читал вовсе. То есть
     * поле проверяло не понимание физики, а умение угадать его формат.
     *
     * Поэтому не расширяем список частных случаев, а приводим запись к одному виду: знаки
     * умножения → *, надстрочные цифры → ^n, любое тире → минус, пробелы и разделители тысяч →
     * ничего, запятая → точка. Мантисса у степени десятки необязательна: «10^5» это «1·10^5» —
     * ровно так степени и написаны в тексте.
     *
     * Что не разобралось — NaN, и страница обязана сказать об этом словами (js/tutor.js):
     * молчащая кнопка «Проверить» была отдельной бедой этой же истории.
     */
    function parseValue(raw) {
        if (typeof raw === 'number') return isFinite(raw) ? raw : NaN;
        var s = String(raw == null ? '' : raw);
        s = s.replace(/[\s'’«»]/g, '');            // пробелы-разделители тысяч, апострофы, кавычки
        s = s.replace(/[≈≃∼≅~]/g, '');                        // «примерно» — прикидка и так про порядок
        s = s.replace(/[−‐‑‒–—―]/g, '-');      // минус U+2212 и все тире
        s = s.replace(/[·⋅∙×✕✖•xX*]/g, '*');   // знаки умножения
        s = s.replace(/[⁰¹²³⁴-⁹⁺⁻]+/g, function (m) {
            var out = '';
            for (var i = 0; i < m.length; i++) out += SUP[m.charAt(i)] || '';
            return '^' + out;
        });
        s = fixSeparators(s);
        s = s.replace(/(\d)\*?10\^([+-]?\d+)/g, '$1e$2');            // «5·10^32»
        s = s.replace(/(^|[^\d.eE])10\^([+-]?\d+)/g, '$11e$2');      // «10^32» — мантисса единица
        s = s.replace(/^[^\d+\-.]+/, '');                            // «порядка 10^33», «~»: слова слева отбрасываем

        var m = s.match(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/);
        if (!m) return NaN;
        // Хвост вроде «Дж» или «состояний» — это единица, её и так печатает страница. А вот
        // ещё одна цифра в хвосте значит, что мы поняли ввод не так, как задумал читатель;
        // тихо взять первое число было бы враньём.
        if (/\d/.test(s.slice(m[0].length))) return NaN;
        var v = parseFloat(m[0]);
        return isFinite(v) ? v : NaN;
    }

    /** Какая семантика задана у вопроса. Возвращает {kind, value}. */
    function band(q) {
        if (typeof q.tolAbs === 'number') return { kind: 'abs', value: Math.abs(q.tolAbs) };
        if (typeof q.tolFactor === 'number') return { kind: 'factor', value: Math.abs(q.tolFactor) };
        if (typeof q.tolerance === 'number') {
            return q.tolerance < 1 ? { kind: 'abs', value: q.tolerance }
                                   : { kind: 'factor', value: q.tolerance };
        }
        return { kind: 'factor', value: 3 };      // прикидка по-фейнмановски: порядок величины
    }

    /**
     * Проверка ответа. Возвращает {ok, off, kind, band, reason}, где off — насколько
     * промахнулись (в тех же единицах для abs, в разах для factor). Знак учитывается: ответ
     * «−10» и «10» это разные ответы, а не одно и то же по модулю.
     *
     * reason говорит, ПОЧЕМУ промах, когда «во столько-то раз» сказать нельзя:
     *   'unparsed' — число не разобрано; 'sign' — знак другой; 'zero' — читатель ответил нулём;
     *   'far' — эталон ноль, а ответ нет. Без этого поля страница печатала «промахнулись в
     *   Infinity×»: у десяти вопросов из пятидесяти семи это видел живой читатель.
     */
    function estimate(rawValue, q) {
        var val = parseValue(rawValue);
        var ans = q.answer;
        var b = band(q);
        if (!isFinite(val) || typeof ans !== 'number') {
            return { ok: false, off: NaN, kind: b.kind, band: b.value, reason: 'unparsed' };
        }
        if (b.kind === 'abs') {
            var off = Math.abs(val - ans);
            return { ok: off <= b.value + 1e-12, off: off, kind: 'abs', band: b.value, reason: null };
        }
        // множитель: сравниваем модули, но требуем совпадения знака
        if (val === 0 || ans === 0) {
            if (val === ans) return { ok: true, off: 1, kind: 'factor', band: b.value, reason: null };
            return {
                ok: false, off: Infinity, kind: 'factor', band: b.value,
                reason: val === 0 ? 'zero' : 'far'
            };
        }
        if ((val < 0) !== (ans < 0)) {
            return { ok: false, off: Infinity, kind: 'factor', band: b.value, reason: 'sign' };
        }
        var r = Math.max(Math.abs(val / ans), Math.abs(ans / val));
        return { ok: r <= b.value + 1e-12, off: r, kind: 'factor', band: b.value, reason: null };
    }

    var API = { estimate: estimate, band: band, parseValue: parseValue };
    if (typeof module !== 'undefined' && module.exports) module.exports = API;
    global.B42Grade = API;
})(typeof window !== 'undefined' ? window : globalThis);
