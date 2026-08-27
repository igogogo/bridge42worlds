# -*- coding: utf-8 -*-
"""Константы рождаются из формул, а не из статей.

Владелец 27.08: «константы могут в статьях не упоминаться, но надо чтобы нам об
этом сказали наши формулы». Так и есть: элементарный заряд входит в одиннадцать
наших формул и при этом не назван дословно ни в одной статье — обычное сито
рождений его не пропустит никогда, потому что оно ищет упоминания в текстах.
Опора константы — не текст, а разбор формулы: если анатомия говорит «здесь
стоит e = 1.602e-19 Кл», это и есть подтверждение.

Что делаем:

  1. Собираем из data/formula-anatomy.json все константы с ЧИСЛОВЫМ значением.
     Значение — главное сито: у настоящей константы оно одно на всю физику,
     у параметра модели его нет («varies», «model-dependent», «depends on»).
  2. Отсеиваем параметры по имени: slope, factor, coefficient, coupling,
     exponent, efficiency, parameter — это не константы, а ручки моделей,
     их значение верно лишь для одной статьи.
  3. Кого нет в реестре — пишем в data/concepts-grown.json классом constant,
     со значением, единицей и статьями формул.
  4. Кто есть, но числится другим классом (speed_of_light лежит «понятием»),
     — правим класс через data/concept-kind-fix.json, отдельным слоем: реестр
     v3 не трогаем, правка видна и обратима.

Ядро СИ (--codata) добавляет фундаментальные константы, которых нет ни в одной
нашей формуле: постоянная тонкой структуры, Ридберга, боровский радиус. Их
значения — определения СИ-2019 и CODATA-2018, помечены origin="codata-core",
чтобы происхождение было видно в реестре.

  python tools/constants_from_formulas.py            # сухой ход, только отчёт
  python tools/constants_from_formulas.py --apply    # записать
  python tools/constants_from_formulas.py --apply --codata
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AN = ROOT / "data" / "formula-anatomy.json"
LINKED = ROOT / "data" / "formulas-linked.json"
LIVE = ROOT / "data" / "concepts-live.json"
GROWN = ROOT / "data" / "concepts-grown.json"
KINDFIX = ROOT / "data" / "concept-kind-fix.json"

# Ручки моделей, а не константы природы. Слово в имени — повод отказать.
PARAM_WORDS = ("slope", "intercept", "factor", "coefficient", "coupling",
               "exponent", "efficiency", "parameter", "proportionality",
               "amplitude", "scale", "viscosity", "frequency", "temperature",
               "density", "conversion", "structure_constant", "two_pi",
               "permittivity_relative", "relative_", "cutoff", "reference_")
# Признание в самом описании, что значения нет
VAGUE = ("varies", "model-dependent", "material-dependent", "depends on",
         "order unity", "variable", "characteristic")

NUM = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")


def load(p, d=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {} if d is None else d


def numeric(v):
    """Значение — число? «1.602e-19» да, «varies by material» нет."""
    s = (v or "").strip().replace("×10^", "e").replace(" ", "")
    return bool(NUM.match(s))


def looks_param(cid, desc):
    if any(w in cid for w in PARAM_WORDS):
        return True
    d = (desc or "").lower()
    return any(w in d for w in VAGUE)


# Ядро СИ-2019 и CODATA-2018. Первые пять определены точно — это не измерение,
# а определение единицы; остальные измерены, значение с последней доверенной
# цифрой. Список закрыт намеренно: константа входит сюда, только если она
# фундаментальная, а не удобная.
CODATA = {
    "speed_of_light": ("299792458", "metre_per_second", "c",
        "Speed of light in vacuum — exact by definition of the metre since 2019."),
    "planck_constant": ("6.62607015e-34", "joule_second", "h",
        "Planck constant — exact by definition of the kilogram since 2019."),
    "elementary_charge": ("1.602176634e-19", "coulomb", "e",
        "Elementary charge — exact by definition of the ampere since 2019."),
    "boltzmann_constant": ("1.380649e-23", "joule_per_kelvin", "k_B",
        "Boltzmann constant — exact by definition of the kelvin since 2019."),
    "avogadro_constant": ("6.02214076e23", "per_mole", "N_A",
        "Avogadro constant — exact by definition of the mole since 2019."),
    "gravitational_constant": ("6.67430e-11", "newton_metre_squared_per_kilogram_squared",
        "G", "Newtonian constant of gravitation — the least precisely measured "
        "of the fundamental constants."),
    "fine_structure_constant": ("7.2973525693e-3", "dimensionless", "alpha",
        "Fine-structure constant, about 1/137 — the strength of the "
        "electromagnetic interaction, a pure number."),
    "electron_mass": ("9.1093837015e-31", "kilogram", "m_e",
        "Rest mass of the electron."),
    "proton_mass": ("1.67262192369e-27", "kilogram", "m_p",
        "Rest mass of the proton."),
    "neutron_mass": ("1.67492749804e-27", "kilogram", "m_n",
        "Rest mass of the neutron."),
    "vacuum_permittivity": ("8.8541878128e-12", "farad_per_metre", "epsilon_0",
        "Electric constant of vacuum, linking charge to electric field."),
    "vacuum_permeability": ("1.25663706212e-6", "henry_per_metre", "mu_0",
        "Magnetic constant of vacuum, linking current to magnetic field."),
    "gas_constant": ("8.314462618", "joule_per_mole_kelvin", "R",
        "Molar gas constant, the Boltzmann constant per mole."),
    "faraday_constant": ("96485.33212", "coulomb_per_mole", "F",
        "Charge of one mole of electrons."),
    "stefan_boltzmann_constant": ("5.670374419e-8", "watt_per_square_metre_kelvin_to_the_fourth",
        "sigma", "Total power radiated per unit area by a black body, per "
        "temperature to the fourth."),
    "rydberg_constant": ("10973731.568160", "per_metre", "R_infinity",
        "Rydberg constant — sets the wavelengths of hydrogen spectral lines; "
        "the most precisely measured constant in physics."),
    "bohr_radius": ("5.29177210903e-11", "metre", "a_0",
        "Bohr radius, the natural length scale of the hydrogen atom."),
    "bohr_magneton": ("9.2740100783e-24", "joule_per_tesla", "mu_B",
        "Bohr magneton, the natural unit of electron magnetic moment."),
    "atomic_mass_constant": ("1.66053906660e-27", "kilogram", "u",
        "One twelfth of the mass of a carbon-12 atom."),
    "classical_electron_radius": ("2.8179403262e-15", "metre", "r_e",
        "Classical electron radius, the length scale of Thomson scattering."),
    "magnetic_flux_quantum": ("2.067833848e-15", "weber", "Phi_0",
        "Flux quantum h/2e — the indivisible unit of magnetic flux in a "
        "superconducting loop."),
    "conductance_quantum": ("7.748091729e-5", "siemens", "G_0",
        "Conductance quantum 2e²/h — the step by which conductance changes in "
        "a quantum point contact."),
    "von_klitzing_constant": ("25812.80745", "ohm", "R_K",
        "Von Klitzing constant h/e² — the resistance plateau of the quantum "
        "Hall effect, now the resistance standard."),
    "wien_displacement_constant": ("2.897771955e-3", "metre_kelvin", "b",
        "Wien displacement constant: peak wavelength times temperature."),
    "planck_mass": ("2.176434e-8", "kilogram", "m_P",
        "Planck mass, where gravity and quantum effects meet."),
    "planck_length": ("1.616255e-35", "metre", "l_P",
        "Planck length, the scale at which spacetime itself is expected to "
        "need a quantum description."),
    "planck_time": ("5.391247e-44", "second", "t_P",
        "Planck time, light crossing one Planck length."),
    "coulomb_constant": ("8.9875517923e9", "newton_metre_squared_per_coulomb_squared",
        "k_e", "Coulomb constant 1/4πε₀ of the electrostatic force law."),
}


def from_formulas():
    """Кандидаты из разбора формул: имя → значение, единица, описание, формулы."""
    an = load(AN)
    out = {}
    for fid, r in an.items():
        for c in (r.get("constants") or []):
            cid = (c.get("id") or "").strip()
            if not cid:
                continue
            val = (c.get("value") or "").strip()
            desc = c.get("m") or ""
            if not numeric(val) or looks_param(cid, desc):
                continue
            d = out.setdefault(cid, {"value": val, "unit": c.get("unit") or "",
                                     "sym": c.get("s") or "", "desc": desc,
                                     "formulas": []})
            d["formulas"].append(fid)
            if len(desc) > len(d["desc"]):
                d["desc"] = desc
    return out


def articles_of(fids):
    """Статьи, где формула применяется, — константа получает опору через них."""
    bases = load(LINKED, {}).get("bases") or []
    by = {b["base_id"]: b for b in bases}
    arts = []
    for f in fids:
        b = by.get(f) or {}
        for a in (b.get("applications") or []):
            aid = a.get("article") or a.get("art") or ""
            if aid and aid not in arts:
                arts.append(aid)
    return arts[:40]


def main():
    apply = "--apply" in sys.argv
    codata = "--codata" in sys.argv
    live = load(LIVE).get("concepts") or {}
    cand = from_formulas()

    born, fixed, skipped = {}, {}, []
    for cid, d in sorted(cand.items()):
        cur = live.get(cid)
        if cur is None:
            born[cid] = {
                "kind": "constant", "group": "other", "scope": "general",
                "card_en": f'{d["desc"]} Value: {d["value"]}'
                           + (f' {d["unit"].replace("_", " ")}'
                              if d["unit"] and d["unit"] != "dimensionless" else ""),
                "value": d["value"], "unit": d["unit"], "symbol": d["sym"],
                "articles": articles_of(d["formulas"]),
                "origin": "formula-constant",
                "aliases": [],
            }
        elif cur.get("kind") != "constant":
            # Класс правим только при поддержке двух формул и больше. Одна формула
            # ошибается: она назвала «константой» и ускорение свободного падения
            # (величина, зависит от места), и непрозрачность (свойство вещества).
            # Две независимые формулы такую ошибку уже не повторяют.
            if len(d["formulas"]) >= 2:
                fixed[cid] = {"kind": "constant", "was": cur.get("kind"),
                              "why": f'формулы называют константой ({len(d["formulas"])})'}
            else:
                skipped.append(cid)
        else:
            skipped.append(cid)

    # Значение нужно и тем, кто в реестре давно. Постоянная Больцмана лежала там
    # с самого начала — классом constant, с описанием, но без числа. Такой записи
    # в копилку кладём ТОЛЬКО значение: kind и card_en у неё уже свои, из v3, и
    # перебивать их нечем.
    valued = {}
    for cid, d in cand.items():
        if cid in live and live[cid].get("kind") == "constant" and not live[cid].get("value"):
            valued[cid] = {"value": d["value"], "unit": d["unit"], "symbol": d["sym"]}

    if codata:
        for cid, (val, unit, sym, desc) in CODATA.items():
            cur = live.get(cid)
            if cur is not None and not cur.get("value"):
                valued[cid] = {"value": val, "unit": unit, "symbol": sym}
            if cur is None and cid not in born:
                born[cid] = {
                    "kind": "constant", "group": "other", "scope": "general",
                    "card_en": f"{desc} Value: {val}"
                               + (f' {unit.replace("_", " ")}'
                                  if unit != "dimensionless" else ""),
                    "value": val, "unit": unit, "symbol": sym,
                    "articles": [], "origin": "codata-core", "aliases": [],
                }
            elif cid in born:            # формула дала имя, СИ даёт точность
                born[cid]["value"] = val
                born[cid]["unit"] = unit
                born[cid]["symbol"] = sym
            elif cur is not None and cur.get("kind") != "constant":
                fixed.setdefault(cid, {"kind": "constant", "was": cur.get("kind"),
                                       "why": "фундаментальная константа СИ"})

    print(f"из формул кандидатов: {len(cand)} "
          f"(отсеяно параметров: {sum(1 for f in load(AN).values() for c in (f.get('constants') or []) if c.get('id')) - len(cand)})")
    print(f"рождается: {len(born)} · класс поправлен: {len(fixed)} "
          f"· значение дописано: {len(valued)} · без изменений: {len(skipped)}")
    for cid, b in sorted(born.items()):
        src = "СИ" if b["origin"] == "codata-core" else "формулы"
        print(f"  + {cid:32s} {b.get('value',''):18s} [{src}]")
    for cid, f in sorted(fixed.items()):
        print(f"  ~ {cid:32s} {f['was']} → constant · {f['why']}")

    if not apply:
        print("\nсухой ход. записать: --apply")
        return 0

    g = load(GROWN)
    for cid, b in born.items():
        g[cid] = b
    for cid, v in valued.items():
        rec = g.get(cid) or {}
        rec.update(v)
        g[cid] = rec
    GROWN.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
    kf = load(KINDFIX)
    for cid, f in fixed.items():
        kf[cid] = f["kind"]
    KINDFIX.write_text(json.dumps(kf, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nзаписано: копилка {len(g)} записей · правок класса {len(kf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
