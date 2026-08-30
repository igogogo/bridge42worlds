"""Разводит две семантики допуска у числовых прикидок курса по разным полям.

Было: одно поле `tolerance` и два разных смысла. Грейдер понимал его как МНОЖИТЕЛЬ
(засчитать, если ответ отличается не больше чем в tolerance раз), а авторы половины тем
писали туда АБСОЛЮТНУЮ погрешность («200 ± 30 Мпк»). Последствия:
  · девять вопросов не проходились никогда, включая точный авторский ответ (tolerance < 1 —
    как множитель такое условие невыполнимо в принципе);
  · «5000 эВ ± 200» превращалось в «принимаю всё от 25 до миллиона»;
  · «10 бит ± 1» — в «только ровно 10».

Стало: семантика написана в данных явно — `tolAbs` или `tolFactor`. Правило проверки живёт
в js/quiz-grade.js и им же пользуется проверочный скрипт tools/quiz_check.js.

Решение по каждому вопросу принято поимённо, а не эвристикой: у одинаковых на вид чисел
смысл разный. «499 кПа, 1.5» — это множитель (±1,5 кПа для прикидки в уме абсурдно узко),
а «990 Гц, 50» — абсолютная погрешность (множитель 50 принял бы всё подряд).

    python tools/quiz_tolerance_fix.py --check   показать, что будет сделано
    python tools/quiz_tolerance_fix.py           записать
"""
import json
import sys
from pathlib import Path

ROOT = Path("data/theory/courses")
# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS

# урок/вопрос → (вид допуска, величина). Величина взята из авторского tolerance:
# нигде не меняем ЧИСЛО, меняем только то, как оно читается.
DECISION = {
    # ── абсолютная погрешность: число написано в единицах ответа ──────────────────
    "analytical/01-action:a4": ("abs", 2),          # 9,9 Дж·с ± 2
    "analytical/02-lagrange:n4": ("abs", 1.5),      # 8 рад/с ± 1,5
    "atom/01-spectra:sp4": ("abs", 1),              # 10,2 эВ ± 1
    "atom/02-orbitals:o4": ("abs", 2),              # 32 электрона ± 2
    "atom/03-periodic:pe4": ("abs", 2),             # 18 элементов ± 2
    "cosmology/01-expansion:c4": ("abs", 30),       # 200 Мпк ± 30
    "cosmology/02-cmb:m4": ("abs", 20),             # 100 мкм ± 20
    "cosmology/03-dark:d4": ("abs", 25),            # 93 млрд масс Солнца ± 25
    "electricity/01-current:e4": ("abs", 1),        # 10 А ± 1
    "electricity/02-magnetism:m4": ("abs", 0.04),   # 1,08 раза ± 0,04 — был непроходим
    "electricity/03-induction:n4": ("abs", 5),      # 44 раза ± 5
    "electrostatics/01-coulomb:c4": ("abs", 2),     # порядок 42 ± 2 (это показатель степени)
    "electrostatics/02-field:f4": ("abs", 6),       # 30 кВ ± 6
    "electrostatics/03-potential:p4": ("abs", 200), # 5000 эВ ± 200 — принимал от 25 до миллиона
    "entropy/01-microstates:e4": ("abs", 2),        # порядок 29 ± 2
    "entropy/02-arrow:a4": ("abs", 5),              # порядок 20 ± 5
    "entropy/03-information:i4": ("abs", 1),        # 10 бит ± 1
    "gravity/01-kepler:g4": ("abs", 1),             # 8 раз ± 1
    "gravity/02-orbits:o4": ("abs", 0.6),           # 5,6 км/с ± 0,6 — был непроходим
    "gravity/03-tides:t4": ("abs", 1),              # 8 раз ± 1
    "language/01-models:m4": ("abs", 0.15),         # 0,3 % ± 0,15 — был непроходим
    "language/02-scale:s4": ("abs", 5),             # 12,5 м/с ± 5
    "language/03-phase:p4": ("abs", 1),             # порядок 32 ± 1
    "mechanics/01-kinematics:k3": ("abs", 1.4),     # 3,5 м/с² ± 1,4
    "mechanics/02-newton:n4": ("abs", 1.3),         # 3,6 кН ± 1,3
    "nuclear/01-nucleus:n4": ("abs", 0.5),          # 7,1 МэВ ± 0,5 — был непроходим
    "nuclear/02-decay:d4": ("abs", 2),              # 17,2 тыс. лет ± 2
    "nuclear/03-energy:f4": ("abs", 1),             # 3 тыс. тонн ± 1
    "optics/01-light:l4": ("abs", 1),               # порядок 14 ± 1
    "optics/02-refraction:r4": ("abs", 0.3),        # 2,25 м ± 0,3 — был непроходим
    "optics/03-colour:c4": ("abs", 1.5),            # 5,9 раза ± 1,5
    "oscillations/01-rotation:r4": ("abs", 1.4),    # 5,5 м/с² ± 1,4
    "oscillations/03-resonance:r4": ("abs", 4),     # 20 раз ± 4
    "quantum/01-quanta:q4": ("abs", 0.4),           # 2,5 эВ ± 0,4 — был непроходим
    "quantum/02-waves:w4": ("abs", 1),              # порядок −10 ± 1 — отрицательный ответ
    "relativity/01-postulates:s4": ("abs", 0.1),    # γ = 1,25 ± 0,1 — был непроходим
    "relativity/02-time:t4": ("abs", 0.15),         # 1,67 раза ± 0,15 — был непроходим
    "relativity/03-energy:e4": ("abs", 1),          # порядок 14 ± 1
    "waves/01-travelling:w4": ("abs", 10),          # 77 см ± 10
    "waves/02-standing:s4": ("abs", 50),            # 990 Гц ± 50 — принимал от 20 до 49 500
    "waves/03-interference:i4": ("abs", 30),        # 137 нм ± 30

    # ── множитель: ответ оценивается по порядку, «в разы» ─────────────────────────
    "analytical/03-hamilton:h4": ("factor", 10),    # 5·10³² состояний — тут только порядок
    "mechanics/03-conservation:c4": ("factor", 1.3),
    "oscillations/02-hooke:h4": ("factor", 1.5),    # 0,63 с — ±1,5 с было бы шире самого ответа
    "quantum/03-uncertainty:u4": ("factor", 3),     # 4 эВ, вопрос именно про порядок
    "thermodynamics/01-molecules:m3": ("factor", 1.5),   # 499 кПа: ±1,5 кПа для «в уме» абсурд
    "thermodynamics/02-phase:p3": ("factor", 1.5),       # 2260 кДж — то же самое
    "thermodynamics/03-engines:e4": ("factor", 1.3),     # 62 %
}


