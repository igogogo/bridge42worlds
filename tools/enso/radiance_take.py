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
DST = Path(__file__).resolve().parents[2] / "data" / "enso" / "radiance.json"


def complete(d):
    try:
        cr = d["sources"]["n21_cris"]
        years = set()
        for ser in cr["series"].values():
            for v in ser.values():
                if isinstance(v, dict):
                    years |= set(v.keys())
        return bool(cr.get("detectors")) and len(years) >= 3
    except Exception:                                            # noqa: BLE001
        return False


def main():
    t0 = time.time()
    status, note = "ok", ""
    if not SRC.exists():
        status, note = "partial", "source file missing"
    else:
        try:
            d = json.loads(SRC.read_text(encoding="utf-8"))
            if complete(d):
                old = json.loads(DST.read_text(encoding="utf-8")).get("updated") if DST.exists() else None
                if old != d.get("updated"):
                    shutil.copy(SRC, DST)
                    note = f"taken: updated {d.get('updated')}, {len(d.get('alerts') or [])} alert(s)"
                else:
                    note = f"unchanged: {d.get('updated')}"
            else:
                status, note = "partial", f"source incomplete (updated {d.get('updated')}), kept previous copy"
        except Exception as e:                                   # noqa: BLE001
            status, note = "partial", f"unreadable: {str(e)[:80]}"
    print("radiance:", status, note)
    try:
        import ops as OPSLOG
        OPSLOG.record_run("radiance", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, note=note)
    except Exception:                                            # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
