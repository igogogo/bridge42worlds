#!/usr/bin/env python3
"""Короткая строка в канал: что сделано, по какой задаче. Одна команда, одно сообщение.

Владелец 13 августа: «пиши кратко, когда в канал идёт сообщение — по какой задаче
обновление, что сделано или изменено; если это вручную — не знаю, если автомат, он сам
знает, что писать».

Разница между этим инструментом и `status_tg.py`: тот шлёт готовые тексты про сбои
прогонов, а этот — одну строку про сделанную работу. Он же вызывается из git-хука после
коммита, поэтому ручная работа отчитывается сама и одинаково с автоматической: канал
показывает ленту изменений, а не выборку из того, о чём кто-то вспомнил написать.

Правило про длину не косметическое. Длинное сообщение в канале читают по диагонали, а
через неделю перестают открывать вовсе; одна строка держит внимание и остаётся полезной.

    python tools/say.py "Совет: голосование по вариантам"
    python tools/say.py --task 13 "Вес страницы: минус 13 МБ"
    python tools/say.py --auto            # взять последний коммит (так зовёт хук)
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 220          # столько влезает в уведомление телефона целиком


def last_commit():
    """Заголовок последнего коммита и ветка — то, что и есть «что изменено»."""
    def git(*a):
        r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return (r.stdout or "").strip()
    return git("log", "-1", "--pretty=%s"), git("rev-parse", "--abbrev-ref", "HEAD")


def send(text):
    """Через status_tg: там уже решены кодировка, ключи и молчание при их отсутствии.

    Текст передаём ФАЙЛОМ, а не аргументом: консоль Windows отдаёт аргументы в OEM-
    кодировке, и русские слова уже приезжали в канал кракозябрами (4 августа).
    """
    tmp = ROOT / "logs" / "say.txt"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(text, encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"),
                        "--file", str(tmp)], cwd=ROOT, timeout=120)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="что сделано, одной строкой")
    ap.add_argument("--task", help="номер задачи, если работа по ней")
    ap.add_argument("--auto", action="store_true", help="взять заголовок последнего коммита")
    ap.add_argument("--dry", action="store_true", help="показать, но не отправлять")
    args = ap.parse_args()

    branch = ""
    text = args.text or ""
    if args.auto:
        subj, branch = last_commit()
        text = text or subj
        # Сборочные и служебные коммиты в канал не идут: они не «что изменено», а
        # «переложили файлы». Иначе лента изменений тонет в пересборках.
        if not text or text.startswith(("Merge ", "Пересборка", "wip", "WIP")):
            return 0
    if not text:
        print("нужен текст или --auto")
        return 2

    head = "🔧" if not args.task else f"🔧 задача {args.task}"
    line = f"{head} {text}".strip()[:LIMIT]
    if branch and branch != "main":
        line += f"\n<i>ветка {branch}</i>"

    if args.dry:
        print(line)
        return 0
    return 0 if send(line) else 1


if __name__ == "__main__":
    sys.exit(main())
