# -*- coding: utf-8 -*-
"""Состояние панели одним небольшим файлом — опора чата-исследования.

Зачем это появилось (владелец, 09.09): «что самое опасное в текущем состоянии — это простой
вопрос; агент должен оркестрировать такие вопросы, лезть в вектор, ориентироваться в
структуре». Живая проверка показала, чего не хватало: вектор ищет ПО СМЫСЛУ, а вопрос
«самое опасное» — СТРУКТУРНЫЙ: возьми риски, отсортируй по уровню, посмотри тревоги и
вердикт. Сходство эмбеддингов такого не делает и никогда не сделает: на «что самое опасное»
вектор поднял работу про грозы в США, а на панели в этот момент лежали три риска пятого
уровня и две громкие тревоги.

Поэтому у воркера должна быть не только выдача поиска, но и КАРТА состояния: короткий файл,
где всё главное разложено по полкам и у каждой строки есть свой адрес на панели. Он кладётся
в промпт целиком (он маленький) — и структурные вопросы становятся отвечаемыми, а пометки
[risk:…] — проверяемыми, потому что идентификаторы настоящие.

Что внутри: вердикт дня и индекс риска, риски по убыванию уровня, громкие тревоги, ключевые
показатели журнала с последним значением и переменой, единицы статистики строкой, список
сцен. Английский — как и весь индекс панели.

    python tools/enso/agent_state.py            записать data/enso/agent-state.json
    python tools/enso/agent_state.py --plan     показать, что получится, ничего не писать
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "enso"
OUT = DATA / "agent-state.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Показатели, которые панель держит в верхней полосе: их и кладём как «ключевые».
STRIP = ["n34_weekly", "n34_daily", "oni", "sst_world", "alerts_n", "models_broken",
         "iri_share_below", "food_index", "wind7", "gulf_sst", "risk_index", "wwv_share"]
KEEP_KPI = 26          # сверх полосы добираем самые свежие


def load(name, default=None):
    p = DATA / name
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def first_sentence(t, n=2):
    s = " ".join(str(t or "").split())
    if not s:
        return ""
    parts = s.replace("! ", ". ").replace("? ", ". ").split(". ")
    return ". ".join(parts[:n]).strip().rstrip(".") + ("." if parts else "")


# Общее описание — то, с чего агент начинает думать (владелец 09.09: «надо добавить работу с
# рассуждениями на основе общего описания нашего сайта, потом искать по вектору»). Сначала
# понять, ЧТО у нас вообще есть и как оно устроено, и только потом решать, нужен ли поиск.
ABOUT = (
    "bridge42worlds is a site that parses scientific papers and keeps a live panel on the "
    "El Niño event of 2026-2027. Two kinds of knowledge sit behind this chat. "
    "FIRST, the panel: our own measurements and readings, rebuilt every day from public "
    "sources (NOAA OISST and CPC, ERA5, TAO/TRITON moorings, GODAS, satellite radiance, "
    "FAO food prices and more). It is organised as scenes, and each scene holds charts, "
    "indicators and short notes. On top of the raw numbers we keep four kinds of statement, "
    "and every one of them has an address you can cite: risks (a judgement with a level from "
    "1 to 5, what it rests on and what to watch), alerts (a reading that broke a record or a "
    "threshold today), indicators of the journal (a number with its history, source and date), "
    "and units of our own statistics (a method applied to our series: trends, change points, "
    "clusters, extremes, coherence, epochs and so on). There is also a verdict of the day and "
    "a glossary. SECOND, the works: scientific papers we parsed and adapted, searched by "
    "meaning through a vector index. "
    "How to use the two. The state map below is the WHOLE structure of the panel today, not a "
    "search result: questions about what is most dangerous, what changed, what to watch, what "
    "is at a record are answered from it by sorting and picking, because similarity of words "
    "cannot rank by level or date. The vector search is for meaning: a mechanism, a term, a "
    "comparison with the literature, anything the map does not spell out. Reason from the map "
    "first, ask for a search second."
)

SCENES = [
    ("brief", "Briefing: the whole day in plain words, with live numbers and links."),
    ("verdict", "The verdict of the day: what the panel concludes right now, and why."),
    ("overview", "Overview: every scene as a small tile with one line and a chart."),
    ("news", "News: what changed this week, and the loud readings behind it."),
    ("research", "Research: this chat."),
    ("mentions", "Mentions: how our sources and works talk about the event."),
    ("now", "Now: where the event stands today, with the analogue years beside it."),
    ("ocean", "Ocean: sea surface by region, month by month and day by day."),
    ("radiance", "Satellite: raw radiance from four instruments, deep convection over the box."),
    ("models", "Models: the IRI plume, how the models break, and their revisions."),
    ("air", "Air and fuel: pressure, convection, trade winds, warm water volume, the layers."),
    ("trend", "Dynamics: our daily watch series with trends, bands and change points."),
    ("regions", "Regions: what the event means for named parts of the world."),
    ("food", "Food: FAO price indices and the lag behind the event."),
    ("planet", "Long term: the century-scale record, land and ocean, belts of the planet."),
]


def build():
    d = load("latest.json")
    J = load("journal.json")
    ST = load("stats.json")
    sm = d.get("summary") or {}

    risks = []
    for r in sorted(d.get("risks") or [], key=lambda x: -(x.get("level") or 0)):
        rid = r.get("id") or ""
        if not rid:
            continue
        risks.append({
            "id": "risk:" + rid, "level": r.get("level"), "title": r.get("title") or rid,
            "plain": first_sentence(r.get("plain"), 2),
            "watch": first_sentence(r.get("watch"), 1),
            "hash": "#risk/" + rid,
        })

    alerts = []
    for a in d.get("alerts") or []:
        aid = a.get("id") or ""
        alerts.append({"id": "alert:" + aid, "level": a.get("level"),
                       "title": a.get("title") or aid,
                       "detail": first_sentence(a.get("detail"), 1),
                       "hash": "#now/analogs"})

    kpis, metrics = [], (J.get("metrics") or {})
    def kpi_row(k, m):
        e = m.get("entries") or []
        last = e[-1] if e else None
        prev = e[-2] if len(e) > 1 else None
        if not last:
            return None
        row = {"id": "kpi:" + k, "title": m.get("title") or k, "value": last.get("v"),
               "unit": m.get("unit") or "", "date": last.get("d"), "src": m.get("src") or "",
               "hash": "#overview"}
        if prev and isinstance(last.get("v"), (int, float)) and isinstance(prev.get("v"), (int, float)):
            row["was"] = prev.get("v")
            row["was_date"] = prev.get("d")
        return row
    for k in STRIP:
        m = metrics.get(k)
        if m:
            row = kpi_row(k, m)
            if row:
                kpis.append(row)
    rest = [(k, m) for k, m in metrics.items()
            if not k.startswith("risk:") and k not in STRIP and (m.get("entries") or [])]
    rest.sort(key=lambda kv: (kv[1].get("entries") or [{}])[-1].get("d") or "", reverse=True)
    for k, m in rest[:KEEP_KPI]:
        row = kpi_row(k, m)
        if row:
            kpis.append(row)

    stats = []
    for it in (ST.get("items") or []):
        k0 = (it.get("kpis") or [{}])[0]
        stats.append({"id": "stat:" + (it.get("id") or ""), "title": it.get("title") or "",
                      "scene": it.get("scene") or "overview",
                      "value": (str(k0.get("value")) + " " + (k0.get("unit") or "")).strip()
                               if k0.get("value") is not None else "",
                      "name": k0.get("name") or "",
                      "hash": "#" + (it.get("scene") or "overview")})

    return {
        "about": ABOUT,
        "scenes": [{"id": "scene:" + k, "hash": "#" + k, "text": t} for k, t in SCENES],
        "built": d.get("generated") or d.get("stamp") or "",
        "verdict": first_sentence(sm.get("verdict"), 3),
        "risk_index": d.get("risk_index"),
        "risks": risks, "alerts": alerts, "kpis": kpis, "stats": stats,
        "counts": {"risks": len(risks), "alerts": len(alerts), "kpis": len(kpis), "stats": len(stats)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="показать и не писать")
    a = ap.parse_args()
    st = build()
    body = json.dumps(st, ensure_ascii=False, separators=(",", ":"))
    print(f"состояние панели: рисков {st['counts']['risks']}, тревог {st['counts']['alerts']}, "
          f"показателей {st['counts']['kpis']}, единиц статистики {st['counts']['stats']}; "
          f"{len(body) / 1024:.1f} КБ")
    top = st["risks"][:3]
    for r in top:
        print(f"   {r['level']} {r['id']:28s} {r['title'][:60]}")
    if a.plan:
        return
    OUT.write_text(body, encoding="utf-8")
    print(f"✅ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
