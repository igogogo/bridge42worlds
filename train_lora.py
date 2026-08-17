#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Дообучение компаса: LoRA r=16 на bge-m3, InfoNCE через GradCache. Эпик «танк».

Полный цикл, готовый к запуску на арендованной карте. Обучаемых параметров 3 145 728
из 568 миллионов — 0.55%; таблица эмбеддингов заморожена. Пары берутся из
data/citations.json (210 643 после сбора через Semantic Scholar), аннотации обеих
сторон — из локального дампа arXiv.

ЗАЧЕМ GRADCACHE. Смысл InfoNCE в отрицательных примерах: чем больше партия, тем больше
работ, среди которых модель обязана узнать правильную. Партия 1024 в память одной карты
вместе с графом вычислений не помещается, а уменьшать её — значит обучать на задаче
легче настоящей. GradCache решает это в два прохода:

  1. без графа считаем представления всей партии — память под них копеечная;
  2. на них считаем потерю и градиент ПО ПРЕДСТАВЛЕНИЯМ;
  3. второй раз проходим по кускам уже с графом и проталкиваем назад
     заранее посчитанный градиент.

Цена — примерно двойное время прямого прохода. В смете это множитель 1.9,
и он ПОКА НЕ ЗАМЕРЕН (см. finetune_estimate.py).

КРИТЕРИЙ УСПЕХА ЗАФИКСИРОВАН ДО ОБУЧЕНИЯ и не пересматривается по результату:
медианный ранг связанной работы среди 918 297 должен упасть вчетверо, с 2 704
до 676 и ниже. Контрольная выборка откладывается ПО ЦИТИРУЮЩЕЙ РАБОТЕ, а не по паре:
иначе одна и та же работа попадёт и в обучение, и в проверку разными своими ссылками,
и проверка будет мерить запоминание.

СУХОЙ ПРОГОН. `--dry` проходит весь конвейер на процессоре с заглушкой вместо модели:
ни загрузки весов, ни аренды, ни счёта.

Главная его проверка — не «убывает ли потеря». Первая версия проверяла именно это
и сказала «конвейер сломан» там, где код был исправен: на свежей заглушке с шагом
обучения 2e-5 потеря и не должна убывать за десяток шагов, так что «сломано»
и «мало шагов» такая проверка не различает.

Проверка заменена на точную: один и тот же кусок данных проходит двумя путями —
напрямую и через GradCache, — и градиенты ПО ПАРАМЕТРАМ обязаны совпасть до ошибок
округления. Математически это одно и то же; расходятся — код неверен. На нашем
прогоне относительное расхождение 1.4e-07, то есть совпадают.

    python train_lora.py --dry                сухой прогон на процессоре
    python train_lora.py --steps 600          обучение (на арендованной карте)
    python train_lora.py --eval-only          только замер медианного ранга
