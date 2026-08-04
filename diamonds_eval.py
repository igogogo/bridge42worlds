#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мерка честности для охоты за бриллиантами: эталон OpenAlex + прогон дешёвых признаков.

ЗАЧЕМ. Любой критерий «это прорыв» без проверки — гадание. Здесь мы берём статьи, про
которые уже ЗАДНИМ ЧИСЛОМ известно, выстрелили они или нет, считаем на них дешёвые
признаки и смотрим, различают ли признаки хоть что-нибудь.

ЭТАЛОН. Статьи 2023 года из дампа arXiv (data/arxiv-bulk) — им три года, цитирования
набрались. Цитирования берём в OpenAlex: свободный справочник, КЛЮЧ НЕ НУЖЕН, запросы
бесплатны. arXiv-статья адресуется через DOI 10.48550/arXiv.<id>.

ПОЧЕМУ 2023, А НЕ НАШ АРХИВ. Наш корпус слишком молодой: статей старше года — 87 из 2088,
процитированы изнутри 68 (3,3%). Своего эталона у нас нет и в этом году не будет.

ЧЕСТНОСТЬ. Признаки считаются ТОЛЬКО по данным, известным на момент выхода статьи
(абстракт, авторы, категории). Эталон в признаки не подглядывает.

    python diamonds_eval.py --month 2023-01 --field astro-ph --n 400
