#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор климатических работ для дашборда Эль-Ниньо: список → run.py ids кусками.

Владелец 03.09: «все работы, которые касаются климата и этой темы, разбираем; для них
делаем английские версии, пока забудем про перевод; поехали сейчас, если окно позволяет».

Что здесь и почему не просто `run.py ids --ids-file`:
  · кусками по CHUNK: один вызов на 325 работ держит все страницы в памяти до конца и при
    любом сбое теряет всё; кусок — единица, которую не жалко повторить;
  · окно DeepSeek: перед каждым куском смотрим deepseek_peak_status(); в пик (цена x2)
    ждём, а не жжём — тот же приём, что у bulk_generate и deep_uplift --wait;
  · пропуск готовых: работа, у которой уже есть lang/ru/archive/*/<id>/advanced.html,
    в кусок не идёт — повторный запуск продолжает с места остановки;
  · пост-шаги (разметка вектором, понятия, формулы, машина знаний) — один раз, последним
    куском, а не после каждого: они идут по всему архиву и стоят минут;
  · замок `tree` на всё время: ежедневный прогон на тех же файлах не пускаем.

    python tools/enso/works_run.py data/enso/works-tier1.txt            # весь список
    python tools/enso/works_run.py data/enso/works-tier1.txt --limit 2  # проба
    python tools/enso/works_run.py ... --now                            # не ждать окна
"""
import argparse
import glob
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

CHUNK = 8
LOG = ROOT / "data" / "enso" / "works-log.txt"


def have():
    """Номера работ, уже разобранных полностью (есть advanced на русском — языке источника)."""
    out = set()
    for p in glob.glob(str(ROOT / "lang" / "ru" / "archive" / "*" / "*" / "advanced.html")):
        out.add(Path(p).parent.name.split("v")[0])
    return out


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def wait_window(now):
    from common import deepseek_peak_status
    while True:
        peak, hrs = deepseek_peak_status()
        if now or not peak:
            return
        log(f"⏸ пик DeepSeek (x2) — жду {hrs:.1f} ч")
        time.sleep(min(1800, max(60, int(hrs * 3600))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("list", help="файл со списком id, по одному на строку; # — комментарий")
    ap.add_argument("--limit", type=int, help="взять только первые N ещё не разобранных")
    ap.add_argument("--lang", default="en", help="языки перевода через запятую (по умолчанию en)")
    ap.add_argument("--now", action="store_true", help="не ждать не-пикового окна")
    ap.add_argument("--no-post", action="store_true", help="без пост-шагов и в последнем куске")
    a = ap.parse_args()

    ids = [l.strip() for l in Path(a.list).read_text(encoding="utf-8").splitlines()
           if l.strip() and not l.startswith("#")]
    done = have()
    todo = [i for i in ids if i.split("v")[0] not in done]
    have_n = len(ids) - len(todo)
    if a.limit:
        todo = todo[:a.limit]
    log(f"▶ {a.list}: в списке {len(ids)}, уже есть {have_n}, к разбору {len(todo)}, языки ru+{a.lang}")
    if not todo:
        return 0

    import runlock
    runlock.acquire("tree", f"enso works {a.list}")
    # Выкладка одна на прогон, а не после каждого куска: run.py публикует в конце любой
    # команды, и на прогоне из кусков это обход четверти миллиона файлов облака по кругу
    # плюс промежуточные состояния на проде. Та же правка, что в tools/topics.py.
    quiet = os.environ.get("B42_NO_PUBLISH") == "1"
    env = dict(os.environ, B42_RUN_ORIGIN="manual", PYTHONIOENCODING="utf-8",
               B42_NO_PUBLISH="1", SKIP_R2_BACKUP="1",
               B42_SKIP_DERIVED="1")   # копия, выкладка и производные файлы — по разу, в конце
    chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
    try:
        for n, ch in enumerate(chunks, 1):
            wait_window(a.now)
            last = n == len(chunks)
            cmd = [sys.executable, "run.py", "ids", *ch, "--lang", a.lang, "--allow-restricted"]
            if not last or a.no_post:
                cmd.append("--no-post")
            log(f"кусок {n}/{len(chunks)}: {' '.join(ch)}")
            t0 = time.time()
            rc = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
            got = sum(1 for i in ch if i.split("v")[0] in have())
            log(f"  кусок {n}: код {rc}, готово {got}/{len(ch)}, {int(time.time() - t0)} с")
    finally:
        runlock.release("tree")
    if not quiet:
        log("· выкладка одним разом")
        rc = subprocess.run([sys.executable, "run.py", "publish"], cwd=str(ROOT),
                            env=dict(env, B42_NO_PUBLISH="0", SKIP_R2_BACKUP="", B42_SKIP_DERIVED="")).returncode
        log(f"  выкладка: код {rc}")
    log(f"■ конец: разобрано всего {sum(1 for i in ids if i.split('v')[0] in have())}/{len(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
