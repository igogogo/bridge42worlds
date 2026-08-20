#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Портрет автора словами — БЕЗ модели, прямо из чисел.

Владелец 2026-08-19, глядя на сгенерированный моделью абзац: «такой текст запросто можно
динамически собрать, всё есть в базе у нас». Он прав, и это меняет всю экономику затеи.

ЧТО МОДЕЛЬ ДЕЛАЛА И ПОЧЕМУ ЭТО ЛИШНЕЕ. Ей давали шесть чисел (работ, годы, области, темы,
соавторы) и просили сложить из них два предложения. Ни одного факта сверх этих чисел она
не знала — значит, всё, что она умела, это перефразировать. За перефразирование мы платили
вызовом на каждого автора и получали взамен риск: модель то называла 216 соавторов «нулём»,
то добавляла оценки вроде «активное сотрудничество», которых в данных нет.

ЧТО ДАЁТ ОТКАЗ ОТ НЕЁ:
  · авторов у нас 45 101 — портрет становится бесплатным для ВСЕХ, а не для избранной сотни;
  · пять языков сразу, без переводчика и без утечки русского в арабскую версию;
  · текст пересобирается мгновенно при изменении данных — его можно считать на лету
    в облаке, а не печь в статический HTML;
  · воспроизводимость: одни и те же числа всегда дают один и тот же текст.

ЧТОБЫ НЕ ЗВУЧАЛО РОБОТОМ. Сорок пять тысяч одинаковых фраз — это шум, поэтому формулировка
выбирается по ФОРМЕ данных: у человека с работами в одной области и у человека с работами
в пяти — разные предложения; двадцать лет между первой и последней работой упоминаются,
три года молчат; одиночные работы и коллаборации описываются по-разному.

    python tools/author_phrase.py --show "A. D. Panov"
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Названия областей arXiv по-человечески: в тексте «astro-ph, nlin, physics» выглядит
# машинной выдачей, а «астрофизика, нелинейная динамика» читается.
FIELDS = {
    "astro-ph": {"ru": "астрофизика", "en": "astrophysics", "es": "astrofísica",
                 "fr": "astrophysique", "ar": "الفيزياء الفلكية"},
    "cond-mat": {"ru": "физика конденсированного состояния", "en": "condensed matter",
                 "es": "materia condensada", "fr": "matière condensée", "ar": "المادة المكثفة"},
    "hep-th": {"ru": "теория высоких энергий", "en": "high-energy theory",
               "es": "teoría de altas energías", "fr": "théorie des hautes énergies",
               "ar": "نظرية الطاقات العالية"},
    "hep-ph": {"ru": "феноменология частиц", "en": "particle phenomenology",
               "es": "fenomenología de partículas", "fr": "phénoménologie des particules",
               "ar": "ظواهر الجسيمات"},
    "hep-ex": {"ru": "эксперимент высоких энергий", "en": "high-energy experiment",
               "es": "experimento de altas energías", "fr": "expérience hautes énergies",
               "ar": "تجارب الطاقة العالية"},
    "gr-qc": {"ru": "гравитация и космология", "en": "gravitation and cosmology",
              "es": "gravitación y cosmología", "fr": "gravitation et cosmologie",
              "ar": "الجاذبية والكونيات"},
    "quant-ph": {"ru": "квантовая физика", "en": "quantum physics", "es": "física cuántica",
                 "fr": "physique quantique", "ar": "الفيزياء الكمية"},
    "nucl-th": {"ru": "теория ядра", "en": "nuclear theory", "es": "teoría nuclear",
                "fr": "théorie nucléaire", "ar": "النظرية النووية"},
    "nucl-ex": {"ru": "ядерный эксперимент", "en": "nuclear experiment",
                "es": "experimento nuclear", "fr": "expérience nucléaire", "ar": "التجارب النووية"},
    "nlin": {"ru": "нелинейная динамика", "en": "nonlinear dynamics", "es": "dinámica no lineal",
             "fr": "dynamique non linéaire", "ar": "الديناميكا اللاخطية"},
    "math": {"ru": "математика", "en": "mathematics", "es": "matemáticas",
             "fr": "mathématiques", "ar": "الرياضيات"},
    "math-ph": {"ru": "математическая физика", "en": "mathematical physics",
                "es": "física matemática", "fr": "physique mathématique",
                "ar": "الفيزياء الرياضية"},
    "cs": {"ru": "информатика", "en": "computer science", "es": "informática",
           "fr": "informatique", "ar": "علوم الحاسوب"},
    "q-bio": {"ru": "биология", "en": "biology", "es": "biología", "fr": "biologie",
              "ar": "علم الأحياء"},
    "physics": {"ru": "общая физика", "en": "general physics", "es": "física general",
                "fr": "physique générale", "ar": "الفيزياء العامة"},
    "stat": {"ru": "статистика", "en": "statistics", "es": "estadística",
             "fr": "statistiques", "ar": "الإحصاء"},
    "eess": {"ru": "техника и сигналы", "en": "engineering and signals",
             "es": "ingeniería y señales", "fr": "ingénierie et signaux", "ar": "الهندسة والإشارات"},
    "econ": {"ru": "экономика", "en": "economics", "es": "economía", "fr": "économie",
             "ar": "الاقتصاد"},
    "q-fin": {"ru": "финансы", "en": "finance", "es": "finanzas", "fr": "finance", "ar": "التمويل"},
}


