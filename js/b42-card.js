/* b42-card — всплывающая карточка понятия. Одна на весь сайт.

   Владелец 28.08: «подсветка есть по тексту, но тултипа нет — абзацем с
   кнопками "закрыть" и "подробно". Это же было! Иначе каждый раз щёлкать
   ссылки и уходить». И следом: «с графом то же самое», «тултип не строкой, а
   аккуратной карточкой».

   Смысл простой: встретил в тексте незнакомое слово — посмотрел, что это, и
   ЧИТАЕШЬ ДАЛЬШЕ. Уход на страницу понятия — отдельное решение, кнопкой, а не
   побочный эффект любопытства.

   Один компонент на три места: подсвеченные слова в тексте статьи, узлы
   большого графа, узлы мини-графа. Данные берёт у воркера (/api/concept) —
   значит карточка всегда свежая и не требует пересборки страниц; ответы
   кэшируются в памяти вкладки, повторное наведение бесплатно.

   Показ:  B42Card.show(id, x, y)   — по идентификатору понятия и точке экрана
   Скрыть: B42Card.hide()
*/
(function () {
'use strict';

var LANG = document.documentElement.lang || 'en';
var API = (window.B42_API || '').replace(/\/$/, '');
var cache = {}, rels = {}, box = null, cur = null, pinned = false;
var lastX = 0, lastY = 0;

/* ПОДПИСИ КАРТОЧКИ — ТАБЛИЦЕЙ ПО ЯЗЫКАМ, а не тройкой `RU ? … : …`.

   Карточку читают на пяти языках, а подписи знали два: испанцу, арабу и французу
   доставалось «Details», «articles», «Broader». Это тот же изъян, что и в облаке,
   где имя понятия жило в столбце name_ru: язык записан условием, а не значением,
   и шестой язык требует шестой ветки в каждой строке. Здесь язык — ключ; добавить
   китайский значит дописать один блок, и ни одной правки в коде ниже.

   Английский — дно: язык, которого в таблице нет, получает его целиком, а язык
   переведённый наполовину — только недостающие строки (Object.assign). Пустой
   карточки не бывает ни при каком языке. */
var STRINGS = {
    ru: { more: 'Подробно', close: 'Закрыть', arts: 'статей', links: 'связей',
          wait: 'смотрю…', none: 'Карточки пока нет', graph: 'В графе',
          fact: 'Кстати', wider: 'Шире', deeper: 'Глубже' },
    es: { more: 'Detalles', close: 'Cerrar', arts: 'artículos', links: 'enlaces',
          wait: 'cargando…', none: 'Aún no hay ficha', graph: 'En el grafo',
          fact: 'Por cierto', wider: 'Más amplio', deeper: 'Más profundo' },
    ar: { more: 'تفاصيل', close: 'إغلاق', arts: 'مقالة', links: 'روابط',
          wait: 'جارٍ التحميل…', none: 'لا توجد بطاقة بعد', graph: 'في الرسم البياني',
          fact: 'بالمناسبة', wider: 'أوسع', deeper: 'أعمق' },
    fr: { more: 'Détails', close: 'Fermer', arts: 'articles', links: 'liens',
          wait: 'chargement…', none: 'Pas encore de fiche', graph: 'Dans le graphe',
          fact: 'Au fait', wider: 'Plus large', deeper: 'Plus profond' },
    zh: { more: '详情', close: '关闭', arts: '篇文章', links: '关联',
          wait: '加载中…', none: '暂无卡片', graph: '在图谱中',
          fact: '顺带一提', wider: '更广', deeper: '更深' }
};
var EN = { more: 'Details', close: 'Close', arts: 'articles', links: 'links',
           wait: 'loading…', none: 'No card yet', graph: 'In graph',
           fact: 'By the way', wider: 'Broader', deeper: 'Deeper' };
var T = Object.assign({}, EN, STRINGS[LANG] || {});

/* УРОВЕНЬ ЧТЕНИЯ НАСЛЕДУЕТСЯ. Владелец 29.08: «если я открываю карточку понятия
   с популярной или простой версии, она должна вести на популярное понятие».
   Читаешь популярное изложение, наводишь на слово — и получаешь учебник: голос
   сбивается ровно там, где читателю нужнее всего помощь.

   Уровень страницы уже знает effVersion() из search.js: он подключён на всех
   типах страниц, спрашивать больше нечего. Простое и популярное берут
   description_popular и живой факт, подробное — формальное определение, как и
   было: его читатель пришёл за точностью. */
function level() {
    try {
        return (typeof window.effVersion === 'function' ? window.effVersion() : 'popular');
    } catch (e) {
        return 'popular';
    }
}

/* Карточка — не статья: длинный текст в ней не читают, его проматывают. Режем по
   границе предложения, а не по буквам: обрубок на полуслове выглядит поломкой. */
function brief(t, cap) {
    t = String(t || '').trim();
    if (t.length <= cap) return t;
    var cut = t.slice(0, cap);
    var stop = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('! '), cut.lastIndexOf('? '));
    return stop > cap * 0.5 ? cut.slice(0, stop + 1) : cut.replace(/\s+\S*$/, '') + '…';
}

/* Класс понятия — тем же приёмом. Английские ключи (law, phenomenon, quantity)
   и были подписью для всех, кроме русского: испанец читал «phenomenon» посреди
   испанской фразы. */
var KINDS = {
    ru: { concept: 'понятие', law: 'закон', principle: 'принцип', theorem: 'теорема',
          equation: 'уравнение', phenomenon: 'явление', effect: 'эффект',
          method: 'метод', process: 'процесс', object: 'объект', substance: 'вещество',
          instrument: 'прибор', quantity: 'величина', unit: 'единица',
          constant: 'константа', statistics: 'статистика', math: 'математика',
          theory: 'теория', property: 'свойство', formula: 'формула' },
    es: { concept: 'concepto', law: 'ley', principle: 'principio', theorem: 'teorema',
          equation: 'ecuación', phenomenon: 'fenómeno', effect: 'efecto',
          method: 'método', process: 'proceso', object: 'objeto', substance: 'sustancia',
          instrument: 'instrumento', quantity: 'magnitud', unit: 'unidad',
          constant: 'constante', statistics: 'estadística', math: 'matemáticas',
          theory: 'teoría', property: 'propiedad', formula: 'fórmula' },
    ar: { concept: 'مفهوم', law: 'قانون', principle: 'مبدأ', theorem: 'مبرهنة',
          equation: 'معادلة', phenomenon: 'ظاهرة', effect: 'أثر',
          method: 'طريقة', process: 'عملية', object: 'جسم', substance: 'مادة',
          instrument: 'أداة', quantity: 'كمية', unit: 'وحدة',
          constant: 'ثابت', statistics: 'إحصاء', math: 'رياضيات',
          theory: 'نظرية', property: 'خاصية', formula: 'صيغة' },
    fr: { concept: 'concept', law: 'loi', principle: 'principe', theorem: 'théorème',
          equation: 'équation', phenomenon: 'phénomène', effect: 'effet',
          method: 'méthode', process: 'processus', object: 'objet', substance: 'substance',
          instrument: 'instrument', quantity: 'grandeur', unit: 'unité',
          constant: 'constante', statistics: 'statistique', math: 'mathématiques',
          theory: 'théorie', property: 'propriété', formula: 'formule' },
    zh: { concept: '概念', law: '定律', principle: '原理', theorem: '定理',
          equation: '方程', phenomenon: '现象', effect: '效应',
          method: '方法', process: '过程', object: '客体', substance: '物质',
          instrument: '仪器', quantity: '物理量', unit: '单位',
          constant: '常数', statistics: '统计', math: '数学',
          theory: '理论', property: '性质', formula: '公式' }
};

function el() {
    if (box) return box;
    box = document.createElement('div');
    box.className = 'b42card';
    box.setAttribute('role', 'dialog');
    document.body.appendChild(box);
    /* Клик внутри карточки не должен её закрывать — иначе кнопка «Подробно»
       не успевает сработать. */
    box.addEventListener('click', function (e) { e.stopPropagation(); });
    document.addEventListener('click', function () { hide(); });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') hide();
    });
    return box;
}

