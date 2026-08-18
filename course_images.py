"""Образные картинки к параграфам курса (FLUX-1-schnell, дёшево).

Одна картинка на параграф, лежит рядом с уроком: data/theory/courses/<тема>/img/<id>.jpg.
Поля в JSON не нужно — course.html и оглавление берут файл по имени урока.

Почему сюжеты прописаны руками, а не выведены из текста автоматически: FLUX хорошо рисует
КОНКРЕТНЫЕ предметы и плохо — абстракции. Просьба «петля, намекающая на цикл» дала ручку ведра
(см. F2 в COURSE-FEEDBACK). Поэтому у каждого параграфа свой предметный сюжет.

Картинки БЕЗ текста: тогда они не требуют перевода на четыре языка.

    python course_images.py            # только недостающие
    python course_images.py --force    # перерисовать всё
    python course_images.py --only atom/01-spectra
"""
import argparse
import sys
from pathlib import Path

import common  # noqa: F401  — подхватывает .env с ключом DeepInfra
import gen_llm

ROOT = Path("data/theory/courses")

# Общая часть промпта: та самая, что сработала на механике и термодинамике.
STYLE = ("editorial science illustration, warm cream paper background, "
         "muted ink teal and brass palette, soft grain, vintage textbook plate aesthetic, "
         "generous negative space, no text, no letters, no numbers, no labels")

# Сюжет каждого параграфа — предметами, а не понятиями.
SUBJECTS = {
    "atom/01-spectra": "a brass spectroscope and a glass prism splitting a light beam into separate bright stripes on a screen",
    # «гантель» FLUX понял буквально и нарисовал спортивный снаряд — просим предмет-модель
    "atom/02-orbitals": "two translucent glass demonstration models on a wooden laboratory stand, one a hollow sphere and one made of two rounded lobes meeting at a narrow waist",
    "atom/03-periodic": "a printer's wooden type case with empty square compartments arranged in a rising staircase pattern",
    "electricity/01-current": "a copper wire coil, a cylindrical resistor with colour bands and a single battery cell on a workbench",
    "electricity/02-magnetism": "a bar magnet under paper with iron filings arranged in curved lines, a small brass compass beside it",
    "electricity/03-induction": "a bar magnet sliding through a coil of copper wire connected to a galvanometer with a deflected needle",
    "electrostatics/01-coulomb": "two small pith balls hanging on silk threads from a stand, pushed apart from each other",
    "electrostatics/02-field": "two metal spheres on stands with curved lines drawn between them on gridded drafting paper",
    "electrostatics/03-potential": "a topographic relief plate with nested closed contour rings around two rounded hills",
    "entropy/01-microstates": "a shallow wooden box divided by a low partition, small ivory balls scattered unevenly on both sides",
    "entropy/02-arrow": "a broken porcelain teacup on a tiled floor with its shards spread outward, one intact cup standing nearby",
    "entropy/03-information": "a punched card and a row of small brass toggle switches, some up and some down",
    "gravity/01-kepler": "a brass orrery arm tracing an elongated elliptical path around a small sun, one shaded sector swept near the sun",
    "gravity/02-orbits": "a globe with concentric orbital rings and a tiny satellite, an arcing launch trajectory rising from the surface",
    "gravity/03-tides": "a globe wrapped in a stretched water envelope bulging on two opposite sides, the moon nearby",
    "language/01-models": "a folded paper map lying beside a small clay landscape model of the same valley",
    "language/02-scale": "a brass caliper, a folding ruler and a magnifying lens arranged from largest to smallest",
    "language/03-phase": "a pendulum on a stand and a spiral curve drawn on gridded paper beside it",
    "nuclear/01-nucleus": "a tight cluster of small spheres packed together, two shades mixed, held as if by invisible tension",
    "nuclear/02-decay": "a cluster of spheres with one tiny particle flying away, beside a stack of coins halving in height",
    "nuclear/03-energy": "a large sphere splitting into two smaller spheres with fragments, and beside it two tiny spheres merging into one",
    "optics/01-light": "an oil lamp behind a narrow slit, curved wavefronts spreading outward like ripples",
    "optics/02-refraction": "a pencil standing in a glass of water appearing broken at the surface, a glass prism beside the glass",
    "optics/03-colour": "a soap bubble with iridescent swirls and a small diffraction grating card catching light",
    "oscillations/01-rotation": "a turntable with a ball on a string swinging in a circle, its shadow cast as a line on the wall behind",
    "oscillations/02-hooke": "a coil spring hanging from a hook with a brass weight on its end, a vertical ruler beside it",
    "oscillations/03-resonance": "a thin wine glass beside a tuning fork, fine ripples visible on the liquid surface",
    "quantum/01-quanta": "a glowing hot metal plate in a dark workshop, tiny discrete packets of light leaving its surface",
    # без предметов сцены вышел абстрактный полосатый прямоугольник — ставим лампу, плиту и экран
    "quantum/02-waves": "a laboratory bench in three quarter view: a brass lamp on the left, an upright metal plate with two narrow vertical slits in the middle, and a separate white screen on the right showing alternating vertical bands",
    "quantum/03-uncertainty": "a magnifying lens held over a small sphere that appears blurred and smeared with motion",
    "relativity/01-postulates": "a railway carriage interior with a lantern beam bouncing between floor and ceiling mirrors",
    "relativity/02-time": "two identical brass pocket watches, one resting on a moving carriage step and one on a station platform",
    "relativity/03-energy": "a balance scale with a tiny sphere on one pan and a burst of radiating lines on the other",
    "waves/01-travelling": "a long rope tied to a post with a single hump travelling along it, a hand holding the free end",
    "waves/02-standing": "a plucked guitar string vibrating with still points along it, an organ pipe cut away beside it",
    "waves/03-interference": "a ripple tank with two dippers making overlapping circular waves that cross in a pattern",

    # Космология и теоретическая механика: у этих двух тем картинок не было вовсе, и каждая
    # загрузка урока уходила в 404 (находка QA). Сюжеты, как и везде, предметные: «расширение
    # Вселенной» FLUX рисует туманным пятном, а растянутая резинка с метками — это вещь.
    "cosmology/01-expansion": "a wide rubber band stretched between two brass pins on a wooden board, ink marks along it spaced further apart towards the right, a small ruler lying beside it",
    "cosmology/02-cmb": "a large white horn antenna on a concrete mount against an empty evening sky, an abandoned bird nest on the ground beside it",
    # «прибор без деталей» FLUX нарисовал целым — нехватка не читается. Просим весы: видимый
    # груз мал, а перевешивает пустая чаша, и это ровно то, что показали измерения масс.
    "cosmology/03-dark": "a brass balance scale on a workbench, one pan holding a single small sphere and raised high, the opposite pan empty yet tipped all the way down",
    # Три новые темы, закрывающие дыры первого курса. Сюжеты, как всегда, предметные:
    # «давление» и «перенос импульса» FLUX рисует туманом, а барометр и ложка в чашке — вещи.
    "fluids/01-hydrostatics": "a tall glass tube of mercury standing inverted in a shallow dish, a brass ruler beside it marking the height of the column",
    "fluids/02-bernoulli": "a brass venturi tube on a wooden stand, two vertical glass standpipes rising from it with water at different levels",
    "fluids/03-viscosity": "a glass jar of honey with a steel ball halfway down, and beside it a jar of water with an identical ball at the bottom",
    "statistical/01-maxwell": "an archery target riddled with arrows clustered densely near the centre and scattered thinly at the edges",
    "statistical/02-boltzmann": "a tall glass column of air with tiny dust motes, dense at the bottom and sparse towards the top, a barometer standing beside it",
    "statistical/03-brownian": "a drop of ink spreading in a glass of still water, a brass microscope leaning over it",
    "transport/01-diffusion": "a teabag resting in a glass of clear water with a soft plume of colour reaching out from it",
    "transport/02-conduction": "a metal spoon and a wooden spoon standing in the same cup of hot tea, faint steam above",
    "transport/03-viscosity-gas": "two brass cylinders side by side connected by a thin tube, a small paddle wheel between them",
    "analytical/01-action": "a wire loop dipped in soap solution held by a hand, the film stretched into a smooth curved surface",
    "analytical/02-lagrange": "a spinning top on a mirror table, its reflection perfectly symmetrical below it",
    "analytical/03-hamilton": "a pendulum clock with its case open, a paper chart beside it showing a single closed oval curve drawn in ink",
}


