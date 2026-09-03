# -*- coding: utf-8 -*-
"""Оценка моделей IRI: справляется, отстаёт, сломалась — и с какого выпуска (ТЗ, 5.4),
плюс разбор «как они ломаются» во времени (владелец 03.09).

ГЛАВНОЕ ПРО ГОД СЕЗОНА. Плюм подписывает сезоны тремя буквами (ASO, NDJ, DJF…), и подписи
повторяются каждый год. Первая версия сравнивала прогноз августовского выпуска на DJF с
официальным ONI за DJF ЭТОГО года — то есть прогноз на будущую зиму с прошлой зимой. Здесь
каждому сезону выпуска присваивается настоящий год: идём от месяца выпуска вперёд и
переваливаем год, когда подпись «отматывается» назад (NDJ → DJF).

Метод:
  1. Для каждого сохранённого выпуска (data/enso/iri/*.svg) строим (сезон, год) по порядку.
  2. Берём те, для которых официальный ONI уже вышел → ошибка = прогноз − ONI, лид = место
     сезона в прогнозной части выпуска (1 — ближайший).
  3. Класс модели по лидам 1–3:
       keeping up (ok)  — все |ошибка| ≤ 0.5 и знак не систематический;
       lagging (lag)    — занижала на ≥ 0.5 в двух выпусках подряд; «с выпуска» — первый из пары;
       broken (broke)   — занижала на ≥ 1.0, или отстала три выпуска подряд, либо её прогноз
                          на текущий сезон ниже уже достигнутого недельного уровня.
  4. breakdown(): по выпускам — сколько моделей были ниже реальности на ближайшем
     проверяемом сезоне, и кто занижает постоянно. Это и есть «часть моделей отваливается».
Ограничение: плюм извлечён из рисунка, ±0.05 °C; ошибки меньше этого — шум.
"""
from pathlib import Path

import iri_plume as IP

SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
SEASON_MID = {s: i + 1 for i, s in enumerate(SEASONS)}      # центральный месяц сезона
MONTH_ORDER = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                                               "Aug", "Sep", "Oct", "Nov", "Dec"])}
NOISE = 0.05            # точность разбора рисунка: ошибки меньше — шум


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


def _observed(oni):
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


def _errors(issues, obs):
    """{модель: [ошибки по всем проверяемым сезонам всех выпусков]}."""
    per_model = {}
    for i in issues:
        for k, label, year, lead in _dated_seasons(i):
            v = obs.get((label, year))
            if v is None:
                continue
            for nm, m in i["models"].items():
                if m["section"] not in ("dyn", "stat") or not m["values"]:
                    continue
                f = m["values"][k]
                if f is None:
                    continue
                per_model.setdefault(nm, []).append(
                    {"issue": i["issued"], "season": f"{label} {year}", "lead": lead,
                     "forecast": f, "observed": v, "err": round(f - v, 2)})
    return per_model


def classify(iri, oni, observed_weekly):
    issues = _issues()
    if not issues:
        return {"classes": {}, "tally": {}, "targets": [], "note": "no stored issues"}
    obs = _observed(oni)
    per_model = _errors(issues, obs)

    # Считаем и показываем только модели ТЕКУЩЕГО выпуска: за год состав плюма меняется, и
    # «11 сломанных из 29» пересчитывало давно ушедшие модели.
    cur_models = {nm: m for nm, m in ((iri or {}).get("models") or {}).items()
                  if m.get("section") in ("dyn", "stat") and m.get("values")}
    names = sorted(cur_models) or sorted(per_model)
    ao = (iri or {}).get("against_observed") or {}
    cur_seasons = (iri or {}).get("seasons") or []
    cur_first = cur_seasons.index(ao["season"]) if ao.get("season") in cur_seasons else None

    classes = {}
    for name in names:
        errs = per_model.get(name, [])
        short = sorted([e for e in errs if e["lead"] <= 3], key=lambda e: _issue_key(e["issue"]))
        cls, since = None, None
        below_now = False
        cur_m = cur_models.get(name)
        if cur_m and cur_first is not None and cur_m["values"][cur_first] is not None \
                and observed_weekly is not None and cur_m["values"][cur_first] < observed_weekly:
            below_now = True
        if short:
            if any(e["err"] <= -1.0 for e in short):
                cls = "broke"
                since = next(e["issue"] for e in short if e["err"] <= -1.0)
            else:
                run, start = 0, None
                for e in short:
                    if e["err"] <= -0.5:
                        run += 1
                        start = start or e["issue"]
                        if run >= 3:
                            cls = "broke"
                            since = start
                            break
                        if run >= 2 and cls is None:
                            cls = "lag"
                            since = start
                    else:
                        run, start = 0, None
                if cls is None:
                    ok = all(abs(e["err"]) <= 0.5 for e in short)
                    signs = [e["err"] for e in short]
                    systematic = len(signs) >= 3 and (all(x < -0.2 for x in signs) or all(x > 0.2 for x in signs))
                    cls = "ok" if ok and not systematic else "lag"
                    since = None if cls == "ok" else short[0]["issue"]
        if below_now and cls != "broke":
            cls = "broke"
            since = since or (iri or {}).get("issued")
        classes[name] = {"cls": cls, "since": since, "errors": short[-8:], "below_now": below_now,
                         "n_checked": len(short),
                         "mean_err": round(sum(e["err"] for e in short) / len(short), 2) if short else None,
                         "section": (cur_m or {}).get("section")}
    tally = {"ok": 0, "lag": 0, "broke": 0, "none": 0}
    for c in classes.values():
        tally[c["cls"] or "none"] += 1
    return {"classes": classes, "tally": tally,
            "targets": sorted({e["season"] for v in per_model.values() for e in v}),
            "issues": [i["issued"] for i in issues], "n_models": len(names),
            "note": "error = forecast minus the official ONI of that exact season; plume read from a figure, ±0.05 °C"}


