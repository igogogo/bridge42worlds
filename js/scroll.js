let articlesIndex = [];
// Персистим между переходами (sessionStorage) — иначе viewedIds обнулялся на каждой
// новой странице (полная навигация через window.location.href), и если у двух статей
// лучший кандидат друг на друга, кнопка "следующая" зацикливалась A→B→A→B...
let viewedIds = new Set();
try { viewedIds = new Set(JSON.parse(sessionStorage.getItem('b42_viewed') || '[]')); } catch (e) {}

function persistViewed() {
    try { sessionStorage.setItem('b42_viewed', JSON.stringify(Array.from(viewedIds))); } catch (e) {}
}

function getLang() {
    var pp = window.location.pathname.split('/');
    var langIdx = pp.indexOf('lang');
    return (langIdx >= 0 && pp[langIdx + 1]) ? pp[langIdx + 1] : 'ru';
}

var NO_MORE_ARTICLES = {
    ru: 'Больше нет статей', en: 'No more articles', es: 'No hay más artículos', zh: '没有更多文章了', fr: 'Plus d\'articles',
    ar: 'لا مزيد من المقالات'
};

/* ── Счётчик прочитанного за всё время ──────────────────────────────────────
   viewedIds выше живёт в sessionStorage и обнуляется с закрытием браузера — он про
   «не предлагать одно и то же в этой сессии». Здесь другое: сколько статей человек
   открыл ЗА ВСЁ ВРЕМЯ. По этому числу на главной появляется приглашение (js/search.js).

   Считаем ОТКРЫТЫЕ статьи, а не пролистанные карточки: сто карточек проматываются
   за минуту ленты, сто открытых статей — это месяцы жизни в проекте. Порог должен
   быть честным, иначе приглашение обесценится.

   Храним не число, а множество идентификаторов: иначе перечитывание одной статьи
   накручивало бы счётчик. Дальше порога список не растим — он не нужен, а место занимает. */
var READ_KEY = 'b42_read';
var READ_CAP = 400;          // с запасом над порогом приглашения

function countRead(id) {
    if (!id) return;
    try {
        var seen = JSON.parse(localStorage.getItem(READ_KEY) || '[]');
        if (seen.indexOf(id) !== -1) return;
        seen.push(id);
        if (seen.length > READ_CAP) seen = seen.slice(-READ_CAP);
        localStorage.setItem(READ_KEY, JSON.stringify(seen));
    } catch (e) { /* приватный режим — счётчик не ведём, приглашения просто не будет */ }
}

/* Индекс нужен ДВУМ блокам внизу статьи: «похожие» и «следующая». Оба находятся под
   текстом, и до них долистывает меньшинство — а грузился индекс всегда и сразу, 6,4 МБ
   на каждой странице статьи (замер роли «дашборд» 2026-07-31). После ночной оптимизации
   search.js на статье индекс не тянет, и scroll.js остался его единственным заказчиком:
   экономия не состоялась, просто сменился виновник.

   Взял ленивую загрузку, а НЕ latest-индекс (150 КБ), хотя он и предлагался. Причина:
   latest — это шестьдесят самых свежих статей, и «похожие по тегам» для статьи двухлетней
   давности искались бы среди них — то есть блок бы остался, а смысл из него ушёл. Здесь
   дешевле отложить, чем ухудшить: кто долистал до блоков, получает те же данные, что и
   раньше, кто не долистал — не платит за них ничего.

   Загрузку начинаем заранее (rootMargin), чтобы к моменту появления блока данные уже были;
   без IntersectionObserver — грузим сразу, как раньше. */
