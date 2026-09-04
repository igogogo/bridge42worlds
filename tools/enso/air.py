# -*- coding: utf-8 -*-
"""Атмосфера, топливо, слои и цены поимённо — четыре блока, которых панели не хватало.

Владелец 04.09: «бери первое, второе, третье, четвёртое — всё делай».

ПОЧЕМУ ЭТО НЕ УКРАШЕНИЕ. До сих пор дашборд мерил ТОЛЬКО ОКЕАН. Эль-Ниньо — связка океана
и атмосферы: вода может греться, а воздух не отвечать, и тогда телесвязей (засух, дождей,
урожая) не будет — не будет и того, ради чего мы вообще считаем регионы. Здесь появляется
атмосферная половина: давление (SOI), конвекция (OLR) и пассаты (ветер 850 гПа).

ТОПЛИВО. Тёплый объём воды в верхних 300 метрах — единственный ИЗМЕРЯЕМЫЙ признак того, есть
ли событию чем расти: он опережает Niño 3.4 на два-три сезона. Пик оценки мы до сих пор брали
из аналогов и моделей, то есть из чужих предположений; здесь — из градусника.

СЛОИ. Спутниковые ряды UAH по четырём этажам: нижняя тропосфера, средняя, тропопауза, нижняя
стратосфера. Событие проходит вверх с задержкой, и задержку мы не постулируем, а считаем
по самим рядам.

ЦЕНЫ. Индекс FAO — одно число на всю еду. Pink Sheet Всемирного банка даёт товары поимённо,
и это важно: Эль-Ниньо бьёт не по «еде», а по пальмовому маслу, рису и рыбной муке.
"""
import math

MONTHS_BACK = 60          # сколько месяцев рядов отдаём панели
LAG_MAX = 12              # в каких пределах ищем опережение


def _last(d, n=1):
    ks = sorted(d)
    return [(k, d[k]) for k in ks[-n:]]


def _tail(d, n=MONTHS_BACK):
    ks = sorted(d)[-n:]
    return {"months": ks, "values": [round(d[k], 3) for k in ks]}


def _mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def _corr(a, b):
    n = len(a)
    if n < 24:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def best_lead(src, dst, lag_max=LAG_MAX):
    """На сколько месяцев ряд src опережает ряд dst, и насколько тесно они связаны.

    Опережение не постулируем («считается, что объём ведёт на два сезона»), а ищем перебором:
    для каждого сдвига считаем корреляцию и берём лучший. Так число на панели всегда
    относится к ТЕКУЩИМ данным, а не к учебнику."""
    best = (None, None)
    ks = sorted(set(src) & set(dst))
    if len(ks) < 60:
        return {"lag": None, "r": None}
    for lag in range(0, lag_max + 1):
        xs, ys = [], []
        for k in ks:
            y, m = int(k[:4]), int(k[5:])
            m2 = m + lag
            y2 = y + (m2 - 1) // 12
            m2 = (m2 - 1) % 12 + 1
            k2 = f"{y2}-{m2:02d}"
            if k in src and k2 in dst:
                xs.append(src[k]); ys.append(dst[k2])
        r = _corr(xs, ys)
        if r is not None and (best[1] is None or r > best[1]):
            best = (lag, r)
    return {"lag": best[0], "r": round(best[1], 2) if best[1] is not None else None}


# ---------------------------------------------------------------- сцепка
def coupling(soi, olr, uw, uc, ue):
    """Отвечает ли воздух океану. Три признака, каждый в стандартных отклонениях.

    Пороги мягкие и одинаковые (−0.5 σ): нам нужен не приговор, а честный счёт «сколько из
    трёх». Знаки: SOI отрицателен, когда давление над Дарвином выше, чем над Таити (пассаты
    слабеют); OLR отрицателен, когда над центральной частью океана вырос облачный столб —
    то есть конвекция ПЕРЕЕХАЛА туда, и именно это включает телесвязи; ветер 850 гПа
    отрицателен, когда пассаты ослабли или развернулись на западные.
    """
    def one(d, name, title):
        if not d:
            return None
        k, v = _last(d)[0]
        m3 = _mean([d[x] for x in sorted(d)[-3:]])
        return {"key": name, "title": title, "date": k, "value": round(v, 2),
                "mean3": round(m3, 2) if m3 is not None else None,
                "on": v <= -0.5, "series": _tail(d)}

    parts = [one(soi, "soi", "Southern Oscillation Index"),
             one(olr, "olr", "Convection at the date line (OLR)"),
             one(uw, "u850_west", "Trade wind, western Pacific"),
             one(uc, "u850_centre", "Trade wind, central Pacific"),
             one(ue, "u850_east", "Trade wind, eastern Pacific")]
    parts = [p for p in parts if p]
    core = [p for p in parts if p["key"] in ("soi", "olr", "u850_west")]
    score = sum(1 for p in core if p["on"])
    verdict = ("the atmosphere answers the ocean" if score == 3 else
               "the atmosphere answers in part" if score == 2 else
               "the atmosphere is barely answering" if score == 1 else
               "the ocean is warming alone")
    return {"parts": parts, "score": score, "of": len(core), "verdict": verdict,
            "note": ("El Niño is a coupling of ocean and air, not a warm patch of water. These three "
                     "say whether the air is answering: pressure across the Pacific, the cloud tower "
                     "over the date line, and the trade winds. When they stop answering, the "
                     "teleconnections that carry the event to harvests stop with them.")}


