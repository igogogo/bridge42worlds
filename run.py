#!/usr/bin/env python3
"""
run.py — единый оркестратор Bridge For Two Worlds.

Один скрипт с параметрами вместо запоминания «какой файл в каком случае».

Команды:
  init                     Первичная настройка с нуля (последовательно):
                             теги-список → учёные → теги-описания → перевод справочников
  daily [--date D]         Сгенерировать один день (по умолчанию — вчера).
                             Уже готовые статьи пропускаются (не качаем повторно).
  range --from D --to D    Пройтись по диапазону дней для наполнения историей.
  regen-day --date D       Пересоздать все статьи дня заново (--force генерации).
  html                     Пересобрать весь HTML из data.json (без API) + пересчитать индексы.
  reindex                  Пересобрать articles-index*.json и графы из data.json.
  status                   Собрать дашборд состояния системы → status.html.
  tags [--educational-only]  Пересобрать теги (список+описания+граф+облака).
  delete <arxiv_id>        Удалить статью целиком (контент, картинки, PDF, индексы).
  regen <arxiv_id>         Пересоздать одну статью с нуля (удалить + сгенерировать).
  check [--fix]            Проверка целостности; --fix чинит HTML/индексы (офлайн).

Даты — в формате YYYY-MM-DD.
Флаги генерации (--force) заставляют пересоздавать уже существующие статьи.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows-консоль по умолчанию cp1252 — принудительно UTF-8, чтобы кириллица/эмодзи не падали.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _yesterday():
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def _valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        raise argparse.ArgumentTypeError(f"дата должна быть YYYY-MM-DD, получено: {s}")


# ── init: последовательный прогон standalone-скриптов ──
def cmd_init(args):
    steps = [
        ("Список тегов", "generate_tags_list.py"),
        ("Учёные", "generate_scientists_list.py"),
        ("Описания тегов + граф", "generate_tags.py"),
        ("Перевод справочников", "translate_reference.py"),
    ]
    only = set(args.only or [])
    for label, script in steps:
        if only and script not in only and script.replace(".py", "") not in only:
            continue
        print(f"\n{'=' * 60}\n▶️  {label}: {script}\n{'=' * 60}")
        child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        code = subprocess.run([sys.executable, script], env=child_env).returncode
        if code != 0:
            print(f"❌ {script} завершился с кодом {code}")
            if not args.keep_going:
                print("   Прерываю. Исправьте и запустите заново "
                      "(скрипты возобновляемы — повтор доберёт недостающее).")
                sys.exit(code)
    print("\n🎉 init завершён")


def cmd_daily(args):
    import generate
    generate.process_day(args.date or _yesterday(), force=args.force)


def cmd_range(args):
    import generate
    d = datetime.strptime(args.from_date, "%Y-%m-%d")
    end = datetime.strptime(args.to_date, "%Y-%m-%d")
    if d > end:
        print("❌ --from позже --to"); sys.exit(1)
    total = 0
    while d <= end:
        # Агрегаты (облака/страницы тегов и авторов) пересчитываем один раз в конце,
        # а не каждый день — иначе тратим время впустую.
        total += generate.process_day(d.strftime("%Y-%m-%d"), force=args.force, refresh_aggregates=False)
        d += timedelta(days=1)
    print("\n🔄 Финальный пересчёт агрегатов...")
    for lang in generate.LANGUAGES:
        generate.update_all_tags(lang)
        generate.update_all_scientists(lang)
    generate.update_all_authors()
    print(f"\n🎉 range: сгенерировано {total} статей")


def cmd_regen_day(args):
    import generate
    generate.process_day(args.date, force=True)


def cmd_html(args):
    import generate
    generate.regenerate_all_html()
    generate.rebuild_indexes()


def cmd_status(args):
    import generate
    generate.generate_status_page()
    print("   → status.html")


def cmd_tags(args):
    """Пересобрать теги: список(и) → описания+граф → перевод справочников → облака/страницы.
    --educational-only перегенерирует только образовательный ярус."""
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if args.educational_only:
        chain = [["generate_tags_list.py", "--educational-only"],
                 ["generate_tags.py", "--educational-only"],
                 ["translate_reference.py"]]
    else:
        chain = [["generate_tags_list.py"], ["generate_tags.py"], ["translate_reference.py"]]
    for cmd in chain:
        print(f"\n{'=' * 60}\n▶️  {' '.join(cmd)}\n{'=' * 60}")
        code = subprocess.run([sys.executable, *cmd], env=child_env).returncode
        if code != 0:
            print(f"❌ {cmd[0]} завершился с кодом {code}")
            sys.exit(code)
    import generate
    generate.recompute_tag_counts()
    for lang in generate.LANGUAGES:
        generate.update_all_tags(lang)
    print("\n🎉 Теги пересобраны (граф + облака + страницы)")


def cmd_laws(args):
    """Слой законов: реестр → описания+формулы+граф → перевод → облако/граф + секции на тегах.
    «Законы для тегов — то же, что теги для статей»."""
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    chain = [["generate_laws_list.py"], ["generate_laws.py"], ["translate_reference.py"]]
    for cmd in chain:
        print(f"\n{'=' * 60}\n▶️  {' '.join(cmd)}\n{'=' * 60}")
        code = subprocess.run([sys.executable, *cmd], env=child_env).returncode
        if code != 0:
            print(f"❌ {cmd[0]} завершился с кодом {code}")
            sys.exit(code)
    import generate
    for lang in generate.LANGUAGES:
        generate.update_all_laws(lang)
        generate.update_all_tags(lang)  # секция «Законы» на страницах тегов
    print("\n🎉 Законы пересобраны (облако + граф + секции на тегах)")


def cmd_reindex(args):
    import generate
    generate.rebuild_indexes()
    generate.rebuild_author_graph()
    generate.recompute_tag_counts()
    for lang in generate.LANGUAGES:
        generate.update_all_tags(lang)
        generate.update_all_scientists(lang)
    generate.update_all_authors()


def cmd_delete(args):
    import generate
    n = generate.delete_article(args.id)
    print(f"🗑️ удалено папок: {n}")


def cmd_regen(args):
    import generate
    generate.regenerate_article(args.id)


def cmd_check(args):
    import generate
    problems = generate.integrity_check(fix=args.fix)
    sys.exit(1 if problems and not args.fix else 0)


def cmd_ids(args):
    import generate
    ids = list(args.ids or [])
    if args.ids_file:
        for line in Path(args.ids_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    ids = list(dict.fromkeys(ids))  # уникальные, порядок сохранён
    if not ids:
        print("❌ не указано ни одного id (позиционно или через --ids-file)")
        sys.exit(1)
    generate.generate_ids(ids, force=args.force)


def cmd_author(args):
    import generate
    found = generate.search_arxiv_author(args.name, args.from_date, args.to_date)
    if not found:
        print("❌ ничего не найдено (проверьте имя в формате \"Family, Given\")")
        sys.exit(1)
    print(f"\n🔎 Найдено {len(found)} статей для «{args.name}»"
          + (f" за {args.from_date}…{args.to_date}" if args.from_date else "") + ":")
    for a in found:
        print(f"   {a['published']}  {a['id']}  {a['title'][:70]}")
    if not args.yes:
        ans = input(f"\nСгенерировать все {len(found)}? [y/N] ").strip().lower()
        if ans not in ("y", "yes", "д", "да"):
            print("Отменено.")
            return
    generate.generate_ids([a["id"] for a in found], force=args.force)


def cmd_images(args):
    import generate
    generate.backfill_images(force=args.force)
    generate.regenerate_all_html()


def cmd_add_lang(args):
    lang = args.code
    cfg_path = Path("config.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    langs = cfg.get("languages", [])
    if lang not in langs:
        langs.append(lang)
        cfg["languages"] = langs
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"➕ '{lang}' добавлен в config.json → {langs}")
    else:
        print(f"ℹ️  '{lang}' уже в config.json")

    # 1) Справочники (теги/учёные) на новый язык — отдельным процессом
    print(f"\n▶️  Перевод справочников на {lang}...")
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, "translate_reference.py", lang], env=child_env)

    # generate импортируем ПОСЛЕ правки config, чтобы LANGUAGES включал новый язык
    import generate
    # 2) Бэкфилл архива статей
    print(f"\n▶️  Перевод статей архива на {lang}...")
    generate.backfill_language(lang)
    # 3) Пересборка HTML + индексов
    print(f"\n▶️  Пересборка HTML и индексов...")
    generate.regenerate_all_html()
    generate.rebuild_indexes()
    print(f"\n🎉 Язык {lang} добавлен и наполнен")


def build_parser():
    p = argparse.ArgumentParser(prog="run.py", description="Оркестратор Bridge For Two Worlds",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="первичная настройка с нуля")
    s.add_argument("--only", nargs="*", help="запустить только указанные скрипты (имена без .py)")
    s.add_argument("--keep-going", action="store_true", help="не прерываться при ошибке шага")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("daily", help="сгенерировать один день")
    s.add_argument("--date", type=_valid_date, help="YYYY-MM-DD (по умолчанию вчера)")
    s.add_argument("--force", action="store_true", help="пересоздать уже существующие статьи")
    s.set_defaults(func=cmd_daily)

    s = sub.add_parser("range", help="диапазон дней для наполнения историей")
    s.add_argument("--from", dest="from_date", required=True, type=_valid_date)
    s.add_argument("--to", dest="to_date", required=True, type=_valid_date)
    s.add_argument("--force", action="store_true", help="пересоздавать существующие статьи")
    s.set_defaults(func=cmd_range)

    s = sub.add_parser("regen-day", help="пересоздать все статьи дня")
    s.add_argument("--date", required=True, type=_valid_date)
    s.set_defaults(func=cmd_regen_day)

    s = sub.add_parser("html", help="пересобрать HTML из data.json (без API) + индексы")
    s.set_defaults(func=cmd_html)

    s = sub.add_parser("reindex", help="пересобрать индексы и графы из data.json")
    s.set_defaults(func=cmd_reindex)

    s = sub.add_parser("status", help="собрать дашборд состояния → status.html")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("tags", help="пересобрать теги (список+описания+граф+облака)")
    s.add_argument("--educational-only", action="store_true",
                   help="только образовательный ярус тегов")
    s.set_defaults(func=cmd_tags)

    s = sub.add_parser("laws", help="слой законов (реестр+описания+формулы+граф+секции на тегах)")
    s.set_defaults(func=cmd_laws)

    s = sub.add_parser("delete", help="удалить статью целиком")
    s.add_argument("id", help="arXiv id, напр. 2606.30936v1")
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("regen", help="пересоздать одну статью с нуля")
    s.add_argument("id", help="arXiv id")
    s.set_defaults(func=cmd_regen)

    s = sub.add_parser("check", help="проверка целостности")
    s.add_argument("--fix", action="store_true", help="починить HTML/индексы офлайн")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("images", help="сгенерировать AI-промпты (и картинки при наличии ключа)")
    s.add_argument("--force", action="store_true", help="пересоздать даже если уже есть")
    s.set_defaults(func=cmd_images)

    s = sub.add_parser("add-lang", help="добавить язык и перевести весь архив")
    s.add_argument("code", help="код языка, напр. ar, de, es")
    s.set_defaults(func=cmd_add_lang)

    s = sub.add_parser("ids", help="сгенерировать конкретные статьи по arXiv id")
    s.add_argument("ids", nargs="*", help="список arXiv id")
    s.add_argument("--ids-file", help="файл со списком id (по одному на строку)")
    s.add_argument("--force", action="store_true", help="пересоздать существующие")
    s.set_defaults(func=cmd_ids)

    s = sub.add_parser("author", help="статьи автора за период (с превью-подтверждением)")
    s.add_argument("name", help='имя автора, формат "Family, Given"')
    s.add_argument("--from", dest="from_date", type=_valid_date, help="YYYY-MM-DD")
    s.add_argument("--to", dest="to_date", type=_valid_date, help="YYYY-MM-DD")
    s.add_argument("--yes", action="store_true", help="без подтверждения")
    s.add_argument("--force", action="store_true", help="пересоздать существующие")
    s.set_defaults(func=cmd_author)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
