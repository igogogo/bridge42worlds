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
        var INDEX_FILES = { popular: 'articles-index.json', simple: 'articles-index-simple.json',
                            advanced: 'articles-index-advanced.json', mini: 'articles-index.json' };
        var sameTier = typeof window.effVersion === 'function'
            && window.effVersion() === (version === 'mini' ? 'popular' : version);
        try {
            if (sameTier && typeof window.ensureSearchIndex === 'function') {
                articlesIndex = await window.ensureSearchIndex() || [];
            }
            if (!articlesIndex.length) {
                var resp = await fetch('/lang/' + lang + '/' + INDEX_FILES[version]);
                if (!resp.ok) return;
                articlesIndex = await resp.json();
            }
        } catch (e) {
            console.log('Scroll: no index yet');
            return;
        }
        updateNextButton(version);
        renderRelated(currentId, lang, version);
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
    // Похожие статьи — те же карточки-подложки с миниатюрой, что на страницах тега/закона/учёного
    // (юзер 2026-07-24: «related как в карточках тегов, на плашках с картинкой»).
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