function whenNeeded(fn) {
    var marks = [document.getElementById('related')].concat(
        Array.prototype.slice.call(document.querySelectorAll('.next-btn')));
    marks = marks.filter(Boolean);
    if (!marks.length) { fn(); return; }

    var fired = false;
    function go() {
        if (fired) return;
        fired = true;
        if (io) io.disconnect();
        EVENTS.forEach(function (e) { window.removeEventListener(e, go); });
        fn();
    }

    // Два независимых повода загрузить, и достаточно любого.
    // 1) блок подошёл к экрану — обычный случай;
    // 2) читатель вообще шевельнулся — страховка: IntersectionObserver молчит, когда
    //    высота окна нулевая (скрытая панель, фоновая вкладка), и без неё блоки внизу
    //    остались бы пустыми навсегда. Таймаут сюда не годится: он сработал бы у всех,
    //    и экономия снова исчезла бы.
    var EVENTS = ['scroll', 'pointerdown', 'keydown', 'wheel', 'touchstart'];
    EVENTS.forEach(function (e) { window.addEventListener(e, go, { once: true, passive: true }); });

    var io = null;
    if (typeof IntersectionObserver === 'function') {
        io = new IntersectionObserver(function (entries) {
            for (var i = 0; i < entries.length; i++) {
                if (entries[i].isIntersecting) { go(); return; }
            }
        }, { rootMargin: '800px 0px' });   // с запасом: успеть загрузить до появления блока
        marks.forEach(function (m) { io.observe(m); });
    }
}

async function initScroll() {
    var lang = getLang();
    var path = window.location.pathname;
    var version = path.indexOf('advanced.html') !== -1 ? 'advanced'
                : (path.indexOf('simple.html') !== -1 ? 'simple'
                : (path.indexOf('mini.html') !== -1 ? 'mini' : 'popular'));
    try { localStorage.setItem('b42_version', version); } catch(e) {}

    // Счётчик прочитанного и «просмотрено в этой сессии» индекса не требуют — считаем сразу,
    // иначе статья не засчиталась бы тем, кто её не долистал.
    var currentId = document.querySelector('[data-article-id]')?.dataset.articleId;
    // data-article-id теперь составной: id_lang_version. Выделяем чистый arXiv id.
    if (currentId) {
        var parts = currentId.split('_');
        // arXiv id: 2607.00565, иногда с версией — 2607.00565v1. Версия НЕОБЯЗАТЕЛЬНА:
        // требование «v и цифра» ломало отсечение, id оставался составным
        // (2606.31362_en_popular) и не совпадал ни с чем в индексе. Отсюда два бага:
        // статья попадала в собственный список похожих, а «прочитанное» копилось
        // под мусорными ключами, и «следующая статья» предлагала уже прочитанное.
        if (parts.length >= 2 && /^\d{4}\.\d{4,5}(v\d+)?$/.test(parts[0])) {
            currentId = parts[0];
        }
        viewedIds.add(currentId);
        persistViewed();
        countRead(currentId);
    }

    whenNeeded(async function () {
        // Общий промис из search.js — но только когда он про ТОТ ЖЕ уровень чтения.
        // search.js держит индекс выбранного в ленте уровня, а страница может быть другого:
        // на advanced.html при «популярно» в ленте мы бы показали чужие заголовки. Ссылки
        // тир правит сам (urlForVersion), а вот подписи взялись бы не те — поэтому сверяем.
        var sameTier = typeof window.effVersion === 'function'
            && window.effVersion() === (version === 'mini' ? 'popular' : version);
        // ИНДЕКС ЗДЕСЬ БОЛЬШЕ НЕ КАЧАЕТСЯ САМ. Он нужен был двум блокам: «похожие»
        // и кнопке «следующая». Оба теперь питаются ответом /api/side (7 КБ), который
        // приходит в начале страницы. Качать 14.6 МБ ради того же — та же ошибка, что
        // и на ленте, только на самой посещаемой странице сайта.
        //
        // ЗАПАСНОГО ПУТИ БОЛЬШЕ НЕТ. Здесь стояло: облако промолчало — поднимаем индекс
        // и ищем по тегам, как раньше. Ровно этот путь и держал сорок мегабайт живыми:
        // пока он есть, его зовут. Владелец 2026-09-01: «никаких индексов в браузере,
        // никаких запасных путей». Молчит облако — блока «похожие» просто нет; это
        // честнее, чем качать архив ради трёх ссылок внизу страницы.
        if (window.__sidePool && window.__sidePool.length) {
            updateNextButton(version);
            return;
        }
        return;
    });
}

