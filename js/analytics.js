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
  var PAL = ['#2E8AA0', '#C77F3A', '#6C5CE7', '#2FA84F', '#D64545', '#C9A227', '#5AA9C9', '#E4A860',
             '#9B7EDE', '#4CAF50', '#E06666', '#00897B', '#8E24AA', '#F4511E', '#3949AB', '#00ACC1',
             '#7CB342', '#D81B60', '#5E35B1', '#FB8C00', '#43A047', '#1E88E5', '#6D4C41', '#546E7A'];

  root.innerHTML =
    '<h1 class="dash-h1">' + T.title + '</h1>' +
    '<div class="an-tabs"><button class="an-tab active" data-t="articles">' + T.articles + '</button>' +
    '<button class="an-tab" data-t="authors">' + T.authors + '</button></div>' +
    '<p class="an-intro" id="an-intro">' + T.introA + '</p>' +
    '<div class="an-stage"><canvas id="an-canvas"></canvas><div class="an-hint">' + T.hint + '</div>' +
    '<div class="an-tip" id="an-tip" hidden></div></div>' +
    '<div class="an-legend" id="an-legend"></div>' +
    '<div class="b42-loader" id="an-loading">' + T.loading + '</div>';

  var canvas = document.getElementById('an-canvas'), ctx = canvas.getContext('2d');
  var tip = document.getElementById('an-tip'), legendEl = document.getElementById('an-legend');
  var state = { data: null, mode: 'articles', yaw: 0.6, pitch: -0.3, zoom: 1, spin: true, hover: -1 };
  var cache = {};

  function sizeCanvas() {
    var w = canvas.clientWidth || 640, h = 460;
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
    if (intro) intro.innerHTML = mode === 'authors' ? T.introB : T.introA;
    if (cache[mode]) { state.data = cache[mode]; prep(); return; }
    document.getElementById('an-loading').style.display = '';
    fetch('/data/analytics/' + (mode === 'authors' ? 'authors-map' : 'articles-map') + '.json')
      .then(function (r) { return r.json(); })
      .then(function (d) { cache[mode] = d; state.data = d; prep(); })
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
    renderLegend();
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

  function draw() {
    if (!state.pts) return;
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
    var items = Object.keys(cl).map(function (c) {
      var col = state.mode === 'authors' ? 'var(--soft)' : PAL[c % PAL.length];
      var lt = titles && titles[c] ? titles[c][LANG] || titles[c].en : null;
      var text = lt ? ('<b>' + lt.title + '</b>' + (lt.desc ? ' — ' + lt.desc : '')) :
        (cl[c] || []).map(niceLabel).join(' · ');
      return '<span class="an-lg"><i style="background:' + col + '"></i>' + text + '</span>';
    }).join('');
    legendEl.innerHTML = '<div class="an-lg-h">' + T.clusters + ' · <b>' + state.data.n + '</b> ' + T.n + '</div>' + items + extra;
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
      state.yaw += (e.clientX - drag.x) * 0.01; state.pitch += (e.clientY - drag.y) * 0.01;
      state.pitch = Math.max(-1.5, Math.min(1.5, state.pitch));
      drag = { x: e.clientX, y: e.clientY }; draw(); return;
    }
    // hover
    var rect = canvas.getBoundingClientRect(), mx = e.clientX - rect.left, my = e.clientY - rect.top;
    if (mx < 0 || my < 0 || mx > state.W || my > state.H) { if (state.hover !== -1) { state.hover = -1; tip.hidden = true; draw(); } return; }
    var best = -1, bd = 12;
    for (var i = 0; i < state.pts.length; i++) { var pr = project(state.pts[i]); var d = Math.hypot(pr.sx - mx, pr.sy - my); if (d < bd) { bd = d; best = i; } }
    if (best !== state.hover) {
      state.hover = best;
      if (best >= 0) { tip.hidden = false; tip.textContent = state.pts[best].label; tip.style.left = (mx + 12) + 'px'; tip.style.top = (my + 12) + 'px'; }
      else tip.hidden = true;
      draw();
    }
  });
  canvas.addEventListener('click', function () {
    if (state.hover >= 0 && state.pts[state.hover].url) window.location = state.pts[state.hover].url;
  });
  canvas.addEventListener('wheel', function (e) { e.preventDefault(); state.zoom = Math.max(0.4, Math.min(4, state.zoom * (e.deltaY < 0 ? 1.1 : 0.9))); draw(); }, { passive: false });

  document.querySelectorAll('.an-tab').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.an-tab').forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active'); state.spin = true; load(b.dataset.t);
    });
  });

  // медленное авто-вращение, пока не трогают
  (function spin() { if (state.spin && state.pts) { state.yaw += 0.0025; draw(); } requestAnimationFrame(spin); })();

  window.addEventListener('resize', function () { sizeCanvas(); draw(); });
  sizeCanvas();
  load('articles');
})();