# ---------------------------------------------------------------- топливо
def fuel(wwv, t300, n34_monthly):
    """Тёплый объём воды: сколько топлива осталось и когда оно начало расходоваться."""
    if not wwv:
        return None
    ks = sorted(wwv)
    last_k = ks[-1]
    last_v = wwv[last_k]
    # пик за текущее событие: ищем максимум за последние два года
    recent = ks[-24:]
    peak_k = max(recent, key=lambda k: wwv[k])
    since = (int(last_k[:4]) - int(peak_k[:4])) * 12 + int(last_k[5:]) - int(peak_k[5:])
    lead = best_lead(wwv, n34_monthly) if n34_monthly else {"lag": None, "r": None}
    # доля от рекорда ряда — чтобы «много» и «мало» были сравнимы с историей
    hi = max(wwv.values())
    levels = {k: round(v / 1e14, 2) for k, v in same_month_levels(wwv, last_k).items()}
    return {"levels": levels,
            "date": last_k, "value": last_v, "peak_date": peak_k, "peak_value": wwv[peak_k],
            "months_since_peak": since, "share_of_record": round(100 * last_v / hi) if hi else None,
            "record": hi, "lead": lead,
            "discharging": since >= 2 and last_v < wwv[peak_k] * .85,
            "t300": ({"date": _last(t300)[0][0], "value": _last(t300)[0][1], "series": _tail(t300)}
                     if t300 else None),
            "series": _tail(wwv),
            "note": ("Warm water volume is the fuel gauge: the heat piled up in the upper 300 m of the "
                     "equatorial Pacific before it reaches the surface. It leads the surface index, so it "
                     "answers the one question the models only guess at — whether the event still has "
                     "something to grow on. The lead is measured on our own data, not assumed.")}


# ---------------------------------------------------------------- слои
LAYER_TITLES = {"tlt": "Lower troposphere", "tmt": "Mid troposphere",
                "ttp": "Tropopause", "tls": "Lower stratosphere"}
LAYER_ORDER = ["tls", "ttp", "tmt", "tlt"]


def layers(uah, n34_monthly):
    """Как событие поднимается по этажам атмосферы: значение, задержка и знак на каждом.

    Стратосфера при Эль-Ниньо ведёт себя ПРОТИВОПОЛОЖНО тропосфере — стынет. Поэтому знак
    задержки там ищется по обратной связи, и мы говорим об этом словами, а не прячем минус.
    """
    out = []
    for key in LAYER_ORDER:
        d = (uah or {}).get(key)
        if not d:
            continue
        trop, globe = d.get("tropics") or {}, d.get("globe") or {}
        if not trop:
            continue
        k, v = _last(trop)[0]
        lead = best_lead(n34_monthly, trop) if n34_monthly else {"lag": None, "r": None}
        # С ЧЕМ СРАВНИВАТЬ. Владелец 04.09: «нет сопоставлений с другими событиями, нечем
        # сравнивать; все графики должны иметь смысл». Для каждого прошлого сильного события
        # берём МАКСИМУМ этого слоя в году ПОСЛЕ его зимнего пика — именно тогда атмосфера
        # отвечает океану. Получается честная планка: столько же было тогда.
        after = {}
        for ay in (1982, 1997, 2015, 2023):
            win = [trop[f"{ay + 1}-{m:02d}"] for m in range(1, 13) if f"{ay + 1}-{m:02d}" in trop]
            if win:
                after[str(ay)] = round(max(win), 2)
        out.append({"key": key, "title": LAYER_TITLES.get(key, key), "date": k,
                    "tropics": round(v, 2), "globe": round(globe.get(k, float("nan")), 2) if k in globe else None,
                    "lag": lead["lag"], "r": lead["r"], "after_events": after,
                    "series": _tail(trop, 36)})
    return {"items": out,
            "after_note": ("The dashed levels are what each floor reached in the year AFTER the peak of a "
                           "past strong El Nino - that is when the atmosphere answers. Being below them "
                           "today is normal: this event has not peaked yet."),
            "note": ("Four floors of the atmosphere, from satellites. The ocean heats the troposphere "
                     "with a delay of several months — the delay here is measured against our own Niño 3.4 "
                     "series, not taken from a textbook. The stratosphere does the opposite: during a "
                     "strong El Niño it cools, which is why its correlation is weak or negative.")}


