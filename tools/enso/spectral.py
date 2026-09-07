# -*- coding: utf-8 -*-
"""Спектральный сторож: появление линии на периодах 2…7 суток в дневных рядах.

ЗАЧЕМ (владелец 07.09): «ищем не под фонарём, а просто появление сигнала на какой-то частоте;
пока его нет, и это хорошо, но он может быть». Гипотеза владельца: перед срывом системы на
пределе устойчивости в дневных рядах появляется гребёнка периодов 1, 2, 3 … 7 суток
(субгармоники суточного форсинга). Сторож не доказывает теорию, он смотрит: есть ли сейчас в
каком-нибудь ряду линия над шумом, которой раньше не было.

ЧТО СЧИТАЕТ. Для каждого дневного ряда окно последних 30 дней: линейный тренд снят, окно
Ханна, периодограмма с дополнением нулями до 120 точек (чтобы попасть на периоды ровно 2, 3, 4,
5, 6, 7 суток; разрешение остаётся 1/30 сут⁻¹, поэтому 6 и 7 суток различимы едва). Фон —
красный шум AR(1) с тем же лагом-1, что у окна; отношение мощности к фону на каждом периоде
распределено как χ²₂/2: порог 95 % ≈ 3.0, 99 % ≈ 4.6 (Торренс и Компо, 1998). Сутки в дневных
средних не видны (граница Найквиста двое суток) — для них нужны часовые данные, см. отчёт.

С ЧЕМ СРАВНИВАЕТ. (1) История: все 30-дневные окна ряда с шагом 5 дней (у рядов Climate
Reanalyzer с 1981/1940 года) — процентиль нынешнего максимума линии и доли полосы 2–7 суток.
(2) Наши годы: то же календарное окно в 1982, 1997, 2015, 2023 (аналоги) — «как там шумело».
(3) Ход за последние 180 дней с шагом 3 дня — для графика и для правила устойчивости: сигналом
считаем линию ≥ 99 % над красным фоном, стоящую на том же периоде два обновления подряд и
выше 95-го процентиля истории (где история есть).

ВЫХОД: data/enso/spectral.json; запись в журнал прогонов (ops). Запуск: python spectral.py
(в ежедневной обёртке light_daily.ps1). Только numpy, без сети, кроме буёв TAO (последние
60 дней, поверхность), которые тянутся с ERDDAP и при отказе пропускаются.
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
LG = ROOT / "last_good"
OUT = ROOT / "spectral.json"
W = 30                      # окно, дней
PAD = 120                   # дополнение нулями: периоды 2,3,4,5,6,7 попадают в бины 60,40,30,24,20,17
PERIODS = [2, 3, 4, 5, 6, 7]
ANALOG_YEARS = [1982, 1997, 2015, 2023]
CHI95, CHI99, CHI999 = 3.0, 4.6, 6.9     # χ²₂/2 квантили: 95 %, 99 %, 99.9 %
PERSIST = 3                 # обновлений подряд (шаг 3 дня) на том же периоде
STEP_HIST, STEP_TRACK, TRACK_DAYS = 5, 3, 180


# ── загрузка рядов ────────────────────────────────────────────────────────────────────────
def _cr(name):
    """Climate Reanalyzer: список годов по 366 значений → (dates, values) непрерывно."""
    raw = json.load(open(LG / f"{name}.json", encoding="utf-8"))
    ys = {int(x["name"]): x["data"] for x in raw if str(x.get("name", "")).isdigit()}
    dates, vals = [], []
    for y in range(min(ys), max(ys) + 1):
        arr = ys.get(y) or []
        for i in range(366):
            d0 = date(y, 1, 1) + timedelta(days=i)
            if d0.year != y:
                break
            v = arr[i] if i < len(arr) else None
            dates.append(d0); vals.append(np.nan if v is None else float(v))
    return np.array(dates), np.array(vals, float)


def _doy_series(year, arr366):
    """Годовой массив по дню года → (dates, values)."""
    dates, vals = [], []
    for i in range(366):
        d0 = date(year, 1, 1) + timedelta(days=i)
        if d0.year != year:
            break
        v = arr366[i] if i < len(arr366) else None
        dates.append(d0); vals.append(np.nan if v is None else float(v))
    return np.array(dates), np.array(vals, float)


def _dict_series(d):
    ks = sorted(k for k, v in d.items() if v is not None)
    return np.array([date.fromisoformat(k) for k in ks]), np.array([float(d[k]) for k in ks])


def _oisst_box(box):
    cur = json.load(open(ROOT / "oisst" / f"{box}.json", encoding="utf-8")).get("sst") or {}
    cl = json.load(open(ROOT / "oisst" / f"clim_{box}.json", encoding="utf-8"))
    analogs = {int(y): _doy_series(int(y), a) for y, a in (cl.get("analogs") or {}).items()}
    return _dict_series(cur), analogs


def _era5_wind():
    cur = json.load(open(ROOT / "wind" / "era5_recent.json", encoding="utf-8")).get("u") or {}
    an = json.load(open(ROOT / "wind" / "analogs_era5.json", encoding="utf-8"))
    return _dict_series(cur), {int(y): _doy_series(int(y), a) for y, a in an.items()}


# РЕГИОНЫ СУШИ (владелец 07.09: «средней температуры по регионам нет, кроме регионов Эль-Ниньо»).
# ERA5 по дням через Open-Meteo, одна точка на регион, с 1981 года; склад data/enso/spectral/<ключ>.json,
# при каждом прогоне дотягиваются последние 90 дней. История даёт процентиль и те же годы-аналоги.
REGIONS = [("kuwait", "Kuwait, 2 m air (ERA5)", 29.35, 47.96), ("europe", "Central Europe 50°N 10°E, 2 m air", 50.0, 10.0),
           ("lima", "Lima, Peru coast, 2 m air", -12.05, -77.04), ("jakarta", "Jakarta, 2 m air", -6.2, 106.8),
           ("nairobi", "Nairobi, East Africa, 2 m air", -1.29, 36.82), ("delhi", "Delhi, India, 2 m air", 28.6, 77.2)]
RCACHE = ROOT / "spectral"


def _om(lat, lon, d0, d1):
    import urllib.request
    u = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={d0}&end_date={d1}"
         "&daily=temperature_2m_mean&timezone=UTC")
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "bridge42worlds enso"}), timeout=120) as r:
        d = json.loads(r.read().decode("utf-8"))["daily"]
    return {t: v for t, v in zip(d["time"], d["temperature_2m_mean"]) if v is not None}


def _region(key, lat, lon):
    RCACHE.mkdir(parents=True, exist_ok=True)
    p = RCACHE / f"{key}.json"
    m = json.load(open(p, encoding="utf-8")) if p.exists() else {}
    today = date.today()
    err = None
    for attempt in range(3):                                     # Open-Meteo иногда отдаёт пустой ответ: три попытки
        try:
            d0 = "1981-01-01" if not m else (today - timedelta(days=90)).isoformat()
            m.update(_om(lat, lon, d0, today.isoformat()))
            p.write_text(json.dumps(m), encoding="utf-8")
            err = None
            break
        except Exception as e:                                   # noqa: BLE001
            err = e
            time.sleep(5)
    if err is not None and not m:
        raise err
    d, v = _dict_series(m)
    yrs = np.array([x.year for x in d])
    analogs = {y: (d[yrs == y], v[yrs == y]) for y in ANALOG_YEARS if (yrs == y).any()}
    return (d, v), analogs


def _tao_surface(days=60):
    """Поверхностная температура буёв TAO за последние дни (сеть; при отказе пусто)."""
    out = {}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import subsurface as SB
        t0 = (date.today() - timedelta(days=days)).isoformat()
        for name, lon in SB.STATIONS:
            try:
                rows = SB._tao_rows(lon, t0, timeout=60)
            except Exception:                                    # noqa: BLE001
                continue
            m = {}
            for d0, prof in rows.items():
                pr = SB._profile(prof)
                if pr is not None and np.isfinite(pr[0]):
                    m[d0] = float(pr[0])
            if len(m) >= W:
                out[f"tao_{name}"] = (f"TAO {SB.lon_label(lon)}, surface", _dict_series(m))
    except Exception:                                            # noqa: BLE001
        pass
    return out


# ── спектр окна ───────────────────────────────────────────────────────────────────────────
def window_stats(x):
    """x: 30 дневных значений (могут быть nan). → dict линий и полосы, или None."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    if ok.sum() < W - 3:
        return None
    t = np.arange(len(x))
    p = np.polyfit(t[ok], x[ok], 1)
    r = np.where(ok, x - np.polyval(p, t), 0.0)
    sd = r[ok].std()
    if sd < 1e-9:
        return None
    a1 = float(np.corrcoef(r[:-1], r[1:])[0, 1]) if len(r) > 2 else 0.0
    a1 = min(max(a1, 0.0), 0.98)
    w = np.hanning(len(r))
    X = np.fft.rfft(r * w, n=PAD)
    f = np.fft.rfftfreq(PAD, d=1.0)
    P = np.abs(X) ** 2
    bg = (1 - a1 ** 2) / (1 - 2 * a1 * np.cos(2 * np.pi * f) + a1 ** 2)
    # нормировка фона на среднюю мощность (бины 1..Найквист)
    bg = bg * (P[1:].mean() / bg[1:].mean())
    ratio = P / bg
    lines = {}
    for per in PERIODS:
        i = int(round(PAD / per))
        lines[str(per)] = round(float(ratio[i]), 2)
    band = (f >= 1 / 7) & (f <= 1 / 2)
    share = float(P[band].sum() / P[1:].sum())
    best = max(lines, key=lambda k: lines[k])
    # гребёнка: сколько НЕЗАВИСИМЫХ линий ≥ 95 % (соседние периоды при разрешении 1/30 — один широкий пик)
    hot = sorted(int(k) for k, v in lines.items() if v >= CHI95)
    comb, last = 0, -9
    for per in hot:
        if per - last >= 2:
            comb += 1; last = per
    return {"lines": lines, "max_line": lines[best], "max_period": int(best), "band_share": round(share, 3),
            "comb": comb, "ar1": round(a1, 2), "sd": round(float(sd), 3)}


