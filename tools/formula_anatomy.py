# -*- coding: utf-8 -*-
"""Анатомия формул: переменные, операторы, константы, описание, применимость.

Владелец 26.08: «формула просто так не существует — у неё есть переменные, операторы
и константы, и всё должно быть описано. Оператор должен быть в математике у нас;
константа — какой-то класс констант, там же в понятиях; переменные просто объяснены
в формуле. Плюс у формулы описание и область применимости. Это наши мозги — надо
отнестись серьёзно к облаку формул».

СТРУКТУРА (data/formula-anatomy.json, по base_id основной формы):

  variables    [{s: "v", m: "particle speed"}]      объяснены НА МЕСТЕ
  operators    [{s: "∇", id: "nabla_operator"}]     ссылка в реестр, класс math
  constants    [{s: "ħ", id: "planck_constant"}]    ссылка в реестр, класс constant
  description  3-5 предложений: что утверждает и почему это так
  applicability где формула работает и где ломается — границы, а не реклама

ОПЕРАТОРЫ И КОНСТАНТЫ — СУЩНОСТИ РЕЕСТРА. Модель называет их каноническим
идентификатором; сверка вектором (как у кандидатов harvest) решает, есть ли такое
понятие. Нет — рождается через тот же живой механизм: оператор с kind=math,
константа с НОВЫМ kind=constant. Так облако формул само наращивает математический
и константный слои реестра — по мере разбора, а не ручным посевом.

КОМАНДЫ (платное отделено, дорогой период под охраной):
  --sample N     разобрать N форм на просмотр (микро-трата)
  --run          все 642 — только в дешёвое окно DeepSeek (19:30-03:30 Кувейта)
  --link         операторы/константы → реестр вектором; не нашлись — в копилку
                 harvest как кандидаты (kind math/constant)

Смета --run: 642 формы × ~1100 токенов ≈ $0.3-0.5 в дешёвое окно.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
OUT = ROOT / "data" / "formula-anatomy.json"

sys.path.insert(0, str(ROOT))
from tools.concept_harvest import env, embed, load_harvest, save_harvest  # noqa: E402
from tools.concept_fullcards import cheap_window  # noqa: E402

PER_CALL = 3

SYS = """You dissect physics formulas for a knowledge base.

For each numbered formula you get its id, name, LaTeX and a one-line meaning.
Return a JSON array, one object per formula, same order:

