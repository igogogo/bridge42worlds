"""Чинит аннотации, вышедшие не на своём языке (класс «молчаливый откат», 2026-07-31).

Аудит по корпусу: ru 24, en 33, ar 21, es 1, fr 1 — аннотация лежит на чужом языке.
Тексты самих статей при этом чистые (проверено тем же признаком), дефект только здесь.

Два разных лечения, потому что разные причины:
  • русская аннотация английская  → генерим заново из авторского абстракта (generate_abstract);
  • перевод на языке L русский/латиница → переводим заново из русской (translate_scipop).

Работа в два шага, чтобы не писать в дерево под идущей сборкой:
    python tools/abstract_lang_fix.py --scan            что сломано (бесплатно)
    python tools/abstract_lang_fix.py --run --out F.json  посчитать и СЛОЖИТЬ в файл (платно)
    python tools/abstract_lang_fix.py --apply F.json     разложить по data.json (быстро, офлайн)
"""
import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CYR = re.compile(r"[А-Яа-яЁё]")
ARA = re.compile(r"[؀-ۿ]")
ARCHIVE = Path("lang/ru/archive")


def wrong_lang(text, lang):
    """Признак чужого языка — тот же, что в аудите: доля алфавита в тексте."""
    if not text or len(text) < 40:
        return False
    if lang == "ru":
        return len(CYR.findall(text)) / len(text) < 0.15
    if lang == "ar":
        return len(ARA.findall(text)) / len(text) < 0.15
    return len(CYR.findall(text)) / len(text) > 0.30   # en/es/fr залиты русским


def scan(langs):
    """[(файл, id, язык)] — по регистру popular: он показательный и самый заметный."""
    out = []
    for f in ARCHIVE.glob("*/*/data.json"):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ab = j.get("abstract") or {}
        for l in langs:
            if wrong_lang((ab.get(l) or {}).get("popular", ""), l):
                out.append((f, j.get("id", f.parent.name), l))
    return out


def author_summary(folder):
    """Авторский абстракт из сохранённого atom.xml — источник для русской аннотации."""
    p = folder / "arxiv-atom.xml"
    if not p.exists():
        return ""
    m = re.search(r"<summary>(.*?)</summary>", p.read_text(encoding="utf-8"), re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--apply", metavar="FILE")
    ap.add_argument("--out", default="temp/abstract-fix.json")
    ap.add_argument("--langs", default="ru,en,es,ar,fr")
    args = ap.parse_args()
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]

    if args.apply:
        data = json.loads(Path(args.apply).read_text(encoding="utf-8"))
        n = 0
        for rec in data:
            f = Path(rec["file"])
            j = json.loads(f.read_text(encoding="utf-8"))
            j.setdefault("abstract", {})[rec["lang"]] = rec["abstract"]
            if rec["lang"] == "ru":
                j["abstract_v"] = rec.get("abstract_v", 2)
            f.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
            n += 1
        print(f"✅ разложено по data.json: {n}")
        return 0

    broken = scan(langs)
    by_lang = {}
    for _, _, l in broken:
        by_lang[l] = by_lang.get(l, 0) + 1
    print(f"сломанных аннотаций: {len(broken)} — {by_lang}")
    if args.scan or not args.run:
        return 0

    import generate  # тянет LLM-слой; при --scan не нужен
    done = []
    for i, (f, aid, lang) in enumerate(broken, 1):
        j = json.loads(f.read_text(encoding="utf-8"))
        try:
            if lang == "ru":
                s = author_summary(f.parent)
                if not s:
                    print(f"  ⏭️ {aid}: нет arxiv-atom.xml — русскую аннотацию не из чего сделать")
                    continue
                res = generate.generate_abstract(s)
            else:
                ru = (j.get("abstract") or {}).get("ru") or {}
                if not ru or wrong_lang(ru.get("popular", ""), "ru"):
                    print(f"  ⏭️ {aid}/{lang}: русская аннотация сама сломана — чиню её первым проходом")
                    continue
                res = generate.translate_scipop(ru, lang)
            if not res:
                print(f"  ⚠️ {aid}/{lang}: пусто")
                continue
            if wrong_lang((res or {}).get("popular", ""), lang):
                print(f"  ⚠️ {aid}/{lang}: снова не тот язык — пропускаю, не подменяю")
                continue
            done.append({"file": str(f), "id": aid, "lang": lang, "abstract": res,
                         "abstract_v": getattr(generate, "ABSTRACT_PROMPT_V", 2)})
            print(f"  ✅ {i}/{len(broken)} {aid}/{lang}")
        except Exception as e:
            print(f"  ❌ {aid}/{lang}: {e}")
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ посчитано {len(done)} → {out}. Разложить: --apply {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
