# -*- coding: utf-8 -*-
"""Оценка моделей IRI: справляется, отстаёт, сломалась — и с какого выпуска (ТЗ, 5.4).

Метод:
  1. Целевые сезоны — завершённые трёхмесячные сезоны текущего года, по которым уже есть
     официальный ONI (oni.current: DJF … с числом).
  2. Для каждого сохранённого выпуска плюма (data/enso/iri/*.svg), который прогнозировал
     такой сезон, берётся значение модели → ошибка = прогноз − ONI; лид = место сезона
     среди прогнозных сезонов выпуска (1 — ближайший).
  3. Класс модели по лидам 1–3 текущего года:
       keeping up (ok)  — все |ошибка| ≤ 0.5 и нет систематического знака;
       lagging (lag)    — занижала на ≥ 0.5 в двух выпусках подряд; «с выпуска» — первый из пары;
       broken (broke)   — занижала на ≥ 1.0, или отстала три выпуска подряд, или её прогноз
                          на текущий сезон ниже уже достигнутого недельного уровня.
     Без единого завершённого сезона в прогнозах — класс по последнему правилу или none.
  4. То же для сводного, динамического и статистического средних.
Ограничение: плюм извлечён из рисунка, ±0.05 °C; ошибки меньше этого — шум.
"""
from pathlib import Path

import iri_plume as IP

SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
MONTH_ORDER = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                                            "Sep", "Oct", "Nov", "Dec"])}


def _issue_key(issued):
    """'Aug 2026' → (2026, 7) для сортировки выпусков по времени."""
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


def classify(iri, oni, observed_weekly):
    issues = _issues()
    if not issues:
        return {"classes": {}, "tally": {}, "targets": [], "note": "no stored issues"}
    observed = {s: v for s, v in (oni.get("current") or {}).items() if v is not None}
    targets = [s for s in SEASONS if s in observed]
    names = set()
    for i in issues:
        names.update(k for k, m in i["models"].items() if m["values"])
    ao = (iri or {}).get("against_observed") or {}
    cur_seasons = (iri or {}).get("seasons") or []
    cur_first = cur_seasons.index(ao["season"]) if ao.get("season") in cur_seasons else None

    classes = {}
    for name in sorted(names):
        errs = []
        for i in issues:
            fc = [s for s in i["seasons"] if "OBS" not in s]
            m = i["models"].get(name)
            if not m or not m["values"]:
                continue
            for s in targets:
                if s not in i["seasons"]:
                    continue
                v = m["values"][i["seasons"].index(s)]
                if v is None or s not in fc:
                    continue
                lead = fc.index(s) + 1
                errs.append({"issue": i["issued"], "season": s, "lead": lead,
                             "forecast": v, "observed": observed[s], "err": round(v - observed[s], 2)})
        short = [e for e in errs if e["lead"] <= 3]
        short.sort(key=lambda e: _issue_key(e["issue"]))
        cls, since = None, None
        # текущий сезон ниже реальности — сломалась по определению ТЗ
        below_now = False
        cur_m = (iri or {}).get("models", {}).get(name)
        if cur_m and cur_first is not None and cur_m.get("values") and cur_m["values"][cur_first] is not None \
                and observed_weekly is not None and cur_m["values"][cur_first] < observed_weekly:
            below_now = True
        if short:
            under = [e["err"] <= -0.5 for e in short]
            if any(e["err"] <= -1.0 for e in short):
                cls = "broke"; since = next(e["issue"] for e in short if e["err"] <= -1.0)
            else:
                run = 0; start = None
                for e, u in zip(short, under):
                    if u:
                        run += 1; start = start or e["issue"]
                        if run >= 3:
                            cls = "broke"; since = start; break
                        if run >= 2 and cls is None:
                            cls = "lag"; since = start
                    else:
                        run = 0; start = None
                if cls is None:
                    ok = all(abs(e["err"]) <= 0.5 for e in short)
                    signs = [e["err"] for e in short]
                    systematic = len(signs) >= 2 and (all(x < -0.2 for x in signs) or all(x > 0.2 for x in signs))
                    cls = "ok" if ok and not systematic else "lag"
                    since = None if cls == "ok" else short[0]["issue"]
        if below_now:
            if cls != "broke":
                cls = "broke"; since = since or (iri or {}).get("issued")
        # На страницу уезжает только последнее: полный список ошибок по всем выпускам раздувал
        # latest.json со 195 до 321 КБ, а панели нужен класс, дата и короткий хвост.
        errs_tail = sorted(errs, key=lambda e: (_issue_key(e["issue"]), e["lead"]))[-8:]
        classes[name] = {"cls": cls, "since": since, "errors": errs_tail, "below_now": below_now,
                         "section": (cur_m or {}).get("section") or next(
                             (i["models"][name]["section"] for i in issues if name in i["models"]), None)}
    tally = {"ok": 0, "lag": 0, "broke": 0, "none": 0}
    for name, c in classes.items():
        if c["section"] in ("dyn", "stat"):
            tally[c["cls"] or "none"] += 1
    return {"classes": classes, "tally": tally, "targets": targets,
            "issues": [i["issued"] for i in issues], "observed": observed,
            "note": "errors are forecast minus official ONI for completed seasons; plume read from the figure, ±0.05 °C"}
