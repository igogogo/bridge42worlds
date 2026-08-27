# -*- coding: utf-8 -*-
"""Системы единиц — каркас поверх класса unit (владелец 27.08: «единицы измерения —
как устроено? есть разные системы: СИ, планковская и так далее — надо доводить до ума»).

ДВА ШАГА:

  --seed        родить 5 понятий-систем (kind=unit_system) с опорными карточками:
                СИ, гауссова СГС, планковские, натуральные, атомные единицы.
                Той же механикой, что живой цикл: запись в grown + вектор в матрицу.
                Полные записи им допишет обычный concept_fullcards.
  --link-units  по каждому понятию класса unit/quantity спросить DeepSeek: в каких
                системах живёт единица, чем определяется в СИ; величинам — их
                единицы в разных системах. Результат — поле "systems"/"units_by_system"
                прямо в live-записи (концепт-дельта data/unit-systems-links.json,
                вливается в live на месте).

Формулы в разных системах — отдельный проход tools/formula_anatomy.py --systems.

ЗАПУСКАТЬ ПОСЛЕ ночной цепочки: births пишет в те же grown/матрицу — гонка.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.concept_harvest import env, embed  # noqa: E402
from tools.concept_cycle import append_to_matrix  # noqa: E402
from tools.concept_fullcards import cheap_window  # noqa: E402

GROWN = ROOT / "data" / "concepts-grown.json"
LIVE = ROOT / "data" / "concepts-live.json"
LINKS = ROOT / "data" / "unit-systems-links.json"

# Опорные карточки — определения для вектора; полные записи допишет fullcards.
SYSTEMS = {
    "si_units": {
        "name": "SI units",
        "card": "The International System of Units (SI) is the modern metric system "
                "built on seven base units — metre, kilogram, second, ampere, kelvin, "
                "mole and candela — from which all other units are derived; since 2019 "
                "every base unit is defined by fixing an exact value of a fundamental "
                "constant of nature.",
    },
    "gaussian_units": {
        "name": "Gaussian units",
        "card": "The Gaussian unit system is a centimetre-gram-second (CGS) system for "
                "electromagnetism in which the Coulomb constant equals one, so electric "
                "charge carries mechanical dimensions and factors of 4*pi*epsilon_0 "
                "disappear from formulas while factors of the speed of light appear "
                "explicitly in field equations.",
    },
    "planck_units": {
        "name": "Planck units",
        "card": "Planck units are natural units defined by setting the speed of light, "
                "the gravitational constant, the reduced Planck constant and the "
                "Boltzmann constant to one, which makes the Planck length, time, mass "
                "and temperature the characteristic scales at which quantum gravity "
                "effects become significant.",
    },
    "natural_units": {
        "name": "natural units",
        "card": "Natural units are unit systems used in particle physics where the "
                "speed of light and the reduced Planck constant are set to one, so "
                "mass, energy and momentum share one unit (typically the electronvolt) "
                "and formulas lose their factors of c and hbar.",
    },
    "atomic_units": {
        "name": "atomic units",
        "card": "Atomic units are a system used in atomic physics and quantum "
                "chemistry where the electron mass, elementary charge, reduced Planck "
                "constant and Coulomb constant equal one, making the Bohr radius and "
                "the Hartree energy the natural scales of atomic structure.",
    },
}


def seed():
    grown = json.loads(GROWN.read_text(encoding="utf-8")) if GROWN.exists() else {}
    todo = {cid: s for cid, s in SYSTEMS.items() if cid not in grown}
    if not todo:
        print("все системы уже рождены")
        return 0
    vecs = embed([s["card"] for s in todo.values()])
    for (cid, s), v in zip(todo.items(), vecs):
        grown[cid] = {
            "kind": "unit_system", "group": "units of measurement",
            "scope": "general", "card_en": s["card"], "articles": [],
            "aliases": [], "born": datetime.now().date().isoformat(),
            "origin": "unit-systems-seed", "names": {"en": s["name"]},
        }
        append_to_matrix(cid, list(map(float, v)))
        print(f"   🌱 {cid}")
    GROWN.write_text(json.dumps(grown, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"✅ систем рождено: {len(todo)}")
    return 0


SYS_LINK = """You classify measurement units and physical quantities for a knowledge base.

