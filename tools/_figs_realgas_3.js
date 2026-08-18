/* ЗАГОТОВКА СХЕМ — realgas / 03-heatcap («Теплоёмкости C_V и C_p: куда уходит тепло»).

   Файл не самостоятельный: восемь функций ниже написаны для вклейки в js/figures.js
   внутрь его IIFE, где уже определены svg(), txt(), mol(), arrow(), wall() и цвета
   INK / SOFT / LINK / WARN / BORD / MOSS. Отдельно этот файл не подключается.

   Русские подписи, попадающие внутрь SVG через txt(), выписаны списком в самом конце
   файла — их надо добавить в словарь js/figures-i18n.js. */

// 1. Теплоёмкость — свойство процесса: одна и та же теплота, два разных прироста температуры.
F.realheat = function () {
    var W = 440, H = 214, base = 168;
    var s = txt(W / 2, 18, 'одна и та же теплота, два разных ответа', SOFT, 11);

    // жёсткий баллон
    s += '<rect x="42" y="52" width="128" height="86" fill="' + WARN + '" opacity="0.10" stroke="' + INK + '" stroke-width="2"/>';
    s += txt(106, 44, 'жёсткий баллон', WARN, 10.5);
    s += mol(74, 76, 5, WARN); s += mol(120, 68, 5, WARN); s += mol(96, 108, 5, WARN); s += mol(146, 112, 5, WARN);
    s += arrow(106, 200, 106, 142, WARN, 'ahw');
    s += txt(90, 190, 'Q', WARN, 13, 'end');

    // цилиндр со свободным поршнем
    s += '<rect x="272" y="52" width="128" height="86" fill="' + LINK + '" opacity="0.10" stroke="' + INK + '" stroke-width="2"/>';
    s += '<rect x="272" y="46" width="128" height="10" fill="' + LINK + '" opacity="0.55" stroke="' + LINK + '" stroke-width="1.4"/>';
    s += '<line x1="272" y1="66" x2="400" y2="66" stroke="' + SOFT + '" stroke-width="1" stroke-dasharray="4,3"/>';
    s += arrow(336, 40, 336, 22, LINK, 'ahl');
    s += txt(336, 14, 'поршень уходит вверх', LINK, 10.5);
    s += mol(304, 88, 5, LINK); s += mol(350, 80, 5, LINK); s += mol(326, 118, 5, LINK); s += mol(376, 114, 5, LINK);
    s += arrow(336, 200, 336, 142, LINK, 'ahl');
    s += txt(320, 190, 'Q', LINK, 13, 'end');

    // столбики прироста температуры: 100 против 71 пикселя — это и есть 1,40
    s += '<rect x="42" y="' + base + '" width="100" height="11" fill="' + WARN + '" opacity="0.75"/>';
    s += txt(152, base + 10, 'ΔT больше', WARN, 10.5, 'start');
    s += '<rect x="272" y="' + base + '" width="71" height="11" fill="' + LINK + '" opacity="0.75"/>';
    s += txt(352, base + 10, 'ΔT меньше', LINK, 10.5, 'start');
    s += txt(W / 2, H - 6, 'пока не сказано, что закреплено, вопрос «сколько» без ответа', SOFT, 10.5);
    return svg(W, H, s);
};

