#!/usr/bin/env python3
"""Переводит справочники (tags.json, scientists.json, laws.json) с языка по умолчанию
на остальные языки из config.json.

Возобновляемый: результат пишется после каждой пачки, уже переведённые записи не переводятся
повторно. Пачки идут ПАРАЛЛЕЛЬНО (config.translate.workers). Промт — data/prompts/reference-translate.txt;
модель — config.agents.translate_ref. Добавили язык в config.json → просто запустите ещё раз.

Запуск:
    python reference_translate.py        # все языки из config.json
    python reference_translate.py de      # только конкретный язык
"""

import sys, json
from pathlib import Path
from string import Template
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import CONFIG, LANGUAGES, DEFAULT_LANG, chat, load_prompt, parse_json_salvage
from gen_llm import CULTURE_NOTES

TCFG = CONFIG.get("translate", {})
BATCH = TCFG.get("batch", 5)
WORKERS = TCFG.get("workers", 5)

LANG_NAMES = {
    "ru": "Russian", "en": "English", "cn": "Chinese", "zh": "Chinese",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "nl": "Dutch",
}


def translate_chunk(chunk, lang_name, lang=""):
    prompt = Template(load_prompt("reference-translate")).safe_substitute(
        lang_name=lang_name, payload=json.dumps(chunk, ensure_ascii=False),
        culture_note=CULTURE_NOTES.get(lang, ""))
    r = chat("translate_ref", prompt)
    data = parse_json_salvage(r.choices[0].message.content)
    if data is None:
        return {}
    items = data.get("items", data)
    return items if isinstance(items, dict) else {}


SCI_TEXT_FIELDS = ["description", "biography", "fun_fact", "quote"]
SCI_LIST_FIELDS = ["fields", "key_discoveries"]


