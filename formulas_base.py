#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Основные формы формул: их ПИШУТ, а не находят кластеризацией. Шаг 7 волны 5.

Владелец 25 августа: «убираем разметку формул, пишем для формулы основную форму —
это отдельный список, потом карточку на основную, и дальше по карточке вяжем
с понятиями. Тегов больше нет». И отдельно: «есть основная форма, каноническая,
общая — и есть применение, частный случай в статье».

ПОЧЕМУ НЕ КЛАСТЕРИЗАЦИЕЙ — это замерено, а не предположено. Я сначала попробовала
свести записи в основные формы по смысловой близости, рассудив, что буквенный канон
слоя формул провалился (1225 записей свернулись в 1217), а смысловой сработает.
Не сработал: при пороге 0.97 получается 1218 форм из 1218 записей, при 0.87 — 1202.
Не свернулось ничего.

Причина ровно в том различии, которое провёл владелец. Поле `meaning` у записи
описывает ПРИМЕНЕНИЕ в конкретной работе, а не общий закон: два автора, пишущие
про закон Хаббла, описывают его через свои величины и свой контекст. Векторы таких
описаний кластеризуются по теме статьи, а не по закону под ней. Основную форму
из применения не вычислить — её надо назвать.

ПОЭТОМУ ЗДЕСЬ ДВА ЯРУСА И МОДЕЛЬ МЕЖДУ НИМИ:

    запись в статье (частное)  →  модель называет общий закон  →  ОСНОВНАЯ ФОРМА
                                                                  ↓
                                                       карточка → вектор → понятие

Модель получает латех и описание записи и отвечает: какой это общий закон, как он
записывается в каноническом виде, и одна фраза о том, что он утверждает. Записи
с одинаковым ответом становятся применениями ОДНОЙ основной формы.

ЧЕСТНЫЙ ОТКАЗ РАЗРЕШЁН. Если запись — не проявление известного закона, а выкладка
конкретной работы, модель ставит пустой `base_id`. Такая запись остаётся частным
случаем без основной формы, и это правильный ответ: не всякая формула в статье
является законом.

    python formulas_base.py --plan       посчитать, ничего не тратить
    python formulas_base.py              написать основные формы
    python formulas_base.py --link       связать основные формы с понятиями
"""
import argparse
import collections
import json
import pathlib
import re
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
PER_CALL = 6
OUT = DATA / "formulas-base.json"

SYS = """You identify the general law behind a formula as it appears in one paper.

For each numbered item you get a LaTeX formula and a sentence about how that paper
uses it. Say which general, canonical law or relation this is an instance of.

Return a JSON array, one object per item, same order:
  {"n": <number>,
   "base_id": "<snake_case_english_id of the general law, or empty string>",
   "base_name": "<short English name, 1-5 words>",
   "base_latex": "<the law in its general canonical form, LaTeX, no numbers>",
   "card": "<one English sentence, max 25 words, stating what the law says>"}

Rules:
1. base_latex must be the GENERAL form with symbols, not the paper's special case.
   v = H_0 d is general; v = 70 * 400 is not.
2. If the formula is a derivation step or a fit specific to that paper and not an
   instance of a named general relation, return base_id "" — an honest empty answer
   is required, not a guess.
3. Use the standard name a physicist would use, so that two papers using the same
   law get the SAME base_id.
