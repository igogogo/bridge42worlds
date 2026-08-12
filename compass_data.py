#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Данные для дообучения компаса: пары «связано по делу, но далеко по вектору».

Владелец 11 августа: «завтра перейдём же к тренировке модели, начнём во всяком случае».

ЧТО ИМЕННО МЫ УЧИМ. Не «понимать физику» — этому энкодер не научить на наших объёмах.
Учим ровно одному: видеть связь там, где заводская модель её не видит. Замер на текущем
поле (876 тыс. работ, 2026-08-11):

    связанных пар:                             2 102
    из них модель считает далёкими (кос.<0,65)  78,1%
    медиана косинуса у связанной пары           0,586
    медиана у случайной пары                    0,451
    ЗАЗОР — предмет обучения                   +0,135

Зазор есть, но он мал: модель что-то видит, но недостаточно. Обучение должно его
раздвинуть, и это измеримо до и после одной и той же командой.

ОТКУДА ПОЛОЖИТЕЛЬНЫЕ ПАРЫ (числа — из файла, не из памяти):

  1. ПРЯМАЯ ССЫЛКА — 232 пары. Связь установлена автором, не нами; самая надёжная.
  2. БИБЛИОГРАФИЧЕСКОЕ СОПРЯЖЕНИЕ — 1 870 пар при пороге в три общие ссылки.
     Две общие ссылки — это чаще «оба цитируют один обзор», а не родство.

Ко-цитирования здесь нет: для него нужно знать, кто ссылается на НАШИ работы,
а этого в разобранных нами PDF нет по устройству — мы читали свои списки литературы,
а не чужие. Появится с Semantic Scholar.

ЧЕГО НЕ ДЕЛАЕМ. Не берём транзитивное замыкание («A→B, B→C, значит A~C»): на
цитированиях оно за два шага соединяет всё со всем. Не берём пары «одинаковый тег» —
это учит модель нашей же разметке, то есть самой себе.

ОТРИЦАТЕЛЬНЫЕ ПРИМЕРЫ важнее положительных. Случайная пара — слишком лёгкая задача:
астрофизику от биологии модель отличит и без нас. Нужны ТРУДНЫЕ отрицательные —
работы, близкие по вектору и НЕ связанные по делу. Майним по полю: ближайшие соседи
минус все связанные. Остальное — честные «похоже, но мимо».

⚠️ РАЗДЕЛЕНИЕ ПО ВРЕМЕНИ У НАС ПОКА НЕ РАБОТАЕТ, и это надо знать до обучения.
Правильный способ проверки — учить на «до даты», проверять на «после». Но наш корпус
почти весь свежий: 1 672 пары из 2 102 — 2026 год, 428 — 2025, и ровно 2 пары старше.
При отсечке 2025-01 в обучении остаётся 2 пары. Отсечка внутри 2026 года даёт хоть
какое-то разделение (2026-05: около 1 200 на обучение), но «прошлое» и «будущее»
там отстоят друг от друга на месяцы, и утечка через общий контекст велика.
Честный вывод: **первые опыты меряем на нашей мерке из 800 вопросов, а
ретроспективную проверку откладываем до корпуса с настоящей глубиной по времени.**
Выдавать разделение по трём месяцам за проверку временем было бы обманом.

    python compass_data.py --check                 сколько чего есть, ничего не писать
    python compass_data.py --cutoff 2026-05 --out data/compass-pairs.jsonl
