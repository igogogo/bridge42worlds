"""Двойная кодировка в общих файлах: проверка и починка.

Откуда берётся. Файл в UTF-8 дописывают через PowerShell (`Set-Content`, `>`, `Out-File`)
без явной кодировки: байты читаются как cp1252, снова кодируются в UTF-8, и «обучение»
превращается в «Ð¾Ð±ÑƒÑ‡ÐµÐ½Ð¸Ðµ». В редакторе это ещё читается, в терминале уже нет,
а замечает следующий — через день. Доску команды так ломали дважды за сутки.

Вызывается из pre-commit (`--check`), поэтому проверка дешёвая: только текстовые файлы
репозитория, без lang/ и служебных папок.

    python tools/fix_encoding.py --check     # только сказать, где сломано (код 1 при находке)
    python tools/fix_encoding.py --fix       # починить обратным преобразованием
    python tools/fix_encoding.py --fix ФАЙЛ  # починить один файл

Чинится не всё: обратное преобразование работает, если строку целиком удаётся прочитать
как cp1252. Строки со знаками вне cp1252 (× → и подобные) не поддаются — такие файлы
проще собрать заново из последнего целого коммита, о чём скрипт и сообщает.
"""
import io
import os
import sys

SKIP_DIRS = {".git", "lang", "node_modules", "reports_theory", ".venv", "temp", "__pycache__"}
EXT = {".md", ".txt", ".json", ".html", ".js", ".css", ".py"}

# Верные признаки двойной кодировки: так выглядят частые русские буквы и тире.
MARKERS = ("Ð°", "Ð¾", "Ð¸", "Ñ‚", "Ñ", "â€”", "â€™", "Â«", "Â»")


def looks_broken(text):
    return sum(1 for m in MARKERS if m in text) >= 2


def restore_line(s):
    """Обратное преобразование одной строки. None — если не поддалась."""
    try:
        out = s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    return out if not looks_broken(out) else None


SELF = os.path.basename(__file__)


def walk(root="."):
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in files:
            # себя не проверяем: образцы битого текста лежат здесь намеренно,
            # иначе скрипт находит «порчу» в собственных примерах и блокирует коммит
            if f == SELF:
                continue
            if os.path.splitext(f)[1].lower() in EXT:
                yield os.path.join(dirpath, f)


def scan(paths):
    hits = []
    for p in paths:
        try:
            t = io.open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if looks_broken(t):
            n = sum(1 for l in t.splitlines() if looks_broken(l))
            hits.append((p, n))
    return hits


def fix(path):
    t = io.open(path, encoding="utf-8-sig").read()      # -sig: BOM прилетает тем же путём
    lines = t.splitlines()
    done = stuck = 0
    for i, l in enumerate(lines):
        if not looks_broken(l):
            continue
        r = restore_line(l)
        if r is None:
            stuck += 1
        else:
            lines[i] = r
            done += 1
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return done, stuck


def main():
    args = sys.argv[1:]
    mode = "--check" if not args else args[0]
    targets = args[1:] or None

    paths = targets or list(walk("."))
    hits = scan(paths)

    if mode == "--check":
        for p, n in hits:
            print(f"  двойная кодировка: {p} ({n} строк)")
        return 1 if hits else 0

    if mode == "--fix":
        if not hits:
            print("нечего чинить")
            return 0
        for p, n in hits:
            done, stuck = fix(p)
            state = "починен" if not stuck else f"частично ({stuck} строк не поддались)"
            print(f"  {p}: {done} строк восстановлено — {state}")
            if stuck:
                print("     не поддавшиеся строки проще взять из последнего целого коммита:")
                print(f"     git log --oneline -- {p}   →   git show <коммит>:{p}")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
