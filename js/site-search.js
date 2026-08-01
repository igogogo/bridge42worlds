/* Единый поиск по сайту: один движок, два источника, один формат ответа.
 *
 * Зачем отдельный файл. Поиск в search.js умеет ровно одно — фильтровать ленту статей.
 * Читатель же чаще ищет понятие, а не статью: у нас 363 тега, 145 законов, 201 учёный,
 * и ни один из них в выдачу не попадал. Здесь поиск идёт по всем видам сразу и отвечает
 * группами, а не одним списком.
 *
 * СТЫК (ТЗ-ПОИСК, задачи/ПОИСК-КТО-ЧТО.md). Страница не должна знать, откуда пришли
 * результаты. Поэтому источник — сменная деталь: сейчас это лёгкий индекс рядом
 * (lang/<язык>/search-index.json), дальше появится /api/search у DevOps — он ищет по
 * смыслу, а не по словам. Формат ответа один и тот же, поэтому подключение вектора
 * не потребует трогать отрисовку:
 *
 *     { q, source, total, groups: { tag: [], law: [], sci: [], sec: [], art: [] } }
 *     запись группы: { t, id, n, url, c?, s?, score }
 *
 * У /api/search сегодня только статьи (он векторный, по корпусу статей), поэтому в
 * гибридном режиме понятия/законы/учёные всё равно берутся из локального индекса, а
 * статьи — из сети. Это осознанно: смысловой поиск по двум тысячам заголовков даёт
 * заметно больше, чем по названиям тегов, где совпадение слов и так работает.
 */
