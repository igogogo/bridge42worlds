#!/usr/bin/env python3
"""Страж молчаливых откатов — наш главный класс багов.

За два дня поймали восемь штук вида «внешне работает, внутри пусто»: словарь без ключа
падал на английский, валидатор возвращал непереведённое, turnstileOk отвечал true без
секрета, webp не конвертился, отбор возвращал ноль, тултип съедал клик, счётчик
накручивался, шаг конверсии жил не там.

Скрипт считает такие места и НЕ ДАЁТ ЧИСЛУ РАСТИ: базовая линия в data/silent-baseline.json,
при превышении — ненулевой код возврата. Это не запрет фолбэков: осознанный фолбэк
допустим, но он обязан оставлять след (лог, счётчик, пометка) — и тогда добавляется
в исключения ниже с причиной.

Запуск: python tools/silent_watch.py [--update-baseline]
"""
import glob
import io
import json
import re
import sys
from pathlib import Path

# Консоль Windows по умолчанию cp1251 — русский текст и галочки роняют скрипт
# на выводе, а не на работе. Ставим utf-8 сами, не полагаясь на PYTHONIOENCODING.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "data" / "silent-baseline.json"

PATTERNS = [
    (r"except\s*:\s*\n\s*pass", "except: pass"),
    (r"except\s+Exception\s*:\s*\n\s*pass", "except Exception: pass"),
    (r"catch\s*\([^)]*\)\s*\{\s*\}", "catch(e) {} — js"),
    (r"catch\s*\{\s*\}", "catch {} — js"),
    (r"\|\|\s*d\.ru\b", "|| d.ru — откат на русский"),
    (r"\.get\(lang,\s*[A-Z_]+\[[\"']en[\"']\]\)", "словарь без языка → en"),
    (r"return\s+scipop\b", "return scipop — непереведённое как перевод"),
]

# Осознанные фолбэки: путь → причина. Их считаем, но не штрафуем.
ALLOWED = {
    "js/likes.js": "хранилище может быть заблокировано (приватный режим) — реакции не критичны",
}


def scan():
    rows = []
    for f in (glob.glob("*.py") + glob.glob("js/*.js")
              + glob.glob("tools/*.py") + glob.glob("cloudflare/*.js")):
        try:
            s = io.open(ROOT / f, encoding="utf-8").read()
        except OSError:
            continue
        for pat, name in PATTERNS:
            for m in re.finditer(pat, s):
                rows.append({"file": f.replace("\\", "/"),
                             "line": s[:m.start()].count("\n") + 1,
                             "kind": name})
    return rows


def main():
    rows = scan()
    by_kind = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(f"{r['file']}:{r['line']}")
    total = len(rows)

    print(f"молчаливых откатов: {total}")
    for kind, places in sorted(by_kind.items(), key=lambda x: -len(x[1])):
        print(f"  {len(places):3}  {kind}")

    if "--update-baseline" in sys.argv:
        BASELINE.write_text(json.dumps({"total": total, "by_kind": {k: len(v) for k, v in by_kind.items()}},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nбазовая линия записана: {total}")
        return 0

    if BASELINE.exists():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        if total > base.get("total", total):
            print(f"\n❌ выросло: было {base['total']}, стало {total}. "
                  f"Осознанный фолбэк? Оставь след (лог/счётчик) и обнови базовую линию.")
            return 1
        if total < base.get("total", total):
            print(f"\n✅ убыло: было {base['total']}, стало {total} — обнови базовую линию.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
