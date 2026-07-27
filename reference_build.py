"""Справочник формул и констант — собирается из курса, а не пишется отдельно.

Формулы, авторы и константы уже описаны в уроках. Если переписать их в отдельный файл, две копии
разойдутся при первой же правке урока. Поэтому справочник — производная величина: пересобирается
одной командой и всегда совпадает с курсом, включая переводы.

Запуск:  python reference_build.py
"""
import json
import os
from pathlib import Path

os.chdir(Path(__file__).parent)
COURSES = Path("data/theory/courses")
OUT = Path("data/theory/reference.json")
LANGS = ["ru", "en", "es", "ar"]

UI = {
    "ru": {
        "title": "Справочник: формулы, константы, принципы",
        "subtitle": "Всё, что выведено в курсе, — на одной странице",
        "lead": "Здесь собрано то, что в курсе выводится подробно: главные уравнения с расшифровкой "
                "каждого символа, физические константы с единицами и мнемоникой, а также сквозные "
                "принципы, которые работают сразу в нескольких разделах. Каждая карточка ведёт в "
                "параграф, где показано, откуда это взялось.",
        "formulas": "Формулы", "constants": "Константы", "principles": "Принципы",
        "openLesson": "разбор в параграфе", "symbols": "обозначения",
        "search": "Поиск по формуле, символу или названию…", "nothing": "Ничего не нашлось",
    },
    "en": {
        "title": "Reference: formulas, constants, principles",
        "subtitle": "Everything derived in the course, on one page",
        "lead": "This gathers what the course derives step by step: the main equations with every "
                "symbol explained, physical constants with units and memory hooks, and the "
                "cross-cutting principles that work across several topics. Each card links to the "
                "paragraph where it comes from.",
        "formulas": "Formulas", "constants": "Constants", "principles": "Principles",
        "openLesson": "worked out in the paragraph", "symbols": "notation",
        "search": "Search by formula, symbol or name…", "nothing": "Nothing found",
    },
    "es": {
        "title": "Referencia: fórmulas, constantes, principios",
        "subtitle": "Todo lo deducido en el curso, en una sola página",
        "lead": "Aquí se reúne lo que el curso deduce paso a paso: las ecuaciones principales con "
                "cada símbolo explicado, las constantes físicas con unidades y reglas "
                "mnemotécnicas, y los principios transversales que valen para varios temas. Cada "
                "ficha enlaza con el párrafo del que procede.",
        "formulas": "Fórmulas", "constants": "Constantes", "principles": "Principios",
        "openLesson": "deducción en el párrafo", "symbols": "notación",
        "search": "Buscar por fórmula, símbolo o nombre…", "nothing": "No se encontró nada",
    },
    "ar": {
        "title": "المرجع: الصيغ والثوابت والمبادئ",
        "subtitle": "كل ما اشتُقّ في المقرر، في صفحة واحدة",
        "lead": "هنا يُجمع ما يشتقّه المقرر خطوة بخطوة: المعادلات الأساسية مع شرح كل رمز، والثوابت "
                "الفيزيائية بوحداتها ووسائل تذكّرها، والمبادئ الجامعة التي تسري على عدة مواضيع. "
                "وكل بطاقة تقود إلى الفقرة التي جاءت منها.",
        "formulas": "الصيغ", "constants": "الثوابت", "principles": "المبادئ",
        "openLesson": "الاشتقاق في الفقرة", "symbols": "الرموز",
        "search": "ابحث بالصيغة أو الرمز أو الاسم…", "nothing": "لا نتائج",
    },
}

