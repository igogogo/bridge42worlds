"""Догнать язык до полного корпуса: перевести все статьи, которых на нём ещё нет.

Решение владельца 2026-08-01: французский раздел выглядит недоделанным (133 статьи
из 2110 — 6%), и никакая кнопка «перевести по требованию» этого не лечит: читатель
видит лоскутное одеяло. Догоняем язык целиком, и ПОСЛЕ этого кнопку по требованию
убираем — она останется только как ремонт молчаливых сбоев перевода.

    python tools/lang_backfill.py --lang fr --dry        сколько статей и почём (бесплатно)
    python tools/lang_backfill.py --lang fr --limit 50   перевести 50 (проба)
    python tools/lang_backfill.py --lang fr              перевести все недостающие

Идёт по одной статье через generate.translate_article_lang (возобновляемо: то, что уже
переведено, пропускается), после каждой N статей печатает расход. Прерывать можно —
повторный запуск продолжит с того же места.

Цена (замер 2026-08-01): дешёвой моделью ~$0.019 на статью на язык, весь французский
(1977 статей) ≈ $37. Дорогой моделью вчетверо дороже — поэтому здесь используется
конфиг как есть: если владелец переключил перевод на дешёвую модель, догон дешевеет сам.
"""
import argparse
import json
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PER_ARTICLE_USD = 0.019      # дешёвая модель, замер по журналу вызовов


def missing(lang):
    """Статьи, у которых нет перевода на язык. Смотрим data.json — источник правды,
    а не собранные страницы: страница может существовать заглушкой."""
    import generate
    out = []
    for f in sorted((ROOT / "lang" / generate.DEFAULT_LANG / "archive").glob("*/*/data.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        tr = (d.get("simple") or {}).get(lang) or (d.get("popular") or {}).get(lang)
        if not tr or tr.get("untranslated") or not tr.get("title"):
            out.append((d.get("id") or f.parent.name, f.parent.parent.name))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry", action="store_true", help="только посчитать, ничего не тратить")
    args = ap.parse_args()

    todo = missing(args.lang)
    print(f"нет перевода на «{args.lang}»: {len(todo)} статей · ориентировочно "
          f"${len(todo) * PER_ARTICLE_USD:.0f}")
    if args.dry:
        for aid, day in todo[:10]:
            print(f"   {day} {aid}")
        if len(todo) > 10:
            print(f"   … и ещё {len(todo) - 10}")
        return 0

    if args.limit:
        todo = todo[:args.limit]
    import generate
    ok = fail = 0
    t0 = time.time()
    for i, (aid, _day) in enumerate(todo, 1):
        try:
            if generate.translate_article_lang(aid, args.lang):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"  ❌ {aid}: {type(e).__name__} {e}")
        if i % 25 == 0 or i == len(todo):
            el = time.time() - t0
            print(f"  … {i}/{len(todo)} · переведено {ok}, сбоев {fail} · "
                  f"{el/60:.1f} мин · ≈${i * PER_ARTICLE_USD:.2f}", flush=True)
    print(f"\n✅ готово: {ok} переведено, {fail} сбоев. "
          f"Дальше — пересборка (страницы соберутся с новым языком).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
