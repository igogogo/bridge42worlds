#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 1 волны 5, вторая половина: найти новые понятия и написать карточки.

Владелец 25 августа: довести реестр до 1000-2000 понятий; «жогнал карточки понятий,
перестроил и переразметил». Добро на 0.85 $ получено 25.08, карточки входят.

ОТКУДА БЕРУТСЯ НОВЫЕ ПОНЯТИЯ — ИЗ ДВУХ РАЗНЫХ МЕСТ, И ЭТО ВАЖНО.

  РАСЩЕПЛЕНИЕ ТОЛСТЫХ. 47 понятий с опорой ≥150 работ держат 83% архива:
  `spectroscopy` — 913 работ. Это не понятие, а суперпонятие не на своём месте.
  Его пул режется на подгруппы, и каждая подгруппа — кандидат в настоящее понятие.
  Здесь новые понятия рождаются осмысленными по построению: все работы подгруппы
  уже про спектроскопию, различает их что-то более тонкое.

  ДЫРЫ. Работы, не покрытые ни одним понятием с достаточной опорой, собираются
  в группы отдельно. Их меньше и они шумнее — зато это то, чего в реестре нет вовсе.

ЧЕМ КАНДИДАТ ОТСЕИВАЕТСЯ. Центроид подгруппы сравнивается с центроидами ВСЕХ
существующих понятий: косинус выше порога — это не новое понятие, а то же самое
другими словами. Платить за переименование того, что уже есть, незачем.

БЮДЖЕТ ЖЁСТКИЙ. Расход считается по токенам, которые вернул поставщик, и на потолке
прогон ОСТАНАВЛИВАЕТСЯ, а не «почти останавливается». Всё, что успели, дописано
на диск: прерывание не теряет работу.

    python concepts_grow.py --plan             найти кандидатов, ничего не тратить
    python concepts_grow.py --budget 0.85      найти и назвать
"""
import argparse
import collections
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
PRICE_IN, PRICE_OUT = 0.27 / 1e6, 1.00 / 1e6      # $/токен, вне пика
FAT = 60             # опора, с которой понятие считается суперпонятием.
                     # Было 150 — замер показал, что при 60 кандидатов вдвое
                     # больше при той же опоре у новых понятий.
PIECE = 8            # целевой размер подгруппы при расщеплении.
                     # Замер связи «мельче кусок — больше понятий, но
                     # слабее опора»: 12→1122 понятия при медиане 8 работ,
                     # 8→1622 при 7, 6→2560 при 6, 4→3876 при 4. Цель
                     # владельца 1000-2000 берётся на 8, и опора ещё жива.
MIN_PIECE = 5        # меньше — нет опоры, понятие не заводим
DUP_COS = 0.93       # выше — это уже существующее понятие
PER_CALL = 4         # кандидатов в одном запросе

SYS = """You name scientific concepts for a knowledge registry, from evidence only.

For each numbered group you get real article titles from one physics corpus. All
articles in a group are close in meaning. Your job: name the concept they share.

Return a JSON array, one object per group, same order:
  {"n": <group number>,
   "id": "<snake_case_english_id>",
   "name": "<short English name, 1-4 words>",
   "kind": "<one of: concept|method|object|law|equation|effect|theorem|math|
             substance|principle|instrument|phenomenon|invention>",
   "card": "<one English sentence, max 25 words, saying what it is>"}

Rules:
1. Name ONLY what the titles actually show. If they share nothing specific,
   set "id" to "" — an honest refusal is better than an invented concept.
2. The name must be MORE SPECIFIC than the parent concept given for the group.
   Repeating the parent is a failure.
