#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Таблица синонимов тегов — склейка на входе сборки аналитики и графа.

Волна 17 августа, пункт 3 раздела ML. Аудит нашёл на странице «реионизация ⟷
реионизация» и «активное ядро · активное ядро»: два разных идентификатора,
показанных читателю одним и тем же словом.

ДВА РАЗНЫХ ЯВЛЕНИЯ, И ЛОВЯТСЯ ОНИ РАЗНЫМ.

  ОДИНАКОВОЕ ИМЯ. Два идентификатора с совпадающей подписью в словаре: `reionization`
  и `cosmic_reionization` оба показываются как «реионизация». Это ловится сравнением
  строк, без всякой геометрии, и это самый надёжный класс: читатель уже видит ошибку.

  РАЗНОЕ ИМЯ, ОДНО ПОНЯТИЕ. `neutrino` и `neutrino_oscillations`, `superposition`
  и `quantum_superposition`. Здесь нужны свидетельства: общий пул статей, косинус
  центроидов (тег представлен средним вектором своих работ) и общие слова в названии.

ГЕОМЕТРИЯ В ТАБЛИЦУ НЕ ПОПАДАЕТ ВООБЩЕ, И ЭТО РЕЗУЛЬТАТ ЗАМЕРА, А НЕ ОСТОРОЖНОСТЬ.
Первая версия пускала пару в склейку, если у названий есть общее слово, а косинус
центроидов выше 0.93. Вот что она предложила слить:

    white_dwarf   → brown_dwarf      белый карлик и коричневый — разные объекты
    red_dwarf     → brown_dwarf      красный карлик тоже
    dwarf_galaxy  → brown_dwarf      карликовая галактика вообще не звезда
    moon          → exomoon          Луна и экзолуна
    game_theory   → probability_theory

Общее слово оказалось модификатором, а не сутью: «карлик» стоит в четырёх разных
понятиях. Косинус при этом честно высокий — работы про карликов действительно рядом
в пространстве. То есть геометрия не ошиблась, она ответила на другой вопрос: «про
близкое ли это», а не «про одно ли это».

Та же ловушка была на прошлой волне у учёных: поиск дублей поднял соавторов — Майор
и Кело, Пензиас и Уилсон, Жаккар до 0.94. Третий случай одного правила: близость
в пространстве не есть тождество, и никакой порог этого не исправит.

Поэтому в склейку идёт только то, что видно без геометрии: одинаковая подпись
в словаре или один и тот же идентификатор, записанный по-разному. Всё остальное
уходит в очередь на разбор человеком и НЕ применяется.

КУДА ВЕДЁТ СТРЕЛКА. К тому идентификатору, у которого больше работ, а при равенстве —
к более короткому. Переименование не трогает данные статей: таблица применяется
на входе сборки, поэтому откат — это удаление строки из таблицы.

    python tag_synonyms.py
    python tag_synonyms.py --apply-to data/tag-synonyms.json
