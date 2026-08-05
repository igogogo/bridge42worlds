#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отбор V2: три векторные оценки кандидатов дня перед промптом отбора.

1. ПОЛНОТА — где кандидат стоит относительно нашего корпуса. Целевая зона середина:
   слишком близко = дубль темы, слишком далеко = не наш профиль.
2. ОСЬ практика/теория — проекция на ось между центроидами двух корзин наших статей.
3. АНАЛОГИЙНОСТЬ — близость к статьям, которые УЖЕ дали живые аналогии в карточках.

ПОПРАВКА К КОНСТРУКЦИИ, важная. Корзину аналогий задумывалось строить из ТЕКСТОВ лучших
карточек. Так нельзя: вектор карточки кодирует, о чём она (чёрные дыры, полимеры), а не
то, что в ней есть образ. Центроид полусотни карточек на разные темы — это средняя тема,
то есть шум. Поэтому корзина собирается из ВЕКТОРОВ САМИХ СТАТЕЙ, чьи карточки вышли
с аналогиями: оценка читается как «эта работа похожа на те, из которых получались живые
образы». Топикальность остаётся, но обе стороны сравнения в одном пространстве.

Гипотеза №3 непроверенная. Проверяется отдельно: --hypothesis берёт 20 верхних и 20
нижних кандидатов, для каждого генерится карточка, доля живых аналогий считается глазами.
Нет разницы — ось выкидываем, так и напишем.

    python selection_v2.py --buckets              # собрать корзины, показать примеры
    python selection_v2.py --score --date 2026-08-03
    python selection_v2.py --hypothesis 20
