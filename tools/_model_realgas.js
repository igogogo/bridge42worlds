/* _model_realgas.js — ЗАГОТОВКА фабрики стенда темы realgas.

   КАК ПОДКЛЮЧАТЬ (для ведущей сессии). Файл самодостаточен: он кладёт фабрику в
   window.B42ModelsExtra.realgas и js/models.js не трогает. Дальше нужно:
     1) переименовать в js/models-realgas.js и подключить ПОСЛЕ js/stage-kit.js;
     2) добавить строку realgas: realgasModel в FACTORIES внутри js/models.js
        (или прогнать B42ModelsExtra через тот же withUnits, что и остальные, —
        здесь единицы в подписи не подставляются, так что обёртка безвредна).
   Данные ползунков и подписи лежат в data/theory/realgas.json.

   ЧТО СЧИТАЕТ. Всё в приведённых координатах: p/p_c = 8(T/T_c)/(3V/V_c − 1) − 3/(V/V_c)².
   В них кривая ОДНА на все вещества — это закон соответственных состояний, и потому
   купол сосуществования и спинодаль считаются один раз при загрузке, а не каждый кадр.
   Купол — правило равных площадей Максвелла: бисекция по давлению, площади через
   аналитическую первообразную F(V) = (8T/3)·ln(3V − 1) + 3/V. Проверено счётом:
   при T/T_c = 0,90 выходит p_s = 0,6470, V_l = 0,6035, V_g = 2,3489, невязка 1e-13.

   ПРЕССЕТЫ. Постоянные a и b держатся в полной справочной точности (CO₂ b = 0,04267 л/моль),
   а ползунки показывают ближайшее значение своей сетки (42,7). Иначе критическая
   температура CO₂ съезжала бы с 304,0 на 303,8 К и расходилась с текстом параграфа.
   У гелия a = 0,0346 мельче шага ползунка 0,01 — это и есть причина держать его пресетом,
   и стенд пишет об этом подписью, а не умалчивает.

   ОТСТУПЛЕНИЕ ОТ ПЛАНА. Отдельной кнопки «идеальный газ» нет: движок explorable даёт
   один ряд кнопок, и он занят выбором вещества. Идеальная изотерма нарисована всегда —
   серым пунктиром с подписью, расхождение видно без переключения. Если кнопка нужна,
   её место — в modes, но тогда вещества придётся вынести в отдельный контрол. */

