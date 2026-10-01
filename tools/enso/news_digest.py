# -*- coding: utf-8 -*-
"""Дайджест новостей по дням (владелец 01.10): «там, где мы агрегируем новости, добавь дайджест — анализируй
статьи и делай выжимку на английском на каждый день: что произошло, на что стоит обратить внимание; может,
натолкнёт на мысли по анализу или добавлению новых данных».

Вход — mentions.json: заголовки девяти языковых выпусков Google News (как опубликованы, с изданием и языком)
и публикации центров прогноза и ReliefWeb. Тексты статей недоступны: ссылки Google News ведут на страницу-
переадресацию, поэтому выжимка строится по заголовкам, и это сказано на панели. Модель — та же, что пишет
вердикт (DEEPSEEK_API_KEY, ELNINO_LLM_MODEL, по умолчанию deepseek-v4-pro); каждый пункт ссылается на
заголовки, на которых стоит, ссылки проверяются.

Дни копятся в digest.json (лента в mentions.json держит только последние 300 заголовков): сегодня и вчера
пересказываются на каждом прогоне — статьи ещё приходят, прошлые дни — только если заголовков стало больше.

    python news_digest.py           # новые и свежие дни
    python news_digest.py --redo    # пересказать все дни, что есть в ленте
"""
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import safeio                                                     # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "enso"
try:                                       # ключ DeepSeek живёт в .env репозитория, как у всего конвейера
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:                                                # noqa: BLE001
    pass
OUT = DATA / "digest.json"
MODEL = os.environ.get("ELNINO_LLM_MODEL", "deepseek-v4-pro")
KEEP_DAYS = 60
MIN_ARTICLES = 5
REDO_DAYS = 2
MAX_HEADLINES = 160
LANG_NAMES = {"en": "English", "es": "Spanish", "pt": "Portuguese", "zh": "Chinese", "id": "Indonesian", "de": "German",
              "ru": "Russian", "fr": "French", "ar": "Arabic"}

# что панель уже меряет — чтобы «зацепки» не предлагали то, что есть
PANEL_HAS = ("daily and weekly Niño 1+2, 3, 3.4 and 4 sea surface indices; ONI and RONI; comparisons of this event "
             "with 1982, 1997, 2015, 2023 and with every year on record, including whether it is the strongest measured; "
             "the IRI model plume and model scoring; TAO moorings and the subsurface section (GODAS); warm water volume "
             "and upper-300 m heat; westerly wind bursts, the MJO, OLR and the Southern Oscillation; satellite infrared "
             "and microwave over the Pacific; the FAO food price index and monthly World Bank prices of wheat, rice, "
             "maize, sugar, palm oil, soybean oil, coconut oil, arabica coffee, cocoa, fish meal and two fertilisers, "
             "plus commodity futures; river discharge (GloFAS); tropical water vapour; fires (FIRMS); reservoirs in "
             "Brazil and California; forecasts against fact in 50 cities; tide gauges from Peru to Washington that "
             "follow the coastal Kelvin wave, with the highest tides of the season; sea surface boxes for the Persian "
             "Gulf, Mediterranean, Bay of Bengal, Barents Sea, Gulf of Panama, east Australia and three off California; "
             "rain over land boxes; northern-hemisphere circulation regimes and blocking; global temperature, sea ice, "
             "CO2 and sea level")

SYSTEM = ("You write a short daily digest of news headlines about El Niño for a public scientific dashboard. Write in "
          "English only.\n"
          "You get the headlines of one day in up to nine languages, as published and untranslated, each with an id, the "
          "outlet and the language, plus the official publications of forecast and relief centres that day.\n"
          "Rules:\n"
          "- Summarize what the headlines report. Do not add facts, places, numbers or dates that are not in the "
          "headlines. Begin every 'happened' point with who reports it ('Outlets in Peru report…', 'UNICEF says…', "
          "'Several Spanish-language outlets say…'); never state a reported event as a fact in your own voice.\n"
          "- Translate the meaning of non-English headlines; never quote them in another language.\n"
          "- Group repeating stories. Prefer what many outlets or several languages carry, and the official publications.\n"
          "- Every point cites the ids of the headlines it rests on.\n"
          "- 'watch': what is worth following in the coming days because of these reports.\n"
          "- 'leads': ideas for the dashboard's own analysis or for new data it could add, prompted by these reports. "
          "The dashboard already has: " + PANEL_HAS + ". Do not suggest what it already has; say in one clause why the "
          "lead matters.\n"
          "- Plain words, short sentences, no hype, no long dashes.\n"
          "Return JSON with exactly these keys: {\"headline\": one sentence, \"happened\": [{\"text\": str, \"refs\": "
          "[ids]}] (3 to 6 items), \"watch\": [{\"text\": str, \"refs\": [ids]}] (2 to 4 items), \"leads\": [{\"text\": "
          "str, \"kind\": \"data\" or \"analysis\"}] (1 to 3 items), \"regions\": [countries or regions named]}")


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return default


def _clean_title(t, source):
    t = str(t or "").strip()
    if source and t.endswith(" - " + source):
        t = t[: -len(source) - 3]
    return re.sub(r"\s+", " ", t)[:220]


def _norm(t):
    return re.sub(r"[^\w]+", " ", t.lower()).strip()


