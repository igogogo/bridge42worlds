#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полное поле: вектор по всем 3,13 млн аннотаций arXiv.

Владелец 11 августа: «я прошу полный вектор, потому что полный вектор — поиск статей,
дальше разбор, определение, чего не хватает, опоры, догенерация их экспрессом. Полное
поле вектора на 3 миллиона, а не на то, что собрано».

Платим за ОДИН проход аннотации через модель; дальше числа наши, и пользование ими
бесплатно навсегда. Хранение — на диске, тоже бесплатно: сервис векторного поиска
(Vectorize, $0,04 за млн измерений в месяц) нужен живому сайту, где ответ ждут
миллисекунды, а нам нужен ночной перебор, где 32 секунды — норма. Замер: перебор
по 3,13 млн через memmap даёт 1,5 с на статью пачкой по двадцать.

ЧТО БЕРЁМ (решение владельца 11 августа, по числам): физику и смежное естествознание,
последние годы. Не всё подряд — cs и math это 44,5% корпуса и не наш предмет.

    физика 2025-2026   149 350 работ · $0,51 · 0,3 ГБ · полчаса
    физика 2024-2026   229 517 работ · $0,65 · 0,5 ГБ · 42 минуты
    физика целиком   1 561 047 работ · $4,31 · 3,2 ГБ · 5 часов
    всё подряд       3 127 799 работ · $8,68 · 6,4 ГБ · 10 часов

Начинаем с малого не из экономии — суммы тут копеечные, — а потому что поле
РАСШИРЯЕМО без потерь: посчитанное лежит в .ids и повторно не считается никогда.
Добавить год или раздел — это тот же прогон с другими ключами, дописывающий хвост.

ПОЧЕМУ НЕ ЧЕРЕЗ embeddings_build.run(). Тот пишет JSONL — по 297 МБ на 29 тысяч работ,
то есть тридцать с лишним гигабайт на полное поле. Их некуда положить: на диске 46 ГБ.
Здесь векторы идут сразу в двоичный формат vecstore, минуя текстовое промежуточное
состояние. Это не оптимизация, а условие выполнимости.

ДОЛГИЙ ПРОГОН БУДЕТ ПРЕРВАН. Сон машины, разрыв сети, перезапуск — что-нибудь
случится. Поэтому:
  · продолжение с любого места (что посчитано, лежит в .ids, повторно не считаем);
  · сверка длин при старте: обрыв посреди записи оставляет .f16 и .ids разной длины,
    и без починки файл молча становится мусором — векторы после точки обрыва
    разложатся со сдвигом и будут принадлежать чужим работам;
  · потолок расходов: прогон сам останавливается, а не выясняет цену по счёту.

    python field_build.py --check --months 2025,2026    сколько выйдет, ничего не тратя
    python field_build.py --months 2025,2026            посчитать физику за два года
    python field_build.py --months 2024 --max-cost 1    дописать ещё год, потолок $1
    python field_build.py --cats all --months 2026      добрать cs/math за год, если решим
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
BULK = MAIN / "data" / "arxiv-bulk"
OUT = DATA / "field"
PRICE = 0.010                      # $/млн токенов, DeepInfra, проверено 2026-08-10
MAX_CHARS = 2400                   # аннотация в среднем 1082 знака; обрезка — от аномалий
# Знаков на токен — ЗАМЕРЕНО на 200 случайных аннотациях из восьми разных лет:
# 178 657 знаков дали 44 732 токена, то есть 3,99. Считать было чем, и это оказалось
# важно: моя рабочая оценка «знаки/1,5» (верная для полных текстов с формулами)
# завышала цену полного поля втрое — $22,56 против настоящих $8,47.
CHARS_PER_TOKEN = 3.9
BATCH_ITEMS = 96                   # предел контекста — 60k токенов НА ПАЧКУ; 96 аннотаций
                                   # это ~27k, вдвое с запасом. Упирается в число работ,
                                   # а не в токены, поэтому пачка крупная: меньше запросов —
                                   # меньше часов, а часы тут дороже денег.
WORKERS = 6                        # пачки уходят параллельно: прогон упирается в ожидание
                                   # ответа, а не в счёт. Без этого 3,13 млн — это ночь.

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def months(spec=None):
    ms = sorted(p.stem for p in BULK.glob("*.jsonl"))
    if spec:
        want = tuple(x.strip() for x in spec.split(",") if x.strip())
        ms = [m for m in ms if m.startswith(want)]
    return ms