def translate_scientists(targets):
    """Учёные — ОТДЕЛЬНО от tags/laws: имя учёного = ключ словаря = отображаемое имя ВЕЗДЕ,
    его нельзя терять/путать при переводе. Шлём МАССИВ полей-для-перевода (без id вообще —
    ключ никогда не покидает Python), сверяем ответ ПО ПОЗИЦИИ, а не по ключу — так LLM
    физически не может «перевести» или перепутать id. lifespan/related_tags/name копируются
    из исходника без изменений."""
    src_path = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    if not src_path.exists():
        return
    source = json.loads(src_path.read_text(encoding="utf-8"))
    if not source:
        return

    def translate_batch(lang, lang_name, out_path, done, done_lock, sids):
        payload = [
            {**{f: source[sid].get(f, "") for f in SCI_TEXT_FIELDS},
             **{f: source[sid].get(f, []) for f in SCI_LIST_FIELDS}}
            for sid in sids
        ]
        prompt = Template(load_prompt("scientist-translate")).safe_substitute(
            lang_name=lang_name, payload=json.dumps(payload, ensure_ascii=False),
            culture_note=CULTURE_NOTES.get(lang, ""))
        try:
            r = chat("translate_ref", prompt)
            data = parse_json_salvage(r.choices[0].message.content)
        except Exception as e:
            print(f"   ❌ {lang}/scientists.json пачка: {e}")
            return 0
        items = (data or {}).get("items", [])
        if not isinstance(items, list) or len(items) != len(sids):
            print(f"   ⚠️ {lang}/scientists.json: пачка вернулась не той длины ({len(items) if isinstance(items, list) else '?'} vs {len(sids)}) — пропускаю, доберётся следующим прогоном")
            return 0
        merged = 0
        with done_lock:
            for sid, translated in zip(sids, items):
                entry = dict(source[sid])
                for f in SCI_TEXT_FIELDS + SCI_LIST_FIELDS:
                    if translated.get(f):
                        entry[f] = translated[f]
                done[sid] = entry
                merged += 1
            out_path.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
        return merged

    for lang in targets:
        out_path = Path(f"lang/{lang}/data/scientists.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        done = {}
        if out_path.exists():
            try:
                done = json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                done = {}
        missing = [sid for sid in source if sid not in done]
        if not missing:
            print(f"✅ {lang}/scientists.json: уже полный ({len(done)})")
            continue
        lang_name = LANG_NAMES.get(lang, lang)
        lock = Lock()
        batches = [missing[i:i + BATCH] for i in range(0, len(missing), BATCH)]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            merged_counts = list(ex.map(
                lambda b: translate_batch(lang, lang_name, out_path, done, lock, b), batches))
        print(f"   +{sum(merged_counts)} {lang}/scientists.json ({len(done)}/{len(source)})")


def translate_about(targets):
    """Страница-гид About: переводимые строки lang/{DEFAULT}/data/about.json → на целевые языки.
    Плоский словарь {ключ: строка-с-инлайн-HTML}; отдельный промт (reference-translate-about)
    бережёт теги и фиксированные токены (бренд, #black_hole, arXiv, латинские метки, эмодзи).
    Резюмируемо: уже полный about.json пропускаем — так add-lang авто-переводит гид новому языку,
    не трогая существующие. about.json мал (≈70 строк) → один вызов на язык, без батчинга."""
    src_path = Path(f"lang/{DEFAULT_LANG}/data/about.json")
    if not src_path.exists():
        print("⏭️ about.json (источник) не найден — пропускаю гид")
        return
    source = json.loads(src_path.read_text(encoding="utf-8"))
    for lang in targets:
        out_path = Path(f"lang/{lang}/data/about.json")
        done = {}
        if out_path.exists():
            try:
                done = json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                done = {}
        missing = {k: v for k, v in source.items() if k not in done}
        if not missing:
            print(f"✅ {lang}/about.json: уже полный ({len(done)})")
            continue
        lang_name = LANG_NAMES.get(lang, lang)
        prompt = Template(load_prompt("reference-translate-about")).safe_substitute(
            lang_name=lang_name, payload=json.dumps(missing, ensure_ascii=False))
        try:
            r = chat("translate_ref", prompt)
            items = parse_json_salvage(r.choices[0].message.content) or {}
        except Exception as e:
            print(f"   ❌ {lang}/about.json: {e}")
            continue
        for k, v in items.items():
            if k in source:
                done[k] = v
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   +{len(items)} {lang}/about.json ({len(done)}/{len(source)})")


def main():
    targets = [sys.argv[1]] if len(sys.argv) > 1 else [l for l in LANGUAGES if l != DEFAULT_LANG]
    print(f"🌐 Перевод справочников: {DEFAULT_LANG} → {', '.join(targets) or '(нет целей)'}")

    # Все задачи (файл × язык × чанк) собираем в ОДИН пул — иначе файлы/языки шли бы гуськом,
    # недозагружая воркеров. Состояние (done+lock) — на каждую пару (файл, язык).
    states = {}   # (fname, lang) -> {out, done, source, lock}
    tasks = []    # (key, chunk, lang_name)
    for fname in ["tags.json", "laws.json"]:
        src_path = Path(f"lang/{DEFAULT_LANG}/data/{fname}")
        if not src_path.exists():
            print(f"⏭️ {src_path} не найден — пропускаю")
            continue
        source = json.loads(src_path.read_text(encoding="utf-8"))
        for lang in targets:
            out_path = Path(f"lang/{lang}/data/{fname}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            done = {}
            if out_path.exists():
                try:
                    done = json.loads(out_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    done = {}
            missing = [k for k in source if k not in done]
            if not missing:
                print(f"✅ {lang}/{fname}: уже полный ({len(done)})")
                continue
            key = (fname, lang)
            states[key] = {"out": out_path, "done": done, "source": source, "lock": Lock()}
            lang_name = LANG_NAMES.get(lang, lang)
            for i in range(0, len(missing), BATCH):
                tasks.append((key, {k: source[k] for k in missing[i:i + BATCH]}, lang_name))

    if not tasks:
        print("🎉 Готово! (нечего переводить в tags/laws)")
    else:
        print(f"🌐 Всего задач-пачек: {len(tasks)} на {WORKERS} потоков (единый пул)")

        def work(task):
            key, chunk, lang_name = task
            try:
                items = translate_chunk(chunk, lang_name, lang=key[1])
            except Exception as e:
                return (key, 0, str(e))
            st = states[key]
            with st["lock"]:
                merged = 0
                for k, v in items.items():
                    if k in st["source"]:
                        st["done"][k] = v
                        merged += 1
                st["out"].write_text(json.dumps(st["done"], ensure_ascii=False, indent=2), encoding="utf-8")
            return (key, merged, None)

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for key, merged, err in ex.map(work, tasks):
                fname, lang = key
                if err:
                    print(f"   ❌ {lang}/{fname} пачка: {err}")
                else:
                    st = states[key]
                print(f"   +{merged} {lang}/{fname} ({len(st['done'])}/{len(st['source'])})")

    translate_scientists(targets)
    translate_about(targets)
    print("🎉 Готово!")


if __name__ == "__main__":
    main()
