#!/usr/bin/env python3
"""Реестр законов/принципов/теорем/эффектов для Bridge For Two Worlds.

Закон — сущность-зонтик (type: закон | принцип | теорема | эффект | уравнение).
«Законы для тегов — то же, что теги для статей»: каждый закон привязан к тегам-понятиям.
Формула — лишь отображение закона (генерится позже в law_describe.py), поэтому здесь
только имя + тип + связанные теги.

Количество/пачки — из config.json → "laws". Промт — data/prompts/law-list.txt.
Модель/температура/max_tokens — config.json → agents.laws_list. → lang/ru/data/laws-list.json
Генерится пачками параллельно, с дедупом и исключением уже собранных.
"""

import json, re, argparse
from pathlib import Path
from string import Template
from concurrent.futures import ThreadPoolExecutor

from common import CONFIG, chat, load_prompt, parse_json_salvage, sample_corpus, format_corpus_samples, focus_line

CFG = CONFIG.get("laws", {})
COUNT = CFG.get("count", 50)
LIST_BATCH = CFG.get("list_batch", 40)
WORKERS = CFG.get("workers", 5)
MAX_ROUNDS = CFG.get("max_rounds", 20)

LAWS_PATH = Path("lang/ru/data/laws-list.json")
ACTIVE_TAGS = Path("lang/ru/data/tags-list.json")
EDU_TAGS = Path("lang/ru/data/tags-list-educational.json")


def slugify(s):
    s = s.strip().lower()
    s = re.sub(r"[\s_]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def normalize_ids(laws, seen_ids):
    out = []
    for law in laws:
        slug = slugify(law.get("en", ""))
        if not slug:
            continue
        if slug in seen_ids:
            i = 2
            while f"{slug}_{i}" in seen_ids:
                i += 1
            slug = f"{slug}_{i}"
        seen_ids.add(slug)
        law["en"] = slug
        out.append(law)
    return out


def load_tag_ids():
    ids = []
    for p in (ACTIVE_TAGS, EDU_TAGS):
        if p.exists():
            ids += [t["en"] for t in json.loads(p.read_text(encoding="utf-8"))]
    return ids


def _norm(name):
    return (name or "").strip().lower()


def dedupe_tags_vs_laws(laws):
    """Закон и тег — разные сущности («закон = дом формул», тег = понятие). Иногда LLM всё же
    предлагает тег, который на деле закон/принцип/теорема/эффект (совпадает по имени с законом) —
    убираем такой тег, оставляя каноничную запись только среди законов. Аккуратно: сверка ТОЛЬКО
    по точному совпадению русского названия (без фаззи-логики, ничего лишнего не заденет)."""
    law_names = {_norm(l.get("ru", "")) for l in laws.values()} if isinstance(laws, dict) else {_norm(l.get("ru", "")) for l in laws}
    for p in (ACTIVE_TAGS, EDU_TAGS):
        if not p.exists():
            continue
        tags = json.loads(p.read_text(encoding="utf-8"))
        kept = [t for t in tags if _norm(t.get("ru", "")) not in law_names]
        removed = [t.get("ru", "") for t in tags if _norm(t.get("ru", "")) in law_names]
        if removed:
            p.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"   🧹 {p.name}: убрано {len(removed)} тег(ов)-дублей закона: {', '.join(removed)}")


def gen_batch(need, tag_ids, exclude):
    excl = ", ".join(sorted(exclude)[:300])
    excl_line = f"НЕ включай уже собранные: {excl}\n" if exclude else ""
    prompt = Template(load_prompt("law-list")).safe_substitute(
        need=need, tag_ids=", ".join(tag_ids), exclude_line=excl_line)
    try:
        r = chat("laws_list", prompt)
        return (parse_json_salvage(r.choices[0].message.content) or {}).get("laws", [])
    except Exception as e:
        print(f"    ⚠️ пачка законов: ошибка {e}")
        return []


