let searchIndex = [];
let tagsLoc = {};
let scientistsData = {};
let lawsData = {};
let authorsGraph = {};
// Уровни сложности: popular (по умолчанию) → simple → advanced.
var VERSION_INDEX_FILES = { popular: 'articles-index.json', simple: 'articles-index-simple.json',
                            advanced: 'articles-index-advanced.json' };
// Маленький индекс последних статей (~60 записей) — для мгновенной первой ленты, пока
// полный тир (~3.6МБ) едет в фоне.
var VERSION_INDEX_LATEST_FILES = { popular: 'articles-latest.json', simple: 'articles-latest-simple.json',
                                   advanced: 'articles-latest-advanced.json' };
let currentVersion = (function() {
    try { return localStorage.getItem('b42_version') || 'popular'; } catch(e) { return 'popular'; }
})();
// «мини» — не отдельный индекс, а режим ленты (полный threads-текст). Работает только там,
// где есть кнопка «мини» (главная). На прочих страницах трактуем как popular, чтобы ленты/описания не пустовали.
if (currentVersion === 'mini' && !document.querySelector('[data-version="mini"]')) currentVersion = 'popular';
// Эффективная версия для выборки статей: мини берёт popular-статьи.
function effVersion() { return currentVersion === 'mini' ? 'popular' : currentVersion; }
window.__favoritesPage = /\/favorites(\.html)?([?#]|$)/.test(location.pathname);

// Тёмная тема: применяем сохранённый выбор как можно раньше, чтобы не мигало светлым.
(function initTheme() {
    try {
        if (localStorage.getItem('b42_theme') === 'dark')
            document.documentElement.setAttribute('data-theme', 'dark');
    } catch (e) {}
})();
function toggleTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (dark) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', 'dark');
    try { localStorage.setItem('b42_theme', dark ? 'light' : 'dark'); } catch (e) {}
    var b = document.getElementById('theme-toggle');
    if (b) b.textContent = dark ? '☾' : '☀';
}
window.toggleTheme = toggleTheme;
document.addEventListener('DOMContentLoaded', function() {
    var host = document.querySelector('.header-right') || document.getElementById('langs-bar');
    if (host && !document.getElementById('theme-toggle')) {
        var b = document.createElement('button');
        b.id = 'theme-toggle'; b.type = 'button'; b.className = 'theme-toggle';
        b.setAttribute('aria-label', 'Theme');
        b.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? '☀' : '☾';
        b.addEventListener('click', toggleTheme);
        host.appendChild(b);
    }
});

function getLang() {
    var pp = window.location.pathname.split('/');
    var langIdx = pp.indexOf('lang');
    return (langIdx >= 0 && pp[langIdx + 1]) ? pp[langIdx + 1] : 'ru';
}

function getDefaultLang() {
    return 'ru';
}

function getPagePath() {
    var pp = window.location.pathname.split('/');
    var langIdx = pp.indexOf('lang');
    if (langIdx >= 0 && pp.length > langIdx + 2) {
        return '/' + pp.slice(langIdx + 2).join('/');
    }
    return '/index.html';
}

var lang = getLang();
var defaultLang = getDefaultLang();
var pagePath = getPagePath();

var UI_STRINGS = {
    ru: { tagNotFound: 'Тег не найден', selectTag: 'Выберите тег:', scientistNotFound: 'Учёный не найден',
          selectScientist: 'Выберите учёного:', authorNotFound: 'Автор не найден', selectAuthor: 'Выберите автора:',
          articlesWord: 'статей', noResults: 'Ничего не найдено', more: 'Подробнее →', profile: 'Профиль →', moreWord: 'ещё', min: 'мин',
          express: 'экспресс', expressTip: 'Экспресс: быстрый пересказ по авторской аннотации. Полные статьи мы пишем по всему тексту работы — глубже и подробнее.',
          hideExpress: 'Скрыть экспресс-статьи', showLess: 'Свернуть',
          favTitle: 'Избранное', like: 'Нравится', dislike: 'Не нравится', superlike: 'Супер!',
          refineTip: 'Отшлифовано редактором' },
    en: { tagNotFound: 'Tag not found', selectTag: 'Select a tag:', scientistNotFound: 'Scientist not found',
          selectScientist: 'Select a scientist:', authorNotFound: 'Author not found', selectAuthor: 'Select an author:',
          articlesWord: 'articles', noResults: 'Nothing found', more: 'More →', profile: 'Profile →', moreWord: 'more', min: 'min',
          express: 'express', expressTip: 'Express: a quick take from the author\'s abstract only. Full articles are written from the whole paper — deeper and more detailed.',
          hideExpress: 'Hide express articles', showLess: 'Collapse',
          favTitle: 'Favorites', like: 'Like', dislike: 'Dislike', superlike: 'Super!',
          refineTip: 'Polished by an editor' },
    es: { tagNotFound: 'Etiqueta no encontrada', selectTag: 'Elige una etiqueta:', scientistNotFound: 'Científico no encontrado',
          selectScientist: 'Elige un científico:', authorNotFound: 'Autor no encontrado', selectAuthor: 'Elige un autor:',
          articlesWord: 'artículos', noResults: 'Nada encontrado', more: 'Más →', profile: 'Perfil →', moreWord: 'más', min: 'min',
          express: 'exprés', expressTip: 'Exprés: un resumen rápido solo del abstract del autor. Los artículos completos se escriben a partir de todo el texto.',
          hideExpress: 'Ocultar artículos exprés', showLess: 'Contraer',
          favTitle: 'Favoritos', like: 'Me gusta', dislike: 'No me gusta', superlike: '¡Genial!',
          refineTip: 'Pulido por un editor' },
    zh: { tagNotFound: '未找到标签', selectTag: '选择标签：', scientistNotFound: '未找到科学家',
          selectScientist: '选择科学家：', authorNotFound: '未找到作者', selectAuthor: '选择作者：',
          articlesWord: '篇文章', noResults: '未找到结果', more: '详情 →', profile: '主页 →', moreWord: '更多', min: '分钟',
          express: '速览', expressTip: '速览版：基于作者摘要，未解析全文', hideExpress: '隐藏速览文章', showLess: '收起',
          favTitle: '收藏', like: '喜欢', dislike: '不喜欢', superlike: '太赞了！',
          refineTip: '编辑润色' },
    fr: { tagNotFound: 'Tag introuvable', selectTag: 'Choisir un tag :', scientistNotFound: 'Scientifique introuvable',
          selectScientist: 'Choisir un scientifique :', authorNotFound: 'Auteur introuvable', selectAuthor: 'Choisir un auteur :',
          articlesWord: 'articles', noResults: 'Aucun résultat', more: 'En savoir plus →', profile: 'Profil →', moreWord: 'autres', min: 'min',
          express: 'express', expressTip: 'Version express : basée sur le résumé de l\'auteur, pas le texte complet',
          hideExpress: 'Masquer les articles express', showLess: 'Réduire',
          favTitle: 'Favoris', like: 'J\'aime', dislike: 'Je n\'aime pas', superlike: 'Génial !',
          refineTip: 'Peaufiné par un éditeur' },
    ar: { tagNotFound: 'الوسم غير موجود', selectTag: 'اختر وسمًا:', scientistNotFound: 'العالم غير موجود',
          selectScientist: 'اختر عالمًا:', authorNotFound: 'المؤلف غير موجود', selectAuthor: 'اختر مؤلفًا:',
          articlesWord: 'مقالات', noResults: 'لا نتائج', more: 'المزيد ←', profile: 'الملف ←', moreWord: 'آخرون', min: 'دقيقة',
          express: 'سريع', expressTip: 'سريع: ملخّص سريع من خلاصة المؤلف فقط. أما المقالات الكاملة فتُكتب من النص الكامل — أعمق وأكثر تفصيلاً.',
          hideExpress: 'إخفاء المقالات السريعة', showLess: 'طي',
          favTitle: 'المفضلة', like: 'إعجاب', dislike: 'عدم إعجاب', superlike: 'رائع!',
          refineTip: 'تم صقله بواسطة محرر' }
};
var UI = UI_STRINGS[lang] || UI_STRINGS.en;

// Заполняется из /data/arxiv-categories.json (единый источник — ARXIV_CATEGORIES в gen_base.py),
// см. Promise.all ниже — раньше тут была отдельная хардкоженная копия, расходившаяся с сервером.
var ARXIV_CAT_NAMES = {};
window.ARXIV_CAT_NAMES = ARXIV_CAT_NAMES;
// Развёрнутые описания (англ., официальный текст arXiv) — для title= у бейджей категорий,
// см. ARXIV_CATEGORY_DESCRIPTIONS в gen_base.py / data/arxiv-category-descriptions.json.
var ARXIV_CAT_DESC = {};
window.ARXIV_CAT_DESC = ARXIV_CAT_DESC;

var resultsEl = document.getElementById('search-results');
// Тег-страница передаёт один id, страница закона — ВСЕ свои теги через запятую (закон
// показывает статьи, у которых есть ХОТЯ БЫ ОДИН из его тегов — раньше здесь бралась только
// первая точка, из-за чего «Статьи по теме» у закона могли уйти в пустоту, если первый по
// алфавиту тег закона случайно оказывался образовательным и ни разу не встречался в статьях).
var pageContext = {
    tags: resultsEl && resultsEl.dataset.contextTag ? resultsEl.dataset.contextTag.split(',').filter(Boolean) : [],
    scientist: resultsEl ? (resultsEl.dataset.contextScientist || '') : '',
    author: resultsEl ? (resultsEl.dataset.contextAuthor || '') : '',
    category: resultsEl ? (resultsEl.dataset.contextCategory || '') : ''  // страница раздела arXiv
};
pageContext.tag = pageContext.tags[0] || ''; // назад-совместимость: код, читающий одиночный tag (напр. filters.tags UI), видит первый

function applyPageContext(results) {
    if (pageContext.tags.length) {
        results = results.filter(function(item) {
            return pageContext.tags.some(function(t) { return (item.tags || []).indexOf(t) !== -1; });
        });
    }
    if (pageContext.scientist) {
        results = results.filter(function(item) { return (item.scientists || []).indexOf(pageContext.scientist) !== -1; });
    }
    if (pageContext.author) {
        results = results.filter(function(item) {
            return (item.authors || []).some(function(a) { return authorSlug(a) === pageContext.author; });
        });
    }
    if (pageContext.category) {
        results = results.filter(function(item) { return (item.categories || []).indexOf(pageContext.category) !== -1; });
    }
    if (hideExpress) {
        results = results.filter(function(item) { return !item.express; });
    }
    return results;
}

// Глобальный тумблер «скрыть экспресс-статьи» — персистится в localStorage, применяется через
// applyPageContext() (общий фильтр-чокпоинт для showLatest/filterByDate/applyCategoryFilter/doSearch).
var hideExpress = false;
try { hideExpress = localStorage.getItem('b42_hide_express') === '1'; } catch (e) {}

function initExpressFilter() {
    var cb = document.getElementById('express-filter-toggle');
    if (!cb) return;
    var label = document.getElementById('express-filter-label');
    if (label) label.textContent = UI.hideExpress;
    cb.checked = hideExpress;
    cb.onchange = function() {
        hideExpress = cb.checked;
        try { localStorage.setItem('b42_hide_express', hideExpress ? '1' : '0'); } catch (e) {}
        // Тумблер — глобальный фильтр поверх текущего вида; проще всего сбросить на «последние»,
        // чем пытаться помнить, какой именно фильтр (дата/категория/поиск) был активен.
        _defaultFeed();
    };
}
window.initExpressFilter = initExpressFilter;

fetch('/config.json')
    .then(function(r) { return r.json(); })
    .then(function(data) {
        var bar = document.getElementById('langs-bar');
        if (bar && data.languages) {
            // Страница автора существует только в одном языке (карточка = только имя, переводить нечего).
            // Поэтому переключатель языка не ведёт на несуществующую страницу, а меняет язык списка статей на месте.
            if (pageContext.author) {
                bar.innerHTML = data.languages.map(function(l) {
                    return '<a href="javascript:void(0)" data-l="' + l + '" onclick="switchFeedLang(\'' + l + '\')" class="' + (l === lang ? 'active' : '') + '">' + l.toUpperCase() + '</a>';
                }).join(' ');
            } else {
                bar.innerHTML = data.languages.map(function(l) {
                    return '<a href="/lang/' + l + pagePath + '" class="' + (l === lang ? 'active' : '') + '">' + l.toUpperCase() + '</a>';
                }).join(' ');
            }
        }
    }).catch(function() {});

// Переключает язык ленты статей на месте (для страниц, существующих в одном языке — автор).
function switchFeedLang(l) {
    lang = l;
    Promise.all([
        fetch('/lang/' + l + '/' + VERSION_INDEX_FILES.popular).then(function(r) { return r.json(); }).catch(function() { return []; }),
        fetch('/lang/' + l + '/' + VERSION_INDEX_FILES.simple).then(function(r) { return r.json(); }).catch(function() { return []; }),
        fetch('/lang/' + l + '/' + VERSION_INDEX_FILES.advanced).then(function(r) { return r.json(); }).catch(function() { return []; })
    ]).then(function(res) {
        searchIndex = res[0].concat(res[1]).concat(res[2]);
        window.searchIndex = searchIndex;
        showLatest();
        var bar = document.getElementById('langs-bar');
        if (bar) bar.querySelectorAll('a').forEach(function(a) { a.classList.toggle('active', a.getAttribute('data-l') === l); });
    });
}
window.switchFeedLang = switchFeedLang;

var tagsPath = '/lang/' + lang + '/data/tags.json';
var scientistsPath = '/lang/' + lang + '/data/scientists.json';

function fetchIndex(version) {
    return fetch('/lang/' + lang + '/' + VERSION_INDEX_FILES[version])
        .then(function(r) { return r.json(); }).catch(function() { return []; });
}

// Первая отрисовка ленты не должна ждать ~20МБ данных (3 тира индекса + граф авторов +
// теги/законы/учёные) — раньше все они грузились одним Promise.all ПЕРЕД первым showLatest(),
// из-за чего главная страница висела пустой, пока не скачается и не распарсится всё разом
// (граф авторов сам по себе ~7МБ на 11000+ авторов). Теперь: сначала грузим ТОЛЬКО индекс
// текущего тира (нужен для видимой ленты прямо сейчас) — отрисовываем немедленно; всё
// остальное (два других тира для переключалки сложности, теги/учёные/законы для тултипов,
// граф авторов) грузится ПАРАЛЛЕЛЬНО, но не блокирует первую отрисовку.
// Двухступенчатая загрузка ленты. Шаг 1: крошечный latest-индекс (~60 свежих записей, ~150КБ)
// рисует ленту почти мгновенно, не дожидаясь полного тира (~3.6МБ) — юзер 2026-07-23: «долго
// грузится первый раз». Фильтры/календарь/статистика/поиск требуют полного набора, поэтому
// висят до шага 2, но пользователь уже видит ленту. На избранном latest не нужен — там свой
// источник (localStorage), сразу грузим полный.
function fetchLatest(version) {
    return fetch('/lang/' + lang + '/' + VERSION_INDEX_LATEST_FILES[version])
        .then(function(r) { if (!r.ok) throw 0; return r.json(); });
}

var _fullIndexPromise = fetchIndex(effVersion());  // стартуем полный индекс сразу, параллельно latest

if (!window.__favoritesPage) {
    fetchLatest(effVersion()).then(function(latest) {
        if (searchIndex.length) return;   // полный уже успел прийти — latest не нужен
        searchIndex = latest;
        window.searchIndex = searchIndex;
        var container = document.getElementById('search-results');
        if (container && !document.querySelector('.search-box')?.value) _defaultFeed();
    }).catch(function() {});
}

_fullIndexPromise.then(function(primary) {
    searchIndex = primary;   // полный индекс заменяет latest — лента, поиск, фильтры на полном наборе
    window.searchIndex = searchIndex;

    var container = document.getElementById('search-results');
    if (container && !document.querySelector('.search-box')?.value) {
        _defaultFeed();
    }
    if (window.__favoritesPage) {
        ['calendar-btn', 'calendar-panel', 'category-bar'].forEach(function(id) { var e = document.getElementById(id); if (e) e.style.display = 'none'; });
    } else {
        initCalendar();
        initCategoryBar();
        initExpressFilter();
    }
    initAllTooltips();
    renderSiteStats();
}).catch(function(e) {
    console.error('Init error:', e);
});

var OTHER_VERSIONS = ['popular', 'simple', 'advanced'].filter(function(v) { return v !== effVersion(); });
Promise.all(
    OTHER_VERSIONS.map(fetchIndex).concat([
        fetch(tagsPath).then(function(r) { return r.json(); }).catch(function() {
            return fetch('/lang/' + defaultLang + '/data/tags.json').then(function(r) { return r.json(); });
        }),
        fetch(scientistsPath).then(function(r) { return r.json(); }).catch(function() {
            return fetch('/lang/' + defaultLang + '/data/scientists.json').then(function(r) { return r.json(); });
        }),
        fetch('/lang/' + lang + '/data/laws.json').then(function(r) { return r.json(); }).catch(function() { return {}; }),
        // Локализованный набор названий/описаний разделов, с откатом на английскую базу —
        // она же остаётся источником для lang=en и для категорий, перевода которых ещё нет.
        fetch('/data/arxiv-categories-' + lang + '.json').then(function(r) {
            if (!r.ok) throw 0; return r.json();
        }).catch(function() {
            return fetch('/data/arxiv-categories.json').then(function(r) { return r.json(); }).catch(function() { return {}; });
        }),
        fetch('/data/arxiv-category-descriptions-' + lang + '.json').then(function(r) {
            if (!r.ok) throw 0; return r.json();
        }).catch(function() {
            return fetch('/data/arxiv-category-descriptions.json').then(function(r) { return r.json(); }).catch(function() { return {}; });
        })
    ])
).then(function(results) {
    var otherIndexes = results.slice(0, OTHER_VERSIONS.length);
    var rest = results.slice(OTHER_VERSIONS.length);

    var byVersion = {};
    byVersion[effVersion()] = searchIndex;
    OTHER_VERSIONS.forEach(function(v, i) { byVersion[v] = otherIndexes[i]; });
    searchIndex = (byVersion.popular || []).concat(byVersion.simple || []).concat(byVersion.advanced || []);
    window.searchIndex = searchIndex;

    tagsLoc = rest[0];
    scientistsData = rest[1];
    lawsData = rest[2] || {};
    // Единый источник правды для названий разделов arXiv — Python-словарь ARXIV_CATEGORIES
    // (gen_base.py), экспортируемый в data/arxiv-categories.json. Раньше тут была отдельная
    // хардкоженная копия, которая расходилась с серверной при каждом добавлении категории.
    Object.assign(ARXIV_CAT_NAMES, rest[3] || {});
    Object.assign(ARXIV_CAT_DESC, rest[4] || {});

    window.tagsLoc = tagsLoc;
    window.scientistsData = scientistsData;
    window.lawsData = lawsData;

    renderSiteStats();
    // Граф авторов — 8.9МБ, самый тяжёлый файл сайта, а нужен он лишь для @-подсказок, тултипа
    // автора и счётчика в статистике. Раньше он качался в одном Promise.all со справочниками и
    // индексами и отъедал канал у самого индекса поиска — из-за чего поиск «долго думал» перед
    // первой выдачей. Теперь стартует только после лёгкой волны (и подтягивается по требованию).
    ensureAuthorsGraph();
    // Первая лента уже отрисована с тегами как raw id (tagsLoc ещё не пришёл) — теперь, когда
    // справочники подгрузились, перерисовываем дефолтный фид начисто, чтобы подтянуть красивые
    // названия тегов. Если пользователь уже начал искать — его результаты не трогаем.
    var container = document.getElementById('search-results');
    if (container && !document.querySelector('.search-box')?.value) {
        _defaultFeed();
    }
}).catch(function(e) {
    console.error('Background data load error:', e);
});

// Ленивая загрузка графа авторов: один общий промис, сколько бы раз ни позвали.
var _authorsGraphPromise = null;
function ensureAuthorsGraph() {
    if (_authorsGraphPromise) return _authorsGraphPromise;
    _authorsGraphPromise = fetch('/data/authors-graph.json')
        .then(function(r) { return r.json(); })
        .catch(function() { return {}; })
        .then(function(g) {
            authorsGraph = g || {};
            window.authorsGraph = authorsGraph;
            renderSiteStats();   // счётчик авторов появляется, как только граф доехал
            return authorsGraph;
        });
    return _authorsGraphPromise;
}
window.ensureAuthorsGraph = ensureAuthorsGraph;

// Служебная строка-статистика: всё в ОДНУ строку через « / » (юзер 2026-07-24) — статьи (полные +
// express), законы, теги, разделы, учёные, авторы, языки. Ключи-подписи локализованы.
var STATS_LABELS2 = {
    ru: {articles:'статей', full:'полных', express:'экспресс', laws:'законов', tags:'тегов', sections:'разделов', scientists:'учёных', authors:'авторов', langs:'языка'},
    en: {articles:'articles', full:'full', express:'express', laws:'laws', tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages'},
    es: {articles:'artículos', full:'completos', express:'exprés', laws:'leyes', tags:'etiquetas', sections:'secciones', scientists:'científicos', authors:'autores', langs:'idiomas'},
    ar: {articles:'مقالات', full:'كاملة', express:'سريعة', laws:'قوانين', tags:'وسوم', sections:'أقسام', scientists:'علماء', authors:'مؤلفين', langs:'لغات'}
};
function renderSiteStats() {
    var el = document.getElementById('site-stats');
    if (!el) return;
    var L = STATS_LABELS2[lang] || STATS_LABELS2.en;
    var uniq = {}, express = 0;
    searchIndex.forEach(function(a){ if (!uniq[a.id]) { uniq[a.id] = 1; if (a.express) express++; } });
    var nA = Object.keys(uniq).length, full = nA - express;
    var nL = Object.keys(window.lawsData || {}).length;
    var nT = Object.keys(window.tagsLoc || {}).length;
    var nSec = Object.keys(window.ARXIV_CAT_NAMES || {}).length;
    var nS = Object.keys(window.scientistsData || {}).length;
    var nAu = Object.keys(window.authorsGraph || {}).length;
    var nLang = (document.querySelectorAll('#langs-bar a').length || 4);
    function part(n, w){ return '<b>' + n + '</b> ' + w; }
    var bits = [
        part(nA, L.articles) + ' (' + full + ' ' + L.full + ' · ' + express + ' ' + L.express + ')',
        part(nL, L.laws), part(nT, L.tags), part(nSec, L.sections),
        part(nS, L.scientists), part(nAu, L.authors), part(nLang, L.langs)
    ];
    el.innerHTML = bits.join(' / ');
    if (!el.dataset.builtLoaded) {
        el.dataset.builtLoaded = '1';
        var upd = {ru:'обновлено', en:'updated', es:'actualizado', ar:'حُدّث'}[lang] || 'updated';
        fetch('/data/build-info.json').then(function(r){ return r.json(); }).then(function(b){
            if (b && b.built) el.innerHTML += ' <span class="stats-built">/ ' + upd + ' ' + b.built + '</span>';
        }).catch(function(){});
    }
}

function parseSearchQuery(query) {
    var filters = { tags: [], authors: [], scientists: [], text: '' };
    var parts = query.split(/\s+/);
    var textParts = [];
    for (var i = 0; i < parts.length; i++) {
        var part = parts[i];
        if (part.startsWith('#') && part.length > 1) filters.tags.push(part.slice(1).toLowerCase());
        else if (part.startsWith('@') && part.length > 1) filters.authors.push(part.slice(1).toLowerCase().replace(/_/g, ' '));
        else if (part.startsWith('!') && part.length > 1) filters.scientists.push(part.slice(1).toLowerCase());
        else textParts.push(part);
    }
    filters.text = textParts.join(' ').toLowerCase();
    return filters;
}

function doSearch(query) {
    var container = document.getElementById('search-results');
    if (!container) return;
    renderActiveFilters(query);
    if (!query || query.trim().length === 0) { showLatest(); return; }

    // Подсказки решаются по ПОСЛЕДНЕМУ токену — так можно набрать
    // "#supernova #star" и получить дропдаун только для второго тега,
    // а не заново фильтровать по всей строке.
    var tokens = query.split(/\s+/);
    var last = tokens[tokens.length - 1];

    if (last === '#') { showTagSuggestions(''); return; }
    if (last === '!') { showScientistSuggestions(''); return; }
    if (last === '@') { showAuthorSuggestions(''); return; }
    if (last.startsWith('#') && last.length > 1) { showTagSuggestions(last.slice(1).toLowerCase()); return; }
    if (last.startsWith('!') && last.length > 1) { showScientistSuggestions(last.slice(1).toLowerCase()); return; }
    if (last.startsWith('@') && last.length > 1) { showAuthorSuggestions(last.slice(1).toLowerCase()); return; }

    doFullSearch(query);
}

// searchIndex после догрузки — конкатенация трёх тиров (~60k записей), а отбор нужного тира
// шёл заново на КАЖДЫЙ символ ввода. Кэшируем срез по (ссылка на индекс, версия) — обе меняются
// редко (догрузка тиров, переключалка сложности), так что инвалидация тривиальна.
var _verSliceCache = { src: null, ver: null, out: null };
function versionSlice() {
    var v = effVersion();
    if (_verSliceCache.src === searchIndex && _verSliceCache.ver === v) return _verSliceCache.out;
    var out = searchIndex.filter(function(item) { return item.version === v; });
    _verSliceCache = { src: searchIndex, ver: v, out: out };
    return out;
}

function doFullSearch(query) {
    var container = document.getElementById('search-results');
    renderActiveFilters(query);
    var filters = parseSearchQuery(query);
    var results = versionSlice().slice();
    results = applyPageContext(results);

    if (filters.tags.length) {
        results = results.filter(function(item) {
            return filters.tags.some(function(t) {
                return item.tags.some(function(itemTag) {
                    if (itemTag === t) return true;
                    var tagName = (window.tagsLoc[itemTag]?.name || '').toLowerCase();
                    return tagName === t || tagName.includes(t);
                });
            });
        });
    }
    if (filters.authors.length) {
        results = results.filter(function(item) {
            return filters.authors.some(function(a) {
                return item.authors.some(function(ia) { return ia.toLowerCase().includes(a); });
            });
        });
    }
    if (filters.scientists.length) {
        results = results.filter(function(item) {
            return filters.scientists.some(function(s) {
                return (item.scientists || []).some(function(ss) { return ss.toLowerCase().includes(s); });
            });
        });
    }
    if (filters.text) {
        var q = filters.text;
        results = results.filter(function(item) {
            return (item.title || '').toLowerCase().includes(q) ||
                   (item.oneliner || '').toLowerCase().includes(q) ||
                   (item.description || '').toLowerCase().includes(q) ||
                   (item.authors || []).some(function(a) { return a.toLowerCase().includes(q); });
        });
    }

    renderResults(results.slice(0, 20));
}

function showTagSuggestions(query) {
    var container = document.getElementById('search-results');
    var matches = Object.entries(tagsLoc)
        .filter(function(entry) {
            var id = entry[0], data = entry[1];
            var name = (data.name || '').toLowerCase();
            return !query || id.includes(query) || name.includes(query);
        })
        .slice(0, 15);

    if (!matches.length) {
        container.innerHTML = '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.tagNotFound + '</p>';
        return;
    }

    container.innerHTML = '<div style="padding:10px 0;color:var(--soft);font-size:12px">' + UI.selectTag + '</div>' +
        matches.map(function(entry) {
            var id = entry[0], data = entry[1];
            return '<div class="suggestion-item" onclick="selectTag(\'' + id + '\')" style="cursor:pointer;padding:8px 12px;border-bottom:1px solid var(--border);font-size:14px">' +
                '<strong>#' + id + '</strong> <span style="color:var(--soft)">' + (data.name || '') + '</span>' +
                '<span style="float:right;color:var(--soft);font-size:11px">' + (data.description || '').substring(0, 80) + '</span>' +
                '</div>';
        }).join('');
}

function showScientistSuggestions(query) {
    var container = document.getElementById('search-results');
    var matches = Object.entries(scientistsData)
        .filter(function(entry) {
            var id = entry[0], data = entry[1];
            var name = (data.name || '').toLowerCase();
            return !query || id.toLowerCase().includes(query) || name.includes(query);
        })
        .slice(0, 15);

    if (!matches.length) {
        container.innerHTML = '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.scientistNotFound + '</p>';
        return;
    }

    container.innerHTML = '<div style="padding:10px 0;color:var(--soft);font-size:12px">' + UI.selectScientist + '</div>' +
        matches.map(function(entry) {
            var id = entry[0], data = entry[1];
            return '<div class="suggestion-item" onclick="selectScientist(\'' + id + '\')" style="cursor:pointer;padding:8px 12px;border-bottom:1px solid var(--border);font-size:14px">' +
                '<strong>!' + id + '</strong> <span style="color:var(--soft)">' + (data.name || '') + ' (' + (data.lifespan || '') + ')</span>' +
                '</div>';
        }).join('');
}

function showAuthorSuggestions(query) {
    var container = document.getElementById('search-results');
    // Граф авторов теперь грузится лениво — если @ нажали раньше, чем он доехал,
    // показываем «загрузка» и перерисовываем подсказки, как только данные придут.
    if (!Object.keys(authorsGraph).length) {
        container.innerHTML = '<p style="color:var(--soft);text-align:center;padding:40px">…</p>';
        ensureAuthorsGraph().then(function() { showAuthorSuggestions(query); });
        return;
    }
    var names = Object.keys(authorsGraph)
        .filter(function(name) { return !query || name.toLowerCase().includes(query); })
        .slice(0, 15);

    if (!names.length) {
        container.innerHTML = '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.authorNotFound + '</p>';
        return;
    }

    container.innerHTML = '<div style="padding:10px 0;color:var(--soft);font-size:12px">' + UI.selectAuthor + '</div>' +
        names.map(function(name) {
            var d = authorsGraph[name] || {};
            var count = d.article_count || (d.articles || []).length || 0;
            return '<div class="suggestion-item" onclick="selectAuthor(\'' + name.replace(/'/g, "\\'") + '\')" style="cursor:pointer;padding:8px 12px;border-bottom:1px solid var(--border);font-size:14px">' +
                '<strong>@' + name + '</strong> <span style="float:right;color:var(--soft);font-size:11px">' + count + ' ' + UI.articlesWord + '</span></div>';
        }).join('');
}

// Заменяет незавершённый последний токен (то что печаталось, чтобы вызвать
// дропдаун) на выбранное значение, сохраняя уже добавленные ранее фильтры —
// так можно накопить несколько #тегов подряд, а не терять предыдущий выбор.
function appendFilterToken(prefix, value) {
    var input = document.querySelector('.search-box');
    if (!input) return;
    var tokens = input.value.split(/\s+/).filter(Boolean);
    var token = prefix + value;
    var last = tokens[tokens.length - 1];
    if (last && last.charAt(0) === prefix) {
        tokens[tokens.length - 1] = token;
    } else if (tokens.indexOf(token) === -1) {
        tokens.push(token);
    }
    var seen = {}, unique = [];
    tokens.forEach(function(t) { if (!seen[t]) { seen[t] = true; unique.push(t); } });
    input.value = unique.join(' ') + ' ';
    doFullSearch(input.value);
    input.focus();
}

function selectTag(tagId) { appendFilterToken('#', tagId); }
function selectScientist(scientistId) { appendFilterToken('!', scientistId); }
function selectAuthor(name) { appendFilterToken('@', name.replace(/\s+/g, '_')); }

window.selectTag = selectTag;
window.selectScientist = selectScientist;
window.selectAuthor = selectAuthor;

function renderActiveFilters(query) {
    var container = document.getElementById('active-filters');
    if (!container) return;
    if (!query || !query.trim()) { container.innerHTML = ''; return; }
    var filters = parseSearchQuery(query);
    var chips = [];
    filters.tags.forEach(function(t) {
        chips.push({ type: 'tag', prefix: '#', value: t, label: '#' + ((tagsLoc[t] && tagsLoc[t].name) || t) });
    });
    filters.authors.forEach(function(a) {
        chips.push({ type: 'author', prefix: '@', value: a, label: '@' + a });
    });
    filters.scientists.forEach(function(s) {
        chips.push({ type: 'scientist', prefix: '!', value: s, label: '!' + ((scientistsData[s] && scientistsData[s].name) || s) });
    });
    if (!chips.length) { container.innerHTML = ''; return; }
    container.innerHTML = chips.map(function(c) {
        var escaped = c.value.replace(/'/g, "\\'");
        return '<span class="filter-' + c.type + '">' + c.label +
            ' <span class="remove" onclick="removeFilter(\'' + c.prefix + '\',\'' + escaped + '\')">×</span></span>';
    }).join('');
}

function removeFilter(prefix, value) {
    var input = document.querySelector('.search-box');
    if (!input) return;
    var tokens = input.value.split(/\s+/).filter(Boolean).filter(function(t) {
        if (t.charAt(0) !== prefix) return true;
        var v = t.slice(1).toLowerCase();
        if (prefix === '@') v = v.replace(/_/g, ' ');
        return v !== value;
    });
    input.value = tokens.join(' ') + (tokens.length ? ' ' : '');
    if (input.value.trim()) { doFullSearch(input.value); } else { showLatest(); renderActiveFilters(''); }
}
window.removeFilter = removeFilter;

function clearSearch() {
    var input = document.querySelector('.search-box');
    if (input) input.value = '';
    renderActiveFilters('');
    showLatest();
    if (input) input.focus();
}
window.clearSearch = clearSearch;

function filterCloudItems(containerId, query) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var q = query.trim().toLowerCase();
    var group = null, groupHasVisible = false;
    Array.prototype.forEach.call(container.children, function(el) {
        if (el.classList.contains('cloud-group-label')) {
            if (group) group.style.display = groupHasVisible ? '' : 'none';
            group = el; groupHasVisible = false;
            return;
        }
        if (!el.matches('a')) return;
        var visible = !q || el.textContent.toLowerCase().includes(q);
        el.style.display = visible ? '' : 'none';
        if (visible) groupHasVisible = true;
    });
    if (group) group.style.display = groupHasVisible ? '' : 'none';
}

// Индексная страница авторов рендерит на сервере только ОДНУ букву-по-умолчанию (список из
// тысяч авторов сразу целиком слишком длинный) — определяем это по отсутствию активной буквы
// в алфавитной навигации. На таких страницах поиск не может просто скрывать/показывать DOM-строки
// (там только одна буква) — вместо этого строит результаты из authorsGraph (уже загружен целиком
// для тултипов) и подменяет содержимое контейнера, а при очистке строки возвращает исходный вид.
var _authorsDefaultHTML = null;
function isAuthorsIndexPage() {
    var nav = document.getElementById('alphabet-nav');
    return !!nav && !nav.querySelector('.alpha-link.active');
}

function authorTagsFor(name) {
    var seen = {}, tags = [];
    searchIndex.forEach(function(item) {
        if ((item.authors || []).indexOf(name) === -1) return;
        (item.tags || []).forEach(function(t) { if (!seen[t]) { seen[t] = 1; tags.push(t); } });
    });
    return tags.slice(0, 6);
}

function authorRowHTML(name, data) {
    var slug = authorSlug(name);
    var count = data ? (data.article_count || (data.articles || []).length || 0) : 0;
    var tagsHtml = authorTagsFor(name).map(function(t) {
        return '<span onclick="event.stopPropagation();window.location=\'/lang/' + lang + '/tags/' + t + '.html\'" class="text-tag" data-tag="' + t + '">' +
            ((tagsLoc[t] && tagsLoc[t].name) || t) + '</span>';
    }).join(' ');
    return '<a href="/lang/' + lang + '/authors/' + slug + '.html" class="author-row" data-author="' + name + '">' +
        '<span class="author-name">' + name + '</span>' +
        '<span class="author-tags">' + tagsHtml + '</span>' +
        '<span class="author-count">' + count + ' ' + UI.articlesWord + '</span></a>';
}

function filterAuthors(query) {
    var container = document.getElementById('author-cloud');
    if (!container) return;
    var q = query.trim().toLowerCase();

    if (isAuthorsIndexPage()) {
        if (_authorsDefaultHTML === null) _authorsDefaultHTML = container.innerHTML;
        if (!q) { container.innerHTML = _authorsDefaultHTML; return; }
        if (!Object.keys(authorsGraph).length) {   // граф ленивый — дождаться и повторить
            ensureAuthorsGraph().then(function() { filterAuthors(query); });
            return;
        }
        var names = Object.keys(authorsGraph)
            .filter(function(name) { return name.toLowerCase().includes(q); })
            .sort(function(a, b) { return a.localeCompare(b); });
        container.innerHTML = names.length
            ? names.map(function(n) { return authorRowHTML(n, authorsGraph[n]); }).join('')
            : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>';
        return;
    }

    container.querySelectorAll('.author-row').forEach(function(el) {
        var text = el.textContent.toLowerCase();
        var show = !q || text.includes(q);
        el.style.display = show ? '' : 'none';
    });
    container.querySelectorAll('.letter-section').forEach(function(section) {
        var visible = section.querySelectorAll('.author-row[style*="display: none"]').length === 0
            ? section.querySelector('.author-row') !== null
            : Array.from(section.querySelectorAll('.author-row')).some(function(r) { return r.style.display !== 'none'; });
        section.style.display = visible ? '' : 'none';
    });
}
function filterScientists(query) { filterCloudItems('scientist-cloud', query); }
window.filterAuthors = filterAuthors;
window.filterScientists = filterScientists;

function authorSlug(name) {
    return name.replace(/ /g, '_').replace(/\./g, '');
}

// Появление на скролле. Класс вешается JS — без JS контент виден сразу.
var _revealObs = ('IntersectionObserver' in window) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); _revealObs.unobserve(e.target); } });
}, { rootMargin: '0px 0px -8% 0px' }) : null;
function initReveal() {
    if (!_revealObs) return;
    document.querySelectorAll('.article-card, .article-main section, .ai-cover, .formula, .key-numbers').forEach(function (el) {
        if (el.dataset.rev) return; el.dataset.rev = '1'; el.classList.add('reveal');
        _revealObs.observe(el);
    });
}
window.initReveal = initReveal;
document.addEventListener('DOMContentLoaded', initReveal);