// mini переиспользует индекс popular (у него нет своего) — url в записях индекса
// всегда указывает на index.html/simple.html/advanced.html СВОЕГО индекса, а не на
// mini.html. Раз мы читаем чужой индекс, URL надо перезаписать на текущий тир вручную,
// иначе ссылки "похожие статьи"/"следующая" из mini уводят на popular (баг из фидбека).
var TIER_FILE = { popular: 'index.html', simple: 'simple.html', advanced: 'advanced.html', mini: 'mini.html' };
function urlForVersion(url, version) {
    var file = TIER_FILE[version];
    if (!file) return url;
    return url.replace(/\/[^\/]+$/, '/' + file);
}

/* Похожие статьи: сначала СМЫСЛ, тегами добираем.
 *
 * Владелец 2026-08-02: «вектор строили как раз для этого — связь статей напрямую; можно
 * ссылок понаставить по тексту, это будет эффектно».
 *
 * Раньше «похожие» подбирались по совпадению тегов. Тег — грубая мерка: две работы про
 * «энтропию» бывают о совершенно разном, а работа про приливные силы и работа про
 * деформацию звёзд общего тега могут не иметь вовсе. data/related-vec.json содержит
 * связи, посчитанные по САМИМ ТЕКСТАМ (tools/vector_links_local.py): 6313 связей,
 * 88% статей. Где смысловой связи нет — остаётся прежний подбор по тегам, чтобы блок
 * не пустовал.
 */
var _relVec = null;

/* Похожие из облака — ПЕРВЫЙ путь. Один запрос на 7 КБ отдаёт готовые карточки похожих
   и цитируемых; старый путь ниже качал ради того же related-vec.json плюс ПОЛНЫЙ индекс
   языка (3.7 МБ по сети) — самый дорогой блок на странице статьи. Старый путь оставлен
   запасным: облако молчит — читатель видит ровно то, что видел до этого модуля. */
function sideArgs() {
    var args = window.__relatedArgs;
    if (args) return args;
    var el = document.querySelector('[data-article-id]');
    var raw = el ? el.dataset.articleId : '';
    var id = (raw.split('_')[0] || '');
    if (!/^\d{4}\.\d{4,5}(v\d+)?$/.test(id)) return null;
    var path = location.pathname;
    var ver = path.indexOf('advanced.html') !== -1 ? 'advanced'
            : (path.indexOf('simple.html') !== -1 ? 'simple'
            : (path.indexOf('mini.html') !== -1 ? 'mini' : 'popular'));
    return [id, getLang(), ver];
}

(function () {
    var args = sideArgs();
    if (!args || !document.getElementById('related')) return legacyRelated();
    var v = args[2] === 'mini' ? 'popular' : args[2];
    fetch('/api/side?id=' + encodeURIComponent(args[0]) +
          '&lang=' + args[1] + '&version=' + v)
        .then(function (r) { if (!r.ok) throw 0; return r.json(); })
        .then(function (d) {
            // Упомянутые едут тем же ответом и рисуются независимо от похожих:
            // у статьи может не быть соседей, а подсказки к чтению — есть.
            drawMentions(d && d.mentions, args[1]);
            var box = document.getElementById('related');
            if (d && d.related && d.related.length && box) {
                drawRelated(box, d.related.map(function (a) { return { a: a }; }),
                            args[1], args[2]);
                // Тем же ответом питаем кнопку «следующая статья». Раньше она ждала
                // индекс на 14.6 МБ и до того молчала — читатель, долиставший быстро,
                // видел кнопку без цели.
                window.__sidePool = d.related.concat(d.cited || []);
                updateNextButton(args[2]);
            } else {
                legacyRelated();
            }
        })
        .catch(legacyRelated);
})();

