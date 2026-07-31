#!/usr/bin/env python3
"""Сколько статей существует на каждом языке — маленький файл для дашборда.

Зачем. Первый вопрос любого, кому показываешь проект: «а на арабском сколько?»
Ответа не было нигде: KPI считает статьи по индексу ТЕКУЩЕГО языка, поэтому на
любой странице выходит одно и то же число, и разница между языками не видна.
А она есть и она важная: французский добавлен пятым и пока догоняет.

Почему отдельный файл, а не подсчёт на клиенте: индексы весят по 5-6 МБ, и чтобы
посчитать пять языков в браузере, пришлось бы скачать около тридцати мегабайт
ради девяти чисел. Здесь это чтение с диска и файл на несколько сотен байт.

Выход: data/lang-coverage.json
    {"base": "ru", "max": 2110,
     "langs": [{"lang": "ru", "articles": 2110, "full": 601, "express": 1509}, ...]}

Запуск: python tools/lang_coverage.py   (хвостом run.py, см. DERIVED_ASSETS)
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
LANGS = CONFIG.get("languages", ["ru"])
LANG_DIR = CONFIG.get("lang_dir", "lang")
OUT = ROOT / "data" / "lang-coverage.json"


def count(lang):
    """Считаем по индексу «популярного» тира: в нём ровно одна запись на статью.
    Нет индекса — язык объявлен в config, но ещё не собран; это не ошибка, это ноль."""
    path = ROOT / LANG_DIR / lang / "articles-index.json"
    if not path.exists():
        return None
    idx = json.loads(path.read_text(encoding="utf-8"))
    seen, express = set(), 0
    for a in idx:
        aid = a.get("id")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        if a.get("express"):
            express += 1
    return {"lang": lang, "articles": len(seen), "full": len(seen) - express, "express": express}


def main():
    rows = [r for r in (count(l) for l in LANGS) if r]
    if not rows:
        print("❌ ни одного собранного индекса — сначала сборка сайта")
        return 1
    out = {"base": LANGS[0], "max": max(r["articles"] for r in rows), "langs": rows}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("✅ lang-coverage.json: " + " · ".join(f"{r['lang']} {r['articles']}" for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