function kindLabel(k) {
    var by = KINDS[LANG];
    return (by && by[k]) || k || '';
}

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c];
    });
}

/* Число константы — крупно и по-человечески: 1.602176634e-19 → 1,602176634·10⁻¹⁹ */
function niceValue(v) {
    var m = /^(-?\d+(?:\.\d+)?)[eE]([-+]?\d+)$/.exec(String(v || '').trim());
    if (!m) return esc(v);
    var sup = String(parseInt(m[2], 10))
        .replace(/-/g, '⁻').replace(/0/g, '⁰').replace(/1/g, '¹').replace(/2/g, '²')
        .replace(/3/g, '³').replace(/4/g, '⁴').replace(/5/g, '⁵').replace(/6/g, '⁶')
        .replace(/7/g, '⁷').replace(/8/g, '⁸').replace(/9/g, '⁹');
    return esc(m[1].replace('.', ',')) + '·10' + sup;
}

/* КУДА ДВИГАТЬСЯ ДАЛЬШЕ. Владелец 29.08: «карточка понятия всегда показывает,
   куда двигаться дальше, и, перемещаясь по ссылкам, мы познаём предмет».

   Направление берём из числа статей у соседа, без всякой модели: понятие, которое
   встречается ЧАЩЕ, почти всегда шире и проще — на нём стоит начинать; которое
   реже — уже и глубже. Это не закон природы, а надёжная примета, и её видно
   проверкой: «чёрная дыра» встречается чаще «энтропии Вальда».

   Сосед открывается КАРТОЧКОЙ, а не переходом: читатель остаётся в тексте статьи
   и идёт по понятиям, пока не решит уйти совсем — для этого есть «Подробно». */
