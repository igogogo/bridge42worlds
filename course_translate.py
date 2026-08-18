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
import re
import sys
from pathlib import Path

from common import chat, clean_json, parse_json_salvage

LANG_NAME = {"en": "English", "es": "Spanish", "ar": "Arabic", "fr": "French"}
CYR = re.compile(r"[А-Яа-яЁё]")
ROOTS = [Path("data/theory/courses"), Path("data/theory/lectures"), Path("data/theory")]


def shape_broken(ru, tr):
    """Правда ли перевод потерял форму оригинала.

    Третий вид пробела, который не ловили ни «нет ключа», ни «есть кириллица»: ключ на месте,
    кириллицы нет, а внутри пусто или список короче русского. Так бывает после пересборки русской
    ветки — в путеводитель добавили законы, в тему параграф, — и на английской странице темы
    оставался один параграф из трёх при полностью зелёной проверке. Разбор и починка россыпью:
    tools/translation_holes.py.
    """
    if isinstance(ru, dict):
        if not isinstance(tr, dict):
            return True
        return any(k not in tr or shape_broken(v, tr[k]) for k, v in ru.items())
    if isinstance(ru, list):
        if not isinstance(tr, list) or len(tr) < len(ru):
            return True
        return any(shape_broken(a, b) for a, b in zip(ru, tr))
    if isinstance(ru, str):
        return bool(ru.strip()) and isinstance(tr, str) and not tr.strip()
    return False


def branches(d):
    """Наборы языковых веток в файле.

    Обычно ветки лежат на верхнем уровне: рядом с id и schema стоят ru/en/es/ar. Но у
    интерактивного учебника (course-thermodynamics.json) их два и оба внутри полей: `ui` и
    `course`. Такой файл переводчик просто не видел — искал `d["ru"]`, не находил и молча
    проходил мимо. Из-за этого учебник остался единственным материалом курса без перевода,
    а страница на en/es/ar падала с TypeError вместо содержания.
    """
    if isinstance(d.get("ru"), dict):
        return {"": d}
    return {k: v for k, v in d.items() if isinstance(v, dict) and isinstance(v.get("ru"), dict)}


def targets():
    files, seen = [], set()
    for r in ROOTS:
        if not r.exists():
            continue
        # В папках курса и лекций переводим всё; в корне theory — тоже всё, что имеет языковые
        # ветки. Раньше здесь стоял поимённый список, и материал, не попавший в него, оставался
        # русским на всех языках навсегда: так `frontier.json` (край известного, 15 тысяч знаков)
        # читался по-русски на en/es/ar. Отбор по содержимому, а не по имени файла: новый
        # материал подхватывается сам.
        it = r.rglob("*.json") if r.name in ("courses", "lectures") else r.glob("*.json")
        for f in it:
            if f in seen:
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(d, dict) and branches(d):
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
- IMPORTANT — Cyrillic SUBSCRIPTS and units written plainly, without \text{{}}: things like
  N_удар, Δp_полн, L_мол, V_пар, T_гор, 67 кДж. They are human-readable too and must not stay
  in Cyrillic: translate the subscript (L_мол → L_mol, T_гор → T_hot) and convert the unit
  (кДж → kJ, кПа → kPa, °С → °C). Keep the symbol itself and the underscore.
- Names of laws and effects (fields like "law") ARE human-readable — translate them using the
  standard name in {lang} ("Закон Ома" → "Ohm's law").
- Keep the EXACT same JSON structure and keys; only values change.
- Keep the tone of the original: clear, engaging, no condescension, no jargon left unexplained.
- No alcohol analogies.
- Physics terminology must be the standard one used in {lang}-language textbooks.

Return STRICT JSON with the same shape as the input, nothing else.

