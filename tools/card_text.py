"""Текст карточки: отдельный дешёвый вызов дорогой модели по одной аннотации.

Решение владельца 2026-08-02: «карточка — из аннотации, дорогой моделью, отдельным
вызовом; входных токенов мало, значит дорогая почти ничего не стоит, а это лицо сайта».

Почему отдельным вызовом, а не полем в общем промпте генерации: у карточки свои жёсткие
требования (3-4 предложения, ни одного термина без объяснения, никаких названий моделей),
и в общем промпте они тонут среди двух десятков других правил. Отдельный вызов стоит
доли цента — аннотация короткая.

    python tools/card_text.py --ids 2607.1234v1 …     переписать конкретные
    python tools/card_text.py --latest 15             свежие
    python tools/card_text.py --varied 15             по две из каждого домена
    python tools/card_text.py --all                   весь архив (спросит подтверждение)

Старый текст сохраняется в description_orig — чтобы можно было сравнить и откатить.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("simple", "popular", "advanced")

SPEC = """Ты пишешь ТЕКСТ КАРТОЧКИ для научно-популярного сайта — это витрина, по ней человек
за несколько секунд решает, читать ли статью. Читатель умный, любознательный, но БЕЗ научной
подготовки.

Жёсткие требования:
1. РОВНО 3-4 предложения, всего 350-550 знаков.
2. Каждое предложение не длиннее 25 слов. Короткая фраза сильнее длинной.
3. Первое предложение — живой образ или аналогия из обычной жизни, без единого термина.
4. НИ ОДНОГО научного термина без бытового объяснения рядом. Названия моделей, эффектов
   и уравнений НЕ УПОМИНАЙ ВООБЩЕ — читателю карточки они не говорят ничего.
5. Обязательно скажи: что сделали учёные, что оказалось неожиданным, зачем это нам.
6. Тон живой и честный. Без «сенсации», без штампа «представьте себе», без риторических
   вопросов, без «мы».

Пиши СТРОГО по-русски. Ответь ТОЛЬКО этим абзацем, без заголовка и кавычек.

Аннотация работы:
"""


def env():
    out = {}
    p = ROOT / ".env"
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def abstract_of(d):
    ab = d.get("abstract")
    if isinstance(ab, dict):
        ab = ab.get("en") or ab.get("ru")
    if isinstance(ab, dict):
        ab = ab.get("advanced") or ab.get("popular") or next(iter(ab.values()), "")
    return ab or ""


def ask(key, abstract, model="deepseek-v4-pro"):
    """Один вызов с ВЫКЛЮЧЕННЫМИ рассуждениями.

    Замер 2026-08-02 на одной карточке: с рассуждениями — $0.00711 и ПУСТОЙ ответ (все
    8000 токенов ушли в размышления, до текста дело не дошло); без них — $0.00035 и
    готовый текст за 6 секунд. Разница в 21 раз, качество не страдает: задача узкая,
    думать тут не над чем. У дорогой модели reasoning_effort='low' маппится в 'high' —
    экономного режима у неё нет, только выключать целиком."""
    r = requests.post("https://api.deepseek.com/chat/completions", timeout=300,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.75, "max_tokens": 8000,
                            "thinking": {"type": "disabled"},
                            "messages": [{"role": "user", "content": SPEC + abstract}]})
    j = r.json()
    ch = j["choices"][0]
    txt = (ch["message"].get("content") or "").strip()
    u = j.get("usage", {})
    return txt, ch.get("finish_reason"), u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def pick(args, idx):
    uniq = {}
    for a in idx:
        uniq.setdefault(a["id"], a)
    items = sorted(uniq.values(), key=lambda x: x["date"], reverse=True)
    if args.ids:
        return [a for a in items if a["id"] in set(args.ids)]
    if args.varied:
        by = {}
        for a in items:
            cat = (a.get("categories") or [""])[0]
            by.setdefault(cat.split(".")[0] or "?", []).append(a)
        out = []
        for dom in sorted(by, key=lambda d: -len(by[d])):
            out += by[dom][:2]
            if len(out) >= args.varied:
                break
        return out[:args.varied]
    if args.all:
        return items
    return items[:args.latest or 15]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--latest", type=int)
    ap.add_argument("--varied", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model", default="deepseek-v4-pro")
    args = ap.parse_args()

    key = env()["DEEPSEEK_API_KEY"]
    idx = json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8"))
    targets = pick(args, idx)
    print(f"к переписи: {len(targets)}")

    ok = skipped = 0
    si = so = 0
    for a in targets:
        hits = list((ROOT / "lang/ru/archive").glob(f"*/{a['id']}/data.json"))
        if not hits:
            print(f"⚠️ нет файла: {a['id']}"); skipped += 1; continue
        p = hits[0]
        d = json.loads(p.read_text(encoding="utf-8"))
        # Тиры, где описание вообще есть. У экспресс-статей полные уровни — заглушки,
        # писать в них нечего; двух статей архива поле нет вовсе (обломки генерации).
        live = [t for t in TIERS if isinstance(d.get(t, {}).get("ru"), dict)
                and d[t]["ru"].get("description")]
        if not live:
            print(f"⚠️ описания нет ни в одном уровне: {a['id']} — статью надо пересоздать")
            skipped += 1; continue
        ab = abstract_of(d)
        if not ab:
            print(f"⚠️ нет аннотации: {a['id']}"); skipped += 1; continue

        new = ""
        for attempt in range(3):
            try:
                new, fin, pi, po = ask(key, ab, args.model)
                si += pi; so += po
                if len(new) >= 120:
                    break
                print(f"   пусто (finish={fin}), попытка {attempt + 2}", flush=True)
            except Exception as e:
                print(f"   сбой {type(e).__name__}, попытка {attempt + 2}", flush=True)
                time.sleep(3)
        if len(new) < 120:
            print(f"❌ не получилось: {a['id']}"); skipped += 1; continue

        for t in live:
            d[t]["ru"].setdefault("description_orig", d[t]["ru"]["description"])
            d[t]["ru"]["description"] = new
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

        # Проверка ЧТЕНИЕМ, а не намерением: скрипт уже однажды рапортовал успехом,
        # ничего не записав (2026-08-02). Успех — это то, что лежит в файле.
        check = json.loads(p.read_text(encoding="utf-8"))
        if check[live[0]]["ru"]["description"] != new:
            print(f"❌ запись не подтвердилась: {a['id']}"); skipped += 1; continue
        ok += 1
        print(f"✅ {a['id']} [{(a.get('categories') or ['?'])[0]}] {len(new)} знаков", flush=True)

    cost = si * 0.435 / 1e6 + so * 0.87 / 1e6
    print(f"\nпереписано {ok}, пропущено {skipped} · токены {si}+{so} · ~${cost:.3f}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
