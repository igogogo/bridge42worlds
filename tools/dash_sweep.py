#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веник по тире: убирает из готовых текстов плотное длинное тире.

Владелец 29.08: «у нас часто по тексту тире, типа astrophysics—from, что плохо,
люди это воспринимают как то, что сделал ИИ. Может, заменим типа на двоеточие,
где-то на запятую, где-то на вводное слово».

ОТКУДА ОНО БЕРЁТСЯ. Не из генерации, а из перевода. В русском тире — рядовой знак
и стоит с пробелами: «поле — это область». Переводчик переносил его в английский
как есть и прижимал к словам. Замер по корпусу: русских тире с пробелами 128 206
(норма), английских плотных — 62 325 на 16 272 страницах. Причину закрыли в
data/prompts/article-translate.txt и в системной роли переводчика; этот инструмент
подметает то, что уже написано.

ЧЕГО НЕ ТРОГАЕМ:
  · диапазоны чисел («300–800 GeV») — там знак на своём месте;
  · русское тире с пробелами — это правильная русская типографика;
  · маркеры [tag:...]/[law:...]/[scientist:...] — сверяем до и после, и если счёт
    не сошёлся, оставляем исходное предложение.

ПОЧЕМУ НЕ РЕГУЛЯРКОЙ. Замена одна на все случаи выдаёт себя не хуже тире. В
«very long—longer than the age of the Universe» просится запятая, в «an hour
later—nothing» двоеточие, а в «a table—each grain rolls down» запятая даст
сращение двух самостоятельных предложений. Выбор — языковая работа, поэтому
предложения уходят пачками в модель, а результат проверяется механически.

ДЕДУПЛИКАЦИЯ. Одно и то же предложение живёт в нескольких уровнях и полях:
вхождений 75 912, разных предложений 33 151. Платим за разные.

    python tools/dash_sweep.py --scan                 сколько и где, ничего не тратя
    python tools/dash_sweep.py --sample 20            прогнать двадцать штук и показать
    python tools/dash_sweep.py --apply --langs en     подмести и записать
    python tools/dash_sweep.py --apply --limit 200    ограничить пачку
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import chat, clean_json  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

LANGS = ("en", "es", "fr", "ar")
TIERS = ("simple", "popular", "advanced")
# Поля с прозой. key_numbers и glossary — словари подписей, там тире почти не бывает,
# а структура сложнее; их отдельно, если понадобится.
FIELDS = ("text", "title", "oneliner", "description", "mini", "threads",
          "fun_fact", "scifi", "metaphor")

# Плотное длинное тире МЕЖДУ БУКВАМИ. Цифры исключены нарочно: «300—800» это диапазон.
TIGHT = re.compile(r"(?<=[^\W\d_])[—](?=[^\W\d_])")
# Предложение: до точки/восклицательного/вопросительного или до конца абзаца.
SENT = re.compile(r"[^.!?\n]*[.!?\n]|[^.!?\n]+$")
MARKER = re.compile(r"\[(?:/?tag|/?law|/?scientist|/?callout)(?::[^\]]+)?\]")
NUM = re.compile(r"\d[\d.,]*")

BATCH = 20
SYSTEM = (
    "You are a copy editor. You receive numbered sentences that contain an em dash "
    "squeezed between words. Rewrite ONLY that punctuation: replace each tight em dash "
    "with a colon, a pair of commas, parentheses, or a short linking word (that is, "
    "which means, so, because), chosen by the meaning of the connection. Vary the "
    "choice across sentences; uniform replacement reads as mechanical too. "
    "Change NOTHING else: keep every word, number, name, bracket marker such as "
    "[tag:x]...[/tag], and the original language of the sentence. Never merge two "
    "independent clauses with a comma: use a colon or a semicolon there. "
    "Answer with a JSON object mapping each number to the rewritten sentence."
)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sentences(text):
    """Предложения текста, в которых есть плотное тире."""
    return [s for s in SENT.findall(text) if TIGHT.search(s)]


def collect(langs, limit=0):
    """Все затронутые предложения и карта, где они встречаются."""
    where = {}          # предложение → [(файл, уровень, язык, поле)]
    files = sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json"))
    for p in files:
        try:
            d = load(p)
        except Exception:
            continue
        for tier in TIERS:
            for lang in langs:
                v = (d.get(tier, {}) or {}).get(lang)
                if not isinstance(v, dict):
                    continue
                for k in FIELDS:
                    txt = v.get(k)
                    if not isinstance(txt, str) or "—" not in txt:
                        continue
                    for s in sentences(txt):
                        where.setdefault(s.strip(), []).append((p, tier, lang, k))
        if limit and len(where) >= limit:
            break
    return where


