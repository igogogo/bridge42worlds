"""Чинит связи уроков с сайтом: битые ссылки и отсутствующие примеры из статей.

Что было не так.
  · Теги уроков — внутренние ярлыки курса («mechanics», «energy»), которых в словаре сайта нет.
    Страница делала из них ссылки, и читатель упирался в 404: 45 битых ссылок из 67.
  · Законы указаны под другими идентификаторами, чем в базе: `conservation_of_energy` вместо
    `law_of_conservation_of_energy`, `newtons_laws_of_motion` вместо трёх отдельных законов.
    Ещё 19 битых ссылок. Сами страницы при этом есть — чинится переименованием, а не написанием.
  · `examples_from_articles` не было ни у одного урока, а страница их и не показывала.

Теги подобраны вручную: автоподбор по тексту предлагал термодинамике тег «пульсар», а волнам —
«галактику». У нас архив астрофизический, поэтому связка честная только там, где физика урока
действительно встречается в статьях — это видно человеку, а не совпадению подстрок.

    B42_SITE_ROOT=../bridge42worlds python tools/relink.py --check
    B42_SITE_ROOT=../bridge42worlds python tools/relink.py
"""
import json
import os
import sys
from pathlib import Path

LANG = "ru"
LESSONS = Path("data/theory/courses")

# Идентификаторы законов в базе отличаются от тех, что стояли в уроках.
LAW_FIX = {
    "conservation_of_energy": ["law_of_conservation_of_energy"],
    "conservation_of_momentum": ["law_of_conservation_of_momentum"],
    "newtons_law_of_universal_gravitation": ["law_of_universal_gravitation"],
    "newtons_laws_of_motion": ["newtons_first_law", "newtons_second_law", "newtons_third_law"],
    "mass_energy_equivalence": ["massenergy_equivalence"],
    "keplers_laws_of_planetary_motion": ["keplers_first_law", "keplers_second_law", "keplers_third_law"],
    "special_relativity": ["lorentz_transformations"],
}

# Реальные теги сайта под каждый параграф: где эта физика встречается в нашем архиве.
TAGS = {
    "language/01-models": ["numerical_simulation", "information_theory"],
    "language/02-scale": ["numerical_simulation"],
    "language/03-phase": ["entropy", "quantum_thermodynamics"],
    "mechanics/01-kinematics": ["gravity"],
    "mechanics/02-newton": ["gravity"],
    "mechanics/03-conservation": ["gravitational_waves", "gravity"],
    "gravity/01-kepler": ["gravity", "exoplanet"],
    "gravity/02-orbits": ["gravity", "exoplanet", "transit_method"],
    "gravity/03-tides": ["gravity", "neutron_star"],
    "oscillations/01-rotation": ["pulsar", "neutron_star"],
    "oscillations/02-hooke": ["interferometry", "gravitational_waves"],
    "oscillations/03-resonance": ["interferometry", "gravitational_waves"],
    "waves/01-travelling": ["gravitational_waves"],
    "waves/02-standing": ["superposition"],
    "waves/03-interference": ["superposition", "interferometry"],
    "thermodynamics/01-molecules": ["plasma", "quantum_thermodynamics"],
    "thermodynamics/02-phase": ["phase_transition", "water"],
    "thermodynamics/03-engines": ["entropy", "quantum_thermodynamics"],
    "entropy/01-microstates": ["entropy", "quantum_thermodynamics"],
    "entropy/02-arrow": ["entropy", "spacetime_curvature"],
    "entropy/03-information": ["information_theory", "entropy", "quantum_information"],
    "electrostatics/01-coulomb": ["electromagnetism"],
    "electrostatics/02-field": ["electromagnetism"],
    "electrostatics/03-potential": ["electromagnetism"],
    "electricity/01-current": ["electromagnetism", "superconductivity"],
    "electricity/02-magnetism": ["magnetic_reconnection", "magnetar"],
    "electricity/03-induction": ["electromagnetism", "magnetar"],
    "optics/01-light": ["speed_of_light", "electromagnetism"],
    "optics/02-refraction": ["spectroscopy", "gravitational_lensing"],
    "optics/03-colour": ["spectroscopy", "photometry"],
    "relativity/01-postulates": ["speed_of_light", "spacetime_curvature"],
    "relativity/02-time": ["time_dilation", "spacetime_curvature"],
    "relativity/03-energy": ["spacetime_curvature", "nucleosynthesis"],
    "quantum/01-quanta": ["quantum_field", "quantum_optics"],
    "quantum/02-waves": ["waveparticle_duality", "quantum_field"],
    "quantum/03-uncertainty": ["quantum_measurement", "wave_function_collapse"],
    "atom/01-spectra": ["spectroscopy", "hydrogen"],
    "atom/02-orbitals": ["quantum_field", "hydrogen"],
    "atom/03-periodic": ["nucleosynthesis", "carbon"],
    "nuclear/01-nucleus": ["nucleosynthesis", "neutron_star"],
    "nuclear/02-decay": ["nucleosynthesis", "supernova"],
    "nuclear/03-energy": ["nucleosynthesis", "sun", "supernova"],
    "analytical/01-action": ["numerical_simulation", "quantum_field"],
    "analytical/02-lagrange": ["standard_model", "quantum_field"],
    "analytical/03-hamilton": ["entropy", "quantum_information"],
}

