# -*- coding: utf-8 -*-
"""Отметка о проверке панели: кто проверил, когда, что нашёл и что поправил.

Владелец 06.09: «подпиши обе модели на вкладке verdict». Подпись должна быть ПРАВДОЙ на
каждую выкладку, а не общим словом о порядке работы: вердикт пишет DeepSeek при каждом
обновлении, а проверяет его Fable — отдельным запуском и не всегда. Поэтому проверка
кладётся в данные и привязывается к штампу пересчёта: если после отметки данные пересчитали,
панель честно скажет, что новый вердикт ещё не проверен.

Запись:
    python review.py --model claude-fable-5-1 --findings 3 --edits 5 \
        --note "две формулировки уточнены, одна ссылка снята"

Читает и пишет только data/enso/latest.json (ключ summary.review).
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
LATEST = ROOT / "latest.json"


def main():
    ap = argparse.ArgumentParser(description="отметить проверку панели перед выкладкой")
    ap.add_argument("--model", default="claude-fable-5-1", help="кто проверял")
    ap.add_argument("--findings", type=int, default=0, help="сколько нашлось расхождений")
    ap.add_argument("--edits", type=int, default=0, help="сколько формулировок поправлено")
    ap.add_argument("--note", default="", help="одна строка: что именно")
    ap.add_argument("--blocking", action="store_true", help="есть то, что мешает выкладке")
    ap.add_argument("--clear", action="store_true", help="снять отметку")
    a = ap.parse_args()

    d = json.loads(LATEST.read_text(encoding="utf-8"))
    sm = d.get("summary") or {}
    if a.clear:
        sm.pop("review", None)
        print("отметка снята")
    else:
        sm["review"] = {
            "model": a.model,
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            # ШТАМП ПЕРЕСЧЁТА — ЯДРО ЧЕСТНОСТИ. Панель сравнивает его со своим текущим:
            # разошлись — значит вердикт с тех пор переписан и проверка к нему не относится.
            "stamp": d.get("stamp"),
            "data": d.get("generated"),
            "findings": a.findings,
            "edits": a.edits,
            "blocking": bool(a.blocking),
            "note": a.note[:200],
        }
        print("отмечено:", sm["review"]["model"], sm["review"]["at"],
              f"· находок {a.findings} · правок {a.edits}" + (" · ЕСТЬ БЛОКИРУЮЩЕЕ" if a.blocking else ""))
    d["summary"] = sm
    LATEST.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    try:                                                         # в журнал прогонов (вкладка Ops)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ops as OPSLOG
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        OPSLOG.record_run("review", now, now, "cleared" if a.clear else ("blocking" if a.blocking else "ok"),
                          note=a.note[:120], stamp=d.get("stamp"), findings=a.findings, edits=a.edits, model=a.model)
    except Exception as e:                                       # noqa: BLE001
        print("журнал прогонов не обновлён:", str(e)[:100])
    return 0


if __name__ == "__main__":
    sys.exit(main())
