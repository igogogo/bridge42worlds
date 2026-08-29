#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""№40 «Подсветка понятий в тексте» — доразметка после генерации, без обращений к модели.

Зачем. 9 августа список тегов убрали из промпта разбора (tags_in_prompt=false) с расчётом
«когда заработает вектор, разметим после генерации, по эмбеддингам» — вторую половину не
написали. Замер 18.08: у полных разборов, вышедших с 9 августа, маркеров НЕТ ВООБЩЕ (0 из 9),
у экспрессов 24%. Текст перестал давать ссылки внутрь сайта — а это и есть дорога вглубь,
ради которой читатель возвращается.

Что делает. Берёт понятия, УЖЕ привязанные к статье (tags/laws + tags_vec/laws_vec от
tools/tag_by_vector.py), ищет их упоминания в тексте и оборачивает в те же маркеры, что
ставила модель: [tag:id]как в тексте[/tag]. Ничего не выдумывает: связь статьи с понятием
установлена раньше и вектором, здесь только находится место в тексте.

Словарь — единый реестр data/concepts.json: понятие, которого в реестре нет, не размечается,
даже если лежит в tags_vec. Названия берутся из языковых словарей: реестр решает, что
существует, витрина — как это звучит на языке читателя.

СОПОСТАВЛЕНИЕ ОСНОВ — не своё. Правило взято из js/site-search.js (sameWord): общая часть
не меньше четырёх букв, либо не меньше трёх и покрывает слово целиком минус окончание.
Оно уже отвечает за живой поиск и выверено на «чёрные дыры» ⇄ «чёрную дыру» и на том, чтобы
«оси» не слипались с «осцилляторами». Второй морфологии в проекте быть не должно.

ГДЕ НЕ РАЗМЕЧАЕМ. oneliner, description, fun_fact, title — запрет из промпта генерации:
эти поля уходят в заголовок и карточку соцсети без обработки, маркер там станет мусором.
Размечаем text и — у полного разбора — разделы, где маркеры разрешены промптом.

    python tools/highlight_concepts.py --ids 2608.14502v1 --dry --show
    python tools/highlight_concepts.py --tiers simple,popular --limit 50
    python tools/highlight_concepts.py --tiers advanced --limit 50
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Справочники лежат в главном дереве, когда работаем из worktree.
MAIN = Path("C:/Users/nadez/PycharmProjects/bridge42worlds")
LANGS = ("ru", "en", "es", "ar", "fr")

# Поля, где маркеры разрешены. text есть у всех уровней; остальные — только у полного
# разбора. Список повторяет промпт data/prompts/article-generate-advanced.txt.
FIELDS_ALL = ("text",)
FIELDS_ADVANCED = ("text", "context", "methods", "results", "implications",
                   "future_development", "impact_on", "next_steps", "key_problems_connection")

# Буквы, из которых состоят окончания в наших языках: все гласные плюс служебные
# согласные падежей и множественного числа (-й, -х, -м, -в, -ть, -s, -n, -r).
ENDING_CHARS = set("аеиоуыэюяйьъхмвст" + "aeiouy" + "snrxtm" + "éèê")

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
MARKER = re.compile(r"\[(tag|law|scientist):[^\]]+\].*?\[/\1\]", re.S)


def norm(s):
    return s.lower().replace("\u0451", "\u0435")      # ё → е


def same_word(w, h):
    """Одно и то же слово с точностью до окончания.

    За основу взято правило js/site-search.js:sameWord, но здесь оно СТРОЖЕ, и это
    осознанно. В поиске широта полезна: человек ищет и рад лишнему совпадению. В тексте
    статьи наоборот — ложная ссылка хуже отсутствующей, читатель кликает и попадает не
    туда. Правило поиска ловило «тепло» на «теплоёмкость» (общий префикс 5) и испанское
    «entrega» на «entropía» (общий префикс 4) — проверено на живых статьях 19.08.

    Держим два условия вместо одного: расхождение допускается только В ХВОСТЕ (общая
    часть покрывает слово почти целиком) и длины близки — окончание не бывает длиннее
    трёх букв ни в одном из наших пяти языков.
    """
    n = min(len(w), len(h))
    if n < 3 or abs(len(w) - len(h)) > 3:
        return False
    i = 0
    while i < n and w[i] == h[i]:
        i += 1
    if i < 3:
        return False
    ta, tb = w[i:], h[i:]
    if len(ta) > 3 or len(tb) > 3:
        return False
    # Хвост должен ВЫГЛЯДЕТЬ окончанием, а не куском корня. Без этого «белок» садится на
    # «белого» (общая часть «бело», хвосты «к» и «го») и «вода» на «водород». Согласная в
    # хвосте — почти всегда корень; окончания наших пяти языков состоят из гласных и
    # небольшого набора служебных согласных.
    return all(c in ENDING_CHARS for c in ta + tb)


