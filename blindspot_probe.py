#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка «слепой зоны»: есть ли в arXiv работы по теме заявки народной науки.

ЗАЧЕМ ЭТО НЕ ОДИН ЗАПРОС К ВЕКТОРУ. Ответ «максимальный косинус 0,55» сам по себе
не значит ничего: у bge-m3 распределение узкое (замер 2026-08-04: между «всё подряд»
и «почти ничего» всего 0,15 по косинусу). Поэтому меряем ОТНОСИТЕЛЬНО:

  · контрольные темы, которые в arXiv заведомо есть (дрейф нуля МЭМС-гироскопа,
    шум квантования АЦП) — что даёт «нашлось»;
  · случайная выборка дампа — что даёт «мимо».

Тема заявки считается слепой зоной, если её максимум лежит ближе к случайному фону,
чем к контрольным темам. Это утверждение проверяемо числом, а не на глаз.

ПОЧЕМУ СНАЧАЛА ОТБОР ПО СЛОВАМ. Эмбеддинг всех 3 млн аннотаций — 13 часов и $13.
Отбор по широкому списку слов сужает до тысяч за минуты, и уже их считаем вектором.
Цена — отбор по словам может пропустить работу, написанную другими словами; поэтому
список нарочно широкий, а рядом считается случайный фон, который от слов не зависит.

    python blindspot_probe.py --scan          # этап 1: кандидаты из дампа
    python blindspot_probe.py --embed         # этап 2: векторы и сравнение