"""
import argparse
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

STOP = {"of", "the", "and", "in", "a"}


def words(s):
    return {w for w in re.split(r"[^a-z0-9]+", s.lower()) if w and w not in STOP}


def same_stem(a, b):
    x, y = a.lower().replace("-", "_"), b.lower().replace("-", "_")
    return x in y or y in x or x.rstrip("s") == y.rstrip("s")


def norm_name(s):
    return re.sub(r"[^0-9a-zа-яё]+", " ", (s or "").lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--out", default=str(MAIN / "data" / "tag-synonyms.json"))
    ap.add_argument("--min-cos", type=float, default=0.93)
    ap.add_argument("--min-jac", type=float, default=0.15)
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb
    from analytics_v2 import load_articles

    names = json.loads((MAIN / f"lang/{args.lang}/data/tags.json")
                       .read_text(encoding="utf-8"))
    art = load_articles(args.lang)
    ids, M = vecstore.load(DATA / "field", mmap=True)
    rowof = {}
    for i, s in enumerate(ids):
        rowof[fb._base_id(s)] = i

    pool = {}
    for aid, r in art.items():
        if aid not in rowof:
            continue
        for t in r["tags"]:
            pool.setdefault(t, set()).add(aid)
    print(f"тегов в словаре {len(names)} · встречаются в статьях {len(pool)}")

    tags = sorted(pool)
    cent = np.zeros((len(tags), M.shape[1]), dtype=np.float32)
    for k, t in enumerate(tags):
        rows = [rowof[a] for a in pool[t]]
        v = np.zeros(M.shape[1], dtype=np.float32)
        for r in rows:
            v += M[r]
        cent[k] = v / (np.linalg.norm(v) + 1e-9)
    kof = {t: k for k, t in enumerate(tags)}

    pairs, seen = [], set()
    by_art = {}
    for t in tags:
        for a in pool[t]:
            by_art.setdefault(a, []).append(t)
    for a, ts in by_art.items():
        if len(ts) > 60:
            continue
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                p = tuple(sorted((ts[i], ts[j])))
                if p in seen:
                    continue
                seen.add(p)
                A, B = pool[p[0]], pool[p[1]]
                inter = len(A & B)
                if inter < 2:
                    continue
                jac = inter / len(A | B)
                cos = float(cent[kof[p[0]]] @ cent[kof[p[1]]])
                wa, wb = words(p[0]), words(p[1])
                nam = len(wa & wb) / max(1, min(len(wa), len(wb)))
                pairs.append((p[0], p[1], jac, cos, nam, inter))

    # Одинаковая подпись — отдельный, самый надёжный класс: читатель уже видит
    # два одинаковых слова рядом, и никаких доказательств больше не требуется.
    byname = {}
    for t in tags:
        n = norm_name((names.get(t) or {}).get("name"))
        if n:
            byname.setdefault(n, []).append(t)
    same_label = [(v[0], v[1], n) for n, v in byname.items() if len(v) > 1]
    print(f"\n{'=' * 78}\nОДИНАКОВАЯ ПОДПИСЬ В СЛОВАРЕ\n{'=' * 78}")
    for a, b, n in same_label:
        print(f"  «{n}»: {a} + {b}  (работ {len(pool.get(a, ()))} / "
              f"{len(pool.get(b, ()))})")
    if not same_label:
        print("  нет")

    strong = [p for p in pairs
              if (same_stem(p[0], p[1]) or p[4] > 0)
              and p[3] >= args.min_cos and p[2] >= args.min_jac]
    strong.sort(key=lambda r: -(r[4] * 2 + r[2] + r[3]))

    table, why = {}, {}
    def add(a, b, reason):
        # Стрелка ведёт к тому, у кого больше работ; при равенстве — к короткому.
        na, nb = len(pool.get(a, ())), len(pool.get(b, ()))
        src, dst = (b, a) if (na, -len(a)) >= (nb, -len(b)) else (a, b)
        if src in table or dst in table:
            return
        table[src] = dst
        why[src] = reason

    def bare(t):
        """Идентификатор без знаков и множественного числа — для сравнения записей."""
        return re.sub(r"[^a-z0-9]", "", t.lower()).rstrip("s")

    for a, b, n in same_label:
        add(a, b, f"одинаковая подпись «{n}»")
    # В склейку идёт ТОЛЬКО то, что видно без геометрии: один и тот же
    # идентификатор, записанный по-разному. Всё остальное — в очередь на разбор.
    for a, b, jac, cos, nam, inter in strong:
        if bare(a) == bare(b):
            add(a, b, "тот же идентификатор в другой записи")
    review = [{"a": a, "b": b, "shared": inter, "jaccard": round(jac, 3),
               "cosine": round(cos, 3)}
              for a, b, jac, cos, nam, inter in strong
              if bare(a) != bare(b) and a not in table and b not in table]

    print(f"\n{'=' * 78}\nТАБЛИЦА СКЛЕЙКИ — {len(table)} пар\n{'=' * 78}")
    for src in sorted(table, key=lambda s: -len(pool.get(table[s], ()))):
        print(f"  {src:<34} → {table[src]:<30} {why[src]}")

    print(f"\n{'=' * 78}")
    print(f"ОЧЕРЕДЬ НА РАЗБОР — {len(review)} пар, НЕ применяются")
    print(f"{'=' * 78}")
    for r in review[:12]:
        print(f"  {r['a']:<34} ~ {r['b']:<30} общих {r['shared']:>3} · "
              f"косинус {r['cosine']:.3f}")
    print("  Здесь геометрия говорит «близко», а не «одно и то же». Среди таких пар")
    print("  белый и коричневый карлик, Луна и экзолуна. Решает человек.")

    out = {"built": "2026-08-17", "n": len(table),
           "note": "map применять на ВХОДЕ сборки аналитики и графа: тег слева "
                   "заменяется тегом справа до подсчёта. Данные статей не меняются, "
                   "откат — удаление строки. review НЕ применять: там близость, "
                   "а не тождество.",
           "map": table, "why": why, "review": review}
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"\n→ {args.out}")
    print(f"  склейка убирает {len(table)} из {len(pool)} живых тегов "
          f"({len(table) / max(1, len(pool)) * 100:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