"""
import argparse
import collections
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))


def load_pairs(min_shared=3):
    """Связанные пары из `data/citations.json`. Структура файла ПРОЧИТАНА, а не угадана.

    Первая версия этой функции разбирала выдуманный формат {источник: [ссылки]}
    и выдала 500 «рёбер» из мусора, ни одно из которых не нашлось в поле. Настоящий
    файл устроен иначе, и в нём уже посчитано то, что я собирался считать заново:

        internal — 235 прямых ссылок между нашими статьями: {"from": ..., "to": ...}
        coupled  — 2817 пар библиографического сопряжения: {"a":..,"b":..,"shared":N}
        wanted   — 500 внешних работ, на которые мы часто ссылаемся (не пары)
        _fixed   — служебная запись citations_fix.py о нормализации

    Урок для протокола: прежде чем писать разбор чужого файла, открой его.
    Час, потраченный на догадку о формате, — это час, потраченный зря.

    ПОРОГ ОБЩИХ ССЫЛОК. `shared` доходит до 66, но пары с двумя общими ссылками —
    это чаще всего «оба цитируют один обзор», а не родство. Берём от трёх.
    Пары вида (X, Xv1) — одна и та же работа с версией и без — отбрасываем:
    в файле они встречаются (наибольшие `shared` в сыром виде были именно такими),
    и учить на них модель значит учить её тому, что она и так знает.
    """
    p = DATA / "citations.json"
    if not p.exists():
        p = MAIN / "data" / "citations.json"
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    import field_build as fb
    out = {}
    for r in raw.get("coupled", []):
        a, b = fb._base_id(r.get("a", "")), fb._base_id(r.get("b", ""))
        n = int(r.get("shared", 0))
        if a and b and a != b and n >= min_shared:
            out[tuple(sorted((a, b)))] = ("coupling", n)
    for r in raw.get("internal", []):
        a, b = fb._base_id(r.get("from", "")), fb._base_id(r.get("to", ""))
        if a and b and a != b:
            out[tuple(sorted((a, b)))] = ("direct", 1)   # прямая ссылка сильнее
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--cutoff", default="2025-01",
                    help="месяц отсечки: пары до него — обучение, после — проверка")
    ap.add_argument("--min-shared", type=int, default=3,
                    help="сколько общих ссылок считать родством, а не общей модой")
    ap.add_argument("--negatives", type=int, default=8,
                    help="сколько трудных отрицательных на одну положительную пару")
    ap.add_argument("--out", default="data/compass-pairs.jsonl")
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb

    allpairs = load_pairs(args.min_shared)
    if not allpairs:
        sys.exit("нет данных о связях — нечего строить")
    kinds = collections.Counter(v[0] for v in allpairs.values())
    print(f"прямых ссылок: {kinds['direct']:,} · "
          f"сопряжений (≥{args.min_shared} общих): {kinds['coupling']:,}")
    print(f"ВСЕГО положительных пар: {len(allpairs):,}")

    ids, M = vecstore.load(DATA / "field", latest=True)
    pos = {fb._base_id(i): k for k, i in enumerate(ids)}
    have = [p for p in allpairs if p[0] in pos and p[1] in pos]
    print(f"из них обе работы есть в поле: {len(have):,} "
          f"({len(have)*100//max(len(allpairs),1)}%)")
    if not have:
        sys.exit("ни одна пара не покрыта полем — сначала достройте поле")

    A = np.asarray(M, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    sims = np.array([float(A[pos[a]] @ A[pos[b]]) for a, b in have])
    blind = float((sims < 0.65).mean())
    print(f"\nКЛЮЧЕВОЕ ЧИСЛО: {blind*100:.1f}% связанных пар модель считает далёкими "
          f"(косинус < 0,65)")
    print(f"   медиана косинуса у связанных пар: {np.median(sims):.3f}")
    rng = np.random.default_rng(42)
    ra = rng.integers(0, len(A), 20000)
    rb = rng.integers(0, len(A), 20000)
    rs = np.sum(A[ra] * A[rb], axis=1)
    print(f"   для сравнения, случайная пара:    {np.median(rs):.3f}")
    print(f"   ЗАЗОР, который и есть предмет обучения: "
          f"{np.median(sims) - np.median(rs):+.3f}")

    if args.check:
        train = [p for p in have if (fb.id_month(p[0]) or "9999") < args.cutoff]
        print(f"\nразделение по времени (отсечка {args.cutoff}):")
        print(f"   обучение: {len(train):,} пар · проверка: {len(have)-len(train):,}")
        return 0

    # Трудные отрицательные: близкие по вектору, но не связанные ни одним способом.
    linked = collections.defaultdict(set)
    for a, b in allpairs:
        linked[a].add(b)
        linked[b].add(a)
    out, n_neg = [], 0
    for a, b in have:
        ia, ib = pos[a], pos[b]
        sim = A @ A[ia]
        sim[ia] = -2
        cand = np.argsort(-sim)[:args.negatives * 6]
        negs = []
        for j in cand:
            k = fb._base_id(ids[j])
            if k == a or k == b or k in linked[a]:
                continue
            negs.append(k)
            if len(negs) >= args.negatives:
                break
        n_neg += len(negs)
        out.append({"anchor": a, "positive": b,
                    "negatives": negs,
                    "kind": allpairs[(a, b)][0], "weight": allpairs[(a, b)][1],
                    "split": "train" if (fb.id_month(a) or "9999") < args.cutoff else "test"})
    p = pathlib.Path(args.out)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n",
                 encoding="utf-8")
    tr = sum(1 for r in out if r["split"] == "train")
    print(f"\nзаписано: {len(out):,} троек (якорь + положительный + {args.negatives} "
          f"трудных отрицательных)")
    print(f"   обучение {tr:,} · проверка {len(out)-tr:,} · отрицательных всего {n_neg:,}")
    print(f"   → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