// 2. V = const: работы нет, вся теплота уходит во внутреннюю энергию.
F.realpiston = function () {
    var W = 430, H = 200;
    var s = txt(W / 2, 18, 'поршень закреплён: dV = 0', SOFT, 11);
    s += '<rect x="60" y="42" width="200" height="96" fill="' + LINK + '" opacity="0.10" stroke="' + INK + '" stroke-width="2"/>';
    s += '<rect x="256" y="42" width="14" height="96" fill="' + SOFT + '" opacity="0.55" stroke="' + INK + '" stroke-width="1.4"/>';
    // стопоры: поршню некуда идти
    s += '<line x1="270" y1="56" x2="300" y2="56" stroke="' + INK + '" stroke-width="3"/>';
    s += '<line x1="270" y1="124" x2="300" y2="124" stroke="' + INK + '" stroke-width="3"/>';
    s += txt(306, 94, 'стопор', SOFT, 10.5, 'start');
    // молекулы: до и после — те же места, но быстрее
    [[100, 66], [160, 58], [128, 104], [196, 96], [214, 62], [86, 118]].forEach(function (p, k) {
        s += mol(p[0], p[1], 5, k % 2 ? LINK : WARN);
        s += arrow(p[0] + 6, p[1], p[0] + 6 + (k % 2 ? 16 : 30), p[1] - (k % 3 ? 6 : -8),
                   k % 2 ? LINK : WARN, k % 2 ? 'ahl' : 'ahw');
    });
    s += arrow(160, 186, 160, 142, WARN, 'ahw');
    s += txt(144, 178, 'Q', WARN, 13, 'end');
    s += txt(W / 2, 166, 'C_V = (∂U/∂T) при V = const', INK, 13);
    s += txt(W / 2, H - 5, 'вся теплота — в скорости молекул, наружу не ушло ничего', SOFT, 10.5);
    return svg(W, H, s);
};

// 3. p = const: поршень свободен, и газ доплачивает работу p·ΔV = R·ΔT.
F.realwork = function () {
    var W = 430, H = 214, x0 = 90, x1 = 250, yTop = 96, dh = 34;
    var s = txt(W / 2, 18, 'давление постоянно: груз на поршне тот же', SOFT, 11);
    // груз
    s += '<rect x="' + (x0 + 34) + '" y="30" width="92" height="20" fill="' + SOFT + '" opacity="0.45" stroke="' + INK + '" stroke-width="1.4"/>';
    s += txt(x0 + 80, 44, 'груз', SOFT, 10.5);
    // цилиндр
    s += '<rect x="' + x0 + '" y="' + yTop + '" width="' + (x1 - x0) + '" height="60" fill="' + LINK + '" opacity="0.10" stroke="' + INK + '" stroke-width="2"/>';
    // прибавка объёма
    s += '<rect x="' + x0 + '" y="' + (yTop - dh) + '" width="' + (x1 - x0) + '" height="' + dh + '" fill="' + MOSS + '" opacity="0.18" stroke="' + MOSS + '" stroke-dasharray="4,3"/>';
    s += txt((x0 + x1) / 2, yTop - dh / 2 + 4, 'ΔV', MOSS, 13);
    s += '<rect x="' + x0 + '" y="' + (yTop - dh - 10) + '" width="' + (x1 - x0) + '" height="10" fill="' + LINK + '" opacity="0.55" stroke="' + LINK + '" stroke-width="1.4"/>';
    s += '<line x1="' + (x1 + 8) + '" y1="' + yTop + '" x2="' + (x1 + 8) + '" y2="' + (yTop - dh) + '" stroke="' + BORD + '" stroke-width="1"/>';
    s += arrow(x1 + 8, yTop, x1 + 8, yTop - dh + 2, MOSS);
    s += txt(x1 + 16, yTop - dh / 2 + 4, 'Δh', MOSS, 11, 'start');
    s += arrow((x0 + x1) / 2, 198, (x0 + x1) / 2, 162, WARN, 'ahw');
    s += txt((x0 + x1) / 2 - 16, 190, 'Q', WARN, 13, 'end');
    s += txt(340, 116, 'работа', MOSS, 11);
    s += txt(340, 134, 'p · ΔV = R · ΔT', MOSS, 13);
    s += txt(340, 158, 'на моль и на градус', SOFT, 10);
    s += txt(W / 2, H - 5, 'доплата не зависит от того, что за газ', SOFT, 10.5);
    return svg(W, H, s);
};

