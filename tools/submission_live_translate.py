#!/usr/bin/env python3
"""Оригинальный html автора — на все наши языки.

Владелец 2026-08-08: «оригинальный html переведи тоже на все языки, ну и PDF, понятно…
авторы могут прислать на любом языке, но у нас стандарт на все распространяется».

Он прав: ссылка «работа автора: HTML» стоит на арабской странице ровно так же, как на
русской, и арабский читатель по ней попадал в русский текст. Стандарт сайта — пять языков,
и первоисточник из него не исключение.

Что переводим и чего НЕ трогаем. Переводим только текстовые узлы и подписи (alt, title,
placeholder). Не трогаем: содержимое <script> и <style>, имена файлов, числа, единицы,
идентификаторы элементов — на них завязаны авторские визуализации, и перевод строки внутри
скрипта попросту сломал бы их.

    python tools/submission_live_translate.py b42p-2026-001
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LANGS = ["en", "es", "ar", "fr"]
RTL = {"ar"}
SKIP_TAGS = {"script", "style", "code", "pre", "noscript"}
ATTRS = ("alt", "title", "placeholder", "aria-label")
# Пакет строк за один запрос. Меньше — дороже и дольше, больше — модель начинает
# терять строки и рвать JSON (проверено на арабском: пакет из 27 подписей не собрался).
CHUNK = 25


class Collector(HTMLParser):
    """Собирает переводимые куски: (вид, позиция, текст).

    Свой разбор, а не BeautifulSoup: пакет не установлен, а задача узкая — пройти документ
    и запомнить, где лежит человеческий текст. Восстанавливаем подстановкой по исходным
    строкам, поэтому разметка автора остаётся ровно такой, какой была.
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.skip = 0
        self.items = []          # (kind, raw, value)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        for k, v in attrs:
            if k in ATTRS and v and _worth(v):
                self.items.append(("attr", v, v))

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if self.skip:
            return
        if _worth(data):
            self.items.append(("text", data, data.strip()))


def _worth(s):
    """Стоит ли переводить строку.

    Отсеиваем то, что переводом только испортишь: числа, единицы, имена файлов, куски
    кода. Признак человеческого текста простой — есть буквы и хотя бы два слова, либо
    одно длинное слово.
    """
    s = (s or "").strip()
    if len(s) < 3 or len(s) > 3000:
        return False
    if not re.search(r"[A-Za-zА-Яа-яЁё؀-ۿ]", s):
        return False
    if re.fullmatch(r"[\w.\-/]+\.(png|jpg|jpeg|svg|webp|mp4|csv|json|py|md|txt)", s, re.I):
        return False
    letters = sum(c.isalpha() for c in s)
    return letters / len(s) > 0.35


def translate_chunk(items, lang, retries=2):
    """Пакет строк → перевод. Возвращает словарь исходная→переведённая.

    Промпт и проверка берутся ОБЩИЕ, из gen_llm — те самые, что переводят статьи.
    Свой самодельный вызов сюда я уже написал однажды, и он повторил болезнь, которую
    общий переводчик пережил и вылечил: модель возвращала аккуратный JSON нужной длины,
    но частью значений клала обратно русский текст. Формально ответ верный — читатель
    видит треть арабской страницы по-русски (владелец 2026-08-08).

    Проверка тоже общая: gen_llm._script_ratio считает долю букв нужного алфавита. Своя
    проверка рядом с чужой — это два разных представления о том, что такое перевод, и
    расходиться они начнут в первый же месяц.
    """
    import gen_llm
    from common import chat, clean_json
    src = {str(i): v for i, v in enumerate(items)}
    NL = "\n"
    ask = ("Переведи значения JSON на язык с кодом " + lang + "." + NL +
           "Ключи оставь как есть. Ничего не добавляй, не убирай и не объясняй." + NL +
           "ПЕРЕВОДИ КАЖДОЕ значение. Оставить строку на языке оригинала — ошибка." + NL +
           "Числа, единицы измерения, обозначения и имена файлов не трогай." + NL + NL +
           json.dumps(src, ensure_ascii=False))
    for _ in range(retries):
        try:
            r = chat("translate_flash", ask,
                     system=f"Ты переводчик научного текста. Отвечай только на языке {lang}.")
            got = json.loads(clean_json(r.choices[0].message.content))
        except Exception:
            continue
        out = {}
        for k, v in got.items():
            try:
                idx = int(k)
            except (TypeError, ValueError):
                continue
            if not (0 <= idx < len(items)):
                continue
            val = str(v).strip()
            if val and _translated(val, lang, gen_llm):
                out[items[idx]] = val
        if out:
            return out
    return {}


