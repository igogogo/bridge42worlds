# -*- coding: utf-8 -*-
"""Забрать radiance.json у внешнего сборщика сырых спутниковых гранул (C:\\CL\\radiance).

Владелец 07.09: «они сами будут обновлять, мы просто берём результат». Копируем файл в
data/enso/radiance.json только если он полный: есть детекторы и ряды за несколько лет.
В середине их пересборки файл бывает частичным (один день, без аналогов) — такой не берём,
на панели остаётся прошлая полная копия. Запись в журнал прогонов.
"""
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

SRC = Path(r"C:\CL\radiance\data\radiance.json")
SRC_FULL = Path(r"C:\CL\radiance\data\radiance-full.json")
DST = Path(__file__).resolve().parents[2] / "data" / "enso" / "radiance.json"


def series_years(d, inst="n21_cris"):
    """Годы, за которые у прибора есть суточный ряд конвекции над Niño 3.4."""
    try:
        cf = d["sources"][inst]["series"]["nino34_A"]["conv_frac"]
        return {str(y) for y, v in cf.items() if isinstance(v, (dict, list)) and v}
    except Exception:                                            # noqa: BLE001
        return set()


def complete(d):
    """Полный файл — это детекторы И годы сравнения в рядах.

    Прежняя проверка считала «годами» любые ключи внутри series и пропустила v6: сборщик
    09.09 разделил выход на компактный radiance.json (только текущий год в series) и
    radiance-full.json (все годы). Компактный прошёл как полный, и панель потеряла наложения
    2023–2025 на сцене Convection и сравнение приборов «2026 против 2023–2025».
    """
    try:
        cr = d["sources"]["n21_cris"]
        win = set(str(y) for y in ((d.get("window") or {}).get("years") or []))
        return bool(cr.get("detectors")) and len(series_years(d) & win) >= 3
    except Exception:                                            # noqa: BLE001
        return False


def from_full(full):
    """Собрать файл панели из полного: ряды только за годы окна, остальное как есть.

    Полный файл держит 24 года AIRS (1,5 МБ); панели для наложений нужны годы окна
    (2023–2026), как в файлах v4–v5. Траектории и эпохи берём целиком: они годовые.
    Так панель не зависит от того, что сборщик решит оставить в компактном файле.
    """
    d = json.loads(json.dumps(full))
    win = set(str(y) for y in ((d.get("window") or {}).get("years") or []))
    for inst, src in (d.get("sources") or {}).items():
        ser = src.get("series") if isinstance(src, dict) else None
        if not isinstance(ser, dict):
            continue
        for node, metrics in ser.items():
            if not isinstance(metrics, dict):
                continue
            for mk, years in metrics.items():
                if isinstance(years, dict):
                    metrics[mk] = {y: v for y, v in years.items() if (y in win) or (not y.isdigit())}
    return d


def _clean(o):
    import math
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def _log(t0, status, note):
    try:
        import ops as OPSLOG
        OPSLOG.record_run("radiance", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, note=note)
    except Exception:                                            # noqa: BLE001
        pass


def _write(d, t0, note_prefix):
    """Записать очищенный файл, если он новее лежащего; NaN/Infinity → null (09.09: один NaN
    ронял разбор в браузере и всю вкладку Satellite)."""
    d = _clean(d)
    raw = json.dumps(d, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    old = json.loads(DST.read_text(encoding="utf-8")).get("updated") if DST.exists() else None
    if old == d.get("updated") and DST.stat().st_size == len(raw.encode("utf-8")):
        return "ok", f"unchanged: {d.get('updated')}"
    DST.write_text(raw, encoding="utf-8")
    return "ok", f"{note_prefix}: updated {d.get('updated')}, series years {sorted(series_years(d))}, {len(raw) // 1024} KB"


def main():
    t0 = time.time()
    status, note = "ok", ""
    if not SRC.exists() and not SRC_FULL.exists():
        status, note = "partial", "source file missing"
    else:
        try:
            d = json.loads(SRC.read_text(encoding="utf-8")) if SRC.exists() else {}
            if complete(d):
                status, note = _write(d, t0, "taken")
            elif SRC_FULL.exists():
                full = json.loads(SRC_FULL.read_text(encoding="utf-8"))
                if len(series_years(full)) >= 3:
                    status, note = _write(from_full(full), t0, "built from radiance-full")
                else:
                    status, note = "partial", f"both files incomplete (updated {d.get('updated')}), kept previous copy"
            else:
                status, note = "partial", f"source incomplete (updated {d.get('updated')}), kept previous copy"
        except Exception as e:                                   # noqa: BLE001
            status, note = "partial", f"unreadable: {str(e)[:80]}"
    print("radiance:", status, note)
    _log(t0, status, note)


if __name__ == "__main__":
    main()
