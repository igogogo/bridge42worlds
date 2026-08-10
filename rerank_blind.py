#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Слепая приёмка реранкера: теряет ли отбор в качестве, если резать кандидатов заранее.

Зачем отдельно от rerank_eval.py. Та мерка отвечает на вопрос «совпадает ли реранкер
с моделью» — и это НЕ вопрос о качестве. Модель выбирает двенадцать статей из ста;
если отдать ей пятьдесят, она всё равно выберет двенадцать, просто других. Совпадение
82% не означает, что восемнадцать процентов подборки испортились: оно означает ровно
то, что написано — восемнадцать процентов её прежних находок в укороченный список
не попали. Хуже подборка или нет — из этого числа не следует.

Поэтому здесь опыт: для одного дня берём выбор модели ИЗ ВСЕХ кандидатов (он уже
сохранён в temp/ДАТА/selection.json — доплачивать за него не надо) и выбор той же
модели из верхней половины реранкера. Обе подборки перемешиваются и печатаются
без пометок, какая откуда. Ключ пишется в отдельный файл и в глаза не попадает.

    python rerank_blind.py --days 4          провести опыт, напечатать вслепую
    python rerank_blind.py --key             показать ключ ПОСЛЕ того, как оценил

Так устроены все наши слепые проверки: смотреть на ответ до оценки — значит оценить
ответ, а не подборку.
"""
import argparse
import json
import os
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
KEYFILE = ROOT / "data" / ".blind-rerank-key.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))
import rerank_eval as ev


def pick_with_llm(cands, count, tag):
    """Тот же промт и тот же агент, что в ночном прогоне. Своего вкуса не заводим."""
    os.chdir(MAIN)                      # промты и config.json лежат в главной папке
    from common import chat, load_prompt
    from gen_llm import _cands_json, clean_json
    prompt = load_prompt("article-select").format(count=count, articles_json=_cands_json(cands))
    r = chat("select", prompt)
    raw = r.choices[0].message.content
    try:
        data = json.loads(clean_json(raw))
        items = data.get("articles", data if isinstance(data, list) else [])
        return [ev.base_id(x["id"]) for x in items if isinstance(x, dict) and x.get("id")]
    except Exception:
        print(f"  ⚠️ {tag}: ответ не разобран")
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=4)
    ap.add_argument("--model", default="8B", choices=list(ev.MODELS))
    ap.add_argument("--frac", type=float, default=0.5)
    ap.add_argument("--skip", type=int, default=0,
                    help="пропустить N последних дней — чтобы взять дни, которых ещё не видел")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--key", action="store_true", help="показать ключ прошлого опыта")
    args = ap.parse_args()

    if args.key:
        if not KEYFILE.exists():
            sys.exit("ключа нет — опыт не проводился")
        k = json.loads(KEYFILE.read_text(encoding="utf-8"))
        for day, v in k.items():
            print(f"\n{day}:  A = {v['A']}   B = {v['B']}")
            print(f"   только в A: {', '.join(v['only_a']) or '—'}")
            print(f"   только в B: {', '.join(v['only_b']) or '—'}")
        return 0

    key = ev.load_env()
    days = sorted(p.name for p in (MAIN / "temp").glob("20??-??-??") if p.is_dir())
    chosen_days, data, seen = [], {}, 0
    for d in reversed(days):
        r = ev.day_data(d)
        if not (r and len(r[1]) >= 5):  # день с одной находкой сравнивать не на чем
            continue
        seen += 1
        if seen <= args.skip:           # эти дни уже смотрел — глаз замылен, ключ известен
            continue
        data[d] = r
        chosen_days.append(d)
        if len(chosen_days) >= args.days:
            break
    if not chosen_days:
        sys.exit("нет подходящих дней")

    answer, out = {}, []
    rng = random.Random(args.seed)
    for d in chosen_days:
        cands, full_pick = data[d]
        sc = ev.score_day(cands, key, args.model, {})
        order = sorted(range(len(cands)), key=lambda i: -sc[i])
        keep = [cands[i] for i in order[:max(10, int(len(cands) * args.frac))]]
        print(f"{d}: {len(cands)} кандидатов → {len(keep)} после реранкера, "
              f"модель выбирала {len(full_pick)}")
        cut_pick = pick_with_llm(keep, len(full_pick), d)
        os.chdir(ROOT)
        meta = {c["id"]: c["title"] for c in cands}
        # Какая подборка получит букву A — решает монетка, а не порядок в коде.
        swap = rng.random() < 0.5
        a, b = (cut_pick, full_pick) if swap else (full_pick, cut_pick)
        answer[d] = {"A": "реранкер+модель" if swap else "модель по всем",
                     "B": "модель по всем" if swap else "реранкер+модель",
                     "only_a": sorted(set(a) - set(b)), "only_b": sorted(set(b) - set(a))}
        out.append((d, a, b, meta))

    KEYFILE.write_text(json.dumps(answer, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n" + "=" * 70)
    print("СЛЕПАЯ ВЫБОРКА. Какая подборка лучше — A или B? Ключ в --key, но ПОСЛЕ.")
    for d, a, b, meta in out:
        print(f"\n───── {d} ─────")
        for letter, lst in (("A", a), ("B", b)):
            print(f"  {letter}:")
            for i in lst:
                print(f"     · {meta.get(i, i)[:95]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