# ---------------------------------------------------------------- цены поимённо
EL_NINO_LINK = {
    "palm_oil": "Indonesia and Malaysia dry out in an El Niño; palm oil is the first to react.",
    "coconut_oil": "The Philippines dry out; the harvest falls with a lag of two or three quarters.",
    "soybean_oil": "Argentina and southern Brazil usually get MORE rain in an El Niño — this one often falls.",
    "rice": "South and South-East Asia dry out; the monsoon weakens.",
    "wheat": "Australia is the classic loser of an El Niño; India and southern Africa follow.",
    "maize": "Southern Africa dries out, the United States are usually unaffected.",
    "sugar": "India and Thailand dry out; Brazil gets more rain and often gains.",
    "coffee_arabica": "Brazil and Colombia — mixed: more rain in the south, drought in the north.",
    "cocoa": "West Africa dries out; the harvest falls with a lag of two quarters.",
    "fishmeal": "Peru: the anchoveta leaves the warm water. This is the most direct price signal of an El Niño.",
    "fertilizer_dap": "Not a weather channel: it is here because fertiliser cost decides the NEXT harvest.",
    "fertilizer_urea": "Same: energy prices and fertiliser set the cost of the next sowing.",
}


def commodities(pink, onset=None):
    """Товары поимённо: сейчас, месяц назад, год назад и от начала события."""
    out = []
    for key, rec in (pink or {}).items():
        ser = rec.get("series") or {}
        ks = sorted(ser)
        if not ks:
            continue
        last_k = ks[-1]
        last = ser[last_k]

        def at(back):
            i = len(ks) - 1 - back
            return ser[ks[i]] if 0 <= i < len(ks) else None

        mom, yoy = at(1), at(12)
        base = ser.get(onset) if onset else None
        out.append({
            "key": key, "name": rec.get("name") or key, "unit": rec.get("unit") or "",
            "date": last_k, "value": last,
            "mom_pct": round(100 * (last / mom - 1), 1) if mom else None,
            "yoy_pct": round(100 * (last / yoy - 1), 1) if yoy else None,
            "since_onset_pct": round(100 * (last / base - 1), 1) if base else None,
            "onset": onset if base else None,
            "why": EL_NINO_LINK.get(key, ""),
            "series": {"months": ks[-36:], "values": [ser[k] for k in ks[-36:]]},
        })
    out.sort(key=lambda r: -(abs(r["since_onset_pct"]) if r["since_onset_pct"] is not None
                             else abs(r["yoy_pct"] or 0)))
    return {"items": out, "as_of": out[0]["date"] if out else None,
            "note": ("World Bank Pink Sheet, monthly, free and without registration. The FAO index is one "
                     "number for all food; El Niño does not hit “food”, it hits palm oil, rice and fishmeal "
                     "by name. Sorted by the move since the event began — which is a coincidence in time, "
                     "not a proof of cause.")}


