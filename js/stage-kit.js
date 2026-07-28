/* stage-kit.js — набор блоков для сцены стенда (B42Kit).

   Зачем: модели в models.js рисовали каждую сцену с нуля, и одни и те же вещи —
   стрелка-вектор, пружина, груз, сосуд с поршнем, шкала, приборная надпись в углу —
   были скопированы по 5–8 раз с чуть разными числами. Из-за этого новый стенд под новый
   закон стоил дорого, а правка стиля не доезжала до половины моделей.

   Здесь эти вещи собраны один раз. Модель описывает ФИЗИКУ, а сцену набирает из готовых
   блоков: KIT.spring(...), KIT.body(...), KIT.arrow(...). Новый закон = новая комбинация
   блоков, а не новый рисовальщик.

   Правила набора:
   · Ноль зависимостей, только canvas 2D. Работает без движка (пригодно и вне explorable.js).
   · Каждый блок сам сохраняет и восстанавливает состояние контекста (alpha, dash, шрифт,
     выравнивание). Вызвавший не обязан за собой убирать — это был главный источник
     «протёкших» пунктиров и полупрозрачности в соседний примитив.
   · Цвета: тематические (текст/фон/рамка) приходят из ctx.c движка, предметные — из KIT.palette.
   · Единицы не форматируются здесь: число приходит уже готовым (см. B42Units в models.js).

   API: window.B42Kit — см. разделы ниже. */
