"""Обложки FLUX-2-pro для ПОЛНЫХ статей (не экспресс).

Зачем отдельный скрипт, а не `run.py images`: тот всегда предпочитает кадр из PDF и, если
ai.jpg уже есть, статью пропускает. Поэтому 68 полных статей навсегда оставались с кадром из
PDF, а 23 — пустыми. Здесь идём по полным статьям и рисуем всем, у кого нет FLUX-2-pro.

Оригиналы кадров из PDF не теряются: они лежат рядом как 0.jpg, 1.jpg… — перезаписывается
только ai.jpg (это и так была копия выбранного кадра).

webp пишем сами: webp_convert.py пропускает файл, если .webp уже есть, поэтому после замены
обложки на сайте остался бы старый снимок.

    python _covers_full.py --dry              # только показать, кого возьмём
    python _covers_full.py --limit 3          # проба на трёх
    python _covers_full.py                    # все
"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common  # подхватывает .env  # noqa: F401
import generate
import gen_llm

HQ = "black-forest-labs/FLUX-2-pro"
ARCHIVE = Path("lang/ru/archive")


def targets():
    out = []
    for data_file in ARCHIVE.glob("*/*/data.json"):
        try:
            d = json.loads(data_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("express") and not INCLUDE_EXPRESS:
            continue                      # экспресс — второй эшелон, не трогаем по умолчанию
        if d.get("image_model") == HQ:
            continue                      # уже нарисовано в высоком качестве
        out.append((data_file, d))
    return sorted(out, key=lambda t: str(t[0]))


# Экспрессы берём только по явному указанию: в ленте их карточка выглядит наравне с полной,
# и когда собираешь страницу конкретного учёного, половина работ без картинки — это дыра
# на витрине. Массово же рисовать экспрессам дорогие обложки незачем.
INCLUDE_EXPRESS = False


def to_webp(jpg: Path):
    """jpg → webp с перезаписью (иначе на сайте останется прежняя картинка)."""
    try:
        from PIL import Image
        im = Image.open(jpg)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(jpg.with_suffix(".webp"), "WEBP", quality=88, method=4)
        return True
    except Exception as e:
        print(f"    webp не вышел: {jpg.name}: {e}")
        return False


def one(item):
    data_file, d = item
    folder = data_file.parent
    lang = generate.DEFAULT_LANG
    scipop = (d.get("popular", {}).get(lang) or d.get("simple", {}).get(lang)
              or d.get("advanced", {}).get(lang) or {})
    if not scipop:
        return "нет текста", folder.name

    prompt = gen_llm.generate_image_prompt(scipop)
    if not prompt:
        return "пустой промпт", folder.name

    img = folder / "ai.jpg"
    ok, model = gen_llm.generate_image(prompt, img, preset="image_quality")
    if not ok:
        return "картинка не вышла", folder.name

    d["image_prompt"] = prompt
    d["image_model"] = model
    d["image_pending"] = False
    d["thumbs"] = generate.make_thumbnails(folder)
    data_file.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    to_webp(img)
    t = folder / "t_ai.jpg"
    if t.exists():
        to_webp(t)
    return "ok", folder.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    # Точечно по автору: обложки дорогие, и чаще всего нужны не «все подряд», а конкретный
    # набор — работы одного учёного к его странице, свежая волна, разбор для встречи.
    ap.add_argument("--author", help="только статьи этого автора (подстрока имени)")
    ap.add_argument("--ids", nargs="*", help="только эти arXiv id")
    a = ap.parse_args()

    items = targets()
    global INCLUDE_EXPRESS
    if a.author or a.ids:
        INCLUDE_EXPRESS = True
        items = targets()
    if a.author:
        items = [(f, d) for f, d in items
                 if any(a.author.lower() in str(x).lower() for x in (d.get("authors") or []))]
    if a.ids:
        want = set(a.ids)
        items = [(f, d) for f, d in items if d.get("id") in want]
    if a.limit:
        items = items[:a.limit]
    print(f"Полных статей без FLUX-2-pro: {len(items)}")
    if a.dry:
        for f, d in items[:20]:
            print("   ", f.parent.name, "| было:", d.get("image_model") or ("PDF-кадр" if (f.parent / "ai.jpg").exists() else "пусто"))
        return

    t0 = time.time()
    done = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, (status, name) in enumerate(ex.map(one, items), 1):
            done[status] = done.get(status, 0) + 1
            if status != "ok":
                print(f"  [{i}/{len(items)}] {name}: {status}")
            elif i % 10 == 0:
                print(f"  [{i}/{len(items)}] ... {int(time.time()-t0)}с")
    print("Итого:", done, f"за {int(time.time()-t0)}с")


main()