def safe(before, after):
    """Ответ модели годится, только если изменилась ПУНКТУАЦИЯ, а не содержание."""
    if not after or not isinstance(after, str):
        return False
    if TIGHT.search(after):
        return False
    if MARKER.findall(before) != MARKER.findall(after):
        return False
    if NUM.findall(before) != NUM.findall(after):
        return False
    # Длина не должна гулять: замена знака — это единицы символов, не абзац.
    if not 0.7 <= len(after) / max(1, len(before)) <= 1.4:
        return False
    return True


def rewrite(batch):
    """Пачка предложений в словарь номер-новое предложение. Что не прошло сверку,
    возвращаем как было: молчаливая порча текста хуже оставшегося тире."""
    items = {str(i): s for i, s in enumerate(batch)}
    out = dict(zip(range(len(batch)), batch))
    try:
        raw = chat("translate_light",
                   "Sentences:\n" + json.dumps(items, ensure_ascii=False, indent=1),
                   system=SYSTEM).choices[0].message.content
        got = json.loads(clean_json(raw))
    except Exception as e:
        print(f"  !! пачка пропущена ({type(e).__name__}: {str(e)[:80]})")
        return out
    for i, s in enumerate(batch):
        cand = got.get(str(i))
        if safe(s, cand):
            out[i] = cand.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description="Веник по плотному длинному тире")
    ap.add_argument("--scan", action="store_true", help="только счёт, ничего не тратим")
    ap.add_argument("--sample", type=int, default=0, help="прогнать столько штук и показать")
    ap.add_argument("--apply", action="store_true", help="записать в data.json")
    ap.add_argument("--langs", default=",".join(LANGS), help="языки через запятую")
    ap.add_argument("--limit", type=int, default=0, help="ограничить число предложений")
    ap.add_argument("--workers", type=int, default=6, help="сколько пачек считать разом")
    a = ap.parse_args()
    langs = tuple(x.strip() for x in a.langs.split(",") if x.strip())

    where = collect(langs, a.limit)
    hits = sum(len(v) for v in where.values())
    per = Counter(w[2] for v in where.values() for w in v)
    arts = {w[0] for v in where.values() for w in v}
    print(f"предложений разных {len(where):,} · вхождений {hits:,} · статей {len(arts):,}")
    print("  по языкам: " + " · ".join(f"{k} {v:,}" for k, v in sorted(per.items())))
    if a.scan:
        return 0

    keys = list(where)
    if a.sample:
        keys = keys[:a.sample]
    packs = [keys[i:i + BATCH] for i in range(0, len(keys), BATCH)]
    fixed = {}
    # Пачки идут параллельно: работа упирается в ожидание ответа, а не в счёт.
    # Полторы тысячи запросов подряд это два часа, вшестером — минут двадцать.
    done = 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for part, got in zip(packs, ex.map(rewrite, packs)):
            for j, s in enumerate(part):
                if got[j] != s:
                    fixed[s] = got[j]
            done += len(part)
            if done % (BATCH * 10) == 0 or done == len(keys):
                print(f"  {done:,}/{len(keys):,} · переписано {len(fixed):,}")

    if a.sample:
        for s, r in list(fixed.items())[:a.sample]:
            print(f"\n  было:  {s.strip()[:200]}")
            print(f"  стало: {r[:200]}")
        print(f"\nпереписано {len(fixed)} из {len(keys)} — это проба, ничего не записано")
        return 0

    if not a.apply:
        print("это сверка; --apply запишет")
        return 0

    # Пишем по файлам: один файл открываем и сохраняем один раз, сколько бы
    # предложений в нём ни правилось.
    by_file = {}
    for s, r in fixed.items():
        for p, tier, lang, k in where[s]:
            by_file.setdefault(p, []).append((tier, lang, k, s, r))
    n_files = 0
    for p, jobs in by_file.items():
        d = load(p)
        touched = False
        for tier, lang, k, s, r in jobs:
            v = (d.get(tier, {}) or {}).get(lang)
            if not isinstance(v, dict) or not isinstance(v.get(k), str):
                continue
            if s in v[k]:
                v[k] = v[k].replace(s, r)
                touched = True
        if touched:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            n_files += 1
    print(f"записано в {n_files:,} статей · предложений {len(fixed):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
