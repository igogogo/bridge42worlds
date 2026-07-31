#!/usr/bin/env python3
"""Свод машинного расхода для дашборда: сколько запросов к модели ушло на корпус.

Зачем. Журнал `data/usage-log.jsonl` пишется по строке на каждый вызов модели
(common.py, с 2026-07-30) и уже вырос до тысяч строк. Сам он на сайт не попадает
и не должен: это внутренний файл, и .jsonl вообще не публикуется. Но сводка по
нему — самая честная «кухня», какая у нас есть: видно, что стоит за статьёй,
куда уходит основная работа (перевод, а не написание) и насколько выручает кэш.

Токены, не деньги. Пересчёт в валюту зависит от тарифа и меняется без нас, а
показывать читателю «мы потратили столько-то» — отдельное решение владельца.
Здесь только то, что измерено: вызовы, токены, доля попаданий в кэш.

Выход: data/usage-summary.json
    {"from": "2026-07-30", "to": "2026-07-31", "days": 2, "calls": 3649,
     "prompt": 9552817, "completion": 24067348, "cacheHit": ..., "cachePct": 27,
     "agents": [["translate", 1519, 3120411], ...], "models": [["deepseek-v4-pro", 2478], ...]}

Запуск: python tools/usage_summary.py   (хвостом run.py, см. DERIVED_ASSETS)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "usage-log.jsonl"
OUT = ROOT / "data" / "usage-summary.json"


def main():
    if not LOG.exists():
        print(f"ℹ️  {LOG.name} ещё нет — журнал пишется во время прогонов; сводку не трогаю")
        return 0
    calls = prompt = completion = hit = miss = 0
    first = last = ""
    agents = defaultdict(lambda: [0, 0])   # вызовы, completion-токены
    models = defaultdict(int)
    for line in LOG.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue   # оборванная строка в конце файла — прогон мог быть прерван
        calls += 1
        prompt += r.get("prompt", 0)
        completion += r.get("completion", 0)
        hit += r.get("cache_hit", 0)
        miss += r.get("cache_miss", 0)
        a = agents[r.get("agent") or "?"]
        a[0] += 1
        a[1] += r.get("completion", 0)
        models[r.get("model") or "?"] += 1
        ts = str(r.get("ts", ""))[:10]
        if ts:
            first = ts if not first or ts < first else first
            last = ts if ts > last else last
    if not calls:
        print("ℹ️  журнал пуст — сводку не трогаю")
        return 0
    days = 1
    if first and last:
        from datetime import date
        y1, m1, d1 = (int(x) for x in first.split("-"))
        y2, m2, d2 = (int(x) for x in last.split("-"))
        days = (date(y2, m2, d2) - date(y1, m1, d1)).days + 1
    out = {
        "from": first, "to": last, "days": days, "calls": calls,
        "prompt": prompt, "completion": completion,
        "cacheHit": hit, "cacheMiss": miss,
        "cachePct": round(100 * hit / (hit + miss)) if (hit + miss) else 0,
        "agents": sorted(([k, v[0], v[1]] for k, v in agents.items()), key=lambda x: -x[1])[:10],
        "models": sorted(models.items(), key=lambda x: -x[1]),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"✅ usage-summary.json: {calls} вызовов за {days} дн. ({first} → {last}), "
          f"{round((prompt + completion) / 1e6, 1)} млн токенов, кэш {out['cachePct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