// 4. Соотношение Майера: разность двух теплоёмкостей есть в точности R.
F.realmayer = function () {
    var W = 430, H = 216, base = 168, k = 4.0;   // 4 пикселя на Дж/(моль·К)
    var s = txt(W / 2, 18, 'два измерения и одна разность', SOFT, 11);
    function bar(x, val, color, cap, num) {
        var h = val * k;
        var t = '<rect x="' + x + '" y="' + (base - h) + '" width="66" height="' + h + '" fill="' + color + '" opacity="0.70" stroke="' + color + '" stroke-width="1.4"/>';
        t += txt(x + 33, base - h - 8, num, color, 12);
        t += txt(x + 33, base + 16, cap, SOFT, 10.5);
        return t;
    }
    s += bar(66, 20.79, WARN, 'при V = const', '20,79');
    s += bar(182, 29.10, LINK, 'при p = const', '29,10');
    s += bar(298, 8.31, MOSS, 'разность', '8,31');
    s += '<line x1="52" y1="' + base + '" x2="378" y2="' + base + '" stroke="' + BORD + '" stroke-width="1.4"/>';
    s += '<line x1="248" y1="' + (base - 29.10 * k) + '" x2="331" y2="' + (base - 29.10 * k) + '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
    s += '<line x1="132" y1="' + (base - 20.79 * k) + '" x2="331" y2="' + (base - 20.79 * k) + '" stroke="' + BORD + '" stroke-width="1" stroke-dasharray="3,3"/>';
    s += txt(W / 2, base + 38, 'C_p − C_V = R = 8,314 Дж/(моль·К)', INK, 13.5);
    s += txt(W / 2, H - 5, 'воздух, Дж на моль и на градус', SOFT, 10.5);
    return svg(W, H, s);
};

// 5. Счёт степеней свободы: по ½kT на каждую, и опыт с гелием это подтверждает.
F.realdof = function () {
    var W = 440, H = 206, cx = 108, cy = 92, base = 156, k = 4.4;
    var s = txt(W / 2, 18, 'одноатомный газ: только три направления движения', SOFT, 11);
    s += mol(cx, cy, 13, LINK);
    [[0, -46], [42, 22], [-42, 22]].forEach(function (d) {
        s += arrow(cx, cy, cx + d[0], cy + d[1], LINK, 'ahl');
    });
    s += txt(cx, cy - 56, 'z', LINK, 11);
    s += txt(cx + 54, cy + 30, 'x', LINK, 11);
    s += txt(cx - 54, cy + 30, 'y', LINK, 11);
    s += txt(cx, base + 14, 'три степени свободы', SOFT, 10.5);
    s += txt(cx, base + 30, 'по ½kT на каждую', SOFT, 10.5);
    function bar(x, val, color, cap, num) {
        var h = val * k;
        var t = '<rect x="' + x + '" y="' + (base - h) + '" width="52" height="' + h + '" fill="' + color + '" opacity="0.70" stroke="' + color + '" stroke-width="1.4"/>';
        t += txt(x + 26, base - h - 8, num, color, 11.5);
        t += txt(x + 26, base + 14, cap, SOFT, 10.5);
        return t;
    }
    s += bar(238, 12.47, INK, 'формула', '12,47');
    s += bar(316, 12.5, WARN, 'гелий, опыт', '12,5');
    s += '<line x1="226" y1="' + base + '" x2="382" y2="' + base + '" stroke="' + BORD + '" stroke-width="1.4"/>';
    s += txt(304, 40, 'C_V = (i / 2) R', INK, 14);
    s += txt(W / 2, H - 5, 'совпадение до третьей значащей цифры', SOFT, 10.5);
    return svg(W, H, s);
};

