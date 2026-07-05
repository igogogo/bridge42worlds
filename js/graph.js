// Граф тегов (тег↔тег по related). Движок — force-graph.js.
(function () {
    var TAG_COLORS = { concept: '#7F77DD', object: '#D85A30', substance: '#1D9E75', method: '#378ADD', instrument: '#BA7517' };
    if (!window.createForceGraph) return;
    createForceGraph({
        canvas: 'tgcanvas', resizeKey: '__graphResize',
        build: function (lang) {
            return Promise.all([
                fetch('/data/tags-graph.json').then(function (r) { return r.json(); }),
                fetch('/lang/' + lang + '/data/tags.json').then(function (r) { return r.json(); }).catch(function () { return {}; })
            ]).then(function (res) {
                var graph = res[0].graph || {}, names = res[1] || {}, ids = Object.keys(graph);
                var nodes = [], links = [], byId = {}, seen = {};
                ids.forEach(function (id) {
                    var g = graph[id];
                    if ((g.related || []).length === 0 && (g.article_count || 0) === 0) return;
                    byId[id] = nodes.length;
                    nodes.push({ id: id, name: (names[id] && names[id].name) || id, level: g.level || 'concept', educational: !!g.educational });
                });
                ids.forEach(function (id) {
                    (graph[id].related || []).forEach(function (rt) {
                        if (byId[id] === undefined || byId[rt] === undefined) return;
                        var a = byId[id], b = byId[rt], k = Math.min(a, b) + '_' + Math.max(a, b);
                        if (seen[k]) return; seen[k] = 1; links.push([a, b]);
                    });
                });
                return { nodes: nodes, links: links };
            });
        },
        radius: function (n) { return 4 + Math.min(n.deg, 16) * 0.7; },
        color: function (n) { return TAG_COLORS[n.level] || '#888'; },
        hollow: function (n) { return n.educational; },
        labelAlways: function () { return false; },
        href: function (n, lang) { return '/lang/' + lang + '/tags/' + encodeURIComponent(n.id) + '.html'; }
    });
})();