"""
import json, math, os, pathlib, random, re, sys, time, argparse
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
BULK = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds\data\arxiv-bulk")
OUT = ROOT / "data"
MODEL = "@cf/baai/bge-m3"
BATCH = 20
RANDOM_N = 4000     # фон: сколько случайных аннотаций взять для калибровки
SEED = 42

# Широко нарочно: пропустить работу дороже, чем посчитать лишнюю сотню.
KEYWORDS = [
    "accelerometer", "mems", "lis3dsh", "adxl", "mpu6050", "mpu-6050", "bmi160",
    "imu", "inertial measurement", "inertial sensor",
    "i2c", "i²c", "spi bus", "serial bus", "sensor bus",
    "quantization", "quantisation", "adc ", "analog-to-digital", "analogue-to-digital",
    "stuck bit", "stuck-at", "bit error", "byte error", "sensor fault", "sensor artifact",
    "sensor artefact", "digital sensor noise", "sensor readout", "readout noise",
    "rotating sensor", "rotating frame sensor", "centrifugal", "vibration-induced",
    "esp32", "microcontroller", "embedded sensor", "low-cost sensor",
]

QUERIES = {
    # --- тема заявки, разложенная на грани ---
    "заявка: залипание байта МЭМС":
        "Byte sticking artifact in MEMS accelerometer readings: the low byte of one axis "
        "repeatedly returns the same fixed value in 10-14 percent of samples, observed only "
        "on rotating nodes and absent at rest. Quantization or readout artifact of a digital "
        "three-axis accelerometer LIS3DSH sampled over I2C from an ESP32 microcontroller.",
    "заявка: аномалия данных при вращении":
        "Data anomaly appearing only when a digital accelerometer is mounted on a rotating "
        "wheel: repeated identical sensor values under centrifugal acceleration, disappearing "
        "when rotation stops. Possible causes: sensor internal filtering, bus timing under "
        "vibration, power supply noise on a rotating platform.",
    "заявка: неравномерная выборка по случайному триггеру":
        "Irregular sampling of a sensor triggered by a hardware random process instead of a "
        "fixed-rate timer: measurements are taken at the moments when a random 32-bit integer "
        "passes a primality test, producing non-uniform sampling intervals.",
    # --- контроль: это в arXiv заведомо есть ---
    "контроль: дрейф нуля МЭМС-гироскопа":
        "Bias instability and zero drift of MEMS gyroscopes: Allan variance characterization "
        "of inertial sensor noise, temperature dependence of bias, calibration of low-cost "
        "inertial measurement units.",
    "контроль: шум квантования АЦП":
        "Quantization noise in analog-to-digital converters: effect of finite ADC resolution "
        "on measurement precision, dithering, and the statistical distribution of quantization "
        "error in digitized signals.",
    "контроль: чёрные дыры (заведомо чужая тема)":
        "Accretion disk around a supermassive black hole and the observed X-ray variability "
        "of active galactic nuclei.",
}


def load_env():
    env = {}
    for line in (pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds") / ".env"
                 ).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def scan():
    """Этап 1: широкий отбор по словам + случайный фон. Вектор здесь не нужен."""
    pat = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.I)
    files = sorted(BULK.glob("*.jsonl"))
    cands, pool, seen_total = [], [], 0
    rnd = random.Random(SEED)
    t0 = time.time()
    for n, f in enumerate(files, 1):
        if f.stat().st_size == 0:
            continue
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                seen_total += 1
                text = f"{j.get('title','')} {j.get('abstract','')}"
                if pat.search(text):
                    cands.append({"id": j.get("id"), "title": (j.get("title") or "").strip(),
                                  "abstract": (j.get("abstract") or "").strip()[:2500],
                                  "published": j.get("published"),
                                  "cats": j.get("categories")})
                # резервуарная выборка: фон без перекоса по годам
                if len(pool) < RANDOM_N:
                    pool.append({"id": j.get("id"), "title": (j.get("title") or "").strip(),
                                 "abstract": (j.get("abstract") or "").strip()[:2500]})
                else:
                    k = rnd.randint(0, seen_total - 1)
                    if k < RANDOM_N:
                        pool[k] = {"id": j.get("id"), "title": (j.get("title") or "").strip(),
                                   "abstract": (j.get("abstract") or "").strip()[:2500]}
        if n % 50 == 0:
            print(f"  {n}/{len(files)} файлов, просмотрено {seen_total:,}, "
                  f"кандидатов {len(cands):,}, {time.time()-t0:.0f}с")
    OUT.mkdir(exist_ok=True)
    (OUT / "blindspot-candidates.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cands), encoding="utf-8")
    (OUT / "blindspot-random.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in pool), encoding="utf-8")
    print(f"\nпросмотрено аннотаций: {seen_total:,}")
    print(f"кандидатов по словам: {len(cands):,} ({100*len(cands)/seen_total:.2f}%)")
    print(f"случайный фон: {len(pool):,}")


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
                time.sleep(2 ** a * 2)
                continue
            raise
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 ** a * 2)
    raise RuntimeError("эмбеддинги не получены")


def nz(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def run_embed(limit):
    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]

    qnames = list(QUERIES)
    qvecs = [nz(v) for v in embed([QUERIES[k] for k in qnames], acc, tok)]

    def sweep(path, label):
        rows = [json.loads(l) for l in (OUT / path).read_text(encoding="utf-8").splitlines() if l.strip()]
        if limit:
            rows = rows[:limit]
        best = {q: [] for q in qnames}
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            vs = embed([f"{r['title']} {r['abstract']}"[:6000] for r in chunk], acc, tok)
            for r, v in zip(chunk, vs):
                vn = nz(v)
                for q, qv in zip(qnames, qvecs):
                    s = sum(a * b for a, b in zip(qv, vn))
                    best[q].append((s, r["id"], r["title"][:90]))
            if (i // BATCH) % 10 == 0:
                print(f"  {label}: {min(i+BATCH, len(rows))}/{len(rows)}")
        for q in best:
            best[q].sort(reverse=True)
        return best, len(rows)

    # candidates2 — после ужесточения фильтра, см. blindspot_filter.py:
    # первый проход дал 602k из-за `imu` без границы слова (совпадало в maximum, simulation)
    cand_file = ("blindspot-candidates2.jsonl"
                 if (OUT / "blindspot-candidates2.jsonl").exists()
                 else "blindspot-candidates.jsonl")
    cand_best, ncand = sweep(cand_file, "кандидаты")
    rand_best, nrand = sweep("blindspot-random.jsonl", "фон")

    out = {"n_candidates": ncand, "n_random": nrand, "model": MODEL, "queries": {}}
    print(f"\n{'тема':<44} {'макс по канд.':>13} {'макс по фону':>13} {'95% фона':>10}")
    for q in qnames:
        c = cand_best[q]
        r = [x[0] for x in rand_best[q]]
        r.sort()
        p95 = r[int(0.95 * (len(r) - 1))]
        print(f"{q:<44} {c[0][0]:>13.3f} {r[-1]:>13.3f} {p95:>10.3f}")
        out["queries"][q] = {
            "max_candidates": round(c[0][0], 4),
            "max_random": round(r[-1], 4),
            "p95_random": round(p95, 4),
            "top": [{"id": i, "sim": round(s, 4), "title": t} for s, i, t in c[:12]],
        }
    (OUT / "blindspot-result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nподробности: {OUT/'blindspot-result.json'}")
    for q in qnames:
        print(f"\n--- {q} ---")
        for e in out["queries"][q]["top"][:6]:
            print(f"  {e['sim']:.3f}  {e['id']}  {e['title']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.scan:
        scan()
    elif a.embed:
        run_embed(a.limit)
    else:
        ap.print_help()
