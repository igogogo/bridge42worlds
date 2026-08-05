#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Расширяющий поиск в ПРОСТРАНСТВЕ МЕТОДОВ, а не аннотаций.

ЗАЧЕМ. Поиск по аннотациям дал 17% уместных (замер 2026-08-05): эмбеддинг кодирует ТЕМУ,
и «диффузия в тепле» с «диффузией в эпидемии» оказываются далеко — слова разные.
Проверяем прямое следствие этого объяснения: если эмбеддить ОПИСАНИЕ ПРИЁМА, работы
с одинаковой механикой должны сойтись независимо от предметной области.

Поле `advanced.en.methods` есть у 605 наших статей — это и есть описание приёма
своими словами. Гипотезу можно проверить сегодня, не дожидаясь слоя `methodology`.

ЧИСТОТА СРАВНЕНИЯ. Та же слепая выборка, тот же фильтр «другая корневая область»,
та же зона по квантилям. Меняется ровно один множитель — текст, из которого построен
вектор. Иначе сравнивать было бы нечего.

НИЧЕГО СЫРОГО НА ДИСК. Скрипт пишет только векторы и косинусы; выходов языковой модели
здесь нет вовсе (эмбеддинги — не текст). Требование роли о том, что не идёт в витрину —
не сохраняется, тут выполняется по построению.

    python engine_methods.py --build        # векторы методов
    python engine_methods.py --blind 8      # та же выборка, сравнение с 17%
"""
import json, math, pathlib, random, sys, time, argparse
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
MODEL = "@cf/baai/bge-m3"
BATCH = 20
SEED = 42
LO_Q, HI_Q = 0.75, 0.97
TAGRE = None


def clean(s):
    """Снять нашу разметку [tag:...]...[/tag] — в вектор должен идти текст, а не теги."""
    import re
    global TAGRE
    if TAGRE is None:
        TAGRE = re.compile(r"\[/?(?:tag|law|scientist)(?::[^\]]*)?\]")
    return " ".join(TAGRE.sub("", s or "").split())


def load_env():
    env = {}
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def nz(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def sources():
    out = {}
    for p in (MAIN / "lang" / "ru" / "archive").rglob("data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = d.get("id")
        m = clean(((d.get("advanced") or {}).get("en") or {}).get("methods"))
        if aid and len(m) > 120:
            out[aid] = {"methods": m[:4000],
                        "title": (d.get("original_title") or "")[:110],
                        "cat": d.get("primary_category") or "?",
                        "root": (d.get("primary_category") or "?").split(".")[0]}
    return out


def embed(texts, acc, tok, tries=5):
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODEL}"
    body = json.dumps({"text": texts}).encode("utf-8")
    for a in range(tries):
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            v = (d.get("result") or {}).get("data")
            if v and len(v) == len(texts):
                return v
            raise ValueError("ответ не по размеру")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** a * 2); continue
            raise
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 ** a * 2)
    raise RuntimeError("эмбеддинги не получены")


def build():
    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    src = sources()
    ids = sorted(src)
    chars = sum(len(src[i]["methods"]) for i in ids)
    print(f"статей с описанием приёма: {len(ids)}, знаков {chars:,}, "
          f"~${chars/4/1e6*0.012:.4f}")
    out = DATA / "embeddings-methods.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for i in range(0, len(ids), BATCH):
            ch = ids[i:i + BATCH]
            vs = embed([src[a]["methods"] for a in ch], acc, tok)
            for a, v in zip(ch, vs):
                f.write(json.dumps({"id": a, "vec": [round(x, 6) for x in v]},
                                   ensure_ascii=False) + "\n")
            if (i // BATCH) % 10 == 0:
                print(f"  {min(i+BATCH, len(ids))}/{len(ids)}")
    print(f"записано: {out}")


def blind(n):
    p = DATA / "embeddings-methods.jsonl"
    if not p.exists():
        sys.exit("сначала --build")
    vecs = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            vecs[r["id"]] = nz(r["vec"])
    src = sources()
    print(f"в пространстве приёмов: {len(vecs)} статей")

    rnd = random.Random(SEED)
    for a in rnd.sample(sorted(vecs), min(n, len(vecs))):
        av = vecs[a]
        sims = sorted(((sum(x * y for x, y in zip(av, v)), b)
                       for b, v in vecs.items() if b != a), reverse=True)
        vals = sorted(s for s, _ in sims)
        lo, hi = vals[int(LO_Q * (len(vals) - 1))], vals[int(HI_Q * (len(vals) - 1))]
        root = src[a]["root"]
        picks = [(s, b) for s, b in sims if lo <= s <= hi
                 and src.get(b, {}).get("root") != root][:3]
        if not picks:
            continue
        print(f"\n=== {src[a]['title'][:72]}  [{src[a]['cat']}]")
        for s, b in picks:
            print(f"   {s:.3f} [{src[b]['cat']}] {src[b]['title'][:64]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--blind", type=int, default=0)
    a = ap.parse_args()
    if a.build: build()
    elif a.blind: blind(a.blind)
    else: ap.print_help()
