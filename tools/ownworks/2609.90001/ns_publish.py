# -*- coding: utf-8 -*-
"""Вынести работу 2609.90001 на сайт: страницы, разметка понятиями, вектор, облако, выкладка.

Порядок — тот же, каким конвейер проводит статью дня, только для одной работы. Замок дерева
берёт сам run.py; запускать после конца недельного прогона.

  1. html --only         страницы работы на пяти языках + индексы и агрегаты
  2. vec-ours + vec-push вектор работы в пространство «ours» (из английской аннотации)
  3. field --ours        вектор в поле b42-ml, иначе разметка ответит «нет в корпусе»
  4. retag --live        понятия вектором → wave5_apply в data.json
  5. highlight           пометки понятий в текстах трёх уровней
  6. html --only         страницы заново, уже с понятиями
  7. context / cards / side   KV-контекст для бота, карточки в D1, обвязка
  8. lic-audit --fix     ключ lic:* в KV — воркер вырежет чужое при отдаче
  9. deploy              дельта в R2
"""
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
ML = ROOT.parent / "b42-ml"
AID = "2609.90001"
PY = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", B42_DEPLOY_OK="1", B42_LEAD="1")


def run(name, cmd, cwd=ROOT, soft=False, timeout=7200):
    t0 = time.time()
    print(f"\n▶ {name}: {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(cwd), env=ENV, timeout=timeout)
    print(f"  {'✓' if r.returncode == 0 else '✗'} {name} ({int(time.time() - t0)} с, код {r.returncode})")
    if r.returncode and not soft:
        sys.exit(f"стоп на шаге {name}")
    return r.returncode


steps = [
    ("html-1", [PY, "-X", "utf8", "run.py", "html", "--only", AID], ROOT, False),
    ("vec-ours", [PY, "-X", "utf8", "embeddings_export.py"], ROOT, True),
    ("vec-push", [PY, "-X", "utf8", "cloudflare/vector_build.py"], ROOT, True),
    ("field", [PY, "-X", "utf8", "field_build.py", "--ours", "--months", "2026-09", "--max-cost", "0.5"], ML, True),
    ("retag", [PY, "-X", "utf8", "tools/retag_hub.py", "--live", AID, "--apply", "--thr", "0.50", "--margin", "0.12"], ROOT, True),
    ("apply", [PY, "-X", "utf8", "tools/wave5_apply.py", "--apply", "--articles-only"], ROOT, True),
    ("highlight", [PY, "-X", "utf8", "tools/highlight_concepts.py", "--ids", AID, "--tiers", "simple,popular,advanced"], ROOT, True),
    ("html-2", [PY, "-X", "utf8", "run.py", "html", "--only", AID], ROOT, False),
    ("context", [PY, "-X", "utf8", "cloudflare/context_build.py"], ROOT, True),
    ("cards", [PY, "-X", "utf8", "cloudflare/cards_sync.py", "--apply"], ROOT, True),
    ("side", [PY, "-X", "utf8", "cloudflare/frame_sync.py", "--apply"], ROOT, True),
    ("lic-audit", [PY, "-X", "utf8", "tools/license_audit.py", "--fix"], ROOT, True),
    ("deploy", [PY, "-X", "utf8", "cloudflare/deploy_r2.py"], ROOT, False),
]
only = set(sys.argv[1:])
for name, cmd, cwd, soft in steps:
    if only and name not in only:
        continue
    run(name, cmd, cwd, soft)
print("\nготово:", f"https://bridge42worlds.academy/lang/ru/archive/2026-09-08/{AID}/index.html")
