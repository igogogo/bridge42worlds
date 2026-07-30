#!/usr/bin/env python3
"""Ре-перевод статей, у которых в data.json лежит русский вместо перевода.

Причина завала (промпт-инженер, 2026-07-30): валидатор считал служебные поля браком,
три ретрая, затем молчаливый `return scipop` — весь догон 17–23 июля лёг по-русски
на en/es/ar (177 тиров на язык). Фикс валидатора уже в main — повтор проходит.

Переводит ТОЛЬКО тиры, где payload_in_source_lang: advanced полностью (pro, контракт,
глоссарий), popular/simple — слимом (flash) от переведённого advanced. Пишет data.json.
Страницы потом: run.py html --only <даты>.

Запуск: python tools/retranslate_days.py 2026-07-17 2026-07-18 ... [--dry]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generate as G  # noqa: E402
from gen_llm import translate_scipop, translate_scipop_slim  # noqa: E402

DRY = "--dry" in sys.argv
DATES = [a for a in sys.argv[1:] if not a.startswith("--")]
LANGS = [l for l in G.LANGUAGES if l != G.DEFAULT_LANG]
TIERS = ("advanced", "popular", "simple")

tot_fixed = tot_skip = tot_fail = 0
for date in DATES:
    day = Path(G.LANG_DIR) / G.DEFAULT_LANG / "archive" / date
    if not day.exists():
        print(f"{date}: папки нет"); continue
    for art in sorted(day.iterdir()):
        dj = art / "data.json"
        if not dj.exists():
            continue
        d = json.loads(dj.read_text(encoding="utf-8"))
        ru = {t: (d.get(t) or {}).get("ru") for t in TIERS}
        if not all(ru.values()):
            continue
        changed = False
        for lang in LANGS:
            cur_adv = (d.get("advanced") or {}).get(lang)
            need = [t for t in TIERS
                    if G.payload_in_source_lang((d.get(t) or {}).get(lang) or ru[t])]
            if not need:
                tot_skip += 1
                continue
            print(f"  {date}/{d.get('id')}: {lang} → {need}")
            if DRY:
                tot_fixed += len(need); continue
            adv_l = cur_adv if "advanced" not in need else \
                translate_scipop(ru["advanced"], lang)
            if G.payload_in_source_lang(adv_l):
                print(f"    ✗ advanced {lang} снова не прошёл — пропускаю статью")
                tot_fail += 1
                continue
            d["advanced"][lang] = adv_l
            for t in ("popular", "simple"):
                if t not in need:
                    continue
                res = translate_scipop_slim(ru[t], adv_l, lang) or \
                    translate_scipop(ru[t], lang)
                if not G.payload_in_source_lang(res):
                    d[t][lang] = res
                else:
                    tot_fail += 1
            changed = True
            tot_fixed += len(need)
        if changed and not DRY:
            dj.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\nитого: переведено тиров {tot_fixed}, пропущено (уже ок) {tot_skip}, "
      f"провалов {tot_fail}" + (" [dry]" if DRY else ""))
