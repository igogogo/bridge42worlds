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
  bulk-select --categories ... [--months-back N]
                            Year-wide каскадный отбор из локального arXiv-кэша (data/arxiv-bulk/,
                             см. arxiv_bulk_chunk.py) — не «сегодня лучшее», а весь пул за N
                             месяцев, 2 прохода фильтрации + ранжирование + аудит лицензий →
                             data/bulk-select/<run>.json.
  bulk-generate --file PATH [--batch-size N]
                             Генерирует статьи из bulk-select файла батчами, приостанавливается
                             перед пиковыми часами DeepSeek (цена x2).
  regen-day --date D       Пересоздать все статьи дня заново (--force генерации).
  html                     Пересобрать весь HTML из data.json (без API) + пересчитать индексы.
  reindex                  Пересобрать articles-index*.json и графы из data.json.
  status                   Собрать дашборд состояния системы → status.html.
  tags [--educational-only]  Пересобрать теги (список+описания+граф+облака).
  evolve [--rounds N]      Ко-эволюция графа знаний: растит tags/laws/scientists пробел-
                             осведомлённо (--gaps) до потолков из config.json → growth.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Windows-консоль по умолчанию cp1252 — принудительно UTF-8, чтобы кириллица/эмодзи не падали.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", line_buffering=True)
    except (AttributeError, ValueError):
        pass


def _yesterday():
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


def _valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        raise argparse.ArgumentTypeError(f"дата должна быть YYYY-MM-DD, получено: {s}")


