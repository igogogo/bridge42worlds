// Граф учёный↔тег (двудольный). Движок — force-graph.js.
(function () {
    var SCI_COLOR = '#2e7d32';
    var TAG_COLORS = { concept: '#7F77DD', object: '#D85A30', substance: '#1D9E75', method: '#378ADD', instrument: '#BA7517' };
    if (!window.createForceGraph) return;
    function slug(name) { return name.replace(/ /g, '_').replace(/\./g, ''); }
    createForceGraph({
        canvas: 'scicanvas', resizeKey: '__sciGraphResize',
        build: function (lang) {
            return Promise.all([
                fetch('/lang/' + lang + '/data/scientists.json').then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/lang/' + lang + '/data/tags.json').then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/data/tags-graph.json').then(function (r) { return r.json(); }).catch(function () { return { graph: {} }; })
            ]).then(function (res) {
                var scientists = res[0] || {}, tagNames = res[1] || {}, tagGraph = (res[2] && res[2].graph) || {};
                var nodes = [], links = [], byKey = {};
                function ensureTag(tid) {
                    var key = 'tag:' + tid;
                    if (byKey[key] === undefined) {
                        byKey[key] = nodes.length;
                        nodes.push({ kind: 'tag', id: tid, name: (tagNames[tid] && tagNames[tid].name) || tid, level: (tagGraph[tid] && tagGraph[tid].level) || 'concept' });
                    }
                    return byKey[key];
                }
                Object.keys(scientists).forEach(function (name) {
                    var rel = (scientists[name].related_tags || []).filter(function (t) { return tagGraph[t]; });
                    if (!rel.length) return;
                    var si = nodes.length;
                    nodes.push({ kind: 'sci', id: name, name: scientists[name].name || name });
                    rel.forEach(function (tid) { links.push([si, ensureTag(tid)]); });
                });
                return { nodes: nodes, links: links };
            });
        },
        radius: function (n) { return n.kind === 'sci' ? (6 + Math.min(n.deg, 12) * 0.8) : (3 + Math.min(n.deg, 14) * 0.6); },
        color: function (n) { return n.kind === 'sci' ? SCI_COLOR : (TAG_COLORS[n.level] || '#888'); },
        hollow: function (n) { return n.kind === 'tag'; },
        labelAlways: function (n) { return n.kind === 'sci'; },
        href: function (n, lang) {
            return n.kind === 'sci'
                ? '/lang/' + lang + '/scientists/' + encodeURIComponent(slug(n.id)) + '.html'
                : '/lang/' + lang + '/tags/' + encodeURIComponent(n.id) + '.html';
        }
    });
})();
