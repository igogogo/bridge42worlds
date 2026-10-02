# -*- coding: utf-8 -*-
"""Оценка моделей IRI: кто идёт с событием, кто отстаёт, кто сломался, кто бежит выше — и с
какого выпуска (ТЗ, 5.4); как они ломаются и что правят от выпуска к выпуску (владелец 03.09
и 02.10: «ты же хранишь историю — посмотри, что корректируется и как, и что ломается»).

ГЛАВНОЕ ПРО ГОД СЕЗОНА. Плюм подписывает сезоны тремя буквами (ASO, NDJ, DJF…), и подписи
повторяются каждый год. Первая версия сравнивала прогноз августовского выпуска на DJF с
официальным ONI за DJF ЭТОГО года — то есть прогноз на будущую зиму с прошлой зимой. Здесь
каждому сезону выпуска присваивается настоящий год: идём от месяца выпуска вперёд и
переваливаем год, когда подпись «отматывается» назад (NDJ → DJF).

ТОЛЬКО ЗАКРЫТЫЕ СЕЗОНЫ (переделка 02.10, владелец: «сейчас по сути закончился JAS и начался ASO,
а ты показываешь текущее SON и оценку моделей по нему; надо только по истекшим периодам»).
Прежде рядом с оценкой по прожитым сезонам стояло сравнение плюма с НЕДЕЛЕЙ на сезоне, который
только начался (SON против недельного Niño 3.4): трёхмесячное среднее против одной точки, да ещё
на сезоне, где прожит один месяц из трёх. Теперь модель проверяется только там, где сезон
закрыт целиком: по официальному ONI, а для закрытого сезона, у которого ONI ещё не вышел, — по
КОРИДОРУ (reference): от нашего дневного OISST до OISST за вычетом разрыва ONI/OISST этого года.

ЧЕСТНОЕ ПРАВИЛО КЛАССОВ (02.10, владелец: «кажется, сломанных должно быть меньше»). Прежнее
правило записывало в сломанные 7 моделей из 24 и врало трижды: (1) «три выпуска подряд» считало
ЗАПИСИ, а у выпуска их две (лиды 2 и 3), — модель ломалась за полтора выпуска; (2) один промах
на третьем лиде в самом разгоне события делал модель сломанной навсегда, хотя ошибка на третьем
лиде в 2026-м у всех в среднем −0,3…−0,4 (на пятом −0,8): XRO с ошибкой −0,09 на последней
проверке числилась сломанной с марта; (3) модель, систематически дающая ВЫШЕ реальности
(AUS-ACCESS, +0,4…+0,7), называлась «отстающей». Теперь:
  · у выпуска ОДНА проверка: ближайший сезон, где у модели есть число и сезон закрыт; лид 1 не
    берётся (сезон уже на две трети измерен, это не прогноз). На деле это лид 2;
  · класс решают последние три проверки (RECENT): сломана — все три ниже на LOW и больше;
    отстаёт — последняя и ещё одна ниже на GOOD; выше реальности (hot) — последняя и ещё одна
    выше на GOOD; догнала (caught) — раньше было две подряд ниже на LOW, а последняя в пределах
    GOOD; иначе — идёт с событием (ok);
  · предварительная проверка (коридор) решает, только если её исход один и тот же на обоих
    концах коридора; иначе ждём официальный ONI.

ЧТО МОДЕЛЬ ПРАВИТ (correction). Для каждого закрытого сезона берём прогнозы модели на него из
выпусков подряд (лид 3 → лид 2 → …) и смотрим, какую долю своей прежней ошибки модель закрыла
следующим выпуском. У хороших моделей это 25–45 % за выпуск, у сломанных — около нуля: данные
приходят, прогноз не исправляется. Это и есть «ломается».

ПОГОНЯ (chase). По каждому сезону события — как среднее и разброс моделей менялись от выпуска к
выпуску, и где факт: официальный ONI, коридор закрытого сезона или прожитая часть идущего.

Ограничение: плюм извлечён из рисунка, ±0.05 °C (NOISE); ошибки меньше этого — шум.
"""
import json
import statistics as _st
from datetime import date, timedelta
from pathlib import Path

import iri_plume as IP

SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
SEASON_MID = {s: i + 1 for i, s in enumerate(SEASONS)}      # центральный месяц сезона
SEASON_MONTHS = {s: [((i - 1 + k) % 12) + 1 for k in range(3)] for i, s in enumerate(SEASONS)}  # DJF → 12, 1, 2
MONTH_ORDER = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                                               "Aug", "Sep", "Oct", "Nov", "Dec"])}
NOISE = 0.05            # точность разбора рисунка: ошибки меньше — шум
GOOD = 0.3              # в пределах — модель идёт с событием
LOW = 0.5               # ниже на столько и больше — модель заметно отстала
RECENT = 3              # класс решают последние три проверенных выпуска
OISST_DIR = Path(__file__).resolve().parents[2] / "data" / "enso" / "oisst"


