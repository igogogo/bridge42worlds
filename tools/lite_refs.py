#!/usr/bin/env python3
"""Лёгкие справочники для браузера: только то, что читатель реально видит.

Замер 13 августа, что качается при заходе на главную:

    lang/ru/articles-index-advanced.json   11.0 МБ
    lang/ru/articles-index.json             9.9 МБ
    lang/ru/articles-index-simple.json      9.0 МБ
    lang/ru/data/tags.json                  4.5 МБ
    lang/ru/data/scientists.json            0.6 МБ
                                         ─────────
                                          ~34 МБ

Владелец 13 августа: «что у нас тормозит для индекса реализации, там расходы вырастут?
У нас пользователей сейчас немного». Расходы не вырастут — Workers Paid уже оплачен и его
норма на три порядка больше нашего трафика. Тормозило другое: страница читает справочники
ЦЕЛИКОМ, хотя показывает из них одно-два поля.

Из tags.json браузер берёт `name` и одно описание для подсказки — остальные двадцать полей
(история, как работает, формулы, сырьё для генерации, промпты картинок) нужны СТРАНИЦЕ
тега, а не ленте. Отсюда файл на 4.5 МБ ради 368 названий.

Здесь мы готовим `*-lite.json`: имя, тип и описание, обрезанное до размера подсказки.
Полные справочники остаются на месте — страницы тегов и законов читают их как раньше.

    python tools/lite_refs.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
_sys.path.insert(0, str(ROOT))
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
TIP = 260          # столько знаков влезает в подсказку; остальное всё равно обрезается


def lite_tags(d):
    out = {}
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        row = {"name": v.get("name", k)}
        for f in ("description_popular", "description_simple", "description"):
            s = (v.get(f) or "").strip()
            if s:
                row[f] = s[:TIP]
        out[k] = row
    return out


def lite_laws(d):
    out = {}
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        row = {"name": v.get("name", k)}
        if v.get("type"):
            row["type"] = v["type"]
        for f in ("description_popular", "description_simple", "description"):
            s = (v.get(f) or "").strip()
            if s:
                row[f] = s[:TIP]
        out[k] = row
    return out


def lite_sci(d):
    out = {}
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        row = {"name": v.get("name", k)}
        for f in ("lifespan", "description"):
            s = (v.get(f) or "").strip()
            if s:
                row[f] = s[:TIP] if f == "description" else s
        out[k] = row
    return out


MAKERS = {"tags.json": lite_tags, "laws.json": lite_laws, "scientists.json": lite_sci}

# ── Второй разрез: имена отдельно от подсказок ──────────────────────────────
#
# Замер 25 августа: в tags-lite.json имена весят 2.3%, три описания — 97.7%. Уровней
# чтения три, показывается один; два лишних едут всегда. А имена нужны в ленте ВСЕГДА
# (иначе вместо «куперовская пара» стоит cooper_pair), описания — только по наведению.
#
# Отсюда два файла вместо одного: имена (~10 КБ, грузятся всегда) и подсказки своего
# уровня (~90 КБ, грузятся при первом наведении). Читатель, который ни на что не навёл,
# не платит за описания вовсе.
KEEP_ALWAYS = {"tags.json": (), "laws.json": ("type",), "scientists.json": ("lifespan",)}
TIP_FIELD = {"popular": "description_popular", "simple": "description_simple",
             "advanced": "description"}


def names_of(lite, extra):
    out = {}
    for k, v in lite.items():
        row = {"name": v.get("name", k)}
        for f in extra:
            if v.get(f):
                row[f] = v[f]
        out[k] = row
    return out


def tips_of(lite, field):
    """Описание одного уровня. Если его нет — берём соседнее: пустая подсказка хуже
    подсказки не того уровня, а у части записей заполнен только один вид."""
    order = [field] + [f for f in ("description_popular", "description", "description_simple")
                       if f != field]
    out = {}
    for k, v in lite.items():
        for f in order:
            if v.get(f):
                out[k] = v[f]
                break
    return out


def main():
    saved = 0
    for lang in LANGS:
        for name, fn in MAKERS.items():
            src = ROOT / "lang" / lang / "data" / name
            if not src.exists():
                continue
            try:
                d = json.loads(src.read_text(encoding="utf-8"))
            except Exception as ex:
                print(f"  ⚠️ {lang}/{name}: {type(ex).__name__}")
                continue
            out = fn(d)
            dst = src.with_name(name.replace(".json", "-lite.json"))
            dst.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            was, now = src.stat().st_size, dst.stat().st_size
            saved += was - now
            print(f"  {lang}/{dst.name}: {was/1e6:.2f} → {now/1e6:.2f} МБ")

            # имена — то, что грузится всегда
            nm = src.with_name(name.replace(".json", "-names.json"))
            nm.write_text(json.dumps(names_of(out, KEEP_ALWAYS[name]), ensure_ascii=False),
                          encoding="utf-8")
            # подсказки — по уровню чтения, грузятся при первом наведении
            tip_sizes = []
            for ver, field in TIP_FIELD.items():
                tp = src.with_name(name.replace(".json", f"-tips-{ver}.json"))
                tp.write_text(json.dumps(tips_of(out, field), ensure_ascii=False),
                              encoding="utf-8")
                tip_sizes.append(tp.stat().st_size)
            print(f"      имена {nm.stat().st_size/1024:.0f} КБ · "
                  f"подсказки {max(tip_sizes)/1024:.0f} КБ на уровень "
                  f"(было {now/1024:.0f} КБ одним куском)")
    print(f"✅ экономия на одном заходе: {saved/1e6/len(LANGS):.1f} МБ "
          f"(суммарно по языкам {saved/1e6:.1f} МБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
