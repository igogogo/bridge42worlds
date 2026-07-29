"""Показывает места, где в переводе русский перемешан с формулой — их правят руками."""
import json
import re
from pathlib import Path

CYR = re.compile(r"[А-Яа-яЁё]")
TEXT = re.compile(r"\\(?:text|mathrm)\{([^{}]*)\}")
ROOT = Path("data/theory/courses")


def rest(s):
    return TEXT.sub("", re.sub(r"\$[^$]*\$", "", s))


def walk(node, path, lang, file):
    if isinstance(node, str):
        if CYR.search(node) and CYR.search(rest(node)):
            print(f"{file} [{lang}] {path}\n    {node[:220]}")
        return
    if isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", lang, file)
    elif isinstance(node, dict):
        for k, v in node.items():
            walk(v, f"{path}.{k}", lang, file)


for f in sorted(ROOT.rglob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    for L in ("en", "es", "ar"):
        if L in d:
            walk(d[L], "", L, f.relative_to(ROOT))
