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
              perDay:'статей за день', updated:'обновлено', loading:'Собираем данные…', none:'—' },
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
    var T = L || ({ title:'Dashboard', articles:'articles', full:'full', express:'express', laws:'laws',
        tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
        nodes:'nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
        bySection:'Coverage by area', kitchen:'Covers & coverage', covers:'Covers', withCover:'with cover',
        noCover:'no cover', topTags:'Top tags', topSci:'Top scientists', perDay:'articles that day',
        updated:'updated', loading:'…', none:'—' });

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
            kpi(nA, T.articles, '<b>' + full + '</b> ' + T.full + ' · <b>' + express + '</b> ' + T.express) +
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

        root.innerHTML = html;

        // Дата сборки
        fetch('/data/build-info.json').then(function (r) { return r.json(); }).then(function (b) {
            if (b && b.built) { var e = document.createElement('div'); e.className = 'dash-built';
                e.textContent = T.updated + ' ' + b.built; root.appendChild(e); }
        }).catch(function () {});
    }
})();
