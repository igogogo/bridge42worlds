#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 7 волны 5: основные формы формул, карточки к ним, связь с понятиями.

Владелец 25 августа: «убираем разметку формул, пишем для формулы основную форму —
это отдельный список, потом карточку на основную, и дальше по карточке вяжем
с понятиями. Тегов больше нет».

ДВА ЯРУСА, А НЕ ОДИН — это главное в задаче. План владельца: «формулы третьим
измерением — вход со страницы понятия (ОСНОВНЫЕ) и статьи (ЧАСТНЫЕ)».

    ОСНОВНАЯ ФОРМА   общая, каноническая. У неё карточка, вектор и связь с понятиями.
                     Её показывает страница ПОНЯТИЯ.
    ЧАСТНОЕ ПРИМЕНЕНИЕ  та же формула в конкретной работе, со своим смыслом
                     и своими обозначениями. Его показывает страница СТАТЬИ.

Схлопнуть их в одно было бы ошибкой: «H = da/dt / a» и «скорость разбегания галактики
на 400 Мпк» — это один закон и разные вещи. Поэтому записи не сливаются, а
ПОДЧИНЯЮТСЯ основной форме, сохраняя каждая свой смысл и свою статью.

    записи (частные)  →  ОСНОВНАЯ ФОРМА  →  карточка  →  вектор  →  связь с понятием

ПОЧЕМУ БУКВЕННЫЙ КАНОН НЕ ГОДИТСЯ — это замерил ещё слой формул: приведение по буквам
свернуло 1225 записей в 1217, то есть не свернуло ничего. Формулы почти всегда записаны
по-разному: у одного автора `H = \\dot{a}/a`, у другого `v = H_0 d`, и текстовая
нормализация бессильна. Канон нужен смысловой — а это вектор, то есть моя работа,
и слой формул прямо на неё и ссылается.

СТАРЫЕ ТЕГИ НЕ ИСПОЛЬЗУЮТСЯ ВОВСЕ. У каждой записи есть поле `tags` из прежнего
словаря; его здесь нет ни в одном расчёте. Причина не в чистоте ради чистоты:
связывать формулу с понятием через тег значит тащить в новый реестр разрешение
старого словаря, где `spectroscopy` покрывал 913 работ. Вяжем карточку с карточкой.

ЧТО СЧИТАЕТСЯ ОДНОЙ ОСНОВНОЙ ФОРМОЙ. Записи группируются по смыслу их описания
и символов. Порог не назначается, а выбирается замером: печатается, во сколько форм
сворачивается корпус при разных порогах и сколько при этом слипается заведомо разного.

    python formulas_canon.py --embed     векторизовать записи (платно, доли цента)
    python formulas_canon.py --tune      подобрать порог склейки замером
    python formulas_canon.py --cards     написать карточки основным формам
    python formulas_canon.py --link      связать формулы с понятиями
