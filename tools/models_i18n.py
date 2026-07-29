"""Достраивает словари стендов на недостающие языки (data/theory/<модель>.json → i18n).

Подписи ползунков, осей и сцены живут здесь. Русский и английский были, испанского и арабского
не было ни у одной из 17 моделей — на этих языках движок не находил перевода и показывал сырой
ключ (`xTime2`, `wheel`). То есть стенд, ради которого урок и затевался, был нечитаем.

Переводим с АНГЛИЙСКОГО (он полный и уже выверен), сверяясь с русским как подстраховкой.

    python tools/models_i18n.py --check      чего не хватает
    python tools/models_i18n.py --dry        перевести и показать
    python tools/models_i18n.py              записать
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import chat, clean_json, parse_json_salvage  # noqa: E402

ROOT = Path("data/theory")
LANG_NAME = {"es": "Spanish", "ar": "Arabic"}
SKIP = {"constants.json", "course-thermodynamics.json", "reference.json", "mathkit.json",
        "hypotheses.json", "discoveries.json", "frontier.json"}

PROMPT = """Translate this dictionary of labels for an interactive physics simulation into {lang}.

These strings sit on the simulation itself: slider captions, axis names, units, short notes.

Rules:
- Keep the SAME keys. Only values change.
- Keep it SHORT — these are captions under sliders and on axes, not sentences.
- Units must be the international symbols in {lang} usage: m, s, kg, J, N, W, V, A, K, Hz, mol,
  rad, eV, MeV. Never Cyrillic.
- Use the standard physics terminology of {lang}-language textbooks.
- Where the English value is a bare symbol or a number, leave it exactly as it is.

Return STRICT JSON with the same keys, nothing else.

INPUT:
{payload}"""


def files():
    out = []
    for f in sorted(ROOT.glob("*.json")):
        if f.name in SKIP:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d.get("i18n"), dict) and "ru" in d["i18n"]:
            out.append((f, d))
    return out


def translate(d18n, lang, retries=2):
    src = d18n.get("en") or d18n["ru"]
    for _ in range(retries):
        try:
            r = chat("translate",
                     PROMPT.format(lang=LANG_NAME[lang], payload=json.dumps(src, ensure_ascii=False)),
                     model="deepseek-v4-flash", max_tokens=16000)
            raw = r.choices[0].message.content or ""
            data = parse_json_salvage(raw) or json.loads(clean_json(raw))
            if isinstance(data, dict) and data:
                # берём только известные ключи, пропуски добиваем английским
                return {k: (data.get(k) if isinstance(data.get(k), str) and data.get(k).strip() else v)
                        for k, v in src.items()}
        except Exception as e:
            print(f"    ⚠️ {lang}: {e}")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="es,ar")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    langs = [l for l in args.langs.split(",") if l in LANG_NAME]

    todo = []
    for f, d in files():
        miss = [l for l in langs if l not in d["i18n"]]
        if miss:
            todo.append((f, d, miss))
    print(f"моделей без перевода: {len(todo)}")
    for f, d, miss in todo:
        print(f"  {f.name}: нет {', '.join(miss)} (ключей {len(d['i18n']['ru'])})")
    if args.check:
        return 0

    done = 0
    for f, d, miss in todo:
        for lang in miss:
            got = translate(d["i18n"], lang)
            if not got:
                print(f"  ✗ {f.name} [{lang}]")
                continue
            d["i18n"][lang] = got
            done += 1
            sample = list(got.items())[:3]
            print(f"  ✓ {f.name} [{lang}] " + "; ".join(f"{k}={v}" for k, v in sample))
        if not args.dry:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("ГОТОВО БЫ" if args.dry else "ЗАПИСАНО") + f": {done} словарей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
