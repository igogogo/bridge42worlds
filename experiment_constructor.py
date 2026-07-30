#!/usr/bin/env python3
"""Эксперимент «конструктор» (владелец, 2026-07-30): снизить цену статьи вдвое
переиспользованием результатов.

Гипотезы:
  A. popular+simple+mini — ОДНИМ вызовом из advanced (сейчас два вызова);
     общие блоки (formulas/key_numbers/fun_fact/scifi/теги) не пересказываются
     моделью, а копируются кодом из advanced.
  B. Перевод с дедупликацией: общие блоки переводятся ОДИН раз (в составе advanced),
     а у popular/simple переводится только их уникальный текст. Сейчас fun_fact,
     scifi и смыслы формул переводятся трижды на язык — деньги за одно и то же.
  C. Перевод дешёвой моделью (flash) — контроль тем же валидатором.

Скрипт НИЧЕГО не пишет в lang/ — только в scratch-папку эксперимента.
Использование: python experiment_constructor.py <arxiv_id_дата_папка>
"""
import json
import sys
import time
from pathlib import Path

from common import chat, clean_json, load_prompt
from gen_llm import (_translation_system, validate_translation, LANG_NAMES,
                     CULTURE_NOTES, _termbase_block, inherit_facts)

OUT = Path("temp/experiment-constructor")
OUT.mkdir(parents=True, exist_ok=True)

# Поля, которые конструктор переиспользует из advanced (модель их не пишет, код копирует)
SHARED = ("formulas", "key_numbers", "fun_fact", "scifi", "main_tag",
          "extra_tags", "scientists", "glossary")
# Поля, общие при переводе (переводятся один раз в advanced, копируются в тиры)
SHARED_TRANSLATE = ("fun_fact", "scifi", "formulas", "key_numbers")


def usage_of(resp):
    u = resp.usage
    return {"hit": getattr(u, "prompt_cache_hit_tokens", 0),
            "miss": getattr(u, "prompt_cache_miss_tokens", 0),
            "out": u.completion_tokens}


def cost(u, model="pro"):
    if model == "pro":
        return u["hit"] * 3.625e-9 + u["miss"] * 4.35e-7 + u["out"] * 8.7e-7
    return u["miss"] * 1.4e-7 + u["out"] * 2.8e-7   # flash: из экспорта владельца


def combo_generate(advanced):
    prompt = load_prompt("article-generate-combo").format(
        advanced_json=json.dumps(advanced, ensure_ascii=False))
    r = chat("article_popular", prompt)          # тот же агент/лимиты, промпт другой
    data = json.loads(clean_json(r.choices[0].message.content))
    pop, simp, mini = data["popular"], data["simple"], data.get("mini", "")
    for tier in (pop, simp):
        for k in SHARED:
            if k in advanced:
                tier[k] = advanced[k]
    pop["mini"] = simp["mini"] = mini
    return pop, simp, mini, usage_of(r)


def dedup_translate(advanced, tier, target_lang, model_agent="translate"):
    """Переводит тир БЕЗ общих полей; общие берёт из уже переведённого advanced."""
    slim = {k: v for k, v in tier.items() if k not in SHARED_TRANSLATE}
    target_language = LANG_NAMES.get(target_lang, target_lang)
    prompt = load_prompt("article-translate").format(
        article_json=json.dumps(slim, ensure_ascii=False),
        target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, "")) + _termbase_block(slim, target_lang)
    r = chat(model_agent, prompt, system=_translation_system(target_language, slim))
    out = json.loads(clean_json(r.choices[0].message.content))
    for k in ("main_tag", "extra_tags", "tags", "scientists", "laws", "glossary"):
        if k in slim:
            out[k] = slim[k]
    for k in SHARED_TRANSLATE:                       # общие — из перевода advanced
        if k in advanced:
            out[k] = advanced[k]
    ok, problems = validate_translation(tier, out, target_lang)
    return out, ok, problems, usage_of(r)


def main(article_dir):
    d = Path(article_dir)
    adv = json.loads((d / "api" / "advanced-ru.json").read_text(encoding="utf-8")) \
        if (d / "api" / "advanced-ru.json").exists() else None
    if adv is None:
        data = json.loads((d / "data.json").read_text(encoding="utf-8"))
        adv = (data.get("advanced") or {}).get("ru") or data.get("advanced")
    assert adv, "advanced-ru не найден"

    report = {"article": str(d), "steps": {}}

    t0 = time.time()
    pop, simp, mini, u = combo_generate(adv)
    report["steps"]["combo_generate"] = {"usage": u, "cost": round(cost(u), 4),
                                          "sec": round(time.time() - t0)}
    (OUT / "combo-popular.json").write_text(json.dumps(pop, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "combo-simple.json").write_text(json.dumps(simp, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "combo-mini.txt").write_text(mini, encoding="utf-8")

    # B: en — pro с дедупликацией (advanced переводим целиком как опору)
    t0 = time.time()
    target = "en"
    target_language = LANG_NAMES[target]
    prompt = load_prompt("article-translate").format(
        article_json=json.dumps(adv, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target, "")) + _termbase_block(adv, target)
    r = chat("translate", prompt, system=_translation_system(target_language, adv))
    adv_en = json.loads(clean_json(r.choices[0].message.content))
    u_adv = usage_of(r)
    ok_adv, probs_adv = validate_translation(adv, adv_en, target)
    pop_en, ok_pop, probs_pop, u_pop = dedup_translate(adv_en, pop, target)
    report["steps"]["translate_en_dedup"] = {
        "advanced": {"ok": ok_adv, "problems": probs_adv, "usage": u_adv, "cost": round(cost(u_adv), 4)},
        "popular_slim": {"ok": ok_pop, "problems": probs_pop, "usage": u_pop, "cost": round(cost(u_pop), 4)},
        "sec": round(time.time() - t0)}

    # C: попытка flash на simple->es (валидатор судит)
    t0 = time.time()
    try:
        simp_es, ok_es, probs_es, u_es = dedup_translate(adv_en, simp, "es", model_agent="translate_flash")
        report["steps"]["translate_es_flash"] = {"ok": ok_es, "problems": probs_es,
                                                  "usage": u_es, "cost": round(cost(u_es, "flash"), 4),
                                                  "sec": round(time.time() - t0)}
        (OUT / "flash-simple-es.json").write_text(json.dumps(simp_es, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        report["steps"]["translate_es_flash"] = {"error": str(e)[:200]}

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["steps"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
