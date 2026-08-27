# -*- coding: utf-8 -*-
"""Цикл роста понятий: одна команда, которую фабрика зовёт каждый день.

Владелец 26 августа: «надо увидеть процесс пополнения понятий и обновления вектора.
Всё должно работать В ПРОДЕ без ручного управления: понятия растут, наполняются,
результат повторяем и достоверен».

Ручное управление здесь заканчивается. Цикл делает за прогон:

  1. СПРОСИТЬ   статьи, которых ещё не спрашивали (журнал помнит какие) — промпт
                по группам, ответ структурированный (tools/concept_harvest.py --ask).
                Единственный платный шаг: DeepSeek, ~копейки за статью, бюджет
                ограничен ключом --budget.
  2. СВЕРИТЬ    кандидатов с реестром вектором (bge-m3, тот же движок, что считал
                карточки). Совпал >= 0.80 — статья к старому понятию; нет — копится.
  3. ДИСТИЛЛ.   слить кандидатов-дубли (>= 0.86 по карточкам) — разные статьи
                называют одно чуть разными словами.
  4. РОДИТЬ     кандидат с >= 5 статьями и без совпадения — дорос. Карточка у него
                УЖЕ ЕСТЬ (однострочник пришёл из промпта), вектор УЖЕ ПОСЧИТАН
                (на шаге сверки) — рождение бесплатное:
                  · понятие пишется в data/concepts-grown.json (дельта к реестру;
                    сборка вливает её в боевой реестр),
                  · вектор уходит в Vectorize, пространство «concepts» — живая
                    разметка новых статей видит его немедленно.
  5. ЗАПИСАТЬ   строку в data/concept-cycle-log.jsonl: спрошено, найдено, слито,
                рождено, потрачено. «Увидеть процесс» — это сюда: журнал читается
                утренним отчётом, и рост виден по дням, а не по ощущениям.

ПОВТОРЯЕМОСТЬ. Каждый шаг идемпотентен: спрошенная статья не спрашивается второй раз
(журнал), совпавший кандидат не сверяется заново (matched в копилке), рождённое
понятие не рождается дважды (born в копилке). Оборванный прогон продолжается со
своего места следующим запуском — состояние в файлах, не в памяти процесса.

ДОСТОВЕРНОСТЬ. Пороги не назначены, а откалиброваны замером 26 августа:
тождество 0.88-0.91, сосед 0.72, мусор 0.49 — совпадение 0.80 в середине разрыва.
Рождение требует пяти НЕЗАВИСИМЫХ статей: одна статья не рождает понятие никогда.

ЗАПУСК:  python tools/concept_cycle.py --dry          показать, что сделал бы
         python tools/concept_cycle.py --budget 30    прогон (фабрика зовёт так)
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import concept_harvest as H

STATE = ROOT / "data" / "concept-cycle.json"
LOG = ROOT / "data" / "concept-cycle-log.jsonl"
GROWN = ROOT / "data" / "concepts-grown.json"
BORN_MIN = H.ARTICLES_MIN


def state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"asked": []}


def fresh_articles(asked, limit):
    """Кого спрашивать: свежие статьи, которых цикл ещё не видел. Свежие первыми —
    цикл живёт на потоке, а хвост архива добирается остатком бюджета."""
    seen = set(asked)
    out = []
    for p in sorted(ROOT.glob("lang/ru/archive/*/*/data.json"), reverse=True):
        aid = p.parent.name
        if aid not in seen:
            out.append(aid)
        if len(out) >= limit:
            break
    return out


def born_candidates(rows):
    return [r for r in rows.values()
            if not r.get("matched") and not r.get("born")
            and len(r["articles"]) >= BORN_MIN and r.get("vec")]


def s2_alive(name):
    """Валидация термина Семантик Сколаром перед рождением. ДОПОЛНЕНИЕ к нашим
    правилам (5 статей, вектор, дистилляция), не замена: наш механизм решает
    «дорос ли», Scholar отвечает на один вопрос — существует ли такой термин в
    науке вообще. Живой термин даёт тысячи работ, склейка-фантом — единицы.

    Мягкая: Scholar недоступен или лимит — рождаем как раньше, ночь не блокируем.
    Пауза 1.1 с — их предел 1 запрос/сек на ключ, волнами не грузим (владелец)."""
    import time
    import urllib.request
    import urllib.parse
    try:
        k = None
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("SEMANTIC_SCHOLAR_KEY"):
                k = line.split("=", 1)[1].strip()
        if not k:
            return True
        q = urllib.parse.quote(name.replace("_", " "))
        r = urllib.request.Request(
            f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit=1&fields=title",
            headers={"x-api-key": k})
        with urllib.request.urlopen(r, timeout=30) as resp:
            total = json.loads(resp.read().decode("utf-8")).get("total", 0)
        time.sleep(1.1)
        if total < 30:
            print(f"   🔎 {name}: в Scholar всего {total} работ — фантом, не рождаем")
            return False
        return True
    except Exception:
        return True     # внешний сервис не должен уметь останавливать наш цикл


def give_birth(rows, dry):
    """Кандидат становится понятием: дельта реестра + вектор в облако."""
    ready = born_candidates(rows)
    if not ready:
        return 0
    grown = {}
    if GROWN.exists():
        grown = json.loads(GROWN.read_text(encoding="utf-8"))
    born = 0
    for r in ready:
        name = r["name"]
        if name in grown:
            r["born"] = True     # уже рождён прошлым прогоном, отметка потерялась
            continue
        if dry:
            print(f"   родилось бы: {name} ({len(r['articles'])} статей) — {r['line'][:60]}")
            born += 1
            continue
        if not s2_alive(name):
            r["matched"] = "__s2_reject__"     # больше не кандидат; след остаётся виден
            continue
        grown[name] = {
            "kind": r["kind"], "group": r["group"], "scope": r["scope"],
            "card_en": r["line"], "articles": r["articles"],
            "aliases": r.get("aliases") or [],
            "born": datetime.now().date().isoformat(), "origin": "live-harvest",
        }
        # В ОБЛАКО НИЧЕГО (владелец 26.08: «сначала всё локально проверю»):
        # заливка вектора в Vectorize отключена до его слова. Локальной матрицы
        # достаточно для всего локального цикла; облако получит все карточки разом
        # массовой заливкой (tools/concepts_to_vectorize.py) при публикации.
        # upsert_vector(name, r["vec"], r["kind"])
        append_to_matrix(name, r["vec"])
        r["born"] = True
        born += 1
        print(f"   🌱 {name} ({len(r['articles'])} статей)")
    if not dry and born:
        GROWN.write_text(json.dumps(grown, ensure_ascii=False, indent=1), encoding="utf-8")
    return born


def append_to_matrix(name, vec):
    """Новорождённый — в ЛОКАЛЬНУЮ матрицу карточек (b42-ml/concept-cards.f16/.ids).

    Без этого дыра: понятие рождено, вектор в облаке, а переразметка (retag_hub)
    читает локальную матрицу — и новорождённого в ней нет, статьи его не получат.
    Матрица и список id дописываются в конец, согласованно."""
    import numpy as np
    ml = ROOT.parent / "b42-ml" / "data"
    ids_p, vec_p = ml / "concept-cards.ids", ml / "concept-cards.f16"
    ids = ids_p.read_text(encoding="utf-8").splitlines()
    if name in ids:
        return
    V = np.fromfile(vec_p, dtype=np.float16).reshape(len(ids), -1)
    a = np.asarray(vec, dtype=np.float32)
    a /= np.linalg.norm(a) + 1e-9
    V = np.vstack([V, a.astype(np.float16)])
    V.tofile(vec_p)
    ids_p.write_text(chr(10).join(ids + [name]) + chr(10), encoding="utf-8")


def upsert_vector(name, vec, kind):
    """Один вектор в Vectorize, пространство «concepts» — тем же путём, что массовая
    заливка (tools/concepts_to_vectorize.py). Живая разметка видит понятие сразу."""
    import os
    import requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    index = os.environ.get("VECTORIZE_INDEX", "b42-articles")
    if not (acc and tok):
        print("   ⚠️ вектор не залит: нет ключей Cloudflare — доедет при массовой заливке")
        return
    body = json.dumps({"id": f"c:{name}", "values": vec,
                       "namespace": "concepts", "metadata": {"kind": kind}},
                      ensure_ascii=False)
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{acc}/vectorize/v2/indexes/{index}/upsert",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/x-ndjson"},
        data=body.encode("utf-8"), timeout=120)
    if r.status_code >= 400:
        print(f"   ⚠️ вектор {name} не залит ({r.status_code}) — доедет при массовой заливке")


def main():
    ap = argparse.ArgumentParser(description="Цикл роста понятий — фабричный шаг")
    ap.add_argument("--budget", type=int, default=30, help="статей спросить за прогон")
    ap.add_argument("--dry", action="store_true", help="показать план, ничего не звать")
    a = ap.parse_args()

    # Замок общий: цикл — прогон, платный шаг внутри.
    if not a.dry:
        try:
            from tools.freeze import guard
            guard("цикл роста понятий")
        except ImportError:
            pass

    st = state()
    todo = fresh_articles(st["asked"], a.budget)
    rows = H.load_harvest()
    print(f"цикл: не спрошено статей в очереди {len(todo)} (бюджет {a.budget}) · "
          f"в копилке {len(rows)} кандидатов")

    if a.dry:
        print("— сухой прогон —")
        for aid in todo[:5]:
            print(f"   спросил бы: {aid}")
        give_birth(rows, dry=True)
        return 0

    # 1. спросить — единственный платный шаг
    asked_now = 0
    if todo:
        H.ask(todo)
        st["asked"].extend(todo)
        asked_now = len(todo)

    # 2-3. сверить и слить — на копилке целиком, идемпотентно
    rows = H.load_harvest()
    if any(r.get("matched") is None and not r.get("vec") for r in rows.values()):
        H.match()
    H.distill()

    # 4. рождение
    rows = H.load_harvest()
    born = give_birth(rows, dry=False)
    if born:
        H.save_harvest(rows)

    # 5. журнал — «увидеть процесс» живёт здесь
    rows = H.load_harvest()
    new = [r for r in rows.values() if not r.get("matched") and not r.get("born")]
    entry = {
        "when": datetime.now().isoformat(timespec="minutes"),
        "asked": asked_now,
        "candidates": len(rows),
        "waiting": len(new),
        "born": born,
        "born_total": sum(1 for r in rows.values() if r.get("born")),
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    print(f"\nитог: спрошено {asked_now} · кандидатов {len(rows)} "
          f"(ждут {len(new)}) · родилось {born}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
