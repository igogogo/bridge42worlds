#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Настоящая дотяжка экспресса: «Подробно» из текста работы, «Популярно» из «Подробно».

ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ ПРЕЖНЕЙ ДОТЯЖКИ. Прежняя (tools/express_uplift.py) брала уровень
«Просто», написанный по авторской аннотации, и поднимала его до «Популярно» одним дешёвым
вызовом. Тон получался взрослый, а знание оставалось прежним: под популярным уровнем
лежала всё та же аннотация — несколько предложений витрины, которые автор пишет для
привлечения. Так поднято 2 090 статей, и они опаснее прямо заблокированных: выглядят
готовыми. Владелец 2026-09-01: «популярно из просто не делаем».

Здесь ход единственно правильный и он же исходный: текст работы → «Подробно» → «Популярно».

ПОЧЕМУ ЭТО НЕ ДОРОГО. Текст работы уже лежит на диске. Когда экспресс рождался, PDF всё
равно качали ради картинок и обложки, разбирали pypdf и клали рядом со статьёй —
original.pdf и fulltext.txt есть у 6 010 экспрессов из 6 024. Значит платим только за
работу модели: ни скачиваний, ни обращений к arXiv (лицензия тоже лежит в data.json).

ЧЕГО НЕ ДЕЛАЕМ. «Просто» не трогаем — ни текст, ни четыре его перевода (владелец: «если
просто уже собран для экспресса, то оставь; в целом просто всегда можно собирать из
абстракта, пусть так и останется»). Это половина цены дотяжки и то же правило воронки,
что раньше берегло короткий текст: оплаченное не выбрасываем. Механика — в generate.py,
флаг keep_simple; здесь только очередь и порядок.

ПОРЯДОК ОЧЕРЕДИ
    1. Поднятые прежним способом — они уже показывают читателю популярный уровень,
       под которым ничего нет. Ложное «готово» чиним раньше честного «не готово».
    2. Те, кого просят: звезда в избранном, читатели, «бриллианты» ML
       (data/upgrade-queue.json, готовит tools/upgrade_queue.py).
    3. Остальные, начиная со свежих: у свежей работы больше шансов, что автор ещё
       рядом и письмо застанет его за этой темой.

ТЕМП — СТО РАБОТ В СУТКИ. Владелец 2026-09-01 на вопрос о сроке: «да растяни на два хоть
месяца». Шесть тысяч работ за шестьдесят дней это сто в сутки — около $3.7 за заход в
дешёвое окно, то есть ~$110 в месяц вместе с дневными полными. Месячный потолок $200
выдерживает с запасом; попытка закрыть за месяц его бы пробила.

    python tools/deep_uplift.py --plan             показать очередь, ничего не делать
    python tools/deep_uplift.py --limit 100 --wait ночной заход: ждёт дешёвого окна
    python tools/deep_uplift.py --limit 20 --now   не ждать, платить по пиковому

Возобновляемый: дотянутая работа перестаёт быть экспрессом и в очередь больше не попадает.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def queue(need_text=True):
    """Все экспрессы, годные к дотяжке, в порядке приоритета.

    Годность — наличие разобранного текста ИЛИ самого PDF: без них строить «Подробно»
    не из чего, и такую работу честнее оставить экспрессом, чем разбирать по аннотации
    (это ровно та ошибка, которую мы здесь и исправляем).
    """
    want = {}
    qf = ROOT / "data" / "upgrade-queue.json"
    if qf.exists():
        try:
            for r in json.loads(qf.read_text(encoding="utf-8")):
                want[r["id"]] = float(r.get("score") or 0)
        except Exception:
            pass
    rows = []
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("express"):
            continue
        folder = p.parent
        has_text = (folder / "fulltext.txt").exists() and (folder / "fulltext.txt").stat().st_size > 2000
        has_pdf = (folder / "original.pdf").exists() and (folder / "original.pdf").stat().st_size > 10_000
        if need_text and not (has_text or has_pdf):
            continue
        ru_pop = (d.get("popular") or {}).get("ru") or {}
        ru_simple = (d.get("simple") or {}).get("ru") or {}
        rows.append({
            "id": d["id"],
            "date": d.get("date") or p.parent.parent.name,
            "title": ru_simple.get("title") or d.get("original_title") or d["id"],
            # 0 — ложное «готово», 1 — просят, 2 — очередь
            "rank": 0 if ru_pop.get("uplifted") else (1 if d["id"] in want else 2),
            "score": want.get(d["id"], 0.0),
            "keep_simple": bool(ru_simple.get("text")) and not ru_simple.get("express_locked"),
        })
    rows.sort(key=lambda r: (r["rank"], -r["score"], r["date"]), reverse=False)
    # внутри «остальных» — свежие вперёд; сортировка выше даёт старые, поэтому
    # третью группу переворачиваем отдельно, не трогая первые две.
    head = [r for r in rows if r["rank"] < 2]
    tail = sorted([r for r in rows if r["rank"] == 2], key=lambda r: r["date"], reverse=True)
    return head + tail


