# -*- coding: utf-8 -*-
"""Общая запись прогона в data/pipeline-runs.json — тот файл, из которого рисуется /pipeline.html.

Владелец 06.09: «есть же страница для мониторинга пайплайнов» — и обновление панели шло
мимо неё, как до этого шёл прогон по теме. Формат один на всех: дневной и недельный
прогоны пишет tools/full_run.py, прогон по теме — works_run.py, обновление панели —
refresh.py. Род (kind) решает, какой строкой это ляжет на схему.

Сбой записи журнала не должен ронять прогон: он стоит строки в логе, а не работы.
"""
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "pipeline-runs.json"
_IDS = {}                                                        # род → id текущего прогона


def report(kind="topic", plan=None, done=None, current=None, steps=None,
           failed=None, finish=False, title="", label=None):
    """Заводит или дописывает запись прогона. Возвращает её id (он же ключ рода)."""
    try:
        runs = json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else []
    except Exception:                                            # noqa: BLE001
        runs = []
    if not isinstance(runs, list):
        runs = []
    rid = _IDS.get(kind)
    if rid is None:
        rid = (label or kind) + " " + datetime.now().strftime("%Y-%m-%d %H:%M")
        _IDS[kind] = rid
    rec = next((r for r in runs if r.get("id") == rid), None)
    if rec is None:
        rec = {"id": rid, "kind": kind, "days": [],
               "started": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "origin": os.environ.get("B42_RUN_ORIGIN") or "manual", "title": title}
        runs.append(rec)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if plan is not None:
        rec["plan"] = list(plan)
    if done is not None:
        rec["done"] = list(done)
    if steps is not None:
        rec["steps"] = dict(steps)
    if failed is not None:
        rec["failed"] = list(failed)
    if title:
        rec["title"] = title
    rec["current"] = None if finish else current
    rec["at"] = now
    if finish:
        rec["finished"] = now
    try:
        RUNS.write_text(json.dumps(runs[-30:], ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as e:
        print(f"  ⚠️ журнал прогонов не записан: {e}")
    return rid