# Разделы физики и смежного естествознания. Владелец 11 августа: «там явно не всё,
# там много математики или чего-то ещё… не 4 миллиона явно, подумай по разделам».
# Замер подтвердил: cs — 797 716 работ (25,5% корпуса), math — 593 617 (19,0%).
# Почти половина поля — это то, чем мы не занимаемся по прямому решению владельца.
#
# ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ ЛОВУШКИ С `astro-ph.*` В ЛЕНТЕ. Тем, что это решение принято
# с числами на руках и записано здесь. Дырка в разделе, который мы сознательно
# не брали, — не слепая зона, а выбор. Слепой её делает не отсутствие, а забытая
# причина отсутствия. Поэтому список открыт: добавить раздел — одна строка и один
# прогон, уже посчитанное не пересчитывается.
PHYSICS = ("astro-ph", "cond-mat", "physics", "hep-ph", "quant-ph", "hep-th", "gr-qc",
           "nucl-th", "hep-ex", "hep-lat", "nucl-ex", "math-ph", "nlin", "q-bio",
           "chao-dyn", "adap-org", "solv-int", "patt-sol", "supr-con", "mtrl-th")


def _base_id(s):
    """Номер работы без версии: 2508.00529v1 и 2508.00529 — одна и та же."""
    s = str(s).strip().split("/")[-1].split(":")[-1]
    return s.split("v")[0] if "v" in s[-3:] else s


def id_month(aid):
    """Месяц работы прямо из её номера: 2607.11163 → 2026-07. Обе схемы нумерации
    arXiv: до 2007 года номер шёл после раздела (astro-ph/9909003), после — сам по себе."""
    core = str(aid).split(":", 1)[-1]
    core = core.split("/")[-1] if "/" in core else core
    d = core.split("v")[0][:4]
    if not d.isdigit():
        return None
    yy, mm = int(d[:2]), int(d[2:4])
    if not 1 <= mm <= 12:
        return None
    return f"{1900 + yy if yy >= 91 else 2000 + yy}-{mm:02d}"