def lessons():
    """(тема, id, путь к картинке) для всех параграфов курса."""
    import json
    out = []
    for topic_dir in sorted(ROOT.iterdir()):
        if not topic_dir.is_dir():
            continue
        for f in sorted(topic_dir.glob("*.json")):
            if f.name in ("course.json", "guide.json"):
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            lid = data.get("id")
            if not lid:
                continue
            out.append((topic_dir.name, lid, topic_dir / "img" / f"{lid}.jpg"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="перерисовать даже то, что уже есть")
    ap.add_argument("--only", help="один параграф, например atom/01-spectra")
    ap.add_argument("--preset", default="image_cheap",
                    choices=["image", "image_cheap", "image_quality"])
    args = ap.parse_args()

    todo = []
    for topic, lid, path in lessons():
        key = f"{topic}/{lid}"
        if args.only and key != args.only:
            continue
        if path.exists() and not args.force:
            continue
        if key not in SUBJECTS:
            print(f"  ⚠️ нет сюжета для {key} — пропуск")
            continue
        todo.append((key, path))

    if not todo:
        print("Всё на месте, рисовать нечего.")
        return 0

    print(f"Рисую {len(todo)} шт. ({args.preset})")
    ok = 0
    for i, (key, path) in enumerate(todo, 1):
        path.parent.mkdir(parents=True, exist_ok=True)
        prompt = f"{SUBJECTS[key]}, {STYLE}"
        done, model = gen_llm.generate_image(prompt, str(path), preset=args.preset)
        mark = "✓" if done else "✗"
        print(f"  [{i}/{len(todo)}] {mark} {key}")
        if done:
            ok += 1
    print(f"Готово: {ok} из {len(todo)}")
    return 0 if ok == len(todo) else 1


if __name__ == "__main__":
    sys.exit(main())
