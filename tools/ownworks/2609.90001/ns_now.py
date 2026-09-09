# -*- coding: utf-8 -*-
"""Довести работу 2609.90001 до сайта, не дожидаясь длинных пересборок.

Владелец 09.09: «можешь это делать уже сейчас, пусть там учёные пересобираются или нет».

ПОРЯДОК ВАЖЕН, И ЭТО ГЛАВНОЕ, ЧТО ЗДЕСЬ ЗАПИСАНО. Разметка вектором берёт список статей из
lang/ru/articles-index.json, а индекс пересобирает только run.py html. Пока сборка не прошла,
новая работа для разметки не существует: 09.09 шаг честно ответил «статьи 2609.90001 нет в
корпусе», хотя вектор её уже знал. Поэтому сборка идёт ДВАЖДЫ:

  1. вектор и поле (без замка, можно параллельно с чужой заливкой);
  2. сборка без выкладки — она заводит работу в индекс;
  3. разметка понятиями, запись в статью, подсветка терминов, граф, связи;
  4. сборка с выкладкой — страницы уже с понятиями, run.py публикует их сам;
  5. неспешное: страницы понятий, облако, полная пересборка.

ДВЕ ВЫКЛАДКИ ОДНОВРЕМЕННО НЕЛЬЗЯ: обе пишут cloudflare/.r2-manifest.json, и вторая затрёт
учёт первой. Поэтому шаги 2 и 4 ждут замка дерева, а не идут напролом с --ignore-lock.
"""
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
ML = ROOT.parent / "b42-ml"
LOCK = ROOT / "data" / "locks" / "tree.lock"
AID = "2609.90001"
PY = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", B42_DEPLOY_OK="1", B42_LEAD="1")
T = lambda *a: [PY, "-X", "utf8", *a]


def run(name, cmd, cwd=ROOT, soft=True, timeout=10 * 3600, env=None):
    t0 = time.time()
    print(f"\n▶ {name}: {' '.join(cmd)}")
    log = ROOT / "logs" / f"ns-{name}-0909.log"
    with log.open("w", encoding="utf-8") as fo:
        r = subprocess.run(cmd, cwd=str(cwd), env=env or ENV, stdout=fo,
                           stderr=subprocess.STDOUT, timeout=timeout)
    print(f"  {'✓' if r.returncode == 0 else '✗'} {name} ({int(time.time() - t0)} с, код {r.returncode}) → {log.name}")
    if r.returncode and not soft:
        sys.exit(f"стоп на шаге {name}")


def wait_lock():
    """Дождаться, пока замок дерева освободится. Мёртвый замок не считаем: его снимет runlock."""
    t0 = time.time()
    while LOCK.exists():
        d = dict(ln.split("=", 1) for ln in LOCK.read_text(encoding="utf-8").splitlines() if "=" in ln)
        pid = int(d.get("pid") or 0)
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ 'Y' }} else {{ 'N' }}"],
                             capture_output=True, text=True).stdout.strip()
        if not out.endswith("Y"):
            break
        if time.time() - t0 > 3 * 3600:
            sys.exit("замок держат больше трёх часов — не лезу")
        print(f"  ждём замок: pid {pid} · {d.get('what', '')}", flush=True)
        time.sleep(60)
    if t0 != time.time():
        print(f"замок свободен (ждали {int((time.time() - t0) / 60)} мин)")


only = set(sys.argv[1:])
step = lambda n: not only or n in only

# ── 1. вектор и поле: без замка, можно параллельно ─────────────────────────
if step("vec"):
    run("vec-ours", T("embeddings_export.py"))
    run("vec-push", T("cloudflare/vector_build.py"))
    run("field", T("field_build.py", "--ours", "--months", "2026-09", "--max-cost", "0.5"), cwd=ML)

# ── 2. сборка без выкладки: работа попадает в индекс ───────────────────────
if step("index"):
    wait_lock()
    run("html-index", T("run.py", "html", "--only", AID), soft=False,
        env=dict(ENV, B42_NO_PUBLISH="1"))

# ── 3. разметка понятиями ──────────────────────────────────────────────────
if step("mark"):
    run("retag", T("tools/retag_hub.py", "--live", AID, "--apply", "--thr", "0.50", "--margin", "0.12"), soft=False)
    run("apply", T("tools/wave5_apply.py", "--apply", "--articles-only"))
    run("highlight", T("tools/highlight_concepts.py", "--ids", AID, "--tiers", "simple,popular,advanced"))
    run("graph", T("tools/concepts_graph_export.py"))
    run("related", T("tools/vector_links_local.py"))
    run("cited", T("tools/cited_ours.py"))

# ── 4. сборка с выкладкой: страницы уже с понятиями ────────────────────────
if step("publish"):
    run("lic-audit", T("tools/license_audit.py", "--fix"))
    wait_lock()
    run("html-only", T("run.py", "html", "--only", AID), soft=False)   # публикует сам
    print("\nРАБОТА НА САЙТЕ: "
          f"https://bridge42worlds.academy/lang/ru/archive/2026-09-08/{AID}/index.html", flush=True)

# ── 5. неспешное ───────────────────────────────────────────────────────────
if step("rest"):
    run("pages-c", T("concepts_pages.py"))
    run("context", T("cloudflare/context_build.py"))
    run("cloud-vec", T("tools/concepts_to_vectorize.py", "--apply"))
    run("cards-sync", T("cloudflare/cards_sync.py", "--apply"))
    run("side", T("cloudflare/frame_sync.py", "--apply"))
    run("cloud-d1", T("cloudflare/concepts_sync.py"))
    wait_lock()
    run("html", T("run.py", "html"), soft=False)
    print("\nготово целиком")
