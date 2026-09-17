# -*- coding: utf-8 -*-
"""Опасность высшего уровня: не «сильное событие», а смена режима.

Владелец 15.09: «нужна такая метрика, опасность высшего уровня, типа фазовый переход —
отдельная страница, отдельная метрика, отдельная оценка, пусть субъективно, пусть с
рассуждениями, но честно».

ЧТО ЗДЕСЬ МЕРЯЕТСЯ И ЧЕГО ЗДЕСЬ НЕТ. Рекорд — это положение НА кривой. Смену режима выдаёт
разладка самой кривой: связи, по которым система жила, перестают держать. Поэтому здесь нет ни
одного «уровня» — ни температуры, ни индекса. Здесь только связи, память ряда и запас обратного
хода. Сильнейшее в истории событие может пройти целиком внутри старого режима, а слабое —
случиться уже в новом.

ПЯТЬ ЧАСТЕЙ, КАЖДАЯ ИЗМЕРЕНА ОТДЕЛЬНО:

  1. ПАМЯТЬ РЯДА (критическое замедление). Классический предвестник: перед срывом система всё
     медленнее возвращается к своему среднему, и это видно как рост связи соседних значений и
     рост разброса. Считается по трём рядам разной длины и разного шага, чтобы одна прихоть
     обработки не решала за всех.
  2. СВЯЗЬ МОРЕ → ВОЗДУХ. Наклон зависимости «температура Niño 3.4 → глубокая конвекция»,
     подогнанный по двум десяткам лет, и остаток этого года от него. Считает внешний сборщик
     радиансов, здесь только читается и оценивается.
  3. СЦЕПКА. Три признака того, что воздух вообще отвечает океану: давление поперёк Тихого,
     башня облака над линией смены дат, пассаты. Когда они перестают отвечать — событие
     перестаёт быть Эль-Ниньо в обычном смысле.
  4. ВОЗВРАЩАЮЩАЯ СИЛА. У колебания она есть: разрядка тёплого объёма. Если топливо горит и
     система качается назад — это колебание, каким бы сильным ни было. Если объём стоит на
     рекорде, а качка не приходит — вот это и есть вопрос.
  5. РАБОТА ВНЕ ДИАПАЗОНА. Насколько сегодня система вышла за пределы, на которых подогнаны
     наши собственные инструменты. Это не свойство природы, это честность о нас: за краем
     подгонки любой прогноз становится экстраполяцией.

ОЦЕНКА СУБЪЕКТИВНА, И ЭТО НАПИСАНО НА ЭКРАНЕ. Складывать пять разнородных признаков в одно
число «научно» нельзя: никто не измерил их веса. Поэтому уровень ставится правилом, правило
написано словами рядом, а каждая часть показана своим числом, чтобы читатель мог не согласиться
с итогом, не отказываясь от данных.

ЧЕГО ЭТА СТРАНИЦА НЕ ЗНАЕТ. Два экваториальных бокса — это 0,4 % поверхности планеты. Ни один
из оценённых элементов климатической системы (лёд Гренландии, АМОК, Амазония, вечная мерзлота)
здесь первым не проявится. Это сторож тропической Пацифики, а не всей системы, и так и подписан.

    python tools/enso/phase.py            посчитать и записать phase.json
    python tools/enso/phase.py --show     напечатать разбор в консоль
"""
import argparse
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
LAST = ROOT / "last_good"
OUT = ROOT / "phase.json"

MON = dict(JAN=1, FEB=2, MAR=3, APR=4, MAY=5, JUN=6, JUL=7, AUG=8, SEP=9, OCT=10, NOV=11, DEC=12)
WROW = re.compile(r"^\s*(\d{2})([A-Z]{3})(\d{4})\s+(.*)$")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


