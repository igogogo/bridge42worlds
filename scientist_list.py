#!/usr/bin/env python3
"""Генерирует список учёных с привязкой к тегам → lang/ru/data/scientists.json.

Крутится РАУНДАМИ, пока не соберёт TOTAL уникальных: в каждом раунде WORKERS параллельных
запросов (каждому передаётся список уже собранных имён «не повторяй»), затем дедуп по id.
Промт — data/prompts/scientist-list.txt; модель — config.agents.scientists.
Возобновляемый: подхватывает scientists.json из прошлого запуска.
"""

import json, random, argparse
from pathlib import Path
from string import Template
from concurrent.futures import ThreadPoolExecutor

from common import CONFIG, chat, load_prompt, parse_json_salvage, as_list, sample_corpus, format_corpus_samples, focus_line

_SCFG = CONFIG.get("scientists", {})
TOTAL = _SCFG.get("total", 100)
PER_REQUEST = _SCFG.get("per_request", 5)
MAX_ROUNDS = _SCFG.get("max_requests", 80)
SAMPLE_TAGS = _SCFG.get("sample_tags", 20)
WORKERS = _SCFG.get("workers", 4)

TAGS_PATH = Path("lang/ru/data/tags-list.json")
LAWS_PATH = Path("lang/ru/data/laws-list.json")
OUT_PATH = Path("lang/ru/data/scientists.json")


def gen_one(need, all_en, laws_names, exclude_names):
    tags_str = ", ".join(random.sample(all_en, min(SAMPLE_TAGS, len(all_en))))
    laws_str = ", ".join(laws_names) if laws_names else "(законов пока нет)"
    exclusion = ("\n\nЭти учёные УЖЕ ЕСТЬ в списке — НЕ включай их снова: " + ", ".join(exclude_names)) if exclude_names else ""
    prompt = Template(load_prompt("scientist-list")).safe_substitute(
        need=need, tags_str=tags_str, laws_str=laws_str, exclusion=exclusion)
    try:
        r = chat("scientists", prompt)
        return (parse_json_salvage(r.choices[0].message.content) or {}).get("scientists", [])
    except Exception as e:
        print(f"  ⚠️ запрос учёных: ошибка {e}")
        return []


def gen_famous(need):
    """Промт роста (scientist-list.txt/gaps) намеренно уводит от Эйнштейна/Ньютона в сторону
    менее раскрученных фигур — из-за этого в базе может не хватать САМЫХ канонических имён.
    Отдельный проход без этого уклона: явно ищет пробелы среди общеизвестных учёных."""
    all_en = [t["en"] for t in json.loads(TAGS_PATH.read_text(encoding="utf-8"))]
    collected = {}
    if OUT_PATH.exists():
        try:
            for sid, s in json.loads(OUT_PATH.read_text(encoding="utf-8")).items():
                collected[sid] = {**s, "id": sid}
        except json.JSONDecodeError:
            pass
    exclude_names = ", ".join(sorted(collected.keys())) or "(пока никого нет)"
    tags_str = ", ".join(random.sample(all_en, min(SAMPLE_TAGS, len(all_en))))
    print(f"👨‍🔬 Учёные — добор общеизвестных (не менее раскрученных) по {len(collected)} существующим: +{need}")
    prompt = Template(load_prompt("scientist-list-famous")).safe_substitute(
        exclude_names=exclude_names, need=need, tags_str=tags_str)
    r = chat("scientists", prompt)
    new_sci = (parse_json_salvage(r.choices[0].message.content) or {}).get("scientists", [])
    added = 0
    for s in new_sci:
        sid = (s.get("id") or "").strip()
        if sid and sid not in collected:
            collected[sid] = s
            added += 1
    n_final = len(_save(collected))
    print(f"✅ scientists.json: +{added} общеизвестных (всего {n_final}): {', '.join(s.get('id','') for s in new_sci if s.get('id','').strip() and s['id'] in collected)}")
    return collected


