"""Раскладывает список лекций в языковые ветки data/theory/lectures/index.json.

Зачем. learn.html берёт список из ветки языка (`lx[LANG].lectures`) и откатывается на общий
`lx.lectures`, который существует только по-русски. Веток с лекциями не было — читатель на
en/es/ar видел русские названия в дереве знаний. Переводы при этом уже лежали в самих файлах
лекций, переводить заново нечего: собираем ветки из них.

Запускать после добавления или переименования лекции:
    python tools/theory_index_i18n.py
"""
import json
from pathlib import Path

LANGS = ["ru", "en", "es", "ar"]
DIR = Path("data/theory/lectures")


def main():
    idx_path = DIR / "index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))

    for lang in LANGS:
        out = []
        for item in idx["lectures"]:
            f = DIR / f"{item['id']}.json"
            src = json.loads(f.read_text(encoding="utf-8")).get(lang) if f.exists() else None
            if not src or not src.get("title"):
                out.append(dict(item))
                print(f"  ⚠️ {item['id']} [{lang}]: перевода нет, оставлен русский")
                continue
            # В файле лекции подзаголовок идёт с префиксом «Лекция N · », в дереве он лишний.
            sub = src.get("subtitle") or item["sub"]
            if " · " in sub:
                sub = sub.split(" · ", 1)[1]
            out.append({"id": item["id"], "title": src["title"], "sub": sub})
        idx.setdefault(lang, {})["lectures"] = out

    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"лекций: {len(idx['lectures'])} × {len(LANGS)} языка → {idx_path}")


if __name__ == "__main__":
    main()
