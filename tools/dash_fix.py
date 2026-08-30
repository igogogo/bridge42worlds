#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Следы перевода в данных статей — правилами, без модели.

Владелец 29.08: «боюсь, что это риск, что дешёвая модель нам текст сломает,
проблем не оберёшься… если можно, просто каким-то инструментом хитрым это сделать
без модели… или хотя бы в пробелы их обрамить, а то так даже сливаются».

Близнец js/typography.js: там та же лестница правил лечит СТРАНИЦЫ, уже лежащие
на сайте, без пересборки; здесь она же лечит ИСТОЧНИК, чтобы следующая сборка
пришла уже чистой. Правила должны совпадать буква в букву — иначе страница до
пересборки и после будет читаться по-разному.

ЛЕСТНИЦА (только там, где выбор однозначен):
  · тире парой, вокруг вставки        -> запятые: «qubit, a tiny loop, crunches»;
    если внутри вставки своя запятая  -> скобки;
  · перед and/but/or/nor/so/yet       -> запятая;
  · перед like/just/as/such           -> запятая;
  · перед a/an/the и коротким хвостом -> запятая;
  · перед it/they/this/each/there…    -> двоеточие (дальше самостоятельное
    предложение, запятая склеила бы два предложения в одно);
  · во всех прочих случаях            -> тире с пробелами.
Последнее и есть страховка: пробельное тире всегда грамматично (так пишет AP),
и слова больше не слипаются. Гадать правила не пытаются: угаданное неверно
читается хуже оставшегося тире.

НЕ ТРОГАЕМ диапазоны чисел («300—800 GeV»): по обе стороны знака должна стоять
БУКВА, цифры исключены.

ВТОРОЙ АРТЕФАКТ ОТТУДА ЖЕ — литеральный перенос строки посреди абзаца: обратная
косая и буква n, видимые как есть (владелец 29.08: «и там ещё символ встретился»).
Переводчик отдавал перенос экранированным, а разбор ответа считал такую пару
перед латинской буквой началом команды LaTeX и удваивал слэш. По-русски после
переноса идёт кириллица, поэтому там таких 141, а в английском, испанском и
французском — по тридцать пять тысяч. Причина закрыта в common.py; здесь
литеральный знак становится настоящим переносом, и при следующей сборке абзац
встанет на место, как в русском оригинале.

ЦЕНА. Ноль: ни одного обращения к модели. Но data.json меняется, а значит
ближайшая сборка HTML посчитает эти статьи изменившимися и пересоберёт их.
Пока пересборки нет, читатель видит правку благодаря js/typography.js.

    python tools/dash_fix.py            сверка: сколько и что получится
    python tools/dash_fix.py --show 20  показать двадцать примеров
    python tools/dash_fix.py --apply    записать
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
_sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
TIERS = ("simple", "popular", "advanced")
FIELDS = ("text", "title", "oneliner", "description", "mini", "threads",
          "fun_fact", "scifi", "metaphor")

# Буква с обеих сторон: в питоне \w уже юникодный, поэтому [^\W\d_] — это
# «любая буква любого алфавита». Цифры и подчёркивание исключены.
TIGHT = re.compile(r"(?<=[^\W\d_])—(?=[^\W\d_])")
COMMA_BEFORE = re.compile(r"^(and|but|or|nor|so|yet|like|just|as|such)\b", re.I)
CLAUSE_AHEAD = re.compile(
    r"^(it|its|it's|they|their|this|that|that's|these|those|there|there's"
    r"|we|you|he|she|each|every)\b", re.I)
ARTICLE = re.compile(r"^(a|an|the)\b", re.I)
BREAK = re.compile(r"[.!?\n]")
# Литеральное «\n» — обратная косая и буква — посреди текста. Переводчик отдавал
# перенос строки экранированным, а разбор ответа считал «\n» перед латинской буквой
# началом команды LaTeX (\nu) и удваивал слэш. По-русски после переноса идёт
# кириллица, поэтому там таких 141, а в английском, испанском и французском — по
# тридцать пять тысяч на 4 713 статей. Причина закрыта в common.py (теперь командой
# считается только СТРОЧНАЯ латинская после слэша); здесь чинится написанное.
# Заглавная после — верный признак: по корпусу она встретилась 13 456 раз и ни разу
# не была командой, строчная — 10 раз и каждый раз была.
SLASH_N = re.compile(r"\\n(?=[A-ZА-ЯЁ])")
MANY_NL = re.compile(r"\n{3,}")


# Маркеры сущностей стоят прямо в тексте: «...[tag:qubit]qubit[/tag]—a tiny loop».
# Слева от тире тогда не буква, а закрывающая скобка, и правило тире не видело —
# а размечены как раз термины, то есть это самый частый случай. Для ПОИСКА маркер
# закрашиваем буквами той же длины (адреса не сдвигаются), для РЕШЕНИЯ вырезаем
# совсем: следующее слово это «helium», а не «[tag:helium]helium[/tag]».
MARKER = re.compile(r"\[/?(?:tag|law|scientist|callout)(?::[^\]]*)?\]")


