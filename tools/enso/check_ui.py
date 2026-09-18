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
J. Производные слои: ни один не собран раньше разбора, рядом с которым показан.
K. Дубликаты величин: одно и то же число, лежащее в нескольких файлах, всюду одинаково.
L. Застрявшие источники: отвечает без ошибки, но данные не двигаются дольше двенадцати дней.
M. Один ряд — один последний день во всех файлах (кроме тех, о ком уже сказало L).
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
    "cities.py": "cities.json", "fires.py": "fires.json", "water.py": "water.json", "futures.py": "futures.json",
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

# J. ПРОИЗВОДНЫЙ СЛОЙ НЕ МОЖЕТ БЫТЬ СТАРШЕ РАЗБОРА, РЯДОМ С КОТОРЫМ ОН ПОКАЗАН (17.09).
# Каждый из этих файлов читает latest.json и считает своё поверх. Собранный раньше разбора,
# он показывает вчерашние числа рядом с сегодняшними, и заметить это можно только глазами:
# журнальных рядов у них нет, они сами себе источник. Владелец и заметил — «на Standing out
# +2.69, хотя у нас уже 2.96».
DERIVED = ["outliers.json", "stats.json", "zones-flow.json", "phase.json", "agent-state.json"]
try:
    _cur = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    _stamp = str(_cur.get("stamp") or "")[:16]
    for _f in DERIVED:
        try:
            _b = str(json.loads((DATA / _f).read_text(encoding="utf-8")).get("built") or "")[:16]
        except Exception:                                        # noqa: BLE001
            bad.append(f"J derived layer unreadable: {_f}")
            continue
        if not _b:
            warn.append(f"J {_f}: no build stamp, cannot tell whether it matches the assessment")
            continue
        # У части слоёв штамп без времени («2026-09-17»): сравнивать его со строкой
        # «2026-09-17 07:15» побуквенно значит объявлять сегодняшний слой вчерашним.
        _cmp = _stamp[:len(_b)] if len(_b) < len(_stamp) else _stamp
        if _b < _cmp:
            bad.append(f"J {_f} was built {_b}, before the assessment {_stamp}: it shows older numbers beside newer ones")
except Exception as e:                                           # noqa: BLE001
    warn.append(f"J derived layers not checked: {str(e)[:70]}")

from numfmt import r2   # noqa: E402  одно округление на всех (17.09)

# K. ОДНА ВЕЛИЧИНА — ОДНО ЧИСЛО ВО ВСЕХ ФАЙЛАХ (17.09).
#
# Сверка показателей в обходе сравнивает то, что показано на ЭКРАНЕ и названо журнальным ключом.
# Но производные слои сами себе источник: они переписывают числа разбора к себе и ключей не
# называют. Сцена «кто выбивается» так и показала +2.69 рядом со сценами, где стоит +2.72, —
# и никакая экранная сверка этого поймать не могла.
#
# Здесь перечислены ВЕЛИЧИНЫ, которые лежат больше чем в одном файле, и места, где они лежат.
# Список явный: он и есть тот самый реестр дубликатов, которого не хватало. Появился новый слой,
# переписавший чужое число, — строка сюда, иначе расхождение опять будет некому заметить.
#
# Сравниваем с допуском по САМОЙ ГРУБОЙ из записанных точностей: слой может держать два знака
# там, где разбор держит три, и это не расхождение, а выбор точности.
def _dig(x):
    s = repr(float(x))
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def _row(doc, key):
    for r in (doc.get("rows") or []):
        if r.get("key") == key:
            return r
    return {}


def _at(doc, path):
    cur = doc
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


try:
    _D = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    _OU = json.loads((DATA / "outliers.json").read_text(encoding="utf-8"))
    _ZF = json.loads((DATA / "zones-flow.json").read_text(encoding="utf-8"))
    _PH = json.loads((DATA / "phase.json").read_text(encoding="utf-8"))
    DUP = [
        # (что это, (значение А, откуда А), (значение Б, откуда Б))
        ("Niño 3.4, 30-day mean", _row(_OU, "sst_nino34").get("anom"), "outliers",
         _at(_D, ["nino34", "current30"]), "latest.nino34.current30"),
        ("world ocean, 30-day mean", _row(_OU, "sst_world").get("anom"), "outliers",
         _at(_D, ["watch", "sst_world", "level30", "anom"]), "latest.watch.sst_world.level30"),
        ("land+ocean, 30-day mean", _row(_OU, "t2_world").get("anom"), "outliers",
         _at(_D, ["watch", "t2_world", "level30", "anom"]), "latest.watch.t2_world.level30"),
        ("Niño 3, weekly", _row(_OU, "zone_n3a").get("anom"), "outliers",
         _at(_D, ["noaa", "latest", "n3a"]), "latest.noaa.latest.n3a"),
        ("Niño 4, weekly", _at(_ZF, ["now", "values", "n4"]), "zones-flow",
         _at(_D, ["noaa", "latest", "n4a"]), "latest.noaa.latest.n4a"),
        ("Niño 3.4, weekly", _at(_ZF, ["now", "values", "n34"]), "zones-flow",
         _at(_D, ["noaa", "latest", "n34a"]), "latest.noaa.latest.n34a"),
        ("Niño 3, weekly (zones)", _at(_ZF, ["now", "values", "n3"]), "zones-flow",
         _at(_D, ["noaa", "latest", "n3a"]), "latest.noaa.latest.n3a"),
        ("Niño 1+2, weekly", _at(_ZF, ["now", "values", "n12"]), "zones-flow",
         _at(_D, ["noaa", "latest", "n12a"]), "latest.noaa.latest.n12a"),
        ("coupling score", _at(_PH, ["coupling", "score"]), "phase",
         _at(_D, ["air", "coupling", "score"]), "latest.air.coupling.score"),
        ("coupling, of how many", _at(_PH, ["coupling", "of"]), "phase",
         _at(_D, ["air", "coupling", "of"]), "latest.air.coupling.of"),
    ]
    for _what, _a, _pa, _b, _pb in DUP:
        if _a is None or _b is None:
            warn.append(f"K {_what}: missing in {_pa if _a is None else _pb}, cannot compare")
            continue
        _nd = min(_dig(_a), _dig(_b))
        # БЕЗ ДОПУСКА. Вчера здесь стоял допуск в один шаг разряда — «2.715 честно пишется то
        # как 2.71, то как 2.72». Но читатель видит на одной панели 2.71 и 2.72 и не обязан
        # знать, что это одно число. Значит, округлять все обязаны одним способом (numfmt.r2,
        # как Math.round у панели), а проверка сравнивает строго — на общей точности, тем же
        # округлением (проверка Fable 17.09).
        if r2(_a, _nd) != r2(_b, _nd):
            bad.append(f"K {_what}: {_pa} has {_a}, {_pb} has {_b} — the same quantity, two numbers")
    # дата тоже величина: слой, стоящий на другой неделе, покажет другое число
    _zd, _nd2 = _at(_ZF, ["now", "date"]), _at(_D, ["noaa", "date"])
    if _zd and _nd2 and _zd != _nd2:
        bad.append(f"K weekly date: zones-flow stands at {_zd}, the assessment at {_nd2}")
