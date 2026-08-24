#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полный отчёт за сутки в канал: что сделано, чего стоило, что требует решения.

Владелец 2026-08-19: «в ежедневный отчёт в канал… он видимо вечером и не полный день.
Данные лучше формировать полный отчёт за вчера: что сделано, какие проблемы, сколько
потрачено, сколько статей сделано по классам — экспресс, полные, с разбором машиной,
что нового по каким разделам, какие-то общие метрики, чтобы сразу посмотрел, и вся
информация, что требует внимания от нас: деньги куда класть, какие вопросы открыты,
незавершёнка… напоминалка по голосованию, если были сообщения на почту — тоже, здоровье
сервисов. Не перебарщивай».

ПОЧЕМУ ЗА ВЧЕРА, А НЕ ЗА СЕГОДНЯ. Прежний вечерний статус показывал незакрытые сутки:
ночной прогон в них ещё не попал, утренний уже попал — сравнивать такие отчёты между
собой нельзя. Отчёт за полные вчерашние сутки сопоставим с любым другим днём.

ЧТО СЧИТАЕТСЯ ФАКТОМ. Каждое число берётся из своего источника и не выводится «примерно»:
статьи — из архива по дате папки, деньги — из журнала вызовов модели по ценам того часа,
сбои — из журналов прогонов, вопросы совета — из повестки, письма — из состояния сторожа
почты. Чего нет, о том молчим: пустой раздел не печатается вовсе (владелец: «если не было
— не надо»).

    python tools/daily_report.py                 отчёт за вчера, показать
    python tools/daily_report.py --send          отчёт за вчера в канал
    python tools/daily_report.py --day 2026-08-18 --send
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def esc(s):
    return (str(s) or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Статьи ────────────────────────────────────────────────────────────────────
def articles(day):
    """Что появилось за день: по классам, разделам и с машиной знаний."""
    folder = ROOT / "lang/ru/archive" / day
    out = {"express": 0, "full": 0, "km": 0, "cats": Counter(), "titles": []}
    if not folder.exists():
        return out
    for p in folder.glob("*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("express"):
            out["express"] += 1
        else:
            out["full"] += 1
        if (d.get("recommend") or {}).get("ru"):
            out["km"] += 1
        for c in (d.get("categories") or [])[:2]:
            out["cats"][c.split(".")[0]] += 1
        t = ((d.get("popular") or {}).get("ru") or {}).get("title")
        if t and len(out["titles"]) < 3:
            out["titles"].append(t)
    return out


# ── Деньги ────────────────────────────────────────────────────────────────────
def spend(day):
    """Расход за день по видам работ — по ценам того часа, когда вызов случился."""
    try:
        from tools.budget_guard import price_for
    except Exception:
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            from budget_guard import price_for
        except Exception:
            return 0.0, Counter()
    total, by_agent = 0.0, Counter()
    log = ROOT / "data" / "usage-log.jsonl"
    if not log.exists():
        return 0.0, by_agent
    with log.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except Exception:
                continue
            ts = r.get("ts", "")
            if not ts.startswith(day):
                continue
            p = price_for(r.get("model"), ts)
            # Ключи тарифа: h — попадание в кэш, m — промах, o — выход. Первая версия
            # считала по выдуманным «in/out» и показывала $0.00 за день, когда денег
            # ушло на несколько долларов. Молчаливый ноль в отчёте о деньгах опаснее
            # отсутствия отчёта: он выглядит как хорошая новость.
            cost = (r.get("cache_hit", 0) * p["h"] + r.get("cache_miss", 0) * p["m"]
                    + r.get("completion", 0) * p["o"]) / 1_000_000
            total += cost
            by_agent[r.get("agent") or "прочее"] += cost
    return total, by_agent


# ── Сбои ──────────────────────────────────────────────────────────────────────
# Настоящий сбой, а не предупреждение. Первый прогон отчёта показал, как важна разница:
# в «сбои» попали «во время заливки успели измениться 20 файлов» (штатное поведение),
# «идёт пересборка» (защита от гонки сработала как надо), «arXiv retry 1/3» (сеть моргнула
# и восстановилась) и даже сообщение о лицензии NC-ND. Отчёт, где каждый день шесть
# «сбоев», перестают читать через неделю.
_BAD = re.compile(r"traceback|❌|не уложил|споткн|failed|exit code [1-9]|"
                  r"critical|отказ|не записал|не отправ", re.I)
_NOT_BAD = re.compile(r"retry \d|успели измениться|идёт пересборка|только собственный разбор|"
                      r"пропускаю|уже есть", re.I)


def failures(day):
    """Строки о сбоях из журналов прогонов за этот день. Только суть, без простыней."""
    out = []
    logs = ROOT / "logs"
    if not logs.exists():
        return out
    stamp = day.replace("-", "")
    for f in sorted(logs.glob("*.log")) + sorted(logs.glob("*.err")):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime).date().isoformat() != day \
               and stamp not in f.name:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            if _BAD.search(line) and not _NOT_BAD.search(line) and len(line.strip()) > 12:
                out.append(f"{f.name}: {line.strip()[:150]}")
                break                     # по одной строке с файла: остальное в самом логе
    return out[:6]


# ── Совет ─────────────────────────────────────────────────────────────────────
def council():
    """Ближайшее заседание и сколько вопросов ждёт голоса."""
    p = ROOT / "data" / "council" / "upcoming.json"
    if not p.exists():
        # Повестки лежат по датам: берём ближайшую будущую.
        files = sorted((ROOT / "data" / "council").glob("20*.json"))
        today = date.today().isoformat()
        future = [f for f in files if f.stem >= today]
        if not future:
            return None
        p = future[0]
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    items = d.get("items") or d.get("questions") or []
    return {"date": d.get("date") or p.stem, "n": len(items)}


# ── Почта ─────────────────────────────────────────────────────────────────────
def mail(day):
    """Сколько писем сторож почты обработал за день. Нет писем — нет раздела."""
    p = ROOT / "data" / "mail-state.json"
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return 0
    seen = d.get("seen") or d.get("handled") or {}
    if isinstance(seen, dict):
        return sum(1 for v in seen.values() if str(v).startswith(day))
    return 0


# ── Здоровье сервисов ─────────────────────────────────────────────────────────
def services():
    """Что запускается по расписанию и когда отработало в последний раз."""
    out = []
    try:
        r = subprocess.run(["schtasks", "/query", "/fo", "csv", "/nh"],
                           capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        for line in (r.stdout or "").splitlines():
            if "b42" not in line.lower():
                continue
            parts = [x.strip('"') for x in line.split('","')]
            if len(parts) >= 3:
                name = parts[0].split("\\")[-1]
                out.append((name, parts[2]))
    except Exception:
        pass
    return out[:8]


def pending():
    """Открытые вопросы из незавершёнки: только заголовки разделов, требующих решения."""
    p = ROOT / "НЕЗАВЕРШЁНКА.md"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    block = text.split("## Требует решения владельца", 1)
    if len(block) < 2:
        return []
    rows = []
    for line in block[1].splitlines():
        if line.startswith("| `"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                rows.append((cells[0].strip("`"), cells[1]))
        if line.startswith("## "):
            break
    return rows[:6]



# ── Посещения ─────────────────────────────────────────────────────────────────
def visits(day):
    """Читатели за день: люди, страницы, визиты и возвраты.

    Источник — наш же счётчик в D1 через ручку /api/stats: она считает по событиям
    просмотра с флагом dev=0, то есть без нашей собственной возни с тестами. Владелец
    отдельно просил показывать посещения в отчёте — без них картина дня неполная:
    видно, сколько мы сделали, и не видно, читал ли это кто-нибудь.
    """
    try:
        import requests
        s = requests.get("https://bridge42worlds.academy/api/stats?days=30",
                         timeout=25).json()
    except Exception:
        return None
    days = s.get("byDay") or []
    row = next((d for d in days if str(d.get("day", "")).startswith(day)), None)
    t = s.get("totals") or {}
    return {"uniq": (row or {}).get("uniq", 0), "views": (row or {}).get("views", 0),
            "m_uniq": t.get("uniq", 0), "m_views": t.get("n", 0),
            "visits": t.get("visits", 0), "returning": s.get("returning", 0)}


# ── Деньги на счетах ──────────────────────────────────────────────────────────
def balances():
    """Сколько осталось на счетах. Владелец просил: «деньги, куда класть»."""
    out = {}
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from deepseek_balance import balance as ds_balance
        v = ds_balance()
        if isinstance(v, (int, float)):
            out["DeepSeek"] = float(v)
        elif isinstance(v, dict):
            out["DeepSeek"] = float(v.get("total") or v.get("balance") or 0)
    except Exception:
        pass
    return out


# ── Общие метрики ─────────────────────────────────────────────────────────────
def totals():
    """Размер проекта одной строкой: сколько всего статей, понятий, авторов."""
    arch = ROOT / "lang/ru/archive"
    n_art = sum(1 for _ in arch.glob("*/*/data.json")) if arch.exists() else 0
    n_con = 0
    try:
        n_con = len(json.loads((ROOT / "data/concepts.json").read_text(
            encoding="utf-8"))["concepts"])
    except Exception:
        pass
    n_auth = 0
    try:
        n_auth = len(json.loads((ROOT / "data/author-records.json").read_text(
            encoding="utf-8")))
    except Exception:
        pass
    return {"articles": n_art, "concepts": n_con, "authors": n_auth}


def week_block(day):
    """Агрегат за неделю — по понедельникам (владелец 2026-08-24: «агрегацию
    выполненного пишем за неделю, а не месяц, бюджет тоже на неделю по сервисам»).
    Неделя — семь дней, кончая отчётным воскресеньем; отчёт за него приходит в пн 04:00."""
    d0 = date.fromisoformat(day)
    if d0.weekday() != 6:
        return []
    days = [(d0 - timedelta(days=i)).isoformat() for i in range(7)]
    n_full = n_exp = 0
    for dd in days:
        a = articles(dd)
        n_full += a["full"]
        n_exp += a["express"]
    w_total, w_agent = 0.0, Counter()
    for dd in days:
        t, ba = spend(dd)
        w_total += t
        for k, v in ba.items():
            w_agent[k] += v
    head = f"\n📅 <b>Неделя {days[-1]} — {days[0]}</b>"
    body = (f"Статей: {n_full + n_exp} (полных {n_full}, экспрессов {n_exp}). "
            f"Бюджет недели: ${w_total:.2f}.")
    L = [head, body]
    if w_agent:
        L.append("По сервисам: " + " · ".join(
            f"{k} ${v:.2f}" for k, v in w_agent.most_common(6) if v >= 0.01))
    return L


def build(day):
    a = articles(day)
    total, by_agent = spend(day)
    fails = failures(day)
    c = council()
    letters = mail(day)
    svc = services()
    open_q = pending()

    L = [f"📋 <b>Отчёт за {day}</b>"]

    L.append(f"\n📚 <b>Статьи</b>: {a['full'] + a['express']}"
             + (f" · полных {a['full']}" if a["full"] else "")
             + (f" · экспрессов {a['express']}" if a["express"] else "")
             + (f" · с машиной знаний {a['km']}" if a["km"] else ""))
    if a["cats"]:
        L.append("Разделы: " + " · ".join(f"{k} {v}" for k, v in a["cats"].most_common(5)))
    for t in a["titles"]:
        L.append(f"  · {esc(t)[:80]}")

    v = visits(day)
    if v:
        L.append(f"\n👥 <b>Читатели</b>: за день {v['uniq']} человек, {v['views']} страниц."
                 f"\nЗа 30 дней: {v['m_uniq']} человек, {v['m_views']} страниц, "
                 f"{v['visits']} визитов, вернувшихся {v['returning']}.")

    tt = totals()
    L.append(f"\n📊 <b>Всего</b>: статей {tt['articles']}, понятий {tt['concepts']}, "
             f"авторов в карточках {tt['authors']}")

    L.append(f"\n💰 <b>Потрачено</b>: ${total:.2f}")
    if by_agent:
        L.append("  " + " · ".join(f"{k} ${v:.2f}" for k, v in by_agent.most_common(4)
                                   if v >= 0.005))

    bal = balances()
    if bal:
        # Порог тревоги: ниже трёх долларов прогон уже не влезает целиком, и лучше
        # узнать об этом утром за чаем, чем в момент, когда фабрика встала.
        line = " · ".join(f"{k} ${v:.2f}" for k, v in bal.items())
        low = [k for k, val in bal.items() if val < 3]
        L.append(f"\n🏦 <b>На счетах</b>: {line}"
                 + (f"\n❗ Пора пополнить: {', '.join(low)}" if low else ""))

    if fails:
        L.append("\n⚠️ <b>Сбои</b>")
        for f in fails:
            L.append(f"  · {esc(f)}")

    if letters:
        L.append(f"\n✉️ <b>Письма</b>: {letters} обработано сторожем")

    if c and c["n"]:
        L.append(f"\n🗳 <b>Совет</b>: заседание {c['date']}, вопросов {c['n']} — голоса ждут")

    if svc:
        bad = [f"{n}: {s}" for n, s in svc if s.lower() not in ("готово", "ready", "running")]
        L.append(f"\n🔧 <b>Сервисы</b>: {len(svc)} задач в расписании"
                 + (f", требуют внимания: {', '.join(bad[:3])}" if bad else ", все в норме"))

    L.extend(week_block(day))

    if open_q:
        L.append("\n❓ <b>Ждёт твоего решения</b>")
        for name, what in open_q:
            L.append(f"  · <b>{esc(name)}</b> — {esc(what)[:90]}")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", help="YYYY-MM-DD, по умолчанию вчера")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()
    day = args.day or (date.today() - timedelta(days=1)).isoformat()
    text = build(day)
    print(text)
    if args.send:
        subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"), text],
                       cwd=str(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
