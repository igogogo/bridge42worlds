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
G. Источники: у каждого ключа sources.SOURCES есть подпись в sources.LABELS.
H. Данные: ни одного NaN/Infinity — браузерный JSON.parse такого не разберёт.
I. Раскладка и показатели: отчёт ночного обхода сцен (check_layout.py) — находки, сверка
   журнальных рядов (один ключ — одно число везде) и возраст самого отчёта.
Выход: список расхождений; код возврата 1, если есть блокирующие (A, C, D, F, G, H, I).
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

# D2. ЕЖЕДНЕВНЫЙ СЛОЙ ВЫКЛАДЫВАЕТСЯ ЦЕЛИКОМ. Трижды — 06.09, 10.09, 15.09 — обнаруживалось одно
# и то же: сборщик кладёт свежий файл, а выкладка его не отправляет, и на сайте он меняется
# только с полным прогоном, то есть когда придётся. Правило C ловит обратную сторону (файл
# грузится панелью, но не выкладывается); эта ловит свою: скрипт в ночной обёртке пишет файл,
# а файла нет в FRESH_FILES.
DAILY_OUT = {
    "cities.py": "cities.json", "fires.py": "fires.json", "water.py": "water.json",
    "ice_snow.py": "ice-snow.json", "glaciers.py": "glaciers.json", "precip.py": "precip.json",
    "zones_flow.py": "zones-flow.json", "outliers.py": "outliers.json",
    "phase.py": "phase.json",
    "agent_state.py": "agent-state.json", "stats_layer.py": "stats.json",
    "check_layout.py": "layout-check.json",
}
fresh = set(PUB.FRESH_FILES)
for scr in sorted(set(re.findall(r"-u (\w+\.py)", ps1))):
    out = DAILY_OUT.get(scr)
    if out and ("data/enso/" + out) not in fresh:
        bad.append(f"D the daily wrapper rebuilds {out} but it is not in publish.FRESH_FILES")

# E. свежесть
BY_HAND = {"neighbours.json", "models-ref.json", "chain-ref.json"}
today = date.today()
for f in sorted(DATA.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:                                       # noqa: BLE001
        bad.append(f"E unreadable json: {f.name}: {str(e)[:60]}"); continue
    if not isinstance(d, dict):
        continue
    # ИСТОРИЯ НЕ ПРОТУХАЕТ. Разрезы прошлых событий (sections-1982 и прочие) собираются один
    # раз и намеренно кэшируются: в них закрытое прошлое, которое не изменится. Правило
    # свежести жаловалось на них каждый день и приучало не читать собственные предупреждения.
    if re.match(r"^sections-(19|20)\d{2}\.json$", f.name):
        continue
    # СПРАВОЧНИК, НАПИСАННЫЙ РУКОЙ, ТОЖЕ НЕ ПРОТУХАЕТ (17.09). neighbours.json — список
    # родственных проектов с их лицензиями, проверенными у источника; он меняется, когда мы
    # его пересматриваем, а не каждые сутки. Правило свежести девять дней подряд называло его
    # несвежим, и это ровно тот шум, от которого перестают читать собственные предупреждения.
    # Список ЯВНЫЙ: молчать по одной фразе в примечании файла нельзя — опечатка заглушила бы
    # настоящую поломку.
    if f.name in BY_HAND:
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

# H. НИ ОДНОГО NaN В ДАННЫХ ПАНЕЛИ (09.09: один NaN в radiance.json от сборщика — и вкладка
# Satellite мертва на проде: браузерный JSON.parse падает там, где питон читает молча).
DATA = ROOT / "data" / "enso"
for f in sorted(DATA.glob("*.json")):
    try:
        t = f.read_text(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        continue
    if re.search(r'(?<![\"\w])(NaN|-?Infinity)(?![\"\w])', t):
        bad.append(f"H {f.name}: NaN/Infinity — браузер такой JSON не разберёт (publish.py чинит, но источник надо править)")

# I. ОБХОД РАСКЛАДКИ (владелец 16.09: «сделай такой обход постоянной проверкой»). Сам обход
# живёт в браузере и идёт ночью — tools/enso/check_layout.py; здесь читается его отчёт, чтобы
# ОДНА команда по-прежнему отвечала на вопрос «панель цела или нет». Без этого проверка осталась
# бы строкой в ночном логе, которую никто не открывает, — а такая проверка всё равно что нет.
LY = DATA / "layout-check.json"
try:
    ly = json.loads(LY.read_text(encoding="utf-8"))
except Exception:                                                # noqa: BLE001
    ly = None
if ly is None:
    warn.append("I layout walk has never run here: python tools/enso/check_layout.py")
elif ly.get("status") == "skipped":
    # на машине нет браузера — это не поломка панели, а отсутствие инструмента
    warn.append(f"I layout walk skipped: {ly.get('why')}")
elif ly.get("status") != "ok":
    bad.append(f"I layout walk did not finish: {ly.get('why')}")
else:
    for f in (ly.get("findings") or [])[:12]:
        bad.append("I layout {t} at {w} px · {scene} · {p} · {x}".format(
            t=f.get("t"), w=f.get("width"), scene=str(f.get("scene"))[:26],
            p=str(f.get("p"))[:34], x=str(f.get("x"))[:60]))
    # СВЕРКА ПОКАЗАТЕЛЕЙ (17.09). Тот же обход по дороге собирает, какой журнальный ряд где
    # показан: один ключ обязан давать одно число везде. Расхождение — это либо ссылка карточки
    # не на свой ряд (нашли три таких), либо два разных вычисления одного и того же.
    kp = ly.get("kpi") or {}
    for x in (kp.get("out_of_sync") or [])[:8]:
        vals = " | ".join("%s: %s" % (v.get("v"), ", ".join(v.get("scenes") or [])[:40]) for v in (x.get("values") or []))
        bad.append("I indicator %s (%s) shows different numbers — %s" % (x.get("key"), str(x.get("title"))[:40], vals))
    ns = kp.get("not_shown") or []
    if ns:
        warn.append("I %d journal rows are on no card: %s" % (len(ns), ", ".join(y["key"] for y in ns[:10])))
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(ly.get("built") or ""))
    if m:
        age = (date.today() - date.fromisoformat(m.group(1))).days
        if age > 3:
            warn.append(f"I layout walk is {age} days old (built {m.group(1)}): it only guards what it has seen")

print(f"check_ui: {len(bad)} blocking, {len(warn)} warnings")
for b in bad:
    print("  !!", b)
for w in warn:
    print("  ..", w)
sys.exit(1 if bad else 0)
