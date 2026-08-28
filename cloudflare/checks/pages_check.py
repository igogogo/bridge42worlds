# -*- coding: utf-8 -*-
"""Проверка живых СТРАНИЦ: отвечают ли и то ли отвечают.

Что уже проверялось и чего не хватало. api_check смотрит эндпоинты воркера,
verify_publish — индексы лент. Обе проверяют динамику. А сам сайт — двадцать
тысяч статических страниц — не проверял никто: раздел мог не доехать в R2 целиком,
и узнали бы об этом от читателя.

Проверяем по одному представителю каждого вида и смотрим не код ответа, а
содержимое: код 200 отдаёт и страница-заглушка, и обрезанный до половины файл.

    python cloudflare/checks/pages_check.py            # боевой сайт
    python cloudflare/checks/pages_check.py --dev      # испытательный воркер
    python cloudflare/checks/pages_check.py --base http://localhost:8420
"""
import argparse
import sys
import urllib.error
import urllib.request
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROD = "https://bridge42worlds.academy"
DEV = "https://bridge42worlds-dev.bridge42worlds-dev.workers.dev"

# Вид страницы → адрес и что на ней обязано быть. Проверяем СОДЕРЖАНИЕ, а не код:
# пустая страница с кодом 200 — самая частая поломка выкладки.
CASES = [
    ("главная ru", "/lang/ru/index.html", ["bridge42worlds", "concepts"]),
    ("главная en", "/lang/en/index.html", ["bridge42worlds", "concepts"]),
    ("статья", "/lang/ru/archive/2026-08-18/2608.17807v1/index.html",
     ["side-tag", "lv-btn"]),
    ("облако понятий", "/lang/ru/concepts/index.html", ["Понятия", "details"]),
    ("страница понятия", "/lang/ru/concepts/black_hole.html",
     ["b42mini", "Описание"]),
    ("граф", "/lang/ru/concepts/graph.html", ["b42-graph.js", "canvas"]),
    ("формула", "/lang/ru/formula/hubble_law.html", ["katex", "fx-s"]),
    ("учёный", "/lang/ru/scientists/Albert_Einstein.html", ["side-sci"]),
    ("автор", "/lang/en/authors/Y_Wang.html", ["data-akey"]),
    ("разделы", "/lang/ru/sections/index.html", ["astro-ph"]),
    ("о проекте", "/lang/ru/about.html", ["Понятие", "граф"]),
    ("переадресация тега", "/lang/ru/tags/black_hole.html", ["refresh"]),
    # Корневая карта — оглавление на карты языков, а не список адресов.
    ("карта сайта", "/sitemap.xml", ["<sitemapindex", "sitemap-ru.xml"]),
]


def get(base, path, timeout=25):
    req = urllib.request.Request(base + path, headers={"User-Agent": "b42-pages"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser(description="Проверка страниц сайта")
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--base")
    a = ap.parse_args()
    base = a.base or (DEV if a.dev else PROD)
    print(f"═══ ПРОВЕРКА СТРАНИЦ: {base} ═══")

    ok = bad = 0
    for name, path, needles in CASES:
        code, body = get(base, path)
        if code != 200:
            print(f"  ✗ {name:22s} код {code}  {path}")
            bad += 1
            continue
        missing = [n for n in needles if n not in body]
        if missing:
            print(f"  ✗ {name:22s} 200, но нет: {', '.join(missing)}  ({len(body)} байт)")
            bad += 1
            continue
        print(f"  ✓ {name:22s} {len(body):>7} байт")
        ok += 1
    print(f"    итог: {ok} прошло, {bad} нет")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
