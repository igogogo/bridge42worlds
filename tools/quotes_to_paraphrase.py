#!/usr/bin/env python3
"""Цитаты учёных → пересказ. Правило волны 17.08: цитата без источника не публикуется
как цитата.

Почему все 189, а не только 35-38 «в кавычках». Аудит считал цитаты с «ёлочками»
в тексте, но шаблон (generate.py:3119) сам оборачивает В КАВЫЧКИ любую непустую цитату
и подписывает «Цитата». То есть КАЖДАЯ из 189 публикуется как прямая речь — а источника
нет ни у одной. Проверить подлинность двухсот высказываний на пяти языках мы не можем;
значит по правилу все становятся пересказом. Настоящая цитата с источником сможет
вернуться — полем quote_source, когда оно у кого-то появится.

Пересказ — косвенная речь без кавычек и без первого лица: не «Свет — это не волна»,
а «Считал свет не волной и не частицей, а ...». Модель переводит форму, не содержание:
добавлять факты и украшать запрещено системной ролью.

Рядом с новым текстом пишется quote_kind="paraphrase" — по нему повторный запуск
пропускает уже сделанное, и по нему же рендер сможет отличать пересказ от будущей
настоящей цитаты.

ВАЖНО про рендер: пока generate.py:3119 оборачивает текст в кавычки, пересказ на проде
будет выглядеть цитатой. Строка рендера — зона архитектора; запрос ему в отчёте
стратегии. Данные готовим сейчас, чтобы пересборка забрала обе правки разом.

Запуск ИЗ ГЛАВНОЙ ПАПКИ (данные и config там):
    python tools/quotes_to_paraphrase.py --dry            объём и примеры, без трат
    python tools/quotes_to_paraphrase.py --lang ru        один язык
    python tools/quotes_to_paraphrase.py                  все пять
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
BATCH = 10

LANG_NAME = {"ru": "русском", "en": "английском", "es": "испанском",
             "ar": "арабском", "fr": "французском"}

SYSTEM = """Ты редактор научно-популярного сайта. Тебе дают приписываемые учёным
высказывания, у которых нет подтверждённого источника. Твоя задача — переписать каждое
КОСВЕННОЙ РЕЧЬЮ: как пересказ взгляда учёного, а не как его слова.

Правила, все обязательные:
— никакого первого лица и никаких кавычек в результате;
— начинай с глагола отношения в прошедшем времени: считал/считала, говорил, называл,
  сравнивал, видел в... — по смыслу;
— содержание сохраняй точно: ничего не добавлять, не усиливать, не украшать;
— если высказывание невозможно пересказать без потери смысла, верни его смысловое ядро
  одним предложением;
— пиши СТРОГО на {lang_name} языке — на том же, на котором дан исходный текст.

Ответ строго JSON: {{"paraphrases": {{"<id>": "<пересказ>", ...}}}} — по одному на каждый
входной id. Никакого текста вне JSON."""


def load(lang):
    p = ROOT / "lang" / lang / "data" / "scientists.json"
    return p, json.loads(p.read_text(encoding="utf-8"))


def save(p, d):
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)          # атомарно: обрыв на середине не оставит битого файла


def pending(d):
    out = []
    for name, s in d.items():
        q = (s.get("quote") or "").strip()
        if q and s.get("quote_kind") != "paraphrase":
            out.append((name, q))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--lang", choices=LANGS)
    a = ap.parse_args()
    langs = [a.lang] if a.lang else list(LANGS)

    if a.dry:
        for lang in langs:
            _, d = load(lang)
            todo = pending(d)
            print(f"{lang}: к пересказу {len(todo)}")
            for n, q in todo[:2]:
                print(f"   {n}: {q[:70]}")
        return 0

    from common import chat, parse_json_salvage, deepseek_peak_status
    is_peak, _ = deepseek_peak_status()
    if is_peak:
        print("⛔ пиковые часы DeepSeek — правило волны: массовые прогоны только вне пика.")
        return 1

    for lang in langs:
        p, d = load(lang)
        todo = pending(d)
        print(f"\n{lang}: к пересказу {len(todo)}")
        done = 0
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            payload = {str(k): q for k, (_, q) in enumerate(batch)}
            sysmsg = SYSTEM.format(lang_name=LANG_NAME[lang])
            resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False),
                        system=sysmsg)
            data = parse_json_salvage(resp.choices[0].message.content) or {}
            got = data.get("paraphrases") or {}
            for k, (name, orig) in enumerate(batch):
                new = (got.get(str(k)) or "").strip().strip('«»"“”')
                # Пустой или несжавшийся ответ оставляет старый текст и НЕ ставит метку:
                # молча превратить цитату в пустоту хуже, чем не тронуть.
                if not new:
                    print(f"   ⚠️ {name}: пересказа нет — пропущено, зайдёт в повтор")
                    continue
                d[name]["quote"] = new
                d[name]["quote_kind"] = "paraphrase"
                done += 1
            save(p, d)       # после каждой пачки: обрыв теряет одну пачку, не всё
            print(f"   {min(i + BATCH, len(todo))}/{len(todo)}")
        print(f"{lang}: готово {done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
