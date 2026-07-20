// bridge42worlds · интерактивная карта-мозаика (treemap) для облака тегов/законов.
// Дефолтное представление: области науки (теги) / типы (законы) — плитки, размер = число статей.
// Клик по области → зум к её элементам; «назад» → к областям. Клик по элементу → его страница.
// Данные готовит сервер: window.__TREEMAP = { groups: [{key,label,count,color,children:[{name,url,count}]}] }.
(function () {
    var host = document.getElementById('treemap');
    var data = window.__TREEMAP;
    if (!host || !data || !data.groups) return;

    // ── squarified treemap: раскладка списка значений в прямоугольник ────────────────────────
    // Возвращает [{x,y,w,h,item}] для каждого item (item.value — вес). Классический алгоритм
    // Bruls/Huizing/van Wijk — стремится к квадратным ячейкам (читабельные подписи).
    function squarify(items, x, y, w, h) {
        var out = [];
        items = items.slice().sort(function (a, b) { return b.value - a.value; });
        var total = items.reduce(function (s, it) { return s + it.value; }, 0) || 1;
        var scale = (w * h) / total;
        var vals = items.map(function (it) { return { item: it, area: it.value * scale }; });

        function worst(row, side) {
            var s = row.reduce(function (a, r) { return a + r.area; }, 0);
            var mx = Math.max.apply(null, row.map(function (r) { return r.area; }));
            var mn = Math.min.apply(null, row.map(function (r) { return r.area; }));
            var s2 = s * s, side2 = side * side;
            return Math.max((side2 * mx) / s2, s2 / (side2 * mn));
        }
        var rx = x, ry = y, rw = w, rh = h, i = 0;
        while (i < vals.length) {
            var horizontal = rw >= rh;           // раскладываем вдоль короткой стороны
            var side = horizontal ? rh : rw;
            var row = [vals[i]];
            i++;
            while (i < vals.length) {
                var withNext = row.concat([vals[i]]);
                if (worst(withNext, side) <= worst(row, side)) { row = withNext; i++; }
                else break;
            }
            var rowArea = row.reduce(function (a, r) { return a + r.area; }, 0);
            var thick = rowArea / side;          // толщина полосы
            var off = 0;
            for (var k = 0; k < row.length; k++) {
                var cell = row[k].area / thick;  // длина ячейки вдоль полосы
                if (horizontal) out.push({ x: rx, y: ry + off, w: thick, h: cell, item: row[k].item });
                else out.push({ x: rx + off, y: ry, w: cell, h: thick, item: row[k].item });
                off += cell;
            }
            if (horizontal) { rx += thick; rw -= thick; } else { ry += thick; rh -= thick; }
        }
        return out;
    }

    var GAP = 3;
    var stack = [];  // хлебные крошки зума: [] = уровень областей, [group] = внутри области

    function textColor(bg) {
        // читаемый текст на плитке: тёмный на светлой, светлый на тёмной
        var m = /^#?([0-9a-f]{6})$/i.exec(bg || '');
        if (!m) return '#fff';
        var n = parseInt(m[1], 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
        return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? '#1a1a1a' : '#fff';
    }

    function tileHTML(rect, opts) {
        var it = rect.item;
        var pad = Math.min(rect.w, rect.h) > 46 ? 8 : 4;
        var showCount = rect.w > 54 && rect.h > 30 && it.count;
        var fs = Math.max(11, Math.min(17, Math.round(rect.w / 9)));
        var style = 'left:' + rect.x + 'px;top:' + rect.y + 'px;width:' + Math.max(0, rect.w - GAP) +
            'px;height:' + Math.max(0, rect.h - GAP) + 'px;background:' + it.color + ';color:' + textColor(it.color) +
            ';padding:' + pad + 'px;font-size:' + fs + 'px';
        var label = (rect.w > 34 && rect.h > 20) ?
            ('<span class="tm-label">' + it.label + (showCount ? ' <b class="tm-n">' + it.count + '</b>' : '') + '</span>') : '';
        var tag = opts.href ? 'a' : 'button';
        var attr = opts.href ? ('href="' + it.url + '"') : ('type="button" data-key="' + (it.key || '') + '"');
        return '<' + tag + ' class="tm-tile' + (opts.leaf ? ' tm-leaf' : '') + '" ' + attr +
            ' style="' + style + '" title="' + it.label + (it.count ? ' · ' + it.count : '') + '">' + label + '</' + tag + '>';
    }

    function render() {
        var r = host.getBoundingClientRect();
        var W = r.width, H = Math.max(320, Math.min(560, W * 0.62));
        host.style.height = H + 'px';
        var group = stack.length ? stack[0] : null;
        var items, leaf;
        if (group) {
            items = group.children.map(function (c) {
                return { value: Math.max(1, c.count || 1), label: c.name, count: c.count, url: c.url, color: group.color };
            });
            leaf = true;
        } else {
            items = data.groups.map(function (g) {
                return { value: Math.max(1, g.count || 1), label: g.label, count: g.count, key: g.key, color: g.color };
            });
            leaf = false;
        }
        var rects = squarify(items, 0, 0, W, H);
        var crumb = group
            ? '<button type="button" class="tm-back">‹ ' + (data.allLabel || 'all') + '</button><span class="tm-crumb">' + group.label + '</span>'
            : '';
        host.innerHTML = '<div class="tm-bar">' + crumb + '</div>' +
            '<div class="tm-stage" style="height:' + H + 'px">' +
            rects.map(function (rc) { return tileHTML(rc, { leaf: leaf, href: leaf }); }).join('') + '</div>';

        if (!group) {
            host.querySelectorAll('.tm-tile[data-key]').forEach(function (el) {
                el.addEventListener('click', function () {
                    var g = data.groups.filter(function (x) { return x.key === el.getAttribute('data-key'); })[0];
                    if (g && g.children && g.children.length) { stack = [g]; render(); }
                });
            });
        } else {
            var back = host.querySelector('.tm-back');
            if (back) back.addEventListener('click', function () { stack = []; render(); });
        }
    }

    render();
    var rt;
    window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(render, 150); });
    window.__treemapRender = render;  // для показа при переключении вида
})();
