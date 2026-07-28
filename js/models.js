/* models.js — реестр физических моделей для движка explorable.js.
   Физика вынесена из отдельных lab-*.html страниц сюда, чтобы одну и ту же модель можно было
   вставить в любую статью/учебник одной строкой, а не копипастить код. Каждая модель —
   самодостаточная фабрика: держит своё состояние в замыкании и возвращает
       { cfg, modes?, setMode?, extras? }
   cfg     — конфиг для Explorable(el, cfg)
   modes   — список режимов (если модель многорежимная), setMode(m) — переключение
   extras  — extras(state, derived, T) → HTML, живая строка под стендом (единицы, счётчики)

   Контент (подписи, единицы, тексты) НЕ здесь — он приходит из data/theory/<id>.json. */
(function (global) {
    'use strict';

    var R = 8.314;

    // Набор блоков сцены (stage-kit.js): стрелка, пружина, груз, сосуд, шкала, приборы.
    // Модель описывает физику и собирает сцену из готовых частей — рисовать с нуля не нужно.
    // Грузится ПЕРЕД этим файлом; заглушка нужна лишь чтобы отсутствие набора падало понятно.
    var KIT = global.B42Kit;
    if (!KIT) throw new Error('models.js: подключите js/stage-kit.js перед models.js');

    // ── общие хелперы ──────────────────────────────────────────────
    function clampDt(t, last) { return Math.max(0, Math.min(0.05, t - last)); }  // dt≥0: защита от «времени назад»
    function KtoC(K) { return K - 273.15; }
    function KtoF(K) { return K * 9 / 5 - 459.67; }
    function hueBySpeed(tt) { return 'hsl(' + Math.round(210 * (1 - Math.max(0, Math.min(1, tt)))) + ',72%,55%)'; }

    // ── СИСТЕМА ЕДИНИЦ ────────────────────────────────────────────
    // Одна и та же величина показывается в выбранной системе — чтобы глаз привыкал читать
    // физику в разных единицах, а не только в «школьных». Выбор глобальный на страницу
    // (window.B42_UNITS), модели просто спрашивают текущий формат.
    // Планковские: показываем величину в долях планковской — видно, насколько лабораторная
    // физика далека от масштаба, где ломается само пространство-время.
    var PL = { T: 1.416784e32, P: 4.63309e110 /* кПа */, V: 4.2217e-102 /* л */ };
    function exp3(x) { return x.toExponential(2).replace('e', '·10^').replace('+', ''); }

    var UNIT_SYSTEMS = {
        si:       { name: 'СИ',          T: 'K',   P: 'Па',  V: 'м³',
                    Tf: function (K) { return K; },  Pf: function (kPa) { return kPa * 1000; },     Vf: function (L) { return L / 1000; },      Td: 0, Pd: 0, Vd: 4 },
        metric:   { name: 'бытовая',     T: '°C',  P: 'атм', V: 'л',
                    Tf: KtoC,                        Pf: function (kPa) { return kPa / 101.325; },  Vf: function (L) { return L; },             Td: 0, Pd: 2, Vd: 1 },
        bar:      { name: 'техническая', T: '°C',  P: 'бар', V: 'л',
                    Tf: KtoC,                        Pf: function (kPa) { return kPa / 100; },      Vf: function (L) { return L; },             Td: 0, Pd: 2, Vd: 1 },
        imperial: { name: 'имперская',   T: '°F',  P: 'psi', V: 'gal',
                    Tf: KtoF,                        Pf: function (kPa) { return kPa * 0.145038; }, Vf: function (L) { return L * 0.264172; },  Td: 0, Pd: 1, Vd: 2 },
        planck:   { name: 'планковская', T: 'T_P', P: 'P_P', V: 'V_P', sci: true,
                    Tf: function (K) { return K / PL.T; }, Pf: function (kPa) { return kPa / PL.P; }, Vf: function (L) { return L / PL.V; } }
    };
    function units() { return UNIT_SYSTEMS[global.B42_UNITS] || UNIT_SYSTEMS.metric; }
    function num(v, d, sci) { return sci ? exp3(v) : v.toFixed(d); }
    function fmtT(K) { var u = units(); return num(u.Tf(K), u.Td, u.sci) + ' ' + u.T; }
    function fmtP(kPa) { var u = units(); return num(u.Pf(kPa), u.Pd, u.sci) + ' ' + u.P; }
    function fmtV(L) { var u = units(); return num(u.Vf(L), u.Vd, u.sci) + ' ' + u.V; }
    // raw — только число в выбранной системе (для делений осей), fmt — число с единицей (для подписей).
    // Через них график в explorable.js пересчитывается той же логикой, что и приборы на сцене.
    global.B42Units = {
        list: UNIT_SYSTEMS, T: fmtT, P: fmtP, V: fmtV, current: units,
        raw: {
            T: function (K) { var u = units(); return u.sci ? exp3(u.Tf(K)) : Math.round(u.Tf(K) * Math.pow(10, u.Td)) / Math.pow(10, u.Td); },
            // Tc — вход в градусах Цельсия (так считает модель чайника), а не в кельвинах
            Tc: function (C) { var u = units(); var K = C + 273.15; return u.sci ? exp3(u.Tf(K)) : Math.round(u.Tf(K) * Math.pow(10, u.Td)) / Math.pow(10, u.Td); },
            P: function (kPa) { var u = units(); return u.sci ? exp3(u.Pf(kPa)) : Math.round(u.Pf(kPa) * Math.pow(10, u.Pd)) / Math.pow(10, u.Pd); },
            V: function (L) { var u = units(); return u.sci ? exp3(u.Vf(L)) : Math.round(u.Vf(L) * Math.pow(10, u.Vd)) / Math.pow(10, u.Vd); }
        },
        fmt: { T: fmtT, Tc: function (C) { return fmtT(C + 273.15); }, P: fmtP, V: fmtV }
    };

    // ── КРАСИВЫЙ МАНОМЕТР ─────────────────────────────────────────
    // Не серая дужка, а живой прибор: цветные зоны (синяя «спокойно» → зелёная «норма» →
    // красная «опасно»), риски, стрелка с тенью и крупное читаемое число.
    // Прибор живёт в наборе (KIT.gauge); здесь остаётся только «в каких единицах показывать».
    function drawGauge(g, cx, cy, r, value, max, label, col) {
        KIT.gauge(g, cx, cy, r, value, max, label, col, fmtP);
    }

    // ═══════════════════════════════════════════════════════════════
    // 1. ИДЕАЛЬНЫЙ ГАЗ — частицы, поршень, манометр, эффузия через дырку
    // ═══════════════════════════════════════════════════════════════
    // opts.effusion — дырка в крышке, через которую убегают быстрые молекулы. ПО УМОЛЧАНИЮ ВЫКЛЮЧЕНА:
    // в параграфе про уравнение состояния сосуд обязан быть замкнутым, иначе число частиц меняется
    // и давление не может быть постоянным — модель противоречила бы формуле, которую иллюстрирует.
    function gasModel(data, opts) {
        var EFFUSION = !!(opts && opts.effusion);
        var HOLE = [0.42, 0.58];
        var sim = { parts: [], T: null, last: 0, escaped: 0 };
        function speedFor(T) { return 0.5 * Math.sqrt(T / 300); }
        function respawn(p, T) {
            var s = speedFor(T), a = Math.random() * 6.2832;
            p.x = 0.05 + Math.random() * 0.9; p.y = 0.1 + Math.random() * 0.85;
            p.vx = Math.cos(a) * s; p.vy = Math.sin(a) * s; p.out = false; p.life = 0;
            return p;
        }
        function ensure(st) {
            while (sim.parts.length < st.N) sim.parts.push(respawn({}, st.T));
            if (sim.parts.length > st.N) sim.parts.length = st.N;
            if (sim.T != null && st.T !== sim.T) {
                var k = Math.sqrt(st.T / sim.T);
                for (var i = 0; i < sim.parts.length; i++) { sim.parts[i].vx *= k; sim.parts[i].vy *= k; }
            }
            sim.T = st.T;
        }
        function nMol(st) { return st.N / 100; }
        function pressure(st) { return nMol(st) * R * st.T / st.V; }

        return {
            escapedCount: function () { return sim.escaped; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    ensure(st);
                    var dt = clampDt(t, sim.last); sim.last = t;
                    for (var i = 0; i < sim.parts.length; i++) {
                        var p = sim.parts[i];
                        if (p.out) { p.x += p.vx * dt; p.y += p.vy * dt; p.life -= dt; if (p.life <= 0) respawn(p, st.T); continue; }
                        p.x += p.vx * dt; p.y += p.vy * dt;
                        if (p.x < 0) { p.x = 0; p.vx = -p.vx; } else if (p.x > 1) { p.x = 1; p.vx = -p.vx; }
                        if (p.y > 1) { p.y = 1; p.vy = -p.vy; }
                        else if (p.y < 0) {
                            if (EFFUSION && p.x >= HOLE[0] && p.x <= HOLE[1]) { p.out = true; p.life = 1.1; sim.escaped++; }
                            else { p.y = 0; p.vy = -p.vy; }   // замкнутый сосуд: N постоянно, формула честна
                        }
                    }
                    return { parts: sim.parts };
                },
                derive: function (st) { return { P: pressure(st), n: nMol(st) }; },
                stage: {
                    height: 250,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, a = ctx.anim;
                        // Справа жёстко зарезервирована зона приборов (термометр + манометр), плюс
                        // место под шток поршня — иначе сосуд наезжает на приборы при большом объёме.
                        var GAUGES = 150, ROD = 54, vx0 = 22;   // 150 — колонка приборов вместе с подписями сбоку
                        var maxW = Math.max(120, W - GAUGES - ROD - vx0);
                        var hbox = H * 0.72, vy0 = (H - hbox) / 2 + 6;
                        var wbox = maxW * (0.32 + 0.68 * (st.V - 1) / 9), xP = vx0 + wbox;
                        function SX(nx) { return vx0 + nx * wbox; }
                        g.strokeStyle = col.soft; g.lineWidth = 2; g.lineCap = 'round';
                        g.beginPath();
                        g.moveTo(vx0, vy0); g.lineTo(vx0, vy0 + hbox); g.lineTo(xP, vy0 + hbox);
                        if (EFFUSION) {                        // крышка с отверстием
                            g.moveTo(vx0, vy0); g.lineTo(SX(HOLE[0]), vy0);
                            g.moveTo(SX(HOLE[1]), vy0); g.lineTo(xP, vy0);
                        } else {                               // сплошная крышка — сосуд замкнут
                            g.moveTo(vx0, vy0); g.lineTo(xP, vy0);
                        }
                        g.stroke();
                        if (EFFUSION) {                        // «губы» отверстия
                            g.strokeStyle = col.accent; g.lineWidth = 3;
                            g.beginPath(); g.moveTo(SX(HOLE[0]), vy0); g.lineTo(SX(HOLE[0]) - 5, vy0 - 6);
                            g.moveTo(SX(HOLE[1]), vy0); g.lineTo(SX(HOLE[1]) + 5, vy0 - 6); g.stroke();
                        }
                        KIT.piston(g, xP, vy0, hbox, {
                            color: col.link, thickness: 8, rod: 40, rodWidth: 4,
                            knob: 'stroke', knobR: 6, knobAt: 46
                        });
                        // молекулы: цвет по скорости, улетевшие гаснут
                        KIT.particles(g, a.parts, {
                            r: 3.3,
                            toX: function (p) { return SX(p.x); },
                            toY: function (p) { return vy0 + p.y * hbox; },
                            color: function (p) { return hueBySpeed((Math.hypot(p.vx, p.vy) - 0.29) / 0.62); },
                            alpha: function (p) { return p.out ? Math.max(0, p.life) : 1; }
                        });
                        // ── ПАНЕЛЬ ПРИБОРОВ: вертикальная колонка справа, у каждого прибора своя
                        // полоса по высоте. Раньше манометр и термометр стояли в ряд, и их подписи
                        // («27 °C» и «1,97 атм») налезали друг на друга — теперь пересечься нечему.
                        var panelX = W - GAUGES / 2;            // центр колонки приборов
                        drawGauge(g, panelX, 46, 30, ctx.derived.P, 3000, ctx.T('gauge'), col);   // верх: манометр
                        // низ: термометр (значение в выбранной системе единиц)
                        var tCy = H - 62, tlen = 54, tx = panelX - 26;
                        var tfrac = Math.max(0, Math.min(1, (st.T - 100) / 900));
                        KIT.thermometer(g, tx, tCy - tlen / 2, tlen, tfrac, {
                            color: hueBySpeed(tfrac), track: col.border, width: 7, bulbR: 6
                        });
                        // подписи СБОКУ от прибора, не под ним — иначе налезают на манометр
                        KIT.readout(g, [
                            { text: ctx.T('T'), y: tCy - tlen / 2 + 10, size: 9.5, weight: '', color: col.soft },
                            { text: fmtT(st.T), y: tCy + 4, size: 12, weight: '600', color: col.text },
                            { text: fmtV(st.V), y: tCy + 20, size: 9.5, color: col.soft }
                        ], { x: tx + 12 });
                    }
                },
                formula: function (st, d, T) {
                    var P0 = 0.40 * R * 300 / 5;
                    var note = d.P > P0 * 1.05 ? T('hot') : (d.P < P0 * 0.95 ? T('cold') : '');
                    return '<span class="xf-op">P = nRT ∕ V = </span><span class="xf-var">' + d.n.toFixed(2) +
                        '</span><span class="xf-op">·8.314·</span><span class="xf-var">' + st.T +
                        '</span><span class="xf-op"> ∕ </span><span class="xf-var">' + st.V +
                        '</span><span class="xf-op"> = </span><span class="xf-res">' + d.P.toFixed(0) + ' ' + T('unit_kPa') + '</span>' +
                        (note ? '<br><i>' + note + '</i>' : '');
                },
                plot: {
                    height: 170,
                    x: { label: 'xV', min: 1, max: 10 },
                    y: { label: 'yP', unit: 'unit_kPa', kind: 'P', min: 0, max: function (s) { return Math.round(nMol(s) * R * s.T * 1.05); } },
                    samples: 120,
                    curve: function (V, s) { return nMol(s) * R * s.T / V; },
                    marker: function (s, a, d) { return { x: s.V, y: d.P }; }
                }
            },
            // Все величины — в выбранной системе единиц (переключается одним местом на странице),
            // плюс «сырое» значение в скобках, чтобы связь с формулой не терялась.
            extras: function (st, d, T) {
                var P = pressure(st);
                return '<b>T</b> ' + fmtT(st.T) + ' &nbsp;·&nbsp; <b>V</b> ' + fmtV(st.V) +
                    ' &nbsp;·&nbsp; <b>P</b> ' + fmtP(P) +
                    ' &nbsp;·&nbsp; <b>N</b> ' + st.N +
                    (EFFUSION ? ' &nbsp;·&nbsp; <b>' + T('escaped') + '</b> ' + sim.escaped : '');
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 2. ФАЗОВЫЙ ПЕРЕХОД — закипающий чайник (плато кипения = скрытая теплота)
    // ═══════════════════════════════════════════════════════════════
    function kettleModel(data) {
        var C = data.constants;
        var sim = { Q: 0, last: 0, mol: [], bub: [], steam: [], bubAcc: 0, stAcc: 0 };
        function TboilC(P) { return 1 / (1 / 373.15 - (C.R / C.Lmol) * Math.log(P)) - 273.15; }
        function phaseOf(st, Q) {
            var Tb = TboilC(st.pressure), Q1 = C.m * C.c * (Tb - C.Tstart), Qv = C.m * C.Lvap, T, vf, ph;
            if (Q < Q1) { T = C.Tstart + Q / (C.m * C.c); vf = 0; ph = 'heat'; }
            else if (Q < Q1 + Qv) { T = Tb; vf = (Q - Q1) / Qv; ph = 'boil'; }
            else { T = Tb; vf = 1; ph = 'dry'; }
            return { T: T, vf: vf, phase: ph, Tb: Tb, Q1: Q1, Qv: Qv, Q: Q };
        }
        function rndMol() { var a = Math.random() * 6.2832; return { x: 0.1 + Math.random() * 0.8, y: 0.1 + Math.random() * 0.8, vx: Math.cos(a), vy: Math.sin(a) }; }

        return {
            boilPointAt: TboilC,
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    if (!sim.mol.length) for (var k = 0; k < 22; k++) sim.mol.push(rndMol());
                    var dt = clampDt(t, sim.last); sim.last = t;
                    sim.Q += st.power * dt * C.timescale;
                    var ph = phaseOf(st, sim.Q);
                    if (sim.Q > ph.Q1 + ph.Qv + C.m * C.c * 8) sim.Q = 0;    // выкипел → доливаем
                    var sf = 0.26 * Math.sqrt(Math.max(0.2, ph.T / 293));
                    for (var i = 0; i < sim.mol.length; i++) {
                        var p = sim.mol[i]; p.x += p.vx * sf * dt; p.y += p.vy * sf * dt;
                        if (p.x < 0) { p.x = 0; p.vx = -p.vx; } else if (p.x > 1) { p.x = 1; p.vx = -p.vx; }
                        if (p.y < 0) { p.y = 0; p.vy = -p.vy; } else if (p.y > 1) { p.y = 1; p.vy = -p.vy; }
                    }
                    if (ph.phase === 'boil') {
                        sim.bubAcc += dt * (st.power / 1500);
                        while (sim.bubAcc > 0.11) { sim.bubAcc -= 0.11; sim.bub.push({ x: 0.1 + Math.random() * 0.8, y: 1, r: 1.4 + Math.random() * 2 }); }
                        sim.stAcc += dt;
                        while (sim.stAcc > 0.16) { sim.stAcc -= 0.16; sim.steam.push({ dx: (Math.random() - 0.5) * 12, y: 0, r: 3 + Math.random() * 3, life: 1 }); }
                    }
                    for (var b = sim.bub.length - 1; b >= 0; b--) { sim.bub[b].y -= 0.7 * dt; if (sim.bub[b].y < 0.03) sim.bub.splice(b, 1); }
                    for (var s = sim.steam.length - 1; s >= 0; s--) { sim.steam[s].y += 24 * dt; sim.steam[s].life -= dt * 0.7; if (sim.steam[s].life <= 0) sim.steam.splice(s, 1); }
                    return { Q: sim.Q, mol: sim.mol, bub: sim.bub, steam: sim.steam };
                },
                derive: function (st, a) { return phaseOf(st, a.Q); },
                stage: {
                    height: 260,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, a = ctx.anim, d = ctx.derived, Tmax = 130;
                        function rr(x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
                        var tx = 26, ttop = 24, tbot = H - 40, tlen = tbot - ttop;          // термометр
                        g.strokeStyle = col.border; g.lineWidth = 2; g.beginPath(); g.moveTo(tx, ttop); g.lineTo(tx, tbot); g.stroke();
                        g.fillStyle = col.warn; g.beginPath(); g.arc(tx, tbot + 6, 6, 0, 6.2832); g.fill();
                        var my = tbot - tlen * Math.max(0, Math.min(1, d.T / Tmax));
                        g.strokeStyle = col.warn; g.lineWidth = 4; g.beginPath(); g.moveTo(tx, tbot); g.lineTo(tx, my); g.stroke();
                        var byk = tbot - tlen * Math.max(0, Math.min(1, d.Tb / Tmax));      // пунктир точки кипения
                        g.strokeStyle = col.soft; g.lineWidth = 1; g.setLineDash([3, 2]);
                        g.beginPath(); g.moveTo(tx - 6, byk); g.lineTo(tx + 10, byk); g.stroke(); g.setLineDash([]);
                        g.fillStyle = col.text; g.font = '600 10px Inter'; g.textAlign = 'left'; g.fillText(Math.round(d.T) + '°', tx + 7, my - 3);
                        // ── ЧАЙНИК: корпус слегка на конус (как настоящий), гнутый носик,
                        // дугообразная ручка, крышка с шишечкой. Рисуем до воды, чтобы вода легла внутрь.
                        var bx = 92, bw = Math.min(W - bx - 62, 210), by = 46, bh = H - 116;
                        var taper = bw * 0.07;                       // сужение к горлу
                        g.strokeStyle = col.soft; g.lineWidth = 2; g.lineJoin = 'round';
                        g.beginPath();
                        g.moveTo(bx + taper, by);                    // горло слева
                        g.lineTo(bx, by + bh - 14);                  // расширяется книзу
                        g.quadraticCurveTo(bx, by + bh, bx + 14, by + bh);          // скруглённое дно
                        g.lineTo(bx + bw - 14, by + bh);
                        g.quadraticCurveTo(bx + bw, by + bh, bx + bw, by + bh - 14);
                        g.lineTo(bx + bw - taper, by);               // горло справа
                        g.stroke();
                        // носик — гнутый, с расширением на конце
                        g.beginPath();
                        g.moveTo(bx + bw - taper - 2, by + 12);
                        g.quadraticCurveTo(bx + bw + 26, by + 4, bx + bw + 34, by - 14);
                        g.lineTo(bx + bw + 44, by - 8);
                        g.quadraticCurveTo(bx + bw + 34, by + 16, bx + bw - taper + 4, by + 30);
                        g.closePath(); g.stroke();
                        // ручка — дуга над корпусом
                        g.lineWidth = 2.5;
                        g.beginPath();
                        g.moveTo(bx + taper + 4, by + 2);
                        g.quadraticCurveTo(bx + bw * 0.42, by - 34, bx + bw - taper - 6, by + 2);
                        g.stroke();
                        // крышка + шишечка
                        g.lineWidth = 2;
                        g.beginPath(); g.moveTo(bx + taper - 3, by); g.lineTo(bx + bw - taper + 3, by); g.stroke();
                        g.beginPath(); g.moveTo(bx + bw * 0.34, by); g.lineTo(bx + bw * 0.40, by - 7);
                        g.lineTo(bx + bw * 0.52, by - 7); g.lineTo(bx + bw * 0.58, by); g.stroke();
                        g.fillStyle = col.soft;
                        g.beginPath(); g.arc(bx + bw * 0.46, by - 10, 3.5, 0, 6.2832); g.fill();
                        var pad = 9, wx = bx + pad, wxw = bw - 2 * pad, wyBot = by + bh - pad, fullH = bh - 2 * pad - 4;
                        var wTop = wyBot - fullH * Math.max(0.12, 1 - d.vf);
                        g.fillStyle = 'rgba(74,124,170,0.30)'; g.fillRect(wx, wTop, wxw, wyBot - wTop);
                        g.strokeStyle = 'rgba(74,124,170,0.65)'; g.lineWidth = 1.5;
                        g.beginPath(); g.moveTo(wx, wTop); g.lineTo(wx + wxw, wTop); g.stroke();
                        g.fillStyle = hueBySpeed((d.T - 20) / 110);
                        for (var i = 0; i < a.mol.length; i++) { var p = a.mol[i]; g.beginPath(); g.arc(wx + p.x * wxw, wTop + p.y * (wyBot - wTop), 2.4, 0, 6.2832); g.fill(); }
                        g.strokeStyle = 'rgba(255,255,255,0.75)'; g.lineWidth = 1.2;
                        for (var b2 = 0; b2 < a.bub.length; b2++) { var bb = a.bub[b2]; g.beginPath(); g.arc(wx + bb.x * wxw, wTop + bb.y * (wyBot - wTop), bb.r, 0, 6.2832); g.stroke(); }
                        var spx = bx + bw + 16, spy = by - 6;
                        for (var s2 = 0; s2 < a.steam.length; s2++) {
                            var ss = a.steam[s2]; g.globalAlpha = Math.max(0, ss.life) * 0.45; g.fillStyle = col.soft;
                            g.beginPath(); g.arc(spx + ss.dx, spy - ss.y, ss.r, 0, 6.2832); g.fill();
                        }
                        g.globalAlpha = 1;
                        var fy = by + bh, pw = (st.power - 500) / 2500, fh = 9 + pw * 26;    // пламя ∝ мощности
                        for (var f = 0; f < 7; f++) {
                            var fx = bx + bw * (0.16 + 0.68 * f / 6);
                            g.fillStyle = 'rgba(230,120,30,0.85)';
                            g.beginPath(); g.moveTo(fx - 5, fy + fh); g.quadraticCurveTo(fx - 6, fy + fh * 0.35, fx, fy + 2); g.quadraticCurveTo(fx + 6, fy + fh * 0.35, fx + 5, fy + fh); g.closePath(); g.fill();
                            g.fillStyle = 'rgba(250,210,70,0.9)';
                            g.beginPath(); g.moveTo(fx - 2.5, fy + fh * 0.75); g.quadraticCurveTo(fx - 3, fy + fh * 0.4, fx, fy + fh * 0.15); g.quadraticCurveTo(fx + 3, fy + fh * 0.4, fx + 2.5, fy + fh * 0.75); g.closePath(); g.fill();
                        }
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">T = </span><span class="xf-res">' + d.T.toFixed(0) + ' °C</span>' +
                        '<span class="xf-op"> (' + (d.T + 273.15).toFixed(0) + ' K · ' + (d.T * 9 / 5 + 32).toFixed(0) + ' °F) — </span><i>' + T('phase_' + d.phase) + '</i>' +
                        '<br><span class="xf-op">' + T('boilpoint') + ' </span><span class="xf-var">' + d.Tb.toFixed(0) +
                        '</span><span class="xf-op"> °C · ' + T('vapor') + ' </span><span class="xf-var">' + Math.round(d.vf * 100) + '%</span>' +
                        '<span class="xf-op"> · ' + T('energyx') + ' ×' + (d.Qv / d.Q1).toFixed(1) + '</span>';
                },
                plot: {
                    height: 175,
                    x: { label: 'xHeat', min: 0, max: function (s) { var ph = phaseOf(s, 1e12); return Math.round((ph.Q1 + ph.Qv) / 1000); } },
                    y: { label: 'yTemp', kind: 'Tc', min: 0, max: 130 },
                    samples: 130,
                    curve: function (xkJ, s) { return phaseOf(s, xkJ * 1000).T; },
                    marker: function (s, a, d) { return { x: d.Q / 1000, y: d.T }; }
                }
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 3. ПРОЦЕССЫ И ДВИГАТЕЛЬ — 4 изопроцесса + цикл Отто, с авторазвёрткой
    // ═══════════════════════════════════════════════════════════════
    function engineModel(data) {
        var K = data.constants, P0 = K.n * K.R * K.T0 / K.V0;
        var MODES = ['isothermal', 'adiabatic', 'isobaric', 'isochoric', 'engine'];
        var AUTO = { isothermal: 0, adiabatic: 0, isobaric: 0, isochoric: 1 };   // какой слайдер ведём сами
        var mode = 'isothermal', host = null;
        var sim = { parts: [], T: null, last: 0 };

        function pointFor(m, st) {
            var V = st.V, T = st.T, P;
            if (m === 'isothermal') P = K.n * K.R * T / V;
            else if (m === 'adiabatic') { P = P0 * Math.pow(K.V0 / V, K.gamma); T = P * V / (K.n * K.R); }
            else if (m === 'isobaric') { P = P0; T = P0 * V / (K.n * K.R); }
            else { V = K.V0; P = K.n * K.R * T / V; }
            return { V: V, T: T, P: P };
        }

        // Связанные ползунки: если величина в процессе НЕ независима, а вычисляется (в адиабате и
        // изобаре температура определяется объёмом), её бегунок должен ехать сам. Иначе выходит
        // ложь: число в формуле меняется, а ползунок стоит на месте.
        function syncDependentSlider(m, pt) {
            if (!host) return;
            var inputs = host.querySelectorAll('.xpl-ctrl input');
            var idx = (m === 'adiabatic' || m === 'isobaric') ? 1 : (m === 'isochoric' ? 0 : -1);
            if (idx < 0 || !inputs[idx]) return;
            var val = idx === 1 ? pt.T : pt.V, p = data.params[idx];
            val = Math.max(p.min, Math.min(p.max, val));
            if (Math.abs(parseFloat(inputs[idx].value) - val) < 0.01) return;   // уже там — не дёргаем
            inputs[idx].value = val;
            // важно: обновляем и подпись значения, но НЕ шлём 'input' — иначе уйдём в рекурсию
            // (input → animate → syncDependentSlider → input → ...). Состояние обновляем напрямую.
            var labels = host.querySelectorAll('.xpl-ctrl-val');
            if (labels[idx]) {
                var u = data.i18n && data.i18n[cfgLang()] && data.i18n[cfgLang()][p.unit];
                labels[idx].textContent = (Math.abs(val) >= 100 ? Math.round(val) : Math.round(val * 100) / 100) + (u ? ' ' + u : '');
            }
        }
        function cfgLang() { return (document.documentElement.getAttribute('lang')) || 'ru'; }
        function corners(st) {
            var r = 6, Vmax = Math.max(4, st.V), Vmin = Vmax / r;
            var T1 = 300, P1 = K.n * K.R * T1 / Vmax;
            var T2 = T1 * Math.pow(r, K.gamma - 1), P2 = P1 * Math.pow(r, K.gamma);
            var T3 = Math.max(st.T, T2 * 1.08), P3 = P2 * (T3 / T2);
            var T4 = T3 / Math.pow(r, K.gamma - 1);
            var Cv = K.n * K.R / (K.gamma - 1);
            return { r: r, Vmax: Vmax, Vmin: Vmin, T1: T1, T2: T2, T3: T3, T4: T4, P1: P1, P3: P3,
                     W: Cv * (T3 - T2) - Cv * (T4 - T1), eta: 1 - 1 / Math.pow(r, K.gamma - 1) };
        }
        function ottoAt(t, st) {
            var c = corners(st), phase = ((t % 4.8) / 4.8) * 4;
            var leg = Math.min(3, Math.floor(phase)), f = phase - leg; f = f * f * (3 - 2 * f);
            var V, P, T;
            if (leg === 0) { V = c.Vmax + (c.Vmin - c.Vmax) * f; P = c.P1 * Math.pow(c.Vmax / V, K.gamma); T = P * V / (K.n * K.R); }
            else if (leg === 1) { V = c.Vmin; T = c.T2 + (c.T3 - c.T2) * f; P = K.n * K.R * T / V; }
            else if (leg === 2) { V = c.Vmin + (c.Vmax - c.Vmin) * f; P = c.P3 * Math.pow(c.Vmin / V, K.gamma); T = P * V / (K.n * K.R); }
            else { V = c.Vmax; T = c.T4 + (c.T1 - c.T4) * f; P = K.n * K.R * T / V; }
            return { V: V, P: P, T: T, leg: leg, corners: c };
        }
        // Ведущий параметр колеблется сам — характерная кривая процесса рисуется без перетаскивания.
        function autoSweep(t) {
            if (mode === 'engine' || !host) return;
            var idx = AUTO[mode], p = data.params[idx];
            var inputs = host.querySelectorAll('.xpl-ctrl input');
            if (!inputs[idx]) return;
            var mid = (p.min + p.max) / 2, amp = (p.max - p.min) / 2;
            inputs[idx].value = mid + amp * Math.sin(2 * Math.PI * t / (idx === 0 ? 6 : 8));
            inputs[idx].dispatchEvent(new Event('input'));
        }
        function stepParticles(t, T) {
            if (!sim.parts.length) for (var k = 0; k < 24; k++) {
                var a0 = Math.random() * 6.2832, s0 = 0.34;
                sim.parts.push({ x: 0.08 + Math.random() * 0.84, y: 0.08 + Math.random() * 0.84, vx: Math.cos(a0) * s0, vy: Math.sin(a0) * s0 });
            }
            var dt = clampDt(t, sim.last); sim.last = t;
            if (sim.T != null && T !== sim.T) {
                var kf = Math.sqrt(Math.max(50, T) / Math.max(50, sim.T));
                for (var j = 0; j < sim.parts.length; j++) { sim.parts[j].vx *= kf; sim.parts[j].vy *= kf; }
            }
            sim.T = T;
            for (var i = 0; i < sim.parts.length; i++) {
                var p = sim.parts[i]; p.x += p.vx * dt; p.y += p.vy * dt;
                if (p.x < 0) { p.x = 0; p.vx = -p.vx; } else if (p.x > 1) { p.x = 1; p.vx = -p.vx; }
                if (p.y < 0) { p.y = 0; p.vy = -p.vy; } else if (p.y > 1) { p.y = 1; p.vy = -p.vy; }
            }
            return sim.parts;
        }

        return {
            modes: MODES,
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; },
            bindHost: function (el) { host = el; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    autoSweep(t);
                    var pt = mode === 'engine' ? ottoAt(t, st) : pointFor(mode, st);
                    if (mode !== 'engine') syncDependentSlider(mode, pt);   // зависимый бегунок едет сам
                    pt.parts = stepParticles(t, pt.T);
                    return pt;
                },
                derive: function (st, a) { return a; },
                stage: {
                    height: 240,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, a = ctx.anim, d = ctx.derived;
                        var Vmax = mode === 'engine' ? d.corners.Vmax : 10, Vmin = mode === 'engine' ? d.corners.Vmin : 1;
                        var hbox = H * 0.7, y0 = (H - hbox) / 2, x0 = 26;
                        var frac = Math.max(0, Math.min(1, (a.V - Vmin) / (Vmax - Vmin)));
                        var wbox = (W - 96) * (0.24 + 0.72 * frac), xP = x0 + wbox;
                        g.strokeStyle = col.soft; g.lineWidth = 2; g.strokeRect(x0, y0, wbox, hbox);
                        g.fillStyle = col.link; g.fillRect(xP, y0 - 2, 8, hbox + 4);
                        g.strokeStyle = col.link; g.lineWidth = 4;
                        g.beginPath(); g.moveTo(xP + 8, y0 + hbox / 2); g.lineTo(xP + 34, y0 + hbox / 2); g.stroke();
                        var tt = Math.max(0, Math.min(1, (a.T - 250) / 900));
                        g.fillStyle = 'hsla(' + Math.round(210 * (1 - tt)) + ',70%,55%,0.30)';
                        g.fillRect(x0 + 2, y0 + 2, wbox - 4, hbox - 4);
                        g.fillStyle = hueBySpeed(tt);
                        for (var i = 0; i < a.parts.length; i++) {
                            var pp = a.parts[i];
                            g.beginPath(); g.arc(x0 + 6 + pp.x * (wbox - 12), y0 + 6 + pp.y * (hbox - 12), 2.6, 0, 6.2832); g.fill();
                        }
                        g.fillStyle = col.soft; g.font = '11px Inter'; g.textAlign = 'center';
                        g.fillText(Math.round(a.T) + ' K', x0 + wbox / 2, y0 + hbox + 16);
                    }
                },
                formula: function (st, d, T) {
                    if (mode === 'isothermal')
                        return '<span class="xf-op">P·V = nRT = </span><span class="xf-var">' + (K.n * K.R * d.T).toFixed(0) +
                            '</span><span class="xf-op"> → P = </span><span class="xf-res">' + d.P.toFixed(0) + ' ' + T('unit_kPa') + '</span>';
                    if (mode === 'adiabatic')
                        return '<span class="xf-op">P·V^1.4 = const → P = </span><span class="xf-res">' + d.P.toFixed(0) + ' ' + T('unit_kPa') +
                            '</span><span class="xf-op">, T = </span><span class="xf-var">' + d.T.toFixed(0) + ' K</span> ' +
                            (d.V < K.V0 ? '🔥' : (d.V > K.V0 ? '❄️' : ''));
                    if (mode === 'isobaric')
                        return '<span class="xf-op">P = ' + P0.toFixed(0) + ' ' + T('unit_kPa') + ' (const) → T = P·V∕(nR) = </span>' +
                            '<span class="xf-res">' + d.T.toFixed(0) + ' K</span>';
                    if (mode === 'isochoric')
                        return '<span class="xf-op">V = 5 ' + T('unit_L') + ' (const) → P = nRT∕V = </span>' +
                            '<span class="xf-res">' + d.P.toFixed(0) + ' ' + T('unit_kPa') + '</span>';
                    var c = d.corners;
                    return '<span class="xf-op">η = 1 − 1∕r^0.4 = </span><span class="xf-res">' + (c.eta * 100).toFixed(0) + '%</span>' +
                        '<span class="xf-op"> · W = </span><span class="xf-var">' + c.W.toFixed(0) + ' ' + T('unit_kJ_alt') +
                        '</span><span class="xf-op"> ∕' + T('cycle') + ' · r=' + c.r + '</span>';
                },
                plot: {
                    height: 170,
                    x: { label: 'xV', min: 1, max: 10 },
                    y: { label: 'yP', unit: 'unit_kPa', kind: 'P', min: 0,
                         max: function (s) { return mode === 'engine' ? Math.round(corners(s).P3 * 1.1) : Math.round(P0 * 3.2); } },
                    samples: 110,
                    curve: function (V, st, d) {
                        if (mode === 'isothermal') return K.n * K.R * st.T / V;
                        if (mode === 'isobaric') return P0;
                        if (mode === 'isochoric') return null;       // вертикаль — не функция y(V), перо отрывается
                        if (mode === 'adiabatic') return P0 * Math.pow(K.V0 / V, K.gamma);
                        var c = d.corners || corners(st);
                        if (d.leg == null) return null;
                        return d.leg <= 1 ? c.P1 * Math.pow(c.Vmax / V, K.gamma) : c.P3 * Math.pow(c.Vmin / V, K.gamma);
                    },
                    marker: function (st, a, d) { return { x: d.V, y: d.P }; }
                }
            },
            extras: function (st, d, T) {
                if (mode === 'engine') {
                    var c = corners(st);
                    return '<b>T₁</b> ' + c.T1.toFixed(0) + ' K · <b>T₂</b> ' + c.T2.toFixed(0) + ' K · <b>T₃</b> ' + c.T3.toFixed(0) +
                        ' K · <b>T₄</b> ' + c.T4.toFixed(0) + ' K &nbsp;·&nbsp; <b>' + T('efficiency') + '</b> ' + (c.eta * 100).toFixed(0) +
                        '% &nbsp;·&nbsp; <b>' + T('work') + '</b> ' + c.W.toFixed(0) + ' ' + T('unit_kJ_alt') + '/' + T('cycle');
                }
                var pt = pointFor(mode, st);
                return '<b>T</b> ' + pt.T.toFixed(0) + ' ' + T('unit_K') + ' = ' + KtoC(pt.T).toFixed(0) + ' °C = ' + KtoF(pt.T).toFixed(0) + ' °F' +
                    ' &nbsp;·&nbsp; <b>V</b> ' + pt.V.toFixed(2) + ' ' + T('unit_L') +
                    ' &nbsp;·&nbsp; <b>P</b> ' + pt.P.toFixed(0) + ' ' + T('unit_kPa') + ' = ' + (pt.P / 101.325).toFixed(2) + ' ' + T('unit_atm');
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 4. РАВНОУСКОРЕННОЕ ДВИЖЕНИЕ — тело, векторы v и a, график x(t)
    // ═══════════════════════════════════════════════════════════════
    // Главное, что должен увидеть ученик: когда векторы смотрят в разные стороны, тело
    // тормозит, останавливается и едет назад — при том, что ускорение всё время постоянно.
    function motionModel(data) {
        var K = data.constants || {}, TMAX = K.tmax || 8;
        function xAt(t, st) { return st.v0 * t + st.a * t * t / 2; }
        function vAt(t, st) { return st.v0 + st.a * t; }

        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var tt = t % TMAX;                       // цикл: пробег заново
                    return { t: tt, x: xAt(tt, st), v: vAt(tt, st) };
                },
                derive: function (st, a) {
                    var tStop = st.a !== 0 ? -st.v0 / st.a : null;   // момент разворота, если он есть
                    return { t: a.t, x: a.x, v: a.v,
                             tStop: (tStop !== null && tStop > 0 && tStop < TMAX) ? tStop : null };
                },
                stage: {
                    height: 210,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var y = H * 0.52, pad = 30;
                        // диапазон координаты по всему пробегу — чтобы масштаб не прыгал
                        var lo = 0, hi = 0;
                        for (var s = 0; s <= TMAX; s += 0.25) { var xv = xAt(s, st); if (xv < lo) lo = xv; if (xv > hi) hi = xv; }
                        var span = Math.max(1, hi - lo);
                        var SX = KIT.scale({ min: lo, max: lo + span, from: pad, to: W - pad });
                        // ось-дорога с делениями
                        KIT.axis(g, pad, W - pad, y, {
                            color: col.border, ticks: 4, tickSize: 4, labelDy: 18, labelColor: col.soft,
                            tickLabel: function (k) { return Math.round(lo + span * k / 4) + ' м'; }
                        });
                        // точка старта и точка разворота, если тело возвращается
                        KIT.marker(g, SX(0), y - 26, y + 8, { dash: [3, 3], color: col.soft, label: 'старт', labelY: y - 32, labelColor: col.soft });
                        if (d.tStop) {
                            KIT.marker(g, SX(xAt(d.tStop, st)), y - 26, y + 8,
                                { dash: [2, 3], color: col.accent, label: 'разворот', labelY: y - 32, labelColor: col.accent });
                        }
                        // тело
                        var bx = SX(d.x);
                        KIT.body(g, bx, y - 12, { shape: 'dot', size: 18, color: col.link });
                        // вектор скорости (зелёный) и ускорения (красный) — разной длины, от тела
                        function vec(val, sc, colr, dy, label) {
                            if (Math.abs(val) < 0.05) return;
                            var len = Math.max(-70, Math.min(70, val * sc));
                            KIT.arrow(g, bx, y + dy, len, 0, {
                                color: colr, width: 2.5, head: 7, headW: 4, shorten: 0, min: 0,
                                label: label, labelGap: 6, labelDy: 3, labelAlign: len > 0 ? 'left' : 'right'
                            });
                        }
                        vec(d.v, 3, '#2e7d32', -34, 'v');
                        vec(st.a, 9, '#b31b1b', 22, 'a');
                        // счётчик времени
                        KIT.readout(g, [
                            { text: 't = ' + d.t.toFixed(1) + ' с', y: 20, size: 12, weight: '600', color: col.text },
                            { text: 'v = ' + d.v.toFixed(1) + ' м/с', y: 36, size: 11, color: col.soft },
                            { text: 'x = ' + d.x.toFixed(1) + ' м', y: 51, size: 11, color: col.soft }
                        ]);
                    }
                },
                formula: function (st, d, T) {
                    var sign = st.a >= 0 ? '+' : '−';
                    var mode = Math.abs(d.v) < 0.2 ? T('turn') : (d.v * st.a > 0 ? T('speedup') : T('slowdown'));
                    return '<span class="xf-op">x = v₀t ' + sign + ' at²∕2 = </span>' +
                        '<span class="xf-var">' + st.v0 + '</span><span class="xf-op">·' + d.t.toFixed(1) + ' ' + sign + ' </span>' +
                        '<span class="xf-var">' + Math.abs(st.a) + '</span><span class="xf-op">·' + d.t.toFixed(1) + '²∕2 = </span>' +
                        '<span class="xf-res">' + d.x.toFixed(1) + ' м</span>' +
                        '<br><i>' + mode + '</i>';
                },
                plot: {
                    height: 165,
                    x: { label: 'xTime', min: 0, max: TMAX },
                    y: { label: 'yCoord',
                         min: function (s) { var lo = 0; for (var t = 0; t <= TMAX; t += 0.25) lo = Math.min(lo, xAt(t, s)); return Math.floor(lo); },
                         max: function (s) { var hi = 0; for (var t = 0; t <= TMAX; t += 0.25) hi = Math.max(hi, xAt(t, s)); return Math.ceil(hi + 1); } },
                    samples: 120,
                    curve: function (t, s) { return xAt(t, s); },
                    marker: function (s, a, d) { return { x: d.t, y: d.x }; }
                }
            },
            extras: function (st, d, T) {
                var tStop = st.a !== 0 ? -st.v0 / st.a : null;
                return '<b>v₀</b> ' + st.v0 + ' м/с &nbsp;·&nbsp; <b>a</b> ' + st.a + ' м/с²' +
                    (tStop && tStop > 0 ? ' &nbsp;·&nbsp; <b>' + T('stopAt') + '</b> ' + tStop.toFixed(1) + ' с' : '') +
                    ' &nbsp;·&nbsp; <b>' + T('pathAt') + '</b> ' + xAt(TMAX, st).toFixed(1) + ' м';
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 5. ВТОРОЙ ЗАКОН НЬЮТОНА — тележка, приложенная сила, трение, масса
    // ═══════════════════════════════════════════════════════════════
    // Дидактическая цель: показать, что до преодоления трения покоя тело СТОИТ, несмотря на силу,
    // а после — разгоняется тем медленнее, чем больше масса. F = ma «на ощупь».
    function newtonModel(data) {
        var K = data.constants || {}, G = K.g || 10, TMAX = K.tmax || 6;
        function friction(st) { return st.mu * st.m * G; }
        function netForce(st) {
            var fr = friction(st);
            if (st.F <= fr) return 0;                 // трение покоя держит — движения нет
            return st.F - fr;
        }
        function accel(st) { return netForce(st) / st.m; }

        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var tt = t % TMAX, a = accel(st);
                    return { t: tt, a: a, v: a * tt, x: a * tt * tt / 2, moving: a > 0 };
                },
                derive: function (st, a) {
                    return { t: a.t, a: a.a, v: a.v, x: a.x, moving: a.moving,
                             fr: friction(st), net: netForce(st) };
                },
                stage: {
                    height: 215,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var floor = H - 52, x0 = 40;
                        var travel = Math.max(1, accel(st) * TMAX * TMAX / 2);
                        var span = W - x0 - 150;
                        var bx = x0 + Math.min(span, d.x / travel * span);
                        // пол со штриховкой (шероховатость ∝ коэффициенту трения)
                        KIT.ground(g, 0, W, floor, {
                            color: col.soft, width: 2, step: 11, hatch: 7, hatchDy: 8,
                            alpha: Math.min(1, 0.25 + st.mu)
                        });
                        // тележка: размер растёт с массой — масса видна глазом
                        var bw = 34 + st.m * 1.6, bh = 22 + st.m * 0.8;
                        KIT.body(g, bx + bw / 2, floor - bh / 2 - 7, {
                            w: bw, h: bh, color: col.link,
                            label: st.m + ' кг', labelSize: 11, labelColor: col.text
                        });
                        g.fillStyle = col.soft;                       // колёса — деталь только этой сцены
                        g.beginPath(); g.arc(bx + 9, floor - 3.5, 5, 0, 6.2832); g.fill();
                        g.beginPath(); g.arc(bx + bw - 9, floor - 3.5, 5, 0, 6.2832); g.fill();
                        // стрелки сил: приложенная (синяя) и трение (красная, всегда против движения)
                        var midY = floor - bh / 2 - 7;
                        function force(fromX, val, dir, colr, label) {
                            if (val <= 0.01) return;
                            var len = Math.max(12, Math.min(95, val * 0.9));
                            KIT.arrow(g, fromX, midY, dir * len, 0, {
                                color: colr, width: 3, head: 8, headW: 5, shorten: 0, min: 0,
                                label: label, labelMid: true, labelDy: -9
                            });
                        }
                        force(bx + bw, st.F, 1, '#155E74', 'F = ' + st.F + ' Н');
                        force(bx, d.fr, -1, '#b31b1b', 'тр = ' + d.fr.toFixed(0) + ' Н');
                        // состояние
                        KIT.readout(g, [
                            { text: d.moving ? ('a = ' + d.a.toFixed(2) + ' м/с²') : 'тележка стоит: трение сильнее',
                              y: 20, size: 12, weight: '600', color: d.moving ? col.text : '#b31b1b' },
                            d.moving ? { text: 'v = ' + d.v.toFixed(1) + ' м/с   ·   t = ' + d.t.toFixed(1) + ' с',
                                         y: 36, size: 11, color: col.soft } : null
                        ]);
                    }
                },
                formula: function (st, d, T) {
                    if (!d.moving) {
                        return '<span class="xf-op">F = ' + st.F + ' Н ≤ F<sub>тр</sub> = μmg = ' + d.fr.toFixed(0) +
                            ' Н → </span><span class="xf-res">a = 0</span><br><i>' + T('stuck') + '</i>';
                    }
                    return '<span class="xf-op">a = (F − μmg) ∕ m = (' + st.F + ' − ' + d.fr.toFixed(0) + ') ∕ </span>' +
                        '<span class="xf-var">' + st.m + '</span><span class="xf-op"> = </span>' +
                        '<span class="xf-res">' + d.a.toFixed(2) + ' м/с²</span>';
                },
                plot: {
                    height: 165,
                    x: { label: 'xMass', min: 5, max: 50 },
                    y: { label: 'yAccel', min: 0,
                         max: function (s) { return Math.max(1, Math.ceil((s.F - s.mu * 5 * G) / 5)); } },
                    samples: 100,
                    // как ускорение падает с ростом массы при той же силе — гипербола a = (F−μmg)/m
                    curve: function (mass, s) {
                        var fr = s.mu * mass * G;
                        return s.F > fr ? (s.F - fr) / mass : 0;
                    },
                    marker: function (s, a, d) { return { x: s.m, y: d.a }; }
                }
            },
            extras: function (st, d, T) {
                var fr = friction(st), net = netForce(st);
                return '<b>F</b> ' + st.F + ' Н &nbsp;·&nbsp; <b>' + T('fricForce') + '</b> ' + fr.toFixed(0) + ' Н' +
                    ' &nbsp;·&nbsp; <b>' + T('netForce') + '</b> ' + net.toFixed(0) + ' Н' +
                    ' &nbsp;·&nbsp; <b>a</b> ' + accel(st).toFixed(2) + ' м/с²';
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 6. СОУДАРЕНИЕ — сохранение импульса всегда, энергии — только при упругом ударе
    // ═══════════════════════════════════════════════════════════════
    function collisionModel(data) {
        var K = data.constants || {}, TMAX = K.tmax || 7;
        var X1_0 = -6, X2_0 = 6;                       // стартовые позиции в мировых единицах
        var mode = 'elastic';

        // Радиус тела растёт с массой — и он ЖЕ участвует в расчёте момента касания,
        // иначе тела «сталкиваются» по таймеру, проходя сквозь друг друга или ударяясь на расстоянии.
        function radiusOf(m) { return (10 + m * 1.6) / 16; }   // px → мировые единицы (span/16)

        // Момент реального касания: расстояние между центрами равно сумме радиусов.
        // Если тела расходятся или слишком медленно сближаются — удара в пределах TMAX не будет.
        function hitTime(st) {
            var gap = (X2_0 - X1_0) - (radiusOf(st.m1) + radiusOf(st.m2));
            var closing = st.v1 - st.v2;               // скорость сближения
            if (closing <= 0.001) return null;         // не догонит
            var t = gap / closing;
            return (t >= 0 && t <= TMAX) ? t : null;
        }

        // Скорости после удара: упругий — обмен по классическим формулам, неупругий — общая скорость
        function after(st) {
            var m1 = st.m1, m2 = st.m2, v1 = st.v1, v2 = st.v2;
            if (mode === 'inelastic') {
                var u = (m1 * v1 + m2 * v2) / (m1 + m2);
                return { u1: u, u2: u };
            }
            return {
                u1: ((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2),
                u2: ((m2 - m1) * v2 + 2 * m1 * v1) / (m1 + m2)
            };
        }
        function pSum(st, u) { return u ? st.m1 * u.u1 + st.m2 * u.u2 : st.m1 * st.v1 + st.m2 * st.v2; }
        function eSum(st, u) {
            return u ? (st.m1 * u.u1 * u.u1 + st.m2 * u.u2 * u.u2) / 2
                     : (st.m1 * st.v1 * st.v1 + st.m2 * st.v2 * st.v2) / 2;
        }

        return {
            modes: ['elastic', 'inelastic'],
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var tt = t % TMAX, u = after(st), th = hitTime(st);
                    var hit = (th !== null && tt >= th);
                    // До касания тела летят со своими скоростями; после — расходятся с новыми,
                    // причём точка стыковки берётся из ФАКТИЧЕСКОГО момента встречи, а не по таймеру.
                    var x1 = hit ? (X1_0 + st.v1 * th) + u.u1 * (tt - th) : X1_0 + st.v1 * tt;
                    var x2 = hit ? (X2_0 + st.v2 * th) + u.u2 * (tt - th) : X2_0 + st.v2 * tt;
                    return { t: tt, hit: hit, tHit: th, x1: x1, x2: x2, u: u };
                },
                derive: function (st, a) {
                    return { t: a.t, hit: a.hit, tHit: a.tHit, x1: a.x1, x2: a.x2, u: a.u,
                             willHit: a.tHit !== null,
                             pBefore: pSum(st), pAfter: pSum(st, a.u),
                             eBefore: eSum(st), eAfter: eSum(st, a.u) };
                },
                stage: {
                    height: 200,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var y = H * 0.5, span = W - 60, cx = W / 2;
                        var SX = KIT.scale({ min: 0, max: 16, from: cx, to: cx + span });
                        KIT.axis(g, 20, W - 20, y + 26, { color: col.border });
                        // тела: радиус растёт с массой, чтобы масса читалась глазом
                        function ball(x, m, v, colr, label) {
                            var r = 10 + m * 1.6, px = SX(x);
                            KIT.body(g, px, y, { shape: 'ball', size: 2 * r, color: colr, fillAlpha: .2,
                                                 label: m + ' кг', labelSize: 11, labelColor: col.text });
                            if (Math.abs(v) > 0.05) {          // вектор скорости
                                var len = Math.max(-70, Math.min(70, v * 12));
                                KIT.arrow(g, px, y - r - 12, len, 0, {
                                    color: colr, width: 2.5, head: 7, headW: 4, shorten: 0, min: 0, cap: 'butt',
                                    label: v.toFixed(1), labelMid: true, labelDy: -6
                                });
                            }
                            KIT.text(g, label, px, y + r + 16, { color: col.soft });
                        }
                        var v1 = d.hit ? d.u.u1 : st.v1, v2 = d.hit ? d.u.u2 : st.v2;
                        ball(d.x1, st.m1, v1, '#155E74', 'A');
                        ball(d.x2, st.m2, v2, '#b31b1b', 'B');
                        // Вспышка — в точке РЕАЛЬНОЙ встречи (между центрами тел), а не в центре сцены
                        if (d.hit && d.tHit !== null && d.t < d.tHit + 0.35) {
                            KIT.flash(g, SX((d.x1 + d.x2) / 2), y, 34, {
                                color: col.accent, rays: 8, inner: 22, width: 2, cap: 'butt',
                                alpha: Math.max(0, 1 - (d.t - d.tHit) / 0.35)
                            });
                        }
                        KIT.readout(g, [
                            { text: ctx.T(!d.willHit ? 'noHit' : (d.hit ? 'afterHit' : 'beforeHit')),
                              y: 20, size: 11, weight: '', color: col.soft },
                            d.willHit ? { text: ctx.T('hitAt') + ' ' + d.tHit.toFixed(1) + ' c',
                                          y: 35, size: 10, color: col.soft } : null
                        ], { x: 14 });
                    }
                },
                formula: function (st, d, T) {
                    var lost = d.eBefore - d.eAfter;
                    return '<span class="xf-op">p = m₁v₁ + m₂v₂ = </span><span class="xf-res">' +
                        d.pBefore.toFixed(1) + '</span><span class="xf-op"> → ' + d.pAfter.toFixed(1) +
                        ' кг·м/с</span><br>' +
                        '<span class="xf-op">E = </span><span class="xf-var">' + d.eBefore.toFixed(1) +
                        '</span><span class="xf-op"> → ' + d.eAfter.toFixed(1) + ' Дж</span>' +
                        (lost > 0.05 ? '<br><i>' + T('lost') + ' ' + lost.toFixed(1) + ' Дж (' +
                            Math.round(100 * lost / d.eBefore) + '%)</i>' : '<br><i>' + T('kept') + '</i>');
                },
                plot: {
                    height: 160,
                    x: { label: 'xMass2', min: 1, max: 20 },
                    y: { label: 'ySpeed',
                         min: function (s) { return -Math.ceil(Math.abs(s.v1) + Math.abs(s.v2) + 1); },
                         max: function (s) { return Math.ceil(Math.abs(s.v1) + Math.abs(s.v2) + 1); } },
                    samples: 90,
                    // как меняется скорость первого тела после удара в зависимости от массы второго
                    curve: function (m2, s) {
                        if (mode === 'inelastic') return (s.m1 * s.v1 + m2 * s.v2) / (s.m1 + m2);
                        return ((s.m1 - m2) * s.v1 + 2 * m2 * s.v2) / (s.m1 + m2);
                    },
                    marker: function (s, a, d) { return { x: s.m2, y: d.u.u1 }; }
                }
            },
            extras: function (st, d, T) {
                var u = after(st), pb = pSum(st), pa = pSum(st, u), eb = eSum(st), ea = eSum(st, u);
                return '<b>' + T('pLabel') + '</b> ' + pb.toFixed(1) + ' → ' + pa.toFixed(1) +
                    ' кг·м/с &nbsp;·&nbsp; <b>' + T('eLabel') + '</b> ' + eb.toFixed(1) + ' → ' + ea.toFixed(1) + ' Дж' +
                    ' &nbsp;·&nbsp; <b>u₁</b> ' + u.u1.toFixed(2) + ' &nbsp;·&nbsp; <b>u₂</b> ' + u.u2.toFixed(2) + ' м/с';
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 7. ВРАЩЕНИЕ И СИСТЕМЫ ОТСЧЁТА — одна сцена глазами двух наблюдателей
    // ═══════════════════════════════════════════════════════════════
    // Слева: инерциальный наблюдатель видит движение по кругу и силу натяжения к центру.
    // Справа: наблюдатель НА диске видит покой и вынужден ввести центробежную силу инерции.
    // Внизу: проекция вращения на ось — уже синус, мостик к следующему параграфу.
    function rotationModel(data) {
        var mode = 'inertial';
        function omega(st) { return 2 * Math.PI / st.T; }
        function accel(st) { return omega(st) * omega(st) * st.R; }
        function force(st) { return st.m * accel(st); }

        return {
            modes: ['inertial', 'rotating'],
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var ph = omega(st) * t;
                    return { t: t, phase: ph, x: Math.cos(ph), y: Math.sin(ph) };
                },
                derive: function (st, a) {
                    return { phase: a.phase, x: a.x, y: a.y, t: a.t,
                             w: omega(st), a: accel(st), F: force(st), v: omega(st) * st.R };
                },
                stage: {
                    height: 250,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var cx = W * 0.30, cy = H * 0.46, rad = Math.min(H * 0.32, W * 0.22);
                        var rot = (mode === 'rotating');
                        // ── диск ──
                        g.strokeStyle = col.border; g.lineWidth = 1.5;
                        g.beginPath(); g.arc(cx, cy, rad, 0, 6.2832); g.stroke();
                        // спица диска: в инерциальной системе крутится, во вращающейся стоит
                        var spokeAng = rot ? 0 : d.phase;
                        KIT.dashed(g, [3, 3], function () {
                            g.strokeStyle = col.soft; g.lineWidth = 1;
                            g.beginPath(); g.moveTo(cx, cy);
                            g.lineTo(cx + Math.cos(spokeAng) * rad, cy + Math.sin(spokeAng) * rad);
                            g.stroke();
                        });
                        // тело
                        var bx = cx + Math.cos(spokeAng) * rad, by = cy + Math.sin(spokeAng) * rad;
                        // верёвка (реальная сила натяжения — есть в обеих системах)
                        KIT.polyline(g, [[cx, cy], [bx, by]], { color: '#8F6417', width: 2 });
                        KIT.body(g, bx, by, { shape: 'dot', size: 20, color: '#155E74' });
                        // векторы: подпись стоит на 1.25 длины от начала — чуть дальше острия
                        function vec(x1, y1, dx, dy, colr, label) {
                            var len = Math.hypot(dx, dy);
                            if (len < 2) return;
                            KIT.arrow(g, x1, y1, dx, dy, {
                                color: colr, width: 2.5, head: 8, headW: 4, shorten: 0, min: 2,
                                label: label, labelGap: len * 0.25, labelDy: 3
                            });
                        }
                        var toC = 34;   // длина вектора к центру
                        vec(bx, by, -Math.cos(spokeAng) * toC, -Math.sin(spokeAng) * toC, '#b31b1b', 'T');
                        if (rot) {
                            // центробежная сила инерции — только в системе диска
                            vec(bx, by, Math.cos(spokeAng) * toC, Math.sin(spokeAng) * toC, '#8F6417', 'Fцб');
                        } else {
                            // скорость по касательной — только в инерциальной
                            vec(bx, by, -Math.sin(spokeAng) * 40, Math.cos(spokeAng) * 40, '#4C6B4E', 'v');
                        }
                        // подпись режима
                        KIT.readout(g, [
                            { text: ctx.T(rot ? 'obsRot' : 'obsLab'), y: 18, size: 11, weight: '600', color: col.text },
                            { text: ctx.T(rot ? 'obsRotNote' : 'obsLabNote'), y: 33, size: 10, color: col.soft }
                        ]);

                        // ── справа: проекция на ось = синус ──
                        var px0 = W * 0.60, pw = W - px0 - 20, pcy = cy;
                        KIT.axis(g, px0, px0 + pw, pcy, { color: col.border });
                        KIT.curve(g, {
                            from: 0, to: 90, samples: 90, color: '#155E74', width: 2,
                            fn: function (i) {
                                return { x: px0 + pw * i / 90,
                                         y: pcy - Math.sin(d.phase - (1 - i / 90) * 6.2832) * rad * 0.8 };
                            }
                        });
                        // текущая точка синусоиды + связь с телом на диске
                        var curY = pcy - Math.sin(d.phase) * rad * 0.8;
                        KIT.dashed(g, [2, 3], function () {
                            g.strokeStyle = col.soft; g.lineWidth = 1;
                            g.beginPath(); g.moveTo(bx, by); g.lineTo(px0 + pw, curY); g.stroke();
                        });
                        KIT.body(g, px0 + pw, curY, { shape: 'dot', size: 10, color: '#8F6417' });
                        KIT.text(g, ctx.T('projection'), px0 + pw / 2, pcy + rad * 0.8 + 22, { color: col.soft });
                    }
                },
                formula: function (st, d, T) {
                    if (mode === 'rotating') {
                        return '<span class="xf-op">' + T('rotEq') + ': T − F<sub>цб</sub> = 0, &nbsp; F<sub>цб</sub> = mω²R = </span>' +
                            '<span class="xf-res">' + d.F.toFixed(0) + ' Н</span>' +
                            '<br><i>' + T('rotNote') + '</i>';
                    }
                    return '<span class="xf-op">a<sub>ц</sub> = ω²R = </span><span class="xf-var">' + d.w.toFixed(2) +
                        '</span><span class="xf-op">² · </span><span class="xf-var">' + st.R +
                        '</span><span class="xf-op"> = </span><span class="xf-res">' + d.a.toFixed(1) + ' м/с²</span>' +
                        '<span class="xf-op"> = ' + (d.a / 9.81).toFixed(1) + ' g</span>' +
                        '<br><i>' + T('labNote') + '</i>';
                },
                plot: {
                    height: 160,
                    x: { label: 'xPeriod', min: 1, max: 8 },
                    y: { label: 'yAccel2', min: 0, max: function (s) { return Math.ceil(4 * Math.PI * Math.PI * s.R / 1); } },
                    samples: 100,
                    // как ускорение растёт при уменьшении периода — квадратичная зависимость
                    curve: function (T_, s) { var w = 2 * Math.PI / T_; return w * w * s.R; },
                    marker: function (s, a, d) { return { x: s.T, y: d.a }; }
                }
            },
            extras: function (st, d, T) {
                var w = omega(st), a = accel(st);
                return '<b>ω</b> ' + w.toFixed(2) + ' рад/с &nbsp;·&nbsp; <b>v</b> ' + (w * st.R).toFixed(1) + ' м/с' +
                    ' &nbsp;·&nbsp; <b>a<sub>ц</sub></b> ' + a.toFixed(1) + ' м/с² (' + (a / 9.81).toFixed(1) + ' g)' +
                    ' &nbsp;·&nbsp; <b>F</b> ' + (st.m * a).toFixed(0) + ' Н';
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // 8. ГАРМОНИЧЕСКИЙ ОСЦИЛЛЯТОР — груз на пружине + колесо-фантом
    // ═══════════════════════════════════════════════════════════════
    // Дидактическое ядро: рядом с пружиной вращается «фантомное колесо» той же частоты;
    // горизонталь груза и проекция точки колеса связаны пунктиром и совпадают ВСЕГДА —
    // колебание есть проекция вращения, тождество видно глазами.
    function oscillatorModel(data) {
        function omega(st) { return Math.sqrt(st.k / st.m); }
        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var w = omega(st), x = st.A * Math.cos(w * t);
                    return { t: t, x: x, v: -st.A * w * Math.sin(w * t), phase: w * t };
                },
                derive: function (st, a) {
                    var w = omega(st);
                    return { x: a.x, v: a.v, phase: a.phase, w: w, T: 2 * Math.PI / w,
                             Ek: st.m * a.v * a.v / 2, Ep: st.k * a.x * a.x / 2, E: st.k * st.A * st.A / 2 };
                },
                stage: {
                    height: 250,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var midY = H * 0.42;
                        // масштаб: амплитуда в см → пиксели
                        var ampPx = Math.min(W * 0.16, 90) * (st.A / 10);
                        // ── слева: колесо-фантом ──
                        var wx = W * 0.20, wr = Math.max(14, ampPx);
                        g.strokeStyle = col.border; g.lineWidth = 1.5;
                        g.beginPath(); g.arc(wx, midY, wr, 0, 6.2832); g.stroke();
                        var px = wx + Math.cos(d.phase) * wr, py = midY - Math.sin(d.phase) * wr;
                        g.strokeStyle = col.soft; g.lineWidth = 1; g.setLineDash([3, 3]);
                        g.beginPath(); g.moveTo(wx, midY); g.lineTo(px, py); g.stroke(); g.setLineDash([]);
                        g.fillStyle = '#8F6417';
                        g.beginPath(); g.arc(px, py, 6, 0, 6.2832); g.fill();
                        g.fillStyle = col.soft; g.font = '10px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillText(ctx.T('wheel'), wx, midY + wr + 18);
                        // ── справа: пружина с грузом (горизонтальная) ──
                        var anchorX = W * 0.44, eqX = W * 0.66;
                        var bodyX = eqX + (d.x / 10) * Math.min(W * 0.16, 90);
                        // стена-крепление, пружина и груз — блоки из набора сцены
                        KIT.wall(g, anchorX, midY, 60, { color: col.soft });
                        KIT.spring(g, anchorX, bodyX - 14, midY, { coils: 8 });
                        var bw = 18 + st.m * 3;                       // размер груза ∝ массе
                        KIT.body(g, bodyX - 14 + bw / 2, midY, { size: bw, label: st.m + ' кг', labelColor: col.text });
                        // положение равновесия
                        KIT.marker(g, eqX, midY - 42, midY + 42, { color: col.border });
                        // ── связь: проекция точки колеса == координата груза ──
                        // проекция по x колеса → переносим на ось груза
                        var projX = eqX + Math.cos(d.phase) * Math.min(W * 0.16, 90) * (st.A / 10);
                        g.strokeStyle = '#8F6417'; g.lineWidth = 1; g.setLineDash([2, 3]);
                        g.beginPath(); g.moveTo(px, py); g.lineTo(px, midY + 62); g.lineTo(projX, midY + 62);
                        g.lineTo(projX, midY + bw / 2 + 6); g.stroke(); g.setLineDash([]);
                        g.fillStyle = '#8F6417'; g.font = '10px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillText(ctx.T('sameX'), (px + projX) / 2, midY + 76);
                        // энергии — две полоски
                        var eb = H - 26, ew = W * 0.4, ex0 = W * 0.30;
                        KIT.bar(g, ex0, eb, ew, 7, {
                            split: d.Ek / d.E, border: col.border, labelColor: col.soft,
                            labelLeft: ctx.T('kin'), labelRight: ctx.T('pot')
                        });
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">ω = √(k∕m) = √(</span><span class="xf-var">' + st.k +
                        '</span><span class="xf-op">∕</span><span class="xf-var">' + st.m +
                        '</span><span class="xf-op">) = </span><span class="xf-res">' + d.w.toFixed(2) + ' рад/с</span>' +
                        '<span class="xf-op"> · T = </span><span class="xf-res">' + d.T.toFixed(2) + ' с</span>' +
                        '<br><i>x = ' + st.A + '·cos(' + d.w.toFixed(2) + 't) = ' + d.x.toFixed(1) + ' см — ' + T('noAmp') + '</i>';
                },
                plot: {
                    height: 160,
                    x: { label: 'xTime2', min: 0, max: 12 },
                    y: { label: 'yX', min: -10, max: 10 },
                    samples: 140,
                    curve: function (t, s) { return s.A * Math.cos(Math.sqrt(s.k / s.m) * t); },
                    marker: function (s, a, d) { return { x: a.t % 12, y: d.x }; }
                }
            },
            extras: function (st, d, T) {
                var w = omega(st);
                return '<b>ω</b> ' + w.toFixed(2) + ' рад/с &nbsp;·&nbsp; <b>T</b> ' + (2 * Math.PI / w).toFixed(2) + ' с' +
                    ' &nbsp;·&nbsp; <b>f</b> ' + (w / 2 / Math.PI).toFixed(2) + ' Гц' +
                    ' &nbsp;·&nbsp; <b>E</b> ' + (st.k * st.A * st.A / 2 / 10000).toFixed(2) + ' Дж';
            }
        };
    }

    /* ── Резонанс: вынужденные колебания с затуханием ───────────────────────────
       Установившееся решение x = A(ω)·cos(ωt − φ). Всё, что нужно показать:
       амплитуда резко растёт, когда частота внешней силы подходит к собственной,
       и тем резче, чем меньше трение. Кривая на графике — амплитуда против частоты. */
    function resonanceModel(data) {
        function w0(st) { return Math.sqrt(st.k / st.m); }          // собственная частота
        function gamma(st) { return st.b / (2 * st.m); }            // коэффициент затухания
        // амплитуда установившихся колебаний при частоте силы wf
        function amp(st, wf) {
            var W0 = w0(st), g = gamma(st), F = st.F / st.m;
            var d1 = W0 * W0 - wf * wf, d2 = 2 * g * wf;
            return F / Math.sqrt(d1 * d1 + d2 * d2);
        }
        function phase(st, wf) {
            var W0 = w0(st), g = gamma(st);
            return Math.atan2(2 * g * wf, W0 * W0 - wf * wf);
        }
        // добротность: во сколько раз амплитуда на резонансе больше статического отклонения
        function Q(st) { var g = gamma(st); return g > 0 ? w0(st) / (2 * g) : 999; }

        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var wf = st.wf, A = amp(st, wf), ph = phase(st, wf);
                    return { t: t, x: A * Math.cos(wf * t - ph), A: A, drive: Math.cos(wf * t), phase: ph };
                },
                derive: function (st, a) {
                    var W0 = w0(st);
                    return { x: a.x, A: a.A, drive: a.drive, w0: W0, wf: st.wf, Q: Q(st),
                             ratio: st.wf / W0, gain: a.A / (st.F / st.k), phase: a.phase };
                },
                stage: {
                    height: 250,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var midY = H * 0.40;
                        var scale = Math.min(W * 0.14, 80);           // 1 условная единица амплитуды → px
                        var eqX = W * 0.60;
                        var bodyX = eqX + Math.max(-2.2, Math.min(2.2, d.x)) * scale;

                        // рука, качающая опору — источник вынуждающей силы
                        var handX = W * 0.18 + d.drive * 12;
                        KIT.wall(g, handX, midY, 64, { color: col.soft, hatchH: 60 });
                        KIT.text(g, ctx.T('driver'), handX, midY - 42, { color: KIT.palette.ochre });

                        // пружина от качающейся опоры к грузу
                        KIT.spring(g, handX, bodyX - 15, midY, { coils: 9 });

                        // демпфер — показываем трение отдельным элементом, оно здесь главный герой
                        var dx0 = bodyX + 22, dw = 26;
                        g.strokeStyle = col.soft; g.lineWidth = 1.4;
                        g.strokeRect(dx0, midY - 9, dw, 18);
                        g.fillStyle = col.soft; g.globalAlpha = Math.min(.5, st.b / 8);
                        g.fillRect(dx0, midY - 9, dw, 18); g.globalAlpha = 1;
                        g.beginPath(); g.moveTo(bodyX + 4, midY); g.lineTo(dx0, midY); g.stroke();
                        g.font = '10px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillStyle = col.soft; g.fillText(ctx.T('damper'), dx0 + dw / 2, midY + 26);

                        // груз
                        var bw = 20 + st.m * 3;
                        KIT.body(g, bodyX - 15 + bw / 2, midY, { size: bw });

                        // положение равновесия
                        KIT.marker(g, eqX, midY - 46, midY + 46, { color: col.border });

                        // размах: сколько раз груз шире статического отклонения
                        var swing = Math.min(2.2, d.A) * scale;
                        g.strokeStyle = '#8F6417'; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(eqX - swing, midY + 54); g.lineTo(eqX + swing, midY + 54); g.stroke();
                        g.beginPath(); g.moveTo(eqX - swing, midY + 50); g.lineTo(eqX - swing, midY + 58);
                        g.moveTo(eqX + swing, midY + 50); g.lineTo(eqX + swing, midY + 58); g.stroke();
                        g.fillStyle = '#8F6417'; g.textAlign = 'center';
                        g.fillText(ctx.T('gain') + ' ×' + d.gain.toFixed(1), eqX, midY + 70);

                        // предупреждение о разрушении, когда размах уходит за шкалу
                        if (d.A > 2.2) {
                            g.fillStyle = '#9B2C2C'; g.font = '600 11px Inter, sans-serif';
                            g.fillText(ctx.T('breaks'), eqX, midY - 60);
                        }
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">A(ω) = F∕m ∕ √((ω₀²−ω²)² + (2γω)²) &nbsp; ω₀ = </span>' +
                        '<span class="xf-res">' + d.w0.toFixed(2) + '</span><span class="xf-op"> рад/с · ω = </span>' +
                        '<span class="xf-var">' + st.wf.toFixed(2) + '</span>' +
                        '<span class="xf-op"> · усиление = </span><span class="xf-res">×' + d.gain.toFixed(2) + '</span>' +
                        '<br><i>' + T('qNote') + ' Q = ' + d.Q.toFixed(1) + '</i>';
                },
                plot: {
                    height: 170,
                    x: { label: 'xFreq', min: 0, max: 12 },
                    y: { label: 'yAmp', min: 0, max: 3 },
                    samples: 220,
                    // резонансная кривая: амплитуда как функция частоты вынуждающей силы
                    curve: function (wf, s) { return Math.min(3, amp(s, wf)); },
                    marker: function (s, a, d) { return { x: s.wf, y: Math.min(3, d.A) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>ω₀</b> ' + d.w0.toFixed(2) + ' рад/с &nbsp;·&nbsp; <b>ω∕ω₀</b> ' + d.ratio.toFixed(2) +
                    ' &nbsp;·&nbsp; <b>Q</b> ' + d.Q.toFixed(1) +
                    ' &nbsp;·&nbsp; <b>' + T('gain') + '</b> ×' + d.gain.toFixed(2);
            }
        };
    }

    /* ── Энтропия: N частиц в ящике с перегородкой ──────────────────────────────
       Все начинают слева. Каждая частица независимо блуждает, и распределение
       само сползает к половине — не потому, что это «закон», а потому что
       состояний с равным делением несравнимо больше. Показываем сразу три вещи:
       сами частицы, число слева во времени и логарифм числа микросостояний. */
    function entropyModel(data) {
        var LN2 = Math.LN2;
        // ln числа способов разложить N частиц так, чтобы слева оказалось n — через Стирлинга
        function lnW(N, n) {
            if (n <= 0 || n >= N) return 0;
            function lnFact(x) {                     // формула Стирлинга с поправкой
                return x * Math.log(x) - x + 0.5 * Math.log(2 * Math.PI * x);
            }
            return lnFact(N) - lnFact(n) - lnFact(N - n);
        }
        // равновесное значение и характерный размах флуктуаций
        function sigma(N) { return Math.sqrt(N) / 2; }

        // состояние живёт в замыкании — движок вызывает animate(t, state) без предыдущего кадра
        var sim = null;
        function ensure(N) {
            if (sim && sim.p.length === N) return;
            var p = [];
            for (var i = 0; i < N; i++) {                 // старт: все частицы в левой половине
                p.push({ x: 0.02 + Math.random() * 0.44, y: 0.06 + Math.random() * 0.88, side: 0 });
            }
            sim = { p: p, last: 0, hist: [] };
        }

        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    var N = Math.round(st.N);
                    ensure(N);
                    var dt = Math.min(0.05, Math.max(0, t - sim.last));
                    sim.last = t;
                    // скорость перемешивания задаётся ползунком: это не физика, а темп показа
                    var rate = st.rate * dt;
                    for (var i = 0; i < N; i++) {
                        var q = sim.p[i];
                        q.x += (Math.random() - 0.5) * rate;
                        q.y += (Math.random() - 0.5) * rate * 0.6;
                        if (q.x < 0.02) q.x = 0.02; if (q.x > 0.98) q.x = 0.98;
                        if (q.y < 0.04) q.y = 0.04; if (q.y > 0.96) q.y = 0.96;
                        q.side = q.x < 0.5 ? 0 : 1;
                    }
                    var left = 0;
                    for (var j = 0; j < N; j++) if (sim.p[j].side === 0) left++;
                    sim.hist.push({ t: t, left: left });
                    if (sim.hist.length > 400) sim.hist.shift();
                    return { t: t, sim: sim, left: left, N: N };
                },
                derive: function (st, a) {
                    var N = a.N, n = a.left;
                    var S = lnW(N, n);                       // энтропия в единицах k_B
                    var Smax = lnW(N, Math.round(N / 2));
                    return { left: n, right: N - n, N: N, S: S, Smax: Smax,
                             frac: n / N, sig: sigma(N),
                             bits: S / LN2,                  // та же величина в битах — мост к Шеннону
                             // вероятность вернуться к «все слева» относительно равновесия
                             lnReturn: -Smax };
                },
                stage: {
                    height: 260,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, d = ctx.derived, a = ctx.anim;
                        var bx = W * 0.06, bw = W * 0.56, by = 16, bh = H - 86;
                        // ящик и перегородка-отметка посередине
                        g.strokeStyle = col.border; g.lineWidth = 1.5;
                        g.strokeRect(bx, by, bw, bh);
                        g.setLineDash([3, 4]); g.strokeStyle = col.soft;
                        g.beginPath(); g.moveTo(bx + bw / 2, by); g.lineTo(bx + bw / 2, by + bh); g.stroke();
                        g.setLineDash([]);
                        // частицы: цвет по стороне, чтобы перемешивание было видно
                        if (a && a.sim) {
                            for (var i = 0; i < a.sim.p.length; i++) {
                                var q = a.sim.p[i];
                                g.fillStyle = q.side === 0 ? '#155E74' : '#8F6417';
                                g.globalAlpha = .75;
                                g.beginPath();
                                g.arc(bx + q.x * bw, by + q.y * bh, 2.6, 0, 6.2832);
                                g.fill();
                            }
                            g.globalAlpha = 1;
                        }
                        // счётчики под ящиком
                        g.font = '600 12px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillStyle = '#155E74';
                        g.fillText(ctx.T('leftN') + ' ' + d.left, bx + bw * 0.25, by + bh + 20);
                        g.fillStyle = '#8F6417';
                        g.fillText(ctx.T('rightN') + ' ' + d.right, bx + bw * 0.75, by + bh + 20);

                        // справа — история числа слева, чтобы видеть сползание к половине
                        var gx = bx + bw + 22, gw = W - gx - 14, gy = by, gh = bh;
                        g.strokeStyle = col.border; g.lineWidth = 1;
                        g.strokeRect(gx, gy, gw, gh);
                        // линия равновесия N/2 и коридор флуктуаций ±σ
                        var yOf = function (v) { return gy + gh * (1 - v / d.N); };
                        g.fillStyle = col.soft; g.globalAlpha = .13;
                        g.fillRect(gx, yOf(d.N / 2 + d.sig), gw, yOf(d.N / 2 - d.sig) - yOf(d.N / 2 + d.sig));
                        g.globalAlpha = 1;
                        g.strokeStyle = col.soft; g.setLineDash([2, 3]);
                        g.beginPath(); g.moveTo(gx, yOf(d.N / 2)); g.lineTo(gx + gw, yOf(d.N / 2)); g.stroke();
                        g.setLineDash([]);
                        if (a && a.sim && a.sim.hist.length > 1) {
                            var hs = a.sim.hist, n0 = hs.length;
                            g.strokeStyle = '#155E74'; g.lineWidth = 1.4; g.beginPath();
                            for (var h = 0; h < n0; h++) {
                                var xx = gx + gw * h / Math.max(1, n0 - 1);
                                if (h === 0) g.moveTo(xx, yOf(hs[h].left)); else g.lineTo(xx, yOf(hs[h].left));
                            }
                            g.stroke();
                        }
                        g.fillStyle = col.soft; g.font = '10px Inter, sans-serif'; g.textAlign = 'left';
                        g.fillText(ctx.T('histLabel'), gx + 4, gy + 13);
                        g.textAlign = 'right';
                        g.fillText('N/2 ± √N/2', gx + gw - 4, yOf(d.N / 2) - 5);

                        // полоса энтропии внизу
                        var eb = H - 34, ew = W - 28, ex0 = 14;
                        g.strokeStyle = col.border; g.strokeRect(ex0, eb, ew, 9);
                        g.fillStyle = '#4C6B4E';
                        g.fillRect(ex0, eb, ew * Math.max(0, Math.min(1, d.S / (d.Smax || 1))), 9);
                        g.fillStyle = col.soft; g.font = '10px Inter, sans-serif'; g.textAlign = 'left';
                        g.fillText(ctx.T('entLabel') + ' S/k = ' + d.S.toFixed(1) +
                                   '  (max ' + d.Smax.toFixed(1) + ')', ex0, eb - 5);
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">S = k·ln W · слева </span><span class="xf-var">' + d.left +
                        '</span><span class="xf-op"> из </span><span class="xf-var">' + d.N +
                        '</span><span class="xf-op"> · S/k = </span><span class="xf-res">' + d.S.toFixed(2) + '</span>' +
                        '<span class="xf-op"> = </span><span class="xf-res">' + d.bits.toFixed(1) + '</span><span class="xf-op"> бит</span>' +
                        '<br><i>' + T('returnNote') + ' e^(−' + d.Smax.toFixed(1) + ')</i>';
                },
                plot: {
                    height: 165,
                    x: { label: 'xLeft', min: 0, max: 1 },
                    y: { label: 'yEnt', min: 0, max: 1 },
                    samples: 120,
                    // энтропия как функция доли частиц слева: колокол с максимумом на половине
                    curve: function (f, s) {
                        var N = Math.round(s.N), n = Math.round(f * N);
                        var mx = lnW(N, Math.round(N / 2));
                        return mx > 0 ? lnW(N, n) / mx : 0;
                    },
                    marker: function (s, a, d) { return { x: d.frac, y: d.Smax ? d.S / d.Smax : 0 }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>' + T('leftN') + '</b> ' + d.left + ' / ' + d.N +
                    ' &nbsp;·&nbsp; <b>S/k</b> ' + d.S.toFixed(2) +
                    ' &nbsp;·&nbsp; <b>' + T('bitsLabel') + '</b> ' + d.bits.toFixed(1) +
                    ' &nbsp;·&nbsp; <b>±√N/2</b> ' + d.sig.toFixed(1);
            }
        };
    }

    /* ── Орбита: тело в поле тяготения точечной массы ───────────────────────────
       Считаем честно, скоростным Верле: круг, эллипс, парабола и гипербола
       получаются сами, из одной и той же силы — меняется только начальная
       скорость. Это и есть содержание темы: Кеплер не постулируется, а выходит. */
    function orbitModel(data) {
        var R0 = 1.0;                       // старт всегда на этом расстоянии, в условных единицах
        function mu(st) { return st.M; }    // гравитационный параметр GM в тех же единицах

        var sim = null;
        function reset(st) {
            sim = { x: R0, y: 0, vx: 0, vy: st.v0, t: 0, last: 0,
                    trail: [], rmin: R0, rmax: R0, escaped: false, turns: 0, lastAng: 0 };
        }
        function ensure(st) { if (!sim) reset(st); }

        function step(st, dt) {
            var m = mu(st);
            function acc(x, y) {
                var r2 = x * x + y * y, r = Math.sqrt(r2);
                var f = -m / (r2 * r);      // -GM/r³ · вектор
                return { ax: f * x, ay: f * y };
            }
            var a1 = acc(sim.x, sim.y);
            sim.x += sim.vx * dt + 0.5 * a1.ax * dt * dt;
            sim.y += sim.vy * dt + 0.5 * a1.ay * dt * dt;
            var a2 = acc(sim.x, sim.y);
            sim.vx += 0.5 * (a1.ax + a2.ax) * dt;
            sim.vy += 0.5 * (a1.ay + a2.ay) * dt;
            var r = Math.sqrt(sim.x * sim.x + sim.y * sim.y);
            if (r < sim.rmin) sim.rmin = r;
            if (r > sim.rmax && r < 40) sim.rmax = r;
            if (r > 40) sim.escaped = true;
            // считаем обороты по пересечению начального луча
            var ang = Math.atan2(sim.y, sim.x);
            if (sim.lastAng < 0 && ang >= 0 && r < 40) sim.turns++;
            sim.lastAng = ang;
        }

        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    ensure(st);
                    // при смене параметров начинаем заново — иначе орбита не отвечает ползункам
                    if (sim.M !== st.M || sim.v0 !== st.v0) { reset(st); sim.M = st.M; sim.v0 = st.v0; }
                    var dt = Math.min(0.05, Math.max(0, t - sim.last)); sim.last = t;
                    var n = 40, h = dt / n;                       // мелкий шаг: орбита должна не разъезжаться
                    for (var i = 0; i < n && !sim.escaped; i++) { step(st, h); sim.t += h; }
                    sim.trail.push({ x: sim.x, y: sim.y });
                    if (sim.trail.length > 900) sim.trail.shift();
                    return { t: t, sim: sim };
                },
                derive: function (st, a) {
                    var s = a.sim, m = mu(st);
                    var r = Math.sqrt(s.x * s.x + s.y * s.y);
                    var v = Math.sqrt(s.vx * s.vx + s.vy * s.vy);
                    var Ek = v * v / 2, Ep = -m / r, E = Ek + Ep;
                    var L = s.x * s.vy - s.y * s.vx;              // момент импульса на единицу массы
                    var vCirc = Math.sqrt(m / R0), vEsc = Math.sqrt(2 * m / R0);
                    var aMaj = E < 0 ? -m / (2 * E) : Infinity;   // большая полуось
                    var ecc = Math.sqrt(Math.max(0, 1 + 2 * E * L * L / (m * m)));
                    return { r: r, v: v, Ek: Ek, Ep: Ep, E: E, L: L, a: aMaj, e: ecc,
                             vCirc: vCirc, vEsc: vEsc, escaped: s.escaped,
                             rmin: s.rmin, rmax: s.rmax, turns: s.turns,
                             T: isFinite(aMaj) ? 2 * Math.PI * Math.sqrt(aMaj * aMaj * aMaj / m) : Infinity };
                },
                stage: {
                    height: 280,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, d = ctx.derived, a = ctx.anim;
                        var cx = W * 0.44, cy = H * 0.5;
                        var scale = Math.min(W, H) * 0.16;         // 1 условная единица длины → px

                        // след орбиты
                        if (a && a.sim && a.sim.trail.length > 1) {
                            g.strokeStyle = col.soft; g.lineWidth = 1; g.globalAlpha = .55;
                            g.beginPath();
                            a.sim.trail.forEach(function (p, i) {
                                var px = cx + p.x * scale, py = cy - p.y * scale;
                                if (i === 0) g.moveTo(px, py); else g.lineTo(px, py);
                            });
                            g.stroke(); g.globalAlpha = 1;
                        }
                        // центральное тело
                        var cr = 7 + Math.sqrt(ctx.state.M) * 4;
                        g.fillStyle = '#8F6417'; g.beginPath(); g.arc(cx, cy, cr, 0, 6.2832); g.fill();
                        // окружность старта — для сравнения с круговой орбитой
                        g.strokeStyle = col.border; g.setLineDash([2, 4]); g.lineWidth = 1;
                        g.beginPath(); g.arc(cx, cy, scale, 0, 6.2832); g.stroke(); g.setLineDash([]);

                        // тело
                        if (a && a.sim) {
                            var bx = cx + a.sim.x * scale, by = cy - a.sim.y * scale;
                            if (Math.abs(bx - cx) < W && Math.abs(by - cy) < H) {
                                g.fillStyle = '#155E74';
                                g.beginPath(); g.arc(bx, by, 5, 0, 6.2832); g.fill();
                                // вектор скорости
                                g.strokeStyle = '#155E74'; g.lineWidth = 1.6;
                                var k = 16 / Math.max(0.2, d.vCirc);
                                g.beginPath(); g.moveTo(bx, by);
                                g.lineTo(bx + a.sim.vx * k, by - a.sim.vy * k); g.stroke();
                            }
                        }

                        // подпись режима орбиты — главное, что должен увидеть читатель
                        var kind = d.escaped ? ctx.T('kindEscape')
                                 : (d.e < 0.03 ? ctx.T('kindCircle')
                                 : (d.e < 1 ? ctx.T('kindEllipse') : ctx.T('kindHyper')));
                        g.font = '600 12px Inter, sans-serif'; g.textAlign = 'left';
                        g.fillStyle = d.escaped ? '#9B2C2C' : '#155E74';
                        g.fillText(kind, 12, 20);
                        g.fillStyle = col.soft; g.font = '10.5px Inter, sans-serif';
                        g.fillText(ctx.T('eLabel') + ' e = ' + (isFinite(d.e) ? d.e.toFixed(2) : '—'), 12, 36);
                        g.fillText(ctx.T('vCircLabel') + ' ' + d.vCirc.toFixed(2) +
                                   ' · ' + ctx.T('vEscLabel') + ' ' + d.vEsc.toFixed(2), 12, 50);

                        // столбики энергии: кинетическая, потенциальная, полная
                        var bw2 = 13, bx0 = W - 96, base = H - 28, hmax = H * 0.30;
                        var scaleE = hmax / Math.max(0.6, Math.abs(d.Ep));
                        function bar(i, val, color, lab) {
                            var xx = bx0 + i * 30, hh = Math.max(1, Math.abs(val) * scaleE);
                            g.fillStyle = color; g.globalAlpha = .8;
                            if (val >= 0) g.fillRect(xx, base - hh, bw2, hh);
                            else g.fillRect(xx, base, bw2, hh);
                            g.globalAlpha = 1;
                            g.fillStyle = col.soft; g.font = '9.5px Inter, sans-serif'; g.textAlign = 'center';
                            g.fillText(lab, xx + bw2 / 2, base + 26);
                        }
                        g.strokeStyle = col.border; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(bx0 - 8, base); g.lineTo(W - 10, base); g.stroke();
                        bar(0, d.Ek, '#4C6B4E', 'Eк');
                        bar(1, d.Ep, '#8F6417', 'Eп');
                        bar(2, d.E, '#155E74', 'E');
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">E = v²∕2 − GM∕r = </span><span class="xf-res">' + d.E.toFixed(3) +
                        '</span><span class="xf-op"> · L = </span><span class="xf-res">' + d.L.toFixed(3) + '</span>' +
                        '<span class="xf-op"> · e = </span><span class="xf-res">' + (isFinite(d.e) ? d.e.toFixed(3) : '∞') + '</span>' +
                        '<br><i>' + (d.E < 0 ? T('boundNote') + ' T = ' + d.T.toFixed(2) : T('freeNote')) + '</i>';
                },
                plot: {
                    height: 170,
                    x: { label: 'xR', min: 0.2, max: 6 },
                    y: { label: 'yV', min: 0, max: 3 },
                    samples: 200,
                    // скорость как функция расстояния — прямо из сохранения энергии
                    curve: function (r, s) {
                        var E = s.v0 * s.v0 / 2 - s.M / R0;
                        var v2 = 2 * (E + s.M / r);
                        return v2 > 0 ? Math.min(3, Math.sqrt(v2)) : null;   // null — сюда тело не долетит
                    },
                    marker: function (s, a, d) { return { x: Math.min(6, d.r), y: Math.min(3, d.v) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>r</b> ' + d.r.toFixed(2) + ' &nbsp;·&nbsp; <b>v</b> ' + d.v.toFixed(2) +
                    ' &nbsp;·&nbsp; <b>e</b> ' + (isFinite(d.e) ? d.e.toFixed(2) : '∞') +
                    ' &nbsp;·&nbsp; <b>' + T('periLabel') + '</b> ' + d.rmin.toFixed(2) +
                    ' / ' + (d.escaped ? '∞' : d.rmax.toFixed(2)) +
                    ' &nbsp;·&nbsp; <b>' + T('turnsLabel') + '</b> ' + d.turns;
            }
        };
    }

    /* ── Волна: бегущая, стоячая, интерференция ─────────────────────────────────
       Три режима одной формулы. Бегущая — профиль едет; стоячая — сумма двух
       встречных, узлы стоят на месте; интерференция — две волны с разными
       частотами дают биения. Везде одна и та же y = A·sin(kx − ωt). */
    function waveModel(data) {
        var mode = 'run';
        function k(st) { return 2 * Math.PI / st.lam; }
        function w(st) { return 2 * Math.PI * st.v / st.lam; }
        // профиль волны в точке x в момент t — то, что рисуется и на сцене, и на графике
        function yAt(x, t, st) {
            var K = k(st), W = w(st);
            if (mode === 'stand') return 2 * st.A * Math.sin(K * x) * Math.cos(W * t);
            if (mode === 'two') {
                var K2 = K * st.ratio, W2 = W * st.ratio;
                return st.A * Math.sin(K * x - W * t) + st.A * Math.sin(K2 * x - W2 * t);
            }
            return st.A * Math.sin(K * x - W * t);
        }
        return {
            modes: ['run', 'stand', 'two'],
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) { return { t: t, probe: yAt(st.xprobe, t, st) }; },
                derive: function (st, a) {
                    var T = st.lam / st.v;
                    return { T: T, f: 1 / T, k: k(st), w: w(st), probe: a.probe,
                             mode: mode, nodes: st.lam / 2 };
                },
                stage: {
                    height: 250,
                    draw: function (g, ctx) {
                        var W2 = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived, a = ctx.anim;
                        var midY = H * 0.42, L = 10;                  // показываем 10 условных метров
                        var px = function (x) { return 20 + x / L * (W2 - 40); };
                        var py = function (y) { return midY - y * 18; };

                        // ось
                        g.strokeStyle = col.border; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(px(0), midY); g.lineTo(px(L), midY); g.stroke();

                        // для стоячей волны — призрак второй огибающей
                        if (mode === 'stand') {
                            g.strokeStyle = col.soft; g.globalAlpha = .35; g.setLineDash([3, 4]);
                            [1, -1].forEach(function (s) {
                                g.beginPath();
                                for (var x = 0; x <= L; x += 0.02) {
                                    var y = s * 2 * st.A * Math.sin(k(st) * x);
                                    if (x === 0) g.moveTo(px(x), py(y)); else g.lineTo(px(x), py(y));
                                }
                                g.stroke();
                            });
                            g.setLineDash([]); g.globalAlpha = 1;
                            // узлы — точки, которые не двигаются никогда
                            g.fillStyle = '#9B2C2C';
                            for (var n = 0; n * st.lam / 2 <= L; n++) {
                                g.beginPath(); g.arc(px(n * st.lam / 2), midY, 3, 0, 6.2832); g.fill();
                            }
                        }

                        // сама волна
                        g.strokeStyle = '#155E74'; g.lineWidth = 2; g.beginPath();
                        for (var x2 = 0; x2 <= L; x2 += 0.02) {
                            var yy = yAt(x2, a.t, st);
                            if (x2 === 0) g.moveTo(px(x2), py(yy)); else g.lineTo(px(x2), py(yy));
                        }
                        g.stroke();

                        // пробная частица: она колеблется поперёк и никуда не едет
                        var yp = yAt(st.xprobe, a.t, st);
                        g.fillStyle = '#8F6417';
                        g.beginPath(); g.arc(px(st.xprobe), py(yp), 5, 0, 6.2832); g.fill();
                        g.strokeStyle = '#8F6417'; g.setLineDash([2, 3]); g.lineWidth = 1;
                        g.beginPath(); g.moveTo(px(st.xprobe), midY - 40); g.lineTo(px(st.xprobe), midY + 40); g.stroke();
                        g.setLineDash([]);
                        g.fillStyle = col.soft; g.font = '10px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillText(ctx.T('probeNote'), px(st.xprobe), midY + 58);

                        // длина волны стрелкой — главное, что надо увидеть глазами.
                        // Держим её у нижнего края: наверху уже стоит подпись режима.
                        if (mode !== 'two') {
                            var y0 = H - 26;
                            g.strokeStyle = '#4C6B4E'; g.lineWidth = 1.4;
                            g.beginPath(); g.moveTo(px(0.5), y0); g.lineTo(px(0.5 + st.lam), y0); g.stroke();
                            [0.5, 0.5 + st.lam].forEach(function (xx) {
                                g.beginPath(); g.moveTo(px(xx), y0 - 5); g.lineTo(px(xx), y0 + 5); g.stroke();
                            });
                            g.fillStyle = '#4C6B4E'; g.textAlign = 'center';
                            g.fillText('λ = ' + st.lam.toFixed(1) + ' м', px(0.5 + st.lam / 2), y0 - 9);
                        }

                        // подпись режима
                        g.font = '600 12px Inter, sans-serif'; g.textAlign = 'left'; g.fillStyle = '#155E74';
                        g.fillText(ctx.T('mode_' + mode), 20, 20);
                        g.font = '10.5px Inter, sans-serif'; g.fillStyle = col.soft;
                        g.fillText(ctx.T('periodNote') + ' T = ' + d.T.toFixed(2) + ' с · f = ' + d.f.toFixed(2) + ' Гц', 20, 36);
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">v = λf = </span><span class="xf-var">' + st.lam.toFixed(1) +
                        '</span><span class="xf-op"> · </span><span class="xf-var">' + d.f.toFixed(2) +
                        '</span><span class="xf-op"> = </span><span class="xf-res">' + st.v.toFixed(1) + ' м/с</span>' +
                        '<br><i>k = 2π∕λ = ' + d.k.toFixed(2) + ' рад/м · ω = 2πf = ' + d.w.toFixed(2) + ' рад/с</i>';
                },
                plot: {
                    height: 160,
                    x: { label: 'xTimeW', min: 0, max: 8 },
                    y: { label: 'yDisp', min: -3, max: 3 },
                    samples: 200,
                    // колебание одной точки во времени: период виден, длина волны — нет
                    curve: function (t, s) { return yAt(s.xprobe, t, s); },
                    marker: function (s, a, d) { return { x: a.t % 8, y: d.probe }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>T</b> ' + d.T.toFixed(2) + ' с &nbsp;·&nbsp; <b>f</b> ' + d.f.toFixed(2) + ' Гц' +
                    ' &nbsp;·&nbsp; <b>k</b> ' + d.k.toFixed(2) + ' рад/м' +
                    (mode === 'stand' ? ' &nbsp;·&nbsp; <b>' + T('nodeLabel') + '</b> ' + d.nodes.toFixed(2) + ' м' : '');
            }
        };
    }

    /* ── Электростатика: два заряда, поле и потенциал ───────────────────────────
       Показываем поле стрелками на сетке, пробный заряд на оси и график E(x).
       Главное, что должно быть видно: между разноимённых поле складывается,
       между одноимённых есть точка, где оно ровно ноль. */
    function chargeModel(data) {
        var Ke = 1;                                   // в условных единицах
        function positions(st) { return { x1: -st.d / 2, x2: st.d / 2 }; }
        // поле в точке (x,y) от двух точечных зарядов
        function fieldAt(x, y, st) {
            var p = positions(st), ex = 0, ey = 0;
            [[p.x1, st.q1], [p.x2, st.q2]].forEach(function (c) {
                var dx = x - c[0], dy = y, r2 = dx * dx + dy * dy;
                if (r2 < 0.02) return;                // не рисуем внутри самого заряда
                var r = Math.sqrt(r2), e = Ke * c[1] / r2;
                ex += e * dx / r; ey += e * dy / r;
            });
            return { ex: ex, ey: ey, mag: Math.sqrt(ex * ex + ey * ey) };
        }
        function potAt(x, y, st) {
            var p = positions(st), v = 0;
            [[p.x1, st.q1], [p.x2, st.q2]].forEach(function (c) {
                var dx = x - c[0], r = Math.sqrt(dx * dx + y * y);
                if (r > 0.14) v += Ke * c[1] / r;
            });
            return v;
        }
        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) { return { t: t }; },
                derive: function (st) {
                    var f = fieldAt(st.xt, 0, st);
                    var p = positions(st);
                    // точка, где поле обращается в ноль (есть только у одноимённых зарядов)
                    var zero = null;
                    if (st.q1 * st.q2 > 0) {
                        // расстояния до зарядов относятся как корни из их величин
                        var s = Math.sqrt(Math.abs(st.q2 / st.q1));
                        zero = st.d / (1 + s) + p.x1;
                    }
                    return { E: f.ex, Emag: f.mag, V: potAt(st.xt, 0, st),
                             x1: p.x1, x2: p.x2, zero: zero,
                             same: st.q1 * st.q2 > 0 };
                },
                stage: {
                    height: 270,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var cx = W / 2, cy = H * 0.46, sc = Math.min(W / 9, 46);   // 1 усл. ед. → px
                        var PX = function (x) { return cx + x * sc; };
                        var PY = function (y) { return cy - y * sc; };

                        // сетка стрелок поля — картина силовых линий без самих линий
                        for (var gx = -4; gx <= 4; gx += 0.8) {
                            for (var gy = -1.6; gy <= 1.6; gy += 0.8) {
                                var f = fieldAt(gx, gy, st);
                                if (!f.mag || f.mag > 60) continue;
                                var len = Math.min(16, 5 + 9 * Math.log10(1 + f.mag));
                                var ux = f.ex / f.mag, uy = f.ey / f.mag;
                                var x0 = PX(gx), y0 = PY(gy);
                                g.strokeStyle = col.soft; g.globalAlpha = .55; g.lineWidth = 1;
                                g.beginPath(); g.moveTo(x0, y0); g.lineTo(x0 + ux * len, y0 - uy * len); g.stroke();
                                // наконечник
                                g.beginPath();
                                g.moveTo(x0 + ux * len, y0 - uy * len);
                                g.lineTo(x0 + ux * len - ux * 4 - uy * 2.5, y0 - uy * len + uy * 4 - ux * 2.5);
                                g.moveTo(x0 + ux * len, y0 - uy * len);
                                g.lineTo(x0 + ux * len - ux * 4 + uy * 2.5, y0 - uy * len + uy * 4 + ux * 2.5);
                                g.stroke(); g.globalAlpha = 1;
                            }
                        }

                        // ось
                        g.strokeStyle = col.border; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(PX(-4.4), cy); g.lineTo(PX(4.4), cy); g.stroke();

                        // сами заряды: цвет по знаку, размер по величине
                        [[d.x1, st.q1], [d.x2, st.q2]].forEach(function (c) {
                            var r = 8 + Math.abs(c[1]) * 2.2;
                            g.fillStyle = c[1] >= 0 ? '#9B2C2C' : '#155E74';
                            g.beginPath(); g.arc(PX(c[0]), cy, r, 0, 6.2832); g.fill();
                            g.fillStyle = '#fff'; g.font = '600 12px Inter, sans-serif';
                            g.textAlign = 'center'; g.textBaseline = 'middle';
                            g.fillText(c[1] > 0 ? '+' : (c[1] < 0 ? '−' : '0'), PX(c[0]), cy);
                            g.textBaseline = 'alphabetic';
                            g.fillStyle = col.soft; g.font = '10.5px Inter, sans-serif';
                            g.fillText(c[1] + ' ' + ctx.T('unit_q'), PX(c[0]), cy + r + 14);
                        });

                        // точка нулевого поля — только для одноимённых
                        if (d.zero !== null && Math.abs(d.zero) < 4.3) {
                            g.strokeStyle = '#4C6B4E'; g.setLineDash([3, 3]); g.lineWidth = 1.4;
                            g.beginPath(); g.moveTo(PX(d.zero), cy - 34); g.lineTo(PX(d.zero), cy + 34); g.stroke();
                            g.setLineDash([]);
                            g.fillStyle = '#4C6B4E'; g.font = '10.5px Inter, sans-serif'; g.textAlign = 'center';
                            g.fillText(ctx.T('zeroNote'), PX(d.zero), cy - 40);
                        }

                        // пробный заряд и сила на него
                        var tx = PX(st.xt);
                        g.fillStyle = '#8F6417';
                        g.beginPath(); g.arc(tx, cy, 5, 0, 6.2832); g.fill();
                        var scaleF = 26 / Math.max(0.4, Math.abs(d.E));
                        var arrow = Math.max(-70, Math.min(70, d.E * scaleF));
                        g.strokeStyle = '#8F6417'; g.lineWidth = 2;
                        g.beginPath(); g.moveTo(tx, cy - 22); g.lineTo(tx + arrow, cy - 22); g.stroke();
                        g.beginPath();
                        g.moveTo(tx + arrow, cy - 22);
                        g.lineTo(tx + arrow - Math.sign(arrow) * 6, cy - 26);
                        g.moveTo(tx + arrow, cy - 22);
                        g.lineTo(tx + arrow - Math.sign(arrow) * 6, cy - 18);
                        g.stroke();
                        g.fillStyle = '#8F6417'; g.font = '10.5px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillText(ctx.T('probeQ'), tx, cy + 22);

                        // читаемые значения в углу
                        g.textAlign = 'left'; g.font = '600 11.5px Inter, sans-serif'; g.fillStyle = '#155E74';
                        g.fillText(ctx.T(d.same ? 'kindSame' : 'kindOpp'), 12, 18);
                        g.font = '10.5px Inter, sans-serif'; g.fillStyle = col.soft;
                        g.fillText('E = ' + d.E.toFixed(2) + ' · φ = ' + d.V.toFixed(2), 12, 34);
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">E = k(q₁∕r₁² + q₂∕r₂²) = </span><span class="xf-res">' + d.E.toFixed(3) + '</span>' +
                        '<span class="xf-op"> · φ = k(q₁∕r₁ + q₂∕r₂) = </span><span class="xf-res">' + d.V.toFixed(3) + '</span>' +
                        '<br><i>' + (d.zero !== null ? T('zeroAt') + ' x = ' + d.zero.toFixed(2) : T('noZero')) + '</i>';
                },
                plot: {
                    height: 165,
                    x: { label: 'xAxis', min: -4, max: 4 },
                    y: { label: 'yField', min: -8, max: 8 },
                    samples: 240,
                    // проекция поля на ось: видно и обращение в ноль, и разрывы у зарядов
                    curve: function (x, s) {
                        var f = fieldAt(x, 0, s);
                        if (Math.abs(f.ex) > 8) return null;    // у самого заряда поле уходит в бесконечность
                        return f.ex;
                    },
                    marker: function (s, a, d) { return { x: s.xt, y: Math.max(-8, Math.min(8, d.E)) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>E</b> ' + d.E.toFixed(3) + ' &nbsp;·&nbsp; <b>φ</b> ' + d.V.toFixed(3) +
                    ' &nbsp;·&nbsp; <b>' + T('distLabel') + '</b> ' + st.d.toFixed(1) +
                    (d.zero !== null ? ' &nbsp;·&nbsp; <b>E = 0</b> ' + T('atLabel') + ' x = ' + d.zero.toFixed(2) : '');
            }
        };
    }

    /* ── Магнетизм: заряд в магнитном поле ──────────────────────────────────────
       Сила Лоренца перпендикулярна скорости, поэтому работы не совершает —
       она только заворачивает. Отсюда окружность, радиус которой зависит от
       импульса, а период не зависит от скорости вовсе (циклотрон). */
    function magnetModel(data) {
        var mode = 'circle';
        var sim = null;
        function reset(st) {
            sim = { x: -1.8, y: 0, vx: st.v, vy: 0, last: 0, trail: [] };
        }
        function ensure(st) { if (!sim) reset(st); }
        function step(st, dt) {
            // dv/dt = (q/m)(E + v×B); поле B — вдоль оси z, E — вдоль y
            var qm = st.q;                       // отношение заряда к массе в условных единицах
            var ax = qm * (st.vy0 * 0 + sim.vy * st.B);
            var ay = qm * (st.E - sim.vx * st.B);
            sim.vx += ax * dt; sim.vy += ay * dt;
            sim.x += sim.vx * dt; sim.y += sim.vy * dt;
        }
        return {
            modes: ['circle', 'drift'],
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; reset({ v: 1 }); },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) {
                    ensure(st);
                    if (sim.B !== st.B || sim.v !== st.v || sim.q !== st.q || sim.E !== st.E) {
                        reset(st); sim.B = st.B; sim.v = st.v; sim.q = st.q; sim.E = st.E;
                    }
                    var dt = Math.min(0.05, Math.max(0, t - sim.last)); sim.last = t;
                    var n = 30, h = dt / n;
                    for (var i = 0; i < n; i++) step(st, h);
                    // не даём улететь за пределы сцены — заворачиваем обратно
                    if (Math.abs(sim.x) > 6 || Math.abs(sim.y) > 4) reset(st);
                    sim.trail.push({ x: sim.x, y: sim.y });
                    if (sim.trail.length > 700) sim.trail.shift();
                    return { t: t, sim: sim };
                },
                derive: function (st, a) {
                    var s = a.sim, v = Math.sqrt(s.vx * s.vx + s.vy * s.vy);
                    var R = st.B !== 0 ? Math.abs(st.v / (st.q * st.B)) : Infinity;
                    var T = st.B !== 0 ? 2 * Math.PI / Math.abs(st.q * st.B) : Infinity;
                    return { v: v, R: R, T: T, x: s.x, y: s.y,
                             F: Math.abs(st.q * v * st.B),
                             drift: st.B !== 0 ? st.E / st.B : 0,
                             mode: mode };
                },
                stage: {
                    height: 270,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived, a = ctx.anim;
                        var cx = W * 0.5, cy = H * 0.48, sc = Math.min(W / 13, 40);
                        var PX = function (x) { return cx + x * sc; };
                        var PY = function (y) { return cy - y * sc; };

                        // поле B «из плоскости» — сетка точек в кружках, стандартное обозначение
                        g.strokeStyle = col.soft; g.globalAlpha = .45; g.lineWidth = 1;
                        for (var gx = -5.5; gx <= 5.5; gx += 1.1) {
                            for (var gy = -3; gy <= 3; gy += 1.1) {
                                g.beginPath(); g.arc(PX(gx), PY(gy), 4, 0, 6.2832); g.stroke();
                                g.beginPath(); g.arc(PX(gx), PY(gy), 1.2, 0, 6.2832); g.fillStyle = col.soft; g.fill();
                            }
                        }
                        g.globalAlpha = 1;

                        // след частицы
                        if (a && a.sim && a.sim.trail.length > 1) {
                            g.strokeStyle = '#155E74'; g.lineWidth = 1.6; g.globalAlpha = .75; g.beginPath();
                            a.sim.trail.forEach(function (p, i) {
                                if (i === 0) g.moveTo(PX(p.x), PY(p.y)); else g.lineTo(PX(p.x), PY(p.y));
                            });
                            g.stroke(); g.globalAlpha = 1;
                        }
                        // частица и векторы
                        if (a && a.sim) {
                            var bx = PX(a.sim.x), by = PY(a.sim.y);
                            g.fillStyle = st.q >= 0 ? '#9B2C2C' : '#155E74';
                            g.beginPath(); g.arc(bx, by, 6, 0, 6.2832); g.fill();
                            // скорость
                            var vv = Math.sqrt(a.sim.vx * a.sim.vx + a.sim.vy * a.sim.vy) || 1;
                            g.strokeStyle = '#4C6B4E'; g.lineWidth = 2;
                            g.beginPath(); g.moveTo(bx, by);
                            g.lineTo(bx + a.sim.vx / vv * 30, by - a.sim.vy / vv * 30); g.stroke();
                            // сила Лоренца — всегда поперёк скорости
                            var fx = st.q * a.sim.vy * st.B, fy = -st.q * a.sim.vx * st.B;
                            var ff = Math.sqrt(fx * fx + fy * fy) || 1;
                            g.strokeStyle = '#8F6417'; g.lineWidth = 2;
                            g.beginPath(); g.moveTo(bx, by);
                            g.lineTo(bx + fx / ff * 24, by - fy / ff * 24); g.stroke();
                            g.fillStyle = '#4C6B4E'; g.font = '10px Inter, sans-serif'; g.textAlign = 'center';
                            g.fillText('v', bx + a.sim.vx / vv * 38, by - a.sim.vy / vv * 38);
                            g.fillStyle = '#8F6417';
                            g.fillText('F', bx + fx / ff * 32, by - fy / ff * 32);
                        }

                        // подписи
                        g.textAlign = 'left'; g.font = '600 11.5px Inter, sans-serif'; g.fillStyle = '#155E74';
                        g.fillText(ctx.T('mode_' + mode), 12, 18);
                        g.font = '10.5px Inter, sans-serif'; g.fillStyle = col.soft;
                        g.fillText(ctx.T('bOut') + ' · R = ' + (isFinite(d.R) ? d.R.toFixed(2) : '∞') +
                                   ' · T = ' + (isFinite(d.T) ? d.T.toFixed(2) : '∞'), 12, 34);
                        if (mode === 'drift') {
                            g.fillStyle = '#4C6B4E';
                            g.fillText(ctx.T('driftNote') + ' v = E/B = ' + d.drift.toFixed(2), 12, 50);
                        }
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">F = qvB = </span><span class="xf-res">' + d.F.toFixed(2) + '</span>' +
                        '<span class="xf-op"> · R = mv∕qB = </span><span class="xf-res">' + (isFinite(d.R) ? d.R.toFixed(2) : '∞') + '</span>' +
                        '<span class="xf-op"> · T = 2πm∕qB = </span><span class="xf-res">' + (isFinite(d.T) ? d.T.toFixed(2) : '∞') + '</span>' +
                        '<br><i>' + T('periodNote2') + '</i>';
                },
                plot: {
                    height: 160,
                    x: { label: 'xSpeed', min: 0.2, max: 3 },
                    y: { label: 'yRadius', min: 0, max: 4 },
                    samples: 120,
                    // радиус растёт со скоростью линейно, а период от неё не зависит вовсе
                    curve: function (v, s) { return s.B !== 0 ? Math.min(4, v / Math.abs(s.q * s.B)) : null; },
                    marker: function (s, a, d) { return { x: s.v, y: Math.min(4, d.R) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>R</b> ' + (isFinite(d.R) ? d.R.toFixed(2) : '∞') +
                    ' &nbsp;·&nbsp; <b>T</b> ' + (isFinite(d.T) ? d.T.toFixed(2) : '∞') +
                    ' &nbsp;·&nbsp; <b>F</b> ' + d.F.toFixed(2) +
                    (mode === 'drift' ? ' &nbsp;·&nbsp; <b>E/B</b> ' + d.drift.toFixed(2) : '');
            }
        };
    }

    /* ── СТО: световые часы ─────────────────────────────────────────────────────
       Свет ходит между зеркалами. В движущейся системе он вынужден идти по
       диагонали — путь длиннее, а скорость та же, значит такт длиннее.
       Замедление времени получается из одной теоремы Пифагора. */
    function srtModel(data) {
        function gamma(b) { return 1 / Math.sqrt(1 - b * b); }
        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) { return { t: t, ph: (t * 0.6) % 1 }; },
                derive: function (st, a) {
                    var g = gamma(st.beta);
                    return { g: g, beta: st.beta, ph: a.ph,
                             tDil: st.t0 * g,               // движущиеся часы отстают
                             lCon: st.L0 / g,               // движущаяся линейка короче
                             mAdd: (g - 1) * 100,           // прирост энергии в процентах от покоя
                             vkm: st.beta * 299792.458 };
                },
                stage: {
                    height: 265,
                    draw: function (g2, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
                        var midY = H * 0.5, hh = 46;                // половина расстояния между зеркалами
                        // — левые часы: покоятся
                        var x1 = W * 0.22;
                        g2.strokeStyle = col.border; g2.lineWidth = 2;
                        g2.beginPath(); g2.moveTo(x1 - 26, midY - hh); g2.lineTo(x1 + 26, midY - hh);
                        g2.moveTo(x1 - 26, midY + hh); g2.lineTo(x1 + 26, midY + hh); g2.stroke();
                        var p = d.ph < 0.5 ? d.ph * 2 : (1 - d.ph) * 2;    // вверх-вниз
                        g2.strokeStyle = '#8F6417'; g2.lineWidth = 1.5;
                        g2.beginPath(); g2.moveTo(x1, midY + hh); g2.lineTo(x1, midY - hh); g2.stroke();
                        g2.fillStyle = '#8F6417';
                        g2.beginPath(); g2.arc(x1, midY + hh - 2 * hh * p, 5, 0, 6.2832); g2.fill();
                        g2.fillStyle = col.soft; g2.font = '10.5px Inter, sans-serif'; g2.textAlign = 'center';
                        g2.fillText(ctx.T('restClock'), x1, midY + hh + 22);

                        // — правые часы: движутся, свет идёт по диагонали
                        var x2 = W * 0.62, span = Math.min(W * 0.22, 120) * st.beta;
                        var shift = -span / 2 + span * d.ph;
                        g2.strokeStyle = col.border; g2.lineWidth = 2;
                        g2.beginPath();
                        g2.moveTo(x2 + shift - 26, midY - hh); g2.lineTo(x2 + shift + 26, midY - hh);
                        g2.moveTo(x2 + shift - 26, midY + hh); g2.lineTo(x2 + shift + 26, midY + hh);
                        g2.stroke();
                        // диагональный путь света — вот он и длиннее
                        g2.strokeStyle = '#155E74'; g2.lineWidth = 1.5;
                        g2.beginPath();
                        g2.moveTo(x2 - span / 2, midY + hh);
                        g2.lineTo(x2, midY - hh);
                        g2.lineTo(x2 + span / 2, midY + hh);
                        g2.stroke();
                        var px, py;
                        if (d.ph < 0.5) { px = x2 - span / 2 + span * d.ph; py = midY + hh - 2 * hh * (d.ph * 2); }
                        else { px = x2 - span / 2 + span * d.ph; py = midY - hh + 2 * hh * ((d.ph - 0.5) * 2); }
                        g2.fillStyle = '#155E74';
                        g2.beginPath(); g2.arc(px, py, 5, 0, 6.2832); g2.fill();
                        g2.fillStyle = col.soft; g2.textAlign = 'center';
                        g2.fillText(ctx.T('movingClock'), x2, midY + hh + 22);
                        // стрелка скорости
                        g2.strokeStyle = '#4C6B4E'; g2.lineWidth = 2;
                        g2.beginPath(); g2.moveTo(x2 - 30, midY - hh - 20); g2.lineTo(x2 + 30, midY - hh - 20); g2.stroke();
                        g2.beginPath(); g2.moveTo(x2 + 30, midY - hh - 20); g2.lineTo(x2 + 22, midY - hh - 24);
                        g2.moveTo(x2 + 30, midY - hh - 20); g2.lineTo(x2 + 22, midY - hh - 16); g2.stroke();
                        g2.fillStyle = '#4C6B4E'; g2.font = '10.5px Inter, sans-serif';
                        g2.fillText('v = ' + (st.beta * 100).toFixed(0) + ' % c', x2, midY - hh - 26);

                        // сводка справа
                        g2.textAlign = 'left'; g2.font = '600 11.5px Inter, sans-serif'; g2.fillStyle = '#155E74';
                        g2.fillText('γ = ' + d.g.toFixed(3), 12, 18);
                        g2.font = '10.5px Inter, sans-serif'; g2.fillStyle = col.soft;
                        g2.fillText(ctx.T('dilNote') + ' ' + d.tDil.toFixed(2) + ' ' + ctx.T('unit_s'), 12, 34);
                        g2.fillText(ctx.T('conNote') + ' ' + d.lCon.toFixed(2) + ' ' + ctx.T('unit_m'), 12, 50);
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">γ = 1∕√(1 − v²/c²) = </span><span class="xf-res">' + d.g.toFixed(4) + '</span>' +
                        '<span class="xf-op"> · Δt = γΔt₀ = </span><span class="xf-res">' + d.tDil.toFixed(3) + ' с</span>' +
                        '<span class="xf-op"> · L = L₀∕γ = </span><span class="xf-res">' + d.lCon.toFixed(3) + ' м</span>' +
                        '<br><i>' + T('energyNote') + ' +' + d.mAdd.toFixed(1) + ' %</i>';
                },
                plot: {
                    height: 165,
                    x: { label: 'xBeta', min: 0, max: 0.99 },
                    y: { label: 'yGamma', min: 1, max: 8 },
                    samples: 200,
                    // до 0,5 c поправка почти незаметна, дальше уходит в бесконечность
                    curve: function (b, s) { return Math.min(8, gamma(b)); },
                    marker: function (s, a, d) { return { x: s.beta, y: Math.min(8, d.g) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>γ</b> ' + d.g.toFixed(3) + ' &nbsp;·&nbsp; <b>v</b> ' + Math.round(d.vkm).toLocaleString('ru') + ' км/с' +
                    ' &nbsp;·&nbsp; <b>Δt</b> ' + d.tDil.toFixed(2) + ' с &nbsp;·&nbsp; <b>L</b> ' + d.lCon.toFixed(2) + ' м';
            }
        };
    }

    /* ── Квант: частица в ящике ─────────────────────────────────────────────────
       Волна де Бройля, запертая между стенками, обязана уложиться целым числом
       полуволн — ровно как струна. Отсюда дискретные уровни энергии. */
    function quantumModel(data) {
        var mode = 'psi';
        function psi(x, n, L) { return Math.sqrt(2 / L) * Math.sin(n * Math.PI * x / L); }
        function En(n, L, m) { return n * n / (m * L * L); }        // в условных единицах
        return {
            modes: ['psi', 'prob'],
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) { return { t: t, ph: Math.cos(t * En(st.n, st.L, st.m) * 2) }; },
                derive: function (st, a) {
                    var n = Math.round(st.n);
                    return { n: n, E: En(n, st.L, st.m), lam: 2 * st.L / n,
                             nodes: n - 1, ph: a.ph,
                             E1: En(1, st.L, st.m), ratio: n * n };
                },
                stage: {
                    height: 265,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived, a = ctx.anim;
                        var x0 = W * 0.10, x1 = W * 0.72, midY = H * 0.44, amp = 46;
                        var PX = function (x) { return x0 + x / st.L * (x1 - x0); };

                        // стенки ящика — бесконечно высокие
                        g.strokeStyle = col.border; g.lineWidth = 2.5;
                        g.beginPath(); g.moveTo(x0, midY - 78); g.lineTo(x0, midY + 78);
                        g.moveTo(x1, midY - 78); g.lineTo(x1, midY + 78); g.stroke();
                        g.strokeStyle = col.soft; g.lineWidth = 1; g.setLineDash([2, 4]);
                        g.beginPath(); g.moveTo(x0, midY); g.lineTo(x1, midY); g.stroke(); g.setLineDash([]);

                        // сама волновая функция (мигает во времени) или плотность вероятности
                        var isProb = mode === 'prob';
                        g.strokeStyle = isProb ? '#4C6B4E' : '#155E74'; g.lineWidth = 2;
                        g.beginPath();
                        for (var x = 0; x <= st.L; x += st.L / 300) {
                            var v = psi(x, d.n, st.L);
                            var y = isProb ? -(v * v) * amp * 0.9 : v * (a ? a.ph : 1) * amp;
                            if (x === 0) g.moveTo(PX(x), midY - y); else g.lineTo(PX(x), midY - y);
                        }
                        g.stroke();

                        // узлы — точки, где частицы не бывает никогда
                        g.fillStyle = '#9B2C2C';
                        for (var k = 1; k < d.n; k++) {
                            g.beginPath(); g.arc(PX(k * st.L / d.n), midY, 3.5, 0, 6.2832); g.fill();
                        }

                        // лесенка уровней справа
                        var lx = W * 0.80, ly0 = H - 30, lh = H - 70;
                        g.strokeStyle = col.border; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(lx - 6, ly0); g.lineTo(lx - 6, ly0 - lh); g.stroke();
                        for (var lev = 1; lev <= 5; lev++) {
                            var yy = ly0 - lh * (lev * lev) / 25;
                            g.strokeStyle = lev === d.n ? '#8F6417' : col.soft;
                            g.lineWidth = lev === d.n ? 2.5 : 1;
                            g.beginPath(); g.moveTo(lx, yy); g.lineTo(lx + 44, yy); g.stroke();
                            g.fillStyle = lev === d.n ? '#8F6417' : col.soft;
                            g.font = '10px Inter, sans-serif'; g.textAlign = 'left';
                            g.fillText('n=' + lev, lx + 48, yy + 3);
                        }
                        g.fillStyle = col.soft; g.font = '10px Inter, sans-serif'; g.textAlign = 'left';
                        g.fillText(ctx.T('levelsNote'), lx - 6, ly0 - lh - 8);

                        // подписи
                        g.textAlign = 'left'; g.font = '600 11.5px Inter, sans-serif'; g.fillStyle = '#155E74';
                        g.fillText(ctx.T('mode_' + mode), 12, 18);
                        g.font = '10.5px Inter, sans-serif'; g.fillStyle = col.soft;
                        g.fillText('λ = 2L/n = ' + d.lam.toFixed(2) + ' · E ∝ n² = ' + d.ratio, 12, 34);
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">L = n·λ∕2 · λ = </span><span class="xf-res">' + d.lam.toFixed(3) + '</span>' +
                        '<span class="xf-op"> · Eₙ = n²h²∕8mL² ∝ </span><span class="xf-res">' + d.ratio + '·E₁</span>' +
                        '<br><i>' + T('nodesNote') + ' ' + d.nodes + '</i>';
                },
                plot: {
                    height: 160,
                    x: { label: 'xN', min: 1, max: 6 },
                    y: { label: 'yE', min: 0, max: 36 },
                    samples: 60,
                    // уровни растут как квадрат номера — не линейно
                    curve: function (n, s) { return n * n; },
                    marker: function (s, a, d) { return { x: d.n, y: d.ratio }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>n</b> ' + d.n + ' &nbsp;·&nbsp; <b>λ</b> ' + d.lam.toFixed(2) +
                    ' &nbsp;·&nbsp; <b>E/E₁</b> ' + d.ratio +
                    ' &nbsp;·&nbsp; <b>' + T('nodeWord') + '</b> ' + d.nodes;
            }
        };
    }

    /* ── Ядро: энергия связи по формуле Вайцзеккера ─────────────────────────────
       Пять слагаемых с ясным смыслом: объём, поверхность, кулон, симметрия,
       спаривание. Из их спора получается кривая с максимумом на железе —
       и сразу видно, почему лёгкие ядра выгодно сливать, а тяжёлые делить. */
    function nucleusModel(data) {
        var aV = 15.75, aS = 17.8, aC = 0.711, aA = 23.7, aP = 11.18;   // МэВ
        function terms(A, Z) {
            var N = A - Z;
            var vol = aV * A;
            var surf = -aS * Math.pow(A, 2 / 3);
            var coul = -aC * Z * (Z - 1) / Math.cbrt(A);
            var asym = -aA * (A - 2 * Z) * (A - 2 * Z) / A;
            var pair = 0;
            if (A % 2 === 0) pair = (Z % 2 === 0 ? 1 : -1) * aP / Math.sqrt(A);
            return { vol: vol, surf: surf, coul: coul, asym: asym, pair: pair,
                     total: vol + surf + coul + asym + pair };
        }
        // наиболее устойчивое Z при данном A — минимум по энергии
        function bestZ(A) {
            var best = 1, bb = -1e9;
            for (var z = 1; z < A; z++) { var b = terms(A, z).total / A; if (b > bb) { bb = b; best = z; } }
            return best;
        }
        return {
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) { return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit }; }),
                animate: function (t, st) { return { t: t }; },
                derive: function (st) {
                    var A = Math.round(st.A), Z = Math.round(st.Z);
                    if (Z >= A) Z = A - 1;
                    var t1 = terms(A, Z);
                    return { A: A, Z: Z, N: A - Z, B: t1.total, BA: t1.total / A,
                             vol: t1.vol / A, surf: t1.surf / A, coul: t1.coul / A,
                             asym: t1.asym / A, pair: t1.pair / A,
                             bestZ: bestZ(A), stable: Math.abs(Z - bestZ(A)) <= 1,
                             fusion: A < 56, peak: 56 };
                },
                stage: {
                    height: 275,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, d = ctx.derived;
                        // — слева: само ядро горстью нуклонов
                        var cx = W * 0.20, cy = H * 0.42, R = 8 + Math.cbrt(d.A) * 7;
                        var seedA = d.A;
                        for (var i = 0; i < d.A && i < 240; i++) {
                            // раскладка по спирали Фибоначчи — устойчивая и без случайности
                            var t2 = i * 2.39996, rr = R * Math.sqrt(i / Math.max(1, d.A));
                            var px = cx + rr * Math.cos(t2), py = cy + rr * Math.sin(t2);
                            g.fillStyle = i < d.Z ? '#9B2C2C' : '#155E74';
                            g.globalAlpha = .85;
                            g.beginPath(); g.arc(px, py, 3.2, 0, 6.2832); g.fill();
                        }
                        g.globalAlpha = 1;
                        g.fillStyle = col.soft; g.font = '10.5px Inter, sans-serif'; g.textAlign = 'center';
                        g.fillText(ctx.T('protons') + ' ' + d.Z + ' · ' + ctx.T('neutrons') + ' ' + d.N, cx, cy + R + 24);
                        g.fillStyle = d.stable ? '#4C6B4E' : '#9B2C2C'; g.font = '600 11px Inter, sans-serif';
                        g.fillText(ctx.T(d.stable ? 'stable' : 'unstable') +
                                   (d.stable ? '' : ' · ' + ctx.T('bestZ') + ' ' + d.bestZ), cx, cy + R + 40);

                        // — справа: разложение энергии связи по вкладам
                        var bx = W * 0.46, by = H * 0.16, bw = W * 0.48, rowH = 22;
                        var rows = [['vol', d.vol, '#4C6B4E'], ['surf', d.surf, '#8F6417'],
                                    ['coul', d.coul, '#9B2C2C'], ['asym', d.asym, '#155E74']];
                        var scale = bw / 20;
                        rows.forEach(function (r, i) {
                            var y = by + i * rowH;
                            var len = Math.max(-bw / 2, Math.min(bw / 2, r[1] * scale));
                            g.fillStyle = r[2]; g.globalAlpha = .75;
                            if (len >= 0) g.fillRect(bx + bw / 2, y, len, 13);
                            else g.fillRect(bx + bw / 2 + len, y, -len, 13);
                            g.globalAlpha = 1;
                            g.fillStyle = col.soft; g.font = '10px Inter, sans-serif'; g.textAlign = 'left';
                            g.fillText(ctx.T('term_' + r[0]) + ' ' + r[1].toFixed(2), bx, y + 24);
                        });
                        g.strokeStyle = col.border; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(bx + bw / 2, by - 4); g.lineTo(bx + bw / 2, by + 4 * rowH); g.stroke();

                        // итог
                        g.textAlign = 'left'; g.font = '600 12px Inter, sans-serif'; g.fillStyle = '#155E74';
                        g.fillText(ctx.T('bindPer') + ' ' + d.BA.toFixed(2) + ' ' + ctx.T('unit_mev'),
                                   bx, H - 30);
                        g.font = '10.5px Inter, sans-serif'; g.fillStyle = col.soft;
                        g.fillText(ctx.T(d.fusion ? 'fusionSide' : 'fissionSide'), bx, H - 14);
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">B∕A = </span><span class="xf-res">' + d.BA.toFixed(2) +
                        '</span><span class="xf-op"> МэВ · A = </span><span class="xf-var">' + d.A +
                        '</span><span class="xf-op"> · Z = </span><span class="xf-var">' + d.Z + '</span>' +
                        '<br><i>' + T('peakNote') + '</i>';
                },
                plot: {
                    height: 170,
                    x: { label: 'xA', min: 2, max: 240 },
                    y: { label: 'yBA', min: 0, max: 10 },
                    samples: 238,
                    // главная кривая ядерной физики: удельная энергия связи против массового числа
                    curve: function (A, s) {
                        var Ai = Math.max(2, Math.round(A));
                        var b = terms(Ai, bestZ(Ai)).total / Ai;
                        return b > 0 ? Math.min(10, b) : null;
                    },
                    marker: function (s, a, d) { return { x: d.A, y: Math.max(0, Math.min(10, d.BA)) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>B/A</b> ' + d.BA.toFixed(2) + ' МэВ &nbsp;·&nbsp; <b>B</b> ' + d.B.toFixed(0) + ' МэВ' +
                    ' &nbsp;·&nbsp; <b>' + T('bestZ') + '</b> ' + d.bestZ +
                    ' &nbsp;·&nbsp; ' + T(d.fusion ? 'fusionSide' : 'fissionSide');
            }
        };
    }

    global.B42Models = { gas: gasModel, kettle: kettleModel, engine: engineModel,
                         motion: motionModel, newton: newtonModel, collision: collisionModel,
                         rotation: rotationModel, oscillator: oscillatorModel,
                         resonance: resonanceModel, entropy: entropyModel,
                         orbit: orbitModel, wave: waveModel, charge: chargeModel, magnet: magnetModel,
                         srt: srtModel, quantum: quantumModel, nucleus: nucleusModel };
})(window);
