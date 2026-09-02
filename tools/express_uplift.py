"""ОТМЕНЁН 2026-09-01. Поднимал «Популярно» из «Просто» — так больше не делаем.

Инструмент оставлен как история решения, а не как рабочий: запускаться он отказывается.
Живая дотяжка — tools/deep_uplift.py.

ЧТО ОН ДЕЛАЛ И ПОЧЕМУ ЭТО КАЗАЛОСЬ ПРАВИЛЬНЫМ. Внешний аудит 05.08 нашёл главное: у ~70%
архива три уровня чтения — один и тот же текст с баннером. Ответом стал дешёвый подъём:
взять «Просто» (написанное по авторской аннотации) и переписать его взрослее — термины по
имени, чуть больше механизма. Источник фактов — только имеющийся текст, ничего не
выдумывать. Уровень переставал быть клоном, и стоило это копейки.

ПОЧЕМУ ЭТО ВСЁ РАВНО НЕВЕРНО. Тон становился популярным, а знание оставалось прежним:
под уровнем лежала аннотация — несколько предложений витрины, которые автор пишет для
привлечения, а не тело работы с методикой, оговорками и настоящими результатами.
Читатель, открывший «Популярно», вправе ждать, что ниже есть чем подпереть. Так поднято
2 090 статей, и они опаснее прямо заблокированных: выглядят готовыми.

Владелец 2026-09-01, когда цепочку разобрали вслух: «популярно из просто не делаем;
популярная версия должна базироваться на advanced». Направление одно и оно исходное:
текст работы → «Подробно» → «Популярно». Разбирать есть из чего — fulltext.txt и PDF
лежат рядом с 6 010 экспрессами из 6 024.

    python tools/deep_uplift.py --plan       очередь настоящей дотяжки
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
    # ОТКАЗ ЗАПУСКАТЬСЯ — В КОДЕ, А НЕ В ЗАПИСКЕ. Шаг стоял в ежедневном конвейере и
    # тихо работал месяц; убрать его из одного места и понадеяться, что никто не позовёт
    # руками, значит оставить ту же грабельку под ногой. Отказ здесь покрывает и
    # расписание, и чужую сессию, и собственную забывчивость.
    print("⛔ Дотяжка «Популярно из Просто» отменена 2026-09-01 (см. заголовок файла).")
    print("   Популярное строится только из «Подробно», а «Подробно» — из текста работы.")
    print("   Живой инструмент: python tools/deep_uplift.py --plan")
    return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int)
    ap.add_argument("--all", action="store_true")
    # Перевод поднятого уровня. Аудит 16 августа: дотяжка была сделана только для ru,
    # «en 2 / es 2 / ar 1 — приоритетная аудитория читает копии». Поднять текст и не
    # перевести его значит починить уровень на одном языке и оставить обман на четырёх.
    # Начинаем с арабского — по аудиту и по решению владельца об аудитории.
    ap.add_argument("--translate", default="", metavar="ar,en",
                    help="перевести поднятый популярный на эти языки")
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
        # Перевод поднятого — сразу, тем же проходом: отложенный перевод это ещё один
        # кран, который потом кто-то забудет закрыть.
        for tl in [x.strip() for x in args.translate.split(",") if x.strip()]:
            try:
                from gen_llm import translate_scipop
                tr = translate_scipop(po, tl)
                if tr:
                    d["popular"][tl] = tr
            except Exception as e:
                print(f"    ⚠️ перевод {tl}: {type(e).__name__}")
        if args.translate:
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
