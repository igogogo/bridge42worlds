#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прогон мерки через живой /api/search.

Читает набор из search_eval.py, стучится в поиск, складывает results.json,
который потом считает `search_eval.py score`.

ПРО НОРМУ РАСХОДА. Поиск стоит денег и закрыт суточной нормой (поле dayLeft в ответе).
Прогонщик останавливается сам, как только норма кончилась или сервер начал отказывать —
и всё равно пишет то, что успел: частичный прогон лучше нулевого, а score считает
недостающие запросы как ненайденные, то есть в нашу пользу не соврёт.

    python search_run.py --base https://bridge42worlds.academy --limit 12
    python search_run.py --base ... --all --token <если появится>
"""
import json, sys, time, pathlib, argparse, urllib.parse, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent


def fetch(base, query, lang, topk, token, timeout=20):
    url = f"{base}/api/search?" + urllib.parse.urlencode(
        {"q": query, "lang": lang, "topK": topk})
    req = urllib.request.Request(url, headers={"User-Agent": "b42-ml-eval/1.0"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--queries", default="data/search-eval-queries.jsonl")
    ap.add_argument("--out", default="data/search-eval-results.json")
    ap.add_argument("--limit", type=int, default=12, help="сколько запросов; --all для всех")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--token", default="")
    ap.add_argument("--pause", type=float, default=0.4)
    args = ap.parse_args()

    rows = [json.loads(x) for x in
            (ROOT / args.queries).read_text(encoding="utf-8").splitlines() if x.strip()]
    if not args.all:
        # берём равномерно по всему набору, а не первые N подряд:
        # иначе выборка сведётся к паре статей и мерка ничего не покажет
        step = max(1, len(rows) // args.limit)
        rows = rows[::step][:args.limit]

    results, done, stopped = {}, 0, ""
    for r in rows:
        try:
            data = fetch(args.base, r["query"], r["lang"], args.topk, args.token)
        except urllib.error.HTTPError as e:
            stopped = f"HTTP {e.code} на запросе {done + 1}"
            break
        except Exception as e:
            stopped = f"{type(e).__name__}: {e}"
            break

        found = data.get("results") or []
        results[r["qid"]] = [str(x.get("id")) for x in found if x.get("id")]
        done += 1

        left = data.get("dayLeft")
        if isinstance(left, int) and left <= 0:
            stopped = f"норма кончилась после {done} запросов"
            break
        time.sleep(args.pause)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"выполнено запросов: {done} из {len(rows)}")
    if stopped:
        print(f"остановился: {stopped}")
    print(f"результаты: {out}")


if __name__ == "__main__":
    main()
