# -*- coding: utf-8 -*-
"""IRI/CCSR ENSO plume — прогнозы двух десятков моделей, вытащенные из SVG.

IRI не отдаёт таблицу моделей файлом: страница рисует её через
https://ensoforecast.iri.columbia.edu/figure4_plot/<год>/<месяц> как SVG из matplotlib.
В таком SVG нет текста — подписи набраны глифами шрифта, но идентификатор глифа
это код символа со сдвигом 29 (glyph 0x13 = '0'), а минус — отдельный глиф U+0C9C.
Так читаются оси, легенда и заголовок; линии моделей — обычные <path>, их цвет и
штрих совпадают с образцом в легенде. Дальше — геометрия: y-пиксель → °C по тикам
оси, x-пиксель → сезон по подписям.

Месяц в адресе — месяц ВЫПУСКА минус один? Нет: figure4_plot/2026/7 — плюм,
опубликованный в августе (заголовок «from Aug 2026»); первая точка на оси — наблюдённый
сезон MJJ, вторая — наблюдённый июль. Поэтому здесь месяц адреса называется «start».
"""
import io
import re
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# Хост сменился 03.09.2026: ensoforecast2 перестал резолвиться, страница IRI ссылается на
# ensoforecast.iri.columbia.edu. Тот же путь figure4_plot/<год>/<месяц выпуска − 1>.
URL = "https://ensoforecast.iri.columbia.edu/figure4_plot/{y}/{m}"
ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"   # данные дашборда живут в data/enso/, код в tools/enso/
DIR = ROOT / "iri"


def fetch(y, m, timeout=40):
    DIR.mkdir(parents=True, exist_ok=True)
    p = DIR / f"plume_{y}_{m:02d}.svg"
    req = urllib.request.Request(URL.format(y=y, m=m), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if b"<svg" not in data[:2000]:
        raise ValueError("не SVG")
    p.write_bytes(data)
    return p


def _decode(body):
    out = ""
    for mm in re.finditer(r'xlink:href="#[A-Za-z]+-([0-9a-f]+)"', body):
        code = int(mm.group(1), 16)
        if code == 0x0C9C:
            out += "-"
        elif code < 0x100:
            out += chr(code + 29)
        else:
            out += "?"
    return out


def _texts(s):
    """matplotlib пишет подпись HTML-комментарием перед глифами: <!-- UKMO -->.
    Берём его; декодирование глифов остаётся запасным путём."""
    out = []
    for m in re.finditer(r'<g id="(text_\d+)">(.*?)</g>\s*</g>', s, re.S):
        body = m.group(2)
        tr = re.search(r'translate\(([-\d.]+)\s+([-\d.]+)\)', body)
        cm = re.search(r'<!--\s*(.*?)\s*-->', body, re.S)
        text = cm.group(1).strip() if cm else _decode(body).strip()
        out.append({"id": m.group(1), "text": text,
                    "x": float(tr.group(1)) if tr else None, "y": float(tr.group(2)) if tr else None,
                    "rot": "rotate(-90)" in body})
    return out


def _paths(s):
    """Все path с абсолютными координатами: (stroke, dash, [(x,y),...])."""
    out = []
    for m in re.finditer(r'<path([^>]*)/>', s, re.S):
        attrs = m.group(1)
        d = re.search(r'\bd="([^"]+)"', attrs)
        if not d:
            continue
        st = re.search(r'style="([^"]*)"', attrs)
        style = st.group(1) if st else ""
        stroke = re.search(r'stroke:\s*(#[0-9a-fA-F]{6})', style)
        dash = re.search(r'stroke-dasharray:\s*([^;]+)', style)
        nums = re.findall(r'[-\d.]+', d.group(1))
        pts = [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums) - 1, 2)]
        out.append({"stroke": stroke.group(1).lower() if stroke else None,
                    "dash": (dash.group(1).strip() if dash else "solid"),
                    "pts": pts, "width": re.search(r'stroke-width:\s*([\d.]+)', style)})
    return out


