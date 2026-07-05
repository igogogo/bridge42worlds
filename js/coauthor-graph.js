(function () {
    var box = document.getElementById('cograph');
    var cv = document.getElementById('cgcanvas');
    if (!box || !cv) return;
    var me = box.dataset.author || '';
    if (!me) return;

    function slug(n) { return n.replace(/ /g, '_').replace(/\./g, ''); }
    var ctx = cv.getContext('2d'), W = 0, H = 0, dpr = Math.max(1, window.devicePixelRatio || 1);
    var txtCol = getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#2c2c2a';
    var authorCol = getComputedStyle(document.body).getPropertyValue('--author-color').trim() || '#8b5cf6';
    var nodes = [], links = [], adj = [], alpha = 1, drag = -1, hover = -1, px = 0, py = 0, ready = false, down = null;

    function resize() { var r = cv.getBoundingClientRect(); W = r.width; H = r.height || 340; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }

    fetch('/data/authors-graph.json').then(function (r) { return r.json(); }).then(function (g) {
        var mine = g[me];
        if (!mine) { box.style.display = 'none'; return; }
        var cos = (mine.coauthors || []).slice(0, 24);
        if (!cos.length) { box.style.display = 'none'; return; }
        var idx = {};
        function add(name, center) { idx[name] = nodes.length; nodes.push({ name: name, center: center, x: W / 2 + (Math.random() - 0.5) * 200, y: H / 2 + (Math.random() - 0.5) * 200, vx: 0, vy: 0, r: center ? 9 : 5 }); }
        add(me, true);
        cos.forEach(function (c) { add(c, false); });
        cos.forEach(function (c) { links.push([idx[me], idx[c]]); });
        // рёбра между соавторами, если они тоже соавторы друг друга
        cos.forEach(function (a) {
            var ga = g[a]; if (!ga) return;
            (ga.coauthors || []).forEach(function (b) {
                if (idx[b] !== undefined && b !== me && a < b) links.push([idx[a], idx[b]]);
            });
        });
        adj = nodes.map(function () { return {}; });
        links.forEach(function (l) { adj[l[0]][l[1]] = 1; adj[l[1]][l[0]] = 1; });
        ready = true;
    }).catch(function () { box.style.display = 'none'; });

    function step() {
        var cx = W / 2, cy = H / 2;
        for (var i = 0; i < nodes.length; i++) {
            var a = nodes[i];
            for (var j = i + 1; j < nodes.length; j++) {
                var b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy || 0.01;
                if (d2 < 90000) { var d = Math.sqrt(d2), f = 1400 / d2 / d; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f; }
            }
            a.vx += (cx - a.x) * (a.center ? 0.02 : 0.004); a.vy += (cy - a.y) * (a.center ? 0.02 : 0.006);
        }
        links.forEach(function (l) { var a = nodes[l[0]], b = nodes[l[1]], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 0.01, f = (d - 70) * 0.02 / d; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f; });
        for (var k = 0; k < nodes.length; k++) { var n = nodes[k]; if (k === drag) { n.x = px; n.y = py; n.vx = n.vy = 0; continue; } n.vx *= 0.86; n.vy *= 0.86; n.x += n.vx * alpha; n.y += n.vy * alpha; var m = 22 + n.r; n.x = Math.max(m, Math.min(W - m, n.x)); n.y = Math.max(m, Math.min(H - m, n.y)); }
        if (alpha > 0.05) alpha *= 0.99;
    }
    function draw() {
        ctx.clearRect(0, 0, W, H); ctx.lineWidth = 1;
        links.forEach(function (l) { var a = nodes[l[0]], b = nodes[l[1]], hot = hover >= 0 && (l[0] === hover || l[1] === hover); ctx.strokeStyle = hot ? 'rgba(139,92,246,0.5)' : 'rgba(140,140,140,0.18)'; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); });
        for (var i = 0; i < nodes.length; i++) { var a = nodes[i], dim = hover >= 0 && i !== hover && !adj[hover][i] && i !== 0; ctx.globalAlpha = dim ? 0.3 : 1; ctx.fillStyle = a.center ? '#b31b1b' : authorCol; ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 7); ctx.fill(); }
        ctx.globalAlpha = 1; ctx.font = '11px sans-serif'; ctx.textAlign = 'center'; ctx.fillStyle = txtCol;
        for (var j = 0; j < nodes.length; j++) { var n = nodes[j]; if (n.center || j === hover || adj[hover] && adj[hover][j]) { ctx.globalAlpha = 1; } else { ctx.globalAlpha = 0.5; } ctx.fillText(n.name.length > 22 ? n.name.slice(0, 21) + '…' : n.name, n.x, n.y - n.r - 3); }
        ctx.globalAlpha = 1;
    }
    function loop() { if (ready) { step(); draw(); } requestAnimationFrame(loop); }
    function pos(e) { var r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
    function pick(x, y) { var bi = -1, bd = 1e9; for (var i = 0; i < nodes.length; i++) { var a = nodes[i], d = Math.hypot(a.x - x, a.y - y); if (d < a.r + 8 && d < bd) { bd = d; bi = i; } } return bi; }
    cv.addEventListener('pointerdown', function (e) { var p = pos(e), i = pick(p[0], p[1]); down = p; if (i >= 0) { drag = i; px = p[0]; py = p[1]; alpha = Math.max(alpha, 0.5); cv.setPointerCapture(e.pointerId); } });
    cv.addEventListener('pointermove', function (e) { var p = pos(e); if (drag >= 0) { px = p[0]; py = p[1]; } else { hover = pick(p[0], p[1]); cv.style.cursor = hover >= 0 ? 'pointer' : 'grab'; } });
    cv.addEventListener('pointerup', function (e) { var p = pos(e), moved = down && (Math.abs(p[0] - down[0]) + Math.abs(p[1] - down[1]) > 6), i = pick(p[0], p[1]); if (!moved && i > 0) window.location.href = slug(nodes[i].name) + '.html'; drag = -1; down = null; });
    window.__cographResize = resize; resize(); loop();
})();
