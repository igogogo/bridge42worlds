# -*- coding: utf-8 -*-
"""Учёные на статье: логарифмическое глушение вместо «взять всех подряд».

ЧТО БЫЛО. Учёные не выбираются, а ВЫВОДЯТСЯ: берём всех, кого называют назначенные
статье законы и теги, объединяем и режем до шести (tools/tag_by_vector.py). Ни веса,
ни порядка — режется тем, что первым легло в список. Итог замером 25 августа:

    Альберт Эйнштейн   3685 статей из 6678 = 55.1% архива
    Алан Гут           2265 = 33.9%
    Адам Рисс          1619 = 24.2%
    в среднем 5.2 имени на статью

Имя, стоящее у каждой второй работы, не говорит ничего. Владелец 25 августа:
«Эйнштейна просто поменьше сделай, типа логарифмически, а то он везде будет —
только там, где прям без него никак».

ПОЧЕМУ ТАК ВЫШЛО. Две беды, и обе в реестре понятий (data/concepts.json):

  1. В среднем 12.7 имён на понятие. У `black_hole` их 127 — это весь наш список
     учёных целиком. Список АЛФАВИТНЫЙ, а не по значимости: Эйнштейн там третий
     только потому, что «Albert» рано сортируется. Порядок не несёт смысла.
  2. Знаменитые имена расползлись по чужим понятиям. Эйнштейн вписан в 127 понятий
     из 536, включая `convolutional_neural_networks`, `bayesian_inference` и `carbon`.
     К свёрточным сетям он отношения не имеет.

При этом точные записи в реестре есть и они хороши: у `laser` ровно одно имя —
Чарльз Таунс. Значит, чинить надо не реестр целиком, а способ читать его.

КАК СЧИТАЕМ. Логарифм стоит в двух местах, и оба раза он делает одно и то же —
гасит то, чего слишком много.

  точность понятия   prec(c) = 1 / ln(e + |учёных в c| - 1)
      понятие с одним именем — это атрибуция (1.00), со 127 именами — свалка (0.20).

  редкость имени     idf(s)  = ln(1 + N_понятий / сколько понятий называют s)
      имя из трёх понятий весит втрое больше имени из ста двадцати семи.

  вес места          1 / (1 + позиция)
      списки laws_vec/tags_vec упорядочены по близости (см. pick() в tag_by_vector),
      поэтому первое понятие статьи весит больше третьего.

  порода             закон 1.0, тег 0.7
      «закон знает своих авторов точнее, чем модель» — из tag_by_vector.

  вес(статья, имя) = idf(имя) × Σ по понятиям статьи, называющим имя:
                     порода × вес места × точность понятия

ПРАВИЛО ДВУХ ОПОР. Одного веса мало: маленькое, но насквозь неверное понятие
(`convolutional_neural_networks` — восемь имён, все не по делу) даёт редкому имени
достаточный вес. Поэтому имя остаётся, только если выполнено одно из двух:

    либо оно пришло из ТОЧНОГО понятия (названы единицы — это атрибуция, а не список),
    либо его подтвердили минимум ДВА разных понятия статьи.

Так `laser → Таунс` (одно понятие, одно имя) остаётся, а `свёрточные сети → Фарадей`
(одно понятие на восемь имён) уходит.

ЧТО ПОЛУЧАЕТСЯ (порог 0.45, до 4 имён, точным считаем понятие с ≤4 именами):

    Эйнштейн 55.1% → 3.2%, и остаётся ровно там, где без него никак: уравнения поля,
    принцип эквивалентности, гравитационное линзирование, эквивалентность массы и
    энергии, гравитационные волны.
    Имён на статью 5.2 → 2.8. Ни одно имя не стоит больше чем у 8.7% архива.
    РАЗНЫХ имён в ходу становится БОЛЬШЕ: 274 → 350. Прежний слепой срез по шестёрке
    выталкивал точные редкие имена ради знаменитых.
    Без учёных остаются 15% статей. Из них 3% неизбежны — у их понятий в реестре
    вообще нет учёных. Остальные честно пусты: все кандидаты были шумом.

ОТКАТ. Данные статей вне гита, поэтому прежние значения сохраняются в
data/scientists-prune-backup.jsonl. Вернуть: --restore.

ЧЕГО ЭТОТ ИНСТРУМЕНТ НЕ ДЕЛАЕТ. Он не чинит реестр. `carbon → Мария Кюри` останется
неверной записью, просто перестанет попадать в статьи. Чистка самого реестра — работа
на отдельный разговор: 466 понятий × 12.7 имён требуют суждения, а не арифметики.
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "lang" / "ru" / "archive"
REGISTRY = ROOT / "data" / "concepts.json"
BACKUP = ROOT / "data" / "scientists-prune-backup.jsonl"
LANGS = ("ru", "en", "es", "ar", "fr")
TIERS = ("simple", "popular", "advanced")


def load_registry():
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["concepts"]
    sci_of = {cid: (c.get("scientists") or []) for cid, c in reg.items()}
    n_concepts = sum(1 for v in sci_of.values() if v)
    cf = collections.Counter()
    for names in sci_of.values():
        for s in names:
            cf[s] += 1
    return sci_of, n_concepts, cf


class Scorer:
    def __init__(self, sci_of, n_concepts, cf):
        self.sci_of, self.n_concepts, self.cf = sci_of, n_concepts, cf

    def size(self, cid):
        return len(self.sci_of.get(cid) or [])

    def prec(self, cid):
        n = self.size(cid)
        return 1.0 / math.log(math.e + max(0, n - 1)) if n else 0.0

    def idf(self, name):
        return math.log(1 + self.n_concepts / max(1, self.cf[name]))

    def rank(self, laws, tags):
        """Веса и опоры всех кандидатов одной статьи."""
        score = collections.defaultdict(float)
        support = collections.defaultdict(list)
        for names, kind_w in ((laws, 1.0), (tags, 0.7)):
            for pos, cid in enumerate(names):
                w = kind_w * (1.0 / (1 + pos)) * self.prec(cid)
                if not w:
                    continue
                for s in self.sci_of.get(cid) or []:
                    score[s] += w
                    support[s].append(cid)
        for s in score:
            score[s] *= self.idf(s)
        return score, support

    def keep(self, laws, tags, floor, top, precise):
        score, support = self.rank(laws, tags)
        out = []
        for s, x in sorted(score.items(), key=lambda kv: (-kv[1], kv[0])):
            if len(out) >= top:
                break
            if x < floor:
                break                      # список отсортирован — дальше только меньше
            # правило двух опор: точное понятие ИЛИ подтверждение вторым понятием
            if min(self.size(c) for c in support[s]) <= precise or len(support[s]) >= 2:
                out.append(s)
        return out


def articles():
    for p in sorted(ARCHIVE.glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        v = (d.get("popular", {}) or {}).get("ru") or (d.get("simple", {}) or {}).get("ru") or {}
        if not isinstance(v, dict):
            continue
        yield p, d, v


def write_all(d, names):
    """Кладём во ВСЕ уровни и языки — как это делает tag_by_vector.

    Учёные это идентификаторы, они общие для языков: страница подставит перевод имени.
    Записать только в русский значило бы получить сайт, где русская версия размечена
    по-новому, а арабская по-старому — расхождение, которого никто не заметит."""
    for tier in TIERS:
        for lang in LANGS:
            v = (d.get(tier, {}) or {}).get(lang)
            if isinstance(v, dict):
                v["scientists_vec"] = list(names)


def main():
    ap = argparse.ArgumentParser(description="Логарифмическое глушение учёных на статьях")
    ap.add_argument("--floor", type=float, default=0.45, help="порог веса (по умолчанию 0.45)")
    ap.add_argument("--top", type=int, default=4, help="сколько имён максимум на статью")
    ap.add_argument("--precise", type=int, default=4,
                    help="понятие с таким числом имён и меньше считаем точной атрибуцией")
    ap.add_argument("--apply", action="store_true", help="записать в данные статей")
    ap.add_argument("--restore", action="store_true", help="вернуть прежние значения из отката")
    ap.add_argument("--show", metavar="ID", help="разобрать одну статью по косточкам")
    args = ap.parse_args()

    if args.restore:
        if not BACKUP.exists():
            print("отката нет:", BACKUP)
            return 1
        old = {}
        for line in BACKUP.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                old[r["id"]] = r["old"]
        n = 0
        for p, d, _ in articles():
            if p.parent.name in old:
                write_all(d, old[p.parent.name])
                p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                n += 1
        print(f"возвращено прежних значений: {n}")
        return 0

    sci_of, n_concepts, cf = load_registry()
    sc = Scorer(sci_of, n_concepts, cf)
    print(f"реестр: {len(sci_of)} понятий, из них с учёными {n_concepts}; "
          f"разных имён {len(cf)}")
    print(f"настройка: порог {args.floor} · до {args.top} имён · "
          f"точным считаем понятие с ≤{args.precise} именами")

    if args.show:
        for p, d, v in articles():
            if p.parent.name != args.show:
                continue
            laws, tags = v.get("laws_vec") or [], v.get("tags_vec") or []
            score, support = sc.rank(laws, tags)
            keep = set(sc.keep(laws, tags, args.floor, args.top, args.precise))
            print(f"\n{v.get('title', '')}")
            print(f"  законы: {', '.join(laws) or '—'}")
            print(f"  теги:   {', '.join(tags) or '—'}")
            print(f"  было:   {', '.join(v.get('scientists_vec') or []) or '—'}")
            print("  разбор (✓ — остаётся):")
            for s, x in sorted(score.items(), key=lambda kv: -kv[1])[:14]:
                least = min(sc.size(c) for c in support[s])
                print(f"   {'✓' if s in keep else ' '} {x:5.2f}  {s:<28} "
                      f"опор {len(support[s])}, наименьшее понятие на {least} имён")
            return 0
        print("статья не найдена")
        return 1

    was = collections.Counter()
    now = collections.Counter()
    rows = []
    empty_before = empty_after = 0
    for p, d, v in articles():
        old = list(v.get("scientists_vec") or [])
        new = sc.keep(v.get("laws_vec") or [], v.get("tags_vec") or [],
                      args.floor, args.top, args.precise)
        for s in old:
            was[s] += 1
        for s in new:
            now[s] += 1
        empty_before += not old
        empty_after += not new
        rows.append((p, d, p.parent.name, old, new))

    n = len(rows)
    print(f"\nстатей: {n}")
    print(f"имён на статью: {sum(len(o) for *_, o, _ in rows) / n:.1f} → "
          f"{sum(len(x) for *_, x in rows) / n:.1f}")
    print(f"без учёных: {empty_before} → {empty_after} ({100 * empty_after / n:.1f}%)")
    print(f"разных имён в ходу: {len(was)} → {len(now)}")
    print("\nбыло → стало, по самым частым именам:")
    for s, k in was.most_common(12):
        print(f"  {s:<28} {k:5d} ({100 * k / n:4.1f}%) → {now[s]:4d} ({100 * now[s] / n:4.1f}%)")
    print("\nновый порядок по охвату:")
    for s, k in now.most_common(8):
        print(f"  {s:<28} {k:5d} ({100 * k / n:4.1f}%)")

    if not args.apply:
        print("\nэто сверка — ничего не записано; --apply запишет и сделает откат")
        return 0

    with BACKUP.open("w", encoding="utf-8") as fh:
        for _, _, aid, old, _ in rows:
            fh.write(json.dumps({"id": aid, "old": old}, ensure_ascii=False) + "\n")
    print(f"\nоткат записан: {BACKUP.relative_to(ROOT)} ({len(rows)} строк)")

    changed = 0
    for p, d, _, old, new in rows:
        if old == new:
            continue
        write_all(d, new)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        changed += 1
    print(f"переписано статей: {changed}")
    print("на сайте появится после пересборки и заливки связей в облако")
    return 0


if __name__ == "__main__":
    sys.exit(main())
