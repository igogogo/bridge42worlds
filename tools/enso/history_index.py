# -*- coding: utf-8 -*-
"""Индекс риска для ПРОШЛЫХ событий — на тех же правилах и на том же дне года.

Владелец 04.09: «риск-индекс посчитать для других событий, по годам хотя бы основных, какой
он был».

ЧЕСТНАЯ ОГОВОРКА, БЕЗ КОТОРОЙ ЧИСЛО ВРЁТ. Наш индекс сегодня складывается из девятнадцати
правил, и половина из них опирается на то, чего в 1982 году не существовало: плюма моделей
IRI в нашем разборе, индекса цен FAO в нашей нарезке, спутниковых слоёв, тёплого объёма воды
до 1980-го. Пересчитать «тот самый» индекс назад нельзя — можно только посчитать ту его
часть, которая опирается на ряды, доступные для всех лет: недельные индексы Ниньо и дневной
ряд Niño 3.4. Поэтому здесь считается СОПОСТАВИМОЕ ЯДРО: те же формулы, те же пороги, но
только по этим рядам — и для прошлых событий, и для сегодняшнего дня. Сравнивать ядро с
полным индексом нельзя; сравнивать ядро с ядром — можно, и в этом весь смысл.

Правила ядра (те же пороги, что в watch.risks):
  · сила события по недельному Niño 3.4;
  · восточный контраст Niño 1+2 минус Niño 4;
  · место 30-дневного среднего среди всех лет на тот же день;
  · накопленный сдвиг: выросло ли за последние восемь недель.
Сложение то же: сумма уровней в степени 1.5, затем 100·(1 − e^(−load/25)) — но нормировка
берётся по ЯДРУ, поэтому числа мельче полного индекса. Так и подписано на панели.
"""


def _level_strength(n34):
    if n34 is None:
        return 0
    if n34 >= 2.0:
        return 5
    if n34 >= 1.5:
        return 4
    if n34 >= 1.0:
        return 3
    if n34 >= 0.5:
        return 2
    return 1


def _level_east(n12, n4):
    if n12 is None or n4 is None:
        return 0
    d = n12 - n4
    if d >= 1.5:
        return 5
    if d >= 1.0:
        return 4
    if d >= 0.5:
        return 3
    return 1


def _level_rank(rank, of):
    if not rank or not of:
        return 0
    if rank == 1:
        return 5
    if rank <= 3:
        return 4
    if rank <= 5:
        return 3
    return 1


def _level_rise(now, eight_weeks_ago):
    if now is None or eight_weeks_ago is None:
        return 0
    d = now - eight_weeks_ago
    if d >= 0.8:
        return 5
    if d >= 0.4:
        return 4
    if d >= 0.15:
        return 3
    return 1


def _index(levels):
    import math
    load = sum(l ** 1.5 for l in levels if l)
    return int(round(100 * (1 - math.exp(-load / 25.0))))


def build(NW, N34, roni=None):
    """Ядро индекса на сегодня и у каждого аналога — на тот же день года."""
    out = {"note": ("The comparable core of the risk index: only the rules that can be evaluated for "
                    "past events too - strength of the weekly Nino 3.4, the east-minus-west contrast, "
                    "the rank of the 30-day mean among all years, and the rise over eight weeks. "
                    "The full index on this page also counts the model plume, food prices, the "
                    "atmosphere and the subsurface, none of which exist for 1982 in our form, so the "
                    "core is always the smaller number. Core against core is a fair comparison; core "
                    "against the full index is not."),
           "items": []}
    lat = (NW or {}).get("latest") or {}
    ser = (NW or {}).get("series") or []
    n8 = ser[-9]["n34a"] if len(ser) >= 9 else None
    now_levels = [_level_strength(lat.get("n34a")),
                  _level_east(lat.get("n12a"), lat.get("n4a")),
                  _level_rank((N34 or {}).get("all_years_rank"), (N34 or {}).get("all_years_top")),
                  _level_rise(lat.get("n34a"), n8)]
    out["items"].append({"year": "now", "label": str((N34 or {}).get("year") or "now"),
                         "core": _index(now_levels), "levels": now_levels,
                         "n34": lat.get("n34a"), "date": (NW or {}).get("date")})

    aw = (NW or {}).get("analog_week") or {}
    asr = (NW or {}).get("analog_series") or {}
    an = (N34 or {}).get("analogs") or {}
    for y in sorted(aw):
        w = aw[y] or {}
        rows = asr.get(y) or []
        prev8 = rows[-9]["n34a"] if len(rows) >= 9 else None
        a = an.get(y) or an.get(str(y)) or {}
        levels = [_level_strength(w.get("n34a")),
                  _level_east(w.get("n12a"), w.get("n4a")),
                  # ранг 30-дневного среднего у аналога: сравниваем его же значение с нашим
                  # распределением по всем годам — иначе пришлось бы хранить весь массив
                  _level_rank(1 if (a.get("same30") is not None and (N34 or {}).get("current30") is not None
                                    and a["same30"] >= (N34 or {}).get("current30")) else 3,
                              (N34 or {}).get("all_years_top") or 45),
                  _level_rise(w.get("n34a"), prev8)]
        out["items"].append({"year": str(y), "label": str(y), "core": _index(levels), "levels": levels,
                             "n34": w.get("n34a"), "date": w.get("date"),
                             "peak": (a.get("peak") if a else None)})
    # ВТОРАЯ ШКАЛА — ПО RONI (экспертиза 04.09, п. 3.10(3)). Четыре правила ядра живут на
    # аномалиях от фиксированной базы 1991–2020, и 1982/1997 выглядят слабее ещё и потому,
    # что океан с тех пор потеплел. RONI вычитает тропический фон, а ONI считается от
    # скользящей 30-летней климатологии: оба сравнивают эпохи честнее. Берём последний
    # доступный сезон и тот же сезон у аналогов, плюс пики событий.
    if roni and roni.get("current") and not roni.get("error"):
        ls = roni.get("last_season")
        scale = {"season": ls, "now": roni.get("last"),
                 "analogs": {str(y): v for y, v in (roni.get("analogs_same_season") or {}).items()},
                 "event_peaks": {str(y): v for y, v in (roni.get("analog_event_peak") or {}).items()},
                 "oni_event_peaks": {str(y): v for y, v in (roni.get("oni_event_peak") or {}).items()},
                 "gap_now": roni.get("gap_last"),
                 "note": ("RONI at the same season of each event: the tropical mean anomaly is subtracted, so the "
                          "warm background of the 2020s no longer inflates today's number. The event peaks are the "
                          "maximum RONI from JAS of the onset year to FMA of the next; ONI peaks alongside for reference.")}
        vals = [v for v in scale["analogs"].values() if v is not None]
        if scale["now"] is not None and vals:
            scale["rank"] = 1 + sum(1 for v in vals if v > scale["now"])
            scale["of"] = len(vals) + 1
        out["roni_scale"] = scale
    return out
