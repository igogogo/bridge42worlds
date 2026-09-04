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
        # Одного «ниже в большинстве выпусков» мало: модель могла догнать. Рядом с классом —
        # ошибка двух последних проверяемых выпусков, с знаком и величиной (экспертиза 04.09).
        last2 = [{"issue": e["issue"], "season": e["season"], "err": e["err"]} for e in short[-2:]]
        trend = None
        if len(last2) == 2:
            trend = "catching up" if last2[1]["err"] > last2[0]["err"] + 0.1 else (
                "falling further" if last2[1]["err"] < last2[0]["err"] - 0.1 else "steady")
        classes[name] = {"cls": cls, "since": since, "errors": short[-8:], "below_now": below_now,
                         "last2": last2, "trend": trend,
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


# ---------------------------------------------------------------- живые модели
#
# Владелец 04.09: «мы показываем средние по моделям — а те, что поломались, нам не нужны;
# либо у них веса очень слабые. Нам нужны модели, которые шли с нами вместе, по ним и
# рисуем среднее. А то мы показываем, что всё хорошо, а это не так».
#
# ПОЧЕМУ ЭТО НЕ ПРИДИРКА. Опубликованное сводное по плюму — среднее по ВСЕМ моделям, включая
# те, что уже показали заниженный прогноз на прожитых сезонах. Одиннадцать из двадцати шести
# сломаны, шесть отстают: их числа тянут сводное вниз, и панель успокаивает там, где данные
# тревожат. Здесь среднее взвешенное: сломанная модель не участвует вовсе, отстающая входит
# с малым весом, непроверенная — с половинным (у неё нет истории, а не хорошая история).
WEIGHTS = {"ok": 1.0, "lag": 0.4, "none": 0.6, "broke": 0.0}


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
        cls = (classes.get(nm) or {}).get("cls") or "none"
        rows.append((nm, cls, WEIGHTS.get(cls, 0.6), m["values"]))
    mean, rms, lo, hi, n = [], [], [], [], []
    for i in range(len(seasons)):
        vals = [(r[3][i], r[2]) for r in rows
                if r[2] > 0 and i < len(r[3]) and r[3][i] is not None]
        if not vals:
            mean.append(None); rms.append(None); lo.append(None); hi.append(None); n.append(0)
            continue
        wsum = sum(w for _, w in vals)
        mean.append(round(sum(v * w for v, w in vals) / wsum, 2))
        # СРЕДНЕКВАДРАТИЧНАЯ, А НЕ СРЕДНЯЯ. Владелец 04.09: «лучше среднеквадратичную брать,
        # чем среднюю: если большая какая-то — это очень важно, это не среднее». Обычное
        # среднее гасит одиночный сильный прогноз, а нас как раз он и должен тревожить:
        # событие уже идёт по верхнему краю пучка. Квадрат даёт большим значениям больший
        # вес, знак берём у взвешенного среднего — иначе при разнознаковых прогнозах
        # (какими они бывают в конце ряда) корень вернул бы бессмысленный плюс.
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
            "by_class": {c: sum(1 for r in rows if r[1] == c) for c in ("ok", "lag", "none", "broke")},
            "note": ("Root-mean-square over the models that kept up with reality (the mean is kept "
                     "alongside for reference): squaring gives the strong forecasts the weight they "
                     "deserve, because a single model calling a much larger peak is news, not noise. "
                     "Weighted mean over the models that kept up with reality: broken ones are out "
                     "entirely, chronic laggards enter with a small weight, unverified ones with half. "
                     "The published plume average counts all of them equally.")}


def _monthly_range(td_fi, live_stats, i_fi):
    """Какой месячной аномалии требуют края пучка живых моделей на ближайшем прогнозном сезоне.

    Модель даёт СРЕДНЕЕ за три месяца. Если часть месяцев уже измерена, то из значения модели
    вычитается измеренное, и остаток делится на число неизмеренных месяцев — получается,
    какой должна быть каждая оставшаяся неделя, чтобы модель оказалась права. Этот же коридор
    и переносим на сезоны, которых модели не публикуют (JJA, JAS): у них неизвестен ровно
    один-два месяца, и брать их не из воздуха, а из того же пучка — честнее всего.
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


def position(iri, td_list, live_stats, month_range=None):
    """Где мы САМИ стоим на шкале плюма — точкой там, где сезон прожит, полосой там, где нет.

    Владелец 04.09: «ASO — это среднее, а сейчас начало сентября; сравнивать надо с прожитым
    сезоном, и не точкой, а диапазоном — шире, по разбросу моделей».

    Прожитая часть сезона — это факт: среднее уже измеренных месяцев. Оставшиеся месяцы
    неизвестны, и границы для них берём из разброса ЖИВЫХ моделей на этот же сезон (p10…p90):
    нижняя граница — если остаток пойдёт по нижнему краю пучка, верхняя — по верхнему.
    Поэтому у сезона с одним прожитым месяцем полоса шире, чем у сезона с двумя, а у
    полностью прожитого её нет вовсе.
    """
    seasons = iri.get("seasons") or []
    out = []
    for td in td_list or []:
        if not td:
            continue
        # Сезон, прожитый нами, может вообще не быть столбцом плюма (JJA в августовском
        # выпуске): рисуем его слева от прогнозной части, поэтому индекс тут не обязателен.
        i = seasons.index(td["season"]) if td["season"] in seasons else None
        done, val = td["months_done"], td["value"]
        rec = {"season": td["season"], "i": i, "months_done": done, "months": 3,
               "todate": val, "complete": done >= 3}
        if done >= 3:
            rec["lo"] = rec["hi"] = val
        else:
            s = val * done
            mlo = (live_stats.get("lo") or [None] * len(seasons))[i] if i is not None else None
            mhi = (live_stats.get("hi") or [None] * len(seasons))[i] if i is not None else None
            if mlo is None or mhi is None:
                # Сезона нет в прогнозах моделей (JJA, JAS: плюм начинает с ASO) — берём
                # коридор для оставшихся месяцев с ближайшего сезона, который они дают.
                if not month_range:
                    continue
                mlo, mhi = month_range
                rec["rest_via"] = "the nearest forecast season"
            rec["lo"] = round((s + (3 - done) * mlo) / 3, 2)
            rec["hi"] = round((s + (3 - done) * mhi) / 3, 2)
            rec["rest_from"] = [round(mlo, 2), round(mhi, 2)]
        out.append(rec)
    return out