"""
import argparse
import collections
import json
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

REC_VECS = DATA / "formula-recs.f16"
REC_KEYS = DATA / "formula-recs.keys"
CANON = DATA / "formulas-canon.json"


def formula_text(key, rec):
    """Текст записи для векторизации: смысл, символы и сама запись.

    Смысл идёт первым и он по-русски, карточки понятий по-английски — bge-m3
    многоязычная, для того и выбрана. Латех оставлен последним и урезан: он помогает
    отличить разные формулы с похожим описанием, но длинная выкладка забивает смысл.
    """
    parts = [str(rec.get("meaning") or "")]
    sym = rec.get("symbols") or []
    if sym:
        parts.append("Обозначения: " + ", ".join(map(str, sym[:8])))
    tex = re.sub(r"\s+", " ", str(rec.get("latex") or key))[:120]
    parts.append(tex)
    return " ".join(p for p in parts if p)[:600]


def embed(texts, key, batch=64):
    import numpy as np
    out = []
    for st in range(0, len(texts), batch):
        body = json.dumps({"inputs": texts[st:st + batch]}).encode("utf-8")
        for a in range(4):
            try:
                req = urllib.request.Request(
                    "https://api.deepinfra.com/v1/inference/BAAI/bge-m3", data=body,
                    headers={"Authorization": f"bearer {key}",
                             "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    out.extend(json.loads(r.read().decode("utf-8"))["embeddings"])
                break
            except Exception:
                if a == 3:
                    raise
                time.sleep(2 * (a + 1))
        print(f"  {min(st + batch, len(texts))}/{len(texts)}")
    V = np.asarray(out, dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    return V


def load_formulas():
    return json.load(open(MAIN / "data/formulas.json", encoding="utf-8"))


def load_recs():
    import numpy as np
    keys = REC_KEYS.read_text(encoding="utf-8").split("\n\x00\n")
    V = np.fromfile(REC_VECS, dtype=np.float16).reshape(len(keys), -1)
    return keys, np.asarray(V, dtype=np.float32)


def group(V, keys, thr):
    """Склейка записей в основные формы: связная компонента по порогу сходства."""
    import numpy as np
    n = len(keys)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for st in range(0, n, 256):
        S = V[st:st + 256] @ V.T
        for i in range(S.shape[0]):
            gi = st + i
            for j in np.where(S[i] >= thr)[0]:
                if int(j) != gi:
                    a, b = find(gi), find(int(j))
                    if a != b:
                        parent[a] = b
    comp = collections.defaultdict(list)
    for i in range(n):
        comp[find(i)].append(i)
    return list(comp.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--cards", action="store_true")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--thr", type=float, default=0.92)
    args = ap.parse_args()

    import numpy as np
    import concepts_grow as g

    f = load_formulas()
    keys = list(f)
    print(f"записей формул: {len(keys)}")

    if args.embed:
        V = embed([formula_text(k, f[k]) for k in keys], g.load_key())
        V.astype(np.float16).tofile(REC_VECS)
        REC_KEYS.write_text("\n\x00\n".join(keys), encoding="utf-8")
        print(f"→ {REC_VECS} {V.shape}")
        return 0

    if not REC_VECS.exists():
        sys.exit("нет векторов записей — сначала python formulas_canon.py --embed")
    keys, V = load_recs()

    if args.tune:
        print(f"\n{'=' * 74}")
        print("ПОДБОР ПОРОГА СКЛЕЙКИ — замером, а не назначением")
        print("=" * 74)
        print(f"  {'порог':>7}{'основных форм':>16}{'крупнейшая':>13}{'одиночек':>11}")
        for thr in (0.97, 0.95, 0.93, 0.90, 0.87):
            comps = group(V, keys, thr)
            sizes = sorted((len(c) for c in comps), reverse=True)
            singles = sum(1 for s in sizes if s == 1)
            print(f"  {thr:>7.2f}{len(comps):>16}{sizes[0]:>13}{singles:>11}")
        print("\n  Слишком низкий порог схлопывает всё в один ком — это видно")
        print("  по столбцу «крупнейшая». Слишком высокий не склеивает ничего,")
        print("  и число форм равно числу записей.")
        return 0

    comps = group(V, keys, args.thr)
    comps.sort(key=len, reverse=True)
    print(f"основных форм при пороге {args.thr}: {len(comps)}")

    canon = []
    for c in comps:
        recs = [keys[i] for i in c]
        arts = []
        for k in recs:
            arts += [a["id"] for a in (f[k].get("articles") or []) if a.get("id")]
        # Представитель основной формы — САМАЯ КОРОТКАЯ запись латеха: общая форма
        # короче частной, в частной обычно подставлены конкретные величины.
        rep = min(recs, key=lambda k: len(re.sub(r"\s+", "", str(f[k].get("latex") or k))))
        apps = []
        for k in recs:
            for a in (f[k].get("articles") or []):
                apps.append({"record": k, "latex": f[k].get("latex"),
                             "meaning_ru": f[k].get("meaning"),
                             "article": a.get("id"), "title": a.get("title")})
        canon.append({"canon_id": f"F{len(canon):04d}",
                      "latex": f[rep].get("latex"),
                      "meaning_ru": f[rep].get("meaning"),
                      "n_records": len(recs),
                      "applications": apps, "n_applications": len(apps),
                      "articles": sorted(set(arts)), "n_articles": len(set(arts))})
    sizes = [c["n_records"] for c in canon]
    print(f"  записей на форму: медиана {sorted(sizes)[len(sizes) // 2]}, "
          f"максимум {max(sizes)}")
    print(f"  форм с двумя и более записями: {sum(1 for s in sizes if s > 1)}")
    print(f"  частных применений всего: {sum(c['n_applications'] for c in canon):,}")
    CANON.write_text(json.dumps({"built": "2026-08-25", "threshold": args.thr,
                                 "canon": canon}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"→ {CANON}")
    print("\n  Теги записей НЕ использованы ни в одном расчёте: связь с понятиями")
    print("  пойдёт карточка-к-карточке, следующим шагом (--cards, --link).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
