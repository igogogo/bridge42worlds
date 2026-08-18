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

    // Одно и то же излучение: сжатое было горячим, растянутое стало холодным.
    F.cooldown = function () {
        var W = 430, H = 168, y1 = 62, y2 = 118, x0 = 60;
        var s = txt(W / 2, 26, 'растяжение остужает', INK, 11.5);
        function wave(y, step, color, w) {
            var pts = [], i;
            for (i = 0; i <= 240; i++) {
                var x = x0 + i * (330 / 240);
                pts.push(x + ',' + (y - 13 * Math.sin(i * (330 / 240) / step)));
            }
            return '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color +
                '" stroke-width="' + w + '"/>';
        }
        s += wave(y1, 4.2, WARN, 2);
        s += wave(y2, 12, LINK, 2);
        s += txt(x0 - 8, y1 + 4, '3000 K', WARN, 10.5, 'end');
        s += txt(x0 - 8, y2 + 4, '2,7 K', LINK, 10.5, 'end');
        s += txt(W / 2, H - 10, 'T ∝ 1/a: во сколько раз выросла Вселенная, во столько остыл свет', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Плазма непрозрачна, нейтральный газ прозрачен: свет уходит после рекомбинации.
    F.recombination = function () {
        var W = 440, H = 170, y = 92, mid = W / 2;
        var s = txt(W / 4, 26, 'плазма: свет в тумане', WARN, 11);
        s += txt(3 * W / 4, 26, 'атомы: свет уходит', MOSS, 11);
        s += '<line x1="' + mid + '" y1="40" x2="' + mid + '" y2="' + (H - 26) +
            '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="4 4"/>';
        var i;
        for (i = 0; i < 9; i++) {          // слева: электроны врассыпную, путь света ломаный
            var px = 30 + (i % 3) * 46, py = 58 + Math.floor(i / 3) * 26;
            s += '<circle cx="' + px + '" cy="' + py + '" r="3.5" fill="' + WARN + '"/>';
        }
        s += '<polyline points="34,120 66,96 92,124 128,100 158,126" fill="none" stroke="' + LINK +
            '" stroke-width="1.6"/>';
        for (i = 0; i < 6; i++) {          // справа: нейтральные атомы, свет летит прямо
            var ax = mid + 34 + (i % 3) * 52, ay = 62 + Math.floor(i / 3) * 30;
            s += '<circle cx="' + ax + '" cy="' + ay + '" r="8" fill="none" stroke="' + SOFT + '" stroke-width="1.2"/>';
            s += '<circle cx="' + ax + '" cy="' + ay + '" r="2.5" fill="' + SOFT + '"/>';
        }
        s += arrow(mid + 16, 124, W - 22, 124, MOSS, 'ahl');
        s += txt(mid + 90, 140, 'до нас', MOSS, 10.5);
        s += txt(W / 2, H - 6, '3000 K — граница прозрачности', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Чем холоднее тело, тем правее пик его спектра.
    F.planckpeak = function () {
        var W = 430, H = 175, base = 132, x0 = 46, x1 = 396;
        var s = '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        function hump(cx, hgt, color, w, dash) {
            var pts = [], x;
            for (x = x0; x <= x1; x += 4) {
                var u = (x - cx) / 52;
                pts.push(x + ',' + (base - hgt * Math.exp(-u * u)));
            }
            return '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color +
                '" stroke-width="' + w + '"' + (dash ? ' stroke-dasharray="4 4"' : '') + '/>';
        }
        s += hump(150, 86, WARN, 2, false);
        s += hump(300, 52, LINK, 2.4, false);
        s += txt(150, 34, '3000 K', WARN, 10.5);
        s += txt(300, 62, '2,7 K', LINK, 10.5);
        s += txt(x1, base + 16, 'длина волны →', SOFT, 10, 'end');
        s += txt(W / 2, H - 6, 'λ пика обратно пропорциональна T', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Две области за горизонтом друг друга: сигнал между ними пройти не успевал.
    F.horizon = function () {
        var W = 430, H = 180, cy = 96, r = 58, cx1 = 118, cx2 = 312;
        var s = txt(W / 2, 26, 'одинаковая температура без общей истории', INK, 11.5);
        [[cx1, WARN], [cx2, LINK]].forEach(function (p) {
            s += '<circle cx="' + p[0] + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + p[1] +
                '" stroke-width="1.4" stroke-dasharray="5 4"/>';
            s += '<circle cx="' + p[0] + '" cy="' + cy + '" r="7" fill="' + p[1] + '"/>';
        });
        s += txt(cx1, cy + r + 18, 'её горизонт', WARN, 10);
        s += txt(cx2, cy + r + 18, 'её горизонт', LINK, 10);
        s += txt(W / 2, cy - 6, '2,725 K', INK, 11);
        s += txt(W / 2, cy + 14, '=', SOFT, 12);
        s += txt(W / 2, H - 8, 'круги не пересекаются: сигнал не успевал пройти', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Скорость на орбите задаёт только масса внутри неё.
    F.circularv = function () {
        var W = 420, H = 175, cx = 200, cy = 96, r1 = 34, r2 = 74;
        var s = txt(W / 2, 24, 'тянет только то, что внутри орбиты', INK, 11.5);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r1 + '" fill="' + WARN + '" opacity="0.28"/>';
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r2 + '" fill="none" stroke="' + BORD +
            '" stroke-width="1" stroke-dasharray="4 4"/>';
        s += txt(cx, cy + 4, 'M(r)', WARN, 11);
        s += '<circle cx="' + (cx + r2) + '" cy="' + cy + '" r="5.5" fill="' + LINK + '"/>';
        s += arrow(cx + r2, cy - 6, cx + r2, cy - 44, LINK, 'ahl');
        s += txt(cx + r2 + 22, cy - 30, 'v', LINK, 12);
        s += arrow(cx + r2 - 8, cy, cx + 12, cy, WARN, 'ahl');
        s += txt(cx + r2 - 34, cy - 10, 'F', WARN, 11);
        s += txt(W / 2, H - 8, 'внешние слои не притягивают: их вклад взаимно гасится', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Если масса кончилась, кривая скоростей должна падать.
    F.keplerfall = function () {
        var W = 420, H = 168, base = 124, x0 = 52, x1 = 380, top = 44;
        var s = txt(W / 2, 26, 'как должно быть, если вся масса видна', INK, 11.5);
        var pts = [], x;
        for (x = x0 + 22; x <= x1; x += 5) {
            var v = 78 / Math.sqrt((x - x0) / 40);
            pts.push(x + ',' + (base - Math.min(base - top, v)));
        }
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + SOFT +
            '" stroke-width="2" stroke-dasharray="5 4"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(x1, base + 16, 'радиус →', SOFT, 10, 'end');
        s += txt(x0 + 6, top - 8, 'скорость', SOFT, 10, 'start');
        s += txt(W / 2, H - 8, 'v ∝ 1/√r — как у планет вокруг Солнца', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Плоская кривая: то, что измеряют на самом деле.
    F.flatcurve = function () {
        var W = 420, H = 172, base = 126, x0 = 52, x1 = 380, top = 46;
        var s = txt(W / 2, 26, 'что измеряют на самом деле', INK, 11.5);
        var kep = [], flat = [], x;
        for (x = x0 + 22; x <= x1; x += 5) {
            kep.push(x + ',' + (base - Math.min(base - top, 78 / Math.sqrt((x - x0) / 40))));
            flat.push(x + ',' + (base - 62 * Math.sqrt(Math.min(1, (x - x0) / 70))));
        }
        s += '<polyline points="' + kep.join(' ') + '" fill="none" stroke="' + SOFT +
            '" stroke-width="1.6" stroke-dasharray="5 4"/>';
        s += '<polyline points="' + flat.join(' ') + '" fill="none" stroke="' + WARN + '" stroke-width="2.6"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(x1 - 10, base - 74, 'измерено', WARN, 10.5, 'end');
        s += txt(x1 - 10, base - 26, 'видимая масса', SOFT, 10, 'end');
        s += txt(W / 2, H - 8, 'разница и есть тёмное гало', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Материя разбавляется, тёмная энергия — нет.
    F.friedmann = function () {
        var W = 430, H = 172, base = 126, x0 = 52, x1 = 386, top = 44;
        var s = txt(W / 2, 26, 'что происходит с плотностями при росте', INK, 11.5);
        var mat = [], lam = [], x;
        for (x = x0; x <= x1; x += 4) {
            var a = 1 + 3 * (x - x0) / (x1 - x0);
            mat.push(x + ',' + (base - Math.min(base - top, 80 / (a * a * a))));
            lam.push(x + ',' + (base - 26));
        }
        s += '<polyline points="' + mat.join(' ') + '" fill="none" stroke="' + WARN + '" stroke-width="2.4"/>';
        s += '<polyline points="' + lam.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(x0 + 60, top + 2, 'материя ∝ 1/a³', WARN, 10.5);
        s += txt(x1 - 8, base - 34, 'тёмная энергия — постоянна', LINK, 10.5, 'end');
        s += txt(x1, base + 16, 'размер a →', SOFT, 10, 'end');
        s += txt(W / 2, H - 8, 'пересечение кривых — момент смены знака ускорения', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Инфляция: всё видимое вышло из одной успевшей выровняться области.
    F.inflation = function () {
        var W = 430, H = 176, y = 92;
        var s = txt(W / 2, 26, 'раздувание одной выровнявшейся области', INK, 11.5);
        s += '<circle cx="70" cy="' + y + '" r="12" fill="' + WARN + '" opacity="0.55"/>';
        s += txt(70, y + 32, 'до: успела выровняться', SOFT, 10);
        s += arrow(92, y, 168, y, LINK, 'ahl');
        s += txt(130, y - 14, 'e⁶⁰', LINK, 11.5);
        s += '<circle cx="300" cy="' + y + '" r="66" fill="none" stroke="' + LINK + '" stroke-width="1.6"/>';
        s += '<circle cx="300" cy="' + y + '" r="26" fill="' + WARN + '" opacity="0.28"/>';
        s += txt(300, y + 4, 'видимая часть', INK, 10.5);
        s += txt(300, y + 96, 'после: та же однородность на всём небе', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Переход от торможения к ускорению: перегиб на кривой роста.
    F.accelflip = function () {
        var W = 420, H = 172, base = 130, x0 = 48, x1 = 380, top = 40;
        var s = txt(W / 2, 24, 'сначала тормозит, потом разгоняется', INK, 11.5);
        var pts = [], x, xf = x0 + (x1 - x0) * 0.45;
        for (x = x0; x <= x1; x += 4) {
            var u = (x - x0) / (x1 - x0);
            var a = Math.pow(u, 0.62) * 0.72 + Math.pow(Math.max(0, u - 0.45), 2.1) * 1.5;
            pts.push(x + ',' + (base - Math.min(base - top, a * 96)));
        }
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.6"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + xf + '" y1="' + base + '" x2="' + xf + '" y2="' + top +
            '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += txt(xf, top - 8, 'z ≈ 0,7', WARN, 10.5);
        s += txt(x0 + 54, base - 16, 'торможение', SOFT, 10);
        s += txt(x1 - 40, base - 92, 'ускорение', LINK, 10.5, 'end');
        s += txt(x1, base + 16, 'время →', SOFT, 10, 'end');
        return svg(W, H, s);
    };

    // Стандартная свеча: известная светимость плюс видимая яркость дают расстояние.
    F.standardcandle = function () {
        var W = 430, H = 168, y = 88;
        var s = txt(W / 2, 26, 'одинаковая вспышка как линейка', INK, 11.5);
        [[92, 15, 1], [214, 9, 0.55], [336, 5.5, 0.3]].forEach(function (p, i) {
            s += '<circle cx="' + p[0] + '" cy="' + y + '" r="' + p[1] + '" fill="' + WARN +
                '" opacity="' + p[2] + '"/>';
            s += txt(p[0], y + 40, ['близко', 'дальше', 'ещё дальше'][i], SOFT, 10);
        });
        s += txt(W / 2, y + 66, 'светимость одна — значит видимая яркость меряет расстояние', SOFT, 10.5);
        return svg(W, H, s);
    };


    // ─────────── Гидродинамика, параграф 3: вязкость и сопротивление ───────────

    // Слои идут с разной скоростью; тепловое движение переносит импульс поперёк потока.
    F.viscolayers = function () {
        var W = 430, H = 196, x0 = 50, x1 = 250, ys = [52, 78, 104, 130], ln = [92, 69, 46, 23], i, x;
        var s = txt(W / 2, 22, 'слои идут с разной скоростью', INK, 11.5);
        for (i = 0; i < ys.length; i++) {
            s += '<line x1="' + x0 + '" y1="' + ys[i] + '" x2="' + x1 + '" y2="' + ys[i] +
                '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3 4"/>';
            s += arrow(x0 + 4, ys[i], x0 + 4 + ln[i], ys[i], LINK, 'ahl');
        }
        s += txt(x0 + 106, 48, 'v', LINK, 11, 'start');
        // перескок молекулы из быстрого слоя в медленный: с ней уходит и её импульс
        s += mol(190, 78, 5.5, WARN);
        s += '<path d="M190,84 Q208,93 190,101" fill="none" stroke="' + WARN +
            '" stroke-width="1.6" marker-end="url(#ahw)"/>';
        s += txt(196, 120, 'перескок', WARN, 10, 'start');
        s += '<line x1="' + x0 + '" y1="152" x2="' + x1 + '" y2="152" stroke="' + INK + '" stroke-width="3"/>';
        for (x = x0; x < x1; x += 9) {
            s += '<line x1="' + x + '" y1="152" x2="' + (x + 7) + '" y2="160" stroke="' + SOFT + '" stroke-width="1"/>';
        }
        s += txt((x0 + x1) / 2, 178, 'стенка: скорость нуль', SOFT, 10.5);
        s += txt(345, 76, '&#964; = &#951; dv/dy', INK, 14);
        s += txt(345, 100, 'перенос импульса', SOFT, 10.5);
        s += txt(345, 118, 'поперёк потока', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Две пластины и зазор: определение вязкости через силу на единицу площади.
    F.noslip = function () {
        var W = 430, H = 190, xa = 60, xb = 300, yt = 50, yb = 138, x, y, L, tip = [];
        var s = txt(W / 2, 22, 'опыт, которым меряют вязкость', INK, 11.5);
        s += '<line x1="' + xa + '" y1="' + yt + '" x2="' + xb + '" y2="' + yt + '" stroke="' + INK + '" stroke-width="3"/>';
        s += '<line x1="' + xa + '" y1="' + yb + '" x2="' + xb + '" y2="' + yb + '" stroke="' + INK + '" stroke-width="3"/>';
        for (x = xa; x < xb; x += 9) {
            s += '<line x1="' + x + '" y1="' + yt + '" x2="' + (x + 7) + '" y2="' + (yt - 8) + '" stroke="' + SOFT + '" stroke-width="1"/>';
            s += '<line x1="' + x + '" y1="' + yb + '" x2="' + (x + 7) + '" y2="' + (yb + 8) + '" stroke="' + SOFT + '" stroke-width="1"/>';
        }
        for (y = yt + 6; y < yb; y += 11) {
            L = Math.max(6, 96 * (yb - y) / (yb - yt));
            s += arrow(xa + 12, y, xa + 12 + L, y, LINK, 'ahl');
            tip.push((xa + 12 + L) + ',' + y);
        }
        s += '<polyline points="' + tip.join(' ') + '" fill="none" stroke="' + WARN +
            '" stroke-width="1.4" stroke-dasharray="4 3"/>';
        s += txt((xa + xb) / 2, yt - 14, 'верхняя пластина: скорость u', SOFT, 10.5);
        s += txt((xa + xb) / 2, yb + 26, 'нижняя пластина: скорость нуль', SOFT, 10.5);
        s += arrow(xb + 22, yt, xb + 22, yb, SOFT);
        s += txt(xb + 44, (yt + yb) / 2, 'зазор h', SOFT, 10.5, 'start');
        s += txt(W / 2, H - 8, 'скорость растёт равномерно поперёк зазора', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Баланс сил на воображаемом цилиндре внутри трубы: торцы против боковой поверхности.
    F.pipebalance = function () {
        var W = 430, H = 196, xa = 46, xb = 384, yt = 46, yb = 146, mid = 96;
        var s = txt(W / 2, 22, 'что держит цилиндр внутри потока', INK, 11.5);
        s += '<line x1="' + xa + '" y1="' + yt + '" x2="' + xb + '" y2="' + yt + '" stroke="' + INK + '" stroke-width="3"/>';
        s += '<line x1="' + xa + '" y1="' + yb + '" x2="' + xb + '" y2="' + yb + '" stroke="' + INK + '" stroke-width="3"/>';
        s += '<line x1="' + xa + '" y1="' + mid + '" x2="' + xb + '" y2="' + mid +
            '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="5 4"/>';
        s += '<rect x="128" y="' + (mid - 20) + '" width="180" height="40" fill="' + LINK +
            '" opacity="0.12" stroke="' + LINK + '" stroke-width="1.2" stroke-dasharray="4 3"/>';
        s += arrow(218, mid, 218, mid - 20, LINK, 'ahl');
        s += txt(226, mid - 8, 'r', LINK, 11, 'start');
        s += arrow(104, mid - 10, 126, mid - 10, LINK, 'ahl');
        s += arrow(104, mid + 10, 126, mid + 10, LINK, 'ahl');
        s += txt(98, mid + 4, 'p&#8321;', LINK, 12, 'end');
        s += arrow(332, mid - 10, 310, mid - 10, SOFT);
        s += arrow(332, mid + 10, 310, mid + 10, SOFT);
        s += txt(340, mid + 4, 'p&#8322;', SOFT, 12, 'start');
        s += arrow(230, mid - 26, 176, mid - 26, WARN, 'ahw');
        s += arrow(230, mid + 32, 176, mid + 32, WARN, 'ahw');
        s += txt(238, mid - 30, 'вязкое трение', WARN, 10, 'start');
        s += arrow(128, 166, 308, 166, SOFT);
        s += txt(218, 162, 'L', SOFT, 11);
        s += txt(W / 2, H - 6, 'перепад давления гонит, трение держит', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Решение с условием прилипания: парабола вместо ровного профиля.
    F.poiseuilleprofile = function () {
        var W = 420, H = 190, xa = 46, xb = 380, yt = 50, yb = 146, mid = 98, R = 48;
        var s = txt(W / 2, 22, 'параболический профиль скорости', INK, 11.5);
        s += '<line x1="' + xa + '" y1="' + yt + '" x2="' + xb + '" y2="' + yt + '" stroke="' + INK + '" stroke-width="3"/>';
        s += '<line x1="' + xa + '" y1="' + yb + '" x2="' + xb + '" y2="' + yb + '" stroke="' + INK + '" stroke-width="3"/>';
        var x0 = 120, tip = [], y, u, L;
        for (y = yt + 3; y <= yb - 3; y += 8) {
            u = (y - mid) / R;
            L = Math.max(2, 126 * (1 - u * u));
            s += arrow(x0, y, x0 + L, y, LINK, 'ahl');
            tip.push((x0 + L) + ',' + y);
        }
        s += '<polyline points="' + tip.join(' ') + '" fill="none" stroke="' + WARN + '" stroke-width="1.8"/>';
        s += arrow(x0 - 16, mid, x0 - 16, yt, SOFT);
        s += txt(x0 - 24, 74, 'R', SOFT, 11, 'end');
        s += txt(150, yt + 10, 'у стенки нуль', SOFT, 10, 'start');
        s += txt(330, 88, 'v(r) = v&#8320;(1 &#8722; r²/R²)', INK, 12);
        s += txt(330, 110, 'на оси быстрее всего', SOFT, 10);
        s += txt(W / 2, H - 8, 'средняя скорость вдвое меньше максимальной', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Расход как сумма по кольцам: площадь кольца растёт, скорость в нём падает.
    F.ringsum = function () {
        var W = 420, H = 200, cx = 122, cy = 102, R = 58;
        var s = txt(W / 2, 22, 'расход собирается по кольцам', INK, 11.5);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="none" stroke="' + INK + '" stroke-width="2.4"/>';
        [14, 26, 38, 48].forEach(function (r) {
            s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD + '" stroke-width="1"/>';
        });
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="32" fill="none" stroke="' + LINK +
            '" stroke-width="10" opacity="0.28"/>';
        s += arrow(cx, cy, cx + 32, cy, WARN, 'ahw');
        s += txt(cx + 16, cy - 6, 'r', WARN, 11);
        s += txt(cx, cy + R + 20, 'сечение трубы', SOFT, 10.5);
        s += txt(300, 76, 'dQ = v(r)·2&#960;r·dr', INK, 12);
        s += txt(300, 104, 'Q = &#960;R&#8308;&#916;p / (8&#951;L)', WARN, 13);
        s += txt(W / 2, H - 8, 'дальние кольца шире, но течение в них медленнее', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Что означает четвёртая степень: кривая, по которой читают цену сужения.
    F.fourthpower = function () {
        var W = 430, H = 190, x0 = 62, x1 = 392, base = 146, top = 46, pts = [], x, u;
        var s = txt(W / 2, 22, 'радиус в четвёртой степени', INK, 11.5);
        for (x = x0; x <= x1; x += 3) {
            u = (x - x0) / (x1 - x0);
            pts.push(x + ',' + (base - (base - top) * Math.pow(u, 4)));
        }
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.6"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + top + '" stroke="' + BORD + '" stroke-width="1"/>';
        var xm = x0 + (x1 - x0) * 0.75, ym = base - (base - top) * 0.3164;
        s += '<line x1="' + xm + '" y1="' + base + '" x2="' + xm + '" y2="' + ym +
            '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += '<line x1="' + x0 + '" y1="' + ym + '" x2="' + xm + '" y2="' + ym +
            '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += '<circle cx="' + xm + '" cy="' + ym + '" r="3.5" fill="' + WARN + '"/>';
        s += txt(xm - 8, ym - 12, 'радиус меньше на четверть — расход втрое', WARN, 10, 'end');
        s += txt(x1, base + 18, 'радиус →', SOFT, 10, 'end');
        s += txt(x0 - 6, top + 4, 'расход', SOFT, 10, 'end');
        return svg(W, H, s);
    };

    // Число Рейнольдса как приговор картине течения: слева слои, справа завитки.
    F.reynolds = function () {
        var W = 430, H = 200, i, y, x, d;
        var s = txt(W / 2, 22, 'инерция против вязкости', INK, 11.5);
        s += '<rect x="42" y="40" width="146" height="64" fill="none" stroke="' + BORD + '" stroke-width="1"/>';
        for (i = 0; i < 5; i++) {
            y = 50 + i * 12;
            s += '<line x1="50" y1="' + y + '" x2="180" y2="' + y + '" stroke="' + LINK + '" stroke-width="1.6"/>';
        }
        s += txt(115, 122, 'ламинарное', LINK, 10.5);
        s += '<rect x="242" y="40" width="146" height="64" fill="none" stroke="' + BORD + '" stroke-width="1"/>';
        for (i = 0; i < 5; i++) {
            y = 50 + i * 12;
            d = 'M250,' + y;
            for (x = 250; x < 378; x += 16) d += ' q8,' + (i % 2 ? -7 : 7) + ' 16,0';
            s += '<path d="' + d + '" fill="none" stroke="' + WARN + '" stroke-width="1.5"/>';
        }
        s += txt(315, 122, 'турбулентное', WARN, 10.5);
        s += '<line x1="42" y1="152" x2="388" y2="152" stroke="' + BORD + '" stroke-width="1.5"/>';
        s += '<line x1="215" y1="143" x2="215" y2="161" stroke="' + WARN + '" stroke-width="2"/>';
        s += txt(215, 139, 'Re &#8776; 2300', WARN, 10.5);
        s += txt(46, 172, 'вязкость сильнее', SOFT, 10, 'start');
        s += txt(384, 172, 'инерция сильнее', SOFT, 10, 'end');
        s += txt(W / 2, 192, 'Re = &#961;vD / &#951;', INK, 13);
        return svg(W, H, s);
    };

    // Шар в вязкой среде: вес против выталкивания и сопротивления Стокса.
    F.stokesdrag = function () {
        var W = 430, H = 196, xa = 44, xb = 168, yt = 42, yb = 168, cx = 106, cy = 100;
        var s = txt(W / 2, 22, 'три силы и предельная скорость', INK, 11.5);
        s += '<rect x="' + xa + '" y="' + yt + '" width="' + (xb - xa) + '" height="' + (yb - yt) +
            '" fill="' + LINK + '" opacity="0.08" stroke="' + BORD + '" stroke-width="1"/>';
        s += mol(cx, cy, 13, SOFT);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="13" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
        s += arrow(cx, cy + 15, cx, cy + 52, INK);
        s += arrow(cx - 12, cy - 15, cx - 12, cy - 46, LINK, 'ahl');
        s += arrow(cx + 12, cy - 15, cx + 12, cy - 40, WARN, 'ahw');
        s += txt(cx + 24, cy + 42, 'v', SOFT, 11, 'start');
        s += txt(228, 64, 'вес шарика', INK, 11, 'start');
        s += txt(228, 92, 'выталкивающая сила', LINK, 11, 'start');
        s += txt(228, 120, 'сопротивление по Стоксу', WARN, 11, 'start');
        s += txt(228, 146, '6&#960;&#951;rv', WARN, 12.5, 'start');
        s += txt(W / 2, H - 8, 'равновесие трёх сил задаёт предельную скорость', SOFT, 10.5);
        return svg(W, H, s);
    };

    /* ——— Течение: неразрывность и Бернулли (тема fluids, параграф 2) ———
       Общий контур трубы с сужением: одна геометрия на все схемы параграфа, чтобы
       читатель узнавал ту же трубу от шага к шагу. Вертикальный размер здесь читается
       как ПЛОЩАДЬ сечения, а не как диаметр: иначе равные по объёму порции пришлось бы
       рисовать с неверным отношением длин, и картинка спорила бы с текстом. */
    function flowPipe(x0, x1, midY, r1, r2, xa, xb) {
        function side(sign) {
            return '<path d="M' + x0 + ',' + (midY + sign * r1) + ' L' + xa + ',' + (midY + sign * r1) +
                ' L' + xb + ',' + (midY + sign * r2) + ' L' + x1 + ',' + (midY + sign * r2) +
                '" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        }
        return side(-1) + side(1);
    }

    // 1. Неразрывность: за одинаковое время через оба сечения проходит один объём.
    F.contintube = function () {
        var W = 440, H = 178, midY = 86, r1 = 34, r2 = 17, x0 = 20, x1 = 420, xa = 170, xb = 250;
        var s = txt(W / 2, 20, 'за одно и то же время', INK, 11.5);
        s += flowPipe(x0, x1, midY, r1, r2, xa, xb);
        s += '<rect x="62" y="' + (midY - r1) + '" width="34" height="' + (2 * r1) +
            '" fill="' + LINK + '" opacity="0.18" stroke="' + LINK + '" stroke-dasharray="3,3"/>';
        s += '<rect x="320" y="' + (midY - r2) + '" width="68" height="' + (2 * r2) +
            '" fill="' + LINK + '" opacity="0.18" stroke="' + LINK + '" stroke-dasharray="3,3"/>';
        s += txt(79, midY + r1 + 16, 'v₁·&#916;t', LINK, 11);
        s += txt(354, midY + r2 + 16, 'v₂·&#916;t', LINK, 11);
        s += arrow(112, midY, 128, midY, LINK, 'ahl');
        s += arrow(256, midY, 306, midY, WARN, 'ahw');
        s += txt(40, midY + 4, 'A₁', SOFT, 11);
        s += txt(406, midY + 4, 'A₂', SOFT, 11);
        s += txt(W / 2, H - 8, 'сколько втекло, столько и вытекло: A₁v₁ = A₂v₂', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 2. Выделенная порция за Δt: середина не изменилась, перенесён только объём ΔV.
    F.flowslug = function () {
        var W = 440, H = 196, midY = 104, r1 = 34, r2 = 17, x0 = 20, x1 = 420, xa = 180, xb = 250;
        var s = txt(W / 2, 20, 'что изменилось за &#916;t', INK, 11.5);
        s += flowPipe(x0, x1, midY, r1, r2, xa, xb);
        s += '<line x1="70" y1="' + (midY - r1) + '" x2="70" y2="' + (midY + r1) +
            '" stroke="' + SOFT + '" stroke-width="1.2" stroke-dasharray="4,3"/>';
        s += '<line x1="340" y1="' + (midY - r2) + '" x2="340" y2="' + (midY + r2) +
            '" stroke="' + SOFT + '" stroke-width="1.2" stroke-dasharray="4,3"/>';
        s += '<rect x="70" y="' + (midY - r1) + '" width="20" height="' + (2 * r1) +
            '" fill="' + WARN + '" opacity="0.3"/>';
        s += '<rect x="340" y="' + (midY - r2) + '" width="40" height="' + (2 * r2) +
            '" fill="' + MOSS + '" opacity="0.3"/>';
        s += arrow(100, 52, 330, 52, SOFT, 'ah');
        s += txt(215, 44, 'как будто перенесли &#916;V', SOFT, 10.5);
        s += txt(215, midY + 4, 'середина не изменилась', SOFT, 10.5);
        s += txt(80, midY + r1 + 18, '&#916;x₁', WARN, 10.5);
        s += txt(360, midY + r2 + 18, '&#916;x₂', MOSS, 10.5);
        s += txt(W / 2, H - 8, 'вся бухгалтерия сводится к двум концам', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 3. Работа сил давления на концах: сзади толкает, спереди сопротивляется.
    F.presswork = function () {
        var W = 440, H = 182, midY = 92, r1 = 34, r2 = 17, x0 = 20, x1 = 420, xa = 180, xb = 250;
        var s = txt(W / 2, 20, 'работа сил давления на концах', INK, 11.5);
        s += flowPipe(x0, x1, midY, r1, r2, xa, xb);
        s += '<line x1="70" y1="' + (midY - r1) + '" x2="70" y2="' + (midY + r1) +
            '" stroke="' + LINK + '" stroke-width="4"/>';
        s += '<line x1="340" y1="' + (midY - r2) + '" x2="340" y2="' + (midY + r2) +
            '" stroke="' + WARN + '" stroke-width="4"/>';
        s += arrow(74, midY, 122, midY, LINK, 'ahl');
        s += txt(100, midY - 10, 'p₁A₁', LINK, 11);
        s += arrow(392, midY, 348, midY, WARN, 'ahw');
        s += txt(372, midY - 24, 'p₂A₂', WARN, 11);
        s += '<line x1="70" y1="' + (midY + r1 + 16) + '" x2="90" y2="' + (midY + r1 + 16) +
            '" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += txt(80, midY + r1 + 30, '&#916;x₁', SOFT, 10);
        s += '<line x1="340" y1="' + (midY + r2 + 16) + '" x2="380" y2="' + (midY + r2 + 16) +
            '" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += txt(360, midY + r2 + 30, '&#916;x₂', SOFT, 10);
        s += txt(W / 2, H - 8, 'работа = p·A·&#916;x = p·&#916;V', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 4. Работа тяжести: перенос порции с одной высоты на другую.
    F.flowheight = function () {
        var W = 440, H = 192, base = 172;
        var s = txt(W / 2, 20, 'подъём порции на разность высот', INK, 11.5);
        s += '<path d="M53,153 L403,77" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += '<path d="M47,127 L397,51" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += '<line x1="30" y1="' + base + '" x2="424" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="5,4"/>';
        s += '<circle cx="113" cy="126" r="11" fill="' + LINK + '" opacity="0.55"/>';
        s += '<circle cx="302" cy="85" r="11" fill="' + WARN + '" opacity="0.55"/>';
        s += '<line x1="113" y1="137" x2="113" y2="' + base +
            '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="330" y1="80" x2="330" y2="' + base +
            '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += txt(126, 158, 'h₁', SOFT, 11, 'start');
        s += txt(342, 132, 'h₂', SOFT, 11, 'start');
        s += arrow(302, 98, 302, 126, WARN, 'ahw');
        s += txt(268, 118, '&#961;&#916;V·g', WARN, 10.5, 'end');
        s += txt(418, 166, 'уровень отсчёта', SOFT, 10, 'end');
        s += txt(W / 2, H - 6, 'работа тяжести: &#8722;&#961;·&#916;V·g·(h₂ &#8722; h₁)', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 5. Прирост кинетической энергии: скорость входит квадратом.
    F.flowkinetic = function () {
        var W = 440, H = 196, base = 160;
        var s = txt(W / 2, 18, 'энергия движения растёт как квадрат скорости', INK, 11.5);
        s += '<rect x="90" y="42" width="60" height="28" fill="' + LINK +
            '" opacity="0.16" stroke="' + LINK + '" stroke-dasharray="3,3"/>';
        s += mol(105, 56, 4) + mol(120, 50, 4) + mol(134, 62, 4);
        s += arrow(156, 56, 178, 56, LINK, 'ahl');
        s += txt(172, 38, 'v₁', LINK, 11);
        s += '<rect x="270" y="42" width="60" height="28" fill="' + WARN +
            '" opacity="0.16" stroke="' + WARN + '" stroke-dasharray="3,3"/>';
        s += mol(285, 56, 4, WARN) + mol(300, 50, 4, WARN) + mol(314, 62, 4, WARN);
        s += arrow(336, 56, 392, 56, WARN, 'ahw');
        s += txt(376, 38, 'v₂ = 2v₁', WARN, 11);
        s += '<rect x="110" y="' + (base - 20) + '" width="40" height="20" fill="' + LINK + '" opacity="0.75"/>';
        s += '<rect x="290" y="' + (base - 80) + '" width="40" height="80" fill="' + WARN + '" opacity="0.75"/>';
        s += '<line x1="60" y1="' + base + '" x2="392" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(130, base + 16, '½&#961;v₁²', LINK, 10.5);
        s += txt(310, base + 16, '½&#961;v₂²', WARN, 10.5);
        s += txt(W / 2, H - 6, 'скорость вдвое — энергия вчетверо', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 6. Теорема о работе: всё, что сделали силы, ушло в кинетическую энергию.
    F.bernsum = function () {
        var W = 440, H = 176, base = 142;
        var s = txt(W / 2, 20, 'полная работа = прирост кинетической энергии', INK, 11.5);
        s += '<rect x="120" y="' + (base - 64) + '" width="56" height="64" fill="' + LINK + '" opacity="0.75"/>';
        s += '<rect x="120" y="' + (base - 86) + '" width="56" height="22" fill="' + MOSS + '" opacity="0.7"/>';
        s += '<rect x="290" y="' + (base - 86) + '" width="56" height="86" fill="' + WARN + '" opacity="0.75"/>';
        s += '<line x1="96" y1="' + base + '" x2="370" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(112, base - 30, 'давление', LINK, 10, 'end');
        s += txt(112, base - 74, 'тяжесть', MOSS, 10, 'end');
        s += txt(354, base - 42, 'движение', WARN, 10, 'start');
        s += txt(233, base - 34, '=', INK, 22);
        s += txt(W / 2, H - 8, '&#916;V входит в каждое слагаемое и сокращается', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 7. Инвариант вдоль линии тока: доли меняются, сумма — нет.
    F.bernconst = function () {
        var W = 450, H = 202, base = 150, w = 52;
        var s = txt(W / 2, 20, 'вдоль линии тока сумма не меняется', INK, 11.5);
        s += '<line x1="55" y1="50" x2="400" y2="50" stroke="' + INK +
            '" stroke-width="1.2" stroke-dasharray="5,4"/>';
        s += txt(W / 2, 42, 'сумма одна и та же', SOFT, 10.5);
        [[70, 70, 12, 18, 'широко'], [200, 40, 42, 18, 'узко'], [330, 48, 12, 40, 'выше']]
            .forEach(function (b) {
                var x = b[0], p = b[1], k = b[2], gh = b[3];
                s += '<rect x="' + x + '" y="' + (base - p) + '" width="' + w + '" height="' + p +
                    '" fill="' + LINK + '" opacity="0.78"/>';
                s += '<rect x="' + x + '" y="' + (base - p - k) + '" width="' + w + '" height="' + k +
                    '" fill="' + WARN + '" opacity="0.78"/>';
                s += '<rect x="' + x + '" y="' + (base - p - k - gh) + '" width="' + w + '" height="' + gh +
                    '" fill="' + MOSS + '" opacity="0.78"/>';
                s += txt(x + w / 2, base + 16, b[4], SOFT, 10);
            });
        s += '<line x1="55" y1="' + base + '" x2="400" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<rect x="70" y="182" width="12" height="10" fill="' + LINK + '" opacity="0.78"/>';
        s += txt(88, 191, 'p', SOFT, 10, 'start');
        s += '<rect x="130" y="182" width="12" height="10" fill="' + WARN + '" opacity="0.78"/>';
        s += txt(148, 191, '½&#961;v²', SOFT, 10, 'start');
        s += '<rect x="215" y="182" width="12" height="10" fill="' + MOSS + '" opacity="0.78"/>';
        s += txt(233, 191, '&#961;gh', SOFT, 10, 'start');
        return svg(W, H, s);
    };

    // 8. Два прибора из одной формулы: Вентури меряет расход, Пито — скорость.
    F.venturipitot = function () {
        var W = 450, H = 200, midY = 120;
        var s = flowPipe(20, 228, midY, 22, 11, 100, 140);
        s += arrow(28, midY, 52, midY, LINK, 'ahl');
        s += arrow(186, midY, 218, midY, WARN, 'ahw');
        // манометрические трубки: столбик воды тем ниже, чем быстрее течение под ним
        s += '<path d="M56,98 L56,52 M64,98 L64,52" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
        s += '<rect x="56" y="62" width="8" height="36" fill="' + LINK + '" opacity="0.7"/>';
        s += '<path d="M176,109 L176,52 M184,109 L184,52" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
        s += '<rect x="176" y="88" width="8" height="21" fill="' + WARN + '" opacity="0.7"/>';
        s += '<line x1="64" y1="62" x2="200" y2="62" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="184" y1="88" x2="200" y2="88" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += arrow(200, 62, 200, 88, SOFT, 'ah');
        s += txt(214, 78, '&#916;p', INK, 11, 'start');
        s += txt(124, 168, 'трубка Вентури', INK, 11);
        // трубка Пито: носик навстречу потоку, поток в нём останавливается
        [96, 120, 144].forEach(function (y) { s += arrow(258, y, 330, y, LINK, 'ahl'); });
        s += '<path d="M352,110 A10,10 0 0 0 352,130 L428,130 L428,110 Z" fill="none" stroke="' +
            INK + '" stroke-width="2"/>';
        s += '<circle cx="343" cy="120" r="4" fill="' + WARN + '"/>';
        s += txt(352, 100, 'v = 0', WARN, 10.5, 'start');
        s += '<circle cx="404" cy="130" r="2.5" fill="' + INK + '"/>';
        s += txt(404, 146, 'p', SOFT, 10);
        s += txt(348, 168, 'трубка Пито', INK, 11);
        s += txt(W / 2, H - 8, 'перепад давления меряет и расход, и скорость', SOFT, 10.5);
        return svg(W, H, s);
    };


    // ── Гидростатика: давление в покоящейся жидкости ─────────────────────────

    // Давление: сила на площадку строго по нормали, касательной составляющей нет.
    F.presarea = function () {
        var W = 430, H = 178;
        var s = txt(W / 2, 24, 'жидкость в покое давит только по нормали', INK, 11.5);
        s += '<rect x="52" y="44" width="216" height="112" fill="' + LINK + '" opacity="0.08"/>';
        s += '<line x1="120" y1="132" x2="220" y2="92" stroke="' + INK + '" stroke-width="3"/>';
        s += txt(170, 150, 'площадка A', SOFT, 10.5);
        s += arrow(170, 112, 148, 57, LINK, 'ahl');
        s += txt(134, 48, 'F⊥', LINK, 12.5);
        s += arrow(170, 112, 216, 94, WARN, 'ahw');
        s += '<line x1="184" y1="95" x2="200" y2="111" stroke="' + WARN + '" stroke-width="1.6"/>';
        s += '<line x1="200" y1="95" x2="184" y2="111" stroke="' + WARN + '" stroke-width="1.6"/>';
        s += txt(244, 126, 'сдвига нет', WARN, 10.5);
        s += txt(350, 92, 'p = F⊥ / A', INK, 16);
        s += txt(350, 116, 'Па = Н / м²', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Клин в жидкости: площади граней сокращаются, вес исчезает быстрее — давления равны.
    F.presiso = function () {
        var W = 430, H = 204, ax = 118, ay = 152, bx = 252, cy = 66;
        var s = txt(W / 2, 24, 'клин в жидкости: три грани, три силы давления', INK, 11.5);
        s += '<path d="M' + ax + ',' + ay + ' L' + bx + ',' + ay + ' L' + ax + ',' + cy +
             ' Z" fill="' + LINK + '" opacity="0.16" stroke="' + LINK + '" stroke-width="1.4"/>';
        s += arrow(84, 106, 112, 106, LINK, 'ahl');
        s += txt(78, 110, 'сбоку', LINK, 10.5, 'end');
        s += arrow(178, 178, 178, 158, LINK, 'ahl');
        s += txt(214, 176, 'снизу', LINK, 10.5);
        s += arrow(210, 70, 192, 99, LINK, 'ahl');
        s += txt(258, 58, 'на наклонную грань', LINK, 10.5);
        s += arrow(150, 112, 150, 142, SOFT);
        s += txt(150, 106, 'вес', SOFT, 10);
        s += txt(350, 96, 'силы давления ∝ L²', LINK, 10.5);
        s += txt(350, 116, 'вес ∝ L³', SOFT, 10.5);
        s += txt(350, 144, 'L → 0', INK, 12.5);
        s += txt(W / 2, H - 8, 'уменьшаем клин — вес исчезает быстрее сил давления', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Закон Паскаля и гидравлический пресс: добавка доходит до каждой точки.
    F.pascalram = function () {
        var W = 430, H = 200;
        var s = txt(W / 2, 22, 'добавленное давление доходит до каждой точки', INK, 11.5);
        s += '<path d="M62,86 L104,86 L104,128 L326,128 L326,70 L392,70 L392,158 L62,158 Z" fill="' +
             LINK + '" opacity="0.16" stroke="' + LINK + '" stroke-width="1.2"/>';
        s += '<rect x="62" y="78" width="42" height="8" fill="' + INK + '"/>';
        s += '<rect x="326" y="62" width="66" height="8" fill="' + INK + '"/>';
        s += arrow(83, 42, 83, 74, WARN, 'ahw');
        s += txt(83, 34, 'F₁', WARN, 12.5);
        s += txt(83, 106, 'A₁', SOFT, 11.5);
        s += arrow(359, 58, 359, 26, LINK, 'ahl');
        s += txt(359, 18, 'F₂', LINK, 12.5);
        s += txt(359, 90, 'A₂', SOFT, 11.5);
        s += txt(214, 148, 'p = F₁/A₁ = F₂/A₂', INK, 13);
        s += txt(W / 2, H - 8, 'выигрыш в силе равен отношению площадей, в работе — нет', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Столбик жидкости: разность давлений сверху и снизу держит его вес.
    F.depthslab = function () {
        var W = 430, H = 206, sur = 62, bot = 184, hb = 146;
        var s = txt(W / 2, 22, 'вертикальный столбик жидкости в равновесии', INK, 11.5);
        s += '<rect x="58" y="' + sur + '" width="316" height="' + (bot - sur) + '" fill="' + LINK + '" opacity="0.12"/>';
        s += '<line x1="58" y1="' + sur + '" x2="374" y2="' + sur + '" stroke="' + LINK + '" stroke-width="1.6"/>';
        s += txt(70, sur - 8, 'p₀', SOFT, 11.5);
        s += '<rect x="196" y="' + sur + '" width="54" height="' + (hb - sur) + '" fill="' + LINK +
             '" opacity="0.22" stroke="' + LINK + '" stroke-dasharray="4,3"/>';
        s += arrow(223, sur - 30, 223, sur - 4, INK);
        s += txt(300, sur - 16, 'p₀ · A', INK, 11.5);
        s += arrow(223, hb + 32, 223, hb + 5, LINK, 'ahl');
        s += txt(306, hb + 28, 'p(h) · A', LINK, 11.5);
        s += arrow(223, sur + 24, 223, sur + 54, WARN, 'ahw');
        s += txt(190, sur + 56, 'ρghA', WARN, 11.5, 'end');
        s += arrow(88, sur, 88, hb, SOFT);
        s += arrow(88, hb, 88, sur, SOFT);
        s += txt(78, (sur + hb) / 2 + 4, 'h', INK, 13, 'end');
        s += txt(W / 2, H - 8, 'разность давлений сверху и снизу равна весу столбика', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Гидростатический парадокс: форма разная, глубина и площадь дна одни.
    F.shapeparadox = function () {
        var W = 430, H = 210, top = 58, base = 138;
        var s = txt(W / 2, 24, 'разная форма, одна глубина — одна сила на дно', INK, 11.5);
        var shapes = ['M64,%T L124,%T L124,%B L64,%B Z',
                      'M156,%T L266,%T L242,%B L182,%B Z',
                      'M318,%T L346,%T L362,%B L302,%B Z'];
        shapes.forEach(function (d) {
            s += '<path d="' + d.split('%T').join(top).split('%B').join(base) + '" fill="' + LINK +
                 '" opacity="0.16" stroke="' + LINK + '" stroke-width="1.4"/>';
        });
        s += '<line x1="40" y1="' + top + '" x2="392" y2="' + top +
             '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="5,4"/>';
        s += arrow(44, top, 44, base, SOFT);
        s += arrow(44, base, 44, top, SOFT);
        s += txt(34, (top + base) / 2 + 4, 'h', INK, 13, 'end');
        [94, 212, 332].forEach(function (x) { s += arrow(x, base + 32, x, base + 6, WARN, 'ahw'); });
        s += txt(W / 2, base + 46, 'сила на дно одна и та же', WARN, 11);
        s += txt(W / 2, H - 8, 'лишний вес несут наклонные стенки', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Сообщающиеся сосуды: на общем уровне давления равны.
    F.commvessel = function () {
        var W = 430, H = 210;
        var s = txt(W / 2, 22, 'сообщающиеся сосуды: две несмешивающиеся жидкости', INK, 11.5);
        s += '<path d="M92,86 L122,86 L122,138 L192,138 L192,168 L92,168 Z" fill="' + LINK + '" opacity="0.34"/>';
        s += '<path d="M192,138 L262,138 L262,56 L292,56 L292,168 L192,168 Z" fill="' + WARN + '" opacity="0.20"/>';
        s += '<path d="M92,44 L92,168 L292,168 L292,44" fill="none" stroke="' + BORD + '" stroke-width="2"/>';
        s += '<path d="M122,44 L122,138 L262,138 L262,44" fill="none" stroke="' + BORD + '" stroke-width="2"/>';
        s += '<line x1="66" y1="138" x2="330" y2="138" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="5,4"/>';
        s += txt(372, 142, 'общий уровень', SOFT, 10);
        s += txt(107, 80, 'ρ₁', INK, 11.5);
        s += txt(277, 50, 'ρ₂', INK, 11.5);
        s += arrow(76, 86, 76, 138, SOFT);
        s += arrow(76, 138, 76, 86, SOFT);
        s += txt(66, 116, 'h₁', INK, 11.5, 'end');
        s += arrow(308, 56, 308, 138, SOFT);
        s += arrow(308, 138, 308, 56, SOFT);
        s += txt(318, 100, 'h₂', INK, 11.5, 'start');
        s += txt(W / 2, 188, 'ρ₁h₁ = ρ₂h₂', INK, 13);
        s += txt(W / 2, H - 8, 'высоты столбов обратны плотностям', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Архимед из разности давлений на нижнюю и верхнюю грань.
    F.archslab = function () {
        var W = 430, H = 210, sur = 58, bot = 190;
        var s = txt(W / 2, 22, 'силы давления на грани погружённого бруска', INK, 11.5);
        s += '<rect x="52" y="' + sur + '" width="326" height="' + (bot - sur) + '" fill="' + LINK + '" opacity="0.12"/>';
        s += '<line x1="52" y1="' + sur + '" x2="378" y2="' + sur + '" stroke="' + LINK + '" stroke-width="1.6"/>';
        s += txt(66, sur - 8, 'p₀', SOFT, 11.5);
        s += '<rect x="172" y="104" width="92" height="54" fill="' + INK + '" opacity="0.14" stroke="' + INK + '" stroke-width="1.4"/>';
        [190, 218, 246].forEach(function (x) { s += arrow(x, 78, x, 101, INK); });
        s += txt(322, 86, 'сверху', INK, 10.5);
        s += txt(322, 100, '(p₀+ρgh₁)·A', INK, 10.5);
        [190, 218, 246].forEach(function (x) { s += arrow(x, 186, x, 161, LINK, 'ahl'); });
        s += txt(322, 174, 'снизу', LINK, 10.5);
        s += txt(322, 188, '(p₀+ρgh₂)·A', LINK, 10.5);
        s += arrow(146, 131, 168, 131, SOFT);
        s += arrow(290, 131, 268, 131, SOFT);
        s += txt(218, 134, 'боковые гасятся', SOFT, 10);
        s += arrow(118, sur, 118, 104, SOFT);
        s += txt(108, 86, 'h₁', INK, 11, 'end');
        s += arrow(88, sur, 88, 158, SOFT);
        s += txt(78, 112, 'h₂', INK, 11, 'end');
        s += txt(W / 2, H - 8, 'разность этих сил и есть ρgV', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Плавание: доля погружённого объёма равна отношению плотностей.
    F.floatfrac = function () {
        var W = 430, H = 200, sur = 100, bot = 168;
        var s = txt(W / 2, 24, 'чем плотнее тело, тем глубже оно сидит', INK, 11.5);
        s += txt(W / 2, 50, 'доля под водой = ρтела / ρжидкости', INK, 12);
        s += '<rect x="44" y="' + sur + '" width="342" height="' + (bot - sur) + '" fill="' + LINK + '" opacity="0.14"/>';
        s += '<line x1="44" y1="' + sur + '" x2="386" y2="' + sur + '" stroke="' + LINK + '" stroke-width="1.6"/>';
        [[72, 0.25, '0,25'], [182, 0.6, '0,6'], [297, 0.9, '0,9']].forEach(function (b) {
            var x = b[0], f = b[1], hgt = 46;
            var t = Math.round(sur - hgt * (1 - f)), d = Math.round(sur + hgt * f);
            s += '<rect x="' + x + '" y="' + sur + '" width="66" height="' + (d - sur) +
                 '" fill="' + LINK + '" opacity="0.45"/>';
            s += '<rect x="' + x + '" y="' + t + '" width="66" height="' + hgt +
                 '" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
            s += txt(x + 33, 188, b[2], SOFT, 11);
        });
        return svg(W, H, s);
    };


    // ─────────── Космология, параграф 3: профиль массы и линзирование ───────────

    // Обращение кривой вращения: из v(r) точка за точкой получается M(r), а из неё — плотность.
    F.massprofile = function () {
        var W = 440, H = 206, top = 62, base = 148;
        var s = txt(W / 2, 24, 'кривую обращают точка за точкой', INK, 11.5);
        var px = [42, 174, 306], pw = 96, i, x, u;
        var titles = ['v(r): измерено', 'M(r) = v²r/G', 'ρ ∝ 1/r²'];
        for (i = 0; i < 3; i++) {
            s += '<line x1="' + px[i] + '" y1="' + base + '" x2="' + (px[i] + pw) + '" y2="' + base +
                '" stroke="' + BORD + '" stroke-width="1"/>';
            s += '<line x1="' + px[i] + '" y1="' + base + '" x2="' + px[i] + '" y2="' + top +
                '" stroke="' + BORD + '" stroke-width="1"/>';
            s += txt(px[i] + pw / 2, base + 18, titles[i], i === 0 ? WARN : LINK, 10.5);
        }
        // 1. измеренная кривая: подъём и плато, точками показаны сами замеры
        var vv = [];
        for (x = px[0] + 6; x <= px[0] + pw; x += 4) {
            u = (x - px[0]) / pw;
            vv.push(x + ',' + (base - 52 * Math.sqrt(Math.min(1, u / 0.28))));
        }
        s += '<polyline points="' + vv.join(' ') + '" fill="none" stroke="' + WARN + '" stroke-width="2.4"/>';
        for (i = 0; i < 5; i++) {
            s += '<circle cx="' + (px[0] + 30 + i * 16) + '" cy="' + (base - 52) + '" r="2.6" fill="' + WARN + '"/>';
        }
        // 2. масса внутри радиуса: на плато растёт линейно
        s += '<line x1="' + (px[1] + 4) + '" y1="' + (base - 6) + '" x2="' + (px[1] + pw) + '" y2="' + (base - 74) +
            '" stroke="' + LINK + '" stroke-width="2.4"/>';
        // 3. плотность: производная массы по объёму слоя падает как обратный квадрат
        var rr = [];
        for (x = px[2] + 18; x <= px[2] + pw; x += 3) {
            u = (x - px[2]) / pw;
            rr.push(x + ',' + (base - Math.min(80, 2.6 / (u * u))));
        }
        s += '<polyline points="' + rr.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += arrow(px[0] + pw + 8, base - 34, px[1] - 6, base - 34, SOFT);
        s += arrow(px[1] + pw + 8, base - 34, px[2] - 6, base - 34, SOFT);
        s += txt(W / 2, H - 8, 'масса растёт линейно, плотность падает как обратный квадрат', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Гравитационное линзирование: масса отклоняет луч, и источник виден не там, где он есть.
    F.lensdeflect = function () {
        var W = 440, H = 214, ax = 108, ox = 44, mx = 228, sx = 398, up = 74, dn = 142;
        var s = txt(W / 2, 20, 'масса отклоняет луч — и картинка смещается', INK, 11.5);
        // истинное направление на источник
        s += '<line x1="' + ox + '" y1="' + ax + '" x2="' + sx + '" y2="' + ax +
            '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="4 4"/>';
        // два луча, переломленные у массы
        s += '<polyline points="' + sx + ',' + ax + ' ' + mx + ',' + up + ' ' + ox + ',' + ax +
            '" fill="none" stroke="' + LINK + '" stroke-width="2"/>';
        s += '<polyline points="' + sx + ',' + ax + ' ' + mx + ',' + dn + ' ' + ox + ',' + ax +
            '" fill="none" stroke="' + LINK + '" stroke-width="2"/>';
        // продолжение назад: туда, где источник только кажется
        s += '<line x1="' + ox + '" y1="' + ax + '" x2="372" y2="47" stroke="' + SOFT +
            '" stroke-width="1" stroke-dasharray="3 4"/>';
        s += '<line x1="' + ox + '" y1="' + ax + '" x2="372" y2="169" stroke="' + SOFT +
            '" stroke-width="1" stroke-dasharray="3 4"/>';
        s += '<ellipse cx="372" cy="47" rx="13" ry="6" fill="' + SOFT + '" opacity="0.45"/>';
        s += '<ellipse cx="372" cy="169" rx="13" ry="6" fill="' + SOFT + '" opacity="0.45"/>';
        s += txt(360, 34, 'видимые положения', SOFT, 10);
        // масса-линза и прицельное расстояние
        s += '<circle cx="' + mx + '" cy="' + ax + '" r="16" fill="' + WARN + '" opacity="0.32"/>';
        s += txt(mx, ax + 4, 'M', WARN, 12);
        s += '<line x1="' + mx + '" y1="' + ax + '" x2="' + mx + '" y2="' + up +
            '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="3 3"/>';
        s += txt(mx + 8, 92, 'b', WARN, 11.5, 'start');
        s += txt(mx + 26, up - 4, '&#945;', LINK, 12, 'start');
        s += '<circle cx="' + ox + '" cy="' + ax + '" r="4" fill="' + INK + '"/>';
        s += txt(ox + 4, ax + 20, 'наблюдатель', SOFT, 10, 'start');
        s += '<ellipse cx="' + sx + '" cy="' + ax + '" rx="13" ry="6" fill="' + LINK + '" opacity="0.5"/>';
        s += txt(sx, ax + 22, 'источник', SOFT, 10);
        s += txt(W / 2, H - 8, 'угол отклонения вдвое больше ньютоновского', SOFT, 10.5);
        return svg(W, H, s);
    };


    /* ——— Явления переноса, §3: вязкость газа ——— */

    // Сдвиговое течение газа: дрейф мал, тепловое движение велико.
    F.gasshear = function () {
        var W = 440, H = 210, top = 62, bot = 168;
        var s = txt(W / 2, 22, 'дрейф мал, тепловая скорость велика', INK, 11.5);
        s += '<rect x="40" y="' + (top - 12) + '" width="356" height="12" fill="' + INK + '" opacity="0.18"/>';
        s += '<rect x="40" y="' + bot + '" width="356" height="12" fill="' + INK + '" opacity="0.18"/>';
        s += arrow(300, top - 22, 376, top - 22, INK);
        s += txt(338, top - 28, 'пластина едет', INK, 10.5);
        s += txt(120, bot + 30, 'пластина стоит', SOFT, 10.5);
        var xs = 78;
        for (var i = 0; i <= 4; i++) {
            var y = Math.round(bot - i * (bot - top) / 4);
            s += arrow(xs, y, xs + 8 + i * 16, y, LINK, 'ahl');
        }
        s += '<line x1="' + xs + '" y1="' + bot + '" x2="' + (xs + 72) + '" y2="' + top + '" stroke="' + LINK + '" stroke-width="1.4" stroke-dasharray="4,3"/>';
        s += txt(xs + 84, top + 4, 'u(y)', LINK, 12, 'start');
        var pts = [[238, 84], [292, 118], [226, 142], [318, 92], [272, 152]];
        var ang = [40, -55, 118, -142, 196];
        for (var k = 0; k < pts.length; k++) {
            s += mol(pts[k][0], pts[k][1], 5, SOFT);
            var a = ang[k] * Math.PI / 180;
            s += arrow(pts[k][0], pts[k][1], Math.round(pts[k][0] + 42 * Math.cos(a)), Math.round(pts[k][1] + 42 * Math.sin(a)), WARN, 'ahw');
        }
        s += txt(W - 18, 100, '&#10216;v&#10217; &#8776; 460 м/с', WARN, 11, 'end');
        s += txt(W - 18, 118, 'u — сантиметры в секунду', LINK, 11, 'end');
        return svg(W, H, s);
    };

    // Шесть направлений: на площадку приходит шестая часть потока с каждой стороны.
    F.sixways = function () {
        var W = 440, H = 210, cx = 150, cy = 112;
        var s = txt(W / 2, 22, 'шесть направлений — по одной шестой на каждое', INK, 11.5);
        s += '<rect x="' + (cx - 46) + '" y="' + (cy - 9) + '" width="92" height="18" fill="' + LINK + '" opacity="0.16" stroke="' + LINK + '" stroke-width="1.4"/>';
        s += txt(cx, cy + 5, 'A', LINK, 12);
        s += arrow(cx, cy - 60, cx, cy - 16, WARN, 'ahw');
        s += arrow(cx, cy + 60, cx, cy + 16, WARN, 'ahw');
        var dirs = [[-1, -1], [1, -1], [-1, 1], [1, 1]];
        for (var i = 0; i < dirs.length; i++) {
            s += arrow(cx + dirs[i][0] * 74, cy + dirs[i][1] * 46, cx + dirs[i][0] * 30, cy + dirs[i][1] * 18, SOFT);
        }
        s += txt(cx, cy - 70, 'сверху', WARN, 10.5);
        s += txt(cx, cy + 84, 'снизу', WARN, 10.5);
        s += txt(cx + 118, cy - 40, 'вдоль площадки —', SOFT, 10.5, 'start');
        s += txt(cx + 118, cy - 24, 'ничего не переносят', SOFT, 10.5, 'start');
        s += txt(cx + 118, cy + 24, '(1/6)&#183;n&#10216;v&#10217;', INK, 14, 'start');
        s += txt(cx + 118, cy + 44, 'в каждую сторону', INK, 10.5, 'start');
        return svg(W, H, s);
    };

    // Молекула приносит импульс того слоя, где столкнулась последний раз.
    F.momentumcarry = function () {
        var W = 450, H = 220, y0 = 120, dy = 50;
        var s = txt(W / 2, 22, 'молекула помнит слой, в котором столкнулась', INK, 11.5);
        var rows = [[y0 - dy, 'u(y+&#955;)', LINK], [y0, 'u(y)', SOFT], [y0 + dy, 'u(y&#8722;&#955;)', LINK]];
        for (var i = 0; i < rows.length; i++) {
            s += '<line x1="60" y1="' + rows[i][0] + '" x2="332" y2="' + rows[i][0] + '" stroke="' + BORD + '" stroke-width="1.2" stroke-dasharray="5,4"/>';
            s += txt(342, rows[i][0] + 4, rows[i][1], rows[i][2], 11.5, 'start');
        }
        s += '<line x1="60" y1="' + y0 + '" x2="332" y2="' + y0 + '" stroke="' + INK + '" stroke-width="2"/>';
        s += mol(160, y0 - dy, 6, WARN);
        s += arrow(160, y0 - dy + 9, 160, y0 + dy - 9, WARN, 'ahw');
        s += mol(250, y0 + dy, 6, LINK);
        s += arrow(250, y0 + dy - 9, 250, y0 - dy + 9, LINK, 'ahl');
        s += arrow(104, y0, 104, y0 - dy, SOFT);
        s += txt(96, y0 - 22, '&#955;', INK, 12, 'end');
        s += txt(W / 2, H - 12, 'разность приносимого = 2&#955;&#183;du/dy', INK, 12);
        return svg(W, H, s);
    };

    // Сборка вязкости: сколько носильщиков умножить на то, что приносит каждый.
    F.etaassemble = function () {
        var W = 450, H = 200;
        var s = txt(W / 2, 22, 'сколько носильщиков &#215; сколько приносит каждый', INK, 11.5);
        function box(x, w, l1, l2, col) {
            var t = '<rect x="' + x + '" y="44" width="' + w + '" height="58" rx="6" fill="' + col +
                '" opacity="0.12" stroke="' + col + '" stroke-width="1.3"/>';
            t += txt(x + w / 2, 68, l1, col, 12);
            t += txt(x + w / 2, 88, l2, col, 10.5);
            return t;
        }
        s += box(24, 136, '2 &#215; (1/6)&#183;n&#10216;v&#10217;', 'носильщиков через площадку', LINK);
        s += txt(172, 78, '&#215;', INK, 16);
        s += box(190, 136, 'm&#183;2&#955;&#183;du/dy', 'импульса приносит каждый', WARN);
        s += arrow(336, 73, 372, 73, INK);
        s += txt(408, 78, '&#964;', INK, 17);
        s += txt(W / 2, 138, '&#964; = (1/3)&#961;&#10216;v&#10217;&#955;&#183;du/dy', INK, 15);
        s += txt(W / 2, 166, '&#951; = (1/3)&#961;&#10216;v&#10217;&#955;', MOSS, 17);
        s += txt(W / 2, 188, 'трение получилось, а не было постулировано', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Концентрация сокращается: меньше носильщиков — длиннее перебежки.
    F.pcancel = function () {
        var W = 450, H = 214;
        var s = txt(W / 2, 22, 'носильщиков вдвое меньше — каждый идёт вдвое дальше', INK, 11.5);
        function vessel(x, n, step, cap) {
            var t = '<rect x="' + x + '" y="44" width="160" height="112" fill="none" stroke="' + BORD + '" stroke-width="1.6"/>';
            for (var i = 0; i < n; i++) {
                var r1 = Math.sin((i + 1) * 12.9898 + x) * 43758.5453, r2 = Math.sin((i + 1) * 78.233 + x) * 12345.678;
                var gx = x + 12 + (r1 - Math.floor(r1)) * 136, gy = 56 + (r2 - Math.floor(r2)) * 76;
                t += mol(Math.round(gx), Math.round(gy), 3.4, SOFT);
            }
            t += arrow(x + 18, 148, x + 18 + step, Math.round(148 - step * 0.45), LINK, 'ahl');
            t += txt(x + 80, 176, cap, INK, 11);
            return t;
        }
        s += vessel(26, 48, 34, 'плотный газ: пробег мал');
        s += vessel(258, 14, 76, 'разрежённый: пробег велик');
        s += txt(W / 2, 202, '&#961;&#955; = nm &#183; 1/(&#8730;2&#183;n&#963;): концентрация сокращается', MOSS, 12);
        return svg(W, H, s);
    };

    // Вязкость и температура: у газа растёт, у жидкости падает.
    F.etatemp = function () {
        var W = 440, H = 224, x0 = 62, x1 = 398, base = 178, top = 48;
        var s = txt(W / 2, 22, 'нагрев: газ густеет, жидкость жидеет', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base + '" stroke="' + BORD + '" stroke-width="1.4"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + top + '" stroke="' + BORD + '" stroke-width="1.4"/>';
        var gas = '', liq = '', span = base - top;
        for (var i = 0; i <= 40; i++) {
            var f = i / 40, X = Math.round(x0 + f * (x1 - x0));
            var Yg = Math.round(base - span * (0.16 + 0.50 * Math.sqrt(f)));
            var Yl = Math.round(base - span * (0.04 + 0.90 * Math.exp(-2.6 * f)));
            gas += (i ? ' L' : 'M') + X + ',' + Yg;
            liq += (i ? ' L' : 'M') + X + ',' + Yl;
        }
        s += '<path d="' + gas + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += '<path d="' + liq + '" fill="none" stroke="' + WARN + '" stroke-width="2.4"/>';
        s += txt(x1 - 6, top + 40, 'газ: &#8776; &#8730;T', LINK, 11.5, 'end');
        s += txt(x1 - 6, base - 14, 'жидкость: &#8776; exp(E/kT)', WARN, 11.5, 'end');
        s += txt(x1 + 8, base + 16, 'T', INK, 12, 'end');
        s += txt(x0 - 10, top + 4, '&#951;', INK, 13, 'end');
        s += txt(W / 2, H - 8, 'механизмы разные — потому и знак разный', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Три переноса из одного механизма: число, энергия, импульс.
    F.threetransports = function () {
        var W = 460, H = 232;
        var s = txt(W / 2, 22, 'один механизм — три коэффициента', INK, 11.5);
        var cols = [[16, 'диффузия', 'число частиц', 'D = (1/3)&#955;&#10216;v&#10217;', LINK],
                    [164, 'теплопроводность', 'энергия', '&#954; = (1/3)&#955;&#10216;v&#10217;&#961;c', WARN],
                    [312, 'вязкость', 'импульс', '&#951; = (1/3)&#955;&#10216;v&#10217;&#961;', MOSS]];
        for (var i = 0; i < cols.length; i++) {
            var x = cols[i][0], c = cols[i][4];
            s += '<rect x="' + x + '" y="46" width="132" height="118" rx="6" fill="' + c +
                '" opacity="0.10" stroke="' + c + '" stroke-width="1.3"/>';
            s += txt(x + 66, 68, cols[i][1], c, 11.5);
            s += txt(x + 66, 96, 'переносится:', SOFT, 10.5);
            s += txt(x + 66, 114, cols[i][2], INK, 12);
            s += txt(x + 66, 146, cols[i][3], INK, 12);
            s += arrow(x + 66, 170, x + 66, 190, SOFT);
        }
        s += txt(W / 2, 214, 'поток = &#8722;(1/3)&#955;&#10216;v&#10217; &#183; градиент того, что переносится', INK, 11.5);
        return svg(W, H, s);
    };

    // Число Прандтля: отношение двух коэффициентов переноса, шкала логарифмическая.
    F.prandtlbar = function () {
        var W = 460, H = 196, x0 = 46, x1 = 414, y = 114;
        var s = txt(W / 2, 22, 'число Прандтля: что расплывается быстрее — импульс или тепло', INK, 11);
        s += '<line x1="' + x0 + '" y1="' + y + '" x2="' + x1 + '" y2="' + y + '" stroke="' + BORD + '" stroke-width="1.6"/>';
        function pos(p) { return Math.round(x0 + (Math.log(p) / Math.LN10 + 2) / 6 * (x1 - x0)); }
        var marks = [[0.025, 'ртуть', WARN, -1], [0.7, 'газы', LINK, 1], [7, 'вода', LINK, -1], [1000, 'глицерин', MOSS, 1]];
        for (var i = 0; i < marks.length; i++) {
            var x = pos(marks[i][0]), up = marks[i][3] < 0, col = marks[i][2];
            s += '<line x1="' + x + '" y1="' + (y - 9) + '" x2="' + x + '" y2="' + (y + 9) + '" stroke="' + col + '" stroke-width="2.6"/>';
            s += txt(x, y + (up ? -34 : 36), marks[i][1], col, 11.5);
            s += txt(x, y + (up ? -18 : 22), String(marks[i][0]).replace('.', ','), SOFT, 10.5);
        }
        s += txt(W / 2, H - 12, 'у всех газов около 0,7 — переносчик-то один', SOFT, 11);
        return svg(W, H, s);
    };

    // Почему рекомбинация при трёх тысячах кельвинов, а не при ста пятидесяти восьми:
    // порог ионизации лежит далеко в хвосте распределения, но фотонов на девять порядков больше.
    F.phototail = function () {
        var W = 440, H = 196, base = 142, x0 = 46, x1 = 402, peak = 84, thr = 322;
        var s = txt(W / 2, 24, 'почему 3000 К, а не 158 000 К', INK, 11.5);
        function ord(x) {                       // u²e⁻ᵘ — форма планковского распределения по энергии
            var u = (x - x0) / 46;
            return base - peak * (u * u * Math.exp(-u)) / 0.5413;
        }
        var pts = [], tail = [], x;
        for (x = x0; x <= x1; x += 3) pts.push(x + ',' + ord(x).toFixed(1));
        for (x = thr; x <= x1; x += 3) tail.push(x + ',' + ord(x).toFixed(1));
        s += '<polygon points="' + thr + ',' + base + ' ' + tail.join(' ') + ' ' + x1 + ',' + base +
            '" fill="' + WARN + '" opacity="0.32"/>';
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.2"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + thr + '" y1="' + base + '" x2="' + thr + '" y2="52" stroke="' + WARN +
            '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += txt(thr + 5, 46, '13,6 эВ', WARN, 10.5, 'start');
        s += txt(x0 + 4, 46, 'на атом — полтора миллиарда фотонов', LINK, 10.5, 'start');
        s += arrow(392, 110, 358, 136, WARN, 'ahw');
        s += txt(W - 14, 104, 'хвост ещё ионизует', WARN, 10, 'end');
        s += txt(x1, base + 16, 'энергия фотона →', SOFT, 10, 'end');
        s += txt(W / 2, H - 8, 'хвост нарисован крупнее: на деле там один фотон из миллиарда', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Пятно известного размера: угол, под которым мы его видим, меряет геометрию пространства.
    F.flatangle = function () {
        var W = 450, H = 208, ytop = 80, ybot = 162, half = 34, ymid = (ytop + ybot) / 2;
        var s = txt(W / 2, 24, 'одна и та же линейка под разным углом', INK, 11.5);
        s += txt(W / 2, 46, 'размер пятна известен: докуда дошёл звук в плазме', SOFT, 10.5);
        [[80, 18, WARN, 'сфера', 'угол больше'],
         [225, 0, MOSS, 'плоскость', 'ровно 1°'],
         [370, -12, LINK, 'седло', 'угол меньше']].forEach(function (c) {
            var cx = c[0], bow = c[1], col = c[2];
            s += '<line x1="' + (cx - half) + '" y1="' + ytop + '" x2="' + (cx + half) + '" y2="' + ytop +
                '" stroke="' + INK + '" stroke-width="3"/>';
            s += '<path d="M' + (cx - half) + ',' + ytop + ' Q' + (cx - half / 2 - bow) + ',' + ymid +
                ' ' + cx + ',' + ybot + '" fill="none" stroke="' + col + '" stroke-width="1.6"/>';
            s += '<path d="M' + (cx + half) + ',' + ytop + ' Q' + (cx + half / 2 + bow) + ',' + ymid +
                ' ' + cx + ',' + ybot + '" fill="none" stroke="' + col + '" stroke-width="1.6"/>';
            var w = half / 2 + bow, k = 24 / Math.sqrt(w * w + 41 * 41),
                dx = (w * k).toFixed(1), dy = (41 * k).toFixed(1);
            s += '<path d="M' + (cx - dx) + ',' + (ybot - dy) + ' A24,24 0 0 1 ' +
                (cx - -dx) + ',' + (ybot - dy) + '" fill="none" stroke="' + SOFT + '" stroke-width="1"/>';
            s += '<circle cx="' + cx + '" cy="' + ybot + '" r="4" fill="' + INK + '"/>';
            s += txt(cx, ytop - 12, c[3], SOFT, 10);
            s += txt(cx, ybot + 22, c[4], col, 10.5);
        });
        s += txt(W / 2, H - 8, 'измеряют ровно градус — значит, пространство плоское', SOFT, 10.5);
        return svg(W, H, s);
    };

    // ─────────── Аналитическая механика, параграф 2: симметрии и теорема Нётер ───────────

    // Что такое сдвиг координаты: та же установка на новом месте, скорости прежние.
    F.shiftinvar = function () {
        var W = 430, H = 216, ground = 160, x1 = 76, dx = 140;
        function hill(x0, color, dash) {
            var p = '<path d="M' + x0 + ',' + ground + ' Q' + (x0 + 44) + ',' + (ground - 96) + ' ' +
                (x0 + 88) + ',' + ground + '" fill="none" stroke="' + color + '" stroke-width="2.2"' +
                (dash ? ' stroke-dasharray="5,4"' : '') + '/>';
            p += '<circle cx="' + (x0 + 26) + '" cy="' + (ground - 40) + '" r="7" fill="' + color + '"/>';
            p += arrow(x0 + 36, ground - 48, x0 + 62, ground - 64, color, dash ? 'ahl' : 'ah');
            return p;
        }
        var s = txt(W / 2, 22, 'сдвиг: та же установка на новом месте', INK, 11.5);
        s += '<line x1="52" y1="' + ground + '" x2="398" y2="' + ground + '" stroke="' + BORD + '" stroke-width="1.5"/>';
        s += hill(x1, INK, false);
        s += hill(x1 + dx, LINK, true);
        s += arrow(x1 + 44, 86, x1 + dx + 44, 86, SOFT);
        s += txt(x1 + dx / 2 + 44, 78, 'ε', INK, 13);
        s += txt(x1 + dx / 2 + 44, 104, 'скорость та же', SOFT, 10.5);
        s += txt(W / 2, 186, 'q → q + ε', INK, 13);
        s += txt(W / 2, H - 8, 'ε любое — значит, множитель при ε равен нулю', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Сдвиг сразу двух тел: взаимное расстояние прежнее, сохраняется сумма импульсов.
    F.shiftpair = function () {
        var W = 430, H = 224, y = 92;
        function spring(xa, xb, yy) {
            var w = (xb - xa) / 6, d = 'M' + xa + ',' + yy;
            for (var i = 0; i < 6; i++) {
                d += ' l' + (w / 2) + ',' + (i % 2 ? 7 : -7) + ' l' + (w / 2) + ',' + (i % 2 ? -7 : 7);
            }
            return '<path d="' + d + '" fill="none" stroke="' + SOFT + '" stroke-width="1.3"/>';
        }
        function span(xa, xb, yy) {
            var p = arrow(xa + 5, yy, xb - 5, yy, SOFT) + arrow(xb - 5, yy, xa + 5, yy, SOFT);
            p += '<line x1="' + xa + '" y1="' + (yy - 6) + '" x2="' + xa + '" y2="' + (yy + 6) +
                '" stroke="' + SOFT + '" stroke-width="1"/>';
            p += '<line x1="' + xb + '" y1="' + (yy - 6) + '" x2="' + xb + '" y2="' + (yy + 6) +
                '" stroke="' + SOFT + '" stroke-width="1"/>';
            p += txt((xa + xb) / 2, yy + 20, 'x₂ − x₁', SOFT, 11);
            return p;
        }
        function group(xa) {
            var p = spring(xa + 12, xa + 60, y);
            p += mol(xa, y, 12, LINK) + txt(xa, y + 4, '1', '#fff', 11);
            p += mol(xa + 72, y, 12, WARN) + txt(xa + 72, y + 4, '2', '#fff', 11);
            p += span(xa, xa + 72, y + 30);
            return p;
        }
        var s = txt(W / 2, 22, 'сдвигаем оба тела сразу', INK, 11.5);
        s += group(74);
        s += group(268);
        s += arrow(196, y, 244, y, INK);
        s += txt(220, y - 12, 'сдвиг на ε', INK, 11);
        s += txt(W / 2, 172, 'расстояние то же — лагранжиан не изменился', SOFT, 10.5);
        s += txt(W / 2, 196, '∂L/∂x₁ + ∂L/∂x₂ = 0   →   p₁ + p₂ = const', INK, 12.5);
        s += txt(W / 2, H - 8, 'сохраняется сумма импульсов, а не каждый по отдельности', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Угол как координата: обобщённый импульс оказывается моментом импульса.
    F.rotcoord = function () {
        var W = 430, H = 206, cx = 148, cy = 110, r = 62, a1 = -0.95, a2 = -1.55;
        function pt(a, rad) { return [cx + rad * Math.cos(a), cy + rad * Math.sin(a)]; }
        function ray(a, color, dash) {
            var p = pt(a, r);
            return '<line x1="' + cx + '" y1="' + cy + '" x2="' + p[0].toFixed(1) + '" y2="' + p[1].toFixed(1) +
                '" stroke="' + color + '" stroke-width="1.7"' + (dash ? ' stroke-dasharray="5,4"' : '') + '/>';
        }
        var p1 = pt(a1, r), q1 = pt(a2, 26), q2 = pt(a1, 26), m = pt((a1 + a2) / 2, 44);
        var s = txt(W / 2, 22, 'поворот на ε: радиус не меняется', INK, 11.5);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + BORD +
            '" stroke-width="1.4" stroke-dasharray="4,3"/>';
        s += ray(a1, INK, false) + ray(a2, LINK, true);
        s += '<path d="M' + q1[0].toFixed(1) + ',' + q1[1].toFixed(1) + ' A26,26 0 0 1 ' +
            q2[0].toFixed(1) + ',' + q2[1].toFixed(1) + '" fill="none" stroke="' + MOSS + '" stroke-width="1.6"/>';
        s += txt(m[0].toFixed(1), m[1].toFixed(1), 'ε', MOSS, 12.5);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="3" fill="' + SOFT + '"/>';
        s += mol(p1[0].toFixed(1), p1[1].toFixed(1), 7, INK);
        s += arrow(p1[0].toFixed(1), p1[1].toFixed(1), (p1[0] + 30 * Math.cos(a1)).toFixed(1),
            (p1[1] + 30 * Math.sin(a1)).toFixed(1), LINK, 'ahl');
        s += txt(230, 34, 'v<tspan baseline-shift="sub" font-size="8">r</tspan>', LINK, 12);
        s += arrow(p1[0].toFixed(1), p1[1].toFixed(1), (p1[0] - 34 * Math.sin(a1)).toFixed(1),
            (p1[1] + 34 * Math.cos(a1)).toFixed(1), MOSS, 'ah');
        s += txt(234, 94, 'r · ω', MOSS, 12);
        s += txt(176, 100, 'r', INK, 12);
        s += txt(330, 76, 'K = m(v<tspan baseline-shift="sub" font-size="8">r</tspan>² + r²ω²) / 2', INK, 11.5);
        s += txt(330, 104, 'U зависит только от r', SOFT, 10.5);
        s += txt(330, 128, 'угол в L не входит', SOFT, 10.5);
        s += txt(330, 158, '∂L/∂ω = m r² ω', MOSS, 12.5);
        s += txt(W / 2, H - 8, 'момент импульса — обобщённый импульс для угла', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Однородность времени: тот же опыт, начатый позже, — и сохранение энергии.
    F.timeshift = function () {
        var W = 430, H = 224;
        function run(x0, y, color, dash) {
            var p = '<line x1="52" y1="' + y + '" x2="326" y2="' + y + '" stroke="' + BORD + '" stroke-width="1.2"/>';
            p += '<path d="M' + x0 + ',' + y + ' q30,-40 60,0 q30,40 60,0" fill="none" stroke="' + color +
                '" stroke-width="2.4"' + (dash ? ' stroke-dasharray="5,4"' : '') + '/>';
            p += '<circle cx="' + x0 + '" cy="' + y + '" r="4.5" fill="' + color + '"/>';
            p += '<line x1="' + x0 + '" y1="' + y + '" x2="' + x0 + '" y2="172" stroke="' + SOFT +
                '" stroke-width="1" stroke-dasharray="3,3"/>';
            return p;
        }
        var s = txt(W / 2, 22, 'опыт, начатый позже, идёт точно так же', INK, 11.5);
        s += run(84, 76, INK, false);
        s += run(148, 138, LINK, true);
        s += txt(368, 72, 'старт', SOFT, 10.5) + txt(368, 88, 't₀', INK, 11.5);
        s += txt(368, 134, 'старт', SOFT, 10.5) + txt(368, 150, 't₀ + ε', INK, 11.5);
        s += arrow(84, 180, 148, 180, INK);
        s += txt(116, 196, 'ε', INK, 12.5);
        s += txt(268, 190, 'E = p · v − L = K + U', MOSS, 12.5);
        s += txt(W / 2, H - 8, 'сдвиг во времени даёт сохранение энергии', SOFT, 10.5);
        return svg(W, H, s);
    };

    // ── Принцип наименьшего действия: механика варьирования ──

    // Пробный путь: истинный плюс горб eta(t), прижатый к нулю на обоих концах.
    F.actiontrial = function () {
        var W = 430, H = 238, x0 = 72, x1 = 356, yA = 128;
        var s = txt(W / 2, 22, 'пробный путь: истинный плюс горб с множителем ε', INK, 11.5);
        s += '<path d="M' + x0 + ',' + yA + ' Q214,4 ' + x1 + ',' + yA + '" fill="none" stroke="' + SOFT +
             '" stroke-width="1.3" stroke-dasharray="5,4"/>';
        s += '<path d="M' + x0 + ',' + yA + ' Q214,104 ' + x1 + ',' + yA + '" fill="none" stroke="' + SOFT +
             '" stroke-width="1.3" stroke-dasharray="5,4"/>';
        s += '<path d="M' + x0 + ',' + yA + ' Q214,54 ' + x1 + ',' + yA + '" fill="none" stroke="' + LINK +
             '" stroke-width="2.6"/>';
        s += '<circle cx="' + x0 + '" cy="' + yA + '" r="5" fill="' + INK + '"/>';
        s += '<circle cx="' + x1 + '" cy="' + yA + '" r="5" fill="' + INK + '"/>';
        s += txt(x0 - 14, yA + 5, 'A', INK, 12, 'end');
        s += txt(x1 + 14, yA + 5, 'B', INK, 12, 'start');
        s += txt(214, 50, 'ε > 0', SOFT, 10.5);
        s += txt(214, 84, 'истинный', LINK, 11);
        s += txt(214, 132, 'ε < 0', SOFT, 10.5);
        s += '<line x1="' + x0 + '" y1="196" x2="' + x1 + '" y2="196" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<path d="M' + x0 + ',196 Q214,156 ' + x1 + ',196" fill="none" stroke="' + MOSS + '" stroke-width="2"/>';
        s += '<circle cx="' + x0 + '" cy="196" r="3.5" fill="' + MOSS + '"/>';
        s += '<circle cx="' + x1 + '" cy="196" r="3.5" fill="' + MOSS + '"/>';
        s += txt(214, 168, 'η(t)', MOSS, 12);
        s += txt(x0, 212, 'η = 0', MOSS, 10.5);
        s += txt(x1, 212, 'η = 0', MOSS, 10.5);
        s += txt(W / 2, H - 8, 'форма горба любая, концы прижаты', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Разложение S(eps): в минимуме линейный член обязан отсутствовать.
    F.actionorder = function () {
        var W = 430, H = 228, cx = 210, minY = 152, axisY = 198;
        var s = txt(W / 2, 22, 'что означает «первый порядок обязан обнулиться»', INK, 11.5);
        s += txt(W / 2, 44, 'S(ε) = S₀ + c₁·ε + c₂·ε² + …', INK, 12);
        s += '<line x1="60" y1="' + axisY + '" x2="360" y2="' + axisY + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(370, axisY + 4, 'ε', SOFT, 12, 'start');
        s += '<line x1="' + cx + '" y1="62" x2="' + cx + '" y2="204" stroke="' + BORD +
             '" stroke-width="1" stroke-dasharray="3 3"/>';
        var pts = [];
        for (var dx = -116; dx <= 116; dx += 4) pts.push((cx + dx) + ',' + (minY - 0.0056 * dx * dx).toFixed(1));
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += '<line x1="' + (cx - 66) + '" y1="' + minY + '" x2="' + (cx + 66) + '" y2="' + minY +
             '" stroke="' + MOSS + '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += '<circle cx="' + cx + '" cy="' + minY + '" r="5" fill="' + MOSS + '"/>';
        s += txt(cx - 74, minY - 4, 'c₁ = 0', MOSS, 11, 'end');
        s += '<line x1="' + (cx - 62) + '" y1="' + (minY - 28) + '" x2="' + (cx + 62) + '" y2="' + (minY + 28) +
             '" stroke="' + WARN + '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += arrow(cx + 26, minY + 12, cx + 58, minY + 26, WARN, 'ahw');
        s += txt(cx + 72, minY + 34, 'c₁ ≠ 0: есть куда упасть', WARN, 10.5, 'start');
        s += txt(W / 2, H - 8, 'ненулевой наклон в нуле означает: рядом есть путь дешевле', SOFT, 10);
        return svg(W, H, s);
    };

    // Цепное правило: добавка шевелит и координату, и наклон.
    F.actionchain = function () {
        var W = 430, H = 222;
        var s = txt(W / 2, 22, 'сдвиг пути меняет сразу две вещи', INK, 11.5);
        s += '<line x1="48" y1="152" x2="178" y2="116" stroke="' + LINK + '" stroke-width="2.6"/>';
        s += '<line x1="48" y1="132" x2="178" y2="80" stroke="' + SOFT +
             '" stroke-width="1.4" stroke-dasharray="5,4"/>';
        s += arrow(113, 134, 113, 106, LINK, 'ahl');
        s += txt(107, 126, 'ε·η', LINK, 11, 'end');
        s += txt(113, 176, 'наклоны разные', SOFT, 10);
        s += txt(218, 104, 'сдвиг координаты', LINK, 10.5, 'start');
        s += arrow(320, 100, 344, 100, LINK, 'ahl');
        s += txt(350, 104, '∂L/∂y', LINK, 11, 'start');
        s += txt(218, 140, 'сдвиг наклона', MOSS, 10.5, 'start');
        s += arrow(320, 136, 344, 136, MOSS, 'ah');
        s += txt(350, 140, '∂L/∂y′', MOSS, 11, 'start');
        s += txt(W / 2, 198, 'штрих — производная по времени', SOFT, 10);
        s += txt(W / 2, H - 8, 'два слагаемых вариации — это цепное правило, ничего больше', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Интегрирование по частям: производная переезжает, граничный член гибнет.
    F.actionparts = function () {
        var W = 430, H = 214, x0 = 72, x1 = 356;
        var s = txt(W / 2, 22, 'производная переезжает с горба на импульсный множитель', INK, 11);
        s += '<rect x="48" y="40" width="136" height="34" fill="' + LINK + '" opacity="0.12" stroke="' + BORD +
             '" stroke-width="1.2"/>';
        s += txt(116, 62, '∂L/∂y′ · η′', LINK, 12);
        s += '<rect x="248" y="40" width="134" height="34" fill="' + LINK + '" opacity="0.12" stroke="' + BORD +
             '" stroke-width="1.2"/>';
        s += txt(315, 62, '− (∂L/∂y′)′ · η', LINK, 12);
        s += '<path d="M188,57 Q216,84 240,57" fill="none" stroke="' + INK +
             '" stroke-width="1.6" marker-end="url(#ah)"/>';
        s += txt(216, 98, 'по частям', SOFT, 10);
        s += txt(206, 126, '[ ∂L/∂y′ · η ] на концах', WARN, 11);
        s += '<line x1="132" y1="122" x2="280" y2="122" stroke="' + WARN + '" stroke-width="1.4"/>';
        s += txt(292, 126, '= 0', WARN, 11.5, 'start');
        s += '<line x1="' + x0 + '" y1="168" x2="' + x1 + '" y2="168" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<path d="M' + x0 + ',168 Q214,140 ' + x1 + ',168" fill="none" stroke="' + MOSS + '" stroke-width="2"/>';
        s += '<circle cx="' + x0 + '" cy="168" r="3.5" fill="' + MOSS + '"/>';
        s += '<circle cx="' + x1 + '" cy="168" r="3.5" fill="' + MOSS + '"/>';
        s += txt(x0, 186, 'η = 0', MOSS, 10.5);
        s += txt(x1, 186, 'η = 0', MOSS, 10.5);
        s += txt(W / 2, H - 8, 'граничный член гибнет: концы закреплены', SOFT, 10.5);
        return svg(W, H, s);
    };


    // — Броуновское движение: как увидели молекулы —

    // 1. Удары со всех сторон почти гасятся; остаётся перевес порядка корня из их числа.
    F.brownkick = function () {
        var W = 430, H = 215, cx = 196, cy = 112, R = 32, i, a, x1, y1, x2, y2;
        var s = txt(W / 2, 24, 'удары со всех сторон почти гасятся', INK, 11.5);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="' + LINK +
             '" opacity="0.18" stroke="' + LINK + '" stroke-width="1.6"/>';
        for (i = 0; i < 16; i++) {
            a = i * Math.PI * 2 / 16 + 0.19;
            x1 = (cx + Math.cos(a) * (R + 38)).toFixed(1);
            y1 = (cy + Math.sin(a) * (R + 38) * 0.78).toFixed(1);
            x2 = (cx + Math.cos(a) * (R + 7)).toFixed(1);
            y2 = (cy + Math.sin(a) * (R + 7) * 0.78).toFixed(1);
            s += '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 +
                 '" stroke="' + SOFT + '" stroke-width="1.3" marker-end="url(#ah)" opacity="0.6"/>';
        }
        s += txt(cx, cy + 4, 'зерно', INK, 11);
        s += arrow(cx + R - 4, cy - 10, cx + R + 58, cy - 32, WARN, 'ahw');
        s += txt(cx + R + 66, cy - 38, 'перевес', WARN, 11, 'start');
        s += txt(W / 2, H - 26, 'N ≈ 10²⁰ ударов в секунду', SOFT, 10.5);
        s += txt(W / 2, H - 8, 'перевес ~ √N, то есть доля 1/√N от всех ударов', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 2. Случайное блуждание: ломаная из N одинаковых шагов со случайными направлениями.
    F.randwalk = function () {
        var W = 430, H = 215, x = 96, y = 132, i, p, baseY = 178;
        var d = [[24, -10], [-14, 18], [26, 4], [8, -19], [-16, -14], [25, -6], [14, 17],
                 [-9, 20], [24, 8], [18, -16], [-12, -18], [26, -3], [10, 19], [22, 6]];
        var poly = [x + ',' + y];
        for (i = 0; i < d.length; i++) { x += d[i][0]; y += d[i][1]; poly.push(x + ',' + y); }
        var s = txt(W / 2, 24, 'путь длинный, смещение короткое', INK, 11.5);
        s += '<polyline points="' + poly.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2"/>';
        for (i = 1; i < poly.length - 1; i++) {
            p = poly[i].split(',');
            s += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="2.4" fill="' + LINK + '"/>';
        }
        s += '<circle cx="96" cy="132" r="4.5" fill="' + INK + '"/>';
        s += '<circle cx="' + x + '" cy="' + y + '" r="4.5" fill="' + WARN + '"/>';
        s += txt(92, 122, 'старт', SOFT, 10.5, 'end');
        s += txt(x + 8, y - 8, 'через N шагов', SOFT, 10.5, 'start');
        s += '<line x1="96" y1="132" x2="96" y2="' + baseY + '" stroke="' + SOFT +
             '" stroke-width="1" stroke-dasharray="3 3"/>';
        s += '<line x1="' + x + '" y1="' + y + '" x2="' + x + '" y2="' + baseY + '" stroke="' + SOFT +
             '" stroke-width="1" stroke-dasharray="3 3"/>';
        s += arrow(96, baseY, x, baseY, WARN, 'ahw');
        s += arrow(x, baseY, 96, baseY, WARN, 'ahw');
        s += txt((96 + x) / 2, baseY - 7, 'смещение x', WARN, 11);
        s += txt(W / 2, H - 26, 'длина пути N·ℓ растёт как N', SOFT, 10.5);
        s += txt(W / 2, H - 8, 'смещение растёт как √N', INK, 11);
        return svg(W, H, s);
    };

    // 3. Квадрат суммы: диагональ выживает, перекрёстные члены в среднем гасятся.
    F.sumsquare = function () {
        var W = 430, H = 220, n = 6, c = 20, x0 = 60, y0 = 52, i, j, dg;
        var s = txt(W / 2, 24, 'квадрат суммы: что переживает усреднение', INK, 11.5);
        for (i = 0; i < n; i++) for (j = 0; j < n; j++) {
            dg = (i === j);
            s += '<rect x="' + (x0 + j * c) + '" y="' + (y0 + i * c) + '" width="' + (c - 2) +
                 '" height="' + (c - 2) + '" fill="' + (dg ? LINK : SOFT) +
                 '" opacity="' + (dg ? 0.55 : 0.10) + '" stroke="' + BORD + '" stroke-width="0.8"/>';
        }
        s += txt(x0 + n * c / 2, y0 - 8, 'i', SOFT, 10.5);
        s += txt(x0 - 10, y0 + n * c / 2, 'j', SOFT, 10.5, 'end');
        s += txt(x0 + n * c + 16, y0 + 22, 'ℓᵢ² — всегда положительны', LINK, 11, 'start');
        s += txt(x0 + n * c + 16, y0 + 56, 'ℓᵢℓⱼ — в среднем нуль', SOFT, 11, 'start');
        s += txt(x0 + n * c + 16, y0 + 88, 'их больше, но они гасятся', SOFT, 10.5, 'start');
        s += txt(W / 2, H - 26, 'остаётся только диагональ: N членов', INK, 11);
        s += txt(W / 2, H - 8, '⟨x²⟩ = N·ℓ²', INK, 13);
        return svg(W, H, s);
    };

    // 4. Корень из времени: чтобы уйти вдвое дальше, нужно вчетверо больше времени.
    F.sqrtt = function () {
        var W = 430, H = 210, x0 = 66, x1 = 392, base = 152, top = 46, pts = [], x, u, xq, yq;
        var s = txt(W / 2, 24, 'вчетверо дольше — вдвое дальше', INK, 11.5);
        for (x = x0; x <= x1; x += 3) {
            u = (x - x0) / (x1 - x0);
            pts.push(x + ',' + (base - (base - top) * Math.sqrt(u)).toFixed(1));
        }
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.6"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + top + '" stroke="' + BORD + '" stroke-width="1"/>';
        xq = x0 + (x1 - x0) * 0.25; yq = base - (base - top) * 0.5;
        s += '<line x1="' + xq + '" y1="' + base + '" x2="' + xq + '" y2="' + yq + '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += '<line x1="' + x0 + '" y1="' + yq + '" x2="' + xq + '" y2="' + yq + '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += '<circle cx="' + xq + '" cy="' + yq + '" r="3.4" fill="' + WARN + '"/>';
        s += '<line x1="' + x1 + '" y1="' + base + '" x2="' + x1 + '" y2="' + top + '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += '<line x1="' + x0 + '" y1="' + top + '" x2="' + x1 + '" y2="' + top + '" stroke="' + WARN + '" stroke-width="1.2" stroke-dasharray="4 4"/>';
        s += '<circle cx="' + x1 + '" cy="' + top + '" r="3.4" fill="' + WARN + '"/>';
        s += txt(xq, base + 16, 't', INK, 11);
        s += txt(x1 - 8, base + 16, '4t', INK, 11);
        s += txt(x0 - 6, yq + 4, 'x', INK, 11, 'end');
        s += txt(x0 - 6, top + 4, '2x', INK, 11, 'end');
        s += txt(x1, base + 34, 'время →', SOFT, 10, 'end');
        s += txt(x0 + 10, top - 8, '√⟨x²⟩ = √(2Dt)', LINK, 11, 'start');
        s += txt(W / 2, H - 6, 'кривая круче всего в начале', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 5. Равновесие взвеси в поле тяжести: концентрация падает вверх по экспоненте.
    F.sedimbal = function () {
        var W = 430, H = 235, xL = 84, xR = 200, yT = 48, yB = 190, i, j, gx, u, yy, x2 = 300;
        var s = txt(W / 2, 24, 'взвесь в поле тяжести приходит в равновесие', INK, 11.5);
        s += '<rect x="' + xL + '" y="' + yT + '" width="' + (xR - xL) + '" height="' + (yB - yT) +
             '" fill="' + LINK + '" opacity="0.07" stroke="' + BORD + '" stroke-width="1"/>';
        var rows = [[182, 8], [166, 7], [150, 5], [134, 4], [118, 3], [102, 2], [86, 2], [70, 1], [56, 1]];
        for (i = 0; i < rows.length; i++) for (j = 0; j < rows[i][1]; j++) {
            gx = xL + 12 + ((j * 31 + i * 17) % (xR - xL - 24));
            s += mol(gx, rows[i][0], 3.2, LINK);
        }
        s += arrow(xL - 18, 96, xL - 18, 168, INK);
        s += txt(xL - 24, 134, 'оседание', INK, 10.5, 'end');
        s += arrow(xR + 18, 168, xR + 18, 96, LINK, 'ahl');
        s += txt(xR + 24, 134, 'диффузия', LINK, 10.5, 'start');
        var env = [];
        for (i = 0; i <= 40; i++) {
            u = i / 40; yy = yB - (yB - yT) * u;
            env.push((x2 + 92 * Math.exp(-2.6 * u)).toFixed(1) + ',' + yy.toFixed(1));
        }
        s += '<line x1="' + x2 + '" y1="' + yB + '" x2="' + x2 + '" y2="' + yT + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x2 + '" y1="' + yB + '" x2="' + (x2 + 104) + '" y2="' + yB + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<polyline points="' + env.join(' ') + '" fill="none" stroke="' + WARN + '" stroke-width="2.2"/>';
        s += txt(x2 - 6, yT + 6, 'h', SOFT, 10.5, 'end');
        s += txt(x2 + 104, yB + 16, 'n', SOFT, 10.5, 'end');
        s += txt(x2 + 52, yT - 10, 'n = n₀e^(−mgh/kT)', WARN, 11);
        s += txt(W / 2, H - 8, 'встречные потоки равны — картина не меняется', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 6. Баланс потоков даёт соотношение Эйнштейна: и концентрация, и сила сокращаются.
    F.fluxbal = function () {
        var W = 430, H = 205;
        var s = txt(W / 2, 24, 'в равновесии два потока равны', INK, 11.5);
        s += '<rect x="34" y="46" width="150" height="76" fill="' + INK + '" opacity="0.06" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(109, 66, 'снос силой', INK, 11);
        s += arrow(56, 90, 162, 90, INK);
        s += txt(109, 112, 'j = n·F/γ', INK, 12);
        s += '<rect x="246" y="46" width="150" height="76" fill="' + LINK + '" opacity="0.10" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(321, 66, 'диффузия', LINK, 11);
        s += arrow(374, 90, 268, 90, LINK, 'ahl');
        s += txt(321, 112, 'j = −D·dn/dx', LINK, 12);
        s += txt(215, 96, '=', INK, 18);
        s += txt(W / 2, 150, 'подставили n = n₀e^(−Fx/kT) — сократились и n, и F', SOFT, 10.5);
        s += txt(W / 2, 178, 'D = kT/γ', INK, 15);
        s += txt(W / 2, H - 6, 'трение и разброс задаются одной величиной', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 7. Стоксово трение шара: γ = 6πηa — здесь в формулу входит размер частицы.
    F.stokesgam = function () {
        var W = 430, H = 215, cx = 190, cy = 100, R = 30, i, yy, bow;
        var s = txt(W / 2, 24, 'откуда берётся коэффициент трения', INK, 11.5);
        for (i = -2; i <= 2; i++) {
            yy = cy + i * 20;
            bow = (i === 0) ? 0 : (i > 0 ? 1 : -1) * (52 - Math.abs(i) * 14);
            s += '<path d="M56,' + yy + ' Q' + cx + ',' + (yy + bow) + ' 330,' + yy +
                 '" fill="none" stroke="' + SOFT + '" stroke-width="1.2" opacity="0.65"/>';
        }
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="' + LINK +
             '" opacity="0.22" stroke="' + LINK + '" stroke-width="1.6"/>';
        s += arrow(cx, cy, cx + R, cy, INK);
        s += txt(cx + 15, cy - 7, 'a', INK, 11.5);
        s += txt(72, 46, 'вязкость η', SOFT, 10.5, 'start');
        s += arrow(cx + 42, 176, cx + 100, 176, WARN, 'ahw');
        s += txt(cx + 71, 168, 'скорость v', WARN, 11);
        s += arrow(cx - 42, 176, cx - 100, 176, INK);
        s += txt(cx - 71, 168, 'сила трения', INK, 11);
        s += txt(W / 2, H - 8, 'F = 6πηa·v  ⇒  γ = 6πηa', INK, 13);
        return svg(W, H, s);
    };

    // 8. Опыт Перрена: положения одной крупинки через равные промежутки времени.
    F.perrinjump = function () {
        var W = 430, H = 245, gx0 = 90, gy0 = 46, c = 22, i, j;
        var s = txt(W / 2, 24, 'положения крупинки через равные промежутки', INK, 11.5);
        for (i = 0; i <= 10; i++) {
            s += '<line x1="' + (gx0 + i * c) + '" y1="' + gy0 + '" x2="' + (gx0 + i * c) +
                 '" y2="' + (gy0 + 6 * c) + '" stroke="' + BORD + '" stroke-width="0.7"/>';
        }
        for (j = 0; j <= 6; j++) {
            s += '<line x1="' + gx0 + '" y1="' + (gy0 + j * c) + '" x2="' + (gx0 + 10 * c) +
                 '" y2="' + (gy0 + j * c) + '" stroke="' + BORD + '" stroke-width="0.7"/>';
        }
        var p = [[1.2, 3.1], [2.4, 2.2], [2.1, 4.0], [3.6, 3.4], [3.0, 1.8], [4.5, 2.6],
                 [5.2, 4.3], [6.4, 3.2], [5.9, 1.6], [7.2, 2.4], [8.1, 4.1], [8.8, 2.9]];
        var poly = p.map(function (q) {
            return (gx0 + q[0] * c).toFixed(1) + ',' + (gy0 + q[1] * c).toFixed(1);
        });
        s += '<polyline points="' + poly.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="1.8"/>';
        p.forEach(function (q) { s += mol(gx0 + q[0] * c, gy0 + q[1] * c, 3.4, LINK); });
        s += txt(gx0 + 5 * c, gy0 + 6 * c + 22, 'сетка окуляра', SOFT, 10.5);
        s += txt(W / 2, H - 26, 'каждый отрезок — смещение за 30 секунд', SOFT, 10.5);
        s += txt(W / 2, H - 8, 'усредняем квадраты отрезков — получаем ⟨x²⟩', INK, 11);
        return svg(W, H, s);
    };

    // ── Космология: доводка вывода о красном смещении ──

    // Два соседних гребня — метки на одной сопутствующей сетке: Δχ фиксирован, λ = a·Δχ.
    F.twocrests = function () {
        var W = 440, H = 216, x0 = 54;
        var s = txt(W / 2, 22, 'гребень стоит на своём узле сопутствующей сетки', INK, 11.5);
        function row(y, step, color, mark, tag) {
            var t = '', i, x, n, f, xx, pts = [];
            for (i = 0; i <= 6; i++) {
                x = x0 + i * step;
                t += '<line x1="' + x + '" y1="' + (y - 24) + '" x2="' + x + '" y2="' + (y + 14) +
                    '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="2 3"/>';
                t += txt(x, y + 26, String(i), SOFT, 9.5);
            }
            var xa = x0 + 2 * step, xb = x0 + 4 * step;
            for (n = 0; n <= 120; n++) {
                f = n / 120; xx = x0 + f * 6 * step;
                pts.push(xx.toFixed(1) + ',' + (y - 13 * Math.cos(2 * Math.PI * (xx - xa) / (xb - xa))).toFixed(1));
            }
            t += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="2.2"/>';
            t += '<circle cx="' + xa + '" cy="' + (y - 13) + '" r="4" fill="' + color + '"/>';
            t += '<circle cx="' + xb + '" cy="' + (y - 13) + '" r="4" fill="' + color + '"/>';
            t += arrow(xa, y - 22, xb, y - 22, color, mark) + arrow(xb, y - 22, xa, y - 22, color, mark);
            t += txt((xa + xb) / 2, y - 30, tag, color, 10.5);
            return t;
        }
        s += row(84, 33, WARN, 'ahw', 'λ при излучении');
        s += row(170, 52, LINK, 'ahl', 'λ при приёме');
        s += txt(W / 2, H - 8, 'Δχ между гребнями не меняется — растёт только a', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Как читают z: лабораторный узор линий и тот же узор, умноженный целиком на (1+z).
    F.specshift = function () {
        var W = 440, H = 200, xL = 56, xR = 402, yA = 74, yB = 142, hh = 34, zz = 1.07;
        function xof(lam) { return xL + (lam - 380) * (xR - xL) / 380; }
        var s = txt(W / 2, 22, 'узор линий не искажается — он смещается целиком', INK, 11.5);
        s += '<rect x="' + xL + '" y="' + (yA - hh / 2) + '" width="' + (xR - xL) + '" height="' + hh +
            '" fill="' + BORD + '" opacity="0.45"/>';
        s += '<rect x="' + xL + '" y="' + (yB - hh / 2) + '" width="' + (xR - xL) + '" height="' + hh +
            '" fill="' + BORD + '" opacity="0.45"/>';
        [410.2, 434.0, 486.1, 656.3].forEach(function (lam) {
            var x1 = xof(lam).toFixed(1), x2 = xof(lam * zz).toFixed(1);
            s += '<line x1="' + x1 + '" y1="' + (yA - hh / 2) + '" x2="' + x1 + '" y2="' + (yA + hh / 2) +
                '" stroke="' + INK + '" stroke-width="2.2"/>';
            s += '<line x1="' + x2 + '" y1="' + (yB - hh / 2) + '" x2="' + x2 + '" y2="' + (yB + hh / 2) +
                '" stroke="' + WARN + '" stroke-width="2.2"/>';
            s += '<line x1="' + x1 + '" y1="' + (yA + hh / 2) + '" x2="' + x2 + '" y2="' + (yB - hh / 2) +
                '" stroke="' + SOFT + '" stroke-width="0.9" stroke-dasharray="2 3"/>';
        });
        s += txt(xL, yA - hh / 2 - 6, 'лаборатория', SOFT, 10, 'start');
        s += txt(xof(656.3), yA - hh / 2 - 6, 'Hα 656 нм', SOFT, 10);
        s += txt(xL, yB + hh / 2 + 14, 'галактика', WARN, 10, 'start');
        s += txt(xof(656.3 * zz), yB + hh / 2 + 14, 'Hα 702 нм', WARN, 10);
        s += txt(412, 112, '×(1+z)', SOFT, 10.5, 'end');
        s += txt(W / 2, H - 8, 'по каждой линии z выходит одним и тем же', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Докуда линейная формула честна: кривая a(t) и касательная к ней в точке «сегодня».
    F.ztangent = function () {
        var W = 440, H = 216, x0 = 52, xT = 384, base = 158, amp = 92, k = 1.15, uz = -1 / k;
        function xu(u) { return xT + u * (xT - x0); }
        function ya(a) { return base - amp * a; }
        var i, u, pts = [], poly = [];
        for (i = 0; i <= 60; i++) { u = uz * (1 - i / 60); poly.push(xu(u).toFixed(1) + ',' + ya(Math.exp(k * u)).toFixed(1)); }
        poly.push(xu(uz).toFixed(1) + ',' + base);
        var s = '<polygon points="' + poly.join(' ') + '" fill="' + WARN + '" opacity="0.10"/>';
        s += txt(W / 2, 22, 'рядом с сегодня кривая a(t) — почти прямая', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + (W - 24) + '" y2="' + base +
            '" stroke="' + BORD + '" stroke-width="1.4"/>';
        for (i = 0; i <= 100; i++) { u = -1 + i / 100; pts.push(xu(u).toFixed(1) + ',' + ya(Math.exp(k * u)).toFixed(1)); }
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += '<line x1="' + xu(uz).toFixed(1) + '" y1="' + base + '" x2="' + xT + '" y2="' + ya(1) +
            '" stroke="' + SOFT + '" stroke-width="1.6" stroke-dasharray="5 4"/>';
        s += txt(136, 138, 'касательная', SOFT, 10.5, 'end');
        s += txt(56, 100, 'настоящая a(t)', LINK, 10.5, 'start');
        s += '<circle cx="' + xT + '" cy="' + ya(1) + '" r="4.5" fill="' + INK + '"/>';
        s += txt(xT + 8, ya(1) - 8, 'сегодня', INK, 10.5, 'start');
        s += txt(44, ya(1) + 4, 'a', SOFT, 11, 'end');
        [[0.1, 'z = 0,1', 'проценты', MOSS], [0.5, 'z = 0,5', 'около пятнадцати процентов', SOFT],
         [1, 'z = 1', 'вся кривая', WARN]].forEach(function (m) {
            var a = 1 / (1 + m[0]), x = xu(Math.log(a) / k), y = ya(a);
            s += '<line x1="' + x.toFixed(1) + '" y1="' + y.toFixed(1) + '" x2="' + x.toFixed(1) + '" y2="' + base +
                '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="2 3"/>';
            s += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="4" fill="' + m[3] + '"/>';
            s += txt(x, 174, m[1], INK, 10.5);
            s += txt(x, 192, m[2], m[3], 10);
        });
        s += txt(W / 2, H - 8, 'линейная формула честна примерно до z = 0,1', MOSS, 10.5);
        return svg(W, H, s);
    };

    // Преобразование Лежандра: выпуклую кривую можно задать точками, а можно касательными.
    F.legendre = function () {
        var W = 440, H = 212, x0 = 95, y0 = 128, len = 285, hgt = 95, u0 = 0.72;
        var s = txt(W / 2, 22, 'выпуклая кривая: каждому наклону — своя касательная', INK, 11.5);
        s += '<line x1="60" y1="' + y0 + '" x2="412" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="36" x2="' + x0 + '" y2="192" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(406, y0 + 17, 'q&#775;', SOFT, 12);
        s += txt(x0 - 13, 46, 'L', SOFT, 12);
        var d = '', i, u;
        for (i = 0; i <= 40; i++) {
            u = i / 40;
            d += (i ? 'L' : 'M') + (x0 + len * u).toFixed(1) + ',' + (y0 - hgt * u * u).toFixed(1);
        }
        s += '<path d="' + d + '" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        var px = x0 + len * u0, py = y0 - hgt * u0 * u0, k = 2 * hgt * u0 / len;
        var yi = py + k * (px - x0);                       // касательная пересекает ось L
        s += '<line x1="' + x0 + '" y1="' + yi.toFixed(1) + '" x2="386" y2="' +
             (py - k * (386 - px)).toFixed(1) + '" stroke="' + LINK + '" stroke-width="1.8"/>';
        s += '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x0 + '" y2="' + yi.toFixed(1) +
             '" stroke="' + WARN + '" stroke-width="3.5"/>';
        s += txt(x0 - 11, yi + 4, '&#8722;H', WARN, 13, 'end');
        s += '<line x1="' + px.toFixed(1) + '" y1="' + py.toFixed(1) + '" x2="' + px.toFixed(1) +
             '" y2="' + y0 + '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += mol(px, py, 5, LINK);
        s += txt(px, y0 + 17, 'q&#775;(p)', SOFT, 11.5);
        s += txt(352, 47, 'наклон = p', LINK, 11.5, 'start');
        s += txt(W / 2, H - 8, 'H = p&#8201;q&#775; &#8722; L', INK, 12.5);
        return svg(W, H, s);
    };

    // Дифференциал H: слагаемое со скоростью гасится определением импульса.
    F.hcancel = function () {
        var W = 440, H = 180, by = 60, bh = 46;
        var s = txt(W / 2, 24, 'дифференцируем H = p&#8201;q&#775; &#8722; L по всем переменным сразу', INK, 11.5);
        s += txt(38, by + 29, 'dH =', INK, 12.5, 'end');
        function box(x, w, body, color) {
            return '<rect x="' + x + '" y="' + by + '" width="' + w + '" height="' + bh +
                   '" rx="6" fill="' + color + '" opacity="0.10"/>' +
                   '<rect x="' + x + '" y="' + by + '" width="' + w + '" height="' + bh +
                   '" rx="6" fill="none" stroke="' + color + '" stroke-width="1.4"/>' +
                   txt(x + w / 2, by + 29, body, color, 12.5);
        }
        s += box(44, 96, 'q&#775;&#8201;dp', LINK);
        s += box(148, 160, '(p &#8722; &#8706;L/&#8706;q&#775;)&#8201;dq&#775;', WARN);
        s += box(316, 118, '&#8722;(&#8706;L/&#8706;q)&#8201;dq', INK);
        s += '<line x1="158" y1="' + (by + bh / 2) + '" x2="298" y2="' + (by + bh / 2) +
             '" stroke="' + WARN + '" stroke-width="2"/>';
        s += txt(228, by + bh + 22, 'ноль по определению импульса', WARN, 11);
        s += txt(W / 2, 152, 'dH = q&#775;&#8201;dp &#8722; (&#8706;L/&#8706;q)&#8201;dq', INK, 13);
        s += txt(W / 2, H - 8, 'скорость исчезла из ответа — обмен честный', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Сравнение коэффициентов при независимых dq и dp даёт пару уравнений.
    F.coefmatch = function () {
        var W = 440, H = 214, cA = 190, cB = 336;
        var s = txt(W / 2, 24, 'dq и dp независимы — коэффициенты сравниваем порознь', INK, 11.5);
        s += txt(30, 60, 'dH =', INK, 12.5, 'start');
        s += txt(cA, 60, 'q&#775;&#8201;dp', LINK, 13);
        s += txt(cB, 60, '&#8722;&#8201;p&#775;&#8201;dq', WARN, 13);
        s += txt(30, 76, 'из Лежандра и Лагранжа', SOFT, 10, 'start');
        s += txt(30, 122, 'dH =', INK, 12.5, 'start');
        s += txt(cA, 122, '(&#8706;H/&#8706;p)&#8201;dp', LINK, 13);
        s += txt(cB, 122, '(&#8706;H/&#8706;q)&#8201;dq', WARN, 13);
        s += txt(30, 138, 'общий вид дифференциала', SOFT, 10, 'start');
        [cA, cB].forEach(function (c) {
            s += '<line x1="' + c + '" y1="68" x2="' + c + '" y2="106" stroke="' + SOFT +
                 '" stroke-width="1" stroke-dasharray="3,3"/>';
            s += txt(c + 12, 91, '=', SOFT, 12, 'start');
            s += arrow(c, 148, c, 168, MOSS);
        });
        s += txt(cA, 186, 'q&#775; = &#8706;H/&#8706;p', MOSS, 13.5);
        s += txt(cB, 186, 'p&#775; = &#8722;&#8706;H/&#8706;q', MOSS, 13.5);
        s += txt(W / 2, H - 6, 'минус пришёл из первой строки, а не введён рукой', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Теорема Лиувилля: пятно состояний течёт как несжимаемая жидкость.
    // Шаг «Эйлер — Лагранж это Ньютон». Раньше здесь стояла таблица Нётер из соседнего
    // параграфа: схема существовала и рисовалась, но рассказывала про другое (находка сверки).
    F.eulerlagrange = function () {
        var W = 440, H = 224;
        var s = txt(W / 2, 22, 'подставляем L = K(q&#775;) &#8722; U(q)', INK, 11.5);
        s += txt(112, 58, 'd/dt (&#8706;L/&#8706;q&#775;)', LINK, 13);
        s += txt(224, 58, '&#8722;', SOFT, 13);
        s += txt(316, 58, '&#8706;L/&#8706;q', WARN, 13);
        s += txt(400, 58, '= 0', INK, 13);
        s += arrow(112, 70, 112, 106, LINK, 'ahl');
        s += arrow(316, 70, 316, 106, WARN, 'ahw');
        function box(cx, top, bot, color) {
            var x = cx - 84;
            return '<rect x="' + x + '" y="112" width="168" height="58" rx="6" fill="' + color +
                   '" opacity="0.10"/><rect x="' + x + '" y="112" width="168" height="58" rx="6" ' +
                   'fill="none" stroke="' + color + '" stroke-width="1.4"/>' +
                   txt(cx, 138, top, color, 12.5) + txt(cx, 159, bot, SOFT, 10.5);
        }
        s += box(112, 'd/dt (m&#8201;q&#775;) = m&#8201;q&#776;', 'масса на ускорение', LINK);
        s += box(316, '&#8722;&#8706;U/&#8706;q = F', 'сила', WARN);
        s += txt(W / 2, 196, 'm&#8201;q&#776; = F', INK, 14);
        s += txt(W / 2, H - 8, 'Ньютон получился следствием, а не отдельным постулатом', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Шаг «берём уравнение из прошлого параграфа»: две части уравнения отвечают на два
    // разных вопроса — что будет, если сдвинуть координату, и что, если изменить скорость.
    F.elstart = function () {
        var W = 440, H = 212;
        var s = txt(W / 2, 22, 'одно уравнение связывает два разных вопроса', INK, 11.5);
        function panel(x, title, color) {
            return '<rect x="' + x + '" y="38" width="180" height="104" rx="8" fill="none" stroke="' +
                   BORD + '" stroke-width="1.4"/>' + txt(x + 90, 58, title, color, 11);
        }
        s += panel(28, 'сдвинем координату', WARN);
        s += panel(232, 'изменим скорость', LINK);
        s += '<line x1="48" y1="118" x2="188" y2="118" stroke="' + BORD + '" stroke-width="1.2"/>';
        s += mol(88, 110, 8, SOFT);
        s += mol(126, 110, 8, WARN);
        s += arrow(94, 88, 120, 88, WARN, 'ahw');
        s += txt(107, 82, '&#948;q', WARN, 10.5);
        s += txt(118, 136, '&#8706;L/&#8706;q', WARN, 12);
        s += '<line x1="252" y1="118" x2="392" y2="118" stroke="' + BORD + '" stroke-width="1.2"/>';
        s += mol(286, 110, 8, SOFT);
        s += arrow(296, 110, 330, 110, SOFT);
        s += arrow(296, 88, 368, 88, LINK, 'ahl');
        s += txt(332, 82, '&#948;q&#775;', LINK, 10.5);
        s += txt(322, 136, '&#8706;L/&#8706;q&#775;', LINK, 12);
        s += txt(W / 2, 172, 'd/dt (&#8706;L/&#8706;q&#775;) = &#8706;L/&#8706;q', INK, 13.5);
        s += txt(W / 2, H - 8, 'ответ на второй вопрос, взятый по времени, равен первому', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Шаг «производная равна нулю — значит, величина сохраняется»: координата гуляет,
    // а комбинация держится ровной линией.
    F.pconserve = function () {
        var W = 440, H = 218, x0 = 58, x1 = 396, base = 158;
        var s = txt(W / 2, 22, 'координата меняется, а импульс держится', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(x1 + 12, base + 5, 't', SOFT, 12, 'start');
        var i, pts = [];
        for (i = 0; i <= 80; i++) {
            var u = i / 80, x = x0 + (x1 - x0) * u;
            pts.push(x.toFixed(1) + ',' + (base - 28 - 20 * Math.sin(6.6 * u)).toFixed(1));
        }
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + BORD + '" stroke-width="2"/>';
        s += '<line x1="' + x0 + '" y1="72" x2="' + x1 + '" y2="72" stroke="' + LINK + '" stroke-width="2.8"/>';
        s += txt(x0 + 2, 62, '&#8706;L/&#8706;q&#775; — ровная линия', LINK, 11, 'start');
        s += txt(x0 + 2, 178, 'сама координата при этом гуляет', SOFT, 10.5, 'start');
        s += txt(W / 2, 200, 'd/dt (&#8706;L/&#8706;q&#775;) = 0 &#8658; &#8706;L/&#8706;q&#775; = const', INK, 13);
        return svg(W, H, s);
    };

    // Шаг «Гамильтон меняет скорость на импульс»: та же система, вторая переменная другая.
    F.qptrade = function () {
        var W = 440, H = 190;
        var s = txt(W / 2, 22, 'вторую переменную выбираем заново', INK, 11.5);
        function pair(x, a, b, colorB, note) {
            var g = '<rect x="' + x + '" y="46" width="150" height="54" rx="8" fill="none" stroke="' +
                    BORD + '" stroke-width="1.4"/>';
            g += txt(x + 46, 80, a, INK, 15);
            g += txt(x + 75, 80, ',', SOFT, 15);
            g += txt(x + 106, 80, b, colorB, 15);
            g += txt(x + 75, 122, note, SOFT, 10.5);
            return g;
        }
        s += pair(30, 'q', 'q&#775;', SOFT, 'координата и скорость');
        s += pair(260, 'q', 'p', LINK, 'координата и импульс');
        s += arrow(190, 72, 252, 72, LINK, 'ahl');
        s += txt(221, 62, 'p = &#8706;L/&#8706;q&#775;', LINK, 11);
        s += txt(W / 2, 158, 'теперь обе переменные равноправны', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Шаг «два уравнения вместо одного»: минус в правом уравнении и есть причина того,
    // что движение на плоскости получается вращением, а не разбеганием.
    F.heqpair = function () {
        var W = 440, H = 236, cx = 140, cy = 132;
        var s = txt(W / 2, 20, 'два уравнения первого порядка вместо одного второго', INK, 11.5);
        s += '<line x1="' + (cx - 92) + '" y1="' + cy + '" x2="' + (cx + 92) + '" y2="' + cy +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="' + (cy - 76) + '" x2="' + cx + '" y2="' + (cy + 76) +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(cx + 100, cy + 14, 'q', SOFT, 12);
        s += txt(cx + 13, cy - 80, 'p', SOFT, 12);
        var i, a, r = 54;
        for (i = 0; i < 8; i++) {
            a = i * Math.PI / 4;
            var x = cx + r * Math.cos(a), y = cy - r * 0.72 * Math.sin(a);
            s += arrow(x.toFixed(1), y.toFixed(1), (x + 21 * Math.sin(a)).toFixed(1),
                       (y + 15 * Math.cos(a)).toFixed(1), LINK, 'ahl');
        }
        s += txt(330, 96, 'q&#775; = &#8706;H/&#8706;p', INK, 13);
        s += txt(330, 130, 'p&#775; = &#8722;&#8706;H/&#8706;q', WARN, 13);
        s += txt(330, 154, 'вот этот минус', WARN, 10.5);
        s += txt(W / 2, H - 8, 'без минуса точки разбегались бы; с ним они ходят по кругу', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Шаг «состояние — точка на плоскости (q, p)»: для пружины линия постоянной энергии эллипс.
    F.phaseellipse = function () {
        var W = 440, H = 232, cx = 208, cy = 130, rx = 106, ry = 58;
        var s = txt(W / 2, 20, 'состояние груза — одна точка на плоскости (q, p)', INK, 11.5);
        s += '<line x1="' + (cx - rx - 28) + '" y1="' + cy + '" x2="' + (cx + rx + 28) + '" y2="' + cy +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="' + (cy - ry - 24) + '" x2="' + cx + '" y2="' + (cy + ry + 24) +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(cx + rx + 36, cy + 14, 'q', SOFT, 12);
        s += txt(cx + 13, cy - ry - 28, 'p', SOFT, 12);
        s += '<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + rx + '" ry="' + ry + '" fill="' + LINK +
             '" opacity="0.07"/><ellipse cx="' + cx + '" cy="' + cy + '" rx="' + rx + '" ry="' + ry +
             '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        s += '<circle cx="' + cx + '" cy="' + (cy - ry) + '" r="4.5" fill="' + INK + '"/>';
        s += txt(cx, cy - ry - 10, 'q = 0, вся энергия в движении', INK, 10.5);
        s += '<circle cx="' + (cx + rx) + '" cy="' + cy + '" r="4.5" fill="' + INK + '"/>';
        s += txt(cx + rx + 10, cy - 6, 'p = 0', INK, 10.5, 'start');
        s += txt(cx + rx + 10, cy + 10, 'энергия в пружине', SOFT, 10, 'start');
        s += arrow(cx - rx + 6, cy + 30, cx - rx + 2, cy - 6, LINK, 'ahl');
        s += txt(W / 2, cy + ry + 34, 'p&#178;/2m + k&#8201;q&#178;/2 = E', INK, 12.5);
        s += txt(W / 2, H - 8, 'полный обход эллипса — один период колебания', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Шаг «точка не сходит со своей кривой»: разным запасам энергии — разные кривые,
    // и перепрыгнуть с одной на другую движение не может.
    F.stayoncurve = function () {
        var W = 440, H = 224, cx = 214, cy = 122;
        var s = txt(W / 2, 20, 'каждому запасу энергии — своя замкнутая кривая', INK, 11.5);
        s += '<line x1="' + (cx - 132) + '" y1="' + cy + '" x2="' + (cx + 132) + '" y2="' + cy +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="' + (cy - 74) + '" x2="' + cx + '" y2="' + (cy + 74) +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(cx + 140, cy + 14, 'q', SOFT, 12);
        s += txt(cx + 13, cy - 78, 'p', SOFT, 12);
        [[54, 30], [122, 66]].forEach(function (e) {
            s += '<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + e[0] + '" ry="' + e[1] +
                 '" fill="none" stroke="' + BORD + '" stroke-width="1.5" stroke-dasharray="5,4"/>';
        });
        s += '<ellipse cx="' + cx + '" cy="' + cy + '" rx="88" ry="48" fill="none" stroke="' + LINK +
             '" stroke-width="2.4"/>';
        var px = cx + 88 * Math.cos(-0.9), py = cy - 48 * Math.sin(-0.9);
        s += '<circle cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) + '" r="5" fill="' + INK + '"/>';
        s += arrow(px.toFixed(1), py.toFixed(1), (px + 34).toFixed(1), (py + 20).toFixed(1), WARN, 'ahw');
        var mx = px + 24, my = py + 14;
        s += '<line x1="' + (mx - 7) + '" y1="' + (my - 7) + '" x2="' + (mx + 7) + '" y2="' + (my + 7) +
             '" stroke="' + WARN + '" stroke-width="2.4"/>';
        s += '<line x1="' + (mx + 7) + '" y1="' + (my - 7) + '" x2="' + (mx - 7) + '" y2="' + (my + 7) +
             '" stroke="' + WARN + '" stroke-width="2.4"/>';
        s += txt(cx - 96, cy + 84, 'меньше энергии', SOFT, 10.5);
        s += txt(cx + 96, cy + 84, 'больше энергии', SOFT, 10.5);
        s += txt(W / 2, 198, 'dH/dt = 0', INK, 13);
        s += txt(W / 2, H - 8, 'сойти на соседнюю кривую точка не может', SOFT, 10.5);
        return svg(W, H, s);
    };

    F.phaseblob = function () {
        var W = 440, H = 226, cx = 210, cy = 118, rx = 118, ry = 62;
        var s = txt(W / 2, 20, 'облако состояний течёт как несжимаемая жидкость', INK, 11.5);
        s += '<line x1="76" y1="' + cy + '" x2="358" y2="' + cy + '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="46" x2="' + cx + '" y2="194" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(366, cy + 15, 'q', SOFT, 12);
        s += txt(cx + 13, 54, 'p', SOFT, 12);
        s += '<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + rx + '" ry="' + ry +
             '" fill="none" stroke="' + BORD + '" stroke-width="1.5" stroke-dasharray="5,4"/>';
        function blob(pts) {
            var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0] + ',' + p[1]; }).join('') + 'Z';
            return '<path d="' + d + '" fill="' + LINK + '" opacity="0.28"/>' +
                   '<path d="' + d + '" fill="none" stroke="' + LINK + '" stroke-width="1.6"/>';
        }
        s += blob([[314, 104], [342, 104], [342, 132], [314, 132]]);
        s += blob([[186, 48], [230, 40], [238, 56], [194, 64]]);
        s += blob([[78, 90], [90, 86], [108, 144], [96, 148]]);
        s += txt(328, 152, 't = 0', LINK, 11);
        s += txt(264, 44, 'позже', SOFT, 11, 'start');
        s += txt(92, 168, 'ещё позже', SOFT, 11);
        s += arrow(232, 180, 188, 180, SOFT);
        s += txt(W / 2, 208, '&#8706;q&#775;/&#8706;q + &#8706;p&#775;/&#8706;p = 0', INK, 12.5);
        s += txt(W / 2, H - 6, 'площадь пятна одна и та же', SOFT, 10.5);
        return svg(W, H, s);
    };


    // ── Перенос: диффузия ────────────────────────────────────────────────────

    // 1. Мысленная плоскость в неоднородном газе: встречные потоки не равны.
    F.diffplane = function () {
        var W = 440, H = 200, xp = 222;
        var s = txt(W / 2, 20, 'мысленная плоскость в неоднородном газе', INK, 11.5);
        s += '<rect x="30" y="34" width="380" height="116" fill="' + LINK + '" opacity="0.05"/>';
        [[48, 50], [74, 88], [56, 126], [92, 58], [100, 110], [118, 140], [132, 72],
         [146, 104], [160, 136], [174, 52], [186, 92], [198, 124], [84, 142], [206, 64]]
            .forEach(function (p) { s += mol(p[0], p[1], 5); });
        [[248, 58], [280, 112], [316, 142], [342, 66], [378, 104], [400, 140]]
            .forEach(function (p) { s += mol(p[0], p[1], 5, SOFT); });
        s += '<line x1="' + xp + '" y1="30" x2="' + xp + '" y2="158" stroke="' + INK +
            '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += arrow(140, 70, 304, 70, LINK, 'ahl');
        s += txt(222, 62, 'больше пересечений', LINK, 10.5);
        s += arrow(304, 124, 140, 124, WARN, 'ahw');
        s += txt(222, 140, 'меньше пересечений', WARN, 10.5);
        s += txt(120, 176, 'гуще', SOFT, 10.5);
        s += txt(330, 176, 'реже', SOFT, 10.5);
        s += txt(xp, 176, 'x', SOFT, 11);
        s += txt(W / 2, H - 8, 'слева молекул больше — значит, и пересечений слева направо больше', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 2. Шесть направлений: к плоскости летит примерно шестая часть молекул.
    F.diffsix = function () {
        var W = 440, H = 200, cx = 140, cy = 104;
        var s = txt(W / 2, 20, 'грубая модель: шесть направлений, по одной шестой на каждое', INK, 11.5);
        s += arrow(cx, cy, cx - 64, cy, SOFT);
        s += arrow(cx, cy, cx, cy - 58, SOFT);
        s += arrow(cx, cy, cx, cy + 58, SOFT);
        s += arrow(cx, cy, cx + 44, cy - 42, SOFT);
        s += arrow(cx, cy, cx - 44, cy + 42, SOFT);
        s += arrow(cx, cy, cx + 64, cy, LINK, 'ahl');
        s += txt(cx + 34, cy - 12, '⅙', LINK, 14);
        s += mol(cx, cy, 6);
        s += '<line x1="250" y1="52" x2="250" y2="172" stroke="' + INK +
            '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += txt(250, 44, 'плоскость', SOFT, 10);
        s += txt(352, 98, 'j₊ = ⅙ n v̄', INK, 15);
        s += txt(352, 120, 'на единицу площади за секунду', SOFT, 9.5);
        s += txt(W / 2, H - 8, 'точный расчёт даёт ¼ вместо ⅙ — на оценку порядка это не влияет', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 3. Молекула приходит от места последнего столкновения — за λ от плоскости.
    F.difflast = function () {
        var W = 440, H = 200, xp = 300;
        var s = txt(W / 2, 20, 'молекула приносит концентрацию с расстояния λ', INK, 11.5);
        s += '<line x1="' + xp + '" y1="44" x2="' + xp + '" y2="160" stroke="' + INK +
            '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += txt(xp + 12, 56, 'плоскость', SOFT, 10, 'start');
        s += '<polyline points="36,150 66,104 96,146 128,92 156,134 188,86 222,128" ' +
            'fill="none" stroke="' + SOFT + '" stroke-width="1.6"/>';
        [[66, 104], [96, 146], [128, 92], [156, 134], [188, 86]].forEach(function (p) {
            s += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="3" fill="' + SOFT + '"/>';
        });
        s += arrow(222, 128, xp - 4, 112, LINK, 'ahl');
        s += '<circle cx="222" cy="128" r="4.5" fill="' + LINK + '"/>';
        s += txt(214, 150, 'последнее столкновение', SOFT, 10, 'end');
        s += '<line x1="222" y1="172" x2="300" y2="172" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += '<line x1="222" y1="167" x2="222" y2="177" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += '<line x1="300" y1="167" x2="300" y2="177" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += txt(261, 165, 'λ', LINK, 12);
        s += txt(316, 112, 'приносит n(x−λ)', LINK, 10.5, 'start');
        s += txt(W / 2, H - 8, 'между столкновениями молекула летит по прямой и ничего не забывает', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 4. Линеаризация: на длине λ кривая неотличима от своей касательной.
    F.difflinear = function () {
        var W = 440, H = 212, base = 170;
        var s = txt(W / 2, 20, 'на длине λ концентрация меняется почти линейно', INK, 11.5);
        s += '<line x1="50" y1="' + base + '" x2="410" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="50" y1="40" x2="50" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(42, 48, 'n', INK, 12, 'end');
        s += '<polyline points="60,58 100,64 140,76 180,96 220,120 260,140 300,152 340,158 400,163" ' +
            'fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += '<line x1="168" y1="91" x2="286" y2="156" stroke="' + WARN +
            '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += txt(300, 108, 'касательная', WARN, 10, 'start');
        [[180, 96], [220, 120], [260, 140]].forEach(function (p) {
            s += '<line x1="' + p[0] + '" y1="' + p[1] + '" x2="' + p[0] + '" y2="' + base +
                '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        });
        s += mol(180, 96, 4.5) + mol(220, 120, 4.5, INK) + mol(260, 140, 4.5, WARN);
        s += txt(180, base + 16, 'x − λ', SOFT, 10);
        s += txt(220, base + 16, 'x', SOFT, 10);
        s += txt(260, base + 16, 'x + λ', SOFT, 10);
        s += txt(W / 2, H - 8, 'n(x ± λ) ≈ n(x) ± λ · dn/dx', INK, 12.5);
        return svg(W, H, s);
    };

    // 5. Итог вывода: поток пропорционален градиенту и направлен против него.
    F.fickflux = function () {
        var W = 440, H = 200;
        var s = txt(W / 2, 20, 'поток идёт против градиента', INK, 11.5);
        for (var i = 0; i < 8; i++) {
            s += '<rect x="' + (40 + 45 * i) + '" y="42" width="45" height="58" fill="' + LINK +
                '" opacity="' + (0.5 - 0.06 * i).toFixed(2) + '"/>';
        }
        s += '<rect x="40" y="42" width="360" height="58" fill="none" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(40, 116, 'гуще', SOFT, 10.5, 'start');
        s += txt(400, 116, 'реже', SOFT, 10.5, 'end');
        s += arrow(160, 130, 306, 130, WARN, 'ahw');
        s += txt(232, 122, 'поток j', WARN, 11);
        s += arrow(306, 152, 160, 152, SOFT);
        s += txt(232, 168, 'рост концентрации', SOFT, 10.5);
        s += txt(W / 2, H - 8, 'поток и градиент смотрят в разные стороны — отсюда минус', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 6. Сохранение вещества в тонком слое: закон Фика становится уравнением диффузии.
    F.diffbox = function () {
        var W = 440, H = 200;
        var s = txt(W / 2, 20, 'что втекло минус что вытекло — то накопилось', INK, 11.5);
        s += '<rect x="150" y="60" width="150" height="80" fill="' + LINK +
            '" opacity="0.10" stroke="' + INK + '" stroke-width="1.6"/>';
        s += arrow(66, 100, 146, 100, LINK, 'ahl');
        s += txt(106, 90, 'j(x)', LINK, 11);
        s += arrow(304, 100, 374, 100, WARN, 'ahw');
        s += txt(340, 90, 'j(x+&#916;x)', WARN, 11);
        s += txt(225, 96, '&#8706;n/&#8706;t · &#916;x', INK, 13);
        s += txt(225, 118, 'накопление', SOFT, 10.5);
        s += '<line x1="150" y1="156" x2="300" y2="156" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += '<line x1="150" y1="151" x2="150" y2="161" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += '<line x1="300" y1="151" x2="300" y2="161" stroke="' + SOFT + '" stroke-width="1.2"/>';
        s += txt(225, 172, '&#916;x', SOFT, 10.5);
        s += txt(W / 2, H - 8, '&#8706;n/&#8706;t = &#8722;&#8706;j/&#8706;x = D · &#8706;²n/&#8706;x²', INK, 12.5);
        return svg(W, H, s);
    };

    // 7. Ширина пятна растёт как корень из времени, а не пропорционально ему.
    F.diffsqrt = function () {
        var W = 450, H = 212, base = 160;
        var s = txt(W / 2, 20, 'ширина пятна растёт как корень из времени', INK, 11.5);
        s += '<line x1="60" y1="' + base + '" x2="420" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="60" y1="44" x2="60" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<polyline points="60,160 74,138 92,127 116,116 148,105 186,94 232,83 284,72 344,61 410,50" ' +
            'fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += '<line x1="60" y1="105" x2="148" y2="105" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="148" y1="105" x2="148" y2="' + base + '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="60" y1="50" x2="410" y2="50" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="410" y1="50" x2="410" y2="' + base + '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += mol(148, 105, 4.5) + mol(410, 50, 4.5, WARN);
        s += txt(52, 109, 'w', SOFT, 11, 'end');
        s += txt(52, 54, '2w', SOFT, 11, 'end');
        s += txt(148, base + 16, 't', SOFT, 11);
        s += txt(410, base + 16, '4t', SOFT, 11);
        s += txt(96, 40, 'ширина', SOFT, 10);
        s += txt(300, base + 16, 'время', SOFT, 10.5);
        s += txt(300, 130, 'x ≈ √(2Dt)', INK, 14);
        s += txt(W / 2, H - 8, 'вчетверо дольше — всего вдвое шире', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 8. От чего зависит D: через λ и v̄ он зависит от температуры и давления.
    F.difftp = function () {
        var W = 440, H = 195;
        var s = txt(W / 2, 20, 'от чего зависит коэффициент диффузии', INK, 11.5);
        s += '<rect x="32" y="46" width="144" height="46" fill="none" stroke="' + BORD + '" stroke-width="1.4"/>';
        s += txt(104, 64, 'длина пробега', SOFT, 10.5);
        s += txt(104, 84, 'λ ∝ T / p', INK, 13);
        s += '<rect x="32" y="110" width="144" height="46" fill="none" stroke="' + BORD + '" stroke-width="1.4"/>';
        s += txt(104, 128, 'тепловая скорость', SOFT, 10.5);
        s += txt(104, 148, 'v̄ ∝ √T', INK, 13);
        s += arrow(180, 70, 244, 92, SOFT);
        s += arrow(180, 132, 244, 112, SOFT);
        s += '<rect x="250" y="74" width="162" height="56" fill="' + LINK +
            '" opacity="0.10" stroke="' + INK + '" stroke-width="1.6"/>';
        s += txt(331, 96, 'D = ⅓ λ v̄', INK, 13);
        s += txt(331, 118, 'D ∝ T·√T / p', INK, 13);
        s += txt(W / 2, H - 8, 'нагрели вдвое — D вырос почти втрое; сжали вдвое — D упал вдвое', SOFT, 10.5);
        return svg(W, H, s);
    };

    // ---- Теплопроводность (transport/02) ----

    // Два равных встречных потока молекул через плоскость: число сходится, энергия — нет.
    F.condplane = function () {
        var W = 430, H = 200, px = 215;
        var s = txt(W / 2, 20, 'счёт пересечений одинаков в обе стороны', SOFT, 11);
        s += '<rect x="24" y="34" width="' + (px - 24) + '" height="126" fill="' + WARN + '" opacity="0.10"/>';
        s += '<rect x="' + px + '" y="34" width="' + (386 - px) + '" height="126" fill="' + LINK + '" opacity="0.10"/>';
        s += '<line x1="' + px + '" y1="30" x2="' + px + '" y2="164" stroke="' + INK +
             '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += txt(112, 50, 'горячее', WARN, 11.5);
        s += txt(318, 50, 'холоднее', LINK, 11.5);
        [80, 124].forEach(function (y) {
            s += mol(140, y, 7, WARN);
            s += arrow(152, y, px - 6, y, WARN, 'ahw');
        });
        [102, 146].forEach(function (y) {
            s += mol(292, y, 5, LINK);
            s += arrow(282, y, px + 6, y, LINK, 'ahl');
        });
        s += txt(122, 84, 'энергии больше', WARN, 10.5, 'end');
        s += txt(308, 150, 'энергии меньше', LINK, 10.5, 'start');
        s += txt(px, 182, '&#934; = &#188; n v', INK, 13);
        s += txt(W / 2, H - 6, 'переносится разность энергий, а не число частиц', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Молекула несёт память о последнем столкновении — на λ в стороне от плоскости.
    F.condlast = function () {
        var W = 430, H = 190, px = 300, cx = 232;
        var s = txt(W / 2, 20, 'молекула помнит последнее столкновение', SOFT, 11);
        s += '<line x1="' + px + '" y1="34" x2="' + px + '" y2="132" stroke="' + INK +
             '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += '<path d="M96,62 L134,100 L172,56 L' + cx + ',104 L' + px + ',74" fill="none" stroke="' +
             LINK + '" stroke-width="1.8"/>';
        [[96, 62], [134, 100], [172, 56]].forEach(function (p) { s += mol(p[0], p[1], 4, SOFT); });
        s += mol(cx, 104, 6, WARN);
        s += mol(px, 74, 5, LINK);
        s += '<line x1="' + cx + '" y1="110" x2="' + cx + '" y2="150" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="' + px + '" y1="132" x2="' + px + '" y2="150" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += arrow(cx, 150, px - 2, 150, INK);
        s += arrow(px, 150, cx + 2, 150, INK);
        s += txt((cx + px) / 2, 143, '&#955;', INK, 13);
        s += txt(cx, 92, 'последнее столкновение', WARN, 10.5);
        s += txt(W / 2, H - 8, 'приносит энергию точки x &#8722; &#955;', SOFT, 11);
        return svg(W, H, s);
    };

    // На отрезке 2λ профиль температуры неотличим от касательной.
    F.condtaylor = function () {
        var W = 430, H = 200, xm = 220;
        var s = txt(W / 2, 20, 'на отрезке в две длины пробега кривая неотличима от прямой', SOFT, 10.5);
        s += '<path d="M60,62 Q220,92 380,154" fill="none" stroke="' + INK + '" stroke-width="2"/>';
        s += '<line x1="140" y1="77" x2="300" y2="123" stroke="' + LINK +
             '" stroke-width="1.8" stroke-dasharray="5,4"/>';
        s += txt(392, 152, 'T(x)', INK, 12, 'start');
        s += txt(122, 74, 'касательная', LINK, 10.5, 'end');
        [[180, 89], [260, 112]].forEach(function (p) {
            s += mol(p[0], p[1], 4, WARN);
            s += '<line x1="' + p[0] + '" y1="' + p[1] + '" x2="' + p[0] + '" y2="168" stroke="' +
                 BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
        });
        s += mol(xm, 100, 5, INK);
        s += arrow(180, 168, 258, 168, INK);
        s += arrow(260, 168, 182, 168, INK);
        s += txt(xm, 161, '2&#955;', INK, 12.5);
        s += txt(W / 2, H - 8, 'профиль температуры', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Теплоёмкость одной молекулы: степени свободы у одноатомного и двухатомного газа.
    F.condenergy = function () {
        var W = 430, H = 180;
        var s = txt(112, 24, 'одноатомный: три степени свободы', SOFT, 10.5);
        s += txt(318, 24, 'двухатомный: пять', SOFT, 10.5);
        s += mol(112, 88, 12, LINK);
        [[0, -34], [30, 18], [-30, 18]].forEach(function (d) {
            s += arrow(112, 88, 112 + d[0], 88 + d[1], LINK, 'ahl');
        });
        s += mol(300, 88, 11, WARN);
        s += mol(340, 88, 11, WARN);
        s += '<line x1="300" y1="88" x2="340" y2="88" stroke="' + WARN + '" stroke-width="3"/>';
        [[0, -32], [26, 16], [-26, 16]].forEach(function (d) {
            s += arrow(320, 88, 320 + d[0], 88 + d[1], WARN, 'ahw');
        });
        s += '<path d="M292,66 A28,28 0 0 1 348,66" fill="none" stroke="' + WARN +
             '" stroke-width="1.4" stroke-dasharray="3,3" marker-end="url(#ahw)"/>';
        s += '<path d="M292,110 A28,28 0 0 0 348,110" fill="none" stroke="' + WARN +
             '" stroke-width="1.4" stroke-dasharray="3,3" marker-end="url(#ahw)"/>';
        s += txt(W / 2, 148, 'c = (i / 2) k&#8342;', INK, 14);
        s += txt(W / 2, H - 8, 'теплоёмкость одной молекулы', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Поток тепла идёт против градиента температуры.
    F.condflux = function () {
        var W = 430, H = 200;
        var s = txt(W / 2, 20, 'поток идёт против градиента', SOFT, 11);
        s += '<line x1="46" y1="166" x2="392" y2="166" stroke="' + BORD + '" stroke-width="1.4"/>';
        s += '<line x1="60" y1="52" x2="372" y2="140" stroke="' + INK + '" stroke-width="2"/>';
        s += txt(384, 48, 'T', INK, 13, 'start');
        s += arrow(252, 88, 176, 88, WARN, 'ahw');
        s += txt(214, 78, 'рост температуры', WARN, 10.5);
        s += arrow(176, 124, 292, 124, LINK, 'ahl');
        s += txt(234, 116, 'поток тепла', LINK, 10.5);
        s += txt(W / 2, 188, 'q = &#8722;&#954; dT/dx', INK, 14);
        return svg(W, H, s);
    };

    // κ газа не зависит от давления: n падает, λ растёт, произведение постоянно.
    F.condkappa = function () {
        var W = 430, H = 200;
        function box(x, label, pts, path) {
            var t = '<rect x="' + x + '" y="46" width="160" height="96" fill="none" stroke="' + BORD + '" stroke-width="1.4"/>';
            pts.forEach(function (p) { t += mol(x + p[0], 46 + p[1], 4, SOFT); });
            t += '<path d="' + path + '" fill="none" stroke="' + LINK + '" stroke-width="1.8"/>';
            t += txt(x + 80, 36, label, SOFT, 10.5);
            return t;
        }
        var dense = [[18, 22], [46, 68], [74, 30], [102, 76], [130, 40], [34, 50], [88, 14],
                     [118, 62], [62, 88], [146, 84]];
        var rare = [[24, 30], [70, 74], [116, 26], [142, 70], [50, 56]];
        var s = box(28, 'плотный газ', dense, 'M32,110 L58,84 L84,104 L110,80 L136,102');
        s += box(242, 'разрежённый вдвое', rare, 'M246,116 L306,76 L366,112');
        s += txt(108, 156, 'пробег короче', LINK, 10.5);
        s += txt(322, 156, 'пробег вдвое длиннее', LINK, 10.5);
        s += txt(W / 2, 182, 'n &#183; &#955; = const', INK, 14);
        s += txt(W / 2, H - 6, 'произведение n&#183;&#955; не зависит от давления', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Стационарный профиль в двухслойной стенке: ломаная из прямых, поток один и тот же.
    F.condwall = function () {
        var W = 430, H = 220, x0 = 70, x1 = 190, x2 = 330;
        var s = txt(W / 2, 20, 'температура падает по прямой в каждом слое', SOFT, 10.5);
        s += '<rect x="' + x0 + '" y="34" width="' + (x1 - x0) + '" height="122" fill="' + WARN + '" opacity="0.12" stroke="' + BORD + '"/>';
        s += '<rect x="' + x1 + '" y="34" width="' + (x2 - x1) + '" height="122" fill="' + LINK + '" opacity="0.12" stroke="' + BORD + '"/>';
        s += txt((x0 + x1) / 2, 174, 'кирпич', SOFT, 10.5);
        s += txt((x1 + x2) / 2, 174, 'утеплитель', SOFT, 10.5);
        s += '<path d="M' + x0 + ',52 L' + x1 + ',72 L' + x2 + ',140" fill="none" stroke="' + INK + '" stroke-width="2.2"/>';
        s += mol(x0, 52, 4, INK); s += mol(x1, 72, 4, INK); s += mol(x2, 140, 4, INK);
        s += txt(x0 - 10, 50, 'T&#8321;', INK, 12, 'end');
        s += txt(x2 + 10, 144, 'T&#8322;', INK, 12, 'start');
        [86, 168, 250].forEach(function (x) { s += arrow(x, 148, x + 60, 148, SOFT); });
        s += txt(W / 2, 198, 'R = L / &#954;, сопротивления складываются', INK, 12.5);
        s += txt(W / 2, H - 6, 'поток одинаков во всех сечениях', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Кто носит энергию: колебания решётки в диэлектрике и электроны в металле.
    F.condmetal = function () {
        var W = 430, H = 200;
        var s = txt(110, 24, 'диэлектрик: колебания решётки', SOFT, 10.5);
        s += txt(320, 24, 'металл: электроны проводимости', SOFT, 10.5);
        var i, j;
        for (i = 0; i < 4; i++) for (j = 0; j < 3; j++) {
            s += mol(46 + i * 42, 62 + j * 34, 5, BORD);
            s += mol(240 + i * 42, 62 + j * 34, 5, BORD);
        }
        s += '<path d="M40,96 Q66,64 92,96 Q118,128 144,96 Q170,64 196,96" fill="none" stroke="' +
             WARN + '" stroke-width="2"/>';
        [79, 113].forEach(function (y) {
            s += arrow(234, y, 396, y, LINK, 'ahl');
        });
        [[256, 79], [312, 79], [280, 113], [344, 113]].forEach(function (p) {
            s += mol(p[0], p[1], 3.5, LINK);
        });
        s += txt(118, 156, 'медленно', WARN, 10.5);
        s += txt(320, 156, 'быстро', LINK, 10.5);
        s += txt(W / 2, 182, '&#954; / (&#963;T) = 2,44&#183;10&#8315;&#8312; Вт&#183;Ом/К&#178;', INK, 13);
        s += txt(W / 2, H - 4, 'одни и те же частицы несут заряд и тепло', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Барометрия, шаг 1. Тонкий слой воздуха покоится: три силы в сумме дают ноль.
    F.barolayer = function () {
        var W = 440, H = 236;
        var s = txt(W / 2, 18, 'слой воздуха толщиной Δh покоится', INK, 11.5);
        s += '<rect x="30" y="34" width="90" height="170" fill="' + LINK + '" opacity="0.08" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<rect x="30" y="104" width="90" height="22" fill="' + LINK + '" opacity="0.30" stroke="' + LINK + '" stroke-width="1.4"/>';
        s += '<line x1="120" y1="104" x2="250" y2="96" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += '<line x1="120" y1="126" x2="250" y2="132" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="3,3"/>';
        s += txt(75, 220, 'столб воздуха', SOFT, 10.5);
        s += '<rect x="250" y="96" width="140" height="36" fill="' + LINK + '" opacity="0.18" stroke="' + LINK + '" stroke-width="1.6"/>';
        s += txt(320, 119, 'A · Δh', INK, 12);
        s += arrow(285, 176, 285, 136, LINK, 'ahl');
        s += txt(285, 192, 'p(h) · A', LINK, 11);
        s += arrow(285, 52, 285, 92, INK);
        s += txt(285, 44, 'p(h + Δh) · A', INK, 11);
        s += arrow(362, 136, 362, 176, WARN, 'ahw');
        s += txt(362, 192, 'ρ · A · Δh · g', WARN, 11);
        s += txt(W / 2, 226, 'сумма трёх сил равна нулю', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Барометрия, шаг 2. Толщина слоя из ответа выпадает — переход к пределу законен.
    F.baroslope = function () {
        var W = 430, H = 206;
        var s = txt(W / 2, 20, 'отношение не зависит от толщины слоя', INK, 11.5);
        [[46, 62, 'толстый слой'], [176, 30, 'тоньше'], [306, 11, 'в пределе']].forEach(function (b) {
            var x = b[0], hgt = b[1], base = 150;
            s += '<rect x="' + x + '" y="' + (base - hgt) + '" width="90" height="' + hgt +
                 '" fill="' + LINK + '" opacity="0.20" stroke="' + LINK + '" stroke-width="1.4"/>';
            s += txt(x + 45, base - hgt - 8, 'Δh', LINK, 11);
            s += txt(x + 45, 170, b[2], SOFT, 10.5);
            s += '<line x1="' + (x + 96) + '" y1="' + (base - hgt) + '" x2="' + (x + 96) + '" y2="' + base +
                 '" stroke="' + SOFT + '" stroke-width="1"/>';
            s += txt(x + 104, base - hgt / 2 + 4, 'Δp', SOFT, 10.5, 'start');
        });
        s += txt(W / 2, 194, 'Δp / Δh = −ρg   ⟶   dp/dh = −ρg', INK, 13);
        return svg(W, H, s);
    };

    // Барометрия, шаг 3. При одной температуре плотность идёт следом за давлением.
    F.barodensity = function () {
        var W = 430, H = 198, seed = 11;
        function rnd() { seed = (seed * 1103515 + 12345) % 2147483; return seed / 2147483; }
        var s = txt(W / 2, 18, 'одна температура: плотность идёт следом за давлением', INK, 11.5);
        s += txt(W / 2, 36, 'T одинакова', SOFT, 10.5);
        [[60, 30, INK, 'давление высокое'], [250, 9, SOFT, 'давление низкое']].forEach(function (b) {
            var x = b[0], n = b[1], i;
            s += '<rect x="' + x + '" y="46" width="130" height="106" fill="' + LINK +
                 '" opacity="0.08" stroke="' + BORD + '" stroke-width="1"/>';
            for (i = 0; i < n; i++) {
                s += mol(Math.round(x + 8 + rnd() * 114), Math.round(54 + rnd() * 90), 3.6, b[2]);
            }
            s += txt(x + 65, 170, b[3], b[2], 11);
        });
        s += txt(W / 2, 190, 'ρ = m · p / (kT)', INK, 12.5);
        return svg(W, H, s);
    };

    // Барометрия, шаг 4. Наклон в каждой точке пропорционален самому значению.
    F.baroode = function () {
        var W = 430, H = 202, x0 = 62, x1 = 396, base = 158, top = 42, L = x1 - x0, amp = base - top;
        var s = txt(W / 2, 20, 'наклон пропорционален самому значению', INK, 11.5), pts = [], x, u;
        for (x = x0; x <= x1; x += 3) {
            u = (x - x0) / L;
            pts.push(x + ',' + (base - amp * Math.exp(-2.2 * u)));
        }
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + (top - 6) + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.6"/>';
        [0.06, 0.38, 0.78].forEach(function (u2) {
            var xt = x0 + u2 * L, yt = base - amp * Math.exp(-2.2 * u2),
                k = amp * 2.2 / L * Math.exp(-2.2 * u2), d = 30;
            s += '<line x1="' + (xt - d) + '" y1="' + (yt - k * d) + '" x2="' + (xt + d) + '" y2="' + (yt + k * d) +
                 '" stroke="' + WARN + '" stroke-width="1.8"/>';
            s += '<circle cx="' + xt + '" cy="' + yt + '" r="3.4" fill="' + WARN + '"/>';
        });
        s += txt(x0 - 8, top + 4, 'p', INK, 12, 'end');
        s += txt(x1, base + 18, 'высота ⟶', SOFT, 10, 'end');
        s += txt(W / 2, 194, 'dp/dh = −(mg/kT) · p', INK, 12.5);
        return svg(W, H, s);
    };

    // Барометрия, шаг 5. Разделение переменных: давление налево, высота направо.
    F.barointeg = function () {
        var W = 430, H = 118;
        var s = txt(118, 48, 'dp / p', LINK, 17);
        s += txt(214, 48, '=', INK, 16);
        s += txt(318, 48, '−(mg/kT) · dh', WARN, 17);
        s += '<line x1="72" y1="64" x2="164" y2="64" stroke="' + LINK + '" stroke-width="1.5"/>';
        s += '<line x1="240" y1="64" x2="396" y2="64" stroke="' + WARN + '" stroke-width="1.5"/>';
        s += txt(118, 82, 'только давление', SOFT, 11);
        s += txt(318, 82, 'только высота', SOFT, 11);
        s += txt(214, 104, '∫ каждую часть отдельно', INK, 12);
        return svg(W, H, s);
    };

    // Барометрия, шаг 6. Экспонента: каждая шкала высот отнимает одну и ту же долю.
    F.baroexp = function () {
        var W = 440, H = 214, x0 = 64, x1 = 400, base = 162, top = 42, L = x1 - x0, amp = base - top;
        var s = txt(W / 2, 20, 'каждая шкала высот отнимает одну и ту же долю', INK, 11.5), pts = [], x, u;
        for (x = x0; x <= x1; x += 3) {
            u = (x - x0) / L;
            pts.push(x + ',' + (base - amp * Math.exp(-4 * u)));
        }
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + (top - 6) + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + LINK + '" stroke-width="2.6"/>';
        s += txt(x0 - 8, top + 4, '100 %', INK, 10.5, 'end');
        [[1, '37 %', 'H'], [2, '14 %', '2H'], [3, '5 %', '3H']].forEach(function (b) {
            var xm = x0 + L * b[0] / 4, ym = base - amp * Math.exp(-b[0]);
            s += '<line x1="' + xm + '" y1="' + base + '" x2="' + xm + '" y2="' + ym +
                 '" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="4,4"/>';
            s += '<circle cx="' + xm + '" cy="' + ym + '" r="3.4" fill="' + WARN + '"/>';
            s += txt(xm, ym - 10, b[1], WARN, 10.5);
            s += txt(xm, base + 17, b[2], INK, 11);
        });
        s += txt(x1, base + 34, 'высота, в шкалах H', SOFT, 10, 'end');
        s += txt(W / 2, 204, 'p = p₀ · exp(−h / H)', INK, 12.5);
        return svg(W, H, s);
    };

    // Барометрия, шаг 7. У каждого газа своя шкала высот: она обратна массе молекулы.
    F.baroscale = function () {
        var W = 440, H = 218, x0 = 60, x1 = 296, base = 170, top = 44, L = x1 - x0, amp = base - top;
        var s = txt(W / 2, 20, 'у каждого газа своя шкала высот', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x1 + '" y2="' + base + '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + (top - 6) + '" stroke="' + BORD + '" stroke-width="1"/>';
        [[120, LINK, 'водород: 120 км', 60], [8.7, INK, 'азот: 8,7 км', 82], [5.5, WARN, 'углекислый газ: 5,5 км', 104]]
            .forEach(function (b) {
                var pts = [], x, km;
                for (x = x0; x <= x1; x += 3) {
                    km = (x - x0) / L * 40;
                    pts.push(x + ',' + (base - amp * Math.exp(-km / b[0])));
                }
                s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + b[1] + '" stroke-width="2.4"/>';
                s += '<line x1="316" y1="' + (b[3] - 4) + '" x2="342" y2="' + (b[3] - 4) + '" stroke="' + b[1] + '" stroke-width="2.4"/>';
                s += txt(348, b[3], b[2], b[1], 10.5, 'start');
            });
        s += txt(x0 - 8, top + 4, 'p', INK, 12, 'end');
        s += txt(x1, base + 18, 'высота, км', SOFT, 10, 'end');
        s += txt(W / 2, 206, 'H = kT / (mg): чем тяжелее молекула, тем ниже столб', SOFT, 10.5);
        return svg(W, H, s);
    };

    // Шаг 8. Общий закон: заселённость уровня падает экспоненциально с его энергией.
    F.boltzlevels = function () {
        var W = 440, H = 218, x = 126, wmax = 176;
        var s = txt(W / 2, 20, 'заселённость падает экспоненциально с энергией', INK, 11.5);
        [[170, 1, 'E = 0', '100 %'], [140, 0.368, 'kT', '37 %'], [110, 0.135, '2kT', '14 %'], [80, 0.050, '3kT', '5 %']]
            .forEach(function (b) {
                var y = b[0], w = Math.max(2, wmax * b[1]);
                s += '<line x1="' + (x - 8) + '" y1="' + y + '" x2="' + (x + wmax + 8) + '" y2="' + y +
                     '" stroke="' + BORD + '" stroke-width="1"/>';
                s += '<rect x="' + x + '" y="' + (y - 11) + '" width="' + w + '" height="11" fill="' + LINK + '" opacity="0.55"/>';
                s += txt(x - 16, y + 4, b[2], INK, 11.5, 'end');
                s += txt(x + wmax + 16, y + 4, b[3], SOFT, 10.5, 'start');
            });
        s += '<line x1="' + (x - 8) + '" y1="48" x2="' + (x + wmax + 8) + '" y2="48" stroke="' + WARN +
             '" stroke-width="1.4" stroke-dasharray="5,4"/>';
        s += '<rect x="' + x + '" y="41" width="2" height="7" fill="' + WARN + '"/>';
        s += txt(x - 16, 52, 'колебание N₂: 11 kT', WARN, 10.5, 'end');
        s += txt(x + wmax + 16, 52, 'одна молекула из 80 000', WARN, 10.5, 'start');
        s += txt(W / 2, 206, 'n₂ / n₁ = exp(−ΔE / kT)', INK, 12.5);
        return svg(W, H, s);
    };


    // ── Распределение Максвелла: у газа нет одной скорости, есть кривая ───────

    /* Заготовка кривой для схем ниже: точки ломаной по готовой функции.
       Масштаб по вертикали задаётся явно (scaleY), чтобы на одной картинке можно было
       рисовать сомножители с разными «потолками» и сравнивать их форму, а не величину. */
    function mxPath(x0, y0, wpx, hpx, xmax, scaleY, fn) {
        var p = '', n = 120;
        for (var i = 0; i <= n; i++) {
            var x = xmax * i / n, X = x0 + wpx * i / n, Y = y0 - hpx * fn(x) / scaleY;
            p += (i ? ' L' : 'M') + X.toFixed(1) + ',' + Y.toFixed(1);
        }
        return p;
    }

    // 1. Одной скорости у газа нет: спрашивать надо про долю в интервале.
    F.mxspread = function () {
        var W = 450, H = 196, x0 = 22, y0 = 36, bw = 186, bh = 116, base = y0 + bh;
        var s = txt(W / 2, 20, 'одна температура — разные скорости', INK, 11.5);
        s += '<rect x="' + x0 + '" y="' + y0 + '" width="' + bw + '" height="' + bh +
             '" fill="none" stroke="' + INK + '" stroke-width="1.6"/>';
        [[54, 62, 30, -8], [104, 54, 11, 13], [148, 74, 42, 7], [66, 104, 7, -15],
         [112, 120, 28, -20], [168, 112, 15, 17], [46, 136, 36, 5], [154, 44, 6, 11]]
        .forEach(function (p) {
            s += mol(p[0], p[1], 4.5);
            s += arrow(p[0] + 6, p[1], p[0] + 6 + p[2], p[1] + p[3], LINK, 'ahl');
        });
        var bx = 254;
        [9, 25, 43, 52, 41, 27, 15, 8, 4].forEach(function (h, i) {
            s += '<rect x="' + (bx + i * 19) + '" y="' + (base - h) + '" width="15" height="' + h +
                 '" fill="' + LINK + '" opacity="0.7"/>';
        });
        s += '<line x1="' + (bx - 10) + '" y1="' + base + '" x2="' + (bx + 178) + '" y2="' + base +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(bx + 84, base + 16, 'скорость', SOFT, 10.5);
        s += txt(bx + 84, y0 + 4, 'сколько молекул', SOFT, 10.5);
        s += txt(W / 2, H - 6, 'вопрос не «какая скорость», а «какая доля»', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 2. Пространство скоростей: молекула — точка, газ — облако точек.
    F.mxvspace = function () {
        var W = 440, H = 214, cx = 148, cy = 116, R = 84;
        var s = txt(W / 2, 20, 'пространство скоростей', INK, 11.5);
        s += '<line x1="' + (cx - R - 16) + '" y1="' + cy + '" x2="' + (cx + R + 16) + '" y2="' + cy +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="' + (cy + R + 16) + '" x2="' + cx + '" y2="' + (cy - R - 16) +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(cx + R + 26, cy + 4, 'v&#8339;', SOFT, 11);
        s += txt(cx + 10, cy - R - 22, 'v<tspan font-size="8" dy="2">y</tspan>', SOFT, 11, 'start');
        [[6, -10], [-14, 8], [22, 16], [-28, -20], [38, -8], [-8, 32], [16, -34], [-40, 26],
         [48, 30], [-52, -14], [30, 52], [-22, -48], [62, -24], [-64, 18], [10, 64], [-36, -58],
         [70, 44], [-74, -36], [44, -70], [2, 4], [-6, -2], [18, -4], [-18, -14], [26, -28],
         [-30, 40], [54, 6], [-46, -4]].forEach(function (p) {
            var d = Math.sqrt(p[0] * p[0] + p[1] * p[1]);
            s += '<circle cx="' + (cx + p[0]) + '" cy="' + (cy + p[1]) + '" r="3" fill="' + LINK +
                 '" opacity="' + (d > 60 ? 0.35 : 0.75) + '"/>';
        });
        s += arrow(cx, cy, cx + 48, cy + 30, WARN, 'ahw');
        s += txt(cx + 56, cy + 52, 'одна молекула', WARN, 10.5, 'start');
        s += txt(268, 88, 'модуль скорости —', SOFT, 10.5, 'start');
        s += txt(268, 104, 'расстояние от нуля', SOFT, 10.5, 'start');
        s += txt(W / 2, H - 6, 'весь газ — облако точек, самое густое у начала координат', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 3. Изотропия: плотность облака зависит только от модуля.
    F.mxisotropy = function () {
        var W = 430, H = 206, cx = 148, cy = 112, R = 74;
        var s = txt(W / 2, 20, 'ни одно направление не выделено', INK, 11.5);
        s += '<line x1="' + (cx - R - 18) + '" y1="' + cy + '" x2="' + (cx + R + 18) + '" y2="' + cy +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + cx + '" y1="' + (cy + R + 18) + '" x2="' + cx + '" y2="' + (cy - R - 18) +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        [30, 52, 74].forEach(function (r, i) {
            s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + LINK +
                 '" stroke-width="1.2" stroke-dasharray="4,4" opacity="' + (0.8 - i * 0.18) + '"/>';
        });
        [0.6, 2.1, 3.9, 5.2].forEach(function (a) {
            s += '<circle cx="' + (cx + 52 * Math.cos(a)).toFixed(1) + '" cy="' + (cy + 52 * Math.sin(a)).toFixed(1) +
                 '" r="4.5" fill="' + WARN + '"/>';
        });
        s += arrow(cx, cy, cx + 52 * Math.cos(0.6), cy + 52 * Math.sin(0.6), SOFT);
        s += txt(cx + 8, cy + 44, 'v', SOFT, 11, 'start');
        s += txt(288, 96, 'одинаковый модуль —', INK, 10.5, 'start');
        s += txt(288, 112, 'одинаковая плотность', INK, 10.5, 'start');
        s += txt(W / 2, H - 6, 'плотность облака — функция одного только модуля', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 4. Больцмановский множитель: энергии складываются, вероятности умножаются.
    F.mxboltz = function () {
        var W = 450, H = 208, x0 = 42, base = 150, wpx = 170, hpx = 96;
        var s = txt(W / 2, 20, 'вероятность энергии падает по экспоненте', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + (x0 + wpx + 14) + '" y2="' + base +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + (base - hpx - 14) +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        [[1.0, LINK, 2.2], [0.42, WARN, 1.8]].forEach(function (c) {
            s += '<path d="' + mxPath(x0, base, wpx, hpx, 3, 1, function (t) { return Math.exp(-t * c[0]); }) +
                 '" fill="none" stroke="' + c[1] + '" stroke-width="' + c[2] + '"/>';
        });
        s += txt(x0 + 116, base - 60, 'горячее', WARN, 10.5, 'start');
        s += txt(x0 + 56, base - 22, 'холоднее', LINK, 10.5, 'start');
        s += txt(x0 + wpx / 2, base + 18, 'энергия &#949;', SOFT, 10.5);
        var rx = 268;
        s += '<rect x="' + rx + '" y="50" width="64" height="44" fill="' + LINK +
             '" opacity="0.14" stroke="' + LINK + '"/>';
        s += '<rect x="' + (rx + 86) + '" y="50" width="64" height="44" fill="' + LINK +
             '" opacity="0.14" stroke="' + LINK + '"/>';
        s += txt(rx + 32, 78, '&#949;₁', INK, 13);
        s += txt(rx + 118, 78, '&#949;₂', INK, 13);
        s += txt(rx + 75, 118, 'энергии складываются', SOFT, 10.5);
        s += txt(rx + 75, 136, 'вероятности умножаются', SOFT, 10.5);
        s += txt(rx + 75, 164, 'p(&#949;₁+&#949;₂) = p(&#949;₁)·p(&#949;₂)', INK, 11);
        s += txt(W / 2, H - 6, 'сумму в произведение превращает только экспонента', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 5. Шаровой слой: единственный источник множителя v².
    F.mxshell = function () {
        var W = 440, H = 214, cx = 132, cy = 116, R = 78;
        var s = txt(W / 2, 20, 'все молекулы с модулем v лежат в шаровом слое', INK, 11.5);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="' + LINK + '" opacity="0.10"/>';
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="none" stroke="' + LINK + '" stroke-width="1.5"/>';
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + (R - 9) + '" fill="none" stroke="' + LINK + '" stroke-width="1.5"/>';
        s += '<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + R + '" ry="26" fill="none" stroke="' +
             SOFT + '" stroke-width="1" stroke-dasharray="4,4"/>';
        s += arrow(cx, cy, cx + 53, cy - 51, INK);
        s += txt(cx + 24, cy - 40, 'v', INK, 12, 'start');
        s += '<line x1="' + (cx + R - 12) + '" y1="' + (cy + 34) + '" x2="' + (cx + R + 22) + '" y2="' + (cy + 50) +
             '" stroke="' + SOFT + '" stroke-width="1"/>';
        s += txt(cx + R + 26, cy + 54, 'dv', SOFT, 10.5, 'start');
        var rx = 262;
        s += txt(rx, 72, 'площадь сферы', SOFT, 10.5, 'start');
        s += txt(rx, 92, '4&#960;v²', INK, 15, 'start');
        s += txt(rx, 118, 'толщина слоя', SOFT, 10.5, 'start');
        s += txt(rx, 138, 'dv', INK, 15, 'start');
        s += '<line x1="' + rx + '" y1="152" x2="' + (rx + 132) + '" y2="152" stroke="' + BORD + '" stroke-width="1"/>';
        s += txt(rx, 174, 'объём 4&#960;v²dv', WARN, 12.5, 'start');
        s += txt(W / 2, H - 6, 'при v → 0 слой стягивается в точку — медленных молекул почти нет', SOFT, 10);
        return svg(W, H, s);
    };

    // 6. Горка как произведение растущего v² на падающую экспоненту.
    F.mxproduct = function () {
        var W = 450, H = 216, x0 = 44, base = 166, wpx = 350, hpx = 118, XM = 2.6;
        var s = txt(W / 2, 20, 'горка получается из борьбы двух сомножителей', INK, 11.5);
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + (x0 + wpx + 12) + '" y2="' + base +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + x0 + '" y2="' + (base - hpx - 12) +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<path d="' + mxPath(x0, base, wpx, hpx, XM, XM * XM, function (x) { return x * x; }) +
             '" fill="none" stroke="' + SOFT + '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += '<path d="' + mxPath(x0, base, wpx, hpx, XM, 1, function (x) { return Math.exp(-x * x); }) +
             '" fill="none" stroke="' + WARN + '" stroke-width="1.6" stroke-dasharray="5,4"/>';
        s += '<path d="' + mxPath(x0, base, wpx, hpx, XM, Math.exp(-1), function (x) { return x * x * Math.exp(-x * x); }) +
             '" fill="none" stroke="' + LINK + '" stroke-width="2.6"/>';
        s += txt(x0 + 300, base - 108, 'v²', SOFT, 12.5, 'start');
        s += txt(x0 + 112, base - 98, 'e^(&#8722;mv²/2kT)', WARN, 11, 'start');
        s += txt(x0 + 170, base - 82, 'f(v)', LINK, 12.5, 'start');
        s += txt(x0 + wpx / 2, base + 18, 'скорость', SOFT, 10.5);
        s += txt(W / 2, H - 6, 'слева душит геометрия, справа — экспонента, максимум посередине', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 7. Три характерные скорости на одной несимметричной кривой.
    F.mxthree = function () {
        var W = 460, H = 208, x0 = 36, base = 156, wpx = 266, hpx = 98, XM = 3.0;
        var SY = Math.exp(-1), i, xx;
        var fn = function (x) { return x * x * Math.exp(-x * x); };
        var px = function (x) { return x0 + wpx * x / XM; };
        var py = function (x) { return base - hpx * fn(x) / SY; };
        var s = txt(x0 + wpx / 2, 20, 'три скорости одного и того же газа', INK, 11.5);
        var p = 'M' + px(1.2247).toFixed(1) + ',' + base;
        for (i = 0; i <= 60; i++) { xx = 1.2247 + (XM - 1.2247) * i / 60; p += ' L' + px(xx).toFixed(1) + ',' + py(xx).toFixed(1); }
        p += ' L' + px(XM).toFixed(1) + ',' + base + ' Z';
        s += '<path d="' + p + '" fill="' + LINK + '" opacity="0.16"/>';
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + (x0 + wpx + 10) + '" y2="' + base +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<path d="' + mxPath(x0, base, wpx, hpx, XM, SY, fn) + '" fill="none" stroke="' + LINK + '" stroke-width="2.4"/>';
        [[1, INK, 'вероятнейшая', '1,00'], [1.1284, MOSS, 'средняя', '1,13'], [1.2247, WARN, 'среднеквадр.', '1,22']]
        .forEach(function (m, k) {
            var X = px(m[0]).toFixed(1);
            s += '<line x1="' + X + '" y1="' + base + '" x2="' + X + '" y2="' + (base - hpx - 8 - k * 9) +
                 '" stroke="' + m[1] + '" stroke-width="1.5"/>';
            s += '<rect x="316" y="' + (58 + k * 24) + '" width="11" height="11" fill="' + m[1] + '"/>';
            s += txt(334, 68 + k * 24, m[2], INK, 10.5, 'start');
            s += txt(452, 68 + k * 24, m[3], SOFT, 10.5, 'end');
        });
        s += txt(x0 + wpx / 2 + 30, base + 18, 'длинный хвост тянет среднее вправо', SOFT, 10.5);
        s += txt(W / 2, H - 6, 'отношение 1 : 1,128 : 1,225 одинаково для любого газа', SOFT, 10.5);
        return svg(W, H, s);
    };

    // 8. Хвост: доля за порогом отзывается на нагрев несоразмерно сильно.
    F.mxtail = function () {
        var W = 460, H = 214, x0 = 40, base = 160, wpx = 372, hpx = 100, XM = 3.2, CUT = 2.0;
        var SY = Math.exp(-1);
        var px = function (x) { return x0 + wpx * x / XM; };
        var s = txt(W / 2, 20, 'порог сдвинулся чуть — хвост вырос в разы', INK, 11.5);
        [[1.0, LINK, 0.20], [1.22, WARN, 0.32]].forEach(function (c) {
            var w = c[0];
            var fn = function (x) { var u = x / w; return u * u * Math.exp(-u * u) / w; };
            var p = 'M' + px(CUT).toFixed(1) + ',' + base, i, xx;
            for (i = 0; i <= 60; i++) {
                xx = CUT + (XM - CUT) * i / 60;
                p += ' L' + px(xx).toFixed(1) + ',' + (base - hpx * fn(xx) / SY).toFixed(1);
            }
            p += ' L' + px(XM).toFixed(1) + ',' + base + ' Z';
            s += '<path d="' + p + '" fill="' + c[1] + '" opacity="' + c[2] + '"/>';
            s += '<path d="' + mxPath(x0, base, wpx, hpx, XM, SY, fn) + '" fill="none" stroke="' + c[1] + '" stroke-width="2.2"/>';
        });
        s += '<line x1="' + x0 + '" y1="' + base + '" x2="' + (x0 + wpx + 10) + '" y2="' + base +
             '" stroke="' + BORD + '" stroke-width="1"/>';
        s += '<line x1="' + px(CUT).toFixed(1) + '" y1="' + base + '" x2="' + px(CUT).toFixed(1) +
             '" y2="40" stroke="' + INK + '" stroke-width="1.8" stroke-dasharray="4,3"/>';
        s += txt(px(CUT) - 6, 36, 'порог', INK, 10.5, 'end');
        s += '<rect x="350" y="46" width="11" height="11" fill="' + LINK + '" opacity="0.85"/>';
        s += txt(368, 56, 'холоднее', LINK, 10.5, 'start');
        s += '<rect x="350" y="68" width="11" height="11" fill="' + WARN + '" opacity="0.85"/>';
        s += txt(368, 78, 'горячее', WARN, 10.5, 'start');
        s += txt(px(2.6), base + 18, 'быстрее порога', SOFT, 10.5);
        s += txt(W / 2, H - 6, 'средняя скорость подросла на проценты, доля за порогом — в разы', SOFT, 10.5);
        return svg(W, H, s);
    };

    global.B42Figures = F;
})(window);