# Сквозные принципы: они не принадлежат одному параграфу, поэтому описаны здесь.
PRINCIPLES = [
    {"id": "conservation", "icon": "scale", "topics": ["mechanics", "thermodynamics", "atom"],
     "ru": {"h": "Законы сохранения", "t": "Если условия опыта не меняются при сдвиге во времени, месте или повороте, найдётся величина, которая не меняется вовсе: энергия, импульс, момент импульса. Теорема Нётер превращает симметрию в закон сохранения."},
     "en": {"h": "Conservation laws", "t": "If the setup is unchanged by a shift in time, place or orientation, some quantity stays fixed: energy, momentum, angular momentum. Noether's theorem turns a symmetry into a conservation law."},
     "es": {"h": "Leyes de conservación", "t": "Si el experimento no cambia al desplazarlo en el tiempo, el lugar o el giro, hay una magnitud que no cambia: energía, momento lineal, momento angular. El teorema de Noether convierte una simetría en una ley de conservación."},
     "ar": {"h": "قوانين الحفظ", "t": "إذا لم تتغيّر التجربة بإزاحة في الزمان أو المكان أو بالدوران، فثمّة مقدار لا يتغيّر: الطاقة أو الزخم أو الزخم الزاوي. مبرهنة نويتر تحوّل التناظر إلى قانون حفظ."}},
    {"id": "leastaction", "icon": "sigma", "topics": ["mechanics", "optics", "quantum"],
     "ru": {"h": "Принцип наименьшего действия", "t": "Из всех мыслимых путей природа выбирает тот, на котором действие принимает крайнее значение. Из одного этого принципа выводятся и механика, и оптика, и уравнения поля."},
     "en": {"h": "Principle of least action", "t": "Of all conceivable paths, nature takes the one where the action is extremal. Mechanics, optics and field equations all follow from this single principle."},
     "es": {"h": "Principio de acción mínima", "t": "De todos los caminos posibles, la naturaleza elige aquel en que la acción es extrema. De este único principio se deducen la mecánica, la óptica y las ecuaciones de campo."},
     "ar": {"h": "مبدأ الفعل الأصغر", "t": "من بين كل المسارات الممكنة تختار الطبيعة ما يكون الفعل عنده متطرفاً. ومن هذا المبدأ وحده تُشتقّ الميكانيكا والبصريات ومعادلات المجال."}},
    {"id": "superposition", "icon": "sigma", "topics": ["waves", "electrostatics", "quantum"],
     "ru": {"h": "Суперпозиция", "t": "Пока уравнение линейно, отклики складываются: два источника дают сумму своих полей, две волны — сумму смещений. Отсюда интерференция и весь спектральный подход."},
     "en": {"h": "Superposition", "t": "While the equation is linear, responses add up: two sources give the sum of their fields, two waves the sum of displacements. Interference and the whole spectral approach follow."},
     "es": {"h": "Superposición", "t": "Mientras la ecuación sea lineal, las respuestas se suman: dos fuentes dan la suma de sus campos, dos ondas la suma de desplazamientos. De ahí la interferencia y todo el enfoque espectral."},
     "ar": {"h": "التراكب", "t": "ما دامت المعادلة خطية فالاستجابات تُجمع: مصدران يعطيان مجموع مجاليهما، وموجتان مجموع إزاحتيهما. ومن هنا يأتي التداخل والمنهج الطيفي كله."}},
    {"id": "irreversible", "icon": "clock", "topics": ["thermodynamics", "entropy"],
     "ru": {"h": "Стрела времени", "t": "Уравнения механики одинаково работают в обе стороны времени, а мир — нет. Разницу создаёт статистика: состояний беспорядка несравнимо больше, поэтому энтропия растёт."},
     "en": {"h": "Arrow of time", "t": "The equations of mechanics run equally well both ways in time; the world does not. Statistics makes the difference: disordered states are incomparably more numerous, so entropy grows."},
     "es": {"h": "Flecha del tiempo", "t": "Las ecuaciones de la mecánica funcionan igual en ambos sentidos del tiempo; el mundo no. La diferencia la crea la estadística: los estados desordenados son incomparablemente más numerosos, así que la entropía crece."},
     "ar": {"h": "سهم الزمن", "t": "معادلات الميكانيكا تعمل في اتجاهي الزمن سواءً بسواء، أما العالم فلا. الفارق تصنعه الإحصاء: حالات الفوضى أكثر بما لا يُقاس، ولذلك تتزايد الإنتروبيا."}},
    {"id": "quantization", "icon": "hash", "topics": ["quantum", "atom", "nuclear"],
     "ru": {"h": "Квантование", "t": "Запертая в области волна может иметь лишь избранные частоты — как струна. Отсюда дискретные уровни атома, спектральные линии и устойчивость вещества."},
     "en": {"h": "Quantisation", "t": "A wave confined to a region can only have selected frequencies, like a string. Hence the discrete levels of the atom, spectral lines and the stability of matter."},
     "es": {"h": "Cuantización", "t": "Una onda confinada en una región solo admite ciertas frecuencias, como una cuerda. De ahí los niveles discretos del átomo, las líneas espectrales y la estabilidad de la materia."},
     "ar": {"h": "التكميم", "t": "الموجة المحصورة في منطقة لا تقبل إلا ترددات مختارة، كالوتر. ومن هنا مستويات الذرة المنفصلة والخطوط الطيفية واستقرار المادة."}},
    {"id": "relativityp", "icon": "ruler", "topics": ["relativity", "gravity"],
     "ru": {"h": "Принцип относительности", "t": "Законы природы одинаковы во всех инерциальных системах, а скорость света одна для всех наблюдателей. Из этих двух утверждений следует всё остальное, включая связь массы и энергии."},
     "en": {"h": "Principle of relativity", "t": "The laws of nature are the same in every inertial frame, and the speed of light is the same for all observers. Everything else follows from these two statements, mass–energy equivalence included."},
     "es": {"h": "Principio de relatividad", "t": "Las leyes de la naturaleza son iguales en todos los sistemas inerciales y la velocidad de la luz es la misma para todos los observadores. De estas dos afirmaciones se sigue todo lo demás, incluida la equivalencia masa-energía."},
     "ar": {"h": "مبدأ النسبية", "t": "قوانين الطبيعة واحدة في كل الأطر العطالية، وسرعة الضوء واحدة لكل الراصدين. ومن هذين القولين يتبع كل ما عداهما، ومنه تكافؤ الكتلة والطاقة."}},
    {"id": "dimension", "icon": "ruler", "topics": ["language"],
     "ru": {"h": "Анализ размерностей", "t": "Единицы в правой и левой части обязаны совпадать. Проверка занимает секунды и ловит большинство ошибок, а иногда даёт вид формулы без всякого вывода."},
     "en": {"h": "Dimensional analysis", "t": "Units on both sides must match. The check takes seconds, catches most mistakes and sometimes hands you the shape of the formula with no derivation at all."},
     "es": {"h": "Análisis dimensional", "t": "Las unidades de ambos lados deben coincidir. La comprobación lleva segundos, detecta la mayoría de los errores y a veces da la forma de la fórmula sin deducción alguna."},
     "ar": {"h": "التحليل البُعدي", "t": "يجب أن تتطابق الوحدات في الطرفين. الفحص يستغرق ثوانٍ ويلتقط معظم الأخطاء، وأحياناً يعطي شكل الصيغة دون أي اشتقاق."}},
]


