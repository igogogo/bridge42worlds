"""Добавляет ещё один язык в словари интерфейса курса.

Зачем отдельный инструмент. Материалы уроков переводит `course_translate.py` — он работает
с JSON. Но подписи интерфейса живут в двух JS-словарях: `js/course-i18n.js` (текст узлов
страницы) и `js/figures-i18n.js` (подписи внутри схем). Пока язык добавляли руками, и на
пятом языке это перестало быть разумным: 315 строк.

Как работает. Значения вынимаются исполнением самих файлов (а не разбором текста), поэтому
ключи всегда настоящие. Перевод идёт батчами: русский ключ плюс уже готовый английский
перевод как опора — так модель не переизобретает термин заново. Запись — точечная вставка в
существующий литерал, комментарии и порядок строк файла не трогаются.

    python tools/dict_lang.py --lang fr --check    сколько строк не хватает
    python tools/dict_lang.py --lang fr --dry      перевести и показать, без записи
    python tools/dict_lang.py --lang fr            сделать
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import chat, clean_json, parse_json_salvage  # noqa: E402

LANG_NAME = {"fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese"}
COURSE_I18N = Path("js/course-i18n.js")
FIG_I18N = Path("js/figures-i18n.js")
# порядок значений в course-i18n.js: массив [en, es, ar, ...]
ORDER = ["en", "es", "ar"]

PROMPT = """Translate UI strings of a physics course website into {lang}.

Each item has the Russian original and the existing English translation — use the English one
as the reference for terminology, and the Russian one for tone and punctuation.

