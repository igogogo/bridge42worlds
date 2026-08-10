#!/usr/bin/env python3
"""Добрать разобранный текст из PDF, которые уже лежат в папках статей.

Владелец 2026-08-09: «нам бы вектор по всем статьям из PDF, поэтому PDF сохраняем,
парсим и строим хотя бы вектор».

Что было не так. Генератор разбирал PDF, отдавал текст в промпт и выбрасывал — рядом
со статьёй оставались только сам PDF и список литературы. Для вектора это и есть потеря:
аннотация написана автором как витрина, а методика, оговорки и настоящие результаты живут
в теле статьи. Дыры в знании по аннотациям не найти.

Вперёд это уже починено (generate.py пишет fulltext.txt), здесь — назад, по тому, что
на диске. Модель не вызывается ни разу, только разбор файлов.

    python tools/fulltext_backfill.py --check     сколько PDF без текста
    python tools/fulltext_backfill.py             разобрать всё
    python tools/fulltext_backfill.py --limit 50  проба на полусотне
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ARCHIVE = ROOT / "lang" / "ru" / "archive"


def targets(limit=None):
    """Статьи, где PDF есть, а текста ещё нет."""
    out = []
    for pdf in sorted(ARCHIVE.glob("*/*/original.pdf")):
        if pdf.stat().st_size < 10_000:
            continue                      # обрубок, разбирать нечего
        if (pdf.parent / "fulltext.txt").exists():
            continue
        out.append(pdf)
        if limit and len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    todo = targets(args.limit)
    have = len(list(ARCHIVE.glob("*/*/fulltext.txt")))
    pdfs = len(list(ARCHIVE.glob("*/*/original.pdf")))
    print(f"PDF на диске: {pdfs} · текст уже есть: {have} · разобрать: {len(todo)}")
    if args.check or not todo:
        return 0

    import generate
    ok = fail = 0
    chars = 0
    for i, pdf in enumerate(todo, 1):
        try:
            text, _imgs = generate.parse_pdf(pdf)
            body, _refs = generate.split_references(text)
            # Ссылки выкидываем — те же двадцать процентов токенов, что и при генерации,
            # и для смыслового сравнения они только шум.
            body = re.sub(r"https?://\S+", "", body or "")
            if len(body) < 500:
                fail += 1
                continue
            (pdf.parent / "fulltext.txt").write_text(body, encoding="utf-8", errors="replace")
            ok += 1
            chars += len(body)
        except Exception as ex:
            fail += 1
            if fail <= 5:
                print(f"  ⚠️ {pdf.parent.name}: {type(ex).__name__} {ex}")
        if i % 200 == 0:
            print(f"  … {i}/{len(todo)}, разобрано {ok}, пропущено {fail}")

    print(f"\n✅ разобрано {ok}, пропущено {fail}")
    print(f"   текста: {chars / 1e6:.0f} млн знаков ≈ {chars / 2**20:.0f} МБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