// 6. Лесенка уровней: вращательная ступенька ниже kT, колебательная — много выше.
F.realladder = function () {
    var W = 440, H = 224, xL = 70, xR = 300, wl = 100, ykT = 132;
    var s = txt(W / 2, 18, 'ступенька дешевле теплового кванта — работает; дороже — молчит', SOFT, 10.5);
    // ось энергии
    s += '<line x1="34" y1="200" x2="34" y2="40" stroke="' + BORD + '" stroke-width="1.4" marker-end="url(#ah)"/>';
    s += txt(24, 46, 'E', SOFT, 11, 'end');
    // линия kT
    s += '<line x1="40" y1="' + ykT + '" x2="410" y2="' + ykT + '" stroke="' + INK + '" stroke-width="1.6" stroke-dasharray="6,4"/>';
    s += txt(414, ykT + 4, 'kT при 300 К', INK, 10.5, 'start');
    // вращения: густые ступеньки под линией
    var i;
    for (i = 0; i < 7; i++) {
        s += '<line x1="' + xL + '" y1="' + (196 - i * 7) + '" x2="' + (xL + wl) + '" y2="' + (196 - i * 7) + '" stroke="' + MOSS + '" stroke-width="2"/>';
    }
    s += txt(xL + wl / 2, 214, 'вращение, θ = 2,9 К', MOSS, 10.5);
    s += arrow(xL + wl + 14, 190, xL + wl + 14, 176, MOSS);
    s += txt(xL + wl + 20, 186, 'ступеньки мелкие', MOSS, 10, 'start');
    // колебания: редкие ступеньки высоко над линией
    for (i = 0; i < 3; i++) {
        s += '<line x1="' + xR + '" y1="' + (96 - i * 26) + '" x2="' + (xR + wl) + '" y2="' + (96 - i * 26) + '" stroke="' + WARN + '" stroke-width="2"/>';
    }
    s += txt(xR + wl / 2, 112, 'колебание, θ = 3390 К', WARN, 10.5);
    s += arrow(xR - 14, 118, xR - 14, 100, WARN, 'ahw');
    s += txt(xR - 20, 118, 'первая ступень', WARN, 10, 'end');
    s += txt(xR - 20, 132, 'недосягаема', WARN, 10, 'end');
    s += txt(W / 2, 60, 'i = 3 + 2 + 0 = 5, а не 7', INK, 14);
    return svg(W, H, s);
};

// 7. Показатель γ безразмерен: три числа, которые надо просто различить в опыте.
F.realgamma = function () {
    var W = 440, H = 190, y = 108, x0 = 40, wpx = 340, g0 = 1.25, g1 = 1.75;
    function X(g) { return x0 + wpx * (g - g0) / (g1 - g0); }
    var s = txt(W / 2, 18, 'γ = (i + 2) / i — число без единиц', SOFT, 11);
    s += '<line x1="' + x0 + '" y1="' + y + '" x2="' + (x0 + wpx) + '" y2="' + y + '" stroke="' + INK + '" stroke-width="1.6"/>';
    [[1.286, 'CO₂', '9/7 = 1,29', 'i ≈ 7', WARN],
     [1.400, 'воздух, N₂', '7/5 = 1,40', 'i = 5', LINK],
     [1.667, 'гелий, аргон', '5/3 = 1,67', 'i = 3', MOSS]].forEach(function (p) {
        var x = X(p[0]);
        s += '<line x1="' + x + '" y1="' + (y - 9) + '" x2="' + x + '" y2="' + (y + 9) + '" stroke="' + p[4] + '" stroke-width="2.4"/>';
        s += mol(x, y, 4.5, p[4]);
        s += txt(x, y - 32, p[2], p[4], 12);
        s += txt(x, y - 16, p[3], p[4], 10.5);
        s += txt(x, y + 26, p[1], SOFT, 10.5);
    });
    s += txt(x0, y + 46, '1,25', SOFT, 10);
    s += txt(x0 + wpx, y + 46, '1,75', SOFT, 10);
    s += txt(W / 2, H - 6, 'меньше степеней свободы — больше γ', SOFT, 10.5);
    return svg(W, H, s);
};