# ── ЧТЕНИЕ РЯДОВ ────────────────────────────────────────────────────────────────────────────
def read_psl_monthly(p=LAST / "psl_nino34_monthly.txt"):
    """Niño 3.4 помесячно с 1948 года (PSL). Самый длинный наш ряд самого события."""
    if not p.exists():
        return None
    vals, dates = [], []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*(\d{4})\s+(-?\d+\.\d+(?:\s+-?\d+\.\d+){11})\s*$", line)
        if not m:
            continue
        y = int(m.group(1))
        for i, v in enumerate(m.group(2).split()):
            fv = float(v)
            if fv < -90:                               # заполнитель пропуска
                continue
            dates.append(date(y, i + 1, 15)); vals.append(fv)
    return (dates, np.array(vals, float)) if len(vals) > 200 else None


def read_oni(p=LAST / "oni.txt"):
    """ONI: перекрывающиеся трёхмесячные средние с 1950 года."""
    if not p.exists():
        return None
    SEAS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    dates, vals = [], []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        f = line.split()
        if len(f) < 4 or f[0] not in SEAS:
            continue
        try:
            y, a = int(f[1]), float(f[3])
        except ValueError:
            continue
        dates.append(date(y, SEAS.index(f[0]) + 1, 15)); vals.append(a)
    return (dates, np.array(vals, float)) if len(vals) > 200 else None


def read_weekly(p=LAST / "noaa_weekly.txt"):
    """Недельный Niño 3.4 с сентября 1981 года."""
    if not p.exists():
        return None
    dates, vals = [], []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = WROW.match(line)
        if not m:
            continue
        nums = re.findall(r"-?\d+\.\d", m.group(4))
        if len(nums) < 8:
            continue
        dates.append(date(int(m.group(3)), MON[m.group(2)], int(m.group(1))))
        vals.append(float(nums[5]))                    # пары идут 1+2, 3, 3.4, 4 → аномалия 3.4
    o = np.argsort(dates)
    return ([dates[i] for i in o], np.array([vals[i] for i in o], float)) if len(vals) > 500 else None


