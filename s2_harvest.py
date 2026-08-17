#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сбор пар цитирований через Semantic Scholar. Строка f1 техлиста.

Узкое место дообучения компаса — данные, а не вычисления: пар сейчас 3052 из наших
PDF, для LoRA нужно порядка 200 тысяч. Пара — это «цитирующая работа + цитируемая»,
положительный пример; отрицательные берутся из той же партии и отдельно не собираются.

ПОЧЕМУ ПАКЕТНАЯ РУЧКА, А НЕ ПО ОДНОЙ РАБОТЕ. `POST /graph/v1/paper/batch` принимает
до 500 номеров за раз и возвращает списки ссылок сразу для всех. Пятьдесят тысяч работ
— это сто запросов, а не пятьдесят тысяч. Разница не в скорости, а в том, поместимся
ли мы в чужой сервис вежливо.

ГЛАВНОЕ ЗДЕСЬ — НЕ СКОРОСТЬ, А ОГРАНИЧЕНИЕ СКОРОСТИ. Волна: «уважать лимиты API:
бан ключа стоит дороже суток ожидания». Проверила живым запросом: без ключа второй
запрос подряд уже отдаёт 429 — общий пул тесный. Поэтому:

  · по умолчанию один запрос в две секунды, а не «как получится»;
  · на 429 пауза удваивается до минуты, и это не ошибка, а нормальный режим;
  · после восьми неудач подряд сборщик ОСТАНАВЛИВАЕТСЯ сам. Упереться и ждать лучше,
    чем продолжать долбить и получить бан;
  · всё, что собрано, дописывается на диск сразу. Прерывание не теряет работу,
    повторный запуск продолжает с того места.

ЧТО ОТБИРАЕТСЯ. Ссылка идёт в пары, только если у цитируемой работы есть номер arXiv
И она есть в нашем поле. Причина простая: обе стороны пары должны иметь аннотацию
локально, иначе на этой паре нельзя обучаться.

    python s2_harvest.py --dry                 показать план, ничего не запрашивать
    python s2_harvest.py --seeds 2000          пробный сбор
    python s2_harvest.py --seeds 50000         полный сбор (~100 запросов, ~4 минуты
                                               при паузе 2 с, дольше при 429)
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

API = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = "externalIds,references.externalIds"
BATCH = 500                 # предел ручки
CACHE = DATA / "s2-refs.jsonl"       # что уже опрошено — чтобы не спрашивать дважды
PAIRS = DATA / "s2-pairs.jsonl"      # собранные пары, дописываются сразу


