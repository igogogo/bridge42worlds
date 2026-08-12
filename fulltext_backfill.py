#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разовый проход по лежащим PDF: сохранить текст статьи рядом с ней.

ЗАЧЕМ. Сейчас текст PDF разбирается, уходит в промпт и выбрасывается — остаётся только
`references.txt`. Из-за этого вектор строится по АННОТАЦИИ, а аннотация это витрина:
методика, оговорки и «что на самом деле сделали» живут в теле статьи. Владелец 2026-08-09:
«нам бы вектор по всем статьям из PDF».

У нас лежит 3207 файлов `original.pdf` на 12 ГБ. Текста из них выйдет около 150 МБ —
разбор бесплатный, ни одного обращения к модели.

ПАРСЕР БЕРЁМ СВОЙ, НЕ ПИШЕМ ВТОРОЙ. `gen_arxiv.parse_pdf()` уже существует, уже лечён
(вся работа с arXiv идёт через общий ретрай после потери двух статей 31 июля) и уже
используется генератором. Правило волны: не писать своё рядом с готовым — дважды на этом
обожглись 8 августа.

ЧТО СОХРАНЯЕМ. `fulltext.txt` рядом с `original.pdf`. Список литературы отрезаем тем же
`split_references()`, что и генератор: в векторе он только мешает — это чужие заголовки,
из-за которых любые две статьи по одной теме кажутся похожими.

    python fulltext_backfill.py --check          # что есть, что выйдет, ничего не пишет
    python fulltext_backfill.py --run [--limit N]
"""
import re, sys, pathlib, argparse, time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
ARCHIVE = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds\lang\ru\archive")

from gen_arxiv import parse_pdf, split_references  # noqa: E402  — свой парсер проекта

MIN_CHARS = 500      # ниже этого PDF не разобрался: скан, только картинки, битый файл

_SURROGATE = re.compile(r"[\ud800-\udfff]")


def fix_surrogates(s):
    """Починить текст, который не записывается в UTF-8.

    ЗАМЕР 2026-08-09: прогон упал на `\\ud835` — одиночном суррогате. pypdf отдаёт
    математические буквы из блока U+1D400 (𝐀, 𝑥 — ими набирают векторы и операторы
    в физических статьях) половинкой суррогатной пары. Такой символ формально не
    является кодовой точкой UTF-8, и запись падает на всей статье целиком.

    Сначала пробуем СКЛЕИТЬ пары обратно — тогда 𝐀 сохраняется как настоящая буква.
    Что не склеилось (обломки без второй половины) — выбрасываем: одна половина
    суррогата не значит ничего, а ронять из-за неё статью на сто тысяч знаков глупо.
    """
    try:
        return s.encode("utf-16", "surrogatepass").decode("utf-16")
    except UnicodeDecodeError:
        return _SURROGATE.sub("", s)


def targets(archive):
    for pdf in sorted(archive.rglob("original.pdf")):
        yield pdf, pdf.with_name("fulltext.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--archive", default=str(ARCHIVE))
    a = ap.parse_args()
    archive = pathlib.Path(a.archive)
    if not archive.exists():
        sys.exit(f"нет архива: {archive}")

    todo = [(p, t) for p, t in targets(archive) if not t.exists()]
    have = sum(1 for _, t in targets(archive) if t.exists())
    print(f"PDF всего: {have + len(todo)}   уже разобрано: {have}   осталось: {len(todo)}")

    if a.check or not a.run:
        # ПРОВЕРКА ДО ЗАПИСИ — второе правило волны. Смотрим на десятке, что выходит
        # из парсера, прежде чем писать три тысячи файлов.
        sample = todo[:10]
        if not sample:
            print("нечего проверять")
            return
        print("\nпробный разбор десяти:")
        ok = 0
        for pdf, _ in sample:
            text, _imgs = parse_pdf(pdf)
            body, _refs = split_references(text) if text else ("", "")
            status = "ок" if len(body) >= MIN_CHARS else "ПУСТО"
            if len(body) >= MIN_CHARS:
                ok += 1
            print(f"  {pdf.parent.name:<16} {len(text):>8} знаков → тело {len(body):>8}  {status}")
        print(f"\nразобралось {ok} из {len(sample)}")
        print("если доля пустых велика — это сканы или картиночные PDF, а не поломка парсера")
        print("\n--check: ничего не записано. Для записи: --run")
        return

    if a.limit:
        todo = todo[:a.limit]
    t0 = time.time()
    written = skipped = 0
    for n, (pdf, out) in enumerate(todo, 1):
        text, _imgs = parse_pdf(pdf)
        if not text:
            skipped += 1
            continue
        body, _refs = split_references(text)
        if len(body) < MIN_CHARS:
            skipped += 1
            continue
        out.write_text(fix_surrogates(body), encoding="utf-8")
        written += 1
        if n % 200 == 0:
            print(f"  {n}/{len(todo)}: записано {written}, пропущено {skipped}, "
                  f"{time.time()-t0:.0f}с")
    size = sum((p.with_name("fulltext.txt").stat().st_size
                for p, _ in targets(archive) if p.with_name("fulltext.txt").exists()), 0)
    print(f"\nзаписано: {written}, пропущено: {skipped}")
    print(f"объём текста: {size/1024/1024:.0f} МБ (PDF занимали 12 ГБ)")


if __name__ == "__main__":
    main()

