"""Пересчёт витринных метрик и отчёт в канал — раз в 8 часов, задачей планировщика.

Владелец 2026-08-06: «сделай, чтобы мы видели и обновлялось каждые 8 часов» и «пиши в чат
наш, у нас же уговор — что сделано, что происходит».

Что здесь чинится. Сводка на сайте собирается из шести источников. Один живой — /api/stats,
он спрашивает базу при каждом открытии страницы. Остальные пять — файлы, которые
пересчитываются ТОЛЬКО при полной пересборке сайта. Между пересборками они молча стареют:
покрытие arXiv, полнота языков, расходы, дата сборки. Раз в сутки лента добавляет статьи,
а витрина об этом узнаёт через раз.

Этот прогон дешёвый: ни одного обращения к модели, только пересчёт по локальным данным
и выкладка нескольких файлов. Поэтому его можно гонять часто.

    python tools/stats_refresh.py            пересчитать, выложить, написать в канал
    python tools/stats_refresh.py --quiet    без сообщения в канал
    python tools/stats_refresh.py --dry      только показать, что получилось бы
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent

# Каждый пересчитывает свой файл витрины. Порядок не важен, зависимостей между ними нет.
STEPS = [
    ("corpus_stats.py", "покрытие arXiv"),
    ("tools/lang_coverage.py", "полнота языков"),
    ("tools/usage_summary.py", "расходы на модель"),
]


def run(script):
    p = ROOT / script
    if not p.exists():
        return None, f"{script} не найден"
    r = subprocess.run([sys.executable, str(p)], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    return r.returncode, (r.stdout or "")[-300:] + (r.stderr or "")[-300:]


def _short_reason(tail):
    """Из хвоста лога — одна человеческая фраза для канала.

    Полный лог в сообщение не вставишь, а код возврата ничего не объясняет. Берём первую
    содержательную строку: скрипты пишут причину первой, а не в конце.
    """
    for line in (tail or "").splitlines():
        s = line.strip().lstrip("⚠️✅❌ ").strip()
        if len(s) > 12 and not s.startswith(("Traceback", "File ")):
            return s[:180]
    return "смотри лог прогона в logs/"


_RUN_FLAG = ROOT / "logs" / ".stats-last-failed"


def _last_run_failed():
    return _RUN_FLAG.exists()


def _remember_run(failed):
    """Помним исход прошлого прогона — только чтобы сказать «а теперь всё хорошо»."""
    try:
        if failed:
            _RUN_FLAG.write_text("1", encoding="utf-8")
        else:
            _RUN_FLAG.unlink(missing_ok=True)
    except Exception:
        pass


def money_line():
    """Расход в пересчёте НА СТАТЬИ — владелец 7 августа: «каждый день в телегу, что
    потратили с точки зрения статей».

    Доллары сами по себе ничего не говорят: $4 это много или мало? А вот «сделали 96
    статей, потратили $3,10, вышло по три цента» — говорит сразу и про объём, и про то,
    не подорожал ли конвейер."""
    import subprocess as sp
    from datetime import date, timedelta
    import glob, os

    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import budget_guard as bg
        month, today, by = bg.spend()
        cap, day_cap = bg.MONTH_CAP, bg.DAY_CAP
    except Exception:
        return ""

    # Статей, созданных сегодня — по времени появления папки, а не по дате arXiv
    t = date.today()
    made_today = sum(1 for d in glob.glob(str(ROOT / "lang/ru/archive/*/*/"))
                     if date.fromtimestamp(os.path.getctime(d)) == t)
    made_month = sum(1 for d in glob.glob(str(ROOT / "lang/ru/archive/*/*/"))
                     if date.fromtimestamp(os.path.getctime(d)) >= t.replace(day=1))

    # Считаем по СТРОКЕ «Статьи», а не по потолку месяца. На статьи выделено 130 из 200 —
    # остальное это машина открытий, Cloudflare и резерв, и на ленту они не идут. Прежний
    # расчёт делил весь остаток месяца на цену статьи и обещал «ещё 3230 статей», хотя
    # оплачено вдвое меньше (владелец 2026-08-08: «на статьи выделено не 200, а 130»).
    # Ровно эта ошибка уже ловилась в бюджетном файле для людей — в ежедневный отчёт
    # правка тогда не доехала.
    lines = bg.spend_by_line() if hasattr(bg, "spend_by_line") else {}
    art = lines.get("Статьи") or {"план": cap, "потрачено": month, "остаток": cap - month}
    art_plan, art_used, art_left = art["план"], art["потрачено"], art["остаток"]

    per_today = f"${today / made_today:.3f}" if made_today else "—"
    per_article = (art_used / made_month) if made_month and art_used else 0
    per_month = f"${per_article:.3f}" if per_article else "—"
    left_articles = int(art_left / per_article) if per_article else 0

    out = ("\n\n💰 <b>Деньги</b>"
           f"\nСегодня: <b>{made_today}</b> статей за <b>${today:.2f}</b> "
           f"(по {per_today} за статью)."
           f"\nСтатьи за месяц: {made_month} штук за ${art_used:.2f} из ${art_plan:.0f}, "
           f"по {per_month}."
           f"\nОстаток на статьи ${art_left:.2f} — это ещё около <b>{left_articles}</b> статей."
           f"\nВесь месяц: ${month:.2f} из ${cap:.0f}.")
    others = [f"{k} ${v['потрачено']:.2f}/${v['план']:.0f}"
              for k, v in lines.items() if k != "Статьи"]
    if others:
        out += "\n" + " · ".join(others)
    if today > day_cap * 0.8:
        out += f"\n🟡 Дневной предел ${day_cap:.2f} почти выбран."
    if art_plan and art_used > art_plan * 0.85:
        out += f"\n🔴 Бюджет статей выбран на {art_used / art_plan * 100:.0f}%."
    out += balances_line(today)
    return out


def balances_line(spent_today=0.0):
    """Сколько реально осталось НА СЧЕТАХ сервисов, а не по нашей бухгалтерии.

    Владелец 12 августа: «остаток ещё на DeepSeek туда, и на других сервисах если есть —
    раз в день всё, что есть». Разница принципиальная: наш журнал считает, сколько мы
    потратили по прайсу, а на счету может лежать меньше — списания идут со скидкой, курс
    и НДС плавают, пополнения делает владелец руками. Конвейер встанет по балансу счёта,
    а не по нашей смете, и узнать об этом лучше из отчёта, чем из отказа генерации.
    """
    import requests
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return ""
    try:
        r = requests.get("https://api.deepseek.com/user/balance",
                         headers={"Authorization": f"Bearer {key}"}, timeout=20)
        j = r.json()
        usd = next((b for b in (j.get("balance_infos") or [])
                    if b.get("currency") == "USD"), None)
        if not usd:
            return ""
        left = float(usd.get("total_balance") or 0)
    except Exception:
        return ""
    line = f"\n💳 На счету DeepSeek: <b>${left:.2f}</b>"
    # Дни жизни считаем по сегодняшнему расходу — он и есть наш нынешний темп.
    if spent_today > 0.05:
        line += f" — при сегодняшнем темпе это ещё около {left / spent_today:.0f} дн."
    if left < 3:
        line += "\n🔴 Меньше трёх долларов: пополнить, иначе конвейер встанет."
    elif left < 8:
        line += "\n🟡 Меньше восьми долларов — пора пополнить."
    return line


def zone_traffic():
    """Статистика на грани сети: запросы, страницы, уникальные адреса за последние дни.

    Берём CLOUDFLARE_DNS_TOKEN, а не рабочий CLOUDFLARE_API_TOKEN. Причина простая и
    проверенная делом 2026-08-06: зонные права (маршруты, аналитика) выданы именно ему,
    а на основной токен они почему-то не сохраняются в панели. Основной умеет аккаунт
    (Worker, R2, D1, KV), этот — зону. Оба нужны, подменять их друг другом нельзя.

    Старый REST-эндпоинт аналитики Cloudflare закрыла («sunset»), поэтому только GraphQL.
    """
    import datetime
    import os

    import requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    tok = os.environ.get("CLOUDFLARE_DNS_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    zone = os.environ.get("CLOUDFLARE_ZONE_ID", "8f69b7580365ef9ceab3d24c5e632bf5")
    if not tok:
        return None
    since = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    q = ("""{ viewer { zones(filter: {zoneTag: "%s"}) {
      httpRequests1dGroups(limit: 3, filter: {date_geq: "%s"}, orderBy: [date_ASC]) {
        dimensions { date } sum { requests pageViews bytes } uniq { uniques } } } } }"""
         % (zone, since))
    try:
        r = requests.post("https://api.cloudflare.com/client/v4/graphql",
                          headers={"Authorization": f"Bearer {tok}"}, json={"query": q}, timeout=40)
        j = r.json()
        if j.get("errors"):
            return None
        return j["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
    except Exception:
        return None


def _genre_mix(idx, days=14):
    """Каких работ мы набрали за последние две недели: измерено, а не на глаз.

    Жанр берём из data/article-kind.json — его размечает article_kind.py по смыслу
    аннотации (эксперимент / теория / методы / обзор). Считаем только свежие статьи:
    старый архив набирался с прежним приоритетом и разбавляет картину так, что новую
    настройку в ней не разглядеть.
    """
    try:
        kinds = json.loads((ROOT / "data" / "article-kind.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    from datetime import date, timedelta
    edge = (date.today() - timedelta(days=days)).isoformat()
    seen = {}
    for a in idx:
        if (a.get("date") or "") < edge:
            continue
        k = kinds.get(a.get("id"))
        k = (k or {}).get("kind") if isinstance(k, dict) else k
        if k:
            seen[k] = seen.get(k, 0) + 1
    return seen


def site_numbers():
    """Числа для отчёта: из свежепересчитанных файлов, а не из головы."""
    out = {}
    try:
        idx = json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8"))
        out["статей"] = len(idx)
        out["последняя"] = max((a.get("date", "") for a in idx), default="?")
        # Сколько работ уже разобрано машиной знаний — те самые «с плюсиком». Владелец
        # 12 августа: «пиши в канал везде, сколько статей с нашими рекомендациями, чтобы
        # видеть в динамике». Считаем по флагу km в индексе — по нему же рисуется значок
        # в ленте, так что число в отчёте и значки на сайте не разойдутся.
        out["с_рекомендациями"] = sum(1 for a in idx if a.get("km"))
        out["полных"] = sum(1 for a in idx if not a.get("express"))
        # Жанровый перекос — то, что владелец просил править 12 августа: «побольше бы
        # практических экспериментальных работ». Без строки в отчёте правку промпта
        # нечем проверить: доля меняется медленно и незаметно, а замечают её только
        # глазами по ленте, то есть через неделю.
        out["жанры"] = _genre_mix(idx)
    except Exception:
        pass
    for name, key in (("data/corpus-stats.json", "покрытие"), ("data/lang-coverage.json", "языки"),
                      ("data/usage-summary.json", "расходы")):
        try:
            out[key] = json.loads((ROOT / name).read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="не писать в Telegram")
    ap.add_argument("--dry", action="store_true", help="ничего не менять и не выкладывать")
    args = ap.parse_args()

    # Причину отказа держим рядом с названием шага: в канал уходило одно слово
    # «выкладка», и по нему нельзя было отличить сработавшую защиту от аварии.
    # 8 августа выкладка отказалась заливать сайт во время пересборки — ровно то, ради
    # чего замок и сделан, — а владелец увидел в канале голое «не получилось».
    done, failed, why = [], [], {}
    for script, what in STEPS:
        if args.dry:
            print(f"  [сухой прогон] {script} — {what}")
            continue
        code, tail = run(script)
        if code == 0:
            done.append(what)
            print(f"  ✅ {what}")
        else:
            failed.append(what)
            print(f"  ⚠️ {what}: код {code}\n     {tail.strip()[:200]}")

    # Выкладка: только витринные файлы, без трогания страниц. deploy_r2 сам сверяет хэши
    # и заливает изменённое, так что лишнего трафика не будет.
    if not args.dry:
        code, tail = run("cloudflare/deploy_r2.py")
        if code == 0:
            print("  ✅ выложено")
        else:
            failed.append("выкладка")
            print(f"  ⚠️ выкладка: код {code}\n     {tail.strip()[:300]}")

    n = site_numbers()
    stats, growth = "", ""
    try:
        import requests
        s = requests.get("https://bridge42worlds.academy/api/stats?days=30", timeout=30).json()
        t = s.get("totals", {})
        days = s.get("byDay") or []
        today = days[-1] if days else {}
        prev = days[-2] if len(days) > 1 else {}
        stats = (f"\n\n👥 <b>Читатели</b>"
                 f"\nСегодня: <b>{today.get('uniq', 0)}</b> человек, "
                 f"<b>{today.get('views', 0)}</b> страниц."
                 f"\nВчера: {prev.get('uniq', 0)} человек, {prev.get('views', 0)} страниц."
                 f"\nЗа 30 дней: {t.get('uniq', '?')} человек, {t.get('n', '?')} страниц, "
                 f"{t.get('visits', '?')} визитов.")
        # Страниц на человека — единственная мерка, которую нельзя накрутить роботами и по
        # которой видно, читают у нас или уходят с первой страницы.
        if today.get("uniq"):
            per = today.get("views", 0) / today["uniq"]
            growth = f"\nСтраниц на человека сегодня: {per:.1f}."
        if not s.get("returning"):
            growth += "\n⚠️ Вернувшихся пока нет — люди заходят по одному разу."
    except Exception:
        stats = "\n\n👥 <b>Читатели</b>: счётчик не ответил."

    # Сеть считает ЗАПРОСЫ (вместе с роботами), наш счётчик — ЛЮДЕЙ. Показываем обе цифры
    # рядом: разрыв в тысячи раз и есть ответ на вопрос «у нас 70 тысяч посетителей?».
    # Плюс сторож лимита: на бесплатном тарифе Worker обслуживает 100 000 запросов в сутки,
    # и 5 августа было 73 001 — узнать об упоре в потолок хочется заранее.
    net = ""
    rows = zone_traffic()
    if rows:
        last = rows[-1]
        req = last["sum"]["requests"]
        net = (f"\n\n🌐 <b>Сеть</b> за {last['dimensions']['date']}: {req:,} запросов, "
               f"{last['sum']['pageViews']:,} страниц, {last['uniq']['uniques']:,} адресов, "
               f"{last['sum']['bytes'] / 2**30:.1f} ГБ."
               f"\nБольшая часть — поисковые роботы, живых людей показывает счётчик выше.")
        if req > 70000:
            net += f"\n🔴 Близко к пределу бесплатного тарифа (100 000 запросов в сутки)."
        elif req > 50000:
            net += f"\n🟡 Половина суточного предела Worker пройдена."

    # Строка машины знаний идёт сразу за объёмом ленты: владелец смотрит её в динамике,
    # а не разыскивает в конце отчёта. Доля считается от ПОЛНЫХ разборов — экспрессам
    # раздел не пишется вовсе, и процент от всей ленты был бы неверным по смыслу.
    km, full = n.get("с_рекомендациями", 0), n.get("полных", 0)
    km_line = ""
    if km:
        share = f", это {km / full * 100:.0f}% полных разборов" if full else ""
        km_line = (f"\n🧭 Разобрано машиной знаний: <b>{km}</b> из {full}{share}. "
                   f"На их страницах стоит ✛ и раздел с рекомендациями автору.")

    msg = (f"<b>Витрина обновлена</b>\n"
           f"Статей в ленте: {n.get('статей', '?')}, последняя за {n.get('последняя', '?')}."
           f"{km_line}{stats}{growth}{money_line()}{net}")
    if failed:
        msg += f"\n\n⚠️ Не получилось: {', '.join(failed)}."

    print("\n" + msg.replace("<b>", "").replace("</b>", ""))

    if not args.quiet and not args.dry:
        f = ROOT / "logs" / "_stats_msg.txt"
        f.parent.mkdir(exist_ok=True)
        f.write_text(msg, encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"), "--file", str(f)],
                       cwd=ROOT, timeout=120)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
