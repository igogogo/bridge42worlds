#!/usr/bin/env python3
"""LLM-слой генерации статей (отбор, 3 уровня, перевод, промт картинки, сама картинка).

Все вызовы — через common.chat(agent, prompt): модель/температура/max_tokens берутся из
config.agents (select / article_advanced / article_simple / article_popular / translate /
image_prompt / image). Языковой guard (_default_lang_ok) не даёт RU-генерации свалиться в
английский на кросс-доменных статьях.
"""

import os
import re
import json
import random
from pathlib import Path
from openai import OpenAI

from common import CONFIG, AGENTS, DEFAULT_LANG, LANG_DIR, chat, clean_json, load_prompt

SELECTION_PERCENT = CONFIG.get("selection_percent", 10)
MAX_ARTICLES = CONFIG.get("max_articles", 10)

LANG_NAMES = {
    "ru": "Russian", "en": "English", "cn": "Chinese", "zh": "Chinese",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "nl": "Dutch",
}

CULTURE_NOTES = {
    "ar": ("ПРАВИЛО АНАЛОГИЙ (для всех языков): аналогию заменяй ТОЛЬКО если она непереводима или незнакома целевой аудитории; во всех остальных случаях переводи как есть. Молча «адаптировать» без причины нельзя. Алкогольные аналогии не используются ни в каком языке. В key_numbers переводятся И значения, И КЛЮЧИ словаря. "
           "ТЕРМИНОЛОГИЯ: используй принятые арабские научные термины; при ПЕРВОМ появлении термина дай латинский термин в скобках — это норма чтения для университетской аудитории Залива. "
           "ВАЖНО — КУЛЬТУРНАЯ АДАПТАЦИЯ ДЛЯ АРАБСКОЙ И МУСУЛЬМАНСКОЙ АУДИТОРИИ (в т.ч. читатели "
           "из университетов стран Персидского залива, включая Кувейт — материал рассчитан на "
           "академическую, а не только массовую аудиторию): переводи с уважением к исламским "
           "ценностям и обычаям. Избегай аналогий и примеров, связанных с алкоголем, свининой, "
           "азартными играми, романтическими или интимными отношениями, откровенными описаниями "
           "тела/внешности, и любых образов, которые могут быть восприняты как неуважение к религии "
           "или как противопоставление науки и веры (не формулируй так, будто научный факт "
           "«опровергает» или «заменяет» религиозные представления — просто излагай физику по "
           "существу, без оценочных сравнений с верой). Сохраняй достоинство, точность термина и "
           "уважительный, уместный для академической аудитории региона тон — не упрощай на грани "
           "снисходительности. Если в тексте уместен исторический или культурный мостик — например, "
           "речь идёт об оптике, алгебре, астрономии, медицине — можно бережно и ненавязчиво "
           "упомянуть вклад арабских учёных, философов и мыслителей (Ибн аль-Хайсам/Альхазен, "
           "Аль-Хорезми, Ибн Сина/Авиценна, Аль-Бируни и т.п.), если это органично и не притянуто "
           "за уши — не в каждом тексте, только где это действительно уместно. При сомнении в "
           "уместности конкретной аналогии или примера — выбирай более нейтральный и безопасный "
           "вариант, а не самый выразительный."),
    "en": ("Аудитория — международная, английский как lingua franca науки. Термины — общепринятые англоязычные; единицы СИ. Тон: ясный научпоп уровня хорошего научного журнала. ПРАВИЛО АНАЛОГИЙ (для всех языков): аналогию заменяй ТОЛЬКО если она непереводима или незнакома целевой аудитории; во всех остальных случаях переводи как есть. Молча «адаптировать» без причины нельзя. Алкогольные аналогии не используются ни в каком языке. В key_numbers переводятся И значения, И КЛЮЧИ словаря."),
    "fr": ("Аудитория — франкоязычные читатели Франции, Канады, Бельгии, Швейцарии и Африки. "
           "Нейтральный международный французский, термины — как в франкоязычных учебниках "
           "(éviter les anglicismes там, где есть устоявшийся французский термин). "
           "ПРАВИЛО АНАЛОГИЙ (для всех языков): аналогию заменяй ТОЛЬКО если она непереводима "
           "или незнакома целевой аудитории; во всех остальных случаях переводи как есть. "
           "Алкогольные аналогии не используются ни в каком языке. "
           "В key_numbers переводятся И значения, И КЛЮЧИ словаря."),
    "es": ("Аудитория — испаноязычные читатели Испании и Латинской Америки. Используй нейтральный международный испанский без региональных идиом; термины — принятые в испаноязычных учебниках. ПРАВИЛО АНАЛОГИЙ (для всех языков): аналогию заменяй ТОЛЬКО если она непереводима или незнакома целевой аудитории; во всех остальных случаях переводи как есть. Молча «адаптировать» без причины нельзя. Алкогольные аналогии не используются ни в каком языке. В key_numbers переводятся И значения, И КЛЮЧИ словаря."),
}

IMG_VARIATIONS = {
    "lighting": ["soft volumetric light", "dramatic rim light", "golden hour glow", "cold moonlight",
                 "bioluminescent glow", "harsh directional light", "diffuse studio light", "backlit haze"],
    "camera": ["wide establishing shot", "extreme close-up macro", "low angle looking up",
               "top-down view", "tilted dutch angle", "shallow depth of field", "long lens compression"],
    "palette": ["airy indigo and cyan", "warm amber and cream", "soft monochrome teal", "violet and gold",
                "emerald and mint", "muted pastel", "bright whites with a single vivid accent"],
    "style": ["cinematic photorealism", "elegant scientific 3D render", "abstract minimalism",
              "painterly digital art", "crisp editorial illustration", "atmospheric concept art"],
    "mood": ["serene and vast", "tense and dramatic", "mysterious", "hopeful and luminous",
             "cold and precise", "awe-inspiring", "intimate and quiet"],
    # Отдельное измерение ПОД КОМПОЗИЦИЮ — lighting/camera/palette/style меняют только "обёртку",
    # а сюжет для космических тем (чёрная дыра/звезда/планета) всё равно почти всегда сваlivался
    # в один большой шар по центру кадра. Эти варианты меняют, ЧТО буквально изображено и как
    # закадрировано, чтобы разбить этот дефолт.
    "composition": ["extreme macro texture filling the entire frame edge-to-edge, no single outlined shape visible",
                     "the subject small and distant, dwarfed by a vast surrounding environment",
                     "abstract data-visualization of flowing particles, field lines or waveforms instead of a solid object",
                     "a cutaway or cross-section view exposing internal structure",
                     "silhouette against a bright backdrop, negative-space framing",
                     "the instrument or observatory looking toward the phenomenon, not the phenomenon itself",
                     "a fragmented multi-detail composition, several related close-ups arranged in one frame",
                     "subject pushed to one edge of the frame, asymmetric off-center framing"],
}



def _base_id(arxiv_id):
    """2607.19435v1 -> 2607.19435. Модель отбора возвращает id без версии, живой API отдаёт
    с версией — точное сравнение давало пустое пересечение, и день молча пропадал
    (2026-07-21: 15 выбранных, 0 в обработку; повторилось на замере 30-го)."""
    return re.sub(r"v\d+$", "", str(arxiv_id or ""))


def _cands_json(articles):
    """Кандидаты для промптов отбора и ранжирования.

    Поле "cat" добавлено 2026-08-06 (решение владельца): в машинном обучении и математике
    берём не «поменьше», а только то, что работает на естественную науку и на нашу
    практику. Правило отсева живёт в data/prompts/article-select.txt, но без раздела оно
    неисполнимо — по заголовку и аннотации модель не всегда отличит работу про сам ИИ от
    применения ИИ в физике. Восемь лишних токенов на кандидата, зато фильтр точный."""
    return json.dumps([{"id": a["id"], "cat": a.get("primary_category", ""),
                        "title": a["title"], "summary": a["summary"][:500]} for a in articles],
                      ensure_ascii=False)


def _match_selected(articles, ids, count):
    want = {_base_id(i) for i in ids}
    picked = [a for a in articles if _base_id(a["id"]) in want][:count]
    if ids and not picked:
        print(f"  ⚠️ отбор вернул {len(ids)} id, но ни один не совпал с кандидатами — "
              f"беру топ-{count} по порядку (раньше тут молча выходил ноль)")
        return articles[:count]
    return picked