def parse(path):
    s = io.open(path, encoding="utf-8", errors="replace").read()
    T = _texts(s)
    P = _paths(s)
    title = next((t["text"] for t in T if "Predictions" in t["text"]), "")
    m = re.search(r"from\s+([A-Za-z]{3})\s+(\d{4})", title)
    issued = f"{m.group(1)} {m.group(2)}" if m else ""

    # оси: подписи сезонов внизу (y ≈ одинаковые, самые нижние), значения слева
    xt = [t for t in T if t["y"] and t["y"] > 480 and t["x"] and 60 < t["x"] < 800 and t["text"]]
    xt.sort(key=lambda t: t["x"])
    seasons = [t["text"] for t in xt]
    xs = [t["x"] for t in xt]
    yt = []
    for t in T:
        if t["x"] and t["x"] < 60 and re.fullmatch(r"-?\d+\.\d", t["text"]):
            yt.append((float(t["text"]), t["y"]))
    yt.sort()
    yv = np.array([v for v, _ in yt]); yp = np.array([p for _, p in yt])
    a, b = np.polyfit(yp, yv, 1)                    # °C = a*y_px + b

    def to_val(ypx): return float(a * ypx + b)
    # подписи сезонов стоят под тиками; x тика = x текста + половина ширины текста.
    # Надёжнее взять сами тики оси: короткие вертикальные path на нижней оси.
    # тики оси X — маркеры <use x=".."> внутри групп xtick_N, ровно по одному на подпись
    ticks = []
    for m in re.finditer(r'<g id="xtick_\d+">(.*?)</g>\s*</g>', s, re.S):
        u = re.search(r'<use[^>]*\bx="([-\d.]+)"', m.group(1))
        if u:
            ticks.append(float(u.group(1)))
    if len(ticks) == len(seasons):
        xs = ticks

    def to_season(xpx):
        return int(np.argmin([abs(xpx - x) for x in xs]))

    # Палитра у IRI всего из семи цветов на 28 моделей, поэтому по цвету линии не
    # различить. Зато matplotlib рисует линии данных в том же порядке, в каком выводит
    # легенду: тонкие линии моделей ↔ тонкие образцы, толстые средние ↔ толстые.
    # Связываем по порядку и проверяем совпадение цвета — расхождение значит,
    # что IRI поменял рисунок, и парсер обязан об этом сказать, а не молчать.
    i_leg = s.find('id="legend_1"')
    def groups(chunk):
        out = []
        for m in re.finditer(r'<g id="(line2d_\d+)">(.*?)</g>', chunk, re.S):
            p = re.search(r'<path d="([^"]+)"[^>]*style="([^"]*)"', m.group(2))
            if not p:
                continue
            nums = re.findall(r'[-\d.]+', p.group(1))
            pts = [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums) - 1, 2)]
            st = re.search(r'stroke:\s*(#[0-9a-fA-F]{6})', p.group(2))
            w = re.search(r'stroke-width:\s*([\d.]+)', p.group(2))
            out.append({"id": m.group(1), "pts": pts, "stroke": st.group(1).lower() if st else None,
                        "thick": bool(w and float(w.group(1)) >= 3)})
        return out
    data = [g for g in groups(s[:i_leg]) if g["stroke"] and len(g["pts"]) >= 3
            and all(60 < x < 800 for x, _ in g["pts"])]
    handles = groups(s[i_leg:])
    leg = [t for t in T if t["x"] and t["x"] > 800]
    leg.sort(key=lambda t: t["y"])
    # подписи и образцы идут парами в одном порядке
    pairs = list(zip(handles, leg))
    models = {}
    section = None
    thin_data = [g for g in data if not g["thick"]]
    thick_data = [g for g in data if g["thick"]]
    ti = 0
    warnings = []
    for h, t in pairs:
        name = t["text"].strip()
        if not name:
            continue
        if name.endswith(":"):
            section = "dyn" if name.startswith("DYN") else "stat"
            continue
        if not h["stroke"]:
            continue
        if h["thick"]:
            src = next((g for g in thick_data if g["stroke"] == h["stroke"]), None)
            sec = "avg"
        else:
            src = thin_data[ti] if ti < len(thin_data) else None
            ti += 1
            sec = section
            if src and src["stroke"] != h["stroke"]:
                warnings.append(f"{name}: цвет линии {src['stroke']} не совпал с легендой {h['stroke']}")
        vals = [None] * len(seasons)
        if src:
            for x, y in src["pts"]:
                vals[to_season(x)] = round(to_val(y), 2)
        models[name] = {"stroke": h["stroke"], "section": sec, "values": vals if src else None}
    if ti != len(thin_data):
        warnings.append(f"линий моделей {len(thin_data)}, подписей {ti} — рисунок изменился")
    # наблюдённые точки: маркеры (короткие замкнутые path) чёрного цвета у первых сезонов
    obs = {}
    for p in P:
        if p["stroke"] in ("#000000",) and 3 <= len(p["pts"]) <= 12:
            xc = np.mean([x for x, _ in p["pts"]]); yc = np.mean([y for _, y in p["pts"]])
            if 60 < xc < 800 and 40 < yc < 480:
                obs[seasons[to_season(xc)]] = round(to_val(yc), 2)
    return {"file": Path(path).name, "issued": issued, "title": title, "seasons": seasons,
            "y_axis": [float(v) for v in yv], "observed": obs, "warnings": warnings,
            "models": {k: {"section": v["section"], "values": v["values"]} for k, v in models.items()}}


