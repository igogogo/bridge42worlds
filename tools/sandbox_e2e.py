# -*- coding: utf-8 -*-
"""Сквозной прогон конвейера насыщения В ПЕСОЧНИЦЕ — все механизмы подряд.

Владелец 27.08: «тестирование пайплайна всего отдельно не забудь, аккуратно,
чтобы не мешать ничему; все механизмы погоняй».

Прогоняет цепочку на маленькой копии (b42-sandbox), которая не видит боевых
файлов на запись. Каждый шаг проверяется не «код не упал», а фактом в данных:
что реально изменилось и на сколько.

  1 harvest-target  целевая добыча law/math/constant/principle (2 статьи)
  2 harvest-stats   статистический проход (2 статьи)
  3 formula-link    опора константам/операторам из статей применений формул
  4 match           сверка кандидатов с реестром вектором
  5 distill         дистилляция кандидатов между собой
  6 group-grow      дорост изнутри групп (2 группы)
  7 field-support   полевой добор опоры вектором
  8 births --dry    рождения вхолостую (кто дорос) — без записи
  9 audit           аудит реестра и групп
 10 graph-export    данные графа

    python tools/sandbox_e2e.py            весь прогон
    python tools/sandbox_e2e.py --no-paid  только бесплатные шаги
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SBX = ROOT.parent / "b42-sandbox"
PY = sys.executable


def snap():
    """Снимок песочницы: по чему судим об изменениях."""
    s = {}
    hp = SBX / "data" / "concept-harvest.jsonl"
    rows = []
    if hp.exists():
        for line in hp.open(encoding="utf-8"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    s["кандидатов"] = len(rows)
    s["сверено"] = sum(1 for r in rows if r.get("matched"))
    s["с вектором"] = sum(1 for r in rows if r.get("vec"))
    s["готовы к рождению"] = sum(
        1 for r in rows if not r.get("matched") and not r.get("born")
        and len(r.get("articles") or []) >= 5)
    s["от групп"] = sum(1 for r in rows if r.get("src") == "group")
    lp = SBX / "data" / "concepts-live.json"
    if lp.exists():
        s["понятий"] = len(json.loads(lp.read_text(encoding="utf-8"))["concepts"])
    return s


def diff(a, b):
    out = []
    for k in b:
        d = b[k] - a.get(k, 0)
        if d:
            out.append(f"{k} {a.get(k, 0)}→{b[k]} ({d:+})")
    return "; ".join(out) or "без изменений в данных"


def step(n, title, cmd, paid=False, no_paid=False):
    if paid and no_paid:
        print(f"{n:>2}. {title:26s} ПРОПУЩЕН (платный)")
        return
    before = snap()
    t0 = time.time()
    r = subprocess.run([PY] + cmd.split(), cwd=SBX,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=3600,
                       env={**__import__("os").environ, "B42_LEAD": "1",
                            "PYTHONIOENCODING": "utf-8"})
    dt = time.time() - t0
    after = snap()
    mark = "✓" if r.returncode == 0 else "✗"
    print(f"{n:>2}. {mark} {title:26s} {dt:5.1f}с  {diff(before, after)}")
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        for line in tail:
            print(f"      {line[:110]}")
    else:
        # последняя содержательная строка вывода шага
        lines = [x for x in (r.stdout or "").strip().splitlines() if x.strip()]
        if lines:
            print(f"      {lines[-1][:110]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-paid", action="store_true")
    a = ap.parse_args()
    if not SBX.exists():
        print("песочницы нет: python tools/sandbox.py --make")
        return 1
    print(f"═══ СКВОЗНОЙ ПРОГОН В ПЕСОЧНИЦЕ ({SBX.name}) ═══")
    print(f"   старт: {snap()}")
    step(1, "целевая добыча", "tools/concept_harvest_target.py --run --cap 2",
         paid=True, no_paid=a.no_paid)
    step(2, "статистика", "tools/concept_harvest_target.py --run --cap 2 --profile stats",
         paid=True, no_paid=a.no_paid)
    step(3, "опора из формул", "tools/formula_anatomy.py --link")
    step(4, "сверка вектором", "tools/concept_harvest.py --match")
    step(5, "дистилляция", "tools/concept_harvest.py --distill")
    step(6, "дорост из групп", "tools/group_integrity.py --grow --limit 2",
         paid=True, no_paid=a.no_paid)
    step(7, "сверка вектором·2", "tools/concept_harvest.py --match")
    step(8, "полевой добор опоры", "tools/group_integrity.py --support")
    step(9, "рождения (вхолостую)", "tools/concept_cycle.py --budget 0 --dry")
    step(10, "аудит реестра", "tools/concepts_audit.py")
    step(11, "аудит групп", "tools/group_integrity.py --audit")
    step(12, "данные графа", "tools/concepts_graph_export.py")
    print(f"   финиш: {snap()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
