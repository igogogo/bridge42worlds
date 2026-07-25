// Дашборд-витрина проекта (на месте /archive). Клиентский: читает индексы, загруженные search.js
// (window.searchIndex + tagsLoc/lawsData/scientistsData/authorsGraph/ARXIV_CAT_NAMES), считает и
// рисует всё сам — чистый SVG/HTML, без внешних библиотек (строгий CSP). Живёт на рефреше: числа
// пересчитываются при каждой загрузке из свежих данных.  (юзер 2026-07-24: «делаем дашборд, всё как
// в бизнесе — уровни, срезы, визуализации; открываем немного кухню, динамику, масштаб».)
(function () {
    var root = document.getElementById('dashboard');
    if (!root) return;

    var L = ({
        ru: { title:'Сводка проекта', articles:'статей', full:'полных', express:'экспресс', laws:'законов',
              tags:'тегов', sections:'разделов', scientists:'учёных', authors:'авторов', langs:'языка',
              nodes:'узлов графа', edges:'рёбер', activity:'Активность по дням', dynamics:'Динамика по месяцам',
              bySection:'Охват по разделам', kitchen:'Кухня: обложки и покрытие', covers:'Обложки',
              withCover:'с обложкой', noCover:'без обложки', topTags:'Частые теги', topSci:'Частые учёные',
              perDay:'статей за день', updated:'обновлено', loading:'Собираем данные…', none:'—',
              topLaws:'Ключевые законы', engagement:'Вовлечённость (данные сайта)', views:'просмотров',
              likes:'лайков', dislikes:'дизлайков', comments:'откликов', viewsByType:'Просмотры по типу',
              viewsByDevice:'Просмотры по устройству', reactions:'Реакции', lawTypes:'Типы законов',
              eArticle:'статьи', eTag:'теги', eLaw:'законы', eScientist:'учёные', eAuthor:'авторы' },
        en: { title:'Project dashboard', articles:'articles', full:'full', express:'express', laws:'laws',
              tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
              nodes:'graph nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
              bySection:'Coverage by area', kitchen:'Behind the scenes: covers & coverage', covers:'Covers',
              withCover:'with cover', noCover:'no cover', topTags:'Top tags', topSci:'Top scientists',
              perDay:'articles that day', updated:'updated', loading:'Crunching the data…', none:'—' },
        es: { title:'Panel del proyecto', articles:'artículos', full:'completos', express:'exprés', laws:'leyes',
              tags:'etiquetas', sections:'secciones', scientists:'científicos', authors:'autores', langs:'idiomas',
              nodes:'nodos', edges:'aristas', activity:'Actividad diaria', dynamics:'Dinámica mensual',
              bySection:'Cobertura por área', kitchen:'Tras bambalinas: portadas y cobertura', covers:'Portadas',
              withCover:'con portada', noCover:'sin portada', topTags:'Etiquetas frecuentes', topSci:'Científicos frecuentes',
              perDay:'artículos ese día', updated:'actualizado', loading:'Procesando datos…', none:'—' },
        ar: { title:'لوحة المشروع', articles:'مقالات', full:'كاملة', express:'سريعة', laws:'قوانين',
              tags:'وسوم', sections:'أقسام', scientists:'علماء', authors:'مؤلفين', langs:'لغات',
              nodes:'عقدة', edges:'حافة', activity:'النشاط اليومي', dynamics:'الديناميكية الشهرية',
              bySection:'التغطية حسب المجال', kitchen:'من الكواليس: الأغلفة والتغطية', covers:'الأغلفة',
              withCover:'بغلاف', noCover:'بدون غلاف', topTags:'وسوم متكررة', topSci:'علماء متكررون',
              perDay:'مقالات في ذلك اليوم', updated:'حُدّث', loading:'نُعالج البيانات…', none:'—' }
    })[window.lang] || null;
    // Английская карта — база-фолбэк: любой ключ, которого нет в языковой карте (напр. v2-подписи
    // добавлены только в ru/en), берётся отсюда, чтобы не было "undefined".
    var DEFAULT = { title:'Dashboard', articles:'articles', full:'full', express:'express', laws:'laws',
        tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
        nodes:'nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
        bySection:'Coverage by area', kitchen:'Covers & coverage', covers:'Covers', withCover:'with cover',
        noCover:'no cover', topTags:'Top tags', topSci:'Top scientists', perDay:'articles that day',
        updated:'updated', loading:'…', none:'—',
        engagement:'Engagement (site data)', views:'views', likes:'likes', dislikes:'dislikes',
        comments:'feedback', viewsByType:'Views by type', viewsByDevice:'Views by device',
        reactions:'Reactions', lawTypes:'Law types', eArticle:'articles', eTag:'tags', eLaw:'laws',
        eScientist:'scientists', eAuthor:'authors', topLaws:'Key laws' };
    var T = Object.assign({}, DEFAULT, L || {});

    var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
        return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]; }); };

    root.innerHTML = '<div class="b42-loader">' + T.loading + '</div>';

    // Ждём, пока search.js догрузит индекс и справочники (searchIndex собран из 3 тиров).
    var tries = 0;
    (function waitData() {
        var idx = window.searchIndex || [];
        if (idx.length && window.tagsLoc && window.lawsData) { build(); return; }
        if (tries++ > 120) { build(); return; }   // ~12с фолбэк — рисуем что есть
        setTimeout(waitData, 100);
    })();

    function build() {
        var idx = window.searchIndex || [];
        // Уникальные статьи по id (в индексе 3 тира на статью).
        var byId = {};
        idx.forEach(function (a) { if (!byId[a.id]) byId[a.id] = a; });
        var arts = Object.keys(byId).map(function (k) { return byId[k]; });

        var express = 0, withImg = 0;
        var byDay = {}, byMonth = {}, bySection = {}, tagCount = {}, sciCount = {};
        arts.forEach(function (a) {
            if (a.express) express++;
            if (a.image !== false) withImg++;
            if (a.date) { byDay[a.date] = (byDay[a.date] || 0) + 1;
                var m = a.date.slice(0, 7); if (!byMonth[m]) byMonth[m] = { full: 0, express: 0 };
                byMonth[m][a.express ? 'express' : 'full']++; }
            (a.categories || []).slice(0, 1).forEach(function (c) { var p = c.split('.')[0]; bySection[p] = (bySection[p] || 0) + 1; });
            (a.tags || []).forEach(function (t) { if (t) tagCount[t] = (tagCount[t] || 0) + 1; });
            (a.scientists || []).forEach(function (s) { if (s) sciCount[s] = (sciCount[s] || 0) + 1; });
        });
        var nA = arts.length, full = nA - express;
        var nL = Object.keys(window.lawsData || {}).length;
        var nT = Object.keys(window.tagsLoc || {}).length;
        var nSec = Object.keys(window.ARXIV_CAT_NAMES || {}).length;
        var nS = Object.keys(window.scientistsData || {}).length;
        var nAu = Object.keys(window.authorsGraph || {}).length;
        var nLang = (document.querySelectorAll('#langs-bar a').length || 4);

        var html = '<h1 class="dash-h1">' + esc(T.title) + '</h1>';

        // ── KPI ───────────────────────────────────────────────
        function kpi(n, label, sub) {
            return '<div class="kpi"><div class="kpi-n">' + n.toLocaleString() + '</div>' +
                '<div class="kpi-l">' + esc(label) + '</div>' + (sub ? '<div class="kpi-s">' + sub + '</div>' : '') + '</div>';
        }
        html += '<div class="kpi-grid">' +
            kpi(nA, T.articles, '<b>' + full + '</b> ' + T.full + ' · <b>' + express + '</b> ' + T.express) + kpi(full, T.full) + kpi(express, T.express) +
            kpi(nL, T.laws) + kpi(nT, T.tags) + kpi(nSec, T.sections) +
            kpi(nS, T.scientists) + kpi(nAu, T.authors) + kpi(nLang, T.langs) +
            '</div>';

        // ── Тепловая карта по дням (месяц-строка × дни) ────────
        var months = Object.keys(byMonth).sort().reverse();
        var maxDay = 0; Object.keys(byDay).forEach(function (d) { if (byDay[d] > maxDay) maxDay = byDay[d]; });
        function heatColor(n) {
            if (!n) return 'var(--card)';
            var t = Math.min(1, n / (maxDay || 1));
            return 'color-mix(in srgb, var(--cyan) ' + Math.round(18 + t * 72) + '%, transparent)';
        }
        var heat = '<div class="dash-block"><h2>' + esc(T.activity) + '</h2><div class="heatmap">';
        months.forEach(function (m) {
            heat += '<div class="heat-row"><span class="heat-m">' + m + '</span><span class="heat-days">';
            for (var d = 1; d <= 31; d++) {
                var ds = m + '-' + (d < 10 ? '0' + d : d);
                var n = byDay[ds] || 0;
                heat += '<a class="heat-cell" href="/lang/' + window.lang + '/index.html#d=' + ds + '" ' +
                    'style="background:' + heatColor(n) + '" title="' + ds + ': ' + n + ' ' + esc(T.perDay) + '"></a>';
            }
            heat += '</span></div>';
        });
        heat += '</div></div>';
        html += heat;

        // ── Динамика по месяцам (стек full/express) ────────────
        var maxMonth = 0; months.forEach(function (m) { var s = byMonth[m].full + byMonth[m].express; if (s > maxMonth) maxMonth = s; });
        var dyn = '<div class="dash-block"><h2>' + esc(T.dynamics) + '</h2><div class="bars">';
        months.slice().reverse().forEach(function (m) {
            var f = byMonth[m].full, e = byMonth[m].express, s = f + e;
            var h = Math.round(100 * s / (maxMonth || 1));
            dyn += '<div class="bar-col" title="' + m + ': ' + f + ' ' + esc(T.full) + ' · ' + e + ' ' + esc(T.express) + '">' +
                '<div class="bar-stack" style="height:' + h + '%">' +
                '<div class="bar-e" style="flex:' + e + '"></div><div class="bar-f" style="flex:' + f + '"></div></div>' +
                '<span class="bar-x">' + m.slice(2) + '</span></div>';
        });
        dyn += '</div><div class="bar-legend"><span class="lg lg-f"></span>' + esc(T.full) +
            ' <span class="lg lg-e"></span>' + esc(T.express) + '</div></div>';
        html += dyn;

        // ── Охват по разделам ──────────────────────────────────
        var secArr = Object.keys(bySection).map(function (k) { return [k, bySection[k]]; })
            .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 14);
        var maxSec = secArr.length ? secArr[0][1] : 1;
        var sec = '<div class="dash-block"><h2>' + esc(T.bySection) + '</h2><div class="hbars">';
        secArr.forEach(function (r) {
            sec += '<div class="hbar"><span class="hbar-l">' + esc(r[0]) + '</span>' +
                '<span class="hbar-t"><span class="hbar-fill" style="width:' + Math.round(100 * r[1] / maxSec) + '%"></span></span>' +
                '<span class="hbar-n">' + r[1] + '</span></div>';
        });
        sec += '</div></div>';
        html += sec;

        // ── Кухня: обложки ─────────────────────────────────────
        var pctCover = nA ? Math.round(100 * withImg / nA) : 0;
        html += '<div class="dash-block"><h2>' + esc(T.kitchen) + '</h2>' +
            '<div class="cover-bar"><span class="cover-fill" style="width:' + pctCover + '%"></span></div>' +
            '<div class="cover-legend"><b>' + withImg + '</b> ' + esc(T.withCover) + ' · <b>' + (nA - withImg) + '</b> ' + esc(T.noCover) +
            ' (' + pctCover + '%)</div></div>';

        // ── Топы ───────────────────────────────────────────────
        function topBlock(counts, title, kind) {
            var arr = Object.keys(counts).map(function (k) { return [k, counts[k]]; })
                .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 12);
            var loc = kind === 'tag' ? window.tagsLoc : null;
            var chips = arr.map(function (r) {
                var name = (loc && loc[r[0]] && loc[r[0]].name) || r[0].replace(/_/g, ' ');
                var href = kind === 'tag' ? ('/lang/' + window.lang + '/tags/' + encodeURIComponent(r[0]) + '.html')
                    : ('/lang/' + window.lang + '/scientists/' + (window.authorSlug ? authorSlug(r[0]) : r[0]) + '.html');
                return '<a class="dash-chip" href="' + href + '">' + esc(name) + ' <b>' + r[1] + '</b></a>';
            }).join('');
            return '<div class="dash-block"><h2>' + esc(title) + '</h2><div class="dash-chips">' + (chips || esc(T.none)) + '</div></div>';
        }
        html += topBlock(tagCount, T.topTags, 'tag');
        html += topBlock(sciCount, T.topSci, 'sci');

        // ── Топ-законы (по числу связанных тегов из справочника законов) ──
        var ld = window.lawsData || {};
        var lawArr = Object.keys(ld).map(function (k) {
            return [k, ((ld[k] && ld[k].tags) || []).length, (ld[k] && ld[k].name) || k, (ld[k] && ld[k].type) || ''];
        }).filter(function (r) { return r[1] > 0; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 12);
        if (lawArr.length) {
            html += '<div class="dash-block"><h2>' + esc(T.topLaws) + '</h2><div class="dash-chips">' +
                lawArr.map(function (r) {
                    return '<a class="dash-chip" href="/lang/' + window.lang + '/laws/' + encodeURIComponent(r[0]) + '.html">' +
                        esc(r[2]) + ' <b>' + r[1] + '</b></a>';
                }).join('') + '</div></div>';
        }
        // Типы законов — пай-чарт
        var typeCount = {};
        Object.keys(ld).forEach(function (k) { var t = (ld[k] && ld[k].type) || '?'; typeCount[t] = (typeCount[t] || 0) + 1; });

        root.innerHTML = html;

        // Пай-чарт из сегментов [{label,value,color}] → SVG-«пончик»
        function pie(segments, title) {
            var total = segments.reduce(function (s, x) { return s + x.value; }, 0) || 1;
            var R = 52, C = 60, sw = 22, circ = 2 * Math.PI * R, off = 0;
            var rings = segments.map(function (s) {
                var frac = s.value / total, len = frac * circ;
                var el = '<circle cx="' + C + '" cy="' + C + '" r="' + R + '" fill="none" stroke="' + s.color +
                    '" stroke-width="' + sw + '" stroke-dasharray="' + len + ' ' + (circ - len) +
                    '" stroke-dashoffset="' + (-off) + '" transform="rotate(-90 ' + C + ' ' + C + ')"><title>' +
                    esc(s.label) + ': ' + s.value + '</title></circle>';
                off += len; return el;
            }).join('');
            var legend = segments.filter(function (s) { return s.value; }).map(function (s) {
                return '<span class="pie-lg"><i style="background:' + s.color + '"></i>' + esc(s.label) + ' <b>' + s.value + '</b></span>';
            }).join('');
            return '<div class="pie-wrap"><div class="pie-title">' + esc(title) + '</div>' +
                '<svg viewBox="-6 -6 132 132" class="pie">' + rings + '</svg>' +
                '<div class="pie-legend">' + legend + '</div></div>';
        }
        var PAL = ['var(--cyan)', 'var(--ochre)', '#6C5CE7', '#2FA84F', '#D64545', '#C9A227', '#5AA9C9'];
        // Типы законов — пай сразу (данные локальные)
        var typeSegs = Object.keys(typeCount).map(function (t, i) { return { label: t, value: typeCount[t], color: PAL[i % PAL.length] }; });

        // ── Движок вовлечённости из Supabase (реальные просмотры/лайки/отклики) ──
        var SB = 'https://gyfdyfbuolnciaqxgybx.supabase.co/rest/v1/';
        var KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZmR5ZmJ1b2xuY2lhcXhneWJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTk0MzQsImV4cCI6MjA5ODM3NTQzNH0.rKsgWoj5ubRpkvElPfELOn-G9StW5RSOkxBbpvFyWc4';
        function cnt(table, filter) {
            return fetch(SB + table + '?select=id' + (filter ? '&' + filter : ''),
                { headers: { apikey: KEY, Authorization: 'Bearer ' + KEY, Prefer: 'count=exact', Range: '0-0' } })
                .then(function (r) { var cr = r.headers.get('content-range') || '0-0/0'; return parseInt(cr.split('/')[1], 10) || 0; })
                .catch(function () { return 0; });
        }
        Promise.all([
            cnt('views'), cnt('likes', 'reaction=eq.like'), cnt('likes', 'reaction=eq.dislike'), cnt('feedback'),
            cnt('views', 'entity_type=eq.article'), cnt('views', 'entity_type=eq.tag'),
            cnt('views', 'entity_type=eq.law'), cnt('views', 'entity_type=eq.scientist'), cnt('views', 'entity_type=eq.author'),
            cnt('views', 'device=eq.desktop'), cnt('views', 'device=eq.mobile'), cnt('views', 'device=eq.tablet')
        ]).then(function (v) {
            var totalViews = v[0], likes = v[1], dislikes = v[2], fb = v[3];
            var eng = document.createElement('div');
            eng.innerHTML =
                '<div class="dash-block"><h2>' + esc(T.engagement) + '</h2>' +
                '<div class="kpi-grid">' +
                    '<div class="kpi"><div class="kpi-n">' + totalViews.toLocaleString() + '</div><div class="kpi-l">' + esc(T.views) + '</div></div>' +
                    '<div class="kpi"><div class="kpi-n">' + likes.toLocaleString() + '</div><div class="kpi-l">' + esc(T.likes) + '</div></div>' +
                    '<div class="kpi"><div class="kpi-n">' + fb.toLocaleString() + '</div><div class="kpi-l">' + esc(T.comments) + '</div></div>' +
                '</div>' +
                '<div class="pies">' +
                    pie([
                        { label: T.eArticle, value: v[4], color: PAL[0] }, { label: T.eTag, value: v[5], color: PAL[1] },
                        { label: T.eLaw, value: v[6], color: PAL[2] }, { label: T.eScientist, value: v[7], color: PAL[3] },
                        { label: T.eAuthor, value: v[8], color: PAL[4] }
                    ], T.viewsByType) +
                    pie([
                        { label: 'desktop', value: v[9], color: PAL[0] }, { label: 'mobile', value: v[10], color: PAL[1] },
                        { label: 'tablet', value: v[11], color: PAL[2] }
                    ], T.viewsByDevice) +
                    pie([
                        { label: T.likes, value: likes, color: PAL[3] }, { label: T.dislikes, value: dislikes, color: PAL[4] }
                    ], T.reactions) +
                    pie(typeSegs, T.lawTypes) +
                '</div></div>';
            // Вставляем движок вовлечённости сразу после KPI-шапки (первый .kpi-grid)
            var firstKpi = root.querySelector('.kpi-grid');
            if (firstKpi && firstKpi.parentNode === root) root.insertBefore(eng, firstKpi.nextSibling);
            else root.appendChild(eng);
        });

        // ── Покрытие архива (corpus-stats.json из скана Kaggle-дампа, юзер 2026-07-25): сколько ВСЕГО
        //    в arXiv за 2025-2026 vs сколько мы обработали, разбивка по лицензиям и разделам. ──
        Promise.all([
            fetch('/data/corpus-stats.json').then(function (r) { return r.json(); }).catch(function () { return null; }),
            fetch('/data/arxiv-taxonomy-en.json').then(function (r) { return r.json(); }).catch(function () { return {}; })
        ]).then(function (arr) {
            var cs = arr[0], TAX = arr[1] || {};
            if (!cs || !cs.months) return;
            var CL = ({
                ru: { h: 'Покрытие архива · 2025–2026', dump: 'всего в arXiv', take: 'можем взять (откр. лиц.)',
                      done: 'обработали', sub: '{e} express · {f} полных', lic: 'Лицензии в arXiv',
                      sec: 'Топ разделов: взято / всего', note: 'Из открытых лицензий освоена лишь малая часть — материала на годы вперёд.' },
                en: { h: 'Archive coverage · 2025–2026', dump: 'total on arXiv', take: 'we can take (open lic.)',
                      done: 'processed', sub: '{e} express · {f} full', lic: 'Licenses on arXiv',
                      sec: 'Top sections: taken / total', note: 'Only a fraction of the open-licensed pool is covered — years of material ahead.' },
                es: { h: 'Cobertura del archivo · 2025–2026', dump: 'total en arXiv', take: 'podemos tomar (lic. abierta)',
                      done: 'procesados', sub: '{e} express · {f} completos', lic: 'Licencias en arXiv',
                      sec: 'Secciones: tomadas / total', note: 'Solo cubrimos una fracción del material con licencia abierta.' },
                ar: { h: 'تغطية الأرشيف · 2025–2026', dump: 'المجموع في arXiv', take: 'يمكننا أخذها (رخصة مفتوحة)',
                      done: 'عالجنا', sub: '{e} سريع · {f} كامل', lic: 'الرخص في arXiv',
                      sec: 'أهم الأقسام: مأخوذ / الكل', note: 'لم نغطِّ سوى جزء يسير من المتاح برخصة مفتوحة.' }
            })[window.lang] || null;
            CL = CL || { h: 'Archive coverage · 2025–2026', dump: 'total on arXiv', take: 'we can take', done: 'processed',
                         sub: '{e} express · {f} full', lic: 'Licenses', sec: 'Top sections', note: '' };
            var g = cs.generated_total || { gen: 0, express: 0, full: 0 };
            var licSegs = (cs.licenses || []).slice(0, 6).map(function (l, i) { return { label: l[0], value: l[1], color: PAL[i % PAL.length] }; });
            // Полное ЛОКАЛИЗОВАННОЕ имя раздела из НАШЕГО справочника (юзер 2026-07-25: «используй наши
            // названия, все языки»). Коды arXiv: подкатегория после точки бывает ЗАГЛАВНОЙ (astro-ph.CO).
            function catName(code) {
                var m = window.ARXIV_CAT_NAMES || {};
                var up = code.replace(/\.([a-z-]+)$/, function (_, s) { return '.' + s.toUpperCase(); });
                return m[code] || m[up] || TAX[code] || TAX[up] || code;   // наш локал. справочник → офиц. таксономия arXiv → код
            }
            var maxSec = (cs.sections && cs.sections[0] && cs.sections[0][1]) || 1;
            var secBars = (cs.sections || []).slice(0, 10).map(function (s) {
                var name = catName(s[0]);
                var pct = Math.round(s[2] / maxSec * 100), pctTot = Math.round(s[1] / maxSec * 100);
                return '<div class="cov-row"><span class="cov-name">' + esc(name) + '</span>' +
                    '<span class="cov-bar"><i class="cov-bar-tot" style="width:' + pctTot + '%"></i>' +
                    '<i class="cov-bar-take" style="width:' + pct + '%"></i></span>' +
                    '<span class="cov-num">' + s[2].toLocaleString() + ' / ' + s[1].toLocaleString() + '</span></div>';
            }).join('');
            var cov = document.createElement('div');
            cov.innerHTML = '<div class="dash-block"><h2>' + esc(CL.h) + '</h2>' +
                '<div class="kpi-grid">' +
                    '<div class="kpi"><div class="kpi-n">' + (cs.dump_total || 0).toLocaleString() + '</div><div class="kpi-l">' + esc(CL.dump) + '</div></div>' +
                    '<div class="kpi"><div class="kpi-n">' + (cs.allowed_total || 0).toLocaleString() + '</div><div class="kpi-l">' + esc(CL.take) + '</div></div>' +
                    '<div class="kpi"><div class="kpi-n">' + (g.gen || 0).toLocaleString() + '</div><div class="kpi-l">' + esc(CL.done) +
                        '<br><span class="kpi-sub">' + esc(CL.sub.replace('{e}', g.express).replace('{f}', g.full)) + '</span></div></div>' +
                '</div>' +
                '<p class="cov-note">' + esc(CL.note) + '</p>' +
                '<div class="pies">' + pie(licSegs, CL.lic) + '</div>' +
                '<h3 class="cov-h3">' + esc(CL.sec) + '</h3><div class="cov-list">' + secBars + '</div>' +
                '</div>';
            root.appendChild(cov);
        }).catch(function () {});

        // Дата сборки
        fetch('/data/build-info.json').then(function (r) { return r.json(); }).then(function (b) {
            if (b && b.built) { var e = document.createElement('div'); e.className = 'dash-built';
                e.textContent = T.updated + ' ' + b.built; root.appendChild(e); }
        }).catch(function () {});
    }
})();
