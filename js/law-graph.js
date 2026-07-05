// Граф закон↔тег (двудольный). Движок — force-graph.js.
(function () {
    var LAW_COLORS = { 'закон': '#C0392B', 'принцип': '#8E44AD', 'теорема': '#2471A3', 'эффект': '#B9770E', 'уравнение': '#148F77', 'теория': '#5D6D7E' };
    if (!window.createForceGraph) return;
    createForceGraph({
        canvas: 'lawcanvas', resizeKey: '__lawGraphResize',
        build: function (lang) {
            return Promise.all([
                fetch('/lang/' + lang + '/data/laws.json').then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/lang/' + lang + '/data/tags.json').then(function (r) { return r.json(); }).catch(function () { return {}; })
            ]).then(function (res) {
                var laws = res[0] || {}, tagNames = res[1] || {};
                var nodes = [], links = [], byKey = {};
                function ensureTag(tid) {
                    var key = 'tag:' + tid;
                    if (byKey[key] === undefined) {
                        byKey[key] = nodes.length;
                        nodes.push({ kind: 'tag', id: tid, name: (tagNames[tid] && tagNames[tid].name) || tid });
                    }
                    return byKey[key];
                }
                Object.keys(laws).forEach(function (lid) {
                    var tags = (laws[lid].tags || []).filter(function (t) { return tagNames[t]; });
                    var li = nodes.length;
                    nodes.push({ kind: 'law', id: lid, name: laws[lid].name || lid, type: laws[lid].type || 'закон' });
                    tags.forEach(function (tid) { links.push([li, ensureTag(tid)]); });
                });
                return { nodes: nodes, links: links };
            });
        },
        radius: function (n) { return n.kind === 'law' ? (6 + Math.min(n.deg, 12) * 0.8) : (3 + Math.min(n.deg, 14) * 0.6); },
        color: function (n) { return n.kind === 'law' ? (LAW_COLORS[n.type] || '#C0392B') : '#888'; },
        hollow: function (n) { return n.kind === 'tag'; },
        labelAlways: function (n) { return n.kind === 'law'; },
        href: function (n, lang) {
            return n.kind === 'law'
                ? '/lang/' + lang + '/laws/' + encodeURIComponent(n.id) + '.html'
                : '/lang/' + lang + '/tags/' + encodeURIComponent(n.id) + '.html';
        }
    });
})();
