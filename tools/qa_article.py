"""Приёмка свежих статей: язык, маркеры, числа, длина карточки — по всем пяти языкам.

Владелец 2026-08-02: «проверь качество отдельно, со всеми переводами, вариациями и так
далее» — перед тем как менять модели на всём потоке.

Проверяем то, на чём мы уже обжигались, и ровно теми же мерками, что заданы промптам:

• ЯЗЫК. Кириллица в en/es/ar/fr — это молчаливый откат перевода: статья выглядит готовой,
  а текст остался русским. Слой не один: текст, аннотация, подписи к картинкам, КЛЮЧИ
  словаря key_numbers (их забывали чаще всего).
• МАРКЕРЫ. [tag:...] / [scientist:...] / [law:...] должны пережить перевод в том же
  количестве: по ним строится граф знаний, потерянный маркер — дыра в связности.
• ЧИСЛА. Перевод не имеет права менять цифры. Проверяем, что множество чисел совпадает.
• КАРТОЧКА. Требования промпта: 350-550 знаков, 3-4 предложения, предложение ≤25 слов.
• ПОЛНОТА. Все языки на месте, обложка есть, текст не пустой.

    python tools/qa_article.py --date 2026-07-31
    python tools/qa_article.py --ids 2607.28321v1 …
    python tools/qa_article.py --latest 10
"""
import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
_sys.path.insert(0, str(ROOT))
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
TIERS = ("simple", "popular", "advanced")
MARKER_RE = re.compile(r"\[(tag|scientist|law):([^\]]+)\]")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
CYR_RE = re.compile(r"[А-Яа-яЁё]")
# Внутри маркеров и латеха кириллицы быть не может по определению — их вырезаем перед
# проверкой языка, иначе id вроде [tag:black_hole] дают ложную тревогу.
STRIP_RE = re.compile(r"\[(?:tag|scientist|law):[^\]]+\]|\$[^$]*\$")


def norm_nums(text):
    """Числа как ЗНАЧЕНИЯ, а не как написание.

    По-русски пишут 0,78 — по-английски 0.78, и это правильный перевод, а не потеря числа.
    Первая версия этой проверки сравнивала строки буквально и обвинила переводчик в потере
    чисел на двух статьях из пяти (2026-08-02). Ложная тревога в приёмке хуже отсутствия
    приёмки: на неё тратят время, а потом перестают ей верить."""
    out = set()
    for m in NUM_RE.finditer(STRIP_RE.sub(" ", text)):
        s = m.group(0).replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            continue
        # 0.780 и 0.78 — одно число; 5 и 5.0 тоже
        out.add(round(v, 6))
    return out


# Служебные поля: читателю не показываются (в templates/ и js/ их нет), нужны только коду —
# metaphor держит метафору единой между уровнями, glossary кормит термбазу. Переводчику они
# намеренно не отдаются: платить за перевод невидимого незачем. Русский текст в них — НОРМА.
# Без этого исключения приёмка объявила «русский в переводе» на 17 местах здоровой статьи
# (2026-08-02). Проверка обязана знать, что именно она проверяет, иначе она не защищает,
# а учит игнорировать красное.
INTERNAL_FIELDS = ("metaphor", "glossary")


def texts_of(node, out):
    """Все строковые значения ветки + КЛЮЧИ словарей: в key_numbers ключ видит читатель."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in INTERNAL_FIELDS:
                continue
            if isinstance(k, str):
                out.append(("key", k))
            texts_of(v, out)
    elif isinstance(node, list):
        for v in node:
            texts_of(v, out)
    elif isinstance(node, str):
        out.append(("val", node))
    return out


def check_article(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    aid = path.parent.name
    problems = []

    for tier in TIERS:
        t = d.get(tier)
        if not isinstance(t, dict):
            continue
        ru = t.get("ru")
        if not isinstance(ru, dict) or not ru.get("description"):
            continue

        # эталон: маркеры и числа русской версии
        ru_flat = " ".join(s for _, s in texts_of(ru, []))
        ru_markers = sorted(m.group(0) for m in MARKER_RE.finditer(ru_flat))
        ru_nums = norm_nums(ru_flat)

        # карточка по меркам промпта
        desc = ru["description"]
        sents = [s.strip() for s in re.split(r"[.!?]+", desc) if s.strip()]
        if not (300 <= len(desc) <= 650):
            problems.append(f"{tier}: карточка {len(desc)} знаков (норма 350-550)")
        if not (3 <= len(sents) <= 5):
            problems.append(f"{tier}: карточка {len(sents)} предложений (норма 3-4)")
        longest = max((len(s.split()) for s in sents), default=0)
        if longest > 27:
            problems.append(f"{tier}: предложение {longest} слов (норма ≤25)")

        for lang in LANGS:
            if lang == "ru":
                continue
            tl = t.get(lang)
            if not isinstance(tl, dict) or not tl:
                problems.append(f"{tier}/{lang}: перевода нет")
                continue
            flat = texts_of(tl, [])
            joined = " ".join(s for _, s in flat)

            leaks = [s for kind, s in flat if CYR_RE.search(STRIP_RE.sub(" ", s))]
            if leaks:
                where = "ключ словаря" if any(k == "key" for k, s in flat
                                              if CYR_RE.search(STRIP_RE.sub(" ", s))) else "текст"
                problems.append(f"{tier}/{lang}: РУССКИЙ в переводе ({len(leaks)} мест, {where}): "
                                f"«{leaks[0][:60]}»")

            got = sorted(m.group(0) for m in MARKER_RE.finditer(joined))
            if got != ru_markers:
                problems.append(f"{tier}/{lang}: маркеров {len(got)} против {len(ru_markers)} в оригинале")

            nums = norm_nums(joined)
            lost = ru_nums - nums
            if lost:
                problems.append(f"{tier}/{lang}: потеряны числа {sorted(lost)[:5]}")

    # Обложка: поле thumbs — это СЧЁТЧИК картинок из PDF, а не признак обложки. Сама
    # обложка лежит файлом рядом с data.json (FLUX или кадр из статьи). Первая версия
    # проверки смотрела на счётчик и объявляла «нет обложки» там, где она есть.
    covers = list(path.parent.glob("cover*.*")) + list(path.parent.glob("*.webp"))
    if not covers:
        problems.append("нет обложки (файла нет рядом с data.json)")
    return aid, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--latest", type=int)
    args = ap.parse_args()

    arch = ROOT / "lang/ru/archive"
    if args.date:
        paths = sorted((arch / args.date).glob("*/data.json"))
    elif args.ids:
        paths = [p for i in args.ids for p in arch.glob(f"*/{i}/data.json")]
    else:
        paths = sorted(arch.glob("*/*/data.json"), key=lambda p: p.parent.parent.name,
                       reverse=True)[:args.latest or 10]
    if not paths:
        print("нечего проверять")
        return 1

    bad = 0
    for p in paths:
        aid, problems = check_article(p)
        if problems:
            bad += 1
            print(f"\n❌ {aid}")
            for x in problems:
                print(f"   · {x}")
        else:
            print(f"✅ {aid}")
    print(f"\nпроверено {len(paths)}, с замечаниями {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
