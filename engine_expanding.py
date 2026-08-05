#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Исследовательский движок, поиск №2: РАСШИРЯЮЩИЕ работы.

ЧТО ЭТО. Не «похожие» (их даёт обычный ближний поиск), а «аналогичные по сути»: та же
структура задачи или тот же приём в ДРУГОЙ области. Диффузия в тепле ↔ в эпидемии ↔
в опционах. Это сердце услуги: релевантное исследователь и так знает, расширяющее — нет.

КОНСТРУКЦИЯ. Три условия одновременно:
  1. косинус в СРЕДНЕЙ зоне — выше неё работа про то же самое, ниже просто чужая;
  2. arXiv-раздел из ДРУГОЙ корневой группы — иначе это сосед по цеху, а не перенос;
  3. общая расчётная формула, если есть — прямая улика переноса метода (дерево формул).

ПРО ГРАНИЦЫ СРЕДНЕЙ ЗОНЫ. Не берём 0,45-0,60 на веру: они считаются от РАСПРЕДЕЛЕНИЯ
косинусов этой конкретной статьи к корпусу. У bge-m3 разброс узкий и плавает от статьи
к статье — фиксированные пороги на нём разъезжаются, я это уже ловил на тегах
(между «всё подряд» и «почти ничего» было 0,15).

ЧЕСТНАЯ ОГОВОРКА ПРО ОХВАТ. Ищем пока по нашим 2124 статьям, а не по всему arXiv:
эмбеддинги дампа на 3,1 млн — это 13 часов. Механизм меряется и на своём корпусе
(в нём есть astro-ph, quant-ph, cond-mat, cs, q-bio), а охват расширяется потом
выборкой из дампа. Мерить сначала на дешёвом, платить потом за подтверждённое.

    python engine_expanding.py --article 2607.13417 --n 8
    python engine_expanding.py --blind 12
"""
import json, math, pathlib, random, sys, argparse, collections

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
SEED = 42
# Доля корпуса, попадающая в «среднюю зону». Берём квантилями, а не абсолютом.
LO_Q, HI_Q = 0.75, 0.97


def nz(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def load():
    p = DATA / "embeddings-articles.jsonl"
    if not p.exists():
        sys.exit("нет embeddings-articles.jsonl")
    vecs = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            vecs[r["id"].split(":", 1)[1]] = nz(r["vec"])
    meta = {}
    for q in (MAIN / "lang" / "ru" / "archive").rglob("data.json"):
        try:
            d = json.loads(q.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = d.get("id")
        if aid in vecs:
            meta[aid] = {
                "title": (d.get("original_title") or "")[:110],
                "root": (d.get("primary_category") or "?").split(".")[0],
                "cat": d.get("primary_category") or "?",
                "tags": d.get("tags") or [],
            }
    # общие расчётные формулы: улика переноса метода
    lv_p, tr_p = DATA / "formula-levels.json", DATA / "formulas.json"
    art_f = collections.defaultdict(set)
    if lv_p.exists() and tr_p.exists():
        lv = json.loads(lv_p.read_text(encoding="utf-8"))
        fs = json.loads(tr_p.read_text(encoding="utf-8"))
        for key, rec in fs.items():
            for a in (rec.get("articles") or []):
                if a.get("id"):
                    art_f[a["id"]].add(key)
    return vecs, meta, art_f, (json.loads(lv_p.read_text(encoding="utf-8"))
                               if lv_p.exists() else {})


def expanding(src, vecs, meta, art_f, levels, n=8):
    if src not in vecs:
        return None
    sv = vecs[src]
    sims = []
    for aid, v in vecs.items():
        if aid == src:
            continue
        sims.append((sum(a * b for a, b in zip(sv, v)), aid))
    sims.sort(reverse=True)
    vals = sorted(s for s, _ in sims)
    lo = vals[int(LO_Q * (len(vals) - 1))]
    hi = vals[int(HI_Q * (len(vals) - 1))]

    src_root = meta.get(src, {}).get("root")
    src_f = art_f.get(src, set())
    out = []
    for s, aid in sims:
        if not (lo <= s <= hi):
            continue
        m = meta.get(aid) or {}
        if m.get("root") == src_root:      # свой раздел — это сосед, а не перенос
            continue
        shared = sorted(src_f & art_f.get(aid, set()))
        # приоритет тем, у кого общая расчётная формула: прямая улика переноса метода
        calc = [f for f in shared if (levels.get(f) or {}).get("level") == "расчётная"]
        why = [f"другая область: {m.get('cat')} против {meta.get(src,{}).get('cat')}"]
        if calc:
            why.append(f"общая расчётная формула ({len(calc)})")
        elif shared:
            why.append(f"общая формула ({len(shared)})")
        common_tags = set(meta.get(src, {}).get("tags", [])) & set(m.get("tags", []))
        if common_tags:
            why.append("общие понятия: " + ", ".join(sorted(common_tags)[:3]))
        out.append({"id": aid, "cos": round(s, 4), "title": m.get("title", ""),
                    "cat": m.get("cat"), "shared_calc": len(calc),
                    "why": "; ".join(why), "_rank": (len(calc), len(shared), s)})
    out.sort(key=lambda r: r["_rank"], reverse=True)
    for r in out:
        r.pop("_rank")
    return {"src": src, "zone": [round(lo, 4), round(hi, 4)], "expanding": out[:n]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", default="")
    ap.add_argument("--blind", type=int, default=0)
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args()
    vecs, meta, art_f, levels = load()
    print(f"корпус: {len(vecs)} статей, разделов "
          f"{len(set(m['root'] for m in meta.values()))}")

    if a.article:
        r = expanding(a.article, vecs, meta, art_f, levels, a.n)
        if not r:
            sys.exit("нет такой статьи в индексе")
        d = DATA / "research" / a.article
        d.mkdir(parents=True, exist_ok=True)
        (d / "engine.json").write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        print(f"\nисходная: {meta[a.article]['title']}  [{meta[a.article]['cat']}]")
        print(f"средняя зона: {r['zone'][0]}…{r['zone'][1]}\n")
        for e in r["expanding"]:
            print(f"  {e['cos']:.3f}  [{e['cat']}]  {e['title'][:70]}")
            print(f"         {e['why']}")
        print(f"\nзаписано: {d/'engine.json'}")
        return

    if a.blind:
        rnd = random.Random(SEED)
        for src in rnd.sample(sorted(vecs), a.blind):
            r = expanding(src, vecs, meta, art_f, levels, 3)
            if not r or not r["expanding"]:
                continue
            print(f"\n=== {meta[src]['title'][:74]}  [{meta[src]['cat']}]")
            for e in r["expanding"]:
                print(f"   {e['cos']:.3f} [{e['cat']}] {e['title'][:66]}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
