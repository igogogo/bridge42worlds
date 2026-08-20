#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Волна по учёным: выбрать активных авторов, найти их непокрытые работы, собрать очередь.

Владелец 2026-08-19: «тематика — то же самое сделать для топовых авторов, и через них
вскрывать новые пласты. А то только Панов имеет привилегию. Нагоним за недельку, только
механизм допили».

ЗАЧЕМ ЧЕРЕЗ АВТОРОВ. Обычный отбор идёт по дням и по разделам: берём срез потока. У учёного
же работы связаны не темой дня, а линией мысли, которая тянется годами. Разобрав их подряд,
мы получаем не десяток разрозненных статей, а сюжет — и заодно вскрываем соседние темы, куда
по дневному отбору не забрели бы никогда. Панов тому пример: космические лучи, квантовый
эффект Зенона и динамическое обобщение уравнения Дрейка у одного человека.

ТРИ ШАГА, И ВСЕ ПРОВЕРЯЕМЫЕ:
  1. КОГО. Активные авторы нашего архива, у кого имя опознаёт человека (не «Y. Li»).
  2. ЧТО У НЕГО ЕСТЬ ЕЩЁ. Спрашиваем arXiv по имени, вычитаем то, что уже разобрали.
  3. ЧЕМ ПЛАТИМ. Список делится на полные разборы и экспрессы; файлы очереди готовы
     для run.py ids. Ни одна работа не генерится этим инструментом — он только считает.

СВЕДЕНИЕ ИМЁН. Один человек приходит под несколькими написаниями. Кандидатов ищем по
фамилии и инициалу, а подтверждаем ОБЩИМ СОАВТОРОМ: двух разных людей общая работа
случайно не связывает. Без подтверждения написания не сводим (см. author_portraits.py —
там на Панове это стоило чуть не приписанных чужих работ).

    python tools/author_wave.py --top 10 --dry        кого возьмём и сколько работ найдём
    python tools/author_wave.py --top 10              записать очереди в data/wave-authors/
    python tools/author_wave.py --author "A. D. Panov"   по одному человеку
