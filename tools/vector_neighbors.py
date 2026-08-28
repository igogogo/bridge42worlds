# -*- coding: utf-8 -*-
"""Соседи по смыслу — тем, у кого нет соседей по статьям.

Связи в реестре считает супер, и считает он их по со-встречаемости: два понятия
соседи, если стоят вместе в статьях, а вектор лишь уточняет вес. Для добытого из
статей это верно. Но константа пришла из формулы, а статистический метод из
канона предмета — статей у них ноль, значит и соседей ноль: понятие открывается,
показывает своё определение и никуда не ведёт.

Владелец 27.08: «сирота относительно статьи оправдана, сирот не должно быть
относительно связей внутри понятий».

Здесь связь берётся из одного вектора карточки — того же bge-m3, которым супер
меряет близость. Порог 0.55 подобран по замеру: ниже начинается «всё похоже на
всё» (у статистических методов особенно, они все про данные), выше связи
пропадают совсем. Вес пишем отдельным полем, чтобы страница и граф могли отличить
смысловую связь от статейной.

  python tools/vector_neighbors.py            # показать
  python tools/vector_neighbors.py --apply
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
VECS = ML / "data" / "concept-cards.f16"
IDS = ML / "data" / "concept-cards.ids"
LIVE = ROOT / "data" / "concepts-live.json"
OUT = ROOT / "data" / "concept-vec-neighbors.json"

THR = 0.55
TOP = 6


def main():
    apply = "--apply" in sys.argv
    import numpy as np

    live = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    ids = IDS.read_text(encoding="utf-8").splitlines()
    V = np.fromfile(VECS, dtype=np.float16).reshape(len(ids), -1).astype(np.float32)
    V /= (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
    pos = {c: i for i, c in enumerate(ids)}

    lonely = [c for c, v in live.items()
              if not (v.get("related") or []) and c in pos]
    print(f"понятий без соседей: {len(lonely)} из {len(live)}")
    if not lonely:
        return 0

    out, empty = {}, 0
    for cid in lonely:
        sims = V @ V[pos[cid]]
        order = np.argsort(-sims)
        got = []
        for j in order[:TOP * 4]:
            other = ids[j]
            if other == cid or other not in live:
                continue
            s = float(sims[j])
            if s < THR:
                break
            got.append({"id": other, "w": round(s, 3), "src": "vec"})
            if len(got) >= TOP:
                break
        if got:
            out[cid] = got
        else:
            empty += 1

    print(f"нашлись соседи: {len(out)} · осталось без связей: {empty}")
    shown = 0
    for cid, got in out.items():
        if shown >= 8:
            break
        if live[cid].get("origin") in ("formula-constant", "codata-core",
                                       "statistics-core"):
            print(f"  {cid:32s} → " + ", ".join(f'{g["id"]} {g["w"]}' for g in got[:3]))
            shown += 1
    if not apply:
        print("\nсухой ход. записать: --apply")
        return 0
    # ДОПОЛНЯЕМ, а не перезаписываем. Прогон видит только тех, кто одинок ПРЯМО
    # СЕЙЧАС, и это зависит от того, когда его запустили: 28.08 он попал между
    # пересчётом связности и сборкой реестра, нашёл пятерых — и затёр тысячу с
    # лишним записей, посчитанных до того. Файл здесь — копилка, как и всюду в
    # доме, а не снимок последнего прогона.
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            old = {}
    old.update(out)
    OUT.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    print(f"→ {OUT.name}: +{len(out)} записей, всего {len(old)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