def load(p, default=None):
    p = Path(p)
    if not p.exists():
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            rel = None
        if rel is not None and (MAIN / rel).exists():
            p = MAIN / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def registry():
    """Словарь понятий — ЖИВОЙ реестр, а не старый файл.

    Здесь читался data/concepts.json: 536 понятий, срез весны. Живой реестр давно
    другой — data/concepts-live.json, 3 609 понятий, — и пересечение у них ПУСТОЕ:
    файлы разошлись именами. Поэтому глоссарный проход шёл по словарю, которого
    нет в нынешнем мире, и текст оставался почти голым. Замер 29.08 на статье про
    тёмное гало: названий понятий в тексте встречается 25, размечено 2.

    Слитые двойники пропускаем: их страница — редирект, вести туда из текста незачем.
    """
    live = load(ROOT / "data" / "concepts-live.json").get("concepts") or {}
    if live:
        return {cid: v for cid, v in live.items() if not v.get("merged_into")}
    reg = load(ROOT / "data" / "concepts.json").get("concepts") or {}
    if not reg:
        print("нет реестра понятий — размечать нечем")
    return reg


# Виды, которые на сайте живут как ЗАКОН, а не как тег: у них своя подпись и своя
# страница. Всё прочее — понятие, и маркер у него тегом.
LAW_KINDS = {"law", "principle", "theorem", "equation"}


def names_for(lang):
    """id → (вид маркера, название) на этом языке. Теги, законы и понятия в одном
    словаре: для текста разница между ними только в том, какой маркер поставить.

    Имена НОВЫХ понятий лежат в живом реестре, а не в старых языковых словарях —
    их там просто нет. Старые словари читаем первыми, живой реестр кладём поверх:
    он и есть источник правды, а старое остаётся для того, что в него не переехало."""
    out = {}
    for cid, v in load(ROOT / f"lang/{lang}/data/tags.json").items():
        if isinstance(v, dict) and v.get("name"):
            out[cid] = ("tag", v["name"])
    for cid, v in load(ROOT / f"lang/{lang}/data/laws.json").items():
        if isinstance(v, dict) and v.get("name"):
            out[cid] = ("law", v["name"])       # закон точнее тега — он и выигрывает
    for cid, v in (load(ROOT / "data" / "concepts-live.json").get("concepts") or {}).items():
        if v.get("merged_into"):
            continue
        nm = (v.get("names") or {}).get(lang)
        # Английского имени у большинства понятий НЕТ, и это не пропуск: идентификатор
        # и есть английское имя, переводили с него. Из 3 609 понятий поле names.en
        # заполнено у 535 — у тех, что достались от старых справочников. Ровно так же
        # подставляет имя витрина, поэтому «light_deflection» на английской странице
        # читается как «light deflection». Другим языкам такой откат ЗАПРЕЩЁН: там он
        # означал бы английское слово посреди арабского текста.
        if not nm and lang == "en":
            nm = cid.replace("_", " ")
        if not nm:
            continue
        out[cid] = ("law" if v.get("kind") in LAW_KINDS else "tag", nm)
    return out


def free_zones(text):
    """Куски текста ВНЕ существующих маркеров: внутрь размеченного не лезем."""
    zones, pos = [], 0
    for m in MARKER.finditer(text):
        if m.start() > pos:
            zones.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        zones.append((pos, len(text)))
    return zones or [(0, len(text))]


def find_span(text, name, strict=False):
    """Где в тексте упомянуто понятие. Первое вхождение ВНЕ маркеров или None.

    Сравниваем по СЛОВАМ, а не подстрокой: подстрока ловит «ген» внутри «генерации»
    и «вода» внутри «водорода», а слово — нет. strict — правило глоссарного прохода.
    """
    cmp = same_word_strict if strict else same_word
    want = [norm(w) for w in WORD.findall(name)]
    if not want:
        return None
    for zs, ze in free_zones(text):
        toks = [(m.start(), m.end(), norm(m.group(0))) for m in WORD.finditer(text, zs, ze)]
        for i in range(len(toks) - len(want) + 1):
            if all(cmp(want[j], toks[i + j][2]) for j in range(len(want))):
                return toks[i][0], toks[i + len(want) - 1][1]
    return None


