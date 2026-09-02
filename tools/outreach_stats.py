#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Статистика рассылки для страницы конвейера: сводка наружу, имена — внутрь.

Владелец 2026-09-01: «отмечай, что отправил, в статистику, в закрытую аналитику, чтобы
видел, кому когда отправлено; мы должны так же отслеживать все посещения страниц авторов
и посещения статей; отдельно в пайплайне, чтобы была статистика и я видел во всплывающем
окошке, кому отправлено».

ДВА ФАЙЛА, И ЭТО ГЛАВНОЕ РЕШЕНИЕ ЗДЕСЬ. /pipeline.html — страница ПУБЛИЧНАЯ, она есть в
карте сайта. Класть на неё имена людей, которым мы написали, и тем более их адреса нельзя:
адрес взят из работы для переписки и используется один раз по назначению, а не публикуется.

  · data/outreach-stats.json  — только числа. Публикуется вместе с сайтом.
  · data/outreach-sent.jsonl  — кому и когда. НЕ публикуется: заливка в R2 пропускает
    все .jsonl (cloudflare/deploy_r2.py, SKIP_SUFFIX). То есть «закрытая аналитика» здесь
    не новый секрет, который надо помнить и охранять, а уже действующее правило деплоя.

Адрес почты не попадает ДАЖЕ в закрытый файл: для ответа на вопрос «кому и когда» хватает
имени и номера работы, а лишняя копия персональных данных — лишний способ их потерять.

    python tools/outreach_stats.py          собрать оба файла
    python tools/outreach_stats.py --show   и показать в терминале
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

PUB = ROOT / "data" / "outreach-stats.json"
PRIV = ROOT / "data" / "outreach-sent.jsonl"
LOG = ROOT / "data" / "outreach-log.jsonl"
CAND = ROOT / "data" / "outreach-candidates.jsonl"


def _lines(p):
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def visits(sql, path=None, like=None, since=None):
    """Сколько раз открывали адрес (или группу адресов) с указанного дня."""
    where = "path=?" if path else "path LIKE ?"
    arg = path or like
    q = (f"SELECT COUNT(*) n, COUNT(DISTINCT uid) u, COUNT(DISTINCT path) p, MIN(day) first "
         f"FROM events WHERE dev=0 AND type='view' AND {where}")
    params = [arg]
    if since:
        q += " AND day>=?"
        params.append(since)
    try:
        r = sql(q, params) or [{}]
    except Exception:
        return {}
    return r[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="показать в терминале")
    args = ap.parse_args()

    import generate as G
    from author_letter import daily_cap
    try:
        from comments_triage import sql
    except Exception:
        sql = None

    sent = _lines(LOG)
    queue = _lines(CAND)
    today = date.today().isoformat()
    week = (date.today() - timedelta(days=7)).isoformat()

    # ── подробности: одна строка на письмо, без адреса ────────────────────────
    rows = []
    for r in sent:
        who = r.get("author") or ""
        day = (r.get("at") or "")[:10]
        aid = (r.get("aid") or "").strip()
        row = {"author": who, "aid": aid, "at": day, "lang": r.get("lang") or "en",
               "author_visits": 0, "paper_visits": 0, "came": False, "first": None}
        if sql and who:
            apath = f"/lang/en/authors/{G.author_slug(who)}.html"
            a = visits(sql, path=apath, since=day)
            row["author_visits"] = int(a.get("n") or 0)
            if aid:
                b = visits(sql, like=f"%/{aid}/%", since=day)
                row["paper_visits"] = int(b.get("n") or 0)
            row["came"] = bool(row["author_visits"] or row["paper_visits"])
            row["first"] = a.get("first") or None
        rows.append(row)
    rows.sort(key=lambda x: x["at"], reverse=True)

    # ── общая посещаемость: ВСЕ страницы авторов и статей, а не только адресаты.
    # Владелец просил именно так: рассылка это часть картины, а не вся картина.
    seen = {}
    if sql:
        month = (date.today() - timedelta(days=30)).isoformat()
        a = visits(sql, like="/lang/%/authors/%", since=month)
        p = visits(sql, like="/lang/%/archive/%", since=month)
        seen = {"authors": {"views": int(a.get("n") or 0), "pages": int(a.get("p") or 0),
                            "devices": int(a.get("u") or 0)},
                "papers": {"views": int(p.get("n") or 0), "pages": int(p.get("p") or 0),
                           "devices": int(p.get("u") or 0)},
                "days": 30}

    # ── сколько работ ещё ждёт разбора машиной знаний ─────────────────────────
    with_plus = without_plus = 0
    for f in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("recommend"):
            with_plus += 1
        else:
            without_plus += 1

    pub = {
        "updated": today,
        "sent": {"total": len(rows),
                 "week": sum(1 for r in rows if r["at"] >= week),
                 "today": sum(1 for r in rows if r["at"] == today),
                 "can_today": daily_cap()},
        "came": sum(1 for r in rows if r["came"]),
        "queue": len(queue),
        "plus": {"with": with_plus, "without": without_plus},
        "seen": seen,
        "detail": PRIV.name,
    }
    PUB.write_text(json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    PRIV.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")

    print(f"сводка → {PUB.relative_to(ROOT)} · подробности ({len(rows)}) → "
          f"{PRIV.relative_to(ROOT)} (не публикуется)")
    if args.show:
        print(f"\nотправлено {pub['sent']['total']} · за неделю {pub['sent']['week']} · "
              f"сегодня {pub['sent']['today']} (можно ещё {pub['sent']['can_today']})")
        print(f"пришли после письма: {pub['came']} · в очереди готовых: {pub['queue']}")
        print(f"работ с ✛ {with_plus}, ждут разбора {without_plus}")
        if seen:
            s = seen["authors"]
            print(f"за 30 дней · страницы авторов: {s['views']} заходов на {s['pages']} "
                  f"страниц, {s['devices']} устройств")
            s = seen["papers"]
            print(f"           · страницы статей: {s['views']} заходов на {s['pages']} "
                  f"страниц, {s['devices']} устройств")
        for r in rows[:20]:
            mark = "✅" if r["came"] else "· "
            print(f"  {mark} {r['at']}  {r['author'][:28]:28} {r['aid']:16} {r['lang']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
