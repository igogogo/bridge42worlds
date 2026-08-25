#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Склейка расщеплённых профилей по почтовому адресу: кто на самом деле один человек.

ЗАЧЕМ. Semantic Scholar разводит авторов хорошо, но ошибается в ОБЕ стороны: у него бывают
и слитые профили, и лишне расщеплённые. Проверка 25 августа на нашем корпусе: в 124 ключах
работы с ОДНИМ И ТЕМ ЖЕ почтовым адресом попали к разным authorId. Самый наглядный случай —
тот, на котором владелец отлаживал страницы: `panov|ad` разошёлся на ЧЕТЫРЕХ «людей», а все
четверо пишут с одного адреса в Институте ядерной физики МГУ. Это один человек.

ПРАВИЛО, И ОНО НЕСИММЕТРИЧНО. Совпал адрес — один человек, спорить не о чем. Обратное
НЕВЕРНО: разные адреса вовсе не значат разных людей — человек меняет институт и почту,
оставаясь собой. Замер тех же данных: 47 пар «разные адреса при одном authorId», из них
14 в одном домене. Применить признак симметрично значило бы наплодить ложных разделений на
ровном месте. Поэтому здесь только СКЛЕЙКА и никогда разделение.

ГРАНИЦА ПРИВАТНОСТИ. Адреса живут только на этой машине: data/authors-contacts.jsonl закрыт
и от git, и от публикации. В облако уходит ТОЛЬКО person_id — число, по которому ничего
нельзя восстановить. Почтовый адрес не должен появляться в базе, которую читает сайт, даже
в служебной колонке: то, чего там нет, невозможно случайно отдать наружу.

    python tools/person_merge.py            что склеится, ничего не меняя
    python tools/person_merge.py --apply    записать person_id в D1
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cloudflare"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

CONTACTS = ROOT / "data" / "authors-contacts.jsonl"


def norm(addr):
    """Адрес к сравнимому виду.

    Из PDF почта нередко приходит со знаком сноски, приклеенным спереди: «1panov@…» — это
    надстрочная единица, съехавшая в текст при извлечении. Без чистки такой адрес выглядит
    чужим, и человек разъезжается сам с собой ровно по этой мелочи (поймано на Панове)."""
    a = (addr or "").strip().lower()
    a = a.lstrip("0123456789*†‡§¶,;")
    return a


def load_mail():
    """(ключ автора, id работы) → адрес."""
    out = {}
    if not CONTACTS.exists():
        return out
    with CONTACTS.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            aid = (d.get("id") or "").split("v")[0]
            for e in (d.get("emails") or []):
                k, a = e.get("akey"), norm(e.get("email"))
                if k and a:
                    out[(k, aid)] = a
    return out


def plan(rows, mail):
    """Что с чем склеить: для каждого ключа — отображение s2_author_id → канонический.

    Канонический выбираем по числу работ: у профиля, под которым их больше, выше шанс, что
    именно он останется живым в S2 и совпадёт с тем, что человек видит о себе сам."""
    by_key = defaultdict(lambda: defaultdict(set))     # ключ → адрес → {s2 id}
    weight = defaultdict(lambda: defaultdict(int))     # ключ → s2 id → работ
    for r in rows:
        k = r["akey"]
        s2 = r.get("s2_author_id")
        if s2:
            weight[k][s2] += 1
        a = mail.get((k, (r["id"] or "").split("v")[0]))
        if a and s2:
            by_key[k][a].add(s2)

    merges = {}
    for k, addrs in by_key.items():
        # объединяем идентификаторы, встретившиеся под одним адресом, транзитивно:
        # адрес A связал 1 и 2, адрес B связал 2 и 3 — значит 1, 2 и 3 один человек
        groups = []
        for ids in addrs.values():
            hit = [g for g in groups if g & ids]
            if hit:
                merged = set(ids)
                for g in hit:
                    merged |= g
                    groups.remove(g)
                groups.append(merged)
            else:
                groups.append(set(ids))
        for g in groups:
            if len(g) < 2:
                continue
            canon = max(g, key=lambda s: (weight[k][s], s))
            for s in g:
                if s != canon:
                    merges[(k, s)] = canon
    return merges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--probe", help="показать разбор одного ключа")
    args = ap.parse_args()

    import cards_sync as cs

    mail = load_mail()
    print(f"адресов, привязанных к работам: {len(mail)}")
    rows = cs.q("SELECT akey, id, s2_author_id FROM card_authors")
    merges = plan(rows, mail)

    keys = sorted({k for k, _ in merges})
    print(f"профилей к склейке: {len(merges)} · затронуто ключей автора: {len(keys)}")
    for k in keys[:10]:
        pairs = [(s, c) for (kk, s), c in merges.items() if kk == k]
        print(f"   {k:18} " + ", ".join(f"{s}→{c}" for s, c in pairs[:4]))

    if args.probe:
        for r in rows:
            if r["akey"] == args.probe:
                s2 = r.get("s2_author_id")
                print(f"   {r['id']:14} s2={s2} → person="
                      f"{merges.get((r['akey'], s2), s2)}")

    if not args.apply:
        print("\nничего не менялось — добавь --apply")
        return 0

    # ALTER TABLE ... ADD COLUMN не умеет IF NOT EXISTS в SQLite — ловим повтор по
    # тексту ошибки, ровно как это уже сделано в cards_sync.ensure_schema.
    try:
        cs.q("ALTER TABLE card_authors ADD COLUMN person_id TEXT")
        print("  колонка person_id заведена")
    except RuntimeError as e:
        if "duplicate column" not in str(e):
            raise
    cs.q("CREATE INDEX IF NOT EXISTS card_authors_person ON card_authors(akey, person_id)")

    # По умолчанию человек — это профиль S2; склейка только переписывает часть значений.
    cs.q("UPDATE card_authors SET person_id = s2_author_id WHERE person_id IS NULL OR person_id <> s2_author_id")
    n = 0
    items = list(merges.items())
    for i in range(0, len(items), 60):
        part = items[i:i + 60]
        cond = " OR ".join(
            f"(akey={cs.lit(k)} AND s2_author_id={cs.lit(s)})" for (k, s), _ in part)
        # у пачки может быть несколько разных канонических — пишем по одному CASE
        case = " ".join(
            f"WHEN akey={cs.lit(k)} AND s2_author_id={cs.lit(s)} THEN {cs.lit(c)}"
            for (k, s), c in part)
        cs.q(f"UPDATE card_authors SET person_id = CASE {case} ELSE person_id END "
             f"WHERE {cond}")
        n += len(part)
        print(f"      … {n}/{len(items)}")
    print(f"\nсклеено профилей: {n}")
    left = cs.q("SELECT COUNT(DISTINCT person_id) p, COUNT(DISTINCT s2_author_id) s "
                "FROM card_authors WHERE s2_author_id IS NOT NULL")[0]
    print(f"разных людей после склейки: {left['p']} (профилей S2 было {left['s']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
