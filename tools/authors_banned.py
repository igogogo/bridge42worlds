# -*- coding: utf-8 -*-
"""Авторы, которых мы больше не разбираем и не показываем.

ЗАЧЕМ. В каждом письме автору мы обещаем: «если не хотите быть здесь вовсе — ответьте
одной строкой, и страница снимается в тот же день, без выяснений». 16.09.2026 таким
ответом воспользовались впервые. Снять одну работу оказалось мало: у автора в архиве
остаются другие работы, из них заново собирается его страница, а ежедневный отбор может
взять его новый препринт завтра же. Обещание «вас здесь не будет» без этого списка
выполнить нечем.

Механизм снятия у нас был только для работ, которые авторы присылали нам сами (коды wd:
в KV, cloudflare/submissions_sync.py). Для автора с arXiv не было ничего.

ЧТО ДЕЛАЕТ ЗАПИСЬ В СПИСКЕ:
  · его работы не берутся в разбор (ежедневный отбор пропускает);
  · его страница автора не собирается и удаляется, если была;
  · уже разобранные работы НЕ удаляются сами — это отдельное решение, потому что у
    работы бывают соавторы, и снимать чужой труд по просьбе одного нельзя молча.

ГДЕ ЛЕЖИТ. В tools/, а не в data/: data/ публикуется целиком, и список людей, которых мы
не показываем, сам не должен оказаться на сайте.

    python tools/authors_banned.py --list
    python tools/authors_banned.py --add "C. Regenfus" --why "попросил снять работу"
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED = Path(__file__).resolve().parent / "authors-banned.json"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

_CACHE = None


def _norm(name):
    """Имя к сравнимому виду: пробелы и регистр не должны решать, забанен человек или нет."""
    return " ".join(str(name or "").split()).strip().lower()


def load():
    """{нормализованное имя: причина}. Пустой словарь — законный ответ."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        raw = json.loads(BANNED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    _CACHE = {_norm(k): v for k, v in (raw.get("authors") or {}).items()}
    return _CACHE


def is_banned(name):
    return _norm(name) in load()


def any_banned(names):
    """Есть ли среди авторов работы хоть один из списка."""
    return any(is_banned(n) for n in (names or []))


def add(name, why=""):
    try:
        raw = json.loads(BANNED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    raw.setdefault("_", [
        "Авторы, которых мы не разбираем и не показываем — по их собственной просьбе.",
        "Файл лежит в tools/, а не в data/: data/ публикуется целиком.",
        "Подробности — в шапке tools/authors_banned.py",
    ])
    raw.setdefault("authors", {})[str(name).strip()] = why
    BANNED.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    global _CACHE
    _CACHE = None
    return True


def main():
    ap = argparse.ArgumentParser(description="Авторы, которых мы не разбираем")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--add", metavar="ИМЯ")
    ap.add_argument("--why", default="", metavar="ПРИЧИНА")
    a = ap.parse_args()
    if a.add:
        add(a.add, a.why)
        print(f"добавлен: {a.add}" + (f" — {a.why}" if a.why else ""))
    banned = load()
    print(f"в списке: {len(banned)}")
    for k, v in sorted(banned.items()):
        print(f"   {k}" + (f" — {v}" if v else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
