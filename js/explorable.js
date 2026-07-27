/* explorable.js — крошечный движок интерактивных «экспериментальных столов» для theory-статей.
   Ноль внешних зависимостей. Тема из CSS-переменных сайта, RTL-aware, подписи из словаря по языку
   (i18n), поэтому одна и та же модель работает на ru/en/es/ar без переписывания разметки —
   заодно закрывает баг «подписи в SVG не переводятся».

   Автор статьи описывает только СУТЬ модели (параметры, физику, отрисовку, формулу, график),
   всё остальное — панель, слайдеры, цикл анимации, пауза вне экрана, ретина, тема, локаль —
   даёт движок. См. пример конфигурации в lab-doppler.html.

   API:  const api = Explorable(rootEl, cfg);  api.setLang('en');  api.destroy();

   cfg = {
     lang,                                  // стартовый язык (иначе <html lang>)
     i18n: { key: {ru,en,es,ar} },          // словарь подписей
     params: [ {key,label,min,max,step,value,unit,fmt} ],   // label/unit — ключи i18n или строка
     animate(t, state) -> anim,             // анимируемые величины (позиция и т.п.); t — секунды
     derive(state, anim) -> derived,        // производные числа (подставляются в формулу/график)
     stage: { height, draw(g, ctx) },       // ctx={W,H,state,anim,derived,time,c(name),rtl,T}
     formula(state, derived, T) -> html,    // формула с подставленными числами → HTML
     plot: { height, x:{label,min,max}, y:{label,min,max,unit}, samples,
             curve(x,state,derived)->y, marker(state,anim,derived)->{x,y} }
   }
*/
(function (global) {
    'use strict';

    var STYLE_ID = 'xpl-style';
    var CSS = [
        /* Единое поле прибора: сцена, ползунки, формула и график живут в ОДНОЙ рамке и
           разделены тонкими линиями — визуально это один инструмент, а не три блока подряд. */
        '.xpl{max-width:680px;margin:22px 0 30px;font-size:14px;border:1px solid var(--border,#e2e2e2);',
        'border-radius:14px;overflow:hidden;background:var(--bg,#fff)}',
        '.xpl-stage-wrap,.xpl-plot-wrap{position:relative;overflow:hidden;background:var(--tag-bg,#f3f3f3)}',
        '.xpl-plot-wrap{border-top:1px solid var(--border,#e2e2e2)}',
        '.xpl-stage,.xpl-plot{display:block;width:100%}',
        '.xpl-panel{padding:14px 16px;border-top:1px solid var(--border,#e2e2e2);background:var(--bg,#fff)}',
        '.xpl-controls{display:flex;flex-wrap:wrap;gap:12px 22px}',
        '.xpl-ctrl{flex:1 1 200px;min-width:170px}',
        '.xpl-ctrl-top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px}',
        '.xpl-ctrl-label{font-size:12.5px;color:var(--muted,#6b6b6b)}',
        '.xpl-ctrl-val{font-size:13px;font-weight:600;color:var(--text,#2c2c2c);font-variant-numeric:tabular-nums}',
        '.xpl-ctrl input[type=range]{width:100%;accent-color:var(--link,#4a7c9b);cursor:pointer}',
        '.xpl-formula{margin-top:14px;padding-top:12px;border-top:1px dashed var(--border,#e2e2e2);',
        'font-size:15px;line-height:1.7;overflow-x:auto;text-align:center}',
        '.xpl-formula .xf-var{color:var(--link,#4a7c9b);font-weight:600;font-variant-numeric:tabular-nums}',
        '.xpl-formula .xf-res{color:var(--text,#2c2c2c);font-weight:700;font-variant-numeric:tabular-nums}',
        '.xpl-formula .xf-op{color:var(--soft,#8a8a8a)}',
        '.xpl-formula i{color:var(--muted,#6b6b6b);font-style:italic}',
        '.xpl-reset{margin-top:10px;font-size:12px;color:var(--soft,#8a8a8a);background:none;',
        'border:1px solid var(--border,#e2e2e2);border-radius:14px;padding:3px 12px;cursor:pointer}',
        '.xpl-reset:hover{border-color:var(--link,#4a7c9b);color:var(--link,#4a7c9b)}',
        /* Замок у связанной величины: закрытый — держим значение, открытый — величина
           свободна и поедет сама, когда сдвинут соседний ползунок. */
        '.xpl-lock{margin-left:8px;font-size:12px;line-height:1;background:none;border:none;cursor:pointer;',
        'color:var(--soft,#8a8a8a);padding:0 2px}',
        '.xpl-lock.on{color:var(--brass,#b8860b)}',
        '.xpl-lock:hover{color:var(--link,#4a7c9b)}',
        '.xpl-ctrl input[type=range].xpl-range-free{accent-color:var(--brass,#b8860b);opacity:.92}',
        /* Приборная строка поверх сцены — крупные значения, как на панели установки */
        '.xpl-readout{display:flex;flex-wrap:wrap;gap:0;background:var(--bg,#fff);',
        'border-top:1px solid var(--border,#e2e2e2)}',
        '.xpl-ro{flex:1 1 90px;min-width:80px;padding:5px 8px 6px;text-align:center;',
        'border-right:1px solid var(--border,#e2e2e2)}',
        '.xpl-ro:last-child{border-right:none}',
        '.xpl-ro-val{font-size:14px;font-weight:700;color:var(--text,#2c2c2c);',
        'font-variant-numeric:tabular-nums;line-height:1.2}',
        '.xpl-ro-lab{font-size:9.5px;color:var(--soft,#8a8a8a);text-transform:uppercase;',
        'letter-spacing:.06em;margin-top:2px;line-height:1.25}'
    ].join('');

    function injectStyle() {
        if (document.getElementById(STYLE_ID)) return;
        var s = document.createElement('style');
        s.id = STYLE_ID; s.textContent = CSS;
        document.head.appendChild(s);
    }

    function el(tag, cls, html) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html != null) e.innerHTML = html;
        return e;
    }

    // Пиксель-плотный холст: логический размер в CSS px, буфер — ×dpr.
    function fitCanvas(canvas, cssH) {
        var dpr = Math.min(global.devicePixelRatio || 1, 2);
        var cssW = canvas.parentNode.clientWidth || 600;
        canvas.style.height = cssH + 'px';
        canvas.width = Math.round(cssW * dpr);
        canvas.height = Math.round(cssH * dpr);
        var g = canvas.getContext('2d');
        g.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { g: g, W: cssW, H: cssH };
    }

    function Explorable(root, cfg) {
        injectStyle();
        var lang = cfg.lang || (document.documentElement.getAttribute('lang')) || 'en';
        var rtl = getComputedStyle(document.documentElement).direction === 'rtl';

        // Подписи: поддерживаем ОБА формата словаря —
        //   «язык→ключ»  cfg.i18n = {ru:{k:..}, en:{k:..}}  (стиль контент-JSON, удобно переводить пачкой),
        //   «ключ→язык»  cfg.i18n = {k:{ru,en}}             (удобно писать инлайн в странице),
        // плюс инлайн-объект {ru,en} прямо в label/unit. Первым пробуем язык-первый.
        function T(key) {
            if (key == null) return '';
            if (typeof key === 'object') return key[lang] || key.en || key.ru || '';
            var langDict = cfg.i18n && cfg.i18n[lang];
            if (langDict && langDict[key] != null) return langDict[key];
            var keyDict = cfg.i18n && cfg.i18n[key];
            if (keyDict) return keyDict[lang] || keyDict.en || keyDict.ru || key;
            return key;
        }
        function cvar(name, fallback) {
            var v = getComputedStyle(root).getPropertyValue(name);
            return (v && v.trim()) || fallback;
        }
        function colors() {
            return {
                text: cvar('--text', '#2c2c2c'), muted: cvar('--muted', '#6b6b6b'),
                soft: cvar('--soft', '#8a8a8a'), link: cvar('--link', '#4a7c9b'),
                border: cvar('--border', '#e2e2e2'), bg: cvar('--bg', '#fff'),
                accent: cvar('--brass', '#b8860b'), warn: cvar('--red', '#b31b1b')
            };
        }

        var state = {};
        cfg.params.forEach(function (p) { state[p.key] = p.value; });

        // ── разметка ──
        root.classList.add('xpl');
        root.innerHTML = '';
        var stageWrap = el('div', 'xpl-stage-wrap');
        var stageCanvas = el('canvas', 'xpl-stage');
        stageWrap.appendChild(stageCanvas);
        var panel = el('div', 'xpl-panel');
        var controls = el('div', 'xpl-controls');
        var formula = el('div', 'xpl-formula');
        panel.appendChild(controls); panel.appendChild(formula);
        var plotWrap, plotCanvas;
        if (cfg.plot) { plotWrap = el('div', 'xpl-plot-wrap'); plotCanvas = el('canvas', 'xpl-plot'); plotWrap.appendChild(plotCanvas); }

        root.appendChild(stageWrap);
        root.appendChild(panel);
        if (plotWrap) root.appendChild(plotWrap);

        // ── контролы ──
        // У связанных величин (cfg.link) каждый ползунок получает замок. Замкнутые держатся,
        // незамкнутые пересчитываются моделью и ФИЗИЧЕСКИ едут следом — видно, что величины
        // не независимы, а связаны уравнением.
        var ctrlRefs = [], linked = cfg.link || null;
        var locks = {};
        if (linked) linked.keys.forEach(function (k, i) { locks[k] = !!(linked.lockedByDefault || [])[i]; });

        cfg.params.forEach(function (p) {
            var wrap = el('div', 'xpl-ctrl');
            var top = el('div', 'xpl-ctrl-top');
            var lab = el('span', 'xpl-ctrl-label');
            var val = el('span', 'xpl-ctrl-val');
            top.appendChild(lab); top.appendChild(val);

            var lockBtn = null;
            if (linked && linked.keys.indexOf(p.key) >= 0) {
                lockBtn = el('button', 'xpl-lock');
                lockBtn.type = 'button';
                lockBtn.addEventListener('click', function () {
                    // хотя бы одна величина обязана оставаться свободной, иначе решать нечего
                    var free = linked.keys.filter(function (k) { return !locks[k]; });
                    if (!locks[p.key] && free.length <= 1) return;
                    locks[p.key] = !locks[p.key];
                    syncLabels();
                });
                top.appendChild(lockBtn);
            }

            var input = el('input');
            input.type = 'range'; input.min = p.min; input.max = p.max;
            input.step = p.step != null ? p.step : 1; input.value = p.value;
            input.addEventListener('input', function () {
                state[p.key] = parseFloat(input.value);
                if (linked && linked.keys.indexOf(p.key) >= 0) relax(p.key);
                syncLabels(); if (paused) frame(lastT);
            });
            wrap.appendChild(top); wrap.appendChild(input);
            controls.appendChild(wrap);
            ctrlRefs.push({ p: p, lab: lab, val: val, input: input, lock: lockBtn });
        });

        // Пересчёт связанных величин: модель возвращает новые значения для свободных ключей,
        // мы их вгоняем в допустимый диапазон и двигаем сами ползунки.
        function relax(changed) {
            var free = linked.keys.filter(function (k) { return k !== changed && !locks[k]; });
            if (!free.length) return;
            var upd = linked.solve(state, changed, free) || {};
            Object.keys(upd).forEach(function (k) {
                var r = byKey(k); if (!r) return;
                var v = clamp(upd[k], r.p.min, r.p.max);
                state[k] = v; r.input.value = v;
            });
        }
        function byKey(k) { for (var i = 0; i < ctrlRefs.length; i++) if (ctrlRefs[i].p.key === k) return ctrlRefs[i]; return null; }
        function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

        var reset = el('button', 'xpl-reset');
        reset.type = 'button';
        reset.addEventListener('click', function () {
            cfg.params.forEach(function (p, i) { state[p.key] = p.value; ctrlRefs[i].input.value = p.value; });
            syncLabels(); if (paused) frame(lastT);
        });
        panel.appendChild(reset);

        // Значение ползунка в выбранной системе единиц: если у параметра указан kind,
        // число и подпись берутся из общей установки единиц страницы.
        function fmtVal(p) {
            var v = state[p.key], U = global.B42Units;
            if (p.kind && U && U.fmt[p.kind]) return U.fmt[p.kind](v);
            var s = p.fmt ? p.fmt(v) : (Math.abs(v) >= 100 ? Math.round(v) : v);
            return s + (p.unit ? (' ' + T(p.unit)) : '');
        }
        function syncLabels() {
            ctrlRefs.forEach(function (r) {
                r.lab.textContent = T(r.p.label);
                r.val.textContent = fmtVal(r.p);
                if (r.lock) {
                    var on = !!locks[r.p.key];
                    r.lock.className = 'xpl-lock' + (on ? ' on' : '');
                    r.lock.textContent = on ? '◉' : '○';
                    r.lock.title = on ? T('lockedHint') : T('freeHint');
                    r.input.classList.toggle('xpl-range-free', !on);
                }
            });
            reset.textContent = '↺ ' + T('reset');
            if (readout) drawReadout();
        }

        // ── приборная строка: ключевые величины крупно, рядом со стендом ──
        var readout = null, readoutRefs = [];
        if (cfg.readout && cfg.readout.length) {
            readout = el('div', 'xpl-readout');
            cfg.readout.forEach(function (r) {
                var cell = el('div', 'xpl-ro');
                var v = el('div', 'xpl-ro-val'), l = el('div', 'xpl-ro-lab');
                cell.appendChild(v); cell.appendChild(l);
                readout.appendChild(cell);
                readoutRefs.push({ r: r, v: v, l: l });
            });
            stageWrap.appendChild(readout);
        }
        function drawReadout(derived, anim) {
            readoutRefs.forEach(function (x) {
                var U = global.B42Units, val;
                try { val = x.r.get(state, derived || {}, anim || {}); } catch (e) { val = null; }
                if (val == null) val = '—';
                else if (x.r.kind && U && U.fmt[x.r.kind]) val = U.fmt[x.r.kind](val);
                else if (typeof val === 'number') val = (Math.abs(val) >= 100 ? Math.round(val) : Math.round(val * 100) / 100) +
                    (x.r.unit ? ' ' + T(x.r.unit) : '');
                x.v.textContent = val;
                x.l.textContent = T(x.r.label);
            });
        }

        // ── график (общий рисовальщик) ──
        function drawPlot(C, derived, anim) {
            var g = C.g, W = C.W, H = C.H, col = colors();
            var pl = cfg.plot;
            var padL = 44, padR = 14, padT = 12, padB = 26;
            g.clearRect(0, 0, W, H);
            var x0 = padL, x1 = W - padR, y0 = H - padB, y1 = padT;
            // Диапазоны осей — число ИЛИ функция(state) (ось Y может подстраиваться под параметры).
            function rv(v) { return typeof v === 'function' ? v(state) : v; }
            var xmin = rv(pl.x.min), xmax = rv(pl.x.max), ymin = rv(pl.y.min), ymax = rv(pl.y.max);
            function sx(x) { return x0 + (x - xmin) / (xmax - xmin) * (x1 - x0); }
            function sy(y) { return y0 + (y - ymin) / (ymax - ymin) * (y1 - y0); }
            // оси
            g.strokeStyle = col.border; g.lineWidth = 1;
            g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y0); g.moveTo(x0, y0); g.lineTo(x0, y1); g.stroke();
            g.fillStyle = col.soft; g.font = '11px Inter, sans-serif';
            g.textAlign = 'center'; g.fillText(T(pl.x.label), (x0 + x1) / 2, H - 8);
            g.save(); g.translate(12, (y0 + y1) / 2); g.rotate(-Math.PI / 2);
            g.textAlign = 'center'; g.fillText(T(pl.y.label), 0, 0); g.restore();
            // Деления по Y — в ВЫБРАННОЙ системе единиц. Если ось помечена видом величины
            // (pl.y.kind: 'P' | 'T' | 'V'), число пересчитывается тем же конвертером, что и приборы:
            // переключил единицы — поменялось всё, включая график.
            var U = global.B42Units;
            function axisNum(v, kind) {
                if (U && kind && U.raw && U.raw[kind]) return U.raw[kind](v);
                return Math.round(v);
            }
            g.textAlign = 'right'; g.fillStyle = col.soft;
            g.fillText(axisNum(ymax, pl.y.kind), x0 - 6, y1 + 8);
            g.fillText(axisNum(ymin, pl.y.kind), x0 - 6, y0);
            // кривая — curve() может вернуть null/NaN (напр. вертикальный участок, который не
            // является функцией y(x)); тогда «отрываем перо», а не тянем линию через 0.
            var n = pl.samples || 120;
            g.strokeStyle = col.link; g.lineWidth = 2; g.beginPath();
            var penDown = false;
            for (var i = 0; i <= n; i++) {
                var x = xmin + (xmax - xmin) * i / n;
                var y = pl.curve(x, state, derived);
                if (y == null || isNaN(y)) { penDown = false; continue; }
                var px = sx(x), py = sy(Math.max(ymin, Math.min(ymax, y)));
                if (!penDown) { g.moveTo(px, py); penDown = true; } else { g.lineTo(px, py); }
            }
            g.stroke();
            // маркер текущего состояния
            if (pl.marker) {
                var m = pl.marker(state, anim, derived);
                if (m) {
                    var mx = sx(m.x), my = sy(Math.max(ymin, Math.min(ymax, m.y)));
                    g.strokeStyle = col.border; g.setLineDash([3, 3]); g.lineWidth = 1;
                    g.beginPath(); g.moveTo(mx, y0); g.lineTo(mx, my); g.lineTo(x0, my); g.stroke();
                    g.setLineDash([]);
                    g.fillStyle = col.accent;
                    g.beginPath(); g.arc(mx, my, 4.5, 0, 7); g.fill();
                    g.fillStyle = col.text; g.textAlign = (mx > (x0 + x1) / 2) ? 'right' : 'left';
                    g.font = '600 12px Inter, sans-serif';
                    // подпись маркера — тоже в выбранной системе (с единицей), иначе график «отстаёт» от приборов
                    var mlabel = (U && pl.y.kind && U.fmt && U.fmt[pl.y.kind])
                        ? U.fmt[pl.y.kind](m.y)
                        : Math.round(m.y) + (pl.y.unit ? (' ' + T(pl.y.unit)) : '');
                    g.fillText(mlabel, mx + (mx > (x0 + x1) / 2 ? -8 : 8), my - 8);
                }
            }
        }

        // ── цикл ──
        var stageC, plotC, raf = null, paused = false, startTs = null, lastT = 0;
        function layout() {
            stageC = fitCanvas(stageCanvas, cfg.stage.height || 220);
            if (plotCanvas) plotC = fitCanvas(plotCanvas, cfg.plot.height || 170);
        }
        function frame(t) {
            lastT = t;
            var anim = cfg.animate ? cfg.animate(t, state) : {};
            var derived = cfg.derive ? cfg.derive(state, anim) : {};
            // сцена
            var g = stageC.g;
            g.clearRect(0, 0, stageC.W, stageC.H);
            cfg.stage.draw(g, { W: stageC.W, H: stageC.H, state: state, anim: anim, derived: derived, time: t, c: colors(), rtl: rtl, T: T });
            // формула
            formula.innerHTML = cfg.formula ? cfg.formula(state, derived, T) : '';
            // приборы
            if (readout) drawReadout(derived, anim);
            // график
            if (plotC) drawPlot(plotC, derived, anim);
        }
        function loop(ts) {
            if (startTs == null) startTs = ts;
            frame((ts - startTs) / 1000);
            raf = global.requestAnimationFrame(loop);
        }
        function start() {
            if (raf != null) return;
            var reduce = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (reduce) { paused = true; frame(0); return; }
            paused = false; startTs = null; raf = global.requestAnimationFrame(loop);
        }
        function stop() {
            if (raf != null) { global.cancelAnimationFrame(raf); raf = null; }
            paused = true;
        }

        // пауза вне экрана
        var io = null;
        if (global.IntersectionObserver) {
            io = new IntersectionObserver(function (es) {
                es.forEach(function (e) { if (e.isIntersecting) start(); else stop(); });
            }, { threshold: 0.05 });
            io.observe(root);
        }
        // перерисовка при resize и смене темы
        var ro = global.ResizeObserver ? new ResizeObserver(function () { layout(); if (paused) frame(lastT); }) : null;
        if (ro) ro.observe(root);
        var mo = new MutationObserver(function () { if (paused) frame(lastT); });
        mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

        // Первый кадр рисуем синхронно — модель видна сразу, даже если rAF ещё не тикнул
        // (важно и для страниц вне экрана, и против «мигания» пустым холстом на загрузке).
        layout(); syncLabels(); frame(0); start();

        return {
            state: state,
            render: function (t) { frame(t != null ? t : lastT); },
            setLang: function (l) { lang = l; rtl = getComputedStyle(document.documentElement).direction === 'rtl'; syncLabels(); frame(lastT); },
            destroy: function () { stop(); if (io) io.disconnect(); if (ro) ro.disconnect(); mo.disconnect(); root.innerHTML = ''; }
        };
    }

    global.Explorable = Explorable;
})(window);
