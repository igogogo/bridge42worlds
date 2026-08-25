#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Свести новые понятия с реестром: отсеять дубли между собой и собрать реестр v2.

ПОЧЕМУ ОТДЕЛЬНЫЙ ШАГ. При поиске кандидатов каждая подгруппа сверялась с СУЩЕСТВУЮЩИМИ
понятиями, но не с другими кандидатами. Это дало ожидаемую поломку: `little_red_dots`
из `primordial_black_hole` и `red_dots` из `black_hole` — одно и то же, названное
дважды, потому что пришли они от разных родителей и друг друга не видели.

ТРИ РАЗНЫХ СЛУЧАЯ, И ПУТАТЬ ИХ НЕЛЬЗЯ.

  ТОЖДЕСТВЕННЫЕ ИМЕНА. Из 1008 названий различных всего 808: `primordial_black_holes`
  модель выдала ТРИНАДЦАТЬ раз для тринадцати разных подгрупп. Это не ошибка модели,
  а её честный ответ — и заодно сигнал мне: в той области нарезка оказалась слишком
  мелкой, одно понятие разлетелось на куски. Такие записи схлопываются, их опоры
  объединяются, и число работ у понятия растёт, а не теряется.

  СОВПАДЕНИЕ С РЕЕСТРОМ. Новое имя равно существующему понятию. Это тоже не мусор:
  подгруппа даёт СТАРОМУ понятию новые опорные работы. Такие идут в «обогащение»,
  а не в отброс.

  БЛИЗКИЕ, НО РАЗНЫЕ ИМЕНА. Вот здесь и нужна сверка тремя признаками, и здесь же
  действует прежнее правило: без свидетельства ПО НАЗВАНИЮ пара не сливается.

Здесь дубли ищутся среди новых, и не одним признаком, а тремя, как и раньше:
пересечение пула работ, косинус центроидов и совпадение слов в названии. Правило то же,
что работало на прошлых волнах: без свидетельства ПО НАЗВАНИЮ пара не сливается —
геометрия отвечает на вопрос «про близкое ли это», а не «про одно ли».

ПРОВЕРКА, КОТОРУЮ МОЖНО ПРОВАЛИТЬ. Печатается, сколько среди верхних пар таких, где
одно название содержится в другом (`red_dots` ⊂ `little_red_dots`). Если ранжирование
их не поднимает, оно ранжирует что-то другое, и это будет видно.

    python concepts_merge.py --plan     показать дубли, ничего не писать
    python concepts_merge.py            собрать data/concepts-v2.json
