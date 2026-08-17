"""Сколько запросов съел Worker — по дням, из аналитики Cloudflare.

Зачем инструмент, а не разовый запрос. Бесплатный тариф Workers даёт 100 000 запросов
в сутки, и мы к нему подходим вплотную: 15 августа — 164 237. Такой замер нужен не один
раз, а каждый раз, когда меняем что-то, влияющее на число запросов, — иначе «стало лучше»
остаётся ощущением. Одна команда вместо составления GraphQL-запроса по памяти.

Что показываем и почему именно это:
  • запросы за сутки — то самое число, которое сравнивается с потолком;
  • ОШИБКИ — без них картина врёт: превышение потолка выглядит как отказы читателям,
    и отличить «много трафика» от «людей начали отшивать» можно только по ним;
  • подзапросы — обращения Worker'а наружу (модель, D1, R2): по ним видно, наш ли это
    собственный расход или чужой обход сайта.

    python tools/cf_usage.py              # неделя
    python tools/cf_usage.py --days 30    # месяц
    python tools/cf_usage.py --json       # для отчётов и сравнений
"""
import argparse
import datetime
import json
import os
import sys

import requests
from dotenv import load_dotenv
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
FREE_DAILY = 100_000        # потолок бесплатного тарифа Workers
QUERY = """
query($acc:String!,$since:Date!,$until:Date!){
  viewer{ accounts(filter:{accountTag:$acc}){
    workersInvocationsAdaptive(limit:1000, filter:{date_geq:$since, date_leq:$until}){
      sum{ requests errors subrequests }
      dimensions{ date }
    } } } }
"""


def fetch(days):
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        raise SystemExit("нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN")
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days - 1)
    r = requests.post(
        "https://api.cloudflare.com/client/v4/graphql", timeout=60,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json={"query": QUERY, "variables": {"acc": acc, "since": start.isoformat(),
                                            "until": end.isoformat()}})
    d = r.json()
    if d.get("errors"):
        raise SystemExit("Cloudflare: " + json.dumps(d["errors"], ensure_ascii=False)[:300])
    rows = d["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"]
    per = {}
    for x in rows:
        day = x["dimensions"]["date"]
        acc_ = per.setdefault(day, {"requests": 0, "errors": 0, "subrequests": 0})
        for k in acc_:
            acc_[k] += x["sum"][k]
    return per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    per = fetch(a.days)
    if a.json:
        print(json.dumps(per, ensure_ascii=False, indent=1))
        return 0

    today = datetime.date.today().isoformat()
    print(f"{'дата':12} {'запросов':>10} {'ошибок':>8} {'подзапросов':>12}  доля потолка")
    over = 0
    for day in sorted(per):
        v = per[day]
        share = v["requests"] / FREE_DAILY
        # Сегодняшний день неполный — сравнивать его с потолком нечестно, отмечаем.
        mark = "  (день идёт)" if day == today else ""
        if day != today and v["requests"] > FREE_DAILY:
            over += 1
            mark = "  ⚠️ ВЫШЕ ПОТОЛКА"
        print(f"{day:12} {v['requests']:10,} {v['errors']:8,} {v['subrequests']:12,}"
              f"  {share * 100:5.0f}%{mark}")
    if over:
        print(f"\nдней выше бесплатного потолка ({FREE_DAILY:,}/сутки): {over} из "
              f"{len(per) - 1}.")
        print("Ошибки в такие дни смотреть обязательно: если их единицы — читателей не "
              "отшивали, и это вопрос тарифа, а не аварии.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
