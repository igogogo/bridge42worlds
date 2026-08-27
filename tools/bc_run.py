# -*- coding: utf-8 -*-
"""Этапы B и C плана одной цепочкой — по «да» владельца 27.08 («пункты B C»).

ФАЗА B — карточки и языки (ждёт ДЕШЁВОЕ ОКНО DeepSeek, 19:30 по Кувейту:
массовые прогоны в пик стоят вдвое дороже, окно через ~2 часа):
  b-fullcards   полные записи 2006 понятиям без записи (~$3-5)
  b-tr-concepts русские переводы полных карточек (~$2-3)
  b-tr-formulas русские переводы анатомий формул (~$1)
  b-systems     формы в разных системах единиц (СИ/СГС/планковская, ~$0.3)

ФАЗА C — финальная разметка (ждёт МАРКЕР «A4 ЗАВЕРШЁН»: переразмечать надо
выросший реестр, а не сегодняшний):
  c-seed        посев 5 понятий-систем единиц (после births A4 — grown свободен)
  c-link-units  единицы и величины → системы
  c-retag       переразметка всех статей на утверждённом реестре
  c-apply       применение разметки в статьи + пересборка live из хранилищ
  c-mentions-ru добить русские якоря (осталось ~700 статей)
  c-highlight   разметка текстов ссылками, все уровни
  c-export      словари клиенту (concepts-names по языкам)
  c-graph       свежие данные графа
  c-pages       перегенерация /concepts/ и /formula/ (все языки)
  c-status      дашборд

После — СТОП: полная пересборка сайта (этап D) отдельным «да» владельца.
Шаги в data/bc-state.json; обрыв продолжается. Лог data/bc.log.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PY = sys.executable
LOG = ROOT / "data" / "bc.log"
STATE = ROOT / "data" / "bc-state.json"
A4LOG = ROOT / "data" / "a4.log"

from tools.concept_fullcards import cheap_window  # noqa: E402


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"done": []}


def run(step, cmd, timeout=28800, cwd=None):
    st = state()
    if step in st["done"]:
        log(f"· {step}: уже сделан")
        return True
    log(f"▶ {step}")
    try:
        r = subprocess.run(cmd, cwd=cwd or ROOT, timeout=timeout)
        ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
    log(("✓ " if ok else "✗ ") + step)
    if ok:
        st["done"].append(step)
        STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return ok


def wait_cheap():
    if cheap_window():
        return
    log("ждём дешёвое окно DeepSeek (19:30 по Кувейту)…")
    while not cheap_window():
        time.sleep(600)
    log("окно открылось")


def wait_a4():
    while True:
        try:
            if "A4 ЗАВЕРШЁН" in A4LOG.read_text(encoding="utf-8", errors="ignore"):
                return
        except FileNotFoundError:
            pass
        time.sleep(300)


def main():
    log("═══ ЭТАПЫ B+C: карточки, языки, финальная разметка ═══")

    # Владелец 27.08, уходя: «берись после того, как завершится [A4] и начнётся
    # окно, пункт B C». Сначала ждём финиш A4 — параллельно ничего не гоним,
    # потом дешёвое окно DeepSeek.
    log("ждём финиша A4…")
    wait_a4()
    log("A4 завершён")
    wait_cheap()
    run("b-fullcards", [PY, "tools/concept_fullcards.py", "--run"])
    run("b-tr-concepts", [PY, "tools/cards_translate_ru.py", "--concepts"])
    run("b-tr-formulas", [PY, "tools/cards_translate_ru.py", "--formulas"])
    run("b-systems", [PY, "tools/formula_anatomy.py", "--systems"])

    # ── ФАЗА C: финальная разметка на выросшем реестре ──
    log("── фаза C: финальная разметка ──")
    run("c-seed", [PY, "tools/unit_systems_seed.py", "--seed"], timeout=1200)
    run("c-link-units", [PY, "tools/unit_systems_seed.py", "--link-units",
                         "--force-peak"], timeout=7200)
    # новорождённым A4 — записи и переводы вдогонку (инкрементально)
    run("c-fullcards2", [PY, "tools/concept_fullcards.py", "--run", "--force-peak"])
    run("c-revector", [PY, "tools/concept_fullcards.py", "--revector"], timeout=7200)
    run("c-tr2", [PY, "tools/cards_translate_ru.py", "--concepts", "--force-peak"])
    run("c-retag", [PY, "tools/retag_hub.py", "--thr", "0.50", "--margin", "0.12"],
        timeout=14400)
    run("c-apply", [PY, "tools/wave5_apply.py", "--apply"], timeout=14400)
    run("c-names-ru", [PY, "tools/concept_names_translate.py"], timeout=7200)
    run("c-mentions-ru", [PY, "tools/mentions_ru.py"], timeout=21600)
    run("c-highlight", [PY, "tools/highlight_concepts.py",
                        "--tiers", "simple,popular,advanced"], timeout=28800)
    if "c-export" not in state()["done"]:
        live = json.loads((ROOT / "data/concepts-live.json")
                          .read_text(encoding="utf-8"))["concepts"]
        for lang in ("ru", "en", "es", "ar", "fr"):
            out = {c: {"name": (v.get("names") or {}).get(lang)
                       or (v.get("names") or {}).get("en") or c.replace("_", " ")}
                   for c, v in live.items()}
            (ROOT / f"lang/{lang}/data/concepts-names.json").write_text(
                json.dumps(out, ensure_ascii=False), encoding="utf-8")
        st = state()
        st["done"].append("c-export")
        STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        log("✓ c-export")
    run("c-graph", [PY, "tools/concepts_graph_export.py"], timeout=1800)
    run("c-pages", [PY, "concepts_pages.py"], timeout=14400)
    run("c-pages-f", [PY, "formulas_pages.py"], timeout=14400)
    run("c-audit", [PY, "tools/concepts_audit.py"], timeout=1800)
    run("c-gaudit", [PY, "tools/group_integrity.py", "--audit"], timeout=1800)
    run("c-status", [PY, "-c",
        "import sys; sys.path.insert(0,'.'); import generate as G; "
        "G.generate_status_page()"], timeout=1800)
    log("═══ B+C ЗАВЕРШЕНЫ — стоп до смотра владельца (полная пересборка = этап D) ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
