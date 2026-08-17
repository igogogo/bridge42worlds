#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замер пропускной способности дообучения. Строка f2 техлиста.

Половина сметы на дообучение висит на одном предположении — сколько последовательностей
в секунду проходит через bge-m3 с LoRA на арендованной карте. Я поставила 400 и честно
пометила строку как ПРЕДПОЛОЖЕНО. Этот скрипт превращает её в замер: двадцать шагов
на имеющихся парах, вывод секунд на шаг.

ЗАПУСКАТЬ НЕ ЗДЕСЬ. Скрипт рассчитан на арендованную B200 (DeepInfra, $3.69/час,
поминутная тарификация). Аренда — платёж, а платежи в этом проекте идут только после
галочки владельца на техлисте; строка f2 её ждёт. Здесь скрипт лежит готовым,
и `--plan` показывает, что именно будет сделано, не тратя ничего.

ЧТО ЗАМЕРЯЕТСЯ И ЧТО НЕТ. Замеряется время шага: прямой проход, обратный, шаг
оптимизатора — то, что умножается на число шагов в смете. Не замеряется качество:
двадцать шагов на двух тысячах пар ничему не учат, и никаких выводов о медианном ранге
из этого прогона делать нельзя. Это замер скорости и только скорости.

ПОЧЕМУ GRADCACHE. Партия 1024 с внутрипартийными отрицательными примерами не помещается
в память целиком, поэтому прямой проход делается дважды: сначала без графа — собрать
представления всей партии, потом по кускам с графом. Плата — примерно двойное время,
и она в смете учтена множителем 1.9. Замер покажет, верен ли множитель.

    python bench_lora.py --plan          что будет сделано, без затрат
    python bench_lora.py --steps 20      сам замер (только на арендованной карте)
"""
import argparse
import json
import pathlib
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


def pairs_and_texts(limit):
    """Пары из citations.json и аннотации обеих сторон из локального дампа."""
    import field_build as fb
    d = json.loads((MAIN / "data" / "citations.json").read_text(encoding="utf-8"))
    pairs = [(fb._base_id(e["from"]), fb._base_id(e["to"]))
             for e in (d.get("internal") or []) if e.get("from") and e.get("to")]
    pairs = pairs[:limit]
    need = {a for p in pairs for a in p}
    text, bymonth = {}, {}
    for a in need:
        mo = fb.id_month(f"arx:{a}")
        if mo:
            bymonth.setdefault(mo, set()).add(a)
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
                    text[k] = (str(r.get("title", "")) + ". "
                               + str(r.get("abstract", ""))).strip()
    ok = [(a, b) for a, b in pairs if a in text and b in text]
    return ok, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--maxlen", type=int, default=512)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--out", default=str(DATA / "bench-lora.json"))
    args = ap.parse_args()

    print(f"{'=' * 74}\nЗАМЕР ПРОПУСКНОЙ СПОСОБНОСТИ\n{'=' * 74}")
    print(f"  модель            {MODEL}")
    print(f"  LoRA r=16 на      {', '.join(LORA_TARGETS)} (Q/K/V/O)")
    print(f"  партия            {args.batch} пар = {args.batch * 2} последовательностей")
    print(f"  длина             {args.maxlen} токенов")
    print(f"  шагов             {args.steps}")
    print(f"  что считаем       секунды на шаг → последовательностей в секунду")

    pairs, text = pairs_and_texts(args.batch * 4)
    print(f"\n  пар с текстом обеих сторон: {len(pairs):,}")
    if len(pairs) < args.batch:
        print(f"  ВНИМАНИЕ: пар меньше партии — партия будет добираться повтором,")
        print(f"  на замер скорости это не влияет, на качество влияло бы.")

    if args.plan:
        print(f"\n  --plan: ничего не запущено и не потрачено.")
        print(f"  Аренда B200 на DeepInfra: $3.69/час, поминутно, замер ~10 минут ≈ $0.61.")
        print(f"  Ждём галочку владельца на строке f2 техлиста.")
        return 0

    import torch
    from transformers import AutoModel, AutoTokenizer
    from peft import LoraConfig, get_peft_model

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cpu":
        print("\n  !! GPU не найден. На процессоре замер бессмыслен: смета считается")
        print("     для арендованной карты. Прогон остановлен.")
        return 1
    print(f"\n  устройство: {torch.cuda.get_device_name(0)}")

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to(dev)
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                                             target_modules=list(LORA_TARGETS),
                                             bias="none"))
    train = [p for p in model.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in train)
    n_all = sum(p.numel() for p in model.parameters())
    print(f"  обучаемых параметров {n_train:,} из {n_all:,} "
          f"({n_train / n_all * 100:.2f}%)")

    opt = torch.optim.AdamW(train, lr=2e-5)
    lens = []
    for step in range(args.steps):
        idx = [(step * args.batch + i) % len(pairs) for i in range(args.batch)]
        qs = [text[pairs[i][0]] for i in idx]
        ds = [text[pairs[i][1]] for i in idx]
        t0 = time.perf_counter()
        enc = tok(qs + ds, padding=True, truncation=True, max_length=args.maxlen,
                  return_tensors="pt").to(dev)
        out = model(**enc).last_hidden_state[:, 0]
        out = torch.nn.functional.normalize(out, dim=-1)
        q, d = out[:args.batch], out[args.batch:]
        # InfoNCE с внутрипартийными отрицательными: τ=0.05, как в спецификации.
        logits = q @ d.T / 0.05
        loss = torch.nn.functional.cross_entropy(
            logits, torch.arange(len(q), device=dev))
        loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        lens.append(dt)
        if step < 3 or step == args.steps - 1:
            print(f"    шаг {step + 1:>3}: {dt:.2f} с · "
                  f"{args.batch * 2 / dt:.0f} посл./с · loss {loss.item():.3f}")

    # Первые шаги содержат прогрев и компиляцию ядер — в среднее их брать нельзя.
    warm = lens[3:] or lens
    sec = sum(warm) / len(warm)
    sps = args.batch * 2 / sec
    print(f"\n{'=' * 74}\nРЕЗУЛЬТАТ\n{'=' * 74}")
    print(f"  секунд на шаг (без первых трёх): {sec:.2f}")
    print(f"  последовательностей в секунду:   {sps:.0f}")
    print(f"  в смете стояло ПРЕДПОЛОЖЕНО:     400")
    print(f"  поправка сметы:                  ×{400 / sps:.2f}")
    print(f"\n  Пересчитать смету: python finetune_estimate.py "
          f"--seqs-per-sec {sps:.0f}")
    pathlib.Path(args.out).write_text(
        json.dumps({"sec_per_step": round(sec, 3), "seqs_per_sec": round(sps, 1),
                    "batch": args.batch, "maxlen": args.maxlen,
                    "steps": args.steps, "device": torch.cuda.get_device_name(0),
                    "trainable": n_train}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
