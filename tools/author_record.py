#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полный список работ автора — из НАШЕГО дампа arXiv, без обращений к сети.

Владелец 2026-08-19: «у нас есть полная база офлайн, мы качали её»; «дашборд и описание —
по всем его статьям, а не только по тем, что мы перебрали».

Он прав дважды. Во-первых, ходить в arXiv API за списком работ незачем: в data/arxiv-bulk
лежат 445 месячных файлов на 4 ГБ, и в каждой записи уже есть разобранные авторы
(authors_parsed). Во-вторых, честный дашборд автора показывает ВСЕ его работы, а наши
разборы — как покрытие поверх них: видно и сколько человек публикует, и насколько мы за
ним успеваем. Страница, где у Панова «16 работ», говорит неправду о человеке, у которого
их под сотню.

КАК СОПОСТАВЛЯЮТСЯ ИМЕНА. В дампе автор записан как ['Panov', 'A. D.', ''], у нас на
странице — «A. D. Panov». Ключом служит фамилия плюс первый инициал: «panov|a». Это
намеренно грубый ключ — он объединяет A. Panov и A. D. Panov, но НЕ объединяет их с
B. Panov. Более тонкое различение имени человек сделает сам, письмом (см. решение
владельца о раздельных страницах для однофамильцев).

    python tools/author_record.py --build          построить индекс по нашим авторам
    python tools/author_record.py --show "A. D. Panov"
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import write_json_atomic  # noqa: E402

DUMP = ROOT / "data" / "arxiv-bulk"
OUT = ROOT / "data" / "author-records.json"


def _first_cat(cats):
    if isinstance(cats, list):
        return str(cats[0]) if cats else ""
    return str(cats or "").split(" ")[0]


def key_from_parts(surname, given):
    """Ключ автора: фамилия + ВСЕ инициалы имени.

    Первая версия брала один инициал, и владелец сразу поймал результат: у ключа «panov|a»
    оказалось 171 работа с 1998 по 2026 год — при том что разобрали мы 19. Под этим ключом
    слиплись разные люди: A. D. Panov из космических лучей, A. N. Panov из алгебры и все
    прочие Пановы на букву А. Полные инициалы разводят их: «panov|ad» и «panov|an».
    Оставшиеся сомнения решаются в пользу разделения — по решению владельца лучше две
    страницы, чем одна с чужими работами.
    """
    sn = re.sub(r"[^a-zа-яё]", "", (surname or "").lower())
    ini = "".join(w[0].lower() for w in re.split(r"[\s.\-]+", (given or "")) if w[:1].isalpha())
    return f"{sn}|{ini}" if sn and ini else ""


def key_from_display(name):
    """Тот же ключ, но из отображаемого имени «A. D. Panov» или «Alexander Panov»."""
    parts = [p for p in re.split(r"[\s.]+", (name or "").strip()) if p]
    if len(parts) < 2:
        return ""
    return key_from_parts(parts[-1], " ".join(parts[:-1]))


def our_authors():
    """Имена авторов, встречающиеся в нашем архиве: только их и индексируем."""
    names = set()
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        names.update(d.get("authors") or [])
    return names


def ours_by_key(names):
    """Ключ → отображаемые имена и наши работы под ними."""
    by_key = defaultdict(lambda: {"names": set(), "ours": {}})
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = (d.get("id") or "").split("v")[0]
        kind = "express" if d.get("express") else "full"
        date = d.get("date", "")
        for a in d.get("authors") or []:
            k = key_from_display(a)
            if not k:
                continue
            by_key[k]["names"].add(a)
            by_key[k]["ours"][aid] = {"date": date, "kind": kind,
                                      "km": bool((d.get("recommend") or {}).get("ru"))}
    return by_key


