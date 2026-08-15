#!/usr/bin/env python3
"""Чинит связность графа: учёный ⇄ закон ⇄ тег. Кодом, без единого вызова модели.

Что было не так (нашёл владелец 2026-08-08: «проверь ещё Планка, почему у него нет связей
с законом Планка, странно»).

  · У ВСЕХ 201 учёного поле tags пустое. Страница учёного строит связи по тегам — значит
    связей нет ни у кого, и Планк тут не исключение, а правило. При этом данные для связи
    давно лежат рядом: теги есть у законов, где учёный числится, и у статей, где он упомянут.

  · 69 имён в законах не совпадают ни с одним ключом справочника — 72 упоминания в пустоту.
    Шесть из них просто записаны по-русски: «Макс Планк» при существующем «Max Planck»,
    «Альберт Эйнштейн» при «Albert Einstein». Закон излучения Планка ссылался на Планка
    так, что связь не сходилась по ключу.

Чиним обе беды одним проходом и обязательно ОБРАТИМО: сперва --check показывает, что
изменится, и только потом запись.

    python tools/graph_repair.py --check     посмотреть, ничего не трогая
    python tools/graph_repair.py             починить
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LANGS = ["ru", "en", "es", "ar", "fr"]
# Сколько тегов держим у учёного. Больше — боковая колонка превращается в простыню,
# и по ней уже не видно, чем человек занимался.
MAX_TAGS = 12

# Кириллические написания имён, у которых есть английский ключ в справочнике. Ручной
# словарь, а не транслитерация: «Макс Планк» → «Maks Plank» не совпадёт ни с чем, а
# фамилии учёных пишутся исторически (Эйлер → Euler, Мёссбауэр → Mössbauer).
RU_TO_KEY = {
    "Макс Планк": "Max Planck",
    "Альберт Эйнштейн": "Albert Einstein",
    "Леонард Эйлер": "Leonhard Euler",
    "Пифагор": "Pythagoras",
    "Евклид": "Euclid",
    "Исаак Ньютон": "Isaac Newton",
    "Нильс Бор": "Niels Bohr",
    "Эрвин Шрёдингер": "Erwin Schrödinger",
    "Поль Дирак": "Paul Dirac",
    "Вернер Гейзенберг": "Werner Heisenberg",
    "Джеймс Максвелл": "James Clerk Maxwell",
    "Людвиг Больцман": "Ludwig Boltzmann",
    "Мария Кюри": "Marie Curie",
    "Энрико Ферми": "Enrico Fermi",
    "Ричард Фейнман": "Richard Feynman",
}



# Пишем ФАЙЛ ТОЛЬКО ЕСЛИ СОДЕРЖИМОЕ ИЗМЕНИЛОСЬ — см. подробное объяснение в
# tools/tag_by_vector.py: ночная перезапись всех 5 245 data.json обновляла дату правки,
# карта сайта сообщала «изменился весь сайт», и роботы каждый день переобходили всё
# заново. Именно это, а не сами боты, упёрло нас в предел бесплатного тарифа Cloudflare.
def _save_if_changed(path, data, indent=1):
    new = json.dumps(data, ensure_ascii=False, indent=indent)
    try:
        if path.read_text(encoding="utf-8") == new:
            return False
    except Exception:
        pass
    path.write_text(new, encoding="utf-8")
    return True


def _norm(s):
    """Имя к сравнимому виду: без диакритики, регистра и лишних пробелов.

    Нужно, потому что одного человека пишут и «Erwin Schrödinger», и «Erwin Schrodinger»,
    и «E. Schrödinger». Сравнение сырых строк такие пары не ловит.
    """
    s = unicodedata.normalize("NFKD", (s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).lower()


def _surname(s):
    parts = [p for p in re.split(r"[\s.]+", _norm(s)) if len(p) > 1]
    return parts[-1] if parts else ""


def match_scientist(name, known):
    """Имя из закона → ключ справочника. Возвращает ключ или ''.

    Три попытки по убыванию строгости: точное совпадение, нормализованное (без диакритики),
    по фамилии — если фамилия в справочнике одна-единственная. Однофамильцев НЕ склеиваем:
    ошибиться человеком хуже, чем оставить связь несделанной.
    """
    if name in known:
        return name
    if name in RU_TO_KEY and RU_TO_KEY[name] in known:
        return RU_TO_KEY[name]
    n = _norm(name)
    by_norm = {_norm(k): k for k in known}
    if n in by_norm:
        return by_norm[n]
    sur = _surname(name)
    if sur:
        hits = [k for k in known if _surname(k) == sur]
        # Совпадения фамилии МАЛО. Проверка --check поймала на этом две пары: «Johann
        # Bernoulli → Daniel Bernoulli» и «Pierre Curie → Marie Curie» — родственники,
        # а не один человек. Приписать закон не тому учёному хуже, чем не приписать
        # никому: ошибку в справочнике потом никто не найдёт. Поэтому требуем ещё и
        # совпадения первой буквы имени: «R. K. Sachs → Rainer Sachs» проходит,
        # «Pierre → Marie» нет.
        first = _norm(name).split(" ")[0][:1]
        hits = [k for k in hits if _norm(k).split(" ")[0][:1] == first]
        if len(hits) == 1:
            return hits[0]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="показать, ничего не записывая")
    args = ap.parse_args()

    sci_p = ROOT / "lang" / "ru" / "data" / "scientists.json"
    laws_p = ROOT / "lang" / "ru" / "data" / "laws.json"
    sci = json.loads(sci_p.read_text(encoding="utf-8"))
    laws = json.loads(laws_p.read_text(encoding="utf-8"))
    known = set(sci.keys())

    # ── 1. Имена в законах приводим к ключам справочника ─────────────────────
    fixed, orphan = {}, {}
    for lid, L in laws.items():
        names = L.get("scientists") or []
        new = []
        for nm in names:
            if nm in known:
                new.append(nm)
                continue
            key = match_scientist(nm, known)
            if key:
                fixed.setdefault(nm, key)
                new.append(key)
            else:
                orphan.setdefault(nm, []).append(lid)
                new.append(nm)          # не выбрасываем: имя может быть верным, просто
                                        # человека нет в справочнике — это отдельная задача
        L["scientists"] = list(dict.fromkeys(new))

    print(f"имён приведено к справочнику: {len(fixed)}")
    for a, b in list(fixed.items())[:12]:
        print(f"   · {a}  →  {b}")
    print(f"имён, которых нет в справочнике: {len(orphan)} (связи повиснут, нужен top-up)")
    for nm, lids in list(orphan.items())[:8]:
        print(f"   · {nm}  ({', '.join(lids[:2])})")

    # ── 2. Теги учёным — из законов и из статей ──────────────────────────────
    # Учёный получает теги тех законов, где он числится, и тех статей, где он упомянут.
    # Ничего не выдумываем: берём то, что уже размечено и оплачено.
    from collections import Counter
    per_sci = {k: Counter() for k in sci}
    for lid, L in laws.items():
        for nm in (L.get("scientists") or []):
            if nm in per_sci:
                for t in (L.get("tags") or []):
                    per_sci[nm][t] += 3     # закон — прямая связь, вес выше

    idx_p = ROOT / "lang" / "ru" / "articles-index.json"
    if idx_p.exists():
        idx = json.loads(idx_p.read_text(encoding="utf-8"))
        for a in idx:
            for nm in (a.get("scientists") or []):
                if nm in per_sci:
                    for t in (a.get("tags") or [])[:8]:
                        per_sci[nm][t] += 1
    else:
        print("⚠️ нет articles-index.json — теги только из законов")

    filled = 0
    for k, cnt in per_sci.items():
        if not cnt:
            continue
        sci[k]["tags"] = [t for t, _ in cnt.most_common(MAX_TAGS)]
        filled += 1
    print(f"\nучёных получили теги: {filled} из {len(sci)}")
    ex = next((k for k in ("Max Planck", "Albert Einstein") if sci.get(k, {}).get("tags")), "")
    if ex:
        print(f"   пример — {ex}: {', '.join(sci[ex]['tags'][:6])}")

    if args.check:
        print("\n[проверка] ничего не записано")
        return 0

    laws_p.write_text(json.dumps(laws, ensure_ascii=False, indent=1), encoding="utf-8")
    sci_p.write_text(json.dumps(sci, ensure_ascii=False, indent=1), encoding="utf-8")
    # Остальные языки: теги — идентификаторы, они общие; переносим их, не трогая переводы имён.
    for lang in LANGS:
        if lang == "ru":
            continue
        for name, src in (("scientists.json", sci), ("laws.json", laws)):
            p = ROOT / "lang" / lang / "data" / name
            if not p.exists():
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for k, v in d.items():
                if k in src and isinstance(v, dict):
                    if src[k].get("tags"):
                        v["tags"] = src[k]["tags"]
                    if src[k].get("scientists"):
                        v["scientists"] = src[k]["scientists"]
            _save_if_changed(p, d)
    print("\n✅ записано. Дальше: run.py html — страницы подхватят связи")
    return 0


if __name__ == "__main__":
    sys.exit(main())
