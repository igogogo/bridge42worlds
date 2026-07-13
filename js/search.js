let searchIndex = [];
let tagsLoc = {};
let scientistsData = {};
let lawsData = {};
let authorsGraph = {};
// Уровни сложности: popular (по умолчанию) → simple → advanced.
var VERSION_INDEX_FILES = { popular: 'articles-index.json', simple: 'articles-index-simple.json',
                            advanced: 'articles-index-advanced.json' };
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
          articlesWord: 'статей', noResults: 'Ничего не найдено', more: 'Подробнее →', profile: 'Профиль →', moreWord: 'ещё', min: 'мин' },
    en: { tagNotFound: 'Tag not found', selectTag: 'Select a tag:', scientistNotFound: 'Scientist not found',
          selectScientist: 'Select a scientist:', authorNotFound: 'Author not found', selectAuthor: 'Select an author:',
          articlesWord: 'articles', noResults: 'Nothing found', more: 'More →', profile: 'Profile →', moreWord: 'more', min: 'min' },
    es: { tagNotFound: 'Etiqueta no encontrada', selectTag: 'Elige una etiqueta:', scientistNotFound: 'Científico no encontrado',
          selectScientist: 'Elige un científico:', authorNotFound: 'Autor no encontrado', selectAuthor: 'Elige un autor:',
          articlesWord: 'artículos', noResults: 'Nada encontrado', more: 'Más →', profile: 'Perfil →', moreWord: 'más', min: 'min' },
    zh: { tagNotFound: '未找到标签', selectTag: '选择标签：', scientistNotFound: '未找到科学家',
          selectScientist: '选择科学家：', authorNotFound: '未找到作者', selectAuthor: '选择作者：',
          articlesWord: '篇文章', noResults: '未找到结果', more: '详情 →', profile: '主页 →', moreWord: '更多', min: '分钟' },
    fr: { tagNotFound: 'Tag introuvable', selectTag: 'Choisir un tag :', scientistNotFound: 'Scientifique introuvable',
          selectScientist: 'Choisir un scientifique :', authorNotFound: 'Auteur introuvable', selectAuthor: 'Choisir un auteur :',
          articlesWord: 'articles', noResults: 'Aucun résultat', more: 'En savoir plus →', profile: 'Profil →', moreWord: 'autres', min: 'min' },
    ar: { tagNotFound: 'الوسم غير موجود', selectTag: 'اختر وسمًا:', scientistNotFound: 'العالم غير موجود',
          selectScientist: 'اختر عالمًا:', authorNotFound: 'المؤلف غير موجود', selectAuthor: 'اختر مؤلفًا:',
          articlesWord: 'مقالات', noResults: 'لا نتائج', more: 'المزيد ←', profile: 'الملف ←', moreWord: 'آخرون', min: 'دقيقة' }
};
var UI = UI_STRINGS[lang] || UI_STRINGS.en;

var ARXIV_CAT_NAMES = {
    'astro-ph.CO':'Cosmology','astro-ph.EP':'Exoplanets','astro-ph.GA':'Galaxies',
    'astro-ph.HE':'High Energy','astro-ph.IM':'Instrumentation','astro-ph.SR':'Stellar',
    'gr-qc':'General Relativity','hep-ex':'HEP Experiment','hep-ph':'HEP Phenomenology',
    'hep-th':'HEP Theory','hep-lat':'HEP Lattice','math-ph':'Math Physics',
    'nucl-ex':'Nuclear Exp','nucl-th':'Nuclear Theory','quant-ph':'Quantum Physics',
    'cond-mat':'Condensed Matter','cond-mat.mes-hall':'Mesoscale','cond-mat.mtrl-sci':'Materials',
    'cond-mat.stat-mech':'Statistical Mech','cond-mat.str-el':'Strongly Correlated',
    'cond-mat.supr-con':'Superconductivity','physics.space-ph':'Space Physics',
    'physics.geo-ph':'Geophysics','physics.plasm-ph':'Plasma Physics','physics.optics':'Optics',
    'physics.atom-ph':'Atomic Physics','physics.flu-dyn':'Fluid Dynamics',
    'cs.LG':'Machine Learning','cs.AI':'Artificial Intelligence','cs.CV':'Computer Vision',
    'cs.NE':'Neural Computing','stat.ML':'Statistical ML','eess.SP':'Signal Processing','eess.IV':'Image Processing'
};

