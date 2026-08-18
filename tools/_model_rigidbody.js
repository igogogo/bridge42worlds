/* _model_rigidbody.js — ЗАГОТОВКА фабрики стенда темы «Твёрдое тело».
   js/models.js я не трогаю: ведущая сессия вклеивает эту функцию рядом с
   rotationModel и добавляет в реестр строку  rigid: rigidModel.
   Данные — data/theory/rigid.json, в параграфах поле "model": "rigid".

   ТРИ РОЛИ ОДНОГО СТЕНДА (переключатель режима, как MODES в engineModel):
     spinup — §1: I = k·mR², штейнеровская добавка md², ε = M/I, ω(t) и обороты за 2 с;
     gyro   — §2: L = Iω, M = mga·sinθ, Ω = mga/(Iω) и период прецессии;
     drift  — §3: один полёт шарика двумя следами, a_кор = 2ωv и число Россби.

   Ползунки общие на все три роли, поэтому лишние прячутся: SHOW перечисляет
   ИНДЕКСЫ параметров (порядок — как в rigid.json), а applyVisibility ходит по
   .xpl-ctrl внутри host. Host приходит через bindHost — course.html его уже зовёт.

   ПРОВЕРОЧНЫЕ ЗНАЧЕНИЯ (посчитаны, сходятся с текстом параграфов):
     spinup по умолчанию (обруч, m 2,0, R 0,35, M 3,5): I = 0,245 кг·м², ε = 14,29 рад/с²,
       за 2 с ω = 28,57 рад/с, 4,55 оборота; переключение обруч→диск ровно удваивает ε;
       стержень при R = 0,40 и d = 0,20 даёт 1/12 + 1/4 = 1/3, то есть I = 0,1067 кг·м².
     gyro по умолчанию (обруч, m 2,0, R 0,35, ω₀ 30, a 0,25, θ 30°): L = 7,35 кг·м²/с,
       mga = 4,905 Н·м, Ω = 0,667 рад/с, оборот оси за 9,42 с; при протяжке θ Ω не меняется.
     drift по умолчанию (ω 2,0, v 2,0, площадка 0,5 м): a_кор = 8 м/с², снос ωvt² = 0,25 м
       к краю площадки (t = 0,25 с), Ro = v/(2ωR) = 1,0.
*/

