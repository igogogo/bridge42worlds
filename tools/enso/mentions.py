# -*- coding: utf-8 -*-
"""Лента упоминаний: кто и где говорит об Эль-Ниньо. Не измерение, а разговор о событии, и
подписано как таковое (владелец 07.09: «новостная лента из интернета, кто где упоминает»).

Источники, без ключей:
  · Google News RSS по языковым редакциям (en, es, ar, ru, fr, pt, id, zh, de): до ста свежих
    статей на редакцию, заголовок, издание, дата. Основа ленты: из неё и список статей, и
    «кто говорит» по языкам и изданиям, и счёт статей по дням.
  · Bing News RSS — вторая подборка на английском.
  · Просмотры статьи «El Niño» в Википедии по языкам (Wikimedia REST): внимание читателей.
  · GDELT DOC 2.0 (доля мировых новостей с упоминанием, по дням) — необязательная добавка:
    лимит на адрес жёсткий, один запрос в сутки, при 429 берётся прошлая копия.
  · RSS официальных источников, что отвечают (IRI).

    python mentions.py     # обновить data/enso/mentions.json (кэш data/enso/mentions/)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1] / "data" / "enso"
CACHE = ROOT / "mentions"
OUT = ROOT / "mentions.json"
UA = "Mozilla/5.0 (compatible; bridge42worlds-enso/1.0; +https://bridge42worlds.academy)"
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"

# язык → (запрос, hl, gl, ceid, название языка)
EDITIONS = {
    "en": ('"El Niño"', "en-US", "US", "US:en", "English"),
    "es": ('"El Niño"', "es-419", "MX", "MX:es-419", "Spanish"),
    "ar": ("النينيو", "ar", "EG", "EG:ar", "Arabic"),
    "ru": ("Эль-Ниньо", "ru", "RU", "RU:ru", "Russian"),
    "fr": ('"El Niño"', "fr", "FR", "FR:fr", "French"),
    "pt": ('"El Niño"', "pt-BR", "BR", "BR:pt-419", "Portuguese"),
    "id": ('"El Niño"', "id", "ID", "ID:id", "Indonesian"),
    "zh": ("厄尔尼诺", "zh-CN", "CN", "CN:zh-Hans", "Chinese"),
    "de": ('"El Niño"', "de", "DE", "DE:de", "German"),
}
WIKI = {"en": "El_Niño", "es": "El_Niño", "ar": "النينيو", "ru": "Эль-Ниньо", "fr": "El_Niño", "pt": "El_Niño",
        "id": "El_Niño", "zh": "厄尔尼诺现象", "de": "El_Niño"}
RSS = {"iri": ("IRI Columbia, news", "https://iri.columbia.edu/feed/")}
DAYS_WIKI = 90


def _get(url, timeout=60, tries=2, pause=20):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                                   # noqa: BLE001
            last = e
            if getattr(e, "code", None) in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(pause * (i + 1))
                continue
            break
    raise last


def _cached(key, fetch):
    """Свежий ответ или последняя удачная копия; (объект, fetched, fresh, error)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{key}.json"
    try:
        obj = fetch()
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return obj, datetime.now().strftime("%Y-%m-%d %H:%M"), True, ""
    except Exception as e:                                       # noqa: BLE001
        if p.exists():
            return (json.loads(p.read_text(encoding="utf-8")),
                    datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"), False, str(e)[:120])
        return None, None, False, str(e)[:120]


def _rss(xml):
    root = ET.fromstring(xml.strip().encode("utf-8", "replace"))
    out = []
    for it in root.iter("item"):
        t = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        d = (it.findtext("pubDate") or "").strip()
        src_el = it.find("source")
        src = (src_el.text or "").strip() if src_el is not None else ""
        src_url = src_el.get("url") if src_el is not None else ""
        try:
            iso = parsedate_to_datetime(d).strftime("%Y-%m-%d") if d else ""
        except Exception:                                        # noqa: BLE001
            iso = d[:10]
        if t:
            # Google News пишет издание хвостом заголовка: «… - Reuters»
            if not src and " - " in t:
                t, src = t.rsplit(" - ", 1)
            out.append({"title": t.strip(), "url": link, "date": iso, "source": src, "source_url": src_url})
    return out


def gnews(lang):
    q, hl, gl, ceid, _ = EDITIONS[lang]
    u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl={hl}&gl={gl}&ceid={urllib.parse.quote(ceid)}"
    return {"items": _rss(_get(u, tries=1))}


def bing():
    u = "https://www.bing.com/news/search?q=%22El+Ni%C3%B1o%22&format=rss"
    return {"items": _rss(_get(u, tries=1))}


def wiki_views(lang):
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=DAYS_WIKI)
    title = urllib.parse.quote(WIKI[lang].replace(" ", "_"))
    u = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/"
         f"{title}/daily/{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}")
    items = json.loads(_get(u, tries=1)).get("items") or []
    return {"dates": [x["timestamp"][:8] for x in items], "views": [int(x["views"]) for x in items]}


