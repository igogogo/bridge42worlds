# -*- coding: utf-8 -*-
"""Semantic Scholar: собрать всё по каждой нашей статье. Владелец 26.08: «прогнать
все через этот сервис, собрать всё-всё, прикрепить к статье, расширить функционал».

ДВА ПРОХОДА:

  1. ПАКЕТНЫЙ (минуты): POST /paper/batch по 500 arXiv-id за запрос — весь архив
     за ~15 запросов. Поля: цитирования (сколько/влиятельных), журнал, дата
     публикации, открытый PDF, области, tldr, авторы с h-index-ссылками.
  2. ГРАФ (часы, 1 запрос/сек — их лимит на весь ключ): по каждой статье до 100
     цитирующих и до 100 опорных работ, с их arXiv-id — чтобы связывать НАШИ
     разборы настоящим графом цитирований, а не догадкой.

Результат: data/s2/papers.json (пакетные поля) и data/s2/graph/{id}.json (граф).
Состояние в data/s2/state.json — обрыв продолжается с места, ничего не повторяется.

ЛЕГАЛЬНОСТЬ: официальный API, ключ выдан нам, атрибуция «Data: Semantic Scholar»
обязательна при показе — рендер её ставит. Чужие полные аннотации не публикуем.

    python tools/s2_collect.py            оба прохода (сам продолжает)
    python tools/s2_collect.py --status
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "s2"
PAPERS = OUT / "papers.json"
STATE = OUT / "state.json"
GRAPH = OUT / "graph"

# Владелец 27.08: «всё, что там есть, надо собирать — потом используем».
BATCH_FIELDS = ("citationCount,influentialCitationCount,referenceCount,externalIds,"
                "venue,publicationVenue,journal,year,publicationDate,publicationTypes,"
                "isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,tldr,abstract,"
                "authors.name,authors.hIndex,authors.authorId")
# БЕЗ aliases: author/batch его не знает и валит всю пачку HTTP 400
# («Unrecognized or unsupported fields: [aliases]», проверено 27.08).
AUTHOR_FIELDS = ("name,hIndex,paperCount,citationCount,affiliations,"
                 "homepage,externalIds")
GRAPH_FIELDS = "externalIds,title,citationCount,year"
PAUSE = 1.05          # их лимит: 1 запрос в секунду на ключ, на все ручки


def key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("SEMANTIC_SCHOLAR_KEY"):
            return line.split("=", 1)[1].strip()
    raise SystemExit("нет SEMANTIC_SCHOLAR_KEY в .env")


def req(url, payload=None, k=None, tries=6):
    for attempt in range(tries):
        r = urllib.request.Request(url, headers={"x-api-key": k or key(),
                                                 "Content-Type": "application/json"},
                                   data=json.dumps(payload).encode() if payload else None)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                # 429 у них затяжной: обычный бэкоф (до 33с) выгорал все 6 попыток
                # подряд и пачки «пустели» (прогон 27.08). Ждём минутами.
                time.sleep(10 * 2 ** attempt if e.code == 429 else 2 ** attempt + 1)
                continue
            if e.code == 404:
                return None
            if e.code == 400:
                # детерминированный отказ (плохое поле/id) — повторять бессмысленно,
                # но и валить весь прогон нельзя: лог и дальше
                log(f"  ⚠️ 400 Bad Request: {e.read().decode()[:160]}")
                return None
            raise
        except Exception:
            time.sleep(2 ** attempt + 1)
    return None


def our_ids():
    return [p.parent.name for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json"))]


def state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"batch_done": False, "graph_done": []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def batch_pass(ids, k):
    papers = json.loads(PAPERS.read_text(encoding="utf-8")) if PAPERS.exists() else {}
    # и перезапросить уже собранных без расширенных полей (сбор расширялся 27.08)
    todo = [i for i in ids
            if i not in papers or (papers[i] is not None and "abstract" not in papers[i])]
    log(f"пакетный проход: {len(todo)} статей")
    for s in range(0, len(todo), 500):
        chunk = todo[s:s + 500]
        body = {"ids": [f"ARXIV:{i.split('v')[0]}" for i in chunk]}
        d = req(f"https://api.semanticscholar.org/graph/v1/paper/batch?fields={BATCH_FIELDS}",
                body, k)
        if d is None:
            log(f"  пачка {s}: пусто, пропускаю")
            continue
        for aid, rec in zip(chunk, d):
            papers[aid] = rec          # None = S2 работу не знает; помним, чтобы не спрашивать
        PAPERS.write_text(json.dumps(papers, ensure_ascii=False), encoding="utf-8")
        known = sum(1 for v in papers.values() if v)
        log(f"  собрано {len(papers)}/{len(ids)} (в S2 найдено {known})")
        time.sleep(PAUSE)
    return papers


def graph_pass(ids, papers, k):
    GRAPH.mkdir(parents=True, exist_ok=True)
    st = state()
    done = set(st["graph_done"])
    todo = [i for i in ids if i not in done and papers.get(i)]
    log(f"граф цитирований: {len(todo)} статей (~{len(todo) * 2 * PAUSE / 60:.0f} мин)")
    for n, aid in enumerate(todo, 1):
        bare = aid.split("v")[0]
        cits = req(f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{bare}/citations"
                   f"?fields={GRAPH_FIELDS}&limit=100", None, k)
        time.sleep(PAUSE)
        refs = req(f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{bare}/references"
                   f"?fields={GRAPH_FIELDS}&limit=100", None, k)
        time.sleep(PAUSE)
        slim = lambda rows, kk: [
            {"arxiv": ((r.get(kk) or {}).get("externalIds") or {}).get("ArXiv"),
             "title": (r.get(kk) or {}).get("title"),
             "n": (r.get(kk) or {}).get("citationCount"),
             "year": (r.get(kk) or {}).get("year")}
            for r in ((rows or {}).get("data") or [])]
        (GRAPH / f"{aid}.json").write_text(json.dumps({
            "citations": slim(cits, "citingPaper"),
            "references": slim(refs, "citedPaper"),
        }, ensure_ascii=False), encoding="utf-8")
        done.add(aid)
        if n % 50 == 0:
            st["graph_done"] = sorted(done)
            save_state(st)
            log(f"  граф {n}/{len(todo)}")
    st["graph_done"] = sorted(done)
    save_state(st)


def authors_pass(papers, k):
    """Всё по НАШИМ авторам: суммарные цитирования, число работ, аффилиации,
    псевдонимы. Пакетная ручка авторов — сотня за запрос."""
    out_p = OUT / "authors.json"
    authors = json.loads(out_p.read_text(encoding="utf-8")) if out_p.exists() else {}
    ids = sorted({a["authorId"] for v in papers.values() if v
                  for a in (v.get("authors") or []) if a.get("authorId")}
                 - set(authors))
    log(f"проход по авторам: {len(ids)} новых (всего известно {len(authors)})")
    for s in range(0, len(ids), 100):
        chunk = ids[s:s + 100]
        d = req(f"https://api.semanticscholar.org/graph/v1/author/batch?fields={AUTHOR_FIELDS}",
                {"ids": chunk}, k)
        if d is None:
            continue
        for aid, rec in zip(chunk, d):
            authors[aid] = rec
        out_p.write_text(json.dumps(authors, ensure_ascii=False), encoding="utf-8")
        if (s // 100) % 20 == 0:
            log(f"  авторов {len(authors)}")
        time.sleep(PAUSE)
    log(f"✅ авторов собрано: {len(authors)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.status:
        st = state()
        papers = json.loads(PAPERS.read_text(encoding="utf-8")) if PAPERS.exists() else {}
        print(f"пакетно: {len(papers)} · граф: {len(st['graph_done'])}")
        return 0
    k = key()
    ids = our_ids()
    log(f"наших статей: {len(ids)}")
    papers = batch_pass(ids, k)
    graph_pass(ids, papers, k)
    authors_pass(papers, k)
    log("✅ сбор Semantic Scholar завершён")
    return 0


if __name__ == "__main__":
    sys.exit(main())
