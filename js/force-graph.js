// Общий движок force-графа для облаков тегов / учёных / законов.
// Различия (данные, цвета, полые ли узлы, подписи, куда ведёт клик) — в конфиге opts.
// opts: {
//   canvas: id, resizeKey: 'window.__xResize',
//   build: (lang) => Promise<{nodes:[{id,name,...}], links:[[i,j],...]}>,
//   radius: (node) => number,           // node.deg уже проставлен
//   color:  (node) => cssColor,
//   hollow: (node) => bool,             // полое кольцо (вторичные узлы) vs сплошной
//   labelAlways: (node) => bool,        // показывать подпись всегда (не только на ховере/deg>=3)
//   href:   (node, lang) => url|null    // куда вести по клику
//   tooltip: (node) => string|null      // необязательно: текст всплывающей подсказки при наведении
// }
window.createForceGraph = function (opts) {
    var cv = document.getElementById(opts.canvas);
    if (!cv) return;
    var pp = window.location.pathname.split('/'), li = pp.indexOf('lang');
    var lang = (li >= 0 && pp[li + 1]) ? pp[li + 1] : 'ru';

    var ctx = cv.getContext('2d'), W = 0, H = 0, dpr = Math.max(1, window.devicePixelRatio || 1);
    var txtCol = getComputedStyle(document.body).getPropertyValue('--text').trim() || '#2c2c2a';
    var nodes = [], links = [], adj = [], alpha = 1, drag = -1, hover = -1, px = 0, py = 0, downXY = null, ready = false;

    // Кнопка «развернуть на весь экран» — CSS-оверлей поверх текущего канваса (не Fullscreen API:
    // на iOS Safari поддержка нестабильна для произвольных элементов). Канвас всегда лежит прямо
    // в бордер-боксе графа (.mini-graph / #tag-graph / #kg-graph / ...), так что один обработчик
    // здесь в общем движке покрывает все графы сайта разом.
    var fsContainer = cv.parentElement, isFs = false;

    // Тултип при наведении на узел — один div на граф, позиционируется у курсора. Только
    // hover (десктоп); на тач-устройствах наведения нет, там как раньше — тап сразу ведёт по href.
    var tip = null;
    if (opts.tooltip && fsContainer) {
        tip = document.createElement('div');
        tip.className = 'graph-tooltip';
        fsContainer.appendChild(tip);
    }
    function showTip(node, x, y) {
        if (!tip) return;
        var text = opts.tooltip(node);
        if (!text) { tip.style.display = 'none'; return; }
        tip.textContent = text;
        tip.style.left = x + 'px'; tip.style.top = y + 'px';
        tip.style.display = 'block';
    }
    function hideTip() { if (tip) tip.style.display = 'none'; }

    if (fsContainer) {
        var fsBtn = document.createElement('button');
        fsBtn.type = 'button'; fsBtn.className = 'graph-fs-btn'; fsBtn.setAttribute('aria-label', 'fullscreen');
        fsBtn.textContent = '⛶';
        fsBtn.addEventListener('click', function (e) { e.stopPropagation(); setFs(!isFs); });
        fsContainer.appendChild(fsBtn);
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && isFs) setFs(false); });
    }
    function setFs(v) {
        isFs = v;
        fsContainer.classList.toggle('graph-fs-active', v);
        document.body.classList.toggle('graph-fs-open', v);
        fsBtn.textContent = v ? '✕' : '⛶';
        // resize() одного пересчёта W/H мало — авто-масштаб узлов в step() ограничен ×2.2 от
        // текущего разброса точек, скачок с компактного мини-графа на весь экран так не влезет.
        // restart() пересоздаёт позиции узлов уже в новых границах — граф сразу расправляется.
        restart();
    }

    function resize() {
        var r = cv.getBoundingClientRect(); W = r.width; H = r.height || 460;
        cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function _ingest(g) {
        nodes = g.nodes || []; links = g.links || [];
        nodes.forEach(function (n) { n.x = Math.random() * (W - 60) + 30; n.y = Math.random() * (H - 60) + 30; n.vx = 0; n.vy = 0; n.deg = 0; });
        links.forEach(function (l) { nodes[l[0]].deg++; nodes[l[1]].deg++; });
        nodes.forEach(function (n) { n.r = opts.radius(n); });
        adj = nodes.map(function () { return {}; });
        links.forEach(function (l) { adj[l[0]][l[1]] = 1; adj[l[1]][l[0]] = 1; });
        alpha = 1; hover = -1; drag = -1; ready = true;
    }

    function rebuild() {  // перестроить по новому фильтру (opts.build читает актуальное состояние)
        ready = false;
        opts.build(lang).then(_ingest);
    }

    opts.build(lang).then(_ingest);

    function step() {
        var cx = W / 2, cy = H / 2;
        for (var i = 0; i < nodes.length; i++) {
            var a = nodes[i];
            for (var j = i + 1; j < nodes.length; j++) {
                var b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy || 0.01;
                if (d2 < 62500) { var d = Math.sqrt(d2), f = 1500 / d2 / d; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f; }
            }
            a.vx += (cx - a.x) * 0.0026; a.vy += (cy - a.y) * 0.0045;
        }
        links.forEach(function (l) {
            var a = nodes[l[0]], b = nodes[l[1]], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 0.01, f = (d - 52) * 0.02 / d;
            a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
        });
        for (var k = 0; k < nodes.length; k++) {
            var n = nodes[k];
            if (k === drag) { n.x = px; n.y = py; n.vx = n.vy = 0; continue; }
            n.vx *= 0.85; n.vy *= 0.85; n.x += n.vx * alpha; n.y += n.vy * alpha;
            var m = 30 + n.r; n.x = Math.max(m, Math.min(W - m, n.x)); n.y = Math.max(m, Math.min(H - m, n.y));
        }
        // Мягкое вписывание облака в окно: масштабируем к ~85% канваса + центрируем,
        // чтобы граф не скучивался по центру, а занимал всё место (не трогаем во время драга).
        if (nodes.length > 1 && drag < 0) {
            var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
            for (var q = 0; q < nodes.length; q++) {
                var nq = nodes[q];
                if (nq.x < minx) minx = nq.x; if (nq.x > maxx) maxx = nq.x;
                if (nq.y < miny) miny = nq.y; if (nq.y > maxy) maxy = nq.y;
            }
            var mgn = 44, bw = (maxx - minx) || 1, bh = (maxy - miny) || 1;
            var s = Math.max(0.6, Math.min(Math.min((W - 2 * mgn) / bw, (H - 2 * mgn) / bh), 2.2));
            var ccx = (minx + maxx) / 2, ccy = (miny + maxy) / 2, ease = 0.06;
            for (var t = 0; t < nodes.length; t++) {
                var nt = nodes[t];
                nt.x += ((W / 2 + (nt.x - ccx) * s) - nt.x) * ease;
                nt.y += ((H / 2 + (nt.y - ccy) * s) - nt.y) * ease;
            }
        }
        if (alpha > 0.03) alpha *= 0.992;
    }

    function draw() {
        ctx.clearRect(0, 0, W, H); ctx.lineWidth = 1;
        links.forEach(function (l) {
            var a = nodes[l[0]], b = nodes[l[1]], hot = hover >= 0 && (l[0] === hover || l[1] === hover);
            ctx.strokeStyle = hot ? 'rgba(120,120,120,0.5)' : 'rgba(140,140,140,0.13)';
            if (l[2] === 'dashed') ctx.setLineDash([3, 3]); // напр. закон↔учёный «оказал влияние», не «открыл»
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
            if (l[2] === 'dashed') ctx.setLineDash([]);
        });
        for (var i = 0; i < nodes.length; i++) {
            var a = nodes[i], dim = hover >= 0 && i !== hover && !adj[hover][i], col = opts.color(a);
            ctx.globalAlpha = dim ? 0.22 : 1;
            ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 7);
            if (opts.hollow(a)) {
                ctx.globalAlpha = dim ? 0.15 : 0.5; ctx.fillStyle = col; ctx.fill();
                ctx.globalAlpha = dim ? 0.3 : 0.85; ctx.lineWidth = 1.3; ctx.strokeStyle = col; ctx.stroke(); ctx.lineWidth = 1;
            } else {
                ctx.fillStyle = col; ctx.fill();
            }
            if (i === hover) { ctx.globalAlpha = 1; ctx.lineWidth = 2; ctx.strokeStyle = txtCol; ctx.stroke(); ctx.lineWidth = 1; }
        }
        ctx.textAlign = 'center';
        for (var j = 0; j < nodes.length; j++) {
            var n = nodes[j], always = opts.labelAlways && opts.labelAlways(n);
            if (j === hover || always || n.deg >= 3) {
                var strong = j === hover || (hover >= 0 && adj[hover][j]);
                ctx.font = (always ? '10px' : '9px') + ' sans-serif';
                ctx.globalAlpha = strong ? 0.95 : (hover >= 0 ? 0.08 : (always ? 0.6 : 0.28));
                ctx.fillStyle = txtCol; ctx.fillText(n.name, n.x, n.y - n.r - 3);
            }
        }
        ctx.globalAlpha = 1;
    }

    function loop() { if (ready) { step(); draw(); } requestAnimationFrame(loop); }
    function pos(e) { var r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
    function pick(x, y) { var bi = -1, bd = 1e9; for (var i = 0; i < nodes.length; i++) { var a = nodes[i], d = Math.hypot(a.x - x, a.y - y); if (d < a.r + 6 && d < bd) { bd = d; bi = i; } } return bi; }
    cv.addEventListener('pointerdown', function (e) { var p = pos(e), i = pick(p[0], p[1]); downXY = p; if (i >= 0) { drag = i; px = p[0]; py = p[1]; alpha = Math.max(alpha, 0.5); cv.setPointerCapture(e.pointerId); } });
    cv.addEventListener('pointermove', function (e) {
        var p = pos(e);
        if (drag >= 0) { px = p[0]; py = p[1]; hideTip(); }
        else {
            hover = pick(p[0], p[1]);
            cv.style.cursor = hover >= 0 ? 'pointer' : 'grab';
            if (hover >= 0 && opts.tooltip) showTip(nodes[hover], p[0] + 14, p[1] + 14); else hideTip();
        }
    });
    cv.addEventListener('pointerleave', hideTip);
    cv.addEventListener('pointerup', function (e) {
        var p = pos(e), moved = downXY && (Math.abs(p[0] - downXY[0]) + Math.abs(p[1] - downXY[1]) > 6);
        var i = pick(p[0], p[1]);
        if (!moved && i >= 0) { var url = opts.href(nodes[i], lang); if (url) window.location.href = url; }
        drag = -1; downXY = null;
    });

    function restart() {
        resize();
        for (var i = 0; i < nodes.length; i++) {
            nodes[i].x = Math.random() * (W - 80) + 40; nodes[i].y = Math.random() * (H - 80) + 40;
            nodes[i].vx = nodes[i].vy = 0;
        }
        alpha = 1;
    }
    window[opts.resizeKey] = restart;
    if (opts.rebuildKey) window[opts.rebuildKey] = rebuild;
    resize(); loop();
};