"""
import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_DIR = ROOT / "data" / "wave-authors"
NS = {"a": "http://www.w3.org/2005/Atom"}

# Имя должно опознавать человека: хотя бы одно слово целиком, а не инициал. «Y. Li» в нашем
# архиве — десятки разных людей, и волна по такому имени соберёт работы половины Китая.
FULL_NAME = re.compile(r"(^|[\s.])[A-ZА-Я][a-zа-яё]{2,}")


# Граница «личной» работы. В коллаборации на двести имён соавторство не означает знакомства:
# любые два Чжана из CMS формально делят сотню соавторов, и по этому признаку их можно слить
# в одного человека — что сухой прогон 19 августа и сделал, собрав 196 написаний «J. Zhang».
# Поэтому и родство имён, и «активность» автора считаем ТОЛЬКО по работам небольшого круга.
PERSONAL_MAX_AUTHORS = 15


def archive_index():
    """Автор → работы у нас, автор → соавторы ПО ЛИЧНЫМ работам, автор → число личных работ."""
    by_author, coauth, personal = defaultdict(set), defaultdict(set), defaultdict(set)
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        authors = d.get("authors") or []
        aid = (d.get("id") or "").split("v")[0]
        small = len(authors) <= PERSONAL_MAX_AUTHORS
        for a in authors:
            by_author[a].add(aid)
            if small:
                coauth[a] |= set(authors) - {a}
                personal[a].add(aid)
    return by_author, coauth, personal


def surname(name):
    parts = [x for x in re.split(r"[\s.]+", name.strip()) if x]
    return parts[-1].lower() if parts else ""


def initials(name):
    """Инициалы имени без фамилии: «Alexander D. Panov» → «ad»."""
    parts = [x for x in re.split(r"[\s.]+", name.strip()) if x][:-1]
    return "".join(p[0].lower() for p in parts)


def group_variants(name, by_author, coauth):
    """Написания одного человека. Правило владельца 19.08: «лучше два, чем слить в одного».

    Поэтому сводим только при СОВПАДЕНИИ ВСЕХ признаков сразу:
      · та же фамилия;
      · совместимые инициалы (одно написание — сокращение другого, а не другое имя:
        «Alexander D.» и «A. D.» совместимы, «A. D.» и «X.» — нет);
      · не менее ДВУХ общих соавторов по личным работам. Один общий соавтор случается
        и у чужих людей из одной лаборатории;
      · кандидатов не больше четырёх. Если написаний много — это распространённая
        фамилия, а не один плодовитый человек: сухой прогон дал «Xin Zhang» из
        семнадцати написаний и «J. Zhang» из ста девяноста шести.
    Всё, что не прошло, остаётся отдельными людьми: разделить потом дешевле, чем
    объяснять учёному, почему ему приписали чужие работы.
    """
    sn, ini = surname(name), initials(name)
    same = []
    for n in by_author:
        if n == name or surname(n) != sn:
            continue
        j = initials(n)
        if not (ini.startswith(j) or j.startswith(ini)) or not (ini and j):
            continue
        if len(coauth[n] & coauth[name]) >= 2:
            same.append(n)
    if len(same) > 3:
        print(f"    ⚠️ «{name}»: похожих написаний {len(same)} — распространённая фамилия, "
              f"не свожу")
        return [name]
    return sorted([name] + same)


def arxiv_works(name, limit=60):
    """Что у этого автора есть на arXiv. Уважаем лимиты: пауза между запросами."""
    parts = [x for x in re.split(r"[\s.]+", name.strip()) if x]
    if len(parts) < 2:
        return []
    query = f'au:"{parts[-1]}_{parts[0][0]}"'
    try:
        r = requests.get("http://export.arxiv.org/api/query", timeout=40, params={
            "search_query": query, "max_results": limit,
            "sortBy": "submittedDate", "sortOrder": "descending"})
        root = ET.fromstring(r.text)
    except Exception as ex:
        print(f"    ⚠️ arXiv не ответил по «{name}»: {type(ex).__name__}")
        return []
    out = []
    for e in root.findall("a:entry", NS):
        idn = e.find("a:id", NS)
        pub = e.find("a:published", NS)
        if idn is None or pub is None:
            continue                      # запись-заглушка на неизвестный запрос
        aid = idn.text.rsplit("/", 1)[-1]
        names = [x.find("a:name", NS).text for x in e.findall("a:author", NS)]
        title = " ".join((e.find("a:title", NS).text or "").split())
        out.append({"id": aid, "base": aid.split("v")[0], "year": pub.text[:4],
                    "title": title, "authors": names,
                    "n_authors": len(names)})
    time.sleep(3)                          # бан ключа стоит дороже суток ожидания
    return out



def supports_ranking(personal, min_personal):
    """Авторы, на чьи работы машина знаний ссылается как на опоры, по убыванию.

    Опоры лежат в разделе recommend каждой разобранной статьи: у каждого направления
    есть based_on — идентификаторы работ, на которых оно держится. Считаем, сколько раз
    работы автора послужили опорой чужим рекомендациям.
    """
    from collections import Counter
    cited = Counter()
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec = (d.get("recommend") or {}).get("ru") or {}
        for direction in rec.get("directions") or []:
            for aid in direction.get("based_on") or []:
                cited[str(aid).split("v")[0]] += 1
    if not cited:
        print("  ⚠️ опор пока нет: машина знаний не размечала статьи — беру обычный отбор")
        return []
    by_id_authors = {}
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        by_id_authors[(d.get("id") or "").split("v")[0]] = d.get("authors") or []
    score = Counter()
    for aid, n in cited.items():
        for a in by_id_authors.get(aid, []):
            score[a] += n
    out = [a for a, _ in score.most_common()
           if len(personal.get(a, ())) >= min_personal and FULL_NAME.search(a)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10, help="сколько авторов взять")
    ap.add_argument("--min", type=int, default=6, help="минимум работ у нас, чтобы считать активным")
    ap.add_argument("--author", help="конкретный автор вместо подбора")
    ap.add_argument("--full", type=int, default=3, help="сколько работ каждого автора — полным разбором")
    ap.add_argument("--from-supports", action="store_true",
                    help="кандидатов брать из опор машины знаний: авторы, на чьи работы "
                         "вектор ссылается в рекомендациях чаще всего")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    by_author, coauth, personal = archive_index()

    if args.author:
        picked = [args.author]
    elif args.from_supports:
        # Владелец 19.08: «можно сначала ходить нашим вектором — мы же им ищем — или по
        # машине, которая дала опоры, потом формировать кандидатов». Опора в рекомендациях
        # это работа, на которую вектор сослался, объясняя другому автору, куда двигаться.
        # Такие работы — узлы поля: их авторы интереснее, чем просто плодовитые.
        picked = supports_ranking(personal, args.min)[:args.top]
        print(f"кандидаты из опор машины знаний: {len(picked)}")
    else:
        # Активность считаем по личным работам: сто статей коллаборации не делают
        # человека автором, которого стоит разбирать поимённо.
        cand = [(len(personal[n]), n) for n, v in by_author.items()
                if len(personal[n]) >= args.min and FULL_NAME.search(n)]
        cand.sort(reverse=True)
        picked = [n for _, n in cand[:args.top]]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_new = 0
    for name in picked:
        variants = group_variants(name, by_author, coauth)
        have = set().union(*[by_author[v] for v in variants])
        works = arxiv_works(name)
        # Работы соавторов-однофамильцев отсекаем по тому же правилу: в списке с arXiv
        # оставляем только те, где среди авторов есть одно из подтверждённых написаний.
        # Сопоставляем по фамилии и первому инициалу: arXiv отдаёт «T. Taniguchi», а у нас
        # записан «Takashi Taniguchi» — точное сравнение строк давало ноль работ у человека
        # с тысячей статей (поймано сухим прогоном 19 августа).
        keys = {(surname(v), (initials(v) or "?")[0]) for v in variants}
        mine = [w for w in works
                if any((surname(a), (initials(a) or "?")[0]) in keys for a in w["authors"])]
        new = [w for w in mine if w["base"] not in have]
        # Полный разбор — тем, где автор в узком кругу: коллаборация на сто имён это работа
        # прибора, а не человека, и разбирать её как «его работу» нечестно.
        new.sort(key=lambda w: (w["n_authors"], -int(w["year"] or 0)))
        full = [w["id"] for w in new[:args.full] if w["n_authors"] <= 12]
        express = [w["id"] for w in new if w["id"] not in full]
        total_new += len(new)
        print(f"\n{name}  (написаний: {len(variants)})")
        print(f"  у нас {len(have)} · на arXiv нашлось {len(mine)} · новых {len(new)}"
              f" → полных {len(full)}, экспрессом {len(express)}")
        for w in new[:5]:
            print(f"    {w['year']} {w['id']:16s} авторов {w['n_authors']:3d}  {w['title'][:58]}")
        if args.dry or not new:
            continue
        slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
        if full:
            (OUT_DIR / f"{slug}-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")
        if express:
            (OUT_DIR / f"{slug}-express.txt").write_text("\n".join(express) + "\n", encoding="utf-8")

    print(f"\nвсего новых работ найдено: {total_new}")
    if not args.dry:
        print(f"очереди в {OUT_DIR.relative_to(ROOT)} — дальше:")
        print("  python run.py ids --ids-file <файл>-full.txt")
        print("  python run.py ids --ids-file <файл>-express.txt --express")
        print("  python tools/author_portraits.py --variants \"Имя|Вариант\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