For each numbered entry (a unit or a physical quantity) return a JSON array,
one object per entry, same order:

For a UNIT:
{"n": <number>,
 "systems": ["<si|gaussian|planck|natural|atomic>", ...],
 "si_definition": "<one sentence: how the unit is defined / expressed in SI>"}

For a QUANTITY:
{"n": <number>,
 "units_by_system": {"si": "<canonical_snake_case unit>",
                     "gaussian": "<unit or empty>",
                     "planck": "<unit or empty>",
                     "natural": "<unit or empty>"}}

Rules:
1. "systems" lists every system where the unit is actually used (a second is used
   in SI and Gaussian; an erg only in Gaussian; electronvolt in natural units and
   accepted alongside SI).
2. Never invent: leave a field empty when honestly unsure.
Output ONLY the JSON array."""


def link_units(force_peak=False):
    if not cheap_window() and not force_peak:
        print("ПИКОВЫЙ тариф DeepSeek — дешёвое окно 19:30–03:30 Кувейта; --force-peak обойдёт.")
        return 1
    live = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    done = json.loads(LINKS.read_text(encoding="utf-8")) if LINKS.exists() else {}
    targets = [(cid, v) for cid, v in live.items()
               if v.get("kind") in ("unit", "quantity") and cid not in done]
    if not targets:
        print("все единицы/величины уже привязаны")
        return 0
    key = env("DEEPSEEK_API_KEY")
    print(f"единиц/величин на привязку: {len(targets)}")
    for s in range(0, len(targets), 8):
        batch = targets[s:s + 8]
        lines = [f"{i}. [{v.get('kind').upper()}] {cid.replace('_', ' ')} — "
                 f"{(v.get('card_en') or '')[:160]}"
                 for i, (cid, v) in enumerate(batch, 1)]
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": SYS_LINK},
                         {"role": "user", "content": chr(10).join(lines)}],
            "temperature": 0.2, "max_tokens": 1600,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read().decode("utf-8"))
            raw = d["choices"][0]["message"]["content"]
            m = re.search(r"\[.*\]", raw, re.S)
            got = json.loads(m.group(0)) if m else []
        except Exception as e:
            print(f"  сбой пачки {s}: {e} — пауза и дальше")
            time.sleep(5)
            continue
        for it in got:
            try:
                n = int(it["n"])
                if not (1 <= n <= len(batch)):
                    continue
                cid = batch[n - 1][0]
                rec = {}
                if it.get("systems"):
                    rec["systems"] = [x for x in it["systems"]
                                      if x in ("si", "gaussian", "planck",
                                               "natural", "atomic")]
                if it.get("si_definition"):
                    rec["si_definition"] = str(it["si_definition"])[:300]
                if isinstance(it.get("units_by_system"), dict):
                    rec["units_by_system"] = {
                        k: re.sub(r"[^a-z0-9_]", "", str(v).lower())[:50]
                        for k, v in it["units_by_system"].items()
                        if k in ("si", "gaussian", "planck", "natural", "atomic") and v}
                done[cid] = rec
            except (KeyError, ValueError, TypeError):
                continue
        LINKS.write_text(json.dumps(done, ensure_ascii=False, indent=1),
                         encoding="utf-8")
        print(f"  привязано {len(done)}")
    # влить в live на месте — рендер страниц понятий читает live
    live_doc = json.loads(LIVE.read_text(encoding="utf-8"))
    for cid, rec in done.items():
        if cid in live_doc["concepts"]:
            live_doc["concepts"][cid].update(rec)
    LIVE.write_text(json.dumps(live_doc, ensure_ascii=False), encoding="utf-8")
    print(f"✅ привязки в live: {len(done)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Системы единиц")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--link-units", action="store_true")
    ap.add_argument("--force-peak", action="store_true")
    a = ap.parse_args()
    if a.seed:
        return seed()
    if a.link_units:
        return link_units(force_peak=a.force_peak)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
