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
    tabs: { verdict: 'Verdict', overview: 'Overview', news: 'News', research: 'Research', mentions: 'Mentions', now: 'Where we are', ocean: 'Ocean', radiance: 'Satellite raw', models: 'Models', air: 'Air & fuel', trend: 'Dynamics', regions: 'Regions', food: 'Food', planet: 'Long record', how: 'Method', refs: 'References', chain: 'Data chain', ops: 'Ops', about: 'About' },
    tabHelp: {
      verdict: 'What the machine makes of it today: the verdict written from the numbers on this page, the turning point, the outlook, what to watch, the caveats.',
      overview: 'One screen with everything: a strip of key indicators and a mosaic of every chart, each a door into its section.',
      news: 'What changed in the last week — values, risks, alerts, the verdict — and what is due next week.',
      mentions: 'Who is talking about El Niño: news feeds in nine languages, Wikipedia readers, the forecast centres. Talk about the event, not a measurement of it.',
      now: 'Where the event stands: the daily and weekly Niño indices against the strongest past events, the map of the Pacific, ONI and RONI.',
      ocean: 'The ocean itself: daily boxes straight from the NOAA grid, the water under the equator by mooring, the reanalysis section.',
      models: 'The forecast models: the plume, three issues stacked, the scoreboard of who keeps up, how they break, how they revise.',
      air: 'The atmosphere and the fuel: the coupling, the warm water volume, the satellite floors, daily wind and bursts, the MJO, the other indices.',
      radiance: 'Measured by us from raw NOAA-21 granules (CrIS infrared, ATMS microwave): deep convection and the raw Walker contrast over the Pacific boxes, temperature layers through cloud, plus earthquakes and the sun from the same collector.',
      trend: 'Dynamics: the daily series with records and the 14-day analogue forecast, our own index against past events, the background of ocean heat.',
      regions: 'What it means where you live: 17 regions by season and scenario; the Gulf measured directly.',
      food: 'Food: the FAO index, its path since the onset against past events, and the commodities by name.',
      planet: 'The long record: greenhouse gases, sea ice, global temperature and sea level over the whole history of measurement, every year as a line. The background the event runs on, not the event.',
      how: 'Glossary, method and parameters, sources with their freshness, the release calendar, what changed.',
      chain: 'The chain of data end to end: sources, collectors, computed states, outputs — with the freshness of every piece.',
      research: 'Ask in your own words; the board on the left fills with the indicators, concepts, panel scenes and works the conversation touches, and keeps a summary you can verify and save (prototype).',
      refs: 'One register of everything this panel rests on: the papers we parsed and attached, the data sources, the literature quoted — each with a link and where it is used.',
      about: 'What this panel is, what it does and does not claim, and how to read it.',
      ops: 'Runs and sources: every run with its start, duration and outcome; every source with its date range, last update and errors; the fresh layer and its triggers.',
      state: 'The state column: the risk index, the key numbers and the alerts.',
      risks: 'The board of risks with their levels, horizons and series.'
    },
    subHelp: {
      'verdict/now': 'Today\'s verdict.', 'verdict/history': 'Every verdict that actually changed, in order.',
      'now/analogs': 'Daily Niño 3.4 this year against the four strongest past events on the same days.', 'now/map': 'The four Niño boxes on the map, this week against the same week of a past event.',
      'now/weekly': 'The four weekly indices over the last weeks, with the same weeks of past events beside them.', 'now/weekly_a': 'One weekly index against the strongest events on the same calendar.',
      'ocean/surface': 'Daily box means from the NOAA grid, one day behind, with own climatologies.', 'ocean/hovmoller': 'How the heat moves: the subsurface anomaly along the equator month by month, this event beside a past one.', 'mentions/attention': 'How much the world talks about it: articles per day, Wikipedia views, share of world news.', 'mentions/articles': 'Latest headlines in nine languages, with the publisher.', 'mentions/official': 'What the forecast centres publish.', 'ocean/moorings': 'Temperature by depth under the equator, mooring by mooring, every day.', 'ocean/section': 'The reanalysis section along the equator, monthly.',
      'models/plume': 'All models\' seasonal forecasts, the live-model centre, where we stand in the season.', 'models/stack': 'The last three issues, one under the other, against the same reality.', 'models/scoreboard': 'Each model against the official value it forecast.', 'models/breakdown': 'How many models fell below reality, issue by issue; the chronic ones.', 'models/revisions': 'How each model moved its peak between issues.',
      'air/coupling': 'The three atmospheric signs that the ocean and the air are coupled.', 'air/fuel': 'The warm water volume under the equator: the fuel gauge and its lead.', 'air/layers': 'The four satellite floors of the atmosphere and their delay.', 'air/wind': 'Daily zonal wind over the western Pacific and the westerly bursts.', 'air/mjo': 'The Madden–Julian Oscillation: phase and amplitude.', 'air/indices': 'MEI, the Indian Ocean Dipole and RONI next to our coupling score.',
      'trend/sst_nino34': 'Niño 3.4 daily: 400 days, the band of all years, the 14-day forecast, where past events went from here.', 'trend/sst_world': 'The world ocean, daily.', 'trend/t2_world': 'Land and ocean, daily.', 'trend/index': 'Our risk index by update, and the comparable core against past events.', 'trend/months': 'Thirteen months of the three series with their ranks.', 'trend/background': 'Ocean heat content and the energy imbalance: the state of the whole system.',
      'regions/table': 'Every region by season and scenario, with food vulnerability and what to do.', 'regions/place': 'One region at a time; the Gulf with its own measurements.',
      'food/prices': 'The FAO index and its five groups.', 'food/onset': 'The index, or one commodity, as a percentage of the onset month, against past events.', 'food/goods': 'Twelve commodities by name: price, month, year, since the onset.', 'food/abs': 'One commodity, five years, dollars per tonne; the start of the event marked.', 'ocean/motion': 'The reanalysis section as a film: one frame per month, a past event beside it.', 'radiance/convection': 'Share of satellite footprints colder than 235 K: deep convection over Niño 3.4 and the warm pool, this year against 2023–2025.', 'radiance/walker': 'Brightness-temperature contrast east minus west: the Walker circulation read raw; a fall to zero means the convection moved east.', 'radiance/clouds': 'Each scene sorted by the window brightness temperature: deep, mid, low cloud and clear sky, shares per day; the day-time cloud share is the albedo proxy.', 'radiance/greenhouse': 'How much the atmosphere closes the 11 µm window: G on all scenes (follows cloud) and G_clear on the least cloudy scenes (the water-vapour greenhouse proxy), with the p90/p99 caveat.', 'radiance/profile': 'Temperature layers: infrared (blind under cloud) and microwave (through cloud), the last 14 days against each analogue year.', 'radiance/cross': 'Two independent satellites, NOAA-21 CrIS and Aqua AIRS, against each other: the 2026 shift of convection and of the atmospheric layers on both, and how closely they agree day by day.', 'radiance/seismic': 'Earthquakes by Pacific-rim zone with aftershocks separated, and solar activity, from the same collector; side series, not El Niño physics.', 'models/board': 'Every model of the plume as a card: latest forecast, class, how far below reality.', 'models/revision': 'How each centre revised its forecast issue after issue.', 'refs/works': 'Our parsed arXiv works attached to the claims of this panel, with the reason for each link.', 'refs/sources': 'Every data source with its address, cadence and last date.', 'refs/literature': 'Literature and reports quoted on the panel, not measured by us.', 'refs/concepts': 'The concept register attached to every anchor of the panel: risks, alerts, blocks, regions and glossary terms, each with its nearest concepts and a link to the graph on that set.', 'refs/neighbours': 'Kindred projects: who else shows the planet on a globe or a map, with what data and under what licence, and what we can take from each.', 'trend/rain': 'Rain by region (ERA5 box sums against the normal and against every year since 1981) and for the whole planet (GPCP monthly).', 'trend/spectral': 'A line at 2–7 days appearing in any daily series over the last 30 days: the owner’s hypothesis of a comb before a spontaneous transition, watched, not assumed.',
      'planet/gases': 'CO₂, CH₄ and N₂O since the start of measurement, with the annual growth of CO₂.', 'planet/ice': 'Arctic and Antarctic sea ice extent, every year as a line against the 1981–2010 median.', 'planet/temperature': 'Land+ocean and ocean daily temperature every year since 1940 and 1981; global annual means since 1850.', 'planet/sea': 'Global mean sea level from satellites since 1993.',
      'how/glossary': 'Every underlined term explained.', 'how/method': 'How things are computed, and which numbers are parameters.', 'how/sources': 'Every source, whether it answered, and when its data last changed.', 'how/calendar': 'When each source publishes next.', 'how/changed': 'What changed since the previous update.',
      'ops/runs': 'Every run on record: when, what kind, how long, how it ended.', 'ops/sources': 'Every source: date range held, last update, answered or stale, errors.', 'ops/fresh': 'Fresh data since the last assessment and the triggers that decide whether it deserves one.'
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
    legOpen: false,         // легенда свёрнута по умолчанию везде (владелец 08.09); кнопка legend в строке заголовка
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
  /* ДАТА ЧЕЛОВЕКУ (владелец 07.09: «YYYY-MM-DD читается плохо, лучше Jul 26»): «Sep 7», год
     дописывается только если он не тот, в котором живёт панель; полная дата — в подсказке. */
  var MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function dt(v) {
    var t = String(v == null ? '' : v), m = t.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?/);
    if (!m) return esc(t);
    var y = +m[1], mo = +m[2], d = m[3] ? +m[3] : null, cy = +String((S.D || {}).stamp || '').slice(0, 4) || new Date().getFullYear();
    return '<span class="dt" title="' + esc(t) + '">' + MON3[mo - 1] + (d ? ' ' + d : '') + (y !== cy ? " '" + String(y).slice(2) : '') + '</span>';
  }
  function term(key, text) { return '<span data-term="' + esc(key) + '">' + esc(text) + '</span>'; }
  /* АББРЕВИАТУРА В РАМКЕ (владелец 07.09): как зоны, но другим цветом; подсказка из словаря. */
  function ab(key, text) { return '<span class="zn ab" data-term="' + esc(key) + '">' + esc(text) + '</span>'; }
  /* ДИАПАЗОН В СКОБКАХ (владелец 07.09): «[2026-08-06 … 2026-09-04]» вместо «to …; 30 days». */
  function span(to, days) { return '<span class="mono">[' + dt(addDays(to, -(days - 1))) + ' … ' + dt(to) + ']</span>'; }
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
  var SRC_RX = /((?:https?:\/\/)?(?:[a-z0-9-]+\.)+(?:gov|org|edu|int|com|net|academy|info|au|uk|eu|ae|sa|pe)(?:\/[^\s,;)]*)?)/i;
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
    return '<span class="' + upDown(c) + '"' + (c === 0 ? ' title="unchanged since the previous update"' : '') + '>' + (c === 0 ? '±0' : fnum(c, d == null ? 2 : d)) + '</span>';
  }

  // ---------------------------------------------------------------- svg helpers
  /* ЗАГОЛОВОК ПО ШИРИНЕ. Текст в SVG не переносится и не обрезается сам: на телефоне
     подписи графиков уезжали за правый край. Считаем, сколько знаков влезает при нашем
     моноширинном кегле, и режем по слову с многоточием. */
  /* РАННЕЙ ОБРЕЗКИ БОЛЬШЕ НЕТ (владелец 07.09: «надписи никогда не обрываются»). Оценка по
     числу знаков врала — у одного кегля буквы разной ширины, и заголовок то резался зря, то
     всё равно уезжал. Теперь текст отдаётся целиком, а по месту его меряет и ужимает
     fitSvgTitles() уже в документе. Крайний предохранитель — совсем немыслимая длина. */
  function fitText(text, w, px) {
    if (!text) return '';
    if (text.length <= 400) return text;
    return text.slice(0, 399) + '…';
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
  var YEAR_DASH = { '1982': '2 3', '1997': '', '2015': '7 3', '2023': '2 2 7 2' };   // год читается штрихом, не только цветом
  function yearDash(y) { return YEAR_DASH[y] != null ? YEAR_DASH[y] : dashOf(parseInt(y, 10) % 4); }

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

  /* ЛЕГЕНДА ОТКРЫВАЕТСЯ ПОД СВОЕЙ КНОПКОЙ (владелец 07.09: «легенда должна открываться под
     кнопкой легенда, и кнопка не наезжать на текст описания»). Раньше здесь рисовался список
     прямо в поле графика слева, а кнопка стояла справа — открывалось не там, где нажимали.
     Теперь путь один на все графики: та же накладная панель, что у legend(), правым верхним
     углом под кнопкой. Место под кнопку заголовку освобождает fitSvgTitles(). */
  function legendAt(items, x, y) {
    return legend(items, S._chartW || 600, 0, 1, (y == null ? 20 : y) + 2);
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
    /* Начинаем с первой линии ВНУТРИ поля: floor давал линию ниже минимума, её подпись
       печаталась под картинкой и обрезалась (владелец 06.09: «не видно нижнюю шкалу»). */
    var s = '', g = Math.ceil(vmin / step) * step, guard = 0;
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
  /* Колонки под легенду больше нет. Владелец 06.09: «график на всю ширину, а легенда
     справа вверху, выезжающая». Возвращаем только запас, чтобы подпись последнего значения
     не упиралась в край; сама легенда ложится поверх поля (см. legend()). */
  /* ХВОСТ СВЕЖИХ ДНЕЙ (владелец 06.09): точки после разобранной даты, в днях от неё. Только когда
     свежий слой считан против ЭТОГО разбора; для ветра база — последний день ERA5 в разборе. */
  function freshTail(key) {
    var D = S.D || {}, F = S.F || {};
    if (!key || !F.stamp || F.assessed_stamp !== D.stamp) return [];
    var sr = (F.series || {})[key];
    if (!sr || !(sr.tail || []).length) return [];
    var base = key === 'wind' ? (((D.wind || {}).era5 || {}).last_date) : ((D.watch && D.watch[key]) ? D.watch[key].last_date : null);
    base = base || sr.assessed_last_date;
    if (!base) return [];
    var t0 = Date.parse(base + 'T00:00:00Z');
    return sr.tail.map(function (p) { return [Math.round((Date.parse(p[0] + 'T00:00:00Z') - t0) / 86400000), p[1]]; }).filter(function (p) { return p[0] > 0 && fin(p[1]); });
  }
  function freshDot(x, y, r) { return '<circle class="fresh-dot" cx="' + (+x).toFixed(1) + '" cy="' + (+y).toFixed(1) + '" r="' + (r || 4.5) + '" style="stroke:var(--ochre)"/>'; }
  function legendW(w) { return w < 560 ? 0 : 54; }
  /* Верхний отступ поля графика. В тесном режиме (плитка обзора) легенды в картинке нет —
     она уехала в метку и подсказку, и держать под неё 42 пикселя незачем: именно этот
     зазор владелец 06.09 назвал «огромным между названием и графиком». */
  function topPad(w) { return S._tight ? 16 : (legendW(w) ? 26 : 42); }
  /* КЛИКАБЕЛЬНАЯ ЛЕГЕНДА. Владелец 04.09: «все линии тоже нужно дать легенду по моделям,
     отдельно выделить визуально; при нажатии на элемент легенды график её высвечивать
     отдельно, остальные делать блёклыми». Пятый элемент строки — имя того, что выделяем:
     класс моделей или конкретная модель. Обработчик один, на поле графика. */
  /* Метка свёрнутой легенды: та же форма, что в плитке обзора, и на том же месте —
     правый верхний угол поля. Нажатие разворачивает панель обратно. */
  function legToggle(w, top, open) {
    var bw = 72, x = w - bw - 6, y = Math.max(2, top - 16);
    return '<g data-legtoggle="1" style="cursor:pointer">' +
      '<rect x="' + x + '" y="' + y + '" width="' + bw + '" height="14" rx="7" style="fill:var(--surface);stroke:var(--soft)" stroke-width=".9" opacity=".95"/>' +
      '<text x="' + (x + bw / 2) + '" y="' + (y + 10) + '" text-anchor="middle" font-size="8.5" style="fill:var(--soft);letter-spacing:.06em">legend ' + (open ? '×' : '▾') + '</text></g>';
  }

  function legend(items, w, h, R, top) {
    if (S._tight) return legIcon(items, w);
    var s = '', i;
    if (R > 0) {
      /* НАКЛАДНАЯ ПАНЕЛЬ, А НЕ КОЛОНКА. Раньше под легенду отдавалась четверть ширины и
         стояла пустой ниже последней строки (владелец 06.09: «даже когда заканчивается
         легенда, там ещё куча места»). Теперь она лежит поверх графика справа сверху, на
         своей подложке, и сворачивается крестиком. */
      var rows = items.filter(function (it) { return it && it[0]; });
      /* ЛЕГЕНДА — СТРОКОЙ ПОД ШАПКОЙ, НЕ ПОВЕРХ ГРАФИКА (владелец 08.09: «legend подними выше,
         одной строкой, где полный экран и back, иначе наезжает на мини-графики»). Пункты
         запоминаем, строку собирает syncLegendBar после отрисовки; кнопка legend встаёт в
         строку заголовка рядом с source и notes. В SVG ничего не рисуем. */
      S._legItems = items;
      return '';
      var maxCh = 0;
      rows.forEach(function (it) { maxCh = Math.max(maxCh, String(it[0]).length); });
      maxCh = Math.min(maxCh, 30);
      var bw = Math.max(96, Math.min(maxCh * 6.15 + 46, Math.round(w * 0.5)));
      var bx = w - bw - 6, by = Math.max(2, top - 14);
      var bh = 0;
      items.forEach(function (it) { bh += (it && it[0]) ? 16 : 7; });
      s += '<rect x="' + bx + '" y="' + by + '" width="' + bw + '" height="' + (bh + 20) + '" rx="8" style="fill:var(--surface);stroke:var(--hair)" stroke-width="1" opacity=".93"/>';
      s += legToggle(w, by + 16, true);
      var LX = bx, LW = bw;
      var ly = by + 20;
      maxCh = Math.max(8, Math.floor((bw - 44) / 6.15));
      for (i = 0; i < items.length; i++) {
        var it = items[i].slice();
        if (it[0] === '' || it[0] == null) { ly += 7; continue; }   // пустая строка отделяет нажимаемое от справочного
        if (it[0] && it[0].length > maxCh) it[0] = it[0].slice(0, maxCh - 1) + '…';   // не вылезать за панель
        var tag = it[4] ? ' data-pick="' + esc(it[4]) + '" class="pick' + (S.pick === it[4] ? ' on' : '') + '"' : '';
        if (tag) s += '<g' + tag + '>';
        if (it[4] && S.pick === it[4]) s += '<rect x="' + (LX + 3) + '" y="' + (ly - 1) + '" width="' + (LW - 6) + '" height="15" rx="4" style="fill:var(--ochre)" opacity=".14"/>';
        if (it[2] === 'dot') s += '<circle cx="' + (LX + 18) + '" cy="' + (ly + 4) + '" r="4" style="fill:' + it[1] + '"/>';
        else s += '<line x1="' + (LX + 8) + '" y1="' + (ly + 4) + '" x2="' + (LX + 28) + '" y2="' + (ly + 4) + '" style="stroke:' + it[1] + '" stroke-width="' + (it[2] || 2) + '"' + (it[3] ? ' stroke-dasharray="' + it[3] + '"' : '') + '/>';
        s += '<text x="' + (LX + 34) + '" y="' + (ly + 8) + '"' + (it[4] ? ' style="cursor:pointer"' : '') + '>' + esc(it[0]) + '</text>';
        if (it[4]) s += '<rect x="' + (LX + 4) + '" y="' + ly + '" width="' + (LW - 8) + '" height="15" style="fill:transparent;cursor:pointer"/></g>';
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
    var ft = freshTail(seriesKey(w));
    if (ft.length && fin(rec[n - 1])) {
      var tp = [[x0, Y(rec[n - 1])]].concat(ft.map(function (p) { return [X(n - 1 + p[0]), Y(p[1])]; }));
      s += poly(tp, 'var(--ochre)', 1.6, 1, '3 3');
      var lastT = tp[tp.length - 1];
      s += freshDot(lastT[0], lastT[1], 4.5) + '<text x="' + (lastT[0] + 6).toFixed(0) + '" y="' + (lastT[1] - 7).toFixed(0) + '" font-size="9" style="fill:var(--ochre)">fresh ' + fnum(ft[ft.length - 1][1]) + '</text>';
    }
    s += '<polygon points="' + x0.toFixed(1) + ',' + Y(f.from).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p90).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p10).toFixed(1) + '" style="fill:var(--nino)" opacity=".18"/>';
    s += poly([[x0, Y(f.from)], [x1, Y(f.p50)]], 'var(--nino)', 1.6, 1, '5 3');
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p90) + 3).toFixed(0) + '">' + fnum(f.p90) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p50) + 3).toFixed(0) + '" class="tt">' + fnum(f.p50) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p10) + 3).toFixed(0) + '">' + fnum(f.p10) + '</text>';
    var legR = [['last 30 days', 'var(--nino)', 2.6, '', 'last30'], ['400 days', 'var(--text)', 1.8, '', 'all'], ['10–90 % of all years', 'var(--band)', 6, '', 'band'], ['forecast +14 d', 'var(--nino)', 1.6, '5 3', 'fc']];
    if (ft.length) legR.push(['fresh, not yet assessed', 'var(--ochre)', 1.6, '3 3', 'fresh']);
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
    var ftA = freshTail('sst_nino34');
    if (ftA.length && fin(N.current_day)) {
      var tpA = [[X(N.day), Y(N.current_day)]].concat(ftA.map(function (p) { return [X(N.day + p[0]), Y(p[1])]; }));
      s += poly(tpA, 'var(--ochre)', 1.6, 1, '3 3');
      var lA = tpA[tpA.length - 1];
      s += freshDot(lA[0], lA[1], 4.5);
    }
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
    if (ftA.length) legItems.push(['fresh, not yet assessed', 'var(--ochre)', 1.6, '3 3', 'fresh']);
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
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">NOAA weekly indices, last ' + n + ' weeks, °C' + (RC ? '; right: the same four in the strongest past events, to the same week of the year' : '') + '</text>';
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
    /* Легенда теперь накладная (см. legend()), колонку под неё не держим: линии выпусков
       занимали 75 % ширины при пунктирной оси во всю (владелец 06.09). */
    var RCs = W >= 620 ? 12 : 0;
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
      /* Пояснение к выпуску — по центру поля, а не у правого края: там теперь стоит кнопка
         легенды, и они наезжали друг на друга (владелец 06.09: «кнопка легенды наехала на
         надпись вверху; если это надпись с пояснением, отцентрируй её по ширине»). */
      if (!S._tight) s2 += '<text x="' + Math.round((Lp + (W - R)) / 2) + '" y="' + (top + 10) + '" text-anchor="middle" style="fill:var(--soft)">' + below + ' of ' + tot + ' below ' + esc(lab || '') + ' as lived so far (' + fnum(ref2) + (td2 ? ', ' + td2.done + '/3 months' : '') + ')</text>';
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
    var zone = S.sub.zone || 'all', labels = '';
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
      var gOpen = '<g data-src="' + esc(JSON.stringify(pay)) + '" data-zone="' + b[0] + '"' + (dim ? ' opacity=".12"' : '') + '>';
      s += gOpen +
        '<rect' + (b[0] === 'nino34' && zone === 'all' ? ' class="breathe"' : '') + ' x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" style="fill:' + col + ';stroke:' + col + '" fill-opacity="' + (zone === b[0] ? '.42' : '.3') + '" stroke-width="' + (zone === b[0] ? 2.6 : 1.8) + '" rx="3"/></g>';
      var L = gOpen;
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
        L += '<rect x="' + lx0.toFixed(1) + '" y="' + ly0.toFixed(1) + '" width="' + lw.toFixed(1) + '" height="14" rx="7" style="fill:var(--surface);stroke:' + col + '" stroke-width="1.2"/>';
        L += '<text x="' + (lx0 + lw / 2).toFixed(1) + '" y="' + (ly0 + 10.5).toFixed(1) + '" text-anchor="middle" font-size="10" style="fill:' + col + ';font-weight:600;letter-spacing:.03em">' + b[1] + '</text>';
      }
      /* ЧИСЛА — БЕЛЫЕ ПОЛУЖИРНЫЕ С ТЁМНОЙ ОБВОДКОЙ. Владелец 06.09: «все цифры надо
         изменить на белый жирный, потому что всё сливается с фоном». Обводка (paint-order:
         stroke) держит их читаемыми и на светлой заливке зоны, и в тёмной теме, где белое
         на белом было бы не лучше. */
      var HALO = 'fill:#fff;paint-order:stroke;stroke:rgba(20,22,28,.75);stroke-width:3.4;stroke-linejoin:round;font-weight:700';
      L += '<text x="' + tx.toFixed(1) + '" y="' + (cy + (small ? 8 : 7)).toFixed(1) + '" text-anchor="middle" style="' + HALO + '" font-size="' + big + '">' + fnum(v, 1) + '</text>';
      // Сравнение с аналогом — у выбранной зоны крупнее, в режиме «все» мельче, но тоже поверх (владелец 08.09)
      var cmpOn = fin(then) && (zone === b[0] || (zone === 'all' && !small));
      if (cmpOn) L += '<text x="' + tx.toFixed(1) + '" y="' + (cy + (zone === b[0] ? (small ? 21 : 23) : 19)).toFixed(1) + '" text-anchor="middle" style="' + HALO.replace('stroke-width:3.4', 'stroke-width:3') + '" font-size="' + (zone === b[0] ? (small ? 10 : 12) : 9.5) + '">' + cmpYear + ' ' + fnum(then, 1) + ' · ' + (v >= then ? '▲' : '▼') + fnum(Math.abs(v - then), 1, false) + '</text>';
      labels += L + '</g>';
    });
    return s + labels + '</svg>';
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
    if (m.analogs && Object.keys(m.analogs).length) return null;   // ряд принёс своих аналогов (боксы OISST): чужие по имени не подмешиваем — в absolute они ложились у нуля (08.09)
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
    W = W || 60; H = H || 26;   // без размеров получался viewBox "undefined" и точка с NaN (07.09)
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
        '<a class="wk-read" href="' + u + '"' + tgt + '>Read the adapted article →</a> <span class="wk-num">' + esc(l.id) + '</span></p>';
    }).join('');
  }
  /* Тот же slug, что в tools/enso/links.py (_aslug): менять только вместе. */
  /* ОБЛАКО ПОНЯТИЙ (задание ведущей сессии 08.09, ЭЛЬНИНЬО-РАЗМЕТКА-ПОНЯТИЯМИ.md). Слой данных —
     data/enso/concepts.json (concepts_link.py): у каждого якоря панели (риск, тревога, term:*,
     region:*, block:*) три–семь понятий реестра. Вид: строка чипов внутри уже существующих
     подсказок и ящиков, третьего окна нет; чип ведёт на страницу понятия на языке читателя,
     одна ссылка в конце открывает граф сразу на наборе — новой вкладкой, с панели не уводим.
     Понятия к сценам и карточкам руками не привязываются: только якорь → данные. */
  var CN_LANGS = ['en', 'ru', 'ar', 'es', 'fr'];
  /* Язык понятий — язык самой панели, а не сохранённый выбор сайта: панель английская, и
     русские чипы со ссылками на русские страницы на ней смотрелись чужими (владелец 08.09).
     Когда у панели появится свой язык (атрибут lang на <html>), понятия пойдут за ним. */
  function cnLang() {
    var l = String(document.documentElement.getAttribute('lang') || 'en').slice(0, 2);
    return CN_LANGS.indexOf(l) >= 0 ? l : 'en';
  }
  function conceptsFor(anchors) {
    var A = (S.CN || {}).anchors || {}, seen = {}, out = [];
    (Array.isArray(anchors) ? anchors : [anchors]).forEach(function (a) {
      (A[a] || []).forEach(function (c) { if (!seen[c.id]) { seen[c.id] = 1; out.push(c); } });
    });
    return out.sort(function (a, b) { return (b.score || 0) - (a.score || 0); });
  }
  function cnAnchor(cands) { for (var i = 0; i < cands.length; i++) if (conceptsFor(cands[i]).length) return cands[i]; return cands[0] || ''; }
  function cnName(c) { var l = cnLang(); return (l === 'ru' && c.name_ru) ? c.name_ru : (c.name_en || c.id); }
  function cnUrl(id) { return '/lang/' + cnLang() + '/concepts/' + encodeURIComponent(id) + '.html'; }
  function cnGraph(ids, focus) { return '/lang/' + cnLang() + '/concepts/graph.html?set=' + ids.map(encodeURIComponent).join(',') + '&focus=' + encodeURIComponent(focus || ids[0]); }
  function cnPay(c) {
    return esc(JSON.stringify({ name: cnName(c), html: '<p>' + esc(c.line || '') + '</p><a href="' + cnUrl(c.id) + '" target="_blank" rel="noopener">open the concept page ↗</a>',
      src: 'concept' + (c.kind ? ' · ' + c.kind : '') + (fin(c.score) ? ' · closeness ' + c.score.toFixed(2) : '') }));
  }
  /* Строка чипов: до семи понятий, дальше «all N» на граф; в конце одна ссылка на граф набора. */
  function conceptsHtml(anchors, full, col) {
    var cs = conceptsFor(anchors); if (!cs.length) return '';
    var show = full ? cs : cs.slice(0, 7), ids = cs.map(function (c) { return c.id; });
    var gbtn = '<button type="button" class="cn-mg" data-ids="' + esc(ids.join(',')) + '" data-focus="' + esc(ids[0]) + '">graph</button>';
    if (col) {
      /* Подсказка: колонкой, имя и одна строка смысла (владелец 08.09: «в аккуратную колонку»). */
      return '<div class="cn col"><span class="cn-h">concepts</span>' +
        show.map(function (c) { return '<a class="cn-r" href="' + cnUrl(c.id) + '" target="_blank" rel="noopener"><b>' + esc(cnName(c)) + '</b><span>' + esc(c.line || '') + '</span></a>'; }).join('') +
        '<div class="cn-f">' + (cs.length > show.length ? '<span class="cn-more">all ' + cs.length + ' on the graph</span>' : '') + gbtn + '</div></div>';
    }
    return '<div class="cn"><span class="cn-h">concepts</span>' +
      show.map(function (c) { return '<a class="cn-c" href="' + cnUrl(c.id) + '" target="_blank" rel="noopener" data-src="' + cnPay(c) + '">' + esc(cnName(c)) + '</a>'; }).join('') +
      (cs.length > show.length ? '<span class="cn-c more">all ' + cs.length + ' on the graph</span>' : '') + gbtn + '</div>';
  }
  /* МИНИ-ГРАФ В КАРТОЧКЕ (второй шаг задания, владелец 08.09: «граф должен открываться
     отдельно, в конце»). Движок общий — js/b42-graph-core.js + js/b42-mini.js, тот же, что на
     страницах понятий и статей; грузится по первому нажатию. Кадр встаёт под облаком,
     повторное нажатие сворачивает; узлы открывают страницы новой вкладкой. */
  function miniLib() {
    if (window.B42Mini && window.B42Mini.mount) return Promise.resolve();
    if (S._miniLoad) return S._miniLoad;
    function one(src) { return new Promise(function (ok, bad) { var sc = document.createElement('script'); sc.src = src; sc.onload = ok; sc.onerror = function () { bad(new Error(src)); }; document.head.appendChild(sc); }); }
    S._miniLoad = one('/js/b42-graph-core.js').then(function () { return one('/js/b42-mini.js'); }).catch(function (e) { S._miniLoad = null; throw e; });
    return S._miniLoad;
  }
  /* Окно графа поверх панели (владелец 08.09: «мини-граф открывать во всплывающем окошке, не
     отдельное окно; если захочется — там кнопка перехода»). Одно окно на страницу; закрывают
     крестик, Esc и клик мимо. Узлы и «весь граф» открываются новой вкладкой, панель остаётся. */
  function cnBtn(anchors, label) {
    var a = Array.isArray(anchors) ? anchors : [anchors];
    if (!conceptsFor(a).length) return '';
    return '<button type="button" class="cn-mg rail" data-anchors="' + esc(a.join(',')) + '">' + esc(label || 'graph') + '</button>';
  }
  function closeGraphModal() { var m = $('cnModal'); if (m) m.remove(); }
  function openGraphModal(ids, focus, width, anchors) {   // width — ширина карточки, из которой открыли (владелец 08.09: «в размер карточки»); anchors — показать и облако
    closeGraphModal();
    var tip = $('tip'); if (tip) { tip.classList.remove('on', 'pin'); S.pinned = null; }
    var m = el('div', 'cn-modal'); m.id = 'cnModal';
    var names = ids.map(function (id) { var c = conceptsFor(Object.keys((S.CN || {}).anchors || {})).filter(function (q) { return q.id === id; })[0]; return c ? cnName(c) : id; });
    m.innerHTML = '<div class="cn-modal-box"><div class="cn-modal-h"><b>' + ids.length + ' concepts on the graph</b><span class="cn-modal-n">' + esc(names.slice(0, 5).join(' · ')) + (names.length > 5 ? ' · …' : '') + '</span>' +
      '<button type="button" class="x" title="close (Esc)">×</button></div>' +
      (anchors && anchors.length ? conceptsHtml(anchors, true).replace(/<button[^>]*class="cn-mg"[\s\S]*?<\/button>/, '') : '') +
      '<div class="b42mini" data-ids="' + esc(ids.join(',')) + '" data-focus="' + esc(focus || ids[0]) + '" data-newtab="1" data-lang="' + cnLang() + '"></div>' +
      '<div class="cn-modal-f"><span>drag a node; hover for the meaning; click to open its page in a new tab</span>' +
      '<a class="cn-g" href="' + cnGraph(ids, focus) + '" target="_blank" rel="noopener">open the full graph ↗</a></div></div>';
    if (width) m.querySelector('.cn-modal-box').style.width = Math.min(window.innerWidth - 24, 760, Math.max(360, width)) + 'px';   // из полного экрана не растягивается на всю ширину (владелец 08.09)
    document.body.appendChild(m);
    m.addEventListener('click', function (e) { if (e.target === m || e.target.closest('.x')) closeGraphModal(); });
    var box = m.querySelector('.b42mini');
    miniLib().then(function () { window.B42Mini.mount(box); }).catch(function () { box.innerHTML = '<div class="note warn">The graph engine did not load; the full graph link below still works.</div>'; });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.cn-mg'); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    var host = b.closest('.tip, .card, .risk, .kpi, .ov-kpi, .info-pane, .cn-box, .cn-row, .stage-body, .tile');
    var hw = host ? host.getBoundingClientRect().width : 0;
    if (host && host.closest('#railL, #railR')) hw = Math.max(hw, 720);   // rail column is narrow; the window needs room for the graph
    var an = b.getAttribute('data-anchors');
    if (an) {                                    // кнопка по якорям: набор считаем здесь, в окне и облако, и граф
      var al = an.split(',').filter(Boolean), cs = conceptsFor(al); if (!cs.length) return;
      openGraphModal(cs.map(function (c) { return c.id; }), cs[0].id, hw, al);
      return;
    }
    openGraphModal(b.getAttribute('data-ids').split(',').filter(Boolean), b.getAttribute('data-focus'), hw);
  }, true);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeGraphModal(); });
  /* Якоря сцены для ящика source/notes и подсказок на графике: блоки утверждений links.py. */
  var SCENE_ANCHORS = { now: ['block:type', 'block:peak'], risk: ['block:type', 'block:peak'], models: ['block:models'], food: ['block:food'], radiance: ['block:radiance'],
    'trend/rain': ['block:rain'], 'trend/spectral': ['block:spectral'], regions: ['block:landbox'], gulf: ['block:landbox'], air: ['block:peak'] };
  function sceneAnchors() { return SCENE_ANCHORS[S.view + '/' + (S.sub[S.view] || '')] || SCENE_ANCHORS[S.view] || []; }
  /* Подсветка в тексте: первое вхождение имени понятия словами, только в текстовых узлах,
     не внутри ссылок и терминов. Дорога вглубь, а не раскраска. */
  function hlConcepts(root, anchors) {
    var cs = conceptsFor(anchors); if (!cs.length || !root) return;
    var names = cs.map(function (c) { return (c.name_en || '').toLowerCase(); });
    cs.slice().sort(function (a, b) { return (b.name_en || '').length - (a.name_en || '').length; }).forEach(function (c) {
      var nm = c.name_en; if (!nm || nm.length < 4) return;
      if (names.some(function (o) { return o !== nm.toLowerCase() && o.indexOf(nm.toLowerCase()) >= 0; })) return;
      var re = new RegExp('(^|[^A-Za-z])(' + nm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')(?![A-Za-z])', 'i');
      var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), n;
      while ((n = w.nextNode())) {
        if (n.parentNode.closest('a,[data-term],.cn,button,svg')) continue;
        var m = re.exec(n.nodeValue); if (!m) continue;
        var at = m.index + m[1].length, a = document.createElement('a');
        a.className = 'cn-in'; a.href = cnUrl(c.id); a.target = '_blank'; a.rel = 'noopener'; a.setAttribute('data-src', cnPay(c)); a.textContent = m[2];
        var rest = n.splitText(at); rest.nodeValue = rest.nodeValue.slice(m[2].length);
        n.parentNode.insertBefore(a, rest);
        return;
      }
    });
  }
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
        ' · <span class="wk-num">' + esc(l.id) + '</span></i><em class="wk-read">Read the adapted article →</em></a>';
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
    /* ДВА РЯДА (владелец 07.09: «меню разрослось; основные вверху влево, служебные ниже вправо»). */
    var rowMain = el('div', 'trow'), rowSvc = el('div', 'trow svc');
    list.forEach(function (v) {
      /* Служебные вкладки (метод, цепочка, о панели) выглядят иначе: пунктирная рамка,
         приглушённый цвет; вердикт — контрастный чёрно-белый. У каждой — подсказка,
         что это (владелец 05.09). */
      var svc = v[0] === 'how' || v[0] === 'chain' || v[0] === 'about' || v[0] === 'refs' || v[0] === 'ops';
      /* Подсказка к пункту меню — на значке «i» справа от текста, а не на самой кнопке
         (владелец 05.09: «для меню неудобно тултипы — пусть будет небольшая иконка i»). */
      var b = el('button', 'tab' + (v[0] === 'verdict' ? ' verdict' : '') + (svc ? ' svc' : '') + (S.view === v[0] ? ' on' : ''),
        esc(v[1]) + (T.tabHelp[v[0]] ? '<i class="ti" data-src="' + esc(JSON.stringify({ name: v[1], def: T.tabHelp[v[0]] })) + '">i</i>' : ''));
      b.type = 'button';
      b.onclick = function (e) { if (e.target.closest && e.target.closest('.ti')) return; S.view = v[0]; S.risk = null; render(); };
      (svc ? rowSvc : rowMain).appendChild(b);
    });
    host.appendChild(rowMain); host.appendChild(rowSvc);
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
    item('<b>updated</b> ' + dt((D.stamp || '').slice(0, 10)), { name: 'This update', def: 'The panel was recomputed at ' + D.stamp + (P ? '; the previous update was at ' + P.stamp + '.' : '.') + ' Updating is semi-automatic: a person runs it and looks at the result before it goes out.', src: 'this panel, recomputed by hand after each release', date: D.generated });
    item('<b>daily</b> ' + esc(n34.last_date) + ' <i>' + n34.days_stale + ' d ago</i>', { name: 'Daily series', def: 'Niño 3.4 and the world ocean: final OISST from climatereanalyzer' + (n34.prelim_from ? ' to ' + addDays(n34.prelim_from, -1) + ', then the preliminary NOAA grid (NRT) spliced on directly, one day behind; the last two weeks are re-pulled every update' : ', which lags one to three weeks') + '. Land+ocean (ERA5) reaches ' + tw.last_date + '.', src: n34.prelim_from ? 'climatereanalyzer.org + NOAA OISST NRT via ERDDAP' : 'climatereanalyzer.org', date: n34.last_date }, n34.days_stale > 14 ? 'bad' : '');
    item('<b>NOAA week</b> ' + esc(D.noaa.date), { name: 'NOAA weekly indices', def: 'Published every Wednesday for the previous week; always fresher than the daily OISST, and where they disagree the panel trusts the weekly.', src: 'NOAA CPC wksst9120.for', date: D.noaa.date });
    if (D.iri && D.iri.issued) item('<b>IRI</b> ' + esc(D.iri.issued), { name: 'IRI model plume', def: 'The forecasts of two dozen centres, published around the 19th of each month. ' + ((D.iri.class_issues || []).length) + ' issues are stored here, which is what makes the model scoreboard possible.', src: 'iri.columbia.edu', date: D.iri.issued });
    if (D.food && !D.food.error) item('<b>FAO</b> ' + esc(D.food.last_month), { name: 'FAO Food Price Index', def: 'Monthly, published on the first Friday for the previous month: the only live food series available without registration.', src: 'fao.org', date: D.food.last_month });
    /* РЯДА ТОЧЕК БОЛЬШЕ НЕТ. Он горел всегда и потому не значил ничего; откуда взято
       и за когда — теперь на каждом кирпиче отдельно (владелец 04.09). Осталась одна
       строка и только когда есть о чём сказать: источник не ответил. */
    /* В шапке — только «updated» (владелец 05.09: «источников много — просто updated
       оставить, всё убрать»); свежесть каждого источника живёт на Data chain и References. */
    Array.prototype.slice.call(host.children, 1).forEach(function (c) { host.removeChild(c); });   // владелец 07.09: дата обновления панели остаётся, остальное — на Data chain
    /* СВЕЖЕЕ, НЕ РАЗОБРАННОЕ (владелец 06.09): лёгкий прогон без модели; пунктирная точка дышит,
       пока данные не прошли разбор. Показывается только если слой считан против ЭТОГО разбора. */
    var F = S.F || {};
    if (F.stamp && F.assessed_stamp === D.stamp && F.stamp !== D.stamp) {
      var latestF = Object.keys(F.series || {}).map(function (q) { return (F.series[q] || {}).last_date || ''; }).sort().pop() || '';
      var nT = (F.triggers || []).length;
      item('<span class="fdot"></span><b>fresh</b> to ' + dt(latestF) + (nT ? ' · ' + nT + ' trigger' + (nT > 1 ? 's' : '') : ''),
        { name: 'Fresh, not yet assessed', def: (F.summary || '') + ' ' + (F.note || ''), src: 'light run ' + F.stamp + ', rules only, no model', date: latestF }, F.needs_assessment ? 'bad' : '');
    }
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
      '<div class="cgo">' + esc(ALERT_GO[a.kind || 'climate'].label) + ' →</div>' + (linksHtml('alert:' + (a.id || aslug(a.title))) || linksHtml('alert:' + aslug(a.title)) || linksHtml('alert:' + i)) +
      cnBtn(['alert:' + (a.id || aslug(a.title)), 'alert:' + aslug(a.title)], 'graph');
    /* КАРТОЧКА ТРЕВОГИ ВЕДЁТ ТУДА, ГДЕ ЕЁ ЧИСЛА. Владелец 04.09: «слева карточки, они же тоже
       могут вести на какие-то риски или наши графики навигации». Тревога — это утверждение,
       и у каждого утверждения на панели есть своя сцена: климат живёт в рядах, цены в товарах,
       модели в плюме, а «источник молчит» — в списке источников. Клик по ссылке в конце
       карточки открывает именно её; клик по самой карточке не трогаем, чтобы не мешать
       выделять текст. */
    var go = ALERT_GO[a.kind || 'climate'];
    var an = cnAnchor(['alert:' + (a.id || aslug(a.title)), 'alert:' + aslug(a.title), 'alert:' + i]);
    c.setAttribute('data-anchor', an); hlConcepts(c.querySelector('.cd'), an);
    c.querySelector('.cgo').setAttribute('data-go', go.view);
    if (go.sub) c.querySelector('.cgo').setAttribute('data-gosub', go.sub);
    return c;
  }

  /* ЛЕНТА ГЛАВНЫХ KPI ПОД ВКЛАДКАМИ (владелец 08.09: «главные KPI, которые сильно изменились,
     в ряд: просто цифра с названием и стрелкой вверху; на стрелочку — историю»). Источник —
     журнал (journal.json), тот же, что у стрелок на плашках: значение последней записи,
     изменение к предыдущей. Порядок — по важности; сначала те, что изменились. */
  var STRIP_KEYS = ['n34_weekly', 'n34_daily', 'oni', 'risk_index', 'sst_world', 'n_alerts', 'models_broke', 'iri_share_below', 'food_index', 'wwv', 'subsurface_warmest', 'wind_week', 'gulf_sst', 'mjo_amp'];
  var STRIP_NAME = { n34_weekly: 'Niño 3.4 weekly', n34_daily: 'Niño 3.4 daily', oni: 'ONI', risk_index: 'risk index', sst_world: 'world ocean', n_alerts: 'alerts', models_broke: 'models broken', iri_share_below: 'models below reality', food_index: 'food index', wwv: 'warm water volume', subsurface_warmest: 'warmest layer', wind_week: 'westerly, week', gulf_sst: 'Gulf SST', mjo_amp: 'MJO amplitude' };
  function buildStrip() {
    var host = $('kstrip'); if (!host) return;
    var items = [];
    STRIP_KEYS.forEach(function (k) {
      var r = jrec(k), e = r ? (r.entries || []) : []; if (!e.length) return;
      var last = e[e.length - 1], prev = e.length > 1 ? e[e.length - 2] : null;
      if (typeof last.v !== 'number') return;
      var dv = prev && typeof prev.v === 'number' ? last.v - prev.v : 0;
      items.push({ k: k, r: r, last: last, prev: prev, dv: dv });
    });
    var changed = items.filter(function (x) { return x.dv; }), still = items.filter(function (x) { return !x.dv; });
    var show = changed.concat(still).slice(0, 12);
    if (!show.length) { host.hidden = true; return; }
    host.hidden = false;
    host.innerHTML = '<span class="ks-h" data-src="' + esc(JSON.stringify({ name: 'Main indicators', def: 'The value of the last reading and its change against the previous one, from the panel journal; the ones that moved come first. Click any to see its history.' })) + '">KPI</span>' +
      show.map(function (x) {
        var dg = x.r.digits, u = x.r.unit || '', sign = x.dv > 0 && x.last.v >= 0 && dg > 0 ? '' : '';
        var pay = { name: x.r.title, def: (x.prev ? 'Was ' + jval(x.prev.v, dg) + ' on ' + x.prev.d + ', now ' + jval(x.last.v, dg) + ' on ' + x.last.d + '.' : 'First reading we hold: ' + jval(x.last.v, dg) + ' on ' + x.last.d + '.') + ' Click for the history.', src: x.r.src, date: x.last.d };
        return '<button type="button" class="ks" data-hist="' + esc(x.k) + '" data-src="' + esc(JSON.stringify(pay)) + '">' +
          '<span class="ks-row"><span class="ks-v">' + (x.k === 'oni' || /nino|n34|sst_world|wind|mjo/.test(x.k) && x.last.v > 0 ? '+' : '') + jval(x.last.v, dg) + (u ? '<small>' + esc(u) + '</small>' : '') + '</span>' +
          (x.dv ? '<span class="ks-d ' + jsign(x.dv) + '">' + jarrow(x.dv) + (x.dv > 0 ? '+' : '') + jval(x.dv, dg) + '</span>' : '') + '</span>' +
          '<span class="ks-n">' + esc(STRIP_NAME[x.k] || x.r.title) + '</span></button>';
      }).join('');
  }
  /* ══ ИССЛЕДОВАНИЕ В ДИАЛОГЕ (владелец 08.09; контур ведущей сессии — ЭЛЬНИНЬО-ЧАТ-ИССЛЕДОВАНИЕ-РУЧКА.md) ══
     «Чат с моделью: справа диалог, слева собираются наши KPI, граф, облако понятий и резюме
     беседы; проверять моделью; сохранять». Данные и ручка за ведущей сессией: индекс панели в
     Vectorize (пространство panel), /api/research (ответ с пометками [risk:…] и [номер работы],
     режим verify), /api/research/save|list|delete в D1 по uid. Здесь — вид: доска, диалог,
     чтение ответа одной функцией. Без ручки (localhost) — извлечённый ответ с пометкой demo и
     сохранение в браузере. */
  var KPI_SCENE = { n34_weekly: 'now/weekly', n12_weekly: 'now/weekly', n34_daily: 'trend/sst_nino34', n34_30d: 'trend/sst_nino34', rec_sst_nino34: 'trend/sst_nino34', fc14_sst_nino34: 'trend/sst_nino34',
    n34_box: 'ocean/surface', n12_box: 'ocean/surface', gulf_sst: 'ocean/surface', subsurface_warmest: 'ocean/moorings', d20_east: 'ocean/section',
    oni: 'now/analogs', roni: 'now/analogs', risk_index: 'verdict', n_risks: 'now/analogs', n_alerts: 'now/analogs', scenario: 'regions',
    sst_world: 'trend', t2_world: 'trend', rec_sst_world: 'trend', rec_t2_world: 'trend', fc14_sst_world: 'trend', fc14_t2_world: 'trend',
    models_broke: 'models/breakdown', models_ok: 'models/breakdown', models_lag: 'models/breakdown', models_above: 'models/breakdown', models_below_n: 'models/breakdown', iri_share_below: 'models/breakdown', iri_peak: 'models/plume', live_mean: 'models/plume', n_live: 'models/plume',
    food_index: 'food/prices', food_yoy: 'food/prices', price_palm_oil: 'food/goods', price_rice: 'food/goods', price_fishmeal: 'food/goods', price_wheat: 'food/goods',
    wwv: 'air', wwv_share: 'air', wind_week: 'air', mjo_amp: 'air', dmi: 'air', soi: 'air', olr: 'air', u850_west: 'air', coupling_score: 'air', tlt_tropics: 'air', tls_tropics: 'air',
    ohc_2000: 'planet', kuwait_tmax30: 'regions/place/gulf_arabia', peak_estimate: 'now/analogs' };
  var RS_STOP = { the: 1, and: 1, for: 1, with: 1, that: 1, this: 1, what: 1, why: 1, how: 1, does: 1, are: 1, is: 1, of: 1, to: 1, in: 1, on: 1, a: 1, an: 1, it: 1, its: 1, be: 1, will: 1, was: 1, were: 1, has: 1, have: 1, from: 1, about: 1, than: 1, now: 1, our: 1, we: 1, you: 1, can: 1, not: 1, which: 1, when: 1, where: 1, there: 1, into: 1, over: 1, any: 1, all: 1 };
  var RS_SYN = { nino: 'niño', 'el': '', nina: 'niña', temperature: 'temperature warm', warming: 'warm', rain: 'rain precipitation', rainfall: 'rain', drought: 'rain dry', prices: 'price food', food: 'food price', models: 'model forecast', forecast: 'forecast model', ocean: 'ocean sea', sea: 'sea ocean', wind: 'wind westerly', volume: 'volume fuel', fuel: 'fuel volume', peak: 'peak', strength: 'strong', strong: 'strong' };
  /* Ручка: явный адрес, иначе своя на сайте; на localhost ручки нет — демо. */
  function rsApi() {
    if (window.B42_RESEARCH_API !== undefined) return window.B42_RESEARCH_API || '';
    return /^(localhost|127\.0\.0\.1)$/.test(location.hostname) ? '' : '/api/research';
  }
  var RS_TOKEN_KEY = 'b42_tutor_token';   // тот же токен, что у тьютора: одна норма, одна выдача
  function rsToken() { try { return localStorage.getItem(RS_TOKEN_KEY) || ''; } catch (e) { return ''; } }
  function rsSetToken(t) { try { t ? localStorage.setItem(RS_TOKEN_KEY, t) : localStorage.removeItem(RS_TOKEN_KEY); } catch (e) { } }
  function rsPass() {   // пропуск: токен заменяет капчу; иначе Turnstile общим помощником
    if (rsToken()) return Promise.resolve({ token: rsToken() });
    return new Promise(function (ok) {
      function go() { (window.b42TurnstilePass ? window.b42TurnstilePass() : Promise.resolve('')).then(function (t) { ok({ turnstile: t }); }, function () { ok({ turnstile: '' }); }); }
      if (window.b42TurnstilePass) return go();
      var s = document.createElement('script'); s.src = '/js/b42-turnstile.js'; s.onload = go; s.onerror = function () { ok({ turnstile: '' }); }; document.head.appendChild(s);
    });
  }
  function rsPost(body) {
    return rsPass().then(function (p) {
      var h = { 'content-type': 'application/json' }; if (p.token) h['x-b42-token'] = p.token; else body.turnstile = p.turnstile || '';
      return fetch(rsApi(), { method: 'POST', headers: h, credentials: 'same-origin', body: JSON.stringify(body) }).then(function (r) { return r.json().then(function (d) { d._status = r.status; return d; }); });
    });
  }
  function rsTokens(q) {
    var out = [];
    String(q || '').toLowerCase().replace(/[^a-z0-9°ñ.+\s-]/g, ' ').split(/\s+/).forEach(function (w) {
      w = w.replace(/^[.+-]+|[.+-]+$/g, ''); if (!w || RS_STOP[w] || w.length < 3) return;
      out.push(w); if (RS_SYN[w]) RS_SYN[w].split(' ').forEach(function (x) { if (x && x !== w && out.indexOf(x) < 0) out.push(x); });
    });
    return out;
  }
  function rsCorpus() {
    if (S._rsCorpus) return S._rsCorpus;
    var D = S.D || {}, items = [];
    (D.risks || []).forEach(function (r) { items.push({ kind: 'risk', id: r.id, title: r.title, text: [r.plain, r.evidence, r.watch].filter(Boolean).join(' '), hash: '#risk/' + (r.id || ''), anchors: ['risk:' + (r.id || '')], w: 1.25 }); });
    (D.alerts || []).forEach(function (a) { items.push({ kind: 'alert', id: a.id || aslug(a.title), title: a.title, text: a.detail || '', hash: '#now/analogs', anchors: [cnAnchor(['alert:' + (a.id || aslug(a.title)), 'alert:' + aslug(a.title)])], w: 1 }); });
    var M = (S.J || {}).metrics || {};
    Object.keys(M).forEach(function (k) {
      if (k.indexOf('risk:') === 0) return;
      var r = M[k], e = r.entries || [], last = e[e.length - 1];
      var plainKey = Object.keys(KPI_PLAIN).filter(function (p) { return (r.title || '').toLowerCase().indexOf(p) >= 0 || (STRIP_NAME[k] || '').toLowerCase().indexOf(p) >= 0; })[0];
      items.push({ kind: 'kpi', id: k, title: r.title || k, text: (STRIP_NAME[k] || '') + ' ' + (plainKey ? KPI_PLAIN[plainKey] : '') + ' ' + (r.src || '') + (last ? ' latest ' + jval(last.v, r.digits) + ' ' + (r.unit || '') + ' on ' + last.d : ''),
        hash: '#' + (KPI_SCENE[k] || 'overview'), anchors: ['kpi:' + k], w: 1.1 });
    });
    Object.keys(S.G || {}).forEach(function (k) { var g = S.G[k]; if (!g || !g.name) return; items.push({ kind: 'term', id: k, title: g.name, text: (g.def || '') + ' ' + (g.why || ''), hash: '#how', anchors: ['term:' + k], w: 1 }); });
    Object.keys(SCENE_INFO).forEach(function (v) { var i = SCENE_INFO[v]; items.push({ kind: 'scene', id: v, title: T.tabs[v] || v, text: (i.plain || '') + ' ' + (i.source || ''), hash: '#' + v, anchors: SCENE_ANCHORS[v] || [], w: 0.8 }); });
    var seen = {};
    Object.keys(((S.CN || {}).anchors || {})).forEach(function (a) { (S.CN.anchors[a] || []).forEach(function (c) { if (seen[c.id]) return; seen[c.id] = 1; items.push({ kind: 'concept', id: c.id, title: c.name_en || c.id, text: c.line || '', url: cnUrl(c.id), anchors: [], c: c, w: 0.9 }); }); });
    var sm = D.summary || {}; if (sm.verdict) items.push({ kind: 'verdict', id: 'verdict', title: 'The verdict of the day', text: sm.verdict, hash: '#verdict', anchors: ['block:type', 'block:peak'], w: 1.1 });
    ((S.ST || {}).items || []).forEach(function (it) { items.push({ kind: 'stat', id: it.id, title: it.title, text: (it.kpis || []).map(function (k) { return k.name + ' ' + k.value + ' ' + (k.unit || '') + '. ' + (k.plain || ''); }).join(' ') + ' ' + ((it.method || {}).plain || ''), hash: '#' + it.scene, anchors: it.anchors || [], w: 1.05 }); });
    items.forEach(function (it) { it.lt = String(it.title || '').toLowerCase(); it.lx = String(it.text || '').toLowerCase(); });
    S._rsCorpus = items; return items;
  }
  function rsSearch(q, n) {
    var toks = rsTokens(q), ql = String(q || '').toLowerCase().trim(); if (!toks.length) return [];
    var scored = rsCorpus().map(function (it) {
      var sc = 0;
      toks.forEach(function (t) { if (it.lt.indexOf(t) >= 0) sc += 3; if (it.lx.indexOf(t) >= 0) sc += 1; });
      if (ql.length > 6 && (it.lt.indexOf(ql) >= 0 || it.lx.indexOf(ql) >= 0)) sc += 4;
      return { it: it, sc: sc * it.w };
    }).filter(function (x) { return x.sc > 0; }).sort(function (a, b) { return b.sc - a.sc; });
    return scored.slice(0, n || 8).map(function (x) { x.it.score = x.sc; return x.it; });
  }
  function rsState() {
    if (!S.rs) S.rs = { msgs: [], kpis: [], anchors: [], concepts: {}, links: {}, works: {}, summary: [], verdicts: [], created: new Date().toISOString().slice(0, 16).replace('T', ' ') };
    return S.rs;
  }
  function rsFirstSentences(t, n) { var p = String(t || '').split(/(?<=[.!?])\s+/); return p.slice(0, n || 2).join(' '); }
  function rsDemoAnswer(q, hits, lead) {
    if (!hits.length) return '<p>' + (lead || 'Nothing on the panel matches this yet.') + ' Try the words the panel uses: Niño 3.4, ONI, fuel, warm water volume, models, food prices, rain, a region.</p>' + (rsApi() ? '' : '<span class="demo">demo · no model behind this answer; the search is lexical, over the statements of this panel</span>');
    var s = '<p>' + (lead || 'What the panel says about this:') + '</p><ul>' + hits.slice(0, 4).map(function (h) {
      return '<li><b>' + esc(h.title) + '</b> — ' + esc(rsFirstSentences(h.text, 2)) + (h.hash ? ' <a href="enso.html' + esc(h.hash) + '" target="_blank" rel="noopener">open ↗</a>' : (h.url ? ' <a href="' + esc(h.url) + '" target="_blank" rel="noopener">concept ↗</a>' : '')) + '</li>';
    }).join('') + '</ul>' + (rsApi() ? '' : '<span class="demo">demo · no model behind this answer: extracted from the statements of this panel by a lexical search; on the site the same question goes to /api/research</span>');
    return s;
  }
  /* Ответ ручки — одной функцией: пометки [risk:…] ведут на панель, [номер] — на нашу статью. */
  function rsRenderAnswer(d) {
    var byId = {}; (d.panel || []).forEach(function (p) { byId[p.id] = p; });
    var byW = {}; (d.works || []).forEach(function (w) { byW[String(w.id).replace(/v\d+$/, '')] = w; });
    var t = esc(d.answer || '');
    t = t.replace(/\[([a-z]+:[A-Za-z0-9_.\-]+)\]/g, function (m, id) { var p = byId[id]; return p ? '<a class="rs-cite" href="enso.html' + esc(p.hash || '') + '" target="_blank" rel="noopener" title="' + esc(p.title || '') + '">' + esc(p.kind || 'panel') + '</a>' : '<span class="rs-cite">' + esc(id) + '</span>'; });
    t = t.replace(/\[(\d{4}\.\d{4,5})(?:v\d+)?\]/g, function (m, id) { var w = byW[id]; return w ? '<a class="rs-cite wk" href="' + esc(w.url || '#') + '" target="_blank" rel="noopener" title="' + esc(w.title || '') + '">' + esc(id) + '</a>' : '<span class="rs-cite wk">' + esc(id) + '</span>'; });
    return '<p>' + t.replace(/\n{2,}/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
  }
  function rsMergeApi(rs, d) {
    (d.kpis || []).forEach(function (k) { var key = String(k.id || '').replace(/^kpi:/, ''); if (jrec(key) && rs.kpis.indexOf(key) < 0) rs.kpis.push(key); });
    (d.concepts || []).forEach(function (c) { rs.concepts[c.id] = { id: c.id, name_en: c.name || c.id, name_ru: c.name_ru, kind: c.kind, line: c.line || '' }; });
    (d.panel || []).forEach(function (p) { if (!p.hash) return; var key = p.hash + '|' + p.kind; var old = rs.links[key]; rs.links[key] = { kind: p.kind, title: p.title, hash: p.hash, cited: !!(p.cited || (old && old.cited)) }; if (p.anchor && rs.anchors.indexOf(p.anchor) < 0) rs.anchors.push(p.anchor); });
    (d.works || []).forEach(function (w) { var old = rs.works[w.id]; rs.works[w.id] = { id: w.id, title: w.title, url: w.url, date: w.date, cited: !!(w.cited || (old && old.cited)), no_text: !!w.no_text, api: true }; });
    if (d.dayLeft != null) rs.left = { day: d.dayLeft, week: d.weekLeft };
  }
  function rsMerge(rs, hits) {
    hits.forEach(function (h) {
      (h.anchors || []).forEach(function (a) { if (a && rs.anchors.indexOf(a) < 0) rs.anchors.push(a); });
      if (h.kind === 'kpi' && rs.kpis.indexOf(h.id) < 0) rs.kpis.push(h.id);
      if (h.kind === 'concept') rs.concepts[h.id] = h.c;
      if (h.hash && h.kind !== 'kpi') rs.links[h.hash + '|' + h.kind] = rs.links[h.hash + '|' + h.kind] || { kind: h.kind, title: h.title, hash: h.hash, cited: false };
    });
    conceptsFor(rs.anchors).forEach(function (c) { rs.concepts[c.id] = c; });
    rs.anchors.forEach(function (a) { linksFor(a).forEach(function (l) { if (!rs.works[l.id]) rs.works[l.id] = l; }); });
    (rs.anchors || []).forEach(function (a) { if (a.indexOf('kpi:') === 0 && rs.kpis.indexOf(a.slice(4)) < 0 && jrec(a.slice(4))) rs.kpis.push(a.slice(4)); });
  }
  var RS_ERR = { captcha_failed: 'The page could not get a “not a robot” pass. Enter an access token (button below) or reload the page.', token_required: 'An access token is needed.', token_invalid: 'The access token is not valid.', token_expired: 'The access token has expired.',
    limit_day: 'The token’s daily allowance is used up.', limit_total: 'The token’s allowance is used up.', quota_day: 'Today’s allowance of questions is used up.', quota_week: 'This week’s allowance of questions is used up.', not_configured: 'The answer service is not configured on this server.', no_key: 'The model key is missing on the server.' };
  function rsAsk(q) {
    var rs = rsState(), hits = rsSearch(q, 8);
    var msg = { q: q, a: '', hits: hits.map(function (h) { return { kind: h.kind, title: h.title, hash: h.hash || h.url || '' }; }), demo: true, t: new Date().toISOString().slice(11, 16) };
    rs.msgs.push(msg);
    if (!rsApi()) { rsMerge(rs, hits); rs.summary.push(q + ' → ' + (hits.length ? hits.slice(0, 2).map(function (h) { return h.title; }).join('; ') : 'nothing on the panel')); msg.a = rsDemoAnswer(q, hits); render(); return; }
    msg.a = '<span class="demo">asking the model…</span>'; render();
    var history = rs.msgs.slice(0, -1).slice(-8).map(function (m) { return { q: m.q, a: String(m.a || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 600) }; });
    rsPost({ question: q, lang: 'en', history: history }).then(function (d) {
      msg.demo = false;
      if (d.dayLeft != null) rs.left = { day: d.dayLeft, week: d.weekLeft };
      if (d.error) {
        msg.a = '<span class="demo">' + esc(RS_ERR[d.error] || ('the service answered: ' + d.error)) + (d.limit ? ' (limit ' + esc(String(d.limit)) + ')' : '') + '</span>';
        if (/^(captcha_failed|token_)/.test(d.error)) msg.needToken = true;
        rsMerge(rs, hits); msg.a += rsDemoAnswer(q, hits, 'Meanwhile, what the panel itself says:'); render(); return;
      }
      if (d.nothing_found) { msg.a = '<p><b>Nothing in our materials is close enough to this question.</b> That is an answer, not a failure: the vector search found no statement of the panel or work of ours above the threshold.</p>' + rsDemoAnswer(q, hits, 'The nearest words on the panel:'); rsMerge(rs, hits); rs.summary.push(q + ' → nothing in our materials'); render(); return; }
      if (d.unsupported) { msg.a = '<p><b>The model answered without a single supported citation, so we do not show its text.</b> Here is what was found; judge it yourself.</p>' + rsFoundList(d); rsMergeApi(rs, d); rs.summary.push(q + ' → found, but the model’s answer was not supported'); render(); return; }
      msg.a = rsRenderAnswer(d) + rsFoundList(d);
      rsMergeApi(rs, d);
      rs.summary.push(d.summary_delta ? String(d.summary_delta) : (q + ' → answered'));
      render();
    }).catch(function () { msg.a = '<span class="demo">the answer service is unreachable; showing the extracted answer</span>' + rsDemoAnswer(q, hits); rsMerge(rs, hits); render(); });
  }
  function rsFoundList(d) {
    var P = (d.panel || []).slice().sort(function (a, b) { return (b.cited ? 1 : 0) - (a.cited ? 1 : 0) || (b.score || 0) - (a.score || 0); });
    var W = (d.works || []).slice().sort(function (a, b) { return (b.cited ? 1 : 0) - (a.cited ? 1 : 0) || (b.score || 0) - (a.score || 0); });
    if (!P.length && !W.length) return '';
    return '<div class="rs-hits">' + P.slice(0, 6).map(function (p) { return '<a class="rs-hit' + (p.cited ? ' on' : '') + '" href="enso.html' + esc(p.hash || '') + '" target="_blank" rel="noopener"><b>' + esc(p.kind) + '</b>' + esc(p.title || p.id) + '</a>'; }).join('') +
      W.slice(0, 4).map(function (w) { return '<a class="rs-hit wk' + (w.cited ? ' on' : '') + '" href="' + esc(w.url || '#') + '" target="_blank" rel="noopener"><b>work</b>' + esc(w.title || w.id) + (w.no_text ? ' · link only' : '') + '</a>'; }).join('') + '</div>';
  }
  /* Сохранение: на сайте — D1 по uid через ручку; без ручки — в браузере. Доска едет внутри
     первого хода (ходы — любой JSON по договору), утверждения — резюме по ходам. */
  function rsPack(rs) {
    return { id: rs.id || undefined, lang: 'en', title: ((rs.msgs[0] || {}).q || 'research').slice(0, 160), summary: rs.summary.join('\n').slice(0, 4000),
      turns: rs.msgs.slice(0, 40).map(function (m, i) { var t = { q: m.q, a: m.a, hits: m.hits, t: m.t, demo: !!m.demo }; if (i === 0) t.board = { kpis: rs.kpis, anchors: rs.anchors, concepts: rs.concepts, links: rs.links, works: rs.works, created: rs.created, verdicts: rs.verdicts || [] }; return t; }),
      claims: rs.summary.slice(0, 40) };
  }
  function rsUnpack(rec) {
    var turns = rec.turns || [], b = (turns[0] || {}).board || {};
    return { id: rec.id, msgs: turns.map(function (t) { return { q: t.q, a: t.a, hits: t.hits || [], t: t.t, demo: !!t.demo }; }), kpis: b.kpis || [], anchors: b.anchors || [], concepts: b.concepts || {}, links: b.links || {}, works: b.works || {},
      summary: rec.claims || String(rec.summary || '').split('\n').filter(Boolean), verdicts: b.verdicts || [], created: b.created || rec.created || '', saved: rec.updated || rec.created };
  }
  function rsLocalList() { try { return JSON.parse(localStorage.getItem('b42_research') || '[]'); } catch (e) { return []; } }
  function rsLocalSave(rs) {
    var list = rsLocalList(), id = rs.id || ('r' + Date.now().toString(36)); rs.id = id;
    var item = { id: id, title: (rs.msgs[0] || {}).q || 'research', created: rs.created, saved: new Date().toISOString().slice(0, 16).replace('T', ' '), n: rs.msgs.length, rs: rs };
    var i = list.findIndex(function (x) { return x.id === id; }); if (i >= 0) list[i] = item; else list.unshift(item);
    try { localStorage.setItem('b42_research', JSON.stringify(list.slice(0, 30))); } catch (e) { }
  }
  function rsSave(rs, done) {
    if (!rsApi()) { rsLocalSave(rs); done('saved in this browser'); return; }
    fetch(rsApi() + '/save', { method: 'POST', headers: { 'content-type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify(rsPack(rs)) })
      .then(function (r) { return r.json(); }).then(function (d) { if (d && d.ok) { rs.id = d.id; rs.saved = d.updated; S._rsList = null; done('saved to your account'); } else { rsLocalSave(rs); done('server refused (' + esc(String((d || {}).error || 'error')) + '); saved in this browser'); } })
      .catch(function () { rsLocalSave(rs); done('server unreachable; saved in this browser'); });
  }
  function rsList(cb) {
    if (!rsApi()) { cb(rsLocalList().map(function (x) { return { id: x.id, title: x.title, saved: x.saved, n: x.n, local: true }; })); return; }
    if (S._rsList) { cb(S._rsList); return; }
    fetch(rsApi() + '/list', { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
      S._rsList = (d.items || []).map(function (x) { return { id: x.id, title: x.title, saved: x.updated || x.created, n: null }; }).concat(rsLocalList().map(function (x) { return { id: x.id, title: x.title, saved: x.saved, n: x.n, local: true }; }));
      cb(S._rsList);
    }).catch(function () { cb(rsLocalList().map(function (x) { return { id: x.id, title: x.title, saved: x.saved, n: x.n, local: true }; })); });
  }
  function rsOpen(id, local) {
    if (local || !rsApi()) { var it = rsLocalList().filter(function (x) { return x.id === id; })[0]; if (it) { S.rs = it.rs; render(); } return; }
    fetch(rsApi() + '/list?id=' + encodeURIComponent(id), { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) { var rec = d.item || d; if (rec && rec.turns) { S.rs = rsUnpack(rec); render(); } }).catch(function () { });
  }
  function rsDelete(id, local) {
    if (local || !rsApi()) { var l = rsLocalList().filter(function (x) { return x.id !== id; }); try { localStorage.setItem('b42_research', JSON.stringify(l)); } catch (x) { } S._rsList = null; render(); return; }
    fetch(rsApi() + '/delete', { method: 'POST', headers: { 'content-type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify({ id: id }) }).then(function () { S._rsList = null; render(); }).catch(function () { render(); });
  }
  function rsExportText(rs) {
    return 'Research on the El Niño panel · ' + rs.created + '\n\n' + rs.msgs.map(function (m, i) { return (i + 1) + '. Q: ' + m.q + '\n   A: ' + String(m.a || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); }).join('\n\n') +
      '\n\nSummary:\n' + rs.summary.map(function (l, i) { var v = (rs.verdicts || [])[i]; return (i + 1) + '. ' + l + (v && v.status ? ' [' + v.status + ']' : ''); }).join('\n') +
      '\n\nKPI: ' + rs.kpis.map(function (k) { var r = jrec(k), e = r ? r.entries || [] : [], last = e[e.length - 1]; return (r ? r.title : k) + (last ? ' ' + jval(last.v, r.digits) + ' ' + (r.unit || '') + ' (' + last.d + ')' : ''); }).join('; ') +
      '\nConcepts: ' + Object.keys(rs.concepts).map(function (id) { return cnName(rs.concepts[id]); }).join(', ') +
      '\nOn the panel: ' + Object.keys(rs.links).map(function (k) { return rs.links[k].title + ' (' + location.origin + '/enso.html' + rs.links[k].hash + ')'; }).join('; ') +
      '\nWorks: ' + Object.keys(rs.works).map(function (id) { var l = rs.works[id]; return (l.our_title || l.title) + ' [' + l.id + ']' + (l.url ? ' ' + l.url : ''); }).join('; ') + '\n';
  }
  function rsKpiTile(k) {
    var r = jrec(k), e = r ? (r.entries || []) : []; if (!r || !e.length) return '';
    var last = e[e.length - 1], prev = e.length > 1 ? e[e.length - 2] : null, dg = r.digits, u = r.unit || '';
    var dv = prev && typeof last.v === 'number' && typeof prev.v === 'number' ? last.v - prev.v : 0;
    var pay = { name: r.title, def: (prev ? 'Was ' + jval(prev.v, dg) + ' on ' + prev.d + ', now ' + jval(last.v, dg) + ' on ' + last.d + '.' : 'First reading: ' + jval(last.v, dg) + ' on ' + last.d + '.') + ' Click for the history.', src: r.src, date: last.d };
    return '<button type="button" class="ks" data-hist="' + esc(k) + '" data-src="' + esc(JSON.stringify(pay)) + '"><span class="ks-row"><span class="ks-v">' + jval(last.v, dg) + (u ? '<small>' + esc(u) + '</small>' : '') + '</span>' +
      (dv ? '<span class="ks-d ' + jsign(dv) + '">' + jarrow(dv) + (dv > 0 ? '+' : '') + jval(dv, dg) + '</span>' : '') + '</span><span class="ks-n">' + esc(STRIP_NAME[k] || r.title) + '</span></button>';
  }
  function rsWorkRow(l) {
    if (l.api) return '<p class="wk-p"><b>' + esc(l.title || l.id) + '</b>' + (l.cited ? '<i>cited by the model</i>' : '<i>found nearby</i>') + (l.url ? '<a class="wk-read" href="' + esc(l.url) + '" target="_blank" rel="noopener">Read the adapted article →</a>' : '') + ' <span class="wk-num">' + esc(l.id) + '</span></p>';
    return worksHtml([l]);
  }
  function viewResearch() {
    var rs = rsState(), live = !!rsApi();
    var body = stageShell('Research: ask in your words; the board on the left builds itself from the panel', []);
    body.setAttribute('data-own-info', '1');
    var wrap = el('div', 'rs');
    // ── доска
    var board = el('div', 'rs-board');
    var cids = Object.keys(rs.concepts), lks = Object.keys(rs.links).sort(function (a, b) { return (rs.links[b].cited ? 1 : 0) - (rs.links[a].cited ? 1 : 0); }), wks = Object.keys(rs.works).sort(function (a, b) { return (rs.works[b].cited ? 1 : 0) - (rs.works[a].cited ? 1 : 0); });
    var empty = !rs.msgs.length;
    board.innerHTML =
      '<div class="rs-h">KPI in this conversation</div>' + (rs.kpis.length ? '<div class="rs-kpis">' + rs.kpis.map(rsKpiTile).join('') + '</div>' : '<div class="rs-empty">' + (empty ? 'Ask about a number and it appears here with its arrow and history.' : 'No indicator matched yet.') + '</div>') +
      '<div class="rs-h">Concepts</div>' + (cids.length ? '<div class="cn"><span class="cn-h">concepts</span>' + cids.slice(0, 24).map(function (id) { var c = rs.concepts[id]; return '<a class="cn-c" href="' + cnUrl(id) + '" target="_blank" rel="noopener" data-src="' + cnPay(c) + '">' + esc(cnName(c)) + '</a>'; }).join('') +
        (cids.length > 24 ? '<span class="cn-c more">all ' + cids.length + ' on the graph</span>' : '') + '<button type="button" class="cn-mg" data-ids="' + esc(cids.join(',')) + '" data-focus="' + esc(cids[0]) + '">graph</button></div>' : '<div class="rs-empty">The cloud grows with every question; the graph opens on the whole set.</div>') +
      '<div class="rs-h">On the panel</div>' + (lks.length ? '<div class="rs-links">' + lks.map(function (k) { var l = rs.links[k]; return '<a href="enso.html' + esc(l.hash) + '" target="_blank" rel="noopener"' + (l.cited ? ' class="cited"' : '') + '><b>' + esc(l.kind) + '</b>' + esc(l.title) + (l.cited ? ' <i>cited</i>' : '') + ' ↗</a>'; }).join('') + '</div>' : '<div class="rs-empty">Risks, alerts and scenes the conversation touched — where to go and look.</div>') +
      '<div class="rs-h">Works we parsed</div>' + (wks.length ? '<div class="rs-works">' + wks.slice(0, 6).map(function (id) { return rsWorkRow(rs.works[id]); }).join('') + '</div>' : '<div class="rs-empty">Parsed papers attached to the same anchors.</div>') +
      '<div class="rs-h">Summary of the conversation</div>' + (rs.summary.length ? '<div class="rs-sum"><ol>' + rs.summary.map(function (l, i) { var v = (rs.verdicts || [])[i]; return '<li>' + esc(l) + (v && v.status ? ' <span class="rs-v ' + esc(v.status) + '" data-src="' + esc(JSON.stringify({ name: 'Checked by the model: ' + v.status, def: v.why || '' })) + '">' + esc(v.status) + '</span>' : '') + '</li>'; }).join('') + '</ol></div>' : '<div class="rs-empty">One line per turn; “verify” sends the lines back to the model to check them against the sources.</div>') +
      '<div class="rs-btns"><button type="button" class="rs-btn" data-rs="verify"' + (rs.msgs.length && live ? '' : ' disabled') + '>verify with the model</button><button type="button" class="rs-btn main" data-rs="save"' + (rs.msgs.length ? '' : ' disabled') + '>' + (rs.id ? 'saved ✓ · save again' : 'save this research') + '</button><button type="button" class="rs-btn" data-rs="copy"' + (rs.msgs.length ? '' : ' disabled') + '>copy as text</button><button type="button" class="rs-btn" data-rs="new">new research</button><span class="rs-note"></span></div>' +
      '<div class="rs-h">Saved research</div><div class="rs-saved"><div class="rs-empty">loading…</div></div>';
    rsList(function (items) {
      var host = board.querySelector('.rs-saved'); if (!host) return;
      host.innerHTML = items.length ? items.map(function (x) { return '<div class="it"><span class="t">' + esc(x.title || 'research') + '</span><span class="m">' + esc(String(x.saved || '').slice(0, 16)) + (x.n ? ' · ' + x.n + ' turn' + (x.n > 1 ? 's' : '') : '') + (x.local ? ' · this browser' : '') + '</span><button type="button" class="rs-btn" data-rs="open" data-id="' + esc(x.id) + '"' + (x.local ? ' data-local="1"' : '') + '>open</button><button type="button" class="rs-btn" data-rs="del" data-id="' + esc(x.id) + '"' + (x.local ? ' data-local="1"' : '') + '>✕</button></div>'; }).join('')
        : '<div class="rs-empty">' + (live ? 'Nothing saved yet. Saved research lives in your account (or this session) on the server, up to 50.' : 'Nothing saved yet. Without the server this browser keeps the copy.') + '</div>';
    });
    board.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-rs]'); if (!b) return;
      var op = b.getAttribute('data-rs'), note = board.querySelector('.rs-note');
      if (op === 'save') { b.textContent = 'saving…'; rsSave(rs, function (m) { if (note) note.textContent = m; render(); }); }
      else if (op === 'new') { S.rs = null; render(); }
      else if (op === 'copy') { var txt = rsExportText(rs); (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(function () { b.textContent = 'copied ✓'; }, function () { window.prompt('Copy the text:', txt); }); }
      else if (op === 'open') rsOpen(b.getAttribute('data-id'), !!b.getAttribute('data-local'));
      else if (op === 'del') rsDelete(b.getAttribute('data-id'), !!b.getAttribute('data-local'));
      else if (op === 'verify') {
        b.textContent = 'verifying…';
        rsPost({ mode: 'verify', lang: 'en', claims: rs.summary.slice(0, 40) }).then(function (d) {
          if (d.error) { b.textContent = RS_ERR[d.error] ? 'not verified: ' + RS_ERR[d.error] : 'verification failed'; return; }
          var V = d.verdicts || []; rs.verdicts = rs.summary.map(function (_, i) { return V.filter(function (v) { return v.n === i + 1; })[0] || V[i] || null; });
          if (d.dayLeft != null) rs.left = { day: d.dayLeft, week: d.weekLeft };
          render();
        }).catch(function () { b.textContent = 'verification failed'; });
      }
    });
    // ── диалог
    var chat = el('div', 'rs-chat');
    var log = el('div', 'rs-log');
    log.innerHTML = (rs.msgs.length ? rs.msgs.map(function (m) {
      return '<div class="rs-m q"><span class="rs-t">' + esc(m.t || '') + '</span>' + esc(m.q) + '</div><div class="rs-m a">' + (m.a || '') + (m.demo && m.hits && m.hits.length ? '<div class="rs-hits">' + m.hits.slice(0, 5).map(function (h) { return '<span class="rs-hit"><b>' + esc(h.kind) + '</b>' + esc(h.title) + '</span>'; }).join('') + '</div>' : '') + (m.needToken ? '<button type="button" class="rs-btn" data-rs-token="1">enter an access token</button>' : '') + '</div>';
    }).join('') : '<div class="rs-m a"><p>Ask about the event in your own words. The question goes to the model with our own materials: the statements of this panel (risks, alerts, indicators, glossary, scenes, the news of the week, regions, the verdict) and the works we parsed. The answer carries marks that lead to the panel or to the work; the board on the left collects the numbers, concepts, scenes and papers involved, and keeps a summary you can verify and save.</p><p>Try: <i>is the event still growing or has it turned?</i> · <i>why is the fuel at its record?</i> · <i>what do the models expect for winter?</i> · <i>what happens to food prices?</i></p>' +
      (live ? '' : '<span class="demo">demo mode on this server: no model behind the answers; the retrieval and the board are real, the answer service lives on the site</span>') + '</div>');
    var inp = el('div', 'rs-in');
    var ta = document.createElement('textarea'); ta.placeholder = 'Ask about the event…'; ta.rows = 2;
    var go = el('button', 'rs-btn main', 'Ask'); go.type = 'button';
    function send() { var q = ta.value.trim(); if (q.length < 3) { ta.focus(); return; } ta.value = ''; rsAsk(q); }
    go.onclick = send;
    ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
    inp.appendChild(ta); inp.appendChild(go);
    chat.appendChild(log); chat.appendChild(inp);
    var foot = el('div', 'rs-quota');
    foot.innerHTML = (rs.left ? 'questions left: ' + esc(String(rs.left.day)) + ' today' + (rs.left.week != null ? ' · ' + esc(String(rs.left.week)) + ' this week' : '') + ' · ' : '') + (live ? (rsToken() ? 'access token in use · <a href="#" data-rs-token="1">change</a>' : 'no token: “not a robot” pass on every question · <a href="#" data-rs-token="1">enter a token</a>') : 'demo, no server');
    chat.appendChild(foot);
    chat.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-rs-token]'); if (!b) return;
      e.preventDefault();
      var t = window.prompt('Access token for the panel (issued for a period, with a daily allowance). Leave empty to remove:', rsToken() || '');
      if (t !== null) { rsSetToken(t.trim()); render(); }
    });
    wrap.appendChild(board); wrap.appendChild(chat);
    body.appendChild(wrap);
    requestAnimationFrame(function () { log.scrollTop = log.scrollHeight; if (!rs.msgs.length) ta.focus(); });
  }

  function railState() {
    var D = S.D, N = D.nino34, NW = D.noaa, ONI = D.oni, sm = D.summary || {}, P = S.P;
    var col = $('railL'); col.innerHTML = '';
    var t = tile('State', term('type', 'event type: ' + NW.type) + cnBtn(['kpi:risk_index', 'term:riskindex', 'block:type', 'term:type'], 'graph') + railFullBtn('L'), 'grow');
    var idx = D.risk_index, gc = idx >= 80 ? 'var(--lv5)' : (idx >= 60 ? 'var(--lv4)' : (idx >= 40 ? 'var(--lv3)' : 'var(--ok)'));
    var ls = ONI.last_season;
    var ri = pair(idx, P ? P.risk_index : null, 0);
    var box = el('div', 'cards');

    // 1. KPI-карточка состояния
    var k1 = el('div', 'card kpi-card');
    // Подпись шкалы стоит СНАРУЖИ круга: внутри она не помещалась и обрезалась
    // (владелец 03.09: «в кружок текст не поместился, вынеси его»).
    k1.innerHTML = '<div class="gauge-row"><div class="gauge' + (idx >= 70 ? ' hot' : '') + '" data-term="riskindex" style="--v:' + idx + ';--c:' + gc + '"><div class="gv">' + idx + '</div></div>' +
      '<div class="g-side">' + '<button type="button" class="vgo" data-view="verdict">read the verdict →</button>' + '<b>' + zone('nino34') + ' ' + fnum(NW.latest.n34a, 1) + ' °C' + jchip('n34_weekly') + '</b>' +
      /* Каждое утверждение — своей строкой и без точки в конце (владелец 07.09:
         «точки после предложений на карточках убрать, просто перенос строки»). */
      '<div class="ln">rank ' + N.all_years_rank + ' of all years on the same 30 days</div>' +
      '<div class="ln">' + ab('oni', 'ONI') + ' ' + fnum(ONI.current[ls]) + ' ' + ab('seasons', ls) + jchip('oni') + '</div>' +
      '' + kmeta('risk_index') + freshLine() +
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
      var c3 = el('div', 'card models-card'); c3.setAttribute('data-anchor', 'block:models');
      c3.innerHTML = '<div class="ch"><b>MODELS</b><span class="kk">since ' + esc(first.issue) + '</span></div>' +
        '<div class="ct">' + last.share + ' % of models are below reality, against ' + first.share + ' % a year ago</div>' +
        '<div class="cd">Verified on ' + rows.length + ' issues: for each we take its nearest season that already has an official ONI. The average model error went ' +
        fnum(first.mean_err) + ' → ' + fnum(last.mean_err) + ' °C.</div>' +
        (chronic.length ? '<div class="cd chronic">Below reality in most issues: ' + chronic.slice(0, 5).map(function (c) { return modelSpan(c.model, c.model) + ' ' + c.issues_low + '/' + c.of; }).join(', ') + '</div>' : '') +
        (rv && rv.combined_peak_prev != null ? '<div class="cd">Since the ' + esc(rv.prev_issued || '') + ' issue the combined peak went ' + fnum(rv.combined_peak_prev) + ' → ' + fnum(rv.combined_peak_cur) + ' °C; ' + rv.n_up + ' of ' + rv.n + ' models raised it. The next issue is due around the 19th.</div>' : '') +
        '<div class="spark">' + sparkBars(rows) + '</div>' +
        '<div class="cgo" data-go="models" data-gosub="breakdown">see how they break \u2192</div>' + linksHtml('block:models') + cnBtn('block:models', 'graph');
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
    var t = tile('Risks', risks.length + ' · index ' + D.risk_index + (P ? ' ' + chg(D.risk_index, P.risk_index, 0) : '') + cnBtn(risks.map(function (r) { return 'risk:' + (r.id || ''); }), 'graph') + railFullBtn('R'), 'grow');
    t._b.classList.add('flush');
    var box = el('div'); box.style.padding = '0 10px 8px';
    risks.forEach(function (r, i) {
      /* Стрелка на карточке риска — из журнала, по имени риска, а не по заголовку: заголовок
         может смениться, уровень должен идти подряд (владелец 04.09). */
      var jr = jrec('risk:' + (r.id || '')), je = jr ? (jr.entries || []) : [];
      var wasJ = je.length > 1 ? je[je.length - 2] : null;
      /* Сравнение по имени риска; по заголовку — только для снимков до 03.09, где имени нет
         (владелец 06.09: число в заголовке меняется с данными, риск не должен становиться «new»). */
      var was = P && P.risks ? (P.risks[r.id] != null ? P.risks[r.id] : P.risks[r.title]) : null;
      var c = el('div', 'risk' + (S.risk === i ? ' on' : '')); c.setAttribute('data-anchor', 'risk:' + (r.id || ''));
      c.innerHTML = '<div class="rl" style="background:' + lvlColor(r.level) + '">' + r.level + '</div>' +
        '<div><div class="rt">' + mark(r.title) + (was == null && P ? ' <span class="new">new</span>' : '') + '</div>' +
        '<div class="rh">' + esc(r.horizon) + (wasJ ? ' · <span class="' + jsign(r.level - wasJ.v) + '">' + jarrow(r.level - wasJ.v) + ' was ' + wasJ.v + ' on ' + esc(wasJ.d) + '</span>' : '') + (r.metric ? ' · ' + esc(r.metric.name) : '') + '</div>' +
        (r.metric ? '<div class="rs">' + spark(r.metric, 200, 24) + '</div>' : '') +
        '<div class="rf">' + (linksHtml('risk:' + (r.id || '')) || '') + cnBtn('risk:' + (r.id || ''), 'graph') + (jr ? '<button type="button" class="jh" data-hist="risk:' + esc(r.id) + '">history</button>' : '') +
        dateBadge(null, (r.metric ? r.metric.name : 'this rule'), (r.metric && r.metric.dates ? String(r.metric.dates[r.metric.dates.length - 1]) : (je.length ? je[je.length - 1].d : '')), r.title) + '</div></div>';
      hlConcepts(c.querySelector('.rt'), 'risk:' + (r.id || ''));
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
    /* КНОПКА ВОЗВРАТА. Владелец 06.09: «когда я с обзора ухожу на соответствующую страницу,
       там нет кнопки назад, чтобы вернуться». Кнопка появляется только если пришли с
       обзора, и уводит ровно туда же, откуда пришли. */
    var top = el('div', 'stage-top');
    top.appendChild(el('div', 'stage-h', title));
    /* Владелец 07.09: «яркую кнопку back в правом верхнем углу поля графиков». Кнопка стоит
       всегда, когда есть куда вернуться: с обзора — на обзор, иначе на прошлую сцену
       (по истории адреса, как браузерная «назад»). */
    if ((S._back && S.view !== 'overview') || S._navN > 0) {
      // класс vgo НЕ ставим: на нём висит общий обработчик переходов, и он уводил в «now»
      var b = el('button', 'back-go bright', '← ' + (S._back && S.view !== 'overview' ? (T.tabs.overview || 'Overview') : 'back'));
      b.type = 'button';
      /* Возврат идём через адрес, а не прямой сменой состояния: с карточки риска прямая
         смена приводила на «Where we are» (viewRisk при пустом S.risk сам уводит в now, и
         порядок вызовов внутри render это подхватывал). Через хэш путь один и тот же, что
         у кнопки «назад» браузера. */
      var toOverview = S._back && S.view !== 'overview';
      b.onclick = function () {
        S.full = null; S.risk = null; S.pick = null;
        if (toOverview) { S._back = null; if ((location.hash || '') === '#overview') { S.view = 'overview'; render(); } else location.hash = '#overview'; return; }
        S._navN = Math.max(0, (S._navN || 0) - 2);   // шаг назад по истории сам вызовет render через hashchange
        history.back();
      };
      top.appendChild(b);
    }
    /* ⛶ у любой сцены, справа от back (владелец 07.09) */
    var narrowFb = window.matchMedia('(max-width:700px)').matches;
    var fb = el('button', 'back-go bright', S.full ? (narrowFb ? '✕' : '✕ full screen') : '⛶'); fb.type = 'button'; fb.title = S.full ? 'back to three columns (Esc)' : 'this scene full screen';
    fb.onclick = function () { S.full = !S.full; render(); };
    if (globeMode()) {
      var gb = el('button', 'back-go bright' + (S.globe ? ' on' : ''), S.globe ? '🌐 flat' : '🌐 globe'); gb.type = 'button';
      gb.title = S.globe ? 'back to the flat view' : 'the same on a globe (pilot)';
      gb.onclick = function () { S.globe = !S.globe; render(); };
      top.appendChild(gb);
    }
    top.appendChild(fb);
    head.appendChild(top);
    /* Владелец 08.09: «source и notes в подменю первой строкой слева, справа back, globe,
       потом со следующей строки само подменю». Заголовок остаётся один в своей строке;
       кнопки уходят в строку управления, source/notes в неё же вешает sceneInfoBar. */
    var ctl = el('div', 'stage-ctl'), nav = el('div', 'ctl-nav');
    ctl.appendChild(el('div', 'seg ctl-info'));
    [].slice.call(top.querySelectorAll('.back-go')).forEach(function (b) { nav.appendChild(b); });
    ctl.appendChild(nav);
    top.appendChild(ctl);                     // в той же строке, что заголовок (владелец 08.09, вторая правка)
    requestAnimationFrame(fitStageTitle); setTimeout(fitStageTitle, 120);
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
      var lt = e.target.closest && e.target.closest('[data-legtoggle]');
      if (lt) { S.legOpen = !S.legOpen; S.pw = 0; redrawPlot(); return; }   // размер не менялся — сбрасываем кэш размера
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
  /* ЗАГОЛОВКИ ГРАФИКОВ НЕ ОБРЫВАЮТСЯ И НЕ ЛЕЗУТ ПОД КНОПКУ (владелец 07.09, дважды).
     Оценка «сколько знаков влезет» врала: у одного и того же кегля буквы разной ширины,
     и текст уезжал за край. Здесь он меряется по-настоящему, уже в документе
     (getComputedTextLength), кегль уменьшается 12 → 7.5, и только если и этого мало —
     режется. Заодно единственный заголовок прижимается к левому краю поля, а справа
     оставляется место под кнопку «legend», если она на этом графике есть. */
  /* ГОД ДВУМЯ ЦИФРАМИ ВЕЗДЕ (владелец 07.09: «год нужно везде писать только 26»), а месяц —
     словом: подписи осей приводятся к одному виду уже в готовой картинке, чтобы не править
     два десятка сборщиков. «2026» → «'26», «2026-01» → «Jan '26». */
  function tidyAxisText(t) {
    var v = (t.textContent || '').trim(), m;
    if ((m = v.match(/^(19|20)(\d{2})$/))) { t.textContent = "'" + m[2]; return; }
    if ((m = v.match(/^(19|20)(\d{2})-(\d{2})$/))) { t.textContent = MON3[+m[3] - 1] + " '" + m[2]; return; }
    if ((m = v.match(/^(19|20)(\d{2})-(\d{2})-(\d{2})$/))) { t.textContent = MON3[+m[3] - 1] + ' ' + (+m[4]); return; }
    if ((m = v.match(/^(19|20)(\d{2})[–-](19|20)?(\d{2})$/))) { t.textContent = "'" + m[2] + '–' + m[4]; return; }
    // «Jul 2026» и «6 Sep 2026» — тот же вид, что и остальные даты
    if (v.length <= 14 && (m = v.match(/^(.*?)(19|20)(\d{2})$/)) && /[A-Za-z]/.test(m[1])) t.textContent = m[1].trim() + " '" + m[3];
  }

  /* ПЛИТКА ОБЗОРА — ТОЛЬКО ЛИНИЯ (владелец 07.09: «никаких надписей на миниграфиках; тексты
     was… after… наезжают друг на друга, убери их в легенду; на осях оставь начальную и
     конечную, кегль уменьши»). Разбор по месту: подписи осей узнаются по геометрии (низ поля
     и левая колонка), всё словесное внутри поля снимается — это пояснения, у них есть своё
     место в подсказке плитки и на большой сцене. */
  function tidyTileSvg(svg, W, H) {
    var texts = [].slice.call(svg.querySelectorAll('text'));
    var bottom = [], left = [];
    texts.forEach(function (t) {
      var x = parseFloat(t.getAttribute('x')) || 0, y = parseFloat(t.getAttribute('y')) || 0;
      var v = (t.textContent || '').trim();
      // длинная подпись внизу — не ось, а пояснение шкалы: в плитке ей места нет
      if (y > H - 22) { if (v.length > 12 || v.indexOf('·') >= 0) t.remove(); else bottom.push({ t: t, x: x }); return; }
      if (x < 62 && (t.getAttribute('text-anchor') || '') === 'end') { left.push({ t: t, y: y }); return; }
      // внутри поля оставляем только числа: слова — это пояснения
      if (/[A-Za-zА-Яа-я]{3}/.test(v) || t.classList.contains('tt')) t.remove();
    });
    function thin(arr, key) {
      if (arr.length < 3) return;
      arr.sort(function (p, q) { return p[key] - q[key]; });
      arr.forEach(function (o, i) { if (i !== 0 && i !== arr.length - 1) o.t.remove(); });
    }
    thin(bottom, 'x'); thin(left, 'y');
    [].forEach.call(svg.querySelectorAll('text'), function (t) { t.style.fontSize = '8px'; });
    /* ПУСТЫЕ ПОЛЯ СЛЕВА И СПРАВА (владелец 07.09: «много места пропадает, график должен идти
       по полной ширине с учётом подписей оси»). Поля закладывались под подписи и легенду,
       которых в плитке больше нет. Вместо правки двадцати сборщиков подрезаем окно картинки
       по тому, что в ней действительно нарисовано: viewBox = рамка содержимого, и рисунок
       сам растягивается на всю плитку. */
    try {
      var bb = svg.getBBox();
      if (bb.width > 20 && bb.height > 10) {
        svg.setAttribute('viewBox', (bb.x - 2).toFixed(1) + ' ' + (bb.y - 2).toFixed(1) + ' ' +
          (bb.width + 4).toFixed(1) + ' ' + (bb.height + 4).toFixed(1));
        /* Тянем по обеим осям только ряды и сетки: у карты искажались бы очертания суши,
           поэтому географию (много многоугольников) оставляем в своих пропорциях. */
        var geo = svg.querySelectorAll('polygon').length > 3;
        svg.setAttribute('preserveAspectRatio', geo ? 'xMidYMid meet' : 'none');
        [].forEach.call(svg.querySelectorAll('text'), function (t) {
          t.style.fontSize = (8 * bb.width / (W || bb.width)).toFixed(1) + 'px';   // кегль обратно к 8 на экране
        });
      }
    } catch (e) { /* картинка ещё не в документе — оставляем как есть */ }
  }

  function fitSvgTitles(host, tight) {
    if (!host) return;
    [].forEach.call(host.querySelectorAll('svg'), function (svg) {
      var vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/), W = parseFloat(vb[2]) || 0;
      if (!W) return;
      [].forEach.call(svg.querySelectorAll('text'), tidyAxisText);
      if (tight) { tidyTileSvg(svg, W, parseFloat(vb[3]) || 0); return; }
      var tts = [].slice.call(svg.querySelectorAll('text.tt'));
      if (!tts.length) return;
      var hasLeg = !!svg.querySelector('[data-legtoggle]');
      /* Сосед справа мешает только если он на ТОЙ ЖЕ строке: у разреза и недельных индексов
         подписи мини-панелей тоже помечены как заголовки, но лежат ниже (07.09). */
      var pos = tts.map(function (t) { return { t: t, x: parseFloat(t.getAttribute('x')) || 0, y: parseFloat(t.getAttribute('y')) || 0 }; });
      pos.sort(function (p, q) { return p.y - q.y || p.x - q.x; });
      var topY = pos[0].y, alone = pos.filter(function (q) { return Math.abs(q.y - topY) < 8; }).length === 1;
      pos.forEach(function (o) {
        var t = o.t, x = o.x;
        if ((t.getAttribute('text-anchor') || '') === 'end') return;   // подпись у правого края — не заголовок
        if (alone && Math.abs(o.y - topY) < 8 && x > 8) { x = 8; t.setAttribute('x', 8); }
        var near = pos.filter(function (q) { return q !== o && Math.abs(q.y - o.y) < 8 && q.x > x; });
        var next = near.length ? Math.min.apply(null, near.map(function (q) { return q.x; })) : 0;
        var avail = next ? next - x - 10 : W - x - (hasLeg && Math.abs(o.y - topY) < 8 ? 86 : 8);
        if (avail <= 20) return;
        /* Кегль задаём СТИЛЕМ, а не атрибутом: правило .plot svg text{font-size:11px} сильнее
           презентационного атрибута, и уменьшение молча не срабатывало (07.09). */
        var px = parseFloat(getComputedStyle(t).fontSize) || parseFloat(t.getAttribute('font-size')) || 12, len = 0;
        try { len = t.getComputedTextLength(); } catch (e) { return; }
        while (len > avail && px > 7) { px -= .5; t.style.fontSize = px + 'px'; try { len = t.getComputedTextLength(); } catch (e) { return; } }
        if (len > avail) {
          var full = t.textContent, k = Math.max(4, Math.floor(full.length * avail / len) - 1);
          t.textContent = full.slice(0, k).replace(/[\s,;:.\u2014-]+$/, '') + '…';
          t.setAttribute('title', full);
        }
      });
    });
  }

  function redrawPlot() {
    var p = S.plotEl;
    if (!p || !S.draw || !p.isConnected) return;
    S._chartW = p.clientWidth || 0;
    var badge = p.querySelector('.dcal-wrap');
    var w = Math.max(220, Math.round(p.clientWidth)), h = Math.max(150, Math.round(p.clientHeight));
    if (w === S.pw && h === S.ph) return;
    S.pw = w; S.ph = h;
    /* ЗАГОЛОВОК ГРАФИКА РЕЖЕТСЯ ПО ШИРИНЕ — ОДНИМ МЕСТОМ НА ВСЕ ГРАФИКИ. Текст в SVG не
       переносится и не обрезается сам: на телефоне подписи уезжали за правый край. Править
       четырнадцать мест сборки строк — напрашиваться на опечатку (одну уже поймали), поэтому
       чиним готовую картинку: у заголовка своя примета (class="tt" на строке y="13"), и
       только он подрезается по числу знаков, которые влезают. */
    S._legItems = null;
    p.innerHTML = String(S.draw(w, h));
    fitSvgTitles(p);                            // заголовок меряется по-настоящему, уже в документе
    if (badge) p.appendChild(badge);           // значок даты данных переживает перерисовку
    syncLegendBar();
  }
  function legSwatch(it) {
    var col = it[1] || 'var(--soft)';
    if (it[2] === 'dot') return '<svg viewBox="0 0 24 10" width="24" height="10" aria-hidden="true"><circle cx="12" cy="5" r="4" style="fill:' + col + '"/></svg>';
    if (it[2] === 'box') return '<svg viewBox="0 0 24 10" width="24" height="10" aria-hidden="true"><rect x="1" y="1" width="22" height="8" rx="2" style="fill:' + col + '" opacity="' + (it[3] || 1) + '"/></svg>';
    return '<svg viewBox="0 0 24 10" width="24" height="10" aria-hidden="true"><line x1="1" y1="5" x2="23" y2="5" style="stroke:' + col + '" stroke-width="' + (it[2] || 2) + '"' + (it[3] ? ' stroke-dasharray="' + it[3] + '"' : '') + '/></svg>';
  }
  function syncLegendBar() {
    var head = document.querySelector('.stage-head'), ci = head && head.querySelector('.ctl-info');
    var old = head && head.querySelector('.leg-bar'); if (old) old.remove();
    var items = S._legItems || [], btn = ci && ci.querySelector('.legbtn');
    if (!items.length || !ci) { if (btn) btn.remove(); return; }
    if (!btn) {
      btn = el('button', 'sq legbtn', ''); btn.type = 'button';
      btn.onclick = function () { S.legOpen = !S.legOpen; S.pw = 0; redrawPlot(); };
      ci.appendChild(btn);
    }
    btn.className = 'sq legbtn' + (S.legOpen ? ' on' : ''); btn.textContent = 'legend ' + (S.legOpen ? '▴' : '▾');
    if (!S.legOpen) return;
    var bar = el('div', 'leg-bar');
    items.forEach(function (it) {
      if (!it || !it[0]) { bar.appendChild(el('span', 'leg-sep', '')); return; }
      var c = el('span', 'leg-c' + (it[4] ? ' pick' : '') + (it[4] && S.pick === it[4] ? ' on' : ''), legSwatch(it) + esc(String(it[0])));
      if (it[4]) c.setAttribute('data-pick', it[4]);
      bar.appendChild(c);
    });
    bar.addEventListener('click', function (e) {
      var g = e.target.closest && e.target.closest('[data-pick]'); if (!g) return;
      var v = g.getAttribute('data-pick'); S.pick = (S.pick === v || !v) ? null : v; render();
    });
    head.appendChild(bar);
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
  function jarrow(dv) { return dv > 0 ? '↑' : (dv < 0 ? '↓' : '±'); }
  function jval(v, dg) { return (typeof v === 'number') ? v.toFixed(dg == null ? 2 : dg) : esc(String(v)); }
  function jdelta(a, b, dg) {
    // Не всякий показатель — число: «сценарий в силе» это слово. Для слов стрелка не имеет
    // смысла, и мы показываем сам переход, а не разность.
    if (typeof a !== 'number' || typeof b !== 'number')
      return '<b class="same">' + esc(String(b)) + ' → ' + esc(String(a)) + '</b>';
    var dv = a - b;
    if (dv === 0) return '<b class="same" title="unchanged">±0</b>';
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
      return out + '<div class="jsrc"><span>' + mark(src0 || '') + (date0 ? ' · ' + dt(date0) : '') + '</span>' + dateBadge(null, src0, date0) + '</div></div>';
    }
    var e = r.entries || [], last = e[e.length - 1], prev = e[e.length - 2], dg = r.digits;
    function moved(a, b) { return typeof a === 'number' && typeof b === 'number' ? a !== b : a !== b; }
    if (last && prev && moved(last.v, prev.v)) out += '<div class="jr">' + jdelta(last.v, prev.v, dg) + ' since ' + dt(prev.d) + '</div>';
    if (last && r.since_event && moved(last.v, r.since_event.v))
      out += '<div class="jr">' + jdelta(last.v, r.since_event.v, dg) + ' since the event began, ' + dt(r.since_event.d) + '</div>';
    /* СТРОКА ИСТОЧНИКА — ТОЖЕ ПОДСКАЗКА, И БЕЗ ОБРЫВА. Владелец 04.09: «что там за многоточия
       в тексте, немного почётче пиши». Многоточие рисовала обрезка по ширине: длинное имя
       источника не влезало в строку кирпича. Теперь подпись переносится и сама стала якорем:
       по наведению видно, что это за ряд, откуда он и за какое число. */
    var srcPay = { name: r.title || k,
      def: (r.title || k) + ' — the series behind this number. ' +
        (r.since_event ? 'Since the event began (' + r.since_event.d + '): ' + jval(r.since_event.v, dg) + '. ' : '') +
        ((r.entries || []).length > 1 ? 'We hold ' + r.entries.length + ' changes of this value.'
          : 'This is the first reading we hold.'),
      src: r.src || '', date: last ? last.d : '', lk: 'kpi:' + k };   // якорь облака понятий (08.09)
    out += '<div class="jsrc" data-kpi="' + esc(k) + '"><span data-src="' + esc(JSON.stringify(srcPay)) + '">' + mark(r.src || '') +
      (last ? ' · ' + dt(last.d) : '') + '</span>' +
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
    return ' <span class="' + jsign(dv) + ' jc" data-hist="' + esc(k) + '" data-src="' + esc(JSON.stringify({ name: r.title, def: 'Was ' + prev.v + ' on ' + prev.d + ', now ' + last.v + ' on ' + last.d + '. The arrow follows changes of the data, not our refreshes. Click for the history.', src: r.src, date: last.d })) + '">' +
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
      /* Подписи колонок: без них столбик чисел и стрелок читался как одно месиво
         (владелец 06.09: «не понятно расположено до конца»). */
      '<table class="htab"><tr class="hh"><td>date of the data</td><td class="v">value</td>' +
      '<td class="a">change</td></tr>' + rows.map(function (x, i) {
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
          /* Поправка к старому вердикту: запись остаётся, под ней сказано, что было неверно и как
             на самом деле (data/enso/verdict-corrections.json через журнал; владелец 06.09). */
          (x.correction ? '<div class="note warn" style="margin-top:6px"><strong>Correction' + (x.corrected_on ? ' (' + esc(x.corrected_on) + ')' : '') + '.</strong> ' + esc(x.correction) + '</div>' : '') +
          '<div class="s">risk index ' + (x.risk_index == null ? '\u2014' : x.risk_index) + ' \u00b7 ' + esc(x.model || '') + '</div></div>';
      }).join('');
      body.appendChild(g);
      body.appendChild(el('div', 'cap', 'Only the changes are kept: the model writes a verdict on every update, but while the numbers stay put it repeats itself word for word. ' +
        vs.length + ' distinct verdicts are stored.'));
      return;
    }

    var tp = sm.turning_point || {}, cav = Array.isArray(sm.caveats) ? sm.caveats : (sm.caveats ? [sm.caveats] : []);
    var lead = el('div', 'lead');
    /* Две подписи в шапке: кто написал и кто проверил. Пояснение — в подсказке у каждой,
       чтобы читатель понимал, что одна модель пишет, а другая сверяет (владелец 06.09). */
    var wPay = { name: CREW.writer + ' \u2014 writes', def: 'Writes this verdict from the numbers on this page: the rules extract the facts, the model puts them into words. It may choose what to talk about; it may not invent a number or change its meaning.', src: 'our pipeline', date: (S.D.stamp || '').slice(0, 10) };
    var st0 = reviewState();
    var cPay = { name: CREW.supervisor + ' \u2014 checks', def: 'Reads every claim of the verdict against the same numbers, sharpens the wording where it is unclear, and writes nothing of its own. ' + (st0.done ? 'This verdict has been checked.' : 'This verdict has not been checked yet: ' + st0.why + '.'), src: 'our pipeline', date: st0.done ? (st0.rv.at || '').slice(0, 10) : (S.D.stamp || '').slice(0, 10) };
    lead.innerHTML = '<b>' + (sm.error ? 'By rules, without the model'
      : '<span data-src="' + esc(JSON.stringify(wPay)) + '">' + esc(sm.model || 'model') + '</span> writes, <span data-src="' + esc(JSON.stringify(cPay)) + '">' + esc(CREW.supervisor) + '</span> checks') + ':</b> ' + mark(sm.verdict || '');
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
      '<div class="kpi"><div class="kn">who wrote and who checked</div>' +
      '<div class="kv crew"><span class="cr-r">writes</span> ' + esc(sm.model || 'rules') + '<br>' +
      '<span class="cr-r">checks</span> ' + esc(CREW.supervisor) + '</div>' +
      '<div class="km">' + (sm.error ? esc(sm.error)
        : 'The rules pull the facts, ' + esc(CREW.writer) + ' puts them into words and may not invent a number; ' +
          esc(CREW.supervisor) + ' reads every claim against the same numbers and sharpens the wording. ' + reviewLine()) +
      '</div>' + kmeta(null, 'our pipeline', (D.stamp || '').slice(0, 10)) + '</div>';
    body.appendChild(kp);
    body.appendChild(el('div', 'cap', 'The verdict is an interpretation of our own numbers by a language model, not a source. Every claim in it can be checked on the scene it came from \u2014 the buttons above lead there. Two models work here and neither measures anything: ' + esc(CREW.writer) + ' writes the verdict from the numbers, ' + esc(CREW.supervisor) + ' checks it against the same numbers before it is published and says so above. When the writing model is unavailable, the same block is filled by rules and says so.'));
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
      /* НЕДЕЛЯ ЗА НЕДЕЛЕЙ (владелец 07.09: «с анимацией супер наглядно, примени где ещё можно»):
         те же участки, но по неделям последних двадцати, рядом та же неделя года-сравнения
         (analog_series выровнен по концу ряда на ту же неделю года). Кадр = подмена latest. */
      var ser = NW.series || [], AS = (NW.analog_series || {})[cmp] || [], nF = Math.min(ser.length, AS.length || ser.length), off = ser.length - nF;
      if (S.mapI == null || S.mapI >= nF) S.mapI = nF - 1;
      function frameNW(i) {
        var wk = ser[off + i], aw2 = {}; aw2[cmp] = AS[i + (AS.length - nF)] || {};
        return Object.assign({}, NW, { date: wk.date, latest: wk, analog_week: Object.assign({}, NW.analog_week || {}, aw2) });
      }
      var prow = el('div', 'seg sub');
      var bPlay = el('button', 'sq', '▶ play the weeks'); bPlay.type = 'button';
      var rng = document.createElement('input'); rng.type = 'range'; rng.min = 0; rng.max = nF - 1; rng.value = S.mapI; rng.style.cssText = 'flex:1;min-width:120px;max-width:320px;align-self:center';
      var lab = el('span', 'mono', 'week of ' + (ser[off + S.mapI] || {}).date); lab.style.cssText = 'align-self:center;font-size:12px;min-width:120px';
      function showFrame() { lab.textContent = 'week of ' + (ser[off + S.mapI] || {}).date; rng.value = S.mapI; S.pw = 0; redrawPlot(); }
      bPlay.onclick = function () {
        if (S.animT) { animStop(); bPlay.textContent = '▶ play the weeks'; bPlay.className = 'sq'; return; }
        if (S.mapI >= nF - 1) S.mapI = 0;
        S.animT = setInterval(function () {
          if (!S.plotEl || !S.plotEl.isConnected) { animStop(); return; }
          S.mapI = (S.mapI + 1) % nF; showFrame();
          if (S.mapI === nF - 1) { animStop(); bPlay.textContent = '▶ play the weeks'; bPlay.className = 'sq'; }
        }, 600);
        bPlay.textContent = '❚❚ pause'; bPlay.className = 'sq on';
      };
      rng.oninput = function () { animStop(); bPlay.textContent = '▶ play the weeks'; bPlay.className = 'sq'; S.mapI = +rng.value; showFrame(); };
      prow.appendChild(bPlay); prow.appendChild(rng); prow.appendChild(lab);
      body.appendChild(prow);
      plot(body, function (w, h) { return pacific(nF && S.mapI < nF - 1 ? frameNW(S.mapI) : NW, w, h); });
      // поле карты держит форму 2:1, иначе в полном экране вокруг неё пустота
      if (S.plotEl) S.plotEl.classList.add('map-fit');
      /* Под картой ещё два ряда кнопок и четыре плашки: на невысоком экране они не влезают
         и сцена их обрезала (владелец 06.09: «карточки внизу вышли за пределы экрана»).
         Карта ужимается первой, а если и этого мало — тело сцены прокручивается. */
      body.classList.add('scroll');
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
    /* ТОЧКИ СУШИ КАК У NIÑO 3.4 (владелец 07.09): те же кирпичи watch, данные regions-daily.json. */
    var RD = (S.RD || {}).series || {}, RDK = Object.keys(RD);
    var RNAME = LAND_NAME;
    var opts = [['sst_nino34', 'Niño 3.4'], ['sst_world', 'Ocean'], ['t2_world', 'Land+ocean']].concat(RDK.map(function (q) { return [q, RNAME[q] || q]; })).concat([['index', 'Our index'], ['months', '13 months'], ['rain', 'Rain'], ['background', 'Background'], ['spectral', 'Spectral watch']]);
    var body = stageShell(k === 'spectral' ? spectralHead() : k === 'rain' ? rainHead() : 'The world ocean has broken daily records for ' + W.sst_world.records.streak + ' days running, land+ocean for ' + W.t2_world.records.streak,
      opts.map(function (o) { return segBtn('trend', o[0], o[1], 'sst_nino34'); }));
    if (k === 'spectral') { viewSpectral(body); return; }
    if (k === 'rain') { viewRain(body); return; }
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
      var keys = [['sst_nino34', 'Niño 3.4'], ['sst_world', 'ocean'], ['t2_world', 'land+ocean']].concat(RDK.map(function (q) { return [q, RNAME[q] || q]; }));
      var WM = Object.assign({}, W, RD);
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap.innerHTML = '<table class="e"><thead><tr><th>month</th>' + keys.map(function (x) { return '<th colspan="2">' + x[1] + '</th>'; }).join('') + '</tr></thead><tbody>' +
        (W.sst_nino34.months13 || []).map(function (m) {
          return '<tr><td>' + MONTHS[m.m - 1] + ' ' + m.y + '</td>' + keys.map(function (x) {
            var mm = ((WM[x[0]] || {}).months13 || []).filter(function (q) { return q.y === m.y && q.m === m.m; })[0];
            return mm ? '<td class="num' + (mm.rank === 1 ? ' top' : '') + '">' + fnum(mm.anom) + '</td><td class="num src">' + mm.rank + '/' + mm.of + '</td>' : '<td>—</td><td>—</td>';
          }).join('') + '</tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Red marks a month that became the warmest of its calendar month in the whole record. The current month is incomplete. Land columns are single ERA5 grid points (2 m air), not regional means.'));
    } else {
      var w0 = W[k] || RD[k];
      if (!w0) { body.appendChild(el('div', 'note', 'No series for ' + esc(k) + '.')); return; }
      var isLand = !W[k];
      // ряд сцены → показатель журнала: один и тот же кирпич обслуживает три ряда
      var JK = { sst_nino34: 'n34_daily', sst_world: 'sst_world', t2_world: 't2_world' };
      plot(body, function (w, h) { return chartRecent(w0, w, h); });
      var lv = pair(w0.last_value, P && P.daily ? P.daily[k] : null, 2, '°C');
      var p50 = pair(w0.forecast14.p50, P && P.p50 ? P.p50[k] : null, 2, '°C');
      var kp = el('div', 'kpis');
      kp.innerHTML = '<div class="kpi"><div class="kn">last day</div><div class="kv">' + lv.big + '</div><div class="km">' + span(w0.last_date, 30) + ' ' + fnum(w0.level30.anom) + ', ' + term('rank', 'rank ' + w0.level30.rank_raw + ' of ' + w0.level30.of) + '</div>' + kmeta(JK[k]) + '</div>' +
        '<div class="kpi"><div class="kn">' + term('analog', 'forecast +14 days') + '</div><div class="kv">' + p50.big + '</div><div class="km">' + term('p10p50p90', 'p10 … p90') + ': ' + fnum(w0.forecast14.p10) + ' … ' + fnum(w0.forecast14.p90) + '</div>' + kmeta('fc14_' + k) + '</div>' +
        '<div class="kpi"><div class="kn">records and CUSUM</div><div class="kv" style="font-size:17px">' + w0.records.streak + '<small>days in a row</small></div><div class="km">' + w0.records.last30 + ' record days of 30; ' + term('cusum', 'CUSUM') + ' ' + (w0.cusum.alarm ? 'alarm' : 'quiet') + ', ' + term('trend', 'above trend') + ' ' + fnum(w0.level30.det) + '</div>' +
        kmeta('rec_' + k) + '</div>';
      body.appendChild(kp);
      if (isLand) { body.appendChild(el('div', 'cap', esc((S.RD || {}).note || '') + ' Box ' + esc(boxLabel(w0.box)) + '; ' + esc(w0.source) + '; built ' + esc((S.RD || {}).built || '') + '. ' + (w0.region ? vLink('this region on the Regions tab', 'regions', 'place') : ''))); worksFoot(body, 'block:landbox'); }
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
    if (CM && CM.items && CM.items.length) segs2.push(segBtn('food', 'goods', 'By commodity', 'prices'), segBtn('food', 'abs', 'Price, $ per tonne', 'prices'));
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
    } else if (k === 'abs' && CM) {
      /* АБСОЛЮТНЫЕ ЦЕНЫ (владелец 07.09): товар — линия в долларах за тонну за пять лет; «all» —
         все товары сеткой 4×3 без прокрутки; «bundle» — все текущие ряды одним пучком к месяцу
         начала, без прошлых лет. Над графиком переключатель привязки прошлых путей и его объяснение. */
      var items = CM.items.slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0) || a.name.localeCompare(b.name); }), pk2 = S.sub.absc || 'all';
      var OPa = ((D.air || {}).onset_paths || {}), opa = OPa.items || [], align = S.sub.absAlign || 'onset';
      function pathsOf(key) { var it = opa.filter(function (x) { return x.key === key; })[0]; return it ? { span: OPa.span || 18, analogs: it.analogs || {} } : null; }
      var rowA = el('div', 'seg sub');
      [['all', 'all together'], ['bundle', 'one bundle']].concat(items.map(function (it) { return [it.key, it.name.replace(/,.*$/, '')]; })).forEach(function (o, i) {
        var b = el('button', (pk2 === o[0] ? 'on' : '') + (i < 2 ? ' sq' : ''), o[1]); b.type = 'button'; b.onclick = function () { S.sub.absc = o[0]; S.pick = null; render(); }; rowA.appendChild(b);   // выбор в легенде не тащим между видами
        if (i === 1) rowA.appendChild(el('span', 'seg-gap', ''));
      });
      body.appendChild(rowA);
      var onsetM = (items[0] || {}).onset || '';
      if (pk2 !== 'bundle') {
        var rowB = el('div', 'seg sub'); rowB.style.alignItems = 'center';
        [['onset', 'past paths through the onset price'], ['now', 'past paths through today’s price']].forEach(function (o) { var b = el('button', (align === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.absAlign = o[0]; render(); }; rowB.appendChild(b); });
        rowB.appendChild(el('span', 'sub', align === 'onset'
          ? 'The thin lines are what the commodity did after the onsets of 1982, 1997, 2015 and 2023, in per cent of its price in each onset month; they are drawn here through this event’s onset price (' + esc(onsetM) + '), so they all meet there by construction and fan out as they did then. Not the dollars of those years: wheat cost about $160 in 1982.'
          : 'The same past paths, drawn through today’s price instead: each is scaled so that it passes through the latest month, and the fan ahead shows where the price would go if it followed that event from here. Left of today the lines differ only because their histories differ.'));
        rowB.lastChild.style.cssText = 'font-size:11.5px;color:var(--muted);line-height:1.35;flex:1 1 320px';
        body.appendChild(rowB);
      }
      if (pk2 === 'all') {
        var yrs = Object.keys((pathsOf(items[0].key) || {}).analogs || {}).sort();
        var leg = el('div', 'seg sub'); leg.style.alignItems = 'center';
        leg.appendChild(el('span', 'sub', 'legend, click to pick out:')); leg.lastChild.style.cssText = 'font-size:11px;color:var(--muted)';
        [['now', 'this event, $', 'var(--text)', '']].concat(yrs.map(function (y) { return [y, 'after ' + y + ' onset', 'var(--a' + y + ')', yearDash(y)]; })).forEach(function (o) {
          var b = el('button', 'leg' + (S.pick === o[0] ? ' on' : ''), '<svg width="30" height="10" viewBox="0 0 30 10"><line x1="1" y1="5" x2="29" y2="5" style="stroke:' + o[2] + '" stroke-width="' + (o[0] === 'now' ? 2.4 : 1.8) + '"' + (o[3] ? ' stroke-dasharray="' + o[3] + '"' : '') + '/></svg> ' + esc(o[1]));
          b.type = 'button'; b.onclick = function () { S.pick = S.pick === o[0] ? null : o[0]; [].forEach.call(leg.querySelectorAll('button'), function (q) { q.classList.remove('on'); }); if (S.pick) b.classList.add('on'); drawGrid(); };
          leg.appendChild(b);
        });
        body.appendChild(leg);
        var grid = el('div', 'pgrid fit');
        items.slice(0, 12).forEach(function (it) { var cell = el('div', 'pcell'); cell._it = it; grid.appendChild(cell); });
        body.appendChild(grid);
        var drawGrid = function () {
          if (!grid.isConnected) return;
          [].forEach.call(grid.children, function (cell) { var w = Math.max(160, cell.clientWidth), h = Math.max(110, cell.clientHeight); cell.innerHTML = chartPrice(cell._it, w, h, { mini: true, paths: pathsOf(cell._it.key), align: align }); fitSvgTitles(cell); });
        };
        requestAnimationFrame(drawGrid);
        if (window.ResizeObserver) { var ro = new ResizeObserver(function () { drawGrid(); }); ro.observe(grid); }
        body.appendChild(el('div', 'cap', 'Every commodity in dollars per tonne (sugar per kilogram), World Bank Pink Sheet, nominal, ordered by food-security weight; the dashed line is the month the event began, the shaded tail two years ahead. Click a commodity above for the full chart with its numbers.'));
      } else if (pk2 === 'bundle') {
        plot(body, function (w, h) { return chartBundle(items, w, h); });
        body.appendChild(el('div', 'cap', 'All twelve commodities as one bundle: each as a percentage of its own price in the month the event began (' + esc(onsetM) + ' = 100), this event only, no past years. Lines above 100 have risen since the onset. Click a name in the legend to pick one out; the same prices in dollars are under “all together”.'));
      } else {
        var itA = items.filter(function (x) { return x.key === pk2; })[0] || items[0], serA = itA.series || {}, nA = (serA.months || []).length, PA = pathsOf(itA.key);
        plot(body, function (w, h) { return chartPrice(itA, w, h, { paths: PA, align: align }); });
        var kA = el('div', 'kpis');
        kA.innerHTML = '<div class="kpi"><div class="kn">' + esc(itA.name) + ' · ' + esc(itA.date) + '</div><div class="kv">' + fnum(itA.value, itA.value > 100 ? 0 : 2, false) + '<small> ' + esc(itA.unit.replace(/[()]/g, '')) + '</small></div><div class="km">month ' + fnum(itA.mom_pct, 1) + ' %, year ' + fnum(itA.yoy_pct, 1) + ' %' + (fin(itA.since_onset_pct) ? ', since the event began ' + fnum(itA.since_onset_pct, 1) + ' %' : '') + '</div>' + kmeta(null, 'World Bank Pink Sheet', itA.date) + '</div>' +
          (PA && itA.onset && fin(itA.value) ? '<div class="kpi"><div class="kn">where the past events went</div><div class="kv" style="font-size:14px">' + Object.keys(PA.analogs).sort().map(function (y) { var r = PA.analogs[y], k12 = 6 + 12, k24 = 6 + 24, b0 = (itA.series.values || [])[(itA.series.months || []).indexOf(itA.onset)]; return y + ': ' + (fin(r.values[k12]) && b0 ? fnum(b0 * r.values[k12] / 100, 0, false) : '…') + ' at +12, ' + (fin(r.values[k24]) && b0 ? fnum(b0 * r.values[k24] / 100, 0, false) : '…') + ' at +24'; }).join(' · ') + '</div><div class="km">months after the onset, through the onset price</div>' + kmeta(null, 'Pink Sheet, our onset dates', itA.date) + '</div>' : '') +
          '<div class="kpi"><div class="kn">' + term('foodweight', 'food-security weight') + '</div><div class="kv">' + (itA.weight || 1) + '<small> of 5</small></div><div class="km">' + esc(itA.weight_basis || '') + '</div>' + kmeta(null, CM.weight_src || '', itA.date) + '</div>';
        body.appendChild(kA);
        body.appendChild(el('div', 'cap', '<strong>' + esc(itA.name) + ':</strong> ' + esc(itA.why) + ' The bold line is the World Bank Pink Sheet monthly price in ' + esc(itA.unit.replace(/[()]/g, '')) + ' over the last ' + (nA > 48 ? 'five years' : Math.round(nA / 12) + ' years') + ', nominal dollars, no inflation adjustment; the shaded part is since the event began. The thin lines are a hint of the range, not a forecast; the same paths in percentages are on the “Since onset” tab.'));
      }
    } else if (k === 'goods' && CM) {
      /* ТОВАРЫ ПОИМЁННО. Индекс FAO — одно число на всю еду; Эль-Ниньо бьёт по пальмовому
         маслу, рису и рыбной муке, и по каждому своим путём. Владелец 06.09: сортировка по
         изменению за год, вес продовольственной значимости, месяц против обычного размаха
         этого месяца, шапка выровнена по числам, заголовки нажимаются (пересортировка). */
      var GKEY = { yoy: 'yoy_pct', mom: 'mom_pct', onset: 'since_onset_pct', weight: 'weight', value: 'value' };
      var gs = S.sub.goodsSort || 'yoy', gk = GKEY[gs] || 'yoy_pct';
      var rows = CM.items.slice().sort(function (a, b) { return (fin(b[gk]) ? b[gk] : -1e9) - (fin(a[gk]) ? a[gk] : -1e9); });
      function th(label, key, num) { return '<th' + (num ? ' class="num' : ' class="') + (gs === key ? ' sorted' : '') + '"' + (key ? ' data-gs="' + key + '"' : '') + '>' + label + (gs === key ? ' ↓' : '') + '</th>'; }
      var wrapG = el('div'); wrapG.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrapG.innerHTML = '<table class="e goods"><thead><tr>' + th('commodity', null) + th(term('foodweight', 'weight'), 'weight', true) + th('price', 'value', true) +
        th('month', 'mom', true) + th('year', 'yoy', true) + th('since the event began', 'onset', true) + th('why it is here', null) + '</tr></thead><tbody>' +
        rows.map(function (c) {
          var w = c.weight || 1;
          var pay = { name: c.name + ' (' + c.unit + ')', def: c.why + ' Price ' + c.value + ' ' + c.unit + ' in ' + c.date + '.' + (c.gulf ? ' Imported by the Gulf states.' : ''), src: 'World Bank Pink Sheet, monthly', date: c.date };
          var wpay = { name: c.name + ': weight ' + w + ' of 5', def: (c.weight_basis || 'no basis recorded') + '. The weight is set by hand and orders the alerts: large moves in staples raise an alert, the same move in a niche crop only shows here.', src: CM.weight_src || 'FAOSTAT food balances; our own scoring', date: c.date };
          var mz = fin(c.mom_z) ? c.mom_z : null, yr = fin(c.yoy_rank) ? c.yoy_rank : null;
          var mcls = mz != null && mz >= 2 ? ' top' : (mz != null && mz <= -2 ? ' dn' : ''), ycls = fin(c.yoy_pct) && c.yoy_pct >= 30 ? ' top' : (fin(c.yoy_pct) && c.yoy_pct <= -30 ? ' dn' : '');
          return '<tr><td>' + src(pay, c.name) + '<div class="sub">' + esc(c.unit) + (c.gulf ? ' · Gulf import' : '') + '</div></td>' +
            '<td class="num"><span class="wdots" data-src="' + esc(JSON.stringify(wpay)) + '">' + '●●●●●'.slice(0, w) + '<i>' + '○○○○○'.slice(0, 5 - w) + '</i></span></td>' +
            '<td class="num">' + fnum(c.value, c.value > 100 ? 0 : 2, false) + '</td>' +
            '<td class="num' + mcls + '">' + fnum(c.mom_pct, 1) + ' %' + (fin(c.mom_typical) ? '<div class="sub">usual ' + fnum(c.mom_typical, 1) + ' ± ' + fnum(c.mom_sd, 1, false) + '</div>' : '') + '</td>' +
            '<td class="num' + ycls + '">' + fnum(c.yoy_pct, 1) + ' %' + (yr != null ? '<div class="sub">' + ord(yr) + ' pct since ' + (c.since_year || 1960) + '</div>' : '') + '</td>' +
            '<td class="num' + ((c.since_onset_pct || 0) > 10 ? ' top' : '') + '">' + fnum(c.since_onset_pct, 1) + ' %</td>' +
            '<td class="act">' + esc(c.why) + '</td></tr>';
        }).join('') + '</tbody></table>';
      wrapG.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('th[data-gs]');
        if (t) { S.sub.goodsSort = t.getAttribute('data-gs'); render(); }
      });
      body.appendChild(wrapG);
      body.appendChild(el('div', 'cap', esc(CM.note) + ' Prices are ' + esc(CM.as_of) + ', one month fresher than the FAO index. Click a column header to sort; red marks a rise unusual for the month or of 30 % and more over the year, blue a fall of the same size.'));
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
    var body = stageShell(esc(r.title), []);   // общая кнопка back в шапке; своя дублировала её (владелец 08.09)
    if (r.metric) plot(body, function (w, h) { return chartMetric(r.metric, w, h, r.metric.name); });
    var was = S.P && S.P.risks ? (S.P.risks[r.id] != null ? S.P.risks[r.id] : S.P.risks[r.title]) : null;
    body.appendChild(el('div', 'lead', '<b>Level ' + r.level + ' · ' + esc(r.horizon) + '.</b> ' + mark(r.plain || '') + (fin(was) && was !== r.level ? ' <i>Level was ' + was + ' at ' + esc(prevStamp()) + '.</i>' : '')));
    body.appendChild(el('div', 'note', '<strong>Evidence.</strong> ' + mark(r.evidence) + (r.metric ? '<br>' + dynWords(r.metric) : '')));
    body.appendChild(el('div', 'note warn', '<strong>Watch.</strong> ' + mark(r.watch)));
    var cnr = conceptsHtml('risk:' + (r.id || ''), true);
    if (cnr) body.appendChild(el('div', 'note cn-box', cnr));
    [].slice.call(body.querySelectorAll('.lead, .note')).forEach(function (q) { hlConcepts(q, 'risk:' + (r.id || '')); });
    // по имени риска; по номеру — только пока на проде лежит старый links.json
    var lk = linksHtml('risk:' + (r.id || ''), true) || linksHtml('risk:' + S.risk, true);
    if (lk) body.appendChild(el('div', 'links-box', lk));
  }


  // ---------------------------------------------------------------- Ocean (экспертиза 04.09)
  var CREW = { writer: 'DeepSeek V4 Pro', supervisor: 'Fable (Claude)' };

  /* Строка «свежее, не разобранное» на карточке состояния: что пришло после разбора и сколько
     триггеров пересечено. Только когда слой считан против текущего разбора и новее его. */
  function freshLine() {
    var D = S.D || {}, F = S.F || {};
    if (!F.stamp || F.assessed_stamp !== D.stamp || F.stamp === D.stamp) return '';
    var s = F.series || {}, a = s.sst_nino34 || {}, w = s.sst_world || {}, k = F.kpi || {}, parts = [];
    if (a.last_date && a.last_date !== a.assessed_last_date) parts.push('Niño 3.4 ' + fnum(a.last_value) + ' °C (' + esc(a.last_date) + ')');
    if (w.last_date && w.last_date !== w.assessed_last_date) parts.push('world ' + fnum(w.last_value) + ' °C');
    if (k.noaa && k.noaa.date && k.noaa.date !== (D.noaa || {}).date) parts.push('NOAA week ' + esc(k.noaa.date) + ' ' + fnum(k.noaa.n34a, 1));
    if (k.tao && k.tao.date && k.tao.date !== ((D.subsurface || {}).tao || {}).last_date) parts.push('mooring ' + fnum(k.tao.warmest, 1) + ' °C (' + esc(k.tao.date) + ')');
    if (k.wind && k.wind.date && k.wind.date !== (((D.wind || {}).era5 || {}).last_date)) parts.push('wind ' + fnum(k.wind.mean7, 1) + ' m/s (' + esc(k.wind.date) + ')');
    var nT = (F.triggers || []).length;
    return '<div class="fresh' + (F.needs_assessment ? ' hot' : '') + '"><span class="fdot"></span>' + term('fresh', 'fresh, not yet assessed') + (parts.length ? ': ' + parts.join(' · ') : ': no newer days yet') +
      ' · ' + (nT ? '<b>' + nT + ' trigger' + (nT > 1 ? 's' : '') + (F.needs_assessment ? ', assessment needed' : '') + '</b>' : 'triggers:&nbsp;none') + ' <span class="cgo" data-go="ops" data-gosub="fresh">details →</span></div>';
  }

  /* ПРОВЕРКА — ФАКТ, А НЕ ОБЕЩАНИЕ. review.py кладёт в summary.review, кто проверил и при
     каком штампе пересчёта. Если после этого данные пересчитали, вердикт стал другим, и
     старая отметка к нему не относится: панель обязана сказать это вслух. */
  function reviewState() {
    var D = S.D || {}, rv = ((D.summary || {}).review) || null;
    if (!rv || !rv.model) return { done: false, why: 'not checked yet' };
    if (rv.stamp && D.stamp && rv.stamp !== D.stamp)
      return { done: false, stale: true, rv: rv, why: 'the verdict was rewritten after the last check (' + rv.at + ')' };
    return { done: true, rv: rv };
  }

  function reviewLine() {
    var st = reviewState();
    if (!st.done) return '<span class="rv-no">' + esc(st.why) + '</span>';
    var rv = st.rv, bits = [];
    if (rv.findings) bits.push(rv.findings + (rv.findings === 1 ? ' finding' : ' findings'));
    if (rv.edits) bits.push(rv.edits + (rv.edits === 1 ? ' wording fixed' : ' wordings fixed'));
    if (!bits.length) bits.push('nothing to correct');
    return '<span class="rv-ok">checked ' + esc((rv.at || '').slice(0, 10)) + ' \u00b7 ' + esc(bits.join(', ')) +
      '</span>' + (rv.blocking ? ' <span class="rv-no">blocking issues open</span>' : '');
  }
  var BOX_ORDER = [['nino34', 'Niño 3.4'], ['nino3', 'Niño 3'], ['nino12', 'Niño 1+2'], ['nino4', 'Niño 4'], ['gulf', 'Gulf'], ['world', 'World ocean']];

  /* Тепловая карта разреза: столбцы — долготы, строки — глубины; цвет — знак и величина
     аномалии на переменных темы (не «синий-красный» из палитры Matplotlib, а наши --nino и
     --nina с прозрачностью), пустые ячейки — сеточным цветом. Линия D20 поверх, если есть. */
  /* Цвет тепла по величине: тёплое от янтарного к густо-красному, холодное от голубого к
     синему; чем сильнее аномалия, тем краснее (владелец 08.09: «самое горячее должно быть
     краснее»). op — доля от максимума шкалы, 0…1. */
  function heatColor(v, op) {
    op = Math.max(0, Math.min(1, op));
    return v >= 0 ? 'hsl(' + Math.round(38 - 38 * op) + ',88%,' + Math.round(62 - 26 * op) + '%)'
                  : 'hsl(' + Math.round(196 + 16 * op) + ',72%,' + Math.round(68 - 24 * op) + '%)';
  }
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
    vmax = cfg.vmax || Math.max(0.5, Math.ceil(vmax * 2) / 2);   // общая шкала для двух кадров рядом
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
        s += '<rect ' + geo + ' style="fill:' + heatColor(v, op) + '" opacity="' + (0.4 + 0.6 * op).toFixed(2) + '"/>';
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
    var SCALE = [[vmax, heatColor(vmax, 1), 1], [vmax / 2, heatColor(vmax / 2, .5), .7], [0, 'var(--grid)', .6], [-vmax / 2, heatColor(-vmax / 2, .5), .7], [-vmax, heatColor(-vmax, 1), 1]];
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
    var ftW = freshTail('wind');
    if (ftW.length && fin(vals[li])) {
      var tpW = [[X(li), Y(vals[li])]].concat(ftW.map(function (p) { return [X(li + p[0]), Y(p[1])]; }));
      s += poly(tpW, 'var(--ochre)', 1.4, 1, '3 3');
      var lW = tpW[tpW.length - 1];
      s += freshDot(lW[0], lW[1], 4);
    }
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
    // Колонка подписей справа: на большом графике она есть, в плитке подписи уехали в метку.
    var RC = S._tight ? 8 : Math.max(120, Math.min(210, Math.round(W * .3)));
    var gap = 10, hh = (H - 20 - gap * (items.length - 1)) / items.length;
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

  /* АНАЛОГИ В АБСОЛЮТНЫХ ГРАДУСАХ. Прошлые события в файле лежат аномалиями; в режиме
     «absolute °C» они рисовались как есть и ложились у нуля под шкалой 0–30 (владелец 08.09:
     «неужели аналогичные события были на 0?»). Климатология по дням берётся из самого ряда:
     SST минус аномалия того же дня; аналог = его аномалия + климатология этого дня. */
  function boxMetric(b, absolute) {
    var an = b.analogs || {}, out = an;
    if (absolute && b.sst && b.anom) {
      var clim = b.sst.map(function (v, i) { return fin(v) && fin(b.anom[i]) ? v - b.anom[i] : null; });
      out = {};
      Object.keys(an).forEach(function (y) { var av = an[y] || [], off = b.dates.length - av.length; out[y] = av.map(function (v, i) { var c = clim[off + i]; return fin(v) && fin(c) ? v + c : null; }); });
    }
    return { name: b.title + (absolute ? ', daily SST' : ', daily anomaly') + ' — our box on the NOAA grid, one day behind', unit: '°C', step: 'day',
      dates: b.dates, values: absolute ? b.sst : b.anom, analogs: out };
  }

  function viewOcean() {
    var D = S.D, O = D.oisst || {}, SB = D.subsurface || {}, k = sub('ocean', 'surface');
    var boxes = O.boxes || {}, T34 = boxes.nino34 || {}, TAO = SB.tao || {}, GD = SB.godas || {};
    var head = 'Ocean';
    if (k === 'surface') head = fin(T34.last_anom) ? 'Niño 3.4 today: ' + fnum(T34.last_anom) + ' °C on our box, ' + (T34.days_stale === 1 ? 'one day' : T34.days_stale + ' days') + ' behind' : 'Daily boxes straight from the NOAA grid';
    else if (k === 'moorings') head = TAO.warmest ? 'Water ' + fnum(TAO.warmest.value, 1) + ' °C above normal is sitting at ' + TAO.warmest.depth + ' m under ' + TAO.warmest.station : 'Below the surface: the moorings';
    else head = GD.max_anom ? 'Reanalysis, ' + esc(GD.month) + ': up to ' + fnum(GD.max_anom.value, 1) + ' °C above normal at ' + GD.max_anom.depth + ' m, ' + esc(GD.max_anom.label) : 'Reanalysis section along the equator';
    if (k === 'hovmoller') head = 'How the heat moves: month by month, beside a past event';
    if (k === 'motion') head = 'The section month by month';
    var body = stageShell(head, [segBtn('ocean', 'surface', 'Surface, daily', 'surface'), segBtn('ocean', 'moorings', 'Below the surface', 'surface'), segBtn('ocean', 'section', 'Reanalysis section', 'surface'), segBtn('ocean', 'hovmoller', 'Heat on the move', 'surface'), segBtn('ocean', 'motion', 'Month by month', 'surface')]);
    if (O.error) { body.appendChild(el('div', 'note warn', 'The direct OISST block did not load: ' + esc(O.error))); }
    if (k === 'motion') { viewOceanMotion(body); return; }
    if (k === 'hovmoller') {
      var HV = S.HV || {}, hm = S.sub.hovMetric || 'anom100', ha = S.sub.hovAnalog == null ? '1997' : S.sub.hovAnalog;
      var row1 = el('div', 'seg sub');
      [['anom100', 'anomaly at 100 m'], ['d20_anom', 'thermocline depth']].forEach(function (o) { var b = el('button', (hm === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.hovMetric = o[0]; render(); }; row1.appendChild(b); });
      row1.appendChild(el('span', 'seg-gap', ''));
      [['', 'this event alone']].concat(Object.keys(HV.analogs || {}).sort().map(function (y) { return [y, 'beside ' + y]; })).forEach(function (o) { var b = el('button', ha === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.hovAnalog = o[0]; render(); }; row1.appendChild(b); });
      body.appendChild(row1);
      plot(body, function (w, h) { return chartHovmoller(HV, w, h, { metric: hm, analog: ha || null }); });
      var cur = HV.current || {}, lastRow = (cur[hm] || [])[(cur.months || []).length - 1] || [], mx = -Infinity, mj = -1;
      lastRow.forEach(function (v, j) { if (fin(v) && v > mx) { mx = v; mj = j; } });
      var kh = el('div', 'kpis');
      if (mj >= 0) kh.innerHTML = '<div class="kpi"><div class="kn">' + (hm === 'anom100' ? 'warmest at ' + Math.round(cur.level) + ' m' : 'deepest thermocline anomaly') + ' · ' + esc(cur.months[cur.months.length - 1]) + '</div><div class="kv">' + fnum(mx, 1) + '<small>' + (hm === 'anom100' ? ' °C' : ' m') + ' at ' + esc(cur.labels[mj]) + '</small></div><div class="km">the eastern edge of the warm band is where the wave surfaces</div>' + kmeta(null, 'GODAS via PSL', cur.months[cur.months.length - 1]) + '</div>';
      body.appendChild(kh);
      body.appendChild(el('div', 'cap', esc(HV.note || '') + ' Built ' + esc(HV.built || '') + '. ' + vLink('the reanalysis section for the last month', 'ocean', 'section') + ' ' + vLink('the moorings, daily', 'ocean', 'moorings')));
      return;
    }

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
      kt.innerHTML = (TAO.warmest ? '<div class="kpi"><div class="kn">' + term('tao', 'warmest layer') + '</div><div class="kv">' + fnum(TAO.warmest.value, 1) + '<small>°C at ' + TAO.warmest.depth + ' m</small></div><div class="km">' + esc(TAO.warmest.station) + ', five-day mean to ' + esc(TAO.warmest.date) + (TAO.warmest.prev_max ? '; the mooring record before 2026: ' + fnum(TAO.warmest.prev_max.value, 1) + ' °C at ' + TAO.warmest.prev_max.depth + ' m on ' + esc(TAO.warmest.prev_max.date) + (TAO.warmest.above_record ? ', now exceeded' : ', not exceeded') : '') + '</div>' + kmeta('subsurface_warmest') + '</div>' : '') +
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
  var BLOCK_LBL = { models: 'How the forecast models break', peak: 'When the growth stops', food: 'El Niño and food prices', type: 'Eastern-type El Niño', radiance: 'Convection and the Walker circulation in raw radiances', spectral: 'Early-warning signals before a transition', rain: 'El Niño and regional rainfall', landbox: 'Regional temperature response' };
  function anchorLabel(key) {
    var D = S.D, i = key.indexOf(':'), kind = key.slice(0, i), id = key.slice(i + 1);
    if (kind === 'risk') { var r = (D.risks || []).filter(function (x) { return x.id === id; })[0]; return r ? 'risk: ' + r.title : (/^\d+$/.test(id) && D.risks[id] ? 'risk: ' + D.risks[id].title : null); }
    if (kind === 'alert') { var a = (D.alerts || []).filter(function (x) { return x.id === id || aslug(x.title) === id; })[0]; return a ? 'alert: ' + a.title : (/^\d+$/.test(id) && D.alerts[id] ? 'alert: ' + D.alerts[id].title : null); }
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
      [segBtn('refs', 'works', 'Our works (' + works.length + ')', 'works'), segBtn('refs', 'sources', 'Data sources (' + srcs.length + ')', 'works'), segBtn('refs', 'literature', 'Literature (' + lit.length + ')', 'works'), segBtn('refs', 'neighbours', 'Neighbours (' + ((S.NB || {}).items || []).length + ')', 'works'), segBtn('refs', 'concepts', 'Concepts (' + ((S.CN || {}).n_anchors || 0) + ')', 'works')]);
    body.classList.add('scroll');
    var tgt = window.matchMedia('(max-width:900px)').matches ? '' : ' target="_blank" rel="noopener"';
    if (k === 'concepts') {
      /* Реестр понятий, привязанный к якорям панели: тот же список, что в подсказках, но целиком.
         Группы по виду якоря; у каждой строки чипы и граф набора; наверху граф всех понятий сцены. */
      var CNA = (S.CN || {}).anchors || {}, keys = Object.keys(CNA).sort(), GR = [['risk', 'Risks'], ['alert', 'Alerts'], ['block', 'Blocks of the panel'], ['region', 'Regions'], ['term', 'Terms of the glossary']];
      var allIds = {}; keys.forEach(function (a) { CNA[a].forEach(function (c) { allIds[c.id] = 1; }); });
      var nIds = Object.keys(allIds).length;
      body.appendChild(el('div', 'note', esc((S.CN || {}).note || '') + ' Built ' + esc((S.CN || {}).built || '') + '; ' + keys.length + ' anchors, ' + ((S.CN || {}).n_links || 0) + ' links, ' + nIds + ' distinct concepts. Names open the concept page in your language; ' +
        '<a href="' + cnGraph(Object.keys(allIds)) + '" target="_blank" rel="noopener">all ' + nIds + ' on the graph ↗</a>'));
      function anchorLabel(a) {
        var p = a.split(':'), id = p.slice(1).join(':');
        if (p[0] === 'term') return (S.G[id] || {}).name || id;
        if (p[0] === 'risk') { var rr = ((S.D || {}).risks || []).filter(function (x) { return x.id === id; })[0]; return rr ? rr.title : id; }
        if (p[0] === 'alert') { var aa = ((S.D || {}).alerts || []).filter(function (x) { return (x.id || aslug(x.title)) === id; })[0]; return aa ? aa.title : id.replace(/_/g, ' '); }
        if (p[0] === 'region') { var rg = (((S.D || {}).regions || {}).items || []).filter(function (x) { return x.id === id; })[0]; return rg ? rg.name : id.replace(/_/g, ' '); }
        return id.replace(/_/g, ' ');
      }
      GR.forEach(function (g) {
        var ks = keys.filter(function (a) { return a.indexOf(g[0] + ':') === 0; }); if (!ks.length) return;
        var sec = el('div', 'cn-sec');
        sec.innerHTML = '<div class="lk-h">' + esc(g[1]) + ' · ' + ks.length + '</div>' + ks.map(function (a) {
          return '<div class="cn-row"><div class="cn-a">' + esc(anchorLabel(a)) + '</div>' + conceptsHtml(a, true) + '</div>';
        }).join('');
        body.appendChild(sec);
      });
      return;
    }
    if (k === 'neighbours') {
      /* СОСЕДИ (владелец 08.09: «подборку ресурсов отдельно — сходные проекты, ссылки на соседей»).
         Ручной справочник data/enso/neighbours.json; лицензии проверены по первоисточникам. */
      var NB = S.NB || {}, nb = NB.items || [], nbk = S.sub.nbKind || 'all';
      var rowN = el('div', 'seg sub');
      [['all', 'all'], ['app', 'sites and apps'], ['library', 'libraries']].forEach(function (o) { var b = el('button', (nbk === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.nbKind = o[0]; render(); }; rowN.appendChild(b); });
      body.appendChild(rowN);
      var listN = el('div', 'refs');
      listN.innerHTML = nb.filter(function (x) { return nbk === 'all' || x.kind === nbk; }).map(function (x) {
        return '<div class="gl-i"><b><a href="' + esc(x.url) + '"' + tgt + '>' + esc(x.name) + '</a></b> <span class="s">' + esc(x.kind === 'library' ? 'library' : 'site') + '</span>' +
          '<div>' + esc(x.what) + '</div>' +
          '<div class="sub"><b>Data:</b> ' + esc(x.data) + '</div>' +
          '<div class="sub"><b>Code:</b> ' + (x.code ? '<a href="' + esc(x.code) + '"' + tgt + '>' + esc(x.code.replace(/^https?:\/\/(www\.)?/, '')) + '</a>' : 'not published') + ' · <b>licence:</b> ' + esc(x.licence) + '</div>' +
          '<div class="sub"><b>For us:</b> ' + esc(x.why) + '</div></div>';
      }).join('');
      body.appendChild(listN);
      body.appendChild(el('div', 'cap', esc(NB._ || '') + ' Built ' + esc(NB.built || '') + '. "Open code" means the repository is public under the stated licence: MIT and Apache 2.0 allow reuse, including commercial, with attribution and the licence text kept; a live site is not a service to embed unless its owner says so.'));
      return;
    }
    var list = el('div', 'refs');
    if (k === 'works') {
      list.innerHTML = works.map(function (w) {
        /* КАРТОЧКА РАБОТЫ — ТА ЖЕ, ЧТО ВЕЗДЕ НА ПАНЕЛИ. Владелец 06.09: «покажи карточку
           статьи в специальном виде, мы это уже делаем, соблюдай его; и там же ссылка
           перейти на статью». Собираем её тем же worksHtml, что и подсказки «N works»,
           поэтому вид и ссылка «read our version ↗» одинаковые во всей панели. */
        var card = worksHtml([{ id: w.id, date: w.date, folder: w.folder, title: w.orig,
                                our_title: w.title, oneliner: w.oneliner }]);
        var pay = { name: w.title, html: card + '<p><b>Used at</b></p>' + w.uses.map(function (u) { return '<p class="wk-p">' + esc(u.at) + (u.why ? '<i>' + esc(u.why) + '</i>' : '') + '</p>'; }).join(''),
          src: 'our own retelling of this work', date: w.date };
        /* Номер arXiv — со своей подсказкой: он ведёт в НАШ разбор, а не в архив, и это
           должно быть видно до нажатия (владелец 06.09). Ссылка на первоисточник — там же,
           отдельной строкой. */
        var numPay = { name: 'Our adapted article',
          html: '<p>The number identifies the paper; the link opens <b>our adapted article</b> in English, where the original is linked.</p>' + card,
          src: 'arXiv ' + w.id, date: w.date };
        var ourUrl = '/lang/en/archive/' + esc(w.date) + '/' + esc(w.folder) + '/index.html';
        return '<div class="ref" data-src="' + esc(JSON.stringify(pay)) + '"><div class="ref-t"><a href="' + ourUrl + '"' + tgt + '>' + esc(w.title) + '</a><span class="ref-n">' + w.uses.length + ' use' + (w.uses.length > 1 ? 's' : '') + '</span></div>' +
          '<div class="ref-d">' + esc(w.oneliner || w.orig) + '</div><div class="ref-m"><a class="wk-num" href="' + ourUrl + '"' + tgt + ' data-src="' + esc(JSON.stringify(numPay)) + '"><span class="wk-read">Read the adapted article →</span> <span class="wk-num">' + esc(w.id) + '</span></a> · ' + esc(w.date) + ' · ' + esc(w.uses.map(function (u) { return u.at.split(':')[0]; }).filter(function (v, i, a) { return a.indexOf(v) === i; }).join(', ')) + '</div></div>';
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
    d.addEventListener('click', function (ev) { if (ev.target.closest('.dcal')) return; S._back = 'overview'; S.full = false; S.view = go[0]; if (go[1]) S.sub[go[0]] = go[1]; S.risk = null; render(); });
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
    /* плитки новых источников 07.09 */
    var RA1 = S.RA || {}, PR1 = S.PR || {}, RD1 = (S.RD || {}).series || {}, HV1 = S.HV || {}, MN1 = S.MN || {};
    var cr1 = ((RA1.sources || {}).n21_cris || {}).series || {}, cur1 = String((RA1.window || {}).current || 2026), dl1 = RA1.window ? radDays(RA1) : null;
    if (cr1.walker_A) add('Raw Walker contrast', 'East minus west brightness temperature from raw granules; near zero this year.', ['radiance', 'walker'], function (w, h) { return chartRadSeries({ byYear: cr1.walker_A, cur: cur1, n: 68, dayLabel: dl1, zero: true, title: 'Raw Walker, K, day' }, w, h); });
    if (cr1.nino34_A && cr1.nino34_A.conv_frac) add('Deep convection over Niño 3.4', 'Share of cold cloud tops, this year against 2023–2025.', ['radiance', 'convection'], function (w, h) { var by = {}; Object.keys(cr1.nino34_A.conv_frac).forEach(function (y) { by[y] = {}; Object.keys(cr1.nino34_A.conv_frac[y]).forEach(function (d) { by[y][d] = cr1.nino34_A.conv_frac[y][d] * 100; }); }); return chartRadSeries({ byYear: by, cur: cur1, n: 68, dayLabel: dl1, zero: true, title: 'Convection, % of footprints, day' }, w, h); });
    var gp1 = (PR1.gpcp || {}).global;
    if (gp1) add('Rain over the planet', gp1.pct_of_normal + ' % of normal in ' + gp1.last + '.', ['trend', 'rain'], function (w, h) { return chartRainBars({ ym: gp1.ym, values: gp1.values, normal: gp1.normal_series, title: 'Planet, mm per day, GPCP', unit: 'mm/day' }, w, h); });
    Object.keys(PR1.regions || {}).slice(0, 2).forEach(function (k) { var r0 = PR1.regions[k]; add('Rain, ' + (LAND_NAME[k] || k), r0.sum30.pct_of_normal + ' % of normal over 30 days.', ['trend', 'rain'], function (w, h) { return chartRainBars({ ym: r0.months.map(function (m) { return m.ym; }), values: r0.months.map(function (m) { return m.mm; }), normal: r0.months_normal, title: (LAND_NAME[k] || k) + ', mm per month', unit: 'mm', partialLast: true }, w, h); }); });
    ['land_peru_coast', 'land_gulf_north'].forEach(function (k) { var r1 = RD1[k]; if (r1) add((LAND_NAME[k] || k) + ', air', fnum(r1.level30.anom) + ' °C over 30 days, rank ' + r1.level30.rank_raw + '.', ['trend', k], function (w, h) { return chartRecent(r1, w, h); }); });
    if (HV1.current && HV1.current.months) add('Heat on the move (Hovmöller)', 'Subsurface anomaly along the equator, month by month.', ['ocean', 'hovmoller'], function (w, h) { return chartHovmoller(HV1, w, h, { metric: 'anom100', analog: null }); });
    if ((MN1.per_day || {}).dates) add('In the news', (MN1.articles || []).length + ' headlines in nine languages.', ['mentions', 'attention'], function (w, h) { return chartDaysPanels([{ title: 'Articles per day', dates: MN1.per_day.dates, series: [{ name: 'articles', values: MN1.per_day.counts, bars: true, color: 'var(--ochre)' }] }], w, h); });
    (D.risks || []).forEach(function (r, i) {
      if (!r.metric || !r.metric.values || T2.length >= 48) return;
      if (T2.some(function (t) { return t.title === r.title; })) return;
      add(r.title, 'Level ' + r.level + ' · ' + r.horizon + '. ' + (r.plain || '').slice(0, 160), ['risk', i], function (w, h) { return chartMetric(r.metric, w, h, r.metric.name); });
    });
    return T2.slice(0, 48);
  }

  function viewOverview() {
    var D = S.D, NW = D.noaa, N = D.nino34, IRI = D.iri && !D.iri.error ? D.iri : null, A = D.air || {}, O = D.oisst || {}, SB = D.subsurface || {}, FO = D.food && !D.food.error ? D.food : null, ONI = D.oni, CORE = D.risk_core || {}, G = D.gulf || {};
    var body = stageShell('Overview: ' + D.risk_index + ' of 100, ' + (D.risks || []).length + ' risks, ' + (D.alerts || []).length + ' alerts — every tile opens its section', []);
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
    /* НОВЫЕ ПОКАЗАТЕЛИ 07.09 (владелец: «пройдись по overview, наверняка появились новые KPI»). */
    var RA0 = S.RA || {}, PR0 = S.PR || {}, SP0 = S.SP || {}, MN0 = S.MN || {}, RD0 = (S.RD || {}).series || {};
    var wkA = (((RA0.sources || {}).n21_cris || {}).series || {}).walker_A || {}, wkCur = wkA[String((RA0.window || {}).current || 2026)] || {};
    var wkKeys = Object.keys(wkCur).map(Number).sort(function (a, b) { return a - b; }), wkLast = wkKeys.length ? wkCur[String(wkKeys[wkKeys.length - 1])] : null;
    if (fin(wkLast)) strip.appendChild(ovKpi(term('walkerraw', 'raw Walker'), fnum(wkLast, 1, false) + '<small>K east−west</small>', 'past years +19…+26 K; near zero = convection moved east', spark({ values: wkKeys.map(function (d) { return wkCur[String(d)]; }) }, 60, 26), ['radiance', 'walker'], null, ['NOAA-21 CrIS, raw granules', String(RA0.updated || '').slice(0, 10)]));
    var gp = (PR0.gpcp || {}).global;
    if (gp && fin(gp.pct_of_normal)) strip.appendChild(ovKpi(term('gpcp', 'rain, planet'), gp.pct_of_normal + '<small>% of normal</small>', esc(gp.last) + ' · wetter than ' + gp.rank_pct + ' % of years', spark({ values: gp.values.slice(-24) }, 60, 26), ['trend', 'rain'], null, ['GPCP monthly', gp.last]));
    var dryK = Object.keys(PR0.regions || {}).sort(function (a, b) { return PR0.regions[a].sum30.pct_of_normal - PR0.regions[b].sum30.pct_of_normal; })[0];
    if (dryK) strip.appendChild(ovKpi('driest region, 30 d', esc(LAND_NAME[dryK] || dryK) + '<small>' + PR0.regions[dryK].sum30.pct_of_normal + ' % of normal</small>', 'drier than ' + (100 - PR0.regions[dryK].sum30.rank_pct) + ' % of years since 1981', barFill(PR0.regions[dryK].sum30.pct_of_normal, 'var(--nino)'), ['trend', 'rain'], null, ['ERA5 box sum', PR0.regions[dryK].last_date]));
    var peru = RD0.land_peru_coast;
    if (peru) strip.appendChild(ovKpi(term('landbox', 'Peru coast, air'), fnum(peru.level30.anom) + '<small>°C, 30 d</small>', 'rank ' + peru.level30.rank_raw + ' of ' + peru.level30.of + ' years; ' + peru.records.streak + ' record days running', spark({ values: (peru.recent || []).slice(-60) }, 60, 26), ['trend', 'land_peru_coast'], null, ['ERA5 box mean', peru.last_date]));
    if (SP0.built) strip.appendChild(ovKpi(term('spectral', 'spectral watch'), (SP0.signals || []).length ? '<span class="dn">SIGNAL</span>' : 'quiet<small>' + SP0.lines_99_now + ' vs ' + SP0.lines_99_expected_by_chance + ' by chance</small>', (SP0.candidates || []).length ? 'candidate: ' + SP0.candidates.map(function (q) { return q.replace(/^land_/, ''); }).join(', ') : 'no line at 2–7 days in ' + (SP0.series || []).length + ' series', '', ['trend', 'spectral'], null, ['our own test', String(SP0.built || '').slice(0, 10)]));
    if (MN0.built) strip.appendChild(ovKpi(term('mentions', 'in the news'), (MN0.articles || []).length + '<small>headlines</small>', ((MN0.languages || []).filter(function (l) { return l.n; }).length) + ' languages · Wikipedia ' + (((MN0.wiki || {}).en || {}).last7_per_day || '…') + ' views a day', spark({ values: ((MN0.per_day || {}).counts || []) }, 60, 26), ['mentions', 'attention'], null, ['Google News, Wikipedia', String(MN0.built || '').slice(0, 10)]));
    body.appendChild(strip);
    var tiles = ovTiles();
    var grid = el('div', 'ov-grid');
    tiles.forEach(function (t) {
      var d = el('div', 'ov-tile');
      d.setAttribute('data-src', JSON.stringify({ name: t.title, def: t.meaning, why: 'Click to open the section.' }));
      /* Название — отдельным элементом, а не голым текстом: голый текст внутри flex
         становится безымянным элементом, который не умеет ужиматься, и на телефоне длинное
         название выталкивало метку «legend» за край плитки (проверка 06.09, 375 px). */
      d.innerHTML = '<div class="ov-t"><span class="ov-tt">' + esc(t.title) + '</span></div><div class="ov-p"></div>';
      d.addEventListener('click', function (e) { if (e.target.closest('[data-pick]')) return; S._back = 'overview'; S.full = false; S.pick = null; if (t.go[0] === 'risk') { S.risk = t.go[1]; S.view = 'risk'; } else { S.view = t.go[0]; if (t.go[1] != null) S.sub[t.go[0]] = t.go[1]; S.risk = null; } render(); });
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
        try { host.innerHTML = t.draw(w, h); fitSvgTitles(host, true); } catch (err) { host.innerHTML = '<div class="note warn">' + esc(String(err.message || err)) + '</div>'; }
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
      nodes.filter(function (n) { return n.layer === 'collect'; }).length + ' collectors, ' + nodes.filter(function (n) { return n.layer === 'state'; }).length + ' computed states', []);
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
    ['How an update works', 'One command pulls every source, keeps the raw copies, recomputes every state, compares with the previous update and with a week ago, writes the value journal and a full snapshot. A language model (DeepSeek V4 Pro) then reads a digest of the numbers and writes the verdict; a second model (Fable, Claude) reads the verdict against the same numbers and corrects it where it strays; a person looks at the result and decides whether it goes out. Nothing on this page is written by hand at update time except the reference tables, which are dated. Between assessments a light run applies the same rules to fresh data without the model: the panel shows that data as fresh, not yet assessed, with a pulsing hollow dot, and the Ops tab lists every run and every source with its date range.'],
    ['What is measured here that is not measured elsewhere', 'The daily Niño boxes straight from the NOAA grid, one day behind, with our own climatologies; the water under the equator by mooring, every day, against each mooring\u2019s own record; the westerly wind bursts from daily reanalysis wind; the live-model centre and where we stand inside the season; the comparable core of the risk index for past events, and the same by RONI; the Gulf and Kuwait measured, not quoted.'],
    ['What we do not claim', 'We have no model of our own and forecast nothing. A “broken” model is one below the official value in most verified issues, not a bad model. The risk index is a construction of this page, comparable only with itself; the core and RONI are the fair comparisons across decades. Analogue paths of prices are what happened then, not what will happen. Regional impacts are typical, never guaranteed; the teleconnections for Europe and Russia are weak and the page says so on the row.'],
    ['Reading the charts', 'Every chart with more than one series distinguishes them by dash pattern, not by colour alone; the legend is clickable and lights one series. Past events are drawn on the same days of the year, dashed, in the same order everywhere: 1982, 1997, 2015, 2023, then last year in grey. Negative values on heat maps are hatched. The vertical mark on the plume shows the lived part of the season as a point and the rest as a range.'],
    ['Changelog', '2026-09-03 — first version: daily series, weekly indices, ONI, the plume, food, regions, risks, the verdict. 2026-09-04 — the value journal, the atmosphere and fuel, satellite layers, commodities by name, models by class, the live centre, the comparable core, contextual links to parsed papers. 2026-09-04, evening, after the first expert review — OISST direct with own climatologies, the moorings and the reanalysis section, daily wind and bursts, the MJO, RONI and the second scale, MEI and the Indian Ocean Dipole, the ocean heat content, the release calendar, the Regions tab with the Gulf measured, commodity paths since onset, dashed series and clickable legends everywhere, this chain and this page.']
  ];
  /* РАЗДЕЛ ИСТОРИИ ИЗМЕРЕНИЙ (владелец 06.09): фон, на котором идёт событие, не само событие.
     Данные planet.json (tools/enso/planet.py): газы, лёд, температура, уровень моря. Без модели. */
  function niceStep(range) {
    var raw = range / 5, p = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10)), m = raw / p;
    return (m < 1.5 ? 1 : (m < 3.5 ? 2 : (m < 7.5 ? 5 : 10))) * p;
  }
  function ym2x(ym) { var y = parseInt(ym.slice(0, 4), 10), m = parseInt(ym.slice(5, 7), 10); return y + (m - .5) / 12; }
  function monthName(ym) { return MONTHS[parseInt(ym.slice(5, 7), 10) - 1] || ym; }

  /* СПАГЕТТИ ПО ГОДАМ, как на climatereanalyzer: каждый год тонкой линией по дню года, годы
     сильных Эль-Ниньо своими штрихами, текущий год охрой, норма пунктиром. Легенда нажимаемая. */
  function chartYears(cfg, W, H) {
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var ys = Object.keys(cfg.years || {}).sort(), cur = String(cfg.current || ys[ys.length - 1]);
    var all = [];
    ys.forEach(function (y) { all = all.concat((cfg.years[y] || []).filter(fin)); });
    if (!all.length) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var vmin = Math.min.apply(null, all), vmax = Math.max.apply(null, all), pad = (vmax - vmin) * .06; vmin -= pad; vmax += pad * 2;
    var X = cfg.monthly ? function (i) { return Lp + ((ME[i] + ME[i + 1]) / 2) / 365 * pw; } : function (i) { return Lp + i / 365 * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var dg = cfg.digits == null ? 1 : cfg.digits;
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + fitText(cfg.title, W, 12) + '</text>';
    s += gridY(vmin, vmax, niceStep(vmax - vmin), Y, Lp, R + 8, W, dg);
    for (var m = 0; m < 12; m++) if (W > 470 || m % 2 === 0) s += '<text x="' + X((ME[m] + ME[m + 1]) / 2).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + MONTHS[m] + '</text>';
    var hl = (cfg.highlight || []).map(String).filter(function (y) { return cfg.years[y] && y !== cur; });
    ys.forEach(function (y, k) {
      if (y === cur || hl.indexOf(y) >= 0) return;
      s += segs(cfg.years[y].map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', .7, pickOp('others', .1 + .3 * k / Math.max(1, ys.length - 1)));
    });
    if (cfg.clim) s += segs(cfg.clim.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--soft)', 1.4, pickOp('clim', .95), '6 3');
    var leg = [];
    hl.forEach(function (y, k) {
      var col = ['1982', '1997', '2015', '2023'].indexOf(y) >= 0 ? 'var(--a' + y + ')' : 'var(--nina)';
      s += segs(cfg.years[y].map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), col, 1.4, pickOp(y, .95), dashOf(k + 1));
      leg.push([y, col, 1.4, dashOf(k + 1), y]);
    });
    var ca = cfg.years[cur] || [];
    s += segs(ca.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--ochre)', 2.4, pickOp('now'));
    var li = ca.length - 1; while (li >= 0 && !fin(ca[li])) li--;
    if (li >= 0) s += nowDot(X(li), Y(ca[li]), 'var(--ochre)', 4) + '<text x="' + (X(li) + 6).toFixed(0) + '" y="' + (Y(ca[li]) + 4).toFixed(0) + '" class="tt" font-size="10" style="fill:var(--ochre)">' + fnum(ca[li], dg, cfg.signed !== false) + '</text>';
    var items = [[cur + ' — this year', 'var(--ochre)', 2.4, '', 'now']].concat(leg);
    if (cfg.clim) items.push([cfg.climLabel || 'norm', 'var(--soft)', 1.4, '6 3', 'clim']);
    items.push([(ys.length - 1 - leg.length) + ' other years', 'var(--text)', .7, '', 'others']);
    s += legend(items, W, H, R, Tp);
    return s + '</svg>';
  }

  /* ДЛИННЫЕ РЯДЫ ПАНЕЛЯМИ: общая ось лет, у каждой панели своя шкала; десятилетия сеткой,
     годы начала сильных Эль-Ниньо тёплыми засечками. Столбики — для годовых приростов и аномалий. */
  function chartLong(items, W, H) {
    if (!items.length) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var RC = S._tight ? 8 : 84, gap = 14, hh = (H - 18 - gap * (items.length - 1)) / items.length;
    var xmin = Infinity, xmax = -Infinity;
    items.forEach(function (o) { xmin = Math.min(xmin, o.x[0]); xmax = Math.max(xmax, o.x[o.x.length - 1]); });
    var s = svgOpen(W, H) + hatchDefs();
    items.forEach(function (o, xi) {
      var top = 6 + xi * (hh + gap), Lp = 50, Tp = top + 14, pw = W - Lp - RC - 10, ph = hh - 24;
      var vv = o.y.filter(fin).concat((o.y2 || []).filter(fin));
      var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv), pad = (vmax - vmin) * .08; vmin -= pad; vmax += pad;
      if (o.bars) vmin = Math.min(0, vmin);
      var X = function (x) { return Lp + (x - xmin) / (xmax - xmin) * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
      s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw.toFixed(1) + '" height="' + ph.toFixed(1) + '" rx="5" style="fill:var(--ink)" opacity=".03"/>';
      s += '<text class="tt" x="' + Lp + '" y="' + (top + 9) + '" font-size="10">' + fitText(o.title, W - RC, 10) + '</text>';
      s += gridY(vmin, vmax, niceStep(vmax - vmin), Y, Lp, RC + 10, W, o.digits == null ? 0 : o.digits);
      for (var yr = Math.ceil(xmin / 10) * 10; yr <= xmax; yr += 10) {
        s += '<line x1="' + X(yr).toFixed(1) + '" y1="' + Tp + '" x2="' + X(yr).toFixed(1) + '" y2="' + (Tp + ph).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".5"/>';
        if (xi === items.length - 1) s += '<text x="' + X(yr).toFixed(0) + '" y="' + (H - 3) + '" text-anchor="middle">' + yr + '</text>';
      }
      ((S.PL || {}).elnino_years || []).forEach(function (ey) {
        if (ey >= xmin && ey <= xmax) s += '<line x1="' + X(ey + .5).toFixed(1) + '" y1="' + Tp + '" x2="' + X(ey + .5).toFixed(1) + '" y2="' + (Tp + ph).toFixed(1) + '" style="stroke:var(--nino)" stroke-width=".8" opacity=".35" stroke-dasharray="2 2"/>';
      });
      if (o.bars) {
        var bw = Math.max(1, pw / o.x.length - .5);
        o.y.forEach(function (v, i) {
          if (!fin(v)) return;
          var g = 'x="' + (X(o.x[i]) - bw / 2).toFixed(1) + '" y="' + Math.min(Y(0), Y(v)).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.abs(Y(v) - Y(0)).toFixed(1) + '"';
          s += '<rect ' + g + ' style="fill:' + (v >= 0 ? 'var(--nino)' : 'var(--nina)') + '" opacity=".8"/>' + (v < 0 ? '<rect ' + g + ' fill="url(#hneg)"/>' : '');
        });
      } else {
        s += segs(o.y.map(function (v, i) { return [X(o.x[i]), fin(v) ? Y(v) : NaN]; }), o.color || 'var(--text)', 1.4, 1);
        if (o.y2) s += segs(o.y2.map(function (v, i) { return [X(o.x[i]), fin(v) ? Y(v) : NaN]; }), 'var(--nino)', 1.2, .9, '5 3');
      }
      var li = o.y.length - 1; while (li > 0 && !fin(o.y[li])) li--;
      if (fin(o.y[li])) {
        s += nowDot(X(o.x[li]), Y(o.y[li]), 'var(--ochre)', 3.5);
        if (!S._tight) s += '<text x="' + (X(o.x[li]) + 7).toFixed(0) + '" y="' + (Y(o.y[li]) + 4).toFixed(0) + '" class="tt" font-size="10">' + fnum(o.y[li], o.digits == null ? 1 : o.digits, o.signed === true) + ' ' + esc(o.unit || '') + '</text>';
      }
    });
    return s + '</svg>';
  }

  function viewPlanet() {
    var PL = S.PL || {}, k = sub('planet', 'gases');
    var body = stageShell('The long record: the background the event runs on',
      [segBtn('planet', 'gases', 'Greenhouse gases', 'gases'), segBtn('planet', 'ice', 'Sea ice', 'gases'), segBtn('planet', 'temperature', 'Temperature', 'gases'), segBtn('planet', 'sea', 'Sea level', 'gases')]);
    if (!PL.built) { body.appendChild(el('div', 'note', 'No long-record data yet: run python tools/enso/planet.py.')); return; }
    var kp = el('div', 'kpis'), caps = [], EY = PL.elnino_years || [];
    function kpi(name, val, small, sub2, src, dt) { return '<div class="kpi"><div class="kn">' + name + '</div><div class="kv">' + val + '<small>' + esc(small || '') + '</small></div><div class="km">' + sub2 + '</div>' + kmeta(null, src, dt) + '</div>'; }
    function pickRow(opts, key, def) {
      var cur = S.sub[key] || def, row = el('div', 'seg sub');
      opts.forEach(function (o) { var b = el('button', cur === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub[key] = o[0]; render(); }; row.appendChild(b); });
      body.appendChild(row);
      return cur;
    }
    if (k === 'gases') {
      var G = PL.gases || {}, items = [];
      if (G.co2) items.push({ title: 'CO₂ at Mauna Loa, monthly mean; dashed: seasonally adjusted', unit: 'ppm', x: G.co2.months.map(ym2x), y: G.co2.values, y2: G.co2.trend, digits: 0 });
      if (G.co2 && G.co2.growth) items.push({ title: 'CO₂ annual growth at Mauna Loa', unit: 'ppm/yr', x: G.co2.growth.years, y: G.co2.growth.values, bars: true, digits: 1, signed: true });
      if (G.ch4) items.push({ title: 'CH₄, global monthly mean; dashed: trend', unit: 'ppb', x: G.ch4.months.map(ym2x), y: G.ch4.values, y2: G.ch4.trend, digits: 0 });
      if (G.n2o) items.push({ title: 'N₂O, global monthly mean; dashed: trend', unit: 'ppb', x: G.n2o.months.map(ym2x), y: G.n2o.values, y2: G.n2o.trend, digits: 0 });
      plot(body, function (w, h) { return chartLong(items, w, h); });
      [['co2', 'CO₂'], ['ch4', 'CH₄'], ['n2o', 'N₂O']].forEach(function (p) {
        var g = G[p[0]]; if (!g || !g.last) return; var L = g.last;
        kp.innerHTML += kpi(p[1] + ' · ' + esc(L.month), fnum(L.value, p[0] === 'co2' ? 1 : 0, false), ' ' + g.unit,
          (L.change_year != null ? fnum(L.change_year, 1) + ' ' + g.unit + ' on the year · ' : '') + (L.record ? 'the highest ' + monthName(L.month) + ' in the record' : ord(L.rank_same_month) + ' highest ' + monthName(L.month) + ' of ' + L.of),
          'NOAA Global Monitoring Laboratory', L.month);
      });
      caps.push('Mauna Loa CO₂ since 1958 (the Keeling curve), global CH₄ since 1983 and N₂O since 2001: NOAA Global Monitoring Laboratory. The saw-tooth is the northern growing season; the dashed line removes it. Warm dashed verticals mark the onset years of the strongest El Niños: the years after them, 1998 and 2016, stand out in the growth bars, because a warm and dry tropical year releases carbon from forests and soils.');
    } else if (k === 'ice') {
      var hemi = pickRow([['north', 'Arctic'], ['south', 'Antarctic']], 'planetIce', 'north');
      var I = (PL.ice || {})[hemi];
      if (I) {
        plot(body, function (w, h) { return chartYears({ title: I.label + ', daily, every year since ' + Object.keys(I.years).sort()[0], years: I.years, clim: I.clim, climLabel: 'median ' + I.clim_years.join('–'), highlight: EY, current: I.last.year, digits: 1, signed: false }, w, h); });
        var L = I.last, pct = fin(L.median_norm) && L.median_norm ? Math.round(100 * (L.value / L.median_norm - 1)) : null;
        kp.innerHTML += kpi(esc(I.label) + ' · ' + esc(L.date), fnum(L.value, 2, false), ' million km²',
          (pct != null ? (pct >= 0 ? '+' : '') + pct + ' % against the ' + I.clim_years.join('–') + ' median for the date · ' : '') + (L.rank_low === 1 ? 'the lowest for the date in the record' : ord(L.rank_low) + ' lowest for the date of ' + L.of + ' years') + ' · record low for the date: ' + fnum(L.extreme.value, 2, false) + ' in ' + L.extreme.year,
          'NSIDC Sea Ice Index v4', L.date);
      }
      caps.push('Sea ice extent from passive microwave satellites since October 1978 (NSIDC Sea Ice Index, version 4). Every year is a line; the current year in ochre, El Niño onset years by their dashes, the 1981–2010 median dashed grey. Click a legend entry to fade the rest. Days before 1988 were measured every other day and are filled in between.');
    } else if (k === 'temperature') {
      var RK = PL.regions_keys || [];
      var tk = pickRow([['t2_world', 'Land+ocean, daily'], ['sst_world', 'Ocean, daily'], ['land_m', 'Land, monthly'], ['t2_nh', 'N. hemisphere, daily'], ['t2_sh', 'S. hemisphere, daily'], ['t2_tropics', 'Tropics, daily'], ['t2_arctic', 'Arctic, daily'], ['t2_antarctic', 'Antarctic, daily'], ['hadcrut', 'Global, annual since 1850'], ['crutem', 'Land, annual since 1850']].filter(function (o) { return (PL.temperature || {})[o[0]] || RK.indexOf(o[0]) >= 0; }), 'planetTemp', 't2_world');
      /* Пояса лежат в своём файле (1,3 МБ) и берутся по первому запросу (владелец 08.09: «интересная разбивка, давай возьмём»). */
      if (RK.indexOf(tk) >= 0 && !S.PLR) {
        if (!S._plrLoad) { S._plrLoad = get('/data/enso/planet-regions.json').then(function (d) { S.PLR = d; if (S.view === 'planet') render(); }).catch(function () { S.PLR = { temperature: {} }; if (S.view === 'planet') render(); }); }
        body.appendChild(el('div', 'note', 'Loading the regional series…'));
        return;
      }
      var T2 = RK.indexOf(tk) >= 0 ? ((S.PLR || {}).temperature || {})[tk] : (PL.temperature || {})[tk], annual = tk === 'hadcrut' || tk === 'crutem';
      if (T2 && T2.monthly) {
        /* Суша по месяцам, каждый год линией — как суточные ряды, только двенадцать точек в году
           (владелец 08.09: «аналогично Ocean, daily»; суточной суши в открытых источниках нет). */
        var hlM = []; EY.forEach(function (y) { hlM.push(y); if (T2.years[String(y + 1)]) hlM.push(y + 1); });
        plot(body, function (w, h) { return chartYears({ title: 'Land air temperature, monthly anomaly against ' + T2.base + ' (NOAA NCEI), every year since ' + Object.keys(T2.years).sort()[0] + '; dashed: ' + T2.clim_years.join('–') + ' mean', years: T2.years, clim: T2.clim, climLabel: 'mean ' + T2.clim_years.join('–'), highlight: hlM, monthly: true, digits: 2, signed: true }, w, h); });
        var LM = T2.last;
        kp.innerHTML += kpi('Land, monthly · ' + esc(LM.date), fnum(LM.value, 2), ' °C', (fin(LM.median_norm) ? fnum(LM.value - LM.median_norm, 2) + ' against the ' + T2.clim_years.join('–') + ' mean for the month · ' : '') + (LM.rank_high === 1 ? 'the warmest ' + MONTHS[LM.month - 1] + ' in the record' : ord(LM.rank_high) + ' warmest ' + MONTHS[LM.month - 1] + ' of ' + LM.of) + ' · record ' + LM.record.year + ' at ' + fnum(LM.record.value, 2), 'NOAA NCEI Climate at a Glance, land only', LM.date);
        caps.push('Global land-only air temperature by month, NOAA NCEI Climate at a Glance, anomalies against 1901–2000, every year as a line with the 1991–2020 monthly mean dashed. No daily land-only series exists in the open near-real-time sources (climatereanalyzer and Climate Pulse publish land+ocean and ocean; Berkeley Earth daily stops in 2022), so the month is the finest step for land. Highlighted: the onset years of the strongest El Niños and the years after them.');
      } else if (T2 && !annual) {
        var hlT = []; EY.forEach(function (y) { hlT.push(y); if (T2.years[String(y + 1)]) hlT.push(y + 1); });
        plot(body, function (w, h) { return chartYears({ title: T2.label + ': daily mean, every year since ' + Object.keys(T2.years).sort()[0] + '; dashed: ' + T2.clim_years.join('–') + ' mean', years: T2.years, clim: T2.clim, climLabel: 'mean ' + T2.clim_years.join('–'), highlight: hlT, current: T2.last.year, digits: 1, signed: false }, w, h); });
        var LT = T2.last;
        kp.innerHTML += kpi(esc(T2.label) + ' · ' + esc(LT.date), fnum(LT.value, 2, false), ' °C', (fin(LT.median_norm) ? fnum(LT.value - LT.median_norm, 2) + ' against the ' + T2.clim_years.join('–') + ' mean for the date · ' : '') + (LT.rank_high === 1 ? 'the warmest for the date in the record' : ord(LT.rank_high) + ' warmest for the date of ' + LT.of + ' years') + ' · record for the date: ' + fnum(LT.extreme.value, 2, false) + ' in ' + LT.extreme.year, tk === 'sst_world' ? 'NOAA OISST via climatereanalyzer' : 'ECMWF ERA5 via climatereanalyzer', LT.date);
        caps.push('The same daily series as on Dynamics, but every year at once, as on climatereanalyzer: absolute daily means, with the 1991–2020 mean dashed. Highlighted: the onset years of the strongest El Niños and the years after them, when the air answers the ocean.');
      } else if (T2) {
        var isLand = tk === 'crutem', DS = isLand ? 'CRUTEM5' : 'HadCRUT5';
        var TG = (PL.temperature || {}).hadcrut;   // суша отдельно, а рядом — глобальный ряд тонкой линией для масштаба
        plot(body, function (w, h) { return chartLong([{ title: (isLand ? 'Land air temperature, annual anomaly against 1961–1990 (CRUTEM5)' : 'Global mean temperature, annual anomaly against 1961–1990 (HadCRUT5)'), unit: '°C', x: T2.years, y: T2.values, bars: true, digits: 1, signed: true }], w, h); });
        var LH = T2.last;
        kp.innerHTML += kpi(DS + ' · ' + LH.year, fnum(LH.value, 2), ' °C', (LH.rank === 1 ? 'the warmest year in the record' : ord(LH.rank) + ' warmest year of ' + LH.of) + ' · warmest: ' + LH.warmest.year + ' at ' + fnum(LH.warmest.value, 2) + (isLand && TG && TG.last ? ' · global that year ' + fnum(TG.last.value, 2) : ''), 'Met Office HadCRUT5', String(LH.year));
        caps.push(isLand ? 'Annual land air temperature since 1850, Met Office CRUTEM5, against the 1961–1990 baseline: land warms about twice as fast as the ocean, so its anomaly runs ahead of the global one. The years after strong El Niños stand out on land too.' : 'Annual global mean temperature since 1850, Met Office HadCRUT5, against the 1961–1990 baseline (the usual pre-industrial reference is about 0.36 °C below it). Red bars above the baseline, blue below with hatching. The years after strong El Niños, 1998, 2016 and 2024, each set the record of their time.');
      }
    } else {
      var SL = PL.sea_level;
      if (SL && SL.years) {
        plot(body, function (w, h) { return chartLong([{ title: 'Global mean sea level from satellite altimetry, against the start of the record', unit: 'mm', x: SL.years, y: SL.values, digits: 0, signed: true }], w, h); });
        var LS = SL.last;
        if (LS) kp.innerHTML += kpi('Sea level · ' + String(LS.year).slice(0, 4), fnum(LS.since_start, 0), ' mm since ' + String(LS.start).slice(0, 4), 'rate ' + fnum(LS.rate_all_mm_per_year, 1, false) + ' mm per year over the record' + (LS.rate_10y_mm_per_year != null ? ', ' + fnum(LS.rate_10y_mm_per_year, 1, false) + ' over the last ten years' : ''), 'NOAA STAR altimetry', String(LS.year).slice(0, 4));
        caps.push('Global mean sea level from TOPEX/Poseidon and the Jason satellites since 1993, NOAA STAR, seasonal signal removed, no glacial isostatic adjustment. El Niño years bulge above the trend: a warm Pacific holds more water on the ocean and less on land.');
      } else body.appendChild(el('div', 'note', 'Sea level: the source did not answer yet.'));
    }
    if (kp.innerHTML) body.appendChild(kp);
    var srcs = (PL.sources || []).filter(function (s) { return s.fresh === false; }).map(function (s) { return s.label; });
    body.appendChild(el('div', 'cap', caps.join(' ') + ' ' + esc(PL.note || '') + ' Built ' + esc(PL.built || '') + (srcs.length ? '; did not answer this time: ' + esc(srcs.join('; ')) : '') + '. ' + vLink('sources and their date ranges', 'ops', 'sources')));
  }

  /* ХОВМЁЛЛЕР (владелец 07.09: «как движется тепло — самый важный фактор для прогноза»).
     Время вниз по странице, долгота поперёк; волна Кельвина — тёплая полоса, сползающая с запада
     на восток. Слева это событие, справа прошлое сильное на тех же календарных месяцах,
     сдвинутых на годы. Данные data/enso/hovmoller.json (GODAS, месяц, наша климатология). */
  function chartHovmoller(HV, W, H, opts) {
    var cur = HV.current || {}, metric = (opts && opts.metric) || 'anom100', an = (opts && opts.analog) ? (HV.analogs || {})[opts.analog] : null;
    if (!cur.months || !cur.months.length) return svgOpen(W, H) + '<text x="20" y="40">no Hovmöller data yet</text></svg>';
    var lons = cur.lons, nL = lons.length, vmax = metric === 'anom100' ? 4 : 40, unit = metric === 'anom100' ? '°C' : 'm';
    var months = cur.months.slice(), curY = parseInt(months[months.length - 1].slice(0, 4), 10);
    var ahead = an ? 12 : 0;                       // у аналога показываем ещё год вперёд: что было дальше
    var lastYm = months[months.length - 1], ly = parseInt(lastYm.slice(0, 4), 10), lm = parseInt(lastYm.slice(5, 7), 10);
    for (var k = 1; k <= ahead; k++) { var mm = lm + k, yy = ly + Math.floor((mm - 1) / 12); mm = ((mm - 1) % 12) + 1; months.push(yy + '-' + (mm < 10 ? '0' : '') + mm); }
    var nR = months.length, panels = an ? 2 : 1;
    var Lp = 52, R = 12, Tp = 30, B = 36, gap = 26, pw = (W - Lp - R - gap * (panels - 1)) / panels, ph = H - Tp - B;
    var cw = pw / nL, rh = ph / nR;
    var s = svgOpen(W, H) + hatchDefs();
    function cell(v) { var a = Math.min(1, Math.abs(v) / vmax); return { fill: v >= 0 ? 'var(--nino)' : 'var(--nina)', op: (.08 + .92 * a).toFixed(2), neg: v < 0 }; }
    function panel(x0, rows, title, offsetYears) {
      s += '<text class="tt" x="' + x0 + '" y="' + (Tp - 14) + '" font-size="11">' + fitText(title, pw, 11) + '</text>';
      s += '<rect x="' + x0 + '" y="' + Tp + '" width="' + pw.toFixed(1) + '" height="' + ph.toFixed(1) + '" style="fill:var(--ink)" opacity=".03"/>';
      months.forEach(function (ym, r) {
        var key = offsetYears ? (parseInt(ym.slice(0, 4), 10) + offsetYears) + ym.slice(4) : ym;
        var i = rows.months ? rows.months.indexOf(key) : -1;
        var row = i >= 0 ? rows[metric][i] : null;
        var y = Tp + r * rh;
        if (row) row.forEach(function (v, j) {
          if (!fin(v)) return;
          var c = cell(v), g = 'x="' + (x0 + j * cw).toFixed(2) + '" y="' + y.toFixed(2) + '" width="' + (cw + .3).toFixed(2) + '" height="' + (rh + .3).toFixed(2) + '"';
          s += '<rect ' + g + ' style="fill:' + c.fill + '" opacity="' + c.op + '"/>' + (c.neg && Math.abs(v) > vmax * .25 ? '<rect ' + g + ' fill="url(#hneg)" opacity=".5"/>' : '');
        });
        if (ym.slice(5) === '01' || r === 0) s += '<line x1="' + x0 + '" y1="' + y.toFixed(1) + '" x2="' + (x0 + pw).toFixed(1) + '" y2="' + y.toFixed(1) + '" style="stroke:var(--soft)" stroke-width=".6" opacity=".7"/>';
      });
      // подписи долгот: каждые 30°
      lons.forEach(function (L, j) { if (Math.abs(L % 30) < .6) s += '<line x1="' + (x0 + j * cw).toFixed(1) + '" y1="' + Tp + '" x2="' + (x0 + j * cw).toFixed(1) + '" y2="' + (Tp + ph).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".5"/><text x="' + (x0 + j * cw).toFixed(0) + '" y="' + (H - 20) + '" text-anchor="middle">' + esc(cur.labels[j]) + '</text>'; });
    }
    panel(Lp, cur, (metric === 'anom100' ? 'Anomaly at ' + Math.round(cur.level) + ' m' : 'Thermocline (20 °C) depth anomaly') + ', this event, ' + months[0] + ' → ' + lastYm, 0);
    if (an) {
      var ay = parseInt(opts.analog, 10), off = ay - curY;
      panel(Lp + pw + gap, an, 'Beside ' + opts.analog + '–' + (ay + 1) + ', same months, plus the year after', off);
    }
    // подписи месяцев слева и строка «сейчас»
    months.forEach(function (ym, r) {
      var y = Tp + r * rh;
      if (ym.slice(5) === '01' || ym.slice(5) === '07' || r === nR - 1) s += '<text x="' + (Lp - 6) + '" y="' + (y + rh * .5 + 3).toFixed(1) + '" text-anchor="end" font-size="9">' + esc(ym) + '</text>';
      if (ym === lastYm) s += '<rect x="' + (Lp - 2) + '" y="' + y.toFixed(1) + '" width="' + (pw + 4).toFixed(1) + '" height="' + rh.toFixed(1) + '" fill="none" style="stroke:var(--ochre)" stroke-width="1.4"/>' + '<text x="' + (Lp + pw + 4) + '" y="' + (y + rh * .5 + 3).toFixed(1) + '" font-size="9" style="fill:var(--ochre)">' + (an ? '' : 'now') + '</text>';
    });
    s += '<text x="' + (W - R) + '" y="' + (H - 4) + '" text-anchor="end" font-size="9" style="fill:var(--soft)">red warm · blue cold (hatched) · full colour at ±' + vmax + ' ' + unit + '</text>';
    return s + '</svg>';
  }

  /* ЦЕНЫ В АБСОЛЮТНЫХ ЧИСЛАХ (владелец 07.09: «привык видеть в абсолютных ценах», затем «сравнение
     с нашими годами и следующий год тоже»). Один товар — линия в долларах за тонну за пять лет,
     начало события полосой; тонкие линии — те же месяцы после начала прошлых событий, переведённые
     в сегодняшние доллары через цену месяца начала (в процентах они лежат на вкладке Since onset).
     Ось времени тянется до +24 месяцев от начала: видно, куда шли цены и на следующий год. */
  function chartPrice(c, W, H, opts) {
    opts = opts || {};
    var mini = !!opts.mini, P = opts.paths || null;
    var ser = c.series || {}, m = (ser.months || []).slice(), v = (ser.values || []).slice(), nS = m.length;
    if (nS < 2) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var io = c.onset ? m.indexOf(c.onset) : -1, span = P && P.span ? P.span : 24;
    // хвост будущих месяцев до +span от начала, чтобы прошлые пути дошли до следующего года
    if (io >= 0 && P) {
      var ly = parseInt(m[nS - 1].slice(0, 4), 10), lm = parseInt(m[nS - 1].slice(5, 7), 10);
      while (m.length < io + span + 1) { lm += 1; if (lm > 12) { lm = 1; ly += 1; } m.push(ly + '-' + (lm < 10 ? '0' : '') + lm); }
    }
    var n = m.length, base = io >= 0 ? v[io] : null;
    /* ПРИВЯЗКА ПУТЕЙ (владелец 07.09: «почему все линии сходятся в одной точке»): пути прошлых
       событий лежат в процентах к месяцу своего начала, в долларах их нельзя положить рядом
       (пшеница 1982 года стоила 160). 'onset' — все проходят через нашу цену месяца начала;
       'now' — через сегодняшнюю цену: тогда читается «куда дальше с сегодняшней точки». */
    var align = opts.align || 'onset', kNow = nS - 1 - io;
    var an = P && base ? Object.keys(P.analogs || {}).sort().map(function (y) {
      var r = P.analogs[y], from = r.from != null ? r.from : -6, fac = base / 100;
      if (align === 'now') { var pvNow = r.values[kNow - from]; fac = fin(pvNow) && pvNow ? v[nS - 1] / pvNow : NaN; }
      return { y: y, pts: r.values.map(function (pv, k) { var i = io + from + k; return [i, fin(pv) && fin(fac) && i >= 0 && i < n ? fac * pv : NaN]; }) };
    }) : [];
    var Lp = mini ? 44 : 56, R = mini ? 10 : 16, Tp = mini ? 20 : 26, B = mini ? 18 : 26, pw = W - Lp - R, ph = H - Tp - B;
    var vv = v.filter(fin); an.forEach(function (a) { a.pts.forEach(function (q) { if (fin(q[1])) vv.push(q[1]); }); });
    var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv), pad = (vmax - vmin) * .12 || 1;
    vmin = Math.max(0, vmin - pad); vmax += pad * (mini ? 1.2 : 1.6);
    var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (x) { return Tp + (vmax - x) / (vmax - vmin) * ph; };
    var unit = (c.unit || '').replace(/[()]/g, '');
    var s = svgOpen(W, H) + hatchDefs() + '<text class="tt" x="' + Lp + '" y="' + (mini ? 12 : 15) + '" font-size="' + (mini ? 11 : 12) + '"' + (mini ? ' font-weight="600"' : '') + '>' + fitText(esc(mini ? c.name.replace(/,.*$/, '') + ', ' + unit : c.name + ', ' + unit + ', monthly, ' + m[0] + ' → ' + m[nS - 1]), W, mini ? 11 : 12) + '</text>';
    var step = niceStep(vmax - vmin, Math.max(3, Math.floor(ph / (mini ? 30 : 26))));
    for (var g = Math.ceil(vmin / step) * step; g < vmax; g += step) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 3.5).toFixed(1) + '" text-anchor="end" font-size="9">' + fnum(g, g < 10 ? 1 : 0, false) + '</text>';
    for (var i = 0; i < n; i++) if (m[i].slice(5) === '01') s += '<line x1="' + X(i).toFixed(1) + '" y1="' + Tp + '" x2="' + X(i).toFixed(1) + '" y2="' + (Tp + ph) + '" style="stroke:var(--grid)" stroke-width=".5"/><text x="' + X(i).toFixed(1) + '" y="' + (H - (mini ? 5 : 9)) + '" text-anchor="middle" font-size="9">' + m[i].slice(0, 4) + '</text>';
    if (io >= 0) {
      s += '<rect x="' + X(io).toFixed(1) + '" y="' + Tp + '" width="' + (X(nS - 1) - X(io)).toFixed(1) + '" height="' + ph + '" style="fill:var(--nino)" opacity=".07"/>';
      if (n > nS) s += '<rect x="' + X(nS - 1).toFixed(1) + '" y="' + Tp + '" width="' + (X(n - 1) - X(nS - 1)).toFixed(1) + '" height="' + ph + '" style="fill:var(--ink)" opacity=".035"/>' + (mini ? '' : '<text x="' + (X(n - 1) - 4).toFixed(1) + '" y="' + (Tp + ph - 6) + '" text-anchor="end" font-size="9" style="fill:var(--soft)">ahead: where the past events went, in today’s dollars</text>');
      s += '<line x1="' + X(io).toFixed(1) + '" y1="' + Tp + '" x2="' + X(io).toFixed(1) + '" y2="' + (Tp + ph) + '" style="stroke:var(--ochre)" stroke-dasharray="5 3" stroke-width="1.2"/>' + (mini ? '' : '<text x="' + (X(io) + (X(io) > W - 130 ? -4 : 4)).toFixed(1) + '" y="' + (Tp + 11) + '" font-size="9" text-anchor="' + (X(io) > W - 130 ? 'end' : 'start') + '" style="fill:var(--ochre)">event began ' + esc(c.onset) + '</text>');
    }
    an.forEach(function (a) { s += segs(a.pts.map(function (q) { return [X(q[0]), fin(q[1]) ? Y(q[1]) : NaN]; }), 'var(--a' + a.y + ')', (mini ? 1.2 : 1.6) * (S.pick === a.y ? 1.8 : 1), pickOp(a.y, 1), yearDash(a.y)); });
    s += poly(v.map(function (x, i) { return [X(i), fin(x) ? Y(x) : NaN]; }), 'var(--text)', mini ? 1.8 : 2.4, pickOp('now', 1));
    var lo = v.indexOf(Math.min.apply(null, v.filter(fin))), hiI = v.indexOf(Math.max.apply(null, v.filter(fin)));
    if (!mini) {
      s += '<line x1="' + Lp + '" y1="' + Y(v[hiI]).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(v[hiI]).toFixed(1) + '" style="stroke:var(--nino)" stroke-width=".8" stroke-dasharray="2 3"/><text x="' + (W - R) + '" y="' + (Y(v[hiI]) - 3).toFixed(1) + '" text-anchor="end" font-size="9" style="fill:var(--nino)">five-year high ' + fnum(v[hiI], v[hiI] > 100 ? 0 : 2, false) + ' · ' + m[hiI] + '</text>';
      s += '<line x1="' + Lp + '" y1="' + Y(v[lo]).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(v[lo]).toFixed(1) + '" style="stroke:var(--nina)" stroke-width=".8" stroke-dasharray="2 3"/><text x="' + (W - R) + '" y="' + (Y(v[lo]) + 10).toFixed(1) + '" text-anchor="end" font-size="9" style="fill:var(--nina)">low ' + fnum(v[lo], v[lo] > 100 ? 0 : 2, false) + ' · ' + m[lo] + '</text>';
      if (nS > 13 && fin(v[nS - 13])) s += '<circle cx="' + X(nS - 13).toFixed(1) + '" cy="' + Y(v[nS - 13]).toFixed(1) + '" r="3" fill="none" style="stroke:var(--text)" stroke-width="1.2"/><text x="' + X(nS - 13).toFixed(1) + '" y="' + (Y(v[nS - 13]) - 7).toFixed(1) + '" text-anchor="middle" font-size="9">a year ago ' + fnum(v[nS - 13], v[nS - 13] > 100 ? 0 : 2, false) + '</text>';
    }
    s += nowDot(X(nS - 1), Y(v[nS - 1]), 'var(--text)', mini ? 3 : 4) + '<text x="' + (X(nS - 1) - 6).toFixed(1) + '" y="' + (Y(v[nS - 1]) - 8).toFixed(1) + '" text-anchor="end" font-size="' + (mini ? 9 : 10) + '" font-weight="600">' + fnum(v[nS - 1], v[nS - 1] > 100 ? 0 : 2, false) + '</text>';
    if (an.length && !mini) s += legendAt([['now', 'var(--text)', 2.4, '', 'now']].concat(an.map(function (a) { return [a.y + ' (' + P.analogs[a.y].onset + ')', 'var(--a' + a.y + ')', 1.6, yearDash(a.y), a.y]; })), Lp + 8, Tp + 14);
    return s + '</svg>';
  }

  /* ПУЧОК (владелец 07.09): все текущие ряды приведены к месяцу начала события, без прошлых лет. */
  var BUNDLE_COLORS = ['#8B2E2E', '#B06A8F', '#7D5B8F', '#2F6F8F', '#3E8E6E', '#C07B53', '#D08A2B', '#5A5A5A', '#A34E8C', '#4F7F3F', '#8A6A3A', '#2B7A99'];
  function chartBundle(items, W, H) {
    var rows = items.map(function (it, i) {
      var ser = it.series || {}, m = ser.months || [], v = ser.values || [], io = it.onset ? m.indexOf(it.onset) : -1, base = io >= 0 ? v[io] : null;
      return { it: it, m: m, io: io, vals: base ? v.map(function (x) { return fin(x) ? 100 * x / base : NaN; }) : [], color: BUNDLE_COLORS[i % BUNDLE_COLORS.length], dash: dashOf(Math.floor(i / 3)) };
    }).filter(function (r) { return r.vals.length && r.io >= 0; });
    if (!rows.length) return svgOpen(W, H) + '<text x="20" y="40">no onset yet</text></svg>';
    var m = rows[0].m, n = m.length, io = rows[0].io;
    var Lp = 46, R = 16, Tp = 30, B = 26, pw = W - Lp - R, ph = H - Tp - B;
    var all = []; rows.forEach(function (r) { r.vals.forEach(function (x) { if (fin(x)) all.push(x); }); });
    /* Шкала по 95-му процентилю: один пик какао в 400 % сплющивал остальные одиннадцать
       линий в полосу; что выше — обрезается, и об этом сказано в заголовке. */
    /* ЛОГАРИФМИЧЕСКАЯ ШКАЛА (владелец 07.09: «какао упёрлось в потолок»): проценты к базе
       естественно читаются по логарифму — вдвое вверх и вдвое вниз на одинаковом расстоянии;
       пик какао в 400 % влезает целиком, а остальные не сплющиваются в полосу. */
    var vmin = Math.min.apply(null, all) / 1.08, vmax = Math.max.apply(null, all) * 1.25, L0 = Math.log(vmin), L1 = Math.log(vmax);
    var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (x) { return Tp + (L1 - Math.log(x)) / (L1 - L0) * ph; };
    var s = svgOpen(W, H) + hatchDefs() + '<text class="tt" x="' + Lp + '" y="15">' + fitText('All commodities as % of their price in the onset month (' + m[io] + ' = 100), this event only; log scale', W, 12) + '</text>';
    [30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300, 400, 500].forEach(function (g) { if (g > vmin && g < vmax) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(1) + '" style="stroke:var(--grid)" stroke-width="' + (g === 100 ? 1.4 : .6) + '"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 3.5).toFixed(1) + '" text-anchor="end" font-size="9">' + g + '</text>'; });
    for (var i = 0; i < n; i++) if (m[i].slice(5) === '01') s += '<line x1="' + X(i).toFixed(1) + '" y1="' + Tp + '" x2="' + X(i).toFixed(1) + '" y2="' + (Tp + ph) + '" style="stroke:var(--grid)" stroke-width=".5"/><text x="' + X(i).toFixed(1) + '" y="' + (H - 9) + '" text-anchor="middle" font-size="9">' + m[i].slice(0, 4) + '</text>';
    s += '<rect x="' + X(io).toFixed(1) + '" y="' + Tp + '" width="' + (X(n - 1) - X(io)).toFixed(1) + '" height="' + ph + '" style="fill:var(--nino)" opacity=".07"/>';
    s += '<line x1="' + X(io).toFixed(1) + '" y1="' + Tp + '" x2="' + X(io).toFixed(1) + '" y2="' + (Tp + ph) + '" style="stroke:var(--ochre)" stroke-dasharray="5 3" stroke-width="1.2"/><text x="' + (X(io) + 4).toFixed(1) + '" y="' + (Tp + 11) + '" font-size="9" style="fill:var(--ochre)">event began ' + esc(m[io]) + '</text>';
    rows.forEach(function (r) {
      s += segs(r.vals.map(function (x, i) { return [X(i), fin(x) ? Y(x) : NaN]; }), r.color, S.pick === r.it.key ? 2.8 : 1.5, pickOp(r.it.key, 1), r.dash);
      var last = r.vals[n - 1];
      if (fin(last)) s += '<text x="' + (X(n - 1) + 3) + '" y="' + (Y(last) + 3).toFixed(1) + '" font-size="8.5" style="fill:' + r.color + '" opacity="' + pickOp(r.it.key, 1) + '">' + fnum(last, 0, false) + '</text>';
    });
    s += legendAt(rows.map(function (r) { return [r.it.name.replace(/,.*$/, '') + ' ' + fnum(r.vals[n - 1], 0, false), r.color, 1.5, r.dash, r.it.key]; }), Lp + 8, Tp + 14);
    return s + '</svg>';
  }

  /* РАЗРЕЗ МЕСЯЦ ЗА МЕСЯЦЕМ (владелец 07.09: «динамику показывать, тепловую карту анимировать»).
     Кадры — полные разрезы GODAS из hovmoller.json (это событие) и sections-<год>.json (прошлые,
     грузятся по требованию). Таймер двигает кадр и перерисовывает график; уход со сцены
     останавливает таймер (render). */
  function animStop() { if (S.animT) { clearInterval(S.animT); S.animT = null; } }
  function sectionFrames() { return ((S.HV || {}).sections) || null; }
  function viewOceanMotion(body) {
    var SC = sectionFrames();
    if (!SC || !SC.months || !SC.months.length) { body.appendChild(el('div', 'note', 'The month-by-month frames are not built yet: run subsurface.py --hov.')); return; }
    var n = SC.months.length, ha = S.sub.animAnalog == null ? '1997' : S.sub.animAnalog;
    if (S.animI == null || S.animI >= n) S.animI = n - 1;
    var AN = ha ? (S.SEC || {})[ha] : null;
    if (ha && !AN && !(S.SECload || {})[ha]) {
      S.SECload = S.SECload || {}; S.SECload[ha] = true;
      get('/data/enso/sections-' + ha + '.json').then(function (d) { S.SEC = S.SEC || {}; S.SEC[ha] = d; if (S.view === 'ocean') render(); }).catch(function () { S.SECload[ha] = 'failed'; if (S.view === 'ocean') render(); });
    }
    var row = el('div', 'seg sub');
    var bPlay = el('button', S.animT ? 'on' : '', S.animT ? '❚❚ pause' : '▶ play'); bPlay.type = 'button';
    bPlay.onclick = function () {
      if (S.animT) { animStop(); bPlay.textContent = '▶ play'; bPlay.className = ''; return; }
      if (S.animI >= n - 1) S.animI = 0;
      S.animT = setInterval(function () {
        if (!S.plotEl || !S.plotEl.isConnected) { animStop(); return; }
        S.animI = (S.animI + 1) % n; rng.value = S.animI; lab.textContent = SC.months[S.animI]; S.pw = 0; redrawPlot();
        if (S.animI === n - 1) { animStop(); bPlay.textContent = '▶ play'; bPlay.className = ''; }
      }, 650);
      bPlay.textContent = '❚❚ pause'; bPlay.className = 'on';
    };
    row.appendChild(bPlay);
    var rng = document.createElement('input'); rng.type = 'range'; rng.min = 0; rng.max = n - 1; rng.value = S.animI; rng.style.cssText = 'flex:1;min-width:120px;max-width:360px;align-self:center';
    var lab = el('span', 'mono', SC.months[S.animI]); lab.style.cssText = 'align-self:center;font-size:12px;min-width:56px';
    rng.oninput = function () { animStop(); bPlay.textContent = '▶ play'; bPlay.className = ''; S.animI = +rng.value; lab.textContent = SC.months[S.animI]; S.pw = 0; redrawPlot(); };
    row.appendChild(rng); row.appendChild(lab); row.appendChild(el('span', 'seg-gap', ''));
    [['', 'this event alone']].concat(Object.keys((S.HV || {}).analogs || {}).sort().map(function (y) { return [y, 'beside ' + y]; })).forEach(function (o) { var b = el('button', ha === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { animStop(); S.sub.animAnalog = o[0]; render(); }; row.appendChild(b); });
    body.appendChild(row);
    plot(body, function (w, h) {
      var i = S.animI, ym = SC.months[i], cur = { title: 'This event · ' + ym, cols: SC.labels, rows: SC.levels, get: function (a, b) { return SC.anom[i][b][a]; }, d20: SC.d20[i], d20clim: SC.d20_clim[i], legendNote: 'GODAS, monthly', vmax: 10 };
      var A2 = ha ? (S.SEC || {})[ha] : null;
      if (!A2) return chartSection(cur, w, h);
      var ay = parseInt(ha, 10), cy = parseInt(SC.months[n - 1].slice(0, 4), 10), key = (parseInt(ym.slice(0, 4), 10) + (ay - cy)) + ym.slice(4), j = A2.months.indexOf(key);
      var half = (w - 10) / 2, left = chartSection(cur, half, h), right;
      if (j < 0) right = svgOpen(half, h) + '<text x="20" y="40" font-size="11">' + esc(ha) + ': no frame for ' + esc(key) + '</text></svg>';
      else right = chartSection({ title: ha + ' event · ' + key, cols: A2.labels, rows: A2.levels, get: function (a, b) { return A2.anom[j][b][a]; }, d20: A2.d20[j], d20clim: A2.d20_clim[j], legendNote: 'same month', vmax: 10 }, half, h);
      // два SVG в одной картинке: вкладываем как <svg x=…>
      return svgOpen(w, h) + left.replace(/^<svg /, '<svg x="0" width="' + half + '" height="' + h + '" ') + right.replace(/^<svg /, '<svg x="' + (half + 10) + '" width="' + half + '" height="' + h + '" ') + '</svg>';
    });
    var mx = SC.max[S.animI], kh = el('div', 'kpis');
    kh.innerHTML = (mx ? '<div class="kpi"><div class="kn">warmest anomaly · ' + esc(SC.months[S.animI]) + '</div><div class="kv">' + fnum(mx.value, 1) + '<small> °C at ' + mx.depth + ' m</small></div><div class="km">' + esc(mx.label) + '</div>' + kmeta(null, 'GODAS via PSL', SC.months[S.animI]) + '</div>' : '') +
      '<div class="kpi"><div class="kn">frames</div><div class="kv" style="font-size:17px">' + n + ' months</div><div class="km">' + esc(SC.months[0]) + ' → ' + esc(SC.months[n - 1]) + (ha ? '; the ' + esc(ha) + ' event on the same calendar months' : '') + '</div>' + kmeta(null, 'GODAS, our climatology', SC.months[n - 1]) + '</div>';
    body.appendChild(kh);
    body.appendChild(el('div', 'cap', 'The reanalysis section along the equator, one frame per month: red warmer than normal, blue colder with hatching, the solid line the 20 °C isotherm now and the dashed one its normal depth. Play it and watch the warm water slide east and up along the thermocline. Beside it the same calendar month of a past strong event, shifted by whole years. ' + (ha && (S.SECload || {})[ha] === 'failed' ? 'The ' + esc(ha) + ' frames did not load. ' : '') + vLink('the Hovmöller diagram of the same motion', 'ocean', 'hovmoller') + ' ' + vLink('the last month in full', 'ocean', 'section')));
  }

  /* СПЕКТРАЛЬНЫЙ СТОРОЖ (владелец 07.09: «ищем не под фонарём, просто появление сигнала на
     какой-то частоте, пока его нет и это хорошо»). Таблица из data/enso/spectral.json: у каждого
     дневного ряда отношение мощности к красному фону на периодах 2…7 суток за последние 30 дней,
     процентиль истории, те же окна в наши годы. Числа считает spectral.py, здесь только показ. */
  function viewSpectral(body) {
    var SP = S.SP || {}, ser = SP.series || [], TH = SP.thresholds || { chi95: 3.0, chi99: 4.6 }, per = SP.periods || [2, 3, 4, 5, 6, 7];
    if (!SP.built) { body.appendChild(el('div', 'note', 'No spectral watch yet: run python tools/enso/spectral.py.')); return; }
    body.classList.add('scroll');
    function cell(v) { if (!fin(v)) return '<td class="num">·</td>'; var c = v >= TH.chi99 ? ' top' : (v >= TH.chi95 ? ' warn' : ''); return '<td class="num' + c + '">' + fnum(v, 1, false) + '</td>'; }
    var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
    wrap.innerHTML = '<table class="e"><thead><tr><th>series</th><th>verdict</th>' + per.map(function (p) { return '<th class="num">' + p + ' d</th>'; }).join('') +
      '<th class="num">band 2–7 d</th><th class="num">history pct</th><th>same window in our years</th></tr></thead><tbody>' +
      ser.map(function (s) {
        if (s.error) return '<tr><td>' + esc(s.label) + '</td><td class="st-bad" colspan="' + (per.length + 4) + '">' + esc(s.error) + '</td></tr>';
        var nw = s.now, h = s.history, an = s.analogs || {};
        var vcls = s.verdict === 'signal' ? ' st-bad' : (s.verdict === 'candidate' ? ' top' : (s.verdict === 'weak' ? ' warn' : ' st-ok'));
        return '<tr><td>' + esc(s.label) + '<div class="sub">' + esc(s.window[0]) + ' → ' + esc(s.window[1]) + '</div></td>' +
          '<td class="' + vcls + '"><b>' + esc(s.verdict) + '</b>' + (s.persist_updates ? '<div class="sub">' + s.persist_updates + ' update(s) at 99 %</div>' : '') + '</td>' +
          per.map(function (p) { return cell(nw.lines[String(p)]); }).join('') +
          '<td class="num">' + fnum(nw.band_share * 100, 0, false) + ' %</td>' +
          '<td class="num">' + (h ? h.max_line_pct + ' %<div class="sub">p95 ' + fnum(h.max_line_p95, 1, false) + ' · ' + h.share_of_windows_with_line_99 + ' % of windows had a 99 % line</div>' : '<span class="sub">no history</span>') + '</td>' +
          '<td class="act">' + (Object.keys(an).length ? Object.keys(an).sort().map(function (y) { return y + ': ' + fnum(an[y].max_line, 1, false) + ' at ' + an[y].max_period + ' d'; }).join(' · ') : '<span class="sub">none</span>') + '</td></tr>';
      }).join('') + '</tbody></table>';
    body.appendChild(wrap);
    body.appendChild(el('div', 'cap', esc(SP.note || '') + ' Cells: power over the red-noise background at that period; red at 99 %, amber at 95 %. Verdict: none / weak (95 %) / candidate (99 %, first time) / signal (99.9 % or a comb of two independent periods, three updates running on the same period, above the 99th percentile of history). Built ' + esc(SP.built) + ', ' + ser.length + ' series, window ' + SP.window_days + ' days. One-day periods need hourly data and are not tested here.'));
    worksFoot(body, 'block:spectral');
  }

  /* РЕГИОНАЛЬНЫЕ БОКСЫ: имена и привязка к вкладке Regions. */
  var LAND_NAME = { land_gulf_north: 'N. Gulf', land_europe_central: 'Europe', land_peru_coast: 'Peru coast', land_java: 'Java', land_east_africa: 'E. Africa', land_north_india: 'N. India' };
  function boxLabel(b) { if (!b || b.length < 4) return ''; function la(x) { return Math.abs(x) + '°' + (x < 0 ? 'S' : 'N'); } function lo(x) { return Math.abs(x) + '°' + (x < 0 ? 'W' : 'E'); } return la(b[0]) + '–' + la(b[1]) + ', ' + lo(b[2]) + '–' + lo(b[3]); }
  function landKeyOfRegion(rid) { var RD = (S.RD || {}).series || {}; for (var k in RD) if (RD[k].region === rid) return k; return null; }
  function landOfRegion(rid) { var k = landKeyOfRegion(rid); return k ? S.RD.series[k] : null; }

  /* РЕЛЬСЫ ВО ВЕСЬ ЭКРАН (владелец 07.09: «state выезжает во весь экран, то же с risks;
     меню остаётся»). Класс на .mid прячет две другие колонки; Esc и повторное нажатие возвращают. */
  function railFullBtn(side) {
    var on = S.railFull === side;
    return '<button type="button" class="rail-full" data-side="' + side + '" title="' + (on ? 'back to three columns (Esc)' : 'this column full screen') + '">' + (on ? '✕' : '⛶') + '</button>';
  }
  function applyRailFull() {
    var mid = $('mid'); if (!mid) return;
    mid.classList.toggle('rf-L', S.railFull === 'L'); mid.classList.toggle('rf-R', S.railFull === 'R');
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.rail-full');
    if (!b) return;
    var side = b.getAttribute('data-side');
    S.railFull = S.railFull === side ? null : side; render();
  });

  /* ЗАГОЛОВОК СЦЕНЫ В ОДНУ СТРОКУ (владелец 07.09: «не надо в две, просто уменьшай шрифт,
     иначе подменю скачет»): после раскладки уменьшаем кегль, пока текст не влезет. */
  function fitStageTitle() {
    var h = document.querySelector('.stage-h'); if (!h) return;
    h.style.fontSize = '';
    if (window.matchMedia('(max-width:900px)').matches) return;   // на телефоне заголовок переносится, а не ужимается
    /* На телефоне заголовок обрезался: замер шёл до того, как колонка получила ширину, и
       нижний предел кегля был великоват (владелец 07.09). Меряем ещё раз кадром позже и
       по изменению ширины окна, вниз пускаем до 9 пикселей. */
    var px = parseFloat(getComputedStyle(h).fontSize) || 18, guard = 0;
    while (h.scrollWidth > h.clientWidth + 1 && px > 9 && guard++ < 32) { px -= 0.5; h.style.fontSize = px + 'px'; }
  }
  window.addEventListener('resize', function () { fitStageTitle(); });

  /* ОСАДКИ (владелец 07.09: «нет источников по осадкам? бери всё что есть»). Данные precip.json:
     регионы — ERA5 по боксам (суммы за 30/90 дней против нормы и всех лет), планета — GPCP месячный.
     Столбики месяцев с нормой пунктиром: красный столбик суше нормы, синий влажнее. */
  function chartRainBars(cfg, W, H) {
    var ym = cfg.ym || [], v = cfg.values || [], nm = cfg.normal || [], n = ym.length;
    if (!n) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var Lp = 46, R = 14, Tp = 26, B = 32, pw = W - Lp - R, ph = H - Tp - B;
    var all = v.concat(nm).filter(fin), vmax = Math.max.apply(null, all) * 1.15 || 1;
    var X = function (i) { return Lp + (i + .5) / n * pw; }, Y = function (x) { return Tp + (vmax - x) / vmax * ph; };
    var s = svgOpen(W, H) + hatchDefs() + '<text class="tt" x="' + Lp + '" y="15">' + fitText(esc(cfg.title || ''), W, 12) + '</text>';
    var step = niceStep(vmax, Math.max(3, Math.floor(ph / 26)));
    for (var g = 0; g < vmax; g += step) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(1) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 3.5).toFixed(1) + '" text-anchor="end" font-size="9">' + fnum(g, step < 1 ? 1 : 0, false) + '</text>';
    var bw = Math.max(2, pw / n * .7);
    v.forEach(function (x, i) {
      if (!fin(x)) return;
      var dry = fin(nm[i]) && x < nm[i], col = dry ? 'var(--nino)' : 'var(--nina)';
      s += '<rect x="' + (X(i) - bw / 2).toFixed(1) + '" y="' + Y(x).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + (Y(0) - Y(x)).toFixed(1) + '" style="fill:' + col + '" opacity="' + (cfg.partialLast && i === n - 1 ? .45 : .8) + '"/>' + (dry ? '<rect x="' + (X(i) - bw / 2).toFixed(1) + '" y="' + Y(x).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + (Y(0) - Y(x)).toFixed(1) + '" fill="url(#hneg)" opacity=".5"/>' : '');
      if (ym[i].slice(5) === '01' || n <= 12) s += '<text x="' + X(i).toFixed(1) + '" y="' + (H - 15) + '" text-anchor="middle" font-size="9">' + (n <= 12 ? ym[i].slice(5) : ym[i].slice(0, 4)) + '</text>';
    });
    s += segs(nm.map(function (x, i) { return [X(i), fin(x) ? Y(x) : NaN]; }), 'var(--text)', 1.4, .9, '5 3');
    // подпись шкалы внизу справа, не в строке заголовка (владелец 07.09: «тексты наезжают»)
    s += '<text x="' + (W - R) + '" y="' + (H - 4) + '" text-anchor="end" font-size="9" style="fill:var(--soft)">' + esc(cfg.unit || '') + ' · dashed: 1991–2020 normal · red hatched: drier than normal' + (cfg.partialLast ? ' · last bar incomplete' : '') + '</text>';
    return s + '</svg>';
  }

  function viewRain(body) {
    var PR = S.PR || {}, RG = PR.regions || {}, G = PR.gpcp || null, keys = Object.keys(RG);
    if (!PR.built) { body.appendChild(el('div', 'note', 'No rain data yet: run python tools/enso/precip.py.')); return; }
    var pick = S.sub.rain || 'planet';
    var row = el('div', 'seg sub');
    [['planet', 'planet (GPCP)']].concat(keys.map(function (k) { return [k, LAND_NAME[k] || k]; })).forEach(function (o, i) {
      var b = el('button', (pick === o[0] ? 'on' : '') + (i === 0 ? ' sq' : ''), o[1]); b.type = 'button'; b.onclick = function () { S.sub.rain = o[0]; render(); }; row.appendChild(b);
      if (i === 0) row.appendChild(el('span', 'seg-gap', ''));
    });
    // график или таблица — переключатель, а не всё сразу (владелец 07.09)
    var mode = S.sub.rainMode || 'chart';
    row.appendChild(el('span', 'seg-gap', ''));
    [['chart', 'chart'], ['table', 'table']].forEach(function (o) { var b = el('button', (mode === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.rainMode = o[0]; render(); }; row.appendChild(b); });
    body.appendChild(row);
    body.classList.add('scroll');
    if (mode === 'chart' && pick === 'planet') {
      if (!G) { body.appendChild(el('div', 'note warn', 'GPCP did not load.')); }
      else {
        var g = G.global;
        plot(body, function (w, h) { return chartRainBars({ ym: g.ym, values: g.values, normal: g.normal_series, title: 'Rain over the whole planet, land and ocean, monthly mean, GPCP', unit: 'mm per day' }, w, h); });
        var kg = el('div', 'kpis');
        kg.innerHTML = '<div class="kpi"><div class="kn">planet · ' + esc(g.last) + '</div><div class="kv">' + fnum(g.now, 2, false) + '<small> mm/day</small></div><div class="km">' + g.pct_of_normal + ' % of the normal for that month; rank ' + g.rank_pct + ' % of ' + g.of_years + ' years</div>' + kmeta(null, G.source, g.last) + '</div>' +
          '<div class="kpi"><div class="kn">same month in our years</div><div class="kv" style="font-size:14px">' + Object.keys(g.analogs).sort().map(function (y) { return y + ': ' + fnum(g.analogs[y], 2, false); }).join(' · ') + '</div><div class="km">mm per day, planet</div>' + kmeta(null, G.source, g.last) + '</div>';
        body.appendChild(kg);
      }
    } else if (mode === 'chart') {
      var r = RG[pick], s30 = r.sum30, s90 = r.sum90, gb = G && G.boxes ? G.boxes[pick] : null;
      plot(body, function (w, h) { return chartRainBars({ ym: r.months.map(function (m) { return m.ym; }), values: r.months.map(function (m) { return m.mm; }), normal: r.months_normal, title: (LAND_NAME[pick] || pick) + ', ' + boxLabel(r.box) + ': rain by month, last 24 months, ERA5 box sum', unit: 'mm per month', partialLast: true }, w, h); });
      var kr = el('div', 'kpis');
      kr.innerHTML = '<div class="kpi"><div class="kn">last 30 days to ' + esc(r.last_date) + '</div><div class="kv">' + fnum(s30.now, 0, false) + '<small> mm</small></div><div class="km">' + s30.pct_of_normal + ' % of the normal ' + fnum(s30.normal, 0, false) + ' mm; wetter than ' + s30.rank_pct + ' % of ' + s30.of_years + ' years</div>' + kmeta(null, 'ERA5 box sum via Open-Meteo', r.last_date) + '</div>' +
        '<div class="kpi"><div class="kn">last 90 days</div><div class="kv">' + fnum(s90.now, 0, false) + '<small> mm</small></div><div class="km">' + s90.pct_of_normal + ' % of the normal ' + fnum(s90.normal, 0, false) + ' mm; wetter than ' + s90.rank_pct + ' % of years</div>' + kmeta(null, 'ERA5 box sum via Open-Meteo', r.last_date) + '</div>' +
        '<div class="kpi"><div class="kn">same 30 days in our years</div><div class="kv" style="font-size:14px">' + Object.keys(s30.analogs).sort().map(function (y) { return y + ': ' + fnum(s30.analogs[y], 0, false); }).join(' · ') + '</div><div class="km">mm, ERA5</div>' + kmeta(null, 'ERA5 box sum', r.last_date) + '</div>' +
        (gb ? '<div class="kpi"><div class="kn">GPCP, last month ' + esc(gb.last) + '</div><div class="kv">' + gb.pct_of_normal + '<small> % of normal</small></div><div class="km">' + fnum(gb.now, 2, false) + ' mm/day against ' + fnum(gb.normal, 2, false) + '; satellites and gauges, a second source</div>' + kmeta(null, G.source, gb.last) + '</div>' : '');
      body.appendChild(kr);
    }
    // сводная таблица по регионам — только в табличном режиме
    var wrap = el('div');
    if (mode !== 'table') { body.appendChild(el('div', 'cap', esc(PR.note || ''))); worksFoot(body, 'block:rain'); return; }
    wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
    wrap.innerHTML = '<table class="e rain"><thead><tr><th>region</th><th class="num">30 d, mm</th><th class="num">% of normal</th><th class="num">wetter than</th><th class="num">90 d, % of normal</th><th>same 30 d in our years, mm</th><th class="num">GPCP last month</th></tr></thead><tbody>' +
      keys.map(function (k) { var r2 = RG[k], a = r2.sum30, b = r2.sum90, gb2 = G && G.boxes ? G.boxes[k] : null; var cls = fin(a.pct_of_normal) ? (a.pct_of_normal < 60 ? ' top' : (a.pct_of_normal > 160 ? ' warn' : '')) : '';
        return '<tr><td style="white-space:nowrap;min-width:190px">' + esc(LAND_NAME[k] || k) + '<div class="sub">' + esc(boxLabel(r2.box)) + '</div></td><td class="num">' + fnum(a.now, 0, false) + '</td><td class="num' + cls + '">' + a.pct_of_normal + ' %</td><td class="num">' + a.rank_pct + ' % of years</td><td class="num">' + b.pct_of_normal + ' %</td><td class="act">' + Object.keys(a.analogs).sort().map(function (y) { return y + ': ' + fnum(a.analogs[y], 0, false); }).join(' · ') + '</td><td class="num">' + (gb2 ? gb2.pct_of_normal + ' %' : '·') + '</td></tr>'; }).join('') + '</tbody></table>';
    body.appendChild(wrap);
    body.appendChild(el('div', 'cap', esc(PR.note || '') + ' Red: under 60 % of normal over 30 days, amber: over 160 %. Built ' + esc(PR.built) + (PR.chirps_reachable ? '; CHIRPS reachable, not yet wired' : '; CHIRPS not reachable') + '.'));
    worksFoot(body, 'block:rain');
  }

  /* Короткий заголовок сцены: длинная сводка уезжала в две-три строки (владелец 07.09). */
  function spectralHead() {
    var SP = S.SP || {};
    if (!SP.built) return 'Spectral watch: no data yet';
    if ((SP.signals || []).length) return 'Spectral watch: SIGNAL in ' + SP.signals.join(', ');
    return 'Spectral watch: no signal in ' + (SP.series || []).length + ' series, '
      + SP.lines_99_now + ' line at 99 % against ' + SP.lines_99_expected_by_chance + ' by chance';
  }

  function rainHead() {
    var PR = S.PR || {}, G = (PR.gpcp || {}).global, RG = PR.regions || {};
    var dry = Object.keys(RG).filter(function (k) { return fin(RG[k].sum30.pct_of_normal) && RG[k].sum30.pct_of_normal < 60; }).map(function (k) { return LAND_NAME[k] || k; });
    var wet = Object.keys(RG).filter(function (k) { return fin(RG[k].sum30.pct_of_normal) && RG[k].sum30.pct_of_normal > 160; }).map(function (k) { return LAND_NAME[k] || k; });
    return 'Rain: ' + (G ? 'the planet at ' + G.pct_of_normal + ' % of normal in ' + G.last : 'no planet series') + (dry.length ? '; dry: ' + dry.join(', ') : '') + (wet.length ? '; wet: ' + wet.join(', ') : '');
  }

  /* СПУТНИК, СЫРЫЕ ГРАНУЛЫ (владелец 07.09: «новые источники… они сами будут обновлять, мы берём
     результат»). Внешний модуль C:\CL\radiance читает гранулы NOAA-21 (CrIS + ATMS) из открытого
     бакета NOAA и пишет radiance.json; здесь только показ. Ряды индексированы днём окна
     (0 = 1 июля), по годам — для наложения 2023/24/25 на 2026. Оговорки из meta.caveats
     обязательны на каждой сцене: яркостная температура, короткая база, афтершоки не отделены. */
  var RAD_YEAR_COLOR = { '2026': 'var(--text)', '2025': 'var(--a2023)', '2024': 'var(--a2015)', '2023': 'var(--a1997)' };
  function radDays(RD0) { var w = (RD0.window || {}); var m0 = parseInt((w.start || '07-01').slice(0, 2), 10), d0 = parseInt((w.start || '07-01').slice(3), 10); return function (i) { var d = new Date(Date.UTC(2026, m0 - 1, d0 + i)); return (d.getUTCMonth() + 1) + '-' + (d.getUTCDate() < 10 ? '0' : '') + d.getUTCDate(); }; }
  function chartRadSeries(cfg, W, H) {
    var by = cfg.byYear || {}, years = Object.keys(by).sort(), cur = String(cfg.cur || '2026');
    var n = cfg.n || 68, Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var all = [];
    years.forEach(function (y) { Object.keys(by[y]).forEach(function (k) { var v = by[y][k]; if (fin(v)) all.push(v); }); });
    if (!all.length) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var vmin = Math.min.apply(null, all), vmax = Math.max.apply(null, all), pad = (vmax - vmin) * .1 || 1;
    if (cfg.zero) vmin = Math.min(0, vmin);
    vmin -= pad; vmax += pad * 1.5;
    var X = function (i) { return Lp + i / (n - 1) * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + hatchDefs() + '<text class="tt" x="' + Lp + '" y="13">' + fitText(esc(cfg.title || ''), W, 12) + '</text>';
    var step = niceStep(vmax - vmin, Math.max(3, Math.floor(ph / 26)));
    for (var g = Math.ceil(vmin / step) * step; g < vmax; g += step) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(1) + '" x2="' + (W - R - 8) + '" y2="' + Y(g).toFixed(1) + '" style="stroke:var(--grid)" stroke-width="' + (Math.abs(g) < 1e-9 ? 1.3 : .6) + '"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 3.5).toFixed(1) + '" text-anchor="end" font-size="9">' + fnum(g, step < 1 ? 2 : (step < 10 ? 1 : 0), false) + '</text>';
    var lab = cfg.dayLabel || function (i) { return String(i); };
    for (var i = 0; i < n; i += 10) s += '<text x="' + X(i).toFixed(1) + '" y="' + (H - 9) + '" text-anchor="middle" font-size="9">' + esc(lab(i)) + '</text>';
    var legs = [];
    years.forEach(function (y, yi) {
      var pts = [];
      for (var i = 0; i < n; i++) { var v = by[y][String(i)]; pts.push([X(i), fin(v) ? Y(v) : NaN]); }
      // аналоги через день: соединяем через пропуски
      var clean = pts.filter(function (p) { return fin(p[1]); });
      var col = RAD_YEAR_COLOR[y] || 'var(--soft)', isCur = y === cur;
      if (cfg.bars && isCur) {
        var bw = Math.max(2, pw / n * .7);
        for (var j = 0; j < n; j++) { var vv = by[y][String(j)]; if (fin(vv)) s += '<rect x="' + (X(j) - bw / 2).toFixed(1) + '" y="' + Y(vv).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0, Y(Math.max(0, vmin)) - Y(vv)).toFixed(1) + '" style="fill:' + col + '" opacity=".75"/>'; }
      } else if (clean.length > 1) s += poly(clean, col, isCur ? 2.4 : 1.4, pickOp(y, 1), isCur ? '' : dashOf(yi + 1));
      legs.push([y, col, isCur ? 2.4 : 1.4, isCur ? '' : dashOf(yi + 1), y]);
      if (isCur && clean.length) s += nowDot(clean[clean.length - 1][0], clean[clean.length - 1][1], col, 3.5);
    });
    s += legend(legs, W, H, R, Tp);
    return s + '</svg>';
  }

  /* ФОРМУЛЫ И ОГОВОРКИ СБОРЩИКА ПО-АНГЛИЙСКИ. Файл radiance.json пишет их по-русски, панель
     английская (владелец 03.09): здесь их английские версии по ключу; незнакомый ключ
     отдаётся как есть, чтобы новое не потерялось. */
  var RAD_EN = {
    conv_frac: 'share of footprints with BT(900 cm⁻¹) below 235 K in the box per day',
    walker_raw: 'BT900(Niño 3.4) minus BT900(warm pool), K; a fall means the convection has moved east',
    detector: 'mean of the last 14 days minus the previous 14, in units of the window’s daily σ; threshold 1.5',
    seismic: 'event counts in the window by zone in four variants: thresholds M ≥ 4.5 and M ≥ 5.5, raw and with aftershocks separated by Gardner–Knopoff (1974) windows; an alert only on independent M ≥ 5.5 events',
    profile_anom: 'mean of the last 14 days of 2026 minus the mean of the whole window of the analogue year',
    clouds: 'floors by BT900: deep below 235 K, mid 235–270 K, low 270–285 K; clear when BT900 is within 4 K of the sea surface (2 K histogram bins plus OISST in K)',
    greenhouse: 'G = SST (OISST, K) minus the mean BT900 over the box, K. Caution: in this form G is set mostly by cloud tops, not by greenhouse gases; read it with the cloud floors',
    greenhouse_clear: 'G_clear = SST (K) minus BT900 at the 90th percentile of the daily histogram (the warmest, least cloudy scenes): the window trap by an almost cloud-free atmosphere, a proxy for the greenhouse action of water vapour; the night node is free of solar heating'
  };
  var RAD_CAV_EN = [
    [/^база NOAA-21/, 'the NOAA-21 record starts in February 2023, so the sigmas are short'],
    [/^ИК-каналы/, 'infrared channels are blind under cloud (that is part of the convection signal); the all-weather layers are ATMS'],
    [/^яркостная/, 'brightness temperature, not air or ocean temperature'],
    [/^сейсмика/, 'quakes: the raw count does not separate aftershocks (the declustered counts do, since v3); catalogue magnitudes are a computed product'],
    [/^G \(полный\)/, 'the full G follows cloud cover; for the greenhouse signal read G_clear'],
    [/^G_clear на p90/, 'G_clear on the 90th percentile is partly contaminated by residual cloud: on the 99th percentile the 2026 signal over Niño 3.4 falls from +2.6…+2.8 K to +1.4 K, but does not vanish (collector check_gclear.py)'],
    [/^над тёплым бассейном/, 'over the warm pool there are almost no truly clear scenes (0–3 % of days), so its G_clear is an upper bound, not a clean measurement'],
    [/^AIRS и CrIS/, 'AIRS and CrIS agree in the shape of the curves, not in absolute values: the instruments have different spectral response functions (offsets up to 12 K at correlations above 0.9 in the upper troposphere; cross_check.py)'],
    [/^Aqua с 2022/, 'Aqua has been drifting freely since 2022: the local time of the AIRS overpass has crept from 13:30 towards 15:00 and later, so its day and night nodes do not coincide in local time with NOAA-21'],
    [/^сырой счёт событий/, 'a raw event count misleads: about half of the catalogue are aftershocks, and one strong sequence looks like a rise in seismicity (Central America 2026: a record by the raw M ≥ 4.5 count, ordinary and below the median once aftershocks are separated)'],
    [/^порог M>=4\.5/, 'the M ≥ 4.5 threshold is unfit for comparing epochs: network sensitivity grows, and the trend in independent events reaches +10–20 % per decade even where tectonics has not changed; M ≥ 5.5 is steadier'],
    [/^связь сейсмичности/, 'no link between seismicity and El Niño is established: the USGS position is that weather and earthquakes are unrelated; the few papers concern mid-ocean ridges (the Easter microplate), not subduction zones. The block is independent monitoring']
  ];
  function radF(F, key) { return RAD_EN[key] || F[key] || ''; }
  function radCav(cav) { return (cav || []).map(function (c) { for (var i = 0; i < RAD_CAV_EN.length; i++) if (RAD_CAV_EN[i][0].test(c)) return RAD_CAV_EN[i][1]; return c; }).join('. ') + (cav && cav.length ? '.' : ''); }

  /* СТАНДАРТ СЦЕНЫ (владелец 08.09): сверху график, ниже плашки с метриками; описание источника
     и разбор (формула, детекторы, оговорки) — за двумя переключателями в строке подменю, а
     ссылка на работы — кнопкой в правом нижнем углу, как на карточках. Механизм общий. */
  function infoToggles(row, items) {
    var ci = document.querySelector('.stage-head .ctl-info');   // с 08.09 кнопки живут в строке управления
    if (ci) row = ci; else row.appendChild(el('span', 'seg-gap', ''));
    items.forEach(function (it) {
      var b = el('button', (S.sub.info === it.key ? 'on' : '') + ' sq', it.label + (S.sub.info === it.key ? ' ▴' : ' ▾'));
      b.type = 'button'; b.onclick = function () { S.sub.info = S.sub.info === it.key ? null : it.key; render(); };
      row.appendChild(b);
    });
  }
  function infoPane(body, items) {
    var it = items.filter(function (q) { return q.key === S.sub.info; })[0];
    if (!it) return;
    var p = el('div', 'info-pane'), mode = S.sub.noteMode || 'plain';
    if (it.plain) {
      p.innerHTML = '<div class="seg sub" style="margin-bottom:6px">' + [['plain', 'in plain words'], ['tech', 'technical']].map(function (o) { return '<button type="button" class="sq' + (mode === o[0] ? ' on' : '') + '" data-notemode="' + o[0] + '">' + o[1] + '</button>'; }).join('') + '</div>' + (mode === 'plain' ? '<div>' + esc(it.plain) + '</div>' : it.html);
      p.addEventListener('click', function (e) { var b = e.target.closest('[data-notemode]'); if (b) { S.sub.noteMode = b.getAttribute('data-notemode'); render(); } });
    } else p.innerHTML = it.html;
    p.innerHTML += conceptsHtml(sceneAnchors(), true);
    body.appendChild(p);
  }
  function worksFoot(body, anchor) {
    var h = linksHtml(anchor); if (!h) return;
    var f = el('div', 'works-foot'); f.innerHTML = h; body.appendChild(f);
  }

  function viewRadiance() {
    var RA = S.RA || {}, k = sub('radiance', 'convection'), SRC = RA.sources || {}, CRIS = SRC.n21_cris || {}, AIRS = SRC.aqua_airs || {}, AT = SRC.n21_atms || {}, US = SRC.usgs_catalog || {}, SO = SRC.gfz_solar || {};
    /* Платформа (v3, 08.09): CrIS на NOAA-21 или AIRS на Aqua — та же схема рядов, тот же вид. */
    var plat = S.sub.radPlat === 'airs' && AIRS.series ? 'airs' : 'cris', CR = plat === 'airs' ? AIRS : CRIS, PLAT = plat === 'airs' ? 'Aqua AIRS' : 'NOAA-21 CrIS';
    var alerts = RA.alerts || [], dets = CR.detectors || {}, trig = Object.keys(dets).filter(function (q) { return dets[q].triggered; });
    var W0 = RA.window || {}, cur = String(W0.current || 2026), dl = RA.updated ? radDays(RA) : null, F = (RA.meta || {}).formulas || {}, cav = (RA.meta || {}).caveats || [];
    var head = !RA.updated ? 'Satellite, raw granules: no file yet' :
      'Raw satellite view: convection over Niño 3.4 ' + (function () { var s0 = ((CR.series || {}).nino34_A || {}).conv_frac || {}; var c = s0[cur] || {}; var ks = Object.keys(c).map(Number).sort(function (a, b) { return a - b; }); var v = c[String(ks[ks.length - 1])]; return fin(v) ? fnum(v * 100, 1, false) + ' % of footprints' : ''; })() + (trig.length ? '; detectors fired: ' + trig.join(', ') : '; ' + Object.keys(dets).length + ' turning-point detectors quiet');
    var body = stageShell(head, [segBtn('radiance', 'convection', 'Convection', 'convection'), segBtn('radiance', 'walker', 'Raw Walker', 'convection'), segBtn('radiance', 'clouds', 'Cloud floors', 'convection'), segBtn('radiance', 'greenhouse', 'Window trap', 'convection'), segBtn('radiance', 'profile', 'Layers through cloud', 'convection'), segBtn('radiance', 'cross', 'Two satellites', 'convection'), segBtn('radiance', 'seismic', 'Quakes and sun', 'convection')]);
    if (!RA.updated) { body.appendChild(el('div', 'note', 'No radiance.json yet: the collector at C:\\CL\\radiance writes it; the daily wrapper copies it in.')); return; }
    body.classList.add('scroll'); body.setAttribute('data-own-info', '1');
    // описание источника — по-английски, из данных, а не из русской строки файла
    var alertsEn = alerts.map(function (a) {
      var m = String(a.metric || ''), z = m.indexOf('seismic_') === 0 ? (US.zones || {})[m.slice(8)] : null;
      if (z) return '<b>' + esc(m.slice(8).replace(/_/g, ' ')) + '</b>: ' + z.cur + ' quakes M ≥ 4.5 in the window, above the 2000–2025 maximum of ' + z.max + '; M ≥ 5.5: ' + z.cur_m55 + ' against a median of ' + z.median_m55 + ' (aftershocks not separated)';
      return '<b>' + esc(m) + '</b>: ' + esc(a.text || '');
    });
    var srcHtml = '<b>Measured by us, from raw granules.</b> NOAA-21 CrIS (infrared, 2223 channels, the long-wave band read by HTTP range) and ATMS (microwave, 22 channels) straight from the anonymous NOAA NODD bucket; USGS earthquake catalogue; GFZ Potsdam Kp, sunspots, F10.7. Boxes Niño 3.4 and the warm pool, day (13:30) and night (01:30) nodes; window ' + esc(dl ? dl(0) : W0.start) + ' → ' + esc(W0.end) + ', years ' + (W0.years || []).join(', ') + '; updated ' + dt(String(RA.updated || '').slice(0, 10)) + '. The collector (C:\\CL\\radiance, schema v2) is run by its author; the panel copies the result when it is complete and re-derives the headline numbers from the layer-1 tables (radiance_check.py). Collector alerts: ' + (alertsEn.length ? alertsEn.join(' · ') : 'none') + '.';
    function detLine(keys) { return keys.filter(function (q) { return dets[q]; }).map(function (q) { var d = dets[q]; return esc(q) + ' ' + fnum(d.sigma_units, 2) + 'σ' + (d.triggered ? ' <b>fired</b>' : ''); }).join(' · '); }
    function notes(formula, extra, detKeys) { return '<b>Formula.</b> ' + esc(formula) + (extra ? ' ' + extra : '') + '<br><b>Turning-point detectors</b> (14-day step in daily σ, threshold 1.5): ' + (detLine(detKeys) || 'none for this view') + '.<br><b>Caveats.</b> ' + esc(radCav(cav)); }
    var boxk = S.sub.radBox || 'nino34', node = S.sub.radNode || 'A';
    function platRow(row) {
      if (!AIRS.series) return row;
      row.appendChild(el('span', 'seg-gap', ''));
      [['cris', 'NOAA-21 CrIS'], ['airs', 'Aqua AIRS']].forEach(function (o) { var b = el('button', (plat === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.title = o[0] === 'airs' ? 'independent platform; its overpass drifts towards 15:00 local' : 'NOAA-21, overpass 13:25 local'; b.onclick = function () { S.sub.radPlat = o[0]; render(); }; row.appendChild(b); });
      return row;
    }
    function boxRow(withNode) {
      var row = el('div', 'seg sub');
      [['nino34', 'Niño 3.4 box'], ['warmpool', 'warm pool box']].forEach(function (o) { var b = el('button', boxk === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radBox = o[0]; render(); }; row.appendChild(b); });
      if (withNode) { row.appendChild(el('span', 'seg-gap', '')); [['A', 'day, 13:30'], ['D', 'night, 01:30']].forEach(function (o) { var b = el('button', (node === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radNode = o[0]; render(); }; row.appendChild(b); }); }
      return platRow(row);
    }
    var RAD_PLAIN = {
      convection: 'Tall storm clouds have moved from the western Pacific to the middle of it, where they almost never are. The satellite counts how much of each day’s view is cold cloud tops; this year it is many times more than in the past three years.',
      walker: 'Normally the west of the Pacific is cloudy and the east is clear, so the satellite sees the east as much warmer at the top of the atmosphere. This year that contrast has vanished: the whole circulation has shifted east, which is the signature of a strong El Niño.',
      clouds: 'Each satellite scene is sorted by how high its clouds are, from clear sky to deep storms. Over the central Pacific there is now far more cloud and far less clear sky than before; over the west the opposite. More cloud means more sunlight reflected there.',
      greenhouse: 'Moist air holds heat in. Even on the clearest days the air over the central Pacific now traps more of the sea’s heat than in past years, because the warm sea puts more water vapour above it; the drier west traps less.',
      profile: 'A temperature ladder through the atmosphere, layer by layer: the microwave channels look through the clouds and show the air above the central Pacific warmer than in every recent year.',
      seismic: 'Earthquakes and the sun are shown beside the climate rows because people ask; nothing here claims they drive El Niño, and the USGS says weather and quakes are unrelated. Once aftershocks are separated, this summer’s counts are ordinary everywhere.',
      cross: 'Two different satellites, one from NOAA and one from NASA, looked at the same patches of ocean. Both saw the storms jump east by the same amount. When two independent instruments agree, the finding is not an artefact of one of them.'
    };
    var INFO = [{ key: 'source', label: 'source', html: srcHtml }], row, nt = '';

    if (k === 'convection') {
      row = boxRow(true);
      nt = notes(radF(F, 'conv_frac'), 'Deep convection is where the infrared window sees cloud tops colder than 235 K; the share of such footprints per day is the cleanest count of convection the granules give.', ['conv_frac_' + boxk + '_A', 'conv_frac_' + boxk + '_D']);
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      var ser = ((CR.series || {})[boxk + '_' + node] || {});
      plot(body, function (w, h) { return chartRadSeries({ byYear: pct(ser.conv_frac || {}), cur: cur, n: 68, dayLabel: dl, zero: true, title: 'Deep convection: share of footprints colder than 235 K at 900 cm⁻¹, ' + boxk + ', ' + (node === 'A' ? 'day' : 'night') + ', % of footprints, ' + cur + ' against 2023–2025' }, w, h); });
      body.appendChild(kpiRow(kpiLast(ser.conv_frac || {}, 100, ' %', 'deep convection · ' + boxk + ' · ' + (node === 'A' ? 'day' : 'night'), 'share of footprints, last 14 days, against the window means of past years')));
    } else if (k === 'walker') {
      row = el('div', 'seg sub');
      [['A', 'day, 13:30'], ['D', 'night, 01:30']].forEach(function (o) { var b = el('button', (node === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radNode = o[0]; render(); }; row.appendChild(b); });
      platRow(row);
      nt = notes(radF(F, 'walker_raw'), 'In every past year the east read 19–26 K warmer at the top of the atmosphere than the cloudy west; this year the contrast sits near zero: the convection has moved east.', ['walker_A', 'walker_D']);
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      var wk = (CR.series || {})['walker_' + node] || {};
      plot(body, function (w, h) { return chartRadSeries({ byYear: wk, cur: cur, n: 68, dayLabel: dl, zero: true, title: 'Raw Walker: brightness temperature at 900 cm⁻¹, Niño 3.4 minus warm pool, K, ' + (node === 'A' ? 'day' : 'night') }, w, h); });
      body.appendChild(kpiRow(kpiLast(wk, 1, ' K', 'raw Walker contrast · ' + (node === 'A' ? 'day' : 'night'), 'east minus west, last 14 days, against the window means of past years')));
    } else if (k === 'clouds') {
      var floor = S.sub.radFloor || 'clear', mode = S.sub.radMode || 'chart';
      row = boxRow(true);
      row.appendChild(el('span', 'seg-gap', ''));
      [['clear', 'clear sky'], ['low', 'low cloud'], ['mid', 'mid cloud'], ['deep', 'deep convection']].forEach(function (o) { var b = el('button', floor === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radFloor = o[0]; render(); }; row.appendChild(b); });
      row.appendChild(el('span', 'seg-gap', ''));
      [['chart', 'chart'], ['table', 'table']].forEach(function (o) { var b = el('button', (mode === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radMode = o[0]; render(); }; row.appendChild(b); });
      nt = notes(radF(F, 'clouds'), 'The day-time cloud share is the panel’s proxy for albedo: more reflecting cover over the east, less over the west; infrared does not measure albedo itself, VIIRS would.', ['highcloud_' + boxk + '_A', 'highcloud_' + boxk + '_D']);
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      var CLb = ((CR.clouds || {})[boxk + '_' + node]) || {};
      var FL = { clear: 'clear sky (window within 4 K of the sea)', low: 'low cloud (270–285 K)', mid: 'mid cloud (235–270 K)', deep: 'deep convection (below 235 K)' };
      function floorSeries(f) { var by = {}; Object.keys(CLb).forEach(function (y) { by[y] = {}; Object.keys(CLb[y]).forEach(function (dd) { var v = (CLb[y][dd] || {})[f]; by[y][dd] = fin(v) ? v * 100 : null; }); }); return by; }
      if (mode === 'chart') {
        plot(body, function (w, h) { return chartRadSeries({ byYear: floorSeries(floor), cur: cur, n: 68, dayLabel: dl, zero: true, title: 'Share of scenes: ' + FL[floor] + ', ' + boxk + ', ' + (node === 'A' ? 'day' : 'night') + ', % of footprints, ' + cur + ' against 2023–2025' }, w, h); });
        body.appendChild(kpiRow(kpiLast(floorSeries(floor), 1, ' %', FL[floor].replace(/ \(.*$/, '') + ' · ' + boxk + ' · ' + (node === 'A' ? 'day' : 'night'), 'share of scenes, last 14 days, against the window means of past years')));
      } else {
        var yrs = Object.keys(CLb).sort(), tb = el('div'); tb.style.cssText = 'flex:1;min-height:0;overflow:auto';
        tb.innerHTML = '<table class="e"><thead><tr><th>floor</th><th class="num">' + cur + ', last 14 d</th>' + yrs.filter(function (y) { return y !== cur; }).map(function (y) { return '<th class="num">' + y + ', window</th>'; }).join('') + '</tr></thead><tbody>' +
          ['deep', 'mid', 'low', 'clear'].map(function (f) { var by = floorSeries(f), st = kpiLast(by, 1, ' %', '', ''); return '<tr><td>' + esc(FL[f]) + '</td><td class="num"><b>' + esc(st.now) + '</b></td>' + yrs.filter(function (y) { return y !== cur; }).map(function (y) { return '<td class="num">' + esc(st.by[y] || '·') + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table>';
        body.appendChild(tb);
      }
    } else if (k === 'greenhouse') {
      var gk = S.sub.radG || 'greenhouse_clear';
      row = el('div', 'seg sub');
      [['greenhouse_clear', 'G_clear, least cloudy scenes'], ['greenhouse', 'G, all scenes']].forEach(function (o) { var b = el('button', (gk === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radG = o[0]; render(); }; row.appendChild(b); });
      row.appendChild(el('span', 'seg-gap', ''));
      [['nino34', 'Niño 3.4 box'], ['warmpool', 'warm pool box']].forEach(function (o) { var b = el('button', boxk === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radBox = o[0]; render(); }; row.appendChild(b); });
      row.appendChild(el('span', 'seg-gap', ''));
      [['A', 'day, 13:30'], ['D', 'night, 01:30']].forEach(function (o) { var b = el('button', (node === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radNode = o[0]; render(); }; row.appendChild(b); });
      platRow(row);
      nt = notes(radF(F, gk), gk === 'greenhouse_clear' ? 'On the strictest 1 % of scenes the Niño 3.4 signal halves to about +1.4 K but stays; over the warm pool truly clear scenes are 0–3 % of days, so its value is an upper bound.' : 'The full index follows cloud cover, read it beside the cloud floors; the greenhouse signal is G_clear.', [gk + '_' + boxk + '_A', gk + '_' + boxk + '_D']);
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      var Gb = ((CR[gk] || {})[boxk + '_' + node]) || {};
      plot(body, function (w, h) { return chartRadSeries({ byYear: Gb, cur: cur, n: 68, dayLabel: dl, zero: true, title: (gk === 'greenhouse_clear' ? 'G_clear: sea surface minus the warmest tenth of window scenes, K' : 'G: sea surface minus the mean window brightness temperature, K') + ', ' + boxk + ', ' + (node === 'A' ? 'day' : 'night') }, w, h); });
      body.appendChild(kpiRow(kpiLast(Gb, 1, ' K', (gk === 'greenhouse_clear' ? term('gclear', 'G_clear') : 'G') + ' · ' + boxk + ' · ' + (node === 'A' ? 'day' : 'night'), 'last 14 days, against the window means of past years')));
    } else if (k === 'cross') {
      /* ДВА СПУТНИКА (v3, 08.09). Сборщик пишет: перескок конвекции на восток совпал у двух приборов
         с точностью полтора процента. Таблица считается ЗДЕСЬ, из рядов файла, а не берётся из их
         текста: сдвиг 2026 против среднего 2023–2025 у каждой платформы и разность. Суточная
         корреляция по конвекции — тоже наша, из тех же рядов. */
      row = el('div', 'seg sub');
      nt = '<b>Method.</b> For each platform: the 2026 window mean minus the mean of the 2023–2025 window means, from the daily series in the file (deep convection share, both nodes) and from the 14-day profile anomalies (channels 662, 690, 900 cm⁻¹). The collector’s own cross_check.py reports the same picture: daily correlation 0.98 in the upper troposphere and 0.97 in the stratosphere, 0.65–0.8 in the window and lower troposphere, where Aqua’s drifting overpass (~15:00 local against 13:25) sees another phase of the cloud diurnal cycle. Caveat: the platforms agree in the shape of the curves, not in absolute brightness temperatures.';
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      function mAll2(o) { var v = Object.keys(o || {}).map(function (kk) { return o[kk]; }).filter(fin); return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : null; }
      function shift(src, key, prop) { var ser = (((src.series || {})[key] || {})[prop]) || {}; var c = mAll2(ser[cur]); var past = ['2023', '2024', '2025'].map(function (y) { return mAll2(ser[y]); }).filter(fin); return fin(c) && past.length ? c - past.reduce(function (a, b) { return a + b; }, 0) / past.length : null; }
      function pshift(src, box, ch) { var p = (((src.profile || {})[box] || {})[ch]) || {}; var v = ['2023', '2024', '2025'].map(function (y) { return p['anom_vs_' + y]; }).filter(fin); return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : null; }
      function corr(a, b) { var ks = Object.keys(a || {}).filter(function (x) { return fin(a[x]) && fin((b || {})[x]); }); if (ks.length < 10) return null; var xa = ks.map(function (x) { return a[x]; }), xb = ks.map(function (x) { return b[x]; }); var ma = xa.reduce(function (p, q) { return p + q; }, 0) / ks.length, mb = xb.reduce(function (p, q) { return p + q; }, 0) / ks.length; var num = 0, da = 0, db = 0; ks.forEach(function (x, i) { num += (xa[i] - ma) * (xb[i] - mb); da += (xa[i] - ma) * (xa[i] - ma); db += (xb[i] - mb) * (xb[i] - mb); }); return da && db ? num / Math.sqrt(da * db) : null; }
      var rowsX = [
        ['Deep convection, Niño 3.4, day', shift(AIRS, 'nino34_A', 'conv_frac'), shift(CRIS, 'nino34_A', 'conv_frac'), 100, ' pt'],
        ['Deep convection, Niño 3.4, night', shift(AIRS, 'nino34_D', 'conv_frac'), shift(CRIS, 'nino34_D', 'conv_frac'), 100, ' pt'],
        ['Deep convection, warm pool, day', shift(AIRS, 'warmpool_A', 'conv_frac'), shift(CRIS, 'warmpool_A', 'conv_frac'), 100, ' pt'],
        ['Deep convection, warm pool, night', shift(AIRS, 'warmpool_D', 'conv_frac'), shift(CRIS, 'warmpool_D', 'conv_frac'), 100, ' pt'],
        ['Stratosphere (662 cm⁻¹), Niño 3.4', pshift(AIRS, 'nino34', '662'), pshift(CRIS, 'nino34', '662'), 1, ' K'],
        ['Upper troposphere (690), Niño 3.4', pshift(AIRS, 'nino34', '690'), pshift(CRIS, 'nino34', '690'), 1, ' K'],
        ['Upper troposphere (690), warm pool', pshift(AIRS, 'warmpool', '690'), pshift(CRIS, 'warmpool', '690'), 1, ' K'],
        ['Window (900), warm pool', pshift(AIRS, 'warmpool', '900'), pshift(CRIS, 'warmpool', '900'), 1, ' K'],
        ['Window (900), Niño 3.4', pshift(AIRS, 'nino34', '900'), pshift(CRIS, 'nino34', '900'), 1, ' K']
      ];
      var wx = el('div'); wx.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wx.innerHTML = '<table class="e"><thead><tr><th>2026 against 2023–2025</th><th class="num">Aqua AIRS</th><th class="num">NOAA-21 CrIS</th><th class="num">difference</th></tr></thead><tbody>' +
        rowsX.map(function (r) { var a = fin(r[1]) ? r[1] * r[3] : null, c = fin(r[2]) ? r[2] * r[3] : null; var d = fin(a) && fin(c) ? a - c : null; var close = fin(d) && Math.abs(d) <= (r[4] === ' pt' ? 1 : 0.5); return '<tr><td>' + esc(r[0]) + '</td><td class="num">' + (fin(a) ? fnum(a, r[4] === ' pt' ? 1 : 2) + r[4] : '·') + '</td><td class="num">' + (fin(c) ? fnum(c, r[4] === ' pt' ? 1 : 2) + r[4] : '·') + '</td><td class="num' + (close ? ' st-ok' : '') + '">' + (fin(d) ? fnum(d, r[4] === ' pt' ? 1 : 2) + r[4] : '·') + '</td></tr>'; }).join('') + '</tbody></table>' +
        '<div class="cap">Green difference: within 1 point of convection share or 0.5 K. The eastward jump of convection (+7 points over Niño 3.4, −5 to −6 over the warm pool) is the same on both instruments; the window channel differs by kelvins because the two overpasses see different cloud phases.</div>';
      body.appendChild(wx);
      var rc = corr((((AIRS.series || {}).nino34_A || {}).conv_frac || {})[cur], (((CRIS.series || {}).nino34_A || {}).conv_frac || {})[cur]);
      var rw = corr(((AIRS.series || {}).walker_A || {})[cur], ((CRIS.series || {}).walker_A || {})[cur]);
      var kx = el('div', 'kpis');
      kx.innerHTML = '<div class="kpi"><div class="kn">convection shift, two instruments</div><div class="kv">' + (fin(rowsX[0][1]) && fin(rowsX[0][2]) ? fnum(rowsX[0][1] * 100, 1) + ' / ' + fnum(rowsX[0][2] * 100, 1) + '<small> pt</small>' : '·') + '</div><div class="km">Niño 3.4, day: AIRS / CrIS, 2026 against 2023–2025</div>' + kmeta(null, 'AIRS and CrIS, raw granules', String(RA.updated || '').slice(0, 10)) + '</div>' +
        '<div class="kpi"><div class="kn">daily agreement, convection</div><div class="kv">' + (fin(rc) ? 'r ' + fnum(rc, 2, false) : '·') + '</div><div class="km">day-by-day correlation of the two convection series over Niño 3.4 in ' + cur + '; low is expected: the overpasses are 1.5 hours apart in the diurnal cycle of cloud</div>' + kmeta(null, 'our calculation from the file', String(RA.updated || '').slice(0, 10)) + '</div>' +
        '<div class="kpi"><div class="kn">daily agreement, raw Walker</div><div class="kv">' + (fin(rw) ? 'r ' + fnum(rw, 2, false) : '·') + '</div><div class="km">east–west contrast, day node, ' + cur + '</div>' + kmeta(null, 'our calculation from the file', String(RA.updated || '').slice(0, 10)) + '</div>' +
        '<div class="kpi"><div class="kn">detectors, both platforms</div><div class="kv">' + (Object.keys(CRIS.detectors || {}).length + Object.keys(AIRS.detectors || {}).length) + '<small> · ' + (Object.keys(CRIS.detectors || {}).filter(function (q) { return CRIS.detectors[q].triggered; }).length + Object.keys(AIRS.detectors || {}).filter(function (q) { return AIRS.detectors[q].triggered; }).length) + ' fired</small></div><div class="km">14-day turning-point detectors; none fired: the event is in a steady phase</div>' + kmeta(null, 'AIRS and CrIS', String(RA.updated || '').slice(0, 10)) + '</div>';
      body.appendChild(kx);
    } else if (k === 'profile') {
      row = boxRow(false);
      nt = notes(radF(F, 'profile_anom'), 'Over Niño 3.4 the infrared window and lower troposphere read 17–20 K colder because the instrument sees cloud tops, not the surface; the microwave channels see through and show the troposphere 2–3 K warmer than every analogue year.', []);
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      var CRL = { '662': 'CO₂ 662 cm⁻¹ · stratosphere', '690': 'CO₂ 690 · upper troposphere', '710': 'CO₂ 710 · mid troposphere', '750': 'CO₂ 750 · lower troposphere', '900': 'window 900 · surface or cloud top' };
      var ATL = { ch05: 'ch 5 · ~900 hPa', ch06: 'ch 6 · ~700 hPa', ch07: 'ch 7 · ~400 hPa', ch08: 'ch 8 · ~250 hPa', ch09: 'ch 9 · ~180 hPa', ch10: 'ch 10 · ~90 hPa', ch11: 'ch 11 · ~50 hPa', ch12: 'ch 12 · ~25 hPa', ch13: 'ch 13 · ~10 hPa', ch14: 'ch 14 · ~5 hPa', ch15: 'ch 15 · ~2 hPa' };
      function cell(v) { if (!fin(v)) return '<td class="num">·</td>'; var c = v >= 1 ? ' top' : (v <= -1 ? ' st-ok' : ''); return '<td class="num' + c + '">' + fnum(v, 1) + '</td>'; }
      function tbl(title, prof, LB) { var keys = Object.keys(prof), yrs2 = ['2025', '2024', '2023']; return '<h4 style="margin:8px 0 4px;font-size:12.5px">' + title + '</h4><table class="e"><thead><tr><th>layer</th><th class="num">now, 14 d mean, K</th>' + yrs2.map(function (y) { return '<th class="num">vs ' + y + '</th>'; }).join('') + '</tr></thead><tbody>' + keys.map(function (c) { var p = prof[c]; return '<tr><td>' + esc(LB[c] || c) + '</td><td class="num">' + fnum(p.now14, 1, false) + '</td>' + yrs2.map(function (y) { return cell(p['anom_vs_' + y]); }).join('') + '</tr>'; }).join('') + '</tbody></table>'; }
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap.innerHTML = tbl('NOAA-21 CrIS, infrared (blind under cloud): ' + boxk, (CRIS.profile || {})[boxk] || {}, CRL) + (AIRS.profile ? tbl('Aqua AIRS, infrared, independent platform: ' + boxk, (AIRS.profile || {})[boxk] || {}, CRL) : '') + tbl('NOAA-21 ATMS, microwave (through cloud): ' + boxk, (AT.profile || {})[boxk] || {}, ATL);
      body.appendChild(wrap);
    } else {
      var zones = US.zones || {};
      function zq(z, v) { var q = zones[z] || {}; return q[v] || (v === 'm45_dec' ? { cur: q.cur, median: q.median, max: q.max } : {}); }   // v3: четыре варианта счёта; старая схема — как m45_raw
      var zk = Object.keys(zones).sort(function (a, b) { return (zq(b, 'm45_dec').cur / Math.max(1, zq(b, 'm45_dec').median)) - (zq(a, 'm45_dec').cur / Math.max(1, zq(a, 'm45_dec').median)); });
      var zsel = S.sub.radZone || (zk[0] || 'central_america'), zmode = S.sub.radMode || 'chart';
      row = el('div', 'seg sub');
      zk.forEach(function (z) { var b = el('button', zsel === z ? 'on' : '', z.replace(/_/g, ' ')); b.type = 'button'; b.onclick = function () { S.sub.radZone = z; render(); }; row.appendChild(b); });
      row.appendChild(el('span', 'seg-gap', ''));
      [['chart', 'quakes'], ['table', 'table'], ['sun', 'sun']].forEach(function (o) { var b = el('button', (zmode === o[0] ? 'on' : '') + ' sq', o[1]); b.type = 'button'; b.onclick = function () { S.sub.radMode = o[0]; render(); }; row.appendChild(b); });
      nt = '<b>Quakes, aftershocks separated.</b> Events by Pacific-rim zone in the same calendar window, this year against every year 2000–2025, in four counts: M ≥ 4.5 and M ≥ 5.5, raw and declustered by Gardner–Knopoff (1974) windows. About ' + (US.dependent_frac != null ? Math.round(US.dependent_frac * 100) + ' %' : 'half') + ' of the catalogue are dependent events, so the raw count misleads: Central America looked like a 27-year record by raw M ≥ 4.5 and is below its median once aftershocks are removed. The M ≥ 4.5 threshold is unfit across epochs (network sensitivity grows +10–20 % per decade); an alert would fire only on independent M ≥ 5.5 events. Catalogue magnitudes are a computed product; the raw record is the IRIS seismograms.<br><b>Sun.</b> Sunspots, F10.7 and Kp from GFZ Potsdam over the same window.<br><b>Neither is El Niño physics</b> on this panel: no link is claimed or established (the USGS holds weather and quakes unrelated); they are side series of the same collector.<br><b>Caveats.</b> ' + esc(radCav(cav));
      INFO.push({ key: 'notes', label: 'notes', html: nt, plain: RAD_PLAIN[k] || '' }); infoToggles(row, INFO); body.appendChild(row); infoPane(body, INFO);
      if (zmode === 'sun') {
        var sd = SO.daily_cur || {}, byS = {}; byS[cur] = {}; for (var i2 = 0; i2 < 68; i2++) byS[cur][String(i2)] = sd[String(i2)] ? sd[String(i2)].sunspot : null;
        plot(body, function (w, h) { return chartRadSeries({ byYear: byS, cur: cur, n: 68, dayLabel: dl, zero: true, bars: true, title: 'Sunspot number per day (SILSO via GFZ), ' + cur + ' — the sun in the same window' }, w, h); });
      } else if (zmode === 'chart') {
        var zd = (zones[zsel] || {}).daily_cur_dec || (zones[zsel] || {}).daily_cur || {}, byZ = {}; byZ[cur] = {}; for (var i = 0; i < 68; i++) byZ[cur][String(i)] = zd[String(i)] || 0;
        plot(body, function (w, h) { return chartRadSeries({ byYear: byZ, cur: cur, n: 68, dayLabel: dl, zero: true, bars: true, title: 'Independent quakes M ≥ 4.5 per day (aftershocks removed), ' + zsel.replace(/_/g, ' ') + ', ' + cur }, w, h); });
      } else {
        var wz = el('div'); wz.style.cssText = 'flex:1;min-height:0;overflow:auto';
        wz.innerHTML = '<table class="e"><thead><tr><th>zone</th><th class="num">M ≥ 4.5 raw</th><th class="num">M ≥ 4.5 independent</th><th class="num">median · max</th><th class="num">rank of 27</th><th class="num">M ≥ 5.5 independent</th><th class="num">trend, % per decade</th></tr></thead><tbody>' +
          zk.map(function (z) { var r45 = zq(z, 'm45_raw'), d45 = zq(z, 'm45_dec'), d55 = zq(z, 'm55_dec'); var hot = d55.cur > d55.max; return '<tr><td>' + esc(z.replace(/_/g, ' ')) + '</td><td class="num">' + (r45.cur != null ? r45.cur : '·') + '</td><td class="num' + (hot ? ' top' : '') + '"><b>' + (d45.cur != null ? d45.cur : '·') + '</b></td><td class="num">' + (d45.median != null ? d45.median : '·') + ' · ' + (d45.max != null ? d45.max : '·') + '</td><td class="num">' + (d45.rank != null ? d45.rank : '·') + '</td><td class="num">' + (d55.cur != null ? d55.cur : '·') + ' <small>vs ' + (d55.median != null ? d55.median : '·') + '</small></td><td class="num">' + (d45.trend_pct_decade != null ? fnum(d45.trend_pct_decade, 1) : '·') + '</td></tr>'; }).join('') + '</tbody></table><div class="cap">Independent = aftershocks removed by Gardner–Knopoff windows; rank 1 = the busiest of the 27 windows 2000–2026; the trend is the growth of independent counts per decade, mostly the network, not the Earth.</div>';
        body.appendChild(wz);
      }
      var q0 = zq(zsel, 'm45_dec'), q0r = zq(zsel, 'm45_raw'), q55 = zq(zsel, 'm55_dec'), wm = SO.window_means || {}, lastS = wm[cur] || {};
      var ks2 = el('div', 'kpis');
      ks2.innerHTML = '<div class="kpi"><div class="kn">' + esc(zsel.replace(/_/g, ' ')) + ' · independent M ≥ 4.5</div><div class="kv">' + (q0.cur != null ? q0.cur : '·') + '<small> vs median ' + q0.median + ', max ' + q0.max + (q0r.cur != null ? '; raw ' + q0r.cur : '') + '</small></div><div class="km">aftershocks removed' + (q55.cur != null ? '; M ≥ 5.5 independent: ' + q55.cur + ' vs median ' + q55.median : '') + '</div>' + kmeta(null, 'USGS catalogue, declustered', String(RA.updated || '').slice(0, 10)) + '</div>' +
        '<div class="kpi"><div class="kn">sun in the window · ' + cur + '</div><div class="kv">' + fnum(lastS.sunspot, 0, false) + '<small> sunspots</small></div><div class="km">F10.7 ' + fnum(lastS.f107, 0, false) + '; Kp max ' + fnum(lastS.kp_max, 1, false) + '; ' + lastS.storm_days_kp5 + ' storm days (Kp ≥ 5)</div>' + kmeta(null, 'GFZ Potsdam', String(RA.updated || '').slice(0, 10)) + '</div>' +
        '<div class="kpi"><div class="kn">same window, our years</div><div class="kv" style="font-size:14px">' + ['2015', '2023', '2024', '2025'].filter(function (y) { return wm[y]; }).map(function (y) { return y + ': ' + fnum(wm[y].sunspot, 0, false) + ' spots, ' + wm[y].storm_days_kp5 + ' storms'; }).join(' · ') + '</div><div class="km">no physical link to El Niño is claimed</div>' + kmeta(null, 'GFZ Potsdam', String(RA.updated || '').slice(0, 10)) + '</div>';
      body.appendChild(ks2);
    }
    worksFoot(body, 'block:radiance');

    function pct(by) { var o = {}; Object.keys(by).forEach(function (y) { o[y] = {}; Object.keys(by[y]).forEach(function (d) { var v = by[y][d]; o[y][d] = fin(v) ? v * 100 : null; }); }); return o; }
    /* плашки: последние 14 дней этого года против среднего по окну каждого прошлого года */
    function kpiLast(by, mult, unit, name, meaning) {
      function m14(o) { var ks = Object.keys(o || {}).map(Number).sort(function (a, b) { return a - b; }).slice(-14); var v = ks.map(function (kk) { return o[String(kk)]; }).filter(fin); return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : null; }
      function mAll(o) { var v = Object.keys(o || {}).map(function (kk) { return o[kk]; }).filter(fin); return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : null; }
      var now = m14(by[cur]), out = { by: {} }, yrs = Object.keys(by).filter(function (y) { return y !== cur; }).sort(), vals = [];
      yrs.forEach(function (y) { var v = mAll(by[y]); if (fin(v)) { vals.push(v); out.by[y] = fnum(v * (mult === 100 ? 1 : 1), mult === 100 ? 1 : 1, false) + unit; } });
      out.now = fin(now) ? fnum(now, mult === 100 ? 1 : 1, false) + unit : '·';
      out.name = name; out.meaning = meaning; out.diff = fin(now) && vals.length ? now - vals.reduce(function (a, b) { return a + b; }, 0) / vals.length : null;
      out.yrs = yrs;
      return out;
    }
    function kpiRow(st) {
      var kp = el('div', 'kpis');
      kp.innerHTML = '<div class="kpi"><div class="kn">' + st.name + '</div><div class="kv">' + esc(st.now) + '</div><div class="km">' + esc(st.meaning) + '</div>' + kmeta(null, PLAT + ', raw granules', String(RA.updated || '').slice(0, 10)) + '</div>' +
        st.yrs.map(function (y) { return '<div class="kpi"><div class="kn">' + y + ' · same window</div><div class="kv">' + esc(st.by[y] || '·') + '</div><div class="km">window mean of that year</div>' + kmeta(null, PLAT + ', raw granules', y) + '</div>'; }).join('') +
        (st.diff != null ? '<div class="kpi"><div class="kn">against the mean of past years</div><div class="kv">' + fnum(st.diff, 1) + '<small>' + (st.now.slice(-2) === ' %' ? ' pt' : ' K') + '</small></div><div class="km">this year’s last 14 days minus the average of the past windows</div>' + kmeta(null, 'our own difference', String(RA.updated || '').slice(0, 10)) + '</div>' : '');
      return kp;
    }
  }

  /* ШАР (пилот, владелец 08.09: «переключатель на каждое наше представление, чтобы на шаре
     видеть, где уместно»). Библиотека globe.gl (MIT, three.js) грузится по требованию с jsdelivr,
     только когда человек нажал «globe»; страница без неё не тяжелеет. Данные — data/enso/globe.json
     (globe_data.py): аномалия OISST за последний день на сетке 1°, боксы и буи из того, что уже
     посчитано. Текстура шара рисуется на холсте из сетки, береговая линия — наш coast.json. */
  var GLOBE_VIEWS = { now: 'nino', regions: 'land', ocean: 'moorings', radiance: 'radiance', trend: 'rain' };
  function globeMode() {
    var m = GLOBE_VIEWS[S.view]; if (!m) return null;
    if (S.view === 'now' && (S.sub.now || 'analogs') !== 'map') return null;
    if (S.view === 'ocean' && (S.sub.ocean || 'surface') !== 'moorings') return null;
    if (S.view === 'trend' && (S.sub.trend || 'sst_nino34') !== 'rain') return null;
    return m;
  }
  function globeLib() {
    if (window.Globe) return Promise.resolve();
    if (S._globeLoad) return S._globeLoad;
    S._globeLoad = new Promise(function (ok, bad) {
      var sc = document.createElement('script'); sc.src = 'https://cdn.jsdelivr.net/npm/globe.gl'; sc.async = true;
      sc.onload = function () { ok(); }; sc.onerror = function () { S._globeLoad = null; bad(new Error('globe.gl did not load')); };
      document.head.appendChild(sc);
    });
    return S._globeLoad;
  }
  function globeData() {
    if (S.GL) return Promise.resolve(S.GL);
    return Promise.all([get('/data/enso/globe.json'), S.COAST ? Promise.resolve(S.COAST) : get('/data/enso/coast.json').catch(function () { return null; })])
      .then(function (r) { S.GL = r[0]; if (r[1]) S.COAST = r[1]; return S.GL; });
  }
  function sstColor(v) {   // расходящаяся шкала: синий холоднее, красный теплее, ±3 °C полный цвет
    if (!fin(v)) return null;
    var a = Math.max(-1, Math.min(1, v / 3));
    return a >= 0 ? 'rgba(' + Math.round(180 + 60 * a) + ',' + Math.round(120 - 90 * a) + ',' + Math.round(90 - 60 * a) + ',' + (0.35 + 0.65 * Math.abs(a)).toFixed(2) + ')'
                  : 'rgba(' + Math.round(110 + 40 * a) + ',' + Math.round(150 + 30 * a) + ',' + Math.round(210) + ',' + (0.35 + 0.65 * Math.abs(a)).toFixed(2) + ')';
  }
  function globeTexture(G) {
    var W = 1440, H = 720, c = document.createElement('canvas'); c.width = W; c.height = H;
    var x = c.getContext('2d');
    x.fillStyle = '#1b2230'; x.fillRect(0, 0, W, H);                     // суша и полюса
    x.fillStyle = '#2b3446'; x.fillRect(0, H * (30 / 180), W, H * (120 / 180));   // океан без данных
    var g = G.sst; if (g && g.rows) {
      var s = g.step || 1, px = W / 360 * s, py = H / 180 * s;
      g.rows.forEach(function (row, i) {
        var lat = g.lat0 + i * s;                                       // lat0 = -60 → вверх
        row.forEach(function (v, j) {
          var col = sstColor(v); if (!col) return;
          var lon = g.lon0 + j * s;
          x.fillStyle = col; x.fillRect((lon + 180) / 360 * W, (90 - lat - s) / 180 * H, px + .5, py + .5);
        });
      });
    }
    var CO = S.COAST; if (CO && CO.polys) {
      x.strokeStyle = 'rgba(235,225,205,.55)'; x.lineWidth = 1.2;
      CO.polys.forEach(function (poly) { x.beginPath(); poly.forEach(function (q, k) { var X = (q[0] + 180) / 360 * W, Y = (90 - q[1]) / 180 * H; if (k) x.lineTo(X, Y); else x.moveTo(X, Y); }); x.stroke(); });
    }
    return c.toDataURL('image/png');
  }
  /* Бокс через 180-й меридиан (Niño 4: 160°E → 150°W) библиотека натягивала на всю сферу —
     крышка закрывала весь шар красным. Такие боксы режем на две половины по антимеридиану. */
  function boxPoly(b) {
    var lo0 = b.lon[0], lo1 = b.lon[1];
    if (lo1 > 180) lo1 -= 360;
    // d3-geo: кольцо по часовой стрелке = внутренность; против часовой шар красил целиком (проверено 08.09)
    function ring(a, c) { return [[a, b.lat[0]], [a, b.lat[1]], [c, b.lat[1]], [c, b.lat[0]], [a, b.lat[0]]]; }
    if (lo0 > lo1) return { type: 'MultiPolygon', coordinates: [[ring(lo0, 179.99)], [ring(-179.99, lo1)]] };
    return { type: 'Polygon', coordinates: [ring(lo0, lo1)] };
  }
  /* Шрифт подписей на шаре знает только ASCII: «Niño» ломалось (владелец 08.09), ° тоже. */
  function gl(t) { return String(t).replace(/ñ/g, 'n').replace(/Ñ/g, 'N').replace(/°/g, '').replace(/−/g, '-').replace(/[^\x20-\x7e]/g, ''); }
  function mountGlobe(mode) {
    var body = document.querySelector('.stage-body'); if (!body) return;
    var plot = body.querySelector('.plot');
    var box = el('div', 'globe-box'); box.innerHTML = '<div class="globe-wait">loading the globe…</div>';
    if (plot) body.replaceChild(box, plot); else body.insertBefore(box, body.firstChild.nextSibling || null);
    S.plotEl = null; S.draw = null;
    Promise.all([globeLib(), globeData()]).then(function (r) {
      if (!box.isConnected) return;
      var G = r[1], W = Math.max(300, box.clientWidth), H = Math.max(300, box.clientHeight);
      box.innerHTML = '';
      var kinds = { nino: ['nino'], land: ['land'], moorings: ['nino'], radiance: ['radiance'], rain: ['land'] }[mode] || ['nino'];
      var polys = (G.boxes || []).filter(function (b) { return kinds.indexOf(b.kind) >= 0; });
      function val(b) { return mode === 'rain' ? b.rain_pct : b.value; }
      var vmaxSet = 0; polys.forEach(function (b) { var v = val(b); if (fin(v) && mode !== 'rain') vmaxSet = Math.max(vmaxSet, Math.abs(v)); });
      function colr(b) {
        var v = val(b); if (!fin(v)) return 'rgba(200,200,200,.25)';
        if (mode === 'rain') { var d = Math.max(-1, Math.min(1, (v - 100) / 100)); return d < 0 ? 'rgba(212,115,92,' + (0.3 + 0.6 * -d).toFixed(2) + ')' : 'rgba(124,155,203,' + (0.3 + 0.6 * d).toFixed(2) + ')'; }
        var op = vmaxSet ? Math.abs(v) / vmaxSet : 1;
        return heatColor(v, op).replace('hsl(', 'hsla(').replace(')', ',' + (0.55 + 0.35 * op).toFixed(2) + ')');
      }
      var g = Globe({ animateIn: false })(box)
        .width(W).height(H).backgroundColor('rgba(0,0,0,0)')
        .globeImageUrl(globeTexture(G)).showAtmosphere(true).atmosphereColor('#7C9BCB').atmosphereAltitude(0.12)
        .polygonsData(polys.map(function (b) { return { geo: boxPoly(b), b: b }; }))
        .polygonGeoJsonGeometry(function (d) { return d.geo; })
        .polygonCapColor(function (d) { return colr(d.b); })
        .polygonSideColor(function () { return 'rgba(0,0,0,0)'; })
        .polygonStrokeColor(function () { return '#f2e9d8'; })
        .polygonAltitude(0.008)
        .polygonLabel(function (d) { return '<div style="font:12px/1.4 system-ui;padding:4px 6px;background:rgba(20,24,32,.9);color:#eee;border-radius:6px"><b>' + esc(d.b.label) + '</b><br>' + esc(d.b.text || '') + (d.b.date ? '<br><small>' + esc(d.b.date) + '</small>' : '') + '</div>'; })
        .labelsData(polys.map(function (b) { var lc = (b.lon[0] + b.lon[1]) / 2; if (lc > 180) lc -= 360; return { lat: (b.lat[0] + b.lat[1]) / 2, lng: lc, sz: 1.1, text: gl(b.label.replace(/^Satellite: /, '') + (fin(val(b)) ? '  ' + (mode === 'rain' ? val(b) + ' %' : fnum(val(b), 1) + (mode === 'radiance' ? ' %' : ' C')) : '')) }; })
          .concat(mode === 'moorings' ? (G.moorings || []).map(function (m) { return { lat: m.lat + 1.2, lng: m.lon, sz: 0.7, text: gl((m.label || m.id || '').replace(/^TAO /, '') + (fin(m.value) ? '  ' + fnum(m.value, 1) + ' C at ' + m.depth + ' m' : '')) }; }) : []))
        .labelSize(function (d) { return d.sz; }).labelColor(function () { return '#f2e9d8'; }).labelDotRadius(0).labelAltitude(0.012);
      if (mode === 'moorings') {
        g.pointsData(G.moorings || []).pointLat('lat').pointLng('lon')
          .pointAltitude(function (d) { return fin(d.value) ? 0.02 + d.value / 60 : 0.02; })
          .pointRadius(0.6).pointColor(function (d) { return fin(d.value) ? '#D4735C' : '#888'; })
          .pointLabel(function (d) { return '<div style="font:12px/1.4 system-ui;padding:4px 6px;background:rgba(20,24,32,.9);color:#eee;border-radius:6px"><b>' + esc(d.label) + '</b><br>' + esc(d.text) + (d.date ? '<br><small>' + esc(d.date) + '</small>' : '') + '</div>'; });
      }
      var focus = { nino: -140, land: 40, moorings: -150, radiance: -170, rain: 40 }[mode] || -140;
      g.pointOfView({ lat: mode === 'land' || mode === 'rain' ? 10 : 0, lng: focus, altitude: 2.1 }, 0);
      g.controls().autoRotate = true; g.controls().autoRotateSpeed = 0.35;
      var leg = el('div', 'globe-legend');
      leg.innerHTML = '<b>' + ({ rain: 'boxes: rain, % of normal over 30 days', land: 'boxes: air anomaly over 30 days, °C', radiance: 'boxes: deep convection, % of footprints', moorings: 'boxes: NOAA weekly anomaly, °C' }[mode] || 'boxes: NOAA weekly anomaly, °C') + '</b> · sea: OISST anomaly ' + esc((G.sst || {}).date || '') + ' against 1971–2000' +
        '<span class="gl-bar"></span>−3 … +3 °C · drag to turn, wheel to zoom, point at a box' + (mode === 'moorings' ? '; pillars: warmest layer under each mooring' : '');
      box.appendChild(leg);
      S._globeInst = g; window.B42Globe = g;   // наружу — для отладки из консоли
    }).catch(function (e) { box.innerHTML = '<div class="note warn">The globe did not load: ' + esc(String(e.message || e)) + '. The flat view is one click away.</div>'; });
  }

  /* SOURCE И NOTES НА КАЖДОЙ СЦЕНЕ (владелец 08.09: «source и notes везде, например #models»;
     «простой человеческий вариант описания переключателем, техническое сохранить»). Для каждой
     сцены здесь: source — откуда числа; plain — в чём суть, двумя-тремя фразами для обычного
     человека; tech — техническое, к нему прибавляются подписи сцены (.cap), которые с экрана
     убираются в этот же разбор. Стандарт сцены: сверху график, ниже плашки, слова — за кнопками. */
  var SCENE_INFO = {
    verdict: { source: 'The verdict is written by DeepSeek V4 Pro from the numbers on this panel and checked by Claude (Fable) against the same numbers; nothing in it is typed by hand. The numbers come from the daily and weekly rows below.',
      plain: 'This is the machine’s summary of where the event stands today, in plain words: what is happening, whether it has turned, what to watch next and what we are not sure about. A second machine checks every number in it before it goes out.',
      tech: 'The model receives a digest of the panel’s state (series, ranks, records, detectors, model plume) and returns verdict, turning point, outlook, watch list, confidence and caveats; a review pass compares each number with the digest and edits wording only. Corrections to earlier verdicts stay in the history.' },
    overview: { source: 'Every tile is the same chart as on its own scene, drawn small from the same files; the strip on top repeats the headline numbers.',
      plain: 'One screen with everything: the key numbers on top, and below them small versions of every chart. Point at a tile to read what it means, click it to open the full scene.',
      tech: 'Tiles are rendered by the scene chart functions in a tight mode: annotations removed, axes thinned to first and last labels, viewBox cropped to the drawn content. The strip is built from latest.json, precip.json, radiance.json, spectral.json and mentions.json.' },
    news: { source: 'Built by rules from the value journal (data/enso/journal.json): a line appears when a number, a risk level, an alert or the verdict changed in the last seven days. Release dates come from each source’s schedule.',
      plain: 'What changed in the last week and what is due next: new records, alerts that fired, risks that moved a level, and the releases we are waiting for.',
      tech: 'Unchanged values are skipped; absolute series carry no sign; a verdict rewritten on the same numbers is marked as reworded, not changed. Nothing here is written by a model.' },
    mentions: { source: 'Google News RSS editions in nine languages and Bing News (headlines and publisher), Wikimedia page views of the El Niño article in nine languages, RSS of agencies and forecast centres filtered to ENSO posts.',
      plain: 'How much the world is talking about the event and where: headlines by language, Wikipedia readers per day, and what the forecast centres publish. This is talk, not measurement.',
      tech: 'Each edition holds only its latest hundred items, so older days are undercounted; duplicates are removed by normalised title; GDELT is optional and rate-limited; official feeds show only posts mentioning ENSO and list the silent ones.' },
    now: { source: 'NOAA CPC weekly Niño indices (wksst9120), NOAA OISST v2.1 daily boxes read from the ERDDAP grid with our own 1991–2020 climatologies, NOAA ONI, IRI plume, Natural Earth coastline.',
      plain: 'Where the event stands against the strongest ones on record on the same calendar days, week by week and on the map of the Pacific. A rank of 1 means warmer than any past event at this point of the year.',
      tech: 'Analogue years are 1982, 1997, 2015 and 2023 aligned on day of year; the map colours the four Niño boxes by the weekly anomaly and shows the same week of the comparison event underneath; the play control steps the last twenty weeks.' },
    ocean: { source: 'OISST v2.1 daily boxes (own climatology), TAO/TRITON moorings via PMEL ERDDAP (daily profiles), GODAS reanalysis via NOAA PSL OPeNDAP (monthly sections and the Hovmöller diagram).',
      plain: 'The ocean from the surface down: daily surface temperature by box, the moorings that measure the warm water below, and the reanalysis picture of heat moving east along the equator month by month.',
      tech: 'Mooring anomalies are against the 1991–2020 climatology of each station; the SHOUT rule for the subsurface fires only above the mooring’s own record before this event; GODAS lags about six weeks and smooths extremes; the Hovmöller rows are monthly anomalies at ~95 m or the 20 °C isotherm depth.' },
    radiance: { source: 'NOAA-21 CrIS and ATMS granules read straight from the anonymous NOAA NODD bucket by an external collector (C:\\CL\\radiance, schema v2); USGS catalogue; GFZ solar indices.',
      plain: 'What the satellite itself sees over the Pacific: where the tall storm clouds are, how the east-west contrast has collapsed, and how much the moist air traps heat. Measured by us from the raw data, not taken from anyone’s product.',
      tech: 'Brightness temperatures, not air or ocean temperature; the record starts in February 2023; infrared is blind under cloud (that is the convection signal), microwave sees through; G_clear on the warmest tenth of scenes is partly residual cloud, on the strictest percent the signal halves but stays.' },
    models: { source: 'IRI/CPC ENSO plume, monthly issues: two dozen dynamical and statistical models; our classification of each model against the observed ONI.',
      plain: 'What the forecast centres expect and how well they have kept up: which models have fallen below reality, how each issue revised upward, and where the combined forecast now puts the peak.',
      tech: 'A model is counted broken when its forecast for a season already observed lies below the observed ONI by the threshold; the stack shows three issues on the same calendar; the breakdown is the share of models below reality per issue; RONI removes the warm background from ONI.' },
    air: { source: 'NOAA PSL daily and monthly indices (SOI, OLR, 850 hPa zonal wind), ERA5 wind via Open-Meteo, PMEL warm water volume and 300 m temperature, UAH satellite layers, World Bank Pink Sheet commodity prices.',
      plain: 'The atmosphere and the fuel: whether the winds and pressure have joined the ocean, how much warm water is stored below the surface to feed the event, and how the air and food prices answer.',
      tech: 'Coupling counts the atmospheric signs in place (SOI, OLR, westerlies); the fuel is warm water volume as a share of its record with its lead on the surface; layers are UAH lower-troposphere anomalies; commodity alerts use weights, seasonal z-scores and year-on-year percentiles.' },
    trend: { source: 'Daily series from climatereanalyzer.org (OISST Niño 3.4 and world ocean, ERA5 2 m air), ERA5 land boxes via Open-Meteo, GPCP monthly rain, NOAA OHC, our own spectral test and risk index history.',
      plain: 'The daily temperature rows over the last year and more, with every past year as a band behind them, records marked, a two-week outlook from similar days, plus rain by region and a watch for unusual rhythms in the data.',
      tech: 'Records are per calendar day since the start of each series; CUSUM accumulates excess above a threshold; the 14-day forecast is the spread of what followed similar states; land boxes are 3×3 ERA5 grid means; the spectral watch tests 30-day windows for lines at 2–7 days against red noise with a multiplicity correction.' },
    regions: { source: 'A hand-written reference by region (typical impacts by season, food exposure, sources with DOIs), the Gulf block with measured series, and for six regions the ERA5 box series and rain from the same data as on Dynamics.',
      plain: 'What this event usually does to each region and what is measured there now: the air over the region, the rain against normal, and the typical picture by season.',
      tech: 'Levels by scenario come from the reference tables keyed to event strength; measured blocks are shown only where a box or station exists; Gulf sea and weather series are our own OISST box and ERA5 point.' },
    food: { source: 'FAO Food Price Index monthly, World Bank Pink Sheet monthly commodity prices, FAOSTAT dietary shares for the weights, our own onset dates for past events.',
      plain: 'What food prices are doing: the world index, twelve commodities by name in dollars per tonne, and how each moved after the start of past events. A rise in time with the event is not proof of cause.',
      tech: 'Paths after onset are percentages of the onset-month price; in dollars they are scaled through the onset or today’s price; weights 1–5 order the alerts; the bundle uses a log scale; series are nominal, not inflation-adjusted.' },
    planet: { source: 'NOAA GML greenhouse gases, NSIDC sea ice index v4, Met Office HadCRUT5 (global) and CRUTEM5 (land), NOAA NCEI land monthly, NOAA STAR sea level, and the daily ERA5 and OISST series from climatereanalyzer (world, hemispheres, tropics, Arctic, Antarctic, ocean) drawn year by year.',
      plain: 'The long record behind the event: gases in the air, ice at both poles, the planet’s temperature and sea level, decades at a glance. The El Niño years and the years after them are highlighted.',
      tech: 'Annual and daily series are shown against their own baselines as stated on each chart; CO₂ uses the trend column of the GML file; sea level has no glacial isostatic adjustment.' },
    how: { source: 'Written by hand: glossary, method notes and the release calendar of every source.',
      plain: 'The dictionary of the panel: what each term means, why it matters here, and where it comes from; plus how the whole thing is put together and when each source updates.',
      tech: 'Glossary keys match data-term attributes in the code; the calendar is the publishing cadence of each provider, not our run times.' },
    research: { source: 'The statements of this panel (risks, alerts, indicators, glossary, scenes, the concept register) searched in the browser; the model contour is specified in the concept note and not yet wired.',
      plain: 'A conversation that builds a small research board: what you ask, the panel answers with its own statements, and the left side collects the numbers, concepts, scenes and papers involved.',
      tech: 'Retrieval is lexical over ~450 short units built from latest.json, journal.json, glossary.json, SCENE_INFO and concepts.json; anchors of the hits drive concepts (concepts.json) and works (links.json); saving is localStorage (b42_research).' },
    refs: { source: 'Our parsed arXiv works attached to claims by a model with a deny list, the register of data sources, quoted literature, and a hand-written list of kindred projects with licences checked at the source.',
      plain: 'Everything we lean on: the papers we have read that support a claim, the data providers, the reports we quote, and similar projects elsewhere.',
      tech: 'Links are proposed by a model from the pool of parsed works and filtered by links-deny.json; anchors are risks, alerts, regions, terms and hand-written claim blocks; a work standing at many anchors is flagged in the check as possibly too general.' },
    chain: { source: 'A hand-written map of sources, collectors, computed states and outputs; dates and freshness dots come from latest.json and the value journal.',
      plain: 'How a number travels: from the provider through our collectors and rules to the page you are reading. Click a node to see what depends on it.',
      tech: 'Nodes carry src_keys and journal keys; the green dot means the source answered on the last run; the date is when its data last changed, not when we asked.' },
    ops: { source: 'data/enso/ops.json and runs.json, written at the end of every run by ops.py; the fresh layer from fresh.py.',
      plain: 'The service room: which runs happened, how long they took and whether they finished, which source is behind, and what new data has arrived that the verdict has not looked at yet.',
      tech: 'Runs are recorded by kind with start, seconds, status and notes; sources carry date ranges read from the raw copies; the fresh layer compares light-run tails with the assessed state and lists crossed triggers.' },
    about: { source: 'Written by hand.', plain: 'What this panel is, who writes what, and how to read it.', tech: 'The division of labour: rules compute, DeepSeek writes the verdict, Claude checks it, a person runs the updates and publishes.' }
  };

  /* ПЛАШКИ KPI: ПРОСТОЕ ОБЪЯСНЕНИЕ (владелец 08.09: «простое объяснение к плашкам KPI»).
     Ключ — подпись плашки (текст .kn до « · », без дат и чисел) или её термин; кнопка «?»
     раскрывает абзац человеческими словами. Подписи без записи в словаре кнопки не получают. */
  var KPI_PLAIN = {
    'same 30 days in our years': 'The same calendar days in each of our reference events, so this year is compared like with like.',
    'who wrote and who checked': 'Who produced the readings on this page and who checked them afterwards.',
    'who publishes most': 'The outlet that has written most about the event in our mentions feed over the window.',
    'where the past events went': 'What this same reading did next in the strongest past events after this point of the calendar.',
    'warmest anomaly': 'The warmest water under the surface in this frame of the film, and how deep it sits.',
    'verdicts stored': 'How many links between a claim on the panel and a parsed work have been judged and kept.',
    'upper-ocean heat, 0–300 m': 'Heat stored in the top 300 m of the equatorial Pacific: the fuel an El Niño draws on.',
    'this calendar year': 'The value accumulated since 1 January of this year.',
    'the box': 'The rectangle of sea or land we average over; its corners are named in the source.',
    'sun in the window': 'Solar activity over the same days, shown for completeness; it does not drive El Niño.',
    'strongest rise, year on year': 'The food group whose price rose most against the same month a year earlier.',
    'scenario in force': 'Which of the three scenarios (base, strong, record) the data currently support.',
    'same window, our years': 'The same span of days in the reference years, for a like-for-like comparison.',
    'same month in our years': 'The same month in the reference years, for a like-for-like comparison.',
    'same window': 'The same span of days in that year.',
    'records and cusum': 'How many days set a record for their date, and whether the running sum of surprises has crossed its alarm line.',
    'record days': 'Days when the reading was the highest ever seen on that date.',
    'rain, last 30 days': 'Rain that fell over the region in the last 30 days, against what is normal for these dates.',
    'rain since': 'Rain accumulated since the start of the wet season, against normal.',
    'planet': 'The whole-planet value for the latest month from the global dataset.',
    'peak of the charge': 'The highest the ocean fuel reading reached while the event was charging.',
    'moorings live': 'How many of the equatorial buoys are reporting; the silent ones are named.',
    'lead over the surface': 'How far the water below has run ahead of the surface: a warm layer at depth reaches the surface later.',
    'last day': 'The latest daily value we hold.',
    'last 90 days': 'The mean of the last 90 days against the same dates in past years.',
    'last 30 days to': 'The mean of the last 30 days, ending on the date shown.',
    'last 30 days': 'The mean of the last 30 days against the same dates in past years.',
    'languages': 'How many languages the mentions feed covers.',
    'lag': 'How far the forecast trails behind what the ocean has already done.',
    'hottest day this year': 'The hottest day of this year in the region, with its date.',
    'heat, 0–700 m': 'Heat stored in the top 700 m of the world ocean: a slow reading that moves over years.',
    'heat, 0–2000 m': 'Heat stored in the top 2000 m of the world ocean: the slowest and steadiest reading on the panel.',
    'frames': 'How many monthly frames the film holds.',
    'forecast +14 days': 'Where the reading is expected in two weeks if it keeps following its analogue years.',
    'days above 35 °c': 'How many days this year the air over the region passed 35 °C.',
    'bursts, 120 days': 'How many westerly wind bursts the last 120 days held; a burst pushes warm water east.',
    'burst window': 'The span of days we scan for westerly wind bursts.',
    'amplitude': 'How strong the MJO pulse is; below 1 it is too weak to matter.',
    'air over the region, last day': 'The air temperature over the region on the latest day, against normal for the date.',
    'against the mean of past years': 'This year’s value minus the average of the reference years over the same window.',
    'wikipedia, english': 'How much attention the event gets on English Wikipedia over the window.',
    'gpcp, last month': 'Global rain for the last complete month from the satellite-and-gauge dataset.',
    'warm water volume': 'How much warm water sits above the 20 °C surface along the equator: the fuel gauge of an El Niño.',
    'last week': 'Westerly wind over the last week; a strong westerly burst pushes warm water east.',
    'noaa weekly': 'NOAA’s official weekly sea-surface anomaly for the zone.',
    'event type': 'Whether the warmest water sits in the east (canonical) or the centre (Modoki) of the Pacific.',
    'warmest layer': 'The warmest anomaly under the mooring and the depth it sits at.',
    'mooring': 'One equatorial buoy: its latest reading down the water column.',
    'upper 300 m': 'Mean temperature anomaly of the top 300 m along the equator.',
    'roni': 'ONI with the global warming trend removed: the El Niño signal on its own.',
    'risk index': 'Our 0–100 score of how strong and how certain the event is, built from the readings on this panel.',
    'oni official': 'The official three-month mean of Niño 3.4: the number NOAA declares El Niño by.',
    'daily oisst': 'The daily satellite-and-buoy sea-surface temperature for the zone.',
    'phase today': 'Where the MJO pulse sits today on its trip around the tropics.',
    'mei v2': 'A combined index of sea temperature, pressure, wind and cloud: El Niño read from five signs at once.',
    'indian ocean dipole': 'The temperature difference between the west and east Indian Ocean; a positive dipole often comes with El Niño.',
    'gulf today': 'The sea surface of the Gulf today, against normal for the date.',
    'food-security weight': 'The weight we give the region in food-security terms.',
    'fao food price index': 'The FAO index of world food prices, where 2014–2016 = 100.',
    'energy imbalance': 'How much more energy the planet takes in than it sends back to space, from the literature.',
    '20 °c isotherm': 'The depth of the 20 °C water: the boundary between the warm upper layer and the cold below.',
    'm ≥ 4.5 in the window': 'Earthquakes of magnitude 4.5 and above in the zone over the window; shown beside the climate rows, not as a cause.',
    'this event, today': 'Where this event stands today.',
    'at the same date in': 'The same reading at the same date in that past event.',
    'warmest at': 'The warmest water at that depth in this month of the film.',
    'deepest thermocline anomaly': 'How far the warm-cold boundary has been pushed down this month.',
    'clear sky': 'The share of satellite scenes with no cloud, last 14 days.',
    'deep convection': 'The share of satellite scenes with very cold cloud tops: tall storm clouds.',
    'walker': 'The contrast between the east and west of the Pacific as the satellite sees it; near zero means the storms moved east.',
    'southern oscillation index': 'The air-pressure difference between Tahiti and Darwin; strongly negative means El Niño.',
    'convection at the date line (olr)': 'Heat radiated to space near the date line; low values mean tall storm clouds have moved to the centre of the Pacific.',
    'trade wind, western pacific': 'Strength of the easterly trade winds in the west; weaker or reversed trades let warm water flow east.',
    'trade wind, central pacific': 'Strength of the easterly trade winds in the centre; weaker or reversed trades let warm water flow east.',
    'niño 3.4 weekly': 'NOAA’s official weekly sea-surface anomaly for the central Pacific zone: the standard El Niño gauge.',
    'niño 3.4 daily box': 'Our own daily mean of the central Pacific zone from the satellite-and-buoy dataset.',
    'niño 3.4': 'Sea surface of the central Pacific zone: the standard El Niño gauge.',
    'niño 3': 'Sea surface of the east-central zone, between the centre and the coast.',
    'niño 1+2': 'Sea surface off the coast of Peru: the first zone to warm in an eastern event.',
    'niño 4': 'Sea surface of the western zone, where the warm pool normally sits.',
    'gulf': 'Sea surface of the Gulf against normal for the date.',
    'the gulf': 'Sea surface of the Gulf against normal for the date.',
    'world ocean': 'The mean sea-surface anomaly of the whole world ocean.',
    'models': 'How many forecast models have fallen below what the ocean already did.',
    'fuel': 'Warm water stored above the 20 °C surface along the equator: the fuel of the event.',
    'under the surface': 'The warmest anomaly below the surface and its depth: what will surface later.',
    'wind bursts': 'Westerly wind bursts in the last months; each pushes warm water east.',
    'food index': 'The FAO index of world food prices, 2014–2016 = 100.',
    'core vs 1997': 'How the central Pacific compares with the same date in the 1997–98 event.',
    'raw walker': 'The east-west contrast the satellite sees at the top of the atmosphere; near zero means the storms moved east.',
    'rain, planet': 'Global rain for the last complete month against normal.',
    'driest region, 30 d': 'The region of ours with the least rain against normal over the last 30 days.',
    'peru coast, air': 'Air temperature over the coast of Peru against normal.',
    'spectral watch': 'Whether any daily series shows a 2–7 day rhythm over the last 30 days: watched, not assumed.',
    'in the news': 'How much the event is written about, from our mentions feed.',
    'co₂': 'Carbon dioxide in the air at Mauna Loa, the latest month; it does not follow El Niño week by week.',
    'ch₄': 'Methane in the air, the latest month from the global network.',
    'n₂o': 'Nitrous oxide in the air, the latest month from the global network.'
  };
  function kpiKey(kn) {
    var t = kn.querySelector('[data-term]'), cands = [];
    if (t) cands.push((t.textContent || '').toLowerCase().trim());
    var txt = (kn.textContent || '').normalize('NFC').replace(/\u00a0/g, ' ').replace(/\?$/, '').toLowerCase();
    cands.push(txt.trim()); txt.split(' · ').forEach(function (p) { cands.push(p.replace(/\b(19|20)\d\d\b/g, '').trim()); });
    var keys = Object.keys(KPI_PLAIN).sort(function (a, b) { return b.length - a.length; });
    for (var i = 0; i < cands.length; i++) {
      var c = cands[i]; if (!c) continue;
      if (KPI_PLAIN[c]) return c;
      for (var k = 0; k < keys.length; k++) if (c.indexOf(keys[k]) === 0) return keys[k];
    }
    return null;
  }
  /* Плашки: якорь облака и ключ простого объяснения; само объяснение живёт в подсказке
     (владелец 08.09: «вопросики не обязательно, в окошке тултипа достаточно»). */
  function kpiExplain() {
    [].slice.call(document.querySelectorAll('.stage-body .kpi, .stage-body .ov-kpi')).forEach(function (card) {
      var kn = card.querySelector('.kn'); if (!kn) return;
      var kj = card.querySelector('.jsrc[data-kpi]'), tk = kn.querySelector('[data-term]');
      if (kj && conceptsFor('kpi:' + kj.getAttribute('data-kpi')).length) card.setAttribute('data-anchor', 'kpi:' + kj.getAttribute('data-kpi'));
      else if (tk && !card.getAttribute('data-anchor')) card.setAttribute('data-anchor', 'term:' + tk.getAttribute('data-term'));
      var key = kpiKey(kn); if (key) card.setAttribute('data-plain', key);
      var an = card.getAttribute('data-anchor'), js = card.querySelector('.jsrc');
      if (an && js && !js.querySelector('.cn-mg')) js.insertAdjacentHTML('beforeend', cnBtn(an, 'graph'));
    });
  }
  function kpiPlainFor(t) {
    var card = t && t.closest ? t.closest('[data-plain]') : null;
    var key = card && card.getAttribute('data-plain');
    return key && KPI_PLAIN[key] ? '<div class="kp">' + esc(KPI_PLAIN[key]) + '</div>' : '';
  }
  /* СТАТИСТИЧЕСКИЙ СЛОЙ (владелец 08.09: «статистический анализ нами, где возможно: кластеризация,
     регрессии, Байес — с пояснением, что за метод; порождаем собственные KPI»). Данные —
     data/enso/stats.json (tools/enso/stats_layer.py, офлайн, без модели). Единица знает свою
     сцену; на сцене с выбором ряда (Dynamics, Long record) показываем единицы того ряда, что на
     экране, плюс общие. Кнопка stats ▾ рядом с source и notes. */
  var STATS_DEFAULT_SUB = { now: 'analogs', trend: 'sst_nino34', planet: 'gases', ocean: 'surface', models: 'plume', food: 'prices', radiance: 'convection', refs: 'works' };
  function statsFor(view) {
    var items = (S.ST || {}).items || []; if (!items.length) return [];
    var sub = S.sub[view] || STATS_DEFAULT_SUB[view] || '', scene = view + (sub ? '/' + sub : '');
    var out = items.filter(function (it) { return it.scene === scene || it.scene === view || (it.also || []).indexOf(scene) >= 0 || (it.also || []).indexOf(view) >= 0; });
    if (view === 'planet') { if (sub !== 'temperature') return []; var pick = S.sub.planetTemp || 't2_world'; out = out.filter(function (it) { return !it.series || typeof it.series !== 'string' || it.series === pick || it.kind === 'coherence'; }); }
    if (view === 'trend' && sub && sub !== 'spectral') out = out.filter(function (it) { return it.scene === scene || it.kind === 'coherence'; });
    return out;
  }
  function statsHtml(items, mode) {
    var sw = '<div class="seg sub" style="margin-bottom:6px">' + [['plain', 'in plain words'], ['tech', 'technical']].map(function (o) { return '<button type="button" class="sq' + (mode === o[0] ? ' on' : '') + '" data-notemode="' + o[0] + '">' + o[1] + '</button>'; }).join('') + '<span class="st-note">our own statistics on this scene · ' + esc(String((S.ST || {}).built || '').slice(0, 16)) + '</span></div>';
    return sw + items.map(function (it) {
      var m = it.method || {};
      return '<div class="st-item"><div class="st-t">' + esc(it.title) + '</div>' +
        '<div class="kpis st-kpis">' + (it.kpis || []).map(function (k) { return '<div class="kpi"><div class="kn">' + esc(k.name) + '</div><div class="kv">' + esc(String(k.value)) + (k.unit ? '<small> ' + esc(k.unit) + '</small>' : '') + '</div><div class="km">' + esc(k.plain || '') + '</div></div>'; }).join('') + '</div>' +
        '<div class="st-m"><b>' + esc(m.name || 'Method') + '.</b> ' + esc(mode === 'plain' ? (m.plain || '') : (m.tech || '')) +
        (mode === 'tech' && (m.caveats || []).length ? '<ul class="st-cav">' + m.caveats.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul>' : '') +
        (it.window && it.window[0] ? '<span class="st-w">window ' + esc(it.window[0]) + (it.window[1] ? ' … ' + esc(it.window[1]) : '') + '</span>' : '') + '</div>' +
        conceptsHtml(it.anchors || [], false) + '</div>';
    }).join('');
  }
  function sceneInfoBar() {
    var view = S.view === 'gulf' ? 'regions' : (S.view === 'risk' ? 'now' : S.view), info = SCENE_INFO[view];
    var head = document.querySelector('.stage-head'), body = document.querySelector('.stage-body');
    if (!info || !head || !body || body.getAttribute('data-own-info') || body.querySelector('button[data-info]')) return;
    var seg = head.querySelector('.ctl-info'); if (!seg) { seg = el('div', 'seg ctl-info'); head.appendChild(seg); }
    // подписи сцены уходят в технический разбор
    var caps = [].slice.call(body.querySelectorAll('.cap')).map(function (c) { c.hidden = true; return c.innerHTML; }).filter(Boolean);
    var open = S.sub.info, mode = S.sub.noteMode || 'plain';
    var stItems = statsFor(view);
    if (open === 'stats' && !stItems.length) open = null;
    [['source', 'source'], ['notes', 'notes']].concat(stItems.length ? [['stats', 'stats · ' + stItems.length]] : []).forEach(function (o) {
      var b = el('button', (open === o[0] ? 'on' : '') + ' sq' + (o[0] === 'stats' ? ' stats' : ''), o[1] + (open === o[0] ? ' ▴' : ' ▾')); b.type = 'button'; b.setAttribute('data-info', o[0]);
      if (o[0] === 'stats') b.setAttribute('data-src', esc(JSON.stringify({ name: 'Our statistics on this scene', def: 'Regression, change-points, persistence, clusters, extremes, correlations — computed by us from the same series the chart shows, with the method explained in plain words and technically.' })));
      b.onclick = function () { S.sub.info = S.sub.info === o[0] ? null : o[0]; render(); };
      seg.appendChild(b);
    });
    if (!open) return;
    var pane = el('div', 'info-pane');
    if (open === 'source') pane.innerHTML = '<b>Source.</b> ' + esc(info.source);
    else if (open === 'stats') {
      pane.classList.add('stats');
      pane.innerHTML = statsHtml(stItems, mode);
      pane.addEventListener('click', function (e) { var b = e.target.closest('[data-notemode]'); if (b) { S.sub.noteMode = b.getAttribute('data-notemode'); render(); } });
      body.insertBefore(pane, body.firstChild);
      return;
    } else {
      var sw = '<div class="seg sub" style="margin-bottom:6px">' + [['plain', 'in plain words'], ['tech', 'technical']].map(function (o) { return '<button type="button" class="sq' + (mode === o[0] ? ' on' : '') + '" data-notemode="' + o[0] + '">' + o[1] + '</button>'; }).join('') + '</div>';
      pane.innerHTML = sw + (mode === 'plain' ? '<div>' + esc(info.plain) + '</div>' : '<div>' + esc(info.tech) + '</div>' + caps.map(function (c) { return '<div class="cap" style="margin-top:6px">' + c + '</div>'; }).join(''));
      pane.addEventListener('click', function (e) { var b = e.target.closest('[data-notemode]'); if (b) { S.sub.noteMode = b.getAttribute('data-notemode'); render(); } });
    }
    pane.innerHTML += conceptsHtml(sceneAnchors(), true);
    body.insertBefore(pane, body.firstChild);
  }

  /* ЛЕНТА УПОМИНАНИЙ (владелец 07.09): разговор о событии, не измерение. Данные mentions.json. */
  function chartDaysPanels(items, W, H) {
    if (!items.length) return svgOpen(W, H) + '<text x="20" y="40">no series</text></svg>';
    var RC = S._tight ? 8 : 60, gap = 16, hh = (H - 18 - gap * (items.length - 1)) / items.length;
    var s = svgOpen(W, H) + hatchDefs();
    items.forEach(function (o, xi) {
      var top = 6 + xi * (hh + gap), Lp = 46, Tp = top + 14, pw = W - Lp - RC - 10, ph = hh - 26, n = o.dates.length;
      var vv = []; (o.series || []).forEach(function (q) { vv = vv.concat(q.values.filter(fin)); });
      if (!vv.length) return;
      var vmax = Math.max.apply(null, vv) * 1.1, vmin = 0;
      var X = function (i) { return Lp + (n > 1 ? i / (n - 1) : 0) * pw; }, Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
      s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw.toFixed(1) + '" height="' + ph.toFixed(1) + '" rx="5" style="fill:var(--ink)" opacity=".03"/>';
      s += '<text class="tt" x="' + Lp + '" y="' + (top + 9) + '" font-size="10">' + fitText(o.title, W - RC, 10) + '</text>';
      s += gridY(vmin, vmax, niceStep(vmax - vmin), Y, Lp, RC + 10, W, 0);
      o.dates.forEach(function (d, i) { if (d.slice(8) === '01' || i === 0 || i === n - 1) s += '<text x="' + X(i).toFixed(0) + '" y="' + (Tp + ph + 11) + '" text-anchor="' + (i === 0 ? 'start' : (i === n - 1 ? 'end' : 'middle')) + '" font-size="9">' + esc(d.slice(5)) + '</text>'; });
      (o.series || []).forEach(function (q, k) {
        if (q.bars) {
          var bw = Math.max(2, pw / n - 2);
          q.values.forEach(function (v, i) { if (fin(v)) s += '<rect x="' + (X(i) - bw / 2).toFixed(1) + '" y="' + Y(v).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + (Y(0) - Y(v)).toFixed(1) + '" style="fill:' + (q.color || 'var(--nino)') + '" opacity=".75"/>'; });
        } else {
          s += segs(q.values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), q.color || 'var(--text)', q.w || 1.4, pickOp(q.key || q.name, 1), q.dash || '');
        }
      });
      var legs = (o.series || []).map(function (q, k) { return [q.name, q.color || 'var(--text)', q.w || 1.4, q.dash || '', q.key || q.name]; });
      if (legs.length > 1 && !S._tight) s += legendAt(legs, W - RC - 150, Tp + 12);   // под кнопкой legend, а не слева
    });
    return s + '</svg>';
  }

  function viewMentions() {
    var M = S.MN || {}, k = sub('mentions', 'attention');
    var arts = M.articles || [], langs = M.languages || [];
    var body = stageShell('Who is talking about El Niño: ' + arts.length + ' articles in ' + langs.filter(function (l) { return l.n; }).length + ' languages',
      [segBtn('mentions', 'attention', 'Attention', 'attention'), segBtn('mentions', 'articles', 'Headlines (' + arts.length + ')', 'attention'), segBtn('mentions', 'official', 'Forecast centres', 'attention')]);
    if (!M.built) { body.appendChild(el('div', 'note', 'No mentions data yet: run python tools/enso/mentions.py.')); return; }
    body.classList.add('scroll');
    if (k === 'attention') {
      var items = [];
      var pd = M.per_day || {};
      if ((pd.dates || []).length) items.push({ title: 'Articles per day in the nine news feeds (latest hundred per language, so older days are undercounted)', dates: pd.dates, series: [{ name: 'articles', values: pd.counts, bars: true, color: 'var(--ochre)' }] });
      var wk = M.wiki || {}, wl = Object.keys(wk);
      if (wl.length) {
        var base = wk.en || wk[wl[0]];
        items.push({ title: 'Wikipedia article views per day, ' + wl.length + ' languages', dates: base.dates, series: wl.map(function (l, i) { return { name: l, values: wk[l].views, color: l === 'en' ? 'var(--text)' : (l === 'es' ? 'var(--nino)' : (l === 'ar' ? 'var(--ochre)' : 'var(--soft)')), w: l === 'en' ? 1.8 : 1, dash: dashOf(i), key: 'w' + l }; }) });
      }
      if (M.gdelt && (M.gdelt.values || []).length) items.push({ title: 'GDELT: share of all monitored world news mentioning El Niño, %', dates: M.gdelt.dates, series: [{ name: '% of news', values: M.gdelt.values, color: 'var(--nina)' }] });
      plot(body, function (w, h) { return chartDaysPanels(items, w, h); });
      var kp = el('div', 'kpis');
      kp.innerHTML = '<div class="kpi"><div class="kn">languages</div><div class="kv" style="font-size:12px;line-height:1.5">' + langs.map(function (l) { return (l.url ? '<a href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.name) + '</a>' : esc(l.name)) + ' ' + l.n; }).join(' · ') + '</div><div class="km">articles now in each feed</div>' + kmeta(null, 'Google News RSS', (M.built || '').slice(0, 10)) + '</div>' +
        '<div class="kpi"><div class="kn">who publishes most</div><div class="kv" style="font-size:12px;line-height:1.5">' + (M.top_sources || []).slice(0, 8).map(function (t) { return (t.url ? '<a href="' + esc(t.url) + '" target="_blank" rel="noopener">' + esc(t.source) + '</a>' : esc(t.source)) + ' ' + t.n; }).join(' · ') + '</div><div class="km">across all feeds, duplicates removed</div>' + kmeta(null, 'Google News, Bing News', (M.built || '').slice(0, 10)) + '</div>' +
        (wk.en ? '<div class="kpi"><div class="kn">Wikipedia, English</div><div class="kv">' + wk.en.last7_per_day + '<small> views a day</small></div><div class="km">this week, against ' + wk.en.base_per_day + ' a day before</div>' + kmeta(null, 'Wikimedia pageviews', (M.built || '').slice(0, 10)) + '</div>' : '');
      body.appendChild(kp);
      body.appendChild(el('div', 'cap', esc(M.summary || '') + ' ' + esc(M.note || '')));
    } else if (k === 'articles') {
      var lf = S.sub.mentLang || 'all';
      var row = el('div', 'seg sub');
      [['all', 'all']].concat(langs.filter(function (l) { return l.n; }).map(function (l) { return [l.lang, l.name]; })).forEach(function (o) { var b = el('button', lf === o[0] ? 'on' : '', o[1]); b.type = 'button'; b.onclick = function () { S.sub.mentLang = o[0]; render(); }; row.appendChild(b); });
      body.appendChild(row);
      var list = arts.filter(function (a) { return lf === 'all' || a.lang === lf; }).slice(0, 120);
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap.innerHTML = '<table class="e"><thead><tr><th>date</th><th>language</th><th>source</th><th>headline</th></tr></thead><tbody>' +
        list.map(function (a) { return '<tr><td style="white-space:nowrap">' + dt(a.date || '') + '</td><td>' + esc(a.lang) + '</td><td>' + esc(a.source || '') + '</td><td class="act"><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.title) + '</a></td></tr>'; }).join('') + '</tbody></table>';
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Headlines as written by the publishers, newest first, duplicates removed; a link goes to the publisher through Google News or Bing News. Not our words and not a source of numbers.'));
    } else {
      var g = el('div', 'gloss'), off = M.official || {};
      var withE = Object.keys(off).filter(function (key) { return (off[key].items || []).length; }), without = Object.keys(off).filter(function (key) { return !(off[key].items || []).length; });
      g.innerHTML = withE.map(function (key) { var o = off[key]; return '<div class="gl-i"><b>' + esc(o.label) + '</b> <span class="s">' + o.items.length + ' of the latest ' + (o.n_all || o.items.length) + ' posts mention El Niño</span><ul>' + o.items.map(function (x) { return '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.title) + '</a> <span class="s">' + esc(x.date || '') + '</span></li>'; }).join('') + '</ul></div>'; }).join('') +
        (without.length ? '<div class="gl-i"><b>Nothing about El Niño in the latest posts</b><ul>' + without.map(function (key) { var o = off[key]; return '<li><a href="' + esc(o.url || '#') + '" target="_blank" rel="noopener">' + esc(o.label) + '</a> <span class="s">' + (o.n_all || 0) + ' posts checked</span></li>'; }).join('') + '</ul></div>' : '') || '<div class="note">No official feed answered.</div>';
      body.appendChild(g);
      body.appendChild(el('div', 'cap', 'Agencies and forecast centres with an open feed, only the posts that mention El Niño or ENSO; feeds with nothing on the subject are listed at the end so the silence is visible too. NOAA CPC publishes its ENSO discussion on the second Thursday of the month and BoM its wrap-up fortnightly; neither has a feed we can read, see ' + vLink('the release calendar', 'how', 'calendar') + '.'));
    }
  }

  /* ВКЛАДКА OPS (владелец 06.09): журнал прогонов, состояние источников, свежий слой с триггерами.
     Всё из data/enso/ops.json и fresh.json, которые пишутся в конце каждого прогона, не живьём. */
  function viewOps() {
    var D = S.D || {}, O = S.O || {}, F = S.F || {};
    var k = sub('ops', 'runs');
    /* источники раздела истории измерений (planet.json) — той же таблицей, своей группой */
    var plS = (((S.PL || {}).sources) || []).map(function (q) { return { key: q.key, label: q.label, group: 'long record', cadence: 'daily wrapper, slow series', url: q.page || q.url, data_from: q.data_from, data_to: q.data_to, behind_days: null, fetched: q.fetched, fresh: q.fresh, error: q.error }; });
    var runs = O.runs || [], srcs = (O.sources || []).concat(plS);
    var body = stageShell('Runs and sources: ' + runs.length + ' runs on record, ' + srcs.length + ' sources, ' + ((O.stale || []).length + plS.filter(function (q) { return q.fresh === false; }).length) + ' stale',
      [segBtn('ops', 'runs', 'Runs (' + runs.length + ')', 'runs'), segBtn('ops', 'sources', 'Sources (' + srcs.length + ')', 'runs'), segBtn('ops', 'fresh', 'Fresh layer', 'runs')]);
    body.classList.add('scroll');
    if (k === 'runs') {
      var rows = runs.slice().reverse();
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap.innerHTML = '<table class="e"><thead><tr><th>started</th><th>kind</th><th class="num">seconds</th><th>status</th><th>data stamp</th><th class="num">index</th><th class="num">risks</th><th class="num">alerts</th><th>outcome, errors</th></tr></thead><tbody>' +
        rows.map(function (r) {
          var bad = r.status && r.status !== 'ok' && r.status !== 'cleared';
          var errs = (r.errors || []).concat(r.errors_list || []).concat(r.model_error ? ['model: ' + r.model_error] : []);
          var note = [r.note, r.stale && r.stale.length ? 'stale: ' + r.stale.join(', ') : '',
            r.triggers != null ? r.triggers + ' trigger' + (r.triggers === 1 ? '' : 's') + (r.needs_assessment ? ', assessment needed' : '') : '',
            r.findings != null ? r.findings + ' findings, ' + r.edits + ' wordings fixed' : '',
            r.files != null ? r.files + ' files' + (r.reviewed != null ? (r.reviewed ? ', reviewed' : ', NOT reviewed') : '') : '',
            r.anchors != null ? r.anchors + ' of ' + r.of + ' anchors, ' + r.links + ' links' : '',
            r.stations != null ? r.stations + ' moorings' : '', r.model ? r.model : ''].filter(Boolean).join(' · ');
          return '<tr><td>' + esc(r.started || '') + '</td><td>' + esc(r.label || r.kind || '') + '</td><td class="num">' + (fin(r.secs) ? r.secs : '') + '</td>' +
            '<td class="' + (bad ? 'st-bad' : 'st-ok') + '">' + esc(r.status || '') + '</td><td>' + esc(r.stamp || '') + '</td>' +
            '<td class="num">' + (r.risk_index != null ? r.risk_index : '') + '</td><td class="num">' + (r.n_risks != null ? r.n_risks : '') + '</td>' +
            '<td class="num">' + (r.n_alerts != null ? r.n_alerts : '') + (r.shout ? ' <b>SHOUT</b>' : '') + '</td>' +
            '<td class="act">' + esc(note) + (errs.length ? '<div class="sub st-bad">' + esc(errs.join('; ')) + '</div>' : '') + '</td></tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Every run writes one line when it finishes: full updates (rules, model verdict, snapshot), light runs (rules only, the fresh layer), links to our works, mooring records, publishing, review marks. Not live: a run in progress appears only when it ends. Journal data/enso/runs.json, last ' + runs.length + ' shown, written ' + esc(O.runs_built || O.built || '') + '.'));
    } else if (k === 'sources') {
      var wrap2 = el('div'); wrap2.style.cssText = 'flex:1;min-height:0;overflow:auto';
      wrap2.innerHTML = '<table class="e"><thead><tr><th>source</th><th>cadence</th><th>data from</th><th>to</th><th class="num">behind</th><th>last update</th><th>status</th></tr></thead><tbody>' +
        srcs.map(function (s) {
          return '<tr><td>' + (s.url ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.label) + '</a>' : esc(s.label)) + '<div class="sub">' + esc(s.key) + (s.group === 'modules' ? ' · module, fetched inside the run' : (s.group === 'long record' ? ' · long record (planet.py)' : '')) + '</div></td>' +
            '<td>' + esc(s.cadence || '') + '</td><td>' + esc(s.data_from || '') + '</td><td>' + esc(s.data_to || '') + '</td>' +
            '<td class="num">' + (s.behind_days != null ? s.behind_days + ' d' : '') + '</td><td>' + esc(s.fetched || '') + '</td>' +
            '<td class="' + (s.fresh ? 'st-ok' : 'st-bad') + '">' + (s.fresh ? 'answered' : 'stale, last good copy') + (s.error ? '<div class="sub">' + esc(s.error) + '</div>' : '') + '</td></tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(wrap2);
      body.appendChild(el('div', 'cap', esc(O.note || '') + ' Assessed state ' + esc(O.assessed_stamp || '') + ', written ' + esc(O.built || '') + '. ' + vLink('the chain of data', 'chain') + ' ' + vLink('the release calendar', 'how', 'calendar')));
    } else {
      var g = el('div', 'gloss'), tr = F.triggers || [];
      g.innerHTML = '<div class="gl-i"><b>' + (F.stamp ? 'Light run ' + esc(F.stamp) + ' against the assessment ' + esc(F.assessed_stamp || '') : 'No fresh layer yet') + '</b>' + esc(F.summary || '') +
        (F.assessed_stamp && D.stamp && F.assessed_stamp !== D.stamp ? '<div class="s" style="color:var(--nino)">This fresh layer was computed against a different assessment (' + esc(F.assessed_stamp) + '): run python refresh.py --light again.</div>' : '') + '</div>' +
        '<div class="gl-i"><b>Triggers' + (tr.length ? ' (' + tr.length + ')' : '') + '</b>' + (tr.length ? '<ul>' + tr.map(function (t) { return '<li><span class="' + (t.severity === 'high' ? 'st-bad' : '') + '">' + esc(t.severity) + '</span> · ' + esc(t.text) + '</li>'; }).join('') + '</ul>' : 'None crossed: the assessed state stands.') +
        '<div class="s">Rules: a new SHOUT or alert, a changed alert or risk level, the risk index moving by 3 points or more, a daily Niño 3.4 value outside the assessed 14-day band, a new weekly or monthly release. Thresholds at the top of tools/enso/fresh.py.</div></div>' +
        Object.keys(F.series || {}).map(function (key) {
          var s = F.series[key] || {};
          return '<div class="gl-i"><b>' + esc(s.label || key) + '</b>assessed to ' + esc(s.assessed_last_date || '') + ' (' + fnum(s.assessed_last_value) + ' ' + (s.unit || '°C') + '), fresh to ' + esc(s.last_date || '') + ' (' + fnum(s.last_value) + ' ' + (s.unit || '°C') + ')' +
            ((s.tail || []).length ? '<div class="s">new days: ' + s.tail.map(function (p) { return esc(p[0]) + ' ' + fnum(p[1]); }).join(' · ') + '</div>' : '<div class="s">no new days</div>') + '</div>';
        }).join('') +
        '<div class="gl-i"><b>Rules on the fresh data</b>risk index ' + (F.risk_index != null ? F.risk_index : '—') + ' (assessed ' + (F.assessed_risk_index != null ? F.assessed_risk_index : '—') + ') · alerts: ' + ((F.alerts || []).map(function (a) { return a.level + ' ' + a.title; }).join('; ') || 'none') + '</div>';
      body.appendChild(g);
      body.appendChild(el('div', 'cap', esc(F.note || "The fresh layer is written by a light run (python refresh.py --light): the same rules on today's data, no model, no snapshot, the verdict untouched.")));
    }
  }

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
    var cng = conceptsHtml('region:' + r.id, true);
    if (cng) body.appendChild(el('div', 'note cn-box', cng));
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
      /* БОКС РЕГИОНА (владелец 07.09: «подключи к регионам»): дневной ряд воздуха по боксу ERA5,
         тем же кирпичом, что Niño 3.4, если у региона есть свой бокс в regions-daily.json. */
      var LB = landOfRegion(rid);
      if (LB) {
        plot(body, function (w, h) { return chartRecent(LB, w, h); });
        var kl = el('div', 'kpis');
        kl.innerHTML = '<div class="kpi"><div class="kn">air over the region, last day</div><div class="kv">' + fnum(LB.last_value) + '<small> °C</small></div><div class="km">' + span(LB.last_date, 30) + ' ' + fnum(LB.level30.anom) + ', rank ' + LB.level30.rank_raw + ' of ' + LB.level30.of + '</div>' + kmeta(null, 'ERA5 box mean via Open-Meteo', LB.last_date) + '</div>' +
          '<div class="kpi"><div class="kn">forecast +14 days</div><div class="kv">' + fnum(LB.forecast14.p50) + '</div><div class="km">p10 … p90: ' + fnum(LB.forecast14.p10) + ' … ' + fnum(LB.forecast14.p90) + '</div>' + kmeta(null, 'analogues of past days', LB.last_date) + '</div>' +
          '<div class="kpi"><div class="kn">record days</div><div class="kv" style="font-size:17px">' + LB.records.last30 + '<small> of 30</small></div><div class="km">warmest of that calendar day since 1981; streak ' + LB.records.streak + '</div>' + kmeta(null, 'ERA5 box mean', LB.last_date) + '</div>';
        var PRr = ((S.PR || {}).regions || {})[landKeyOfRegion(rid)];
        if (PRr) {
          var kr2 = el('div', 'kpis'), a2 = PRr.sum30, b2 = PRr.sum90;
          kr2.innerHTML = '<div class="kpi"><div class="kn">rain, last 30 days</div><div class="kv">' + fnum(a2.now, 0, false) + '<small> mm · ' + a2.pct_of_normal + ' % of normal</small></div><div class="km">wetter than ' + a2.rank_pct + ' % of years since 1981; 90 days at ' + b2.pct_of_normal + ' % of normal</div>' + kmeta(null, 'ERA5 box sum via Open-Meteo', PRr.last_date) + '</div>' +
            '<div class="kpi"><div class="kn">same 30 days in our years</div><div class="kv" style="font-size:14px">' + Object.keys(a2.analogs).sort().map(function (y) { return y + ': ' + fnum(a2.analogs[y], 0, false); }).join(' · ') + '</div><div class="km">mm; ' + vLink('monthly bars and the planet', 'trend', 'rain') + '</div>' + kmeta(null, 'ERA5 box sum', PRr.last_date) + '</div>';
          body.appendChild(kr2);
        }
        body.appendChild(kl);
        body.appendChild(el('div', 'cap', 'Box ' + esc(boxLabel(LB.box)) + ', 2 m air, ERA5 box mean; the same series with all its numbers is on ' + vLink('Dynamics', 'trend', landKeyOfRegion(rid)) + '. Below it, the reference: typical impacts by season, food exposure and the sources.'));
      } else body.appendChild(el('div', 'note', 'No local measurements for this region yet — below is the reference: typical impacts by season, food exposure and the sources. The Gulf is the first region with measured series (sea, weather, imports); others follow as sources are found.'));
    }
    regionCard(body, r, RG);
  }

  // ---------------------------------------------------------------- render
  /* АДРЕС СЦЕНЫ. Ссылка вида enso.html#ocean/moorings открывает нужную вкладку и подвкладку:
     так вкладку можно послать письмом, а панель — снять снимком без кликов. Адрес
     обновляется при каждой перерисовке и никогда не перезагружает страницу. */
  function readHash() {
    if (/[?&]globe=1(?:&|$)/.test(location.search)) S.globe = true;   // ссылка сразу на шар (пилот 08.09)
    var h = (location.hash || '').replace(/^#/, '');
    if (!h) return;
    var parts = h.split('/');
    if (parts[0] === 'gulf') {                   // старый адрес вкладки Kuwait · Gulf
      S.view = 'regions'; S.sub.regions = 'place'; S.region = 'gulf_arabia';
      if (parts[1]) S.sub.gulf = parts[1];
      return;
    }
    if (parts[0] === 'risk' && parts[1] && S.D) {          // #risk/<id> — сцена риска по имени правила (08.09)
      var ri = -1; (S.D.risks || []).forEach(function (r, i) { if (ri < 0 && r.id === parts[1]) ri = i; });
      if (ri >= 0) { S.view = 'risk'; S.risk = ri; return; }
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
    if (location.hash === h) { S._hashInit = 1; return; }   // адрес уже верный — но первая запись уже сделана
    /* СМЕНА ВИДА — ЗАПИСЬ В ИСТОРИИ. Раньше адрес переписывался на месте (replaceState), и
       кнопка «назад» уводила со страницы целиком: ушёл с обзора в раздел — вернуться нечем
       (владелец 06.09). Меняем страницей истории: браузерная «назад» возвращает на обзор.
       Первую запись при загрузке по-прежнему только правим, чтобы не плодить пустой шаг. */
    try {
      if (S._hashInit) { history.pushState(null, '', h); S._navN = (S._navN || 0) + 1; }
      else { history.replaceState(null, '', h); S._hashInit = 1; }
    } catch (e) { /* file: без истории */ }
  }
  function render() {
    animStop();
    writeHash();
    /* ВЫБОР В ЛЕГЕНДЕ ЖИВЁТ ТОЛЬКО НА СВОЕЙ СЦЕНЕ. Владелец 05.09: «походил, вернулся на
       Against analogues — всё блёклое, не могу вернуть яркость». Уход со сцены снимает выбор. */
    var scene = S.view + '/' + (S.sub[S.view] || '');
    if (S._scene !== scene) { S.pick = (scene === 'models/plume' || scene === 'models/stack') ? 'ok' : null; S._scene = scene; }
    if (S.view === 'overview' && S.full == null) S.full = true;   // обзор открывается сразу на весь экран
    var mapScene = S.view === 'now' && (S.sub.now || 'analogs') === 'map';
    if (S._fullView !== S.view) { if (S.view !== 'overview') S.full = null; S._fullView = S.view; }   // смена сцены снимает полный экран
    $('stage').classList.toggle('full', !!S.full);
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
    applyRailFull();
    L.classList.toggle('show', narrow && S.view === 'state');
    R.classList.toggle('show', narrow && (S.view === 'risks' || S.view === 'risk'));
    stage.classList.toggle('hide', narrow && (S.view === 'state' || S.view === 'risks'));
    if (narrow && (S.view === 'state' || S.view === 'risks')) { S.draw = null; S.plotEl = null; return; }
    if (S.view === 'risk') viewRisk();
    else if (S.view === 'verdict') viewVerdict();
    else if (S.view === 'models') viewModels();
    else if (S.view === 'air') viewAir();
    else if (S.view === 'ocean') viewOcean();
    else if (S.view === 'radiance') viewRadiance();
    else if (S.view === 'regions' || S.view === 'gulf') viewRegions();
    else if (S.view === 'chain') viewChain();
    else if (S.view === 'news') viewNews();
    else if (S.view === 'overview') viewOverview();
    else if (S.view === 'refs') viewRefs();
    else if (S.view === 'planet') viewPlanet();
    else if (S.view === 'mentions') viewMentions();
    else if (S.view === 'ops') viewOps();
    else if (S.view === 'about') viewAbout();
    else if (S.view === 'trend') viewTrend();
    else if (S.view === 'food') viewFood();
    else if (S.view === 'how') viewHow();
    else if (S.view === 'research') viewResearch();
    else viewNow();
    sceneInfoBar();                          // source / notes на каждой сцене (08.09)
    kpiExplain();                            // «?» на плашках KPI (08.09)
    if (S.globe && globeMode()) mountGlobe(globeMode());
    // Сцена собрана целиком — только теперь у рамки графика окончательная высота.
    redrawPlot();
    requestAnimationFrame(redrawPlot);
  }
  window.B42EnsoRedraw = function () { redrawPlot(); };
  window.B42EnsoState = S;                 // наружу — только для отладки из консоли
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
    function tipAnchors(p) {
      if (p.lk) return [p.lk];
      var t = S.tipAnchor, card = t && t.closest ? t.closest('[data-anchor]') : null;
      if (card) return [card.getAttribute('data-anchor')];
      return t && t.closest && t.closest('#stage') ? sceneAnchors() : [];
    }
    function fill(p) {
      return '<b>' + esc(p.name || '') + '</b>' + (p.html ? p.html : esc(p.def || '')) + (p.why ? ' ' + esc(p.why) : '') +
        (p.url ? ' <a href="' + esc(p.url) + '" target="_blank" rel="noopener">source ↗</a>' : '') +
        (p.lk && linksFor(p.lk).length ? ' <button type="button" class="jh tip-lk" data-lk="' + esc(p.lk) + '">' + linksFor(p.lk).length + ' work' + (linksFor(p.lk).length > 1 ? 's' : '') + ' →</button>' : '') +
        (p.src || p.date ? '<span class="s">' + srcHtml(p.src) + (p.date ? '<div>' + esc(p.date) + '</div>' : '') + '</span>' : '') +
        kpiPlainFor(S.tipAnchor) +      // плашка: объяснение простыми словами в подсказке (владелец 08.09: «в окошке тултипа достаточно»)
        conceptsHtml(tipAnchors(p), false, true);   // понятия колонкой под источником (08.09)
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
    var showT = null, showX = null;
    document.addEventListener('mouseover', function (e) {
      if (overTip) return;
      var x = find(e);
      if (!x || x === S.pinned) return;
      /* НЕ МГНОВЕННО. Владелец 08.09: «любое перемещение мышки, даже случайное, вызывает
         подсказку». Ждём 260 мс на самом слове; ушёл раньше — ничего не всплывает. Если
         карточка уже открыта, содержимое меняется сразу — так переход между словами плавный. */
      clearTimeout(showT); showX = x;
      var ex = { clientX: e.clientX, clientY: e.clientY };
      function open() {
        show(x, ex);
        if (S.pinned) { S.pinned = x; return; }        // уже приколота — просто меняем содержимое
        clearTimeout(pinT);
        if (x.closest('#pmeta')) return;              // шапка: только пока курсор на слове, без прикалывания
        pinT = setTimeout(function () {
          if (tip.classList.contains('on')) { S.pinned = x; tip.classList.add('pin'); }
        }, 600);
      }
      // задержка всегда, и для смены слова при открытой карточке тоже: иначе после первой карточки следующие мигали мгновенно (владелец 08.09)
      showT = setTimeout(function () { if (showX === x && x.isConnected) open(); }, 380);
    });
    document.addEventListener('mouseout', function (e) {
      var f = find(e);
      if (!f) return;
      if (f === showX) { clearTimeout(showT); showX = null; }   // ушли раньше задержки — не показываем
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
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { S.pinned = null; hide(); if (S.full || S.railFull) { S.full = false; S.railFull = null; render(); } } });
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
    get('/data/enso/news.json').catch(function () { return {}; }),
    get('/data/enso/fresh.json').catch(function () { return {}; }),
    get('/data/enso/ops.json').catch(function () { return {}; }),
    get('/data/enso/planet.json').catch(function () { return {}; }),
    get('/data/enso/hovmoller.json').catch(function () { return {}; }),
    get('/data/enso/mentions.json').catch(function () { return {}; }),
    get('/data/enso/spectral.json').catch(function () { return {}; }),
    get('/data/enso/regions-daily.json').catch(function () { return {}; }),
    get('/data/enso/precip.json').catch(function () { return {}; }),
    get('/data/enso/radiance.json').catch(function () { return {}; }),
    get('/data/enso/neighbours.json').catch(function () { return {}; }),
    get('/data/enso/concepts.json').catch(function () { return {}; }),
    get('/data/enso/stats.json').catch(function () { return {}; })])
    .then(function (r) {
      S.D = r[0]; S.G = (r[1] && r[1].en) || {}; S.H = r[2] || []; S.P = r[0].prev || null;
      S.M = r[3] || {}; S.L = r[4] || {}; S.J = r[5] || {}; S.C = r[6] || {}; S.N = r[7] || {}; S.F = r[8] || {}; S.O = r[9] || {}; S.PL = r[10] || {}; S.HV = r[11] || {}; S.MN = r[12] || {}; S.SP = r[13] || {}; S.RD = r[14] || {}; S.PR = r[15] || {}; S.RA = r[16] || {}; S.NB = r[17] || {}; S.CN = r[18] || {}; S.ST = r[19] || {};
      var db = $('deltaBtn');
      if (db) db.onclick = function () {
        S.delta = S.delta === '' ? 'update' : (S.delta === 'update' ? 'week' : '');
        render();
      };
      readHash();
      buildMeta(); buildStrip(); initDock(); render();
      window.addEventListener('hashchange', function () { S._navN = (S._navN || 0) + 1; readHash(); render(); });   // адрес сменил браузер: шаг в истории уже есть
      var ro = new ResizeObserver(function () { redrawPlot(); });
      ro.observe($('stage'));
      var t = null;
      window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(render, 150); });
    })
    .catch(function (e) { $('stage').innerHTML = '<div class="e-empty">The data did not load: ' + esc(e.message) + '</div>'; });
})();
