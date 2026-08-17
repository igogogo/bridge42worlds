#!/usr/bin/env python3
"""Сторож бюджета: считает расход по журналу вызовов и не даёт превысить потолок.

Владелец 7 августа: «даю двести, но чтобы всё было и без косяков — не переводить по пять
раз одно и то же и не запускать заново; учти и строго соблюдай контроль».

Это отказ, а не совет. Прогон, упирающийся в потолок, не запускается — потому что
предупреждение в логе никто не читает, а деньги кончаются молча.

Три предела, каждый со своим смыслом:
  · МЕСЯЦ  — общий потолок, дальше не идём вовсе;
  · ДЕНЬ   — месячный потолок, разделённый на дни, плюс запас: иначе весь бюджет
             можно сжечь за трое суток и остаться без ленты на три недели;
  · ПРОГОН — предохранитель от одной сорвавшейся команды, которая крутится в цикле.

    python tools/budget_guard.py             показать состояние
    python tools/budget_guard.py --check     проверить перед прогоном (код 1 = не запускать)
    python tools/budget_guard.py --room 5    хватит ли ещё на $5
"""
import argparse
import collections
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Потолок месяца. Меняется решением владельца, а не по ходу дела — поэтому здесь,
# а не в переменной окружения, где правку никто не заметит.
# Бюджетный период начался 8 августа, а не первого числа: до этого деньги тратились по
# другим правилам, и мешать их с новым бюджетом — значит пугать себя цифрами, которых
# в кошельке нет (владелец 2026-08-09: «считай только то, что потрачено со вчера, не пугай;
# у нас потрачено максимум 6-7, и вот это и есть бюджет — он начался с 8 августа»).
BUDGET_START = "2026-08-08"
MONTH_CAP = 200.0
# Дневная доля с запасом в полтора раза: лента идёт неравномерно, догоны бывают крупными,
# и жёсткое деление на 31 останавливало бы законные прогоны.
DAY_CAP = MONTH_CAP / 31 * 1.5
# Один прогон дороже этого — почти наверняка сорвавшийся цикл, а не работа.
RUN_CAP = 25.0

# Цены за миллион токенов. С 16 августа 2026 (16:00 UTC) DeepSeek ввёл разные тарифы
# для часов пик и остального времени: вне пика ровно вдвое дешевле.
#
# Пик по UTC: 01:00-04:00 и 06:00-10:00. У нашей машины UTC+3, значит по местному
# времени пик — с 04:00 до 07:00 и с 09:00 до 13:00. Всё остальное дешевле вдвое.
#
# Считать по времени КАЖДОЙ записи, а не по текущему часу: журнал расхода читается
# задним числом, и запрос, сделанный ночью, должен стоить ночную цену и через неделю.
PRICES = {
    "deepseek-v4-pro":   {"off": {"h": 0.022, "m": 0.66, "o": 1.98},
                          "peak": {"h": 0.044, "m": 1.32, "o": 3.96}},
    "deepseek-v4-flash": {"off": {"h": 0.007, "m": 0.22, "o": 0.66},
                          "peak": {"h": 0.014, "m": 0.44, "o": 1.32}},
}
# До этой даты действовал прежний прайс — старые записи журнала пересчитывать по новому
# нельзя, иначе месячный расход задним числом вырастет вдвое и остаток соврёт.
NEW_PRICES_FROM = "2026-08-16"
OLD_PRICES = {"deepseek-v4-pro":   {"h": 0.003625, "m": 0.435, "o": 0.87},
              "deepseek-v4-flash": {"h": 0.0028,   "m": 0.14,  "o": 0.28}}


# Чужие модели считаем по ИХ цене, а не по нашей.
#
# Реранкер (qwen3-reranker-8b) и векторизатор (bge-m3) работают у DeepInfra, а не у
# DeepSeek, но в журнале расхода лежат вперемешку. price_for раньше не знал таких имён
# и падал на «пусть будет flash» — 19,2 млн их токенов оказались посчитаны по прайсу
# DeepSeek: $2,68 вместо примерно $0,96, а по новому прайсу насчитало бы $4,22.
# Отчёт о деньгах, который завышает расход втрое на четверти объёма, вреден вдвойне:
# по нему принимаются решения о том, сколько статей мы можем себе позволить.
#
# Цены DeepInfra за миллион токенов. СВЕРЕНО 2026-08-17 по их собственному прайсу
# (GET https://api.deepinfra.com/models/list, поле pricing.cents_per_input_token —
# проверить можно командой `python tools/deepinfra_prices.py`):
#   Qwen/Qwen3-Reranker-8B — 5e-06 цента за токен = $0.05 за миллион
#   BAAI/bge-m3            — 1e-06 цента за токен = $0.01 за миллион
# Пометка «предположено» снята: оценка совпала с прайсом до цифры. Это стоит записать
# именно так, а не молча — иначе следующий человек снова пойдёт сверять уже сверенное.
# Кэша у этих моделей нет: все три поля одинаковые, чтобы формула осталась одна на всех.
OTHER_PRICES = {
    "qwen3-reranker-8b": {"h": 0.05, "m": 0.05, "o": 0.05},
    "bge-m3":            {"h": 0.01, "m": 0.01, "o": 0.01},
}