# ── init: последовательный прогон standalone-скриптов ──
def cmd_init(args):
    steps = [
        ("Список тегов", "tag_list.py"),
        ("Законы", "law_list.py"),          # ←тегов (+ чистит теги-дубли законов)
        ("Учёные", "scientist_list.py"),    # ←тегов+законов
        ("Описания тегов + граф", "tag_describe.py"),  # ←учёных+законов
        ("Описания законов", "law_describe.py"),       # ←учёных+тегов
        ("Перевод справочников", "reference_translate.py"),
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
    if args.refine:
        os.environ["REFINE"] = "1"
    import generate
    generate.process_day(args.date or _yesterday(), force=args.force, express=args.express, category=args.category, limit=args.limit)


def cmd_range(args):
    if args.refine:
        os.environ["REFINE"] = "1"
    import generate
    d = datetime.strptime(args.from_date, "%Y-%m-%d")
    end = datetime.strptime(args.to_date, "%Y-%m-%d")
    if d > end:
        print("❌ --from позже --to"); sys.exit(1)
    total = 0
    while d <= end:
        if args.limit is not None and total >= args.limit:
            print(f"\n🏁 Достигнут общий лимит {args.limit} статей — останавливаюсь раньше срока.")
            break
        # Агрегаты (облака/страницы тегов и авторов) пересчитываем один раз в конце,
        # а не каждый день — иначе тратим время впустую.
        day_limit = (args.limit - total) if args.limit is not None else None
        total += generate.process_day(d.strftime("%Y-%m-%d"), force=args.force, refresh_aggregates=False,
                                       express=args.express, limit=day_limit, category=args.category)
        d += timedelta(days=1)
    print("\n🔄 Финальный пересчёт агрегатов...")
    for lang in generate.LANGUAGES:
        generate.update_all_tags(lang)
        generate.update_all_scientists(lang)
    generate.update_all_authors()
    print(f"\n🎉 range: сгенерировано {total} статей{' [экспресс]' if args.express else ''}")


def cmd_bulk_select(args):
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    cmd = [sys.executable, "article_bulk_select.py",
           "--categories", *args.categories,
           "--months-back", str(args.months_back),
           "--round1-percent", str(args.round1_percent),
           "--round2-percent", str(args.round2_percent)]
    if args.target_count:
        cmd += ["--target-count", str(args.target_count)]
    code = subprocess.run(cmd, env=child_env).returncode
    if code != 0:
        sys.exit(code)


def cmd_bulk_generate(args):
    import generate
    generate.bulk_generate(args.file, batch_size=args.batch_size, express=not args.full,
                            force=args.force, skip_peak_check=args.skip_peak_check,
                            max_batches=args.max_batches)


def cmd_regen_day(args):
    if args.refine:
        os.environ["REFINE"] = "1"
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


def _run_chain(chain):
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for cmd in chain:
        print(f"\n{'=' * 60}\n▶️  {' '.join(cmd)}\n{'=' * 60}")
        code = subprocess.run([sys.executable, *cmd], env=child_env).returncode
        if code != 0:
            print(f"❌ {cmd[0]} завершился с кодом {code}")
            sys.exit(code)


def cmd_tags(args):
    """Теги: список(и) → описания+граф → перевод → облака/страницы.
    По умолчанию — ДОГЕНЕРАЦИЯ недостающего (top-up, не трогает уже описанное).
      --force        переописать все описания (список не трогаем)
      --rebuild      снести список тегов и собрать заново с нуля
      --educational-only  только образовательный ярус
      --gaps N       пробел-осведомлённая догенерация +N по реальному корпусу (Итерация 2)"""
    if args.rebuild:
        for f in ("lang/ru/data/tags-list.json", "lang/ru/data/tags-list-educational.json"):
            Path(f).unlink(missing_ok=True)
        print("♻️  списки тегов удалены — полная пересборка")
    edu = ["--educational-only"] if args.educational_only else []
    describe = ["--force"] if args.force else []
    if args.refine: describe.append("--refine")
    focus = ["--focus", args.focus] if getattr(args, "focus", "") else []
    active_exists = Path("lang/ru/data/tags-list.json").exists()
    if args.gaps:
        list_step = ["tag_list.py", "--gaps", str(args.gaps), *edu, *focus]
    elif active_exists and not args.rebuild and not args.educational_only:
        # tag_list.py без --gaps генерит АКТИВНЫЙ список слепо и ПОЛНОСТЬЮ ПЕРЕЗАПИСЫВАЕТ его
        # (не топ-ап, в отличие от educational/laws/scientists) — если список уже есть, трогать
        # его тут нельзя, иначе --force на описаниях случайно сносит и список тоже.
        list_step = None
    else:
        list_step = ["tag_list.py", *edu]
    chain = ([list_step] if list_step else []) + [["tag_describe.py", *edu, *describe], ["reference_translate.py"]]
    _run_chain(chain)
    import generate
    generate.recompute_tag_counts()
    for lang in generate.LANGUAGES:
        generate.update_all_tags(lang)
        generate.generate_knowledge_graph_page(lang)
    generate.build_knowledge_graph_data()
    print("\n🎉 Теги пересобраны (граф + облака + страницы + граф знаний)")


def cmd_laws(args):
    """Законы: реестр → описания+формулы+граф → перевод → облако/граф + секции на тегах.
    По умолчанию — ДОГЕНЕРАЦИЯ недостающего. --force переописать все; --rebuild снести реестр.
    --gaps N пробел-осведомлённая догенерация +N по реальному корпусу (Итерация 2)."""
    if args.rebuild:
        Path("lang/ru/data/laws-list.json").unlink(missing_ok=True)
        print("♻️  реестр законов удалён — полная пересборка")
    describe = ["--force"] if args.force else []
    if args.refine: describe.append("--refine")
    focus = ["--focus", args.focus] if getattr(args, "focus", "") else []
    if getattr(args, "important", None):
        list_step = ["law_list.py", "--important", str(args.important), *focus]
    elif args.gaps:
        list_step = ["law_list.py", "--gaps", str(args.gaps), *focus]
    else:
        list_step = ["law_list.py"]
    _run_chain([list_step, ["law_describe.py", *describe], ["reference_translate.py"]])
    import generate
    for lang in generate.LANGUAGES:
        generate.update_all_laws(lang)
        generate.update_all_tags(lang)  # секция «Законы» на страницах тегов
        generate.generate_knowledge_graph_page(lang)
    generate.build_knowledge_graph_data()
    print("\n🎉 Законы пересобраны (облако + граф + секции на тегах + граф знаний)")


def cmd_scientists(args):
    """Учёные: список (top-up до цели) → перевод справочников → облака/страницы.
    --rebuild снести scientists.json и собрать заново.
    --gaps N пробел-осведомлённая догенерация +N по реальному корпусу (Итерация 2)."""
    if args.rebuild:
        Path("lang/ru/data/scientists.json").unlink(missing_ok=True)
        print("♻️  scientists.json удалён — полная пересборка")
    focus = ["--focus", args.focus] if getattr(args, "focus", "") else []
    if getattr(args, "famous", None):
        list_step = ["scientist_list.py", "--famous", str(args.famous)]
    elif args.gaps:
        list_step = ["scientist_list.py", "--gaps", str(args.gaps), *focus]
    else:
        list_step = ["scientist_list.py"]
    _run_chain([list_step, ["reference_translate.py"]])
    import generate
    for lang in generate.LANGUAGES:
        generate.update_all_scientists(lang)
        generate.generate_knowledge_graph_page(lang)
    generate.build_knowledge_graph_data()
    print("\n🎉 Учёные пересобраны (+ граф знаний)")


def cmd_evolve(args):
    """Ко-эволюция графа знаний (Трек 3, Итерация 2): растит tags/laws/scientists пробел-
    осведомлённо (--gaps), понемногу за раунд, до потолков из config.json → growth.*_max.
    Раньше рост делался вручную (поднять *_count в config.json → перезапустить) — теперь
    это делает сам evolve, раунд за раундом, пока не упрётся в потолки или не кончатся раунды.
      --rounds N   сколько раундов максимум (по умолчанию 1 — один шаг роста на каждую сущность)
    Останавливается раньше, если ВСЕ три уже на потолке (did_anything=False)."""
    import generate
    cfg_path = Path("config.json")
    growth = json.loads(cfg_path.read_text(encoding="utf-8")).get("growth", {})
    step = growth.get("step", 10)
    caps = {
        "active": growth.get("tags_active_max", 150),
        "edu": growth.get("tags_educational_max", 150),
        "laws": growth.get("laws_max", 100),
        "sci": growth.get("scientists_max", 100),
    }

    def count(path):
        if not Path(path).exists():
            return 0
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return len(data)

    rounds = args.rounds or 1
    for r in range(1, rounds + 1):
        print(f"\n{'=' * 60}\n🌳 Ко-эволюция графа знаний: раунд {r}/{rounds}\n{'=' * 60}")
        n_active = count("lang/ru/data/tags-list.json")
        n_edu = count("lang/ru/data/tags-list-educational.json")
        n_laws = count("lang/ru/data/laws-list.json")
        n_sci = count("lang/ru/data/scientists.json")
        did_anything = False

        if n_active < caps["active"]:
            add = min(step, caps["active"] - n_active)
            print(f"🏷️  Активные теги: {n_active} → +{add} (потолок {caps['active']}), пробел-осведомлённо")
            cmd_tags(argparse.Namespace(rebuild=False, educational_only=False, force=False, refine=False, gaps=add))
            did_anything = True
        else:
            print(f"🏷️  Активные теги: {n_active}/{caps['active']} — потолок достигнут")

        if n_edu < caps["edu"]:
            add = min(step, caps["edu"] - n_edu)
            print(f"📚 Образовательные теги: {n_edu} → +{add} (потолок {caps['edu']}), блинд top-up")
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["tags"]["educational_count"] = n_edu + add
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            cmd_tags(argparse.Namespace(rebuild=False, educational_only=True, force=False, refine=False, gaps=None))
            did_anything = True
        else:
            print(f"📚 Образовательные теги: {n_edu}/{caps['edu']} — потолок достигнут")

        if n_laws < caps["laws"]:
            add = min(step, caps["laws"] - n_laws)
            print(f"⚖️  Законы: {n_laws} → +{add} (потолок {caps['laws']}), пробел-осведомлённо")
            cmd_laws(argparse.Namespace(rebuild=False, force=False, refine=False, gaps=add))
            did_anything = True
        else:
            print(f"⚖️  Законы: {n_laws}/{caps['laws']} — потолок достигнут")

        if n_sci < caps["sci"]:
            add = min(step, caps["sci"] - n_sci)
            print(f"👨‍🔬 Учёные: {n_sci} → +{add} (потолок {caps['sci']}), пробел-осведомлённо")
            cmd_scientists(argparse.Namespace(rebuild=False, gaps=add))
            did_anything = True
        else:
            print(f"👨‍🔬 Учёные: {n_sci}/{caps['sci']} — потолок достигнут")

        if not did_anything:
            print("\n🎉 Все потолки достигнуты — эволюция завершена раньше срока.")
            break

    print("\n🔄 Финальный rebuild HTML...")
    generate.regenerate_all_html()
    generate.rebuild_indexes()
    print("\n🎉 run.py evolve завершён")


def cmd_reset(args):
    """Удаление сгенерированного (осторожно!). Всё под lang/ — это ВЫВОД (страницы+данные).
      --articles   статьи: lang/*/archive + authors + articles-index* + authors-graph + temp + sitemap/status
      --refs       справочники: описания+графы+ОТРЕНДЕРЕННЫЕ страницы tags/laws/scientists/graph
      --all        всё сгенерированное (статьи + справочники + страницы). Списки без --lists сохраняются.
      --lang CODE  весь язык lang/CODE/
      --lists      вместе с --refs/--all снести и *-list.json (иначе списки-семена сохраняются)"""
    import shutil, glob

    def rm(p):
        p = Path(p)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()

    if args.lang:
        rm(f"lang/{args.lang}")
        print(f"🗑️  удалён язык {args.lang}: lang/{args.lang}/")
        return

    # Отрендеренные общие страницы (index/about) — вывод, чистим при любом сбросе.
    if args.articles or args.refs or args.all:
        for p in glob.glob("lang/*/index.html") + glob.glob("lang/*/about.html"):
            rm(p)

    if args.articles or args.all:
        for sub in ("archive", "authors"):
            for p in glob.glob(f"lang/*/{sub}"):
                rm(p)
        for p in glob.glob("lang/*/articles-index*.json") + glob.glob("temp/*") + glob.glob("sitemap*.xml"):
            rm(p)
        rm("data/authors-graph.json")
        rm("status.html")
        print("🗑️  статьи + страницы + индексы + граф авторов + sitemap + temp удалены")

    if args.refs or args.all:
        # отрендеренные страницы справочников (папки целиком)
        for sub in ("tags", "laws", "scientists", "graph"):
            for p in glob.glob(f"lang/*/{sub}"):
                rm(p)
        for lang_dir in glob.glob("lang/*/data"):
            for name in ("tags.json", "scientists.json", "laws.json"):
                rm(Path(lang_dir, name))
            if args.lists:
                for name in ("tags-list.json", "tags-list-educational.json", "laws-list.json"):
                    rm(Path(lang_dir, name))
        for name in ("tags-graph.json", "laws-graph.json", "knowledge-graph.json"):
            rm(Path("data", name))
        print("🗑️  справочники: описания + графы + страницы (tags/laws/scientists/graph)"
              + (" + списки" if args.lists else "") + " удалены")

    if not (args.articles or args.refs or args.all):
        print("Ничего не указано. Скоупы: --articles / --refs / --all / --lang CODE (+ --lists).")


def cmd_lang(args):
    """Управление языками: add CODE / remove CODE."""
    cfg_path = Path("config.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    langs = cfg.get("languages", [])
    if args.action == "remove":
        import shutil
        if args.code == cfg.get("default_lang"):
            print(f"❌ нельзя удалить язык по умолчанию ({args.code})")
            sys.exit(1)
        if args.code in langs:
            langs.remove(args.code)
            cfg["languages"] = langs
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.rmtree(Path(f"lang/{args.code}"), ignore_errors=True)
        print(f"🗑️  язык {args.code} удалён (config + lang/{args.code}/) → {langs}")
    else:  # add
        args_ns = argparse.Namespace(code=args.code)
        cmd_add_lang(args_ns)


def cmd_reindex(args):
    import generate
    generate.rebuild_indexes()
    generate.rebuild_author_graph()
    generate.recompute_tag_counts()
    for lang in generate.LANGUAGES:
        generate.update_all_tags(lang)
        generate.update_all_scientists(lang)
    generate.update_all_authors()
    _run_chain([["build_knowledge_graph.py"]])


def cmd_graph(args):
    """Пересобрать единый граф знаний (теги⇄законы⇄учёные) → data/knowledge-graph.json."""
    _run_chain([["build_knowledge_graph.py"]])


def cmd_delete(args):
    import generate
    n = generate.delete_article(args.id)
    print(f"🗑️ удалено папок: {n}")


def cmd_regen(args):
    if args.refine:
        os.environ["REFINE"] = "1"
    import generate
    generate.regenerate_article(args.id)


def cmd_check(args):
    import generate
    problems = generate.integrity_check(fix=args.fix)
    broken = {}
    if args.links:
        import link_check
        broken = link_check.check_links()
    sys.exit(1 if (problems and not args.fix) or broken else 0)


def cmd_links(args):
    import link_check
    broken = link_check.check_links()
    sys.exit(1 if broken else 0)


def cmd_ids(args):
    if args.refine:
        os.environ["REFINE"] = "1"
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
    if args.refine:
        os.environ["REFINE"] = "1"
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
    if not args.refs_only:
        generate.backfill_images(force=args.force, gen_images=args.gen_images, preset=args.preset)
        generate.regenerate_all_html()
    if not args.articles_only:
        generate.backfill_tag_law_images(force=args.force, gen_images=args.gen_images, preset=args.preset)
        for lang in generate.LANGUAGES:
            generate.update_all_tags(lang)
            generate.update_all_laws(lang)


def cmd_abstracts(args):
    import generate
    generate.backfill_abstracts(force=args.force)
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
    subprocess.run([sys.executable, "reference_translate.py", lang], env=child_env)

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


def cmd_translate_one(args):
    import generate
    generate.translate_article_lang(args.id, args.lang, force=args.force)


def cmd_stats(args):
    """Быстрая офлайн-сводка покрытия: справочники (описано/недостаёт), перевод по языкам, статьи.
    Подсказывает, что догенерить (run.py tags/laws/scientists)."""
    import glob
    cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
    langs = cfg.get("languages", [])
    default = cfg.get("default_lang", "ru")

    def jload(p, d):
        p = Path(p)
        if not p.exists():
            return d
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return d

    def tip(total, done):
        return "" if total <= done else f"   ← недостаёт {total - done}"

    print(f"\n📊 СВОДКА bridge42worlds (язык-источник: {default})\n")

    active = jload(f"lang/{default}/data/tags-list.json", [])
    edu = jload(f"lang/{default}/data/tags-list-educational.json", [])
    tags_ru = jload(f"lang/{default}/data/tags.json", {})
    total_tags = len(active) + len(edu)
    desc_tags = sum(1 for t in (active + edu) if (tags_ru.get(t.get("en")) or {}).get("description"))
    print(f"🏷️  Теги:   {total_tags:>4} в списках (active {len(active)}, edu {len(edu)}) · описано {desc_tags}{tip(total_tags, desc_tags)}")

    laws_list = jload(f"lang/{default}/data/laws-list.json", [])
    laws_ru = jload(f"lang/{default}/data/laws.json", {})
    desc_laws = sum(1 for x in laws_list if (laws_ru.get(x.get("en")) or {}).get("description"))
    print(f"⚖️  Законы: {len(laws_list):>4} в реестре · описано {desc_laws}{tip(len(laws_list), desc_laws)}")

    sci = jload(f"lang/{default}/data/scientists.json", {})
    target = cfg.get("scientists", {}).get("total", 0)
    print(f"👨‍🔬 Учёные: {len(sci):>4} · цель {target}{tip(target, len(sci))}")

    others = [l for l in langs if l != default]
    if others:
        print("\n🌐 Перевод справочников (переведено / всего в источнике):")
        srcs = [("tags", tags_ru), ("laws", laws_ru), ("scientists", sci)]
        for lang in others:
            cells = []
            for name, src in srcs:
                tgt = jload(f"lang/{lang}/data/{name}.json", {})
                mark = "✅" if len(tgt) >= len(src) and src else ("—" if not src else "⏳")
                cells.append(f"{name} {len(tgt)}/{len(src)}{mark}")
            print(f"   {lang}: " + " · ".join(cells))
    else:
        print("\n🌐 Языки: только источник (" + default + "). Добавить: run.py lang add <code>")

    arts = glob.glob(f"lang/{default}/archive/*/*/data.json")
    dates = sorted(set(Path(p).parent.parent.name for p in arts))
    span = f" ({dates[0]}…{dates[-1]})" if dates else ""
    print(f"\n📰 Статьи: {len(arts)} за {len(dates)} дней{span}")

    todo = []
    if total_tags > desc_tags:
        todo.append("run.py tags")
    if len(laws_list) > desc_laws:
        todo.append("run.py laws")
    if target > len(sci):
        todo.append("run.py scientists")
    if todo:
        print("\n💡 Догенерить недостающее: " + " ; ".join(todo))
    print()


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
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка Simple и Popular")
    s.add_argument("--express", action="store_true", help="дешёвый режим: по аннотации, не по полному тексту PDF; только config.express.tiers полноценно (см. TODO.md)")
    s.add_argument("--category", metavar="CAT", help="arXiv-категория(и) для поиска — ОДНА или НЕСКОЛЬКО через запятую (напр. 'astro-ph.*,gr-qc,hep-th,quant-ph'); по умолчанию astro-ph.*")
    s.add_argument("--limit", type=int, metavar="N", help="взять топ-N лучших за день (после ранжирования единым пулом по всем категориям)")
    s.set_defaults(func=cmd_daily, refine=False)

    s = sub.add_parser("range", help="диапазон дней для наполнения историей")
    s.add_argument("--from", dest="from_date", required=True, type=_valid_date)
    s.add_argument("--to", dest="to_date", required=True, type=_valid_date)
    s.add_argument("--force", action="store_true", help="пересоздавать существующие статьи")
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка Simple и Popular")
    s.add_argument("--express", action="store_true", help="дешёвый режим по аннотации (см. daily --express)")
    s.add_argument("--limit", type=int, metavar="N", help="общий лимит статей на весь диапазон (не на день)")
    s.add_argument("--category", metavar="CAT", help="arXiv-категория (напр. quant-ph) — по умолчанию astro-ph.*")
    s.set_defaults(func=cmd_range, refine=False)

    s = sub.add_parser("bulk-select", help="year-wide каскадный отбор из локального arXiv-кэша (data/arxiv-bulk/) → data/bulk-select/<run>.json")
    s.add_argument("--categories", nargs="+", required=True, help="напр. astro-ph.* nucl-ex nucl-th quant-ph gr-qc")
    s.add_argument("--months-back", type=int, default=12, help="сколько месяцев назад брать пул кандидатов (по умолч. 12)")
    s.add_argument("--round1-percent", type=float, default=10, help="%% на батч в грубом проходе (по умолч. 10)")
    s.add_argument("--round2-percent", type=float, default=20, help="%% на батч в тонком проходе (по умолч. 20)")
    s.add_argument("--target-count", type=int, help="обрезать финальный ранжированный список до N перед аудитом лицензий")
    s.set_defaults(func=cmd_bulk_select)

    s = sub.add_parser("bulk-generate", help="генерирует статьи из data/bulk-select/<run>.json батчами, с учётом пиковых часов DeepSeek")
    s.add_argument("--file", required=True, metavar="PATH", help="путь к data/bulk-select/<run>.json")
    s.add_argument("--batch-size", type=int, default=100)
    s.add_argument("--max-batches", type=int, metavar="N", help="остановиться после N батчей (напр. пробный прогон)")
    s.add_argument("--full", action="store_true", help="полный цикл вместо экспресс (дороже)")
    s.add_argument("--force", action="store_true", help="пересоздать уже существующие статьи")
    s.add_argument("--skip-peak-check", action="store_true", help="игнорировать пиковые часы DeepSeek (не рекомендуется)")
    s.set_defaults(func=cmd_bulk_generate)

    s = sub.add_parser("regen-day", help="пересоздать все статьи дня")
    s.add_argument("--date", required=True, type=_valid_date)
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка Simple и Popular")
    s.set_defaults(func=cmd_regen_day, refine=False)

    s = sub.add_parser("html", help="пересобрать HTML из data.json (без API) + индексы")
    s.set_defaults(func=cmd_html)

    s = sub.add_parser("reindex", help="пересобрать индексы и графы из data.json")
    s.set_defaults(func=cmd_reindex)

    s = sub.add_parser("status", help="собрать дашборд состояния → status.html")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("stats", help="быстрая офлайн-сводка покрытия (что готово / что догенерить)")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("graph", help="единый граф знаний теги⇄законы⇄учёные → data/knowledge-graph.json")
    s.set_defaults(func=cmd_graph)

    s = sub.add_parser("tags", help="теги: догенерация недостающего (top-up); --force/--rebuild/--gaps")
    s.add_argument("--educational-only", action="store_true", help="только образовательный ярус")
    s.add_argument("--force", action="store_true", help="переописать все описания (список не трогать)")
    s.add_argument("--rebuild", action="store_true", help="снести список тегов и собрать с нуля")
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка описаний тегов")
    s.add_argument("--gaps", type=int, metavar="N", help="пробел-осведомлённая догенерация +N тегов по реальному корпусу (Итерация 2 ко-эволюции), вместо топ-апа до active_count")
    s.add_argument("--focus", default="", help="разовый приоритет темы для --gaps, напр. 'quantum mechanics'")
    s.set_defaults(func=cmd_tags)

    s = sub.add_parser("laws", help="законы: догенерация недостающего; --force/--rebuild/--gaps")
    s.add_argument("--force", action="store_true", help="переописать все описания законов")
    s.add_argument("--rebuild", action="store_true", help="снести реестр законов и собрать с нуля")
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка описаний законов")
    s.add_argument("--gaps", type=int, metavar="N", help="пробел-осведомлённая догенерация +N законов по реальному корпусу")
    s.add_argument("--focus", default="", help="разовый приоритет темы для --gaps/--important")
    s.add_argument("--important", type=int, metavar="N", help="добор +N фундаментальных/общеизвестных законов независимо от корпуса")
    s.set_defaults(func=cmd_laws)

    s = sub.add_parser("scientists", help="учёные: top-up до цели; --rebuild с нуля; --gaps")
    s.add_argument("--rebuild", action="store_true", help="снести scientists.json и собрать с нуля")
    s.add_argument("--gaps", type=int, metavar="N", help="пробел-осведомлённая догенерация +N учёных по реальному корпусу")
    s.add_argument("--focus", default="", help="разовый приоритет темы для --gaps")
    s.add_argument("--famous", type=int, metavar="N", help="добор +N общеизвестных учёных (Эйнштейн/Ньютон и т.п.) без уклона в сторону менее раскрученных")
    s.set_defaults(func=cmd_scientists)

    s = sub.add_parser("evolve", help="ко-эволюция графа знаний: растит tags/laws/scientists пробел-осведомлённо до потолков (config.json → growth)")
    s.add_argument("--rounds", type=int, default=1, metavar="N", help="сколько раундов роста максимум (по умолчанию 1)")
    s.set_defaults(func=cmd_evolve)

    s = sub.add_parser("reset", help="удалить сгенерированное (--articles/--refs/--all/--lang; +--lists)")
    s.add_argument("--articles", action="store_true", help="статьи + индексы + граф авторов + temp")
    s.add_argument("--refs", action="store_true", help="справочники (описания+графы тегов/учёных/законов)")
    s.add_argument("--all", action="store_true", help="статьи + справочники")
    s.add_argument("--lang", help="удалить всё сгенерированное только для языка CODE")
    s.add_argument("--lists", action="store_true", help="с --refs/--all снести и *-list.json")
    s.set_defaults(func=cmd_reset)

    s = sub.add_parser("lang", help="языки: add CODE / remove CODE")
    s.add_argument("action", choices=["add", "remove"])
    s.add_argument("code", help="код языка, напр. ar, de, ja")
    s.set_defaults(func=cmd_lang)

    s = sub.add_parser("delete", help="удалить статью целиком")
    s.add_argument("id", help="arXiv id, напр. 2606.30936v1")
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("regen", help="пересоздать одну статью с нуля")
    s.add_argument("id", help="arXiv id")
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка Simple и Popular")
    s.set_defaults(func=cmd_regen, refine=False)

    s = sub.add_parser("check", help="проверка целостности")
    s.add_argument("--fix", action="store_true", help="починить HTML/индексы офлайн")
    s.add_argument("--links", action="store_true", help="+ проверка внутренних ссылок на 404 (офлайн, без API)")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("links", help="офлайн-проверка внутренних ссылок сайта на 404 (без API, перед публикацией)")
    s.set_defaults(func=cmd_links)

    s = sub.add_parser("images", help="Обложки статей (из PDF, бесплатно) + тегов/законов (промпты, FLUX только с --gen-images)")
    s.add_argument("--force", action="store_true", help="пересоздать даже если уже есть")
    s.add_argument("--articles-only", action="store_true", help="только статьи (не трогать теги/законы)")
    s.add_argument("--refs-only", action="store_true", help="только теги/законы (не трогать статьи)")
    s.add_argument("--gen-images", action="store_true",
                    help="теги/законы: реально потратить бюджет на FLUX (без флага — только промпт + честная пометка image_pending)")
    s.add_argument("--preset", default="image", choices=["image", "image_cheap", "image_quality"],
                    help="конфиг из config.agents: image (дефолт/текущий), image_cheap (FLUX-1-schnell, ~$0.002/img), image_quality (FLUX-2-pro, ~$0.015/img)")
    s.set_defaults(func=cmd_images)

    s = sub.add_parser("abstracts", help="«Аннотации» из авторского arXiv-abstract → data.json + HTML")
    s.add_argument("--force", action="store_true", help="переписать даже если уже есть")
    s.set_defaults(func=cmd_abstracts)

    s = sub.add_parser("add-lang", help="добавить язык и перевести весь архив")
    s.add_argument("code", help="код языка, напр. ar, de, es")
    s.set_defaults(func=cmd_add_lang)

    s = sub.add_parser("translate-one", help="перевести ОДНУ статью на ОДИН язык (для точечных правок / чистого замера стоимости перевода)")
    s.add_argument("id", help="arXiv id статьи")
    s.add_argument("lang", help="код языка, напр. ar, de, es")
    s.add_argument("--force", action="store_true", help="перевести заново, даже если уже есть")
    s.set_defaults(func=cmd_translate_one)

    s = sub.add_parser("ids", help="сгенерировать конкретные статьи по arXiv id")
    s.add_argument("ids", nargs="*", help="список arXiv id")
    s.add_argument("--ids-file", help="файл со списком id (по одному на строку)")
    s.add_argument("--force", action="store_true", help="пересоздать существующие")
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка Simple и Popular")
    s.set_defaults(func=cmd_ids, refine=False)

    s = sub.add_parser("author", help="статьи автора за период (с превью-подтверждением)")
    s.add_argument("name", help='имя автора, формат "Family, Given"')
    s.add_argument("--from", dest="from_date", type=_valid_date, help="YYYY-MM-DD")
    s.add_argument("--to", dest="to_date", type=_valid_date, help="YYYY-MM-DD")
    s.add_argument("--yes", action="store_true", help="без подтверждения")
    s.add_argument("--force", action="store_true", help="пересоздать существующие")
    s.add_argument("--refine", action="store_true", help="рефлексивная шлифовка Simple и Popular")
    s.set_defaults(func=cmd_author, refine=False)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
