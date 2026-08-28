# -*- coding: utf-8 -*-
"""Подпись боковой колонки на готовых страницах: «Теги» → «Понятия».

Слова «тег» на сайте больше нет — меню, облако, страницы и документация уже
говорят «понятия». Последним местом осталась подпись колонки справа на карточке
статьи: она собирается в тело страницы, а тел этих двадцать тысяч.

Причина закрыта в коде (generate.SIDE_TAGS_LABEL), и следующая полная пересборка
поставит правильное слово сама. Но пересборка идёт два часа, а до неё страницы
уже уедут к читателю — поэтому готовые файлы догоняем точечно. Замена строгая:
меняется ровно содержимое подписи, ничего кроме.

    python tools/relabel_sidebar.py            посмотреть, сколько найдётся
    python tools/relabel_sidebar.py --apply    заменить
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# По языку — что было и что стало. Списком, а не одной парой: страницы собраны
# на двух языках, и «Tags» на английской странице такое же старое слово.
PAIRS = {
    "ru": ('<div class="side-tags-label">Теги</div>',
           '<div class="side-tags-label">Понятия</div>'),
    "en": ('<div class="side-tags-label">Tags</div>',
           '<div class="side-tags-label">Concepts</div>'),
    "es": ('<div class="side-tags-label">Etiquetas</div>',
           '<div class="side-tags-label">Conceptos</div>'),
    "fr": ('<div class="side-tags-label">Tags</div>',
           '<div class="side-tags-label">Notions</div>'),
    "ar": ('<div class="side-tags-label">الوسوم</div>',
           '<div class="side-tags-label">المفاهيم</div>'),
}


def main():
    apply = "--apply" in sys.argv
    total = 0
    for lang, (old, new) in PAIRS.items():
        base = ROOT / "lang" / lang
        if not base.exists():
            continue
        n = 0
        for p in base.rglob("*.html"):
            try:
                t = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if old not in t:
                continue
            n += 1
            if apply:
                p.write_text(t.replace(old, new), encoding="utf-8")
        total += n
        if n:
            print(f"  {lang}: {n} страниц")
    print(f"{'заменено' if apply else 'найдено'}: {total}")
    if not apply and total:
        print("сухой ход. заменить: --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
