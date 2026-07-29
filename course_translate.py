"""Перевод обучающих материалов курса (data/theory/courses/**, data/theory/course*.json) на en/es/ar.

Специфика курса учтена: НЕ переводим формулы (KaTeX/LaTeX), обозначения величин, единицы, имена
констант и id — только человеческий текст. Структура как на остальном сайте: рядом с полем `ru`
появляются `en`/`es`/`ar` с той же схемой.

Идемпотентно: уже переведённые файлы/языки пропускаются, можно гонять повторно.

Запуск:
    python course_translate.py --check          # что и сколько осталось
    python course_translate.py --langs en       # только английский
    python course_translate.py                  # все три языка
    python course_translate.py --limit 5        # первые 5 файлов (проба)
"""
import json
import sys
from pathlib import Path

from common import chat, clean_json, parse_json_salvage

LANG_NAME = {"en": "English", "es": "Spanish", "ar": "Arabic"}
ROOTS = [Path("data/theory/courses"), Path("data/theory/lectures"), Path("data/theory")]


def targets():
    files, seen = [], set()
    for r in ROOTS:
        if not r.exists():
            continue
        # в папках курса и лекций переводим всё, в корне theory — только файлы курса
        it = r.rglob("*.json") if r.name in ("courses", "lectures") else (
                list(r.glob("course*.json")) + [r / "discoveries.json", r / "mathkit.json", r / "hypotheses.json"])
        for f in it:
            if f in seen:
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(d, dict) and isinstance(d.get("ru"), dict):
                seen.add(f)
                files.append(f)
    return sorted(files)


PROMPT = """Translate this physics-course material into {lang}. It is educational text for a
popular-science site, adult non-expert audience.

RULES — critical:
- Translate ONLY human-readable text (titles, explanations, examples, notes).
- Do NOT translate or alter: LaTeX/KaTeX commands and structure, symbols of quantities
  (E, F, q, Δt…), numbers, constant names/ids, JSON keys, and any technical identifiers.
- IMPORTANT — words INSIDE formulas: text written as \text{…} or \mathrm{…} is a human-readable
  label (a subscript such as \text{ionisation}, or a caption). Translate what is inside the
  braces, keep the command and the braces intact. Leaving a Russian word inside \text{} is a
  bug: the reader sees Cyrillic in an English/Spanish/Arabic formula.
  Units inside \text{} become the international symbols: м→m, с→s, кг→kg, Дж→J, Н→N, Вт→W,
  В→V, А→A, Кл→C, К→K, Гц→Hz, эВ→eV, МэВ→MeV, моль→mol.
- Names of laws and effects (fields like "law") ARE human-readable — translate them using the
  standard name in {lang} ("Закон Ома" → "Ohm's law").
- Keep the EXACT same JSON structure and keys; only values change.
- Keep the tone of the original: clear, engaging, no condescension, no jargon left unexplained.
- No alcohol analogies.
- Physics terminology must be the standard one used in {lang}-language textbooks.

Return STRICT JSON with the same shape as the input, nothing else.

INPUT:
{payload}"""


def _one(payload, lang, retries=2):
    for _ in range(retries):
        try:
            r = chat("translate", PROMPT.format(lang=LANG_NAME[lang], payload=json.dumps(payload, ensure_ascii=False)),
                     model="deepseek-v4-flash", max_tokens=32000)
            raw = r.choices[0].message.content or ""
            data = parse_json_salvage(raw)
            if data is None:
                data = json.loads(clean_json(raw))
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return None


def translate_block(block, lang, chunk_chars=6000):
    """Переводим ПО ЧАСТЯМ: урок целиком (40k+ символов) не помещается в ответ модели —
    ответ обрывался на середине JSON. Режем по ключам верхнего уровня, мелкие группируем."""
    out, batch, size = {}, {}, 0

    def flush():
        nonlocal batch, size
        if not batch:
            return
        got = _one(batch, lang)
        out.update(got if isinstance(got, dict) else batch)
        batch, size = {}, 0

    for k, v in block.items():
        s = len(json.dumps(v, ensure_ascii=False))
        if s > chunk_chars:          # крупный раздел — отдельным запросом
            flush()
            got = _one({k: v}, lang)
            out[k] = (got or {}).get(k, v)
            continue
        if size + s > chunk_chars:
            flush()
        batch[k] = v
        size += s
    flush()
    return out


def main():
    argv = sys.argv
    langs = ["en", "es", "ar"]
    if "--langs" in argv:
        langs = argv[argv.index("--langs") + 1].split(",")
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 0

    files = targets()
    todo = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        missing = [l for l in langs if l not in d]
        if missing:
            todo.append((f, missing))
    if limit:
        todo = todo[:limit]

    chars = sum(len(json.dumps(json.loads(f.read_text(encoding="utf-8"))["ru"], ensure_ascii=False)) * len(m)
                for f, m in todo)
    print(f"материалов курса: {len(files)} | к переводу: {len(todo)} файлов, ~{chars/1000:.0f}k символов", flush=True)
    if "--check" in argv or not todo:
        return

    # Параллельно по файлам: материалы объёмные, последовательный проход слишком долгий.
    # Внутри файла языки идём по очереди — чтобы не держать один и тот же файл открытым на запись.
    from concurrent.futures import ThreadPoolExecutor

    done = 0

    def work(item):
        f, missing = item
        d = json.loads(f.read_text(encoding="utf-8"))
        made = []
        for lang in missing:
            try:
                d[lang] = translate_block(d["ru"], lang)
                made.append(lang)
            except Exception as e:
                print(f"  ✗ {f.name} → {lang}: {str(e)[:80]}", flush=True)
        if made:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  ✔ {f.name} → {', '.join(made)}", flush=True)
        return len(made)

    with ThreadPoolExecutor(max_workers=4) as ex:
        for got in ex.map(work, todo):
            done += got
    print(f"✅ переведено блоков: {done}", flush=True)


if __name__ == "__main__":
    main()
