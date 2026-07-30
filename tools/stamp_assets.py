#!/usr/bin/env python3
"""Версии в адресах css/js на статических страницах.

Шаблоны в templates/ подставляют `?v=$asset_ver` сами, а страницы в корне
(корневая, учебник, курс, справочники) написаны руками — и версия там либо
отсутствовала совсем, либо стояла рукописным числом, которое не менялось от
правок кода (`icons.js?v=2` при десятке правок icons.js).

Чем это плохо: сайт отдаётся с `immutable` на год, и без версии в адресе
у вернувшегося читателя навсегда остаётся старый файл — его не исправит даже
Ctrl+R. В живом Chrome с /learn.html поднимался css на 34 КБ младше того, что
сервер отдаёт сейчас (замер 2026-07-30).

Версия = первые 10 знаков md5 самого файла: поменялся файл — поменялся адрес,
не поменялся — читатель не качает лишнего.

Запуск: python tools/stamp_assets.py [--check]
"""
import hashlib
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
# Страницы в корне: те, что не проходят через templates/.
PAGES = sorted(p for p in ROOT.glob("*.html") if p.name != "status.html")
ASSET_RE = re.compile(r'(?P<pre>(?:href|src)=")(?P<path>/(?:css|js)/[A-Za-z0-9_\-.]+\.(?:css|js))'
                      r'(?:\?[^"]*)?(?P<post>")')

_hash_cache = {}


def asset_version(rel):
    if rel in _hash_cache:
        return _hash_cache[rel]
    f = ROOT / rel.lstrip("/")
    try:
        v = hashlib.md5(f.read_bytes()).hexdigest()[:10]
    except OSError:
        v = ""
    _hash_cache[rel] = v
    return v


def stamp(text):
    def sub(m):
        v = asset_version(m.group("path"))
        if not v:
            return m.group(0)          # файла нет — не выдумываем версию
        return f'{m.group("pre")}{m.group("path")}?v={v}{m.group("post")}'
    return ASSET_RE.sub(sub, text)


def main():
    check = "--check" in sys.argv
    changed = []
    for p in PAGES:
        try:
            src = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out = stamp(src)
        if out == src:
            continue
        changed.append(p.name)
        if not check:
            p.write_text(out, encoding="utf-8")
    if check:
        if changed:
            print("без актуальной версии: " + ", ".join(changed))
            return 1
        print("версии в адресах актуальны")
        return 0
    print(f"проставлены версии: {len(changed)} страниц" + (f" ({', '.join(changed)})" if changed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