def build():
    out = {"schema": "b42.reference/1",
           "note": "Собран из уроков курса скриптом reference_build.py — правьте урок, не этот файл.",
           "principles": PRINCIPLES}
    for lang in LANGS:
        out[lang] = dict(UI[lang])
        out[lang]["formulas"] = UI[lang]["formulas"]

    formulas, missing = [], 0
    for cj in sorted(COURSES.glob("*/course.json")):
        topic = cj.parent.name
        for lf in sorted(p for p in cj.parent.glob("*.json") if p.name[0].isdigit()):
            d = json.loads(lf.read_text(encoding="utf-8"))
            row = {"topic": topic, "lesson": lf.stem, "model": d.get("model"),
                   "tags": d.get("tags") or [], "laws": d.get("laws") or []}
            got = False
            for lang in LANGS:
                br = d.get(lang) or {}
                f = br.get("formula")
                if not isinstance(f, dict) or not f.get("latex"):
                    continue
                row[lang] = {
                    "name": f.get("name"), "latex": f.get("latex"),
                    "alsoKnown": f.get("alsoKnown"),
                    "authors": [{"who": a.get("who"), "year": a.get("year")}
                                for a in (f.get("authors") or [])],
                    "symbols": f.get("symbols") or [],
                    "title": br.get("title"),
                }
                got = True
            if got:
                formulas.append(row)
            else:
                missing += 1
    out["formulas"] = formulas

    # В constants.json константы лежат словарём по символу — разворачиваем в список,
    # чтобы страница просто шла по нему и не знала про формат хранения.
    consts = json.loads(Path("data/theory/constants.json").read_text(encoding="utf-8"))
    items = consts.get("items") or {}
    if isinstance(items, dict):
        items = [dict(v, sym=k) for k, v in items.items()]
    out["constants"] = items

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"формул: {len(formulas)} · констант: {len(out['constants'])} · "
          f"принципов: {len(PRINCIPLES)}" + (f" · без формулы: {missing}" if missing else ""))


if __name__ == "__main__":
    build()
