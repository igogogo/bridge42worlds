# -*- coding: utf-8 -*-
"""Дыры в переводе, которые не видит ни один существующий детектор.

Штатный конвейер считает пробелом отсутствие ключа или кириллицу внутри перевода. Есть третий
случай, и он молчит громче двух первых: ключ на месте, кириллицы нет, а значение ПУСТОЕ.
Так бывает, когда модель вернула не все поля блока — переводчик честно пишет в лог
«оставлены пустыми, повторный прогон возьмётся за них», но если повторный прогон не сделали,
читатель получает страницу с пустым заголовком, и ни одна проверка об этом не скажет.

Четвёртый случай того же рода: список в переводе короче русского (шаг вывода потерялся,
вариант ответа пропал). Для derivation это уже ловит course_check.js; здесь — для всех списков.

Откуда берётся укороченный список: русскую ветку пересобрали (в путеводитель добавились законы,
в тему — параграфы), а перевод остался от прошлой версии. Ключ на месте, кириллицы нет — и на
английской странице темы оказывается один параграф из трёх, а в путеводителе ноль ссылок из
четырёх. Ни один детектор об этом не говорил.

    python tools/translation_holes.py           разбор
    python tools/translation_holes.py --strict  вернуть код 1, если дыры есть
    python tools/translation_holes.py --fix     снять дырявые блоки, чтобы их перевели заново
"""
import glob
import io
import json
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LANGS = ("en", "es", "ar", "fr")
ROOTS = ["data/theory/courses/*/*.json", "data/theory/*.json"]


def branches(d):
    if isinstance(d.get("ru"), dict):
        return {"": d}
    return {k: v for k, v in d.items() if isinstance(v, dict) and isinstance(v.get("ru"), dict)}


def compare(ru, tr, path, out):
    """Сравнивает русское значение с переведённым и копит расхождения формы."""
    if isinstance(ru, dict):
        if not isinstance(tr, dict):
            return
        for k, v in ru.items():
            if k in tr:
                compare(v, tr[k], path + "." + k, out)
        return
    if isinstance(ru, list):
        if not isinstance(tr, list):
            return
        if len(tr) < len(ru):
            out.append((path, "список короче: %d против %d" % (len(tr), len(ru))))
        for i in range(min(len(ru), len(tr))):
            compare(ru[i], tr[i], "%s[%d]" % (path, i), out)
        return
    if isinstance(ru, str):
        if ru.strip() and isinstance(tr, str) and not tr.strip():
            out.append((path, "пусто, а в русском %d знаков" % len(ru.strip())))


def main():
    fix = "--fix" in sys.argv
    files, seen = [], set()
    for pat in ROOTS:
        for f in glob.glob(pat):
            if f not in seen:
                seen.add(f)
                files.append(f)

    holes, dropped, touched = 0, 0, 0
    for f in sorted(files):
        raw = io.open(f, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in raw else "\n"
        try:
            d = json.loads(raw)
        except Exception as e:
            print("НЕВАЛИДНЫЙ JSON: %s — %s" % (f, e))
            holes += 1
            continue
        changed = False
        for owner, br in branches(d).items():
            ru = br.get("ru")
            if not isinstance(ru, dict):
                continue
            for lang in LANGS:
                tr = br.get(lang)
                if not isinstance(tr, dict):
                    continue
                out = []
                compare(ru, tr, lang, out)
                if not out:
                    continue
                name = f.replace("\\", "/").split("courses/")[-1]
                if owner:
                    name += " · " + owner
                for path, why in out[:8]:
                    print("  %-40s %s — %s" % (name, path, why))
                if len(out) > 8:
                    print("  %-40s … и ещё %d" % (name, len(out) - 8))
                holes += len(out)
                if fix:
                    # Снимаем блок верхнего уровня целиком: перевод куска, у которого поехала
                    # форма, чинить по кускам нельзя — модель переводит блок как единое целое.
                    blocks = {p.split(".")[1].split("[")[0] for p, _ in out if "." in p}
                    for b in blocks:
                        if b in tr:
                            tr.pop(b)
                            dropped += 1
                            changed = True
        if changed:
            io.open(f, "w", encoding="utf-8", newline=nl).write(
                json.dumps(d, ensure_ascii=False, indent=1) + "\n")
            touched += 1

    print("дыр в переводе (пустое значение или укороченный список): %d" % holes)
    if fix:
        print("снято блоков: %d в %d файлах — обычный прогон переведёт их заново" % (dropped, touched))
    return 1 if (holes and "--strict" in sys.argv and not fix) else 0


if __name__ == "__main__":
    sys.exit(main())
