#!/usr/bin/env python3
"""Двойная кодировка в общих файлах: находит и чинит.

Симптом — «Ð¾Ð±ÑƒÑ‡ÐµÐ½Ð¸Ðµ» вместо «обучение». Так выглядит текст, который один раз
уже был UTF-8, был прочитан как однобайтовая кодировка и записан UTF-8 повторно.
Мы наступали на это дважды за сутки на одном и том же файле — доске команды.

Откуда берётся. PowerShell пишет `Set-Content`/`Add-Content` в СИСТЕМНОЙ кодировке,
если не указать `-Encoding utf8`. Дозапись строки в общий файл через них ломает весь
файл, и заметно это не сразу: в редакторе вроде читается, в терминале — уже нет.

Почему одной перекодировкой не обходится. Испорченный текст — это UTF-8-байты,
прочитанные как однобайтовая кодировка, но КАКАЯ именно, зависит от байта:
    0x80-0x9F  → в cp1252 это типографика (€ ’ “ —), но пять слотов там ПУСТЫ;
                 те же байты в latin-1 дают управляющие символы U+0080-U+009F.
Реальная строка содержит и то, и другое: «в» это D0 B2 (обе кодировки согласны),
а «с» это D1 81 — и 0x81 в cp1252 не определён. Поэтому encode('cp1252') падает
на первом же «с», а encode('latin-1') — на первом же тире. Обращаем посимвольно:
каждый символ той таблицей, которая его знает.

Запуск:
    python tools/fix_encoding.py --check   # только проверка, ненулевой код при находке
    python tools/fix_encoding.py           # починить
"""
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
# Общие файлы, которые правят из разных сессий разными инструментами.
TARGETS = ["задачи/*.md", "задачи/отчёты/*.md", "ПРАВИЛА-РАБОТЫ.md", "HANDOFF.md"]
MOJI = set("ÐÑÂÃâ€™“”")


def cyr(s):
    return sum(1 for c in s if "Ѐ" <= c <= "ӿ")


def to_bytes(s):
    """Обратно в байты: cp1252 там, где она знает символ, иначе latin-1."""
    out = bytearray()
    for ch in s:
        for codec in ("cp1252", "latin-1"):
            try:
                out += ch.encode(codec)
                break
            except UnicodeEncodeError:
                continue
        else:
            return None          # символ вне однобайтового диапазона — это не мохибейк
    return bytes(out)


def unmoji(line):
    # Каждая дозапись из PowerShell приносила ещё и свой BOM в середину файла.
    line = line.replace("﻿", "")
    if not any(ch in MOJI for ch in line):
        return line
    best = line
    for _ in range(4):           # часть строк испорчена дважды
        raw = to_bytes(best)
        if raw is None:
            break
        try:
            step = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            break
        if cyr(step) <= cyr(best) and not any(ch in MOJI for ch in step):
            break
        best = step
    return best if cyr(best) > cyr(line) else line


def files():
    for pat in TARGETS:
        yield from sorted(ROOT.glob(pat))


def main():
    check = "--check" in sys.argv
    broken = 0
    for p in files():
        try:
            src = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out = "\n".join(unmoji(l) for l in src.split("\n"))
        if out == src:
            continue
        n = sum(1 for a, b in zip(src.split("\n"), out.split("\n")) if a != b)
        rel = p.relative_to(ROOT).as_posix()
        broken += 1
        if check:
            print(f"❌ {rel}: {n} строк в двойной кодировке")
        else:
            p.write_text(out, encoding="utf-8")
            print(f"✅ {rel}: починено строк {n}")
    if check and broken:
        print("\nПочинить: python tools/fix_encoding.py")
        print("Причина обычно одна: дозапись через PowerShell без -Encoding utf8.")
        return 1
    if not broken:
        print("двойной кодировки не найдено")
    return 0


if __name__ == "__main__":
    sys.exit(main())
