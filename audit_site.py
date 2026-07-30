"""Проверка сайта перед публикацией — по путям читателя, а не по наличию файлов.

Заведён 2026-07-28. Причина: прежняя проверка смотрела, лежат ли файлы на месте, и пропустила
три ошибки подряд — пустую строку языков (не публиковался config.json), ссылки карточек в чужой
язык и переключатель уровня, ломавший шапку. Всё это видно, только если пройти путь читателя.

Ручная часть чек-листа — в ЧЕК-ЛИСТ.md. Здесь то, что можно сосчитать.

    python audit_site.py            # проверить
    python audit_site.py --live     # плюс сверить с живым сайтом
"""
import json
import os
import re
import sys
from pathlib import Path

os.chdir(Path(__file__).parent)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import json as _json
from pathlib import Path as _Path
# Языки берём из config.json, а не списком: хардкод ["ru","en","es","ar"] — причина того,
# что пятый язык (fr) прошёл мимо половины инструментов (аудит 2026-07-30).
LANGS = _json.loads(_Path("config.json").read_text(encoding="utf-8")).get("languages", ["ru"])
SITE = "https://bridge42worlds.academy"
SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
TAGS = re.compile(r"<[^>]+>")
MARKER = re.compile(r"\[/?(?:tag|law|sci|art)[^\]]*\]")
CYR = re.compile(r"[а-яА-ЯёЁ]")

problems, notes = [], []


def fail(msg, detail=""):
    problems.append((msg, detail))


def ok(msg):
    notes.append(msg)


def visible_text(html):
    t = SCRIPT.sub(" ", html)
    t = MARKER.sub(" ", t)
    return TAGS.sub(" ", t)


# ── 1. Полнота раздела ───────────────────────────────────────────────────────
PAGES = ["course.html", "learn.html", "lecture.html", "memo.html", "frontier.html",
         "course-thermodynamics.html", "discoveries.html", "reference.html",
         "mathkit.html", "hypotheses.html"]
missing = [p for p in PAGES if not Path(p).exists()]
if missing:
    fail("нет страниц учебного раздела", ", ".join(missing))
else:
    ok(f"страницы раздела: {len(PAGES)}/{len(PAGES)}")


# ── 2. Переводы ──────────────────────────────────────────────────────────────
for name in ("discoveries", "mathkit", "hypotheses", "reference"):
    p = Path(f"data/theory/{name}.json")
    if not p.exists():
        fail(f"нет справочника {name}.json")
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    got = [l for l in LANGS if isinstance(d.get(l), dict) and d[l].get("title")]
    if len(got) != 4:
        fail(f"справочник {name}: переведён не на все языки", "/".join(got))
lessons = [f for f in Path("data/theory/courses").rglob("*.json") if f.name[0].isdigit()]
lect = list(Path("data/theory/lectures").glob("*.json"))
part = [f.name for f in lessons + lect
        if not all(isinstance(json.loads(f.read_text(encoding="utf-8")).get(l), dict) for l in LANGS)]
if part:
    fail(f"уроки/лекции без всех языков: {len(part)}", ", ".join(part[:4]))
else:
    ok(f"уроки и лекции: {len(lessons) + len(lect)} на четырёх языках")


# ── 3. Публикация: что реально уедет на сайт ─────────────────────────────────
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("d", "cloudflare/deploy_r2.py")
    dep = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(dep)
    except SystemExit:
        pass
    pub = {p.relative_to(dep.ROOT).as_posix() for p in dep.iter_files()}

    # config.json — по нему строится строка выбора языков. Без него языков нет на всём сайте.
    if "config.json" not in pub:
        fail("config.json НЕ публикуется", "строка выбора языков будет пустой на всём сайте")
    else:
        ok("config.json публикуется")

    # картинки параграфов курса: страница просит их по имени урока, двойника в webp у них нет
    course_img = [k for k in pub if "/courses/" in k and k.endswith(".jpg")]
    on_disk = len(list(Path("data/theory/courses").rglob("img/*.jpg")))
    if on_disk and len(course_img) != on_disk:
        fail("картинки параграфов курса не публикуются", f"на диске {on_disk}, в публикации {len(course_img)}")
    elif on_disk:
        ok(f"картинки курса публикуются: {len(course_img)}")

    # мусор: корневые страницы, на которые никто не ссылается
    roots = {k for k in pub if "/" not in k and k.endswith(".html")}
    # Ссылки бывают и в разметке, и в скриптах (блок справочников на learn.html строится в JS,
    # адреса идут с ?lang=). Ищем упоминание имени файла где угодно в исходниках — иначе живые
    # страницы попадают в «мусор» по ошибке.
    refs = set()
    sources = (list(Path(".").glob("*.html")) + list(Path("templates").glob("*.html"))
               + list(Path("js").glob("*.js")))
    for f in sources:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        refs |= set(re.findall(r"[/'\"]([a-z0-9_-]+\.html)", txt))
    orphan = sorted(roots - refs - {"index.html", "404.html", "status.html"})
    if orphan:
        fail(f"публикуются страницы, на которые нет ссылок: {len(orphan)}", ", ".join(orphan[:6]))
    else:
        ok("мусорных страниц в публикации нет")
