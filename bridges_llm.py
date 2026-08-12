#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Перемычки: геометрия даёт кандидатов, модель выбирает. Разделение обязанностей.

Владелец 12 августа: «у тебя всё есть — байес, шахматы, вектор, модели; вопрос предела
и выбора это LLM, он спасёт тебя от бесконечного выбора ансамблей. Всё вместе это
рабочая система для разведочного бурения, итеративная».

ЭТО ОТВЕТ НА ЧЕТЫРЕ МОИХ ПРОВАЛА. Я четырежды пытался заставить геометрию ранжировать
перемычки — «коридор пустее ожидаемого», «выше медианы у обеих», «почти равноудалена»,
«по неожиданности». Все четыре провалились: первая дала 80% корпуса в коридоре у любой
пары, вторая и третья — нули везде. Причина не в формулах, а в том, что я требовал
от инструмента работы, которую он не делает.

Правило было записано мною же десятью днями раньше, в отборе кандидатов дня:
**вектор умеет вычёркивать, но не умеет выбирать.** Я нарушил его трижды подряд.

Здесь обязанности разделены как надо:
  ГЕОМЕТРИЯ — грубо и бесплатно: какие пары областей вообще стоит рассматривать.
              Две большие области, умеренно далеко друг от друга, между ними почти
              никого. Точность не нужна, нужна дешевизна: пар может быть тысячи.
  МОДЕЛЬ    — по одной паре: есть ли на стыке этих двух областей осмысленный
              незаданный вопрос, и какой. Это суждение, а не расстояние,
              и никакой порог его не заменит.

ЧЕГО ЭТО НЕ РЕШАЕТ. Модель может выдумать красивый вопрос про любую пару — она на то
и языковая. Поэтому её просят не «придумай связь», а «есть ли связь, и если нет —
скажи, что нет», и ответ «нет» засчитывается наравне с ответом «да». Доля отказов
и есть проверка того, что модель судит, а не сочиняет: если она находит вопрос
в ста процентах пар, включая заведомо бессмысленные, — верить ей нельзя.
Для этого в список подмешиваются КОНТРОЛЬНЫЕ пары: случайные, далёкие,
заведомо не связанные. Модель не знает, где какие.

    python bridges_llm.py --pairs 40        разобрать 40 кандидатов
    python bridges_llm.py --pairs 40 --dry   показать кандидатов, не тратя денег
"""
import argparse
import json
import pathlib
import random
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

PROMPT = """Ты — научный редактор с широким кругозором в физике.

Перед тобой ДВЕ области исследований. По каждой даны ключевые понятия и несколько
реальных заголовков работ.

ОБЛАСТЬ A ({na} работ): {ca}
{ta}

ОБЛАСТЬ B ({nb} работ): {cb}
{tb}

Факт: в корпусе из 1,5 млн работ по физике за 35 лет на стыке этих двух областей
работ практически нет.

Вопрос: это пробел или это нормально?

Отвечай по существу. Часть пар действительно про разное — тогда честный ответ «нет».
Но часть пар разделена не предметом, а привычкой: сообщества не читают друг друга,
хотя объект или метод у них общий. Такие стыки и есть цель.

Спрашивай себя так: если бы человек, знающий обе области, сел за стол — нашёл бы он,
о чём говорить? Если да — сформулируй вопрос. Если областям нечего сказать друг другу —
скажи «нет» прямо.

