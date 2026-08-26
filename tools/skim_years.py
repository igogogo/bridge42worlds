#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снять сливки за годы: глобальный отбор по всему полю, а не по дню.

Владелец 2026-08-24: «надо всё вектором, чтобы не наобум искать; и 2025 год брать тоже,
снять сливки».

ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ ТОГО, ЧТО БЫЛО. Дневной отбор (gen_llm.select_best) уже идёт через
вектор: предфильтр режет два края, реранкер режет по интересности, модель ранжирует
середину. Но соревнование там ВНУТРИ ОДНОГО ДНЯ: посредственная работа в пустой день
проходит, отличная в плотный — нет. Ночная накачка (tools/overnight.py) выбирает ДЕНЬ
вслепую — «где статей меньше нормы», — и внутри снова упирается в тот же дневной пул.
Поэтому «сливок за год» не получалось ни разу: их некому было снимать.

Здесь пул общий на все годы сразу, и три сита стоят по порядку дешевизны:
  1. ЛИЦЕНЗИЯ и ПОВТОР — бесплатно, по нашей базе (sqlite лицензий + наш архив).
  2. ВЕКТОРНАЯ ПОЛОСА — бесплатно, по НАШЕМУ полю на диске (2,96 млн векторов):
     вычёркиваем «такое у нас уже есть» (слишком близко к корпусу) и «не наш профиль»
     (слишком далеко). Ровно логика vector_select.prefilter, но по всему пулу разом
     и без единого обращения к API: вектор кандидата уже посчитан и лежит рядом.
  3. РЕРАНКЕР — кросс-энкодер, единственный из трёх, кто умеет ранжировать по
     интересности (см. замеры в vector_select.rerank_cut). Стоит копейки и работает
     только по выжившим после первых двух сит.

ПОЧЕМУ ВЕКТОР НЕ РАНЖИРУЕТ САМ. Проверено и записано в vector_select: ранжирование по
близости к корпусу даёт шорт-лист, где 45% cs/math при 4% астрофизики — наши профильные
темы близки к корпусу, и «полнота» у них низкая. Вектор умеет вычёркивать, но не
выбирать. Здесь он и вычёркивает.

    python tools/skim_years.py --years 2025,2026 --take 200 --dry
    python tools/skim_years.py --years 2025 --take 300
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BULK = ROOT / "data" / "arxiv-bulk"
OUT_DIR = ROOT / "data" / "skim"
FIELD_DIR = ROOT.parent / "b42-ml" / "data"
FIELD_VEC = FIELD_DIR / "field.f16"
FIELD_IDS = FIELD_DIR / "field.ids"
DIM = 1024

# Периметр — тот же, что у фабрики: расхождение списков означало бы, что «сливки»
# собираются не из того корпуса, который мы ведём.
CATEGORIES = ("astro-ph", "gr-qc", "hep-th", "hep-ph", "hep-ex", "nucl-th", "nucl-ex",
              "quant-ph", "cond-mat", "physics", "q-bio", "math-ph")


def our_ids():
    """Что уже разобрано — по базовым id, без версии."""
    out = set()
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        out.add(re.sub(r"v\d+$", "", p.parent.name))
    return out


def in_perimeter(cats):
    for c in cats or []:
        head = str(c).split(".")[0]
        if head in CATEGORIES:
            return True
    return False


def pool(years, have):
    """Кандидаты нужных лет из локального дампа: в периметре, ещё не наши."""
    from gen_arxiv import license_class
    rows = []
    seen_lic = Counter()
    for f in sorted(BULK.glob("*.jsonl")):
        if f.stem[:4] not in years:
            continue
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                aid = d.get("id", "")
                if not aid or aid in have:
                    continue
                if not in_perimeter(d.get("categories")):
                    continue
                rows.append({"id": aid, "title": d.get("title", ""),
                             "summary": d.get("abstract", ""),
                             "cats": d.get("categories") or [],
                             "published": d.get("published", "")})
    # Лицензия — отдельным проходом по нашей базе: один запрос на кандидата, но
    # sqlite отвечает за микросекунды и в сеть не ходит.
    from gen_arxiv import local_license
    kept = []
    for r in rows:
        cls = license_class(local_license(r["id"]) or "")
        seen_lic[cls] += 1
        if cls != "no":
            kept.append(r)
    print(f"  пул: {len(rows)} кандидатов в периметре · после лицензий {len(kept)}"
          f" ({dict(seen_lic)})")
    return kept