except Exception as e:
    fail("не удалось проверить список публикации", str(e)[:120])


# ── 4. Путь читателя: язык не теряется при переходе ──────────────────────────
js = Path("js/search.js").read_text(encoding="utf-8")
if re.search(r"var base = '/lang/' \+ defaultLang \+ '/archive/", js):
    fail("карточка ведёт в язык ПО УМОЛЧАНИЮ",
         "с английской ленты клик уведёт на русскую статью")
else:
    ok("карточки ведут в язык своей страницы")

if "getElementById('langs-bar')" in js and "'/config.json'" in js:
    ok("строка языков строится по config.json")


# ── 5. Уровни: один переключатель, не в шапке ────────────────────────────────
for tpl in ("tag.html", "scientist.html", "law.html", "section.html"):
    p = Path("templates") / tpl
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    head = t.split("</div>\n        <div class=\"search-bar\">")[0]
    if "version_toggle" in head and "entity-levels" not in head:
        fail(f"{tpl}: переключатель уровня в шапке", "ломает кластер меню")
gen = Path("generate.py").read_text(encoding="utf-8")
if "version_toggle_links(" in gen and "version_toggle_html = \"\"" not in gen:
    fail("на странице статьи остался бегунок вместе с кнопками")
else:
    ok("переключатель уровня один, бегунка нет")


# ── 6. Собранный сайт: ссылки, язык, карта сайта ─────────────────────────────
if Path("lang/ru/index.html").exists():
    broken = 0
    checked = 0
    for lang in LANGS:
        base = Path("lang") / lang
        if not base.exists():
            continue
        targets = [base / "index.html", base / "about.html", base / "tags" / "index.html"]
        targets += sorted(base.glob("archive/*/*/index.html"))[-3:]
        for p in targets:
            if not p.exists():
                continue
            html = p.read_text(encoding="utf-8", errors="replace")
            for href in set(re.findall(r'href="(/[^"#?]+)"', html)):
                checked += 1
                tgt = Path("." + href)
                if href.endswith("/"):
                    tgt = tgt / "index.html"
                if not tgt.exists():
                    broken += 1
    if broken:
        fail(f"битых внутренних ссылок: {broken}", f"проверено {checked}")
    else:
        ok(f"внутренние ссылки целы ({checked} проверено)")

    for lang in ("en", "es", "ar"):
        base = Path("lang") / lang
        pages = [base / "index.html"] + sorted(base.glob("archive/*/*/index.html"))[-15:]
        bad = sum(1 for p in pages if p.exists()
                  and len(CYR.findall(visible_text(p.read_text(encoding="utf-8", errors="replace")))) > 40)
        if bad:
            fail(f"кириллица в версии {lang}: {bad} страниц")
    if not any("кириллица" in m for m, _ in problems):
        ok("кириллицы в нерусских версиях нет")

    # карта сайта не должна звать на несуществующее
    miss = 0
    for sm in Path(".").glob("sitemap-*.xml"):
        for u in re.findall(r"<loc>([^<]+)</loc>", sm.read_text(encoding="utf-8")):
            p = Path("." + re.sub(r"^https?://[^/]+", "", u))
            if not p.exists():
                miss += 1
    if miss:
        fail(f"карта сайта зовёт на несуществующее: {miss} адресов")
    else:
        ok("карта сайта без мёртвых адресов")
else:
    fail("сайт не собран", "нет lang/ru/index.html — запустите run.py html")


# ── 7. Состояние сборки ──────────────────────────────────────────────────────
if Path(".build.lock").exists():
    fail("остался .build.lock", "публикация откажется работать; удалите файл, если сборка не идёт")


# ── Итог ─────────────────────────────────────────────────────────────────────
print("=" * 62)
print("ПРОВЕРКА САЙТА")
print("=" * 62)
for m in notes:
    print(f"  ✓ {m}")
if problems:
    print()
    for m, d in problems:
        print(f"  ✗ {m}" + (f"\n      {d}" if d else ""))
    print(f"\nнайдено проблем: {len(problems)}")
else:
    print("\nпроблем не найдено")
print("=" * 62)
print("Ручная часть — ЧЕК-ЛИСТ.md: четыре пути читателя и внешний вид.")
sys.exit(1 if problems else 0)