(function () {
    'use strict';

    var LANG = (function () {
        var m = location.pathname.match(/^\/lang\/([a-z]{2})\//);
        if (m) return m[1];
        var q = (location.search.match(/[?&]lang=([a-z]{2})/) || [])[1];
        return q || document.documentElement.lang || 'ru';
    })();

    var TYPES = ['tag', 'law', 'sci', 'sec', 'art'];
    var index = null, loading = null;

    function loadIndex() {
        if (index) return Promise.resolve(index);
        if (loading) return loading;
        loading = fetch('/lang/' + LANG + '/search-index.json')
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (rows) { index = rows || []; return index; })
            .catch(function () { index = []; return index; });
        return loading;
    }

    /* Имя файла учёного — ровно то же правило, что у генератора (author_slug в gen_base.py):
       пробел в подчёркивание, точка ВЫБРАСЫВАЕТСЯ, слэши и запрещённые в Windows символы — в
       дефис. Без выброшенной точки «Albert A. Michelson» уводил бы в 404, а файл называется
       Albert_A_Michelson.html. Правило продублировано осознанно: тянуть ради него ещё один
       файл в браузер дороже, чем повторить пять замен — но менять его надо в обоих местах. */
    function authorSlug(name) {
        return (name || '').replace(/ /g, '_').replace(/\./g, '')
            .replace(/[/\\]/g, '-').replace(/[:<>"|?*]/g, '-');
    }

    /* Адрес сущности собирается здесь, а не хранится в индексе: правило одно на весь сайт,
       а в файле это лишние сорок с лишним килобайт повторяющихся префиксов. */
    function urlFor(row) {
        var base = '/lang/' + LANG + '/';
        if (row.t === 'tag') return base + 'tags/' + row.id + '.html';
        if (row.t === 'law') return base + 'laws/' + row.id + '.html';
        if (row.t === 'sci') return base + 'scientists/' + authorSlug(row.id) + '.html';
        if (row.t === 'sec') return base + 'sections/' + row.id.replace(/[./]/g, '_') + '.html';
        if (row.t === 'art') return base + 'archive/' + (row.d || '') + '/' + row.id + '/index.html';
        return base;
    }

    function norm(s) { return (s || '').toString().toLowerCase().trim(); }

    /* Аббревиатура понятия из его латинского id: cosmic_microwave_background → CMB.
       Физик набирает «CMB», а не полное название, и получал ноль при существующем теге
       (нашёл QA). Считаем здесь, а не храним в индексе: id уже есть в каждой записи,
       поле стоило бы двенадцать килобайт на язык, а русский и так в 396 из 400.
       Латинский id один на все языки — поэтому «CMB» работает и на арабской странице. */
    var ID_STOPWORDS = { of: 1, the: 1, and: 1, 'in': 1, on: 1, 'for': 1, de: 1, la: 1, le: 1 };

    function abbrev(id) {
        var words = (id || '').split(/[_\-\s]+/).filter(function (w) {
            return w && !ID_STOPWORDS[w.toLowerCase()];
        });
        if (words.length < 2) return '';
        var ab = words.map(function (w) { return w.charAt(0); }).join('').toLowerCase();
        return ab.length >= 2 ? ab : '';
    }

    /* Вес совпадения — порядок из ТЗ. Разрыв между ступенями заведомо больше любого
       счётчика статей, чтобы популярность не перебивала точное совпадение имени. */
    function score(row, q) {
        var n = norm(row.n), id = norm(row.id);
        var names = [n, id].concat((row.a || []).map(norm));
        var best = 0;
        for (var i = 0; i < names.length; i++) {
            var v = names[i];
            if (!v) continue;
            var s = v === q ? 4000 : (v.indexOf(q) === 0 ? 3000 : (v.indexOf(q) !== -1 ? 2000 : 0));
            if (s > best) best = s;
        }
        // Аббревиатура — только точным совпадением: «CMB» обязано находить понятие, но
        // подстрочное совпадение по двум буквам засоряло бы выдачу на каждом коротком запросе.
        if (!best && row.t !== 'art' && abbrev(row.id) === q) best = 3500;
        return best;
    }

    function rank(rows, q) {
        var out = [];
        for (var i = 0; i < rows.length; i++) {
            var s = score(rows[i], q);
            if (s) out.push({ row: rows[i], s: s });
        }
        out.sort(function (a, b) {
            if (b.s !== a.s) return b.s - a.s;
            if (a.row.t === 'art') {
                // При равном весе совпадения полный разбор идёт впереди экспресса
                // (правило владельца 2026-07-31: экспресс находится, но не вытесняет).
                var ax = a.row.x ? 1 : 0, bx = b.row.x ? 1 : 0;
                if (ax !== bx) return ax - bx;
                return (b.row.d || '').localeCompare(a.row.d || '');   // затем свежесть
            }
            return (b.row.c || 0) - (a.row.c || 0);                    // справочники — популярность
        });
        return out.map(function (x) {
            var r = x.row;
            // nl — имя на языке страницы (у учёных); без него выдача снова показывала бы
            // «Johannes Kepler» там, где индекс уже знает «Иоганн Кеплер».
            return { t: r.t, id: r.id, n: r.n, nl: r.nl, url: urlFor(r),
                     c: r.c, s: r.s, d: r.d, score: x.s };
        });
    }

    /* Поиск внутри раздела: на странице тега, закона, учёного ищем только по статьям этого
       раздела — читатель пришёл за содержимым раздела, а не за всем сайтом. Список id даёт
       страница; если его нет, сужать нечего и поиск остаётся общим. */
    function inScope(rows, scope) {
        if (!scope || !scope.ids || !scope.ids.length) return rows;
        var allow = {};
        scope.ids.forEach(function (id) { allow[id] = 1; });
        return rows.filter(function (r) { return r.t !== 'art' || allow[r.id]; });
    }

    function group(list, limits) {
        var g = {};
        TYPES.forEach(function (t) { g[t] = []; });
        list.forEach(function (r) { if (g[r.t]) g[r.t].push(r); });
        TYPES.forEach(function (t) {
            var lim = (limits && limits[t]) || 0;
            if (lim) g[t] = g[t].slice(0, lim);
        });
        return g;
    }

    /* Мягкое совпадение по основам слов: «white dwarfs» не находил тег «white dwarf», а
       «чёрные дыры» — «чёрную дыру» (нашёл QA). Отбрасывать окончание последнего слова мало:
       в русском множественное меняет ОБА слова, и «чёрные дыры» → «чёрные дыр» не совпадёт
       ни с чем. Поэтому сравниваем основы: каждое слово запроса должно начинать какое-нибудь
       слово названия. Длинные слова режем на два символа — этого хватает на падеж и число,
       короткие сравниваем целиком, иначе «оси» начнут находить «осцилляторы».

       Полноценной морфологии на пять языков здесь быть не должно — это работа вектора.
       Мягкий проход включается, только если строгий не нашёл ни одного ПОНЯТИЯ. */
    function commonPrefix(a, b) {
        var i = 0, n = Math.min(a.length, b.length);
        while (i < n && a.charAt(i) === b.charAt(i)) i++;
        return i;
    }

    /* Слова считаем «одним и тем же», если общая часть либо не меньше четырёх букв
       («чёрные»/«чёрная» → чёрн), либо покрывает слово целиком минус окончание
       («дыры»/«дыра» → дыр). Отсечка в три буквы обязательна: без неё «оси» слипалось бы
       с «осцилляциями». */
    function sameWord(w, h) {
        var k = commonPrefix(w, h);
        if (k >= 4) return true;
        return k >= 3 && k >= Math.min(w.length, h.length) - 1;
    }

    function softMatch(row, q) {
        var words = q.split(/\s+/).filter(Boolean);
        if (!words.length) return false;
        var hay = [norm(row.n), norm(row.id).replace(/[_\-]/g, ' ')]
            .concat((row.a || []).map(norm)).join(' ').split(/\s+/);
        return words.every(function (w) {
            return hay.some(function (h) { return sameWord(w, h); });
        });
    }

    function localSearch(q, opts) {
        return loadIndex().then(function (rows) {
            var ranked = inScope(rank(rows, q), opts.scope);
            // Мягкий проход нужен, когда не нашлось ПОНЯТИЙ, а не когда пусто вообще:
            // «white dwarfs» находил две статьи и на этом останавливался, так что тег
            // «white dwarf» читателю не показывался (нашёл QA). Статьи по строгому запросу
            // остаются первыми, мягкие находки добавляются следом и своих не вытесняют.
            var hasEntity = ranked.some(function (r) { return r.t !== 'art'; });
            if (!hasEntity) {
                var seen = {};
                ranked.forEach(function (r) { seen[r.t + r.id] = 1; });
                var soft = rows.filter(function (r) {
                    return r.t !== 'art' && !seen[r.t + r.id] && softMatch(r, q);
                }).sort(function (a, b) { return (b.c || 0) - (a.c || 0); });
                ranked = ranked.concat(soft.map(function (r) {
                    return { t: r.t, id: r.id, n: r.n, nl: r.nl, url: urlFor(r),
                             c: r.c, s: r.s, d: r.d, score: 1000 };
                }));
            }
            return {
                q: q, source: 'local', total: ranked.length,
                groups: group(ranked, opts.limits)
            };
        });
    }

    /* Векторный источник. Отвечает только статьями, поэтому справочники всё равно берём
       локально и склеиваем. Любая осечка сети — молча возвращаемся к локальному поиску:
       поиск, который «не работает, потому что упал Worker», хуже поиска по словам.
       Новый ввод отменяет прежний сетевой запрос, а зависший Worker обрубается по
       таймауту — иначе Promise.all держал бы и готовую локальную часть выдачи
       (блокер QA 2026-07-31). */
    var _apiCtl = null;
    function apiSearch(q, opts) {
        var local = localSearch(q, opts);
        if (_apiCtl) { try { _apiCtl.abort(); } catch (e) {} }
        var ctl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
        _apiCtl = ctl;
        var kill = ctl ? setTimeout(function () { ctl.abort(); }, 8000) : null;
        var remote = fetch('/api/search?q=' + encodeURIComponent(q),
                           ctl ? { signal: ctl.signal } : undefined)
            .then(function (r) { if (kill) clearTimeout(kill); return r.ok ? r.json() : null; })
            .catch(function () { if (kill) clearTimeout(kill); return null; });
        return Promise.all([local, remote]).then(function (res) {
            var base = res[0], api = res[1];
            if (!api || !api.results || !api.results.length) return base;
            var arts = api.results.map(function (m) {
                return {
                    t: 'art', id: m.id, n: m.title || m.id,
                    url: m.url || '', d: m.date || '', score: Math.round((m.score || 0) * 1000)
                };
            });
            arts = inScope(arts, opts.scope);
            var lim = (opts.limits && opts.limits.art) || 0;
            base.groups.art = lim ? arts.slice(0, lim) : arts;
            base.source = 'vector';
            base.total = TYPES.reduce(function (n, t) { return n + base.groups[t].length; }, 0);
            return base;
        });
    }

    /* Приставки #тег, !учёный, @автор остаются рабочими для тех, кто привык, но теперь
       они лишь сужают вид, а не требуют знания синтаксиса: без приставки ищется всё. */
    var PREFIX = { '#': 'tag', '!': 'sci' };

    function search(query, options) {
        var opts = options || {};
        var q = norm(query);
        if (!q) return Promise.resolve({ q: '', source: 'none', total: 0, groups: group([], null) });
        var only = PREFIX[q.charAt(0)];
        if (only) q = q.slice(1).trim();
        if (!q) return Promise.resolve({ q: '', source: 'none', total: 0, groups: group([], null) });

        var limits = opts.limits || { tag: 6, law: 4, sci: 4, sec: 4, art: 20 };
        var run = (opts.source === 'vector' ? apiSearch : localSearch);
        return run(q, { scope: opts.scope, limits: limits }).then(function (res) {
            if (only) {
                TYPES.forEach(function (t) { if (t !== only) res.groups[t] = []; });
                res.total = res.groups[only].length;
            }
            return res;
        });
    }

    window.B42Search = {
        search: search,
        urlFor: urlFor,
        lang: LANG,
        types: TYPES,
        _loadIndex: loadIndex        // для проверок: даёт дождаться загрузки индекса
    };
})();
