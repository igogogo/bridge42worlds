"""Связи между статьями ПО СМЫСЛУ: карта «похожих» из векторной базы.

Владелец 2026-08-02: «можно и ссылок понаставить по тексту по векторной базе — это будет
эффектно». И раньше: «мы же вектор строили как раз для этого, в том числе связь напрямую
статей, поиск похожих».

Зачем это, если «похожие статьи» уже есть: сейчас они подбираются по СОВПАДЕНИЮ ТЕГОВ.
Тег — грубая мерка: две работы про «энтропию» могут быть о совершенно разном, а работа
про приливные силы и работа про деформацию нейтронных звёзд общего тега может не иметь
вовсе. Вектор знает, о чём текст на самом деле, и находит родство там, где словарь молчит.

Векторы живут в Cloudflare Vectorize, локально их нет — поэтому спрашиваем живой поиск
нашего же сайта: запрос = заголовок и первые фразы статьи, ответ = ближайшие по смыслу.
Один вызов на статью, эмбеддинг стоит доли цента за тысячу.

    python tools/vector_links.py --limit 50      попробовать на полусотне
    python tools/vector_links.py                 весь архив
    python tools/vector_links.py --min 0.45      порог близости

Результат — data/related-vec.json: {id статьи: [{id, score}, …]}. Его читает страница
статьи и показывает связи по смыслу вместо совпадения тегов. Прогон возобновляемый:
уже посчитанные статьи пропускаются.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "related-vec.json"
API = "https://bridge42worlds.academy/api/search"


def load_done():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def query(text, tries=3):
    for i in range(tries):
        try:
            r = requests.post(API, json={"q": text[:280], "lang": "ru"}, timeout=60,
                              headers={"content-type": "application/json; charset=utf-8"})
            if r.status_code == 200:
                return r.json().get("results", [])
            if r.status_code in (429, 503):
                time.sleep(5 * (i + 1))
        except Exception:
            time.sleep(3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--min", type=float, default=0.42)
    ap.add_argument("--top", type=int, default=4)
    args = ap.parse_args()

    idx = json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8"))
    uniq = {}
    for a in idx:
        uniq.setdefault(a["id"], a)
    items = sorted(uniq.values(), key=lambda x: x["date"], reverse=True)

    done = load_done()
    todo = [a for a in items if a["id"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"всего статей {len(items)}, уже посчитано {len(done)}, к работе {len(todo)}")

    ok = empty = fail = 0
    for n, a in enumerate(todo, 1):
        # Запрос — заголовок плюс начало описания: это самое плотное описание смысла статьи,
        # какое у нас есть. Весь текст брать нельзя: у поиска предел длины запроса, да и
        # длинный текст размывает вектор до «вообще про физику».
        q = (a.get("title", "") + ". " + (a.get("description") or a.get("oneliner") or ""))[:280]
        res = query(q)
        if res is None:
            fail += 1
            print(f"  ✗ {a['id']}: поиск не ответил")
            continue
        near = [{"id": r["id"], "score": round(r.get("score", 0), 3)}
                for r in res if r.get("id") != a["id"] and r.get("score", 0) >= args.min][:args.top]
        done[a["id"]] = near
        if near:
            ok += 1
        else:
            empty += 1
        if n % 25 == 0 or n == len(todo):
            OUT.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
            print(f"  … {n}/{len(todo)} · со связями {ok} · без связей {empty} · сбоев {fail}")

    OUT.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
    total_links = sum(len(v) for v in done.values())
    print(f"\nготово: {len(done)} статей, связей {total_links}, "
          f"в среднем {total_links / max(1, len(done)):.1f} на статью")
    print(f"файл: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