def load_key():
    p = MAIN / ".env"
    if not p.exists():
        return ""
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("SEMANTIC_SCHOLAR_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def ask(ids, key, pause, tries=8):
    """Один пакет. Возвращает (ответ, сколько ждать перед следующим запросом)."""
    body = json.dumps({"ids": [f"ARXIV:{i}" for i in ids]}).encode("utf-8")
    head = {"Content-Type": "application/json"}
    if key:
        head["x-api-key"] = key
    wait = pause
    for a in range(tries):
        try:
            req = urllib.request.Request(f"{API}?fields={FIELDS}", data=body,
                                         headers=head)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8")), pause
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503, 504):
                raise
            wait = min(wait * 2, 60)
            print(f"    {e.code} — жду {wait:.0f} с (попытка {a + 1} из {tries})")
            time.sleep(wait)
        except Exception as e:
            wait = min(wait * 2, 60)
            print(f"    {type(e).__name__} — жду {wait:.0f} с")
            time.sleep(wait)
    return None, pause


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50000,
                    help="сколько работ опросить")
    ap.add_argument("--pause", type=float, default=2.0,
                    help="секунд между запросами; меньше 1 без ключа не ставить")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--merge", action="store_true",
                    help="слить собранное в data/citations.json и выйти")
    args = ap.parse_args()

    import vecstore
    import field_build as fb

    ids, _ = vecstore.load(DATA / "field", mmap=True)
    have = {fb._base_id(s) for s in ids}
    print(f"поле: {len(have):,} работ с аннотацией локально")

    if args.merge:
        return merge(have)

    # Кого спрашиваем. Сначала наши собственные работы — их окружение ценнее всего
    # для компаса; дальше — ровная выборка по полю, чтобы пары покрывали всю физику,
    # а не только те углы, где мы уже стоим.
    import drill
    ours = [a for a in drill.our_ids() if a in have]
    rest = sorted(have - set(ours))
    step = max(1, len(rest) // max(1, args.seeds - len(ours)))
    seeds = ours + rest[::step]
    seeds = seeds[:args.seeds]

    done = set()
    if CACHE.exists():
        with CACHE.open(encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["id"])
                except Exception:
                    pass
    todo = [s for s in seeds if s not in done]
    print(f"опросить {len(seeds):,} работ, из них уже опрошено {len(done):,}, "
          f"осталось {len(todo):,}")
    print(f"пакетов по {BATCH}: {(len(todo) + BATCH - 1) // BATCH} · "
          f"пауза {args.pause} с · ключ {'есть' if load_key() else 'НЕТ (медленнее)'}")

    if args.dry:
        print("\n--dry: ни одного запроса не сделано")
        return 0

    key = load_key()
    DATA.mkdir(exist_ok=True)
    got = fails = npairs = 0
    with CACHE.open("a", encoding="utf-8") as fc, PAIRS.open("a", encoding="utf-8") as fp:
        for st in range(0, len(todo), BATCH):
            chunk = todo[st:st + BATCH]
            data, _ = ask(chunk, key, args.pause)
            if data is None:
                fails += 1
                print(f"  !! пакет {st // BATCH + 1} не дался")
                # Восемь неудач подряд — останавливаемся сами. Собранное на диске.
                if fails >= 8:
                    print("\nОСТАНОВКА: восемь неудач подряд. Собранное сохранено, "
                          "запустите позже — продолжит с этого места.")
                    break
                continue
            fails = 0
            for src_id, rec in zip(chunk, data):
                fc.write(json.dumps({"id": src_id}, ensure_ascii=False) + "\n")
                if not rec:
                    continue
                got += 1
                for r in (rec.get("references") or []):
                    if not r:
                        continue
                    dst = (r.get("externalIds") or {}).get("ArXiv")
                    if not dst:
                        continue
                    dst = fb._base_id(str(dst))
                    # Обе стороны обязаны быть в поле: иначе паре не на чем учиться.
                    if dst in have and dst != src_id:
                        fp.write(json.dumps({"from": src_id, "to": dst,
                                             "src": "s2"}, ensure_ascii=False) + "\n")
                        npairs += 1
            print(f"  пакет {st // BATCH + 1}/{(len(todo) + BATCH - 1) // BATCH}: "
                  f"работ с ответом {got:,} · пар {npairs:,}")
            time.sleep(args.pause)

    print(f"\nсобрано пар: {npairs:,} · работ опрошено: {got:,}")
    print(f"пары в {PACKED(PAIRS)}, опрошенные в {PACKED(CACHE)}")
    print("слить в citations.json: python s2_harvest.py --merge")
    return 0


def PACKED(p):
    return f"{p} ({p.stat().st_size / 1e6:.1f} МБ)" if p.exists() else str(p)


def merge(have):
    """Слить собранное в data/citations.json, пометив источник у каждой пары."""
    # Пишем в СВОЮ копию, а не в главную: результат должен оказаться там, где его
    # закоммитит автор. У ведущей скрипт лежит в главной папке, и путь совпадёт сам.
    cp = ROOT / "data" / "citations.json"
    if not cp.exists() and (MAIN / "data" / "citations.json").exists():
        cp.parent.mkdir(exist_ok=True)
        cp.write_text((MAIN / "data" / "citations.json").read_text(encoding="utf-8"),
                      encoding="utf-8")
    d = json.loads(cp.read_text(encoding="utf-8"))
    old = d.get("internal") or []
    # У старых пар источник не проставлен — они из PDF.
    for e in old:
        e.setdefault("src", "pdf")
    seen = {(e["from"], e["to"]) for e in old}
    add = 0
    if PAIRS.exists():
        with PAIRS.open(encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                k = (e["from"], e["to"])
                if k in seen:
                    continue
                seen.add(k)
                old.append(e)
                add += 1
    d["internal"] = old
    d["_sources"] = {"pdf": sum(1 for e in old if e.get("src") == "pdf"),
                     "s2": sum(1 for e in old if e.get("src") == "s2")}
    cp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"добавлено пар: {add:,} · всего внутренних: {len(old):,}")
    print(f"источники: {d['_sources']}")
    print(f"→ {cp} ({cp.stat().st_size / 1e6:.1f} МБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
