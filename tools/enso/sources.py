# -*- coding: utf-8 -*-
"""Источники сторожевого дашборда: что тянем, откуда, как читаем.

Каждый источник забирается с браузерным User-Agent (без него climatereanalyzer
отвечает «Houston, we've had a problem»), кладётся в data/raw/<штамп>/ как есть,
и только потом разбирается. Сырое хранится дословно и с датой — если разбор
сломается через месяц, будет с чем сравнить.

При недоступности источника берётся последняя удачная копия, и это помечается:
дашборд обязан сказать, что данные несвежие, а не молча показать старое.
"""
import io
import json
import os
import re
import shutil
import time
import urllib.request
from datetime import datetime, date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"   # данные дашборда живут в data/enso/, код в tools/enso/
RAW = ROOT / "raw"
LAST = ROOT / "last_good"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# name -> (url, kind)
SOURCES = {
    "t2_world":   ("https://climatereanalyzer.org/clim/t2_daily/json/era5_world_t2_day.json", "cr_json"),
    "t2_nh":      ("https://climatereanalyzer.org/clim/t2_daily/json/era5_nh_t2_day.json", "cr_json"),
    "t2_sh":      ("https://climatereanalyzer.org/clim/t2_daily/json/era5_sh_t2_day.json", "cr_json"),
    "sst_world":  ("https://climatereanalyzer.org/clim/sst_daily/json_2clim/oisst2.1_world2_sst_day.json", "cr_json"),
    "sst_nino34": ("https://climatereanalyzer.org/clim/sst_daily/json_2clim/oisst2.1_nino3.4_sst_day.json", "cr_json"),
    "noaa_weekly": ("https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for", "noaa_weekly"),
    "oni":        ("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", "oni_txt"),
    "psl_nino34_monthly": ("https://psl.noaa.gov/data/correlation/nina34.anom.data", "psl_monthly"),
    # Продовольствие: единственный живой ряд без регистрации (ИСТОЧНИКИ.md, §4). CSV с шапкой
    # в четыре строки: Date, Food Price Index, Meat, Dairy, Cereals, Oils, Sugar; 2014-16 = 100.
    "fao_fpi": ("https://www.fao.org/media/docs/worldfoodsituationlibraries/default-document-library/"
                "food_price_indices_data.csv?download=true", "fao_csv"),
}

LABELS = {
    "t2_world": "Land+ocean, world (ERA5, 2 m)",
    "t2_nh": "Land+ocean, northern hemisphere (ERA5)",
    "t2_sh": "Land+ocean, southern hemisphere (ERA5)",
    "sst_world": "Ocean, 60°S–60°N (OISST)",
    "sst_nino34": "Niño 3.4, the El Niño focus (OISST)",
    "noaa_weekly": "NOAA weekly indices: Niño 1+2, 3, 3.4, 4",
    "oni": "ONI, NOAA official 3-month index",
    "psl_nino34_monthly": "Niño 3.4 monthly (ERSST v6, PSL)",
    "fao_fpi": "FAO Food Price Index and five groups (monthly)",
}


def fetch_all(timeout=40):
    """Тянет всё, что может; возвращает {name: (path, fresh: bool, error)}."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = RAW / stamp
    dest.mkdir(parents=True, exist_ok=True)
    LAST.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, (url, kind) in SOURCES.items():
        ext = ".json" if kind == "cr_json" else (".csv" if kind == "fao_csv" else ".txt")
        p = dest / (name + ext)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if kind == "cr_json":
                json.loads(data.decode("utf-8"))      # проверка, что это JSON, а не страница ошибки
            elif len(data) < 500:
                raise ValueError("слишком короткий ответ: %r" % data[:80])
            p.write_bytes(data)
            shutil.copy(p, LAST / (name + ext))
            out[name] = (LAST / (name + ext), True, "")
        except Exception as e:                       # noqa: BLE001 - любая сетевая беда
            lp = LAST / (name + ext)
            out[name] = (lp if lp.exists() else None, False, str(e)[:160])
    # пустой каталог штампа, если всё упало, не нужен
    if not any(p.exists() for p in dest.iterdir()):
        dest.rmdir()
    return out, stamp


# ------------------------------------------------------------------ разбор
def read_cr_json(path):
    """Ряды climatereanalyzer: {год: массив 366}, климатология 1991-2020, дата последнего дня."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    years, clim = {}, None
    for r in d:
        nm = r.get("name", "")
        arr = np.array([np.nan if v is None else v for v in r["data"]], float)
        if nm.isdigit():
            years[int(nm)] = arr
        elif nm == "1991-2020":
            clim = arr
    y_last = max(years)
    fin = np.where(np.isfinite(years[y_last]))[0]
    n = int(len(fin))
    last_idx = int(fin[-1]) if n else -1
    last_day = grid_index_to_date(y_last, last_idx) if n else None
    return {"years": years, "clim": clim, "last_year": y_last,
            "last_n": n, "last_idx": last_idx, "last_date": last_day}