def _window_at(dates, vals, end):
    """Окно из W дней, заканчивающееся датой end (включительно)."""
    idx = {d: i for i, d in enumerate(dates)}
    xs = []
    for k in range(W - 1, -1, -1):
        d0 = end - timedelta(days=k)
        i = idx.get(d0)
        xs.append(vals[i] if i is not None else np.nan)
    return np.array(xs)


def analyze(name, label, cur, analogs, history=None):
    dates, vals = cur
    if len(dates) < W:
        return {"key": name, "label": label, "error": f"only {len(dates)} days"}
    end = dates[-1]
    now = window_stats(_window_at(dates, vals, end))
    if not now:
        return {"key": name, "label": label, "error": "window too sparse"}
    out = {"key": name, "label": label, "window": [str(end - timedelta(days=W - 1)), str(end)], "now": now}
    # ход за последние 180 дней
    track = []
    src_d, src_v = (history if history is not None else cur)
    for k in range(TRACK_DAYS, -1, -STEP_TRACK):
        e = end - timedelta(days=k)
        st = window_stats(_window_at(src_d, src_v, e))
        if st:
            track.append({"end": str(e), "max_line": st["max_line"], "max_period": st["max_period"], "band_share": st["band_share"]})
    out["track"] = track
    # устойчивость: тот же период (±1 сутки) ≥ 99 % PERSIST обновлений подряд
    if len(track) >= PERSIST:
        tail = track[-PERSIST:]
        out["persistent"] = all(t["max_line"] >= CHI99 and abs(t["max_period"] - tail[-1]["max_period"]) <= 1 for t in tail)
        out["persist_updates"] = sum(1 for t in track[::-1] if t["max_line"] >= CHI99 and abs(t["max_period"] - track[-1]["max_period"]) <= 1)
    # история: все окна ряда
    if history is not None:
        hd, hv = history
        mx, sh = [], []
        for k in range(len(hd) - 1, W, -STEP_HIST):
            st = window_stats(hv[k - W + 1:k + 1])
            if st:
                mx.append(st["max_line"]); sh.append(st["band_share"])
        if mx:
            mx = np.array(mx); sh = np.array(sh)
            out["history"] = {"windows": int(len(mx)), "max_line_pct": round(float((mx < now["max_line"]).mean() * 100)),
                              "band_share_pct": round(float((sh < now["band_share"]).mean() * 100)),
                              "max_line_p95": round(float(np.percentile(mx, 95)), 2),
                              "share_of_windows_with_line_99": round(float((mx >= CHI99).mean() * 100))}
    # наши годы: то же календарное окно
    an = {}
    for y, (ad, av) in (analogs or {}).items():
        try:
            e = end.replace(year=y)
        except ValueError:
            e = end.replace(year=y, day=28)
        st = window_stats(_window_at(ad, av, e))
        if st:
            an[str(y)] = {"lines": st["lines"], "max_line": st["max_line"], "max_period": st["max_period"], "band_share": st["band_share"]}
    if an:
        out["analogs"] = an
    # ПРИГОВОР ПРАВИЛАМИ, с поправкой на множественность: у каждого ряда 7 % окон истории несут
    # линию ≥ 99 % по чистой случайности, на два десятка рядов это одна-две «линии» всегда. Поэтому
    # «signal» требует либо очень сильной линии (99.9 %), либо гребёнки из двух независимых линий,
    # и в обоих случаях устойчивости PERSIST обновлений и верхнего процентиля истории.
    ml = now["max_line"]
    hist_ok = ("history" not in out) or out["history"]["max_line_pct"] >= 99
    strong = ml >= CHI999 or now["comb"] >= 2
    if strong and out.get("persistent") and hist_ok:
        out["verdict"] = "signal"
    elif ml >= CHI99:
        out["verdict"] = "candidate"
    elif ml >= CHI95:
        out["verdict"] = "weak"
    else:
        out["verdict"] = "none"
    return out