def day_items(M, day):
    """Заголовки дня без повторов, вперемешку по языкам (иначе крупный язык забивает лимит), плюс официальные."""
    by_lang, seen = {}, set()
    for a in M.get("articles") or []:
        if str(a.get("date", ""))[:10] != day:
            continue
        t = _clean_title(a.get("title"), a.get("source"))
        n = _norm(t)
        if not t or n in seen:
            continue
        seen.add(n)
        by_lang.setdefault(a.get("lang") or "?", []).append({"t": t, "u": a.get("url"), "o": a.get("source"), "l": a.get("lang")})
    items, i = [], 0
    while len(items) < MAX_HEADLINES and any(i < len(v) for v in by_lang.values()):
        for lg in sorted(by_lang):
            if i < len(by_lang[lg]) and len(items) < MAX_HEADLINES:
                items.append(by_lang[lg][i])
        i += 1
    off = []
    for key, blk in (M.get("official") or {}).items():
        for it in (blk or {}).get("items") or []:
            if str(it.get("date", ""))[:10] == day:
                off.append({"t": _clean_title(it.get("title"), it.get("source")), "u": it.get("url"), "o": it.get("source") or (blk or {}).get("label"), "l": "en", "official": True})
    return items, off


def ask(day, items, off):
    from openai import OpenAI
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    refs = {}
    lines = []
    for i, it in enumerate(off + items):
        rid = f"{'o' if it.get('official') else 'h'}{i + 1}"
        refs[rid] = it
        lines.append({"id": rid, "lang": it.get("l"), "outlet": it.get("o"), "title": it.get("t"), **({"official": True} if it.get("official") else {})})
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=180)
    r = client.chat.completions.create(
        model=MODEL, temperature=0.2, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": f"Day: {day}\nHeadlines and publications:\n" + json.dumps(lines, ensure_ascii=False)}])
    out = json.loads(r.choices[0].message.content)
    usage = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else None
    return out, refs, usage


def tidy(out, refs):
    """Только то, что разрешено форматом, ссылки — только на существующие заголовки."""
    def pts(key, lim, with_refs=True):
        res = []
        for p in (out.get(key) or [])[:lim]:
            if isinstance(p, str):
                p = {"text": p}
            if not isinstance(p, dict) or not str(p.get("text") or "").strip():
                continue
            q = {"text": re.sub(r"\s*—\s*", ", ", str(p["text"]).strip())[:400]}
            if with_refs:
                q["refs"] = [x for x in (p.get("refs") or []) if isinstance(x, str) and x in refs][:6]
            else:
                q["kind"] = p.get("kind") if p.get("kind") in ("data", "analysis") else "analysis"
            res.append(q)
        return res
    used = set()
    happened, watch = pts("happened", 6), pts("watch", 4)
    for p in happened + watch:
        used.update(p["refs"])
    return {"headline": re.sub(r"\s*—\s*", ", ", str(out.get("headline") or "").strip())[:300],
            "happened": happened, "watch": watch, "leads": pts("leads", 3, with_refs=False),
            "regions": [str(x)[:40] for x in (out.get("regions") or [])[:12] if isinstance(x, str)],
            "refs": {k: refs[k] for k in sorted(used)}}


def build(redo=False, verbose=True):
    t0 = time.time()
    M = _load(DATA / "mentions.json", {})
    D = _load(OUT, {"days": []})
    have = {d["date"]: d for d in D.get("days") or []}
    counts = Counter(str(a.get("date", ""))[:10] for a in M.get("articles") or [])
    today = date.today()
    fresh_from = (today - timedelta(days=REDO_DAYS - 1)).isoformat()
    todo = []
    for day, n in sorted(counts.items()):
        if n < MIN_ARTICLES or not day:
            continue
        old = have.get(day)
        if redo or not old or day >= fresh_from or n > (old.get("n_articles") or 0):
            todo.append(day)
    errors = []
    for day in todo:
        items, off = day_items(M, day)
        if len(items) < MIN_ARTICLES:
            continue
        try:
            out, refs, usage = ask(day, items, off)
            rec = tidy(out, refs)
        except Exception as e:                                   # noqa: BLE001
            errors.append(f"{day}: {str(e)[:160]}")
            if verbose:
                print(f"  {day}: НЕ ВЫШЛО — {str(e)[:120]}", flush=True)
            continue
        langs = Counter(it.get("l") for it in items)
        rec.update({"date": day, "n_articles": counts[day], "n_used": len(items), "n_official": len(off),
                    "langs": {LANG_NAMES.get(k, k): v for k, v in langs.most_common()},
                    "model": MODEL, "made": datetime.now().strftime("%Y-%m-%d %H:%M"), "usage": usage,
                    "partial": day >= today.isoformat()})
        have[day] = rec
        if verbose:
            print(f"  {day}: {counts[day]} заголовков, {len(langs)} языков → пунктов {len(rec['happened'])}/{len(rec['watch'])}/{len(rec['leads'])}; {rec['headline'][:90]}", flush=True)
    days = sorted(have.values(), key=lambda d: d["date"], reverse=True)[:KEEP_DAYS]
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": MODEL, "days": days, "errors": errors,
           "secs": round(time.time() - t0),
           "note": "A model's summary of each day's headlines in nine languages and of the forecast and relief centres' "
                   "publications: what the news carries, not a measurement. Article texts are not read, only headlines, "
                   "so a point is never more certain than the headlines it cites; each point links to them. Leads are "
                   "ideas for this dashboard's own analysis or data, prompted by the news."}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, allow_nan=False))
    print(f"digest.json: дней {len(days)}, пересказано сейчас {len(todo) - len(errors)}, ошибок {len(errors)}, {doc['secs']} с")
    return doc


if __name__ == "__main__":
    build(redo="--redo" in sys.argv)
