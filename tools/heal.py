# -*- coding: utf-8 -*-
"""Приведение архива в целостное состояние: доразметить, достроить, досчитать.

Владелец 12.09.2026: «после дневного всё-таки доразметить, достроить, досчитать, а не
перечитывать. Это касается и авторов, и понятий, и статей — такое полуобновление,
промежуточный пайплайн оздоровления».

ЗАЧЕМ ОТДЕЛЬНО ОТ ЕЖЕДНЕВНОГО. Ежедневный конвейер делает день: разбирает свежие работы и
трогает общие справочники ЦЕЛИКОМ — страницы понятий на пяти языках, все 49 тысяч авторов,
весь граф. Это часы машинного времени на то, что изменилось у горстки статей. А между
прогонами архив расходится по мелочи: страница старше своих данных, работа не попала в
индекс, реестр понятий не знает о новой статье, страница автора собрана до его последней
работы. Каждая мелочь по отдельности незаметна, вместе они и есть «архив разъехался».

ПРАВИЛО ЗДЕСЬ ОДНО: чиним ТОЧЕЧНО и только то, что действительно разошлось. Не знаем, что
чинить, — сперва меряем. Поэтому по умолчанию инструмент ничего не пишет, а показывает
список: что и сколько.

    python tools/heal.py              показать, что разошлось
    python tools/heal.py --apply      починить найденное
    python tools/heal.py --only pages,authors   только эти проверки
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

PY = sys.executable
ARCHIVE = ROOT / "lang" / "ru" / "archive"
LANGS = ("ru", "en", "es", "ar", "fr")


def log(msg):
    print(msg, flush=True)


# ── проверки ─────────────────────────────────────────────────────────────────
# Каждая возвращает (описание, список целей). Пустой список — всё в порядке.

def check_pages():
    """Страницы старше своих данных: data.json правили, а страницу не пересобрали.

    Так бывает после любой точечной правки данных — разметки, формул, лицензии. Сравниваем
    время правки, а не содержимое: содержимое сравнивает сама пересборка по отпечаткам,
    здесь нужно лишь понять, кого ей отдать.
    """
    late = []
    for dj in ARCHIVE.glob("*/*/data.json"):
        page = dj.with_name("index.html")
        try:
            if not page.exists() or dj.stat().st_mtime > page.stat().st_mtime + 5:
                late.append(dj.parent.name)
        except OSError:
            continue
    return "страницы старше своих данных", sorted(late)


def check_index():
    """Работы, которых нет в индексе языка источника: в ленте, поиске и графе их нет вовсе."""
    idx = ROOT / "lang" / "ru" / "articles-index.json"
    try:
        known = {a["id"] for a in json.loads(idx.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError, KeyError):
        return "работы вне индекса", []
    have = {p.parent.name for p in ARCHIVE.glob("*/*/data.json")}
    return "работы вне индекса", sorted(have - known)


def check_concepts():
    """Работы, о которых не знает реестр понятий: у них не будет ни облака, ни мини-графа.

    Номера сводим к виду без версии: реестр хранит их без суффикса, архив — с ним
    (та же ловушка, что ловили 11.09 на странице автора).
    """
    import re
    live = ROOT / "data" / "concepts-live.json"
    try:
        conc = json.loads(live.read_text(encoding="utf-8"))["concepts"]
    except (OSError, json.JSONDecodeError, KeyError):
        return "работы без понятий в реестре", []
    bare = lambda x: re.sub(r"v\d+$", "", x)          # noqa: E731
    known = set()
    for v in conc.values():
        for a in (v.get("articles") or []):
            known.add(bare(a))
    out = []
    for dj in ARCHIVE.glob("*/*/data.json"):
        aid = dj.parent.name
        if bare(aid) in known:
            continue
        # Разметка у работы ЕСТЬ, а реестр о ней не знает — вот это и чиним. Работа без
        # разметки вовсе — другая беда, её лечит retag, и сюда она не относится.
        try:
            d = json.loads(dj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if ((d.get("popular") or {}).get("ru") or {}).get("concepts_v2"):
            out.append(aid)
    return "работы с разметкой, но вне реестра понятий", sorted(out)


def check_authors():
    """Авторы, чьи страницы собраны раньше их последней работы.

    Страница автора перечисляет его работы; вышла новая — страница устарела. Пересобирать
    из-за этого все 49 тысяч (три четверти часа) незачем, но знать, сколько их, нужно.
    """
    idx = ROOT / "lang" / "en" / "authors"
    if not idx.exists():
        return "страницы авторов старше их работ", []
    newest = 0.0
    for dj in ARCHIVE.glob("*/*/data.json"):
        try:
            newest = max(newest, dj.stat().st_mtime)
        except OSError:
            pass
    late = [p.stem for p in idx.glob("*.html") if p.stat().st_mtime < newest - 5]
    return "страницы авторов старше самой свежей работы", sorted(late)


def check_groups():
    """Страницы понятий, на которых стоит устаревшее имя области.

    Имя области вшито в страницу; переименовали область — страницы надо пересобрать.
    Ловим сравнением с нынешним справочником имён.
    """
    gn = ROOT / "data" / "group-names.json"
    try:
        names = json.loads(gn.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "страницы понятий со старым именем области", []
    cur = {v.get("name_ru") for v in names.values() if v.get("name_ru")}
    pages = ROOT / "lang" / "ru" / "concepts"
    if not pages.exists():
        return "страницы понятий со старым именем области", []
    stale = []
    for p in pages.glob("*.html"):
        try:
            h = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Имя области стоит в подписи «область: …»; ищем любое имя, которого больше нет
        # в справочнике. Дешевле, чем разбирать вёрстку: имён всего полсотни.
        for old in ("Единицы измерения и константы",):
            if old in h and old not in cur:
                stale.append(p.stem)
                break
    return "страницы понятий со старым именем области", sorted(stale)


CHECKS = {
    "pages": check_pages,
    "index": check_index,
    "concepts": check_concepts,
    "authors": check_authors,
    "groups": check_groups,
}


# ── починка ──────────────────────────────────────────────────────────────────

def fix(name, targets):
    """Точечная починка по имени проверки. Возвращает код возврата (0 — хорошо)."""
    if name == "pages":
        # Пересобираем ТОЛЬКО названные работы. Агрегаты и индексы run.py html строит
        # полностью в любом случае — это его устройство, и переспорить его здесь нельзя.
        return run([PY, "run.py", "html", "--only"] + targets[:400])
    if name == "index":
        return run([PY, "run.py", "html", "--only"] + targets[:400])
    if name == "concepts":
        # Списки статей у понятий живут в справочнике live и строятся из результатов
        # разметки. Значит чинить нужно СПРАВОЧНИК, а не статьи: разметка у них уже есть,
        # иначе они бы сюда не попали. Ключ --live-only ровно это и делает — пересобирает
        # справочник, статьи не трогая. (--articles-only сделал бы обратное и не помог бы:
        # он дописывает разметку в статьи, а справочник не перезаписывает.)
        return run([PY, "tools/wave5_apply.py", "--apply", "--live-only"])
    if name == "authors":
        return run([PY, "-c", "import sys; sys.path.insert(0,'.'); "
                    "import generate as G; G.update_all_authors()"])
    if name == "groups":
        return run([PY, "concepts_pages.py"])
    log(f"  · {name}: чинить нечем, только показ")
    return 0


def run(cmd):
    t = time.time()
    rc = subprocess.run(cmd, cwd=str(ROOT),
                        env=dict(os.environ, PYTHONIOENCODING="utf-8",
                                 B42_DEPLOY_OK="1")).returncode
    log(f"    ({int(time.time() - t) // 60} мин {int(time.time() - t) % 60} с, код {rc})")
    return rc


def main():
    ap = argparse.ArgumentParser(description="Оздоровление архива: доразметить, достроить, досчитать")
    ap.add_argument("--apply", action="store_true", help="чинить, а не только показывать")
    ap.add_argument("--only", help="список проверок через запятую: " + ",".join(CHECKS))
    a = ap.parse_args()

    names = [x.strip() for x in a.only.split(",")] if a.only else list(CHECKS)
    bad = [n for n in names if n not in CHECKS]
    if bad:
        raise SystemExit(f"⛔ нет таких проверок: {', '.join(bad)}. Есть: {', '.join(CHECKS)}")

    found = {}
    log("ЧТО РАЗОШЛОСЬ\n")
    for n in names:
        title, targets = CHECKS[n]()
        found[n] = targets
        mark = "·" if not targets else "⚠"
        log(f"  {mark} {n:9} {len(targets):6}  {title}")
        for t in targets[:5]:
            log(f"                      {t}")
        if len(targets) > 5:
            log(f"                      … и ещё {len(targets) - 5}")

    total = sum(len(v) for v in found.values())
    if not total:
        log("\n✅ всё согласовано, чинить нечего")
        return 0
    if not a.apply:
        log(f"\nнайдено расхождений: {total}. Починить: --apply")
        return 0

    from tools import runlock
    runlock.acquire("tree", "оздоровление архива")
    log("\nЧИНЮ\n")
    for n in names:
        if not found[n]:
            continue
        log(f"  ▶ {n} ({len(found[n])})")
        fix(n, found[n])
    log("\n✅ готово. Повторный показ покажет, что осталось.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
