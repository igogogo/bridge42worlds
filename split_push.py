"""Пуш большого прогона по частям.

Полный реген трогает ~50 тысяч файлов. Одним коммитом такое не уходит: GitHub рвёт соединение
по таймауту (HTTP 408 / unexpected disconnect). Поэтому режем по областям — код и данные
отдельно, каждый язык отдельно — и пушим после каждого коммита. Части независимы: если одна
не ушла, остальные уже на месте, и достаточно повторить упавшую.

Запуск:
    python split_push.py "Заголовок коммита"        # весь цикл
    python split_push.py --dry "Заголовок"          # только показать план
"""
import subprocess
import time
import sys
from pathlib import Path

# Порядок важен: сперва код и данные (по ним читается всё остальное), затем языки.
# lang/en идёт последним и режется надвое — там 17 тысяч страниц авторов.
PARTS = [
    ("код, данные и новые страницы раздела",
     ["*.py", "*.html", "js", "css", "data", "content-manager", ".gitignore", "config.json"]),
    ("страницы: русская версия", ["lang/ru"]),
    ("страницы: испанская версия", ["lang/es"]),
    ("страницы: арабская версия", ["lang/ar"]),
    ("страницы: английская версия, кроме авторов",
     ["lang/en/archive", "lang/en/tags", "lang/en/laws", "lang/en/scientists",
      "lang/en/sections", "lang/en/graph", "lang/en/analytics", "lang/en/index.html",
      "lang/en/about.html", "lang/en/favorites.html", "lang/en/data"]),
    ("страницы: английские авторы", ["lang/en"]),
    ("остальное", ["."]),
]

FOOTER = "\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>"


def run(args, check=True, wait_lock=True, tries=60):
    """Запускает git, пережидая чужой index.lock.

    PyCharm при 50 тысячах изменений подолгу держит индекс, и коммит падает с «index.lock:
    File exists». Лок при этом живой, удалять его нельзя — можно потерять чужую работу.
    Поэтому просто ждём: проверяем раз в 10 секунд, пока не освободится."""
    for attempt in range(tries):
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stderr or "") + (r.stdout or "")
        if r.returncode == 0 or not wait_lock or "index.lock" not in out:
            if check and r.returncode != 0:
                print(out.strip()[:600])
            return r
        if attempt == 0:
            print("   ждём: индекс занят другим процессом (обычно PyCharm)…", flush=True)
        time.sleep(10)
    print("   индекс так и не освободился")
    return r


def staged_count():
    r = run(["git", "diff", "--cached", "--name-only"], check=False)
    return len([x for x in (r.stdout or "").splitlines() if x.strip()])


def main():
    argv = [a for a in sys.argv[1:] if a != "--dry"]
    dry = "--dry" in sys.argv
    if not argv:
        print('нужен заголовок: python split_push.py "Заголовок"')
        return 1
    title = argv[0]

    total = len(PARTS)
    for i, (name, paths) in enumerate(PARTS, 1):
        existing = [p for p in paths if p in (".", "*.py", "*.html") or Path(p).exists()]
        if not existing:
            continue
        run(["git", "add", "--"] + existing, check=False)
        n = staged_count()
        if not n:
            print(f"[{i}/{total}] {name}: нечего коммитить")
            continue
        msg = f"{title} [{i}/{total}: {name}]{FOOTER}"
        print(f"[{i}/{total}] {name}: файлов {n}", flush=True)
        if dry:
            run(["git", "reset"], check=False)
            continue
        r = run(["git", "commit", "-m", msg])
        if r.returncode != 0:
            print("  ✗ коммит не прошёл")
            return 1
        r = run(["git", "push"])
        if r.returncode != 0:
            print(f"  ✗ пуш части {i} не прошёл — повторите: git push")
            return 1
        print(f"  ✔ отправлено", flush=True)

    left = run(["git", "status", "--porcelain"], check=False).stdout.strip()
    print("осталось незакоммиченного:", len(left.splitlines()) if left else 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
