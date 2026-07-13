#!/usr/bin/env python3
"""Списки тегов для Bridge For Two Worlds.

Два яруса:
  • active      — теги для ГЕНЕРАЦИИ статей (идут в промт). → lang/ru/data/tags-list.json
  • educational — справочные физ/мат понятия ТОЛЬКО для облака/графа (обучающая карта),
                  в промт статей НЕ идут. → lang/ru/data/tags-list-educational.json

Количества и размеры пачек — из config.json → "tags". Промты — в data/prompts/.
Модель/температура/max_tokens — из config.json → "agents" (tags_list / tags_educational).
Образовательные генерируются пачками параллельно, с дедупом и исключением уже собранных.
Аргументы: --active-only / --educational-only (по умолчанию — оба).
"""

import json, re, argparse
from pathlib import Path
from string import Template
from concurrent.futures import ThreadPoolExecutor

from common import CONFIG, chat, load_prompt, parse_json_salvage, sample_corpus, format_corpus_samples, focus_line

CFG = CONFIG.get("tags", {})
ACTIVE_COUNT = CFG.get("active_count", 120)
EDU_COUNT = CFG.get("educational_count", 300)
LIST_BATCH = CFG.get("list_batch", 60)
WORKERS = CFG.get("workers", 5)
MAX_ROUNDS = CFG.get("max_rounds", 30)

ACTIVE_PATH = Path("lang/ru/data/tags-list.json")
EDU_PATH = Path("lang/ru/data/tags-list-educational.json")


