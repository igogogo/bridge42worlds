#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ужесточение отбора кандидатов после первого прохода по дампу.

ГРАБЛЯ, из-за которой понадобился этот шаг (2026-08-04). Первый отбор дал 602 109
кандидатов — 19% всего arXiv. Причина: слово `imu` искалось без границ слова и совпало
571 091 раз, потому что это подстрока в maximum, simulation, optimum, stimulus. Одно
слово дало 95% мусора.

Отсюда правило на будущее: **короткие токены ищем только с `\\b`**. И проверять надо
не «сколько нашлось», а «сколько нашлось на каждое слово» — суммарное число выглядело
правдоподобно и ничего бы не сказало.

Второе, менее очевидное: `quantization` в физике означает квантование поля, а не оцифровку
сигнала. 25 737 совпадений — это квантовая теория поля, а не АЦП. Такие слова годятся
только в паре с «железным» словом.

Перефильтровывает уже собранный надмножество-файл, дамп заново не читает.
"""
import json, re, pathlib, collections

W = pathlib.Path(__file__).resolve().parent / "data"

# Достаточно одного попадания: слова, которые вне нашей темы почти не встречаются.
SPECIFIC = [r"\baccelerometer", r"\bMEMS\b", r"\bLIS3DSH\b", r"\bADXL\d*", r"\bMPU-?6050\b",
            r"\bBMI160\b", r"\bESP32\b", r"\bI2C\b", r"\bI²C\b", r"\bSPI bus\b",
            r"\bstuck[- ]at\b", r"\bstuck bit\b", r"\bbyte error\b",
            r"\bsensor artifact", r"\bsensor artefact", r"\bsensor fault",
            r"\binertial sensor", r"\binertial measurement unit", r"\bIMU\b",
            r"\breadout noise", r"\blow-cost sensor", r"\bembedded sensor",
            r"\bsensor readout"]

# Эти по отдельности бессмысленны (квантование поля, центробежная сила в небесной
# механике), но в паре с «железным» словом — уже про нашу тему.
AMBIG = [r"\bquantiz", r"\bquantis", r"\bADC\b", r"\banalog[ue]?-to-digital",
         r"\bbit error", r"\bcentrifugal", r"\bmicrocontroller", r"\bvibration"]
HARDWARE = [r"\bsensor", r"\baccelerometer", r"\bgyroscope", r"\bMEMS\b", r"\bdigitiz",
            r"\bdigitis", r"\bfirmware", r"\bmicrocontroller", r"\bembedded\b",
            r"\bdata acquisition", r"\breadout"]

spec = re.compile("|".join(SPECIFIC), re.I)
amb = re.compile("|".join(AMBIG), re.I)
hw = re.compile("|".join(HARDWARE), re.I)

src = W / "blindspot-candidates.jsonl"
rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"было кандидатов: {len(rows):,}")

kept, why = [], collections.Counter()
for r in rows:
    t = f"{r['title']} {r['abstract']}"
    if spec.search(t):
        kept.append(r); why["точное слово"] += 1
    elif amb.search(t) and hw.search(t):
        kept.append(r); why["двусмысленное + железо"] += 1

out = W / "blindspot-candidates2.jsonl"
out.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in kept), encoding="utf-8")
print(f"осталось: {len(kept):,}  ({100*len(kept)/len(rows):.1f}% от прежнего)")
for k, v in why.most_common():
    print(f"  {k}: {v:,}")
print(f"файл: {out}")