def _issue_key(issued):
    """'Aug 2026' → (2026, 8) для сортировки выпусков по времени."""
    try:
        mon, yr = issued.split()
        return (int(yr), MONTH_ORDER.get(mon[:3], 0))
    except Exception:                                    # noqa: BLE001
        return (0, 0)


def _issues():
    out = []
    for p in sorted(Path(IP.DIR).glob("plume_*.svg")):
        try:
            out.append(IP.parse(p))
        except Exception:                                # noqa: BLE001 — битый файл не ломает оценку
            continue
    seen = {}
    for i in out:
        seen[i["issued"]] = i                            # двойники под разными именами — один выпуск
    return sorted(seen.values(), key=lambda i: _issue_key(i["issued"]))


def _dated_seasons(issue):
    """[(индекс в issue['seasons'], сезон, год, лид)] для прогнозной части выпуска."""
    y, m = _issue_key(issue["issued"])
    out, year, prev_c, lead = [], y, m, 0
    for i, label in enumerate(issue["seasons"]):
        if "OBS" in label or label not in SEASON_MID:
            continue
        c = SEASON_MID[label]
        if c < prev_c:                                   # подпись отмоталась назад — новый год
            year += 1
        prev_c = c
        lead += 1
        out.append((i, label, year, lead))
    return out


def _season_year_months(label, year):
    """[(год, месяц)] трёх месяцев сезона по соглашению ONI: DJF 2026 = дек 2025, янв–фев 2026."""
    out = []
    for m in SEASON_MONTHS[label]:
        y = year
        if label == "DJF" and m == 12:
            y = year - 1
        if label == "NDJ" and m == 1:
            y = year + 1
        out.append((y, m))
    return out


# ---------------------------------------------------------------- факт: ONI и наш дневной OISST
def _grid_index(d):
    """Та же 366-дневная сетка, что у oisst.py: 29 февраля — 59, в невисокосный год пропускается."""
    doy = d.timetuple().tm_yday - 1
    leap = d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)
    return doy if leap or doy < 59 else doy + 1


def box_months(box="nino34", since_year=2005):
    """Месячные аномалии нашего дневного бокса OISST к норме 1991–2020: {'YYYY-MM': {value, days, ndays}}.

    Годовой файл (years_<box>.json) плюс живой хвост (<box>.json) и суточная норма (clim_<box>.json):
    те же файлы, что рисуют «против аналогов». Месяц ЗАКРЫТ, когда измерены все его дни."""
    try:
        Y = json.loads((OISST_DIR / f"years_{box}.json").read_text(encoding="utf-8"))["years"]
        C = json.loads((OISST_DIR / f"clim_{box}.json").read_text(encoding="utf-8"))["doy"]
    except Exception:                                    # noqa: BLE001
        return {}
    try:
        live = json.loads((OISST_DIR / f"{box}.json").read_text(encoding="utf-8")).get("sst") or {}
    except Exception:                                    # noqa: BLE001
        live = {}
    daily = {}
    for ys, arr in Y.items():
        y = int(ys)
        if y < since_year:
            continue
        d = date(y, 1, 1)
        while d.year == y:
            i = _grid_index(d)
            v = arr[i] if i < len(arr) else None
            if v is not None and C[i] is not None:
                daily[d] = v - C[i]
            d += timedelta(days=1)
    for k, v in live.items():
        try:
            d = date.fromisoformat(k)
        except ValueError:
            continue
        if v is not None and d.year >= since_year:
            daily[d] = v - C[_grid_index(d)]
    acc = {}
    for d, v in daily.items():
        acc.setdefault(f"{d.year}-{d.month:02d}", []).append(v)
    out = {}
    for k, vals in acc.items():
        y, m = int(k[:4]), int(k[5:])
        nd = (date(y + (m == 12), m % 12 + 1, 1) - date(y, m, 1)).days
        out[k] = {"value": round(sum(vals) / len(vals), 3), "days": len(vals), "ndays": nd}
    out["_last"] = max(daily).isoformat() if daily else None
    return out


def _box_season(bm, label, year, need_full=True):
    """Сезон по боксу: среднее трёх МЕСЯЧНЫХ средних, как считается ONI; None, если месяц не закрыт."""
    vals = []
    for y, m in _season_year_months(label, year):
        r = bm.get(f"{y}-{m:02d}")
        if not r or (need_full and r["days"] < r["ndays"]):
            return None
        vals.append(r["value"])
    return round(sum(vals) / 3, 3)


