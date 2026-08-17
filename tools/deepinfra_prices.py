"""Прайс DeepInfra на наши модели — из их же API, а не из памяти.

Зачем инструмент. В budget_guard цены DeepInfra полгода стояли с пометкой «оценка
порядка»: точные числа полагалось «взять из счёта». Счёт показывает итог, а не тариф,
и сверка каждый раз откладывалась. У DeepInfra тариф отдаётся машинно
(`GET /models/list`, поле `pricing`), значит сверка — это команда, а не поход в кабинет.

Проверять стоит после каждого изменения прайса у них и перед разговором о бюджете:
цифра, которую никто не перепроверял три месяца, живёт в отчётах как факт.

    python tools/deepinfra_prices.py           # что стоят наши модели
    python tools/deepinfra_prices.py --check   # сверить с budget_guard, код 1 при расхождении
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
URL = "https://api.deepinfra.com/models/list"
# Как модель зовётся у них → как она записана в нашем журнале расхода.
OURS = {
    "Qwen/Qwen3-Reranker-8B": "qwen3-reranker-8b",
    "BAAI/bge-m3": "bge-m3",
}
IMAGES = ("black-forest-labs/FLUX-2-pro", "black-forest-labs/FLUX-1-schnell")


def fetch():
    key = os.environ.get("DEEPINFRA_API_KEY")
    if not key:
        raise SystemExit("нет DEEPINFRA_API_KEY")
    r = requests.get(URL, headers={"Authorization": f"Bearer {key}"}, timeout=60)
    r.raise_for_status()
    return {m.get("model_name"): m for m in r.json()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="сверить с budget_guard")
    a = ap.parse_args()
    models = fetch()

    live_tokens, live_images = {}, {}
    print("токенные модели (цена за миллион токенов):")
    for full, ours in OURS.items():
        m = models.get(full)
        if not m:
            print(f"  ⚠️  {full}: у DeepInfra такой модели больше нет")
            continue
        cents = (m.get("pricing") or {}).get("cents_per_input_token")
        if cents is None:
            print(f"  ⚠️  {full}: тариф не в токенах, смотреть отдельно")
            continue
        usd_per_m = cents * 1e6 / 100
        live_tokens[ours] = round(usd_per_m, 6)
        print(f"  {full:26} → {ours:20} ${usd_per_m:.4f}")

    print("\nкартинки (цена за изображение 1024×1024):")
    for full in IMAGES:
        m = models.get(full)
        if not m:
            print(f"  ⚠️  {full}: больше нет в прайсе")
            continue
        cents = (m.get("pricing") or {}).get("cents_per_image_unit")
        live_images[full] = round((cents or 0) / 100, 6)
        print(f"  {full:34} ${live_images[full]:.4f}")

    if not a.check:
        return 0

    sys.path.insert(0, str(ROOT / "tools"))
    import budget_guard
    bad = []
    for ours, usd in live_tokens.items():
        have = (budget_guard.OTHER_PRICES.get(ours) or {}).get("m")
        if have is None:
            bad.append(f"{ours}: у нас цены нет вовсе, у них ${usd:.4f}")
        elif abs(have - usd) > 1e-6:
            bad.append(f"{ours}: у нас ${have:.4f}, у них ${usd:.4f}")
    for full, usd in live_images.items():
        have = getattr(budget_guard, "IMAGE_PRICES_USD", {}).get(full)
        if have is None:
            bad.append(f"{full}: у нас цены нет вовсе, у них ${usd:.4f}")
        elif abs(have - usd) > 1e-6:
            bad.append(f"{full}: у нас ${have:.4f}, у них ${usd:.4f}")

    if bad:
        print("\n⚠️  РАСХОЖДЕНИЕ с budget_guard:")
        for b in bad:
            print("   ", b)
        print("   Правьте OTHER_PRICES / IMAGE_PRICES_USD в tools/budget_guard.py.")
        return 1
    print("\n✅ цены в budget_guard совпадают с прайсом DeepInfra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
