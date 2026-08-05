#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Уровень формулы: базовая / адаптация / расчётная.

ЗАМЫСЕЛ ВЛАДЕЛЬЦА (2026-08-05): различать не ВИД формулы, а её ПРИМЕНЕНИЕ.
  · базовая     — этой формулой ОПРЕДЕЛЯЮТ закон (уравнение Фридмана, второй закон Ньютона);
  · адаптация   — ею ПРИБЛИЖАЮТ закон к классу задач (слабое поле, изотропная среда,
                  линеаризация);
  · расчётная   — ею СЧИТАЮТ конкретную модель (подставлены значения, выбрана
                  параметризация: w(a)=w0+wa(1-a) — это уже параметризация, а не закон).

ПОЧЕМУ НЕ ПО ЛАТЕХУ. Граница проходит по применению, а не по записи: одна и та же
формула в одной статье определяет закон, в другой считает частный случай. Маркеры
(≈, численные коэффициенты, подстрочные eff/obs) помогают, но решают не они —
поэтому классифицирует модель, а не регулярка.

ПАЧКАМИ ПО 10. Один вызов на формулу — это 1218 обращений и около часа. Десять
за раз даёт 122 вызова и те же деньги.

РАССУЖДЕНИЯ ВЫКЛЮЧЕНЫ. Замер проекта: с ними лимит уходит в размышления и ответ
приходит пустой (я на этом уже обжёгся на проверке гипотезы аналогий).

    python formula_levels.py --run [--limit 100]
    python formula_levels.py --blind 50
"""
import json, pathlib, random, re, sys, time, argparse, collections
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
PACK = 10
SEED = 42

RUBRIC = """Ты классифицируешь формулы из научных статей по УРОВНЮ ПРИМЕНЕНИЯ.

Три уровня. Решает то, ЧТО формулой делают, а не как она выглядит:

1. "базовая" — формулой ОПРЕДЕЛЯЮТ закон или величину в общем виде.
   Уравнение Фридмана, второй закон Ньютона, определение энтропии.
   Признак: верна для целого класса систем, без выбора модели.

2. "адаптация" — формулой ПРИБЛИЖАЮТ закон к классу задач.
   Предел слабого поля, линеаризация, изотропный случай, разложение в ряд,
   асимптотика. Признак: назван режим или допущение, но не конкретные числа.

3. "расчётная" — формулой СЧИТАЮТ конкретную модель.
   Подставлены значения, выбрана параметризация (w(a)=w0+wa(1-a)), заданы
   численные коэффициенты, оценка для конкретного объекта или установки.
   Признак: результат зависит от выбора модели или параметров.

ЖЁСТКОЕ ОГРАНИЧЕНИЕ НА УРОВЕНЬ 1. Замер 2026-08-05: без него в "базовая" уходит
41% формул, а должно быть около 13%. "Базовая" — только если ОБА условия:
  а) формула была известна ДО этой статьи и имеет общепринятое имя
     (уравнение Шрёдингера, закон Стефана-Больцмана, определение энтропии);
  б) она не введена для нужд этой работы.
Формула, введённая В ЭТОЙ РАБОТЕ, — не базовая НИ ПРИ КАКИХ УСЛОВИЯХ, даже если
выглядит общей: оператор этой установки, вспомогательная величина этой модели,
обозначение, придуманное авторами. Такие — "расчётная".
Если в твоём собственном обосновании есть слова "для конкретной", "для данной",
"этой системы", "в этой работе" — уровень НЕ может быть "базовая".

Граница между 2 и 3 размыта. Правило на спорный случай: если названа
конкретная модель, параметризация или число — это "расчётная".

Отвечай ТОЛЬКО массивом JSON, по объекту на формулу, в том же порядке:
[{"n": 1, "level": "базовая|адаптация|расчётная", "why": "до 8 слов"}]
"""


def load_env():
    env = {}
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def formulas():
    p = DATA / "formulas.json"
    if not p.exists():
        p = MAIN / "data" / "formulas.json"
    return json.loads(p.read_text(encoding="utf-8"))


def deepseek(prompt, key, model="deepseek-v4-flash"):
    body = json.dumps({
        "model": model, "temperature": 0.1, "max_tokens": 2000,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d["choices"][0]["message"]["content"].strip()


def parse(txt, k):
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return None
    return arr if len(arr) == k else None


def run(limit):
    key = load_env().get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("нет DEEPSEEK_API_KEY")
    f = formulas()
    out_path = DATA / "formula-levels.json"
    done = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    items = [(k, v) for k, v in f.items() if k not in done]
    if limit:
        items = items[:limit]
    print(f"классифицировать: {len(items)} (готово {len(done)})")

    for i in range(0, len(items), PACK):
        ch = items[i:i + PACK]
        lines = []
        for n, (k, v) in enumerate(ch, 1):
            arts = v.get("articles") or []
            ctx = (arts[0].get("title") if arts else "") or ""
            lines.append(f'{n}. Формула: {v.get("latex","")[:300]}\n'
                         f'   Смысл: {(v.get("meaning") or "")[:300]}\n'
                         f'   Из статьи: {ctx[:120]}')
        txt = None
        for a in range(3):
            try:
                txt = deepseek(RUBRIC + "\n\n" + "\n".join(lines), key)
                break
            except Exception:
                time.sleep(2 ** a * 2)
        arr = parse(txt or "", len(ch))
        if not arr:
            print(f"  !! пачка {i//PACK+1}: разбор не удался, пропускаю")
            continue
        for (k, _), r in zip(ch, arr):
            lv = str(r.get("level", "")).strip().lower()
            if lv not in ("базовая", "адаптация", "расчётная", "расчетная"):
                continue
            done[k] = {"level": "расчётная" if lv.startswith("расч") else lv,
                       "why": str(r.get("why", ""))[:80]}
        if (i // PACK) % 10 == 0:
            out_path.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
            print(f"  {min(i+PACK, len(items))}/{len(items)}")
    out_path.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")

    dist = collections.Counter(v["level"] for v in done.values())
    print(f"\nклассифицировано: {len(done)} из {len(f)}")
    for k, v in dist.most_common():
        print(f"  {k}: {v} ({100*v/len(done):.1f}%)")
    print(f"файл: {out_path}")


def blind(n):
    lv = json.loads((DATA / "formula-levels.json").read_text(encoding="utf-8"))
    f = formulas()
    rnd = random.Random(SEED)
    keys = rnd.sample(sorted(lv), min(n, len(lv)))
    for k in keys:
        r, rec = lv[k], f.get(k, {})
        print(f"\n[{r['level']}] {r['why']}")
        print(f"  {(rec.get('latex') or k)[:95]}")
        print(f"  {(rec.get('meaning') or '')[:135]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--blind", type=int, default=0)
    a = ap.parse_args()
    if a.run: run(a.limit)
    elif a.blind: blind(a.blind)
    else: ap.print_help()
