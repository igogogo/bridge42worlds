# -*- coding: utf-8 -*-
"""Русские названия новым понятиям — ради разметки текста и человеческих плашек.

Владелец 26.08: «если надо — сделай перевод, если он нужен для разметки по тексту;
хотя бы русский и английский пока». Английский есть у всех (родной язык реестра);
русского нет у ~696 новых — и без него:
  · разметка ТЕКСТА статей не находит понятие в русском тексте (X-rays в русском —
    «рентгеновские лучи», совпадения по-английски не будет);
  · плашки на русских страницах стоят английские.

Переводится ТОЛЬКО НАЗВАНИЕ (2-4 слова) — это словарь разметки. Полные записи
переводятся отдельным шагом со всеми языками, позже.

Смета: ~700 названий × ~30 токенов ≈ $0.02. Под замком и дешёвым окном не гоняем —
трата микроскопическая, а название нужно механике; но батчим по 40 за вызов.

    python tools/concept_names_translate.py --plan   посчитать
    python tools/concept_names_translate.py          перевести и влить
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "data" / "concepts-live.json"
# Язык перевода — параметр, а не константа: имена нужны и испанской, и арабской,
# и французской странице. Копилка своя на каждый язык, иначе они затрут друг друга.
LANG_NAME = {"ru": "Russian", "es": "Spanish", "ar": "Arabic", "fr": "French"}
TARGET = "ru"


def out_path():
    return ROOT / "data" / f"concept-names-{TARGET}.json"

sys.path.insert(0, str(ROOT))
from common import write_json_atomic  # noqa: E402
from tools.concept_harvest import env  # noqa: E402

PER_CALL = 40

SYS = """You translate physics concept names into Russian for a science website.

For each numbered item you get an id and its English name. Return a JSON array:
  {"n": <number>, "%LANG%": "<name in the target language, nominative case, lowercase unless a proper
                         noun; the standard Russian physics term, not a calque>"}

Examples: x_rays -> рентгеновские лучи; dark_matter -> тёмная материя;
quantum_squeezing -> квантовое сжатие; mean_free_path -> длина свободного пробега.
Output ONLY the JSON array."""


def targets():
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    done = json.loads(out_path().read_text(encoding="utf-8")) if out_path().exists() else {}
    todo = [(cid, (c.get("names") or {}).get("en") or cid.replace("_", " "))
            for cid, c in live["concepts"].items()
            if not (c.get("names") or {}).get(TARGET) and cid not in done]
    return todo, done, live


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--lang", default="ru", choices=sorted(LANG_NAME))
    a = ap.parse_args()
    global TARGET
    TARGET = a.lang
    todo, done, live = targets()
    print(f"[{TARGET}] без названия: {len(todo)} · уже переведено: {len(done)}")
    if a.plan:
        return 0
    try:
        from tools.freeze import guard
        guard("перевод названий понятий")
    except ImportError:
        pass
    key = env("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("нет DEEPSEEK_API_KEY")
    for s in range(0, len(todo), PER_CALL):
        batch = todo[s:s + PER_CALL]
        lines = [f"{i}. id={cid} en={en}" for i, (cid, en) in enumerate(batch, 1)]
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content":
                          SYS.replace("Russian", LANG_NAME.get(TARGET, TARGET))
                             .replace("%LANG%", TARGET)},
                         {"role": "user", "content": "\n".join(lines)}],
            "temperature": 0.2, "max_tokens": 2000,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            raw = d["choices"][0]["message"]["content"]
            m = re.search(r"\[.*\]", raw, re.S)
            for it in (json.loads(m.group(0)) if m else []):
                try:
                    n = int(it["n"])
                    ru = str(it.get(TARGET) or it.get("ru") or "").strip()
                    if 1 <= n <= len(batch) and ru:
                        done[batch[n - 1][0]] = ru
                except (KeyError, ValueError, TypeError):
                    continue
        except Exception as e:
            print(f"  сбой пачки {s}: {e}")
            time.sleep(4)
            continue
        out_path().write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  переведено {len(done)}")
    # влить в живой справочник — names.ru; страницы и словари возьмут при перегенерации
    for cid, ru in done.items():
        c = live["concepts"].get(cid)
        if c is not None:
            c.setdefault("names", {})[TARGET] = ru
    write_json_atomic(LIVE, live, indent=None)
    print(f"✅ русских названий: {len(done)}; влиты в concepts-live.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
