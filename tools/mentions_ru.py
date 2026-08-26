# -*- coding: utf-8 -*-
"""Русские якоря: где в русском тексте статьи названо каждое её понятие.

Владелец 26.08: «делай русские якоря тоже сразу ночью». Механизм — проба того же
вечера: модель получает РУССКИЙ текст и список понятий статьи и выписывает 1-3
ДОСЛОВНЫЕ подстроки на понятие — в том падеже, числе или парафразе, каким текст
живёт («пульсаров», «Тёмная материя, аннигилируя», «ГэВ»). Подстрока обязана
встречаться посимвольно: ссылка потом ставится точным поиском, без морфологии.

Пишет в тот же журнал, что и английские якоря добычи: data/concept-mentions.jsonl,
строки {art, concept, m[], lang: "ru"}. Проверка вхождения — на нашей стороне:
выдумка модели, которой нет в тексте, в журнал не попадает.

Идёт ПОСЛЕ переразметки (список понятий статьи — финальный, concepts_v2).

    python tools/mentions_ru.py --limit 20     проба
    python tools/mentions_ru.py                все статьи (ночь, ~$7)
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.concept_harvest import env, MENTIONS  # noqa: E402

STATE = ROOT / "data" / "mentions-ru-state.json"

SYS = """You anchor known concepts in a RUSSIAN popular-science text.
For each numbered concept find 1-3 EXACT substrings (character-for-character,
1-4 words) from the given Russian text where the concept is referred to — in
WHATEVER grammatical case, number or paraphrase the text uses. Each substring
must occur verbatim in the text. Empty list if the concept never surfaces in words.
Return a JSON array only: [{"n": 1, "m": ["...", "..."]}]"""


def state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"done": []}


def clean(text):
    return re.sub(r"\[(tag|law|scientist|callout)[^\]]*\]|\[/[a-z]+\]", "", text or "")


def articles():
    for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        v = (d.get("popular", {}) or {}).get("ru") or {}
        cs = [c for c in (v.get("concepts_v2") or []) if c]
        text = clean(v.get("text", ""))
        if cs and len(text) > 300:
            yield p.parent.name, cs[:20], text[:6000]


def ask_one(aid, concepts, text, key):
    user = ("CONCEPTS:\n" + "\n".join(f"{i}. {c}" for i, c in enumerate(concepts, 1))
            + "\n\nRUSSIAN TEXT:\n" + text)
    body = json.dumps({"model": "deepseek-chat",
                       "messages": [{"role": "system", "content": SYS},
                                    {"role": "user", "content": user}],
                       "temperature": 0.2, "max_tokens": 1200}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    m = re.search(r"\[.*\]", raw, re.S)
    rows = []
    for it in (json.loads(m.group(0)) if m else []):
        try:
            n = int(it["n"])
            # только дословные: чего нет в тексте — не якорь, а выдумка
            ms = [s for s in (it.get("m") or [])[:3]
                  if isinstance(s, str) and 2 < len(s) < 80 and s in text]
            if 1 <= n <= len(concepts) and ms:
                rows.append({"art": aid, "concept": concepts[n - 1], "m": ms, "lang": "ru"})
        except (KeyError, ValueError, TypeError):
            continue
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    try:
        from tools.freeze import guard
        guard("русские якоря (DeepSeek)")
    except ImportError:
        pass
    key = env("DEEPSEEK_API_KEY")
    st = state()
    done = set(st["done"])
    todo = [(aid, cs, tx) for aid, cs, tx in articles() if aid not in done]
    if a.limit:
        todo = todo[:a.limit]
    print(f"статей к якорению: {len(todo)}")
    n_rows = 0
    for n, (aid, cs, tx) in enumerate(todo, 1):
        try:
            rows = ask_one(aid, cs, tx, key)
        except Exception as e:
            print(f"  {aid}: {e}")
            time.sleep(4)
            continue
        if rows:
            with MENTIONS.open("a", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n_rows += len(rows)
        done.add(aid)
        if n % 50 == 0:
            st["done"] = sorted(done)
            STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
            print(f"  {n}/{len(todo)} · якорей {n_rows}")
    st["done"] = sorted(done)
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    print(f"✅ русских якорей: {n_rows}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