def _official(oni):
    """{(сезон, год): ONI} по доступной истории плюс текущий год."""
    obs = {}
    for y, row in (oni.get("by_year") or {}).items():
        for s, v in (row or {}).items():
            if v is not None:
                obs[(s, int(y))] = v
    cur_year = oni.get("year")
    for s, v in (oni.get("current") or {}).items():
        if v is not None and cur_year:
            obs[(s, int(cur_year))] = v
    return obs


def reference(oni, bm=None):
    """С чем проверять прогноз сезона: {(сезон, год): запись}.

    Официальный ONI — как есть. Закрытый сезон без ONI (CPC выпускает его в начале следующего
    месяца) — коридор: OISST нашего бокса и он же за вычетом разрыва OISST−ONI последнего сезона,
    где есть оба. Разрыв в 2006–2025 в среднем 0,00 при разбросе 0,12, но в 2026-м вырос до +0,30
    (JJA: ONI +1,80, OISST +2,10): ONI считается по ERSST, модели проверяются по нему."""
    bm = bm if bm is not None else box_months()
    off = _official(oni)
    ref = {k: {"official": True, "value": v} for k, v in off.items()}
    # разрыв по последнему официальному сезону, у которого бокс закрыт
    gap, gap_from = None, None
    for (lab, y) in sorted(off, key=lambda k: (k[1], SEASON_MID[k[0]]), reverse=True):
        b = _box_season(bm, lab, y)
        if b is not None:
            gap, gap_from = round(b - off[(lab, y)], 2), f"{lab} {y}"
            ref[(lab, y)]["oisst"] = b
            break
    last = bm.get("_last")
    if last:
        ly = int(last[:4])
        for y in (ly - 1, ly):
            for lab in SEASONS:
                if (lab, y) in off:
                    if "oisst" not in ref[(lab, y)]:
                        b = _box_season(bm, lab, y)
                        if b is not None:
                            ref[(lab, y)]["oisst"] = b
                    continue
                b = _box_season(bm, lab, y)
                if b is None:
                    continue
                g = gap or 0.0
                lo, hi = sorted((round(b - g, 2), round(b, 2)))
                ref[(lab, y)] = {"official": False, "oisst": b, "lo": lo, "hi": hi,
                                 "gap": gap, "gap_from": gap_from}
    return ref


# ---------------------------------------------------------------- проверки и классы
def _checks(issues, ref):
    """{модель: [проверка]} — у выпуска ОДНА проверка на модель: ближайший сезон (лид 2 и дальше),
    где у модели есть число. Если этот сезон ещё не закрыт — выпуск не проверяется вовсе: брать
    вместо него дальний сезон значило бы мерить модель не тем лидом, что у соседних выпусков."""
    out = {}
    for i in issues:
        dated = [t for t in _dated_seasons(i) if t[3] >= 2]
        for nm, m in i["models"].items():
            if m["section"] not in ("dyn", "stat") or not m["values"]:
                continue
            for k, label, year, lead in dated:
                f = m["values"][k] if k < len(m["values"]) else None
                if f is None:
                    continue
                r = ref.get((label, year))
                if r is None:
                    break
                c = {"issue": i["issued"], "season": f"{label} {year}", "lead": lead, "forecast": f,
                     "official": r["official"]}
                if r["official"]:
                    c["observed"] = r["value"]
                    c["err"] = round(f - r["value"], 2)
                else:
                    c["ref"] = [r["lo"], r["hi"]]
                    c["err_lo"], c["err_hi"] = round(f - r["hi"], 2), round(f - r["lo"], 2)
                out.setdefault(nm, []).append(c)
                break
    for v in out.values():
        v.sort(key=lambda c: _issue_key(c["issue"]))
    return out


def _band(e):
    return 0 if e <= -LOW else 1 if e <= -GOOD else 2 if e < GOOD else 3


def decided(c):
    """Ошибка проверки, на которую можно опереться. Официальная — как есть. Предварительная — только
    если оба конца коридора дают один исход; тогда берётся конец, БЛИЖНИЙ к нулю (в пользу модели)."""
    if c.get("official"):
        return c["err"]
    a, b = c["err_lo"], c["err_hi"]
    if _band(a) != _band(b):
        return None
    if a <= 0 <= b:
        return 0.0
    return b if b < 0 else a


