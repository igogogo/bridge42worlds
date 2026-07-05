let searchIndex = [];
let tagsLoc = {};
let scientistsData = {};
let authorsGraph = {};
// Уровни сложности: popular (по умолчанию) → simple → advanced.
var VERSION_INDEX_FILES = { popular: 'articles-index.json', simple: 'articles-index-simple.json',
                            advanced: 'articles-index-advanced.json' };
let currentVersion = (function() {
    try { return localStorage.getItem('b42_version') || 'popular'; } catch(e) { return 'popular'; }
})();

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
          articlesWord: 'статей', noResults: 'Ничего не найдено', more: 'Подробнее →', profile: 'Профиль →' },
    en: { tagNotFound: 'Tag not found', selectTag: 'Select a tag:', scientistNotFound: 'Scientist not found',
          selectScientist: 'Select a scientist:', authorNotFound: 'Author not found', selectAuthor: 'Select an author:',
          articlesWord: 'articles', noResults: 'Nothing found', more: 'More →', profile: 'Profile →' },
    zh: { tagNotFound: '未找到标签', selectTag: '选择标签：', scientistNotFound: '未找到科学家',
          selectScientist: '选择科学家：', authorNotFound: '未找到作者', selectAuthor: '选择作者：',
          articlesWord: '篇文章', noResults: '未找到结果', more: '详情 →', profile: '主页 →' },
    fr: { tagNotFound: 'Tag introuvable', selectTag: 'Choisir un tag :', scientistNotFound: 'Scientifique introuvable',
          selectScientist: 'Choisir un scientifique :', authorNotFound: 'Auteur introuvable', selectAuthor: 'Choisir un auteur :',
          articlesWord: 'articles', noResults: 'Aucun résultat', more: 'En savoir plus →', profile: 'Profil →' },
    ar: { tagNotFound: 'الوسم غير موجود', selectTag: 'اختر وسمًا:', scientistNotFound: 'العالم غير موجود',
          selectScientist: 'اختر عالمًا:', authorNotFound: 'المؤلف غير موجود', selectAuthor: 'اختر مؤلفًا:',
          articlesWord: 'مقالات', noResults: 'لا نتائج', more: 'المزيد ←', profile: 'الملف ←' }
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
var pageContext = {
    tag: resultsEl ? (resultsEl.dataset.contextTag || '') : '',
    scientist: resultsEl ? (resultsEl.dataset.contextScientist || '') : '',
    author: resultsEl ? (resultsEl.dataset.contextAuthor || '') : ''
};