def select_best(articles, date_str):
    total = len(articles)
    count = max(1, total * SELECTION_PERCENT // 100)
    count = min(count, MAX_ARTICLES)
    if total <= count:
        return articles

    # ВЕКТОРНЫЙ ПРЕДФИЛЬТР перед моделью (ML, волна 2026-08-09, задача 1).
    # Вычёркивает два края — «такое у нас уже есть» и «не наш профиль» — и отдаёт
    # модели середину. Отбор кандидатов был самой дорогой строкой ночного прогона:
    # замер на шести днях показал минус 81% токенов (1058 кандидатов → ~200), причём
    # доля профильных разделов после отсева РАСТЁТ, а не падает.
    # Ранжирование внутри середины остаётся за моделью: вектор умеет вычёркивать,
    # но не выбирать — три ранжирующие оси закрыты числом.
    #
    # ВТОРОЙ ЭТАЖ — реранкер (ML, 2026-08-10, наряд архитектора круг 2). Вектор отвечает
    # «наше ли это по теме», реранкер — «интересно ли это читателю»: первый меряет
    # кандидата и корпус порознь, второй читает описание и кандидата вместе. Слепая
    # приёмка на восьми днях: семь за укороченный список. Стоит $0,0016 за ночь.
    try:
        from vector_select import prefilter, rerank_cut
        articles, why = prefilter(articles)
        print(f"  🧭 {why}")
        articles, why2 = rerank_cut(articles)
        print(f"  🎯 {why2}")
    except Exception as e:
        # Вспомогательный слой не имеет права ронять отбор: без него работает как раньше.
        print(f"  🧭 предфильтр пропущен ({type(e).__name__})")

    j = _cands_json(articles)
    prompt = load_prompt("article-select").format(count=count, articles_json=j)
    print(f"  🤖 Selecting {count} best from {total}...")
    r = chat("select", prompt)
    Path(f"temp/{date_str}").mkdir(parents=True, exist_ok=True)
    Path(f"temp/{date_str}/selection.json").write_text(r.choices[0].message.content, encoding="utf-8")
    try:
        data = json.loads(clean_json(r.choices[0].message.content))
        ids = [x["id"] for x in data.get("articles", data if isinstance(data, list) else [])]
        if not ids and isinstance(data, dict):
            ids = [x["id"] for x in data.get("selection", data.get("articles", []))]
        return _match_selected(articles, ids, count)
    except Exception:
        return articles[:count]


def select_best_n(articles, count, tag="bulk"):
    """Как select_best(), но count задаётся явно (не через SELECTION_PERCENT/MAX_ARTICLES) —
    для bulk-каскада (article_bulk_select.py), где нужен контроль над соотношением на каждом
    проходе, а не фиксированный дневной процент. Тот же промт/критерии — тот же вкус отбора."""
    total = len(articles)
    if total <= count:
        return articles
    j = _cands_json(articles)
    prompt = load_prompt("article-select").format(count=count, articles_json=j)
    r = chat("select", prompt)
    out_dir = Path(f"temp/bulk-select/{tag}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "selection.json").write_text(r.choices[0].message.content, encoding="utf-8")
    try:
        data = json.loads(clean_json(r.choices[0].message.content))
        ids = [x["id"] for x in data.get("articles", data if isinstance(data, list) else [])]
        if not ids and isinstance(data, dict):
            ids = [x["id"] for x in data.get("selection", data.get("articles", []))]
        return _match_selected(articles, ids, count)
    except Exception:
        return articles[:count]


def rank_articles(articles, tag="bulk"):
    """Ранжирующий (не отсеивающий) проход: оценка 1-10 по тем же критериям, что и отбор —
    для приоритезации внутри уже прошедшего каскад пула (bulk-select, раунд 3). Возвращает
    {{id: score}}; отсутствующие в ответе модели статьи получают нейтральный score=5."""
    j = _cands_json(articles)
    prompt = load_prompt("article-rank").format(articles_json=j)
    r = chat("select", prompt)
    out_dir = Path(f"temp/bulk-select/{tag}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rank.json").write_text(r.choices[0].message.content, encoding="utf-8")
    try:
        data = json.loads(clean_json(r.choices[0].message.content))
        scores = {x["id"]: x.get("score", 5) for x in data.get("scores", [])}
    except Exception:
        scores = {}
    return {a["id"]: scores.get(a["id"], 5) for a in articles}


def _script_ratio(text, lo, hi):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    return sum(1 for c in letters if lo <= c <= hi) / len(letters)


def _default_lang_ok(scipop):
    """RU-генерация иногда сваливается в английский на кросс-доменных статьях (cs.LG и т.п.).
    Проверяем, что заголовок/описание реально на русском. Только для кириллического default_lang."""
    if DEFAULT_LANG != "ru":
        return True
    sample = " ".join(str(scipop.get(k, "")) for k in ("title", "oneliner", "description"))
    return _script_ratio(sample, "Ѐ", "ӿ") >= 0.5


def _log_lang_fallback(kind, article_id, category="", attempt=0):
    """_default_lang_ok сработал False (ответ модели не на русском) — раньше был только print,
    который в большом батче никто не читает и не считает. Теперь пишем в файл structured-строкой,
    чтобы частоту/категории-виновники можно было посчитать скриптом/grep после прогона, а не искать
    вручную по логу (см. случай 2026-07-16 — 29% express-статей уходили в повтор, нашли только
    ручным grep'ом лога; промт-фикс — article-generate-express.txt, это — чтобы впредь ловилось
    автоматически, без ручного разбора)."""
    try:
        with open("lang-fallback.log", "a", encoding="utf-8") as f:
            f.write(f"{kind}\t{article_id}\t{category}\t{attempt}\n")
    except Exception:
        pass


# Список тегов в промпте заставляет модель выбирать знакомое: 179 тегов из 363 не проставлены
# ни одной статье, на топ-10 приходится 45% проставлений (замер 2026-08-04). Решение владельца —
# уводить теги на вектор. Переключатель заведён заранее и ПО УМОЛЧАНИЮ ВКЛЮЧЁН: выключать
# только после того, как ML отдаст измеренную привязку по смыслу, иначе останемся без обоих
# механизмов. Без списка модель даёт ОДИН главный тег своими словами, а не выдумывает набор.
TAGS_IN_PROMPT = CONFIG.get("tags_in_prompt", True)

_NO_SCI_BLOCK = (
    "УЧЁНЫЕ: списка учёных в промпте нет намеренно — их привяжет машина знаний по законам "
    "и понятиям статьи. Не выдумывай имена и не размечай их маркерами."
)
_NO_LAWS_BLOCK = (
    "ЗАКОНЫ: списка законов в промпте нет намеренно — их привяжет вектор по смыслу. "
    "Не выдумывай идентификаторы законов и не размечай их маркерами."
)
_NO_TAGS_BLOCK = (
    "ТЕГИ: списка тегов в этом промпте нет намеренно — остальные теги статья получит "
    "привязкой по смыслу. От тебя нужен ТОЛЬКО main_tag: одно понятие, о котором статья, "
    "английским идентификатором в нижнем регистре через подчёркивание (например black_hole). "
    "extra_tags оставь пустым списком. Не выдумывай наборы тегов и не размечай маркерами "
    "[tag:...] то, чего в main_tag нет."
)


def generate_advanced(article, text, tags_input, scientists_keys, law_ids=None, context_block=""):
    """context_block — окружение работы (соседи, плотность, группа карты), его собирает
    gen_context.build_block. Пустая строка — законное значение: вектор мог быть недоступен,
    и тогда промпт возвращается к прежнему виду вместо падения разбора."""
    tags_list = (", ".join(t["en"] for t in tags_input) if TAGS_IN_PROMPT else _NO_TAGS_BLOCK)
    # Учёных тоже не спрашиваем списком: их выводит машина знаний по законам и понятиям
    # статьи (tag_by_vector → scientists_vec). 201 имя в каждом промпте — это плата за то,
    # что реестр уже знает точнее. Ключ общий с тегами и законами.
    scientists_list = (", ".join(scientists_keys) if TAGS_IN_PROMPT else _NO_SCI_BLOCK)
    # Законы уходят тем же путём, что и теги: их ставит вектор (tag_by_vector считает
    # и tags_vec, и laws_vec). Держать в промпте список идентификаторов - платить
    # за то, что потом всё равно пересчитывается по смыслу.
    laws_list = (", ".join(law_ids or []) if TAGS_IN_PROMPT else _NO_LAWS_BLOCK)
    prompt = load_prompt("article-generate-advanced").format(
        tags_list=tags_list, scientists_list=scientists_list, laws_list=laws_list,
        article_text=text, context_block=context_block or "")
    reinforce = "\n\nВНИМАНИЕ: все текстовые поля пиши СТРОГО на русском языке. Не отвечай на английском."
    result = None
    for attempt in range(2):
        r = chat("article_advanced", prompt if attempt == 0 else prompt + reinforce)
        try:
            parsed = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            Path(f"temp/debug_adv_{article['id']}.txt").write_text(r.choices[0].message.content, encoding="utf-8")
            if result is not None:
                break
            return None
        result = parsed
        if _default_lang_ok(result):
            return result
        print(f"    ⚠️ RU-версия вышла не на русском — повтор с усилением языка")
        _log_lang_fallback("advanced", article.get("id", ""), article.get("primary_category", ""), attempt)
    return result


def generate_express(article, abstract_text, tags_input, scientists_keys):
    """Экспресс-режим: ОДИН вызов вместо каскада advanced→simple→popular. Источник — только
    авторская аннотация (короткая, уже готова из arXiv API — не парсим PDF), не полный текст
    статьи. Даёт mini+simple разом. Обложка/мозаика всё равно берутся из PDF (см. build_article),
    просто текст для генерации — дешёвый и короткий. tags_input — обычно урезанное express-
    подмножество (лестница дешевле не только по input article_text, но и по списку тегов в промте)."""
    # Экспресс — последняя дверь, через которую теги ещё уходили в промпт. Решение владельца
    # 2026-08-09 «разметка вектором, не промптом» исполнили наполовину: полный разбор ключ
    # tags_in_prompt=False уважает (см. generate_advanced), а здесь стояла безусловная строка.
    # Цена видна на живой статье: разбор прямо про нейтрино получил neutron_star, потому что
    # в express-списке 53 тега и neutrino в него не входит. Теперь один ключ правит обе двери,
    # а теги ставит вектор (tools/tag_by_vector.py, шаг фабрики перед публикацией).
    tags_list = (", ".join(t["en"] for t in tags_input) if TAGS_IN_PROMPT else _NO_TAGS_BLOCK)
    # Учёных тоже не спрашиваем списком: их выводит машина знаний по законам и понятиям
    # статьи (tag_by_vector → scientists_vec). 201 имя в каждом промпте — это плата за то,
    # что реестр уже знает точнее. Ключ общий с тегами и законами.
    scientists_list = (", ".join(scientists_keys) if TAGS_IN_PROMPT else _NO_SCI_BLOCK)
    prompt = load_prompt("article-generate-express").format(
        tags_list=tags_list, scientists_list=scientists_list, abstract_text=abstract_text)
    reinforce = "\n\nВНИМАНИЕ: все текстовые поля пиши СТРОГО на русском языке. Не отвечай на английском."
    result = None
    for attempt in range(2):
        r = chat("article_express", prompt if attempt == 0 else prompt + reinforce)
        try:
            parsed = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            Path(f"temp/debug_express_{article['id']}.txt").write_text(r.choices[0].message.content, encoding="utf-8")
            if result is not None:
                break
            return None
        result = parsed
        if _default_lang_ok(result):
            return result
        print(f"    ⚠️ RU-версия вышла не на русском — повтор с усилением языка")
        _log_lang_fallback("express", article.get("id", ""), article.get("primary_category", ""), attempt)
    return result


def generate_image_prompt(scipop):
    """LLM придумывает промпт для FLUX по статье, со случайными вариациями (чтобы не однотипно).
    Агент иногда флапает (возвращает пусто) — до 3 попыток."""
    for _ in range(3):
        picks = {k: random.choice(v) for k, v in IMG_VARIATIONS.items()}
        prompt = load_prompt("image-generate").format(
            title=scipop.get("title", ""), oneliner=scipop.get("oneliner", ""),
            description=scipop.get("description", ""),
            tags=", ".join([scipop.get("main_tag", "")] + scipop.get("extra_tags", [])[:5]),
            **picks)
        raw = ""
        try:
            r = chat("image_prompt", prompt)
            raw = r.choices[0].message.content or ""
        except Exception as e:
            print(f"    ⚠️ image_prompt error: {e}")
        out = ""
        try:
            out = json.loads(clean_json(raw)).get("prompt", "")
        except Exception:
            # Ответ мог обрезаться (max_tokens) → JSON не закрылся. Вытаскиваем prompt регуляркой.
            m = re.search(r'"prompt"\s*:\s*"(.+?)"\s*[,}]', raw, re.S) or re.search(r'"prompt"\s*:\s*"(.+)', raw, re.S)
            out = (m.group(1).replace('\\"', '"').replace('\\n', ' ').strip()[:900] if m else "")
        if out:
            return out
    return ""


# Единый визуальный язык набора (юзер-фидбек 2026-07-21: «понравилась визуализация Казимира —
# серебряный стиль, контраст везде, продолжай в этом стиле»): серебро/графит, высокий контраст,
# богатая линейная фактура на светлом фоне + ОДИН выразительный цветной акцент.
REF_PALETTES = ["silver and graphite linework on soft white, high tonal contrast",
                "brushed-silver greys on a pale light background, crisp strong contrast",
                "cool silver and slate on off-white, deep tonal contrast",
                "metallic silver-grey filaments on bright white, sharp contrast",
                "graphite and pewter on light grey, luminous high contrast",
                "fine silver linework on airy white, bold light-and-dark contrast"]
REF_ACCENTS = ["a single teal accent", "one warm gold accent", "a vivid coral accent",
               "a luminous cyan accent", "a warm amber accent", "one deep magenta accent"]


def generate_ref_image_prompt(name, description):
    """FLUX-промпт для картинки ЗАКОНА/ПОНЯТИЯ — полу-схема с ВЕРНОЙ геометрией принципа
    (data/prompts/image-generate-ref.txt). Отдельно от статейного image-generate: у обложки статьи
    другая задача (кинематографичная сцена), а тут — узнаваемая корректная визуализация принципа.
    До 3 попыток — агент иногда возвращает пусто."""
    for _ in range(3):
        prompt = load_prompt("image-generate-ref").format(
            name=name or "", description=(description or "")[:600],
            palette=random.choice(REF_PALETTES), accent=random.choice(REF_ACCENTS))
        raw = ""
        try:
            r = chat("image_prompt", prompt)
            raw = r.choices[0].message.content or ""
        except Exception as e:
            print(f"    ⚠️ ref image_prompt error: {e}")
        out = ""
        try:
            out = json.loads(clean_json(raw)).get("prompt", "")
        except Exception:
            m = re.search(r'"prompt"\s*:\s*"(.+?)"\s*[,}]', raw, re.S) or re.search(r'"prompt"\s*:\s*"(.+)', raw, re.S)
            out = (m.group(1).replace('\\"', '"').replace('\\n', ' ').strip()[:900] if m else "")
        if out:
            return out
    return ""


def generate_image(image_prompt, out_path, preset="image"):
    """Рисует картинку (DeepInfra, модель/размер из config.agents[preset]). Без ключа — пропуск.
    preset — имя блока в config.agents: "image" (текущая/дефолт), "image_cheap" (FLUX-1-schnell,
    дёшево и быстро для больших партий), "image_quality" (FLUX-2-pro, как на уже существующих
    картинках). Возвращает (ok, model) — model нужен вызывающему, чтобы честно записать, чем
    именно сгенерена картинка (потом легко найти дешёвые и точечно апгрейднуть)."""
    key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not key or not image_prompt:
        return False, None
    cfg = AGENTS.get(preset) or AGENTS.get("image", {})
    model = cfg.get("model", "black-forest-labs/FLUX-2-pro")
    try:
        import base64
        cli = OpenAI(base_url="https://api.deepinfra.com/v1/openai", api_key=key)
        resp = cli.images.generate(model=model, prompt=image_prompt, n=1,
                                   size=cfg.get("size", "1024x1024"))
        Path(out_path).write_bytes(base64.b64decode(resp.data[0].b64_json))
        return True, model
    except Exception as e:
        print(f"    ⚠️ FLUX error: {e}")
        return False, model



# Наследование фактуры КОДОМ, а не пересказом модели (ТЗ 2026-07-27, §4): нижний уровень получает
# теги/учёных/законы/числа/метафору/глоссарий готовыми и не вправе их менять — так версии не
# расходятся между уровнями.
_INHERITED = ("main_tag", "extra_tags", "scientists", "laws", "key_numbers", "metaphor",
              "glossary", "contribution")


def inherit_facts(child, parent):
    """Переносит фактуру из родительского уровня в дочерний. Возвращает child."""
    if not isinstance(child, dict) or not isinstance(parent, dict):
        return child
    for k in _INHERITED:
        if k in parent and parent[k] not in (None, "", [], {}):
            child[k] = parent[k]
    return child


# generate_simple() убрана 2026-07-30: её никто не вызывал (живой путь —
# generate_simple_mini из popular), а работать она уже не могла: подставляла advanced_json
# в article-generate-simple.txt, который принимает Popular и отдаёт simple+mini.
# Мёртвый код, который сломался бы при первом же вызове, хуже отсутствующего.


def generate_popular(scipop_adv):
    """Popular генерируется из Advanced. Simple и mini — уже из Popular
    (generate_simple_mini), чтобы уровни не расходились."""
    prompt = load_prompt("article-generate-popular").format(
        advanced_json=json.dumps(scipop_adv, ensure_ascii=False))
    reinforce = "\n\nВНИМАНИЕ: пиши СТРОГО на русском языке."
    data = None
    for attempt in range(2):
        r = chat("article_popular", prompt if attempt == 0 else prompt + reinforce)
        try:
            data = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            return scipop_adv
        if _default_lang_ok(data):
            break
    return inherit_facts(data, scipop_adv)


# ── Конвейер 2.0: конструктор (владелец 2026-07-30, обоснование temp/experiment-constructor) ──
COMBO_SHARED = ("formulas", "key_numbers", "fun_fact", "scifi", "main_tag",
                "extra_tags", "scientists", "glossary", "contribution")
SLIM_SHARED_TRANSLATE = ("fun_fact", "scifi", "formulas", "key_numbers")


def generate_combo(scipop_adv):
    """popular + simple + mini ОДНИМ вызовом из advanced. Общие блоки (формулы, числа,
    факты, теги, глоссарий) модель НЕ пересказывает — копируются кодом из advanced.
    Доказано на эксперименте: −52% цены генерации тиров, метафора едина между уровнями.
    Возвращает (pop, simple) с полем mini в обоих, или (None, None) при провале —
    вызывающий падает на старый путь."""
    prompt = load_prompt("article-generate-combo").format(
        advanced_json=json.dumps(scipop_adv, ensure_ascii=False))
    reinforce = chr(10)*2 + "ВНИМАНИЕ: пиши СТРОГО на русском языке."
    for attempt in range(2):
        r = chat("article_popular", prompt if attempt == 0 else prompt + reinforce)
        try:
            data = json.loads(clean_json(r.choices[0].message.content))
            pop, simp = data["popular"], data["simple"]
            mini = (data.get("mini") or "").strip()
        except Exception:
            continue
        if not (_default_lang_ok(pop) and _default_lang_ok(simp)):
            continue
        for tier in (pop, simp):
            for k in COMBO_SHARED:
                if k in scipop_adv:
                    tier[k] = scipop_adv[k]
        pop["mini"] = simp["mini"] = mini
        return inherit_facts(pop, scipop_adv), inherit_facts(simp, scipop_adv)
    return None, None


def translate_scipop_slim(tier, adv_translated, target_lang, retries=2):
    """Перевод тира БЕЗ общих полей (они уже переведены в advanced и копируются сюда) —
    дешёвой моделью. Валидатор судит итоговую сборку. При провале — None, вызывающий
    падает на полный translate_scipop."""
    slim = {k: v for k, v in tier.items()
            if k not in SLIM_SHARED_TRANSLATE and k not in _INTERNAL_FIELDS}
    target_language = LANG_NAMES.get(target_lang, target_lang)
    prompt = load_prompt("article-translate").format(
        article_json=json.dumps(slim, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, "")) + _termbase_block(slim, target_lang)
    for attempt in range(1, retries + 1):
        r = chat("translate_flash", prompt + _translation_contract(slim),
                 system=_translation_system(target_language))
        try:
            out = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            continue
        for k in ("main_tag", "extra_tags", "tags", "scientists", "laws"):
            if k in slim:
                out[k] = slim[k]
        for k in _INTERNAL_FIELDS:      # служебные — из русского тира, они и не переводились
            if k in tier:
                out[k] = tier[k]
        _keep_based_on(tier, out)
        for k in SLIM_SHARED_TRANSLATE:
            if k in adv_translated:
                out[k] = adv_translated[k]
        ok, problems = validate_translation(tier, out, target_lang)
        if ok:
            return out
        if attempt < retries and all(pr.startswith("кириллица") for pr in problems):
            if _retranslate_cyrillic_fields(out, target_lang, target_language, slim):
                ok2, _ = validate_translation(tier, out, target_lang)
                if ok2:
                    return out
        print(f"    ↻ slim-перевод {target_lang}: {problems[0] if problems else '?'} — повтор {attempt}/{retries}")
    return None


def refine_simple(scipop):
    """Рефлексивная шлифовка Simple версии. Тоже используется для экспресс-режима (там в scipop
    есть доп. поле `mini`, которого промт не знает, — защищаем его так же, как main_tag/extra_tags/
    scientists: сохраняем из ДО-шлифовки, промт его не трогает и не обязан сохранять структуру."""
    prompt = load_prompt("article-refine-simple").format(
        simple_json=json.dumps(scipop, ensure_ascii=False))
    r = chat("article_simple", prompt, temperature=0.6)
    try:
        data = json.loads(clean_json(r.choices[0].message.content))
        data["main_tag"] = scipop.get("main_tag", "")
        data["extra_tags"] = scipop.get("extra_tags", [])
        data["scientists"] = scipop.get("scientists", [])
        data["laws"] = scipop.get("laws", [])
        if "mini" in scipop:
            data["mini"] = scipop.get("mini", "")
        return inherit_facts(data, scipop)
    except Exception:
        return scipop


def refine_popular(scipop):
    """Рефлексивная шлифовка Popular версии."""
    prompt = load_prompt("article-refine-popular").format(
        popular_json=json.dumps(scipop, ensure_ascii=False))
    r = chat("article_popular", prompt, temperature=0.6)
    try:
        data = json.loads(clean_json(r.choices[0].message.content))
        data["main_tag"] = scipop.get("main_tag", "")
        data["extra_tags"] = scipop.get("extra_tags", [])
        data["scientists"] = scipop.get("scientists", [])
        data["laws"] = scipop.get("laws", [])
        return inherit_facts(data, scipop)
    except Exception:
        return scipop


ABSTRACT_LEVELS = ("popular", "simple", "advanced")
# Держим в паре с лимитами в data/prompts/adapt-abstract.txt / refine-abstract.txt — те лимиты
# промпт советует модели именно эти лимиты — модель на практике часто превышает их (не считает
# символы точно). Раньше код-лимит был равен промпт-лимиту, из-за чего бОльшая часть аннотаций
# обрезалась по живому (45/62 popular, 35/62 simple, 35/62 advanced заканчивались «…» — видно
# как «не полные» на сайте). Теперь код-лимит — это подстраховка с запасом (редкий последний
# рубеж против аномального переспама), а не де-факто ограничитель длины.
ABSTRACT_LIMITS = {"simple": 350, "popular": 550, "advanced": 900}
# Держать РАВНЫМИ лимитам в data/prompts/abstract-adapt.txt. Были 500/750/1200 при
# заявленных промптом 350/550/900 — то есть промпт называл лимит жёстким, а код молча
# принимал на 43% длиннее. Замер 2026-08-04 по 1967 аннотациям: за лимит промпта выходили
# 44% simple и 62% popular, и именно эти раздутые тексты читатель видел на карточке.
_ABSTRACT_HARD_LIMITS = {"simple": 350, "popular": 550, "advanced": 1600}
# advanced с 2026-08-05 — это ПЕРЕВОД авторской аннотации (abstract-advanced.txt), а не наш
# пересказ: лимит равен разумной длине абстракта, обрезать перевод нельзя — потеря
# утверждения это брак. Для simple/popular лимиты прежние, они идут на карточку.


def _cap_text(text, limit):
    """Обрезает текст до limit. Сначала пробует границу предложения (. ! ?) — так конец
    читается естественно, без многоточия. Только если предложение не находится в разумных
    пределах (обрезало бы больше четверти текста), режет по границе слова с «…»."""
    if len(text) <= limit:
        return text
    best = -1
    for m in re.finditer(r'[.!?]', text[:limit]):
        best = m.end()
    if best > limit * 0.75:
        return text[:best].strip()
    cut = text.rfind(" ", 0, limit)
    return (text[:cut] if cut > limit * 0.6 else text[:limit]).rstrip(" ,.;:—-") + "…"


def generate_abstract(summary):
    """«Аннотация» на RU в трёх регистрах. Возвращает {level: text}.

    Регистры разошлись по промптам 2026-08-05, потому что у них противоположные задачи:
    simple и popular — наш голос для карточки (abstract-adapt, со стилевым ядром),
    advanced — перевод авторской аннотации для уровня «Подробно», где упрощение запрещено
    (abstract-advanced, без стилевого ядра). Один промпт на оба режима давал бы прямое
    противоречие внутри себя, а такое всегда выигрывает у стиля."""
    summary = (summary or "").strip()
    if not summary:
        return {}
    advanced_ru = generate_abstract_advanced(summary)
    prompt = load_prompt("abstract-adapt").format(summary=summary)
    for attempt in range(3):
        try:
            data = json.loads(clean_json(chat("abstract", prompt).choices[0].message.content))
        except Exception:
            data = {}
        levels = {v: (data.get(v, "") or "").strip() for v in ABSTRACT_LEVELS}
        if not any(levels.values()):
            continue
        fb = next((t for t in levels.values() if t), "")  # если модель дала не все уровни — добить непустым
        levels = {v: levels[v] or fb for v in ABSTRACT_LEVELS}
        # Перебор длины — повод переспросить, а не обрезать. Обрезка рвёт мысль на середине,
        # а этот текст читатель видит первым, на карточке в ленте.
        over = [v for v in ABSTRACT_LEVELS if len(levels[v]) > _ABSTRACT_HARD_LIMITS[v]]
        if over and attempt < 2:
            prompt += ("\n\nПРОШЛАЯ ПОПЫТКА НЕ ПРОШЛА: превышен лимит символов в полях "
                       + ", ".join(f"{v} ({len(levels[v])} при лимите {_ABSTRACT_HARD_LIMITS[v]})"
                                   for v in over)
                       + ". Лимит жёсткий: текст показывается целиком, без обрезки. "
                         "Сократи, убрав детали, а не объяснения.")
            continue
        out = {v: _cap_text(levels[v], _ABSTRACT_HARD_LIMITS[v]) for v in ABSTRACT_LEVELS}
        if advanced_ru:
            out["advanced"] = advanced_ru      # перевод не режем: потеря утверждения — брак
        return out
    return {"advanced": advanced_ru} if advanced_ru else {}


def generate_abstract_advanced(summary, retries=2):
    """Уровень «Подробно»: авторская аннотация по-русски, без упрощения и без потерь.

    Отдельный промпт, а не регистр в abstract-adapt, по одной причине: там подключён
    {style_core} с требованием «первая фраза — картина, а не термин». Для профессионального
    читателя это требование вредно, а противоречие в промпте всегда выигрывает у стиля
    (урок 31 июля). Здесь стилевого ядра нет намеренно."""
    summary = (summary or "").strip()
    if not summary:
        return ""
    prompt = load_prompt("abstract-advanced").format(summary=summary)
    for _ in range(retries):
        try:
            data = json.loads(clean_json(chat("abstract", prompt).choices[0].message.content))
        except Exception:
            continue
        text = (data.get("advanced") or "").strip()
        if text and _script_ratio(text, "Ѐ", "ӿ") >= 0.5:
            return text
    return ""


def refine_abstract(abstract):
    """Рефлексивная шлифовка трёх уровней аннотации одним вызовом. Структуру сохраняем."""
    if not abstract:
        return abstract
    prompt = load_prompt("abstract-refine").format(abstract_json=json.dumps(abstract, ensure_ascii=False))
    try:
        data = json.loads(clean_json(chat("abstract", prompt, temperature=0.5).choices[0].message.content))
    except Exception:
        return abstract
    return {v: _cap_text(((data.get(v) or abstract.get(v, "")) or "").strip(), _ABSTRACT_HARD_LIMITS[v])
            for v in ABSTRACT_LEVELS}


def _log_translation_failure(kind, target_lang, detail=""):
    """Раньше сбой парсинга ответа модели (не сетевая ошибка — chat() её уже ретраит сама, см.
    common.chat) молча откатывался на исходный (русский) текст — страница публиковалась как
    "переведённая", хотя языка не меняла. На арабском это оказалось массовым: скан всего
    корпуса 2026-07-16 показал 60-93% сломанных ar-страниц по тирам, 0% на en, ~0% на es —
    похоже, модель заметно чаще выдаёт невалидный/недо-JSON именно на арабском. Теперь при
    исчерпании ретраев тут же СИЛЬНО логируем в файл (не только print, который никто не видит
    в большом батче) — чтобы сбои можно было найти и пересобрать точечно, а не только когда
    кто-то вручную читает статьи."""
    try:
        with open("translation-failures.log", "a", encoding="utf-8") as f:
            f.write(f"{kind}\t{target_lang}\t{detail}\n")
    except Exception:
        pass



# ── Автопроверки перевода (ТЗ контент-менеджера 2026-07-27, §6.4) ─────────────────────────────
# Проверяем ПЕРЕД записью: брак → повтор вызова, при исчерпании — лог, но НЕ молчаливый откат
# на непереведённый текст. Самая опасная ошибка — потерянное число (результат исследования).
_MARKER_RE = re.compile(r"\[(tag|law|scientist|callout):[^\]]*\]")
# Числа для сверки перевода. Разряды тысяч отделяются по-разному: по-русски пробелом
# («420 000»), по-английски запятой («420,000»), в вёрстке ещё и неразрывным пробелом.
# Ловим группу целиком, иначе «420 000» распадалось на «420» и «000» и любой корректный
# перевод выглядел потерей двух чисел.
_NUM_RE = re.compile(
    # \s покрывает и неразрывный пробел — в Python он считается пробельным.
    r"\d{1,3}(?:[\s,]\d{3})+(?:[.,]\d+)?"          # 420 000 · 420,000 · 1 234 567,8
    r"|\d+(?:[.,]\d+)?"                                   # 0,15 · 1856
    r"(?:\s*[×x*]\s*10\s*\^?\s*-?\d+)?"                  # ... × 10^8
)
_NUM_PARTS = re.compile(r"^([\d\s,.]+?)(\s*[×x*]\s*10\s*\^?\s*(-?\d+))?$")


def _num_key(n):
    """Число в сравнимый вид: снимаем разделители разрядов, приводим запятую-дробь
    к точке, степень десяти — к единой записи. Русское «3,2 × 10^8» и английское
    «3.2 x 10^8» должны совпасть, иначе валидатор бракует ПРАВИЛЬНЫЙ перевод и гонит
    повторы в полную цену (поймано 2026-07-31 на 2607.23140v1: четыре прогона подряд)."""
    n = n.replace(" ", " ")
    m = _NUM_PARTS.match(n)
    if not m:
        return n
    head, _, exp = m.groups()
    head = head.strip()
    if re.fullmatch(r"\d{1,3}(?:[\s,]\d{3})+(?:[.,]\d+)?", head):
        # разделитель разрядов — тот, после которого ровно три цифры; остальное дробь
        head = re.sub(r"[\s,](?=\d{3}(?:\D|$))", "", head)
    head = head.replace(" ", "").replace(",", ".").rstrip(".")
    return f"{head}e{exp}" if exp else head
_CYR_RE = re.compile(r"[а-яА-ЯёЁ]")


# Служебные ключи структуры — это имена полей, а не текст для читателя. Всё остальное
# в ключах словаря читатель ВИДИТ: key_numbers выводится на странице как «ключ: значение».
_STRUCT_KEYS = frozenset((
    "title", "oneliner", "description", "text", "context", "methods", "results",
    "implications", "future_development", "impact_on", "next_steps", "mini",
    "key_problems_connection", "key_problems", "fun_fact", "scifi", "formulas",
    "latex", "meaning", "key_numbers", "main_tag", "extra_tags", "tags", "laws",
    "scientists", "glossary", "metaphor", "term", "plain", "threads", "history",
))


def _flat_text(obj):
    """Весь человекочитаемый текст структуры одной строкой (для подсчётов).

    Ключи словарей тоже считаются: в key_numbers ключ — это подпись на странице
    («типичная масса компонента: 0.6 M☉»). Пока их не считали, непереведённый
    key_numbers проходил валидацию молча и уезжал на прод — так на арабской
    странице 2607.23119v2 осталось 167 знаков кириллицы (замер 2026-07-30)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        keys = [k for k in obj if isinstance(k, str) and k not in _STRUCT_KEYS]
        return " ".join(keys + [_flat_text(v) for v in obj.values()])
    if isinstance(obj, list):
        return " ".join(_flat_text(v) for v in obj)
    return ""


def _latex_bits(obj):
    """Все latex-поля — они переводом меняться не должны."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "latex" and isinstance(v, str):
                out.append(v)
            else:
                out.extend(_latex_bits(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_latex_bits(v))
    return out


# Служебные поля: читателю не показываются (в templates/ и js/ их нет), нужны только коду —
# metaphor держит метафору единой между уровнями, glossary кормит нижние тиры и термбазу.
# Модели они не отдаются и переводом не считаются: русский текст в них — норма, а не брак.
_INTERNAL_FIELDS = ("metaphor", "glossary", "contribution")


def _keep_based_on(src, dst):
    """Опоры neighbourhood — идентификаторы работ, а не текст: переводить их нельзя.

    Ровно та же болезнь, от которой защищены main_tag/tags/laws строкой ниже: переводчик
    в роли «редактора-носителя» переводит и ключи, и arXiv-id 2605.18112 приезжает из
    арабского как «٢٦٠٥.١٨١١٢». Тексты same/different переводить нужно — их не трогаем.
    """
    nb_src, nb_dst = src.get("neighbourhood"), dst.get("neighbourhood")
    if isinstance(nb_src, dict) and isinstance(nb_dst, dict):
        nb_dst["based_on"] = nb_src.get("based_on") or []


def _without_internal(scipop):
    return {k: v for k, v in scipop.items() if k not in _INTERNAL_FIELDS} if isinstance(scipop, dict) else scipop


def validate_translation(src, dst, target_lang):
    """Возвращает (ok, [проблемы]). Порядок проверок — по §6.4 ТЗ.

    Служебные поля из счёта исключены: они копируются из русского оригинала кодом,
    и раньше их кириллица считалась браком перевода — из-за чего каждый уровень
    уезжал на три дорогих ретрая и всё равно возвращался непереведённым."""
    src, dst = _without_internal(src), _without_internal(dst)
    problems = []
    src_t, dst_t = _flat_text(src), _flat_text(dst)
    if not dst_t.strip():
        return False, ["пустой перевод"]

    # 1) кириллица в не-русской версии
    if target_lang != "ru":
        cyr = len(_CYR_RE.findall(dst_t))
        if cyr > max(20, len(dst_t) * 0.02):
            problems.append(f"кириллица в {target_lang}: {cyr} символов")

    # 2) маркеры сущностей должны совпадать по составу
    src_m, dst_m = sorted(_MARKER_RE.findall(src_t)), sorted(_MARKER_RE.findall(dst_t))
    if len(src_m) != len(dst_m):
        problems.append(f"маркеры: было {len(src_m)}, стало {len(dst_m)}")

    # 3) числа оригинала обязаны сохраниться (потерянный результат — худшая ошибка).
    #
    # Сравниваем НОРМАЛИЗОВАННО. Разделитель тысяч у языков разный: по-русски «420 000»,
    # по-английски «420,000», в вёрстке ещё и неразрывный пробел. Сырое сравнение цифровых
    # групп считало это потерей «420» и «000» — то есть браковало ПРАВИЛЬНЫЙ перевод,
    # гнало три повтора (каждый в полную цену) и в итоге оставляло русский текст на
    # английской странице. Поймано 2026-07-31 на статье 2607.23140v1, где «420 000»
    # заваливало перевод четырьмя прогонами подряд.
    src_n = {_num_key(n) for n in _NUM_RE.findall(src_t)}
    dst_n = {_num_key(n) for n in _NUM_RE.findall(dst_t)}
    lost = [n for n in src_n if n not in dst_n]
    # мало чисел — терять нельзя ни одного (это и есть результат исследования);
    # много — допускаем 15% на переформулировки вроде «десятки тысяч».
    tolerance = 0 if len(src_n) <= 6 else len(src_n) * 0.15
    if len(lost) > tolerance:
        problems.append(f"потеряны числа ({len(lost)} из {len(src_n)}): {lost[:5]}")

    # 4) latex не должен меняться
    if _latex_bits(src) != _latex_bits(dst):
        problems.append("изменены latex-формулы")

    # 5) длина — предупреждение, не брак
    if src_t and not (0.7 <= len(dst_t) / len(src_t) <= 1.45):
        print(f"    ⚠️ перевод {target_lang}: длина {len(dst_t)/len(src_t):.0%} от оригинала")

    return (not problems), problems


# ── Термбаза для перевода (ТЗ 2026-07-27, §6.1) ──────────────────────────────────────────────
# Внутри маркеров [tag:...] / [law:...] / [scientist:...] переводчик обязан использовать ИМЕННО
# те формулировки, что уже стоят на карточках этих сущностей — иначе термин в статье и на его
# собственной странице расходятся. Источник — уже переведённые справочники, новых вызовов LLM нет.
_TERMBASE_CACHE = {}


def _ref_names(lang, fname):
    """{id: локализованное имя} из переведённого справочника; пусто, если файла нет."""
    key = (lang, fname)
    if key in _TERMBASE_CACHE:
        return _TERMBASE_CACHE[key]
    p = Path(LANG_DIR) / lang / "data" / fname
    out = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and v.get("name"):
                        out[k] = v["name"]
                    elif isinstance(v, str):
                        out[k] = v
        except Exception:
            pass
    _TERMBASE_CACHE[key] = out
    return out


def build_termbase(scipop, target_lang):
    """Готовые переводы сущностей ЭТОЙ статьи + глоссарий. Пустые секции опускаем."""
    tag_ids = [x for x in [scipop.get("main_tag")] + (scipop.get("extra_tags") or []) if x]
    law_ids = scipop.get("laws") or []
    sci_ids = scipop.get("scientists") or []

    tags_all = _ref_names(target_lang, "tags.json")
    laws_all = _ref_names(target_lang, "laws.json")
    sci_all = _ref_names(target_lang, "scientists.json")

    tb = {}
    got = {k: v for k, v in ((i, tags_all.get(i)) for i in tag_ids) if v}
    if got:
        tb["tags"] = got
    got = {k: v for k, v in ((i, laws_all.get(i)) for i in law_ids) if v}
    if got:
        tb["laws"] = got
    got = {k: v for k, v in ((i, sci_all.get(i)) for i in sci_ids) if v}
    if got:
        tb["scientists"] = got
    # Глоссарий сюда НЕ идёт: это пары «русский термин → русское бытовое объяснение».
    # В блоке, который называется «готовые переводы, используй ТОЛЬКО эти формулировки»,
    # они работали ровно наоборот — подсказывали модели писать по-русски.
    return tb


def _termbase_block(scipop, target_lang):
    """Кусок промпта с термбазой (или пустая строка, если сущностей нет)."""
    tb = build_termbase(scipop, target_lang)
    if not tb:
        return ""
    head = (
        "\n\nТЕРМБАЗА — готовые переводы сущностей этой статьи. Внутри маркеров "
        "[tag:...], [law:...], [scientist:...] используй ТОЛЬКО эти формулировки, "
        "ничего не придумывай:\n"
    )
    return head + json.dumps(tb, ensure_ascii=False, indent=1)



def _translation_system(target_language, src=None):
    """Системная роль переводчика. Язык вывода — ЗДЕСЬ, а не в user-тексте:
    в user модель его теряла, и статья уходила на полный ретрай (цена x2, x3).

    src — исходный scipop: из него в роль вшиваются ТОЧНЫЕ счётчики маркеров и список
    чисел. Замер 2026-07-30 показал: после фикса языка модель стала терять маркеры
    и числа (62 вызова перевода на 3 статьи вместо ~36, переводы = 75% цены статьи).
    Обещание «не теряй» не работает — работает контракт с числами, который валидатор
    потом проверяет теми же счётчиками."""
    return (f"You are a professional scientific translator. TARGET LANGUAGE: {target_language}. "
            f"Every text value in your JSON answer MUST be written in {target_language} only. "
            f"Cyrillic characters are FORBIDDEN in the output (exception: content inside "
            f"[tag:...]/[scientist:...] marker IDs and latex fields, which are copied verbatim). "
            f"Do not add, drop or alter any numbers, markers or latex.")


def _translation_contract(src):
    """Контракт с числами и счётчиком маркеров — в КОНЕЦ пользовательского текста,
    а не в системную роль.

    Он у каждой статьи свой, а системная роль идёт первой строкой запроса. Пока контракт
    жил в ней, начало КАЖДОГО запроса было уникальным — и кэш DeepSeek, который срабатывает
    только на полном совпадении НАЧАЛА, не попадал почти никогда. Замер 2026-08-02: у
    переводов попадание 25-29% против 85% у экспресса — при том, что перевод у нас самая
    массовая операция (1532 вызова за неделю). Сам контракт нужен и остаётся: без него
    модель теряет маркеры и числа (урок 2026-07-30). Он просто переезжает в конец."""
    if src is None:
        return ""
    st = _flat_text(src)
    markers = _MARKER_RE.findall(st)
    nums = sorted(set(_NUM_RE.findall(st)))[:40]
    return (f"\n\nHARD CONTRACT (validator rejects your answer otherwise): the source contains "
            f"EXACTLY {len(markers)} entity markers — reproduce every one of them, same IDs, "
            f"no more, no fewer. These numbers appear in the source and every one of them "
            f"must appear in your output unchanged: {', '.join(nums)}.")


_CYR_FIELD_RE = _CYR_RE

def _retranslate_cyrillic_fields(out, target_lang, target_language, src=None):
    """Точечный добор вместо полного повтора (решение владельца 2026-07-30):
    из-за пары строк с кириллицей раньше на ретрай уезжал ВЕСЬ уровень статьи —
    десятки тысяч знаков по полной цене. Теперь собираем только грязные строки,
    переводим их одним маленьким вызовом и подставляем на место."""
    dirty = []      # [(контейнер, ключ/индекс, строка)] — значения
    dirty_keys = []  # [(словарь, ключ)] — сами ключи: в key_numbers ключ видит читатель

    def walk(node):
        if isinstance(node, dict):
            for k, v in list(node.items()):
                if k in ("latex", "main_tag", "extra_tags", "tags", "scientists", "laws"):
                    continue
                if k not in _STRUCT_KEYS and len(_CYR_FIELD_RE.findall(k)) > 3:
                    dirty_keys.append((node, k))
                if isinstance(v, str):
                    stripped = _MARKER_RE.sub("", v)
                    if len(_CYR_FIELD_RE.findall(stripped)) > 3:
                        dirty.append((node, k, v))
                else:
                    walk(v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str):
                    if len(_CYR_FIELD_RE.findall(_MARKER_RE.sub("", v))) > 3:
                        dirty.append((node, i, v))
                else:
                    walk(v)

    walk(out)
    if not dirty and not dirty_keys:
        return False
    if len(dirty) + len(dirty_keys) > 40:   # слишком много грязи = перевод не удался в целом
        return False
    strings = [v for _, _, v in dirty] + [k for _, k in dirty_keys]
    prompt = ("Translate each string of this JSON array. Keep [tag:...]/[scientist:...] markers, "
              "numbers and $latex$ untouched. Answer with a JSON object {\"strings\": [...]} "
              "of the same length and order.\n" + json.dumps(strings, ensure_ascii=False))
    try:
        # Починка отдельных строк, где осталась кириллица: работа механическая — перевести
        # список коротких строк, не трогая маркеры и числа. Дешёвая модель справляется,
        # а вызовов таких много (это ремонт после каждого перевода).
        r = chat("translate_light", prompt + _translation_contract(src),
                 system=_translation_system(target_language))
        fixed = json.loads(clean_json(r.choices[0].message.content)).get("strings")
        if not isinstance(fixed, list) or len(fixed) != len(strings):
            return False
    except Exception:
        return False
    for (container, key, _), new_val in zip(dirty, fixed[:len(dirty)]):
        if isinstance(new_val, str) and new_val.strip():
            container[key] = new_val
    # Ключи меняем с сохранением порядка: key_numbers выводится списком, и перестановка
    # строк выглядела бы как правка данных.
    for (node, old_key), new_key in zip(dirty_keys, fixed[len(dirty):]):
        if not (isinstance(new_key, str) and new_key.strip()) or new_key == old_key:
            continue
        renamed = {(new_key if k == old_key else k): v for k, v in node.items()}
        node.clear()
        node.update(renamed)
    return True


def translate_scipop(scipop, target_lang, retries=1):
    """retries — сбой здесь почти всегда НЕ сетевой (chat() уже отретраила сетевые сама, см.
    common.chat retries=3), а невалидный/недо-JSON в самом ответе модели — стохастическая штука,
    повторный вызов часто проходит нормально. Раньше единственная попытка молча откатывалась на
    непереведённый scipop — статья выглядела "готовой", но текст оставался на языке источника.

    2026-08-06, решение владельца: «мы теряем время и деньги — усиль промт, и всё, не надо
    проверять». Повторов было три, каждый в полную цену, и на плотных числами статьях они
    съедали прогон. Требование сохранять числа перенесено в НАЧАЛО промпта перевода
    (data/prompts/article-translate.txt) с прямым запретом заменять число словами.
    Здесь остаётся одна попытка: платим один раз.

    Сама проверка не выброшена, но БОЛЬШЕ НЕ РЕШАЕТ судьбу перевода — расхождения уходят
    в журнал (logs/translation-failures.log). Это не стоит ни вызова, ни секунды: числа
    сверяются регулярным выражением на готовом тексте. Слепота обошлась бы дороже —
    потерянное число делает текст гладким и ложным, и заметить это можно только открыв
    оригинал, чего не сделает никто."""
    target_language = LANG_NAMES.get(target_lang, target_lang)
    payload = _without_internal(scipop)   # служебные поля модели не нужны — и это минус токены
    prompt = load_prompt("article-translate").format(
        article_json=json.dumps(payload, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, "")) + _termbase_block(scipop, target_lang)
    for attempt in range(1, retries + 1):
        r = chat("translate", prompt + _translation_contract(payload),
                 system=_translation_system(target_language))
        try:
            out = json.loads(clean_json(r.choices[0].message.content))
        except Exception as e:
            if attempt == retries:
                _log_translation_failure("scipop", target_lang, f"{scipop.get('title', '')[:60]!r}: {e}")
            continue
        # Идентификаторы НЕ переводятся: id тега/закона/учёного — это ключ, по которому строится
        # ссылка. После смены роли переводчика на «редактуру носителем» модель стала переводить и их,
        # отчего ссылки вида /tags/markov_chain.html превращались в /tags/سلاسل ماركوف.html (битые).
        # Возвращаем ключи из оригинала кодом — промпту такое доверять нельзя.
        for _k in ("main_tag", "extra_tags", "tags", "scientists", "laws") + _INTERNAL_FIELDS:
            if _k in scipop:
                out[_k] = scipop[_k]
        _keep_based_on(scipop, out)
        ok, problems = validate_translation(scipop, out, target_lang)
        if ok:
            return out
        # Расхождение по ЧИСЛАМ больше не бракует перевод (владелец 2026-08-06). Пишем в журнал
        # и отдаём текст как есть: повтор стоил полной цены вызова, а выигрывал редко — модель
        # спотыкалась на тех же местах. Ставка теперь на промпт, который требует числа первым
        # пунктом. Журнал остаётся, чтобы «стало хуже» было видно по счётчику, а не по письму
        # читателя. ЯЗЫК — другое дело: русский текст под меткой чужого языка не проходит,
        # это не качество, а подделка, и её мы уже ловили шесть раз за один день.
        numeric_only = all(p.startswith("потеряны числа") for p in problems)
        if numeric_only:
            _log_translation_failure("scipop", target_lang,
                                     f"{scipop.get('title', '')[:60]!r}: {'; '.join(problems)} — принято без повтора")
            return out
        # Кириллица — единственная проблема? Точечный добор грязных полей маленьким
        # вызовом вместо полного повтора всего уровня (экономия и времени, и денег).
        if all(p.startswith("кириллица") for p in problems):
            if _retranslate_cyrillic_fields(out, target_lang, target_language, scipop):
                ok2, problems2 = validate_translation(scipop, out, target_lang)
                if ok2:
                    print(f"    ✚ перевод {target_lang}: добор полей вместо полного повтора — прошло")
                    return out
        if attempt == retries:
            _log_translation_failure("scipop", target_lang,
                                     f"{scipop.get('title', '')[:60]!r}: брак перевода — {'; '.join(problems)}")
            # ПОСЛЕДНИЙ ШАНС: перевести по полям, а не целиком. Брак почти всегда локальный —
            # потерялось число в одном абзаце, съелся маркер в другом, — а мы из-за этого
            # выбрасывали весь перевод и подставляли русский. Владелец 2026-08-02: «может,
            # всё надо по частям; проверяй результат сразу, а не узнавай потом».
            partial = _translate_by_fields(scipop, target_lang, target_language)
            if partial is not None:
                print(f"    ✚ перевод {target_lang}: собран по полям после брака целиком")
                return partial
        else:
            print(f"    ↻ перевод {target_lang}: {problems[0]} — повтор {attempt}/{retries}")
    # Тихого отката БОЛЬШЕ НЕТ. Раньше здесь стоял `return scipop` — русский оригинал
    # возвращался как «перевод», страница выходила с флагом чужого языка и русским текстом,
    # и узнавали об этом, только когда владелец открывал сайт. Из 1102 записей в
    # translation-failures.log никто не прочёл ни одной. Пустой перевод честнее поддельного:
    # None означает «языка у статьи нет», вызывающий код это видит и пишет в сводку прогона.
    return None


def _translate_by_fields(scipop, target_lang, target_language):
    """Перевод ПО ПОЛЯМ: длинный уровень режется на отдельные строки и переводится группами.

    Зачем: целиком статья иногда не проходит контроль (модель теряет число или маркер
    где-то в одном месте), и весь труд шёл в мусор. По полям брак локализуется — не вышло
    одно поле, остальные всё равно переведены. Возвращает словарь или None, если не собралось
    даже наполовину: полупустая статья хуже отсутствующей."""
    src_fields = {k: v for k, v in scipop.items()
                  if isinstance(v, str) and v.strip() and k not in _INTERNAL_FIELDS
                  and k not in ("main_tag", "extra_tags", "scientists", "laws")}
    if not src_fields:
        return None
    out = dict(scipop)
    done = 0
    keys = list(src_fields)
    # группами по 4 поля: короткий запрос переживает контроль лучше длинного,
    # но по одному полю платить за системную роль накладно
    for i in range(0, len(keys), 4):
        chunk = {k: src_fields[k] for k in keys[i:i + 4]}
        try:
            r = chat("translate_light",
                     load_prompt("article-translate").format(
                         article_json=json.dumps(chunk, ensure_ascii=False),
                         target_language=target_language,
                         culture_note=CULTURE_NOTES.get(target_lang, ""))
                     + _translation_contract(chunk),
                     system=_translation_system(target_language))
            got = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            continue
        for k in chunk:
            v = got.get(k)
            if isinstance(v, str) and v.strip():
                out[k] = v
                done += 1
    if done < max(1, len(keys) // 2):
        return None
    for _k in ("main_tag", "extra_tags", "tags", "scientists", "laws") + _INTERNAL_FIELDS:
        if _k in scipop:
            out[_k] = scipop[_k]
    return out


def translate_captions(captions_en, target_lang, retries=3):
    """Подписи к рисункам вытаскиваются regex'ом из англоязычного PDF (extract_captions) и
    без этого шага так и остаются на английском на ЛЮБОМ языке сайта. Один вызов на язык —
    переводит весь список сразу (короткие строки, дёшево). retries — см. translate_scipop."""
    if not captions_en:
        return []
    target_language = LANG_NAMES.get(target_lang, target_lang)
    prompt = load_prompt("caption-translate").format(
        captions_json=json.dumps(captions_en, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, ""))
    for attempt in range(1, retries + 1):
        try:
            # Подписи к рисункам — короткие технические строки («Рис. 3: спектр образца»),
            # редактуры носителем они не требуют. Дорогая модель здесь ничего не добавляет,
            # а стоит вчетверо (замер 2026-08-01: $0.0071 против $0.0018 за вызов).
            r = chat("translate_light", prompt)
            data = json.loads(clean_json(r.choices[0].message.content))
            out = data.get("captions") if isinstance(data, dict) else data
            if isinstance(out, list) and len(out) == len(captions_en):
                return out
            if attempt == retries:
                _log_translation_failure("captions", target_lang, f"got {type(out).__name__} len-mismatch")
        except Exception as e:
            if attempt == retries:
                _log_translation_failure("captions", target_lang, str(e))
            continue
    # Последний тихий откат в переводах (находка аудитора 2026-08-05): провал перевода
    # подписей молча оставлял английские. Откат остаётся (подпись на английском лучше
    # отсутствующей — это цитата из PDF), но теперь ГРОМКИЙ: в журнал сбоев, как всё.
    _log_translation_failure("captions", target_lang, f"{len(captions_en)} подписей остались en")
    return captions_en


def validate_tags(scipop, valid_tags_set):
    all_tags = [scipop.get("main_tag", "")] + scipop.get("extra_tags", [])
    fixed = []
    for t in all_tags:
        if not t:
            continue
        if t in valid_tags_set:
            fixed.append(t)
        else:
            t_lower = t.lower().replace(" ", "_").replace("-", "_")
            for vt in valid_tags_set:
                if vt in t_lower or t_lower in vt:
                    fixed.append(vt)
                    break
    seen = set()
    fixed_unique = []
    for t in fixed:
        if t not in seen:
            seen.add(t)
            fixed_unique.append(t)
    if fixed_unique:
        scipop["main_tag"] = fixed_unique[0]
        scipop["extra_tags"] = fixed_unique[1:11] if len(fixed_unique) > 1 else []
    return scipop


def generate_simple_mini(scipop_popular):
    """simple + mini ОДНИМ вызовом из popular (ТЗ 2026-07-27, §4): mini — выжимка из simple,
    а не из advanced; фактура наследуется кодом. Возвращает (simple_dict, mini_text)."""
    prompt = load_prompt("article-generate-simple").format(
        popular_json=json.dumps(scipop_popular, ensure_ascii=False),
        advanced_json=json.dumps(scipop_popular, ensure_ascii=False))
    reinforce = "\n\nВНИМАНИЕ: пиши СТРОГО на русском языке."
    data = None
    for attempt in range(2):
        r = chat("article_simple", prompt if attempt == 0 else prompt + reinforce)
        try:
            data = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            return scipop_popular, ""
        if _default_lang_ok(data):
            break
    mini = (data.pop("mini", "") or "").strip()
    return inherit_facts(data, scipop_popular), mini