// 8. Скорость звука как измеритель γ: Ньютон считал изотермой, Лаплас вернул адиабату.
F.realsound = function () {
    var W = 440, H = 224, base = 150, sc = 0.30;   // 0,30 пикселя на м/с
    var s = txt(W / 2, 18, 'сжатия в звуковой волне идут без теплообмена', SOFT, 11);
    // волна сжатий и разрежений
    var i, x;
    for (i = 0; i < 26; i++) {
        x = 34 + i * 5.4;
        var dense = Math.cos(i * 0.62) > 0 ? 2.2 : 0.9;
        s += '<line x1="' + x.toFixed(1) + '" y1="36" x2="' + x.toFixed(1) + '" y2="86" stroke="' + LINK + '" stroke-width="' + dense + '"/>';
    }
    s += arrow(34, 100, 176, 100, INK);
    s += txt(105, 116, 'волна идёт со скоростью c', SOFT, 10.5);
    s += txt(300, 52, 'c = √(γRT / M)', INK, 15);
    s += txt(300, 74, 'γ вытаскивается секундомером,', SOFT, 10.5);
    s += txt(300, 90, 'а не калориметром', SOFT, 10.5);
    // два столбика для воздуха: Ньютон против опыта
    s += '<rect x="60" y="' + base + '" width="' + (290 * sc).toFixed(0) + '" height="14" fill="none" stroke="' + SOFT + '" stroke-width="1.6" stroke-dasharray="5,4"/>';
    s += txt(66 + 290 * sc, base + 12, '290 м/с — Ньютон, изотерма', SOFT, 10.5, 'start');
    s += '<rect x="60" y="' + (base + 24) + '" width="' + (343 * sc).toFixed(0) + '" height="14" fill="' + LINK + '" opacity="0.70"/>';
    s += txt(66 + 343 * sc, base + 36, '343 м/с — опыт и Лаплас', LINK, 10.5, 'start');
    s += txt(W / 2, H - 22, 'гелий 1007 · воздух 343 · CO₂ 267 м/с', INK, 12);
    s += txt(W / 2, H - 6, 'три скорости читаются как i = 3, i = 5 и i ≈ 7', SOFT, 10.5);
    return svg(W, H, s);
};


/* ──────────────────────────────────────────────────────────────────────────
   РУССКИЕ ПОДПИСИ ВНУТРИ СХЕМ — в словарь js/figures-i18n.js.
   Порядок: по функциям сверху вниз. Чисто математические строки
   («C_V = (i / 2) R», «290 м/с», «1,25») сюда не вынесены — кроме тех,
   где рядом стоит русское слово.

   realheat:
     'одна и та же теплота, два разных ответа'
     'жёсткий баллон'
     'поршень уходит вверх'
     'ΔT больше'
     'ΔT меньше'
     'пока не сказано, что закреплено, вопрос «сколько» без ответа'

   realpiston:
     'поршень закреплён: dV = 0'
     'стопор'
     'C_V = (∂U/∂T) при V = const'
     'вся теплота — в скорости молекул, наружу не ушло ничего'

   realwork:
     'давление постоянно: груз на поршне тот же'
     'груз'
     'работа'
     'на моль и на градус'
     'доплата не зависит от того, что за газ'

   realmayer:
     'два измерения и одна разность'
     'при V = const'
     'при p = const'
     'разность'
     'C_p − C_V = R = 8,314 Дж/(моль·К)'
     'воздух, Дж на моль и на градус'

   realdof:
     'одноатомный газ: только три направления движения'
     'три степени свободы'
     'по ½kT на каждую'
     'формула'
     'гелий, опыт'
     'совпадение до третьей значащей цифры'

   realladder:
     'ступенька дешевле теплового кванта — работает; дороже — молчит'
     'kT при 300 К'
     'вращение, θ = 2,9 К'
     'ступеньки мелкие'
     'колебание, θ = 3390 К'
     'первая ступень'
     'недосягаема'
     'i = 3 + 2 + 0 = 5, а не 7'

   realgamma:
     'γ = (i + 2) / i — число без единиц'
     'воздух, N₂'
     'гелий, аргон'
     'меньше степеней свободы — больше γ'

   realsound:
     'сжатия в звуковой волне идут без теплообмена'
     'волна идёт со скоростью c'
     'γ вытаскивается секундомером,'
     'а не калориметром'
     '290 м/с — Ньютон, изотерма'
     '343 м/с — опыт и Лаплас'
     'гелий 1007 · воздух 343 · CO₂ 267 м/с'
     'три скорости читаются как i = 3, i = 5 и i ≈ 7'
   ────────────────────────────────────────────────────────────────────────── */
