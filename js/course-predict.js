/* Предсказание на стенде: «сначала подумай, потом смотри».
 *
 * Зачем. Анимацию можно смотреть бесконечно и всё это время чувствовать, что понимаешь.
 * Проверяется это одним способом: заставить сказать заранее, куда пойдёт величина. Ошибся —
 * значит модель в голове неверная, и это видно сразу, а не на экзамене. Поэтому блок стоит
 * ПЕРЕД тем, как читатель начнёт крутить ползунки сам.
 *
 * Как устроено. Модуль ничего не знает про конкретную физику: он берёт параметры стенда и
 * производные величины (cfg.derive), сам находит пару «ползунок → величина», у которой связь
 * заметна, и спрашивает направление. Ответ не берётся из текста урока — его вычисляет сама
 * модель, а потом стенд ДВИГАЕТ настоящий ползунок, и читатель видит, как всё меняется.
 * Поэтому вопросы появляются на всех уроках сразу и не расходятся с физикой.
 *
 * B42Predict.mount(host, mdl, api, modelData, lang)
 */
(function (global) {
    'use strict';

    var L = {
        ru: {
            head: 'Сначала предскажите',
            q: 'Что произойдёт с величиной «{y}», если увеличить «{x}»?',
            up: 'вырастет', down: 'уменьшится', same: 'почти не изменится',
            checking: 'Смотрим…',
            right: 'Верно.', wrong: 'Не угадали.',
            became: 'стало', was: 'было',
            grew: 'выросла', fell: 'упала', held: 'осталась почти прежней',
            verdict: 'Величина «{y}» {dir}: {a} → {b}.',
            again: 'Ещё вопрос',
            streak: 'подряд верно',
            note: 'Ответьте до того, как крутить ползунки сами: смысл в том, чтобы проверить свою догадку, а не подсмотреть.'
        },
        en: {
            head: 'Predict first',
            q: 'What happens to “{y}” if you increase “{x}”?',
            up: 'it grows', down: 'it drops', same: 'barely changes',
            checking: 'Let us look…',
            right: 'Correct.', wrong: 'Not this time.',
            became: 'now', was: 'was',
            grew: 'grew', fell: 'dropped', held: 'stayed nearly the same',
            verdict: '“{y}” {dir}: {a} → {b}.',
            again: 'Another one',
            streak: 'in a row',
            note: 'Answer before you touch the sliders: the point is to test your guess, not to peek.'
        },
        es: {
            head: 'Predice primero',
            q: '¿Qué le pasa a «{y}» si aumentas «{x}»?',
            up: 'crece', down: 'baja', same: 'apenas cambia',
            checking: 'Veamos…',
            right: 'Correcto.', wrong: 'Esta vez no.',
            became: 'ahora', was: 'era',
            grew: 'creció', fell: 'bajó', held: 'se mantuvo casi igual',
            verdict: '«{y}» {dir}: {a} → {b}.',
            again: 'Otra pregunta',
            streak: 'seguidas',
            note: 'Responde antes de mover los controles: se trata de comprobar tu intuición, no de mirar.'
        },
        ar: {
            head: 'توقّع أولاً',
            q: 'ماذا يحدث لـ«{y}» إذا زدت «{x}»؟',
            up: 'يزداد', down: 'ينقص', same: 'لا يكاد يتغير',
            checking: 'لنرَ…',
            right: 'صحيح.', wrong: 'ليس هذه المرة.',
            became: 'الآن', was: 'كان',
            grew: 'ازداد', fell: 'نقص', held: 'بقي كما هو تقريباً',
            verdict: '«{y}» {dir}: {a} ← {b}.',
            again: 'سؤال آخر',
            streak: 'متتالية',
            note: 'أجب قبل تحريك المؤشرات: الهدف اختبار حدسك لا النظر إلى النتيجة.'
        },
        fr: {
            head: 'Prédisez d’abord',
            q: 'Qu’arrive-t-il à « {y} » si vous augmentez « {x} » ?',
            up: 'augmente', down: 'diminue', same: 'ne change presque pas',
            checking: 'Voyons…',
            right: 'Exact.', wrong: 'Raté.',
            became: 'devient', was: 'était',
            grew: 'a augmenté', fell: 'a diminué', held: 'est restée presque la même',
            verdict: '« {y} » {dir} : {a} → {b}.',
            again: 'Une autre question',
            streak: 'de suite',
            note: 'Répondez avant de bouger les curseurs : le but est de vérifier votre intuition, pas de regarder la réponse.'
        }
    };

    var STYLE_ID = 'b42-predict-style';
    var CSS = [
        '.b42p{max-width:620px;margin:14px 0 0;padding:13px 16px;border-radius:12px;',
        'background:var(--tag-bg);border:1px solid var(--border)}',
        '.b42p-h{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--soft);',
        'font-weight:700;margin-bottom:7px;display:flex;align-items:center;gap:7px}',
        '.b42p-h .b42p-streak{margin-inline-start:auto;text-transform:none;letter-spacing:0;font-weight:600;color:var(--link)}',
        '.b42p-q{font-size:14.5px;line-height:1.6;color:var(--text);margin-bottom:10px}',
        '.b42p-opts{display:flex;flex-wrap:wrap;gap:7px}',
        '.b42p-opts button{font-size:13px;padding:6px 14px;border-radius:16px;cursor:pointer;',
        'background:var(--bg);border:1px solid var(--border);color:var(--muted);font-family:inherit}',
        '.b42p-opts button:hover{border-color:var(--link);color:var(--link)}',
        '.b42p-opts button[disabled]{cursor:default;opacity:.55}',
        '.b42p-opts button.picked{border-color:var(--link);color:var(--link);font-weight:600}',
        '.b42p-fb{margin-top:10px;font-size:13.5px;line-height:1.65}',
        '.b42p-fb.ok{color:#2e7d32}.b42p-fb.no{color:#b31b1b}',
        '.b42p-fb b{font-variant-numeric:tabular-nums}',
        '.b42p-note{margin-top:8px;font-size:12px;color:var(--soft);line-height:1.55}',
        '.b42p-again{margin-top:9px;font-size:12.5px;padding:5px 13px;border-radius:15px;cursor:pointer;',
        'background:none;border:1px solid var(--border);color:var(--soft);font-family:inherit}',
        '.b42p-again:hover{border-color:var(--link);color:var(--link)}'
    ].join('');

    function injectStyle() {
        if (document.getElementById(STYLE_ID)) return;
        var s = document.createElement('style');
        s.id = STYLE_ID; s.textContent = CSS;
        document.head.appendChild(s);
    }
    function el(tag, cls, txt) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (txt != null) e.textContent = txt;
        return e;
    }
    function label(md, lang, key) {
        var d = md && md.i18n && (md.i18n[lang] || md.i18n.ru);
        return (d && d[key]) || key;
    }
    function fmt(v) {
        var a = Math.abs(v);
        return a >= 100 ? String(Math.round(v))
             : a >= 1 ? String(Math.round(v * 10) / 10)
             : String(Math.round(v * 1000) / 1000);
    }
    function derive(mdl, state) {
        try {
            var d = mdl && mdl.cfg && mdl.cfg.derive ? mdl.cfg.derive(state, {}) : null;
            return (d && typeof d === 'object') ? d : {};
        } catch (e) { return {}; }
    }

    /* О какой величине спрашивать. Единственное место, где у величины ТОЧНО есть человеческое
       имя, — подпись оси графика параграфа. Словарь модели для этого не годится: в нём лежат
       подписи ползунков, и по совпадению ключей выходили вопросы вида «что будет с n, если
       увеличить n». Значение берём из самой кривой графика: она и есть та величина, про
       которую параграф. */
    function plotted(mdl, md, lang) {
        var pl = mdl && mdl.cfg && mdl.cfg.plot;
        if (!pl || !pl.curve || !pl.y || !pl.y.label) return null;
        var name = label(md, lang, pl.y.label);
        if (!name || name === pl.y.label) return null;      // подписи нет — молчим
        return { pl: pl, name: name };
    }

    /** Значение величины с графика в точке x при данном состоянии ползунков. */
    function valueAt(mdl, pl, state, x) {
        try {
            var v = pl.curve(x, state, derive(mdl, state));
            return (typeof v === 'number' && isFinite(v)) ? v : null;
        } catch (e) { return null; }
    }

    /** Точки по оси x, в которых сравниваем кривую до и после сдвига ползунка. */
    function probes(pl, state) {
        var rv = function (v) { return typeof v === 'function' ? v(state) : v; };
        var lo = rv(pl.x.min), hi = rv(pl.x.max), out = [];
        for (var i = 1; i <= 9; i++) out.push(lo + (hi - lo) * i / 10);
        return out;
    }

    /* Насколько связь устойчива. Смотрим не одну точку кривой, а девять: если ползунок
       двигает величину в одну и ту же сторону почти везде — связь настоящая, и вопрос честный.
       Если направление скачет (а так бывает у всего колеблющегося: смещение маятника, волна),
       то «правильный ответ» был бы артефактом того, в какой точке мы посмотрели. Такое не
       спрашиваем вовсе. */
    function response(mdl, pl, before, after) {
        var xs = probes(pl, before), up = 0, down = 0, rels = [];
        for (var i = 0; i < xs.length; i++) {
            var a = valueAt(mdl, pl, before, xs[i]), b = valueAt(mdl, pl, after, xs[i]);
            if (a === null || b === null) continue;
            var rel = (b - a) / (Math.abs(a) || 1);
            if (Math.abs(rel) < 0.02) continue;              // шум, не голосует
            rels.push(Math.abs(rel));
            if (rel > 0) up++; else down++;
        }
        var votes = up + down;
        if (votes < 5) return null;                          // слишком мало данных
        var agree = Math.max(up, down) / votes;
        if (agree < 0.85) return null;                       // направление скачет — не спрашиваем
        rels.sort(function (p, q) { return p - q; });
        return { dir: up >= down ? 1 : -1, strength: rels[Math.floor(rels.length / 2)] };
    }

    /* Ползунок с заметным влиянием на эту величину. Берём тот, где отклик сильнее:
       на нём вопрос честный (есть один верный ответ), а не «изменится в пятом знаке». */
    function pickPair(mdl, params, state, md, lang) {
        var P = plotted(mdl, md, lang);
        if (!P) return null;
        var best = null;
        params.forEach(function (p) {
            var up = {}, cur = state[p.key];
            Object.keys(state).forEach(function (k) { up[k] = state[k]; });
            // сдвигаем ощутимо, но остаёмся в пределах ползунка
            var target = cur + (p.max - cur) * 0.6;
            if (Math.abs(target - cur) < (p.step || 1)) target = cur - (cur - p.min) * 0.6;
            if (Math.abs(target - cur) < 1e-9) return;
            up[p.key] = target;
            var r = response(mdl, P.pl, state, up);
            if (!r || r.strength < 0.05) return;
            if (!best || r.strength > best.rel) {
                // для разбора показываем значение в середине диапазона
                var xs = probes(P.pl, state), xm = xs[Math.floor(xs.length / 2)];
                best = { p: p, name: P.name, from: cur, to: target, dir: r.dir, rel: r.strength,
                         a: valueAt(mdl, P.pl, state, xm), b: valueAt(mdl, P.pl, up, xm) };
            }
        });
        return best;
    }

    /** Двигает НАСТОЯЩИЙ ползунок стенда — читатель видит, как меняется картинка. */
    function sweep(host, params, pKey, from, to, done) {
        var idx = -1;
        params.forEach(function (p, i) { if (p.key === pKey) idx = i; });
        var inputs = host.querySelectorAll('.xpl-ctrl input[type=range]');
        var input = idx >= 0 ? inputs[idx] : null;
        if (!input) { done(); return; }
        var steps = 24, i = 0;
        var timer = setInterval(function () {
            i++;
            var v = from + (to - from) * (i / steps);
            input.value = v;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            if (i >= steps) { clearInterval(timer); done(); }
        }, 34);
    }

    function mount(host, mdl, api, md, lang) {
        injectStyle();
        var t = L[lang] || L.ru;
        var params = (mdl && mdl.cfg && mdl.cfg.params) || [];
        if (params.length < 1) return null;

        var box = el('div', 'b42p');
        var head = el('div', 'b42p-h');
        head.appendChild(el('span', null, t.head));
        var streakEl = el('span', 'b42p-streak');
        head.appendChild(streakEl);
        var qEl = el('div', 'b42p-q');
        var opts = el('div', 'b42p-opts');
        var fb = el('div', 'b42p-fb'); fb.style.display = 'none';
        var note = el('div', 'b42p-note', t.note);
        box.appendChild(head); box.appendChild(qEl); box.appendChild(opts);
        box.appendChild(fb); box.appendChild(note);

        var KEY = 'b42_predict_streak';
        var streak = 0;
        try { streak = parseInt(localStorage.getItem(KEY), 10) || 0; } catch (e) {}
        function showStreak() {
            streakEl.textContent = streak > 1 ? (streak + ' ' + t.streak) : '';
        }

        var pair = null;

        function ask() {
            fb.style.display = 'none';
            note.style.display = '';
            opts.innerHTML = '';
            var state = {};
            params.forEach(function (p) { state[p.key] = api.state[p.key]; });
            pair = pickPair(mdl, params, state, md, lang);
            if (!pair) { box.style.display = 'none'; return; }
            box.style.display = '';

            var yName = pair.name;
            var xName = label(md, lang, pair.p.label || pair.p.key);
            qEl.textContent = t.q.replace('{y}', yName).replace('{x}', xName);

            [['up', t.up], ['down', t.down], ['same', t.same]].forEach(function (o) {
                var b = el('button', null, o[1]);
                b.type = 'button';
                b.addEventListener('click', function () { answer(o[0], b, yName); });
                opts.appendChild(b);
            });
        }

        function answer(pick, btn, yName) {
            var all = opts.querySelectorAll('button');
            all.forEach(function (b) { b.disabled = true; });
            btn.classList.add('picked');
            note.style.display = 'none';
            fb.className = 'b42p-fb';
            fb.textContent = t.checking;
            fb.style.display = '';

            // истину считает сама модель (по устойчивому направлению, а не по одной точке)
            var truth = pair.dir > 0 ? 'up' : 'down';
            var ok = (pick === truth);

            sweep(host, params, pair.p.key, pair.from, pair.to, function () {
                var dir = truth === 'up' ? t.grew : (truth === 'down' ? t.fell : t.held);
                fb.className = 'b42p-fb ' + (ok ? 'ok' : 'no');
                fb.innerHTML = '<b>' + (ok ? t.right : t.wrong) + '</b> ' +
                    t.verdict.replace('{y}', yName).replace('{dir}', dir)
                             .replace('{a}', '<b>' + fmt(pair.a) + '</b>')
                             .replace('{b}', '<b>' + fmt(pair.b) + '</b>');
                streak = ok ? streak + 1 : 0;
                try { localStorage.setItem(KEY, String(streak)); } catch (e) {}
                showStreak();
                var again = el('button', 'b42p-again', '↻ ' + t.again);
                again.type = 'button';
                again.addEventListener('click', ask);
                fb.appendChild(document.createElement('br'));
                fb.appendChild(again);
            });
        }

        showStreak();
        ask();
        if (box.style.display === 'none') return null;
        host.appendChild(box);
        return { ask: ask };
    }

    global.B42Predict = { mount: mount };
})(window);
