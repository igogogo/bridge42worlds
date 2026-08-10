#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вектор по ТЕЛУ статьи против вектора по аннотации — на замороженной мерке.

ЧТО СРАВНИВАЕМ. Сейчас вектор строится из `original_title` + наша английская аннотация
(~900 знаков). Владелец 2026-08-09: «нам бы вектор по всем статьям из PDF». Тело статьи
в среднем 61 587 знаков — там методика, оговорки и то, что на самом деле сделали.

ЧЕМ МЕРЯЕМ. Замороженным набором `data/search-eval-queries.jsonl`: 800 вопросов на четырёх
языках, эталон известен заранее (вопрос построен из статьи X — найтись должна X).
Набор собран 30 июля и с тех пор не менялся, поэтому сравнение честное.

ПОЧЕМУ ЭТО МОЖНО ТОЛЬКО СЕЙЧАС. Мерка висела с 30 июля: живой `/api/search` держит
суточную норму в два запроса, и 800 через него не прогнать. Теперь оба набора векторов
лежат локально, и прогон считается матрицей — без сети, без нормы, бесплатно.

СКОЛЬКО ТЕЛА БРАТЬ. Не всё: у bge-m3 предел 60k токенов, но качество падает задолго до
него, а 61 тысяча знаков — это ~15k токенов. Берём первые 12 000 знаков тела: туда
попадает введение и методика, то есть ровно то, чего нет в аннотации. Это решение,
а не истина — если разница выйдет в пользу тела, стоит проверить и другие срезы.

    python fulltext_vs_abstract.py --build     # векторы по телу
    python fulltext_vs_abstract.py --compare   # два числа рядом