"""
import json, re, sys, time, math, random, pathlib, argparse, collections
import urllib.parse, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
BULK = ROOT / "data" / "arxiv-bulk"
# OpenAlex просит представляться — тогда запросы идут в «вежливый пул» и не режутся.
MAILTO = "bridge42worlds@gmail.com"
BATCH = 50          # OpenAlex принимает до 50 значений в фильтре через |
TOP_SHARE = 0.10    # верхняя доля по цитированиям = «выстрелила»


def load_month(month, field, limit, seed=42):
    p = (BULK / f"{month}.jsonl")
    if not p.exists():
        sys.exit(f"нет файла дампа: {p}")
    rows = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            try:
                j = json.loads(line)
            except Exception:
                continue
            cats = j.get("categories") or []
            if isinstance(cats, str):
                cats = cats.split()
            if not any(c.startswith(field) for c in cats):
                continue
            rows.append({
                "id": j.get("id"),
                "title": j.get("title") or "",
                "abstract": j.get("abstract") or "",
                "authors": j.get("authors_parsed") or [],
                "cats": cats,
                "published": j.get("published") or "",
            })
    rnd = random.Random(seed)
    rnd.shuffle(rows)
    return rows[:limit] if limit else rows


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def openalex_citations(rows, pause=1.0):
    """Цитирования ПО ЗАГОЛОВКУ, а не по DOI препринта.

    ПОЧЕМУ НЕ ПО DOI. Проверено 2026-07-31 на живом API: у работы
    «CEERS Spectroscopic Confirmation…» препринт arXiv показывает 9 цитирований,
    а журнальная версия того же текста — 163. Разница в восемнадцать раз. Цитируют
    опубликованную статью, у неё другой DOI, и запись препринта остаётся почти пустой.
    Эталон, построенный по DOI препринта, показывает медиану 0 и меряет не влияние
    работы, а то, попал ли кто-то ссылкой в arXiv вместо журнала.

    Поэтому ищем по заголовку и берём МАКСИМУМ по найденным версиям — это и есть
    влияние работы независимо от того, где её процитировали.
    """
    # Кэш на диске. Запрос к OpenAlex — секунда, триста статей — пять минут, и прогон
    # уже дважды обрывался (429, выход сессии) с потерей всего. Кэш делает повтор
    # бесплатным и позволяет добирать выборку по частям.
    cache_path = ROOT / "data" / "openalex-cites.json"
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    out = {k: v for k, v in cache.items() if v is not None}
    if out:
        print(f"  из кэша: {len(out)}")

    def save():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    bad = 0
    for n, r in enumerate(rows, 1):
        if r["id"] in cache:
            continue
        title = " ".join((r["title"] or "").split())
        if len(title) < 15:
            continue
        # Значение фильтра OpenAlex — не свободный текст: запятая разделяет условия,
        # вертикальная черта задаёт варианты, двоеточие обрывает имя фильтра. А заголовки
        # astro-ph вдобавок полны LaTeX ($z\sim$, ^{-1}). Перечислять запрещённые символы
        # бесполезно — на 20-й статье найдётся ещё один. Оставляем только буквы и цифры.
        q = re.sub(r"[^A-Za-z0-9 ]+", " ", title)
        q = " ".join(q.split())[:120]
        if len(q) < 15:
            continue
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": f"title.search:{q}",
            "select": "doi,title,cited_by_count,publication_year,type",
            "per-page": "5",
            "mailto": MAILTO,
        })
        # Пачками тут не получится. Проверено: у опубликованной работы в OpenAlex среди
        # locations стоят журнал, репозитории вуза, HAL, DOAJ — но НЕ arXiv. Препринт
        # живёт отдельной записью и с журнальной версией не связан. Значит только поиск
        # по заголовку, по одному запросу на статью, и надо не долбить API.
        data = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # не теряем статью, а ждём и повторяем ЕЁ ЖЕ
                    time.sleep(2 ** attempt * 2)
                    continue
                bad += 1
                break
            except Exception:
                bad += 1
                break
        if data is None:
            if bad > 40:
                print(f"  !! слишком много отказов ({bad}), останавливаюсь")
                break
            continue

        want = norm_title(title)
        best = None
        for w in data.get("results") or []:
            # защита от чужой работы с похожим названием: сверяем нормализованные заголовки
            got = norm_title(w.get("title") or "")
            if got and (got == want or got.startswith(want[:60]) or want.startswith(got[:60])):
                c = w.get("cited_by_count", 0)
                best = c if best is None else max(best, c)
        # в кэш пишем и промах (None) — чтобы при повторе не спрашивать заново то,
        # чего в OpenAlex просто нет
        cache[r["id"]] = best
        if best is not None:
            out[r["id"]] = best
        if n % 25 == 0:
            save()
            print(f"  {n}/{len(rows)}: сопоставлено {len(out)}")
        time.sleep(pause)
    save()
    return out


def signals(r):
    """Дешёвые признаки — ТОЛЬКО из того, что известно в день выхода."""
    cats = r["cats"]
    roots = {c.split(".")[0] for c in cats}
    na = len(r["authors"])
    return {
        "длина абстракта": len(r["abstract"]),
        "число авторов": na,
        "коллаборация >20": 1 if na > 20 else 0,
        "одиночка": 1 if na == 1 else 0,
        "число категорий": len(cats),
        "cross-list в др. область": 1 if len(roots) > 1 else 0,
        "длина заголовка": len(r["title"]),
        "двоеточие в заголовке": 1 if ":" in r["title"] else 0,
    }


def auc(pos, neg):
    """Доля пар (выстрелила, обычная), где признак у первой БОЛЬШЕ. 0,5 = не различает."""
    if not pos or not neg:
        return float("nan")
    wins = ties = 0
    for a in pos:
        for b in neg:
            if a > b: wins += 1
            elif a == b: ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default="2023-01")
    ap.add_argument("--field", default="astro-ph")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--out", default="data/diamonds-eval.json")
    args = ap.parse_args()

    rows = load_month(args.month, args.field, args.n)
    print(f"взято статей {args.field} за {args.month}: {len(rows)}")

    print("спрашиваю цитирования у OpenAlex (бесплатно, без ключа)...")
    cites = openalex_citations(rows)
    for r in rows:
        r["cites"] = cites.get(r["id"])

    known = [r for r in rows if r["cites"] is not None]
    print(f"\nцитирования известны у {len(known)} из {len(rows)} "
          f"({100*len(known)/max(1,len(rows)):.0f}%)")
    if len(known) < 50:
        sys.exit("слишком мало данных для мерки")

    known.sort(key=lambda r: -r["cites"])
    k = max(1, int(len(known) * TOP_SHARE))
    top, rest = known[:k], known[k:]
    cc = [r["cites"] for r in known]
    print(f"цитирования: медиана {sorted(cc)[len(cc)//2]}, среднее {sum(cc)/len(cc):.1f}, "
          f"макс {max(cc)}, нулевых {sum(1 for x in cc if x == 0)}")
    print(f"«выстрелили» — верхние {int(TOP_SHARE*100)}%: {len(top)} статей, "
          f"порог {top[-1]['cites']} цитирований")
    print(f"«обычные»: {len(rest)}")

    print(f"\n{'признак':<26} {'выстр.':>9} {'обычные':>9} {'AUC':>7}  вердикт")
    results = {}
    for name in signals(known[0]):
        pos = [signals(r)[name] for r in top]
        neg = [signals(r)[name] for r in rest]
        a = auc(pos, neg)
        mp = sum(pos) / len(pos)
        mn = sum(neg) / len(neg)
        verdict = ("различает" if a >= 0.60 or a <= 0.40 else
                   "слабо" if a >= 0.55 or a <= 0.45 else "НЕ различает")
        results[name] = {"auc": a, "mean_top": mp, "mean_rest": mn}
        print(f"{name:<26} {mp:>9.1f} {mn:>9.1f} {a:>7.3f}  {verdict}")

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "month": args.month, "field": args.field,
        "n": len(known), "top_share": TOP_SHARE,
        "cite_threshold": top[-1]["cites"],
        "signals": results,
        "top_titles": [{"id": r["id"], "cites": r["cites"], "title": r["title"][:120]}
                       for r in top[:15]],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nподробности: {out}")
    print("\nверх списка по цитированиям (глазами — похожи ли на бриллианты):")
    for r in top[:10]:
        print(f"  {r['cites']:>5}  {r['title'][:95]}")


if __name__ == "__main__":
    main()