def slugify(s):
    s = s.strip().lower()
    s = re.sub(r"[\s_]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def normalize_ids(tags, seen_ids):
    """ID тега — slug для URL/имён файлов. Нормализуем и разрешаем коллизии."""
    out = []
    for t in tags:
        slug = slugify(t.get("en", ""))
        if not slug:
            continue
        if slug in seen_ids:
            i = 2
            while f"{slug}_{i}" in seen_ids:
                i += 1
            slug = f"{slug}_{i}"
        seen_ids.add(slug)
        t["en"] = slug
        out.append(t)
    return out


def gen_active():
    print(f"🏷️  Активные теги (для статей): цель {ACTIVE_COUNT}")
    prompt = Template(load_prompt("tag-list-active")).safe_substitute(count=ACTIVE_COUNT)
    r = chat("tags_list", prompt)
    tags = (parse_json_salvage(r.choices[0].message.content) or {}).get("tags", [])
    tags = normalize_ids(tags, set())
    ACTIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PATH.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")
    types = {}
    for t in tags:
        types[t.get("type", "?")] = types.get(t.get("type", "?"), 0) + 1
    print(f"✅ tags-list.json: {len(tags)} активных · {', '.join(f'{k}={v}' for k, v in sorted(types.items()))}")
    return tags


def gen_active_gaps(need, focus=""):
    """Итерация 2 ко-эволюции: НЕ слепой список «ещё интересных тем», а пробел-осведомлённая
    догенерация — модель видит существующие теги + реальные статьи корпуса и предлагает то,
    чего конкретно не хватает для их точной категоризации. Добавляет к списку (не переписывает).
    focus — разовый приоритет темы (см. common.focus_line), напр. перед заливкой новой рубрики."""
    active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8")) if ACTIVE_PATH.exists() else []
    existing_names = ", ".join(sorted({t.get("ru", "") for t in active if t.get("ru")}))
    samples = format_corpus_samples(sample_corpus(60))
    print(f"🏷️  Активные теги — пробел-анализ по {len(active)} существующим + выборке статей: +{need}"
          + (f" (фокус: {focus})" if focus else ""))
    prompt = Template(load_prompt("tag-list-gaps")).safe_substitute(
        existing_names=existing_names, corpus_samples=samples, need=need, focus_line=focus_line(focus))
    r = chat("tags_list", prompt)
    new_tags = (parse_json_salvage(r.choices[0].message.content) or {}).get("tags", [])
    seen_ids = {t["en"] for t in active}
    existing_ru = {t.get("ru", "").strip().lower() for t in active}
    added = [t for t in normalize_ids(new_tags, seen_ids) if t.get("ru", "").strip().lower() not in existing_ru]
    active.extend(added)
    ACTIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PATH.write_text(json.dumps(active, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ tags-list.json: +{len(added)} новых из пробел-анализа (всего {len(active)}): "
          f"{', '.join(t['ru'] for t in added) or '(ничего не нашлось)'}")
    return active


def gen_edu_batch(need, exclude, focus=""):
    """Одна пачка образовательных тегов, исключая уже известные названия."""
    excl = ", ".join(sorted(exclude)[:400])
    excl_line = f"НЕ включай эти уже собранные понятия: {excl}\n" if exclude else ""
    prompt = Template(load_prompt("tag-list-educational")).safe_substitute(
        need=need, exclude_line=excl_line, focus_line=focus_line(focus))
    try:
        r = chat("tags_educational", prompt)
        return (parse_json_salvage(r.choices[0].message.content) or {}).get("tags", [])
    except Exception as e:
        print(f"    ⚠️ пачка образовательных: ошибка {e}")
        return []


def gen_educational(active_tags, focus="", need=None):
    """need=None — топ-ап до глобальной цели EDU_COUNT (обычный режим). need=N — точечный
    ограниченный топ-ап на +N (напр. для --gaps --educational-only --focus)."""
    target_desc = f"цель {EDU_COUNT}" if need is None else f"точечно +{need}"
    print(f"\n📚 Образовательные теги (только для облака/графа): {target_desc}" + (f" (фокус: {focus})" if focus else ""))
    collected = {}
    if EDU_PATH.exists():
        try:
            for t in json.loads(EDU_PATH.read_text(encoding="utf-8")):
                collected[t["en"]] = t
            print(f"   Продолжаем: уже есть {len(collected)}")
        except json.JSONDecodeError:
            pass
    target = len(collected) + need if need is not None else EDU_COUNT
    seen_ids = {t["en"] for t in active_tags} | set(collected.keys())
    exclude_names = {t.get("ru", "") for t in active_tags} | {t.get("ru", "") for t in collected.values()}

    rounds = 0
    while len(collected) < target and rounds < MAX_ROUNDS:
        rounds += 1
        remaining = target - len(collected)
        n_batches = min(WORKERS, max(1, -(-remaining // LIST_BATCH)))
        per = min(LIST_BATCH, -(-remaining // n_batches))
        with ThreadPoolExecutor(max_workers=n_batches) as ex:
            results = list(ex.map(lambda _: gen_edu_batch(per, exclude_names, focus), range(n_batches)))
        added = 0
        for batch in results:
            for t in normalize_ids(batch, seen_ids):
                if t["en"] in collected:
                    continue
                t["educational"] = True
                collected[t["en"]] = t
                exclude_names.add(t.get("ru", ""))
                added += 1
        print(f"   Раунд {rounds}: +{added} (всего {len(collected)}/{target})")
        EDU_PATH.write_text(json.dumps(list(collected.values())[:target], ensure_ascii=False, indent=2), encoding="utf-8")
        if added == 0:
            print("   Новых не приходит — останавливаюсь.")
            break
    print(f"✅ tags-list-educational.json: {len(collected)} образовательных")
    return list(collected.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--active-only", action="store_true")
    ap.add_argument("--educational-only", action="store_true")
    ap.add_argument("--gaps", type=int, metavar="N", help="пробел-осведомлённая догенерация +N тегов (Итерация 2); с --educational-only — точечный топ-ап +N (не до глобальной цели)")
    ap.add_argument("--focus", default="", help="разовый приоритет темы для --gaps, напр. 'quantum mechanics' (см. common.focus_line)")
    args = ap.parse_args()

    if args.gaps and args.educational_only:
        active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8")) if ACTIVE_PATH.exists() else []
        gen_educational(active, focus=args.focus, need=args.gaps)
    elif args.gaps:
        gen_active_gaps(args.gaps, focus=args.focus)
    elif args.educational_only:
        active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8")) if ACTIVE_PATH.exists() else []
        gen_educational(active)
    elif args.active_only:
        gen_active()
    else:
        active = gen_active()
        gen_educational(active)


if __name__ == "__main__":
    main()