/* УПОМЯНУТЫЕ В ТЕКСТЕ — тихим рядом под плашками.

   Зачем вообще. Слово в тексте подсвечено и ведёт на понятие, а в колонке этого
   понятия нет: плашки считает вектор с поправкой на хабность и общие понятия
   отбрасывает намеренно (требование владельца 26.08 — «к общим не привязывать»).
   Обе разметки правы, но читатель видел несогласие. Показываем вторую связь
   рядом и НЕ вместо: слить их значило бы вернуть хабы в граф.

   Разметку колонки не трогаем — находим её по уже стоящим плашкам и дописываем
   ряд. Поэтому пересборка сайта для этого не нужна. */
var MENTIONS_LBL = {
    ru: 'Упомянуты', en: 'Mentioned', es: 'Mencionados',
    ar: 'مذكورة', fr: 'Mentionnés'
};

function drawMentions(list, lang) {
    if (!list || !list.length) return;
    var side = document.querySelector('.article-side');
    if (!side || side.querySelector('.side-mention')) return;
    /* Уже стоящее плашкой не повторяем: одно понятие в двух рядах читается как
       ошибка, а не как два разных утверждения. */
    var have = {};
    Array.prototype.forEach.call(
        side.querySelectorAll('[data-tag], [data-law]'), function (a) {
            have[a.dataset.tag || a.dataset.law] = 1;
        });
    var fresh = list.filter(function (m) { return m && m.id && !have[m.id]; });
    if (!fresh.length) return;
    var lbl = document.createElement('div');
    lbl.className = 'side-tags-label side-mentions-label';
    lbl.textContent = MENTIONS_LBL[lang] || MENTIONS_LBL.en;
    side.appendChild(lbl);
    fresh.slice(0, 14).forEach(function (m) {
        var a = document.createElement('a');
        a.className = 'side-mention';
        a.href = '/lang/' + lang + '/concepts/' + encodeURIComponent(m.id) + '.html';
        a.textContent = m.name || m.id.replace(/_/g, ' ');
        a.dataset.tag = m.id;          // карточка понятия цепляется тем же признаком
        side.appendChild(a);
    });
    /* Мини-графу отдаём те же понятия, но не рисуем их сами: у него свой потолок
       узлов (на телефоне десяток), и решать, влезут ли, должен он. */
    /* Мини-граф может ещё не загрузиться: обвязка приходит запросом, а b42-mini.js
       выполняется своим чередом. Кто быстрее — зависит от сети, и на проде победил
       запрос: кнопка «+ упомянуты» молча не ставилась. Ждём готовности с потолком,
       а не надеемся на порядок загрузки. */
    var g = document.getElementById('article-graph');
    if (!g) return;
    var ids = fresh.map(function (m) { return m.id; });
    var label = MENTIONS_LBL[lang] || MENTIONS_LBL.en;
    var tries = 0;
    (function ready() {
        if (window.B42Mini && window.B42Mini.addMentions) {
            window.B42Mini.addMentions(g, ids, label);
            return;
        }
        if (++tries > 40) return;      // четыре секунды; дольше ждать нечего
        setTimeout(ready, 100);
    })();
}