INPUT:
{payload}"""


def _one(payload, lang, retries=2, prompt=None):
    for _ in range(retries):
        try:
            r = chat("translate", (prompt or PROMPT).format(lang=LANG_NAME[lang], payload=json.dumps(payload, ensure_ascii=False)),
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


def _big(v, lang, limit):
    """Крупный кусок режем по составу: список — по элементам, словарь — по ключам.

    Раньше «слишком большое» уходило одним запросом, и если оно не помещалось в ответ, ответ
    обрывался на середине JSON — блок терялся целиком. У учебника три главы по десять тысяч
    знаков, каждая заведомо больше предела, поэтому без деления перевести его нельзя.
    """
    if isinstance(v, (list, dict)):
        items = enumerate(v) if isinstance(v, list) else v.items()
        out = [] if isinstance(v, list) else {}
        for k, x in items:
            if isinstance(x, (list, dict)) and len(json.dumps(x, ensure_ascii=False)) > limit:
                got = _big(x, lang, limit)
            else:
                key = "v" if isinstance(v, list) else k
                g = _one({key: x}, lang)
                got = g.get(key) if isinstance(g, dict) else None
            if got is None:
                return None
            if isinstance(v, list):
                out.append(got)
            else:
                out[k] = got
        return out
    g = _one({"v": v}, lang)
    return g.get("v") if isinstance(g, dict) else None


def graft(orig, got):
    """Сшиваем перевод с оригиналом по форме оригинала.

    Модель переводит текст, но заодно может переставить ключи, потерять элемент списка или
    «перевести» служебное значение. В тесте это стоит правильного ответа: `answer` — номер
    варианта, и сдвиг на единицу делает вопрос неверным молча. Поэтому из перевода берём
    только строки, а числа, флаги, идентификаторы и длину списков сохраняем исходные.
    """
    if isinstance(orig, dict):
        if not isinstance(got, dict):
            return orig
        return {k: (orig[k] if k in ("id", "model", "type", "href", "icon") else graft(v, got.get(k)))
                for k, v in orig.items()}
    if isinstance(orig, list):
        if not isinstance(got, list) or len(got) != len(orig):
            return orig
        return [graft(a, b) for a, b in zip(orig, got)]
    if isinstance(orig, str):
        return got if isinstance(got, str) and got.strip() else orig
    return orig          # числа и флаги остаются как есть


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
            # Ключ, которого в ответе нет, — это НЕ повод положить русский оригинал. Такой
            # откат уже стоил нам утечки: перевод «есть», а читатель видит кириллицу. Здесь он
            # оставался в последнем виде — через graft. Модель молча теряла по нескольку полей
            # (`constants`, `mnemonic` в строгом выводе), и они уезжали в перевод по-русски.
            for k, v in batch.items():
                if k in got and got[k] is not None:
                    out[k] = graft(v, got[k])
                else:
                    failed.append(k)
        else:
            failed.extend(batch.keys())
        batch, size = {}, 0

    for k, v in block.items():
        s = len(json.dumps(v, ensure_ascii=False))
        if s > chunk_chars:          # крупный раздел — отдельным запросом, при нужде по частям
            flush()
            # совсем крупное (главы учебника — по десять тысяч знаков) сразу делим по составу:
            # одним запросом такое не возвращается, попытка только тратит время
            got = None if s > 3 * chunk_chars else _one({k: v}, lang)
            got = got[k] if isinstance(got, dict) and k in got else _big(v, lang, chunk_chars)
            if got is None:
                failed.append(k)
            else:
                out[k] = graft(v, got)
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


FILL_PROMPT = r"""Translate these strings from a physics course into {lang}. Each key holds one
string; return STRICT JSON with the SAME keys and translated values, nothing else.

RULES:
- Keep LaTeX/KaTeX commands, markdown (**bold**), numbers and symbols of quantities intact.
- Cyrillic subscripts and units are human-readable and must NOT stay in Cyrillic:
  L_мол -> L_mol, N_удар -> N_hit, V_пар -> V_vap, T_гор -> T_hot, T_хол -> T_cold,
  кДж -> kJ, кПа -> kPa, моль -> mol, Дж -> J, эВ -> eV.
- Physics terminology must be the standard one in {lang}-language textbooks.
- Keep the tone: clear, engaging, no condescension. No alcohol analogies.

