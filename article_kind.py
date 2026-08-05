"""Жанр статьи для оси отбора: experimental / theoretical / methods / review.

Зачем. ML показал, что корзина «теории», набранная поиском по словам, вырождена:
29 статей против 694 практических, косинус центроидов 0,875 — ось ранжирует шум.
Слова в аннотации не разделяют жанры, потому что «model» и «data» есть почти везде.
Поэтому жанр определяет модель по смыслу — один раз по корпусу, дальше это просто файл.

Дёшево: flash, пачками по 25 работ, вход — заголовок и первые 700 знаков аннотации
(жанр виден по первым фразам, дальше идут детали и цена).

    python article_kind.py --limit 50      # проба
    python article_kind.py                 # весь корпус → data/article-kind.json
    python article_kind.py --sample 100    # слепая выборка для проверки глазами

Результат: {id: kind}. Повторный запуск дописывает только недостающие id.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ключ живёт в главной папке проекта; рабочие копии ролей его не держат.
load_dotenv()
if not os.environ.get("DEEPSEEK_API_KEY"):
    load_dotenv(Path(__file__).resolve().parent.parent / "bridge42worlds" / ".env")

from common import chat, clean_json, load_prompt  # noqa: E402

OUT = Path("data/article-kind.json")
ARCHIVE = Path("lang/ru/archive")
KINDS = ("experimental", "theoretical", "methods", "review")
BATCH = 25
ABSTRACT_CHARS = 700


def corpus(archive=None):
    """{id: (заголовок, английская аннотация)} — источник тот же, что у вектора ML.

    archive — путь к lang/ru/archive. Он нужен, потому что рабочие копии ролей держат
    исходники, а собранный сайт лежит только в главной папке: скрипт запускается из своей
    папки (там промпты), а данные читает оттуда."""
    out = {}
    for path in sorted(Path(archive or ARCHIVE).glob("*/*/data.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = data.get("original_title") or ""
        abstract = ((data.get("abstract") or {}).get("en") or {}).get("advanced") or ""
        if title and abstract:
            out[data.get("id") or path.parent.name] = (title, abstract)
    return out


def classify(batch):
    items = "\n\n".join(f"id: {aid}\nЗаголовок: {title}\nАннотация: {abstract[:ABSTRACT_CHARS]}"
                        for aid, (title, abstract) in batch)
    prompt = load_prompt("article-kind").format(items=items)
    try:
        raw = chat("translate_flash", prompt).choices[0].message.content
        data = json.loads(clean_json(raw))
    except Exception as e:
        print(f"    ⚠️ пачка не разобралась: {e}")
        return {}
    return {k: v for k, v in data.items() if v in KINDS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="обработать только N статей (проба)")
    ap.add_argument("--sample", type=int, help="напечатать слепую выборку для проверки глазами")
    ap.add_argument("--archive", help="путь к lang/ru/archive, если данные в другой папке")
    args = ap.parse_args()

    known = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}

    if args.sample:
        import random
        rng = random.Random(42)          # фиксированный, чтобы выборку можно было повторить
        pool = [(k, v) for k, v in known.items()]
        rng.shuffle(pool)
        data = corpus(args.archive)
        for aid, kind in pool[:args.sample]:
            title = data.get(aid, ("", ""))[0]
            print(f"{aid}\t{kind}\t{title[:110]}")
        return

    data = corpus(args.archive)
    todo = [(k, v) for k, v in data.items() if k not in known]
    if args.limit:
        todo = todo[:args.limit]
    print(f"корпус {len(data)}, уже размечено {len(known)}, к обработке {len(todo)}")

    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        got = classify(batch)
        known.update(got)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)} — размечено {len(got)} из {len(batch)}")

    from collections import Counter
    counts = Counter(known.values())
    total = sum(counts.values())
    print(f"\nвсего размечено {total}:")
    for kind in KINDS:
        print(f"   {kind:14} {counts.get(kind, 0):>5}  {counts.get(kind, 0) * 100 // max(1, total)}%")


if __name__ == "__main__":
    main()
