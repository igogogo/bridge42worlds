"""Проверяет, что связи уроков ведут на существующие страницы сайта.

Урок ссылается на теги, законы и учёных (`entities`). Страница курса делает из них ссылки —
и если сущности нет в собранном сайте, читатель упирается в 404. Проверить это по коду нельзя:
нужен сам сайт, поэтому справочники берём из дерева, где сборка есть (B42_SITE_ROOT).

    python tools/audit_links.py                сводка
    python tools/audit_links.py --full         каждая битая ссылка
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

LANG = "ru"
LESSONS = Path("data/theory/courses")


def site_root():
    probe = f"lang/{LANG}/tags"
    if Path(probe).exists():
        return Path(".")
    env = os.environ.get("B42_SITE_ROOT")
    if env and (Path(env) / probe).exists():
        return Path(env)
    for sib in sorted(Path("..").iterdir()):
        if sib.is_dir() and (sib / probe).exists():
            return sib
    raise SystemExit("Не найден собранный сайт (lang/ru/tags). Укажите B42_SITE_ROOT=../bridge42worlds")


def main():
    root = site_root()
    full = "--full" in sys.argv
    kinds = {"tags": "tags", "laws": "laws", "scientists": "scientists"}
    bad, total = Counter(), Counter()
    broken = {k: Counter() for k in kinds}

    for f in sorted(LESSONS.rglob("*.json")):
        if not f.name[0].isdigit():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        ent = d.get("entities") or {}
        for kind, folder in kinds.items():
            for name in ent.get(kind) or []:
                total[kind] += 1
                fname = name.replace(" ", "_") if kind == "scientists" else name
                if not (root / f"lang/{LANG}/{folder}/{fname}.html").exists():
                    bad[kind] += 1
                    broken[kind][name] += 1
                    if full:
                        print(f"  БИТАЯ  {f.parent.name}/{d.get('id')} · {kind}: {name}")

    print(f"сайт: {root}")
    for kind in kinds:
        print(f"{kind:12} всего ссылок {total[kind]:>3} · битых {bad[kind]:>3}")
    for kind in kinds:
        if broken[kind]:
            print(f"\nнесуществующие {kind} (сколько уроков ссылается):")
            for name, n in broken[kind].most_common():
                print(f"   {n:>2}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
