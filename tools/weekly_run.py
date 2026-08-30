# -*- coding: utf-8 -*-
"""Служебный прогон: то, что обходит ВЕСЬ корпус. Раз в неделю, отдельно.

Владелец 28.08: «обычный прогон должен быть простым и быстрым, точечным и
аккуратным; если надо что-то догонять или прогонять — это отдельные служебные
пайплайны пересчёта».

Так и разделено. tools/full_run.py делает ежедневную работу: забрал новые статьи,
достал из них понятия, дописал карточки, пересобрал затронутое, выложил. Всё, что
идёт по всему архиву и по всему реестру, живёт здесь и запускается тогда, когда
это осмысленно — раз в неделю или после большой перестройки.

ЧТО ЗДЕСЬ И ЗАЧЕМ:

  retag       переразметка ВСЕГО архива вектором. Нужна, когда реестр заметно
              изменился: новые понятия должны найти свои старые статьи.
  super       кластеризация реестра заново: области понятий пересобираются.
  vecnb       соседи по вектору для всех понятий разом.
  gnames      имена и пояснения всех областей.
  weave       связи знанием: обход реестра запросами к модели.
  g-grow      дорост областей — чего в области не хватает по скелету.
  f-support   опора формул по всему реестру.
  mentions-ru упоминания понятий по всему архиву.
  highlight   подсветка терминов во всех статьях, три уровня.
  tr-formulas перевод анатомий формул.
  html --force полная пересборка сайта: после переразметки меняются все страницы.

ЗАПУСКАЕТСЯ ТОЛЬКО РУКАМИ. Владелец 28.08: «отдельный пайплайн вручную, чтобы
стартовать, когда переедем на VPS; пока подготовь и задокументируй, запускать
будем сами — пока всё точечно». Ни в расписании, ни в ежедневном прогоне его нет
и быть не должно: он тратит часы и деньги, и решение потратить их принимает
человек.

КОГДА ЕГО ЗАПУСКАТЬ. Главный признак — реестр понятий заметно изменился, и старые
статьи об этом не знают: родились новые понятия, прошло слияние двойников,
переписаны карточки. Тогда переразметка находит новым понятиям их старые статьи,
кластеризация пересобирает области, а полная пересборка разносит это по страницам.
Пока таких изменений нет, гнать его незачем — ежедневный прогон уже сделал всё,
что касается новых статей.

Каждый шаг помнится (data/weekly-state.json): прогон можно оборвать и продолжить.

    python tools/weekly_run.py              весь служебный круг
    python tools/weekly_run.py --only retag,super
    python tools/weekly_run.py --no-publish
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import full_run as F  # noqa: E402

PY = F.PY

# Шаг → команда. Порядок важен: разметка перед кластеризацией, кластеризация
# перед именами областей, связи перед экспортом графа.
STEPS = [
    ("retag", [PY, "tools/retag_hub.py", "--thr", "0.50", "--margin", "0.12"], 4 * 3600),
    ("apply", [PY, "tools/wave5_apply.py", "--apply"], 3600),
    ("g-grow", [PY, "tools/group_integrity.py", "--grow"], 3600),
    ("f-support", [PY, "tools/group_integrity.py", "--support"], 3600),
    ("super", None, 2 * 3600),          # особый: готовит вход, см. ниже
    ("live-2", [PY, "tools/wave5_apply.py", "--live-only"], 1800),
    ("vecnb", [PY, "tools/vector_neighbors.py", "--apply"], 1800),
    ("gnames", [PY, "tools/group_names.py", "--run", "--force-peak"], 3600),
    ("weave", [PY, "tools/link_weaving.py", "--all", "--limit", "600", "--apply"], 4 * 3600),
    ("live-3", [PY, "tools/wave5_apply.py", "--live-only"], 1800),
    ("tr-formulas", [PY, "tools/cards_translate_ru.py", "--formulas", "--force-peak"], 4 * 3600),
    ("graph", [PY, "tools/concepts_graph_export.py"], 1800),
    ("mentions-ru", [PY, "tools/mentions_ru.py"], 4 * 3600),
    ("highlight", [PY, "tools/highlight_concepts.py",
                   "--tiers", "simple,popular,advanced"], 6 * 3600),
    ("pages-c", [PY, "concepts_pages.py"], 3600),
    ("pages-f", [PY, "formulas_pages.py"], 3600),
    ("html-force", [PY, "run.py", "html", "--force"], 8 * 3600),
    ("cloud-d1", [PY, "cloudflare/concepts_sync.py"], 4 * 3600),
    ("cloud-vec", [PY, "tools/concepts_to_vectorize.py", "--apply"], 2 * 3600),
    ("audit", [PY, "tools/concepts_audit.py"], 1800),
    ("gaudit", [PY, "tools/group_integrity.py", "--audit"], 1800),
    ("links", [PY, "tools/link_check.py"], 1800),
]


def main():
    ap = argparse.ArgumentParser(description="Служебный недельный прогон")
    ap.add_argument("--only", help="только эти шаги через запятую")
    ap.add_argument("--no-publish", action="store_true")
    # Языки полной пересборки. По умолчанию ru,en — этого хватает, когда служебный
    # прогон идёт за переразметкой: понятия языко-независимы. Но правки САМОГО
    # ТЕКСТА (следы перевода: тире, литеральные переносы) живут в каждом языке
    # своей копией, и там нужны все пять — иначе испанский и французский останутся
    # со старыми страницами до следующего такого же прогона.
    ap.add_argument("--langs", default="ru,en",
                    help="языки полной пересборки, через запятую; all — все пять")
    a = ap.parse_args()

    # Своё состояние: недельный прогон не должен путаться с ежедневным.
    F.STATE = ROOT / "data" / "weekly-state.json"
    F.FULL = True                      # здесь недельные шаги не пропускаются
    only = {s.strip() for s in (a.only or "").split(",") if s.strip()}
    env = {} if a.langs.strip().lower() == "all" else {"B42_LANGS": a.langs}
    if a.no_publish:
        env["B42_NO_PUBLISH"] = "1"

    F.log("═══ СЛУЖЕБНЫЙ ПРОГОН: пересчёт по всему корпусу ═══")
    st = F.state()
    st.setdefault("run_id", F.time.strftime("%Y-%m-%d %H:%M"))
    st.setdefault("started", st["run_id"])
    st["plan"] = [s for s, _, _ in STEPS if not only or s in only]
    st["days"] = []
    F.save(st)

    for step, cmd, timeout in STEPS:
        if only and step not in only:
            continue
        if step == "super":
            # Супер живёт в соседнем дереве и ест свой формат реестра — готовим вход.
            F.prepare_super_input()
            F.run("super", [PY, "concepts_super.py", "--embed",
                            "--reg", "data/concepts-v4.json", "--name-supers"],
                  timeout=timeout, cwd=ROOT.parent / "b42-ml", soft=True)
            continue
        F.run(step, cmd, timeout=timeout,
              env=(env or None) if step.startswith("html") else None,
              soft=step in ("g-grow", "f-support", "tr-formulas", "mentions-ru",
                            "highlight", "audit", "gaudit", "links", "vecnb",
                            "gnames", "weave"))
    F.log("═══ СЛУЖЕБНЫЙ ПРОГОН ЗАВЕРШЁН ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
