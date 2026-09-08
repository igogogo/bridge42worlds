# -*- coding: utf-8 -*-
"""Индекс панели для чата-исследования: наша часть, которую вектор ещё не знал.

Записка сессии панели 08.09 (ИССЛЕДОВАНИЕ-ЧАТ-КОНЦЕПТ-2026-09-08.md, п. 2): вектор знает
только статьи, а половина знания живёт на панели — риски, тревоги, показатели, термины,
сцены, вердикт. Четыреста-пятьсот коротких английских текстов, у каждого адрес на панели
и якорь понятий.

ЧТО СОБИРАЕМ (и почему именно так):

  · РИСК — заголовок, простыми словами, свидетельство, за чем следить. Один текст, потому
    что читателю нужен риск целиком, а не его четвертинка;
  · ТРЕВОГА — заголовок и деталь;
  · ПОКАЗАТЕЛЬ ЖУРНАЛА — имя, единица, источник, последнее значение и когда; плюс простое
    объяснение из KPI_PLAIN панели, если оно там есть;
  · ТЕРМИН СЛОВАРЯ — что это и почему важно здесь;
  · СЦЕНА — из SCENE_INFO: простыми словами и откуда данные;
  · ВЕРДИКТ дня и ЛЕНТА за неделю — по одному тексту.

Понятия реестра в индекс НЕ кладём: они уже лежат в пространстве «concepts» и ищутся
тем же вектором. Дублировать значило бы дважды платить за одно и то же и получать
две разные записи одного понятия в выдаче.

KPI_PLAIN и SCENE_INFO живут в js/enso.js — их читаем оттуда разбором литерала. Если
разбор не удался, единицы всё равно собираются, просто без человеческого пояснения:
индекс важнее украшения, и молчать об этом нельзя (печатаем предупреждение).

    python tools/enso/research_index.py --plan     сколько единиц и каких
    python tools/enso/research_index.py --run      записать data/enso/research-index.json
    python tools/enso/research_index.py --push     посчитать вектора и залить в Vectorize
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = ROOT / "data" / "enso"
OUT = DATA / "research-index.json"
CACHE = DATA / "research-embed-cache.jsonl"
INDEX = os.environ.get("VECTORIZE_INDEX", "b42-articles")
NAMESPACE = "panel"
UPSERT_BATCH = 200


def js_dict(name, text):
    """Достать литерал `var NAME = { … };` из js/enso.js.

    Не полноценный разбор JavaScript и не претендует: нам нужны две плоские таблицы
    строк. Считаем скобки, чтобы найти конец литерала, и переводим одинарные кавычки
    в двойные. Не получилось — возвращаем пустоту, вызывающий об этом скажет вслух.
    """
    i = text.find("var " + name)
    if i < 0:
        return {}
    i = text.find("{", i)
    depth, j, instr, esc, quote = 0, i, False, False, ""
    while j < len(text):
        c = text[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                instr = False
        elif c in "'\"":
            instr, quote = True, c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    body = text[i:j + 1]
    try:
        import json5                                        # если вдруг стоит
        return json5.loads(body)
    except Exception:                                       # noqa: BLE001
        pass
    # Своими силами: ключи в кавычки, одинарные строки в двойные, хвостовые запятые прочь.
    s = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', body)
    s = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: json.dumps(m.group(1).replace('\\"', '"')), s)
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    try:
        return json.loads(s)
    except Exception:                                       # noqa: BLE001
        return {}


def load(name, default=None):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:                                       # noqa: BLE001
        return default if default is not None else {}


def units():
    """Единицы индекса: короткий английский текст, адрес на панели, якорь."""
    d = load("latest.json")
    J = load("journal.json")
    gl = (load("glossary.json").get("en") or {})
    news = load("news.json")
    js = (ROOT / "js" / "enso.js").read_text(encoding="utf-8", errors="ignore")
    plain = js_dict("KPI_PLAIN", js)
    scenes = js_dict("SCENE_INFO", js)
    if not plain or not scenes:
        print("⚠️ не разобрал KPI_PLAIN/SCENE_INFO из js/enso.js — "
              "единицы собраны без человеческих пояснений")

    out = []
    for r in d.get("risks") or []:
        rid = r.get("id") or ""
        if not rid:
            continue
        out.append({
            "id": "risk:" + rid, "kind": "risk", "title": r.get("title") or rid,
            "text": " ".join(filter(None, [r.get("title"), r.get("plain"),
                                           r.get("evidence"),
                                           "What to watch: " + (r.get("watch") or "")])),
            "hash": "#risk/" + rid, "anchor": "risk:" + rid,
        })
    for a in d.get("alerts") or []:
        aid = a.get("id") or ""
        if not aid:
            continue
        out.append({
            "id": "alert:" + aid, "kind": "alert", "title": a.get("title") or aid,
            "text": " ".join(filter(None, [a.get("level"), a.get("title"), a.get("detail")])),
            "hash": "#now/analogs", "anchor": "alert:" + aid,
        })
    for k, m in (J.get("metrics") or {}).items():
        if k.startswith("risk:"):
            continue
        e = m.get("entries") or []
        last = e[-1] if e else None
        prev = e[-2] if len(e) > 1 else None
        title = m.get("title") or k
        # Человеческое пояснение ищем по вхождению ключа в заголовок — так же, как панель.
        why = ""
        for key, txt in plain.items():
            if key and key.lower() in title.lower():
                why = txt
                break
        bits = [title, m.get("unit") or "", why, m.get("src") or ""]
        if last:
            bits.append(f"latest {last.get('v')} {m.get('unit') or ''} on {last.get('d')}")
        if last and prev and isinstance(last.get("v"), (int, float)) \
                and isinstance(prev.get("v"), (int, float)):
            bits.append(f"changed from {prev['v']} on {prev.get('d')}")
        out.append({"id": "kpi:" + k, "kind": "kpi", "title": title,
                    "text": " ".join(x for x in bits if x),
                    "hash": "#overview", "anchor": "kpi:" + k})
    for key, g in gl.items():
        out.append({"id": "term:" + key, "kind": "term", "title": g.get("name") or key,
                    "text": " ".join(filter(None, [g.get("name"), g.get("def"),
                                                   g.get("why"), g.get("src")])),
                    "hash": "#how/glossary", "anchor": "term:" + key})
    for v, info in (scenes or {}).items():
        if not isinstance(info, dict):
            continue
        out.append({"id": "scene:" + v, "kind": "scene", "title": v,
                    "text": " ".join(filter(None, [info.get("plain"), info.get("source"),
                                                   info.get("tech")]))[:1200],
                    "hash": "#" + v, "anchor": "block:" + v})
    sm = d.get("summary") or {}
    if sm.get("verdict"):
        out.append({"id": "verdict:today", "kind": "verdict", "title": "Verdict today",
                    "text": " ".join(filter(None, [sm.get("verdict"),
                                                   " ".join(sm.get("watch") or [])]))[:1500],
                    "hash": "#verdict/now", "anchor": "block:verdict"})
    week = [x.get("title") for x in (news.get("this_week") or [])][:20]
    if week:
        out.append({"id": "news:week", "kind": "news", "title": "What changed this week",
                    "text": " · ".join(week)[:1500], "hash": "#news", "anchor": "block:news"})
    # Каждая строка ленты — своя единица: вопрос «что изменилось у FAO» должен находить
    # именно эту строку, а не общий свод недели.
    for i, x in enumerate((news.get("this_week") or [])[:40]):
        txt = " ".join(filter(None, [x.get("title"), x.get("detail"), x.get("why")]))
        if len(txt) < 40:
            continue
        out.append({"id": f"news:{i}", "kind": "news", "title": x.get("title") or "news",
                    "text": txt[:900], "hash": "#news", "anchor": "block:news"})
    # Регионы: у каждого свой текст про уязвимость и что делать — это ровно то, что
    # спрашивают «а что будет у нас».
    for r in ((d.get("regions") or {}).get("items") or []):
        rid = r.get("id") or ""
        v = r.get("vulnerability") or {}
        txt = " ".join(filter(None, [r.get("name"), r.get("countries"), v.get("note"),
                                     " ".join(r.get("actions") or [])]))
        if not rid or len(txt) < 40:
            continue
        out.append({"id": "region:" + rid, "kind": "region", "title": r.get("name") or rid,
                    "text": txt[:900], "hash": "#regions/table", "anchor": "region:" + rid})
    # Пустые и слишком короткие выбрасываем: вектор от трёх слов ищет случайное.
    return [u for u in out if len((u.get("text") or "").strip()) >= 40]


def push(rows):
    """Вектора для единиц и заливка в пространство «panel»."""
    import requests
    from embeddings_build import load_env
    # ВЕКТОР СЧИТАЕМ ТОЙ ЖЕ МАШИНОЙ, ЧТО И У СТАТЕЙ — Workers AI. Модель одна (bge-m3),
    # но считать единицы панели через другого поставщика значит сравнивать в поиске то,
    # что посчитано разными руками: расхождение мелкое, а ловится не сразу и не всегда.
    # Воркер спрашивает Workers AI, статьи залиты Workers AI — и панель тоже.
    envv = load_env(ROOT)
    key = envv.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    acc = envv.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not (key and acc):
        sys.exit("нет CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID")
    sess0 = requests.Session()
    head0 = {"Authorization": f"Bearer {key}"}
    vecs = []
    for s in range(0, len(rows), 50):
        part = [r["text"][:2000] for r in rows[s:s + 50]]
        for attempt in range(6):
            rr = sess0.post(
                f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/baai/bge-m3",
                headers=head0, json={"text": part}, timeout=120)
            if rr.status_code == 429 or rr.status_code >= 500:
                time.sleep(min(2 ** attempt, 30))
                continue
            rr.raise_for_status()
            vecs += rr.json()["result"]["data"]
            break
        else:
            sys.exit("Workers AI недоступна после шести попыток")
        print(f"  вектор {min(s + 50, len(rows))}/{len(rows)}")
    base = f"https://api.cloudflare.com/client/v4/accounts/{acc}"
    sess = requests.Session()
    sent = 0
    for s in range(0, len(rows), UPSERT_BATCH):
        chunk = rows[s:s + UPSERT_BATCH]
        lines = []
        for i, r in enumerate(chunk, start=s):
            lines.append(json.dumps({
                "id": "p:" + r["id"],
                "values": [round(float(x), 5) for x in vecs[i]],
                "namespace": NAMESPACE,
                # Метаданные держим маленькими, но достаточными: воркер строит по ним
                # ответ и ссылку, не ходя больше никуда.
                "metadata": {"kind": r["kind"], "title": r["title"][:120],
                             "hash": r["hash"], "anchor": r["anchor"],
                             "text": r["text"][:900]},
            }, ensure_ascii=False))
        body = "\n".join(lines).encode("utf-8")
        for attempt in range(5):
            resp = sess.post(f"{base}/vectorize/v2/indexes/{INDEX}/upsert",
                             headers={"Authorization": f"Bearer {key}",
                                      "Content-Type": "application/x-ndjson"},
                             data=body, timeout=180)
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(min(2 ** attempt * 2, 30))
                continue
            resp.raise_for_status()
            break
        sent += len(lines)
        print(f"  залито {sent}/{len(rows)}")
    print(f"✅ пространство «{NAMESPACE}» обновлено: {sent} единиц")


def main():
    ap = argparse.ArgumentParser(description="Индекс панели для чата-исследования")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    rows = units()
    import collections
    c = collections.Counter(r["kind"] for r in rows)
    print(f"единиц: {len(rows)} · {dict(c)}")
    if a.plan or not (a.run or a.push):
        for r in rows[:6]:
            print(f"   {r['kind']:8s} {r['id']:28s} {r['text'][:60]}")
        return 0

    if a.run or a.push:
        OUT.write_text(json.dumps({
            "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "n": len(rows), "namespace": NAMESPACE,
            "note": "Units of the panel for the research chat: one short English text per "
                    "risk, alert, indicator, term, scene, verdict and the week's feed. "
                    "Concepts are not here — they live in the 'concepts' namespace.",
            "units": rows,
        }, ensure_ascii=False), encoding="utf-8")
        print(f"→ {OUT.relative_to(ROOT)}")
    if a.push:
        push(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
