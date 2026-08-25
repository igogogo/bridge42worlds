#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Добивка отсутствующих обложек дешёвой моделью — статьи и понятия.

ОТКУДА ДЫРЫ. Аудит 25 августа: у 43 статей после 15 августа обложек нет вовсе — ни FLUX,
ни кадра из PDF (дни, когда фабрика падала по сети, дорисовать было некому). И 32 понятия
остались голыми после слияния тегов в облако законов: 360 обложек переехали копированием,
а этих 32 не было и у тегов.

ЧЕМ РИСУЕМ. FLUX-1-schnell (preset image_cheap) — решение владельца: «платные обложки для
особых случаев пока отложим, если вообще нет картинок в PDF — рисуем бесплатно». Поле
image_model честно записывает, чем сгенерено: дешёвые потом легко найти и точечно поднять
до pro. Промпт — общий (data/prompts/image-generate.txt), только что обогащённый палитрой,
светом и настроением: владелец поймал набор на однотипности и белесости, причина была в
том, что шесть измерений вариаций существовали в коде, а в промпт попадало одно.

    python tools/cover_backfill.py --dry              что нарисуется
    python tools/cover_backfill.py --since 2026-08-15 статьи с даты + все голые понятия
    python tools/cover_backfill.py --all              все статьи без обложки (их ~1.5 тыс.)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import gen_llm
from generate import make_thumbnails


def article_targets(since, all_):
    """Статьи без всякой обложки: нет ai.jpg/ai.webp и нет ни одного кадра из PDF."""
    out = []
    for d in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json")):
        folder = d.parent
        if (folder / "ai.webp").exists() or (folder / "ai.jpg").exists():
            continue
        if (folder / "0.jpg").exists():
            continue                      # кадр из PDF есть — обложку выберет пайплайн
        date = folder.parent.name
        if not all_ and (not since or date < since):
            continue
        out.append(folder)
    return out


def concept_targets():
    """Понятия без обложки: страница есть, картинки в laws/img нет."""
    img = {p.stem for p in (ROOT / "lang/ru/laws/img").glob("*.webp")}
    out = []
    for p in sorted((ROOT / "lang/ru/laws").glob("*.html")):
        if p.stem not in img:
            out.append(p.stem)
    return out


def concept_scipop(key):
    """Подобие статьи для генератора промпта — из справочника законов."""
    for name in ("laws-lite.json",):
        f = ROOT / "data" / name
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        e = data.get(key) or {}
        title = (e.get("name") or {}).get("en") if isinstance(e.get("name"), dict) else e.get("name")
        desc = (e.get("desc") or {}).get("en") if isinstance(e.get("desc"), dict) else e.get("desc")
        if title or desc:
            return {"title": title or key.replace("_", " "),
                    "oneliner": desc or "", "description": desc or "",
                    "main_tag": key, "extra_tags": []}
    return {"title": key.replace("_", " "), "oneliner": "", "description": "",
            "main_tag": key, "extra_tags": []}


def draw_article(folder):
    try:
        d = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    ru = (d.get("versions") or {}).get("popular") or {}
    scipop = {"title": ru.get("title") or d.get("original_title", ""),
              "oneliner": ru.get("oneliner", ""),
              "description": ru.get("description", "") or (d.get("abstract") or {}).get("ru", ""),
              "main_tag": d.get("main_tag", ""), "extra_tags": d.get("tags", [])[:5]}
    prompt = gen_llm.generate_image_prompt(scipop)
    if not prompt:
        return False
    ok, model = gen_llm.generate_image(prompt, folder / "ai.jpg", preset="image_cheap")
    if not ok:
        return False
    # webp-двойник и миниатюры — как делает пайплайн; страницы просят оба формата
    try:
        from PIL import Image
        im = Image.open(folder / "ai.jpg").convert("RGB")
        im.save(folder / "ai.webp", "WEBP", quality=84, method=6)
    except Exception:
        pass
    d["image_model"] = model
    d["image_prompt"] = prompt
    (folder / "data.json").write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    make_thumbnails(folder)
    return True


def draw_concept(key):
    prompt = gen_llm.generate_image_prompt(concept_scipop(key))
    if not prompt:
        return False
    out = ROOT / "lang/ru/laws/img" / f"{key}.jpg"
    ok, model = gen_llm.generate_image(prompt, out, preset="image_cheap")
    if not ok:
        return False
    try:
        from PIL import Image
        im = Image.open(out).convert("RGB")
        im.save(out.with_suffix(".webp"), "WEBP", quality=84, method=6)
    except Exception:
        pass
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--since", default="2026-08-15")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    arts = article_targets(args.since, args.all)
    cons = concept_targets()
    if args.limit:
        arts = arts[:args.limit]
    print(f"статей без всякой обложки: {len(arts)} · понятий без обложки: {len(cons)}")
    if args.dry:
        for f in arts[:10]:
            print("   ", f.parent.name, f.name)
        print("   понятия:", ", ".join(cons[:10]), "…" if len(cons) > 10 else "")
        return 0

    ok = bad = 0
    for f in arts:
        r = draw_article(f)
        ok += 1 if r else 0
        bad += 0 if r else 1
        print(f"   {'✓' if r else '✗'} {f.name}")
    for k in cons:
        r = draw_concept(k)
        ok += 1 if r else 0
        bad += 0 if r else 1
        print(f"   {'✓' if r else '✗'} понятие {k}")
    print(f"\nнарисовано: {ok} · не вышло: {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