def gen_gaps(need, focus=""):
    """Итерация 2 ко-эволюции: пробел-осведомлённая догенерация — модель видит существующих
    учёных + реальные статьи корпуса (теги + уже упомянутые в тексте учёные) и предлагает тех,
    кто реально стоит за содержанием этих статей, но ещё не представлен карточкой.
    focus — разовый приоритет темы (см. common.focus_line)."""
    all_en = [t["en"] for t in json.loads(TAGS_PATH.read_text(encoding="utf-8"))]
    collected = {}
    if OUT_PATH.exists():
        try:
            for sid, s in json.loads(OUT_PATH.read_text(encoding="utf-8")).items():
                collected[sid] = {**s, "id": sid}
        except json.JSONDecodeError:
            pass
    exclude_names = ", ".join(sorted(collected.keys())) or "(пока никого нет)"
    samples = format_corpus_samples(sample_corpus(60))
    tags_str = ", ".join(random.sample(all_en, min(SAMPLE_TAGS, len(all_en))))
    print(f"👨‍🔬 Учёные — пробел-анализ по {len(collected)} существующим + выборке статей: +{need}"
          + (f" (фокус: {focus})" if focus else ""))
    prompt = Template(load_prompt("scientist-list-gaps")).safe_substitute(
        exclude_names=exclude_names, corpus_samples=samples, need=need, tags_str=tags_str,
        focus_line=focus_line(focus))
    r = chat("scientists", prompt)
    new_sci = (parse_json_salvage(r.choices[0].message.content) or {}).get("scientists", [])
    added = 0
    for s in new_sci:
        sid = (s.get("id") or "").strip()
        if sid and sid not in collected:
            collected[sid] = s
            added += 1
    n_final = len(_save(collected))
    print(f"✅ scientists.json: +{added} новых из пробел-анализа (всего {n_final})")
    return collected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", type=int, metavar="N", help="пробел-осведомлённая догенерация +N учёных (Итерация 2), вместо слепого топ-апа до total")
    ap.add_argument("--focus", default="", help="разовый приоритет темы для --gaps (см. common.focus_line)")
    ap.add_argument("--famous", type=int, metavar="N", help="добор +N общеизвестных учёных (Эйнштейн/Ньютон и т.п.) без обычного уклона в сторону менее раскрученных")
    args = ap.parse_args()
    if args.famous:
        gen_famous(args.famous)
        return
    if args.gaps:
        gen_gaps(args.gaps, focus=args.focus)
        return

    if not TAGS_PATH.exists():
        print("❌ lang/ru/data/tags-list.json not found.")
        exit(1)
    all_en = [t["en"] for t in json.loads(TAGS_PATH.read_text(encoding="utf-8"))]
    laws_names = [l["ru"] for l in json.loads(LAWS_PATH.read_text(encoding="utf-8"))] if LAWS_PATH.exists() else []
    print(f"👨‍🔬 Учёные: цель {TOTAL}, за запрос {PER_REQUEST}, потоков {WORKERS}")

    collected = {}
    if OUT_PATH.exists():
        try:
            for sid, s in json.loads(OUT_PATH.read_text(encoding="utf-8")).items():
                collected[sid] = {**s, "id": sid}
            print(f"   Продолжаем: уже есть {len(collected)}")
        except json.JSONDecodeError:
            pass

    rounds = 0
    while len(collected) < TOTAL and rounds < MAX_ROUNDS:
        rounds += 1
        remaining = TOTAL - len(collected)
        n = min(WORKERS, max(1, -(-remaining // PER_REQUEST)))
        need = min(PER_REQUEST, -(-remaining // n))
        exclude = list(collected.keys())
        with ThreadPoolExecutor(max_workers=n) as ex:
            results = list(ex.map(lambda _: gen_one(need, all_en, laws_names, exclude), range(n)))
        added = 0
        for batch in results:
            for s in batch:
                sid = (s.get("id") or "").strip()
                if sid and sid not in collected:
                    collected[sid] = s
                    added += 1
        print(f"   Раунд {rounds}: +{added} (всего {len(collected)}/{TOTAL})")
        _save(collected)
        if added == 0:
            print("   Новых не приходит — останавливаюсь.")
            break

    n_final = len(_save(collected))
    print(f"✅ lang/ru/data/scientists.json: {n_final} учёных")


def _save(collected):
    # БЕЗ среза [:TOTAL] — раньше это молча отрубало учёных, добавленных сверх TOTAL
    # (напр. gen_gaps() растит НАМЕРЕННО сверх исходной цели; блинд-режим и так сам
    # останавливается по TOTAL в своём while-цикле, ему обрезка не нужна).
    out = {}
    for sid, s in collected.items():
        out[sid] = {
            "name": s.get("name", sid), "lifespan": s.get("lifespan", ""),
            "description": s.get("description", ""), "biography": s.get("biography", ""),
            "key_discoveries": as_list(s.get("key_discoveries", [])), "fields": as_list(s.get("fields", [])),
            "quote": s.get("quote", ""), "fun_fact": s.get("fun_fact", ""),
            "related_tags": s.get("related_tags", []),
        }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
