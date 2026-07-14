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

from common import CONFIG, AGENTS, DEFAULT_LANG, chat, clean_json, load_prompt

SELECTION_PERCENT = CONFIG.get("selection_percent", 10)
MAX_ARTICLES = CONFIG.get("max_articles", 10)

LANG_NAMES = {
    "ru": "Russian", "en": "English", "cn": "Chinese", "zh": "Chinese",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "nl": "Dutch",
}

CULTURE_NOTES = {
    "ar": ("ВАЖНО — КУЛЬТУРНАЯ АДАПТАЦИЯ ДЛЯ АРАБСКОЙ И МУСУЛЬМАНСКОЙ АУДИТОРИИ (в т.ч. читатели "
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


def select_best(articles, date_str):
    total = len(articles)
    count = max(1, total * SELECTION_PERCENT // 100)
    count = min(count, MAX_ARTICLES)
    if total <= count:
        return articles
    j = json.dumps([{"id": a["id"], "title": a["title"], "summary": a["summary"][:500]} for a in articles],
                   ensure_ascii=False)
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
        return [a for a in articles if a["id"] in ids][:count]
    except Exception:
        return articles[:count]


def select_best_n(articles, count, tag="bulk"):
    """Как select_best(), но count задаётся явно (не через SELECTION_PERCENT/MAX_ARTICLES) —
    для bulk-каскада (article_bulk_select.py), где нужен контроль над соотношением на каждом
    проходе, а не фиксированный дневной процент. Тот же промт/критерии — тот же вкус отбора."""
    total = len(articles)
    if total <= count:
        return articles
    j = json.dumps([{"id": a["id"], "title": a["title"], "summary": a["summary"][:500]} for a in articles],
                   ensure_ascii=False)
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
        return [a for a in articles if a["id"] in ids][:count]
    except Exception:
        return articles[:count]


def rank_articles(articles, tag="bulk"):
    """Ранжирующий (не отсеивающий) проход: оценка 1-10 по тем же критериям, что и отбор —
    для приоритезации внутри уже прошедшего каскад пула (bulk-select, раунд 3). Возвращает
    {{id: score}}; отсутствующие в ответе модели статьи получают нейтральный score=5."""
    j = json.dumps([{"id": a["id"], "title": a["title"], "summary": a["summary"][:500]} for a in articles],
                   ensure_ascii=False)
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


def generate_advanced(article, text, tags_input, scientists_keys):
    tags_list = ", ".join(t["en"] for t in tags_input)
    scientists_list = ", ".join(scientists_keys)
    prompt = load_prompt("article-generate-advanced").format(
        tags_list=tags_list, scientists_list=scientists_list, article_text=text)
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
    return result


def generate_express(article, abstract_text, tags_input, scientists_keys):
    """Экспресс-режим: ОДИН вызов вместо каскада advanced→simple→popular. Источник — только
    авторская аннотация (короткая, уже готова из arXiv API — не парсим PDF), не полный текст
    статьи. Даёт mini+simple разом. Обложка/мозаика всё равно берутся из PDF (см. build_article),
    просто текст для генерации — дешёвый и короткий. tags_input — обычно урезанное express-
    подмножество (лестница дешевле не только по input article_text, но и по списку тегов в промте)."""
    tags_list = ", ".join(t["en"] for t in tags_input)
    scientists_list = ", ".join(scientists_keys)
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


def generate_image(image_prompt, out_path):
    """Рисует картинку (DeepInfra, модель/размер из config.agents.image). Без ключа — пропуск."""
    key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not key or not image_prompt:
        return False
    cfg = AGENTS.get("image", {})
    try:
        import base64
        cli = OpenAI(base_url="https://api.deepinfra.com/v1/openai", api_key=key)
        resp = cli.images.generate(model=cfg.get("model", "black-forest-labs/FLUX-2-pro"),
                                   prompt=image_prompt, n=1, size=cfg.get("size", "1024x1024"))
        Path(out_path).write_bytes(base64.b64decode(resp.data[0].b64_json))
        return True
    except Exception as e:
        print(f"    ⚠️ FLUX error: {e}")
        return False


def generate_simple(scipop_advanced):
    prompt = load_prompt("article-generate-simple").format(
        advanced_json=json.dumps(scipop_advanced, ensure_ascii=False))
    reinforce = "\n\nВНИМАНИЕ: пиши СТРОГО на русском языке."
    data = None
    for attempt in range(2):
        r = chat("article_simple", prompt if attempt == 0 else prompt + reinforce)
        try:
            data = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            return scipop_advanced
        if _default_lang_ok(data):
            break
    data["main_tag"] = scipop_advanced.get("main_tag", "")
    data["extra_tags"] = scipop_advanced.get("extra_tags", [])
    data["scientists"] = scipop_advanced.get("scientists", [])
    return data


def generate_popular(scipop_adv):
    """Самая простая версия, генерируется из Advanced (не из Simple — независимо)."""
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
    data["main_tag"] = scipop_adv.get("main_tag", "")
    data["extra_tags"] = scipop_adv.get("extra_tags", [])
    data["scientists"] = scipop_adv.get("scientists", [])
    return data


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
        if "mini" in scipop:
            data["mini"] = scipop.get("mini", "")
        return data
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
        return data
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
_ABSTRACT_HARD_LIMITS = {"simple": 500, "popular": 750, "advanced": 1200}


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
    """Адаптирует авторский arXiv-abstract в «Аннотацию» на RU в ТРЁХ регистрах
    (popular/simple/advanced) одним вызовом. Возвращает {level: text}. До 3 попыток."""
    summary = (summary or "").strip()
    if not summary:
        return {}
    prompt = load_prompt("abstract-adapt").format(summary=summary)
    for _ in range(3):
        try:
            data = json.loads(clean_json(chat("abstract", prompt).choices[0].message.content))
        except Exception:
            data = {}
        levels = {v: (data.get(v, "") or "").strip() for v in ABSTRACT_LEVELS}
        if any(levels.values()):
            fb = next((t for t in levels.values() if t), "")  # если модель дала не все уровни — добить непустым
            return {v: _cap_text(levels[v] or fb, _ABSTRACT_HARD_LIMITS[v]) for v in ABSTRACT_LEVELS}
    return {}


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


def translate_scipop(scipop, target_lang):
    target_language = LANG_NAMES.get(target_lang, target_lang)
    prompt = load_prompt("article-translate").format(
        article_json=json.dumps(scipop, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, ""))
    r = chat("translate", prompt)
    try:
        return json.loads(clean_json(r.choices[0].message.content))
    except Exception:
        return scipop


def translate_captions(captions_en, target_lang):
    """Подписи к рисункам вытаскиваются regex'ом из англоязычного PDF (extract_captions) и
    без этого шага так и остаются на английском на ЛЮБОМ языке сайта. Один вызов на язык —
    переводит весь список сразу (короткие строки, дёшево)."""
    if not captions_en:
        return []
    target_language = LANG_NAMES.get(target_lang, target_lang)
    prompt = load_prompt("caption-translate").format(
        captions_json=json.dumps(captions_en, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, ""))
    try:
        r = chat("translate", prompt)
        data = json.loads(clean_json(r.choices[0].message.content))
        out = data.get("captions") if isinstance(data, dict) else data
        if isinstance(out, list) and len(out) == len(captions_en):
            return out
    except Exception:
        pass
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
