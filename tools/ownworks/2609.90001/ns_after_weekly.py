# -*- coding: utf-8 -*-
"""После недельного прогона: провести работу 2609.90001 через конвейер целиком.

Владелец 09.09: «если надо, наши понятия дополнить этой работой, и разметку сделать; в целом
всё как надо чтобы было». Поэтому цепочка — та же, что у статьи дня, только для одной работы:

  понятия     добыча кандидатов из работы (профиль target) → рождение при опоре ≥ 5 статей
              (одиночных понятий не заводим — правило владельца 07.09) → двойники → реестр →
              карточки, переводы, имена → граф и страницы понятий
  разметка    поле → разметка вектором → запись в статью → подсветка в текстах
  страницы    ОДНА полная сборка html: подпись генератора изменилась 09.09, он всё равно
              пересоберёт архив, заодно вернёт ~970 страниц на язык, не дописанных упавшим html
  связи       похожие, цитируемые
  облако      контекст для бота, карточки, обвязка, реестр понятий и оба вектора, лицензии
  выкладка    дельта в R2

Замок дерева берут сами шаги. Предохранители: ждём не дольше шести часов, чужой замок не снимаем.

    python ns_after_weekly.py <pid недельного>        ждать и провести
    python ns_after_weekly.py now                       без ожидания
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


def alive(pid):
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ 'Y' }} else {{ 'N' }}"],
                         capture_output=True, text=True).stdout.strip()
    return out.endswith("Y")


def run(name, cmd, cwd=ROOT, soft=True, timeout=10 * 3600):
    t0 = time.time()
    print(f"\n▶ {name}: {' '.join(cmd)}")
    log = ROOT / "logs" / f"ns-{name}-0909.log"
    with log.open("w", encoding="utf-8") as fo:
        r = subprocess.run(cmd, cwd=str(cwd), env=ENV, stdout=fo, stderr=subprocess.STDOUT, timeout=timeout)
    print(f"  {'✓' if r.returncode == 0 else '✗'} {name} ({int(time.time() - t0)} с, код {r.returncode}) → {log.name}")
    if r.returncode and not soft:
        sys.exit(f"стоп на шаге {name}")


arg = sys.argv[1] if len(sys.argv) > 1 else "now"
if arg != "now":
    pid, t0 = int(arg), time.time()
    while alive(pid):
        if time.time() - t0 > 6 * 3600:
            sys.exit("недельный не кончился за шесть часов — не запускаю")
        time.sleep(120)
    print(f"недельный закончился, ждали {int((time.time() - t0) / 60)} мин")
    time.sleep(30)
if LOCK.exists():
    sys.exit("замок дерева занят: " + LOCK.read_text(encoding="utf-8")[:80])

T = lambda *a: [PY, "-X", "utf8", *a]
# ── понятия из работы ──────────────────────────────────────────────────────
run("harvest", T("tools/concept_harvest_target.py", "--run", "--profile", "target",
                 "--ids-file", "data/ns-ids.txt", "--cap", "5"))
run("births", T("tools/concept_cycle.py", "--budget", "0"))
run("twins", T("tools/concept_twins.py", "--apply"))
run("live-1", T("tools/wave5_apply.py", "--live-only"))
run("cards", T("tools/concept_fullcards.py", "--run", "--force-peak"))
run("tr-cards", T("tools/cards_translate_ru.py", "--concepts", "--force-peak"))
run("names-ru", T("tools/concept_names_translate.py"))
run("live-2", T("tools/wave5_apply.py", "--live-only"))
# ── разметка работы ────────────────────────────────────────────────────────
run("vec-ours", T("embeddings_export.py"))
run("vec-push", T("cloudflare/vector_build.py"))
run("field", T("field_build.py", "--ours", "--months", "2026-09", "--max-cost", "0.5"), cwd=ML)
run("retag", T("tools/retag_hub.py", "--live", AID, "--apply", "--thr", "0.50", "--margin", "0.12"))
run("apply", T("tools/wave5_apply.py", "--apply", "--articles-only"))
run("highlight", T("tools/highlight_concepts.py", "--ids", AID, "--tiers", "simple,popular,advanced"))
# ── граф, страницы понятий, связи, сборка ──────────────────────────────────
run("graph", T("tools/concepts_graph_export.py"))
run("pages-c", T("concepts_pages.py"))
run("related", T("tools/vector_links_local.py"))
run("cited", T("tools/cited_ours.py"))
run("html", T("run.py", "html"), soft=False)
# ── облако и выкладка ──────────────────────────────────────────────────────
run("context", T("cloudflare/context_build.py"))
run("cloud-d1", T("cloudflare/concepts_sync.py"))
run("cloud-vec", T("tools/concepts_to_vectorize.py", "--apply"))
run("cards-sync", T("cloudflare/cards_sync.py", "--apply"))
run("side", T("cloudflare/frame_sync.py", "--apply"))
run("lic-audit", T("tools/license_audit.py", "--fix"))
run("deploy", T("cloudflare/deploy_r2.py"), soft=False)
print("\nготово:", f"https://bridge42worlds.academy/lang/ru/archive/2026-09-08/{AID}/index.html")
