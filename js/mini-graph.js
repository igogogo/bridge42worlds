// Мини-граф на странице сущности (тег/закон/учёный): узел + его N-хоп соседи из
// knowledge-graph.json (глубина управляется кнопками +/-, как на большом графе). Движок — force-graph.js.
// Контейнер: <div class="mini-graph" data-node="t:tagid|l:lawid|s:Name"><canvas id="minigraph"></canvas></div>
// Фильтр типов (.mg-kind чекбоксы, если есть в разметке) — как на большом графе, но центр
// всегда показан независимо от галочек (спрятать сам узел страницы было бы бессмысленно).
(function () {
    var box = document.querySelector('.mini-graph[data-node]');
    if (!box || !window.createForceGraph || !document.getElementById('minigraph')) return;
    var center = box.getAttribute('data-node');
    var BUST = '?_=' + Date.now();
    var TAG_COLORS = { concept: '#7F77DD', object: '#D85A30', substance: '#1D9E75', method: '#378ADD', instrument: '#BA7517' };
    var LAW_COLORS = { 'закон': '#C0392B', 'принцип': '#8E44AD', 'теорема': '#2471A3', 'эффект': '#B9770E', 'уравнение': '#148F77', 'теория': '#5D6D7E' };
    var SCI_COLOR = '#2e7d32';
    function slug(n) { return n.replace(/ /g, '_').replace(/\./g, ''); }

    window.__miniDepth = window.__miniDepth || 1;

    function checkedKinds() {
        var boxes = document.querySelectorAll('.mg-kind');
        if (!boxes.length) return null;  // разметки нет на этой странице — фильтр не активен, показываем всё
        var s = {};
        boxes.forEach(function (c) { if (c.checked) s[c.value] = 1; });
        return s;
    }

    // Типы рёбер (.mg-edge, если есть): null = разметки нет, показываем все рёбра как раньше.
    // "tag-law"/"tag-sci"/"law-sci" — компактные ярлыки чекбоксов; в graph.json кросс-рёбра
    // называются иначе (law-tag/sci-tag/law-sci) + law-sci заодно покрывает law-influence
    // (мини-граф не различает "открыл" от "оказал влияние" — упрощение для компактного вида).
    var EDGE_KG_TYPES = {
        'tag-law': ['law-tag'], 'tag-sci': ['sci-tag'], 'law-sci': ['law-sci', 'law-influence'],
        'tag-tag': ['tag-tag'], 'law-law': ['law-law'], 'sci-sci': ['sci-sci']
    };
    function checkedEdgeKgTypes() {
        var boxes = document.querySelectorAll('.mg-edge');
        if (!boxes.length) return null;
        var s = {};
        boxes.forEach(function (c) {
            if (!c.checked) return;
            (EDGE_KG_TYPES[c.value] || []).forEach(function (t) { s[t] = 1; });
        });
        return s;
    }

    createForceGraph({
        canvas: 'minigraph', resizeKey: '__miniResize', rebuildKey: '__miniRebuild',
        build: function (lang) {
            return Promise.all([
                fetch('/data/knowledge-graph.json' + BUST).then(function (r) { return r.json(); }),
                fetch('/lang/' + lang + '/data/tags.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/lang/' + lang + '/data/laws.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/lang/' + lang + '/data/scientists.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; })
            ]).then(function (res) {
                var kg = res[0], tn = res[1], ln = res[2], sn = res[3];
                var edgeTypes = checkedEdgeKgTypes();
                var visibleEdges = kg.edges.filter(function (e) { return !edgeTypes || edgeTypes[e.t]; });
                // BFS от центра на глубину __miniDepth (1 хоп по умолчанию — как раньше), только
                // по рёбрам, прошедшим фильтр типов связи — иначе узел мог бы остаться виден без
                // единой видимой линии к нему (нашёлся бы по скрытому ребру другого типа).
                var adj = {};
                visibleEdges.forEach(function (e) {
                    (adj[e.a] = adj[e.a] || []).push(e.b);
                    (adj[e.b] = adj[e.b] || []).push(e.a);
                });
                var dist = {}; dist[center] = 0;
                var queue = [center], head = 0, depth = window.__miniDepth;
                while (head < queue.length) {
                    var cur = queue[head++], d = dist[cur];
                    if (d >= depth) continue;
                    (adj[cur] || []).forEach(function (nb) {
                        if (dist[nb] === undefined) { dist[nb] = d + 1; queue.push(nb); }
                    });
                }
                var kinds = checkedKinds();
                var idx = {}, nodes = [];
                kg.nodes.forEach(function (n) {
                    if (dist[n.id] === undefined) return;
                    var isCenter = n.id === center;
                    if (kinds && !isCenter && !kinds[n.kind]) return;  // фильтр типов — центр не трогаем
                    var rawid = n.id.slice(2), name, tip;
                    if (n.kind === 'tag') {
                        var t = tn[rawid] || {};
                        name = t.name || rawid;
                        tip = t.mini || t.description_popular || t.description_simple || t.description || '';
                    } else if (n.kind === 'law') {
                        var l = ln[rawid] || {};
                        name = l.name || rawid;
                        tip = l.mini || l.description_popular || l.description_simple || l.description || '';
                    } else {
                        name = rawid;
                        tip = (sn[rawid] || {}).description || '';
                    }
                    idx[n.id] = nodes.length;
                    nodes.push({ rawid: rawid, name: name, kind: n.kind, sub: n.sub, center: isCenter, tip: tip });
                });
                var links = [];
                visibleEdges.forEach(function (e) {
                    if (idx[e.a] !== undefined && idx[e.b] !== undefined) links.push([idx[e.a], idx[e.b]]);
                });
                return { nodes: nodes, links: links };
            });
        },
        radius: function (n) { return n.center ? 9 : (n.kind === 'tag' ? 4 : 6); },
        color: function (n) {
            return n.kind === 'tag' ? (TAG_COLORS[n.sub] || '#888')
                : n.kind === 'law' ? (LAW_COLORS[n.sub] || '#C0392B') : SCI_COLOR;
        },
        hollow: function (n) { return n.kind === 'tag' && !n.center; },
        labelAlways: function () { return true; },  // соседей мало — подписываем все
        tooltip: function (n) { return n.name + (n.tip ? ' — ' + n.tip : ''); },
        href: function (n, lang) {
            if (n.kind === 'tag') return '/lang/' + lang + '/tags/' + encodeURIComponent(n.rawid) + '.html';
            if (n.kind === 'law') return '/lang/' + lang + '/laws/' + encodeURIComponent(n.rawid) + '.html';
            return '/lang/' + lang + '/scientists/' + encodeURIComponent(slug(n.rawid)) + '.html';
        }
    });

    // Кнопки +/- глубины (если есть в разметке — не на всех страницах обязательны).
    var depthVal = document.getElementById('mini-depth-val');
    function setMiniDepth(d) {
        window.__miniDepth = Math.max(1, Math.min(4, d));
        if (depthVal) depthVal.textContent = window.__miniDepth;
        if (window.__miniRebuild) window.__miniRebuild();
    }
    var minus = document.getElementById('mini-depth-minus');
    if (minus) minus.addEventListener('click', function () { setMiniDepth(window.__miniDepth - 1); });
    var plus = document.getElementById('mini-depth-plus');
    if (plus) plus.addEventListener('click', function () { setMiniDepth(window.__miniDepth + 1); });

    // Чекбоксы типов узлов → перестроить + авто-переключить КРОСС-рёбра (не "сам-на-себя" —
    // те юзер крутит вручную, см. mg-edges). Тип X только что появился среди отмеченных типов —
    // включаем связи X с каждым уже отмеченным ДРУГИМ типом; тип X пропал — гасим все рёбра,
    // где он участвует (юзер-фидбек 2026-07-15: "тот же принцип... на каждый тип одинаково").
    var CROSS_EDGE_OF = {
        'tag,law': 'tag-law', 'law,tag': 'tag-law',
        'tag,sci': 'tag-sci', 'sci,tag': 'tag-sci',
        'law,sci': 'law-sci', 'sci,law': 'law-sci'
    };
    function edgeCheckbox(value) { return document.querySelector('.mg-edge[value="' + value + '"]'); }
    document.querySelectorAll('.mg-kind').forEach(function (kindBox) {
        kindBox.addEventListener('change', function () {
            var kinds = checkedKinds() || {};
            ['tag', 'law', 'sci'].forEach(function (other) {
                if (other === kindBox.value) return;
                var edgeVal = CROSS_EDGE_OF[kindBox.value + ',' + other];
                var box = edgeCheckbox(edgeVal);
                if (!box) return;
                // Оба конца теперь отмечены — включаем связь; конец пропал — гасим.
                box.checked = !!(kinds[kindBox.value] && kinds[other]);
            });
            if (window.__miniRebuild) window.__miniRebuild();
        });
    });
    // Рёбра-чекбоксы (кросс — авто, "сам-на-себя" — вручную) → просто перестроить.
    document.querySelectorAll('.mg-edge').forEach(function (c) {
        c.addEventListener('change', function () { if (window.__miniRebuild) window.__miniRebuild(); });
    });
})();
