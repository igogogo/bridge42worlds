# -*- coding: utf-8 -*-
"""Английское имя понятия: то, как это пишет область, а не как выглядит идентификатор.

Сессия панели 08.09: «имена в name_en похожи на идентификаторы: „nino 3 4“, „ersst“,
всё строчными. Правильнее настоящие имена в данных: „Niño 3.4“, „ERSST“».

Справедливо, и болезнь шире панели: русское имя у понятий есть у всех, английского нет
ни у кого — витрины показывали идентификатор с подчёркиваниями вместо пробелов. Для
«bjerknes feedback» это сходило, для «nino 3 4» и «ersst» уже нет: сокращения пишутся
прописными, диакритика значима, числа с точкой.

Заполняем `names.en` в реестре — там же, где живёт `names.ru`, то есть польза сразу всем
витринам, а не одной панели.

Два источника, в этом порядке:
  1. СЛОВАРЬ ПАНЕЛИ (data/enso/glossary.json) — там имена написаны рукой человека:
     «Niño 3.4», «ONI», «CUSUM». Бесплатно и точнее модели.
  2. МОДЕЛЬ — на остальные, пачками по полсотни. Просим НЕ переводить и не объяснять, а
     записать общепринятое написание термина: заглавные там, где это сокращение, имя
     учёного с большой буквы, диакритика на месте.

    python tools/concept_names_en.py --plan            сколько и что
    python tools/concept_names_en.py --run [--only F]  заполнить (F — файл со списком id)
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIVE = ROOT / "data" / "concepts-live.json"
GROWN = ROOT / "data" / "concepts-grown.json"
GLOSS = ROOT / "data" / "enso" / "glossary.json"
BATCH = 50

PROMPT = """You are normalising concept identifiers into the names the field actually writes.

For each identifier below, return the conventional English rendering:
- acronyms in capitals: ersst -> "ERSST", oni -> "ONI", era5 -> "ERA5", gpcp -> "GPCP";
- region and index names as printed: nino_3_4 -> "Niño 3.4", nino_1_2 -> "Niño 1+2";
- people's names capitalised: bjerknes_feedback -> "Bjerknes feedback",
  hurst_exponent -> "Hurst exponent", zebiak_cane_model -> "Zebiak-Cane model";
- everything else in sentence case: ocean_heat_content -> "ocean heat content".

Do NOT translate, do NOT explain, do NOT expand an acronym into words.
Answer with a JSON object {"identifier": "Name", ...} and nothing else.

IDENTIFIERS:
%s
"""


def glossary_names():
    """Имена, написанные рукой: ключ понятия → отображаемое имя."""
    out = {}
    try:
        g = json.loads(GLOSS.read_text(encoding="utf-8"))["en"]
    except Exception:                                            # noqa: BLE001
        return out
    for v in g.values():
        name = (v.get("name") or "").strip()
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9]+", "_",
                      name.lower().replace("ñ", "n").replace("é", "e")).strip("_")
        if slug:
            out[slug[:48]] = name
    return out


def ask(ids):
    from tools.concept_harvest import env
    key = env("DEEPSEEK_API_KEY")
    body = json.dumps({"model": "deepseek-chat",
                       "messages": [{"role": "user", "content": PROMPT % "\n".join(ids)}],
                       "temperature": 0, "max_tokens": 2000}).encode("utf-8")
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    raw = d["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else {}


def main():
    ap = argparse.ArgumentParser(description="Английские имена понятий")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", help="файл со списком id (по одному на строку)")
    a = ap.parse_args()

    reg = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    want = None
    if a.only:
        want = {l.strip() for l in Path(a.only).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")}
    todo = [k for k, v in reg.items()
            if not (v.get("names") or {}).get("en") and (want is None or k in want)]
    gl = glossary_names()
    free = [k for k in todo if k in gl]
    print(f"без английского имени: {len(todo)} · из них словарь панели закрывает {len(free)}")
    print(f"остальные пачками по {BATCH}: ~{(len(todo) - len(free) + BATCH - 1) // BATCH} вызовов")
    if not a.run:
        for k in todo[:8]:
            print(f"   {k} → {gl.get(k) or '(спросим модель)'}")
        return 0

    names = {k: gl[k] for k in free}
    rest = [k for k in todo if k not in names]
    for i in range(0, len(rest), BATCH):
        part = rest[i:i + BATCH]
        try:
            got = ask(part)
        except Exception as e:                                   # noqa: BLE001
            print(f"  пачка {i // BATCH + 1}: сбой {str(e)[:70]}")
            continue
        for k in part:
            v = (got.get(k) or "").strip()
            if v and len(v) < 60:
                names[k] = v
        print(f"  {min(i + BATCH, len(rest))}/{len(rest)}")

    # Пишем и в живой реестр, и в дельту: живой пересобирается из дельты, и без второй
    # записи имена исчезли бы на первом же live-1 (тем же способом теряли русские имена).
    for k, v in names.items():
        reg[k].setdefault("names", {})["en"] = v
    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    doc["concepts"] = reg
    LIVE.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if GROWN.exists():
        grown = json.loads(GROWN.read_text(encoding="utf-8"))
        for k, v in names.items():
            if k in grown:
                grown[k].setdefault("names", {})["en"] = v
        GROWN.write_text(json.dumps(grown, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ английских имён проставлено: {len(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
