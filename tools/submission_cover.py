#!/usr/bin/env python3
"""Обложка авторской работы — заметно ярче, чем у обычной статьи.

Владелец 2026-08-08: «на кастомные статьи особенные хорошие картинки генери, чтобы были
класс», «обложка чтобы была в цветах, контраст, чтобы выделялась».

Почему отдельно от covers_full.py. Тот идёт по архиву arXiv и берёт текст статьи из
data.json. У авторской работы ни архива, ни data.json — она живёт в data/submissions и
собирается своим конвейером. Плюс задача другая: обложка статьи должна вписываться в ленту
и не спорить с соседками, а обложка авторской работы должна из ленты ВЫДЕЛЯТЬСЯ — таких
работ единицы, и они наше отличие от arXiv.

Отсюда и разница в промпте: насыщенный цвет, сильный контраст, один ясный объект вместо
общей научной абстракции. Модель — FLUX-2-pro, тот же высокий пресет, что у полных статей.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import common  # noqa: F401  подхватывает .env
import gen_llm
import generate

HQ_PRESET = "image_quality"


def _prompt(work: dict) -> str:
    """Промпт для FLUX по нашему же пересказу работы.

    Не отдаём модели сырой текст автора: он длинный, полон формул и обозначений, и картинка
    выходит про формулы. Берём наш пересказ — он уже про смысл.
    """
    ours = (work.get("ours", {}) or {}).get("ru", {}) or {}
    title = ours.get("title") or work.get("title", "")
    one = ours.get("oneliner", "")
    body = (ours.get("simple") or ours.get("mini") or "")[:1200]
    kind = work.get("kind", "")

    ask = (
        "Придумай промпт для генератора изображений (FLUX) — обложку научной работы.\n\n"
        f"НАЗВАНИЕ: {title}\n"
        f"О ЧЁМ: {one}\n"
        f"ВИД РАБОТЫ: {kind}\n"
        f"ТЕКСТ: {body}\n\n"
        "Требования к картинке:\n"
        "· ОДИН ясный образ по сути работы, а не коллаж из научных значков;\n"
        "· насыщенные цвета и сильный контраст — обложка должна выделяться в ленте среди\n"
        "  сдержанных научных иллюстраций, но не выглядеть кричащей рекламой;\n"
        "· глубокий тёмный фон, свет падает на главный объект;\n"
        "· без текста, надписей, формул, цифр и подписей на изображении;\n"
        "· без людей и лиц;\n"
        "· горизонтальная композиция, объект смещён от центра, есть воздух.\n\n"
        "Промпт пиши по-английски, одним абзацем, 60–90 слов, конкретными зримыми деталями.\n"
        'Ответь JSON: {"prompt": "..."}'
    )
    from common import chat, clean_json
    for _ in range(3):
        try:
            r = chat("image_prompt", ask)
            got = json.loads(clean_json(r.choices[0].message.content or "")).get("prompt", "")
            if got:
                return got.strip()
        except Exception as ex:
            print(f"  ⚠️ промпт обложки не вышел: {type(ex).__name__}")
    return ""


def build(code: str) -> str:
    """Рисует обложку и кладёт рядом со страницей. Возвращает публичный адрес или ''."""
    box = ROOT / "data" / "submissions" / code
    pj = box / "publish.json"
    if not pj.exists():
        print(f"  ⚠️ {code}: нет publish.json — работа ещё не опубликована")
        return ""
    work = json.loads(pj.read_text(encoding="utf-8"))

    prompt = _prompt(work)
    if not prompt:
        return ""
    print(f"  🎨 промпт: {prompt[:110]}…")

    d = ROOT / "lang" / "ru" / "community" / code
    d.mkdir(parents=True, exist_ok=True)
    jpg = d / "cover.jpg"
    ok, model = gen_llm.generate_image(prompt, jpg, preset=HQ_PRESET)
    if not ok:
        print("  ⚠️ обложка не нарисовалась")
        return ""

    # webp пишем сразу и с перезаписью: иначе на сайте останется прежняя картинка —
    # на этих граблях уже стояли, когда меняли обложки статей.
    try:
        from PIL import Image
        im = Image.open(jpg)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(jpg.with_suffix(".webp"), "WEBP", quality=90, method=4)
    except Exception as ex:
        print(f"  ⚠️ webp не вышел: {ex}")

    url = f"/lang/ru/community/{code}/cover.jpg"
    work["cover_url"] = url
    work["cover_prompt"] = prompt
    work["cover_model"] = model
    pj.write_text(json.dumps(work, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  🖼️ обложка: {jpg.stat().st_size // 1024} КБ, {model}")
    return url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("нужен код работы: python tools/submission_cover.py b42p-2026-001")
        sys.exit(2)
    print(build(sys.argv[1]) or "не получилось")
