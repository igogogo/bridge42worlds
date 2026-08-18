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

    /** Разбор того, что ввёл читатель: запятая, пробелы, «3,2×10^-5». */
    function parseValue(raw) {
        if (typeof raw === 'number') return raw;
        var s = String(raw == null ? '' : raw).trim().replace(/\s/g, '').replace(',', '.');
        s = s.replace(/(\d)[eE]?[x*×]10\^?([+-]?\d+)/, '$1e$2');
        var v = parseFloat(s);
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
     * Проверка ответа. Возвращает {ok, off, kind, band}, где off — насколько промахнулись
     * (в тех же единицах для abs, в разах для factor). Знак учитывается: ответ «−10» и «10»
     * это разные ответы, а не одно и то же по модулю.
     */
    function estimate(rawValue, q) {
        var val = parseValue(rawValue);
        var ans = q.answer;
        var b = band(q);
        if (!isFinite(val) || typeof ans !== 'number') {
            return { ok: false, off: NaN, kind: b.kind, band: b.value };
        }
        if (b.kind === 'abs') {
            var off = Math.abs(val - ans);
            return { ok: off <= b.value + 1e-12, off: off, kind: 'abs', band: b.value };
        }
        // множитель: сравниваем модули, но требуем совпадения знака
        if (val === 0 || ans === 0) {
            return { ok: val === ans, off: Infinity, kind: 'factor', band: b.value };
        }
        if ((val < 0) !== (ans < 0)) {
            return { ok: false, off: Infinity, kind: 'factor', band: b.value };
        }
        var r = Math.max(Math.abs(val / ans), Math.abs(ans / val));
        return { ok: r <= b.value + 1e-12, off: r, kind: 'factor', band: b.value };
    }

    var API = { estimate: estimate, band: band, parseValue: parseValue };
    if (typeof module !== 'undefined' && module.exports) module.exports = API;
    global.B42Grade = API;
})(typeof window !== 'undefined' ? window : globalThis);