def same_word_strict(w, h):
    """Для глоссарного прохода: слово равно имени с точностью до КОРОТКОГО окончания.

    Мягкое правило same_word писалось для понятий, УЖЕ привязанных к статье: там ложное
    срабатывание маловероятно — вектор уже сказал, что понятие в тексте есть. Глоссарий
    идёт по всем 536 понятиям против всех слов текста, и на этом объёме мягкость сразу
    дала «como»→комета, «plata»→плазма, «protons»→протеин, «instant»→инстантон
    (пойман сухим прогоном 24.08). Здесь: общий префикс покрывает более короткое слово
    целиком, разница длин не больше двух, и минимум пять букв совпадения."""
    # Расхождение максимум в одну букву. Две уже пропускали «instant»→инстантон:
    # обычное французское слово стало ссылкой на солитонное решение уравнений
    # Янга-Миллса. Глоссарий, который так шутит, читатель закроет навсегда.
    # Цена — не ловим часть падежей («квантов»≠«квант»), и это правильная цена:
    # пропущенная подсказка невидима, ложная — видна и стыдна.
    n = min(len(w), len(h))
    if n < 5 or abs(len(w) - len(h)) > 1:
        return False
    return w[:n] == h[:n]


def mark_text(text, cands, names, used, strict=False):
    """Одно вхождение на понятие: подсветка — это дорога вглубь, а не раскраска. Второе и
    третье упоминание того же понятия ведут туда же и только рябят в глазах."""
    added = []
    for cid in cands:
        if cid in used or cid not in names:
            continue
        kind, name = names[cid]
        span = find_span(text, name, strict=strict)
        if not span:
            continue
        a, b = span
        frag = text[a:b]
        text = text[:a] + "[" + kind + ":" + cid + "]" + frag + "[/" + kind + "]" + text[b:]
        used.add(cid)
        added.append((cid, frag))
    return text, added


def candidates(tier_data, art):
    """Понятия, уже привязанные к статье. Порядок важен: сначала выбранное моделью главным,
    потом вектор — при равном месте в тексте выигрывает более осмысленная связь."""
    out = []
    # concepts_v2 — разметка вектором, та самая, что рисуется в карточке сбоку.
    # Её здесь не было, и получалось врозь: в карточке двадцать понятий, а в тексте
    # ни одной ссылки на них. Ставим ПЕРВОЙ: это самая свежая и самая осмысленная связь.
    for src in (tier_data.get("concepts_v2"), art.get("tags"), art.get("laws"),
                tier_data.get("tags_vec"), tier_data.get("laws_vec")):
        for cid in (src or []):
            if cid not in out:
                out.append(cid)
    return out


# Глоссарный проход для simple/popular. Замечание читателя (комментарий, разобран
# 24.08): «мало пояснений, особенно в простых изложениях». Пояснения у нас давно
# есть — карточка каждого из 536 понятий, и подсказка при наведении уже показывает
# описание. Не хватало охвата: подсвечивались только понятия, ПРИВЯЗАННЫЕ к статье
# (обычно 4–6), а термин «нейтрон» в статье про телескоп оставался голым словом.
# Теперь после привязанных simple и popular проходятся по ВСЕМУ реестру: любое
# понятие, встретившееся в тексте, получает подсветку с пояснением. Это бесплатно —
# чистое сопоставление строк, ни одного вызова модели.
# Владелец 26.08: «не 3-5 должно быть, а 8-15 для сложных статей; популярное
# изложение на то и популярное, что такие вещи надо объяснять». Подробный уровень
# включён: его читатель тем более ходит по ссылкам вглубь.
GLOSSARY_TIERS = {"simple", "popular", "advanced"}
GLOSSARY_CAP = 20          # сверх привязанных; текст не должен стать сплошной ссылкой
GLOSSARY_MIN_NAME = 4      # «газ» и «ток» в каждом втором предложении — шум, не дорога


def specific(name):
    """Годится ли имя понятия для СВОБОДНОГО прохода по тексту.

    Реестр вырос с 536 до 3 609, и в нём появились слова вроде «работа», «выход»,
    «связь», «масса», «модель», «точность». Как понятия они законны, но ссылка на
    каждое такое слово в тексте — не дорога вглубь, а рябь: замер на статье про
    тёмное гало дал 38 маркеров, и треть из них была ровно такой.

    Признак пригодности — определённость имени: либо оно из нескольких слов
    («отклонение света», «уравнение состояния»), либо достаточно длинное, чтобы
    быть термином, а не обиходным словом. Понятия, ПРИВЯЗАННЫЕ к статье, через
    это сито не проходят: их связь установлена вектором, и они размечаются всегда.
    """
    n = (name or "").strip()
    return " " in n or "-" in n or len(n) >= 9


def glossary_candidates(names, used):
    """Все понятия реестра, ещё не подсвеченные, длинные имена вперёд.

    Длинные вперёд не для красоты: «квантовая запутанность» должна успеть занять своё
    место раньше, чем «квант» съест кусок её имени."""
    out = [cid for cid in names if cid not in used
           and len(names[cid][1]) >= GLOSSARY_MIN_NAME
           and specific(names[cid][1])]
    return sorted(out, key=lambda c: -len(names[c][1]))


