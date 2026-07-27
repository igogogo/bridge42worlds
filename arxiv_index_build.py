"""Компактный индекс arXiv из Kaggle-снапшота — чтобы не хранить 5 ГБ ради нескольких полей.

Из снапшота (5 ГБ) вытаскиваем только то, что реально нужно проекту:
id, разделы, ЛИЦЕНЗИЯ (без неё нельзя брать статью), дата, есть ли DOI/journal-ref, длина абстракта.
Получается ~200-300 МБ. Дальше balanced_select.py и corpus_stats.py работают с ним, а сам снапшот
нужен только когда захотим обновить базу свежими месяцами.

Запуск:
    python arxiv_index_build.py                    # собрать индекс из снапшота
    python arxiv_index_build.py --years 25,26      # только нужные годы (меньше и быстрее)
"""
import json
import sys
from pathlib import Path

SNAPSHOT = Path(r"C:/Users/nadez/Downloads/arxiv-metadata-oai-snapshot.json")
OUT = Path("data/arxiv-index.jsonl")


def main():
    argv = sys.argv
    years = (argv[argv.index("--years") + 1].split(",") if "--years" in argv else None)
    if not SNAPSHOT.exists():
        print(f"нет снапшота: {SNAPSHOT}")
        print("положи Kaggle-датасет «arXiv Dataset» (archive.zip → arxiv-metadata-oai-snapshot.json) туда")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    kept = seen = 0
    with SNAPSHOT.open(encoding="utf-8") as src, OUT.open("w", encoding="utf-8") as dst:
        for line in src:
            seen += 1
            if years:
                head = line[:20]
                if not any(f'"{y}' in head for y in years):
                    continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            aid = d.get("id", "")
            if years and aid[:2] not in years:
                continue
            versions = d.get("versions") or [{}]
            rec = {
                "id": aid,
                "c": d.get("categories", ""),                 # разделы строкой, как в снапшоте
                "l": d.get("license") or "",                  # лицензия — главное, ради чего всё
                "d": versions[0].get("created", ""),          # дата первой версии
                "p": 1 if (d.get("doi") or d.get("journal-ref")) else 0,   # прошла ли рецензию
                "n": len(d.get("abstract") or ""),            # объём абстракта (для ранжирования)
            }
            dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
            if kept % 200000 == 0:
                print(f"  … {kept:,} записей", flush=True)

    size = OUT.stat().st_size / 1024 / 1024
    print(f"готово: {kept:,} записей из {seen:,} строк → {OUT} ({size:.0f} МБ)")
    print("теперь снапшот можно удалять — отбор и статистика работают с этим индексом")


if __name__ == "__main__":
    main()
