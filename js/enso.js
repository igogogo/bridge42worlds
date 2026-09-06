/* Панель «El Niño 2026–2027»: один экран, без прокрутки страницы.

   Владелец 03.09, разбор второй итерации:
     · подсветку понятий оставить внизу, но подвал сделать выше и НЕПОДВИЖНЫМ (он дёргался
       при наведении), а рядом с курсором показывать карточку-абзац;
     · слева всё карточками: тревоги по климату, по ЦЕНАМ и по ПОЛОМКЕ МОДЕЛЕЙ, разбор
       «кто отваливается постоянно» (у нас есть выпуски с прошлого августа), вердикт;
     · на карте Тихого океана — сравнение с самым сильным событием (1997-98 и остальные);
     · у сезонов SON/DJF/MAM и у сценариев base/strong/record — пояснения по наведению;
     · на каждом числе переключатель «сейчас / что изменилось с прошлого измерения»;
     · строка обновления и источников — наверх, у каждого источника своё пояснение.

   Данные — три файла с нашего домена. Сайт не пересобирается: обновить дашборд значит
   положить новый latest.json. Язык панели английский. */
(function () {
  'use strict';

  var T = {
    fresh: 'fresh', stale: 'stale',
    tabs: { verdict: 'Verdict', overview: 'Overview', news: 'News', now: 'Where we are', ocean: 'Ocean', models: 'Models', air: 'Air & fuel', trend: 'Dynamics', regions: 'Regions', food: 'Food', how: 'Method', refs: 'References', chain: 'Data chain', about: 'About' },
    tabHelp: {
      verdict: 'What the machine makes of it today: the verdict written from the numbers on this page, the turning point, the outlook, what to watch, the caveats.',
      overview: 'One screen with everything: a strip of key indicators and a mosaic of every chart, each a door into its section.',
      news: 'What changed in the last week — values, risks, alerts, the verdict — and what is due next week.',
      now: 'Where the event stands: the daily and weekly Niño indices against the strongest past events, the map of the Pacific, ONI and RONI.',
      ocean: 'The ocean itself: daily boxes straight from the NOAA grid, the water under the equator by mooring, the reanalysis section.',
      models: 'The forecast models: the plume, three issues stacked, the scoreboard of who keeps up, how they break, how they revise.',
      air: 'The atmosphere and the fuel: the coupling, the warm water volume, the satellite floors, daily wind and bursts, the MJO, the other indices.',
      trend: 'Dynamics: the daily series with records and the 14-day analogue forecast, our own index against past events, the background of ocean heat.',
      regions: 'What it means where you live: 17 regions by season and scenario; the Gulf measured directly.',
      food: 'Food: the FAO index, its path since the onset against past events, and the commodities by name.',
      how: 'Glossary, method and parameters, sources with their freshness, the release calendar, what changed.',
      chain: 'The chain of data end to end: sources, collectors, computed states, outputs — with the freshness of every piece.',
      refs: 'One register of everything this panel rests on: the papers we parsed and attached, the data sources, the literature quoted — each with a link and where it is used.',
      about: 'What this panel is, what it does and does not claim, and how to read it.',
      state: 'The state column: the risk index, the key numbers and the alerts.',
      risks: 'The board of risks with their levels, horizons and series.'
    },
    subHelp: {
      'verdict/now': 'Today\'s verdict.', 'verdict/history': 'Every verdict that actually changed, in order.',
      'now/analogs': 'Daily Niño 3.4 this year against the four strongest past events on the same days.', 'now/map': 'The four Niño boxes on the map, this week against the same week of a past event.',
      'now/weekly': 'The four weekly indices over the last weeks, with the same weeks of past events beside them.', 'now/weekly_a': 'One weekly index against the strongest events on the same calendar.',
      'ocean/surface': 'Daily box means from the NOAA grid, one day behind, with own climatologies.', 'ocean/moorings': 'Temperature by depth under the equator, mooring by mooring, every day.', 'ocean/section': 'The reanalysis section along the equator, monthly.',
      'models/plume': 'All models\' seasonal forecasts, the live-model centre, where we stand in the season.', 'models/stack': 'The last three issues, one under the other, against the same reality.', 'models/scoreboard': 'Each model against the official value it forecast.', 'models/breakdown': 'How many models fell below reality, issue by issue; the chronic ones.', 'models/revisions': 'How each model moved its peak between issues.',
      'air/coupling': 'The three atmospheric signs that the ocean and the air are coupled.', 'air/fuel': 'The warm water volume under the equator: the fuel gauge and its lead.', 'air/layers': 'The four satellite floors of the atmosphere and their delay.', 'air/wind': 'Daily zonal wind over the western Pacific and the westerly bursts.', 'air/mjo': 'The Madden–Julian Oscillation: phase and amplitude.', 'air/indices': 'MEI, the Indian Ocean Dipole and RONI next to our coupling score.',
      'trend/sst_nino34': 'Niño 3.4 daily: 400 days, the band of all years, the 14-day forecast, where past events went from here.', 'trend/sst_world': 'The world ocean, daily.', 'trend/t2_world': 'Land and ocean, daily.', 'trend/index': 'Our risk index by update, and the comparable core against past events.', 'trend/months': 'Thirteen months of the three series with their ranks.', 'trend/background': 'Ocean heat content and the energy imbalance: the state of the whole system.',
      'regions/table': 'Every region by season and scenario, with food vulnerability and what to do.', 'regions/place': 'One region at a time; the Gulf with its own measurements.',
      'food/prices': 'The FAO index and its five groups.', 'food/onset': 'The index, or one commodity, as a percentage of the onset month, against past events.', 'food/goods': 'Twelve commodities by name: price, month, year, since the onset.',
      'how/glossary': 'Every underlined term explained.', 'how/method': 'How things are computed, and which numbers are parameters.', 'how/sources': 'Every source, whether it answered, and when its data last changed.', 'how/calendar': 'When each source publishes next.', 'how/changed': 'What changed since the previous update.'
    },
    railTabs: { state: 'State', risks: 'Risks' },
    dockHint: 'Point at anything underlined — definition, source and date appear here.',
    okC: 'keeping up', lagC: 'lagging', brokeC: 'broken', naC: 'no data',
    months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  };
  var MONTHS = T.months;
  var ME = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366];
  var STEP = { day: { one: 'last day', many: 'days' }, week: { one: 'last week', many: 'weeks' }, issue: { one: 'last issue', many: 'issues' } };
  var SERIES_NAME = { sst_nino34: 'Niño 3.4', sst_world: 'world ocean', t2_world: 'land+ocean' };

  var S = {
    D: null, G: {}, H: [], P: null, M: {}, L: {},
    view: 'now', sub: {}, risk: null, model: null, scenario: null, pick: null, region: null,
    // Режим сравнения: '' — показываем значения, 'update' — изменение с прошлого прогона,
    // 'week' — с ближайшего снимка недельной давности (владелец 03.09: «было/стало от
    // последней недели»). Кнопка в шапке перебирает три состояния.
    delta: '',
    draw: null, plotEl: null, pinned: null
  };

  // ---------------------------------------------------------------- utils
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fin(v) { return typeof v === 'number' && isFinite(v); }
  function fnum(v, d, sign) {
    if (!fin(v)) return '—';
    d = d == null ? 2 : d;
    var s = Math.abs(v).toFixed(d);
    return sign === false ? (v < 0 ? '−' : '') + s : (v > 0 ? '+' : (v < 0 ? '−' : '')) + s;
  }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function term(key, text) { return '<span data-term="' + esc(key) + '">' + esc(text) + '</span>'; }
  /* ЗОНА — НЕ ЧИСЛО. Владелец 04.09: «наши номера зон типа 1+2, 3.4 путаются с температурами,
     если рядом в строках; писать в рамочке, с префиксом, чтобы понятно было, что это зона».
     Код зоны идёт в рамке, моноширинным, с буквой Z впереди: «Z3.4» уже не прочитать как
     «плюс три и четыре». Подсказка по наведению остаётся прежней. */
  var ZONES = { nino12: '1+2', nino3: '3', nino34: '3.4', nino4: '4' };
  function zone(key) {
    return '<span class="zn" data-term="' + esc(key) + '">Niño&nbsp;' + esc(ZONES[key] || '') + '</span>';
  }

  /* Владелец 03.09: «ещё много понятий не подсвечено, например Niño 3, CPC MRKOV (9/9),
     надо описание моделей». Термины и имена моделей помечаются прямо в готовом тексте:
     длинные образцы идут первыми (Niño 3.4 раньше Niño 3), помечается первое вхождение —
     подчёркнутая строка в каждом предложении читается хуже, чем непомеченная. */
  var TERMS = [
    ['Niño 3.4', 'nino34'], ['Niño 1+2', 'nino12'], ['Niño 3', 'nino3'], ['Niño 4', 'nino4'],
    ['La Niña', 'lanina'], ['El Niño', 'elnino'], ['ONI', 'oni'], ['CUSUM', 'cusum'],
    ['OISST', 'oisst'], ['ERA5', 'era5'], ['SOI', 'soi'], ['FAO', 'fao'],
    ['teleconnections', 'teleconnection'], ['teleconnection', 'teleconnection'],
    ['percentile', 'percentile'], ['plume', 'plume'], ['Modoki', 'type'],
    ['analogues', 'analog'], ['analogue', 'analog'], ['p10', 'p10p50p90'],
    ['net importers', 'importer'], ['risk index', 'riskindex'],
    // добавлено 04.09 вместе с блоком «воздух»: длинные образцы раньше коротких
    ['warm water volume', 'wwv'], ['upper 300 m', 't300'],
    ['outgoing longwave radiation', 'olr'], ['convection', 'olr'],
    ['trade winds', 'u850'], ['trade wind', 'u850'],
    ['coupling', 'coupling'], ['Pink Sheet', 'pinksheet'], ['World Bank', 'pinksheet'],
    // имена источников: длинные раньше коротких, иначе «NOAA CPC» съест «NOAA»
    ['NOAA CPC', 'cpc'], ['CPC', 'cpc'], ['PMEL', 'pmel'], ['TAO', 'pmel'],
    ['UAH', 'uah'], ['IRI', 'iri'], ['ERSST', 'ersst'], ['GIEWS', 'giews'],
    ['lower troposphere', 'tlt'], ['troposphere', 'tlt'], ['stratosphere', 'tlt']
  ];
  function mark(text) {
    var out = esc(text == null ? '' : text), used = {};
    TERMS.forEach(function (t) {
      if (used[t[1]] || !S.G[t[1]]) return;
      // имя зоны в тексте — та же рамка: «Niño 1+2 +4.2» иначе читается как два числа подряд
      if (ZONES[t[1]] && t[0].indexOf('Niño') === 0) {
        var iZ = out.indexOf(t[0]);
        if (iZ >= 0) { out = out.slice(0, iZ) + zone(t[1]) + out.slice(iZ + t[0].length); used[t[1]] = 1; }
        return;
      }
      var i = out.indexOf(t[0]);
      if (i < 0 || out.lastIndexOf('<', i) > out.lastIndexOf('>', i)) return;
      used[t[1]] = 1;
      out = out.slice(0, i) + '<span data-term="' + t[1] + '">' + t[0] + '</span>' + out.slice(i + t[0].length);
    });
    // Имена моделей: их описания живут в data/enso/models-ref.json, а измеренное поведение
    // (класс, средняя ошибка, сколько выпусков ниже реальности) подставляется из наших данных.
    Object.keys(S.M.models || {}).sort(function (a, b) { return b.length - a.length; }).forEach(function (nm) {
      var i = out.indexOf(nm);
      if (i < 0 || out.lastIndexOf('<', i) > out.lastIndexOf('>', i)) return;
      out = out.slice(0, i) + modelSpan(nm, nm) + out.slice(i + nm.length);
    });
    return out;
  }
  function modelSpan(nm, text) {
    var m = (S.M.models || {})[nm] || {}, iri = S.D.iri || {}, c = (iri.classes || {})[nm] || {};
    var bd = (iri.breakdown || {}).chronic || [];
    var row = bd.filter(function (x) { return x.model === nm; })[0] || {};
    var kind = (S.M.kinds || {})[((iri.models || {})[nm] || {}).section] || '';
    var perf = [];
    if (c.cls) perf.push('Our class for it: ' + ({ ok: T.okC, lag: T.lagC, broke: T.brokeC }[c.cls] || T.naC) + (c.since ? ', since the ' + c.since + ' issue' : '') + '.');
    if (fin(c.mean_err)) perf.push('Mean error against the official ONI on the seasons we can check: ' + fnum(c.mean_err) + ' °C.');
    if (row.of) perf.push('Below reality in ' + row.issues_low + ' of ' + row.of + ' verified issues.');
    if (c.last2 && c.last2.length) perf.push('Last checked issues: ' + c.last2.map(function (e) { return e.issue + ' ' + fnum(e.err) + ' °C'; }).join(', ') + (c.trend ? ' — ' + c.trend : '') + '.');
    var pay = { name: nm + (m.org ? ' · ' + m.org : ''), def: (m.note ? m.note + ' ' : '') + kind, why: perf.join(' '),
      src: (S.M.src || 'IRI plume'), date: iri.issued };
    /* ПЛАШКА У МОДЕЛИ, КАК У ЗОНЫ, НО ДРУГОЙ ФОРМЫ. Владелец 04.09: «модели тоже в плашки
       собери, у нас зоны в плашках — так же, только форму поменяй, по всему дашборду».
       Зона — скруглённая пилюля цвета охры; модель — прямоугольная рамка холодного цвета
       с классом внутри (справляется / отстаёт / сломана). Так их не спутать между собой и
       ни ту, ни другую не спутать с числом. */
    var cls2 = c.cls ? ' ' + c.cls : '';
    return '<span class="mn' + cls2 + '" data-src="' + esc(JSON.stringify(pay)) + '">' + esc(text) + '</span>';
  }
  /* ИСТОЧНИКИ — СЛОВАМИ И ССЫЛКАМИ. Владелец 04.09 (вечер): «на названии региона сначала всё
     понятно, а потом идёт какой-то текст из ссылок и всего подряд — какой в том смысл; если
     ссылки — делать ссылками на внешние источники». Строка источников склеивалась через « · »
     в одну простыню; адрес без пробелов давал горизонтальную прокрутку. Теперь каждый
     источник — своей строкой, а адрес в нём — живой ссылкой на домен. */
  var SRC_RX = /((?:https?:\/\/)?(?:[a-z0-9-]+\.)+(?:gov|org|edu|int|com|net|academy|info|au|uk|eu)(?:\/[^\s,;)]*)?)/i;
  function srcHtml(s0) {
    if (!s0) return '';
    return String(s0).split(' · ').filter(Boolean).map(function (t) {
      var m = SRC_RX.exec(t);
      if (!m) return '<div>' + esc(t) + '</div>';
      var url = m[1], href = /^https?:/i.test(url) ? url : 'https://' + url;
      var label = t.slice(0, m.index).replace(/[,;\s]+$/, '');
      var dom = url.replace(/^https?:\/\//i, '').split('/')[0];
      return '<div>' + esc(label || dom) + ' <a href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(dom) + ' ↗</a></div>';
    }).join('');
  }
  function src(payload, text) { return '<span data-src="' + esc(JSON.stringify(payload)) + '">' + esc(text) + '</span>'; }
  function addDays(iso, n) { var d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function lvlColor(l) { return 'var(--lv' + Math.max(1, Math.min(5, l)) + ')'; }
  function upDown(v) { return v > 0 ? 'up' : (v < 0 ? 'dn' : ''); }
  function ord(n) { var s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }
  function sub(view, def) { return S.sub[view] || def; }
  function prevStamp() { return (S.P && S.P.stamp) || 'the previous update'; }

  /* База сравнения по режиму. Прошлый прогон лежит в latest.prev целиком; «неделя назад» —
     ближайший снимок не новее семи дней, из history.json (там с этого прогона есть уровни
     рисков и ключевые числа). */
  function baseline() {
    if (S.delta === 'week') {
      var rows = (S.H || []).filter(function (r) { return r.date; });
      if (rows.length < 2) return null;
      var last = rows[rows.length - 1].date;
      var want = new Date(last + 'T00:00:00Z'); want.setUTCDate(want.getUTCDate() - 7);
      var iso = want.toISOString().slice(0, 10);
      var pick = null;
      rows.forEach(function (r) { if (r.date <= iso) pick = r; });
      if (!pick) pick = rows[0];
      if (pick.stamp === (S.D || {}).stamp) return null;
      return { stamp: pick.stamp || pick.date, risk_index: pick.risk_index, risks: pick.risks || {},
        noaa: { n34a: pick.n34_weekly_prev }, daily: { sst_nino34: pick.n34_daily, sst_world: pick.sst_world, t2_world: pick.t2_world },
        food_index: pick.food_index, class_tally: pick.class_tally, iri_peak: pick.combined_peak,
        iri_below: pick.n_below, iri_n: pick.n_models, week: true };
    }
    return S.delta === 'update' ? S.P : null;
  }

  /* «Сейчас» или «что изменилось»: одно число показывается двумя способами, переключатель
     в шапке. Возвращает {big, small} — крупное значение и подпись под ним. */
  function pair(now, before, d, unit) {
    d = d == null ? 2 : d;
    var has = fin(before) && fin(now);
    var ch = has ? now - before : null;
    if (S.delta && has) {
      return { big: '<span class="' + upDown(ch) + '">' + fnum(ch, d) + '</span>' + (unit ? '<small>' + unit + '</small>' : ''),
        small: 'now ' + fnum(now, d) + ', was ' + fnum(before, d) + ' at ' + esc(prevStamp()) };
    }
    return { big: fnum(now, d) + (unit ? '<small>' + unit + '</small>' : ''),
      small: has ? (ch === 0 ? 'unchanged since ' + esc(prevStamp()) : '<span class="' + upDown(ch) + '">' + fnum(ch, d) + '</span> since ' + esc(prevStamp())) : '' };
  }
  function chg(now, before, d) {
    if (!fin(now) || !fin(before)) return '';
    var c = now - before;
    return '<span class="' + upDown(c) + '">' + (c === 0 ? '=' : fnum(c, d == null ? 2 : d)) + '</span>';
  }

  // ---------------------------------------------------------------- svg helpers
  /* ЗАГОЛОВОК ПО ШИРИНЕ. Текст в SVG не переносится и не обрезается сам: на телефоне
     подписи графиков уезжали за правый край. Считаем, сколько знаков влезает при нашем
     моноширинном кегле, и режем по слову с многоточием. */
  function fitText(text, w, px) {
    var max = Math.max(8, Math.floor((w - 60) / ((px || 12) * .58)));
    if (!text || text.length <= max) return text || '';
    var cut = text.slice(0, max - 1), sp = cut.lastIndexOf(' ');
    return (sp > max * .5 ? cut.slice(0, sp) : cut) + '…';
  }
  function svgOpen(w, h) { return '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img">'; }
  function poly(pts, color, w, op, dash) {
    var s = pts.filter(function (p) { return fin(p[0]) && fin(p[1]); }).map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    return '<polyline points="' + s + '" fill="none" style="stroke:' + color + '" stroke-width="' + (w || 1.2) + '" opacity="' + (op == null ? 1 : op) + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + ' stroke-linejoin="round"/>';
  }
  /* ЛИНИЯ УЗНАЁТСЯ ПО ШТРИХУ, А НЕ ПО ЦВЕТУ. Владелец 04.09: «линии я не понимаю, цвета
     мне нужны пунктиры лучше везде, где можно». Цвет остаётся, но различать ряды можно и
     без него: у каждого ряда свой рисунок штриха, и он одинаков на всех графиках панели —
     сплошная это всегда «главное/сейчас», а прошлые события идут пунктирами по возрастанию
     длины штриха. Это же спасает при печати, на плохом экране и при дальтонизме. */
  var DASH = ['', '5 3', '2 2', '8 3 2 3', '1 3', '6 2 1 2'];
  function dashOf(i) { return DASH[i % DASH.length]; }

  /* Расшифровка внутри поля, слева вверху: справа теперь стоят мини-графики прошлых
     событий, и место занято ими (владелец 04.09). */
  /* НАЖИМАЕМАЯ ЛЕГЕНДА ВЕЗДЕ. Владелец 04.09 (вечер): «я дальтоник — графики разными
     пунктирами; легенды лучше делать нажимающимися: нажал на строчку — подсветился график».
     Пятый элемент строки — ключ ряда; клик по строке выделяет ряд, остальные бледнеют
     (обработчик один, на поле графика: plot()). Штрих в легенде тот же, что у линии. */
  function pickOp(key, base) {
    base = base == null ? 1 : base;
    return (!S.pick || S.pick === key) ? base : base * 0.15;
  }
  /* ЛЕГЕНДА ЗНАЧКОМ. Владелец 06.09: «легенды везде сделать иконкой и открывать в
     тултипе, чтобы не захламлять: и так тут мало места». Значок — обычный якорь подсказки
     панели (data-src), список рядов идёт готовой разметкой, с цветом каждой линии. */
  function legIcon(items, W) {
    /* Список рядов в подсказке — той же формы, что легенда на большом графике: слева штрих
       нужного цвета и вида (сплошной, пунктир, точка), справа подпись. Рисуем крошечными
       svg, чтобы не заводить новых стилей и чтобы подсказка не прокручивалась. */
    var rows = items.filter(function (it) { return it && it[0]; }).map(function (it) {
      var col = it[1] || 'var(--soft)', wid = it[2] || 1.4, dash = it[3] || '';
      var mark = it[2] === 'dot'
        ? '<circle cx="11" cy="7" r="3.4" style="fill:' + col + '"/>'
        : '<line x1="1" y1="7" x2="21" y2="7" style="stroke:' + col + '" stroke-width="' + (it[2] === 'dot' ? 1.4 : wid) + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + '/>';
      return '<span class="leg-row"><svg viewBox="0 0 22 14" width="22" height="14" aria-hidden="true">' + mark + '</svg>' + esc(String(it[0])) + '</span>';
    }).join('');
    var pay = { name: 'What the lines are', html: '<span class="leg-list">' + rows + '</span>' };
    /* Метка живёт НЕ в картинке, а в строке названия карточки (владелец 06.09: «метку
       legend поднять, где название карточки»). Здесь только складываем список — плитка
       заберёт его после отрисовки и повесит метку рядом с заголовком. */
    if (S._tight) { S._legend = pay; return ''; }
    var w = 44, x = W - w - 4;
    return '<g class="leg-i" data-src="' + esc(JSON.stringify(pay)) + '">' +
      '<rect x="' + x + '" y="4" width="' + w + '" height="13" rx="6.5" style="fill:var(--surface);stroke:var(--soft)" stroke-width=".9" opacity=".95"/>' +
      '<text x="' + (x + w / 2) + '" y="13.5" text-anchor="middle" font-size="8.5" style="fill:var(--soft);letter-spacing:.06em">legend</text></g>';
  }

  /* Шкала цвета у разрезов и подписи слоёв — та же легенда, только рисуется прямо в поле
     графика. В плитке её нет места: отдаём тем же путём, что и обычную легенду. */
  function scaleLegend(rows) {
    if (!S._tight) return false;
    S._legend = { name: 'What the colours are', html: '<span class="leg-list">' + rows.map(function (r) {
      return '<span class="leg-row"><svg viewBox="0 0 22 14" width="22" height="14" aria-hidden="true">' +
        (r[2] === 'line' ? '<line x1="1" y1="7" x2="21" y2="7" style="stroke:' + r[1] + '" stroke-width="2"' + (r[3] ? ' stroke-dasharray="5 3"' : '') + '/>'
                         : '<rect x="1" y="2" width="20" height="10" rx="2" style="fill:' + r[1] + '" opacity="' + (r[3] || 1) + '"/>') +
        '</svg>' + esc(String(r[0])) + '</span>';
    }).join('') + '</span>' };
    return true;
  }

  function legendAt(items, x, y) {
    if (S._tight) return legIcon(items, S._tightW || 300);
    return items.map(function (it, i) {
      var yy = y + i * 13, key = it[4];
      var op = key && S.pick && S.pick !== key ? ' opacity=".35"' : '';
      var open = key ? '<g data-pick="' + esc(key) + '" class="pick' + (S.pick === key ? ' on' : '') + '"' + op + ' style="cursor:pointer">' : '<g>';
      return open + (key ? '<rect x="' + (x - 2) + '" y="' + (yy - 7) + '" width="' + (26 + it[0].length * 5.8) + '" height="14" style="fill:transparent"/>' : '') +
        '<line x1="' + x + '" y1="' + yy + '" x2="' + (x + 18) + '" y2="' + yy +
        '" style="stroke:' + it[1] + '" stroke-width="' + (it[2] || 1.4) + '"' +
        (it[3] ? ' stroke-dasharray="' + it[3] + '"' : '') + '/>' +
        '<text x="' + (x + 24) + '" y="' + (yy + 3.5) + '" font-size="10">' + it[0] + '</text></g>';
    }).join('');
  }
  /* Штриховка для отрицательных значений на тепловых картах и столбиках: знак виден и без цвета. */
  function hatchDefs() {
    return '<defs><pattern id="hneg" patternUnits="userSpaceOnUse" width="6" height="6"><path d="M0 6 L6 0" style="stroke:var(--ink)" stroke-width="1" opacity=".55"/></pattern></defs>';
  }

  function segs(pts, color, w, op, dash) {
    var out = [], cur = [];
    pts.forEach(function (p) { if (fin(p[0]) && fin(p[1])) cur.push(p); else { if (cur.length > 1) out.push(poly(cur, color, w, op, dash)); cur = []; } });
    if (cur.length > 1) out.push(poly(cur, color, w, op, dash));
    return out.join('');
  }
  /* ПРЕДОХРАНИТЕЛЬ НА СЕТКЕ. Ряд карточки риска может быть в каких угодно единицах — у
     тёплого объёма воды это кубометры, то есть числа порядка 10¹⁵. Шаг сетки подбирался
     под градусы (0.25…1), и цикл честно пытался нарисовать несколько триллионов линий:
     страница вставала на пять секунд (владелец 04.09: «при переключении рисков заметное
     подвисание, где-то прям залипает»). Теперь шаг, если он не годится, пересчитывается
     под размах ряда, и линий не бывает больше двенадцати — при любых единицах. */
  function niceStep(span, want) {
    var raw = span / Math.max(2, want || 6);
    if (!(raw > 0) || !isFinite(raw)) return 1;
    var mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
    var n = raw / mag;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * mag;
  }
  /* Подпись деления: у больших единиц (кубометры воды) обычная запись не помещается и
     ничего не сообщает — показываем порядок, как в науке: 2.7e15. */
  function gridLabel(g, step, dg) {
    if (Math.abs(g) >= 1e4) {
      var e = Math.floor(Math.log(Math.abs(g)) / Math.LN10);
      return (g / Math.pow(10, e)).toFixed(1) + 'e' + e;
    }
    return fnum(g, dg == null ? (step < 0.5 ? 2 : 1) : dg);
  }
  function gridY(vmin, vmax, step, Y, L, R, W, dg) {
    var span = vmax - vmin;
    if (!(step > 0) || span / step > 12) step = niceStep(span, 6);
    /* ЛИНИЙ СТОЛЬКО, СКОЛЬКО ЧИТАЕТСЯ. В плитке обзора шаг, выбранный для большого поля,
       давал два десятка подписей на 150 пикселей высоты, и они наезжали друг на друга
       сплошной колонкой цифр (владелец 06.09: «чтобы ничего не сливалось»). Считаем шаг от
       ВЫСОТЫ: подписи не ближе четырнадцати пикселей друг к другу. */
    var hpx = Math.abs(Y(vmin) - Y(vmax));
    if (hpx > 10) {
      var maxLines = Math.max(3, Math.floor(hpx / 22));
      while (span / step > maxLines) step *= 2;
    }
    var s = '', g = Math.floor(vmin / step) * step, guard = 0;
    for (; g < vmax && guard < 40; g += step, guard++) {
      var zero = Math.abs(g) < 1e-9;
      s += '<line x1="' + L + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width="' + (zero ? 1.3 : 0.6) + '"/>';
      s += '<text x="' + (L - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + gridLabel(g, step, dg) + '</text>';
    }
    return s;
  }
  /* Колонка легенды шире и с запасом: подписи справа выезжали за поле (владелец 05.09:
     «сделай отступ резервный, не жмись»). */
  /* ЖИВАЯ ТОЧКА «ГДЕ МЫ СЕЙЧАС». Владелец 05.09: «пусть мигает, концентрические круги,
     чтобы красиво». Сама точка стоит на месте — читать значение по ней должно быть можно;
     от неё расходятся два кольца со сдвигом по фазе (CSS, transform на fill-box, поэтому
     работает и внутри масштабируемого svg; при prefers-reduced-motion гаснет вся анимация). */
  function nowDot(x, y, color, r) {
    r = r || 4.5;
    var c = 'cx="' + (+x).toFixed(1) + '" cy="' + (+y).toFixed(1) + '" r="' + r + '"';
    return '<circle class="ring" ' + c + ' style="stroke:' + color + '"/><circle class="ring r2" ' + c + ' style="stroke:' + color + '"/>' +
      '<circle class="now-dot" ' + c + ' style="fill:' + color + '"/>';
  }
  function legendW(w) { return w < 560 ? 0 : Math.min(240, Math.round(w * 0.27)); }
  /* Верхний отступ поля графика. В тесном режиме (плитка обзора) легенды в картинке нет —
     она уехала в метку и подсказку, и держать под неё 42 пикселя незачем: именно этот
     зазор владелец 06.09 назвал «огромным между названием и графиком». */
  function topPad(w) { return S._tight ? 16 : (legendW(w) ? 26 : 42); }
  /* КЛИКАБЕЛЬНАЯ ЛЕГЕНДА. Владелец 04.09: «все линии тоже нужно дать легенду по моделям,
     отдельно выделить визуально; при нажатии на элемент легенды график её высвечивать
     отдельно, остальные делать блёклыми». Пятый элемент строки — имя того, что выделяем:
     класс моделей или конкретная модель. Обработчик один, на поле графика. */
  function legend(items, w, h, R, top) {
    if (S._tight) return legIcon(items, w);
    var s = '', i;
    if (R > 0) {
      var ly = top + 4, maxCh = Math.max(8, Math.floor((R - 40) / 6.3));
      for (i = 0; i < items.length; i++) {
        var it = items[i].slice();
        if (it[0] === '' || it[0] == null) { ly += 7; continue; }   // пустая строка отделяет нажимаемое от справочного
        if (it[0] && it[0].length > maxCh) it[0] = it[0].slice(0, maxCh - 1) + '…';   // не вылезать за поле (владелец 05.09)
        var tag = it[4] ? ' data-pick="' + esc(it[4]) + '" class="pick' + (S.pick === it[4] ? ' on' : '') + '"' : '';
        if (tag) s += '<g' + tag + '>';
        if (it[4] && S.pick === it[4]) s += '<rect x="' + (w - R + 2) + '" y="' + (ly - 1) + '" width="' + (R - 4) + '" height="15" rx="4" style="fill:var(--ochre)" opacity=".14"/>';
        if (it[2] === 'dot') s += '<circle cx="' + (w - R + 18) + '" cy="' + (ly + 4) + '" r="4" style="fill:' + it[1] + '"/>';
        else s += '<line x1="' + (w - R + 8) + '" y1="' + (ly + 4) + '" x2="' + (w - R + 28) + '" y2="' + (ly + 4) + '" style="stroke:' + it[1] + '" stroke-width="' + (it[2] || 2) + '"' + (it[3] ? ' stroke-dasharray="' + it[3] + '"' : '') + '/>';
        s += '<text x="' + (w - R + 34) + '" y="' + (ly + 8) + '"' + (it[4] ? ' style="cursor:pointer"' : '') + '>' + esc(it[0]) + '</text>';
        if (it[4]) s += '<rect x="' + (w - R + 4) + '" y="' + ly + '" width="' + (R - 6) + '" height="15" style="fill:transparent;cursor:pointer"/></g>';
        ly += 16;
      }
      return s;
    }
    var x = 46;
    for (i = 0; i < items.length; i++) {
      s += '<rect x="' + x + '" y="' + (top - 14) + '" width="12" height="4" style="fill:' + items[i][1] + '"/>';
      s += '<text x="' + (x + 16) + '" y="' + (top - 10) + '" font-size="10">' + esc(items[i][0]) + '</text>';
      x += 22 + esc(items[i][0]).length * 5.6;
    }
    return s;
  }

  // ---------------------------------------------------------------- charts
  function chartRecent(w, W, H) {
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 46, ph = H - Tp - B;
    var rec = w.recent, n = rec.length, idx = w.last_idx;
    var cal = []; for (var i = 0; i < n; i++) cal.push(((idx - (n - 1 - i)) % 366 + 366) % 366);
    function fill(a) {
      var b = a.map(function (v) { return fin(v) ? v : NaN; });
      for (var j = 0; j < b.length; j++) if (!fin(b[j])) { var lo = j ? b[j - 1] : NaN, hi = j + 1 < b.length ? b[j + 1] : NaN; b[j] = fin(lo) && fin(hi) ? (lo + hi) / 2 : (fin(lo) ? lo : hi); }
      return b;
    }
    var B10 = fill(w.band_p10), B90 = fill(w.band_p90), BMAX = fill(w.band_max), BMIN = fill(w.band_min);
    var p10 = cal.map(function (c) { return B10[c]; }), p90 = cal.map(function (c) { return B90[c]; });
    var bmax = cal.map(function (c) { return BMAX[c]; }), bmin = cal.map(function (c) { return BMIN[c]; });
    var f = w.forecast14;
    /* ПРОДОЛЖЕНИЕ НА ГОД ВПРАВО. Владелец 04.09: «в dynamics продли вправо исторические
       данные, чтобы видно было развитие ещё на год». Данных из будущего не бывает, поэтому
       вправо уходит не наш ряд, а прошлые события: что делал этот же показатель у них через
       столько же дней. Для Niño 3.4 такие ряды есть (они же на «Against analogues»); для
       мирового океана и суши их нет, и там график остаётся прежним — врать нечем. */
    var AF = w.analog_forward || null, FW = AF ? 365 : 0;
    var vals = rec.filter(fin).concat(bmax.filter(fin), bmin.filter(fin), [f.p90, f.p10]);
    if (AF) Object.keys(AF).forEach(function (y) { vals = vals.concat((AF[y] || []).filter(fin)); });
    var vmin = Math.min.apply(null, vals) - .05, vmax = Math.max.apply(null, vals) + .25;
    var X = function (i) { return Lp + i / (n - 1 + 14 + FW) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + fitText(esc(w.label) +
      (AF ? ' \u2014 and where past events went from this same day' : ''), W, 12) + '</text>';
    if (AF) {
      var kf = 0;
      Object.keys(AF).sort().forEach(function (y) {
        kf++;
        var seq = AF[y] || [];
        s += segs(seq.map(function (v, i2) { return [X(n - 1 + i2), fin(v) ? Y(v) : NaN]; }),
          'var(--a' + y + ')', 1.1, pickOp(y, .85), dashOf(kf));
      });
      s += '<line x1="' + X(n - 1).toFixed(1) + '" y1="' + Tp + '" x2="' + X(n - 1).toFixed(1) + '" y2="' + (H - B) +
        '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="2 3" opacity=".7"/>';
    }
    s += gridY(vmin, vmax, vmax - vmin < 2 ? .25 : .5, Y, Lp, R + 46, W);
    function band(lo, hi, op) {
      var up = [], dn = [];
      for (var i = 0; i < n; i++) if (fin(hi[i])) up.push(X(i).toFixed(1) + ',' + Y(hi[i]).toFixed(1));
      for (var j = n - 1; j >= 0; j--) if (fin(lo[j])) dn.push(X(j).toFixed(1) + ',' + Y(lo[j]).toFixed(1));
      return '<polygon points="' + up.join(' ') + ' ' + dn.join(' ') + '" style="fill:var(--band)" opacity="' + op + '"/>';
    }
    s += band(bmin, bmax, pickOp('band', .22)) + band(p10, p90, pickOp('band', .38));
    for (var i2 = 0; i2 < n; i2++) {
      var d = addDays(w.last_date, -(n - 1 - i2));
      if (d.slice(8) === '01') {
        var mo = parseInt(d.slice(5, 7), 10);
        s += '<line x1="' + X(i2).toFixed(0) + '" y1="' + Tp + '" x2="' + X(i2).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--grid)" stroke-width=".5"/>';
        // подписи месяцев — через один на среднем поле и через два в плитке обзора,
        // иначе они стоят вплотную и читаются как одно слово (владелец 06.09)
        var mEvery = W > 620 ? 1 : (W > 400 ? 2 : 3);
        if (mo % mEvery === 0 || mEvery === 1) s += '<text x="' + (X(i2) + 2).toFixed(0) + '" y="' + (H - 10) + '">' + MONTHS[mo - 1] + (mo === 1 && !S._tight ? " '" + d.slice(2, 4) : '') + '</text>';
      }
    }
    s += segs(rec.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 1.8, pickOp('all'));
    s += segs(rec.slice(-30).map(function (v, i) { return [X(n - 30 + i), fin(v) ? Y(v) : NaN]; }), 'var(--nino)', 2.6, pickOp('last30'));
    // где стоял ряд на прошлом обновлении — линия «было»
    var pv = S.P && S.P.daily && S.P.daily[seriesKey(w)];
    if (fin(pv)) {
      s += '<line x1="' + Lp + '" y1="' + Y(pv).toFixed(1) + '" x2="' + (W - R - 46) + '" y2="' + Y(pv).toFixed(1) + '" style="stroke:var(--soft)" stroke-width="1" stroke-dasharray="2 4" opacity=".8"/>';
      s += '<text x="' + (Lp + 3) + '" y="' + (Y(pv) - 3).toFixed(0) + '" style="fill:var(--soft)">was ' + fnum(pv) + ' at ' + esc(prevStamp()) + '</text>';
    }
    var x0 = X(n - 1), x1 = X(n - 1 + 14);
    if (fin(rec[n - 1])) s += nowDot(x0, Y(rec[n - 1]), 'var(--nino)', 4);
    s += '<polygon points="' + x0.toFixed(1) + ',' + Y(f.from).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p90).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p10).toFixed(1) + '" style="fill:var(--nino)" opacity=".18"/>';
    s += poly([[x0, Y(f.from)], [x1, Y(f.p50)]], 'var(--nino)', 1.6, 1, '5 3');
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p90) + 3).toFixed(0) + '">' + fnum(f.p90) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p50) + 3).toFixed(0) + '" class="tt">' + fnum(f.p50) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p10) + 3).toFixed(0) + '">' + fnum(f.p10) + '</text>';
    var legR = [['last 30 days', 'var(--nino)', 2.6, '', 'last30'], ['400 days', 'var(--text)', 1.8, '', 'all'], ['10–90 % of all years', 'var(--band)', 6, '', 'band'], ['forecast +14 d', 'var(--nino)', 1.6, '5 3', 'fc']];
    if (AF) Object.keys(AF).sort().forEach(function (y, k2) { legR.push([y + ' from this day on', 'var(--a' + y + ')', 1.1, dashOf(k2 + 1), y]); });
    s += legend(legR, W, H, R, Tp);
    return s + '</svg>';
  }
  /* Сезон НА СЕГОДНЯ: среднее тех месяцев сезона, что уже измерены недельными данными.
     Владелец 03.09: «ASO это среднее, а сейчас 3 сентября, сравнивать надо относительно
     сегодня». Модель, чей трёхмесячный прогноз ниже прожитой части, уже не может быть права:
     остаток сезона должен был бы стать холоднее прожитого. */
  var SEASON_MONTHS = { DJF: [12, 1, 2], JFM: [1, 2, 3], FMA: [2, 3, 4], MAM: [3, 4, 5], AMJ: [4, 5, 6],
    MJJ: [5, 6, 7], JJA: [6, 7, 8], JAS: [7, 8, 9], ASO: [8, 9, 10], SON: [9, 10, 11], OND: [10, 11, 12], NDJ: [11, 12, 1] };
  function seasonTodate(label, year) {
    var mon = (S.D.noaa || {}).monthly || {}, wk = (S.D.noaa || {}).monthly_weeks || {};
    var months = SEASON_MONTHS[label];
    if (!months) return null;
    var vals = [], parts = [], y = year, prev = null;
    months.forEach(function (m) {
      if (prev != null && m < prev) y++;
      prev = m;
      var key = y + '-' + (m < 10 ? '0' : '') + m;
      if (fin(mon[key]) && (wk[key] || 0) >= 2) { vals.push(mon[key]); parts.push(key); }
    });
    if (!vals.length) return null;
    var sum = 0; vals.forEach(function (v) { sum += v; });
    return { season: label, value: Math.round(sum / vals.length * 100) / 100, done: vals.length, of: 3, parts: parts };
  }
  function issueYear(issued) { var m = /(\d{4})/.exec(issued || ''); return m ? parseInt(m[1], 10) : (new Date()).getUTCFullYear(); }

  function seriesKey(w) {
    for (var k in SERIES_NAME) if (S.D.watch[k] === w) return k;
    return null;
  }

  /* ПРОШЛЫЕ СОБЫТИЯ ОТДЕЛЬНЫМИ ПАНЕЛЯМИ. Владелец 04.09: «на where we are мини-графы бы
     тоже сделать со шкалой температур и, может, одна шкала на все внизу месяцы». В общем
     пучке четыре события накладываются друг на друга и различаются только цветом; в столбце
     справа у каждого своя панель, но шкала температур ОДНА на всех и та же, что у большого
     графика, — поэтому сравнивать можно глазом, а подписи месяцев внизу общие. */
  function chartAnalogs(N, W, H) {
    var years = Object.keys(N.analogs).sort();
    var RC = (W >= 640 && years.length) ? Math.max(110, Math.min(190, Math.round(W * .24))) : 0;
    var Lp = 46, R = RC ? 12 : legendW(W), Tp = topPad(W), B = 26;
    var pw = W - Lp - R - (RC ? RC + 14 : 8), ph = H - Tp - B, n = 366 + 120;
    var all = [];
    Object.keys(N.analogs).forEach(function (y) { all = all.concat(N.analogs[y].series.filter(fin), N.analogs[y].next.filter(fin)); });
    all = all.concat(N.current_series.filter(fin));
    var vmin = Math.min.apply(null, all) - .1, vmax = Math.max.apply(null, all) + .45;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">Niño 3.4 daily anomaly: ' + (N.year || '') + ' against the four strongest events</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R + 8, W, 1);
    for (var m = 0; m < 12; m++) if (W > 470 || m % 2 === 0) s += '<text x="' + X((ME[m] + ME[m + 1]) / 2).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + MONTHS[m] + '</text>';
    for (var m2 = 0; m2 < 4; m2++) if (W > 470) s += '<text x="' + X(366 + (ME[m2] + ME[m2 + 1]) / 2).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle" opacity=".55">' + MONTHS[m2] + '+1</text>';
    s += '<line x1="' + X(366).toFixed(0) + '" y1="' + Tp + '" x2="' + X(366).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="3 3"/>';
    var leg = [];
    Object.keys(N.analogs).sort().forEach(function (y, yi) {
      var a = N.analogs[y], ser = a.series.concat(a.next);
      s += segs(ser.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--a' + y + ')', 1.4, pickOp(y, .9), dashOf(yi + 1));
      // В узкой плитке легенда идёт строкой под заголовком: там помещается только год.
      leg.push([R ? (y + '→' + (parseInt(y, 10) + 1) + ': peak ' + fnum(a.peak)) : y, 'var(--a' + y + ')', 1.6, dashOf(yi + 1), y]);
    });
    s += segs(N.current_series.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 2.6, pickOp('now'));
    s += nowDot(X(N.day), Y(N.current_day), 'var(--nino)', 4.5);
    var pe = N.peak_estimate;
    // Черта рекорда и её подпись держатся внутри ОСНОВНОГО поля: справа теперь стоят
    // мини-панели, и подпись налезала прямо на них (владелец 04.09).
    var xEnd = Lp + pw;
    s += '<line x1="' + Lp + '" y1="' + Y(pe.hist_ceiling).toFixed(0) + '" x2="' + xEnd.toFixed(0) + '" y2="' + Y(pe.hist_ceiling).toFixed(0) + '" style="stroke:var(--nino)" stroke-width=".9" stroke-dasharray="6 4"/>';
    s += '<text x="' + (xEnd - 4).toFixed(0) + '" y="' + (Y(pe.hist_ceiling) - 4).toFixed(0) + '" text-anchor="end" style="fill:var(--nino)">record of the series ' + fnum(pe.hist_ceiling) + '</text>';
    if (RC) {
      var x0 = W - RC - 12, gap = 5, hh = (ph - gap * (years.length - 1)) / years.length;
      years.forEach(function (y, yi) {
        var a = N.analogs[y], top = Tp + yi * (hh + gap);
        var Ym = function (v) { return top + (vmax - v) / (vmax - vmin) * hh; };
        var Xm = function (i) { return x0 + 4 + i / (n - 1) * (RC - 8); };
        s += '<rect x="' + x0 + '" y="' + top.toFixed(1) + '" width="' + RC + '" height="' + hh.toFixed(1) + '" rx="5" style="fill:var(--ink)" opacity=".04"/>';
        var seq = (a.series || []).concat(a.next || []);
        s += segs(seq.map(function (v, i) { return [Xm(i), fin(v) ? Ym(v) : NaN]; }), 'var(--a' + y + ')', 1.2, pickOp(y, .95), dashOf(yi + 1));
        // наш ряд той же шкалой поверх — видно, где мы против них
        s += segs((N.current_series || []).map(function (v, i) { return [Xm(i), fin(v) ? Ym(v) : NaN]; }), 'var(--text)', 1, .8, '2 2');
        if (fin(a.peak)) s += '<line x1="' + (x0 + 4) + '" y1="' + Ym(a.peak).toFixed(1) + '" x2="' + (x0 + RC - 4) + '" y2="' + Ym(a.peak).toFixed(1) + '" style="stroke:var(--a' + y + ')" stroke-width=".8" stroke-dasharray="2 2" opacity=".8"/>';
        s += '<text x="' + (x0 + 4) + '" y="' + (top + 10) + '" class="tt" font-size="10" style="fill:var(--a' + y + ')">' + esc(y) + '</text>' +
          '<text x="' + (x0 + RC - 4) + '" y="' + (top + 10) + '" text-anchor="end" font-size="9" style="fill:var(--soft)">peak ' + fnum(a.peak, 1) + '</text>';
      });
      s += '<text x="' + (W - RC - 12) + '" y="' + (H - 9) + '" font-size="9" style="fill:var(--soft)">same months, same scale</text>';
    }
    // Расшифровка налезала на мини-панели: в правом поле теперь живут они. Когда панели
    // показаны, легенда уходит внутрь графика, слева вверху (владелец 04.09).
    var legItems = [[(N.year || 'now') + ' — now', 'var(--text)', 2.6, '', 'now']].concat(leg);
    if (RC) s += legendAt(legItems, Lp + 8, Tp + 12);
    else s += legend(legItems, W, H, R, Tp);
    return s + '</svg>';
  }

  /* НЕДЕЛЬНЫЕ ИНДЕКСЫ + ПРОШЛЫЕ СОБЫТИЯ РЯДОМ. Владелец 04.09: «хорошо бы по прошлым важным
     событиям сделать такие же графики, небольшие справа, где сейчас расшифровка, в колонку;
     расшифровку слева вверху». Мини-панели рисуют ТЕ ЖЕ четыре индекса теми же штрихами и
     в той же шкале по вертикали — поэтому сравнивать можно глазом, не пересчитывая: видно,
     что в 1982 и 2015 восточные индексы шли низко, а 1997 единственный поднимал Niño 1+2
     так же круто, как сейчас. */
  function chartNoaa(NW, W, H, mode) {
    if (mode === 'analog') return chartNoaaAnalog(NW, W, H);
    var ser = NW.series, n = ser.length;
    var keys = [['n12a', 'Niño 1+2', 'var(--lv5)'], ['n3a', 'Niño 3', 'var(--nino)'], ['n34a', 'Niño 3.4', 'var(--text)'], ['n4a', 'Niño 4', 'var(--nina)']];
    var years = Object.keys(NW.analog_series || {}).sort();
    var RC = (W >= 620 && years.length) ? Math.max(120, Math.min(200, Math.round(W * .27))) : 0;
    var Lp = 46, R = 12, Tp = topPad(W), B = 26;
    var pw = W - Lp - R - RC - (RC ? 16 : 0), ph = H - Tp - B;
    var all = []; ser.forEach(function (r) { keys.forEach(function (k) { if (fin(r[k[0]])) all.push(r[k[0]]); }); });
    years.forEach(function (y) { (NW.analog_series[y] || []).forEach(function (r) { keys.forEach(function (k) { if (fin(r[k[0]])) all.push(r[k[0]]); }); }); });
    var vmin = Math.min.apply(null, all) - .2, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">NOAA weekly indices, last ' + n + ' weeks (anomaly, °C)' + (RC ? ' — and the same four, over their last ' + ((NW.analog_series[years[0]] || []).length || '') + ' weeks to the same week of the year, in the strongest past events' : '') + '</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, RC + R + 16, W, 1);
    /* Подписи месяцев ставим не «каждый первый в месяце», а столько, сколько влезает: в
       плитке обзора шириной 240 их выходило семь подряд и они слипались в кашу (владелец
       06.09: «внизу сливаются даты»). Шаг считаем от ширины поля: месяц занимает 26 пикселей. */
    /* Считаем не «через сколько месяцев», а РАССТОЯНИЕ в пикселях до предыдущей подписи:
       ширина поля у этого графика зависит от режима (у сравнения с сильнейшими справа стоит
       колонка панелей), и формула по ширине давала подписи в тринадцати пикселях друг от
       друга при ширине слова в двадцать (владелец 06.09: «внизу всё равно сливается ось»). */
    var lastLabelX = -1e9, monthEvery = 1;
    ser.forEach(function (r, i) {
      if (parseInt(r.date.slice(8), 10) > 7) return;
      var xx = X(i);
      if (xx - lastLabelX < 34) return;
      monthEvery = (xx - lastLabelX) < 70 ? 3 : 1;   // подписи редкие — значит это сезоны
      lastLabelX = xx;
      /* Через три месяца подписываем сезон тремя заглавными — JAS, ASO, как во всей
         панели: три полных названия подряд всё равно слипались (владелец 06.09). */
      var mi = parseInt(r.date.slice(5, 7), 10) - 1;
      var lab = monthEvery >= 3
        ? (MONTHS[mi] || '').charAt(0) + (MONTHS[(mi + 1) % 12] || '').charAt(0) + (MONTHS[(mi + 2) % 12] || '').charAt(0)
        : MONTHS[mi];
      s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + lab + '</text>';
    });
    keys.forEach(function (k, ki) { s += segs(ser.map(function (r, i) { return [X(i), fin(r[k[0]]) ? Y(r[k[0]]) : NaN]; }), k[2], k[0] === 'n34a' ? 2.2 : 1.4, pickOp(k[0]), dashOf(ki)); });
    s += legendAt(keys.map(function (k, ki) {
      return [k[1] + ' ' + fnum(NW.latest[k[0]], 1), k[2], k[0] === 'n34a' ? 2.2 : 1.4, dashOf(ki), k[0]];
    }), Lp + 8, Tp + 12);
    // мини-панели прошлых событий, та же шкала по вертикали
    if (RC) {
      var x0 = W - RC - R, gap = 6, hh = (ph + Tp - Tp) / years.length - gap;
      years.forEach(function (y, yi) {
        var rows = NW.analog_series[y] || [], m = rows.length;
        if (!m) return;
        var top = Tp + yi * (hh + gap), Ym = function (v) { return top + (vmax - v) / (vmax - vmin) * hh; };
        var Xm = function (i) { return x0 + 6 + i / Math.max(1, m - 1) * (RC - 12); };
        s += '<rect x="' + x0 + '" y="' + top.toFixed(1) + '" width="' + RC + '" height="' + hh.toFixed(1) + '" rx="5" style="fill:var(--ink)" opacity=".04"/>';
        if (vmin < 0 && vmax > 0) s += '<line x1="' + (x0 + 6) + '" y1="' + Ym(0).toFixed(1) + '" x2="' + (x0 + RC - 6) + '" y2="' + Ym(0).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".6"/>';
        keys.forEach(function (k, ki) {
          s += segs(rows.map(function (r, i) { return [Xm(i), fin(r[k[0]]) ? Ym(r[k[0]]) : NaN]; }), k[2], k[0] === 'n34a' ? 1.6 : 1, pickOp(k[0], .95), dashOf(ki));
        });
        var lastRow = rows[m - 1] || {};
        s += '<text x="' + (x0 + 6) + '" y="' + (top + 10) + '" class="tt" font-size="10">' + esc(y) + '</text>' +
          '<text x="' + (x0 + RC - 6) + '" y="' + (top + 10) + '" text-anchor="end" font-size="9" style="fill:var(--soft)">3.4 ' + fnum(lastRow.n34a, 1) + ' · 1+2 ' + fnum(lastRow.n12a, 1) + '</text>';
      });
    }
    return s + '</svg>';
  }

  /* Тот же недельный индекс против сильнейших событий: 1982, 1997, 2015, 2023 по тому же
     календарю (владелец 03.09: «weekly indices тоже сравнение должно быть с годами, когда
     Эль-Ниньо было максимальным»). */
  function chartNoaaAnalog(NW, W, H) {
    var key = S.sub.wkey || 'n34a';
    var NAMES = { n12a: 'Niño 1+2', n3a: 'Niño 3', n34a: 'Niño 3.4', n4a: 'Niño 4' };
    var ser = NW.series, n = ser.length;
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var all = ser.map(function (r) { return r[key]; }).filter(fin);
    var ana = [];
    Object.keys(NW.analog_series || {}).forEach(function (y) {
      var rows = (NW.analog_series[y] || []).slice(-n).map(function (r) { return r[key]; });
      if (rows.length) { ana.push({ year: y, values: rows }); all = all.concat(rows.filter(fin)); }
    });
    var vmin = Math.min.apply(null, all) - .2, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + fitText(NAMES[key] + ' weekly, last ' + n + ' weeks, against the strongest events on the same calendar', W, 12) + '</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R + 8, W, 1);
    /* То же правило, что и на недельном графике: расстояние до предыдущей подписи не
       меньше тридцати четырёх пикселей, иначе месяцы стоят вплотную и читаются как одно
       слово; при редких подписях печатаем сезон тремя заглавными (владелец 06.09). */
    var lastMX = -1e9;
    ser.forEach(function (r, i) {
      if (parseInt(r.date.slice(8), 10) > 7) return;
      var xx = X(i);
      if (xx - lastMX < 34) return;
      var far = (xx - lastMX) < 70 && lastMX > -1e8;
      lastMX = xx;
      var mi = parseInt(r.date.slice(5, 7), 10) - 1;
      var lab = far ? (MONTHS[mi] || '').charAt(0) + (MONTHS[(mi + 1) % 12] || '').charAt(0) + (MONTHS[(mi + 2) % 12] || '').charAt(0) : MONTHS[mi];
      s += '<text x="' + xx.toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + lab + '</text>';
    });
    ana.forEach(function (a, ai) {
      var off = n - a.values.length;
      s += segs(a.values.map(function (v, i) { return [X(off + i), fin(v) ? Y(v) : NaN]; }), 'var(--a' + a.year + ')', 1.4, pickOp(a.year, .9), dashOf(ai + 1));
    });
    s += segs(ser.map(function (r, i) { return [X(i), fin(r[key]) ? Y(r[key]) : NaN]; }), 'var(--text)', 2.6, pickOp('now'));
    var li = n - 1;
    s += nowDot(X(li), Y(ser[li][key]), 'var(--nino)', 4);
    var leg = [['now ' + fnum(ser[li][key], 1), 'var(--text)', 2.6, '', 'now']];
    ana.forEach(function (a) {
      var v = a.values[a.values.length - 1];
      leg.push([a.year + ' ' + fnum(v, 1) + (fin(v) ? ' (' + fnum(ser[li][key] - v, 1) + ' now)' : ''), 'var(--a' + a.year + ')', 1.4, dashOf(ana.indexOf(a) + 1), a.year]);
    });
    s += legend(leg, W, H, R, Tp);
    return s + '</svg>';
  }

  /* Сводное по живым моделям на сезоне сравнения — то самое число, ради которого всё
     затевалось: «а то мы показываем, что всё хорошо, а это не так» (владелец 04.09). */
  function liveNow(IRI, which) {
    var LV = IRI.live, ao = IRI.against_observed || {}, ss = IRI.seasons || [];
    var arr = LV && (which === 'rms' ? LV.rms : LV.mean);
    if (!arr) return null;
    var i = ss.indexOf(ao.season);
    return i >= 0 ? arr[i] : null;
  }

  /* ГДЕ МЫ В СЕЗОНЕ — ОТРЕЗКОМ, А НЕ ТОЧКОЙ. Владелец 04.09: «линия там, где пройдено;
     то, что ещё не пройдено — пунктир; точка, где мы сейчас, тогда линией показываем, а не
     точкой — тогда будет видно, что тут прошли треть, а тут половину».
     Сплошная часть отрезка занимает ровно ту долю ширины столбца, какая доля сезона прожита
     (JJA — вся, JAS — две трети, ASO — треть), и лежит на измеренном значении. Пунктир идёт
     от её конца к середине полосы: это остаток сезона, которого ещё нет. Вертикальная полоса
     — куда этот остаток может увести среднее за сезон. */
  /* ГДЕ МЫ СЕЙЧАС И ГДЕ БУДЕМ — ВЕРТИКАЛЬНЫМ ОТРЕЗКОМ. Владелец 04.09: «я имел в виду не
     горизонтальные отрезки текущего значения, а вертикальное: оно бы показало на этом
     отрезке, где мы сейчас и где будем в этот трёхмесячный период».
     Отрезок идёт снизу вверх по шкале температуры: жирная точка — уже измеренная часть
     сезона (это факт), а вертикаль над ней и под ней — куда может уехать среднее за сезон,
     когда допишутся оставшиеся месяцы. Засечки на концах подписаны, доля прожитого стоит
     подписью рядом: у прожитого целиком сезона вертикали нет вовсе — там нечему двигаться. */
  function livedMark(x, w, p, Y) {
    var s = '';
    if (p.complete || !fin(p.lo) || !fin(p.hi)) {
      s += '<circle cx="' + x.toFixed(1) + '" cy="' + Y(p.todate).toFixed(1) + '" r="4.5" style="fill:var(--ok)"/>';
      return s;
    }
    var cap = Math.max(5, w * .3);
    /* ТОЧКА ВНУТРИ ОТРЕЗКА. Владелец 05.09: «если мы в середине или начале периода —
       отображается не точка, а вертикальный отрезок, и точка должна быть внутри отрезка».
       Отрезок идёт от прожитого (точка) до того, где может кончиться среднее за сезон
       по разбросу живых моделей: «где мы сейчас и где будем». */
    var segLo = Math.min(p.lo, p.todate), segHi = Math.max(p.hi, p.todate);
    s += '<line x1="' + x.toFixed(1) + '" y1="' + Y(segHi).toFixed(1) + '" x2="' + x.toFixed(1) +
      '" y2="' + Y(segLo).toFixed(1) + '" style="stroke:var(--nino)" stroke-width="3" opacity=".55"/>';
    [p.lo, p.hi].forEach(function (v) {
      s += '<line x1="' + (x - cap).toFixed(1) + '" y1="' + Y(v).toFixed(1) + '" x2="' + (x + cap).toFixed(1) +
        '" y2="' + Y(v).toFixed(1) + '" style="stroke:var(--nino)" stroke-width="1.6" opacity=".8"/>';
    });
    s += nowDot(x, Y(p.todate), 'var(--nino)', 4.5);
    s += '<text x="' + (x + cap + 4).toFixed(1) + '" y="' + (Y(p.todate) + 3.5).toFixed(1) + '" font-size="9" style="fill:var(--nino)">' +
      p.months_done + '/3 lived, ' + fnum(p.todate) + '</text>';
    return s;
  }

  function chartPlume(IRI, obs, W, H) {
    var seasons = IRI.seasons, models = IRI.models;
    var fc = []; seasons.forEach(function (sn, i) { if (sn.indexOf('OBS') < 0) fc.push(i); });
    var ao = IRI.against_observed || {};
    var i0 = seasons.indexOf(ao.season) >= 0 ? seasons.indexOf(ao.season) : (fc[0] || 2);
    /* ОСЬ НАЧИНАЕТСЯ С ПРОЖИТОГО, А НЕ С ПЕРВОГО СТОЛБЦА МОДЕЛЕЙ. Владелец 04.09: «нужно ещё
       назад периоды показать, JJA и JAS; на JAS мы сейчас в большей степени, а не на ASO».
       Плюм начинает прогноз с ASO, где прожит один месяц из трёх. JAS прожит на два из трёх,
       а JJA целиком — и его в плюме нет вовсе. Поэтому колонки собираем сами: сначала наши
       прожитые сезоны (даже те, которых модели не публикуют), потом прогнозные. Модельные
       линии рисуются только там, где у моделей есть числа, и обрыв слева честен: они туда
       и не заглядывают. */
    var POS = IRI.position || [];
    var cols = [];
    POS.forEach(function (p) { if (p.i == null) cols.push({ label: p.season, i: null, pos: p }); });
    var startI = Math.min.apply(null, POS.filter(function (p) { return p.i != null; })
      .map(function (p) { return p.i; }).concat([i0]));
    seasons.forEach(function (sn, i) {
      if (i < startI || sn.indexOf('OBS') >= 0) return;
      cols.push({ label: sn, i: i, pos: POS.filter(function (p) { return p.i === i; })[0] || null });
    });
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var all = [obs];
    Object.keys(models).forEach(function (k) { (models[k].values || []).forEach(function (v) { if (fin(v)) all.push(v); }); });
    POS.forEach(function (p) { [p.lo, p.hi, p.todate].forEach(function (v) { if (fin(v)) all.push(v); }); });
    var vmin = Math.min.apply(null, all) - .3, vmax = Math.max.apply(null, all) + .5;
    var colOf = {}; cols.forEach(function (c, k) { if (c.i != null) colOf[c.i] = k; });
    var XK = function (k) { return Lp + k / Math.max(1, cols.length - 1) * pw; };
    var X = function (i) { return XK(colOf[i] != null ? colOf[i] : 0); };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var td = seasonTodate(ao.season, issueYear(IRI.issued));
    var ref = td ? td.value : obs;                 // с чем честно сравнивать модели
    /* Самый прожитый из начатых сезонов — наша твёрдая опора: у него больше всего измеренных
       месяцев. Именно про него владелец сказал «на JAS мы сейчас в большей степени». */
    var best = (IRI.position || []).filter(function (p) { return !p.complete; })
      .sort(function (a, b) { return b.months_done - a.months_done; })[0] || null;
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">IRI model plume, ' + esc(IRI.issued) + ' issue: Niño 3.4 by season, °C</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R + 8, W, 1);
    cols.forEach(function (c, k) {
      if (W <= 470 && k % 2 !== 0) return;
      var lived = c.pos && c.pos.months_done;
      // крайняя подпись прижимается к краю поля, иначе уезжает за картинку
      var xk = XK(k), edge = W - R - 6;
      var anc = xk > edge - 10 ? 'end' : 'middle';
      s += '<text x="' + Math.min(xk, edge).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + anc + '"' + (lived ? ' style="fill:var(--nino)"' : '') + '>' + esc(c.label) + '</text>';
    });
    var cls = IRI.classes || {};
    /* САМАЯ СИЛЬНАЯ МОДЕЛЬ — ОТДЕЛЬНОЙ ЛИНИЕЙ. Владелец 04.09: «самую сильную модель выдели».
       Сильная здесь — та, что даёт самый высокий пик среди ЖИВЫХ: именно она говорит, куда
       событие может уйти, если правы окажутся не середина, а край. */
    var strongest = null, strongestPeak = -99;
    Object.keys(models).forEach(function (name) {
      var m = models[name];
      if ((m.section !== 'dyn' && m.section !== 'stat') || !m.values) return;
      if (((cls[name] || {}).cls) === 'broke') return;
      var pk = Math.max.apply(null, m.values.filter(fin).concat([-99]));
      if (pk > strongestPeak) { strongestPeak = pk; strongest = name; }
    });
    Object.keys(models).forEach(function (name) {
      var m = models[name]; if ((m.section !== 'dyn' && m.section !== 'stat') || !m.values) return;
      var c = (cls[name] || {}).cls;
      var hot = S.model === name, picked = S.pick && (S.pick === c || S.pick === name);
      var dim = (S.pick && !picked) || (S.model && !hot);
      var col = hot || picked ? 'var(--ochre)' : (c === 'broke' ? 'var(--lv5)' : (c === 'lag' ? 'var(--lv3)' : (m.section === 'dyn' ? 'var(--nina)' : 'var(--ok)')));
      var wid = hot ? 2.6 : (picked ? 1.8 : (name === strongest ? 2 : 1));
      var op = dim ? .12 : (hot || picked ? 1 : (name === strongest ? .95 : (c === 'broke' ? .45 : .38)));
      if (name === strongest && !S.pick && !S.model) col = 'var(--lv4)';
      s += segs(fc.map(function (i) { return [X(i), fin(m.values[i]) ? Y(m.values[i]) : NaN]; }), col, wid, op);
    });
    var hist = IRI.history || [];
    if (hist.length > 1 && hist[1].combined) {
      var pv = hist[1], idx = {}; pv.seasons.forEach(function (sn, k) { idx[sn] = k; });
      s += segs(fc.map(function (i) { var k = idx[seasons[i]]; return [X(i), (k != null && fin(pv.combined[k])) ? Y(pv.combined[k]) : NaN]; }), 'var(--soft)', 1.6, pickOp('prev'), '5 4');
    }
    var comb = (IRI.summary || {}).combined;
    // опубликованное сводное по ВСЕМ моделям остаётся для сверки, но тонкой бледной линией:
    // владелец 04.09 — «толстая тёмная линия среднее по всем моделям нас мало интересует»
    if (comb) s += segs(cols.map(function (c) { return [XK(cols.indexOf(c)), (c.i != null && fin(comb[c.i])) ? Y(comb[c.i]) : NaN]; }), 'var(--soft)', 1.1, pickOp('pub', .75), '3 3');
    /* СРЕДНЕЕ ПО ЖИВЫМ. Опубликованное сводное считает все модели поровну, включая
       одиннадцать сломанных, и оттого лежит ниже. Владелец 04.09: «нам нужны модели,
       которые шли с нами вместе, по ним и рисуем среднее». */
    var LV = IRI.live;
    if (LV && (LV.rms || LV.mean)) {
      var main = LV.rms || LV.mean;
      s += segs(fc.map(function (i) { return [X(i), fin(main[i]) ? Y(main[i]) : NaN]; }), 'var(--ochre)', 3.2, pickOp('rms'));
      if (LV.rms && LV.mean) s += segs(fc.map(function (i) { return [X(i), fin(LV.mean[i]) ? Y(LV.mean[i]) : NaN]; }), 'var(--ochre)', 1, pickOp('mean', .5), '2 3');
    }
    /* ЧЕРТА УЖЕ ДОСТИГНУТОГО УРОВНЯ через весь график. Без неё глаз сравнивал всю кривую
       с одной точкой и спрашивал: почему линии выше 2.6, если модели «ломаются»? Линии идут
       в будущее, событие ещё растёт — сравнивать можно только на первом прогнозном сезоне,
       и вот он, отмечен вертикалью, а под чертой видно, кто уже отстал. */
    s += '<line x1="' + Lp + '" y1="' + Y(ref).toFixed(1) + '" x2="' + (W - R - 8) + '" y2="' + Y(ref).toFixed(1) + '" style="stroke:var(--nino)" stroke-width="1" stroke-dasharray="4 3" opacity=".85"/>';
    s += '<line x1="' + X(i0).toFixed(1) + '" y1="' + Tp + '" x2="' + X(i0).toFixed(1) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="2 3" opacity=".8"/>';
    /* РОССЫПИ ТОЧЕК БОЛЬШЕ НЕТ. Владелец 04.09: «на plume сегодняшний уровень убери точки,
       оставь только текущую, и так видно пересечение, иначе сливается». Две дюжины кружков
       на одной вертикали читались как клякса; пересечение линий с чертой прожитого уровня
       видно и без них, а счёт «сколько ниже» стоит фишкой под графиком. */
    var lowN = 0, totN = 0;
    Object.keys(models).forEach(function (name) {
      var m = models[name];
      if ((m.section !== 'dyn' && m.section !== 'stat') || !m.values || !fin(m.values[i0])) return;
      totN++;
      if (m.values[i0] < ref) lowN++;
    });
    /* ГДЕ МЫ СТОИМ — ПОЛОСА, А НЕ ТОЧКА. Владелец 04.09: «ASO — это среднее, а сейчас
       начало сентября; сравнивать надо с прожитым сезоном, и не точкой, а диапазоном,
       шире — по разбросу моделей». Прожитая часть сезона это факт (засечка), остаток
       неизвестен, и его границы взяты из разброса живых моделей на тот же сезон. */
    cols.forEach(function (c, k) {
      var p = c.pos;
      if (!p) return;
      if (p.complete) {                                   // сезон прожит целиком — сплошной отрезок во всю ширину
        var wc = Math.max(14, pw / Math.max(5, cols.length) * .62);
        s += livedMark(XK(k), wc, p, Y) +
          '<text x="' + XK(k).toFixed(0) + '" y="' + (Y(p.todate) - 9).toFixed(0) + '" text-anchor="middle" font-size="10" style="fill:var(--ok)">' + esc(p.season) + ' ' + fnum(p.todate) + '</text>';
        return;
      }
      var x = XK(k), w2 = Math.max(14, pw / Math.max(5, cols.length) * .62);
      s += livedMark(x, w2, p, Y);
      if (best && p.season === best.season)
        s += '<text x="' + (x + w2 / 2 + 5).toFixed(0) + '" y="' + (Y(p.hi) - 6).toFixed(0) + '" class="tt">' +
          esc(p.season) + ' ' + fnum(p.lo) + ' … ' + fnum(p.hi) + '</text>';
      // вторая строка ушла в подпись под графиком: на самом графике она налезала на счёт моделей
    });
    var LF = IRI.last_full_season;
    if (LF) {
      s += '<line x1="' + Lp + '" y1="' + Y(LF.value).toFixed(1) + '" x2="' + (W - R - 8) +
        '" y2="' + Y(LF.value).toFixed(1) + '" style="stroke:var(--ok)" stroke-width="1" stroke-dasharray="2 4" opacity=".8"/>';
      // подпись не дублируем: столбец JJA теперь на графике и подписан сам
    }
    if (best) {
      s += '<text x="' + (W - R - 10) + '" y="' + (Tp + 12) + '" text-anchor="end" class="tt" style="fill:var(--nino)">our firmest reading: ' +
        esc(best.season) + ' ' + fnum(best.todate) + ', ' + best.months_done + ' of 3 months measured</text>';
    }
    // счёт «сколько ниже прожитого» ушёл в фишки под графиком: на графике он налезал на полосу
    var LVn = IRI.live || {}, tally2 = IRI.class_tally || {};
    /* Сначала то, что нажимается и выделяет ряды; пустая строка; потом справочные строки
       без действия (владелец 05.09). По умолчанию выделены «keeping up». */
    var leg = [['keeping up ' + (tally2.ok || 0), 'var(--nina)', 1.4, null, 'ok'],
      ['lagging ' + (tally2.lag || 0), 'var(--lv3)', 1.4, null, 'lag'],
      ['broken ' + (tally2.broke || 0), 'var(--lv5)', 1.4, null, 'broke'],
      [(strongest ? 'strongest: ' + strongest + ' ' + fnum(strongestPeak) : 'strongest model'), 'var(--lv4)', 2, null, strongest || ''],
      ['RMS, live ' + (LVn.n_live || '—') + ' of ' + (LVn.n_all || '—'), 'var(--ochre)', 3.2, '', 'rms'],
      ['their plain mean', 'var(--ochre)', 1, '2 3', 'mean'],
      ['published, all ' + (LVn.n_all || '—'), 'var(--soft)', 1.1, '3 3', 'pub'],
      ['previous issue' + (hist.length > 1 ? ' (' + hist[1].issued + ')' : ''), 'var(--soft)', 1.6, '5 4', 'prev'],
      [''],
      [esc(ao.season) + ' so far ' + fnum(ref), 'var(--nino)', 1, '4 3'], ['below the lived part', 'var(--lv5)', 'dot']];
    if (IRI.last_full_season) leg.push([esc(IRI.last_full_season.season) + ' lived in full', 'var(--ok)', 1, '2 4']);
    leg.push(['lived part of a season: dot', 'var(--nino)', 'dot']);
    leg.push(['where its mean can end: bar', 'var(--nino)', 4]);
    if (S.model) leg.unshift([S.model, 'var(--ochre)', 2.6, '', S.model]);
    s += legend(leg, W, H, R, Tp);
    return s + '</svg>';
  }

  /* ТРИ ВЫПУСКА ДРУГ ПОД ДРУГОМ. Один плюм отвечает на вопрос «что модели ждут», но не на
     вопрос «видели ли они это раньше». Три выпуска в одной шкале, свежий сверху, с одной и
     той же чертой уже достигнутого уровня, отвечают: месяц назад почти весь пучок лежал
     ниже сегодняшней воды, то есть событие обгоняет прогноз, а не наоборот. */
  function chartStack(stack, obs, W, H) {
    if (!stack || stack.length < 2) return svgOpen(W, H) + '<text x="20" y="' + (H / 2) + '">Fewer than two stored issues.</text></svg>';
    var rows = stack.slice(0, 3);
    // Легенда справа, как на остальных сценах (владелец 04.09: «month by month то же самое,
    // легенды справа»): место под неё режется у поля графиков один раз, на все три выпуска.
    var RCs = W >= 620 ? Math.max(120, Math.min(190, Math.round(W * .24))) : 0;
    var all = [obs];
    rows.forEach(function (r) {
      Object.keys(r.models).forEach(function (k) { (r.models[k].values || []).forEach(function (v) { if (fin(v)) all.push(v); }); });
    });
    var vmin = Math.min.apply(null, all) - .2, vmax = Math.max.apply(null, all) + .2;
    var gap = 8, hh = (H - gap * (rows.length - 1)) / rows.length;
    var s2 = svgOpen(W, H);
    rows.forEach(function (r, ri) {
      var top = ri * (hh + gap);
      var Lp = 44, R = 8, Tp = top + 14, B = 16, pw = W - Lp - R - RCs, ph = hh - 14 - B;
      var fc = []; r.seasons.forEach(function (sn, i) { if (sn.indexOf('OBS') < 0) fc.push(i); });
      if (!fc.length) return;
      var X = function (i) { return Lp + (fc.indexOf(i) < 0 ? 0 : fc.indexOf(i)) / Math.max(1, fc.length - 1) * pw; };
      var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
      s2 += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph + '" rx="6" style="fill:var(--ink)" opacity="' + (ri === 0 ? '.035' : '.02') + '"/>';
      [Math.ceil(vmin), Math.round((vmin + vmax) / 2), Math.floor(vmax)].forEach(function (g) {
        if (g <= vmin || g >= vmax) return;
        s2 += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".5"/>';
        s2 += '<text x="' + (Lp - 5) + '" y="' + (Y(g) + 3).toFixed(1) + '" text-anchor="end" font-size="9">' + fnum(g, 1) + '</text>';
      });
      // У КАЖДОГО ВЫПУСКА СВОЙ первый прогнозный сезон, и сравнивать его надо с прожитой
      // частью именно этого сезона: у июньского выпуска это JJA, который сегодня прожит
      // целиком, у августовского — ASO, прожитый на треть.
      var fi0 = fc.filter(function (i) { var any = false; Object.keys(r.models).forEach(function (nm) { if (fin(r.models[nm].values[i])) any = true; }); return any; })[0];
      var lab = fi0 != null ? r.seasons[fi0] : null;
      var td2 = lab ? seasonTodate(lab, issueYear(r.issued)) : null;
      var ref2 = td2 ? td2.value : obs;
      s2 += '<line x1="' + Lp + '" y1="' + Y(ref2).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(ref2).toFixed(1) + '" style="stroke:var(--nino)" stroke-width="1" stroke-dasharray="4 3" opacity=".8"/>';
      var CL = ((S.D.iri || {}).classes) || {};
      var below = 0, tot = 0;
      Object.keys(r.models).forEach(function (nm) {
        var m = r.models[nm];
        if (m.section !== 'dyn' && m.section !== 'stat') return;
        var c2 = (CL[nm] || {}).cls || 'none';
        var picked2 = S.pick && (S.pick === c2 || S.pick === nm), dim2 = S.pick && !picked2;
        var pts = fc.map(function (i) { return [X(i), fin(m.values[i]) ? Y(m.values[i]) : NaN]; });
        s2 += segs(pts, picked2 ? 'var(--ochre)' : (c2 === 'broke' ? 'var(--lv5)' : (c2 === 'lag' ? 'var(--lv3)' : 'var(--nina)')),
          picked2 ? 1.6 : 1, dim2 ? .1 : (picked2 ? .95 : .35));
        if (fi0 != null && fin(m.values[fi0])) { tot++; if (m.values[fi0] < ref2) below++; }
      });
      /* СРЕДНЕЕ — ТОЛЬКО ПО ЖИВЫМ, И ЗДЕСЬ ТОЖЕ. Владелец 04.09: «на month by month то же
         самое: те модели, которые отвалились, не учитывать в среднем; основная средняя линия
         — для тех моделей, что живы». Опубликованное сводное остаётся тонкой линией рядом:
         разрыв между ними и есть цена того, что кто-то давно сломался. */
      var comb = Object.keys(r.models).filter(function (k) { return k.indexOf('COMBINED') === 0; })[0];
      if (comb) s2 += segs(fc.map(function (i) { return [X(i), fin(r.models[comb].values[i]) ? Y(r.models[comb].values[i]) : NaN]; }), 'var(--soft)', 1.2, pickOp('pub', .9), '3 3');
      var liveMean = fc.map(function (i) {
        var sum = 0, wsum = 0;
        Object.keys(r.models).forEach(function (nm) {
          var m = r.models[nm];
          if (m.section !== 'dyn' && m.section !== 'stat' || !fin(m.values[i])) return;
          var w3 = ({ ok: 1, lag: .4, broke: 0 })[((CL[nm] || {}).cls || 'none')];
          if (w3 == null) w3 = .6;
          if (!w3) return;
          sum += m.values[i] * w3; wsum += w3;
        });
        return [X(i), wsum ? Y(sum / wsum) : NaN];
      });
      // среднеквадратичная по живым: большой прогноз должен весить больше, а не тонуть в среднем
      var liveRms = fc.map(function (i) {
        var sq = 0, wsum = 0, sgn = 0;
        Object.keys(r.models).forEach(function (nm) {
          var m = r.models[nm];
          if (m.section !== 'dyn' && m.section !== 'stat' || !fin(m.values[i])) return;
          var w3 = ({ ok: 1, lag: .4, broke: 0 })[((CL[nm] || {}).cls || 'none')];
          if (w3 == null) w3 = .6;
          if (!w3) return;
          sq += m.values[i] * m.values[i] * w3; wsum += w3; sgn += m.values[i] * w3;
        });
        if (!wsum) return [X(i), NaN];
        var v = Math.sqrt(sq / wsum);
        return [X(i), Y(sgn >= 0 ? v : -v)];
      });
      s2 += segs(liveMean, 'var(--ochre)', 1, pickOp('mean', .5), '2 3');
      s2 += segs(liveRms, 'var(--ochre)', 2.8, pickOp('rms'));
      /* КАК ДВИГАЛСЯ ДИАПАЗОН ЖИВЫХ. Владелец 04.09: «как менялись диапазоны за последние
         три месяца». Классы у моделей общие (по сегодняшней проверке), поэтому в каждом
         выпуске берём те же живые имена — и видно, что месяц назад их коридор был ниже
         сегодняшней воды, а сейчас выше: догоняют, а не ведут. */
      var live2 = [];
      fc.forEach(function (i) {
        var vs = [];
        Object.keys(r.models).forEach(function (nm) {
          var m = r.models[nm];
          if (m.section !== 'dyn' && m.section !== 'stat' || !fin(m.values[i])) return;
          if (((CL[nm] || {}).cls || 'none') === 'broke') return;
          vs.push(m.values[i]);
        });
        if (vs.length > 2) { vs.sort(function (a, b) { return a - b; }); live2.push([i, vs[Math.floor(vs.length * .1)], vs[Math.ceil(vs.length * .9) - 1]]); }
      });
      if (live2.length > 1) {
        var up = live2.map(function (q) { return X(q[0]).toFixed(1) + ',' + Y(q[2]).toFixed(1); });
        var dn = live2.slice().reverse().map(function (q) { return X(q[0]).toFixed(1) + ',' + Y(q[1]).toFixed(1); });
        s2 += '<polygon points="' + up.concat(dn).join(' ') + '" style="fill:var(--ochre)" opacity=".14"/>';
      }
      /* Где мы стоим в ЭТОМ выпуске — отрезком: длина сплошной части показывает, какая
         доля его первого прогнозного сезона уже прожита. У июньского выпуска она полная,
         у августовского — треть, и это видно без единой цифры. */
      if (fi0 != null && td2) {
        var vs2 = [];
        Object.keys(r.models).forEach(function (nm) {
          var m = r.models[nm];
          if (m.section !== 'dyn' && m.section !== 'stat' || !fin(m.values[fi0])) return;
          if (((CL[nm] || {}).cls || 'none') === 'broke') return;
          vs2.push(m.values[fi0]);
        });
        vs2.sort(function (a, b) { return a - b; });
        var doneN = td2.done, restN = 3 - doneN, sumN = td2.value * doneN;
        var pRec = { season: td2.season, todate: td2.value, months_done: doneN, months: 3, complete: restN <= 0 };
        if (restN > 0 && vs2.length > 2) {
          pRec.lo = (sumN + restN * vs2[Math.floor(vs2.length * .1)]) / 3;
          pRec.hi = (sumN + restN * vs2[Math.ceil(vs2.length * .9) - 1]) / 3;
        }
        s2 += livedMark(X(fi0), Math.max(12, pw / Math.max(5, fc.length) * .6), pRec, Y);
      }
      s2 += '<text class="tt" x="' + Lp + '" y="' + (top + 10) + '">' + esc(r.issued) + ' issue' + (ri === 0 ? ' — the newest' : '') + '</text>';
      if (RCs && ri === 0) {
        var CLt = ((S.D.iri || {}).class_tally) || {};
        s2 += legend([['keeping up ' + (CLt.ok || 0), 'var(--nina)', 1.4, null, 'ok'],
          ['lagging ' + (CLt.lag || 0), 'var(--lv3)', 1.4, null, 'lag'],
          ['broken ' + (CLt.broke || 0), 'var(--lv5)', 1.4, null, 'broke'],
          ['RMS, live models', 'var(--ochre)', 2.8, '', 'rms'],
          ['their plain mean', 'var(--ochre)', 1, '2 3', 'mean'],
          ['published, all', 'var(--soft)', 1.2, '3 3', 'pub'],
          [''],
          ['each model', 'var(--soft)', 1],
          ['live spread', 'var(--ochre)', 6],
          ['where we stand', 'var(--nino)', 3]], W, H, RCs, Tp);
      }
      if (!S._tight) s2 += '<text x="' + (W - R) + '" y="' + (top + 10) + '" text-anchor="end" style="fill:var(--soft)">' + below + ' of ' + tot + ' below ' + esc(lab || '') + ' as lived so far (' + fnum(ref2) + (td2 ? ', ' + td2.done + '/3 months' : '') + ')</text>';
      fc.forEach(function (i, k) { if (k % 2 === 0) s2 += '<text x="' + X(i).toFixed(0) + '" y="' + (Tp + ph + 12) + '" text-anchor="middle" font-size="9">' + esc(r.seasons[i]) + '</text>'; });
    });
    return s2 + '</svg>';
  }

  /* Как ломаются модели: доля ниже реальности по выпускам + средняя ошибка. */
  function chartBreakdown(bd, W, H) {
    var rows = bd.by_issue || [];
    if (rows.length < 2) return svgOpen(W, H) + '<text x="20" y="' + (H / 2) + '">Not enough verified issues yet.</text></svg>';
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 30, pw = W - Lp - R - 42, ph = H - Tp - B, n = rows.length;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (100 - v) / 100 * ph; };
    var errs = rows.map(function (r) { return r.mean_err; });
    var emin = Math.min.apply(null, errs) - .1, emax = Math.max.apply(null, errs) + .1;
    var Y2 = function (v) { return Tp + (emax - v) / (emax - emin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">Share of models below reality, by issue — and the average model error</text>';
    [0, 25, 50, 75, 100].forEach(function (g) { s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R - 42) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '%</text>'; });
    rows.forEach(function (r, i) {
      var bw = Math.max(6, pw / n * .5);
      s += '<rect x="' + (X(i) - bw / 2).toFixed(1) + '" y="' + Y(r.share).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + (Y(0) - Y(r.share)).toFixed(1) + '" style="fill:var(--nino)" opacity=".55" rx="2"/>';
      /* Подписей столько, сколько влезает: в плитке обзора «через одну» всё равно давало
         десяток слипшихся слов (владелец 06.09: «внизу сливаются даты»). */
      var every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(pw / 36))));
      if (i % every === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 16) + '" text-anchor="middle">' + esc(r.issue.split(' ')[0]) + '</text><text x="' + X(i).toFixed(0) + '" y="' + (H - 5) + '" text-anchor="middle" opacity=".6">' + esc(r.season.split(' ')[0]) + '</text>';
    });
    s += poly(rows.map(function (r, i) { return [X(i), Y2(r.mean_err)]; }), 'var(--text)', 2);
    rows.forEach(function (r, i) { s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y2(r.mean_err).toFixed(1) + '" r="2.6" style="fill:var(--text)"/>'; });
    [emin, (emin + emax) / 2, emax].forEach(function (g) { s += '<text x="' + (W - R - 38) + '" y="' + (Y2(g) + 4).toFixed(0) + '" style="fill:var(--soft)">' + fnum(g, 1) + '</text>'; });
    if (!S._tight) s += '<text x="' + (W - R - 38) + '" y="' + (Tp - 6) + '" style="fill:var(--soft)">mean err, °C</text>';
    s += legend([['share below reality', 'var(--nino)', 6], ['average model error', 'var(--text)', 2]], W, H, R, Tp);
    return s + '</svg>';
  }

  function chartHistory(rows, W, H) {
    var byDay = {}; rows.forEach(function (r) { if (r.date) byDay[r.date] = r; });
    var days = Object.keys(byDay).sort(), list = days.map(function (d) { return byDay[d]; });
    if (list.length < 2) return svgOpen(W, H) + '<text x="20" y="' + (H / 2) + '">Only one snapshot so far: the history line appears from the second update.</text></svg>';
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B, n = list.length;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (100 - v) / 100 * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">Our risk index by update, and the share of models below reality</text>';
    [0, 25, 50, 75, 100].forEach(function (g) { s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R - 8) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>'; });
    /* Подписи по расстоянию, крайняя — прижата к краю: «09-04» уезжала за картинку. */
    var lastHX = -1e9;
    list.forEach(function (r, i) {
      var xx = X(i);
      if (xx - lastHX < 40 && i !== n - 1) return;
      lastHX = xx;
      var edge = W - R - 4, anc = xx > edge - 12 ? 'end' : (xx < Lp + 14 ? 'start' : 'middle');
      s += '<text x="' + Math.min(xx, edge).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + anc + '">' + esc(r.date.slice(5)) + '</text>';
    });
    s += poly(list.map(function (r, i) { return [X(i), Y(r.risk_index)]; }), 'var(--nino)', 2.2);
    list.forEach(function (r, i) { s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(r.risk_index).toFixed(1) + '" r="3" style="fill:' + (r.shout ? 'var(--lv5)' : 'var(--nino)') + '"/>'; });
    if (list.length) { var lr = list[list.length - 1]; s += nowDot(X(list.length - 1), Y(lr.risk_index), lr.shout ? 'var(--lv5)' : 'var(--nino)', 3.5); }
    s += poly(list.map(function (r, i) { return [X(i), fin(r.n_below) && r.n_models ? Tp + (1 - r.n_below / r.n_models) * ph : NaN]; }), 'var(--nina)', 1.4, 1, '4 3');
    s += legend([['risk index 0–100', 'var(--nino)', 2.2], ['a SHOUT alert', 'var(--lv5)', 'dot'], ['models below reality, %', 'var(--nina)', 1.4, '4 3']], W, H, R, Tp);
    return s + '</svg>';
  }

  /* Карта Тихого океана: текущий индекс каждого участка и то же место у сильнейших событий. */
  /* СУША. Владелец 03.09: «карту ты на pacific map не нарисовал». Очертания схематичны и
     нарисованы прямо в координатах окна (120° в. д. … 70° з. д., 15° с. ш. … 15° ю. ш.):
     это не карта для навигации, а опора для глаза — где Индонезия, где Южная Америка, между
     ними участки Niño. Точки берега упрощены до десятка на контур. */
  var LAND = [
    { name: 'Philippines', pts: [[120, 15], [124, 14], [126, 11], [124.5, 7], [122, 6], [120.5, 9], [119.5, 12]] },
    { name: 'Indonesia', pts: [[119, 1.5], [122.5, 0.5], [125.5, 1.5], [127, -1], [124, -4], [121, -5.5], [119, -3.5], [118.5, -1]] },
    { name: '', pts: [[124, -8.5], [128, -8], [131, -8.5], [127, -10], [124.5, -9.5]] },
    { name: 'New Guinea', pts: [[131, -1], [136, -2], [141, -2.5], [147, -6], [150.5, -8.5], [147, -9.5], [141, -8], [136, -6], [132, -4]] },
    { name: 'N. Australia', pts: [[129, -11], [133, -11.5], [136.5, -12], [138, -15], [140, -18], [141, -22], [129, -22]] },
    { name: 'Mexico', pts: [[255, 22], [262, 22], [266, 19], [272, 17], [275, 15], [272, 15], [263, 18], [256, 20]] },
    { name: '', pts: [[141, -10.8], [143.5, -12], [145.5, -15], [139, -15], [139.5, -12.5]] },
    { name: 'Central America', pts: [[275, 15], [279, 13], [281, 10], [280, 8.5], [277.5, 9.5], [274, 11], [272, 15]] },
    { name: 'South America', pts: [[280, 8.5], [282.5, 6], [281.5, 2], [279.3, 0], [280, -4], [281.5, -8], [283, -12], [284.5, -15], [288, -19], [290, -22], [295, -22], [295, 8.5]] }
  ];

  /* Береговая линия грузится один раз и лениво: 11 КБ, но карта нужна не на каждой
     вкладке. Пришла — перерисовываем текущий график, если он на экране. */
  function loadCoast() {
    if (S.COAST !== undefined) return;
    S.COAST = null;
    fetch('/data/enso/coast.json', { cache: 'force-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d && d.polys) { S.COAST = d; redrawPlot(); } })
      .catch(function () {});
  }

  function pacific(NW, W, H) {
    loadCoast();
    // В низкой плитке (телефон, короткое окно) подписи долгот и «экватор» съедали карту —
    // при высоте меньше 200 пикселей оставляем только сами участки.
    var small = H < 200;
    var Lp = small ? 14 : 40, R = small ? 10 : 26, Tp = small ? 22 : 34, B = small ? 10 : 30;
    var LON0 = 110, LON1 = 295, LAT0 = 22;
    var pw = W - Lp - R, ph = H - Tp - B;
    /* КАРТА ДЕРЖИТ СВОИ ПРОПОРЦИИ. Окно — 185° долготы на 44° широты, это примерно 4:1;
       в полноэкранном режиме (особенно на телефоне) поле оказывалось вдвое выше, и суша
       растягивалась в вертикальные кляксы. Лишнюю высоту отдаём полям, карту ставим по
       центру (владелец 06.09: «люди хотят увидеть на карте мира, где это находится»). */
    var ideal = pw * (2 * LAT0) / (LON1 - LON0);
    /* Двойное растяжение по вертикали для приэкваториальных карт привычно и полезно:
       участки Niño узкие по широте, при честных пропорциях они схлопываются в полоску.
       Ограничиваем не пропорцией 1:1, а двойной — дальше начинается клякса. */
    if (ph > ideal * 2.2) { Tp += (ph - ideal * 2) / 2; ph = ideal * 2; }
    /* ШИРЕ И КРУПНЕЕ. Владелец 05.09: «очень маленькие цифры; побольше значения, побольше
       контраста, чуть меньше масштаб, чтобы очертания континентов появились, и сетку». */
    var lon = function (d) { return Lp + (d - LON0) / (LON1 - LON0) * pw; };
    var lat = function (d) { return Tp + (LAT0 - d) / (2 * LAT0) * ph; };
    var lv = NW.latest, aw = NW.analog_week || {}, ap = NW.analog_peak || {};
    var years = Object.keys(aw).sort();
    var cmpYear = S.sub.cmp || (years.indexOf('1997') >= 0 ? '1997' : years[years.length - 1]);
    var boxes = [['nino4', 'Niño 4', 160, 210, 5, -5, 'n4a'], ['nino34', 'Niño 3.4', 190, 240, 5, -5, 'n34a'],
      ['nino3', 'Niño 3', 210, 270, 5, -5, 'n3a'], ['nino12', 'Niño 1+2', 270, 280, 0, -10, 'n12a']];
    var s = svgOpen(W, H);
    s += '<text class="tt" x="' + Lp + '" y="13">Week of ' + esc(NW.date) + ' against ' + esc(cmpYear) + '–' + (parseInt(cmpYear, 10) + 1) + ' on the same week</text>';
    s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph + '" rx="8" style="fill:var(--nina)" opacity=".08"/>';
    // суша поверх воды, до участков Niño
    s += '<clipPath id="pacclip"><rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph + '" rx="8"/></clipPath><g clip-path="url(#pacclip)">';
    /* НАСТОЯЩАЯ БЕРЕГОВАЯ ЛИНИЯ, если она уже загружена (data/enso/coast.json, Natural
       Earth 110m, общественное достояние). Пока файл едет — рисуем прежние схематичные
       пятна: карта не должна быть пустой ни секунды. */
    var CO = S.COAST;
    if (CO && CO.polys) {
      CO.polys.forEach(function (poly) {
        var pts = poly.map(function (q) {
          return lon(Math.max(LON0 - 5, Math.min(LON1 + 5, q[0]))).toFixed(1) + ',' +
                 lat(Math.max(-LAT0 - 4, Math.min(LAT0 + 4, q[1]))).toFixed(1);
        }).join(' ');
        s += '<polygon points="' + pts + '" style="fill:var(--ink);stroke:var(--text)" fill-opacity=".13" stroke-width=".8" stroke-opacity=".5"/>';
      });
    } else LAND.forEach(function (L) {
      var pts = L.pts.map(function (p) { return lon(p[0]).toFixed(1) + ',' + lat(Math.max(-LAT0, Math.min(LAT0, p[1]))).toFixed(1); }).join(' ');
      s += '<polygon points="' + pts + '" style="fill:var(--ink);stroke:var(--text)" fill-opacity=".14" stroke-width="1" stroke-opacity=".6"/>';
      if (L.name && !small && !CO) {
        var LBL = { 'South America': [294, -18, 'end'], 'Central America': [266.5, 18.8, 'middle'], 'Mexico': [257.5, 21, 'middle'], 'Indonesia': [111.5, -5, 'start'], 'Philippines': [111.5, 17.5, 'start'] };
        var cx = 0, cy = 0;
        L.pts.forEach(function (p) { cx += lon(p[0]); cy += lat(Math.max(-LAT0, Math.min(LAT0, p[1]))); });
        var lb = LBL[L.name], px = lb ? lon(lb[0]) : cx / L.pts.length, py = lb ? lat(lb[1]) : cy / L.pts.length;
        s += '<text x="' + px.toFixed(0) + '" y="' + py.toFixed(0) + '" text-anchor="' + (lb ? lb[2] : 'middle') + '" font-size="10" style="fill:var(--text)" opacity=".8">' + esc(L.name) + '</text>';
      }
    });
    /* Подписи суши по координатам — они полезны и на настоящей линии: читателю нужно
       понять, что слева Индонезия, а справа Южная Америка (владелец 06.09). */
    if (CO && !small) {
      [['Philippines', 122, 14, 'middle'], ['Indonesia', 114, -4.5, 'middle'], ['New Guinea', 141, -5.5, 'middle'],
       ['Australia', 134, -20, 'middle'], ['Japan', 137, 20.5, 'middle'], ['Mexico', 258, 20, 'middle'],
       ['Central America', 271, 13.5, 'middle'], ['South America', 289, -14, 'middle']].forEach(function (L) {
        s += '<text x="' + lon(L[1]).toFixed(0) + '" y="' + lat(L[2]).toFixed(0) + '" text-anchor="' + L[3] +
          '" font-size="10" style="fill:var(--text)" opacity=".62">' + L[0] + '</text>';
      });
    }
    // Галапагосы — единственная суша посреди очага, полезный ориентир
    if (!small) {
      s += '<circle cx="' + lon(269.5).toFixed(1) + '" cy="' + lat(-0.5).toFixed(1) + '" r="2.2" style="fill:var(--ink)" opacity=".45"/>';
      s += '<text x="' + (lon(269.5) - 4).toFixed(0) + '" y="' + (lat(-0.5) - 6).toFixed(0) + '" font-size="8.5" text-anchor="end" style="fill:var(--soft)">Galápagos</text>';
    }
    s += '</g>';
    // сетка: широты через 10°, долготы через 30°
    [-20, -10, 10, 20].forEach(function (d) {
      s += '<line x1="' + Lp + '" y1="' + lat(d).toFixed(1) + '" x2="' + (W - R) + '" y2="' + lat(d).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".7"/>';
      if (!small) s += '<text x="' + (Lp - 4) + '" y="' + (lat(d) + 3).toFixed(1) + '" text-anchor="end" font-size="9">' + Math.abs(d) + '°' + (d > 0 ? 'N' : 'S') + '</text>';
    });
    [120, 150, 180, 210, 240, 270].forEach(function (d) { s += '<line x1="' + lon(d).toFixed(1) + '" y1="' + Tp + '" x2="' + lon(d).toFixed(1) + '" y2="' + (Tp + ph) + '" style="stroke:var(--grid)" stroke-width=".7"/>'; });
    s += '<line x1="' + Lp + '" y1="' + lat(0) + '" x2="' + (W - R) + '" y2="' + lat(0) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="4 4"/>';
    s += '<text x="' + (Lp + 4) + '" y="' + (lat(0) + 12) + '" font-size="9">equator</text>';
    if (!small) {
      [120, 150, 180, 210, 240, 270].forEach(function (d) { s += '<text x="' + lon(d).toFixed(0) + '" y="' + (H - 8) + '" text-anchor="middle">' + (d <= 180 ? d + '°E' : (360 - d) + '°W') + '</text>'; });
      s += '<text x="' + (W - R) + '" y="' + (Tp - 9) + '" text-anchor="end">South America →</text><text x="' + Lp + '" y="' + (Tp - 9) + '">← Australia, Indonesia</text>';
    }
    /* ВЫБОР ЗОНЫ. Четыре участка перекрываются по долготе, и в режиме «все» их числа и
       подписи неизбежно спорят за место (владелец 06.09: «квадратики сливаются, всё
       нечитаемо»). Выбранная зона остаётся в полном цвете и с полным сравнением, соседние
       гаснут до 12% и молчат — карта читается даже на телефоне. */
    var zone = S.sub.zone || 'all';
    boxes.forEach(function (b) {
      var x = lon(b[2]), w = lon(b[3]) - x, y = lat(b[4]), h = lat(b[5]) - y, key = b[6], v = lv[key];
      var on = zone === 'all' || zone === b[0];
      var dim = !on;
      var then = (aw[cmpYear] || {})[key], peak = (ap[cmpYear] || {})[key];
      var col = v >= 2 ? 'var(--lv5)' : (v >= 1 ? 'var(--nino)' : (v >= .5 ? 'var(--lv3)' : (v <= -.5 ? 'var(--nina)' : 'var(--lv2)')));
      var pay = { name: b[1] + ' — week of ' + NW.date,
        def: 'Now ' + fnum(v, 1) + ' °C. On the same week of ' + cmpYear + ': ' + fnum(then, 1) + ' °C; the peak of that event was ' + fnum(peak, 1) + ' °C. ' +
          (fin(then) ? (v > then ? 'This event is ' + fnum(v - then, 1) + ' °C warmer at the same point of the calendar.' : 'This event is ' + fnum(v - then, 1) + ' °C against it.') : ''),
        src: 'NOAA CPC weekly indices, wksst9120', date: NW.date };
      s += '<g data-src="' + esc(JSON.stringify(pay)) + '" data-zone="' + b[0] + '"' + (dim ? ' opacity=".12"' : '') + '>' +
        '<rect' + (b[0] === 'nino34' && zone === 'all' ? ' class="breathe"' : '') + ' x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" style="fill:' + col + ';stroke:' + col + '" fill-opacity="' + (zone === b[0] ? '.42' : '.3') + '" stroke-width="' + (zone === b[0] ? 2.6 : 1.8) + '" rx="3"/>';
      /* Боксы Niño 4, 3.4 и 3 перекрываются по долготе — подписи ярусами: 4 выше, 3.4 по
         центру, 3 ниже; у Niño 1+2 бокс узкий — подписи слева от него. */
      /* ПОДПИСЬ ЗОНЫ — ВНУТРИ ЕЁ ПРЯМОУГОЛЬНИКА, у верхнего края. Раньше плашка стояла по
         центру бокса, с ярусным сдвигом, и у соседних зон эти плашки налезали друг на друга
         и на чужие участки (владелец 06.09: «проверить, чтобы надписи классов попадали в
         прямоугольник зоны»). Узкой Niño 1+2 плашка не по росту — ей подпись под боксом. */
      var big = small ? 14 : 18;
      var tier = { nino4: -0.32, nino34: 0, nino3: 0.32 }[b[0]] || 0;
      var cy = y + h / 2 + (zone === 'all' ? tier * h : 0), tx = x + w / 2;
      var lw = Math.min(b[1].length * 7.2 + 12, w - 6), narrowBox = lw < b[1].length * 6;
      var lx0 = narrowBox ? x + w / 2 - (b[1].length * 7.2 + 12) / 2 : x + 3;
      var ly0 = narrowBox ? y + h + 3 : y + 3;
      if (narrowBox) lw = b[1].length * 7.2 + 12;
      /* На узком экране в режиме «все зоны» плашки имён неизбежно налезают друг на друга:
         четыре подписи на 250 пикселей ширины. Там оставляем только числа, а имя показываем
         у выбранной зоны — за этим и сделан выбор (владелец 06.09). */
      var showName = !(pw < 420 && zone === 'all');
      if (showName) {
        s += '<rect x="' + lx0.toFixed(1) + '" y="' + ly0.toFixed(1) + '" width="' + lw.toFixed(1) + '" height="14" rx="7" style="fill:var(--surface);stroke:' + col + '" stroke-width="1.2"/>';
        s += '<text x="' + (lx0 + lw / 2).toFixed(1) + '" y="' + (ly0 + 10.5).toFixed(1) + '" text-anchor="middle" font-size="10" style="fill:' + col + ';font-weight:600;letter-spacing:.03em">' + b[1] + '</text>';
      }
      /* ЧИСЛА — БЕЛЫЕ ПОЛУЖИРНЫЕ С ТЁМНОЙ ОБВОДКОЙ. Владелец 06.09: «все цифры надо
         изменить на белый жирный, потому что всё сливается с фоном». Обводка (paint-order:
         stroke) держит их читаемыми и на светлой заливке зоны, и в тёмной теме, где белое
         на белом было бы не лучше. */
      var HALO = 'fill:#fff;paint-order:stroke;stroke:rgba(20,22,28,.75);stroke-width:3.4;stroke-linejoin:round;font-weight:700';
      s += '<text x="' + tx.toFixed(1) + '" y="' + (cy + (small ? 8 : 7)).toFixed(1) + '" text-anchor="middle" style="' + HALO + '" font-size="' + big + '">' + fnum(v, 1) + '</text>';
      // Сравнение с аналогом — только у выбранной зоны: в режиме «все» четыре таких строки
      // и были главной кашей на карте.
      if (fin(then) && zone === b[0]) s += '<text x="' + tx.toFixed(1) + '" y="' + (cy + (small ? 21 : 23)).toFixed(1) + '" text-anchor="middle" style="' + HALO.replace('stroke-width:3.4', 'stroke-width:3') + '" font-size="' + (small ? 10 : 12) + '">' + cmpYear + ' ' + fnum(then, 1) + ' · ' + (v >= then ? '▲' : '▼') + fnum(Math.abs(v - then), 1, false) + '</text>';
      s += '</g>';
    });
    return s + '</svg>';
  }

  /* КУДА МОГУТ УЙТИ ЦЕНЫ. Владелец 04.09: «пунктиром текущую, как если бы была корреляция
     цен от воздействия Ниньо; указать, куда мы можем уйти в трёх сценариях».
     Прогноза цен у нас нет и быть не может — мы не экономисты и не торгуем зерном. Зато есть
     три прожитых события с их ценовыми путями: индекс FAO в процентах от месяца начала
     события. Продолжаем сегодняшний индекс по каждому из этих путей и подписываем, чей он.
     Сценарии привязаны к силе события: 1997-98 — рекордное, 2015-16 — сильное, 2023-24 —
     базовое. Пути расходятся в РАЗНЫЕ стороны, и это честнее любой одной линии: после
     1997-98 индекс падал (пришёл азиатский кризис), после 2023-24 рос. */
  /* СИЛА НАШЕГО СОБЫТИЯ — В МАСШТАБЕ ПУТИ. Владелец 04.09: «сделать на вкладке since onset
     с учётом реалий текущего состояния динамики и прошлых прогнозов по важным событиям».
     Тонкие сплошные линии на этом графике — что цены делали ТОГДА. Пунктир — та же форма
     пути, но растянутая на отношение пиков: наш ожидаемый пик по ЖИВЫМ моделям делённый на
     пик того события. 1997-98 достиг +2.37, 2015-16 +2.59, 2023-24 +1.99, а живые модели
     сейчас ведут к +3.6 — то есть отклик от каждого аналога усиливается в полтора-два раза.
     Это не прогноз цен: это ответ на вопрос «если цены отзовутся так же, как тогда, только
     соразмерно нынешней силе — куда мы придём». Множитель ограничен сверху, чтобы одна
     слабая аналогия не рисовала фантазию. */
  function onsetPaths(ov, oni, peakNow) {
    var an = ov.analogs || {}, cur = ov.current || {}, vals = cur.values || [], here = -1;
    vals.forEach(function (v, i) { if (v != null) here = i; });
    if (here < 0 || !fin(peakNow)) return [];
    var peaks = (oni || {}).peak_of_analogs || {};
    return Object.keys(an).sort().map(function (y) {
      var a = an[y].values || [], base = a[here], pk = peaks[y];
      if (!fin(base) || !base || !fin(pk) || !pk) return null;
      var f = Math.max(.5, Math.min(2.5, peakNow / pk));
      var path = [];
      for (var i = 0; i < a.length; i++) path.push(i <= here || !fin(a[i]) ? null : vals[here] * (1 + (a[i] / base - 1) * f));
      return { year: y, color: 'var(--a' + y + ')', f: f, peak: pk, path: path };
    }).filter(Boolean);
  }
  /* Ожидаемый пик: сначала живые модели, и только если их нет — оценка по аналогам. */
  function peakExpected(D) {
    var lv = ((D.iri || {}).live || {}).mean || [];
    var m = lv.filter(fin);
    if (m.length) return Math.max.apply(null, m);
    var pe = (D.nino34 || {}).peak_estimate;
    return pe && fin(pe.additive_mid) ? pe.additive_mid : null;
  }

  function chartFood(FO, W, H) {
    var Sr = FO.series, n = Sr.months.length;
    var Lp = 44, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var keys = [['Cereals', 'var(--lv3)'], ['Oils', 'var(--nino)'], ['Meat', 'var(--lv2)'], ['Dairy', 'var(--nina)'], ['Sugar', 'var(--ok)']];
    var all = Sr.index.filter(fin); keys.forEach(function (k) { all = all.concat((Sr.groups[k[0]] || []).filter(fin)); });
    var vmin = Math.min.apply(null, all) - 5, vmax = Math.max.apply(null, all) + 8;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">FAO Food Price Index and groups, last ' + n + ' months (2014–16 = 100)</text>';
    var step = vmax - vmin > 80 ? 20 : 10;
    for (var g = Math.ceil(vmin / step) * step; g < vmax; g += step) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R - 8) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>';
    Sr.months.forEach(function (m, i) { if (m.slice(5) === '01') s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + esc(m.slice(0, 4)) + '</text>'; else if (m.slice(5) === '07' && W > 520) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle" opacity=".55">Jul</text>'; });
    keys.forEach(function (k, ki) { s += segs(Sr.months.map(function (m, i) { var v = (Sr.groups[k[0]] || [])[i]; return [X(i), fin(v) ? Y(v) : NaN]; }), k[1], 1.2, pickOp(k[0], .8), dashOf(ki + 1)); });
    s += segs(Sr.months.map(function (m, i) { return [X(i), fin(Sr.index[i]) ? Y(Sr.index[i]) : NaN]; }), 'var(--text)', 2.6, pickOp('index'));
    s += nowDot(X(n - 1), Y(Sr.index[n - 1]), 'var(--text)', 3.5);
    s += legend([['index ' + fnum(Sr.index[n - 1], 1, false), 'var(--text)', 2.6, '', 'index']]
      .concat(keys.map(function (k, ki) { return [k[0] + ' ' + fnum((Sr.groups[k[0]] || [])[n - 1], 1, false), k[1], 1.4, dashOf(ki + 1), k[0]]; })), W, H, R, Tp);
    return s + '</svg>';
  }

  function chartOverlay(ov, W, H, opts) {
    opts = opts || {};
    var Lp = 44, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var series = [['now (' + ov.onset + ')', ov.current, 'var(--text)', 2.6, 'now']];
    Object.keys(ov.analogs).sort().forEach(function (y) { series.push([y + ' (' + ov.analogs[y].onset + ')', ov.analogs[y], 'var(--a' + y + ')', 1.5, y]); });
    var all = []; series.forEach(function (r) { all = all.concat(r[1].values.filter(fin)); });
    var vmin = Math.min.apply(null, all) - 3, vmax = Math.max.apply(null, all) + 9;
    var n = ov.current.values.length, from = ov.current.from;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + fitText(esc(opts.title || 'Food price index as % of the onset month: this event against analogues'), W, 12) + '</text>';
        /* Шаг сетки — от высоты поля, а не жёсткие пять процентов: в плитке обзора на 150
       пикселей приходилось два десятка подписей, и они сливались в колонку цифр
       (владелец 06.09). */
    var gstep = 5;
    while ((vmax - vmin) / gstep > Math.max(3, Math.floor(ph / 22))) gstep *= 2;
    for (var g = Math.ceil(vmin / gstep) * gstep; g < vmax; g += gstep) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R - 8) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width="' + (g === 100 ? 1.3 : .6) + '"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>';
    var mstep = Math.max(3, 3 * Math.ceil(n / Math.max(1, Math.floor(pw / 26)) / 3));
    /* Крайняя подпись прижимается к краю поля, иначе «+18» наполовину уезжает за картинку
       (владелец 06.09: «подписи иногда заезжают за правый край, например Cocoa since onset»). */
    for (var i = 0; i < n; i++) {
      var m = from + i;
      if (m % mstep !== 0) continue;
      var xx = X(i), edge = W - R - 8;
      var anc = xx > edge - 12 ? 'end' : (xx < Lp + 12 ? 'start' : 'middle');
      s += '<text x="' + Math.min(xx, edge).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + anc + '">' + (m > 0 ? '+' : '') + m + '</text>';
    }
    s += '<line x1="' + X(-from).toFixed(0) + '" y1="' + Tp + '" x2="' + X(-from).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="3 3"/><text x="' + (X(-from) + 3).toFixed(0) + '" y="' + (Tp + 10) + '">onset</text>';
    series.slice(1).forEach(function (r, ri) { s += segs(r[1].values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), r[2], r[3], pickOp(r[4], .9), dashOf(ri + 1)); });
    s += segs(series[0][1].values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), series[0][2], series[0][3], pickOp('now'));
    // куда уходит наш путь, если отклик повторится соразмерно силе события
    var pk = peakExpected(S.D), pp = opts.noProject ? [] : onsetPaths(ov, S.D.oni, pk), here = -1;
    ov.current.values.forEach(function (v, i) { if (v != null) here = i; });
    /* СЫРОЙ ПУТЬ — ОСНОВНОЙ, УСИЛЕНИЕ — ПОЛОСА. Владелец 04.09: «не понимаю теперь график
       since onset: раньше все шли примерно вверх после узла, а теперь все индексы падают».
       Падают они честно: во ВСЕХ трёх прошлых событиях индекс FAO после второго месяца шёл
       ВНИЗ относительно месяца начала (1997-98 −12 %, 2015-16 −14 %, 2023-24 −1 %). Но
       множитель по силе события усиливал и это падение, а падало тогда не от океана —
       от азиатского кризиса и дешёвой нефти. Поэтому теперь основной пунктир — сырой путь
       («повторим ровно то же»), а полоса между ним и усиленным показывает, куда сместится
       ответ, если он и правда соразмерен силе. */
    pp.forEach(function (p) {
      var raw = [[X(here), Y(ov.current.values[here])]], scaled = [[X(here), Y(ov.current.values[here])]];
      p.path.forEach(function (v, i) {
        if (i <= here || !fin(v)) return;
        var rawV = ov.current.values[here] * (1 + (v / ov.current.values[here] - 1) / p.f);
        raw.push([X(i), Y(rawV)]);
        scaled.push([X(i), Y(v)]);
      });
      if (raw.length > 2) {
        var poly2 = raw.map(function (q) { return q[0].toFixed(1) + ',' + q[1].toFixed(1); })
          .concat(scaled.slice().reverse().map(function (q) { return q[0].toFixed(1) + ',' + q[1].toFixed(1); }));
        s += '<polygon points="' + poly2.join(' ') + '" style="fill:' + p.color + '" opacity=".10"/>';
      }
      s += segs(raw, p.color, 1.8, pickOp('rep' + p.year, .95), '4 4');
      s += segs(scaled, p.color, 1, pickOp('rep' + p.year, .55), '1 3');
    });
    if (pp.length) s += '<line x1="' + X(here).toFixed(0) + '" y1="' + Tp + '" x2="' + X(here).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--nino)" stroke-width="1" stroke-dasharray="2 3" opacity=".8"/>' +
      '<text x="' + (X(here) + 3).toFixed(0) + '" y="' + (Tp + 22) + '" style="fill:var(--nino)">today</text>';
    s += legend(series.map(function (r, ri) { return [r[0], r[2], r[3], ri ? dashOf(ri) : '', r[4]]; })
      .concat(pp.map(function (p) { return [p.year + ' path repeated', p.color, 1.8, '4 4', 'rep' + p.year]; }))
      .concat(pp.length ? [['band: path × strength ≤' + Math.max.apply(null, pp.map(function (p) { return p.f; })).toFixed(1), 'var(--soft)', 1, '1 3']] : []), W, H, R, Tp);
    return s + '</svg>';
  }

  /* Ряд аналога под тот же метрик: недельные индексы Niño берём из noaa.analog_series,
     суточную аномалию Niño 3.4 — из nino34.analogs. Владелец 03.09: «на графиках рисков
     нет сравнения с самым сильным событием, которое мы знаем, это 97-98». */
  function analogFor(m) {
    if (!m || !m.name) return null;
    var D = S.D, out = [];
    var wk = { 'Niño 3.4, NOAA weekly': 'n34a' };
    var key = wk[m.name];
    if (key && (D.noaa.analog_series || {})) {
      Object.keys(D.noaa.analog_series || {}).forEach(function (y) {
        var ser = D.noaa.analog_series[y] || [];
        if (ser.length) out.push({ year: y, values: ser.slice(-m.values.length).map(function (r) { return r[key]; }) });
      });
      return out.length ? out : null;
    }
    if (m.name.indexOf('Niño 3.4, daily') === 0 && D.nino34 && D.nino34.analogs) {
      var idx = D.nino34.day, n = m.values.length;
      Object.keys(D.nino34.analogs).forEach(function (y) {
        var a = D.nino34.analogs[y].series || [];
        var seg = a.slice(Math.max(0, idx - n + 1), idx + 1);
        if (seg.length) out.push({ year: y, values: seg });
      });
      return out.length ? out : null;
    }
    return null;
  }

  /* ДАТА НА ОСИ — ПО-ЧЕЛОВЕЧЕСКИ. Владелец 06.09: «внизу сливаются даты по горизонтальной
     оси, надо изменить формат, достаточно трёхбуквенных месяцев, как у других». Ряд знает
     свой шаг: день → «3 Sep», месяц → «Sep 2026», всё остальное (сезоны, кварталы) уже
     приходит готовой подписью. */
  function axisDate(d, step, withYear) {
    var t = String(d == null ? '' : d);
    var m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(t);
    if (!m) return t;
    var mon = MONTHS[parseInt(m[2], 10) - 1] || m[2];
    var yy = " '" + m[1].slice(2);
    if (step === 'day' && m[3]) return parseInt(m[3], 10) + ' ' + mon + (withYear ? yy : '');
    return mon + (withYear ? ' ' + m[1] : '');
  }

  function chartMetric(m, W, H, title) {
    var vals = m.values, dates = m.dates || [], n = vals.length;
    /* Правое поле — под подпись последнего значения. Держать его 76 пикселей в плитке
       шириной 230 значило отдать четверть картинки пустоте (владелец 06.09: «график не во
       всю ширину блока»). Узкой плитке хватает 26. */
    var Lp = 46, R = W < 420 ? 26 : 76, Tp = topPad(W), B = 26, pw = W - Lp - R, ph = H - Tp - B;
    var vv = vals.filter(fin);
    if (vv.length < 2) return svgOpen(W, H) + '<text x="20" y="' + (H / 2) + '">no series for this item</text></svg>';
    var ana = analogFor(m) || [];
    ana.forEach(function (a) { vv = vv.concat(a.values.filter(fin)); });
    /* ШКАЛА ВКЛЮЧАЕТ ВСЁ, ЧТО РИСУЕМ. Ряды прошлых событий и планки считались ПОСЛЕ шкалы —
       и уезжали далеко за поле: у мирового океана своя аномалия +0.74, а у аналогов +0.1,
       шкала строилась по одному нашему ряду шириной в сотые доли, и чужие линии оказывались
       за тысячи пикселей от картинки (владелец 04.09: «для этого риска нет ничего, что бы
       показать для прошлых событий» — они были, просто вне экрана). */
    Object.keys(m.analogs || {}).forEach(function (y) {
      (m.analogs[y] || []).forEach(function (v) { if (fin(v)) vv.push(v); });
    });
    Object.keys(m.levels || {}).forEach(function (y) { if (fin(m.levels[y])) vv.push(m.levels[y]); });
    var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv);
    if (vmax - vmin < 1e-6) vmax = vmin + 1;
    var pad = (vmax - vmin) * .12; vmin -= pad; vmax += pad * 2;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + fitText(esc(title || m.name) +
      ((m.analogs && Object.keys(m.analogs).length) ? ' \u2014 against the same days of the strongest past events' : ''), W, 12) + '</text>';
    // прошлые события тем же календарём, тонко и пунктиром — под нашей линией
    // планки: сколько было в год после пика прошлых событий (для рядов без своих аналогов)
    var LV = m.levels || {}, lvi = 0;
    Object.keys(LV).sort().forEach(function (y) {
      if (!fin(LV[y])) return;
      lvi++;
      s += '<line x1="' + Lp + '" y1="' + Y(LV[y]).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(LV[y]).toFixed(1) +
        '" style="stroke:var(--a' + y + ')" stroke-width="1" stroke-dasharray="' + dashOf(lvi) + '" opacity=".85"/>' +
        '<text x="' + (Lp + 3) + '" y="' + (Y(LV[y]) - 3).toFixed(1) + '" font-size="9" style="fill:var(--a' + y + ')">after ' + esc(y) + ' ' + fnum(LV[y]) + '</text>';
    });
    var MAN = m.analogs || {}, legM = [['now', 'var(--text)', 2.2, '', 'now']];
    Object.keys(MAN).sort().forEach(function (y, k) {
      var av = MAN[y] || [], off = n - av.length;
      s += segs(av.map(function (v, i) { return [X(off + i), fin(v) ? Y(v) : NaN]; }),
        'var(--a' + y + ')', 1.3, pickOp(y, .9), dashOf(k + 1));
      legM.push([y, 'var(--a' + y + ')', 1.3, dashOf(k + 1), y]);
    });
    var step = (vmax - vmin) > 4 ? 1 : ((vmax - vmin) > 1.2 ? .5 : .25);
    s += gridY(vmin, vmax, step, Y, Lp, R, W);
    /* ГОД НА ОСИ — ОДИН РАЗ. Владелец 06.09: «на каких-то графиках пишешь год, на каких-то
       нет; если пишешь, то только в одном положении». Пишем у крайней правой подписи — она
       и есть «сегодня»; остальные подписи только день и месяц. */
    if (dates.length === n) dates.forEach(function (d, i) {
      if (!(i === 0 || i === n - 1 || (n > 6 && i === Math.floor(n / 2)))) return;
      s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + (i === 0 ? 'start' : (i === n - 1 ? 'end' : 'middle')) + '">' +
        esc(axisDate(d, m.step, i === n - 1)) + '</text>';
    });
    // аналоги того же календарного окна — тонкими цветными линиями под нашим рядом
    ana.forEach(function (a, ai) {
      var off = n - a.values.length;
      legM.push([String(a.year), 'var(--a' + a.year + ')', 1.3, dashOf(ai + 1), String(a.year)]);
      s += segs(a.values.map(function (v, i) { return [X(off + i), fin(v) ? Y(v) : NaN]; }), 'var(--a' + a.year + ')', 1.3, pickOp(String(a.year), .85), dashOf(ai + 1));
      var li2 = a.values.length - 1; while (li2 > 0 && !fin(a.values[li2])) li2--;
      // Год у конца линии подписываем, только если справа есть поле: в плитке обзора
      // (узкий график, R=26) эти подписи вылезали за картинку — там их заменяет значок.
      if (fin(a.values[li2]) && !S._tight) s += '<text x="' + (X(off + li2) + 4).toFixed(0) + '" y="' + (Y(a.values[li2]) + 4).toFixed(0) + '" style="fill:var(--a' + a.year + ')" font-size="10">' + a.year + '</text>';
    });
    s += segs(vals.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 2.2, pickOp('now'));
    /* В плитке обзора легенда не помещается и съедает саму картинку: там её заменяет
       значок, а список рядов читатель видит в подсказке плитки (владелец 06.09). */
    if (legM.length > 1) {
      if (W < 420) s += legIcon(legM, W);
      else s += legendAt(legM, Lp + 8, Tp + 12);
    }
    if (m.flags && m.flags.length === n) vals.forEach(function (v, i) { if (m.flags[i] && fin(v)) s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(v).toFixed(1) + '" r="2.2" style="fill:var(--nino)"/>'; });
    var li = n - 1; while (li > 0 && !fin(vals[li])) li--;
    s += nowDot(X(li), Y(vals[li]), 'var(--nino)', 4);
    s += '<text x="' + (X(li) + 7).toFixed(0) + '" y="' + (Y(vals[li]) + 4).toFixed(0) + '" class="tt">' + fnum(Math.abs(vals[li]) < 0.005 ? 0 : vals[li]) + (m.unit && m.unit.length <= 4 ? ' ' + esc(m.unit) : '') + '</text>';
    return s + '</svg>';
  }

  function spark(m, W, H) {
    if (!m || !m.values) return '';
    var vals = m.values, xs = [];
    vals.forEach(function (v, i) { if (fin(v)) xs.push(i); });
    if (xs.length < 2) return '';
    var vv = xs.map(function (i) { return vals[i]; });
    var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv);
    if (vmax - vmin < 1e-6) vmax = vmin + 1;
    var X = function (i) { return 2 + i / (vals.length - 1) * (W - 4); };
    var Y = function (v) { return 2 + (vmax - v) / (vmax - vmin) * (H - 4); };
    /* ПРОШЛЫЕ СОБЫТИЯ ПРЯМО В ИСКРЕ. Владелец 04.09: «желательно, чтобы все карточки рисков
       справа показывали графики со сравнением с событиями, как и везде, а то опять же не с
       чем сравнивать». Аналоги идут по ТОМУ ЖЕ КАЛЕНДАРЮ (тот же день года), тонко и
       пунктиром; наш ряд — сплошной и толще. На двадцати пикселях высоты этого хватает,
       чтобы увидеть главное: выше мы сейчас или ниже, чем были они в это же время года. */
    var AN = m.analogs || {}, ak = Object.keys(AN).sort();
    ak.forEach(function (y) { (AN[y] || []).forEach(function (v) { if (fin(v)) { vmin = Math.min(vmin, v); vmax = Math.max(vmax, v); } }); });
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" style="display:block">';
    ak.forEach(function (y, k) {
      var av = AN[y] || [], off = vals.length - av.length;
      s += segs(av.map(function (v, i) { return [X(off + i), fin(v) ? Y(v) : NaN]; }),
        'var(--a' + y + ')', .9, .8, dashOf(k + 1));
    });
    s += poly(xs.map(function (i) { return [X(i), Y(vals[i])]; }), 'var(--nino)', 1.5);
    var li = xs[xs.length - 1];
    s += '<circle cx="' + X(li).toFixed(1) + '" cy="' + Y(vals[li]).toFixed(1) + '" r="2" style="fill:var(--nino)"/>';
    return s + '</svg>';
  }

  function miniBar(v, ref, w, h) {
    w = w || 74; h = h || 14;
    if (!fin(v) || !fin(ref)) return '';
    var d = v - ref, span = 1.5, x0 = w / 2, x = x0 + Math.max(-span, Math.min(span, d)) / span * (w / 2 - 2);
    return '<span class="mini"><svg viewBox="0 0 ' + w + ' ' + h + '"><line x1="' + x0 + '" y1="1" x2="' + x0 + '" y2="' + (h - 1) + '" style="stroke:var(--grid)"/><rect x="' + Math.min(x0, x).toFixed(1) + '" y="3" width="' + Math.abs(x - x0).toFixed(1) + '" height="' + (h - 6) + '" style="fill:' + (d < 0 ? 'var(--nina)' : 'var(--nino)') + '" opacity=".85"/></svg></span>';
  }

  /* Контекстные ссылки на разобранные работы (tools/enso/links.py): вектор нашёл, модель
     проверила, здесь только показываем. Ссылка означает «вот что об этом говорит наука»,
     а не «отсюда взято это число» — так и подписано. */
  function linksFor(anchor) { return (S.L.anchors || {})[anchor] || []; }
  /* Список работ для подсказки: абзацами, жирным, со ссылкой на популярную английскую версию;
     на компьютере — в новой вкладке, на телефоне просто переход (владелец 05.09). */
  function worksHtml(ls) {
    var tgt = window.matchMedia('(max-width:900px)').matches ? '' : ' target="_blank" rel="noopener"';
    return ls.map(function (l) {
      var u = '/lang/en/archive/' + esc(l.date) + '/' + esc(l.folder) + '/index.html';
      return '<p class="wk-p"><b>' + esc(l.our_title || l.title) + '</b>' + (l.oneliner ? esc(l.oneliner) : '') +
        (l.why ? '<i>' + esc(l.why) + '</i>' : '') + (l.weak ? '<i>more distant match</i>' : '') +
        '<a href="' + u + '"' + tgt + '>read our version ↗</a> <span class="wk-num">arXiv ' + esc(l.id) + '</span></p>';
    }).join('');
  }
  /* Тот же slug, что в tools/enso/links.py (_aslug): менять только вместе. */
  function aslug(t) { return String(t == null ? '' : t).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 48); }
  function linksHtml(anchor, full) {
    var ls = linksFor(anchor);
    if (!ls.length) return '';
    if (!full) {
      /* ЗАМЕТНАЯ ПЛАШКА ВМЕСТО БЛЕДНОГО ЧИПА. Цель дашборда — чтобы разобранные нами работы
         появлялись там, где они к месту (владелец 04.09); значит, их надо ВИДЕТЬ. Плашка той
         же формы, что у ссылок на работы во всём проекте, а в подсказке — НАШ заголовок и
         НАША строка о работе, а не только «почему она здесь». */
      /* КАЖДАЯ РАБОТА — СВОИМ АБЗАЦЕМ И СО ССЫЛКОЙ. Владелец 05.09: «если две работы — не
         понятно, где начинается одна и заканчивается другая; жирным, разными абзацами; и
         нет ссылки на сами работы на наш сайт». Ссылка — на популярную английскую версию;
         на компьютере в новой вкладке, на телефоне просто переход. */
      var pay = { name: ls.length + ' work' + (ls.length > 1 ? 's' : '') + ' we parsed on this', html: worksHtml(ls),
        src: 'our archive, matched by meaning and checked by the model', date: S.L.built };
      return '<span class="lk wk-chip" data-src="' + esc(JSON.stringify(pay)) + '">' + ls.length + ' work' + (ls.length > 1 ? 's' : '') + '</span>';
    }
    return '<div class="lk-h">What the research says about this</div>' + ls.map(function (l) {
      /* Сначала НАШ заголовок и НАША строка: читатель должен понять, о чём работа, не уходя
         со страницы. Авторское название и номер идут подписью снизу. */
      return '<a class="lk-i" href="/lang/en/archive/' + esc(l.date) + '/' + esc(l.folder) + '/index.html"' + (window.matchMedia('(max-width:900px)').matches ? '' : ' target="_blank" rel="noopener"') + '>' +
        '<b>' + esc(l.our_title || l.title) + '</b>' +
        (l.oneliner ? '<span class="lk-one">' + esc(l.oneliner) + '</span>' : '') +
        '<span>' + esc(l.why || '') + '</span><i>' + esc(l.kind || '') +
        (l.weak ? ' · more distant match' : '') +
        ' · <span class="wk-num">arXiv ' + esc(l.id) + '</span></i></a>';
    }).join('') + '<div class="lk-n">Matched by meaning across the works we parsed, then checked by the model: a link means “this is what the research says about this”, not “this is the source of that number”.</div>';
  }

  function dynWords(m) {
    if (!m || !m.values) return '';
    var vv = m.values.filter(fin); if (vv.length < 3) return '';
    var st = STEP[m.step] || { one: 'last step', many: 'steps' };
    var d1 = vv[vv.length - 1] - vv[vv.length - 2];
    var d7 = vv.length >= 8 ? vv[vv.length - 1] - vv[vv.length - 8] : null;
    var k = Math.min(vv.length, 14), tail = vv.slice(-k), sx = 0, sy = 0, sxy = 0, sxx = 0;
    tail.forEach(function (v, i) { sx += i; sy += v; sxy += i * v; sxx += i * i; });
    var sl = (k * sxy - sx * sy) / (k * sxx - sx * sx) * (k - 1);
    var tr = sl > .02 ? 'rising' : (sl < -.02 ? 'falling' : 'holding');
    return 'now <b>' + fnum(vv[vv.length - 1]) + '</b> ' + esc(m.unit || '') + ' · ' + st.one + ' <span class="' + upDown(d1) + '">' + fnum(d1) + '</span>' +
      (d7 != null ? ' · seven ' + st.many + ' <span class="' + upDown(d7) + '">' + fnum(d7) + '</span>' : '') + ' · ' + tr;
  }

  // ---------------------------------------------------------------- shell
  function tile(title, right, cls) {
    var t = el('section', 'tile' + (cls ? ' ' + cls : ''));
    t.appendChild(el('div', 'th', '<span>' + title + '</span>' + (right ? '<span class="rt">' + right + '</span>' : '')));
    var b = el('div', 'tb'); t.appendChild(b); t._b = b;
    return t;
  }

  function buildTabs() {
    var host = $('tabs'); host.innerHTML = '';
    var list = [];
    if (window.matchMedia('(max-width:900px)').matches) list.push(['state', T.railTabs.state], ['risks', T.railTabs.risks]);
    Object.keys(T.tabs).forEach(function (k) { list.push([k, T.tabs[k]]); });
    list.forEach(function (v) {
      /* Служебные вкладки (метод, цепочка, о панели) выглядят иначе: пунктирная рамка,
         приглушённый цвет; вердикт — контрастный чёрно-белый. У каждой — подсказка,
         что это (владелец 05.09). */
      var svc = v[0] === 'how' || v[0] === 'chain' || v[0] === 'about' || v[0] === 'refs';
      /* Подсказка к пункту меню — на значке «i» справа от текста, а не на самой кнопке
         (владелец 05.09: «для меню неудобно тултипы — пусть будет небольшая иконка i»). */
      var b = el('button', 'tab' + (v[0] === 'verdict' ? ' verdict' : '') + (svc ? ' svc' : '') + (S.view === v[0] ? ' on' : ''),
        esc(v[1]) + (T.tabHelp[v[0]] ? '<i class="ti" data-src="' + esc(JSON.stringify({ name: v[1], def: T.tabHelp[v[0]] })) + '">i</i>' : ''));
      b.type = 'button';
      b.onclick = function (e) { if (e.target.closest && e.target.closest('.ti')) return; S.view = v[0]; S.risk = null; render(); };
      host.appendChild(b);
    });
    var t = $('deltaBtn');
    if (t) {
      t.className = 'tab delta' + (S.delta ? ' on' : '');
      t.textContent = S.delta === 'update' ? 'change since last update'
        : (S.delta === 'week' ? 'change since a week ago' : 'now');
      t.title = 'Switch between the values, the change since the previous update, and the change since a week ago';
    }
  }

  /* Верхняя строка: когда собрано, докуда дотянулись ряды и что с каждым источником. */
  function buildMeta() {
    var D = S.D, n34 = D.watch.sst_nino34, tw = D.watch.t2_world, P = S.P;
    var host = $('pmeta'); host.innerHTML = '';
    function item(text, payload, cls) {
      var sp = el('span', cls || '');
      sp.setAttribute('data-src', JSON.stringify(payload));
      sp.innerHTML = text;
      host.appendChild(sp);
    }
    item('<b>updated</b> ' + esc((D.stamp || '').slice(0, 10)), { name: 'This update', def: 'The panel was recomputed at ' + D.stamp + (P ? '; the previous update was at ' + P.stamp + '.' : '.') + ' Updating is semi-automatic: a person runs it and looks at the result before it goes out.', src: 'this panel, recomputed by hand after each release', date: D.generated });
    item('<b>daily</b> ' + esc(n34.last_date) + ' <i>' + n34.days_stale + ' d ago</i>', { name: 'Daily series', def: 'Niño 3.4 and the world ocean: final OISST from climatereanalyzer' + (n34.prelim_from ? ' to ' + addDays(n34.prelim_from, -1) + ', then the preliminary NOAA grid (NRT) spliced on directly, one day behind; the last two weeks are re-pulled every update' : ', which lags one to three weeks') + '. Land+ocean (ERA5) reaches ' + tw.last_date + '.', src: n34.prelim_from ? 'climatereanalyzer.org + NOAA OISST NRT via ERDDAP' : 'climatereanalyzer.org', date: n34.last_date }, n34.days_stale > 14 ? 'bad' : '');
    item('<b>NOAA week</b> ' + esc(D.noaa.date), { name: 'NOAA weekly indices', def: 'Published every Wednesday for the previous week; always fresher than the daily OISST, and where they disagree the panel trusts the weekly.', src: 'NOAA CPC wksst9120.for', date: D.noaa.date });
    if (D.iri && D.iri.issued) item('<b>IRI</b> ' + esc(D.iri.issued), { name: 'IRI model plume', def: 'The forecasts of two dozen centres, published around the 19th of each month. ' + ((D.iri.class_issues || []).length) + ' issues are stored here, which is what makes the model scoreboard possible.', src: 'iri.columbia.edu', date: D.iri.issued });
    if (D.food && !D.food.error) item('<b>FAO</b> ' + esc(D.food.last_month), { name: 'FAO Food Price Index', def: 'Monthly, published on the first Friday for the previous month: the only live food series available without registration.', src: 'fao.org', date: D.food.last_month });
    /* РЯДА ТОЧЕК БОЛЬШЕ НЕТ. Он горел всегда и потому не значил ничего; откуда взято
       и за когда — теперь на каждом кирпиче отдельно (владелец 04.09). Осталась одна
       строка и только когда есть о чём сказать: источник не ответил. */
    /* В шапке — только «updated» (владелец 05.09: «источников много — просто updated
       оставить, всё убрать»); свежесть каждого источника живёт на Data chain и References. */
    Array.prototype.slice.call(host.children, 1).forEach(function (c) { host.removeChild(c); });
    var stale = Object.keys(D.sources).filter(function (q) { return !D.sources[q].fresh; });
    if (false && stale.length) {
      item('<b>stale</b> ' + stale.length, { name: 'Sources that did not answer', def: stale.map(function (q) { return D.sources[q].label + ': ' + (D.sources[q].error || 'no answer'); }).join('; ') + '. The panel is showing the last good value for these.', src: 'our fetch log', date: (D.stamp || '').slice(0, 10) }, 'bad');
    }
  }

  // ---------------------------------------------------------------- rails
  // куда ведёт тревога каждого вида
  var ALERT_GO = {
    climate: { view: 'now', sub: 'analogs', label: 'see the series' },
    food: { view: 'food', sub: 'goods', label: 'see the prices' },
    models: { view: 'models', sub: 'breakdown', label: 'see the models' },
    data: { view: 'how', sub: 'sources', label: 'see the sources' }
  };
  function alertCard(a, i) {
    var c = el('div', 'card alert-card ' + (a.level === 'SHOUT' ? 'lv-shout' : 'lv-watch') + ' kind-' + (a.kind || 'climate'));
    var isNew = S.P && S.P.alerts && S.P.alerts.indexOf(a.title) < 0;
    c.innerHTML = '<div class="ch"><b>' + esc(a.level) + '</b><span class="kk">' + esc(a.kind || 'climate') + '</span>' + (isNew ? '<span class="new">new</span>' : '') + '</div>' +
      '<div class="ct">' + mark(a.title) + '</div><div class="cd">' + mark(a.detail) + '</div>' +
      '<div class="cgo">' + esc(ALERT_GO[a.kind || 'climate'].label) + ' →</div>' + (linksHtml('alert:' + aslug(a.title)) || linksHtml('alert:' + i));
    /* КАРТОЧКА ТРЕВОГИ ВЕДЁТ ТУДА, ГДЕ ЕЁ ЧИСЛА. Владелец 04.09: «слева карточки, они же тоже
       могут вести на какие-то риски или наши графики навигации». Тревога — это утверждение,
       и у каждого утверждения на панели есть своя сцена: климат живёт в рядах, цены в товарах,
       модели в плюме, а «источник молчит» — в списке источников. Клик по ссылке в конце
       карточки открывает именно её; клик по самой карточке не трогаем, чтобы не мешать
       выделять текст. */
    var go = ALERT_GO[a.kind || 'climate'];
    c.querySelector('.cgo').setAttribute('data-go', go.view);
    if (go.sub) c.querySelector('.cgo').setAttribute('data-gosub', go.sub);
    return c;
  }

  function railState() {
    var D = S.D, N = D.nino34, NW = D.noaa, ONI = D.oni, sm = D.summary || {}, P = S.P;
    var col = $('railL'); col.innerHTML = '';
    var t = tile('State', term('type', 'event type: ' + NW.type), 'grow');
    var idx = D.risk_index, gc = idx >= 80 ? 'var(--lv5)' : (idx >= 60 ? 'var(--lv4)' : (idx >= 40 ? 'var(--lv3)' : 'var(--ok)'));
    var ls = ONI.last_season;
    var ri = pair(idx, P ? P.risk_index : null, 0);
    var box = el('div', 'cards');

    // 1. KPI-карточка состояния
    var k1 = el('div', 'card kpi-card');
    // Подпись шкалы стоит СНАРУЖИ круга: внутри она не помещалась и обрезалась
    // (владелец 03.09: «в кружок текст не поместился, вынеси его»).
    k1.innerHTML = '<div class="gauge-row"><div class="gauge' + (idx >= 70 ? ' hot' : '') + '" data-term="riskindex" style="--v:' + idx + ';--c:' + gc + '"><div class="gv">' + idx + '</div></div>' +
      '<div class="g-side">' + '<button type="button" class="vgo" data-view="verdict">read the verdict →</button>' + '<b>' + zone('nino34') + ' ' + fnum(NW.latest.n34a, 1) + ' °C</b>' +
      'rank ' + N.all_years_rank + ' of all years on the same 30 days. ' + term('oni', 'ONI') + ' ' + fnum(ONI.current[ls]) + ' (' + esc(ls) + ').' +
      '' + kmeta('risk_index') +
      '<div class="cgo" data-go="now" data-gosub="analogs">see where we are \u2192</div></div></div>';
    box.appendChild(k1);

    // 2. тревоги карточками, по видам
    var alerts = D.alerts || [];
    ['climate', 'food', 'models'].forEach(function (kind) {
      alerts.forEach(function (a, i) { if ((a.kind || 'climate') === kind) box.appendChild(alertCard(a, i)); });
    });
    if (!alerts.length) box.appendChild(el('div', 'card quiet', '<div class="ct">The watchdog sees no turning point</div><div class="cd">No rule fired: no record broken, no reversal, no run of records ended.</div>'));

    // 3. карточка «как ломаются модели»
    var bd = (D.iri || {}).breakdown, rv = (D.iri || {}).revisions || {};
    if (bd && (bd.by_issue || []).length) {
      var rows = bd.by_issue, first = rows[0], last = rows[rows.length - 1];
      var chronic = (bd.chronic || []).filter(function (c) { return c.of >= 3 && c.issues_low >= Math.max(3, c.of * 0.6); });
      var c3 = el('div', 'card models-card');
      c3.innerHTML = '<div class="ch"><b>MODELS</b><span class="kk">since ' + esc(first.issue) + '</span></div>' +
        '<div class="ct">' + last.share + ' % of models are below reality, against ' + first.share + ' % a year ago</div>' +
        '<div class="cd">Verified on ' + rows.length + ' issues: for each we take its nearest season that already has an official ONI. The average model error went ' +
        fnum(first.mean_err) + ' → ' + fnum(last.mean_err) + ' °C.</div>' +
        (chronic.length ? '<div class="cd chronic">Below reality in most issues: ' + chronic.slice(0, 5).map(function (c) { return modelSpan(c.model, c.model) + ' ' + c.issues_low + '/' + c.of; }).join(', ') + '</div>' : '') +
        (rv && rv.combined_peak_prev != null ? '<div class="cd">Since the ' + esc(rv.prev_issued || '') + ' issue the combined peak went ' + fnum(rv.combined_peak_prev) + ' → ' + fnum(rv.combined_peak_cur) + ' °C; ' + rv.n_up + ' of ' + rv.n + ' models raised it. The next issue is due around the 19th.</div>' : '') +
        '<div class="spark">' + sparkBars(rows) + '</div>' +
        '<div class="cgo" data-go="models" data-gosub="breakdown">see how they break \u2192</div>' + linksHtml('block:models');
      box.appendChild(c3);
    }

    // 4. вердикт модели
    var tp = sm.turning_point || {}, cav = Array.isArray(sm.caveats) ? sm.caveats : (sm.caveats ? [sm.caveats] : []);
    var v = el('div', 'card verdict');
    v.innerHTML = '<div class="ch"><b>VERDICT</b><span class="kk">' + (sm.error ? 'rules' : esc(sm.model || '')) + '</span></div>' +
      '<p class="vv' + (D.shout ? ' on' : '') + '">' + mark(sm.verdict || '') + '</p>' +
      '<dl><dt>turning point</dt><dd>' + (tp.happened ? 'yes' : 'no') + ': ' + esc(tp.why || '') + '</dd>' +
      '<dt>2–3 weeks</dt><dd>' + esc(sm.outlook_2_3w || '') + '</dd>' +
      '<dt>what changed</dt><dd>' + esc(sm.changed || '') + '</dd>' +
      '<dt>what to watch</dt><dd><ul>' + (sm.watch || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></dd>' +
      '<dt>confidence</dt><dd>' + esc(sm.confidence || '') + '</dd>' +
      '<dt>caveats</dt><dd><ul>' + cav.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></dd></dl>' +
      '<div class="cgo" data-go="verdict">open the full verdict \u2192</div>';
    box.appendChild(v);
    t._b.appendChild(box);
    col.appendChild(t);
  }

  function sparkBars(rows) {
    var W = 230, H = 30, n = rows.length, bw = W / n;
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="' + H + '" style="display:block">';
    rows.forEach(function (r, i) {
      var h = Math.max(1, r.share / 100 * (H - 2));
      s += '<rect x="' + (i * bw + 1).toFixed(1) + '" y="' + (H - h).toFixed(1) + '" width="' + (bw - 2).toFixed(1) + '" height="' + h.toFixed(1) + '" style="fill:var(--nino)" opacity="' + (0.35 + 0.5 * r.share / 100).toFixed(2) + '" rx="1"/>';
    });
    return s + '</svg>';
  }

  function railRisks() {
    var D = S.D, col = $('railR'); col.innerHTML = '';
    var risks = D.risks || [], P = S.P;
    var t = tile('Risks', risks.length + ' · index ' + D.risk_index + (P ? ' ' + chg(D.risk_index, P.risk_index, 0) : ''), 'grow');
    t._b.classList.add('flush');
    var box = el('div'); box.style.padding = '0 10px 8px';
    risks.forEach(function (r, i) {
      /* Стрелка на карточке риска — из журнала, по имени риска, а не по заголовку: заголовок
         может смениться, уровень должен идти подряд (владелец 04.09). */
      var jr = jrec('risk:' + (r.id || '')), je = jr ? (jr.entries || []) : [];
      var wasJ = je.length > 1 ? je[je.length - 2] : null;
      var was = P && P.risks ? P.risks[r.title] : null;
      var c = el('div', 'risk' + (S.risk === i ? ' on' : ''));
      c.innerHTML = '<div class="rl" style="background:' + lvlColor(r.level) + '">' + r.level + '</div>' +
        '<div><div class="rt">' + mark(r.title) + (was == null && P ? ' <span class="new">new</span>' : '') + '</div>' +
        '<div class="rh">' + esc(r.horizon) + (wasJ ? ' · <span class="' + jsign(r.level - wasJ.v) + '">' + jarrow(r.level - wasJ.v) + ' was ' + wasJ.v + ' on ' + esc(wasJ.d) + '</span>' : '') + (r.metric ? ' · ' + esc(r.metric.name) : '') + '</div>' +
        (r.metric ? '<div class="rs">' + spark(r.metric, 200, 24) + '</div>' : '') +
        '<div class="rf">' + (linksHtml('risk:' + (r.id || '')) || '') + (jr ? '<button type="button" class="jh" data-hist="risk:' + esc(r.id) + '">history</button>' : '') +
        dateBadge(null, (r.metric ? r.metric.name : 'this rule'), (r.metric && r.metric.dates ? String(r.metric.dates[r.metric.dates.length - 1]) : (je.length ? je[je.length - 1].d : '')), r.title) + '</div></div>';
      c.onclick = function (e) {
        if (e.target.closest('[data-hist]')) return;      // кнопка истории живёт своей жизнью
        S.risk = (S.risk === i ? null : i); S.view = S.risk == null ? 'now' : 'risk'; render();
      };
      box.appendChild(c);
    });
    t._b.appendChild(box);
    col.appendChild(t);
  }

  // ---------------------------------------------------------------- stage
  function stageShell(title, segs2) {
    var st = $('stage'); st.innerHTML = '';
    var head = el('div', 'stage-head');
    head.appendChild(el('div', 'stage-h', title));
    if (segs2 && segs2.length) {
      var seg = el('div', 'seg');
      segs2.forEach(function (b) {
        var btn = el('button', b.on ? 'on' : '', esc(b.label) + (b.help ? '<i class="ti" data-src="' + esc(JSON.stringify({ name: b.label, def: b.help })) + '">i</i>' : '')); btn.type = 'button';
        btn.onclick = function (e) { if (e.target.closest && e.target.closest('.ti')) return; b.click(e); };
        seg.appendChild(btn);
      });
      head.appendChild(seg);
    }
    st.appendChild(head);
    var body = el('div', 'stage-body');
    st.appendChild(body);
    return body;
  }
  /* ГРАФИК МЕРЯЕТ СЕБЯ, А НЕ СЦЕНУ. Владелец 04.09: «где-то я бродил, и график сжался —
     чтобы все графики по ширине не сбивались». Причина: рисовали сразу при вставке, а
     соседей по сцене (подпись, ряд KPI, врезку) добавляли ПОСЛЕ — в гибкой раскладке они
     отбирали ширину уже у нарисованного. Картинка тянется по viewBox, поэтому готовый SVG
     честно сплющивался. Наблюдатель теперь висит на самой рамке графика: ширина сцены
     могла и не поменяться, а его — да. Память о последнем размере снимает лишние
     перерисовки и петлю: перерисовка размер рамки не меняет.
     НО НАБЛЮДАТЕЛЮ ВЕРИТЬ НЕЛЬЗЯ: в встроенном браузере ResizeObserver молчит вовсе —
     проверено, ни одного вызова, включая первый. Поэтому главный ход другой: рамку
     вставляем пустой, а рисуем в конце render(), когда сцена собрана и высота у рамки
     окончательная. Наблюдатель остаётся вторым рубежом для настоящих браузеров. */
  var plotRO = window.ResizeObserver ? new ResizeObserver(function () { redrawPlot(); }) : null;
  function plot(body, draw) {
    var p = el('div', 'plot');
    // Клик по элементу легенды выделяет линию (или целый класс), повторный — снимает.
    p.addEventListener('click', function (e) {
      var g = e.target.closest && e.target.closest('[data-pick]');
      if (!g) return;
      var v = g.getAttribute('data-pick');
      S.pick = (S.pick === v || !v) ? null : v;
      render();
    });
    body.appendChild(p);
    S.plotEl = p; S.draw = draw; S.pw = 0; S.ph = 0;
    // дата данных — значок в правом нижнем углу поля графика
    var wrapB = el('span', 'dcal-wrap', dateBadge(plotKey(draw)));
    p.appendChild(wrapB);
    if (plotRO) { plotRO.disconnect(); plotRO.observe(p); }
  }
  function redrawPlot() {
    var p = S.plotEl;
    if (!p || !S.draw || !p.isConnected) return;
    var badge = p.querySelector('.dcal-wrap');
    var w = Math.max(220, Math.round(p.clientWidth)), h = Math.max(150, Math.round(p.clientHeight));
    if (w === S.pw && h === S.ph) return;
    S.pw = w; S.ph = h;
    /* ЗАГОЛОВОК ГРАФИКА РЕЖЕТСЯ ПО ШИРИНЕ — ОДНИМ МЕСТОМ НА ВСЕ ГРАФИКИ. Текст в SVG не
       переносится и не обрезается сам: на телефоне подписи уезжали за правый край. Править
       четырнадцать мест сборки строк — напрашиваться на опечатку (одну уже поймали), поэтому
       чиним готовую картинку: у заголовка своя примета (class="tt" на строке y="13"), и
       только он подрезается по числу знаков, которые влезают. */
    p.innerHTML = String(S.draw(w, h)).replace(
      /(<text class="tt"[^>]*y="13"[^>]*>)([^<]{1,400})(<\/text>)/,
      // текст уже экранирован сборщиком — повторно не экранируем, только режем
      function (all, head, txt, tail) { return head + fitText(txt, w, 12) + tail; });
    if (badge) p.appendChild(badge);           // значок даты данных переживает перерисовку
  }
  /* ══ ЖУРНАЛ ЗНАЧЕНИЙ НА КИРПИЧЕ ══════════════════════════════════════════════
     Владелец 04.09: «изменение данных не равно времени обновления… на каждом кирпичике
     стрелочка, выросла или снизилась, и дата значения». Панель до сих пор сравнивала с
     ПРОШЛЫМ ПРОГОНОМ: недельный индекс NOAA выходит раз в неделю, прогонов за сутки
     шесть — и пять раз из шести кирпич честно писал «не изменилось», хотя не изменился
     не показатель, а наш будильник. Здесь всё считается по data/enso/journal.json, где
     запись появляется только при смене САМОГО ЗНАЧЕНИЯ или даты данных под ним. */
  function jrec(k) { var m = (S.J || {}).metrics || {}; return k && m[k] ? m[k] : null; }
  function jsign(dv) { return dv > 0 ? 'up' : (dv < 0 ? 'dn' : 'same'); }
  function jarrow(dv) { return dv > 0 ? '↑' : (dv < 0 ? '↓' : '='); }
  function jval(v, dg) { return (typeof v === 'number') ? v.toFixed(dg == null ? 2 : dg) : esc(String(v)); }
  function jdelta(a, b, dg) {
    // Не всякий показатель — число: «сценарий в силе» это слово. Для слов стрелка не имеет
    // смысла, и мы показываем сам переход, а не разность.
    if (typeof a !== 'number' || typeof b !== 'number')
      return '<b class="same">' + esc(String(b)) + ' → ' + esc(String(a)) + '</b>';
    var dv = a - b;
    return '<b class="' + jsign(dv) + '">' + jarrow(dv) + ' ' + (dv > 0 ? '+' : '') + jval(dv, dg) + '</b>';
  }
  /* Подпись под числом. src0/date0 — для кирпичей, у которых своего ряда в журнале нет
     (сводные и производные): стрелок не будет, но откуда и за когда — будет всегда. */
  /* ДАТА ДАННЫХ — ЗНАЧКОМ В ПРАВОМ НИЖНЕМ УГЛУ. Владелец 05.09: «нам не важно, когда
     обновлялся дашборд — важно, когда изменились данные; на всех визуалах и KPI — маленький
     календарь с подсказкой». Дата берётся из журнала значений (смена данного, а не опрос);
     если ряда в журнале нет — дата, которую назвал сам блок; и только в крайнем случае —
     штамп пересчёта, честно так и подписанный. */
  var CAL_SVG = '<svg viewBox="0 0 12 12" width="11" height="11" aria-hidden="true"><rect x="1" y="2.5" width="10" height="8.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.1"/><line x1="1" y1="5.2" x2="11" y2="5.2" stroke="currentColor" stroke-width="1.1"/><line x1="3.8" y1="1" x2="3.8" y2="3.5" stroke="currentColor" stroke-width="1.1"/><line x1="8.2" y1="1" x2="8.2" y2="3.5" stroke="currentColor" stroke-width="1.1"/></svg>';
  function dateBadge(k, src0, date0, title0) {
    var r = k ? jrec(k) : null, e = r ? (r.entries || []) : [], last = e[e.length - 1];
    var pay;
    if (last) pay = { name: 'Data date · ' + (r.title || k), def: 'The data behind this changed on ' + last.d + ' (we saw it ' + (last.seen || '').slice(0, 10) + ').' + (e.length > 1 ? ' Before that: ' + e[e.length - 2].d + '.' : ' First reading we hold.'), src: r.src || '', date: last.d };
    else if (date0) pay = { name: 'Data date · ' + (title0 || src0 || ''), def: 'The data behind this is dated ' + date0 + '.', src: src0 || '', date: date0 };
    else pay = { name: 'Data date', def: 'No separate data date for this piece: it was recomputed with the panel at ' + (S.D.stamp || '') + '.', src: 'our pipeline', date: (S.D.stamp || '').slice(0, 10) };
    return '<span class="dcal" data-src="' + esc(JSON.stringify(pay)) + '">' + CAL_SVG + '</span>';
  }
  /* Какой ряд журнала стоит за графиком: по имени функции внутри отрисовщика, чтобы не
     трогать сорок мест вызова. */
  var PLOT_KEY = [
    [/chartAnalogs|chartRecent\(w0|sst_nino34/, 'n34_daily'], [/pacific|chartNoaa/, 'n34_weekly'],
    [/chartPlume|chartStack|chartBreakdown/, 'iri_peak'], [/chartAir/, 'soi'], [/chartFuel/, 'wwv'], [/chartLayers/, 'tlt_tropics'],
    [/chartWind/, 'wind_week'], [/chartMJO/, 'mjo_amp'], [/chartFood|chartOverlay/, 'food_index'], [/chartOHC/, 'ohc_2000'],
    [/chartKuwait/, 'kuwait_tmax30'], [/chartHistory/, 'risk_index'], [/boxMetric\(bx/, 'n34_box'], [/title: 'Persian Gulf'/, 'gulf_sst'],
    [/get: function \(i, j\) \{ return good/, 'subsurface_warmest'], [/GD\.labels/, 'subsurface_warmest'], [/blk\.title/, 'dmi']
  ];
  function plotKey(draw) {
    var src = String(draw);
    for (var i = 0; i < PLOT_KEY.length; i++) if (PLOT_KEY[i][0].test(src)) return PLOT_KEY[i][1];
    return null;
  }
  function kmeta(k, src0, date0) {
    var r = jrec(k), out = '<div class="kj">';
    if (!r) {
      if (!src0 && !date0) return '';
      return out + '<div class="jsrc"><span>' + mark(src0 || '') + (date0 ? ' · ' + esc(date0) : '') + '</span>' + dateBadge(null, src0, date0) + '</div></div>';
    }
    var e = r.entries || [], last = e[e.length - 1], prev = e[e.length - 2], dg = r.digits;
    if (last && prev) out += '<div class="jr">' + jdelta(last.v, prev.v, dg) + ' since ' + esc(prev.d) + '</div>';
    else out += '<div class="jr same">first reading we hold</div>';
    if (last && r.since_event)
      out += '<div class="jr">' + jdelta(last.v, r.since_event.v, dg) + ' since the event began, ' + esc(r.since_event.d) + '</div>';
    /* СТРОКА ИСТОЧНИКА — ТОЖЕ ПОДСКАЗКА, И БЕЗ ОБРЫВА. Владелец 04.09: «что там за многоточия
       в тексте, немного почётче пиши». Многоточие рисовала обрезка по ширине: длинное имя
       источника не влезало в строку кирпича. Теперь подпись переносится и сама стала якорем:
       по наведению видно, что это за ряд, откуда он и за какое число. */
    var srcPay = { name: r.title || k,
      def: (r.title || k) + ' — the series behind this number. ' +
        (r.since_event ? 'Since the event began (' + r.since_event.d + '): ' + jval(r.since_event.v, dg) + '. ' : '') +
        ((r.entries || []).length > 1 ? 'We hold ' + r.entries.length + ' changes of this value.'
          : 'This is the first reading we hold.'),
      src: r.src || '', date: last ? last.d : '' };
    out += '<div class="jsrc"><span data-src="' + esc(JSON.stringify(srcPay)) + '">' + mark(r.src || '') +
      (last ? ' · ' + esc(last.d) : '') + '</span>' +
      '<button type="button" class="jh" data-hist="' + esc(k) + '">history</button>' + dateBadge(k) + '</div>';
    return out + '</div>';
  }
  /* Стрелка в одну щепотку — для фишек под графиками, где целой строке журнала нет места
     (владелец 04.09: «где на KPI стрелочки изменения от прошлого, я их не вижу»). */
  function jchip(k) {
    var r = jrec(k), e = r ? (r.entries || []) : [];
    if (e.length < 2) return '';
    var last = e[e.length - 1], prev = e[e.length - 2];
    if (typeof last.v !== 'number' || typeof prev.v !== 'number') return '';
    var dv = last.v - prev.v;
    if (!dv) return '';
    return ' <span class="' + jsign(dv) + '" data-src="' + esc(JSON.stringify({ name: r.title, def: 'Was ' + prev.v + ' on ' + prev.d + ', now ' + last.v + ' on ' + last.d + '. The arrow follows changes of the data, not our refreshes.', src: r.src, date: last.d })) + '">' +
      jarrow(dv) + ' ' + (dv > 0 ? '+' : '') + jval(dv, r.digits) + '</span>';
  }

  /* Карточка истории: последние восемь изменений и кнопка «все» (владелец 04.09). */
  function histHtml(k, all) {
    var r = jrec(k);
    if (!r) return '<b>No history</b>This number is not in the value journal yet.';
    var e = (r.entries || []).slice().reverse(), n = e.length, dg = r.digits;
    var rows = all ? e : e.slice(0, 8);
    var s = '<b>' + esc(r.title || k) + '</b>' +
      'Every line is a change of the DATA, not of our refresh: the panel can update six times a day and this list stay still.' +
      '<table class="htab">' + rows.map(function (x, i) {
        var nx = rows[i + 1];
        return '<tr><td>' + esc(x.d) + '</td><td class="v">' + jval(x.v, dg) + (r.unit ? ' ' + esc(r.unit) : '') +
          '</td><td class="a">' + (nx ? jdelta(x.v, nx.v, dg) : '') + '</td></tr>';
      }).join('') + '</table>';
    if (!all && n > 8) s += '<button type="button" class="hmore" data-histall="' + esc(k) + '">all ' + n + ' changes</button>';
    if (r.since_event) s += '<span class="s">Since the event began (' + esc(r.since_event.d) + '): ' + jval(r.since_event.v, dg) + '</span>';
    s += '<span class="s">' + esc(r.src || '') + '</span>';
    return s;
  }

  function segBtn(view, key, label, defKey) {
    return { help: T.subHelp[view + '/' + key] || '', label: label, on: sub(view, defKey) === key, click: function () { S.sub[view] = key; render(); } };
  }

  /* ══ ВЕРДИКТ ОТДЕЛЬНОЙ СЦЕНОЙ ═══════════════════════════════════════════════════
     Владелец 04.09: «слева вердикт первое продублировать отдельной вкладкой меню, его
     проходишь сам аккуратно, проверяешь, со ссылками если надо на страницы дашборда,
     тултипами как положено, тоже history чтобы там было, и выносишь кнопкой под индекс
     риска». В левой колонке вердикт ужат до трёх строк и читается плохо; здесь он целиком,
     каждое утверждение с кнопкой перехода на ту сцену, где это число живёт, и с историей
     прошлых вердиктов — а она показывает не то, как мы обновлялись, а то, как менялась
     сама оценка. */
  function vLink(label, view, sub2) {
    return '<button type="button" class="vgo" data-view="' + esc(view) + '"' +
      (sub2 ? ' data-sub="' + esc(sub2) + '"' : '') + '>' + esc(label) + ' \u2192</button>';
  }

  function viewVerdict() {
    var D = S.D, sm = D.summary || {}, J = S.J || {};
    var k = sub('verdict', 'now');
    var body = stageShell(D.shout ? 'The watchdog is shouting' : 'What the machine makes of it today',
      [segBtn('verdict', 'now', 'Today', 'now'), segBtn('verdict', 'history', 'How it changed', 'now')]);
    body.classList.add('scroll');

    if (k === 'history') {
      var vs = (J.verdicts || []).slice().reverse();
      if (!vs.length) { body.appendChild(el('div', 'note', 'No stored verdicts yet.')); return; }
      var g = el('div', 'gloss');
      g.innerHTML = vs.map(function (x) {
        return '<div class="gl-i"><b>' + esc(x.d || '') + (x.shout ? ' \u00b7 ALERT' : '') + '</b>' + mark(x.v) +
          '<div class="s">risk index ' + (x.risk_index == null ? '\u2014' : x.risk_index) + ' \u00b7 ' + esc(x.model || '') + '</div></div>';
      }).join('');
      body.appendChild(g);
      body.appendChild(el('div', 'cap', 'Only the changes are kept: the model writes a verdict on every update, but while the numbers stay put it repeats itself word for word. ' +
        vs.length + ' distinct verdicts are stored.'));
      return;
    }

    var tp = sm.turning_point || {}, cav = Array.isArray(sm.caveats) ? sm.caveats : (sm.caveats ? [sm.caveats] : []);
    var lead = el('div', 'lead');
    lead.innerHTML = '<b>' + (sm.error ? 'By rules, without the model' : esc(sm.model || 'model') + ', supervised by ' + CREW.supervisor) + ':</b> ' + mark(sm.verdict || '');
    body.appendChild(lead);

    var rows = [
      ['Turning point', (tp.happened ? 'Yes. ' : 'No. ') + (tp.why || ''), 'now', 'analogs'],
      ['Next two or three weeks', sm.outlook_2_3w || '', 'trend', 'sst_nino34'],
      ['What changed since the previous update', sm.changed || '', 'how', 'changed'],
      ['Confidence', sm.confidence || '', 'how', 'method']
    ];
    var dl = el('div', 'gloss');
    dl.innerHTML = rows.filter(function (r) { return r[1]; }).map(function (r) {
      return '<div class="gl-i"><b>' + esc(r[0]) + '</b>' + mark(r[1]) + '<div class="s">' + vLink('open the numbers', r[2], r[3]) + '</div></div>';
    }).join('') +
      '<div class="gl-i"><b>What to watch</b><ul>' + (sm.watch || []).map(function (x) { return '<li>' + mark(x) + '</li>'; }).join('') +
      '</ul><div class="s">' + vLink('risks and their series', 'now', 'analogs') + ' ' + vLink('models', 'models', 'plume') + ' ' + vLink('air and fuel', 'air', 'fuel') + '</div></div>' +
      (cav.length ? '<div class="gl-i"><b>Caveats</b><ul>' + cav.map(function (x) { return '<li>' + mark(x) + '</li>'; }).join('') + '</ul>' +
        '<div class="s">' + vLink('sources and freshness', 'how', 'sources') + '</div></div>' : '');
    body.appendChild(dl);

    var kp = el('div', 'kpis');
    kp.innerHTML = '<div class="kpi"><div class="kn">' + term('riskindex', 'risk index') + '</div><div class="kv">' + D.risk_index + '<small>of 100</small></div><div class="km">' + (D.risks || []).length + ' risks on the board, ' + (D.alerts || []).length + ' alerts</div>' + kmeta('risk_index') + '</div>' +
      '<div class="kpi"><div class="kn">verdicts stored</div><div class="kv" style="font-size:17px">' + ((J.verdicts || []).length) + '</div><div class="km">only the ones that actually changed</div>' + kmeta(null, 'our own record', (J.built || '').slice(0, 10)) + '</div>' +
      '<div class="kpi"><div class="kn">the machine</div><div class="kv" style="font-size:15px;line-height:1.25">' + esc(sm.model || 'rules') + '<br><small style="margin:0">supervised by ' + esc(CREW.supervisor) + '</small></div><div class="km">' + (sm.error ? esc(sm.error) : 'DeepSeek writes the verdict from the numbers on this page; Fable reads it against the same numbers before it goes out') + '</div>' + kmeta(null, 'our pipeline', (D.stamp || '').slice(0, 10)) + '</div>';
    body.appendChild(kp);
    body.appendChild(el('div', 'cap', 'The verdict is an interpretation of our own numbers by a language model, not a source. Every claim in it can be checked on the scene it came from \u2014 the buttons above lead there. When the model is unavailable, the same block is filled by rules and says so.'));
  }

  function viewNow() {
    var D = S.D, N = D.nino34, NW = D.noaa, ONI = D.oni, n34 = D.watch.sst_nino34, P = S.P;
    var k = sub('now', 'analogs');
    var above = Object.keys(N.analogs).every(function (y) { return N.analogs[y].same30 < N.current30; });
    var segs2 = [segBtn('now', 'analogs', 'Against analogues', 'analogs'), segBtn('now', 'map', 'Pacific map', 'analogs'),
      segBtn('now', 'weekly', 'Weekly indices', 'analogs'), segBtn('now', 'weekly_a', 'Weekly vs strongest', 'analogs')];
    /* Полный экран у карты — как у обзора и цепочки данных. Владелец 06.09: «на мобильной
       тем более каша, надо предусмотреть полноэкранный режим: люди хотят увидеть на карте
       мира, где это находится». */
    if (k === 'map') segs2.push({ label: S.full ? 'exit full screen (Esc)' : '⛶ full screen', on: !!S.full,
                                  click: function () { S.full = !S.full; render(); } });
    var body = stageShell(above ? 'Warmer today than any of the four strongest events were at this time of year'
      : 'The event follows the strongest ones: rank ' + N.rank_same30 + ' among the analogues', segs2);
    if (k === 'map') {
      // выбор года сравнения — прямо на сцене
      var years = Object.keys(NW.analog_week || {}).sort();
      var cmp = S.sub.cmp || (years.indexOf('1997') >= 0 ? '1997' : years[years.length - 1]);
      var row = el('div', 'seg sub');
      years.forEach(function (y) {
        var b = el('button', cmp === y ? 'on' : '', 'vs ' + y + '–' + String(parseInt(y, 10) + 1).slice(2));
        b.type = 'button'; b.onclick = function () { S.sub.cmp = y; render(); };
        row.appendChild(b);
      });
      body.appendChild(row);
      /* ВЫБОР ЗОНЫ отдельным рядом (владелец 06.09). «Все зоны» — обзор, любая другая
         кнопка гасит соседей и показывает у выбранной сравнение с годом-аналогом. */
      var zrow = el('div', 'seg sub');
      var ZN = [['all', 'All zones'], ['nino12', 'Niño 1+2'], ['nino3', 'Niño 3'], ['nino34', 'Niño 3.4'], ['nino4', 'Niño 4']];
      var zcur = S.sub.zone || 'all';
      ZN.forEach(function (z) {
        var b = el('button', zcur === z[0] ? 'on' : '', z[1]);
        b.type = 'button'; b.onclick = function () { S.sub.zone = z[0]; render(); };
        zrow.appendChild(b);
      });
      body.appendChild(zrow);
      plot(body, function (w, h) { return pacific(NW, w, h); });
      // поле карты держит форму 2:1, иначе в полном экране вокруг неё пустота
      if (S.plotEl) S.plotEl.classList.add('map-fit');
    } else if (k === 'weekly') plot(body, function (w, h) { return chartNoaa(NW, w, h); });
    else if (k === 'weekly_a') {
      var NAMES2 = { n34a: 'Niño 3.4', n3a: 'Niño 3', n12a: 'Niño 1+2', n4a: 'Niño 4' };
      var row2 = el('div', 'seg sub');
      Object.keys(NAMES2).forEach(function (kk) {
        var b = el('button', (S.sub.wkey || 'n34a') === kk ? 'on' : '', NAMES2[kk]);
        b.type = 'button'; b.onclick = function () { S.sub.wkey = kk; render(); };
        row2.appendChild(b);
      });
      body.appendChild(row2);
      plot(body, function (w, h) { return chartNoaa(NW, w, h, 'analog'); });
    } else plot(body, function (w, h) { return chartAnalogs(N, w, h); });

    var pe = N.peak_estimate, ls = ONI.last_season, c4 = NW.chg4w || {}, c8 = NW.chg8w || {};
    var cap = el('div', 'cap');
    var aw = (NW.analog_week || {})[S.sub.cmp || '1997'] || {};
    var td = (D.iri || {}).todate, lf = (D.iri || {}).last_full_season;
    cap.innerHTML = k === 'map' ? 'The coastline is real (Natural Earth, public domain); the boxes are the four Niño regions. Colour is the anomaly of the week; the small number under it is the same week of the comparison event. Pick a zone above to bring it forward and see how it compares with the same week of the chosen event; point at a patch for the peak that event reached.'
      : (k === 'weekly' ? 'Over 4 weeks: Niño 3.4 ' + fnum(c4.n34a, 1) + ', Niño 1+2 ' + fnum(c4.n12a, 1) + '; over 8 weeks ' + fnum(c8.n34a, 1) + ' and ' + fnum(c8.n12a, 1) + '. Record of the weekly Niño 3.4: ' + fnum(NW.hist_max_n34.n34a, 1) + ' (' + esc(NW.hist_max_n34.date) + ').'
        : (k === 'weekly_a' ? 'The same weekly index against 1982, 1997, 2015 and 2023 on the same weeks of the year. The number in brackets is how much this event is above that one right now.'
          : '<strong>Peak estimate.</strong> ' + esc(pe.note) + ' Typical peak window ' + esc(pe.typical_peak_window) + '.' +
            (lf ? ' The last season lived through in full is ' + esc(lf.season) + ' at ' + fnum(lf.value) + ' °C' + (td ? '; the current ' + esc(td.season) + ' is ' + td.months_done + ' month of 3 measured, at ' + fnum(td.observed_todate) + ' °C.' : '.') : '')));
    body.appendChild(cap);

    var wk = pair(NW.latest.n34a, P && P.noaa ? P.noaa.n34a : null, 1, '°C');
    var dy = pair(N.current_day, P && P.daily ? P.daily.sst_nino34 : null, 2, '°C');
    var on = pair(ONI.current[ls], P && P.oni ? P.oni[ls] : null, 2, '');
    var kp = el('div', 'kpis');
    kp.innerHTML =
      '<div class="kpi"><div class="kn">' + term('weekly', 'NOAA weekly') + '</div><div class="kv">' + wk.big + '</div><div class="km">' + term('percentile', ord(Math.round(NW.n34_rank_pct)) + ' percentile') + ' of this season’s weeks</div><div class="kd"><span>4 w <span class="' + upDown(c4.n34a) + '">' + fnum(c4.n34a, 1) + '</span></span><span>8 w <span class="' + upDown(c8.n34a) + '">' + fnum(c8.n34a, 1) + '</span></span></div>' + kmeta('n34_weekly') + '</div>' +
      '<div class="kpi"><div class="kn">' + term('oisst', 'daily OISST') + '</div><div class="kv">' + dy.big + '</div><div class="km">30 days ' + fnum(N.current30) + ', ' + term('rank', 'rank ' + N.all_years_rank) + ' of all years</div><div class="kd"><span>slope ' + fnum(n34.slope14.now) + '</span><span>' + term('cusum', 'CUSUM') + ' ' + (n34.cusum.alarm ? 'alarm' : 'quiet') + '</span></div>' + kmeta('n34_daily') + '</div>' +
      '<div class="kpi"><div class="kn">' + term('oni', 'ONI official') + ' · ' + term('roni', 'RONI') + '</div><div class="kv">' + on.big + '<small>' + esc(ls) + '</small></div><div class="km">analogues: ' + [1982, 1997, 2015, 2023].map(function (y) { return y + ' ' + fnum((ONI.analogs[y] || {})[ls]); }).join(', ') + '</div>' +
      (ONI.roni && !ONI.roni.error && fin(ONI.roni.last) ? '<div class="chgline">' + term('roni', 'RONI') + ' ' + fnum(ONI.roni.last) + ' (' + esc(ONI.roni.last_season) + '); ONI − RONI = ' + fnum(ONI.roni.gap_last) + ' is the warm background</div>' : '') + kmeta('oni') + '</div>' +
      '<div class="kpi"><div class="kn">' + term('type', 'event type') + '</div><div class="kv" style="font-size:15px;line-height:1.25">' + esc(NW.type) + '</div><div class="km">' + zone('nino12') + ' ' + fnum(NW.latest.n12a, 1) + ' · ' + zone('nino4') + ' ' + fnum(NW.latest.n4a, 1) + ' · east−centre ' + fnum(NW.east_minus_central, 1) + '</div>' +
      (aw.n34a != null ? '<div class="chgline">' + (S.sub.cmp || '1997') + ' on this week: Niño 3.4 ' + fnum(aw.n34a, 1) + ', 1+2 ' + fnum(aw.n12a, 1) + '</div>' : '') + kmeta('n12_weekly') + '</div>';
    body.appendChild(kp);
  }

  function viewModels() {
    var D = S.D, IRI = D.iri && !D.iri.error ? D.iri : null, NW = D.noaa, P = S.P;
    if (!IRI) { var b0 = stageShell('The IRI plume did not load', []); b0.appendChild(el('div', 'note warn', esc((D.iri || {}).error || ''))); return; }
    var ao = IRI.against_observed || {}, rv = IRI.revisions || {}, models = IRI.models, classes = IRI.classes || {}, bd = IRI.breakdown || {};
    var names = Object.keys(models).filter(function (k) { return (models[k].section === 'dyn' || models[k].section === 'stat') && models[k].values; });
    var tally = IRI.class_tally || null;
    var k = sub('models', 'plume');
    var title = tally ? ('Of ' + names.length + ' models ' + tally.ok + ' keep up, ' + tally.lag + ' lag, ' + tally.broke + ' are broken')
      : (ao.below.length + ' of ' + ao.n + ' models are already below reality for ' + esc(ao.season));
    var body = stageShell(title, [segBtn('models', 'plume', 'Plume', 'plume'), segBtn('models', 'stack', 'Month by month', 'plume'),
      segBtn('models', 'board', 'Scoreboard', 'plume'), segBtn('models', 'breakdown', 'How they break', 'plume'),
      segBtn('models', 'revision', 'Revisions', 'plume')]);
    var i0 = IRI.seasons.indexOf(ao.season);

    if (k === 'plume') {
      plot(body, function (w, h) { return chartPlume(IRI, NW.latest.n34a, w, h); });
      var hist = (IRI.history || []).filter(function (h2) { return h2.combined; }).map(function (h2) { return h2.issued + ': ' + fnum(Math.max.apply(null, h2.combined.filter(fin))); });
      body.appendChild(el('div', 'cap', 'Each thin line is one model, coloured by its class: keeping up, lagging, broken. Thick is the combined mean, dashed the previous issue. The red dot is this week’s reality. Combined peak by issue: ' + hist.reverse().join(' → ') + '.' +
        ((IRI.position || []).filter(function (q) { return !q.complete; }).map(function (q) {
          return ' Where we stand on this scale is a band, not a dot: ' + q.season + ' has ' + q.months_done +
            ' month' + (q.months_done > 1 ? 's' : '') + ' of 3 measured (' + fnum(q.todate) + '), and the rest of the season is taken from the spread of the live models, ' +
            fnum(q.rest_from ? q.rest_from[0] : null) + ' … ' + fnum(q.rest_from ? q.rest_from[1] : null) + ' — hence ' + fnum(q.lo) + ' … ' + fnum(q.hi) + '.';
        }).join('')) +
        (IRI.last_full_season ? ' The green dashed line is the last season lived in full, ' + IRI.last_full_season.season + ' ' + fnum(IRI.last_full_season.value) + ': that one is a fact, not an estimate.' : '')));
    } else if (k === 'stack') {
      plot(body, function (w, h) { return chartStack(IRI.stack || [], NW.latest.n34a, w, h); });
      var st = IRI.stack || [];
      body.appendChild(el('div', 'cap', 'The same plume in three issues, newest on top, all on one scale. The thick ochre line is the mean over the models that KEPT UP: broken ones are left out entirely, laggards enter with a small weight. The published average of all models is the thin dashed grey line — the gap between the two is what the broken ones cost. The red mark on the first forecast season of each issue is where we stand in that season: its solid part is the share of the season already measured, the dashed part is what is left, and the pale band is where the season mean can still end up. In the June issue that mark is a full solid line — JJA is lived through; in the August one it is a third. Month by month the whole bundle climbs towards the water: the forecasts are dated by the issue, not by the data behind them.'));
    } else if (k === 'breakdown') {
      plot(body, function (w, h) { return chartBreakdown(bd, w, h); });
      var rows = bd.by_issue || [];
      var chronic = (bd.chronic || []).filter(function (c) { return c.of >= 3; }).slice(0, 10);
      var tb = el('div', 'tbl-inline');
      tb.innerHTML = '<table class="e"><thead><tr><th>model</th><th>class</th><th>below reality</th><th>mean error</th><th>worst</th><th>since</th></tr></thead><tbody>' +
        chronic.map(function (c) {
          return '<tr><td>' + modelSpan(c.model, c.model) + '</td><td><span class="cls ' + (c.cls || 'na') + '">' + ({ ok: T.okC, lag: T.lagC, broke: T.brokeC }[c.cls] || T.naC) + '</span></td>' +
            '<td class="num">' + c.issues_low + ' / ' + c.of + '</td><td class="num">' + fnum(c.mean_err) + '</td><td class="num' + ((c.worst_err || 0) <= -1 ? ' top' : '') + '">' + fnum(c.worst_err) + '</td><td>' + esc(c.since || '—') + '</td></tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(tb);
      body.appendChild(el('div', 'cap', 'For every stored issue we take its nearest season that now has an official ONI and count the models that came in below it. ' + (rows.length ? 'From ' + esc(rows[0].issue) + ' (' + rows[0].share + ' %) to ' + esc(rows[rows.length - 1].issue) + ' (' + rows[rows.length - 1].share + ' %). ' : '') + esc(bd.note || '')));
    } else if (k === 'revision') {
      /* ТРИ ВЫПУСКА, А НЕ ДВА. Владелец 04.09: «в revisions хотели не за один месяц изменения,
         а за три; направление изменений стрелочками на отрезках; внизу, где классы, нажимаем —
         те модели, которые относятся к классу, подсвечиваются».
         По каждой модели берём её ПИК в каждом из трёх последних выпусков и рисуем путь:
         два отрезка со стрелками на конце. Одна стрелка — случайность, две подряд в одну
         сторону — это уже поведение модели, и видно, кто гонится за событием, а кто уходит. */
      var stack3 = (IRI.stack || []).slice(0, 3).slice().reverse();   // от старого к новому
      plot(body, function (w, h) {
        var W = w, Hh = h, Lp = 46, R = 20, Tp = topPad(w), B = 76, pw = W - Lp - R, ph = Hh - Tp - B;
        if (stack3.length < 2) return svgOpen(W, Hh) + '<text x="20" y="40">fewer than two stored issues</text></svg>';
        var peaks = {};
        stack3.forEach(function (iss, si) {
          Object.keys(iss.models || {}).forEach(function (nm) {
            var m = iss.models[nm];
            if (m.section !== 'dyn' && m.section !== 'stat') return;
            var vv = (m.values || []).filter(fin);
            if (!vv.length) return;
            (peaks[nm] = peaks[nm] || [])[si] = Math.max.apply(null, vv);
          });
        });
        var rows2 = Object.keys(peaks).filter(function (nm) {
          return peaks[nm].filter(fin).length === stack3.length;
        }).sort(function (a, b) {
          return (peaks[b][stack3.length - 1] - peaks[b][0]) - (peaks[a][stack3.length - 1] - peaks[a][0]);
        });
        if (!rows2.length) return svgOpen(W, Hh) + '<text x="20" y="40">no model kept its peak across the three issues</text></svg>';
        var vals = []; rows2.forEach(function (nm) { peaks[nm].forEach(function (v) { if (fin(v)) vals.push(v); }); });
        var vmin = Math.min.apply(null, vals) - .2, vmax = Math.max.apply(null, vals) + .2;
        var X = function (i2) { return Lp + (rows2.length < 2 ? pw / 2 : i2 / (rows2.length - 1) * pw); };
        var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
        var s = svgOpen(W, Hh) + '<text class="tt" x="' + Lp + '" y="13">Where each model put the winter peak across the last ' +
          stack3.length + ' issues (' + stack3.map(function (x) { return esc(x.issued); }).join(' \u2192 ') + ')</text>';
        s += gridY(vmin, vmax, .5, Y, Lp, R, W, 1);
        rows2.forEach(function (nm, i2) {
          var c = (classes[nm] || {}).cls || 'none';
          var picked = S.pick && (S.pick === c || S.pick === nm), dim = S.pick && !picked;
          var col = picked ? 'var(--ochre)' : (c === 'broke' ? 'var(--lv5)' : (c === 'lag' ? 'var(--lv3)' : 'var(--nina)'));
          var op = dim ? .15 : .95;
          var x = X(i2), pk = peaks[nm];
          for (var k2 = 1; k2 < pk.length; k2++) {
            var y0 = Y(pk[k2 - 1]), y1 = Y(pk[k2]), up = pk[k2] >= pk[k2 - 1];
            s += '<line x1="' + x.toFixed(1) + '" y1="' + y0.toFixed(1) + '" x2="' + x.toFixed(1) + '" y2="' + y1.toFixed(1) +
              '" style="stroke:' + col + '" stroke-width="' + (k2 === pk.length - 1 ? 2 : 1.2) + '" opacity="' + op + '"/>';
            // стрелка направления на конце отрезка
            var d = up ? -4 : 4;
            s += '<path d="M' + (x - 3).toFixed(1) + ',' + (y1 - d).toFixed(1) + ' L' + x.toFixed(1) + ',' + y1.toFixed(1) +
              ' L' + (x + 3).toFixed(1) + ',' + (y1 - d).toFixed(1) + '" style="fill:none;stroke:' + col + '" stroke-width="1.2" opacity="' + op + '"/>';
          }
          s += '<circle cx="' + x.toFixed(1) + '" cy="' + Y(pk[0]).toFixed(1) + '" r="1.8" style="fill:var(--soft)" opacity="' + op + '"/>';
          s += '<text x="' + x.toFixed(1) + '" y="' + (Hh - B + 12) + '" transform="rotate(-90 ' + x.toFixed(1) + ' ' + (Hh - B + 12) +
            ')" text-anchor="end" font-size="9" opacity="' + op + '" style="fill:' + (picked ? 'var(--ochre)' : 'var(--soft)') + '">' + esc(nm) + '</text>';
        });
        var tl2 = IRI.class_tally || {};
        s += legend([['keeping up ' + (tl2.ok || 0), 'var(--nina)', 1.6, null, 'ok'],
          ['lagging ' + (tl2.lag || 0), 'var(--lv3)', 1.6, null, 'lag'],
          ['broken ' + (tl2.broke || 0), 'var(--lv5)', 1.6, null, 'broke']], W, Hh, legendW(W), Tp);
        return s + '</svg>';
      });
      body.appendChild(el('div', 'cap', 'One vertical path per model, named along the bottom: it starts at the peak that model put in the oldest of the three issues and each arrow shows where it moved it next. ' +
        'Two arrows the same way are not noise, they are behaviour: the model is chasing the event, or walking away from it. ' +
        (rv.n ? rv.n_up + ' of ' + rv.n + ' models raised their peak in the last issue alone, ' + rv.n_down + ' lowered it; the combined peak went ' + fnum(rv.combined_peak_prev) + ' \u2192 ' + fnum(rv.combined_peak_cur) + ' \u00b0C. ' : '') +
        'Click a class in the legend to light up only those models. This is about the coming winter, not about what is broken today: for that see \u201cHow they break\u201d.'));
    } else {
      var rvMap = {}; (rv.rows || []).forEach(function (r) { rvMap[r.model] = r; });
      var list = names.map(function (nm) {
        var m = models[nm], v = i0 >= 0 ? m.values[i0] : null, pk = Math.max.apply(null, m.values.filter(fin)), r = rvMap[nm] || {}, c = classes[nm];
        var was = P && P.model_season ? P.model_season[nm] : null;
        return { name: nm, sec: m.section, v: v, was: was, gap: fin(v) ? v - ao.observed_weekly : null, peak: pk, dpk: r.d_peak, cls: c };
      }).sort(function (a, b) { return (a.gap == null ? 9 : a.gap) - (b.gap == null ? 9 : b.gap); });
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap.innerHTML = '<table class="e"><thead><tr><th>model</th><th>type</th>' + (tally ? '<th>class · since</th>' : '') + '<th>' + esc(ao.season) + '</th>' +
        (S.delta ? '<th>since last update</th>' : '<th>vs reality</th>') + '<th></th><th>peak</th><th>shift</th></tr></thead><tbody>' +
        list.map(function (r) {
          var cc = r.cls && r.cls.cls ? '<span class="cls ' + r.cls.cls + '">' + ({ ok: T.okC, lag: T.lagC, broke: T.brokeC }[r.cls.cls] || T.naC) + '</span>' + (r.cls.since ? ' <span class="src">' + esc(r.cls.since) + '</span>' : '') : '<span class="cls na">' + T.naC + '</span>';
          var mid = S.delta ? '<td class="num">' + (fin(r.was) ? chg(r.v, r.was) : '—') + '</td>' : '<td class="num' + (r.gap != null && r.gap < 0 ? ' top' : '') + '">' + fnum(r.gap) + '</td>';
          return '<tr data-model="' + esc(r.name) + '"' + (S.model === r.name ? ' class="on"' : '') + '><td>' + modelSpan(r.name, r.name) + '</td><td>' + (r.sec === 'dyn' ? 'dyn.' : 'stat.') + '</td>' + (tally ? '<td>' + cc + '</td>' : '') +
            '<td class="num">' + fnum(r.v) + '</td>' + mid + '<td>' + miniBar(r.v, ao.observed_weekly) + '</td><td class="num">' + fnum(r.peak) + '</td><td class="num' + ((r.dpk || 0) > .3 ? ' top' : '') + '">' + fnum(r.dpk) + '</td></tr>';
        }).join('') + '</tbody></table>';
      wrap.addEventListener('click', function (e) {
        var tr = e.target.closest && e.target.closest('tr[data-model]');
        if (!tr) return;
        S.model = S.model === tr.getAttribute('data-model') ? null : tr.getAttribute('data-model');
        S.sub.models = 'plume'; render();
      });
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Click a row to light that model in the plume. The forecast for ' + esc(ao.season) + ' is a three-month mean while reality is a weekly point, so the comparison is honest only as “the model is below a level already reached”.'));
    }
    var tl = el('div', 'tally');
    tl.innerHTML = '<span><i style="background:var(--nino)"></i>below reality ' + ao.below.length + jchip('models_below_n') + '</span>' +
      '<span><i style="background:var(--ok)"></i>above ' + ao.above.length + jchip('models_above') + '</span>' +
      (tally ? '<span><i style="background:var(--ok)"></i>' + T.okC + ' ' + tally.ok + jchip('models_ok') + '</span><span><i style="background:var(--lv3)"></i>' + T.lagC + ' ' + tally.lag + jchip('models_lag') + '</span><span><i style="background:var(--lv5)"></i>' + T.brokeC + ' ' + tally.broke + jchip('models_broke') + '</span>' : '') +
      '<span>' + src({ name: 'Mean over the live models', def: 'The weighted mean over the models that kept up with reality: broken ones are out entirely, chronic laggards enter with weight 0.4, unverified ones with 0.6. The published plume average counts all ' + ((IRI.live || {}).n_all || '—') + ' equally and therefore sits lower — that is the difference between “the models say” and “the models that were right say”.', src: 'IRI plume, our verification', date: IRI.issued }, 'live RMS ' + fnum(liveNow(IRI, 'rms')) + ' \u00b7 their mean ' + fnum(liveNow(IRI)) + ' \u00b7 published ' + fnum(ao.mean)) + jchip('live_mean') + '</span>';
    body.appendChild(tl);
  }

  /* ══ ВОЗДУХ, ТОПЛИВО И ЭТАЖИ ═══════════════════════════════════════════════════
     До 4 сентября панель мерила только океан, и это была её главная слепота: Эль-Ниньо —
     сцепка воды и воздуха. Здесь три сцены. «Coupling» отвечает, отвечает ли атмосфера
     океану (давление, конвекция, пассаты). «Fuel» — тёплый объём воды под экватором:
     единственный измеряемый признак того, есть ли событию чем расти, и он опережает
     поверхность. «Layers» — как тепло поднимается по этажам атмосферы, с задержкой,
     посчитанной по нашим же рядам, а не взятой из учебника. */
  function chartAir(parts, W, H) {
    var keep = parts.filter(function (p) { return p.series && p.series.values.length > 3; });
    if (!keep.length) return svgOpen(W, H) + '<text x="20" y="40">no atmospheric series</text></svg>';
    var n = Math.max.apply(null, keep.map(function (p) { return p.series.values.length; }));
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var all = []; keep.forEach(function (p) { all = all.concat(p.series.values.filter(fin)); });
    var vmin = Math.min.apply(null, all) - .3, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">The atmosphere over the Pacific, last ' + n + ' months (standard deviations)</text>';
    s += gridY(vmin, vmax, 1, Y, Lp, R + 8, W, 1);
    // порог, по которому мы считаем признак сработавшим
    s += '<line x1="' + Lp + '" y1="' + Y(-0.5).toFixed(1) + '" x2="' + (W - R - 8) + '" y2="' + Y(-0.5).toFixed(1) + '" style="stroke:var(--nino)" stroke-width="1" stroke-dasharray="2 3" opacity=".7"/>' +
      (S._tight ? '' : '<text x="' + (Lp + 4) + '" y="' + (Y(-0.5) - 4).toFixed(0) + '" style="fill:var(--nino)">−0.5 σ: we call the sign in place below this</text>');
    var months = keep[0].series.months;
    months.forEach(function (m, i) { if (m.slice(5) === '01') s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + esc(m.slice(0, 4)) + '</text>'; });
    keep.forEach(function (p, pi) {
      var off = n - p.series.values.length;
      s += segs(p.series.values.map(function (v, i) { return [X(off + i), fin(v) ? Y(v) : NaN]; }),
        pi === 0 ? 'var(--text)' : (pi === 1 ? 'var(--nino)' : 'var(--nina)'), pi < 3 ? 2 : 1.2, pi < 3 ? 1 : .7, dashOf(pi));
    });
    s += legend(keep.map(function (p, pi) {
      return [p.title + ' ' + fnum(p.value), pi === 0 ? 'var(--text)' : (pi === 1 ? 'var(--nino)' : 'var(--nina)'), pi < 3 ? 2 : 1.2, dashOf(pi)];
    }), W, H, R, Tp);
    return s + '</svg>';
  }

  /* Топливо и поверхность на одной картинке: объём сдвинут вперёд на измеренное опережение,
     и видно, что поверхность идёт по следу объёма, а не наоборот. */
  function chartFuel(F, NW, W, H) {
    var ser = F.series, n = ser.values.length;
    var Lp = 52, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var vals = ser.values.filter(fin).map(function (v) { return v / 1e14; });
    var vmin = Math.min.apply(null, vals) - .3, vmax = Math.max.apply(null, vals) + .3;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var lag = (F.lead || {}).lag || 0;
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">Warm water volume under the equator, 10¹⁴ m³ — the fuel of the event</text>';
    s += gridY(vmin, vmax, 1, Y, Lp, R + 8, W, 1);
    ser.months.forEach(function (m, i) { if (m.slice(5) === '01') s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + esc(m.slice(0, 4)) + '</text>'; });
    s += '<line x1="' + Lp + '" y1="' + Y(0).toFixed(1) + '" x2="' + (W - R - 8) + '" y2="' + Y(0).toFixed(1) + '" style="stroke:var(--grid)" stroke-width="1"/>';
    // поверхностный индекс на вторую шкалу, сдвинутый на опережение
    var mon = (NW || {}).monthly || {}, sk = Object.keys(mon).sort();
    if (sk.length > 6) {
      var svals = sk.map(function (k) { return mon[k]; }).filter(fin);
      var smin = Math.min.apply(null, svals), smax = Math.max.apply(null, svals);
      var Y2 = function (v) { return Tp + (smax - v) / Math.max(.5, smax - smin) * ph; };
      var pts = [];
      ser.months.forEach(function (m, i) {
        var y = +m.slice(0, 4), mm = +m.slice(5) + lag, yy = y + Math.floor((mm - 1) / 12);
        var key = yy + '-' + String(((mm - 1) % 12) + 1).padStart(2, '0');
        pts.push([X(i), fin(mon[key]) ? Y2(mon[key]) : NaN]);
      });
      s += segs(pts, 'var(--nino)', 1.8, pickOp('n34', .95), '5 3');
    }
    s += segs(ser.months.map(function (m, i) { return [X(i), fin(ser.values[i]) ? Y(ser.values[i] / 1e14) : NaN]; }), 'var(--text)', 2.6, pickOp('wwv'));
    var li = n - 1;
    s += nowDot(X(li), Y(ser.values[li] / 1e14), 'var(--text)', 4);
    s += legend([['warm water volume ' + fnum(ser.values[li] / 1e14) + '·10¹⁴', 'var(--text)', 2.6, '', 'wwv'],
      ['Niño 3.4, −' + lag + ' months', 'var(--nino)', 1.8, '5 3', 'n34']], W, H, R, Tp);
    return s + '</svg>';
  }

  /* Четыре этажа: у каждого своя панель, общая шкала времени, подпись задержки. */
  /* СЛОИ: ПОДПИСИ СПРАВА, ГРАФИК СЛЕВА. Владелец 04.09: «на layers подписи сливаются и
     наезжают на графики; просто справа от них сделать легенду, и всё». Раньше и заголовок
     этажа, и значение, и три планки прошлых событий рисовались поверх самой линии — на
     четырёх узких панелях это каша. Теперь поле графика заканчивается там, где начинается
     колонка текста: этаж, сегодняшнее значение, задержка и уровни прошлых событий с их
     штрихами. Ось времени общая, под нижней панелью. */
  function chartLayers(items, W, H) {
    if (!items.length) return svgOpen(W, H) + '<text x="20" y="40">no satellite layers</text></svg>';
    // Правая колонка подписей в плитке пуста — она уехала в метку легенды: отдаём место графику.
    var RC = S._tight ? 6 : Math.max(120, Math.min(210, Math.round(W * .3)));
    var B0 = 18, gap = 8, hh = (H - B0 - gap * (items.length - 1)) / items.length;
    var all = []; items.forEach(function (x) { all = all.concat(x.series.values.filter(fin)); });
    items.forEach(function (x) {
      Object.keys(x.after_events || {}).forEach(function (y) { if (fin(x.after_events[y])) all.push(x.after_events[y]); });
    });
    var vmin = Math.min.apply(null, all) - .1, vmax = Math.max.apply(null, all) + .1;
    var LEGROWS = [];
    var s = svgOpen(W, H);
    items.forEach(function (x, xi) {
      var top = xi * (hh + gap), Lp = 46, Tp = top + 4, B = 4;
      var pw = W - Lp - RC - 10, ph = hh - 8, n = x.series.values.length;
      var X = function (i) { return Lp + i / Math.max(1, n - 1) * pw; };
      var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
      s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph.toFixed(1) + '" rx="5" style="fill:var(--ink)" opacity=".03"/>';
      if (vmin < 0 && vmax > 0) s += '<line x1="' + Lp + '" y1="' + Y(0).toFixed(1) + '" x2="' + (Lp + pw) + '" y2="' + Y(0).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".6"/>';
      // шкала градусов: две подписи, верх и низ поля — чтобы читались значения, а не только форма
      [vmax - .1, vmin + .1].forEach(function (g) {
        s += '<text x="' + (Lp - 5) + '" y="' + (Y(g) + 3).toFixed(1) + '" text-anchor="end" font-size="9">' + fnum(g, 1) + '</text>';
      });
      // планки прошлых событий — линиями по полю, но БЕЗ подписей: подписи справа
      var AE = x.after_events || {}, k = 0;
      ['1997', '2015', '2023'].forEach(function (y) {
        if (!fin(AE[y])) return;
        k++;
        s += '<line x1="' + Lp + '" y1="' + Y(AE[y]).toFixed(1) + '" x2="' + (Lp + pw) + '" y2="' + Y(AE[y]).toFixed(1) +
          '" style="stroke:var(--a' + y + ')" stroke-width="1" stroke-dasharray="' + dashOf(k) + '" opacity=".8"/>';
      });
      s += segs(x.series.values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }),
        xi === 0 ? 'var(--nina)' : 'var(--nino)', 2, 1);
      var li = n - 1;
      while (li > 0 && !fin(x.series.values[li])) li--;
      if (fin(x.series.values[li])) s += '<circle cx="' + X(li).toFixed(1) + '" cy="' + Y(x.series.values[li]).toFixed(1) + '" r="3" style="fill:' + (xi === 0 ? 'var(--nina)' : 'var(--nino)') + '"/>';
      // колонка подписей
      var lx = Lp + pw + 10, ly = Tp + 10;
      if (S._tight) { LEGROWS.push([x.title + ': ' + fnum(x.tropics) + ' °C' + (x.lag == null ? '' : ', lags ' + x.lag + ' mo'), x.col || 'var(--text)', 'line']); return; }
      s += '<text x="' + lx + '" y="' + ly + '" class="tt" font-size="11">' + esc(x.title) + '</text>';
      s += '<text x="' + lx + '" y="' + (ly + 13) + '" font-size="10" style="fill:var(--text)">now ' + fnum(x.tropics) + ' \u00b0C</text>';
      s += '<text x="' + lx + '" y="' + (ly + 25) + '" font-size="9" style="fill:var(--soft)">' +
        (x.lag == null ? 'no measurable delay' : 'lags ' + x.lag + ' mo, r ' + x.r) + '</text>';
      var ry = ly + 38, kk = 0;
      ['1997', '2015', '2023'].forEach(function (y) {
        if (!fin(AE[y])) return;
        kk++;
        if (ry > top + hh - 2) return;
        s += '<line x1="' + lx + '" y1="' + (ry - 3) + '" x2="' + (lx + 16) + '" y2="' + (ry - 3) +
          '" style="stroke:var(--a' + y + ')" stroke-width="1" stroke-dasharray="' + dashOf(kk) + '"/>' +
          '<text x="' + (lx + 21) + '" y="' + ry + '" font-size="9" style="fill:var(--soft)">after ' + y + ': ' + fnum(AE[y]) + '</text>';
        ry += 12;
      });
      // общая ось времени под нижней панелью
      if (xi === items.length - 1) {
        x.series.months.forEach(function (m, i) {
          if (m.slice(5) !== '01' && m.slice(5) !== '07') return;
          s += '<line x1="' + X(i).toFixed(1) + '" y1="' + (Tp + ph) + '" x2="' + X(i).toFixed(1) + '" y2="' + (Tp + ph + 4) + '" style="stroke:var(--grid)"/>' +
            '<text x="' + X(i).toFixed(0) + '" y="' + (Tp + ph + 14) + '" text-anchor="middle" font-size="9">' +
            (m.slice(5) === '01' ? esc(m.slice(0, 4)) : 'Jul') + '</text>';
        });
      }
    });
    if (S._tight && LEGROWS.length) scaleLegend(LEGROWS);
    return s + '</svg>';
  }

  function viewAir() {
    var D = S.D, A = D.air;
    if (!A || A.error) {
      var b0 = stageShell('The air block did not load', []);
      b0.appendChild(el('div', 'note warn', esc((A || {}).error || 'no data')));
      return;
    }
    var k = sub('air', 'coupling');
    var C = A.coupling, F = A.fuel, L = A.layers;
    var head = k === 'fuel' && F
      ? 'The fuel is at ' + F.share_of_record + ' % of the record of the whole series'
      : (k === 'layers' ? 'The event climbs the floors of the atmosphere with a measured delay'
        : (C ? C.verdict[0].toUpperCase() + C.verdict.slice(1) + ': ' + C.score + ' of ' + C.of + ' signs in place' : 'Atmosphere'));
    var WD = (D.wind || {}).era5, MJ = D.mjo, BG = D.background || {};
    if (k === 'wind' && WD && !WD.error) head = WD.active ? 'A westerly wind burst is under way' : ((WD.events || []).length + ' westerly bursts in the last 120 days' + (WD.days_since_last != null ? ', the latest ' + WD.days_since_last + ' days ago' : ''));
    if (k === 'mjo' && MJ && !MJ.error) head = 'MJO phase ' + MJ.last.phase + ', amplitude ' + MJ.last.amp + (MJ.burst_window ? ': the window for a wind burst is open' : ': ' + (MJ.active ? 'organised, but away from the western Pacific' : 'no organised pulse'));
    if (k === 'indices') head = 'Three independent indices next to our three-sign coupling';
    var body = stageShell(head, [segBtn('air', 'coupling', 'Coupling', 'coupling'),
      segBtn('air', 'fuel', 'Fuel', 'coupling'), segBtn('air', 'layers', 'Layers', 'coupling'),
      segBtn('air', 'wind', 'Wind, daily', 'coupling'), segBtn('air', 'mjo', 'MJO', 'coupling'), segBtn('air', 'indices', 'MEI · IOD · RONI', 'coupling')]);

    if (k === 'wind') {
      if (!WD || WD.error) { body.appendChild(el('div', 'note warn', 'The daily wind did not load: ' + esc((WD || {}).error || 'no data'))); return; }
      plot(body, function (w, h) { return chartWind(WD, w, h); });
      body.appendChild(el('div', 'cap', esc(WD.note) + ' ' + esc(WD.clim) + '.'));
      var TW = (D.wind || {}).tao || {};
      var kw = el('div', 'kpis');
      kw.innerHTML = '<div class="kpi"><div class="kn">' + term('wwb', 'last week') + '</div><div class="kv">' + fnum(WD.mean7, 1) + '<small>m/s</small></div><div class="km">westerly anomaly over 130°E–180°; burst threshold ' + fnum(WD.threshold, 1) + ' (2σ)</div>' + kmeta('wind_week') + '</div>' +
        '<div class="kpi"><div class="kn">bursts, 120 days</div><div class="kv">' + (WD.events || []).length + '<small>' + (WD.active ? 'one under way' : (WD.days_since_last != null ? 'last ended ' + WD.days_since_last + ' d ago' : 'none')) + '</small></div><div class="km">' + (WD.events || []).map(function (x) { return x.start.slice(5) + '→' + x.end.slice(5) + ' (' + x.days + ' d, peak ' + fnum(x.peak, 1) + ')'; }).join('; ') + '</div>' + kmeta(null, 'ERA5 via Open-Meteo', WD.last_date) + '</div>' +
        Object.keys(TW).map(function (nm) { var t = TW[nm]; return t.error ? '' : '<div class="kpi"><div class="kn">' + term('tao', 'mooring') + ' ' + esc(nm) + '</div><div class="kv">' + fnum(t.mean7, 1) + '<small>m/s</small></div><div class="km">measured surface wind, 7-day anomaly against the mooring\'s own record</div>' + kmeta(null, 'TAO/TRITON via ERDDAP', t.last_date) + '</div>'; }).join('');
      body.appendChild(kw);
      return;
    }
    if (k === 'mjo') {
      if (!MJ || MJ.error) { body.appendChild(el('div', 'note warn', 'The MJO index did not load: ' + esc((MJ || {}).error || 'no data'))); return; }
      plot(body, function (w, h) { return chartMJO(MJ, w, h); });
      body.appendChild(el('div', 'cap', esc(MJ.note) + ' Source: ' + esc(MJ.src) + '.'));
      var km = el('div', 'kpis');
      km.innerHTML = '<div class="kpi"><div class="kn">' + term('mjo', 'phase today') + '</div><div class="kv">' + MJ.last.phase + '<small>of 8</small></div><div class="km">' + ({ 1: 'Western Hemisphere and Africa', 2: 'Indian Ocean', 3: 'Indian Ocean', 4: 'Maritime Continent', 5: 'Maritime Continent', 6: 'western Pacific', 7: 'western Pacific', 8: 'Western Hemisphere' }[MJ.last.phase] || '') + '</div>' + kmeta('mjo_amp') + '</div>' +
        '<div class="kpi"><div class="kn">amplitude</div><div class="kv">' + fnum(MJ.last.amp, 1, false) + '</div><div class="km">' + (MJ.active ? 'organised pulse (≥ 1)' : 'below 1: no organised pulse') + '</div>' + kmeta(null, 'NOAA PSL OMI', MJ.last.d) + '</div>' +
        '<div class="kpi"><div class="kn">burst window</div><div class="kv" style="font-size:17px">' + (MJ.burst_window ? 'open' : 'closed') + '</div><div class="km">' + MJ.days_in_6_8_of_15 + ' of the last 15 days in phases 6–8 with amplitude ≥ 1</div>' + kmeta(null, 'our rule', MJ.last.d) + '</div>';
      body.appendChild(km);
      return;
    }
    if (k === 'indices') {
      var which = S.sub.idx || 'mei';
      var rowI = el('div', 'seg sub');
      [['mei', 'MEI v2'], ['dmi', 'IOD (DMI)']].forEach(function (o) {
        var b = el('button', which === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.idx = o[0]; render(); }; rowI.appendChild(b);
      });
      body.appendChild(rowI);
      var blk = BG[which];
      if (blk) plot(body, function (w, h) { return chartMetric({ name: blk.title, unit: blk.unit, step: 'month', dates: blk.months, values: blk.values, levels: blk.levels || {} }, w, h, blk.title + ' — dashes: the same month of the strongest past events'); });
      else body.appendChild(el('div', 'note warn', 'This index did not load.'));
      body.appendChild(el('div', 'cap', esc((blk || {}).note || '')));
      var RN = (D.oni || {}).roni || {};
      var ki = el('div', 'kpis');
      ki.innerHTML = (BG.mei ? '<div class="kpi"><div class="kn">' + term('mei', 'MEI v2') + '</div><div class="kv">' + fnum(BG.mei.last) + '<small>σ</small></div><div class="km">' + esc(BG.mei.date) + '; same month: ' + Object.keys(BG.mei.levels || {}).map(function (y) { return y + ' ' + fnum(BG.mei.levels[y]); }).join(', ') + '</div>' + kmeta(null, 'NOAA PSL', BG.mei.date) + '</div>' : '') +
        (BG.dmi ? '<div class="kpi"><div class="kn">' + term('iod', 'Indian Ocean Dipole') + '</div><div class="kv">' + fnum(BG.dmi.last) + '<small>°C · ' + esc(BG.dmi.phase) + '</small></div><div class="km">' + esc(BG.dmi.date) + '; same month: ' + Object.keys(BG.dmi.levels || {}).map(function (y) { return y + ' ' + fnum(BG.dmi.levels[y]); }).join(', ') + '</div>' + kmeta('dmi') + '</div>' : '') +
        (RN && fin(RN.last) ? '<div class="kpi"><div class="kn">' + term('roni', 'RONI') + '</div><div class="kv">' + fnum(RN.last) + '<small>' + esc(RN.last_season) + '</small></div><div class="km">ONI − RONI = ' + fnum(RN.gap_last) + '; analogues on ' + esc(RN.last_season) + ': ' + Object.keys(RN.analogs_same_season || {}).map(function (y) { return y + ' ' + fnum(RN.analogs_same_season[y]); }).join(', ') + '</div>' + kmeta('roni') + '</div>' : '');
      body.appendChild(ki);
      return;
    }
    if (k === 'fuel' && F) {
      plot(body, function (w, h) { return chartFuel(F, D.noaa, w, h); });
      body.appendChild(el('div', 'cap', esc(F.note) + ' The lead of ' + ((F.lead || {}).lag) + ' months and the correlation ' + ((F.lead || {}).r) + ' are computed on our own series, by trying every shift from zero to twelve months.'));
      var kp = el('div', 'kpis');
      kp.innerHTML = '<div class="kpi"><div class="kn">' + term('wwv', 'warm water volume') + '</div><div class="kv">' + fnum(F.value / 1e14) + '<small>·10¹⁴ m³</small></div><div class="km">' + F.share_of_record + ' % of the highest value since 1980</div>' + kmeta('wwv') + '</div>' +
        '<div class="kpi"><div class="kn">peak of the charge</div><div class="kv" style="font-size:17px">' + esc(F.peak_date) + '</div><div class="km">' + (F.months_since_peak ? F.months_since_peak + ' months ago; ' : 'this month; ') + (F.discharging ? 'the fuel is being spent' : 'not spent yet') + '</div>' + kmeta('wwv_share') + '</div>' +
        '<div class="kpi"><div class="kn">lead over the surface</div><div class="kv" style="font-size:17px">' + ((F.lead || {}).lag) + '<small>months</small></div><div class="km">correlation ' + ((F.lead || {}).r) + ', measured on our data</div>' + kmeta(null, 'NOAA PMEL / TAO', F.date) + '</div>' +
        (F.t300 ? '<div class="kpi"><div class="kn">' + term('t300', 'upper 300 m') + '</div><div class="kv">' + fnum(F.t300.value) + '<small>°C</small></div><div class="km">the same heat as a temperature, not a volume</div>' + kmeta(null, 'NOAA PMEL / TAO', F.t300.date) + '</div>' : '');
      body.appendChild(kp);
    } else if (k === 'layers' && L) {
      plot(body, function (w, h) { return chartLayers(L.items, w, h); });
      body.appendChild(el('div', 'cap', esc(L.note)));
    } else if (C) {
      plot(body, function (w, h) { return chartAir(C.parts, w, h); });
      body.appendChild(el('div', 'cap', esc(C.note)));
      var kp2 = el('div', 'kpis');
      kp2.innerHTML = C.parts.slice(0, 4).map(function (p) {
        return '<div class="kpi"><div class="kn">' + esc(p.title) + '</div><div class="kv">' + fnum(p.value) + '<small>σ</small></div>' +
          '<div class="km">' + (p.on ? 'in place' : 'not in place') + '; three-month mean ' + fnum(p.mean3) + '</div>' + kmeta(p.key) + '</div>';
      }).join('');
      body.appendChild(kp2);
    }
  }

  function viewTrend() {
    var D = S.D, W = D.watch, P = S.P;
    var k = sub('trend', 'sst_nino34');
    var opts = [['sst_nino34', 'Niño 3.4'], ['sst_world', 'Ocean'], ['t2_world', 'Land+ocean'], ['index', 'Our index'], ['months', '13 months'], ['background', 'Background']];
    var body = stageShell('The world ocean has broken daily records for ' + W.sst_world.records.streak + ' days running, land+ocean for ' + W.t2_world.records.streak,
      opts.map(function (o) { return segBtn('trend', o[0], o[1], 'sst_nino34'); }));
    if (k === 'index') {
      plot(body, function (w, h) { return chartHistory(S.H, w, h); });
      /* ЯДРО ИНДЕКСА У ПРОШЛЫХ СОБЫТИЙ. Владелец 04.09: «риск-индекс посчитать для других
         событий, по годам хотя бы основных, какой он был». Полный индекс назад не считается —
         половина его правил опирается на то, чего в 1982-м у нас не было. Считаем ту часть,
         которая живёт на общих для всех лет рядах, и сравниваем ядро с ядром. */
      var CORE = D.risk_core;
      if (CORE && CORE.items && CORE.items.length > 1) {
        var mx = Math.max.apply(null, CORE.items.map(function (x) { return x.core; })) || 100;
        var cw = el('div', 'kpis');
        cw.innerHTML = CORE.items.map(function (x) {
          var now = x.year === 'now';
          return '<div class="kpi"><div class="kn">' + (now ? 'this event, today' : 'at the same date in ' + esc(x.label)) + '</div>' +
            '<div class="kv" style="color:' + (now ? 'var(--nino)' : 'var(--text)') + '">' + x.core + '<small>core</small></div>' +
            '<div class="km">' + zone('nino34') + ' ' + fnum(x.n34, 1) + (x.peak != null ? ', that event peaked at ' + fnum(x.peak, 1) : '') + '</div>' +
            '<div class="kj"><div class="jr"><span class="jbar" style="--w:' + Math.round(100 * x.core / mx) + '%"></span></div>' +
            '<div class="jsrc"><span>' + esc((x.date || '')) + '</span>' + dateBadge(null, now ? 'our core index, on this event' : 'our core index, on the ' + x.label + ' event', x.date || '', 'core ' + (now ? 'today' : x.label)) + '</div></div></div>';
        }).join('');
        body.appendChild(cw);
        body.appendChild(el('div', 'cap', esc(CORE.note)));
        /* ВТОРАЯ ШКАЛА — ПО RONI (экспертиза 04.09): ядро живёт на аномалиях от фиксированной
           базы, и старые события выглядят слабее ещё и из-за потепления фона. RONI фон вычитает. */
        var RS = CORE.roni_scale;
        if (RS && fin(RS.now)) {
          var rw = el('div', 'kpis');
          rw.innerHTML = '<div class="kpi"><div class="kn">' + term('roni', 'RONI') + ', ' + esc(RS.season) + ' this year</div><div class="kv" style="color:var(--nino)">' + fnum(RS.now) + '<small>rank ' + (RS.rank || '—') + ' of ' + (RS.of || '—') + '</small></div><div class="km">ONI − RONI = ' + fnum(RS.gap_now) + ': the warm background subtracted</div>' + kmeta('roni') + '</div>' +
            Object.keys(RS.analogs || {}).map(function (y) { return '<div class="kpi"><div class="kn">' + esc(RS.season) + ' ' + y + '</div><div class="kv">' + fnum(RS.analogs[y]) + '</div><div class="km">event peak by RONI ' + fnum((RS.event_peaks || {})[y]) + ', by ONI ' + fnum((RS.oni_event_peaks || {})[y]) + '</div>' + dateBadge(null, 'NOAA CPC, RONI', esc(RS.season) + ' ' + y, 'RONI ' + y) + '</div>'; }).join('');
          body.appendChild(rw);
          body.appendChild(el('div', 'cap', esc(RS.note)));
        }
      }
      body.appendChild(el('div', 'cap', 'Every update leaves a snapshot; the lines are built from snapshots and deleting any one of them breaks nothing. ' + S.H.length + ' snapshots so far.'));
    } else if (k === 'background') {
      var BGb = D.background || {};
      if (BGb.error || (!BGb.ohc_700 && !BGb.ohc_2000)) { body.appendChild(el('div', 'note warn', 'The background block did not load: ' + esc(BGb.error || 'no series'))); return; }
      plot(body, function (w, h) { return chartOHC(BGb, w, h); });
      body.appendChild(el('div', 'cap', esc(BGb.note)));
      var E = BGb.eei || {}, o7 = BGb.ohc_700 || {}, o2 = BGb.ohc_2000 || {};
      var kb = el('div', 'kpis');
      kb.innerHTML = (o2.last != null ? '<div class="kpi"><div class="kn">' + term('ohc', 'heat, 0–2000 m') + '</div><div class="kv">' + fnum(o2.last, 1, false) + '<small>10²² J</small></div><div class="km">' + esc(o2.date) + (o2.record ? ', a record of the series since 1955' : '') + '; +' + fnum(o2.rise_10y, 1, false) + ' in ten years</div>' + kmeta('ohc_2000') + '</div>' : '') +
        (o7.last != null ? '<div class="kpi"><div class="kn">heat, 0–700 m</div><div class="kv">' + fnum(o7.last, 1, false) + '<small>10²² J</small></div><div class="km">' + esc(o7.date) + (o7.record ? ', a record' : '') + '; +' + fnum(o7.rise_10y, 1, false) + ' in ten years</div>' + kmeta(null, o7.src, o7.date) + '</div>' : '') +
        '<div class="kpi"><div class="kn">' + term('eei', 'energy imbalance') + ' · literature</div><div class="kv">' + esc(E.value) + '<small>' + esc(E.unit) + ' · ' + E.year + '</small></div><div class="km">' + esc(E.claim) + '</div>' + kmeta(null, E.src, String(E.year)) + '</div>';
      body.appendChild(kb);
      body.appendChild(el('div', 'note warn', '<strong>Quoted, not measured.</strong> ' + esc(E.note)));
    } else if (k === 'months') {
      var keys = [['sst_nino34', 'Niño 3.4'], ['sst_world', 'ocean'], ['t2_world', 'land+ocean']];
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap.innerHTML = '<table class="e"><thead><tr><th>month</th>' + keys.map(function (x) { return '<th colspan="2">' + x[1] + '</th>'; }).join('') + '</tr></thead><tbody>' +
        (W.sst_nino34.months13 || []).map(function (m) {
          return '<tr><td>' + MONTHS[m.m - 1] + ' ' + m.y + '</td>' + keys.map(function (x) {
            var mm = (W[x[0]].months13 || []).filter(function (q) { return q.y === m.y && q.m === m.m; })[0];
            return mm ? '<td class="num' + (mm.rank === 1 ? ' top' : '') + '">' + fnum(mm.anom) + '</td><td class="num src">' + mm.rank + '/' + mm.of + '</td>' : '<td>—</td><td>—</td>';
          }).join('') + '</tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Red marks a month that became the warmest of its calendar month in the whole record. The current month is incomplete.'));
    } else {
      var w0 = W[k];
      // ряд сцены → показатель журнала: один и тот же кирпич обслуживает три ряда
      var JK = { sst_nino34: 'n34_daily', sst_world: 'sst_world', t2_world: 't2_world' };
      plot(body, function (w, h) { return chartRecent(w0, w, h); });
      var lv = pair(w0.last_value, P && P.daily ? P.daily[k] : null, 2, '°C');
      var p50 = pair(w0.forecast14.p50, P && P.p50 ? P.p50[k] : null, 2, '°C');
      var kp = el('div', 'kpis');
      kp.innerHTML = '<div class="kpi"><div class="kn">last day</div><div class="kv">' + lv.big + '</div><div class="km">to ' + esc(w0.last_date) + '; 30 days ' + fnum(w0.level30.anom) + ', ' + term('rank', 'rank ' + w0.level30.rank_raw + ' of ' + w0.level30.of) + '</div>' + kmeta(JK[k]) + '</div>' +
        '<div class="kpi"><div class="kn">' + term('analog', 'forecast +14 days') + '</div><div class="kv">' + p50.big + '</div><div class="km">' + term('p10p50p90', 'p10 … p90') + ': ' + fnum(w0.forecast14.p10) + ' … ' + fnum(w0.forecast14.p90) + '</div>' + kmeta('fc14_' + k) + '</div>' +
        '<div class="kpi"><div class="kn">records and CUSUM</div><div class="kv" style="font-size:17px">' + w0.records.streak + '<small>days in a row</small></div><div class="km">' + w0.records.last30 + ' record days of 30; ' + term('cusum', 'CUSUM') + ' ' + (w0.cusum.alarm ? 'alarm' : 'quiet') + ', ' + term('trend', 'above trend') + ' ' + fnum(w0.level30.det) + '</div>' +
        kmeta('rec_' + k) + '</div>';
      body.appendChild(kp);
    }
  }

  function viewFood() {
    var D = S.D, RG = D.regions && !D.regions.error ? D.regions : null, FO = D.food && !D.food.error ? D.food : null, P = S.P;
    var k = sub('food', 'prices');
    /* ПО УМОЛЧАНИЮ СЧИТАЕМ ОТ STRONG. Владелец 04.09: «base это хорошо, но надо
       отталкиваться от strong — по умолчанию риск считать от strong, потом на графике можно
       переключить на base и на record». Логика простая и осторожная: планировать разумно от
       сильного сценария, а не от середины; переключатель рядом и показывает доли. */
    var scen = S.scenario || 'strong';
    var segs2 = [];
    if (FO) segs2.push(segBtn('food', 'prices', 'Food prices', 'prices'), segBtn('food', 'onset', 'Since onset', 'prices'));
    var CM = (D.air || {}).commodities;
    if (CM && CM.items && CM.items.length) segs2.push(segBtn('food', 'goods', 'By commodity', 'prices'));
    var body = stageShell(FO ? 'World food prices: index ' + fnum(FO.index, 1, false) + ' in ' + esc(FO.last_month) + ', ' + fnum(FO.yoy_pct, 1) + ' % on the year'
      : 'What it means for food', segs2);

    if (k === 'prices' && FO) {
      plot(body, function (w, h) { return chartFood(FO, w, h); });
      var G2 = FO.groups;
      body.appendChild(el('div', 'cap', 'Index ' + fnum(FO.index, 1, false) + ' in ' + esc(FO.last_month) + ': month ' + fnum(FO.mom, 1) + ', year ' + fnum(FO.yoy_pct, 1) + ' %. Year on year: ' + Object.keys(G2).map(function (g) { return g.toLowerCase() + ' ' + fnum(G2[g].yoy_pct, 1) + ' %'; }).join(', ') + '. The continuations of this line, scaled to the strength of the event, are on the “Since onset” tab.'));
    } else if (k === 'onset' && FO && FO.overlay && FO.overlay.current) {
      /* ПО ТОВАРАМ, НЕ ТОЛЬКО АГРЕГАТ. Владелец 04.09 (вечер): «since onset не понимаю: почему у
         нас риски растут, а цены падают». Падал индекс FAO — от кризисов, не от погоды; товары,
         по которым бьёт Эль-Ниньо, идут своими путями. Переключатель показывает каждый. */
      var OP = ((D.air || {}).onset_paths || {}), opi = OP.items || [], pickC = S.sub.onsetc || 'fao';
      var rowC = el('div', 'seg sub');
      [['fao', 'FAO index']].concat(opi.map(function (it) { return [it.key, it.name.replace(/,.*$/, '')]; })).forEach(function (o) {
        var b = el('button', pickC === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.onsetc = o[0]; render(); }; rowC.appendChild(b);
      });
      body.appendChild(rowC);
      var itC = opi.filter(function (x) { return x.key === pickC; })[0];
      if (pickC !== 'fao' && itC) {
        var ov2 = { onset: itC.current.onset, current: itC.current, analogs: itC.analogs || {} };
        plot(body, function (w, h) { return chartOverlay(ov2, w, h, { title: itC.name + ' as % of the onset month: this event against the same months after past onsets', noProject: true }); });
        body.appendChild(el('div', 'cap', '<strong>' + esc(itC.name) + ':</strong> ' + fnum(itC.now_pct, 1) + ' % since the onset month (' + esc(itC.current.onset) + ' = 100, ' + itC.months_in + ' months in). At the same point after past onsets: ' +
          Object.keys(itC.at6 || {}).map(function (y) { return y + ' ' + fnum(itC.at6[y], 1) + ' % at +6 months, ' + fnum(itC.at12[y], 1) + ' % at +12'; }).join('; ') + '. ' + esc(itC.why) + ' ' + esc(OP.note || '')));
      } else {
        plot(body, function (w, h) { return chartOverlay(FO.overlay, w, h); });
        body.appendChild(el('div', 'cap', '<strong>Why the risks on this page rise while this line falls.</strong> The index as a percentage of its value in the onset month (' + esc(FO.overlay.onset) + ' = 100, the first three-month season with ONI ≥ +0.5). ' +
          'The thin lines are what the aggregate index actually did after the past onsets: it went DOWN in all three — 1997-98 by about 12 %, 2015-16 by 14 %, 2023-24 by 1 % — because 1998 was the Asian crisis and 2015 was cheap oil, not the weather. ' +
          'El Niño hits the harvests of particular crops; the aggregate is harvests plus everything else. Switch to a commodity above to see the paths the event actually touches. ' +
          'The bold dotted lines carry today’s index along the past paths; the pale band scales them to the strength of the event (this one is heading for ' + fnum(peakExpected(S.D)) + ' °C against +2.37, +2.59 and +1.99 then) — a hint, not a forecast.'));
      }
    } else if (k === 'goods' && CM) {
      /* ТОВАРЫ ПОИМЁННО. Индекс FAO — одно число на всю еду; Эль-Ниньо бьёт по пальмовому
         маслу, рису и рыбной муке, и по каждому своим путём. Сортировка по движению с начала
         события, и тут же сказано, почему этот товар вообще в списке. */
      var wrapG = el('div'); wrapG.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrapG.innerHTML = '<table class="e"><thead><tr><th>commodity</th><th>price</th><th>month</th><th>year</th><th>since the event began</th><th>why it is here</th></tr></thead><tbody>' +
        CM.items.map(function (c) {
          var pay = { name: c.name + ' (' + c.unit + ')', def: c.why + ' Price ' + c.value + ' ' + c.unit + ' in ' + c.date + '.', src: 'World Bank Pink Sheet, monthly', date: c.date };
          return '<tr><td>' + src(pay, c.name) + '<div class="sub">' + esc(c.unit) + '</div></td>' +
            '<td class="num">' + fnum(c.value, c.value > 100 ? 0 : 2, false) + '</td>' +
            '<td class="num' + ((c.mom_pct || 0) > 0 ? ' top' : '') + '">' + fnum(c.mom_pct, 1) + ' %</td>' +
            '<td class="num">' + fnum(c.yoy_pct, 1) + ' %</td>' +
            '<td class="num' + ((c.since_onset_pct || 0) > 10 ? ' top' : '') + '">' + fnum(c.since_onset_pct, 1) + ' %</td>' +
            '<td class="act">' + esc(c.why) + '</td></tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(wrapG);
      body.appendChild(el('div', 'cap', esc(CM.note) + ' Prices are ' + esc(CM.as_of) + ', one month fresher than the FAO index.'));
    }
  }

  /* Таблица регионов — теперь на вкладке Regions (владелец 04.09, вечер: «вместо Kuwait · Gulf
     сделай такую вкладку, а внутри неё переключать регионы»). */
  function regionsTable(body, RG, scen, P) {
    var D = S.D;
    {
      var sup = RG.scenario_support || {};
      var lead = el('div', 'lead');
      lead.innerHTML = 'Scenario: ' + ['base', 'strong', 'record'].map(function (c) {
        var sc = sup[c] || {};
        var pay = { name: c + ' scenario', def: (sc.what ? sc.what[0].toUpperCase() + sc.what.slice(1) + '. ' : '') + (sc.threshold != null ? 'Threshold on the Niño 3.4 peak: ' + fnum(sc.threshold) + ' °C; ' + sc.models_at_or_above + ' of ' + sc.of + ' models reach it, that is ' + sc.share + ' %. ' : '') + (sup._note || ''), src: 'IRI plume, model peaks', date: (D.iri || {}).issued };
        return '<span class="scen' + (c === scen ? ' on' : '') + '" data-scen="' + c + '" data-src="' + esc(JSON.stringify(pay)) + '">' + c + (sc.share != null ? ' <b>' + sc.share + ' %</b>' : '') + '</span>';
      }).join(' ') + ' — the share is how many of the ' + ((sup.base || {}).of || '—') + ' models reach that peak, not a probability.'
        /* Лестница base→strong→record читается как рост тяжести, но пороги задаются данными,
           и сейчас порог «record» (рекорд недельного ряда) НИЖЕ медианы модельных пиков.
           Молчать об этом нечестно: читатель видит «record 69 %» рядом со «strong 15 %»
           и думает, что мы ошиблись. Говорим прямо — и только когда это действительно так. */
        + (fin((sup.record || {}).threshold) && fin((sup.base || {}).threshold) && sup.record.threshold < sup.base.threshold
          ? ' These are not a ladder: the record threshold (' + fnum(sup.record.threshold) + ') sits below the median model peak (' + fnum(sup.base.threshold) + '), so most models already put this event above the strongest week ever measured.' : '');
      lead.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('[data-scen]');
        if (t) { S.scenario = t.getAttribute('data-scen'); render(); }
      });
      body.appendChild(lead);
      /* ПЕРЕКЛЮЧАТЕЛЬ СЦЕНАРИЕВ ОТДЕЛЬНЫМ РЯДОМ. Владелец 04.09: «сделать переключение между
         сценариями». Раньше сценарий переключался словами внутри предложения и кликабельным
         заголовком колонки — это работало, но выглядело как текст, а не как орган управления.
         Теперь тот же выбор стоит рядом кнопок, как подвкладки, и видно, где мы находимся. */
      var srow = el('div', 'seg sub');
      ['base', 'strong', 'record'].forEach(function (c) {
        var sc2 = sup[c] || {};
        var b = el('button', c === scen ? 'on' : '', c + (sc2.share != null ? ' ' + sc2.share + ' %' : ''));
        b.type = 'button';
        b.title = (sc2.what || '') + (sc2.threshold != null ? '. Peak threshold ' + fnum(sc2.threshold) + ' °C' : '');
        b.onclick = function () { S.scenario = c; render(); };
        srow.appendChild(b);
      });
      body.appendChild(srow);
      var IMP = { dry: ['drought', 'var(--lv3)'], heat: ['heat', 'var(--lv4)'], wet: ['wet', 'var(--nina)'], flood: ['floods', 'var(--nina)'], none: ['no signal', 'var(--lv2)'] };
      var notes = RG.season_notes || {};
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      /* Порядок задаёт base, а не выбранный сценарий (владелец 04.09): при равенстве
         смотрим strong, потом record, потом уязвимость. Иначе список прыгал при каждом
         переключении колонки, и «первым» оказывался то Залив, то кто-то ещё. */
      var items = RG.items.slice().sort(function (a, b) {
        return b.levels.base - a.levels.base || b.levels.strong - a.levels.strong ||
          b.levels.record - a.levels.record || b.vulnerability.level - a.vulnerability.level;
      });
      wrap.innerHTML = '<table class="e regions"><thead><tr><th>region</th>' +
        RG.seasons.map(function (s2) { return '<th>' + src({ name: s2, def: notes[s2] || '', src: 'three-month season, the same convention as ONI', date: RG.as_of }, s2) + '</th>'; }).join('') +
        '<th class="vul">' + src({ name: 'Food vulnerability', def: 'Five bars: how exposed the region is through food — the share of imports in cereal consumption and the size of the population close to the margin. Point at a region name for the detail and the source.', src: 'FAO / World Bank', date: RG.as_of }, 'food') + '</th>' +
        '<th class="lvls">' + ['base', 'strong', 'record'].map(function (c) {
          var sc = (RG.scenario_support || {})[c] || {};
          return '<span class="sc' + (c === scen ? ' on' : '') + '" data-scen="' + c + '">' + src({ name: c + ' scenario', def: (sc.what || '') + (sc.threshold != null ? '. Peak threshold ' + fnum(sc.threshold) + ' °C, reached by ' + sc.models_at_or_above + ' of ' + sc.of + ' models (' + sc.share + ' %). ' : '. ') + ((RG.scenario_support || {})._note || ''), src: 'IRI plume', date: (D.iri || {}).issued }, c === 'strong' ? 'str' : (c === 'record' ? 'rec' : c)) + '</span>';
        }).join('') + '</th><th class="act">what to do</th></tr></thead><tbody>' +
        items.map(function (r) {
          var was = P && P.regions ? (P.regions[r.id] || {})[scen] : null;
          var cells = RG.seasons.map(function (s2) {
            var x = r.seasons[s2] || {}, im = IMP[x.impact] || IMP.none;
            var pay = { name: r.name + ' · ' + s2, def: x.note || 'No consistent signal for this season.', src: r.sources.join(' · '), date: RG.as_of };
            return '<td><span class="imp" data-src="' + esc(JSON.stringify(pay)) + '" style="--c:' + im[1] + '">' + im[0] + (x.impact && x.impact !== 'none' ? ' <small>' + esc(x.strength || '') + '</small>' : '') + '</span></td>';
          }).join('');
          var vb = '<span class="vbar">' + [1, 2, 3, 4, 5].map(function (i) { return '<i' + (i <= r.vulnerability.level ? ' class="on"' : '') + '></i>'; }).join('') + '</span>';
          var lv = '<td class="lvls">' + ['base', 'strong', 'record'].map(function (c) {
            var d2 = (c === scen && fin(was) && was !== r.levels[c]) ? '<sup>' + (r.levels[c] > was ? '+' : '−') + '</sup>' : '';
            var sc2 = (RG.scenario_support || {})[c] || {};
            var pay = { name: r.name + ' · ' + c + ' scenario', def: 'Level ' + r.levels[c] + ' of 5: how strong the teleconnection is here, multiplied by how exposed the region is through food. ' + (sc2.what ? sc2.what[0].toUpperCase() + sc2.what.slice(1) + '.' : ''), src: r.sources.join(' · '), date: RG.as_of };
            return '<span class="lvl' + (c === scen ? ' cur' : '') + '" data-scen="' + c + '" data-src="' + esc(JSON.stringify(pay)) + '" style="background:' + lvlColor(r.levels[c]) + '">' + r.levels[c] + '</span>' + d2;
          }).join('') + '</td>';
          return '<tr><td>' + src({ name: r.name, def: r.countries + '. Vulnerability ' + r.vulnerability.level + ' of 5: ' + r.vulnerability.note + (r.vulnerability.importers && r.vulnerability.importers.length ? ' Net importers: ' + r.vulnerability.importers.join(', ') + '.' : ''), src: r.sources.join(' · '), date: RG.as_of }, r.name) +
            '<div class="sub">' + esc(r.countries) + '</div></td>' + cells + '<td>' + vb + '</td>' + lv + '<td class="act">' + r.actions.map(function (a) { return '<div>' + esc(a) + '</div>'; }).join('') + linksHtml('region:' + r.id) + '</td></tr>';
        }).join('') + '</tbody></table>';
      wrap.addEventListener('click', function (e) {
        var th = e.target.closest && e.target.closest('[data-scen]');
        if (th) { S.scenario = th.getAttribute('data-scen'); render(); }
      });
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Impacts are typical for a strong eastern-type El Niño, from published NOAA CPC and IRI impact maps, FAO GIEWS alerts and the regional literature: “usually”, never “will”. Click a scenario to switch the highlighted column.'));
    }

    var FO = D.food && !D.food.error ? D.food : null;
    if (FO) {
      var kp = el('div', 'kpis'), G3 = FO.groups;
      var fi = pair(FO.index, P ? P.food_index : null, 1, '');
      var worst = Object.keys(G3).sort(function (a, b) { return (G3[b].yoy_pct || 0) - (G3[a].yoy_pct || 0); })[0];
      kp.innerHTML = '<div class="kpi"><div class="kn">' + term('fao', 'FAO food price index') + '</div><div class="kv">' + fi.big + '<small>' + esc(FO.last_month) + '</small></div><div class="km">month ' + fnum(FO.mom, 1) + ' · year ' + fnum(FO.yoy_pct, 1) + ' %</div>' + kmeta('food_index') + '</div>' +
        '<div class="kpi"><div class="kn">strongest rise, year on year</div><div class="kv" style="font-size:17px">' + esc(worst) + '<small>' + fnum(G3[worst].yoy_pct, 1) + ' %</small></div><div class="km">' + esc(worst) + ' index ' + fnum(G3[worst].last, 1, false) + '</div>' + kmeta('food_yoy') + '</div>' +
        '<div class="kpi"><div class="kn">scenario in force</div><div class="kv" style="font-size:17px">' + esc(RG ? RG.current_scenario : '—') + '</div><div class="km">chosen by the data: where reality sits against the model spread</div>' +
        kmeta('scenario') + '</div>';
      body.appendChild(kp);
    }
  }

  function viewHow() {
    var D = S.D, gl = S.G;
    var k = sub('how', 'glossary');
    var body = stageShell('Glossary, method, sources', [segBtn('how', 'glossary', 'Glossary', 'glossary'), segBtn('how', 'method', 'Method', 'glossary'), segBtn('how', 'sources', 'Sources', 'glossary'), segBtn('how', 'calendar', 'Release calendar', 'glossary'), segBtn('how', 'changed', 'What changed', 'glossary')]);
    body.classList.add('scroll');
    if (k === 'calendar') {
      var CAL = ((D.background || {}).calendar) || {};
      var tc = el('table', 'e');
      tc.innerHTML = '<thead><tr><th>what</th><th>who</th><th>next</th><th>in</th><th>rule</th></tr></thead><tbody>' +
        (CAL.items || []).map(function (x) { return '<tr><td>' + esc(x.name) + '</td><td>' + esc(x.src) + '</td><td class="num">' + esc(x.next) + '</td><td class="num' + (x.in_days <= 2 ? ' top' : '') + '">' + (x.in_days === 0 ? 'today' : x.in_days + ' d') + '</td><td>' + esc(x.rule) + '</td></tr>'; }).join('') + '</tbody>';
      body.appendChild(tc);
      body.appendChild(el('div', 'cap', esc(CAL.note || '') + ' Today: ' + esc(CAL.today || '') + '.'));
      return;
    }
    if (k === 'glossary') {
      var g = el('div', 'gloss');
      Object.keys(gl).forEach(function (key) { var x = gl[key]; g.innerHTML += '<div class="gl-i"><b>' + esc(x.name) + '</b>' + esc(x.def) + '<div class="why">' + esc(x.why) + '</div><div class="s">' + esc(x.src) + '</div>' + linksHtml('term:' + key) + '</div>'; });
      body.appendChild(g);
    } else if (k === 'sources') {
      /* ЧЕТВЁРТАЯ КОЛОНКА — КОГДА ДАННЫЕ РЕАЛЬНО МЕНЯЛИСЬ. Владелец 04.09: «нам неважно,
         когда мы обновляли, нам важно, когда данные обновились». «Свежесть» отвечает лишь
         на вопрос «источник ответил»; здесь — дата последней СМЕНЫ значения из журнала,
         и она у ленты FAO может отстоять на месяц, а у недельной NOAA на неделю. */
      var SRCJ = { sst_nino34: 'n34_daily', sst_world: 'sst_world', t2_world: 't2_world',
        noaa_weekly: 'n34_weekly', oni: 'oni', fao_fpi: 'food_index',
        soi: 'soi', olr: 'olr', u850_west: 'u850_west', wwv: 'wwv',
        uah_tlt: 'tlt_tropics', uah_tls: 'tls_tropics', wb_pink: 'price_palm_oil' };
      var t = el('table', 'e');
      t.innerHTML = '<thead><tr><th>series</th><th>what it is</th><th>the source answered</th><th>the data last changed</th></tr></thead><tbody>' +
        Object.keys(D.sources).map(function (key) {
          var v = D.sources[key], jr = jrec(SRCJ[key]), e = jr ? (jr.entries || []) : [];
          var last = e[e.length - 1], prev = e[e.length - 2];
          var cell = last ? esc(last.d) + (prev ? ' <span class="' + jsign(last.v - prev.v) + '">' + jarrow(last.v - prev.v) + '</span>' : '') : '—';
          return '<tr><td>' + esc(key) + '</td><td>' + esc(v.label) + '</td><td' + (v.fresh ? '' : ' class="top"') + '>' + (v.fresh ? T.fresh : T.stale + ': ' + esc(v.error)) + '</td><td class="num">' + cell + '</td></tr>';
        }).join('') + '</tbody>';
      body.appendChild(t);
      body.appendChild(el('div', 'cap', 'climatereanalyzer.org (ERA5 2 m; OISST v2.1) · NOAA CPC weekly Niño indices and ONI · NOAA PSL ERSST v6 monthly Niño 3.4 · IRI/CCSR model plume · FAO Food Price Index. The raw data of every update is stored verbatim with its date.'));
    } else if (k === 'changed') {
      body.appendChild(el('div', 'lead', (D.diff || []).map(function (d) { return '· ' + esc(d); }).join('<br>') || 'First update: nothing to compare with yet.'));
      if (S.P) body.appendChild(el('div', 'cap', 'The previous update was at ' + esc(S.P.stamp) + ': risk index ' + S.P.risk_index + ', ' + S.P.n_risks + ' risks, ' + S.P.n_alerts + ' alerts. Switch the header button to “change since last update” to see every number as a delta.'));
    } else if (k === 'method') {
      /* ЧТО ЗНАЧИТ «ОБНОВИТЬ ДАШБОРД». Владелец 04.09 спросил прямо: что делается само, а
         что руками. Ответ должен лежать на панели, а не в голове у того, кто её ведёт. */
      var hyb = el('div', 'gloss');
      hyb.innerHTML = [
        ['Runs itself, every update', 'Eight daily and weekly feeds plus the FAO monthly index: fetch, anomalies against 1991–2020, CUSUM, analogue comparison, risk levels, regional impact, watchdog alerts, the value journal and a full snapshot of everything on disk.'],
        ['Runs itself, but I look', 'The IRI plume is read off a published figure. A change of layout breaks the parser, and it is built to fail loudly rather than to guess. Once a month, when the new issue appears around the 19th, I check the parsed numbers against the picture.'],
        ['Only on decision', 'The model summary and the links to the parsed papers cost money to recompute, so they are not run on every refresh.'],
        ['Only by hand', 'The reference tables: regions and their vulnerability, the glossary, the descriptions of the forecast centres. These are written, not measured.'],
        ['What “updated” means', 'The stamp in the header is when the panel was recomputed. It is not when the data changed: every brick carries its own date, and the history button behind it lists the changes of the number itself.']
      ].map(function (x) { return '<div class="gl-i"><b>' + esc(x[0]) + '</b>' + esc(x[1]) + '</div>'; }).join('');
      body.appendChild(hyb);
      var m2 = el('div', 'note');
      m2.innerHTML = '<strong>Method.</strong> Anomalies against the 1991–2020 base. CUSUM accumulates the excess over the mean of the last full year and fires when the sum passes a threshold — that is what tells a spike apart from a new level. Analogues are the four strongest events since 1982, aligned by day of year. Model classes come from our own verification of the stored issues against the official ONI.';
      body.appendChild(m2);
      /* ПАРАМЕТРЫ, А НЕ ФАКТЫ (экспертиза 04.09, п. 3.10): веса моделей и заимствованный
         разброс — наши допущения, и они должны быть названы допущениями на самой панели. */
      var LVw = ((D.iri || {}).live || {}).weights || {};
      var m3 = el('div', 'note warn');
      m3.innerHTML = '<strong>Parameters, not measurements.</strong> The live-model centre uses weights by class: keeping up ' + (LVw.ok != null ? LVw.ok : 1) + ', lagging ' + (LVw.lag != null ? LVw.lag : 0.4) + ', unverified ' + (LVw.none != null ? LVw.none : 0.6) + ', broken ' + (LVw.broke != null ? LVw.broke : 0) + ' — a heuristic, shown next to the plain mean everywhere it appears. The root-mean-square is an indicator of sensitivity to the strong forecasts, not a better estimate of the centre. For seasons the models do not publish (JJA, JAS) the spread of the unmeasured months is borrowed from the nearest forecast season: an assumption, labelled as such on the plume. Comparisons across decades are given twice — on the fixed 1991–2020 base and by RONI, which subtracts the warm background. A “broken” model is one below the official value in most verified issues; its last two errors are shown so that a model that is catching up can be seen to be.';
      body.appendChild(m3);
    } else {
      var m = el('div', 'note');
      m.innerHTML = '<strong>Method.</strong> Everything is computed on ' + term('anomaly', 'anomalies to 1991–2020') + ' taken from the source files themselves. “Rank” is the position of the same 30 calendar days among all years. “Above trend” is after subtracting the linear warming. Slope and noise are compared with the same windows of the same season, so a percentile means “unusual for this time of year”. The 14-day forecast is ' + term('analog', 'analogue-based') + '. ' + term('cusum', 'CUSUM') + ' accumulates the deviation from the level at the start of the window; threshold 5. The ' + term('riskindex', 'risk index') + ' is a saturating sum of levels: 100·(1 − exp(−Σ level^1.5/25)). Model classes come from the forecasts of stored IRI issues against the official ONI of the exact season each issue was forecasting.';
      body.appendChild(m);
      var c = el('div', 'note warn');
      c.innerHTML = '<strong>Caveats.</strong> The climatereanalyzer series are global means; the focus of the event is visible only through the NOAA Niño regions. Daily OISST lags. The ' + term('plume', 'IRI plume') + ' is extracted from a figure: a change of layout would break the parser, which must then fail loudly. The ' + term('summary', 'model summary') + ' is an interpretation, not a source. ' + term('teleconnection', 'Teleconnections') + ' are typical, not guaranteed, and for Europe and Russia they are weak enough that we say so on the row itself.';
      body.appendChild(c);
    }
  }

  function viewRisk() {
    var D = S.D, r = (D.risks || [])[S.risk];
    if (!r) { S.view = 'now'; return viewNow(); }
    var body = stageShell(esc(r.title), [{ label: '← back', on: false, click: function () { S.risk = null; S.view = 'now'; render(); } }]);
    if (r.metric) plot(body, function (w, h) { return chartMetric(r.metric, w, h, r.metric.name); });
    var was = S.P && S.P.risks ? S.P.risks[r.title] : null;
    body.appendChild(el('div', 'lead', '<b>Level ' + r.level + ' · ' + esc(r.horizon) + '.</b> ' + mark(r.plain || '') + (fin(was) && was !== r.level ? ' <i>Level was ' + was + ' at ' + esc(prevStamp()) + '.</i>' : '')));
    body.appendChild(el('div', 'note', '<strong>Evidence.</strong> ' + mark(r.evidence) + (r.metric ? '<br>' + dynWords(r.metric) : '')));
    body.appendChild(el('div', 'note warn', '<strong>Watch.</strong> ' + mark(r.watch)));
    // по имени риска; по номеру — только пока на проде лежит старый links.json
    var lk = linksHtml('risk:' + (r.id || ''), true) || linksHtml('risk:' + S.risk, true);
    if (lk) body.appendChild(el('div', 'links-box', lk));
  }


  // ---------------------------------------------------------------- Ocean (экспертиза 04.09)
  var CREW = { writer: 'DeepSeek V4 Pro', supervisor: 'Fable (Claude)' };
  var BOX_ORDER = [['nino34', 'Niño 3.4'], ['nino3', 'Niño 3'], ['nino12', 'Niño 1+2'], ['nino4', 'Niño 4'], ['gulf', 'Gulf'], ['world', 'World ocean']];

  /* Тепловая карта разреза: столбцы — долготы, строки — глубины; цвет — знак и величина
     аномалии на переменных темы (не «синий-красный» из палитры Matplotlib, а наши --nino и
     --nina с прозрачностью), пустые ячейки — сеточным цветом. Линия D20 поверх, если есть. */
  function chartSection(cfg, W, H) {
    var cols = cfg.cols, rows = cfg.rows, get = cfg.get, nC = cols.length, nR = rows.length;
    if (!nC || !nR) return svgOpen(W, H) + '<text x="20" y="40">no section</text></svg>';
    /* Колонка легенды справа нужна только на большом графике: в плитке легенда уехала в
       метку, и держать под неё 108 пикселей — значит показывать разрез в половину ширины
       (владелец 06.09: «график остался не на всю ширину, ты убрал легенду, но не расширил»). */
    var Lp = S._tight ? 40 : 44, Rp = S._tight ? 10 : 108, Tp = S._tight ? 16 : 26, B = 26;
    var pw = W - Lp - Rp, ph = H - Tp - B;
    var vmax = 0, i, j, v;
    for (i = 0; i < nC; i++) for (j = 0; j < nR; j++) { v = get(i, j); if (fin(v)) vmax = Math.max(vmax, Math.abs(v)); }
    vmax = Math.max(0.5, Math.ceil(vmax * 2) / 2);
    var depthMax = rows[nR - 1] + (rows[nR - 1] - rows[nR - 2]) / 2;
    var Y = function (d) { return Tp + d / depthMax * ph; };
    var cw = pw / nC;
    var s = svgOpen(W, H) + hatchDefs() + '<text class="tt" x="' + Lp + '" y="15">' + fitText(esc(cfg.title), W, 12) + '</text>';
    for (i = 0; i < nC; i++) {
      for (j = 0; j < nR; j++) {
        v = get(i, j);
        var y0 = j === 0 ? Tp : Y((rows[j - 1] + rows[j]) / 2), y1 = j === nR - 1 ? Tp + ph : Y((rows[j] + rows[j + 1]) / 2);
        var x0 = Lp + i * cw;
        var geo = 'x="' + x0.toFixed(1) + '" y="' + y0.toFixed(1) + '" width="' + (cw + .5).toFixed(1) + '" height="' + (y1 - y0 + .5).toFixed(1) + '"';
        if (!fin(v)) { s += '<rect ' + geo + ' style="fill:var(--grid)" opacity=".35"/>'; continue; }
        var op = Math.min(1, Math.abs(v) / vmax);
        s += '<rect ' + geo + ' style="fill:' + (v >= 0 ? 'var(--nino)' : 'var(--nina)') + '" opacity="' + (0.08 + 0.92 * op).toFixed(2) + '"/>';
        // холоднее нормы — ещё и штриховкой: знак читается без цвета
        if (v < -0.25) s += '<rect ' + geo + ' fill="url(#hneg)" opacity="' + (0.3 + 0.5 * op).toFixed(2) + '"/>';
      }
    }
    // D20 поверх — сплошная сейчас, пунктир норма
    if (cfg.d20) s += segs(cfg.d20.map(function (d, k) { return [Lp + (k + .5) * cw, fin(d) ? Y(d) : NaN]; }), 'var(--text)', 2);
    if (cfg.d20clim) s += segs(cfg.d20clim.map(function (d, k) { return [Lp + (k + .5) * cw, fin(d) ? Y(d) : NaN]; }), 'var(--text)', 1.2, .8, '5 3');
    // подписи глубин слева, долгот снизу
    (S._tight ? [0, 150, 300] : [0, 50, 100, 150, 200, 250, 300]).forEach(function (d) { if (d <= depthMax) s += '<text x="' + (Lp - 5) + '" y="' + (Y(d) + 3.5).toFixed(1) + '" text-anchor="end" font-size="9">' + d + (S._tight ? '' : ' m') + '</text>'; });
    /* В плитке обзора долготы стояли вплотную и сливались: там оставляем только края —
       первую и последнюю (владелец 06.09). Глубины слева тоже прореживаем. */
    if (S._tight) {
      [0, nC - 1].forEach(function (i2) {
        s += '<text x="' + (Lp + (i2 + .5) * cw).toFixed(1) + '" y="' + (H - 9) + '" text-anchor="' + (i2 ? 'end' : 'start') + '" font-size="9">' + esc(cols[i2]) + '</text>';
      });
    } else {
      var every = Math.max(1, Math.round(nC / Math.max(3, Math.floor(pw / 58))));
      for (i = 0; i < nC; i++) if (i % every === 0 || i === nC - 1) s += '<text x="' + (Lp + (i + .5) * cw).toFixed(1) + '" y="' + (H - 9) + '" text-anchor="middle" font-size="9">' + esc(cols[i]) + '</text>';
    }
    // легенда справа
    var lx = W - Rp + 10, ly = Tp + 4;
    var SCALE = [[vmax, 'var(--nino)', 1], [vmax / 2, 'var(--nino)', .5], [0, 'var(--grid)', .6], [-vmax / 2, 'var(--nina)', .5], [-vmax, 'var(--nina)', 1]];
    if (scaleLegend(SCALE.map(function (it) { return [fnum(it[0], 1) + ' °C', it[1], 'box', it[2]]; })
        .concat(cfg.d20 ? [['20 °C now', 'var(--text)', 'line']] : [])
        .concat(cfg.d20clim ? [['20 °C normal', 'var(--text)', 'line', 1]] : []))) return s + '</svg>';
    SCALE.forEach(function (it, k) {
      s += '<rect x="' + lx + '" y="' + (ly + k * 15) + '" width="14" height="11" style="fill:' + it[1] + '" opacity="' + it[2] + '"/>' +
        (it[0] < 0 ? '<rect x="' + lx + '" y="' + (ly + k * 15) + '" width="14" height="11" fill="url(#hneg)" opacity=".7"/>' : '') +
        '<text x="' + (lx + 19) + '" y="' + (ly + k * 15 + 9) + '" font-size="9">' + fnum(it[0], 1) + ' °C</text>';
    });
    if (cfg.d20) s += '<line x1="' + lx + '" y1="' + (ly + 84) + '" x2="' + (lx + 14) + '" y2="' + (ly + 84) + '" style="stroke:var(--text)" stroke-width="2"/><text x="' + (lx + 19) + '" y="' + (ly + 87) + '" font-size="9">20 °C now</text>';
    if (cfg.d20clim) s += '<line x1="' + lx + '" y1="' + (ly + 98) + '" x2="' + (lx + 14) + '" y2="' + (ly + 98) + '" style="stroke:var(--text)" stroke-dasharray="5 3"/><text x="' + (lx + 19) + '" y="' + (ly + 101) + '" font-size="9">20 °C normal</text>';
    if (cfg.legendNote) s += '<text x="' + lx + '" y="' + (ly + 116) + '" font-size="9" style="fill:var(--soft)">' + esc(cfg.legendNote) + '</text>';
    return s + '</svg>';
  }

  function chartWind(e, W, H) {
    var vals = e.anom, n = vals.length, dates = e.dates;
    var Lp = 46, R = 40, Tp = 26, B = 26, pw = W - Lp - R, ph = H - Tp - B;
    var vv = vals.filter(fin).concat([e.threshold || 0, -(e.threshold || 0)]);
    var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv);
    var pad = (vmax - vmin) * .12; vmin -= pad; vmax += pad * 2;
    var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + hatchDefs() + '<text class="tt" x="' + Lp + '" y="15">' + fitText('Westerly wind anomaly over 130°E–180°, daily — shaded: bursts; hatched: easterly', W, 12) + '</text>';
    (e.events || []).forEach(function (ev) {
      var i0 = dates.indexOf(ev.start), i1 = dates.indexOf(ev.end);
      if (i0 < 0 || i1 < 0) return;
      s += '<rect x="' + X(i0).toFixed(1) + '" y="' + Tp + '" width="' + Math.max(2, X(i1) - X(i0)).toFixed(1) + '" height="' + ph + '" style="fill:var(--nino)" opacity=".12"/>';
    });
    s += gridY(vmin, vmax, 2, Y, Lp, R, W, 0);
    if (fin(e.threshold)) s += '<line x1="' + Lp + '" y1="' + Y(e.threshold).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(e.threshold).toFixed(1) + '" style="stroke:var(--nino)" stroke-dasharray="5 3"/><text x="' + (Lp + 4) + '" y="' + (Y(e.threshold) - 4).toFixed(1) + '" font-size="9" style="fill:var(--nino)">burst threshold ' + fnum(e.threshold, 1) + ' m/s (2σ)</text>';
    // столбики по дням: западная аномалия вверх (тёплый цвет), восточная вниз
    var bw = Math.max(1, pw / n - .6);
    vals.forEach(function (v, i) {
      if (!fin(v)) return;
      var geo2 = 'x="' + (X(i) - bw / 2).toFixed(1) + '" y="' + Math.min(Y(0), Y(v)).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.abs(Y(v) - Y(0)).toFixed(1) + '"';
      s += '<rect ' + geo2 + ' style="fill:' + (v >= 0 ? 'var(--nino)' : 'var(--nina)') + '" opacity=".8"/>' + (v < 0 ? '<rect ' + geo2 + ' fill="url(#hneg)"/>' : '');
    });
    dates.forEach(function (d, i) { if (i === 0 || i === n - 1 || i === Math.floor(n / 2)) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + (i === 0 ? 'start' : (i === n - 1 ? 'end' : 'middle')) + '">' + esc(d) + '</text>'; });
    var li = n - 1; while (li > 0 && !fin(vals[li])) li--;
    s += '<text x="' + (X(li) - 4).toFixed(0) + '" y="' + (Y(vals[li]) - 6).toFixed(0) + '" text-anchor="end" class="tt">' + fnum(vals[li], 1) + ' m/s</text>';
    return s + '</svg>';
  }

  /* Круг фаз MJO: ось x = −PC2 (≈RMM1), y = PC1 (≈RMM2); след последних 30 дней, точка сегодня,
     круг единичной амплитуды. Сектора подписаны номерами фаз. */
  function chartMJO(M, W, H) {
    var cx = Math.min(W * .34, H * .5), cy = H / 2 + 6, r = Math.min(cx - 14, H / 2 - 22);
    var scale = r / 2.5;
    var s = svgOpen(W, H) + '<text class="tt" x="12" y="15">' + fitText('MJO phase diagram, last 30 days', W, 12) + '</text>';
    s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" style="stroke:var(--grid)"/>';
    s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + scale + '" fill="none" style="stroke:var(--soft)" stroke-dasharray="3 3"/>';
    for (var a = 0; a < 360; a += 45) {
      var rad = a * Math.PI / 180;
      s += '<line x1="' + cx + '" y1="' + cy + '" x2="' + (cx + r * Math.cos(rad)).toFixed(1) + '" y2="' + (cy - r * Math.sin(rad)).toFixed(1) + '" style="stroke:var(--grid)"/>';
      var ph = Math.floor(((a + 22.5 - 180 + 360) % 360) / 45) + 1;
      var mid = (a + 22.5) * Math.PI / 180;
      var west = ph >= 6 && ph <= 8;
      s += '<text x="' + (cx + (r - 12) * Math.cos(mid)).toFixed(1) + '" y="' + (cy - (r - 12) * Math.sin(mid) + 4).toFixed(1) + '" text-anchor="middle" font-size="11" style="fill:' + (west ? 'var(--nino)' : 'var(--soft)') + ';font-weight:' + (west ? 600 : 400) + '">' + ph + '</text>';
    }
    var n = M.pc1.length, from = Math.max(0, n - 30), pts = [];
    for (var i = from; i < n; i++) pts.push([cx + (-M.pc2[i]) * scale, cy - M.pc1[i] * scale]);
    s += poly(pts, 'var(--text)', 1.4, .8);
    pts.forEach(function (p, k) { s += '<circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + (k === pts.length - 1 ? 4.5 : 1.6) + '" style="fill:' + (k === pts.length - 1 ? 'var(--nino)' : 'var(--soft)') + '"/>'; });
    s += '<text x="' + (cx + r + 6) + '" y="' + (cy - 2) + '" font-size="9">Maritime</text><text x="' + (cx + r + 6) + '" y="' + (cy + 9) + '" font-size="9">Continent</text>';
    s += '<text x="' + cx + '" y="' + (cy - r - 5) + '" text-anchor="middle" font-size="9">western Pacific</text>';
    s += '<text x="' + cx + '" y="' + (cy + r + 13) + '" text-anchor="middle" font-size="9">Indian Ocean</text>';
    // амплитуда по дням справа
    var Lp = Math.round(cx + r + 72), R = 14, Tp = 30, B = 26, pw = W - Lp - R, ph2 = H - Tp - B;
    if (pw > 120) {
      var amp = M.amp, vmax = Math.max(2, Math.max.apply(null, amp.filter(fin)));
      var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (v) { return Tp + (vmax - v) / vmax * ph2; };
      s += '<text x="' + Lp + '" y="' + (Tp - 8) + '" font-size="10" class="tt">amplitude, ' + n + ' days</text>';
      s += '<line x1="' + Lp + '" y1="' + Y(1).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(1).toFixed(1) + '" style="stroke:var(--soft)" stroke-dasharray="3 3"/><text x="' + (Lp + 2) + '" y="' + (Y(1) - 3).toFixed(1) + '" font-size="9">1 = organised</text>';
      s += '<line x1="' + Lp + '" y1="' + Y(0).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(0).toFixed(1) + '" style="stroke:var(--grid)"/>';
      // фазы 6–8 — подсветка дней
      amp.forEach(function (v, i) { if (M.phase[i] >= 6 && M.phase[i] <= 8 && v >= 1) s += '<rect x="' + (X(i) - pw / n / 2).toFixed(1) + '" y="' + Tp + '" width="' + (pw / n + .5).toFixed(1) + '" height="' + ph2 + '" style="fill:var(--nino)" opacity=".12"/>'; });
      s += segs(amp.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 1.6);
      s += '<text x="' + Lp + '" y="' + (H - 9) + '">' + esc(M.dates[0]) + '</text><text x="' + (W - R) + '" y="' + (H - 9) + '" text-anchor="end">' + esc(M.dates[n - 1]) + '</text>';
    }
    return s + '</svg>';
  }

  function chartOHC(B, W, H) {
    var items = [B.ohc_2000, B.ohc_700].filter(Boolean);
    if (!items.length) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var RC = Math.max(120, Math.min(210, Math.round(W * .3))), gap = 10, hh = (H - 20 - gap * (items.length - 1)) / items.length;
    var OHCROWS = [];
    var s = svgOpen(W, H);
    items.forEach(function (o, xi) {
      var top = xi * (hh + gap), Lp = 50, Tp = top + 6, pw = W - Lp - RC - 10, ph = hh - 12, n = o.values.length;
      var vmin = Math.min.apply(null, o.values), vmax = Math.max.apply(null, o.values);
      var pad = (vmax - vmin) * .1; vmin -= pad; vmax += pad;
      var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
      s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph.toFixed(1) + '" rx="5" style="fill:var(--ink)" opacity=".03"/>';
      [vmax - pad, vmin + pad, 0].forEach(function (g) { if (g >= vmin && g <= vmax) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(1) + '" x2="' + (Lp + pw) + '" y2="' + Y(g).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 3).toFixed(1) + '" text-anchor="end" font-size="9">' + fnum(g, 0, false) + '</text>'; });
      s += segs(o.values.map(function (v, i) { return [X(i), Y(v)]; }), 'var(--nino)', 1.8);
      s += nowDot(X(n - 1), Y(o.values[n - 1]), 'var(--nino)', 3.5);
      var seenDec = {};
      o.years.forEach(function (y, i) { var dec = Math.floor(y); if (dec % 10 === 0 && !seenDec[dec]) { seenDec[dec] = 1; s += '<text x="' + X(i).toFixed(0) + '" y="' + (Tp + ph + 12) + '" text-anchor="middle" font-size="9">' + dec + '</text>'; } });
      var lx = Lp + pw + 10, ly = Tp + 12;
      /* В плитке правая колонка подписей не помещается ни при какой ширине: уводим её в
         метку легенды, как у остальных графиков (владелец 06.09). */
      if (S._tight) {
        OHCROWS.push([esc(o.title.replace('Ocean heat content, ', '')) + ': ' + fnum(o.last, 1, false) + ' ×10²² J, ' + esc(o.date), 'var(--nino)', 'line']);
      } else {
        s += '<text x="' + lx + '" y="' + ly + '" class="tt" font-size="11">' + esc(o.title.replace('Ocean heat content, ', '')) + '</text>';
        s += '<text x="' + lx + '" y="' + (ly + 14) + '" font-size="10" style="fill:var(--text)">' + fnum(o.last, 1, false) + ' ×10²² J, ' + esc(o.date) + '</text>';
        s += '<text x="' + lx + '" y="' + (ly + 27) + '" font-size="9" style="fill:var(--soft)">' + (o.record ? 'record' : 'below record') + ', +' + fnum(o.rise_10y, 1, false) + ' in 10 y</text>';
        s += '<text x="' + lx + '" y="' + (ly + 40) + '" font-size="9" style="fill:var(--soft)">anomaly from 1955–2006, NCEI</text>';
      }
    });
    if (S._tight && OHCROWS.length) scaleLegend(OHCROWS);
    return s + '</svg>';
  }

  function chartKuwait(K, W, H) {
    var n = K.tmax.length, Lp = 46, R = 40, Tp = 26, B = 26, pw = W - Lp - R, ph = H - Tp - B;
    var vv = K.tmax.filter(fin).concat((K.tmax_clim || []).filter(fin)).concat(K.tmin.filter(fin));
    var vmin = Math.min.apply(null, vv) - 1, vmax = Math.max.apply(null, vv) + 3;
    var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">' + fitText('Kuwait, daily maximum and minimum (ERA5) against the 1991–2020 normal', W, 12) + '</text>';
    s += gridY(vmin, vmax, 5, Y, Lp, R, W, 0);
    if (vmax > 45) s += '<line x1="' + Lp + '" y1="' + Y(45).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(45).toFixed(1) + '" style="stroke:var(--nino)" stroke-dasharray="2 3"/><text x="' + (W - R - 3) + '" y="' + (Y(45) - 3).toFixed(1) + '" text-anchor="end" font-size="9" style="fill:var(--nino)">45 °C</text>';
    if (K.tmax_clim) s += segs(K.tmax_clim.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--soft)', 1.2, pickOp('clim', .9), '5 3');
    s += segs(K.tmin.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--nina)', 1.2, pickOp('tmin', .8), '2 2');
    s += segs(K.tmax.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--nino)', 2, pickOp('tmax'));
    s += legendAt([['daily maximum', 'var(--nino)', 2, '', 'tmax'], ['daily minimum', 'var(--nina)', 1.2, '2 2', 'tmin'], ['normal maximum', 'var(--soft)', 1.2, '5 3', 'clim']], Lp + 6, Tp + 10);
    K.dates.forEach(function (d, i) { if (i === 0 || i === n - 1 || i === Math.floor(n / 2)) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + (i === 0 ? 'start' : (i === n - 1 ? 'end' : 'middle')) + '">' + esc(d) + '</text>'; });
    return s + '</svg>';
  }

  function boxMetric(b, absolute) {
    return { name: b.title + (absolute ? ', daily SST' : ', daily anomaly') + ' — our box on the NOAA grid, one day behind', unit: '°C', step: 'day',
      dates: b.dates, values: absolute ? b.sst : b.anom, analogs: absolute ? {} : (b.analogs || {}) };
  }

  function viewOcean() {
    var D = S.D, O = D.oisst || {}, SB = D.subsurface || {}, k = sub('ocean', 'surface');
    var boxes = O.boxes || {}, T34 = boxes.nino34 || {}, TAO = SB.tao || {}, GD = SB.godas || {};
    var head = 'Ocean';
    if (k === 'surface') head = fin(T34.last_anom) ? 'Niño 3.4 today: ' + fnum(T34.last_anom) + ' °C on our box, ' + (T34.days_stale === 1 ? 'one day' : T34.days_stale + ' days') + ' behind' : 'Daily boxes straight from the NOAA grid';
    else if (k === 'moorings') head = TAO.warmest ? 'Water ' + fnum(TAO.warmest.value, 1) + ' °C above normal is sitting at ' + TAO.warmest.depth + ' m under ' + TAO.warmest.station : 'Below the surface: the moorings';
    else head = GD.max_anom ? 'Reanalysis, ' + esc(GD.month) + ': up to ' + fnum(GD.max_anom.value, 1) + ' °C above normal at ' + GD.max_anom.depth + ' m, ' + esc(GD.max_anom.label) : 'Reanalysis section along the equator';
    var body = stageShell(head, [segBtn('ocean', 'surface', 'Surface, daily', 'surface'), segBtn('ocean', 'moorings', 'Below the surface', 'surface'), segBtn('ocean', 'section', 'Reanalysis section', 'surface')]);
    if (O.error) { body.appendChild(el('div', 'note warn', 'The direct OISST block did not load: ' + esc(O.error))); }

    if (k === 'surface') {
      var pick = S.sub.obox || 'nino34', absolute = !!S.sub.oabs;
      var row = el('div', 'seg sub');
      BOX_ORDER.forEach(function (o) {
        if (!boxes[o[0]]) return;
        var b = el('button', pick === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.obox = o[0]; render(); }; row.appendChild(b);
      });
      var ab = el('button', absolute ? 'on' : '', absolute ? 'absolute °C' : 'anomaly'); ab.type = 'button'; ab.style.marginInlineStart = 'auto';
      ab.onclick = function () { S.sub.oabs = !absolute; render(); }; row.appendChild(ab);
      body.appendChild(row);
      var bx = boxes[pick];
      if (bx && bx.dates && (absolute ? bx.sst : bx.anom)) plot(body, function (w, h) { return chartMetric(boxMetric(bx, absolute), w, h); });
      else body.appendChild(el('div', 'note warn', 'No climatology yet for this box: the anomaly appears once the thirty-year build finishes.'));
      var ck = (O.check || {}).nino34;
      body.appendChild(el('div', 'cap', esc(O.note || '') + ' ' + esc(O.clim || '') + '. Dashes: the same days of 1982, 1997, 2015, 2023 and last year on the same box.' +
        (ck ? ' Check against climatereanalyzer on ' + ck.n_days + ' overlapping days: mean offset ' + fnum(ck.offset, 3) + ' °C (sd ' + ck.sd + '); the spliced tail carries this offset.' : '')));
      var kp = el('div', 'kpis');
      kp.innerHTML = BOX_ORDER.map(function (o) {
        var b = boxes[o[0]]; if (!b || b.error && !b.dates) return '';
        var jk = { nino34: 'n34_box', nino12: 'n12_box', gulf: 'gulf_sst' }[o[0]];
        return '<div class="kpi"><div class="kn">' + (ZONES[o[0]] ? zone(o[0]) : esc(o[1])) + '</div><div class="kv">' + (fin(b.last_anom) ? fnum(Math.abs(b.last_anom) < 0.005 ? 0 : b.last_anom) : fnum(b.last_sst, 2, false)) + '<small>' + (fin(b.last_anom) ? '°C anom' : '°C abs') + '</small></div><div class="km">' + esc(b.last_date) + (fin(b.chg30) ? '; 30 d ' + fnum(b.chg30) : '') + (fin(b.mean7) ? '; 7 d mean ' + fnum(b.mean7) : '') + (b.error ? '; NRT did not answer, showing the last good tail' : '') + '</div>' + (jk ? kmeta(jk) : kmeta(null, 'NOAA OISST NRT via ERDDAP', b.last_date)) + '</div>';
      }).join('');
      body.appendChild(kp);
      return;
    }
    if (k === 'moorings') {
      if (!TAO.stations || TAO.error) { body.appendChild(el('div', 'note warn', 'The moorings did not load: ' + esc(TAO.error || SB.error || 'no data'))); return; }
      var sec = TAO.section || {}, good = (TAO.stations || []).filter(function (s) { return s.anom; });
      if (good.length) {
        plot(body, function (w, h) {
          return chartSection({ title: 'Temperature anomaly under the equator, moorings, five-day mean to ' + TAO.last_date,
            cols: good.map(function (s) { return s.label; }), rows: TAO.depths, get: function (i, j) { return good[i].anom[j]; },
            d20: good.map(function (s) { return s.d20; }), legendNote: good.length + ' moorings' }, w, h);
        });
      } else body.appendChild(el('div', 'note warn', 'The moorings answered, but their thirty-year climatologies are still being built: anomalies appear when they finish.'));
      body.appendChild(el('div', 'cap', esc(TAO.note || '') + ' ' + esc(TAO.clim || '') + '. Columns are moorings west to east; the line is the 20 °C isotherm.'));
      var kt = el('div', 'kpis');
      kt.innerHTML = (TAO.warmest ? '<div class="kpi"><div class="kn">' + term('tao', 'warmest layer') + '</div><div class="kv">' + fnum(TAO.warmest.value, 1) + '<small>°C at ' + TAO.warmest.depth + ' m</small></div><div class="km">' + esc(TAO.warmest.station) + ', five-day mean to ' + esc(TAO.warmest.date) + '</div>' + kmeta('subsurface_warmest') + '</div>' : '') +
        '<div class="kpi"><div class="kn">' + term('d20', '20 °C isotherm') + '</div><div class="kv">' + (TAO.d20_east == null ? '—' : TAO.d20_east) + '<small>m east</small></div><div class="km">' + (TAO.d20_west == null ? '—' : TAO.d20_west) + ' m in the west; normally shallow in the east and deep in the west</div>' + kmeta('d20_east') + '</div>' +
        '<div class="kpi"><div class="kn">moorings live</div><div class="kv">' + TAO.n_live + '<small>of ' + (TAO.stations || []).length + '</small></div><div class="km">' + (TAO.stations || []).map(function (s) { return s.label + (s.error ? ' ✗' : ' ' + (s.d20 == null ? '—' : s.d20 + ' m')); }).join(' · ') + '</div>' + kmeta(null, 'TAO/TRITON via ERDDAP', TAO.last_date) + '</div>';
      body.appendChild(kt);
      return;
    }
    if (!GD.temp || GD.error) { body.appendChild(el('div', 'note warn', 'The reanalysis did not load: ' + esc(GD.error || SB.error || 'no data'))); return; }
    var A = GD.anom, hasA = !!A;
    plot(body, function (w, h) {
      return chartSection({ title: (hasA ? 'Temperature anomaly' : 'Temperature') + ' along the equator (2°S–2°N), GODAS ' + GD.month,
        cols: GD.labels, rows: GD.levels, get: function (i, j) { return hasA ? A[j][i] : GD.temp[j][i]; },
        d20: GD.d20, d20clim: GD.d20_clim, legendNote: 'monthly' }, w, h);
    });
    body.appendChild(el('div', 'cap', esc(GD.note || '') + ' ' + esc(GD.clim || '') + '.'));
    var hc = GD.heat_content || {}, hv = hc.values || [];
    var kg = el('div', 'kpis');
    kg.innerHTML = (GD.max_anom ? '<div class="kpi"><div class="kn">' + term('godas', 'warmest anomaly') + '</div><div class="kv">' + fnum(GD.max_anom.value, 1) + '<small>°C at ' + GD.max_anom.depth + ' m</small></div><div class="km">' + esc(GD.max_anom.label) + ', ' + esc(GD.month) + '</div>' + kmeta(null, 'GODAS via PSL', GD.month) + '</div>' : '') +
      (hv.length ? '<div class="kpi"><div class="kn">upper-ocean heat, 0–300 m</div><div class="kv">' + fnum(hv[hv.length - 1]) + '<small>°C</small></div><div class="km">' + esc(hc.band) + '; a month ago ' + fnum(hv[hv.length - 2]) + '</div>' + kmeta(null, 'GODAS, our climatology', GD.month) + '</div>' : '') +
      '<div class="kpi"><div class="kn">lag</div><div class="kv" style="font-size:17px">~6 weeks</div><div class="km">the moorings tab shows the same water a month earlier</div>' + kmeta(null, 'NCEP GODAS', GD.month) + '</div>';
    body.appendChild(kg);
  }

  // ---------------------------------------------------------------- Kuwait · Gulf
  function gulfHead(G, k) {
    var sea = (G || {}).sea || {}, K = (G || {}).kuwait || {};
    if (k === 'sea' && fin(sea.last_sst)) return 'The Gulf off Kuwait: ' + fnum(sea.last_sst, 1, false) + ' °C, ' + fnum(Math.abs(sea.last_anom) < 0.005 ? 0 : sea.last_anom) + ' against its own normal' + (sea.days_over_35 ? ', ' + sea.days_over_35 + ' days above 35 °C this summer' : '');
    if (k === 'weather' && !K.error) return 'Kuwait: the last 30 days ' + fnum(K.tmax_anom_30d, 1) + ' °C against the normal daily maximum';
    if (k === 'winter') return 'Winter: a wetter storm track is the risk, not a forecast';
    if (k === 'food') return 'Wheat from Australia, rice from India: the two chains this event can touch';
    return 'Gulf and Arabian Peninsula: what is measured here and what the literature says';
  }
  /* Измеренное по Заливу и Кувейту — теперь внутри вкладки Regions (владелец 04.09, вечер:
     «не выпячивать ничего»): регион выбирается в списке, а эти четыре вида — его подвкладки. */
  function gulfBody(body, k, G) {
    var D = S.D;
    if (!G || G.error) { body.appendChild(el('div', 'note warn', 'The Gulf measurements did not load: ' + esc((G || {}).error || 'no data'))); return; }
    var sea = G.sea || {}, K = G.kuwait || {}, Wn = G.winter || {}, I = G.imports || {}, BGc = ((D.background || {}).calendar || {}).items || [];
    var rowS = el('div', 'seg sub');
    [['sea', 'Sea'], ['weather', 'Weather'], ['winter', 'Winter outlook'], ['food', 'Imports'], ['ref', 'Reference']].forEach(function (o) {
      var b = el('button', k === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.gulf = o[0]; render(); }; rowS.appendChild(b);
    });
    body.appendChild(rowS);
    if (k === 'ref') return;

    if (k === 'sea') {
      var absolute = !!S.sub.gabs;
      var row = el('div', 'seg sub');
      [['anomaly', false], ['absolute °C', true]].forEach(function (o) { var b = el('button', absolute === o[1] ? 'on' : '', o[0]); b.type = 'button'; b.onclick = function () { S.sub.gabs = o[1]; render(); }; row.appendChild(b); });
      body.appendChild(row);
      if (sea.dates) plot(body, function (w, h) { return chartMetric(boxMetric({ title: 'Persian Gulf', dates: sea.dates, sst: sea.sst, anom: sea.anom, analogs: sea.analogs }, absolute), w, h); });
      else body.appendChild(el('div', 'note warn', 'The Gulf box has not loaded yet.'));
      body.appendChild(el('div', 'cap', esc(sea.note || '') + ' Dashes: the same days of the strongest past events and last year on the same box.'));
      var ks = el('div', 'kpis');
      ks.innerHTML = '<div class="kpi"><div class="kn">' + term('gulfbox', 'Gulf today') + '</div><div class="kv">' + fnum(sea.last_sst, 1, false) + '<small>°C</small></div><div class="km">anomaly ' + fnum(Math.abs(sea.last_anom) < 0.005 ? 0 : sea.last_anom) + ' on ' + esc(sea.last_date) + (fin(sea.chg30) ? '; 30 d ' + fnum(sea.chg30) : '') + '</div>' + kmeta('gulf_sst') + '</div>' +
        '<div class="kpi"><div class="kn">days above 35 °C</div><div class="kv">' + (sea.days_over_35 == null ? '—' : sea.days_over_35) + '<small>of 120</small></div><div class="km">peak ' + fnum(sea.max_sst, 1, false) + ' °C on ' + esc(sea.max_sst_date || '') + '; the stress line for desalination and fisheries</div>' + kmeta(null, 'NOAA OISST NRT, our box', sea.last_date) + '</div>' +
        '<div class="kpi"><div class="kn">the box</div><div class="kv" style="font-size:15px;line-height:1.3">24–30°N<br>48–56°E</div><div class="km">sea cells only, full 0.25° resolution, own 1991–2020 climatology</div>' + kmeta(null, 'our box mean on the NOAA grid', sea.fetched) + '</div>';
      body.appendChild(ks);
      return;
    }
    if (k === 'weather') {
      if (K.error) { body.appendChild(el('div', 'note warn', 'Kuwait weather did not load: ' + esc(K.error))); return; }
      plot(body, function (w, h) { return chartKuwait(K, w, h); });
      body.appendChild(el('div', 'cap', esc(K.source) + '; ' + esc(K.clim) + '. The rainy season here runs November to April; “season” below counts from 1 September.'));
      var kk = el('div', 'kpis');
      kk.innerHTML = '<div class="kpi"><div class="kn">last 30 days</div><div class="kv">' + fnum(K.tmax_anom_30d, 1) + '<small>°C</small></div><div class="km">daily maximum against the normal; data to ' + esc(K.last_date) + '</div>' + kmeta('kuwait_tmax30') + '</div>' +
        '<div class="kpi"><div class="kn">hottest day this year</div><div class="kv">' + fnum((K.hottest || {}).value, 1, false) + '<small>°C</small></div><div class="km">' + esc((K.hottest || {}).date || '') + '; ' + K.hot_days + ' days at or above 45 °C against a normal ' + K.hot_days_normal + '</div>' + kmeta(null, 'ERA5 via Open-Meteo', K.last_date) + '</div>' +
        '<div class="kpi"><div class="kn">rain since ' + esc((K.rain_season_from || '').slice(5)) + '</div><div class="kv">' + fnum(K.rain_season_mm, 0, false) + '<small>mm</small></div><div class="km">normal to date ' + fnum(K.rain_season_normal_todate_mm, 0, false) + ' mm; a whole season ' + fnum(K.rain_season_normal_mm, 0, false) + ' mm' + (K.last_rain ? '; last rain ' + esc(K.last_rain.date) + ', ' + K.last_rain.mm + ' mm' : '') + '</div>' + kmeta(null, 'ERA5 via Open-Meteo', K.last_date) + '</div>' +
        '<div class="kpi"><div class="kn">this calendar year</div><div class="kv">' + fnum(K.rain_ytd_mm, 0, false) + '<small>mm</small></div><div class="km">normal to date ' + fnum(K.rain_ytd_normal_mm, 0, false) + ' mm</div>' + kmeta(null, 'ERA5 via Open-Meteo', K.last_date) + '</div>';
      body.appendChild(kk);
      return;
    }
    if (k === 'winter') {
      var RN = (D.oni || {}).roni || {}, DM = (D.background || {}).dmi || {};
      body.appendChild(el('div', 'lead', '<b>' + esc(Wn.claim || '') + '</b>'));
      var g = el('div', 'gloss');
      g.innerHTML = (Wn.refs || []).map(function (r) { return '<div class="gl-i"><b>' + esc(r.what) + '</b><div class="s">' + esc(r.src) + (r.url ? ' · <a href="' + esc(r.url) + '" target="_blank" rel="noopener">source</a>' : '') + '</div></div>'; }).join('') +
        '<div class="gl-i"><b>What the indices say now</b>' + term('roni', 'RONI') + ' ' + fnum(RN.last) + ' (' + esc(RN.last_season || '') + '), ' + term('iod', 'Indian Ocean Dipole') + ' ' + fnum(DM.last) + ' (' + esc(DM.phase || '') + ', ' + esc(DM.date || '') + '). Hochman et al. find the two act together on Middle East rainfall; a positive dipole with an El Niño is the wetter combination.<div class="s">' + vLink('the indices', 'air', 'indices') + '</div></div>';
      body.appendChild(g);
      body.appendChild(el('div', 'lead', '<b>Seasonal forecasts to read, with the caveat that they are forecasts and this panel is not:</b>'));
      var f = el('div', 'gloss');
      f.innerHTML = (Wn.forecasts || []).map(function (r) { return '<div class="gl-i"><b><a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.name) + '</a></b>' + esc(r.note) + '</div>'; }).join('');
      body.appendChild(f);
      body.appendChild(el('div', 'note warn', '<strong>Quoted, not measured.</strong> The teleconnection lines above are the literature; the panel measures the sea and the weather here and the indices in the Pacific and the Indian Ocean, and nothing more. Formulate it as a risk of a wet winter and flash floods, never as a forecast.'));
      return;
    }
    // imports
    var pick = S.sub.grain || 'wheat', pr = (G.prices || []).filter(function (x) { return x.key === pick; })[0];
    var rowg = el('div', 'seg sub');
    (G.prices || []).forEach(function (x) { var b = el('button', pick === x.key ? 'on' : '', x.name); b.type = 'button'; b.onclick = function () { S.sub.grain = x.key; render(); }; rowg.appendChild(b); });
    body.appendChild(rowg);
    if (pr) plot(body, function (w, h) { return chartMetric({ name: pr.name + ', ' + pr.unit + ' — World Bank Pink Sheet', unit: pr.unit, step: 'month', dates: pr.months, values: pr.values }, w, h); });
    body.appendChild(el('div', 'cap', 'Monthly world prices; “since onset” counts from ' + esc((G.prices || [{}])[0].onset || 'the onset month') + ', the month the ONI crossed +0.5. A coincidence in time is not a cause.'));
    var t = el('div', 'gloss');
    t.innerHTML = (I.rows || []).map(function (r) {
      var lp = (G.prices || []).filter(function (x) { return x.key === r.commodity; })[0];
      return '<div class="gl-i"><b>' + esc(r.item) + (lp && fin(lp.since_onset_pct) ? ' · ' + fnum(lp.since_onset_pct, 1) + ' % since onset' : '') + '</b>' + esc(r.fact) + '<div class="s">' + esc(r.src) + (lp ? ' · price ' + lp.value + ' ' + esc(lp.unit) + ' in ' + esc(lp.date) : '') + '</div></div>';
    }).join('') +
      (I.precedents || []).map(function (r) { return '<div class="gl-i"><b>Precedent, ' + esc(r.when) + '</b>' + esc(r.what) + '<div class="s">' + esc(r.src) + '</div></div>'; }).join('');
    body.appendChild(t);
    var wl = el('div', 'gloss');
    wl.innerHTML = (I.watch || []).map(function (r) {
      var w0 = r.name.split(' ')[0];
      var nx = w0 === 'FAO' ? null : BGc.filter(function (c) { return c.name.toLowerCase().indexOf(w0.toLowerCase()) === 0; })[0];
      return '<div class="gl-i"><b><a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.name) + '</a></b>' + esc(r.cadence) + (nx ? '<div class="s">next: ' + esc(nx.next) + ' (' + (nx.in_days === 0 ? 'today' : 'in ' + nx.in_days + ' d') + ')</div>' : '') + '</div>';
    }).join('');
    body.appendChild(wl);
    body.appendChild(el('div', 'note warn', '<strong>Quoted, not measured.</strong> Import shares and the precedents are from the sources named, as of ' + esc(I.as_of || '') + '; the prices are measured monthly.'));
  }





  // ---------------------------------------------------------------- References (владелец 05.09)
  /* ЕДИНЫЙ РЕЕСТР. Три полки: наши разобранные работы (из links.json — только те, что
     привязаны к утверждениям), источники данных (из справочника цепочки) и литература (из
     справочников регионов, Залива, фона и глоссария). Ничего не дублируется руками: реестр
     собирается из тех же файлов, которые кормят сцены, и у каждой строки — где она
     использована и зачем. */
  var BLOCK_LBL = { models: 'How the forecast models break', peak: 'When the growth stops', food: 'El Niño and food prices', type: 'Eastern-type El Niño' };
  function anchorLabel(key) {
    var D = S.D, i = key.indexOf(':'), kind = key.slice(0, i), id = key.slice(i + 1);
    if (kind === 'risk') { var r = (D.risks || []).filter(function (x) { return x.id === id; })[0]; return r ? 'risk: ' + r.title : (/^\d+$/.test(id) && D.risks[id] ? 'risk: ' + D.risks[id].title : null); }
    if (kind === 'alert') { var a = (D.alerts || []).filter(function (x) { return aslug(x.title) === id; })[0]; return a ? 'alert: ' + a.title : (/^\d+$/.test(id) && D.alerts[id] ? 'alert: ' + D.alerts[id].title : null); }
    if (kind === 'term') return S.G[id] ? 'term: ' + S.G[id].name : null;
    if (kind === 'region') { var rg = (((D.regions || {}).items) || []).filter(function (x) { return x.id === id; })[0]; return rg ? 'region: ' + rg.name : null; }
    if (kind === 'block') return 'block: ' + (BLOCK_LBL[id] || id);
    return null;
  }
  function refsWorks() {
    var by = {};
    Object.keys(S.L.anchors || {}).forEach(function (k) {
      var lab = anchorLabel(k);
      if (!lab) return;                                     // якорь прошлого прогона, которого больше нет
      (S.L.anchors[k] || []).forEach(function (l) {
        var w = by[l.id] || (by[l.id] = { id: l.id, date: l.date, folder: l.folder, title: l.our_title || l.title, orig: l.title, oneliner: l.oneliner, uses: [] });
        w.uses.push({ at: lab, why: l.why, kind: l.kind, weak: l.weak });
      });
    });
    return Object.keys(by).map(function (k) { return by[k]; }).sort(function (a, b) { return b.uses.length - a.uses.length || (b.date > a.date ? 1 : -1); });
  }
  function refsSources() {
    var nodes = (S.C.nodes || []), byId = {};
    nodes.forEach(function (n) { byId[n.id] = n; });
    return nodes.filter(function (n) { return n.layer === 'src'; }).map(function (n) {
      var f = chainFresh(n);
      var users = nodes.filter(function (m) { return (m.in || []).indexOf(n.id) >= 0; }).map(function (m) { return m.name; });
      var states = [];
      users.forEach(function (u) { nodes.forEach(function (m) { if (m.layer === 'state' && (m.in || []).some(function (x) { return byId[x] && byId[x].name === u; })) states.push(m.name); }); });
      return { name: n.name, sub: n.sub, url: n.url, def: n.def, why: n.why, cadence: n.cadence, date: f.date, dot: f.dot, users: users, states: states.filter(function (v, i, a) { return a.indexOf(v) === i; }) };
    });
  }
  function refsLiterature() {
    var D = S.D, out = [], seen = {};
    function push(name, url, desc, at) {
      var key = (name || '').toLowerCase().slice(0, 60);
      if (!name || seen[key]) { if (seen[key] && at) seen[key].at.push(at); return; }
      seen[key] = { name: name, url: url || '', desc: desc || '', at: at ? [at] : [] };
      out.push(seen[key]);
    }
    ((D.gulf || {}).winter || {}).refs && D.gulf.winter.refs.forEach(function (r) { push(r.src, r.url, r.what, 'Regions · Gulf · winter outlook'); });
    ((D.gulf || {}).winter || {}).forecasts && D.gulf.winter.forecasts.forEach(function (r) { push(r.name, r.url, r.note, 'Regions · Gulf · winter outlook'); });
    var I = (D.gulf || {}).imports || {};
    (I.rows || []).forEach(function (r) { push(r.src, '', r.fact, 'Regions · Gulf · imports'); });
    (I.precedents || []).forEach(function (r) { push(r.src, '', r.when + ': ' + r.what, 'Regions · Gulf · imports'); });
    (I.watch || []).forEach(function (r) { push(r.name, r.url, r.cadence, 'Regions · Gulf · imports'); });
    var E = (D.background || {}).eei;
    if (E) push(E.src, E.url, E.claim, 'Dynamics · background');
    var RS = (D.regions || {}).sources || {};
    Object.keys(RS).forEach(function (k) {
      var t = RS[k], m = SRC_RX.exec(t), url = m ? (/^https?:/i.test(m[1]) ? m[1] : 'https://' + m[1]) : '';
      var used = (((D.regions || {}).items) || []).filter(function (r) { return (r.sources || []).indexOf(t) >= 0; }).map(function (r) { return r.name; });
      push(t.split(',')[0], url, t, used.length ? 'Regions: ' + used.slice(0, 6).join(', ') + (used.length > 6 ? ' …' : '') : 'Regions');
    });
    Object.keys(S.G).forEach(function (k) {
      var g = S.G[k]; if (!g.src) return;
      var m = SRC_RX.exec(g.src), url = m ? (/^https?:/i.test(m[1]) ? m[1] : 'https://' + m[1]) : '';
      push(g.src.split(';')[0], url, g.src, 'Glossary: ' + g.name);
    });
    return out;
  }
  function viewRefs() {
    var k = sub('refs', 'works'), D = S.D;
    var works = refsWorks(), srcs = refsSources(), lit = refsLiterature();
    var body = stageShell('References: ' + works.length + ' parsed works attached, ' + srcs.length + ' data sources, ' + lit.length + ' literature and reference items',
      [segBtn('refs', 'works', 'Our works (' + works.length + ')', 'works'), segBtn('refs', 'sources', 'Data sources (' + srcs.length + ')', 'works'), segBtn('refs', 'literature', 'Literature (' + lit.length + ')', 'works')]);
    body.classList.add('scroll');
    var tgt = window.matchMedia('(max-width:900px)').matches ? '' : ' target="_blank" rel="noopener"';
    var list = el('div', 'refs');
    if (k === 'works') {
      list.innerHTML = works.map(function (w) {
        var pay = { name: w.title, html: '<p>' + esc(w.oneliner || '') + '</p><p><b>Used at</b></p>' + w.uses.map(function (u) { return '<p class="wk-p">' + esc(u.at) + (u.why ? '<i>' + esc(u.why) + '</i>' : '') + '</p>'; }).join(''), src: 'arXiv ' + w.id + ' · ' + w.orig, date: w.date };
        return '<div class="ref" data-src="' + esc(JSON.stringify(pay)) + '"><div class="ref-t"><a href="/lang/en/archive/' + esc(w.date) + '/' + esc(w.folder) + '/index.html"' + tgt + '>' + esc(w.title) + '</a><span class="ref-n">' + w.uses.length + ' use' + (w.uses.length > 1 ? 's' : '') + '</span></div>' +
          '<div class="ref-d">' + esc(w.oneliner || w.orig) + '</div><div class="ref-m"><span class="wk-num">arXiv ' + esc(w.id) + '</span> · ' + esc(w.date) + ' · ' + esc(w.uses.map(function (u) { return u.at.split(':')[0]; }).filter(function (v, i, a) { return a.indexOf(v) === i; }).join(', ')) + '</div></div>';
      }).join('') || '<div class="note">No works attached yet.</div>';
      body.appendChild(list);
      body.appendChild(el('div', 'cap', 'Only the papers that a model judged to belong next to a statement of this panel; the full pool is our archive of parsed works. Point at a row for where it is used and why; the link opens our version. Register built from data/enso/links.json at ' + esc(S.L.built || '') + '.'));
    } else if (k === 'sources') {
      list.innerHTML = srcs.map(function (s) {
        var pay = { name: s.name, def: s.def, why: s.why + (s.states.length ? ' Feeds: ' + s.states.join('; ') + '.' : ''), src: s.sub + (s.cadence ? ' · ' + s.cadence : ''), date: s.date, url: s.url };
        return '<div class="ref" data-src="' + esc(JSON.stringify(pay)) + '"><div class="ref-t"><i class="dot ' + s.dot + '"></i>' + (s.url ? '<a href="' + esc(s.url) + '"' + tgt + '>' + esc(s.name) + ' ↗</a>' : esc(s.name)) + '<span class="ref-n">' + esc(s.cadence || '') + '</span></div>' +
          '<div class="ref-d">' + esc(s.sub || '') + '</div><div class="ref-m">' + (s.date ? 'data ' + esc(s.date) + ' · ' : '') + 'read by ' + esc(s.users.join(', ')) + (s.states.length ? ' → ' + esc(s.states.slice(0, 3).join('; ')) + (s.states.length > 3 ? ' …' : '') : '') + '</div></div>';
      }).join('');
      body.appendChild(list);
      body.appendChild(el('div', 'cap', 'Every source is open and machine-readable; the dot is whether it answered on the last update, the date is when its data last changed. The same register drives the Data chain tab.'));
    } else {
      list.innerHTML = lit.map(function (r) {
        var pay = { name: r.name, def: r.desc, why: r.at.length ? 'Used at: ' + r.at.join('; ') + '.' : '', url: r.url };
        return '<div class="ref" data-src="' + esc(JSON.stringify(pay)) + '"><div class="ref-t">' + (r.url ? '<a href="' + esc(r.url) + '"' + tgt + '>' + esc(r.name) + ' ↗</a>' : esc(r.name)) + '</div>' +
          '<div class="ref-d">' + esc(r.desc) + '</div>' + (r.at.length ? '<div class="ref-m">' + esc(r.at.join(' · ')) + '</div>' : '') + '</div>';
      }).join('');
      body.appendChild(list);
      body.appendChild(el('div', 'cap', 'Quoted, not measured: the papers, agencies and reports behind the regional impacts, the winter outlook, the import chain, the energy imbalance and the glossary. Where a line carries a link it goes to the publisher.'));
    }
  }

  // ---------------------------------------------------------------- Overview (владелец 05.09)
  /* ОДИН ЭКРАН НА ВСЁ. Сверху — строка ключевых показателей, каждый со своей мини-картинкой
     (дуга, кольцо, полоса, искра, стрелка); ниже — мозаика из всех графиков панели, каждый
     в своём маленьком окне, с подсказкой сжатого смысла; щелчок ведёт в его раздел.
     Открывается на весь экран. Графики — те же функции, что и на своих сценах: одна правда. */
  function plainText(h) { return String(h == null ? '' : h).replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim(); }
  function ovKpi(kn, big, small, vis, go, pay, jk) {
    var d = el('div', 'ov-kpi');
    /* Подсказка — чистым текстом: имя показателя приходит с плашкой зоны, а подсказка
       экранирует разметку и показывала «/span» (владелец 05.09). */
    d.setAttribute('data-src', JSON.stringify(pay || { name: plainText(kn), def: plainText(big) + ' — ' + plainText(small), why: 'Click to open the section.' }));
    d.innerHTML = '<div class="kn">' + kn + '</div><div class="ov-row"><div class="kv">' + big + '</div><div class="ov-vis">' + (vis || '') + '</div></div><div class="km">' + small + '</div>' +
      (jk ? '<span class="dcal-wrap">' + (typeof jk === 'string' ? dateBadge(jk) : dateBadge(null, jk[0], jk[1])) + '</span>' : '');
    d.addEventListener('click', function (ev) { if (ev.target.closest('.dcal')) return; S.full = false; S.view = go[0]; if (go[1]) S.sub[go[0]] = go[1]; S.risk = null; render(); });
    return d;
  }
  function arcGauge(v, max, color) {
    var r = 17, c = 2 * Math.PI * r, f = Math.max(0, Math.min(1, v / max));
    return '<svg viewBox="0 0 44 44" width="44" height="44"><circle cx="22" cy="22" r="' + r + '" fill="none" style="stroke:var(--grid)" stroke-width="5"/>' +
      '<circle cx="22" cy="22" r="' + r + '" fill="none" style="stroke:' + color + '" stroke-width="5" stroke-dasharray="' + (c * f).toFixed(1) + ' ' + c.toFixed(1) + '" transform="rotate(-90 22 22)" stroke-linecap="round"/></svg>';
  }
  function donut(parts) {
    var tot = 0; parts.forEach(function (x) { tot += x[0]; });
    if (!tot) return '';
    var r = 17, c = 2 * Math.PI * r, off = 0, s = '<svg viewBox="0 0 44 44" width="44" height="44">';
    parts.forEach(function (x) {
      var len = c * x[0] / tot;
      s += '<circle cx="22" cy="22" r="' + r + '" fill="none" style="stroke:' + x[1] + '" stroke-width="7" stroke-dasharray="' + len.toFixed(1) + ' ' + c.toFixed(1) + '" stroke-dashoffset="' + (-off).toFixed(1) + '" transform="rotate(-90 22 22)"/>';
      off += len;
    });
    return s + '</svg>';
  }
  function barFill(pct, color) {
    return '<svg viewBox="0 0 60 14" width="60" height="14"><rect x="0" y="3" width="60" height="8" rx="4" style="fill:var(--grid)"/><rect x="0" y="3" width="' + Math.max(0, Math.min(60, pct * .6)).toFixed(1) + '" height="8" rx="4" style="fill:' + color + '"/></svg>';
  }
  function twoBars(a, b, la, lb, color) {
    var mx = Math.max(a, b, 1);
    return '<svg viewBox="0 0 60 30" width="60" height="30"><text x="0" y="9" font-size="8" style="fill:var(--soft)">' + la + '</text><rect x="22" y="2" width="' + (38 * a / mx).toFixed(1) + '" height="8" rx="2" style="fill:' + color + '"/>' +
      '<text x="0" y="24" font-size="8" style="fill:var(--soft)">' + lb + '</text><rect x="22" y="17" width="' + (38 * b / mx).toFixed(1) + '" height="8" rx="2" style="fill:var(--soft)"/></svg>';
  }
  function arrow(v, d) { return fin(v) ? '<span class="' + upDown(v) + '">' + (v > 0 ? '▲' : (v < 0 ? '▼' : '=')) + ' ' + fnum(Math.abs(v), d == null ? 1 : d, false) + '</span>' : ''; }

  function ovTiles() {
    var D = S.D, NW = D.noaa, N = D.nino34, IRI = D.iri && !D.iri.error ? D.iri : null, A = D.air || {}, O = D.oisst || {}, SB = D.subsurface || {}, BG = D.background || {}, FO = D.food && !D.food.error ? D.food : null, G = D.gulf || {};
    var T2 = [];
    function add(title, meaning, go, draw) { if (draw) T2.push({ title: title, meaning: meaning, go: go, draw: draw }); }
    var W = D.watch;
    add('Niño 3.4 against the strongest events', 'Rank ' + N.rank_same30 + ' among the analogues on the same 30 days; the record of the series is ' + fnum(N.peak_estimate.hist_ceiling) + '.', ['now', 'analogs'], function (w, h) { return chartAnalogs(N, w, h); });
    add('Pacific map, this week', 'The four Niño boxes against the same week of 1997.', ['now', 'map'], function (w, h) { return pacific(NW, w, h); });
    add('Weekly indices', 'Niño 1+2 ' + fnum(NW.latest.n12a, 1) + ', 3 ' + fnum(NW.latest.n3a, 1) + ', 3.4 ' + fnum(NW.latest.n34a, 1) + ', 4 ' + fnum(NW.latest.n4a, 1) + '.', ['now', 'weekly'], function (w, h) { return chartNoaa(NW, w, h); });
    add('Weekly Niño 3.4 vs strongest', 'The weekly index on the same calendar as 1982, 1997, 2015, 2023.', ['now', 'weekly_a'], function (w, h) { var k0 = S.sub.wkey; S.sub.wkey = 'n34a'; var r = chartNoaaAnalog(NW, w, h); S.sub.wkey = k0; return r; });
    ['nino34', 'nino3', 'nino12', 'nino4', 'gulf', 'world'].forEach(function (bx) {
      var b = (O.boxes || {})[bx]; if (!b || !b.anom) return;
      add(b.title + ', daily box', 'Our box on the NOAA grid: ' + fnum(b.last_anom) + ' °C on ' + b.last_date + ', one day behind.', ['ocean', 'surface'], function (w, h) { return chartMetric(boxMetric(b, false), w, h, b.title + ' daily'); });
    });
    var TAO = SB.tao || {}, good = (TAO.stations || []).filter(function (s) { return s.anom; });
    if (good.length) add('Under the equator: moorings', 'Warmest layer ' + fnum((TAO.warmest || {}).value, 1) + ' °C at ' + (TAO.warmest || {}).depth + ' m under ' + (TAO.warmest || {}).station + '.', ['ocean', 'moorings'], function (w, h) { return chartSection({ title: 'Moorings, anomaly by depth', cols: good.map(function (s) { return s.label; }), rows: TAO.depths, get: function (i, j) { return good[i].anom[j]; }, d20: good.map(function (s) { return s.d20; }) }, w, h); });
    var GD = SB.godas || {};
    if (GD.anom) add('Reanalysis section', 'GODAS ' + GD.month + ': up to ' + fnum((GD.max_anom || {}).value, 1) + ' °C at ' + (GD.max_anom || {}).depth + ' m.', ['ocean', 'section'], function (w, h) { return chartSection({ title: 'GODAS ' + GD.month, cols: GD.labels, rows: GD.levels, get: function (i, j) { return GD.anom[j][i]; }, d20: GD.d20, d20clim: GD.d20_clim }, w, h); });
    if (IRI) {
      add('Model plume', (IRI.class_tally || {}).broke + ' of ' + Object.keys(IRI.models || {}).length + ' models broken; live RMS ' + fnum(liveNow(IRI, 'rms')) + '.', ['models', 'plume'], function (w, h) { return chartPlume(IRI, NW.latest.n34a, w, h); });
      if (IRI.stack) add('Three issues stacked', 'How the plume caught up with the event, issue by issue.', ['models', 'stack'], function (w, h) { return chartStack(IRI.stack, NW.latest.n34a, w, h); });
      if (IRI.breakdown) add('How the models break', 'Share below reality by issue.', ['models', 'breakdown'], function (w, h) { return chartBreakdown(IRI.breakdown, w, h); });
    }
    if (A.coupling) add('Coupling', A.coupling.score + ' of ' + A.coupling.of + ' atmospheric signs in place.', ['air', 'coupling'], function (w, h) { return chartAir(A.coupling.parts, w, h); });
    if (A.fuel) add('Fuel: warm water volume', A.fuel.share_of_record + ' % of the record; leads the surface by ' + (A.fuel.lead || {}).lag + ' months.', ['air', 'fuel'], function (w, h) { return chartFuel(A.fuel, NW, w, h); });
    if (A.layers && A.layers.items) add('Satellite layers', 'The troposphere follows the ocean by three months.', ['air', 'layers'], function (w, h) { return chartLayers(A.layers.items, w, h); });
    var WD = (D.wind || {}).era5;
    if (WD && WD.dates) add('Westerly wind bursts', (WD.events || []).length + ' bursts in 120 days; last week ' + fnum(WD.mean7, 1) + ' m/s.', ['air', 'wind'], function (w, h) { return chartWind(WD, w, h); });
    if (D.mjo && D.mjo.dates) add('MJO', 'Phase ' + D.mjo.last.phase + ', amplitude ' + D.mjo.last.amp + '.', ['air', 'mjo'], function (w, h) { return chartMJO(D.mjo, w, h); });
    ['mei', 'dmi'].forEach(function (k) { var blk = BG[k]; if (blk) add(blk.title, blk.title + ' ' + fnum(blk.last) + ' in ' + blk.date + '.', ['air', 'indices'], function (w, h) { return chartMetric({ name: blk.title, unit: blk.unit, step: 'month', dates: blk.months, values: blk.values, levels: blk.levels || {} }, w, h, blk.title); }); });
    [['sst_nino34', 'Niño 3.4, 400 days'], ['sst_world', 'World ocean, 400 days'], ['t2_world', 'Land+ocean, 400 days']].forEach(function (x) {
      var w0 = W[x[0]]; if (w0) add(x[1], 'Last day ' + fnum(w0.last_value) + ', record run ' + w0.records.streak + ' days.', ['trend', x[0]], function (w, h) { return chartRecent(w0, w, h); });
    });
    if (S.H && S.H.length > 1) add('Our risk index by update', 'Index ' + D.risk_index + ' of 100.', ['trend', 'index'], function (w, h) { return chartHistory(S.H, w, h); });
    if (BG.ohc_2000 || BG.ohc_700) add('Ocean heat content', 'Record of the series since 1955.', ['trend', 'background'], function (w, h) { return chartOHC(BG, w, h); });
    var sea = G.sea || {};
    if (sea.dates) add('Persian Gulf, daily', fnum(sea.last_sst, 1, false) + ' °C, anomaly ' + fnum(sea.last_anom) + '.', ['regions', 'place'], function (w, h) { return chartMetric(boxMetric({ title: 'Persian Gulf', dates: sea.dates, sst: sea.sst, anom: sea.anom, analogs: sea.analogs }, false), w, h, 'Persian Gulf, daily anomaly'); });
    if (G.kuwait && G.kuwait.tmax) add('Kuwait, daily temperature', 'Last 30 days ' + fnum(G.kuwait.tmax_anom_30d, 1) + ' °C against the normal maximum.', ['regions', 'place'], function (w, h) { return chartKuwait(G.kuwait, w, h); });
    if (FO) {
      add('FAO food price index', 'Index ' + fnum(FO.index, 1, false) + ' in ' + FO.last_month + '.', ['food', 'prices'], function (w, h) { return chartFood(FO, w, h); });
      if (FO.overlay && FO.overlay.current) add('Food index since onset', 'The aggregate against past events from the onset month.', ['food', 'onset'], function (w, h) { return chartOverlay(FO.overlay, w, h); });
    }
    ((A.onset_paths || {}).items || []).slice(0, 4).forEach(function (it) {
      add(it.name + ' since onset', fnum(it.now_pct, 1) + ' % since the onset month.', ['food', 'onset'], function (w, h) { return chartOverlay({ onset: it.current.onset, current: it.current, analogs: it.analogs || {} }, w, h, { title: it.name + ' since onset', noProject: true }); });
    });
    (D.risks || []).forEach(function (r, i) {
      if (!r.metric || !r.metric.values || T2.length >= 42) return;
      if (T2.some(function (t) { return t.title === r.title; })) return;
      add(r.title, 'Level ' + r.level + ' · ' + r.horizon + '. ' + (r.plain || '').slice(0, 160), ['risk', i], function (w, h) { return chartMetric(r.metric, w, h, r.metric.name); });
    });
    return T2.slice(0, 42);
  }

  function viewOverview() {
    var D = S.D, NW = D.noaa, N = D.nino34, IRI = D.iri && !D.iri.error ? D.iri : null, A = D.air || {}, O = D.oisst || {}, SB = D.subsurface || {}, FO = D.food && !D.food.error ? D.food : null, ONI = D.oni, CORE = D.risk_core || {}, G = D.gulf || {};
    var body = stageShell('Overview: ' + D.risk_index + ' of 100, ' + (D.risks || []).length + ' risks, ' + (D.alerts || []).length + ' alerts — every tile opens its section',
      [{ label: S.full ? 'exit full screen (Esc)' : '⛶ full screen', on: !!S.full, click: function () { S.full = !S.full; render(); } }]);
    body.classList.add('scroll');
    var strip = el('div', 'ov-strip');
    var tally = (IRI || {}).class_tally || {}, live = (IRI || {}).live || {};
    var c4 = (NW.chg4w || {}).n34a, b34 = (O.boxes || {}).nino34 || {}, TAO = SB.tao || {}, WD = (D.wind || {}).era5 || {};
    var sh = (D.alerts || []).filter(function (a) { return a.level === 'SHOUT'; }).length, wt = (D.alerts || []).length - sh;
    var core = (CORE.items || []), coreNow = core.filter(function (x) { return x.year === 'now'; })[0], core97 = core.filter(function (x) { return x.year === '1997'; })[0];
    strip.appendChild(ovKpi(term('riskindex', 'risk index'), D.risk_index + '<small>of 100</small>', (D.risks || []).length + ' risks, ' + sh + ' shout · ' + wt + ' watch', arcGauge(D.risk_index, 100, 'var(--nino)'), ['trend', 'index'], null, 'risk_index'));
    strip.appendChild(ovKpi(zone('nino34') + ' weekly', fnum(NW.latest.n34a, 1) + '<small>°C</small>', '4 weeks ' + arrow(c4, 1) + ' · ' + esc(NW.date), spark({ values: NW.series.slice(-26).map(function (r) { return r.n34a; }) }, 60, 26), ['now', 'weekly'], null, 'n34_weekly'));
    if (fin(b34.last_anom)) strip.appendChild(ovKpi(zone('nino34') + ' daily box', fnum(b34.last_anom) + '<small>°C</small>', '30 days ' + arrow(b34.chg30, 2) + ' · ' + esc(b34.last_date), spark({ values: b34.anom }, 60, 26), ['ocean', 'surface'], null, 'n34_box'));
    strip.appendChild(ovKpi(term('oni', 'ONI') + ' · ' + term('roni', 'RONI'), fnum(ONI.current[ONI.last_season]) + '<small>' + esc(ONI.last_season) + '</small>', 'RONI ' + fnum((ONI.roni || {}).last) + ' — the gap is the warm background', twoBars(ONI.current[ONI.last_season] || 0, (ONI.roni || {}).last || 0, 'ONI', 'RONI', 'var(--nino)'), ['now', 'analogs'], null, 'oni'));
    if (IRI) strip.appendChild(ovKpi('models', (tally.broke || 0) + '<small>broken of ' + ((tally.ok || 0) + (tally.lag || 0) + (tally.broke || 0)) + '</small>', 'live RMS ' + fnum(liveNow(IRI, 'rms')) + ' · published ' + fnum((IRI.against_observed || {}).mean), donut([[tally.ok || 0, 'var(--nina)'], [tally.lag || 0, 'var(--lv3)'], [tally.broke || 0, 'var(--lv5)']]), ['models', 'plume'], null, 'models_broke'));
    if (A.fuel) strip.appendChild(ovKpi(term('wwv', 'fuel'), A.fuel.share_of_record + '<small>% of record</small>', (A.fuel.discharging ? 'being spent' : 'not spent yet') + ' · leads by ' + (A.fuel.lead || {}).lag + ' mo', barFill(A.fuel.share_of_record, 'var(--ochre)'), ['air', 'fuel'], null, 'wwv'));
    if (TAO.warmest) strip.appendChild(ovKpi(term('tao', 'under the surface'), fnum(TAO.warmest.value, 1) + '<small>°C at ' + TAO.warmest.depth + ' m</small>', esc(TAO.warmest.station) + ' · D20 east ' + TAO.d20_east + ' m', barFill(Math.min(100, TAO.warmest.value * 8), 'var(--nino)'), ['ocean', 'moorings'], null, 'subsurface_warmest'));
    if (WD.dates) strip.appendChild(ovKpi(term('wwb', 'wind bursts'), (WD.events || []).length + '<small>in 120 d</small>', (WD.active ? 'one under way' : 'last ' + WD.days_since_last + ' d ago') + ' · week ' + fnum(WD.mean7, 1) + ' m/s', spark({ values: WD.anom.slice(-60) }, 60, 26), ['air', 'wind'], null, 'wind_week'));
    if (FO) strip.appendChild(ovKpi(term('fao', 'food index'), fnum(FO.index, 1, false) + '<small>' + esc(FO.last_month) + '</small>', 'year ' + arrow(FO.yoy_pct, 1) + ' % · month ' + arrow(FO.mom, 1), spark({ values: FO.series.index.slice(-24) }, 60, 26), ['food', 'prices'], null, 'food_index'));
    if (coreNow && core97) strip.appendChild(ovKpi('core vs 1997', coreNow.core + '<small>vs ' + core97.core + '</small>', 'comparable rules only; by RONI 1997 is still ahead', twoBars(coreNow.core, core97.core, 'now', '1997', 'var(--nino)'), ['trend', 'index'], null, ['our core index', coreNow.date || '']));
    if (G.sea && fin(G.sea.last_sst)) strip.appendChild(ovKpi(term('gulfbox', 'the Gulf'), fnum(G.sea.last_sst, 1, false) + '<small>°C</small>', 'anomaly ' + fnum(Math.abs(G.sea.last_anom) < .005 ? 0 : G.sea.last_anom) + ' · ' + (G.sea.days_over_35 || 0) + ' d above 35', barFill((G.sea.last_sst - 20) * 100 / 16, 'var(--ochre)'), ['regions', 'place'], null, 'gulf_sst'));
    body.appendChild(strip);
    var tiles = ovTiles();
    var grid = el('div', 'ov-grid');
    tiles.forEach(function (t) {
      var d = el('div', 'ov-tile');
      d.setAttribute('data-src', JSON.stringify({ name: t.title, def: t.meaning, why: 'Click to open the section.' }));
      d.innerHTML = '<div class="ov-t">' + esc(t.title) + '</div><div class="ov-p"></div>';
      d.addEventListener('click', function (e) { if (e.target.closest('[data-pick]')) return; S.full = false; S.pick = null; if (t.go[0] === 'risk') { S.risk = t.go[1]; S.view = 'risk'; } else { S.view = t.go[0]; if (t.go[1] != null) S.sub[t.go[0]] = t.go[1]; S.risk = null; } render(); });
      grid.appendChild(d);
      t._el = d;
    });
    body.appendChild(grid);
    body.appendChild(el('div', 'cap', tiles.length + ' tiles: the same charts as on their scenes, drawn small. Point at a tile for its meaning; click to open. ' + esc((D.stamp || '').slice(0, 16)) + '.'));
    // рисуем после раскладки: у окон должны быть настоящие размеры
    function drawAll() {
      tiles.forEach(function (t) {
        var host = t._el.querySelector('.ov-p'); if (!host || !host.isConnected) return;
        var w = Math.max(160, Math.round(host.clientWidth)), h = Math.max(110, Math.round(host.clientHeight));
        /* В плитке легенда не помещается ни у одного графика: 300 пикселей ширины на
           картинку и подписи (владелец 06.09: «легенды везде сделать иконкой и открывать в
           тултипе»). Флаг включает у всех графиков одно поведение — значок вместо столбца. */
        S._tight = w < 420; S._tightW = w; S._legend = null;
        try { host.innerHTML = t.draw(w, h); } catch (err) { host.innerHTML = '<div class="note warn">' + esc(String(err.message || err)) + '</div>'; }
        /* Метка «legend» — в строке названия карточки (владелец 06.09), а не в картинке:
           там она отнимала место у самого графика. Список рядов график сложил в S._legend. */
        var head = t._el && t._el.querySelector('.ov-t');
        if (head) {
          var oldChip = head.querySelector('.ov-leg');
          if (oldChip) oldChip.remove();
          if (S._legend) {
            var chip = el('span', 'ov-leg', 'legend');
            chip.setAttribute('data-src', JSON.stringify(S._legend));
            head.appendChild(chip);
          }
        }
        S._tight = false; S._legend = null;
      });
    }
    requestAnimationFrame(drawAll);
    setTimeout(drawAll, 300);
  }

  // ---------------------------------------------------------------- News (владелец 05.09)
  var KIND_LBL = { alert: 'alert', risk: 'risk', value: 'value', verdict: 'verdict' };
  function viewNews() {
    var N = S.N || {}, D = S.D;
    var tw = N.this_week || [], nx = N.next_week || [], watch = N.watch || [];
    var body = stageShell(tw.length ? tw.length + ' things changed in the last week; ' + nx.length + ' releases ahead' : 'News: what changed, what is ahead', []);
    body.classList.add('scroll');
    if (!N.built) { body.appendChild(el('div', 'note warn', 'The news feed did not load (data/enso/news.json).')); return; }
    var wrap = el('div', 'news');
    var colA = el('div', 'news-col');
    colA.innerHTML = '<div class="chain-h">This week<span>' + esc(N.since) + ' → ' + esc(N.until) + ': every line is a value, a risk, an alert or the verdict that actually changed, with the date of the data.</span></div>' +
      (tw.length ? tw.map(function (it) {
        var go = it.go || [];
        return '<div class="news-i k-' + esc(it.kind) + '"><div class="ni-h"><span class="ni-k">' + esc(KIND_LBL[it.kind] || it.kind) + '</span><span class="ni-d">' + esc(it.date) + '</span></div>' +
          '<div class="ni-t">' + mark(it.title) + '</div>' + (it.detail ? '<div class="ni-s">' + mark(it.detail) + '</div>' : '') +
          (it.why ? '<div class="ni-w">' + mark(it.why) + '</div>' : '') +
          (go[0] === 'risk' ? '<div class="ni-go"><button type="button" class="vgo" data-view="now" data-risk="' + esc(go[1]) + '">open the risk →</button></div>'
            : (go[0] ? '<div class="ni-go">' + vLink('open the numbers', go[0], go[1]) + '</div>' : '')) + '</div>';
      }).join('') : '<div class="note">Nothing changed in the last week.</div>');
    var colB = el('div', 'news-col');
    colB.innerHTML = '<div class="chain-h">Next week<span>What is due, from each source\u2019s stated schedule; the panel is recomputed after each release worth it.</span></div>' +
      nx.map(function (c) {
        return '<div class="news-i k-cal"><div class="ni-h"><span class="ni-k">release</span><span class="ni-d">' + esc(c.next) + (c.in_days === 0 ? ' · today' : ' · in ' + c.in_days + ' d') + '</span></div>' +
          '<div class="ni-t">' + esc(c.name) + '</div><div class="ni-s">' + esc(c.src) + ' · ' + esc(c.rule) + '</div></div>';
      }).join('') +
      (watch.length ? '<div class="chain-h" style="margin-top:14px">What would change the picture<span>From the current verdict.</span></div>' +
        watch.map(function (w) { return '<div class="news-i k-watch"><div class="ni-t">' + mark(w) + '</div></div>'; }).join('') : '') +
      '<div class="cap" style="margin-top:10px">' + esc(N.update_note || '') + '</div>';
    wrap.appendChild(colA); wrap.appendChild(colB);
    body.appendChild(wrap);
    body.appendChild(el('div', 'cap', esc(N.note || '')));
  }

  // ---------------------------------------------------------------- Data chain (владелец 04.09, ночь)
  /* ПЛАНШЕТ ПОТОКОВ ДАННЫХ. Четыре колонки: источники → сборщики → что считаем сами → куда
     уходит. У источника — свежесть (ответил ли на последнем обновлении) и дата последней
     СМЕНЫ данных из журнала: видно, что обновилось, а что тянуть заново незачем. У состояния —
     дата данных, из которых оно посчитано. Рёбра — какие входы у каждого узла; клик по узлу
     подсвечивает его цепочку. Описания — в data/enso/chain-ref.json, даты — из latest.json. */
  function chainFresh(n) {
    var D = S.D, out = { dot: 'ok', date: '', note: '' };
    var stale = (n.src_keys || []).filter(function (k) { return D.sources[k] && !D.sources[k].fresh; });
    var missing = (n.src_keys || []).filter(function (k) { return !D.sources[k]; });
    if (stale.length) { out.dot = 'bad'; out.note = 'did not answer on the last update: ' + stale.join(', ') + ' — showing the last good copy'; }
    else if (n.src_keys && n.src_keys.length && missing.length === n.src_keys.length) { out.dot = 'off'; out.note = 'not part of this update'; }
    var jr = n.jkey ? jrec(n.jkey) : null, e = jr ? (jr.entries || []) : [];
    if (e.length) out.date = e[e.length - 1].d;
    var L = n.live;
    if (L === 'oisst_nino34') out.date = ((D.oisst || {}).boxes || {}).nino34 ? D.oisst.boxes.nino34.last_date : out.date;
    if (L === 'iri') out.date = (D.iri || {}).issued || out.date;
    if (L === 'tao') out.date = ((D.subsurface || {}).tao || {}).last_date || out.date;
    if (L === 'godas') out.date = ((D.subsurface || {}).godas || {}).month || out.date;
    if (L === 'wind') out.date = ((D.wind || {}).era5 || {}).last_date || out.date;
    if (L === 'kuwait') out.date = ((D.gulf || {}).kuwait || {}).last_date || out.date;
    if (n.layer === 'out') out.date = (D.stamp || '').slice(0, 10);
    if (n.layer === 'collect') out.date = (D.stamp || '').slice(0, 10);
    return out;
  }
  function viewChain() {
    var C = S.C || {}, D = S.D, nodes = C.nodes || [], layers = C.layers || [];
    var body = stageShell('The chain, end to end: ' + nodes.filter(function (n) { return n.layer === 'src'; }).length + ' sources, ' +
      nodes.filter(function (n) { return n.layer === 'collect'; }).length + ' collectors, ' + nodes.filter(function (n) { return n.layer === 'state'; }).length + ' computed states',
      [{ label: S.full ? 'exit full screen (Esc)' : '⛶ full screen', on: !!S.full, click: function () { S.full = !S.full; render(); } }]);
    /* ПОДСВЕТКА ВСЕЙ ЦЕПОЧКИ. Владелец 05.09: «нажал на одну — остаётся она и всё, что с ней
       связано». Раньше горел только соседний слой; теперь — все предки и все потомки. */
    var byId = {}; nodes.forEach(function (n) { byId[n.id] = n; });
    var litSet = null;
    if (S.pick && byId[S.pick]) {
      litSet = {};
      var stA = [S.pick];
      while (stA.length) { var idA = stA.pop(); if (litSet[idA]) continue; litSet[idA] = 1; (byId[idA].in || []).forEach(function (x) { stA.push(x); }); }
      var stD = [S.pick], seenD = {};
      while (stD.length) { var idD = stD.pop(); if (seenD[idD]) continue; seenD[idD] = 1; nodes.forEach(function (m) { if ((m.in || []).indexOf(idD) >= 0) { litSet[m.id] = 1; stD.push(m.id); } }); }
    }
    body.classList.add('scroll');
    if (!nodes.length) { body.appendChild(el('div', 'note warn', 'The chain reference did not load (data/enso/chain-ref.json).')); return; }
    if (window.matchMedia('(max-width:900px)').matches) body.appendChild(el('div', 'note', 'The diagram with its links is a desktop view; on a phone the nodes are listed layer by layer. ' + vLink('the register', 'refs', 'sources')));
    body.appendChild(el('div', 'lead', 'Point at anything: what it is, why it is here, where it comes from and when its data last changed. Click a node to light its chain; click again to release. ' +
      'The dot is the state of the source on the last update (' + esc((D.stamp || '').slice(0, 16)) + '): green answered, ochre did not answer and the last good copy is shown, grey not part of this update.'));
    var wrap = el('div', 'chain');
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'chain-edges');
    wrap.appendChild(svg);
    var cols = el('div', 'chain-cols');
    layers.forEach(function (L) {
      var col = el('div', 'chain-col');
      col.innerHTML = '<div class="chain-h">' + esc(L.title) + '<span>' + esc(L.note) + '</span></div>';
      nodes.filter(function (n) { return n.layer === L.id; }).forEach(function (n) {
        var f = chainFresh(n), lit = !!(litSet && litSet[n.id]);
        var card = el('div', 'chain-node' + (S.pick ? (lit ? ' lit' : ' dim') : '') + (S.pick === n.id ? ' on' : ''));
        card.setAttribute('data-node', n.id);
        var pay = { name: n.name, def: n.def, why: n.why + (f.note ? ' ' + f.note + '.' : ''), src: (n.sub || '') + (n.cadence ? ' · ' + n.cadence : ''), date: f.date, url: n.url };
        card.setAttribute('data-src', JSON.stringify(pay));
        card.innerHTML = '<div class="cn-h"><i class="dot ' + f.dot + '"></i><b>' + esc(n.name) + '</b></div>' +
          '<div class="cn-s">' + esc(n.sub || '') + '</div>' +
          '<div class="cn-m">' + (n.cadence ? esc(n.cadence) + ' · ' : '') + (f.date ? 'data ' + esc(f.date) : '') + (n.url ? ' · <a href="' + esc(n.url) + '" target="_blank" rel="noopener">source ↗</a>' : '') + '</div>';
        card.addEventListener('click', function (e) { if (e.target.closest('a')) return; S.pick = S.pick === n.id ? null : n.id; render(); });
        col.appendChild(card); n._el = card;
      });
      cols.appendChild(col);
    });
    wrap.appendChild(cols);
    body.appendChild(wrap);
    // рёбра — после раскладки, по реальным координатам карточек
    function drawEdges() {
      var wr = wrap.getBoundingClientRect();
      var cwid = wrap.clientWidth;
      svg.setAttribute('width', cwid); svg.setAttribute('height', wrap.scrollHeight);
      svg.setAttribute('viewBox', '0 0 ' + cwid + ' ' + wrap.scrollHeight);
      var s = '';
      nodes.forEach(function (n) {
        (n.in || []).forEach(function (src0) {
          var a = byId[src0], b = n;
          if (!a || !a._el || !b._el) return;
          var ra = a._el.getBoundingClientRect(), rb = b._el.getBoundingClientRect();
          var x1 = ra.right - wr.left + wrap.scrollLeft, y1 = ra.top + ra.height / 2 - wr.top + wrap.scrollTop;
          var x2 = rb.left - wr.left + wrap.scrollLeft, y2 = rb.top + rb.height / 2 - wr.top + wrap.scrollTop;
          var lit = !!(litSet && litSet[a.id] && litSet[b.id]);
          var mx = (x1 + x2) / 2;
          s += '<path d="M' + x1.toFixed(0) + ',' + y1.toFixed(0) + ' C' + mx.toFixed(0) + ',' + y1.toFixed(0) + ' ' + mx.toFixed(0) + ',' + y2.toFixed(0) + ' ' + x2.toFixed(0) + ',' + y2.toFixed(0) +
            '" fill="none" style="stroke:' + (lit ? 'var(--ochre)' : 'var(--soft)') + '" stroke-width="' + (lit ? 2 : 1) + '" opacity="' + (S.pick ? (lit ? .95 : .12) : .35) + '"/>';
        });
      });
      svg.innerHTML = s;
    }
    requestAnimationFrame(drawEdges);
    setTimeout(drawEdges, 250);
    body.appendChild(el('div', 'cap', vLink('the register of sources and references', 'refs', 'sources') + ' Reference: data/enso/chain-ref.json, written by hand; dates and the dots come from data/enso/latest.json and the value journal at every update. ' +
      'The climatologies (1991–2020 for every box, mooring and point; the reanalysis section by month) and the past-event series are built once and cached — an update pulls only the tails.'));
  }

  // ---------------------------------------------------------------- About
  var ABOUT = [
    ['What this is', 'A live panel on one climate event, the El Niño of 2026–27, for readers who plan against it: engineers, agronomists, importers, city services. It measures the ocean and the atmosphere every day from open sources, computes its own states and risks the same way every day, reads the forecasts of two dozen models and keeps score of them, and says in plain words what the numbers mean — with the source and the date on every number.'],
    ['Three kinds of knowledge, kept apart', 'Measured: a number from a source as it is, with its date. Computed: something we derived — an anomaly, a rank, an index, a class — with the method on the Method tab and the parameters named as parameters. Quoted: a claim from the literature or a forecast from someone else\u2019s model, shown with its author and never as our own. The panel never mixes the three; when a line is a quote it says so on the line.'],
    ['How an update works', 'One command pulls every source, keeps the raw copies, recomputes every state, compares with the previous update and with a week ago, writes the value journal and a full snapshot. A language model (DeepSeek V4 Pro) then reads a digest of the numbers and writes the verdict; a second model (Fable, Claude) reads the verdict against the same numbers and corrects it where it strays; a person looks at the result and decides whether it goes out. Nothing on this page is written by hand at update time except the reference tables, which are dated.'],
    ['What is measured here that is not measured elsewhere', 'The daily Niño boxes straight from the NOAA grid, one day behind, with our own climatologies; the water under the equator by mooring, every day, against each mooring\u2019s own record; the westerly wind bursts from daily reanalysis wind; the live-model centre and where we stand inside the season; the comparable core of the risk index for past events, and the same by RONI; the Gulf and Kuwait measured, not quoted.'],
    ['What we do not claim', 'We have no model of our own and forecast nothing. A “broken” model is one below the official value in most verified issues, not a bad model. The risk index is a construction of this page, comparable only with itself; the core and RONI are the fair comparisons across decades. Analogue paths of prices are what happened then, not what will happen. Regional impacts are typical, never guaranteed; the teleconnections for Europe and Russia are weak and the page says so on the row.'],
    ['Reading the charts', 'Every chart with more than one series distinguishes them by dash pattern, not by colour alone; the legend is clickable and lights one series. Past events are drawn on the same days of the year, dashed, in the same order everywhere: 1982, 1997, 2015, 2023, then last year in grey. Negative values on heat maps are hatched. The vertical mark on the plume shows the lived part of the season as a point and the rest as a range.'],
    ['Changelog', '2026-09-03 — first version: daily series, weekly indices, ONI, the plume, food, regions, risks, the verdict. 2026-09-04 — the value journal, the atmosphere and fuel, satellite layers, commodities by name, models by class, the live centre, the comparable core, contextual links to parsed papers. 2026-09-04, evening, after the first expert review — OISST direct with own climatologies, the moorings and the reanalysis section, daily wind and bursts, the MJO, RONI and the second scale, MEI and the Indian Ocean Dipole, the ocean heat content, the release calendar, the Regions tab with the Gulf measured, commodity paths since onset, dashed series and clickable legends everywhere, this chain and this page.']
  ];
  function viewAbout() {
    var body = stageShell('What this panel is, what it does, and how to read it', []);
    body.classList.add('scroll');
    var g = el('div', 'about');
    g.innerHTML = ABOUT.map(function (x) { return '<section><h3>' + esc(x[0]) + '</h3><p>' + mark(x[1]) + '</p></section>'; }).join('') +
      '<section><h3>Where to look</h3><p>' + vLink('the references: works, sources, literature', 'refs', 'works') + ' ' + vLink('the chain of data', 'chain') + ' ' + vLink('the method', 'how', 'method') + ' ' + vLink('the sources', 'how', 'sources') + ' ' + vLink('the release calendar', 'how', 'calendar') + ' ' + vLink('the verdict', 'verdict', 'now') + '</p></section>';
    body.appendChild(g);
  }

  // ---------------------------------------------------------------- Regions
  var IMPACT = { dry: 'drought', heat: 'heat', wet: 'wet', flood: 'floods', none: 'no signal' };
  function regionCard(body, r, RG) {
    var g = el('div', 'gloss');
    g.innerHTML = '<div class="gl-i"><b>' + esc(r.name) + '</b>' + esc(r.countries || '') + '<div class="s">food vulnerability ' + ((r.vulnerability || {}).level || '—') + ' of 5</div></div>' +
      '<div class="gl-i"><b>Food exposure</b>' + esc((r.vulnerability || {}).note || '') + ((r.vulnerability || {}).importers && r.vulnerability.importers.length ? '<div class="s">net importers: ' + esc(r.vulnerability.importers.join(', ')) + '</div>' : '') + '</div>' +
      (RG.seasons || []).map(function (s2) {
        var x = (r.seasons || {})[s2] || {};
        return '<div class="gl-i"><b>' + esc(s2) + ' · ' + esc(IMPACT[x.impact] || 'no signal') + (x.impact && x.impact !== 'none' && x.strength ? ' (' + esc(x.strength) + ')' : '') + '</b>' + esc(x.note || 'No consistent signal for this season.') + '</div>';
      }).join('') +
      (r.actions && r.actions.length ? '<div class="gl-i"><b>What to do</b><ul>' + r.actions.map(function (a) { return '<li>' + esc(a) + '</li>'; }).join('') + '</ul></div>' : '') +
      '<div class="gl-i"><b>Sources</b><div class="s">' + srcHtml((r.sources || []).join(' · ')) + (RG.as_of ? '<div>' + esc(RG.as_of) + '</div>' : '') + '</div></div>';
    body.appendChild(g);
    var lk = linksHtml('region:' + r.id, true);
    if (lk) body.appendChild(el('div', 'links-box', lk));
  }

  function viewRegions() {
    var D = S.D, RG = D.regions && !D.regions.error ? D.regions : null, P = S.P, k = sub('regions', 'table');
    var scen = S.scenario || 'strong';
    var items = RG ? RG.items.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }) : [];
    var rid = S.region || 'gulf_arabia';
    var r = items.filter(function (x) { return x.id === rid; })[0] || items[0];
    var G = D.gulf, measured = !!(r && r.id === 'gulf_arabia' && G && !G.error), gk = sub('gulf', 'sea');
    var high = RG ? RG.items.filter(function (x) { return x.levels[scen] >= 4; }).length : 0;
    var head = k === 'table' ? (RG ? high + ' of ' + RG.items.length + ' regions at level 4–5 under the “' + scen + '” scenario' : 'Regions')
      : (measured && gk !== 'ref' ? gulfHead(G, gk) : (r ? r.name + ': level ' + r.levels[scen] + ' of 5 under the “' + scen + '” scenario' : 'By region'));
    var body = stageShell(head, [segBtn('regions', 'table', 'Overview', 'table'), segBtn('regions', 'place', 'By region', 'table')]);
    if (k === 'table') {
      if (!RG) { body.appendChild(el('div', 'note warn', 'The regions block did not load.')); return; }
      regionsTable(body, RG, scen, P);
      return;
    }
    var row = el('div', 'seg sub'), sel = el('select', 'rsel');
    items.forEach(function (x) {
      var o = document.createElement('option'); o.value = x.id;
      o.textContent = x.name + (x.id === 'gulf_arabia' ? ' · measured here' : '') + ' · level ' + x.levels[scen];
      if (r && x.id === r.id) o.selected = true;
      sel.appendChild(o);
    });
    sel.onchange = function () { S.region = sel.value; S.sub.gulf = null; render(); };
    row.appendChild(sel);
    body.appendChild(row);
    if (!r) { body.appendChild(el('div', 'note warn', 'No regions loaded.')); return; }
    body.classList.toggle('scroll', !measured || ['winter', 'food', 'ref'].indexOf(gk) >= 0);
    if (measured) {
      gulfBody(body, gk, G);
      if (gk !== 'ref') return;
    } else {
      body.appendChild(el('div', 'note', 'No local measurements for this region yet — below is the reference: typical impacts by season, food exposure and the sources. The Gulf is the first region with measured series (sea, weather, imports); others follow as sources are found.'));
    }
    regionCard(body, r, RG);
  }

  // ---------------------------------------------------------------- render
  /* АДРЕС СЦЕНЫ. Ссылка вида enso.html#ocean/moorings открывает нужную вкладку и подвкладку:
     так вкладку можно послать письмом, а панель — снять снимком без кликов. Адрес
     обновляется при каждой перерисовке и никогда не перезагружает страницу. */
  function readHash() {
    var h = (location.hash || '').replace(/^#/, '');
    if (!h) return;
    var parts = h.split('/');
    if (parts[0] === 'gulf') {                   // старый адрес вкладки Kuwait · Gulf
      S.view = 'regions'; S.sub.regions = 'place'; S.region = 'gulf_arabia';
      if (parts[1]) S.sub.gulf = parts[1];
      return;
    }
    if (T.tabs[parts[0]] || parts[0] === 'state' || parts[0] === 'risks') {
      S.view = parts[0];
      if (parts[1]) S.sub[parts[0]] = parts[1];
      if (parts[0] === 'regions' && parts[2]) S.region = parts[2];
    }
  }
  function writeHash() {
    if (S.view === 'risk') return;
    var h = '#' + S.view + (S.sub[S.view] ? '/' + S.sub[S.view] : '') +
      (S.view === 'regions' && S.sub.regions === 'place' && S.region ? '/' + S.region : '');
    if (location.hash !== h) { try { history.replaceState(null, '', h); } catch (e) { /* file: без истории */ } }
  }
  function render() {
    writeHash();
    /* ВЫБОР В ЛЕГЕНДЕ ЖИВЁТ ТОЛЬКО НА СВОЕЙ СЦЕНЕ. Владелец 05.09: «походил, вернулся на
       Against analogues — всё блёклое, не могу вернуть яркость». Уход со сцены снимает выбор. */
    var scene = S.view + '/' + (S.sub[S.view] || '');
    if (S._scene !== scene) { S.pick = (scene === 'models/plume' || scene === 'models/stack') ? 'ok' : null; S._scene = scene; }
    if (S.view === 'overview' && S.full == null) S.full = true;   // обзор открывается сразу на весь экран
    var mapScene = S.view === 'now' && (S.sub.now || 'analogs') === 'map';
    if (S.view !== 'overview' && S.view !== 'chain' && !mapScene) S.full = null;
    $('stage').classList.toggle('full', !!(S.full && (S.view === 'chain' || S.view === 'overview' || mapScene)));
    var narrow = window.matchMedia('(max-width:900px)').matches;
    // База сравнения выбирается режимом, но код блоков читает S.P — подменяем на время отрисовки.
    S.P = S.delta ? baseline() : (S.D || {}).prev || null;
    buildTabs();
    /* Прокрутка колонок переживает перерисовку. Первая попытка запоминала scrollTop у
       самой колонки — и не работала: колонка не прокручивается, прокручивается тело
       плитки внутри неё (.tile > .tb), а его перерисовка создаёт заново. Запоминаем по
       телу плитки и возвращаем туда же (владелец 04.09: «я выбираю — она прокручивается
       вверх», дважды). */
    function railTop(id) { var b = $(id) && $(id).querySelector('.tb'); return b ? b.scrollTop : 0; }
    function railTopSet(id, v) { var b = $(id) && $(id).querySelector('.tb'); if (b && v) b.scrollTop = v; }
    var keepL = railTop('railL'), keepR = railTop('railR');
    railState(); railRisks();
    railTopSet('railL', keepL); railTopSet('railR', keepR);
    var stage = $('stage'), L = $('railL'), R = $('railR');
    L.classList.toggle('show', narrow && S.view === 'state');
    R.classList.toggle('show', narrow && (S.view === 'risks' || S.view === 'risk'));
    stage.classList.toggle('hide', narrow && (S.view === 'state' || S.view === 'risks'));
    if (narrow && (S.view === 'state' || S.view === 'risks')) { S.draw = null; S.plotEl = null; return; }
    if (S.view === 'risk') viewRisk();
    else if (S.view === 'verdict') viewVerdict();
    else if (S.view === 'models') viewModels();
    else if (S.view === 'air') viewAir();
    else if (S.view === 'ocean') viewOcean();
    else if (S.view === 'regions' || S.view === 'gulf') viewRegions();
    else if (S.view === 'chain') viewChain();
    else if (S.view === 'news') viewNews();
    else if (S.view === 'overview') viewOverview();
    else if (S.view === 'refs') viewRefs();
    else if (S.view === 'about') viewAbout();
    else if (S.view === 'trend') viewTrend();
    else if (S.view === 'food') viewFood();
    else if (S.view === 'how') viewHow();
    else viewNow();
    // Сцена собрана целиком — только теперь у рамки графика окончательная высота.
    redrawPlot();
    requestAnimationFrame(redrawPlot);
  }
  window.B42EnsoRedraw = function () { redrawPlot(); };
  /* ВСЕ КАРТОЧКИ СЛЕВА ВЕДУТ НА СВОЮ СЦЕНУ. Владелец 04.09: «слева карточки state не
     переводят на наши вкладки?». Каждая карточка — утверждение, и у каждого есть место,
     где лежат его числа: состояние ведёт к рядам, тревога — к своему разделу, модели — к
     разбору поломок, вердикт — на свою вкладку. Обработчик один на все, чтобы новая
     карточка получала переход одной строкой разметки. */
  document.addEventListener('click', function (e) {
    var g = e.target.closest && e.target.closest('.cgo[data-go]');
    if (!g) return;
    e.stopPropagation();
    S.view = g.getAttribute('data-go');
    var sb = g.getAttribute('data-gosub');
    if (sb) S.sub[S.view] = sb;
    S.risk = null;
    render();
  });
  /* Кнопки перехода из вердикта и из левой колонки: одна точка входа на все сцены. */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.vgo');
    if (!b) return;
    e.stopPropagation();
    var rid = b.getAttribute('data-risk');
    if (rid) {
      var idx = (S.D.risks || []).map(function (r) { return r.id; }).indexOf(rid);
      if (idx >= 0) { S.risk = idx; S.view = 'risk'; render(); return; }
    }
    S.view = b.getAttribute('data-view') || 'now';
    var sb = b.getAttribute('data-sub');
    if (sb) S.sub[S.view] = sb;
    S.risk = null;
    render();
  });

  // ---------------------------------------------------------------- dock + карточка у курсора
  function initDock() {
    var tip = $('tip');
    function payloadOf(target) {
      var k = target.getAttribute('data-term');
      if (k && S.G[k]) { var g = S.G[k]; return { name: g.name, def: g.def, why: g.why, src: g.src, lk: 'term:' + k }; }
      if (target.getAttribute('data-src')) { try { return JSON.parse(target.getAttribute('data-src')); } catch (e) { return null; } }
      return null;
    }
    function fill(p) {
      return '<b>' + esc(p.name || '') + '</b>' + (p.html ? p.html : esc(p.def || '')) + (p.why ? ' ' + esc(p.why) : '') +
        (p.url ? ' <a href="' + esc(p.url) + '" target="_blank" rel="noopener">source ↗</a>' : '') +
        (p.lk && linksFor(p.lk).length ? ' <button type="button" class="jh tip-lk" data-lk="' + esc(p.lk) + '">' + linksFor(p.lk).length + ' work' + (linksFor(p.lk).length > 1 ? 's' : '') + ' →</button>' : '') +
        (p.src || p.date ? '<span class="s">' + srcHtml(p.src) + (p.date ? '<div>' + esc(p.date) + '</div>' : '') + '</span>' : '');
    }
    function place(e) {
      var pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
      var x = e.clientX + pad, y = e.clientY + pad;
      // карточка от строки источников в шапке встаёт ПОД верхней полосой, чтобы не накрывать вкладки
      if (S.tipAnchor && S.tipAnchor.closest && S.tipAnchor.closest('#pmeta')) {
        var tb = document.querySelector('.top-bar');
        if (tb) y = tb.getBoundingClientRect().bottom + 6;
      }
      if (x + w > window.innerWidth - 8) x = e.clientX - w - pad;
      if (y + h > window.innerHeight - 8) y = e.clientY - h - pad;
      tip.style.left = Math.max(6, x) + 'px';
      tip.style.top = Math.max(6, y) + 'px';
    }
    function closeBtn() { return '<button type="button" class="x" title="close">×</button>'; }
    /* ПОДВАЛ БОЛЬШЕ НЕ ПОВТОРЯЕТ ПОДСКАЗКУ. Владелец 04.09: «тултип внизу не надо
       дублировать, в подвале не надо ничего писать кроме обновления — туда смотреть тяжело».
       Взгляд и правда не должен прыгать вниз через весь экран за тем, что уже написано у
       курсора. В подвале остались только даты источников. */
    function show(target, e) {
      var p = payloadOf(target);
      if (!p) return;
      S.tipAnchor = target;
      tip.innerHTML = closeBtn() + fill(p);
      tip.classList.add('on');
      if (e) place(e);
    }
    /* ДО КАРТОЧКИ НАДО ДОХОДИТЬ. Владелец 04.09: «навёл — появилась, ушёл — закрылась,
       а в ней ссылки, я не могу ничего выбрать». Три правила лечат это разом:
       ухожу с подчёркнутого слова — карточка ждёт треть секунды, и если курсор пошёл в
       НЕЁ, она остаётся; за курсором она едет только пока он на самом слове; крестик,
       клик по слову и Esc — три способа закрыть. Подвал внизу тоже больше не стирается
       на выходе: там те же ссылки, и с них надо успевать уйти на статью. */
    /* ПОЧЕМУ КАРТОЧКУ ВСЁ РАВНО БЫЛО НЕ ПОЙМАТЬ (владелец 04.09: «неуловимы совсем»).
       Она ехала за курсором: пока курсор на подчёркнутом слове, mousemove переставлял её
       на курсор + 14 пикселей. То есть человек двигался к карточке, а карточка отодвигалась
       ровно на ту же величину — догнать нельзя в принципе. Теперь ставим её ОДИН РАЗ, при
       появлении, и больше не трогаем; уход прощаем целую секунду; а если на слове задержаться
       на полсекунды, карточка прилипает сама — как и просил владелец: «долго подержал —
       осталась». Прилипшую закрывают крестик, Esc, повторный клик или клик мимо. */
    var hideT = null, pinT = null, overTip = false;
    function hide() { clearTimeout(hideT); clearTimeout(pinT); S.pinned = null; tip.classList.remove('on', 'pin'); }
    function laterHide() {
      clearTimeout(hideT); clearTimeout(pinT);
      hideT = setTimeout(function () { if (!overTip && !S.pinned) hide(); }, 1500);
    }
    function find(e) { return e.target.closest && e.target.closest('[data-term],[data-src]'); }
    /* Пришёл ли клик из самой карточки. Проверяем и путь события: содержимое карточки
       подменяется на лету («N works» → список работ), и к моменту всплытия кликнутая
       кнопка уже не в документе. */
    function inTip(e) {
      if (tip.contains(e.target)) return true;
      var path = e.composedPath ? e.composedPath() : null;
      return !!(path && path.indexOf(tip) >= 0);
    }
    tip.addEventListener('mouseenter', function () {
      // курсор дошёл до карточки — значит она нужна: прикалываем, чтобы не исчезла из-под рук
      overTip = true; clearTimeout(hideT); clearTimeout(pinT);
      if (!S.pinned) { S.pinned = true; tip.classList.add('pin'); }
    });
    tip.addEventListener('mouseleave', function () { overTip = false; laterHide(); });
    tip.addEventListener('click', function (e) {
      if (e.target.closest('.x')) { S.pinned = null; hide(); return; }
      // клик по пустому месту карточки закрывает её: иначе она стоит и мешает целиться
      /* И ПРОХОДИТ НАСКВОЗЬ. Владелец 04.09 (вечер): «Kuwait · Gulf не нажимается». Карточка из
         шапки (даты источников) всплывала ровно над строкой вкладок и, приколовшись, съедала
         первый клик по вкладке — закрывалась, а вкладка не открывалась. Теперь клик по пустому
         месту карточки закрывает её И нажимает то, что лежало под ней: карточка больше не
         крадёт клики ни у вкладок, ни у кнопок. */
      if (!e.target.closest('a') && !e.target.closest('button')) {
        S.pinned = null; hide();
        tip.style.pointerEvents = 'none';
        var under = document.elementFromPoint(e.clientX, e.clientY);
        tip.style.pointerEvents = '';
        if (under && under !== tip && !tip.contains(under)) {
          var ctl = under.closest && under.closest('button, .cgo, .vgo, .risk, [data-go]');
          if (ctl) ctl.click();
        }
        return;
      }
      var m = e.target.closest('[data-histall]');
      if (m) { tip.innerHTML = closeBtn() + histHtml(m.getAttribute('data-histall'), true); }
      // «N works» внутри подсказки: та же карточка, теперь со списком работ (владелец 05.09)
      var lk = e.target.closest('[data-lk]');
      if (lk) { S.pinned = true; tip.classList.add('pin'); tip.innerHTML = closeBtn() + '<b>What the research says about this</b>' + worksHtml(linksFor(lk.getAttribute('data-lk'))); }
    });
    /* КАРТОЧКА НЕ ДОЛЖНА ОТБИРАТЬ КЛИКИ У КНОПОК. Владелец 04.09: «вкладки fuel и layers не
       отвечают», «by commodity не работает». Кнопки были в порядке — их перехватывала
       прилипшая карточка: она всплывает у курсора и накрывает то место, куда человек
       целится. Три правила: прилипаем только после ДОЛГОЙ задержки (1.2 с, а не полсекунды),
       никогда не прилипаем, пока курсор над органом управления (вкладка, сегмент, кнопка),
       и клик по пустому месту самой карточки её закрывает. */
    /* ОДИНАКОВОЕ ПОВЕДЕНИЕ У ВСЕХ ПОДСКАЗОК. Владелец 04.09: «почему некоторые тултипы
       нормально висят при наведении, а другие пропадают — например у риск-индекса, это
       плохо». Разница была не в подсказках, а в пороге: над органами управления карточка не
       прилипала вовсе, а в остальных местах — только после долгих 1.2 секунды. Кто задержался
       — у того висит, кто нет — у того исчезает; со стороны это выглядит как случайность.
       Теперь правило одно на всех: полсекунды задержки — и карточка прилипла; довёл до неё
       курсор — тоже прилипла. Уход прощается полторы секунды. Клики она больше не крадёт по
       другой причине: клик по её пустому месту закрывает её, а не проваливается внутрь. */
    /* ПОДСКАЗКА ОТВЕЧАЕТ ВСЕГДА. Владелец 04.09: «то он не появляется, то надо кликнуть».
       Причина была в прилипании: приколотая карточка глушила наведение на ВСЕ остальные
       слова — пока не щёлкнешь мимо, новая не показывалась. Теперь наведение на другое
       слово просто меняет содержимое карточки; приколотость означает лишь «не исчезай
       сама», а не «не слушай больше никого». Внутри самой карточки наведение игнорируем,
       иначе она перебивала бы себя, пока читаешь. */
    document.addEventListener('mouseover', function (e) {
      if (overTip) return;
      var x = find(e);
      if (!x || x === S.pinned) return;
      show(x, e);
      if (S.pinned) { S.pinned = x; return; }        // уже приколота — просто меняем содержимое
      clearTimeout(pinT);
      if (x.closest('#pmeta')) return;              // шапка: только пока курсор на слове, без прикалывания
      pinT = setTimeout(function () {
        if (tip.classList.contains('on')) { S.pinned = x; tip.classList.add('pin'); }
      }, 600);
    });
    document.addEventListener('mouseout', function (e) {
      var f = find(e);
      if (!f) return;
      if (f.closest('#pmeta') && !S.pinned) { clearTimeout(hideT); hideT = setTimeout(function () { if (!overTip) hide(); }, 300); }
      else laterHide();
    });
    document.addEventListener('click', function (e) {
      var h = e.target.closest && e.target.closest('[data-hist]');
      if (h) {                                   // кнопка «history» на кирпиче
        S.pinned = h;
        tip.innerHTML = closeBtn() + histHtml(h.getAttribute('data-hist'), false);
        tip.classList.add('on', 'pin');
        place(e);
        return;
      }
      var x = find(e);
      if (x) { S.pinned = (S.pinned === x ? null : x); if (S.pinned) { show(x, e); tip.classList.add('pin'); } else hide(); return; }
      /* КЛИК ВНУТРИ КАРТОЧКИ НЕ ЗАКРЫВАЕТ ЕЁ — ДАЖЕ ЕСЛИ КНОПКИ УЖЕ НЕТ. Владелец 06.09:
         «на ONI в подсказке указано 1 works, но кнопка ничего не производит». Кнопка
         работала: обработчик карточки успевал подставить список работ. Следом срабатывал
         этот, общий, и не находил кликнутый узел в документе — потому что сам список его
         только что и заменил. Отвязанный узел «не внутри #tip», карточку закрывало,
         и со стороны это выглядело как мёртвая кнопка. Путь события помнит, откуда клик
         пришёл, и после подмены разметки. */
      if (S.pinned && !inTip(e)) { S.pinned = null; hide(); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { S.pinned = null; hide(); if (S.full) { S.full = false; render(); } } });
    hide();
  }

  // ---------------------------------------------------------------- go
  function get(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(u + ': ' + r.status); return r.json(); }); }
  Promise.all([get('/data/enso/latest.json'), get('/data/enso/glossary.json').catch(function () { return {}; }),
    get('/data/enso/history.json').catch(function () { return []; }),
    get('/data/enso/models-ref.json').catch(function () { return {}; }),
    get('/data/enso/links.json').catch(function () { return {}; }),
    get('/data/enso/journal.json').catch(function () { return {}; }),
    get('/data/enso/chain-ref.json').catch(function () { return {}; }),
    get('/data/enso/news.json').catch(function () { return {}; })])
    .then(function (r) {
      S.D = r[0]; S.G = (r[1] && r[1].en) || {}; S.H = r[2] || []; S.P = r[0].prev || null;
      S.M = r[3] || {}; S.L = r[4] || {}; S.J = r[5] || {}; S.C = r[6] || {}; S.N = r[7] || {};
      var db = $('deltaBtn');
      if (db) db.onclick = function () {
        S.delta = S.delta === '' ? 'update' : (S.delta === 'update' ? 'week' : '');
        render();
      };
      readHash();
      buildMeta(); initDock(); render();
      window.addEventListener('hashchange', function () { readHash(); render(); });
      var ro = new ResizeObserver(function () { redrawPlot(); });
      ro.observe($('stage'));
      var t = null;
      window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(render, 150); });
    })
    .catch(function (e) { $('stage').innerHTML = '<div class="e-empty">The data did not load: ' + esc(e.message) + '</div>'; });
})();
