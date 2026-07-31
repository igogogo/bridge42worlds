"""jpg → webp по всему сайту (юзер 2026-07-25: «картинки оригинал локально сохрани, gitignore их,
переименуй — поехали»). Оригиналы .jpg ОСТАЮТСЯ на диске (в .gitignore), в git и на сервер уходят
только .webp: 7.08 ГБ → ~2.2 ГБ без видимой потери качества.

Запуск:  python webp_convert.py            # конвертация всех (пропускает уже готовые)
         python webp_convert.py --check     # только посчитать, сколько осталось
"""
import sys
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # огромные страницы PDF — не бомба, это наши сканы

# cp1252-консоль Windows роняет печать ✅/❌ при ручном запуске
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUALITY = 88
ROOTS = ["lang"]


def targets():
    out = []
    for r in ROOTS:
        for p in Path(r).rglob("*.jpg"):
            w = p.with_suffix(".webp")
            # Не только «webp нет», но и «jpg свежее webp»: regen с 2026-07-31 пишет ПОВЕРХ
            # старой папки (реюз оплаченного), и перезаписанный jpg при пропуске по exists
            # молча оставлял бы читателю старую картинку — сайт отдаёт webp, не jpg.
            if not w.exists() or w.stat().st_mtime < p.stat().st_mtime:
                out.append(str(p))
    return out


def convert(src):
    try:
        p = Path(src)
        im = Image.open(p)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(p.with_suffix(".webp"), "WEBP", quality=QUALITY, method=4)
        return 1
    except Exception:
        return 0


def main():
    todo = targets()
    total_jpg = sum(1 for r in ROOTS for _ in Path(r).rglob("*.jpg"))
    print(f"всего .jpg: {total_jpg:,} | к конвертации: {len(todo):,}", flush=True)
    if "--check" in sys.argv or not todo:
        return
    done = 0
    # щадящий режим: треть ядер, чтобы комп не отваливался
    with ProcessPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) // 3)) as ex:
        for ok in ex.map(convert, todo, chunksize=64):
            done += ok
            if done % 2000 == 0:
                print(f"  … {done:,}/{len(todo):,}", flush=True)
    jb = sum(p.stat().st_size for r in ROOTS for p in Path(r).rglob("*.jpg"))
    wb = sum(p.stat().st_size for r in ROOTS for p in Path(r).rglob("*.webp"))
    print(f"✅ готово: {done:,} файлов | jpg {jb/1024**3:.2f} ГБ → webp {wb/1024**3:.2f} ГБ", flush=True)


if __name__ == "__main__":
    main()
