/* b42-mini — мини-граф на странице статьи, понятия и формулы.

   Владелец 27.08: «старый заменить нашим простым вариантом — он просто
   показывает структуру с точки зрения статьи с учётом её внутренних связей
   первого уровня» и «продумай мобильный: объекты меньше, ограничение по
   количеству — заменяем граф на наш везде».

   ПРОСТОЙ ВАРИАНТ, без панелей и режимов: узлы статьи (её понятия и формулы),
   рёбра — только МЕЖДУ НИМИ (первый уровень, ничего чужого не подмешиваем),
   мощность = число общих статей. Наведение — имя и класс, клик — страница
   понятия, «весь граф →» уводит в большое приложение на этом же фокусе.

   Рисует ядро js/b42-graph-core.js — тот же визуальный язык, что у большого
   графа: формы классов, цвета, штрихи, дуги-струны.

   Разметка:
     <div class="b42mini" data-ids="black_hole,event_horizon,f:kerr_metric"
          data-focus="black_hole"></div>
   Мобильный: сам режет число узлов и мельчит значки по ширине холста. */
(function () {
'use strict';

var boxes = document.querySelectorAll('.b42mini[data-ids]');
if (!boxes.length || !window.B42GraphCore) return;
var CORE = window.B42GraphCore;
var LANG = document.documentElement.lang || 'en';
var RU = LANG === 'ru';

CORE.data().then(function (G) {
    boxes.forEach(function (box) { init(box, G); });
});

function nodeName(n) { return (RU && n.ru) ? n.ru : n.en; }

function init(box, G) {
    var ids = (box.dataset.ids || '').split(',').filter(Boolean);
    var focus = box.dataset.focus || '';
    /* узлы: только те, что есть в графе */
    var idxs = [];
    ids.forEach(function (id) {
        var i = G.byId[id];
        if (i !== undefined && idxs.indexOf(i) < 0) idxs.push(i);
    });
    if (idxs.length < 2) { box.style.display = 'none'; return; }

    var canvas = document.createElement('canvas');
    canvas.className = 'b42mini-c';
    box.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    var TK = CORE.tokens();
    new MutationObserver(function () { TK = CORE.tokens(); }).observe(
        document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

    /* ПРЕДЕЛ ПО ЧИСЛУ — на телефоне меньше: узкий холст не вмещает больше
       десятка значков, а физика на 30 узлах в 320px превращается в кашу. */
    var W = box.clientWidth || 640;
    var CAP = W < 420 ? 10 : (W < 700 ? 16 : 24);
    if (idxs.length > CAP) {
        /* режем по важности: фокус всегда, дальше — по числу связей внутри набора */
        var inSet = {};
        idxs.forEach(function (i) { inSet[i] = 1; });
        idxs.sort(function (a, b) {
            if (G.nodes[a].id === focus) return -1;
            if (G.nodes[b].id === focus) return 1;
            var da = 0, db = 0;
            G.adj[a].forEach(function (p) { if (inSet[p[0]]) da += p[1]; });
            G.adj[b].forEach(function (p) { if (inSet[p[0]]) db += p[1]; });
            return db - da;
        });
        idxs = idxs.slice(0, CAP);
    }

    var pos = {};
    idxs.forEach(function (gi, i) { pos[gi] = i; });
    var nodes = idxs.map(function (gi, i) {
        var n = G.nodes[gi];
        return {gi: gi, id: n.id, label: nodeName(n), kind: n.kind, card: n.card,
                n: n.n, center: n.id === focus,
                size: 0, x: 0, y: 0, vx: 0, vy: 0};
    });
    /* рёбра ТОЛЬКО между своими — «внутренние связи первого уровня» */
    var edges = [], seen = {};
    idxs.forEach(function (gi) {
        G.adj[gi].forEach(function (p) {
            if (pos[p[0]] === undefined) return;
            var a = pos[gi], b = pos[p[0]];
            var k = Math.min(a, b) + ':' + Math.max(a, b);
            if (!seen[k]) { seen[k] = 1; edges.push([a, b, p[1]]); }
        });
    });
    var wMax = 1;
    edges.forEach(function (e) { if (e[2] > wMax) wMax = e[2]; });

    /* размеры значков: от холста и числа узлов — на телефоне мельче */
    var scale = Math.max(0.42, Math.min(1, (W / 700) * (7 / Math.sqrt(nodes.length))));
    nodes.forEach(function (nd) {
        nd.size = (nd.center ? 11 : 8) * scale;
    });

    /* стартовая раскладка: фокус в центре, остальные кольцом */
    var R0 = 60;
    nodes.forEach(function (nd, i) {
        if (nd.center) { nd.x = 0; nd.y = 0; return; }
        var a = (i / nodes.length) * Math.PI * 2;
        nd.x = Math.cos(a) * R0; nd.y = Math.sin(a) * R0;
    });

    var hover = -1, alive = 260, mouse = {}, cam = {z: 1, px: 0, py: 0};

    function resize() {
        var w = box.clientWidth || 640;
        var h = w < 420 ? 190 : (w < 700 ? 220 : 260);
        canvas.width = w * devicePixelRatio;
        canvas.height = h * devicePixelRatio;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        alive = Math.max(alive, 120);
    }
    window.addEventListener('resize', resize);
    resize();

    function tick() {
        if (alive <= 0) return;
        alive--;
        var i, j, N = nodes.length;
        for (i = 0; i < N; i++) {
            for (j = i + 1; j < N; j++) {
                var dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y;
                var d2 = dx * dx + dy * dy + 30;
                var f = 2600 / d2, d = Math.sqrt(d2);
                dx /= d; dy /= d;
                nodes[i].vx -= dx * f; nodes[i].vy -= dy * f;
                nodes[j].vx += dx * f; nodes[j].vy += dy * f;
            }
        }
        edges.forEach(function (e) {
            var a = nodes[e[0]], b = nodes[e[1]];
            var dx = b.x - a.x, dy = b.y - a.y;
            var d = Math.sqrt(dx * dx + dy * dy) + 0.01;
            var target = 76 / (1 + Math.log(1 + e[2]) * 0.4);
            var f = (d - target) * 0.0012 * Math.min(d, 200);
            if (f > 6) f = 6; else if (f < -6) f = -6;
            dx /= d; dy /= d;
            a.vx += dx * f; a.vy += dy * f;
            b.vx -= dx * f; b.vy -= dy * f;
        });
        var tot = 0;
        for (i = 0; i < N; i++) {
            var nd = nodes[i];
            /* фокус держим у центра — картинка «с точки зрения статьи/понятия» */
            var pull = nd.center ? 0.06 : 0.0022;
            nd.vx = (nd.vx - nd.x * pull) * 0.84;
            nd.vy = (nd.vy - nd.y * pull) * 0.84;
            var sp = Math.hypot(nd.vx, nd.vy);
            if (sp > 18) { nd.vx *= 18 / sp; nd.vy *= 18 / sp; }
            nd.x += nd.vx; nd.y += nd.vy;
            tot += sp;
        }
        if (tot / N < 0.05) alive = Math.min(alive, 4);
        fit();
    }

    function fit() {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
        nodes.forEach(function (nd) {
            if (nd.x < minX) minX = nd.x;
            if (nd.x > maxX) maxX = nd.x;
            if (nd.y < minY) minY = nd.y;
            if (nd.y > maxY) maxY = nd.y;
        });
        var pad = w < 420 ? 74 : 62;    // поле под подписи снизу и по бокам
        var z = Math.min((w - pad) / Math.max(60, maxX - minX),
                         (h - pad) / Math.max(60, maxY - minY));
        cam.z += (Math.max(0.3, Math.min(1.6, z)) - cam.z) * 0.12;
        cam.px += (-(minX + maxX) / 2 - cam.px) * 0.12;
        cam.py += (-(minY + maxY) / 2 - cam.py) * 0.12;
    }

    function P(nd) {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        return [w / 2 + (nd.x + cam.px) * cam.z, h / 2 + (nd.y + cam.py) * cam.z];
    }

    function draw() {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
        ctx.clearRect(0, 0, w, h);
        var pts = nodes.map(P);
        var nbr = {};
        if (hover >= 0) {
            edges.forEach(function (e) {
                if (e[0] === hover) nbr[e[1]] = 1;
                if (e[1] === hover) nbr[e[0]] = 1;
            });
        }
        /* струны */
        edges.forEach(function (e) {
            var hot = hover >= 0 && (e[0] === hover || e[1] === hover);
            var dim = hover >= 0 && !hot;
            var wgt = Math.log(1 + e[2]) / Math.log(1 + wMax);
            ctx.strokeStyle = hot ? TK.cyan : TK.muted;
            ctx.globalAlpha = dim ? 0.07 : (hot ? 0.75 : 0.12 + wgt * 0.38);
            ctx.lineWidth = 0.4 + wgt * 2;
            ctx.beginPath(); CORE.edgePath(ctx, pts[e[0]], pts[e[1]]); ctx.stroke();
        });
        ctx.globalAlpha = 1;
        /* узлы и подписи с анти-коллизией */
        var taken = [];
        nodes.forEach(function (nd, i) {
            var p = pts[i], r = Math.max(2.5, nd.size * cam.z);
            var hot = i === hover;
            var dim = hover >= 0 && !hot && !nbr[i];
            CORE.drawNodeIcon(ctx, TK, p[0], p[1], r, CORE.styleOf(nd.kind),
                              dim ? 0.25 : 1, hot || nd.center);
        });
        var order = nodes.map(function (_, i) { return i; }).sort(function (a, b) {
            var pa = (a === hover ? 1e9 : 0) + (nodes[a].center ? 1e6 : 0) + nodes[a].n;
            var pb = (b === hover ? 1e9 : 0) + (nodes[b].center ? 1e6 : 0) + nodes[b].n;
            return pb - pa;
        });
        order.forEach(function (i) {
            var nd = nodes[i], p = pts[i], r = Math.max(2.5, nd.size * cam.z);
            var hot = i === hover;
            var dim = hover >= 0 && !hot && !nbr[i];
            if (dim) return;
            /* на узком холсте подписи короче и мельче — иначе лезут за край */
            var narrow = w < 420;
            var fs = (hot || nd.center ? 10.5 : 9) * (narrow ? 0.92 : 1);
            ctx.font = (hot || nd.center ? '600 ' : '') + fs + 'px ' + TK.mono;
            var lim = narrow ? 14 : 24;
            var text = nd.label.length > lim ? nd.label.slice(0, lim - 1) + '…' : nd.label;
            var tw = ctx.measureText(text).width;
            /* не рисуем то, что вышло бы за холст: обрезка по краю читается как брак */
            if (p[0] - tw / 2 < 3 || p[0] + tw / 2 > w - 3) return;
            if (p[1] + r + fs + 3 > h) return;
            var bx = [p[0] - tw / 2 - 2, p[1] + r + 2, tw + 4, fs + 3];
            for (var t = 0; t < taken.length; t++) {
                var B = taken[t];
                if (bx[0] < B[0] + B[2] && bx[0] + bx[2] > B[0] &&
                    bx[1] < B[1] + B[3] && bx[1] + bx[3] > B[1]) return;
            }
            taken.push(bx);
            ctx.fillStyle = hot ? TK.cyan : (nd.center ? TK.text : TK.muted);
            ctx.globalAlpha = hot || nd.center ? 1 : 0.8;
            ctx.textAlign = 'center';
            ctx.fillText(text, p[0], p[1] + r + fs + 1);
            ctx.globalAlpha = 1;
        });
        /* подсказка у курсора */
        if (hover >= 0 && mouse.x !== undefined) {
            var hd = nodes[hover];
            var lines = [hd.label,
                         hd.kind + ' · ' + hd.n + (RU ? ' статей' : ' articles')];
            ctx.font = '10.5px ' + TK.mono;
            var tww = 0;
            lines.forEach(function (s) { tww = Math.max(tww, ctx.measureText(s).width); });
            var tx = Math.min(mouse.x + 12, w - tww - 16);
            var ty = Math.min(mouse.y + 4, h - 34);
            ctx.globalAlpha = 0.95;
            ctx.fillStyle = TK.surface; ctx.strokeStyle = TK.hair;
            ctx.beginPath(); ctx.roundRect(tx - 6, ty - 12, tww + 12, 32, 5);
            ctx.fill(); ctx.stroke();
            ctx.globalAlpha = 1;
            ctx.textAlign = 'start';
            lines.forEach(function (s, li) {
                ctx.font = (li ? '10px ' : '600 10.5px ') + TK.mono;
                ctx.fillStyle = li ? TK.soft : TK.text;
                ctx.fillText(s, tx, ty + li * 13);
            });
        }
        box._pts = pts;
    }

    function loop() { tick(); draw(); requestAnimationFrame(loop); }

    function pick(mx, my) {
        if (!box._pts) return -1;
        var best = -1, bd = 1e9;
        box._pts.forEach(function (p, i) {
            var d = Math.hypot(p[0] - mx, p[1] - my);
            var r = Math.max(10, nodes[i].size * cam.z + 7);
            if (d < r && d < bd) { best = i; bd = d; }
        });
        return best;
    }
    canvas.addEventListener('mousemove', function (e) {
        mouse.x = e.offsetX; mouse.y = e.offsetY;
        var h = pick(e.offsetX, e.offsetY);
        if (h !== hover) { hover = h; canvas.style.cursor = h >= 0 ? 'pointer' : ''; }
    });
    canvas.addEventListener('mouseleave', function () { hover = -1; });
    canvas.addEventListener('click', function (e) {
        var i = pick(e.offsetX, e.offsetY);
        if (i < 0) return;
        var nd = nodes[i];
        location.href = nd.kind === 'formula'
            ? '/lang/' + LANG + '/formula/' + nd.id.slice(2) + '.html'
            : '/lang/' + LANG + '/concepts/' + nd.id + '.html';
    });
    /* тап на телефоне: первый — показать подпись, второй — перейти */
    canvas.addEventListener('touchstart', function (e) {
        var t = e.touches[0], r = canvas.getBoundingClientRect();
        mouse.x = t.clientX - r.left; mouse.y = t.clientY - r.top;
        hover = pick(mouse.x, mouse.y);
    }, {passive: true});

    loop();
}
})();
