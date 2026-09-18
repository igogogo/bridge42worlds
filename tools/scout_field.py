# -*- coding: utf-8 -*-
"""Разведка по темам в локальном поле arXiv: что за год написано про X.

Владелец 18.09.2026: «астрофизику пока отставить, меня интересуют макроквантовые явления,
антиэнтропия и гравитация; антиэнтропия и омоложение связаны — попробуй сам поискать что-то
интересное, а вдруг».

ЧЕМ ИЩЕМ. Не промптом и не словами, а вектором по нашему же полю: 2,96 млн работ arXiv
лежат на диске с эмбеддингами bge-m3. Запрос-тему кодируем той же моделью (Workers AI,
копейки) и считаем близость к каждой работе года. Так находится и то, что не называет
себя нужным словом — «негэнтропия» может звучать как «информационный двигатель» или
«локальное снижение энтропии», и слово не поймало бы, а смысл ловит.

ЭТО РАЗВЕДКА, А НЕ ОТБОР. Разбор здесь не запускается и модель не зовётся: результат —
файл с кандидатами и читаемый список, по которому решает человек.

    python tools/scout_field.py                     все темы, год 2026, по 30 на тему
    python tools/scout_field.py --years 25,26 --top 40
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
# ПОРЯДОК ПУТЕЙ ВАЖЕН. В b42-ml лежат свои копии common.py, gen_arxiv.py, vector_select.py —
# старые, без наших правок. Корень обязан быть ПЕРВЫМ: тогда общие имена берутся отсюда,
# а из b42-ml — только то, чего в корне нет (vecstore, analytics_v2, field_build).
sys.path.insert(0, str(ML))
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

OUT = ROOT / "tools" / "outside" / "pools"

# Несколько формулировок на тему — вектор усредняем. Одна формулировка ловит один говор,
# а физики говорят о том же по-разному.
THEMES = {
    "macro-quantum": [
        "macroscopic quantum superposition of a massive object",
        "quantum coherence and entanglement at macroscopic scale",
        "Schrodinger cat state in a mechanical resonator or large molecule",
        "quantum effects in large systems: superfluidity, optomechanics, macroscopic tunneling",
    ],
    "anti-entropy": [
        "negative entropy and negentropy in living systems",
        "Maxwell demon and information engine reducing entropy",
        "local decrease of entropy, self-organization far from equilibrium",
        "thermodynamics of information: erasure, Landauer bound, feedback control",
    ],
    "gravity": [
        "quantum gravity tabletop experiment",
        "gravitationally induced entanglement between masses",
        "gravitational decoherence of quantum superpositions",
        "entropic or emergent gravity from thermodynamics and information",
    ],
    "entropy-aging-bridge": [
        "thermodynamics of aging and entropy production in organisms",
        "free energy principle, dissipative structures and lifespan",
        "information theory of aging: entropy accumulation and loss of order in cells",
        "physics of life: how organisms maintain low entropy and repair",
    ],
}


def main():
    ap = argparse.ArgumentParser(description="Разведка тем по локальному полю arXiv")
    ap.add_argument("--years", default="26", help="двузначные годы через запятую, напр. 25,26")
    ap.add_argument("--top", type=int, default=30, help="сколько работ на тему")
    ap.add_argument("--out", default="scout-2026.json")
    ap.add_argument("--ours", action="store_true",
                    help="искать только среди НАШИХ разобранных работ (data.json), все годы")
    a = ap.parse_args()

    import numpy as np
    import vecstore
    from analytics_v2 import _field_dir
    import field_build as fb
    import vector_select as vs
    # В b42-ml лежит СВОЯ, старая копия gen_arxiv.py без local_meta, и по sys.path она
    # оказывается первой. Берём модуль по точному пути, а не по имени.
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("gen_arxiv_main", ROOT / "gen_arxiv.py")
    _ga = _iu.module_from_spec(_sp); _sp.loader.exec_module(_ga)
    local_meta = _ga.local_meta

    years = tuple(y.strip() for y in a.years.split(",") if y.strip())
    print(f"поле: читаю индекс …")
    ids, M = vecstore.load(_field_dir() / "field", mmap=True, latest=True)
    # Номера в поле лежат с префиксом «arx:» (та самая ловушка старого написания поля):
    # год виден только после _base_id, иначе фильтр молча отдаёт ноль.
    if a.ours:
        # Что у нас УЖЕ есть по теме (владелец 18.09: «в том числе если у нас что-то есть»):
        # те же запросы, но поле сужаем до наших разобранных работ, годы любые.
        ours = {d.name.split("v")[0] for d in (ROOT / "lang" / "ru" / "archive").glob("*/*") if d.is_dir()}
        print(f"наших работ: {len(ours):,}")
        keep = [i for i, s in enumerate(ids) if fb._base_id(str(s)) in ours]
    else:
        keep = [i for i, s in enumerate(ids) if any(fb._base_id(str(s)).startswith(y) for y in years)]
    print(f"работ в поле: {len(ids):,}; за годы {years}: {len(keep):,}")
    X = np.asarray(M[keep], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    kid = [ids[i] for i in keep]

    env = vs.load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    result = {}
    for theme, qs in THEMES.items():
        Q = np.asarray(vs.embed(qs, acc, tok), dtype=np.float32)
        Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
        q = Q.mean(axis=0)
        q /= np.linalg.norm(q) + 1e-9
        sims = X @ q
        top = np.argsort(-sims)[: a.top]
        rows = []
        for j in top:
            aid = fb._base_id(str(kid[j]))
            m = local_meta(aid) or {}
            rows.append({
                "id": aid, "sim": round(float(sims[j]), 3),
                "title": " ".join((m.get("title") or "").split()),
                "cats": m.get("categories") or [],
                "date": (m.get("published") or "")[:10],
                "abstract": " ".join((m.get("summary") or "").split())[:900],
            })
        result[theme] = rows
        print(f"\n== {theme} ==  (близость топ-1 {rows[0]['sim'] if rows else '—'})")
        for r in rows[:12]:
            print(f"  {r['sim']:.3f} {r['id']:12} [{(r['cats'] or ['?'])[0]:14}] {r['title'][:78]}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / a.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {OUT / a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
