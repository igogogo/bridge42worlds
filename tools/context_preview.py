#!/usr/bin/env python3
"""Показать, какое окружение увидит модель при полном разборе — без вызова модели.

Волна 18.08 требует показать макет промпта ДО массового прогона, и это тот случай, когда
инструмент нужен не один раз: блок окружения зависит от состояния вектор-индекса, а он
наполняется отдельным шагом (tools/upkeep.cmd). Через месяц вопрос «а что там сейчас
подставляется» возникнет снова, и отвечать на него дешевле командой, чем чтением кода.

    python tools/context_preview.py 2608.06321v1          # блок окружения
    python tools/context_preview.py 2608.06321v1 --full   # весь промпт целиком

Денег не тратит на разбор, но ДЁРГАЕТ ВЕКТОР: эмбеддинг запроса через Workers AI —
доли цента за вызов. Нужны ключи CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN в .env.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gen_context  # noqa: E402


def load_article(aid):
    """Собираем тот же объект, что придёт из arXiv API на генерации: title + summary."""
    hits = list((ROOT / "lang" / "ru" / "archive").glob(f"*/{aid}/data.json"))
    if not hits:
        hits = list((ROOT / "lang" / "ru" / "archive").glob(f"*/{aid}*/data.json"))
    if not hits:
        print(f"нет статьи {aid} в архиве")
        return None, ""
    d = json.loads(hits[0].read_text(encoding="utf-8"))
    abstract = d.get("abstract_orig") or ""
    if not abstract:
        # У свежих работ abstract_orig ещё не заполнен (его пишет отдельный backfill).
        # На живой генерации аннотация приходит из arXiv API и всегда есть — здесь же
        # берём наш пересказ, чтобы превью было о чём.
        adv = ((d.get("advanced") or {}).get("ru") or {})
        abstract = adv.get("description") or (d.get("popular") or {}).get("ru", {}).get("description", "")
    art = {"id": aid, "title": d.get("original_title") or d.get("title", ""), "summary": abstract}
    text = ""
    ft = hits[0].parent / "fulltext.txt"
    if ft.exists():
        text = ft.read_text(encoding="utf-8", errors="replace")[:4000]
    return art, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aid", help="arXiv id статьи из нашего архива")
    ap.add_argument("--full", action="store_true", help="показать промпт целиком, а не только блок")
    args = ap.parse_args()

    art, text = load_article(args.aid)
    if not art:
        return 1

    block, meta = gen_context.build_block(art, text, aid=args.aid)
    print("=" * 78)
    print(block or "(окружение пустое — разбор пойдёт как раньше)")
    print("=" * 78)
    print(f"соседей из архива: {len(meta.get('neighbours') or [])}, "
          f"из мирового поля: {len(meta.get('world') or [])}, "
          f"плотность: {meta.get('frontier')}, группа: "
          f"{(meta.get('cluster') or {}).get('tags')}")

    if args.full:
        from common import load_prompt
        prompt = load_prompt("article-generate-advanced").format(
            tags_list="(теги передаются вектором, см. tags_in_prompt)",
            scientists_list="(список учёных)", laws_list="(список законов)",
            article_text=text[:600] + " …", context_block=block)
        print("\n" + "=" * 78 + "\nПРОМПТ ЦЕЛИКОМ\n" + "=" * 78)
        print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
