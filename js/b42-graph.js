/* b42-graph v3 — полноэкранное приложение-граф понятий. Свой движок, ноль библиотек.

   Владелец 27.08 (третий заход): «во весь экран; больше прозрачности; иконки —
   цвето-штрихографика, не просто фигурки; рёбра — играть толщиной; дриллдаун —
   фокус остаётся, а не смена картинки; больше плавности; больше статистики;
   шрифты — когда много, выделять главные, мельче, информативней; путь
   исследователя; распределение несимметричное, с натяжениями, чтобы видна
   структура; больше объёмных видов и представлений; панель без наездов,
   тултипы; главное — визуальность, лёгкость, прозрачность».

   ЧТО ВНУТРИ
   · кадры: обзор 50 групп → группа → эго; ребро = ЧИСЛО ОБЩИХ СТАТЕЙ
   · непрерывный фокус: узел, в который проваливаешься, не прыгает — соседи
     рождаются из его точки, камера плавно доезжает
   · классы: свой цвет + свой штрих (двойной контур, диагональ, точка, сетка…)
   · рёбра: квадратичные дуги, толщина/яркость от мощности, подсветка потока
   · подписи: приоритет size·degree, анти-коллизия, три яруса шрифта
   · тултип у курсора; статистика кадра и путь исследователя в панели
   · раскладка с натяжениями: сильное ребро короче, хабы расталкивают сильнее,
     к центру почти не тянет — видна структура, не шар
   · представления: силы · кольцо · сфера · галактика · слои (3D по классам)
   · всё на бренд-токенах, темы, прозрачность и лёгкость */