"""
import json, math, pathlib, sys, time, argparse, collections
import urllib.request, urllib.error
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
MODEL = "@cf/baai/bge-m3"
BATCH = 10
BODY_CHARS = 12000
TRANSLATE = '--translated' in sys.argv   # мерить боевой путь: вопрос переводится в en


def load_env():
    env = {}
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def embed(texts, acc, tok, tries=5):
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODEL}"
    body = json.dumps({"text": texts}).encode("utf-8")
    for a in range(tries):
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            v = (d.get("result") or {}).get("data")
            if v and len(v) == len(texts):
                return v
            raise ValueError("ответ не по размеру")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** a * 2); continue
            # Тело ответа Cloudflare объясняет причину отказа, но urllib его прячет
            # за кодом. Без этого 400 неотличим от 400 и приходится гадать.
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:400]
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 ** a * 2)
    raise RuntimeError("эмбеддинги не получены")


def build():
    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    items = []
    for p in sorted((MAIN / "lang" / "ru" / "archive").rglob("fulltext.txt")):
        aid = p.parent.name
        t = p.read_text(encoding="utf-8", errors="ignore")[:BODY_CHARS]
        if len(t) > 500:
            items.append((aid, " ".join(t.split())))
    out = DATA / "embeddings-fulltext.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
    todo = [x for x in items if x[0] not in done]
    chars = sum(len(t) for _, t in todo)
    print(f"статей с телом: {len(items)}, посчитать: {len(todo)}, "
          f"знаков {chars:,}, ~${chars/4/1e6*0.012:.3f}")
    # ОДИН ПЛОХОЙ ВХОД НЕ ДОЛЖЕН РОНЯТЬ ПРОГОН НА ТРИ ТЫСЯЧИ.
    # Первая попытка упала на HTTP 400 после 130 статей: пачка отвергнута целиком,
    # и непонятно, из-за какой именно. Перебирать поштучно ради поиска — дорого
    # и всё равно повторится на следующей. Поэтому: пачка не прошла — повторяем её
    # содержимое по одному, виноватого пропускаем и записываем его id.
    bad = []
    with out.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            ch = todo[i:i + BATCH]
            try:
                vs = embed([t for _, t in ch], acc, tok)
                pairs = list(zip(ch, vs))
            except Exception as e:
                print(f"  пачка {i//BATCH + 1} отвергнута ({str(e)[:80]}), иду поштучно")
                pairs = []
                for aid, t in ch:
                    try:
                        pairs.append(((aid, t), embed([t], acc, tok)[0]))
                    except Exception as e2:
                        bad.append((aid, str(e2)[:100]))
            for (aid, _), v in pairs:
                f.write(json.dumps({"id": aid, "vec": [round(x, 6) for x in v]},
                                   ensure_ascii=False) + "\n")
            f.flush()
            if (i // BATCH) % 20 == 0:
                print(f"  {min(i+BATCH, len(todo))}/{len(todo)}"
                      + (f", отказов {len(bad)}" if bad else ""))
    if bad:
        print(f"\nне посчитано: {len(bad)}")
        for aid, why in bad[:10]:
            print(f"  {aid}: {why}")
    print(f"записано: {out}")


def load_vecs(path, strip_prefix=False):
    m = {}
    for line in (DATA / path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        aid = r["id"].split(":", 1)[1] if strip_prefix else r["id"]
        v = np.array(r["vec"], dtype=np.float32)
        m[aid] = v / (np.linalg.norm(v) or 1)
    return m


def translate_queries(rows, key):
    """Перевести неанглийские вопросы в английский — как это делает боевой Worker.

    ПОЧЕМУ ЭТО ОБЯЗАТЕЛЬНО ДЛЯ ЧЕСТНОГО ЗАМЕРА. Первый прогон дал арабскому 24,7%
    против 52,0% у английского, и я предложил «включить перевод запроса». Проверил
    код — перевод УЖЕ включён: `handleSearch` и `handleAsk` в worker.js зовут
    translateText(q, "en") перед поиском (строки 1399 и 1581). То есть я померил путь,
    которого в проде нет, и чуть не отправил архитектора чинить работающее.

    Промпт берём тот же, что в Worker, слово в слово — иначе замер снова будет
    про другую систему.
    """
    cache_p = DATA / "eval-query-en.json"
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    names = {"en": "English", "ru": "Russian", "es": "Spanish",
             "ar": "Arabic", "fr": "French"}
    todo = [r for r in rows if r["lang"] != "en" and r["qid"] not in cache]
    print(f"перевести вопросов: {len(todo)}")
    for n, r in enumerate(todo, 1):
        body = json.dumps({
            "model": "deepseek-v4-flash", "temperature": 0, "max_tokens": 300,
            "thinking": {"type": "disabled"},
            "messages": [
                {"role": "system", "content":
                 "Translate to English. Scientific text: keep terminology precise. "
                 "Answer with the translation only, no quotes, no explanation."},
                {"role": "user", "content": r["query"]},
            ]}).encode("utf-8")
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            cache[r["qid"]] = d["choices"][0]["message"]["content"].strip()
        except Exception:
            cache[r["qid"]] = r["query"]      # не перевелось — ищем как есть
        if n % 50 == 0:
            cache_p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  {n}/{len(todo)}")
    cache_p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


def compare():
    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    abs_v = load_vecs("embeddings-articles.jsonl", strip_prefix=True)
    ful_v = load_vecs("embeddings-fulltext.jsonl")
    common = sorted(set(abs_v) & set(ful_v))
    print(f"аннотаций {len(abs_v)}, тел {len(ful_v)}, общих {len(common)}")

    rows = [json.loads(l) for l in
            (DATA / "search-eval-queries.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    # только те вопросы, чей эталон есть в ОБОИХ наборах — иначе сравнение нечестное
    rows = [r for r in rows if r["expect"] in set(common)]
    print(f"вопросов из мерки, применимых к обоим: {len(rows)} из 800")

    # Боевой путь: неанглийский вопрос переводится ДО поиска. Без этого замер
    # описывает систему, которой у нас нет.
    en_q = translate_queries(rows, env["DEEPSEEK_API_KEY"]) if TRANSLATE else {}
    suffix = "-tr" if TRANSLATE else ""

    qcache = DATA / f"eval-query-vecs{suffix}.json"
    qv = json.loads(qcache.read_text(encoding="utf-8")) if qcache.exists() else {}
    for r in rows:
        r["_q"] = en_q.get(r["qid"], r["query"]) if TRANSLATE else r["query"]
    todo = [r for r in rows if r["qid"] not in qv]
    if todo:
        print(f"считаю векторы вопросов: {len(todo)}")
        for i in range(0, len(todo), 20):
            ch = todo[i:i + 20]
            vs = embed([r["_q"] for r in ch], acc, tok)
            for r, v in zip(ch, vs):
                qv[r["qid"]] = [round(x, 6) for x in v]
        qcache.write_text(json.dumps(qv), encoding="utf-8")

    M_abs = np.stack([abs_v[a] for a in common])
    M_ful = np.stack([ful_v[a] for a in common])
    idx = {a: i for i, a in enumerate(common)}

    res = {}
    for name, M in (("аннотация", M_abs), ("тело статьи", M_ful)):
        buckets = collections.defaultdict(lambda: {"n": 0, "r1": 0, "r5": 0, "r10": 0, "mrr": 0.0})
        for r in rows:
            q = np.array(qv[r["qid"]], dtype=np.float32)
            q /= (np.linalg.norm(q) or 1)
            sims = M @ q
            order = np.argsort(-sims)[:10]
            want = idx[r["expect"]]
            pos = int(np.where(order == want)[0][0]) + 1 if want in order else 0
            for key in ("ВСЕГО", f"язык {r['lang']}"):
                b = buckets[key]
                b["n"] += 1
                if pos == 1: b["r1"] += 1
                if 0 < pos <= 5: b["r5"] += 1
                if 0 < pos <= 10: b["r10"] += 1
                if pos: b["mrr"] += 1.0 / pos
        res[name] = buckets

    print(f"\n{'срез':<14} {'аннотация @1':>13} {'тело @1':>9} | "
          f"{'аннот. @5':>10} {'тело @5':>9} | {'аннот. MRR':>11} {'тело MRR':>9}")
    keys = sorted(res["аннотация"], key=lambda k: (k != "ВСЕГО", k))
    for k in keys:
        a = res["аннотация"][k]; f = res["тело статьи"][k]
        n = a["n"] or 1
        print(f"{k:<14} {100*a['r1']/n:>12.1f}% {100*f['r1']/n:>8.1f}% | "
              f"{100*a['r5']/n:>9.1f}% {100*f['r5']/n:>8.1f}% | "
              f"{a['mrr']/n:>11.3f} {f['mrr']/n:>9.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--translated", action="store_true")
    a = ap.parse_args()
    if a.build: build()
    elif a.compare: compare()
    else: ap.print_help()

