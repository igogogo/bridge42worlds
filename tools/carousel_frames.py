#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кадры для карусели в ленте: отбор годных картинок из PDF и сборка под десктопный блок.

Владелец 2026-08-25: «что если сделать карусель в ленте, а то динамики не хватает — на экране
я вижу всего две-три карточки, а так они ещё будут крутиться».

МАТЕРИАЛ УЖЕ ЕСТЬ. make_thumbnails давно кладёт рядом с обложкой до шести кадров из PDF
(t_0..t_5) — их 21 027 на архив. Они делались для полоски превью под галереей (блок 66×44 css),
поэтому 220 px им хватало. Для ленты этого мало, и переиспользовать их напрямую нельзя.

ПОЧЕМУ 400, А НЕ 720 КАК У ОБЛОЖКИ. Обложке 720 нужно потому, что на телефоне она идёт во всю
ширину карточки (343 css → 686 физических при двойной плотности). Карусель по решению владельца
только десктопная, а там блок .card-img-wrap — 130 css при 3:2, то есть 260 физических пикселей
при двойной плотности и 390 при тройной. 400 закрывает и тройную. Вчетверо дешевле, и разницы
на экране нет никакой.

ПОЧЕМУ НЕ ВСЕ КАДРЫ. Кадры из PDF — это графики, схемы и микроскопия. В блоке 130 px серый скан
и график с осями на белом фоне выглядят пустым прямоугольником: карусель, которая раз в три
секунды показывает белое пятно, хуже статичной карточки. Отбор идёт по трём дешёвым признакам
(насыщенность, доля белого, форма) — тем же, которыми мерился аудит обложек. Проходит 47%.

Порог здесь МЯГЧЕ, чем был бы для обложки: карусель — добавка к обложке, а не единственная
картинка статьи, и потерять живой кадр из-за строгости обиднее, чем показать средний.

    python tools/carousel_frames.py --pilot 20     двадцать статей, посмотреть глазами
    python tools/carousel_frames.py --all          весь архив + справочник для ленты
    python tools/carousel_frames.py --all --force  пересобрать уже собранное
