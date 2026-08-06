#!/usr/bin/env python3
"""Отчёт «сделано за спринт» — собирается сам, из истории работы.

Замысел владельца: круг замыкается не решением, а отчётом. Совет проголосовал →
это попало в план спринта → через неделю видно, что из этого вышло → следующая
повестка растёт из реальности, а не из желаний.

Ручной отчёт для этого не годится: его пишут по памяти и в свою пользу. Поэтому
берём то, что не врёт, — историю правок за неделю. У нас сообщения к правкам пишутся
человеческим языком и объясняют ПОЧЕМУ, а не что: из них отчёт читается прямо.

Что делает:
  · берёт окно спринта из файла заседания;
  · собирает правки за это окно (только осмысленные — слияния и мелочь отсекает);
  · раскладывает их по вопросам повестки: что к чему относится;
  · пишет в sprint.done, а к каждому принятому вопросу — outcome.

Что НЕ делает: не решает, выполнено ли обещание. Отмечает, что было сделано рядом
с вопросом, а вывод «сделали или нет» остаётся человеку — иначе отчёт начнёт
подтверждать сам себя.

Запуск:
    python council_sprint.py 2026-08-04            # собрать и записать
    python council_sprint.py 2026-08-04 --dry      # показать, не записывая
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "data" / "council"

# Правки, которые в отчёт не идут: они про порядок в репозитории, а не про проект.
SKIP_PREFIX = ("Merge branch", "Merge remote", "Доска:", "Отчёт", "Уборка", "Контекст")

SYSTEM = """Ты — секретарь наблюдательного совета. Тебе дан список правок проекта за неделю
и список вопросов, которые совет принял к работе.

Задача: разложить правки по вопросам и сказать человеческим языком, что сделано.

Требования:
— НЕ решай, выполнено обещание или нет. Твоё дело — показать, что делалось рядом
  с вопросом; вывод сделает человек.
— правку, не относящуюся ни к одному вопросу, отправь в «прочее» — не выбрасывай:
  совет должен видеть всю работу, а не только ту, что он заказывал;
— пиши коротко и по делу, без канцелярита, по-русски;
— не выдумывай сделанного, чего нет в списке правок.

Ответ строго JSON:
{"по вопросам": [{"id": "a1", "сделано": ["строка", "строка"]}],
 "прочее": ["строка", "строка"]}
Никакого текста вне JSON."""


def git_log(since, until):
    """История за окно. Берём из ГЛАВНОЙ папки: там живёт main, куда всё сливается,
    а моя ветка знает только свою часть работы."""
    # Обязательно из ГЛАВНОЙ папки, и не только ради полноты истории: в рабочем дереве
    # (worktree) тот же запрос идёт 38 секунд против 4 — замерено. Плюс на холодном
    # кэше первый запрос бывает вдесятеро медленнее, отсюда щедрый предел ожидания.
    main = ROOT.parent / "bridge42worlds"
    cwd = main if (main / ".git").exists() else ROOT
    # Берём ПОСЛЕДНИЕ правки и фильтруем по дате сами. Штатный фильтр git по дате
    # заставляет его обойти всю историю и на нашем репозитории не укладывается
    # и в минуту (проверено), а последние четыре сотни отдаются за треть секунды.
    # Четырёхсот с запасом хватает на неделю: у нас редко бывает больше сотни за день.
    try:
        out = subprocess.run(
            ["git", "log", "-n", "400", "--pretty=%h|%ad|%s", "--date=short", "--no-merges"],
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=180).stdout
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  ⚠️ история не прочиталась: {e}")
        return []
    rows, oldest = [], None
    for line in (out or "").splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        h, day, subj = parts[0].strip(), parts[1].strip(), parts[2].strip()
        oldest = day if oldest is None else min(oldest, day)
        if not (since <= day <= until):
            continue
        if subj.startswith(SKIP_PREFIX):
            continue
        rows.append({"hash": h, "day": day, "subject": subj})
    # Если четырёхсот не хватило и окно начинается раньше самой старой из них —
    # говорим об этом, а не делаем вид, что за начало недели ничего не делали.
    if oldest and since < oldest:
        print(f"  ⚠️ последние 400 правок доходят только до {oldest}, "
              f"а спринт начинается {since} — начало недели в отчёт не попало")
    return rows


def spread(commits, accepted):
    from common import chat, clean_json
    payload = {
        "правки": [c["subject"] for c in commits],
        "вопросы совета": [{"id": a.get("id"), "title": a.get("title")} for a in accepted],
    }
    resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False, indent=1),
                system=SYSTEM)
    text = (resp.choices[0].message.content or "").strip()
    return json.loads(clean_json(text))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args:
        print("укажи дату заседания: python council_sprint.py 2026-08-04")
        return 1
    path = DIR / f"{args[0]}.json"
    if not path.exists():
        print(f"нет заседания {args[0]}")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    sprint = data.get("sprint") or {}
    since, until = sprint.get("from"), sprint.get("to")
    if not (since and until):
        print("у заседания не задано окно спринта (sprint.from / sprint.to)")
        return 1

    commits = git_log(since, until)
    print(f"правок за {since} — {until}: {len(commits)}")
    for c in commits[:12]:
        print(f'  · {c["subject"][:88]}')
    if len(commits) > 12:
        print(f"  … и ещё {len(commits) - 12}")
    if not commits:
        print("за окно спринта правок нет — отчёт пустой, это тоже результат")
        return 0

    accepted = [a for a in (data.get("agenda") or []) if a.get("decision") == "принято"]
    print(f"принятых вопросов: {len(accepted)}")

    try:
        res = spread(commits, accepted)
    except Exception as e:
        print(f"⚠️ разложить по вопросам не вышло ({type(e).__name__}: {e}) — "
              f"кладу правки в отчёт списком, без разбора по вопросам")
        res = {"по вопросам": [], "прочее": [c["subject"] for c in commits]}

    by_id = {a.get("id"): a for a in data.get("agenda") or []}
    done_all = []
    for row in res.get("по вопросам") or []:
        item = by_id.get(row.get("id"))
        lines = row.get("сделано") or []
        if not lines:
            continue
        done_all += lines
        print(f'\n· {item.get("title","") if item else row.get("id")}')
        for l in lines:
            print(f"    {l}")
        if item and not dry:
            # Не «выполнено», а «что делалось рядом»: вывод остаётся человеку.
            item["outcome"] = "; ".join(lines)
    other = res.get("прочее") or []
    if other:
        print("\n· прочее (совет этого не заказывал, но работа шла)")
        for l in other[:10]:
            print(f"    {l}")
        done_all += other

    if dry:
        print("\n[сухой прогон] ничего не записано")
        return 0
    data.setdefault("sprint", {})["done"] = done_all
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nзаписано в отчёт: {len(done_all)} строк → {path.relative_to(ROOT)}")
    print("дальше: python council_build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
