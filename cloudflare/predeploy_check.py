"""Замок выкладки Worker: не даёт выложить его из главной папки и из устаревшей копии.

Зачем. `wrangler deploy` выкладывает тот `worker.js`, который лежит рядом с ним, а копий
теперь две: главная папка и рабочая копия DevOps. Дважды за сутки вышло так, что моя
выкладка молча уезжала обратно — кто-то деплоил из главной папки следом, и живой код
возвращался к её версии. Заметить это можно только по поведению сайта, а не по ошибке:
`wrangler` бодро пишет «Uploaded» в обоих случаях.

Правило 6б в ПРАВИЛА-РАБОТЫ.md говорит то же словами. Здесь оно кодом — потому что
памятка не спасла ни в первый раз, ни во второй.

Проверяем три вещи:
  1. Не главная ли это папка (выкладывает только DevOps из своей копии).
  2. Не отстала ли копия от origin/main — иначе выложим старое поверх нового.
  3. Нет ли незакоммиченных правок в cloudflare/ — выложить то, чего нет в git,
     значит потерять возможность понять, что именно сейчас работает у читателей.

Обойти сознательно: B42_DEPLOY_OK=1. Это защита от случайности, а не от намерения —
если вы её обходите, вы знаете, что делаете, и отвечаете за результат сами.

Запуск (сам, из wrangler-хука или руками перед деплоем):
    python cloudflare/predeploy_check.py
"""
import os, sys, subprocess
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MAIN_DIR = Path(os.environ.get("B42_MAIN_DIR",
                               r"C:\Users\nadez\PycharmProjects\bridge42worlds")).resolve()


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8", "replace").strip(), r.returncode


def fail(title, *lines):
    print()
    print(f"==> СТОП: {title}")
    for l in lines:
        print(f"    {l}")
    print()
    print("    Осознанно обойти: B42_DEPLOY_OK=1")
    print()
    sys.exit(1)


def main():
    if os.environ.get("B42_DEPLOY_OK") == "1":
        print("замок выкладки снят вручную (B42_DEPLOY_OK=1)")
        return 0

    # 1. Главная папка — не место для выкладки.
    if ROOT.resolve() == MAIN_DIR:
        fail("выкладка Worker из главной папки.",
             "Здесь живут сборка и слияния, а выкладывает Worker только DevOps",
             "из своей копии (ПРАВИЛА-РАБОТЫ.md, правило 6б).",
             "Дважды за сутки выкладка отсюда молча откатывала чужую работу.")

    # 2. Копия не должна отставать от main: иначе выложим старое поверх нового.
    subprocess.run(["git", "fetch", "origin", "--quiet"], cwd=ROOT, capture_output=True)
    behind, code = git("rev-list", "--count", "HEAD..origin/main")
    if code == 0 and behind.isdigit() and int(behind) > 0:
        fail(f"копия отстала от origin/main на {behind} коммит(ов).",
             "Выкладка сейчас вернёт читателям старый Worker.",
             "Сначала: git merge origin/main — потом деплой.")

    # 3. Незакоммиченное в cloudflare/ — выкладываем то, чего нет в истории.
    dirty, _ = git("status", "--porcelain", "--", "cloudflare")
    if dirty:
        files = [l[3:] for l in dirty.splitlines()][:5]
        fail("в cloudflare/ есть незакоммиченные правки.",
             "Выложить их — значит через день не понять, что именно работает",
             "у читателей и почему. Сначала коммит:",
             *[f"  {f}" for f in files])

    print("замок выкладки: всё чисто, можно деплоить")
    return 0


if __name__ == "__main__":
    sys.exit(main())
