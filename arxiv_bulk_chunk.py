#!/usr/bin/env python3
"""Разовый скрипт: разбивает bulk-дамп Kaggle arXiv (Cornell-University/arxiv,
arxiv-metadata-oai-snapshot.json, ~5.4GB) на помесячные .jsonl-чанки в data/arxiv-bulk/.

Месяц/дата берутся из даты ПЕРВОЙ версии (v1.created) — тот же критерий, что
submittedDate в live arXiv API, так что day-фильтрация в fetch_arxiv_local()
(gen_arxiv.py) даёт те же результаты, что и живой запрос.

Сам исходный файл НЕ входит в репозиторий (лежит в кэше kagglehub), и
data/arxiv-bulk/ тоже в .gitignore — это чисто локальный кэш для обхода
rate-limit'а arXiv API при бэкфилле исторических диапазонов."""

import sys
import json
from pathlib import Path
from email.utils import parsedate_to_datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

SRC = Path.home() / ".cache/kagglehub/datasets/Cornell-University/arxiv/versions/294/arxiv-metadata-oai-snapshot.json"
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.jsonl"):
        old.unlink()

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
                    fh = (OUT_DIR / f"{mkey}.jsonl").open("w", encoding="utf-8")
                    handles[mkey] = fh
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if n % 200000 == 0:
                    print(f"  ... {n} обработано, {len(handles)} месяцев, пропущено {skipped}", flush=True)
    finally:
        for fh in handles.values():
            fh.close()
    print(f"✅ Готово: {n} записей, {len(handles)} месячных файлов ({OUT_DIR}), пропущено {skipped}")


if __name__ == "__main__":
    main()