# ── ПАМЯТЬ РЯДА ─────────────────────────────────────────────────────────────────────────────
def _deseason(dates, v, period):
    """Убрать годовой ход: у ENSO он сильный, и без этого «память» меряет календарь."""
    if period <= 1:
        return v
    key = np.array([d.month if period == 12 else (d.timetuple().tm_yday // 7) for d in dates])
    out = v.astype(float).copy()
    for k in np.unique(key):
        m = key == k
        if m.sum() >= 3:
            out[m] -= np.nanmean(v[m])
    return out


def _slow(v, win):
    """Медленная составляющая гауссовым окном: вычитаем её, чтобы тренд не выдавал себя за память."""
    n = len(v)
    w = max(3, int(win) | 1)
    x = np.arange(w) - w // 2
    g = np.exp(-0.5 * (x / (w / 6.0)) ** 2)
    g /= g.sum()
    pad = np.r_[v[:w // 2][::-1], v, v[-(w // 2):][::-1]]
    return np.convolve(pad, g, mode="valid")[:n]


def _ar1(x):
    x = x - x.mean()
    d = float(np.dot(x, x))
    return float(np.dot(x[:-1], x[1:]) / d) if d else 0.0


def _kendall(y):
    from scipy import stats
    t, p = stats.kendalltau(np.arange(len(y)), y)
    return (float(t) if t == t else None), (float(p) if p == p else None)


def memory(name, label, dates, v, period, win_pts, slow_pts, step=1):
    """Критическое замедление: связь соседних значений и разброс в скользящем окне.

    Это СТОРОЖ, а не доказательство. Рост памяти бывает и без всякого перехода: от смены
    инструмента, от долгого тёплого периода, от самой процедуры сглаживания. Поэтому рядом с
    итогом печатается, сколько в ряду независимых окон (перекрывающиеся окна делают любой тренд
    «значимым», если считать их занезависимые наблюдения) и на каком именно вычитании он получен.
    """
    if v is None or len(v) < win_pts + 40:
        return None
    r = _deseason(dates, v, period)
    r = r - _slow(r, slow_pts)
    idx, ar, va = [], [], []
    for i in range(win_pts, len(r) + 1, step):
        w = r[i - win_pts:i]
        idx.append(i - 1); ar.append(_ar1(w)); va.append(float(np.var(w)))
    ar, va = np.array(ar), np.array(va)
    t_ar, p_ar = _kendall(ar)
    t_va, p_va = _kendall(va)
    # последние тридцать лет отдельно: переход, если он близко, виден в конце, а не в среднем
    tail = max(10, int(len(ar) * 0.4))
    t_ar2, p_ar2 = _kendall(ar[-tail:])
    t_va2, p_va2 = _kendall(va[-tail:])
    n_indep = max(1, (len(r) - win_pts) // win_pts)     # неперекрывающихся окон
    return {
        "id": name, "label": label,
        "n_points": int(len(v)), "from": dates[0].isoformat(), "to": dates[-1].isoformat(),
        "window_points": int(win_pts), "window_note": f"{win_pts} points of the series",
        "ar1_now": round(float(ar[-1]), 3), "ar1_pct": round(float((ar[:-1] <= ar[-1]).mean() * 100), 1),
        "var_now": round(float(va[-1]), 4), "var_pct": round(float((va[:-1] <= va[-1]).mean() * 100), 1),
        "tau_ar1": None if t_ar is None else round(t_ar, 3), "p_ar1": None if p_ar is None else round(p_ar, 4),
        "tau_var": None if t_va is None else round(t_va, 3), "p_var": None if p_va is None else round(p_va, 4),
        "tau_ar1_recent": None if t_ar2 is None else round(t_ar2, 3),
        "tau_var_recent": None if t_va2 is None else round(t_va2, 3),
        "n_independent_windows": int(n_indep),
        "series": {"dates": [dates[i].isoformat() for i in idx],
                   "ar1": [round(float(x), 3) for x in ar],
                   "var": [round(float(x), 4) for x in va]},
    }


# ── ОСТАЛЬНЫЕ ЧАСТИ ─────────────────────────────────────────────────────────────────────────
def link_integrity():
    """Держится ли связь «температура моря → отклик атмосферы». Считает сборщик радиансов."""
    p = ROOT / "radiance.json"
    if not p.exists():
        return None
    R = json.loads(p.read_text(encoding="utf-8"))
    rg = ((R.get("sources") or {}).get("regime") or {})
    var = rg.get("variants") or {}
    rows = []
    for k, v in var.items():
        rel, cur = (v.get("relation") or {}), (v.get("current") or {})
        if rel.get("slope") is None or cur.get("conv") is None:
            continue
        ratio = cur.get("ratio_obs_pred")
        sd = cur.get("residual_sd")
        rows.append({"variant": k, "slope": rel.get("slope"), "slope_se": rel.get("slope_se"),
                     "r2": rel.get("r2"), "years": rel.get("n_years_fitted"),
                     "observed": cur.get("conv"), "predicted": cur.get("conv_predicted"),
                     "ratio": ratio, "residual_sd": sd})
    if not rows:
        return None
    # Вариант называется «прибор|проход|окно»: сезон и год к дате — разные вопросы, и общий
    # ответ по ним обоим сразу ничего не значит.
    by_win = {}
    for r in rows:
        w = r["variant"].split("|")[-1]
        by_win.setdefault(w, []).append(r)
    wins = {}
    for w, rs in by_win.items():
        sds = [r["residual_sd"] for r in rs if r["residual_sd"] is not None]
        if not sds:
            continue
        wins[w] = {"n": len(sds), "worst_abs_sd": round(max(abs(x) for x in sds), 2),
                   "all_same_sign": bool(len({x > 0 for x in sds}) == 1),
                   "mean_sd": round(sum(sds) / len(sds), 2)}
    # для итога берём то окно, где расхождение сильнее: сторож должен смотреть на худшее
    worst_win = max(wins.values(), key=lambda q: (q["all_same_sign"], q["worst_abs_sd"]), default=None) if wins else None
    return {"rows": rows, "windows": wins,
            "worst_abs_sd": (worst_win or {}).get("worst_abs_sd"),
            "all_same_sign": bool((worst_win or {}).get("all_same_sign")), "n": len(rows),
            "agreement": rg.get("agreement"), "scope": rg.get("scope"),
            "reading": ("The response of the air is ordinary for this sea temperature while every variant "
                        "stays inside two prediction errors; a break shows first as all of them leaving "
                        "on the same side.")}


def coupling_and_fuel():
    """Сцепка воздуха с океаном и запас обратного хода (тёплый объём)."""
    p = ROOT / "latest.json"
    if not p.exists():
        return None, None
    L = json.loads(p.read_text(encoding="utf-8"))
    air = L.get("air") or {}
    cp = air.get("coupling") or {}
    fuel = air.get("fuel") or {}
    cpl = {"score": cp.get("score"), "of": cp.get("of"), "signs": cp.get("signs"),
           "note": cp.get("note")}
    fl = {"value": fuel.get("value"), "date": fuel.get("date"),
          "share_of_record": fuel.get("share_of_record"), "record": fuel.get("record"),
          "peak_date": fuel.get("peak_date"), "months_since_peak": fuel.get("months_since_peak"),
          # «разряжается» считает сборщик воздуха по своему ряду — берём его ответ, а не свой
          "discharging": fuel.get("discharging"), "lead": fuel.get("lead"),
          # единица та же, что на сцене Air, иначе число читается как сырой байт
          "unit": "m³·°C", "value_e14": (round(fuel["value"] / 1e14, 2) if isinstance(fuel.get("value"), (int, float)) else None),
          "record_e14": (round(fuel["record"] / 1e14, 2) if isinstance(fuel.get("record"), (int, float)) else None),
          "note": fuel.get("note")}
    return cpl, fl


def recharge():
    """Осциллятор с подзарядкой: сборщик радиансов v10 (16.09), блок `recharge`.

    Почему берём его, а не свой. У нас тёплый объём был числом без проверки: «на рекорде и не
    разряжается». У них то же самое, но с восемью условиями, при которых эту фразу вообще можно
    произносить, и с отказом, когда условия не пройдены. Два из восьми сейчас не пройдены —
    событию девять недель при нужных девятнадцати и сравнимых событий два при нужных трёх, —
    и их вердикт звучит «вывод пока не осмыслен». Мы переносим это слово в слово: наш уровень
    не имеет права опираться на признак, который сам себя объявил непросчитанным.

    И ещё одно, чего у нас не было: объём там ЗАМЕНИТЕЛЬ (аномалия уровня моря по альтиметрии),
    а не измеренный объём воды выше изотермы 20 °C. Так и подписано.
    """
    p = ROOT / "radiance.json"
    if not p.exists():
        return None
    R = json.loads(p.read_text(encoding="utf-8"))
    rc = ((R.get("sources") or {}).get("recharge") or {})
    if not rc:
        return None
    cond = rc.get("conditions") or []
    failed = [c for c in cond if not c.get("passed")]
    dis = (rc.get("discharge") or {}).get("current") or {}
    now = rc.get("now") or {}
    pp = rc.get("phase_portrait") or {}
    return {
        "verdict": rc.get("verdict"),
        "conclusive": not failed,
        "conditions_passed": len(cond) - len(failed), "conditions_total": len(cond),
        "failed": [{"id": c.get("id"), "value": c.get("value"), "text": c.get("text")} for c in failed],
        "weeks_since_onset": dis.get("weeks_since_onset"), "onset": dis.get("onset_date"),
        "charge_max_m": dis.get("charge_max_m"), "now_m": dis.get("v_now_m"),
        # отрицательное «разряжено» значит, что объём не упал, а вырос
        "discharged_m": dis.get("discharged_m"),
        "rank_pct": now.get("volume_rank_pct"), "weeks_above": now.get("volume_weeks_above"),
        "weeks_total": now.get("volume_weeks_total"), "date": now.get("date"),
        "lead_median_weeks": pp.get("lead_median_weeks"), "loop_sense": pp.get("loop_sense_all_record"),
        "kind": ((rc.get("measurement_kind") or {}).get("warm_volume")),
        "coverage": rc.get("coverage"),
    }


def provenance():
    """Версия обработки и журнал её изменений: то, без чего эта страница опасна.

    Сама идея «связь разладилась» держится на том, что ряд не менял под собой обработку. Сборщик
    радиансов v10 отдаёт это явно: сколько суток у каждого прибора, в скольких из них смешаны
    версии и какие версии вообще встречались. Скачок, совпавший с датой из журнала, — это не
    новость о климате.
    """
    p = ROOT / "radiance.json"
    if not p.exists():
        return None
    R = json.loads(p.read_text(encoding="utf-8"))
    pr = ((R.get("sources") or {}).get("provenance") or {})
    src = pr.get("sources") or {}
    rows = []
    for k, v in src.items():
        if not isinstance(v, dict):
            continue
        rows.append({"source": k, "n_days": v.get("n_days"), "mixed": v.get("days_mixed_versions"),
                     "mixed_first": v.get("mixed_first"), "mixed_last": v.get("mixed_last"),
                     "versions": list((v.get("versions_seen") or {}).keys())[:4]})
    return {"rows": rows, "why": pr.get("why")} if rows else None


def out_of_range():
    """Насколько сегодня система вышла за пределы, на которых подогнаны наши инструменты."""
    out = []
    p = ROOT / "models-history.json"
    if p.exists():
        M = json.loads(p.read_text(encoding="utf-8"))
        rec, today = (M.get("record") or {}), (M.get("today") or {})
        if rec.get("value") is not None and today.get("combined_peak") is not None:
            out.append({"what": "the forecast models",
                        "fitted_up_to": rec["value"],
                        "fitted_note": f"every error in their record was measured below the highest ONI since {rec.get('since')}, {rec.get('value')} °C ({rec.get('season')} {rec.get('year')})",
                        "today": today["combined_peak"],
                        "today_note": f"their own combined forecast for {today.get('peak_season')} is {today.get('combined_peak')} °C",
                        "beyond": round(float(today["combined_peak"]) - float(rec["value"]), 2)})
    q = ROOT / "latest.json"
    if q.exists():
        L = json.loads(q.read_text(encoding="utf-8"))
        NW = L.get("noaa") or {}
        hm, lat, hmd = (NW.get("hist_max") or {}), (NW.get("latest") or {}), (NW.get("hist_max_date") or {})
        for k, nm in (("n3a", "Niño 3"), ("n12a", "Niño 1+2"), ("n34a", "Niño 3.4")):
            if lat.get(k) is None or hm.get(k) is None:
                continue
            if lat[k] > hm[k]:
                out.append({"what": nm + ", weekly",
                            "fitted_up_to": hm[k],
                            "fitted_note": f"the highest weekly value before this event began, {hm[k]} °C ({hmd.get(k)})",
                            "today": lat[k], "today_note": "this week",
                            "beyond": round(float(lat[k]) - float(hm[k]), 2)})
    return out


# ── ОЦЕНКА ──────────────────────────────────────────────────────────────────────────────────
def assess(mem, link, cpl, fuel, oor, rch=None):
    """Уровень ставится правилом, правило написано словами. Веса никто не измерял — и так сказано.

    0 — ничего из сторожевых признаков не сработало.
    1 — система работает за краем подгонки наших инструментов, но связи держат.
    2 — к этому добавился рост памяти хотя бы в одном длинном ряду.
    3 — память растёт в двух рядах из трёх, либо отклик атмосферы ушёл от связи в одну сторону
        у всех приборов.
    4 — связь не держит (все приборы за двумя ошибками предсказания) ИЛИ сцепка распалась.
    5 — связь не держит И возвращающая сила не сработала: топливо на рекорде без разрядки.
    """
    reasons, level = [], 0
    # ДВА УСЛОВИЯ СРАЗУ: память растёт по последней трети ряда И стоит высоко в собственной
    # истории. Одного тренда мало — окна перекрываются, и положительное τ набирается само.
    grow = [m for m in mem if m and (m.get("tau_ar1_recent") or 0) > 0.2 and (m.get("ar1_pct") or 0) >= 80]
    warm = [m for m in mem if m and (m.get("tau_ar1_recent") or 0) > 0.2 and m not in grow]
    if oor:
        level = max(level, 1)
        # ПРИЧИНЫ ИДУТ НА ЭКРАН, А ПАНЕЛЬ АНГЛИЙСКАЯ. Русский остаётся в комментариях кода.
        reasons.append("We are working past the edge of our own calibration: " + "; ".join(
            f"{o['what']} stands at {o['today']} today against {o['fitted_up_to']}, which is all it was fitted on" for o in oor[:3]))
    if len(grow) >= 1:
        level = max(level, 2)
        reasons.append("Memory both high and rising: " + ", ".join(
            f"{m['label']} (τ {m['tau_ar1_recent']}, {m['ar1_pct']}th percentile of its own history)" for m in grow))
    if warm:
        reasons.append("Rising but not high, so it does not count as a sign: " + ", ".join(
            f"{m['label']} (τ {m['tau_ar1_recent']}, {m['ar1_pct']}th percentile)" for m in warm))
    if len(grow) >= 2:
        level = max(level, 3)
    # НАКЛОН И РАЗЛАДКА — РАЗНЫЕ ВЕЩИ. Согласное отклонение в полсигмы это ещё поведение внутри
    # связи: собственное правило радиансов говорит, что «обычно» это |остаток| < 2. За признак
    # берём полторы, а меньшее просто называем вслух и уровень им не поднимаем.
    if link and link.get("all_same_sign") and (link.get("worst_abs_sd") or 0) >= 1.5:
        level = max(level, 3)
        reasons.append(f"The air has left the relation on one side for every instrument, by up to {link['worst_abs_sd']} prediction errors")
    elif link and link.get("all_same_sign") and (link.get("worst_abs_sd") or 0) >= 0.5:
        reasons.append(f"The air leans one way for every instrument, but no further than {link['worst_abs_sd']} prediction errors, which is still inside the relation")
    if link and (link.get("worst_abs_sd") or 0) >= 2.0 and link.get("all_same_sign"):
        level = max(level, 4)
        reasons.append("Связь не держит: все приборы дальше двух ошибок предсказания")
    if cpl and cpl.get("score") is not None and cpl.get("of") and cpl["score"] <= cpl["of"] - 2:
        level = max(level, 4)
        reasons.append(f"The coupling has come apart: {cpl['score']} of {cpl['of']} signs left")
    # ВОЗВРАЩАЮЩАЯ СИЛА — ТОЛЬКО ПО ПРОВЕРЕННОМУ ТЕСТУ. Свой прежний признак («объём на рекорде
    # и не разряжается») звучал как вывод, хотя был просто двумя числами. У сборщика радиансов
    # тот же признак обставлен восемью условиями и умеет отказываться. Пока он отказывается,
    # уровень на него не опирается — но молчать об этом нельзя, и отказ печатается как есть.
    if rch and rch.get("conclusive") and level >= 4 \
            and (rch.get("discharged_m") or 0) <= 0 and (rch.get("rank_pct") or 0) >= 99:
        level = 5
        reasons.append("And the restoring force has not come: the fuel stands at its record and has not discharged")
    elif rch and not rch.get("conclusive"):
        # ВЕРДИКТ СБОРЩИКА ПРИХОДИТ ПО-РУССКИ, А ЭТО ЭКРАН: передаём смысл, не строку.
        f = ", ".join(c["id"] for c in (rch.get("failed") or []))
        reasons.append("The restoring force cannot be judged yet, and the collector refuses to judge it: "
                       + f"{rch.get('conditions_passed')} of {rch.get('conditions_total')} conditions are met, "
                       + f"and these are not: {f}. "
                       + f"The fuel stands at the {rch.get('rank_pct')}th percentile of {rch.get('weeks_total')} weeks "
                       + f"and over {rch.get('weeks_since_onset')} weeks of this event it has not fallen but risen by "
                       + f"{abs(round((rch.get('discharged_m') or 0) * 1000)):.0f} mm")
    if not reasons:
        reasons.append("None of the watch signs has fired")
    return level, reasons


# Слова уровня повторяют правило дословно: читатель должен видеть, за что именно поставлено.
LEVEL_WORD = {
    0: "none of the watch signs has fired",
    1: "we are working past the edge of our own calibration, and every relation still holds",
    2: "and one long record now has a memory that is both high and rising",
    3: "two long records have it, or the air has left the relation on one side by more than one and a half prediction errors",
    4: "a relation the system lived by is no longer holding, or the coupling has come apart",
    5: "a relation is not holding and the restoring force has not come: the fuel stands at its record without discharging",
}


def build(show=False):
    t0 = time.time()
    psl, oni, wk = read_psl_monthly(), read_oni(), read_weekly()
    mem = []
    if psl:
        mem.append(memory("nino34_monthly", "Niño 3.4, monthly since 1948", psl[0], psl[1], 12, 300, 97))
    if oni:
        mem.append(memory("oni_seasonal", "ONI, three-month means since 1950", oni[0], oni[1], 12, 300, 97))
    if wk:
        mem.append(memory("nino34_weekly", "Niño 3.4, weekly since 1981", wk[0], wk[1], 52, 520, 261, step=4))
    mem = [m for m in mem if m]
    link = link_integrity()
    cpl, fuel = coupling_and_fuel()
    oor = out_of_range()
    rch, prov = recharge(), provenance()
    level, reasons = assess(mem, link, cpl, fuel, oor, rch)

    doc = {
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "level": level, "of": 5, "word": LEVEL_WORD.get(level, ""),
        "reasons": reasons,
        "subjective": True,
        "memory": mem, "link": link, "coupling": cpl, "fuel": fuel, "out_of_range": oor,
        "recharge": rch, "provenance": prov,
        "what_this_is": ("A watch for a change of regime, which is a different question from how strong the "
                         "event is. A record is a position on the curve; a change of regime is the curve itself "
                         "giving way. Nothing on this page is a level of anything — these are relations, the "
                         "memory of the series, and the restoring force."),
        "how_the_level_is_set": ("By a written rule, not by a formula: nobody has measured the weights of these "
                                 "five signs against each other, so adding them into one number would be an "
                                 "invention. The rule is printed beside the level, each sign carries its own "
                                 "figure, and a reader who disagrees with the verdict can still keep the data."),
        "what_it_cannot_see": ("Two equatorial boxes are 0.4 % of the planet. None of the assessed tipping "
                               "elements — the Greenland ice, the Atlantic overturning, the Amazon, the permafrost "
                               "— would show here first. This is a watch on the tropical Pacific and on the three "
                               "long records of the index itself, and it is not a watch on the climate system."),
        "false_alarms": ("Rising memory in a series has honest causes that are not a transition: a change of "
                         "instrument, a long warm spell, the smoothing we applied ourselves. The windows overlap, "
                         "so a trend across them looks more significant than it is; the count of independent "
                         "windows is printed beside each record for that reason."),
        "secs": int(time.time() - t0),
    }
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False))
    print(f"phase.json: уровень {level} из 5, {len(mem)} рядов памяти, {OUT.stat().st_size/1024:.0f} КБ, {doc['secs']} с")
    if show:
        print(f"\n  слово: {doc['word']}")
        for r in reasons:
            print("   ·", r)
        print("\n  память рядов:")
        for m in mem:
            print(f"    {m['label']}: связь соседних {m['ar1_now']} ({m['ar1_pct']}-й процентиль своей истории), "
                  f"τ всего {m['tau_ar1']}, τ по последней трети {m['tau_ar1_recent']}, "
                  f"разброс {m['var_now']} ({m['var_pct']}-й), независимых окон {m['n_independent_windows']}")
        if link:
            print(f"\n  связь море→воздух: приборов {link['n']}, худший остаток {link['worst_abs_sd']} ошибки, "
                  f"все в одну сторону: {link['all_same_sign']}")
        if cpl:
            print(f"  сцепка: {cpl.get('score')} из {cpl.get('of')}")
        if fuel:
            print(f"  топливо: {fuel.get('value')} {fuel.get('unit') or ''}, {fuel.get('share_of_record')} % рекорда, "
                  f"разряжается: {fuel.get('discharging')}")
        for o in oor:
            print(f"  вне диапазона: {o['what']} — сегодня {o['today']}, подгонка до {o['fitted_up_to']} (+{o['beyond']})")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("phase", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok", note=f"level {level}")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    build(a.show)


if __name__ == "__main__":
    main()
