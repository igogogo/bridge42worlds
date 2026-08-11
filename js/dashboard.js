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
              withCover:'с обложкой', noCover:'без обложки', km:'Машина знаний', kmOf:'из полных разборов', kmNote:'Полные разборы, у которых есть раздел с рекомендациями автору', topTags:'Частые теги', topSci:'Частые учёные',
              perDay:'статей за день', updated:'обновлено', loading:'Собираем данные…', none:'—',
              topLaws:'Ключевые законы', mainPage:'главная', audience:'Аудитория (свой счётчик)', uniqueVisitors:'уникальных', visits:'визитов', returning:'вернулись', topPages:'Куда ходили', byLangViews:'Языки читателей', sources:'Откуда пришли', clicks:'Что нажимали', readDepth:'Глубина чтения, %', audienceNote:'За 30 дней. Наши собственные визиты помечены и в эти числа не входят.', engagement:'Вовлечённость (данные сайта)', views:'просмотров',
              likes:'лайков', dislikes:'дизлайков', comments:'откликов', viewsByType:'Просмотры по типу',
              viewsByDevice:'Просмотры по устройству', reactions:'Реакции', lawTypes:'Типы законов',
              eArticle:'статьи', eTag:'теги', eLaw:'законы', eScientist:'учёные', eAuthor:'авторы',
              pace:'Темп', d7:'за 7 дней', d30:'за 30 дней', perDayAvg:'в среднем в день',
              lastArticle:'последняя статья', growth:'Рост корпуса', totalBy:'всего к',
              ofThemFull:'из них полных',
              langCoverage:'Языковое покрытие', connectivity:'Связность: что не связано',
              noTags:'статей без тегов', orphanTags:'тегов без статей', lawsNoTags:'законов без связей',
              sciNoArticles:'учёных без статей', machine:'Машинное время', calls:'запросов к модели',
              tokensM:'млн токенов', cachePct:'взято из кэша', byAgent:'По шагам работы',
              period:'период', ofMax:'от максимума' },
        en: { title:'Project dashboard', articles:'articles', full:'full', express:'express', laws:'laws',
              tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
              nodes:'graph nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
              bySection:'Coverage by area', kitchen:'Behind the scenes: covers & coverage', covers:'Covers',
              withCover:'with cover', noCover:'no cover', km:'Knowledge machine', kmOf:'of full reviews', kmNote:'Full reviews that carry a section of recommendations for the author', topTags:'Top tags', topSci:'Top scientists',
              perDay:'articles that day', updated:'updated', loading:'Crunching the data…', none:'—' },
        es: { title:'Panel del proyecto', articles:'artículos', full:'completos', express:'exprés', laws:'leyes',
              tags:'etiquetas', sections:'secciones', scientists:'científicos', authors:'autores', langs:'idiomas',
              nodes:'nodos', edges:'aristas', activity:'Actividad diaria', dynamics:'Dinámica mensual',
              bySection:'Cobertura por área', kitchen:'Tras bambalinas: portadas y cobertura', covers:'Portadas',
              withCover:'con portada', noCover:'sin portada', km:'Máquina del conocimiento', kmOf:'de los análisis completos', kmNote:'Análisis completos que incluyen la sección de recomendaciones para el autor', topTags:'Etiquetas frecuentes', topSci:'Científicos frecuentes',
              perDay:'artículos ese día', updated:'actualizado', loading:'Procesando datos…', none:'—',
              topLaws:'Leyes clave', mainPage:'inicio', audience:'Audiencia (contador propio)', uniqueVisitors:'únicos', visits:'visitas', returning:'volvieron', topPages:'Adónde fueron', byLangViews:'Idiomas de lectores', sources:'De dónde llegaron', clicks:'Qué pulsaron', readDepth:'Profundidad de lectura, %', audienceNote:'Últimos 30 días. Nuestras propias visitas están marcadas y excluidas.', engagement:'Interacción (datos del sitio)', views:'vistas',
              likes:'me gusta', dislikes:'no me gusta', comments:'respuestas', viewsByType:'Vistas por tipo',
              viewsByDevice:'Vistas por dispositivo', reactions:'Reacciones', lawTypes:'Tipos de leyes',
              eArticle:'artículos', eTag:'etiquetas', eLaw:'leyes', eScientist:'científicos', eAuthor:'autores',
              pace:'Ritmo', d7:'últimos 7 días', d30:'últimos 30 días', perDayAvg:'al día de media',
              lastArticle:'último artículo', growth:'Crecimiento del corpus', totalBy:'total hasta',
              ofThemFull:'de ellos completos',
              langCoverage:'Cobertura por idioma', connectivity:'Conexiones: lo que quedó suelto',
              noTags:'artículos sin etiquetas', orphanTags:'etiquetas sin artículos',
              lawsNoTags:'leyes sin vínculos', sciNoArticles:'científicos sin artículos',
              machine:'Tiempo de máquina', calls:'llamadas al modelo', tokensM:'M de tokens',
              cachePct:'servido desde caché', byAgent:'Por etapa de trabajo', period:'periodo',
              ofMax:'del máximo' },
        ar: { title:'لوحة المشروع', articles:'مقالات', full:'كاملة', express:'سريعة', laws:'قوانين',
              tags:'وسوم', sections:'أقسام', scientists:'علماء', authors:'مؤلفين', langs:'لغات',
              nodes:'عقدة', edges:'حافة', activity:'النشاط اليومي', dynamics:'الديناميكية الشهرية',
              bySection:'التغطية حسب المجال', kitchen:'من الكواليس: الأغلفة والتغطية', covers:'الأغلفة',
              withCover:'بغلاف', noCover:'بدون غلاف', km:'آلة المعرفة', kmOf:'من التحليلات الكاملة', kmNote:'التحليلات الكاملة التي تتضمن قسم التوصيات لمؤلف العمل', topTags:'وسوم متكررة', topSci:'علماء متكررون',
              perDay:'مقالات في ذلك اليوم', updated:'حُدّث', loading:'نُعالج البيانات…', none:'—',
              topLaws:'قوانين أساسية', mainPage:'الرئيسية', audience:'الجمهور (عدّادنا الخاص)', uniqueVisitors:'زوار فريدون', visits:'زيارات', returning:'عادوا', topPages:'أين ذهبوا', byLangViews:'لغات القراء', sources:'من أين جاؤوا', clicks:'ما الذي ضغطوه', readDepth:'عمق القراءة، %', audienceNote:'آخر 30 يومًا. زياراتنا الخاصة مُعلَّمة ومستبعدة.', engagement:'التفاعل (بيانات الموقع)', views:'مشاهدات',
              likes:'إعجابات', dislikes:'عدم إعجاب', comments:'ردود', viewsByType:'المشاهدات حسب النوع',
              viewsByDevice:'المشاهدات حسب الجهاز', reactions:'التفاعلات', lawTypes:'أنواع القوانين',
              eArticle:'مقالات', eTag:'وسوم', eLaw:'قوانين', eScientist:'علماء', eAuthor:'مؤلفون',
              pace:'الوتيرة', d7:'خلال 7 أيام', d30:'خلال 30 يومًا', perDayAvg:'يوميًا في المتوسط',
              lastArticle:'آخر مقالة', growth:'نمو المجموعة', totalBy:'المجموع بحلول', ofThemFull:'منها كاملة',
              langCoverage:'التغطية اللغوية', connectivity:'الترابط: ما بقي غير مرتبط',
              noTags:'مقالات بلا وسوم', orphanTags:'وسوم بلا مقالات', lawsNoTags:'قوانين بلا روابط',
              sciNoArticles:'علماء بلا مقالات', machine:'وقت الآلة', calls:'طلبات إلى النموذج',
              tokensM:'مليون رمز', cachePct:'من الذاكرة المؤقتة', byAgent:'حسب مرحلة العمل',
              period:'الفترة', ofMax:'من الحد الأقصى' },
        // Французский появился пятым языком позже дашборда, и до сих пор весь его текст
        // приезжал из английского фолбэка — читатель видел «Daily activity» на французской
        // странице. Ключи те же, что у остальных.
        fr: { title:'Tableau de bord du projet', articles:'articles', full:'complets', express:'express',
              laws:'lois', tags:'tags', sections:'sections', scientists:'scientifiques', authors:'auteurs',
              langs:'langues', nodes:'nœuds', edges:'arêtes', activity:'Activité quotidienne',
              dynamics:'Dynamique mensuelle', bySection:'Couverture par domaine',
              kitchen:'Dans les coulisses : illustrations et couverture', covers:'Illustrations',
              withCover:'avec couverture', noCover:'sans couverture', km:'Machine du savoir', kmOf:'des analyses complètes', kmNote:'Analyses complètes comportant une section de recommandations pour l\'auteur', topTags:'Tags fréquents',
              topSci:'Scientifiques fréquents', perDay:'articles ce jour-là', updated:'mis à jour',
              loading:'Traitement des données…', none:'—', topLaws:'Lois clés',
              mainPage:'accueil', audience:'Audience (notre compteur)', uniqueVisitors:'uniques', visits:'visites', returning:'revenus', topPages:'Où ils sont allés', byLangViews:'Langues des lecteurs', sources:'D’où ils viennent', clicks:'Ce qu’ils ont cliqué', readDepth:'Profondeur de lecture, %', audienceNote:'30 derniers jours. Nos propres visites sont marquées et exclues.', engagement:'Engagement (données du site)', views:'vues', likes:'j’aime',
              dislikes:'je n’aime pas', comments:'retours', viewsByType:'Vues par type',
              viewsByDevice:'Vues par appareil', reactions:'Réactions', lawTypes:'Types de lois',
              eArticle:'articles', eTag:'tags', eLaw:'lois', eScientist:'scientifiques', eAuthor:'auteurs',
              pace:'Rythme', d7:'sur 7 jours', d30:'sur 30 jours', perDayAvg:'par jour en moyenne',
              lastArticle:'dernier article', growth:'Croissance du corpus', totalBy:'total au',
              ofThemFull:'dont complets',
              langCoverage:'Couverture linguistique', connectivity:'Connexions : ce qui reste isolé',
              noTags:'articles sans tags', orphanTags:'tags sans articles', lawsNoTags:'lois sans liens',
              sciNoArticles:'scientifiques sans articles', machine:'Temps machine',
              calls:'appels au modèle', tokensM:'M de jetons', cachePct:'servi depuis le cache',
              byAgent:'Par étape de travail', period:'période', ofMax:'du maximum' }
    })[window.lang] || null;
    // Английская карта — база-фолбэк: любой ключ, которого нет в языковой карте (напр. v2-подписи
    // добавлены только в ru/en), берётся отсюда, чтобы не было "undefined".
    var DEFAULT = { title:'Dashboard', articles:'articles', full:'full', express:'express', laws:'laws',
        tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
        nodes:'nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
        bySection:'Coverage by area', kitchen:'Covers & coverage', covers:'Covers', withCover:'with cover',
        noCover:'no cover', km:'Knowledge machine', kmOf:'of full reviews', kmNote:'Full reviews that carry a section of recommendations for the author', topTags:'Top tags', topSci:'Top scientists', perDay:'articles that day',
        updated:'updated', loading:'…', none:'—',
        mainPage:'home', audience:'Audience (our own counter)', uniqueVisitors:'unique', visits:'visits', returning:'returned', topPages:'Where they went', byLangViews:'Reader languages', sources:'Where they came from', clicks:'What they clicked', readDepth:'Read depth, %', audienceNote:'Last 30 days. Our own visits are flagged and excluded.', engagement:'Engagement (site data)', views:'views', likes:'likes', dislikes:'dislikes',
        comments:'feedback', viewsByType:'Views by type', viewsByDevice:'Views by device',
        reactions:'Reactions', lawTypes:'Law types', eArticle:'articles', eTag:'tags', eLaw:'laws',
        eScientist:'scientists', eAuthor:'authors', topLaws:'Key laws',
        pace:'Pace', d7:'last 7 days', d30:'last 30 days', perDayAvg:'per day on average',
        lastArticle:'latest article', growth:'Corpus growth', totalBy:'total by', ofThemFull:'of them full',
        langCoverage:'Language coverage', connectivity:'Connectivity: what is left loose',
        noTags:'articles without tags', orphanTags:'tags without articles', lawsNoTags:'laws without links',
        sciNoArticles:'scientists without articles', machine:'Machine time', calls:'model calls',
        tokensM:'M tokens', cachePct:'served from cache', byAgent:'By work stage', period:'period',
        ofMax:'of the maximum' };
    var T = Object.assign({}, DEFAULT, L || {});

    var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
        return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]; }); };

    root.innerHTML = '<div class="b42-loader">' + T.loading + '</div>';

    // Данные ПРОСИМ, а не ждём. Раньше здесь стоял опрос window.searchIndex раз в 100 мс с
    // выходом по 12-секундному таймеру — он молча терпел любую причину, по которой индекс не
    // приехал, и рисовал нули. Именно так дашборд и опустел 2026-07-31, когда search.js стал
    // грузить индекс только на страницах со списком: у дашборда списка нет, ждать было нечего,
    // и через 12 секунд он показывал 0 статей при живом корпусе. Теперь три источника
    // запрашиваются явно: индекс (вся сводка), справочники (теги/законы/учёные), граф авторов
    // (счётчик авторов — он по той же причине показывал 0).
    Promise.all([
        window.ensureSearchIndex ? window.ensureSearchIndex() : Promise.resolve(window.searchIndex || []),
        window.B42Refs || Promise.resolve({}),
        window.ensureAuthorsGraph ? window.ensureAuthorsGraph() : Promise.resolve({})
    ]).then(function (r) { build(r[0]); })
      // Сводка без части данных лучше вечного «Собираем данные…»: рисуем тем, что доехало.
      .catch(function (e) { console.error('Dashboard data error:', e); build(window.searchIndex || []); });

    function build(index) {
        var idx = index || window.searchIndex || [];
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
            // По разделу считаем не только «сколько», но и «сколько из них полных»: раздел
            // с 300 экспрессами и разделом с 300 разборами — разные вещи, а полоса была одна.
            (a.categories || []).slice(0, 1).forEach(function (c) {
                var p = c.split('.')[0];
                if (!bySection[p]) bySection[p] = { total: 0, full: 0 };
                bySection[p].total++;
                if (!a.express) bySection[p].full++;
            });
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

        // ── Темп ──────────────────────────────────────────────
        // Общие счётчики отвечают «сколько накопили», но не «идёт ли работа сейчас»: корпус
        // в две тысячи статей выглядит одинаково и когда мы пишем каждый день, и когда встали
        // неделю назад. Отсчёт — от сегодняшнего дня читателя, а не от последней сборки.
        function iso(d) { return new Date(d).toISOString().slice(0, 10); }
        var todayMs = Date.now();
        var since7 = iso(todayMs - 7 * 864e5), since30 = iso(todayMs - 30 * 864e5);
        var n7 = 0, n30 = 0, lastDate = '';
        arts.forEach(function (a) {
            if (!a.date) return;
            if (a.date > since7) n7++;
            if (a.date > since30) n30++;
            if (a.date > lastDate) lastDate = a.date;
        });
        function kpiText(text, label, sub) {
            return '<div class="kpi"><div class="kpi-n kpi-n-sm">' + esc(text) + '</div>' +
                '<div class="kpi-l">' + esc(label) + '</div>' + (sub ? '<div class="kpi-s">' + sub + '</div>' : '') + '</div>';
        }
        html += '<div class="dash-block"><h2>' + esc(T.pace) + '</h2><div class="kpi-grid">' +
            kpi(n7, T.d7) + kpi(n30, T.d30) +
            kpi(Math.round(n30 / 30 * 10) / 10, T.perDayAvg) +
            kpiText(lastDate || T.none, T.lastArticle) +
            '</div></div>';
        // Слот под языковое покрытие: данные приезжают отдельным файлом, но место в потоке
        // держим заранее — иначе блок встал бы в конец, куда попадает всё асинхронное.
        html += '<div id="dash-langs"></div>';

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

        // ── Рост корпуса (накопительно) ────────────────────────
        // Столбики по месяцам показывают «сколько сделали в июле», но не отвечают на вопрос,
        // который задаёт каждый, кто видит проект впервые: он вообще растёт? Накопительная
        // кривая отвечает одним взглядом — и заодно видно, когда темп менялся.
        var asc = months.slice().reverse();
        var cum = 0;
        var pts = asc.map(function (m) { cum += byMonth[m].full + byMonth[m].express; return { m: m, v: cum }; });
        if (pts.length > 1) {
            var W = 620, H = 150, PL = 6, PB = 20, PT = 8;
            var maxV = pts[pts.length - 1].v || 1;
            var xy = pts.map(function (p, i) {
                return [PL + i * (W - 2 * PL) / (pts.length - 1),
                        PT + (H - PT - PB) * (1 - p.v / maxV)];
            });
            var line = xy.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ');
            var area = line + ' L' + xy[xy.length - 1][0].toFixed(1) + ' ' + (H - PB) + ' L' + PL + ' ' + (H - PB) + ' Z';
            var dots = xy.map(function (p, i) {
                return '<circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="2.5" fill="var(--cyan)">' +
                    '<title>' + pts[i].m + ': ' + pts[i].v.toLocaleString() + '</title></circle>';
            }).join('');
            html += '<div class="dash-block"><h2>' + esc(T.growth) + '</h2>' +
                '<svg class="growth-svg" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" role="img">' +
                '<path d="' + area + '" fill="color-mix(in srgb, var(--cyan) 16%, transparent)"/>' +
                '<path d="' + line + '" fill="none" stroke="var(--cyan)" stroke-width="2" ' +
                'stroke-linejoin="round" stroke-linecap="round"/>' + dots + '</svg>' +
                '<div class="growth-legend"><span>' + esc(pts[0].m) + '</span>' +
                '<span><b>' + maxV.toLocaleString() + '</b> ' + esc(T.totalBy) + ' ' + esc(pts[pts.length - 1].m) + '</span></div></div>';
        }

        // ── Охват по разделам ──────────────────────────────────
        var secArr = Object.keys(bySection).map(function (k) { return [k, bySection[k].total, bySection[k].full]; })
            .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 14);
        var maxSec = secArr.length ? secArr[0][1] : 1;
        var sec = '<div class="dash-block"><h2>' + esc(T.bySection) + '</h2><div class="hbars">';
        secArr.forEach(function (r) {
            // Две полосы в одном жёлобе: вся охра — сколько статей в разделе, циан поверх —
            // сколько из них полных разборов. Ширины считаются от одного максимума, поэтому
            // разделы сравнимы между собой, а не каждый сам с собой.
            sec += '<div class="hbar" title="' + esc(r[0]) + ': ' + r[1] + ' · ' + r[2] + ' ' + esc(T.full) + '">' +
                '<span class="hbar-l">' + esc(r[0]) + '</span>' +
                '<span class="hbar-t"><span class="hbar-fill" style="width:' + Math.round(100 * r[1] / maxSec) + '%"></span>' +
                '<span class="hbar-fill hbar-fill-full" style="width:' + Math.round(100 * r[2] / maxSec) + '%"></span></span>' +
                '<span class="hbar-n">' + r[1] + '<i class="hbar-sub">' + r[2] + '</i></span></div>';
        });
        sec += '</div></div>';
        html += sec;

        // ── Кухня: обложки ─────────────────────────────────────
        // Владелец 11 августа: «в дашборд — сколько статей имеют такое дополнение».
        // Считаем от ПОЛНЫХ разборов, а не от всего архива: экспрессам раздел не пишется
        // вовсе, и доля от 3.6 тысяч показывала бы вечные 0.4% вместо честной картины.
        function kmBar() {
            var full = arts.filter(function (a) { return !a.express; });
            var km = full.filter(function (a) { return a.km; }).length;
            if (!full.length) return '';
            var pct = Math.round(100 * km / full.length);
            return '<div class="cover-bar km-bar"><span class="cover-fill" style="width:' + pct + '%"></span></div>' +
                '<div class="cover-legend" title="' + esc(T.kmNote || '') + '"><b>' + km + '</b> ' +
                esc(T.km) + ' · ' + esc(T.kmOf) + ' <b>' + full.length + '</b> (' + pct + '%)</div>';
        }
        var pctCover = nA ? Math.round(100 * withImg / nA) : 0;
        html += '<div class="dash-block"><h2>' + esc(T.kitchen) + '</h2>' +
            '<div class="cover-bar"><span class="cover-fill" style="width:' + pctCover + '%"></span></div>' +
            '<div class="cover-legend"><b>' + withImg + '</b> ' + esc(T.withCover) + ' · <b>' + (nA - withImg) + '</b> ' + esc(T.noCover) +
            ' (' + pctCover + '%)</div>' + kmBar() + '</div>';

        // ── Связность: что не связано ──────────────────────────
        // Витрина показывает, сколько всего накоплено; это — сколько из накопленного висит
        // само по себе. Половина словаря тегов может не встречаться ни в одной статье, и по
        // общим счётчикам этого не видно вообще. Считается из тех же справочников, что уже
        // загружены страницей, — ни одного лишнего запроса.
        var tagsAll = window.tagsLoc || {}, sciAll = window.scientistsData || {}, lawsAll = window.lawsData || {};
        var noTagArts = arts.filter(function (a) { return !((a.tags || []).length); }).length;
        var orphanTags = Object.keys(tagsAll).filter(function (t) { return !tagCount[t]; }).length;
        var lawsLoose = Object.keys(lawsAll).filter(function (k) { return !(((lawsAll[k] || {}).tags || []).length); }).length;
        var sciLoose = Object.keys(sciAll).filter(function (s) { return !sciCount[s]; }).length;
        html += '<div class="dash-block"><h2>' + esc(T.connectivity) + '</h2><div class="kpi-grid">' +
            kpi(noTagArts, T.noTags) + kpi(orphanTags, T.orphanTags) +
            kpi(lawsLoose, T.lawsNoTags) + kpi(sciLoose, T.sciNoArticles) +
            '</div></div>';

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

        // Слот под машинное время — перед покрытием архива: сначала «чем это сделано»,
        // потом «сколько такого ещё осталось в arXiv».
        html += '<div id="dash-machine"></div>';

        root.innerHTML = html;

        // ── Языковое покрытие ─────────────────────────────────
        // KPI считают по индексу ТЕКУЩЕГО языка, поэтому на любой странице выходит одно и то
        // же число и разрыв между языками не виден. Файл собирает tools/lang_coverage.py.
        fetch('/data/lang-coverage.json').then(function (r) { return r.json(); }).then(function (lc) {
            var slot = document.getElementById('dash-langs');
            if (!slot || !lc || !lc.langs || !lc.langs.length) return;
            var mx = lc.max || 1;
            slot.innerHTML = '<div class="dash-block"><h2>' + esc(T.langCoverage) + '</h2><div class="hbars">' +
                lc.langs.map(function (r) {
                    // Вниз, а не к ближайшему: 2109 из 2110 округлялось в «100%», и недобор
                    // одной статьи читался как полный паритет. Недобор должен быть виден.
                    var pct = Math.floor(100 * r.articles / mx);
                    return '<div class="hbar" title="' + esc(r.lang) + ': ' + r.articles + ' · ' + r.full + ' ' + esc(T.full) + '">' +
                        '<span class="hbar-l">' + esc(String(r.lang).toUpperCase()) + '</span>' +
                        '<span class="hbar-t"><span class="hbar-fill" style="width:' + pct + '%"></span>' +
                        '<span class="hbar-fill hbar-fill-full" style="width:' + Math.round(100 * r.full / mx) + '%"></span></span>' +
                        '<span class="hbar-n">' + r.articles.toLocaleString() + '<i class="hbar-sub">' + pct + '%</i></span></div>';
                }).join('') + '</div><div class="cover-legend"><span class="lg lg-f"></span>' +
                esc(T.ofThemFull) + '</div></div>';
        }).catch(function () {});

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

        /* ── Аудитория: свой счётчик (/api/stats), а не Supabase ──
           Владелец 2026-07-31: «кто зашёл, сколько, куда ходили, что нажимали, ретеншн,
           уникальные». Блок молчит, пока ручка не выложена: пустой дашборд лучше, чем
           дашборд с нулями, которые выглядят как «читателей нет».
           Свои визиты в эти числа не входят — события с меткой тестировщика (d=1)
           /api/stats отфильтровывает на своей стороне. */
        (function audience() {
            fetch('/api/stats?days=30')
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (s) {
                    if (!s || !s.totals) return;
                    var t = s.totals;
                    // Ноль просмотров = счётчик только выложили и данных ещё нет. Показывать
                    // такой блок незачем — он расскажет ровно ничего.
                    if (!t.n) return;
                    function row(label, val, max) {
                        return '<div class="hbar"><span class="hbar-l">' + esc(String(label).slice(0, 22)) + '</span>' +
                            '<span class="hbar-t"><span class="hbar-fill" style="width:' +
                            Math.round(100 * val / (max || 1)) + '%"></span></span>' +
                            '<span class="hbar-n">' + val + '</span></div>';
                    }
                    /* Путь целиком в узкую колонку не влезает и обрезается на «/lang/ar/arc…» —
                       по такой подписи не понять, какая это страница. Убираем языковой
                       префикс (язык и так виден в соседнем ряду) и служебный index.html,
                       из статьи оставляем её arXiv-номер: он опознаётся с одного взгляда. */
                    function shortPath(p) {
                        var s = String(p || '').replace(/^\/lang\/[a-z]{2}\//, '/').replace(/index\.html$/, '');
                        var art = s.match(/archive\/\d{4}-\d{2}-\d{2}\/([^/]+)/);
                        if (art) return art[1];
                        s = s.replace(/^\/|\/$/g, '');
                        return s || T.mainPage;
                    }
                    function bars(list, key, valKey, title, fmt) {
                        if (!list || !list.length) return '';
                        var max = Math.max.apply(null, list.map(function (r) { return r[valKey]; }));
                        return '<div class="dash-sub"><h3>' + esc(title) + '</h3><div class="hbars">' +
                            list.slice(0, 8).map(function (r) {
                                return row((fmt ? fmt(r[key]) : r[key]) || T.none, r[valKey], max);
                            }).join('') +
                            '</div></div>';
                    }
                    var pctReturn = t.uniq ? Math.round(100 * s.returning / t.uniq) : 0;
                    var el = document.createElement('div');
                    el.innerHTML = '<div class="dash-block"><h2>' + esc(T.audience) + '</h2>' +
                        '<div class="kpi-grid">' +
                          '<div class="kpi"><div class="kpi-n">' + t.uniq.toLocaleString() + '</div><div class="kpi-l">' + esc(T.uniqueVisitors) + '</div></div>' +
                          '<div class="kpi"><div class="kpi-n">' + t.visits.toLocaleString() + '</div><div class="kpi-l">' + esc(T.visits) + '</div></div>' +
                          '<div class="kpi"><div class="kpi-n">' + t.n.toLocaleString() + '</div><div class="kpi-l">' + esc(T.views) + '</div></div>' +
                          '<div class="kpi"><div class="kpi-n">' + pctReturn + '%</div><div class="kpi-l">' + esc(T.returning) + '</div></div>' +
                        '</div>' +
                        bars(s.byPath, 'path', 'n', T.topPages, shortPath) +
                        bars(s.byLang, 'lang', 'n', T.byLangViews) +
                        bars(s.byRef, 'ref', 'n', T.sources) +
                        bars(s.byClick, 'kind', 'n', T.clicks) +
                        bars(s.depth, 'pct', 'n', T.readDepth) +
                        '<div class="dash-note">' + esc(T.audienceNote) + '</div>' +
                      '</div>';
                    root.appendChild(el);
                })
                .catch(function () { /* ручка не выложена — блока просто нет */ });
        })();

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
                      sec: 'أهم الأقسام: مأخوذ / الكل', note: 'لم نغطِّ سوى جزء يسير من المتاح برخصة مفتوحة.' },
                fr: { h: 'Couverture de l’archive · 2025–2026', dump: 'total sur arXiv', take: 'accessible (licence ouverte)',
                      done: 'traités', sub: '{e} express · {f} complets', lic: 'Licences sur arXiv',
                      sec: 'Principales sections : pris / total', note: 'Nous n’avons couvert qu’une fraction du matériel sous licence ouverte — il y en a pour des années.' }
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

        // ── Машинное время ────────────────────────────────────
        // Самая честная кухня, какая у нас есть: что стоит за статьями. Показываем измеренное —
        // вызовы, токены, долю кэша, — и намеренно не переводим в деньги: тариф меняется без
        // нас, а решение показывать сумму читателю не техническое. Свод: tools/usage_summary.py.
        fetch('/data/usage-summary.json').then(function (r) { return r.json(); }).then(function (u) {
            var slot = document.getElementById('dash-machine');
            if (!slot || !u || !u.calls) return;
            var mTok = Math.round((u.prompt + u.completion) / 1e5) / 10;
            var maxAg = (u.agents && u.agents[0] && u.agents[0][1]) || 1;
            var bars = (u.agents || []).slice(0, 6).map(function (a) {
                return '<div class="hbar" title="' + esc(a[0]) + ': ' + a[1] + '"><span class="hbar-l">' + esc(a[0]) + '</span>' +
                    '<span class="hbar-t"><span class="hbar-fill hbar-fill-full" style="width:' +
                    Math.round(100 * a[1] / maxAg) + '%"></span></span>' +
                    '<span class="hbar-n">' + a[1].toLocaleString() + '</span></div>';
            }).join('');
            slot.innerHTML = '<div class="dash-block"><h2>' + esc(T.machine) + '</h2><div class="kpi-grid">' +
                kpi(u.calls, T.calls) + kpi(mTok, T.tokensM) + kpiText(u.cachePct + '%', T.cachePct) +
                kpiText(u.from + ' → ' + u.to, T.period) +
                '</div><h3 class="cov-h3">' + esc(T.byAgent) + '</h3><div class="hbars">' + bars + '</div></div>';
        }).catch(function () {});

        // Дата сборки
        fetch('/data/build-info.json').then(function (r) { return r.json(); }).then(function (b) {
            if (b && b.built) { var e = document.createElement('div'); e.className = 'dash-built';
                e.textContent = T.updated + ' ' + b.built; root.appendChild(e); }
        }).catch(function () {});
    }
})();
