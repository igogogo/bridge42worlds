# -*- coding: utf-8 -*-
"""Целевое донасыщение реестра: законы, математика, константы, принципы.

Шаг A4 плана (владелец 27.08: «кажется, мало математики; зашёл — а законов
нет; насытить и по всему пройтись»). Аудит подтвердил дыры: math 32, law 58,
constant 4 на 3231 понятие.

Не новая машина, а второй проход той же добычи с ЦЕЛЕВЫМ промптом
(data/prompts/concept-extract-target.txt): модель ищет ТОЛЬКО четыре
недосыпанных класса, ноль — валидный ответ. Кандидаты падают в ОБЩУЮ копилку
(concept-harvest.jsonl) со своим состоянием спрошенных статей; дальше их ждут
обычные --match / --distill / рождения — то же сито, что у всех.

Выборка статей: полные разборы (не экспресс) в первую очередь — законы и
математика живут в advanced-текстах; добор экспрессами тяжёлых разделов
(gr-qc, hep-th, quant-ph, math-ph...).

    python tools/concept_harvest_target.py --plan          посчитать выборку
    python tools/concept_harvest_target.py --run [--cap N] спросить (платно)
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import concept_harvest as CH  # noqa: E402 — общий движок добычи

PROMPT = ROOT / "data" / "prompts" / "concept-extract-target.txt"
STATE = ROOT / "data" / "harvest-target-state.json"
# профили целевых проходов: law/math/... и отдельный статистический
PROFILES = {
    "target": {"prompt": "concept-extract-target.txt",
               "state": "harvest-target-state.json",
               "kinds": ("law", "math", "constant", "principle")},
    "stats": {"prompt": "concept-extract-stats.txt",
              "state": "harvest-stats-state.json",
              "kinds": ("statistics",)},
}
HEAVY = ("gr-qc", "hep-th", "hep-ph", "quant-ph", "math-ph", "nucl-th",
         "cond-mat", "astro-ph")


def state(prof):
    p = ROOT / "data" / PROFILES[prof]["state"]
    try:
        return set(json.loads(p.read_text(encoding="utf-8"))["asked"])
    except Exception:
        return set()


def save_state(prof, asked):
    (ROOT / "data" / PROFILES[prof]["state"]).write_text(
        json.dumps({"asked": sorted(asked)}, ensure_ascii=False),
        encoding="utf-8")


def pick_articles():
    """Полные разборы первыми, затем экспрессы тяжёлых разделов."""
    full, heavy = [], []
    for p in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = d.get("id") or p.parent.name
        cat = (d.get("primary_category") or "").split(".")[0]
        if not d.get("express"):
            full.append(aid)
        elif cat in HEAVY:
            heavy.append(aid)
    return full + heavy


def build_prompt(aid, prof="target"):
    title, text = CH.article_text(aid)
    if not title:
        return None
    ptxt = ROOT / "data" / "prompts" / PROFILES[prof]["prompt"]
    return (ptxt.read_text(encoding="utf-8")
            .replace("{groups}", CH.groups_text())
            .replace("{title}", title)
            .replace("{text}", text))


def run(cap, prof="target"):
    try:
        from tools.freeze import guard
        guard("целевое донасыщение (DeepSeek)")
    except ImportError:
        pass
    key = CH.env("DEEPSEEK_API_KEY")
    kinds = PROFILES[prof]["kinds"]
    asked = state(prof)
    todo = [a for a in pick_articles() if a not in asked][:cap]
    print(f"целевой прогон: {len(todo)} статей (спрошено ранее {len(asked)})")
    n_c = 0
    for i, aid in enumerate(todo, 1):
        p = build_prompt(aid, prof)
        if not p:
            asked.add(aid)
            continue
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": p}],
            "temperature": 0.2, "max_tokens": 1100,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            raw = d["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  {aid}: сбой {e} — пауза и дальше")
            time.sleep(5)
            continue
        cands = CH.parse_answer(raw)
        # целевой проход принимает только целевые классы — модель иногда
        # приносит лишнее вопреки промпту
        cands = [c for c in cands if c.get("kind") in kinds]
        if cands:
            CH.ingest(aid, cands)
            n_c += len(cands)
        asked.add(aid)
        if i % 25 == 0:
            save_state(prof, asked)
            print(f"  {i}/{len(todo)} · кандидатов +{n_c}")
    save_state(prof, asked)
    print(f"✅ целевых кандидатов: +{n_c}; дальше обычные --match/--distill/рождения")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Целевое донасыщение: law/math/constant/principle")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--cap", type=int, default=1700)
    ap.add_argument("--profile", default="target", choices=sorted(PROFILES))
    a = ap.parse_args()
    arts = pick_articles()
    if a.plan or not a.run:
        asked = state(a.profile)
        todo = [x for x in arts if x not in asked]
        est = min(len(todo), a.cap)
        print(f"выборка: {len(arts)} статей (полные + экспрессы тяжёлых разделов)")
        print(f"не спрошено: {len(todo)} · в прогон пойдёт: {est}")
        print(f"смета: ~{est} × 1.4k ток ≈ ${est * 0.0006:.2f}–{est * 0.0011:.2f}")
        return 0
    return run(a.cap, a.profile)


if __name__ == "__main__":
    sys.exit(main())
