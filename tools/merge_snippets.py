# -*- coding: utf-8 -*-
"""Вклеивает заготовки схем и моделей в общие файлы.

Зачем так. Когда тему пишут несколько агентов сразу, общий файл (js/figures.js, js/models.js)
становится узким местом: двое одновременно перезаписывают его целиком, и правка одного пропадает.
Поэтому каждый пишет СВОЮ заготовку — tools/_figs_<что-то>.js, tools/_model_<тема>.js, — а
сборка в общий файл делается один раз и последовательно, вот этим скриптом.

Что делает:
  · берёт все tools/_figs_*.js и вставляет их функции в js/figures.js перед закрытием модуля;
  · берёт все tools/_model_*.js и вставляет их в js/models.js туда же;
  · пропускает функции, которые в общем файле уже есть (повторный прогон безопасен);
  · после сборки прогоняет оба файла через node и печатает, что появилось.

Заготовки после сборки НЕ удаляет: пусть остаются в ветке до слияния — по ним видно, кто что писал.

    python tools/merge_snippets.py --check    что будет вклеено
    python tools/merge_snippets.py            вклеить
"""
import glob
import io
import re
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JOBS = [
    ("tools/_figs_*.js", "js/figures.js", r"F\.([A-Za-z][A-Za-z0-9]*)\s*=\s*function",
     "    global.B42Figures = F;"),
    ("tools/_model_*.js", "js/models.js", r"function\s+([A-Za-z][A-Za-z0-9]*Model)\s*\(",
     None),
]


def names(text, pattern):
    return [m.group(1) for m in re.finditer(pattern, text)]


def main():
    check = "--check" in sys.argv
    for pat, target, name_re, anchor in JOBS:
        files = sorted(glob.glob(pat))
        if not files:
            continue
        raw = io.open(target, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in raw else "\n"
        body = raw.replace("\r\n", "\n")
        have = set(names(body, name_re))
        added, chunks = [], []
        for f in files:
            piece = io.open(f, encoding="utf-8", newline="").read().replace("\r\n", "\n")
            new = [n for n in names(piece, name_re) if n not in have]
            if not new:
                print("  %-34s всё уже вклеено" % f)
                continue
            have.update(new)
            added += new
            chunks.append("\n    /* из %s */\n%s\n" % (f, piece.rstrip()))
        if not chunks:
            continue
        print("  %s → %s: %d функций (%s)" % (pat, target, len(added), ", ".join(added[:6]) +
                                              ("…" if len(added) > 6 else "")))
        if check:
            continue
        if anchor and anchor in body:
            body = body.replace(anchor, "".join(chunks) + anchor, 1)
        else:
            # у моделей своей опоры нет — вставляем перед последней строкой файла
            cut = body.rstrip().rfind("\n")
            body = body[:cut] + "\n" + "".join(chunks) + body[cut:]
        io.open(target, "w", encoding="utf-8", newline=nl).write(body)

    if not check:
        for t in ("js/figures.js", "js/models.js"):
            r = subprocess.run(["node", "--check", t], capture_output=True, text=True)
            print("  %s: %s" % (t, "разбирается" if r.returncode == 0 else "СЛОМАН — " + r.stderr[:200]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
