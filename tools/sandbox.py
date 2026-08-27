# -*- coding: utf-8 -*-
"""Песочница: маленькая копия хозяйства для опытов, не трогающая боевое.

Владелец 27.08: «потестируй пайплайн добора, но отдельно, чтобы не мешать
процессу боевому — сделай себе маленькую копию, погоняй».

ЧТО ДЕЛАЕТ --make:
  ../b42-sandbox/                   отдельное дерево рядом с проектом
    tools/, data/prompts/           копии кода и промптов
    data/concepts-live.json         УРЕЗАННЫЙ реестр (N понятий) + их группы
    data/concept-harvest.jsonl      копилка только их кандидатов
    data/*.json                     мелкие состояния — пустые
    lang/ru/archive/…               ССЫЛКА (junction) на реальный архив: только
                                    чтение, копировать 9 ГБ незачем
  ../b42-ml-sandbox/data/           матрица карточек урезана до тех же понятий,
                                    поле статей — junction на реальное (чтение)

Инструменты в песочнице считают своим корнем её саму (ROOT = родитель tools),
поэтому пишут только внутрь неё. Боевые файлы не открываются на запись нигде.

  python tools/sandbox.py --make [--n 300]   собрать песочницу
  python tools/sandbox.py --run "<команда>"  выполнить в песочнице
  python tools/sandbox.py --drop             снести
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
SBX = ROOT.parent / "b42-sandbox"
SBX_ML = ROOT.parent / "b42-ml-sandbox"


def junction(link: Path, target: Path):
    """Ссылка на каталог без копирования (Windows junction, иначе symlink)."""
    if link.exists():
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)


def make(n):
    import numpy as np
    if SBX.exists():
        print(f"песочница уже есть: {SBX} (--drop чтобы снести)")
        return 1
    (SBX / "data" / "prompts").mkdir(parents=True)
    (SBX_ML / "data").mkdir(parents=True, exist_ok=True)

    # код и промпты
    shutil.copytree(ROOT / "tools", SBX / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for f in (ROOT / "data" / "prompts").glob("*.txt"):
        shutil.copy2(f, SBX / "data" / "prompts" / f.name)
    for f in ("concepts_grow.py", "concepts_super.py"):
        if (ML / f).exists():
            shutil.copy2(ML / f, SBX_ML / f)
    shutil.copy2(ROOT / ".env", SBX / ".env")

    # урезанный реестр: N самых опорных понятий и их группы
    live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
    C = live["concepts"]
    keep = [c for c, _ in sorted(C.items(),
                                 key=lambda kv: -len(kv[1].get("articles") or []))[:n]]
    kset = set(keep)
    small = {c: C[c] for c in keep}
    for v in small.values():
        v["related"] = [r for r in (v.get("related") or []) if r["id"] in kset]
    groups = {g: [m for m in mem if m in kset]
              for g, mem in (live.get("groups") or {}).items()}
    groups = {g: m for g, m in groups.items() if m}
    (SBX / "data" / "concepts-live.json").write_text(
        json.dumps({"built": live.get("built", ""), "groups": groups,
                    "concepts": small}, ensure_ascii=False), encoding="utf-8")

    # матрица карточек — только эти понятия
    ids = (ML / "data/concept-cards.ids").read_text(encoding="utf-8").split()
    V = np.fromfile(ML / "data/concept-cards.f16", dtype=np.float16).reshape(len(ids), -1)
    rows = [i for i, c in enumerate(ids) if c in kset]
    V[rows].tofile(SBX_ML / "data" / "concept-cards.f16")
    (SBX_ML / "data" / "concept-cards.ids").write_text(
        "\n".join(ids[i] for i in rows) + "\n", encoding="utf-8")

    # копилка: кандидаты с опорой из этих же статей (первые 2000 строк)
    arts = {a for v in small.values() for a in (v.get("articles") or [])}
    kept = 0
    with (SBX / "data" / "concept-harvest.jsonl").open("w", encoding="utf-8") as out:
        for line in (ROOT / "data/concept-harvest.jsonl").open(encoding="utf-8"):
            r = json.loads(line)
            if arts & set(r.get("articles") or []):
                out.write(line)
                kept += 1
                if kept >= 2000:
                    break

    # прочее мелкое: формулы и отзеркаленные состояния
    for f in ("formulas-linked.json",):
        if (ML / "data" / f).exists():
            shutil.copy2(ML / "data" / f, SBX_ML / "data" / f)
    for f in ("formula-anatomy.json", "wave5-review.json", "articles-retag-v2.json"):
        if (ROOT / "data" / f).exists():
            shutil.copy2(ROOT / "data" / f, SBX / "data" / f)

    # тяжёлое — ссылками, только на чтение
    junction(SBX / "lang", ROOT / "lang")
    for f in ("field.f16", "field.ids", "articles-corpus-ru.json"):
        src = ML / "data" / f
        if src.exists() and not (SBX_ML / "data" / f).exists():
            try:
                os.link(src, SBX_ML / "data" / f)      # жёсткая ссылка, 0 байт
            except OSError:
                pass
    print(f"✅ песочница: {SBX}")
    print(f"   понятий {len(small)} · групп {len(groups)} · кандидатов {kept}")
    print(f"   ML-копия: {SBX_ML}")
    print(f'   запуск:   python tools/sandbox.py --run "tools/group_integrity.py --audit"')
    return 0


def run(cmd):
    if not SBX.exists():
        print("песочницы нет — сначала --make")
        return 1
    # b42-ml внутри песочницы должен указывать на ML-копию: инструменты ищут
    # ROOT.parent/"b42-ml", поэтому кладём junction с этим именем
    junction(SBX.parent / "b42-ml-sbxlink", SBX_ML)
    link = SBX.parent / "b42-ml"
    parts = cmd.split()
    env = dict(os.environ, B42_LEAD="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable] + parts, cwd=SBX, env=env)
    return r.returncode


def drop():
    for p in (SBX, SBX_ML):
        if p.exists():
            # junction внутри сносим отдельно, чтобы не удалить реальный архив
            lang = p / "lang"
            if lang.is_dir() and lang.is_symlink() or (os.name == "nt" and lang.exists()):
                subprocess.run(["cmd", "/c", "rmdir", str(lang)], capture_output=True)
            shutil.rmtree(p, ignore_errors=True)
            print(f"снесено: {p}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Песочница для опытов")
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--run", metavar="CMD")
    ap.add_argument("--drop", action="store_true")
    a = ap.parse_args()
    if a.make:
        return make(a.n)
    if a.run:
        return run(a.run)
    if a.drop:
        return drop()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