function ways(d, rel) {
    if (!rel || !rel.length) return '';
    var own = d.n || 0, wide = [], deep = [];
    for (var i = 0; i < rel.length; i++) {
        var r = rel[i];
        if (!r || !r.id || !r.name) continue;
        ((r.n || 0) >= own ? wide : deep).push(r);
        if (wide.length >= 3 && deep.length >= 3) break;
    }
    function row(label, list) {
        if (!list.length) return '';
        return '<div class="b42card-way"><span>' + label + '</span>' +
            list.slice(0, 3).map(function (r) {
                return '<button type="button" class="b42card-next" data-id="' +
                    esc(r.id) + '">' + esc(r.name) + '</button>';
            }).join('') + '</div>';
    }
    return row(T.wider, wide) + row(T.deeper, deep);
}


function render(d, id, rel) {
    /* Имя воркер уже отдал на языке страницы (поле names, все языки разом);
       разбирать его здесь по языкам больше нечего. */
    var name = d.name || id.replace(/_/g, ' ');
    var href = '/lang/' + LANG + '/concepts/' + encodeURIComponent(id) + '.html';
    var stats = [];
    if (d.n) stats.push(d.n + ' ' + T.arts);
    if (d.links) stats.push(d.links + ' ' + T.links);
    /* Текст по уровню чтения. Популярного описания нет у 512 понятий из 3 589 —
       там честно остаётся формальное, а не пустое место. */
    var full = d.full || {};
    var pop = level() !== 'advanced' && full.description_popular;
    var body = pop ? brief(full.description_popular, 300) : (d.card || T.none);
    var fact = pop ? brief(full.fun_fact_popular || '', 200) : '';

    return '' +
        '<div class="b42card-h">' +
            '<span class="b42card-kind">' + esc(kindLabel(d.kind)) + '</span>' +
            '<b>' + esc(name) + '</b>' +
        '</div>' +
        (d.value ? '<div class="b42card-val">' + niceValue(d.value) +
                   (d.unit ? ' <em>' + esc(d.unit.replace(/_/g, ' ')) + '</em>' : '') +
                   '</div>' : '') +
        '<div class="b42card-t">' + esc(body) + '</div>' +
        (fact ? '<div class="b42card-fact"><span>' + T.fact + '</span> ' +
                esc(fact) + '</div>' : '') +
        ways(d, rel) +
        (stats.length ? '<div class="b42card-n">' + stats.join(' · ') + '</div>' : '') +
        '<div class="b42card-a">' +
            '<a class="b42card-go" href="' + href + '">' + T.more + '</a>' +
            '<a class="b42card-go b42card-graph" href="/lang/' + LANG +
                '/concepts/graph.html?focus=' + encodeURIComponent(id) + '">' + T.graph + '</a>' +
            '<button type="button" class="b42card-x">' + T.close + '</button>' +
        '</div>';
}

function place(x, y) {
    var b = el(), w = b.offsetWidth || 320, h = b.offsetHeight || 160;
    var vw = document.documentElement.clientWidth;
    var vh = document.documentElement.clientHeight;
    /* Держим карточку в окне: у правого края разворачиваем влево, у нижнего —
       вверх. Иначе на узком экране половина уезжает за пределы. */
    var left = Math.min(Math.max(8, x - w / 2), vw - w - 8);
    var top = y + 16;
    if (top + h > vh - 8) top = Math.max(8, y - h - 16);
    b.style.left = Math.round(left) + 'px';
    b.style.top = Math.round(top + (window.scrollY || 0)) + 'px';
}

function fill(id, data, rel) {
    var b = el();
    b.innerHTML = render(data || {}, id, rel);
    b.querySelector('.b42card-x').addEventListener('click', hide);
    /* Переход к соседу — та же карточка на том же месте. Позицию помним: если
       пересчитывать её от кнопки, карточка убегает вниз с каждым шагом. */
    var next = b.querySelectorAll('.b42card-next');
    for (var i = 0; i < next.length; i++) {
        next[i].addEventListener('click', function (e) {
            e.stopPropagation();
            show(this.getAttribute('data-id'), lastX, lastY);
        });
    }
}

