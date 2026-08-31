/* b42-graph-core — общий визуальный язык графа знаний: классы, цвета, формы,
   штрихографика, дуги рёбер. Один код рисует и большое приложение
   (/concepts/graph.html, js/b42-graph.js), и мини-графы на страницах статьи,
   понятия и формулы (js/b42-mini.js).

   Вынесено 27.08 при добавлении мини-графов: два рисователя с одинаковым видом —
   это гарантированное расхождение через неделю. Правило дома: брать общее,
   не писать своё.

   Всё чистое: функции получают ctx и токены темы аргументами, состояния нет. */
(function () {
'use strict';

/* классы понятий: форма + цвет + штрих. Порядок = порядок в легенде. */
/* ПОДПИСЬ СЕМЕЙСТВА НА ЯЗЫКЕ СТРАНИЦЫ. Пара ru/en держалась с тех пор, когда
   языков было два: испанец, араб и француз читали легенду графа по-английски.
   Язык теперь ключ в записи, а выбор — одна функция ниже; шестой язык это ещё
   один ключ и ни одной правки в коде, который рисует. */
var KINDS = [
    {k: 'law+', shapes: ['law', 'principle', 'theorem', 'equation'], sh: 'sq',
     color: '#4a7ab5', hatch: 'double',
     ru: 'закон · принцип', en: 'law · principle', es: 'ley · principio', ar: 'قانون · مبدأ', fr: 'loi · principe', zh: '定律 · 原理'},
    {k: 'method+', shapes: ['method', 'process'], sh: 'di',
     color: '#b8860b', hatch: 'diag',
     ru: 'метод · процесс', en: 'method · process', es: 'método · proceso', ar: 'طريقة · عملية', fr: 'méthode · processus', zh: '方法 · 过程'},
    {k: 'phen+', shapes: ['phenomenon', 'effect'], sh: 'tr',
     color: '#0d7d8c', hatch: 'rays',
     ru: 'явление · эффект', en: 'phenomenon · effect', es: 'fenómeno · efecto', ar: 'ظاهرة · أثر', fr: 'phénomène · effet', zh: '现象 · 效应'},
    {k: 'obj+', shapes: ['object', 'substance', 'structure'], sh: 'ring',
     color: '#8a6db1', hatch: 'ring',
     ru: 'объект · вещество', en: 'object · substance', es: 'objeto · sustancia', ar: 'جسم · مادة', fr: 'objet · substance', zh: '客体 · 物质'},
    {k: 'instr+', shapes: ['instrument', 'experiment'], sh: 'hex',
     color: '#5f8d4e', hatch: 'dot',
     ru: 'прибор', en: 'instrument', es: 'instrumento', ar: 'أداة', fr: 'instrument', zh: '仪器'},
    {k: 'math', shapes: ['math'], sh: 'circle',
     color: '#a05c65', hatch: 'grid',
     ru: 'математика', en: 'math', es: 'matemáticas', ar: 'رياضيات', fr: 'mathématiques', zh: '数学'},
    {k: 'units+', shapes: ['quantity', 'constant', 'unit', 'unit_system'],
     sh: 'pent', color: '#767c85', hatch: 'horiz',
     ru: 'величины · единицы', en: 'quantities · units', es: 'magnitudes · unidades', ar: 'كميات · وحدات', fr: 'grandeurs · unités', zh: '物理量 · 单位'},
    {k: 'stats', shapes: ['statistics'], sh: 'circle', color: '#4e8076',
     hatch: 'scatter', ru: 'статистика', en: 'statistics', es: 'estadística', ar: 'إحصاء', fr: 'statistique', zh: '统计'},
    {k: 'formula', shapes: ['formula'], sh: 'fx', color: '#8c6d3f',
     hatch: 'none', ru: 'формулы', en: 'formulas', es: 'fórmulas', ar: 'صيغ', fr: 'formules', zh: '公式'},
    /* Учёные — отдельным классом и отдельной формой (владелец 28.08: «есть ли
       опция включить учёных, иконка для них»). Форма «человек»: круг головы над
       дугой плеч — единственная фигура в наборе, читаемая как имя, а не как
       предмет. Выключается тем же переключателем, что и остальные классы. */
    {k: 'sci', shapes: ['scientist'], sh: 'person', color: '#b5654a',
     hatch: 'none', ru: 'учёные', en: 'scientists', es: 'científicos', ar: 'علماء', fr: 'scientifiques', zh: '科学家'},
    {k: 'rest', shapes: [], sh: 'circle', color: '#6b7f8c', hatch: 'none',
     ru: 'понятие', en: 'concept', es: 'concepto', ar: 'مفهوم', fr: 'concept', zh: '概念'},
];
var bucket = {}, style = {};
KINDS.forEach(function (K) {
    style[K.k] = K;
    K.shapes.forEach(function (s) { bucket[s] = K.k; });
});

function kindLabel(K, lang) {
    return (K && (K[lang] || K.en)) || '';
}

function bucketOf(kind) { return bucket[kind] || 'rest'; }
function styleOf(kind) { return style[bucketOf(kind)]; }

/* токены темы сайта — граф всегда в цвете страницы, включая тёмную */
function tokens() {
    var cs = getComputedStyle(document.documentElement);
    function v(n, fb) { return (cs.getPropertyValue(n) || fb).trim() || fb; }
    return {text: v('--text', '#222'), muted: v('--muted', '#777'),
            soft: v('--soft', '#999'), hair: v('--hairline', '#ddd'),
            cyan: v('--cyan', '#0d7d8c'), link: v('--link', '#0d7d8c'),
            ochre: v('--ochre', '#b8860b'),
            bg: v('--bg', '#faf9f5'), surface: v('--surface', '#f4f2ec'),
            mono: v('--mono', 'ui-monospace, monospace')};
}

function pathShape(ctx, x, y, r, sh) {
    ctx.beginPath();
    var i, a;
    if (sh === 'person') {
        /* голова и плечи: маленький круг сверху, дуга снизу */
        ctx.arc(x, y - r * 0.42, r * 0.42, 0, Math.PI * 2);
        ctx.moveTo(x - r * 0.85, y + r * 0.9);
        ctx.arc(x, y + r * 0.9, r * 0.85, Math.PI, Math.PI * 2, false);
        ctx.closePath();
    }
    else if (sh === 'sq') ctx.rect(x - r * 0.85, y - r * 0.85, r * 1.7, r * 1.7);
    else if (sh === 'di') {
        ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r);
        ctx.lineTo(x - r, y); ctx.closePath();
    } else if (sh === 'tr') {
        ctx.moveTo(x, y - r); ctx.lineTo(x + r * 0.9, y + r * 0.7);
        ctx.lineTo(x - r * 0.9, y + r * 0.7); ctx.closePath();
    } else if (sh === 'hex') {
        for (i = 0; i < 6; i++) {
            a = Math.PI / 3 * i - Math.PI / 6;
            ctx[i ? 'lineTo' : 'moveTo'](x + r * Math.cos(a), y + r * Math.sin(a));
        }
        ctx.closePath();
    } else if (sh === 'pent') {
        for (i = 0; i < 5; i++) {
            a = Math.PI * 2 / 5 * i - Math.PI / 2;
            ctx[i ? 'lineTo' : 'moveTo'](x + r * Math.cos(a), y + r * Math.sin(a));
        }
        ctx.closePath();
    } else if (sh === 'fx') {
        /* формула: кружок со струной-синусоидой внутри */
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.moveTo(x - r * 0.62, y);
        ctx.quadraticCurveTo(x - r * 0.3, y - r * 0.75, x, y);
        ctx.quadraticCurveTo(x + r * 0.3, y + r * 0.75, x + r * 0.62, y);
    } else ctx.arc(x, y, r, 0, Math.PI * 2);
}

function drawNodeIcon(ctx, TK, x, y, r, st, alpha, hot, isGroup) {
    var col = st.color;
    if (isGroup) {
        /* группа — объёмный полупрозрачный шарик: свет сверху-слева */
        var g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4,
                                         r * 0.1, x, y, r);
        g.addColorStop(0, col + '55');
        g.addColorStop(0.65, col + '2e');
        g.addColorStop(1, col + '0a');
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fillStyle = g;
        ctx.globalAlpha = alpha;
        ctx.fill();
        ctx.strokeStyle = hot ? TK.cyan : col;
        ctx.globalAlpha = alpha * (hot ? 0.95 : 0.5);
        ctx.lineWidth = hot ? 1.8 : 1;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x - r * 0.34, y - r * 0.4, r * 0.16, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.globalAlpha = alpha * 0.35;
        ctx.fill();
        return;
    }
    /* мягкая цветная заливка — прозрачность и лёгкость */
    pathShape(ctx, x, y, r, st.sh);
    ctx.fillStyle = col;
    ctx.globalAlpha = alpha * (hot ? 0.30 : 0.13);
    ctx.fill();
    /* штрих внутри формы */
    if (st.hatch !== 'none' && r > 5) {
        ctx.save();
        pathShape(ctx, x, y, r, st.sh);
        ctx.clip();
        ctx.strokeStyle = col;
        ctx.globalAlpha = alpha * 0.45;
        ctx.lineWidth = 1;
        ctx.beginPath();
        var s, k;
        if (st.hatch === 'diag') {
            for (s = -r * 2; s <= r * 2; s += 3.6) {
                ctx.moveTo(x + s - r, y - r); ctx.lineTo(x + s + r, y + r);
            }
        } else if (st.hatch === 'horiz') {
            for (s = -r; s <= r; s += 3.4) {
                ctx.moveTo(x - r, y + s); ctx.lineTo(x + r, y + s);
            }
        } else if (st.hatch === 'grid') {
            for (s = -r; s <= r; s += 3.8) {
                ctx.moveTo(x - r, y + s); ctx.lineTo(x + r, y + s);
                ctx.moveTo(x + s, y - r); ctx.lineTo(x + s, y + r);
            }
        } else if (st.hatch === 'rays') {
            for (k = 0; k < 7; k++) {
                var an = -Math.PI / 2 + (k - 3) * 0.28;
                ctx.moveTo(x, y - r * 0.15);
                ctx.lineTo(x + Math.cos(an + Math.PI / 2) * r * 1.4,
                           y - r * 0.15 + Math.sin(an + Math.PI / 2) * r * 1.4);
            }
        } else if (st.hatch === 'ring') {
            ctx.moveTo(x + r * 0.55, y);
            ctx.arc(x, y, r * 0.55, 0, Math.PI * 2);
        } else if (st.hatch === 'dot') {
            ctx.moveTo(x + r * 0.22, y);
            ctx.arc(x, y, r * 0.22, 0, Math.PI * 2);
        } else if (st.hatch === 'scatter') {
            /* статистика: россыпь точек, как скаттер-плот */
            var pts = [[-0.45, -0.3], [0.1, -0.5], [0.45, -0.05],
                       [-0.15, 0.15], [0.3, 0.45], [-0.5, 0.4]];
            for (k = 0; k < pts.length; k++) {
                ctx.moveTo(x + pts[k][0] * r + r * 0.12, y + pts[k][1] * r);
                ctx.arc(x + pts[k][0] * r, y + pts[k][1] * r, r * 0.12,
                        0, Math.PI * 2);
            }
        }
        ctx.stroke();
        if (st.hatch === 'dot') {
            ctx.fillStyle = col; ctx.globalAlpha = alpha * 0.7;
            ctx.beginPath(); ctx.arc(x, y, r * 0.2, 0, Math.PI * 2); ctx.fill();
        }
        ctx.restore();
    }
    /* контур; double — двойной */
    pathShape(ctx, x, y, r, st.sh);
    ctx.strokeStyle = hot ? TK.cyan : col;
    ctx.globalAlpha = alpha * (hot ? 1 : 0.85);
    ctx.lineWidth = hot ? 2 : 1.25;
    ctx.stroke();
    if (st.hatch === 'double' && r > 5) {
        pathShape(ctx, x, y, r * 0.72, st.sh);
        ctx.globalAlpha = alpha * 0.5;
        ctx.lineWidth = 1;
        ctx.stroke();
    }
}