RULES:
- Keep it SHORT: these are buttons, captions and headings, they must fit the same space.
- Keep numbers, symbols of quantities, LaTeX, HTML entities (&#916;) and placeholders ($1, $2)
  exactly as they are.
- Physics terms must be the standard ones in {lang}-language textbooks.
- Return STRICT JSON: the same keys, translated values, nothing else.

INPUT:
{payload}"""


def load_js(path, expr):
    """Значения словаря берём исполнением файла: ключи гарантированно настоящие."""
    node = ("const fs=require('fs');global.window={};"
            "eval(fs.readFileSync(%s,'utf8'));"
            "process.stdout.write(JSON.stringify(%s));" % (json.dumps(str(path)), expr))
    out = subprocess.run(["node", "-e", node], capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise SystemExit("не прочитать %s: %s" % (path, out.stderr[:200]))
    return json.loads(out.stdout)


def load_dict():
    """course-i18n.js держит DICT внутри замыкания, поэтому вырезаем литерал."""
    src = COURSE_I18N.read_text(encoding="utf-8")
    i = src.index("var DICT = {")
    j = src.index("\n    };", i)
    lit = src[i + len("var DICT = "):j + len("\n    }")]
    node = "process.stdout.write(JSON.stringify((%s)));" % lit
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(node)
        tmp = f.name
    out = subprocess.run(["node", tmp], capture_output=True, text=True, encoding="utf-8")
    Path(tmp).unlink(missing_ok=True)
    if out.returncode != 0:
        raise SystemExit("не разобрать DICT: %s" % out.stderr[:200])
    return json.loads(out.stdout)


def translate(pairs, lang, chunk=2500):
    """pairs: [(ключ_ru, en)] → {ключ_ru: перевод}. Батчами, чтобы ответ не обрывался."""
    done, batch, size = {}, {}, 0

    def flush():
        nonlocal batch, size
        if not batch:
            return
        payload = {k: {"ru": k, "en": v} for k, v in batch.items()}
        for _ in range(2):
            try:
                r = chat("translate", PROMPT.format(lang=LANG_NAME[lang],
                                                    payload=json.dumps(payload, ensure_ascii=False)),
                         model="deepseek-v4-flash", max_tokens=8000)
                raw = r.choices[0].message.content or ""
                got = parse_json_salvage(raw) or json.loads(clean_json(raw))
                if isinstance(got, dict):
                    for k in batch:
                        v = got.get(k)
                        if isinstance(v, dict):
                            v = v.get(lang) or v.get("fr") or v.get("text")
                        # пустое или оставшееся кириллицей не берём: пусть лучше не хватает
                        if isinstance(v, str) and v.strip() and not re.search(r"[А-Яа-яЁё]", v):
                            done[k] = v.strip()
                    break
            except Exception:
                continue
        batch, size = {}, 0

    for k, en in pairs:
        s = len(k) + len(en or "")
        if size + s > chunk and batch:
            flush()
        batch[k] = en or k
        size += s
    flush()
    return done


def put_course_i18n(add, lang):
    """Дописываем значение в конец массива у каждой записи DICT."""
    src = COURSE_I18N.read_text(encoding="utf-8")
    start = src.index("var DICT = {")
    end = src.index("\n    };", start)
    head, body, tail = src[:start], src[start:end], src[end:]
    n = 0
    for key, val in add.items():
        # Ключ может встречаться в словаре ДВАЖДЫ: в JS вторая запись перекрывает первую, и
        # такой дубль легко не заметить. Если писать только в первое вхождение, перевод
        # уходит в мёртвую запись, а страница остаётся без него — на «Открытых вопросах»
        # ровно так и вышло. Поэтому дописываем во все вхождения и говорим о дубле вслух.
        pats = [r"(?m)^\s*'" + re.escape(key.replace("'", "\\'")) + r"':\s*\[",
                r"(?m)^\s*" + re.escape(json.dumps(key, ensure_ascii=False)) + r":\s*\["]
        spots = []
        for p in pats:
            spots += [m.end() - 1 for m in re.finditer(p, body)]
        if not spots:
            continue
        if len(spots) > 1:
            print("    ⚠️ ключ встречается %d раза, дописываю везде: %s" % (len(spots), key[:60]), flush=True)
        ins = (", " + json.dumps(val, ensure_ascii=False).replace('"', "'")) if "'" not in val \
            else (", " + json.dumps(val, ensure_ascii=False))
        for start in sorted(spots, reverse=True):     # с конца, чтобы позиции не поехали
            i, depth = start, 0
            while i < len(body):
                if body[i] == "[":
                    depth += 1
                elif body[i] == "]":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            body = body[:i] + ins + body[i:]
        n += 1
    COURSE_I18N.write_text(head + body + tail, encoding="utf-8")
    return n


def put_fig_i18n(add, lang):
    """figures-i18n.js — обычный JSON-объект, правим как данные."""
    data = load_js(FIG_I18N, "window.B42FigText")
    n = 0
    for k, v in add.items():
        if k in data and lang not in data[k]:
            data[k][lang] = v
            n += 1
    src = FIG_I18N.read_text(encoding="utf-8")
    head = src[:src.index("window.B42FigText = {")]
    FIG_I18N.write_text(head + "window.B42FigText = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
                        encoding="utf-8")
    return n


def main():
    argv = sys.argv
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else "fr"
    check, dry = "--check" in argv, "--dry" in argv
    if lang not in LANG_NAME:
        raise SystemExit("не знаю язык %s" % lang)

    dic = load_dict()
    fig = load_js(FIG_I18N, "window.B42FigText")
    idx = len(ORDER)

    need_dic = [(k, (v[0] if len(v) > 0 else "")) for k, v in dic.items() if len(v) <= idx]
    need_fig = [(k, v.get("en", "")) for k, v in fig.items() if lang not in v]
    print("интерфейс: %d из %d без %s | схемы: %d из %d без %s"
          % (len(need_dic), len(dic), lang, len(need_fig), len(fig), lang), flush=True)
    if check:
        for k, _ in (need_dic[:5] + need_fig[:5]):
            print("   ", k[:70], flush=True)
        return

    got_dic = translate(need_dic, lang) if need_dic else {}
    got_fig = translate(need_fig, lang) if need_fig else {}
    print("переведено: интерфейс %d, схемы %d" % (len(got_dic), len(got_fig)), flush=True)
    if dry:
        for k in list(got_dic)[:8]:
            print("    %s → %s" % (k[:44], got_dic[k][:44]), flush=True)
        return

    a = put_course_i18n(got_dic, lang)
    b = put_fig_i18n(got_fig, lang)
    print("записано: интерфейс %d, схемы %d" % (a, b), flush=True)
    miss = (len(need_dic) - len(got_dic)) + (len(need_fig) - len(got_fig))
    if miss:
        print("⚠️ осталось без перевода: %d — повторный прогон возьмётся за них" % miss, flush=True)


if __name__ == "__main__":
    main()