function show(id, x, y, seed) {
    if (!id) return;
    cur = id;
    pinned = true;
    lastX = x; lastY = y;
    var b = el();
    b.classList.add('on');
    if (cache[id]) {
        fill(id, cache[id], rels[id]);
        place(x, y);
        return;
    }
    /* Пока летит запрос — показываем то, что уже знаем (граф передаёт имя и
       определение узла): карточка не должна мигать пустотой. */
    fill(id, seed || {card: T.wait});
    place(x, y);
    /* Пустой API — это НЕ «ручек нет», а «ручки по своему же адресу»: в проде сайт
       и воркер один источник, и относительный путь работает. Здесь стоял выход
       при пустом API, и карточка в проде навсегда замирала на «смотрю…» —
       наводишь на подсвеченное слово, а определения не будет никогда. Так же
       читают адрес соседи (author-live, entity-live, formula-live): пусто —
       значит свой origin. Локальный файловый сервер на 8420 ручек не отдаёт,
       и там запрос просто не удастся — это ловит catch ниже. */
    fetch(API + '/api/concept?id=' + encodeURIComponent(id) + '&lang=' + LANG)
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (!d || !d.concept) return;
            cache[id] = d.concept;
            rels[id] = d.related || [];
            if (cur === id && b.classList.contains('on')) {
                fill(id, d.concept, rels[id]);
                place(x, y);
            }
        })
        .catch(function () {});
}

function hide() {
    if (!box) return;
    box.classList.remove('on');
    pinned = false;
    cur = null;
}

/* ── подсвеченные слова в тексте ────────────────────────────────────────────
   Клик по подсвеченному понятию открывает карточку ВМЕСТО перехода: читатель
   остаётся в тексте. Уйти можно кнопкой «Подробно» — это уже его решение.
   Ctrl/Cmd-клик и средняя кнопка работают как обычная ссылка: кто хочет в новую
   вкладку, тот и хочет. */
function idOf(a) {
    if (a.dataset.tag) return a.dataset.tag;
    if (a.dataset.law) return a.dataset.law;
    var m = /\/concepts\/([^/.]+)\.html/.exec(a.getAttribute('href') || '');
    return m ? decodeURIComponent(m[1]) : '';
}

/* ПОКАЗЫВАЕТ НАВЕДЕНИЕ, а не клик (владелец 28.08). Читатель ведёт глазами по
   строке, задержался на слове — увидел, что это, и пошёл дальше; клик остаётся
   обычным переходом по ссылке, для тех, кто решил уйти насовсем.

   Две задержки, обе нужны. Перед показом — четверть секунды, иначе карточка
   мигает на каждом слове, через которое мышь просто проехала. Перед скрытием —
   столько же, иначе до самой карточки не дотянуться: она исчезает, пока к ней
   ведёшь курсор. */
var showTimer = null, hideTimer = null;
var HOVER_IN = 240, HOVER_OUT = 260;

function markUnder(t) {
    return t && t.closest ? t.closest('a.ent, a.text-tag, a.side-tag') : null;
}

function armShow(a) {
    var id = idOf(a);
    if (!id) return;
    clearTimeout(hideTimer);
    clearTimeout(showTimer);
    if (cur === id && box && box.classList.contains('on')) return;
    showTimer = setTimeout(function () {
        var r = a.getBoundingClientRect();
        show(id, r.left + r.width / 2, r.bottom);
    }, HOVER_IN);
}

function armHide() {
    clearTimeout(showTimer);
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, HOVER_OUT);
}

document.addEventListener('mouseover', function (e) {
    var a = markUnder(e.target);
    if (a) {
        if (a.classList.contains('ent-nocard') || a.classList.contains('ent-sci')) return;
        armShow(a);
        return;
    }
    /* мышь внутри самой карточки — держим её открытой */
    if (box && e.target.closest && e.target.closest('.b42card')) {
        clearTimeout(hideTimer);
    }
});

document.addEventListener('mouseout', function (e) {
    var a = markUnder(e.target);
    var inCard = box && e.target.closest && e.target.closest('.b42card');
    if (a || inCard) armHide();
});

/* Палец: наведения нет, поэтому первый тап показывает карточку, а уйти можно
   кнопкой «Подробно» — иначе на телефоне определение не посмотреть вовсе. */
document.addEventListener('click', function (e) {
    if (window.matchMedia && window.matchMedia('(hover: hover)').matches) return;
    var a = markUnder(e.target);
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
    if (a.classList.contains('ent-nocard') || a.classList.contains('ent-sci')) return;
    var id = idOf(a);
    if (!id || cur === id) return;
    e.preventDefault();
    e.stopPropagation();
    var r = a.getBoundingClientRect();
    show(id, r.left + r.width / 2, r.bottom);
});

window.B42Card = {show: show, hide: hide, isOpen: function () { return pinned; }};
})();
