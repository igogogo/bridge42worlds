# -*- coding: utf-8 -*-
"""Свежий слой: что пришло из источников ПОСЛЕ разобранного состояния, и стоит ли это разбора.

Владелец 06.09: «раз в день или по запросу запустились, проверили, есть ли что новое в наших
источниках, и долили к нам чужие данные, ещё не прошедшие анализ… если свежее имеет сильный
выброс, тогда именно тогда проводим обновление, а если нет, показываем мигающую пунктирную
точку: свежие данные, ещё не участвующие в представлении».

Два темпа:
  · разобранное состояние — latest.json: правила + вердикт модели + проверка; штамп разбора;
  · свежий слой — fresh.json: те же правила на сегодняшних данных, БЕЗ модели и без снимка.
    Панель рисует его отдельно и подписывает «fresh, not yet assessed».

ТРИГГЕРЫ — числа, по которым лёгкий прогон говорит «нужен разбор». Все сравнивают свежий
результат правил с разобранным состоянием; пороги ниже — параметры, менять здесь.
"""
from datetime import date

# Пороги триггеров
IDX_STEP = 3            # индекс риска ушёл на столько пунктов и больше
BAND_KEY = "sst_nino34"  # суточный ряд, который сверяем с коридором прогноза разобранного состояния
SILENT_DAYS = 21        # источник молчит дольше — пометка


def _series(cur, key):
    w = (cur.get("watch") or {}).get(key) or {}
    t = w.get("tail45") or {}
    return w, list(zip(t.get("dates") or [], t.get("anom") or t.get("values") or []))   # значения лежат под «anom»


# Какие риски держатся на каком источнике: если пришла дыра (риск вида data про молчание),
# зависимые от неё риски считаются приостановленными, а не снятыми.
SUSPENDS = {
    "tao_silent": ("subsurface_warm",),
}
# то же для тревог: ключ — id тревоги, которую держит этот источник
SUSPENDS_AL = {
    "tao_silent": ("water_above_normal_at_m_depth_w",),
}