3. No marketing, no hedging. A physicist must recognise the term.
Output ONLY the JSON array."""


def field_rows():
    import vecstore
    import field_build as fb
    from analytics_v2 import _field_dir
    ids, M = vecstore.load(_field_dir() / "field", mmap=True)
    rowof = {}
    for i, s in enumerate(ids):
        rowof[fb._base_id(s)] = i
    return rowof, M


def load_corpus(lang):
    import field_build as fb
    idx = json.load(open(MAIN / f"lang/{lang}/articles-index.json", encoding="utf-8"))
    art = {}
    for a in idx:
        aid = fb._base_id(str(a.get("id") or ""))
        if not aid:
            continue
        r = art.setdefault(aid, {"con": set(), "title": ""})
        r["con"] |= set((a.get("tags") or []) + (a.get("laws") or []))
        if not r["title"]:
            r["title"] = a.get("title") or ""
    return art


def load_key():
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DEEPINFRA_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("нет ключа")


def ask(payload, key, tries=4):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": payload}],
        "temperature": 0.2, "max_tokens": 900,
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


def find_candidates(reg, art, X, pos, have, pool):
    import numpy as np
    from sklearn.cluster import KMeans

    names, vecs = [], []
    for k, ps in pool.items():
        if len(ps) >= 3:
            v = X[[pos[a] for a in ps]].mean(0)
            n = np.linalg.norm(v)
            if n:
                names.append(k)
                vecs.append(v / n)
    E = np.vstack(vecs)
    print(f"существующих понятий с опорой ≥3: {len(names)}")

    cands = []

    def take(mem, origin, parent):
        v = X[[pos[a] for a in mem]].mean(0)
        v /= np.linalg.norm(v) + 1e-9
        sims = E @ v
        j = int(sims.argmax())
        if float(sims[j]) >= DUP_COS:
            return
        cands.append({"origin": origin, "parent": parent, "articles": mem,
                      "n": len(mem), "closest": round(float(sims[j]), 3),
                      "closest_id": names[j]})

    fat = sorted(((k, ps) for k, ps in pool.items() if len(ps) >= FAT),
                 key=lambda x: -len(x[1]))
    print(f"расщепляю {len(fat)} толстых понятий…")
    for k, ps in fat:
        arts = sorted(ps)
        n_sub = max(2, len(arts) // PIECE)
        lab = KMeans(n_clusters=n_sub, n_init=3,
                     random_state=0).fit(X[[pos[a] for a in arts]]).labels_
        for c in range(n_sub):
            mem = [arts[i] for i in np.where(lab == c)[0]]
            if len(mem) >= MIN_PIECE:
                take(mem, "split", k)

    thin = [a for a in have
            if not any(len(pool.get(e, ())) >= MIN_PIECE for e in art[a]["con"])]
    print(f"работ без опорного понятия: {len(thin):,}")
    if len(thin) >= MIN_PIECE * 2:
        n_sub = max(2, len(thin) // PIECE)
        lab = KMeans(n_clusters=n_sub, n_init=3,
                     random_state=0).fit(X[[pos[a] for a in thin]]).labels_
        for c in range(n_sub):
            mem = [thin[i] for i in np.where(lab == c)[0]]
            if len(mem) >= MIN_PIECE:
                take(mem, "hole", None)

    cands.sort(key=lambda c: -c["n"])
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--budget", type=float, default=0.85)
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--out", default=str(DATA / "concepts-new.json"))
    args = ap.parse_args()

    import numpy as np

    reg = json.load(open(MAIN / "data/concepts.json", encoding="utf-8"))["concepts"]
    art = load_corpus(args.lang)
    rowof, M = field_rows()
    have = [a for a in art if a in rowof]
    X = np.empty((len(have), M.shape[1]), dtype=np.float32)
    for i, a in enumerate(have):
        X[i] = M[rowof[a]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    pos = {a: i for i, a in enumerate(have)}
    print(f"работ с вектором: {len(have):,} из {len(art):,}")

    pool = collections.defaultdict(set)
    for a in have:
        for e in art[a]["con"]:
            if e in reg:
                pool[e].add(a)

    cands = find_candidates(reg, art, X, pos, have, pool)
    by = collections.Counter(c["origin"] for c in cands)
    print(f"\n{'=' * 74}")
    print("КАНДИДАТЫ В НОВЫЕ ПОНЯТИЯ")
    print("=" * 74)
    print(f"  всего {len(cands)} · расщепление {by['split']} · дыры {by['hole']}")
    print(f"  работ в них: {sum(c['n'] for c in cands):,}")
    print(f"  реестр стал бы {len(reg)} + {len(cands)} = {len(reg) + len(cands)}")
    calls = (len(cands) + PER_CALL - 1) // PER_CALL
    est = calls * (1400 * PRICE_IN + 700 * PRICE_OUT)
    print(f"  запросов по {PER_CALL} кандидата: {calls} · оценка {est:.2f} $ "
          f"(потолок {args.budget:.2f} $)")
    for c in cands[:8]:
        print(f"    {c['origin']:<6}{c['n']:>4} работ · ближайшее "
              f"{c['closest_id']} ({c['closest']:.2f})"
              + (f" ← из {c['parent']}" if c["parent"] else ""))

    if args.plan:
        print("\n  --plan: ни одного вызова не сделано")
        pathlib.Path(args.out).write_text(
            json.dumps({"candidates": cands, "estimate": round(est, 3)},
                       ensure_ascii=False), encoding="utf-8")
        print(f"→ {args.out}")
        return 0

    key = load_key()
    named, spent, tin, tout = [], 0.0, 0, 0
    out_path = pathlib.Path(args.out)
    for st in range(0, len(cands), PER_CALL):
        if spent >= args.budget:
            print(f"\nПОТОЛОК {args.budget:.2f} $ ДОСТИГНУТ — останавливаюсь. "
                  f"Названо {len(named)} из {len(cands)}.")
            break
        chunk = cands[st:st + PER_CALL]
        lines = []
        for i, c in enumerate(chunk, 1):
            t = [art[a]["title"] for a in c["articles"][:6] if art[a]["title"]]
            lines.append(f"GROUP {i} (parent concept: {c['parent'] or 'none'}, "
                         f"{c['n']} articles)\n"
                         + "\n".join(f"  - {x[:110]}" for x in t))
        try:
            res, pi, po = ask("\n\n".join(lines), key)
        except Exception as ex:
            print(f"  !! пачка {st // PER_CALL + 1}: {type(ex).__name__} — пропуск")
            continue
        tin += pi
        tout += po
        spent = tin * PRICE_IN + tout * PRICE_OUT
        for c, r in zip(chunk, res if isinstance(res, list) else []):
            if not isinstance(r, dict) or not r.get("id"):
                continue
            named.append({**{k: v for k, v in c.items() if k != "articles"},
                          "id": r.get("id"), "name": r.get("name"),
                          "kind": r.get("kind"), "card": r.get("card"),
                          "support": c["articles"][:12]})
        done = st + len(chunk)
        print(f"  {done}/{len(cands)} · названо {len(named)} · "
              f"потрачено {spent:.3f} $")
        out_path.write_text(json.dumps(
            {"built": "2026-08-25", "named": named, "spent": round(spent, 4),
             "tokens_in": tin, "tokens_out": tout,
             "candidates_total": len(cands)}, ensure_ascii=False, indent=1),
            encoding="utf-8")

    print(f"\n{'=' * 74}")
    print(f"названо понятий: {len(named)} · потрачено {spent:.3f} $ "
          f"из {args.budget:.2f} $")
    print(f"токенов: вход {tin:,} · выход {tout:,}")
    print(f"→ {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
