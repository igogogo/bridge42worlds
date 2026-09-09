# -*- coding: utf-8 -*-
"""Проверка согласованности панели (владелец 07.09: «диагностика на консистентность и стандартизацию,
подготовиться к ежедневному обновлению»). Без сети, секунды. Что сверяет:

A. Термины: каждый data-term в js/enso.js и enso.html есть в glossary.json (иначе подсказка пустая).
B. Подсказки подменю: у каждого segBtn(view, key, …) есть T.subHelp['view/key'].
C. Файлы: каждый get('/data/enso/*.json') в загрузчике есть в publish.FILES и лежит на диске;
   каждый файл из FILES существует; FRESH_FILES ⊆ FILES.
D. Обёртка: каждый скрипт, который зовёт light_daily.ps1, существует и компилируется.
E. Свежесть данных: у каждого json в data/enso дата сборки (built/updated/stamp) — сколько дней назад.
F. Вкладки: каждый ключ T.tabs имеет tabHelp и ветку в render().
Выход: список расхождений; код возврата 1, если есть блокирующие (A, C, D, F).
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = (ROOT / "js" / "enso.js").read_text(encoding="utf-8")
HTML = (ROOT / "enso.html").read_text(encoding="utf-8")
DATA = ROOT / "data" / "enso"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish as PUB                                           # noqa: E402

bad, warn = [], []

# A. термины
gl = json.loads((DATA / "glossary.json").read_text(encoding="utf-8"))["en"]
terms = set(re.findall(r"data-term=\\?\"([a-z0-9_]+)\\?\"", JS + HTML))
terms |= set(re.findall(r"\b(?:term|ab|zone)\('([a-z0-9_]+)'", JS))
zones = {"nino12", "nino3", "nino34", "nino4"}
for t in sorted(terms):
    if t not in gl and t not in zones:
        bad.append(f"A term without glossary entry: {t}")

# B. подсказки подменю
sub = re.findall(r"segBtn\('([a-z]+)', '([a-z0-9_]+)'", JS)
helps = set(re.findall(r"'([a-z]+/[a-z0-9_]+)':", JS))
for v, k in sorted(set(sub)):
    if f"{v}/{k}" not in helps:
        warn.append(f"B sub-tab without subHelp: {v}/{k}")

# C. файлы
loads = re.findall(r"get\('/data/enso/([a-z0-9_.-]+\.json)'\)", JS)
files = set(PUB.FILES)
for f in loads:
    if f"data/enso/{f}" not in files:
        bad.append(f"C loaded by the panel but not in publish.FILES: {f}")
    if not (DATA / f).exists():
        bad.append(f"C loaded by the panel but missing on disk: {f}")
for f in PUB.FILES:
    if not (ROOT / f).exists():
        bad.append(f"C in publish.FILES but missing on disk: {f}")
for f in PUB.FRESH_FILES:
    if f not in files:
        bad.append(f"C in FRESH_FILES but not in FILES: {f}")

# D. обёртка
ps1 = (ROOT / "tools" / "enso" / "light_daily.ps1").read_text(encoding="utf-8")
for scr in sorted(set(re.findall(r"-u (\w+\.py)", ps1))):
    p = ROOT / "tools" / "enso" / scr
    if not p.exists():
        bad.append(f"D wrapper calls a missing script: {scr}")
    else:
        try:
            compile(p.read_text(encoding="utf-8"), scr, "exec")
        except SyntaxError as e:
            bad.append(f"D wrapper script does not compile: {scr}: {e}")

# E. свежесть
today = date.today()
for f in sorted(DATA.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:                                       # noqa: BLE001
        bad.append(f"E unreadable json: {f.name}: {str(e)[:60]}"); continue
    if not isinstance(d, dict):
        continue
    st = d.get("built") or d.get("updated") or d.get("stamp") or d.get("generated")
    if st:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", str(st))
        if m:
            age = (today - date.fromisoformat(m.group(1))).days
            if age > 7:
                warn.append(f"E {f.name}: built {m.group(1)}, {age} days ago")

# F. вкладки
tabs = re.search(r"tabs: \{([^}]*)\}", JS).group(1)
tab_keys = re.findall(r"(\w+): '", tabs)
help_block = re.search(r"tabHelp: \{(.*?)\n    \},", JS, re.S).group(1)
for k in tab_keys:
    if not re.search(rf"\b{k}:", help_block):
        warn.append(f"F tab without tabHelp: {k}")
    if not re.search(rf"S\.view === '{k}'", JS) and k not in ("state", "risks"):
        bad.append(f"F tab without a render branch: {k}")

# G. каждый источник имеет подпись (09.09: три новых ряда поясов без LABELS уронили лёгкий прогон)
try:
    import sources as SRC
    for k in SRC.SOURCES:
        if k not in SRC.LABELS:
            bad.append(f"G source without a label in sources.LABELS: {k}")
except Exception as e:                                           # noqa: BLE001
    warn.append(f"G sources.py did not import: {str(e)[:80]}")

print(f"check_ui: {len(bad)} blocking, {len(warn)} warnings")
for b in bad:
    print("  !!", b)
for w in warn:
    print("  ..", w)
sys.exit(1 if bad else 0)