function cardHTML(item) {
    var base = '/lang/' + defaultLang + '/archive/' + item.date + '/' + item.id + '/';
    var isMini = (currentVersion === 'mini' && item.threads);
    // В мини-режиме ссылка карточки должна вести на mini.html, иначе клик «сбрасывает»
    // выбор на popular (item.url всегда указывает на index.html — версия mini своего URL в индексе не имеет).
    var url = isMini ? (base + 'mini.html') : (item.url || (base + 'index.html'));
    // В списках — полная аннотация (адаптация авторского arXiv-abstract) БЕЗ обрезки на дисплее —
    // нужный размер уже задан в промпте генерации (data/prompts/adapt-abstract.txt: 350/550/900
    // символов на popular/simple/advanced), здесь всегда показываем как есть, целиком.
    // Мини — свой threads-текст, короче по своей природе, но и он не режется.
    var bodyText = isMini ? item.threads : (item.abstract || item.description || item.oneliner || '');
    var cat = (item.categories || [])[0] || '';
    var catName = (window.ARXIV_CAT_NAMES && ARXIV_CAT_NAMES[cat]) || cat;
    var catDesc = (window.ARXIV_CAT_DESC && ARXIV_CAT_DESC[cat]) || '';
    // Авторы: своя строка (переносится на 1-2 строки по ширине карточки), до 20 — с "+N" на остаток
    var au = item.authors || [];
    var authorsHtml = au.slice(0, 20).map(function(a) {
        return '<a href="/lang/' + lang + '/authors/' + authorSlug(a) + '.html" data-author="' + a + '">' + a + '</a>';
    }).join('<span class="sep">·</span>') + (au.length > 20 ? ' <span class="au-more-lite">+' + (au.length - 20) + '</span>' : '');
    var tagsHtml = (item.tags || []).slice(0, 6).map(function(t) {
        return '<a href="/lang/' + lang + '/tags/' + encodeURIComponent(t) + '.html" data-tag="' + t + '">' + ((tagsLoc[t] && tagsLoc[t].name) || t.replace(/_/g, ' ')) + '</a>';
    }).join('<span class="sep">·</span>');
    // Реакции + избранное прямо в карточке (клики — через делегирование в likes.js; подсветка — на этапе сборки)
    var _likeId = item.id + '_' + lang + '_' + currentVersion;
    var _myR = (typeof myReaction === 'function' ? (myReaction(_likeId) || '') : '');
    var _favOn = (typeof isFavorite === 'function' && isFavorite(item.id));
    var cardActions =
        '<div class="card-actions" data-article-id="' + _likeId + '">' +
        '<button class="react-btn sm' + (_myR === 'like' ? ' active' : '') + '" data-react="like" title="Нравится">👍</button>' +
        '<button class="react-btn sm' + (_myR === 'dislike' ? ' active' : '') + '" data-react="dislike" title="Не нравится">👎</button>' +
        '<button class="react-btn sm' + (_myR === 'superlike' ? ' active' : '') + '" data-react="superlike" title="Супер">⭐</button>' +
        '<button class="fav-btn sm' + (_favOn ? ' active' : '') + '" data-fav="' + item.id + '" title="В избранное"><span class="fav-ic">' + (_favOn ? '★' : '☆') + '</span></button>' +
        '</div>';
    var img = base + 't_ai.jpg';
    var imgFb = base + 'ai.jpg';
    // item.image === false — решено уже при генерации (нет ai.jpg), не пытаемся грузить и не
    // резервируем место под картинку. undefined (старый индекс до пересборки) — считаем как есть.
    var hasImg = item.image !== false;
    // Мета-строка (раздел·дата·бейдж) — полноширинный «eyebrow» НАД картинкой: тогда плавающая
    // мини-картинка стартует под ним, вровень с заголовком (юзер-фидбек 2026-07-19: "мини картинку
    // выровнять по названию"). Раньше мета была первой строкой card-body — картинка обтекалась от
    // самого верха и её край торчал выше заголовка на высоту меты.
    var eyebrow = (catName || item.date || item.express) ?
        '<div class="card-eyebrow">' +
            (catName ? '<a class="card-cat" href="#" title="' + catDesc.replace(/"/g, '&quot;') + '" onclick="filterByCategory(\'' + cat + '\');return false;">' + catName + '</a>' : '') +
            (item.date ? '<span class="card-date">' + item.date + '</span>' : '') +
            (item.express ? '<span class="card-express-badge" title="' + UI.expressTip + '">' + UI.express + '</span>' : '') +
        '</div>' : '';
    return '<article class="article-card">' +
        eyebrow +
        (hasImg ? (
        '<a class="card-img-wrap" href="' + url + '">' +
            '<img src="' + img + '" data-fb="' + imgFb + '" loading="lazy" onerror="if(this.dataset.fb){this.src=this.dataset.fb;this.removeAttribute(\'data-fb\');}else{this.closest(\'.card-img-wrap\').style.display=\'none\';}" alt="">' +
        '</a>') : '') +
        '<div class="card-body">' +
            '<a class="card-title" href="' + url + '">' + item.title + '</a>' +
            (bodyText ? '<div class="card-desc' + (isMini ? ' card-mini' : '') + '">' + bodyText + '</div>' : '') +
            (authorsHtml ? '<div class="card-authors">' + authorsHtml + '</div>' : '') +
            '<div class="card-meta">' + (item.reading ? '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12.5" r="7.6"/><path d="M12 8.4V12.6L15 14.6"/></svg> ' + item.reading + ' ' + UI.min + '<span class="sep">·</span>' : '') + 'arXiv:' + item.id + '</div>' +
            (tagsHtml ? '<div class="card-tags">' + tagsHtml + '</div>' : '') +
            cardActions +
        '</div>' +
    '</article>';
}

function renderResults(items) {
    feed.active = false;
    var container = document.getElementById('search-results');
    if (!container) return;
    if (!items.length) {
        container.innerHTML = '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>';
        return;
    }
    container.innerHTML = items.map(cardHTML).join('');
    initAllTooltips();
    initReveal();
}

// Лента: сортировка по дате (новые сверху), группировка по дням, подгрузка на скролле.
var feed = { items: [], shown: 0, batch: 12, lastDay: null, active: false };

// На странице тега/закона/учёного/автора строка поиска не нужна, если у сущности вообще нет
// статей — искать в пустом списке незачем. На главной (нет page-контекста) не трогаем.
var isEntityPage = !!(pageContext.tag || pageContext.scientist || pageContext.author || pageContext.category);
function updateSearchRowVisibility() {
    if (!isEntityPage) return;
    var row = document.querySelector('.search-row'), hint = document.querySelector('.search-hint');
    var show = feed.items.length > 0;
    if (row) row.style.display = show ? '' : 'none';
    if (hint) hint.style.display = show ? '' : 'none';
    // Нет статей у сущности → не показываем ни заголовок «Похожие статьи», ни «ничего не найдено»
    // (юзер-фидбек 2026-07-22: пустой блок Related/Nada encontrado убрать).
    var results = document.getElementById('search-results');
    var title = results && results.previousElementSibling;
    if (title && title.classList && title.classList.contains('section-title')) title.style.display = show ? '' : 'none';
    if (!show && results) results.innerHTML = '';
}

function showLatest() {
    // Порядок ленты (юзер 2026-07-24): сначала ПОЛНЫЕ статьи, потом express; внутри — новые сверху.
    // Плюс верхние ~10 перемешиваем при каждой загрузке, чтобы лента не была одинаковой и скучной
    // («первые случайные, потом по дате»). Math.random здесь — обычный клиентский код, ок.
    var arr = applyPageContext(searchIndex.filter(function(item) { return item.version === effVersion(); }))
        .sort(function(a, b) {
            var ae = a.express ? 1 : 0, be = b.express ? 1 : 0;
            if (ae !== be) return ae - be;
            return b.date.localeCompare(a.date);
        });
    var topN = Math.min(10, arr.length);
    for (var i = topN - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    feed.items = arr;
    feed.shown = 0; feed.lastDay = null; feed.active = true;
    var c = document.getElementById('search-results');
    if (c) c.innerHTML = feed.items.length ? '' : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>';
    renderMoreFeed();
    updateSearchRowVisibility();
}
window.showLatest = showLatest;

// Вкладка «Избранное»: карточки из localStorage.favorites (клиент, без сервера).
function showFavorites() {
    var favs = [];
    try { favs = JSON.parse(localStorage.getItem('favorites') || '[]'); } catch (e) {}
    var favSet = {};
    favs.forEach(function(id) { favSet[id] = true; });
    feed.items = searchIndex.filter(function(item) { return item.version === effVersion() && favSet[item.id]; })
        .sort(function(a, b) { return b.date.localeCompare(a.date); });
    feed.shown = 0; feed.lastDay = null; feed.active = true;
    var T = { ru: 'Избранное', en: 'Favorites', zh: '收藏', fr: 'Favoris', ar: 'المفضلة' }[lang] || 'Favorites';
    var E = { ru: 'Пока пусто — добавляйте статьи кнопкой ★.', en: 'No saved articles yet — add with ★.', zh: '暂无收藏 — 点 ★ 添加。', fr: 'Aucun favori — ajoutez avec ★.', ar: 'لا مقالات محفوظة — أضف بـ ★.' }[lang] || 'No saved articles yet.';
    var c = document.getElementById('search-results');
    if (!c) return;
    c.innerHTML = '<div class="feed-day">★ ' + T + ' (' + feed.items.length + ')</div>' +
        (feed.items.length ? '' : '<p style="color:var(--soft);text-align:center;padding:40px">' + E + '</p>');
    if (feed.items.length) renderMoreFeed();
}
window.showFavorites = showFavorites;

function _defaultFeed() { if (window.__favoritesPage) showFavorites(); else showLatest(); }

function filterByCategory(cat) {
    var items = applyPageContext(searchIndex.filter(function(item) {
        return item.version === effVersion() && (item.categories || []).indexOf(cat) !== -1;
    })).sort(function(a, b) { return b.date.localeCompare(a.date); });
    var c = document.getElementById('search-results');
    if (!c) return;
    feed.active = false;
    var label = ARXIV_CAT_NAMES[cat] || cat;
    c.innerHTML = '<div class="feed-day" style="cursor:pointer" onclick="showLatest()">' +
        '← ' + label + ' (' + items.length + ')</div>' + items.map(cardHTML).join('');
    initAllTooltips(); initReveal();
}
window.filterByCategory = filterByCategory;

// ── Календарь-фильтр (main): год→месяц→день, клик по дню фильтрует ленту ──
var CAL_LABELS = {
    ru: { title: '📅 Календарь', all: 'Все даты', months: ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'] },
    en: { title: '📅 Calendar', all: 'All dates', months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'] },
    zh: { title: '📅 日历', all: '全部日期', months: ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'] },
    fr: { title: '📅 Calendrier', all: 'Toutes les dates', months: ['jan','fév','mar','avr','mai','juin','juil','août','sep','oct','nov','déc'] },
    ar: { title: '📅 التقويم', all: 'كل التواريخ', months: ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'] }
};

function filterByDate(prefix, label) {
    feed.items = applyPageContext(searchIndex.filter(function(item) {
        return item.version === effVersion() && (item.date || '').indexOf(prefix) === 0;
    })).sort(function(a, b) { return b.date.localeCompare(a.date); });
    feed.shown = 0; feed.lastDay = null; feed.active = true;
    var c = document.getElementById('search-results');
    if (!c) return;
    c.innerHTML = '<div class="feed-day" style="cursor:pointer" onclick="showLatest()">← ' + (label || prefix) + ' (' + feed.items.length + ')</div>' +
        (feed.items.length ? '' : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>');
    renderMoreFeed();
    var p = document.getElementById('calendar-panel'); if (p) p.classList.remove('open');
    window.scrollTo({ top: 0 });
}
window.filterByDate = filterByDate;

function initCalendar() {
    var panel = document.getElementById('calendar-panel');
    var btn = document.getElementById('calendar-btn');
    if (!panel || !btn) return;
    var L = CAL_LABELS[lang] || CAL_LABELS.en;
    btn.title = L.title;
    var tree = {};
    searchIndex.filter(function(i) { return i.version === effVersion() && i.date; }).forEach(function(i) {
        var y = i.date.slice(0, 4), m = i.date.slice(5, 7), d = i.date.slice(8, 10);
        (tree[y] = tree[y] || { c: 0, m: {} }).c++;
        (tree[y].m[m] = tree[y].m[m] || { c: 0, d: {} }).c++;
        tree[y].m[m].d[d] = (tree[y].m[m].d[d] || 0) + 1;
    });
    var html = '<div class="cal-all" data-all="1">' + L.all + '</div>';
    Object.keys(tree).sort().reverse().forEach(function(y) {
        html += '<div class="cal-year"><div class="cal-head cal-y">' + y + '<span class="cal-cnt">' + tree[y].c + '</span></div><div class="cal-sub" hidden>';
        Object.keys(tree[y].m).sort().reverse().forEach(function(m) {
            var nm = L.months[parseInt(m, 10) - 1];
            html += '<div class="cal-month"><div class="cal-head cal-m">' + nm + '<span class="cal-cnt">' + tree[y].m[m].c + '</span></div><div class="cal-sub cal-days" hidden>';
            Object.keys(tree[y].m[m].d).sort().reverse().forEach(function(d) {
                html += '<span class="cal-day" data-date="' + y + '-' + m + '-' + d + '">' + parseInt(d, 10) + '<sup>' + tree[y].m[m].d[d] + '</sup></span>';
            });
            html += '</div></div>';
        });
        html += '</div></div>';
    });
    panel.innerHTML = html;
    btn.onclick = function() { panel.classList.toggle('open'); };
    panel.onclick = function(e) {
        var t = e.target;
        if (t.classList && t.classList.contains('cal-all')) { showLatest(); panel.classList.remove('open'); return; }
        var day = t.closest ? t.closest('.cal-day') : null;
        if (day) { filterByDate(day.getAttribute('data-date'), day.getAttribute('data-date')); return; }
        var head = t.closest ? t.closest('.cal-head') : null;
        if (head) { var sub = head.nextElementSibling; if (sub) { sub.hidden = !sub.hidden; head.classList.toggle('open', !sub.hidden); } }
    };
    document.addEventListener('click', function(e) {
        if (panel.classList.contains('open') && !panel.contains(e.target) && e.target !== btn) {
            panel.classList.remove('open');
        }
    });
}
window.initCalendar = initCalendar;

// ── Фильтр по разделам arXiv (main): чекбокс-чипы, OR-фильтрация ленты ──
var selectedCats = {};
function initCategoryBar() {
    var bar = document.getElementById('category-bar');
    if (!bar) return;
    var counts = {};
    searchIndex.filter(function(i) { return i.version === effVersion(); }).forEach(function(i) {
        (i.categories || []).forEach(function(c) { counts[c] = (counts[c] || 0) + 1; });
    });
    var cats = Object.keys(counts).sort(function(a, b) { return counts[b] - counts[a]; });
    if (!cats.length) { bar.innerHTML = ''; return; }
    bar.innerHTML = cats.map(function(c) {
        var desc = (ARXIV_CAT_DESC[c] || '').replace(/"/g, '&quot;');
        return '<span class="cat-chip' + (selectedCats[c] ? ' active' : '') + '" data-cat="' + c + '" title="' + desc + '">' +
            (ARXIV_CAT_NAMES[c] || c) + '<span class="cat-chip-n">' + counts[c] + '</span>' +
            '<span class="cat-chip-add" title="' + (UI.addToFilter || '+') + '">+</span></span>';
    }).join('');
    function syncChipActive() {
        bar.querySelectorAll('.cat-chip').forEach(function(ch) {
            ch.classList.toggle('active', !!selectedCats[ch.getAttribute('data-cat')]);
        });
    }
    bar.onclick = function(e) {
        var addBtn = e.target.closest ? e.target.closest('.cat-chip-add') : null;
        var chip = e.target.closest ? e.target.closest('.cat-chip') : null;
        if (!chip) return;
        var c = chip.getAttribute('data-cat');
        if (addBtn) {
            // «+» справа — ДОБАВИТЬ/убрать раздел в текущем наборе (мультивыбор)
            if (selectedCats[c]) delete selectedCats[c]; else selectedCats[c] = 1;
        } else {
            // Обычный клик по разделу — ПЕРЕКЛЮЧИТЬ фильтр на него (замена набора).
            // Повторный клик по единственному активному — снять фильтр целиком.
            if (selectedCats[c] && Object.keys(selectedCats).length === 1) selectedCats = {};
            else { selectedCats = {}; selectedCats[c] = 1; }
        }
        syncChipActive();
        applyCategoryFilter();
    };
    // Сворачиваем в ~2 строки, показываем "ещё", если реально не влезло — не показываем
    // кнопку зря, когда список и так короткий (мало категорий на этой ленте).
    var moreBtn = document.getElementById('category-bar-more');
    if (!moreBtn) {
        moreBtn = document.createElement('button');
        moreBtn.type = 'button';
        moreBtn.id = 'category-bar-more';
        moreBtn.className = 'category-bar-more';
        bar.insertAdjacentElement('afterend', moreBtn);
    }
    bar.classList.add('collapsed');
    moreBtn.style.display = 'none';
    moreBtn.textContent = UI.moreWord + ' ▾';
    moreBtn.onclick = function() {
        var collapsed = bar.classList.toggle('collapsed');
        moreBtn.textContent = (collapsed ? UI.moreWord + ' ▾' : UI.showLess + ' ▴');
    };
    requestAnimationFrame(function() {
        if (bar.scrollHeight > bar.clientHeight + 2) moreBtn.style.display = 'inline-block';
    });
}
window.initCategoryBar = initCategoryBar;

function applyCategoryFilter() {
    var sel = Object.keys(selectedCats);
    if (!sel.length) { showLatest(); return; }
    feed.items = applyPageContext(searchIndex.filter(function(item) {
        return item.version === effVersion() && (item.categories || []).some(function(c) { return selectedCats[c]; });
    })).sort(function(a, b) { return b.date.localeCompare(a.date); });
    feed.shown = 0; feed.lastDay = null; feed.active = true;
    var c = document.getElementById('search-results');
    if (!c) return;
    var label = sel.map(function(x) { return ARXIV_CAT_NAMES[x] || x; }).join(' · ');
    c.innerHTML = '<div class="feed-day">' + label + ' (' + feed.items.length + ')</div>' +
        (feed.items.length ? '' : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>');
    renderMoreFeed();
}
window.applyCategoryFilter = applyCategoryFilter;

function renderMoreFeed() {
    var c = document.getElementById('search-results');
    if (!c || !feed.active) return;
    var slice = feed.items.slice(feed.shown, feed.shown + feed.batch);
    var html = '';
    slice.forEach(function(item) { html += cardHTML(item); });
    c.insertAdjacentHTML('beforeend', html);
    feed.shown += slice.length;
    initAllTooltips();
    initReveal();
}

window.addEventListener('scroll', function() {
    if (!feed.active || feed.shown >= feed.items.length) return;
    if (window.scrollY + window.innerHeight > document.body.scrollHeight - 500) renderMoreFeed();
});

var tooltipHideTimer = null;

function getOrCreateTooltip() {
    var tip = document.getElementById('entity-tooltip');
    if (tip) return tip;
    tip = document.createElement('div');
    tip.id = 'entity-tooltip';
    tip.className = 'tag-tooltip';
    document.body.appendChild(tip);
    tip.addEventListener('mouseenter', function() {
        if (tooltipHideTimer) { clearTimeout(tooltipHideTimer); tooltipHideTimer = null; }
    });
    tip.addEventListener('mouseleave', scheduleHideTooltip);
    return tip;
}

function scheduleHideTooltip() {
    if (tooltipHideTimer) clearTimeout(tooltipHideTimer);
    tooltipHideTimer = setTimeout(function() {
        var tip = document.getElementById('entity-tooltip');
        if (tip) tip.style.display = 'none';
    }, 300);
}

// Описание тега/закона под ТЕКУЩУЮ выбранную версию (popular/simple/advanced) — раньше тултипы
// всегда показывали advanced-уровень (тег) или popular (закон) независимо от переключателя.
function descByVersion(obj) {
    var v = effVersion();
    if (v === 'advanced') return obj.description || obj.description_simple || obj.description_popular || '';
    if (v === 'simple') return obj.description_simple || obj.description_popular || obj.description || '';
    return obj.description_popular || obj.description_simple || obj.description || '';
}

function initAllTooltips() {
    document.querySelectorAll('[data-tag], [data-scientist], [data-law], [data-author]').forEach(function(el) {
        if (el.dataset.tooltipInit) return;
        el.dataset.tooltipInit = '1';

        el.addEventListener('mouseenter', function(e) {
            if (tooltipHideTimer) { clearTimeout(tooltipHideTimer); tooltipHideTimer = null; }
            var tip = getOrCreateTooltip();

            var content = '';
            if (el.dataset.tag) {
                var t = tagsLoc[el.dataset.tag];
                content = t
                    ? '<strong>' + t.name + '</strong> &mdash; <span class="tip-desc">' + descByVersion(t) + '</span> <a href="/lang/' + lang + '/tags/' + encodeURIComponent(el.dataset.tag) + '.html">' + UI.more + '</a>'
                    : '<strong>' + (el.textContent || el.dataset.tag) + '</strong> <a href="/lang/' + lang + '/tags/' + encodeURIComponent(el.dataset.tag) + '.html">' + UI.more + '</a>';
            } else if (el.dataset.scientist) {
                var s = scientistsData[el.dataset.scientist];
                content = s
                    ? '<strong>' + s.name + '</strong> (' + s.lifespan + ') &mdash; <span class="tip-desc">' + (s.description || '').substring(0, 200) + '...</span> <a href="/lang/' + lang + '/scientists/' + authorSlug(el.dataset.scientist) + '.html">' + UI.more + '</a>'
                    : '<strong>' + el.dataset.scientist + '</strong> <a href="/lang/' + lang + '/scientists/' + authorSlug(el.dataset.scientist) + '.html">' + UI.profile + '</a>';
            } else if (el.dataset.law) {
                var lw = lawsData[el.dataset.law];
                content = lw
                    ? '<strong>' + lw.name + '</strong>' + (lw.type ? ' &middot; ' + lw.type : '') + ' &mdash; <span class="tip-desc">' + descByVersion(lw).substring(0, 200) + '...</span> <a href="/lang/' + lang + '/laws/' + encodeURIComponent(el.dataset.law) + '.html">' + UI.more + '</a>'
                    : '<strong>' + (el.textContent || el.dataset.law) + '</strong> <a href="/lang/' + lang + '/laws/' + encodeURIComponent(el.dataset.law) + '.html">' + UI.more + '</a>';
            } else if (el.dataset.author) {
                var a = authorsGraph[el.dataset.author];
                var count = a ? (a.article_count || (a.articles || []).length || 0) : 0;
                content = '<strong>' + el.dataset.author + '</strong> &mdash; <span class="tip-desc">' + count + ' ' + UI.articlesWord + '</span> <a href="/lang/' + lang + '/authors/' + authorSlug(el.dataset.author) + '.html">' + UI.profile + '</a>';
            }

            if (content) {
                tip.innerHTML = content;
                tip.style.display = 'block';
                var rect = el.getBoundingClientRect();
                tip.style.left = Math.min(rect.left, window.innerWidth - 330) + 'px';
                tip.style.top = (rect.bottom + 6) + 'px';
            }
        });

        el.addEventListener('mouseleave', scheduleHideTooltip);
    });
}

// ── Локализация статичных строк из серверного HTML ──────────────────────────
// Заголовок/бейджи/тултипы шапки (★ Избранное, реакции 👍👎⭐, значок «экспресс», значок
// «отшлифовано») генератор пишет захардкоженными по-русски (общий шаблон на все языки) —
// раньше это давало русский текст даже на ar/es-страницах. UI_STRINGS уже содержит переводы
// (использовались только для карточек ленты) — просто дописываем их и в статичную разметку.
function localizeStaticUI() {
    var fav = document.querySelector('a[href*="/favorites.html"]');
    if (fav) fav.title = UI.favTitle;

    var likeBtn = document.querySelector('.react-btn[data-react="like"]');
    if (likeBtn) likeBtn.title = UI.like;
    var dislikeBtn = document.querySelector('.react-btn[data-react="dislike"]');
    if (dislikeBtn) dislikeBtn.title = UI.dislike;
    var superBtn = document.querySelector('.react-btn[data-react="superlike"]');
    if (superBtn) superBtn.title = UI.superlike;

    var expressBadge = document.querySelector('.express-badge');
    if (expressBadge) { expressBadge.title = UI.expressTip; expressBadge.textContent = '⚡ ' + UI.express; }

    var refineBadge = document.querySelector('.refine-badge');
    if (refineBadge) refineBadge.title = UI.refineTip;
}
document.addEventListener('DOMContentLoaded', localizeStaticUI);

// ── Сворачивание меню в «…» на языках, где шапка не помещается в 680px ──────
// Юзер-фидбек 2026-07-17: на es/ar (более длинные названия пунктов) шапка переносится на
// 2 строки — контенту нужно ~728px, а .top-bar зажат в 680px. Решили не трогать общую
// ширину шапки, а спрятать часть меню за кнопкой «…» — main/theory/★ остаются на виду,
// tags/laws/scientists/authors/graph уходят в выпадашку. Сделано через JS (переносит уже
// существующие <a> внутрь новой обёртки), а не правкой всех 13 шаблонов — тот же приём,
// что и в localizeStaticUI выше: работает мгновенно на уже сгенерённых страницах.
function collapseNavOverflow() {
    var nav = document.querySelector('.nav-links');
    if (!nav || nav.dataset.navCollapsed) return;
    nav.dataset.navCollapsed = '1';
    var collapsiblePatterns = ['/tags/', '/laws/', '/scientists/', '/sections/', '/authors/', '/graph/', '/theory/'];
    var links = Array.prototype.slice.call(nav.querySelectorAll('a'));
    var toCollapse = links.filter(function(a) {
        var href = a.getAttribute('href') || '';
        return collapsiblePatterns.some(function(p) { return href.indexOf(p) !== -1; });
    });
    if (toCollapse.length < 2) return;  // нечего сворачивать — не создаём пустую кнопку

    var wrap = document.createElement('div');
    wrap.className = 'nav-more';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-more-btn';
    btn.textContent = '☰';
    btn.setAttribute('aria-label', 'Menu');
    var panel = document.createElement('div');
    panel.className = 'nav-more-panel';

    var hasActive = false;
    toCollapse.forEach(function(a) {
        if (a.classList.contains('active')) hasActive = true;
        panel.appendChild(a);  // appendChild ПЕРЕМЕЩАЕТ узел — из старого родителя убирается сам
    });
    if (hasActive) btn.classList.add('active');

    // About и Архив живут в футере, но в шапочном меню их не было — добавляем (юзер 2026-07-22).
    [['/lang/' + lang + '/about.html', 'about'], ['/lang/' + lang + '/archive/', 'dashboard']].forEach(function(e) {
        if (panel.querySelector('a[href="' + e[0] + '"]')) return;
        var a = document.createElement('a');
        a.href = e[0]; a.textContent = e[1];
        panel.appendChild(a);
    });

    // Переключатель экспресс-статей раньше жил чекбоксом внутри панели поиска и только на
    // главной. Юзер 2026-07-23: «экспресс надо уметь отключить как через меню» — кладём пунктом
    // в ☰, он есть на всех типах страниц. Текст берём из готовой локали UI.hideExpress,
    // состояние показываем чекбоксом-глифом, чтобы не заводить новых переводов.
    var exBtn = document.createElement('a');
    exBtn.href = '#';
    exBtn.className = 'nav-express-toggle';
    function paintExpress() {
        exBtn.textContent = (hideExpress ? '☑ ' : '☐ ') + (UI.hideExpress || 'Hide express');
        exBtn.classList.toggle('on', hideExpress);
    }
    paintExpress();
    exBtn.onclick = function(e) {
        e.preventDefault();
        hideExpress = !hideExpress;
        try { localStorage.setItem('b42_hide_express', hideExpress ? '1' : '0'); } catch (err) {}
        paintExpress();
        var cb = document.getElementById('express-filter-toggle');   // держим старый чекбокс в синхроне
        if (cb) cb.checked = hideExpress;
        var input = document.querySelector('.search-box');
        if (window.searchIndex && document.getElementById('search-results')) {
            if (input && input.value.trim()) doSearch(input.value); else _defaultFeed();
        }
    };
    panel.appendChild(exBtn);

    wrap.appendChild(btn);
    wrap.appendChild(panel);
    // Логотип = main: текстовый пункт «main» убираем. Гамбургер ☰ — вплотную к названию сайта
    // (юзер 2026-07-23: «сначала гамбургер, а поиск и календарь вправо»), то есть сразу за
    // логотипом в шапке, а не в начало .nav-links.
    // ВАЖНО: на главной логотип вложен в .logo-wrap внутри .brand-row — вставлять по
    // logo.parentNode нельзя, ☰ попадал внутрь .logo-wrap и ломал шапку на 3 ряда (баг
    // 2026-07-22). Поэтому поднимаемся от логотипа до прямого ребёнка шапки и встаём ПОСЛЕ него.
    var mainLink = nav.querySelector('a[href$="/index.html"]');
    if (mainLink) mainLink.remove();
    var host = document.querySelector('.brand-row') || document.querySelector('.top-bar');
    var logoEl = document.querySelector('.logo');
    var placed = false;
    if (host && logoEl) {
        var anchor = logoEl;
        while (anchor && anchor.parentNode !== host) anchor = anchor.parentNode;
        if (anchor) { host.insertBefore(wrap, anchor.nextSibling); placed = true; }
    }
    if (!placed) nav.insertBefore(wrap, nav.firstChild);

    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        wrap.classList.toggle('open');
    });
    document.addEventListener('click', function(e) {
        if (!wrap.contains(e.target)) wrap.classList.remove('open');
    });
}
document.addEventListener('DOMContentLoaded', collapseNavOverflow);

// Настройки мини-графа (типы узлов/связей/глубина) свёрнуты в подменю за кнопкой-шестерёнкой
// (юзер 2026-07-24: «убрать в подменю, места много занимает»). Клик раскрывает .mini-graph-filters.
document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('.mg-config-toggle') : null;
    if (!t) return;
    var panel = t.nextElementSibling;
    if (panel && panel.classList.contains('mini-graph-filters')) {
        panel.hidden = !panel.hidden;
        t.classList.toggle('open', !panel.hidden);
    }
});

// Шапка .top-bar сама sticky (top:0). Закреплённая строка языков должна вставать ПОД ней, а не
// налезать (юзер 2026-07-23: «языки должны встать под верхнее меню, оно тоже морозится»). Высота
// шапки плавает (десктоп — одна строка, мобилка переносит), поэтому меряем вживую и кладём в
// --stick-top, к которому привязан top у .langs / .langs-row. Пересчитываем на ресайз.
(function () {
    function syncStickTop() {
        var tb = document.querySelector('.top-bar');
        var h = tb ? Math.round(tb.getBoundingClientRect().height) : 0;
        document.documentElement.style.setProperty('--stick-top', h + 'px');
    }
    document.addEventListener('DOMContentLoaded', function () {
        syncStickTop();
        // ☰-сворачивание меняет высоту шапки — пересчитать после него и после подхвата шрифтов
        setTimeout(syncStickTop, 60);
    });
    window.addEventListener('resize', syncStickTop);
    window.addEventListener('load', syncStickTop);
})();

// ── Поиск на главной — свёрнут в 🔍-кнопку рядом с 📅 (тот же паттерн выпадашки) ──────────
// Юзер-фидбек 2026-07-17: поле+подсказка+фильтр экспресс-статей были 2 постоянно открытые
// строки. Кнопка/панель уже отрендерены сервером (templates/index.html) — тут только клик-
// логика, независимая от загрузки searchIndex (в отличие от initCalendar/initCategoryBar).
function initSearchToggle() {
    var btn = document.getElementById('search-toggle-btn');
    var panel = document.getElementById('search-panel');
    if (!btn || !panel) return;
    btn.onclick = function() {
        var open = panel.classList.toggle('open');
        if (open) { var input = panel.querySelector('.search-box'); if (input) input.focus(); }
    };
    document.addEventListener('click', function(e) {
        if (panel.classList.contains('open') && !panel.contains(e.target) && e.target !== btn) {
            panel.classList.remove('open');
        }
    });
}
document.addEventListener('DOMContentLoaded', initSearchToggle);

// Кнопка календаря рендерится сервером, но обработчик ей вешал только initCalendar(), который
// ждёт загрузки и разбора индекса (несколько МБ). До этого момента клик по кнопке не делал
// ровно ничего — юзер 2026-07-23: «календарь не отвечает или долго». Вешаем раскрытие сразу
// на DOMContentLoaded: панель открывается мгновенно и показывает «…», а initCalendar потом
// подменяет содержимое и обработчик, сохраняя уже открытое состояние.
document.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('calendar-btn'), panel = document.getElementById('calendar-panel');
    if (!btn || !panel || btn.onclick) return;
    panel.innerHTML = '<div class="cal-all" style="text-align:center;color:var(--soft)">…</div>';
    btn.onclick = function() { panel.classList.toggle('open'); };
});

// ── Бегунок сложности (заменил кнопки-вкладки) ──────────────────────────────
// Всегда развёрнут целиком в шапке (без попапа). Один обработчик для ВСЕХ типов страниц.
// Точки внутри — либо <button data-version> (JS-переключение: главная/ленты/теги/законы/
// учёные), либо <a href data-version> (обычная навигация на странице статьи — работает
// без JS вообще). На тег/закон-страницах тот же клик ещё переключает видимые блоки
// .tag-ver — раньше это был отдельный дублированный инлайн-скрипт в каждом шаблоне.
document.addEventListener('DOMContentLoaded', function() {
    var wrap = document.getElementById('version-toggle');
    if (!wrap) return;
    var track = wrap.querySelector('.vs-track');
    var fill = wrap.querySelector('.vs-fill');
    var thumb = wrap.querySelector('.vs-thumb');
    var currentLabelEl = wrap.querySelector('.vs-current');
    var dots = Array.prototype.slice.call(wrap.querySelectorAll('.vs-dot'));
    if (!dots.length) return;
    var isLinkMode = dots[0].tagName === 'A';
    // RTL: .vs-dot позиции уже зеркалятся в CSS (html[dir=rtl] .vs-dot:nth-child(N)), .vs-fill растёт
    // от right вместо left (CSS). Бегунок же двигается через inline style.left из JS — простое зеркало
    // числа (100-pct) даёт тот же эффект без необходимости менять anchor/transform под right.
    var isRTL = document.documentElement.getAttribute('dir') === 'rtl';

    function paint(idx) {
        var pct = dots.length > 1 ? (idx / (dots.length - 1) * 100) : 0;
        if (fill) fill.style.width = pct + '%';
        if (thumb) thumb.style.left = (isRTL ? 100 - pct : pct) + '%';
        dots.forEach(function(d, i) { d.classList.toggle('active', i === idx); });
        if (currentLabelEl) currentLabelEl.textContent = dots[idx].dataset.label;
    }

    var tagVerBlocks = document.querySelectorAll('.tag-ver');
    function showTagVer(v) {
        if (!tagVerBlocks.length) return;
        tagVerBlocks.forEach(function(el) { el.style.display = el.dataset.ver === v ? '' : 'none'; });
    }

    function setActive(v, fromUser) {
        var idx = -1;
        dots.forEach(function(d, i) { if (d.dataset.version === v) idx = i; });
        if (idx === -1) return;
        paint(idx);
        showTagVer(v);
        if (!isLinkMode && fromUser) {
            currentVersion = v;
            try { localStorage.setItem('b42_version', currentVersion); } catch (e) {}
            var input = document.querySelector('.search-box');
            if (input && input.value.trim()) { doSearch(input.value); } else { _defaultFeed(); }
        }
    }

    if (isLinkMode) {
        // Ссылки — переход нативный (работает без JS). Красим начальное состояние И запоминаем
        // тир в localStorage (юзер-фидбек 2026-07-17: "тип... должны быть прям чётко везде") —
        // раньше страница статьи вообще не трогала b42_version, поэтому переход со статьи (в
        // любом тире) на тег/закон/учёного откатывал тир на тот, что был выставлен последним на
        // JS-странице (или дефолтный popular), а не на тот, что юзер только что читал.
        var activeIdx = 0;
        dots.forEach(function(d, i) { if (d.classList.contains('active')) activeIdx = i; });
        paint(activeIdx);
        var activeVersion = dots[activeIdx].dataset.version;
        showTagVer(activeVersion);
        currentVersion = activeVersion;
        try { localStorage.setItem('b42_version', currentVersion); } catch (e) {}
    } else {
        dots.forEach(function(d) {
            d.addEventListener('click', function() { setActive(d.dataset.version, true); });
        });
        setActive(currentVersion, false);

        wrap.addEventListener('keydown', function(e) {
            var idx = 0;
            dots.forEach(function(d, i) { if (d.classList.contains('active')) idx = i; });
            if (e.key === 'ArrowRight' && idx < dots.length - 1) setActive(dots[idx + 1].dataset.version, true);
            if (e.key === 'ArrowLeft' && idx > 0) setActive(dots[idx - 1].dataset.version, true);
        });

        // Драг бегунка — тянем к ближайшей точке (мышь и тач).
        var dragging = false;
        function pctFromEvent(e) {
            var rect = track.getBoundingClientRect();
            var x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
            return Math.max(0, Math.min(1, x / rect.width));
        }
        function nearestIdx(pct) { return Math.round((isRTL ? 1 - pct : pct) * (dots.length - 1)); }
        function onMove(e) { if (dragging) setActive(dots[nearestIdx(pctFromEvent(e))].dataset.version, true); }
        function onDown(e) { dragging = true; onMove(e); if (e.cancelable) e.preventDefault(); }
        function onUp() { dragging = false; }
        if (thumb) { thumb.addEventListener('mousedown', onDown); thumb.addEventListener('touchstart', onDown, { passive: true }); }
        if (track) { track.addEventListener('mousedown', onDown); track.addEventListener('touchstart', onDown, { passive: true }); }
        document.addEventListener('mousemove', onMove);
        document.addEventListener('touchmove', onMove, { passive: true });
        document.addEventListener('mouseup', onUp);
        document.addEventListener('touchend', onUp);
    }
});

// Дебаунс ввода в поиске. В шаблонах стоит oninput="doSearch(this.value)", то есть полный скан
// индекса запускался на каждое нажатие клавиши — при ~60k записей ввод заметно залипал
// (юзер 2026-07-23: «поиск когда нажимаю очень долго ждёт»). Оборачиваем только глобальный
// биндинг: внутренние вызовы doSearch(...) остаются мгновенными.
(function() {
    var real = window.doSearch;
    if (typeof real !== 'function') return;
    var timer = null;
    window.doSearch = function(q) {
        clearTimeout(timer);
        timer = setTimeout(function() { real(q); }, 160);
    };
})();