"""
import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

WIDTH = 400          # см. шапку: десктопный блок 130 css, тройная плотность = 390
RATIO = 3 / 2        # соотношение .card-img-wrap
QUALITY = 78
MAX_FRAMES = 3       # больше трёх в ленте никто не досмотрит
SCAN = 6             # столько кадров вынимает make_thumbnails (config.card_pdf_thumbs)

MAP = ROOT / "data" / "carousel.json"


def metrics(im):
    """Насыщенность и доля почти белого. Считаем по уменьшенной копии 48×48: точности
    хватает, а полноразмерный разворот 7000×9000 так не читается по пикселю."""
    s = im.resize((48, 48), Image.BILINEAR)
    px = list(s.getdata())
    sat = white = 0.0
    for r, g, b in px:
        mx, mn = max(r, g, b), min(r, g, b)
        sat += (mx - mn) / max(mx, 1)
        if r > 238 and g > 238 and b > 238:
            white += 1
    n = len(px)
    return sat / n, white / n


def good(im):
    w, h = im.size
    r = w / max(h, 1)
    sat, white = metrics(im)
    if sat < 0.04:              # серый скан, чёрно-белый график
        return False
    if white > 0.62:            # больше двух третей белого — в блоке это пустота
        return False
    if r > 3.0 or r < 0.45:     # панорама или колонка: от обрезки остаётся бессмыслица
        return False
    return True


def crop_to_ratio(im, ratio=RATIO):
    """Та же обрезка, что у обложек: центр по горизонтали, срез вверх на треть.
    У научных картинок смысл (схема, подпись оси) обычно выше геометрического центра."""
    w, h = im.size
    want_h = w / ratio
    if want_h <= h:
        top = (h - want_h) / 3
        return im.crop((0, int(top), w, int(top + want_h)))
    want_w = h * ratio
    left = (w - want_w) / 2
    return im.crop((int(left), 0, int(left + want_w), h))


NONE_MARK = "c_none"     # «проверено, годного кадра нет» — см. build()


def build(folder, force=False):
    """Собирает c_0..c_2 в папке статьи. Возвращает число кадров карусели."""
    folder = Path(folder)
    done = sorted(folder.glob("c_[0-9].webp"))
    if done and not force:
        return len(done)                     # идемпотентно: пересборки не устраиваем
    mark = folder / NONE_MARK
    if mark.exists() and not force:
        # Пустая метка вместо «просто нет файлов». Без неё у четверти архива (кадры есть,
        # но ни один не прошёл отбор) каждый ежедневный прогон заново открывал бы по шесть
        # полноразмерных разворотов из PDF — часы работы ради заведомо пустого результата.
        return 0
    for p in done:
        p.unlink()
    if mark.exists():
        mark.unlink()
    n = 0
    for i in range(SCAN):
        if n >= MAX_FRAMES:
            break
        src = folder / f"{i}.jpg"            # берём ОРИГИНАЛ, а не готовую миниатюру
        if not src.exists() or src.stat().st_size < 2000:
            continue
        try:
            im = Image.open(src).convert("RGB")
        except Exception:
            continue
        if not good(im):
            continue
        im = crop_to_ratio(im)
        if im.width > WIDTH:
            im = im.resize((WIDTH, max(1, round(im.height * WIDTH / im.width))), Image.LANCZOS)
        try:
            im.save(folder / f"c_{n}.webp", "WEBP", quality=QUALITY, method=6)
        except Exception:
            continue
        n += 1
    if not n:
        (folder / NONE_MARK).write_bytes(b"")
    return n


def write_map(counts):
    """Справочник «статья → сколько кадров». Лента подхватывает его одним запросом.

    В индекс ленты это класть НЕЛЬЗЯ: 13 августа поле thumbs оттуда как раз убрали, потому
    что индекс на пять языков весил 30 МБ и грузится он у каждого читателя. Отдельный файл
    в 90 КБ тянется один раз, лениво, и только на десктопе — там, где карусель вообще есть."""
    MAP.parent.mkdir(parents=True, exist_ok=True)
    tmp = MAP.with_suffix(".tmp")
    tmp.write_text(json.dumps(counts, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    tmp.replace(MAP)
    return MAP.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    # Справочник целиком выводится из имён файлов на диске, поэтому его всегда можно
    # пересобрать отдельно — например, если прогон оборвался на середине и кадры уже
    # лежат, а карта ещё не записана.
    ap.add_argument("--map-only", action="store_true")
    args = ap.parse_args()

    if args.map_only:
        counts = {}
        for f in sorted({Path(x).parent for x in
                         glob.glob(str(ROOT / "lang/ru/archive/*/*/c_0.webp"))}):
            n = len(list(f.glob("c_[0-9].webp")))
            if n:
                counts[f.name] = n
        size = write_map(counts)
        print(f"статей с каруселью: {len(counts)} · кадров "
              f"{sum(counts.values())} · справочник {size // 1024} КБ")
        return 0

    global Image
    from PIL import Image as _I
    Image = _I
    # Часть кадров из PDF — гигантские развороты; Pillow считает такое атакой и отказывается
    # открывать. Это наши собственные файлы с диска.
    Image.MAX_IMAGE_PIXELS = None

    folders = sorted({Path(p).parent for p in
                      glob.glob(str(ROOT / "lang/ru/archive/*/*/0.jpg"))}, reverse=True)
    if args.pilot:
        folders = folders[:args.pilot]
    elif not args.all:
        print("укажи --pilot N или --all")
        return 1

    counts, made, total = {}, 0, 0
    for i, f in enumerate(folders, 1):
        n = build(f, args.force)
        if n:
            counts[f.name] = n
            made += n
            total += sum(p.stat().st_size for p in f.glob("c_[0-9].webp"))
        if args.pilot and n:
            print(f"  {f.name}: {n} кадр(ов)")
        elif i % 500 == 0:
            print(f"  … {i}/{len(folders)} · кадров {made}")

    print(f"\nстатей с каруселью: {len(counts)} из {len(folders)} · "
          f"кадров {made} · {total // 1024 // 1024} МБ"
          + (f" · средний вес {total // max(made, 1) // 1024} КБ" if made else ""))
    if args.all:
        size = write_map(counts)
        print(f"справочник: {MAP.relative_to(ROOT)} · {size // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