def _correction(issues, ref, name):
    """Какую долю своей прежней ошибки модель закрывает следующим выпуском (по закрытым сезонам)."""
    seq = {}
    for i in issues:
        m = i["models"].get(name)
        if not m or m["section"] not in ("dyn", "stat") or not m["values"]:
            continue
        for k, label, year, lead in _dated_seasons(i):
            r = ref.get((label, year))
            if not r or not r["official"]:
                continue
            f = m["values"][k] if k < len(m["values"]) else None
            if f is not None:
                seq.setdefault((label, year), {})[lead] = f
    shares = []
    for (label, year), by_lead in seq.items():
        v = ref[(label, year)]["value"]
        for lead, f in by_lead.items():
            g = by_lead.get(lead - 1)
            e = f - v
            if g is not None and abs(e) >= 0.2:
                shares.append((g - f) / -e)
    if len(shares) < 4:
        return None
    return {"share": round(_st.mean(shares), 2), "n": len(shares)}


def _classify_one(checks):
    dec = [(c, decided(c)) for c in checks]
    dec = [(c, e) for c, e in dec if e is not None]
    if not dec:
        return None, None, dec
    last = [e for _, e in dec[-RECENT:]]

    def run_start(pred):
        """Выпуск, с которого идёт нынешняя серия проверок, удовлетворяющих pred."""
        start = None
        for c, e in reversed(dec):
            if not pred(e):
                break
            start = c["issue"]
        return start

    if len(last) == RECENT and all(e <= -LOW for e in last):
        return "broke", run_start(lambda e: e <= -LOW), dec
    if last[-1] <= -GOOD and sum(e <= -GOOD for e in last) >= 2:
        return "lag", run_start(lambda e: e <= -GOOD), dec
    if len(last) >= 2 and last[-1] >= GOOD and sum(e >= GOOD for e in last) >= 2:
        return "hot", run_start(lambda e: e >= GOOD), dec
    was_bad = any(a <= -LOW and b <= -LOW for (_, a), (_, b) in zip(dec, dec[1:]))
    if was_bad and abs(last[-1]) < GOOD:
        return "caught", run_start(lambda e: abs(e) < GOOD), dec
    return "ok", None, dec


def classify(iri, oni, ref=None, issues=None):
    issues = issues or _issues()
    if not issues:
        return {"classes": {}, "tally": {}, "targets": [], "note": "no stored issues"}
    ref = ref if ref is not None else reference(oni)
    per_model = _checks(issues, ref)

    # Считаем и показываем только модели ТЕКУЩЕГО выпуска: за год состав плюма меняется, и
    # «11 сломанных из 29» пересчитывало давно ушедшие модели.
    cur_models = {nm: m for nm, m in ((iri or {}).get("models") or {}).items()
                  if m.get("section") in ("dyn", "stat") and m.get("values")}
    names = sorted(cur_models) or sorted(per_model)
    classes = {}
    for name in names:
        ch = per_model.get(name, [])
        cls, since, dec = _classify_one(ch)
        last2 = [{"issue": c["issue"], "season": c["season"], "err": e} for c, e in dec[-2:]]
        trend = None
        if len(last2) == 2:
            trend = "catching up" if last2[1]["err"] > last2[0]["err"] + 0.1 else (
                "falling further" if last2[1]["err"] < last2[0]["err"] - 0.1 else "steady")
        recent = [e for _, e in dec[-RECENT:]]
        classes[name] = {"cls": cls, "since": since, "errors": ch[-8:], "last2": last2, "trend": trend,
                         "n_checked": len(dec),
                         "mean_err": round(sum(recent) / len(recent), 2) if recent else None,
                         "correction": _correction(issues, ref, name),
                         "section": (cur_models.get(name) or {}).get("section")}
    tally = {"ok": 0, "caught": 0, "lag": 0, "hot": 0, "broke": 0, "none": 0}
    for c in classes.values():
        tally[c["cls"] or "none"] += 1
    return {"classes": classes, "tally": tally,
            "targets": sorted({c["season"] for v in per_model.values() for c in v}),
            "issues": [i["issued"] for i in issues], "n_models": len(names),
            "rule": {"good": GOOD, "low": LOW, "recent": RECENT},
            "note": ("one check per issue: the nearest closed season the model gave a number for (lead 2); "
                     "error = forecast minus the official ONI, or a corridor while the ONI is not out; "
                     "the class is decided by the last three checks; plume read from a figure, ±0.05 °C")}


