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
// «Мини» — это отдельная страница статьи (mini.html), а не режим ленты. Раньше он был режимом
// показа и молча превращался в popular, если у статьи не было короткого текста: читатель нажимал
// и не видел никакой разницы (2026-07-28). В лентах уровень всегда один из трёх.
if (currentVersion === 'mini') currentVersion = 'popular';
// Эффективная версия для выборки статей: мини берёт popular-статьи.
function effVersion() { return currentVersion === 'mini' ? 'popular' : currentVersion; }

/* Экранирование для подстановки в атрибут. Нужно там, где в разметку карточки едет
   переводимая строка: кавычка внутри title="…" рвёт тег, и дальше страница разъезжается.

   Появилась после аварии 13 августа: в карточку добавили title у ссылок без справочной
   карточки, вызвали esc(), а самой функции в этом файле не было. Итог — ReferenceError
   на первой же карточке, лента не строилась НИ НА ОДНОМ языке, главная показывала
   «0 articles / ничего не найдено». Ошибка молчаливая: страница отдавалась с кодом 200,
   в консоли лежало одно сообщение, и заметил её владелец, а не мы. */
function esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
// Наружу — чтобы scroll.js мог сверить, про тот ли уровень чтения общий индекс, прежде чем
// брать его вместо своего: иначе на advanced-странице подписи приехали бы из popular.
window.effVersion = effVersion;
window.__favoritesPage = /\/favorites(\.html)?([?#]|$)/.test(location.pathname);

// Тёмная тема: применяем сохранённый выбор как можно раньше, чтобы не мигало светлым.
(function initTheme() {
    try {
        if (localStorage.getItem('b42_theme') === 'dark')
            document.documentElement.setAttribute('data-theme', 'dark');
    } catch (e) {}
})();
/* Знак из нашего набора (js/icons.js). Запасной вариант нужен на случай, если
   набор не приехал: кнопка не должна остаться пустой и безымянной. */
function b42ic(name, size, fallback) {
    return (window.B42Icons && B42Icons[name]) ? B42Icons[name](size) : (fallback || '');
}
function toggleTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (dark) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', 'dark');
    try { localStorage.setItem('b42_theme', dark ? 'light' : 'dark'); } catch (e) {}
    var b = document.getElementById('theme-toggle');
    // кнопка показывает, куда переключит: в тёмной теме — солнце, в светлой — луна
    if (b) b.innerHTML = dark ? b42ic('moon', 18, '☾') : b42ic('sun', 18, '☀');
}
window.toggleTheme = toggleTheme;
document.addEventListener('DOMContentLoaded', function() {
    var host = document.querySelector('.header-right') || document.getElementById('langs-bar');
    if (host && !document.getElementById('theme-toggle')) {
        var b = document.createElement('button');
        b.id = 'theme-toggle'; b.type = 'button'; b.className = 'theme-toggle';
        b.setAttribute('aria-label', 'Theme');
        b.innerHTML = document.documentElement.getAttribute('data-theme') === 'dark'
            ? b42ic('sun', 18, '☀') : b42ic('moon', 18, '☾');
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
          hideExpress: 'Скрыть экспресс-статьи', onlyAdvice: 'Только с советами автору', showLess: 'Свернуть',
          favTitle: 'Избранное', like: 'Нравится', dislike: 'Не нравится', superlike: 'Супер!',
          refineTip: 'Отшлифовано редактором',
          noCard: 'Карточки пока нет — покажем статьи, где о нём говорится',
          kmTip: 'Разобрано машиной знаний: в конце продвинутой версии есть раздел для автора работы — куда двигаться дальше и что лежит рядом в нашем архиве. Нажмите, чтобы открыть.' },
    en: { tagNotFound: 'Tag not found', selectTag: 'Select a tag:', scientistNotFound: 'Scientist not found',
          selectScientist: 'Select a scientist:', authorNotFound: 'Author not found', selectAuthor: 'Select an author:',
          articlesWord: 'articles', noResults: 'Nothing found', more: 'More →', profile: 'Profile →', moreWord: 'more', min: 'min',
          express: 'express', expressTip: 'Express: a quick take from the author\'s abstract only. Full articles are written from the whole paper — deeper and more detailed.',
          hideExpress: 'Hide express articles', onlyAdvice: 'Only with advice to authors', showLess: 'Collapse',
          favTitle: 'Favorites', like: 'Like', dislike: 'Dislike', superlike: 'Super!',
          refineTip: 'Polished by an editor',
          noCard: 'No profile yet — we will show the articles that mention it',
          kmTip: 'Read by the knowledge machine: the advanced version ends with a section for the paper\'s author — where the work could go next and what lies nearby in our archive. Click to open.' },
    es: { tagNotFound: 'Etiqueta no encontrada', selectTag: 'Elige una etiqueta:', scientistNotFound: 'Científico no encontrado',
          selectScientist: 'Elige un científico:', authorNotFound: 'Autor no encontrado', selectAuthor: 'Elige un autor:',
          articlesWord: 'artículos', noResults: 'Nada encontrado', more: 'Más →', profile: 'Perfil →', moreWord: 'más', min: 'min',
          express: 'exprés', expressTip: 'Exprés: un resumen rápido solo del abstract del autor. Los artículos completos se escriben a partir de todo el texto.',
          hideExpress: 'Ocultar artículos exprés', onlyAdvice: 'Solo con consejos al autor', showLess: 'Contraer',
          favTitle: 'Favoritos', like: 'Me gusta', dislike: 'No me gusta', superlike: '¡Genial!',
          refineTip: 'Pulido por un editor',
          noCard: 'Aún sin ficha: mostraremos los artículos donde se menciona',
          kmTip: 'Analizado por la máquina del conocimiento: la versión avanzada termina con una sección para el autor del trabajo — hacia dónde avanzar y qué hay cerca en nuestro archivo. Pulse para abrir.' },
    zh: { tagNotFound: '未找到标签', selectTag: '选择标签：', scientistNotFound: '未找到科学家',
          selectScientist: '选择科学家：', authorNotFound: '未找到作者', selectAuthor: '选择作者：',
          articlesWord: '篇文章', noResults: '未找到结果', more: '详情 →', profile: '主页 →', moreWord: '更多', min: '分钟',
          express: '速览', expressTip: '速览版：基于作者摘要，未解析全文', hideExpress: '隐藏速览文章', onlyAdvice: '仅含给作者的建议', showLess: '收起',
          favTitle: '收藏', like: '喜欢', dislike: '不喜欢', superlike: '太赞了！',
          refineTip: '编辑润色',
          noCard: '暂无词条——将显示提到它的文章',
          kmTip: '已由知识机器解读：进阶版末尾有写给论文作者的一节——可以往哪里走，档案库里附近有什么。点击打开。' },
    fr: { tagNotFound: 'Tag introuvable', selectTag: 'Choisir un tag :', scientistNotFound: 'Scientifique introuvable',
          selectScientist: 'Choisir un scientifique :', authorNotFound: 'Auteur introuvable', selectAuthor: 'Choisir un auteur :',
          articlesWord: 'articles', noResults: 'Aucun résultat', more: 'En savoir plus →', profile: 'Profil →', moreWord: 'autres', min: 'min',
          express: 'express', expressTip: 'Version express : basée sur le résumé de l\'auteur, pas le texte complet',
          hideExpress: 'Masquer les articles express', onlyAdvice: "Uniquement avec conseils à l'auteur", showLess: 'Réduire',
          favTitle: 'Favoris', like: 'J\'aime', dislike: 'Je n\'aime pas', superlike: 'Génial !',
          refineTip: 'Peaufiné par un éditeur',
          noCard: 'Pas encore de fiche : nous montrerons les articles qui en parlent',
          kmTip: 'Lu par la machine du savoir : la version avancée se termine par une section destinée à l\'auteur — vers où avancer et ce qui se trouve à côté dans notre archive. Cliquez pour ouvrir.' },
    ar: { tagNotFound: 'الوسم غير موجود', selectTag: 'اختر وسمًا:', scientistNotFound: 'العالم غير موجود',
          selectScientist: 'اختر عالمًا:', authorNotFound: 'المؤلف غير موجود', selectAuthor: 'اختر مؤلفًا:',
          articlesWord: 'مقالات', noResults: 'لا نتائج', more: 'المزيد ←', profile: 'الملف ←', moreWord: 'آخرون', min: 'دقيقة',
          express: 'سريع', expressTip: 'سريع: ملخّص سريع من خلاصة المؤلف فقط. أما المقالات الكاملة فتُكتب من النص الكامل — أعمق وأكثر تفصيلاً.',
          hideExpress: 'إخفاء المقالات السريعة', onlyAdvice: 'فقط ما فيه نصائح للمؤلف', showLess: 'طي',
          favTitle: 'المفضلة', like: 'إعجاب', dislike: 'عدم إعجاب', superlike: 'رائع!',
          refineTip: 'تم صقله بواسطة محرر',
          noCard: 'لا توجد بطاقة بعد — سنعرض المقالات التي تذكره',
          kmTip: 'قرأته آلة المعرفة: تنتهي النسخة المتقدمة بقسم موجَّه إلى مؤلف العمل — إلى أين يمكن المضي وما الذي يقع قريبًا في أرشيفنا. اضغط للفتح.' }
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
    category: resultsEl ? (resultsEl.dataset.contextCategory || '') : '',  // страница раздела arXiv
    // Понятие волны 5. Без этой строки список на странице понятия наполнялся
    // ОБЩЕЙ лентой: search.js видел пустой #search-results, не понимал контекста
    // и рисовал туда свежие статьи — на «чёрной дыре» первой шла статья про
    // материалы-хамелеоны (поймано 27.08 при переводе списков на воркер).
    concept: resultsEl ? (resultsEl.dataset.contextConcept || '') : ''
};
pageContext.tag = pageContext.tags[0] || ''; // назад-совместимость: код, читающий одиночный tag (напр. filters.tags UI), видит первый

function applyPageContext(results) {
    if (pageContext.concept) {
        var _c = pageContext.concept;
        results = results.filter(function (item) {
            return (item.tags || []).indexOf(_c) !== -1
                || (item.laws || []).indexOf(_c) !== -1;
        });
    }
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
    if (onlyAdvice) {
        results = results.filter(function(item) { return item.advice; });
    }
    return results;
}

// Глобальный тумблер «скрыть экспресс-статьи» — персистится в localStorage, применяется через
// applyPageContext() (общий фильтр-чокпоинт для showLatest/filterByDate/applyCategoryFilter/doSearch).
var hideExpress = false;
try { hideExpress = localStorage.getItem('b42_hide_express') === '1'; } catch (e) {}

/* Второй тумблер: «только с советами автору». Владелец 14 августа — «я бы добавил такую
   же галочку для отображения страниц с рекомендациями, мне было бы так удобно их искать;
   оставь все сортировки работающими».

   Живёт рядом с экспрессом и по тем же правилам: признак берётся из индекса (поле advice),
   фильтр применяется в общем чекпоинте applyPageContext, сортировки не трогаются вовсе —
   они работают уже после фильтрации. */
var onlyAdvice = false;
try { onlyAdvice = localStorage.getItem('b42_only_advice') === '1'; } catch (e) {}

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
    var ab = document.getElementById('advice-filter-toggle');
    if (!ab) return;
    var alabel = document.getElementById('advice-filter-label');
    if (alabel) alabel.textContent = UI.onlyAdvice || 'advice';
    ab.checked = onlyAdvice;
    ab.onchange = function() {
        onlyAdvice = ab.checked;
        try { localStorage.setItem('b42_only_advice', onlyAdvice ? '1' : '0'); } catch (e) {}
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
                /* Страница может существовать не на всех языках: раздел понятий
                   и формул пока живёт на ru+en (владелец 27.08), остальным там
                   отдаётся редирект. Такая страница объявляет свои языки в
                   data-langs — переключатель показывает только их и не ведёт
                   человека туда, где текста нет. */
                var only = (document.body.dataset.langs || '').split(',').filter(Boolean);
                var list = only.length ? data.languages.filter(function (l) {
                    return only.indexOf(l) >= 0; }) : data.languages;
                bar.innerHTML = list.map(function(l) {
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

// Лёгкие справочники (tools/lite_refs.py): имя и описание для подсказки. Полные
// файлы весят 4.5 МБ ради 368 названий и нужны СТРАНИЦЕ тега, а не ленте.
/* Имена — то, без чего лента показывает cooper_pair вместо «куперовская пара».
   56 КБ на три справочника. Описания для подсказок лежат отдельно и приезжают
   по первому наведению, см. ensureTips ниже: 357 КБ, которые платит только тот,
   кто действительно навёл. */
var tagsPath = '/lang/' + lang + '/data/tags-names.json';
/* Реестр понятий волны 5: 1222 имени. Проверяется ПЕРВЫМ при рисовании плашек:
   понятие из него имеет страницу /concepts/ всегда — «карточки пока нет» больше
   не показывается тем, у кого карточка есть. */
var conceptsNames = {};
var _conceptsNamesP = fetch('/lang/' + lang + '/data/concepts-names.json')
    .then(function (r) { return r.ok ? r.json() : {}; })
    .then(function (m) { conceptsNames = m || {}; return conceptsNames; })
    .catch(function () { return {}; });
var scientistsPath = '/lang/' + lang + '/data/scientists-names.json';

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

/* Индекс статей нужен только там, где есть СПИСОК: лента главной и избранного, выдача
   на странице тега/закона/учёного/раздела/автора. На странице СТАТЬИ и на /analytics
   контейнера списка нет вовсе — а индекс качался и разбирался всё равно: на статье это
   6,3 МБ разбора вдобавок к тому, что тот же файл вторым заходом берёт scroll.js для
   «следующей статьи», на карте проекта — 19 МБ ради трёхмерной сцены, которая индексом
   не пользуется (замер живого сайта 2026-07-30).
   Тултипы и строка статистики от индекса не зависят — им нужны справочники, они грузятся
   отдельной волной, поэтому ниже вызываются в обеих ветках. */
var HAS_LIST = !!document.getElementById('search-results');
/* ИНДЕКС БОЛЬШЕ НЕ КАЧАЕТСЯ САМ. Здесь стояло «есть список — грузим индекс», и это
   было верно, пока список брать было неоткуда. Теперь лента приходит из облака
   постранично, страницы сущностей и автора рисуются своими модулями, а календарь,
   полоса разделов и фильтр глубины считаются по сводке /api/corpus (13 КБ).
   Индекс остаётся запасным путём и источником для дашборда /archive — его поднимает
   ensureSearchIndex по требованию. */
var _fullIndexPromise = null;

/* НАЧАЛЬНАЯ НАСТРОЙКА НИЧЕГО НЕ ЖДЁТ.
   Здесь стоял `_fullIndexPromise.then(...)`: лента, календарь, полоса разделов,
   подсказки и строка статистики заводились ПОСЛЕ загрузки индекса — то есть страница
   стояла мёртвой, пока не доедут 14.6 МБ. Загрузка была ещё и двухступенчатой: сначала
   latest на 150 КБ ради быстрой первой отрисовки, следом полный.

   Теперь лента приходит из облака пачками по двенадцать (~20 КБ), поэтому ни ступени,
   ни ожидания не нужно: рисуем сразу, а сводку для панелей ждём отдельно — каждая
   панель дорисуется, когда та придёт. */
// Запуск ОТЛОЖЕН на микрозадачу, и это не украшение. Блок стоит в файле раньше, чем
// объявляются словари подписей и часть функций; прежний код этого не замечал, потому
// что висел в `.then()` загрузки индекса и по факту выполнялся после всего файла.
// Убрав ожидание, я убрала и эту случайную отсрочку — страница падала на первой же
// подписи. Promise.resolve().then даёт ровно прежний порядок: после того, как файл
// дочитан, но до отрисовки.
Promise.resolve().then(function initListPage() {
    if (HAS_LIST) {
        var container = document.getElementById('search-results');
        if (container && !document.querySelector('.search-box')?.value) _defaultFeed();
        if (window.__favoritesPage) {
            ['calendar-btn', 'calendar-panel', 'category-bar'].forEach(function(id) {
                var e = document.getElementById(id); if (e) e.style.display = 'none';
            });
        } else {
            // Панелям нужны только числа — ждём сводку, а не архив. Если её нет,
            // строим по тому, что уже есть в памяти (после отката на индекс).
            ensureCorpus().then(function () {
                initCalendar();
                initCategoryBar();
                initExpressFilter();
            });
        }
    }
    initAllTooltips();
    renderSiteStats();
});

function catFetch(base, lang) {
    var url = (lang === 'en') ? base + '.json' : base + '-' + lang + '.json';
    return fetch(url)
        .then(function (r) { if (!r.ok) throw 0; return r.json(); })
        .catch(function () {
            // Перевода для этого языка ещё нет — берём английскую базу. Это осознанный
            // откат, и он виден: панель разделов будет по-английски, пока не переведут.
            if (url === base + '.json') return {};
            console.info('разделы arXiv: нет перевода для ' + lang + ', беру английские');
            return fetch(base + '.json').then(function (r) { return r.json(); }).catch(function () { return {}; });
        });
}

var OTHER_VERSIONS = ['popular', 'simple', 'advanced'].filter(function(v) { return v !== effVersion(); });

/* Тяжёлое — ПОСЛЕ первой ленты, а не вместе с ней.
   Замер живого сайта (2026-07-30): первый визит тянул 5,36 МБ, из них первому экрану
   нужно 317 КБ. Все девять запросов стартовали в одну миллисекунду и делили канал
   поровну, поэтому 39-килобайтный файл ленты ждал за компанию с двумя индексами чужих
   уровней (2,5 МБ, 46% веса страницы) и графом авторов (375 КБ по сети, но 10 МБ
   разбора на главном потоке телефона). На 4G это секунды до первой карточки.

   Индексы других уровней нужны только при переключении «просто/популярно/подробно»,
   граф авторов — только для @-подсказок и счётчика. Ждём простоя: первая лента к тому
   моменту нарисована, канал свободен. Если простоя не дождались (страница активна),
   выходим по таймеру — файлы всё равно понадобятся. */
function whenIdle(fn) {
    if (typeof requestIdleCallback === 'function') requestIdleCallback(fn, { timeout: 2500 });
    else setTimeout(fn, 1200);
}

/* Общий доступ к справочникам. Мини-граф и эксплорер живут на тех же страницах, что и
   search.js, и им нужны ровно эти же tags/laws/scientists. Без общего обещания они
   успевали попросить файлы ДО того, как search.js их дочитывал, — и разбирали те же
   4,6 МБ тегов и 1,8 МБ законов вторым комплектом на главном потоке телефона. */
/* Единая точка доступа к справочнику для всех, кто рисует графы. Правило одно: уже
   разобранный объект → общее обещание B42Refs → и только если ни того ни другого нет
   (страница без search.js) — свой запрос. Раньше эта функция была скопирована в
   mini-graph.js и knowledge-graph.js, а author-graph.js качал теги мимо неё вовсе —
   то есть класс «справочники вторым комплектом» был закрыт на два файла из трёх. */
window.B42Ref = function (name, url) {
    var have = window[name];
    if (have && typeof have === 'object' && Object.keys(have).length) {
        return Promise.resolve(have);
    }
    function own() {
        return fetch(url).then(function (r) { return r.json(); }).catch(function (e) {
            // Осознанный откат: без справочника граф рисуется, но без человеческих подписей.
            // Молчать нельзя — иначе назавтра никто не поймёт, почему на узлах сырые id.
            console.warn('справочник не загрузился: ' + url, e);
            return {};
        });
    }
    if (window.B42Refs && window.B42Refs.then) {
        return window.B42Refs.then(function (refs) {
            var got = (refs && refs[name]) || window[name];
            return (got && Object.keys(got).length) ? got : own();
        });
    }
    return own();
};

window.B42Refs = Promise.all(
    [].concat([
        fetch(tagsPath).then(function(r) { return r.json(); }).catch(function() {
            return fetch('/lang/' + defaultLang + '/data/tags-lite.json').then(function(r) { return r.json(); });
        }),
        fetch(scientistsPath).then(function(r) { return r.json(); }).catch(function() {
            return fetch('/lang/' + defaultLang + '/data/scientists-lite.json').then(function(r) { return r.json(); });
        }),
        fetch('/lang/' + lang + '/data/laws-names.json').then(function(r) { return r.json(); }).catch(function() { return {}; }),
        // Локализованный набор названий/описаний разделов, с откатом на английскую базу —
        // она же остаётся источником для lang=en и для категорий, перевода которых ещё нет.
        // Базовый файл — АНГЛИЙСКИЙ, отдельного -en не существует и не должно. Раньше его
        // всё равно просили на каждой английской загрузке: два гарантированных 404 и два
        // лишних round-trip перед отрисовкой панели разделов (замер 2026-07-30).
        catFetch('/data/arxiv-categories', lang),
        catFetch('/data/arxiv-category-descriptions', lang)
    ])
).then(function(rest) {
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
    window.B42RefsReady = true;

    renderSiteStats();
    // Первая лента уже отрисована с тегами как raw id (tagsLoc ещё не пришёл) — теперь, когда
    // справочники подгрузились, перерисовываем дефолтный фид начисто, чтобы подтянуть красивые
    // названия тегов. Если пользователь уже начал искать — его результаты не трогаем.
    var container = document.getElementById('search-results');
    if (container && !document.querySelector('.search-box')?.value) {
        _defaultFeed();
    }
    // Только теперь — тяжёлое. Граф авторов: 375 КБ по сети, но 10 МБ разбора на главном
    // потоке телефона; нужен для @-подсказок, тултипа автора и счётчика в статистике.
    // Индексы соседних уровней: 2,5 МБ, нужны при переключении «просто/популярно/подробно»
    // и для того, чтобы поиск находил статьи во всех трёх видах.
    // Обе вещи нужны только странице со списком: граф авторов — для @-подсказок и
    // счётчика в статистике, индексы соседних уровней — чтобы поиск находил статьи
    // во всех трёх видах. На статье и на карте проекта ни того, ни другого нет,
    // а разбор стоил 10,5 и 2,5 МБ. Обе функции остаются вызываемыми по требованию:
    // @-подсказки и фильтр авторов дёргают ensureAuthorsGraph сами.
    // ПРОГРЕВА БОЛЬШЕ НЕТ. Здесь стояло whenIdle(ensureAuthorsGraph, ensureOtherVersions) —
    // «в простое подтянем, чтобы поиск не ждал». Замер 25 августа: это 24.4 МБ графа
    // авторов и 29.7 МБ двух соседних уровней индекса, на КАЖДОЙ странице со списком,
    // включая читателя, который просто листает ленту и ничего не ищет. Страница понятия
    // весила 71 МБ, из них 69 — эти четыре файла.
    //
    // Ленивая загрузка, которую всегда вызывают сразу, — это обычная загрузка с лишним
    // кодом. Обе функции остались вызываемыми: поиск дёргает ensureOtherVersions сам
    // (doFullSearch), @-подсказки и фильтр авторов — ensureAuthorsGraph. Первый поиск
    // подождёт; платить за это всем читателям не нужно.
    return { tagsLoc: tagsLoc, lawsData: lawsData, scientistsData: scientistsData };
}).catch(function(e) {
    console.error('Background data load error:', e);
    return {};
});

/* Индексы соседних уровней — по требованию. Пока их нет, поиск ищет по текущему уровню:
   это меньше, чем обещано, поэтому переключатель уровня и поиск сами дёргают загрузку,
   а не ждут простоя. Один общий промис, сколько бы раз ни позвали. */
var _otherVersionsPromise = null;
function ensureOtherVersions() {
    if (_otherVersionsPromise) return _otherVersionsPromise;
    _otherVersionsPromise = Promise.all(OTHER_VERSIONS.map(fetchIndex)).then(function (otherIndexes) {
        var byVersion = {};
        byVersion[effVersion()] = window.__primaryIndex || searchIndex;
        OTHER_VERSIONS.forEach(function (v, i) { byVersion[v] = otherIndexes[i]; });
        searchIndex = (byVersion.popular || []).concat(byVersion.simple || []).concat(byVersion.advanced || []);
        window.searchIndex = searchIndex;
        return searchIndex;
    }).catch(function (e) {
        console.error('Other version indexes failed:', e);
        return searchIndex;
    });
    return _otherVersionsPromise;
}
window.ensureOtherVersions = ensureOtherVersions;

/* Полный индекс ПО ТРЕБОВАНИЮ — для страниц, которые считают по корпусу, но списка не
   показывают. Такая ровно одна: дашборд /archive — вся его сводка (статьи, тепловая карта,
   динамика, разделы, обложки, топы) выводится из индекса, а контейнера ленты у него нет.
   С момента, как индекс перестал грузиться всюду подряд (2026-07-31), дашборд получал
   пустой массив и рисовал нули — счётчик статей был пуст. Загрузка «по требованию» держит
   и экономию (статья и /analytics не зовут — значит не качают), и правду на дашборде.
   Один общий промис, сколько бы раз ни позвали; на странице со списком отдаёт тот же
   индекс, который уже грузится, вторым запросом не ходит. */
var _searchIndexPromise = null;
function ensureSearchIndex() {
    if (_searchIndexPromise) return _searchIndexPromise;
    _searchIndexPromise = (_fullIndexPromise || fetchIndex(effVersion())).then(function (primary) {
        searchIndex = primary;
        window.searchIndex = searchIndex;
        window.__primaryIndex = primary;
        return searchIndex;
    }).catch(function (e) {
        console.error('Index on demand failed:', e);
        return [];
    });
    return _searchIndexPromise;
}
window.ensureSearchIndex = ensureSearchIndex;

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
    ru: {articles:'статей', full:'полных', express:'экспресс', concepts:'понятий', formulas:'формул', sections:'разделов', scientists:'учёных', authors:'авторов', langs:'языка'},
    en: {articles:'articles', full:'full', express:'express', concepts:'concepts', formulas:'formulas', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages'},
    es: {articles:'artículos', full:'completos', express:'exprés', concepts:'conceptos', formulas:'fórmulas', sections:'secciones', scientists:'científicos', authors:'autores', langs:'idiomas'},
    ar: {articles:'مقالات', full:'كاملة', express:'سريعة', concepts:'مفاهيم', formulas:'صيغ', sections:'أقسام', scientists:'علماء', authors:'مؤلفين', langs:'لغات'},
    fr: {articles:'articles', full:'complets', express:'express', concepts:'concepts', formulas:'formules', sections:'sections', scientists:'scientifiques', authors:'auteurs', langs:'langues'}
};
function renderSiteStats() {
    var el = document.getElementById('site-stats');
    if (!el) return;
    var L = STATS_LABELS2[lang] || STATS_LABELS2.en;
    // Числа корпуса приходят из build-info.json (двести байт), а не считаются по данным.
    // Раньше статьи считались перебором индекса, авторы — перебором графа авторов: строка
    // под шапкой молчала, пока не доедут 39 МБ, и ради неё же они и качались.
    var B = window.__buildInfo || {};
    var uniq = {}, express = 0;
    searchIndex.forEach(function(a){ if (!uniq[a.id]) { uniq[a.id] = 1; if (a.express) express++; } });
    var nA = B.articles || Object.keys(uniq).length;
    var full = nA - (B.express || express);
    /* Раньше строка считала «законы» и «теги» по старым справочникам и врала:
       175 и 368 при живом реестре в 3231 понятие (владелец увидел 27.08 —
       снаружи такой терминологии больше нет). Теперь понятия и формулы из
       build-info, который пишет сборка. */
    var nC = B.concepts || Object.keys(window.conceptsNames || {}).length;
    var nF = B.formulas || 0;
    var nSec = Object.keys(window.ARXIV_CAT_NAMES || {}).length;
    var nS = Object.keys(window.scientistsData || {}).length;
    // Ноль здесь значил бы «авторов нет», а на самом деле значит «число ещё не
    // приехало»: граф авторов мы больше не качаем (24.4 МБ ради одной цифры).
    // Неизвестное не печатаем — позиция просто отсутствует, пока не станет известной.
    var nAu = (window.__buildInfo && window.__buildInfo.authors)
              || Object.keys(window.authorsGraph || {}).length || 0;
    var nLang = (document.querySelectorAll('#langs-bar a').length || 4);
    // «5 языка» — грамматическая ошибка на самом видном месте главной (владелец 2026-08-02).
    // Русскому нужны три формы: 1 язык, 2-4 языка, 5+ языков.
    var langWord = lang === 'ru'
        ? (nLang % 10 === 1 && nLang % 100 !== 11 ? 'язык'
           : (nLang % 10 >= 2 && nLang % 10 <= 4 && (nLang % 100 < 12 || nLang % 100 > 14) ? 'языка' : 'языков'))
        : L.langs;
    // Компактная ОДНА строка (юзер 2026-07-25 «сократи, сожми, уплотни»): 16795 → 16.8k.
    function kfmt(n){ return n >= 10000 ? (n / 1000).toFixed(1).replace('.0', '') + 'k' : String(n); }
    function part(n, w){ return '<b>' + kfmt(n) + '</b> ' + w; }
    var bits = [
        part(nA, L.articles),
        part(nC, L.concepts), part(nF, L.formulas), part(nSec, L.sections),
        part(nS, L.scientists), part(nAu, L.authors), part(nLang, langWord)
    ].filter(function (s) { return s.indexOf('<b>0</b>') !== 0; });
    el.innerHTML = bits.join(' · ');
    var B2 = window.__buildInfo;
    if (B2 && B2.built) {
        var upd = {ru:'обновлено', en:'updated', es:'actualizado', ar:'حُدّث', fr:'mis à jour'}[lang] || 'updated';
        el.innerHTML += ' <span class="stats-built">/ ' + upd + ' ' + B2.built + '</span>';
    }
}

/* Числа корпуса и дата сборки — один запрос на двести байт, один раз за страницу.
   Раньше он жил внутри renderSiteStats под флажком на элементе; чтобы перерисовать
   строку с приехавшими числами, флажок приходилось снимать — и перерисовка запускала
   загрузку заново, по кругу. Здесь этого не может случиться по устройству: функция
   вызывается один раз, а рисование ничего не грузит. */
(function loadBuildInfo() {
    if (!document.getElementById('site-stats')) return;
    fetch('/data/build-info.json')
        .then(function (r) { return r.json(); })
        .then(function (b) {
            if (!b) return;
            window.__buildInfo = b;
            renderSiteStats();
        })
        .catch(function () {});
})();

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
    // Индексы соседних уровней теперь грузятся в простое, а не в общей волне (см. ниже).
    // Если читатель начал искать раньше, чем простой наступил, — дёргаем сами и
    // перерисовываем выдачу, когда они доедут. До того ищем по текущему уровню:
    // неполно, но мгновенно, и это лучше пустого экрана в ожидании 2,5 МБ.
    if (typeof ensureOtherVersions === 'function' && !_otherVersionsPromise) {
        ensureOtherVersions().then(function () {
            var box = document.querySelector('.search-box');
            if (box && box.value === query) doFullSearch(query);
        });
    }
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
    // На странице избранного поиск ищет ВНУТРИ избранного: подмена его всем сайтом
    // лишала раздел смысла (QA 2026-07-29). Пустое избранное отвечает пустотой честно.
    if (window.__favoritesPage) {
        var favSet = {};
        try { JSON.parse(localStorage.getItem('favorites') || '[]').forEach(function (id) { favSet[id] = true; }); } catch (e) {}
        results = results.filter(function (item) { return favSet[item.id]; });
    }
    if (filters.text) {
        var q = filters.text;
        results = results.filter(function(item) {
            return (item.title || '').toLowerCase().includes(q) ||
                   (item.oneliner || '').toLowerCase().includes(q) ||
                   // Ищем по тому тексту, что видит читатель на карточке — теперь это
                   // description (2026-07-31). Аннотацию оставляем в поиске как второй
                   // источник: она есть у 1967 старых статей и расширяет находимость
                   // (без неё en «quantum» терял 119 статей — QA 2026-07-29), а мусора
                   // не даёт, потому что ищется, но не показывается.
                   (item.description || '').toLowerCase().includes(q) ||
                   // abstract из индекса убран (13 августа): он весил 1.14 МБ и давал
                   // совпадения по тексту, которого на карточке нет. Поиск по полному
                   // смыслу делает векторный поиск на стороне Worker'а.

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
    // Два смысла одного крестика (владелец 2026-08-02: «как закрыть окошко — непонятно»):
    // есть текст — крестик чистит его; ПУСТО — закрывает саму панель. Так работает
    // поиск в браузерах и телефонах, читатель это уже умеет. Esc закрывает всегда —
    // обработчик в initSearchToggle.
    var input = document.querySelector('.search-box');
    if (input && input.value) {
        input.value = '';
        renderActiveFilters('');
        showLatest();
        input.focus();
        return;
    }
    var panel = document.getElementById('search-panel');
    if (panel) panel.classList.remove('open');
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
    return '<a href="/lang/' + 'en' + '/authors/' + slug + '.html" class="author-row" data-author="' + name + '">' +
        '<span class="author-name">' + name + '</span>' +
        '<span class="author-tags">' + tagsHtml + '</span>' +
        '<span class="author-count">' + count + ' ' + UI.articlesWord + '</span></a>';
}

// Отложенный запуск: перебор 45 тысяч имён и сборка HTML на КАЖДОЕ нажатие клавиши
// вешали страницу с первой буквы (владелец 2026-08-24: «как только букву вводишь —
// подвисает»). Считаем только когда пользователь остановился на четверть секунды.
var _authorsDebounce = null;
function filterAuthors(query) {
    clearTimeout(_authorsDebounce);
    _authorsDebounce = setTimeout(function () { _filterAuthorsNow(query); }, 250);
}

var AUTHORS_RENDER_CAP = 300;

function _filterAuthorsNow(query) {
    var container = document.getElementById('author-cloud');
    if (!container) return;
    var q = query.trim().toLowerCase();

    // Поиск задан — ищем по ВСЕМ авторам, а не внутри открытой буквы (владелец:
    // «если поиск задан — забываем про буквы, сыпем всех»). Буквы остаются способом
    // листать без поиска.
    if (q && !isAuthorsIndexPage()) {
        if (_authorsDefaultHTML === null) _authorsDefaultHTML = container.innerHTML;
        if (!Object.keys(authorsGraph).length) {
            ensureAuthorsGraph().then(function () { _filterAuthorsNow(query); });
            return;
        }
        renderAuthorSearch(container, q);
        return;
    }
    if (!q && _authorsDefaultHTML !== null && !isAuthorsIndexPage()) {
        container.innerHTML = _authorsDefaultHTML;
        return;
    }

    if (isAuthorsIndexPage()) {
        if (_authorsDefaultHTML === null) _authorsDefaultHTML = container.innerHTML;
        if (!q) { container.innerHTML = _authorsDefaultHTML; return; }
        if (!Object.keys(authorsGraph).length) {   // граф ленивый — дождаться и повторить
            ensureAuthorsGraph().then(function() { filterAuthors(query); });
            return;
        }
        renderAuthorSearch(container, q);
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
function renderAuthorSearch(container, q) {
    var names = Object.keys(authorsGraph)
        .filter(function (name) { return name.toLowerCase().includes(q); })
        .sort(function (a, b) { return a.localeCompare(b); });
    // Отдаём первые три сотни: строить DOM на двадцать тысяч совпадений по букве «a» —
    // это и была вторая половина подвисания. Уточнил запрос — список сузился.
    var shown = names.slice(0, AUTHORS_RENDER_CAP);
    var more = names.length - shown.length;
    container.innerHTML = (shown.length
        ? shown.map(function (n) { return authorRowHTML(n, authorsGraph[n]); }).join('')
        : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>')
        + (more > 0
            ? '<p style="color:var(--soft);text-align:center;padding:14px">+' + more + '…</p>'
            : '');
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
    var vh = window.innerHeight || 800;
    document.querySelectorAll('.article-card, .article-main section, .ai-cover, .formula, .key-numbers').forEach(function (el) {
        if (el.dataset.rev) return; el.dataset.rev = '1'; el.classList.add('reveal');
        // Мобильные браузеры (особенно после нативного перехода между тирами сложности) часто НЕ
        // присылают начальный колбэк IntersectionObserver для элементов, уже находящихся во вьюпорте —
        // контент застревал на opacity:0 и «пропадал» до ручного обновления (баг только на мобиле,
        // десктоп ок). Раскрываем уже видимые элементы синхронно, а observer оставляем для остальных.
        var r = el.getBoundingClientRect();
        if (r.top < vh && r.bottom > 0) { el.classList.add('in'); return; }
        _revealObs.observe(el);
    });
    // Финальная сеть безопасности: если observer вообще не сработал (сломан на этом заходе),
    // раскрываем всё нераскрытое через 1.6с — контент важнее анимации.
    clearTimeout(initReveal._t);
    initReveal._t = setTimeout(function () {
        document.querySelectorAll('.reveal:not(.in)').forEach(function (el) { el.classList.add('in'); });
    }, 1600);
    initImgSpinners();
}

// D (юзер 2026-07-25): пока картинка грузится — шиммер-плейсхолдер (CSS ::before на обёртке),
// снимаем его классом .img-ready по onload/onerror. Идемпотентно (dataset-флаг).
function initImgSpinners(root) {
    (root || document).querySelectorAll('.card-img-wrap img, .ai-cover img').forEach(function (img) {
        var wrap = img.closest('.card-img-wrap, .ai-cover');
        if (!wrap || wrap.dataset.imgw) return;
        wrap.dataset.imgw = '1';
        var done = function () { wrap.classList.add('img-ready'); };
        if (img.complete && img.naturalWidth > 0) { done(); return; }
        img.addEventListener('load', done);
        img.addEventListener('error', done);   // ошибка → тоже снимаем шиммер (onerror сам подставит фолбэк/скроет)
    });
}
window.initImgSpinners = initImgSpinners;
window.initReveal = initReveal;
document.addEventListener('DOMContentLoaded', initReveal);

// ── Уровни прямо на карточке ────────────────────────────────────────────────
// Три ссылки над заголовком: попасть сразу в нужную глубину, не открывая статью и не
// переключаясь внутри. Заменили общий бегунок в шапке (2026-07-28). Иконки те же, что на
// странице статьи, — вид один на весь сайт.
var LVL_SVG = {
    // Одна строка / две / три — знак про объём текста. Прежние росток-книга-лупа на мелком
    // размере не читались (2026-07-28).
    simple: '<path d="M5 12h14"/>',
    popular: '<path d="M5 9h14"/><path d="M5 15h9"/>',
    advanced: '<path d="M5 7h14"/><path d="M5 12h14"/><path d="M5 17h8"/>'
};
var LVL_FILE = { simple: 'simple.html', popular: 'index.html', advanced: 'advanced.html' };
var LVL_LABEL = {
    ru: { simple: 'Просто', popular: 'Популярно', advanced: 'Подробно' },
    en: { simple: 'Simple', popular: 'Popular', advanced: 'Advanced' },
    es: { simple: 'Simple', popular: 'Popular', advanced: 'Avanzado' },
    ar: { simple: 'بسيط', popular: 'مبسّط', advanced: 'مفصّل' },
    fr: { simple: 'Simple', popular: 'Populaire', advanced: 'Détaillé' }
};

function levelSwitchHTML(base) {
    var loc = LVL_LABEL[lang] || LVL_LABEL.en;
    // На КАРТОЧКЕ в ленте ни один уровень не подсвечивается (владелец 2026-08-02:
    // «кажется, что "Просто" уже выбрано, а результат мы видим только после перехода»).
    // Это три РАВНОЗНАЧНЫХ входа в статью — «открыть проще / популярнее / подробнее», —
    // а не переключатель состояния: сам текст карточки от них не меняется. Подсветка
    // здесь обещала то, чего не происходит. На странице статьи активный уровень
    // подсвечивается по-прежнему — там он и правда выбран.
    return '<div class="lv-switch lv-switch-card">' + ['simple', 'popular', 'advanced'].map(function (v) {
        var on = '';
        return '<a class="lv-btn' + on + '" data-version="' + v + '" href="' + base + LVL_FILE[v]
             + '" title="' + loc[v] + '">'
             + '<svg class="vs-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
             + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + LVL_SVG[v] + '</svg>'
             + '<span class="lv-t">' + loc[v] + '</span></a>';
    }).join('') + '</div>';
}

/* Частота тегов по всему корпусу: считается один раз при первом обращении.
   Нужна, чтобы на карточке показывать ГЛАВНЫЕ теги статьи, а не первые попавшиеся. */
var _tagFreq = null;
function pickTop(tags, n) {
    /* Частота тегов считалась перебором индекса. Индекс на ленте больше не грузится,
       поэтому веса выходят нулевые и сортировка становится тождественной: теги
       остаются в порядке генерации. Это ХУЖЕ прежнего (частый тег вёл в живой раздел,
       редкий в пустой), но не сломано. Чинится числами из сводки — отложено до
       окончания перестройки понятий, чтобы не считать частоты дважды. */
    if (!_tagFreq) {
        _tagFreq = {};
        (window.searchIndex || []).forEach(function (a) {
            (a.tags || []).forEach(function (t) { _tagFreq[t] = (_tagFreq[t] || 0) + 1; });
        });
    }
    return tags.filter(Boolean).slice().sort(function (a, b) {
        return (_tagFreq[b] || 0) - (_tagFreq[a] || 0);
    }).slice(0, n);
}

/* Законы статьи ВЫВОДИМ ИЗ ТЕГОВ по графу знаний, а не спрашиваем у модели.
   Решение владельца 2026-08-02: «законы добавлять в промпт не надо — их надо вытащить
   через теги, у нас же полный граф». И это оказалось не только дешевле, но и точнее:
   напрямую закон проставлен лишь у 14% статей (у экспрессов — ни у одной, промпт про
   законы не спрашивает), а через теги закон находится у 99%. Связи берём из
   data/tag-laws.json — выжимка рёбер law-tag из графа знаний.

   Отбираем законы, подтверждённые НЕСКОЛЬКИМИ тегами статьи: один общий тег даёт
   случайную связь, два и больше — осмысленную. Если таких нет, берём закон самого
   главного тега. */
var _tagLaws = null;
fetch('/data/tag-laws.json').then(function (r) { return r.json(); })
    .then(function (m) { _tagLaws = m; }).catch(function () { _tagLaws = {}; });

function lawsFor(item) {
    if (item.laws && item.laws.length) return item.laws;   // проставлено явно — уважаем
    if (!_tagLaws) return [];
    var tags = item.tags || [], score = {};
    tags.forEach(function (t) {
        (_tagLaws[t] || []).forEach(function (l) { score[l] = (score[l] || 0) + 1; });
    });
    var ranked = Object.keys(score).sort(function (a, b) { return score[b] - score[a]; });
    var strong = ranked.filter(function (l) { return score[l] >= 2; });
    return strong.length ? strong : ranked.slice(0, 1);
}

function cardHTML(item) {
    // Язык страницы, а НЕ язык по умолчанию: иначе с английской ленты клик уводил
    // на русскую статью и выбранный язык терялся (2026-07-28).
    var base = '/lang/' + lang + '/archive/' + item.date + '/' + item.id + '/';
    // Заголовок открывает статью в ТОМ уровне, который читатель выбрал, — иначе выбор
    // ни на что не влияет и кажется, что кнопки не работают (2026-07-28).
    var url = base + (LVL_FILE[currentVersion] || 'index.html');
    // В списках — полная аннотация (адаптация авторского arXiv-abstract) БЕЗ обрезки на дисплее —
    // нужный размер уже задан в промпте генерации (data/prompts/adapt-abstract.txt: 350/550/900
    // символов на popular/simple/advanced), здесь всегда показываем как есть, целиком.
    // Мини — свой threads-текст, короче по своей природе, но и он не режется.
    // ПОРЯДОК ВАЖЕН (владелец 2026-07-31: «такого текста близко у нас быть не должно»).
    // Раньше первой шла аннотация — адаптация авторского abstract. Она сделана отдельным
    // вызовом модели с брифом «сохрани суть и результаты», поэтому открывалась термином
    // и читалась как паспорт статьи, тогда как description той же статьи написан нашим
    // голосом, с аналогией. На карточке — витрина сайта — теперь наш голос: description,
    // и только если его нет — аннотация. Промпт аннотации переписан тем же днём, но
    // у 2110 уже сгенерированных статей она осталась старой; порядок чинит их бесплатно.
    // Аннотации на карточке нет вовсе (решение владельца 2026-07-31: «убери, такое никогда
    // не показывай»). Она остаётся внутри статьи как строгая версия — там она к месту.
    var bodyText = item.description || item.oneliner || '';
    var cat = (item.categories || [])[0] || '';
    var catName = (window.ARXIV_CAT_NAMES && ARXIV_CAT_NAMES[cat]) || cat;
    var catDesc = (window.ARXIV_CAT_DESC && ARXIV_CAT_DESC[cat]) || '';
    // Авторы: своя строка (переносится на 1-2 строки по ширине карточки), до 20 — с "+N" на остаток
    var au = item.authors || [];
    var authorsHtml = au.slice(0, 20).map(function(a) {
        return '<a href="/lang/' + 'en' + '/authors/' + authorSlug(a) + '.html" data-author="' + a + '">' + a + '</a>';
    }).join('<span class="sep">·</span>') + (au.length > 20 ? ' <span class="au-more-lite">+' + (au.length - 20) + '</span>' : '');
    /* Сущности на карточке: ФОРМА отличает тип (владелец 2026-08-02).
       Тег — круглая пилюля, учёный — скруглённый прямоугольник, закон — строгий квадрат.
       Читатель узнаёт тип раньше, чем прочитает слово, и это работает на любом языке,
       включая арабский, где длина слов другая. Типографика одна и та же везде: в ленте,
       в статье, в облаках — иначе форма перестаёт что-либо значить.

       Теги отбираем по ЧАСТОТЕ в корпусе, а не по порядку из генерации: у статьи их до 11,
       на карточке нужно 5 главных. Частый тег ведёт в живой раздел, редкий — в пустой. */
    var tagsHtml = pickTop(item.tags || [], 5).map(function(t) {
        // Показываем ТОЛЬКО то, у чего есть своя страница. Владелец 28.08 нашёл
        // на карточке «molecular dynamics» с подписью «карточки пока нет»:
        // «это откуда, нам не надо — всё, что есть, то есть; чего нет, потом,
        // как появляется, добавляем». Заглушка обещала содержание, которого нет,
        // и уводила в поиск вместо объяснения.
        if (conceptsNames[t]) {
            return '<a class="ent ent-tag" href="/lang/' + lang + '/concepts/' + encodeURIComponent(t) + '.html" data-tag="' + t + '">' + (conceptsNames[t].name || t.replace(/_/g, ' ')) + '</a>';
        }
        return tagsLoc[t]
            ? '<a class="ent ent-tag" href="/lang/' + lang + '/tags/' + encodeURIComponent(t) + '.html" data-tag="' + t + '">' + (tagsLoc[t].name || t.replace(/_/g, ' ')) + '</a>'
            : '';
    }).filter(Boolean).join('');
    var sciHtml = (item.scientists || []).slice(0, 3).map(function(s) {
        var sd = scientistsData[s];
        // Карточка есть не у каждого имени: замер 13 августа — в статьях упоминаются 345
        // учёных, а карточек 201, и 169 ссылок вели прямиком в 404. Пока справочник
        // догоняет, имя без карточки ведёт в поиск по этому имени: читатель попадает
        // на список статей, где о нём говорится, а не в пустоту.
        return sd
            ? '<a class="ent ent-sci" href="/lang/' + lang + '/scientists/' + authorSlug(s) + '.html" data-scientist="' + s + '">' + (sd.name || s) + '</a>'
            : '';
    }).join('');
    var lawHtml = lawsFor(item).slice(0, 2).map(function(l) {
        if (conceptsNames[l]) {
            return '<a class="ent ent-law" href="/lang/' + lang + '/concepts/' + encodeURIComponent(l) + '.html" data-law="' + l + '">' + (conceptsNames[l].name || l.replace(/_/g, ' ')) + '</a>';
        }
        var ld = lawsData[l];
        return ld
            ? '<a class="ent ent-law" href="/lang/' + lang + '/laws/' + encodeURIComponent(l) + '.html" data-law="' + l + '">' + (ld.name || l.replace(/_/g, ' ')) + '</a>'
            : '';
    }).join('');
    tagsHtml = lawHtml + sciHtml + tagsHtml;
    // Реакции + избранное прямо в карточке (клики — через делегирование в likes.js; подсветка — на этапе сборки)
    var _likeId = item.id + '_' + lang + '_' + currentVersion;
    var _myR = (typeof myReaction === 'function' ? (myReaction(_likeId) || '') : '');
    var _favOn = (typeof isFavorite === 'function' && isFavorite(item.id));
    var cardActions =
        '<div class="card-actions" data-article-id="' + _likeId + '">' +
        '<button class="react-btn sm' + (_myR === 'like' ? ' active' : '') + '" data-react="like" title="Нравится">' + b42ic('like', 17, '👍') + '<span class="rc"></span></button>' +
        '<button class="react-btn sm' + (_myR === 'dislike' ? ' active' : '') + '" data-react="dislike" title="Не нравится">' + b42ic('dislike', 17, '👎') + '<span class="rc"></span></button>' +
        '<button class="fav-btn sm' + (_favOn ? ' active' : '') + '" data-fav="' + item.id + '" title="В избранное"><span class="fav-ic">' + (_favOn ? '★' : '☆') + '</span></button>' +
        // Три входа в статью — здесь же, правее реакций; CSS прижимает их к краю.
        levelSwitchHTML(base) +
        '</div>';
    // Обложки лежат ОДИН раз, под ru (умысел: экономия гигабайтов). Ссылки — по языку
    // страницы, а картинки — всегда из ru-папки. Сборка пути по языку страницы давала
    // ленты en/es/ar вовсе без обложек: оба запроса 404 (QA-блокер №1, 2026-07-29).
    var imgBase = '/lang/' + (typeof defaultLang !== 'undefined' ? defaultLang : 'ru') +
                  '/archive/' + item.date + '/' + item.id + '/';
    var img = imgBase + 't_ai.webp';
    var imgFb = imgBase + 'ai.webp';
    // item.image === false — решено уже при генерации (нет ai.webp), не пытаемся грузить и не
    // резервируем место под картинку. undefined (старый индекс до пересборки) — считаем как есть.
    var hasImg = item.image !== false;
    // Мета-строка (раздел·дата·бейдж) — полноширинный «eyebrow» НАД картинкой: тогда плавающая
    // мини-картинка стартует под ним, вровень с заголовком (юзер-фидбек 2026-07-19: "мини картинку
    // выровнять по названию"). Раньше мета была первой строкой card-body — картинка обтекалась от
    // самого верха и её край торчал выше заголовка на высоту меты.
    // Одна служебная строка вместо двух (владелец 2026-08-02: «ссылку на оригинал и сколько
    // минут читать — в ту строку, где раздел и дата, не засоряем подвал»). Всё, что относится
    // к «паспорту» статьи, живёт сверху; низ карточки остаётся под теги и действия.
    // Описание раздела уходит в data-, а не в title: нативная подсказка рисуется строкой,
    // уезжает за экран и на телефоне не показывается вовсе.
    var eyebrow = (catName || item.date || item.express || item.reading) ?
        '<div class="card-eyebrow">' +
            (catName ? '<a class="card-cat" href="#" data-cat="' + cat + '" data-cat-desc="' + catDesc.replace(/"/g, '&quot;') + '" onclick="filterByCategory(\'' + cat + '\');return false;">' +
                // знак группы перед названием: в ленте из двадцати работ разных наук глаз
                // цепляется за рисунок раньше, чем прочитает слово (владелец 2026-08-05)
                (window.B42Icons && B42Icons.sectionIcon ? B42Icons.sectionIcon(cat, 14) : '') +
                '<span class="card-cat-t">' + catName + '</span></a>' : '') +
            (item.date ? '<span class="card-date">' + item.date + '</span>' : '') +
            (item.reading ? '<span class="card-read">' + item.reading + ' ' + UI.min + '</span>' : '') +
            '<a class="card-src" href="https://arxiv.org/abs/' + item.id + '" target="_blank" rel="noopener">arXiv:' + item.id + '</a>' +
            // Цитируемость Scholar (поле cites приходит из индекса; молчим, если нет)
            (item.cites ? '<span class="card-cites" title="Citations — Semantic Scholar">' + item.cites.toLocaleString() + ' cit</span>' : '') +
            (item.express ? '<span class="card-express-badge" title="' + UI.expressTip + '">' + UI.express + '</span>' : '') +
        '</div>' : '';
    return '<article class="article-card">' +
        eyebrow +
        (hasImg ? (
        '<a class="card-img-wrap" href="' + url + '">' +
            '<img src="' + img + '" data-fb="' + imgFb + '" loading="lazy" onerror="if(this.dataset.fb){this.src=this.dataset.fb;this.removeAttribute(\'data-fb\');}else{this.closest(\'.card-img-wrap\').style.display=\'none\';}" alt="">' +
        '</a>') : '') +
        '<div class="card-body">' +
            // Уровни чтения НЕ здесь, а внизу, в строке действий (владелец 28.08:
            // «сверху маячат над названием»). Первым в карточке должен читаться
            // заголовок статьи, а не ряд кнопок.
            '<a class="card-title" href="' + url + '">' + item.title + '</a>' +
            // Значок машины знаний у названия. Ведёт СРАЗУ в раздел рекомендаций и всегда
            // в продвинутую версию — раздел живёт только там (владелец 11 августа: «плюсик
            // виден во всех версиях и списках, при нажатии переход на рекомендации»).
            // Отдельной ссылкой ПОСЛЕ заголовка, а не внутри него: ссылка внутри ссылки —
            // недопустимая вложенность, браузер её разрывает и значок выпадает из строки.
            (item.km ? '<a class="km-badge" href="' + base + 'advanced.html#km-advice"' +
                       ' title="' + (UI.kmTip || '') + '" aria-label="' + (UI.kmTip || '') + '">✛</a>' : '') +
            (bodyText ? '<div class="card-desc">' + bodyText + '</div>' : '') +
            (authorsHtml ? '<div class="card-authors">' + authorsHtml + '</div>' : '') +
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
var feed = { items: [], shown: 0, batch: 12, lastDay: null, active: false,
             q: null, page: 0, more: false, busy: false, total: null };

/* ЛЕНТА ИЗ ОБЛАКА. Адрес ручки: на сайте она своя же (пустая база), локально её
   поднимает tools/dev_server.py. window.B42_API оставлен для случая, когда страницу
   смотрят с файловой системы. */
var API = (typeof window.B42_API === 'string' ? window.B42_API : '');

/* Облако выключается САМО и навсегда для этой страницы после первой неудачи.
   Пробовать снова на каждой прокрутке — значит на плохой сети показывать читателю
   череду пустых догрузок вместо ленты. Один отказ, один откат, дальше индекс. */
var cloudOff = false;

/* Наш порядок зовётся random, ручкин — mix. Ручка неизвестное значение молча
   приводит к mix, поэтому несовпадение работало «само» — и именно поэтому его надо
   назвать вслух: завтра у ручки появится четвёртый порядок, и «само» перестанет. */
function cloudSort(mode) { return mode === 'random' ? 'mix' : mode; }

/* Запрос к облаку собирается В ОДНОМ МЕСТЕ. Дверей в ленту три — обычная, по разделу,
   по дате, — и глобальный тумблер «скрыть экспресс» обязан применяться во всех. Пока
   каждая дверь собирала запрос сама, забыть его в одной из трёх было делом времени.
   Второй тумблер, «только с советами», в облако не ложится (поля advice в карточках
   базы нет) — при нём лента идёт по индексу, см. cloudUsable. */
function cloudQuery(extra) {
    var q = { sort: cloudSort(getSortMode()) };
    if (hideExpress) q.express = 0;
    if (extra) Object.keys(extra).forEach(function (k) { q[k] = extra[k]; });
    return q;
}

/* Можно ли открыть эту ленту из облака. Три «нет»: страница сущности (её рисует свой
   модуль), избранное (источник — localStorage), включённый фильтр по советам. */
function cloudUsable() {
    return !isEntityPage && !window.__favoritesPage && !onlyAdvice && !cloudOff;
}

function feedFromCloud(query, page) {
    var u = API + '/api/feed?lang=' + encodeURIComponent(lang) +
            '&version=' + encodeURIComponent(effVersion()) +
            '&limit=' + feed.batch + '&page=' + page +
            '&sort=' + encodeURIComponent(query.sort || 'mix');
    if (query.cat) u += '&cat=' + encodeURIComponent(query.cat);
    if (query.date) u += '&date=' + encodeURIComponent(query.date);
    if (query.express === 0 || query.express === 1) u += '&express=' + query.express;
    return fetch(u).then(function (r) {
        if (!r.ok) throw 0;
        return r.json();
    }).then(function (j) {
        if (!j || !Array.isArray(j.items)) throw 0;
        return j;
    });
}

/* Сводка корпуса: числа по дням и по разделам. Одна загрузка на страницу, ~13 КБ.
   Ради этих чисел раньше качался весь индекс — календарю нужны ДНИ, полосе разделов
   НАЗВАНИЯ, фильтру глубины ДВА ЧИСЛА, а приезжали все тексты архива. */
var _corpusPromise = null;
function ensureCorpus() {
    if (_corpusPromise) return _corpusPromise;
    _corpusPromise = fetch(API + '/api/corpus?lang=' + encodeURIComponent(lang) +
                           '&version=' + encodeURIComponent(effVersion()))
        .then(function (r) { if (!r.ok) throw 0; return r.json(); })
        .then(function (c) { window.__corpus = c; return c; })
        .catch(function () { return null; });
    return _corpusPromise;
}
window.ensureCorpus = ensureCorpus;

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

// Порядок ленты — выбор читателя, по умолчанию случайный (юзер 2026-07-29).
// Причина отказа от даты по умолчанию: у нас две тысячи статей, а по дате наверху всегда
// одни и те же свежие. Остальное читатель не видел ни разу. Случайный порядок открывает
// архив, ради которого всё и делалось.
var SORT_MODES = ['random', 'new', 'old'];
var SORT_LABELS = {
    ru: { random: 'вперемешку', new: 'сначала новые', old: 'сначала старые', label: 'Порядок' },
    en: { random: 'shuffled',    new: 'newest first', old: 'oldest first',  label: 'Order' },
    es: { random: 'al azar',     new: 'nuevos antes', old: 'antiguos antes', label: 'Orden' },
    ar: { random: 'عشوائي',      new: 'الأحدث أولاً', old: 'الأقدم أولاً',   label: 'الترتيب' },
    fr: { random: 'mélangé',     new: 'récents d\'abord', old: 'anciens d\'abord', label: 'Ordre' }
};
function getSortMode() {
    try {
        var v = localStorage.getItem('b42_sort');
        if (SORT_MODES.indexOf(v) !== -1) return v;
    } catch (e) {}
    return 'random';
}
function setSortMode(m) {
    try { localStorage.setItem('b42_sort', m); } catch (e) {}
}

// Первый экран ленты — витрина: наверх только статьи с настоящей обложкой
// (владелец, ночь 2026-07-30: «первый десяток — картинки наши обязательно хорошие»).
// Перемешивание честное, но безкартиночные опускаются ниже десятого места: пустая
// рамка в первом экране читается как недоделанность, даже если текст отличный.
function promoteWithCovers(arr, topN) {
    var withImg = [], without = [];
    for (var i = 0; i < arr.length; i++) {
        (arr[i].image !== false ? withImg : without).push(arr[i]);
    }
    if (withImg.length >= topN) return withImg.concat(without);
    return arr;   // картинок мало — не перетасовываем, лента честнее полупустой витрины
}

/* Экспресс — в конец любого списка при прочих равных (владелец 2026-07-31).
   Устойчивое разделение на две группы: внутри каждой порядок, который список задал
   сам (свежесть, вес совпадения, случайность), — мы лишь опускаем короткие заметки
   под разборы, а не перетасовываем всё заново. */
function fullFirst(arr) {
    var full = [], express = [];
    for (var i = 0; i < arr.length; i++) (arr[i].express ? express : full).push(arr[i]);
    return full.concat(express);
}
window.b42FullFirst = fullFirst;

function sortFeed(arr, mode) {
    if (mode === 'random') {
        // Тасование Фишера — Йетса по всему списку, а не по верхушке.
        for (var i = arr.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1));
            var t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        }
        // Даже «вперемешку» ставит полные выше: правило владельца 2026-07-31 —
        // «при прочих равных экспресс понижен в ЛЮБЫХ списках». Случайность остаётся
        // внутри каждой группы, поэтому лента по-прежнему разная при каждом заходе.
        return promoteWithCovers(fullFirst(arr), 10);
    }
    // По дате: полные статьи выше express — короткая заметка не должна вытеснять разбор.
    return promoteWithCovers(arr.sort(function(a, b) {
        var ae = a.express ? 1 : 0, be = b.express ? 1 : 0;
        if (ae !== be) return ae - be;
        return mode === 'old' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date);
    }), 10);
}

// Порядок относится к ленте целиком. В отфильтрованных списках (избранное, раздел, дата,
// результаты поиска) он бы врал: там свой порядок и своя логика — прячем.
function hideSortControl() {
    var box = document.getElementById('feed-sort');
    if (box) box.style.display = 'none';
}

function mountSortControl() {
    var results = document.getElementById('search-results');
    if (!results) return;
    var L = SORT_LABELS[lang] || SORT_LABELS.en;
    var box = document.getElementById('feed-sort');
    if (!box) {
        box = document.createElement('div');
        box.id = 'feed-sort';
        box.className = 'feed-sort';
        results.parentNode.insertBefore(box, results);
    }
    box.style.display = '';
    var cur = getSortMode();
    box.innerHTML = '<span class="feed-sort-label">' + L.label + '</span>' +
        SORT_MODES.map(function (m) {
            return '<button type="button" class="feed-sort-btn' + (m === cur ? ' active' : '') +
                   '" data-sort="' + m + '">' + L[m] + '</button>';
        }).join('');
    box.onclick = function (e) {
        var b = e.target.closest('[data-sort]');
        if (!b) return;
        setSortMode(b.dataset.sort);
        showLatest();
    };
}

// Плашка «молодого языка»: тонкая лента без объяснения выглядит сломанной (сценарии fr).
// CSS .young-lang уже свёрстан дизайнером; здесь — разметка и словарь (находка QA: стиль
// был готов, разметку не выдавал никто).
var YOUNG_LANG_TXT = {
    // {tags}/{laws}/{sci} подставляются из ЗАГРУЖЕННЫХ справочников, а не числами в тексте:
    // числа в справочниках растут каждую неделю, а литерал в строке — никогда, и однажды
    // плашка начнёт врать читателю про наш же объём.
    fr: {t: "La section française vient d'ouvrir", d: "<b>{n}</b> articles traduits, de nouveaux chaque jour. En attendant : <a href='/lang/fr/tags/'>{tags} concepts</a>, <a href='/lang/fr/laws/'>{laws} lois</a> et <a href='/lang/fr/scientists/'>{sci} scientifiques</a> déjà en français."},
    es: {t: "Sección joven", d: "<b>{n}</b> artículos y creciendo a diario."},
    ar: {t: "قسم جديد", d: "<b>{n}</b> مقالة مترجمة، والمزيد يومياً."}
};
function mountYoungLangNote(count) {
    var box = document.getElementById('young-lang-note');
    var txt = YOUNG_LANG_TXT[lang];
    if (!txt || count >= 20) { if (box) box.remove(); return; }
    if (!box) {
        var results = document.getElementById('search-results');
        if (!results) return;
        box = document.createElement('div');
        box.id = 'young-lang-note'; box.className = 'young-lang';
        results.parentNode.insertBefore(box, results);
    }
    var size = function (o) { return o ? Object.keys(o).length : 0; };
    box.innerHTML = '<b>' + txt.t + '</b> — ' + txt.d
        .replace('{n}', count)
        .replace('{tags}', size(window.tagsLoc))
        .replace('{laws}', size(window.lawsData))
        .replace('{sci}', size(window.scientistsData));
}

function showLatest() {
    // Страница автора рисуется своим модулем (см. _authorLive). Проверка стоит ЗДЕСЬ, а не
    // только в _defaultFeed: showLatest зовут ещё из четырёх мест напрямую — при смене
    // уровня, при очистке поиска, при сбросе фильтров, — и каждое из них затирало бы
    // разложенный по людям список.
    if (_authorLive()) {
        if (typeof window.B42AuthorLive === 'function') window.B42AuthorLive();
        return;
    }
    // Страницы тега/учёного/раздела, перешедшие на живой список (js/entity-live.js),
    // рисуются им же — по той же причине, что и автор: лента из индекса затёрла бы
    // постраничный список вместе с кнопкой догрузки.
    var _lb = document.getElementById('search-results');
    if (_lb && _lb.dataset && _lb.dataset.live === '1') {
        if (typeof window.B42EntityLive === 'function') window.B42EntityLive();
        return;
    }
    mountSortControl();

    // ЛЕНТА ГЛАВНОЙ — ИЗ ОБЛАКА. Двенадцать карточек это ~20 КБ; тот же экран из индекса
    // стоил 14.6 МБ, потому что весь архив с текстами приезжал ради первой пачки.
    // Условие: страница без контекста сущности (главная), не избранное, облако не отпало.
    if (cloudUsable()) {
        openCloudFeed(cloudQuery(), function () { return ''; })
            .then(function (j) {
                // Плашка «молодого языка» смотрит на РАЗМЕР РАЗДЕЛА, а не на длину пачки:
                // двенадцать карточек приходят и во французском, где статей всего сорок.
                mountYoungLangNote(typeof j.total === 'number' ? j.total : 99);
            })
            .catch(function () { cloudOff = true; showLatestFromIndex(); });
        return;
    }
    showLatestFromIndex();
}

/* Прежняя лента — из индекса. Осталась запасным путём и единственным путём там, где
   облако не при чём: избранное (источник localStorage) и страницы, куда лента попадает
   с контекстом сущности. Индекс поднимается ПО ТРЕБОВАНИЮ: заранее его больше никто
   не качает, иначе вся затея бессмысленна. */
function showLatestFromIndex() {
    var c0 = document.getElementById('search-results');
    if (c0 && !searchIndex.length && typeof ensureSearchIndex === 'function') {
        c0.innerHTML = '<p style="color:var(--soft);text-align:center;padding:40px">' +
                       (UI.loading || '…') + '</p>';
        ensureSearchIndex().then(function () { showLatestFromIndex(); });
        return;
    }
    var arr = sortFeed(
        applyPageContext(searchIndex.filter(function(item) { return item.version === effVersion(); })),
        getSortMode()
    );
    mountYoungLangNote(arr.length);
    feed.q = null;
    feed.items = arr;
    feed.shown = 0; feed.lastDay = null; feed.active = true;
    var c = document.getElementById('search-results');
    if (c) c.innerHTML = feed.items.length ? '' : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>';
    renderMoreFeed();
    updateSearchRowVisibility();
    // Приглашение в совет СНЯТО с ленты (владелец 2026-08-02: «убери окошко, которое
    // стартует; вход — прямой /council.html, а в about только намёк — это небольшой квест»).
    // Причина глубже удобства: в совет зовут за содержательное участие — внятный
    // комментарий, подтверждённое авторство статьи, — а не за число открытых страниц.
    // Всплывашка по счётчику просмотров звала не тех и обесценивала приглашение.
    // mountCouncilInvite();  — функция оставлена ниже: она понадобится, если совет
    // решит вернуть открытый вход (вопрос вынесен на заседание).
}
window.showLatest = showLatest;

/* ── Приглашение тем, кто дочитался ─────────────────────────────────────────
   Идея владельца 2026-07-31: человек, открывший сто статей, доказал делом, что ему
   интересно, — его и зовём. Фильтр по вовлечённости честнее анкеты: не спрашиваем
   «хотите к нам», а смотрим, кто уже здесь живёт.

   Считаем ОТКРЫТЫЕ статьи (js/scroll.js, ключ b42_read), а не пролистанные карточки:
   иначе приглашение получит каждый, кто минуту крутил ленту, и обесценится.

   Показываем строкой в конце ленты, а не окном поперёк экрана: это находка, а не
   объявление. Закрыл — больше не возвращается.

   Язык. Страница пока написана только по-русски, поэтому и приглашение появляется
   только в русской версии: отправлять араба на русскую стену — хуже, чем не звать
   вовсе. Список расширяется по мере перевода страницы, и это ЯВНЫЙ список, а не
   молчаливый откат на русский. */
var COUNCIL_MIN = 100;
// Языки, на которых страница существует. Список ЯВНЫЙ, а не «показываем всем»:
// отправить человека на стену на чужом языке хуже, чем не позвать вовсе. Пополняется
// вместе с переводом страницы (council_translate.py + council_page.py).
var COUNCIL_LANGS = ['ru', 'en', 'es', 'ar', 'fr'];
var COUNCIL_TXT = {
    ru: { t: 'Вы прочитали {n} статей',
          d: 'Дальше начинается кухня: как всё устроено, сколько стоит и что мы планируем.',
          a: 'Посмотреть изнутри' },
    en: { t: 'You have read {n} articles',
          d: 'Beyond this point is the kitchen: how it all works, what it costs, what we plan.',
          a: 'See it from inside' },
    es: { t: 'Ha leído {n} artículos',
          d: 'A partir de aquí empieza la cocina: cómo funciona todo, cuánto cuesta y qué planeamos.',
          a: 'Verlo por dentro' },
    ar: { t: 'قرأت {n} مقالة',
          d: 'من هنا يبدأ المطبخ: كيف يعمل كل شيء، وكم يكلّف، وما الذي نخطّط له.',
          a: 'انظر من الداخل' },
    fr: { t: 'Vous avez lu {n} articles',
          d: 'Ici commence les coulisses : comment tout fonctionne, ce que ça coûte et nos projets.',
          a: "Voir de l'intérieur" }
};

function readCount() {
    try { return (JSON.parse(localStorage.getItem('b42_read') || '[]') || []).length; }
    catch (e) { return 0; }
}

function mountCouncilInvite() {
    if (COUNCIL_LANGS.indexOf(lang) === -1) return;
    if (document.getElementById('council-invite')) return;
    try { if (localStorage.getItem('b42_council_hide') === '1') return; } catch (e) {}
    var n = readCount();
    if (n < COUNCIL_MIN) return;
    var host = document.getElementById('search-results');
    if (!host || !host.parentNode) return;
    var t = COUNCIL_TXT[lang] || COUNCIL_TXT.ru;

    var box = document.createElement('div');
    box.id = 'council-invite';
    box.className = 'council-invite';
    box.innerHTML =
        '<button type="button" class="ci-close" aria-label="закрыть">×</button>' +
        '<b>' + t.t.replace('{n}', n) + '</b>' +
        '<span>' + t.d + '</span>' +
        '<a href="/lang/' + lang + '/council.html">' + t.a + ' →</a>';
    host.parentNode.insertBefore(box, host.nextSibling);
    box.querySelector('.ci-close').addEventListener('click', function () {
        box.remove();
        try { localStorage.setItem('b42_council_hide', '1'); } catch (e) {}
    });
}

// Вкладка «Избранное»: карточки из localStorage.favorites (клиент, без сервера).
function showFavorites() {
    hideSortControl();
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

/* Лента по умолчанию. На странице автора её рисует НЕ этот файл, а js/author-live.js:
   там список приходит из D1 уже разложенным по разным людям с одинаковой подписью, чего
   индекс не умеет в принципе.

   Проверка нужна именно здесь, а не «кто успел». Первая версия полагалась на порядок:
   живой модуль отвечает за 0.2 с, индекс качается дольше — казалось, что модуль всегда
   первый. На проде вышло наоборот, и лента, дорисовавшись, стирала разложенный список
   вместе с кнопками автора. Гонки не выигрывают, их убирают.

   Признак — data-akey на контейнере: он есть только у страниц авторов и ставится тем же
   шаблоном, что подключает модуль. */
function _authorLive() {
    var b = document.getElementById('search-results');
    return !!(b && b.dataset && b.dataset.akey);
}

function _defaultFeed() {
    if (_authorLive()) return;
    if (window.__favoritesPage) showFavorites(); else showLatest();
}

function filterByCategory(cat) {
    hideSortControl();
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
// title уходит во всплывающую подсказку кнопки — там нужен чистый текст.
// Раньше в него был вшит 📅: подсказка читалась как «📅 Календарь», причём
// эмодзи рисовала система, то есть на каждой ОС по-своему. Знак теперь на самой
// кнопке и из нашего набора.
var CAL_LABELS = {
    ru: { title: 'Календарь', all: 'Все даты', months: ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'] },
    en: { title: 'Calendar', all: 'All dates', months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'] },
    zh: { title: '日历', all: '全部日期', months: ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'] },
    fr: { title: 'Calendrier', all: 'Toutes les dates', months: ['jan','fév','mar','avr','mai','juin','juil','août','sep','oct','nov','déc'] },
    ar: { title: 'التقويم', all: 'كل التواريخ', months: ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'] }
};

function filterByDate(prefix, label) {
    hideSortControl();
    var closePanel = function () {
        var p = document.getElementById('calendar-panel');
        if (p) p.classList.remove('open');
        window.scrollTo({ top: 0 });
    };
    if (cloudUsable()) {
        openCloudFeed(cloudQuery({ sort: 'new', date: prefix }), function (total) {
            return '<div class="feed-day" style="cursor:pointer" onclick="showLatest()">← ' +
                   (label || prefix) + (total != null ? ' (' + total + ')' : '') + '</div>';
        }).then(closePanel).catch(function () { cloudOff = true; filterByDate(prefix, label); });
        return;
    }
    if (!searchIndex.length && typeof ensureSearchIndex === 'function') {
        ensureSearchIndex().then(function () { filterByDate(prefix, label); });
        return;
    }
    feed.q = null;
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
    // Дерево год → месяц → день строится из ЧИСЕЛ. Раньше их считали перебором всего
    // индекса — 14.6 МБ текстов ради подписи «3» под датой. Сводка отдаёт готовые
    // счётчики по дням; при её отсутствии считаем по индексу, но только если он уже
    // загружен: качать архив ради календаря — та самая ошибка, от которой уходим.
    var tree = {};
    function addDay(date, n) {
        var y = date.slice(0, 4), m = date.slice(5, 7), d = date.slice(8, 10);
        (tree[y] = tree[y] || { c: 0, m: {} }).c += n;
        (tree[y].m[m] = tree[y].m[m] || { c: 0, d: {} }).c += n;
        tree[y].m[m].d[d] = (tree[y].m[m].d[d] || 0) + n;
    }
    var _c = window.__corpus;
    if (_c && _c.days) {
        Object.keys(_c.days).forEach(function (date) {
            if (date) addDay(date, _c.days[date][0]);
        });
    } else {
        searchIndex.filter(function(i) { return i.version === effVersion() && i.date; })
            .forEach(function(i) { addDay(i.date, 1); });
    }
    if (!Object.keys(tree).length) { panel.innerHTML = ''; return; }
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
    btn.onclick = function(e) { if (e) e.stopPropagation(); panel.classList.toggle('open'); };
    panel.onclick = function(e) {
        var t = e.target;
        if (t.classList && t.classList.contains('cal-all')) { showLatest(); panel.classList.remove('open'); return; }
        var day = t.closest ? t.closest('.cal-day') : null;
        if (day) { filterByDate(day.getAttribute('data-date'), day.getAttribute('data-date')); return; }
        var head = t.closest ? t.closest('.cal-head') : null;
        if (head) { var sub = head.nextElementSibling; if (sub) { sub.hidden = !sub.hidden; head.classList.toggle('open', !sub.hidden); } }
    };
    document.addEventListener('click', function(e) {
        if (panel.classList.contains('open') && !panel.contains(e.target) && !btn.contains(e.target)) {
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
    // Счётчики разделов — из сводки. Считались перебором индекса, хотя это те же числа.
    var counts = {};
    if (window.__corpus && window.__corpus.cats) {
        counts = window.__corpus.cats;
    } else {
        searchIndex.filter(function(i) { return i.version === effVersion(); }).forEach(function(i) {
            (i.categories || []).forEach(function(c) { counts[c] = (counts[c] || 0) + 1; });
        });
    }
    var cats = Object.keys(counts).sort(function(a, b) { return counts[b] - counts[a]; });
    if (!cats.length) { bar.innerHTML = ''; return; }
    bar.innerHTML = cats.map(function(c) {
        var desc = (ARXIV_CAT_DESC[c] || '').replace(/"/g, '&quot;');
        // Описание уходит в data-, а НЕ в title: нативная подсказка браузера рисуется
        // строкой во всю ширину (уезжает за экран) и на телефоне не показывается вовсе.
        // Владелец 2026-08-02: «все тултипы — карточка, а не строка, уходящая справа».
        return '<span class="cat-chip' + (selectedCats[c] ? ' active' : '') + '" data-cat="' + c + '" data-cat-desc="' + desc + '">' +
            // тот же знак, что и на карточке — источник соответствия один (B42Icons.sectionIcon),
            // иначе одна работа окажется в ленте под одним рисунком, а в панели под другим
            (window.B42Icons && B42Icons.sectionIcon ? B42Icons.sectionIcon(c, 13) : '') +
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

    // Один раздел спрашиваем у облака — это самый частый случай и он покрывается ручкой.
    // Несколько разделов сразу («+» на чипе) ручка не умеет, и городить ей список
    // не стоит: набор из пяти разделов выбирают редко, а индекс для этого уже есть.
    if (sel.length === 1 && cloudUsable()) {
        var one = sel[0];
        openCloudFeed(cloudQuery({ sort: 'new', cat: one }),
            function (total) {
                return '<div class="feed-day">' + (ARXIV_CAT_NAMES[one] || one) +
                       (total != null ? ' (' + total + ')' : '') + '</div>';
            }).catch(function () { cloudOff = true; applyCategoryFilter(); });
        return;
    }
    if (!searchIndex.length && typeof ensureSearchIndex === 'function') {
        ensureSearchIndex().then(applyCategoryFilter);
        return;
    }
    feed.q = null;
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

    // Уже пришедшее рисуем сразу — пачка на экране не должна ждать сети.
    var slice = feed.items.slice(feed.shown, feed.shown + feed.batch);
    if (slice.length) {
        var html = '';
        slice.forEach(function (item) { html += cardHTML(item); });
        c.insertAdjacentHTML('beforeend', html);
        feed.shown += slice.length;
        initAllTooltips();
        initReveal();
        return;
    }
    // Кончилось — просим следующую страницу у облака. feed.q пуст на ленте по индексу
    // и на страницах, которые рисуют свои модули: там догружать нечего.
    if (!feed.q || !feed.more || feed.busy || cloudOff) return;
    feed.busy = true;
    feedFromCloud(feed.q, feed.page + 1).then(function (j) {
        feed.busy = false;
        feed.page += 1;
        feed.more = !!j.more;
        if (!j.items.length) return;
        feed.items = feed.items.concat(j.items);
        renderMoreFeed();
    }).catch(function () {
        // Отказ облака на середине ленты: дальше не дёргаем, уже показанное остаётся.
        feed.busy = false; feed.more = false; cloudOff = true;
    });
}

/* Открыть ленту запросом к облаку. Возвращает промис: вызывающий решает, что делать
   при отказе — на первой странице это откат к индексу, дальше просто конец списка. */
function openCloudFeed(query, head) {
    var c = document.getElementById('search-results');
    if (!c) return Promise.reject(0);
    // Ленту открывают из двух мест — начальная настройка и сборка переключателя
    // порядка. Оба срабатывают на первой отрисовке, и облако получало два одинаковых
    // запроса подряд. Повтор того же запроса, пока прежний в пути, пропускаем.
    var key = JSON.stringify(query) + '|' + effVersion() + '|' + lang;
    if (feed._key === key && feed._pending) return feed._pending;
    feed._key = key;
    feed._pending = _openCloudFeed(query, head, c);
    return feed._pending;
}

function _openCloudFeed(query, head, c) {
    /* Ждём ОБА ответа: карточки и справочник имён. Раньше ожидание индекса на 14.6 МБ
       заведомо перекрывало загрузку справочников, и гонки не было видно. Теперь
       карточки приходят за 20 КБ, имена за 56 КБ, и кто первый — как повезёт; пришли
       первыми карточки — в ленте стоит cosmic_rays вместо «космические лучи», а плашка
       помечена как «страницы нет», хотя страница есть.
       Запросы уходят одновременно, поэтому ждём не сумму, а максимум из двух. */
    return Promise.all([
        feedFromCloud(query, 0),
        (window.B42Refs || Promise.resolve(null)).catch(function () { return null; }),
        _conceptsNamesP,
    ]).then(function (both) {
        var j = both[0];
        feed.q = query; feed.page = 0; feed.more = !!j.more;
        feed.items = j.items; feed.shown = 0; feed.lastDay = null;
        feed.active = true; feed.total = (typeof j.total === 'number') ? j.total : null;
        c.innerHTML = (head ? head(feed.total) : '') +
            (j.items.length ? '' :
             '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>');
        renderMoreFeed();
        updateSearchRowVisibility();
        return j;
    });
}
window.openCloudFeed = openCloudFeed;

window.addEventListener('scroll', function() {
    if (!feed.active) return;
    // Кончился массив — это конец ленты только для индекса. Для облака это повод
    // спросить следующую страницу, поэтому условие теперь учитывает feed.more.
    var hasLocal = feed.shown < feed.items.length;
    var hasCloud = feed.q && feed.more && !feed.busy && !cloudOff;
    if (!hasLocal && !hasCloud) return;
    if (window.scrollY + window.innerHeight > document.body.scrollHeight - 500) renderMoreFeed();
});

var tooltipHideTimer = null;

/* Ставит подсказку рядом с плашкой, не давая ей уехать за экран.
   Раньше здесь стояло `left = Math.min(rect.left, innerWidth - 330)` и `top = rect.bottom + 6`.
   Обе половины врали (аудит 2026-07-30):
     · 330 — ширина, которой у карточки нет (max-width 280px), а нижнего предела не было
       вовсе: у плашки в начале строки на 320px получалось left: -10px;
     · по вертикали ограничения не было совсем, и у плашки внизу длинного текста
       подсказка уходила ниже экрана — а она position: fixed, доскроллить до неё нельзя.
   Меряем факт, а не константу, и при нехватке места снизу переворачиваем вверх.
   Порядок важен: сначала сбрасываем left в край, иначе shrink-to-fit посчитает
   ширину для прошлого, уже прижатого положения. */
function placeTip(tip, rect) {
    var M = 8;
    tip.style.left = M + 'px';
    tip.style.top = '0px';
    var w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.max(M, Math.min(rect.left, window.innerWidth - w - M)) + 'px';
    var below = rect.bottom + 6;
    tip.style.top = (below + h + M > window.innerHeight
        ? Math.max(M, rect.top - h - 6)
        : below) + 'px';
}

/* Обрезка описаний в подсказках. Раньше в двух местах стояло substring(0, 200) + '...',
   то есть многоточие лепилось ВСЕГДА — даже к описанию в полторы строки, которое влезло
   целиком. Оборванная на полуслове фраза выталкивает читателя на страницу, то есть
   работает ровно против подсказки. Режем по границе слова и только при превышении. */
function tipCut(text, limit) {
    var t = (text || '').trim();
    var n = limit || 200;
    if (t.length <= n) return t;
    var cut = t.slice(0, n);
    var sp = cut.lastIndexOf(' ');
    return (sp > n * 0.6 ? cut.slice(0, sp) : cut).replace(/[.,;:\s]+$/, '') + '…';
}

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
    // Крестик: на мобиле нет mouseleave, и подсказка «залипала» намертво (юзер 2026-07-25).
    var x = document.createElement('button');
    x.type = 'button'; x.className = 'tip-close'; x.setAttribute('aria-label', 'Close');
    x.textContent = '×';
    x.addEventListener('click', function (e) { e.stopPropagation(); tip.style.display = 'none'; });
    tip.appendChild(x);
    // Тап/клик вне подсказки — тоже закрывает.
    document.addEventListener('click', function (e) {
        if (tip.style.display !== 'none' && !tip.contains(e.target) && !e.target.closest('[data-tag],[data-author],[data-scientist],[data-law],.express-badge,.card-express-badge,.refine-badge')) {
            tip.style.display = 'none';
        }
    });
    return tip;
}

function scheduleHideTooltip() {
    window.__tipFor = null;
    if (tooltipHideTimer) clearTimeout(tooltipHideTimer);
    tooltipHideTimer = setTimeout(function() {
        var tip = document.getElementById('entity-tooltip');
        if (tip) tip.style.display = 'none';
    }, 300);
}

// Описание тега/закона под ТЕКУЩУЮ выбранную версию (popular/simple/advanced) — раньше тултипы
// всегда показывали advanced-уровень (тег) или popular (закон) независимо от переключателя.
/* Описания подсказок — ОТДЕЛЬНЫМ файлом и по требованию.

   Раньше они лежали в тех же справочниках: три описания на запись (простое,
   популярное, подробное) при одном показываемом. 357 КБ приезжали к каждому
   читателю, включая тех, кто ни на что не навёл.

   Теперь: первое наведение заказывает файл своего уровня, дальше всё мгновенно.
   Уровней три, но читатель за сеанс обычно держится одного — заказывается один. */
var _tips = {};          // уровень → {id: описание}
var _tipsWait = {};

function ensureTips(kind) {
    var v = effVersion();
    var key = kind + ':' + v;
    if (_tips[key]) return Promise.resolve(_tips[key]);
    if (_tipsWait[key]) return _tipsWait[key];
    _tipsWait[key] = fetch('/lang/' + lang + '/data/' + kind + '-tips-' + v + '.json')
        .then(function (r) { if (!r.ok) throw 0; return r.json(); })
        .then(function (m) { _tips[key] = m || {}; return _tips[key]; })
        .catch(function () { _tips[key] = {}; return _tips[key]; });
    return _tipsWait[key];
}
window.ensureTips = ensureTips;

/* Описание сущности под текущий уровень чтения. Порядок источников: уже приехавшие
   подсказки → поля самой записи (полные справочники на страницах тега и закона всё
   ещё их содержат) → пусто. */
function descByVersion(obj, kind, id) {
    var v = effVersion();
    if (kind && id) {
        var m = _tips[kind + ':' + v];
        if (m && m[id]) return m[id];
    }
    if (!obj) return '';
    if (v === 'advanced') return obj.description || obj.description_simple || obj.description_popular || '';
    if (v === 'simple') return obj.description_simple || obj.description_popular || obj.description || '';
    return obj.description_popular || obj.description_simple || obj.description || '';
}

function initAllTooltips() {
    // Тач-паттерн (решение владельца 2026-07-30): тап по плашке НЕ переходит сразу,
    // а открывает тултип, и уже В НЁМ два действия — «подробнее» (переход на карточку)
    // и «закрыть» (крестик; тап мимо тоже закрывает — оба уже были). Раньше поведение
    // было случайным: mouseenter эмулировался тапом, переход происходил со второго тапа
    // без всякого объяснения читателю.
    var TOUCH = window.matchMedia && window.matchMedia('(hover: none)').matches;
    // Бейджи «экспресс» и «✦ отшлифовано» тоже объясняются подсказкой. Раньше объяснение
    // жило ТОЛЬКО в нативном title, а он на тач-устройствах не показывается вовсе —
    // то есть на телефоне слово «экспресс» не объяснялось ничем (владелец 2026-07-31).
    // Бейдж это span вне ссылки, поэтому перехват клика ему безопасен, в отличие от
    // чипов-фильтров, на которых мы уже обжигались.
    document.querySelectorAll('[data-tag], [data-scientist], [data-law], [data-author], [data-cat-desc], .express-badge, .card-express-badge, .refine-badge').forEach(function(el) {
        if (el.dataset.tooltipInit) return;
        el.dataset.tooltipInit = '1';

        if (TOUCH) {
            // У авторов тултип не нужен (владелец): обычная ссылка, один тап — переход.
            if (el.dataset.author) return;
            // РАЗДЕЛЫ. Тап по чипу раздела — это ФИЛЬТР, а не подсказка. Обработчик ниже
            // гасит клик на фазе погружения (stopImmediatePropagation), и до фильтра
            // (bar.onclick, filterByCategory) он не доходил вовсе: на телефоне раздел
            // нажимался и ничего не происходило (владелец 2026-08-18: «нажал раздел,
            // фильтр не сработал»). На десктопе баг невидим — там подсказка по наведению,
            // а клик уходит фильтру. Описание раздела на телефоне даём долгим нажатием.
            if (el.classList && (el.classList.contains('cat-chip') ||
                                 el.classList.contains('card-cat') ||
                                 el.classList.contains('cat-badge'))) {
                var lpTimer = null, lpFired = false;
                el.addEventListener('touchstart', function () {
                    lpFired = false;
                    lpTimer = setTimeout(function () { lpFired = true; showTipFor(el); }, 500);
                }, { passive: true });
                ['touchend', 'touchmove', 'touchcancel'].forEach(function (ev) {
                    el.addEventListener(ev, function () {
                        if (lpTimer) { clearTimeout(lpTimer); lpTimer = null; }
                    }, { passive: true });
                });
                // После долгого нажатия показали описание — обычный клик тогда не нужен,
                // иначе следом сработает и фильтр, и читатель получит два действия за один тап.
                el.addEventListener('click', function (e) {
                    if (lpFired) { e.preventDefault(); e.stopPropagation(); lpFired = false; }
                }, true);
                return;
            }
            // capture=true обязателен: у тегов В ТЕКСТЕ статьи висит собственный
            // onclick="window.location=..." прямо в разметке генератора, и без перехвата
            // на фазе погружения наш обработчик приходил вторым — тап давал «подсветку
            // и ничего» (владелец, 2026-07-30, живой телефон).
            el.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                showTipFor(el);
            }, true);
            return;
        }
        el.addEventListener('mouseenter', function(e) { showTipFor(el); });
        el.addEventListener('mouseleave', scheduleHideTooltip);
    });

    function showTipFor(el) {
            if (tooltipHideTimer) { clearTimeout(tooltipHideTimer); tooltipHideTimer = null; }
            /* Описания лежат отдельным файлом и приезжают по первому наведению (ensureTips).
               Ждать их здесь нельзя: подсказка, появляющаяся через полсекунды, — не
               подсказка. Поэтому рисуем немедленно тем, что есть (имя всегда под рукой),
               а когда файл приедет — повторяем показ, но ТОЛЬКО если курсор всё ещё на
               той же плашке. Иначе читатель увидит, как подсказка оживает после того,
               как он ушёл. Второе наведение и все следующие мгновенны. */
            var _k = el.dataset.tag ? 'tags'
                   : (el.dataset.law ? 'laws' : (el.dataset.scientist ? 'scientists' : null));
            if (_k && !_tips[_k + ':' + effVersion()]) {
                ensureTips(_k).then(function () {
                    if (window.__tipFor === el) showTipFor(el);
                });
            }
            window.__tipFor = el;
            var tip = getOrCreateTooltip();

            var content = '';
            var badge = el.classList && (el.classList.contains('express-badge')
                     || el.classList.contains('card-express-badge')
                     || el.classList.contains('refine-badge'));
            if (badge) {
                // Тексты давно переведены на шесть языков (UI_STRINGS) и до сих пор
                // только переписывались в атрибут title — теперь показываем их сами.
                content = '<strong>' + (el.textContent || '').trim() + '</strong> <span class="tip-desc">'
                        + (el.classList.contains('refine-badge') ? UI.refineTip : UI.expressTip) + '</span>';
            } else if (el.dataset.tag) {
                var t = tagsLoc[el.dataset.tag];
                content = t
                    ? '<strong>' + t.name + '</strong> &mdash; <span class="tip-desc">' + tipCut(descByVersion(t, 'tags', el.dataset.tag)) + '</span> <a href="/lang/' + lang + '/tags/' + encodeURIComponent(el.dataset.tag) + '.html">' + UI.more + '</a>'
                    : '<strong>' + (el.textContent || el.dataset.tag) + '</strong> <a href="/lang/' + lang + '/tags/' + encodeURIComponent(el.dataset.tag) + '.html">' + UI.more + '</a>';
            } else if (el.dataset.scientist) {
                var s = scientistsData[el.dataset.scientist];
                content = s
                    ? '<strong>' + s.name + '</strong> (' + s.lifespan + ') &mdash; <span class="tip-desc">' + tipCut(descByVersion(s, 'scientists', el.dataset.scientist)) + '</span> <a href="/lang/' + lang + '/scientists/' + authorSlug(el.dataset.scientist) + '.html">' + UI.more + '</a>'
                    : '<strong>' + el.dataset.scientist + '</strong> <a href="/lang/' + lang + '/scientists/' + authorSlug(el.dataset.scientist) + '.html">' + UI.profile + '</a>';
            } else if (el.dataset.law) {
                var lw = lawsData[el.dataset.law];
                content = lw
                    ? '<strong>' + lw.name + '</strong>' + (lw.type ? ' &middot; ' + lw.type : '') + ' &mdash; <span class="tip-desc">' + tipCut(descByVersion(lw, 'laws', el.dataset.law)) + '</span> <a href="/lang/' + lang + '/laws/' + encodeURIComponent(el.dataset.law) + '.html">' + UI.more + '</a>'
                    : '<strong>' + (el.textContent || el.dataset.law) + '</strong> <a href="/lang/' + lang + '/laws/' + encodeURIComponent(el.dataset.law) + '.html">' + UI.more + '</a>';
            } else if (el.dataset.cat) {
                var cd = el.dataset.catDesc || '';
                content = '<strong>' + (ARXIV_CAT_NAMES[el.dataset.cat] || el.dataset.cat) + '</strong>'
                        + (cd ? ' &mdash; <span class="tip-desc">' + tipCut(cd) + '</span>' : '');
            } else if (el.dataset.author) {
                var a = authorsGraph[el.dataset.author];
                var count = a ? (a.article_count || (a.articles || []).length || 0) : 0;
                content = '<strong>' + el.dataset.author + '</strong> &mdash; <span class="tip-desc">' + count + ' ' + UI.articlesWord + '</span> <a href="/lang/' + 'en' + '/authors/' + authorSlug(el.dataset.author) + '.html">' + UI.profile + '</a>';
            }

            if (content) {
                // Действия — ВВЕРХУ тултипа (владелец: «чтобы палец не двигать»):
                // выносим ссылку «подробнее» из хвоста текста в шапку, рядом с крестиком.
                var mTop = content.match(/<a href="([^"]+)"[^>]*>([^<]*)<\/a>\s*$/);
                if (mTop) {
                    // Стрелку не дописываем: UI.more уже содержит её и на RTL она своя
                    // (было «Подробнее → →», на арабском «← →» — стрелки врозь).
                    content = '<div class="tip-top"><a class="tip-more" href="' + mTop[1] + '">' +
                              mTop[2] + '</a></div>' + content.replace(mTop[0], '');
                }
                // Крестик добавляется при создании тултипа, а этот innerHTML сносил всех
                // детей — на тач-устройстве закрыть было нечем, только тапом мимо
                // (найдено проверкой 2026-07-30). Восстанавливаем после каждой отрисовки.
                tip.innerHTML = content;
                if (!tip.querySelector('.tip-close')) {
                    var _x = document.createElement('button');
                    _x.type = 'button'; _x.className = 'tip-close';
                    _x.setAttribute('aria-label', 'close');
                    _x.textContent = '×';
                    _x.addEventListener('click', function (e) {
                        e.stopPropagation(); tip.style.display = 'none';
                    });
                    tip.appendChild(_x);
                }
                tip.style.display = 'block';
                placeTip(tip, el.getBoundingClientRect());
            }
    }
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
    if (expressBadge) {
        expressBadge.title = UI.expressTip;
        expressBadge.innerHTML = b42ic('bolt', 13, '⚡');
        expressBadge.appendChild(document.createTextNode(' ' + UI.express));
    }

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
    // Что уезжает в шторку. /theory/ убран — раздела больше нет; /learn.html не сворачиваем,
    // он остаётся иконкой в строке и места почти не занимает.
    var collapsiblePatterns = ['/tags/', '/laws/', '/scientists/', '/sections/', '/authors/', '/graph/'];
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
    // Толщину штриха держит --ico-stroke в стилях (на телефоне жирнее); здесь
    // то же значение запасным, чтобы иконка не тончала, если стиль не приехал.
    btn.innerHTML = '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>';
    btn.setAttribute('aria-label', 'Menu');
    var panel = document.createElement('div');
    panel.className = 'nav-more-panel';

    var hasActive = false;
    toCollapse.forEach(function(a) {
        if (a.classList.contains('active')) hasActive = true;
        panel.appendChild(a);  // appendChild ПЕРЕМЕЩАЕТ узел — из старого родителя убирается сам
    });
    if (hasActive) btn.classList.add('active');

    // Extras в ☰ по смыслу (юзер 2026-07-25: «map→analytics, пересортируй, about не в центре»):
    // сначала исследование (dashboard, analytics), «о проекте» — последним.
    // authors и graph добавлены сюда 2026-08-02 вместе с чисткой шапки: раньше они стояли
    // в шаблоне и попадали в шторку сворачиванием. Когда я убрал их из двенадцати шаблонов,
    // они исчезли из меню ЦЕЛИКОМ — разделы остались на сайте, но попасть в них стало
    // неоткуда. Урок: убирая элемент из разметки, проверь, не он ли был источником для кода,
    // который его же и перекладывает.
    [['/lang/' + lang + '/formulas/', 'formulas'],
     ['/lang/en/authors/', 'authors'], ['/lang/' + lang + '/graph/', 'graph'],
     ['/learn.html', 'learn'], ['/lang/' + lang + '/archive/', 'dashboard'], ['/lang/' + lang + '/analytics/', 'analytics'],
     // Авторские работы — ПОСЛЕДНИМ пунктом, намеренно (владелец 2026-08-06: «кнопочка
     // где-то в меню затеряется, не на виду, в общий список пока не включаем»). Раздел
     // существует и находится тем, кто ищет, но не спорит за внимание с основной лентой:
     // работа независимого автора и разбор статьи с arXiv — разные вещи, мешать их
     // в одном потоке рано.
     ['/lang/' + lang + '/community/', 'community']].forEach(function(e) {
        if (panel.querySelector('a[href="' + e[0] + '"]')) return;
        var a = document.createElement('a');
        a.href = e[0]; a.textContent = e[1];
        panel.appendChild(a);
    });

    // Гид — ПЕРВЫМ пунктом, а не последним (владелец 2026-08-06: «about во-первых в меню, его
    // на самый верх»). Прежний порядок «о проекте последним» был решением от 25 июля, когда
    // гид рассказывал только про устройство сайта; теперь это документация для читателя,
    // студента, учёного, автора и преподавателя — то, что человеку нужно раньше ленты.
    // insertBefore, а не appendChild: панель уже содержит свёрнутые из шапки разделы, и
    // добавление в конец положило бы гид под них.
    if (!panel.querySelector('a[href="/lang/' + lang + '/about.html"]')) {
        var ab = document.createElement('a');
        ab.href = '/lang/' + lang + '/about.html';
        ab.textContent = 'about';
        panel.insertBefore(ab, panel.firstChild);
    }

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
        if (!wrap.contains(e.target)) { wrap.classList.remove('open'); return; }
        // На мобиле панель — шторка снизу, а затемнение это ::before САМОГО wrap: клик по нему
        // даёт e.target === wrap, и старая проверка считала его «кликом внутри» → не закрывалось.
        if (e.target === wrap) wrap.classList.remove('open');
    });
    // Escape закрывает шторку
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') wrap.classList.remove('open');
    });
}
document.addEventListener('DOMContentLoaded', collapseNavOverflow);

// ── Иконки шапки уезжают в шторку, когда строка перестаёт помещаться ─────────
// Сворачивание выше разбирается со СПИСКОМ пунктов — оно всегда прячет одни и те же
// разделы, независимо от ширины. Иконок это не касалось, и на 320 строка ломалась
// на два яруса: названию, меню и трём иконкам нужно около 330 пикселей при 288
// доступных. Уменьшать кнопки нельзя — 44 это порог касания, — поэтому лишние
// иконки уезжают туда же, куда давно уезжают лишние пункты.
// Решение принимается по факту переноса, а не по контрольной ширине: так оно верно и
// для длинных названий на других языках, где та же строка ломается раньше.
function fitHeaderCluster() {
    var bar = document.querySelector('.top-bar');
    var right = document.querySelector('.header-right');
    var panel = document.querySelector('.nav-more-panel');
    if (!bar || !right || !panel) return;

    // Когда все пункты уехали в шторку, обёртка остаётся в строке и всё равно съедает
    // просвет. CSS-правило :empty её не ловит: внутри остаётся пробельный узел, а для
    // :empty это уже «не пусто». Прячем по факту отсутствия ссылок.
    var navBox = right.querySelector('.nav-links');
    if (navBox) navBox.style.display = navBox.querySelector('a') ? '' : 'none';

    function wraps() {
        var kids = Array.prototype.filter.call(bar.children, function (el) {
            return el.getBoundingClientRect().width > 0;
        });
        if (kids.length < 2) return false;
        var tops = kids.map(function (el) { return Math.round(el.getBoundingClientRect().top); });
        return Math.max.apply(null, tops) - Math.min.apply(null, tops) > 6;
    }
    // Порядок вытеснения: сначала то, что реже нужно на ходу. Переключатель темы и поиск
    // не трогаем — ими пользуются с любой страницы.
    // Календаря здесь намеренно нет: он тянет за собой сетку месяцев шириной под 620,
    // и в шторке она растягивала список до 1256, возвращая прокрутку вбок. На самых узких
    // экранах он убран из шапки стилями — см. «Шапка на узком экране» в style.css.
    // :not(.nav-moved) обязательно — иначе на следующем витке цикл снова находит то,
    // что уже лежит в шторке (она сама внутри шапки), и перекладывает его по кругу.
    var order = ['.nav-links a[href*="/learn"]:not(.nav-moved)',
                 '.header-right a[href*="/favorites"]:not(.nav-moved)',
                 '.nav-links a.nav-ic:not(.nav-moved)'];

    var guard = 0;
    while (wraps() && guard++ < 5) {
        var el = null;
        for (var i = 0; i < order.length && !el; i++) el = bar.querySelector(order[i]);
        if (!el) break;
        // В шторке пункты подписаны словами, поэтому к иконке добавляем её подсказку —
        // иначе в списке окажется безымянный значок.
        var label = (el.getAttribute('title') || '').trim();
        if (label && !el.textContent.trim()) el.appendChild(document.createTextNode(' ' + label));
        el.classList.add('nav-moved');
        panel.appendChild(el);
    }

    // Переключатель уровней (страницы закона, тега, учёного) в шторку не годится: это
    // главный контрол страницы, а не редкая ссылка. Если строка всё ещё не помещается —
    // кладём его под шапку во всю ширину, ровно так он и живёт на статьях.
    if (wraps()) {
        var lv = bar.querySelector('.lv-switch:not(.lv-moved)');
        if (lv && bar.parentNode) {
            lv.classList.add('lv-moved');
            bar.parentNode.insertBefore(lv, bar.nextSibling);
        }
    }
}
// Считать приходится трижды, и это не перестраховка: на DOMContentLoaded заголовок ещё
// набран запасным шрифтом, его ширина отличается, и строка кажется помещающейся. Тот же
// приём уже используется для высоты липкой шапки ниже.
document.addEventListener('DOMContentLoaded', function () {
    fitHeaderCluster();
    setTimeout(fitHeaderCluster, 60);
});
window.addEventListener('load', fitHeaderCluster);
var _fitTimer = null;
window.addEventListener('resize', function () {
    clearTimeout(_fitTimer);
    _fitTimer = setTimeout(fitHeaderCluster, 180);
});

// Список разделов: группы раскрываемые — клик по строке-группе разворачивает её разделы
// (юзер 2026-07-24: «разделы нажимаем — они раскрываются»). По умолчанию всё свёрнуто.
document.addEventListener('click', function (e) {
    var g = e.target.closest ? e.target.closest('.section-group') : null;
    if (!g || !g.dataset || !g.dataset.group) return;
    var open = g.classList.toggle('open');
    var caret = g.querySelector('.sg-caret'); if (caret) caret.textContent = open ? '▾' : '▸';
    document.querySelectorAll('.sm-' + (window.CSS && CSS.escape ? CSS.escape(g.dataset.group) : g.dataset.group)).forEach(function (r) {
        r.hidden = !open;
    });
});

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
// Ярусов на самом деле ДВА: под шапкой на части страниц стоит своя липкая строка (языки —
// .langs / .langs-row), и всё, что липнет третьим (ряд уровней на статье, буква-разделитель
// на странице авторов), обязано вставать уже под ней. Обе эти вещи были прибиты к top: 0 и
// уезжали под непрозрачную шапку: буква на /authors/ не видна вовсе, переключатель уровней
// «прилипал» вслепую. Поэтому меряем стопку целиком и отдаём вторую переменную.
(function () {
    function syncStickTop() {
        var tb = document.querySelector('.top-bar');
        var h = tb ? Math.round(tb.getBoundingClientRect().height) : 0;
        document.documentElement.style.setProperty('--stick-top', h + 'px');

        var row = document.querySelector('.langs-row, .langs');
        // Только если строка реально липкая: на части страниц она обычная и ничего не занимает.
        var sticky = row && getComputedStyle(row).position === 'sticky';
        var h2 = sticky ? Math.round(row.getBoundingClientRect().height) : 0;
        document.documentElement.style.setProperty('--stick-top2', (h + h2) + 'px');
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
    btn.onclick = function(e) {
        // stopPropagation: иначе этот же клик всплывает до document-закрывашки ниже и панель
        // схлопывается в тот же тик — кнопка «переставала нажиматься» (юзер 2026-07-25).
        if (e) e.stopPropagation();
        var open = panel.classList.toggle('open');
        if (open) { var input = panel.querySelector('.search-box'); if (input) input.focus(); }
    };
    document.addEventListener('click', function(e) {
        // btn.contains(e.target), а не e.target !== btn: клик приходит по SVG-иконке ВНУТРИ кнопки,
        // и строгое сравнение считало его «кликом снаружи» → мгновенное закрытие.
        if (panel.classList.contains('open') && !panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.remove('open');
        }
    });
    // Esc: набранное остаётся (вдруг вернёшься), панель прячется. Заодно закрываем
    // соседей по паттерну «выпадашка от кнопки» — календарь и попап «i»: аналогичная
    // функциональность должна закрываться одинаково (владелец 2026-08-02).
    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        ['search-panel', 'calendar-panel', 'intro-popup'].forEach(function(id) {
            var p = document.getElementById(id);
            if (p) p.classList.remove('open');
        });
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
    btn.onclick = function(e) { if (e) e.stopPropagation(); panel.classList.toggle('open'); };
});

// ── Бегунок сложности (заменил кнопки-вкладки) ──────────────────────────────
// Всегда развёрнут целиком в шапке (без попапа). Один обработчик для ВСЕХ типов страниц.
// Точки внутри — либо <button data-version> (JS-переключение: главная/ленты/теги/законы/
// учёные), либо <a href data-version> (обычная навигация на странице статьи — работает
// без JS вообще). На тег/закон-страницах тот же клик ещё переключает видимые блоки
// .tag-ver — раньше это был отдельный дублированный инлайн-скрипт в каждом шаблоне.
// ── Уровень чтения: запоминание выбора ──────────────────────────────────────
// Бегунок убран (2026-07-28), управление перешло к иконочным кнопкам .lv-btn. Раньше вся
// логика висела на #version-toggle — после его удаления выбор уровня просто перестал
// сохраняться, и страницы открывались не тем уровнем, что читатель выбрал.
// На карточках и в статье кнопки — обычные ссылки: переход работает и без JS, а скрипт лишь
// запоминает выбранный уровень, чтобы следующая страница открылась в нём же.
document.addEventListener('DOMContentLoaded', function () {
    var btns = Array.prototype.slice.call(document.querySelectorAll('.lv-btn[data-version]'));
    if (!btns.length) return;

    // Страница статьи сама сообщает свой уровень активной кнопкой — записываем его,
    // иначе переход со статьи на тег/закон сбрасывал уровень на прошлый.
    var here = document.querySelector('.article-main .lv-btn.active[data-version]');
    if (here) {
        currentVersion = here.dataset.version;
        try { localStorage.setItem('b42_version', currentVersion); } catch (e) {}
    }

    // Текст тега/закона/учёного лежит на странице во всех версиях сразу (блоки .tag-ver),
    // видна одна. Кнопка без href — это переключатель такого текста: показываем нужный блок
    // и заодно перерисовываем список статей ниже, иначе он остаётся на прежнем уровне.
    var verBlocks = Array.prototype.slice.call(document.querySelectorAll('.tag-ver[data-ver]'));
    function showVer(v) {
        if (!verBlocks.length) return;
        var has = verBlocks.some(function (el) { return el.dataset.ver === v; });
        var use = has ? v : 'popular';
        verBlocks.forEach(function (el) { el.style.display = el.dataset.ver === use ? '' : 'none'; });
    }

    btns.forEach(function (b) {
        b.addEventListener('click', function () {
            var v = b.dataset.version;
            try { localStorage.setItem('b42_version', v); } catch (e) {}
            if (b.tagName === 'A') return;          // ссылка — переход сделает браузер
            currentVersion = v;
            showVer(v);
            btns.forEach(function (x) { x.classList.toggle('active', x.dataset.version === v); });
            var input = document.querySelector('.search-box');
            if (input && input.value.trim()) { doSearch(input.value); }
            else if (typeof _defaultFeed === 'function') { _defaultFeed(); }
        });
    });

    // начальное состояние текста карточки — под выбранный уровень
    if (verBlocks.length) showVer(currentVersion);

    // Подсветить выбранный уровень везде, где переключатель не привязан к открытому файлу.
    // Исключение — ряд внутри статьи: там активное состояние ставит сервер по тому, какая
    // версия открыта, и перекрашивать его нельзя.
    document.querySelectorAll('.lv-switch').forEach(function (sw) {
        if (sw.closest('.article-main')) return;
        sw.querySelectorAll('.lv-btn').forEach(function (b) {
            b.classList.toggle('active', b.dataset.version === currentVersion);
        });
    });
});

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

// Плавающая кнопка «наверх» — появляется после прокрутки (юзер 2026-07-25). Одна для всех страниц.
document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('to-top')) return;
    var b = document.createElement('button');
    b.type = 'button'; b.id = 'to-top'; b.setAttribute('aria-label', 'Top'); b.innerHTML = '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V6"/><path d="M6 12l6-6 6 6"/></svg>';
    b.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    document.body.appendChild(b);
    var tick = false;
    window.addEventListener('scroll', function () {
        if (tick) return;
        tick = true;
        requestAnimationFrame(function () {
            b.classList.toggle('show', window.scrollY > 500);
            tick = false;
        });
    }, { passive: true });
});

// ── Язык и уровень держатся ЕДИНЫМИ по всему сайту (юзер 2026-07-25: «не сбиваться при
// переходах, даже где не применимо»). Уровень уже живёт в localStorage b42_version; язык
// запоминаем здесь. Страницы авторов существуют только на en — чтобы переход туда не сбивал
// язык интерфейса, на них восстанавливаем сохранённый язык в ссылках шапки и в ленте.
(function () {
    var isAuthors = /\/authors\//.test(location.pathname);
    try {
        if (!isAuthors) localStorage.setItem('b42_lang', lang);
    } catch (e) {}
    if (!isAuthors) return;
    var saved = null;
    try { saved = localStorage.getItem('b42_lang'); } catch (e) {}
    if (!saved || saved === lang) return;
    document.addEventListener('DOMContentLoaded', function () {
        // ссылки шапки/логотипа — обратно на язык пользователя (кроме самих страниц авторов)
        document.querySelectorAll('a[href^="/lang/en/"]').forEach(function (a) {
            var h = a.getAttribute('href');
            if (/\/authors\//.test(h)) return;
            a.setAttribute('href', h.replace('/lang/en/', '/lang/' + saved + '/'));
        });
        // лента статей автора — на сохранённом языке
        if (typeof switchFeedLang === 'function') switchFeedLang(saved);
    });
})();

/* Свой счётчик посещений и нажатий (js/metrics.js) и отклик-искра (js/spark.js).
   Грузим отсюда, а не тегом в шаблоне: search.js подключён на всех собранных
   страницах, поэтому оба появляются БЕЗ пересборки сайта (правило владельца
   2026-07-31: «если можно оживить без регенерации — делай так»). Лениво и молча:
   упадёт загрузка — страница не заметит. */
(function () {
    function load(src) {
        var s = document.createElement('script');
        s.src = src; s.async = true; s.onerror = function () {};
        document.head.appendChild(s);
    }
    var go = function () { load('/js/metrics.js'); load('/js/spark.js'); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go);
    else go();
})();
