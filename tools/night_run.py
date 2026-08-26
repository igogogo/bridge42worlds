# -*- coding: utf-8 -*-
"""Ночной прогон 26→27.08: добыча понятий из всех статей и пересборка знания.

Поручение владельца (26.08, вечер, после пробы якорения): «сам ищи по статьям —
аббревиатуры, единицы (ГэВ), приборы (Fermi/LAT), общенаучное (аннигиляция,
статистическая значимость, энергетические бины). Если надо ещё 1000 понятий —
загони. Сделай, чтобы ссылок на статью было раза в два больше».

Проверка перед прогоном подтвердила: всего названного им в реестре НЕТ.

ЭТАПЫ (лог каждого — в data/night-run.log, остановка любого не роняет следующие,
кроме жёстких зависимостей):

  1  harvest    спросить ВСЕ статьи усиленным промптом (аббревиатуры/единицы/
                общенаучное обязательны) — единственный большой платный шаг
  2  match      кандидаты против реестра вектором
  3  distill    слить дубли кандидатов
  4  births     рождение доросших (>= 5 статей) — цикл роста, включая ГэВ и Fermi/LAT
  5  anatomy    анатомия 642 формул с единицами и значениями констант
  6  a-link     операторы/константы/величины/единицы из формул → реестр/кандидаты
  7  births2    второй заход рождения (формульные кандидаты)
  8  fullcards  развёрнутые записи всем новым понятиям без записей
  9  names-ru   русские названия всем — подписи плашек и словарь текста
 10  revector   векторы карточек: новые и обновлённые
 11  retag      переразметка статей v2 (хабность, опора 5) на выросшем реестре
 12  apply      разметка в data.json + свежий concepts-live
 13  export     словари клиенту (concepts-names по языкам)
 14  highlight  словарная разметка текстов, потолок 20, все уровни
 15  pages      перегенерация /concepts/ на пяти языках
 16  rebuild    полная пересборка статей (часы; публикация и бэкап под .no-publish)

Якорение ВЕКТОРОМ в тексты — НЕ здесь: делается отдельным шагом после того, как
владелец посмотрит плотность после этой ночи. Сначала честная база: больше понятий
и словарная разметка на выросшем словаре; вектор-якорь добьёт остаток адресно.

Смета: harvest ~6700 статей × ~$0.0009 ≈ $6 · формулы ~$0.5 · записи ~$1.5 ·
переводы ~$0.05 — итого ~$8 в дешёвое окно (скидка 50% уже учтена ценами DeepSeek).

    python tools/night_run.py            запустить (сам ждёт окна, если рано)
    python tools/night_run.py --status   что уже сделано
"""
import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "night-run.log"
STATE = ROOT / "data" / "night-run-state.json"
PY = sys.executable


def log(msg):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"done": []}


def mark(step):
    st = state()
    if step not in st["done"]:
        st["done"].append(step)
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def run(step, cmd, timeout=14400, hard=False):
    """Шаг с журналом и продолжением после обрыва: сделанное не повторяется."""
    if step in state()["done"]:
        log(f"= {step}: уже сделан, пропускаю")
        return True
    log(f"▶ {step}: {' '.join(cmd[1:])}")
    try:
        r = subprocess.run(cmd, timeout=timeout,
                           env={"PYTHONIOENCODING": "utf-8", **__import__('os').environ})
        ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"⏱ {step}: время вышло")
        ok = False
    if ok:
        mark(step)
        log(f"✓ {step}")
    else:
        log(f"✗ {step}" + (" — ЖЁСТКАЯ зависимость, стоп" if hard else " — иду дальше"))
        if hard:
            sys.exit(1)
    return ok


def wait_cheap():
    from tools.concept_fullcards import cheap_window
    while not cheap_window():
        log("ждём дешёвое окно DeepSeek (19:30 по Кувейту)…")
        time.sleep(300)


def all_article_ids():
    ids = [p.parent.name for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json"))]
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        st = state()
        print("сделано:", ", ".join(st["done"]) or "ничего")
        return 0

    log("═══ НОЧНОЙ ПРОГОН: добыча понятий и пересборка знания ═══")
    wait_cheap()

    # 1. harvest всех статей — пачками через concept_cycle не пойдёт (бюджет);
    #    зовём harvest --ask порциями, журнал спрошенных ведёт concept_cycle.state
    if "harvest" not in state()["done"]:
        from tools import concept_harvest as H
        from tools.concept_cycle import state as cyc_state, STATE as CYC_STATE
        st = cyc_state()
        asked = set(st["asked"])
        todo = [i for i in all_article_ids() if i not in asked]
        log(f"▶ harvest: статей к опросу {len(todo)}")
        for n, aid in enumerate(todo, 1):
            try:
                H.ask([aid])
            except SystemExit:
                raise
            except Exception as e:
                log(f"  {aid}: {e}")
            asked.add(aid)
            if n % 50 == 0:
                st["asked"] = sorted(asked)
                CYC_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
                log(f"  спрошено {n}/{len(todo)}")
        st["asked"] = sorted(asked)
        CYC_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        mark("harvest")
        log("✓ harvest")

    run("match", [PY, "tools/concept_harvest.py", "--match"])
    run("distill", [PY, "tools/concept_harvest.py", "--distill"])
    run("births", [PY, "tools/concept_cycle.py", "--budget", "0"])
    run("anatomy", [PY, "tools/formula_anatomy.py", "--run", "--force-peak"])
    run("a-link", [PY, "tools/formula_anatomy.py", "--link"])
    run("births2", [PY, "tools/concept_cycle.py", "--budget", "0"])
    run("fullcards", [PY, "tools/concept_fullcards.py", "--run", "--force-peak"])
    run("names-ru", [PY, "tools/concept_names_translate.py"])
    run("revector", [PY, "tools/concept_fullcards.py", "--revector"])
    run("retag", [PY, "tools/retag_hub.py", "--thr", "0.50", "--margin", "0.12"], hard=True)
    run("apply", [PY, "tools/wave5_apply.py", "--apply"], hard=True)
    run("export", [PY, "-c",
                   "import json,sys;sys.path.insert(0,'.');"
                   "live=json.loads(open('data/concepts-live.json',encoding='utf-8').read())['concepts'];"
                   "from pathlib import Path;"
                   "[Path(f'lang/{l}/data/concepts-names.json').write_text(json.dumps("
                   "{c:{'name':(v.get('names') or {}).get(l) or (v.get('names') or {}).get('en')"
                   " or c.replace('_',' ')} for c,v in live.items()},ensure_ascii=False),"
                   "encoding='utf-8') for l in ('ru','en','es','ar','fr')]"])
    run("highlight", [PY, "tools/highlight_concepts.py", "--tiers", "simple,popular,advanced"],
        timeout=21600)
    run("pages", [PY, "concepts_pages.py"])
    run("rebuild", [PY, "run.py", "html"], timeout=28800)
    log("═══ НОЧНОЙ ПРОГОН ЗАВЕРШЁН ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