function legacyRelated() {
    if (window.__legacyRelStarted) return;
    window.__legacyRelStarted = 1;
    fetch('/data/related-vec.json').then(function (r) { return r.json(); })
    .then(function (m) {
        _relVec = m;
        // Рисуем блок САМИ, не дожидаясь ленивого загрузчика.
        //
        // Раньше «похожие» рисовались только из whenNeeded — обработчика, который ждёт,
        // когда блок подойдёт к экрану. На живой странице он не срабатывал вовсе (проверено
        // 2026-08-02: индекс так и оставался пустым, блок пустовал), и связи по смыслу
        // читатель не увидел бы ни разу. Ждать чужого события, чтобы показать своё, —
        // лишняя зависимость: у нас есть всё нужное, id статьи стоит прямо в разметке.
        var args = window.__relatedArgs;
        if (!args) {
            var el = document.querySelector('[data-article-id]');
            var raw = el ? el.dataset.articleId : '';
            var id = (raw.split('_')[0] || '');
            if (!/^\d{4}\.\d{4,5}(v\d+)?$/.test(id)) return;
            var path = location.pathname;
            var ver = path.indexOf('advanced.html') !== -1 ? 'advanced'
                    : (path.indexOf('simple.html') !== -1 ? 'simple'
                    : (path.indexOf('mini.html') !== -1 ? 'mini' : 'popular'));
            args = [id, getLang(), ver];
        }
        renderRelated.apply(null, args);
    }).catch(function () { _relVec = {}; });
}
/* КАРТОЧКИ ПО НОМЕРАМ — ИЗ ОБЛАКА. И «похожие», и «цитируют у нас» знают номера работ
   заранее (related-vec.json и cited-ours.json — по паре килобайт), а не хватало им только
   заголовков и адресов. За ними ходили в articles-index.json: 15.2 МБ ради трёх ссылок
   внизу страницы. Ручка /api/cards отдаёт ровно нужные карточки.
   Владелец 2026-09-01: «никаких индексов в браузере, полная динамика через облако». */
function cardsByIds(ids, lang, version) {
    var list = (ids || []).filter(Boolean).slice(0, 40);
    if (!list.length) return Promise.resolve([]);
    var api = (window.B42_API || '').replace(/\/$/, '');
    var v = version === 'mini' ? 'popular' : (version || 'popular');
    return fetch(api + '/api/cards?lang=' + encodeURIComponent(lang || 'ru') +
                 '&version=' + encodeURIComponent(v) +
                 '&ids=' + encodeURIComponent(list.join(',')))
        .then(function (r) { return r.ok ? r.json() : { items: [] }; })
        .then(function (j) { return (j && j.items) || []; })
        .catch(function () { return []; });
}

function relatedByMeaning(currentId) {
    if (!_relVec) return null;
    var near = _relVec[currentId];
    if (!near || !near.length) return null;
    var byId = {};
    articlesIndex.forEach(function (a) { if (!byId[a.id]) byId[a.id] = a; });
    return near.map(function (n) { return byId[n.id]; }).filter(Boolean).slice(0, 3);
}

function renderRelated(currentId, lang, version) {
    var box = document.getElementById('related');
    if (!box) return;
    window.__relatedArgs = [currentId, lang, version];
    /* Блок может отрисовываться раньше, чем подъехал индекс статей: у него ленивая
       загрузка (см. whenNeeded), и порядок зависит от того, как быстро читатель долистал
       и что успел кэш. Раньше в этом случае «похожие» просто оставались пустыми — молча.
       Теперь не гадаем о порядке: нет индекса — грузим и перерисовываемся. */
    if (!articlesIndex.length) {
        /* Номера соседей у нас есть (related-vec.json), не хватает их карточек —
           спрашиваем именно их, а не весь архив. */
        if (!window.__relIdxLoading) {
            window.__relIdxLoading = 1;
            var near = (_relVec && _relVec[currentId]) || [];
            cardsByIds(near.map(function (n) { return n.id; }), lang, version)
                .then(function (items) {
                    if (items.length) {
                        articlesIndex = items;
                        renderRelated(currentId, lang, version);
                        if (typeof renderCitedOurs === 'function') {
                            renderCitedOurs(currentId, lang, version);
                        }
                    }
                });
        }
        return;
    }
    var byMeaning = relatedByMeaning(currentId);
    if (byMeaning && byMeaning.length) {
        drawRelated(box, byMeaning.map(function (a) { return { a: a }; }), lang, version);
        return;
    }
    var curTags = Array.from(document.querySelectorAll('.side-tag')).map(function(e){ return e.dataset.tag || ''; });
    var scored = articlesIndex
        .filter(function(a){ return a.id !== currentId; })
        .map(function(a){ return { a: a, s: (a.tags||[]).filter(function(t){ return curTags.indexOf(t) !== -1; }).length }; })
        .filter(function(x){ return x.s > 0; })
        // При равном числе общих тегов: полный разбор выше экспресса, затем свежесть
        // (правило владельца 2026-07-31 — экспресс понижен во ВСЕХ списках, включая
        // «похожие статьи»: читатель дочитал разбор, предлагать заметку — шаг назад).
        .sort(function(p,q){ return q.s - p.s || (p.a.express?1:0) - (q.a.express?1:0)
                                    || q.a.date.localeCompare(p.a.date); })
        .slice(0, 3);
    if (!scored.length) return;
    drawRelated(box, scored, lang, version);
}