def build(cur, assessed):
    """cur — результат правил на свежих данных (как latest.json до саммари); assessed — latest.json."""
    A = assessed or {}
    out = {"stamp": cur.get("stamp"), "generated": cur.get("generated"),
           "assessed_stamp": A.get("stamp"), "assessed_generated": A.get("generated"),
           "series": {}, "kpi": {}, "alerts": [], "risks": {}, "triggers": [], "notes": []}
    trig = out["triggers"]

    # 1. суточные ряды: хвост после разобранной даты
    for key in ("sst_nino34", "sst_world", "t2_world"):
        w, pts = _series(cur, key)
        aw = (A.get("watch") or {}).get(key) or {}
        a_last = aw.get("last_date")
        tail = [[d, v] for d, v in pts if d and (not a_last or d > a_last) and v is not None]
        out["series"][key] = {"label": w.get("label"), "unit": "°C", "last_date": w.get("last_date"), "last_value": w.get("last_value"),
                              "assessed_last_date": a_last, "assessed_last_value": aw.get("last_value"),
                              "level30": (w.get("level30") or {}).get("anom"), "days_stale": w.get("days_stale"),
                              "records_streak": (w.get("records") or {}).get("streak"),
                              "tail": tail}
        if w.get("days_stale") is not None and w["days_stale"] > SILENT_DAYS:
            out["notes"].append(f"{w.get('label')}: silent for {w['days_stale']} days")
    # ветер по дням (ERA5): хвост после разобранной даты, для графика ветра и строки в State
    er, aer = ((cur.get("wind") or {}).get("era5") or {}), ((A.get("wind") or {}).get("era5") or {})
    if er.get("dates"):
        wl = aer.get("last_date")
        wt = [[d, v] for d, v in zip(er.get("dates") or [], er.get("anom") or []) if d and (not wl or d > wl) and v is not None]
        out["series"]["wind"] = {"label": "Westerly wind anomaly, 130°E–180°, daily", "unit": "m/s",
                                 "last_date": er.get("last_date"), "last_value": (er.get("anom") or [None])[-1],
                                 "assessed_last_date": wl, "assessed_last_value": (aer.get("anom") or [None])[-1], "tail": wt}
    # коридор прогноза разобранного состояния: свежая точка вне p10…p90 — повод разобрать
    aw = (A.get("watch") or {}).get(BAND_KEY) or {}
    fc = aw.get("forecast14") or {}
    s = out["series"].get(BAND_KEY) or {}
    if s.get("tail") and fc.get("p10") is not None and fc.get("p90") is not None:
        lo, hi = fc["p10"], fc["p90"]
        for d, v in s["tail"]:
            if v < lo or v > hi:
                trig.append({"kind": "band", "severity": "high",
                             "text": f"Niño 3.4 daily {v:+.2f} °C on {d} is outside the assessed forecast band {lo:+.2f}…{hi:+.2f} °C"})
                break

    # 2. недельные, месячные выпуски: новая дата выпуска — повод разобрать
    def new_issue(name, now, was, path):
        if now and was and now != was:
            trig.append({"kind": "issue", "severity": "high", "text": f"New {name}: {now} (assessed: {was})", "go": path})
    NW, ANW = cur.get("noaa") or {}, A.get("noaa") or {}
    new_issue("NOAA weekly indices", NW.get("date"), ANW.get("date"), ["now", "weekly"])
    IR, AIR_ = cur.get("iri") or {}, A.get("iri") or {}
    if isinstance(IR, dict) and isinstance(AIR_, dict):
        new_issue("IRI issue", IR.get("issued"), AIR_.get("issued"), ["models", "plume"])
    FD, AFD = cur.get("food") or {}, A.get("food") or {}
    if isinstance(FD, dict) and isinstance(AFD, dict):
        new_issue("FAO month", FD.get("last_month"), AFD.get("last_month"), ["food", "prices"])
    O, AO = cur.get("oni") or {}, A.get("oni") or {}
    new_issue("ONI season", O.get("last_season"), AO.get("last_season"), ["now", "analogs"])
    fu, afu = ((cur.get("air") or {}).get("fuel") or {}), ((A.get("air") or {}).get("fuel") or {})
    new_issue("warm water volume month", fu.get("date"), afu.get("date"), ["air", "fuel"])
    gd, agd = ((cur.get("subsurface") or {}).get("godas") or {}), ((A.get("subsurface") or {}).get("godas") or {})
    new_issue("GODAS month", gd.get("month"), agd.get("month"), ["ocean", "section"])

    # 3. тревоги и риски: что бы правила сказали сегодня против того, что разобрано
    now_al = {a.get("id"): a for a in cur.get("alerts") or [] if a.get("id")}
    was_al = {a.get("id"): a for a in A.get("alerts") or [] if a.get("id")}
    out["alerts"] = [{"id": k, "level": a.get("level"), "title": a.get("title"), "kind": a.get("kind")} for k, a in now_al.items()]
    for k, a in now_al.items():
        if k not in was_al:
            trig.append({"kind": "alert", "severity": "high" if a.get("level") == "SHOUT" else "mid",
                         "text": f"New {a.get('level')} alert: {a.get('title')}"})
        elif was_al[k].get("level") != a.get("level"):
            trig.append({"kind": "alert", "severity": "high" if a.get("level") == "SHOUT" else "mid",
                         "text": f"Alert level {was_al[k].get('level')} → {a.get('level')}: {a.get('title')}"})
    # то же правило для тревог: молчащий источник приостанавливает, а не снимает
    now_r_ids = {r.get("id") for r in cur.get("risks") or []}
    for k, a in was_al.items():
        if k in now_al:
            continue
        held = any(k in deps and g in now_r_ids for g, deps in SUSPENDS_AL.items())
        trig.append({"kind": "alert", "severity": "mid",
                     "text": (f"Alert suspended, its source is silent: {a.get('title')}" if held
                              else f"Alert cleared: {a.get('title')}")})
    now_r = {r.get("id"): r for r in cur.get("risks") or [] if r.get("id")}
    was_r = {r.get("id"): r for r in A.get("risks") or [] if r.get("id")}
    out["risks"] = {k: r.get("level") for k, r in now_r.items()}
    for k, r in now_r.items():
        if k not in was_r:
            trig.append({"kind": "risk", "severity": "mid", "text": f"New risk: {r.get('title')} (level {r.get('level')})"})
        elif was_r[k].get("level") != r.get("level"):
            trig.append({"kind": "risk", "severity": "mid",
                         "text": f"Risk level {was_r[k].get('level')} → {r.get('level')}: {r.get('title')}"})
    # ПРИОСТАНОВЛЕН — НЕ СНЯТ. Поймано 12.09: буи не ответили, правило по ним не сработало, и
    # лента объявила «Risk cleared: Water +11.3 °C above normal is sitting at 100 m under
    # 125°W». Вода никуда не делась, мы просто не дозвонились до причала. Пока на доске стоит
    # риск вида data про молчание источника, риски, которые на этом источнике держатся, не
    # объявляются снятыми: они помечаются приостановленными, и это честное слово.
    for k, r in was_r.items():
        if k in now_r:
            continue
        gap = next((g for g, deps in SUSPENDS.items() if k in deps and g in now_r), None)
        if gap:
            trig.append({"kind": "risk", "severity": "mid",
                         "text": f"Risk suspended, its source is silent: {r.get('title')}"})
        else:
            trig.append({"kind": "risk", "severity": "mid", "text": f"Risk cleared: {r.get('title')}"})
    ri, ari = cur.get("risk_index"), A.get("risk_index")
    out["risk_index"] = ri
    out["assessed_risk_index"] = ari
    # разбор шкалы 0–90 / 90–100 (10.09): в latest.json он появляется только после полного
    # прогона, а панели он нужен сразу — она берёт его отсюда, пока там пусто
    if cur.get("risk_index_detail"):
        out["risk_index_detail"] = cur["risk_index_detail"]
    if ri is not None and ari is not None and abs(ri - ari) >= IDX_STEP:
        trig.append({"kind": "index", "severity": "mid", "text": f"Risk index {ari} → {ri}"})

    # 4. ключевые свежие числа для кирпичей и шапки
    ob = ((cur.get("oisst") or {}).get("boxes") or {})
    tao = ((cur.get("subsurface") or {}).get("tao") or {})
    er = ((cur.get("wind") or {}).get("era5") or {})
    gs = ((cur.get("gulf") or {}).get("sea") or {})
    out["kpi"] = {
        "noaa": {"date": NW.get("date"), "n34a": (NW.get("latest") or {}).get("n34a"), "n3a": (NW.get("latest") or {}).get("n3a")},
        "n34_box": {"date": (ob.get("nino34") or {}).get("last_date"), "anom": (ob.get("nino34") or {}).get("last_anom")},
        "tao": {"date": tao.get("last_date"), "warmest": (tao.get("warmest") or {}).get("value"),
                "station": (tao.get("warmest") or {}).get("station"), "depth": (tao.get("warmest") or {}).get("depth")},
        "wind": {"date": er.get("last_date"), "mean7": er.get("mean7"), "active": er.get("active")},
        "gulf": {"date": gs.get("last_date"), "sst": gs.get("last_sst")},
        "food": {"month": FD.get("last_month") if isinstance(FD, dict) else None, "index": FD.get("index") if isinstance(FD, dict) else None},
        "iri": {"issued": IR.get("issued") if isinstance(IR, dict) else None},
    }
    out["sources_stale"] = [k for k, v in (cur.get("sources") or {}).items() if not v.get("fresh")]
    out["needs_assessment"] = any(t["severity"] == "high" for t in trig)
    out["summary"] = _summary(out)
    out["note"] = ("Rules only, no model: the same rules as the assessed state, run on today's data. Nothing here is "
                   "in the verdict, the risks or the alerts of the assessed state until an assessment runs.")
    return out


def _summary(out):
    n = out["triggers"]
    latest = max([s.get("last_date") or "" for s in out["series"].values()] + [""])
    if not n:
        return f"Fresh data to {latest}; nothing crosses a trigger, the assessed state stands."
    high = [t for t in n if t["severity"] == "high"]
    return (f"Fresh data to {latest}; {len(n)} trigger{'s' if len(n) > 1 else ''} crossed"
            + (f", {len(high)} of them call for an assessment" if high else "") + ": "
            + "; ".join(t["text"] for t in n[:4]) + ("…" if len(n) > 4 else ""))
