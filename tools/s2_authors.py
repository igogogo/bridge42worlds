#!/usr/bin/env python3
"""Развод одноимённых авторов через Semantic Scholar: заполнение card_authors.s2_author_id.

Задача владельца («есть сомнения — раздельно, лучше две страницы, чем одна с чужими
работами») упирается в то, что наш ключ автора — фамилия плюс инициалы: под «panov|ad»
слипаются разные люди, и таких неоднозначных ключей 7199.

ПОЧЕМУ ЧЕРЕЗ paper/batch, А НЕ author/search. Поиск по имени возвращает пять Пановых,
и выбирать из них пришлось бы вероятностно, тысячами запросов. Пакетная ручка
POST /graph/v1/paper/batch отдаёт до 500 работ за запрос по НАШИМ же идентификаторам
(externalIds вида ARXIV:2608.06359), и у каждой работы — список авторов с authorId.
То есть развод делает сам S2 ребром «работа → автор», а не мы догадками по имени.
Весь корпус (~6 700 работ) — 14 запросов.

ПРАВИЛО СКЛЕЙКИ (согласовано с архитектором, закреплено комментарием в схеме):
объединяем только при совпадении s2_author_id; чего S2 не знает — остаётся NULL
и к профилю по имени НЕ приклеивается. Слияние двух разных authorId в одного
человека — только руками.

СООТВЕТСТВИЕ ВНУТРИ РАБОТЫ — по ключу имени, не по позиции: порядок авторов у нас
и у S2 может расходиться (у S2 бывают развёрнутые имена). Ключ считаем одной и той же
функцией author_record.key_from_display с обеих сторон; совпадение принимается, только
если оно ЕДИНСТВЕННО в обе стороны — два «Wang J» в одной работе не сопоставляются
вовсе, чем гадать.

Пишет ТОЛЬКО колонку s2_author_id таблицы card_authors (граница с cards_sync:
таблицу cards не трогаем — по ней у ведущей идёт сверка отпечатков).

Запуск ИЗ ГЛАВНОЙ ПАПКИ (ключ и cards_sync там):
    python tools/s2_authors.py --dry            объём, без записи
    python tools/s2_authors.py --probe panov    показать группы по ключу, без записи
    python tools/s2_authors.py                  полный проход
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cloudflare"))
sys.path.insert(0, str(ROOT / "tools"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import requests
from cards_sync import q, lit, _env          # noqa: E402
from author_record import key_from_display   # noqa: E402

S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch"
CHUNK = 500          # предел ручки paper/batch
UPD_CHUNK = 300      # строк на один UPDATE к D1


def s2_key():
    k = _env().get("SEMANTIC_SCHOLAR_KEY", "")
    if not k:
        raise SystemExit("нет SEMANTIC_SCHOLAR_KEY в .env")
    return k


def bare(aid):
    """ARXIV-идентификатор без версии: S2 знает работы, а не версии."""
    i = aid.find("v")
    return aid[:i] if i > 0 and aid[i + 1:].isdigit() else aid


def fetch_batches(ids, key):
    """Работы пакетами. 429 и сеть — с бэкоффом; неотвеченный пакет НЕ теряется молча,
    а возвращается пустым с пометкой: пропуск здесь означал бы «S2 не знает работу»,
    что неправда и навсегда оставило бы её авторов без развода."""
    out = {}
    failed = []
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        body = {"ids": ["ARXIV:" + bare(x) for x in chunk]}
        for attempt in range(5):
            try:
                r = requests.post(S2_BATCH, params={"fields": "externalIds,authors"},
                                  json=body, headers={"x-api-key": key}, timeout=60)
                if r.status_code == 429:
                    wait = [2, 5, 15, 40, 60][attempt]
                    print(f"  429 — пауза {wait}с"); time.sleep(wait); continue
                r.raise_for_status()
                for src, paper in zip(chunk, r.json()):
                    out[src] = paper           # None, если S2 работу не знает
                break
            except requests.RequestException as e:
                if attempt == 4:
                    failed.append((i, len(chunk), type(e).__name__))
                    break
                time.sleep([2, 5, 15, 40][attempt])
        print(f"  пакет {i // CHUNK + 1}/{(len(ids) + CHUNK - 1) // CHUNK}: "
              f"получено {len(out)}")
        time.sleep(1.1)    # 1 rps — стандартный лимит ключа; пакетному пути хватает
    if failed:
        print(f"  ⚠️ НЕ ПОЛУЧЕНО пакетов: {failed} — их работы остаются без развода, "
              f"повторный запуск доберёт")
    return out


def _sur(k):
    return k.split("|", 1)[0]


def _ini(k):
    return k.split("|", 1)[1] if "|" in k else ""


def match_paper(rows_akeys, paper):
    """Сопоставление наших akey с авторами S2 внутри одной работы.
    Возвращает {akey: authorId} только для ОДНОЗНАЧНЫХ пар.

    Два яруса. Первый — точное равенство ключей, единственное в обе стороны.

    Второй появился после дефекта, пойманного ведущей на Панове: S2 сплошь и рядом
    хранит СОКРАЩЁННОЕ имя («A. Panov» там, где у нас «Alexander D. Panov»), и точное
    равенство наказывало за полноту — panov|ad не сопоставлялся вовсе, хотя S2 работы
    знает. Чем полнее автор назван у нас, тем вернее он оставался пустым.

    Поэтому ярус совместимости: фамилия та же, а один набор инициалов — префикс
    другого («a» совместимо с «ad»). Совместимость слабее равенства, и на wang|y она
    склеивала бы лишнее, — применяется ТОЛЬКО когда фамилия встречается ровно один раз
    среди ВСЕХ авторов работы с обеих сторон (не среди оставшихся — среди всех:
    так второй Панов в той же работе выключает ярус целиком). Риск при этом нулевой:
    один Панов у нас, один в S2 — это один человек, как бы коротко его ни записали."""
    if not paper:
        return {}
    s2_pairs = [(key_from_display(a.get("name") or ""), a["authorId"])
                for a in paper.get("authors") or [] if a.get("authorId")]
    s2 = defaultdict(list)                       # ключ имени → [authorId]
    for k, aid in s2_pairs:
        s2[k].append(aid)

    res = {}
    for akey in rows_akeys:
        cands = s2.get(akey) or []
        # ярус 1 — единственность в обе стороны: один кандидат у нас И один у S2
        if len(cands) == 1 and rows_akeys.count(akey) == 1:
            res[akey] = cands[0]

    # ярус 2 — совместимость инициалов при единственной фамилии с обеих сторон
    our_sur = defaultdict(int)
    for k in rows_akeys:
        our_sur[_sur(k)] += 1
    s2_sur = defaultdict(list)
    for k, aid in s2_pairs:
        s2_sur[_sur(k)].append((k, aid))
    for akey in rows_akeys:
        if akey in res:
            continue
        sur = _sur(akey)
        if our_sur[sur] != 1 or len(s2_sur.get(sur) or []) != 1:
            continue
        k2, aid = s2_sur[sur][0]
        i1, i2 = _ini(akey), _ini(k2)
        if i1.startswith(i2) or i2.startswith(i1):
            res[akey] = aid
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--probe", help="показать группы s2_author_id по подстроке ключа")
    a = ap.parse_args()

    rows = q("SELECT akey, id FROM card_authors")
    by_id = defaultdict(list)
    for r in rows:
        by_id[r["id"]].append(r["akey"])
    ids = sorted(by_id)
    print(f"связей {len(rows)}, работ {len(ids)}, пакетов {(len(ids) + CHUNK - 1) // CHUNK}")
    if a.dry:
        return 0

    papers = fetch_batches(ids, s2_key())
    known = sum(1 for p in papers.values() if p)
    print(f"S2 знает {known} из {len(ids)} работ")

    updates = []                                  # (akey, id, s2id)
    for aid, akeys in by_id.items():
        for akey, s2id in match_paper(akeys, papers.get(aid)).items():
            updates.append((akey, aid, s2id))
    print(f"однозначных сопоставлений: {len(updates)} из {len(rows)} связей")

    if a.probe:
        sub = a.probe.lower()
        groups = defaultdict(list)
        for akey, aid, s2id in updates:
            if sub in akey:
                groups[(akey, s2id)].append(aid)
        for (akey, s2id), works in sorted(groups.items()):
            print(f"  {akey} → s2:{s2id} · работ {len(works)}: {works[:6]}")
        print("(показ, записи нет)")
        return 0

    done = 0
    for i in range(0, len(updates), UPD_CHUNK):
        chunk = updates[i:i + UPD_CHUNK]
        whens = " ".join(
            f"WHEN {lit(ak + '|' + aid)} THEN {lit(s2)}" for ak, aid, s2 in chunk)
        keys = ", ".join(lit(ak + "|" + aid) for ak, aid, _ in chunk)
        q(f"UPDATE card_authors SET s2_author_id = CASE akey||'|'||id {whens} END "
          f"WHERE akey||'|'||id IN ({keys})")
        done += len(chunk)
        if (i // UPD_CHUNK) % 10 == 0:
            print(f"  записано {done}/{len(updates)}")
    print(f"✅ записано {done}")

    # Итог, ради которого всё: сколько ключей развелось на нескольких людей
    multi = q("SELECT akey, COUNT(DISTINCT s2_author_id) n FROM card_authors "
              "WHERE s2_author_id IS NOT NULL GROUP BY akey HAVING n > 1 "
              "ORDER BY n DESC LIMIT 15")
    total_multi = q("SELECT COUNT(*) c FROM (SELECT akey FROM card_authors "
                    "WHERE s2_author_id IS NOT NULL GROUP BY akey "
                    "HAVING COUNT(DISTINCT s2_author_id) > 1)")
    print(f"\nключей, под которыми РАЗНЫЕ люди: {total_multi[0]['c']}")
    for r in multi:
        print(f"  {r['akey']}: {r['n']} человек")
    return 0


if __name__ == "__main__":
    sys.exit(main())
