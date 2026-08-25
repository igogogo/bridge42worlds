#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаги 2-4 волны 5: непересекаемость, связи с мощностью, суперпонятия с перекрытием.

Владелец 25 августа: понятия атомарны (шаг 2); связи не бинарные, а с весом (шаг 3);
суперпонятия вычленяются кластеризацией и ПЕРЕСЕКАЮТСЯ, их около полусотни, по ним
строится верхний уровень графа с дрилл-дауном (шаг 4).

ВЕКТОР ПОНЯТИЯ — ТЕПЕРЬ ЕГО СОБСТВЕННЫЙ ТЕКСТ. До карточек понятие было представлено
центроидом своих статей, то есть косвенно: средним по чужим работам. Теперь у каждого
из 1244 понятий есть английская карточка, и она векторизуется напрямую. Это меняет
смысл сравнения: раньше два понятия были «похожи», если их статьи похожи; теперь —
если похожи они сами. Для атомарности это принципиально: два разных понятия могут
стоять в одних и тех же статьях и при этом быть разными.

Обе меры считаются и печатаются рядом, потому что расхождение между ними — само
по себе находка: пара с высоким пересечением пулов и низким сходством карточек
это не дубль, а два разных понятия, которые всегда встречаются вместе.

ПЕРЕКРЫТИЕ СУПЕРПОНЯТИЙ ОГРАНИЧИВАЕТСЯ, А НЕ ПРОСТО РАЗРЕШАЕТСЯ. Понятие обязано
попадать в несколько групп — `entropy` живёт и в термодинамике, и в теории информации,
и в чёрных дырах, и жёсткое разбиение заставило бы выбрать одно и соврать. Но если
понятие попадёт в восемь групп из пятидесяти, верхний уровень превратится в кашу:
круги перекроются все со всеми, и смотреть будет не на что. Поэтому членство даётся
по запасу от лучшего и обрезается сверху, а распределение членств печатается —
это параметр под замер, а не под назначение.

    python concepts_super.py --embed          векторизовать карточки (платно, копейки)
    python concepts_super.py                  шаги 2-4 на готовых векторах