def breakdown(classes_result, iri, oni, ref=None, issues=None):
    """Как ломаются модели во времени: по выпускам — сколько ниже закрытого сезона; постоянные отстающие."""
    issues = issues or _issues()
    ref = ref if ref is not None else reference(oni)
    per_model = _checks(issues, ref)
    by_issue = []
    for i in issues:
        rows = [c for v in per_model.values() for c in v if c["issue"] == i["issued"]]
        if not rows:
            continue
        # у всех моделей выпуска ближайший сезон один и тот же (лид 2); на всякий случай — самый частый
        seas = max({c["season"] for c in rows}, key=lambda s: sum(1 for c in rows if c["season"] == s))
        rows = [c for c in rows if c["season"] == seas]
        n = len(rows)
        if rows[0]["official"]:
            v = rows[0]["observed"]
            below = sum(1 for c in rows if c["err"] < -NOISE)
            above = sum(1 for c in rows if c["err"] > NOISE)
            errs = [c["err"] for c in rows]
            rec = {"observed": v, "mean_err": round(sum(errs) / n, 2), "official": True}
        else:
            lo, hi = rows[0]["ref"]
            below = sum(1 for c in rows if c["forecast"] < lo - NOISE)
            above = sum(1 for c in rows if c["forecast"] > hi + NOISE)
            mf = sum(c["forecast"] for c in rows) / n
            rec = {"ref": [lo, hi], "mean_err_range": [round(mf - hi, 2), round(mf - lo, 2)], "official": False}
        fs = [c["forecast"] for c in rows]
        rec.update({"issue": i["issued"], "season": seas, "lead": rows[0]["lead"], "n": n,
                    "below": below, "above": above, "within": n - below - above,
                    "share": round(100 * below / n), "mean_forecast": round(sum(fs) / n, 2),
                    "sd_forecast": round(_st.stdev(fs), 2) if n > 1 else 0.0,
                    "max_forecast": max(fs)})
        by_issue.append(rec)
    classes = classes_result.get("classes") or {}
    chronic = []
    for nm, c in classes.items():
        dec = [d for d in (decided(x) for x in per_model.get(nm, [])) if d is not None]
        chronic.append({"model": nm, "issues_low": sum(1 for e in dec if e < -NOISE), "of": len(dec),
                        "cls": c.get("cls"), "since": c.get("since"), "mean_err": c.get("mean_err"),
                        "worst_err": min(dec) if dec else None,
                        "correction": (c.get("correction") or {}).get("share")})
    chronic.sort(key=lambda r: (-(r["issues_low"] or 0), r["mean_err"] if r["mean_err"] is not None else 0))
    return {"by_issue": by_issue, "chronic": chronic[:14], "n_models": len(classes),
            "note": ("Per issue: the models' forecast for the nearest season that is now closed (lead 2), "
                     "against the official ONI, or against a corridor while the ONI is not out")}


def scored(bd):
    """Последний закрытый сезон, по которому проверены модели: для заголовков, тревог, журнала и вердикта."""
    rows = bd.get("by_issue") or []
    if not rows:
        return None
    last = rows[-1]
    off = next((r for r in reversed(rows) if r["official"]), None)
    return {"latest": last, "latest_official": off}


# ---------------------------------------------------------------- погоня и профиль лидов
def chase(issues, ref, bm=None, back=4, ahead=2):
    """По каждому сезону события: среднее и разброс моделей от выпуска к выпуску и где факт.

    Четыре последних закрытых сезона и два идущих за ними: у закрытых факт — официальный ONI или
    коридор, у идущих — только прожитые месяцы (это не оценка, а то, что уже измерено)."""
    bm = bm if bm is not None else box_months()
    if not issues or not ref:
        return []
    closed = sorted(ref, key=lambda k: (k[1], SEASON_MID[k[0]]))
    seq = closed[-back:]
    j, y = SEASONS.index(closed[-1][0]), closed[-1][1]
    for _ in range(ahead):
        j += 1
        if j == 12:
            j, y = 0, y + 1
        seq.append((SEASONS[j], y))
    out = []
    for lab, y in seq:
        rows = []
        for i in issues:
            for k, l2, y2, lead in _dated_seasons(i):
                if l2 != lab or y2 != y or lead < 2:
                    continue
                vals = sorted(m["values"][k] for m in i["models"].values()
                              if m["section"] in ("dyn", "stat") and m["values"] and k < len(m["values"])
                              and m["values"][k] is not None)
                comb = next((m["values"][k] for nm, m in i["models"].items() if "COMBINED" in nm and m["values"]
                             and k < len(m["values"])), None)
                if vals:
                    rows.append({"issue": i["issued"], "lead": lead, "n": len(vals),
                                 "mean": round(sum(vals) / len(vals), 2),
                                 "p10": round(_pct(vals, 10), 2), "p90": round(_pct(vals, 90), 2),
                                 "min": vals[0], "max": vals[-1], "combined": comb})
        r = ref.get((lab, y))
        fact = None
        if r and r["official"]:
            fact = {"kind": "official", "value": r["value"], "oisst": r.get("oisst")}
        elif r:
            fact = {"kind": "corridor", "lo": r["lo"], "hi": r["hi"], "oisst": r["oisst"],
                    "gap": r.get("gap"), "gap_from": r.get("gap_from")}
        else:
            lived = [bm.get(f"{yy}-{mm:02d}") for yy, mm in _season_year_months(lab, y)]
            done = [x for x in lived if x and x["days"] >= x["ndays"]]
            if done:
                fact = {"kind": "lived", "value": round(sum(x["value"] for x in done) / len(done), 2),
                        "months_done": len(done)}
        if rows:
            out.append({"season": f"{lab} {y}", "rows": rows, "fact": fact})
    return out