(function (global) {
    'use strict';
    var KIT = global.B42Kit;

    /** Реальный газ: уравнение Ван-дер-Ваальса, купол сосуществования и критическая точка. */
    function realgasModel(data) {
        var R = 0.083145;                       // л·бар/(моль·К) — под литры и бары
        var ZC = 3 / 8;                         // критический коэффициент сжимаемости модели

        // a — л²·бар/моль², b — л/моль; bG/aG — то, что показывает ползунок на своей сетке;
        // Tc/pc/Vc/Zc — ИЗМЕРЕННЫЕ значения, они стоят рядом с расчётными, а не вместо них.
        var PRESETS = {
            co2:   { a: 3.640,  b: 0.04267, aG: 3.64, bG: 42.7, Tc: 304.13, pc: 73.77,  Vc: 94.0, Zc: 0.274 },
            water: { a: 5.536,  b: 0.03049, aG: 5.54, bG: 30.5, Tc: 647.10, pc: 220.64, Vc: 55.9, Zc: 0.229 },
            n2:    { a: 1.370,  b: 0.03870, aG: 1.37, bG: 38.7, Tc: 126.19, pc: 33.96,  Vc: 89.4, Zc: 0.289 },
            he:    { a: 0.0346, b: 0.02380, aG: 0.03, bG: 23.8, Tc: 5.195,  pc: 2.275,  Vc: 57.3, Zc: 0.301 }
        };
        var mode = 'co2', host = null;

        // ── приведённое уравнение и его производная ────────────────────────
        function pr(Tr, V) { return 8 * Tr / (3 * V - 1) - 3 / (V * V); }
        function dpr(Tr, V) { return -24 * Tr / ((3 * V - 1) * (3 * V - 1)) + 6 / (V * V * V); }
        function Fint(Tr, V) { return (8 * Tr / 3) * Math.log(3 * V - 1) + 3 / V; }

        // Локальные минимум и максимум изотермы — концы запрещённого участка (спинодаль).
        function extrema(Tr) {
            var out = [], prev = null;
            for (var V = 0.36; V < 24; V *= 1.002) {
                var d = dpr(Tr, V);
                if (prev && prev.d * d < 0) out.push(refine(function (x) { return dpr(Tr, x); }, prev.V, V));
                prev = { V: V, d: d };
                if (out.length === 2) break;
            }
            return out;                          // [V локального минимума p, V локального максимума p]
        }
        function refine(f, lo, hi) {
            for (var i = 0; i < 60; i++) { var m = (lo + hi) / 2; if (f(lo) * f(m) <= 0) hi = m; else lo = m; }
            return (lo + hi) / 2;
        }
        // Крайние корни уравнения pr(Tr,V) = ps: жидкость слева от впадины, пар справа от горба.
        function edgeRoots(Tr, ps, Vmin, Vmax) {
            var Vl = refine(function (x) { return pr(Tr, x) - ps; }, 0.3400001, Vmin);
            var hi = Vmax;
            while (pr(Tr, hi) > ps && hi < 5000) hi *= 1.6;
            var Vg = refine(function (x) { return pr(Tr, x) - ps; }, Vmax, hi);
            return { Vl: Vl, Vg: Vg };
        }

        /** Правило равных площадей: давление насыщения и объёмы фаз при данной T/T_c. */
        function maxwell(Tr) {
            if (Tr >= 0.99999) return null;
            var e = extrema(Tr);
            if (e.length < 2) return null;
            var lo = Math.max(1e-5, pr(Tr, e[0])), hi = pr(Tr, e[1]);
            if (!(hi > lo)) return null;
            for (var i = 0; i < 50; i++) {
                var ps = (lo + hi) / 2, r = edgeRoots(Tr, ps, e[0], e[1]);
                // площадь под кривой минус площадь под площадкой: знак говорит, куда двигать ps
                if (Fint(Tr, r.Vg) - Fint(Tr, r.Vl) - ps * (r.Vg - r.Vl) > 0) lo = ps; else hi = ps;
            }
            var ps2 = (lo + hi) / 2, rr = edgeRoots(Tr, ps2, e[0], e[1]);
            return { ps: ps2, Vl: rr.Vl, Vg: rr.Vg, Vsl: e[0], Vsg: e[1] };
        }

        // Купол и спинодаль в приведённых координатах одни и те же для ВСЕХ веществ,
        // поэтому считаются один раз при первом кадре, а не каждый раз заново.
        var DOME = null, SPIN = null, MX = {};
        function dome() {
            if (DOME) return DOME;
            DOME = []; SPIN = [];
            for (var Tr = 0.80; Tr < 0.9995; Tr += 0.01) {
                var m = maxwell(Tr);
                if (!m) continue;
                DOME.push({ Tr: Tr, ps: m.ps, Vl: m.Vl, Vg: m.Vg });
                SPIN.push({ Vl: m.Vsl, pl: pr(Tr, m.Vsl), Vg: m.Vsg, pg: pr(Tr, m.Vsg) });
            }
            DOME.push({ Tr: 1, ps: 1, Vl: 1, Vg: 1 });
            SPIN.push({ Vl: 1, pl: 1, Vg: 1, pg: 1 });
            return DOME;
        }
        function mx(Tr) {                        // кэш по шагу ползунка (0,01)
            var k = Tr.toFixed(3);
            if (!(k in MX)) MX[k] = maxwell(Tr);
            return MX[k];
        }

        function P(st) {
            if (mode === 'custom') return { a: st.a, b: st.b / 1000, meas: null };
            var q = PRESETS[mode];
            return { a: q.a, b: q.b, meas: q };
        }
        function crit(st) {
            var q = P(st), b = Math.max(1e-6, q.b);
            return { Tc: 8 * q.a / (27 * R * b), pc: q.a / (27 * b * b), Vc: 3 * b * 1000, meas: q.meas };
        }
        // Пресет физически двигает ползунки a и b: иначе на экране одно, а в расчёте другое.
        function syncPreset() {
            if (mode === 'custom' || !host) return;
            var q = PRESETS[mode], inputs = host.querySelectorAll('.xpl-ctrl input');
            [[2, q.aG], [3, q.bG]].forEach(function (p) {
                if (inputs[p[0]] && parseFloat(inputs[p[0]].value) !== p[1]) {
                    inputs[p[0]].value = p[1];
                    inputs[p[0]].dispatchEvent(new Event('input'));
                }
            });
        }

        return {
            modes: ['co2', 'water', 'n2', 'he', 'custom'],
            getMode: function () { return mode; },
            setMode: function (m) { mode = m; syncPreset(); },
            bindHost: function (el) { host = el; },
            cfg: {
                i18n: data.i18n,
                params: data.params.map(function (p) {
                    return { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit };
                }),
                animate: function (t) { syncPreset(); return { t: t }; },
                derive: function (st) {
                    var c = crit(st), Tr = st.T, Vr = st.V, m = Tr < 1 ? mx(Tr) : null;
                    var two = !!(m && Vr > m.Vl && Vr < m.Vg);
                    var prNow = two ? m.ps : pr(Tr, Vr);
                    return {
                        Tr: Tr, Vr: Vr, pr: prNow, two: two, m: m,
                        Tc: c.Tc, pc: c.pc, Vc: c.Vc, meas: c.meas,
                        Tk: Tr * c.Tc, pbar: prNow * c.pc, Vcm: Vr * c.Vc,
                        // доля пара по правилу рычага: точка делит площадку в обратном отношении
                        xVap: two ? (Vr - m.Vl) / (m.Vg - m.Vl) : (Tr >= 1 || Vr >= (m ? m.Vg : 0) ? 1 : 0),
                        Z: ZC * prNow * Vr / Tr
                    };
                },
                stage: {
                    height: 306,
                    draw: function (g, ctx) {
                        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived, T = ctx.T;
                        var padL = 126, padR = 16, top = 28, base = H - 40;
                        var VMIN = 0.45, VMAX = 6.2, PMAX = 2.0;
                        var SX = KIT.scale({ min: VMIN, max: VMAX, from: padL, to: W - padR });
                        var SY = KIT.scale({ min: 0, max: PMAX, from: base, to: top });
                        function pts(Tr, v0, v1, n) {
                            var out = [];
                            for (var i = 0; i <= n; i++) {
                                var v = v0 + (v1 - v0) * i / n, p = pr(Tr, v);
                                out.push(p >= 0 && p <= PMAX ? [SX(v), SY(p)] : null);
                            }
                            return out;
                        }
                        dome();

                        KIT.axis(g, padL, W - padR, base, { color: col.border });
                        g.save(); g.strokeStyle = col.border; g.lineWidth = 1;
                        g.beginPath(); g.moveTo(padL, top - 6); g.lineTo(padL, base); g.stroke(); g.restore();
                        KIT.text(g, T('xV'), W - padR, base + 16, { size: 10, color: col.soft, align: 'right' });
                        KIT.text(g, T('yP'), padL - 4, top - 10, { size: 10, color: col.soft, align: 'left' });

                        // — купол сосуществования: слева ветвь жидкости, справа ветвь пара
                        var poly = [], k;
                        for (k = 0; k < DOME.length; k++) poly.push([SX(DOME[k].Vl), SY(DOME[k].ps)]);
                        for (k = DOME.length - 1; k >= 0; k--) poly.push([SX(DOME[k].Vg), SY(DOME[k].ps)]);
                        g.save(); g.globalAlpha = 0.14; g.fillStyle = '#155E74';
                        g.beginPath();
                        poly.forEach(function (p, i) { if (i) g.lineTo(p[0], p[1]); else g.moveTo(p[0], p[1]); });
                        g.closePath(); g.fill(); g.restore();
                        KIT.polyline(g, poly, { color: '#155E74', width: 1.6, alpha: 0.75 });

                        // — спинодаль: внутри неё состояний нет вовсе, между ней и куполом они метастабильны
                        var sp = [];
                        for (k = 0; k < SPIN.length; k++) if (SPIN[k].pl >= 0) sp.push([SX(SPIN[k].Vl), SY(SPIN[k].pl)]);
                        for (k = SPIN.length - 1; k >= 0; k--) if (SPIN[k].pg >= 0) sp.push([SX(SPIN[k].Vg), SY(SPIN[k].pg)]);
                        KIT.polyline(g, sp, { color: '#9B2C2C', width: 1.3, dash: [4, 4], alpha: 0.8 });

                        // — бледное семейство изотерм: чтобы был виден ход всей поверхности
                        [0.85, 0.90, 0.95, 1.05, 1.15, 1.30].forEach(function (Tr) {
                            KIT.polyline(g, pts(Tr, VMIN, VMAX, 160), { color: col.soft, width: 1, alpha: 0.35 });
                        });

                        // — идеальный газ при той же температуре: p/p_c = (T/T_c)/(Z_c·V/V_c)
                        var idl = [];
                        for (k = 0; k <= 160; k++) {
                            var v = VMIN + (VMAX - VMIN) * k / 160, pi = st.T / (ZC * v);
                            idl.push(pi <= PMAX ? [SX(v), SY(pi)] : null);
                        }
                        KIT.polyline(g, idl, { color: col.soft, width: 1.4, dash: [2, 4] });

                        // — текущая изотерма и площадка на ней
                        var mm = d.m;
                        KIT.polyline(g, pts(st.T, VMIN, VMAX, 220),
                                     { color: '#155E74', width: st.T === 1 ? 2.8 : 2.2 });
                        if (mm) {
                            KIT.polyline(g, [[SX(mm.Vl), SY(mm.ps)], [SX(Math.min(VMAX, mm.Vg)), SY(mm.ps)]],
                                         { color: '#9B2C2C', width: 2.8 });
                            KIT.text(g, T('liq'), SX(mm.Vl), SY(mm.ps) - 9, { size: 9.5, color: '#9B2C2C' });
                            KIT.text(g, T('vap'), SX(Math.min(VMAX, mm.Vg)), SY(mm.ps) - 9, { size: 9.5, color: '#9B2C2C' });
                        } else {
                            KIT.text(g, T('above'), (padL + W - padR) / 2, top + 12, { size: 10, color: col.soft });
                        }

                        // — критическая точка
                        KIT.body(g, SX(1), SY(1), { shape: 'dot', size: 5, color: '#2e9e5b' });
                        KIT.text(g, T('crit'), SX(1) + 8, SY(1) - 10, { size: 9.5, color: '#2e9e5b', align: 'left' });

                        // — текущее состояние
                        KIT.body(g, SX(st.V), SY(d.pr), { shape: 'dot', size: 6, color: '#8F6417' });
                        KIT.marker(g, SX(st.V), SY(d.pr), base, { color: '#8F6417', width: 1.2 });
                        KIT.text(g, d.two ? T('twoPhase') : T('oneFluid'),
                                 SX(st.V), SY(d.pr) - 12, { size: 10, color: '#8F6417' });
                        if (d.two) {
                            KIT.text(g, T('lever') + ': ' + T('vap') + ' ' + Math.round(d.xVap * 100) + ' % · ' +
                                     T('liq') + ' ' + Math.round((1 - d.xVap) * 100) + ' %',
                                     SX(st.V), SY(d.pr) + 16, { size: 9.5, color: '#8F6417' });
                        }
                        KIT.text(g, T('ideal'), W - padR, top + 4, { size: 9.5, color: col.soft, align: 'right' });

                        // — табличка настоящих единиц: расчёт рядом с измеренным, ничего не прячем
                        var y = top + 2, L = 10;
                        KIT.text(g, T('crit'), L, y, { size: 10.5, weight: '600', color: '#155E74', align: 'left' });
                        [[T('tcLab'), d.Tc.toFixed(d.Tc < 20 ? 2 : 1) + ' ' + T('unit_k'), d.meas && d.meas.Tc],
                         [T('pcLab'), d.pc.toFixed(d.pc < 10 ? 2 : 1) + ' ' + T('unit_bar'), d.meas && d.meas.pc],
                         [T('vcLab'), d.Vc.toFixed(0) + ' ' + T('unit_cm3'), d.meas && d.meas.Vc],
                         [T('zcLab'), ZC.toFixed(3), d.meas && d.meas.Zc]
                        ].forEach(function (row, i) {
                            var yy = y + 18 + i * 30;
                            KIT.text(g, row[0], L, yy, { size: 9.5, color: col.soft, align: 'left' });
                            KIT.text(g, row[1], L, yy + 12, { size: 10.5, color: '#155E74', align: 'left' });
                            if (row[2] != null) {
                                KIT.text(g, T('measured') + ' ' + row[2], L, yy + 23,
                                         { size: 9, color: '#9B2C2C', align: 'left' });
                            }
                        });
                        KIT.text(g, mode === 'he' ? T('heNote') : (mode === 'custom' ? T('corr') : T('presetLock')),
                                 L, base + 30, { size: 9, color: col.soft, align: 'left' });
                    }
                },
                formula: function (st, d, T) {
                    return '<span class="xf-op">p/p_c = 8(T/T_c)/(3V/V_c &minus; 1) &minus; 3(V/V_c)&#8315;&#178; = </span>' +
                        '<span class="xf-res">' + d.pr.toFixed(3) + '</span>' +
                        '<span class="xf-op"> &nbsp;&#8594;&nbsp; </span><span class="xf-var">' +
                        d.pbar.toFixed(d.pbar < 10 ? 2 : 1) + ' ' + T('unit_bar') + '</span>' +
                        '<span class="xf-op"> при </span><span class="xf-var">' +
                        d.Tk.toFixed(d.Tk < 20 ? 2 : 1) + ' ' + T('unit_k') + '</span>' +
                        '<br><i>' + (d.two
                            ? T('twoPhase') + ': ' + T('vap') + ' ' + Math.round(d.xVap * 100) + ' %, ' +
                              T('liq') + ' ' + Math.round((1 - d.xVap) * 100) + ' %'
                            : T('corr')) + '</i>';
                },
                plot: {
                    height: 168,
                    x: { label: 'xV2', min: 0.5, max: 6 },
                    y: { label: 'yZ', min: 0, max: 1.2 },
                    samples: 120,
                    // Z вдоль текущей изотермы: единица — идеальный газ, провал — реальный
                    curve: function (v, s) {
                        var m = s.T < 1 ? mx(s.T) : null;
                        var p = (m && v > m.Vl && v < m.Vg) ? m.ps : pr(s.T, v);
                        return Math.max(0, Math.min(1.2, ZC * p * v / s.T));
                    },
                    marker: function (s, a, d) { return { x: s.V, y: Math.max(0, Math.min(1.2, d.Z)) }; }
                }
            },
            extras: function (st, d, T) {
                return '<b>' + T('tcLab') + '</b> ' + d.Tc.toFixed(d.Tc < 20 ? 2 : 1) + ' ' + T('unit_k') +
                    ' &nbsp;·&nbsp; <b>' + T('pcLab') + '</b> ' + d.pc.toFixed(d.pc < 10 ? 2 : 1) + ' ' + T('unit_bar') +
                    ' &nbsp;·&nbsp; <b>' + T('vcLab') + '</b> ' + d.Vc.toFixed(0) + ' ' + T('unit_cm3') +
                    ' &nbsp;·&nbsp; <b>Z</b> ' + d.Z.toFixed(3);
            }
        };
    }

    global.B42ModelsExtra = global.B42ModelsExtra || {};
    global.B42ModelsExtra.realgas = realgasModel;
})(window);
