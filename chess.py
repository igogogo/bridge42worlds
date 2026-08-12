#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Короткие циклы с возвратом: замыкание вместо суждения. Исход партии для дерева.

Владелец 12 августа: «когда ты высказал предположения и принял их за факт, сделал
следующий ход и вернулся оттуда, откуда начал, — значит это было правильно… возьми
нейронку, которая играет в шахматы, и примени к нам… доработай, чтобы они считали
ходы и могли возвращаться в исходную позицию, пройдя путь из 2-3 шагов».

ЧТО ПЕРЕНОСИТСЯ ИЗ ШАХМАТ, А ЧТО НЕТ. Веса шахматной сети не переносятся: она
оценивает доску 8×8. Переносится устройство поиска — много прогонов из одной позиции,
оценка позиции по исходу партии, накопление статистики по ходам. Но у AlphaZero это
работает потому, что **исход определён**: выиграл или проиграл. У поиска научных
пробелов исхода нет, и это была дыра во всей конструкции.

Замыкание цикла и есть недостающий исход. Партия выиграна, если цепь вернулась.

СХЕМА ХОДА. Из начального утверждения делаем 2-3 шага, принимая каждый ЗА ФАКТ
и не оценивая. Затем — ход назад: «связывается ли последнее с первым, и если да, то как».
Замыкание меряется не словами модели, а геометрией: насколько близко замыкающее
утверждение легло к началу.

Это в точности схема Свенсона A→B→C→A, только с обязательным условием возврата.
У Свенсона (1986) слабое место было именно в том, что цепь A→B→C никуда не обязана
возвращаться, и потому путей длины два в любом корпусе экспоненциально много.
Требование замкнуться отсекает почти всё — и в этом его ценность.

ДВА КОНТРОЛЯ, без которых число не значит ничего:
  ЛОЖНОЕ ЗАМЫКАНИЕ — то же замыкающее утверждение проверяется на ЧУЖОМ начале.
      Если оно ложится к чужому так же близко, как к своему, модель просто пишет
      общие слова, и замыкание — иллюзия.
  СКАТЫВАНИЕ К СЕРЕДИНЕ — цепь может «вернуться», съехав в центр облака, куда
      съезжает всё. Поэтому близость к началу всегда печатается рядом с близостью
      к центру корпуса.

    python chess.py --starts 3 --rollouts 4 --depth 3
"""
import argparse
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

STEP = """Ты делаешь ход в цепи научного рассуждения. Тебя НЕ просят оценивать,
правда это или нет: предыдущее звено принимается ЗА ФАКТ.

Цепь:
{chain}

Ход {n}: одно предложение — что из этого следует или что стоит проверить дальше.
Двигайся в сторону, а не по кругу: следующий ход должен добавлять новое.
Без оговорок и сомнений. Только утверждение, одним предложением."""

CLOSE = """Дана цепь рассуждения:
{chain}

И отдельно — исходное утверждение, с которого всё началось:
{start}

Вопрос: замыкается ли круг? То есть следует ли из последнего звена что-то,
что возвращает нас к исходному утверждению — объясняет его, уточняет или
предсказывает его же с другой стороны?

Если да — сформулируй это возвращение одним предложением: чем именно последнее
звено говорит о первом.
Если круг не замыкается — ответь ровно словом НЕТ.

