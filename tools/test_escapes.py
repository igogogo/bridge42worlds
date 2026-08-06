# -*- coding: utf-8 -*-
"""Проверка починки escape-последовательностей на случаях из живого журнала сбоев."""
import json
import sys

sys.path.insert(0, r"C:\Users\nadez\PycharmProjects\bridge42worlds")
from common import clean_json

CASES = [
    # (что прислала модель, что должно получиться после разбора)
    (r'{"t": "80\% вещества"}', "80\\% вещества"),
    (r'{"t": "формула \frac{a}{b} тут"}', "формула \\frac{a}{b} тут"),
    (r'{"t": "угол \theta и \nu"}', "угол \\theta и \\nu"),
    (r'{"t": "постоянная \upsilon растёт"}', "постоянная \\upsilon растёт"),
    (r'{"t": "уже экранировано \\alpha"}', "\\alpha"),          # частичное совпадение
    (r'{"t": "перенос\nстрока"}', "перенос\nстрока"),           # настоящий \n обязан выжить
    (r'{"t": "кавычка \" внутри"}', 'кавычка " внутри'),
    (r'{"t": "юникод \u0416 буква"}', "юникод Ж буква"),
    (r'{"t": "\beta-распад и \times"}', "\\beta-распад и \\times"),
]

ok = bad = 0
for raw, expect in CASES:
    try:
        got = json.loads(clean_json(raw))["t"]
    except Exception as e:
        print(f"  ПАДЕНИЕ  {raw[:45]:47} → {type(e).__name__}: {e}")
        bad += 1
        continue
    if expect in got:
        print(f"  ок       {raw[:45]:47} → {got[:40]!r}")
        ok += 1
    else:
        print(f"  НЕ ТО    {raw[:45]:47} → {got[:40]!r} (ждали {expect[:30]!r})")
        bad += 1

print(f"\nпройдено {ok}, провалено {bad}")
sys.exit(1 if bad else 0)