"""
import json, math, pathlib, random, re, sys, time, argparse, collections
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
MODEL = "@cf/baai/bge-m3"
BATCH = 20
SEED = 42

# Маркеры сравнения: аналогия — это когда научное объясняется через бытовое.
# Открывающее слово карточки для этого негодный признак (проверено: карточки,
# не начинающиеся с «Учёные…», в основном всё равно без образов).
ANALOGY = re.compile(
    r"(как если бы|подобно тому|подобно|словно|будто|напоминает|похож\w*|"
    r"представьте|вообразите|это как|всё равно что|наподобие)", re.I)

# Одного маркера сравнения мало. Замер 2026-08-05: маркеры есть у 858 карточек из 1967,
# и верх по их числу — это «как у антиферромагнетиков», «подобно тому, как в EOS».
# Сравнение научного с научным аналогией не является. Аналогия — это когда научное
# объясняют через БЫТОВОЕ, поэтому рядом с маркером должно стоять обиходное слово.
EVERYDAY = re.compile(
    r"(мяч|камен|верёвк|веревк|канат|пружин|качел|карусел|волчок|юл[аы]|"
    r"вод[аыу]|лёд|лед[яу]|пар[аоу]|дым|песок|песчин|пыл[иь]|"
    r"толп[аеы]|очеред|танц|хоровод|оркестр|хлоп|эхо|шёпот|шепот|крик|"
    r"кухн|чашк|стакан|чай|кофе|сахар|соль|тесто|пирог|блин|каша|суп|"
    r"комнат|дверь|окн[оа]|лестниц|ковёр|ковер|одеял|подушк|"
    r"дорог|тропинк|мост|пробк|автомобил|велосипед|поезд|качк|"
    r"монет|весы|линейк|часы|маятник|зеркал|лупа|фонар|свеч|"
    r"клубок|нит[ьи]|ткан|сет[ьи]|паутин|решет|сито|губк|"
    r"мыльн|пузыр|шарик|воздушн|парус|ветер|дожд|снеж|снег)", re.I)

PRACTICE = re.compile(
    r"\b(observ|measur|detect|experiment|telescope|survey|instrument|calibrat|"
    r"spectrograph|photometr|sample|data release|monitoring)", re.I)
THEORY = re.compile(
    r"\b(we derive|analytic|theorem|proof|we prove|model predicts|framework|"
    r"formalism|ansatz|lagrangian|we propose a model|solution of the equation)", re.I)


def load_env():
    env = {}
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def nz(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def our_vectors():
    p = DATA / "embeddings-articles.jsonl"
    if not p.exists():
        sys.exit("нет embeddings-articles.jsonl — сначала embeddings_build.py")
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"].split(":", 1)[1]] = nz(r["vec"])
    return out


def our_meta():
    meta = {}
    for p in (MAIN / "lang" / "ru" / "archive").rglob("data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = d.get("id")
        if not aid:
            continue
        ab = (d.get("abstract") or {}).get("ru") or {}
        en = (d.get("abstract") or {}).get("en") or {}
        meta[aid] = {
            "card": (ab.get("popular") or "").strip(),
            "title": (d.get("original_title") or "").strip(),
            "en": (en.get("advanced") or "").strip() if isinstance(en, dict) else "",
        }
    return meta


def centroid(vecs):
    if not vecs:
        return None
    dim = len(vecs[0])
    c = [0.0] * dim
    for v in vecs:
        for i, x in enumerate(v):
            c[i] += x
    return nz([x / len(vecs) for x in c])


def buckets(show=True):
    vecs, meta = our_vectors(), our_meta()

    # аналогийные: карточки с маркерами сравнения, больше маркеров — выше
    scored = []
    for aid, m in meta.items():
        if aid not in vecs or not m["card"]:
            continue
        mk = len(ANALOGY.findall(m["card"]))
        ev = len(EVERYDAY.findall(m["card"]))
        # маркер сравнения И бытовое слово: одного маркера мало, см. комментарий выше
        if mk and ev:
            scored.append((mk + ev, len(m["card"]), aid))
    scored.sort(reverse=True)
    ana_ids = [a for _, _, a in scored[:50]]

    prac, theo = [], []
    for aid, m in meta.items():
        if aid not in vecs:
            continue
        t = f"{m['title']} {m['en']}"
        p, th = len(PRACTICE.findall(t)), len(THEORY.findall(t))
        if p >= 2 and th == 0:
            prac.append((p, aid))
        elif th >= 2 and p == 0:
            theo.append((th, aid))
    prac.sort(reverse=True); theo.sort(reverse=True)
    prac_ids = [a for _, a in prac[:30]]
    theo_ids = [a for _, a in theo[:30]]

    b = {
        "analogy": centroid([vecs[a] for a in ana_ids]),
        "practice": centroid([vecs[a] for a in prac_ids]),
        "theory": centroid([vecs[a] for a in theo_ids]),
        "_ids": {"analogy": ana_ids, "practice": prac_ids, "theory": theo_ids},
    }
    if show:
        print(f"корзины: аналогии {len(ana_ids)} (кандидатов с маркерами {len(scored)}), "
              f"практика {len(prac_ids)} из {len(prac)}, теория {len(theo_ids)} из {len(theo)}")
        print("\nпримеры карточек с аналогией:")
        for _, _, a in scored[:4]:
            print(f"  • {meta[a]['card'][:170]}")
        ax = sum(x * y for x, y in zip(b["practice"], b["theory"]))
        print(f"\nкосинус между корзинами практика/теория: {ax:.3f} "
              f"(чем ниже, тем осмысленнее ось)")
    return b, vecs, meta


def embed(texts, acc, tok, tries=5):
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODEL}"
    body = json.dumps({"text": texts}).encode("utf-8")
    for a in range(tries):
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            v = (d.get("result") or {}).get("data")
            if v and len(v) == len(texts):
                return v
            raise ValueError("ответ не по размеру")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** a * 2); continue
            raise
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 ** a * 2)
    raise RuntimeError("эмбеддинги не получены")


def candidates(date):
    """Кандидаты дня из локального дампа: месяц берём по дате."""
    f = BULKDIR / f"{date[:7]}.jsonl"
    if not f.exists():
        sys.exit(f"нет файла дампа {f}")
    out = []
    with f.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                j = json.loads(line)
            except Exception:
                continue
            if (j.get("published") or "")[:10] == date:
                out.append({"id": j.get("id"), "title": (j.get("title") or "").strip(),
                            "abstract": (j.get("abstract") or "").strip(),
                            "cats": j.get("categories") or []})
    return out


BULKDIR = MAIN / "data" / "arxiv-bulk"


def score(date, out_name):
    env = load_env(); acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    b, vecs, _ = buckets(show=False)
    cands = candidates(date)
    if not cands:
        sys.exit(f"нет кандидатов за {date}")
    print(f"кандидатов за {date}: {len(cands)}")

    ours = list(vecs.values())
    res = {}
    for i in range(0, len(cands), BATCH):
        ch = cands[i:i + BATCH]
        vs = embed([f"{c['title']} {c['abstract']}"[:6000] for c in ch], acc, tok)
        for c, v in zip(ch, vs):
            cv = nz(v)
            near = max(sum(a * x for a, x in zip(cv, o)) for o in ours)
            ana = sum(a * x for a, x in zip(cv, b["analogy"]))
            pr = sum(a * x for a, x in zip(cv, b["practice"]))
            th = sum(a * x for a, x in zip(cv, b["theory"]))
            res[c["id"]] = {"near": round(near, 4), "analogy": round(ana, 4),
                            "axis": round(pr - th, 4), "title": c["title"][:110],
                            "cats": c["cats"]}
        if (i // BATCH) % 5 == 0:
            print(f"  {min(i+BATCH, len(cands))}/{len(cands)}")

    # полнота: целевая зона — середина. Считаем как расстояние от медианы близости,
    # чтобы «дубль темы» и «не наш профиль» штрафовались одинаково.
    nears = sorted(r["near"] for r in res.values())
    med = nears[len(nears) // 2]
    for r in res.values():
        r["novelty"] = round(1 - abs(r["near"] - med) / max(1e-6, (nears[-1] - nears[0])), 4)
        why = []
        if r["near"] < med - 0.02: why.append("тема далека от нашего корпуса")
        elif r["near"] > med + 0.02: why.append("тема у нас уже плотно занята")
        else: why.append("полупустая область корпуса")
        why.append("практика" if r["axis"] > 0 else "теория")
        if r["analogy"] > 0: why.append(f"аналогийность {r['analogy']:.2f}")
        r["why"] = "; ".join(why)

    p = DATA / out_name
    p.write_text(json.dumps({"date": date, "model": MODEL, "median_near": round(med, 4),
                             "scores": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nзаписано: {p}")
    print(f"медиана близости к корпусу: {med:.3f}  (разброс {nears[0]:.3f}…{nears[-1]:.3f})")
    top = sorted(res.items(), key=lambda kv: -kv[1]["analogy"])[:5]
    print("\nтоп-5 по аналогийности:")
    for k, v in top:
        print(f"  {v['analogy']:.3f}  {k}  {v['title'][:70]}")


CARD_PROMPT = (
    "Ты пишешь короткий текст карточки для научно-популярного сайта: 2-3 предложения, "
    "без вводных, простым языком. Если по существу работы уместна БЫТОВАЯ аналогия — "
    "используй её (пример нужного уровня: «Когда сжимаешь резиновый мяч, он сплющивается, "
    "а камень — почти нет»). Если аналогия натянута — обойдись без неё, врать не надо.\n\n"
    "Работа:\n{title}\n{abstract}"
)


def deepseek(prompt, key, model="deepseek-v4-flash"):
    # Рассуждения ВЫКЛЮЧЕНЫ. Замер проекта (СТАТУС.md, 2026-08-04): с ними 8000 токенов
    # уходят в размышления и до текста дело не доходит — ответ приходит ПУСТОЙ. Первый мой
    # прогон гипотезы это и словил: 7 карточек из 10 пустые, и я чуть не отчитался
    # «гипотеза не подтвердилась» по сломанным данным.
    body = json.dumps({
        "model": model, "temperature": 0.7, "max_tokens": 1200,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d["choices"][0]["message"]["content"].strip()


def hypothesis(n):
    """Проверка оси аналогийности: верх против низа, карточки, оценка глазами.

    Гипотеза владельца: кандидат, близкий к статьям с живыми аналогиями, вероятнее
    даст живую аналогию при генерации. Не проверена ничем — проверяем.
    """
    env = load_env()
    key = env.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("нет DEEPSEEK_API_KEY")
    src = json.loads((DATA / "selection-scores.json").read_text(encoding="utf-8"))
    sc = src["scores"]
    cands = candidates(src["date"])
    by_id = {c["id"]: c for c in cands}

    ranked = sorted(sc.items(), key=lambda kv: -kv[1]["analogy"])
    high = [k for k, _ in ranked[:n]]
    low = [k for k, _ in ranked[-n:]]

    out = {"high": [], "low": []}
    for group, ids in (("high", high), ("low", low)):
        for i in ids:
            c = by_id.get(i)
            if not c:
                continue
            try:
                card = deepseek(CARD_PROMPT.format(
                    title=c["title"], abstract=c["abstract"][:1800]), key)
            except Exception as e:
                print(f"  !! {i}: {type(e).__name__}")
                continue
            mk, ev = len(ANALOGY.findall(card)), len(EVERYDAY.findall(card))
            out[group].append({"id": i, "analogy_score": sc[i]["analogy"],
                               "card": card, "markers": mk, "everyday": ev})
            print(f"  {group} {i}  маркеров {mk}, бытовых {ev}")
    p = DATA / "analogy-hypothesis.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    for g in ("high", "low"):
        rows = out[g]
        if not rows:
            continue
        auto = sum(1 for r in rows if r["markers"] and r["everyday"])
        print(f"\n{g}: карточек {len(rows)}, с маркером И бытовым словом {auto} "
              f"({100*auto/len(rows):.0f}%)")
    print(f"\nтексты для оценки глазами: {p}")
    print("Автоподсчёт — только подсказка: решает чтение карточек.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--buckets", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--hypothesis", type=int, default=0)
    ap.add_argument("--date", default="")
    ap.add_argument("--out", default="selection-scores.json")
    a = ap.parse_args()
    if a.buckets: buckets()
    elif a.score and a.date: score(a.date, a.out)
    elif a.hypothesis: hypothesis(a.hypothesis)
    else: ap.print_help()

