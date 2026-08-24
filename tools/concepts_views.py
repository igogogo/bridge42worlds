#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Витрины /tags/ и /laws/ из единого реестра — слой совместимости.

Решение владельца 18.08: одна классификация. `tools/concepts_merge.py` собрал реестр
`data/concepts.json` ИЗ витрин — это был разовый шаг. Дальше направление обратное:
реестр источник правды, а `data/tags-graph.json` и `data/laws-graph.json` —
генерируемые представления. Пока так: витрины читают полтора десятка мест в
generate.py, и переписывать их разом означало бы менять реестр и все страницы одним
коммитом, без возможности откатиться по частям.

Что делает слой: раскладывает 535 понятий обратно на два старых формата, переводя
единый `kind` в те поля, которых ждут читатели (`level` у тегов, русский `type` у
законов). Ничего не выдумывает — только переименование и раскладка.

ПОГЛОЩЁННЫЕ ТЕГИ. Три понятия (hawking_radiation, gravitational_lensing,
casimir_effect) пришли из законов и поглотили одноимённые теги. В витрину тегов они
обязаны попасть: на них ссылаются статьи, и без записи страница тега пропала бы.
Поэтому правило витрины тегов — origin == "tag" ИЛИ есть absorbed_tag; сходится
ровно в 363 записи, как в старом файле.

ПРИЗНАК educational РЕЕСТР НЕ ХРАНИТ, и это не мелочь: 136 тегов из 363 —
образовательные, generate.py печатает их курсивом в списке. Восстанавливаем из
lang/ru/data/tags-list-educational.json, а не выдумываем.

    python tools/concepts_views.py --dry     сверить с нынешними витринами, ничего не писать
    python tools/concepts_views.py           записать витрины
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONCEPTS = ROOT / "data" / "concepts.json"
TAGS_VIEW = ROOT / "data" / "tags-graph.json"
LAWS_VIEW = ROOT / "data" / "laws-graph.json"
EDU_LIST = ROOT / "lang" / "ru" / "data" / "tags-list-educational.json"

# Обратная сторона LAW_KIND из concepts_merge: витрина законов говорит по-русски.
KIND_RU = {"law": "закон", "equation": "уравнение", "theorem": "теорема",
           "principle": "принцип", "effect": "эффект", "invention": "изобретение",
           # Виды, пришедшие из тегов, — тоже группы единого облака (одно облако, 24.08).
           "concept": "понятие", "method": "метод", "object": "объект",
           "instrument": "инструмент", "substance": "вещество", "math": "математика",
           "phenomenon": "явление"}
LAW_KINDS = set(KIND_RU)


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else (default or {})


def educational_ids():
    """Кто из тегов образовательный. Реестр этого не знает — берём из списка."""
    out = set()
    for row in load(EDU_LIST, []):
        if isinstance(row, dict) and row.get("en"):
            out.add(row["en"])
    return out


def build_views(concepts):
    edu = educational_ids()
    tags, laws = {}, {}
    for cid, c in concepts.items():
        origin, kind = c.get("origin"), c.get("kind", "concept")
        if origin == "tag" or c.get("absorbed_tag"):
            node = {
                "level": kind,
                "domain": c.get("domain", ""),
                "related": list(c.get("related", [])),
                "article_count": c.get("article_count", 0),
                "scientists": list(c.get("scientists", [])),
            }
            # Поле пишем ВСЕГДА, а не только у образовательных: старая витрина хранит
            # и False, и читатели вправе на это опираться. Слой совместимости не должен
            # менять форму записи — он только меняет источник.
            node["educational"] = cid in edu
            tags[cid] = node
        # ОДНО ОБЛАКО (владелец 2026-08-24: «слив в одно облако окончательно, на сайте
        # убрав отовсюду теги; в законах есть понятия, и этого достаточно»). Витрина
        # законов из подмножества становится ПОЛНОЙ: каждая запись реестра — страница
        # раздела «Понятия». Бывшие теги получают русский вид по своему kind, чтобы
        # группировка на облаке работала для всех, а не только для шести законных видов.
        laws[cid] = {
            "type": KIND_RU.get(kind, "закон"),
            "tags": list(c.get("tags_of_law", [])),
            "scientists": list(c.get("scientists", [])),
            "influenced_by": list(c.get("influenced_by", [])),
            "related": list(c.get("related", [])),
            "article_count": c.get("article_count", 0),
        }
    return tags, laws


def compare(name, made, have):
    """Сверка с тем, что лежит сейчас. Молчаливая потеря записей здесь означала бы
    исчезнувшие страницы, поэтому расхождения печатаем поимённо."""
    lost = sorted(set(have) - set(made))
    new = sorted(set(made) - set(have))
    print(f"{name}: собрано {len(made)}, было {len(have)}"
          f"{' · пропало ' + str(len(lost)) if lost else ''}"
          f"{' · добавилось ' + str(len(new)) if new else ''}")
    for cid in lost[:10]:
        print(f"    ПРОПАЛО: {cid}")
    for cid in new[:10]:
        print(f"    новое: {cid}")
    # поля сравниваем на общих записях: важно не только «сколько», но и «то же ли»
    diff = 0
    for cid in sorted(set(made) & set(have)):
        for f, v in have[cid].items():
            mv = made[cid].get(f)
            if isinstance(v, list) and isinstance(mv, list):
                if sorted(map(str, v)) != sorted(map(str, mv)):
                    diff += 1
                    if diff <= 6:
                        print(f"    ≠ {cid}.{f}: было {len(v)}, стало {len(mv)}")
            elif v != mv:
                diff += 1
                if diff <= 6:
                    print(f"    ≠ {cid}.{f}: было {v!r}, стало {mv!r}")
    print(f"    расхождений по полям: {diff}")
    return len(lost), diff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="сверить и не писать")
    args = ap.parse_args()

    reg = load(CONCEPTS)
    concepts = reg.get("concepts") or {}
    if not concepts:
        print("нет data/concepts.json — сначала tools/concepts_merge.py")
        return 1
    tags, laws = build_views(concepts)

    have_t = load(TAGS_VIEW).get("graph", {})
    have_l = load(LAWS_VIEW).get("graph", {})
    lost_t, diff_t = compare("теги", tags, have_t)
    lost_l, diff_l = compare("законы", laws, have_l)

    if args.dry:
        print("\n(сухо) ничего не записано")
        return 0
    if lost_t or lost_l:
        print("\nОТКАЗ: витрина потеряла бы записи — это исчезнувшие страницы. "
              "Разберись с реестром прежде чем писать.")
        return 1
    from common import write_json_atomic
    write_json_atomic(TAGS_VIEW, {"graph": tags}, indent=None)
    write_json_atomic(LAWS_VIEW, {"graph": laws}, indent=None)
    print(f"\n✅ витрины записаны: {len(tags)} тегов, {len(laws)} законов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
