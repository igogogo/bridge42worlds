/* b42-mini — мини-граф на странице статьи, понятия и формулы.

   Владелец 27.08: «старый заменить нашим простым вариантом — он просто
   показывает структуру с точки зрения статьи с учётом её внутренних связей
   первого уровня» и «продумай мобильный: объекты меньше, ограничение по
   количеству — заменяем граф на наш везде».

   ПРОСТОЙ ВАРИАНТ, без панелей и режимов: узлы статьи (её понятия и формулы),
   рёбра — только МЕЖДУ НИМИ (первый уровень, ничего чужого не подмешиваем),
   мощность = число общих статей. Наведение — имя и класс, клик — страница
   понятия, «весь граф →» уводит в большое приложение на этом же фокусе.

   Рисует ядро js/b42-graph-core.js — тот же визуальный язык, что у большого
   графа: формы классов, цвета, штрихи, дуги-струны.

   Разметка:
     <div class="b42mini" data-ids="black_hole,event_horizon,f:kerr_metric"
          data-focus="black_hole"></div>
   Мобильный: сам режет число узлов и мельчит значки по ширине холста. */
(function () {
'use strict';

var boxes = document.querySelectorAll('.b42mini[data-ids]');
if (!boxes.length || !window.B42GraphCore) return;
var CORE = window.B42GraphCore;
var LANG = document.documentElement.lang || 'en';
/* «статей» на языке страницы. Мини-граф показывает эту подпись у каждого узла
   под курсором, и она была последней парой ru/en в клиенте графа. */
var ARTS = ({ru: ' статей', es: ' artículos', ar: ' مقالة', fr: ' articles',
             zh: ' 篇文章'})[LANG] || ' articles';

/* «ВЕСЬ ГРАФ» ОТ КАЖДОГО МИНИ-ГРАФА. Ссылку писала только статья — руками, в
   generate.py. Страница автора, понятия, формулы и учёного показывали кадр и обрывались
   на нём: развернуть его во весь экран было нельзя (владелец 31.08 про страницу автора).
   Ставит её сам мини-граф — он и так знает свой набор, — и уносит именно этот набор, а
   не бросает читателя на обзор из пятидесяти кругов. Где ссылка уже написана в разметке,
   второй не появляется. */
var WHOLE = {ru: 'Весь граф', en: 'Whole graph', es: 'Todo el grafo',
             ar: 'الرسم كاملاً', fr: 'Le graphe entier', zh: '完整图谱'};

function wholeLink(box) {
    var ids = (box.dataset.ids || '').split(',').filter(Boolean);
    if (ids.length < 2) return;
    var next = box.nextElementSibling;
    if (next && next.classList.contains('b42mini-note')) return;
    var d = document.createElement('div');
    d.className = 'b42mini-note';
    var a = document.createElement('a');
    a.href = '/lang/' + LANG + '/concepts/graph.html?set=' + encodeURIComponent(ids.join(','));
    a.textContent = (WHOLE[LANG] || WHOLE.en) + ' →';
    d.appendChild(a);
    box.parentNode.insertBefore(d, box.nextSibling);
}

var _G = null;
CORE.data().then(function (G) {
    _G = G;
    boxes.forEach(function (box) { init(box, G); wholeLink(box); });
});

/* УПОМЯНУТЫЕ ПОНЯТИЯ — ПО КНОПКЕ, А НЕ САМИ.

   Мини-граф показывает ПРЕДМЕТ работы: понятия, которые вектор выбрал с поправкой
   на хабность. Упоминания — другое: это слова текста, и их вдвое больше (замер по
   архиву: 12,9 плашек против 16,8 упоминаний на статью). Высыпать их в кадр значит
   утопить предмет в общих словах — на телефоне потолок вообще десять узлов.

   Поэтому решает читатель. Кнопка появляется, только если есть что добавить, и
   только когда обвязка статьи уже пришла (её ставит js/scroll.js). Повторное
   нажатие возвращает прежний кадр — узнать, что тут своё, а что общее, можно
   переключением. */
window.B42Mini = window.B42Mini || {};
window.B42Mini.addMentions = function (box, ids, label) {
    if (!box || !ids || !ids.length || box.dataset.mentions) return;
    var have = (box.dataset.ids || '').split(',');
    var fresh = ids.filter(function (x) { return have.indexOf(x) < 0; });
    if (!fresh.length) return;
    box.dataset.mentions = fresh.join(',');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'b42mini-more';
    btn.textContent = '+ ' + (label || 'mentioned').toLowerCase();
    var on = false;
    btn.onclick = function () {
        on = !on;
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        var base = (box.dataset.base || box.dataset.ids);
        if (!box.dataset.base) box.dataset.base = base;
        box.dataset.ids = on ? (base + ',' + box.dataset.mentions) : base;
        remount(box);
    };
    var note = box.nextElementSibling;
    (note && note.classList.contains('b42mini-note') ? note : box).appendChild(btn);
};

/* Пересобрать кадр на месте: старый холст убираем, иначе их станет два. */
function remount(box) {
    if (!_G) return;
    var old = box.querySelector('canvas');
    if (old) old.remove();
    box.style.display = '';
    init(box, _G);
}

// Имя узла воркер отдаёт готовым полем name — на языке страницы; пара ru/en
// осталась дном для кадров, которые ещё держит кэш браузера.
function nodeName(n) {
    return n.name || (n.names && (n.names[LANG] || n.names.en))
        || ((LANG === 'ru' && n.ru) ? n.ru : n.en);
}

function init(box, G) {
    var ids = (box.dataset.ids || '').split(',').filter(Boolean);
    var focus = box.dataset.focus || '';
    /* узлы: только те, что есть в графе */
    var idxs = [];
    ids.forEach(function (id) {
        var i = G.byId[id];
        if (i !== undefined && idxs.indexOf(i) < 0) idxs.push(i);
    });
    if (idxs.length < 2) { box.style.display = 'none'; return; }

    var canvas = document.createElement('canvas');
    canvas.className = 'b42mini-c';
    box.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    var TK = CORE.tokens();
    new MutationObserver(function () { TK = CORE.tokens(); }).observe(
        document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

    /* ПРЕДЕЛ ПО ЧИСЛУ — на телефоне меньше: узкий холст не вмещает больше
       десятка значков, а физика на 30 узлах в 320px превращается в кашу. */
    var W = box.clientWidth || 640;
    var CAP = W < 420 ? 10 : (W < 700 ? 16 : 24);
    if (idxs.length > CAP) {
        /* режем по важности: фокус всегда, дальше — по числу связей внутри набора */
        var inSet = {};
        idxs.forEach(function (i) { inSet[i] = 1; });
        idxs.sort(function (a, b) {
            if (G.nodes[a].id === focus) return -1;
            if (G.nodes[b].id === focus) return 1;
            var da = 0, db = 0;
            G.adj[a].forEach(function (p) { if (inSet[p[0]]) da += p[1]; });
            G.adj[b].forEach(function (p) { if (inSet[p[0]]) db += p[1]; });
            return db - da;
        });
        idxs = idxs.slice(0, CAP);
    }

    var pos = {};
    idxs.forEach(function (gi, i) { pos[gi] = i; });
    var nodes = idxs.map(function (gi, i) {
        var n = G.nodes[gi];
        return {gi: gi, id: n.id, label: nodeName(n), kind: n.kind, card: n.card,
                n: n.n, center: n.id === focus,
                size: 0, x: 0, y: 0, vx: 0, vy: 0};
    });
    /* рёбра ТОЛЬКО между своими — «внутренние связи первого уровня» */
    var edges = [], seen = {};
    idxs.forEach(function (gi) {
        G.adj[gi].forEach(function (p) {
            if (pos[p[0]] === undefined) return;
            var a = pos[gi], b = pos[p[0]];
            var k = Math.min(a, b) + ':' + Math.max(a, b);
            if (!seen[k]) { seen[k] = 1; edges.push([a, b, p[1]]); }
        });
    });
    /* СТРАХОВКА: узел в кадре без единой линии — это ошибка рисунка, а не факт.
       Мы взяли его в кадр потому, что он сосед фокуса; значит связь есть, просто
       в общем графе она не сохранилась (рёбра там режутся до топ-12 на узел, и
       слабая связь хаба вылетает). Владелец 28.08: «слияние чёрных дыр не связано
       с чёрной дырой, болтается сиротой». Дотягиваем такой узел до фокуса
       минимальным весом — линия тонкая, но она честная. */
    var focusPos = -1;
    nodes.forEach(function (nd, i) { if (nd.center) focusPos = i; });
    if (focusPos >= 0) {
        var touched = {};
        edges.forEach(function (e) { touched[e[0]] = 1; touched[e[1]] = 1; });
        nodes.forEach(function (nd, i) {
            if (i === focusPos || touched[i]) return;
            edges.push([focusPos, i, 1]);
        });
    }

    /* МОСТЫ МЕЖДУ ОСТРОВАМИ. Набор статьи почти никогда не связан внутри себя
       напрямую: «чёрная дыра» и «интерферометр» стоят в разных углах, потому что
       общего ребра между ними в графе нет, и кадр рассыпается на островки. Но
       косвенно они связаны почти всегда — через третьи понятия (владелец 31.08:
       «все понятия так или иначе связаны, может их связать пунктиром пропорционально
       тому, сколько между ними промежуточных связей»).

       Меру берём простую и честную: сколько у двух понятий ОБЩИХ соседей в большом
       графе. Ноль общих — моста нет, и мы его не выдумываем. Мост рисуется пунктиром
       и тянет вчетверо слабее настоящей связи: острова сходятся, но не слипаются, и
       глазом видно, что это связь через третьих, а не прямая. */
    CORE.bridgeEdges(G.adj, idxs, edges).forEach(function (e) { edges.push(e); });

    var wMax = 1;
    edges.forEach(function (e) { if (e[2] > wMax && !e[3]) wMax = e[2]; });

    /* размеры значков: от холста и числа узлов — на телефоне мельче */
    var scale = Math.max(0.42, Math.min(1, (W / 700) * (7 / Math.sqrt(nodes.length))));
    nodes.forEach(function (nd) {
        nd.size = (nd.center ? 11 : 8) * scale;
    });

    /* стартовая раскладка: фокус в центре, остальные ЭЛЛИПСОМ по форме холста.
       Кольцо давало круг, а холст широкий: круг вписывался по высоте, и справа
       со слева оставались пустые поля (владелец 28.08: «по ширине не
       используется место»). Эллипс сразу кладёт узлы туда, где место есть. */
    var R0 = 60;
    nodes.forEach(function (nd, i) {
        if (nd.center) { nd.x = 0; nd.y = 0; return; }
        var a = (i / nodes.length) * Math.PI * 2;
        nd.x = Math.cos(a) * R0 * 1.7; nd.y = Math.sin(a) * R0;
    });

    var hover = -1, alive = 260, mouse = {}, cam = {z: 1, px: 0, py: 0};
    var dragNode = -1, dragMoved = false;

    /* Простор: во сколько раз раскладка шире базовой. Раньше расстояния между
       узлами были заданы в абсолютных единицах, а под ширину подгонялась только
       камера — и упиралась в потолок увеличения. На широкой колонке граф
       собирался кучкой в середине, а по бокам оставалось пустое поле (владелец
       28.08: «по ширине не используется место»). Теперь при большей ширине
       растут сами пружины, и граф расправляется, а не растягивается зумом. */
    var spread = 1;
    /* Насколько холст шире, чем высок (см. resize). */
    var aniso = 1;

    function resize() {
        var w = box.clientWidth || 640;
        /* высота от ширины, а не тремя ступеньками: на широкой колонке графу
           нужно и по вертикали больше места, иначе он снова сплющится */
        var h = Math.round(Math.max(190, Math.min(w * 0.52, 420)));
        canvas.width = w * devicePixelRatio;
        canvas.height = h * devicePixelRatio;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        spread = Math.max(1, Math.min(2.4, w / 430));
        /* Берём отношение сторон целиком, а не его корень: с корнем облако
           расправлялось лишь до 62% ширины при 78% высоты — форма всё ещё
           не повторяла холст. Потолок 2.2 удерживает от полосы в один ряд. */
        aniso = Math.max(1, Math.min(2.2, w / h));
        alive = Math.max(alive, 160);
    }
    window.addEventListener('resize', resize);
    /* Ширину меняет не только окно: колонка сужается сама — вкладки, раскрытые
       блоки, боковая панель. ResizeObserver ловит это, слушатель окна — нет. */
    if (window.ResizeObserver) {
        var _ro = new ResizeObserver(function () { resize(); });
        _ro.observe(box);
    }
    resize();

    function tick() {
        if (alive <= 0) return;
        alive--;
        var i, j, N = nodes.length;
        /* Отталкивание растёт как КВАДРАТ простора, натяжение — линейно: так
           равновесие между ними наступает на большем расстоянии, и рисунок
           расправляется ровно во столько раз, во сколько шире колонка. */
        var rep = 2600 * spread * spread, len = 76 * spread;
        for (i = 0; i < N; i++) {
            for (j = i + 1; j < N; j++) {
                var dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y;
                var d2 = dx * dx + dy * dy + 30;
                var f = rep / d2, d = Math.sqrt(d2);
                dx /= d; dy /= d;
                nodes[i].vx -= dx * f; nodes[i].vy -= dy * f;
                nodes[j].vx += dx * f; nodes[j].vy += dy * f;
            }
        }
        edges.forEach(function (e) {
            var a = nodes[e[0]], b = nodes[e[1]];
            var dx = b.x - a.x, dy = b.y - a.y;
            var d = Math.sqrt(dx * dx + dy * dy) + 0.01;
            var target = len / (1 + Math.log(1 + e[2]) * 0.4);
            if (e[3]) target *= 1.7;                 // мост держит на расстоянии
            var f = (d - target) * 0.0012 * Math.min(d, 200 * spread);
            if (e[3]) f *= 0.25;                     // и тянет вчетверо слабее
            if (f > 6) f = 6; else if (f < -6) f = -6;
            dx /= d; dy /= d;
            a.vx += dx * f; a.vy += dy * f;
            b.vx -= dx * f; b.vy -= dy * f;
        });
        var tot = 0;
        for (i = 0; i < N; i++) {
            var nd = nodes[i];
            if (i === dragNode) continue;      // узел в руке — его ведёт мышь
            /* фокус держим у центра — картинка «с точки зрения статьи/понятия».
               Возврат к центру слабеет с простором: иначе широкая колонка снова
               стягивала бы всё в середину, сколько ни расталкивай. */
            var pull = (nd.center ? 0.06 : 0.0022) / spread;
            /* Возврат к центру РАЗНЫЙ по осям: вдоль широкой стороны холста он
               слабее, поперёк — сильнее. Иначе облако растёт кругом и упирается
               в высоту задолго до того, как займёт ширину: замер до правки —
               81% высоты и 32% ширины. Форма облака теперь повторяет форму
               места, которое ему дали. */
            nd.vx = (nd.vx - nd.x * pull / aniso) * 0.84;
            nd.vy = (nd.vy - nd.y * pull * aniso) * 0.84;
            var sp = Math.hypot(nd.vx, nd.vy);
            if (sp > 18) { nd.vx *= 18 / sp; nd.vy *= 18 / sp; }
            nd.x += nd.vx; nd.y += nd.vy;
            tot += sp;
        }
        /* Засыпаем, только когда рисунок и правда встал И его никто не держит.
           Пока узел в руке, физика живёт — иначе соседи не поедут следом и
           «резинки» не будет. */
        if (dragNode < 0 && tot / N < 0.05) alive = Math.min(alive, 4);
        fit();
    }

    function fit() {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
        nodes.forEach(function (nd) {
            if (nd.x < minX) minX = nd.x;
            if (nd.x > maxX) maxX = nd.x;
            if (nd.y < minY) minY = nd.y;
            if (nd.y > maxY) maxY = nd.y;
        });
        var pad = w < 420 ? 74 : 62;    // поле под подписи снизу и по бокам
        var z = Math.min((w - pad) / Math.max(60, maxX - minX),
                         (h - pad) / Math.max(60, maxY - minY));
        /* Потолок увеличения был 1.6 — на широкой колонке камера упиралась в
           него и оставляла поля пустыми даже там, где рисунок мог заполнить всё.
           Раскладка теперь расправляется сама, а потолок поднят на всякий
           случай: маленькому графу из трёх узлов тоже незачем жаться. */
        cam.z += (Math.max(0.3, Math.min(2.6, z)) - cam.z) * 0.12;
        cam.px += (-(minX + maxX) / 2 - cam.px) * 0.12;
        cam.py += (-(minY + maxY) / 2 - cam.py) * 0.12;
    }

    function P(nd) {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        return [w / 2 + (nd.x + cam.px) * cam.z, h / 2 + (nd.y + cam.py) * cam.z];
    }

    function draw() {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
        ctx.clearRect(0, 0, w, h);
        var pts = nodes.map(P);
        var nbr = {};
        if (hover >= 0) {
            edges.forEach(function (e) {
                if (e[0] === hover) nbr[e[1]] = 1;
                if (e[1] === hover) nbr[e[0]] = 1;
            });
        }
        /* струны */
        edges.forEach(function (e) {
            var hot = hover >= 0 && (e[0] === hover || e[1] === hover);
            var dim = hover >= 0 && !hot;
            var wgt = Math.log(1 + e[2]) / Math.log(1 + wMax);
            ctx.strokeStyle = hot ? TK.cyan : TK.muted;
            if (e[3]) {
                /* мост через третьи понятия: пунктир, тоньше и бледнее прямой связи —
                   толщина по числу общих соседей, чтобы видно было, насколько связь плотна */
                ctx.setLineDash([3, 4]);
                ctx.globalAlpha = dim ? 0.05 : (hot ? 0.5 : 0.10 + wgt * 0.18);
                ctx.lineWidth = 0.4 + wgt * 1.1;
            } else {
                ctx.setLineDash([]);
                ctx.globalAlpha = dim ? 0.07 : (hot ? 0.75 : 0.12 + wgt * 0.38);
                ctx.lineWidth = 0.4 + wgt * 2;
            }
            ctx.beginPath(); CORE.edgePath(ctx, pts[e[0]], pts[e[1]]); ctx.stroke();
        });
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
        /* узлы и подписи с анти-коллизией */
        var taken = [];
        nodes.forEach(function (nd, i) {
            var p = pts[i], r = Math.max(2.5, nd.size * cam.z);
            var hot = i === hover;
            var dim = hover >= 0 && !hot && !nbr[i];
            CORE.drawNodeIcon(ctx, TK, p[0], p[1], r, CORE.styleOf(nd.kind),
                              dim ? 0.25 : 1, hot || nd.center);
        });
        var order = nodes.map(function (_, i) { return i; }).sort(function (a, b) {
            var pa = (a === hover ? 1e9 : 0) + (nodes[a].center ? 1e6 : 0) + nodes[a].n;
            var pb = (b === hover ? 1e9 : 0) + (nodes[b].center ? 1e6 : 0) + nodes[b].n;
            return pb - pa;
        });
        order.forEach(function (i) {
            var nd = nodes[i], p = pts[i], r = Math.max(2.5, nd.size * cam.z);
            var hot = i === hover;
            var dim = hover >= 0 && !hot && !nbr[i];
            if (dim) return;
            /* на узком холсте подписи короче и мельче — иначе лезут за край */
            var narrow = w < 420;
            var fs = (hot || nd.center ? 10.5 : 9) * (narrow ? 0.92 : 1);
            ctx.font = (hot || nd.center ? '600 ' : '') + fs + 'px ' + TK.mono;
            var lim = narrow ? 14 : 24;
            var text = nd.label.length > lim ? nd.label.slice(0, lim - 1) + '…' : nd.label;
            var tw = ctx.measureText(text).width;
            /* не рисуем то, что вышло бы за холст: обрезка по краю читается как брак */
            if (p[0] - tw / 2 < 3 || p[0] + tw / 2 > w - 3) return;
            if (p[1] + r + fs + 3 > h) return;
            var bx = [p[0] - tw / 2 - 2, p[1] + r + 2, tw + 4, fs + 3];
            for (var t = 0; t < taken.length; t++) {
                var B = taken[t];
                if (bx[0] < B[0] + B[2] && bx[0] + bx[2] > B[0] &&
                    bx[1] < B[1] + B[3] && bx[1] + bx[3] > B[1]) return;
            }
            taken.push(bx);
            ctx.fillStyle = hot ? TK.cyan : (nd.center ? TK.text : TK.muted);
            ctx.globalAlpha = hot || nd.center ? 1 : 0.8;
            ctx.textAlign = 'center';
            ctx.fillText(text, p[0], p[1] + r + fs + 1);
            ctx.globalAlpha = 1;
        });
        /* подсказка у курсора */
        if (hover >= 0 && mouse.x !== undefined) {
            var hd = nodes[hover];
            var lines = [hd.label,
                         hd.kind + ' · ' + hd.n + ARTS];
            ctx.font = '10.5px ' + TK.mono;
            /* ОПИСАНИЕ ПОНЯТИЯ ПРЯМО В ПОДСКАЗКЕ — «наведись и узнай». Большой граф это
               умеет с самого начала, мини-граф носил описание в данных и не показывал:
               человек видел «phenomenon · 18 статей» и должен был уходить на страницу,
               чтобы понять, что это вообще такое (владелец 31.08). Ширина 220 — столько
               помещается рядом с курсором на телефоне, не закрывая сам граф. */
            var body = 0;
            if (hd.card) {
                var words = String(hd.card).split(' '), line = '';
                for (var wi = 0; wi < words.length && body < 4; wi++) {
                    var test = line ? line + ' ' + words[wi] : words[wi];
                    if (ctx.measureText(test).width > 220 && line) {
                        lines.push(line); body++; line = words[wi];
                    } else line = test;
                }
                if (line && body < 4) { lines.push(line); body++; }
                else if (body >= 4) lines[lines.length - 1] += '…';
            }
            var tww = 0;
            lines.forEach(function (s) { tww = Math.max(tww, ctx.measureText(s).width); });
            var th = lines.length * 13 + 8;
            var tx = Math.min(mouse.x + 12, w - tww - 16);
            var ty = Math.min(mouse.y + 4, h - th - 4);
            ctx.globalAlpha = 0.95;
            ctx.fillStyle = TK.surface; ctx.strokeStyle = TK.hair;
            ctx.beginPath(); ctx.roundRect(tx - 6, ty - 12, tww + 12, th, 5);
            ctx.fill(); ctx.stroke();
            ctx.globalAlpha = 1;
            ctx.textAlign = 'start';
            lines.forEach(function (s, li) {
                ctx.font = (li ? '10px ' : '600 10.5px ') + TK.mono;
                ctx.fillStyle = li ? TK.soft : TK.text;
                ctx.fillText(s, tx, ty + li * 13);
            });
        }
        box._pts = pts;
    }

    function loop() { tick(); draw(); requestAnimationFrame(loop); }

    function pick(mx, my) {
        if (!box._pts) return -1;
        var best = -1, bd = 1e9;
        box._pts.forEach(function (p, i) {
            var d = Math.hypot(p[0] - mx, p[1] - my);
            var r = Math.max(10, nodes[i].size * cam.z + 7);
            if (d < r && d < bd) { best = i; bd = d; }
        });
        return best;
    }
    /* Куда ведёт узел: у понятия своя страница, у формулы своя, у учёного своя.
       Раньше адрес собирался в двух местах по-разному, и узел-учёный уводил бы
       на несуществующее понятие «s:Albert Einstein». */
    function pageOf(nd) {
        if (nd.kind === 'formula') return '/lang/' + LANG + '/formula/' + nd.id.slice(2) + '.html';
        if (nd.kind === 'scientist') {
            var slug = nd.id.slice(2).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '');
            return '/lang/en/scientists/' + slug + '.html';
        }
        return '/lang/' + LANG + '/concepts/' + nd.id + '.html';
    }

    /* Экран → мир: обратная к P(). Нужна перетаскиванию — узел должен оказаться
       ровно под курсором при любом текущем увеличении. */
    function toWorld(mx, my) {
        var w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
        return [(mx - w / 2) / cam.z - cam.px, (my - h / 2) / cam.z - cam.py];
    }

    /* РЕЗИНОВОЕ ПЕРЕТАСКИВАНИЕ — тот же приём, что в большом графе (b42-graph.js):
       узел следует за рукой, пружины тащат соседей. Владелец 28.08: «этот
       мини-граф не динамический, его нельзя тянуть — а может сделать его тоже
       живым». Клик по узлу при этом сохраняется: переходом считаем только то
       нажатие, которое не сдвинулось с места. */
    canvas.addEventListener('mousedown', function (e) {
        var i = pick(e.offsetX, e.offsetY);
        if (i < 0) return;
        dragNode = i;
        dragMoved = false;
        alive = 1e9;                       // физика живёт, пока держим
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
    });
    window.addEventListener('mouseup', function () {
        if (dragNode < 0) return;
        dragNode = -1;
        alive = 300;                       // дать соседям доехать и уснуть
        canvas.style.cursor = '';
    });
    canvas.addEventListener('mousemove', function (e) {
        mouse.x = e.offsetX; mouse.y = e.offsetY;
        if (dragNode >= 0) {
            var w = toWorld(e.offsetX, e.offsetY);
            var nd = nodes[dragNode];
            nd.x = w[0]; nd.y = w[1]; nd.vx = 0; nd.vy = 0;
            dragMoved = true;
            return;
        }
        var h = pick(e.offsetX, e.offsetY);
        if (h !== hover) {
            hover = h;
            canvas.style.cursor = h >= 0 ? 'grab' : '';
            /* Наведение будит рисунок: подсветка соседей должна быть заметной,
               а на замершем графе она выглядела мёртвой картинкой. */
            if (h >= 0) alive = Math.max(alive, 40);
        }
    });
    canvas.addEventListener('mouseleave', function () { hover = -1; });
    canvas.addEventListener('click', function (e) {
        if (dragMoved) { dragMoved = false; return; }   // тянули, а не выбирали
        var i = pick(e.offsetX, e.offsetY);
        if (i < 0) return;
        var nd = nodes[i];
        location.href = pageOf(nd);
    });
    /* Палец: тап показывает подпись, второй тап переходит, а протяжка тянет
       узел — то же, что мышью. Слушатель НЕ passive: пока узел в руке, страницу
       прокручивать нельзя, иначе рисунок уезжает вместе с ней. */
    canvas.addEventListener('touchstart', function (e) {
        var t = e.touches[0], r = canvas.getBoundingClientRect();
        mouse.x = t.clientX - r.left; mouse.y = t.clientY - r.top;
        hover = pick(mouse.x, mouse.y);
        if (hover >= 0) {
            dragNode = hover;
            dragMoved = false;
            alive = 1e9;
        }
    }, {passive: true});
    canvas.addEventListener('touchmove', function (e) {
        if (dragNode < 0) return;
        var t = e.touches[0], r = canvas.getBoundingClientRect();
        var w = toWorld(t.clientX - r.left, t.clientY - r.top);
        var nd = nodes[dragNode];
        nd.x = w[0]; nd.y = w[1]; nd.vx = 0; nd.vy = 0;
        dragMoved = true;
        e.preventDefault();
    }, {passive: false});
    canvas.addEventListener('touchend', function () {
        if (dragNode < 0) return;
        dragNode = -1;
        alive = 300;
    }, {passive: true});

    loop();
}
})();