def _step(name, cmd):
    """Шаг-подпроцесс с честным итогом. Замок дерева дети не берут заново — родитель
    передаёт им B42_LOCKS через окружение (см. tools/runlock.py)."""
    import subprocess
    print(f"\n▶ {name}…")
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode:
        print(f"  ⚠️ {name}: код {r.returncode} — идём дальше, но это надо посмотреть")
    return r.returncode == 0


def article_stub(d):
    """Метаданные работы из нашего же data.json — чтобы не ходить в arXiv за тем,
    что у нас записано. Шесть тысяч обращений к чужому API ради известных полей —
    это часы ожидания и столько же поводов упасть (ловушка 19.08, см. gen_arxiv)."""
    return {
        "id": d["id"],
        "title": d.get("original_title") or "",
        "summary": d.get("abstract_orig") or "",
        "authors": d.get("authors") or [],
        "published": d.get("date") or "",
        "categories": d.get("categories") or [],
        "primary_category": d.get("primary_category") or "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="сколько работ дотянуть за заход")
    ap.add_argument("--plan", action="store_true", help="показать очередь и выйти")
    ap.add_argument("--now", action="store_true", help="не ждать дешёвого окна DeepSeek")
    ap.add_argument("--wait", action="store_true",
                    help="дождаться дешёвого окна, а не отказываться (для ночных заходов)")
    ap.add_argument("--workers", type=int, default=0, help="потоков (по умолчанию из config)")
    ap.add_argument("--no-recommend", action="store_true", help="без ✛ (по умолчанию с ним)")
    args = ap.parse_args()

    rows = queue()
    by_rank = {0: 0, 1: 0, 2: 0}
    for r in rows:
        by_rank[r["rank"]] += 1
    print(f"в очереди {len(rows)} экспрессов · поднятых прежним способом {by_rank[0]} · "
          f"просят {by_rank[1]} · остальных {by_rank[2]}")
    keep = sum(1 for r in rows if r["keep_simple"])
    print(f"«Просто» переиспользуем у {keep} из {len(rows)} — остальным соберём заново")
    if args.plan or not args.limit:
        for r in rows[:15]:
            why = ("ложное готово" if r["rank"] == 0
                   else f"просят {r['score']:.0f}" if r["rank"] == 1 else "очередь")
            print(f"  {why:>16} · {r['date']} · {r['title'][:56]}")
        if not args.limit:
            print("\nсколько тянуть: --limit N")
        return 0

    from tools.freeze import guard as frozen
    frozen("deep_uplift")

    # ЦЕНА ВДВОЕ — ЭТО НЕ МЕЛОЧЬ НА ШЕСТИ ТЫСЯЧАХ РАБОТ. Замер на пилоте: $0.074 за работу
    # в пик, то есть ~$0.037 в дешёвое окно; на весь архив разница около $110.
    # Окна пика (UTC, пн-пт): 01:00-04:00 и 06:00-10:00.
    from common import deepseek_peak_status
    peak, _ = deepseek_peak_status()
    if peak and not args.now:
        if not args.wait:
            print("\n⏳ сейчас пиковый тариф DeepSeek — дотяжка не начинается.")
            print("   Дождаться самому: --wait. Настаиваете сейчас: --now.")
            return 2
        # Ждём молча, но с отметками: заход в фоне на два часа без единой строки в логе
        # неотличим от зависшего.
        while peak:
            print(f"⏳ пиковый тариф — жду дешёвого окна "
                  f"({time.strftime('%H:%M')} по машине)", flush=True)
            time.sleep(600)
            peak, _ = deepseek_peak_status()
        print(f"✅ дешёвое окно открылось в {time.strftime('%H:%M')} — начинаю", flush=True)

    from tools import runlock
    import generate as G

    todo = rows[:args.limit]
    workers = args.workers or int(G.config.get("article_workers", 8))
    print(f"\nдотягиваю {len(todo)} работ в {workers} потоков…")

    with runlock.hold("tree", "дотяжка экспрессов"):
        inputs = G.load_generation_inputs()
        for lang in G.LANGUAGES:
            G.ensure_lang_structure(lang)

        done, failed = [], []

        def one(row):
            p = next((ROOT / "lang/ru/archive").glob(f"*/{row['id']}/data.json"), None)
            if p is None:
                return row["id"], None, None, "папка не найдена"
            # Дата — ИМЯ ПАПКИ, а не поле даты: страницы уже лежат по этому адресу, и
            # разойдись они на день, дотяжка построила бы статью рядом со старой вместо
            # того, чтобы её заменить.
            day = p.parent.parent.name
            d = json.loads(p.read_text(encoding="utf-8"))
            try:
                item = G.build_article(article_stub(d), day, inputs, force=True,
                                       known_license=d.get("license"))
            except Exception as e:
                return row["id"], None, day, f"{type(e).__name__}: {e}"
            if not item:
                return row["id"], None, day, "генерация не удалась — старая версия не тронута"
            return row["id"], item, day, None

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for aid, item, day, err in ex.map(one, todo):
                if err:
                    failed.append((aid, err))
                    print(f"  ✗ {aid}: {err}")
                else:
                    done.append((aid, item, day))

        mins = (time.time() - t0) / 60
        print(f"\nразобрано {len(done)}, отказов {len(failed)} · {mins:.0f} мин")
        if not done:
            return 1

        ids = [aid for aid, _item, _day in done]
        # ПОРЯДОК ТОТ ЖЕ, ЧТО В ДНЕВНОМ ПРОГОНЕ: разметка → рекомендации → страницы.
        # Он не косметический. Разметка дописывает в data.json понятия и связи, ✛ читает
        # соседей уже размеченной работы, и только потом собираются страницы — иначе
        # получается ровно то, что владелец поймал 31.08: рекомендации в данных есть,
        # раздела на странице нет.
        #
        # Страницы НЕ пишем из памяти (write_article_pages): в item нет ничего, что
        # допишут шаги ниже. Собираем в конце из data.json — run.py html --only.
        _step("разметка вектором", [sys.executable, "tools/retag_hub.py", "--live",
                                    ",".join(ids), "--apply", "--thr", "0.50",
                                    "--margin", "0.12"])
        _step("применение разметки", [sys.executable, "tools/wave5_apply.py",
                                      "--apply", "--articles-only"])
        _step("понятия в тексте", [sys.executable, "tools/highlight_concepts.py",
                                   "--tiers", "simple,popular,advanced", "--ids", ",".join(ids)])

        # ✛ РЕКОМЕНДАЦИИ — ЧАСТЬ ДОТЯЖКИ, А НЕ ОТДЕЛЬНАЯ ЗАБОТА (владелец 2026-09-01:
        # «✛ при дотяжке нужен»). Без них дотянутая работа не годится для письма автору,
        # а письма — весь смысл затеи: пишем только тем, для кого машина знаний написала
        # раздел «куда работа может пойти дальше».
        #
        # По СВОИМ id, а не --all-full: общая очередь рекомендаций берёт любую полную
        # статью без раздела, и на пилоте она честно ушла разбирать чужие работы, оставив
        # без ✛ одну из двух дотянутых.
        if not args.no_recommend:
            print("\nрекомендации автору (✛)…")
            from tools.recommend import build as build_rec
            got = 0
            with ThreadPoolExecutor(max_workers=min(4, len(ids))) as rex:
                for ok in rex.map(lambda i: bool(build_rec(i)), ids):
                    got += 1 if ok else 0
            print(f"  ✛ написано для {got} из {len(ids)}")

        _step("страницы и агрегаты", [sys.executable, "run.py", "html", "--only"] + ids)

    if failed:
        print("\nотказы:")
        for aid, err in failed[:20]:
            print(f"  {aid}: {err}")
    print(f"\nготово: дотянуто {len(done)} · всего в очереди осталось "
          f"{len(queue()) if not failed else '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