def build():
    names = our_authors()
    print(f"авторов в нашем архиве: {len(names)}")
    by_key = ours_by_key(names)
    want = set(by_key)
    print(f"ключей (фамилия+инициал): {len(want)}")

    files = sorted(DUMP.glob("*.jsonl"))
    print(f"месячных файлов дампа: {len(files)}")
    total = defaultdict(list)
    given = defaultdict(set)
    seen = 0
    for i, f in enumerate(files, 1):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                seen += 1
                for parts in d.get("authors_parsed") or []:
                    k = key_from_parts(parts[0] if parts else "",
                                       parts[1] if len(parts) > 1 else "")
                    if k in want:
                        # Полное написание имени из дампа: по числу РАЗНЫХ написаний под
                        # одним ключом видно, один это человек или толпа. У «panov|ad» их
                        # два («A. D.», «Alexander D.»), у «wang|y» — сотни: Yi, Yu, Yan,
                        # Ying, Yong. Это самый прямой измеритель неоднозначности, какой
                        # можно получить из самих данных, без догадок о происхождении имени.
                        given[k].add((parts[1] if len(parts) > 1 else "").strip())
                        total[k].append({
                            "id": d.get("id", ""),
                            "y": (d.get("published") or "")[:4],
                            # categories в дампе — список ['cs.CV'], но в старых месяцах
                            # встречается строка через пробел. Поддерживаем оба вида:
                            # из-за молчаливого расхождения области выходили пустыми.
                            "c": _first_cat(d.get("categories")),
                        })
        if i % 50 == 0:
            print(f"  {i}/{len(files)} файлов · записей просмотрено {seen:,}"
                  .replace(",", " "))

    out = {}
    for k, works in total.items():
        info = by_key[k]
        years = sorted({w["y"] for w in works if w["y"].isdigit()})
        ours = info["ours"]
        # Неоднозначный ключ: под ним слишком много разных написаний имени, значит это
        # не человек, а совпадение фамилии и инициалов. Владелец 19.08: «с китайскими
        # именами осторожно, лучше два, чем слить в одного»; «поработай с базой, чтобы
        # она не часто ошибалась, это важно». Для таких ключей мы НЕ показываем полный
        # список работ с arXiv и не считаем это чьей-то биографией — показываем только
        # наши разборы под этим написанием и говорим об этом прямо.
        variants = {g for g in given[k] if g}
        ambiguous = len(variants) > 6 or len(works) > 400
        out[k] = {
            "ambiguous": ambiguous,
            "given_variants": len(variants),
            "names": sorted(info["names"]),
            "arxiv_total": len(works),
            "arxiv_by_year": _count_by_year(works),
            "first_year": years[0] if years else "",
            "last_year": years[-1] if years else "",
            "fields": _top_fields(works),
            "ours": ours,
            "ours_by_year": _count_by_year(
                [{"y": v["date"][:4]} for v in ours.values() if v.get("date")]),
        }
    write_json_atomic(OUT, out, indent=0)
    print(f"\n✅ {OUT.relative_to(ROOT)} · авторов {len(out)}"
          f" · работ учтено {sum(v['arxiv_total'] for v in out.values()):,}".replace(",", " "))
    return 0


def _count_by_year(works):
    c = defaultdict(int)
    for w in works:
        y = (w.get("y") or "")[:4]
        if y.isdigit():
            c[y] += 1
    return dict(sorted(c.items()))


def _top_fields(works, limit=4):
    c = defaultdict(int)
    for w in works:
        cat = (w.get("c") or "").split(".")[0]
        if cat:
            c[cat] += 1
    return [k for k, _ in sorted(c.items(), key=lambda x: -x[1])[:limit]]


def show(name):
    if not OUT.exists():
        print("индекса нет, сначала --build")
        return 1
    d = json.loads(OUT.read_text(encoding="utf-8"))
    k = key_from_display(name)
    e = d.get(k)
    if not e:
        print(f"нет данных по ключу {k}")
        return 1
    print(f"ключ {k} · написания: {', '.join(e['names'])}")
    print(f"работ на arXiv: {e['arxiv_total']} ({e['first_year']}–{e['last_year']})")
    print(f"разобрано нами: {len(e['ours'])}")
    print(f"области: {', '.join(e['fields'])}")
    print("по годам (arXiv / наши):")
    for y in sorted(e["arxiv_by_year"]):
        print(f"   {y}  {e['arxiv_by_year'][y]:3d} / {e['ours_by_year'].get(y, 0)}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--show")
    args = ap.parse_args()
    if args.build:
        return build()
    if args.show:
        return show(args.show)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
