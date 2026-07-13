#!/usr/bin/env python3
"""Bulk-отбор статей за диапазон месяцев из локального arXiv-кэша (data/arxiv-bulk/) —
вместо «сегодня, лучшее из ~200» смотрим на пул за годы и режем каскадом в 2 прохода
(грубо → тонко, по ~10%/~20% на батч), затем 3-й проход — ранжирование (не отсев) уже
отобранного пула, и аудит лицензий перед генерацией (лицензию НЕ смотрим во время отбора —
только после, чтобы не искажать «интересность» и чтобы посчитать, что реально потеряли).

Кандидаты не трогают live arXiv API вообще (кроме финальной проверки лицензии по каждой
статье) — обходит rate-limit и быстро по времени. Результат — структурированный JSON в
data/bulk-select/<run_id>.json, который потом читает run.py bulk-generate батчами."""

import json
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from gen_arxiv import _category_pattern, _matches_category, _author_name, get_license, is_allowed_license
from gen_llm import select_best_n, rank_articles

BULK_DIR = Path("data/arxiv-bulk")
OUT_DIR = Path("data/bulk-select")
BATCH_SIZE = 200


def _months_back(n, end=None):
    """Список 'YYYY-MM' за последние n месяцев, заканчивая текущим."""
    end = end or datetime.now()
    y, m = end.year, end.month
    months = []
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(months))


def _existing_base_ids():
    import generate
    return generate.load_generation_inputs().get("existing_base_ids", set())


def gather_candidates(categories, months_back, exclude_ids=frozenset()):
    patterns = [_category_pattern(c) for c in categories]
    months = _months_back(months_back)
    candidates, seen = [], set()
    for mkey in months:
        chunk = BULK_DIR / f"{mkey}.jsonl"
        if not chunk.exists():
            print(f"  ⚠️ нет локального чанка за {mkey} — пропускаю")
            continue
        with chunk.open("r", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                aid = d["id"]
                if aid in seen or aid in exclude_ids:
                    continue
                cats = d.get("categories") or []
                if not any(_matches_category(cats, p) for p in patterns):
                    continue
                seen.add(aid)
                candidates.append({
                    "id": aid,
                    "title": d.get("title", ""),
                    "summary": d.get("abstract", ""),
                    "authors": [_author_name(a) for a in d.get("authors_parsed") or []],
                    "published": d.get("published", ""),
                    "categories": cats,
                    "primary_category": cats[0] if cats else "",
                })
    return candidates


def _batched(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def cascade_round(articles, percent, tag_prefix, batch_size=BATCH_SIZE, max_workers=12):
    """Режет articles на батчи по batch_size, на каждый вызывает select_best_n
    (count = round(batch*percent/100)), сшивает результаты. Батчи независимы — параллелим."""
    batches = list(_batched(articles, batch_size))
    print(f"  📦 {tag_prefix}: {len(articles)} статей → {len(batches)} батчей по ≤{batch_size}, "
          f"{percent}% на батч")

    def _one(i_batch):
        i, batch = i_batch
        count = max(1, round(len(batch) * percent / 100))
        return select_best_n(batch, count, tag=f"{tag_prefix}-{i}")

    survivors = []
    done = 0
    step = max(1, len(batches) // 10)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for res in ex.map(_one, enumerate(batches)):
            survivors.extend(res)
            done += 1
            if done % step == 0 or done == len(batches):
                print(f"    … {tag_prefix}: {done}/{len(batches)} батчей")
    print(f"  ✅ {tag_prefix}: выжило {len(survivors)}")
    return survivors


def rank_round(articles, tag_prefix, batch_size=100, max_workers=12):
    batches = list(_batched(articles, batch_size))
    print(f"  🏅 Ранжирование: {len(articles)} статей → {len(batches)} батчей по ≤{batch_size}")

    def _one(i_batch):
        i, batch = i_batch
        return rank_articles(batch, tag=f"{tag_prefix}-rank-{i}")

    scores, done = {}, 0
    step = max(1, len(batches) // 10)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for res in ex.map(_one, enumerate(batches)):
            scores.update(res)
            done += 1
            if done % step == 0 or done == len(batches):
                print(f"    … ранжирование: {done}/{len(batches)} батчей")
    return scores


def license_audit(articles, max_workers=8):
    """Проверяет лицензию по каждой статье (та же логика, что build_article использует перед
    генерацией) ДО генерации — чтобы посчитать статистику, сколько «интересного» реально
    потеряется, и не разбавлять батчи-по-100 молча отсеявшимися."""
    print(f"  ⚖️ Проверка лицензий: {len(articles)} статей...")

    def _check(a):
        oai_xml = get_license(a["id"])
        allowed, lic_url = is_allowed_license(oai_xml)
        return a["id"], allowed, lic_url

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for aid, allowed, lic_url in ex.map(_check, articles):
            results[aid] = {"allowed": allowed, "license": lic_url}
    allowed_n = sum(1 for r in results.values() if r["allowed"])
    print(f"  ✅ Лицензия ok: {allowed_n}/{len(articles)}, отсеяно: {len(articles) - allowed_n}")
    return results


def run(categories, months_back, round1_percent=10, round2_percent=20, target_count=None):
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"🚀 bulk-select {run_id}: категории={categories}, months_back={months_back}")

    exclude_ids = _existing_base_ids()
    pool = gather_candidates(categories, months_back, exclude_ids)
    print(f"  📊 Пул кандидатов (без уже сгенерированных): {len(pool)}")
    if not pool:
        print("  ❌ пустой пул — нечего отбирать")
        return None

    round1 = cascade_round(pool, round1_percent, f"{run_id}-r1")
    round2 = cascade_round(round1, round2_percent, f"{run_id}-r2") if round1 else []

    scores = rank_round(round2, run_id) if round2 else {}
    ranked = sorted(round2, key=lambda a: -scores.get(a["id"], 5))

    if target_count:
        ranked = ranked[:target_count]

    license_results = license_audit(ranked) if ranked else {}
    ready = [a for a in ranked if license_results.get(a["id"], {}).get("allowed")]
    rejected = [a for a in ranked if not license_results.get(a["id"], {}).get("allowed")]

    out = {
        "run_id": run_id,
        "created": datetime.now().isoformat(timespec="seconds"),
        "categories": categories,
        "months_back": months_back,
        "pool_size": len(pool),
        "round1_size": len(round1),
        "round2_size": len(round2),
        "license_stats": {"checked": len(ranked), "allowed": len(ready), "rejected": len(rejected)},
        "ready": [{**a, "score": scores.get(a["id"], 5)} for a in ready],
        "rejected_by_license": [
            {"id": a["id"], "title": a["title"], "license": license_results.get(a["id"], {}).get("license")}
            for a in rejected
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{run_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Готово: {len(ready)} готовы к генерации (из {len(ranked)} ранжированных, "
          f"{len(round1)} после раунда 1, {len(pool)} в исходном пуле). Сохранено: {out_path}")
    return out_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Bulk-отбор статей за N месяцев из локального arXiv-кэша")
    ap.add_argument("--categories", nargs="+", required=True, help="напр. astro-ph.* nucl-ex nucl-th quant-ph gr-qc")
    ap.add_argument("--months-back", type=int, default=12)
    ap.add_argument("--round1-percent", type=float, default=10)
    ap.add_argument("--round2-percent", type=float, default=20)
    ap.add_argument("--target-count", type=int, default=None)
    args = ap.parse_args()
    run(args.categories, args.months_back, args.round1_percent, args.round2_percent, args.target_count)