var resultsEl = document.getElementById('search-results');
// Тег-страница передаёт один id, страница закона — ВСЕ свои теги через запятую (закон
// показывает статьи, у которых есть ХОТЯ БЫ ОДИН из его тегов — раньше здесь бралась только
// первая точка, из-за чего «Статьи по теме» у закона могли уйти в пустоту, если первый по
// алфавиту тег закона случайно оказывался образовательным и ни разу не встречался в статьях).
var pageContext = {
    tags: resultsEl && resultsEl.dataset.contextTag ? resultsEl.dataset.contextTag.split(',').filter(Boolean) : [],
    scientist: resultsEl ? (resultsEl.dataset.contextScientist || '') : '',
    author: resultsEl ? (resultsEl.dataset.contextAuthor || '') : ''
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
    return results;
}

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

Promise.all([
    fetchIndex('popular'),
    fetchIndex('simple'),
    fetchIndex('advanced'),
    fetch('/data/authors-graph.json').then(function(r) { return r.json(); }).catch(function() { return {}; }),
    fetch(tagsPath).then(function(r) { return r.json(); }).catch(function() {
        return fetch('/lang/' + defaultLang + '/data/tags.json').then(function(r) { return r.json(); });
    }),
    fetch(scientistsPath).then(function(r) { return r.json(); }).catch(function() {
        return fetch('/lang/' + defaultLang + '/data/scientists.json').then(function(r) { return r.json(); });
    }),
    fetch('/lang/' + lang + '/data/laws.json').then(function(r) { return r.json(); }).catch(function() { return {}; })
]).then(function(results) {
    searchIndex = results[0].concat(results[1]).concat(results[2]);
    authorsGraph = results[3];
    tagsLoc = results[4];
    scientistsData = results[5];
    lawsData = results[6] || {};

    window.searchIndex = searchIndex;
    window.tagsLoc = tagsLoc;
    window.scientistsData = scientistsData;
    window.lawsData = lawsData;
    window.authorsGraph = authorsGraph;

    var container = document.getElementById('search-results');
    if (container && !document.querySelector('.search-box')?.value) {
        _defaultFeed();
    }
    if (window.__favoritesPage) {
        ['calendar-btn', 'calendar-panel', 'category-bar'].forEach(function(id) { var e = document.getElementById(id); if (e) e.style.display = 'none'; });
    } else {
        initCalendar();
        initCategoryBar();
    }
    initAllTooltips();
    renderSiteStats();
}).catch(function(e) {
    console.error('Init error:', e);
});