def gdelt_volume():
    q = urllib.parse.quote('"El Nino" OR "El Niño"')
    j = json.loads(_get(f"{GDELT}?query={q}&mode=timelinevol&format=json&timespan=90d", tries=1))
    ser = (j.get("timeline") or [{}])[0].get("data") or []
    return {"dates": [x["date"][:8] for x in ser], "values": [round(float(x["value"]), 4) for x in ser],
            "unit": "% of all monitored articles"}


def official(url):
    items = _rss(_get(url, tries=1))
    enso = [x for x in items if re.search(r"ni[nñ]o|enso|la ni[nñ]a", x["title"], re.I)]
    return {"items": (enso or items)[:12], "enso_only": bool(enso)}


def _fmt(d8):
    return f"{d8[:4]}-{d8[4:6]}-{d8[6:8]}" if len(d8) == 8 and d8.isdigit() else d8


def build(verbose=True):
    t0 = time.time()
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "sources": [], "errors": []}

    def src(key, label, page, res):
        obj, fetched, fresh, err = res
        doc["sources"].append({"key": key, "label": label, "page": page, "fetched": fetched, "fresh": fresh, "error": err})
        if verbose:
            print(f"  {'ok ' if fresh else 'OLD'} {key} {err}")
        return obj

    # 1. статьи по языковым редакциям
    articles, per_lang = [], {}
    for lang, (q, hl, gl, ceid, name) in EDITIONS.items():
        r = src(f"gnews_{lang}", f"Google News, {name} edition, query {q}", "https://news.google.com/", _cached(f"gnews_{lang}", lambda lang=lang: gnews(lang)))
        items = (r or {}).get("items") or []
        per_lang[lang] = {"name": name, "n": len(items), "days": sorted({x["date"] for x in items if x["date"]})}
        for x in items:
            articles.append(dict(x, lang=lang))
        time.sleep(1.5)
    r = src("bing", "Bing News, English", "https://www.bing.com/news", _cached("bing", bing))
    for x in (r or {}).get("items") or []:
        articles.append(dict(x, lang="en", via="bing"))
    # без дублей по заголовку, свежие первыми
    seen, uniq = set(), []
    for a in sorted(articles, key=lambda a: a.get("date") or "", reverse=True):
        k = re.sub(r"\W+", " ", a["title"].lower())[:70]
        if k in seen:
            continue
        seen.add(k); uniq.append(a)
    doc["articles"] = uniq[:300]
    # 2. кто говорит: издания и языки; счёт по дням (только дни, покрытые всеми редакциями)
    by_source = Counter((a.get("source") or a.get("source_url") or "?") for a in uniq)
    doc["top_sources"] = [{"source": s, "n": n} for s, n in by_source.most_common(20)]
    doc["languages"] = [{"lang": l, "name": v["name"], "n": v["n"], "from": v["days"][0] if v["days"] else None}
                        for l, v in per_lang.items()]
    by_day = Counter(a["date"] for a in uniq if a.get("date"))
    days = sorted(by_day)[-14:]
    doc["per_day"] = {"dates": days, "counts": [by_day[d] for d in days],
                      "note": "articles in the feeds by publication day; each language feed holds only its latest hundred, so older days are undercounted"}
    # 3. просмотры Википедии
    wiki = {}
    for lang in WIKI:
        w = src(f"wiki_{lang}", f"Wikipedia pageviews, {lang}: {WIKI[lang]}", f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(WIKI[lang])}",
                _cached(f"wiki_{lang}", lambda lang=lang: wiki_views(lang)))
        if w and w.get("views"):
            vv = w["views"]; l7 = vv[-7:]; base = vv[:-7] or vv
            wiki[lang] = {"title": WIKI[lang], "dates": [_fmt(d) for d in w["dates"]], "views": vv,
                          "last7_per_day": round(sum(l7) / max(1, len(l7))), "base_per_day": round(sum(base) / max(1, len(base)))}
        time.sleep(0.5)
    doc["wiki"] = wiki
    # 4. GDELT — один запрос, при отказе прошлая копия
    g = src("gdelt_volume", "GDELT, share of world news mentioning El Niño, daily", "https://www.gdeltproject.org/", _cached("gdelt_volume", gdelt_volume))
    if g and g.get("values"):
        v = g["values"]; l7, p7 = v[-7:], v[-14:-7]
        m7, mp = sum(l7) / max(1, len(l7)), sum(p7) / max(1, len(p7))
        pk = max(range(len(v)), key=lambda i: v[i])
        doc["gdelt"] = {"dates": [_fmt(d) for d in g["dates"]], "values": v, "unit": g["unit"], "last7": round(m7, 4),
                        "change_pct": round(100 * (m7 / mp - 1)) if mp else None, "peak": {"date": _fmt(g["dates"][pk]), "value": v[pk]}}
    # 5. официальные ленты
    doc["official"] = {}
    for key, (label, url) in RSS.items():
        r = src(f"rss_{key}", label, url, _cached(f"rss_{key}", lambda url=url: official(url)))
        if r and r.get("items"):
            doc["official"][key] = {"label": label, "items": r["items"], "enso_only": r.get("enso_only")}
    # сводка правилами
    parts = []
    if uniq:
        top = doc["top_sources"][:4]
        parts.append(f"{len(uniq)} articles in the last days across {len([l for l in per_lang.values() if l['n']])} languages; "
                     f"most from {', '.join(s['source'] for s in top)}.")
    if wiki.get("en"):
        e = wiki["en"]
        parts.append(f"The English Wikipedia article gets {e['last7_per_day']} views a day this week against {e['base_per_day']} before.")
    if doc.get("gdelt"):
        gd = doc["gdelt"]
        parts.append(f"GDELT: El Niño in {gd['last7']:.2f} % of world news this week"
                     + (f", {gd['change_pct']:+d} % against the week before" if gd.get("change_pct") is not None else "") + ".")
    doc["summary"] = " ".join(parts) or "No attention data yet."
    doc["note"] = ("This is talk about the event, not a measurement of it: what the news feeds carry in nine languages, who "
                   "reads about it on Wikipedia, and what the forecast centres publish. Headlines are shown as written; a "
                   "link goes to the publisher.")
    doc["secs"] = int(time.time() - t0)
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    try:
        import ops as OPSLOG
        stale = [s["key"] for s in doc["sources"] if not s["fresh"]]
        OPSLOG.record_run("mentions", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "ok" if len(stale) <= 2 else "partial", note=doc["summary"][:160], stale=stale)
    except Exception as e:                                       # noqa: BLE001
        print("  журнал прогонов не обновлён:", str(e)[:100])
    if verbose:
        print(f"mentions.json: {OUT.stat().st_size // 1024} КБ, {doc['secs']} с; {len(uniq)} статей, {len(wiki)} языков Википедии")
        print("  ·", doc["summary"])
    return doc


if __name__ == "__main__":
    build()