(function () {
'use strict';

var canvas = document.getElementById('b42g');
if (!canvas) return;
var ctx = canvas.getContext('2d');
var LANG = document.documentElement.lang || 'en';
var RU = LANG === 'ru';

/* ── визуальный язык — из общего ядра (js/b42-graph-core.js): классы, цвета,
   штрихографика, формы, дуги. Один код с мини-графами страниц. ── */
var CORE = window.B42GraphCore;
var KINDS = CORE.KINDS;
var bucketOf = CORE.bucketOf;
function tokens() { return CORE.tokens(); }
var TK = tokens();
new MutationObserver(function () { TK = tokens(); }).observe(
    document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
var kindStyle = {};
KINDS.forEach(function (K) { kindStyle[K.k] = K; });
function styleOf(kind, nd) {
    if (kind !== '_group') return CORE.styleOf(kind);
    return {sh: 'circle', color: (nd && nd.color) || TK.cyan, hatch: 'none'};
}
function pathShape(x, y, r, sh) { CORE.pathShape(ctx, x, y, r, sh); }
function drawNodeIcon(x, y, r, st, alpha, hot, isGroup) {
    CORE.drawNodeIcon(ctx, TK, x, y, r, st, alpha, hot, isGroup);
}
function edgePath(a, b) { CORE.edgePath(ctx, a, b); }

function groupColor(g) {
    var cnt = {};
    g.members.forEach(function (m) {
        var b = bucketOf(G.nodes[m].kind);
        cnt[b] = (cnt[b] || 0) + 1;
    });
    var best = 'rest', n = -1;
    Object.keys(cnt).forEach(function (k) { if (cnt[k] > n) { n = cnt[k]; best = k; } });
    return kindStyle[best].color;
}

/* ── данные ──
   Кадры берём У ВОРКЕРА, когда он доступен: облако отдаёт готовый кадр (обзор
   50 групп — 12 КБ), а статический файл на 1.4 МБ качается целиком ради того
   же самого. Правило дома: тело статично, обвязка динамична. Если воркер
   молчит или мы смотрим локально — падаем на файл, и всё работает как прежде. */
var API = (typeof window.B42_API === 'string' ? window.B42_API : '');
var LIVE_FRAMES = false;          // умеет ли облако отдавать кадры

function apiFrame(key) {
    return fetch(API + '/api/graph?frame=' + encodeURIComponent(key) +
                 '&lang=' + LANG)
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
}

var G = null, adj = null, deg = null;
fetch('/data/concepts-graph.json').then(function (r) { return r.json(); })
    .then(function (d) {
        G = d;
        adj = d.nodes.map(function () { return []; });
        d.edges.forEach(function (e) {
            adj[e[0]].push([e[1], e[2]]);
            adj[e[1]].push([e[0], e[2]]);
        });
        deg = adj.map(function (a) { return a.length; });
        buildPanel();
        /* ВХОД ПО ССЫЛКЕ. Граф всегда открывался обзором групп, и переход с
           карточки понятия или статьи терял то, ради чего человек шёл: он хотел
           посмотреть окружение конкретного понятия, а попадал на карту из
           пятидесяти кругов и должен был искать своё заново. Владелец 28.08:
           «непонятно, как пойти смотреть на граф без групп… когда переходим с
           карточки понятия или статьи, надо отталкиваться от того набора,
           который задан статьёй».
             ?focus=black_hole      — эго-кадр понятия: оно и его соседи
             ?set=id1,id2,id3       — кадр из заданного набора (понятия статьи)
           Не нашли — тихо показываем обзор, как раньше. */
        if (!openFromUrl()) showOverview();
        /* Проба облака: один запрос обзора. Ответил — дальше кадры групп и эго
           берём оттуда (свежие после каждой переразметки, без пересборки сайта). */
        apiFrame('overview').then(function (f) {
            LIVE_FRAMES = !!(f && f.nodes && f.nodes.length);
            var b = document.getElementById('b42g-live');
            if (b) b.textContent = LIVE_FRAMES ? 'облако' : 'файл';
        });
    });
function nodeName(n) { return (RU && n.ru) ? n.ru : n.en; }

/* Куда ведёт узел. Классов в графе три вида, и у каждого свой дом: понятие,
   формула, учёный. Раньше панель всегда предлагала «страницу понятия» — для
   формулы это был бы адрес несуществующей страницы, а для учёного тем более
   (владелец 28.08 попросил показать учёных в графе). */
function pageOf(n) {
    if (n.kind === 'formula') return '/lang/' + LANG + '/formula/' + n.id.slice(2) + '.html';
    if (n.kind === 'scientist') {
        return '/lang/en/scientists/' +
               n.id.slice(2).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '') + '.html';
    }
    return '/lang/' + LANG + '/concepts/' + n.id + '.html';
}
function pageLabel(n) {
    if (n.kind === 'formula') return RU ? 'страница формулы →' : 'formula page →';
    if (n.kind === 'scientist') return RU ? 'страница учёного →' : 'scientist page →';
    return RU ? 'страница понятия →' : 'concept page →';
}

/* Открыть кадр по параметрам адреса. Возвращает true, если открыли. */
function openFromUrl() {
    var q;
    try { q = new URLSearchParams(location.search); } catch (e) { return false; }
    var set = (q.get('set') || '').split(',').filter(Boolean);
    if (set.length > 1) {
        var idxs = [];
        set.forEach(function (id) {
            var i = G.byId ? G.byId[id] : undefined;
            if (i === undefined) i = idOf(id);
            if (i >= 0 && idxs.indexOf(i) < 0) idxs.push(i);
        });
        if (idxs.length > 1) { showSet(idxs, q.get('focus') || set[0]); return true; }
    }
    var f = q.get('focus') || q.get('c') || '';
    if (f) {
        var ni = idOf(f);
        if (ni >= 0) { showEgo(ni); return true; }
    }
    return false;
}

/* Индекс узла по строковому идентификатору понятия или формулы (f:...). */
function idOf(id) {
    if (!G || !G.nodes) return -1;
    for (var i = 0; i < G.nodes.length; i++) if (G.nodes[i].id === id) return i;
    return -1;
}

/* Кадр из готового набора — «то, что задано статьёй»: сами понятия статьи и
   связи между ними, без чужих соседей. Ровно то же, что показывает мини-граф
   на карточке, только во весь экран и с панелью. */
function showSet(idxs, focusId) {
    var f = frameFromIds(idxs, true);
    var fi = -1;
    for (var i = 0; i < idxs.length; i++) if (G.nodes[idxs[i]].id === focusId) fi = i;
    trail = [{mode: 'overview', arg: null, label: RU ? 'Обзор' : 'Overview'}];
    trail.push({mode: 'set', arg: idxs,
                label: (RU ? 'набор статьи · ' : 'article set · ') + idxs.length});
    setFrame('set', f.nodes, f.edges, 'set' + idxs.length);
    selI = fi >= 0 ? fi : 0;
    igniteSparks();
    renderInfo();
}
function groupLabel(g) { return (RU && g.label_ru) ? g.label_ru : g.label_en; }

/* ── состояние ── */
var frame = {mode: 'overview', nodes: [], edges: []};
var view = {is3d: false, layout: 'force', spin: false, minW: 2,
            zoom: 1, zoomT: 1, panX: 0, panY: 0, panTX: 0, panTY: 0,
            rotX: -0.35, rotY: 0.5};
var kindOn = {};
KINDS.forEach(function (K) { kindOn[K.k] = true; });
var groupOn = null;
var catOn = null;             // фильтр разделов arXiv (null = все)
var trail = [], path = [];        // путь исследователя: посещённые эго
var hoverI = -1, selI = -1;
var sim = {vx: [], vy: [], vz: [], alive: 0};
var sparks = [];
var T0 = performance.now();
var iconScale = 1;            // авто: чем плотнее кадр, тем мельче значки
function calcIconScale() {
    var N = visIdx().length || 1;
    iconScale = Math.max(0.28, Math.min(0.68, 4.4 / Math.sqrt(N)));
}

function nodeVisible(nd) {
    if (nd.kind !== '_group' && !kindOn[bucketOf(nd.kind)]) return false;
    /* фильтр групп/разделов — только на широких кадрах (обзор, всё облако):
       внутри группы и в эго кадр уже отобран смыслом; прятать там соседей —
       тот самый баг «все галочки стоят, а после двойного клика фильтруется» */
    var wide = frame.mode === 'overview' || frame.mode === 'all';
    if (wide && groupOn && nd.kind !== '_group' &&
        nd.g !== undefined && nd.g !== null && !groupOn.has(nd.g)) return false;
    if (wide && catOn && nd.kind !== '_group' && nd.cat && !catOn.has(nd.cat))
        return false;
    return true;
}

/* ── кадры: фокус НЕ прыгает — новые узлы рождаются из точки фокуса ── */
function setFrame(mode, nodes, edges, focusKey) {
    var prev = {};
    frame.nodes.forEach(function (nd) { prev[nd.key] = [nd.x, nd.y, nd.z]; });
    var seed = focusKey && prev[focusKey] ? prev[focusKey] : null;
    /* КАЛИБРОВКА СВЯЗЕЙ ПО КАДРУ (владелец 27.08: «важные ярче, остальные
       глуше»). Абсолютная шкала врёт: в одном кадре сильная связь — это 30
       общих статей, в другом — 4. Берём медиану и верхний дециль самого кадра
       и растягиваем контраст между ними; ниже медианы — почти невидимо. */
    var ws = edges.map(function (e) { return e[2]; }).sort(function (a, b) { return a - b; });
    var wMax = ws.length ? ws[ws.length - 1] : 1;
    var wMid = ws.length ? ws[Math.floor(ws.length * 0.5)] : 1;
    var wHi = ws.length ? ws[Math.floor(ws.length * 0.9)] : wMax;
    frame = {mode: mode, nodes: nodes, edges: edges,
             wMax: wMax, wMid: wMid, wHi: Math.max(wHi, wMid + 1)};
    hoverI = -1;
    autoFit = true;
    seedLayout(prev, seed);
    calcIconScale();
    /* камера плавно доезжает так, чтобы фокус оказался в центре */
    if (seed) { view.panTX = -seed[0]; view.panTY = -seed[1]; }
    else { view.panTX = 0; view.panTY = 0; }
    renderCrumbs(); renderInfo(); renderStats(); renderPath();
}

function showOverview() {
    var raw = G.groups.map(function (g) {
        var n = 0;
        g.members.forEach(function (m) { n += G.nodes[m].n; });
        return n;
    });
    var mx = Math.max.apply(null, raw) || 1;
    var nodes = G.groups.map(function (g, i) {
        /* размер — доля от крупнейшей группы КАДРА: абсолютная шкала делала
           шарики огромными, потому что сумма статей группы — тысячи */
        return {key: 'g' + i, gi: i, label: groupLabel(g), n: raw[i], kind: '_group',
                g: i, color: groupColor(g),
                size: 5 + 11 * Math.sqrt(raw[i] / mx)};
    });
    var gw = {};
    G.edges.forEach(function (e) {
        var a = G.nodes[e[0]].g, b = G.nodes[e[1]].g;
        if (a === null || b === null || a === b) return;
        var k = Math.min(a, b) + ':' + Math.max(a, b);
        gw[k] = (gw[k] || 0) + e[2];
    });
    var per = {};
    Object.keys(gw).forEach(function (k) {
        var p = k.split(':');
        (per[+p[0]] = per[+p[0]] || []).push([gw[k], +p[1]]);
        (per[+p[1]] = per[+p[1]] || []).push([gw[k], +p[0]]);
    });
    var keep = {};
    Object.keys(per).forEach(function (a) {
        per[a].sort(function (x, y) { return y[0] - x[0]; })
            .slice(0, 4).forEach(function (t) {
                var b = t[1];
                keep[Math.min(a, b) + ':' + Math.max(a, b)] = t[0];
            });
    });
    var edges = Object.keys(keep).map(function (k) {
        var p = k.split(':');
        return [+p[0], +p[1], keep[k]];
    });
    trail = [{mode: 'overview', label: RU ? 'Обзор' : 'Overview'}];
    selI = -1; sparks = [];
    setFrame('overview', nodes, edges);
}

function frameFromIds(ids, centerFirst) {
    var pos = {};
    ids.forEach(function (id, i) { pos[id] = i; });
    var mx = 1;
    ids.forEach(function (id) { if (G.nodes[id].n > mx) mx = G.nodes[id].n; });
    var nodes = ids.map(function (id, i) {
        var n = G.nodes[id];
        return {key: 'n' + id, ni: id, label: nodeName(n), n: n.n, kind: n.kind,
                g: n.g, cat: n.cat, center: centerFirst && i === 0, out: false,
                size: (3.4 + 8.5 * Math.sqrt(n.n / mx)) *
                      (centerFirst && i === 0 ? 1.5 : 1)};
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
    return {nodes: nodes, edges: edges};
}

function showAll() {
    /* всё облако целиком (владелец: «хочу просто целиком смотреть») —
       фильтры классов/групп/разделов работают, физика на сетке */
    var ids = [];
    for (var i = 0; i < G.nodes.length; i++) ids.push(i);
    var f = frameFromIds(ids);
    trail = [{mode: 'overview', label: RU ? 'Обзор' : 'Overview'},
             {mode: 'all', label: RU ? 'всё облако' : 'whole cloud'}];
    selI = -1; sparks = [];
    setFrame('all', f.nodes, f.edges);
    view.zoomT = 0.4;
    /* на полном полотне слабые связи — каша: поднимаем порог, слайдер вслед */
    if (view.minW < 3) {
        view.minW = 3;
        var wr = el('b42g-w'), wv = el('b42g-wv');
        if (wr) wr.value = 3;
        if (wv) wv.textContent = '≥3';
    }
}

function showGroup(gi, pushCrumb, focusKey) {
    if (LIVE_FRAMES) {
        apiFrame('g:' + gi).then(function (f) {
            if (!f || !f.nodes || !f.nodes.length) { showGroupLocal(gi, pushCrumb, focusKey); return; }
            var nodes = f.nodes.map(function (n, i) {
                return {key: 'n' + n.id, ni: G.byId !== undefined ? G.byId[n.id] : undefined,
                        id: n.id, label: (RU && n.ru) ? n.ru : n.en, n: n.n || 0,
                        kind: n.kind, cat: n.cat, card: n.card, out: !!n.out,
                        size: 3.4 + 8.5 * Math.sqrt((n.n || 1) /
                              Math.max(1, Math.max.apply(null, f.nodes.map(function (x) { return x.n || 1; }))))};
            });
            if (pushCrumb !== false) {
                trail = trail.filter(function (c) { return c.mode === 'overview'; });
                trail.push({mode: 'group', arg: gi, label: groupLabel(G.groups[gi])});
            }
            selI = -1; sparks = [];
            setFrame('group', nodes, f.edges || [], focusKey || ('g' + gi));
        });
        return;
    }
    showGroupLocal(gi, pushCrumb, focusKey);
}

function showGroupLocal(gi, pushCrumb, focusKey) {
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
    /* формулы группы (владелец 27.08: «формул не вижу на графе»): формы,
       связанные с членами группы, — до восьми самых применяемых */
    var fml = {};
    g.members.forEach(function (m) {
        adj[m].forEach(function (p) {
            if (G.nodes[p[0]].kind === 'formula')
                fml[p[0]] = Math.max(fml[p[0]] || 0, p[1]);
        });
    });
    Object.keys(fml).map(function (k) { return [+k, fml[k]]; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8)
        .forEach(function (t) { if (ids.indexOf(t[0]) < 0) ids.push(t[0]); });
    var f = frameFromIds(ids);
    f.nodes.forEach(function (nd) { nd.out = !inSet[nd.ni]; });
    if (pushCrumb !== false) {
        trail = trail.filter(function (c) { return c.mode === 'overview'; });
        trail.push({mode: 'group', arg: gi, label: groupLabel(g)});
    }
    selI = -1; sparks = [];
    setFrame('group', f.nodes, f.edges, focusKey || ('g' + gi));
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
    if (!path.length || path[path.length - 1] !== ni) path.push(ni);
    if (path.length > 14) path.shift();
    setFrame('ego', f.nodes, f.edges, 'n' + ni);
    selI = 0;
    igniteSparks();
    renderInfo();
}

/* ── раскладки ── */
function seedLayout(prev, seed) {
    var N = frame.nodes.length;
    for (var i = 0; i < N; i++) {
        var nd = frame.nodes[i];
        var p = prev && prev[nd.key];
        if (p) { nd.x = p[0]; nd.y = p[1]; nd.z = p[2]; }
        else if (seed) {
            /* рождение из точки фокуса — дриллдаун без «смены картинки» */
            var a0 = Math.random() * Math.PI * 2;
            var r0 = 14 + Math.random() * 30;
            nd.x = seed[0] + Math.cos(a0) * r0;
            nd.y = seed[1] + Math.sin(a0) * r0;
            nd.z = seed[2] + (view.is3d ? (Math.random() - 0.5) * r0 : 0);
        } else {
            var a = (i / Math.max(1, N)) * Math.PI * 2 * 3.883;
            var r = 40 + 24 * Math.sqrt(i);
            nd.x = Math.cos(a) * r; nd.y = Math.sin(a) * r;
            nd.z = view.is3d ? (Math.random() - 0.5) * r : 0;
        }
        nd.tx = null;
    }
    sim.vx = new Array(N).fill(0);
    sim.vy = new Array(N).fill(0);
    sim.vz = new Array(N).fill(0);
    sim.alive = 320;
    if (view.layout !== 'force') applyFixedLayout();
}

function visIdx() {
    var out = [];
    frame.nodes.forEach(function (nd, i) { if (nodeVisible(nd)) out.push(i); });
    return out;
}

function applyFixedLayout() {
    var vis = visIdx();
    var N = vis.length || 1;
    var i, nd;
    if (view.layout === 'ring') {
        var order = vis.slice().sort(function (a, b) {
            var A = frame.nodes[a], B = frame.nodes[b];
            return ((A.g || 0) - (B.g || 0)) ||
                   (bucketOf(A.kind) < bucketOf(B.kind) ? -1 : 1);
        });
        var R = 60 + N * 3.1;
        order.forEach(function (idx, j) {
            var a = (j / N) * Math.PI * 2 - Math.PI / 2;
            frame.nodes[idx].tx = [Math.cos(a) * R, Math.sin(a) * R, 0];
        });
    } else if (view.layout === 'sphere') {
        var R2 = 60 + N * 1.9;
        vis.forEach(function (idx, j) {
            var y = 1 - (j / Math.max(1, N - 1)) * 2;
            var rad = Math.sqrt(1 - y * y), th = 2.39996 * j;
            frame.nodes[idx].tx =
                [Math.cos(th) * rad * R2, y * R2, Math.sin(th) * rad * R2];
        });
        if (!view.is3d) set3d(true);
    } else if (view.layout === 'galaxy') {
        /* рукава по группам: каждая группа — свой рукав лог-спирали */
        var byG = {};
        vis.forEach(function (idx) {
            var g = frame.nodes[idx].g || 0;
            (byG[g] = byG[g] || []).push(idx);
        });
        var arms = Object.keys(byG);
        arms.forEach(function (g, ai) {
            var arm = byG[g];
            arm.sort(function (a, b) { return frame.nodes[b].n - frame.nodes[a].n; });
            var base = (ai / arms.length) * Math.PI * 2;
            arm.forEach(function (idx, j) {
                var t = j / Math.max(1, arm.length - 1);
                var ang = base + t * 2.2;
                var r = 34 + t * (70 + arm.length * 6);
                frame.nodes[idx].tx =
                    [Math.cos(ang) * r, Math.sin(ang) * r,
                     view.is3d ? (Math.random() - 0.5) * 26 : 0];
            });
        });
    } else if (view.layout === 'layers') {
        /* этажи по классам в 3D — объёмный вид структуры */
        if (!view.is3d) set3d(true);
        var byK = {};
        vis.forEach(function (idx) {
            var b = bucketOf(frame.nodes[idx].kind);
            (byK[b] = byK[b] || []).push(idx);
        });
        var ks = KINDS.map(function (K) { return K.k; })
            .filter(function (k) { return byK[k]; });
        ks.forEach(function (k, ki) {
            var lvl = (ki - (ks.length - 1) / 2) * 62;
            var arr = byK[k];
            arr.forEach(function (idx, j) {
                var a = (j / arr.length) * Math.PI * 2 * 3.883;
                var r = 26 + 15 * Math.sqrt(j);
                frame.nodes[idx].tx =
                    [Math.cos(a) * r, lvl, Math.sin(a) * r];
            });
        });
    }
    sim.alive = 320;
    autoFit = true;
}

/* длина покоя ребра — одна и та же для пружины и для окраски натяжения */
function restLen(e) {
    var wl = Math.log(1 + e[2]);
    if (frame.mode === 'overview') return 190 + 70 / (1 + wl * 0.2);
    if (frame.mode === 'all') return 120 / (1 + wl * 0.42);
    return 205 / (1 + wl * 0.42);
}

/* натяжения: сильное ребро — коротко и жёстко; хабы расталкивают сильнее;
   к центру почти не тянет — структура вытягивается, а не сворачивается в шар */
function tick() {
    if (sim.alive <= 0) return;
    sim.alive--;
    var n = frame.nodes, N = n.length, i, j;
    if (view.layout !== 'force') {
        for (i = 0; i < N; i++) {
            if (!n[i].tx) continue;
            n[i].x += (n[i].tx[0] - n[i].x) * 0.12;
            n[i].y += (n[i].tx[1] - n[i].y) * 0.12;
            n[i].z += (n[i].tx[2] - n[i].z) * 0.12;
        }
        if (sim.alive % 24 === 0) fitView();
        return;
    }
    var vis = [];
    for (i = 0; i < N; i++) if (nodeVisible(n[i])) vis.push(i);
    function repel(i, j) {
        var dx = n[j].x - n[i].x, dy = n[j].y - n[i].y, dz = n[j].z - n[i].z;
        var d2 = dx * dx + dy * dy + dz * dz + 40;
        /* хабы расталкивают сильнее, но с кэпом — иначе крупные группы
           обзора разгоняли облако за экран (поймано глазами 27.08) */
        var K = 900 * Math.sqrt(
            Math.min(24, n[i].size + 2) * Math.min(24, n[j].size + 2)) * 0.22;
        var f = K / d2, d = Math.sqrt(d2);
        dx /= d; dy /= d; dz /= d;
        sim.vx[i] -= dx * f; sim.vy[i] -= dy * f; sim.vz[i] -= dz * f;
        sim.vx[j] += dx * f; sim.vy[j] += dy * f; sim.vz[j] += dz * f;
    }
    if (vis.length <= 320) {
        for (var a1 = 0; a1 < vis.length; a1++)
            for (var b1 = a1 + 1; b1 < vis.length; b1++)
                repel(vis[a1], vis[b1]);
    } else {
        /* «всё облако»: отталкивание по сетке — только соседние ячейки,
           O(n·k) вместо O(n²); дальнее поле держит слабая гравитация */
        var CELL = 130, grid = {};
        vis.forEach(function (i2) {
            var key = Math.floor(n[i2].x / CELL) + ':' + Math.floor(n[i2].y / CELL);
            (grid[key] = grid[key] || []).push(i2);
        });
        vis.forEach(function (i2) {
            var gx = Math.floor(n[i2].x / CELL), gy = Math.floor(n[i2].y / CELL);
            for (var ox = -1; ox <= 1; ox++)
                for (var oy = -1; oy <= 1; oy++) {
                    var cell = grid[(gx + ox) + ':' + (gy + oy)];
                    if (!cell) continue;
                    for (var c1 = 0; c1 < cell.length; c1++)
                        if (cell[c1] > i2) repel(i2, cell[c1]);
                }
        });
    }
    frame.edges.forEach(function (e) {
        if (e[2] < view.minW) return;
        var a = e[0], b = e[1];
        if (!nodeVisible(n[a]) || !nodeVisible(n[b])) return;
        var dx = n[b].x - n[a].x, dy = n[b].y - n[a].y, dz = n[b].z - n[a].z;
        var d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
        var wl = Math.log(1 + e[2]);
        var target = restLen(e);
        var stiff = 0.00016 * (1 + wl * 0.5);      // и жёстче: натяжение видно
        /* сила ограничена: на тяжёлых рёбрах обзора (веса — тысячи) f растёт
           как d² и за два тика взрывала симуляцию в NaN (поймано 27.08) */
        var f = (d - target) * stiff * Math.min(d, 240);
        if (f > 10) f = 10; else if (f < -10) f = -10;
        dx /= d; dy /= d; dz /= d;
        sim.vx[a] += dx * f; sim.vy[a] += dy * f; sim.vz[a] += dz * f;
        sim.vx[b] -= dx * f; sim.vy[b] -= dy * f; sim.vz[b] -= dz * f;
    });
    /* гравитация анизотропная: по X слабее (экран шире) — облако растягивается
       по всей зоне, а не сжимается в точку по центру */
    var totE = 0;
    for (i = 0; i < N; i++) {
        sim.vx[i] = (sim.vx[i] - n[i].x * 0.00042) * 0.84;
        sim.vy[i] = (sim.vy[i] - n[i].y * 0.0011) * 0.84;
        sim.vz[i] = (sim.vz[i] - n[i].z * 0.0011) * 0.84;
        totE += sim.vx[i] * sim.vx[i] + sim.vy[i] * sim.vy[i];
        /* предельная скорость — вторая страховка устойчивости */
        var sp = Math.sqrt(sim.vx[i] * sim.vx[i] + sim.vy[i] * sim.vy[i] +
                           sim.vz[i] * sim.vz[i]);
        if (sp > 26) {
            var kk = 26 / sp;
            sim.vx[i] *= kk; sim.vy[i] *= kk; sim.vz[i] *= kk;
        }
        if (i === dragNode) continue;      // узел в руке — двигает мышь
        n[i].x += sim.vx[i]; n[i].y += sim.vy[i];
        if (view.is3d) n[i].z += sim.vz[i]; else n[i].z = 0;
    }
    /* уснуть, когда всё доехало — никакого дребезга на месте */
    if (dragNode < 0 && totE / Math.max(1, N) < 0.02 && sim.alive < 1e8)
        sim.alive = Math.min(sim.alive, 8);
    if (dragNode < 0 && sim.alive % 24 === 0) fitView();
}

/* авто-вписывание: облако всегда в кадре, что бы физика ни устроила.
   Мягко — целями zoomT/panT, камера сама доедет с ease. Пока пользователь
   не трогал руками (drag/wheel сбрасывают авто до следующего кадра). */
var autoFit = true;
function fitView() {
    if (!autoFit) return;
    var W = canvas.width / devicePixelRatio, H = canvas.height / devicePixelRatio;
    var vis = visIdx();
    if (vis.length < 2) return;
    var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
    vis.forEach(function (i) {
        var nd = frame.nodes[i];
        if (nd.x < minX) minX = nd.x;
        if (nd.x > maxX) maxX = nd.x;
        if (nd.y < minY) minY = nd.y;
        if (nd.y > maxY) maxY = nd.y;
    });
    var spanX = Math.max(80, maxX - minX), spanY = Math.max(80, maxY - minY);
    /* поля минимальные — кадр занимает весь холст (владелец: «чтобы занимал
       всё место, а то скучено и не видно») */
    var pad = 64;
    var z = Math.min((W - 290 - pad) / spanX, (H - pad) / spanY);
    view.zoomT = Math.max(0.25, Math.min(3.2, z));
    view.panTX = -(minX + maxX) / 2 - 130 / view.zoomT;   // панель справа — центр левее
    view.panTY = -(minY + maxY) / 2 + 34 / view.zoomT;    // и ниже верхней панели
}

/* ── проекция и камера ── */
function project(nd) {
    var x = nd.x, y = nd.y, z = nd.z;
    if (view.is3d) {
        var cy = Math.cos(view.rotY), sy = Math.sin(view.rotY);
        var cx = Math.cos(view.rotX), sx = Math.sin(view.rotX);
        var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
        var y1 = y * cx + z1 * sx, z2 = -y * sx + z1 * cx;
        var p = 620 / (620 + z2);          // ближе фокус — заметнее перспектива
        x = x1 * p; y = y1 * p; nd._depth = p;
    } else nd._depth = 1;
    var W = canvas.width / devicePixelRatio, H = canvas.height / devicePixelRatio;
    return [W / 2 + (x + view.panX) * view.zoom,
            H / 2 + (y + view.panY) * view.zoom];
}

/* ── формы + штрихографика ── */


/* ── искры вдоль рёбер выбранного ── */
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

function neighborsOf(i) {
    var s = {};
    frame.edges.forEach(function (e) {
        if (e[2] < view.minW) return;
        if (e[0] === i) s[e[1]] = 1;
        if (e[1] === i) s[e[0]] = 1;
    });
    return s;
}


/* ── отрисовка ── */
function draw() {
    var W = canvas.width / devicePixelRatio, H = canvas.height / devicePixelRatio;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var n = frame.nodes;
    if (!n.length) return;
    /* камера — всегда плавно */
    view.zoom += (view.zoomT - view.zoom) * 0.12;
    view.panX += (view.panTX - view.panX) * 0.10;
    view.panY += (view.panTY - view.panY) * 0.10;
    if (view.is3d && view.spin) view.rotY += 0.0032;

    var pts = n.map(project);
    var focusI = hoverI >= 0 ? hoverI : selI;
    var nbr = focusI >= 0 ? neighborsOf(focusI) : null;
    var now = performance.now();

    /* рёбра: дуги, толщина и яркость — мощность */
    frame.edges.forEach(function (e) {
        if (e[2] < view.minW) return;
        if (!nodeVisible(n[e[0]]) || !nodeVisible(n[e[1]])) return;
        var a = pts[e[0]], b = pts[e[1]];
        var hot = focusI >= 0 && (e[0] === focusI || e[1] === focusI);
        var dim = focusI >= 0 && !hot;
        /* q: 0 — медианная связь кадра, 1 — уровень верхнего дециля */
        var q = (Math.log(1 + e[2]) - Math.log(1 + frame.wMid)) /
                (Math.log(1 + frame.wHi) - Math.log(1 + frame.wMid) + 1e-6);
        q = q < 0 ? 0 : (q > 1 ? 1 : q);
        var wgt = q;
        /* резиновость видна: растянутое сверх покоя ребро теплеет и тончает */
        var ddx = n[e[1]].x - n[e[0]].x, ddy = n[e[1]].y - n[e[0]].y,
            ddz = n[e[1]].z - n[e[0]].z;
        var dl = Math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz);
        var stretch = Math.max(0, Math.min(1, (dl / restLen(e) - 1.35) / 1.8));
        ctx.strokeStyle = hot ? TK.cyan : (stretch > 0.05 ? TK.ochre : TK.muted);
        /* на кадре-тысячнике рёбра глушим вдвое — иначе войлок */
        var crowd = frame.nodes.length > 800 ? 0.5 : 1;
        /* нелинейно: слабое гаснет, сильное звенит — контраст, а не серая сетка */
        var pow15 = wgt * wgt * (0.4 + wgt * 0.6);
        ctx.globalAlpha = (dim ? 0.035 : (hot ? 0.8 : (0.035 + pow15 * 0.62) * crowd)) *
                          (1 - stretch * 0.35);
        /* струны: тонкие, почти нитяные — мощность в яркости больше, чем в теле */
        ctx.lineWidth = (0.28 + pow15 * 2.6) * (hot ? 1.3 : 1) * (1 - stretch * 0.5);
        if (n[e[0]].out || n[e[1]].out) ctx.setLineDash([4, 5]);
        ctx.beginPath(); edgePath(a, b); ctx.stroke();
        ctx.setLineDash([]);
    });
    ctx.globalAlpha = 1;

    /* искры */
    sparks.forEach(function (s) {
        if (!nodeVisible(n[s.a]) || !nodeVisible(n[s.b])) return;
        s.t += s.sp;
        if (s.t > 1) s.t = 0;
        var a = pts[s.a], b = pts[s.b];
        var x = a[0] + (b[0] - a[0]) * s.t, y = a[1] + (b[1] - a[1]) * s.t;
        ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fillStyle = TK.ochre; ctx.globalAlpha = 0.85; ctx.fill();
    });
    ctx.globalAlpha = 1;

    /* узлы */
    var order = visIdx();
    if (view.is3d) order.sort(function (a, b) { return n[a]._depth - n[b]._depth; });
    order.forEach(function (i) {
        var p = pts[i], nd = n[i];
        var r = Math.max(2.5, nd.size * iconScale * view.zoom *
                              (view.is3d ? nd._depth : 1));
        var hot = i === hoverI || i === selI;
        var dim = focusI >= 0 && !hot && !(nbr && nbr[i]);
        if (i === selI) {
            var ph = (now - T0) / 700;
            ctx.beginPath();
            ctx.arc(p[0], p[1], r + 7 + Math.sin(ph) * 3.5, 0, Math.PI * 2);
            ctx.strokeStyle = TK.cyan;
            ctx.globalAlpha = 0.45 + Math.sin(ph) * 0.22;
            ctx.lineWidth = 1.4; ctx.stroke();
        }
        /* глубина в 3D: передние ярче и больше, задние тают */
        var dp = view.is3d ? Math.max(0, Math.min(1, (nd._depth - 0.55) * 2.2)) : 1;
        var alpha = (dim ? 0.20 : 1) * (view.is3d ? 0.12 + dp * 0.88 : 1);
        drawNodeIcon(p[0], p[1], r, styleOf(nd.kind, nd), alpha, hot,
                     nd.kind === '_group');
    });
    ctx.globalAlpha = 1;

    /* подписи: приоритет size·degree, три яруса, анти-коллизия */
    var labels = [];
    order.forEach(function (i) {
        var nd = n[i], p = pts[i];
        var r = Math.max(2.5, nd.size * iconScale * view.zoom *
                              (view.is3d ? nd._depth : 1));
        var hot = i === hoverI || i === selI;
        var near = nbr && nbr[i];
        var dp = view.is3d ? Math.max(0, Math.min(1, (nd._depth - 0.55) * 2.2)) : 1;
        var pri = ((hot ? 1e9 : 0) + (near ? 1e6 : 0) +
                  nd.size * (1 + (nd.ni !== undefined ? deg[nd.ni] : 10) * 0.15)) *
                  (0.15 + dp * 0.85);       // передние подписи важнее задних
        var dim = focusI >= 0 && !hot && !near;
        if (dim && !hot) return;
        if (view.is3d && dp < 0.22 && !hot) return;   // дальний текст молчит
        labels.push({i: i, x: p[0], y: p[1] + r + 11, pri: pri, hot: hot,
                     dp: dp, big: hot || r > 12 || frame.mode === 'overview'});
    });
    labels.sort(function (a, b) { return b.pri - a.pri; });
    var taken = [];
    var maxLabels = frame.mode === 'overview' ? 50 : (view.zoom > 1.6 ? 70 : 26);
    var shown = 0;
    labels.forEach(function (L) {
        if (shown >= maxLabels && !L.hot) return;
        var nd = n[L.i];
        var fs = L.hot ? 12.5 : (L.big ? 11 : 9.5);
        ctx.font = (L.hot ? '600 ' : '') + fs + 'px ' + TK.mono;
        var text = nd.label.length > 30 ? nd.label.slice(0, 28) + '…' : nd.label;
        var w = ctx.measureText(text).width;
        var box = [L.x - w / 2 - 2, L.y - fs, w + 4, fs + 4];
        for (var t = 0; t < taken.length; t++) {
            var B = taken[t];
            if (box[0] < B[0] + B[2] && box[0] + box[2] > B[0] &&
                box[1] < B[1] + B[3] && box[1] + box[3] > B[1]) return;
        }
        taken.push(box);
        shown++;
        ctx.fillStyle = L.hot ? TK.cyan : (L.big ? TK.text : TK.muted);
        ctx.globalAlpha = (L.hot ? 1 : (L.big ? 0.9 : 0.62)) *
                          (view.is3d ? 0.25 + L.dp * 0.75 : 1);
        ctx.textAlign = 'center';
        ctx.fillText(text, L.x, L.y);
    });
    ctx.globalAlpha = 1;

    /* тултип у курсора */
    if (hoverI >= 0 && mouse.x !== undefined) {
        var hd = n[hoverI];
        var lines = [hd.label], cardFrom = 2;
        if (hd.kind === '_group') {
            lines.push((RU ? 'группа · статей: ' : 'group · articles: ') + hd.n);
            lines.push(RU ? 'клик — открыть' : 'click to open');
            cardFrom = 99;
        } else {
            var gi2 = G.nodes[hd.ni];
            lines.push(gi2.kind + ' · ' + gi2.n + (RU ? ' ст.' : ' art.') +
                       ' · ' + deg[hd.ni] + (RU ? ' св.' : ' links'));
            /* карточка понятия прямо в тултипе — смотреть и учиться на месте */
            if (gi2.card) {
                ctx.font = '10.5px ' + TK.mono;
                var words = gi2.card.split(' '), line = '';
                for (var wi = 0; wi < words.length && lines.length < 7; wi++) {
                    var test = line ? line + ' ' + words[wi] : words[wi];
                    if (ctx.measureText(test).width > 250 && line) {
                        lines.push(line); line = words[wi];
                    } else line = test;
                }
                if (line && lines.length < 7) lines.push(line);
                else if (lines.length >= 7) lines[6] += '…';
            }
        }
        ctx.font = '11px ' + TK.mono;
        var tw = 0;
        lines.forEach(function (s) { tw = Math.max(tw, ctx.measureText(s).width); });
        var th = lines.length * 14 + 10;
        var tx = Math.min(mouse.x + 14, W - tw - 18);
        var ty = Math.min(mouse.y + 6, H - th - 8);
        ctx.globalAlpha = 0.94;
        ctx.fillStyle = TK.surface;
        ctx.strokeStyle = TK.hair;
        ctx.beginPath();
        ctx.roundRect(tx - 7, ty - 13, tw + 14, th, 6);
        ctx.fill(); ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.textAlign = 'start';
        lines.forEach(function (s, li) {
            ctx.font = (li >= cardFrom ? '10.5px ' : (li ? '10.5px ' : '600 11px ')) + TK.mono;
            ctx.fillStyle = li === 0 ? TK.text : (li < cardFrom ? TK.soft : TK.muted);
            ctx.fillText(s, tx, ty + li * 14);
        });
    }
    frame._pts = pts;
}

function loop() {
    window.__loopN = (window.__loopN || 0) + 1;
    try { demoTick(); tick(); draw(); }
    catch (e) { window.__loopErr = String(e) + ' | ' + (e.stack || '').split(String.fromCharCode(10))[1]; }
    requestAnimationFrame(loop);
}

/* ── взаимодействие ── */
var mouse = {};
function pick(mx, my) {
    if (!frame._pts) return -1;
    var best = -1, bd = 20 * 20;
    frame._pts.forEach(function (p, i) {
        if (!nodeVisible(frame.nodes[i])) return;
        var dx = p[0] - mx, dy = p[1] - my, d = dx * dx + dy * dy;
        var r = Math.max(8, frame.nodes[i].size * iconScale * view.zoom);
        if (d < Math.max(bd, r * r) && d < (r + 8) * (r + 8)) { best = i; bd = d; }
    });
    return best;
}
var drag = null, dragNode = -1;
function screenToWorld(mx, my) {
    var W = canvas.width / devicePixelRatio, H = canvas.height / devicePixelRatio;
    return [(mx - W / 2) / view.zoom - view.panX,
            (my - H / 2) / view.zoom - view.panY];
}
canvas.addEventListener('mousedown', function (e) {
    var i = pick(e.offsetX, e.offsetY);
    if (i >= 0) {
        /* резиновое перетаскивание: узел за мышью, пружины тащат остальное */
        dragNode = i;
        stopDemo();
        sim.alive = 1e9;                 // физика живёт, пока тянем
        canvas.style.cursor = 'grabbing';
        return;
    }
    drag = {x: e.offsetX, y: e.offsetY, moved: false};
});
window.addEventListener('mouseup', function () {
    drag = null;
    if (dragNode >= 0) {
        dragNode = -1;
        sim.alive = 300;                 // дать всему доехать и уснуть
        canvas.style.cursor = '';
    }
});
canvas.addEventListener('mousemove', function (e) {
    mouse.x = e.offsetX; mouse.y = e.offsetY;
    if (dragNode >= 0) {
        var nd = frame.nodes[dragNode];
        if (view.is3d) {
            /* в 3D тянем в плоскости экрана: дельту разворачиваем обратно */
            var dx2 = e.movementX / view.zoom, dy2 = e.movementY / view.zoom;
            var cy = Math.cos(-view.rotY), sy = Math.sin(-view.rotY);
            var cx = Math.cos(-view.rotX), sx = Math.sin(-view.rotX);
            var y1 = dy2 * cx, z1 = -dy2 * sx;
            nd.x += dx2 * cy + z1 * sy;
            nd.y += y1;
            nd.z += -dx2 * sy + z1 * cy;
        } else {
            var w = screenToWorld(e.offsetX, e.offsetY);
            nd.x = w[0]; nd.y = w[1];
        }
        sim.vx[dragNode] = 0; sim.vy[dragNode] = 0; sim.vz[dragNode] = 0;
        return;
    }
    if (drag) {
        var dx = e.offsetX - drag.x, dy = e.offsetY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
        autoFit = false;
        if (view.is3d) { view.rotY += dx * 0.008; view.rotX += dy * 0.008; }
        else {
            view.panTX = view.panX = view.panX + dx / view.zoom;
            view.panTY = view.panY = view.panY + dy / view.zoom;
        }
        drag.x = e.offsetX; drag.y = e.offsetY;
        return;
    }
    var h = pick(e.offsetX, e.offsetY);
    if (h !== hoverI) { hoverI = h; canvas.style.cursor = h >= 0 ? 'pointer' : ''; }
});
canvas.addEventListener('mouseleave', function () { hoverI = -1; });
canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    stopDemo();
    autoFit = false;
    view.zoomT *= e.deltaY < 0 ? 1.14 : 0.88;
    view.zoomT = Math.max(0.25, Math.min(5, view.zoomT));
}, {passive: false});
canvas.addEventListener('click', function (e) {
    stopDemo();
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

/* ── демо-автопилот (владелец: «я запустил — и он пошёл всё показывать сам:
   крутит, подсвечивает, ездит; позиционный режим исследования») ── */
var demo = {on: false, phase: 'idle', at: 0, visited: {}};
function startDemo() {
    demo.on = true;
    demo.phase = 'start';
    demo.at = performance.now();
    demo.visited = {};
    var b = el('b42g-demo');
    if (b) b.classList.add('active');
    sim.alive = Math.max(sim.alive, 400);
}
function stopDemo() {
    if (!demo.on) return;
    demo.on = false;
    view.spin = false;
    var b = el('b42g-demo');
    if (b) b.classList.remove('active');
    var sp = el('b42g-spin');
    if (sp) sp.classList.remove('active');
}
function demoTick() {
    if (!demo.on || !G) return;
    var now = performance.now();
    var dt = now - demo.at;
    sim.alive = Math.max(sim.alive, 90);
    switch (demo.phase) {
    case 'start':
        /* старт: от выбранной темы, либо с обзора */
        if (selI >= 0 && frame.mode !== 'overview' && frame.nodes[selI].ni !== undefined) {
            demo.phase = 'ego-look';
        } else {
            if (frame.mode !== 'overview') showOverview();
            demo.phase = 'ov-pick';
        }
        demo.at = now;
        break;
    case 'ov-pick':                       // обзор: подсветить группу побольше
        if (dt < 1400) break;
        var cand = [];
        frame.nodes.forEach(function (nd, i) {
            if (!demo.visited['g' + nd.gi]) cand.push([nd.n, i]);
        });
        cand.sort(function (a, b) { return b[0] - a[0]; });
        if (!cand.length) { demo.visited = {}; break; }
        hoverI = cand[0][1];
        demo.pick = cand[0][1];
        demo.phase = 'ov-enter';
        demo.at = now;
        break;
    case 'ov-enter':                      // …и войти в неё
        if (dt < 1300) break;
        var gi = frame.nodes[demo.pick].gi;
        demo.visited['g' + gi] = 1;
        showGroup(gi);
        demo.phase = 'grp-pick';
        demo.at = now;
        break;
    case 'grp-pick':                      // группа: осмотреться, выбрать хаб
        if (dt < 2600) break;
        var best = -1, bn = -1;
        frame.nodes.forEach(function (nd, i) {
            if (nd.out || nd.ni === undefined) return;
            if (deg[nd.ni] > bn && !demo.visited['n' + nd.ni]) {
                bn = deg[nd.ni]; best = i;
            }
        });
        if (best < 0) { demo.phase = 'start'; demo.at = now; break; }
        selI = best; igniteSparks(); renderInfo();
        demo.phase = 'grp-enter';
        demo.at = now;
        break;
    case 'grp-enter':                     // …и провалиться в эго
        if (dt < 1600) break;
        var ni = frame.nodes[selI].ni;
        demo.visited['n' + ni] = 1;
        showEgo(ni);
        demo.phase = 'ego-look';
        demo.at = now;
        break;
    case 'ego-look':                      // эго: покрутить и оглядеться
        if (view.is3d) view.spin = true;
        if (dt < 4200) break;
        view.spin = false;
        demo.phase = 'ego-next';
        demo.at = now;
        break;
    case 'ego-next':                      // перелёт к сильнейшему непосещённому
        if (dt < 700) break;
        var cur = frame.nodes[0] && frame.nodes[0].ni;
        var nxt = -1;
        if (cur !== undefined) {
            var ns = adj[cur].slice().sort(function (a, b) { return b[1] - a[1]; });
            for (var k = 0; k < ns.length; k++) {
                if (!demo.visited['n' + ns[k][0]]) { nxt = ns[k][0]; break; }
            }
        }
        if (nxt < 0 || Object.keys(demo.visited).length % 7 === 6) {
            demo.phase = 'start';         // время сменить тему — назад к обзору
            selI = -1; sparks = [];
            showOverview();
        } else {
            demo.visited['n' + nxt] = 1;
            showEgo(nxt);
            demo.phase = 'ego-look';
        }
        demo.at = now;
        break;
    }
}

/* ── ПАЛЕЦ (владелец 27.08: «мобильная версия, поведение графа»). До этого на
   телефоне граф был картинкой: ни таскать, ни приближать, ни выбирать.
   Один палец — тащить (в 3D вращать), два — щипок-зум, тап — выбрать,
   двойной тап — вглубь. touch-action: none на холсте, иначе браузер забирает
   жест себе и страница уезжает вместо графа. ── */
canvas.style.touchAction = 'none';
var touch = {mode: null, x: 0, y: 0, d0: 0, z0: 1, t: 0, lastTap: 0, moved: 0};

function tDist(e) {
    var a = e.touches[0], b = e.touches[1];
    return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}
function tLocal(e, i) {
    var r = canvas.getBoundingClientRect(), t = e.touches[i] || e.changedTouches[i];
    return [t.clientX - r.left, t.clientY - r.top];
}

canvas.addEventListener('touchstart', function (e) {
    stopDemo();
    touch.moved = 0;
    if (e.touches.length === 2) {
        touch.mode = 'pinch';
        touch.d0 = tDist(e);
        touch.z0 = view.zoomT;
        autoFit = false;
        return;
    }
    var p = tLocal(e, 0);
    touch.x = p[0]; touch.y = p[1]; touch.t = Date.now();
    mouse.x = p[0]; mouse.y = p[1];
    var i = pick(p[0], p[1]);
    if (i >= 0) {
        touch.mode = 'node';
        dragNode = i;
        sim.alive = 1e9;
        hoverI = i;              /* подсказка под пальцем — как наведение мышью */
    } else {
        touch.mode = 'pan';
        autoFit = false;
    }
}, {passive: true});

canvas.addEventListener('touchmove', function (e) {
    if (!touch.mode) return;
    if (touch.mode === 'pinch' && e.touches.length === 2) {
        e.preventDefault();
        var k = tDist(e) / (touch.d0 || 1);
        view.zoomT = Math.max(0.25, Math.min(5, touch.z0 * k));
        return;
    }
    var p = tLocal(e, 0);
    var dx = p[0] - touch.x, dy = p[1] - touch.y;
    touch.moved += Math.abs(dx) + Math.abs(dy);
    e.preventDefault();
    if (touch.mode === 'node' && dragNode >= 0) {
        var nd = frame.nodes[dragNode];
        if (view.is3d) {
            nd.x += dx / view.zoom; nd.y += dy / view.zoom;
        } else {
            var w = screenToWorld(p[0], p[1]);
            nd.x = w[0]; nd.y = w[1];
        }
        sim.vx[dragNode] = 0; sim.vy[dragNode] = 0; sim.vz[dragNode] = 0;
    } else if (view.is3d) {
        view.rotY += dx * 0.008; view.rotX += dy * 0.008;
    } else {
        view.panTX = view.panX = view.panX + dx / view.zoom;
        view.panTY = view.panY = view.panY + dy / view.zoom;
    }
    touch.x = p[0]; touch.y = p[1];
}, {passive: false});

canvas.addEventListener('touchend', function (e) {
    var wasNode = touch.mode === 'node';
    if (dragNode >= 0) { dragNode = -1; sim.alive = 300; }
    var quick = Date.now() - touch.t < 300 && touch.moved < 12;
    touch.mode = null;
    if (!quick) return;
    var p = tLocal(e, 0);
    var i = pick(p[0], p[1]);
    var now = Date.now();
    var dbl = now - touch.lastTap < 320;
    touch.lastTap = now;
    if (i < 0) { selI = -1; sparks = []; hoverI = -1; renderInfo(); return; }
    var nd = frame.nodes[i];
    if (frame.mode === 'overview') { showGroup(nd.gi); return; }
    if (dbl) { showEgo(nd.ni); return; }
    selI = i; hoverI = i; igniteSparks(); renderInfo();
}, {passive: true});

/* ── панель ── */
function el(id) { return document.getElementById(id); }
function set3d(on) {
    view.is3d = on;
    var b = el('b42g-3d'); if (b) b.classList.toggle('active', on);
    var b2 = el('b42g-2d'); if (b2) b2.classList.toggle('active', !on);
    var sp = el('b42g-spin'); if (sp) sp.style.display = on ? '' : 'none';
    sim.alive = Math.max(sim.alive, 140);
}

function renderCrumbs() {
    var c = el('b42g-crumbs');
    if (!c) return;
    c.innerHTML = '';
    trail.forEach(function (t, i) {
        var a = document.createElement('button');
        a.className = 'b42g-crumb';
        a.textContent = t.label.length > 26 ? t.label.slice(0, 24) + '…' : t.label;
        a.title = t.label;
        a.onclick = function () {
            trail = trail.slice(0, i + 1);
            if (t.mode === 'overview') showOverview();
            else if (t.mode === 'all') showAll();
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
    /* На обзоре под курсором — не узел, а ОБЛАСТЬ, и панель должна объяснять
       именно её: название и строку «о чём это». Раньше здесь всегда висела
       подсказка про клик и зум, а круги оставались молчаливыми — владелец 28.08:
       «название группы мне ни о чём не говорит, а у нас с этого начинается граф
       знаний». */
    if (frame.mode === 'overview') {
        var gi = -1;
        if (hoverI >= 0 && frame.nodes[hoverI]) gi = frame.nodes[hoverI].gi;
        else if (selI >= 0 && frame.nodes[selI]) gi = frame.nodes[selI].gi;
        var gg = gi >= 0 ? G.groups[gi] : null;
        if (gg) {
            var note = (RU && gg.note_ru) ? gg.note_ru : (gg.note_en || '');
            box.innerHTML =
                '<div class="b42g-sel"><b>' + groupLabel(gg) + '</b></div>' +
                '<div class="b42g-dim">' + gg.members.length +
                (RU ? ' понятий' : ' concepts') + '</div>' +
                (note ? '<div class="b42g-note">' + note + '</div>' : '') +
                '<div class="b42g-dim">' +
                (RU ? 'двойной клик — войти в область' : 'double-click to enter') +
                '</div>';
            return;
        }
        box.innerHTML = '<div class="b42g-dim">' +
            (RU ? 'наведи на круг — что это за область · двойной клик — внутрь'
                : 'hover a circle to see the area · double-click to enter') + '</div>';
        return;
    }
    if (selI < 0 || !frame.nodes[selI]) {
        box.innerHTML = '<div class="b42g-dim">' +
            (RU ? 'клик — выбрать · двойной — вглубь · колесо — зум'
                : 'click — select · dbl-click — drill · wheel — zoom') + '</div>';
        return;
    }
    var nd = frame.nodes[selI], gn = G.nodes[nd.ni];
    var neigh = adj[nd.ni].slice().sort(function (a, b) { return b[1] - a[1]; })
        .slice(0, 8);
    var rows = neigh.map(function (p) {
        var m = G.nodes[p[0]];
        return '<button class="b42g-jump" data-ni="' + p[0] + '" title="' +
               nodeName(m) + '"><span>' + nodeName(m) + '</span><em>' +
               p[1] + '</em></button>';
    }).join('');
    box.innerHTML =
        '<div class="b42g-sel"><b>' + nd.label + '</b> <span class="b42g-dim">' +
        gn.kind + '</span></div>' +
        '<div class="b42g-dim">' + gn.n + (RU ? ' статей · ' : ' articles · ') +
        adj[nd.ni].length + (RU ? ' связей' : ' links') + '</div>' +
        '<div style="margin:4px 0 7px"><a href="' + pageOf(gn) + '">' +
        pageLabel(gn) + '</a></div>' +
        '<div class="b42g-dim" style="margin-bottom:3px">' +
        (RU ? 'сильнейшие связи:' : 'strongest links:') + '</div>' + rows;
    box.querySelectorAll('.b42g-jump').forEach(function (b) {
        b.onclick = function () { showEgo(+b.dataset.ni); };
    });
}

function renderStats() {
    var box = el('b42g-stats');
    if (!box) return;
    var vis = visIdx();
    var nEdges = 0, wSum = 0;
    frame.edges.forEach(function (e) {
        if (e[2] >= view.minW && nodeVisible(frame.nodes[e[0]]) &&
            nodeVisible(frame.nodes[e[1]])) { nEdges++; wSum += e[2]; }
    });
    var byK = {};
    vis.forEach(function (i) {
        var b = frame.nodes[i].kind === '_group' ? null
                : bucketOf(frame.nodes[i].kind);
        if (b) byK[b] = (byK[b] || 0) + 1;
    });
    var maxK = 1;
    Object.keys(byK).forEach(function (k) { maxK = Math.max(maxK, byK[k]); });
    var bars = KINDS.filter(function (K) { return byK[K.k]; })
        .map(function (K) {
            var v = byK[K.k];
            return '<div class="b42g-bar" title="' + (RU ? K.ru : K.en) + ': ' +
                v + '"><i style="width:' + Math.round(v / maxK * 100) +
                '%;background:' + K.color + '"></i><span>' + v + '</span></div>';
        }).join('');
    box.innerHTML =
        '<div class="b42g-dim">' +
        vis.length + (RU ? ' узлов · ' : ' nodes · ') +
        nEdges + (RU ? ' рёбер · мощность ' : ' edges · power ') + wSum +
        '</div>' + bars;
}

function renderPath() {
    var box = el('b42g-path');
    if (!box) return;
    if (!path.length) {
        box.innerHTML = '<div class="b42g-dim">' +
            (RU ? 'пусто — начните с поиска или клика' : 'empty — search or click') +
            '</div>';
        return;
    }
    box.innerHTML = path.slice().reverse().map(function (ni) {
        return '<button class="b42g-jump" data-ni="' + ni + '"><span>' +
               nodeName(G.nodes[ni]) + '</span></button>';
    }).join('');
    box.querySelectorAll('.b42g-jump').forEach(function (b) {
        b.onclick = function () { showEgo(+b.dataset.ni); };
    });
}

function buildPanel() {
    var kb = el('b42g-kinds');
    if (kb) {
        KINDS.forEach(function (K) {
            var lab = document.createElement('label');
            lab.className = 'b42g-check';
            lab.title = RU ? K.ru : K.en;
            var cb = document.createElement('input');
            cb.type = 'checkbox'; cb.checked = true;
            cb.onchange = function () {
                kindOn[K.k] = cb.checked;
                if (view.layout !== 'force') applyFixedLayout();
                sim.alive = Math.max(sim.alive, 100);
                renderStats();
            };
            lab.appendChild(cb);
            var sw = document.createElement('canvas');
            sw.width = 18; sw.height = 18; sw.className = 'b42g-sw';
            var keep = ctx; ctx = sw.getContext('2d');
            drawNodeIcon(9, 9, 6, K, 1, false);
            ctx = keep;
            lab.appendChild(sw);
            var sp = document.createElement('span');
            sp.textContent = RU ? K.ru : K.en;
            lab.appendChild(sp);
            kb.appendChild(lab);
        });
    }
    /* разделы arXiv из данных — фильтр «через статьи» */
    var cb2 = el('b42g-cats');
    if (cb2) {
        var cats = {};
        G.nodes.forEach(function (nn) {
            if (nn.cat) cats[nn.cat] = (cats[nn.cat] || 0) + 1;
        });
        Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; })
            .forEach(function (cname) {
                var lab = document.createElement('label');
                lab.className = 'b42g-check';
                var cb = document.createElement('input');
                cb.type = 'checkbox'; cb.checked = true;
                cb.onchange = function () {
                    if (catOn === null) catOn = new Set(Object.keys(cats));
                    if (cb.checked) catOn.add(cname); else catOn.delete(cname);
                    if (catOn.size === Object.keys(cats).length) catOn = null;
                    sim.alive = Math.max(sim.alive, 100);
                    renderStats();
                };
                lab.appendChild(cb);
                var sp2 = document.createElement('span');
                sp2.textContent = cname + ' · ' + cats[cname];
                lab.appendChild(sp2);
                cb2.appendChild(lab);
            });
    }
    var allBtn = el('b42g-all');
    if (allBtn) allBtn.onclick = function () { stopDemo(); showAll(); };
    var gb = el('b42g-groups');
    if (gb) {
        var all = document.createElement('button');
        all.className = 'b42g-mini';
        all.textContent = RU ? 'все' : 'all';
        all.onclick = function () {
            groupOn = null;
            gb.querySelectorAll('input').forEach(function (c) { c.checked = true; });
            sim.alive = Math.max(sim.alive, 100);
            renderStats();
        };
        gb.appendChild(all);
        G.groups.forEach(function (g, i) {
            var lab = document.createElement('label');
            lab.className = 'b42g-check';
            lab.title = groupLabel(g);
            var cb = document.createElement('input');
            cb.type = 'checkbox'; cb.checked = true;
            cb.onchange = function () {
                if (groupOn === null) {
                    groupOn = new Set(G.groups.map(function (_, j) { return j; }));
                }
                if (cb.checked) groupOn.add(i); else groupOn.delete(i);
                if (groupOn.size === G.groups.length) groupOn = null;
                if (view.layout !== 'force') applyFixedLayout();
                sim.alive = Math.max(sim.alive, 100);
                renderStats();
            };
            lab.appendChild(cb);
            var t = document.createElement('span');
            t.className = 'b42g-ell';
            t.textContent = groupLabel(g) + ' · ' + g.members.length;
            lab.appendChild(t);
            gb.appendChild(lab);
        });
    }
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
    var b2 = el('b42g-2d'), b3 = el('b42g-3d'), sp = el('b42g-spin');
    if (b2) b2.onclick = function () {
        set3d(false); view.spin = false;
        if (sp) sp.classList.remove('active');
    };
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
            if (view.layout === 'force') seedLayout();
            else applyFixedLayout();
        };
    });
    var wr = el('b42g-w');
    if (wr) wr.addEventListener('input', function () {
        view.minW = +wr.value;
        var l = el('b42g-wv');
        if (l) l.textContent = '≥' + view.minW;
        igniteSparks();
        sim.alive = Math.max(sim.alive, 80);
        renderStats();
    });
    var home = el('b42g-home');
    if (home) home.onclick = function () { stopDemo(); showOverview(); };
    var dm = el('b42g-demo');
    if (dm) dm.onclick = function () {
        if (demo.on) stopDemo(); else startDemo();
    };
    set3d(false);
}

/* ── размер: весь экран ── */
function resize() {
    /* панели графа стоят под шапкой сайта — её высота меняется от языка и
       ширины экрана, поэтому меряем, а не гадаем (наложение поймано 27.08) */
    var tb = document.querySelector('.top-bar');
    if (tb) {
        document.documentElement.style.setProperty(
            '--b42g-top', Math.round(tb.getBoundingClientRect().bottom + 10) + 'px');
    }
    var r = canvas.parentElement.getBoundingClientRect();
    canvas.width = Math.max(300, r.width) * devicePixelRatio;
    canvas.height = Math.max(300, r.height) * devicePixelRatio;
}
window.addEventListener('resize', resize);
resize();
loop();
/* отладочное окно — смотреть состояние снаружи (глазами через консоль) */
window.B42G = {frame: function () { return frame; }, view: view,
               sim: sim, fit: fitView,
               demo: function (on) { on ? startDemo() : stopDemo(); },
               demoTick: demoTick,
               step: function (n) {           // синхронная прокрутка (тесты/фон)
                   for (var i = 0; i < (n || 60); i++) tick();
                   fitView();
                   view.zoom = view.zoomT; view.panX = view.panTX;
                   view.panY = view.panTY;
                   draw();
               }};
})();
