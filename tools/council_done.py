#!/usr/bin/env python3
"""Отметить, что сделано по решению совета.

Владелец 13 августа: «отчёт по выполнению решений — как думаешь?» и «по плану прогоним,
увидим, что сделано, какие вопросы появились».

Зачем это вообще. Сегодня решение совета никуда не ведёт: проголосовали, записали,
разошлись. Через неделю никто не помнит, что из этого сделано, — и совет незаметно
превращается в опрос мнений. Голосовать второй раз человек придёт только если увидел,
что первый голос к чему-то привёл.

Отсюда правило: у КАЖДОГО принятого решения есть строка исполнения, и она показывается
там, где её увидят, — на странице заседания и первым разделом в письме со следующей
повесткой. Заполняет ведущая при слиянии веток: решение → задача → коммит.

    python tools/council_done.py --список
    python tools/council_done.py --вопрос a3 --статус сделано --что "Порог кворума 3 внесён в регламент" --коммит 7f3a1c2
    python tools/council_done.py --вопрос a1 --статус "в работе" --что "Французский догоняется, 1453 из 2110"
"""
import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUNCIL = ROOT / "data" / "council"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

СТАТУСЫ = ("не начато", "в работе", "сделано", "отменено")


def last_closed():
    """Последнее ЗАКРЫТОЕ заседание: по его решениям и отчитываемся."""
    files = sorted(COUNCIL.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"), reverse=True)
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("status") == "closed":
            return f, d
    return None, None


def commit_subject(sha):
    """Заголовок коммита — чтобы в отчёте стояло человеческое «что сделано», а не хэш."""
    if not sha:
        return ""
    r = subprocess.run(["git", "log", "-1", "--pretty=%s", sha], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--заседание", dest="meeting", help="дата, по умолчанию последнее закрытое")
    ap.add_argument("--вопрос", dest="qid", help="идентификатор вопроса, например a3")
    ap.add_argument("--статус", dest="status", choices=СТАТУСЫ)
    ap.add_argument("--что", dest="what", default="", help="что именно сделано, одной строкой")
    ap.add_argument("--коммит", dest="commit", default="", help="хэш коммита, если есть")
    ap.add_argument("--список", dest="show", action="store_true", help="показать решения и их статус")
    args = ap.parse_args()

    if args.meeting:
        p = COUNCIL / f"{args.meeting}.json"
        if not p.exists():
            print(f"нет заседания {args.meeting}")
            return 1
        d = json.loads(p.read_text(encoding="utf-8"))
    else:
        p, d = last_closed()
        if not d:
            print("закрытых заседаний пока нет — отчитываться не по чему")
            return 1

    agenda = d.get("agenda") or []
    decided = [q for q in agenda if q.get("decision")]

    if args.show or not args.qid:
        print(f"Заседание {d.get('date')} · решений {len(decided)} из {len(agenda)} вопросов\n")
        for q in decided:
            done = q.get("done") or {}
            mark = {"сделано": "✅", "в работе": "🔧", "отменено": "✖", "не начато": "· "}.get(
                done.get("status", "не начато"), "· ")
            print(f"{mark} [{q.get('id')}] {q.get('title', '')[:70]}")
            print(f"      решено: {q['decision'].get('label')} "
                  f"({q['decision'].get('votes')} из {q['decision'].get('of')})")
            if done.get("what"):
                print(f"      сделано: {done['what']}")
        if not decided:
            print("  (решений нет: либо никто не голосовал, либо все вопросы заморожены)")
        return 0

    q = next((x for x in agenda if x.get("id") == args.qid), None)
    if not q:
        print(f"вопроса {args.qid} нет в повестке {d.get('date')}")
        return 1
    if not q.get("decision"):
        print(f"по вопросу {args.qid} решения не было — отмечать нечего")
        return 1
    if not args.status:
        print("нужен --статус: " + ", ".join(СТАТУСЫ))
        return 1

    what = args.what or commit_subject(args.commit)
    q["done"] = {"status": args.status, "what": what, "when": str(date.today()),
                 "commit": args.commit}
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {args.qid}: {args.status}" + (f" — {what}" if what else ""))
    print(f"   записано в {p.relative_to(ROOT)}; страницу заседания пересоберёт council_build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
