#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка поля по СОДЕРЖИМОМУ, а не по длине файлов.

Зачем отдельно от vecstore.repair(). Тот сверяет длины .f16 и .ids и отрезает хвост —
этого хватает при обрыве посреди записи. Но есть отказ пострашнее: два процесса пишут
в один файл одновременно. Тогда длины сойдутся, а вектор окажется склеен с ЧУЖИМ
номером — и такой файл выглядит здоровым, пока однажды не выдаст дикие ответы.

Случилось 11 августа: остановленный прогон по годам оставил живым шелл, тот запускал
новые процессы, и они писали в поле одновременно с проверочным запуском. Длины сошлись.
Правда выяснилась только пересчётом.

Как проверяем: берём случайные работы из поля, заново считаем их вектор у поставщика
и сравниваем с тем, что лежит. У честной пары косинус около 0,9999 (расхождение —
только округление до float16). У склеенной пары будет 0,4-0,7, то есть промах видно
сразу и без порогов на глаз.

    python field_verify.py                 200 случайных работ по всему полю
    python field_verify.py --from 155000   с подозрительного места
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--from", dest="start", type=int, default=0,
                    help="проверять только строки начиная с этой")
    ap.add_argument("--field", default="data/field")
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb
    from embeddings_build import embed_di, load_env

    ids, M = vecstore.load(args.field)
    print(f"в поле {len(ids):,} работ")
    rng = np.random.default_rng(42)
    pool = np.arange(args.start, len(ids))
    pick = rng.choice(pool, min(args.n, len(pool)), replace=False)

    # Тексты берём тем же способом, что и при построении, — иначе сравним не то.
    need = {}
    for i in pick:
        short = fb._base_id(ids[i])
        mo = fb.id_month(short)
        if mo:
            need.setdefault(mo, {})[short] = int(i)
    texts = {}
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
                if fb._base_id(r.get("id", "")) in keys:
                    t = " ".join(f"{r.get('title','')}. {r.get('abstract','')}".split())
                    texts[keys[fb._base_id(r["id"])]] = t[:fb.MAX_CHARS]

    if not texts:
        sys.exit("не нашёл текстов — проверять нечего")
    key = load_env(fb.MAIN)["DEEPINFRA_API_KEY"]
    rows = sorted(texts)
    bad = []
    sims = []
    for s in range(0, len(rows), 32):
        chunk = rows[s:s + 32]
        vecs = embed_di([texts[i] for i in chunk], key)
        for i, v in zip(chunk, vecs):
            a = np.asarray(v, dtype=np.float32)
            a /= np.linalg.norm(a) + 1e-9
            b = np.asarray(M[i], dtype=np.float32)
            b /= np.linalg.norm(b) + 1e-9
            c = float(a @ b)
            sims.append(c)
            if c < 0.99:
                bad.append((i, ids[i], c))
    sims = np.array(sims)
    print(f"\nпроверено {len(sims)} работ")
    print(f"косинус со своим вектором: минимум {sims.min():.4f} · "
          f"медиана {np.median(sims):.4f}")
    if bad:
        print(f"\n❌ РАСХОЖДЕНИЙ: {len(bad)} — поле повреждено, вектор не от своей работы")
        for i, a, c in bad[:10]:
            print(f"   строка {i}: {a} косинус {c:.3f}")
        return 1
    print("\n✅ каждый вектор соответствует своей работе")
    return 0


if __name__ == "__main__":
    sys.exit(main())
