#!/usr/bin/env python3
"""Фабрика: один ночной прогон, который сам решает, что делать сегодня, и укладывается
в деньги, которые реально есть на счету.

Владелец 12 августа, дословно о порядке работ: «всё должно быть автоматически
запланировано и реализовываться в соответствии с бюджетом, который есть на DeepSeek.
Приоритет такой: текущие дни экспресс, если не добрали от последней даты, используя
векторную технику; затем идентификация тех статей, что должны быть сделаны или
доработаны до полной — опять же определяется вектором, с советами по развитию; затем
доработка советов для всех текущих статей, которые полные; для статей автор может
заказать разработку или кто угодно кнопку „предложить наш разбор“. То есть автомат
должен сам всё единообразно наполнять».

ЗАЧЕМ ОТДЕЛЬНЫЙ ОРКЕСТРАТОР, КОГДА ЕСТЬ ТРИ ЗАДАЧИ ПЛАНИРОВЩИКА. Потому что они не
знают друг о друге и не знают о деньгах. `daily` берёт 25 статей независимо от того,
осталось ли на счету три доллара или три цента; `upkeep` следом тратит ещё; порядок
между ними держится только тем, в какие часы их поставили. Пока денег было много, это
не мешало. 12 августа на счету осталось $1.62 — меньше суток работы, — и стало видно:
решать, ЧТО делать сегодня, должен кто-то один, у кого перед глазами и остаток, и
список работ по важности.

ЧЕМ РУКОВОДСТВУЕТСЯ. Двумя числами: дневным потолком владельца (4–5 долларов) и живым
остатком на счету DeepSeek. Берём меньшее и оставляем неприкосновенный запас: прогон,
который выбирает счёт в ноль, останавливает и сторожа почты, и заказы читателей.

    python tools/factory.py --plan     показать план на сегодня и цену, ничего не делая
    python tools/factory.py            выполнить
    python tools/factory.py --only advise    один шаг
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from dotenv import load_dotenv                                       # noqa: E402

load_dotenv(ROOT / ".env")

LOGS = ROOT / "logs"
STATE = ROOT / "data" / "factory-state.json"

# Неприкосновенный запас на счету. Ниже него не тратим ничего: заказ читателя, письмо
# автора и перевод статьи должны сработать даже в день, когда фабрика решила отдохнуть.
RESERVE = 0.50

# Замеры себестоимости по журналу, 11–12 августа. Не «прайс», а то, во что реально
# обходится работа со всеми переводами и попаданиями в кэш.
# Периметр разделов — тот же, что был у daily и overnight. Передавать ОБЯЗАТЕЛЬНО: без
# --category генератор подставляет "astro-ph.*", и лента набирается из одной астрофизики.
# С отключением старых задач фабрика осталась единственным источником свежих статей, и
# эта тихая подстановка стоила бы нам всей широты корпуса.
CATEGORIES = ("astro-ph.*,gr-qc,hep-th,hep-ph,hep-ex,nucl-th,nucl-ex,quant-ph,"
              "cond-mat.*,physics.*,q-bio.*,math-ph,math.*,cs.LG")

COST = {
    "express": 0.0074,     # статья экспрессом на пяти языках
    "full": 0.075,         # полный разбор
    "advise": 0.006,       # раздел «Взгляд машины знаний» + четыре перевода
    "research": 0.010,     # карточка в разделе «Что исследовать» + переводы
    "bush": 0.0009,        # поиск куста в поле (эмбеддинги кандидатов)
}


def balance():
    """Живой остаток на счету DeepSeek. None, если спросить не удалось."""
    import requests
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        r = requests.get("https://api.deepseek.com/user/balance",
                         headers={"Authorization": f"Bearer {key}"}, timeout=20)
        usd = next((b for b in (r.json().get("balance_infos") or [])
                    if b.get("currency") == "USD"), None)
        return float(usd["total_balance"]) if usd else None
    except Exception:
        return None


def spent_today():
    try:
        import budget_guard as bg
        _month, today, _by = bg.spend()
        return today
    except Exception:
        return 0.0


def day_cap():
    try:
        import budget_guard as bg
        return float(bg.DAY_CAP)
    except Exception:
        return 4.0


def purse():
    """Сколько можно потратить этим прогоном. Меньшее из трёх, а не любимое."""
    left_day = max(0.0, day_cap() - spent_today())
    bal = balance()
    left_acc = max(0.0, (bal - RESERVE)) if bal is not None else left_day
    return min(left_day, left_acc), bal, left_day


def uncovered_days(back=10):
    """Дни, за которые статей нет или почти нет.

    Смотрим назад от вчера: сегодняшний день arXiv ещё не закрыт, и требовать от него
    статей — значит каждый прогон объявлять дыру там, где её нет.
    """
    have = {}
    for p in (ROOT / "lang" / "ru" / "archive").glob("*"):
        if p.is_dir():
            have[p.name] = sum(1 for _ in p.glob("*/data.json"))
    out = []
    for i in range(1, back + 1):
        d = (date.today() - timedelta(days=i)).isoformat()
        n = have.get(d, 0)
        if n < 5:
            out.append((d, n))
    return out


def upgrade_candidates(limit=3):
    """Кого дорастить до полного разбора. Выбирает ВЕКТОР, а не наше настроение.

    Владелец: «идентификация тех статей, что должны быть сделаны или доработаны до полной,
    определяется вектором». Признак простой и проверяемый: экспресс, вокруг которого в
    нашем архиве уже собралось несколько работ. Плотное окружение значит, что тема у нас
    живая и полный разбор ляжет не в пустоту, а в середину складывающейся линии.

    Прежний механизм (`tools/upgrade_queue.py`) отбирал по посещаемости и по файлу
    `data/diamonds.json` — файла нет и никто его не пишет, а посещаемости у нас 100
    человек в месяц. Очередь пуста с 4 августа. Вектор в этих условиях — единственный
    сигнал, который у нас действительно есть.
    """
    try:
        import recommend as _rec
    except Exception:
        return []
    rows = []
    for p in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json"), reverse=True):
        if len(rows) >= limit * 8:
            break
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("express") or d.get("upgraded"):
            continue
        pop = (d.get("popular") or {}).get("ru") or {}
        seed = f"{pop.get('title', '')}. {d.get('abstract_orig', '')}"[:1500]
        if len(seed) < 120:
            continue
        rows.append({"id": p.parent.name, "seed": seed, "title": pop.get("title", "")})
    out = []
    for r in rows[:limit * 4]:
        nb = _rec.find_neighbours(r["seed"])
        near = [n for n in nb if (n.get("score") or 0) >= _rec.FRONTIER_NEAR]
        if len(near) >= 3:
            r["near"] = len(near)
            r["nearest"] = round(max(n["score"] for n in near), 3)
            out.append(r)
        if len(out) >= limit:
            break
    out.sort(key=lambda r: (-r["near"], -r["nearest"]))
    return out


def counts():
    """Что у нас есть прямо сейчас — по данным, а не по памяти."""
    full = expr = advised = 0
    for p in (ROOT / "lang" / "ru" / "archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("express"):
            expr += 1
        else:
            full += 1
            if (d.get("recommend") or {}).get("ru"):
                advised += 1
    return {"полных": full, "экспрессов": expr, "с советами": advised,
            "полных без советов": full - advised}


def run(cmd, log=None, timeout=7200):
    """Шаг фабрики — отдельным процессом. Падение шага не роняет прогон: следующий по
    важности должен получить свои деньги, даже если предыдущий споткнулся.

    Вывод шага идёт в НАШ же поток, а не в отдельно открытый файл. Обёртка factory.cmd
    уже перенаправляет всё в лог дня, и попытка открыть тот же файл вторым дескриптором
    на Windows кончается PermissionError — ровно этим первый же запуск по расписанию
    и завершился, не сделав ни шага.
    """
    print(f"\n=== {datetime.now():%H:%M} {' '.join(cmd[1:])}", flush=True)
    sys.stdout.flush()
    try:
        r = subprocess.run(cmd, cwd=ROOT, timeout=timeout,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8",
                                "PYTHONUNBUFFERED": "1"})
        return r.returncode
    except subprocess.TimeoutExpired:
        print("⏱️ шаг не уложился в отведённое время", flush=True)
        return -1


def plan(money):
    """План на сегодня: что делать и в каком порядке. Порядок задан владельцем.

    Доли не равные и не случайные. Свежая лента — то, ради чего сайт существует, ей
    больше половины. Советы дёшевы (полцента) и закрывают накопленный долг — им хватает
    малой доли. Полные разборы дороги в десять раз, поэтому идут по остатку и по одному.
    """
    c = counts()
    gaps = uncovered_days()
    steps = []

    # 1. Свежая лента: добрать дни, где статей нет или почти нет.
    if gaps and money > COST["express"] * 5:
        share = money * 0.55
        n = int(share / COST["express"])
        steps.append({"key": "days", "title": "добрать непокрытые дни экспрессом",
                      "days": gaps[:3], "n": max(5, min(n, 60)),
                      "cost": min(share, COST["express"] * min(n, 60))})

    # 2. Советы всем полным, у кого их ещё нет: дёшево и закрывает долг.
    if c["полных без советов"] > 0 and money > COST["advise"] * 5:
        n = min(c["полных без советов"], int(money * 0.20 / COST["advise"]))
        if n >= 5:
            steps.append({"key": "advise", "title": "советы полным разборам без раздела",
                          "n": n, "cost": n * COST["advise"]})

    # 2b. Доращивание до полного разбора: самое дорогое, поэтому по одной-две штуки
    #     и только если после свежей ленты и советов ещё остались деньги.
    ups = upgrade_candidates(3)
    if ups and money > COST["full"] * 1.5:
        n = max(1, min(len(ups), int(money * 0.15 / COST["full"])))
        steps.append({"key": "upgrade", "title": "дорастить экспресс до полного разбора",
                      "ids": [u["id"] for u in ups[:n]], "n": n, "cost": n * COST["full"]})

    # 3. Раздел «Что исследовать» — витрина смысла всей работы.
    if money > COST["research"] * 3:
        n = max(2, min(6, int(money * 0.10 / COST["research"])))
        steps.append({"key": "research", "title": "пополнить «Что исследовать»",
                      "n": n, "cost": n * COST["research"]})

    # 4. Заказы читателей — по кнопке «предложить наш разбор». Их немного, но они
    #    важнее плановой работы: человек ждёт ответа.
    steps.insert(0, {"key": "orders", "title": "заказы читателей", "n": 0, "cost": 0.0})

    # 5. Бесплатные работы. Идут ВСЕГДА, даже когда на счету ноль — в этом и смысл:
    #    владелец 12 августа сказал «даже если доллар, всё равно ежедневно можно что-то
    #    генерить: и статьи, и исследования, и анализ». Модель здесь не зовётся ни разу,
    #    считается по уже накопленным данным.
    steps += [
        {"key": "points", "title": "пересчёт точек схождения", "n": 0, "cost": 0.0},
        {"key": "analytics", "title": "карта аналитики", "n": 0, "cost": 0.0},
        {"key": "graph", "title": "граф знаний", "n": 0, "cost": 0.0},
        {"key": "status", "title": "дашборд", "n": 0, "cost": 0.0},
    ]
    return steps, c, gaps


def show_plan():
    money, bal, left_day = purse()
    steps, c, gaps = plan(money)
    print(f"\n💳 на счету DeepSeek: {'—' if bal is None else f'${bal:.2f}'}"
          f" · дневной остаток ${left_day:.2f} · к работе ${money:.2f}")
    print(f"📦 в архиве: {c['полных']} полных, {c['экспрессов']} экспрессов, "
          f"{c['с советами']} с советами (долг {c['полных без советов']})")
    if gaps:
        print(f"📅 тощие дни: {', '.join(f'{d} ({n})' for d, n in gaps[:6])}")
    else:
        print("📅 дни закрыты")
    print("\nПЛАН:")
    total = 0.0
    for s in steps:
        total += s["cost"]
        print(f"  {s['key']:9} {s['title']:44} "
              f"{'—' if not s['n'] else s['n']:>4}  ~${s['cost']:.2f}")
    print(f"  {'ИТОГО':9} {'':44} {'':>4}  ~${total:.2f}")
    if money < 0.05:
        print("\n🔴 денег нет — прогон только пересоберёт сайт и отчитается")
    return steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="показать план и выйти")
    ap.add_argument("--only", help="выполнить один шаг: days/advise/research/orders")
    ap.add_argument("--no-publish", action="store_true", help="не пересобирать и не выкладывать")
    args = ap.parse_args()

    if args.plan:
        show_plan()
        return 0

    steps = show_plan()
    if args.only:
        steps = [s for s in steps if s["key"] == args.only]
        if not steps:
            print(f"шаг «{args.only}» сегодня не запланирован")
            return 0

    # Расход на входе — чтобы в отчёте назвать цену ИМЕННО этого прогона, а не всего дня.
    started_spent = spent_today()
    print("\n▶️ работаем")
    done = []
    for s in steps:
        money, _bal, _ = purse()
        if s["cost"] > 0 and money < s["cost"] * 0.5:
            print(f"  ⏭️ {s['key']}: денег осталось ${money:.2f} — пропускаю")
            continue
        rc = do_step(s)
        done.append((s["key"], rc))

    if not args.no_publish:
        print("\n▶️ пересборка и выкладка")
        rc = run([sys.executable, "run.py", "html"], timeout=21600)
        done.append(("publish", rc))
        run([sys.executable, "tools/stats_refresh.py"], timeout=1800)

    STATE.parent.mkdir(exist_ok=True)
    spent = max(0.0, spent_today() - started_spent)
    STATE.write_text(json.dumps({"когда": datetime.now().isoformat(timespec="minutes"),
                                 "шаги": done, "потрачено": round(spent, 3),
                                 "план": [s["key"] for s in steps]},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [k for k, rc in done if rc not in (0, None)]
    print(f"\n{'⚠️' if bad else '✅'} готово: {', '.join(k for k, _ in done)}"
          + (f" · споткнулись: {', '.join(bad)}" if bad else ""))
    report(done, bad, spent)
    return 0


# Человеческие названия шагов для отчёта: в канал уходит не «advise», а то, что реально
# сделано. Владелец 12 августа: «пиши лог, что сделано — даже если доллар, всё равно
# ежедневно можно что-то генерить».
STEP_NAMES = {
    "orders": "заказы читателей", "days": "статьи за непокрытые дни",
    "advise": "советы авторам", "upgrade": "доращивание до полного разбора",
    "research": "направления «Что исследовать»", "points": "точки схождения",
    "analytics": "карта аналитики", "graph": "граф знаний", "status": "дашборд",
    "publish": "пересборка и выкладка",
}


def report(done, bad, spent):
    """Одно сообщение в канал: что фабрика сделала сегодня и во что это обошлось.

    Без него прогон бессловесен: лог лежит в файле, который никто не открывает, а о
    работе конвейера владелец узнаёт по тому, появились ли новые статьи. Отчёт уходит
    в любом случае — «денег не было, сделали бесплатное» это тоже новость, и хорошая:
    значит автомат жив.

    Текст передаём ФАЙЛОМ, а не аргументом: консоль Windows отдаёт аргументы в OEM-
    кодировке, и русские слова уже приезжали в канал кракозябрами (владелец поймал
    это 4 августа).
    """
    ok = [STEP_NAMES.get(k, k) for k, rc in done if rc in (0, None)]
    fail = [STEP_NAMES.get(k, k) for k in bad]
    bal = balance()
    lines = ["🏭 <b>Фабрика отработала</b>",
             "Сделано: " + (", ".join(ok) if ok else "ничего")]
    if fail:
        lines.append("⚠️ Споткнулись: " + ", ".join(fail))
    lines.append(f"Потрачено за прогон: ${spent:.2f}"
                 + (f" · на счету осталось ${bal:.2f}" if bal is not None else ""))
    if bal is not None and bal < 1.0:
        lines.append("🔴 Денег почти нет. Завтра фабрика сделает бесплатное: аналитику, "
                     "граф, дашборд и точки схождения — конвейер не встанет.")
    try:
        msg = LOGS / "factory-report.txt"
        msg.write_text("\n".join(lines), encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"),
                        "--file", str(msg)], cwd=ROOT, timeout=120,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except Exception as ex:
        print(f"⚠️ отчёт в канал не ушёл: {type(ex).__name__}")


def do_step(s):
    """Один шаг фабрики. Каждый — существующий инструмент, а не новая логика."""
    k = s["key"]
    if k == "orders":
        # Без флагов = ровно один проход по очереди (queue_worker.__main__): --loop
        # крутится вечно, --dry ничего не делает. Флага --once там нет и не было.
        return run([sys.executable, "cloudflare/queue_worker.py"], timeout=3600)
    if k == "days":
        rc = 0
        for d, _n in s["days"]:
            rc = run([sys.executable, "run.py", "range", "--from", d, "--to", d,
                      "--express", "--limit", str(max(5, s["n"] // max(1, len(s["days"])))),
                      "--category", CATEGORIES],
                     timeout=7200) or rc
        return rc
    if k == "upgrade":
        # Доращиваем экспресс до полного разбора. B42_NO_PUBLISH=1 — иначе run.py regen
        # публикует сайт после КАЖДОЙ статьи: пять апгрейдов это пять полных выкаток
        # в R2 подряд. Выкладка одна, в конце прогона.
        rc = 0
        for aid in s.get("ids", []):
            rc = run([sys.executable, "run.py", "regen", aid], timeout=5400) or rc
        return rc
    if k == "advise":
        return run([sys.executable, "tools/recommend.py", "--all-full",
                    "--limit", str(s["n"])], timeout=10800)
    if k == "research":
        return run([sys.executable, "tools/research.py", "--build", str(s["n"])],
                   timeout=7200)
    if k == "points":
        # Сгущения направлений: где советы РАЗНЫМ авторам легли рядом. Считается по
        # готовым текстам, стоит доли цента на эмбеддингах и кэшируется по отпечатку.
        return run([sys.executable, "special_points.py"], timeout=3600)
    if k == "analytics":
        # Без --interpret: имена кластерам даёт модель, а это уже платно. Сама карта
        # (кластеры, оси, со-встречаемость) считается локально и бесплатно.
        rc = run([sys.executable, "run.py", "analytics"], timeout=7200)
        # Карта мира — вторая вкладка аналитики: координаты задаёт поле arXiv, а не наши
        # теги. Пересчёт областей делает ML своим инструментом; здесь только перекладка
        # готового в формат страницы, поэтому шаг ничего не стоит и не требует их запуска.
        rc = run([sys.executable, "tools/world_map_view.py"], timeout=1800) or rc
        return rc
    if k == "graph":
        return run([sys.executable, "run.py", "graph"], timeout=3600)
    if k == "status":
        rc = run([sys.executable, "run.py", "status"], timeout=1800)
        # Лёгкие справочники для браузера (имя + описание подсказки). Пересобираются из
        # полных: разойдутся — читатель увидит старое название тега на карточке.
        rc = run([sys.executable, "tools/lite_refs.py"], timeout=1800) or rc
        return rc
    print(f"  ⚠️ шаг {k} пока не реализован")
    return None


if __name__ == "__main__":
    sys.exit(main())
