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
    ru: 'Больше нет статей', en: 'No more articles', zh: '没有更多文章了', fr: 'Plus d\'articles',
    ar: 'لا مزيد من المقالات'
};

async function initScroll() {
    var lang = getLang();
    var path = window.location.pathname;
    var version = path.indexOf('advanced.html') !== -1 ? 'advanced'
                : (path.indexOf('simple.html') !== -1 ? 'simple'
                : (path.indexOf('mini.html') !== -1 ? 'mini' : 'popular'));
    try { localStorage.setItem('b42_version', version); } catch(e) {}
    var INDEX_FILES = { popular: 'articles-index.json', simple: 'articles-index-simple.json',
                        advanced: 'articles-index-advanced.json', mini: 'articles-index.json' };
    var indexFile = INDEX_FILES[version];
    try {
        var resp = await fetch('/lang/' + lang + '/' + indexFile);
        if (!resp.ok) return;
        articlesIndex = await resp.json();
    } catch(e) {
        console.log('Scroll: no index yet');
        return;
    }

    var currentId = document.querySelector('[data-article-id]')?.dataset.articleId;
    // data-article-id теперь составной: id_lang_version. Выделяем чистый arXiv id.
    if (currentId) {
        var parts = currentId.split('_');
        // arXiv id имеет вид 2607.00565v1 (цифры.цифрыvцифры)
        if (parts.length >= 2 && /^\d{4}\.\d{4,5}v\d+/.test(parts[0])) {
            currentId = parts[0];
        }
        viewedIds.add(currentId);
        persistViewed();
    }

    updateNextButton(version);
    renderRelated(currentId, lang, version);
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

function renderRelated(currentId, lang, version) {
    var box = document.getElementById('related');
    if (!box) return;
    var curTags = Array.from(document.querySelectorAll('.side-tag')).map(function(e){ return e.dataset.tag || ''; });
    var scored = articlesIndex
        .filter(function(a){ return a.id !== currentId; })
        .map(function(a){ return { a: a, s: (a.tags||[]).filter(function(t){ return curTags.indexOf(t) !== -1; }).length }; })
        .filter(function(x){ return x.s > 0; })
        .sort(function(p,q){ return q.s - p.s || q.a.date.localeCompare(p.a.date); })
        .slice(0, 3);
    if (!scored.length) return;
    box.innerHTML = '<h3 class="related-h">' + (box.dataset.label || 'Related') + '</h3>' +
        scored.map(function(x){
            var ol = x.a.oneliner ? '<span class="related-oneliner">' + x.a.oneliner + '</span>' : '';
            return '<a href="' + urlForVersion(x.a.url, version) + '" class="related-item">' + x.a.title + ol + '</a>';
        }).join('');
}

function findNextArticle(currentTags, mainTag) {
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
        .sort(function(a, b) { return b.score - a.score || b.date.localeCompare(a.date); });
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

    btns.forEach(function(btn) {
        // Захватываем локализованный текст кнопки, отрендеренный сервером
        // ($next_label в article.html), до первой перезаписи — иначе он теряется.
        if (!btn.dataset.baseLabel) btn.dataset.baseLabel = btn.textContent.replace(/→\s*$/, '').trim();
        var label = btn.dataset.baseLabel;

        if (next) {
            btn.textContent = label + ': ' + next.title.substring(0, 30) + '... →';
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