#!/usr/bin/env python3
"""Авторская работа проходит ТОТ ЖЕ конвейер, что статья с arXiv.

Владелец 2026-08-08: «ты сейчас передаёшь в промпт разобранный PDF, а тут надо убрать
данные и прочую чешую и передать так же в промпт… обычная статья плюс твоё мнение, и
всё, поехали».

До этого у работы был свой упрощённый пересказ (_our_take) и свой шаблон страницы —
и то, и другое пришлось бы поддерживать отдельно от остальных двух тысяч статей.
Теперь так: чистим текст работы от служебного, отдаём в article-generate-advanced —
ровно как текст PDF с arXiv, — дальше обычный каскад advanced → popular + simple,
обычный перевод на четыре языка, обычная сборка страницы.

Отличий от статьи ровно три, и все три — данные, а не отдельная вёрстка:
плашки авторской работы, ссылки на HTML/PDF/архив вместо arXiv, и наш разбор.

    python tools/submission_as_article.py b42p-2026-001
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def clean_text(root: Path, limit=120000) -> str:
    """Текст работы без чешуи: только содержательные тексты, без кода и данных.

    Автор присылает папку целиком — код обработки, csv с измерениями, конфиги. Всё это
    в промпт не идёт: модель должна читать работу, а не журнал прибора. Берём только
    .md и .txt из корня пакета, и вычищаем то, что в них тоже мусор для пересказа.
    """
    parts = []
    for f in sorted(root.glob("*.md")) + sorted(root.glob("*.txt")):
        if f.name.upper().startswith(("LICENSE", "SELF-REVIEW")):
            continue          # лицензия и заключение подготовки — не текст работы
        try:
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
    # index.html автора — основной текст; берём его содержимое без разметки, если .md мало
    idx = root / "index.html"
    if idx.exists() and sum(len(p) for p in parts) < 4000:
        raw = idx.read_text(encoding="utf-8", errors="replace")
        raw = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", raw, flags=re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
        parts.append(re.sub(r"\s+", " ", raw))
    text = "\n\n".join(parts)
    # Ссылки съедают токены и пересказу не нужны — тот же приём, что на статьях arXiv.
    text = re.sub(r"https?://\S+", "", text)
    # Длинные таблицы чисел: строка, где больше половины символов — цифры и разделители.
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if len(s) > 40 and sum(c.isdigit() or c in ".,;\t|-" for c in s) / len(s) > 0.6:
            continue
        keep.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep))[:limit]


def build(code: str):
    box = ROOT / "data" / "submissions" / code
    w = json.loads((box / "publish.json").read_text(encoding="utf-8"))

    un = box / "unpacked"
    root = un / code if (un / code).exists() else un
    text = clean_text(root)
    print(f"  📄 текст работы после чистки: {len(text) // 1000} тыс. знаков")

    import generate
    import gen_llm
    from generate import validate_tags, refine_simple, refine_popular

    # Статья в терминах генератора. Категорий arXiv у работы нет — облако тегов берём общее.
    a = {"id": code, "summary": (w.get("ours", {}).get("ru", {}) or {}).get("oneliner", ""),
         "primary_category": "", "categories": [], "title": w.get("title", "")}

    inputs = generate.prepare_inputs() if hasattr(generate, "prepare_inputs") else None
    if inputs is None:
        # Справочники для промпта — теми же файлами, что у обычной генерации.
        tags_input = json.loads((ROOT / "lang" / "ru" / "data" / "tags-list.json").read_text(encoding="utf-8"))
        sci = json.loads((ROOT / "lang" / "ru" / "data" / "scientists.json").read_text(encoding="utf-8"))
        laws = json.loads((ROOT / "lang" / "ru" / "data" / "laws.json").read_text(encoding="utf-8"))
        inputs = {"tags_input": tags_input, "scientists_keys": list(sci.keys()),
                  "law_ids": list(laws.keys()),
                  "valid_tags": {t.get("en") for t in tags_input if isinstance(t, dict)}}

    print("  🧠 advanced — тем же промптом, что статьи с arXiv")
    adv = gen_llm.generate_advanced(a, text, inputs["tags_input"],
                                    inputs["scientists_keys"], inputs.get("law_ids"))
    if not adv:
        print("  ❌ advanced не вышел")
        return None
    adv = validate_tags(adv, inputs["valid_tags"])

    print("  🧠 popular + simple — обычным каскадом")
    pop, simple = gen_llm.generate_combo(adv)
    pop = validate_tags(pop, inputs["valid_tags"]) if pop else adv
    simple = validate_tags(simple, inputs["valid_tags"]) if simple else adv
    simple = refine_simple(simple)
    pop = refine_popular(pop)

    out = {"advanced": {"ru": adv}, "popular": {"ru": pop}, "simple": {"ru": simple}}
    (box / "article-ru.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"  ✅ русская версия готова: {adv.get('title', '')[:60]}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("нужен код: python tools/submission_as_article.py b42p-2026-001")
        sys.exit(2)
    sys.exit(0 if build(sys.argv[1]) else 1)
