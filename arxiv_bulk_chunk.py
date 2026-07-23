#!/usr/bin/env python3
"""Разбивает bulk-дамп Kaggle arXiv (Cornell-University/arxiv,
arxiv-metadata-oai-snapshot.json, ~5.4GB) на помесячные .jsonl-чанки в data/arxiv-bulk/.

Месяц/дата берутся из даты ПЕРВОЙ версии (v1.created) — тот же критерий, что
submittedDate в live arXiv API, так что day-фильтрация в fetch_arxiv_local()
(gen_arxiv.py) даёт те же результаты, что и живой запрос.

НАДЁЖНОСТЬ (2026-07-22): не удаляем старые чанки заранее. Пишем в {месяц}.jsonl.tmp,
и только в самом конце атомарно переименовываем поверх ({месяц}.jsonl). Значит:
  • при сбое/обрыве старая база остаётся целой (никакого «удалил и не досоздал»);
  • месяцы, которых нет в новом дампе, НЕ трогаются (перезаписываются только обновлённые);
  • можно запускать поверх существующей базы для обновления свежими месяцами.

Источник ищется по порядку: аргумент CLI → ~/Downloads → кэш kagglehub.
Сам исходный файл и data/arxiv-bulk/ — в .gitignore (локальный кэш для обхода
rate-limit'а arXiv API при бэкфилле исторических диапазонов).

Использование:
  python arxiv_bulk_chunk.py [путь/к/arxiv-metadata-oai-snapshot.json]
"""

import os
import sys
import json
from pathlib import Path
from email.utils import parsedate_to_datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Источник: CLI-аргумент → Downloads → кэш kagglehub (первый существующий).
_CANDIDATES = [
    sys.argv[1] if len(sys.argv) > 1 else None,
    str(Path.home() / "Downloads" / "arxiv-metadata-oai-snapshot.json"),
    str(Path.home() / ".cache/kagglehub/datasets/Cornell-University/arxiv/versions/294/arxiv-metadata-oai-snapshot.json"),
]
SRC = next((Path(c) for c in _CANDIDATES if c and Path(c).exists()), Path(_CANDIDATES[-1]))
OUT_DIR = Path("data/arxiv-bulk")


def month_and_date(created):
    try:
        dt = parsedate_to_datetime(created)
        return dt.strftime("%Y-%m"), dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None


def main():
    if not SRC.exists():
        print(f"❌ не найден исходный файл: {SRC}")
        return
    print(f"📂 источник: {SRC}  ({SRC.stat().st_size / 1e9:.1f} ГБ)")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Пишем во ВРЕМЕННЫЕ файлы {месяц}.jsonl.tmp — старые чанки пока не трогаем.
    handles = {}
    n = 0
    skipped = 0
    try:
        with SRC.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n += 1
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                versions = d.get("versions") or []
                if not versions:
                    skipped += 1
                    continue
                mkey, date_str = month_and_date(versions[0].get("created", ""))
                if not mkey:
                    skipped += 1
                    continue
                rec = {
                    "id": d.get("id"),
                    "title": (d.get("title") or "").strip().replace("\n", " "),
                    "abstract": (d.get("abstract") or "").strip().replace("\n", " "),
                    "authors_parsed": d.get("authors_parsed") or [],
                    "categories": (d.get("categories") or "").split(),
                    "published": date_str,
                }
                fh = handles.get(mkey)
                if fh is None:
                    fh = (OUT_DIR / f"{mkey}.jsonl.tmp").open("w", encoding="utf-8")
                    handles[mkey] = fh
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if n % 200000 == 0:
                    print(f"  ... {n} обработано, {len(handles)} месяцев, пропущено {skipped}", flush=True)
    finally:
        for fh in handles.values():
            fh.close()

    # Готово без сбоя → атомарно переносим каждый .tmp поверх боевого чанка.
    # os.replace атомарен в пределах тома: чанк заменяется только целиком готовым.
    replaced = 0
    for mkey in handles:
        tmp = OUT_DIR / f"{mkey}.jsonl.tmp"
        if tmp.exists():
            os.replace(tmp, OUT_DIR / f"{mkey}.jsonl")
            replaced += 1
    print(f"✅ Готово: {n} записей, {replaced} месячных чанков перезаписано ({OUT_DIR}), пропущено {skipped}")
    print("   (месяцы, которых не было в дампе, оставлены как были)")


if __name__ == "__main__":
    main()
