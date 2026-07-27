/* Мини-игра параграфа: «попади в цель» на живом стенде.
 *
 * Викторина проверяет, запомнил ли читатель текст. Здесь другое: цель задаётся в величинах самой
 * модели («сделай давление 200 кПа»), а крутить можно только те же ползунки, что и в уроке.
 * Наугад не выиграть — нужно понять, какая величина куда тянет.
 *
 * Игра ничего не знает про конкретную модель: она берёт производные величины у стенда
 * (cfg.derive), сама выясняет достижимый диапазон, перебирая углы пространства параметров,
 * и ставит цель внутри него. Поэтому испытание работает со всеми моделями курса и не ломается,
 * когда добавляется новая.
 */
(function (global) {
    'use strict';

    var L = {
        ru: {
            head: 'Испытание', start: 'Дать задание', again: 'Другое задание',
            goal: 'Цель', now: 'Сейчас', win: 'Есть попадание!',
            close: 'Совсем близко — чуть-чуть в ту же сторону.',
            far: 'Пока далеко. Подумайте, какая величина тянет в нужную сторону.',
            moves: 'ходов', hint: 'Крутите ползунки стенда. Засчитывается при отклонении меньше',
            best: 'Лучший результат', solved: 'решено'
        },
        en: {
            head: 'Challenge', start: 'Give me a task', again: 'Another task',
            goal: 'Target', now: 'Now', win: 'Hit!',
            close: 'Very close — nudge it the same way.',
            far: 'Still far off. Think which quantity pulls the right way.',
            moves: 'moves', hint: 'Move the sliders on the stand. Counts when the gap is under',
            best: 'Best', solved: 'solved'
        },
        es: {
            head: 'Desafío', start: 'Dame una tarea', again: 'Otra tarea',
            goal: 'Objetivo', now: 'Ahora', win: '¡Acertaste!',
            close: 'Muy cerca: sigue en la misma dirección.',
            far: 'Todavía lejos. Piensa qué magnitud empuja en el sentido correcto.',
            moves: 'movimientos', hint: 'Mueve los controles. Cuenta con una desviación menor a',
            best: 'Mejor', solved: 'resueltos'
        },
        ar: {
            head: 'تحدٍّ', start: 'أعطني مهمة', again: 'مهمة أخرى',
            goal: 'الهدف', now: 'الآن', win: 'إصابة!',
            close: 'قريب جداً — تابع في الاتجاه نفسه.',
            far: 'ما زال بعيداً. فكّر أي مقدار يدفع في الاتجاه الصحيح.',
            moves: 'حركات', hint: 'حرّك المؤشرات. يُحتسب عندما يقل الفارق عن',
            best: 'الأفضل', solved: 'مُنجزة'
        }
    };

    var TOL = 0.06;   // попадание засчитывается при отклонении менее 6 процентов

    function derive(mdl, state) {
        try {
            var d = mdl && mdl.cfg && mdl.cfg.derive ? mdl.cfg.derive(state) : null;
            return (d && typeof d === 'object') ? d : {};
        } catch (e) { return {}; }
    }

    /** Достижимый диапазон величины: обходим углы пространства параметров. */
    function reach(mdl, params, key) {
        var lo = Infinity, hi = -Infinity;
        var corners = 1 << Math.min(params.length, 5);
        for (var c = 0; c < corners; c++) {
            var s = {};
            params.forEach(function (p, i) {
                s[p.key] = (c >> i) & 1 ? p.max : p.min;
            });
            var v = derive(mdl, s)[key];
            if (typeof v === 'number' && isFinite(v)) {
                if (v < lo) lo = v;
                if (v > hi) hi = v;
            }
        }
        return (lo < hi) ? { lo: lo, hi: hi } : null;
    }

    /** Величина для цели: та, что сильнее всех откликается на ползунки. */
    function pickKey(mdl, params) {
        var base = derive(mdl, stateOf(params));
        var best = null, bestSpan = 0;
        Object.keys(base).forEach(function (k) {
            if (typeof base[k] !== 'number' || !isFinite(base[k])) return;
            var r = reach(mdl, params, k);
            if (!r) return;
            var span = Math.abs(r.hi - r.lo) / (Math.abs(base[k]) || 1);
            if (span > bestSpan) { bestSpan = span; best = { key: k, range: r }; }
        });
        return bestSpan > 0.25 ? best : null;   // слишком вялую величину в цель не берём
    }

    function stateOf(params) {
        var s = {};
        params.forEach(function (p) { s[p.key] = p.value; });
        return s;
    }

    function label(md, lang, key) {
        var d = md && md.i18n && (md.i18n[lang] || md.i18n.ru);
        return (d && d[key]) || key;
    }

    /* Величина, которую стенд рисует на графике: у неё в модели уже есть и подпись, и единица,
       и именно про неё параграф. Берём её в цель, если она правда откликается на ползунки. */
    function plotted(mdl, md, lang) {
        var y = mdl && mdl.cfg && mdl.cfg.plot && mdl.cfg.plot.y;
        if (!y || !y.kind) return null;
        return {
            key: y.kind,
            name: label(md, lang, y.label) || y.kind,
            unit: y.unit ? label(md, lang, y.unit) : ''
        };
    }

    function fmt(v) {
        var a = Math.abs(v);
        return a >= 100 ? Math.round(v) : (a >= 1 ? Math.round(v * 10) / 10 : Math.round(v * 1000) / 1000);
    }

    /**
     * Вешает испытание под стендом.
     * @param {HTMLElement} host куда вставить блок
     * @param {object} mdl   модель (из B42Models)
     * @param {object} api   то, что вернул Explorable
     * @param {object} md    JSON модели (для подписей)
     * @param {string} lang  язык интерфейса
     */
    function mount(host, mdl, api, md, lang) {
        var t = L[lang] || L.ru;
        var params = (mdl && mdl.cfg && mdl.cfg.params) || (md && md.params) || [];
        if (!params.length) return null;

        // сначала пробуем ту величину, что нарисована на графике параграфа
        var pl = plotted(mdl, md, lang);
        var found = null;
        if (pl) {
            var r = reach(mdl, params, pl.key);
            if (r && Math.abs(r.hi - r.lo) > 0) found = { key: pl.key, range: r };
        }
        if (!found) { found = pickKey(mdl, params); pl = null; }
        if (!found) return null;   // у модели нет величины, которой можно осмысленно управлять

        var key = found.key, lo = found.range.lo, hi = found.range.hi;
        var unit = pl ? pl.unit : '';
        var name = pl ? pl.name : label(md, lang, key);
        var round = 0, moves = 0, best = null, solved = 0, target = null, done = true, prev = null;

        var box = document.createElement('div');
        box.className = 'k-chal';
        box.innerHTML =
            '<div class="k-chal-h"><span class="k-chal-i"></span>' + t.head + '</div>' +
            '<div class="k-chal-task"></div>' +
            '<div class="k-chal-bar"><div class="k-chal-fill"></div></div>' +
            '<div class="k-chal-now"></div>' +
            '<div class="k-chal-msg">' + t.hint + ' ' + Math.round(TOL * 100) + '%.</div>' +
            '<button type="button" class="k-chal-btn">' + t.start + '</button>';
        host.appendChild(box);
        if (global.B42Icons && B42Icons.star) box.querySelector('.k-chal-i').innerHTML = B42Icons.star(15);

        var task = box.querySelector('.k-chal-task');
        var fill = box.querySelector('.k-chal-fill');
        var now = box.querySelector('.k-chal-now');
        var msg = box.querySelector('.k-chal-msg');
        var btn = box.querySelector('.k-chal-btn');

        function newRound() {
            round++; moves = 0; done = false; prev = null;
            // цель зависит от номера круга, а не от случайности: задания повторяемы
            var k = ((round * 37) % 11) / 10;
            var f = 0.15 + 0.7 * k;
            target = (lo > 0 && hi / lo > 20)
                ? lo * Math.pow(hi / lo, f)
                : lo + (hi - lo) * f;
            task.innerHTML = '<b>' + t.goal + ':</b> ' + name + ' = ' +
                '<span class="k-chal-goal">' + fmt(target) + (unit ? ' ' + unit : '') + '</span>';
            msg.textContent = t.hint + ' ' + Math.round(TOL * 100) + '%.';
            msg.className = 'k-chal-msg';
            btn.textContent = t.again;
            tick();
        }

        function tick() {
            if (target === null || !api || !api.state) return;
            var v = derive(mdl, api.state)[key];
            if (typeof v !== 'number' || !isFinite(v)) return;
            var rel = Math.abs(v - target) / (Math.abs(target) || 1);
            now.textContent = t.now + ': ' + fmt(v) + (unit ? ' ' + unit : '');
            fill.style.width = Math.max(2, Math.min(100, (1 - Math.min(rel, 1)) * 100)) + '%';
            fill.className = 'k-chal-fill' + (rel <= TOL ? ' hit' : (rel <= TOL * 3 ? ' near' : ''));
            if (done) return;
            if (prev !== null && Math.abs(v - prev) > 1e-9) moves++;
            prev = v;
            if (rel <= TOL) {
                done = true; solved++;
                if (best === null || moves < best) best = moves;
                msg.textContent = t.win + ' ' + t.best + ': ' + best + ' ' + t.moves +
                    ' · ' + solved + ' ' + t.solved + '.';
                msg.className = 'k-chal-msg win';
            } else if (rel <= TOL * 3) {
                msg.textContent = t.close; msg.className = 'k-chal-msg near';
            } else {
                msg.textContent = t.far; msg.className = 'k-chal-msg';
            }
        }

        btn.addEventListener('click', newRound);
        setInterval(tick, 250);
        return { newRound: newRound, key: key };
    }

    global.B42Challenge = { mount: mount };
})(window);