function rigidModel(data) {
    var MODES = ['spinup', 'gyro', 'drift'];
    // какие ползунки показывать в каждой роли (индексы в data.params)
    var SHOW = { spinup: [0, 1, 2, 3, 4], gyro: [0, 1, 2, 5, 6, 7], drift: [8, 9] };
    var SHAPES = ['shape_hoop', 'shape_disc', 'shape_ball', 'shape_rod'];
    var KCOEF = [1, 0.5, 0.4, 1 / 12];
    var G = 9.81, PLATE = 0.5;        // радиус вращающейся площадки, м — фиксирован
    var SPIN_T = 2, SPIN_CYCLE = 2.6; // разгон 2 с, потом пауза и сброс

    var mode = 'spinup', host = null;

    function lang() { return (document.documentElement.getAttribute('lang')) || 'ru'; }
    function T(key) { var d = data.i18n && data.i18n[lang()]; return (d && d[key]) || key; }

    function kOf(st) { return KCOEF[Math.round(st.shape)] || 1; }
    function inertiaOwn(st) { return kOf(st) * st.m * st.R * st.R; }   // относительно центра масс
    function inertiaAdd(st) { return st.m * st.d * st.d; }             // добавка Штейнера
    function inertia(st) { return inertiaOwn(st) + (mode === 'spinup' ? inertiaAdd(st) : 0); }
    function epsOf(st) { var I = inertia(st); return I > 0 ? st.Mt / I : 0; }
    function torqueMax(st) { return st.m * G * st.arm; }               // mga — при θ = 90°
    function torqueOf(st) { return torqueMax(st) * Math.sin(st.th * Math.PI / 180); }
    function precess(st) {                                            // Ω = mga/(Iω): sinθ сократился
        var L = inertiaOwn(st) * st.w0;
        return L > 0 ? torqueMax(st) / L : 0;
    }
    function fmtNum(v, n) { return v.toFixed(n == null ? 2 : n).replace('.', ','); }

    // ── видимость ползунков: роли пользуются разными наборами ──
    function applyVisibility() {
        if (!host) return;
        var wraps = host.querySelectorAll('.xpl-ctrl'), keep = SHOW[mode] || [];
        for (var i = 0; i < wraps.length; i++) {
            wraps[i].style.display = keep.indexOf(i) >= 0 ? '' : 'none';
        }
    }

    return {
        modes: MODES,
        getMode: function () { return mode; },
        setMode: function (m) { if (MODES.indexOf(m) >= 0) { mode = m; applyVisibility(); } },
        bindHost: function (el) { host = el; applyVisibility(); },
        cfg: {
            i18n: data.i18n,
            params: data.params.map(function (p) {
                var out = { key: p.key, label: p.key, min: p.min, max: p.max, step: p.step, value: p.value, unit: p.unit };
                // форма — не число, а имя: подпись значения рисуем сами
                if (p.key === 'shape') out.fmt = function (v) { return T(SHAPES[Math.round(v)] || SHAPES[0]); };
                return out;
            }),

            animate: function (t, st) {
                if (mode === 'spinup') {
                    var tt = Math.min(t % SPIN_CYCLE, SPIN_T), e = epsOf(st);
                    return { t: tt, phase: 0.5 * e * tt * tt, w: e * tt };
                }
                if (mode === 'gyro') {
                    return { t: t, phase: precess(st) * t, spin: st.w0 * t };
                }
                // drift: шарик летит от центра, пока не дойдёт до края площадки
                var tFly = PLATE / Math.max(0.1, st.vb);
                var tt2 = (t % (tFly * 1.35));
                return { t: Math.min(tt2, tFly), tFly: tFly, plate: st.wd * t };
            },

            derive: function (st, a) {
                if (mode === 'spinup') {
                    return { t: a.t, phase: a.phase, w: a.w, I: inertia(st), I0: inertiaOwn(st),
                             Iadd: inertiaAdd(st), eps: epsOf(st), k: kOf(st),
                             turns: a.phase / (2 * Math.PI) };
                }
                if (mode === 'gyro') {
                    var I = inertiaOwn(st);
                    var Om = precess(st);
                    return { t: a.t, phase: a.phase, spin: a.spin, I: I, L: I * st.w0,
                             M: torqueOf(st), Mmax: torqueMax(st), Om: Om,
                             Tp: Om > 0 ? 2 * Math.PI / Om : Infinity };
                }
                var f = st.vb > 0 ? st.wd / st.vb : 0;
                return { t: a.t, tFly: a.tFly, plate: a.plate, aCor: 2 * st.wd * st.vb,
                         drift: st.wd * st.vb * a.t * a.t,
                         Ro: st.wd > 0 ? st.vb / (2 * st.wd * PLATE) : Infinity, f: f };
            },

            stage: {
                height: 250,
                draw: function (g, ctx) {
                    if (mode === 'spinup') return drawSpin(g, ctx);
                    if (mode === 'gyro') return drawGyro(g, ctx);
                    return drawDrift(g, ctx);
                }
            },

            formula: function (st, d) {
                if (mode === 'spinup') {
                    var add = d.Iadd > 1e-9
                        ? '<span class="xf-op"> + md&#178; = </span><span class="xf-var">' + fmtNum(d.Iadd, 3) + '</span>'
                        : '';
                    return '<span class="xf-op">I = k&#183;mR&#178; = </span><span class="xf-var">' + fmtNum(d.k, 3) +
                        '</span><span class="xf-op"> &#183; </span><span class="xf-var">' + fmtNum(st.m, 1) +
                        '</span><span class="xf-op"> &#183; </span><span class="xf-var">' + fmtNum(st.R, 2) +
                        '</span><span class="xf-op">&#178;</span>' + add +
                        '<span class="xf-op"> &#8594; </span><span class="xf-res">' + fmtNum(d.I, 3) + ' ' + T('unit_kgm2') + '</span>' +
                        '<br><span class="xf-op">&#949; = M / I = </span><span class="xf-res">' + fmtNum(d.eps, 2) + ' ' + T('unit_rads2') + '</span>' +
                        '<span class="xf-op"> &nbsp;·&nbsp; &#969;(2 с) = </span><span class="xf-var">' +
                        fmtNum(d.eps * SPIN_T, 1) + ' ' + T('unit_rads') + '</span>' +
                        '<br><i>' + T('spinNote') + '</i>';
                }
                if (mode === 'gyro') {
                    return '<span class="xf-op">L = I&#969; = </span><span class="xf-var">' + fmtNum(d.L, 2) +
                        '</span><span class="xf-op"> &nbsp;·&nbsp; M = mga&#183;sin&#952; = </span><span class="xf-var">' +
                        fmtNum(d.M, 2) + ' ' + T('unit_nm') + '</span>' +
                        '<br><span class="xf-op">&#937; = mga / (I&#969;) = </span><span class="xf-res">' +
                        fmtNum(d.Om, 3) + ' ' + T('unit_rads') + '</span>' +
                        '<span class="xf-op"> &nbsp;·&nbsp; ' + T('precPeriod') + ' </span><span class="xf-var">' +
                        fmtNum(d.Tp, 2) + ' ' + T('unit_s') + '</span>' +
                        '<br><i>' + T('precNote') + '</i>';
                }
                return '<span class="xf-op">a<sub>кор</sub> = 2&#969;v = </span><span class="xf-res">' +
                    fmtNum(d.aCor, 2) + ' ' + T('unit_ms2') + '</span>' +
                    '<span class="xf-op"> &nbsp;·&nbsp; ' + T('rossby') + ' Ro = v/(2&#969;R) = </span><span class="xf-var">' +
                    (isFinite(d.Ro) ? fmtNum(d.Ro, 2) : '&#8734;') + '</span>';
            },

            // График строится один раз, а ролей три, поэтому подписи осей — геттеры:
            // движок делает T(pl.x.label) каждый кадр, и геттер отдаёт ключ текущего режима.
            // По оси Y всюду выбраны величины ПОРЯДКА единиц и больше: движок подписывает
            // деления через Math.round, и доли (Ω ≈ 0,67) на нём читались бы как «1».
            plot: {
                height: 160,
                x: {
                    get label() { return mode === 'spinup' ? 'xMassR' : (mode === 'gyro' ? 'xOmega0' : 'xOmegaD'); },
                    get min() { return mode === 'spinup' ? 0.5 : (mode === 'gyro' ? 5 : 0); },
                    get max() { return mode === 'spinup' ? 10 : (mode === 'gyro' ? 50 : 4); }
                },
                y: {
                    get label() { return mode === 'spinup' ? 'yEps' : (mode === 'gyro' ? 'yPrecT' : 'yCor'); },
                    min: 0,
                    max: function (s) {
                        if (mode === 'spinup') {
                            var per = kOf(s) * s.R * s.R + s.d * s.d;        // I на килограмм массы
                            return per > 0 ? Math.ceil(s.Mt / (0.5 * per)) : 10;
                        }
                        if (mode === 'gyro') {
                            var I0 = kOf(s) * s.m * s.R * s.R;
                            return Math.ceil(2 * Math.PI * I0 * 50 / Math.max(1e-6, s.m * G * s.arm));
                        }
                        return Math.ceil(2 * 4 * s.vb);
                    }
                },
                samples: 90,
                // spinup: ε = M/(m·(kR² + d²)) — та же гипербола, что a = F/m у второго закона
                // gyro:   период прецессии растёт линейно с ω₀ (быстрее крутится — медленнее ведёт ось)
                // drift:  a_кор = 2ωv — прямая через ноль
                curve: function (x, s) {
                    if (mode === 'spinup') {
                        var per = kOf(s) * s.R * s.R + s.d * s.d;
                        return (x > 0 && per > 0) ? s.Mt / (x * per) : null;
                    }
                    if (mode === 'gyro') {
                        var I0 = kOf(s) * s.m * s.R * s.R, mga = s.m * G * s.arm;
                        return mga > 0 ? 2 * Math.PI * I0 * x / mga : null;
                    }
                    return 2 * x * s.vb;
                },
                marker: function (s, a, d) {
                    if (mode === 'spinup') return { x: s.m, y: d.eps };
                    if (mode === 'gyro') return { x: s.w0, y: d.Tp };
                    return { x: s.wd, y: d.aCor };
                }
            }
        },

        extras: function (st, d) {
            if (mode === 'spinup') {
                var e = epsOf(st), w2 = e * SPIN_T;
                return '<b>I</b> ' + fmtNum(inertia(st), 3) + ' ' + T('unit_kgm2') +
                    (inertiaAdd(st) > 1e-9 ? ' &nbsp;(' + T('steiner') + ' ' + fmtNum(inertiaAdd(st), 3) + ')' : '') +
                    ' &nbsp;·&nbsp; <b>&#949;</b> ' + fmtNum(e, 2) + ' ' + T('unit_rads2') +
                    ' &nbsp;·&nbsp; <b>&#969;(2 с)</b> ' + fmtNum(w2, 1) + ' ' + T('unit_rads') +
                    ' &nbsp;·&nbsp; ' + fmtNum(0.5 * e * SPIN_T * SPIN_T / (2 * Math.PI), 2) + ' ' + T('turns');
            }
            if (mode === 'gyro') {
                var Om = precess(st);
                return '<b>I</b> ' + fmtNum(inertiaOwn(st), 3) + ' ' + T('unit_kgm2') +
                    ' &nbsp;·&nbsp; <b>L</b> ' + fmtNum(inertiaOwn(st) * st.w0, 2) +
                    ' &nbsp;·&nbsp; <b>M</b> ' + fmtNum(torqueOf(st), 2) + ' ' + T('unit_nm') +
                    ' &nbsp;·&nbsp; <b>&#937;</b> ' + fmtNum(Om, 3) + ' ' + T('unit_rads') +
                    ' &nbsp;·&nbsp; ' + T('precPeriod') + ' ' + (Om > 0 ? fmtNum(2 * Math.PI / Om, 2) : '&#8734;') + ' ' + T('unit_s');
            }
            var Ro = st.wd > 0 ? st.vb / (2 * st.wd * PLATE) : Infinity;
            return '<b>a<sub>кор</sub></b> ' + fmtNum(2 * st.wd * st.vb, 2) + ' ' + T('unit_ms2') +
                ' &nbsp;·&nbsp; <b>Ro</b> ' + (isFinite(Ro) ? fmtNum(Ro, 2) : '&#8734;') +
                ' &nbsp;·&nbsp; ' + fmtNum(PLATE / Math.max(0.1, st.vb), 2) + ' ' + T('unit_s') + ' до края';
        }
    };

    // ═══════════ РОЛЬ 1: РАЗГОН ═══════════════════════════════════════════
    // Тело крутится вокруг оси, отмеченной крестиком; при d > 0 ось уезжает от
    // центра масс, и штейнеровская добавка видна отдельной строкой.
    function drawSpin(g, ctx) {
        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
        var cx = W * 0.30, cy = H * 0.50;
        var pxPerM = Math.min(H * 0.34, W * 0.20) / Math.max(0.05, st.R);   // радиус тела ~ фиксированный на экране
        var rr = st.R * pxPerM, dd = st.d * pxPerM, sh = Math.round(st.shape);
        var ax = cx, ay = cy;                       // ось (центр вращения) стоит на месте
        var bx = ax + Math.cos(d.phase) * dd;       // центр масс ездит вокруг оси, если d > 0
        var by = ay + Math.sin(d.phase) * dd;

        g.save();
        g.translate(bx, by); g.rotate(d.phase);
        g.strokeStyle = col.link; g.fillStyle = col.link; g.lineWidth = 2;
        if (sh === 0) {                              // обруч
            g.lineWidth = 7; g.beginPath(); g.arc(0, 0, rr, 0, 6.2832); g.stroke();
        } else if (sh === 3) {                       // стержень: R — это длина
            KIT.alpha(g, 0.30, function () { g.fillRect(-rr / 2, -6, rr, 12); });
            g.lineWidth = 2; g.strokeRect(-rr / 2, -6, rr, 12);
        } else {                                     // диск и шар
            KIT.alpha(g, sh === 2 ? 0.20 : 0.32, function () {
                g.beginPath(); g.arc(0, 0, rr, 0, 6.2832); g.fill();
            });
            if (sh === 2) KIT.alpha(g, 0.22, function () {
                g.beginPath(); g.arc(0, 0, rr * 0.55, 0, 6.2832); g.fill();
            });
            g.beginPath(); g.arc(0, 0, rr, 0, 6.2832); g.stroke();
        }
        // метка на теле, чтобы вращение читалось глазом
        g.strokeStyle = col.accent; g.lineWidth = 2.5;
        g.beginPath(); g.moveTo(0, 0); g.lineTo(sh === 3 ? rr / 2 : rr, 0); g.stroke();
        g.restore();

        // ось и центр масс
        if (dd > 2) {
            KIT.dashed(g, [3, 3], function () {
                g.strokeStyle = col.soft; g.lineWidth = 1;
                g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
            });
            KIT.body(g, bx, by, { shape: 'dot', size: 7, color: col.soft });
            KIT.text(g, ctx.T('axisShift'), ax, ay - 14, { color: col.text, size: 10 });
        } else {
            KIT.text(g, ctx.T('axisOwn'), ax, ay - 14, { color: col.soft, size: 10 });
        }
        g.strokeStyle = col.warn; g.lineWidth = 2;
        g.beginPath();
        g.moveTo(ax - 6, ay - 6); g.lineTo(ax + 6, ay + 6);
        g.moveTo(ax + 6, ay - 6); g.lineTo(ax - 6, ay + 6);
        g.stroke();

        // момент силы — дуга у обода
        if (st.Mt > 0) {
            g.strokeStyle = col.warn; g.lineWidth = 2;
            g.beginPath(); g.arc(ax, ay, rr + 16, -0.9, 0.35); g.stroke();
            KIT.text(g, 'M = ' + fmtNum(st.Mt, 1) + ' ' + T('unit_nm'), ax, ay + rr + 40, { color: col.warn, size: 11 });
        }

        // правая колонка: числа крупно
        var x = W * 0.62;
        KIT.readout(g, [
            { text: 'I = ' + fmtNum(d.I, 3) + ' ' + T('unit_kgm2'), y: 34, size: 13, weight: '600', color: col.text },
            d.Iadd > 1e-9 ? { text: T('steiner') + ' md² = ' + fmtNum(d.Iadd, 3), y: 52, size: 10.5, color: col.accent } : null,
            { text: 'ε = M / I = ' + fmtNum(d.eps, 2) + ' ' + T('unit_rads2'), y: 78, size: 12, color: col.text },
            { text: 'ω = ' + fmtNum(d.w, 1) + ' ' + T('unit_rads'), y: 100, size: 12, color: col.link },
            { text: fmtNum(d.turns, 2) + ' ' + T('turns'), y: 120, size: 10.5, color: col.soft },
            { text: 't = ' + fmtNum(d.t, 2) + ' ' + T('unit_s'), y: 142, size: 10.5, color: col.soft }
        ], { x: x, align: 'left' });
    }

    // ═══════════ РОЛЬ 2: ГИРОСКОП ═════════════════════════════════════════
    // Вид сбоку-сверху: опора внизу, ось наклонена на θ, конец оси едет по конусу.
    function drawGyro(g, ctx) {
        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
        var px = W * 0.32, py = H * 0.86;                       // точка опоры
        var scale = Math.min(H * 0.62, W * 0.30) / 0.5;         // 0,5 м — во всю высоту сцены
        var th = st.th * Math.PI / 180, aLen = st.arm * scale;
        // проекция конуса: горизонталь сжата вдвое, чтобы читалась перспектива
        var hx = Math.sin(th) * aLen * Math.cos(d.phase), hy = Math.sin(th) * aLen * 0.42 * Math.sin(d.phase);
        var tipX = px + hx, tipY = py - Math.cos(th) * aLen + hy;

        // конус, который описывает ось
        KIT.dashed(g, [4, 4], function () {
            g.strokeStyle = col.border; g.lineWidth = 1;
            g.beginPath();
            g.ellipse(px, py - Math.cos(th) * aLen, Math.sin(th) * aLen, Math.sin(th) * aLen * 0.42, 0, 0, 6.2832);
            g.stroke();
            g.beginPath(); g.moveTo(px, py); g.lineTo(px - Math.sin(th) * aLen, py - Math.cos(th) * aLen);
            g.moveTo(px, py); g.lineTo(px + Math.sin(th) * aLen, py - Math.cos(th) * aLen);
            g.stroke();
            g.strokeStyle = col.soft;
            g.beginPath(); g.moveTo(px, py); g.lineTo(px, py - aLen * 1.25); g.stroke();
        });
        KIT.text(g, ctx.T('cone'), px, py - Math.cos(th) * aLen - Math.sin(th) * aLen * 0.42 - 12,
                 { color: col.soft, size: 10 });

        // ось волчка и тело на ней
        KIT.polyline(g, [[px, py], [tipX, tipY]], { color: col.text, width: 2.5 });
        var bodyR = Math.max(10, st.R * scale * 0.5);
        g.save(); g.translate(tipX, tipY);
        g.rotate(Math.atan2(tipY - py, tipX - px) + Math.PI / 2);
        g.strokeStyle = col.link; g.fillStyle = col.link; g.lineWidth = 2;
        KIT.alpha(g, 0.28, function () { g.beginPath(); g.ellipse(0, 0, bodyR, bodyR * 0.34, 0, 0, 6.2832); g.fill(); });
        g.beginPath(); g.ellipse(0, 0, bodyR, bodyR * 0.34, 0, 0, 6.2832); g.stroke();
        g.restore();

        // опора
        KIT.body(g, px, py, { shape: 'dot', size: 8, color: col.text });
        KIT.ground(g, px - 44, px + 44, py + 3, { color: col.soft });
        KIT.text(g, ctx.T('pivot'), px, py + 22, { color: col.soft, size: 10 });

        // векторы: L вдоль оси, M горизонтально (перпендикулярно L)
        var ux = (tipX - px), uy = (tipY - py), ul = Math.hypot(ux, uy) || 1;
        KIT.arrow(g, tipX, tipY, ux / ul * 42, uy / ul * 42,
                  { color: col.link, width: 2.5, head: 8, label: 'L', labelSize: 12 });
        KIT.arrow(g, tipX, tipY, -uy / ul * 38, ux / ul * 38,
                  { color: col.warn, width: 2.5, head: 8, label: 'M', labelSize: 12 });

        var x = W * 0.63;
        KIT.readout(g, [
            { text: 'L = Iω = ' + fmtNum(d.L, 2), y: 34, size: 13, weight: '600', color: col.text },
            { text: 'M = mga·sinθ = ' + fmtNum(d.M, 2) + ' ' + T('unit_nm'), y: 56, size: 11.5, color: col.warn },
            { text: 'Ω = mga/(Iω) = ' + fmtNum(d.Om, 3) + ' ' + T('unit_rads'), y: 80, size: 12, color: col.text },
            { text: T('precPeriod') + ' ' + fmtNum(d.Tp, 2) + ' ' + T('unit_s'), y: 100, size: 10.5, color: col.soft },
            { text: T('precNote'), y: 126, size: 10, color: col.accent }
        ], { x: x, align: 'left' });
    }

    // ═══════════ РОЛЬ 3: СНОС ═════════════════════════════════════════════
    // Один и тот же полёт нарисован дважды: слева прямая (неподвижная система),
    // справа дуга (система площадки). Это же и кухонный опыт §3 с листом бумаги.
    function drawDrift(g, ctx) {
        var W = ctx.W, H = ctx.H, col = ctx.c, st = ctx.state, d = ctx.derived;
        var rad = Math.min(H * 0.38, W * 0.20);
        var cy = H * 0.46, cxs = [W * 0.26, W * 0.70];
        var frac = d.tFly > 0 ? Math.min(1, d.t / d.tFly) : 0;

        for (var s = 0; s < 2; s++) {
            var cx = cxs[s], rotFrame = (s === 1);
            g.strokeStyle = col.border; g.lineWidth = 1.5;
            g.beginPath(); g.arc(cx, cy, rad, 0, 6.2832); g.stroke();
            // метка на краю площадки — видно, что площадка крутится
            var mark = rotFrame ? 0 : d.plate;
            KIT.body(g, cx + Math.cos(mark) * rad, cy + Math.sin(mark) * rad, { shape: 'dot', size: 8, color: col.accent });

            // след шарика: 40 точек от старта до текущего момента
            var pts = [], i, u, ang;
            for (i = 0; i <= 40; i++) {
                u = frac * i / 40;
                if (rotFrame) {                       // в системе площадки след закручен назад
                    ang = -st.wd * (u * d.tFly);
                    pts.push([cx + Math.cos(ang) * u * rad, cy + Math.sin(ang) * u * rad]);
                } else {                              // в неподвижной — прямая
                    pts.push([cx + u * rad, cy]);
                }
            }
            if (pts.length > 1) KIT.polyline(g, pts, { color: rotFrame ? col.warn : col.link, width: 2.5 });
            KIT.body(g, pts[pts.length - 1][0], pts[pts.length - 1][1], { shape: 'dot', size: 11, color: rotFrame ? col.warn : col.link });
            KIT.body(g, cx, cy, { shape: 'dot', size: 6, color: col.soft });

            KIT.text(g, ctx.T(rotFrame ? 'frameRot' : 'frameLab'), cx, cy - rad - 22, { color: col.text, size: 11, weight: '600' });
            KIT.text(g, ctx.T(rotFrame ? 'curved' : 'straight'), cx, cy - rad - 8, { color: rotFrame ? col.warn : col.link, size: 10 });
            KIT.text(g, 'R = ' + fmtNum(PLATE, 2) + ' м', cx, cy + rad + 20, { color: col.soft, size: 10 });
        }

        KIT.readout(g, [
            { text: 'a кор = 2ωv = ' + fmtNum(d.aCor, 2) + ' ' + T('unit_ms2'), y: H - 26, size: 11.5, weight: '600', color: col.warn },
            { text: T('rossby') + ' Ro = ' + (isFinite(d.Ro) ? fmtNum(d.Ro, 2) : '∞'), y: H - 10, size: 10.5, color: col.soft }
        ], { x: 14, align: 'left' });
    }
}