# Обложки. Считаются НЕ по токенам, а поштучно, поэтому в общую формулу не встают —
# и до сих пор в расходе не учитывались вовсе. Цена за картинку 1024×1024, прайс тот же:
#   black-forest-labs/FLUX-2-pro     — 1.5 цента за единицу изображения
#   black-forest-labs/FLUX-1-schnell — 0.05 цента (черновой пресет)
# Держим здесь, чтобы число было в одном месте с остальными ценами; пользуется им
# отдельный подсчёт (журнал обложек), а не price_for.
IMAGE_PRICES_USD = {
    "black-forest-labs/FLUX-2-pro": 0.015,
    "black-forest-labs/FLUX-1-schnell": 0.0005,
}


def price_for(model, ts):
    """Тариф для записи журнала: по её дате, часу UTC и владельцу модели."""
    model = model or "deepseek-v4-flash"
    if model in OTHER_PRICES:
        return OTHER_PRICES[model]
    if not ts or ts[:10] < NEW_PRICES_FROM:
        return OLD_PRICES.get(model, OLD_PRICES["deepseek-v4-flash"])
    table = PRICES.get(model, PRICES["deepseek-v4-flash"])
    try:
        # Записи журнала — местное время машины (UTC+3), приводим к UTC.
        hour = (int(ts[11:13]) - 3) % 24
    except Exception:
        return table["off"]
    peak = (1 <= hour < 4) or (6 <= hour < 10)
    return table["peak"] if peak else table["off"]
LOG = ROOT / "data" / "usage-log.jsonl"


def spend():
    """Расход за месяц и за сегодня, плюс разбивка по задачам за сегодня."""
    today = date.today().isoformat()
    month = today[:7]
    m_total = d_total = 0.0
    by_agent = collections.Counter()
    if not LOG.exists():
        return 0.0, 0.0, by_agent
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = r.get("ts", "")
        p = price_for(r.get("model"), ts)
        c = (r.get("cache_hit", 0) * p["h"] + r.get("cache_miss", 0) * p["m"]
             + r.get("completion", 0) * p["o"]) / 1e6
        if ts[:10] >= BUDGET_START:
            m_total += c
        if ts[:10] == today:
            d_total += c
            by_agent[r.get("agent", "?")] += c
    return m_total, d_total, by_agent


def verdict(need=0.0):
    """(можно, причина). need — сколько примерно собираемся потратить."""
    m, d, _ = spend()
    if m + need > MONTH_CAP:
        return False, (f"месячный потолок: потрачено ${m:.2f} из ${MONTH_CAP:.0f}"
                       + (f", запрошено ещё ${need:.2f}" if need else ""))
    if d + need > DAY_CAP:
        return False, (f"дневной предел: сегодня ${d:.2f} из ${DAY_CAP:.2f}"
                       + (f", запрошено ещё ${need:.2f}" if need else ""))
    if need > RUN_CAP:
        return False, f"один прогон на ${need:.2f} — больше предохранителя ${RUN_CAP:.0f}"
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="код 1, если запускать нельзя")
    ap.add_argument("--room", type=float, default=0.0, help="хватит ли ещё на эту сумму")
    args = ap.parse_args()

    m, d, by = spend()
    ok, why = verdict(args.room)

    print(f"месяц:   ${m:>7.2f} из ${MONTH_CAP:.0f}   осталось ${MONTH_CAP - m:.2f}")
    print(f"сегодня: ${d:>7.2f} из ${DAY_CAP:.2f}")
    if by:
        print("на что сегодня:")
        for a, v in by.most_common(5):
            print(f"   {a:18} ${v:.3f}")
    if not ok:
        print(f"\n⛔ НЕ ЗАПУСКАТЬ: {why}")
        return 1 if args.check else 0
    if args.check or args.room:
        print(f"\n✅ можно{f' (запас ${MONTH_CAP - m:.2f})' if not args.room else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

def spend_by_line():
    """Расход месяца, разнесённый по строкам бюджета (data/budget.json).

    Зачем отдельно от spend(). Потолок месяца — 200, но на статьи из них выделено 130:
    остальное это машина открытий, Cloudflare и резерв. Отчёт в канале считал остаток от
    ВСЕХ денег месяца и обещал «ещё 3230 статей» — вдвое больше, чем на самом деле
    оплачено (владелец 2026-08-08: «на статьи там выделено не 200, а 130»). Та же ошибка
    уже ловилась в бюджетном файле для людей; в ежедневный отчёт правка не доехала.

    Возвращает {имя строки: {"план", "потрачено", "остаток"}}.
    """
    cfg_p = ROOT / "data" / "budget.json"
    try:
        cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    today = date.today().isoformat()
    month = today[:7]
    by_agent = collections.Counter()
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ts", "")[:10] < BUDGET_START:
                continue
            p = price_for(r.get("model"), r.get("ts", ""))
            c = (r.get("cache_hit", 0) * p["h"] + r.get("cache_miss", 0) * p["m"]
                 + r.get("completion", 0) * p["o"]) / 1e6
            by_agent[r.get("agent", "?")] += c

    out = {}
    for row in cfg.get("строки", []):
        name = row.get("имя", "?")
        plan = float(row.get("план", 0))
        used = sum(by_agent[a] for a in row.get("агенты", []) or [])
        # Фиксированная плата списывается целиком в начале месяца, а не по журналу вызовов.
        if row.get("фикс"):
            used = plan
        used += float(row.get("вручную", 0) or 0)
        out[name] = {"план": plan, "потрачено": used, "остаток": max(0.0, plan - used)}
    return out
