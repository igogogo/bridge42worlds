#!/usr/bin/env python3
"""Цепочка владельца (2026-07-30, ночь): прожить воронку руками до раздачи заданий.
Экспресс → полная поверх → что реюзается, что теряется, какие языки где.
Пишет матрицу состояний в temp/chain-test/report.md."""
import json, sys, io
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
import generate as G
from gen_arxiv import fetch_arxiv

OUT = Path("temp/chain-test"); OUT.mkdir(parents=True, exist_ok=True)
DATE = "2026-07-29"
inputs = G.load_generation_inputs()

# кандидат: свежий, с чистой лицензией, которого у нас нет
have = {p.name for p in (Path(G.LANG_DIR)/G.DEFAULT_LANG/"archive").glob("*/*")}
cand = None
for a in fetch_arxiv(DATE):
    if a["id"] in have: continue
    cand = a; break
assert cand, "кандидат не найден"
print("кандидат:", cand["id"], cand["title"][:60])

def snapshot(tag):
    dj = Path(G.LANG_DIR)/G.DEFAULT_LANG/"archive"/DATE/cand["id"]/"data.json"
    if not dj.exists(): return {tag: "нет data.json"}
    d = json.loads(dj.read_text(encoding="utf-8"))
    snap = {"express": d.get("express"), "express_tiers": d.get("express_tiers")}
    for tier in ("popular","simple","advanced"):
        td = d.get(tier) or {}
        snap[tier] = {l: ("RU-текст" if G.payload_in_source_lang(td.get(l)) and l!="ru"
                          else ("есть" if td.get(l) else "—")) for l in G.LANGUAGES}
    pop_ru = (d.get("popular") or {}).get("ru") or {}
    snap["mini_len"] = len((pop_ru.get("mini") or pop_ru.get("threads") or ""))
    snap["mini_text_head"] = (pop_ru.get("mini") or pop_ru.get("threads") or "")[:80]
    (OUT/f"{tag}.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    return snap

print("\n=== ШАГ 1: экспресс штатным путём (все языки) ===")
r1 = G.build_article(dict(cand), DATE, inputs, express=True)
s1 = snapshot("step1-express")
print(json.dumps(s1, ensure_ascii=False, indent=1))

print("\n=== ШАГ 2: полная ПОВЕРХ экспресса (as on-demand) ===")
r2 = G.build_article(dict(cand), DATE, inputs, force=True, express=False)
s2 = snapshot("step2-full")
print(json.dumps(s2, ensure_ascii=False, indent=1))

rep = ["# Цепочка экспресс→полная: матрица состояний", "",
       f"статья {cand['id']} ({DATE})", "",
       "## После экспресса", "```json", json.dumps(s1, ensure_ascii=False, indent=1), "```",
       "## После полной поверх", "```json", json.dumps(s2, ensure_ascii=False, indent=1), "```",
       "", "## Вопросы реюза (заполняет ведущая по фактам выше)",
       "- mini полной == короткий текст экспресса? (сравнить mini_text_head)",
       "- переводы экспресса пережили апгрейд или перегенерились?",
       "- что видит читатель языка без полной? (заглушка/экспресс)"]
(OUT/"report.md").write_text("\n".join(rep), encoding="utf-8")
print("\nreport:", OUT/"report.md")
