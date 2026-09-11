# -*- coding: utf-8 -*-
"""Полная цепочка для ОДНОЙ работы не из arXiv: от разбора до сайта.

Владелец 11.09.2026: «прогони одну работу нашим механизмом, но целиком по всем шагам,
чтобы и разметить и так далее. Можно без преформирования понятий, но уж точно на текущих
кандидатах — потом обработаем и переразметим. Заодно отточишь ещё один пайплайн, потом его
сольём в общий».

ЧТО ЗДЕСЬ И ЧЕГО НЕТ

Ежедневный конвейер (tools/full_run.py) делает две разные работы сразу: РАСТИТ реестр
понятий по всему корпусу и ОБРАБАТЫВАЕТ статьи дня. Одной работе нужна только вторая
половина. Поэтому здесь взяты те же шаги и теми же командами — копия, а не пересказ, чтобы
при слиянии обратно ничего не разошлось, — но выброшено всё, что растит реестр: добыча,
анатомия, рождение понятий, двойники, константы, супер-группы, живые справочники, граф,
страницы понятий и формул. Они идут по всему архиву и стоят часов; новой работе они не
нужны, а реестр всё равно пересоберётся ближайшим ежедневным прогоном.

Разметка при этом НЕ пропускается: работа размечается по СЕГОДНЯШНЕМУ реестру. Новых
понятий из неё не родится — это и просил владелец.

    python tools/outside/chain.py 2607.90001
    python tools/outside/chain.py 2607.90001 --from related   продолжить с шага
    python tools/outside/chain.py 2607.90001 --dry            показать план
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

PY = sys.executable
ML = ROOT.parent / "b42-ml"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def find_date(aid):
    """День работы — по папке в архиве."""
    for p in (ROOT / "lang" / "ru" / "archive").glob(f"*/{aid}"):
        if (p / "data.json").exists():
            return p.parent.name
    return ""


def plan(aid, date_str):
    """Шаги цепочки. soft — неудача не валит прогон.

    Порядок повторяет ежедневный: разметка → связность → страницы → облако → выкладка.
    """
    month = date_str[:7]
    return [
        # ── разметка по нынешнему реестру ────────────────────────────────
        # Поле нужно ДО разметки: без вектора работы retag честно отвечает
        # «статьи нет в корпусе» — на этом спотыкались 09.09 с работой OpenAI.
        ("field", [PY, "field_build.py", "--ours", "--months", month, "--max-cost", "0.5"],
         ML, True),
        ("retag", [PY, "tools/retag_hub.py", "--live", aid, "--apply",
                   "--thr", "0.50", "--margin", "0.12"], ROOT, False),
        ("apply", [PY, "tools/wave5_apply.py", "--apply", "--articles-only"], ROOT, False),
        ("highlight", [PY, "tools/highlight_concepts.py", "--tiers",
                       "simple,popular,advanced", "--ids", aid], ROOT, True),
        ("formulas", [PY, "tools/fix_inline_math.py", "--ids", aid], ROOT, True),
        # ── связность ────────────────────────────────────────────────────
        ("related", [PY, "tools/vector_links_local.py"], ROOT, True),
        ("cited", [PY, "tools/cited_ours.py"], ROOT, True),
        ("carousel", [PY, "tools/carousel_frames.py", "--all"], ROOT, True),
        ("recommend", [PY, "tools/recommend.py", aid], ROOT, True),
        # ── страницы ─────────────────────────────────────────────────────
        ("html", [PY, "run.py", "html", "--only", aid], ROOT, False),
        ("lang-pages", [PY, "tools/lang_pages.py"], ROOT, True),
        ("authors", [PY, "-c", "import sys; sys.path.insert(0,'.'); "
                     "import generate as G; G.update_all_authors()"], ROOT, True),
        # ── облако ───────────────────────────────────────────────────────
        ("vec-ours", [PY, "embeddings_export.py"], ROOT, True),
        ("vec-push", [PY, "cloudflare/vector_build.py"], ROOT, True),
        ("cards-sync", [PY, "cloudflare/cards_sync.py", "--apply"], ROOT, True),
        ("side-sync", [PY, "cloudflare/frame_sync.py", "--apply"], ROOT, True),
        # ── выкладка и проверка ──────────────────────────────────────────
        ("deploy", [PY, "cloudflare/deploy_r2.py"], ROOT, False),
        ("lic-audit", [PY, "tools/license_audit.py", "--fix"], ROOT, True),
    ]


def main():
    ap = argparse.ArgumentParser(description="Полная цепочка для одной работы не из arXiv")
    ap.add_argument("aid", help="номер работы, например 2607.90001")
    ap.add_argument("--from", dest="start", help="начать с этого шага")
    ap.add_argument("--dry", action="store_true", help="показать план и выйти")
    a = ap.parse_args()

    date_str = find_date(a.aid)
    if not date_str:
        raise SystemExit(f"⛔ {a.aid}: в архиве нет папки с data.json — сперва приём и разбор "
                         f"(tools/outside/intake.py, затем run.py ids {a.aid})")
    steps = plan(a.aid, date_str)
    if a.start:
        names = [s[0] for s in steps]
        if a.start not in names:
            raise SystemExit(f"⛔ шага «{a.start}» нет. Есть: {', '.join(names)}")
        steps = steps[names.index(a.start):]

    print(f"работа {a.aid} · день {date_str} · шагов {len(steps)}")
    if a.dry:
        for n, cmd, cwd, soft in steps:
            print(f"  {n:12} {'мягкий' if soft else 'жёсткий'}  {' '.join(str(x) for x in cmd[1:])[:90]}")
        return 0

    # ЗАМОК НА ВСЮ ЦЕПОЧКУ, как у ежедневного конвейера. Без него шаги берут его
    # поодиночке, и цепочка спотыкается о чужой прогон посреди дороги — так и вышло
    # на первом запуске 11.09: шаг html встал, потому что предыдущая генерация ещё
    # доделывала агрегаты по пяти языкам. Занят — честно говорим и не начинаем.
    # Занят чужим прогоном — acquire() сам всё скажет и выйдет. Вернул False — значит
    # замок УЖЕ наш (цепочку позвали изнутри другого прогона), и это не отказ.
    # Своим подпроцессам замок не мешает: он передаётся им через окружение, а снимается
    # сам при выходе (atexit внутри acquire).
    from tools import runlock
    runlock.acquire("tree", f"внешняя работа {a.aid}")

    t0 = time.time()
    failed = []
    for n, cmd, cwd, soft in steps:
        log(f"▶ {n}")
        s = time.time()
        try:
            rc = subprocess.run(cmd, cwd=str(cwd),
                                env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8",
                                         B42_DEPLOY_OK="1"),
                                timeout=4 * 3600).returncode
        except subprocess.TimeoutExpired:
            rc = -1
            log(f"  ⏱ {n}: превышено время")
        dt = int(time.time() - s)
        if rc == 0:
            log(f"✓ {n} ({dt // 60} мин {dt % 60} с)")
            continue
        failed.append(n)
        log(f"{'○' if soft else '✗'} {n}: код {rc} ({dt // 60} мин {dt % 60} с)")
        if not soft:
            log(f"═══ ОСТАНОВ на жёстком шаге {n} ═══")
            return 1
    total = int(time.time() - t0)
    log(f"═══ ЦЕПОЧКА ПРОЙДЕНА за {total // 60} мин; мягких неудач: {len(failed)}"
        + (f" ({', '.join(failed)})" if failed else "") + " ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
