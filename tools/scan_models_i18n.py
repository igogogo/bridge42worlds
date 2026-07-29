"""Полнота словарей стендов: подписи ползунков, осей и сцены живут в data/theory/<модель>.json.

Именно их читатель видит на самом стенде — сердце урока. Проверяем, все ли четыре языка есть
и не остался ли внутри русский.
"""
import json
import re
from pathlib import Path

CYR = re.compile(r"[А-Яа-яЁё]")
LANGS = ["ru", "en", "es", "ar"]
SKIP = {"constants.json", "course-thermodynamics.json", "reference.json", "mathkit.json",
        "hypotheses.json", "discoveries.json", "frontier.json"}

rows = []
for f in sorted(Path("data/theory").glob("*.json")):
    if f.name in SKIP:
        continue
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    i18n = d.get("i18n")
    if not isinstance(i18n, dict) or "ru" not in i18n:
        continue
    ru_keys = set(i18n["ru"])
    row = {"file": f.name, "ru": len(ru_keys)}
    for L in LANGS[1:]:
        if L not in i18n:
            row[L] = "нет словаря"
            continue
        missing = ru_keys - set(i18n[L])
        cyr = [k for k, v in i18n[L].items() if isinstance(v, str) and CYR.search(v)]
        row[L] = f"нет {len(missing)}, русских {len(cyr)}"
    rows.append(row)

print(f"{'модель':26} {'ru':>4}  en / es / ar")
for r in rows:
    print(f"{r['file']:26} {r['ru']:>4}  {r['en']} | {r['es']} | {r['ar']}")
print("\nмоделей:", len(rows))
