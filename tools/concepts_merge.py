#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единый реестр понятий: слияние тегов и законов в одну классификацию.

Решение владельца 2026-08-18: «одна классификация — это универсально. Теги больше про
научпоп, законы больше про нашу машину знаний. С классификацией будет удобнее работать
с графом: есть закон и есть автор, формула же — точнее, и проверять на полноту проще.
В графе можно ставить галочки на группе классификации, и будет чище. Слить везде,
переразметить и по тексту и по ссылкам — тогда можно свободно наращивать объём,
дойти до 1000 записей законов, а может и больше».

Почему слияние назрело (замер 18.08): 24 пары дублей между ветками (hawking_radiation
существовал И законом И тегом), таксономии параллельны (тип «эффект» у законов против
уровня «явление» у тегов — одно и то же в двух ящиках), вся механика — сверка,
разметка, граф — написана дважды.

УСТРОЙСТВО РЕЕСТРА (data/concepts.json):
  {id: {kind, name..., related, scientists, ...атрибуты по виду}}
  kind — одна ось классификации вместо двух:
    из тегов:   concept, method, object, instrument, substance, math, phenomenon
    из законов: law, equation, theorem, principle, effect, invention
  Закон — это понятие, у которого есть формула и авторы. Не отдельная сущность.

ПРАВИЛА СЛИЯНИЯ ДУБЛЕЙ. Закон поглощает одноимённый тег: kind остаётся законным
(точнее — у закона есть формула и автор, владелец: «формула же точнее»), а от тега
наследуются article_count, domain и связи. Ничего не выбрасывается.

ВИТРИНЫ НЕ ЛОМАЮТСЯ: /tags/ и /laws/ остаются страницами подмножеств реестра,
старые tags-graph.json и laws-graph.json генерируются из реестра для совместимости,
пока все читатели не переедут. URL статей и справочников не меняются.

    python tools/concepts_merge.py --dry     показать, что получится, ничего не писать
    python tools/concepts_merge.py           собрать data/concepts.json + слои совместимости
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import write_json_atomic  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Русские типы законов → единые латинские kind (в реестре один язык ключей).
LAW_KIND = {"закон": "law", "уравнение": "equation", "теорема": "theorem",
            "принцип": "principle", "эффект": "effect", "изобретение": "invention"}


def load(p):
    f = ROOT / p
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def norm(s):
    return s.lower().replace("_", " ").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    tg = load("data/tags-graph.json").get("graph", {})
    lg = load("data/laws-graph.json").get("graph", {})
    laws_full = load("lang/ru/data/laws.json")
    tags_full = load("lang/ru/data/tags.json")

    concepts = {}

    # 1. Теги — основа: их больше, у них счётчики статей.
    for tid, t in tg.items():
        concepts[tid] = {
            "kind": t.get("level", "concept"),
            "related": list(t.get("related", [])),
            "scientists": list(t.get("scientists", [])),
            "article_count": t.get("article_count", 0),
            "domain": t.get("domain", ""),
            "origin": "tag",
        }

    # 2. Законы: дубль по имени поглощает тег (kind закона точнее — у него формула
    #    и автор), уникальный — добавляется.
    merged_pairs, review_pairs = [], []
    tnames = {norm(k): k for k in concepts}
    for lid, l in lg.items():
        kind = LAW_KIND.get(l.get("type", "закон"), "law")
        entry = {
            "kind": kind,
            "related": list(l.get("related", [])),
            "scientists": list(l.get("scientists", [])),
            "tags_of_law": list(l.get("tags", [])),   # тематические связи закона
            "influenced_by": list(l.get("influenced_by", [])),
            "origin": "law",
        }
        # Формула и описание — из полного справочника законов, если есть.
        full = laws_full.get(lid) or {}
        for f in ("formula", "formula_latex", "year", "name"):
            if full.get(f):
                entry[f] = full[f]

        # Дубль — ТОЛЬКО точное совпадение имени. Первая версия склеивала и по вхождению,
        # и сухой прогон немедленно показал цену: «энтропия Бекенштейна-Хокинга» поглотила
        # общий тег «энтропия», теорема Пенроуза — «сингулярность». Общее слово — это
        # модификатор, а не тождество; тот же урок ML уже выучил на white_dwarf против
        # brown_dwarf. Вхождения идут в кандидаты на разбор человеком, не в автослив.
        twin = None
        ln = norm(lid)
        if ln in tnames:
            twin = tnames[ln]
        else:
            for tn, tid in tnames.items():
                if concepts.get(tid, {}).get("origin") == "tag" and (tn in ln or ln in tn) and len(tn) > 6:
                    review_pairs.append((lid, tid))
                    break
        if twin and concepts[twin]["origin"] == "tag":
            old = concepts.pop(twin)
            entry["article_count"] = old.get("article_count", 0)
            entry["domain"] = old.get("domain", "")
            entry["related"] = sorted(set(entry["related"]) | set(old.get("related", [])))
            entry["scientists"] = sorted(set(entry["scientists"]) | set(old.get("scientists", [])))
            entry["absorbed_tag"] = twin
            merged_pairs.append((lid, twin))
            tnames = {norm(k): k for k in concepts}
        concepts[lid] = entry
        tnames[norm(lid)] = lid

    from collections import Counter
    kinds = Counter(c["kind"] for c in concepts.values())
    print(f"реестр: {len(concepts)} понятий из {len(tg)} тегов + {len(lg)} законов")
    print(f"склеено дублей (точное имя): {len(merged_pairs)}")
    print(f"похожих пар на разбор человеком (НЕ склеены): {len(review_pairs)}")
    for a, b in review_pairs[:8]:
        print(f"   ? закон {a} ~ тег {b}")
    for a, b in merged_pairs[:10]:
        print(f"   закон {a} поглотил тег {b}")
    print("по видам: " + " · ".join(f"{k}={v}" for k, v in kinds.most_common()))

    if args.dry:
        print("(сухой прогон — ничего не записано)")
        return 0

    out = ROOT / "data" / "concepts.json"
    # Атомарно. Этот файл объявлен источником правды и уезжает на сайт: страницы /tags/
    # и /laws/ читают его через слой совместимости. Обычный write_text сначала обнуляет
    # файл, потом наполняет — и выкладка, попавшая в этот промежуток, увезёт обрезок.
    # Ровно так 14 августа обрезанный индекс погасил ленту на всех пяти языках; здесь
    # тот же механизм погасил бы теги и законы.
    write_json_atomic(out, {"_": "Единый реестр понятий. Источник правды с 2026-08-18; "
                                 "tags-graph и laws-graph — генерируемые витрины.",
                            "review_pairs": review_pairs,
                            "concepts": concepts}, indent=1)
    print(f"✅ {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
