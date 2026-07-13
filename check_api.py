#!/usr/bin/env python3
"""Проверка всех API перед запуском генерации."""

import os, sys, json, requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def ok(msg):
    print(f"  {GREEN}✅ {msg}{RESET}")


def fail(msg):
    print(f"  {RED}❌ {msg}{RESET}")


def warn(msg):
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def check_section(title):
    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")


# ── Конфиг ──
check_section("📋 Конфигурация")

config_path = Path("config.json")
if config_path.exists():
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    ok(f"config.json загружен")
    ok(f"  Языки: {cfg.get('languages', [])}")
    ok(f"  Основной язык: {cfg.get('default_lang', '?')}")
    ok(f"  Папка языков: {cfg.get('lang_dir', '?')}")
    ok(f"  Макс статей: {cfg.get('max_articles', '?')}")
    ok(f"  Процент отбора: {cfg.get('selection_percent', '?')}%")
else:
    fail("config.json не найден")
    sys.exit(1)

# ── Переменные окружения ──
check_section("🔑 API ключи")

deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
if deepseek_key:
    masked = deepseek_key[:8] + "****" + deepseek_key[-4:]
    ok(f"DEEPSEEK_API_KEY: {masked}")
else:
    fail("DEEPSEEK_API_KEY не установлен")

supabase_url = os.environ.get("SUPABASE_URL", "https://gyfdyfbuolnciaqxgybx.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "")
if supabase_key:
    ok(f"SUPABASE_URL: {supabase_url[:40]}...")
else:
    warn("SUPABASE_KEY не установлен (лайки не будут работать)")

# ── DeepSeek API ──
check_section("🤖 DeepSeek API")

try:
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

    # Проверка Flash (не-думающая)
    r = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "Ответь одним словом: ОК"}],
        max_tokens=5, temperature=0
    )
    flash_reply = r.choices[0].message.content.strip()
    flash_model = r.model
    flash_tokens = r.usage.total_tokens
    ok(f"deepseek-v4-pro (Flash): '{flash_reply}' — модель: {flash_model}, токенов: {flash_tokens}")
except Exception as e:
    fail(f"deepseek-v4-pro (Flash): {e}")

try:
    # Проверка Pro
    r = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "Ответь одним словом: ОК"}],
        max_tokens=5, temperature=0
    )
    pro_reply = r.choices[0].message.content.strip()
    pro_model = r.model
    pro_tokens = r.usage.total_tokens
    ok(f"deepseek-v4-pro: '{pro_reply}' — модель: {pro_model}, токенов: {pro_tokens}")
except Exception as e:
    warn(f"deepseek-v4-pro: {e} (возможно нет доступа — будем использовать Flash)")

# ── arXiv API ──
check_section("📚 arXiv API")

for name, url in [("es.arxiv.org", "http://es.arxiv.org/api/query?max_results=1"),
                  ("export.arxiv.org", "http://export.arxiv.org/api/query?max_results=1")]:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            ok(f"{name}: статус {r.status_code}, ответ {len(r.text)} байт")
        else:
            warn(f"{name}: статус {r.status_code}")
    except Exception as e:
        fail(f"{name}: {e}")

# ── arXiv OAI-PMH (лицензии) ──
check_section("📜 arXiv OAI-PMH (лицензии)")

try:
    r = requests.get("http://export.arxiv.org/oai2", params={
        "verb": "GetRecord",
        "identifier": "oai:arXiv.org:2606.30643",
        "metadataPrefix": "arXiv"
    }, timeout=10)
    if r.status_code == 200 and "license" in r.text.lower():
        ok(f"OAI-PMH: статус {r.status_code}, лицензия найдена в ответе")
    else:
        warn(f"OAI-PMH: статус {r.status_code}, лицензия не найдена")
except Exception as e:
    fail(f"OAI-PMH: {e}")

# ── Supabase (лайки) ──
check_section("❤️ Supabase (лайки)")

try:
    r = requests.get(f"{supabase_url}/rest/v1/likes?limit=0", headers={
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }, timeout=10)
    if r.status_code in [200, 401]:
        ok(f"Supabase: статус {r.status_code} (доступен)")
    else:
        warn(f"Supabase: статус {r.status_code}")
except Exception as e:
    warn(f"Supabase: {e} (лайки не будут работать)")

# ── Файловая система ──
check_section("📁 Файлы проекта")

required = [
    "config.json",
    "templates/article.html",
    "templates/index.html",
    "templates/tag.html",
    "templates/scientist.html",
    "templates/author.html",
    "css/style.css",
    "js/search.js",
    "js/likes.js",
    "js/scroll.js",
    "data/prompts/system.txt",
    "data/prompts/select-articles.txt",
    "data/prompts/generate-article-advanced.txt",
    "data/prompts/generate-article-simple.txt",
    "data/prompts/translate-article.txt",
]

for f in required:
    if Path(f).exists():
        ok(f)
    else:
        fail(f"не найден: {f}")

# ── Итог ──
print(f"\n{BOLD}{'=' * 50}{RESET}")
print(f"{BOLD}  ✅ Проверка завершена{RESET}")
print(f"{BOLD}{'=' * 50}{RESET}")