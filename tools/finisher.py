# -*- coding: utf-8 -*-
"""Финишер последнего рывка (владелец 27.08: «собирай план и делай последний рывок…
на выходе локально нужен работающий отточенный экземпляр, все сервисы
автоматизированы и проверены; поблажка — пока русский и английский»).

Ждёт маркер «НОЧНОЙ ПРОГОН ЗАВЕРШЁН» в data/night-run.log, затем по порядку:

  1. s2-collect    дособор Semantic Scholar (пакетный хвост, граф, авторы) — ФОНОМ,
                   он ходит в другой API и не мешает DeepSeek-шагам
  2. seed          рождение 5 систем единиц (grown + вектор в матрицу) — только
                   теперь: births/births2 ночи больше не пишут в grown, гонки нет
  3. systems       формы в разных системах единиц (formula_anatomy --systems)
  4. link-units    единицы/величины → системы (unit_systems_seed --link-units)
  5. tr-concepts   русские полные карточки понятий (cards_translate_ru)
  6. tr-formulas   русские анатомии формул
  7. re-apply      wave5_apply --apply: live пересобирается уже с хранилищами
                   (full, переводы, системы) и с новорождёнными системами
  8. wait-s2       дождаться конца s2-collect
  9. author-map    сопоставление авторов с S2 на полных данных
 10. cites         цитируемость в готовые индексы (enrich_index_cites)
 11. ft-dataset    пары для файн-тюнинга bge-m3 (ft_dataset_export)
 12. pages         перегенерация /concepts/ и /formula/ (все языки — там теперь
                   русский контент и блоки систем)
 13. authors-html  страницы авторов с S2-блоком (update_all_authors)
 14. status        дашборд

Каждый шаг отмечается в data/finisher-state.json — обрыв продолжается с места.
DeepSeek-шаги идут с --force-peak: владелец сказал «поехали», суммы копеечные.

    python tools/finisher.py            (обычно фоном, Start-Process Hidden)
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PY = sys.executable
LOG = ROOT / "data" / "finisher.log"
STATE = ROOT / "data" / "finisher-state.json"
NIGHT = ROOT / "data" / "night-run.log"


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


def mark(step):
    st = state()
    st["done"].append(step)
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def run(step, cmd, timeout=21600):
    if step in state()["done"]:
        log(f"· {step}: уже сделан")
        return True
    log(f"▶ {step}: {' '.join(cmd[1:])}")
    try:
        r = subprocess.run(cmd, cwd=ROOT, timeout=timeout)
        ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
    log(("✓ " if ok else "✗ ") + step)
    if ok:
        mark(step)
    return ok


def main():
    log("═══ ФИНИШЕР: ждём конца ночной цепочки ═══")
    while True:
        try:
            if "ЗАВЕРШЁН" in NIGHT.read_text(encoding="utf-8", errors="ignore"):
                break
        except FileNotFoundError:
            pass
        time.sleep(120)
    log("ночная цепочка завершена — поехали")

    # 1. S2 фоном (другой API, DeepSeek-шагам не мешает)
    s2 = None
    if "s2-collect" not in state()["done"]:
        log("▶ s2-collect (фоном)")
        s2 = subprocess.Popen(
            [PY, "tools/s2_collect.py"], cwd=ROOT,
            stdout=(ROOT / "data/s2/collect5.log").open("w", encoding="utf-8"),
            stderr=subprocess.STDOUT)

    run("seed", [PY, "tools/unit_systems_seed.py", "--seed"], timeout=600)
    run("systems", [PY, "tools/formula_anatomy.py", "--systems", "--force-peak"])
    run("link-units", [PY, "tools/unit_systems_seed.py", "--link-units",
                       "--force-peak"])
    run("tr-concepts", [PY, "tools/cards_translate_ru.py", "--concepts",
                        "--force-peak"], timeout=28800)
    run("tr-formulas", [PY, "tools/cards_translate_ru.py", "--formulas",
                        "--force-peak"], timeout=28800)
    run("re-apply", [PY, "tools/wave5_apply.py", "--apply"], timeout=14400)

    if s2 is not None:
        log("▶ wait-s2: ждём дособор Scholar")
        try:
            s2.wait(timeout=32000)
            mark("s2-collect")
            log("✓ wait-s2")
        except subprocess.TimeoutExpired:
            s2.kill()
            log("✗ wait-s2: не дождались — карта авторов пойдёт по собранному")

    run("author-map", [PY, "tools/s2_author_map.py"], timeout=1800)
    run("cites", [PY, "tools/enrich_index_cites.py"], timeout=1800)
    run("ft-dataset", [PY, "tools/ft_dataset_export.py"], timeout=7200)
    run("pages-concepts", [PY, "concepts_pages.py"], timeout=7200)
    run("pages-formulas", [PY, "formulas_pages.py"], timeout=7200)
    run("authors-html", [PY, "-c",
        "import sys; sys.path.insert(0,'.'); import generate as G; "
        "G.update_all_authors()"], timeout=14400)
    run("status", [PY, "-c",
        "import sys; sys.path.insert(0,'.'); import generate as G; "
        "G.generate_status_page()"], timeout=1200)
    log("═══ ФИНИШЕР ЗАВЕРШЁН ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
