# -*- coding: utf-8 -*-
"""Внутренние ссылки: ведут ли они куда-нибудь.

Появился 28.08 из находки перед выкладкой. Утром убрали заглушку «карточки пока
нет» — правильно убрали, она обещала содержание, которого нет. Но у чипов на
карточке статьи проверки не было вовсе: ссылка ставилась на любое имя из
разметки, а в курируемом реестре учёных 201 человек. Выборка из полусотни
страниц дала 188 ссылок в 404 — и это ушло бы в прод, если бы не ручная проверка.

Поэтому проверка стала инструментом. Она смотрит не «есть ли ссылка», а лежит ли
по её адресу файл — на выборке страниц каждого вида, чтобы пройти быстро и всё
же поймать системную поломку.

Считаем только внутренние адреса своего сайта: внешние (arxiv.org, doi) не наша
забота, якоря и запросы отрезаем.

    python tools/link_check.py               выборка по 40 страниц каждого вида
    python tools/link_check.py --all         всё дерево (долго)
    python tools/link_check.py --sample 200
"""
import argparse
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Берём весь адрес и отрезаем запрос/якорь сами. Первая версия исключала «?» и «#»
# прямо в шаблоне — и ссылки с параметрами (graph.html?set=…, а это переход в граф
# с набором статьи) не проверялись ВОВСЕ: шаблон на них просто не совпадал. Проверка,
# которая молча пропускает целый класс ссылок, хуже отсутствующей — она успокаивает.
HREF = re.compile(r'href="(/[^"]*)"')
# Куда смотреть: по одному представителю каждого вида страниц, чтобы поломка в
# любом шаблоне всплыла.
KINDS = {
    "статьи": "lang/ru/archive/*/*/index.html",
    "подробные": "lang/ru/archive/*/*/advanced.html",
    "понятия": "lang/ru/concepts/*.html",
    "формулы": "lang/ru/formula/*.html",
    "учёные": "lang/ru/scientists/*.html",
    "авторы": "lang/en/authors/*.html",
}


def target_exists(url):
    """Есть ли файл по адресу. Каталог годится, если в нём есть index.html."""
    p = ROOT / url.lstrip("/")
    if p.is_dir():
        return (p / "index.html").exists()
    if p.exists():
        return True
    if url.endswith("/"):
        return (p / "index.html").exists()
    return False


def main():
    ap = argparse.ArgumentParser(description="Проверка внутренних ссылок")
    ap.add_argument("--all", action="store_true", help="всё дерево")
    ap.add_argument("--sample", type=int, default=40, help="страниц каждого вида")
    a = ap.parse_args()

    rnd = random.Random(42)
    checked = 0
    bad = defaultdict(list)          # раздел → список битых адресов
    pages_with_bad = set()
    cache = {}

    for kind, pattern in KINDS.items():
        files = list(ROOT.glob(pattern))
        if not files:
            continue
        if not a.all and len(files) > a.sample:
            files = rnd.sample(files, a.sample)
        for f in files:
            try:
                t = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in HREF.finditer(t):
                url = m.group(1).split("?")[0].split("#")[0]
                if not url or url.startswith("//") or url.startswith("/http"):
                    continue
                checked += 1
                ok = cache.get(url)
                if ok is None:
                    ok = target_exists(url)
                    cache[url] = ok
                if not ok:
                    section = url.strip("/").split("/")[2] if url.count("/") > 2 else url
                    bad[section].append(url)
                    pages_with_bad.add(str(f.relative_to(ROOT)))
        print(f"  {kind}: {len(files)} страниц")

    total_bad = sum(len(v) for v in bad.values())
    print(f"\nпроверено ссылок: {checked} · разных адресов: {len(cache)}")
    print(f"битых: {total_bad} на {len(pages_with_bad)} страницах")
    for section, urls in sorted(bad.items(), key=lambda kv: -len(kv[1])):
        uniq = sorted(set(urls))
        print(f"  {section}: {len(urls)} ссылок, {len(uniq)} разных адресов")
        for u in uniq[:5]:
            print(f"      {u}")
    # Код возврата — сигнал для цепочки: битые ссылки это не «к сведению».
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