def mask(s):
    return MARKER.sub(lambda m: "x" * len(m.group(0)), s)


def pick(s, off):
    word = MARKER.sub("", s[off + 1:])
    if COMMA_BEFORE.match(word):
        return ", "
    if CLAUSE_AHEAD.match(word):
        return ": "
    if ARTICLE.match(word) and len(word.split()) <= 9:
        return ", "
    return " — "


def bounds(s, off):
    """Границы предложения вокруг адреса — чтобы отличить пару тире от одиночного."""
    a = 0
    for i in range(off, 0, -1):
        if BREAK.match(s[i - 1]):
            a = i
            break
    b = len(s)
    for i in range(off, len(s)):
        if BREAK.match(s[i]):
            b = i + 1
            break
    return a, b


def fix(s, lang):
    """Строка с исправленными тире и без литеральных «\\n». Буквы не теряются."""
    # Литеральное «\n» становится настоящим переносом: там, где переводчик хотел
    # разрыв абзаца, он и появится при следующей сборке — как в русском оригинале.
    if "\\n" in s:
        s = MANY_NL.sub("\n\n", SLASH_N.sub("\n", s))
    masked = mask(s)
    at = [m.start() for m in TIGHT.finditer(masked)]
    if not at:
        return s
    if lang != "en":
        # Русский, испанский, французский, арабский: лестница написана про английские
        # союзы, переносить её на другие языки — гадание. Разводим пробелами, что для
        # русского вдобавок и есть верная типографика.
        out, prev = [], 0
        for o in at:
            out.append(s[prev:o])
            out.append(" — ")
            prev = o + 1
        out.append(s[prev:])
        return "".join(out)

    edits, used = [], set()
    for o in at:
        if o in used:
            continue
        lo, hi = bounds(masked, o)
        pair = [x for x in at if lo <= x < hi]
        if len(pair) >= 2:
            inner = MARKER.sub("", s[pair[0] + 1:pair[1]])
            paren = "," in inner
            edits.append((pair[0], " (" if paren else ", "))
            edits.append((pair[1], ") " if paren else ", "))
            used.update(pair[:2])
            for x in pair[2:]:
                edits.append((x, " — "))
                used.add(x)
        else:
            edits.append((o, pick(s, o)))
            used.add(o)

    out, prev = [], 0
    for o, rep in sorted(edits):
        out.append(s[prev:o])
        out.append(rep)
        prev = o + 1
    out.append(s[prev:])
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description="Тире в данных статей — правилами, без модели")
    ap.add_argument("--apply", action="store_true", help="записать в data.json")
    ap.add_argument("--show", type=int, default=0, help="показать столько примеров")
    ap.add_argument("--langs", default=",".join(LANGS), help="языки через запятую")
    a = ap.parse_args()
    langs = tuple(x.strip() for x in a.langs.split(",") if x.strip())

    per, nl, arts, shown = Counter(), Counter(), 0, []
    written = 0
    for p in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        touched = False
        for tier in TIERS:
            for lang in langs:
                v = (d.get(tier, {}) or {}).get(lang)
                if not isinstance(v, dict):
                    continue
                for k in FIELDS:
                    txt = v.get(k)
                    # Второй артефакт живёт отдельно от первого: поле бывает без единого
                    # тире, но с литеральным «\n». Отбор только по тире его пропускал.
                    if not isinstance(txt, str) or ("—" not in txt and "\\n" not in txt):
                        continue
                    new = fix(txt, lang)
                    if new == txt:
                        continue
                    nl[lang] += len(SLASH_N.findall(txt))
                    per[lang] += len(TIGHT.findall(mask(txt)))
                    touched = True
                    if len(shown) < a.show:
                        m = TIGHT.search(mask(txt))
                        shown.append((txt[max(0, m.start() - 90):m.start() + 90],
                                      new[max(0, m.start() - 90):m.start() + 95]))
                    v[k] = new
        if touched:
            arts += 1
            if a.apply:
                p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                written += 1

    print(f"статей затронуто {arts:,} · тире исправлено "
          f"{sum(per.values()):,} · " + " · ".join(f"{k} {v:,}" for k, v in sorted(per.items())))
    if sum(nl.values()):
        print(f"литеральных переносов убрано {sum(nl.values()):,} · "
              + " · ".join(f"{k} {v:,}" for k, v in sorted(nl.items())))
    for was, now in shown:
        print(f"\n  было:  …{was.strip()}…\n  стало: …{now.strip()}…")
    if a.apply:
        print(f"\nзаписано в {written:,} статей")
    else:
        print("\nэто сверка; --apply запишет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
