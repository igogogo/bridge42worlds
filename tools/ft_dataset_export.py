# -*- coding: utf-8 -*-
"""Датасет для файн-тюнинга bge-m3 (владелец 27.08: «потом будет рывок в
файн-тюнинг — будем готовы к этому»).

Пары «запрос → карточка понятия» из ПОДТВЕРЖДЁННОЙ разметки — того, что реально
прижилось на сайте, а не сырых кандидатов:

  СИЛЬНЫЕ позитивы — из якорей (concept-mentions.jsonl): дословное выражение
  встретилось в тексте статьи; запрос = предложение вокруг якоря (окно ±240
  символов до границ предложений), позитив = card_en понятия. Русские якоря
  дают кросс-язычные пары ru-текст → en-карточка — то, чем модель и живёт у нас.

  СРЕДНИЕ позитивы — из разметки concepts_v2: запрос = описание статьи
  (description/oneliner), позитив = карточка каждого приписанного понятия.

  HARD NEGATIVES — для каждой пары: карточки 3 ближайших соседей понятия из
  live.related, которых НЕТ в разметке этой статьи. Сосед похож, но разметка
  его отвергла — ровно то, что учит модель различать.

Выход: b42-ml/data/ft-pairs.jsonl
  {"q": "...", "pos": "...", "neg": ["...", ...], "concept": "...",
   "lang": "ru|en", "kind": "anchor|tag"}

Локально и бесплатно; повторный запуск перезаписывает файл целиком
(датасет — производная, не состояние).

    python tools/ft_dataset_export.py [--cap-per-concept 400]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
OUT = ML / "data" / "ft-pairs.jsonl"
MENTIONS = ROOT / "data" / "concept-mentions.jsonl"
LIVE = ROOT / "data" / "concepts-live.json"


def sentence_window(text, pos, span, radius=240):
    """Предложение(я) вокруг вхождения: от границы предложения слева до границы
    справа, не дальше radius символов в каждую сторону."""
    lo = max(0, pos - radius)
    hi = min(len(text), pos + span + radius)
    left = text.rfind(". ", lo, pos)
    lo = left + 2 if left != -1 else lo
    right = text.find(". ", pos + span, hi)
    hi = right + 1 if right != -1 else hi
    return text[lo:hi].strip()


def clean(t):
    t = re.sub(r"\[\[[^\]]*\]\]|\{\{[^}]*\}\}|<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", t).strip()


def article_text(aid, lang):
    """Тексты статьи на языке — все уровни склеены (якорь мог быть найден в любом).
    data.json лежит ОДИН, в ru-дереве; внутри: уровень → язык → {text, concepts_v2}."""
    p = ROOT / "lang" / "ru" / "archive"
    for d in p.glob(f"*/{aid}"):
        try:
            data = json.loads((d / "data.json").read_text(encoding="utf-8"))
        except Exception:
            return None, None
        parts = []
        for lv in ("simple", "popular", "advanced"):
            node = data.get(lv)
            if isinstance(node, dict):
                ln = node.get(lang)
                if isinstance(ln, dict) and ln.get("text"):
                    parts.append(ln["text"])
        return clean("\n".join(parts)), data
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-per-concept", type=int, default=400)
    a = ap.parse_args()
    live = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    cards = {cid: v.get("card_en") or "" for cid, v in live.items()}
    related = {cid: [r["id"] for r in (v.get("related") or [])]
               for cid, v in live.items()}

    # разметка по статьям — для hard negatives
    marked = {}   # aid -> set(concepts)
    text_cache = {}

    def get_text(aid, lang):
        if (aid, lang) not in text_cache:
            text_cache[(aid, lang)] = article_text(aid, lang)
        return text_cache[(aid, lang)]

    def negatives(cid, aid_concepts):
        out = []
        for r in related.get(cid, []):
            if r not in aid_concepts and cards.get(r):
                out.append(cards[r])
            if len(out) >= 3:
                break
        return out

    per_concept = defaultdict(int)
    n_anchor = n_tag = 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        # 1) сильные пары из якорей
        if MENTIONS.exists():
            for line in MENTIONS.open(encoding="utf-8"):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cid = row.get("concept")
                aid = row.get("art") or row.get("article")
                lang = row.get("lang") or "en"
                if not cid or not aid or cid not in cards or not cards[cid]:
                    continue
                if per_concept[cid] >= a.cap_per_concept:
                    continue
                text, data = get_text(aid, lang)
                if not text:
                    continue
                if aid not in marked and data:
                    marked[aid] = set()
                    for lv in ("simple", "popular", "advanced"):
                        node = data.get(lv)
                        if not isinstance(node, dict):
                            continue
                        for ln in node.values():
                            if isinstance(ln, dict) and isinstance(
                                    ln.get("concepts_v2"), list):
                                marked[aid] |= set(ln["concepts_v2"])
                for m in row.get("m") or row.get("mentions") or []:
                    pos = text.find(m)
                    if pos == -1:
                        continue
                    q = sentence_window(text, pos, len(m))
                    if len(q) < 40:
                        continue
                    f.write(json.dumps({
                        "q": q, "pos": cards[cid],
                        "neg": negatives(cid, marked.get(aid, set())),
                        "concept": cid, "lang": lang, "kind": "anchor",
                    }, ensure_ascii=False) + "\n")
                    per_concept[cid] += 1
                    n_anchor += 1
                    break   # одного окна на (статья, понятие, язык) достаточно
        # 2) средние пары из разметки
        for lang in ("ru", "en"):
            idx_p = ROOT / "lang" / lang / "articles-index.json"
            if not idx_p.exists():
                continue
            for art in json.loads(idx_p.read_text(encoding="utf-8")):
                if art.get("version") != "popular":
                    continue
                desc = clean(art.get("description") or art.get("oneliner") or "")
                if len(desc) < 60:
                    continue
                tags = set(art.get("tags") or []) & set(cards)
                for cid in tags:
                    if per_concept[cid] >= a.cap_per_concept or not cards[cid]:
                        continue
                    f.write(json.dumps({
                        "q": desc, "pos": cards[cid],
                        "neg": negatives(cid, tags),
                        "concept": cid, "lang": lang, "kind": "tag",
                    }, ensure_ascii=False) + "\n")
                    per_concept[cid] += 1
                    n_tag += 1
    print(f"✅ пар: {n_anchor} якорных + {n_tag} разметочных = {n_anchor + n_tag}"
          f" → {OUT}")
    print(f"   понятий покрыто: {sum(1 for v in per_concept.values() if v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
