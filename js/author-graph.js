// Мини-граф тем автора: центральный узел-автор + теги его статей, встроенный в текст.
// Рёбра: автор→каждый тег, плюс связи тег-тег из knowledge-graph.json среди этих тегов.
// Контейнер: <div class="mini-graph" data-author="Name" data-tags="tag1,tag2,..."><canvas id="minigraph"></canvas></div>
(function () {
    var box = document.querySelector('.mini-graph[data-tags]');
    if (!box || !window.createForceGraph || !document.getElementById('minigraph')) return;
    var author = box.getAttribute('data-author') || '';
    var tags = (box.getAttribute('data-tags') || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    if (!tags.length) return;
    var BUST = '?_=' + Date.now();
    var TAG_COLOR = '#6C5CE7';  // тег — единый цвет типа (синхронно с mini-graph.js KIND_COLORS)

    createForceGraph({
        canvas: 'minigraph', resizeKey: '__authorGraphResize',
        build: function (lang) {
            return Promise.all([
                fetch('/data/knowledge-graph.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return { nodes: [], edges: [] }; }),
                fetch('/lang/' + lang + '/data/tags.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; })
            ]).then(function (res) {
                var kg = res[0], tn = res[1];
                var sub = {};  // tag id -> level/sub из KG
                kg.nodes.forEach(function (n) { if (n.kind === 'tag') sub[n.id.slice(2)] = n.sub; });
                var tagSet = {};
                tags.forEach(function (t) { tagSet[t] = 1; });
                var nodes = [{ rawid: '', name: author, kind: 'author', center: true }];
                var idx = {};
                tags.forEach(function (t) {
                    idx[t] = nodes.length;
                    nodes.push({ rawid: t, name: (tn[t] && tn[t].name) || t, kind: 'tag', sub: sub[t] });
                });
                var links = [];
                tags.forEach(function (t) { links.push([0, idx[t]]); });  // автор → тег
                // связи тег-тег среди тегов автора
                kg.edges.forEach(function (e) {
                    if (e.a && e.b && e.a.slice(0, 2) === 't:' && e.b.slice(0, 2) === 't:') {
                        var a = e.a.slice(2), b = e.b.slice(2);
                        if (tagSet[a] && tagSet[b] && idx[a] !== undefined && idx[b] !== undefined) links.push([idx[a], idx[b]]);
                    }
                });
                return { nodes: nodes, links: links };
            });
        },
        radius: function (n) { return n.center ? 9 : 5; },
        color: function (n) { return n.kind === 'author' ? '#444' : TAG_COLOR; },
        hollow: function (n) { return n.kind === 'tag'; },
        labelAlways: function () { return true; },
        href: function (n, lang) {
            if (n.kind === 'tag') return '/lang/' + lang + '/tags/' + encodeURIComponent(n.rawid) + '.html';
            return null;
        }
    });
})();