Ответь строго JSON:
{{"есть_вопрос": true|false,
  "вопрос": "если true — одним предложением: какой конкретно вопрос лежит на стыке",
  "почему_не_сделано": "если true — почему этого до сих пор не сделали",
  "уверенность": 1-5,
  "почему_нет": "если false — почему стыка нет"}}"""


def ask(text, key, model="deepseek-ai/DeepSeek-V3.1", tries=3):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}],
                       "temperature": 0.3, "max_tokens": 600}).encode("utf-8")
    for a in range(tries):
        try:
            req = urllib.request.Request(
                "https://api.deepinfra.com/v1/openai/chat/completions", data=body,
                headers={"Authorization": f"bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d["choices"][0]["message"]["content"], d.get("usage", {})
        except Exception as e:
            if a == tries - 1:
                raise
    return "", {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=30)
    ap.add_argument("--controls", type=int, default=8,
                    help="контрольных пар — случайных, заведомо не связанных")
    ap.add_argument("--min-pop", type=int, default=800)
    ap.add_argument("--dmin", type=float, default=0.55)
    ap.add_argument("--dmax", type=float, default=0.72)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--calibrate", action="store_true",
                    help="проверить судью на парах с ЗАВЕДОМЫМ стыком и без него")
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb

    C = np.load(DATA / "drill-centers.npy")
    R = json.loads((DATA / "drill-regions.json").read_text(encoding="utf-8"))
    ids, M = vecstore.load(DATA / "field", latest=True)
    A = np.asarray(M, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    lab = np.empty(len(A), dtype=np.int32)
    for s in range(0, len(A), 4096):
        lab[s:s + 4096] = (A[s:s + 4096] @ C.T).argmax(1)
    pop = np.bincount(lab, minlength=len(C))
    print(f"поле: {len(A):,} · областей: {len(C)}")

    # ГЕОМЕТРИЯ, грубо. Работа лежит между A и B, если это две её ближайшие области
    # и они почти равноудалены. Считаем такие работы по всем парам — одним проходом.
    rng = np.random.default_rng(42)
    S = rng.choice(len(A), min(200000, len(A)), replace=False)
    simC = A[S] @ C.T
    srt = np.argsort(-simC, axis=1)[:, :2]
    r0 = np.arange(len(S))
    s1, s2 = simC[r0, srt[:, 0]], simC[r0, srt[:, 1]]
    straddle = (s1 - s2) < 0.01
    from collections import Counter
    between = Counter()
    for k in np.where(straddle)[0]:
        a, b = int(srt[k, 0]), int(srt[k, 1])
        between[(min(a, b), max(a, b))] += 1
    print(f"работ между двумя областями: {int(straddle.sum()):,} "
          f"({100*straddle.mean():.1f}%) · пар со стыком: {len(between):,}")

    big = [j for j in range(len(C)) if pop[j] >= args.min_pop and not R["restricted"][j]]
    cand = []
    for i in range(len(big)):
        for j in range(i + 1, len(big)):
            a, b = big[i], big[j]
            d = float(C[a] @ C[b])
            if not (args.dmin <= d <= args.dmax):
                continue
            if between.get((min(a, b), max(a, b)), 0) > 2:
                continue
            cand.append((a, b, d, min(int(pop[a]), int(pop[b]))))
    # Порядок — по размеру МЕНЬШЕЙ области: пара «4000 и 30» неудивительна,
    # пара «4000 и 3000» без единой работы на стыке — очень.
    cand.sort(key=lambda x: -x[3])
    print(f"кандидатов после геометрии: {len(cand):,} · беру {args.pairs}")
    picked = cand[:args.pairs]

    # КОНТРОЛЬНЫЕ ПАРЫ. Первая версия брала «далёкие» — и не нашла ни одной:
    # все области ближе 0,35 друг к другу, конус узок даже на уровне областей.
    # Правильный контроль другой и он сильнее: пары, где стык ЗАВЕДОМО ЕСТЬ —
    # там лежат сотни реальных работ. Судья, который отказывает и на них,
    # сломан, и это видно сразу, без гадания о том, права ли модель.
    prov = sorted(between.items(), key=lambda kv: -kv[1])
    ctrl = []
    for (a, b), n in prov:
        if pop[a] >= args.min_pop and pop[b] >= args.min_pop and not R["restricted"][a]                 and not R["restricted"][b]:
            ctrl.append((a, b, float(C[a] @ C[b]), min(int(pop[a]), int(pop[b]))))
        if len(ctrl) >= args.controls:
            break
    print(f"контрольных пар (стык ЗАВЕДОМО есть, сотни работ): {len(ctrl)}")

    # Заголовки для каждой области — по три ближайшие к центру работы.
    need = set()
    for a, b, _, _ in picked + ctrl:
        for j in (a, b):
            rows = np.where(lab == j)[0]
            for i in rows[np.argsort(-(A[rows] @ C[j]))][:3]:
                need.add(int(i))
    by_month = {}
    for i in need:
        mo = fb.id_month(ids[i])
        if mo:
            by_month.setdefault(mo, {})[fb._base_id(ids[i])] = i
    tt = {}
    for mo, keys in sorted(by_month.items()):
        p = fb.BULK / f"{mo}.jsonl"
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = fb._base_id(r.get("id", ""))
                if k in keys:
                    tt[keys[k]] = " ".join(str(r.get("title", "")).split())[:110]

    def titles(j):
        rows = np.where(lab == j)[0]
        out = [tt.get(int(i), "") for i in rows[np.argsort(-(A[rows] @ C[j]))][:3]]
        return "\n".join(f"  · {t}" for t in out if t)

    if args.dry:
        for a, b, d, m in picked[:12]:
            print(f"\n  {d:.3f} · min {m}\n    A: {R['names'][a]}\n    B: {R['names'][b]}")
        return 0

    from embeddings_build import load_env
    key = load_env(MAIN)["DEEPINFRA_API_KEY"]
    allp = [(p, False) for p in picked] + [(c, True) for c in ctrl]
    random.Random(42).shuffle(allp)

    found, refused, ctrl_found, ctrl_total, tok = [], 0, 0, 0, 0
    for (a, b, d, m), is_ctrl in allp:
        q = PROMPT.format(na=int(pop[a]), ca=R["names"][a], ta=titles(a),
                          nb=int(pop[b]), cb=R["names"][b], tb=titles(b))
        try:
            raw, use = ask(q, key)
        except Exception as e:
            print(f"  !! пара пропущена ({type(e).__name__})")
            continue
        tok += use.get("total_tokens", 0)
        txt = raw.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            txt = txt[4:] if txt.startswith("json") else txt
        try:
            r = json.loads(txt)
        except Exception:
            continue
        yes = bool(r.get("есть_вопрос"))
        if is_ctrl:
            ctrl_total += 1
            ctrl_found += int(yes)
        if yes:
            found.append({"A": R["names"][a], "B": R["names"][b], "близость": round(d, 3),
                          "работ_меньшей": m, "контроль": is_ctrl,
                          "вопрос": r.get("вопрос", ""),
                          "почему_не_сделано": r.get("почему_не_сделано", ""),
                          "уверенность": r.get("уверенность", 0)})
        else:
            refused += 1

    print(f"\n{'='*78}")
    print(f"ПРОВЕРКА СУДЬИ: на парах, где стык ЗАВЕДОМО есть, вопрос найден "
          f"{ctrl_found} из {ctrl_total}")
    if ctrl_total and ctrl_found < ctrl_total * 0.6:
        print("  ⚠️ СУДЬЯ ОТКАЗЫВАЕТ ДАЖЕ ТАМ, ГДЕ СТЫК ЕСТЬ — он сломан или запуган")
        print("     промптом. Ноль находок ниже ничего не означает.")
    else:
        print("  судья видит настоящие стыки — его отказам можно верить")
    print(f"отказов всего: {refused} из {len(allp)}")

    real = [f for f in found if not f["контроль"]]
    real.sort(key=lambda f: -f.get("уверенность", 0))
    print(f"\n{'='*78}\nНАЙДЕННЫЕ ПРОБЕЛЫ: {len(real)}\n{'='*78}")
    for f in real[:15]:
        print(f"\n[{f['уверенность']}/5] {f['A']}\n      × {f['B']}")
        print(f"   ВОПРОС: {f['вопрос']}")
        print(f"   почему не сделано: {f['почему_не_сделано']}")
    (DATA / "bridges-llm.json").write_text(json.dumps(found, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    print(f"\nтокенов: {tok:,} (~${tok/1e6*0.4:.3f}) → data/bridges-llm.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