{"n": <number>,
 "variables": [{"s": "<symbol>", "m": "<what it denotes, few words>",
                "id": "<canonical_snake_case name of the physical QUANTITY it is:
                       mass, energy, temperature...; empty if purely auxiliary>",
                "unit": "<SI unit, canonical snake_case: kilogram, joule, kelvin,
                         metre_per_second; \"dimensionless\" when unitless>"}],
 "operators": [{"s": "<symbol>", "id": "<canonical_snake_case_name>",
                "m": "<what this operation does, few words>"}],
 "constants": [{"s": "<symbol>", "id": "<canonical_snake_case_name>",
                "m": "<what this constant IS, one short sentence>",
                "value": "<numeric value with power of ten, e.g. 6.626e-34>",
                "unit": "<SI unit, canonical snake_case>"}],
 "description": "<3-5 sentences: what the formula states and why it holds>",
 "history": "<1-2 sentences: who derived it and when, how it got its modern form;
             empty string if not honestly known — never invent>",
 "applicability": "<2-4 sentences: where it applies and where it BREAKS DOWN —
                   assumptions, limits, regimes>"}

Rules:
1. variables = quantities that vary (v, T, ψ...); give each its canonical physical
   quantity id where one exists (velocity, temperature, wave_function). constants = fixed universal or
   material constants (c, ħ, G, k_B...). operators = mathematical operations
   (∇, ∂/∂t, ∫, [ , ], d/dx...). Classify each symbol into exactly one bucket.
2. operator/constant id: canonical English snake_case (nabla_operator,
   planck_constant, speed_of_light, partial_derivative, commutator).
3. applicability must name real limits (non-relativistic, dilute gas, linear
   response, weak field...) — a formula without limits is advertising, not physics.
4. A physicist must find every sentence unobjectionable.
Output ONLY the JSON array."""


def bases():
    d = json.loads((ML / "data" / "formulas-linked.json").read_text(encoding="utf-8"))
    return d["bases"]


def ask_batch(batch, key):
    lines = []
    for i, b in enumerate(batch, 1):
        lines.append(f"{i}. id={b['base_id']}\n   name: {b.get('name', '')}\n"
                     f"   latex: {b.get('latex', '')}\n   meaning: {b.get('card', '')}")
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.2, "max_tokens": 2400,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode("utf-8"))
    raw = d["choices"][0]["message"]["content"]
    m = re.search(r"\[.*\]", raw, re.S)
    got = json.loads(m.group(0)) if m else []
    out = {}
    for it in got:
        try:
            n = int(it["n"])
            if not (1 <= n <= len(batch)):
                continue
            rec = {
                "variables": [{"s": str(v.get("s", ""))[:20], "m": str(v.get("m", ""))[:120],
                               "id": re.sub(r"[^a-z0-9_]", "", str(v.get("id", "")).lower()),
                               "unit": re.sub(r"[^a-z0-9_]", "", str(v.get("unit", "")).lower())[:40]}
                              for v in (it.get("variables") or []) if v.get("s")],
                "operators": [{"s": str(v.get("s", ""))[:20],
                               "id": re.sub(r"[^a-z0-9_]", "", str(v.get("id", "")).lower()),
                               "m": str(v.get("m", ""))[:120]}
                              for v in (it.get("operators") or []) if v.get("s")],
                "constants": [{"s": str(v.get("s", ""))[:20],
                               "id": re.sub(r"[^a-z0-9_]", "", str(v.get("id", "")).lower()),
                               "m": str(v.get("m", ""))[:200],
                               "value": str(v.get("value", ""))[:40],
                               "unit": re.sub(r"[^a-z0-9_]", "", str(v.get("unit", "")).lower())[:40]}
                              for v in (it.get("constants") or []) if v.get("s")],
                "description": str(it.get("description", ""))[:1200],
                "history": str(it.get("history", ""))[:600],
                "applicability": str(it.get("applicability", ""))[:800],
            }
            if rec["description"] and rec["applicability"]:
                out[batch[n - 1]["base_id"]] = rec
        except (KeyError, ValueError, TypeError):
            continue
    return out


def run(limit=None, force_peak=False):
    try:
        from tools.freeze import guard
        guard("анатомия формул (DeepSeek)")
    except ImportError:
        pass
    if limit is None and not cheap_window() and not force_peak:
        print("ПИКОВЫЙ тариф DeepSeek — владелец просил дешёвое окно "
              "(19:30–03:30 по Кувейту). --force-peak обойдёт.")
        return 1
    key = env("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("нет DEEPSEEK_API_KEY")
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    todo = [b for b in bases() if b["base_id"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"форм без анатомии: {len(todo)}")
    for s in range(0, len(todo), PER_CALL):
        batch = todo[s:s + PER_CALL]
        try:
            got = ask_batch(batch, key)
        except Exception as e:
            print(f"  сбой пачки {s}: {e} — пауза и дальше")
            time.sleep(5)
            continue
        done.update(got)
        OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {len(done)} готово (+{len(got)})")
    print(f"✅ анатомий: {len(done)} → {OUT.relative_to(ROOT)}")
    return 0


def link():
    """Операторы и константы → понятия реестра. Не нашлись — кандидаты в копилку
    живого механизма: оператор kind=math, константа kind=constant. Реестр растёт
    из формул тем же путём, что из статей."""
    import numpy as np
    sys.path.insert(0, str(ML))
    import concepts_super as cs
    cids, CV = cs.load_cards()
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if not done:
        print("анатомий нет — сначала --sample/--run")
        return 1

    # собираем уникальных кандидатов: id → (kind, где встречен)
    want = {}
    for base_id, rec in done.items():
        for kind_key, kind in (("operators", "math"), ("constants", "constant"),
                               ("variables", "quantity")):
            # единицы — отдельный класс: kilogram, joule... собираем из обоих полей
            for o in rec.get(kind_key) or []:
                u = o.get("unit")
                if u and u != "dimensionless":
                    want.setdefault(u, {"kind": "unit", "bases": []})
                    want[u]["bases"].append(base_id)
            for o in rec.get(kind_key) or []:
                if o.get("id"):
                    want.setdefault(o["id"], {"kind": kind, "bases": []})
                    want[o["id"]]["bases"].append(base_id)
    print(f"уникальных операторов/констант: {len(want)}")

    texts = [w.replace("_", " ") for w in want]
    vecs = embed(texts)
    reg = set(cids)
    rows = load_harvest()
    matched = born_cand = 0
    for (wid, info), v in zip(want.items(), vecs):
        a = np.asarray(v, dtype=np.float32)
        a /= np.linalg.norm(a) + 1e-9
        sims = CV @ a
        j = int(sims.argmax())
        if wid in reg or float(sims[j]) >= 0.80:
            info["concept"] = wid if wid in reg else cids[j]
            matched += 1
        else:
            info["concept"] = None
            if wid not in rows:
                grp = {"math": "mathematics", "constant": "physical constants",
                       "quantity": "physical quantities",
                       "unit": "units of measurement"}[info["kind"]]
                rows[wid] = {"name": wid, "kind": info["kind"], "group": grp,
                             "scope": "general",
                             "line": f"{wid.replace('_', ' ')} — from formula anatomy",
                             "articles": [], "matched": None,
                             "from_formulas": info["bases"][:20]}
                born_cand += 1
    save_harvest(rows)
    # прописываем связь в анатомию
    for base_id, rec in done.items():
        for kind_key in ("operators", "constants"):
            for o in rec.get(kind_key) or []:
                w = want.get(o.get("id") or "")
                if w:
                    o["concept"] = w["concept"]
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"связано с реестром: {matched} · новых кандидатов (math/constant): {born_cand}")
    print("кандидаты дорастут через обычный цикл; у констант kind=constant — новый класс")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Анатомия формул")
    ap.add_argument("--sample", type=int, metavar="N")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--force-peak", action="store_true")
    ap.add_argument("--link", action="store_true")
    a = ap.parse_args()
    if a.link:
        return link()
    if a.sample:
        return run(limit=a.sample, force_peak=True)
    if a.run:
        return run(force_peak=a.force_peak)
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    print(f"анатомий: {len(done)} из {len(bases())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
