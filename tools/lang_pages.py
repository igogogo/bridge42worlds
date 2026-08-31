#!/usr/bin/env python3
"""Верхние страницы — по адресу на каждый язык.

Статьи давно живут правильно: /lang/ar/archive/… — свой адрес, свой canonical на
себя, взаимный hreflang на пять языков. Верхние страницы — «Идеи», «Учиться»,
«Что исследовать», курс — жили по ОДНОМУ адресу на все языки, а язык выбирался
на клиенте по ?lang= и сохранённому выбору. Для поисковика это одна русская
страница: четырёх языков из пяти у неё просто нет — ни адреса, ни hreflang, ни
шанса попасть в выдачу. Владелец 31.08: «разные языки не индексируются?» — вот
здесь действительно не индексировались.

Корень остаётся русской версией (и x-default), остальные языки получают копию в
lang/<язык>/<страница>.html. Копия отличается тремя вещами: атрибутом языка у
<html>, предустановкой языка до всех скриптов страницы и своим canonical.

    python tools/lang_pages.py            собрать копии и проставить hreflang
    python tools/lang_pages.py --list     показать список страниц и адресов
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import ALL_LANGS, DEFAULT_LANG  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SITE = "https://bridge42worlds.academy"
RTL = {"ar", "he", "fa"}

# Только ОТКРЫТЫЕ страницы, которые действительно переведены. Служебные (pipeline,
# status, concepts-audit, макеты) сюда не берём: множить на пять языки того, что
# читает один человек, — тратить обход поисковика впустую.
PAGES = [
    "ideas", "learn", "research", "discoveries", "frontier", "hypotheses",
    "ask", "course", "course-thermodynamics", "lecture", "reference",
    "mathkit", "memo",
]

MARK_A = "<!-- b42:hreflang -->"
MARK_B = "<!-- /b42:hreflang -->"


def url_of(page, lang):
    """Корень — язык по умолчанию; остальные языки лежат в своей папке."""
    return (f"{SITE}/{page}.html" if lang == DEFAULT_LANG
            else f"{SITE}/lang/{lang}/{page}.html")


def head_block(page, lang):
    """canonical на себя + взаимные hreflang. Один блок, помеченный с двух сторон,
    чтобы повторный прогон заменял его, а не подшивал второй."""
    rows = [f'<link rel="canonical" href="{url_of(page, lang)}">']
    rows += [f'<link rel="alternate" hreflang="{l}" href="{url_of(page, l)}">'
             for l in ALL_LANGS]
    rows.append(f'<link rel="alternate" hreflang="x-default" '
                f'href="{url_of(page, DEFAULT_LANG)}">')
    return MARK_A + "\n" + "\n".join(rows) + "\n" + MARK_B


def put_head(html, block):
    if MARK_A in html:
        return re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B), lambda m: block,
                      html, count=1, flags=re.S)
    return html.replace("</head>", block + "\n</head>", 1)


def to_lang(html, page, lang):
    """Копия страницы на своём языке.

    Язык предустанавливаем ТРЕМЯ путями, потому что страницы разбирают его каждая
    сама: (1) атрибут <html lang> — его читают ideas.html и меню; (2) сохранённый
    выбор b42_lang — его читают все страницы вторым шагом после ?lang=; (3) запасное
    значение в самом разборе — на случай, если хранилище закрыто (режим инкогнито,
    робот с урезанным окружением). Иначе арабская страница отдала бы русский текст
    под арабским атрибутом — худший из возможных ответов и поисковику, и читателю.
    """
    dirn = "rtl" if lang in RTL else "ltr"
    html = re.sub(r'<html[^>]*>', f'<html lang="{lang}" dir="{dirn}">', html, count=1)
    pre = (f'<script>window.B42_LANG="{lang}";'
           f'try{{localStorage.setItem("b42_lang","{lang}")}}catch(e){{}}</script>')
    html = html.replace("</head>", pre + "\n</head>", 1)
    # запасное значение внутри разбора страницы
    html = re.sub(r"\? saved : '(?:ru|en)'", f"? saved : '{lang}'", html)
    html = re.sub(r'window\.B42_LANG \|\| .ru.', f"window.B42_LANG || '{lang}'", html)
    return put_head(html, head_block(page, lang))


def main():
    if "--list" in sys.argv:
        for p in PAGES:
            print(p, "→", " ".join(url_of(p, l) for l in ALL_LANGS))
        return 0
    made = roots = 0
    for page in PAGES:
        src = ROOT / f"{page}.html"
        if not src.exists():
            print(f"  ⚠ нет {page}.html — пропускаю")
            continue
        html = src.read_text(encoding="utf-8")
        # корень: свой canonical и полный набор языков
        src.write_text(put_head(html, head_block(page, DEFAULT_LANG)), encoding="utf-8")
        roots += 1
        for lang in ALL_LANGS:
            if lang == DEFAULT_LANG:
                continue
            out = ROOT / "lang" / lang / f"{page}.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(to_lang(html, page, lang), encoding="utf-8")
            made += 1
    print(f"✅ верхние страницы по языкам: корней {roots}, копий {made} "
          f"({len(ALL_LANGS) - 1} языка × {roots})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