"""
import argparse
import collections
import json
import math
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

CARD_VECS = DATA / "concept-cards.f16"
CARD_IDS = DATA / "concept-cards.ids"
SUPERS = 50          # верхний уровень: столько кругов человек ещё различает
MAX_MEMBER = 3       # больше членств — верхний уровень становится кашей
MARGIN = 0.04        # насколько близко к лучшему, чтобы засчитать второе членство


def embed_cards(reg, key, batch=64):
    """Векторизовать карточки через bge-m3. 1244 карточки — доли цента."""
    import numpy as np
    ids = [k for k, v in reg.items() if v.get("card_en")]
    texts = [f"{reg[k].get('name') or k}. {reg[k]['card_en']}" for k in ids]
    out = []
    for st in range(0, len(texts), batch):
        body = json.dumps({"inputs": texts[st:st + batch]}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepinfra.com/v1/inference/BAAI/bge-m3", data=body,
            headers={"Authorization": f"bearer {key}",
                     "Content-Type": "application/json"})
        for a in range(4):
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    d = json.loads(r.read().decode("utf-8"))
                out.extend(d["embeddings"])
                break
            except Exception:
                if a == 3:
                    raise
                time.sleep(2 * (a + 1))
        print(f"  {min(st + batch, len(texts))}/{len(texts)}")
    V = np.asarray(out, dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    V.astype(np.float16).tofile(CARD_VECS)
    CARD_IDS.write_text("\n".join(ids), encoding="utf-8")
    print(f"→ {CARD_VECS} ({V.shape})")
    return ids, V


def load_cards():
    import numpy as np
    ids = CARD_IDS.read_text(encoding="utf-8").splitlines()
    V = np.fromfile(CARD_VECS, dtype=np.float16).reshape(len(ids), -1)
    return ids, np.asarray(V, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--reg", default=str(DATA / "concepts-v2.json"))
    ap.add_argument("--supers", type=int, default=SUPERS)
    ap.add_argument("--out", default=str(DATA / "concepts-super.json"))
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--name-supers", action="store_true",
                    help="дать суперпонятиям названия (платно, копейки)")
    args = ap.parse_args()

    import numpy as np
    import concepts_grow as g

    doc = json.load(open(args.reg, encoding="utf-8"))
    reg = doc["concepts"]
    print(f"реестр: {len(reg)} понятий, "
          f"{sum(1 for v in reg.values() if v.get('card_en'))} с карточкой")

    if args.embed:
        ids, V = embed_cards(reg, g.load_key())
    else:
        if not CARD_VECS.exists():
            sys.exit("нет векторов карточек — сначала python concepts_super.py --embed")
        ids, V = load_cards()
    print(f"векторов карточек: {len(ids)}")

    # Пулы статей — для со-встречаемости и для сравнения двух мер.
    art = g.load_corpus(args.lang)
    pool = collections.defaultdict(set)
    for a, r in art.items():
        for e in r["con"]:
            if e in reg:
                pool[e].add(a)
    # у новых понятий пул — их опора
    for k, v in reg.items():
        for a in (v.get("support") or []):
            pool[k].add(a)
    idx = {k: i for i, k in enumerate(ids)}

    # ── ШАГ 2: НЕПЕРЕСЕКАЕМОСТЬ ──────────────────────────────────────────
    S = V @ V.T
    np.fill_diagonal(S, -1)
    print(f"\n{'=' * 76}")
    print("ШАГ 2 · НЕПЕРЕСЕКАЕМОСТЬ ПОНЯТИЙ")
    print("=" * 76)
    rows = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            cos = float(S[i, j])
            if cos < 0.90:
                continue
            A, B = pool.get(ids[i], set()), pool.get(ids[j], set())
            jac = len(A & B) / max(1, len(A | B))
            rows.append((ids[i], ids[j], cos, jac))
    rows.sort(key=lambda r: -r[2])
    print(f"  пар с сходством карточек ≥0.90: {len(rows)}")
    both = [r for r in rows if r[3] >= 0.30]
    only_card = [r for r in rows if r[3] < 0.05]
    print(f"    и пулы пересекаются (≥0.30): {len(both)} ← кандидаты на слияние")
    print(f"    но пулы НЕ пересекаются (<0.05): {len(only_card)} ← омонимы или "
          f"одно понятие в разных областях")
    for a, b, c, j in both[:6]:
        print(f"      {a:<34} ~ {b:<30} карточки {c:.3f} пулы {j:.2f}")
    if only_card:
        print("    из них с явной опиской или вложенным именем — это дубли, "
              "а не омонимы:")
        for a, b, c, j in only_card[:4]:
            print(f"      {a:<34} ~ {b:<30} карточки {c:.3f} пулы {j:.2f}")

    # ── ШАГ 3: СВЯЗИ С МОЩНОСТЬЮ ─────────────────────────────────────────
    print(f"\n{'=' * 76}")
    print("ШАГ 3 · СВЯЗИ С МОЩНОСТЬЮ")
    print("=" * 76)
    co = collections.Counter()
    for a, r in art.items():
        es = sorted(e for e in r["con"] if e in idx)
        for x in range(len(es)):
            for y in range(x + 1, len(es)):
                co[(es[x], es[y])] += 1
    links = []
    for (a, b), n in co.items():
        if n < 3:
            continue
        # Симметричная нормировка: без неё редкое понятие выигрывает у частого
        # не связью, а малым знаменателем — на этом я уже обжигалась.
        w_co = n / math.sqrt(len(pool[a]) * len(pool[b]))
        w_vec = float(V[idx[a]] @ V[idx[b]])
        links.append({"a": a, "b": b, "n": n,
                      "w_cooc": round(w_co, 4), "w_vec": round(w_vec, 4),
                      "w": round(0.5 * w_co + 0.5 * max(0.0, w_vec), 4)})
    links.sort(key=lambda x: -x["w"])
    print(f"  связей с опорой ≥3 работ: {len(links):,}")
    print(f"  вес = половина со-встречаемости + половина сходства карточек")
    for l in links[:6]:
        print(f"    {l['a']:<30} — {l['b']:<28} вес {l['w']:.3f} "
              f"(вместе {l['n']} работ)")

    # ── ШАГ 4: СУПЕРПОНЯТИЯ С ПЕРЕКРЫТИЕМ ────────────────────────────────
    from sklearn.cluster import KMeans
    print(f"\n{'=' * 76}")
    print(f"ШАГ 4 · СУПЕРПОНЯТИЯ — {args.supers} групп с перекрытием")
    print("=" * 76)
    km = KMeans(n_clusters=args.supers, n_init=6, random_state=0).fit(V)
    C = km.cluster_centers_
    C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
    sims = V @ C.T
    best = sims.max(1)
    member = {}
    for i, k in enumerate(ids):
        order = np.argsort(-sims[i])
        take = [int(c) for c in order
                if sims[i, c] >= best[i] - MARGIN][:MAX_MEMBER]
        member[k] = take
    cnt = collections.Counter(len(v) for v in member.values())
    print(f"  членств на понятие: " + " · ".join(
        f"{k} → {v}" for k, v in sorted(cnt.items())))
    print(f"  среднее {sum(len(v) for v in member.values()) / len(member):.2f} "
          f"(потолок {MAX_MEMBER}, запас {MARGIN})")
    groups = collections.defaultdict(list)
    for k, cs in member.items():
        for c in cs:
            groups[c].append(k)
    sizes = sorted((len(v) for v in groups.values()), reverse=True)
    print(f"  размеры групп: крупнейшая {sizes[0]}, медиана {sizes[len(sizes) // 2]}, "
          f"мельчайшая {sizes[-1]}")
    print("\n  чем группы наполнены (по три самых опорных понятия):")
    for c in sorted(groups, key=lambda c: -len(groups[c]))[:8]:
        top = sorted(groups[c], key=lambda k: -len(pool.get(k, ())))[:3]
        print(f"    группа {c:>2} ({len(groups[c]):>3} понятий): {', '.join(top)}")

    titles = {}
    if args.name_supers:
        # Верхний уровень графа без названий бесполезен: круг с номером 17 читателю
        # ничего не говорит. Модель видит опорные понятия группы и даёт ей имя.
        SYS_S = ("You name a broad area of physics from the concepts it contains. "
                 'Return a JSON array: [{"n": <group number>, "name": "<2-4 English words>"}]. '
                 "The name must cover the listed concepts and be recognisable to a "
                 "physicist. No marketing. Output ONLY the array.")
        key = g.load_key()
        gl = sorted(groups, key=lambda c: -len(groups[c]))
        for st in range(0, len(gl), 8):
            part = gl[st:st + 8]
            payload = "\n\n".join(
                f"GROUP {c}: " + ", ".join(
                    sorted(groups[c], key=lambda k: -len(pool.get(k, ())))[:12])
                for c in part)
            body = json.dumps({
                "model": "deepseek-ai/DeepSeek-V3.1",
                "messages": [{"role": "system", "content": SYS_S},
                             {"role": "user", "content": payload}],
                "temperature": 0.2, "max_tokens": 500,
                "response_format": {"type": "json_object"}}).encode("utf-8")
            try:
                req = urllib.request.Request(
                    "https://api.deepinfra.com/v1/openai/chat/completions",
                    data=body, headers={"Authorization": f"bearer {key}",
                                        "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    d = json.loads(r.read().decode("utf-8"))
                txt = d["choices"][0]["message"]["content"].strip()
                if txt.startswith("```"):
                    txt = txt.split("```")[1]
                    txt = txt[4:] if txt.startswith("json") else txt
                res = json.loads(txt)
                if isinstance(res, dict):
                    res = next((v for v in res.values() if isinstance(v, list)), [])
                for r0 in res:
                    if isinstance(r0, dict) and r0.get("name") is not None:
                        titles[str(r0.get("n"))] = r0["name"]
            except Exception as ex:
                print(f"  !! имена групп {part[:2]}…: {type(ex).__name__}")
        print(f"\nназвано групп: {len(titles)} из {len(groups)}")
        for c in gl[:8]:
            print(f"    группа {c:>2}: {titles.get(str(c), '—')}")

    out = {"built": "2026-08-25", "concepts": len(ids), "supers": args.supers,
           "super_names": titles,
           "max_membership": MAX_MEMBER, "margin": MARGIN,
           "membership": {k: v for k, v in member.items()},
           "groups": {str(c): sorted(v, key=lambda k: -len(pool.get(k, ())))
                      for c, v in groups.items()},
           "links": links[:6000],
           "overlap_pairs": [{"a": a, "b": b, "card": round(c, 3),
                              "pool": round(j, 3)} for a, b, c, j in rows[:400]],
           "note": "Членство ограничено сверху: без ограничения верхний уровень "
                   "перекрывается весь со всем и перестаёт что-либо показывать."}
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False),
                                      encoding="utf-8")
    print(f"\n→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