def field_index():
    """id → номер строки в поле. 46 МБ текста, читается один раз."""
    idx = {}
    with FIELD_IDS.open(encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            s = line.strip()
            if s.startswith("arx:"):
                s = s[4:]
            idx[s] = i
    return idx


def band_cut(cands, have, low=0.20, high=0.95, keep_max=8000):
    """Векторная полоса по нашему полю: вычёркиваем оба края. Ни одного вызова API.

    Границы — перцентили ПО ПУЛУ, как в дневном предфильтре, а не абсолютные числа:
    близость зависит от того, из каких разделов набрался пул, и фиксированный порог
    в разные годы означал бы разное.
    """
    import numpy as np
    idx = field_index()
    n_rows = FIELD_VEC.stat().st_size // (DIM * 2)
    vecs = np.memmap(FIELD_VEC, dtype=np.float16, mode="r", shape=(n_rows, DIM))

    # Центроид корпуса — по нашим же статьям, найденным в поле.
    ours = [idx[a] for a in have if a in idx]
    if len(ours) < 50:
        print(f"  ⚠️ наших статей в поле всего {len(ours)} — полосу не считаю")
        return cands
    c = np.asarray(vecs[sorted(ours)], dtype=np.float32).mean(axis=0)
    c /= (np.linalg.norm(c) or 1.0)

    rows, keep = [], []
    for r in cands:
        i = idx.get(r["id"])
        if i is not None:
            rows.append(i)
            keep.append(r)
    if not rows:
        print("  ⚠️ ни один кандидат не найден в поле — полосу пропускаю")
        return cands
    order = np.argsort(rows)
    m = np.asarray(vecs[[rows[i] for i in order]], dtype=np.float32)
    m /= (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
    sim = m @ c
    lo, hi = np.percentile(sim, low * 100), np.percentile(sim, high * 100)
    out = [keep[order[i]] for i in range(len(order)) if lo <= sim[i] <= hi]
    print(f"  🧭 полоса: {len(cands)} → {len(out)} "
          f"(в поле нашлось {len(keep)}, близость {lo:.3f}…{hi:.3f})")
    return by_month_cap(out, keep_max)


def by_month_cap(rows, keep_max):
    """Урезание пула РОВНО по месяцам, а не по порядку файлов.

    Первый прогон вскрыл это сразу: пул 2025 года — 94 913 работ, потолок 8000 срезал
    хвост в том порядке, в каком лежат чанки, то есть хронологически, и «сливки года»
    оказались сливками января-февраля. Все двадцать находок были из первых двух месяцев.
    Реранкер честно ранжировал то, что ему дали, — дефект был на этаже ниже.
    """
    if len(rows) <= keep_max:
        return rows
    buckets = {}
    for r in rows:
        buckets.setdefault((r.get("published") or "")[:7], []).append(r)
    per = max(1, keep_max // max(1, len(buckets)))
    out = []
    for m in sorted(buckets):
        out += buckets[m][:per]
    print(f"  📆 равномерно по месяцам: {len(buckets)} мес. × {per} = {len(out)}")
    return out


def rank(cands, take):
    """Ранжирование по интересности — реранкером, единственным, кто это умеет."""
    try:
        import rerank_eval as rr
        key = rr.load_env()
    except Exception as e:
        print(f"  ⚠️ реранкер недоступен ({type(e).__name__}) — беру первых по порядку")
        return cands[:take]
    docs = [f"{c.get('title','')}. {str(c.get('summary',''))[:900]}" for c in cands]
    sc, stats = [], {}
    for i in range(0, len(docs), 16):
        sc += rr.rerank(rr.QUERY, docs[i:i + 16], key, "8B", stats=stats)
        if i and i % 1600 == 0:
            print(f"    реранкер: {i}/{len(docs)}")
    try:
        from embeddings_build import log_usage
        log_usage("rerank", stats.get("tokens", 0), model="qwen3-reranker-8b")
    except Exception:
        pass
    order = sorted(range(len(cands)), key=lambda i: -sc[i])[:take]
    return [cands[i] for i in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025,2026")
    ap.add_argument("--take", type=int, default=200)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    years = set(y.strip() for y in args.years.split(","))
    have = our_ids()
    print(f"наших статей: {len(have)} · годы: {sorted(years)}")

    cands = pool(years, have)
    if not cands:
        print("кандидатов нет")
        return 1
    cands = band_cut(cands, have)
    top = rank(cands, args.take)

    by_year = Counter(c["published"][:4] for c in top)
    by_cat = Counter(str(c["cats"][0]).split(".")[0] for c in top if c.get("cats"))
    print(f"\nсливки: {len(top)} работ · по годам {dict(by_year)}")
    print(f"по разделам: {dict(by_cat.most_common(8))}")
    for c in top[:10]:
        print(f"  {c['published']} {c['id']:14s} {c['title'][:70]}")

    if args.dry:
        print("\n(сухой прогон — очередь не записана)")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = "-".join(sorted(years))
    f = OUT_DIR / f"skim-{stamp}.txt"
    f.write_text("\n".join(c["id"] for c in top) + "\n", encoding="utf-8")
    print(f"\n✅ очередь: {f.relative_to(ROOT)}")
    print(f"   дальше: python run.py ids --ids-file {f.relative_to(ROOT)} --express")
    return 0


if __name__ == "__main__":
    sys.exit(main())
