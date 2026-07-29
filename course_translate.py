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


PROMPT = r"""Translate this physics-course material into {lang}. It is educational text for a
popular-science site, adult non-expert audience.

RULES — critical:
- Translate ONLY human-readable text (titles, explanations, examples, notes).
- Do NOT translate or alter: LaTeX/KaTeX commands and structure, symbols of quantities
  (E, F, q, Δt…), numbers, constant names/ids, JSON keys, and any technical identifiers.
- IMPORTANT — words INSIDE formulas: text written as \text{{…}} or \mathrm{{…}} is a human-readable
  label (a subscript such as \text{{ionisation}}, or a caption). Translate what is inside the
  braces, keep the command and the braces intact. Leaving a Russian word inside \text{{}} is a
  bug: the reader sees Cyrillic in an English/Spanish/Arabic formula.
  Units inside \text{{}} become the international symbols: м→m, с→s, кг→kg, Дж→J, Н→N, Вт→W,
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
    failed = []

    # ВАЖНО. Здесь стоял молчаливый откат: при сбое запроса в перевод писался РУССКИЙ оригинал
    # (`out.update(got if ... else batch)`). Выглядело безобидно, а на деле давало худший из
    # исходов: читатель на английском видел русский текст, а файл после этого навсегда считался
    # переведённым — блок больше никогда не пробовали перевести заново. Именно так по курсу
    # разошлась кириллица. Теперь при сбое НИЧЕГО не пишем: пропуск виден и будет повторён.
    def flush():
        nonlocal batch, size
        if not batch:
            return
        got = _one(batch, lang)
        if isinstance(got, dict):
            out.update(got)
        else:
            failed.extend(batch.keys())
        batch, size = {}, 0

    for k, v in block.items():
        s = len(json.dumps(v, ensure_ascii=False))
        if s > chunk_chars:          # крупный раздел — отдельным запросом
            flush()
            got = _one({k: v}, lang)
            if isinstance(got, dict) and k in got:
                out[k] = got[k]
            else:
                failed.append(k)
            continue
        if size + s > chunk_chars:
            flush()
        batch[k] = v
        size += s
    flush()
    if failed:
        print(f"    ⚠️ {lang}: не переведены {', '.join(sorted(set(failed)))} — оставлены пустыми,"
              f" повторный прогон возьмётся за них", flush=True)
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
        # Пропуск считаем ПО БЛОКАМ, а не по наличию языковой ветки. Раньше проверялось только
        # `lang not in d`: если перевод одного блока однажды сорвался, ветка оставалась неполной,
        # а файл навсегда считался переведённым. Так по курсу пропали `curiosities` у 27 уроков
        # и `synthesis` у 22 — читатель на en/es/ar не видел ни опытов на кухне, ни сквозного примера.
        missing = {}
        for l in langs:
            if l not in d:
                missing[l] = list(d["ru"].keys())
            else:
                gaps = [k for k in d["ru"] if k not in d[l]]
                if gaps:
                    missing[l] = gaps
        if missing:
            todo.append((f, missing))
    if limit:
        todo = todo[:limit]

    def part(ru, keys):
        return {k: ru[k] for k in keys if k in ru}

    chars = 0
    for f, m in todo:
        ru = json.loads(f.read_text(encoding="utf-8"))["ru"]
        for keys in m.values():
            chars += len(json.dumps(part(ru, keys), ensure_ascii=False))
    gaps = sum(len(v) for _, m in todo for v in m.values())
    print(f"материалов курса: {len(files)} | к переводу: {len(todo)} файлов, "
          f"{gaps} блоков, ~{chars/1000:.0f}k символов", flush=True)
    if "--check" in argv:
        for f, m in todo[:20]:
            for lang, keys in sorted(m.items()):
                print(f"  {f.parent.name}/{f.name} [{lang}]: {', '.join(keys[:6])}", flush=True)
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
        for lang, keys in missing.items():
            try:
                got = translate_block(part(d["ru"], keys), lang)
                if not got:
                    continue
                # Дополняем ветку, а не перезаписываем: уже переведённое трогать незачем.
                d.setdefault(lang, {})
                for k, v in got.items():
                    d[lang][k] = v
                made.append(f"{lang}:{len(got)}")
            except Exception as e:
                print(f"  ✗ {f.name} → {lang}: {str(e)[:80]}", flush=True)
        if made:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  ✔ {f.parent.name}/{f.name} → {', '.join(made)}", flush=True)
        return len(made)

    with ThreadPoolExecutor(max_workers=4) as ex:
        for got in ex.map(work, todo):
            done += got
    print(f"✅ переведено блоков: {done}", flush=True)


if __name__ == "__main__":
    main()
