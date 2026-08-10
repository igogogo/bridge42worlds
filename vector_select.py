#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Векторный отбор кандидатов дня: предфильтр для промпта + независимый канал.

ЧТО ИСПОЛЬЗУЕМ И ЧЕГО НЕТ — по собственным замерам, без повторной проверки:
  · полнота (близость к корпусу) РАБОТАЕТ: медиана 0,613, целевая середина различима;
  · ось практика/теория ВЫРОЖДЕНА (косинус центроидов 0,875) — не используется;
  · ось аналогий МЕРТВА (34% против 28% на n=50) — не используется.

ПОЧЕМУ ЦИТИРОВАНИЙ ЗДЕСЬ НЕТ, хотя признак валиден. Сопряжение по ссылкам считается
по списку литературы, а у свежего кандидата дня его нет: с arXiv приходят только
заголовок и аннотация, PDF ещё не качали. Цитировать его тоже пока некому — работа
вышла сегодня. Признак остаётся сильным для ОЧЕРЕДИ ДЫР (там работы старые и ссылки
на них есть), но к дневному отбору неприменим по устройству данных, а не по качеству.

ТЕМАТИЧЕСКОЕ ОГРАНИЧЕНИЕ (владелец 2026-08-06) вектор исполняет по-своему. Правило
«из cs.LG берём только ИИ как инструмент естественной науки» промпт исполняет чтением.
Вектору читать нечем — зато он умеет мерить: работа про сам ИИ лежит далеко от нашего
корпуса, работа про ИИ в астрофизике — близко. Поэтому для cs.* и math.* требуем
близость ВЫШЕ медианы, а не среднюю зону. Это тот же смысл, выраженный числом.

    python vector_select.py --date 2026-07-15 --count 25 --independent 4
