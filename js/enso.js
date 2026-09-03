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
    tabs: { now: 'Where we are', models: 'Models', trend: 'Dynamics', food: 'Regions & food', how: 'Method' },
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
    D: null, G: {}, H: [], P: null,
    view: 'now', sub: {}, risk: null, model: null, scenario: null,
    delta: false,                 // режим «что изменилось с прошлого измерения»
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
  function src(payload, text) { return '<span data-src="' + esc(JSON.stringify(payload)) + '">' + esc(text) + '</span>'; }
  function addDays(iso, n) { var d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function lvlColor(l) { return 'var(--lv' + Math.max(1, Math.min(5, l)) + ')'; }
  function upDown(v) { return v > 0 ? 'up' : (v < 0 ? 'dn' : ''); }
  function ord(n) { var s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }
  function sub(view, def) { return S.sub[view] || def; }
  function prevStamp() { return (S.P && S.P.stamp) || 'the previous update'; }

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
  function svgOpen(w, h) { return '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img">'; }
  function poly(pts, color, w, op, dash) {
    var s = pts.filter(function (p) { return fin(p[0]) && fin(p[1]); }).map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    return '<polyline points="' + s + '" fill="none" style="stroke:' + color + '" stroke-width="' + (w || 1.2) + '" opacity="' + (op == null ? 1 : op) + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + ' stroke-linejoin="round"/>';
  }
  function segs(pts, color, w, op, dash) {
    var out = [], cur = [];
    pts.forEach(function (p) { if (fin(p[0]) && fin(p[1])) cur.push(p); else { if (cur.length > 1) out.push(poly(cur, color, w, op, dash)); cur = []; } });
    if (cur.length > 1) out.push(poly(cur, color, w, op, dash));
    return out.join('');
  }
  function gridY(vmin, vmax, step, Y, L, R, W, dg) {
    var s = '', g = Math.floor(vmin / step) * step;
    for (; g < vmax; g += step) {
      var zero = Math.abs(g) < 1e-9;
      s += '<line x1="' + L + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width="' + (zero ? 1.3 : 0.6) + '"/>';
      s += '<text x="' + (L - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + fnum(g, dg == null ? (step < 0.5 ? 2 : 1) : dg) + '</text>';
    }
    return s;
  }
  function legendW(w) { return w < 560 ? 0 : Math.min(190, Math.round(w * 0.22)); }
  function topPad(w) { return legendW(w) ? 26 : 42; }
  function legend(items, w, h, R, top) {
    var s = '', i;
    if (R > 0) {
      var ly = top + 4;
      for (i = 0; i < items.length; i++) {
        var it = items[i];
        if (it[2] === 'dot') s += '<circle cx="' + (w - R + 18) + '" cy="' + (ly + 4) + '" r="4" style="fill:' + it[1] + '"/>';
        else s += '<line x1="' + (w - R + 8) + '" y1="' + (ly + 4) + '" x2="' + (w - R + 28) + '" y2="' + (ly + 4) + '" style="stroke:' + it[1] + '" stroke-width="' + (it[2] || 2) + '"' + (it[3] ? ' stroke-dasharray="' + it[3] + '"' : '') + '/>';
        s += '<text x="' + (w - R + 34) + '" y="' + (ly + 8) + '">' + esc(it[0]) + '</text>';
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
    var vals = rec.filter(fin).concat(bmax.filter(fin), bmin.filter(fin), [f.p90, f.p10]);
    var vmin = Math.min.apply(null, vals) - .05, vmax = Math.max.apply(null, vals) + .08;
    var X = function (i) { return Lp + i / (n - 1 + 14) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + esc(w.label) + '</text>';
    s += gridY(vmin, vmax, vmax - vmin < 2 ? .25 : .5, Y, Lp, R + 46, W);
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
        if (W > 480 || mo % 2 === 1) s += '<text x="' + (X(i2) + 2).toFixed(0) + '" y="' + (H - 10) + '">' + MONTHS[mo - 1] + (mo === 1 ? ' ' + d.slice(2, 4) : '') + '</text>';
      }
    }
    s += segs(rec.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 1.8);
    s += segs(rec.slice(-30).map(function (v, i) { return [X(n - 30 + i), fin(v) ? Y(v) : NaN]; }), 'var(--nino)', 2.6);
    // где стоял ряд на прошлом обновлении — линия «было»
    var pv = S.P && S.P.daily && S.P.daily[seriesKey(w)];
    if (fin(pv)) {
      s += '<line x1="' + Lp + '" y1="' + Y(pv).toFixed(1) + '" x2="' + (W - R - 46) + '" y2="' + Y(pv).toFixed(1) + '" style="stroke:var(--soft)" stroke-width="1" stroke-dasharray="2 4" opacity=".8"/>';
      s += '<text x="' + (Lp + 3) + '" y="' + (Y(pv) - 3).toFixed(0) + '" style="fill:var(--soft)">was ' + fnum(pv) + ' at ' + esc(prevStamp()) + '</text>';
    }
    var x0 = X(n - 1), x1 = X(n - 1 + 14);
    s += '<polygon points="' + x0.toFixed(1) + ',' + Y(f.from).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p90).toFixed(1) + ' ' + x1.toFixed(1) + ',' + Y(f.p10).toFixed(1) + '" style="fill:var(--nino)" opacity=".18"/>';
    s += poly([[x0, Y(f.from)], [x1, Y(f.p50)]], 'var(--nino)', 1.6, 1, '5 3');
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p90) + 3).toFixed(0) + '">' + fnum(f.p90) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p50) + 3).toFixed(0) + '" class="tt">' + fnum(f.p50) + '</text>';
    s += '<text x="' + (x1 + 4).toFixed(0) + '" y="' + (Y(f.p10) + 3).toFixed(0) + '">' + fnum(f.p10) + '</text>';
    s += legend([['last 30 days', 'var(--nino)', 2.6], ['400 days', 'var(--text)', 1.8], ['10–90 % of all years', 'var(--band)', 6], ['forecast +14 d', 'var(--nino)', 1.6, '5 3']], W, H, R, Tp);
    return s + '</svg>';
  }
  function seriesKey(w) {
    for (var k in SERIES_NAME) if (S.D.watch[k] === w) return k;
    return null;
  }

  function chartAnalogs(N, W, H) {
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B, n = 366 + 120;
    var all = [];
    Object.keys(N.analogs).forEach(function (y) { all = all.concat(N.analogs[y].series.filter(fin), N.analogs[y].next.filter(fin)); });
    all = all.concat(N.current_series.filter(fin));
    var vmin = Math.min.apply(null, all) - .1, vmax = Math.max.apply(null, all) + .15;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">Niño 3.4 daily anomaly: ' + (N.year || '') + ' against the four strongest events</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R + 8, W, 1);
    for (var m = 0; m < 12; m++) if (W > 470 || m % 2 === 0) s += '<text x="' + X((ME[m] + ME[m + 1]) / 2).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + MONTHS[m] + '</text>';
    for (var m2 = 0; m2 < 4; m2++) if (W > 470) s += '<text x="' + X(366 + (ME[m2] + ME[m2 + 1]) / 2).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle" opacity=".55">' + MONTHS[m2] + '+1</text>';
    s += '<line x1="' + X(366).toFixed(0) + '" y1="' + Tp + '" x2="' + X(366).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="3 3"/>';
    var leg = [];
    Object.keys(N.analogs).forEach(function (y) {
      var a = N.analogs[y], ser = a.series.concat(a.next);
      s += segs(ser.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--a' + y + ')', 1.4, .9);
      // В узкой плитке легенда идёт строкой под заголовком: там помещается только год.
      leg.push([R ? (y + '→' + (parseInt(y, 10) + 1) + ': peak ' + fnum(a.peak)) : y, 'var(--a' + y + ')', 1.6]);
    });
    s += segs(N.current_series.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 2.6);
    s += '<circle cx="' + X(N.day).toFixed(1) + '" cy="' + Y(N.current_day).toFixed(1) + '" r="4.5" style="fill:var(--nino)"/>';
    var pe = N.peak_estimate;
    s += '<line x1="' + Lp + '" y1="' + Y(pe.hist_ceiling).toFixed(0) + '" x2="' + (W - R - 8) + '" y2="' + Y(pe.hist_ceiling).toFixed(0) + '" style="stroke:var(--nino)" stroke-width=".9" stroke-dasharray="6 4"/>';
    s += '<text x="' + (W - R - 12) + '" y="' + (Y(pe.hist_ceiling) - 4).toFixed(0) + '" text-anchor="end" style="fill:var(--nino)">record of the series ' + fnum(pe.hist_ceiling) + '</text>';
    s += legend([[R ? ((N.year || 'now') + ' — now') : 'now', 'var(--text)', 2.6]].concat(leg), W, H, R, Tp);
    return s + '</svg>';
  }

  function chartNoaa(NW, W, H) {
    var ser = NW.series, n = ser.length;
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var keys = [['n12a', 'Niño 1+2', 'var(--lv5)'], ['n3a', 'Niño 3', 'var(--nino)'], ['n34a', 'Niño 3.4', 'var(--text)'], ['n4a', 'Niño 4', 'var(--nina)']];
    var all = []; ser.forEach(function (r) { keys.forEach(function (k) { if (fin(r[k[0]])) all.push(r[k[0]]); }); });
    var vmin = Math.min.apply(null, all) - .2, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">NOAA weekly indices, last ' + n + ' weeks (anomaly, °C)</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R + 8, W, 1);
    ser.forEach(function (r, i) { if (parseInt(r.date.slice(8), 10) <= 7 && (W > 470 || i % 2 === 0)) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + MONTHS[parseInt(r.date.slice(5, 7), 10) - 1] + '</text>'; });
    keys.forEach(function (k) { s += segs(ser.map(function (r, i) { return [X(i), fin(r[k[0]]) ? Y(r[k[0]]) : NaN]; }), k[2], k[0] === 'n34a' ? 2.2 : 1.4); });
    s += legend(keys.map(function (k) {
      var p = S.P && S.P.noaa ? S.P.noaa[k[0]] : null;
      return [k[1] + ': ' + fnum(NW.latest[k[0]], 1) + (fin(p) && p !== NW.latest[k[0]] ? ' (was ' + fnum(p, 1) + ')' : ''), k[2], k[0] === 'n34a' ? 2.2 : 1.4];
    }), W, H, R, Tp);
    return s + '</svg>';
  }

  function chartPlume(IRI, obs, W, H) {
    var seasons = IRI.seasons, models = IRI.models;
    var fc = []; seasons.forEach(function (sn, i) { if (sn.indexOf('OBS') < 0) fc.push(i); });
    var ao = IRI.against_observed || {};
    var i0 = seasons.indexOf(ao.season) >= 0 ? seasons.indexOf(ao.season) : (fc[0] || 2);
    var Lp = 46, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var all = [obs];
    Object.keys(models).forEach(function (k) { (models[k].values || []).forEach(function (v) { if (fin(v)) all.push(v); }); });
    var vmin = Math.min.apply(null, all) - .3, vmax = Math.max.apply(null, all) + .3;
    var X = function (i) { return Lp + (i - i0) / Math.max(1, seasons.length - 1 - i0) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">IRI model plume, ' + esc(IRI.issued) + ' issue: Niño 3.4 by season, °C</text>';
    s += gridY(vmin, vmax, .5, Y, Lp, R + 8, W, 1);
    fc.forEach(function (i, k) { if (W > 470 || k % 2 === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + esc(seasons[i]) + '</text>'; });
    var cls = IRI.classes || {};
    Object.keys(models).forEach(function (name) {
      var m = models[name]; if ((m.section !== 'dyn' && m.section !== 'stat') || !m.values) return;
      var hot = S.model === name, c = (cls[name] || {}).cls;
      var col = hot ? 'var(--ochre)' : (c === 'broke' ? 'var(--lv5)' : (c === 'lag' ? 'var(--lv3)' : (m.section === 'dyn' ? 'var(--nina)' : 'var(--ok)')));
      s += segs(fc.map(function (i) { return [X(i), fin(m.values[i]) ? Y(m.values[i]) : NaN]; }), col, hot ? 2.6 : 1, hot ? 1 : (c === 'broke' ? .5 : .4));
    });
    var hist = IRI.history || [];
    if (hist.length > 1 && hist[1].combined) {
      var pv = hist[1], idx = {}; pv.seasons.forEach(function (sn, k) { idx[sn] = k; });
      s += segs(fc.map(function (i) { var k = idx[seasons[i]]; return [X(i), (k != null && fin(pv.combined[k])) ? Y(pv.combined[k]) : NaN]; }), 'var(--soft)', 1.6, 1, '5 4');
    }
    var comb = (IRI.summary || {}).combined;
    if (comb) s += segs(fc.map(function (i) { return [X(i), fin(comb[i]) ? Y(comb[i]) : NaN]; }), 'var(--text)', 3);
    s += '<circle cx="' + X(i0).toFixed(1) + '" cy="' + Y(obs).toFixed(1) + '" r="5.5" style="fill:var(--nino)"/>';
    s += '<text x="' + (X(i0) + 9).toFixed(0) + '" y="' + (Y(obs) + 4).toFixed(0) + '" class="tt">reality ' + fnum(obs, 1) + '</text>';
    var leg = [['combined forecast', 'var(--text)', 3], ['previous issue' + (hist.length > 1 ? ' (' + hist[1].issued + ')' : ''), 'var(--soft)', 1.6, '5 4'],
      ['keeping up', 'var(--nina)', 1.4], ['lagging', 'var(--lv3)', 1.4], ['broken', 'var(--lv5)', 1.4], ['reality this week', 'var(--nino)', 'dot']];
    if (S.model) leg.unshift([S.model, 'var(--ochre)', 2.6]);
    s += legend(leg, W, H, R, Tp);
    return s + '</svg>';
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
      if (n < 14 || i % 2 === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 16) + '" text-anchor="middle">' + esc(r.issue.split(' ')[0]) + '</text><text x="' + X(i).toFixed(0) + '" y="' + (H - 5) + '" text-anchor="middle" opacity=".6">' + esc(r.season.split(' ')[0]) + '</text>';
    });
    s += poly(rows.map(function (r, i) { return [X(i), Y2(r.mean_err)]; }), 'var(--text)', 2);
    rows.forEach(function (r, i) { s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y2(r.mean_err).toFixed(1) + '" r="2.6" style="fill:var(--text)"/>'; });
    [emin, (emin + emax) / 2, emax].forEach(function (g) { s += '<text x="' + (W - R - 38) + '" y="' + (Y2(g) + 4).toFixed(0) + '" style="fill:var(--soft)">' + fnum(g, 1) + '</text>'; });
    s += '<text x="' + (W - R - 38) + '" y="' + (Tp - 6) + '" style="fill:var(--soft)">mean err, °C</text>';
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
    list.forEach(function (r, i) { if (n < 14 || i % Math.ceil(n / 12) === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + esc(r.date.slice(5)) + '</text>'; });
    s += poly(list.map(function (r, i) { return [X(i), Y(r.risk_index)]; }), 'var(--nino)', 2.2);
    list.forEach(function (r, i) { s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(r.risk_index).toFixed(1) + '" r="3" style="fill:' + (r.shout ? 'var(--lv5)' : 'var(--nino)') + '"/>'; });
    s += poly(list.map(function (r, i) { return [X(i), fin(r.n_below) && r.n_models ? Tp + (1 - r.n_below / r.n_models) * ph : NaN]; }), 'var(--nina)', 1.4, 1, '4 3');
    s += legend([['risk index 0–100', 'var(--nino)', 2.2], ['a SHOUT alert', 'var(--lv5)', 'dot'], ['share of models below reality', 'var(--nina)', 1.4, '4 3']], W, H, R, Tp);
    return s + '</svg>';
  }

  /* Карта Тихого океана: текущий индекс каждого участка и то же место у сильнейших событий. */
  function pacific(NW, W, H) {
    // В низкой плитке (телефон, короткое окно) подписи долгот и «экватор» съедали карту —
    // при высоте меньше 200 пикселей оставляем только сами участки.
    var small = H < 200;
    var Lp = small ? 14 : 40, R = small ? 10 : 16, Tp = small ? 22 : 34, B = small ? 10 : 30;
    var pw = W - Lp - R, ph = H - Tp - B;
    var lon = function (d) { return Lp + (d - 120) / (290 - 120) * pw; };
    var lat = function (d) { return Tp + (15 - d) / 30 * ph; };
    var lv = NW.latest, aw = NW.analog_week || {}, ap = NW.analog_peak || {};
    var years = Object.keys(aw).sort();
    var cmpYear = S.sub.cmp || (years.indexOf('1997') >= 0 ? '1997' : years[years.length - 1]);
    var boxes = [['nino4', 'Niño 4', 160, 210, 5, -5, 'n4a'], ['nino34', 'Niño 3.4', 190, 240, 5, -5, 'n34a'],
      ['nino3', 'Niño 3', 210, 270, 5, -5, 'n3a'], ['nino12', 'Niño 1+2', 270, 280, 0, -10, 'n12a']];
    var s = svgOpen(W, H);
    s += '<text class="tt" x="' + Lp + '" y="13">Week of ' + esc(NW.date) + ' against ' + esc(cmpYear) + '–' + (parseInt(cmpYear, 10) + 1) + ' on the same week</text>';
    s += '<rect x="' + Lp + '" y="' + Tp + '" width="' + pw + '" height="' + ph + '" rx="8" style="fill:var(--nina)" opacity=".08"/>';
    s += '<line x1="' + Lp + '" y1="' + lat(0) + '" x2="' + (W - R) + '" y2="' + lat(0) + '" style="stroke:var(--soft)" stroke-width=".6" stroke-dasharray="4 4"/>';
    s += '<text x="' + (Lp + 4) + '" y="' + (lat(0) - 4) + '">equator</text>';
    if (!small) {
      [120, 150, 180, 210, 240, 270].forEach(function (d) { s += '<text x="' + lon(d).toFixed(0) + '" y="' + (H - 8) + '" text-anchor="middle">' + (d <= 180 ? d + '°E' : (360 - d) + '°W') + '</text>'; });
      s += '<text x="' + (W - R) + '" y="' + (Tp - 9) + '" text-anchor="end">South America →</text><text x="' + Lp + '" y="' + (Tp - 9) + '">← Australia, Indonesia</text>';
    }
    boxes.forEach(function (b) {
      var x = lon(b[2]), w = lon(b[3]) - x, y = lat(b[4]), h = lat(b[5]) - y, key = b[6], v = lv[key];
      var then = (aw[cmpYear] || {})[key], peak = (ap[cmpYear] || {})[key];
      var col = v >= 2 ? 'var(--lv5)' : (v >= 1 ? 'var(--nino)' : (v >= .5 ? 'var(--lv3)' : (v <= -.5 ? 'var(--nina)' : 'var(--lv2)')));
      var pay = { name: b[1] + ' — week of ' + NW.date,
        def: 'Now ' + fnum(v, 1) + ' °C. On the same week of ' + cmpYear + ': ' + fnum(then, 1) + ' °C; the peak of that event was ' + fnum(peak, 1) + ' °C. ' +
          (fin(then) ? (v > then ? 'This event is ' + fnum(v - then, 1) + ' °C warmer at the same point of the calendar.' : 'This event is ' + fnum(v - then, 1) + ' °C against it.') : ''),
        src: 'NOAA CPC weekly indices, wksst9120', date: NW.date };
      s += '<g data-src="' + esc(JSON.stringify(pay)) + '"><rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" style="fill:' + col + ';stroke:' + col + '" fill-opacity=".22" stroke-width="1.2" rx="3"/>';
      var cy = y + h / 2;
      s += '<text class="tt" x="' + (x + w / 2).toFixed(1) + '" y="' + (cy - (small ? 4 : 6)).toFixed(1) + '" text-anchor="middle">' + b[1] + '</text>';
      s += '<text x="' + (x + w / 2).toFixed(1) + '" y="' + (cy + (small ? 8 : 9)).toFixed(1) + '" text-anchor="middle" style="fill:' + col + '" font-size="' + (small ? 12 : 13) + '">' + fnum(v, 1) + '</text>';
      if (fin(then)) s += '<text x="' + (x + w / 2).toFixed(1) + '" y="' + (cy + (small ? 19 : 22)).toFixed(1) + '" text-anchor="middle" style="fill:var(--soft)" font-size="10">' + cmpYear + ': ' + fnum(then, 1) + '</text>';
      s += '</g>';
    });
    return s + '</svg>';
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
    keys.forEach(function (k) { s += segs(Sr.months.map(function (m, i) { var v = (Sr.groups[k[0]] || [])[i]; return [X(i), fin(v) ? Y(v) : NaN]; }), k[1], 1.2, .8); });
    s += segs(Sr.months.map(function (m, i) { return [X(i), fin(Sr.index[i]) ? Y(Sr.index[i]) : NaN]; }), 'var(--text)', 2.6);
    s += '<circle cx="' + X(n - 1).toFixed(1) + '" cy="' + Y(Sr.index[n - 1]).toFixed(1) + '" r="3.5" style="fill:var(--text)"/>';
    s += legend([['index ' + fnum(Sr.index[n - 1], 1, false), 'var(--text)', 2.6]].concat(keys.map(function (k) { return [k[0] + ' ' + fnum((Sr.groups[k[0]] || [])[n - 1], 1, false), k[1], 1.4]; })), W, H, R, Tp);
    return s + '</svg>';
  }

  function chartOverlay(ov, W, H) {
    var Lp = 44, R = legendW(W), Tp = topPad(W), B = 26, pw = W - Lp - R - 8, ph = H - Tp - B;
    var series = [['now (' + ov.onset + ')', ov.current, 'var(--text)', 2.6]];
    Object.keys(ov.analogs).forEach(function (y) { series.push([y + ' (' + ov.analogs[y].onset + ')', ov.analogs[y], 'var(--a' + y + ')', 1.5]); });
    var all = []; series.forEach(function (r) { all = all.concat(r[1].values.filter(fin)); });
    var vmin = Math.min.apply(null, all) - 3, vmax = Math.max.apply(null, all) + 5;
    var n = ov.current.values.length, from = ov.current.from;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">Food price index as % of the onset month: this event against analogues</text>';
    for (var g = Math.ceil(vmin / 5) * 5; g < vmax; g += 5) s += '<line x1="' + Lp + '" y1="' + Y(g).toFixed(0) + '" x2="' + (W - R - 8) + '" y2="' + Y(g).toFixed(0) + '" style="stroke:var(--grid)" stroke-width="' + (g === 100 ? 1.3 : .6) + '"/><text x="' + (Lp - 5) + '" y="' + (Y(g) + 4).toFixed(0) + '" text-anchor="end">' + g + '</text>';
    for (var i = 0; i < n; i++) { var m = from + i; if (m % 3 === 0) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="middle">' + (m > 0 ? '+' : '') + m + '</text>'; }
    s += '<line x1="' + X(-from).toFixed(0) + '" y1="' + Tp + '" x2="' + X(-from).toFixed(0) + '" y2="' + (H - B) + '" style="stroke:var(--soft)" stroke-width=".8" stroke-dasharray="3 3"/><text x="' + (X(-from) + 3).toFixed(0) + '" y="' + (Tp + 10) + '">onset</text>';
    series.slice(1).forEach(function (r) { s += segs(r[1].values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), r[2], r[3], .9); });
    s += segs(series[0][1].values.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), series[0][2], series[0][3]);
    s += legend(series.map(function (r) { return [r[0], r[2], r[3]]; }), W, H, R, Tp);
    return s + '</svg>';
  }

  function chartMetric(m, W, H, title) {
    var vals = m.values, dates = m.dates || [], n = vals.length;
    var Lp = 46, R = 54, Tp = topPad(W), B = 26, pw = W - Lp - R, ph = H - Tp - B;
    var vv = vals.filter(fin);
    if (vv.length < 2) return svgOpen(W, H) + '<text x="20" y="' + (H / 2) + '">no series for this item</text></svg>';
    var vmin = Math.min.apply(null, vv), vmax = Math.max.apply(null, vv);
    if (vmax - vmin < 1e-6) vmax = vmin + 1;
    var pad = (vmax - vmin) * .12; vmin -= pad; vmax += pad;
    var X = function (i) { return Lp + i / (n - 1) * pw; };
    var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
    var s = svgOpen(W, H) + '<text class="tt" x="' + Lp + '" y="13">' + esc(title || m.name) + '</text>';
    var step = (vmax - vmin) > 4 ? 1 : ((vmax - vmin) > 1.2 ? .5 : .25);
    s += gridY(vmin, vmax, step, Y, Lp, R, W);
    if (dates.length === n) dates.forEach(function (d, i) { if (i === 0 || i === n - 1 || (n > 6 && i === Math.floor(n / 2))) s += '<text x="' + X(i).toFixed(0) + '" y="' + (H - 9) + '" text-anchor="' + (i === 0 ? 'start' : (i === n - 1 ? 'end' : 'middle')) + '">' + esc(String(d)) + '</text>'; });
    s += segs(vals.map(function (v, i) { return [X(i), fin(v) ? Y(v) : NaN]; }), 'var(--text)', 2.2);
    if (m.flags && m.flags.length === n) vals.forEach(function (v, i) { if (m.flags[i] && fin(v)) s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(v).toFixed(1) + '" r="2.2" style="fill:var(--nino)"/>'; });
    var li = n - 1; while (li > 0 && !fin(vals[li])) li--;
    s += '<circle cx="' + X(li).toFixed(1) + '" cy="' + Y(vals[li]).toFixed(1) + '" r="4" style="fill:var(--nino)"/>';
    s += '<text x="' + (X(li) + 7).toFixed(0) + '" y="' + (Y(vals[li]) + 4).toFixed(0) + '" class="tt">' + fnum(vals[li]) + ' ' + esc(m.unit || '') + '</text>';
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
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" style="display:block">';
    s += poly(xs.map(function (i) { return [X(i), Y(vals[i])]; }), 'var(--soft)', 1.3);
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
      var b = el('button', 'tab' + (S.view === v[0] ? ' on' : ''), esc(v[1]));
      b.type = 'button';
      b.onclick = function () { S.view = v[0]; S.risk = null; render(); };
      host.appendChild(b);
    });
    var t = $('deltaBtn');
    if (t) { t.className = 'tab delta' + (S.delta ? ' on' : ''); t.textContent = S.delta ? 'change since last update' : 'now'; }
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
    item('<b>updated</b> ' + esc(D.stamp), { name: 'This update', def: 'The panel was recomputed at ' + D.stamp + (P ? '; the previous update was at ' + P.stamp + '.' : '.') + ' Updating is semi-automatic: a person runs it and looks at the result before it goes out.', src: 'tools/enso/publish.py', date: D.generated });
    item('<b>daily</b> ' + esc(n34.last_date) + ' <i>' + n34.days_stale + ' d ago</i>', { name: 'Daily series', def: 'Niño 3.4 and the world ocean come from daily OISST, which lags one to three weeks. Land+ocean (ERA5) reaches ' + tw.last_date + '.', src: 'climatereanalyzer.org', date: n34.last_date }, n34.days_stale > 14 ? 'bad' : '');
    item('<b>NOAA week</b> ' + esc(D.noaa.date), { name: 'NOAA weekly indices', def: 'Published every Wednesday for the previous week; always fresher than the daily OISST, and where they disagree the panel trusts the weekly.', src: 'NOAA CPC wksst9120.for', date: D.noaa.date });
    if (D.iri && D.iri.issued) item('<b>IRI</b> ' + esc(D.iri.issued), { name: 'IRI model plume', def: 'The forecasts of two dozen centres, published around the 19th of each month. ' + ((D.iri.class_issues || []).length) + ' issues are stored here, which is what makes the model scoreboard possible.', src: 'iri.columbia.edu', date: D.iri.issued });
    if (D.food && !D.food.error) item('<b>FAO</b> ' + esc(D.food.last_month), { name: 'FAO Food Price Index', def: 'Monthly, published on the first Friday for the previous month: the only live food series available without registration.', src: 'fao.org', date: D.food.last_month });
    var dots = el('span', 'dots');
    Object.keys(D.sources).forEach(function (k) {
      var v = D.sources[k], i = el('i', v.fresh ? '' : 'bad');
      i.setAttribute('data-src', JSON.stringify({ name: v.label, def: v.fresh ? 'Fresh: this source answered on the current update.' : 'Did not answer: ' + (v.error || '') + ' The panel is using the last good copy.', src: k, date: D.stamp }));
      dots.appendChild(i);
    });
    host.appendChild(dots);
  }

  // ---------------------------------------------------------------- rails
  function alertCard(a) {
    var c = el('div', 'card alert-card ' + (a.level === 'SHOUT' ? 'lv-shout' : 'lv-watch') + ' kind-' + (a.kind || 'climate'));
    var isNew = S.P && S.P.alerts && S.P.alerts.indexOf(a.title) < 0;
    c.innerHTML = '<div class="ch"><b>' + esc(a.level) + '</b><span class="kk">' + esc(a.kind || 'climate') + '</span>' + (isNew ? '<span class="new">new</span>' : '') + '</div>' +
      '<div class="ct">' + esc(a.title) + '</div><div class="cd">' + esc(a.detail) + '</div>';
    return c;
  }

  function railState() {
    var D = S.D, N = D.nino34, NW = D.noaa, ONI = D.oni, sm = D.summary || {}, P = S.P;
    var col = $('railL'); col.innerHTML = '';
    var t = tile('State', esc(NW.type), 'grow');
    var idx = D.risk_index, gc = idx >= 80 ? 'var(--lv5)' : (idx >= 60 ? 'var(--lv4)' : (idx >= 40 ? 'var(--lv3)' : 'var(--ok)'));
    var ls = ONI.last_season;
    var ri = pair(idx, P ? P.risk_index : null, 0);
    var box = el('div', 'cards');

    // 1. KPI-карточка состояния
    var k1 = el('div', 'card kpi-card');
    k1.innerHTML = '<div class="gauge-row"><div class="gauge" data-term="riskindex" style="--v:' + idx + ';--c:' + gc + '"><div class="gv">' + idx + '</div><div class="gl">risk index</div></div>' +
      '<div class="g-side"><b>' + term('nino34', 'Niño 3.4') + ' ' + fnum(NW.latest.n34a, 1) + ' °C</b>' +
      'rank ' + N.all_years_rank + ' of all years on the same 30 days. ' + term('oni', 'ONI') + ' ' + fnum(ONI.current[ls]) + ' (' + esc(ls) + ').' +
      '<span class="chgline">' + ri.small + '</span></div></div>';
    box.appendChild(k1);

    // 2. тревоги карточками, по видам
    var alerts = D.alerts || [];
    ['climate', 'food', 'models'].forEach(function (kind) {
      alerts.filter(function (a) { return (a.kind || 'climate') === kind; }).forEach(function (a) { box.appendChild(alertCard(a)); });
    });
    if (!alerts.length) box.appendChild(el('div', 'card quiet', '<div class="ct">The watchdog sees no turning point</div><div class="cd">No rule fired: no record broken, no reversal, no run of records ended.</div>'));

    // 3. карточка «как ломаются модели»
    var bd = (D.iri || {}).breakdown;
    if (bd && (bd.by_issue || []).length) {
      var rows = bd.by_issue, first = rows[0], last = rows[rows.length - 1];
      var chronic = (bd.chronic || []).filter(function (c) { return c.of >= 3 && c.issues_low >= Math.max(3, c.of * 0.6); });
      var c3 = el('div', 'card models-card');
      c3.innerHTML = '<div class="ch"><b>MODELS</b><span class="kk">since ' + esc(first.issue) + '</span></div>' +
        '<div class="ct">' + last.share + ' % of models are below reality, against ' + first.share + ' % a year ago</div>' +
        '<div class="cd">Verified on ' + rows.length + ' issues: for each we take its nearest season that already has an official ONI. The average model error went ' +
        fnum(first.mean_err) + ' → ' + fnum(last.mean_err) + ' °C.</div>' +
        (chronic.length ? '<div class="cd chronic">Below reality in most issues: ' + chronic.slice(0, 5).map(function (c) { return '<b>' + esc(c.model) + '</b> ' + c.issues_low + '/' + c.of; }).join(', ') + '</div>' : '') +
        '<div class="spark">' + sparkBars(rows) + '</div>';
      c3.onclick = function () { S.view = 'models'; S.sub.models = 'breakdown'; render(); };
      box.appendChild(c3);
    }

    // 4. вердикт модели
    var tp = sm.turning_point || {}, cav = Array.isArray(sm.caveats) ? sm.caveats : (sm.caveats ? [sm.caveats] : []);
    var v = el('div', 'card verdict');
    v.innerHTML = '<div class="ch"><b>VERDICT</b><span class="kk">' + (sm.error ? 'rules' : esc(sm.model || '')) + '</span></div>' +
      '<p class="vv' + (D.shout ? ' on' : '') + '">' + esc(sm.verdict || '') + '</p>' +
      '<dl><dt>turning point</dt><dd>' + (tp.happened ? 'yes' : 'no') + ': ' + esc(tp.why || '') + '</dd>' +
      '<dt>2–3 weeks</dt><dd>' + esc(sm.outlook_2_3w || '') + '</dd>' +
      '<dt>what changed</dt><dd>' + esc(sm.changed || '') + '</dd>' +
      '<dt>what to watch</dt><dd><ul>' + (sm.watch || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></dd>' +
      '<dt>confidence</dt><dd>' + esc(sm.confidence || '') + '</dd>' +
      '<dt>caveats</dt><dd><ul>' + cav.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></dd></dl>';
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
      var was = P && P.risks ? P.risks[r.title] : null;
      var c = el('div', 'risk' + (S.risk === i ? ' on' : ''));
      c.innerHTML = '<div class="rl" style="background:' + lvlColor(r.level) + '">' + r.level + '</div>' +
        '<div><div class="rt">' + esc(r.title) + (was == null && P ? ' <span class="new">new</span>' : '') + '</div>' +
        '<div class="rh">' + esc(r.horizon) + (fin(was) && was !== r.level ? ' · was ' + was : '') + (r.metric ? ' · ' + esc(r.metric.name) : '') + '</div>' +
        (r.metric ? '<div class="rs">' + spark(r.metric, 200, 24) + '</div>' : '') + '</div>';
      c.onclick = function () { S.risk = (S.risk === i ? null : i); S.view = S.risk == null ? 'now' : 'risk'; render(); };
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
        var btn = el('button', b.on ? 'on' : '', esc(b.label)); btn.type = 'button'; btn.onclick = b.click;
        seg.appendChild(btn);
      });
      head.appendChild(seg);
    }
    st.appendChild(head);
    var body = el('div', 'stage-body');
    st.appendChild(body);
    return body;
  }
  function plot(body, draw) {
    var p = el('div', 'plot');
    body.appendChild(p);
    S.plotEl = p; S.draw = draw;
    redrawPlot();
  }
  function redrawPlot() {
    var p = S.plotEl;
    if (!p || !S.draw || !p.isConnected) return;
    var w = Math.max(220, Math.round(p.clientWidth)), h = Math.max(150, Math.round(p.clientHeight));
    p.innerHTML = S.draw(w, h);
  }
  function segBtn(view, key, label, defKey) {
    return { label: label, on: sub(view, defKey) === key, click: function () { S.sub[view] = key; render(); } };
  }

  function viewNow() {
    var D = S.D, N = D.nino34, NW = D.noaa, ONI = D.oni, n34 = D.watch.sst_nino34, P = S.P;
    var k = sub('now', 'analogs');
    var above = Object.keys(N.analogs).every(function (y) { return N.analogs[y].same30 < N.current30; });
    var segs2 = [segBtn('now', 'analogs', 'Against analogues', 'analogs'), segBtn('now', 'map', 'Pacific map', 'analogs'), segBtn('now', 'weekly', 'Weekly indices', 'analogs')];
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
      plot(body, function (w, h) { return pacific(NW, w, h); });
    } else if (k === 'weekly') plot(body, function (w, h) { return chartNoaa(NW, w, h); });
    else plot(body, function (w, h) { return chartAnalogs(N, w, h); });

    var pe = N.peak_estimate, ls = ONI.last_season, c4 = NW.chg4w || {}, c8 = NW.chg8w || {};
    var cap = el('div', 'cap');
    var aw = (NW.analog_week || {})[S.sub.cmp || '1997'] || {};
    cap.innerHTML = k === 'map' ? 'Colour is the anomaly of the week; the small number under it is the same week of the comparison event. Point at a patch for the full comparison and the peak that event reached.'
      : (k === 'weekly' ? 'Over 4 weeks: Niño 3.4 ' + fnum(c4.n34a, 1) + ', Niño 1+2 ' + fnum(c4.n12a, 1) + '; over 8 weeks ' + fnum(c8.n34a, 1) + ' and ' + fnum(c8.n12a, 1) + '. Record of the weekly Niño 3.4: ' + fnum(NW.hist_max_n34.n34a, 1) + ' (' + esc(NW.hist_max_n34.date) + ').'
        : '<strong>Peak estimate.</strong> ' + esc(pe.note) + ' Typical peak window ' + esc(pe.typical_peak_window) + '.');
    body.appendChild(cap);

    var wk = pair(NW.latest.n34a, P && P.noaa ? P.noaa.n34a : null, 1, '°C');
    var dy = pair(N.current_day, P && P.daily ? P.daily.sst_nino34 : null, 2, '°C');
    var on = pair(ONI.current[ls], P && P.oni ? P.oni[ls] : null, 2, '');
    var kp = el('div', 'kpis');
    kp.innerHTML =
      '<div class="kpi"><div class="kn">' + term('weekly', 'NOAA weekly') + '</div><div class="kv">' + wk.big + '</div><div class="km">' + term('percentile', ord(Math.round(NW.n34_rank_pct)) + ' percentile') + ' of this season’s weeks</div><div class="kd"><span>4 w <span class="' + upDown(c4.n34a) + '">' + fnum(c4.n34a, 1) + '</span></span><span>8 w <span class="' + upDown(c8.n34a) + '">' + fnum(c8.n34a, 1) + '</span></span></div><div class="chgline">' + wk.small + '</div></div>' +
      '<div class="kpi"><div class="kn">' + term('oisst', 'daily OISST') + '</div><div class="kv">' + dy.big + '</div><div class="km">30 days ' + fnum(N.current30) + ', ' + term('rank', 'rank ' + N.all_years_rank) + ' of all years</div><div class="kd"><span>slope ' + fnum(n34.slope14.now) + '</span><span>' + term('cusum', 'CUSUM') + ' ' + (n34.cusum.alarm ? 'alarm' : 'quiet') + '</span></div><div class="chgline">' + dy.small + '</div></div>' +
      '<div class="kpi"><div class="kn">' + term('oni', 'ONI official') + '</div><div class="kv">' + on.big + '<small>' + esc(ls) + '</small></div><div class="km">analogues: ' + [1982, 1997, 2015, 2023].map(function (y) { return y + ' ' + fnum((ONI.analogs[y] || {})[ls]); }).join(', ') + '</div><div class="chgline">' + on.small + '</div></div>' +
      '<div class="kpi"><div class="kn">' + term('type', 'event type') + '</div><div class="kv" style="font-size:15px;line-height:1.25">' + esc(NW.type) + '</div><div class="km">' + term('nino12', '1+2') + ' ' + fnum(NW.latest.n12a, 1) + ' · ' + term('nino4', '4') + ' ' + fnum(NW.latest.n4a, 1) + ' · east−centre ' + fnum(NW.east_minus_central, 1) + '</div>' +
      (aw.n34a != null ? '<div class="chgline">' + (S.sub.cmp || '1997') + ' on this week: Niño 3.4 ' + fnum(aw.n34a, 1) + ', 1+2 ' + fnum(aw.n12a, 1) + '</div>' : '') + '</div>';
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
    var body = stageShell(title, [segBtn('models', 'plume', 'Plume', 'plume'), segBtn('models', 'board', 'Scoreboard', 'plume'),
      segBtn('models', 'breakdown', 'How they break', 'plume'), segBtn('models', 'revision', 'Revisions', 'plume')]);
    var i0 = IRI.seasons.indexOf(ao.season);

    if (k === 'plume') {
      plot(body, function (w, h) { return chartPlume(IRI, NW.latest.n34a, w, h); });
      var hist = (IRI.history || []).filter(function (h2) { return h2.combined; }).map(function (h2) { return h2.issued + ': ' + fnum(Math.max.apply(null, h2.combined.filter(fin))); });
      body.appendChild(el('div', 'cap', 'Each thin line is one model, coloured by its class: keeping up, lagging, broken. Thick is the combined mean, dashed the previous issue. The red dot is this week’s reality. Combined peak by issue: ' + hist.reverse().join(' → ') + '.'));
    } else if (k === 'breakdown') {
      plot(body, function (w, h) { return chartBreakdown(bd, w, h); });
      var rows = bd.by_issue || [];
      var chronic = (bd.chronic || []).filter(function (c) { return c.of >= 3; }).slice(0, 10);
      var tb = el('div', 'tbl-inline');
      tb.innerHTML = '<table class="e"><thead><tr><th>model</th><th>class</th><th>below reality</th><th>mean error</th><th>worst</th><th>since</th></tr></thead><tbody>' +
        chronic.map(function (c) {
          return '<tr><td>' + esc(c.model) + '</td><td><span class="cls ' + (c.cls || 'na') + '">' + ({ ok: T.okC, lag: T.lagC, broke: T.brokeC }[c.cls] || T.naC) + '</span></td>' +
            '<td class="num">' + c.issues_low + ' / ' + c.of + '</td><td class="num">' + fnum(c.mean_err) + '</td><td class="num' + ((c.worst_err || 0) <= -1 ? ' top' : '') + '">' + fnum(c.worst_err) + '</td><td>' + esc(c.since || '—') + '</td></tr>';
        }).join('') + '</tbody></table>';
      body.appendChild(tb);
      body.appendChild(el('div', 'cap', 'For every stored issue we take its nearest season that now has an official ONI and count the models that came in below it. ' + (rows.length ? 'From ' + esc(rows[0].issue) + ' (' + rows[0].share + ' %) to ' + esc(rows[rows.length - 1].issue) + ' (' + rows[rows.length - 1].share + ' %). ' : '') + esc(bd.note || '')));
    } else if (k === 'revision') {
      var rrows = (rv.rows || []).slice(0, 40);
      plot(body, function (w, h) {
        var W = w, Hh = h, Lp = 46, R = 20, Tp = topPad(w), B = 26, pw = W - Lp - R, ph = Hh - Tp - B;
        var vals = []; rrows.forEach(function (r) { if (fin(r.peak_prev)) vals.push(r.peak_prev); if (fin(r.peak_cur)) vals.push(r.peak_cur); });
        if (!vals.length) return svgOpen(W, Hh) + '<text x="20" y="40">no previous issue to compare</text></svg>';
        var vmin = Math.min.apply(null, vals) - .2, vmax = Math.max.apply(null, vals) + .2;
        var X = function (i) { return Lp + (rrows.length < 2 ? pw / 2 : i / (rrows.length - 1) * pw); };
        var Y = function (v) { return Tp + (vmax - v) / (vmax - vmin) * ph; };
        var s = svgOpen(W, Hh) + '<text class="tt" x="' + Lp + '" y="13">Peak revision by model, ' + esc(rv.prev_issued || '') + ' → ' + esc(IRI.issued) + ' (°C)</text>';
        s += gridY(vmin, vmax, .5, Y, Lp, R, W, 1);
        rrows.forEach(function (r, i) {
          if (!fin(r.peak_prev) || !fin(r.peak_cur)) return;
          var up = r.peak_cur >= r.peak_prev;
          s += '<line x1="' + X(i).toFixed(1) + '" y1="' + Y(r.peak_prev).toFixed(1) + '" x2="' + X(i).toFixed(1) + '" y2="' + Y(r.peak_cur).toFixed(1) + '" style="stroke:' + (up ? 'var(--nino)' : 'var(--nina)') + '" stroke-width="2" opacity=".7"/>';
          s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(r.peak_cur).toFixed(1) + '" r="3" style="fill:' + (up ? 'var(--nino)' : 'var(--nina)') + '"/>';
          s += '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(r.peak_prev).toFixed(1) + '" r="2" style="fill:var(--soft)"/>';
        });
        return s + '</svg>';
      });
      body.appendChild(el('div', 'cap', (rv.n ? rv.n_up + ' of ' + rv.n + ' models raised their peak, ' + rv.n_down + ' lowered it; the combined peak went ' + fnum(rv.combined_peak_prev) + ' → ' + fnum(rv.combined_peak_cur) + ' °C. ' : '') + 'When almost all models move the same way, they are catching up with the event rather than predicting it.'));
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
          return '<tr data-model="' + esc(r.name) + '"' + (S.model === r.name ? ' class="on"' : '') + '><td>' + esc(r.name) + '</td><td>' + (r.sec === 'dyn' ? 'dyn.' : 'stat.') + '</td>' + (tally ? '<td>' + cc + '</td>' : '') +
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
    tl.innerHTML = '<span><i style="background:var(--nino)"></i>below reality ' + ao.below.length + (P && fin(P.iri_below) ? ' ' + chg(ao.below.length, P.iri_below, 0) : '') + '</span>' +
      '<span><i style="background:var(--ok)"></i>above ' + ao.above.length + '</span>' +
      (tally ? '<span><i style="background:var(--ok)"></i>' + T.okC + ' ' + tally.ok + '</span><span><i style="background:var(--lv3)"></i>' + T.lagC + ' ' + tally.lag + '</span><span><i style="background:var(--lv5)"></i>' + T.brokeC + ' ' + tally.broke + '</span>' : '') +
      '<span>model mean ' + fnum(ao.mean) + ' ± ' + fnum(ao.sd, 2, false) + (P && fin(P.iri_mean) ? ' ' + chg(ao.mean, P.iri_mean) : '') + '</span>';
    body.appendChild(tl);
  }

  function viewTrend() {
    var D = S.D, W = D.watch, P = S.P;
    var k = sub('trend', 'sst_nino34');
    var opts = [['sst_nino34', 'Niño 3.4'], ['sst_world', 'Ocean'], ['t2_world', 'Land+ocean'], ['index', 'Our index'], ['months', '13 months']];
    var body = stageShell('The world ocean has broken daily records for ' + W.sst_world.records.streak + ' days running, land+ocean for ' + W.t2_world.records.streak,
      opts.map(function (o) { return segBtn('trend', o[0], o[1], 'sst_nino34'); }));
    if (k === 'index') {
      plot(body, function (w, h) { return chartHistory(S.H, w, h); });
      body.appendChild(el('div', 'cap', 'Every update leaves a snapshot; the lines are built from snapshots and deleting any one of them breaks nothing. ' + S.H.length + ' snapshots so far.'));
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
      plot(body, function (w, h) { return chartRecent(w0, w, h); });
      var lv = pair(w0.last_value, P && P.daily ? P.daily[k] : null, 2, '°C');
      var p50 = pair(w0.forecast14.p50, P && P.p50 ? P.p50[k] : null, 2, '°C');
      var kp = el('div', 'kpis');
      kp.innerHTML = '<div class="kpi"><div class="kn">last day</div><div class="kv">' + lv.big + '</div><div class="km">to ' + esc(w0.last_date) + '; 30 days ' + fnum(w0.level30.anom) + ', ' + term('rank', 'rank ' + w0.level30.rank_raw + ' of ' + w0.level30.of) + '</div><div class="chgline">' + lv.small + '</div></div>' +
        '<div class="kpi"><div class="kn">' + term('analog', 'forecast +14 days') + '</div><div class="kv">' + p50.big + '</div><div class="km">' + term('p10p50p90', 'p10 … p90') + ': ' + fnum(w0.forecast14.p10) + ' … ' + fnum(w0.forecast14.p90) + '</div><div class="chgline">' + p50.small + '</div></div>' +
        '<div class="kpi"><div class="kn">records and CUSUM</div><div class="kv" style="font-size:17px">' + w0.records.streak + '<small>days in a row</small></div><div class="km">' + w0.records.last30 + ' record days of 30; ' + term('cusum', 'CUSUM') + ' ' + (w0.cusum.alarm ? 'alarm' : 'quiet') + ', ' + term('trend', 'above trend') + ' ' + fnum(w0.level30.det) + '</div>' +
        (P && P.records && fin(P.records[k]) ? '<div class="chgline">was ' + P.records[k] + ' at ' + esc(prevStamp()) + '</div>' : '') + '</div>';
      body.appendChild(kp);
    }
  }

  function viewFood() {
    var D = S.D, RG = D.regions && !D.regions.error ? D.regions : null, FO = D.food && !D.food.error ? D.food : null, P = S.P;
    var k = sub('food', 'regions');
    var scen = S.scenario || (RG && RG.current_scenario) || 'base';
    var segs2 = [segBtn('food', 'regions', 'Regions', 'regions')];
    if (FO) segs2.push(segBtn('food', 'prices', 'Food prices', 'regions'), segBtn('food', 'onset', 'Since onset', 'regions'));
    var high = RG ? RG.items.filter(function (r) { return r.levels[scen] >= 4; }).length : 0;
    var body = stageShell(RG ? (high + ' of ' + RG.items.length + ' regions at level 4–5 under the “' + scen + '” scenario')
      : 'What it means for food in your part of the world', segs2);

    if (k === 'prices' && FO) {
      plot(body, function (w, h) { return chartFood(FO, w, h); });
      var G2 = FO.groups;
      body.appendChild(el('div', 'cap', 'Index ' + fnum(FO.index, 1, false) + ' in ' + esc(FO.last_month) + ': month ' + fnum(FO.mom, 1) + ', year ' + fnum(FO.yoy_pct, 1) + ' %. Year on year: ' + Object.keys(G2).map(function (g) { return g.toLowerCase() + ' ' + fnum(G2[g].yoy_pct, 1) + ' %'; }).join(', ') + '.'));
    } else if (k === 'onset' && FO && FO.overlay && FO.overlay.current) {
      plot(body, function (w, h) { return chartOverlay(FO.overlay, w, h); });
      body.appendChild(el('div', 'cap', 'The index as a percentage of its value in the onset month (' + esc(FO.overlay.onset) + ' = 100, the first three-month season with ONI ≥ +0.5). Past events are not a forecast: 1997-98 came with the Asian crisis, 2015-16 with cheap oil, 2023-24 after the Ukraine price spike.'));
    } else if (RG) {
      var sup = RG.scenario_support || {};
      var lead = el('div', 'lead');
      lead.innerHTML = 'Scenario: ' + ['base', 'strong', 'record'].map(function (c) {
        var sc = sup[c] || {};
        var pay = { name: c + ' scenario', def: (sc.what ? sc.what[0].toUpperCase() + sc.what.slice(1) + '. ' : '') + (sc.threshold != null ? 'Threshold on the Niño 3.4 peak: ' + fnum(sc.threshold) + ' °C; ' + sc.models_at_or_above + ' of ' + sc.of + ' models reach it, that is ' + sc.share + ' %. ' : '') + (sup._note || ''), src: 'IRI plume, model peaks', date: (D.iri || {}).issued };
        return '<span class="scen' + (c === scen ? ' on' : '') + '" data-scen="' + c + '" data-src="' + esc(JSON.stringify(pay)) + '">' + c + (sc.share != null ? ' <b>' + sc.share + ' %</b>' : '') + '</span>';
      }).join(' ') + ' — the share is how many of the ' + ((sup.base || {}).of || '—') + ' models reach that peak, not a probability.';
      lead.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('[data-scen]');
        if (t) { S.scenario = t.getAttribute('data-scen'); render(); }
      });
      body.appendChild(lead);
      var IMP = { dry: ['drought', 'var(--lv3)'], heat: ['heat', 'var(--lv4)'], wet: ['wet', 'var(--nina)'], flood: ['floods', 'var(--nina)'], none: ['no signal', 'var(--lv2)'] };
      var notes = RG.season_notes || {};
      var wrap = el('div'); wrap.style.cssText = 'flex:1;min-height:0;overflow:auto';
      var items = RG.items.slice().sort(function (a, b) { return b.levels[scen] - a.levels[scen] || b.vulnerability.level - a.vulnerability.level; });
      wrap.innerHTML = '<table class="e regions"><thead><tr><th>region</th>' +
        RG.seasons.map(function (s2) { return '<th>' + src({ name: s2, def: notes[s2] || '', src: 'three-month season, the same convention as ONI', date: RG.as_of }, s2) + '</th>'; }).join('') +
        '<th>' + src({ name: 'Food vulnerability', def: 'Five bars: how exposed the region is through food — the share of imports in cereal consumption and the size of the population close to the margin. Point at a region name for the detail and the source.', src: 'FAO / World Bank', date: RG.as_of }, 'food') + '</th>' +
        ['base', 'strong', 'record'].map(function (c) {
          var sc = (RG.scenario_support || {})[c] || {};
          return '<th data-scen="' + c + '"' + (c === scen ? ' class="sorted"' : '') + '>' + src({ name: c + ' scenario', def: (sc.what || '') + (sc.threshold != null ? '. Peak threshold ' + fnum(sc.threshold) + ' °C, reached by ' + sc.models_at_or_above + ' of ' + sc.of + ' models (' + sc.share + ' %). ' : '. ') + ((RG.scenario_support || {})._note || ''), src: 'IRI plume', date: (D.iri || {}).issued }, c) + '</th>';
        }).join('') + '<th>what to do</th></tr></thead><tbody>' +
        items.map(function (r) {
          var was = P && P.regions ? (P.regions[r.id] || {})[scen] : null;
          var cells = RG.seasons.map(function (s2) {
            var x = r.seasons[s2] || {}, im = IMP[x.impact] || IMP.none;
            var pay = { name: r.name + ' · ' + s2, def: x.note || 'No consistent signal for this season.', src: r.sources.join(' · '), date: RG.as_of };
            return '<td><span class="imp" data-src="' + esc(JSON.stringify(pay)) + '" style="--c:' + im[1] + '">' + im[0] + (x.impact && x.impact !== 'none' ? ' <small>' + esc(x.strength || '') + '</small>' : '') + '</span></td>';
          }).join('');
          var vb = '<span class="vbar">' + [1, 2, 3, 4, 5].map(function (i) { return '<i' + (i <= r.vulnerability.level ? ' class="on"' : '') + '></i>'; }).join('') + '</span>';
          var lv = ['base', 'strong', 'record'].map(function (c) {
            var d2 = (c === scen && fin(was) && was !== r.levels[c]) ? '<sup>' + (r.levels[c] > was ? '+' : '−') + '</sup>' : '';
            return '<td class="num"><span class="lvl' + (c === scen ? ' cur' : '') + '" style="background:' + lvlColor(r.levels[c]) + '">' + r.levels[c] + '</span>' + d2 + '</td>';
          }).join('');
          return '<tr><td>' + src({ name: r.name, def: r.countries + '. Vulnerability ' + r.vulnerability.level + ' of 5: ' + r.vulnerability.note + (r.vulnerability.importers && r.vulnerability.importers.length ? ' Net importers: ' + r.vulnerability.importers.join(', ') + '.' : ''), src: r.sources.join(' · '), date: RG.as_of }, r.name) +
            '<div class="sub">' + esc(r.countries) + '</div></td>' + cells + '<td>' + vb + '</td>' + lv + '<td class="act">' + r.actions.map(function (a) { return '<div>' + esc(a) + '</div>'; }).join('') + '</td></tr>';
        }).join('') + '</tbody></table>';
      wrap.addEventListener('click', function (e) {
        var th = e.target.closest && e.target.closest('th[data-scen]');
        if (th) { S.scenario = th.getAttribute('data-scen'); render(); }
      });
      body.appendChild(wrap);
      body.appendChild(el('div', 'cap', 'Impacts are typical for a strong eastern-type El Niño, from published NOAA CPC and IRI impact maps, FAO GIEWS alerts and the regional literature: “usually”, never “will”. Click a scenario to switch the highlighted column.'));
    } else {
      body.appendChild(el('div', 'note warn', 'Regions block failed: ' + esc((D.regions || {}).error || 'no data')));
    }

    if (FO && k === 'regions') {
      var kp = el('div', 'kpis'), G3 = FO.groups;
      var fi = pair(FO.index, P ? P.food_index : null, 1, '');
      var worst = Object.keys(G3).sort(function (a, b) { return (G3[b].yoy_pct || 0) - (G3[a].yoy_pct || 0); })[0];
      kp.innerHTML = '<div class="kpi"><div class="kn">' + term('fao', 'FAO food price index') + '</div><div class="kv">' + fi.big + '<small>' + esc(FO.last_month) + '</small></div><div class="km">month ' + fnum(FO.mom, 1) + ' · year ' + fnum(FO.yoy_pct, 1) + ' %</div><div class="chgline">' + fi.small + '</div></div>' +
        '<div class="kpi"><div class="kn">strongest rise, year on year</div><div class="kv" style="font-size:17px">' + esc(worst) + '<small>' + fnum(G3[worst].yoy_pct, 1) + ' %</small></div><div class="km">' + esc(worst) + ' index ' + fnum(G3[worst].last, 1, false) + (P && P.food_groups && fin(P.food_groups[worst]) ? ', ' + chg(G3[worst].last, P.food_groups[worst], 1) + ' since ' + esc(prevStamp()) : '') + '</div></div>' +
        '<div class="kpi"><div class="kn">scenario in force</div><div class="kv" style="font-size:17px">' + esc(RG ? RG.current_scenario : '—') + '</div><div class="km">chosen by the data: where reality sits against the model spread</div></div>';
      body.appendChild(kp);
    }
  }

  function viewHow() {
    var D = S.D, gl = S.G;
    var k = sub('how', 'glossary');
    var body = stageShell('Glossary, method, sources', [segBtn('how', 'glossary', 'Glossary', 'glossary'), segBtn('how', 'method', 'Method', 'glossary'), segBtn('how', 'sources', 'Sources', 'glossary'), segBtn('how', 'changed', 'What changed', 'glossary')]);
    body.classList.add('scroll');
    if (k === 'glossary') {
      var g = el('div', 'gloss');
      Object.keys(gl).forEach(function (key) { var x = gl[key]; g.innerHTML += '<div class="gl-i"><b>' + esc(x.name) + '</b>' + esc(x.def) + '<div class="why">' + esc(x.why) + '</div><div class="s">' + esc(x.src) + '</div></div>'; });
      body.appendChild(g);
    } else if (k === 'sources') {
      var t = el('table', 'e');
      t.innerHTML = '<thead><tr><th>series</th><th>what it is</th><th>freshness</th></tr></thead><tbody>' +
        Object.keys(D.sources).map(function (key) { var v = D.sources[key]; return '<tr><td>' + esc(key) + '</td><td>' + esc(v.label) + '</td><td' + (v.fresh ? '' : ' class="top"') + '>' + (v.fresh ? T.fresh : T.stale + ': ' + esc(v.error)) + '</td></tr>'; }).join('') + '</tbody>';
      body.appendChild(t);
      body.appendChild(el('div', 'cap', 'climatereanalyzer.org (ERA5 2 m; OISST v2.1) · NOAA CPC weekly Niño indices and ONI · NOAA PSL ERSST v6 monthly Niño 3.4 · IRI/CCSR model plume · FAO Food Price Index. The raw data of every update is stored verbatim with its date.'));
    } else if (k === 'changed') {
      body.appendChild(el('div', 'lead', (D.diff || []).map(function (d) { return '· ' + esc(d); }).join('<br>') || 'First update: nothing to compare with yet.'));
      if (S.P) body.appendChild(el('div', 'cap', 'The previous update was at ' + esc(S.P.stamp) + ': risk index ' + S.P.risk_index + ', ' + S.P.n_risks + ' risks, ' + S.P.n_alerts + ' alerts. Switch the header button to “change since last update” to see every number as a delta.'));
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
    body.appendChild(el('div', 'lead', '<b>Level ' + r.level + ' · ' + esc(r.horizon) + '.</b> ' + esc(r.plain || '') + (fin(was) && was !== r.level ? ' <i>Level was ' + was + ' at ' + esc(prevStamp()) + '.</i>' : '')));
    body.appendChild(el('div', 'note', '<strong>Evidence.</strong> ' + esc(r.evidence) + (r.metric ? '<br>' + dynWords(r.metric) : '')));
    body.appendChild(el('div', 'note warn', '<strong>Watch.</strong> ' + esc(r.watch)));
  }

  // ---------------------------------------------------------------- render
  function render() {
    var narrow = window.matchMedia('(max-width:900px)').matches;
    buildTabs();
    railState(); railRisks();
    var stage = $('stage'), L = $('railL'), R = $('railR');
    L.classList.toggle('show', narrow && S.view === 'state');
    R.classList.toggle('show', narrow && (S.view === 'risks' || S.view === 'risk'));
    stage.classList.toggle('hide', narrow && (S.view === 'state' || S.view === 'risks'));
    if (narrow && (S.view === 'state' || S.view === 'risks')) { S.draw = null; S.plotEl = null; return; }
    if (S.view === 'risk') viewRisk();
    else if (S.view === 'models') viewModels();
    else if (S.view === 'trend') viewTrend();
    else if (S.view === 'food') viewFood();
    else if (S.view === 'how') viewHow();
    else viewNow();
  }
  window.B42EnsoRedraw = function () { redrawPlot(); };

  // ---------------------------------------------------------------- dock + карточка у курсора
  function initDock() {
    var txt = $('dtxt'), tip = $('tip');
    function payloadOf(target) {
      var k = target.getAttribute('data-term');
      if (k && S.G[k]) { var g = S.G[k]; return { name: g.name, def: g.def, why: g.why, src: g.src }; }
      if (target.getAttribute('data-src')) { try { return JSON.parse(target.getAttribute('data-src')); } catch (e) { return null; } }
      return null;
    }
    function fill(p) {
      return '<b>' + esc(p.name || '') + '</b>' + esc(p.def || '') + (p.why ? ' ' + esc(p.why) : '') +
        (p.src || p.date ? '<span class="s">' + esc(p.src || '') + (p.date ? ' · ' + esc(p.date) : '') + '</span>' : '');
    }
    function place(e) {
      var pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
      var x = e.clientX + pad, y = e.clientY + pad;
      if (x + w > window.innerWidth - 8) x = e.clientX - w - pad;
      if (y + h > window.innerHeight - 8) y = e.clientY - h - pad;
      tip.style.left = Math.max(6, x) + 'px';
      tip.style.top = Math.max(6, y) + 'px';
    }
    function show(target, e) {
      var p = payloadOf(target);
      if (!p) return;
      txt.innerHTML = fill(p);
      tip.innerHTML = fill(p);
      tip.classList.add('on');
      if (e) place(e);
    }
    function hide() { tip.classList.remove('on'); if (!S.pinned) txt.innerHTML = '<span class="hint">' + T.dockHint + '</span>'; }
    function find(e) { return e.target.closest && e.target.closest('[data-term],[data-src]'); }
    document.addEventListener('mouseover', function (e) { var x = find(e); if (x) show(x, e); });
    document.addEventListener('mousemove', function (e) { if (tip.classList.contains('on')) place(e); });
    document.addEventListener('mouseout', function (e) { if (find(e)) hide(); });
    document.addEventListener('click', function (e) {
      var x = find(e);
      if (x) { S.pinned = (S.pinned === x ? null : x); if (S.pinned) show(x, e); else hide(); return; }
      if (S.pinned && !e.target.closest('#dock')) { S.pinned = null; hide(); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { S.pinned = null; hide(); } });
    hide();
  }

  // ---------------------------------------------------------------- go
  function get(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(u + ': ' + r.status); return r.json(); }); }
  Promise.all([get('/data/enso/latest.json'), get('/data/enso/glossary.json').catch(function () { return {}; }), get('/data/enso/history.json').catch(function () { return []; })])
    .then(function (r) {
      S.D = r[0]; S.G = (r[1] && r[1].en) || {}; S.H = r[2] || []; S.P = r[0].prev || null;
      var db = $('deltaBtn');
      if (db) db.onclick = function () { S.delta = !S.delta; render(); };
      buildMeta(); initDock(); render();
      var ro = new ResizeObserver(function () { redrawPlot(); });
      ro.observe($('stage'));
      var t = null;
      window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(render, 150); });
    })
    .catch(function (e) { $('stage').innerHTML = '<div class="e-empty">The data did not load: ' + esc(e.message) + '</div>'; });
})();
