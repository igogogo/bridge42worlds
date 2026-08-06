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


def site_numbers():
    """Числа для отчёта: из свежепересчитанных файлов, а не из головы."""
    out = {}
    try:
        idx = json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8"))
        out["статей"] = len(idx)
        out["последняя"] = max((a.get("date", "") for a in idx), default="?")
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

    done, failed = [], []
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

    msg = (f"<b>Витрина обновлена</b>\n"
           f"Статей в ленте: {n.get('статей', '?')}, последняя за {n.get('последняя', '?')}."
           f"{stats}{growth}{net}")
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