def onset_paths(pink, onset, analog_onsets=None, span=18):
    """Цена товара в процентах к месяцу начала события, от −6 до +span месяцев: сейчас и в
    прошлые события. Владелец 04.09 (вечер): «since onset не понимаю: почему у нас риски
    растут, а цены падают». Падал АГРЕГАТ (индекс FAO) — от азиатского кризиса 1998-го и
    дешёвой нефти 2015-го; Эль-Ниньо бьёт по товарам поимённо, и их пути от начала события
    выглядят иначе. Pink Sheet идёт с 1960 года, поэтому и 1982-й, и 1997-й на месте."""
    out = {"onset": onset, "span": span, "from": -6, "items": [],
           "note": ("Each commodity as a percentage of its price in the onset month, this event against the "
                    "same months after the onset of the strongest past events. The aggregate FAO index fell "
                    "after the past onsets for reasons outside the weather; the commodities El Niño touches "
                    "by name did not necessarily follow it.")}
    if not onset:
        return out
    for key, rec in (pink or {}).items():
        ser = rec.get("series") or {}
        ks = sorted(ser)
        if not ks:
            continue

        def rel(on):
            if on not in ser or not ser[on]:
                return None
            base = ser[on]
            i0 = ks.index(on)
            vals = []
            for k in range(-6, span + 1):
                j = i0 + k
                v = ser[ks[j]] if 0 <= j < len(ks) else None
                vals.append(None if v is None else round(100.0 * v / base, 1))
            return {"onset": on, "from": -6, "values": vals, "base": base}

        cur = rel(onset)
        if not cur:
            continue
        an = {}
        for y, on in (analog_onsets or {}).items():
            r = rel(on) if on else None
            if r:
                an[str(y)] = r
        last_i = max(i for i, v in enumerate(cur["values"]) if v is not None)
        out["items"].append({
            "key": key, "name": rec.get("name") or key, "unit": rec.get("unit") or "",
            "why": EL_NINO_LINK.get(key, ""),
            "current": cur, "analogs": an,
            "now_pct": round(cur["values"][last_i] - 100, 1), "months_in": last_i - 6,
            "at6": {y: (None if r["values"][12] is None else round(r["values"][12] - 100, 1)) for y, r in an.items()},
            "at12": {y: (None if r["values"][18] is None else round(r["values"][18] - 100, 1)) for y, r in an.items()},
        })
    out["items"].sort(key=lambda x: -abs(x["now_pct"]))
    return out


def build(parsed, n34_monthly, onset=None):
    """Собрать весь блок из уже разобранных источников."""
    uah = {k[4:]: v for k, v in parsed.items() if k.startswith("uah_") and v}
    soi = parsed.get("soi") or {}
    soi_last = sorted(soi)[-1] if soi else None
    return {
        "_soi_levels": same_month_levels(soi, soi_last),
        "coupling": coupling(parsed.get("soi"), parsed.get("olr"), parsed.get("u850_west"),
                             parsed.get("u850_centre"), parsed.get("u850_east")),
        "fuel": fuel(parsed.get("wwv"), parsed.get("t300"), n34_monthly),
        "layers": layers(uah, n34_monthly),
        "commodities": commodities(parsed.get("wb_pink"), onset),
    }


# ---------------------------------------------------------------- риски по этим данным
ANALOG_YEARS = (1982, 1997, 2015, 2023)


def same_month_levels(d, last_key):
    """Сколько было у прошлых сильных событий в ТОТ ЖЕ месяц года.

    Владелец 04.09: «проверь все рисковые карточки, где уместно — покажи прошлый год, где
    уместно — важные годы события». У месячных рядов (объём воды, давление) своего ряда по
    аналогам не нарисуешь на одной картинке — зато можно поставить планки: вот столько было
    в этом же месяце 1997-го. Сравнение по календарю, а не по фазе события: сезонный ход у
    всех один и тот же, и разница в планках — это разница событий."""
    if not d or not last_key or len(last_key) < 7:
        return {}
    mm = last_key[5:7]
    out = {}
    for y in ANALOG_YEARS:
        k = f"{y}-{mm}"
        if k in d and d[k] is not None:
            out[str(y)] = round(float(d[k]), 2)
    return out


def _metric(series, name, unit="σ", step="month", extra=None):
    """Ряд для карточки риска из наших месячных рядов.

    Владелец 04.09: «все карточки рисков справа должны показывать графики со сравнением с
    событиями, а то не с чем сравнивать». У атмосферных рядов аналогов по годам нет —
    вместо них кладём планки: сколько было в год после пика прошлых сильных событий.
    Карточка рисует их пунктиром, и число перестаёт висеть в пустоте."""
    if not series:
        return None
    m = {"name": name, "unit": unit, "step": step,
         "dates": series.get("months"), "values": series.get("values")}
    if extra:
        m.update(extra)
    return m


