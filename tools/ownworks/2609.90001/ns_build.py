# -*- coding: utf-8 -*-
"""Собрать data.json работы 2609.90001 из пяти языковых модулей и метаданных.

Первая работа не из arXiv в нашем архиве. Номер свой, из хвоста 900xx: формат YYMM.NNNNN
нужен, потому что из номера выводится месяц (drill.py, field_build.py), а 900xx на arXiv
не бывает — по номеру сразу видно, что работа наша. Всё остальное — как у обычной статьи,
плюс поля авторской работы (author_work, sources, review) и три новых: source_kind,
provenance, own_figures.

    python ns_build.py
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ns_ru, ns_en, ns_es, ns_ar, ns_fr  # noqa: E402
from latexify import latexify_tier  # noqa: E402

ROOT = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
AID, DATE = "2609.90001", "2026-09-08"
FOLDER = ROOT / "lang" / "ru" / "archive" / DATE / AID
MODS = {"ru": ns_ru, "en": ns_en, "es": ns_es, "ar": ns_ar, "fr": ns_fr}

TAGS = [ns_ru.MAIN_TAG] + ns_ru.EXTRA_TAGS


def tier(name):
    out = {}
    for lang, m in MODS.items():
        d = latexify_tier(m.DATA[name])
        d["main_tag"] = ns_ru.MAIN_TAG
        d["extra_tags"] = list(ns_ru.EXTRA_TAGS)
        d["scientists"] = list(ns_ru.SCIENTISTS)
        d["laws"] = list(ns_ru.LAWS)
        out[lang] = d
    return out


data = {
    "id": AID,
    "original_title": "Finite Time Blowup for Navier–Stokes",
    "authors": ["OpenAI"],
    "date": DATE,
    "license": "https://openai.com/policies/terms-of-use/",
    "license_name": "© OpenAI",
    "license_class": "analysis",
    "tags": TAGS,
    "tags_unverified": None,
    "main_tag": ns_ru.MAIN_TAG,
    "scientists": list(ns_ru.SCIENTISTS),
    "laws": list(ns_ru.LAWS),
    "categories": ["math.AP", "physics.flu-dyn"],
    "primary_category": "math.AP",
    # Работы, на которые опирается статья и которые есть на arXiv: Кордоба–Мартинес-Сороа
    # (сила для Эйлера, пористая среда), Тао (усреднённый НС), Бакмастер–Викол,
    # Албриттон–Брюэ–Коломбо. У нас в корпусе их пока нет — ссылки пойдут на arXiv.
    "cited_arxiv": ["2309.08495", "2410.22920", "1402.0290", "1709.10033", "2112.03116"],
    "cited_dois": ["10.4007/annals.2022.196.1.3", "10.4007/annals.2019.189.1.3",
                   "10.1002/cpa.3160350604", "10.1007/s00205-026-02198-0",
                   "10.1007/s00205-017-1081-8", "10.1070/RM2003v058n02ABEH000609",
                   "10.1007/BF02547354", "10.1017/S0022112005006464", "10.1017/jfm.2013.460",
                   "10.1103/PhysRevLett.66.2204", "10.1017/S0022112083000191",
                   "10.1063/1.858153", "10.1098/rspa.1986.0061", "10.1140/epjp/i2017-11659-5"],
    "threads": ns_ru.THREADS,
    "abstract": {lang: m.DATA["abstract"] for lang, m in MODS.items()},
    # Авторская аннотация — для машины (вектор, поиск); на странице класс analysis её не показывает.
    "abstract_orig": "For every positive viscosity, we construct a solution of the three-dimensional "
                     "incompressible Navier–Stokes equations that starts from rest and develops "
                     "unbounded velocity in finite time while maintaining uniformly bounded kinetic energy.",
    "thumbs": 0,
    "refined": True,
    "express": False,
    "express_tiers": [],
    "popular": tier("popular"),
    "simple": tier("simple"),
    "advanced": tier("advanced"),
    "image_pending": False,
    "image_model": "black-forest-labs/FLUX-2-pro",
    "captions": {},
    # ── работа не из arXiv ─────────────────────────────────────────────────
    "author_work": True,
    "source_kind": "external",
    "source_org": "OpenAI",
    "kind": "теоретическая работа",
    "code": AID,
    "sources": {
        "live": "https://openai.com/index/navier-stokes-solution/",
        "pdf": "https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf",
        "repo": "https://github.com/openai/NavierStokesAndEuler",
    },
    "source_labels": {lang: m.DATA["source_labels"] for lang, m in MODS.items()},
    "review": {lang: m.DATA["review"] for lang, m in MODS.items()},
    # кем сделано и чем проверено — признак, который владелец назвал сразу
    "made_by": "ai_agents",
    "verified_by": "lean",
    "provenance": {lang: m.DATA["provenance"] for lang, m in MODS.items()},
    # Рисунок OpenAI из анонса — первым, по прямому решению владельца 09.09 («возьми их
    # картинку»); подпись называет источник. Наша схема — второй, она подписана по частям
    # доказательства («схему нашу оставляй, конечно»).
    "own_figures": [{"file": "fig-0-openai.webp",
                     "caption": {"ru": "Иллюстрация OpenAI из анонса работы: спираль внутрь и вытягивание вдоль оси. © OpenAI",
                                 "en": "OpenAI's illustration from the announcement: inward spiral and axial stretching. © OpenAI",
                                 "es": "Ilustración de OpenAI del anuncio: espiral hacia dentro y estiramiento axial. © OpenAI",
                                 "ar": "رسم OpenAI من إعلان العمل: حلزون إلى الداخل وتمدد على طول المحور. © OpenAI",
                                 "fr": "Illustration d'OpenAI tirée de l'annonce : spirale vers l'intérieur et étirement axial. © OpenAI"}},
                    {"file": "fig-1.svg",
                     "caption": {lang: m.DATA["figure_caption"] for lang, m in MODS.items()}}],
}

FOLDER.mkdir(parents=True, exist_ok=True)
out = FOLDER / "data.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
sz = out.stat().st_size // 1024
words = sum(len(str(v).split()) for t in ("simple", "popular", "advanced") for v in data[t].values())
print(f"→ {out.relative_to(ROOT)} ({sz} КБ) · языков 5 · слов в уровнях ≈{words}")
for lang in MODS:
    for t in ("simple", "popular", "advanced"):
        d = data[t][lang]
        assert d.get("title") and d.get("oneliner") and d.get("description"), (lang, t)
        if t != "advanced":
            assert d.get("text"), (lang, t)
        else:
            for k in ("context", "methods", "results", "implications"):
                assert d.get(k), (lang, t, k)
    assert set(data["abstract"][lang]) == {"popular", "simple", "advanced"}, lang
print("проверка структуры: ок")