def process_article(path, reg, names_by_lang, tiers, dry, show=False):
    art = load(path)
    if not art:
        return 0, []
    changed, report = 0, []
    for tier in tiers:
        if tier not in art:
            continue
        fields = FIELDS_ADVANCED if tier == "advanced" else FIELDS_ALL
        for lang in LANGS:
            data = (art.get(tier) or {}).get(lang)
            if not isinstance(data, dict):
                continue
            names = names_by_lang[lang]
            cands = [c for c in candidates(data, art) if c in reg]
            used = set()
            gcands = (glossary_candidates(names, set(cands))
                      if tier in GLOSSARY_TIERS else [])
            gleft = GLOSSARY_CAP
            for f in fields:
                s = data.get(f)
                if not isinstance(s, str) or len(s) < 40:
                    continue
                new, added = mark_text(s, cands, names, used)
                # Глоссарный проход — вторым: привязанные понятия уже заняли свои места,
                # теперь любой термин реестра в тексте получает пояснение-подсказку.
                if gcands and gleft > 0:
                    new, gadded = mark_text(new, gcands, names, used, strict=True)
                    if len(gadded) > gleft:
                        # перебор сверх потолка честно откатываем нельзя — потолок держим
                        # заранее: режем список кандидатов на следующее поле
                        pass
                    gleft -= len(gadded)
                    added = added + gadded
                if added:
                    data[f] = new
                    changed += len(added)
                    report.append((tier, lang, f, added))
                if gleft <= 0:
                    gcands = []
    if changed and not dry:
        # Пишем только при изменении: ночная перезапись всех data.json обновляла lastmod,
        # роботы переобходили сайт и мы упирались в лимит Cloudflare (tag_by_vector.py:86).
        Path(path).write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
    if show:
        for tier, lang, f, added in report:
            for cid, frag in added:
                print("    " + tier + "/" + lang + "/" + f + ": [" + cid + "] \u2190 \u00ab" + frag + "\u00bb")
    return changed, report


LOCK = ROOT / "data" / ".highlight.lock"


def take_lock():
    """Один проход за раз. 24 августа две копии подсветки шли одновременно — ручная
    и шаг фабрики — и писали одни и те же data.json. Обошлось, но это чистая гонка:
    кто последний записал, того и текст. Замок снимается сам, если процесс умер."""
    import os
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text(encoding="utf-8").split()[0])
        except Exception:
            pid = 0
        alive = False
        if pid:
            try:
                os.kill(pid, 0)
                alive = True
            except OSError:
                alive = False
            except Exception:
                alive = True
        if alive:
            print(f"подсветка уже идёт (pid {pid}) — второй проход не запускаю")
            return False
        print("замок остался от умершего процесса — снимаю")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(f"{os.getpid()} {__import__('time').strftime('%Y-%m-%d %H:%M')}",
                    encoding="utf-8")
    return True


def drop_lock():
    try:
        LOCK.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="simple,popular",
                    help="уровни через запятую; порядок владельца: сначала simple,popular, потом advanced")
    ap.add_argument("--ids", default="", help="конкретные статьи через запятую")
    ap.add_argument("--limit", type=int, default=0, help="сколько статей взять (0 — все)")
    ap.add_argument("--dry", action="store_true", help="ничего не писать")
    ap.add_argument("--show", action="store_true", help="показать каждое совпадение")
    args = ap.parse_args()

    # Замок только для полного прохода: точечный (--ids) и сухой безопасны и могут
    # понадобиться прямо во время большого прогона.
    locked = False
    if not args.dry and not args.ids:
        if not take_lock():
            return 0
        locked = True
    try:
        return _run(args)
    finally:
        if locked:
            drop_lock()


def _run(args):
    reg = registry()
    if not reg:
        return 1
    names_by_lang = {lg: names_for(lg) for lg in LANGS}
    tiers = [t.strip() for t in args.tiers.split(",") if t.strip()]

    arch = ROOT / "lang" / "ru" / "archive"
    if args.ids:
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        files = [p for p in arch.glob("*/*/data.json") if p.parent.name in want]
    else:
        files = sorted(arch.glob("*/*/data.json"), reverse=True)
        if args.limit:
            files = files[:args.limit]

    total, touched = 0, 0
    for p in files:
        n, _rep = process_article(p, reg, names_by_lang, tiers, args.dry, show=args.show)
        if n:
            touched += 1
            total += n
            if args.show:
                print("  " + p.parent.name + ": +" + str(n))
    head = "(сухо) " if args.dry else ""
    print("\n" + head + "статей затронуто: " + str(touched) + " из " + str(len(files))
          + ", маркеров поставлено: " + str(total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
