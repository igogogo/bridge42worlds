#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поле → формат приёмника ведущей (`tools/field.py`).

Ведущая 12 августа: «формат намеренно простейший — читается memmap'ом, из зависимостей
только numpy… если вам удобнее другой формат, скажите СЕЙЧАС».

Формат её, а не мой, и это правильный выбор: `.npy` несёт в себе форму и тип данных,
а мой рабочий `data/field.f16` — сырые байты, для чтения которых надо знать размерность
снаружи. Самоописывающийся файл переживёт нас обоих; сырой — первую же смену модели.

    data/field-vectors.npy   float16 (N, 1024), нормированы
    data/field-ids.txt       N строк, arXiv id в том же порядке
    data/field-meta.json     модель, размерность, количество, дата

ЧТО ВАЖНО ЗНАТЬ ПРИ ЧТЕНИИ ЭТИХ ФАЙЛОВ:

1. ДУБЛИКАТЫ. Рабочее хранилище только дописывается: обновление вектора работы — это
   новая строка с тем же id в хвосте, побеждает последняя. Для приёмника это лишнее
   и опасное (две строки с одним id дадут двойной вес при поиске), поэтому на экспорте
   остаётся ровно по одной строке на работу — последняя по времени записи.

2. ОБЪЁМ. В поле физика и смежное естествознание, 1991–2026: 1,56 млн работ, не 3,13.
   Разница — cs и math, 44,5% корпуса arXiv, исключённые решением владельца.
   Это записано в мете, чтобы никто не считал охват полным.

3. НОРМИРОВКА. Векторы единичной длины, поэтому косинус — это скалярное произведение
   без деления. Проверяется на выходе, а не обещается.

    python field_export.py                 выгрузить целиком
    python field_export.py --check         проверить уже выгруженное
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

VEC = DATA / "field-vectors.npy"
IDS = DATA / "field-ids.txt"
META = DATA / "field-meta.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--src", default="data/field")
    ap.add_argument("--date", default="2026-08-12")
    args = ap.parse_args()
    import numpy as np

    if args.check:
        if not VEC.exists():
            sys.exit("выгрузки нет")
        M = np.load(VEC, mmap_mode="r")
        ids = IDS.read_text(encoding="utf-8").splitlines()
        meta = json.loads(META.read_text(encoding="utf-8"))
        print(f"матрица: {M.shape} {M.dtype} · {VEC.stat().st_size/1e9:.2f} ГБ")
        print(f"идентификаторов: {len(ids):,} · дубликатов: {len(ids)-len(set(ids)):,}")
        print(f"мета: {json.dumps(meta, ensure_ascii=False)}")
        ok = len(ids) == M.shape[0] == meta["count"]
        print(f"длины сходятся: {ok}")
        rng = np.random.default_rng(0)
        s = rng.choice(M.shape[0], 2000, replace=False)
        n = np.linalg.norm(np.asarray(M[np.sort(s)], dtype=np.float32), axis=1)
        print(f"длина векторов на выборке: min {n.min():.4f} max {n.max():.4f} "
              f"(должна быть 1)")
        return 0 if ok and abs(n.mean() - 1) < 0.01 else 1

    import vecstore
    ids, M = vecstore.load(args.src, latest=True)
    print(f"в рабочем хранилище: {len(ids):,} строк после схлопывания дубликатов")

    short = [i.split(":", 1)[-1] for i in ids]
    dup = len(short) - len(set(short))
    if dup:
        # Подстраховка: latest=True снимает повторы по ПОЛНОМУ ключу, а приёмник
        # ищет по короткому. Если в поле лежат `arx:2607.1` и `2607.1`, для него
        # это один id в двух строках — и вес такой работы удвоится.
        seen, keep = set(), []
        for k in range(len(short) - 1, -1, -1):
            if short[k] not in seen:
                seen.add(short[k])
                keep.append(k)
        keep = sorted(keep)
        short = [short[k] for k in keep]
        M = M[keep]
        print(f"  снято повторов по короткому идентификатору: {dup:,}")

    A = np.asarray(M, dtype=np.float32)
    n = np.linalg.norm(A, axis=1, keepdims=True)
    bad = int((np.abs(n - 1) > 0.01).sum())
    if bad:
        print(f"  ненормированных строк: {bad:,} — нормирую")
        A /= n + 1e-9
    np.save(VEC, A.astype(np.float16))
    IDS.write_text("\n".join(short) + "\n", encoding="utf-8")
    META.write_text(json.dumps({
        "model": "bge-m3", "dim": int(A.shape[1]), "count": int(A.shape[0]),
        "built": args.date, "normalized": True,
        "scope": "физика и смежное естествознание arXiv, 1991-2026; "
                 "cs и math исключены решением владельца (44,5% корпуса)",
        "source_text": "заголовок + аннотация arXiv, обрезка 2400 знаков",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nвыгружено: {A.shape[0]:,} × {A.shape[1]} → {VEC.name} "
          f"({VEC.stat().st_size/1e9:.2f} ГБ)")
    print(f"           {IDS.name} · {META.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