def docs(month, cats=None, only=None):
    """Работы одного месяца: id и текст для вектора. Заголовок + аннотация вместе —
    заголовок несёт предмет работы, аннотация результат, и порознь они хуже.

    Раздел берём ПЕРВЫЙ из списка: у arXiv это тот, куда работу подал сам автор,
    а остальные — перекрёстные ссылки. Работа по машинному обучению в астрофизике
    подана в astro-ph и попадёт к нам; работа про саму архитектуру сети подана
    в cs.LG и не попадёт, даже если астрофизика указана вторым разделом.
    """
    p = BULK / f"{month}.jsonl"
    out = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if only is not None and _base_id(r.get("id", "")) not in only:
                continue
            if cats:
                c = r.get("categories")
                lst = c if isinstance(c, list) else str(c or "").split()
                if not lst or str(lst[0]).split(".")[0] not in cats:
                    continue
            t = " ".join(f"{r.get('title','')}. {r.get('abstract','')}".split())
            if len(t) < 60 or not r.get("id"):
                continue
            out.append((f"arx:{r['id']}", t[:MAX_CHARS]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="посчитать объём, ничего не тратить")
    ap.add_argument("--months", help="например 2024,2025 — только эти годы")
    ap.add_argument("--max-cost", type=float, default=12.0,
                    help="потолок расходов на прогон, доллары")
    ap.add_argument("--ours", action="store_true",
                    help="добрать в поле работы, о которых написаны НАШИ статьи — "
                         "любого раздела и года")
    ap.add_argument("--cats", default="physics",
                    help="physics — разделы естествознания (по умолчанию); all — всё подряд; "
                         "или через запятую: astro-ph,quant-ph")
    ap.add_argument("--batch-tokens", type=int, default=40000)
    args = ap.parse_args()
    import numpy as np
    sys.path.insert(0, str(ROOT))
    import vecstore
    from embeddings_build import _di_split, load_env, log_usage

    ms = months(args.months)
    # Разделы решаются ПЕРВЫМИ, чтобы режим «наши» мог их отменить последним словом.
    # В первой версии порядок был обратный: `--ours` сбрасывал фильтр, а следующие
    # строки возвращали его обратно, и 283 наши статьи про cs/math в поле не попали.
    if args.cats == "all":
        cats = None
    elif args.cats == "physics":
        cats = set(PHYSICS)
    else:
        cats = {x.strip() for x in args.cats.split(",") if x.strip()}
    if args.ours:
        # НАШИ статьи обязаны быть в поле целиком, вне зависимости от раздела и года.
        # Иначе карта врёт про нас самих: мы писали и про cs, и про math (284 статьи),
        # а поле их не берёт — и эти области выглядели бы пустыми у нас, хотя они
        # как раз не пустые. Исключение из правила про разделы, и оно одно.
        own = {_base_id(p.parent.name) for p in
               (MAIN / "lang/ru/archive").glob("*/*/data.json")}
        cats = None
        ms = sorted({mo for mo in (id_month(a) for a in own) if mo} & set(months()))
        print(f"режим «наши»: статей {len(own)}, месяцев с ними {len(ms)}")
        only = own
    else:
        only = None
    print(f"месяцев: {len(ms)} ({ms[0]} … {ms[-1]}) · разделы: "
          f"{'все' if cats is None else str(len(cats)) + ' шт.'}")

    if args.check:
        n = chars = 0
        for i, m in enumerate(ms):
            d = docs(m, cats, only)
            n += len(d)
            chars += sum(len(t) for _, t in d)
            if i % 60 == 0 and n:
                print(f"  {m}: всего {n:,} работ")
        tok = chars / CHARS_PER_TOKEN
        print(f"\nработ: {n:,} · знаков: {chars:,} · токенов ≈ {tok/1e6:,.0f} млн")
        print(f"цена ≈ ${tok/1e6*PRICE:.2f} · файл {n*1024*2/1e9:.1f} ГБ")
        return 0

    OUT.parent.mkdir(exist_ok=True)
    vecstore.repair(OUT)
    done = set(vecstore.done_ids(OUT))
    print(f"уже посчитано: {len(done):,}")

    key = load_env(MAIN).get("DEEPINFRA_API_KEY", "")
    if not key:
        sys.exit("нет DEEPINFRA_API_KEY")

    spent_tok, t0, added = 0, time.time(), 0
    stop = False
    for m in ms:
        if stop:
            break
        # Отсев повторов идёт по ОДНОМУ множеству `done`, которое пополняется на ходу.
        # Это закрывает три случая сразу: работа посчитана прошлым запуском, работа
        # посчитана раньше в этом же запуске (другой месяц), работа дважды лежит
        # в одном файле. Последний случай `done` из .ids не поймал бы: на момент
        # чтения файла обеих записей ещё нет ни в одном списке.
        todo, seen = [], set()
        for i, t in docs(m, cats, only):
            if i in done or i in seen:
                continue
            seen.add(i)
            todo.append((i, t))
        if not todo:
            continue
        packs = [todo[s:s + BATCH_ITEMS] for s in range(0, len(todo), BATCH_ITEMS)]

        def work(pack):
            st = {}
            return pack, _di_split([x[1] for x in pack], key, st), st

        # Пачки считаются параллельно, но В ФАЙЛ ложатся строго по порядку группы.
        # Порядок внутри файла сам по себе не важен — id лежат рядом с векторами, —
        # а вот СОГЛАСОВАННОСТЬ важна: записывать надо из одного места, иначе два
        # потока перемешают байты векторов с чужими идентификаторами.
        for g in range(0, len(packs), WORKERS):
            group = packs[g:g + WORKERS]
            with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
                futs = [ex.submit(work, p) for p in group]
                res = []
                for fu in futs:
                    try:
                        res.append(fu.result())
                    except Exception as e:
                        # Один сбойный кусок не должен ронять весь прогон:
                        # пропускаем, повторный запуск доберёт его же.
                        print(f"  !! {m}: пачка пропущена "
                              f"({type(e).__name__}: {str(e)[:90]})")
            for pack, vecs, st in res:
                vecstore.append(OUT, [x[0] for x in pack], vecs)
                done.update(x[0] for x in pack)
                added += len(pack)
                spent_tok += st.get("tokens", 0)
            if spent_tok / 1e6 * PRICE >= args.max_cost:
                print(f"\nдостигнут потолок ${args.max_cost}: остановка. "
                      f"Повторный запуск продолжит ровно с этого места.")
                stop = True
                break
        el = time.time() - t0
        speed = added / max(el, 1)
        left = 3_130_000 - len(done)
        print(f"  {m}: +{len(todo):,} → всего {len(done):,} · "
              f"${spent_tok/1e6*PRICE:.2f} · {speed:.0f} работ/с · "
              f"осталось ~{left/max(speed,1e-9)/3600:.1f} ч")

    log_usage("field", spent_tok)
    print(f"\nдобавлено за прогон: {added:,} · токенов {spent_tok:,} · "
          f"${spent_tok/1e6*PRICE:.2f}")
    print(f"всего в поле: {len(done):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
