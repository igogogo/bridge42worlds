#!/usr/bin/env python3
"""Пласты: машина знаний просит — поле отвечает историческими работами.

Владелец 30 августа: «пайплайн обработки от машины знаний: ищем статьи, поднимаем
пласты, обрабатываем вектором, чтобы ещё исторические статьи поднимались до полных
или новые… хотя бы делать несколько разборов важных статей и находить их в прошлом».

ЗАЧЕМ ЭТО ОТДЕЛЬНЫЙ ПАЙПЛАЙН. Ежедневный отбор смотрит на СЕГОДНЯ: что вышло за
день, что из этого интереснее. Он не умеет и не должен уметь спрашивать «а чего нам
не хватает вообще» — у него нет такого вопроса. Этот вопрос есть у машины знаний:
она знает, какие понятия стоят без опоры, какие кандидаты не дорастают, где реестр
жидкий. Отсюда и берётся спрос, а предложение лежит в поле — 2,96 млн работ arXiv
с 1991 года, вектор которых у нас на диске.

КАК СЧИТАЕМ. Спрос — это вектор: у каждого понятия есть карточка, у карточки есть
вектор bge-m3, тот же, которым размечены статьи. Значит «найти в прошлом работы про
это понятие» — одно умножение матриц, без единого запроса к модели и без сети.
Один проход по полю отвечает СРАЗУ ВСЕМ запросам: поле читается с диска один раз,
а не по разу на понятие.

  спрос      понятия с опорой меньше MIN_ARTS статей (реестр знает точно) +
             кандидаты, которым не хватило статей, чтобы родиться
  поле       ../b42-ml/data/field.f16 — 2,96 млн работ, нормализованный bge-m3
  отбор      ближайшие к запросу работы, которых у нас ЕЩЁ НЕТ
  важность   цитируемость Semantic Scholar по короткому списку финалистов:
             вектор говорит «про это», Scholar говорит «и это читают»

ЧЕГО ЗДЕСЬ НЕТ И ПОЧЕМУ. Здесь не вызывается ни одна платная модель. Пайплайн
только НАХОДИТ и РАНЖИРУЕТ; генерацией разборов занимается тот же путь, что и всегда
(run.py ids --full), и решение потратить на неё деньги принимает человек или ночной
прогон — но не эта команда.

    python tools/strata.py --scan            чего просит машина знаний (секунда)
    python tools/strata.py --pick 40         найти в поле, отранжировать, записать
    python tools/strata.py --pick 40 --cite  + цитируемость по финалистам (сеть)
    python tools/strata.py --ids             только идентификаторы, для run.py ids
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIVE = ROOT / "data" / "concepts-live.json"
HARVEST = ROOT / "data" / "concept-harvest.jsonl"
OUT = ROOT / "data" / "strata-picks.json"

# Понятие с опорой меньше пяти статей — то самое «не дорос»: оно есть в реестре,
# у него есть страница, а стоять на ней нечему. Это и есть спрос.
MIN_ARTS = 5
# Сколько работ поля берём на одно понятие. Больше пяти не нужно: дальше идут
# соседи соседей, и разбор перестаёт быть про то, зачем его заказывали.
PER_CONCEPT = 5
# Ниже этой близости работа «вообще про другое». Порог тот же, что у живой
# разметки (retag_hub, сырая планка) — одна шкала на весь проект.
MIN_SIM = 0.55
# Поле читается кусками: 2,96 млн × 1024 float16 это 5,6 ГБ, целиком в память
# класть незачем и незачем ждать.
CHUNK = 100_000


def bare(aid):
    """Идентификатор работы без приставки поля и без версии.

    Поле зовёт работу «arx:quant-ph/9601025», наш архив — папкой «2608.21711v1»,
    Scholar ждёт «quant-ph/9601025». Три написания одного и того же; если их не
    свести, отсев «уже разобранных» молча пропустит всё, а запрос цитируемости
    уйдёт в никуда — обе ошибки тихие, и обе были здесь при первом прогоне.
    """
    a = str(aid)
    if a.startswith("arx:"):
        a = a[4:]
    # версия только у нашего написания и только в хвосте после точки-цифр
    if "/" not in a and "v" in a:
        head = a.rsplit("v", 1)
        if head[-1].isdigit():
            a = head[0]
    return a


def ours():
    """Идентификаторы работ, которые у нас уже разобраны — их поле не предлагает."""
    have = set()
    arch = ROOT / "lang" / "ru" / "archive"
    for day in arch.iterdir():
        if not day.is_dir():
            continue
        for art in day.iterdir():
            if art.is_dir():
                # Папка зовётся с версией (2608.21711v1), поле — без неё.
                have.add(bare(art.name))
    return have


def demand():
    """Чего просит машина знаний: понятие → зачем оно в списке.

    Два источника, и они разной природы. Реестр — про то, что УЖЕ признано
    понятием, но стоит без статей: страница есть, читать нечего. Копилка добычи —
    про то, что понятием ещё не стало ровно потому, что статей не хватило: пять
    работ из поля могут его родить.
    """
    want = {}
    reg = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    for cid, v in reg.items():
        if v.get("merged_into"):
            continue
        n = len(v.get("articles") or [])
        if n < MIN_ARTS:
            want[cid] = {"why": "реестр: опора мала", "arts": n,
                         "name": (v.get("names") or {}).get("ru")
                                 or (v.get("names") or {}).get("en") or cid}
    if HARVEST.exists():
        with HARVEST.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("born") or r.get("matched"):
                    continue
                nm = r.get("name")
                if not nm or nm in want:
                    continue
                n = len(r.get("articles") or [])
                if n < MIN_ARTS:
                    # Вектор кандидата УЖЕ ПОСЧИТАН — на сверке с реестром, тем же
                    # bge-m3. Значит спросить поле от его имени можно ничего не
                    # считая: карточки в матрице понятий у него нет и быть не может,
                    # он ещё не понятие.
                    want[nm] = {"why": "кандидат: не дорос", "arts": n, "name": nm,
                                "vec": r.get("vec")}
    return want


def strongest(want, cap):
    """Спрос сильнее всего там, где до результата ближе всего.

    Просят двенадцать тысяч — это весь хвост копилки, и гнать поле по всем значит
    заплатить памятью за запросы, которые всё равно ничего не поднимут: у кандидата
    с одной статьёй и близость будет случайной. Берём два края: понятия реестра,
    стоящие вовсе без статей (у них есть страница, и на ней пусто), и кандидатов,
    которым до рождения остался шаг.
    """
    if len(want) <= cap:
        return want
    items = list(want.items())
    # ключ: сначала реестр (пустая страница — это стыдно), потом кандидаты по
    # близости к порогу рождения
    items.sort(key=lambda kv: (0 if kv[1]["why"].startswith("реестр") else 1,
                               -kv[1]["arts"]))
    return dict(items[:cap])


def search(want, limit):
    """Один проход по полю — ответ сразу всем запросам.

    Наивно было бы гонять поле по разу на понятие: полторы тысячи запросов ×
    5,6 ГБ чтения. Здесь запросы сложены в одну матрицу, и каждый кусок поля
    умножается на неё целиком — диск читается однажды.
    """
    sys.path.insert(0, str(ML))
    import numpy as np
    import concepts_super as cs
    import vecstore
    from analytics_v2 import _field_dir

    cids, CV = cs.load_cards()
    row = {c: i for i, c in enumerate(cids)}
    q_ids, rows = [], []
    nocard = 0
    for c, v in want.items():
        if c in row:
            rows.append(CV[row[c]])
        elif v.get("vec"):
            rows.append(np.asarray(v["vec"], dtype=np.float32))
        else:
            nocard += 1
            continue
        q_ids.append(c)
    if nocard:
        print(f"без вектора (запросить нечем): {nocard}")
    if not q_ids:
        print("спроса с вектором нет")
        return []
    Q = np.ascontiguousarray(np.vstack(rows), dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
    print(f"запросов с вектором: {len(q_ids)}")

    ids, M = vecstore.load(_field_dir() / "field", mmap=True)
    print(f"поле: {len(ids):,} работ · читаю кусками по {CHUNK:,}")
    have = ours()
    print(f"наших работ (не предлагать): {len(have):,}")

    # Лучшее на каждый запрос копим кучкой фиксированного размера: держать
    # 2,96 млн оценок × полторы тысячи запросов в памяти нельзя и незачем.
    best = [[] for _ in q_ids]
    t0 = time.time()
    for start in range(0, len(ids), CHUNK):
        stop = min(start + CHUNK, len(ids))
        block = np.asarray(M[start:stop], dtype=np.float32)
        S = Q @ block.T                       # (запросы × кусок)
        # Берём кандидатов выше порога — их немного, дальше сортируем дешёвo.
        qi, ci = np.nonzero(S >= MIN_SIM)
        for a, b in zip(qi, ci):
            aid = bare(ids[start + int(b)])
            if aid in have:
                continue
            best[int(a)].append((float(S[a, b]), aid))
        if (start // CHUNK) % 4 == 0:
            done = stop / len(ids)
            print(f"  {done*100:5.1f}% · {int(time.time()-t0)} с", flush=True)
    print(f"проход по полю: {int(time.time()-t0)} с")

    # Свести к работам: одна работа может отвечать нескольким понятиям сразу —
    # такая и есть самая ценная, она закрывает не одну дыру.
    picks = defaultdict(lambda: {"score": 0.0, "for": []})
    for i, c in enumerate(q_ids):
        top = sorted(best[i], key=lambda t: -t[0])[:PER_CONCEPT]
        for sc, aid in top:
            p = picks[aid]
            p["score"] = max(p["score"], sc)
            p["for"].append({"concept": c, "sim": round(sc, 3),
                             "why": want[c]["why"], "name": want[c]["name"]})
    out = []
    for aid, p in picks.items():
        out.append({"id": aid, "score": round(p["score"], 3),
                    "closes": len(p["for"]), "for": p["for"][:6]})
    # Сначала те, кто закрывает больше дыр, потом по близости: работа, нужная
    # трём понятиям сразу, полезнее одной очень близкой.
    out.sort(key=lambda r: (-r["closes"], -r["score"]))
    return out[:limit]


def cited(picks, pause=1.1):
    """Цитируемость финалистов. Вектор сказал «про это» — Scholar скажет «и это читают».

    Мягкая, как и валидация рождений: сервис недоступен — список остаётся, просто
    без числа. Пауза 1,1 с — их предел один запрос в секунду на ключ.
    """
    import urllib.request
    key = None
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("SEMANTIC_SCHOLAR_KEY"):
                key = line.split("=", 1)[1].strip()
    if not key:
        print("ключа Semantic Scholar нет — цитируемость пропускаю")
        return picks
    for i, p in enumerate(picks, 1):
        try:
            r = urllib.request.Request(
                f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{bare(p['id'])}"
                "?fields=citationCount,year,title",
                headers={"x-api-key": key})
            with urllib.request.urlopen(r, timeout=30) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            p["cites"] = d.get("citationCount")
            p["year"] = d.get("year")
            p["title"] = d.get("title")
        except Exception:
            pass
        time.sleep(pause)
        if i % 10 == 0:
            print(f"  цитируемость {i}/{len(picks)}", flush=True)
    # Важность = близость × вес цитирований. Логарифм, а не само число: разница
    # между 10 и 100 цитатами существенна, между 1000 и 1090 — нет.
    import math
    for p in picks:
        c = p.get("cites") or 0
        p["rank"] = round(p["score"] * (1 + math.log10(1 + c)), 3)
    picks.sort(key=lambda r: -r.get("rank", 0))
    return picks


def publishable(aid):
    """Можно ли вообще разбирать эту работу — вопрос лицензии, а не желания.

    Пласты поднимают СТАРЫЕ работы, а у работ до 2007 года свободной лицензии
    часто нет вовсе: arXiv тогда брал бессрочное право на распространение, но не
    давал его нам. Очередь без этой проверки выглядела бы полной, а разбор
    молча пропускал бы работу за работой — и шаг «поднято из прошлого: 0» никто
    бы не понял.

    Проверяем тем же кодом, что и дневной отбор: своего мнения о лицензиях
    заводить нельзя.
    """
    try:
        sys.path.insert(0, str(ROOT))
        from gen_arxiv import get_license, is_allowed_license
    except Exception:
        return True          # проверить нечем — пусть решает генератор
    try:
        lic = get_license(aid)
    except Exception:
        return True
    ok = is_allowed_license(lic)
    # Возвращает ПАРУ (можно ли, какая лицензия) — не голый флаг. bool() от пары
    # всегда истина, и проверка молча пропускала бы всё: quant-ph/9601025 (1996)
    # отвечает (False, None), и именно такие работы пласты поднимают чаще всего.
    if isinstance(ok, tuple):
        return bool(ok[0])
    return bool(ok)


def main():
    ap = argparse.ArgumentParser(description="Пласты: спрос машины знаний → поле arXiv")
    ap.add_argument("--scan", action="store_true", help="только спрос, без поиска")
    ap.add_argument("--pick", type=int, metavar="N", help="сколько работ отобрать")
    ap.add_argument("--cite", action="store_true", help="цитируемость финалистов (сеть)")
    ap.add_argument("--ids", action="store_true", help="печатать только идентификаторы")
    ap.add_argument("--queue", metavar="ФАЙЛ",
                    help="записать идентификаторы очередью для run.py ids --ids-file")
    ap.add_argument("--queue-top", type=int, default=5, metavar="N",
                    help="сколько работ класть в очередь на разбор: отобрать можно "
                         "сорок, а платить за разбор — за пять")
    ap.add_argument("--demand", type=int, default=600,
                    help="сколько запросов брать (сильнейший спрос; память прохода "
                         "растёт линейно по этому числу)")
    a = ap.parse_args()

    want = demand()
    by = defaultdict(int)
    for v in want.values():
        by[v["why"]] += 1
    if not a.ids:
        print(f"спрос машины знаний: {len(want)} понятий")
        for why, n in sorted(by.items(), key=lambda t: -t[1]):
            print(f"   {why}: {n}")
    if a.scan or not a.pick:
        if not a.pick:
            print("\n--pick N найдёт под этот спрос работы в поле")
        return 0

    want = strongest(want, a.demand)
    if not a.ids:
        print(f"беру сильнейший спрос: {len(want)}")
    picks = search(want, a.pick)
    if not picks:
        print("поле не дало ни одной работы выше порога")
        return 0
    if a.cite:
        picks = cited(picks)

    OUT.write_text(json.dumps({
        "built": time.strftime("%Y-%m-%d %H:%M"),
        "demand": len(want), "min_sim": MIN_SIM, "per_concept": PER_CONCEPT,
        "picks": picks,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    if a.queue:
        # Очередь — просто идентификаторы, по одному на строку: её ест
        # run.py ids --ids-file, и никакого своего формата заводить не нужно.
        # Идём по списку сверху и берём первые queue_top ДОПУСТИМЫХ: у работы
        # без свободной лицензии разбора не будет, и держать её в очереди значит
        # обманывать себя же.
        chosen, skipped = [], 0
        for x in picks:
            if len(chosen) >= a.queue_top:
                break
            if publishable(x["id"]):
                chosen.append(x["id"])
            else:
                skipped += 1
            time.sleep(0.4)          # arXiv не любит частых вопросов
        head = ["# Пласты: работы, поднятые по спросу машины знаний",
                f"# собрано {time.strftime('%Y-%m-%d %H:%M')}, "
                f"спрос {len(want)} понятий"]
        Path(a.queue).write_text(
            "\n".join(head + chosen) + "\n", encoding="utf-8")
        print(f"очередь: {len(chosen)} работ → {a.queue}"
              + (f" · отсеяно по лицензии {skipped}" if skipped else ""))
    if a.ids:
        print(",".join(p["id"] for p in picks))
        return 0
    print(f"\nотобрано работ: {len(picks)} → {OUT.relative_to(ROOT)}")
    for p in picks[:12]:
        head = f"  {p['id']}  близость {p['score']}"
        if p.get("cites") is not None:
            head += f"  цитат {p['cites']}"
        if p.get("year"):
            head += f"  {p['year']}"
        print(head)
        if p.get("title"):
            print(f"      {p['title'][:96]}")
        print(f"      закрывает {p['closes']}: "
              + ", ".join(x["name"] for x in p["for"][:4]))
    print("\nразбор заказывается обычным путём:")
    print("  python run.py ids " + " ".join(p["id"] for p in picks[:3]) + " --full")
    return 0


if __name__ == "__main__":
    sys.exit(main())