/* дуга ребра: лёгкий изгиб перпендикуляром — воздух вместо паутины прямых */
function edgePath(ctx, a, b) {
    var mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
    var dx = b[0] - a[0], dy = b[1] - a[1];
    var d = Math.sqrt(dx * dx + dy * dy) + 0.01;
    var k = Math.min(10, d * 0.05);
    ctx.moveTo(a[0], a[1]);
    ctx.quadraticCurveTo(mx - dy / d * k, my + dx / d * k, b[0], b[1]);
}

/* ОПИСАНИЕ ПОНЯТИЯ ПОД КУРСОРОМ — НА ЯЗЫКЕ ЧИТАТЕЛЯ. В самом графе лежит английская
   карточка: пять переводов раздули бы файл с двух с половиной мегабайт до семи, а он
   грузится на каждой странице с мини-графом. Перевод приезжает вторым файлом и только
   свой (600 килобайт), уже после того как граф нарисован: пока он в пути, подсказка
   показывает английское описание, а не пустоту. */
function cards(d) {
    var lang = (document.documentElement.lang || 'en').slice(0, 2);
    if (lang === 'en') return;
    fetch('/data/graph-cards-' + lang + '.json')
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (m) {
            if (!m) return;
            d.nodes.forEach(function (n) { if (m[n.id]) n.card = m[n.id]; });
        })
        .catch(function () {});
}

/* общий загрузчик данных: один запрос на страницу, сколько бы графов ни было */
var dataP = null;
function data() {
    if (!dataP) {
        dataP = fetch('/data/concepts-graph.json')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                d.byId = {};
                d.nodes.forEach(function (n, i) { d.byId[n.id] = i; });
                d.adj = d.nodes.map(function () { return []; });
                d.edges.forEach(function (e) {
                    d.adj[e[0]].push([e[1], e[2]]);
                    d.adj[e[1]].push([e[0], e[2]]);
                });
                cards(d);
                return d;
            });
    }
    return dataP;
}

window.B42GraphCore = {
    KINDS: KINDS, kindLabel: kindLabel, bucketOf: bucketOf, styleOf: styleOf, tokens: tokens,
    pathShape: pathShape, drawNodeIcon: drawNodeIcon, edgePath: edgePath,
    data: data,
};
})();
