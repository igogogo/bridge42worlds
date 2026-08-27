# -*- coding: utf-8 -*-
"""Шаг A4 плана целиком: целевое донасыщение реестра и пересчёт к смотру.

По «да» владельца 27.08 («сироты оставь, и давай A4 донасыщение, поехали»):

  1. target   целевая добыча law/math/constant/principle по 1700 статьям
              (полные + экспрессы тяжёлых разделов), ~$1–2
  2. match    сверка кандидатов с реестром вектором (0.80)
  3. distill  дистилляция между собой (0.86), проигравшие — в алиасы
  4. births   рождения тройным ситом (опора ≥5 + вектор + Scholar)
  5. super    пересчёт связности на выросшем реестре (v4 → concepts_super)
  6. live     пересборка справочника из хранилищ (статьи НЕ трогаются)
  7. graph    свежий снимок данных графа
  8. audit    обновлённый аудит к смотру владельца

После — СТОП: никакой переразметки статей, никаких страниц. Это решает
владелец на смотре (A5). Каждый шаг в data/a4-state.json, обрыв продолжается.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PY = sys.executable
LOG = ROOT / "data" / "a4.log"
STATE = ROOT / "data" / "a4-state.json"


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


def run(step, cmd, timeout=21600, cwd=None):
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


def main():
    log("═══ A4: целевое донасыщение ═══")
    if not run("target", [PY, "tools/concept_harvest_target.py", "--run"],
               timeout=4 * 3600):
        log("добыча не завершилась — стоп"); return 1
    # СТАТИСТИКА — отдельный раздел (владелец 27.08: «собрать эмпирически все
    # статистические методы и приёмы физики, новый раздел кроме математики»)
    if not run("stats", [PY, "tools/concept_harvest_target.py", "--run",
                         "--profile", "stats"], timeout=4 * 3600):
        log("стат-проход не завершился — стоп"); return 1
    # формулы отдают опору константам/операторам: статьи применений форм
    # (владелец 27.08: «константы могут в статьях не упоминаться — об этом
    # скажут наши формулы»); повторный --link идемпотентен
    run("flink", [PY, "tools/formula_anatomy.py", "--link"], timeout=3600)
    run("match", [PY, "tools/concept_harvest.py", "--match"], timeout=3600)
    run("distill", [PY, "tools/concept_harvest.py", "--distill"], timeout=1800)
    run("births", [PY, "tools/concept_cycle.py", "--budget", "0"],
        timeout=4 * 3600)
    # ПЕРЕКРЁСТНАЯ ВНУТРИГРУППОВАЯ ПРОВЕРКА (владелец 27.08: «внутри всё должно
    # быть целостно; дорост изнутри даст ещё процентов 20»): группы называют
    # недостающий скелет → сверка вектором → полевой добор опоры нашими
    # статьями → обычное сито рождений (вектор + Scholar + ≥5 статей)
    run("g-grow", [PY, "tools/group_integrity.py", "--grow"], timeout=3600)
    run("match2", [PY, "tools/concept_harvest.py", "--match"], timeout=3600)
    run("distill2", [PY, "tools/concept_harvest.py", "--distill"], timeout=1800)
    run("f-support", [PY, "tools/group_integrity.py", "--support"], timeout=3600)
    run("births-g", [PY, "tools/concept_cycle.py", "--budget", "0"],
        timeout=4 * 3600)
    run("g-audit", [PY, "tools/group_integrity.py", "--audit"], timeout=1800)
    # вход супера: реестр v4 из live+рождённых собирает wave5_apply.build_live —
    # сначала live с новыми рождениями, потом супер на нём, потом live ещё раз
    run("live-pre", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    if "super" not in state()["done"]:
        # v4 = свежий live (карточки + опора)
        live = json.loads((ROOT / "data/concepts-live.json")
                          .read_text(encoding="utf-8"))["concepts"]
        reg = {cid: {"name": (v.get("names") or {}).get("en") or cid,
                     "kind": v.get("kind") or "concept",
                     "card_en": v.get("card_en") or "",
                     "support": v.get("articles") or []}
               for cid, v in live.items()}
        (ROOT.parent / "b42-ml" / "data" / "concepts-v4.json").write_text(
            json.dumps({"concepts": reg}, ensure_ascii=False), encoding="utf-8")
        log(f"вход супера: {len(reg)} понятий")
    run("super", [PY, "concepts_super.py", "--reg", "data/concepts-v4.json",
                  "--name-supers"],
        timeout=3600, cwd=ROOT.parent / "b42-ml")
    run("live", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    run("graph", [PY, "tools/concepts_graph_export.py"], timeout=1800)
    run("audit", [PY, "tools/concepts_audit.py"], timeout=1800)
    log("═══ A4 ЗАВЕРШЁН — стоп до смотра владельца ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
