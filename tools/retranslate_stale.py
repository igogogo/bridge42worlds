"""Ставит на перевод заново то, что поправили только по-русски.

Зачем. Пробел перевода конвейер видит по двум признакам: ключа нет в языковой ветке или в
нём осталась кириллица. Оба не срабатывают, когда русский блок ИСПРАВИЛИ, а перевод остался
старым: ключ на месте, кириллицы в нём нет — и читатель на английском продолжает видеть то,
что мы уже признали ошибкой. Сегодня так вышло сразу в трёх местах: в шестом шаге вывода
энтропии осталось «twenty-three digits» после починки на двадцать четыре, у резонанса —
старая формулировка про тысячу периодов, у фазового пространства — размерность 6·10²³.

Что делает. Сравнивает нынешние русские блоки с их состоянием в указанной ревизии git и,
если блок изменился, удаляет соответствующий ключ в en/es/ar/fr. Дальше обычный прогон
`course_translate.py` видит пропажу и переводит заново — ровно изменённое, не весь файл.

    python tools/retranslate_stale.py --since HEAD~5            показать, что устарело
    python tools/retranslate_stale.py --since HEAD~5 --apply    снять устаревшие переводы
"""
import json
import subprocess
import sys
from pathlib import Path

# Отчёт печатается по-русски, а консоль Windows отдаёт cp1252 — без этого падало на
# первой же строке вывода и инструмент был недоступен именно на рабочей машине.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOTS = [Path("data/theory/courses"), Path("data/theory")]
LANGS = ("en", "es", "ar", "fr")
# поля, которые переводятся; служебные (id, schema, model, entities) не трогаем
SKIP = {"id", "schema", "kind", "order", "model", "topic", "entities", "lessons"}


def files():
    out, seen = [], set()
    for r in ROOTS:
        it = r.rglob("*.json") if r.name == "courses" else r.glob("*.json")
        for f in it:
            if f in seen:
                continue
            seen.add(f)
            out.append(f)
    return sorted(out)


def at_revision(path, rev):
    """Содержимое файла в ревизии rev или None, если файла там не было."""
    p = str(path).replace("\\", "/")
    r = subprocess.run(["git", "show", "%s:%s" % (rev, p)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def same(a, b):
    """Одинаковы ли два блока. Сравниваем текстом, чтобы списки и словари шли наравне."""
    return json.dumps(a, ensure_ascii=False, sort_keys=True) == \
           json.dumps(b, ensure_ascii=False, sort_keys=True)


def branches(d):
    """Языковые ветки: наверху файла или внутри полей (ui/course у учебника)."""
    if isinstance(d.get("ru"), dict):
        return {"": d}
    return {k: v for k, v in d.items() if isinstance(v, dict) and isinstance(v.get("ru"), dict)}


def main():
    argv = sys.argv
    rev = argv[argv.index("--since") + 1] if "--since" in argv else "HEAD~1"
    apply = "--apply" in argv
    stale, touched_files = [], 0

    for f in files():
        try:
            now = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        old = at_revision(f, rev)
        if not old:
            continue
        now_br, old_br = branches(now), branches(old)
        changed_any = False
        for owner, nb in now_br.items():
            ob = old_br.get(owner)
            if not ob or not isinstance(ob.get("ru"), dict):
                continue
            for key, val in (nb.get("ru") or {}).items():
                if key in SKIP:
                    continue
                old_ru = ob.get("ru") or {}
                if key not in old_ru or same(old_ru[key], val):
                    continue
                # Русский блок изменился. Но если ту же правку внесли и в языковую ветку
                # (так бывает при структурных правках — переименовали поле во всех языках
                # сразу), перевод не устарел, и снимать его значит платить за перевод
                # заново без причины. Поэтому смотрим на ветку языка тоже.
                for lang in LANGS:
                    lb = nb.get(lang)
                    if not (isinstance(lb, dict) and key in lb):
                        continue
                    old_lang = ob.get(lang)
                    if isinstance(old_lang, dict) and key in old_lang:
                        lang_changed = not same(old_lang[key], lb[key])
                    else:
                        # Перевода этого ключа в той ревизии не было вовсе. Раньше здесь
                        # сравнивали json.dumps(None) — «null» — с текстом перевода; они,
                        # понятно, не совпадали, ключ засчитывался как «поправили на всех
                        # языках сразу» и в отчёт не попадал. Молчал инструмент ровно про
                        # свой случай: блок сперва перевели, а потом починили по-русски.
                        # Отсутствие старого перевода ничего не доказывает, а перевод одного
                        # ключа стоит дешевле, чем строчка, которую мы уже признали ошибкой,
                        # оставшаяся у читателя, — считаем такой перевод устаревшим.
                        lang_changed = False
                    if not lang_changed:
                        stale.append("%s%s · %s [%s]" % (f.parent.name + "/" + f.stem,
                                                         ("." + owner) if owner else "", key, lang))
                        if apply:
                            lb.pop(key)
                            changed_any = True
        if changed_any and apply:
            f.write_text(json.dumps(now, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            touched_files += 1

    print("сравнение с %s | устаревших переводов: %d" % (rev, len(stale)))
    for s in stale[:40]:
        print("  ", s)
    if len(stale) > 40:
        print("   … и ещё %d" % (len(stale) - 40))
    if apply:
        print("снято переводов: %d в %d файлах — теперь их переведёт обычный прогон" % (len(stale), touched_files))
    else:
        print("это разбор; чтобы снять, добавьте --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
