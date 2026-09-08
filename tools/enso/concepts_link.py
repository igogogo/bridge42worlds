# -*- coding: utf-8 -*-
"""Понятия к якорям панели: облако терминов рядом с каждым числом и утверждением.

Владелец 07.09: «надо как-то уместить облако тегов — контекстное, подсветить, где уже
подсвечено, в тултип, и ссылку на открытие графа». Слой данных для этого — здесь; вид
делает сессия панели по заданию ЭЛЬНИНЬО-РАЗМЕТКА-ПОНЯТИЯМИ.md.

Устроено как разметка работ (links.py), только ищем не статьи, а понятия:

  · ЯКОРЯ ТЕ ЖЕ. Риск по имени правила, тревога по id, термин словаря, регион, блок —
    один и тот же список на два вида привязки. Панель не учит второй язык адресов.
  · ВЕКТОР ВМЕСТО ПРОМПТА. У понятий есть карточки и посчитанные векторы (bge-m3,
    матрица b42-ml/data/concept-cards.f16, пересчитана 08.09 от полных карточек).
    Спрашивать модель незачем: близость карточки к тексту якоря — и есть ответ.
  · ПОРОГ, А НЕ ПЕРВЫЕ N. Берём то, что реально близко: ниже порога связь случайна,
    и пять случайных понятий хуже двух настоящих.

    python tools/enso/concepts_link.py --plan     посчитать, ничего не записывая
    python tools/enso/concepts_link.py --run      записать data/enso/concepts.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ML = ROOT.parent / "b42-ml"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "enso"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = ROOT / "data" / "enso" / "concepts.json"
FLOOR = 0.42          # ниже — случайная близость; проверено на глаз по выдаче
TOP = 7               # больше семи чипов в подсказку не влезает без прокрутки


def load_cards():
    """Карточки понятий: имена, матрица векторов, живой реестр."""
    sys.path.insert(0, str(ML))
    import concepts_super as cs
    cids, CV = cs.load_cards()
    reg = json.loads((ROOT / "data" / "concepts-live.json").read_text(encoding="utf-8"))["concepts"]
    return cids, CV, reg


def main():
    ap = argparse.ArgumentParser(description="Понятия к якорям панели El Niño")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--floor", type=float, default=FLOOR)
    ap.add_argument("--top", type=int, default=TOP)
    a = ap.parse_args()

    import numpy as np
    import links as LK                                   # те же якоря, что у работ

    anc = LK.anchors()
    cids, CV, reg = load_cards()
    print(f"якорей {len(anc)} · понятий с вектором {len(cids)}")

    # Вектор якоря считаем тем же движком, что и вектор карточки: иначе сравниваем
    # разные пространства и получаем правдоподобную чушь.
    A = LK.vectors([x["text"] for x in anc], "якоря")
    A = np.asarray(A, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    C = np.asarray(CV, dtype=np.float32)
    C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
    S = A @ C.T

    out, empty = {}, 0
    for i, x in enumerate(anc):
        idx = np.argsort(-S[i])[:a.top * 3]
        rows = []
        for j in idx:
            sc = float(S[i][j])
            if sc < a.floor:
                break
            cid = cids[j]
            r = reg.get(cid) or {}
            rows.append({"id": cid, "score": round(sc, 3),
                         "kind": r.get("kind") or "concept",
                         "name_en": ((r.get("names") or {}).get("en")
                                     or cid.replace("_", " ")),
                         # Русское имя лежит в словаре names ({'ru': …}), а не полем:
                         # реестр держит все языки в одном месте (проверено 08.09).
                         "name_ru": (r.get("names") or {}).get("ru") or "",
                         "line": (r.get("card_en") or "")[:220]})
            if len(rows) >= a.top:
                break
        if rows:
            out[x["id"]] = rows
        else:
            empty += 1

    tot = sum(len(v) for v in out.values())
    print(f"якорей с понятиями {len(out)} из {len(anc)} · всего связей {tot} · "
          f"пусто у {empty}")
    for k in list(out)[:6]:
        names = ", ".join(r["name_en"] for r in out[k][:4])
        print(f"   {k}: {names}")
    if not a.run:
        print("(показ; чтобы записать, добавьте --run)")
        return 0

    OUT.write_text(json.dumps({
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "floor": a.floor, "top": a.top,
        "n_anchors": len(anc), "n_links": tot,
        "note": "Concepts near each dashboard statement. Vector distance between the "
                "anchor text and the concept card; no model asked. A link means 'this "
                "term explains what is being said here', not 'this is the source'.",
        "anchors": out,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"✅ {OUT.relative_to(ROOT)}: {len(out)} якорей, {tot} связей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