def _translated(value, lang, gen_llm):
    """Перевод ли это, или модель вернула исходную строку.

    Считаем алфавит тем же _script_ratio, что и вся остальная генерация. Короткие строки
    (обозначения, единицы) пропускаем: их и не надо переводить.
    """
    if len(value.strip()) < 4:
        return True
    # Кириллица в нерусском переводе — верный признак, что строку не тронули.
    if gen_llm._script_ratio(value, "Ѐ", "ӿ") > 0.3:
        return False
    if lang == "ar":
        return gen_llm._script_ratio(value, "؀", "ۿ") > 0.3
    return True


def build(code: str):
    src = ROOT / "lang" / "ru" / "community" / code / "live" / "index.html"
    if not src.exists():
        print(f"нет живой версии: {src}")
        return {}
    html = src.read_text(encoding="utf-8", errors="replace")

    c = Collector()
    c.feed(html)
    uniq, seen = [], set()
    for kind, raw, val in c.items:
        if val not in seen:
            seen.add(val)
            uniq.append(val)
    print(f"  строк к переводу: {len(uniq)}")

    made = {}
    for lang in LANGS:
        # Три прохода уменьшающимися пакетами: что не сошлось большим куском, обычно
        # сходится маленьким. Проверяем результат не «сошёлся ли JSON», а тем, осталась ли
        # строка непереведённой — это единственный признак, который видит читатель.
        table = {}
        todo = list(uniq)
        for size in (CHUNK, 8, 3):
            if not todo:
                break
            for i in range(0, len(todo), size):
                table.update(translate_chunk(todo[i:i + size], lang))
            todo = [x for x in todo if x not in table]
            if todo:
                print(f"     {lang}: осталось непереведённых {len(todo)} — заход пакетом по {size}")
        if todo:
            print(f"  ⚠️ {lang}: не перевелось {len(todo)} строк — останутся на языке автора")
        if not table:
            print(f"  ⚠️ {lang}: перевод не сошёлся — живая версия останется на языке автора")
            continue

        out = html
        # Подставляем от длинных к коротким: иначе короткая строка заменится внутри длинной.
        for k in sorted(table, key=len, reverse=True):
            out = out.replace(k, table[k])
        # Направление письма и язык документа — иначе арабский текст пойдёт слева направо.
        out = re.sub(r'<html[^>]*>', f'<html lang="{lang}" dir="{"rtl" if lang in RTL else "ltr"}">',
                     out, count=1)

        d = ROOT / "lang" / lang / "community" / code / "live"
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(out, encoding="utf-8")
        # Картинки не копируем заново: ссылаемся на русскую папку — файл один и тот же,
        # а лишние 27 копий на каждый язык это 54 МБ на ровном месте.
        for sub in ("figures", "media"):
            s = ROOT / "lang" / "ru" / "community" / code / "live" / sub
            if s.exists():
                rel = f"/lang/ru/community/{code}/live/{sub}/"
                out2 = (d / "index.html").read_text(encoding="utf-8")
                out2 = out2.replace(f'"{sub}/', f'"{rel}').replace(f"'{sub}/", f"'{rel}")
                (d / "index.html").write_text(out2, encoding="utf-8")
        made[lang] = f"/lang/{lang}/community/{code}/live/index.html"
        print(f"  🌐 {lang}: живая версия переведена ({len(table)} строк)")
    return made


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("нужен код: python tools/submission_live_translate.py b42p-2026-001")
        sys.exit(2)
    print(json.dumps(build(sys.argv[1]), ensure_ascii=False, indent=1))
