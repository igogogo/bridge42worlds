#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Миниатюры ленты в человеческом качестве: 560 px вместо 220, обрезка под блок.

Владелец 2026-08-25: «миникартинки в ленте плохо смотрятся, давай улучшим».

ЗАМЕР, из которого всё следует. Миниатюра генерировалась шириной 220 px (JPEG q72,
средний вес 6 КБ). Блок в ленте: на десктопе 130 css при соотношении 3:2, на телефоне —
во всю ширину карточки, около 343 css при 16:9. На экране с двойной плотностью телефону
нужно 686 физических пикселей, при тройной — 1029. Мы давали 220: увеличение втрое-впятеро,
отсюда и мыло. На самой статье та же обложка выглядит хорошо, потому что там подставляется
полноразмерная — потому дефект и не бросался в глаза при проверке страниц.

ВТОРАЯ ПРИЧИНА — ОБРЕЗКА. Блок требует 16:9 на телефоне, а 48% обложек квадратные (1:1):
браузер режет их по бокам почти вдвое, и от композиции остаётся середина. Здесь обрезаем
сами и осмысленно: берём центр по горизонтали, но по вертикали смещаем срез ВВЕРХ на
треть — у наших обложек смысловой центр почти всегда выше геометрического (схема сверху,
свечение снизу). Проверяется глазами, а не теорией.

ЧТО НЕ ДЕЛАЕМ. Модель не зовём ни разу: исходники лежат на диске (7200×3600 у части
обложек), запас качества уже оплачен — мы его просто не брали.

    python tools/thumbs_hq.py --pilot 10        десять статей, посмотреть
    python tools/thumbs_hq.py --all             весь архив
"""
import argparse
import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# 720: телефон при двойной плотности просит 686 физических пикселей, при тройной 1029.
# 720 закрывает двойную с запасом и заметно смягчает тройную. Замер веса на живой обложке:
# 560 → 10 КБ, 720 → 17 КБ, 900 → 27 КБ. Берём середину — резкость видна, вес терпим.
WIDTH = 720
RATIO = 16 / 9       # соотношение блока на телефоне; десктопный 3:2 из него обрезается
QUALITY = 78


def crop_to_ratio(im, ratio):
    """Обрезка под соотношение блока. По вертикали срез смещён вверх на треть —
    у наших обложек смысловой центр выше геометрического."""
    w, h = im.size
    want_h = w / ratio
    if want_h <= h:
        top = (h - want_h) / 3          # не /2: сдвиг вверх
        return im.crop((0, int(top), w, int(top + want_h)))
    want_w = h * ratio
    left = (w - want_w) / 2
    return im.crop((int(left), 0, int(left + want_w), h))


def build(folder, width=WIDTH, dry=False):
    from PIL import Image
    # Часть исходников из PDF — гигантские развороты (7000×9000 и больше), и Pillow
    # по умолчанию считает такое попыткой атаки и отказывается открывать. Это наши
    # собственные файлы с диска, а не присланные извне: снимаем ограничение.
    Image.MAX_IMAGE_PIXELS = None
    folder = Path(folder)
    src = None
    for name in ("ai.jpg", "ai.webp"):
        p = folder / name
        if p.exists() and p.stat().st_size > 2000:
            src = p
            break
    if not src:
        return None
    try:
        im = Image.open(src).convert("RGB")
    except Exception as e:
        print(f"  ⚠️ {folder.name}: {type(e).__name__}")
        return None
    before = im.size
    im = crop_to_ratio(im, RATIO)
    if im.width > width:
        im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
    if dry:
        return (before, im.size)
    out = folder / "t_ai.webp"
    im.save(out, "WEBP", quality=QUALITY, method=6)
    # jpg-двойник тоже обновляем: старые страницы просят его как запасной.
    im.save(folder / "t_ai.jpg", "JPEG", quality=QUALITY, optimize=True)
    return (before, im.size, out.stat().st_size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--width", type=int, default=WIDTH)
    args = ap.parse_args()

    folders = sorted({Path(p).parent for p in
                      glob.glob(str(ROOT / "lang/ru/archive/*/*/ai.*"))}, reverse=True)
    if args.pilot:
        folders = folders[:args.pilot]
    elif not args.all:
        print("укажи --pilot N или --all")
        return 1

    done = total = 0
    for f in folders:
        r = build(f, args.width, args.dry)
        if not r:
            continue
        done += 1
        if args.dry:
            print(f"  {f.name}: {r[0]} → {r[1]}")
        else:
            total += r[2]
            if done <= 10:
                print(f"  {f.name}: {r[0]} → {r[1]}, {r[2] // 1024} КБ")
    print(f"\nобновлено миниатюр: {done}"
          + (f" · средний вес {total // max(done, 1) // 1024} КБ" if not args.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
