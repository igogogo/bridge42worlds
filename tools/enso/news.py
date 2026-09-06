# -*- coding: utf-8 -*-
"""Лента новостей панели: что важного случилось за неделю и что ждать на следующей.

Владелец 05.09: «сделать отдельную вкладку: что когда у нас будет обновляться, новостная лента
именно по нашей тематике — какие важные события на следующую неделю и что важного случилось
на этой неделе и почему; типа news».

ПРАВИЛАМИ, НЕ МОДЕЛЬЮ. Новость здесь — смена ЗНАЧЕНИЯ в журнале (journal.json), новый или
ушедший риск, новая тревога, смена вердикта. У каждой — дата данных, откуда взято, и «почему
это важно» из того же текста, который панель уже показывает у риска или тревоги. Следующая
неделя — из календаря выпусков (background.release_calendar) плюс «за чем следить» из вердикта.
Строится после журнала, в конце refresh; панель читает data/enso/news.json.
"""
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
SNAP = ROOT / "snapshots"
SEEN_FILE = ROOT / "risk-seen.json"
ALERT_FILE = ROOT / "alert-seen.json"   # id риска -> когда впервые увидели (см. шапку)
DAYS = 7

# Какие ряды журнала стоят новости, куда вести и как подписать
WATCHED = {
    "n34_weekly": ("Niño 3.4, weekly", "now", "weekly"),
    "n12_weekly": ("Niño 1+2, weekly", "now", "weekly"),
    "n34_box": ("Niño 3.4, our daily box", "ocean", "surface"),
    "oni": ("ONI, official", "now", "analogs"),
    "roni": ("RONI", "air", "indices"),
    "subsurface_warmest": ("Warmest layer under the equator", "ocean", "moorings"),
    "d20_east": ("Thermocline in the east", "ocean", "moorings"),
    "wind_week": ("Westerly wind, weekly", "air", "wind"),
    "mjo_amp": ("MJO amplitude", "air", "mjo"),
    "wwv": ("Warm water volume", "air", "fuel"),
    "iri_peak": ("Model peak (IRI)", "models", "plume"),
    "models_broke": ("Models broken", "models", "breakdown"),
    "live_mean": ("Live-model centre", "models", "plume"),
    "food_index": ("FAO food price index", "food", "prices"),
    "gulf_sst": ("Persian Gulf SST", "regions", "place"),
    "ohc_2000": ("Ocean heat content 0–2000 m", "trend", "background"),
    "dmi": ("Indian Ocean Dipole", "air", "indices"),
    "risk_index": ("Risk index", "trend", "index"),
    "sst_world": ("World ocean, daily", "trend", "sst_world"),
}


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return default


def _fmt(v, unit, digits):
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        s = f"{v:+.{digits}f}" if unit in ("°C", "σ", "m/s") else f"{v:.{digits}f}"
        return s + (" " + unit if unit else "")
    return str(v)


def _snapshot_before(snaps, when):
    """Последний снимок не новее момента when (для сравнения тревог)."""
    pick = None
    for p in snaps:
        stamp = p.stem[:8]
        try:
            d = datetime.strptime(stamp, "%Y%m%d").date()
        except ValueError:
            continue
        if d <= when:
            pick = p
    return _load(pick, {}) if pick else {}


def _remember(path, ids, today, label=None):
    """Список «когда впервые увидели» — единственный надёжный источник для слова «новый».

    Снимки старше 03.09 не знают id рисков, самый ранний вообще на другом языке, а
    заголовки тревог несут числа: сравнивать не с чем. Поэтому ведём свой список.
    Молчим, когда он только заводится или когда разом пришло больше двух незнакомых id:
    так выглядит не природа, а новые датчики в коде (поймано 06.09 — лента объявила
    новыми двенадцать рисков, висящих неделями).
    """
    reg = _load(path, {})
    fresh = [i for i in ids if i not in reg]
    quiet = (not reg) or len(fresh) > 2
    for i in fresh:
        reg[i] = {"first": today.isoformat(), "quiet": bool(quiet)}
    for i in ids:
        reg[i]["last"] = today.isoformat()
        reg[i].pop("gone", None)                                 # вернулась — снова живая
    if fresh and label:
        print(label + ": запомнили " + str(len(fresh)) + " новых id" + (" (молча)" if quiet else ""))
    path.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return reg


