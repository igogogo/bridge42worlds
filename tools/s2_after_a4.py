# -*- coding: utf-8 -*-
"""Дособрать Semantic Scholar, когда освободится ключ.

Рождения понятий валидируют каждое имя запросом в S2 (сито «не фантом ли»),
а лимит там — один запрос в секунду НА КЛЮЧ. Пустить сборщик рядом значит
получить 429 и в цепочке, и в сборе. Поэтому ждём маркер «A4 ЗАВЕРШЁН» и
только потом идём: авторы (29 613 записей по сотне за запрос — минуты),
хвост пакетного прохода и граф цитирований.

После сбора сразу пересчитываем карту наших авторов и вписываем цитируемость
в индексы — иначе данные лежат в файлах, а на страницах их нет.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
LOG = ROOT / "data" / "s2-after.log"
A4LOG = ROOT / "data" / "a4.log"


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    log("ждём финиша A4 (ключ S2 занят валидацией рождений)…")
    while True:
        try:
            if "A4 ЗАВЕРШЁН" in A4LOG.read_text(encoding="utf-8", errors="ignore"):
                break
        except FileNotFoundError:
            pass
        time.sleep(120)
    log("A4 завершён — идём в Semantic Scholar")
    # Порядок: сначала всё, что видно на страницах, потом пятичасовой граф
    # цитирований. Он идёт последним намеренно — своей страницы у него пока нет,
    # это материал для будущей аналитики, и ставить его перед картой авторов
    # значит отдать ему всю ночь, а утром показать страницы авторов без цифр.
    for title, cmd, t in (
        ("сбор S2 (статьи и авторы)", [PY, "tools/s2_collect.py", "--skip-graph"],
         6 * 3600),
        ("карта авторов", [PY, "tools/s2_author_map.py"], 1800),
        ("цитируемость в индексы", [PY, "tools/enrich_index_cites.py"], 1800),
        ("граф цитирований", [PY, "tools/s2_collect.py", "--only-graph"], 8 * 3600),
    ):
        log(f"▶ {title}")
        try:
            r = subprocess.run(cmd, cwd=ROOT, timeout=t)
            log(("✓ " if r.returncode == 0 else "✗ ") + title)
        except subprocess.TimeoutExpired:
            log("✗ " + title + " (таймаут)")
    log("═══ S2 ЗАВЕРШЁН ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