def lead_profile(issues, ref, iri):
    """Средняя ошибка моделей текущего выпуска по лидам на официально закрытых сезонах этого события."""
    cur = {nm for nm, m in ((iri or {}).get("models") or {}).items()
           if m.get("section") in ("dyn", "stat") and m.get("values")}
    yr = _issue_key(issues[-1]["issued"])[0] if issues else None
    acc = {}
    for i in issues:
        for k, lab, y, lead in _dated_seasons(i):
            r = ref.get((lab, y))
            if not r or not r["official"] or y != yr or lead < 2:
                continue
            for nm, m in i["models"].items():
                if nm not in cur or m["section"] not in ("dyn", "stat") or not m["values"]:
                    continue
                f = m["values"][k] if k < len(m["values"]) else None
                if f is not None:
                    acc.setdefault(lead, []).append(f - r["value"])
    return [{"lead": ld, "mean_err": round(_st.mean(v), 2), "n": len(v),
             "share_low": round(100 * sum(1 for e in v if e <= -LOW) / len(v))}
            for ld, v in sorted(acc.items()) if len(v) >= 10]


def alerts(iri, bd):
    """Тревоги по моделям: что с ними происходит на ЗАКРЫТЫХ сезонах, а не «сколько ниже сегодня»."""
    A = []
    if not iri or "error" in iri:
        return A

    def add(level, title, detail, aid=None):
        a = {"level": level, "title": title, "detail": detail, "kind": "models"}
        if aid:
            a["id"] = aid          # устойчивый id, когда заголовок меняется по данным
        A.append(a)

    tally = iri.get("class_tally") or {}
    total = sum(v for k, v in tally.items() if k in ("ok", "caught", "lag", "hot", "broke", "none"))
    if tally.get("broke"):
        broken = [c["model"] for c in (bd.get("chronic") or []) if c.get("cls") == "broke"][:6]
        add("WATCH", f"{tally['broke']} of {total} forecast models are broken",
            f"their last {RECENT} forecasts for the nearest season each came in {LOW} °C or more below what the "
            "season turned out to be: " + ", ".join(broken) + ("…" if tally["broke"] > len(broken) else ""))
    rows = [r for r in (bd.get("by_issue") or []) if r.get("official")]
    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        if last["share"] - first["share"] >= 15:
            # «keeps growing» при 76 → 71 → 62 % было неправдой (проверка Fable 06.09): если
            # последний шаг вниз, так и говорим. id не меняется, иначе лента объявит новую тревогу.
            prev_row = rows[-2]
            easing = last["share"] < prev_row["share"]
            add("WATCH", (f"The share of models below reality has grown since {first['issue']}" if easing
                          else "The share of models below reality keeps growing"),
                f"{first['share']} % in the {first['issue']} issue → {last['share']} % in the {last['issue']} issue"
                + (f", down from {prev_row['share']} % in the {prev_row['issue']} issue" if easing else "")
                + f"; the average model error went {first['mean_err']:+.2f} → {last['mean_err']:+.2f} °C",
                aid="the_share_of_models_below_reality_keeps_growing")
    allr = bd.get("by_issue") or []
    if allr:
        last = allr[-1]
        if last["official"] and last["share"] >= 50:
            add("WATCH", f"In the {last['issue']} issue {last['below']} of {last['n']} models were below reality",
                f"the latest closed season it forecast: {last['season']}, official ONI {last['observed']:+.2f}; "
                f"the average model was {last['mean_err']:+.2f} °C off",
                aid="in_the_issue_models_were_below_reality")
        elif not last["official"] and last["n"] and 100 * last["below"] / last["n"] >= 50:
            add("WATCH", f"In the {last['issue']} issue {last['below']} of {last['n']} models were below reality",
                f"{last['season']} is closed but its official ONI is not out yet: these models are below even the "
                f"low end of {last['ref'][0]:+.2f} … {last['ref'][1]:+.2f} (our OISST and OISST less this year's "
                "gap to the ONI)", aid="in_the_issue_models_were_below_reality")
        # РЕАЛЬНОСТЬ ВЫШЕ МОДЕЛЕЙ — на ЗАКРЫТОМ сезоне, а не неделя против начавшегося (02.10). Прежде
        # обе тревоги (alerts.py, 2б) сравнивали недельный Niño 3.4 с трёхмесячным прогнозом сезона,
        # в котором прожит месяц из трёх.
        lo = last["observed"] if last["official"] else last["ref"][0]
        what = "official ONI" if last["official"] else "even the low end of the corridor"
        if last["n"] and last["above"] == 0 and last["within"] == 0:
            add("SHOUT", f"{last['season']} came in above every model of the {last['issue']} issue",
                f"{what} {lo:+.2f} °C against a model maximum of {last['max_forecast']:+.2f}; "
                f"the mean forecast was {last['mean_forecast']:+.2f}",
                aid="reality_is_above_every_model")
        elif last["n"] > 1 and lo > last["mean_forecast"] + last["sd_forecast"]:
            add("WATCH", f"{last['season']} came in more than one spread above the models",
                f"{what} {lo:+.2f} °C against {last['mean_forecast']:+.2f} ± {last['sd_forecast']:.2f} "
                f"over {last['n']} models of the {last['issue']} issue (lead {last['lead']})",
                aid="reality_is_above_the_model_spread")
    chronic = [c for c in (bd.get("chronic") or []) if c["of"] >= 3 and c["issues_low"] >= max(3, int(c["of"] * 0.6))]
    if chronic:
        add("WATCH", f"{len(chronic)} models have been below reality in most issues",
            "they are not wrong about the future, they fail to keep up with the present: "
            + ", ".join(f"{c['model']} ({c['issues_low']}/{c['of']})" for c in chronic[:5]))
    return A