def breakdown(classes_result, iri, oni):
    """Как ломаются модели во времени: доля ниже реальности по выпускам и постоянные отстающие."""
    issues = _issues()
    obs = _observed(oni)
    by_issue = []
    low_count, checked_count = {}, {}
    for i in issues:
        dated = [(k, s, y, lead) for k, s, y, lead in _dated_seasons(i) if obs.get((s, y)) is not None]
        if not dated:
            continue
        # Ближайший проверяемый сезон, ПО КОТОРОМУ МОДЕЛИ ВООБЩЕ ДАЛИ ЧИСЛА: в плюме первая
        # колонка после наблюдений часто пустая (сезон почти закончился), и брать её вслепую
        # значило получить ноль моделей и пустой разбор.
        pick = None
        for k, label, year, lead in dated:
            vv = [(nm, m["values"][k]) for nm, m in i["models"].items()
                  if m["section"] in ("dyn", "stat") and m["values"] and m["values"][k] is not None]
            if vv:
                pick = (k, label, year, lead, vv)
                break
        if not pick:
            continue
        k, label, year, lead, vals = pick
        v = obs[(label, year)]
        below = [nm for nm, f in vals if f < v - NOISE]
        for nm, _ in vals:
            checked_count[nm] = checked_count.get(nm, 0) + 1
        for nm in below:
            low_count[nm] = low_count.get(nm, 0) + 1
        by_issue.append({"issue": i["issued"], "season": f"{label} {year}", "lead": lead,
                         "observed": v, "n": len(vals), "below": len(below),
                         "share": round(100 * len(below) / len(vals)),
                         "mean_err": round(sum(f - v for _, f in vals) / len(vals), 2)})
    classes = classes_result.get("classes") or {}
    chronic = []
    for nm, c in classes.items():
        errs = [e["err"] for e in (c.get("errors") or [])]
        chronic.append({"model": nm, "issues_low": low_count.get(nm, 0), "of": checked_count.get(nm, 0),
                        "cls": c.get("cls"), "since": c.get("since"), "mean_err": c.get("mean_err"),
                        "worst_err": min(errs) if errs else None, "below_now": c.get("below_now")})
    chronic.sort(key=lambda r: (-(r["issues_low"] or 0), r["mean_err"] if r["mean_err"] is not None else 0))
    return {"by_issue": by_issue, "chronic": chronic[:14], "n_models": len(classes),
            "note": "per issue: models whose nearest verifiable forecast came in below the ONI that season actually had"}


def alerts(iri, bd):
    """Тревоги по моделям: не «сколько сегодня ниже», а что с ними происходит со временем."""
    A = []
    if not iri or "error" in iri:
        return A

    def add(level, title, detail):
        A.append({"level": level, "title": title, "detail": detail, "kind": "models"})

    tally = iri.get("class_tally") or {}
    total = sum(v for k, v in tally.items() if k in ("ok", "lag", "broke", "none"))
    if tally.get("broke"):
        broken = [c["model"] for c in (bd.get("chronic") or []) if c.get("cls") == "broke"][:6]
        add("WATCH", f"{tally['broke']} of {total} forecast models are broken",
            "on the completed seasons of this year they came in low by 1 °C or more, or three issues in a row: "
            + ", ".join(broken) + ("…" if tally["broke"] > len(broken) else ""))
    rows = bd.get("by_issue") or []
    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        if last["share"] - first["share"] >= 15:
            add("WATCH", "The share of models below reality keeps growing",
                f"{first['share']} % in the {first['issue']} issue → {last['share']} % in the {last['issue']} issue; "
                f"the average model error went {first['mean_err']:+.2f} → {last['mean_err']:+.2f} °C")
        if last["share"] >= 50:
            add("WATCH", f"In the {last['issue']} issue {last['below']} of {last['n']} models were below reality",
                f"target season {last['season']}, observed ONI {last['observed']:+.2f}; "
                f"the average model was {last['mean_err']:+.2f} °C off")
    chronic = [c for c in (bd.get("chronic") or []) if c["of"] >= 3 and c["issues_low"] >= max(3, int(c["of"] * 0.6))]
    if chronic:
        add("WATCH", f"{len(chronic)} models have been below reality in most issues",
            "they are not wrong about the future, they fail to keep up with the present: "
            + ", ".join(f"{c['model']} ({c['issues_low']}/{c['of']})" for c in chronic[:5]))
    ao = iri.get("against_observed") or {}
    if ao.get("reality_above_all"):
        add("SHOUT", "Reality is above every model in the current issue",
            f"weekly Niño 3.4 {ao['observed_weekly']:+.1f} °C against a model maximum of {ao['max']:+.2f} "
            f"for {ao['season']} — read the winter numbers of the plume as a lower bound")
    return A
