#!/usr/bin/env python3
"""Имена понятий по языкам — отдельным хранилищем, а не только в живом реестре.

ЧТО СЛУЧИЛОСЬ. Реестр `data/concepts-live.json` СОБИРАЕТСЯ ЗАНОВО из исходников
(tools/wave5_apply.py, build_live) — это и есть его устройство: он производная, а
не место хранения. Переводчик имён писал результат прямо в него, и первая же
пересборка стёрла работу: 30 августа испанские, арабские и французские имена
упали с 3 609 до 530.

Это ВТОРОЙ раз. 27 августа ровно так же потерялись русские имена (3 231 → 529),
и тогда завели `data/concept-names-ru.json`, который пересборка вливает обратно.
Урок записали для одного языка, а болезнь была общая.

Здесь хранилище на любой язык: `data/concept-names-<язык>.json` вида {id: имя}.
Пересборка реестра вливает их все (см. build_live), а переводчик пишет сюда.

    python tools/concept_names_store.py --from-live      снять имена из текущего реестра
    python tools/concept_names_store.py --from-git       снять из последнего коммита реестра
    python tools/concept_names_store.py --check          что лежит в хранилищах
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import ALL_LANGS                                        # noqa: E402

LIVE = ROOT / "data" / "concepts-live.json"


def store(lang):
    return ROOT / "data" / f"concept-names-{lang}.json"


def load(raw):
    return json.loads(raw)["concepts"]


def harvest(concepts):
    """Разложить имена реестра по языковым хранилищам. Возвращает {язык: сколько}."""
    got = {}
    for lang in ALL_LANGS:
        names = {cid: (v.get("names") or {}).get(lang)
                 for cid, v in concepts.items()
                 if (v.get("names") or {}).get(lang)}
        if not names:
            continue
        p = store(lang)
        # Не затираем: хранилище — это накопитель. Уже лежащее имя старше и, если
        # его правили руками, правка не должна пропасть под автоматической заливкой.
        old = {}
        if p.exists():
            try:
                old = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                old = {}
        merged = dict(names)
        merged.update({k: v for k, v in old.items() if v})
        p.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        got[lang] = len(merged)
    return got


def main():
    ap = argparse.ArgumentParser(description="Хранилище имён понятий по языкам")
    ap.add_argument("--from-live", action="store_true")
    ap.add_argument("--from-git", action="store_true",
                    help="снять из последнего коммита реестра — когда текущий уже обеднел")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if a.check or not (a.from_live or a.from_git):
        for lang in ALL_LANGS:
            p = store(lang)
            n = len(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else 0
            print(f"{lang}: {n} имён" + ("" if p.exists() else "  (хранилища нет)"))
        return 0

    if a.from_git:
        raw = subprocess.run(["git", "show", "HEAD:data/concepts-live.json"],
                             cwd=ROOT, capture_output=True).stdout.decode("utf-8")
        concepts = load(raw)
        print(f"из коммита: понятий {len(concepts)}")
    else:
        concepts = load(LIVE.read_text(encoding="utf-8"))
        print(f"из живого реестра: понятий {len(concepts)}")

    got = harvest(concepts)
    for lang, n in got.items():
        print(f"  {lang}: {n} имён → {store(lang).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
