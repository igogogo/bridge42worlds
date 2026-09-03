# -*- coding: utf-8 -*-
"""Блок F, живой ряд: индекс цен на продовольствие FAO и пять групп.

Что считается (ТЗ, 6.4): последние 36 месяцев индекса и групп; изменение за месяц и за
год; наложение на прошлые события по месяцам от начала события — начало берём из ONI:
первый сезон года зарождения с ONI ≥ +0.5, месяц — средний месяц сезона. Так текущий
2026-й сравнивается с 1997-98, 2015-16 и 2023-24 в одном календаре «месяц 0 = начало».
"""
SEASON_MID = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8,
              "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}
ANALOG_ONSET_YEARS = (1997, 2015, 2023)


def _onset_month(oni_year_rows, year):
    """oni_year_rows: {season: value} для года. Первый сезон с ONI ≥ 0.5 → 'YYYY-MM'."""
    for s in ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]:
        v = (oni_year_rows or {}).get(s)
        if v is not None and v >= 0.5:
            return f"{year}-{SEASON_MID[s]:02d}"
    return None


def _idx(months, ym):
    try:
        return months.index(ym)
    except ValueError:
        return None


def _rel(series, months, onset, span=24):
    """Ряд в процентах к месяцу начала события, от −6 до +span месяцев."""
    i0 = _idx(months, onset) if onset else None
    if i0 is None or series[i0] is None:
        return None
    base = series[i0]
    out = []
    for k in range(-6, span + 1):
        j = i0 + k
        v = series[j] if 0 <= j < len(series) else None
        out.append(None if v is None else round(100.0 * v / base, 1))
    return {"from": -6, "values": out, "base": base, "onset": onset}


def analyze(fao, oni_current, oni_analogs, cur_year):
    months, index, groups = fao["months"], fao["index"], fao["groups"]
    n = len(index)
    last = index[-1]
    mom = round(last - index[-2], 1) if n > 1 else None
    yoy = round(100.0 * (last / index[-13] - 1), 1) if n > 12 and index[-13] else None
    g_last = {}
    for g, ser in groups.items():
        v = ser[-1]; v12 = ser[-13] if n > 12 else None
        g_last[g] = {"last": v, "mom": round(v - ser[-2], 1) if v is not None and ser[-2] is not None else None,
                     "yoy_pct": round(100.0 * (v / v12 - 1), 1) if v is not None and v12 else None}
    onset = _onset_month(oni_current, cur_year)
    overlay = {"onset": onset, "current": _rel(index, months, onset) if onset else None, "analogs": {}}
    for y in ANALOG_ONSET_YEARS:
        o = _onset_month((oni_analogs or {}).get(y) or (oni_analogs or {}).get(str(y)), y)
        r = _rel(index, months, o) if o else None
        if r:
            overlay["analogs"][str(y)] = r
    return {
        "last_month": months[-1], "index": last, "mom": mom, "yoy_pct": yoy,
        "groups": g_last,
        "series": {"months": months[-36:], "index": index[-36:],
                   "groups": {g: ser[-36:] for g, ser in groups.items()}},
        "overlay": overlay,
        "note": "FAO Food Price Index, 2014–16 = 100; published the first Friday of the month for the previous month.",
    }


def alerts(F):
    """Тревоги по продовольственным ценам — теми же правилами, что климатические.

    Владелец 03.09: «слева не вижу алертов, касающихся динамики цен». Правила сравнивают
    свежий индекс со своей же историей: с уровнем на начало события, с годом назад, с
    максимумом пяти лет и с направлением последних месяцев. Ничего из головы."""
    if not F or F.get("error"):
        return []
    A, ser = [], F["series"]
    idx, months = ser["index"], ser["months"]
    last, month = F["index"], F["last_month"]

    def add(level, title, detail):
        A.append({"level": level, "title": title, "detail": detail, "kind": "food"})

    # 1. пятилетний максимум — редкое событие, кричим
    tail60 = idx[-60:] if len(idx) >= 12 else idx
    if last >= max(tail60):
        add("SHOUT", "World food prices are the highest in five years",
            f"FAO index {last:.1f} in {month}, above every month since {months[-len(tail60)]}")
    elif last >= max(idx[-12:]):
        add("WATCH", "World food prices are at a twelve-month high",
            f"FAO index {last:.1f} in {month}; a year ago {idx[-13]:.1f}" if len(idx) > 12 else f"FAO index {last:.1f}")

    # 2. рост три месяца подряд
    if len(idx) >= 4 and idx[-1] > idx[-2] > idx[-3] > idx[-4]:
        add("WATCH", "Food prices have risen three months in a row",
            f"{idx[-4]:.1f} → {idx[-3]:.1f} → {idx[-2]:.1f} → {idx[-1]:.1f} (FAO index)")

    # 3. группы: сильный годовой рост
    for g, v in sorted((F.get("groups") or {}).items(), key=lambda kv: -(kv[1].get("yoy_pct") or 0)):
        y = v.get("yoy_pct")
        if y is not None and y >= 15:
            add("WATCH", f"{g} prices are {y:+.1f} % against a year ago",
                f"{g} index {v['last']:.1f} in {month}; the group most exposed to El Niño droughts "
                "in South-east Asia and southern Africa is vegetable oils")
        elif y is not None and y <= -15:
            add("WATCH", f"{g} prices are {y:+.1f} % against a year ago",
                f"{g} index {v['last']:.1f} in {month}: a fall this large moves the whole index")

    # 4. от начала события
    ov = F.get("overlay") or {}
    cur = ov.get("current")
    if cur and cur.get("values"):
        vals = [v for v in cur["values"] if v is not None]
        if vals:
            delta = vals[-1] - 100
            if abs(delta) >= 3:
                add("WATCH", f"Food prices are {delta:+.1f} % against the onset of the event",
                    f"onset month {ov.get('onset')} = 100; analogues at the same distance from onset: "
                    + ", ".join(f"{y} {(a['values'][len(cur['values']) - 1] or 100) - 100:+.1f} %"
                                for y, a in (ov.get("analogs") or {}).items()))
    return A
