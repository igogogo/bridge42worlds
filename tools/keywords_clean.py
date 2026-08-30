# -*- coding: utf-8 -*-
"""Чистит ключевые слова свободных ответов во всех языковых ветках.

Зачем. Ответ на свободный вопрос засчитывается по вхождению ключевых слов подстрокой, а порог
обычно «нужно два разных». Перевод регулярно ломает это условие, не ломая ничего видимого:
модель возвращает список, где одно слово повторено дважды («proporción», «proporción») или одно
лежит внутри другого («طول» внутри «على طول», «ток» внутри «поток»). Оба случая означают, что
порог в два слова набирается ОДНИМ словом читателя — вопрос сдаётся сам.

Правило: оставляем только самостоятельные ключи. Из пары, где один — подстрока другого, остаётся
БОЛЕЕ ДЛИННЫЙ: он точнее, а короткий и так сработает внутри него. Дубли убираются. Порядок
сохраняется — по нему видно замысел автора.

Русскую ветку тоже проверяем: там та же беда бывает у автора, просто реже.

    python tools/keywords_clean.py           разбор
    python tools/keywords_clean.py --apply   почистить
"""
import glob
import io
import json
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS


def clean(keys):
    out = []
    for k in keys:
        s = (k or "").strip()
        if not s:
            continue
        low = s.lower()
        # уже есть такой же или тот, внутри которого он лежит
        if any(low == x.lower() or low in x.lower() for x in out):
            continue
        # выбрасываем ранее принятые, которые оказались внутри нового
        out = [x for x in out if x.lower() not in low]
        out.append(s)
    return out


def main():
    apply = "--apply" in sys.argv
    touched, dropped = 0, 0
    for p in sorted(glob.glob("data/theory/courses/*/[0-9]*.json")):
        raw = io.open(p, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in raw else "\n"
        d = json.loads(raw)
        changed = False
        for lang in LANGS:
            br = d.get(lang)
            if not isinstance(br, dict):
                continue
            for q in br.get("quiz") or []:
                keys = q.get("keywords")
                if not isinstance(keys, list) or len(keys) < 2:
                    continue
                new = clean(keys)
                if new != keys:
                    gone = [k for k in keys if k not in new]
                    print("  %-34s %s %-4s убрано: %s" %
                          (p.replace("\\", "/").split("courses/")[-1], lang, q.get("id"), ", ".join(gone)))
                    dropped += len(gone)
                    if apply:
                        q["keywords"] = new
                        changed = True
        if changed and apply:
            io.open(p, "w", encoding="utf-8", newline=nl).write(
                json.dumps(d, ensure_ascii=False, indent=1) + "\n")
            touched += 1
    print("лишних ключей: %d%s" % (dropped, (" — убрано в %d файлах" % touched) if apply else
                                   "; чтобы убрать, добавьте --apply"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
