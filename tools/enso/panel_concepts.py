# -*- coding: utf-8 -*-
"""Понятия из САМОЙ панели: словарь, риски, тревоги, блоки, справочники моделей и цепочки.

Владелец 07.09: «я думал, ты возьмёшь не только работы, но и текст с дашборда, его
термины и так далее». Справедливо: добыча по корпусу читала 294 наши климатические
работы и не заглянула в панель, а там лежит отобранный руками словарь на 67 терминов
и вся объяснительная проза — тексты рисков, тревог, блоков, описания моделей плюма и
узлов цепочки данных.

Два источника — две дороги, и они разные по природе:

  1. СЛОВАРЬ ПАНЕЛИ. Это уже готовые словарные статьи: имя, определение, зачем здесь,
     источник. Их не надо выуживать моделью — их надо СВЕРИТЬ с реестром и внести
     недостающие. Ключ словаря («nino34») — внутреннее имя панели, поэтому канонический
     идентификатор строим из отображаемого имени, а определение идёт карточкой как есть.

  2. ПРОЗА ПАНЕЛИ. Тексты рисков, тревог, блоков вердикта, описания моделей и узлов
     цепочки. Здесь работает обычная добыча тем же климатическим промптом, что и по
     статьям: документ собирается по темам, ответ падает в общую копилку и проходит то
     же сито — вектор, твёрдая опора, Semantic Scholar.

    python tools/enso/panel_concepts.py --plan       что найдётся, ничего не тратя
    python tools/enso/panel_concepts.py --glossary   внести словарь панели (без модели)
    python tools/enso/panel_concepts.py --prose      добыть из прозы (платно, копейки)
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tools import concept_harvest as CH  # noqa: E402

DATA = ROOT / "data" / "enso"
PROMPT = ROOT / "data" / "prompts" / "concept-extract-climate.txt"
# Псевдо-работы: копилка ключует опору по идентификатору статьи, и панель получает свои.
DOC_PREFIX = "enso-panel:"


def slug(name):
    """Отображаемое имя → канонический идентификатор понятия."""
    s = name.lower().replace("ñ", "n").replace("é", "e")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:48]


def glossary_rows():
    """Словарь панели как готовые кандидаты: имя, вид, карточка."""
    g = json.loads((DATA / "glossary.json").read_text(encoding="utf-8"))["en"]
    out = []
    for key, v in g.items():
        name = slug(v.get("name") or key)
        if not name:
            continue
        line = (v.get("def") or "").strip()
        if len(line) < 20:
            continue
        # Часть статей словаря объясняет ДВЕ вещи разом: «eastern and central type»,
        # «anomaly and the 1991-2020 climatology», «trend and above trend». Это удобная
        # словарная статья, но не имя понятия: в реестре такое имя не живёт ни у кого.
        # Составные и слишком длинные пропускаем — их термины и так приходят из прозы.
        if "_and_" in name or name.count("_") >= 4:
            continue
        out.append({"name": name, "kind": guess_kind(v), "group": "other",
                    "scope": "specific", "line": line[:400],
                    "mentions": [v.get("name")] if v.get("name") else []})
    return out


def guess_kind(v):
    """Вид понятия по словам определения: панель не хранит вид, а реестр его требует."""
    t = ((v.get("def") or "") + " " + (v.get("why") or "")).lower()
    if any(w in t for w in ("index", "measure of", "we compute", "chart", "statistic")):
        return "method"
    if any(w in t for w in ("feedback", "effect")):
        return "effect"
    if any(w in t for w in ("current", "circulation", "flow", "transport", "wave")):
        return "process"
    if any(w in t for w in ("warming", "phase", "pattern", "oscillation", "event")):
        return "phenomenon"
    return "concept"


def prose_docs():
    """Проза панели, собранная в документы по темам."""
    d = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    docs = {}
    risks = d.get("risks") or []
    docs["risks"] = "\n\n".join(
        " ".join(filter(None, [r.get("title"), r.get("plain"), r.get("evidence"),
                               r.get("watch")])) for r in risks)
    docs["alerts"] = "\n\n".join(
        " ".join(filter(None, [a.get("title"), a.get("detail")]))
        for a in (d.get("alerts") or []))
    sm = d.get("summary") or {}
    docs["verdict"] = "\n\n".join(filter(None, [
        sm.get("verdict"), " ".join(sm.get("watch") or []),
        " ".join(str(x) for x in (sm.get("caveats") or [])),
        " ".join(str(v) for v in (sm.get("blocks") or {}).values())]))
    try:
        m = json.loads((DATA / "models-ref.json").read_text(encoding="utf-8"))
        docs["models"] = "\n".join(
            f"{k}: {v.get('what') or v.get('def') or ''}" for k, v in (m.get("models") or {}).items())
    except Exception:                                            # noqa: BLE001
        pass
    try:
        c = json.loads((DATA / "chain-ref.json").read_text(encoding="utf-8"))
        docs["chain"] = "\n".join(
            f"{n.get('name')}: {n.get('what') or n.get('def') or ''}" for n in (c.get("nodes") or []))
    except Exception:                                            # noqa: BLE001
        pass
    return {k: v for k, v in docs.items() if v and len(v) > 200}


def ask(text, title):
    key = CH.env("DEEPSEEK_API_KEY")
    p = (PROMPT.read_text(encoding="utf-8")
         .replace("{groups}", CH.groups_text())
         .replace("{title}", title)
         .replace("{text}", text[:12000]))
    body = json.dumps({"model": "deepseek-chat",
                       "messages": [{"role": "user", "content": p}],
                       "temperature": 0.2, "max_tokens": 1400}).encode("utf-8")
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    return CH.parse_answer(d["choices"][0]["message"]["content"])


def main():
    ap = argparse.ArgumentParser(description="Понятия из панели El Niño")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--glossary", action="store_true")
    ap.add_argument("--prose", action="store_true")
    a = ap.parse_args()

    gl = glossary_rows()
    docs = prose_docs()
    if a.plan or not (a.glossary or a.prose):
        live = set(json.loads((ROOT / "data" / "concepts-live.json")
                              .read_text(encoding="utf-8"))["concepts"])
        miss = [r for r in gl if r["name"] not in live]
        print(f"словарь панели: {len(gl)} терминов, из них нет в реестре {len(miss)}")
        for r in miss[:12]:
            print(f"   {r['kind']:10s} {r['name']} — {r['line'][:60]}")
        print(f"проза панели: {len(docs)} документов "
              f"({', '.join(f'{k} {len(v)//1000}k' for k, v in docs.items())})")
        print(f"смета прозы: ~{len(docs)} вызовов ≈ ${len(docs) * 0.002:.2f}")
        return 0

    if a.glossary:
        CH.ingest(DOC_PREFIX + "glossary", gl)
        print(f"словарь панели внесён в копилку: {len(gl)} терминов")
    if a.prose:
        for name, text in docs.items():
            try:
                cands = ask(text, f"El Niño dashboard — {name}")
            except Exception as e:                               # noqa: BLE001
                print(f"  {name}: сбой {str(e)[:80]}")
                continue
            CH.ingest(DOC_PREFIX + name, cands)
            print(f"  {name}: кандидатов {len(cands)}")
    print("дальше: python tools/concept_cycle.py --budget 0 --corpus … --min …")
    return 0


if __name__ == "__main__":
    sys.exit(main())