/* Отрисовка блока «похожие» — одна на оба способа подбора (по смыслу и по тегам).
   Карточки-подложки с миниатюрой, как на страницах тега/закона/учёного
   (юзер 2026-07-24: «related как в карточках тегов, на плашках с картинкой»). */
function drawRelated(box, scored, lang, version) {
    box.innerHTML = '<h3 class="related-h">' + (box.dataset.label || 'Related') + '</h3>' +
        scored.map(function(x){
            var a = x.a;
            var base = '/lang/' + (typeof defaultLang !== 'undefined' ? defaultLang : lang) + '/archive/' + a.date + '/' + a.id + '/';
            var hasImg = a.image !== false;
            var thumb = hasImg ? ('<a class="card-img-wrap" href="' + urlForVersion(a.url, version) + '">' +
                '<img src="' + base + 't_ai.webp" data-fb="' + base + 'ai.webp" loading="lazy" ' +
                'onerror="if(this.dataset.fb){this.src=this.dataset.fb;this.removeAttribute(\'data-fb\');}else{this.closest(\'.card-img-wrap\').style.display=\'none\';}" alt=""></a>') : '';
            var ol = a.oneliner ? '<div class="oneliner">' + a.oneliner + '</div>' : '';
            return '<article class="article-card">' +
                '<div class="card-eyebrow"><span class="card-date">' + a.date + '</span></div>' +
                thumb +
                '<div class="card-body"><h3><a href="' + urlForVersion(a.url, version) + '" title="' + (a.title || '').replace(/"/g, '&quot;') + '">' + a.title + '</a></h3>' +
                ol + '</div></article>';
        }).join('');
}

/* №41 «Цитатные связи»: из того, что цитирует эта статья, мы кое-что уже разбирали.
 *
 * Отличие от «похожих» принципиальное и его стоит держать в голове при правках: связь
 * здесь провёл АВТОР статьи, сославшись на работу в списке литературы, а мы её разобрали.
 * «Похожие» — наша догадка о близости, посчитанная вектором. Поэтому врезка стоит ВЫШЕ
 * похожих и подписана честно: ссылку поставил автор, разбор наш.
 *
 * Связей мало и это нормально: 271 статья из 5963 (376 переходов). Мы разбираем пять тысяч
 * работ из трёх миллионов, и совпадение чужого цитирования с нашим выбором — редкая удача.
 * Блок просто не появляется там, где связи нет.
 */
var _citedOurs = null;
function renderCitedOurs(currentId, lang, version) {
    var box = document.getElementById('cited-ours');
    if (!box || !_citedOurs) return;
    var ids = _citedOurs[currentId];
    if (!ids || !ids.length) return;
    if (!articlesIndex.length) {
        // Индекс грузим САМИ. Раньше блок ждал, пока его подтянет цепочка «похожих», а та
        // стартует только после успешной загрузки related-vec.json — стоило файлу ответить
        // 404 (проверено 19.08), и врезка молча пустовала при живых данных. Чужое событие
        // как условие своей отрисовки — та же ошибка, что уже описана выше по файлу.
        if (window.__citedIdxLoading) return;
        window.__citedIdxLoading = 1;
        cardsByIds(ids, lang, version).then(function (items) {
            if (items.length) {
                articlesIndex = items;
                renderCitedOurs(currentId, lang, version);
            }
        });
        return;
    }
    var byId = {};
    articlesIndex.forEach(function (a) { if (!byId[a.id]) byId[a.id] = a; });
    var rows = ids.map(function (id) { return byId[id]; }).filter(Boolean)
                  .map(function (a) { return { a: a, s: 1 }; });
    if (!rows.length) return;
    drawRelated(box, rows.slice(0, 3), lang, version);
    var hint = box.dataset.hint;
    if (hint) {
        var p = document.createElement('p');
        p.className = 'cited-ours-hint';
        p.textContent = hint;
        box.insertBefore(p, box.children[1] || null);
    }
}

fetch('/data/cited-ours.json').then(function (r) { return r.json(); })
    .then(function (m) {
        _citedOurs = m;
        var args = window.__relatedArgs;
        if (!args) {
            var el = document.querySelector('[data-article-id]');
            var raw = el ? el.dataset.articleId : '';
            var id = (raw.split('_')[0] || '');
            if (!/^\d{4}\.\d{4,5}(v\d+)?$/.test(id)) return;
            var path = location.pathname;
            var ver = path.indexOf('advanced.html') !== -1 ? 'advanced'
                    : (path.indexOf('simple.html') !== -1 ? 'simple'
                    : (path.indexOf('mini.html') !== -1 ? 'mini' : 'popular'));
            args = [id, getLang(), ver];
        }
        renderCitedOurs.apply(null, args);
    }).catch(function () { _citedOurs = {}; });

/* Следующая — первая непрочитанная из похожих. Похожие подобраны по СМЫСЛУ текстов,
   а перебор ниже искал по совпадению тегов: две работы про «энтропию» бывают о разном,
   и это правило уже записано выше по файлу — просто до кнопки не дошло. */
function nextFromPool() {
    var pool = window.__sidePool;
    if (!pool || !pool.length) return null;
    for (var i = 0; i < pool.length; i++) {
        if (!viewedIds.has(pool[i].id)) return pool[i];
    }
    return null;
}

function findNextArticle(currentTags, mainTag) {
    var fromPool = nextFromPool();
    if (fromPool) return fromPool;
    var candidates = articlesIndex
        .filter(function(a) { return !viewedIds.has(a.id); })
        .map(function(a) {
            return {
                id: a.id,
                title: a.title,
                oneliner: a.oneliner,
                date: a.date,
                url: a.url,
                authors: a.authors,
                tags: a.tags,
                score: a.tags.filter(function(t) { return currentTags.includes(t); }).length + (a.tags.includes(mainTag) ? 10 : 0)
            };
        })
        // «Следующая статья» — тот же порядок: при равном совпадении сначала полные.
        .sort(function(a, b) { return b.score - a.score || (a.express?1:0) - (b.express?1:0)
                                      || b.date.localeCompare(a.date); });
    return candidates[0] || articlesIndex.find(function(a) { return !viewedIds.has(a.id); });
}

function updateNextButton(version) {
    var currentTags = Array.from(document.querySelectorAll('.side-tag')).map(function(el) { return el.dataset.tag || el.textContent.trim().toLowerCase(); });
    var mainTag = currentTags[0] || '';
    var next = findNextArticle(currentTags, mainTag);
    // Дублируется вверху и внизу страницы (см. .next-top / .next-divider в article.html) —
    // оба обновляем одинаково, чтобы не долистывать при желании перейти дальше.
    var btns = document.querySelectorAll('.next-btn');
    if (!btns.length) return;
    // Стрелка по направлению письма: в RTL «дальше» визуально влево (←), в LTR — вправо (→).
    // Раньше сюда хардкодился «→», а из базовой подписи срезался только «→» (не «←») — на арабском
    // получалось «المقال التالي ← … →» (двойная разнонаправленная стрелка).
    var arr = document.documentElement.getAttribute('dir') === 'rtl' ? '←' : '→';

    btns.forEach(function(btn) {
        // Захватываем локализованный текст кнопки, отрендеренный сервером
        // ($next_label в article.html), до первой перезаписи — иначе он теряется.
        if (!btn.dataset.baseLabel) btn.dataset.baseLabel = btn.textContent.replace(/[→←]\s*$/, '').trim();
        var label = btn.dataset.baseLabel;

        if (next) {
            // Многоточие лепилось всегда, даже к заголовку в три слова, а 30 знаков
            // арабской вязи — совсем не та физическая длина, что 30 латинских: режем
            // по границе слова и только при реальном превышении. Полный заголовок и
            // подзаголовок уходят в title — переход перестаёт быть переходом вслепую.
            var full = next.title || '';
            var short = full;
            if (full.length > 34) {
                var cut = full.slice(0, 34), sp = cut.lastIndexOf(' ');
                short = (sp > 20 ? cut.slice(0, sp) : cut) + '…';
            }
            btn.textContent = label + ': ' + short + ' ' + arr;
            btn.title = full + (next.oneliner ? ' — ' + next.oneliner : '');
            btn.onclick = function() {
                viewedIds.add(next.id);
                persistViewed();
                window.location.href = urlForVersion(next.url, version);
            };
            btn.disabled = false;
        } else {
            btn.textContent = NO_MORE_ARTICLES[getLang()] || NO_MORE_ARTICLES.en;
            btn.disabled = true;
        }
    });
}

document.addEventListener('DOMContentLoaded', initScroll);

/* ── Связи под текстом статьи на телефоне (владелец 2026-07-30, живой телефон) ──
   Проблема: .article-side — соседний блок после .article-main, а .article-main на мобиле
   вырастает до ~6200px (текст + реакции + отклик + похожие). Связи оказывались НИЖЕ
   похожих статей — владелец долистал до конца и решил, что их нет вовсе. CSS тут бессилен:
   order переставляет соседей, а нужно перенести узел ВНУТРЬ main, выше реакций.
   Делаем один раз при загрузке; десктоп не трогаем (там колонка справа, position:fixed). */
(function moveSideOnMobile() {
    function apply() {
        var side = document.querySelector('.article-wrapper > .article-side');
        var main = document.querySelector('.article-wrapper > .article-main');
        if (!side || !main) return;
        var narrow = window.matchMedia('(max-width: 640px)').matches;
        if (narrow && !side.dataset.movedIn) {
            // Место выбрано владельцем (2026-07-30): ПЕРЕД похожими статьями.
            // Логика: «похожие» — это «куда пойти дальше», а связи — «из чего эта статья»,
            // значит связи идут раньше. Ставим перед #related; если его нет — перед
            // реакциями, чтобы всё равно не уехать в самый хвост.
            var anchor = main.querySelector('#related, .related')
                      || main.querySelector('.actions, .lv-bottom, .feedback')
                      || null;
            main.insertBefore(side, anchor);
            side.dataset.movedIn = '1';
            side.classList.add('article-side-inline');
        } else if (!narrow && side.dataset.movedIn) {
            document.querySelector('.article-wrapper').appendChild(side);
            delete side.dataset.movedIn;
            side.classList.remove('article-side-inline');
        }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply);
    else apply();
    window.addEventListener('resize', apply);
})();
