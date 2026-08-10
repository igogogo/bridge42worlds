#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Блокирующая проверка предфильтра: не режет ли он профильные разделы.

ЗАЧЕМ. Первый вариант отбора работал ПРОТИВ профиля: астрофизика близка к нашему
корпусу (у нас её 824 статьи), поэтому «полнота» у неё низкая — и профильные кандидаты
вылетали. Нынешний вариант режет только края и по построению безопасен, но «по
построению» мы за неделю дважды принимали за проверку. Поэтому — замер на нескольких
днях, состав до и после.

ПОРОГ ПРИЁМКИ (условие архитектора): падение доли астро/физики больше чем на два
процентных пункта — стоп.

    python vector_select_check.py --dates 2026-07-01,2026-07-08,2026-07-15
"""
import json, pathlib, sys, argparse, collections
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from vector_select import load_env, day_candidates, score  # noqa: E402

# «Профильные» — то, о чём мы пишем по существу. Именно их нельзя терять.
CORE = ("astro-ph", "gr-qc", "hep-ph", "hep-th", "physics", "cond-mat",
        "quant-ph", "nucl-th", "nucl-ex", "hep-ex")


def share(rows, roots=CORE):
    if not rows:
        return 0.0
    n = sum(1 for r in rows if r["primary_category"].split(".")[0] in roots)
    return 100.0 * n / len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", required=True)
    a = ap.parse_args()
    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]

    print(f"{'день':<12} {'кандидатов':>11} {'после':>7} {'профиль до':>11} "
          f"{'после':>7} {'разница':>8}")
    deltas, total_before, total_after = [], [], []
    for date in [d.strip() for d in a.dates.split(",") if d.strip()]:
        try:
            cands = day_candidates(date)
        except SystemExit:
            print(f"{date:<12} нет в дампе")
            continue
        if len(cands) < 30:
            print(f"{date:<12} мало кандидатов ({len(cands)}), пропускаю")
            continue
        res, _ = score(cands, acc, tok)
        nears = sorted(r["near"] for r in res)
        p_dup = nears[int(0.95 * (len(nears) - 1))]
        p_off = nears[int(0.20 * (len(nears) - 1))]
        kept = [r for r in res if p_off <= r["near"] <= p_dup]
        s0, s1 = share(res), share(kept)
        deltas.append(s1 - s0)
        total_before += res
        total_after += kept
        print(f"{date:<12} {len(res):>11} {len(kept):>7} {s0:>10.1f}% "
              f"{s1:>6.1f}% {s1-s0:>+7.1f}")

    if not deltas:
        sys.exit("нечего считать")
    print(f"\nдней: {len(deltas)}")
    print(f"худший день: {min(deltas):+.1f} п.п.   средний: {sum(deltas)/len(deltas):+.1f} п.п.")
    print(f"по всем дням вместе: {share(total_before):.1f}% → {share(total_after):.1f}% "
          f"({share(total_after)-share(total_before):+.1f} п.п.)")
    verdict = "ПРОХОДИТ" if min(deltas) >= -2.0 else "СТОП — профиль просел"
    print(f"\nусловие «падение не больше 2 п.п. ни в один день»: {verdict}")

    # заодно: что именно вычёркивается, по разделам — чтобы видеть, кого теряем
    cut = collections.Counter()
    kept_ids = {id(r) for r in total_after}
    for r in total_before:
        if id(r) not in kept_ids:
            cut[r["primary_category"].split(".")[0]] += 1
    print("\nвычеркнуто по разделам, топ-8:")
    for k, v in cut.most_common(8):
        print(f"  {k:<12} {v:>5}")


if __name__ == "__main__":
    main()
