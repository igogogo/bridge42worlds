# -*- coding: utf-8 -*-
"""Ежедневный конвейер знаний: всё сегодняшнее — автоматом, не ручками.

Владелец 26.08: «смотри, чтобы всё было зафиксировано автоматами, а не просто
ручками сделано». Ночной прогон — разовый разгон по всему архиву; этот конвейер —
его ПОСТОЯННАЯ форма для потока новых статей. Шаг фабрики «knowledge» зовёт его
ежедневно; каждый под-шаг инкрементален (своё состояние, сделанное не повторяет),
поэтому обычный день — это десятки статей и копейки.

ПОРЯДОК И ЗАЧЕМ КАЖДЫЙ:

  s2         Semantic Scholar по новым статьям: цитирования, граф — state сборщика
  cycle      добыча понятий из новых статей (промпт с определением и якорями),
             сверка вектором, дистилляция, рождения (наши правила + Scholar-сито);
             рождение пишет вектор в матрицу и облако
  anatomy    анатомия новых основных форм формул (единицы, значения) + связка
  fullcards  развёрнутые записи новорождённым (гейт дешёвого окна сам решает)
  retag      переразметка статей на выросшем реестре (локально, минуты)
  apply      разметка в data.json + живой справочник (+рождённые)
  names      русские названия недостающим (инкрементально)
  mentions   русские якоря по ещё не якорённым статьям
  export     словари клиенту (concepts-names.json по языкам)
  pages      перегенерация /concepts/

Разметка текстов (highlight) и заливки в облако — уже свои шаги фабрики, здесь
не дублируются. Пересборку HTML делает фабрика после всех шагов, как всегда.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import ALL_LANGS  # noqa: E402
PY = sys.executable


def run(title, cmd, timeout=7200):
    print(f"▶ {title}")
    try:
        r = subprocess.run(cmd, timeout=timeout)
        ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
    print(("✓ " if ok else "✗ ") + title)
    return ok


def main():
    try:
        from tools.freeze import guard
        guard("конвейер знаний")
    except ImportError:
        pass
    run("Scholar: новые статьи", [PY, "tools/s2_collect.py"], timeout=14400)
    run("добыча и рождения", [PY, "tools/concept_cycle.py", "--budget", "80"])
    run("анатомия новых формул", [PY, "tools/formula_anatomy.py", "--run"])
    run("формы в системах единиц", [PY, "tools/formula_anatomy.py", "--systems"])
    run("связка формул с реестром", [PY, "tools/formula_anatomy.py", "--link"])
    run("рождения из формул", [PY, "tools/concept_cycle.py", "--budget", "0"])
    run("единицы → системы", [PY, "tools/unit_systems_seed.py", "--link-units"])
    run("записи новорождённым", [PY, "tools/concept_fullcards.py", "--run"])
    run("перевекторизация", [PY, "tools/concept_fullcards.py", "--revector"])
    run("переразметка", [PY, "tools/retag_hub.py", "--thr", "0.50", "--margin", "0.12"])
    run("в данные", [PY, "tools/wave5_apply.py", "--apply"])
    run("русские названия", [PY, "tools/concept_names_translate.py"])
    run("русские карточки понятий", [PY, "tools/cards_translate_ru.py", "--concepts"],
        timeout=14400)
    run("русские анатомии формул", [PY, "tools/cards_translate_ru.py", "--formulas"],
        timeout=14400)
    run("русские якоря", [PY, "tools/mentions_ru.py"], timeout=14400)
    run("Scholar → карта авторов", [PY, "tools/s2_author_map.py"], timeout=1800)
    run("цитируемость в индексы", [PY, "tools/enrich_index_cites.py"], timeout=1800)
    run("датасет файн-тюнинга", [PY, "tools/ft_dataset_export.py"], timeout=7200)
    run("данные графа понятий", [PY, "tools/concepts_graph_export.py"], timeout=1800)
    # словари клиенту
    live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))["concepts"]
    for lang in ALL_LANGS:
        out = {c: {"name": (v.get("names") or {}).get(lang)
                   or (v.get("names") or {}).get("en") or c.replace("_", " ")}
               for c, v in live.items()}
        (ROOT / f"lang/{lang}/data/concepts-names.json").write_text(
            json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("✓ словари клиенту")
    run("страницы понятий", [PY, "concepts_pages.py"])
    run("страницы формул", [PY, "formulas_pages.py"])
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
