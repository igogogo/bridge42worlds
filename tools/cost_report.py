"""Куда уходят деньги: себестоимость статьи, расход за день, остаток на счетах.

Владелец 2026-08-01: «себестоимость статьи, экспресса, перевода — всё отдельно; должен
быть план оптимизации; бюджет 250$ в месяц — следи; сделай мониторинг и фиксируй
в бюджете; отчёт раз в день в канал».

Считаем по своему журналу вызовов (data/usage-log.jsonl), а не по счёту поставщика:
счёт приходит одной суммой и не отвечает на вопрос «сколько стоит одна статья».
Журнал пишет каждый вызов с моделью и токенами, поэтому цену можно разложить
по шагам работы — а значит, понять, что именно оптимизировать.

    python tools/cost_report.py                 отчёт за вчера + месяц, в консоль
    python tools/cost_report.py --send          он же — в Telegram-канал
    python tools/cost_report.py --days 7        за неделю
    python tools/cost_report.py --json          machine-readable в data/cost-summary.json

Цены — в config.json (prices), чтобы правка тарифа не требовала правки кода.
Остаток DeepSeek берём живьём из их же API: расход считаем сами, но «сколько осталось»
знает только поставщик.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "usage-log.jsonl"
OUT = ROOT / "data" / "cost-summary.json"

# Цены за миллион токенов (USD). Значения — с прайса DeepSeek, проверено 2026-08-01.
# Держим в коде как запасные: config.json их перекрывает.
DEFAULT_PRICES = {
    "deepseek-v4-pro":   {"cache_hit": 0.003625, "cache_miss": 0.435, "output": 0.87},
    "deepseek-v4-flash": {"cache_hit": 0.0028,   "cache_miss": 0.14,  "output": 0.28},
}

# Шаги работы → к какому продукту относить их стоимость. Нужен, чтобы ответить не
# «сколько стоил день», а «сколько стоит ОДНА экспресс-статья» — иначе оптимизировать
# нечего: видно сумму, не видно причину.
KIND = {
    "article_express": "экспресс",
    "article_advanced": "полная", "article_popular": "полная",
    "article_simple": "полная", "article_combo": "полная",
    "refine_simple": "шлифовка", "refine_popular": "шлифовка",
    "abstract": "аннотация",
    "translate": "перевод", "translate_flash": "перевод", "translate_ref": "перевод",
    "select": "отбор", "rank": "отбор",
    "tutor": "бот", "ask": "бот",
    "cluster_interpret": "аналитика",
}


def cfg():
    try:
        return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def prices():
    p = dict(DEFAULT_PRICES)
    p.update((cfg().get("prices") or {}))
    return p


def cost_of(rec, pr):
    """Цена одного вызова. Кэш-попадания считаем отдельно: у DeepSeek они дешевле входа
    в сто с лишним раз, и без этого разделения расход завышается в разы."""
    m = pr.get(rec.get("model")) or pr.get("deepseek-v4-pro")
    hit = rec.get("cache_hit", 0) or 0
    miss = rec.get("cache_miss")
    if miss is None:                       # старые записи: разницы не знали
        miss = max(0, (rec.get("prompt", 0) or 0) - hit)
    out = rec.get("completion", 0) or 0
    return (hit * m["cache_hit"] + miss * m["cache_miss"] + out * m["output"]) / 1e6


def read(days):
    """Журнал за N последних дней + счётчик статей по дням из архива."""
    if not LOG.exists():
        return [], {}
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = []
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if (r.get("ts") or "")[:10] >= since:
            rows.append(r)
    # Сколько статей сделано в те же дни — чтобы делить деньги на штуки
    made = defaultdict(lambda: {"экспресс": 0, "полная": 0})
    arch = ROOT / "lang" / "ru" / "archive"
    for d in arch.glob("*"):
        if d.name < since:
            continue
        for f in d.glob("*/data.json"):
            try:
                j = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            made[d.name]["экспресс" if j.get("express") else "полная"] += 1
    return rows, made


def balance():
    """Остаток у поставщика — единственное, что нельзя посчитать самим."""
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    key = env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        import requests
        r = requests.get((env.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com") + "/user/balance",
                         headers={"Authorization": f"Bearer {key}"}, timeout=20)
        if r.status_code != 200:
            return None
        for b in r.json().get("balance_infos", []):
            if b.get("currency") == "USD":
                return float(b.get("total_balance", 0))
    except Exception:
        return None
    return None


def build(days):
    rows, made = read(days)
    pr = prices()
    by_day, by_kind, by_agent = defaultdict(float), defaultdict(float), defaultdict(lambda: [0, 0.0])
    tokens = 0
    for r in rows:
        c = cost_of(r, pr)
        day = (r.get("ts") or "")[:10]
        kind = KIND.get(r.get("agent"), "прочее")
        by_day[day] += c
        by_kind[kind] += c
        a = by_agent[r.get("agent") or "?"]
        a[0] += 1
        a[1] += c
        tokens += (r.get("prompt", 0) or 0) + (r.get("completion", 0) or 0)

    n_exp = sum(v["экспресс"] for v in made.values())
    n_full = sum(v["полная"] for v in made.values())
    # Себестоимость штуки. ВАЖНО: разовые работы в неё не входят.
    # Первая версия этого отчёта делила ВЕСЬ перевод недели на статьи недели — и выдала
    # 29 центов за перевод статьи вместо реальных копеек. В ту сумму попали перевод
    # справочников (710 вызовов, делается раз в жизни, а не на каждую статью) и догон
    # старых статей. Владелец поймал ошибку сразу: «у нас статья в центах, ты не прав».
    # Он был прав; теперь разовое считается отдельно и в цену статьи не попадает.
    ONE_OFF = {"translate_ref"}          # справочники: разово на язык, не на статью
    one_off = sum(by_agent[k][1] for k in ONE_OFF if k in by_agent)

    # Точный счёт — по метке вызова (common.job): к какой статье и какому виду он относился.
    # Метка появилась 2026-08-02; для более старых записей её нет, и тогда остаётся дележка
    # поровну — она ЗАВЫШАЕТ экспресс и занижает полную, потому что экспресс переводится
    # дешёвой моделью, а полная дорогой. На сверке 2026-08-02 это дало 12 центов за экспресс
    # вместо девяти и сделало его почти равным полной — а решение «ежедневно только экспресс»
    # принималось как раз по этим числам. Поэтому честность оценки печатается рядом.
    tagged = defaultdict(float)
    tagged_ids = defaultdict(set)
    n_tagged = 0
    for r in rows:
        k = r.get("kind")
        if k in ("экспресс", "полная"):
            n_tagged += 1
            tagged[k] += cost_of(r, pr)
            if r.get("article"):
                tagged_ids[k].add(r["article"])

    per_article = (n_exp + n_full) or 1
    tr_share = max(0.0, by_kind.get("перевод", 0) - one_off) / per_article
    if n_tagged:
        # Делим на число статей, реально помеченных в журнале, а не на число папок в архиве:
        # иначе догон старых статей и статьи, сделанные за пределами окна, снова всё смешают.
        m_exp = len(tagged_ids["экспресс"]) or n_exp or 1
        m_full = len(tagged_ids["полная"]) or n_full or 1
        unit = {
            "экспресс": (tagged["экспресс"] / m_exp) if tagged["экспресс"] else None,
            "полная": (tagged["полная"] / m_full) if tagged["полная"] else None,
            "перевод_одной_статьи": None,
            "точность": f"по метке вызова ({n_tagged} из {len(rows)} записей)",
        }
    else:
        unit = {
            "экспресс": (by_kind.get("экспресс", 0) / n_exp + tr_share) if n_exp else None,
            "полная": ((by_kind.get("полная", 0) + by_kind.get("шлифовка", 0)) / n_full + tr_share) if n_full else None,
            "перевод_одной_статьи": tr_share or None,
            "точность": "оценка: перевод делится поровну, экспресс завышен",
        }
    total = sum(by_day.values())
    month = sum(v for k, v in by_day.items() if k[:7] == datetime.now().strftime("%Y-%m"))
    return {
        "days": days, "total": total, "month": month, "one_off": one_off,
        "budget": (cfg().get("budget_usd") or 250),
        "balance": balance(), "tokens": tokens,
        "by_day": dict(sorted(by_day.items())),
        "by_kind": dict(sorted(by_kind.items(), key=lambda x: -x[1])),
        "by_agent": {k: {"n": v[0], "usd": round(v[1], 4)} for k, v in
                     sorted(by_agent.items(), key=lambda x: -x[1][1])},
        "articles": {"экспресс": n_exp, "полная": n_full},
        "unit_cost": unit,
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def human(s):
    b, mon, budget = s["balance"], s["month"], s["budget"]
    left_pct = int(100 * mon / budget) if budget else 0
    lines = [f"💰 <b>Расходы · {s['built'][:10]}</b>", ""]
    lines.append(f"За {s['days']} дн.: <b>${s['total']:.2f}</b> · с начала месяца: <b>${mon:.2f}</b> из ${budget} ({left_pct}%)")
    if b is not None:
        warn = " ⚠️ ПОПОЛНИТЬ" if b < 20 else ""
        lines.append(f"Остаток на счёте DeepSeek: <b>${b:.2f}</b>{warn}")
    lines.append("")
    u = s["unit_cost"]
    if u.get("экспресс"):
        lines.append(f"Себестоимость экспресса: <b>${u['экспресс']:.4f}</b>")
    if u.get("полная"):
        lines.append(f"Себестоимость полной: <b>${u['полная']:.4f}</b>")
    if u.get("перевод_одной_статьи"):
        lines.append(f"Из них перевод: ${u['перевод_одной_статьи']:.4f}")
    # Насколько числу можно верить — рядом с самим числом, а не в документации.
    # По этим цифрам решают, что гнать ежедневно; молчаливая оценка тут дороже строчки.
    if u.get("точность") and (u.get("экспресс") or u.get("полная")):
        lines.append(f"<i>{u['точность']}</i>")
    lines.append(f"Сделано за период: {s['articles']['экспресс']} экспресс · {s['articles']['полная']} полных")
    lines.append("")
    lines.append("<b>На что ушло:</b>")
    for k, v in list(s["by_kind"].items())[:6]:
        share = int(100 * v / s["total"]) if s["total"] else 0
        lines.append(f"  {k}: ${v:.2f} ({share}%)")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--send", action="store_true", help="отправить в Telegram-канал")
    ap.add_argument("--json", action="store_true", help="записать data/cost-summary.json")
    args = ap.parse_args()
    s = build(args.days)
    text = human(s)
    print(text.replace("<b>", "").replace("</b>", ""))
    if args.json:
        OUT.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ {OUT}")
    if args.send:
        sys.path.insert(0, str(ROOT / "tools"))
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"), text],
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
