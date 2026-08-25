#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Английские карточки для СТАРЫХ понятий реестра. Владелец 25 августа: карточки тоже.

Новые 708 понятий получили карточку при именовании — она писалась по опорным работам.
У 536 исходных карточки нет: их описания живут в языковых витринах (tags.json,
laws.json) и написаны по-русски. Для шага 5 нужна английская: понятие векторизуется
своим текстом, и сравнивать его со статьёй напрямую можно только на одном языке.

ПОЧЕМУ КАРТОЧКА ПИШЕТСЯ ПО СТАТЬЯМ, А НЕ ПЕРЕВОДОМ. Русское описание писалось для
читателя — оно объясняет, а не определяет, и в нём много того, чего в статьях нет.
Карточка же нужна как ОПОРА ДЛЯ СРАВНЕНИЯ: она должна описывать понятие ровно так,
как оно проявляется в нашем корпусе. Поэтому модель видит настоящие заголовки работ
понятия и пишет по ним, а не переводит чужой текст.

Название и вид у старых понятий НЕ трогаются: они уже есть и уже используются
витринами. Меняется только добавляемое поле card_en.

    python concepts_cards.py --plan      посчитать, ничего не тратить
    python concepts_cards.py             написать карточки
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

MODEL = "deepseek-ai/DeepSeek-V3.1"
PRICE_IN, PRICE_OUT = 0.27 / 1e6, 1.00 / 1e6
PER_CALL = 5

SYS = """You write one-sentence English cards for scientific concepts.

For each numbered concept you get its id and real article titles from a physics corpus
where that concept is used. Write what the concept IS, as it appears in that corpus.

Return a JSON array, one object per concept, same order:
  {"n": <number>, "card": "<one English sentence, max 25 words>"}

Rules:
1. Define, do not explain to a child and do not advertise.
2. Ground it in the titles you were given. If they are too scattered to define
   the concept, still define the concept itself from its id — but never invent
   properties the evidence does not show.
3. A physicist must find the sentence unobjectionable.
Output ONLY the JSON array."""


def ask(payload, key, tries=4):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": payload}],
        "temperature": 0.2, "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    for a in range(tries):
        try:
            req = urllib.request.Request(
                "https://api.deepinfra.com/v1/openai/chat/completions", data=body,
                headers={"Authorization": f"bearer {key}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            txt = d["choices"][0]["message"]["content"].strip()
            if txt.startswith("```"):
                txt = txt.split("```")[1]
                txt = txt[4:] if txt.startswith("json") else txt
            out = json.loads(txt)
            if isinstance(out, dict):
                out = next((v for v in out.values() if isinstance(v, list)), [out])
            u = d.get("usage", {})
            return out, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 * (a + 1))
    return [], 0, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--reg", default=str(DATA / "concepts-v2.json"))
    ap.add_argument("--out", default=str(DATA / "concepts-v2.json"))
    ap.add_argument("--lang", default="ru")
    args = ap.parse_args()

    import collections
    import concepts_grow as g

    doc = json.load(open(args.reg, encoding="utf-8"))
    reg = doc["concepts"]
    art = g.load_corpus(args.lang)
    pool = collections.defaultdict(list)
    for a, r in art.items():
        for e in r["con"]:
            if e in reg:
                pool[e].append(a)

    todo = [k for k, v in reg.items() if not v.get("card_en")]
    print(f"понятий в реестре {len(reg)} · без английской карточки {len(todo)}")
    calls = (len(todo) + PER_CALL - 1) // PER_CALL
    est = calls * (1200 * PRICE_IN + 500 * PRICE_OUT)
    print(f"запросов по {PER_CALL}: {calls} · оценка {est:.2f} $")
    if args.plan:
        print("  --plan: ни одного вызова не сделано")
        return 0

    key = g.load_key()
    done, tin, tout = 0, 0, 0
    out = pathlib.Path(args.out)
    for st in range(0, len(todo), PER_CALL):
        chunk = todo[st:st + PER_CALL]
        lines = []
        for i, k in enumerate(chunk, 1):
            titles = [art[a]["title"] for a in pool.get(k, [])[:6] if art[a]["title"]]
            lines.append(f"CONCEPT {i}: {k} (kind: {reg[k].get('kind')})\n"
                         + ("\n".join(f"  - {t[:110]}" for t in titles)
                            or "  (no articles in corpus)"))
        try:
            res, pi, po = ask("\n\n".join(lines), key)
        except Exception as ex:
            print(f"  !! пачка {st // PER_CALL + 1}: {type(ex).__name__}")
            continue
        tin += pi
        tout += po
        for k, r in zip(chunk, res if isinstance(res, list) else []):
            if isinstance(r, dict) and r.get("card"):
                reg[k]["card_en"] = r["card"]
                done += 1
        if (st // PER_CALL) % 10 == 0 or st + PER_CALL >= len(todo):
            spent = tin * PRICE_IN + tout * PRICE_OUT
            print(f"  {min(st + PER_CALL, len(todo))}/{len(todo)} · "
                  f"написано {done} · потрачено {spent:.3f} $")
            doc["concepts"] = reg
            out.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    spent = tin * PRICE_IN + tout * PRICE_OUT
    doc["concepts"] = reg
    doc["cards_written"] = done
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    have = sum(1 for v in reg.values() if v.get("card_en"))
    print(f"\nкарточек написано: {done} · потрачено {spent:.3f} $")
    print(f"понятий с английской карточкой: {have} из {len(reg)}")
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
