#!/usr/bin/env python3
"""Ре-перевод статей, у которых в data.json лежит русский вместо перевода.

Причина завала (промпт-инженер, 2026-07-30): старый валидатор считал служебные поля
браком, три ретрая, затем молчаливый `return scipop` — догон 17–23 июля лёг по-русски
на en/es/ar. Фикс валидатора в main — повтор проходит.

Параллельный (8 потоков по статьям), возобновляемый: переводит ТОЛЬКО тиры, где
payload_in_source_lang. Advanced — полностью (pro, контракт), popular/simple — слимом
(flash) от переведённого advanced.

Запуск: python tools/retranslate_days.py 2026-07-17 ... [--dry]
"""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generate as G  # noqa: E402
from gen_llm import translate_scipop, translate_scipop_slim  # noqa: E402

DRY = "--dry" in sys.argv
DATES = [a for a in sys.argv[1:] if not a.startswith("--")]
LANGS = [l for l in G.LANGUAGES if l != G.DEFAULT_LANG]
TIERS = ("advanced", "popular", "simple")
_print_lock = threading.Lock()


def one_article(dj):
    """Одна статья целиком (все языки) — единица параллелизма."""
    d = json.loads(dj.read_text(encoding="utf-8"))
    ru = {t: (d.get(t) or {}).get("ru") for t in TIERS}
    if not all(ru.values()):
        return (0, 0, 0)
    fixed = skip = fail = 0
    changed = False
    for lang in LANGS:
        cur_adv = (d.get("advanced") or {}).get(lang)
        need = [t for t in TIERS
                if G.payload_in_source_lang((d.get(t) or {}).get(lang) or ru[t])]
        if not need:
            skip += 1
            continue
        if DRY:
            fixed += len(need)
            continue
        adv_l = cur_adv if "advanced" not in need else translate_scipop(ru["advanced"], lang)
        if G.payload_in_source_lang(adv_l):
            fail += 1
            continue
        d["advanced"][lang] = adv_l
        for t in ("popular", "simple"):
            if t not in need:
                continue
            res = translate_scipop_slim(ru[t], adv_l, lang) or translate_scipop(ru[t], lang)
            if not G.payload_in_source_lang(res):
                d[t][lang] = res
            else:
                fail += 1
        changed = True
        fixed += len(need)
    if changed and not DRY:
        dj.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        with _print_lock:
            print(f"  + {dj.parent.name}: тиров {fixed}, провалов {fail}", flush=True)
    return (fixed, skip, fail)


jobs = []
for date in DATES:
    day = Path(G.LANG_DIR) / G.DEFAULT_LANG / "archive" / date
    if not day.exists():
        print(f"{date}: папки нет")
        continue
    for art in sorted(day.iterdir()):
        dj = art / "data.json"
        if dj.exists():
            jobs.append(dj)

print(f"статей к проверке: {len(jobs)}")
tot = [0, 0, 0]
with ThreadPoolExecutor(max_workers=1 if DRY else 8) as ex:
    for r in ex.map(one_article, jobs):
        for i in range(3):
            tot[i] += r[i]

print(f"\nитого: переведено тиров {tot[0]}, пропущено (уже ок) {tot[1]}, "
      f"провалов {tot[2]}" + (" [dry]" if DRY else ""))
