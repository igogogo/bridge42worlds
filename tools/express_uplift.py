"""Дотяжка «Популярно» у экспресс-статей: три уровня становятся настоящими.

Находка внешнего аудита 2026-08-05 (главная): у ~70% архива уровни «Просто», «Популярно»
и «Подробно» — один и тот же текст с баннером-предупреждением. Подтверждено выборкой
104/104. Центральное обещание продукта для большинства статей не выполнялось.

Решение (АУДИТ-ПЛАН п.1): у экспресса настоящий уровень — «Просто» (он и генерится).
«Популярно» ДОТЯГИВАЕТСЯ отдельным дешёвым вызовом: тот же материал, взрослее тон,
термины по имени с пояснением при первом появлении, чуть больше механизма «как именно».
НЕ пересказ заново и НЕ выдумывание: источник фактов — только имеющийся текст.
«Подробно» остаётся честно заблокированным с баннером — для него нужен полный разбор PDF.

    python tools/express_uplift.py --pilot 20      пилот: показать владельцу
    python tools/express_uplift.py --all           весь архив экспрессов (~$3)

Возобновляемый: поднятые пропускаются (по полю uplifted). Проверка записи чтением.
"""
import argparse
import json
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPT = """Ниже — научно-популярный текст уровня «Просто» (для читателя совсем без
подготовки). Подними его до уровня «Популярно»: читатель — взрослый любознательный
человек, который не боится терминов, если их объясняют.

Правила подъёма:
1. ИСТОЧНИК ФАКТОВ — ТОЛЬКО этот текст. Ничего не добавляй из общих знаний: ни чисел,
   ни фактов, ни причин. Если в тексте чего-то нет — этого нет и в подъёме.
2. Верни терминам их имена: там, где «Просто» говорит «частицы-призраки», «Популярно»
   говорит «нейтрино — частицы-призраки, почти не взаимодействующие с веществом».
   Термин + короткое пояснение при первом появлении.
3. Больше механизма: где «Просто» говорит «учёные выяснили», «Популярно» говорит КАК
   выяснили — если это есть в исходном тексте.
4. Аналогии сохраняй — они наша ценность. Можно уточнить, где аналогия упрощает.
5. Маркеры [tag:...]/[scientist:...]/[law:...] сохрани все до единого, те же id.
6. Объём: примерно как исходный, можно на четверть длиннее. Тот же язык (русский).

Верни JSON: {"title": "...", "text": "...", "description": "..."}
title — можно чуть строже исходного; description — 3-4 предложения для карточки уровня.

ИСХОДНЫЙ ТЕКСТ:
"""


def uplift(d, chat, clean_json):
    ru = d["simple"]["ru"]
    src = f"Заголовок: {ru.get('title','')}\n\n{ru.get('text','')}"
    r = chat("article_popular", PROMPT + src)
    out = json.loads(clean_json(r.choices[0].message.content))
    if len(out.get("text", "")) < len(ru.get("text", "")) * 0.6:
        raise ValueError("подъём подозрительно короткий — не записываю")
    # Маркеры обязаны выжить все: по ним граф и связи.
    import re
    mk = lambda s: sorted(re.findall(r"\[(?:tag|scientist|law):[^\]]+\]", s or ""))
    if mk(out.get("text")) != mk(ru.get("text")):
        raise ValueError("маркеры не сошлись — не записываю")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    from common import chat, clean_json
    targets = []
    for p in sorted(ROOT.glob("lang/ru/archive/*/*/data.json"), reverse=True):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not d.get("express"):
            continue
        po = (d.get("popular", {}) or {}).get("ru") or {}
        if po.get("uplifted"):
            continue
        s = (d.get("simple", {}) or {}).get("ru") or {}
        if isinstance(s, dict) and s.get("text"):
            targets.append(p)
        if args.pilot and len(targets) >= args.pilot:
            break
    print(f"к подъёму: {len(targets)}")

    ok = fail = 0
    for p in targets:
        d = json.loads(p.read_text(encoding="utf-8"))
        try:
            out = uplift(d, chat, clean_json)
        except Exception as e:
            fail += 1
            print(f"  ✗ {p.parent.name}: {e}")
            continue
        po = d["popular"]["ru"]
        po["title"] = out.get("title") or po.get("title")
        po["text"] = out["text"]
        if out.get("description"):
            po["description"] = out["description"]
        po["uplifted"] = time.strftime("%Y-%m-%d")
        po.pop("express_locked", None)   # уровень стал настоящим — баннер снимается
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        check = json.loads(p.read_text(encoding="utf-8"))
        if check["popular"]["ru"].get("uplifted"):
            ok += 1
            print(f"  ✅ {p.parent.name} · {out.get('title','')[:50]}")
        else:
            fail += 1
    print(f"\nподнято {ok}, отказов {fail}")
    print("дальше: перевод поднятого уровня на языки — той же механикой, что всегда")
    return 0


if __name__ == "__main__":
    sys.exit(main())