"""
import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

STOP = {"of", "the", "and", "in", "a", "for", "with"}
DUP_COS = 0.95        # среди новых порог строже: они и так все из одной темы
DUP_JAC = 0.20


def words(s):
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower())
            if w and w not in STOP}


def nested(a, b):
    x, y = a.lower().replace("-", "_"), b.lower().replace("-", "_")
    return x in y or y in x or x.rstrip("s") == y.rstrip("s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--new", default=str(DATA / "concepts-new.json"))
    ap.add_argument("--out", default=str(DATA / "concepts-v2.json"))
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb
    from analytics_v2 import _field_dir

    reg = json.load(open(MAIN / "data/concepts.json", encoding="utf-8"))["concepts"]
    raw = json.load(open(args.new, encoding="utf-8"))["named"]
    print(f"реестр {len(reg)} · названий выдано {len(raw)}")

    # 1. Схлопываем тождественные имена: опоры объединяются.
    byid = {}
    for c in raw:
        cid = (c.get("id") or "").strip()
        if not cid:
            continue
        r = byid.setdefault(cid, {**c, "support": [], "parents": set(), "pieces": 0})
        r["support"] = sorted(set(r["support"]) | set(c.get("support") or []))
        r["parents"].add(c.get("parent"))
        r["pieces"] += 1
    for r in byid.values():
        r["parents"] = sorted(x for x in r["parents"] if x)
        r["n"] = len(r["support"])
    collapsed = len(raw) - len(byid)
    print(f"тождественных имён схлопнуто: {collapsed} · различных понятий {len(byid)}")

    # 2. Совпавшие с реестром — это обогащение старого понятия, а не отброс.
    enrich = {k: v for k, v in byid.items() if k in reg}
    new = [v for k, v in byid.items() if k not in reg]
    print(f"совпало с реестром (обогащение): {len(enrich)} · "
          f"действительно новых: {len(new)}")

    ids, M = vecstore.load(_field_dir() / "field", mmap=True)
    rowof = {}
    for i, s in enumerate(ids):
        rowof[fb._base_id(s)] = i

    cent, pools = [], []
    for c in new:
        rows = [rowof[a] for a in c["support"] if a in rowof]
        v = np.zeros(M.shape[1], dtype=np.float32)
        for r in rows:
            v += M[r]
        n = np.linalg.norm(v)
        cent.append(v / n if n else v)
        pools.append(set(c["support"]))
    C = np.vstack(cent)
    S = C @ C.T
    np.fill_diagonal(S, -1)

    pairs = []
    for i in range(len(new)):
        for j in range(i + 1, len(new)):
            cos = float(S[i, j])
            if cos < 0.80:
                continue
            A, B = pools[i], pools[j]
            jac = len(A & B) / max(1, len(A | B))
            wi, wj = words(new[i]["id"]), words(new[j]["id"])
            nam = len(wi & wj) / max(1, min(len(wi), len(wj)))
            pairs.append((i, j, cos, jac, nam))
    pairs.sort(key=lambda p: -(p[4] * 2 + p[2] + p[3]))
    print(f"пар с косинусом ≥0.80: {len(pairs)}")

    # Сливаем только при свидетельстве по названию. Геометрия подтверждает, не решает.
    merge = {}
    obvious = 0
    for i, j, cos, jac, nam in pairs:
        a, b = new[i]["id"], new[j]["id"]
        ev_name = nested(a, b) or nam >= 0.5
        if not ev_name:
            continue
        if not (cos >= DUP_COS or jac >= DUP_JAC):
            continue
        if nested(a, b):
            obvious += 1
        src, dst = (b, a) if len(pools[i]) >= len(pools[j]) else (a, b)
        if src in merge or dst in merge:
            continue
        merge[src] = dst

    print(f"\n{'=' * 74}")
    print(f"ДУБЛИ СРЕДИ НОВЫХ — {len(merge)} пар (вложенных названий среди них {obvious})")
    print("=" * 74)
    for i, j, cos, jac, nam in pairs[:12]:
        a, b = new[i]["id"], new[j]["id"]
        mark = "СЛИТЬ" if merge.get(a) == b or merge.get(b) == a else "оставить"
        print(f"  {a:<32} ~ {b:<32}")
        print(f"     косинус {cos:.3f} · Жаккар {jac:.2f} · слова {nam:.2f}  → {mark}")

    kept = [c for c in new if c["id"] not in merge]
    # Ещё одна проверка: новое понятие не должно повторять имя существующего.
    clash = [c for c in kept if c["id"] in reg]
    kept = [c for c in kept if c["id"] not in reg]
    print(f"\nновых после отсева: {len(kept)} "
          f"(слито {len(merge)}, совпало с реестром {len(clash)})")
    print(f"реестр станет: {len(reg)} + {len(kept)} = {len(reg) + len(kept)}")

    if args.plan:
        print("\n  --plan: ничего не записано")
        return 0

    v2 = dict(reg)
    for k, c in enrich.items():
        v2[k] = {**reg[k],
                 "support_added": c["support"][:12],
                 "article_count": max(reg[k].get("article_count") or 0, c["n"])}
    for c in kept:
        v2[c["id"]] = {"kind": c.get("kind") or "concept",
                       "name": c.get("name"), "card_en": c.get("card"),
                       "related": [], "scientists": [],
                       "origin": f"wave5-split:{c.get('parent')}",
                       "support": c.get("support", [])[:12],
                       "article_count": c.get("n", 0)}
    out = {"_": "Реестр v2: 536 исходных + новые из расщепления толстых понятий "
                "(волна 5, шаг 1). Карточки на английском, перевод отдельным шагом. "
                "Файл — предложение, боевой concepts.json не тронут.",
           "built": "2026-08-25", "from": len(reg), "added": len(kept),
           "collapsed_same_name": collapsed, "enriched": len(enrich),
           "merged_duplicates": merge, "concepts": v2}
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