def risks(A, n34_now=None):
    """Риски, которых без атмосферы, топлива и слоёв просто не существовало.

    Формат тот же, что у остальных правил watch.risks: (заголовок, уровень, горизонт,
    что видно, что это значит, за чем следить, ряд, вид, имя правила).
    """
    out = []
    C, F, L = (A or {}).get("coupling"), (A or {}).get("fuel"), (A or {}).get("layers")

    if C and C.get("of"):
        def v(key):
            return next((p["value"] for p in C["parts"] if p["key"] == key), None)
        if C["score"] >= 2:
            out.append((
                "The air is answering the ocean, so the event can travel", 4, "now",
                f"Southern Oscillation Index {v('soi'):+.1f}, convection at the date line "
                f"{v('olr'):+.1f} standard deviations, trade wind in the west {v('u850_west'):+.1f}. "
                f"{C['score']} of {C['of']} atmospheric signs are in place.",
                "El Niño is not a warm patch of water, it is a coupling: the water heats, the trade winds "
                "give way, the cloud tower moves east, and only then does the event reach harvests on the "
                "other side of the planet. All three are in place now, which is why the regional impacts "
                "on this page are worth taking seriously.",
                "the same three: if the winds return and the convection moves back west, the event stays "
                "in the ocean and the teleconnections fade",
                _metric((next((p for p in C["parts"] if p["key"] == "soi"), {}) or {}).get("series"),
                        "Southern Oscillation Index, monthly",
                        extra={"levels": (A or {}).get("_soi_levels") or {}}),
                "climate", "coupling_on"))
        else:
            out.append((
                "The ocean is warming, the air is not answering", 3, "now",
                f"Only {C['score']} of {C['of']} atmospheric signs are in place.",
                "The water is warm, but pressure, convection and the winds have not followed. Without that "
                "coupling the event stays a warm patch of ocean and the distant impacts may not arrive.",
                "the Southern Oscillation Index and the convection at the date line",
                None, "climate", "coupling_off"))

    if F and F.get("share_of_record") is not None:
        share, since = F["share_of_record"], F.get("months_since_peak")
        lead = (F.get("lead") or {}).get("lag")
        if share >= 90 and not F.get("discharging"):
            out.append((
                "The fuel is at its record and has not started to burn", 5,
                f"{lead or 6}–{(lead or 6) + 3} months",
                f"Warm water volume {F['value'] / 1e14:.2f}·10¹⁴ m³, {share} % of the highest value of the "
                f"series since 1980; the peak was {'this month' if not since else str(since) + ' months ago'}. "
                f"On our own data this gauge leads the surface index by {lead} months.",
                "The heat that will surface later is already piled up under the equator, and it is at a record "
                "for the whole series. This is measured, not forecast: the surface has not yet shown what is "
                "already stored below. While the gauge is not falling, the event has something to grow on.",
                "the monthly PMEL update: the first clear fall of the volume is the earliest honest sign that "
                "the peak is near",
                _metric({"months": (F.get("series") or {}).get("months"),
                         "values": [None if v is None else round(v / 1e14, 2)
                                    for v in ((F.get("series") or {}).get("values") or [])]},
                        "Warm water volume, monthly", unit="·10¹⁴ m³",
                        extra={"levels": (F.get("levels") or {})}),
                "climate", "fuel_charged"))
        elif F.get("discharging"):
            out.append((
                "The fuel is discharging: the peak is close", 4, f"{lead or 6} months",
                f"Warm water volume has fallen to {share} % of the record, {since} months after its peak.",
                "The heat stored under the equator is being spent. In past events the surface peaked within "
                "half a year of this turn.",
                "the volume: a steady fall means the event has passed its charge phase",
                None, "climate", "fuel_discharging"))

    if L and L.get("items"):
        tlt = next((x for x in L["items"] if x["key"] == "tlt"), None)
        if tlt and tlt.get("lag") is not None:
            out.append((
                "The atmosphere is still catching up, by three floors", 3, f"{tlt['lag']} months",
                f"Satellite lower troposphere in the tropics {tlt['tropics']:+.2f} °C; on our own data this "
                f"layer follows Niño 3.4 with a delay of {tlt['lag']} months (correlation {tlt['r']}).",
                "The ocean heats the air, not the other way round, and the air takes months to answer. That is "
                "why the warmest months of the whole record usually arrive AFTER the peak of an El Niño, not "
                "during it — and why the year that follows this one is the one to watch.",
                "the monthly satellite layers: the tropics react first, the global mean follows",
                _metric(tlt.get("series"), "Lower troposphere, tropics", unit="°C",
                        extra={"levels": tlt.get("after_events")}),
                "climate", "layers_lag"))
    return out


def alerts(A):
    """Тревоги по ценам поимённо: движение с начала события, а не «за год»."""
    out = []
    for c in ((A or {}).get("commodities") or {}).get("items", [])[:4]:
        v = c.get("since_onset_pct")
        if v is None or abs(v) < 15:
            continue
        out.append({"level": "WATCH", "kind": "food",
                    "title": f"{c['name']}: {v:+.0f} % since the event began",
                    "detail": (f"{c['value']} {c['unit']} in {c['date']}, against the onset month "
                               f"{c.get('onset')}. {c.get('why', '')} A coincidence in time is not a cause: "
                               "prices move for many reasons at once.")})
    return out