var STATS_LABELS = {
    ru: ['статей', 'авторов', 'учёных'], en: ['articles', 'authors', 'scientists'],
    zh: ['篇文章', '位作者', '位科学家'], fr: ['articles', 'auteurs', 'scientifiques'],
    ar: ['مقالات', 'مؤلفين', 'علماء']
};
function renderSiteStats() {
    var el = document.getElementById('site-stats');
    if (!el) return;
    var L = STATS_LABELS[lang] || STATS_LABELS.en;
    var uniq = {};
    searchIndex.forEach(function(a){ uniq[a.id] = 1; });
    var nA = Object.keys(uniq).length, nAu = Object.keys(authorsGraph || {}).length, nS = Object.keys(scientistsData || {}).length;
    el.innerHTML = '<b>' + nA + '</b> ' + L[0] + ' · <b>' + nAu + '</b> ' + L[1] + ' · <b>' + nS + '</b> ' + L[2];
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

function doFullSearch(query) {
    var container = document.getElementById('search-results');
    renderActiveFilters(query);
    var filters = parseSearchQuery(query);
    var results = searchIndex.filter(function(item) {
        return item.version === effVersion();
    });
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
    // Авторы: до 3 в мете, приглушённо (полный список — на странице статьи)
    var au = item.authors || [];
    var authorsHtml = au.slice(0, 3).map(function(a) {
        return '<a href="/lang/' + lang + '/authors/' + authorSlug(a) + '.html" data-author="' + a + '">' + a + '</a>';
    }).join(', ') + (au.length > 3 ? ' <span class="au-more-lite">+' + (au.length - 3) + '</span>' : '');
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
    return '<article class="article-card">' +
        '<a class="card-img-wrap" href="' + url + '">' +
            '<img src="' + img + '" data-fb="' + imgFb + '" loading="lazy" onerror="if(this.dataset.fb){this.src=this.dataset.fb;this.removeAttribute(\'data-fb\');}else{this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';}" alt="">' +
            '<span class="no-img" style="display:none">📄</span>' +
        '</a>' +
        '<div class="card-body">' +
            (catName ? '<a class="card-cat" href="#" onclick="filterByCategory(\'' + cat + '\');return false;">' + catName + '</a>' : '') +
            '<a class="card-title" href="' + url + '">' + item.title + '</a>' +
            (bodyText ? '<div class="card-desc' + (isMini ? ' card-mini' : '') + '">' + bodyText + '</div>' : '') +
            '<div class="card-meta">' + authorsHtml + (item.reading ? '<span class="sep">·</span>⏱ ' + item.reading + ' ' + UI.min : '') + '<span class="sep">·</span>arXiv:' + item.id + '</div>' +
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
var isEntityPage = !!(pageContext.tag || pageContext.scientist || pageContext.author);
function updateSearchRowVisibility() {
    if (!isEntityPage) return;
    var row = document.querySelector('.search-row'), hint = document.querySelector('.search-hint');
    var show = feed.items.length > 0;
    if (row) row.style.display = show ? '' : 'none';
    if (hint) hint.style.display = show ? '' : 'none';
}

function showLatest() {
    feed.items = applyPageContext(searchIndex.filter(function(item) { return item.version === effVersion(); }))
        .sort(function(a, b) { return b.date.localeCompare(a.date); });
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
        return '<span class="cat-chip' + (selectedCats[c] ? ' active' : '') + '" data-cat="' + c + '">' +
            (ARXIV_CAT_NAMES[c] || c) + '<span class="cat-chip-n">' + counts[c] + '</span></span>';
    }).join('');
    bar.onclick = function(e) {
        var chip = e.target.closest ? e.target.closest('.cat-chip') : null;
        if (!chip) return;
        var c = chip.getAttribute('data-cat');
        if (selectedCats[c]) { delete selectedCats[c]; chip.classList.remove('active'); }
        else { selectedCats[c] = 1; chip.classList.add('active'); }
        applyCategoryFilter();
    };
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
    slice.forEach(function(item) {
        if (item.date !== feed.lastDay) { feed.lastDay = item.date; html += '<div class="feed-day">' + item.date + '</div>'; }
        html += cardHTML(item);
    });
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

    function paint(idx) {
        var pct = dots.length > 1 ? (idx / (dots.length - 1) * 100) : 0;
        if (fill) fill.style.width = pct + '%';
        if (thumb) thumb.style.left = pct + '%';
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
        // Ссылки — переход нативный (работает без JS). Тут только красим начальное состояние.
        var activeIdx = 0;
        dots.forEach(function(d, i) { if (d.classList.contains('active')) activeIdx = i; });
        paint(activeIdx);
        showTagVer(dots[activeIdx].dataset.version);
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
        function nearestIdx(pct) { return Math.round(pct * (dots.length - 1)); }
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