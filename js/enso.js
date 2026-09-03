/* Дашборд «El Niño 2026–2027»: одна страница, всё содержимое из data/enso/*.json.
   Почему рендер в браузере, а не HTML с сервера: сайт динамический, обновление — это
   новый latest.json в R2, а страница не пересобирается (владелец 01.09: «никаких
   пересборок»). Графики — inline SVG, собираются здесь же; никаких библиотек и внешних
   запросов: только свои три JSON с того же домена.

   Порядок блоков A–H — из ТЗ (docs/ТЗ.md в enso_onepage): вывод → доказательство → метод.
   Язык страницы — английский (владелец 03.09: «текст дашборда всё на английском»);
   тексты генератора (риски, тревоги, саммари) тоже приходят по-английски. */
(function () {
  'use strict';
  var root = document.getElementById('root');

  var t = {
    title: 'El Niño 2026–2027', riskOf: 'risk index<br>out of 100',
    built: 'built', stamp: 'stamp', daily: 'daily series until', weekly: 'NOAA week',
    fresh: 'fresh', stale: 'stale',
    refreshNote: 'The page is recomputed from the sources; updates are semi-automatic, under supervision. The next IRI model issue is due around the 19th.',
    shoutOn: 'ALERT: something happened that was never in the data', shoutAttn: 'Watchdog: shifts that need attention',
    quiet: 'The watchdog sees no turning point', quietD: 'No rule fired: no record broken, no reversal, no run of records ended.',
    A: 'Scale', B: 'Verdict', C: 'Where we are', D: 'Risks', E: 'Models', F: 'Regions and food', G: 'Dynamics', H: 'How it is computed',
    aiBy: 'model summary', aiRules: 'rule-based digest', aiNoModel: 'the model did not take part', whatIs: 'what this is',
    turning: 'Turning point', changed: 'What changed', outlook: '2–3 weeks', watch: 'What to watch', conf: 'Confidence', cav: 'Caveats',
    yes: 'yes', no: 'no',
    now: 'now', perDay: 'last day', perWeek: 'last week', perIssue: 'last issue', seven: 'seven', trend: 'course',
    rising: 'rising', falling: 'falling', flat: 'holding',
    lookAt: 'Watch', months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    dyn: 'dyn.', stat: 'stat.', okC: 'keeping up', lagC: 'lagging', brokeC: 'broken', naC: 'no data',
    belowR: 'below reality', aboveR: 'above reality',
    regionsWip: 'This section is being assembled. Reference tables of teleconnections for 14 regions and of food vulnerability are being prepared with a source and a date on every row; a row without a source does not reach the page. The live series, the FAO food price index, is connected next.',
    glossary: 'Glossary', sources: 'Sources and freshness', diffs: 'What changed since the last update', method: 'Method',
    caveatsTitle: 'Caveats', dockHint: 'Point at anything underlined: definition, source, date', pinned: 'pinned · Esc',
    toGloss: 'to the glossary ↓', whatThis: 'what this is', whyHere: 'why it matters here', source: 'source', dataDate: 'data date'
  };
  var MONTHS = t.months;
  var ME = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366];
  var STEP = { day: { one: 'last day', many: 'days' }, week: { one: 'last week', many: 'weeks' }, issue: { one: 'last issue', many: 'issues' } };
  var SHOUT = 'SHOUT';

  // ---------------------------------------------------------------- utils
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
  function addDays(iso, n) { var d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function lvlColor(l) { return 'var(--lv' + Math.max(1, Math.min(5, l)) + ')'; }
  function cls(v) { return v > 0 ? 'up' : (v < 0 ? 'dn' : ''); }
  function ord(n) { var s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }

  // ---------------------------------------------------------------- svg helpers
  function svgOpen(w, h) { return '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg" role="img">'; }
  function poly(pts, color, w, op, dash) {
    var s = pts.filter(function (p) { return fin(p[0]) && fin(p[1]); }).map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    return '<polyline points="' + s + '" fill="none" style="stroke:' + color + '" stroke-width="' + (w || 1.2) + '" opacity="' + (op == null ? 1 : op) + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + ' stroke-linejoin="round"/>';
  }
  function segments(pts, color, w, op, dash) {
    // ряд с пропусками: рвём линию на отрезки, а не тянем через дыры
    var out = [], cur = [];
    pts.forEach(function (p) { if (fin(p[0]) && fin(p[1])) cur.push(p); else { if (cur.length > 1) out.push(poly(cur, color, w, op, dash)); cur = []; } });
    if (cur.length > 1) out.push(poly(cur, color, w, op, dash));
    return out.join('');
  }
  function gridY(vmin, vmax, step, Y, L, R, W) {
    var s = '', g = Math.floor(vmin / step) * step;
    for (; g < vmax; g += step) {
      var zero = Math.abs(g) < 1e-9;
      s += '<line x1="' + L + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width="' + (zero ? 1.3 : 0.6) + '"/>';
      s += '<text x="' + (L - 6) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + fnum(g, step < 0.5 ? 2 : 1) + '</text>';
    }
    return s;
  }

  function spark(m) {
    if (!m || !m.values) return '';
    var vals = m.values, xs = [];
    vals.forEach(function (v, i) { if (fin(v)) xs.push(i); });
    if (xs.length < 2) return '';
    var vv = xs.map(function (i) { return vals[i]; });
    var W = 260, H = 74, Lp = 6, R = 48, Tp = 8, B = 14;
    var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv);
    if (vmax - vmin < 1e-6) vmax = vmin + 1;
    var pad = (vmax - vmin) * .1; vmin -= pad; vmax += pad;
    var X = function (i) { return Lp + i / (vals.length - 1) * (W - Lp - R); };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * (H - Tp - B); };
    var s = svgOpen(W, H);
    if (vmin < 0 && 0 < vmax) s += '<line x1="' + Lp + '" y1="' + Y(0).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(0).toFixed(1) + '" style="stroke:var(--grid)"/>';
    s += poly(xs.map(function (i) { return [X(i), Y(vals[i])]; }), 'var(--text)', 1.5);
    if (m.flags && m.flags.length === vals.length) xs.forEach(function (i) { if (m.flags[i]) s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(vals[i]).toFixed(1) + '" r="1.6" style="fill:var(--nino)"/>'; });
    var li = xs[xs.length - 1];
    s += '<circle cx="' + X(li).toFixed(1) + '" cy="' + Y(vals[li]).toFixed(1) + '" r="3" style="fill:var(--nino)"/>';
    s += '<text x="' + (W - R + 5) + '" y="' + (Y(vals[li]) + 4).toFixed(0) + '" class="tt">' + fnum(vals[li]) + '</text>';
    var d = m.dates || [];
    s += '<text x="' + Lp + '" y="' + (H - 3) + '">' + esc(d[0] || '') + '</text><text x="' + (W - R) + '" y="' + (H - 3) + '" text-anchor="end">' + esc(d[d.length - 1] || '') + '</text>';
    return s + '</svg>';
  }

  function dyn(m) {
    if (!m || !m.values) return '';
    var vv = m.values.filter(fin); if (vv.length < 3) return '';
    var st = STEP[m.step] || { one: 'last step', many: 'steps' };
    var d1 = vv[vv.length - 1] - vv[vv.length - 2];
    var d7 = vv.length >= 8 ? vv[vv.length - 1] - vv[vv.length - 8] : null;
    var k = Math.min(vv.length, 14), tail = vv.slice(-k), sx = 0, sy = 0, sxy = 0, sxx = 0;
    tail.forEach(function (v, i) { sx += i; sy += v; sxy += i * v; sxx += i * i; });
    var sl = (k * sxy - sx * sy) / (k * sxx - sx * sx) * (k - 1);
    var tr = sl > .02 ? t.rising : (sl < -.02 ? t.falling : t.flat);
    return '<span>' + t.now + ' <b>' + fnum(vv[vv.length - 1]) + '</b> ' + esc(m.unit || '') + '</span> · <span>' + st.one + ' <span class="' + cls(d1) + '">' + fnum(d1) + '</span></span>' +
      (d7 != null ? ' · <span>' + t.seven + ' ' + st.many + ' <span class="' + cls(d7) + '">' + fnum(d7) + '</span></span>' : '') +
      ' · <span>' + t.trend + ': ' + tr + ' (' + fnum(sl) + ' over ' + k + ' ' + st.many + ')</span>';
  }

  // ---------------------------------------------------------------- charts
  function fillGaps(arr) {
    var a = arr.map(function (v) { return fin(v) ? v : NaN; });
    for (var j = 0; j < a.length; j++) if (!fin(a[j])) {
      var lo = j ? a[j - 1] : NaN, hi = j + 1 < a.length ? a[j + 1] : NaN;
      a[j] = fin(lo) && fin(hi) ? (lo + hi) / 2 : (fin(lo) ? lo : hi);
    }
    return a;
  }

  function chartRecent(w, title) {
    var W = 940, H = 300, Lp = 46, R = 140, Tp = 26, B = 30, pw = W - Lp - R, ph = H - Tp - B;
    var rec = w.recent, n = rec.length, idx = w.last_idx;
    var cal = []; for (var i = 0; i < n; i++) cal.push(((idx - (n - 1 - i)) % 366 + 366) % 366);
    var B10 = fillGaps(w.band_p10), B90 = fillGaps(w.band_p90), BMAX = fillGaps(w.band_max), BMIN = fillGaps(w.band_min);
    var p10 = cal.map(function (c) { return B10[c]; }), p90 = cal.map(function (c) { return B90[c]; });
    var bmax = cal.map(function (c) { return BMAX[c]; }), bmin = cal.map(function (c) { return BMIN[c]; });
    var f = w.forecast14;
    var vals = rec.filter(fin).concat(bmax.filter(fin), bmin.filter(fin), [f.p90, f.p10]);
    var vmin = Math.min.apply(null, vals) - .05, vmax = Math.max.apply(null, vals) + .08;
    var X = function (i) { return Lp + i / (n - 1 + 14) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">' + esc(title) + '</text>';
    s += gridY(vmin, vmax, vmax - vmin < 2 ? .25 : .5, Y, Lp, R, W);
    function band(lo, hi, op) {
      var up = [], dn = [];
      for (var i = 0; i < n; i++) if (fin(hi[i])) up.push(X(i).toFixed(1) + ',' + Y(hi[i]).toFixed(1));
      for (var j = n - 1; j >= 0; j--) if (fin(lo[j])) dn.push(X(j).toFixed(1) + ',' + Y(lo[j]).toFixed(1));
      return '<polygon points="' + up.join(' ') + ' ' + dn.join(' ') + '" style="fill:var(--band)" opacity="' + op + '"/>';
    }
    s += band(bmin, bmax, .22) + band(p10, p90, .38);
    for (var i2 = 0; i2 < n; i2++) {
      var d = addDays(w.last_date, -(n - 1 - i2));
      if (d.slice(8) === '01') {
        var mo = parseInt(d.slice(5, 7), 10);
        s += '<line x1="' + X(i2).toFixed(0) + '" y1="' + Tp + '" x2="' + X(i2).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--grid)" stroke-width=".5"/>';
        s += '<text x="' + (X(i2) + 2).toFixed(0) + '" y="' + (H - 12) + '">' + MONTHS[mo - 1] + (mo === 1 ? ' ' + d.slice(0, 4) : '') + '</text>';
      }
    }
    s += segments(rec.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 1.8);
    s += segments(rec.slice(-30).map(function (v, i) { return [X(n - 30 + i), fin(v) ? Y(v) : NaN]; }), 'var(--nino)', 2.6);
    var x0 = X(n - 1), x1 = X(n - 1 + 14);
    s += '<polygon points="' + x0.toFixed(1) + ',' + Y(f.from).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p90).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p10).toFixed(1) + '" style="fill:var(--nino)" opacity=".18"/>';
    s += poly([[x0, Y(f.from)], [x1, Y(f.p50)]], 'var(--nino)', 1.6, 1, '5 3');
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p90) + 3).toFixed(0) + '">' + fnum(f.p90) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p50) + 3).toFixed(0) + '" class="tt">' + fnum(f.p50) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p10) + 3).toFixed(0) + '">' + fnum(f.p10) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p90) - 12).toFixed(0) + '">+14 days</text>';
    var ly = H - B - 5 * 17 - 4;
    [['last 30 days', 'var(--nino)'], ['400 days', 'var(--text)'], ['range of all years', 'var(--band)'], ['10–90 % of all years', 'var(--lv2)'], ['forecast p10/p50/p90', 'var(--nino)']].forEach(function (r) {
      s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="8" style="fill:' + r[1] + '" opacity=".8"/><text x="' + (W - R + 32) + '" y="' + (ly + 8) + '">' + r[0] + '</text>'; ly += 17;
    });
    return s + '</svg>';
  }

  function chartAnalogs(N, title) {
    var W = 940, H = 330, Lp = 46, R = 150, Tp = 26, B = 30, pw = W - Lp - R, ph = H - Tp - B, n = 366 + 120;
    var all = [];
    Object.keys(N.analogs).forEach(function (y) { all = all.concat(N.analogs[y].series.filter(fin), N.analogs[y].next.filter(fin)); });
    all = all.concat(N.current_series.filter(fin));
    var vmin = Math.min.apply(null, all) - .1, vmax = Math.max.apply(null, all) + .15;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">' + esc(title) + '</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R, W);
    for (var m = 0; m < 12; m++) s += '<text x="' + X((ME[m] + ME[m + 1]) / 2).toFixed(0) + '" y="' + (H - 10) + '" text-anchor="middle">' + MONTHS[m] + '</text>';
    for (var m2 = 0; m2 < 4; m2++) s += '<text x="' + X(366 + (ME[m2] + ME[m2 + 1]) / 2).toFixed(0) + '" y="' + (H - 10) + '" text-anchor="middle" opacity=".6">' + MONTHS[m2] + '+1</text>';
    s += '<line x1="' + X(366).toFixed(0) + '" y1="' + Tp + '" x2="' + X(366).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="3 3"/>';
    Object.keys(N.analogs).forEach(function (y) {
      var a = N.analogs[y], ser = a.series.concat(a.next);
      s += segments(ser.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--a' + y + ')', 1.5, .9);
    });
    s += segments(N.current_series.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 2.8);
    s += '<circle cx="' + X(N.day).toFixed(1) + '" cy="' + Y(N.current_day).toFixed(1) + '" r="4.5" style="fill:var(--nino)"/>';
    var pe = N.peak_estimate;
    s += '<line x1="' + Lp + '" y1="' + Y(pe.hist_ceiling).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(pe.hist_ceiling).toFixed(0) + '" style="stroke:var(--nino)" stroke-width=".9" stroke-dasharray="6 4"/>';
    s += '<text x="' + (W - R - 4) + '" y="' + (Y(pe.hist_ceiling) - 4).toFixed(0) + '" text-anchor="end" style="fill:var(--nino)">record of the series ' + fnum(pe.hist_ceiling) + '</text>';
    var ly = Tp + 4, yr = (N.year || new Date().getFullYear());
    s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:var(--text)"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '" class="tt">' + yr + ', now</text>'; ly += 17;
    Object.keys(N.analogs).forEach(function (y) {
      var a = N.analogs[y];
      s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:var(--a' + y + ')"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '">' + y + '→' + (parseInt(y, 10) + 1) + ': peak ' + fnum(a.peak) + '</text>'; ly += 17;
    });
    return s + '</svg>';
  }

  function chartNoaa(NW) {
    var ser = NW.series, n = ser.length;
    var W = 940, H = 260, Lp = 46, R = 170, Tp = 26, B = 34, pw = W - Lp - R, ph = H - Tp - B;
    var keys = [['n12a', 'Niño 1+2', 'var(--lv5)'], ['n3a', 'Niño 3', 'var(--nino)'], ['n34a', 'Niño 3.4', 'var(--text)'], ['n4a', 'Niño 4', 'var(--nina)']];
    var all = []; ser.forEach(function (r) { keys.forEach(function (k) { if (fin(r[k[0]])) all.push(r[k[0]]); }); });
    var vmin = Math.min.apply(null, all) - .2, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">NOAA weekly indices, last ' + n + ' weeks (anomaly, °C)</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R, W);
    ser.forEach(function (r, i) { if (parseInt(r.date.slice(8), 10) <= 7) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 14) + '" text-anchor="middle">' + MONTHS[parseInt(r.date.slice(5, 7), 10) - 1] + '</text>'; });
    keys.forEach(function (k) { s += segments(ser.map(function (r, i) { return [X(i), fin(r[k[0]]) ? Y(r[k[0]]) : NaN]; }), k[2], k[0] === 'n34a' ? 2 : 1.4); });
    var ly = Tp + 4;
    keys.forEach(function (k) { s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:' + k[2] + '"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '">' + k[1] + ': ' + fnum(NW.latest[k[0]], 1) + '</text>'; ly += 17; });
    s += '<text x="' + (W - R + 10) + '" y="' + (ly + 12) + '">week of ' + esc(NW.date) + '</text>';
    return s + '</svg>';
  }

  function chartPlume(IRI, obs) {
    var seasons = IRI.seasons, models = IRI.models;
    var fc = []; seasons.forEach(function (sn, i) { if (sn.indexOf('OBS') < 0) fc.push(i); });
    var ao = IRI.against_observed || {};
    var i0 = seasons.indexOf(ao.season) >= 0 ? seasons.indexOf(ao.season) : (fc[0] || 2);
    var W = 940, H = 360, Lp = 46, R = 190, Tp = 26, B = 30, pw = W - Lp - R, ph = H - Tp - B;
    var all = [obs];
    Object.keys(models).forEach(function (k) { (models[k].values || []).forEach(function (v) { if (fin(v)) all.push(v); }); });
    var vmin = Math.min.apply(null, all) - .3, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + (i - i0) / Math.max(1, seasons.length - 1 - i0) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">IRI forecast models, ' + esc(IRI.issued) + ' issue: Niño 3.4 by season, °C</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R, W);
    fc.forEach(function (i) { s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 10) + '" text-anchor="middle">' + esc(seasons[i]) + '</text>'; });
    Object.keys(models).forEach(function (name) {
      var m = models[name]; if ((m.section !== 'dyn' && m.section !== 'stat') || !m.values) return;
      var col = m.section === 'dyn' ? 'var(--nina)' : 'var(--ok)';
      s += segments(fc.map(function (i) { return [X(i), fin(m.values[i]) ? Y(m.values[i]) : NaN]; }), col, 1, .45);
    });
    var hist = IRI.history || [];
    if (hist.length > 1 && hist[1].combined) {
      var pv = hist[1], idx = {}; pv.seasons.forEach(function (sn, k) { idx[sn] = k; });
      s += segments(fc.map(function (i) { var k = idx[seasons[i]]; return [X(i), (k != null && fin(pv.combined[k])) ? Y(pv.combined[k]) : NaN]; }), 'var(--soft)', 1.6, 1, '5 4');
    }
    var comb = (IRI.summary || {}).combined;
    if (comb) s += segments(fc.map(function (i) { return [X(i), fin(comb[i]) ? Y(comb[i]) : NaN]; }), 'var(--text)', 3);
    s += '<circle cx="' + X(i0).toFixed(1) + '" cy="' + Y(obs).toFixed(1) + '" r="5.5" style="fill:var(--nino)"/>';
    s += '<text x="' + (X(i0) + 9).toFixed(0) + '" y="' + (Y(obs) + 4).toFixed(0) + '" class="tt">reality ' + fnum(obs, 1) + '</text>';
    var ly = Tp + 4;
    [['combined forecast', 'var(--text)', 3, ''], ['previous issue' + (hist.length > 1 ? ' (' + hist[1].issued + ')' : ''), 'var(--soft)', 1.6, '5 4'], ['dynamical models', 'var(--nina)', 1, ''], ['statistical models', 'var(--ok)', 1, ''], ['reality this week', 'var(--nino)', 0, '']].forEach(function (r) {
      if (r[2]) s += '<line x1="' + (W - R + 10) + '" y1="' + (ly + 4) + '" x2="' + (W - R + 30) + '" y2="' + (ly + 4) + '" style="stroke:' + r[1] + '" stroke-width="' + r[2] + '"' + (r[3] ? ' stroke-dasharray="' + r[3] + '"' : '') + '/>';
      else s += '<circle cx="' + (W - R + 20) + '" cy="' + (ly + 4) + '" r="4" style="fill:' + r[1] + '"/>';
      s += '<text x="' + (W - R + 36) + '" y="' + (ly + 8) + '">' + esc(r[0]) + '</text>'; ly += 17;
    });
    return s + '</svg>';
  }

  function chartHistory(H) {
    // Наш индекс по снимкам: в день может быть несколько снимков — берём последний за день.
    var byDay = {}; H.forEach(function (r) { if (r.date) byDay[r.date] = r; });
    var days = Object.keys(byDay).sort(), rows = days.map(function (d) { return byDay[d]; });
    if (rows.length < 2) return '';
    var W = 940, Hh = 220, Lp = 46, R = 150, Tp = 26, B = 30, pw = W - Lp - R, ph = Hh - Tp - B, n = rows.length;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (100 - v) / 100 * ph; };
    var s = svgOpen(W, Hh) + '<text class="tt" x="' + Lp + '" y="15">Our risk index by update, and the share of IRI models below reality</text>';
    [0, 25, 50, 75, 100].forEach(function (g) { s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 6) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>'; });
    rows.forEach(function (r, i) { s += '<text x="' + X(i).toFixed(0) + '" y="' + (Hh - 10) + '" text-anchor="middle">' + esc(r.date.slice(5)) + '</text>'; });
    s += poly(rows.map(function (r, i) { return [X(i), Y(r.risk_index)]; }), 'var(--nino)', 2.2);
    rows.forEach(function (r, i) { s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(r.risk_index).toFixed(1) + '" r="3" style="fill:' + (r.shout ? 'var(--lv5)' : 'var(--nino)') + '"/>'; });
    var Y2 = function (v, n2) { return Tp + (1 - v / Math.max(1, n2)) * ph; };
    s += poly(rows.map(function (r, i) { return [X(i), fin(r.n_below) && r.n_models ? Y2(r.n_below, r.n_models) : NaN]; }), 'var(--nina)', 1.4, 1, '4 3');
    var ly = Tp + 4;
    [['risk index 0–100', 'var(--nino)'], ['a SHOUT alert', 'var(--lv5)'], ['share of models below reality', 'var(--nina)']].forEach(function (r) { s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:' + r[1] + '"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '">' + r[0] + '</text>'; ly += 17; });
    return s + '</svg>';
  }

  function pacificScheme(NW) {
    // Схема: экваториальная полоса Тихого океана, четыре участка Niño. Долгота 120° в. д. … 70° з. д.
    var W = 940, H = 200, Lp = 40, R = 20, Tp = 30, B = 30, pw = W - Lp - R, ph = H - Tp - B;
    var lon = function (deg) { return Lp + (deg - 120) / (290 - 120) * pw; };      // deg — «восточная» долгота 120…290
    var lat = function (d) { return Tp + (15 - d) / 30 * ph; };                        // 15N … 15S
    var lv = NW.latest;
    var boxes = [['nino4', 'Niño 4', 160, 210, 5, -5, lv.n4a], ['nino34', 'Niño 3.4', 190, 240, 5, -5, lv.n34a], ['nino3', 'Niño 3', 210, 270, 5, -5, lv.n3a], ['nino12', 'Niño 1+2', 270, 280, 0, -10, lv.n12a]];
    var s = svgOpen(W, H);
    s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph + '" rx="8" style="fill:var(--nina)" opacity=".08"/>';
    s += '<line x1="' + Lp + '" y1="' + lat(0) + '" x2="' + (W - R) + '" y2="' + lat(0) + '" style="stroke:var(--soft)" stroke-width=".6" stroke-dasharray="4 4"/>';
    s += '<text x="' + (Lp + 4) + '" y="' + (lat(0) - 4) + '">equator</text>';
    [120, 150, 180, 210, 240, 270].forEach(function (d) { var lab = d <= 180 ? d + '°E' : (360 - d) + '°W'; s += '<text x="' + lon(d).toFixed(0) + '" y="' + (H - 8) + '" text-anchor="middle">' + lab + '</text>'; });
    s += '<text x="' + (W - R) + '" y="' + (Tp - 8) + '" text-anchor="end">South America →</text><text x="' + Lp + '" y="' + (Tp - 8) + '">← Australia, Indonesia</text>';
    boxes.forEach(function (b) {
      var x = lon(b[2]), w = lon(b[3]) - x, y = lat(b[4]), h = lat(b[5]) - y, v = b[6];
      var col = v >= 2 ? 'var(--lv5)' : (v >= 1 ? 'var(--nino)' : (v >= .5 ? 'var(--lv3)' : (v <= -.5 ? 'var(--nina)' : 'var(--lv2)')));
      s += '<g data-term="' + b[0] + '"><rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" style="fill:' + col + ';stroke:' + col + '" fill-opacity=".22" stroke-width="1.2" rx="3"/>';
      s += '<text class="tt" x="' + (x + w / 2).toFixed(1) + '" y="' + (y + h / 2 - 3).toFixed(1) + '" text-anchor="middle">' + b[1] + '</text>';
      s += '<text x="' + (x + w / 2).toFixed(1) + '" y="' + (y + h / 2 + 11).toFixed(1) + '" text-anchor="middle" style="fill:' + col + '">' + fnum(v, 1) + '</text></g>';
    });
    return s + '</svg>';
  }

  function chartFood(FO) {
    var S = FO.series, n = S.months.length;
    var W = 940, H = 260, Lp = 46, R = 150, Tp = 26, B = 30, pw = W - Lp - R, ph = H - Tp - B;
    var keys = [['Cereals', 'var(--lv3)'], ['Oils', 'var(--nino)'], ['Meat', 'var(--lv2)'], ['Dairy', 'var(--nina)'], ['Sugar', 'var(--ok)']];
    var all = S.index.filter(fin); keys.forEach(function (k) { all = all.concat((S.groups[k[0]] || []).filter(fin)); });
    var vmin = Math.min.apply(null, all) - 5, vmax = Math.max.apply(null, all) + 8;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">FAO Food Price Index and groups, last ' + n + ' months (2014–16 = 100)</text>';
    var step = vmax - vmin > 80 ? 20 : 10;
    for (var g = Math.ceil(vmin / step) * step; g < vmax; g += step) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width=".6"/><text x="' + (Lp - 6) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>';
    S.months.forEach(function (m, i) { if (m.slice(5) === '01' || i === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 10) + '" text-anchor="middle">' + esc(m.slice(0, 4)) + '</text>'; else if (m.slice(5) === '07') s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 10) + '" text-anchor="middle" opacity=".6">Jul</text>'; });
    keys.forEach(function (k) { s += segments(S.months.map(function (m, i) { var v = (S.groups[k[0]] || [])[i]; return [X(i), fin(v) ? Y(v) : NaN]; }), k[1], 1.2, .8); });
    s += segments(S.months.map(function (m, i) { return [X(i), fin(S.index[i]) ? Y(S.index[i]) : NaN]; }), 'var(--text)', 2.6);
    s += '<circle cx="' + X(n - 1).toFixed(1) + '" cy="' + Y(S.index[n - 1]).toFixed(1) + '" r="3.5" style="fill:var(--text)"/>';
    var ly = Tp + 4;
    s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:var(--text)"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '" class="tt">index ' + fnum(S.index[n - 1], 1, false) + '</text>'; ly += 17;
    keys.forEach(function (k) { var v = (S.groups[k[0]] || [])[n - 1]; s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:' + k[1] + '"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '">' + k[0] + ' ' + fnum(v, 1, false) + '</text>'; ly += 17; });
    return s + '</svg>';
  }

  function chartOverlay(ov) {
    var W = 940, H = 240, Lp = 46, R = 150, Tp = 26, B = 30, pw = W - Lp - R, ph = H - Tp - B;
    var series = [['now (' + ov.onset + ')', ov.current, 'var(--text)', 2.6]];
    Object.keys(ov.analogs).forEach(function (y) { series.push([y + ' (' + ov.analogs[y].onset + ')', ov.analogs[y], 'var(--a' + y + ')', 1.5]); });
    var all = []; series.forEach(function (r) { all = all.concat(r[1].values.filter(fin)); });
    var vmin = Math.min.apply(null, all) - 3, vmax = Math.max.apply(null, all) + 5;
    var n = ov.current.values.length, from = ov.current.from;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="15">Food price index as % of the onset month: current event against analogues</text>';
    for (var g = Math.ceil(vmin / 5) * 5; g < vmax; g += 5) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width="' + (g === 100 ? 1.3 : .6) + '"/><text x="' + (Lp - 6) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>';
    for (var i = 0; i < n; i++) { var m = from + i; if (m % 3 === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 10) + '" text-anchor="middle">' + (m > 0 ? '+' : '') + m + '</text>'; }
    s += '<line x1="' + X(-from).toFixed(0) + '" y1="' + Tp + '" x2="' + X(-from).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="3 3"/><text x="' + (X(-from) + 3).toFixed(0) + '" y="' + (Tp + 10) + '">onset</text>';
    series.slice(1).forEach(function (r) { s += segments(r[1].values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), r[2], r[3], .9); });
    s += segments(series[0][1].values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), series[0][2], series[0][3]);
    var ly = Tp + 4;
    series.forEach(function (r) { s += '<rect x="' + (W - R + 10) + '" y="' + ly + '" width="16" height="4" style="fill:' + r[2] + '"/><text x="' + (W - R + 32) + '" y="' + (ly + 7) + '"' + (r === series[0] ? ' class="tt"' : '') + '>' + esc(r[0]) + '</text>'; ly += 17; });
    return s + '</svg>';
  }

  function miniBar(v, ref, w, h) {
    // маленькая линейка «прогноз против реальности»: 0 в середине, вправо тепло
    w = w || 90; h = h || 16;
    if (!fin(v) || !fin(ref)) return '';
    var d = v - ref, span = 1.5, x0 = w / 2, x = x0 + Math.max(-span, Math.min(span, d)) / span * (w / 2 - 2);
    return '<span class="mini"><svg viewBox="0 0 ' + w + ' ' + h + '"><line x1="' + x0 + '" y1="2" x2="' + x0 + '" y2="' + (h - 2) + '" style="stroke:var(--grid)"/><rect x="' + Math.min(x0, x).toFixed(1) + '" y="4" width="' + Math.abs(x - x0).toFixed(1) + '" height="' + (h - 8) + '" style="fill:' + (d < 0 ? 'var(--nina)' : 'var(--nino)') + '" opacity=".8"/></svg></span>';
  }

  // ---------------------------------------------------------------- blocks
  function aiCard(S, key, fallback, big) {
    // Саммари блока: если модель дала блочное — берём; иначе сводка правилами из чисел блока.
    var b = S && S.blocks && S.blocks[key];
    var box = el('div', 'ai' + (big ? ' big' : ''));
    var head = (b ? t.aiBy + ' · ' + esc(S.model || '') : t.aiRules) + (S && S.error ? ' <span class="err">' + t.aiNoModel + '</span>' : '');
    box.innerHTML = '<div class="aih"><span>' + head + '</span><span>' + term('summary', t.whatIs) + '</span></div>' + (b ? '<p>' + esc(b) + '</p>' : fallback);
    return box;
  }

  function blockHead(letter, title, h2) {
    return '<div class="eyebrow"><i>' + letter + '</i>' + esc(title) + '</div><h2>' + h2 + '</h2>';
  }

  function render(D, G, H) {
    var W = D.watch, N = D.nino34, NW = D.noaa, ONI = D.oni, IRI = D.iri && !D.iri.error ? D.iri : null, S = D.summary || {};
    var n34 = W.sst_nino34, sw = W.sst_world, tw = W.t2_world, lat = NW.latest, ls = ONI.last_season;
    var gl = (G && G.en) || {};
    window.__ensoGloss = gl;
    root.innerHTML = '';

    // ---- A. шапка
    var idx = D.risk_index, gc = idx >= 80 ? 'var(--lv5)' : (idx >= 60 ? 'var(--lv4)' : (idx >= 40 ? 'var(--lv3)' : 'var(--ok)'));
    var head = el('div', 'e-head');
    head.innerHTML = '<div class="gauge" data-term="riskindex" style="--v:' + idx + ';--c:' + gc + '"><div class="gv">' + idx + '</div><div class="gl">' + t.riskOf + '</div></div>' +
      '<div><h1>' + t.title + '</h1>' +
      '<div class="e-sub">' + term('nino34', 'Niño 3.4') + ' by the NOAA weekly index is <b>' + fnum(lat.n34a, 1) + ' °C</b>: water in the key patch of the Pacific is ' + fnum(lat.n34a, 1, false) + ' degrees warmer than normal, against a “very strong” threshold of +2.0. Among all years since 1982 for the same 30 days this is <b>rank ' + N.all_years_rank + '</b>. Event type: ' + term('type', NW.type) + '. Official ' + term('oni', 'ONI') + ' for ' + term('seasons', ls) + ': ' + fnum(ONI.current[ls]) + '.</div>' +
      '<div class="e-meta"><span>' + t.built + ' ' + esc(D.generated) + '</span><span>' + t.stamp + ' ' + esc(D.stamp) + '</span><span>' + t.daily + ': Niño 3.4 and ocean ' + esc(n34.last_date) + ' (' + n34.days_stale + ' days ago), land+ocean ' + esc(tw.last_date) + '</span><span>' + t.weekly + ' ' + esc(NW.date) + '</span></div>' +
      '<div class="chips">' + Object.keys(D.sources).map(function (k) { var v = D.sources[k]; return '<span class="chip' + (v.fresh ? '' : ' bad') + '" title="' + esc(v.error || '') + '">' + esc(v.label) + ': ' + (v.fresh ? t.fresh : t.stale.toUpperCase() + ', ' + esc(v.error)) + '</span>'; }).join('') + '</div>' +
      '<div class="e-refresh"><span class="cap" style="margin:0">' + t.refreshNote + '</span></div></div>';
    root.appendChild(head);

    var toc = el('nav', 'toc');
    ['B', 'C', 'D', 'E', 'F', 'G', 'H'].forEach(function (k) { toc.innerHTML += '<a href="#blk-' + k + '">' + k + ' · ' + t[k] + '</a>'; });
    root.appendChild(toc);

    // баннер сторожа
    var alerts = D.alerts || [];
    var ban = el('div', 'shout' + (D.shout ? ' on' : ''));
    if (alerts.length) {
      ban.innerHTML = '<div class="sh">' + (D.shout ? t.shoutOn : t.shoutAttn) + '</div>' + alerts.map(function (a) {
        return '<div class="al ' + (a.level === SHOUT ? 'al5' : 'al3') + '"><b>' + esc(a.level) + '</b><span>' + esc(a.title) + '</span><span class="ald">' + esc(a.detail) + '</span></div>';
      }).join('') + '<div class="cap" style="margin-top:8px">' + term('shout', 'How the watchdog works') + '</div>';
    } else {
      ban.className = 'shout quiet'; ban.innerHTML = '<div class="sh">' + t.quiet + '</div><div class="cap">' + t.quietD + '</div>';
    }
    root.appendChild(ban);

    // ---- B. вердикт
    var B = el('section', 'blk'); B.id = 'blk-B';
    var tp = S.turning_point || {};
    var cav = Array.isArray(S.caveats) ? S.caveats : (S.caveats ? [S.caveats] : []);
    B.innerHTML = blockHead('B', t.B, 'What is happening and what to expect');
    var big = el('div', 'ai big');
    big.innerHTML = '<div class="aih"><span>' + (S.error ? t.aiRules + ' · <span class="err">' + t.aiNoModel + '</span>' : t.aiBy + ' · ' + esc(S.model || '')) + (S.stamp ? ' · ' + esc(S.stamp) : '') + '</span><span>' + term('summary', t.whatIs) + '</span></div>' +
      '<p class="verdict' + (D.shout ? ' on' : '') + '">' + esc(S.verdict || '') + '</p>' +
      '<div class="two" style="gap:6px 22px"><div><b>' + t.turning + '</b>' + (tp.happened ? t.yes : t.no) + ': ' + esc(tp.why || '') + '<b>' + t.changed + '</b>' + esc(S.changed || '') + '<b>' + t.outlook + '</b>' + esc(S.outlook_2_3w || '') + '</div>' +
      '<div><b>' + t.watch + '</b><ul>' + (S.watch || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul><b>' + t.conf + '</b>' + esc(S.confidence || '') + '<b>' + t.cav + '</b><ul>' + cav.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div></div>';
    B.appendChild(big);
    root.appendChild(B);

    // ---- C. где мы
    var C = el('section', 'blk'); C.id = 'blk-C';
    var pe = N.peak_estimate;
    var aboveAll = Object.keys(N.analogs).every(function (y) { return N.analogs[y].same30 < N.current30; });
    C.innerHTML = blockHead('C', t.C, aboveAll ? 'Warmer today than any of the four strongest events were at this time of year' : 'The event follows the strongest ones: rank ' + N.rank_same30 + ' among the analogues');
    var kp = el('div', 'kpis');
    var c4 = NW.chg4w || {}, c8 = NW.chg8w || {};
    kp.innerHTML =
      '<div class="kpi"><div class="kn">' + term('weekly', 'Niño 3.4 · NOAA weekly') + '</div><div class="kv">' + fnum(lat.n34a, 1) + '<small>°C</small></div><div class="km">week of ' + esc(NW.date) + '; ' + term('percentile', ord(Math.round(NW.n34_rank_pct)) + ' percentile') + ' of this season’s weeks</div><div class="kd"><span>4 weeks <span class="' + cls(c4.n34a) + '">' + fnum(c4.n34a, 1) + '</span></span><span>8 weeks <span class="' + cls(c8.n34a) + '">' + fnum(c8.n34a, 1) + '</span></span><span>record ' + fnum(NW.hist_max_n34.n34a, 1) + ' (' + esc(NW.hist_max_n34.date) + ')</span></div></div>' +
      '<div class="kpi"><div class="kn">' + term('oisst', 'Niño 3.4 · daily OISST') + '</div><div class="kv">' + fnum(N.current_day) + '<small>°C</small></div><div class="km">until ' + esc(n34.last_date) + '; 30 days ' + fnum(N.current30) + ', ' + term('rank', 'rank ' + N.all_years_rank) + ' among all years</div><div class="kd"><span>14-day slope <span class="' + cls(n34.slope14.now) + '">' + fnum(n34.slope14.now) + '</span></span><span>' + term('trend', 'above trend') + ' ' + fnum(n34.level30.det) + '</span><span>' + term('cusum', 'CUSUM') + ' ' + (n34.cusum.alarm ? 'alarm' : 'quiet') + '</span></div></div>' +
      '<div class="kpi"><div class="kn">' + term('oni', 'ONI · official') + '</div><div class="kv">' + fnum(ONI.current[ls]) + '<small>' + esc(ls) + '</small></div><div class="km">analogues in the same season: ' + [1982, 1997, 2015, 2023].map(function (y) { return y + ' ' + fnum((ONI.analogs[y] || {})[ls]); }).join(', ') + '</div><div class="kd"><span>“very strong” threshold +2.00</span></div></div>' +
      '<div class="kpi"><div class="kn">' + term('type', 'event type') + '</div><div class="kv" style="font-size:20px;line-height:1.2">' + esc(NW.type) + '</div><div class="km">' + term('nino12', 'Niño 1+2') + ' ' + fnum(lat.n12a, 1) + ', ' + term('nino4', 'Niño 4') + ' ' + fnum(lat.n4a, 1) + '; east minus centre ' + fnum(NW.east_minus_central, 1) + '</div></div>';
    C.appendChild(kp);
    var cf = el('div', 'fig'); cf.innerHTML = pacificScheme(NW) + '<div class="cap">The four patches by which El Niño is judged; the number is the anomaly for the week of ' + esc(NW.date) + '. Point at a patch.</div>';
    C.appendChild(cf);
    var two = el('div', 'two');
    var left = el('div');
    var af = el('div', 'fig'); af.innerHTML = chartAnalogs(N, 'Niño 3.4, daily anomaly: ' + (N.year || '2026') + ' against the four strongest events, same calendar') +
      '<div class="cap">Black line: the current year until ' + esc(n34.last_date) + '; coloured: the onset years of the ' + term('analog', 'analogues') + ' and the first four months of the following year. On the same 30 days the analogues had: ' + Object.keys(N.analogs).map(function (y) { return y + ' ' + fnum(N.analogs[y].same30); }).join(', ') + '; now ' + fnum(N.current30) + '. Dashed: the record of the whole series, ' + fnum(pe.hist_ceiling) + ' °C.</div>';
    left.appendChild(af);
    var note = el('div', 'note warn'); note.innerHTML = '<strong>Peak estimate.</strong> ' + esc(pe.note) + ' For reference: adding the analogues’ gain would give ' + fnum(pe.additive_low, 1) + ' … ' + fnum(pe.additive_high, 1) + ' °C, multiplying it ' + fnum(pe.ratio_mid, 1) + '. Both are arithmetic, not a forecast. Typical peak window: ' + esc(pe.typical_peak_window) + '.';
    left.appendChild(note);
    two.appendChild(left);
    two.appendChild(aiCard(S, 'C', '<p>Niño 3.4 is ' + fnum(lat.n34a, 1) + ' °C by the NOAA week and ' + fnum(N.current_day) + ' by the daily series. For the same 30 days that is rank ' + N.all_years_rank + ' among all years since 1982 and rank ' + N.rank_same30 + ' among the four strongest events. Type: ' + esc(NW.type) + '.</p><p>The official ONI for ' + esc(ls) + ' is ' + fnum(ONI.current[ls]) + ': the three-month average follows the weekly values with a lag.</p>'));
    C.appendChild(two);
    root.appendChild(C);

    // ---- D. риски
    var Dd = el('section', 'blk'); Dd.id = 'blk-D';
    var risks = D.risks || [], n5 = risks.filter(function (r) { return r.level >= 4; }).length;
    Dd.innerHTML = blockHead('D', t.D, risks.length + ' risks, ' + n5 + ' of them high; index ' + idx + ' out of 100');
    var rl = el('div', 'risks');
    risks.forEach(function (r) {
      var c = el('div', 'risk');
      c.innerHTML = '<div class="rl" style="background:' + lvlColor(r.level) + '">' + r.level + '</div><div>' +
        '<div class="rt">' + esc(r.title) + '<span class="rh">· ' + esc(r.horizon) + '</span></div>' +
        '<div class="rp">' + esc(r.plain || '') + '</div><div class="re">' + esc(r.evidence) + '</div>' +
        (r.metric ? '<div class="rd">' + dyn(r.metric) + '</div>' : '') +
        '<div class="rw"><b>' + t.lookAt + ':</b> ' + esc(r.watch) + '</div></div>' +
        '<div class="rs">' + spark(r.metric) + '</div>';
      rl.appendChild(c);
    });
    Dd.appendChild(rl);
    Dd.appendChild(aiCard(S, 'D', '<p>Levels 1–5 add up to the ' + term('riskindex', 'index') + ' of ' + idx + ': it grows with the number and strength of risks and cannot exceed 100. Next to each risk is the series it lives on and its course in words.</p>'));
    root.appendChild(Dd);

    // ---- E. модели
    var E = el('section', 'blk'); E.id = 'blk-E';
    if (IRI) {
      var ao = IRI.against_observed || {}, rv = IRI.revisions || {}, models = IRI.models;
      var names = Object.keys(models).filter(function (k) { return (models[k].section === 'dyn' || models[k].section === 'stat') && models[k].values; });
      var i0 = IRI.seasons.indexOf(ao.season);
      var classes = IRI.classes || {};
      var tally = { ok: 0, lag: 0, broke: 0 };
      names.forEach(function (k) { var c = (classes[k] || {}).cls; if (c) tally[c] = (tally[c] || 0) + 1; });
      var hasCls = tally.ok + tally.lag + tally.broke > 0;
      E.innerHTML = blockHead('E', t.E, hasCls ? ('Of ' + names.length + ' models, ' + tally.ok + ' keep up, ' + tally.lag + ' lag, ' + tally.broke + ' are broken') : (ao.below.length + ' of ' + ao.n + ' models are already below reality for ' + esc(ao.season)));
      var ef = el('div', 'fig'); ef.innerHTML = chartPlume(IRI, lat.n34a) +
        '<div class="cap">Each thin line is one model (' + IRI.n_models + ' of them; ' + term('dynstat', 'dynamical in blue, statistical in green') + '); the thick line is their combined mean; dashed is the combined mean of the previous issue. The red dot is this week’s NOAA Niño 3.4, placed on the first forecast season, ' + esc(ao.season) + '. Everything below the dot has already fallen behind reality. The ' + term('plume', 'plume') + ' is extracted from the figure, accuracy ±0.05 °C.</div>';
      E.appendChild(ef);
      var hist = (IRI.history || []).filter(function (h) { return h.combined; }).map(function (h) { return [h.issued, Math.max.apply(null, h.combined.filter(fin))]; });
      var histTxt = hist.slice().reverse().map(function (h) { return h[0] + ': ' + fnum(h[1]); }).join(' → ');
      var en = el('div', 'note warn');
      en.innerHTML = '<strong>Which models are breaking.</strong> For ' + esc(ao.season) + ' reality is already ' + fnum(ao.observed_weekly, 1) + ' °C, and ' + ao.below.length + ' of ' + ao.n + ' models expected less. The model mean is ' + fnum(ao.mean) + ', the boldest gives ' + fnum(ao.max) + '. Combined forecast peak by issue: ' + histTxt + (rv.n ? '; ' + rv.n_up + ' of ' + rv.n + ' models raised their peak, ' + rv.n_down + ' lowered it' : '') + '. When everyone revises in the same direction, the models are catching up with the event rather than predicting it.';
      E.appendChild(en);
      var tl = el('div', 'tally');
      tl.innerHTML = '<span><i style="background:var(--nino)"></i>' + t.belowR + ': ' + ao.below.length + '</span><span><i style="background:var(--ok)"></i>' + t.aboveR + ': ' + ao.above.length + '</span>' + (hasCls ? '<span><i style="background:var(--ok)"></i>' + t.okC + ' ' + tally.ok + '</span><span><i style="background:var(--lv3)"></i>' + t.lagC + ' ' + tally.lag + '</span><span><i style="background:var(--lv5)"></i>' + t.brokeC + ' ' + tally.broke + '</span>' : '');
      E.appendChild(tl);
      var rvMap = {}; (rv.rows || []).forEach(function (r) { rvMap[r.model] = r; });
      var rows = names.map(function (k) {
        var m = models[k], v = i0 >= 0 ? m.values[i0] : null, pk = Math.max.apply(null, m.values.filter(fin)), r = rvMap[k] || {}, c = classes[k];
        return { name: k, sec: m.section, v: v, gap: fin(v) ? v - ao.observed_weekly : null, peak: pk, dpk: r.d_peak, cls: c };
      }).sort(function (a, b) { return (a.gap == null ? 9 : a.gap) - (b.gap == null ? 9 : b.gap); });
      var tb = el('div', 'tbl');
      tb.innerHTML = '<table class="e"><thead><tr><th>model</th><th>type</th>' + (hasCls ? '<th>class · since issue</th>' : '') + '<th>' + esc(ao.season) + '</th><th>vs reality</th><th></th><th>peak</th><th>peak shift</th></tr></thead><tbody>' +
        rows.map(function (r) {
          var cc = r.cls ? '<span class="cls ' + r.cls.cls + '">' + ({ ok: t.okC, lag: t.lagC, broke: t.brokeC }[r.cls.cls] || t.naC) + '</span>' + (r.cls.since ? ' <span style="font-family:var(--mono);font-size:11px;color:var(--soft)">' + esc(r.cls.since) + '</span>' : '') : '';
          return '<tr><td>' + esc(r.name) + '</td><td>' + (r.sec === 'dyn' ? t.dyn : t.stat) + '</td>' + (hasCls ? '<td>' + cc + '</td>' : '') + '<td class="num">' + fnum(r.v) + '</td><td class="num' + (r.gap != null && r.gap < 0 ? ' top' : '') + '">' + fnum(r.gap) + '</td><td>' + miniBar(r.v, ao.observed_weekly) + '</td><td class="num">' + fnum(r.peak) + '</td><td class="num' + ((r.dpk || 0) > .3 ? ' top' : '') + '">' + fnum(r.dpk) + '</td></tr>';
        }).join('') + '</tbody></table>';
      E.appendChild(tb);
      var ecap = el('div', 'cap'); ecap.innerHTML = 'Peak shift is against the ' + esc(rv.prev_issued || '—') + ' issue. The forecast for ' + esc(ao.season) + ' is a three-month mean while reality is a weekly point, so the comparison is honest only as “the model is below a level already reached”. ' + term('lead', 'Lead') + ' and the classes “keeping up / lagging / broken” are computed on the target completed season once its ONI exists.';
      E.appendChild(ecap);
      E.appendChild(aiCard(S, 'E', '<p>' + esc(IRI.issued) + ' issue: ' + ao.below.length + ' of ' + ao.n + ' models are below the reality of ' + fnum(ao.observed_weekly, 1) + ' °C for ' + esc(ao.season) + '; model mean ' + fnum(ao.mean) + ' ± ' + fnum(ao.sd, 2, false) + '. Combined peak: ' + histTxt + '. Read the models’ winter numbers as a lower bound.</p>'));
    } else {
      E.innerHTML = blockHead('E', t.E, 'The IRI plume did not load') + '<div class="note warn">' + esc((D.iri || {}).error || '') + '</div>';
    }
    root.appendChild(E);

    // ---- F. регионы и еда
    var F = el('section', 'blk'); F.id = 'blk-F';
    var RG = D.regions && !D.regions.error ? D.regions : null, FO = D.food && !D.food.error ? D.food : null;
    if (RG && RG.items && RG.items.length) {
      var scen = RG.current_scenario, SCEN = { base: 'base', strong: 'strong', record: 'record' };
      var high = RG.items.filter(function (r) { return r.levels[scen] >= 4; }).length;
      F.innerHTML = blockHead('F', t.F, high + ' of ' + RG.items.length + ' regions at level 4–5 under the “' + SCEN[scen] + '” scenario' + (FO ? '; world food prices ' + fnum(FO.yoy_pct, 1) + ' % against a year ago' : ''));
      var lead = el('div', 'lead');
      lead.innerHTML = 'Three scenarios of the event: <b>base</b> is the combined model forecast (peak ' + fnum(RG.peak_p50) + ' °C), <b>strong</b> the top of the model spread (' + fnum(RG.peak_max) + '), <b>record</b> reality above every model. Today the data put us in the <b>' + SCEN[scen] + '</b> scenario. Level = ' + term('teleconnection', 'typical impact') + ' × food ' + term('importer', 'vulnerability') + ' + scenario; the formula is in the method note below and every row carries its source.';
      F.appendChild(lead);
      var IMP = { dry: ['drought', 'var(--lv3)'], heat: ['heat', 'var(--lv4)'], wet: ['wet', 'var(--nina)'], flood: ['floods', 'var(--nina)'], none: ['no signal', 'var(--lv2)'] };
      var STR = { robust: 'robust', likely: 'likely', weak: 'weak' };
      function srcPayload(r) {
        return { name: r.name, def: r.countries + '. Vulnerability ' + r.vulnerability.level + ' of 5: ' + r.vulnerability.note + (r.vulnerability.importers && r.vulnerability.importers.length ? ' Net importers: ' + r.vulnerability.importers.join(', ') + '.' : ''), src: r.sources.join(' · '), date: RG.as_of };
      }
      var tb = el('div', 'tbl');
      tb.innerHTML = '<table class="e regions"><thead><tr><th>region</th>' + RG.seasons.map(function (s) { return '<th>' + s + '</th>'; }).join('') + '<th>food vulnerability</th><th>base</th><th>strong</th><th>record</th><th>what to do</th></tr></thead><tbody>' +
        RG.items.map(function (r) {
          var cells = RG.seasons.map(function (s) {
            var x = r.seasons[s] || {}, im = IMP[x.impact] || IMP.none;
            var pay = { name: r.name + ' · ' + s, def: x.note || '', src: r.sources.join(' · '), date: RG.as_of };
            return '<td><span class="imp" data-src="' + esc(JSON.stringify(pay)) + '" style="--c:' + im[1] + '">' + im[0] + (x.impact !== 'none' ? ' <small>' + (STR[x.strength] || '') + '</small>' : '') + '</span></td>';
          }).join('');
          var vb = '<span class="vbar" title="' + r.vulnerability.level + ' of 5">' + [1, 2, 3, 4, 5].map(function (i) { return '<i' + (i <= r.vulnerability.level ? ' class="on"' : '') + '></i>'; }).join('') + '</span>';
          var lv = ['base', 'strong', 'record'].map(function (k) { return '<td class="num"><span class="lvl' + (k === scen ? ' cur' : '') + '" style="background:' + lvlColor(r.levels[k]) + '">' + r.levels[k] + '</span></td>'; }).join('');
          return '<tr><td><b data-src="' + esc(JSON.stringify(srcPayload(r))) + '">' + esc(r.name) + '</b><div class="sub">' + esc(r.countries) + '</div></td>' + cells + '<td>' + vb + '</td>' + lv + '<td class="act">' + r.actions.map(function (a) { return '<div>' + esc(a) + '</div>'; }).join('') + '</td></tr>';
        }).join('') + '</tbody></table>';
      F.appendChild(tb);
      F.appendChild(el('div', 'cap', 'Impacts are typical for a strong eastern-type El Niño, from published NOAA CPC and IRI impact maps and FAO GIEWS alerts: “usually”, never “will”. Point at a region or a season cell for the note and the source. The highlighted level column is the scenario in force today; actions are from FAO and WFP anticipatory-action guidance.'));
      var mn2 = el('div', 'note'); mn2.innerHTML = '<strong>Method.</strong> ' + esc(RG.method);
      F.appendChild(mn2);
    } else {
      F.innerHTML = blockHead('F', t.F, 'What it means for food in your part of the world') + '<div class="honest">' + t.regionsWip + ' ' + term('teleconnection', 'Teleconnections') + ' are typical, not guaranteed; ' + term('importer', 'net food importers') + ' are the first affected; the ' + term('fao', 'FAO index') + ' is the live series.</div>';
    }
    if (FO) {
      var fk = el('div', 'kpis');
      var G = FO.groups;
      fk.innerHTML = '<div class="kpi"><div class="kn">' + term('fao', 'FAO food price index') + '</div><div class="kv">' + fnum(FO.index, 1, false) + '<small>' + esc(FO.last_month) + '</small></div><div class="km">2014–16 = 100; month ' + fnum(FO.mom, 1) + ', year ' + fnum(FO.yoy_pct, 1) + ' %</div><div class="kd">' + Object.keys(G).map(function (g) { return '<span>' + g.toLowerCase() + ' <span class="' + cls(G[g].yoy_pct) + '">' + fnum(G[g].yoy_pct, 1) + ' %</span></span>'; }).join('') + '</div></div>';
      var worst = Object.keys(G).sort(function (a, b) { return (G[b].yoy_pct || 0) - (G[a].yoy_pct || 0); })[0];
      fk.innerHTML += '<div class="kpi"><div class="kn">strongest year-on-year rise</div><div class="kv" style="font-size:22px">' + esc(worst) + '<small>' + fnum(G[worst].yoy_pct, 1) + ' %</small></div><div class="km">' + esc(worst) + ' index ' + fnum(G[worst].last, 1, false) + ' in ' + esc(FO.last_month) + '; the live food series lags by about a month.</div></div>';
      var ov = FO.overlay || {};
      if (ov.current) fk.innerHTML += '<div class="kpi"><div class="kn">since the onset of the event</div><div class="kv">' + fnum(ov.current.values[6 + (function () { var v = ov.current.values.slice(6); var k = -1; v.forEach(function (x, i) { if (fin(x)) k = i; }); return k; })()] - 100, 1) + '<small>%</small></div><div class="km">Onset month ' + esc(ov.onset) + ' = 100 (first three-month season with ONI ≥ +0.5). Analogues at the same distance from onset: ' + Object.keys(ov.analogs).map(function (y) { var a = ov.analogs[y]; var k = ov.current.values.length - 1; while (k > 6 && !fin(ov.current.values[k])) k--; return y + ' ' + fnum((a.values[k] || 100) - 100, 1) + ' %'; }).join(', ') + '.</div></div>';
      F.appendChild(fk);
      var ff = el('div', 'fig'); ff.innerHTML = chartFood(FO) + '<div class="cap">FAO Food Price Index and its five groups, last 36 months (2014–16 = 100). Vegetable oils and cereals are the groups that reacted to past El Niño droughts in South-east Asia and southern Africa.</div>';
      F.appendChild(ff);
      if (ov.current && Object.keys(ov.analogs).length) { var fo2 = el('div', 'fig'); fo2.innerHTML = chartOverlay(ov) + '<div class="cap">The index as a percentage of its value in the onset month, for the current event and three analogues; months −6 … +24 from onset. Past events are not a forecast: 1997-98 came with the Asian crisis, 2015-16 with cheap oil, 2023-24 after the Ukraine price spike.</div>'; F.appendChild(fo2); }
    }
    if (RG || FO) {
      var fRisk = RG ? RG.items.slice(0, 3).map(function (r) { return r.name + ' (' + r.levels[RG.current_scenario] + ')'; }).join(', ') : '';
      F.appendChild(aiCard(S, 'F', '<p>' + (RG ? 'Highest regional levels under the current scenario: ' + fRisk + '. ' : '') + (FO ? 'FAO food price index ' + fnum(FO.index, 1, false) + ' in ' + esc(FO.last_month) + ', ' + fnum(FO.yoy_pct, 1) + ' % against a year ago; oils ' + fnum(FO.groups.Oils.yoy_pct, 1) + ' %, cereals ' + fnum(FO.groups.Cereals.yoy_pct, 1) + ' %.' : '') + '</p>'));
    }
    root.appendChild(F);

    // ---- G. динамика
    var Gd = el('section', 'blk'); Gd.id = 'blk-G';
    Gd.innerHTML = blockHead('G', t.G, 'The world ocean has broken daily records for ' + sw.records.streak + ' days running, land+ocean for ' + tw.records.streak);
    if (H && H.length > 1) { var gh = el('div', 'fig'); gh.innerHTML = chartHistory(H) + '<div class="cap">Every update leaves a snapshot; the lines are built from snapshots, and deleting any one of them breaks nothing.</div>'; Gd.appendChild(gh); }
    var NAMES = { n12a: 'Niño 1+2', n3a: 'Niño 3', n34a: 'Niño 3.4', n4a: 'Niño 4' };
    var nf = el('div', 'fig'); nf.innerHTML = chartNoaa(NW) + '<div class="cap">Over 4 weeks: ' + ['n12a', 'n3a', 'n34a', 'n4a'].map(function (k) { return NAMES[k] + ' ' + fnum(c4[k], 1); }).join(', ') + '; over 8 weeks: ' + ['n12a', 'n3a', 'n34a', 'n4a'].map(function (k) { return fnum(c8[k], 1); }).join(', ') + '. Historical maximum of the weekly Niño 3.4: ' + fnum(NW.hist_max_n34.n34a, 1) + ' (' + esc(NW.hist_max_n34.date) + ').</div>';
    Gd.appendChild(nf);
    [[n34, 'Niño 3.4: anomaly to 1991–2020, last 400 days and two weeks ahead'], [sw, 'World ocean, 60°S–60°N: anomaly to 1991–2020'], [tw, 'Land+ocean (ERA5, 2 m): anomaly to 1991–2020']].forEach(function (p) {
      var w = p[0];
      var f = el('div', 'fig'); f.innerHTML = chartRecent(w, p[1]) + '<div class="cap">Now ' + fnum(w.last_value) + ' °C (until ' + esc(w.last_date) + '); 30 days ' + fnum(w.level30.anom) + ', ' + term('rank', 'rank ' + w.level30.rank_raw + ' of ' + w.level30.of) + ', ' + term('trend', 'above trend') + ' ' + fnum(w.level30.det) + ' (z = ' + w.level30.z + '); ' + term('analog', '+14-day forecast') + ' ' + fnum(w.forecast14.p10) + ' … <b>' + fnum(w.forecast14.p50) + '</b> … ' + fnum(w.forecast14.p90) + ' (' + term('p10p50p90', 'p10/p50/p90') + ' over ' + w.forecast14.n + ' years); ' + w.records.last30 + ' record days of 30, run of ' + w.records.streak + '; trend ' + fnum(w.trend_per_decade) + ' °C per decade.</div>';
      Gd.appendChild(f);
    });
    var keys = [['sst_nino34', 'Niño 3.4'], ['sst_world', 'ocean'], ['t2_world', 'land+ocean']];
    var mt = el('div', 'tbl');
    var mh = '<tr><th>month</th>' + keys.map(function (k) { return '<th colspan="2">' + k[1] + '</th>'; }).join('') + '</tr>';
    var mr = (n34.months13 || []).map(function (m) {
      return '<tr><td>' + MONTHS[m.m - 1] + ' ' + m.y + '</td>' + keys.map(function (k) {
        var mm = (W[k[0]].months13 || []).filter(function (x) { return x.y === m.y && x.m === m.m; })[0];
        return mm ? '<td class="num' + (mm.rank === 1 ? ' top' : '') + '">' + fnum(mm.anom) + '</td><td class="num" style="color:var(--soft);font-size:11px">' + mm.rank + '/' + mm.of + '</td>' : '<td>—</td><td>—</td>';
      }).join('') + '</tr>';
    }).join('');
    mt.innerHTML = '<table class="e"><thead>' + mh + '</thead><tbody>' + mr + '</tbody></table>';
    Gd.appendChild(mt);
    Gd.appendChild(el('div', 'cap', 'Red: a month that became the warmest of its calendar month in the whole record. The current month is incomplete.'));
    Gd.appendChild(aiCard(S, 'G', '<p>Niño 3.4 ' + fnum(n34.last_value) + ' °C, ocean ' + fnum(sw.last_value) + ', land+ocean ' + fnum(tw.last_value) + '. Year to date on the same days: Niño 3.4 ' + term('rank', 'rank ' + n34.ytd.rank + ' of ' + n34.ytd.of) + ', ocean rank ' + sw.ytd.rank + ', land+ocean rank ' + tw.ytd.rank + '. The most anomalous years of the Niño 3.4 series (above trend): ' + n34.annual_z_top.map(function (z) { return z[0] + ' (' + fnum(z[1], 1) + ')'; }).join(', ') + '.</p>'));
    root.appendChild(Gd);

    // ---- H. как посчитано
    var Hh = el('section', 'blk'); Hh.id = 'blk-H';
    Hh.innerHTML = blockHead('H', t.H, 'Glossary, method, sources, what changed');
    var gg = el('div', 'gloss');
    Object.keys(gl).forEach(function (k) { var g = gl[k]; gg.innerHTML += '<div class="gl-i" id="gl-' + esc(k) + '"><b>' + esc(g.name) + '</b>' + esc(g.def) + '<div class="why">' + esc(g.why) + '</div><div class="src">' + esc(g.src) + '</div></div>'; });
    Hh.appendChild(el('h3', null, t.glossary)); Hh.appendChild(gg);
    var mn = el('div', 'note'); mn.innerHTML = '<strong>' + t.method + '.</strong> Everything is computed on ' + term('anomaly', 'anomalies to 1991–2020') + ' taken from the source files themselves. “Rank” is the position of the same 30 calendar days among all years of the series. “Above trend” is after subtracting the linear warming; z is in units of the spread of the same windows across years. Slope and noise are compared with the same 14- and 30-day windows of the same season, so a percentile means “unusual for this time of year”. The 14-day forecast is analogue-based. CUSUM accumulates the deviation from the level at the start of the window in units of the series’ spread; threshold 5. The risk index is a saturating sum of levels: 100·(1 − exp(−Σ level<sup>1.5</sup>/25)).';
    Hh.appendChild(mn);
    var st = el('div', 'tbl');
    st.innerHTML = '<table class="e srcs"><thead><tr><th>series</th><th>what it is</th><th>freshness</th></tr></thead><tbody>' + Object.keys(D.sources).map(function (k) { var v = D.sources[k]; return '<tr><td>' + esc(k) + '</td><td>' + esc(v.label) + '</td><td' + (v.fresh ? '' : ' class="top"') + '>' + (v.fresh ? t.fresh : t.stale + ': ' + esc(v.error)) + '</td></tr>'; }).join('') + '</tbody></table>';
    Hh.appendChild(el('h3', null, t.sources)); Hh.appendChild(st);
    Hh.appendChild(el('div', 'cap', 'climatereanalyzer.org (ERA5 2 m; OISST v2.1) · NOAA CPC weekly Niño indices and ONI · NOAA PSL ERSST v6 monthly Niño 3.4 · IRI/CCSR model plume. Daily OISST lags by one to three weeks: the NOAA weekly data is always fresher, and where they disagree the page trusts the weekly. Analogues: 1982-83, 1997-98, 2015-16, 2023-24, by NOAA ONI. The raw data of every update is stored verbatim with its date.'));
    if (D.diff && D.diff.length) { Hh.appendChild(el('h3', null, t.diffs)); Hh.appendChild(el('ul', 'diff', D.diff.map(function (d) { return '<li>' + esc(d) + '</li>'; }).join(''))); }
    Hh.appendChild(el('h3', null, t.caveatsTitle));
    Hh.appendChild(el('div', 'honest', 'The climatereanalyzer series are global means; the focus of the event is visible only through the NOAA Niño regions. Daily OISST lags by one to three weeks, and the watchdog is blind on it for that long. The IRI plume is extracted from a figure: a change of layout would break the parser, which must then fail loudly. The model summary is an interpretation, not a source: every number in it must be in the digest of facts. Teleconnections are typical, not guaranteed.'));
    root.appendChild(Hh);

    root.querySelectorAll('#blk-H h3').forEach(function (h) { h.style.cssText = 'font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);margin:26px 0 0'; });

    initDock(gl);
    initToc();
  }

  // ---------------------------------------------------------------- dock
  function initDock(gl) {
    var dock = document.getElementById('dock'), body = document.getElementById('dbody'), name = document.getElementById('dname'), title = document.getElementById('dtitle');
    var pinned = null, hot = null;
    title.textContent = t.dockHint;
    function show(target) {
      var k = target.getAttribute('data-term'), payload = null;
      if (k && gl[k]) { var g = gl[k]; payload = { name: g.name, def: g.def, why: g.why, src: g.src }; }
      else if (target.getAttribute('data-src')) { try { payload = JSON.parse(target.getAttribute('data-src')); } catch (e) { payload = null; } }
      if (!payload) return;
      name.textContent = payload.name || ''; title.textContent = '';
      body.innerHTML = '<div><b>' + t.whatThis + '</b>' + esc(payload.def || '') + (payload.why ? '<b>' + t.whyHere + '</b>' + esc(payload.why) : '') + '</div><div>' + (payload.src ? '<b>' + t.source + '</b><span class="dsrc">' + esc(payload.src) + '</span>' : '') + (payload.date ? '<b>' + t.dataDate + '</b><span class="dsrc">' + esc(payload.date) + '</span>' : '') + (k ? '<b></b><a href="#gl-' + esc(k) + '" style="font-family:var(--mono);font-size:12px">' + t.toGloss + '</a>' : '') + '</div>';
      dock.classList.add('open');
      if (hot && hot !== target) hot.classList.remove('hot'); hot = target; hot.classList.add('hot');
    }
    function release() { if (pinned) return; dock.classList.remove('open'); if (hot) { hot.classList.remove('hot'); hot = null; } }
    function find(e) { return e.target.closest && e.target.closest('[data-term],[data-src]'); }
    document.addEventListener('mouseover', function (e) { var x = find(e); if (x && !pinned) show(x); });
    document.addEventListener('mouseout', function (e) { var x = find(e); if (x && !pinned && !(e.relatedTarget && x.contains(e.relatedTarget))) release(); });
    document.addEventListener('click', function (e) {
      var x = find(e);
      if (x) { e.preventDefault(); if (pinned === x) { pinned = null; dock.classList.remove('pinned'); release(); } else { pinned = x; dock.classList.add('pinned'); show(x); } return; }
      if (e.target.closest('#dock')) return;
      if (pinned) { pinned = null; dock.classList.remove('pinned'); release(); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { pinned = null; dock.classList.remove('pinned'); release(); } });
    document.getElementById('dbar').addEventListener('click', function (e) { e.stopPropagation(); if (dock.classList.contains('open') && !pinned) dock.classList.remove('open'); else dock.classList.add('open'); });
  }

  function initToc() {
    var links = [].slice.call(document.querySelectorAll('.toc a')), secs = links.map(function (a) { return document.querySelector(a.getAttribute('href')); });
    if (!('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (x) { if (x.isIntersecting) { links.forEach(function (a) { a.classList.toggle('on', a.getAttribute('href') === '#' + x.target.id); }); } });
    }, { rootMargin: '-20% 0px -70% 0px' });
    secs.forEach(function (s) { if (s) io.observe(s); });
  }

  // ---------------------------------------------------------------- go
  function get(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(u + ': ' + r.status); return r.json(); }); }
  Promise.all([get('/data/enso/latest.json'), get('/data/enso/glossary.json').catch(function () { return {}; }), get('/data/enso/history.json').catch(function () { return []; })])
    .then(function (r) { render(r[0], r[1], r[2]); })
    .catch(function (e) { root.innerHTML = '<div class="e-empty">The data did not load: ' + esc(e.message) + '</div>'; });
})();