Без преамбулы."""


def ask(text, key, model="deepseek-ai/DeepSeek-V3.1", temp=0.8, tries=3):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}],
                       "temperature": temp, "max_tokens": 220}).encode("utf-8")
    for a in range(tries):
        try:
            req = urllib.request.Request(
                "https://api.deepinfra.com/v1/openai/chat/completions", data=body,
                headers={"Authorization": f"bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d["choices"][0]["message"]["content"].strip(), d.get("usage", {})
        except Exception:
            if a == tries - 1:
                raise
    return "", {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--starts", type=int, default=3)
    ap.add_argument("--rollouts", type=int, default=4, help="партий из одной позиции")
    ap.add_argument("--depth", type=int, default=3, help="ходов до попытки замкнуть")
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb
    from embeddings_build import embed_cached, load_env

    ids, M = vecstore.load(DATA / "field", latest=True)
    A = np.asarray(M, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    centroid = A.mean(0)
    centroid /= np.linalg.norm(centroid) + 1e-9
    key = load_env(MAIN)["DEEPINFRA_API_KEY"]

    rng = np.random.default_rng(42)
    picks = rng.choice(len(A), args.starts, replace=False)
    need = {}
    for i in picks:
        mo = fb.id_month(ids[i])
        if mo:
            need.setdefault(mo, {})[fb._base_id(ids[i])] = int(i)
    starts = {}
    for mo, keys in sorted(need.items()):
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
                    starts[keys[k]] = " ".join(
                        f"{r.get('title','')}. {r.get('abstract','')}".split())[:600]
    order = list(starts)
    print(f"поле: {len(A):,} · позиций: {len(order)} · "
          f"партий из каждой: {args.rollouts} · глубина: {args.depth}")

    tok, games = 0, []
    for gi, i in enumerate(order):
        seed = starts[i]
        for r in range(args.rollouts):
            chain = [seed]
            for n in range(args.depth):
                txt, use = ask(STEP.format(
                    chain="\n".join(f"{k+1}. {c[:240]}" for k, c in enumerate(chain)),
                    n=n + 1), key)
                tok += use.get("total_tokens", 0)
                chain.append(txt)
            close, use = ask(CLOSE.format(
                chain="\n".join(f"{k}. {c[:240]}" for k, c in enumerate(chain[1:], 1)),
                start=seed[:400]), key, temp=0.3)
            tok += use.get("total_tokens", 0)
            # ЛОЖНОЕ ЗАМЫКАНИЕ: та же цепь, но замкнуть просят на ЧУЖОЕ начало.
            other = starts[order[(gi + 1) % len(order)]]
            fake, use = ask(CLOSE.format(
                chain="\n".join(f"{k}. {c[:240]}" for k, c in enumerate(chain[1:], 1)),
                start=other[:400]), key, temp=0.3)
            tok += use.get("total_tokens", 0)
            games.append({"start_id": ids[i], "gi": gi, "chain": chain,
                          "close": close, "fake": fake,
                          "said_yes": not close.strip().upper().startswith("НЕТ"),
                          "fake_yes": not fake.strip().upper().startswith("НЕТ")})

    texts, idx = [], {}
    for g in games:
        for t in g["chain"] + [g["close"], g["fake"]]:
            if t not in idx:
                idx[t] = len(texts)
                texts.append(t)
    V = np.asarray(embed_cached(texts, key, DATA / "chess-cache.jsonl", "цепи"),
                   dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9

    print(f"\n{'='*78}\nПАРТИИ\n{'='*78}")
    res = []
    for g in games:
        v0 = V[idx[g["chain"][0]]]
        path = [float(V[idx[t]] @ v0) for t in g["chain"]]
        cl = float(V[idx[g["close"]]] @ v0)
        # Ложное замыкание меряем к ЧУЖОМУ началу — то есть к тому, на которое просили.
        vo = V[idx[starts[order[(g["gi"] + 1) % len(order)]]]] if \
            starts[order[(g["gi"] + 1) % len(order)]] in idx else None
        fk = float(V[idx[g["fake"]]] @ vo) if vo is not None else float("nan")
        res.append({"мин_по_пути": min(path[1:]), "замыкание": cl, "ложное": fk,
                    "сказал_да": g["said_yes"], "ложное_да": g["fake_yes"],
                    "к_центру": float(V[idx[g["close"]]] @ centroid)})
        print(f"\n{g['start_id']} · партия")
        print(f"  путь к началу: {' → '.join(f'{p:.2f}' for p in path[1:])}")
        print(f"  ЗАМЫКАНИЕ {cl:.3f} ({'да' if g['said_yes'] else 'НЕТ'}) · "
              f"ложное на чужом {fk:.3f} ({'да' if g['fake_yes'] else 'НЕТ'})")
        print(f"    {g['close'][:170]}")

    import statistics as st
    real = [r["замыкание"] for r in res]
    fake = [r["ложное"] for r in res if r["ложное"] == r["ложное"]]
    print(f"\n{'='*78}\nИТОГ\n{'='*78}")
    print(f"партий: {len(res)}")
    print(f"замыкание к СВОЕМУ началу:  {st.mean(real):.3f}")
    print(f"замыкание к ЧУЖОМУ началу:  {st.mean(fake):.3f}" if fake else "")
    print(f"минимум по пути (куда ушли): {st.mean(r['мин_по_пути'] for r in res):.3f}")
    print(f"близость замыкания к центру корпуса: {st.mean(r['к_центру'] for r in res):.3f}")
    yes = sum(r["сказал_да"] for r in res)
    fyes = sum(r["ложное_да"] for r in res)
    print(f"\nмодель сказала «замкнулось»: {yes} из {len(res)} · "
          f"на ЧУЖОМ начале: {fyes} из {len(res)}")
    if fake and st.mean(real) - st.mean(fake) < 0.03:
        print("\n⚠️ ЗАМЫКАНИЕ ЛОЖНОЕ: к чужому началу цепь возвращается так же, как")
        print("   к своему. Модель пишет общие слова, критерий не работает.")
    elif fyes >= yes:
        print("\n⚠️ модель говорит «замкнулось» и на чужом начале не реже — словам её")
        print("   верить нельзя, но геометрия может ещё что-то показать (см. числа выше)")
    else:
        print("\n→ замыкание к своему началу отличается от ложного: критерий несёт сигнал")
    (DATA / "chess-games.json").write_text(
        json.dumps([{**g, "оценки": r} for g, r in zip(games, res)],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nтокенов: {tok:,} (~${tok/1e6*0.4:.3f}) → data/chess-games.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
