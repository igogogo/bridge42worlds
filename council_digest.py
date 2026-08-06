#!/usr/bin/env python3
"""Сведение предложений совета в повестку.

Что делает: берёт сырые предложения от участников и превращает их в вопросы повестки —
объединяет одинаковое, отсекает уже сделанное, приводит формулировки в человеческий вид.

ЧЕГО НЕ ДЕЛАЕТ И ДЕЛАТЬ НЕ ДОЛЖНА. Модель не отклоняет предложения по существу. Совсем.
Решать, нужен проекту вопрос или нет, — только голосованием совета. Иначе получится, что
модель тихо отфильтровала неудобное, а мы этого даже не заметили: ровно тот молчаливый
откат, который мы в своём коде считаем худшим классом ошибок. Здесь он был бы хуже —
он касался бы людей.

Поэтому у сведения ровно три права:
  · объединить два предложения об одном и том же (обе исходные формулировки сохраняются);
  · пометить предложение как «уже сделано», ЕСЛИ оно совпадает со сделанным (с указанием,
    чем именно — проверяемо человеком);
  · переписать формулировку понятнее, не меняя смысла.
Всё остальное идёт в повестку как есть, даже если выглядит странно.

Результат — ЧЕРНОВИК повестки. Человек смотрит его глазами и только потом кладёт
в data/council/<дата>.json. Скрипт ничего не публикует сам.

Вход:  data/council/входящие.jsonl — по строке на предложение:
       {"text": "...", "from": "B42-XXXX", "at": "2026-08-01"}
Выход: data/council/черновик-<дата>.json

Запуск:
    python council_digest.py 2026-08-04            # свести к заседанию
    python council_digest.py 2026-08-04 --dry      # показать, что пришло, без модели
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "data" / "council"
INBOX = DIR / "входящие.jsonl"

SYSTEM = """Ты помогаешь секретарю наблюдательного совета свести предложения участников
в повестку заседания.

ТВОИ ПРАВА РОВНО ТРИ:
1. Объединить предложения об ОДНОМ И ТОМ ЖЕ в один вопрос.
2. Пометить предложение как уже сделанное, если оно прямо совпадает с пунктом из списка
   «уже сделано» ниже. Обязательно укажи, с каким именно.
3. Переписать формулировку понятнее, НЕ МЕНЯЯ смысла.

ЧЕГО ТЕБЕ НЕЛЬЗЯ:
— отклонять предложение потому, что оно кажется тебе неважным, странным, дорогим или
  неудобным. Это решает совет голосованием, не ты. Сомневаешься — оставляй как вопрос.
— выдумывать предложения, которых не было.
— терять авторство: у каждого вопроса перечисли всех, от кого он пришёл.

ОТВЕТ — строго JSON:
{"agenda": [{"title": "заголовок одной строкой",
             "body": "суть: что предлагается и почему это вопрос",
             "from": ["ключ или имя"],
             "merged": ["исходная формулировка 1", "исходная формулировка 2"],
             "options": ["За", "Против", "Отложить"],
             "already_done": "" }]}

В options предложи варианты голосования по смыслу вопроса: где уместен выбор из
нескольких путей — перечисли пути, иначе оставь За/Против/Отложить.
В already_done — пусто, либо название того, что уже сделано и покрывает предложение.
Никакого текста вне JSON."""


def load_inbox():
    if not INBOX.exists():
        return []
    out = []
    for line in INBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  ⚠️ строка не разобралась, пропускаю: {line[:60]}")
    return out


def done_list():
    """Список уже сделанного — чтобы модель могла честно пометить повтор.
    Берём из закрытых заседаний: что было принято и у чего заполнено «что вышло»."""
    done = []
    for f in sorted(DIR.glob("*.json")):
        if f.name.startswith("черновик-"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in d.get("agenda") or []:
            if item.get("decision") == "принято" and item.get("outcome"):
                done.append(f'{item.get("title")} — {item.get("outcome")}')
        for x in (d.get("sprint") or {}).get("done") or []:
            done.append(x)
    return done


def digest(items, done):
    from common import chat, clean_json
    payload = {
        "предложения": [{"text": i.get("text", ""), "from": i.get("from", "аноним")}
                        for i in items],
        "уже сделано": done,
    }
    resp = chat("translate_flash",
                json.dumps(payload, ensure_ascii=False, indent=1),
                system=SYSTEM)
    text = (resp.choices[0].message.content or "").strip()
    return json.loads(clean_json(text))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    when = args[0] if args else date.today().isoformat()

    items = load_inbox()
    print(f"предложений во входящих: {len(items)}")
    if not items:
        print(f"положи их в {INBOX.relative_to(ROOT)} — по строке json на предложение")
        return 1
    for i in items:
        print(f"  · [{i.get('from','аноним')}] {str(i.get('text',''))[:80]}")
    if dry:
        return 0

    done = done_list()
    print(f"известно сделанного: {len(done)} пунктов")
    try:
        result = digest(items, done)
    except Exception as e:
        print(f"❌ сведение не удалось ({type(e).__name__}: {e}) — повестку придётся свести руками")
        return 1

    agenda = result.get("agenda") or []
    # Страховка от потери: сведение не имеет права выбросить предложение молча.
    # Если исходных формулировок в сумме меньше, чем пришло, — говорим об этом ГРОМКО.
    kept = sum(len(a.get("merged") or [a.get("title", "")]) for a in agenda)
    if kept < len(items):
        print(f"⚠️  ВНИМАНИЕ: пришло {len(items)} предложений, в повестке отражено {kept}. "
              f"Проверь черновик глазами — что-то потерялось.")

    out = DIR / f"черновик-{when}.json"
    out.write_text(json.dumps({
        "date": when, "status": "план",
        "agenda": [{**a, "votes": {}, "decision": "", "why": "", "outcome": ""}
                   for a in agenda],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nчерновик повестки: {out.relative_to(ROOT)} — {len(agenda)} вопросов")
    print("Посмотри глазами, потом перенеси в заседание и запусти council_build.py")
    for a in agenda:
        mark = f'  [уже сделано: {a["already_done"]}]' if a.get("already_done") else ""
        print(f"  · {a.get('title','')}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