# ---------------------------------------------------------------- живые модели
#
# Владелец 04.09: «мы показываем средние по моделям — а те, что поломались, нам не нужны;
# либо у них веса очень слабые. Нам нужны модели, которые шли с нами вместе, по ним и
# рисуем среднее. А то мы показываем, что всё хорошо, а это не так».
#
# ПОЧЕМУ ЭТО НЕ ПРИДИРКА. Опубликованное сводное по плюму — среднее по ВСЕМ моделям, включая
# те, что уже показали заниженный прогноз на прожитых сезонах. Их числа тянут сводное вниз, и
# панель успокаивает там, где данные тревожат. Здесь среднее взвешенное: сломанная модель не
# участвует вовсе, отстающая и бегущая выше — с малым весом (ошибка систематическая, в какую
# сторону — неважно), догнавшая — почти полным, непроверенная — с половинным.
WEIGHTS = {"ok": 1.0, "caught": 0.8, "lag": 0.4, "hot": 0.4, "none": 0.6, "broke": 0.0}


def _pct(sorted_vals, p):
    """Процентиль по готовому отсортированному списку, линейной интерполяцией."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    i = (len(sorted_vals) - 1) * p / 100.0
    lo, hi = int(i), min(int(i) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def live(iri, classes):
    """Сводное и разброс ПО ЖИВЫМ моделям, по каждому сезону выпуска."""
    seasons = iri.get("seasons") or []
    rows = []
    for nm, m in (iri.get("models") or {}).items():
        if m.get("section") not in ("dyn", "stat") or not m.get("values"):
            continue
        cr = classes.get(nm) or {}
        cls = cr.get("cls") or "none"
        # СКОЛЬКО ЗА КЛАССОМ ПРОВЕРОК. «Keeping up» без минимума выборки даётся и по одной
        # сверке. Голос растёт с числом проверок и добирает полный вес к третьей (15.09).
        w = WEIGHTS.get(cls, 0.6) * min(1.0, max(1, cr.get("n_checked") or 0) / 3.0)
        rows.append((nm, cls, round(w, 3), m["values"]))
    mean, rms, lo, hi, n = [], [], [], [], []
    for i in range(len(seasons)):
        vals = [(r[3][i], r[2]) for r in rows
                if r[2] > 0 and i < len(r[3]) and r[3][i] is not None]
        if not vals:
            mean.append(None); rms.append(None); lo.append(None); hi.append(None); n.append(0)
            continue
        wsum = sum(w for _, w in vals)
        mean.append(round(sum(v * w for v, w in vals) / wsum, 2))
        # СРЕДНЕКВАДРАТИЧНАЯ, А НЕ СРЕДНЯЯ (владелец 04.09): обычное среднее гасит одиночный сильный
        # прогноз, а нас как раз он и должен тревожить. Знак — у взвешенного среднего.
        sq = (sum(v * v * w for v, w in vals) / wsum) ** .5
        rms.append(round(sq if mean[-1] >= 0 else -sq, 2))
        xs = sorted(v for v, _ in vals)
        lo.append(round(_pct(xs, 10), 2))
        hi.append(round(_pct(xs, 90), 2))
        n.append(len(vals))
    used = [r for r in rows if r[2] > 0]
    out_of = [{"name": r[0], "cls": r[1], "since": (classes.get(r[0]) or {}).get("since")}
              for r in rows if r[2] == 0]
    return {"seasons": seasons, "mean": mean, "rms": rms, "lo": lo, "hi": hi, "n": n,
            "n_live": len(used), "n_all": len(rows),
            "weights": WEIGHTS, "excluded": sorted(out_of, key=lambda x: x["name"]),
            "by_class": {c: sum(1 for r in rows if r[1] == c) for c in ("ok", "caught", "lag", "hot", "none", "broke")},
            "note": ("Root-mean-square over the models that kept up with reality (the mean is kept "
                     "alongside for reference): squaring gives the strong forecasts the weight they "
                     "deserve, because a single model calling a much larger peak is news, not noise. "
                     "Weighted over the models that kept up: broken ones are out entirely, models "
                     "running persistently low or high enter with a small weight, ones that caught up "
                     "with most of it, unverified ones with half. "
                     "The published plume average counts all of them equally.")}


def _monthly_range(td_fi, live_stats, i_fi):
    """Какой месячной аномалии требуют края пучка живых моделей на ближайшем прогнозном сезоне.

    Модель даёт СРЕДНЕЕ за три месяца. Если часть месяцев уже измерена, то из значения модели
    вычитается измеренное, и остаток делится на число неизмеренных месяцев — получается,
    какой должна быть каждая оставшаяся неделя, чтобы модель оказалась права.
    """
    lo = (live_stats.get("lo") or [])[i_fi] if i_fi is not None else None
    hi = (live_stats.get("hi") or [])[i_fi] if i_fi is not None else None
    if lo is None or hi is None or not td_fi:
        return None
    done, val = td_fi["months_done"], td_fi["value"]
    u = 3 - done
    if u <= 0:
        return None
    s = val * done
    return ((3 * lo - s) / u, (3 * hi - s) / u)


def position(iri, td_list, live_stats, month_range=None, ref=None):
    """Где мы САМИ стоим на шкале плюма — точкой там, где сезон закрыт, полосой там, где нет.

    Владелец 04.09: «ASO — это среднее, а сейчас начало сентября; сравнивать надо с прожитым
    сезоном, и не точкой, а диапазоном — шире, по разбросу моделей». Прожитая часть сезона — факт:
    среднее измеренных месяцев (наш дневной OISST). Неизмеренные месяцы берут границы из разброса
    ЖИВЫХ моделей на этот же сезон. У закрытого сезона полосы нет; рядом с ним — официальный ONI,
    когда он вышел (модели проверяются по нему, а он в 2026-м ниже OISST на 0,1–0,3).
    """
    seasons = iri.get("seasons") or []
    out = []
    for td in td_list or []:
        if not td:
            continue
        i = seasons.index(td["season"]) if td["season"] in seasons else None
        done, val = td["months_done"], td["value"]
        rec = {"season": td["season"], "i": i, "months_done": done, "months": 3,
               "todate": val, "months_over": td.get("months_over", done),
               "running": td.get("running"),
               "complete": bool(td.get("complete", done >= 3))}
        r = (ref or {}).get((td["season"], td.get("year")))
        if r:
            rec["oni"] = r.get("value") if r.get("official") else None
            if not r.get("official"):
                rec["corridor"] = [r["lo"], r["hi"]]
        if rec["complete"] or done >= 3:
            rec["lo"] = rec["hi"] = val
        else:
            s = val * done
            mlo = (live_stats.get("lo") or [None] * len(seasons))[i] if i is not None else None
            mhi = (live_stats.get("hi") or [None] * len(seasons))[i] if i is not None else None
            if mlo is not None and mhi is not None:
                # СЕЗОН ЕСТЬ В ПРОГНОЗАХ: полоса — их собственный разброс за этот сезон (15.09)
                rec["lo"], rec["hi"] = round(mlo, 2), round(mhi, 2)
                mr = _monthly_range(td, live_stats, i)
                if mr:
                    rec["rest_from"] = [round(mr[0], 2), round(mr[1], 2)]
            else:
                # Сезона нет в прогнозах моделей — коридор оставшихся месяцев с ближайшего сезона
                if not month_range:
                    continue
                mlo, mhi = month_range
                rec["rest_via"] = "the nearest forecast season"
                rec["lo"] = round((s + (3 - done) * mlo) / 3, 2)
                rec["hi"] = round((s + (3 - done) * mhi) / 3, 2)
                rec["rest_from"] = [round(mlo, 2), round(mhi, 2)]
        out.append(rec)
    return out