def main():
    check = "--check" in sys.argv
    seen, changed, missing = set(), 0, []
    for f in sorted(ROOT.glob("*/[0-9]*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        lesson = f.parent.name + "/" + d.get("id", f.stem)
        touched = False
        for lang in LANGS:
            for q in ((d.get(lang) or {}).get("quiz") or []):
                if q.get("type") != "estimate":
                    continue
                key = lesson + ":" + str(q.get("id"))
                seen.add(key)
                dec = DECISION.get(key)
                if not dec:
                    missing.append(key)
                    continue
                kind, val = dec
                field = "tolAbs" if kind == "abs" else "tolFactor"
                if q.get(field) == val and "tolerance" not in q:
                    continue
                q.pop("tolerance", None)
                q.pop("tolAbs", None)
                q.pop("tolFactor", None)
                q[field] = val
                touched = True
                if lang == "ru":
                    changed += 1
                    if check:
                        print("  %-34s %-4s → %s %s" % (lesson, q.get("id"), field, val))
        if touched and not check:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print("вопросов-прикидок: %d | переведено на явную семантику: %d" % (len(seen), changed))
    unknown = sorted(set(missing))
    if unknown:
        print("⚠️ нет решения для: " + ", ".join(unknown))
        print("   допиши их в DECISION — иначе они останутся со старым полем tolerance")
    stale = sorted(set(DECISION) - seen)
    if stale:
        print("⚠️ в таблице есть лишние ключи (вопрос переименован или удалён): " + ", ".join(stale))
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
