"""Календарь совета: заседания по воскресеньям, уведомления за два дня.

Регламент владельца 2026-08-02: «заседания раз в неделю по воскресеньям, ставь
календарь, за два дня уведомления всем — почтой, если есть; если нет, зашли в кабинет,
увидели повестку». Отсюда две команды, обе идут в планировщик:

    python tools/council_schedule.py --notify    пятница: закрыть повестку и уведомить
    python tools/council_schedule.py --close     воскресенье вечером: подвести итоги
    python tools/council_schedule.py --plan      показать календарь на месяц вперёд

Почему отдельным инструментом, а не внутри рассылки: рассылка умеет отправлять письма,
календарь решает КОГДА. Смешаешь — и однажды письмо уйдёт в среду, потому что кто-то
запустил скрипт руками.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
COUNCIL = ROOT / "data" / "council"
NOTIFY_DAYS_BEFORE = 2


def next_sunday(d=None):
    d = d or date.today()
    return d + timedelta(days=(6 - d.weekday()) % 7)


def plan(n=5):
    s = next_sunday()
    return [(s + timedelta(weeks=i), s + timedelta(weeks=i) - timedelta(days=NOTIFY_DAYS_BEFORE))
            for i in range(n)]


def upcoming():
    p = COUNCIL / "upcoming.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def ensure_meeting(day):
    """Файл заседания на дату. Если его нет — заводим пустой каркас: повестку наполнят
    предложения участников и вопросы ИИ-участников, но день должен существовать заранее,
    иначе «раз в неделю» превращается в «когда соберёмся»."""
    p = COUNCIL / f"{day}.json"
    if not p.exists():
        p.write_text(json.dumps({
            "date": str(day), "number": None, "status": "open",
            "opened": str(date.today()), "agenda": [], "sprint": [], "next": []
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  заведено заседание {day}")
    (COUNCIL / "upcoming.json").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    return p


SITE = "https://bridge42worlds.academy"


def results(day):
    import requests
    try:
        r = requests.get(f"{SITE}/api/council/results?meeting={day}", timeout=25)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def frozen(day):
    import requests
    try:
        r = requests.get(f"{SITE}/api/council/frozen?meeting={day}", timeout=25)
        return (r.json() or {}).get("frozen") or {} if r.ok else {}
    except Exception:
        return {}


def carry_over(closed, nxt):
    """Что переезжает на следующее заседание: замороженное и то, по чему никто не решил.

    Владелец 13 августа: замороженный вопрос надо «обработать и пробовать переформулировать
    на следующее заседание с объяснением, почему не принято решение». Поэтому вопрос
    переносится СО СВОИМ идентификатором (иначе счётчик заморозок обнулится от смены
    заголовка) и с пометкой, откуда он взялся. Саму формулировку переписывает секретарь —
    здесь мы только гарантируем, что вопрос не потеряется.
    """
    keep = []
    for q in (closed.get("agenda") or []):
        if q.get("frozen"):
            item = dict(q)
            item.pop("decision", None)
            f = q["frozen"]
            item["carried"] = {
                "from": closed.get("date"),
                "reason": "заморожен",
                "why": f.get("why") or [],
                # Второй раз подряд — по регламенту решает кворум ИИ-участников.
                "to_ai_quorum": bool(f.get("quorum")),
            }
            item.pop("frozen", None)
            keep.append(item)
        elif not q.get("decision"):
            item = dict(q)
            item["carried"] = {"from": closed.get("date"), "reason": "никто не проголосовал"}
            keep.append(item)

    p = COUNCIL / f"{nxt}.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
        "date": str(nxt), "number": (closed.get("number") or 0) + 1, "status": "open",
        "opened": str(date.today()), "agenda": [], "sprint": [], "next": []}
    have = {q.get("id") for q in (data.get("agenda") or [])}
    data["agenda"] = (data.get("agenda") or []) + [q for q in keep if q.get("id") not in have]
    if not data.get("number"):
        data["number"] = (closed.get("number") or 0) + 1
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return keep


def publish():
    """Выложить файлы совета: без этого закрытие видно только на этой машине."""
    r = subprocess.run([sys.executable, str(ROOT / "cloudflare" / "deploy_r2.py")],
                       cwd=ROOT, env={**os.environ, "B42_DEPLOY_OK": "1"})
    print("выложено" if r.returncode == 0 else f"⚠️ выкладка вернула {r.returncode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--close", action="store_true")
    args = ap.parse_args()

    if args.plan or not (args.notify or args.close):
        print("Заседания по воскресеньям, уведомления за два дня:")
        for meet, notify in plan():
            print(f"  {meet}  ←  уведомления {notify}")
        m = upcoming()
        print(f"\nближайшее в работе: {m.get('date','—')}, вопросов {len(m.get('agenda') or [])}")
        return 0

    if args.notify:
        day = next_sunday()
        ensure_meeting(day)
        m = upcoming()
        if not (m.get("agenda") or []):
            print("⚠️ повестка пуста — уведомлять не о чем. Сначала ИИ-участники вносят "
                  "3-4 вопроса развития, предложения читателей подтягиваются сами.")
            return 1
        print(f"повестка заседания {day}: вопросов {len(m['agenda'])} — рассылаю")
        return subprocess.run([sys.executable, str(ROOT / "tools" / "council_mail.py"), "--agenda"]).returncode

    if args.close:
        m = upcoming()
        day = m.get("date")
        if not day:
            print("нет заседания для закрытия")
            return 1
        p = COUNCIL / f"{day}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["status"] = "closed"
        d["closed"] = str(date.today())

        # Итоги — в файл заседания. До этого они жили только в базе, и «история
        # заседаний» показывала закрытое заседание без единого решения: страница читает
        # файлы, а голоса лежали в D1. Пишем решение к каждому вопросу словами.
        res, frz = results(day), frozen(day)
        decided = 0
        for q in (d.get("agenda") or []):
            qid = q.get("id")
            if qid in frz:
                q["frozen"] = {"why": frz[qid].get("why") or [],
                               "times": frz[qid].get("times") or 1,
                               "quorum": bool(frz[qid].get("quorum"))}
                continue
            tally = (res.get("results") or {}).get(qid) or {}
            if not tally:
                continue
            names = {str(o.get("id")): str(o.get("label") or o.get("id"))
                     for o in (q.get("options") or []) if isinstance(o, dict)}
            choice, n = max(tally.items(), key=lambda kv: kv[1])
            q["decision"] = {"choice": choice, "label": names.get(choice, choice),
                             "votes": n, "of": sum(tally.values())}
            decided += 1
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

        nxt = next_sunday(date.today() + timedelta(days=1))
        carried = carry_over(d, nxt)
        d["next_meeting"] = {"date": str(nxt),
                             "questions": [q.get("title", "") for q in carried]}
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        (COUNCIL / "upcoming.json").write_text(
            (COUNCIL / f"{nxt}.json").read_text(encoding="utf-8"), encoding="utf-8")

        print(f"заседание {day} закрыто: решений {decided}, заморожено {len(frz)}, "
              f"перенесено на {nxt}: {len(carried)}")
        publish()
        return subprocess.run([sys.executable, str(ROOT / "tools" / "council_mail.py"), "--results"]).returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
