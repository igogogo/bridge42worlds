#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Догнать переводы «Популярно» там, где русский подняли, а языки отстали.

Владелец 2026-08-24: «дотянуть там надо без промедления, сегодня».

ЧТО СЛУЧИЛОСЬ. Дотяжка уровня «Популярно» (tools/express_uplift.py) переписывает русский
текст: тот же материал, взрослее тон, термины с пояснением, больше механизма «как именно».
Партия 5 августа поднималась ДО того, как перевод пошёл тем же проходом, — русский стал
настоящим «Популярно», а четыре языка остались с прежним коротким текстом. Читатель на
арабском видел уровень, который от «Просто» почти не отличается, при снятом баннере.

ЗАМЕР 24.08: 496 статей с отставшими переводами (арабских 493, английских 133,
испанских 71, французских 34). Свежие партии — с 17 августа — переведены полностью:
дневной конвейер работает правильно, чинить надо только исторический хвост.

ПРИЗНАК ОТСТАВАНИЯ — ДЛИНА, и это осознанный выбор. Отметки об уплифте у переводов нет
вовсе (её никто не ставил), а поднятый русский заметно длиннее прежнего. Перевод короче
60% от русского — значит остался от старого уровня. Мера грубая, но проверяемая, в
отличие от догадки.

    python tools/uplift_retranslate.py --pilot 3       три статьи, показать
    python tools/uplift_retranslate.py --budget 3      дотянуть в пределах $3
"""
import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

LANGS = ("en", "es", "ar", "fr")
SHORT_RATIO = 0.6


def stale_articles():
    """Статьи, где русский поднят, а перевод короче порога."""
    out = []
    for path in sorted(glob.glob(str(ROOT / "lang/ru/archive/*/*/data.json"))):
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        pop = d.get("popular") or {}
        po = pop.get("ru") or {}
        if not po.get("uplifted"):
            continue
        ru = len(po.get("text", ""))
        if not ru:
            continue
        bad = [l for l in LANGS
               if len((pop.get(l) or {}).get("text", "")) < ru * SHORT_RATIO]
        if bad:
            out.append((path, bad))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0, help="сколько статей взять")
    ap.add_argument("--budget", type=float, default=4.0, help="потолок расхода, $")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    todo = stale_articles()
    print(f"статей с отставшими переводами: {len(todo)}")
    if args.pilot:
        todo = todo[:args.pilot]
        print(f"пилот: беру {len(todo)}")
    if args.dry or not todo:
        for path, bad in todo[:10]:
            print(f"  {Path(path).parent.name}: {', '.join(bad)}")
        return 0

    import budget_guard as bg
    from gen_llm import translate_scipop

    start = bg.spend()[1]
    ok = fail = 0
    for path, bad in todo:
        spent = bg.spend()[1] - start
        if spent >= args.budget:
            print(f"\nпотолок ${args.budget} выбран (${spent:.2f}) — остальное следующим прогоном")
            break
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        po = d["popular"]["ru"]
        got = []
        for tl in bad:
            try:
                tr = translate_scipop(po, tl)
                if tr and tr.get("text"):
                    d["popular"][tl] = tr
                    got.append(tl)
            except Exception as e:
                print(f"    {Path(path).parent.name} {tl}: {type(e).__name__}")
        if got:
            # Атомарности ради пишем целиком и сразу: прогон прерываемый, и статья
            # должна быть либо старой, либо новой, но не половинной.
            Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
            ok += 1
            print(f"  ok {Path(path).parent.name} · {'+'.join(got)}")
        else:
            fail += 1
    print(f"\nдотянуто статей: {ok}, без изменений: {fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