Output ONLY the JSON array."""


def ask(payload, key, tries=4):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": payload}],
        "temperature": 0.1, "max_tokens": 1200,
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
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--budget", type=float, default=2.0)
    args = ap.parse_args()

    import concepts_grow as g
    f = json.load(open(MAIN / "data/formulas.json", encoding="utf-8"))
    keys = list(f)
    print(f"записей формул: {len(keys)}")

    if args.link:
        return link(f)

    calls = (len(keys) + PER_CALL - 1) // PER_CALL
    est = calls * (900 * PRICE_IN + 700 * PRICE_OUT)
    print(f"запросов по {PER_CALL}: {calls} · оценка {est:.2f} $")
    if args.plan:
        print("  --plan: ни одного вызова не сделано")
        return 0

    key = g.load_key()
    done, tin, tout, refused = {}, 0, 0, 0
    if OUT.exists():
        try:
            done = json.load(open(OUT, encoding="utf-8")).get("records", {})
            print(f"уже разобрано: {len(done)} — продолжаю")
        except Exception:
            done = {}
    todo = [k for k in keys if k not in done]

    for st in range(0, len(todo), PER_CALL):
        chunk = todo[st:st + PER_CALL]
        lines = []
        for i, k in enumerate(chunk, 1):
            tex = re.sub(r"\s+", " ", str(f[k].get("latex") or k))[:200]
            mean = str(f[k].get("meaning") or "")[:260]
            lines.append(f"ITEM {i}\n  formula: {tex}\n  use in paper: {mean}")
        try:
            res, pi, po = ask("\n\n".join(lines), key)
        except Exception as ex:
            print(f"  !! пачка {st // PER_CALL + 1}: {type(ex).__name__}")
            continue
        tin += pi
        tout += po
        for k, r in zip(chunk, res if isinstance(res, list) else []):
            if not isinstance(r, dict):
                continue
            bid = (r.get("base_id") or "").strip()
            if not bid:
                refused += 1
            done[k] = {"base_id": bid, "base_name": r.get("base_name"),
                       "base_latex": r.get("base_latex"), "card": r.get("card")}
        spent = tin * PRICE_IN + tout * PRICE_OUT
        if (st // PER_CALL) % 15 == 0 or st + PER_CALL >= len(todo):
            print(f"  {min(st + PER_CALL, len(todo))}/{len(todo)} · "
                  f"честных отказов {refused} · потрачено {spent:.3f} $")
            OUT.write_text(json.dumps({"built": "2026-08-25", "records": done,
                                       "spent": round(spent, 4)},
                                      ensure_ascii=False), encoding="utf-8")
        if spent >= args.budget:
            print(f"  потолок {args.budget} $ — останавливаюсь")
            break

    OUT.write_text(json.dumps({"built": "2026-08-25", "records": done,
                               "spent": round(tin * PRICE_IN + tout * PRICE_OUT, 4)},
                              ensure_ascii=False), encoding="utf-8")
    bases = collections.Counter(v["base_id"] for v in done.values() if v["base_id"])
    print(f"\n{'=' * 74}")
    print(f"записей разобрано: {len(done)} · честных отказов: {refused}")
    print(f"РАЗЛИЧНЫХ ОСНОВНЫХ ФОРМ: {len(bases)}")
    print(f"  применений на форму: медиана "
          f"{sorted(bases.values())[len(bases) // 2] if bases else 0}, "
          f"максимум {max(bases.values()) if bases else 0}")
    for b, n in bases.most_common(8):
        print(f"    {b:<40} применений {n}")
    print(f"→ {OUT}")
    return 0


def link(f):
    """Связать основные формы с понятиями: карточка формулы против карточки понятия."""
    import numpy as np
    import concepts_super as cs
    import concepts_grow as g

    doc = json.load(open(OUT, encoding="utf-8"))["records"]
    bases = {}
    for k, v in doc.items():
        b = v.get("base_id")
        if not b:
            continue
        r = bases.setdefault(b, {"base_id": b, "name": v.get("base_name"),
                                 "latex": v.get("base_latex"), "card": v.get("card"),
                                 "applications": []})
        for a in (f[k].get("articles") or []):
            r["applications"].append({"record": k, "article": a.get("id"),
                                      "title": a.get("title"),
                                      "latex": f[k].get("latex"),
                                      "meaning_ru": f[k].get("meaning")})
    print(f"основных форм: {len(bases)} · применений "
          f"{sum(len(b['applications']) for b in bases.values()):,}")

    ids = [b for b in bases if bases[b].get("card")]
    V = cs.embed_cards({b: {"name": bases[b]["name"], "card_en": bases[b]["card"]}
                        for b in ids}, g.load_key())[1] \
        if False else None
    # Векторизуем карточки основных форм тем же способом, что карточки понятий.
    texts = [f"{bases[b]['name']}. {bases[b]['card']}" for b in ids]
    import formulas_canon as fc
    V = fc.embed(texts, g.load_key())

    cids, CV = cs.load_cards()
    S = V @ CV.T
    out = []
    for i, b in enumerate(ids):
        order = np.argsort(-S[i])[:3]
        bases[b]["concepts"] = [{"concept": cids[int(j)], "sim": round(float(S[i, j]), 3)}
                                for j in order]
        out.append(bases[b])
    print("\nпримеры связей формула → понятие:")
    for r in sorted(out, key=lambda x: -len(x["applications"]))[:6]:
        top = ", ".join(f"{c['concept']} ({c['sim']:.2f})" for c in r["concepts"][:2])
        print(f"  {r['base_id']:<36} применений {len(r['applications']):>3} → {top}")
    p = DATA / "formulas-linked.json"
    p.write_text(json.dumps({"built": "2026-08-25", "bases": out},
                            ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