def summarize(plume):
    """Сводка: средние, разброс по сезонам, кто выше/ниже всех."""
    ms = {k: v for k, v in plume["models"].items() if v["values"] and v["section"] in ("dyn", "stat")}
    seasons = plume["seasons"]
    table = []
    for i, sname in enumerate(seasons):
        vals = [(k, v["values"][i]) for k, v in ms.items() if v["values"][i] is not None]
        if not vals:
            continue
        arr = np.array([x for _, x in vals])
        table.append({"season": sname, "n": len(vals), "mean": round(float(arr.mean()), 2),
                      "min": round(float(arr.min()), 2), "max": round(float(arr.max()), 2),
                      "sd": round(float(arr.std(ddof=1)), 2) if len(arr) > 1 else 0.0,
                      "top": max(vals, key=lambda t: t[1])[0], "bottom": min(vals, key=lambda t: t[1])[0]})
    return {"issued": plume["issued"], "n_models": len(ms), "seasons": table,
            "combined": next((v["values"] for k, v in plume["models"].items() if "COMBINED" in k), None),
            "dyn_avg": next((v["values"] for k, v in plume["models"].items() if k.startswith("DYN Average")), None),
            "stat_avg": next((v["values"] for k, v in plume["models"].items() if k.startswith("STAT Average")), None)}


def _peak(vals):
    v = [x for x in (vals or []) if x is not None]
    return max(v) if v else None


def compare(cur, prev):
    """Пересмотр от выпуска к выпуску: у каждой модели — сдвиг пика и сдвиг ближайшего
    общего сезона. «Ломающиеся» модели — те, что переписывают себя сильнее всех."""
    if not prev:
        return None
    common = [s for s in cur["seasons"] if s in prev["seasons"] and "OBS" not in s]
    ci = {s: cur["seasons"].index(s) for s in common}
    pi = {s: prev["seasons"].index(s) for s in common}
    rows = []
    for name, m in cur["models"].items():
        if m["section"] not in ("dyn", "stat") or not m["values"] or name not in prev["models"]:
            continue
        pv = prev["models"][name]["values"]
        if not pv:
            continue
        pk_c, pk_p = _peak(m["values"]), _peak(pv)
        # первый общий сезон, где обе стороны дали число
        first = next((s for s in common if m["values"][ci[s]] is not None and pv[pi[s]] is not None), None)
        d_first = (m["values"][ci[first]] - pv[pi[first]]) if first else None
        rows.append({"model": name, "section": m["section"],
                     "peak_prev": pk_p, "peak_cur": pk_c,
                     "d_peak": round(pk_c - pk_p, 2) if pk_c is not None and pk_p is not None else None,
                     "first_season": first, "d_first": round(d_first, 2) if d_first is not None else None})
    rows.sort(key=lambda r: -(abs(r["d_peak"]) if r["d_peak"] is not None else 0))
    cp, pp = _peak(next((v["values"] for k, v in cur["models"].items() if "COMBINED" in k), None)), \
             _peak(next((v["values"] for k, v in prev["models"].items() if "COMBINED" in k), None))
    ups = sum(1 for r in rows if r["d_peak"] is not None and r["d_peak"] > 0.1)
    downs = sum(1 for r in rows if r["d_peak"] is not None and r["d_peak"] < -0.1)
    return {"prev_issued": prev["issued"], "rows": rows,
            "combined_peak_prev": pp, "combined_peak_cur": cp,
            "n_up": ups, "n_down": downs, "n": len(rows)}


