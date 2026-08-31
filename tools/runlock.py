#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замок на дерево и на облако: два прогона на одних файлах не пускаем.

ПОЧЕМУ ЭТО ЕСТЬ. 31 августа на одном дереве сошлись ежедневный прогон, недельный
и два ремонтных скрипта: ДВА `concepts_pages.py` писали одни и те же восемнадцать
тысяч страниц, а `frame_sync.py` шёл к `DELETE FROM article_side` в тот момент,
когда рядом работал недельный. Разошлось без потерь по случайности. До этого, в
ночь на 31 июля, две сборки уже сходились на дереве и стоили пятого языка.

Владелец 31.08: «надо ставить защиту в логике от гонок сразу — обычно нам такие
штуки потом плодят ошибки». Это она.

ОТКУДА ВЗЯТО. Не новый механизм: `run.py` держал `.build.lock` с pid и умел не
верить мёртвому pid. Здесь то же самое, но с именами и на все долгие писатели —
чтобы правило было одно, а не по замку на инструмент.

ПРАВИЛА.
  · Замок именованный: `tree` — всё, что пишет lang/ и data/; `d1` — всё, что
    пишет в облачную базу. Имён нарочно мало: чем их больше, тем легче
    разминуться там, где разминаться нельзя.
  · Чужой ЖИВОЙ процесс — отказ с именем держателя и временем. Не ждём: ожидание
    в очереди прячет ошибку планирования, а нам нужно её видеть.
  · Чужой МЁРТВЫЙ процесс — замок ничей, забираем и говорим об этом. Требовать
    ручной уборки нельзя: появится привычка удалять замок не глядя.
  · Свои дети замок НЕ берут: родитель передаёт им B42_LOCKS через окружение.
    Иначе шаг конвейера сам себя и остановил бы.

    with runlock.hold("tree", "недельный прогон"):
        ...

    python tools/runlock.py --status      кто что держит
    python tools/runlock.py --break tree  снять замок руками (скажет, чей он был)
"""
import argparse
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "locks"
ENV = "B42_LOCKS"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _alive(pid):
    """Жив ли процесс. На Windows os.kill(pid, 0) не работает — спрашиваем систему."""
    if not pid:
        return False
    if os.name == "nt":
        import subprocess
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                 capture_output=True, text=True, timeout=15).stdout
        except Exception:
            return True          # не смогли спросить — считаем живым, так безопаснее
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _path(name):
    return DIR / f"{name}.lock"


def _read(name):
    p = _path(name)
    if not p.exists():
        return None
    try:
        raw = p.read_text(encoding="utf-8").strip().split("\n")
    except OSError:
        return None
    d = {}
    for line in raw:
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d or None


def _mine(name):
    return name in (os.environ.get(ENV) or "").split(",")


def _age(started):
    try:
        return int(time.time() - float(started))
    except Exception:
        return 0


def _hms(sec):
    return f"{sec // 3600} ч {sec % 3600 // 60} мин" if sec >= 3600 else f"{sec // 60} мин"


def acquire(name, what=""):
    """Взять замок. Вернёт True — взяли, False — он уже наш (родительский)."""
    if _mine(name):
        return False
    DIR.mkdir(parents=True, exist_ok=True)
    old = _read(name)
    if old:
        pid = int(old.get("pid") or 0)
        if pid and pid != os.getpid() and _alive(pid):
            print(f"\n⛔ Замок «{name}» занят.")
            print(f"   держит: {old.get('what') or 'неизвестно'} · pid {pid} · "
                  f"идёт {_hms(_age(old.get('started')))}")
            print("   Два прогона на одних файлах дают смесь версий — так мы уже")
            print("   теряли пятый язык. Дождитесь конца или остановите тот процесс.")
            print(f"   Снять замок вручную: python tools/runlock.py --break {name}\n")
            sys.exit(1)
        if pid:
            print(f"· замок «{name}» был ничей (pid {pid} мёртв) — забираю")
    _path(name).write_text(
        f"pid={os.getpid()}\nstarted={time.time()}\n"
        f"what={what or ' '.join(sys.argv[:2])}\n", encoding="utf-8")
    held = [x for x in (os.environ.get(ENV) or "").split(",") if x]
    os.environ[ENV] = ",".join(held + [name])
    # СНИМАЕМ САМИ, а не надеемся на дисциплину вызывающего. acquire() зовут в начале
    # main(), и без этого замок оставался лежать после нормального выхода: следующий
    # прогон каждый раз сообщал «замок был ничей». Хуже другое — система однажды
    # выдаст тот же pid другому процессу, и мёртвый замок станет живым.
    import atexit
    atexit.register(release, name)
    return True


def release(name):
    """Снять свой замок. Чужой не трогаем: он мог достаться другому прогону."""
    d = _read(name)
    if d and int(d.get("pid") or 0) == os.getpid():
        _path(name).unlink(missing_ok=True)
    held = [x for x in (os.environ.get(ENV) or "").split(",") if x and x != name]
    os.environ[ENV] = ",".join(held)


@contextmanager
def hold(name, what=""):
    took = acquire(name, what)
    try:
        yield
    finally:
        if took:
            release(name)


def main():
    ap = argparse.ArgumentParser(description="Замки прогонов")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--break", dest="brk", metavar="ИМЯ")
    a = ap.parse_args()
    if a.brk:
        d = _read(a.brk)
        if not d:
            print(f"замка «{a.brk}» нет")
            return 0
        pid = int(d.get("pid") or 0)
        print(f"снимаю «{a.brk}»: {d.get('what')} · pid {pid} · "
              f"{'ЖИВ' if _alive(pid) else 'мёртв'} · идёт {_hms(_age(d.get('started')))}")
        _path(a.brk).unlink(missing_ok=True)
        return 0
    if not DIR.exists() or not any(DIR.glob("*.lock")):
        print("замков нет — дерево и облако свободны")
        return 0
    for p in sorted(DIR.glob("*.lock")):
        d = _read(p.stem) or {}
        pid = int(d.get("pid") or 0)
        print(f"{p.stem}: {d.get('what')} · pid {pid} · "
              f"{'жив' if _alive(pid) else 'МЁРТВ — замок ничей'} · "
              f"идёт {_hms(_age(d.get('started')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
