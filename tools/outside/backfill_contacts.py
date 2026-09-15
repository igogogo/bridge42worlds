# -*- coding: utf-8 -*-
"""Дописать адреса авторов в уже принятые работы bioRxiv/medRxiv.

Разбирая JATS, мы брали только <body> и теряли шапку <front>, где у препринт-серверов
живут адреса авторов для переписки. Замер 15.09.2026: адрес нашёлся в 1% наших био-работ
против 74% у arXiv — рассылка по биологии была бы невозможна, и причина была бы невидима,
потому что письма молча не находили бы кому писать.

Сборщик починен (jats_contacts), но принятым работам это не поможет: их fulltext.txt уже
на диске. Этот проход ходит за шапкой ещё раз и приписывает адреса в начало файла — туда,
где их ищет реестр контактов (tools/author_contacts.py).

КУДА ПОПАДАЮТ АДРЕСА. В fulltext.txt, который НЕ публикуется (SKIP_NAMES в deploy_r2) и
не коммитится. Дальше их разбирает author_contacts.py в data/authors-contacts.jsonl —
файл вне git и вне публикации. Персональные данные живых людей нигде не всплывают.

    python tools/outside/backfill_contacts.py          показать, скольким нужно
    python tools/outside/backfill_contacts.py --apply  дописать
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

_spec = importlib.util.spec_from_file_location("bx", HERE / "biorxiv.py")
BX = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BX)

MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def main():
    ap = argparse.ArgumentParser(description="Адреса авторов в принятые био-работы")
    ap.add_argument("--apply", action="store_true", help="дописать; без ключа — показ")
    ap.add_argument("--limit", type=int, default=0, help="сколько взять за прогон")
    a = ap.parse_args()

    todo = []
    for rec_p in sorted((HERE / "works").glob("*.json")):
        try:
            rec = json.loads(rec_p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not rec.get("jatsxml"):
            continue
        hits = list((ROOT / "lang" / "ru" / "archive").glob(f"*/{rec['id']}/fulltext.txt"))
        if not hits:
            continue
        ft = hits[0]
        try:
            head = ft.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        if MAIL.search(head):
            continue                      # адрес уже есть — не трогаем
        todo.append((rec, ft))

    print(f"работ с шапкой JATS и без адреса: {len(todo)}")
    if not a.apply:
        for rec, _ in todo[:5]:
            print(f"   {rec['id']}  {rec['title'][:64]}")
        print("\nэто показ. Дописать: --apply")
        return 0

    if a.limit:
        todo = todo[:a.limit]
    got = empty = failed = 0
    for i, (rec, ft) in enumerate(todo, 1):
        try:
            xml = BX._get(rec["jatsxml"]).decode("utf-8", "replace")
            mails = BX.jats_contacts(xml)
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(todo)}] {rec['id']}: не далось ({type(e).__name__})")
            continue
        if not mails:
            empty += 1
            continue
        try:
            body = ft.read_text(encoding="utf-8", errors="replace")
            ft.write_text("Corresponding author(s): " + ", ".join(mails) + "\n\n" + body,
                          encoding="utf-8")
        except OSError as e:
            failed += 1
            print(f"[{i}/{len(todo)}] {rec['id']}: запись не далась ({e})")
            continue
        got += 1
        if i % 20 == 0:
            print(f"   [{i}/{len(todo)}] с адресами {got}, без {empty}, сбоев {failed}")
    print(f"\n✅ дописано {got}, без адреса в шапке {empty}, сбоев {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