def plural_ru(n, one, few, many):
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


_TAGS_LOC = {}


def tag_names(ids, lang, limit=2):
    """Названия тем на языке страницы.

    Первая версия брала готовые названия из русского справочника и вставляла их во все
    языки: английская страница получала «космические лучи», арабская тоже. Это ровно тот
    класс утечки языка, который у нас уже был на переводах статей — и появляется он всегда
    одинаково: когда текст собирают из заранее переведённого куска, а не из идентификатора.
    """
    if lang not in _TAGS_LOC:
        f = ROOT / f"lang/{lang}/data/tags.json"
        try:
            _TAGS_LOC[lang] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        except Exception:
            _TAGS_LOC[lang] = {}
    loc = _TAGS_LOC[lang]
    out = []
    for t in ids:
        nm = (loc.get(t) or {}).get("name") or t.replace("_", " ")
        if nm not in out:
            out.append(nm)
        if len(out) >= limit:
            break
    return out


def field_names(codes, lang):
    out = []
    for c in codes:
        name = FIELDS.get(c, {}).get(lang)
        if name and name not in out:
            out.append(name)
    return out


def compose(st, lang="ru"):
    """Два-три предложения из чисел. Ни одного факта сверх того, что посчитано."""
    n = st.get("papers", 0)
    y1, y2 = st.get("first_year"), st.get("last_year")
    span = (y2 - y1) if (y1 and y2) else 0
    fields = field_names(st.get("fields") or [], lang)
    topics = tag_names(st.get("top_tags") or [], lang)
    co = st.get("coauthors", 0)
    name = st.get("name", "")

    if lang == "ru":
        works = plural_ru(n, "работа", "работы", "работ")
        s1 = f"В нашем архиве разобрано {n} {works} этого автора"
        s1 += f", {y1}" + (f"–{y2} годов" if span else " года") + "."
        s2 = ""
        if topics:
            s2 = "Чаще всего в них встречается " + topics[0]
            if len(topics) > 1:
                s2 += " и " + topics[1]
            s2 += "."
        s3 = ""
        if len(fields) > 2:
            s3 = ("Работы лежат сразу в нескольких областях — "
                  + ", ".join(fields[:3]) + ", — то есть круг интересов широкий.")
        elif fields:
            s3 = "Область — " + fields[0] + "."
        s4 = ""
        if co >= 50:
            s4 = f"Соавторов в нашем архиве {co}: это работа в больших коллаборациях."
        elif co == 0 and n > 1:
            s4 = "Все разобранные работы написаны в одиночку."
        elif co:
            sci = plural_ru(co, "соавтор", "соавтора", "соавторов")
            s4 = f"Рядом в архиве {co} {sci}."
        if span >= 15:
            s4 += f" Между первой и последней работой {span} лет."
        return " ".join(x for x in (s1, s2, s3, s4) if x).strip()

    if lang == "es":
        s = [f"En nuestro archivo hay {n} trabajo{'s' if n != 1 else ''} de este autor, de {y1} a {y2}."]
        if topics:
            s.append("El tema más frecuente es " + " y ".join(topics) + ".")
        if len(fields) > 2:
            s.append("Los trabajos abarcan varias áreas: " + ", ".join(fields[:3]) + ".")
        elif fields:
            s.append("Área: " + fields[0] + ".")
        if co >= 50:
            s.append(f"Con {co} coautores en el archivo: trabajo en grandes colaboraciones.")
        elif co:
            s.append(f"Con {co} coautores en el archivo.")
        if span >= 15:
            s.append(f"Entre el primer y el último trabajo pasan {span} años.")
        return " ".join(s)

    if lang == "fr":
        s = [f"Notre archive contient {n} travaux de cet auteur" if n != 1 else "Notre archive contient 1 travail de cet auteur, de {y1} à {y2}."]
        if topics:
            s.append("Le thème le plus fréquent : " + " et ".join(topics) + ".")
        if len(fields) > 2:
            s.append("Les travaux couvrent plusieurs domaines : " + ", ".join(fields[:3]) + ".")
        elif fields:
            s.append("Domaine : " + fields[0] + ".")
        if co >= 50:
            s.append(f"{co} co-auteurs dans l'archive : travail en grandes collaborations.")
        elif co:
            s.append(f"{co} co-auteurs dans l'archive.")
        if span >= 15:
            s.append(f"{span} ans séparent le premier et le dernier travail.")
        return " ".join(s)

    if lang == "ar":
        s = [f"في أرشيفنا {n} من أعمال هذا الباحث، بين عامي {y1} و{y2}."]
        if topics:
            s.append("أكثر المواضيع تكرارًا: " + " و".join(topics) + ".")
        if len(fields) > 2:
            s.append("تمتد الأعمال عبر عدة مجالات: " + "، ".join(fields[:3]) + ".")
        elif fields:
            s.append("المجال: " + fields[0] + ".")
        if co >= 50:
            s.append(f"مع {co} مؤلفًا مشاركًا في الأرشيف: عمل ضمن تعاونات كبيرة.")
        elif co:
            s.append(f"مع {co} مؤلفًا مشاركًا في الأرشيف.")
        if span >= 15:
            s.append(f"بين أول عمل وآخره {span} عامًا.")
        return " ".join(s)

    s = [f"Our archive holds {n} paper{'s' if n != 1 else ''} by this author, from {y1} to {y2}."]
    if topics:
        s.append("The recurring subject is " + " and ".join(topics) + ".")
    if len(fields) > 2:
        s.append("The work spans several areas — " + ", ".join(fields[:3]) + ".")
    elif fields:
        s.append("Area: " + fields[0] + ".")
    if co >= 50:
        s.append(f"With {co} co-authors in our archive, this is work inside large collaborations.")
    elif co == 0 and n > 1:
        s.append("Every paper here is single-authored.")
    elif co:
        s.append(f"With {co} co-authors in our archive.")
    if span >= 15:
        s.append(f"{span} years separate the first paper from the latest.")
    return " ".join(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", required=True, help="имя автора из data/author-portraits.json")
    args = ap.parse_args()
    d = json.loads((ROOT / "data/author-portraits.json").read_text(encoding="utf-8"))
    e = d.get(args.show)
    if not e:
        print("нет такого автора в файле портретов")
        return 1
    for lang in ("ru", "en", "es", "fr", "ar"):
        print(f"\n[{lang}] {compose(e['stats'], lang)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
