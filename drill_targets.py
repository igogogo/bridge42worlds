#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карта → конкретные работы к бурению. Не «где пусто», а «вот что писать».

Владелец 11 августа: «попробуйте уже с использованием этого механизма что-то сделать,
во всяком случае определить какие статьи выбрать, дополнить их нашими рекомендациями».

Это замыкающее звено: до сих пор карта отвечала «здесь пусто», а редакция всё равно
не знала, ЧТО именно брать. Здесь пустая область превращается в список работ, каждая
из которых (а) лежит в этой области, (б) прошла проверку на интересность читателю
тем же реранкером, что работает в ночном отборе.

ПОЧЕМУ НЕ ПРОСТО «БЛИЖАЙШИЕ К ЦЕНТРУ ОБЛАСТИ». Потому что близость к центру — это
типичность, а нам нужна не типичная работа, а интересная. Замер 10 августа: вектор
умеет вычёркивать, но не умеет ранжировать по интересности — три ранжирующие оси
закрыты числом. Ранжирует кросс-энкодер, читающий пару «наши критерии + работа» вместе.

ДВА ОТСЕВА, оба нужны:
  · по области — работа должна лежать в дырке, а не рядом с ней;
  · по интересности — в дырке полно проходных работ, и бурить надо не в любую точку
    пласта, а в ту, где есть чем поживиться.

    python drill_targets.py --holes 8 --per-hole 3     план на ближайшие ночи
    python drill_targets.py --holes 20 --per-hole 5 --out data/drill-targets.json
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holes", type=int, default=8, help="сколько слепых зон брать")
    ap.add_argument("--per-hole", type=int, default=3, help="сколько работ из каждой")
    ap.add_argument("--pool", type=int, default=40,
                    help="сколько кандидатов из области отдавать реранкеру")
    ap.add_argument("--out", default="data/drill-targets.json")
    ap.add_argument("--since", default="",
                    help="брать работы не старше месяца ГГГГ-ММ (пусто — вся история)")
    ap.add_argument("--by-size", action="store_true",
                    help="брать крупнейшие дырки вместо самых перспективных")
    ap.add_argument("--model", default="8B")
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import drill
    import rerank_eval as rr
    import field_build as fb

    cp, rp = DATA / "drill-centers.npy", DATA / "drill-regions.json"
    if not (cp.exists() and rp.exists()):
        sys.exit("нет карты — сначала: python drill.py --regions 600 --min-arxiv 15")
    C = np.load(cp)
    R = json.loads(rp.read_text(encoding="utf-8"))

    ids, M = vecstore.load(DATA / "field", latest=True)
    A = np.asarray(M, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    print(f"поле: {len(ids):,} работ · областей: {len(C)}")

    lab = np.empty(len(A), dtype=np.int32)
    for s in range(0, len(A), 4096):
        lab[s:s + 4096] = (A[s:s + 4096] @ C.T).argmax(1)

    holes = [j for j in range(len(C))
             if R["n_ours"][j] == 0 and not R["restricted"][j]
             and R["n_arxiv"][j] >= R["min_arxiv"]]
    # ПОРЯДОК ДЫРОК — ПО ДОБЫЧЕ, А НЕ ПО РАЗМЕРУ. Первая версия брала самые крупные
    # и получила цели с интересностью 0,005-0,028 при том, что в ночном отборе живая
    # работа набирает 0,06 и выше. Крупнейшие дырки оказались пусты ПРАВИЛЬНО: там
    # вычислительные методы, Монте-Карло, алгебры Ли — работы про то, КАК считать.
    # Инструмент, ищущий дырки, и инструмент, судящий интерес, разошлись, и слушать
    # надо второго: бурят не в самый большой пласт, а в тот, где есть чем поживиться.
    holes.sort(key=lambda j: -R["n_arxiv"][j])
    if args.by_size:
        holes = holes[:args.holes]
    print(f"слепых зон всего: {len(holes)}"
          + (f", беру {args.holes} крупнейших" if args.by_size
             else f" — просматриваю все, отберу {args.holes} по добыче"))

    # Тексты нужны и реранкеру, и человеку. Читаем выгрузку по месяцам, вычисленным
    # из номеров работ, — отдельной таблицы соответствия не держим.
    need = {}
    for j in holes:
        rows = np.where(lab == j)[0]
        # Внутри области берём ближайшие к центру: это ещё не ранжирование по
        # интересности, а сужение до пула, который не жалко отдать реранкеру.
        order = rows[np.argsort(-(A[rows] @ C[j]))]
        # ДВА РАЗНЫХ ПРОДУКТА, и различать их надо здесь, а не потом глазами.
        # Полное поле накрывает сорок лет, поэтому без ограничения по дате наверх
        # всплывают КЛАССИКИ: первой целью вышла cond-mat/0509330 — работа Гейма
        # и Новосёлова про графен, за которую дали Нобелевскую премию. Это честная
        # находка (про графен у нас ноль статей), но это заполнение пробела
        # в фундаменте, а не освещение новостей. Ночная лента живёт другим.
        if args.since:
            order = [i for i in order if (fb.id_month(ids[i]) or "0000") >= args.since]
        order = list(order)[:args.pool]
        for i in order:
            mo = fb.id_month(ids[i])
            if mo:
                need.setdefault(mo, {})[fb._base_id(ids[i])] = int(i)
    texts, meta = {}, {}
    for mo, keys in sorted(need.items()):
        p = fb.BULK / f"{mo}.jsonl"
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = fb._base_id(r.get("id", ""))
                if k in keys:
                    i = keys[k]
                    texts[i] = " ".join(f"{r.get('title','')}. {r.get('abstract','')}".split())[:1200]
                    c = r.get("categories")
                    lst = c if isinstance(c, list) else str(c or "").split()
                    meta[i] = {"title": " ".join(str(r.get("title", "")).split()),
                               "cat": str(lst[0]) if lst else "",
                               "id": r.get("id", ""), "date": (r.get("published") or "")[:10]}
    print(f"текстов поднято: {len(texts):,}")

    key = rr.load_env()
    rows_out, stats = [], {}
    for j in holes:
        rows = np.where(lab == j)[0]
        order = rows[np.argsort(-(A[rows] @ C[j]))]
        if args.since:
            order = [i for i in order if (fb.id_month(ids[i]) or "0000") >= args.since]
        order = list(order)[:args.pool]
        cand = [int(i) for i in order if i in texts]
        if not cand:
            continue
        sc = []
        for s in range(0, len(cand), 16):
            sc += rr.rerank(rr.QUERY, [texts[i] for i in cand[s:s + 16]], key,
                            args.model, stats=stats)
        best = sorted(zip(cand, sc), key=lambda x: -x[1])[:args.per_hole]
        rows_out.append({
            "область": R["names"][j],
            "работ_у_мира": R["n_arxiv"][j],
            "у_нас": 0,
            "разделы": R["cats"].get(str(j), [])[:5],
            "лучшая_интересность": round(float(best[0][1]), 4),
            "цели": [{"id": meta[i]["id"], "название": meta[i]["title"],
                      "раздел": meta[i]["cat"], "дата": meta[i]["date"],
                      "интересность": round(float(s), 4)} for i, s in best],
        })
        print(f"  просмотрено {R['names'][j][:46]:<46} лучшее {best[0][1]:.3f}")

    rows_out.sort(key=lambda h: -h["лучшая_интересность"])
    out = rows_out[:args.holes]
    print(f"\n{'='*78}\nПЛАН БУРЕНИЯ — дырки по ДОБЫЧЕ, а не по размеру\n{'='*78}")
    for h in out:
        print(f"\n· {h['область']}  (у мира {h['работ_у_мира']}, у нас 0)")
        for t in h["цели"]:
            print(f"    {t['интересность']:.3f}  {t['id']:<16} {t['название'][:74]}")
    if len(rows_out) > len(out):
        sk = rows_out[len(out):]
        print(f"\nотброшено дырок с бедной добычей: {len(sk)} "
              f"(лучшее от {sk[0]['лучшая_интересность']:.3f} "
              f"до {sk[-1]['лучшая_интересность']:.3f})")

    try:
        from embeddings_build import log_usage
        log_usage("rerank", stats.get("tokens", 0),
                  model=f"qwen3-reranker-{args.model.lower()}")
    except Exception:
        pass
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    n = sum(len(h["цели"]) for h in out)
    print(f"\nплан бурения: {n} работ в {len(out)} слепых зонах → {args.out}")
    print(f"токенов реранкера: {stats.get('tokens', 0):,} "
          f"(${stats.get('tokens', 0)/1e6*0.05:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
