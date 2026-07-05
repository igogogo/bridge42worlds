#!/usr/bin/env python3
"""
Добавляет новый язык в проект.
Использование: python add_language.py zh
"""

import sys, json, time
from pathlib import Path
from openai import OpenAI
import os

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY not set")
    sys.exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

NEW_LANG = sys.argv[1] if len(sys.argv) > 1 else None
if not NEW_LANG:
    print("Usage: python add_language.py <lang_code>")
    print("Example: python add_language.py zh")
    sys.exit(1)

# Load config
config = json.loads(Path("config.json").read_text())
if NEW_LANG in config["languages"]:
    print(f"⚠️ Language '{NEW_LANG}' already exists")
    sys.exit(0)

print(f"🌐 Adding language: {NEW_LANG}")

# 1. Translate tags
print("📝 Translating tags...")
tags_ru = json.loads(Path("data/tags-ru.json").read_text())
prompt = f"""Translate these tag descriptions from Russian to {NEW_LANG}.
Keep the same JSON structure. Translate: name, description, how_it_works, fun_fact.

Tags:
{json.dumps(tags_ru, ensure_ascii=False, indent=2)}

Answer ONLY JSON with the same structure."""
r = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role":"user","content":prompt}],
    temperature=0.3, max_tokens=16000
)
result = r.choices[0].message.content.strip()
if result.startswith("```"): result = result.split("\n",1)[1]
if result.endswith("```"): result = result[:-3]
Path(f"data/tags-{NEW_LANG}.json").write_text(result, encoding="utf-8")
print(f"  ✅ data/tags-{NEW_LANG}.json")

# 2. Create folders
for d in ["archive", "tags", "authors"]:
    Path(f"{NEW_LANG}/{d}").mkdir(parents=True, exist_ok=True)

# 3. Create index.html from template
index_tpl = Path("templates/index.html").read_text(encoding="utf-8")
# Simple replace — will be improved later
Path(f"{NEW_LANG}/index.html").write_text(index_tpl.replace('lang="ru"', f'lang="{NEW_LANG}"'), encoding="utf-8")
Path(f"{NEW_LANG}/about.html").write_text(f'<!DOCTYPE html><html lang="{NEW_LANG}"><head><meta charset="UTF-8"><title>About</title></head><body><h1>About</h1></body></html>', encoding="utf-8")

# 4. Create empty index
Path(f"{NEW_LANG}/articles-index.json").write_text("[]", encoding="utf-8")

# 5. Update config
config["languages"].append(NEW_LANG)
Path("config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2))
print(f"  ✅ config.json updated: {config['languages']}")

# 6. Translate existing articles
print("🌐 Translating existing articles...")
index_ru = json.loads(Path("ru/articles-index.json").read_text())
for i, item in enumerate(index_ru):
    # TODO: translate each article
    # For now, just show progress
    print(f"  [{i+1}/{len(index_ru)}] {item['id']} — skipped (implement translation)")

print(f"\n🎉 Language '{NEW_LANG}' added!")
print(f"   Next: run generate.py to create articles in {NEW_LANG}")