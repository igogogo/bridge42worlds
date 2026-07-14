#!/usr/bin/env python3
"""Целевой отбор ~N статей с авторами из арабских стран (best-effort, эвристика по именам —
НЕ подтверждённая национальность/аффилиация, честно предупреждаем об этом в промте).

Ищет по ШИРОКОМУ кругу физических разделов arXiv (не только наш обычный фокус astro-ph/nucl/
quant-ph/gr-qc — юзер явно просил «в любых разделах»), из локального кэша (без live API).
Сканирует батчами ПОСЛЕДОВАТЕЛЬНО с жёстким потолком батчей — чтобы не улететь в бюджет,
если реальный хитрейт окажется низким.

Запуск:
    python arab_authors_select.py --target 100 --max-batches 20
"""
import argparse
import json
import random
from pathlib import Path
from datetime import datetime

from common import chat, load_prompt, clean_json
from gen_arxiv import get_license, is_allowed_license
from article_bulk_select import gather_candidates, _batched, _existing_base_ids, license_audit, OUT_DIR

BROAD_PHYSICS_CATS = ["astro-ph.*", "gr-qc", "quant-ph", "nucl-ex", "nucl-th",
                       "hep-ph", "hep-th", "hep-ex", "hep-lat", "cond-mat.*", "physics.*", "math-ph"]


def select_batch(batch, tag):
    j = json.dumps([{"id": a["id"], "title": a["title"], "authors": a["authors"]} for a in batch],
                   ensure_ascii=False)
    prompt = load_prompt("arab-authors-select").format(articles_json=j)
    try:
        r = chat("select", prompt)
        data = json.loads(clean_json(r.choices[0].message.content))
        ids = set(data.get("ids", []))
    except Exception as e:
        print(f"    ⚠️ батч {tag}: ошибка {e}")
        return []
    return [a for a in batch if a["id"] in ids]


def run(target, months_back, batch_size, max_batches):
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    exclude = _existing_base_ids()
    pool = gather_candidates(BROAD_PHYSICS_CATS, months_back, exclude)
    random.shuffle(pool)
    print(f"🚀 arab-authors-select {run_id}: пул кандидатов {len(pool)} (широкий физический охват, "
          f"{months_back} мес), цель {target}, потолок {max_batches} батчей")

    found = []
    batches = list(_batched(pool, batch_size))[:max_batches]
    for i, batch in enumerate(batches, 1):
        hits = select_batch(batch, f"{run_id}-{i}")
        found.extend(hits)
        print(f"  батч {i}/{len(batches)}: +{len(hits)}, всего найдено {len(found)}")
        if len(found) >= target + 20:  # запас на лицензии
            break

    if not found:
        print("❌ ничего не найдено")
        return None

    license_results = license_audit(found)
    ready = [a for a in found if license_results.get(a["id"], {}).get("allowed")][:target + 10]
    print(f"\n✅ Готово: {len(ready)} готовы к генерации (из {len(found)} найденных, "
          f"просканировано {sum(len(b) for b in batches[:i])} статей в {i} батчах)")

    out = {
        "run_id": run_id, "created": datetime.now().isoformat(timespec="seconds"),
        "categories": BROAD_PHYSICS_CATS, "months_back": months_back,
        "target": target, "pool_size": len(pool), "found": len(found),
        "ready": [{**a, "score": 10} for a in ready],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"arab-authors-{run_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   Сохранено: {out_path}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Целевой отбор статей с авторами из арабских стран")
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--months-back", type=int, default=24)
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--max-batches", type=int, default=20)
    args = ap.parse_args()
    run(args.target, args.months_back, args.batch_size, args.max_batches)
