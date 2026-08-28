# -*- coding: utf-8 -*-
"""Определение не объясняет предмет через сам предмет.

Владелец 28.08, глядя на карточку постоянной Планка: «Фундаментальная физическая
постоянная, задающая масштаб квантово-механического квантования» — видно, что
масло масляное, два слова «квант» подряд. В определении повторять нельзя, это
тавтология, надо от неё защиту.

Две болезни, и вторая тяжелее:

  ОДНОКОРЕННЫЕ РЯДОМ — «квантово-механического квантования», «поиск аксионов
  включает поиск аксионной тёмной материи». Слово звучит дважды, второе ничего
  не добавляет.

  КРУГ В ОПРЕДЕЛЕНИИ — «Дополнительные временные измерения — это дополнительные
  временные координаты». Читатель, не знающий предмета, после такого определения
  знает ровно столько же. Это не стилистика, это несделанная работа.

Механически такое не различить: «gravity so strong» в определении чёрной дыры —
не тавтология, а «neutrino … neutral» вообще однокоренные лишь на вид. Поэтому
грубый поиск только собирает кандидатов, а решает и переписывает модель.

Правится английская карточка (она источник и опора вектора) и русская — вместе,
одним запросом: иначе перевод унаследует тавтологию обратно.

    python tools/card_tautology.py                показать, что найдено
    python tools/card_tautology.py --apply        переписать
    python tools/card_tautology.py --limit 50
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import write_json_atomic  # noqa: E402

LIVE = ROOT / "data" / "concepts-live.json"
PER_CALL = 5
WORKERS = 4
WORD = re.compile(r"[А-Яа-яЁёA-Za-z]{6,}")

SYS = """You fix definitions that explain a thing through itself.

For each numbered concept you get: id, Russian name, English card, Russian card.

Two faults to look for:
  CIRCLE    — the definition repeats the term being defined ("Extra time
              dimensions are additional time coordinates"). A reader who did not
              know the term knows no more after reading it.
  ECHO      — two words of the same root stand together and the second adds
              nothing ("quantum mechanical quantization").

If a card has neither, answer "ok" and change nothing. Be strict: a term may
legitimately appear inside a longer phrase ("black hole thermodynamics studies
black holes") when it genuinely names the subject; that is not a circle if the
rest of the sentence explains something.

When fixing, keep: the same fact, the same length (±20%), the same register.
Say WHAT IT IS through simpler notions, not through the term itself. Never
invent facts that are not in the original.

Answer per concept, one JSON object per line:
  {"n": 1, "verdict": "ok"}
  {"n": 2, "verdict": "fix", "en": "<new English card>", "ru": "<новая русская карточка>"}
Nothing else."""


def env(k):
    if os.environ.get(k):
        return os.environ[k]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"нет {k}")


def echoes(text):
    """Однокоренные слова в одном предложении — грубый признак, не приговор."""
    out = []
    for sent in re.split(r"[.;!?]", text or ""):
        seen = {}
        for w in WORD.findall(sent):
            s = w.lower()[:5]
            if s in seen and seen[s].lower() != w.lower():
                out.append((seen[s], w))
            seen.setdefault(s, w)
    return out


def circular(name, card):
    """Определение начинается с повторения имени понятия."""
    if not name or not card:
        return False
    head = name.split()[0].lower()
    if len(head) < 6:
        return False
    tail = card.lower()[len(name):] if card.lower().startswith(name.lower()) else card.lower()
    return head[:6] in tail


def candidates(live):
    out = []
    for cid, v in live.items():
        if v.get("merged_into"):
            continue
        ru = ((v.get("full_i18n") or {}).get("ru") or {}).get("card") or ""
        en = v.get("card_en") or ""
        nm = (v.get("names") or {}).get("ru") or ""
        if not en:
            continue
        why = []
        if echoes(ru) or echoes(en):
            why.append("echo")
        if circular(nm, ru) or circular((v.get("names") or {}).get("en") or "", en):
            why.append("circle")
        if why:
            out.append((cid, nm, en, ru, why))
    # Сначала то, что читают чаще: у понятия со статьями карточку видят живые люди.
    out.sort(key=lambda t: -len(live[t[0]].get("articles") or []))
    return out


def ask(batch, key):
    lines = []
    for i, (cid, nm, en, ru, _why) in enumerate(batch, 1):
        lines.append(f'{i}. {cid} (ru name: "{nm}")')
        lines.append(f'   EN: {en}')
        lines.append(f'   RU: {ru}')
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    dec = json.JSONDecoder()
    s, got, i = raw.strip(), [], 0
    if s.startswith("```"):
        s = s.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    while i < len(s):
        try:
            obj, end = dec.raw_decode(s, i)
        except ValueError:
            nxt = s.find("{", i + 1)
            if nxt < 0:
                break
            i = nxt
            continue
        got.append(obj)
        i = end
        while i < len(s) and s[i] in " \r\n\t,":
            i += 1
    if len(got) == 1 and isinstance(got[0], dict) and "n" not in got[0]:
        for v in got[0].values():
            if isinstance(v, list):
                got = v
                break
    out = {}
    for it in got:
        try:
            n = int(it["n"])
            if 1 <= n <= len(batch):
                out[batch[n - 1][0]] = it
        except (KeyError, TypeError, ValueError):
            continue
    return out


def main():
    ap = argparse.ArgumentParser(description="Лечение тавтологии в карточках")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    live = doc["concepts"]
    cands = candidates(live)
    if a.limit:
        cands = cands[:a.limit]
    print(f"кандидатов: {len(cands)}")
    if not cands:
        return 0

    key = env("DEEPSEEK_API_KEY")
    bs = [cands[i:i + PER_CALL] for i in range(0, len(cands), PER_CALL)]
    got = {}

    def safe(b):
        try:
            return ask(b, key)
        except Exception as e:
            print(f"  пачка пропущена: {type(e).__name__}: {str(e)[:70]}")
            return {}

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for part in ex.map(safe, bs):
            got.update(part)

    fixed = ok = 0
    for cid, nm, en, ru, _why in cands:
        v = got.get(cid)
        if not v or v.get("verdict") != "fix":
            ok += 1
            continue
        new_en, new_ru = (v.get("en") or "").strip(), (v.get("ru") or "").strip()
        if not new_en:
            ok += 1
            continue
        fixed += 1
        if fixed <= 12:
            print(f"  {cid}:\n     было: {ru or en}\n     стало: {new_ru or new_en}")
        if a.apply:
            live[cid]["card_en"] = new_en
            if new_ru:
                live[cid].setdefault("full_i18n", {}).setdefault("ru", {})["card"] = new_ru

    print(f"\nпереписано {fixed} · оставлено как есть {ok}")
    if not a.apply:
        print("проба. применить: --apply")
        return 0
    write_json_atomic(LIVE, doc, indent=None)
    print(f"→ {LIVE.name} обновлён")
    return 0


if __name__ == "__main__":
    sys.exit(main())