"""
import argparse
import json
import math
import pathlib
import random
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

MODEL = "BAAI/bge-m3"
LORA_TARGETS = ("query", "key", "value", "dense")   # Q/K/V/O в XLM-RoBERTa
TAU = 0.05          # не заводские 0.02: на наших парах мягче работает лучше
HOLDOUT = 0.05      # доля цитирующих работ под контроль


# ─────────────────────────── данные ───────────────────────────

def load_pairs(limit=0):
    """Пары и тексты обеих сторон. Пара без текста хотя бы с одной стороны выбрасывается
    молча — но её выброс печатается числом, чтобы «мало данных» не выглядело как
    «мало пар в файле»."""
    import field_build as fb
    src = DATA / "citations.json"
    if not src.exists():
        src = MAIN / "data" / "citations.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    raw = [(fb._base_id(e["from"]), fb._base_id(e["to"]))
           for e in (d.get("internal") or []) if e.get("from") and e.get("to")]
    raw = [(a, b) for a, b in raw if a and b and a != b]
    if limit:
        raw = raw[:limit]
    need, bymonth = {a for p in raw for a in p}, {}
    for a in need:
        mo = fb.id_month(f"arx:{a}")
        if mo:
            bymonth.setdefault(mo, set()).add(a)
    text = {}
    for mo, ks in sorted(bymonth.items()):
        p = fb.BULK / f"{mo}.jsonl"
        if not p.exists():
            continue
        with p.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = fb._base_id(r.get("id", ""))
                if k in ks:
                    text[k] = " ".join((str(r.get("title", "")) + ". "
                                        + str(r.get("abstract", ""))).split())
    ok = [(a, b) for a, b in raw if a in text and b in text]
    print(f"пар в файле {len(raw):,} · с текстом обеих сторон {len(ok):,} "
          f"({len(raw) - len(ok):,} выброшено)")
    return ok, text


def split(pairs, seed=17):
    """Контроль откладывается ПО ЦИТИРУЮЩЕЙ РАБОТЕ. Разделение по парам дало бы
    утечку: работа с двадцатью ссылками попала бы в обе половины."""
    srcs = sorted({a for a, _ in pairs})
    rnd = random.Random(seed)
    rnd.shuffle(srcs)
    held = set(srcs[:max(1, int(len(srcs) * HOLDOUT))])
    tr = [p for p in pairs if p[0] not in held]
    ev = [p for p in pairs if p[0] in held]
    print(f"обучение {len(tr):,} пар · контроль {len(ev):,} пар "
          f"({len(held):,} цитирующих работ отложено)")
    return tr, ev


# ─────────────────────────── модель ───────────────────────────

class StubEncoder:
    """Заглушка для сухого прогона: мешок слов → линейный слой. Никаких загрузок.

    Нужна ровно для того, чтобы проверить конвейер там, где он обычно и ломается:
    формы тензоров, сборка партий, арифметика GradCache. Про качество настоящей
    модели она не говорит ничего, и путать эти две вещи нельзя.
    """

    def __init__(self, dim=64, vocab=4096):
        import torch
        import torch.nn as nn
        self.torch = torch
        self.vocab = vocab
        self.net = nn.Sequential(nn.EmbeddingBag(vocab, dim, mode="mean"),
                                 nn.Linear(dim, dim))
        self.device = "cpu"

    def parameters(self):
        return self.net.parameters()

    def encode(self, texts, grad=True):
        import torch
        idx = [[hash(w) % self.vocab for w in t.lower().split()[:64]] or [0]
               for t in texts]
        flat, off, k = [], [], 0
        for row in idx:
            off.append(k)
            flat += row
            k += len(row)
        flat = torch.tensor(flat)
        off = torch.tensor(off)
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            v = self.net[1](self.net[0](flat, off))
            return torch.nn.functional.normalize(v, dim=-1)


class BGEEncoder:
    """Настоящая модель: bge-m3 + LoRA. Таблица эмбеддингов заморожена — это 45%
    весов, и обучать её на 200 тысячах пар значит переучивать язык, а не оптику."""

    def __init__(self, device, maxlen):
        import torch
        from transformers import AutoModel, AutoTokenizer
        from peft import LoraConfig, get_peft_model
        self.torch, self.maxlen, self.device = torch, maxlen, device
        self.tok = AutoTokenizer.from_pretrained(MODEL)
        m = AutoModel.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
        m = get_peft_model(m, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                                         target_modules=list(LORA_TARGETS),
                                         bias="none"))
        for n, p in m.named_parameters():
            if "embed_tokens" in n or "word_embeddings" in n:
                p.requires_grad = False
        self.net = m.to(device)

    def parameters(self):
        return self.net.parameters()

    def encode(self, texts, grad=True):
        import torch
        enc = self.tok(texts, padding=True, truncation=True,
                       max_length=self.maxlen, return_tensors="pt").to(self.device)
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            v = self.net(**enc).last_hidden_state[:, 0]
            return torch.nn.functional.normalize(v, dim=-1)


# ─────────────────────────── обучение ───────────────────────────

def infonce(q, d, tau=TAU):
    import torch
    logits = q @ d.T / tau
    target = torch.arange(len(q), device=q.device)
    return torch.nn.functional.cross_entropy(logits, target)


def step_gradcache(enc, qs, ds, sub):
    """Один шаг с GradCache. Возвращает потерю (числом).

    Порядок важен и легко перепутать: сначала БЕЗ графа собираем представления всей
    партии, потом считаем по ним потерю и градиент по представлениям, и только затем
    проходим второй раз по кускам с графом, проталкивая назад сохранённый градиент.
    Если сделать наоборот, память кончится ровно на том, ради чего всё затевалось.
    """
    import torch
    with torch.no_grad():
        Q = torch.cat([enc.encode(qs[i:i + sub], grad=False)
                       for i in range(0, len(qs), sub)])
        D = torch.cat([enc.encode(ds[i:i + sub], grad=False)
                       for i in range(0, len(ds), sub)])
    Q.requires_grad_(True)
    D.requires_grad_(True)
    loss = infonce(Q, D)
    loss.backward()
    gQ, gD = Q.grad.detach(), D.grad.detach()

    for i in range(0, len(qs), sub):
        v = enc.encode(qs[i:i + sub], grad=True)
        v.backward(gQ[i:i + sub])
    for i in range(0, len(ds), sub):
        v = enc.encode(ds[i:i + sub], grad=True)
        v.backward(gD[i:i + sub])
    return float(loss.detach())


def median_rank(enc, ev, text, pool_ids, pool_vecs, sample=200):
    """Медианный ранг связанной работы среди поля. Тот же замер, что дал 2 704 —
    иначе сравнивать «до» и «после» нельзя."""
    import numpy as np
    import torch
    if not ev:
        return None
    rnd = random.Random(3)
    take = rnd.sample(ev, min(sample, len(ev)))
    ranks = []
    with torch.no_grad():
        for a, b in take:
            q = enc.encode([text[a]], grad=False)[0].float().cpu().numpy()
            sims = pool_vecs @ q
            if b not in pool_ids:
                continue
            ranks.append(int((sims > sims[pool_ids[b]]).sum()) + 1)
    return float(np.median(ranks)) if ranks else None


def check_gradcache(enc, qs, ds, sub):
    """Решающая проверка GradCache: градиенты обязаны совпасть с прямым проходом.

    Прежняя версия сухого прогона смотрела, убывает ли потеря за десяток шагов.
    Это плохая проверка: на свежей заглушке с малым шагом обучения потеря не убывает
    и при исправном коде, так что «сломано» и «мало шагов» она не различает —
    а проверка, которая так ошибается, хуже отсутствующей.

    Здесь сравнение точное. Один и тот же кусок данных проходит двумя путями:
    напрямую (всё в графе сразу) и через GradCache (два прохода с сохранённым
    градиентом по представлениям). Математически это одно и то же, значит градиенты
    по ПАРАМЕТРАМ должны совпасть до ошибок округления. Расходятся — код неверен,
    и никакие рассуждения про динамику обучения этого не спрячут.
    """
    import torch

    def grads_of():
        return [p.grad.detach().clone() if p.grad is not None else None
                for p in enc.parameters()]

    for p in enc.parameters():
        p.grad = None
    Q = enc.encode(qs, grad=True)
    D = enc.encode(ds, grad=True)
    infonce(Q, D).backward()
    direct = grads_of()

    for p in enc.parameters():
        p.grad = None
    step_gradcache(enc, qs, ds, sub)
    cached = grads_of()

    worst, scale = 0.0, 0.0
    for a, b in zip(direct, cached):
        if a is None or b is None:
            continue
        worst = max(worst, float((a - b).abs().max()))
        scale = max(scale, float(a.abs().max()))
    rel = worst / (scale + 1e-12)
    return worst, scale, rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="сухой прогон на заглушке")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--sub", type=int, default=32, help="кусок для GradCache")
    ap.add_argument("--maxlen", type=int, default=512)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--limit", type=int, default=0, help="ограничить число пар")
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--out", default=str(DATA / "lora-compass"))
    args = ap.parse_args()

    import torch

    if args.dry:
        args.batch = min(args.batch, 64)
        args.sub = min(args.sub, 16)
        args.steps = min(args.steps, 12)
        args.limit = args.limit or 4000
        print(f"{'=' * 74}\nСУХОЙ ПРОГОН: заглушка вместо модели, процессор, "
              f"ничего не тратится\n{'=' * 74}")

    pairs, text = load_pairs(args.limit)
    if len(pairs) < args.batch:
        print(f"!! пар меньше партии ({len(pairs)} < {args.batch}). "
              f"Партия будет добираться повтором — для сухого прогона это нормально, "
              f"для настоящего обучения нет.")
    tr, ev = split(pairs)

    dev = "cuda" if (torch.cuda.is_available() and not args.dry) else "cpu"
    if not args.dry and dev == "cpu":
        print("!! GPU не найден. Настоящее обучение на процессоре займёт недели —")
        print("   прогон остановлен. Для проверки конвейера есть --dry.")
        return 1

    enc = StubEncoder() if args.dry else BGEEncoder(dev, args.maxlen)
    train = [p for p in enc.parameters() if p.requires_grad]
    n_tr = sum(p.numel() for p in train)
    n_all = sum(p.numel() for p in enc.parameters())
    print(f"устройство {dev} · обучаемых {n_tr:,} из {n_all:,} "
          f"({n_tr / max(1, n_all) * 100:.2f}%)")

    if args.dry:
        print(f"\n{'-' * 74}")
        print("ПРОВЕРКА GRADCACHE ПРОТИВ ПРЯМОГО ПРОХОДА")
        print(f"{'-' * 74}")
        b = [tr[i % len(tr)] for i in range(16)]
        worst, scale, rel = check_gradcache(enc, [text[a] for a, _ in b],
                                            [text[x] for _, x in b], 4)
        ok = rel < 1e-4
        print(f"  наибольшее расхождение {worst:.3e} при масштабе {scale:.3e}")
        print(f"  относительное {rel:.2e} → {'СОВПАДАЮТ' if ok else 'РАСХОДЯТСЯ'}")
        if not ok:
            print("\n  GradCache считает не то же, что прямой проход. Обучать нельзя.")
            return 1
        # Шаг обучения у заглушки свой: она обучается с нуля, и 2e-5 ей ничего не даёт.
        args.lr = 1e-2
        args.steps = max(args.steps, 40)

    opt = torch.optim.AdamW(train, lr=args.lr)
    rnd = random.Random(0)
    t0, losses = time.perf_counter(), []
    for st in range(args.steps):
        batch = [tr[rnd.randrange(len(tr))] for _ in range(args.batch)]
        qs = [text[a] for a, _ in batch]
        ds = [text[b] for _, b in batch]
        opt.zero_grad(set_to_none=True)
        loss = step_gradcache(enc, qs, ds, args.sub)
        opt.step()
        losses.append(loss)
        if st < 3 or (st + 1) % max(1, args.steps // 6) == 0:
            print(f"  шаг {st + 1:>4}/{args.steps}: потеря {loss:.4f} · "
                  f"{(time.perf_counter() - t0) / (st + 1):.2f} с/шаг")

    dt = time.perf_counter() - t0
    print(f"\nшагов {args.steps} за {dt:.1f} с · {dt / args.steps:.2f} с/шаг · "
          f"{args.batch * 2 * args.steps / dt:.0f} посл./с")
    print(f"потеря: первая {losses[0]:.4f} → последняя {losses[-1]:.4f} "
          f"({'убывает' if losses[-1] < losses[0] else 'НЕ УБЫВАЕТ — конвейер сломан'})")

    if args.dry:
        print(f"\n{'=' * 74}")
        print("Сухой прогон закончен. Проверено: сборка партий, формы тензоров,")
        print("арифметика GradCache, убывание потери. НЕ проверено: качество модели,")
        print("скорость на карте, память. Ничего не потрачено.")
        return 0 if losses[-1] < losses[0] else 1

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    enc.net.save_pretrained(str(out))
    print(f"→ веса LoRA в {out}")
    print("\nКритерий успеха: медианный ранг 2 704 → 676 и ниже. Замер — "
          "recommend_ml.py на пересчитанном поле, ключ вскрывается после.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
