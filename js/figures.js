/* figures.js — схемы-пояснения к шагам вывода формул.
   Каждая функция возвращает готовую SVG-строку.

   ЯЗЫК. Здесь долго стояло утверждение, что внутри схем только математические обозначения
   (m, v, A, Δt, P) и переводить нечего. Это было неверно: словесных подписей на схемах
   оказалось 148 — «стенка», «связи рвутся», «руки прижаты» — и англичанин, испанец и араб
   читали их кириллицей прямо на картинке. Именно из-за этого комментария и не замечали.
   Теперь подписи проходят через label() в txt(), а словарь лежит в js/figures-i18n.js
   (подключать ПЕРЕД этим файлом). Подпись под схемой — отдельная вещь, она живёт
   в JSON урока (figCaption) и переводится вместе с текстом.

   Цвета берутся из CSS-переменных сайта, поэтому схемы работают и в тёмной теме. */
(function (global) {
    'use strict';

    var INK = 'var(--text,#2c2c2c)', SOFT = 'var(--soft,#8a8a8a)', LINK = 'var(--link,#4a7c9b)',
        WARN = 'var(--red,#b31b1b)', BORD = 'var(--border,#e2e2e2)', MOSS = '#2e7d32';

    function svg(w, h, body) {
        return '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" style="max-width:' + w + 'px" ' +
            'xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif" font-size="12">' +
            '<defs>' +
            '<marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">' +
            '<path d="M0,0 L8,3 L0,6 Z" fill="' + INK + '"/></marker>' +
            '<marker id="ahl" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">' +
            '<path d="M0,0 L8,3 L0,6 Z" fill="' + LINK + '"/></marker>' +
            '<marker id="ahw" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">' +
            '<path d="M0,0 L8,3 L0,6 Z" fill="' + WARN + '"/></marker>' +
            '</defs>' + body + '</svg>';
    }
    function wall(x, y1, y2) {   // стенка сосуда — жирная линия со штриховкой
        var s = '<line x1="' + x + '" y1="' + y1 + '" x2="' + x + '" y2="' + y2 + '" stroke="' + INK + '" stroke-width="3"/>';
        for (var y = y1; y < y2; y += 9) {
            s += '<line x1="' + x + '" y1="' + y + '" x2="' + (x + 8) + '" y2="' + (y + 7) + '" stroke="' + SOFT + '" stroke-width="1"/>';
        }
        return s;
    }
    function mol(cx, cy, r, fill) { return '<circle cx="' + cx + '" cy="' + cy + '" r="' + (r || 6) + '" fill="' + (fill || LINK) + '"/>'; }
    function arrow(x1, y1, x2, y2, color, marker) {
        return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" stroke="' + color +
            '" stroke-width="2" marker-end="url(#' + (marker || 'ah') + ')"/>';
    }
    /* Язык страницы. Схемы рисуются одним и тем же кодом на всех языках, поэтому подпись
       переводится здесь, на выходе, а не в 148 местах по файлу. */
    function pageLang() {
        var l = global.B42_LANG ||
                (global.document && global.document.documentElement.getAttribute('lang')) || 'ru';
        return ['ru', 'en', 'es', 'ar', 'fr'].indexOf(l) >= 0 ? l : 'ru';
    }
    function label(s) {
        var lang = pageLang();
        if (lang === 'ru' || typeof s !== 'string') return s;
        var dict = global.B42FigText && global.B42FigText[s];
        return (dict && dict[lang]) || s;
    }

    function txt(x, y, s, color, size, anchor) {
        return '<text x="' + x + '" y="' + y + '" fill="' + (color || INK) + '" font-size="' + (size || 12) +
            '" text-anchor="' + (anchor || 'middle') + '">' + label(s) + '</text>';
    }

    var F = {};

    // 1. Упругий отскок: импульс меняет знак → стенка получает 2mv
    F.bounce = function () {
        var W = 420, H = 150, wx = 330;
        var s = wall(wx, 20, 130);
        s += mol(150, 55, 8);
        s += arrow(165, 55, 300, 55, LINK, 'ahl');
        s += txt(230, 45, '+m·v&#8339;', LINK);
        s += mol(150, 100, 8, WARN);
        s += arrow(300, 100, 165, 100, WARN, 'ahw');
        s += txt(230, 92, '&#8722;m·v&#8339;', WARN);
        s += '<path d="M300,58 Q322,78 300,97" fill="none" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="3,3"/>';
        s += txt(wx + 45, 60, 'стенка', SOFT, 11, 'middle');
        s += txt(wx + 45, 105, '&#916;p = 2m·v&#8339;', INK, 13, 'middle');
        return svg(W, H, s);
    };

    // 2. Цилиндр досягаемости: кто успеет долететь за Δt
    F.cylinder = function () {
        var W = 420, H = 160, wx = 340, x0 = 140;
        var s = '<rect x="' + x0 + '" y="30" width="' + (wx - x0) + '" height="100" fill="' + LINK + '" opacity="0.10" stroke="' + LINK + '" stroke-dasharray="4,3"/>';
        s += wall(wx, 25, 135);
        var pts = [[175, 55], [215, 95], [255, 48], [290, 108], [230, 70], [310, 75], [190, 115]];
        for (var i = 0; i < pts.length; i++) s += mol(pts[i][0], pts[i][1], 5, i % 3 === 2 ? SOFT : LINK);
        s += arrow(x0 + 10, 145, wx - 4, 145, INK);
        s += txt((x0 + wx) / 2, 158, 'v&#8339; · &#916;t', INK, 12);
        s += arrow(x0 - 14, 30, x0 - 14, 130, INK);
        s += txt(x0 - 26, 84, 'A', INK, 13);
        s += txt(60, 60, 'долетят', LINK, 11, 'start');
        s += txt(60, 78, 'за &#916;t', LINK, 11, 'start');
        return svg(W, H, s);
    };

    // 3. Множество ударов складывается в постоянную силу
    F.force = function () {
        var W = 420, H = 150, wx = 250;
        var s = wall(wx, 20, 130);
        for (var i = 0; i < 7; i++) {
            var y = 28 + i * 15;
            s += arrow(150 + (i % 3) * 12, y, wx - 6, y, SOFT);
        }
        s += txt(120, 80, 'много', SOFT, 11, 'end');
        s += txt(120, 96, 'ударов', SOFT, 11, 'end');
        s += '<line x1="' + (wx + 12) + '" y1="75" x2="' + (wx + 30) + '" y2="75" stroke="' + BORD + '" stroke-width="1"/>';
        s += arrow(wx + 34, 75, wx + 120, 75, WARN, 'ahw');
        s += txt(wx + 78, 63, 'F', WARN, 16);
        s += txt(wx + 78, 96, 'постоянная сила', SOFT, 11);
        return svg(W, H, s);
    };

    // 4. Давление = сила на площадь, A сокращается
    F.pressure = function () {
        var W = 420, H = 150;
        var s = '<rect x="120" y="30" width="70" height="90" fill="' + LINK + '" opacity="0.14" stroke="' + LINK + '"/>';
        s += txt(155, 80, 'A', LINK, 15);
        s += arrow(200, 75, 275, 75, WARN, 'ahw');
        s += txt(237, 63, 'F', WARN, 15);
        s += txt(340, 68, 'P = F / A', INK, 17);
        s += txt(340, 92, 'Па = Н / м²', SOFT, 11);
        s += txt(155, 138, 'площадь стенки', SOFT, 11);
        return svg(W, H, s);
    };

    // 5. Три равноправных направления → множитель 1/3
    F.axes = function () {
        var W = 420, H = 160, cx = 160, cy = 90;
        var s = arrow(cx, cy, cx + 85, cy, LINK, 'ahl') + txt(cx + 96, cy + 4, 'x', LINK, 13);
        s += arrow(cx, cy, cx, cy - 65, LINK, 'ahl') + txt(cx, cy - 74, 'y', LINK, 13);
        s += arrow(cx, cy, cx - 55, cy + 45, LINK, 'ahl') + txt(cx - 65, cy + 55, 'z', LINK, 13);
        s += mol(cx, cy, 7, INK);
        s += txt(320, 70, '&#10216;v&#8339;²&#10217; = &#10216;v²&#10217; / 3', INK, 15);
        s += txt(320, 96, 'ни одно направление', SOFT, 11);
        s += txt(320, 112, 'не выделено', SOFT, 11);
        return svg(W, H, s);
    };

    // 6. Определение температуры через среднюю кинетическую энергию
    F.energy = function () {
        var W = 420, H = 150;
        var s = mol(90, 60, 9, LINK) + arrow(103, 60, 150, 60, LINK, 'ahl');
        s += txt(120, 48, 'v', LINK, 12);
        s += txt(90, 95, 'E = m·v² / 2', INK, 13);
        s += '<line x1="185" y1="70" x2="225" y2="70" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="4,3"/>';
        s += txt(205, 58, '=', SOFT, 14);
        // термометр
        var tx = 270;
        s += '<rect x="' + (tx - 6) + '" y="25" width="12" height="80" rx="6" fill="none" stroke="' + SOFT + '" stroke-width="2"/>';
        s += '<rect x="' + (tx - 3) + '" y="55" width="6" height="50" fill="' + WARN + '"/>';
        s += '<circle cx="' + tx + '" cy="112" r="10" fill="' + WARN + '"/>';
        s += txt(tx, 135, 'T', INK, 14);
        s += txt(365, 62, '&#10216;E&#10217; = (3/2)k&#8342;T', INK, 14);
        s += txt(365, 84, 'k&#8342; — курс обмена', SOFT, 11);
        s += txt(365, 100, 'Дж &#8596; К', SOFT, 11);
        return svg(W, H, s);
    };

    // 7. Итог: связь макро- и микромира
    F.result = function () {
        var W = 420, H = 165;
        var s = '<rect x="30" y="30" width="130" height="100" fill="none" stroke="' + INK + '" stroke-width="2" rx="4"/>';
        var pts = [[55, 55], [95, 75], [130, 50], [70, 105], [115, 110], [140, 85], [90, 45]];
        for (var i = 0; i < pts.length; i++) s += mol(pts[i][0], pts[i][1], 4.5, i % 2 ? LINK : WARN);
        s += txt(95, 148, 'микромир: N, m, v', SOFT, 11);
        // манометр
        s += '<path d="M205,95 A35,35 0 0 1 275,95" fill="none" stroke="' + BORD + '" stroke-width="7"/>';
        s += '<path d="M205,95 A35,35 0 0 1 232,62" fill="none" stroke="' + MOSS + '" stroke-width="7"/>';
        s += '<line x1="240" y1="95" x2="222" y2="70" stroke="' + INK + '" stroke-width="2"/>';
        s += '<circle cx="240" cy="95" r="4" fill="' + INK + '"/>';
        s += txt(240, 115, 'P', INK, 13);
        s += txt(240, 148, 'макромир: P, V, T', SOFT, 11);
        s += txt(360, 80, 'PV = nRT', INK, 17);
        s += '<line x1="170" y1="80" x2="196" y2="80" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="3,3"/>';
        s += '<line x1="288" y1="80" x2="312" y2="80" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="3,3"/>';
        return svg(W, H, s);
    };

    // ─────────── Параграф 2: фазовый переход ───────────

    // Нагрев: молекулы ускоряются, столбик термометра растёт
    F.heating = function () {
        var W = 420, H = 130;
        var s = '<rect x="60" y="25" width="110" height="75" fill="none" stroke="' + INK + '" stroke-width="2" rx="3"/>';
        s += '<rect x="63" y="55" width="104" height="42" fill="' + LINK + '" opacity="0.18"/>';
        var pts = [[85, 70], [110, 85], [140, 68], [125, 90], [98, 88]];
        for (var i = 0; i < pts.length; i++) s += mol(pts[i][0], pts[i][1], 4, LINK);
        for (var f = 0; f < 5; f++) s += '<path d="M' + (75 + f * 22) + ',112 q4,-7 0,-13" stroke="' + WARN + '" stroke-width="2" fill="none"/>';
        // термометр
        s += '<rect x="234" y="20" width="11" height="72" rx="5.5" fill="none" stroke="' + SOFT + '" stroke-width="2"/>';
        s += '<rect x="237" y="58" width="5" height="34" fill="' + WARN + '"/>';
        s += '<circle cx="239.5" cy="98" r="8" fill="' + WARN + '"/>';
        s += arrow(262, 60, 262, 32, WARN, 'ahw');
        s += txt(300, 52, 'T растёт', INK, 13, 'start');
        s += txt(300, 74, 'Q = c·m·&#916;T', SOFT, 12, 'start');
        return svg(W, H, s);
    };

    // Кипение: пузырьки и пар, термометр стоит
    F.boiling = function () {
        var W = 420, H = 130;
        var s = '<rect x="60" y="25" width="110" height="75" fill="none" stroke="' + INK + '" stroke-width="2" rx="3"/>';
        s += '<rect x="63" y="62" width="104" height="35" fill="' + LINK + '" opacity="0.18"/>';
        var bub = [[85, 88, 4], [110, 78, 5], [140, 84, 3.5], [125, 70, 4]];
        for (var i = 0; i < bub.length; i++)
            s += '<circle cx="' + bub[i][0] + '" cy="' + bub[i][1] + '" r="' + bub[i][2] + '" fill="none" stroke="' + LINK + '" stroke-width="1.5"/>';
        for (var v = 0; v < 4; v++)
            s += '<circle cx="' + (92 + v * 20) + '" cy="' + (44 - v % 2 * 8) + '" r="' + (5 - v % 2) + '" fill="' + SOFT + '" opacity="0.4"/>';
        for (var f = 0; f < 5; f++) s += '<path d="M' + (75 + f * 22) + ',112 q4,-7 0,-13" stroke="' + WARN + '" stroke-width="2" fill="none"/>';
        s += '<rect x="234" y="20" width="11" height="72" rx="5.5" fill="none" stroke="' + SOFT + '" stroke-width="2"/>';
        s += '<rect x="237" y="40" width="5" height="52" fill="' + WARN + '"/>';
        s += '<circle cx="239.5" cy="98" r="8" fill="' + WARN + '"/>';
        s += '<line x1="256" y1="40" x2="276" y2="40" stroke="' + INK + '" stroke-width="2"/>';
        s += txt(300, 38, 'T стоит', INK, 13, 'start');
        s += txt(300, 60, 'Q = L·m', SOFT, 12, 'start');
        s += txt(300, 78, 'связи рвутся', SOFT, 11, 'start');
        return svg(W, H, s);
    };

    // Сравнение энергий: короткий столбик нагрева против длинного столбика кипения
    function heatbars(highlight) {
        var W = 420, H = 118, x0 = 95, unit = 0.55;
        var s = txt(x0 - 10, 44, 'нагрев', SOFT, 12, 'end');
        s += '<rect x="' + x0 + '" y="30" width="' + (67 * unit) + '" height="18" fill="' + LINK + '" opacity="' + (highlight === 1 ? 1 : 0.35) + '"/>';
        s += txt(x0 + 67 * unit + 10, 44, '67 кДж', INK, 12, 'start');
        s += txt(x0 - 10, 82, 'кипение', SOFT, 12, 'end');
        s += '<rect x="' + x0 + '" y="68" width="' + (452 * unit / 2.6) + '" height="18" fill="' + WARN + '" opacity="' + (highlight === 2 ? 1 : 0.35) + '"/>';
        s += txt(x0 + 452 * unit / 2.6 + 10, 82, '452 кДж', INK, 12, 'start');
        if (highlight === 2) s += txt(210, 108, 'в 6,8 раза больше', WARN, 12);
        return svg(W, H, s);
    }
    F.heatbar1 = function () { return heatbars(1); };
    F.heatbar2 = function () { return heatbars(2); };

    // Равновесие жидкость–пар: пузырёк должен раздвинуть атмосферу
    F.equilibrium = function () {
        var W = 420, H = 150;
        var s = '<rect x="120" y="70" width="170" height="60" fill="' + LINK + '" opacity="0.16"/>';
        s += '<line x1="120" y1="70" x2="290" y2="70" stroke="' + LINK + '" stroke-width="2"/>';
        s += '<circle cx="185" cy="105" r="13" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += txt(185, 109, 'пар', INK, 10);
        for (var i = 0; i < 5; i++) s += arrow(140 + i * 38, 22, 140 + i * 38, 60, SOFT);
        s += txt(205, 16, 'давление атмосферы', SOFT, 11);
        s += arrow(185, 90, 185, 76, MOSS, 'ah');
        s += txt(330, 100, 'пузырёк', INK, 12, 'start');
        s += txt(330, 118, 'раздвигает', SOFT, 11, 'start');
        return svg(W, H, s);
    };

    // Разделение переменных: две части уравнения расходятся
    F.integrate = function () {
        var W = 420, H = 110;
        var s = txt(120, 45, 'dP / P', LINK, 17);
        s += txt(210, 45, '=', INK, 16);
        s += txt(305, 45, '(L/R) · dT / T²', WARN, 17);
        s += '<line x1="70" y1="62" x2="170" y2="62" stroke="' + LINK + '" stroke-width="1.5"/>';
        s += '<line x1="245" y1="62" x2="370" y2="62" stroke="' + WARN + '" stroke-width="1.5"/>';
        s += txt(120, 80, 'только давление', SOFT, 11);
        s += txt(305, 80, 'только температура', SOFT, 11);
        s += txt(210, 95, '&#8747; каждую часть отдельно', INK, 12);
        return svg(W, H, s);
    };

    // Кривая кипения: T(P) — в горах ниже, в скороварке выше
    F.boilcurve = function () {
        var W = 420, H = 165, x0 = 90, y0 = 130, x1 = 350, y1 = 25;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x1 + '" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="' + y1 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M' + x0 + ',115 Q200,75 ' + x1 + ',35" fill="none" stroke="' + LINK + '" stroke-width="2.5"/>';
        s += '<circle cx="130" cy="104" r="4.5" fill="' + MOSS + '"/>';
        s += txt(130, 96, '81&#176;', MOSS, 11);
        s += txt(130, 146, '0,5 атм', SOFT, 10);
        s += '<circle cx="222" cy="72" r="4.5" fill="' + INK + '"/>';
        s += txt(222, 64, '100&#176;', INK, 11);
        s += txt(222, 146, '1 атм', SOFT, 10);
        s += '<circle cx="310" cy="45" r="4.5" fill="' + WARN + '"/>';
        s += txt(310, 37, '121&#176;', WARN, 11);
        s += txt(310, 146, '2 атм', SOFT, 10);
        s += txt(60, 78, 'T', INK, 13);
        s += txt(x1 + 14, y0 + 4, 'P', INK, 13);
        return svg(W, H, s);
    };

    // ─────────── Параграф 3: процессы и двигатель ───────────

    // Первое начало: теплота разделяется на нагрев и работу
    F.firstlaw = function () {
        var W = 420, H = 140;
        var s = arrow(30, 70, 105, 70, WARN, 'ahw') + txt(66, 60, '&#948;Q', WARN, 14);
        s += '<circle cx="130" cy="70" r="22" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += txt(130, 75, 'газ', INK, 11);
        s += arrow(155, 55, 240, 30, LINK, 'ahl') + txt(200, 22, 'dU — нагрев', LINK, 12);
        s += arrow(155, 85, 240, 112, MOSS, 'ah') + txt(205, 130, 'P·dV — работа', MOSS, 12);
        s += '<rect x="285" y="88" width="16" height="40" fill="' + MOSS + '" opacity="0.5"/>';
        s += arrow(305, 108, 350, 108, MOSS, 'ah');
        s += txt(330, 40, 'ничего', SOFT, 11);
        s += txt(330, 56, 'не пропадает', SOFT, 11);
        return svg(W, H, s);
    };

    // Адиабата: сжатие без теплообмена греет газ
    F.adiabatic = function () {
        var W = 420, H = 140;
        var s = '<rect x="55" y="40" width="105" height="60" fill="' + LINK + '" opacity="0.14" stroke="' + INK + '" stroke-width="2"/>';
        for (var i = 0; i < 4; i++) s += mol(75 + i * 25, 55 + (i % 2) * 28, 4, LINK);
        s += txt(107, 118, 'до: 300 K', SOFT, 11);
        s += arrow(175, 70, 215, 70, INK) + txt(195, 60, 'сжали', INK, 11);
        s += '<rect x="235" y="40" width="55" height="60" fill="' + WARN + '" opacity="0.20" stroke="' + INK + '" stroke-width="2"/>';
        for (var j = 0; j < 4; j++) s += mol(248 + (j % 2) * 22, 52 + Math.floor(j / 2) * 30, 4, WARN);
        s += txt(262, 118, 'после: 420 K', WARN, 11);
        s += '<line x1="292" y1="38" x2="292" y2="102" stroke="' + INK + '" stroke-width="4"/>';
        s += txt(360, 58, '&#948;Q = 0', INK, 13);
        s += txt(360, 78, 'тепло', SOFT, 11);
        s += txt(360, 93, 'не уходит', SOFT, 11);
        return svg(W, H, s);
    };

    // Адиабата круче изотермы
    F.curves = function () {
        var W = 420, H = 165, x0 = 80, y0 = 130;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="350" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M100,35 Q170,95 340,118" fill="none" stroke="' + WARN + '" stroke-width="2.5"/>';
        s += txt(250, 90, 'адиабата', WARN, 12, 'start');
        s += txt(250, 106, 'P·V^1,4', WARN, 11, 'start');
        s += '<path d="M100,70 Q180,110 340,126" fill="none" stroke="' + LINK + '" stroke-width="2.5" stroke-dasharray="5,3"/>';
        s += txt(140, 60, 'изотерма P·V', LINK, 12, 'start');
        s += txt(60, 78, 'P', INK, 13);
        s += txt(360, 134, 'V', INK, 13);
        return svg(W, H, s);
    };

    // Замкнутый цикл: площадь петли = работа
    F.cycle = function () {
        var W = 420, H = 170, x0 = 90, y0 = 135;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="330" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M150,110 L150,55 Q200,45 260,80 L260,115 Q205,128 150,110 Z" fill="' + MOSS + '" opacity="0.20" stroke="' + INK + '" stroke-width="2"/>';
        s += txt(205, 95, 'W', INK, 17);
        s += txt(205, 112, 'работа', SOFT, 10);
        s += '<circle cx="150" cy="110" r="4" fill="' + INK + '"/>' + txt(138, 124, '1', SOFT, 10);
        s += '<circle cx="150" cy="55" r="4" fill="' + INK + '"/>' + txt(138, 50, '2', SOFT, 10);
        s += '<circle cx="260" cy="80" r="4" fill="' + INK + '"/>' + txt(273, 74, '3', SOFT, 10);
        s += '<circle cx="260" cy="115" r="4" fill="' + INK + '"/>' + txt(273, 128, '4', SOFT, 10);
        s += txt(70, 78, 'P', INK, 13);
        s += txt(342, 139, 'V', INK, 13);
        s += txt(350, 60, 'площадь', SOFT, 11, 'start');
        s += txt(350, 76, '= работа', SOFT, 11, 'start');
        return svg(W, H, s);
    };

    // Поток теплоты: часть обязана уйти в холодильник
    F.efficiency = function () {
        var W = 420, H = 175;
        var s = '<rect x="40" y="20" width="90" height="34" fill="' + WARN + '" opacity="0.20" stroke="' + WARN + '" stroke-width="1.5"/>';
        s += txt(85, 42, 'нагреватель', WARN, 11);
        s += '<rect x="40" y="122" width="90" height="34" fill="' + LINK + '" opacity="0.20" stroke="' + LINK + '" stroke-width="1.5"/>';
        s += txt(85, 144, 'холодильник', LINK, 11);
        s += arrow(85, 58, 85, 78, WARN, 'ahw') + txt(58, 74, 'Q&#1075;', WARN, 12);
        s += '<circle cx="85" cy="88" r="1" fill="none"/>';
        s += '<rect x="60" y="78" width="50" height="40" fill="none" stroke="' + INK + '" stroke-width="2" rx="3"/>';
        s += txt(85, 103, 'машина', INK, 10);
        s += arrow(85, 118, 85, 120, LINK, 'ahl');
        s += txt(58, 134, 'Q&#1093;', LINK, 12);
        s += arrow(112, 98, 200, 98, MOSS, 'ah') + txt(160, 88, 'W', MOSS, 14);
        s += txt(300, 80, '&#951; = 1 &#8722; Q&#1093;/Q&#1075;', INK, 14);
        s += txt(300, 104, 'Q&#1093; никогда не ноль', SOFT, 11);
        return svg(W, H, s);
    };

    // Теорема Карно: КПД от двух температур
    F.carnot = function () {
        var W = 420, H = 150;
        var s = '<rect x="45" y="25" width="100" height="30" fill="' + WARN + '" opacity="0.18" stroke="' + WARN + '"/>';
        s += txt(95, 45, 'T&#1075;', WARN, 15);
        s += '<rect x="45" y="98" width="100" height="30" fill="' + LINK + '" opacity="0.18" stroke="' + LINK + '"/>';
        s += txt(95, 118, 'T&#1093;', LINK, 15);
        s += arrow(95, 60, 95, 93, SOFT);
        s += txt(190, 70, '&#951; = 1 &#8722;', INK, 16, 'start');
        s += '<line x1="268" y1="70" x2="300" y2="70" stroke="' + INK + '" stroke-width="1.5"/>';
        s += txt(284, 62, 'T&#1093;', LINK, 13);
        s += txt(284, 86, 'T&#1075;', WARN, 13);
        s += txt(330, 108, 'только температуры', SOFT, 11, 'middle');
        s += txt(330, 124, 'никакой конструкции', SOFT, 11, 'middle');
        return svg(W, H, s);
    };

    // ─────────── Механика, параграф 1: кинематика ───────────

    // Система отсчёта: одно движение — два наблюдателя, два верных ответа
    F.frame = function () {
        var W = 420, H = 150;
        var s = '<rect x="60" y="40" width="150" height="46" rx="6" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += '<circle cx="90" cy="92" r="9" fill="none" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<circle cx="180" cy="92" r="9" fill="none" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += mol(135, 63, 6, LINK);
        s += txt(135, 33, 'пассажир', LINK, 11);
        s += arrow(215, 63, 300, 63, INK) + txt(258, 53, '100 км/ч', INK, 11);
        s += '<line x1="30" y1="112" x2="390" y2="112" stroke="' + SOFT + '" stroke-width="1.5"/>';
        for (var i = 0; i < 9; i++) s += '<line x1="' + (40 + i * 42) + '" y1="112" x2="' + (34 + i * 42) + '" y2="122" stroke="' + SOFT + '" stroke-width="1"/>';
        s += mol(330, 100, 6, WARN) + txt(330, 140, 'наблюдатель', WARN, 11);
        s += txt(345, 30, 'v = 0 в вагоне', SOFT, 11);
        s += txt(345, 46, 'v = 100 с перрона', SOFT, 11);
        return svg(W, H, s);
    };

    // Средняя скорость — наклон секущей
    F.secant = function () {
        var W = 420, H = 160, x0 = 70, y0 = 130;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="350" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M' + x0 + ',120 Q170,105 250,60 T340,32" fill="none" stroke="' + LINK + '" stroke-width="2.5"/>';
        s += '<line x1="120" y1="113" x2="290" y2="45" stroke="' + WARN + '" stroke-width="2" stroke-dasharray="5,3"/>';
        s += '<circle cx="120" cy="113" r="4" fill="' + WARN + '"/><circle cx="290" cy="45" r="4" fill="' + WARN + '"/>';
        s += '<line x1="120" y1="113" x2="290" y2="113" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<line x1="290" y1="113" x2="290" y2="45" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(205, 128, '&#916;t', SOFT, 11);
        s += txt(305, 82, '&#916;x', SOFT, 11);
        s += txt(50, 78, 'x', INK, 13);
        s += txt(360, 134, 't', INK, 13);
        s += txt(230, 30, 'секущая', WARN, 11);
        return svg(W, H, s);
    };

    // Предел секущих — касательная, мгновенная скорость
    F.tangent = function () {
        var W = 420, H = 160, x0 = 70, y0 = 130;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="350" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M' + x0 + ',120 Q170,105 250,60 T340,32" fill="none" stroke="' + LINK + '" stroke-width="2.5"/>';
        // семейство секущих, сходящихся к касательной
        s += '<line x1="180" y1="100" x2="300" y2="40" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>';
        s += '<line x1="180" y1="100" x2="260" y2="56" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3" opacity="0.7"/>';
        s += '<line x1="140" y1="112" x2="240" y2="72" stroke="' + MOSS + '" stroke-width="2.5"/>';
        s += '<circle cx="180" cy="100" r="4.5" fill="' + MOSS + '"/>';
        s += txt(255, 92, 'касательная', MOSS, 11, 'start');
        s += txt(255, 108, 'v = dx/dt', MOSS, 12, 'start');
        s += txt(50, 78, 'x', INK, 13);
        s += txt(360, 134, 't', INK, 13);
        return svg(W, H, s);
    };

    // Ускорение — скорость изменения скорости
    F.accel = function () {
        var W = 420, H = 140;
        var s = txt(60, 40, 'x', INK, 13) + arrow(80, 36, 130, 36, SOFT) + txt(105, 26, 'd/dt', SOFT, 10);
        s += txt(150, 40, 'v', MOSS, 15) + arrow(170, 36, 220, 36, SOFT) + txt(195, 26, 'd/dt', SOFT, 10);
        s += txt(240, 40, 'a', WARN, 15);
        s += txt(60, 72, 'м', SOFT, 11) + txt(150, 72, 'м/с', SOFT, 11) + txt(240, 72, 'м/с²', SOFT, 11);
        s += txt(330, 46, 'каждая ступень —', SOFT, 11);
        s += txt(330, 62, 'деление на время', SOFT, 11);
        s += txt(210, 108, 'a = скорость изменения скорости', INK, 12);
        return svg(W, H, s);
    };

    // График скорости при постоянном ускорении — прямая
    F.vline = function () {
        var W = 420, H = 160, x0 = 80, y0 = 130;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="340" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="100" x2="320" y2="40" stroke="' + MOSS + '" stroke-width="2.5"/>';
        s += '<circle cx="' + x0 + '" cy="100" r="4" fill="' + MOSS + '"/>';
        s += txt(x0 - 16, 104, 'v&#8320;', MOSS, 12);
        s += '<line x1="220" y1="70" x2="290" y2="70" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
        s += '<line x1="290" y1="70" x2="290" y2="49" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
        s += txt(310, 64, 'a', WARN, 12);
        s += txt(60, 78, 'v', INK, 13);
        s += txt(352, 134, 't', INK, 13);
        s += txt(200, 150, 'наклон прямой = ускорение', SOFT, 11);
        return svg(W, H, s);
    };

    // Путь как площадь под графиком скорости: прямоугольник + треугольник
    F.area = function () {
        var W = 420, H = 170, x0 = 80, y0 = 130, xe = 280;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="340" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<rect x="' + x0 + '" y="95" width="' + (xe - x0) + '" height="35" fill="' + LINK + '" opacity="0.22"/>';
        s += '<path d="M' + x0 + ',95 L' + xe + ',95 L' + xe + ',45 Z" fill="' + WARN + '" opacity="0.22"/>';
        s += '<line x1="' + x0 + '" y1="95" x2="' + xe + '" y2="45" stroke="' + MOSS + '" stroke-width="2.5"/>';
        s += txt((x0 + xe) / 2, 118, 'v&#8320;·t', LINK, 12);
        s += txt(240, 78, '&#189;·at²', WARN, 12);
        s += txt(60, 78, 'v', INK, 13);
        s += txt(352, 134, 't', INK, 13);
        s += txt(210, 158, 'площадь трапеции = перемещение', SOFT, 11);
        return svg(W, H, s);
    };

    // Итог: координата — парабола
    F.parabola = function () {
        var W = 420, H = 165, x0 = 80, y0 = 132;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="345" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="25" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M' + x0 + ',120 Q200,110 335,35" fill="none" stroke="' + LINK + '" stroke-width="2.5"/>';
        s += '<line x1="' + x0 + '" y1="120" x2="240" y2="97" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="4,3"/>';
        s += txt(175, 92, 'v&#8320;t — равномерная часть', SOFT, 10, 'start');
        s += '<path d="M240,97 L240,70" stroke="' + WARN + '" stroke-width="1.5"/>';
        s += txt(250, 78, 'at²/2', WARN, 11, 'start');
        s += txt(60, 78, 'x', INK, 13);
        s += txt(357, 136, 't', INK, 13);
        return svg(W, H, s);
    };

    // ─────────── Механика, параграф 2: законы Ньютона ───────────

    // Инерция: без сил скорость не меняется
    F.inertia = function () {
        var W = 420, H = 140, y = 80;
        var s = '<line x1="20" y1="' + (y + 20) + '" x2="400" y2="' + (y + 20) + '" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="4,4"/>';
        var xs = [70, 170, 270, 350];
        for (var i = 0; i < xs.length; i++) {
            s += '<rect x="' + (xs[i] - 16) + '" y="' + (y - 14) + '" width="32" height="22" rx="3" fill="none" stroke="' + INK + '" stroke-width="' + (i === 3 ? 2 : 1.2) + '" opacity="' + (i === 3 ? 1 : 0.45) + '"/>';
        }
        s += arrow(370, y - 3, 400, y - 3, MOSS, 'ah');
        s += txt(385, y - 12, 'v', MOSS, 12);
        s += txt(210, 30, 'сил нет — скорость постоянна', SOFT, 12);
        s += txt(210, 128, 'равные промежутки за равное время', SOFT, 11);
        return svg(W, H, s);
    };

    // Сила вдвое больше — ускорение вдвое больше
    F.forceprop = function () {
        var W = 420, H = 150;
        function row(yy, flen, label, alen) {
            var s = '<rect x="70" y="' + (yy - 13) + '" width="34" height="24" rx="3" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
            s += arrow(108, yy, 108 + flen, yy, LINK, 'ahl');
            s += txt(108 + flen / 2, yy - 8, label, LINK, 11);
            s += '<line x1="230" y1="' + yy + '" x2="250" y2="' + yy + '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
            s += arrow(258, yy, 258 + alen, yy, WARN, 'ahw');
            s += txt(258 + alen / 2, yy - 8, 'a', WARN, 11);
            return s;
        }
        var s = row(48, 40, 'F', 34) + row(110, 80, '2F', 68);
        s += txt(210, 138, 'вдвое большая сила — вдвое большее ускорение', SOFT, 11);
        return svg(W, H, s);
    };

    // Одна сила, разная масса — разное ускорение
    F.massprop = function () {
        var W = 420, H = 150;
        function row(yy, bw, mlabel, alen) {
            var s = '<rect x="70" y="' + (yy - bw / 2.6) + '" width="' + bw + '" height="' + (bw / 1.3) + '" rx="3" fill="' + LINK + '" opacity="0.16"/>';
            s += '<rect x="70" y="' + (yy - bw / 2.6) + '" width="' + bw + '" height="' + (bw / 1.3) + '" rx="3" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
            s += txt(70 + bw / 2, yy + 4, mlabel, INK, 11);
            s += arrow(72 + bw, yy, 72 + bw + 50, yy, LINK, 'ahl');
            s += txt(72 + bw + 25, yy - 8, 'F', LINK, 11);
            s += '<line x1="245" y1="' + yy + '" x2="262" y2="' + yy + '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
            s += arrow(270, yy, 270 + alen, yy, WARN, 'ahw');
            s += txt(270 + alen / 2, yy - 8, 'a', WARN, 11);
            return s;
        }
        var s = row(45, 30, 'm', 70) + row(108, 55, '2m', 35);
        s += txt(210, 140, 'та же сила: вдвое тяжелее — вдвое медленнее разгон', SOFT, 11);
        return svg(W, H, s);
    };

    // Второй закон: a = F/m
    F.secondlaw = function () {
        var W = 420, H = 130;
        var s = txt(120, 55, 'a', WARN, 24) + txt(155, 55, '=', INK, 20);
        s += txt(200, 42, 'F', LINK, 22);
        s += '<line x1="180" y1="52" x2="222" y2="52" stroke="' + INK + '" stroke-width="1.8"/>';
        s += txt(200, 78, 'm', INK, 22);
        s += txt(310, 42, 'больше сила →', SOFT, 11, 'start');
        s += txt(310, 58, 'быстрее разгон', SOFT, 11, 'start');
        s += txt(310, 80, 'больше масса →', SOFT, 11, 'start');
        s += txt(310, 96, 'медленнее разгон', SOFT, 11, 'start');
        s += txt(150, 112, '1 Н = 1 кг · 1 м/с²', SOFT, 11);
        return svg(W, H, s);
    };

    // Сила как скорость изменения импульса — ракета теряет массу
    F.impulse = function () {
        var W = 420, H = 145;
        var s = '<path d="M120,70 L155,55 L155,85 Z" fill="' + INK + '" opacity="0.75"/>';
        s += '<rect x="80" y="58" width="42" height="24" rx="4" fill="none" stroke="' + INK + '" stroke-width="1.8"/>';
        for (var i = 0; i < 5; i++) {
            s += '<circle cx="' + (70 - i * 12) + '" cy="' + (70 + (i % 2 ? -5 : 5)) + '" r="' + (5 - i * 0.6) + '" fill="' + WARN + '" opacity="' + (0.5 - i * 0.08) + '"/>';
        }
        s += arrow(160, 70, 215, 70, MOSS, 'ah');
        s += txt(188, 60, 'v ↑', MOSS, 12);
        s += txt(60, 110, 'масса уходит назад', SOFT, 11, 'start');
        s += txt(300, 58, 'F = dp/dt', INK, 15);
        s += txt(300, 80, 'верно даже когда', SOFT, 11);
        s += txt(300, 96, 'масса меняется', SOFT, 11);
        return svg(W, H, s);
    };

    // Третий закон: пара сил на разных телах
    F.action = function () {
        var W = 420, H = 150;
        var s = '<circle cx="140" cy="70" r="26" fill="' + LINK + '" opacity="0.18"/>';
        s += '<circle cx="140" cy="70" r="26" fill="none" stroke="' + INK + '" stroke-width="1.8"/>';
        s += txt(140, 75, 'A', INK, 15);
        s += '<circle cx="280" cy="70" r="26" fill="' + WARN + '" opacity="0.18"/>';
        s += '<circle cx="280" cy="70" r="26" fill="none" stroke="' + INK + '" stroke-width="1.8"/>';
        s += txt(280, 75, 'B', INK, 15);
        s += arrow(168, 58, 250, 58, LINK, 'ahl');
        s += txt(209, 48, 'F<tspan baseline-shift="sub" font-size="8">A→B</tspan>', LINK, 11);
        s += arrow(252, 84, 170, 84, WARN, 'ahw');
        s += txt(211, 100, 'F<tspan baseline-shift="sub" font-size="8">B→A</tspan>', WARN, 11);
        s += txt(210, 128, 'равны по величине, приложены к РАЗНЫМ телам', SOFT, 11);
        return svg(W, H, s);
    };

    // Сохранение импульса как следствие третьего закона
    F.momentum = function () {
        var W = 420, H = 145;
        var s = '<rect x="60" y="30" width="300" height="80" rx="8" fill="none" stroke="' + SOFT + '" stroke-width="1.5" stroke-dasharray="5,4"/>';
        s += txt(210, 24, 'замкнутая система', SOFT, 11);
        s += mol(140, 70, 13, LINK) + txt(140, 75, 'A', '#fff', 11);
        s += mol(280, 70, 13, WARN) + txt(280, 75, 'B', '#fff', 11);
        s += arrow(156, 62, 196, 62, LINK, 'ahl');
        s += arrow(264, 78, 224, 78, WARN, 'ahw');
        s += '<line x1="200" y1="55" x2="220" y2="85" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="220" y1="55" x2="200" y2="85" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += txt(210, 130, 'внутренние силы гасятся → Σp = const', INK, 12);
        return svg(W, H, s);
    };

    // ─────────── Механика, параграф 3: законы сохранения ───────────

    // Работа силы на пути
    F.work = function () {
        var W = 420, H = 140, y = 78;
        var s = '<line x1="60" y1="' + (y + 22) + '" x2="360" y2="' + (y + 22) + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<rect x="80" y="' + (y - 16) + '" width="30" height="28" rx="3" fill="none" stroke="' + INK + '" stroke-width="1.5" opacity="0.4"/>';
        s += '<rect x="260" y="' + (y - 16) + '" width="30" height="28" rx="3" fill="none" stroke="' + INK + '" stroke-width="1.8"/>';
        s += arrow(292, y, 340, y, LINK, 'ahl') + txt(316, y - 10, 'F', LINK, 12);
        s += '<line x1="95" y1="' + (y + 30) + '" x2="275" y2="' + (y + 30) + '" stroke="' + MOSS + '" stroke-width="1.5"/>';
        s += '<line x1="95" y1="' + (y + 26) + '" x2="95" y2="' + (y + 34) + '" stroke="' + MOSS + '" stroke-width="1.5"/>';
        s += '<line x1="275" y1="' + (y + 26) + '" x2="275" y2="' + (y + 34) + '" stroke="' + MOSS + '" stroke-width="1.5"/>';
        s += txt(185, y + 46, 'dx', MOSS, 12);
        s += txt(210, 26, 'A = F · dx', INK, 14);
        return svg(W, H, s);
    };

    // Кинетическая энергия: квадратичный рост
    F.kinetic = function () {
        var W = 420, H = 155, x0 = 80, y0 = 125;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="350" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="22" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M' + x0 + ',' + y0 + ' Q230,118 330,30" fill="none" stroke="' + WARN + '" stroke-width="2.5"/>';
        s += '<line x1="160" y1="' + y0 + '" x2="160" y2="110" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
        s += '<line x1="245" y1="' + y0 + '" x2="245" y2="78" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
        s += txt(160, y0 + 15, 'v', SOFT, 11) + txt(245, y0 + 15, '2v', SOFT, 11);
        s += txt(300, 100, '×4', WARN, 13);
        s += txt(60, 72, 'E', INK, 13);
        s += txt(362, 129, 'v', INK, 13);
        s += txt(215, 40, 'E = mv²/2', INK, 13);
        return svg(W, H, s);
    };

    // Упругий и неупругий удар
    F.elastic = function () {
        var W = 420, H = 165;
        function pair(yy, label, sep, colr2) {
            var s = mol(110, yy, 13, LINK) + mol(110 + sep, yy, 11, colr2);
            s += arrow(126, yy - 22, 156, yy - 22, LINK, 'ahl');
            if (sep > 40) s += arrow(110 + sep + 14, yy - 22, 110 + sep + 44, yy - 22, WARN, 'ahw');
            s += txt(60, yy + 4, label, SOFT, 11, 'end');
            return s;
        }
        var s = pair(45, 'упругий', 120, WARN);
        s += txt(330, 45, 'разлетелись,', SOFT, 10, 'start');
        s += txt(330, 59, 'E сохранилась', MOSS, 10, 'start');
        s += mol(130, 118, 13, LINK) + mol(150, 118, 11, WARN);
        s += arrow(166, 96, 190, 96, SOFT, 'ah');
        s += txt(60, 122, 'неупругий', SOFT, 11, 'end');
        s += txt(330, 112, 'слиплись,', SOFT, 10, 'start');
        s += txt(330, 126, 'часть E → тепло', WARN, 10, 'start');
        s += txt(210, 155, 'импульс сохраняется в обоих случаях', INK, 11);
        return svg(W, H, s);
    };

    // Теорема Нётер: симметрия ↔ закон сохранения
    F.noether = function () {
        var W = 420, H = 160;
        function row(yy, sym, law) {
            var s = txt(120, yy, sym, INK, 12, 'end');
            s += arrow(132, yy - 4, 210, yy - 4, MOSS, 'ah');
            s += txt(225, yy, law, MOSS, 12, 'start');
            return s;
        }
        var s = row(45, 'сдвиг в пространстве', 'импульс');
        s += row(80, 'сдвиг во времени', 'энергия');
        s += row(115, 'поворот', 'момент импульса');
        s += txt(210, 145, 'симметрия рождает закон сохранения', SOFT, 11);
        return svg(W, H, s);
    };

    // ─────────── Колебания, параграф 1: вращение и системы отсчёта ───────────

    // Скорость по касательной непрерывно поворачивается
    F.circmotion = function () {
        var W = 420, H = 175, cx = 150, cy = 88, r = 52;
        var s = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD + '" stroke-width="1.5" stroke-dasharray="4,3"/>';
        var angs = [0, 1.6, 3.2, 4.8];
        for (var i = 0; i < angs.length; i++) {
            var a = angs[i], px = cx + Math.cos(a) * r, py = cy + Math.sin(a) * r;
            var op = i === 0 ? 1 : 0.35;
            s += '<circle cx="' + px + '" cy="' + py + '" r="6" fill="' + LINK + '" opacity="' + op + '"/>';
            var tx = -Math.sin(a) * 32, ty = Math.cos(a) * 32;
            s += '<line x1="' + px + '" y1="' + py + '" x2="' + (px + tx) + '" y2="' + (py + ty) + '" stroke="' + MOSS + '" stroke-width="2" opacity="' + op + '" marker-end="url(#ah)"/>';
        }
        s += txt(cx, cy + 4, '·', SOFT, 14);
        s += txt(300, 62, 'величина v', SOFT, 11, 'start');
        s += txt(300, 78, 'постоянна,', SOFT, 11, 'start');
        s += txt(300, 96, 'направление', MOSS, 11, 'start');
        s += txt(300, 112, 'меняется', MOSS, 11, 'start');
        s += txt(150, 165, 'значит есть ускорение', INK, 12);
        return svg(W, H, s);
    };

    // Подобие треугольников: скоростей и радиусов
    F.vectriangle = function () {
        var W = 420, H = 160;
        var s = '<line x1="60" y1="120" x2="130" y2="55" stroke="' + INK + '" stroke-width="2"/>';
        s += '<line x1="60" y1="120" x2="145" y2="95" stroke="' + INK + '" stroke-width="2"/>';
        s += '<line x1="130" y1="55" x2="145" y2="95" stroke="' + WARN + '" stroke-width="2"/>';
        s += txt(85, 78, 'R', INK, 12) + txt(115, 122, 'R', INK, 12);
        s += txt(152, 72, '&#916;r', WARN, 11, 'start');
        s += txt(100, 145, 'треугольник радиусов', SOFT, 10);
        s += '<line x1="250" y1="120" x2="320" y2="55" stroke="' + MOSS + '" stroke-width="2"/>';
        s += '<line x1="250" y1="120" x2="335" y2="95" stroke="' + MOSS + '" stroke-width="2"/>';
        s += '<line x1="320" y1="55" x2="335" y2="95" stroke="' + WARN + '" stroke-width="2"/>';
        s += txt(275, 78, 'v', MOSS, 12) + txt(305, 122, 'v', MOSS, 12);
        s += txt(342, 72, '&#916;v', WARN, 11, 'start');
        s += txt(292, 145, 'треугольник скоростей', SOFT, 10);
        s += txt(210, 30, '&#916;v / v = &#916;r / R', INK, 13);
        return svg(W, H, s);
    };

    // Ускорение строго к центру
    F.centripetal = function () {
        var W = 420, H = 170, cx = 160, cy = 88, r = 55;
        var s = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD + '" stroke-width="1.5" stroke-dasharray="4,3"/>';
        var px = cx + r, py = cy;
        s += mol(px, py, 8, LINK);
        s += arrow(px, py, px - 42, py, WARN, 'ahw') + txt(px - 21, py - 8, 'a', WARN, 12);
        s += arrow(px, py, px, py - 40, MOSS, 'ah') + txt(px + 12, py - 26, 'v', MOSS, 12);
        s += '<path d="M' + (px - 14) + ',' + (py - 14) + ' L' + (px - 14) + ',' + py + ' L' + px + ',' + py + '" fill="none" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(cx, cy + 4, '+', SOFT, 12);
        s += txt(310, 74, 'a &#8869; v', INK, 13, 'start');
        s += txt(310, 92, 'всегда к центру', SOFT, 11, 'start');
        s += txt(160, 158, 'a = v²/R', INK, 13);
        return svg(W, H, s);
    };

    // Квадратичный рост с частотой
    F.omega = function () {
        var W = 420, H = 150, x0 = 80, y0 = 118;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="350" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="22" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<path d="M' + x0 + ',' + y0 + ' Q220,108 330,28" fill="none" stroke="' + WARN + '" stroke-width="2.5"/>';
        s += '<line x1="170" y1="' + y0 + '" x2="170" y2="103" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
        s += '<line x1="250" y1="' + y0 + '" x2="250" y2="68" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,2"/>';
        s += txt(170, y0 + 14, '&#969;', SOFT, 11) + txt(250, y0 + 14, '2&#969;', SOFT, 11);
        s += txt(300, 92, '×4', WARN, 13);
        s += txt(58, 70, 'a', INK, 13);
        s += txt(215, 40, 'a = &#969;²R', INK, 13);
        return svg(W, H, s);
    };

    // Инерциальная система: реальная сила
    F.inertialframe = function () {
        var W = 420, H = 165, cx = 130, cy = 82, r = 48;
        var s = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD + '" stroke-width="1.5"/>';
        s += '<line x1="' + cx + '" y1="' + cy + '" x2="' + (cx + r) + '" y2="' + cy + '" stroke="#8F6417" stroke-width="2"/>';
        s += mol(cx + r, cy, 8, LINK);
        s += arrow(cx + r, cy, cx + r - 34, cy, WARN, 'ahw') + txt(cx + r - 17, cy - 8, 'T', WARN, 11);
        s += arrow(cx + r, cy, cx + r, cy - 34, MOSS, 'ah') + txt(cx + r + 12, cy - 22, 'v', MOSS, 11);
        s += mol(60, 140, 7, SOFT) + txt(60, 158, 'наблюдатель стоит', SOFT, 9);
        s += txt(280, 62, 'сила есть,', INK, 12, 'start');
        s += txt(280, 80, 'ускорение есть,', INK, 12, 'start');
        s += txt(280, 98, 'F = ma сходится', MOSS, 12, 'start');
        return svg(W, H, s);
    };

    // Вращающаяся система: сила инерции
    F.rotframe = function () {
        var W = 420, H = 165, cx = 130, cy = 82, r = 48;
        var s = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD + '" stroke-width="1.5"/>';
        s += '<line x1="' + cx + '" y1="' + cy + '" x2="' + (cx + r) + '" y2="' + cy + '" stroke="#8F6417" stroke-width="2"/>';
        s += mol(cx + r, cy, 8, LINK);
        s += arrow(cx + r, cy, cx + r - 34, cy, WARN, 'ahw') + txt(cx + r - 17, cy - 9, 'T', WARN, 11);
        s += arrow(cx + r, cy, cx + r + 34, cy, '#8F6417', 'ah') + txt(cx + r + 17, cy - 9, 'F', '#8F6417', 11);
        s += mol(cx, cy - 62, 7, SOFT) + txt(cx, cy - 74, 'наблюдатель вращается', SOFT, 9);
        s += txt(280, 62, 'тело покоится,', INK, 12, 'start');
        s += txt(280, 80, 'силы уравновешены —', INK, 12, 'start');
        s += txt(280, 98, 'но откуда F?', '#8F6417', 12, 'start');
        return svg(W, H, s);
    };

    // Сила инерции — плата за выбор системы
    F.fictitious = function () {
        var W = 420, H = 150;
        var s = '<rect x="55" y="40" width="120" height="62" rx="6" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += mol(115, 74, 10, LINK);
        s += arrow(178, 71, 226, 71, INK) + txt(202, 61, 'a', INK, 12);
        s += txt(115, 118, 'кабина ускоряется', SOFT, 10);
        s += arrow(115, 74, 78, 74, '#8F6417', 'ah');
        s += txt(92, 64, 'F', '#8F6417', 11);
        s += txt(300, 58, 'F = −ma', INK, 14, 'start');
        s += txt(300, 78, 'нет источника,', SOFT, 11, 'start');
        s += txt(300, 94, 'нет пары по', SOFT, 11, 'start');
        s += txt(300, 110, 'третьему закону', SOFT, 11, 'start');
        return svg(W, H, s);
    };

    // ─────────── Колебания, параграф 2: закон Гука и осциллятор ───────────

    // Пружина: сила против смещения
    F.springlaw = function () {
        var W = 420, H = 150, y = 70;
        function spring(x0, x1, yy) {
            var s = '', coils = 7;
            s += '<path d="M' + x0 + ',' + yy;
            for (var c = 1; c <= coils; c++) {
                var xx = x0 + (x1 - x0) * c / (coils + 0.5);
                s += ' L' + xx + ',' + (yy + (c % 2 ? -8 : 8));
            }
            s += ' L' + x1 + ',' + yy + '" fill="none" stroke="' + LINK + '" stroke-width="2"/>';
            return s;
        }
        var s = '<line x1="60" y1="' + (y - 24) + '" x2="60" y2="' + (y + 24) + '" stroke="' + INK + '" stroke-width="2.5"/>';
        s += spring(60, 200, y);
        s += '<rect x="200" y="' + (y - 14) + '" width="28" height="28" rx="3" fill="none" stroke="' + INK + '" stroke-width="1.8"/>';
        s += '<line x1="160" y1="' + (y + 40) + '" x2="160" y2="' + (y + 52) + '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="2,3"/>';
        s += arrow(160, y + 46, 214, y + 46, SOFT) + txt(187, y + 60, 'x', SOFT, 11);
        s += arrow(214, y, 168, y, WARN, 'ahw') + txt(190, y - 10, 'F = −kx', WARN, 12);
        s += txt(320, y - 4, 'оттянули вправо —', SOFT, 11, 'start');
        s += txt(320, y + 12, 'тянет влево', WARN, 11, 'start');
        return svg(W, H, s);
    };

    // Косинус при двойном дифференцировании
    F.sinederiv = function () {
        var W = 420, H = 140;
        var s = txt(80, 60, 'cos', INK, 15);
        s += arrow(105, 56, 155, 56, SOFT) + txt(130, 44, 'd/dt', SOFT, 9);
        s += txt(190, 60, '−sin', MOSS, 15);
        s += arrow(222, 56, 272, 56, SOFT) + txt(247, 44, 'd/dt', SOFT, 9);
        s += txt(310, 60, '−cos', WARN, 15);
        s += '<path d="M310,72 Q195,120 90,72" fill="none" stroke="' + BORD + '" stroke-width="1.2" stroke-dasharray="4,3"/>';
        s += txt(200, 112, 'дважды продифференцировали — вернулись с минусом', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Подстановка: амплитуда сокращается, частота фиксируется
    F.matchfreq = function () {
        var W = 420, H = 130;
        var s = txt(140, 45, '−A&#969;²cos&#969;t = −(k/m)·A cos&#969;t', INK, 13);
        s += '<line x1="88" y1="58" x2="103" y2="58" stroke="' + WARN + '" stroke-width="2"/>';
        s += '<line x1="238" y1="58" x2="253" y2="58" stroke="' + WARN + '" stroke-width="2"/>';
        s += txt(170, 78, 'A сокращается', WARN, 11);
        s += txt(320, 60, '&#969;² = k/m', MOSS, 14, 'start');
        s += txt(210, 112, 'уравнению всё равно, как сильно качнули', SOFT, 11);
        return svg(W, H, s);
    };

    // Изохронизм: разные амплитуды — один период
    F.isochron = function () {
        var W = 420, H = 165, x0 = 70, y0 = 82;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="360" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<path d="M' + x0 + ',' + y0 + ' ';
        for (var i = 0; i <= 100; i++) { s += 'L' + (x0 + i * 2.8) + ',' + (y0 - 48 * Math.cos(i * 0.126)) + ' '; }
        s += '" fill="none" stroke="' + LINK + '" stroke-width="2.2"/>';
        s += '<path d="M' + x0 + ',' + y0 + ' ';
        for (var j = 0; j <= 100; j++) { s += 'L' + (x0 + j * 2.8) + ',' + (y0 - 20 * Math.cos(j * 0.126)) + ' '; }
        s += '" fill="none" stroke="' + WARN + '" stroke-width="2.2"/>';
        s += '<line x1="' + (x0 + 140) + '" y1="24" x2="' + (x0 + 140) + '" y2="140" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += txt(x0 + 140, 152, 'T — общий', INK, 11);
        s += txt(360, 40, 'большая A', LINK, 10, 'start');
        s += txt(360, 68, 'малая A', WARN, 10, 'start');
        return svg(W, H, s);
    };

    // Тень колеса = колебание
    F.shadow = function () {
        var W = 420, H = 170, cx = 120, cy = 78, r = 44;
        var s = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD + '" stroke-width="1.5"/>';
        var ang = 0.8, px = cx + Math.cos(ang) * r, py = cy - Math.sin(ang) * r;
        s += '<line x1="' + cx + '" y1="' + cy + '" x2="' + px + '" y2="' + py + '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += mol(px, py, 6, '#8F6417');
        s += arrow(cx + r + 14, cy - 40, cx + r + 14, cy + 40, SOFT);
        // «луч света» и тень на стене
        s += '<line x1="' + px + '" y1="' + py + '" x2="330" y2="' + py + '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="2,4"/>';
        s += '<line x1="330" y1="26" x2="330" y2="132" stroke="' + INK + '" stroke-width="2.5"/>';
        s += mol(330, py, 6, WARN);
        s += txt(348, py + 4, 'тень', WARN, 11, 'start');
        s += txt(120, 146, 'точка вращается', SOFT, 10.5);
        s += txt(330, 152, 'тень колеблется', SOFT, 10.5);
        s += txt(228, 20, 'x = A cos &#969;t', INK, 12);
        return svg(W, H, s);
    };

    // Перекачка энергии
    F.energyswap = function () {
        var W = 420, H = 150;
        function bar(x, kin, label) {
            var h = 64, s2 = '';
            s2 += '<rect x="' + x + '" y="40" width="26" height="' + h + '" fill="none" stroke="' + BORD + '" stroke-width="1.2"/>';
            s2 += '<rect x="' + x + '" y="' + (40 + h * (1 - kin)) + '" width="26" height="' + (h * kin) + '" fill="' + MOSS + '" opacity="0.75"/>';
            s2 += '<rect x="' + x + '" y="40" width="26" height="' + (h * (1 - kin)) + '" fill="#8F6417" opacity="0.55"/>';
            s2 += txt(x + 13, 122, label, SOFT, 10);
            return s2;
        }
        var s = bar(80, 0, 'край') + bar(160, 0.5, '') + bar(240, 1, 'центр') + bar(320, 0.5, '');
        s += txt(60, 30, 'зелёное — движение, охра — пружина', SOFT, 10.5, 'start');
        s += txt(210, 146, 'сумма всегда одна: E = kA²/2', INK, 12);
        return svg(W, H, s);
    };

    // Любая яма вблизи дна — парабола
    F.anywell = function () {
        var W = 420, H = 165, y0 = 130;
        var s = '<path d="M60,40 C110,150 150,120 210,110 C270,100 310,55 360,30" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        // касательная парабола у минимума (~x=118)
        s += '<path d="M78,110 Q118,152 158,110" fill="none" stroke="' + WARN + '" stroke-width="2.2" stroke-dasharray="5,3"/>';
        s += mol(118, 129, 5, LINK);
        s += txt(118, 152, 'у дна — парабола', WARN, 11);
        s += txt(300, 120, 'сложная яма', SOFT, 11);
        s += txt(210, 22, 'значит внутри спрятана пружина', INK, 12);
        return svg(W, H, s);
    };

    // Момент импульса: плечо имеет значение
    F.angmom = function () {
        var W = 420, H = 165, cx = 145, cy = 85;
        var s = '<circle cx="' + cx + '" cy="' + cy + '" r="58" fill="none" stroke="' + BORD + '" stroke-width="1.2" stroke-dasharray="4,3"/>';
        s += mol(cx, cy, 4, INK);
        var px = cx + 58, py = cy;
        s += mol(px, py, 8, LINK);
        s += '<line x1="' + cx + '" y1="' + cy + '" x2="' + px + '" y2="' + py + '" stroke="' + WARN + '" stroke-width="2"/>';
        s += txt((cx + px) / 2, cy + 16, 'r', WARN, 12);
        s += arrow(px, py, px, py - 44, MOSS, 'ah') + txt(px + 14, py - 30, 'p', MOSS, 12);
        s += '<path d="M' + (px - 16) + ',' + (py - 16) + ' L' + (px - 16) + ',' + py + ' L' + px + ',' + py + '" fill="none" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(320, 66, 'L = r · p', INK, 14, 'start');
        s += txt(320, 88, 'дальше от оси —', SOFT, 11, 'start');
        s += txt(320, 104, 'больше момент', SOFT, 11, 'start');
        s += txt(145, 158, 'момент импульса учитывает плечо', SOFT, 11);
        return svg(W, H, s);
    };

    // Фигуристка: прижала руки — закрутилась быстрее
    F.skater = function () {
        var W = 420, H = 165;
        function figure(x, armLen, speedArcs, label) {
            var s2 = '<circle cx="' + x + '" cy="42" r="9" fill="none" stroke="' + INK + '" stroke-width="1.8"/>';
            s2 += '<line x1="' + x + '" y1="51" x2="' + x + '" y2="100" stroke="' + INK + '" stroke-width="1.8"/>';
            s2 += '<line x1="' + (x - armLen) + '" y1="66" x2="' + (x + armLen) + '" y2="66" stroke="' + LINK + '" stroke-width="2.5"/>';
            s2 += '<line x1="' + x + '" y1="100" x2="' + (x - 10) + '" y2="124" stroke="' + INK + '" stroke-width="1.8"/>';
            s2 += '<line x1="' + x + '" y1="100" x2="' + (x + 10) + '" y2="124" stroke="' + INK + '" stroke-width="1.8"/>';
            for (var i = 0; i < speedArcs; i++) {
                var rr = 30 + i * 9;
                s2 += '<path d="M' + (x - rr) + ',132 A' + rr + ',' + (rr * 0.28) + ' 0 0 0 ' + (x + rr) + ',132" fill="none" stroke="' + MOSS + '" stroke-width="1.4" opacity="' + (0.85 - i * 0.2) + '"/>';
            }
            s2 += txt(x, 152, label, SOFT, 10.5);
            return s2;
        }
        var s = figure(115, 40, 1, 'руки раскинуты: I большой, ω малая');
        s += figure(300, 12, 3, 'руки прижаты: I малый, ω большая');
        s += arrow(185, 80, 235, 80, INK) + txt(210, 70, 'I&#969; = const', INK, 12);
        return svg(W, H, s);
    };

    // Трение покоя подстраивается под силу — до порога срыва
    F.friction = function () {
        var W = 420, H = 160, x0 = 70, y0 = 128;
        var s = '<line x1="' + x0 + '" y1="' + y0 + '" x2="350" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="24" stroke="' + SOFT + '" stroke-width="1.5"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="200" y2="48" stroke="' + WARN + '" stroke-width="2.5"/>';
        s += '<line x1="200" y1="60" x2="340" y2="60" stroke="' + WARN + '" stroke-width="2.5"/>';
        s += '<circle cx="200" cy="48" r="4" fill="' + WARN + '"/>';
        s += '<line x1="200" y1="48" x2="200" y2="' + y0 + '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += txt(200, y0 + 15, 'срыв', SOFT, 10);
        s += txt(130, 60, 'покоя', WARN, 11);
        s += txt(280, 50, 'скольжения', WARN, 11);
        s += txt(52, 76, 'F', INK, 12) + txt(362, 132, 'тяга', INK, 11);
        return svg(W, H, s);
    };

    // Реальный контакт — микровыступы, а не вся площадь
    F.microcontact = function () {
        var W = 420, H = 150;
        function block(x, w, yy) {
            var s2 = '<rect x="' + x + '" y="' + (yy - 26) + '" width="' + w + '" height="24" fill="' + LINK + '" opacity="0.16" stroke="' + INK + '" stroke-width="1.6"/>';
            s2 += '<path d="M' + x + ',' + yy;
            for (var i = 0; i <= w; i += 6) s2 += ' L' + (x + i) + ',' + (yy + (i % 12 ? 0 : 5));
            s2 += '" fill="none" stroke="' + INK + '" stroke-width="1.2"/>';
            s2 += '<line x1="' + (x - 6) + '" y1="' + (yy + 9) + '" x2="' + (x + w + 6) + '" y2="' + (yy + 9) + '" stroke="' + SOFT + '" stroke-width="1.5"/>';
            for (var k = 0; k <= w; k += 12) s2 += '<circle cx="' + (x + k) + '" cy="' + (yy + 6) + '" r="2" fill="' + WARN + '"/>';
            return s2;
        }
        var s = block(60, 84, 60) + block(230, 132, 60);
        s += txt(102, 96, 'малая площадь', SOFT, 10);
        s += txt(296, 96, 'большая площадь', SOFT, 10);
        s += txt(210, 130, 'точек контакта столько же — сила трения та же', INK, 11.5);
        return svg(W, H, s);
    };

    // ── Теоретическая механика: принцип наименьшего действия ──

    // Из точки в точку ведёт бесконечно много путей — природа выбирает один.
    F.manypaths = function () {
        var W = 420, H = 160, x0 = 60, x1 = 360, y = 120;
        var s = '';
        [-46, -26, 0, 22, 40].forEach(function (h, i) {
            var mid = (x0 + x1) / 2;
            s += '<path d="M' + x0 + ',' + y + ' Q' + mid + ',' + (y + 2 * h) + ' ' + x1 + ',' + y + '" ' +
                'fill="none" stroke="' + (h === 0 ? LINK : SOFT) + '" stroke-width="' + (h === 0 ? 2.6 : 1.2) +
                '"' + (h === 0 ? '' : ' stroke-dasharray="4 4" opacity="0.75"') + '/>';
        });
        s += '<circle cx="' + x0 + '" cy="' + y + '" r="5" fill="' + INK + '"/>';
        s += '<circle cx="' + x1 + '" cy="' + y + '" r="5" fill="' + INK + '"/>';
        s += txt(x0, y + 20, 'начало', SOFT, 10);
        s += txt(x1, y + 20, 'конец', SOFT, 10);
        s += txt((x0 + x1) / 2, 28, 'путей бесконечно много', SOFT, 11);
        s += txt((x0 + x1) / 2, y - 4, 'истинный', LINK, 11);
        return svg(W, H, s);
    };

    // Действие складывается по кусочкам: на каждом шаге берём разность энергий.
    F.actionsum = function () {
        var W = 420, H = 165, x0 = 50, base = 118, bw = 30;
        var s = '<line x1="' + (x0 - 10) + '" y1="' + base + '" x2="' + (x0 + 9 * bw + 14) + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        [26, 20, 12, 5, -2, -6, -4, 4, 16].forEach(function (h, i) {
            var x = x0 + i * bw;
            s += '<rect x="' + x + '" y="' + (h >= 0 ? base - h : base) + '" width="' + (bw - 6) +
                '" height="' + Math.abs(h) + '" fill="' + (h >= 0 ? LINK : WARN) + '" opacity="0.55"/>';
        });
        s += txt(x0 + 4.5 * bw, 26, 'K − U на каждом шаге', INK, 11.5);
        s += txt(x0 + 4.5 * bw, 146, 'сумма по всем шагам и есть действие', SOFT, 10.5);
        s += arrow(x0 + 9 * bw + 4, base, x0 + 9 * bw + 4, base - 34, LINK, 'ahl');
        s += txt(x0 + 9 * bw + 4, base - 42, 'S', LINK, 12);
        return svg(W, H, s);
    };

    // Кривая действия: у истинного пути минимум, отклонение в любую сторону его увеличивает.
    F.actionmin = function () {
        var W = 400, H = 175, cx = 200, base = 130, k = 0.011;
        var pts = [];
        for (var x = -150; x <= 150; x += 5) pts.push((cx + x) + ',' + (base - k * x * x));
        var s = '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += '<line x1="' + (cx - 165) + '" y1="' + base + '" x2="' + (cx + 165) + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="' + (base + 8) + '" x2="' + cx + '" y2="30" stroke="' + BORD +
            '" stroke-width="1" stroke-dasharray="3 3"/>';
        s += '<circle cx="' + cx + '" cy="' + base + '" r="5" fill="' + MOSS + '"/>';
        s += txt(cx, base + 20, 'истинный путь', MOSS, 10.5);
        s += txt(cx - 105, base - 40, 'отклонение', SOFT, 10);
        s += txt(cx + 105, base - 40, 'отклонение', SOFT, 10);
        s += txt(cx, 24, 'действие S', INK, 11.5);
        return svg(W, H, s);
    };

    // ── Космология: расширение и красное смещение ──

    // Резинка с метками: номера остаются, расстояния растут в одной пропорции.
    F.rubberband = function () {
        var W = 430, H = 175, x0 = 46, y1 = 58, y2 = 126, k = 1.5;
        var s = txt(W / 2, 24, 'одно и то же растяжение повсюду', SOFT, 11);
        // до растяжения
        s += '<line x1="' + x0 + '" y1="' + y1 + '" x2="' + (x0 + 210) + '" y2="' + y1 +
            '" stroke="' + BORD + '" stroke-width="6" opacity="0.5"/>';
        // после растяжения
        s += '<line x1="' + x0 + '" y1="' + y2 + '" x2="' + (x0 + 210 * k) + '" y2="' + y2 +
            '" stroke="' + LINK + '" stroke-width="6" opacity="0.35"/>';
        [0, 1, 2, 3].forEach(function (n) {
            var xa = x0 + n * 70, xb = x0 + n * 70 * k;
            s += '<circle cx="' + xa + '" cy="' + y1 + '" r="5" fill="' + (n === 0 ? LINK : WARN) + '"/>';
            s += '<circle cx="' + xb + '" cy="' + y2 + '" r="5" fill="' + (n === 0 ? LINK : WARN) + '"/>';
            s += txt(xa, y1 - 12, String(n), SOFT, 10);
            s += txt(xb, y2 + 20, String(n), SOFT, 10);
            if (n) s += '<line x1="' + xa + '" y1="' + (y1 + 9) + '" x2="' + xb + '" y2="' + (y2 - 9) +
                '" stroke="' + SOFT + '" stroke-width="0.8" stroke-dasharray="2 3"/>';
        });
        s += txt(x0 - 6, y1 + 4, 'до', SOFT, 10, 'end');
        s += txt(x0 - 6, y2 + 4, 'после', SOFT, 10, 'end');
        s += txt(W / 2, H - 8, 'метка стоит на своём номере, растёт расстояние', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Скорость пропорциональна расстоянию: стрелки удлиняются линейно, центра нет.
    F.hubblelaw = function () {
        var W = 430, H = 165, x0 = 50, y = 92;
        var s = txt(W / 2, 24, 'дальше — значит быстрее', INK, 11.5);
        s += '<line x1="' + (x0 - 12) + '" y1="' + y + '" x2="' + (W - 20) + '" y2="' + y +
            '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3 4"/>';
        s += '<circle cx="' + x0 + '" cy="' + y + '" r="6" fill="' + LINK + '"/>';
        s += txt(x0, y + 22, 'наблюдатель', LINK, 10);
        [1, 2, 3].forEach(function (n) {
            var x = x0 + n * 95;
            s += '<circle cx="' + x + '" cy="' + y + '" r="5" fill="' + WARN + '"/>';
            s += arrow(x + 8, y, x + 8 + n * 20, y, WARN, 'ahl');
            s += txt(x + 8 + n * 10, y - 12, n + 'v', WARN, 10.5);
            s += txt(x, y + 22, n + 'd', SOFT, 10);
        });
        s += txt(W / 2, H - 8, 'v = H₀·d — та же картина из любой точки', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Волна в пути: пространство растёт, гребни расходятся, линия краснеет.
    F.redshiftwave = function () {
        var W = 430, H = 170, x0 = 40, x1 = 390, y = 86;
        var pts = [], i, f, k;
        for (i = 0; i <= 300; i++) {
            f = i / 300;
            k = 15 + 22 * f;                       // шаг волны растёт по пути
            pts.push((x0 + (x1 - x0) * f) + ',' + (y - 17 * Math.sin(f * (x1 - x0) / k * 0.9)));
        }
        var s = '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.2"/>';
        s += '<circle cx="' + x0 + '" cy="' + y + '" r="5" fill="' + WARN + '"/>';
        s += txt(x0, y + 34, 'галактика', WARN, 10);
        s += '<circle cx="' + x1 + '" cy="' + y + '" r="5" fill="' + LINK + '"/>';
        s += txt(x1, y + 34, 'мы', LINK, 10);
        s += txt(W / 2, 24, 'волна растягивается вместе с пространством', INK, 11.5);
        s += txt(x0 + 40, H - 10, 'короткая волна', SOFT, 10);
        s += txt(x1 - 46, H - 10, 'длинная — краснее', WARN, 10);
        return svg(W, H, s);
    };

    // H — не размер и не скорость, а их отношение: скорость роста на текущий размер.
    F.hubbleconst = function () {
        var W = 420, H = 170, y = 84, x0 = 54;
        var s = txt(W / 2, 24, 'H = скорость роста ÷ текущий размер', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + y + '" x2="' + (x0 + 130) + '" y2="' + y +
            '" stroke="' + BORD + '" stroke-width="7" opacity="0.55"/>';
        s += arrow(x0 + 134, y, x0 + 188, y, LINK, 'ahl');
        s += txt(x0 + 161, y - 12, 'ȧ', LINK, 12);
        s += txt(x0 + 65, y + 22, 'a — размер сейчас', SOFT, 10.5);
        s += txt(W / 2, y + 56, 'одно и то же H для всех пар галактик', SOFT, 10.5);
        s += txt(W / 2, y + 76, '1/H₀ ≈ 14 млрд лет — оценка, не возраст', WARN, 10.5);
        return svg(W, H, s);
    };

    // Рабочая цепочка астронома: спектр → z → скорость → расстояние.
    F.zladder = function () {
        var W = 440, H = 150, y = 78, bw = 86, gap = 30, x0 = 26;
        var items = ['спектр', 'z', 'v = cz', 'd = v/H₀'];
        var s = txt(W / 2, 26, 'от линии в спектре к расстоянию', INK, 11.5);
        items.forEach(function (t, i) {
            var x = x0 + i * (bw + gap);
            s += '<rect x="' + x + '" y="' + (y - 18) + '" width="' + bw + '" height="36" rx="6" fill="none" stroke="' +
                (i === 0 ? WARN : LINK) + '" stroke-width="1.4" opacity="0.85"/>';
            s += txt(x + bw / 2, y + 5, t, i === 0 ? WARN : LINK, 12);
            if (i < items.length - 1) s += arrow(x + bw + 4, y, x + bw + gap - 6, y, SOFT, 'ahl');
        });
        s += txt(W / 2, H - 12, 'последний шаг верен только при малом z', WARN, 10.5);
        return svg(W, H, s);
    };

    global.B42Figures = F;
})(window);