def grid_index_to_date(year, idx):
    """Индекс в 366-дневной сетке ряда -> реальная дата. Сетка всегда содержит
    29 февраля (индекс 59); в невисокосный год эта ячейка пуста и её надо перешагнуть."""
    from datetime import timedelta
    import calendar
    if calendar.isleap(year) or idx < 59:
        return date(year, 1, 1) + timedelta(days=idx)
    return date(year, 1, 1) + timedelta(days=idx - 1)


def read_noaa_weekly(path):
    """Недельные SST и аномалии по четырём регионам Niño."""
    rows = []
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)", ln)
        if not m:
            continue
        dt = datetime.strptime(m.group(1), "%d%b%Y").date()
        nums = re.findall(r"-?\d+\.\d", m.group(2))
        if len(nums) < 8:
            continue
        v = list(map(float, nums[:8]))
        rows.append({"date": dt, "n12": v[0], "n12a": v[1], "n3": v[2], "n3a": v[3],
                     "n34": v[4], "n34a": v[5], "n4": v[6], "n4a": v[7]})
    return rows


def read_oni(path):
    """ONI из oni.ascii.txt: список (сезон, год, аномалия) по порядку, DJF..NDJ."""
    out = []
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        parts = ln.split()
        if len(parts) == 4 and re.fullmatch(r"[A-Z]{3}", parts[0]) and parts[1].isdigit():
            out.append((parts[0], int(parts[1]), float(parts[3])))
    return out


def read_psl_monthly(path):
    """Месячная аномалия Niño 3.4 (ERSST): {год: [12]}; -99.99 = нет данных."""
    out = {}
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        parts = ln.split()
        if len(parts) == 13 and re.fullmatch(r"\d{4}", parts[0]):
            vals = [float(x) for x in parts[1:]]
            out[int(parts[0])] = [np.nan if v < -90 else v for v in vals]
    return out


if __name__ == "__main__":
    res, stamp = fetch_all()
    for k, (p, fresh, err) in res.items():
        print("%-20s %s %s" % (k, "свежее" if fresh else "СТАРОЕ", err))


def read_fao(path):
    """FAO Food Price Index: {"months": ["1990-01", ...], "index": [...], "groups": {"Meat": [...], ...}}.
    Строки без числа в индексе пропускаем; последняя строка файла — последний вышедший месяц."""
    import csv
    months, index, groups = [], [], {"Meat": [], "Dairy": [], "Cereals": [], "Oils": [], "Sugar": []}
    with io.open(path, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    head = next((r for r in rows if r and r[0].strip() == "Date"), None)
    if not head:
        raise ValueError("FAO CSV: строка заголовка Date не найдена — формат изменился")
    col = {name.strip(): i for i, name in enumerate(head) if name.strip()}
    for r in rows:
        if not r or not re.match(r"^\d{4}-\d{2}$", (r[0] or "").strip()):
            continue
        try:
            v = float(r[col["Food Price Index"]])
        except (ValueError, IndexError, KeyError):
            continue
        months.append(r[0].strip()); index.append(v)
        for g in groups:
            try:
                groups[g].append(float(r[col[g]]))
            except (ValueError, IndexError, KeyError):
                groups[g].append(None)
    return {"months": months, "index": index, "groups": groups}