INPUT:
{payload}"""


def walk_strings(node, fn):
    """Обходим значения и заменяем строки через fn (вернула не строку — оставляем как было)."""
    if isinstance(node, dict):
        return {k: walk_strings(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [walk_strings(v, fn) for v in node]
    if isinstance(node, str):
        got = fn(node)
        return got if isinstance(got, str) and got.strip() else node
    return node


def fill_gaps(files, langs, dry=False, chunk_chars=4000):
    """Добор: переводим ОТДЕЛЬНЫЕ строки, в которых осталась кириллица.

    Зачем отдельный проход. Перевод блока целиком не сходится: на каждом заходе модель теряет
    пару полей в новом месте (то `mnemonic`, то `constants`), а блок из-за одной строки уезжает
    на повторный перевод весь — восемьдесят девять тысяч знаков за раз, и снова с потерей.
    Здесь мы просим ровно то, чего не хватает: собираем непереведённые строки, отдаём списком
    и ставим обратно во все места, где они встречались. Дёшево, сходится, и видно ровно то,
    что изменилось.
    """
    total = 0
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        br = branches(d)
        changed = 0
        for lang in langs:
            left = set()
            for b in br.values():
                if lang in b:
                    walk_strings(b[lang], lambda s: left.add(s) if CYR.search(s) else None)
            left = sorted(left)
            if not left:
                continue
            print(f"  {f.name} [{lang}]: строк с кириллицей {len(left)}", flush=True)
            if dry:
                for s in left[:6]:
                    print(f"      {s[:90]}", flush=True)
                continue
            # партиями; ключ — номер строки, чтобы модель не путала их местами
            table, batch, size = {}, {}, 0

            def send(b):
                got = _one(b, lang, prompt=FILL_PROMPT)
                if isinstance(got, dict):
                    for k, src in b.items():
                        v = got.get(k)
                        if isinstance(v, str) and v.strip() and not CYR.search(v):
                            table[src] = v

            for i, s in enumerate(left):
                if size + len(s) > chunk_chars and batch:
                    send(batch)
                    batch, size = {}, 0
                batch[str(i)] = s
                size += len(s)
            if batch:
                send(batch)
            if not table:
                print(f"      ⚠️ {lang}: добрать не удалось, строки остались русскими", flush=True)
                continue
            for b in br.values():
                if lang in b:
                    b[lang] = walk_strings(b[lang], lambda s: table.get(s))
            changed += len(table)
            print(f"      подставлено {len(table)} из {len(left)}", flush=True)
        if changed and not dry:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            total += changed
    print(f"✅ добрано строк: {total}", flush=True)


def main():
    argv = sys.argv
    # По умолчанию три языка: французский добавляем явным --langs fr, круг за кругом,
    # иначе один недосмотр запускает перевод всего курса на пятый язык разом.
    langs = ["en", "es", "ar"]
    if "--langs" in argv:
        langs = argv[argv.index("--langs") + 1].split(",")
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 0
    # --only <кусок пути>: одна тема за круг. Весь курс на новый язык — это полтора миллиона
    # знаков; без отбора любой прогон превращается в многочасовой и неотменяемый.
    only = argv[argv.index("--only") + 1] if "--only" in argv else ""

    files = targets()
    if only:
        files = [f for f in files if only in str(f).replace("\\", "/")]
        print("отбор «%s»: файлов %d" % (only, len(files)), flush=True)

    # --fill: добор отдельных строк вместо перевода блоков целиком (см. fill_gaps)
    if "--fill" in argv:
        only = argv[argv.index("--fill") + 1] if len(argv) > argv.index("--fill") + 1 \
                                                 and not argv[argv.index("--fill") + 1].startswith("--") else ""
        sel = [f for f in files if only in f.name] if only else files
        fill_gaps(sel, langs, dry="--dry" in argv)
        return

    todo = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        # Пропуск считаем ПО БЛОКАМ, а не по наличию языковой ветки. Раньше проверялось только
        # `lang not in d`: если перевод одного блока однажды сорвался, ветка оставалась неполной,
        # а файл навсегда считался переведённым. Так по курсу пропали `curiosities` у 27 уроков
        # и `synthesis` у 22 — читатель на en/es/ar не видел ни опытов на кухне, ни сквозного примера.
        # Блок «есть» ещё не значит «переведён». До того как из translate_block убрали молчаливый
        # откат, сорвавшийся запрос записывал в ветку РУССКИЙ оригинал — ключ на месте, читатель
        # видит кириллицу, а файл навсегда считается готовым. Так уцелел ar-блок mathkit.json.
        # Поэтому готовность меряем по содержимому: кириллица в en/es/ar — это непереведённый блок.
        missing = {}
        for owner, br in branches(d).items():
            for l in langs:
                if l not in br:
                    gaps = list(br["ru"].keys())
                else:
                    gaps = [k for k in br["ru"]
                            if k not in br[l]
                            or CYR.search(json.dumps(br[l][k], ensure_ascii=False))
                            or shape_broken(br["ru"][k], br[l][k])]
                if gaps:
                    missing[(owner, l)] = gaps
        if missing:
            todo.append((f, missing))
    if limit:
        todo = todo[:limit]

    def part(ru, keys):
        return {k: ru[k] for k in keys if k in ru}

    chars = 0
    for f, m in todo:
        br = branches(json.loads(f.read_text(encoding="utf-8")))
        for (owner, _l), keys in m.items():
            chars += len(json.dumps(part(br[owner]["ru"], keys), ensure_ascii=False))
    gaps = sum(len(v) for _, m in todo for v in m.values())
    print(f"материалов курса: {len(files)} | к переводу: {len(todo)} файлов, "
          f"{gaps} блоков, ~{chars/1000:.0f}k символов", flush=True)
    if "--check" in argv:
        for f, m in todo[:20]:
            for (owner, lang), keys in sorted(m.items()):
                where = f"{owner}." if owner else ""
                print(f"  {f.parent.name}/{f.name} [{lang}]: {where}{(', ' + where).join(keys[:6])}", flush=True)
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
        br = branches(d)
        for (owner, lang), keys in missing.items():
            try:
                got = translate_block(part(br[owner]["ru"], keys), lang)
                if not got:
                    continue
                # Дополняем ветку, а не перезаписываем: уже переведённое трогать незачем.
                br[owner].setdefault(lang, {})
                for k, v in got.items():
                    br[owner][lang][k] = v
                made.append(f"{lang}:{(owner + '.') if owner else ''}{len(got)}")
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
