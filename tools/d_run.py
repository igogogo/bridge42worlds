# -*- coding: utf-8 -*-
"""Этап D: полная пересборка сайта и сквозная проверка — по маркеру B+C.

Владелец 27.08, уходя спать: «динамику сам сможешь и публикацию сделать».
Публикацию в прод оставляем на его слово, а вот довести локальное до конца и
проверить — можно и нужно ночью.

  d-html     run.py html --force: все страницы на пяти языках заново — единая
             карточка, единая ширина, мини-графы, авторы со Scholar, вкладки
             понятий, ссылки понятий в текстах
  d-authors  страницы авторов (46 712) с блоком цитируемости
  d-status   дашборд с покрытием машины знаний
  d-checks   проверки: эндпоинты динамики, аудит реестра, аудит групп
  d-report   отчёт к утру: data/night-report.md — цифры, что выросло, что
             осталось

Пересборка идёт ПОСЛЕ всех правок данных: если запустить её раньше, страницы
соберутся на полуфабрикате, и всё придётся повторять.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PY = sys.executable
LOG = ROOT / "data" / "d.log"
STATE = ROOT / "data" / "d-state.json"
BCLOG = ROOT / "data" / "bc.log"


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


def run(step, cmd, timeout=6 * 3600, cwd=None):
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


def counts():
    """Цифры для отчёта — читаем факты, а не рассказываем по памяти."""
    out = {}
    try:
        live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))["concepts"]
        out["понятий"] = len(live)
        out["с полной записью"] = sum(1 for v in live.values() if v.get("full"))
        out["с русским переводом записи"] = sum(
            1 for v in live.values() if (v.get("full_i18n") or {}).get("ru"))
        out["с русским именем"] = sum(
            1 for v in live.values() if (v.get("names") or {}).get("ru"))
        kinds = {}
        for v in live.values():
            kinds[v.get("kind", "?")] = kinds.get(v.get("kind", "?"), 0) + 1
        out["классы"] = dict(sorted(kinds.items(), key=lambda kv: -kv[1])[:12])
    except Exception:
        pass
    try:
        an = json.loads((ROOT / "data/formula-anatomy.json").read_text(encoding="utf-8"))
        out["анатомий формул"] = len(an)
        out["из них с русским"] = sum(1 for r in an.values() if r.get("ru"))
        out["с системами единиц"] = sum(1 for r in an.values() if r.get("unit_systems"))
    except Exception:
        pass
    try:
        st = json.loads((ROOT / "data/mentions-ru-state.json").read_text(encoding="utf-8"))
        out["статей с русскими якорями"] = len(st["done"])
    except Exception:
        pass
    try:
        m = json.loads((ROOT / "data/s2/author-map.json").read_text(encoding="utf-8"))
        out["авторов сопоставлено с Scholar"] = len(m)
        out["из них с цифрами"] = sum(1 for v in m.values() if v.get("citations"))
    except Exception:
        pass
    try:
        live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))["concepts"]
        cs = [v for v in live.values() if v.get("kind") == "constant"]
        out["констант"] = len(cs)
        out["из них со значением"] = sum(1 for v in cs if v.get("value"))
    except Exception:
        pass
    return out


def report():
    c = counts()
    lines = ["# Ночь 27–28 августа: что сделано", "",
             f"Отчёт собран {time.strftime('%d.%m %H:%M')}.", "",
             "## Реестр знаний", ""]
    for k, v in c.items():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "## Цепочки", ""]
    for name, f in (("A4 — донасыщение", "a4.log"),
                    ("B+C — карточки и разметка", "bc.log"),
                    ("D — пересборка", "d.log"),
                    ("Scholar", "s2-after.log")):
        p = ROOT / "data" / f
        if not p.exists():
            lines.append(f"- {name}: не запускалась")
            continue
        done = [ln for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines()
                if "✓" in ln or "✗" in ln]
        lines.append(f"- **{name}**: шагов пройдено {len(done)}"
                     + (f", последний — {done[-1].split('] ')[-1]}" if done else ""))
    lines += ["", "## Смотреть",
              "- [Аудит реестра](/concepts-audit.html)",
              "- [Граф понятий](/lang/ru/concepts/graph.html)",
              "- [Понятие: чёрная дыра](/lang/ru/concepts/black_hole.html)",
              "- [Дашборд](/status.html) · [Пайплайн](/pipeline.html)",
              "", "Прод не тронут: динамика проверена на dev, публикация ждёт слова."]
    (ROOT / "data" / "night-report.md").write_text("\n".join(lines), encoding="utf-8")
    log("отчёт: data/night-report.md")


def main():
    log("═══ ЭТАП D: пересборка и проверка ═══")
    log("ждём финиша B+C…")
    while True:
        try:
            if "B+C ЗАВЕРШЕНЫ" in BCLOG.read_text(encoding="utf-8", errors="ignore"):
                break
        except FileNotFoundError:
            pass
        time.sleep(300)
    log("B+C завершены — полная пересборка")
    # КОНСТАНТЫ ИЗ ФОРМУЛ — до пересборки, иначе страницы соберутся без них.
    # Владелец 27.08: «константы могут в статьях не упоминаться, но об этом
    # скажут наши формулы». Шаг идемпотентен: второй запуск ничего не добавит.
    run("d-consts", [PY, "tools/constants_from_formulas.py", "--apply", "--codata"],
        timeout=900)
    run("d-units-fix", [PY, "tools/fix_truncated_units.py", "--apply"], timeout=900)
    # реестр пересобрать ПОСЛЕ констант: значение и класс живут отдельными
    # слоями, в live они попадают только сборкой
    run("d-live", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    # СВЯЗНОСТЬ для тех, кто родился этой ночью. Константы и статистика пришли не
    # из статей, а из формул и канона, поэтому групп и соседей у них нет ни одного:
    # владелец 27.08 — «сирота относительно статьи оправдана, сирот не должно быть
    # относительно связей внутри понятий». Супер считает и то и другое по карточкам,
    # значит идти он должен ПОСЛЕ карточек и вектора, то есть здесь.
    if "d-super" not in state()["done"]:
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
    # --embed обязателен. Без него супер берёт файл векторов от прошлого прогона,
    # а в нём ровно те понятия, что были на момент векторизации: родившиеся этой
    # ночью туда не попадут, и группы с соседями у них снова окажутся пустыми —
    # то есть шаг отработает и не сделает того, ради чего стоит. Векторизация
    # 3600 карточек через bge-m3 стоит доли цента.
    run("d-super", [PY, "concepts_super.py", "--embed",
                    "--reg", "data/concepts-v4.json", "--name-supers"],
        timeout=3600, cwd=ROOT.parent / "b42-ml")
    run("d-live2", [PY, "tools/wave5_apply.py", "--live-only"], timeout=1800)
    run("d-graph", [PY, "tools/concepts_graph_export.py"], timeout=1800)
    run("d-pages-c", [PY, "concepts_pages.py"], timeout=3600)
    run("d-pages-f", [PY, "formulas_pages.py"], timeout=3600)
    run("d-html", [PY, "run.py", "html", "--force"], timeout=8 * 3600)
    run("d-authors", [PY, "-c",
        "import sys; sys.path.insert(0,'.'); import generate as G; "
        "G.update_all_authors()"], timeout=4 * 3600)
    run("d-status", [PY, "-c",
        "import sys; sys.path.insert(0,'.'); import generate as G; "
        "G.generate_status_page()"], timeout=1800)
    # ОБЛАКО ДОЛЖНО УВИДЕТЬ ВЫРОСШИЙ РЕЕСТР. Без этих двух шагов dev остался бы
    # со вчерашними 3231 понятием: страницы новые, а живые списки, кадры графа и
    # смысловой поиск — старые. Данные идут в те же новые таблицы и пространство
    # «concepts»; прод не задет.
    run("d-cloud-d1", [PY, "cloudflare/concepts_sync.py"], timeout=4 * 3600)
    # Кадры графа — отдельный флаг и отдельный запуск. Без него в облаке остались
    # бы кадры, посчитанные на вчерашнем реестре: страницы новые, а граф в
    # динамике старый.
    run("d-cloud-frames", [PY, "cloudflare/concepts_sync.py", "--frames"],
        timeout=2 * 3600)
    run("d-cloud-vec", [PY, "tools/concepts_to_vectorize.py", "--apply"],
        timeout=2 * 3600)
    run("d-api", [PY, "cloudflare/checks/api_check.py"], timeout=1800)
    run("d-audit", [PY, "tools/concepts_audit.py"], timeout=1800)
    run("d-gaudit", [PY, "tools/group_integrity.py", "--audit"], timeout=1800)
    report()
    log("═══ D ЗАВЕРШЁН — всё готово к смотру владельца ═══")
    return 0


if __name__ == "__main__":
    import os
    os.environ.setdefault("B42_LEAD", "1")
    sys.exit(main())