def build(verbose=True):
    t0 = time.time()
    series = []
    # ряды с полной историей (Climate Reanalyzer)
    for key, label in [("sst_nino34", "Niño 3.4 SST, daily (OISST via Climate Reanalyzer)"),
                       ("sst_world", "World SST 60°S–60°N, daily"),
                       ("t2_world", "World 2 m air, daily (ERA5)"), ("t2_nh", "Northern Hemisphere 2 m air"),
                       ("t2_sh", "Southern Hemisphere 2 m air")]:
        try:
            d, v = _cr(key)
            ok = np.isfinite(v)
            last = np.where(ok)[0][-1]
            cur = (d[: last + 1], v[: last + 1])
            analogs = {y: (d[(np.array([x.year for x in d]) == y)], v[(np.array([x.year for x in d]) == y)]) for y in ANALOG_YEARS}
            series.append(analyze(key, label, cur, analogs, history=cur))
        except Exception as e:                                   # noqa: BLE001
            series.append({"key": key, "label": label, "error": str(e)[:120]})
    # наши боксы OISST: текущий год + аналоги по календарю
    for box, label in [("nino12", "Niño 1+2, own OISST box"), ("nino3", "Niño 3, own OISST box"),
                       ("nino4", "Niño 4, own OISST box"), ("gulf", "Persian Gulf, own OISST box")]:
        try:
            cur, an = _oisst_box(box)
            series.append(analyze("oisst_" + box, label, cur, an))
        except Exception as e:                                   # noqa: BLE001
            series.append({"key": "oisst_" + box, "label": label, "error": str(e)[:120]})
    try:
        cur, an = _era5_wind()
        series.append(analyze("wind_west", "Zonal wind 850 hPa, 130°E–180°, daily (ERA5)", cur, an))
    except Exception as e:                                       # noqa: BLE001
        series.append({"key": "wind_west", "label": "wind", "error": str(e)[:120]})
    for key, label, lat, lon in REGIONS:
        try:
            cur, an = _region(key, lat, lon)
            series.append(analyze("land_" + key, label, cur, an, history=cur))
        except Exception as e:                                   # noqa: BLE001
            series.append({"key": "land_" + key, "label": label, "error": str(e)[:120]})
        time.sleep(1.0)
    for key, (label, cur) in _tao_surface().items():
        series.append(analyze(key, label, cur, {}))
    n_sig = [s["key"] for s in series if s.get("verdict") == "signal"]
    n_cand = [s["key"] for s in series if s.get("verdict") == "candidate"]
    # сколько линий ≥ 99 % ждать по случайности: сумма долей по рядам с историей, у остальных средняя доля
    shares = [s["history"]["share_of_windows_with_line_99"] / 100.0 for s in series if s.get("history")]
    mean_share = float(np.mean(shares)) if shares else 0.07
    expected = sum((s["history"]["share_of_windows_with_line_99"] / 100.0) if s.get("history") else mean_share
                   for s in series if not s.get("error"))
    n99 = sum(1 for s in series if s.get("now") and s["now"]["max_line"] >= CHI99)
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "window_days": W, "periods": PERIODS,
           "thresholds": {"chi95": CHI95, "chi99": CHI99},
           "series": series, "signals": n_sig, "candidates": n_cand,
           "lines_99_now": n99, "lines_99_expected_by_chance": round(expected, 1),
           "summary": (f"{len(series)} daily series scanned for a line at 2–7 days over the last {W} days: "
                       + (f"no signal; {n99} line(s) at 99 % against {expected:.1f} expected by chance"
                          + (", candidates: " + ", ".join(n_cand) if n_cand else "") if not n_sig else
                          "SIGNAL in " + ", ".join(n_sig)) + "."),
           "note": ("A watch, not a proof: for each daily series the last 30 days are tested for a spectral line at "
                    "2, 3, 4, 5, 6 or 7 days above a red-noise background (χ² test, 95 % ≈ 3.0, 99 % ≈ 4.6). One day "
                    "is invisible in daily means (Nyquist); 6 and 7 days are barely separable in a 30-day window. "
                    "By chance alone about 7 % of 30-day windows carry a 99 % line, so with two dozen series one or "
                    "two such lines are always present; a line counts as a signal only if it is very strong (99.9 %) "
                    "or forms a comb of two independent periods, holds on the same period three updates running "
                    "(nine days) and, where history exists, sits above the 99th percentile of all past windows. Analog years show how the "
                    "same calendar window looked in 1982, 1997, 2015 and 2023."),
           "secs": int(time.time() - t0)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"spectral.json: {len(series)} рядов, {doc['secs']} с")
        for s in series:
            if s.get("error"):
                print(f"  {s['key']:<14} —  {s['error']}"); continue
            nw = s["now"]; h = s.get("history") or {}
            an = " | ".join(f"{y}:{a['max_line']:.1f}@{a['max_period']}d" for y, a in (s.get("analogs") or {}).items())
            print(f"  {s['key']:<14} {s['verdict']:<9} max {nw['max_line']:>5.1f} @ {nw['max_period']} d  lines " +
                  " ".join(f"{p}d:{nw['lines'][str(p)]:.1f}" for p in PERIODS) +
                  f"  band {nw['band_share']:.3f}" + (f"  hist pct {h['max_line_pct']}% (p95 {h['max_line_p95']})" if h else "") +
                  (f"  analogs {an}" if an else ""))
        print(" ", doc["summary"])
    try:
        import ops as OPSLOG
        OPSLOG.record_run("spectral", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "ok" if not [s for s in series if s.get("error")] else "partial", note=doc["summary"][:160])
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print("  ops:", str(e)[:80])
    return doc


if __name__ == "__main__":
    build()
