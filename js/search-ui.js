/* Выдача единого поиска: группы по видам + переключатель «по словам | по смыслу».
 *
 * Движок (site-search.js) уже отвечает одинаково независимо от источника; здесь только
 * отрисовка. Блок встаёт НАД существующим списком статей и не отменяет его: в режиме
 * «по словам» статьи по-прежнему показывает лента (search.js), а этот блок добавляет то,
 * чего в ней никогда не было, — понятия, законы, учёных и разделы. В режиме «по смыслу»
 * статьи приходят из /api/search, и тогда старый список прячется, чтобы не было двух
 * разных ответов на один запрос.
 *
 * Почему переключатель, а не «всегда по смыслу»: поиск по словам работает без сети и
 * мгновенно, а смысловой стоит запроса к модели и живёт только пока поднят Worker.
 * Читатель должен понимать, чем он сейчас ищет, — поэтому режим виден, а не угадывается.
 */
(function () {
    'use strict';

    var T = {
        ru: { concepts: 'Понятия', laws: 'Законы', people: 'Учёные', sections: 'Разделы',
              articles: 'Статьи', words: 'по словам', meaning: 'по смыслу',
              fellBack: 'смысловой поиск сейчас недоступен — ищем по словам',
              found: 'Найдено', nothing: 'Ничего не нашлось',
              tryOther: 'Попробуйте другое слово или посмотрите все понятия',
              allTags: 'все понятия', inSection: 'искать среди статей раздела',
              everywhere: 'искать по всему сайту →', artCount: 'ст.',
              searching: 'Ищем по смыслу' },
        en: { concepts: 'Concepts', laws: 'Laws', people: 'Scientists', sections: 'Sections',
              articles: 'Articles', words: 'by words', meaning: 'by meaning',
              fellBack: 'meaning search is unavailable right now — searching by words',
              found: 'Found', nothing: 'Nothing found',
              tryOther: 'Try another word or browse all concepts',
              allTags: 'all concepts', inSection: 'search within this section',
              everywhere: 'search the whole site →', artCount: 'art.',
              searching: 'Searching by meaning' },
        es: { concepts: 'Conceptos', laws: 'Leyes', people: 'Científicos', sections: 'Secciones',
              articles: 'Artículos', words: 'por palabras', meaning: 'por significado',
              fellBack: 'la búsqueda por significado no está disponible — buscamos por palabras',
              found: 'Encontrado', nothing: 'No se encontró nada',
              tryOther: 'Pruebe otra palabra o vea todos los conceptos',
              allTags: 'todos los conceptos', inSection: 'buscar en esta sección',
              everywhere: 'buscar en todo el sitio →', artCount: 'art.',
              searching: 'Buscando por significado' },
        ar: { concepts: 'المفاهيم', laws: 'القوانين', people: 'العلماء', sections: 'الأقسام',
              articles: 'المقالات', words: 'بالكلمات', meaning: 'بالمعنى',
              fellBack: 'البحث بالمعنى غير متاح الآن — نبحث بالكلمات',
              found: 'وُجد', nothing: 'لم يُعثر على شيء',
              tryOther: 'جرّب كلمة أخرى أو تصفّح كل المفاهيم',
              allTags: 'كل المفاهيم', inSection: 'البحث داخل هذا القسم',
              everywhere: 'البحث في الموقع كله ←', artCount: 'مقالة',
              searching: 'نبحث بالمعنى' },
        fr: { concepts: 'Notions', laws: 'Lois', people: 'Scientifiques', sections: 'Sections',
              articles: 'Articles', words: 'par mots', meaning: 'par sens',
              fellBack: 'la recherche par sens est indisponible — recherche par mots',
              found: 'Trouvé', nothing: 'Rien trouvé',
              tryOther: 'Essayez un autre mot ou parcourez toutes les notions',
              allTags: 'toutes les notions', inSection: 'chercher dans cette section',
              everywhere: 'chercher sur tout le site →', artCount: 'art.',
              searching: 'Recherche par sens' }
    };

    var GROUPS = [
        { key: 'tag', label: 'concepts' },
        { key: 'law', label: 'laws' },
        { key: 'sci', label: 'people' },
        { key: 'sec', label: 'sections' }
    ];

    var S = window.B42Search;
    if (!S) return;
    var L = T[S.lang] || T.en;
    var mode = 'words';
    try { mode = localStorage.getItem('b42_search_mode') || 'words'; } catch (e) {}

    function esc(s) {
        return (s == null ? '' : String(s))
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /* Счётчик статей печатаем только когда он есть И не нулевой: у статей поля `c` нет
       вовсе (напечатали бы «undefined»), а «0 статей» у понятия — обещание пустоты,
       по которому читателю незачем кликать. Обе половины — возврат QA. */
    function countHtml(row) {
        if (typeof row.c !== 'number' || row.c <= 0) return '';
        return '<span class="ss-count">' + row.c + ' ' + esc(L.artCount) + '</span>';
    }

    function rowHtml(row) {
        var name = row.nl || row.n;            // у учёных — имя на языке страницы
        var sub = row.s ? '<span class="ss-sub">' + esc(row.s) + '</span>' : '';
        return '<a class="ss-item" href="' + esc(row.url) + '">' +
               '<span class="ss-name">' + esc(name) + '</span>' + sub + countHtml(row) + '</a>';
    }

    function box() {
        var el = document.getElementById('site-search-results');
        if (el) return el;
        el = document.createElement('div');
        el.id = 'site-search-results';
        el.className = 'ss-box';
        var anchor = document.getElementById('search-results');
        if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(el, anchor);
        else document.body.appendChild(el);
        return el;
    }

    function legacyList(show) {
        var el = document.getElementById('search-results');
        if (el) el.style.display = show ? '' : 'none';
        var title = document.getElementById('article-list');
        if (title) title.style.display = show ? '' : 'none';
    }

    /* Контекст страницы: на теге, законе, учёном, разделе поиск сначала ищет ВНУТРИ —
       читатель пришёл за содержимым раздела. Список id берём из уже отрисованных карточек:
       страница знает свой состав, а движку остаётся только сузить. */
    function scope() {
        var host = document.getElementById('search-results');
        if (!host || !host.dataset) return null;
        var d = host.dataset;
        if (!(d.contextTag || d.contextLaw || d.contextScientist || d.contextCategory || d.contextAuthor)) {
            return null;
        }
        var ids = Array.prototype.map.call(
            host.querySelectorAll('[data-article-id], .article-card[data-id]'),
            function (n) { return n.dataset.articleId || n.dataset.id; }
        ).filter(Boolean);
        return ids.length ? { ids: ids } : null;
    }

    var scoped = null, scopeReady = false;

    function render(res, usedScope) {
        var el = box();
        if (!res.q) { el.innerHTML = ''; legacyList(true); return; }

        var parts = [], counts = [];
        GROUPS.forEach(function (g) {
            var rows = res.groups[g.key] || [];
            if (!rows.length) return;
            // «Законы 3», а не «3 законы»: числительное согласуется по-разному в каждом
            // из пяти языков, и подпирать это правилами ради строки-сводки не стоит —
            // порядок «что : сколько» одинаково верен везде.
            counts.push(esc(L[g.label]) + ' ' + rows.length);
            parts.push('<div class="ss-group"><div class="ss-h">' + esc(L[g.label]) + '</div>' +
                       rows.map(rowHtml).join('') + '</div>');
        });

        var head = '<div class="ss-top">' +
            '<div class="ss-modes" role="group">' +
            '<button type="button" class="ss-mode' + (mode === 'words' ? ' on' : '') + '" data-mode="words">' + esc(L.words) + '</button>' +
            '<button type="button" class="ss-mode' + (mode === 'meaning' ? ' on' : '') + '" data-mode="meaning">' + esc(L.meaning) + '</button>' +
            '</div>' +
            (counts.length ? '<div class="ss-found">' + esc(L.found) + ': ' + counts.join(' · ') + '</div>' : '') +
            // Читатель нажал «по смыслу», а Worker не ответил — сказать об этом прямо.
            // Молчаливый откат выглядел бы как «смысловой поиск такой же, как обычный»,
            // и мы бы получили жалобу не на недоступность, а на бесполезность режима.
            (mode === 'meaning' && res.source !== 'vector'
                ? '<div class="ss-note">' + esc(L.fellBack) + '</div>' : '') +
            '</div>';

        var tail = '';
        if (usedScope) {
            tail = '<a class="ss-all" href="#" data-all="1">' + esc(L.everywhere) + '</a>';
        }

        if (!parts.length && !(res.groups.art || []).length) {
            var tagsUrl = '/lang/' + S.lang + '/tags/';
            parts.push('<div class="ss-empty">' + esc(L.nothing) + '. ' + esc(L.tryOther) +
                       ' — <a href="' + tagsUrl + '">' + esc(L.allTags) + '</a></div>');
        }

        var artHtml = '';
        if (mode === 'meaning') {
            var arts = res.groups.art || [];
            artHtml = '<div class="ss-group"><div class="ss-h">' + esc(L.articles) + '</div>' +
                arts.map(function (a) {
                    return '<a class="ss-item" href="' + esc(a.url) + '">' +
                           '<span class="ss-name">' + esc(a.n) + '</span>' +
                           (a.d ? '<span class="ss-sub">' + esc(a.d) + '</span>' : '') + '</a>';
                }).join('') + '</div>';
        }

        el.innerHTML = head + parts.join('') + artHtml + tail;
        legacyList(mode !== 'meaning');
    }

    var lastQuery = '';

    function run(query, ignoreScope) {
        lastQuery = query;
        if (!scopeReady) { scoped = scope(); scopeReady = true; }
        var useScope = ignoreScope ? null : scoped;
        // Одна-две буквы смыслом не обладают, а сетевой запрос стоит единицу нормы —
        // короткий ввод ищем локально даже в смысловом режиме.
        var vector = mode === 'meaning' && query.length >= 3;
        var p = S.search(query, {
            source: vector ? 'vector' : 'local',
            scope: useScope
        });

        /* Поиск по смыслу с холодным индексом отвечает несколько секунд — вместо пустого
           места показываем факт или мини-опрос из наших же статей (B42Waiting). Порог
           в 700 мс: локальный поиск и повторный запрос из кэша укладываются быстрее и
           карточкой не мигают. По словам ищем без сети — там ждать нечего. */
        if (vector && window.B42Waiting) {
            p = window.B42Waiting.inline(box(), { promise: p, delay: 700, title: L.searching });
        }

        p.then(function (res) {
            if (query !== lastQuery) return;       // пришёл ответ на устаревший ввод
            render(res, !!useScope);
        });
    }

    /* Дебаунс: раньше каждый символ звал run(), и в смысловом режиме 11 букв означали
       11 сетевых запросов к /api/search — анонимная норма (3/сутки) сгорала на третьей
       букве, а карточки ожидания копились стопкой (блокер QA 2026-07-31). Пишущему
       человеку 350 мс незаметны; сети достаётся один запрос на паузу в наборе. */
    var _inputTimer = null;
    document.addEventListener('input', function (e) {
        var t = e.target;
        if (!t || !t.classList || !t.classList.contains('search-box')) return;
        var q = t.value.trim();
        lastQuery = q;                        // ответы на устаревший ввод отсекутся сразу
        if (_inputTimer) clearTimeout(_inputTimer);
        _inputTimer = setTimeout(function () { run(q, false); }, 350);
    });

    document.addEventListener('click', function (e) {
        var m = e.target.closest && e.target.closest('.ss-mode');
        if (m) {
            mode = m.dataset.mode;
            try { localStorage.setItem('b42_search_mode', mode); } catch (err) {}
            run(lastQuery, false);
            return;
        }
        var all = e.target.closest && e.target.closest('[data-all]');
        if (all) { e.preventDefault(); run(lastQuery, true); }
    });

    /* Подпись поля объясняет, где именно ищем: безликое «Поиск…» на странице закона и
       было причиной жалобы — читатель ждал поиска внутри закона, получал весь сайт. */
    function labelField() {
        if (!scopeReady) { scoped = scope(); scopeReady = true; }
        if (!scoped) return;
        Array.prototype.forEach.call(document.querySelectorAll('.search-box'), function (input) {
            input.placeholder = L.inSection;
        });
    }

    // Скрипт грузится с конца body, но на части страниц карточки статей дорисовывает лента,
    // поэтому ждём готовности документа, а если он уже готов — не ждём ничего.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', labelField);
    } else {
        labelField();
    }
})();
