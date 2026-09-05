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


def build(verbose=False):
    D = _load(ROOT / "latest.json", {})
    J = _load(ROOT / "journal.json", {})
    if not D or not J:
        return None
    today = date.fromisoformat(D.get("generated") or date.today().isoformat())
    since = today - timedelta(days=DAYS)
    items = []
    risks_by_id = {r.get("id"): r for r in (D.get("risks") or [])}

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
        if len(e) == 1:
            items.append({"date": d, "kind": "risk", "title": "New risk: " + (r.get("title") or m.get("title") or rid),
                          "detail": "level " + str(last["v"]) + " · " + (r.get("horizon") or ""),
                          "why": (r.get("plain") or "")[:280], "go": ["risk", rid]})
        else:
            prev = e[-2]
            if prev["v"] != last["v"]:
                items.append({"date": d, "kind": "risk", "title": (r.get("title") or m.get("title") or rid) + ": level " + str(prev["v"]) + " → " + str(last["v"]),
                              "detail": r.get("horizon") or "", "why": (r.get("plain") or "")[:280], "go": ["risk", rid]})

    # 3. тревоги: сравнение с тем, что было неделю назад
    snaps = sorted(SNAP.glob("*.json"))
    old = _snapshot_before(snaps, since)
    since_note = ""
    if not old and snaps:                                    # панель моложе недели: от первого снимка
        old = _load(snaps[0], {})
        since_note = "alerts compared with the first snapshot, " + str(old.get("generated") or "")
    old_titles = {a.get("title") for a in (old.get("alerts") or [])}
    for a in D.get("alerts") or []:
        if a.get("title") not in old_titles:
            items.append({"date": (D.get("generated") or "")[:10], "kind": "alert", "title": (a.get("level") or "") + ": " + (a.get("title") or ""),
                          "detail": (a.get("detail") or "")[:240], "why": "", "go": ["now", "analogs"]})
    cur_titles = {a.get("title") for a in (D.get("alerts") or [])}
    for t in old_titles - cur_titles:
        if t:
            items.append({"date": (D.get("generated") or "")[:10], "kind": "alert", "title": "Alert cleared: " + t,
                          "detail": "", "why": "", "go": ["now", "analogs"]})

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