function applyPageContext(results) {
    if (pageContext.tag) {
        results = results.filter(function(item) { return (item.tags || []).indexOf(pageContext.tag) !== -1; });
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
    })
]).then(function(results) {
    searchIndex = results[0].concat(results[1]).concat(results[2]);
    authorsGraph = results[3];
    tagsLoc = results[4];
    scientistsData = results[5];

    window.searchIndex = searchIndex;
    window.tagsLoc = tagsLoc;
    window.scientistsData = scientistsData;
    window.authorsGraph = authorsGraph;

    var container = document.getElementById('search-results');
    if (container && !document.querySelector('.search-box')?.value) {
        showLatest();
    }
    initCalendar();
    initCategoryBar();
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
        return item.version === currentVersion;
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
    container.querySelectorAll(':scope > a').forEach(function(el) {
        var text = el.textContent.toLowerCase();
        el.style.display = (!q || text.includes(q)) ? '' : 'none';
    });
}

function filterAuthors(query) { filterCloudItems('author-cloud', query); }
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
    var imgSrc = '/lang/' + defaultLang + '/archive/' + item.date + '/' + item.id + '/0.jpg';
    var authorsHtml = (item.authors || []).slice(0,4).map(function(a) {
        return '<a href="/lang/' + lang + '/authors/' + authorSlug(a) + '.html" class="text-author-link" data-author="' + a + '">' + a + '</a>';
    }).join(', ');
    if ((item.authors || []).length > 4) authorsHtml += ' +' + (item.authors.length - 4) + ' more';
    var tagsHtml = (item.tags || []).slice(0,6).map(function(t) {
        return '<a href="/lang/' + lang + '/tags/' + encodeURIComponent(t) + '.html" data-tag="' + t + '">' + (tagsLoc[t]?.name || t) + '</a>';
    }).join(' · ');
    var scientistsHtml = '';
    if ((item.scientists || []).length) {
        scientistsHtml = '<div class="card-scientists">' + item.scientists.slice(0,3).map(function(s) {
            return '<a href="/lang/' + lang + '/scientists/' + authorSlug(s) + '.html" class="text-scientist" data-scientist="' + s + '">' + s + '</a>';
        }).join(' · ') + '</div>';
    }
    return '<div class="article-card">' +
        '<div class="card-img"><img src="' + imgSrc + '" onerror="this.style.display=\'none\'" alt=""></div>' +
        '<div class="card-content">' +
        '<h3><a href="' + item.url + '">' + item.title + '</a></h3>' +
        '<div class="oneliner">' + (item.oneliner || item.description || '') + '</div>' +
        '<div class="meta">arXiv:' + item.id + ' · ' + item.date + (item.reading ? ' · ⏱ ' + item.reading : '') + ' · ' + authorsHtml + '</div>' +
        ((item.categories && item.categories.length) ? '<div class="card-cats">' + item.categories.slice(0,4).map(function(c) {
            return '<span class="cat-badge" data-cat="' + c + '" onclick="filterByCategory(\'' + c + '\')">' + (ARXIV_CAT_NAMES[c] || c) + '</span>';
        }).join('') + '</div>' : '') +
        '<div class="card-tags">' + tagsHtml + '</div>' +
        scientistsHtml +
        '</div></div>';
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

function showLatest() {
    feed.items = applyPageContext(searchIndex.filter(function(item) { return item.version === currentVersion; }))
        .sort(function(a, b) { return b.date.localeCompare(a.date); });
    feed.shown = 0; feed.lastDay = null; feed.active = true;
    var c = document.getElementById('search-results');
    if (c) c.innerHTML = feed.items.length ? '' : '<p style="color:var(--soft);text-align:center;padding:40px">' + UI.noResults + '</p>';
    renderMoreFeed();
}
window.showLatest = showLatest;

function filterByCategory(cat) {
    var items = applyPageContext(searchIndex.filter(function(item) {
        return item.version === currentVersion && (item.categories || []).indexOf(cat) !== -1;
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
        return item.version === currentVersion && (item.date || '').indexOf(prefix) === 0;
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
    btn.textContent = L.title;
    var tree = {};
    searchIndex.filter(function(i) { return i.version === currentVersion && i.date; }).forEach(function(i) {
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
    searchIndex.filter(function(i) { return i.version === currentVersion; }).forEach(function(i) {
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
        return item.version === currentVersion && (item.categories || []).some(function(c) { return selectedCats[c]; });
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

function initAllTooltips() {
    document.querySelectorAll('[data-tag], [data-scientist], [data-author]').forEach(function(el) {
        if (el.dataset.tooltipInit) return;
        el.dataset.tooltipInit = '1';

        el.addEventListener('mouseenter', function(e) {
            if (tooltipHideTimer) { clearTimeout(tooltipHideTimer); tooltipHideTimer = null; }
            var tip = getOrCreateTooltip();

            var content = '';
            if (el.dataset.tag) {
                var t = tagsLoc[el.dataset.tag];
                if (t) {
                    content = '<strong>' + t.name + '</strong><p>' + (t.description || '') + '</p><a href="/lang/' + lang + '/tags/' + encodeURIComponent(el.dataset.tag) + '.html">' + UI.more + '</a>';
                }
            } else if (el.dataset.scientist) {
                var s = scientistsData[el.dataset.scientist];
                if (s) {
                    content = '<strong>' + s.name + '</strong> (' + s.lifespan + ')<p>' + (s.description || '').substring(0, 200) + '...</p><a href="/lang/' + lang + '/scientists/' + authorSlug(el.dataset.scientist) + '.html">' + UI.more + '</a>';
                }
            } else if (el.dataset.author) {
                var a = authorsGraph[el.dataset.author];
                var count = a ? (a.article_count || (a.articles || []).length || 0) : 0;
                content = '<strong>' + el.dataset.author + '</strong><p>' + count + ' ' + UI.articlesWord + '</p><a href="/lang/' + lang + '/authors/' + authorSlug(el.dataset.author) + '.html">' + UI.profile + '</a>';
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

document.addEventListener('DOMContentLoaded', function() {
    var toggle = document.getElementById('version-toggle');
    if (toggle) {
        toggle.querySelectorAll('span').forEach(function(el) {
            el.classList.toggle('active', el.dataset.version === currentVersion);
            el.addEventListener('click', function() {
                toggle.querySelectorAll('span').forEach(function(s) { s.classList.remove('active'); });
                el.classList.add('active');
                currentVersion = el.dataset.version;
                try { localStorage.setItem('b42_version', currentVersion); } catch(e) {}
                var input = document.querySelector('.search-box');
                if (input && input.value.trim()) {
                    doSearch(input.value);
                } else {
                    showLatest();
                }
            });
        });
    }
});