# -*- coding: utf-8 -*-
"""Полный прогон конвейера: свежие статьи → насыщение знаниями → сборка → выпуск.

Владелец 28.08: «прогони после прода пайплайн целиком обновления свежих статей,
не обращай внимания на лимиты, сделай стандартный прогон и всю цепочку насыщений,
как будто всё на самом деле, потом её проверка — это тест на нашу зрелость и твою
автономность».

Здесь собрано в одну цепочку то, что до сих пор жило отдельными оркестраторами
(a4_run, bc_run, d_run) и запускалось руками по частям. Смысл именно в связности:
конвейер должен пройти от забора работ с arXiv до выложенного сайта без участия
человека — и честно остановиться, если шаг не удался.

  ЗАБОР И РАЗБОР      каждый пропущенный день по очереди: arXiv → отбор →
                      генерация → обложки → переводы → разметка
  НАСЫЩЕНИЕ           добыча понятий из новых статей, анатомия новых формул,
                      сверка вектором, дистилляция, рождения, рост групп
  СВЯЗНОСТЬ           пересчёт супером, соседи по смыслу, экспорт графа
  ЗАПИСИ              карточки новорождённым, русские переводы, имена
  СБОРКА              страницы понятий и формул, весь сайт, дашборд
  ОБЛАКО              D1, векторы, выкладка воркера
  ПРОВЕРКА            эндпоинты, аудит реестра, аудит групп, связность ссылок

Каждый шаг помнится в data/full-state.json: прогон можно остановить и продолжить
с места обрыва, не повторяя сделанное.

    python tools/full_run.py --days 2026-08-22,2026-08-23    конкретные дни
    python tools/full_run.py --catch-up                      все пропущенные
    python tools/full_run.py --catch-up --limit 20           не больше N в день
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PY = sys.executable
LOG = ROOT / "data" / "full-run.log"
STATE = ROOT / "data" / "full-state.json"
# Журнал прогонов — то, что читает схема конвейера (/pipeline.html): не только
# «где мы сейчас», но и история. Владелец 28.08: «зашёл и историю увидел, и
# проблемы, и текущее состояние, и что запланировано». Один файл, по записи на
# прогон, последние тридцать.
RUNS = ROOT / "data" / "pipeline-runs.json"
RUNS_KEEP = 30
STEPS_DIR = ROOT / "data" / "pipeline-steps"


def summarize(out, keep=3):
    """Итог шага: строки, в которых он сам отчитался о сделанном.

    Шаги договорились об одном: важное помечают галочкой или стрелкой в файл.
    Берём последние такие строки — они и есть результат («понятий 3589», «граф:
    4447 узлов»). Ничего не нашли — берём последнюю непустую: пусть будет хоть
    что-то, чем пустая лампочка.
    """
    lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    marked = [ln for ln in lines
              if ln.startswith(("✅", "✓", "→", "⚠")) or " · " in ln]
    picked = (marked or lines)[-keep:]
    return [ln[:160] for ln in picked]


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


def save(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    journal(st)


def journal(st):
    """Дописать текущий прогон в журнал: шаги, время каждого, ошибки, план.

    Пишется на каждом шаге, а не в конце: если прогон оборвётся, журнал всё равно
    покажет, до чего дошли и на чём встали — ровно то, ради чего он и заведён.
    """
    try:
        runs = json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else []
    except Exception:
        runs = []
    rid = st.get("run_id")
    rec = None
    for r in runs:
        if r.get("id") == rid:
            rec = r
            break
    if rec is None:
        rec = {"id": rid, "started": st.get("started"), "days": st.get("days") or []}
        runs.append(rec)
    rec["done"] = list(st.get("done") or [])
    rec["failed"] = list(st.get("failed") or [])
    rec["current"] = st.get("current")
    rec["at"] = st.get("at")
    rec["secs"] = dict(st.get("secs") or {})
    rec["steps"] = dict(st.get("steps") or {})
    rec["plan"] = list(st.get("plan") or [])
    runs = runs[-RUNS_KEEP:]
    RUNS.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")


def run(step, cmd, timeout=8 * 3600, cwd=None, env=None, soft=False):
    """soft — шаг, неудача которого не должна валить прогон (например, обложки:
    без картинки статья всё равно статья).

    Состояние пишется НЕ только для продолжения с места обрыва: схема конвейера
    (/pipeline.html) читает этот же файл и красит узлы — что прошло, что идёт
    сейчас, что упало. Разметка под это была готова с самого начала, не хватало
    только состояния.
    """
    st = state()
    if step in st["done"]:
        log(f"· {step}: уже сделан")
        return True
    log(f"▶ {step}")
    started = time.strftime("%H:%M:%S")
    st["current"] = step
    st["at"] = time.strftime("%Y-%m-%d %H:%M")
    st.setdefault("steps", {})[step] = {"started": started}
    save(st)
    t0 = time.time()
    out = ""
    try:
        e = dict(os.environ, **env) if env else None
        # Вывод шага ЛОВИМ, а не отпускаем в пустоту: в нём и лежат числа, ради
        # которых шаг запускался — «раздел /concepts/: 3589 страниц», «граф: 4447
        # узлов, 42335 рёбер». Без них лампочка говорит «прошло» и молчит о том,
        # ЧТО прошло. Полный вывод кладём в файл шага, короткий итог — в журнал.
        e = dict(e or os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(cmd, cwd=cwd or ROOT, timeout=timeout, env=e,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        ok = r.returncode == 0
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
        STEPS_DIR.mkdir(parents=True, exist_ok=True)
        (STEPS_DIR / f"{step}.log").write_text(out, encoding="utf-8")
        for line in out.splitlines():
            print(line, flush=True)
    except subprocess.TimeoutExpired:
        ok = False
        log(f"  ⏱ {step}: превышено время ({timeout // 60} мин)")
    dt = int(time.time() - t0)
    finished = time.strftime("%H:%M:%S")
    log(("✓ " if ok else "✗ ") + f"{step} ({dt // 60} мин {dt % 60} с)")
    st = state()
    st["current"] = None
    st["at"] = time.strftime("%Y-%m-%d %H:%M")
    st.setdefault("secs", {})[step] = dt
    st.setdefault("steps", {})[step] = {
        "started": started, "finished": finished, "secs": dt, "ok": ok,
        "out": summarize(out),
    }
    if ok:
        st["done"].append(step)
        st.get("failed", []) and step in st["failed"] and st["failed"].remove(step)
    else:
        st.setdefault("failed", []).append(step)
        if not soft:
            log(f"  ШАГ НЕ УДАЛСЯ: {step}. Прогон остановлен — разбираться здесь.")
    save(st)
    return ok or soft


def missing_days(limit_days=10):
    """Дни между последним в архиве и вчерашним — то, что конвейер пропустил."""
    arch = ROOT / "lang" / "ru" / "archive"
    have = sorted(p.name for p in arch.iterdir() if p.is_dir())
    if not have:
        return []
    last = datetime.date.fromisoformat(have[-1])
    end = datetime.date.today() - datetime.timedelta(days=1)
    out, d = [], last + datetime.timedelta(days=1)
    while d <= end and len(out) < limit_days:
        out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser(description="Полный прогон конвейера")
    ap.add_argument("--days", help="дни через запятую")
    ap.add_argument("--catch-up", action="store_true", help="все пропущенные дни")
    ap.add_argument("--limit", type=int, default=20, help="статей в день")
    ap.add_argument("--no-publish", action="store_true", help="собрать, но не выпускать")
    a = ap.parse_args()

    days = ([d.strip() for d in a.days.split(",") if d.strip()] if a.days
            else missing_days() if a.catch_up else [])
    log("═══ ПОЛНЫЙ ПРОГОН КОНВЕЙЕРА ═══")
    log(f"дни: {', '.join(days) if days else 'нет — только насыщение и сборка'}")

    # План объявляем ДО работы: схема конвейера показывает не только пройденное и
    # текущее, но и то, что ещё предстоит. Без этого «запланировано» пришлось бы
    # угадывать по списку шагов, зашитому в страницу, — и она разъехалась бы с
    # цепочкой при первой же правке.
    st = state()
    if not st.get("run_id"):
        st["run_id"] = time.strftime("%Y-%m-%d %H:%M")
        st["started"] = st["run_id"]
    st["days"] = days
    st["plan"] = ([f"day-{d}" for d in days] + [
        "harvest", "anatomy", "flink", "match", "distill", "births", "g-grow",
        "f-support", "twins", "consts", "units-fix", "live-1", "cards", "tr-cards",
        "tr-formulas", "names-ru", "retag", "apply", "super", "live-2", "vecnb",
        "live-3", "gnames", "weave", "live-4", "graph", "mentions-ru", "highlight",
        "pages-c", "pages-f", "html", "authors", "status", "cloud-d1", "cloud-vec",
        "cards-sync", "deploy", "api", "pages", "audit", "gaudit", "links"])
    save(st)

    # ── I. ЗАБОР И РАЗБОР ────────────────────────────────────────────────────
    # Каждый день отдельным шагом: если оборвётся на третьем, первые два не
    # придётся повторять, а разбираться нужно ровно с тем днём, где встали.
    # Полный режим, не экспресс: владелец 28.08 — «сделай стандартный прогон и всю
    # цепочку насыщений, как будто всё на самом деле, не обращай внимания на лимиты».
    # Экспресс читает аннотацию вместо текста и пишет два уровня из трёх — для теста
    # зрелости это была бы репетиция, а не прогон. Языки ru,en: перевод на остальные
    # три владелец отложил, и класть в прод полупереведённое нельзя.
    LANGS = {"B42_LANGS": "ru,en"}
    for d in days:
        run(f"day-{d}", [PY, "run.py", "daily", "--date", d, "--limit", str(a.limit)],
            timeout=6 * 3600, env=LANGS)

    # ── II. НАСЫЩЕНИЕ ЗНАНИЯМИ ───────────────────────────────────────────────
    # Порядок тот же, что в ночной цепочке: добыть кандидатов из новых текстов,
    # разобрать новые формулы, свериться вектором, дистиллировать, родить.
    run("harvest", [PY, "tools/concept_harvest_target.py", "--run"], timeout=6 * 3600)
    run("anatomy", [PY, "tools/formula_anatomy.py", "--run"], timeout=4 * 3600, soft=True)
    run("flink", [PY, "tools/formula_anatomy.py", "--link"], timeout=1800, soft=True)
    run("match", [PY, "tools/concept_harvest.py", "--match"], timeout=3600)
    run("distill", [PY, "tools/concept_harvest.py", "--distill"], timeout=3600)
    run("births", [PY, "tools/concept_cycle.py", "--budget", "0"], timeout=4 * 3600)
    run("g-grow", [PY, "tools/group_integrity.py", "--grow"], timeout=3600, soft=True)
    run("f-support", [PY, "tools/group_integrity.py", "--support"], timeout=3600, soft=True)
    # Двойники родятся каждый прогон: понятие приходит из статьи под своим
    # написанием и совпадает по-русски с уже живущим. Разбирает их модель-судья
    # («один предмет или два»), поэтому шаг стоит сразу после рождений — пока
    # двойник не оброс карточками, статьями и местом в облаке.
    run("twins", [PY, "tools/concept_twins.py", "--apply"], timeout=3600, soft=True)
    run("consts", [PY, "tools/constants_from_formulas.py", "--apply", "--codata"],
        timeout=900, soft=True)
    run("units-fix", [PY, "tools/fix_truncated_units.py", "--apply"], timeout=900, soft=True)

    # ── III. ЗАПИСИ НОВОРОЖДЁННЫМ ────────────────────────────────────────────
    run("live-1", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    run("cards", [PY, "tools/concept_fullcards.py", "--run", "--force-peak"],
        timeout=6 * 3600)
    run("tr-cards", [PY, "tools/cards_translate_ru.py", "--concepts", "--force-peak"],
        timeout=6 * 3600)
    run("tr-formulas", [PY, "tools/cards_translate_ru.py", "--formulas", "--force-peak"],
        timeout=4 * 3600, soft=True)
    run("names-ru", [PY, "tools/concept_names_translate.py"], timeout=3600, soft=True)
    run("retag", [PY, "tools/retag_hub.py", "--thr", "0.50", "--margin", "0.12"],
        timeout=4 * 3600)
    run("apply", [PY, "tools/wave5_apply.py", "--apply"], timeout=3600)

    # ── IV. СВЯЗНОСТЬ ────────────────────────────────────────────────────────
    # Супер считает группы и соседей по карточкам, поэтому идёт ПОСЛЕ карточек;
    # --embed обязателен, иначе он возьмёт вектора прошлого прогона, где новых
    # понятий нет, и отработает вхолостую.
    if "super" not in state()["done"]:
        live = json.loads((ROOT / "data/concepts-live.json")
                          .read_text(encoding="utf-8"))["concepts"]
        # Слитые понятия супер не считает: у записи-указателя нет ни карточки, ни
        # статей, и она попала бы в кластеризацию пустым узлом, оттягивая на себя
        # место в области.
        reg = {cid: {"name": (v.get("names") or {}).get("en") or cid,
                     "kind": v.get("kind") or "concept",
                     "card_en": v.get("card_en") or "",
                     "support": v.get("articles") or []}
               for cid, v in live.items() if not v.get("merged_into")}
        (ROOT.parent / "b42-ml" / "data" / "concepts-v4.json").write_text(
            json.dumps({"concepts": reg}, ensure_ascii=False), encoding="utf-8")
        log(f"вход супера: {len(reg)} понятий")
    run("super", [PY, "concepts_super.py", "--embed",
                  "--reg", "data/concepts-v4.json", "--name-supers"],
        timeout=2 * 3600, cwd=ROOT.parent / "b42-ml", soft=True)
    run("live-2", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    run("vecnb", [PY, "tools/vector_neighbors.py", "--apply"], timeout=1800, soft=True)
    run("live-3", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    run("gnames", [PY, "tools/group_names.py", "--run", "--force-peak"],
        timeout=3600, soft=True)
    # Третий источник связей (владелец 28.08: «связь между законом и константой —
    # это работа твоя как интеллекта, а не только что есть в статьях; раз в неделю
    # этим заниматься»). Статьи дают соседство, вектор — похожесть, знание — «что
    # из чего следует». В цепочке идёт перед экспортом графа, чтобы найденное
    # попало в рёбра этого же прогона, а не следующего.
    run("weave", [PY, "tools/link_weaving.py", "--all", "--limit", "400", "--apply"],
        timeout=4 * 3600, soft=True)
    run("live-4", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800, soft=True)
    run("graph", [PY, "tools/concepts_graph_export.py"], timeout=1800)
    run("mentions-ru", [PY, "tools/mentions_ru.py"], timeout=4 * 3600, soft=True)
    run("highlight", [PY, "tools/highlight_concepts.py",
                      "--tiers", "simple,popular,advanced"], timeout=6 * 3600, soft=True)

    # ── V. СБОРКА ────────────────────────────────────────────────────────────
    run("pages-c", [PY, "concepts_pages.py"], timeout=3600)
    run("pages-f", [PY, "formulas_pages.py"], timeout=3600)
    env = {"B42_LANGS": "ru,en"}
    if a.no_publish:
        env["B42_NO_PUBLISH"] = "1"
    run("html", [PY, "run.py", "html", "--force"], timeout=8 * 3600, env=env)
    run("authors", [PY, "-c", "import sys; sys.path.insert(0,'.'); "
                    "import generate as G; G.update_all_authors()"], timeout=4 * 3600)
    run("status", [PY, "-c", "import sys; sys.path.insert(0,'.'); "
                   "import generate as G; G.generate_status_page()"], timeout=1800)
    run("pipeline-page", [PY, "tools/pipeline_page.py"], timeout=600, soft=True)

    # ── VI. ОБЛАКО ───────────────────────────────────────────────────────────
    run("cloud-d1", [PY, "cloudflare/concepts_sync.py"], timeout=4 * 3600)
    run("cloud-vec", [PY, "tools/concepts_to_vectorize.py", "--apply"], timeout=2 * 3600)
    run("cards-sync", [PY, "cloudflare/cards_sync.py"], timeout=2 * 3600, soft=True)
    run("deploy", [PY, "cloudflare/deploy_worker.py"], timeout=1800,
        env={"B42_DEPLOY_OK": "1"})

    # ── VII. ПРОВЕРКА ────────────────────────────────────────────────────────
    run("api", [PY, "cloudflare/checks/api_check.py"], timeout=1800, soft=True)
    run("pages", [PY, "cloudflare/checks/pages_check.py"], timeout=1800, soft=True)
    run("audit", [PY, "tools/concepts_audit.py"], timeout=1800, soft=True)
    run("gaudit", [PY, "tools/group_integrity.py", "--audit"], timeout=1800, soft=True)
    run("links", [PY, "tools/link_check.py"], timeout=1800, soft=True)
    log("═══ ПОЛНЫЙ ПРОГОН ЗАВЕРШЁН ═══")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
