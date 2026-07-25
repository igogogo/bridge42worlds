// Аналитика-дашборд «карта облака»: 3D-россыпь статей/авторов, которую можно покрутить мышью.
// Self-contained canvas (без внешних либ — строгий CSP). Данные: data/analytics/*.json (офлайн-
// препросчёт analytics_build.py, БЕЗ DeepSeek). Юзер 2026-07-24: показать группировки, 3D, «вау».
(function () {
  var root = document.getElementById('analytics');
  if (!root) return;
  var LANG = window.lang || 'en';
  var L = ({
    ru: { title: 'Карта проекта', articles: 'Статьи', authors: 'Авторы', loading: 'Считаем карту…',
          hint: 'тяни — повернуть · колесо — зум · клик по точке', clusters: 'Тематические группы', n: 'точек',
          theoryExp: 'Цвет точки: экспериментатор (охра) → теоретик (циан)',
          introA: 'Каждая точка — <b>статья</b>. Чем ближе две точки, тем больше у статей общих тем. Цвет — <b>тематическая группа</b> (кластер), в которую их собрал алгоритм по общим тегам. Покрути шар мышью, чтобы разглядеть, из чего состоит наше облако статей и какие темы рядом.',
          introB: 'Каждая точка — <b>автор</b> (все, кого мы разобрали, — тысячи). Рядом — авторы с похожим профилем работ; облака — это направления. Цвет — от <b>экспериментатора</b> к <b>теоретику</b> (по разделам его статей). Смысл не в отдельной точке, а в том, <b>как ведёт себя всё множество</b>: где плотные ядра, где редкие ветви.' },
    en: { title: 'Project map', articles: 'Articles', authors: 'Authors', loading: 'Building the map…',
          hint: 'drag to rotate · wheel to zoom · click a point', clusters: 'Topic groups', n: 'points',
          theoryExp: 'Point colour: experimentalist (ochre) → theorist (cyan)',
          introA: 'Each dot is an <b>article</b>. The closer two dots, the more topics the articles share. Colour = a <b>topic group</b> (cluster) the algorithm formed from shared tags. Rotate the sphere to see what our article cloud is made of and which themes sit together.',
          introB: 'Each dot is an <b>author</b> — every one we processed, thousands of them. Nearby dots share a similar body of work; the clouds are fields. Colour runs from <b>experimentalist</b> to <b>theorist</b> (from their papers’ areas). The point isn’t any single dot but <b>how the whole set behaves</b>: where the dense cores are, where the thin branches reach.' },
    es: { title: 'Mapa del proyecto', articles: 'Artículos', authors: 'Autores', loading: 'Construyendo el mapa…',
          hint: 'arrastra para rotar · rueda para zoom · clic en un punto', clusters: 'Grupos temáticos', n: 'puntos',
          theoryExp: 'Color: experimental (ocre) → teórico (cian)',
          introA: 'Cada punto es un <b>artículo</b>. Cuanto más cerca, más temas comparten. El color es un <b>grupo temático</b> formado por etiquetas comunes. Gira la esfera para ver de qué se compone nuestra nube de artículos.',
          introB: 'Cada punto es un <b>autor</b> — todos los que procesamos, miles. Los cercanos comparten un perfil similar; las nubes son campos. El color va de <b>experimental</b> a <b>teórico</b>. Lo importante no es un punto, sino <b>cómo se comporta todo el conjunto</b>: dónde están los núcleos densos y dónde las ramas escasas.' },
    ar: { title: 'خريطة المشروع', articles: 'المقالات', authors: 'المؤلفون', loading: 'نبني الخريطة…',
          hint: 'اسحب للتدوير · العجلة للتكبير · انقر نقطة', clusters: 'مجموعات موضوعية', n: 'نقطة',
          theoryExp: 'لون النقطة: تجريبي (أوكر) → نظري (سماوي)',
          introA: 'كل نقطة <b>مقالة</b>. كلما اقتربت نقطتان زادت المواضيع المشتركة. اللون = <b>مجموعة موضوعية</b> شكّلها الخوارزم من الوسوم المشتركة. أدر الكرة لترى مِمّ تتكوّن سحابة مقالاتنا.',
          introB: 'كل نقطة <b>مؤلف</b> — كل من عالجناهم، بالآلاف. المتجاورون لهم ملف عمل متشابه؛ والسحب هي المجالات. يتدرّج اللون من <b>تجريبي</b> إلى <b>نظري</b>. المهم ليس نقطة واحدة بل <b>كيف يتصرّف المجموع كله</b>: أين النوى الكثيفة وأين الفروع المتناثرة.' }
  })[LANG] || null;
  var T = L || { title: 'Project map', articles: 'Articles', authors: 'Authors', loading: '…',
                 hint: 'drag to rotate · wheel to zoom', clusters: 'Topic groups', n: 'points',
                 theoryExp: 'experimentalist → theorist', introA: '', introB: '' };
  // Вкладка «Полёт» — интерактивное путешествие сквозь облако статей (юзер 2026-07-25: «чтобы можно
  // было побродить как в 3D, поиграть; путешествие по нашей вселенной»).
  var FLY = ({
    ru: { tab: 'Полёт', fs: 'на весь экран', speed: 'скорость', hint: 'веди — рулить · колесо/ползунок — скорость · клик по звезде в прицеле — открыть',
          intro: 'Ты <b>летишь сквозь нашу вселенную статей</b>. Каждая звезда — работа; чем ярче, тем ближе. Веди мышью или пальцем, чтобы поворачивать, меняй скорость колесом или ползунком. Наведись на звезду в центре — узнаешь её; кликни — откроешь.' },
    en: { tab: 'Fly', fs: 'fullscreen', speed: 'speed', hint: 'steer to turn · wheel/slider for speed · click a star in the crosshair to open',
          intro: 'You are <b>flying through our universe of articles</b>. Each star is a paper; the brighter, the closer. Steer with mouse or finger, change speed with the wheel or slider. Aim at the star in the centre to see it — click to open.' },
    es: { tab: 'Vuelo', fs: 'pantalla completa', speed: 'velocidad', hint: 'dirige para girar · rueda/control para velocidad · clic en la estrella central para abrir',
          intro: 'Vuelas <b>por nuestro universo de artículos</b>. Cada estrella es un trabajo; cuanto más brillante, más cerca. Dirige con el ratón o el dedo, cambia la velocidad con la rueda o el control. Apunta a la estrella del centro para verla y haz clic para abrirla.' },
    ar: { tab: 'تحليق', fs: 'ملء الشاشة', speed: 'السرعة', hint: 'وجّه للدوران · العجلة/المنزلق للسرعة · انقر النجمة في المنتصف لفتحها',
          intro: 'أنت <b>تحلّق عبر كوننا من المقالات</b>. كل نجمة بحث؛ كلما زاد سطوعها اقتربت. وجّه بالفأرة أو الإصبع، وغيّر السرعة بالعجلة أو المنزلق. صوّب نحو النجمة في المنتصف لتراها وانقر لفتحها.' }
  })[LANG] || { tab: 'Fly', fs: 'fullscreen', speed: 'speed', hint: 'steer · wheel = speed · click centre star', intro: '' };
  var PAL = ['#2E8AA0', '#C77F3A', '#6C5CE7', '#2FA84F', '#D64545', '#C9A227', '#5AA9C9', '#E4A860',
             '#9B7EDE', '#4CAF50', '#E06666', '#00897B', '#8E24AA', '#F4511E', '#3949AB', '#00ACC1',
             '#7CB342', '#D81B60', '#5E35B1', '#FB8C00', '#43A047', '#1E88E5', '#6D4C41', '#546E7A'];

  // Панель-объяснение (юзер 2026-07-25: «дать объяснения — что такое кластеры, какие методы,
  // и внизу выводы про контент сайта»). Документация для пользователя, локализованная.
  var ABOUT = ({
    ru: '<h3>Как построена карта</h3>'
      + '<p>Статьи — связующая среда. Мы смотрим, какие <b>темы, разделы и понятия</b> встречаются в статьях вместе, '
      + 'и превращаем это в близость: похожие работы оказываются рядом. Всё считается <b>локально</b>, статистикой '
      + '(TF-IDF по тегам → кластеризация K-means → проекция в 3D методом t-SNE) — без обращения к ИИ, поэтому карту легко держать актуальной.</p>'
      + '<h3>Что значат группы и цвета</h3>'
      + '<ul><li><b>Точка</b> — статья (или автор). Чем ближе точки, тем больше общего.</li>'
      + '<li><b>Цвет</b> — тематическая группа (кластер), которую алгоритм выделил сам.</li>'
      + '<li><b>Название группы</b> даёт <b>ИИ</b>: он читает характерные теги кластера и пишет человеческое имя и краткую трактовку.</li>'
      + '<li>У авторов цвет ещё и по оси <b>экспериментатор → теоретик</b> (по разделам их статей).</li></ul>'
      + '<h3>Что сейчас на карте и куда развиваем</h3>'
      + '<p>Пока это две грани: <b>статьи</b> и <b>авторы</b> — весь наш контент, преломлённый через общие темы. '
      + 'Дальше строим <b>общую карту</b>: добавим вкладки <b>законов, учёных и тегов</b>, где всё связано между собой — '
      + 'чтобы можно было увидеть, из чего складывается знание проекта и куда оно растёт.</p>',
    en: '<h3>How the map is built</h3>'
      + '<p>Articles are the connective tissue. We look at which <b>topics, sections and concepts</b> co-occur in articles '
      + 'and turn that into closeness: similar work ends up nearby. Everything is computed <b>locally</b>, statistically '
      + '(TF-IDF over tags → K-means clustering → 3D projection via t-SNE) — no AI calls, so the map is easy to keep up to date.</p>'
      + '<h3>What the groups and colours mean</h3>'
      + '<ul><li>A <b>dot</b> is an article (or author). The closer the dots, the more they share.</li>'
      + '<li><b>Colour</b> is a topic group (cluster) the algorithm found on its own.</li>'
      + '<li>The <b>group name</b> comes from <b>AI</b>: it reads a cluster’s characteristic tags and writes a human name and a short reading.</li>'
      + '<li>For authors, colour also runs along an <b>experimentalist → theorist</b> axis.</li></ul>'
      + '<h3>What’s on the map now, and where it grows</h3>'
      + '<p>For now two facets: <b>articles</b> and <b>authors</b> — all our content refracted through shared themes. '
      + 'Next we build a <b>general map</b>: tabs for <b>laws, scientists and tags</b>, all interlinked — to see what the project’s knowledge is made of and where it’s heading.</p>',
    es: '<h3>Cómo se construye el mapa</h3>'
      + '<p>Los artículos son el tejido conector. Vemos qué <b>temas, secciones y conceptos</b> aparecen juntos '
      + 'y lo convertimos en cercanía. Todo se calcula <b>localmente</b> (TF-IDF → K-means → proyección 3D con t-SNE), sin IA.</p>'
      + '<h3>Qué significan los grupos y colores</h3>'
      + '<ul><li>Un <b>punto</b> es un artículo (o autor). Cuanto más cerca, más comparten.</li>'
      + '<li>El <b>color</b> es un grupo temático que el algoritmo encontró solo.</li>'
      + '<li>El <b>nombre del grupo</b> lo da la <b>IA</b> a partir de las etiquetas del clúster.</li>'
      + '<li>En autores, el color va de <b>experimental → teórico</b>.</li></ul>'
      + '<h3>Qué hay ahora y hacia dónde crece</h3>'
      + '<p>Por ahora dos facetas: <b>artículos</b> y <b>autores</b>. Luego un <b>mapa general</b> con pestañas de <b>leyes, científicos y etiquetas</b>.</p>',
    ar: '<h3>كيف بُنيت الخريطة</h3>'
      + '<p>المقالات هي النسيج الرابط. ننظر إلى <b>المواضيع والأقسام والمفاهيم</b> التي ترد معًا ونحوّلها إلى قُرب. '
      + 'يُحسب كل شيء <b>محليًا</b> إحصائيًا (TF-IDF ← تجميع K-means ← إسقاط ثلاثي الأبعاد t-SNE) دون ذكاء اصطناعي.</p>'
      + '<h3>ماذا تعني المجموعات والألوان</h3>'
      + '<ul><li><b>النقطة</b> مقالة (أو مؤلف). كلما اقتربت زاد المشترك.</li>'
      + '<li><b>اللون</b> مجموعة موضوعية اكتشفها الخوارزم.</li>'
      + '<li><b>اسم المجموعة</b> من <b>الذكاء الاصطناعي</b> اعتمادًا على وسوم العنقود.</li>'
      + '<li>لدى المؤلفين يتدرّج اللون من <b>تجريبي ← نظري</b>.</li></ul>'
      + '<h3>ما هو معروض الآن وإلى أين ينمو</h3>'
      + '<p>حاليًا وجهان: <b>المقالات</b> و<b>المؤلفون</b>. لاحقًا <b>خريطة عامة</b> بعلامات تبويب للقوانين والعلماء والوسوم.</p>'
  })[LANG] || '';

  root.innerHTML =
    '<h1 class="dash-h1">' + T.title + '</h1>' +
    '<div class="an-tabs"><button class="an-tab active" data-t="articles">' + T.articles + '</button>' +
    '<button class="an-tab" data-t="authors">' + T.authors + '</button>' +
    '<button class="an-tab" data-t="fly">✦ ' + FLY.tab + '</button></div>' +
    '<p class="an-intro" id="an-intro">' + T.introA + '</p>' +
    '<div class="an-stage" id="an-stage"><canvas id="an-canvas"></canvas><div class="an-hint">' + T.hint + '</div>' +
    '<div class="an-stage-ctl"><button class="an-btn" id="an-fs" title="' + (FLY.fs || 'fullscreen') + '">⛶</button></div>' +
    '<div class="an-speed" id="an-speed"><span>' + (FLY.speed || 'speed') + '</span>' +
    '<input type="range" id="an-speed-r" min="0" max="60" value="18"></div>' +
    '<div class="an-tip" id="an-tip" hidden></div></div>' +
    '<div class="an-legend" id="an-legend"></div>' +
    '<div class="b42-loader" id="an-loading">' + T.loading + '</div>' +
    '<div class="an-about">' + ABOUT + '</div>';

  var canvas = document.getElementById('an-canvas'), ctx = canvas.getContext('2d');
  var tip = document.getElementById('an-tip'), legendEl = document.getElementById('an-legend');
  var state = { data: null, mode: 'articles', yaw: 0.6, pitch: -0.3, zoom: 1, spin: true, hover: -1,
                travel: 0, speed: 0.0011, fyaw: 0, fpitch: 0 };   // fly-режим: продвижение + руль
  var cache = {};

  function sizeCanvas() {
    var stage = document.getElementById('an-stage');
    var fs = stage && stage.classList.contains('an-fs');
    var w = canvas.clientWidth || 640, h = fs ? (window.innerHeight || 700) : 460;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    state.W = w; state.H = h;
  }

  function load(mode) {
    state.mode = mode;
    // Авторов немного (у кого ≥4 статей), а разброс плотный — стартуем крупнее, чтобы облако читалось.
    state.zoom = mode === 'authors' ? 1.7 : 1;
    var intro = document.getElementById('an-intro');
    var hintEl = document.querySelector('.an-hint');
    // «Полёт» летит по облаку статей — переиспользуем те же точки; свой intro/hint, без легенды-кластеров.
    var dataMode = mode === 'fly' ? 'articles' : mode;
    if (intro) intro.innerHTML = mode === 'fly' ? FLY.intro : (mode === 'authors' ? T.introB : T.introA);
    if (hintEl) hintEl.textContent = mode === 'fly' ? FLY.hint : T.hint;
    if (mode === 'fly') { state.travel = 0; state.fyaw = 0; state.fpitch = 0; state.speed = 0.0011; }
    var speedBox = document.getElementById('an-speed');
    if (speedBox) speedBox.style.display = mode === 'fly' ? 'flex' : 'none';
    var sr = document.getElementById('an-speed-r');
    if (sr && mode === 'fly') sr.value = Math.round(state.speed / 0.006 * 60);
    if (cache[dataMode]) { state.data = cache[dataMode]; prep(); return; }
    document.getElementById('an-loading').style.display = '';
    fetch('/data/analytics/' + (dataMode === 'authors' ? 'authors-map' : 'articles-map') + '.json')
      .then(function (r) { return r.json(); })
      .then(function (d) { cache[dataMode] = d; state.data = d; prep(); })
      .catch(function () { document.getElementById('an-loading').textContent = '—'; });
  }

  function prep() {
    document.getElementById('an-loading').style.display = 'none';
    // центрируем точки в [-0.5,0.5]
    state.pts = state.data.points.map(function (p) {
      return { x: p.x - 0.5, y: p.y - 0.5, z: (p.z != null ? p.z : 0.5) - 0.5,
               c: p.c, th: p.th, label: p.t || p.id, url: p.url, id: p.id };
    });
    // при большом множестве (все авторы, ~16k) — мельче точки и ниже альфа: важна форма облака, не точка.
    var N = state.pts.length;
    state.ptScale = N > 8000 ? 0.5 : N > 4000 ? 0.7 : 1;
    state.ptAlpha = N > 8000 ? 0.5 : N > 4000 ? 0.7 : 1;
    if (state.mode === 'fly') { legendEl.innerHTML = ''; } else { renderLegend(); }
    draw();
  }

  function colorOf(p) {
    if (state.mode === 'authors' && p.th != null) {
      // градиент экспериментатор(охра) → теоретик(циан)
      var t = p.th;
      var a = [199, 127, 58], b = [46, 138, 160];
      return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * t) + ',' + Math.round(a[1] + (b[1] - a[1]) * t) + ',' + Math.round(a[2] + (b[2] - a[2]) * t) + ')';
    }
    return PAL[p.c % PAL.length];
  }

  function project(p) {
    var cy = Math.cos(state.yaw), sy = Math.sin(state.yaw), cx = Math.cos(state.pitch), sx = Math.sin(state.pitch);
    var x = p.x * cy - p.z * sy;
    var z = p.x * sy + p.z * cy;
    var y = p.y * cx - z * sx;
    z = p.y * sx + z * cx;
    var scale = (state.H * 0.7 * state.zoom) / (1.8 + z);  // перспектива
    return { sx: state.W / 2 + x * scale, sy: state.H / 2 + y * scale, depth: z, r: Math.max(1.2, 3.2 * scale / (state.H * 0.7)) };
  }

  // ── Полёт: камера летит вперёд сквозь облако, точки уходят навстречу и рециркулируют (бесконечный
  //    тоннель из наших статей). Руль — небольшие углы fyaw/fpitch (поворот тоннеля), скорость — travel. ──
  var FLY_RANGE = 2.6, FLY_NEAR = 0.16;
  function projectFly(p) {
    var f = 1 - (((p.z + 0.5 + state.travel) % 1) + 1) % 1;  // 0..1, растёт travel → точка приближается
    var Z = f * FLY_RANGE + FLY_NEAR;
    var X = p.x, Y = p.y;
    var cy = Math.cos(state.fyaw), sy = Math.sin(state.fyaw);
    var X2 = X * cy - Z * sy, Z2 = X * sy + Z * cy;
    var cx = Math.cos(state.fpitch), sx = Math.sin(state.fpitch);
    var Y2 = Y * cx - Z2 * sx, Z3 = Y * sx + Z2 * cx;
    if (Z3 < 0.06) return null;                       // за камерой — не рисуем
    var scale = (state.H * 0.62) / Z3;
    return { sx: state.W / 2 + X2 * scale, sy: state.H / 2 + Y2 * scale, depth: Z3, r: Math.max(0.6, 5 / Z3) };
  }
  function drawFly() {
    ctx.clearRect(0, 0, state.W, state.H);
    var proj = [];
    for (var i = 0; i < state.pts.length; i++) {
      var pr = projectFly(state.pts[i]);
      if (!pr) continue;
      if (pr.sx < -40 || pr.sx > state.W + 40 || pr.sy < -40 || pr.sy > state.H + 40) continue;
      pr.i = i; pr.color = colorOf(state.pts[i]); proj.push(pr);
    }
    proj.sort(function (a, b) { return b.depth - a.depth; });   // дальние сначала
    for (var k = 0; k < proj.length; k++) {
      var q = proj[k];
      ctx.globalAlpha = Math.max(0.1, Math.min(1, 1.25 - q.depth / FLY_RANGE));
      ctx.fillStyle = q.color;
      ctx.beginPath(); ctx.arc(q.sx, q.sy, q.i === state.hover ? q.r * 1.8 : q.r, 0, 6.283); ctx.fill();
    }
    ctx.globalAlpha = 1;
    // прицел по центру
    ctx.strokeStyle = 'rgba(140,150,160,.5)'; ctx.lineWidth = 1;
    var cxp = state.W / 2, cyp = state.H / 2;
    ctx.beginPath(); ctx.arc(cxp, cyp, 13, 0, 6.283); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cxp - 20, cyp); ctx.lineTo(cxp - 15, cyp);
    ctx.moveTo(cxp + 15, cyp); ctx.lineTo(cxp + 20, cyp); ctx.stroke();
  }

  function draw() {
    if (!state.pts) return;
    if (state.mode === 'fly') { drawFly(); return; }
    ctx.clearRect(0, 0, state.W, state.H);
    var proj = state.pts.map(function (p, i) { var pr = project(p); pr.i = i; pr.color = colorOf(p); return pr; });
    proj.sort(function (a, b) { return a.depth - b.depth; }); // дальние сначала
    for (var k = 0; k < proj.length; k++) {
      var pr = proj[k];
      var fade = 0.35 + 0.65 * (1 - (pr.depth + 0.5));
      ctx.globalAlpha = Math.max(0.12, Math.min(1, fade * (state.ptAlpha || 1)));
      ctx.fillStyle = pr.color;
      ctx.beginPath();
      ctx.arc(pr.sx, pr.sy, pr.i === state.hover ? pr.r * 2.4 : pr.r * (state.ptScale || 1), 0, 6.283);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // Метки кластеров приходят как сырые id (теги snake_case у статей; коды разделов у авторов) —
  // переводим в человекочитаемые локализованные имена (юзер 2026-07-24: «на русской версии теги
  // по-английски — называй по-нашему»). tagsLoc/ARXIV_CAT_NAMES грузит search.js.
  function niceLabel(raw) {
    if (state.mode === 'authors') {
      // коды arXiv: подкатегория после точки бывает ЗАГЛАВНОЙ (astro-ph.CO) или строчной
      // (cond-mat.stat-mech) — пробуем варианты, берём первый, что есть в справочнике разделов.
      var m = window.ARXIV_CAT_NAMES || {};
      var dot = raw.replace(/_/g, '.'), up = dot.replace(/\.([a-z-]+)$/, function (_, s) { return '.' + s.toUpperCase(); });
      return m[dot] || m[up] || m[raw] || dot;
    }
    var t = window.tagsLoc && tagsLoc[raw];
    return (t && t.name) || raw.replace(/_/g, ' ');
  }
  function renderLegend() {
    var cl = state.data.clusters || {};
    var titles = state.data.titles || null;   // человеческие названия от LLM-трактовщика (если посчитаны)
    var extra = state.mode === 'authors' ? '<div class="an-axis">' + T.theoryExp + '</div>' : '';
    // Кластеры — КАРТОЧКАМИ (юзер 2026-07-25): цветная полоса, название-заголовок, описание ниже.
    var items = Object.keys(cl).map(function (c) {
      var col = state.mode === 'authors' ? PAL[c % PAL.length] : PAL[c % PAL.length];
      var lt = titles && titles[c] ? titles[c][LANG] || titles[c].en : null;
      var title = lt ? lt.title : (cl[c] || []).map(niceLabel).slice(0, 3).join(' · ');
      var desc = lt && lt.desc ? '<div class="an-card-d">' + lt.desc + '</div>' : '';
      return '<div class="an-card" style="--cc:' + col + '"><div class="an-card-t">' + title + '</div>' + desc + '</div>';
    }).join('');
    legendEl.innerHTML = '<div class="an-lg-h">' + T.clusters + ' · <b>' + state.data.n + '</b> ' + T.n + '</div>' +
      '<div class="an-cards">' + items + '</div>' + extra;
    // search.js грузит tagsLoc асинхронно — если легенда отрисовалась раньше и нет LLM-имён,
    // дорисуем её один раз, когда словарь тегов доедет (иначе на RU останутся англ. id).
    if (!titles && state.mode !== 'authors' && !(window.tagsLoc && Object.keys(window.tagsLoc).length) && !renderLegend._retry) {
      renderLegend._retry = setInterval(function () {
        if (window.tagsLoc && Object.keys(window.tagsLoc).length) {
          clearInterval(renderLegend._retry); renderLegend._retry = 0; renderLegend();
        }
      }, 300);
    }
  }

  // взаимодействие
  var drag = null;
  canvas.addEventListener('mousedown', function (e) { drag = { x: e.clientX, y: e.clientY }; state.spin = false; });
  window.addEventListener('mouseup', function () { drag = null; });
  window.addEventListener('mousemove', function (e) {
    if (drag) {
      if (state.mode === 'fly') {
        // руль: небольшой поворот тоннеля, с автовозвратом (см. цикл). Инверсия по X — как штурвал.
        state.fyaw = Math.max(-0.6, Math.min(0.6, state.fyaw - (e.clientX - drag.x) * 0.004));
        state.fpitch = Math.max(-0.5, Math.min(0.5, state.fpitch + (e.clientY - drag.y) * 0.004));
        drag = { x: e.clientX, y: e.clientY }; return;
      }
      state.yaw += (e.clientX - drag.x) * 0.01; state.pitch += (e.clientY - drag.y) * 0.01;
      state.pitch = Math.max(-1.5, Math.min(1.5, state.pitch));
      drag = { x: e.clientX, y: e.clientY }; draw(); return;
    }
    // hover: ближайшая точка к курсору (в fly проецируем через projectFly)
    var rect = canvas.getBoundingClientRect(), mx = e.clientX - rect.left, my = e.clientY - rect.top;
    if (mx < 0 || my < 0 || mx > state.W || my > state.H) { if (state.hover !== -1) { state.hover = -1; tip.hidden = true; } return; }
    var best = -1, bd = state.mode === 'fly' ? 18 : 12, fly = state.mode === 'fly';
    for (var i = 0; i < state.pts.length; i++) {
      var pr = fly ? projectFly(state.pts[i]) : project(state.pts[i]);
      if (!pr) continue;
      var d = Math.hypot(pr.sx - mx, pr.sy - my); if (d < bd) { bd = d; best = i; }
    }
    if (best !== state.hover || fly) {
      state.hover = best;
      if (best >= 0) { tip.hidden = false; tip.textContent = state.pts[best].label; tip.style.left = (mx + 12) + 'px'; tip.style.top = (my + 12) + 'px'; }
      else tip.hidden = true;
      if (!fly) draw();
    }
  });
  canvas.addEventListener('click', function () {
    if (state.hover >= 0 && state.pts[state.hover].url) window.location = state.pts[state.hover].url;
  });
  canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    if (state.mode === 'fly') { state.speed = Math.max(0, Math.min(0.006, state.speed + (e.deltaY < 0 ? 0.0006 : -0.0006))); return; }
    state.zoom = Math.max(0.4, Math.min(4, state.zoom * (e.deltaY < 0 ? 1.1 : 0.9))); draw();
  }, { passive: false });

  // Тач: рулить/вращать пальцем (мобилка, молодёжь — «поиграть»).
  canvas.addEventListener('touchstart', function (e) { var t = e.touches[0]; drag = { x: t.clientX, y: t.clientY }; state.spin = false; }, { passive: true });
  canvas.addEventListener('touchmove', function (e) {
    if (!drag) return; var t = e.touches[0];
    if (state.mode === 'fly') {
      state.fyaw = Math.max(-0.6, Math.min(0.6, state.fyaw - (t.clientX - drag.x) * 0.004));
      state.fpitch = Math.max(-0.5, Math.min(0.5, state.fpitch + (t.clientY - drag.y) * 0.004));
    } else {
      state.yaw += (t.clientX - drag.x) * 0.01;
      state.pitch = Math.max(-1.5, Math.min(1.5, state.pitch + (t.clientY - drag.y) * 0.01)); draw();
    }
    drag = { x: t.clientX, y: t.clientY };
  }, { passive: true });
  canvas.addEventListener('touchend', function () { drag = null; }, { passive: true });

  // Фуллскрин сцены (юзер 2026-07-25: «возможность развернуть на весь экран»)
  var fsBtn = document.getElementById('an-fs'), stageEl = document.getElementById('an-stage');
  if (fsBtn && stageEl) {
    fsBtn.addEventListener('click', function () {
      stageEl.classList.toggle('an-fs');
      sizeCanvas(); draw();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && stageEl.classList.contains('an-fs')) { stageEl.classList.remove('an-fs'); sizeCanvas(); draw(); }
    });
  }
  // Ползунок скорости полёта
  var speedR = document.getElementById('an-speed-r');
  if (speedR) speedR.addEventListener('input', function () { state.speed = (+speedR.value) / 60 * 0.006; });

  document.querySelectorAll('.an-tab').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.an-tab').forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active'); state.spin = true; load(b.dataset.t);
    });
  });

  // Анимация: в обычном режиме — медленное авто-вращение; в полёте — постоянное движение вперёд
  // (travel) + плавный автовозврат руля к центру, чтобы «выравнивалось» само.
  (function loop() {
    if (state.pts) {
      if (state.mode === 'fly') {
        state.travel += state.speed;
        state.fyaw *= 0.96; state.fpitch *= 0.96;   // автоцентровка штурвала
        draw();
      } else if (state.spin) {
        state.yaw += 0.0025; draw();
      }
    }
    requestAnimationFrame(loop);
  })();

  window.addEventListener('resize', function () { sizeCanvas(); draw(); });
  sizeCanvas();
  load('articles');
})();