# Законы, которых в уроке не стояло вовсе. Страницы всех этих законов в базе есть —
# добавляем, чтобы у каждого параграфа была опора на закон, а не только на теги.
LAWS_ADD = {
    "optics/01-light": ["planckeinstein_relation"],
    "optics/03-colour": ["braggs_law", "wiens_displacement_law"],
    "waves/01-travelling": ["superposition_principle"],
    "waves/02-standing": ["superposition_principle"],
    "waves/03-interference": ["superposition_principle", "doppler_effect"],
    "quantum/01-quanta": ["plancks_law", "planckeinstein_relation"],
    "quantum/02-waves": ["superposition_principle"],
    "quantum/03-uncertainty": ["heisenberg_uncertainty_principle"],
    "atom/01-spectra": ["planckeinstein_relation"],
    "atom/02-orbitals": ["pauli_exclusion_principle"],
    "atom/03-periodic": ["pauli_exclusion_principle"],
    "electricity/02-magnetism": ["amperes_law"],
    "electrostatics/01-coulomb": ["coulombs_law"],
    "oscillations/02-hooke": ["hookes_law"],
    "language/03-phase": ["stefanboltzmann_law"],
    "nuclear/02-decay": ["massenergy_equivalence"],
    "analytical/01-action": ["law_of_conservation_of_energy"],
    "analytical/02-lagrange": ["law_of_conservation_of_momentum", "law_of_conservation_of_angular_momentum"],
    "analytical/03-hamilton": ["law_of_conservation_of_energy"],
}


def site_root():
    probe = f"lang/{LANG}/tags"
    if Path(probe).exists():
        return Path(".")
    env = os.environ.get("B42_SITE_ROOT")
    if env and (Path(env) / probe).exists():
        return Path(env)
    for sib in sorted(Path("..").iterdir()):
        if sib.is_dir() and (sib / probe).exists():
            return sib
    raise SystemExit("Не найден собранный сайт. Укажите B42_SITE_ROOT=../bridge42worlds")


def articles_for(tags, idx, limit=3):
    """Статьи с наибольшим пересечением по тегам, свежие вперёд. Разные версии одной — одна."""
    scored = []
    for a in idx:
        common = set(a.get("tags") or []) & set(tags)
        if common:
            scored.append((len(common), a.get("date", ""), a["id"], sorted(common),
                           (a.get("title") or "").strip()))
    scored.sort(reverse=True)
    out, seen = [], set()
    for _, date, aid, common, title in scored:
        base = aid.split("v")[0]
        if base in seen:
            continue
        seen.add(base)
        # ссылка на статью собирается как /lang/<яз>/archive/<дата>/<id>/ — дату сохраняем
        # название статьи — то, что читатель увидит ссылкой; тег остаётся пояснением
        out.append({"id": aid, "date": date, "title": title, "why": ", ".join(common[:3])})
        if len(out) >= limit:
            break
    return out


def main():
    root = site_root()
    check = "--check" in sys.argv
    idx = json.loads((root / f"lang/{LANG}/articles-index.json").read_text(encoding="utf-8"))
    # Названия статей нужны на всех четырёх языках: иначе на английской странице курса
    # появятся русские заголовки — ровно та утечка, которую только что вычистили.
    titles = {}
    for lang in ("ru", "en", "es", "ar"):
        p = root / f"lang/{lang}/articles-index.json"
        if not p.exists():
            continue
        for a in json.loads(p.read_text(encoding="utf-8")):
            titles.setdefault(a["id"], {})[lang] = (a.get("title") or "").strip()

    unknown_tags, stats = [], {"tags": 0, "laws": 0, "arts": 0, "nolinks": []}
    for f in sorted(LESSONS.rglob("*.json")):
        if not f.name[0].isdigit():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        key = f"{f.parent.name}/{d.get('id')}"
        ent = d.setdefault("entities", {})

        tags = TAGS.get(key, [])
        for t in tags:
            if not (root / f"lang/{LANG}/tags/{t}.html").exists():
                unknown_tags.append(f"{key}: {t}")

        laws, seen = [], set()
        for l in (ent.get("laws") or []) + LAWS_ADD.get(key, []):
            for fixed in LAW_FIX.get(l, [l]):
                if fixed in seen:
                    continue
                if (root / f"lang/{LANG}/laws/{fixed}.html").exists():
                    seen.add(fixed)
                    laws.append(fixed)

        arts = articles_for(tags, idx) if tags else []
        for a in arts:
            a["title"] = titles.get(a["id"], {"ru": a.get("title", "")})
        stats["tags"] += bool(tags)
        stats["laws"] += bool(laws)
        stats["arts"] += bool(arts)
        if not arts:
            stats["nolinks"].append(key)

        if check:
            print(f"{key:32} теги {len(tags)} · законы {len(laws)} · статей {len(arts)}")
            continue

        ent["tags"] = tags
        ent["laws"] = laws
        ent["examples_from_articles"] = arts
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"\nуроков 42 · с тегами {stats['tags']} · с законами {stats['laws']} · со статьями {stats['arts']}")
    if unknown_tags:
        print("ТЕГОВ НЕТ В БАЗЕ (исправить в TAGS):")
        for u in unknown_tags:
            print("   " + u)
    if stats["nolinks"]:
        print("без статей: " + ", ".join(stats["nolinks"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