(function (global) {
    'use strict';

    // ── палитра предметов ──────────────────────────────────────────
    // Раньше эти литералы были разбросаны по всем моделям. Смысловые имена, а не «синий»:
    // одинаковая роль на разных стендах должна быть одного цвета.
    var palette = {
        primary: '#155E74',   // основной объект: пружина, груз, сосуд
        ochre:   '#8F6417',   // связь/проекция/вспомогательное построение
        green:   '#4C6B4E',   // кинетическая энергия, «норма»
        red:     '#9B2C2C',   // сила, опасная зона, потери
        blue:    '#4a7c9b',   // поле, поток, холодная зона
        warm:    '#c0392b',   // нагрев, предел
        ok:      '#2e9e5b'
    };

    var FONT = 'Inter, sans-serif';

    // ── текст и состояние контекста ────────────────────────────────
    function text(g, str, x, y, o) {
        o = o || {};
        g.save();
        g.font = (o.weight ? o.weight + ' ' : '') + (o.size || 10) + 'px ' + (o.font || FONT);
        g.fillStyle = o.color || '#2c2c2c';
        g.textAlign = o.align || 'center';
        g.textBaseline = o.baseline || 'alphabetic';
        if (o.alpha != null) g.globalAlpha = o.alpha;
        g.fillText(str, x, y);
        g.restore();
    }

    // Пунктир, который невозможно забыть сбросить.
    function dashed(g, pattern, fn) {
        g.save();
        g.setLineDash(pattern || [3, 3]);
        fn(g);
        g.restore();
    }
    function alpha(g, a, fn) {
        g.save(); g.globalAlpha = a; fn(g); g.restore();
    }

    // ── масштаб мир→экран ──────────────────────────────────────────
    // Было девять вариантов SX/PX/px в моделях. Возвращает функцию с обратным преобразованием.
    function scale(o) {
        var lo = o.min, hi = o.max, a = o.from, b = o.to;
        var span = (hi - lo) || 1;
        function f(v) { return a + (v - lo) / span * (b - a); }
        f.inv = function (px) { return lo + (px - a) / ((b - a) || 1) * span; };
        f.k = (b - a) / span;
        return f;
    }

    // ── вектор со стрелкой ─────────────────────────────────────────
    // Обобщение восьми реализаций: работает в любом направлении, умеет подпись и ограничение
    // длины (чтобы стрелка силы не улетала за сцену при крупном значении).
    // head    — длина наконечника, headW — половина его ширины,
    // shorten — насколько укоротить древко под наконечник (0 = древко до самого острия),
    // max     — ограничение длины (чтобы вектор силы не улетал за сцену).
    // Разные модели рисовали стрелку по-разному; параметры покрывают эти различия,
    // поэтому один блок заменяет все прежние варианты.
    function arrow(g, x, y, dx, dy, o) {
        o = o || {};
        var len = Math.hypot(dx, dy);
        if (o.max && len > o.max) { var s = o.max / len; dx *= s; dy *= s; len = o.max; }
        if (len < (o.min != null ? o.min : 0.6)) return;   // нулевой вектор не рисуем
        var ux = dx / len, uy = dy / len;
        var x2 = x + dx, y2 = y + dy;
        var head = o.head || 7, headW = o.headW != null ? o.headW : head * 0.5;
        var shorten = o.shorten != null ? o.shorten : head * 0.6;
        var col = o.color || palette.primary;
        g.save();
        g.strokeStyle = col; g.fillStyle = col;
        g.lineWidth = o.width || 2; g.lineCap = o.cap || 'round';
        g.beginPath(); g.moveTo(x, y); g.lineTo(x2 - ux * shorten, y2 - uy * shorten); g.stroke();
        // наконечник — треугольник вдоль направления
        g.beginPath();
        g.moveTo(x2, y2);
        g.lineTo(x2 - ux * head - uy * headW, y2 - uy * head + ux * headW);
        g.lineTo(x2 - ux * head + uy * headW, y2 - uy * head - ux * headW);
        g.closePath(); g.fill();
        g.restore();
        if (o.label) {
            var gap = o.labelGap != null ? o.labelGap : 10;
            // labelMid — подпись над серединой вектора (так подписаны силы), иначе у острия
            var ax = o.labelMid ? x + dx / 2 : x2 + ux * gap;
            var ay = o.labelMid ? y + dy / 2 : y2 + uy * gap;
            text(g, o.label, ax + (o.labelDx || 0), ay + (o.labelDy != null ? o.labelDy : (Math.abs(uy) < 0.4 ? 4 : 0)), {
                size: o.labelSize || 10, color: o.labelColor || col,
                weight: o.labelWeight != null ? o.labelWeight : '600',
                align: o.labelAlign || 'center'
            });
        }
    }

    // ── линии и кривые ─────────────────────────────────────────────
    function polyline(g, pts, o) {
        o = o || {};
        if (!pts || pts.length < 2) return;
        g.save();
        g.strokeStyle = o.color || palette.primary;
        g.lineWidth = o.width || 2;
        if (o.alpha != null) g.globalAlpha = o.alpha;
        if (o.dash) g.setLineDash(o.dash);
        g.beginPath();
        for (var i = 0; i < pts.length; i++) {
            var p = pts[i];
            if (p == null) { g.stroke(); g.beginPath(); continue; }   // разрыв кривой
            var px = p.x != null ? p.x : p[0], py = p.y != null ? p.y : p[1];
            if (i === 0) g.moveTo(px, py); else g.lineTo(px, py);
        }
        g.stroke(); g.restore();
    }

    // Кривая по функции: сэмплинг + отрисовка. fn(u) -> {x,y} | null (null рвёт линию).
    function curve(g, o) {
        var n = o.samples || 120, pts = [];
        for (var i = 0; i <= n; i++) {
            var u = o.from + (o.to - o.from) * i / n;
            var p = o.fn(u);
            pts.push(p && isFinite(p.x) && isFinite(p.y) ? p : null);
        }
        polyline(g, pts, o);
    }

    // След/траектория: старые точки бледнее свежих.
    function trail(g, pts, o) {
        o = o || {};
        polyline(g, pts, { color: o.color || palette.blue, width: o.width || 1.5, alpha: o.alpha != null ? o.alpha : 0.55 });
    }

    // ── частицы ────────────────────────────────────────────────────
    // Шаг отскока в безразмерной коробке 0..1. Модель хранит {x,y,vx,vy}, kit двигает.
    function bounce(p, dt, o) {
        o = o || {};
        var lo = o.min || 0, hi = o.max != null ? o.max : 1;
        p.x += p.vx * dt; p.y += p.vy * dt;
        if (p.x < lo) { p.x = lo; p.vx = Math.abs(p.vx); }
        if (p.x > hi) { p.x = hi; p.vx = -Math.abs(p.vx); }
        if (p.y < lo) { p.y = lo; p.vy = Math.abs(p.vy); }
        if (p.y > hi) { p.y = hi; p.vy = -Math.abs(p.vy); }
        return p;
    }
    // color/r/alpha могут быть функциями частицы — так цвет показывает скорость,
    // а прозрачность гасит улетевшие молекулы.
    function particles(g, list, o) {
        o = o || {};
        var r = o.r || 2.8;
        g.save();
        if (o.stroke) g.lineWidth = o.width || 1;
        for (var i = 0; i < list.length; i++) {
            var p = list[i];
            var c = typeof o.color === 'function' ? o.color(p, i) : (o.color || palette.blue);
            if (o.stroke) g.strokeStyle = c; else g.fillStyle = c;
            if (o.alpha != null) g.globalAlpha = typeof o.alpha === 'function' ? o.alpha(p, i) : o.alpha;
            g.beginPath();
            g.arc(o.toX ? o.toX(p) : p.x, o.toY ? o.toY(p) : p.y, typeof r === 'function' ? r(p, i) : r, 0, 6.2832);
            if (o.stroke) g.stroke(); else g.fill();
        }
        g.restore();
    }

    // ── тела ───────────────────────────────────────────────────────
    // Груз или шар: заливка полупрозрачная, обводка плотная, подпись массы внутри.
    // Так выглядели newton/oscillator/resonance/collision — теперь одинаково.
    // x,y — ЦЕНТР тела. Прямоугольник может быть неквадратным (w/h), например тележка.
    function body(g, x, y, o) {
        o = o || {};
        var col = o.color || palette.primary;
        var size = o.size || 24;
        var w = o.w != null ? o.w : size, h = o.h != null ? o.h : size;
        g.save();
        g.fillStyle = col; g.strokeStyle = col; g.lineWidth = o.width || 2;
        if (o.shape === 'ball') {
            alpha(g, o.fillAlpha != null ? o.fillAlpha : 0.22, function () {
                g.beginPath(); g.arc(x, y, size / 2, 0, 6.2832); g.fill();
            });
            g.beginPath(); g.arc(x, y, size / 2, 0, 6.2832); g.stroke();
        } else if (o.shape === 'dot') {
            // сплошной кружок без обводки — «материальная точка»
            g.beginPath(); g.arc(x, y, size / 2, 0, 6.2832); g.fill();
        } else {
            var x0 = x - w / 2, y0 = y - h / 2;
            alpha(g, o.fillAlpha != null ? o.fillAlpha : 0.22, function () { g.fillRect(x0, y0, w, h); });
            g.strokeRect(x0, y0, w, h);
        }
        g.restore();
        if (o.label) text(g, o.label, x, y + 4, { size: o.labelSize || 10, weight: '600', color: o.labelColor || '#2c2c2c' });
    }

    // ── шкалы-полоски ──────────────────────────────────────────────
    // Два режима: заполнение долей (frac) и раздел на две части (split) — покрывает
    // энергетические полоски осциллятора и шкалу энтропии.
    function bar(g, x, y, w, h, o) {
        o = o || {};
        g.save();
        if (o.split != null) {
            var f = Math.max(0, Math.min(1, o.split));
            g.fillStyle = o.colorA || palette.green; g.fillRect(x, y, w * f, h);
            g.fillStyle = o.colorB || palette.ochre; g.fillRect(x + w * f, y, w * (1 - f), h);
        } else {
            var fr = Math.max(0, Math.min(1, o.frac || 0));
            g.fillStyle = o.color || palette.primary; g.fillRect(x, y, w * fr, h);
        }
        g.strokeStyle = o.border || '#e2e2e2'; g.lineWidth = 1;
        g.strokeRect(x, y, w, h);
        g.restore();
        if (o.labelLeft) text(g, o.labelLeft, x - 6, y + h, { size: 9.5, color: o.labelColor || '#8a8a8a', align: 'right' });
        if (o.labelRight) text(g, o.labelRight, x + w + 6, y + h, { size: 9.5, color: o.labelColor || '#8a8a8a', align: 'left' });
    }

    // Знаковый бар от нулевой оси (энергии на орбите, вклады в энергию связи ядра).
    function signedBar(g, x, y0, w, value, o) {
        o = o || {};
        var h = value * (o.scale || 1);
        g.save();
        g.fillStyle = value >= 0 ? (o.pos || palette.green) : (o.neg || palette.red);
        g.fillRect(x, h >= 0 ? y0 - h : y0, w, Math.abs(h));
        g.restore();
        if (o.label) text(g, o.label, x + w / 2, y0 + (h >= 0 ? 12 : -Math.abs(h) - 5), { size: 9.5, color: o.labelColor || '#8a8a8a' });
    }

    // ── конструкции ────────────────────────────────────────────────
    // Сосуд: рамка со стенками; open — сторона без стенки (туда ходит поршень),
    // divider — пунктирная перегородка посередине (энтропия).
    function vessel(g, x, y, w, h, o) {
        o = o || {};
        g.save();
        g.strokeStyle = o.color || palette.primary; g.lineWidth = o.width || 2;
        g.beginPath();
        if (o.open !== 'left')   { g.moveTo(x, y); g.lineTo(x, y + h); }
        if (o.open !== 'right')  { g.moveTo(x + w, y); g.lineTo(x + w, y + h); }
        if (o.open !== 'top')    { g.moveTo(x, y); g.lineTo(x + w, y); }
        if (o.open !== 'bottom') { g.moveTo(x, y + h); g.lineTo(x + w, y + h); }
        g.stroke();
        g.restore();
        if (o.divider) {
            dashed(g, [4, 4], function () {
                g.strokeStyle = o.dividerColor || '#8a8a8a'; g.lineWidth = 1;
                g.beginPath(); g.moveTo(x + w / 2, y); g.lineTo(x + w / 2, y + h); g.stroke();
            });
        }
    }

    // Поршень со штоком (газ, двигатель — раньше копипаста).
    // rod — до какой координаты (от x) тянется шток; knob — ручка на конце:
    // 'fill' закрашенная, 'stroke' контурная, при knobAt можно отодвинуть её дальше штока.
    function piston(g, x, y, h, o) {
        o = o || {};
        var col = o.color || palette.primary;
        var th = o.thickness || 8, rod = o.rod || 54;
        g.save();
        g.fillStyle = col;
        g.fillRect(x, y - 2, th, h + 4);
        g.strokeStyle = col; g.lineWidth = o.rodWidth || 3;
        g.beginPath(); g.moveTo(x + th, y + h / 2); g.lineTo(x + rod, y + h / 2); g.stroke();
        if (o.knob) {
            var kx = x + (o.knobAt != null ? o.knobAt : rod), kr = o.knobR || 5;
            g.beginPath(); g.arc(kx, y + h / 2, kr, 0, 6.2832);
            if (o.knob === 'stroke') g.stroke(); else g.fill();
        }
        g.restore();
    }

    // Пружина зигзагом между двумя точками (осциллятор и резонанс — была копипаста).
    function spring(g, x1, x2, y, o) {
        o = o || {};
        var coils = o.coils || 8, amp = o.amp || 10;
        g.save();
        g.strokeStyle = o.color || palette.primary; g.lineWidth = o.width || 2;
        g.beginPath(); g.moveTo(x1, y);
        for (var c = 1; c <= coils; c++) {
            g.lineTo(x1 + (x2 - x1) * c / (coils + 0.5), y + (c % 2 ? -amp : amp));
        }
        g.lineTo(x2, y); g.stroke();
        g.restore();
    }

    // Стена-опора со штриховкой. dir: -1 штрихи влево (крепление слева), +1 вправо.
    // hatchH — высота зоны штриховки, если она короче самой стойки (у части стендов так и было).
    function wall(g, x, y, h, o) {
        o = o || {};
        var dir = o.dir || -1, step = o.step || 10, len = o.hatch || 7;
        var hh = o.hatchH != null ? o.hatchH : h;
        g.save();
        g.strokeStyle = o.color || '#8a8a8a';
        g.lineWidth = 2;
        g.beginPath(); g.moveTo(x, y - h / 2); g.lineTo(x, y + h / 2); g.stroke();
        g.lineWidth = 1;
        for (var d = -hh / 2; d < hh / 2; d += step) {
            g.beginPath(); g.moveTo(x, y + d); g.lineTo(x + dir * len, y + d + len); g.stroke();
        }
        g.restore();
    }

    // Пол со штриховкой (горизонтальный вариант стены).
    // alpha применяется только к штрихам — так шероховатость показывает трение,
    // не приглушая саму линию пола.
    function ground(g, x1, x2, y, o) {
        o = o || {};
        var step = o.step || 12, dx = o.hatch || 6, dy = o.hatchDy != null ? o.hatchDy : dx;
        g.save();
        g.strokeStyle = o.color || '#8a8a8a';
        g.lineWidth = o.width || 1.5;
        g.beginPath(); g.moveTo(x1, y); g.lineTo(x2, y); g.stroke();
        g.lineWidth = o.hatchWidth || 1;
        if (o.alpha != null) g.globalAlpha = o.alpha;
        for (var x = x1; x < x2; x += step) {
            g.beginPath(); g.moveTo(x, y); g.lineTo(x - dx, y + dy); g.stroke();
        }
        g.restore();
    }

    // Базовая линия/ось с делениями и подписями.
    function axis(g, x1, x2, y, o) {
        o = o || {};
        g.save();
        g.strokeStyle = o.color || '#e2e2e2'; g.lineWidth = 1;
        g.beginPath(); g.moveTo(x1, y); g.lineTo(x2, y); g.stroke();
        g.restore();
        if (o.ticks) {
            var ts = o.tickSize || 3;
            for (var i = 0; i <= o.ticks; i++) {
                var tx = x1 + (x2 - x1) * i / o.ticks;
                g.save();
                g.strokeStyle = o.tickColor || o.color || '#e2e2e2'; g.lineWidth = 1;
                g.beginPath(); g.moveTo(tx, y - ts); g.lineTo(tx, y + ts); g.stroke();
                g.restore();
                if (o.tickLabel) text(g, o.tickLabel(i, tx), tx, y + (o.labelDy || 15), { size: o.labelSize || 9.5, color: o.labelColor || '#8a8a8a' });
            }
        }
    }

    // Выноска: пунктирная вертикаль с подписью — «здесь старт», «здесь равновесие».
    function marker(g, x, y1, y2, o) {
        o = o || {};
        dashed(g, o.dash || [2, 4], function () {
            g.strokeStyle = o.color || '#e2e2e2'; g.lineWidth = 1;
            g.beginPath(); g.moveTo(x, y1); g.lineTo(x, y2); g.stroke();
        });
        if (o.label) text(g, o.label, x, (o.labelY != null ? o.labelY : y1 - 5), { size: 9.5, color: o.labelColor || '#8a8a8a' });
    }

    // ── приборы ────────────────────────────────────────────────────
    // Круглый манометр: цветные зоны, риски, стрелка с тенью, крупное число.
    // fmt — форматирование значения (обычно из B42Units), чтобы прибор жил в выбранных единицах.
    function gauge(g, cx, cy, r, value, max, label, col, fmt) {
        var frac = Math.max(0, Math.min(1, value / max));
        var A0 = Math.PI, A1 = 0;
        function ang(f) { return A0 + (A1 - A0) * f; }
        g.save();
        g.lineCap = 'butt';
        var zones = [[0, 0.45, palette.blue], [0.45, 0.75, palette.ok], [0.75, 1, palette.warm]];
        for (var z = 0; z < zones.length; z++) {
            g.strokeStyle = zones[z][2]; g.globalAlpha = 0.30; g.lineWidth = 9;
            g.beginPath(); g.arc(cx, cy, r, ang(zones[z][0]), ang(zones[z][1])); g.stroke();
        }
        g.globalAlpha = 1;
        g.strokeStyle = frac > 0.75 ? palette.warm : (frac > 0.45 ? palette.ok : palette.blue);
        g.lineWidth = 9; g.beginPath(); g.arc(cx, cy, r, ang(0), ang(frac)); g.stroke();
        g.strokeStyle = col.soft; g.lineWidth = 1.5; g.globalAlpha = 0.7;
        for (var i = 0; i <= 10; i++) {
            var a = ang(i / 10), r1 = r - 6, r2 = r - (i % 5 === 0 ? 13 : 9);
            g.beginPath();
            g.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
            g.lineTo(cx + Math.cos(a) * r2, cy + Math.sin(a) * r2);
            g.stroke();
        }
        g.globalAlpha = 1;
        var aa = ang(frac);
        g.save(); g.shadowColor = 'rgba(0,0,0,.35)'; g.shadowBlur = 4; g.shadowOffsetY = 1;
        g.strokeStyle = col.text; g.lineWidth = 2.5; g.lineCap = 'round';
        g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(aa) * (r - 15), cy + Math.sin(aa) * (r - 15)); g.stroke();
        g.restore();
        g.fillStyle = col.text; g.beginPath(); g.arc(cx, cy, 4, 0, 6.2832); g.fill();
        g.restore();
        text(g, label, cx, cy + 13, { size: 9.5, color: col.soft });
        text(g, fmt ? fmt(value) : String(Math.round(value)), cx, cy + 28, { size: 13, weight: '600', color: col.text });
    }

    // Термометр: столбик по доле шкалы + колба. mark — отметка (например, точка кипения).
    function thermometer(g, x, yTop, h, frac, o) {
        o = o || {};
        var col = o.color || palette.warm, wid = o.width || 6, bulbR = o.bulbR || 7;
        frac = Math.max(0, Math.min(1, frac));
        g.save();
        g.strokeStyle = o.track || '#e2e2e2';
        g.lineWidth = o.trackWidth || wid; g.lineCap = o.cap || 'round';
        g.beginPath(); g.moveTo(x, yTop); g.lineTo(x, yTop + h); g.stroke();
        g.strokeStyle = col; g.lineWidth = wid;
        g.beginPath(); g.moveTo(x, yTop + h); g.lineTo(x, yTop + h * (1 - frac)); g.stroke();
        g.fillStyle = col;
        g.beginPath(); g.arc(x, yTop + h + (o.bulbGap != null ? o.bulbGap : 6), bulbR, 0, 6.2832); g.fill();
        g.restore();
        if (o.mark != null) {
            var my = yTop + h * (1 - Math.max(0, Math.min(1, o.mark)));
            dashed(g, [3, 3], function () {
                g.strokeStyle = o.markColor || '#8a8a8a'; g.lineWidth = 1;
                g.beginPath(); g.moveTo(x - 12, my); g.lineTo(x + 12, my); g.stroke();
            });
        }
        if (o.label) text(g, o.label, x + (o.labelSide || 14), yTop + h * (1 - frac) + 4, { size: 10, weight: '600', color: col, align: 'left' });
    }

    // Вспышка удара — короткие лучи из точки контакта: от радиуса inner до r.
    function flash(g, x, y, r, o) {
        o = o || {};
        var n = o.rays || 8, inner = o.inner != null ? o.inner : r * 0.5;
        g.save();
        g.strokeStyle = o.color || palette.warm;
        g.lineWidth = o.width || 2; g.lineCap = o.cap || 'round';
        if (o.alpha != null) g.globalAlpha = o.alpha;
        for (var i = 0; i < n; i++) {
            var a = i * 2 * Math.PI / n;
            g.beginPath();
            g.moveTo(x + Math.cos(a) * inner, y + Math.sin(a) * inner);
            g.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
            g.stroke();
        }
        g.restore();
    }

    // Сетка векторов поля: двойной цикл + произвольный рисовальщик в узле.
    function fieldGrid(g, o, fn) {
        for (var x = o.x1; x <= o.x2; x += o.step) {
            for (var y = o.y1; y <= o.y2; y += (o.stepY || o.step)) fn(x, y);
        }
    }

    // ── приборная надпись в углу сцены ─────────────────────────────
    // Была в 12 моделях копипастой с разъезжающимися размерами. Теперь один вид:
    // заголовок цветом объекта, строки — мелко и приглушённо.
    // Строка может быть текстом или объектом {text, y, size, weight, color} — модели вели этот
    // блок каждая по-своему (шрифты разъехались), объектная форма позволяет переносить их
    // один в один, а потом свести к общему виду осознанно, а не случайно.
    function readout(g, lines, o) {
        o = o || {};
        var x = o.x != null ? o.x : 12, y0 = o.y != null ? o.y : 18;
        var step = o.step || 16;
        var align = o.align || 'left';
        for (var i = 0; i < lines.length; i++) {
            var ln = lines[i];
            if (ln == null) continue;
            if (typeof ln === 'string') ln = { text: ln };
            var head = (i === 0 && o.title !== false);
            text(g, ln.text, x, ln.y != null ? ln.y : y0 + i * step, {
                size: ln.size != null ? ln.size : (head ? (o.titleSize || 11.5) : (o.size || 10.5)),
                weight: ln.weight != null ? ln.weight : (head ? '600' : ''),
                color: ln.color || (head ? (o.titleColor || palette.primary) : (o.color || '#8a8a8a')),
                align: align
            });
        }
    }

    global.B42Kit = {
        palette: palette,
        text: text, dashed: dashed, alpha: alpha, scale: scale,
        arrow: arrow, polyline: polyline, curve: curve, trail: trail,
        bounce: bounce, particles: particles,
        body: body, bar: bar, signedBar: signedBar,
        vessel: vessel, piston: piston, spring: spring, wall: wall, ground: ground,
        axis: axis, marker: marker,
        gauge: gauge, thermometer: thermometer, flash: flash, fieldGrid: fieldGrid,
        readout: readout
    };
})(window);