def gen_important(need, focus=""):
    """Аналог gen_famous() у учёных: НЕ корпус-осведомлённая (без sample_corpus), а прямая
    проверка — каких фундаментальных общеизвестных законов/теорем не хватает для целостности,
    независимо от того, что реально попало в корпус статей."""
    tag_ids = load_tag_ids()
    if not tag_ids:
        print("❌ нет tags-list.json — сначала tag_list.py")
        exit(1)
    valid_tags = set(tag_ids)
    collected = {}
    if LAWS_PATH.exists():
        try:
            for law in json.loads(LAWS_PATH.read_text(encoding="utf-8")):
                collected[law["en"]] = law
        except json.JSONDecodeError:
            pass
    existing_names = ", ".join(sorted({l.get("ru", "") for l in collected.values() if l.get("ru")}))
    print(f"⚖️  Законы — добор фундаментальных/важных по {len(collected)} существующим: +{need}"
          + (f" (фокус: {focus})" if focus else ""))
    prompt = Template(load_prompt("law-list-important")).safe_substitute(
        existing_names=existing_names, need=need, tag_ids=", ".join(tag_ids), focus_line=focus_line(focus))
    r = chat("laws_list", prompt)
    new_laws = (parse_json_salvage(r.choices[0].message.content) or {}).get("laws", [])
    seen_ids = set(collected.keys())
    existing_ru = {l.get("ru", "").strip().lower() for l in collected.values()}
    added = []
    for law in normalize_ids(new_laws, seen_ids):
        if law.get("ru", "").strip().lower() in existing_ru:
            continue
        law["tags"] = [t for t in law.get("tags", []) if t in valid_tags]
        collected[law["en"]] = law
        added.append(law.get("ru", ""))
    LAWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAWS_PATH.write_text(json.dumps(list(collected.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ laws-list.json: +{len(added)} важных (всего {len(collected)}): {', '.join(added)}")
    dedupe_tags_vs_laws(collected)
    return collected


def gen_gaps(need, focus=""):
    """Итерация 2 ко-эволюции: пробел-осведомлённая догенерация — модель видит существующие
    законы + реальные статьи корпуса (теги + учёные) и предлагает то, что реально стоит за
    их содержанием, но ещё не представлено карточкой. Добавляет к списку, не переписывает.
    focus — разовый приоритет темы (см. common.focus_line)."""
    tag_ids = load_tag_ids()
    if not tag_ids:
        print("❌ нет tags-list.json — сначала tag_list.py")
        exit(1)
    valid_tags = set(tag_ids)
    collected = {}
    if LAWS_PATH.exists():
        try:
            for law in json.loads(LAWS_PATH.read_text(encoding="utf-8")):
                collected[law["en"]] = law
        except json.JSONDecodeError:
            pass
    existing_names = ", ".join(sorted({l.get("ru", "") for l in collected.values() if l.get("ru")}))
    samples = format_corpus_samples(sample_corpus(60))
    print(f"⚖️  Законы — пробел-анализ по {len(collected)} существующим + выборке статей: +{need}"
          + (f" (фокус: {focus})" if focus else ""))
    prompt = Template(load_prompt("law-list-gaps")).safe_substitute(
        existing_names=existing_names, corpus_samples=samples, need=need, tag_ids=", ".join(tag_ids),
        focus_line=focus_line(focus))
    r = chat("laws_list", prompt)
    new_laws = (parse_json_salvage(r.choices[0].message.content) or {}).get("laws", [])
    seen_ids = set(collected.keys())
    existing_ru = {l.get("ru", "").strip().lower() for l in collected.values()}
    added = 0
    for law in normalize_ids(new_laws, seen_ids):
        if law.get("ru", "").strip().lower() in existing_ru:
            continue
        law["tags"] = [t for t in law.get("tags", []) if t in valid_tags]
        collected[law["en"]] = law
        added += 1
    LAWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAWS_PATH.write_text(json.dumps(list(collected.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ laws-list.json: +{added} новых из пробел-анализа (всего {len(collected)})")
    dedupe_tags_vs_laws(collected)
    return collected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", type=int, metavar="N", help="пробел-осведомлённая догенерация +N законов (Итерация 2), вместо слепого топ-апа до count")
    ap.add_argument("--focus", default="", help="разовый приоритет темы для --gaps/--important (см. common.focus_line)")
    ap.add_argument("--important", type=int, metavar="N", help="добор +N фундаментальных/общеизвестных законов независимо от корпуса статей")
    args = ap.parse_args()
    if args.important:
        gen_important(args.important, focus=args.focus)
        return
    if args.gaps:
        gen_gaps(args.gaps, focus=args.focus)
        return

    tag_ids = load_tag_ids()
    if not tag_ids:
        print("❌ нет tags-list.json — сначала tag_list.py")
        exit(1)
    valid_tags = set(tag_ids)
    print(f"⚖️  Законы: цель {COUNT}, доступно тегов {len(tag_ids)}, пачки по {LIST_BATCH}, потоков {WORKERS}")

    collected = {}
    if LAWS_PATH.exists():
        try:
            for law in json.loads(LAWS_PATH.read_text(encoding="utf-8")):
                collected[law["en"]] = law
            print(f"   Продолжаем: уже есть {len(collected)}")
        except json.JSONDecodeError:
            pass
    seen_ids = set(collected.keys())
    exclude_names = {law.get("ru", "") for law in collected.values()}

    rounds = 0
    while len(collected) < COUNT and rounds < MAX_ROUNDS:
        rounds += 1
        remaining = COUNT - len(collected)
        n_batches = min(WORKERS, max(1, -(-remaining // LIST_BATCH)))
        per = min(LIST_BATCH, -(-remaining // n_batches))
        with ThreadPoolExecutor(max_workers=n_batches) as ex:
            results = list(ex.map(lambda _: gen_batch(per, tag_ids, exclude_names), range(n_batches)))
        added = 0
        for batch in results:
            for law in normalize_ids(batch, seen_ids):
                if law["en"] in collected:
                    continue
                law["tags"] = [t for t in law.get("tags", []) if t in valid_tags]
                collected[law["en"]] = law
                exclude_names.add(law.get("ru", ""))
                added += 1
        print(f"   Раунд {rounds}: +{added} (всего {len(collected)}/{COUNT})")
        LAWS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAWS_PATH.write_text(json.dumps(list(collected.values())[:COUNT], ensure_ascii=False, indent=2), encoding="utf-8")
        if added == 0:
            print("   Новых не приходит — останавливаюсь.")
            break

    types = {}
    for law in collected.values():
        types[law.get("type", "?")] = types.get(law.get("type", "?"), 0) + 1
    print(f"✅ laws-list.json: {len(collected)} законов · {', '.join(f'{k}={v}' for k, v in sorted(types.items()))}")

    dedupe_tags_vs_laws(collected)


if __name__ == "__main__":
    main()