"""
import json, math, pathlib, sys, time, argparse, collections
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
MODEL = "@cf/baai/bge-m3"
BATCH = 20
# Разделы под ограничением владельца: берём только то, что близко к нашей работе.
RESTRICTED = ("cs.", "math.", "stat.", "econ.", "q-fin.")


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


def corpus():
    p = DATA / "embeddings-articles.jsonl"
    if not p.exists():
        sys.exit("нет embeddings-articles.jsonl")
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(nz(json.loads(line)["vec"]))
    return out


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


def prefilter(articles, keep_min=40):
    """Отсев краёв ПЕРЕД моделью. Зовётся из gen_llm.select_best().

    ЧТО ДЕЛАЕТ. Вычёркивает два края: «такое у нас уже есть» (близость к корпусу выше
    95-го перцентиля дня) и «не наш профиль» (ниже 20-го). Середину не трогает и
    НЕ РАНЖИРУЕТ — там решает модель. Это разделение обязанностей, а не временная мера.

    ЗАМЕР 6 августа, шесть дней: в промпт уходит вместо ~1058 кандидатов около 200,
    то есть минус 81% токенов отбора — самой дорогой строки ночного прогона. Доля
    профильных разделов при этом РАСТЁТ во все шесть дней (+0,7…+5,5 п.п.), не падает
    ни разу.

    ПОЧЕМУ НЕ РАНЖИРУЕТ. Первая версия брала «ближе к медиане = интереснее» и дала
    шорт-лист, где 45% cs/math при 4% астрофизики: наши профильные темы близки
    к корпусу, «полнота» у них низкая, и они вылетали. Ранжирующего признака у вектора
    нет — три оси закрыты числом (практика/теория, аналогии, полнота).

    БЕЗОПАСНОСТЬ. Любой сбой — возвращаем список как был. Отбор не должен падать
    из-за вспомогательного слоя: без него он работает как раньше, с ним дешевле.
    """
    if len(articles) <= keep_min:
        return articles, "кандидатов мало, отсев не нужен"
    try:
        env = load_env()
        acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
        ours = corpus()
        import numpy as np
        O = np.array(ours, dtype=np.float32)
        near = []
        for i in range(0, len(articles), BATCH):
            ch = articles[i:i + BATCH]
            vs = embed([f"{a.get('title','')} {a.get('summary','')}"[:6000] for a in ch],
                       acc, tok)
            cv = np.array([nz(v) for v in vs], dtype=np.float32)
            near.extend((cv @ O.T).max(axis=1).tolist())
    except Exception as e:
        return articles, f"вектор недоступен ({type(e).__name__}), беру всех"

    order = sorted(near)
    p_dup = order[int(0.95 * (len(order) - 1))]
    p_off = order[int(0.20 * (len(order) - 1))]
    kept = [a for a, s in zip(articles, near) if p_off <= s <= p_dup]
    if len(kept) < keep_min:          # порезали слишком много — днём не рискуем
        return articles, f"после отсева осталось {len(kept)}, это мало — беру всех"
    return kept, (f"вектор отсеял {len(articles) - len(kept)} из {len(articles)}: "
                  f"дублей темы {sum(1 for s in near if s > p_dup)}, "
                  f"чужого профиля {sum(1 for s in near if s < p_off)}")


def day_candidates(date):
    f = MAIN / "data" / "arxiv-bulk" / f"{date[:7]}.jsonl"
    if not f.exists():
        sys.exit(f"нет дампа {f}; для живого дня кандидаты приходят из API")
    out = []
    with f.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                j = json.loads(line)
            except Exception:
                continue
            if (j.get("published") or "")[:10] != date:
                continue
            cats = j.get("categories") or []
            out.append({"id": j.get("id"), "title": (j.get("title") or "").strip(),
                        "summary": (j.get("abstract") or "").strip(),
                        "primary_category": cats[0] if cats else "?"})
    return out


def score(articles, acc, tok):
    """Считает полноту для ВСЕХ кандидатов. Возвращает список с оценками.

    БЛИЗОСТЬ СЧИТАЕТСЯ МАТРИЧНО. На чистом Python это 1058 кандидатов × 2124 вектора
    × 1024 измерения = 2,3 млрд умножений, минуты вместо секунд — в ежедневный прогон
    такое не поставишь. numpy делает то же одним произведением матриц.
    """
    import numpy as np
    ours = np.array(corpus(), dtype=np.float32)     # (N, 1024), уже нормированы
    res = []
    for i in range(0, len(articles), BATCH):
        ch = articles[i:i + BATCH]
        vs = embed([f"{a['title']} {a['summary']}"[:6000] for a in ch], acc, tok)
        cv = np.array([nz(v) for v in vs], dtype=np.float32)   # (B, 1024)
        near = (cv @ ours.T).max(axis=1)                        # (B,)
        for a, s in zip(ch, near):
            res.append(dict(a, near=round(float(s), 4)))
    nears = sorted(r["near"] for r in res)
    med = nears[len(nears) // 2]
    span = max(1e-6, nears[-1] - nears[0])
    for r in res:
        # полнота: середина ценнее краёв. Слишком близко — дубль темы,
        # слишком далеко — не наш профиль.
        r["novelty"] = round(1 - abs(r["near"] - med) / span, 4)
        r["restricted"] = r["primary_category"].startswith(RESTRICTED)
        # ограничение владельца, выраженное числом: работа про сам ИИ лежит далеко
        # от нашего корпуса, работа про ИИ в науке — близко
        r["allowed"] = (not r["restricted"]) or (r["near"] >= med)
        why = []
        why.append("полупустая область" if abs(r["near"] - med) < 0.02 else
                   ("тема занята" if r["near"] > med else "далеко от профиля"))
        if r["restricted"]:
            why.append("под ограничением: " +
                       ("работает на нашу науку" if r["allowed"] else "про сам метод — отсев"))
        r["why"] = "; ".join(why)
    return res, med


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--count", type=int, default=25)
    ap.add_argument("--independent", type=int, default=4)
    ap.add_argument("--shortlist", type=int, default=0, help="0 = втрое от count")
    a = ap.parse_args()

    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    cands = day_candidates(a.date)
    if not cands:
        sys.exit(f"нет кандидатов за {a.date}")
    chars = sum(len(c["title"]) + len(c["summary"]) for c in cands)
    print(f"кандидатов: {len(cands)}, знаков {chars:,}, "
          f"эмбеддинг ~${chars/4/1e6*0.012:.4f}")

    res, med = score(cands, acc, tok)

    # ВЕКТОР РЕЖЕТ КРАЯ, А НЕ ВЫБИРАЕТ СЕРЕДИНУ. Замер 2026-08-06, ради него всё
    # и делалось: отбор «ближе к медиане = интереснее» дал шорт-лист, где 45% —
    # cs/math/stat, а астрофизики 4%. Механизм обратный задуманному: наши профильные
    # темы близки к корпусу (у нас 824 астро-статьи), значит их «полнота» низкая
    # и они ВЫЛЕТАЮТ; чужие работы умеренно похожи на всё и садятся на медиану.
    #
    # Что вектор действительно умеет — узнавать края: «это у нас уже есть» и «это
    # не наш профиль». Их и режем, состав середины не трогаем: ранжировать внутри
    # неё мне нечем, все проверенные оси мертвы, и подменять отбор жребием нечестно.
    nears = sorted(r["near"] for r in res)
    p_dup = nears[int(0.95 * (len(nears) - 1))]     # выше — почти дубль уже написанного
    p_off = nears[int(0.20 * (len(nears) - 1))]     # ниже — не наш профиль
    for r in res:
        r["keep"] = p_off <= r["near"] <= p_dup
        if r["near"] > p_dup:
            r["why"] = "почти дубль: такое у нас уже есть"
        elif r["near"] < p_off:
            r["why"] = "далеко от нашего профиля"
    allowed = [r for r in res if r["keep"]]
    cut = len(res) - len(allowed)
    # порядок сохраняем исходный: вектор не ранжирует, он только вычёркивает
    ranked = allowed

    short_n = a.shortlist or a.count * 3
    shortlist = ranked[:short_n]

    # НЕЗАВИСИМЫЙ КАНАЛ — СЛУЧАЙНЫЙ ВЫБОР ВНУТРИ ПОЛОСЫ, А НЕ ВЕРХ ПО ОЦЕНКЕ.
    # Замер 2026-08-06: ранжирование по «полноте» даёт максимум ровно на медиане,
    # то есть отбирает САМЫЕ ТИПИЧНЫЕ работы дня. Как фильтр средняя зона работает,
    # как ранжирование — выбирает серость, и сравнение с промптом вышло бы подтасовкой
    # против вектора. Ранжирующего признака у меня нет: ось практика/теория вырождена,
    # ось аналогий мертва, оба закрыты числом. Пока признака нет, честный независимый
    # канал — жребий внутри допустимой полосы: он проверяет ФИЛЬТР, а не ранжирование.
    import random
    band = ranked
    independent = random.Random(42).sample(band, min(a.independent, len(band)))

    out_dir = MAIN / "temp" / a.date
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "vector-select.json"
    p.write_text(json.dumps({
        "date": a.date, "model": MODEL, "median_near": round(med, 4),
        "candidates": len(cands), "cut_by_domain_rule": cut,
        # шорт-лист уходит в промпт вместо всего дня — это и есть экономия токенов
        "shortlist": [{"id": r["id"], "cat": r["primary_category"],
                       "novelty": r["novelty"], "why": r["why"]} for r in shortlist],
        # независимый канал: выбрано ВЕКТОРОМ, промпт не участвует
        "independent": [{"id": r["id"], "cat": r["primary_category"],
                         "novelty": r["novelty"], "chosen_by": "vector",
                         "why": r["why"], "title": r["title"][:110]} for r in independent],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    j_all = sum(len(c["title"]) + len(c["summary"][:500]) for c in cands)
    j_short = sum(len(r["title"]) + len(r["summary"][:500]) for r in shortlist)
    print(f"\nмедиана близости: {med:.3f}")
    print(f"отсеяно тематическим ограничением: {cut} из {len(cands)}")
    print(f"шорт-лист для промпта: {len(shortlist)} вместо {len(cands)}")
    print(f"токенов отбора: было ~{j_all//4:,}, стало ~{j_short//4:,} "
          f"(-{100*(1-j_short/max(1,j_all)):.0f}%)")
    print(f"\nнезависимый канал вектора ({a.independent}):")
    for r in independent:
        print(f"  [{r['primary_category']}] {r['title'][:66]}")
        print(f"     novelty {r['novelty']}  — {r['why']}")
    print(f"\nзаписано: {p}")


if __name__ == "__main__":
    main()