def against_observed(cur, observed_weekly, observed_monthly=None):
    """Какие модели уже ниже реальности на текущий сезон. Реальность — последний
    недельный Niño 3.4 NOAA (точка), прогноз — трёхмесячное среднее, поэтому сравнение
    честное только как «модель ниже уже достигнутого уровня»."""
    seasons = cur["seasons"]
    first = next((s for s in seasons if "OBS" not in s and any(
        (m["values"] or [None] * 12)[seasons.index(s)] is not None for m in cur["models"].values())), None)
    if first is None:
        return None
    i = seasons.index(first)
    vals = [(k, m["values"][i]) for k, m in cur["models"].items()
            if m["section"] in ("dyn", "stat") and m["values"] and m["values"][i] is not None]
    below = sorted([k for k, v in vals if v < observed_weekly])
    above = sorted([k for k, v in vals if v >= observed_weekly])
    arr = np.array([v for _, v in vals])
    return {"season": first, "observed_weekly": observed_weekly, "observed_monthly": observed_monthly,
            "n": len(vals), "below": below, "above": above,
            "share_below": round(100 * len(below) / max(1, len(vals))),
            "mean": round(float(arr.mean()), 2), "max": round(float(arr.max()), 2),
            "min": round(float(arr.min()), 2), "sd": round(float(arr.std(ddof=1)), 2) if len(arr) > 1 else 0.0,
            "reality_above_all": bool(observed_weekly > arr.max()),
            "reality_above_mean_sd": bool(observed_weekly > arr.mean() + arr.std(ddof=1)) if len(arr) > 1 else False}


def latest_issues(today=None, keep=12):
    """Забрать текущий и два прошлых выпуска. Адрес выпуска = месяц публикации минус один
    (августовский плюм лежит под 2026/7). Сентябрьский появится ~19 сентября под 2026/8;
    пока его нет — сервер отдаёт не-SVG, и мы просто остаёмся на августовском."""
    today = today or date.today()
    got, seen = [], set()
    y, m = today.year, today.month
    tries = 0
    while len(got) < keep and tries < keep + 4:
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        tries += 1
        p = DIR / f"plume_{y}_{m:02d}.svg"
        try:
            if not p.exists() or len(got) == 0:      # свежайший всегда перепроверяем
                p = fetch(y, m)
        except Exception:                            # noqa: BLE001
            if not p.exists():
                continue
        # Сервер IRI на ещё не вышедший месяц отдаёт ПРЕДЫДУЩИЙ плюм, а не ошибку.
        # Поэтому различаем выпуски по заголовку внутри SVG, а не по адресу.
        try:
            issued = parse(p)["issued"]
        except Exception:                            # noqa: BLE001
            continue
        if issued in seen:
            try:
                p.unlink()                           # файл-двойник под чужим именем не нужен
            except OSError:
                pass
            continue
        seen.add(issued)
        got.append(p)
    return got


def watch(observed_weekly, observed_monthly=None):
    files = latest_issues()
    if not files:
        return None
    issues = [parse(f) for f in files]
    cur = issues[0]
    prev = issues[1] if len(issues) > 1 else None
    out = {"issued": cur["issued"], "seasons": cur["seasons"], "n_models": len(
        [m for m in cur["models"].values() if m["section"] in ("dyn", "stat")]),
        "models": cur["models"], "summary": summarize(cur), "warnings": cur["warnings"],
        "revisions": compare(cur, prev), "against_observed": against_observed(cur, observed_weekly, observed_monthly),
        "history": [{"issued": i["issued"], "combined": next((v["values"] for k, v in i["models"].items() if "COMBINED" in k), None),
                     "seasons": i["seasons"]} for i in issues]}
    return out


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1:
        r = parse(Path(sys.argv[1]))
        for k, v in r["models"].items():
            print("%-16s %-4s %s" % (k, v["section"], v["values"]))
        print(json.dumps(summarize(r), ensure_ascii=False, indent=1)[:1500])
    else:
        w = watch(observed_weekly=2.6)
        print(json.dumps({k: w[k] for k in ("issued", "n_models", "against_observed", "warnings")}, ensure_ascii=False, indent=1))
        print("пересмотр:", json.dumps({k: w["revisions"][k] for k in ("prev_issued", "combined_peak_prev", "combined_peak_cur", "n_up", "n_down")}, ensure_ascii=False))
        for r in w["revisions"]["rows"][:6]:
            print("  ", r)
