/* b42-graph — приложение-граф понятий, собственный движок без библиотек.

   Владелец 27.08: «разные значки, дриллдаун, панель навигации, 3D» и следом:
   «динамично: подсветка, объём, разные представления; группы и классы
   включать/выключать; панелька справа; информация, переходы; чтобы мигало,
   крутилось, вертелось — высший класс».

   УСТРОЙСТВО
   Кадры (никогда не всё облако): overview 50 групп → group (члены + мостики)
   → ego (понятие + соседи). Мощность ребра = ЧИСЛО ОБЩИХ СТАТЕЙ.
   Представления: force (живая физика) · ring (кольцо секторами) · sphere (3D).
   Панель справа: режимы 2D/3D/⟳, представление, порог мощности, классы
   (вкл/выкл по формам), группы (вкл/выкл), карточка выбранного с переходами.
   Динамика: плавные переходы кадров (tween по id), пульс выбранного, искры
   вдоль его рёбер, автовращение, туман глубины в 3D.

   Пока статикой на клиенте — «потренируемся»; в динамике кадры отдаст воркер. */
(function () {
'use strict';

var canvas = document.getElementById('b42g');
if (!canvas) return;
var ctx = canvas.getContext('2d');
var LANG = document.documentElement.lang || 'en';
var RU = LANG === 'ru';

/* ── токены бренда: граф живёт в теме сайта ── */
function tokens() {
    var cs = getComputedStyle(document.documentElement);
    function v(n, fb) { return (cs.getPropertyValue(n) || fb).trim() || fb; }
    return {text: v('--text', '#222'), muted: v('--muted', '#777'),
            soft: v('--soft', '#999'), hair: v('--hairline', '#ddd'),
            cyan: v('--cyan', '#0d7d8c'), link: v('--link', '#0d7d8c'),
            ochre: v('--ochre', '#b8860b'),
            bg: v('--bg', '#faf9f5'), surface: v('--surface', '#f4f2ec'),
            mono: v('--mono', 'ui-monospace, monospace')};
}
var TK = tokens();
new MutationObserver(function () { TK = tokens(); }).observe(
    document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

/* ── классы: форма + подпись ── */
var KINDS = [
    {k: 'law+', shapes: ['law', 'principle', 'theorem', 'equation'], sh: 'sq',
     ru: 'закон · принцип', en: 'law · principle'},
    {k: 'method+', shapes: ['method', 'process'], sh: 'di',
     ru: 'метод · процесс', en: 'method · process'},
    {k: 'phen+', shapes: ['phenomenon', 'effect'], sh: 'tr',
     ru: 'явление · эффект', en: 'phenomenon · effect'},
    {k: 'obj+', shapes: ['object', 'substance', 'structure'], sh: 'ring',
     ru: 'объект · вещество', en: 'object · substance'},
    {k: 'instr+', shapes: ['instrument', 'experiment'], sh: 'hex',
     ru: 'прибор', en: 'instrument'},
    {k: 'math', shapes: ['math'], sh: 'cross', ru: 'математика', en: 'math'},
    {k: 'units+', shapes: ['quantity', 'constant', 'unit', 'unit_system'],
     sh: 'pent', ru: 'величины · единицы', en: 'quantities · units'},
    {k: 'rest', shapes: [], sh: 'circle', ru: 'понятие', en: 'concept'},
];
var kindBucket = {};
KINDS.forEach(function (K) {
    K.shapes.forEach(function (s) { kindBucket[s] = K.k; });
});
function bucketOf(kind) { return kindBucket[kind] || 'rest'; }
function shapeOf(kind) {
    var b = bucketOf(kind);
    for (var i = 0; i < KINDS.length; i++) if (KINDS[i].k === b) return KINDS[i].sh;
    return 'circle';
}

/* ── данные ── */
var G = null, adj = null;
fetch('/data/concepts-graph.json').then(function (r) { return r.json(); })
    .then(function (d) {
        G = d;
        adj = d.nodes.map(function () { return []; });
        d.edges.forEach(function (e) {
            adj[e[0]].push([e[1], e[2]]);
            adj[e[1]].push([e[0], e[2]]);
        });
        buildPanel();
        showOverview();
    });
function nodeName(n) { return (RU && n.ru) ? n.ru : n.en; }
function groupLabel(g) { return (RU && g.label_ru) ? g.label_ru : g.label_en; }

/* ── состояние ── */
var frame = {mode: 'overview', nodes: [], edges: [], raw: null};
var view = {is3d: false, layout: 'force', spin: false, minW: 2,
            zoom: 1, panX: 0, panY: 0, rotX: -0.35, rotY: 0.5};
var kindOn = {};
KINDS.forEach(function (K) { kindOn[K.k] = true; });
var groupOn = null;         // null = все; иначе Set индексов групп
var trail = [];
var hoverI = -1, selI = -1;
var sim = {vx: [], vy: [], vz: [], alive: 0};
var sparks = [];            // искры по рёбрам выбранного
var T0 = performance.now();

/* ── фильтры кадра ── */
function nodeVisible(nd) {
    if (nd.kind !== '_group' && !kindOn[bucketOf(nd.kind)]) return false;
    if (groupOn && nd.g !== undefined && nd.g !== null &&
        nd.kind !== '_group' && !groupOn.has(nd.g)) return false;
    return true;
}

/* ── сборка кадров (переход: старые позиции по id переезжают) ── */
function setFrame(mode, nodes, edges) {
    var prev = {};
    frame.nodes.forEach(function (nd) {
        prev[nd.key] = [nd.x, nd.y, nd.z];
    });
    frame = {mode: mode, nodes: nodes, edges: edges};
    hoverI = -1;
    seedLayout(prev);
    renderCrumbs(); renderInfo();
}

function showOverview() {
    var nodes = G.groups.map(function (g, i) {
        var n = 0;
        g.members.forEach(function (m) { n += G.nodes[m].n; });
        return {key: 'g' + i, gi: i, label: groupLabel(g), n: n, kind: '_group',
                g: i, size: Math.max(10, Math.sqrt(n) * 1.1)};
    });
    var gw = {};
    G.edges.forEach(function (e) {
        var a = G.nodes[e[0]].g, b = G.nodes[e[1]].g;
        if (a === null || b === null || a === b) return;
        var k = Math.min(a, b) + ':' + Math.max(a, b);
        gw[k] = (gw[k] || 0) + e[2];
    });
    var edges = [];
    Object.keys(gw).forEach(function (k) {
        var p = k.split(':');
        if (gw[k] >= 4) edges.push([+p[0], +p[1], gw[k]]);
    });
    trail = [{mode: 'overview', label: RU ? 'Обзор' : 'Overview'}];
    selI = -1;
    setFrame('overview', nodes, edges);
}

function frameFromIds(ids, centerFirst) {
    var pos = {};
    ids.forEach(function (id, i) { pos[id] = i; });
    var nodes = ids.map(function (id, i) {
        var n = G.nodes[id];
        return {key: 'n' + id, ni: id, label: nodeName(n), n: n.n, kind: n.kind,
                g: n.g, center: centerFirst && i === 0,
                out: false,
                size: Math.max(5, Math.sqrt(n.n) * 2.2) *
                      (centerFirst && i === 0 ? 1.6 : 1)};
    });
    var edges = [], seen = {};
    ids.forEach(function (id) {
        adj[id].forEach(function (p) {
            if (pos[p[0]] === undefined) return;
            var a = pos[id], b = pos[p[0]];
            var k = Math.min(a, b) + ':' + Math.max(a, b);
            if (!seen[k]) { seen[k] = 1; edges.push([a, b, p[1]]); }
        });
    });
    return {nodes: nodes, edges: edges, pos: pos};
}

function showGroup(gi, pushCrumb) {
    var g = G.groups[gi];
    var inSet = {};
    g.members.forEach(function (m) { inSet[m] = 1; });
    var outside = {};
    g.members.forEach(function (m) {
        adj[m].forEach(function (p) {
            if (!inSet[p[0]]) outside[p[0]] = Math.max(outside[p[0]] || 0, p[1]);
        });
    });
    var bridges = Object.keys(outside)
        .map(function (k) { return [+k, outside[k]]; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 12);
    var ids = g.members.slice();
    bridges.forEach(function (b) { ids.push(b[0]); });
    var f = frameFromIds(ids);
    f.nodes.forEach(function (nd) { nd.out = !inSet[nd.ni]; });
    if (pushCrumb !== false) {
        trail = trail.filter(function (c) { return c.mode === 'overview'; });
        trail.push({mode: 'group', arg: gi, label: groupLabel(g)});
    }
    selI = -1;
    setFrame('group', f.nodes, f.edges);
}

function showEgo(ni, pushCrumb) {
    var ids = [ni];
    adj[ni].slice().sort(function (a, b) { return b[1] - a[1]; })
        .forEach(function (p) { if (ids.length < 80) ids.push(p[0]); });
    var f = frameFromIds(ids, true);
    if (pushCrumb !== false) {
        trail = trail.filter(function (c) { return c.mode !== 'ego'; });
        trail.push({mode: 'ego', arg: ni, label: nodeName(G.nodes[ni])});
    }
    setFrame('ego', f.nodes, f.edges);
    selI = 0;
    igniteSparks();
    renderInfo();
}

/* ── раскладки ── */
function seedLayout(prev) {
    var N = frame.nodes.length;
    for (var i = 0; i < N; i++) {
        var nd = frame.nodes[i];
        var p = prev && prev[nd.key];
        if (p) { nd.x = p[0]; nd.y = p[1]; nd.z = p[2]; }
        else {
            var a = (i / Math.max(1, N)) * Math.PI * 2 * 3.883;
            var r = 40 + 24 * Math.sqrt(i);
            nd.x = Math.cos(a) * r; nd.y = Math.sin(a) * r;
            nd.z = view.is3d ? (Math.random() - 0.5) * r : 0;
        }
        nd.tx = null;         // цель tween для фиксированных раскладок
    }
    sim.vx = new Array(N).fill(0);
    sim.vy = new Array(N).fill(0);
    sim.vz = new Array(N).fill(0);
    sim.alive = 260;
    if (view.layout !== 'force') applyFixedLayout();
}

function applyFixedLayout() {
    var vis = [];
    frame.nodes.forEach(function (nd, i) { if (nodeVisible(nd)) vis.push(i); });
    var N = vis.length || 1;
    if (view.layout === 'ring') {
        /* кольцо секторами: сортировка по группе, затем по классу — родня рядом */
        var order = vis.slice().sort(function (a, b) {
            var A = frame.nodes[a], B = frame.nodes[b];
            return (A.g - B.g) || (bucketOf(A.kind) < bucketOf(B.kind) ? -1 : 1);
        });
        var R = 60 + N * 3.1;
        order.forEach(function (idx, i) {
            var a = (i / N) * Math.PI * 2 - Math.PI / 2;
            var nd = frame.nodes[idx];
            nd.tx = [Math.cos(a) * R, Math.sin(a) * R, 0];
        });
    } else if (view.layout === 'sphere') {
        /* фибоначчиева сфера — «объём» */
        var R2 = 60 + N * 1.9;
        vis.forEach(function (idx, i) {
            var y = 1 - (i / Math.max(1, N - 1)) * 2;
            var rad = Math.sqrt(1 - y * y);
            var th = 2.39996 * i;
            var nd = frame.nodes[idx];
            nd.tx = [Math.cos(th) * rad * R2, y * R2, Math.sin(th) * rad * R2];
        });
        if (!view.is3d) set3d(true);
    }
    sim.alive = 260;
}

function tick() {
    if (sim.alive <= 0) return;
    sim.alive--;
    var n = frame.nodes, N = n.length, i, j;
    if (view.layout !== 'force') {
        /* tween к целям фиксированной раскладки */
        for (i = 0; i < N; i++) {
            if (!n[i].tx) continue;
            n[i].x += (n[i].tx[0] - n[i].x) * 0.14;
            n[i].y += (n[i].tx[1] - n[i].y) * 0.14;
            n[i].z += (n[i].tx[2] - n[i].z) * 0.14;
        }
        return;
    }
    var K = 1300;
    for (i = 0; i < N; i++) {
        if (!nodeVisible(n[i])) continue;
        for (j = i + 1; j < N; j++) {
            if (!nodeVisible(n[j])) continue;
            var dx = n[j].x - n[i].x, dy = n[j].y - n[i].y, dz = n[j].z - n[i].z;
            var d2 = dx * dx + dy * dy + dz * dz + 40;
            var f = K / d2, d = Math.sqrt(d2);
            dx /= d; dy /= d; dz /= d;
            sim.vx[i] -= dx * f; sim.vy[i] -= dy * f; sim.vz[i] -= dz * f;
            sim.vx[j] += dx * f; sim.vy[j] += dy * f; sim.vz[j] += dz * f;
        }
    }
    frame.edges.forEach(function (e) {
        if (e[2] < view.minW) return;
        var a = e[0], b = e[1];
        if (!nodeVisible(n[a]) || !nodeVisible(n[b])) return;
        var dx = n[b].x - n[a].x, dy = n[b].y - n[a].y, dz = n[b].z - n[a].z;
        var d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
        var target = 90 / Math.log(2 + e[2]);
        var f = (d - target) * 0.00024 * d;
        dx /= d; dy /= d; dz /= d;
        sim.vx[a] += dx * f; sim.vy[a] += dy * f; sim.vz[a] += dz * f;
        sim.vx[b] -= dx * f; sim.vy[b] -= dy * f; sim.vz[b] -= dz * f;
    });
    for (i = 0; i < N; i++) {
        sim.vx[i] = (sim.vx[i] - n[i].x * 0.003) * 0.85;
        sim.vy[i] = (sim.vy[i] - n[i].y * 0.003) * 0.85;
        sim.vz[i] = (sim.vz[i] - n[i].z * 0.003) * 0.85;
        n[i].x += sim.vx[i]; n[i].y += sim.vy[i];
        if (view.is3d) n[i].z += sim.vz[i]; else n[i].z = 0;
    }
}

/* ── проекция ── */
function project(nd) {
    var x = nd.x, y = nd.y, z = nd.z;
    if (view.is3d) {
        var cy = Math.cos(view.rotY), sy = Math.sin(view.rotY);
        var cx = Math.cos(view.rotX), sx = Math.sin(view.rotX);
        var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
        var y1 = y * cx + z1 * sx, z2 = -y * sx + z1 * cx;
        var p = 900 / (900 + z2);
        x = x1 * p; y = y1 * p; nd._depth = p;
    } else nd._depth = 1;
    var W = canvas.width / devicePixelRatio, H = canvas.height / devicePixelRatio;
    return [W / 2 + (x + view.panX) * view.zoom,
            H / 2 + (y + view.panY) * view.zoom];
}

/* ── формы ── */
function drawShape(x, y, r, shape) {
    ctx.beginPath();
    var i, a;
    if (shape === 'sq') ctx.rect(x - r * 0.85, y - r * 0.85, r * 1.7, r * 1.7);
    else if (shape === 'di') {
        ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r);
        ctx.lineTo(x - r, y); ctx.closePath();
    } else if (shape === 'tr') {
        ctx.moveTo(x, y - r); ctx.lineTo(x + r * 0.9, y + r * 0.7);
        ctx.lineTo(x - r * 0.9, y + r * 0.7); ctx.closePath();
    } else if (shape === 'hex') {
        for (i = 0; i < 6; i++) {
            a = Math.PI / 3 * i - Math.PI / 6;
            ctx[i ? 'lineTo' : 'moveTo'](x + r * Math.cos(a), y + r * Math.sin(a));
        }
        ctx.closePath();
    } else if (shape === 'pent') {
        for (i = 0; i < 5; i++) {
            a = Math.PI * 2 / 5 * i - Math.PI / 2;
            ctx[i ? 'lineTo' : 'moveTo'](x + r * Math.cos(a), y + r * Math.sin(a));
        }
        ctx.closePath();
    } else if (shape === 'cross') {
        var t = r * 0.38;
        ctx.rect(x - t, y - r, t * 2, r * 2); ctx.rect(x - r, y - t, r * 2, t * 2);
    } else ctx.arc(x, y, r, 0, Math.PI * 2);
}

/* ── искры вдоль рёбер выбранного (динамика «чтобы бежало») ── */
function igniteSparks() {
    sparks = [];
    if (selI < 0) return;
    frame.edges.forEach(function (e) {
        if (e[0] !== selI && e[1] !== selI) return;
        if (e[2] < view.minW) return;
        sparks.push({a: e[0], b: e[1], t: Math.random(),
                     sp: 0.004 + Math.min(0.012, e[2] * 0.0006)});
    });
}

/* ── отрисовка ── */
function neighborsOf(i) {
    var s = {};
    frame.edges.forEach(function (e) {
        if (e[2] < view.minW) return;
        if (e[0] === i) s[e[1]] = 1;
        if (e[1] === i) s[e[0]] = 1;
    });
    return s;
}

function draw() {
    var W = canvas.width / devicePixelRatio, H = canvas.height / devicePixelRatio;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var n = frame.nodes;
    if (!n.length) return;
    if (view.is3d && view.spin) view.rotY += 0.0035;
    var pts = n.map(project);
    var focusI = hoverI >= 0 ? hoverI : selI;
    var nbr = focusI >= 0 ? neighborsOf(focusI) : null;
    var now = performance.now();

    /* рёбра */
    frame.edges.forEach(function (e) {
        if (e[2] < view.minW) return;
        if (!nodeVisible(n[e[0]]) || !nodeVisible(n[e[1]])) return;
        var a = pts[e[0]], b = pts[e[1]];
        var hot = focusI >= 0 && (e[0] === focusI || e[1] === focusI);
        var dim = focusI >= 0 && !hot;
        var wgt = Math.min(1, Math.log(1 + e[2]) / Math.log(40));
        ctx.strokeStyle = hot ? TK.cyan : TK.hair;
        ctx.globalAlpha = dim ? 0.10 : (hot ? 0.95 : 0.35 + wgt * 0.5);
        ctx.lineWidth = (0.6 + wgt * 3.4) * (hot ? 1.25 : 1);
        if (n[e[0]].out || n[e[1]].out) ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
        ctx.stroke(); ctx.setLineDash([]);
    });
    ctx.globalAlpha = 1;

    /* искры */
    sparks.forEach(function (s) {
        if (!nodeVisible(n[s.a]) || !nodeVisible(n[s.b])) return;
        s.t += s.sp;
        if (s.t > 1) s.t = 0;
        var a = pts[s.a], b = pts[s.b];
        var x = a[0] + (b[0] - a[0]) * s.t, y = a[1] + (b[1] - a[1]) * s.t;
        ctx.beginPath(); ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = TK.ochre; ctx.globalAlpha = 0.9; ctx.fill();
    });
    ctx.globalAlpha = 1;

    /* узлы (в 3D — дальние первыми) */
    var order = [];
    n.forEach(function (nd, i) { if (nodeVisible(nd)) order.push(i); });
    if (view.is3d) order.sort(function (a, b) { return n[a]._depth - n[b]._depth; });
    order.forEach(function (i) {
        var p = pts[i], nd = n[i];
        var r = nd.size * view.zoom * (view.is3d ? nd._depth : 1);
        var hot = i === hoverI || i === selI;
        var dim = focusI >= 0 && !hot && !(nbr && nbr[i]);
        /* пульс выбранного — «чтобы мигало» */
        if (i === selI) {
            var ph = (now - T0) / 700;
            var pr = Math.max(3, r) + 6 + Math.sin(ph) * 3.5;
            ctx.beginPath(); ctx.arc(p[0], p[1], pr, 0, Math.PI * 2);
            ctx.strokeStyle = TK.cyan;
            ctx.globalAlpha = 0.5 + Math.sin(ph) * 0.25;
            ctx.lineWidth = 1.6; ctx.stroke();
        }
        ctx.globalAlpha = dim ? 0.22 :
            (view.is3d ? 0.35 + nd._depth * 0.65 : 1);
        drawShape(p[0], p[1], Math.max(3, r), shapeOf(nd.kind === '_group' ? '' : nd.kind));
        ctx.fillStyle = hot ? TK.cyan : TK.surface;
        ctx.fill();
        ctx.strokeStyle = hot ? TK.cyan : (nd.center ? TK.link :
                          nd.out ? TK.soft : TK.muted);
        ctx.lineWidth = hot || nd.center ? 2.2 : 1.1;
        ctx.stroke();
        if (hot || (nbr && nbr[i]) || r > 11 || view.zoom > 1.7 ||
            frame.mode === 'overview') {
            ctx.fillStyle = hot ? TK.cyan : (dim ? TK.soft : TK.text);
            ctx.font = (hot ? '600 ' : '') + '11px ' + TK.mono;
            ctx.textAlign = 'center';
            var label = nd.label.length > 28 ? nd.label.slice(0, 26) + '…' : nd.label;
            ctx.fillText(label, p[0], p[1] + Math.max(3, r) + 12);
        }
    });
    ctx.globalAlpha = 1;
    frame._pts = pts;
}

function loop() { tick(); draw(); requestAnimationFrame(loop); }

/* ── взаимодействие ── */
function pick(mx, my) {
    if (!frame._pts) return -1;
    var best = -1, bd = 20 * 20;
    frame._pts.forEach(function (p, i) {
        if (!nodeVisible(frame.nodes[i])) return;
        var dx = p[0] - mx, dy = p[1] - my, d = dx * dx + dy * dy;
        var r = Math.max(8, frame.nodes[i].size * view.zoom);
        if (d < Math.max(bd, r * r) && d < (r + 8) * (r + 8)) { best = i; bd = d; }
    });
    return best;
}
var drag = null;
canvas.addEventListener('mousedown', function (e) {
    drag = {x: e.offsetX, y: e.offsetY, moved: false};
});
window.addEventListener('mouseup', function () { drag = null; });
canvas.addEventListener('mousemove', function (e) {
    if (drag) {
        var dx = e.offsetX - drag.x, dy = e.offsetY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
        if (view.is3d) { view.rotY += dx * 0.008; view.rotX += dy * 0.008; }
        else { view.panX += dx / view.zoom; view.panY += dy / view.zoom; }
        drag.x = e.offsetX; drag.y = e.offsetY;
        return;
    }
    var h = pick(e.offsetX, e.offsetY);
    if (h !== hoverI) { hoverI = h; canvas.style.cursor = h >= 0 ? 'pointer' : ''; }
});
canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    view.zoom *= e.deltaY < 0 ? 1.12 : 0.89;
    view.zoom = Math.max(0.25, Math.min(5, view.zoom));
}, {passive: false});
canvas.addEventListener('click', function (e) {
    if (drag && drag.moved) return;
    var i = pick(e.offsetX, e.offsetY);
    if (i < 0) { selI = -1; sparks = []; renderInfo(); return; }
    var nd = frame.nodes[i];
    if (frame.mode === 'overview') { showGroup(nd.gi); return; }
    selI = i; igniteSparks(); renderInfo();
});
canvas.addEventListener('dblclick', function (e) {
    var i = pick(e.offsetX, e.offsetY);
    if (i < 0) return;
    var nd = frame.nodes[i];
    if (frame.mode === 'overview') showGroup(nd.gi);
    else showEgo(nd.ni);
});

/* ── панель справа ── */
function el(id) { return document.getElementById(id); }
function set3d(on) {
    view.is3d = on;
    var b = el('b42g-3d');
    if (b) b.classList.toggle('active', on);
    var b2 = el('b42g-2d');
    if (b2) b2.classList.toggle('active', !on);
    var sp = el('b42g-spin');
    if (sp) sp.style.display = on ? '' : 'none';
    sim.alive = Math.max(sim.alive, 120);
}

function renderCrumbs() {
    var c = el('b42g-crumbs');
    if (!c) return;
    c.innerHTML = '';
    trail.forEach(function (t, i) {
        var a = document.createElement('button');
        a.className = 'b42g-crumb';
        a.textContent = t.label.length > 30 ? t.label.slice(0, 28) + '…' : t.label;
        a.onclick = function () {
            trail = trail.slice(0, i + 1);
            if (t.mode === 'overview') showOverview();
            else if (t.mode === 'group') showGroup(t.arg, false);
            else showEgo(t.arg, false);
        };
        c.appendChild(a);
        if (i < trail.length - 1) {
            var s = document.createElement('span');
            s.textContent = '›'; s.className = 'b42g-sep';
            c.appendChild(s);
        }
    });
}

function renderInfo() {
    var box = el('b42g-info');
    if (!box) return;
    if (selI < 0 || frame.mode === 'overview' || !frame.nodes[selI]) {
        box.innerHTML = '<div class="b42g-dim" style="padding:6px 0">' +
            (RU ? 'клик — выбрать · двойной клик — вглубь · колесо — зум'
                : 'click — select · double-click — drill · wheel — zoom') + '</div>';
        return;
    }
    var nd = frame.nodes[selI], gn = G.nodes[nd.ni];
    var neigh = adj[nd.ni].slice().sort(function (a, b) { return b[1] - a[1]; })
        .slice(0, 8);
    var rows = neigh.map(function (p) {
        var m = G.nodes[p[0]];
        return '<button class="b42g-jump" data-ni="' + p[0] + '">' +
               nodeName(m) + ' <em>' + p[1] + '</em></button>';
    }).join('');
    box.innerHTML =
        '<div class="b42g-sel"><b>' + nd.label + '</b> <span class="b42g-dim">' +
        gn.kind + '</span></div>' +
        '<div class="b42g-dim">' + gn.n + (RU ? ' статей · ' : ' articles · ') +
        adj[nd.ni].length + (RU ? ' связей' : ' links') + '</div>' +
        '<div style="margin:5px 0 7px"><a href="/lang/' + LANG + '/concepts/' +
        gn.id + '.html">' + (RU ? 'страница понятия →' : 'concept page →') +
        '</a></div>' +
        '<div class="b42g-dim" style="margin-bottom:3px">' +
        (RU ? 'сильнейшие связи (общих статей):' : 'strongest links (shared articles):') +
        '</div>' + rows;
    box.querySelectorAll('.b42g-jump').forEach(function (b) {
        b.onclick = function () { showEgo(+b.dataset.ni); };
    });
}

function buildPanel() {
    /* классы */
    var kb = el('b42g-kinds');
    if (kb) {
        KINDS.forEach(function (K) {
            var lab = document.createElement('label');
            lab.className = 'b42g-check';
            var cb = document.createElement('input');
            cb.type = 'checkbox'; cb.checked = true;
            cb.onchange = function () {
                kindOn[K.k] = cb.checked;
                if (view.layout !== 'force') applyFixedLayout();
                sim.alive = Math.max(sim.alive, 80);
            };
            lab.appendChild(cb);
            var sw = document.createElement('canvas');
            sw.width = 16; sw.height = 16; sw.className = 'b42g-sw';
            var c2 = sw.getContext('2d');
            var keep = ctx; ctx = c2;
            drawShape(8, 8, 5.5, K.sh);
            c2.strokeStyle = TK.muted; c2.lineWidth = 1.3; c2.stroke();
            ctx = keep;
            lab.appendChild(sw);
            lab.appendChild(document.createTextNode(RU ? K.ru : K.en));
            kb.appendChild(lab);
        });
    }
    /* группы */
    var gb = el('b42g-groups');
    if (gb) {
        var all = document.createElement('button');
        all.className = 'b42g-mini';
        all.textContent = RU ? 'все' : 'all';
        all.onclick = function () {
            groupOn = null;
            gb.querySelectorAll('input').forEach(function (c) { c.checked = true; });
            sim.alive = Math.max(sim.alive, 80);
        };
        gb.appendChild(all);
        G.groups.forEach(function (g, i) {
            var lab = document.createElement('label');
            lab.className = 'b42g-check';
            var cb = document.createElement('input');
            cb.type = 'checkbox'; cb.checked = true;
            cb.onchange = function () {
                if (groupOn === null) {
                    groupOn = new Set(G.groups.map(function (_, j) { return j; }));
                }
                if (cb.checked) groupOn.add(i); else groupOn.delete(i);
                if (groupOn.size === G.groups.length) groupOn = null;
                if (view.layout !== 'force') applyFixedLayout();
                sim.alive = Math.max(sim.alive, 80);
            };
            lab.appendChild(cb);
            var t = document.createElement('span');
            var L = groupLabel(g);
            t.textContent = (L.length > 26 ? L.slice(0, 24) + '…' : L) +
                            ' · ' + g.members.length;
            lab.appendChild(t);
            gb.appendChild(lab);
        });
    }
    /* поиск */
    var inp = el('b42g-q'), dl = el('b42g-names');
    if (inp && dl) {
        G.nodes.forEach(function (n) {
            var o = document.createElement('option');
            o.value = nodeName(n);
            dl.appendChild(o);
        });
        inp.addEventListener('change', function () {
            var q = inp.value.toLowerCase();
            for (var i = 0; i < G.nodes.length; i++) {
                var n = G.nodes[i];
                if (nodeName(n).toLowerCase() === q || n.en.toLowerCase() === q) {
                    showEgo(i); inp.blur(); return;
                }
            }
        });
    }
    /* режимы */
    var b2 = el('b42g-2d'), b3 = el('b42g-3d'), sp = el('b42g-spin');
    if (b2) b2.onclick = function () { set3d(false); view.spin = false;
        if (sp) sp.classList.remove('active'); };
    if (b3) b3.onclick = function () { set3d(true); };
    if (sp) sp.onclick = function () {
        view.spin = !view.spin; sp.classList.toggle('active', view.spin);
    };
    document.querySelectorAll('[data-layout]').forEach(function (b) {
        b.onclick = function () {
            view.layout = b.dataset.layout;
            document.querySelectorAll('[data-layout]').forEach(function (x) {
                x.classList.toggle('active', x === b);
            });
            if (view.layout === 'force') { seedLayout(); }
            else applyFixedLayout();
        };
    });
    var wr = el('b42g-w');
    if (wr) wr.addEventListener('input', function () {
        view.minW = +wr.value;
        var l = el('b42g-wv');
        if (l) l.textContent = '≥' + view.minW;
        igniteSparks();
        sim.alive = Math.max(sim.alive, 60);
    });
    var home = el('b42g-home');
    if (home) home.onclick = showOverview;
    set3d(false);
}

/* ── размер ── */
function resize() {
    var r = canvas.parentElement.getBoundingClientRect();
    canvas.width = Math.max(300, r.width) * devicePixelRatio;
    canvas.height = Math.max(420, window.innerHeight - r.top - 24) * devicePixelRatio;
    canvas.style.height = (canvas.height / devicePixelRatio) + 'px';
}
window.addEventListener('resize', resize);
resize();
loop();
})();
