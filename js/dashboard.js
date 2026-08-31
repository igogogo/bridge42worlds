// Дашборд-витрина проекта (на месте /archive). Клиентский: читает индексы, загруженные search.js
// (window.searchIndex + tagsLoc/lawsData/scientistsData/authorsGraph/ARXIV_CAT_NAMES), считает и
// рисует всё сам — чистый SVG/HTML, без внешних библиотек (строгий CSP). Живёт на рефреше: числа
// пересчитываются при каждой загрузке из свежих данных.  (юзер 2026-07-24: «делаем дашборд, всё как
// в бизнесе — уровни, срезы, визуализации; открываем немного кухню, динамику, масштаб».)
(function () {
    var root = document.getElementById('dashboard');
    if (!root) return;

    var L = ({
        ru: { concepts:'понятий', formulas:'формул', areas:'областей', topConcepts:'Частые понятия', cWithArts:'понятий с опорой', cNoArts:'понятий без статей', cOnlyMent:'только упоминаются',  title:'Сводка проекта', articles:'статей', full:'полных', express:'экспресс', laws:'законов',
              tags:'тегов', sections:'разделов', scientists:'учёных', authors:'авторов', langs:'языка',
              nodes:'узлов графа', edges:'рёбер', activity:'Активность по дням', dynamics:'Динамика по месяцам',
              bySection:'Охват по разделам', kitchen:'Кухня: обложки и покрытие', covers:'Обложки',
              withCover:'с обложкой', noCover:'без обложки', km:'Машина знаний', kmOf:'из полных разборов', kmNote:'Полные разборы, у которых есть раздел с рекомендациями автору', topTags:'Частые теги', topSci:'Частые учёные',
              perDay:'статей за день', updated:'обновлено', loading:'Собираем данные…', none:'—',
              topLaws:'Ключевые законы', mainPage:'главная', audience:'Аудитория (свой счётчик)', uniqueVisitors:'уникальных', visits:'визитов', returning:'вернулись', topPages:'Куда ходили', byLangViews:'Языки читателей', sources:'Откуда пришли', clicks:'Что нажимали', readDepth:'Глубина чтения, %', audienceNote:'За 30 дней. Наши собственные визиты помечены и в эти числа не входят.', engagement:'Вовлечённость (данные сайта)', views:'просмотров',
              likes:'лайков', dislikes:'дизлайков', comments:'откликов', viewsByType:'Просмотры по типу',
              viewsByDevice:'Просмотры по устройству', reactions:'Реакции', lawTypes:'Виды понятий',
              eArticle:'статьи', eTag:'теги', eLaw:'законы', eScientist:'учёные', eAuthor:'авторы',
              pace:'Темп', d7:'за 7 дней', d30:'за 30 дней', perDayAvg:'в среднем в день',
              lastArticle:'последняя статья', growth:'Рост корпуса', totalBy:'всего к',
              ofThemFull:'из них полных',
              langCoverage:'Языковое покрытие', connectivity:'Связность: что не связано',
              noTags:'статей без тегов', orphanTags:'тегов без статей', lawsNoTags:'законов без связей',
              sciNoArticles:'учёных без статей', machine:'Машинное время', calls:'запросов к модели',
              tokensM:'млн токенов', cachePct:'взято из кэша', byAgent:'По шагам работы',
              period:'период', ofMax:'от максимума' },
        en: { concepts:'concepts', formulas:'formulas', areas:'areas', topConcepts:'Top concepts', cWithArts:'concepts with support', cNoArts:'concepts without papers', cOnlyMent:'mentioned only',  title:'Project dashboard', articles:'articles', full:'full', express:'express', laws:'laws',
              tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
              nodes:'graph nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
              bySection:'Coverage by area', kitchen:'Behind the scenes: covers & coverage', covers:'Covers',
              withCover:'with cover', noCover:'no cover', km:'Knowledge machine', kmOf:'of full reviews', kmNote:'Full reviews that carry a section of recommendations for the author', topTags:'Top tags', topSci:'Top scientists',
              perDay:'articles that day', updated:'updated', loading:'Crunching the data…', none:'—' },
        es: { concepts:'conceptos', formulas:'fórmulas', areas:'áreas', topConcepts:'Conceptos frecuentes', cWithArts:'conceptos con apoyo', cNoArts:'conceptos sin trabajos', cOnlyMent:'solo mencionados',  title:'Panel del proyecto', articles:'artículos', full:'completos', express:'exprés', laws:'leyes',
              tags:'etiquetas', sections:'secciones', scientists:'científicos', authors:'autores', langs:'idiomas',
              nodes:'nodos', edges:'aristas', activity:'Actividad diaria', dynamics:'Dinámica mensual',
              bySection:'Cobertura por área', kitchen:'Tras bambalinas: portadas y cobertura', covers:'Portadas',
              withCover:'con portada', noCover:'sin portada', km:'Máquina del conocimiento', kmOf:'de los análisis completos', kmNote:'Análisis completos que incluyen la sección de recomendaciones para el autor', topTags:'Etiquetas frecuentes', topSci:'Científicos frecuentes',
              perDay:'artículos ese día', updated:'actualizado', loading:'Procesando datos…', none:'—',
              topLaws:'Leyes clave', mainPage:'inicio', audience:'Audiencia (contador propio)', uniqueVisitors:'únicos', visits:'visitas', returning:'volvieron', topPages:'Adónde fueron', byLangViews:'Idiomas de lectores', sources:'De dónde llegaron', clicks:'Qué pulsaron', readDepth:'Profundidad de lectura, %', audienceNote:'Últimos 30 días. Nuestras propias visitas están marcadas y excluidas.', engagement:'Interacción (datos del sitio)', views:'vistas',
              likes:'me gusta', dislikes:'no me gusta', comments:'respuestas', viewsByType:'Vistas por tipo',
              viewsByDevice:'Vistas por dispositivo', reactions:'Reacciones', lawTypes:'Tipos de conceptos',
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
        ar: { concepts:'مفاهيم', formulas:'صيغ', areas:'مجالات', topConcepts:'مفاهيم متكررة', cWithArts:'مفاهيم لها سند', cNoArts:'مفاهيم بلا أبحاث', cOnlyMent:'مذكورة فقط',  title:'لوحة المشروع', articles:'مقالات', full:'كاملة', express:'سريعة', laws:'قوانين',
              tags:'وسوم', sections:'أقسام', scientists:'علماء', authors:'مؤلفين', langs:'لغات',
              nodes:'عقدة', edges:'حافة', activity:'النشاط اليومي', dynamics:'الديناميكية الشهرية',
              bySection:'التغطية حسب المجال', kitchen:'من الكواليس: الأغلفة والتغطية', covers:'الأغلفة',
              withCover:'بغلاف', noCover:'بدون غلاف', km:'آلة المعرفة', kmOf:'من التحليلات الكاملة', kmNote:'التحليلات الكاملة التي تتضمن قسم التوصيات لمؤلف العمل', topTags:'وسوم متكررة', topSci:'علماء متكررون',
              perDay:'مقالات في ذلك اليوم', updated:'حُدّث', loading:'نُعالج البيانات…', none:'—',
              topLaws:'قوانين أساسية', mainPage:'الرئيسية', audience:'الجمهور (عدّادنا الخاص)', uniqueVisitors:'زوار فريدون', visits:'زيارات', returning:'عادوا', topPages:'أين ذهبوا', byLangViews:'لغات القراء', sources:'من أين جاؤوا', clicks:'ما الذي ضغطوه', readDepth:'عمق القراءة، %', audienceNote:'آخر 30 يومًا. زياراتنا الخاصة مُعلَّمة ومستبعدة.', engagement:'التفاعل (بيانات الموقع)', views:'مشاهدات',
              likes:'إعجابات', dislikes:'عدم إعجاب', comments:'ردود', viewsByType:'المشاهدات حسب النوع',
              viewsByDevice:'المشاهدات حسب الجهاز', reactions:'التفاعلات', lawTypes:'أنواع المفاهيم',
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
        fr: { concepts:'concepts', formulas:'formules', areas:'domaines', topConcepts:'Concepts fréquents', cWithArts:'concepts avec appui', cNoArts:'concepts sans travaux', cOnlyMent:'seulement mentionnés',  title:'Tableau de bord du projet', articles:'articles', full:'complets', express:'express',
              laws:'lois', tags:'tags', sections:'sections', scientists:'scientifiques', authors:'auteurs',
              langs:'langues', nodes:'nœuds', edges:'arêtes', activity:'Activité quotidienne',
              dynamics:'Dynamique mensuelle', bySection:'Couverture par domaine',
              kitchen:'Dans les coulisses : illustrations et couverture', covers:'Illustrations',
              withCover:'avec couverture', noCover:'sans couverture', km:'Machine du savoir', kmOf:'des analyses complètes', kmNote:'Analyses complètes comportant une section de recommandations pour l\'auteur', topTags:'Tags fréquents',
              topSci:'Scientifiques fréquents', perDay:'articles ce jour-là', updated:'mis à jour',
              loading:'Traitement des données…', none:'—', topLaws:'Lois clés',
              mainPage:'accueil', audience:'Audience (notre compteur)', uniqueVisitors:'uniques', visits:'visites', returning:'revenus', topPages:'Où ils sont allés', byLangViews:'Langues des lecteurs', sources:'D’où ils viennent', clicks:'Ce qu’ils ont cliqué', readDepth:'Profondeur de lecture, %', audienceNote:'30 derniers jours. Nos propres visites sont marquées et exclues.', engagement:'Engagement (données du site)', views:'vues', likes:'j’aime',
              dislikes:'je n’aime pas', comments:'retours', viewsByType:'Vues par type',
              viewsByDevice:'Vues par appareil', reactions:'Réactions', lawTypes:'Types de concepts',
              eArticle:'articles', eTag:'tags', eLaw:'lois', eScientist:'scientifiques', eAuthor:'auteurs',
              pace:'Rythme', d7:'sur 7 jours', d30:'sur 30 jours', perDayAvg:'par jour en moyenne',
              lastArticle:'dernier article', growth:'Croissance du corpus', totalBy:'total au',
              ofThemFull:'dont complets',
              langCoverage:'Couverture linguistique', connectivity:'Connexions : ce qui reste isolé',
              noTags:'articles sans tags', orphanTags:'tags sans articles', lawsNoTags:'lois sans liens',
              sciNoArticles:'scientifiques sans articles', machine:'Temps machine',
              calls:'appels au modèle', tokensM:'M de jetons', cachePct:'servi depuis le cache',
              byAgent:'Par étape de travail', period:'période', ofMax:'du maximum' },
        zh: { concepts:'概念', formulas:'公式', areas:'领域', topConcepts:'常见概念',
              cWithArts:'有支撑的概念', cNoArts:'无文章的概念', cOnlyMent:'仅被提及',
              title:'项目概览', articles:'篇文章', full:'完整', express:'速览',
              laws:'定律', tags:'标签', sections:'分区', scientists:'科学家',
              authors:'作者', langs:'种语言', nodes:'图谱节点', edges:'边',
              activity:'按日活动', dynamics:'按月动态', bySection:'各分区覆盖',
              kitchen:'幕后：封面与覆盖', covers:'封面', withCover:'有封面',
              noCover:'无封面', km:'知识机器', kmOf:'占完整分析的',
              kmNote:'含有给作者建议一节的完整分析', topTags:'常见标签',
              topSci:'常见科学家', perDay:'每日文章', updated:'已更新',
              loading:'正在汇总数据…', none:'—', topLaws:'重要定律', mainPage:'首页',
              audience:'读者（自有统计）', uniqueVisitors:'独立访客', visits:'访问',
              returning:'回访', topPages:'去过哪里', byLangViews:'读者语言',
              sources:'来源', clicks:'点击了什么', readDepth:'阅读深度，%',
              audienceNote:'近30天。我们自己的访问已标记，不计入这些数字。',
              engagement:'参与度（站点数据）', views:'浏览', likes:'赞',
              dislikes:'踩', comments:'评论', viewsByType:'按类型浏览',
              viewsByDevice:'按设备浏览', reactions:'反应', lawTypes:'概念种类',
              eArticle:'文章', eTag:'标签', eLaw:'定律', eScientist:'科学家',
              eAuthor:'作者', pace:'节奏', d7:'近7天', d30:'近30天',
              perDayAvg:'日均', lastArticle:'最新文章', growth:'语料增长',
              totalBy:'累计至', ofThemFull:'其中完整', langCoverage:'语言覆盖',
              connectivity:'连通性：什么还孤立着', noTags:'无标签的文章',
              orphanTags:'无文章的标签', lawsNoTags:'无连接的定律',
              sciNoArticles:'无文章的科学家', machine:'机器时间', calls:'模型调用',
              tokensM:'百万词元', cachePct:'来自缓存', byAgent:'按工作阶段',
              period:'时段', ofMax:'占峰值' }

    })[window.lang] || null;
    // Английская карта — база-фолбэк: любой ключ, которого нет в языковой карте (напр. v2-подписи
    // добавлены только в ru/en), берётся отсюда, чтобы не было "undefined".
    var DEFAULT = { title:'Dashboard', concepts:'concepts', formulas:'formulas',
        areas:'areas', topConcepts:'Top concepts', cWithArts:'concepts with support',
        cNoArts:'concepts without papers', cOnlyMent:'mentioned only', articles:'articles', full:'full', express:'express', laws:'laws',
        tags:'tags', sections:'sections', scientists:'scientists', authors:'authors', langs:'languages',
        nodes:'nodes', edges:'edges', activity:'Daily activity', dynamics:'Monthly dynamics',
        bySection:'Coverage by area', kitchen:'Covers & coverage', covers:'Covers', withCover:'with cover',
        noCover:'no cover', km:'Knowledge machine', kmOf:'of full reviews', kmNote:'Full reviews that carry a section of recommendations for the author', topTags:'Top tags', topSci:'Top scientists', perDay:'articles that day',
        updated:'updated', loading:'…', none:'—',
        mainPage:'home', audience:'Audience (our own counter)', uniqueVisitors:'unique', visits:'visits', returning:'returned', topPages:'Where they went', byLangViews:'Reader languages', sources:'Where they came from', clicks:'What they clicked', readDepth:'Read depth, %', audienceNote:'Last 30 days. Our own visits are flagged and excluded.', engagement:'Engagement (site data)', views:'views', likes:'likes', dislikes:'dislikes',
        comments:'feedback', viewsByType:'Views by type', viewsByDevice:'Views by device',
        reactions:'Reactions', lawTypes:'Concept kinds', eArticle:'articles', eTag:'tags', eLaw:'laws',
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
    /* ДАННЫЕ ИЗ ОБЛАКА, А НЕ ИЗ ИНДЕКСА.
       Здесь качались индекс статей (14,2 МБ) и граф авторов (24,5 МБ) — тридцать
       девять мегабайт ради полусотни чисел, которые целиком считаются запросом.
       Владелец 31.08: «всё должно быть в облаке, все индексы».
       /api/summary — словарь и итоги, /api/corpus — дни (для карты и динамики). */
    var API = (window.B42_API || '').replace(/\/$/, '');
    var qs = '?lang=' + encodeURIComponent(window.lang || 'ru') + '&version=popular';
    Promise.all([
        fetch(API + '/api/summary' + qs).then(function (r) { return r.ok ? r.json() : null; }),
        fetch(API + '/api/corpus' + qs).then(function (r) { return r.ok ? r.json() : null; })
    ]).then(function (r) { build(r[0], r[1]); })
      .catch(function (e) {
          console.error('Dashboard data error:', e);
          var box = document.getElementById('dashboard');
          if (box) box.innerHTML = '<p class="dash-empty">' + esc(T.loading) + '</p>';
      });

    function build(S, C) {
        S = S || {}; C = C || {};
        var A = S.articles || {}, CN = S.concepts || {};
        var nA = A.total || 0, express = A.express || 0, full = A.full || 0;
        var withImg = A.covers || 0, kmN = A.km || 0;

        /* Дни приходят тройками [всего, экспрессов, с разбором] — из них выводим и
           карту по дням, и динамику по месяцам. Раньше и то и другое считалось
           обходом всех статей на клиенте. */
        var byDay = {}, byMonth = {};
        var days = C.days || {};
        Object.keys(days).forEach(function (d) {
            var t = days[d], n = t[0] || 0, ex = t[1] || 0;
            byDay[d] = n;
            var m = d.slice(0, 7);
            if (!byMonth[m]) byMonth[m] = { full: 0, express: 0 };
            byMonth[m].express += ex;
            byMonth[m].full += n - ex;
        });
        /* Разделы — из готовых сводок, там уже посчитано «сколько из них полных».
           Группируем по верхнему уровню: astro-ph.HE и astro-ph.GA — одна полоса. */
        var bySection = {};
        (S.secStats || []).forEach(function (r) {
            var p = String(r.cat || '').split('.')[0];
            if (!p) return;
            if (!bySection[p]) bySection[p] = { total: 0, full: 0 };
            bySection[p].total += r.n || 0;
            bySection[p].full += r.full || 0;
        });

        /* СЕГОДНЯШНИЙ СЛОВАРЬ. Здесь стояли «законов» и «тегов» из справочников
           lang/<язык>/data — а их не переписывали с 17 и 25 августа: словарь давно
           переехал в понятия, и дашборд показывал позапрошлый мир (владелец 31.08).
           Теперь: понятия, формулы, области — то, что конвейер обновляет каждый день. */
        var nC = CN.total || 0, nF = S.formulas || 0, nAr = S.areas || 0;
        /* Разделов СТОЛЬКО, СКОЛЬКО ИХ У arXiv (astro-ph.HE, cond-mat.soft…), а не
           сколько групп верхнего уровня: плитка обещает разделы, полоса ниже —
           группы, и путать их нельзя (было 20 вместо 156). */
        var nSec = S.sections || Object.keys(bySection).length || 0;
        var nS = S.scientists || 0;
        var nAu = S.authors || 0;
        var nLang = Object.keys(S.langs || {}).length ||
                    (document.querySelectorAll('#langs-bar a').length || 5);

        var html = '<h1 class="dash-h1">' + esc(T.title) + '</h1>';

        // ── KPI ───────────────────────────────────────────────
        function kpi(n, label, sub) {
            return '<div class="kpi"><div class="kpi-n">' + n.toLocaleString() + '</div>' +
                '<div class="kpi-l">' + esc(label) + '</div>' + (sub ? '<div class="kpi-s">' + sub + '</div>' : '') + '</div>';
        }
        html += '<div class="kpi-grid">' +
            kpi(nA, T.articles, '<b>' + full + '</b> ' + T.full + ' · <b>' + express + '</b> ' + T.express) + kpi(full, T.full) + kpi(express, T.express) +
            kpi(nC, T.concepts) + kpi(nF, T.formulas) + kpi(nAr, T.areas) +
            kpi(nSec, T.sections) + kpi(nS, T.scientists) + kpi(nAu, T.authors) +
            kpi(nLang, T.langs) +
            '</div>';

        // ── Темп ──────────────────────────────────────────────
        // Общие счётчики отвечают «сколько накопили», но не «идёт ли работа сейчас»: корпус
        // в две тысячи статей выглядит одинаково и когда мы пишем каждый день, и когда встали
        // неделю назад. Отсчёт — от сегодняшнего дня читателя, а не от последней сборки.
        function iso(d) { return new Date(d).toISOString().slice(0, 10); }
        var todayMs = Date.now();
        var since7 = iso(todayMs - 7 * 864e5), since30 = iso(todayMs - 30 * 864e5);
        var n7 = 0, n30 = 0, lastDate = A.last || '';
        Object.keys(byDay).forEach(function (d) {
            if (d > since7) n7 += byDay[d];
            if (d > since30) n30 += byDay[d];
            if (d > lastDate) lastDate = d;
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
            if (!full) return '';
            var km = kmN, pct = Math.round(100 * km / full);
            return '<div class="cover-bar km-bar"><span class="cover-fill" style="width:' + pct + '%"></span></div>' +
                '<div class="cover-legend" title="' + esc(T.kmNote || '') + '"><b>' + km + '</b> ' +
                esc(T.km) + ' · ' + esc(T.kmOf) + ' <b>' + full + '</b> (' + pct + '%)</div>';
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
        /* Что висит само по себе. Раньше считались теги без статей и законы без
           связей — по справочникам, которые никто не обновляет. Считаем то же самое
           про понятия: у скольких есть опора (статьи, О КОТОРЫХ понятие) и у скольких
           только упоминания в текстах. Пустая страница понятия — наш долг, и он виден. */
        var noArts = Math.max(0, nC - (CN.withArts || 0));
        var onlyMent = Math.max(0, (CN.withMentions || 0) - (CN.withArts || 0));
        html += '<div class="dash-block"><h2>' + esc(T.connectivity) + '</h2><div class="kpi-grid">' +
            kpi(CN.withArts || 0, T.cWithArts) + kpi(noArts, T.cNoArts) +
            kpi(onlyMent, T.cOnlyMent) + kpi(nF, T.formulas) +
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
        function chipsBlock(arr, title, href) {
            var chips = (arr || []).map(function (r) {
                return '<a class="dash-chip" href="' + href(r) + '">' +
                    esc(r.name || r.id) + ' <b>' + (r.n || 0) + '</b></a>';
            }).join('');
            return '<div class="dash-block"><h2>' + esc(title) + '</h2><div class="dash-chips">' +
                (chips || esc(T.none)) + '</div></div>';
        }
        html += chipsBlock(S.top, T.topConcepts, function (r) {
            return '/lang/' + window.lang + '/concepts/' + encodeURIComponent(r.id) + '.html';
        });
        html += chipsBlock(S.topSci, T.topSci, function (r) {
            return '/lang/' + window.lang + '/scientists/' +
                (window.authorSlug ? authorSlug(r.name) : encodeURIComponent(r.name)) + '.html';
        });

        /* Блок «Ключевые законы» убран. Он считал связи по справочнику законов, а тот
           не переписывался с 25 августа и после переезда на облако вовсе не грузится:
           блок молча не рисовался. Его место занял «Частые понятия» выше — та же мысль
           на сегодняшнем словаре и со ссылками на живые страницы. */
        // Виды понятий — круговая
        /* ВИДЫ ПОНЯТИЙ вместо типов законов. Круг считался по lawsData — справочнику,
           который не переписывали с 25 августа; после переезда на облако его вовсе не
           стало, и круг молча исчез. Считаем по реестру понятий: закон, уравнение,
           явление, величина, прибор — то, что конвейер обновляет каждый день. */
        var KIND_RU = {
            concept:'понятие', law:'закон', principle:'принцип', theorem:'теорема',
            equation:'уравнение', phenomenon:'явление', effect:'эффект', method:'метод',
            process:'процесс', object:'объект', substance:'вещество', instrument:'прибор',
            quantity:'величина', unit:'единица', constant:'константа',
            statistics:'статистика', math:'математика', theory:'теория',
            property:'свойство', formula:'формула'
        };
        var typeCount = {};
        var kindsRaw = (S.concepts || {}).kinds || {};
        Object.keys(kindsRaw).sort(function (a, b) { return kindsRaw[b] - kindsRaw[a]; })
            .slice(0, 8).forEach(function (k) {
                var name = (window.lang === 'ru' && KIND_RU[k]) ? KIND_RU[k] : k;
                typeCount[name] = kindsRaw[k];
            });

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
