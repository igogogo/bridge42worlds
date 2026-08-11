#!/usr/bin/env python3
"""Оригинальная аннотация arXiv рядом с нашим разбором. Бесплатно, без модели.

Владелец 11 августа: «в продвинутую версию добавить оригинальный абстракт на английском —
это бесплатно, быстро и даст возможность привлекать поиск по оригиналу, который могут
делать авторы; мелким текстом, во вторую очередь, и для экспрессов тоже».

Он прав по обоим пунктам. Автор ищет свою работу по её собственным словам, а у нас на
странице их нет ни одного: заголовок образный («Эхо невидимого камня»), текст — пересказ.
Для поиска наша страница по запросу «quantum energy teleportation Kondo» не существует.
Оригинальная аннотация это чинит и заодно даёт читателю сверить пересказ с источником.

Источник — НЕ сеть: `data/arxiv-bulk/<год>-<месяц>.jsonl`, 445 файлов, 3.13 млн записей с
полями id / title / abstract / authors_parsed / categories / published. Дамп уже лежит на
диске ради отбора статей, и запрашивать arXiv по одной работе незачем.

    python tools/abstract_orig.py --check      посмотреть охват, ничего не записывая
    python tools/abstract_orig.py              заполнить всем, у кого поля ещё нет
    python tools/abstract_orig.py 2310.15936   одной статье
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BULK = ROOT / "data" / "arxiv-bulk"


def _bulk_file(aid, date_str):
    """Файл дампа, где лежит эта работа.

    Сначала по её собственному номеру: у arXiv первые четыре цифры это год и месяц ПЕРВОЙ
    публикации (2310.15936 → октябрь 2023). Дата в нашем архиве — это дата, когда мы её
    разобрали, и она бывает на годы позже; по ней файл не найдётся.
    """
    m = re.match(r"^(\d{2})(\d{2})\.", aid)
    if m:
        p = BULK / f"20{m.group(1)}-{m.group(2)}.jsonl"
        if p.exists():
            return p
    p = BULK / f"{date_str[:7]}.jsonl"
    return p if p.exists() else None


def collect(targets):
    """{id: (title, abstract)} — один проход по каждому нужному файлу дампа.

    Сгруппировано по файлам, а не по статьям: месячный файл весит до 30 МБ, и открывать
    его заново на каждую статью значило бы читать одно и то же по сотне раз.
    """
    by_file = defaultdict(set)
    for aid, date_str in targets:
        f = _bulk_file(aid, date_str)
        if f:
            by_file[f].add(aid)
    got = {}
    for f, ids in sorted(by_file.items()):
        # Версия в конце нашего id (2505.00266v1) в дампе не пишется — сверяем по основе.
        base = {re.sub(r"v\d+$", "", a): a for a in ids}
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                key = r.get("id", "")
                if key in base and r.get("abstract"):
                    got[base[key]] = (r.get("title", "").strip(),
                                      " ".join(r["abstract"].split()))
                    if len(got) >= sum(len(v) for v in by_file.values()):
                        break
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aid", nargs="?")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true", help="перезаписать уже заполненные")
    args = ap.parse_args()

    paths = (list(ROOT.glob(f"lang/ru/archive/*/{args.aid}/data.json")) if args.aid
             else sorted(ROOT.glob("lang/ru/archive/*/*/data.json")))
    targets, have, total = [], 0, 0
    docs = {}
    for p in paths:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        total += 1
        if d.get("abstract_orig") and not args.force:
            have += 1
            continue
        # Авторские работы не с arXiv — искать их в дампе бессмысленно.
        if d.get("author_work"):
            continue
        docs[d["id"]] = (p, d)
        targets.append((d["id"], p.parent.parent.name))

    print(f"статей: {total}, уже с оригиналом: {have}, ищем: {len(targets)}")
    if args.check or not targets:
        found = collect(targets[:200]) if targets else {}
        if targets:
            print(f"проба по первым {min(200, len(targets))}: нашлось {len(found)}")
        return 0

    found = collect(targets)
    print(f"нашлось в дампе: {len(found)} из {len(targets)}")
    saved = 0
    for aid, (title, abstract) in found.items():
        p, d = docs[aid]
        d["abstract_orig"] = abstract
        # Оригинальное название у нас уже есть (original_title), но у старых записей
        # оно иногда пустое — заодно чиним, раз всё равно держим запись в руках.
        if title and not d.get("original_title"):
            d["original_title"] = title
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1
    print(f"✅ записано: {saved}")
    missing = len(targets) - len(found)
    if missing:
        print(f"⚠️ не нашлось: {missing} — обычно это работы, которых нет в дампе "
              f"(снят до их публикации) либо не arXiv вовсе")
    return 0


if __name__ == "__main__":
    sys.exit(main())
