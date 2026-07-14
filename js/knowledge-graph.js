// Единый граф знаний: теги ⇄ законы ⇄ учёные. Движок — force-graph.js.
// Фильтр по типам УЗЛОВ (.kg-kind: tag/law/sci) и РЁБЕР (.kg-edge: 6 типов) — чекбоксы + пресеты.
(function () {
    if (!window.createForceGraph) return;
    var TAG_COLORS = { concept: '#7F77DD', object: '#D85A30', substance: '#1D9E75', method: '#378ADD', instrument: '#BA7517' };
    var LAW_COLORS = { 'закон': '#C0392B', 'принцип': '#8E44AD', 'теорема': '#2471A3', 'эффект': '#B9770E', 'уравнение': '#148F77', 'теория': '#5D6D7E' };
    var SCI_COLOR = '#2e7d32';

    var BUST = '?_=' + Date.now();  // данные меняются при регенерации — не даём браузеру отдать старое
    function slug(name) { return name.replace(/ /g, '_').replace(/\./g, ''); }
    function checked(cls) {
        var s = {};
        document.querySelectorAll('.' + cls + ':checked').forEach(function (c) { s[c.value] = 1; });
        return s;
    }

    // Резолвит отображаемое имя узла (учёный: id — само имя, тег/закон — по справочнику).
    function resolveName(n, tn, ln) {
        var rawid = n.id.slice(2);
        if (n.kind === 'tag') return (tn[rawid] && tn[rawid].name) || rawid;
        if (n.kind === 'law') return (ln[rawid] && ln[rawid].name) || rawid;
        return rawid;
    }

    // Мульти-корневой эго-граф: BFS на заданную глубину от КАЖДОГО выбранного узла (может
    // быть несколько чипов тег/закон/учёный сразу). Больше одного корня — всегда пересечение
    // («И»): показываем то, что достижимо на этой глубине от ВСЕХ корней разом — кросс-фильтр,
    // а не объединение (было ИЛИ/И тумблером — убрали по фидбеку, слишком путало выбор).
    // Игнорирует чекбоксы типов/связей — «получить нужный срез» вокруг сущностей, а не по типу.
    function bfsReachable(adj, rootId, depth) {
        var dist = {}; dist[rootId] = 0;
        var queue = [rootId], head = 0;
        while (head < queue.length) {
            var cur = queue[head++], d = dist[cur];
            if (d >= depth) continue;
            (adj[cur] || []).forEach(function (nb) {
                if (dist[nb] === undefined) { dist[nb] = d + 1; queue.push(nb); }
            });
        }
        return dist;
    }
    function multiRootGraph(kg, rootIds, depth, tn, ln) {
        var adj = {};
        kg.edges.forEach(function (e) {
            (adj[e.a] = adj[e.a] || []).push(e.b);
            (adj[e.b] = adj[e.b] || []).push(e.a);
        });
        var sets = rootIds.map(function (id) { return bfsReachable(adj, id, depth); });
        var resultIds;
        if (sets.length > 1) {
            resultIds = Object.keys(sets[0]).filter(function (id) {
                return sets.every(function (s) { return s[id] !== undefined; });
            });
            // Пустое пересечение — не связаны на этой глубине. Не схлопываем граф в пустоту молча,
            // показываем хотя бы сами выбранные корни (глубину можно увеличить +).
            if (!resultIds.length) resultIds = rootIds.slice();
        } else {
            resultIds = Object.keys(sets[0]);
        }
        var byId = {};
        kg.nodes.forEach(function (n) { byId[n.id] = n; });
        var idx = {}, nodes = [];
        resultIds.forEach(function (id) {
            var n = byId[id];
            if (!n) return;
            idx[id] = nodes.length;
            nodes.push({ rawid: n.id.slice(2), name: resolveName(n, tn, ln), kind: n.kind, sub: n.sub });
        });
        var links = [];
        kg.edges.forEach(function (e) {
            if (idx[e.a] !== undefined && idx[e.b] !== undefined) links.push([idx[e.a], idx[e.b]]);
        });
        return { nodes: nodes, links: links };
    }

    // Поиск — СВОЙ словарь имён на каждый тип (тег/закон/учёный): один общий список на ~150
    // узлов путал бы подсказки. Своя выпадашка вместо нативного datalist — нужен контроль
    // сортировки (по алфавиту) и подстрочного поиска (не только по префиксу).
    var nameToId = { tag: {}, law: {}, sci: {} };
    var idToName = {};
    var kgEdgesCache = null;

    function kindOf(id) { return id[0] === 't' ? 'tag' : id[0] === 'l' ? 'law' : 'sci'; }

    // Прямые соседи узла по рёбрам графа, сгруппированные по типу — НЕ зависит от глубины
    // (глубина — только для визуализации эго-графа, кросс-фильтр подсказок отдельно).
    function relatedIds(rootId) {
        var rel = { tag: {}, law: {}, sci: {} };
        (kgEdgesCache || []).forEach(function (e) {
            var other = e.a === rootId ? e.b : (e.b === rootId ? e.a : null);
            if (other) rel[kindOf(other)][other] = 1;
        });
        return rel;
    }

    // Множественный выбор: чипы вместо одного значения поля. window.__kgSelected — id-множества
    // по типам. Комбинация всегда «И» (кросс-фильтр) — см. multiRootGraph выше.
    window.__kgSelected = window.__kgSelected || { tag: {}, law: {}, sci: {} };

    function selectedIds() {
        var ids = [];
        Object.keys(window.__kgSelected).forEach(function (k) {
            Object.keys(window.__kgSelected[k]).forEach(function (id) { ids.push(id); });
        });
        return ids;
    }

    function renderChips() {
        var box = document.getElementById('kg-chips-all');
        if (!box) return;
        box.innerHTML = '';
        var frag = document.createDocumentFragment();
        ['tag', 'law', 'sci'].forEach(function (kind) {
            Object.keys(window.__kgSelected[kind]).forEach(function (id) {
                var chip = document.createElement('span');
                chip.className = 'kg-chip';
                chip.setAttribute('data-kind', kind);
                chip.textContent = idToName[id] || id;
                var x = document.createElement('button');
                x.type = 'button'; x.className = 'kg-chip-x';
                x.textContent = '×';
                x.addEventListener('click', function () { removeChip(kind, id); });
                chip.appendChild(x);
                frag.appendChild(chip);
            });
        });
        box.appendChild(frag);
    }

    function addChip(kind, id) {
        window.__kgSelected[kind][id] = 1;
        renderChips();
        if (window.__kgRebuild) window.__kgRebuild();
    }
    function removeChip(kind, id) {
        delete window.__kgSelected[kind][id];
        renderChips();
        if (window.__kgRebuild) window.__kgRebuild();
    }

    createForceGraph({
        canvas: 'kgcanvas', resizeKey: '__kgResize', rebuildKey: '__kgRebuild',
        build: function (lang) {
            return Promise.all([
                fetch('/data/knowledge-graph.json' + BUST).then(function (r) { return r.json(); }),
                fetch('/lang/' + lang + '/data/tags.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/lang/' + lang + '/data/laws.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; }),
                fetch('/lang/' + lang + '/data/scientists.json' + BUST).then(function (r) { return r.json(); }).catch(function () { return {}; })
            ]).then(function (res) {
                var kg = res[0], tn = res[1], ln = res[2];
                kgEdgesCache = kg.edges;

                kg.nodes.forEach(function (n) {
                    if (!nameToId[n.kind]) return;
                    var name = resolveName(n, tn, ln);
                    nameToId[n.kind][name] = n.id;
                    idToName[n.id] = name;
                });

                var roots = selectedIds();
                if (roots.length) {
                    return multiRootGraph(kg, roots, window.__kgDepth || 1, tn, ln);
                }

                var kinds = checked('kg-kind'), edges = checked('kg-edge');
                var idx = {}, nodes = [];
                kg.nodes.forEach(function (n) {
                    if (!kinds[n.kind]) return;
                    idx[n.id] = nodes.length;
                    nodes.push({ rawid: n.id.slice(2), name: resolveName(n, tn, ln), kind: n.kind, sub: n.sub });
                });
                var links = [];
                kg.edges.forEach(function (e) {
                    if (!edges[e.t]) return;
                    if (idx[e.a] === undefined || idx[e.b] === undefined) return;
                    links.push([idx[e.a], idx[e.b]]);
                });
                return { nodes: nodes, links: links };
            });
        },
        radius: function (n) { return (n.kind === 'tag') ? (3 + Math.min(n.deg, 14) * 0.6) : (5 + Math.min(n.deg, 12) * 0.7); },
        color: function (n) {
            return n.kind === 'tag' ? (TAG_COLORS[n.sub] || '#888')
                : n.kind === 'law' ? (LAW_COLORS[n.sub] || '#C0392B') : SCI_COLOR;
        },
        hollow: function (n) { return n.kind === 'tag'; },
        labelAlways: function () { return true; },  // подписываем и теги (по умолчанию их немного — пресет «каркас»)
        href: function (n, lang) {
            if (n.kind === 'tag') return '/lang/' + lang + '/tags/' + encodeURIComponent(n.rawid) + '.html';
            if (n.kind === 'law') return '/lang/' + lang + '/laws/' + encodeURIComponent(n.rawid) + '.html';
            return '/lang/' + lang + '/scientists/' + encodeURIComponent(slug(n.rawid)) + '.html';
        }
    });

    // Чекбоксы → перестроить граф.
    document.addEventListener('change', function (e) {
        var t = e.target;
        if (t.classList && (t.classList.contains('kg-kind') || t.classList.contains('kg-edge'))) {
            if (window.__kgRebuild) window.__kgRebuild();
        }
    });

    // Поиск: своя выпадашка подсказок на поле (не нативный datalist) — список меняется на
    // каждое нажатие клавиши (поиск по вхождению, не только с начала), отсортирован по
    // алфавиту. Пока хоть что-то выбрано — подсказки во ВСЕХ полях сужаются до пересечения
    // прямых соседей уже выбранного (кросс-фильтр, включается автоматически с первого чипа).
    var searchInputs = { tag: document.getElementById('kg-search-tag'), law: document.getElementById('kg-search-law'), sci: document.getElementById('kg-search-sci') };
    var SUGGEST_BOXES = { tag: 'kg-suggest-tag', law: 'kg-suggest-law', sci: 'kg-suggest-sci' };
    var hlIndex = { tag: -1, law: -1, sci: -1 };
    var SUGGEST_LIMIT = 40;

    function candidateNames(kind) {
        // Кросс-фильтр сужает поле ТОЛЬКО от выбора в ДРУГИХ типах (набрал теги → сузились
        // законы/учёные), но не от выбора в своём же типе — свободно набираем сколько угодно
        // тегов подряд, список тегов от этого не мельчает.
        var ids = selectedIds().filter(function (id) { return kindOf(id) !== kind; });
        var allowed = null;
        if (ids.length) {
            var relSets = ids.map(relatedIds);
            var candIds = Object.keys(relSets[0][kind] || {});
            for (var i = 1; i < relSets.length; i++) {
                var s = relSets[i][kind] || {};
                candIds = candIds.filter(function (id) { return s[id]; });
            }
            allowed = {};
            candIds.forEach(function (id) { allowed[idToName[id]] = 1; });
        }
        return Object.keys(nameToId[kind]).filter(function (n) {
            var id = nameToId[kind][n];
            if (window.__kgSelected[kind][id]) return false;  // уже выбран — не предлагаем повторно
            if (allowed && !allowed[n]) return false;
            return true;
        }).sort(function (a, b) { return a.localeCompare(b, undefined, { sensitivity: 'base' }); });
    }

    function closeSuggest(kind) {
        var box = document.getElementById(SUGGEST_BOXES[kind]);
        if (box) { box.classList.remove('open'); box.innerHTML = ''; }
        hlIndex[kind] = -1;
    }

    function pick(kind, name) {
        var id = nameToId[kind][name];
        if (!id) return;
        if (searchInputs[kind]) searchInputs[kind].value = '';
        closeSuggest(kind);
        addChip(kind, id);
    }

    function highlight(kind) {
        var box = document.getElementById(SUGGEST_BOXES[kind]);
        if (!box) return;
        var items = box.querySelectorAll('.kg-suggest-item');
        items.forEach(function (it, i) { it.classList.toggle('hl', i === hlIndex[kind]); });
        if (hlIndex[kind] >= 0 && items[hlIndex[kind]]) items[hlIndex[kind]].scrollIntoView({ block: 'nearest' });
    }

    function renderSuggest(kind, query) {
        var box = document.getElementById(SUGGEST_BOXES[kind]);
        if (!box) return;
        var q = (query || '').trim().toLowerCase();
        var names = candidateNames(kind).filter(function (n) { return !q || n.toLowerCase().indexOf(q) !== -1; });
        hlIndex[kind] = -1;
        box.innerHTML = '';
        if (!names.length) {
            box.classList.remove('open');
            return;
        }
        var frag = document.createDocumentFragment();
        names.slice(0, SUGGEST_LIMIT).forEach(function (n) {
            var item = document.createElement('div');
            item.className = 'kg-suggest-item';
            item.textContent = n;
            item.addEventListener('mousedown', function (e) { e.preventDefault(); pick(kind, n); });
            frag.appendChild(item);
        });
        box.appendChild(frag);
        box.classList.add('open');
    }

    var depthVal = document.getElementById('kg-depth-val');
    window.__kgDepth = window.__kgDepth || 1;
    function setDepth(d) {
        window.__kgDepth = Math.max(1, Math.min(4, d));
        if (depthVal) depthVal.textContent = window.__kgDepth;
        if (selectedIds().length && window.__kgRebuild) window.__kgRebuild();
    }
    function clearSearch() {
        window.__kgSelected = { tag: {}, law: {}, sci: {} };
        Object.keys(searchInputs).forEach(function (k) { if (searchInputs[k]) searchInputs[k].value = ''; closeSuggest(k); });
        renderChips();
    }
    Object.keys(searchInputs).forEach(function (kind) {
        var inp = searchInputs[kind];
        if (!inp) return;
        inp.addEventListener('input', function () { renderSuggest(kind, inp.value); });
        inp.addEventListener('focus', function () { renderSuggest(kind, inp.value); });
        inp.addEventListener('blur', function () { setTimeout(function () { closeSuggest(kind); }, 150); });
        inp.addEventListener('keydown', function (e) {
            var box = document.getElementById(SUGGEST_BOXES[kind]);
            var items = box ? box.querySelectorAll('.kg-suggest-item') : [];
            if (!items.length) return;
            if (e.key === 'ArrowDown') { e.preventDefault(); hlIndex[kind] = Math.min(hlIndex[kind] + 1, items.length - 1); highlight(kind); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); hlIndex[kind] = Math.max(hlIndex[kind] - 1, 0); highlight(kind); }
            else if (e.key === 'Enter') { e.preventDefault(); pick(kind, items[hlIndex[kind] >= 0 ? hlIndex[kind] : 0].textContent); }
            else if (e.key === 'Escape') { closeSuggest(kind); }
        });
    });
    var clearBtn = document.getElementById('kg-search-clear');
    if (clearBtn) clearBtn.addEventListener('click', function () { clearSearch(); if (window.__kgRebuild) window.__kgRebuild(); });
    var minusBtn = document.getElementById('kg-depth-minus');
    if (minusBtn) minusBtn.addEventListener('click', function () { setDepth(window.__kgDepth - 1); });
    var plusBtn = document.getElementById('kg-depth-plus');
    if (plusBtn) plusBtn.addEventListener('click', function () { setDepth(window.__kgDepth + 1); });

    // Пресеты: выставляют нужные рёбра и вовлечённые типы узлов.
    var PRESETS = {
        // «каркас» — дефолт: законы+учёные и связи МЕЖДУ ними (не внутри типа), БЕЗ тегов
        // (не грузим весь хайрбол сразу)
        core: ['law-sci'],
        all: ['tag-tag', 'law-law', 'sci-sci', 'law-tag', 'sci-tag', 'law-sci'],
        tags: ['tag-tag'], laws: ['law-law', 'law-tag'], sci: ['sci-tag', 'sci-sci'],
        'tag-sci': ['sci-tag'], 'law-sci': ['law-sci'], 'law-tag': ['law-tag']
    };
    window.kgPreset = function (name) {
        clearSearch();  // пресеты — это фильтр по типу, эго-режим поиска им не мешает молча
        var set = PRESETS[name] || PRESETS.all;
        var kinds = {};
        set.forEach(function (tp) { tp.split('-').forEach(function (k) { kinds[k] = 1; }); });
        document.querySelectorAll('.kg-edge').forEach(function (c) { c.checked = set.indexOf(c.value) !== -1; });
        document.querySelectorAll('.kg-kind').forEach(function (c) { c.checked = !!kinds[c.value]; });
        if (window.__kgRebuild) window.__kgRebuild();
    };
})();