def build(verbose=False):
    D = _load(ROOT / "latest.json", {})
    J = _load(ROOT / "journal.json", {})
    if not D or not J:
        return None
    today = date.fromisoformat(D.get("generated") or date.today().isoformat())
    since = today - timedelta(days=DAYS)
    items = []
    risks_by_id = {r.get("id"): r for r in (D.get("risks") or [])}
    # Снимок недельной давности нужен и рискам, и тревогам: «новый» — тот, кого там не было.
    _all_snaps = sorted(SNAP.glob("*.json"))
    # Панель моложе недели: снимка недельной давности может не быть вовсе (первый — 02.09).
    # Тогда сравниваем с САМЫМ РАННИМ, что есть, иначе «новым» окажется всё подряд.
    OLD_SNAP = _snapshot_before(_all_snaps, since) or (_load(_all_snaps[0], {}) if _all_snaps else {})
    # Свой список «когда впервые увидели» — единственный надёжный источник для слова
    # «новый»: снимки старше 03.09 не знают id, а самый ранний ещё и на другом языке.
    SEEN = _remember(SEEN_FILE, [r for r in risks_by_id if r], today, verbose and "риски")
    ALERTS_NOW = {a.get("id"): a for a in (D.get("alerts") or []) if a.get("id")}
    ASEEN = _remember(ALERT_FILE, list(ALERTS_NOW), today, verbose and "тревоги")
    for aid, a in ALERTS_NOW.items():                            # заголовок нужен строке «снята»
        ASEEN[aid]["title"] = a.get("title") or aid
    ALERT_FILE.write_text(json.dumps(ASEEN, ensure_ascii=False, indent=1), encoding="utf-8")

    # 1. значения
    for key, (title, view, sub) in WATCHED.items():
        m = (J.get("metrics") or {}).get(key)
        if not m or not m.get("entries"):
            continue
        e = m["entries"]
        last = e[-1]
        # у сезонных и месячных рядов «дата данных» — подпись вроде JJA или Aug 2026: для
        # ленты берём день, когда мы её увидели, а подпись оставляем в тексте
        d_raw = str(last.get("d") or "")
        d = d_raw[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", d_raw) else (last.get("seen") or "")[:10]
        if not d or d < since.isoformat():
            continue
        prev = e[-2] if len(e) > 1 else None
        unit, dg = m.get("unit", ""), m.get("digits", 2)
        det = _fmt(last["v"], unit, dg) + (" for " + d_raw if d_raw != d else "") +             (" (was " + _fmt(prev["v"], unit, dg) + " on " + str(prev.get("d")) + ")" if prev else " — first reading")
        items.append({"date": d, "kind": "value", "title": title + ": " + _fmt(last["v"], unit, dg),
                      "detail": det, "why": m.get("src", ""), "go": [view, sub], "key": key})

    # 2. риски: новые и сменившие уровень
    for key, m in (J.get("metrics") or {}).items():
        if not key.startswith("risk:"):
            continue
        e = m.get("entries") or []
        if not e:
            continue
        last = e[-1]
        d = (last.get("d") or "")[:10]
        if not d or d < since.isoformat():
            continue
        rid = key[5:]
        r = risks_by_id.get(rid) or {}
        # НОВЫЙ — ЗНАЧИТ ПОЯВИЛСЯ НА ЭТОЙ НЕДЕЛЕ. Журнал пишет запись только при СМЕНЕ
        # значения, поэтому у риска, который держится месяц на одном уровне, ровно одна
        # запись — и лента каждую неделю объявляла его «новым» (12 таких строк 06.09).
        # Смотрим дату ПЕРВОЙ записи: она и есть день появления.
        first_d = (e[0].get("d") or "")[:10]
        # …и его действительно не было в снимке недельной давности. Журнал знает риски
        # только с того дня, как у них появились устойчивые id (03.09), поэтому одной
        # даты первой записи мало: без этой проверки лента объявляла новыми двенадцать
        # давно висящих рисков (поймано 06.09).
        s = SEEN.get(rid) or {}
        # Новый — тот, кого мы впервые увидели внутри окна и не заводили молча.
        is_new = bool(s.get("first")) and s["first"] >= since.isoformat() and not s.get("quiet")
        if len(e) == 1 and first_d >= since.isoformat() and is_new:
            items.append({"date": d, "kind": "risk", "title": "New risk: " + (r.get("title") or m.get("title") or rid),
                          "detail": "level " + str(last["v"]) + " · " + (r.get("horizon") or ""),
                          "why": (r.get("plain") or "")[:280], "go": ["risk", rid]})
        elif len(e) > 1:
            # Смена уровня. Раньше сюда попадали только риски с историей — теперь ветка
            # ловит и молча заведённые, у которых записи всего одна: без этой проверки
            # сборка ленты падала (поймано 06.09).
            prev = e[-2]
            if prev["v"] != last["v"]:
                items.append({"date": d, "kind": "risk", "title": (r.get("title") or m.get("title") or rid) + ": level " + str(prev["v"]) + " → " + str(last["v"]),
                              "detail": r.get("horizon") or "", "why": (r.get("plain") or "")[:280], "go": ["risk", rid]})

    # 3. тревоги: сравнение с тем, что было неделю назад
    since_note = ""
    day = (D.get("generated") or "")[:10]
    for aid, a in ALERTS_NOW.items():
        s = ASEEN.get(aid) or {}
        if s.get("first") and s["first"] >= since.isoformat() and not s.get("quiet"):
            items.append({"date": s["first"], "kind": "alert", "title": (a.get("level") or "") + ": " + (a.get("title") or ""),
                          "detail": (a.get("detail") or "")[:240], "why": "", "go": ["now", "analogs"]})
    # Снята — значит вчера была, сегодня нет. Печатаем один раз: пометка gone остаётся в
    # списке, иначе строка «снята» висела бы всю неделю после исчезновения.
    changed = False
    for aid, s in ASEEN.items():
        if aid in ALERTS_NOW or s.get("quiet") or s.get("gone"):
            continue
        if (s.get("last") or "") >= since.isoformat():
            items.append({"date": day, "kind": "alert", "title": "Alert cleared: " + (s.get("title") or aid),
                          "detail": "", "why": "", "go": ["now", "analogs"]})
        s["gone"] = day
        changed = True
    if changed:
        ALERT_FILE.write_text(json.dumps(ASEEN, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4. вердикт
    for v in (J.get("verdicts") or [])[-3:]:
        d = (v.get("d") or "")[:10]
        if d and d >= since.isoformat():
            items.append({"date": d, "kind": "verdict", "title": "The verdict changed",
                          "detail": (v.get("v") or "")[:300], "why": "", "go": ["verdict", "history"]})

    order = {"alert": 0, "risk": 1, "verdict": 2, "value": 3}
    items.sort(key=lambda x: (x["date"], -order.get(x["kind"], 9)), reverse=True)

    # следующая неделя: календарь и «за чем следить»
    cal = ((D.get("background") or {}).get("calendar") or {}).get("items") or []
    nxt = [c for c in cal if c.get("in_days") is not None and c["in_days"] <= 10]
    watch = ((D.get("summary") or {}).get("watch")) or []

    out = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "since": since.isoformat(), "until": today.isoformat(),
           "this_week": items[:40], "next_week": nxt, "watch": watch[:6],
           "since_note": since_note,
           "update_note": ("The panel is recomputed by hand after each release worth it — usually daily. "
                           "Last recompute " + str(D.get("stamp") or "") + "."),
           "note": ("Built by rules from the value journal: a line appears when a value, a risk level, an alert "
                    "or the verdict actually changed in the last " + str(DAYS) + " days, with the date of the data. "
                    "Nothing here is written by hand.")}
    (ROOT / "news.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    if verbose:
        print(f"новости: {len(items)} за неделю, {len(nxt)} впереди")
    return out


if __name__ == "__main__":
    build(verbose=True)
