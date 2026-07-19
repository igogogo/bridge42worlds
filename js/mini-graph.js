// Мини-граф bridge42worlds — три режима на одном движке (force-graph.js), фирменный подход
// один везде (юзер-фидбек 2026-07-15: "цинфицировать везде один поход"):
//  1) страница сущности (тег/закон/учёный): один центр + N-хоп соседи, data-node="t:x".
//  2) страница статьи: НЕСКОЛЬКО центров сразу (её теги+законы+учёные), data-node="t:x,l:y,s:Name".
//  3) страницы-облака (◉ на списках тегов/законов/учёных): без центра, data-node="" —
//     показываем весь knowledge-graph.json, отфильтрованный по типам узлов/рёбер, узлы без
//     ни одной видимой связи прячем (иначе тысячи точек без единой линии).
// Фильтр типов (.mg-kind/.mg-edge чекбоксы, если есть в разметке) — как на большом графе.
(function () {
    var box = document.querySelector('.mini-graph[data-node]');
    if (!box || !window.createForceGraph || !document.getElementById('minigraph')) return;
    var centersAttr = box.getAttribute('data-node') || '';
    var centers = centersAttr ? centersAttr.split(',').filter(Boolean) : [];
    var BUST = '?_=' + Date.now();
    var TAG_COLORS = { concept: '#7F77DD', object: '#D85A30', substance: '#1D9E75', method: '#378ADD', instrument: '#BA7517' };
    var LAW_COLORS = { 'закон': '#C0392B', 'принцип': '#8E44AD', 'теорема': '#2471A3', 'эффект': '#B9770E', 'уравнение': '#148F77', 'теория': '#5D6D7E' };
    var SCI_COLOR = '#2e7d32';
    var CAT_COLOR = '#B8860B';
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
        'tag-tag': ['tag-tag'], 'law-law': ['law-law'], 'sci-sci': ['sci-sci'], 'tag-cat': ['cat-tag']
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
                fetch('/lang/' + lang + '/data/scientists.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/data/arxiv-categories.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/data/arxiv-category-descriptions.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; })
            ]).then(function (res) {
                var kg = res[0], tn = res[1], ln = res[2], sn = res[3], cn = res[4], cd = res[5];
                var edgeTypes = checkedEdgeKgTypes();
                var visibleEdges = kg.edges.filter(function (e) { return !edgeTypes || edgeTypes[e.t]; });
                var kinds = checkedKinds();

                // BFS (мультиисточник — все центры на дистанции 0) на глубину __miniDepth, только по
                // рёбрам, прошедшим фильтр типов связи. В "облачном" режиме (centers пуст) BFS не
                // нужен — кандидаты все узлы, дальше отсекаем изолированные после фильтра рёбер.
                var dist = {};
                if (centers.length) {
                    var adj = {};
                    visibleEdges.forEach(function (e) {
                        (adj[e.a] = adj[e.a] || []).push(e.b);
                        (adj[e.b] = adj[e.b] || []).push(e.a);
                    });
                    var queue = centers.slice(), head = 0, depth = window.__miniDepth;
                    centers.forEach(function (c) { dist[c] = 0; });
                    while (head < queue.length) {
                        var cur = queue[head++], d = dist[cur];
                        if (d >= depth) continue;
                        (adj[cur] || []).forEach(function (nb) {
                            if (dist[nb] === undefined) { dist[nb] = d + 1; queue.push(nb); }
                        });
                    }
                }

                var idx = {}, nodes = [];
                kg.nodes.forEach(function (n) {
                    var isCenter = centers.indexOf(n.id) > -1;
                    if (centers.length && dist[n.id] === undefined) return;  // не облачный режим — держим BFS-границу
                    // Фильтр типов — центр страницы-сущности (один центр) не трогаем: скрывать сам
                    // предмет страницы по чекбоксу бессмысленно. На статье центров МНОГО (её теги+
                    // законы+учёные разом) — там чекбокс должен прятать лишнее и среди них тоже
                    // (юзер-фидбек 2026-07-17: "граф оказывается перегружен" тегами по умолчанию).
                    var exemptCenter = isCenter && centers.length <= 1;
                    if (kinds && !exemptCenter && !kinds[n.kind]) return;
                    var rawid = n.id.slice(2), name, tip;
                    if (n.kind === 'tag') {
                        var t = tn[rawid] || {};
                        name = t.name || rawid;
                        tip = t.mini || t.description_popular || t.description_simple || t.description || '';
                    } else if (n.kind === 'law') {
                        var l = ln[rawid] || {};
                        name = l.name || rawid;
                        tip = l.mini || l.description_popular || l.description_simple || l.description || '';
                    } else if (n.kind === 'cat') {
                        name = cn[rawid] || rawid;
                        tip = cd[rawid] || '';
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

                if (centers.length) return { nodes: nodes, links: links };

                // Облачный режим: без единой видимой связи узел — просто шум, прячем (юзер-фидбек
                // "неприкаянные сущности" — та же логика, что и у большого графа-эксплорера).
                var deg = {};
                links.forEach(function (l) { deg[l[0]] = (deg[l[0]] || 0) + 1; deg[l[1]] = (deg[l[1]] || 0) + 1; });
                var remap = {}, nodes2 = [];
                nodes.forEach(function (n, i) {
                    if (!deg[i]) return;
                    remap[i] = nodes2.length; nodes2.push(n);
                });
                var links2 = links
                    .filter(function (l) { return deg[l[0]] && deg[l[1]]; })
                    .map(function (l) { return [remap[l[0]], remap[l[1]]]; });
                return { nodes: nodes2, links: links2 };
            });
        },
        radius: function (n) { return n.center ? 9 : (3 + Math.min(n.deg, 16) * 0.7); },
        color: function (n) {
            return n.kind === 'tag' ? (TAG_COLORS[n.sub] || '#888')
                : n.kind === 'law' ? (LAW_COLORS[n.sub] || '#C0392B')
                : n.kind === 'cat' ? CAT_COLOR : SCI_COLOR;
        },
        hollow: function (n) { return n.kind === 'tag' && !n.center; },
        // Один центр (страница тега/закона/учёного) — узлов мало, подписываем все, как раньше.
        // Несколько центров (граф статьи) или облачный режим без центра — узлов может быть
        // много, подписываем только сами центры, соседей — по ховеру/степени (force-graph.js
        // сам покажет подпись при deg>=3), иначе на 10+ центрах подписи заливают весь холст.
        labelAlways: function (n) { return centers.length <= 1 || n.center; },
        tooltip: function (n) { return n.name + (n.tip ? ' — ' + n.tip : ''); },
        href: function (n, lang) {
            if (n.kind === 'tag') return '/lang/' + lang + '/tags/' + encodeURIComponent(n.rawid) + '.html';
            if (n.kind === 'law') return '/lang/' + lang + '/laws/' + encodeURIComponent(n.rawid) + '.html';
            if (n.kind === 'cat') return null;  // раздел arXiv не имеет своей страницы
            return '/lang/' + lang + '/scientists/' + encodeURIComponent(slug(n.rawid)) + '.html';
        }
    });

    // Кнопки +/- глубины (если есть в разметке — не на всех страницах обязательны; в облачном
    // режиме без центра глубина BFS не используется, кнопки там просто не вставляются в шаблон).
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
        'law,sci': 'law-sci', 'sci,law': 'law-sci',
        'tag,cat': 'tag-cat', 'cat,tag': 'tag-cat'
    };
    // Сам-на-себя рёбра — обычно юзер крутит их вручную (см. mg-edges), НО если включён РОВНО
    // один тип узлов, у категории (cat) вообще нет своего "сам-на-себя" ребра, а у tag/law/sci
    // кросс-рёбра не рисуются (не с кем — другие типы выключены). Без этого узлы единственного
    // включённого типа остаются без единой видимой связи — облачный режим прячет узлы без связей
    // как шум, и получается пустой холст (юзер-фидбек 2026-07-19: "если я выбираю только теги,
    // они не отображаются"). Раз тип — единственный, включаем его собственное ребро автоматически.
    var SELF_EDGE_OF = { tag: 'tag-tag', law: 'law-law', sci: 'sci-sci' };
    function edgeCheckbox(value) { return document.querySelector('.mg-edge[value="' + value + '"]'); }
    document.querySelectorAll('.mg-kind').forEach(function (kindBox) {
        kindBox.addEventListener('change', function () {
            var kinds = checkedKinds() || {};
            ['tag', 'law', 'sci', 'cat'].forEach(function (other) {
                if (other === kindBox.value) return;
                var edgeVal = CROSS_EDGE_OF[kindBox.value + ',' + other];
                var box = edgeCheckbox(edgeVal);
                if (!box) return;
                // Оба конца теперь отмечены — включаем связь; конец пропал — гасим.
                box.checked = !!(kinds[kindBox.value] && kinds[other]);
            });
            var activeKinds = Object.keys(kinds).filter(function (k) { return kinds[k]; });
            if (activeKinds.length === 1) {
                var selfBox = edgeCheckbox(SELF_EDGE_OF[activeKinds[0]]);
                if (selfBox) selfBox.checked = true;
            }
            if (window.__miniRebuild) window.__miniRebuild();
        });
    });
    // Рёбра-чекбоксы (кросс — авто, "сам-на-себя" — вручную) → просто перестроить.
    document.querySelectorAll('.mg-edge').forEach(function (c) {
        c.addEventListener('change', function () { if (window.__miniRebuild) window.__miniRebuild(); });
    });
})();