except Exception as e:                                           # noqa: BLE001
    warn.append(f"K duplicated quantities not checked: {str(e)[:80]}")

# L. ИСТОЧНИК ОТВЕЧАЕТ, НО НЕ ПРИНОСИТ НОВОГО (17.09). «Свежий» в таблице источников до сих пор
# значило «ответил»: забор прошёл, ошибки нет, галочка зелёная. А climatereanalyzer в это время
# три недели отдавал один и тот же последний день по суточному океану — и панель молчала.
# Отставание данных — не то же самое, что отказ связи, и называть это надо отдельно.
STUCK_DAYS = 12                      # дольше этого «ещё не обновили» перестаёт быть объяснением
try:
    _ops = json.loads((DATA / "ops.json").read_text(encoding="utf-8"))
    for _s in (_ops.get("sources") or []):
        _bd = _s.get("behind_days")
        if isinstance(_bd, int) and _bd > STUCK_DAYS and not _s.get("error"):
            warn.append("L {k}: answers without error, but its data has not moved for {d} days (to {t}) — "
                        "the source has stopped, not the fetch".format(
                            k=_s.get("key"), d=_bd, t=_s.get("data_to")))
except Exception as e:                                           # noqa: BLE001
    warn.append(f"L stuck sources not checked: {str(e)[:70]}")

# M. ОДИН РЯД — ОДИН ПОСЛЕДНИЙ ДЕНЬ ВО ВСЕХ ФАЙЛАХ (17.09).
#
# Правило K сравнивает ЗНАЧЕНИЯ у перечисленных вручную пар. Это ловит расхождение арифметики,
# но не ловит расхождение ВРЕМЕНИ: файл может держать то же число, просто позавчерашнее. Здесь
# наоборот — обходим все файлы разом и смотрим, до какого дня доведён каждый ряд. Так и нашлась
# остановка суточного океана: на всех сценах 15 сентября, на «Long term» — 30 августа.
#
# Ряд, отставший из-за ЗАСТРЯВШЕГО ИСТОЧНИКА, здесь молчит: о нём уже сказало правило L, и
# повторять одно и то же двумя голосами значит приучить не читать ни один.
try:
    _files = {}
    for _n in ("latest", "planet", "outliers", "fresh"):
        try:
            _files[_n] = json.loads((DATA / f"{_n}.json").read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            _files[_n] = {}
    _where = {}                                                  # ряд -> {файл: последний день}
    for _k, _v in ((_files["latest"].get("watch") or {})).items():
        _where.setdefault(_k, {})["latest.watch"] = _v.get("last_date")
    for _k, _v in ((_files["planet"].get("temperature") or {})).items():
        if isinstance(_v, dict) and (_v.get("last") or {}).get("date"):
            _where.setdefault(_k, {})["planet"] = (_v.get("last") or {}).get("date")
    for _r in (_files["outliers"].get("rows") or []):
        if _r.get("key") and _r.get("date"):
            _where.setdefault(_r["key"], {})["outliers"] = _r["date"]
    for _k, _v in ((_files["fresh"].get("series") or {})).items():
        _where.setdefault(_k, {})["fresh"] = _v.get("last_date")
    # какие ряды уже объявлены застрявшими правилом L — о них здесь молчим
    _stuck = set()
    try:
        for _s in (json.loads((DATA / "ops.json").read_text(encoding="utf-8")).get("sources") or []):
            if isinstance(_s.get("behind_days"), int) and _s["behind_days"] > STUCK_DAYS:
                _stuck.add(_s.get("key"))
    except Exception:                                            # noqa: BLE001
        pass
    for _k, _m in sorted(_where.items()):
        _ds = {str(v)[:10] for v in _m.values() if v}
        if len(_ds) > 1 and _k not in _stuck:
            bad.append("M {k}: the same series ends on different days — {w}".format(
                k=_k, w=", ".join(f"{f} {str(d)[:10]}" for f, d in sorted(_m.items()) if d)))
except Exception as e:                                           # noqa: BLE001
    warn.append(f"M series dates not checked: {str(e)[:70]}")

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
