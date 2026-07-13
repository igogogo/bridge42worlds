#!/usr/bin/env python3
"""Общий фундамент для всех скриптов Bridge For Two Worlds.

Устраняет дублирование (config/пути/UTF-8/LLM-клиент/парсинг JSON/промты), которое
раньше копировалось в каждом generate_*.py. Параметры агентов (модель/температура/
max_tokens) — из config.json → "agents", чтобы менять их в одном месте без правок кода.

Импортируй: `from common import CONFIG, LANGUAGES, chat, load_prompt, parse_json_salvage, clean_json`
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

# Windows-консоль по умолчанию cp1252 — принудительно UTF-8, чтобы кириллица/эмодзи не падали.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", line_buffering=True)
    except (AttributeError, ValueError):
        pass

load_dotenv()

CONFIG = json.loads(Path("config.json").read_text(encoding="utf-8"))
LANGUAGES = CONFIG.get("languages", ["ru"])
DEFAULT_LANG = CONFIG.get("default_lang", "ru")
LANG_DIR = CONFIG.get("lang_dir", "lang")
AGENTS = CONFIG.get("agents", {})

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# Без явного timeout SDK ждёт зависший запрос до 10 минут (дефолт httpx) — на этой сети
# несколько раз ловили запрос, который просто никогда не отвечает (0% CPU, не 429/ошибка).
# 180с — с запасом на реальную долгую генерацию (max_tokens до 32000), но не бесконечность;
# chat() потом сам ретраит по своей логике (10с→30с→30с бэкофф).
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=180.0) if DEEPSEEK_API_KEY else None

SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")


def load_prompt(name):
    """Читает промт из data/prompts/{name}.txt (без .txt в имени)."""
    return Path(f"data/prompts/{name}.txt").read_text(encoding="utf-8")


def focus_line(focus):
    """Директива-приоритет для роста справочников (tag_list.py/law_list.py/scientist_list.py
    --focus) — например, разово подтянуть quantum-теги ПЕРЕД тем как заливать статьи по
    quant-ph (иначе гэп-анализ смотрит на текущий корпус, где этой темы ещё нет, и никогда её
    не предложит). Пусто по умолчанию — не влияет на обычный органический рост."""
    if not focus:
        return ""
    return (f"ОСОБЫЙ ПРИОРИТЕТ в этом раунде: в первую очередь предлагай варианты из области "
            f"«{focus}» — даже если примеры выше её не отражают (это подготовка базы заранее, "
            f"под контент, который скоро появится). Качество и фундаментальность важнее темы, "
            f"плохо подходящее не притягивай.")


# DeepSeek удваивает цену API в пиковые часы (9-12 и 14-18 по Пекину, UTC+8).
DEEPSEEK_PEAK_WINDOWS_BEIJING = [(9, 12), (14, 18)]


def deepseek_peak_status(now=None):
    """Локальная машина на Beijing-5 (пик по местному — 4-7 и 9-13). Возвращает
    (is_peak, hours_until_next_peak) — второе 0.0, если уже в пике сейчас."""
    now = now or datetime.now()
    bj_hour = (now + timedelta(hours=5)).hour + (now + timedelta(hours=5)).minute / 60
    for start, end in DEEPSEEK_PEAK_WINDOWS_BEIJING:
        if start <= bj_hour < end:
            return True, 0.0
    deltas = [(start - bj_hour) % 24 for start, _ in DEEPSEEK_PEAK_WINDOWS_BEIJING]
    return False, min(deltas)


def sample_corpus(n=50):
    """Случайная выборка N реальных статей (title/tags/categories/scientists) из архива —
    контекст для «пробел-осведомлённой» генерации тегов/законов/учёных (Итерация 2 ко-эволюции
    графа знаний): вместо слепого «дай ещё интересных тем» модель видит, что РЕАЛЬНО есть
    в корпусе и что из этого не покрыто существующим списком. Читает только RU (язык-источник)."""
    import random
    paths = list(Path(LANG_DIR, DEFAULT_LANG, "archive").glob("*/*/data.json"))
    random.shuffle(paths)
    items = []
    for p in paths:
        if len(items) >= n:
            break
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        items.append({
            "title": d.get("original_title", ""),
            "tags": d.get("tags", []),
            "category": d.get("primary_category", ""),
            "scientists": d.get("scientists", []),
        })
    return items


def format_corpus_samples(items):
    """Форматирует sample_corpus() в компактный текстовый блок для промта."""
    lines = []
    for it in items:
        sci = f" · учёные: {', '.join(it['scientists'])}" if it["scientists"] else ""
        lines.append(f"- «{it['title']}» [{it['category']}] · теги: {', '.join(it['tags'])}{sci}")
    return "\n".join(lines)


def as_list(v):
    """LLM иногда возвращает список полей как строку через запятую вместо JSON-массива
    (напр. fields/key_discoveries учёных) — наивный join/iteration по такой строке даёт
    посимвольный мусор. Нормализуем: список — как есть, строка — разбиваем по , или ;"""
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [s.strip() for s in re.split(r"[,;]\s*", v) if s.strip()]
    return []


def clean_json(t):
    """Снимает ```-обёртку и добивает незакрытые скобки (быстрый ремонт обрезанного JSON)."""
    t = t.strip()
    for m in ["```json", "```"]:
        if t.startswith(m):
            t = t[len(m):]
    if t.endswith("```"):
        t = t[:-3]
    t = t.strip().rstrip(",")
    t += "}" * (t.count("{") - t.count("}"))
    t += "]" * (t.count("[") - t.count("]"))
    return t


def parse_json_salvage(text):
    """json.loads с восстановлением обрезанного ответа: срез до последнего полного объекта."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    last = text.rfind("},")
    if last != -1:
        for tail in ("}}", "]}", "]"):
            try:
                return json.loads(text[:last + 1] + tail)
            except json.JSONDecodeError:
                continue
    return None


def agent_cfg(agent):
    """Параметры агента из config.agents (с дефолтами)."""
    c = AGENTS.get(agent, {})
    return {
        "model": c.get("model", "deepseek-chat"),
        "temperature": c.get("temperature", 0.7),
        "max_tokens": c.get("max_tokens", 8000),
    }


def chat(agent, user_prompt, retries=3, **overrides):
    """Вызов LLM по ИМЕНИ АГЕНТА (модель/температура/max_tokens из config.agents).
    overrides позволяет точечно переопределить (напр. max_tokens) в конкретном вызове.
    Ретраи — сетевой сбой не должен терять статью."""
    if client is None:
        raise RuntimeError("DEEPSEEK_API_KEY не задан — операция с API невозможна")
    p = agent_cfg(agent)
    p.update({k: v for k, v in overrides.items() if v is not None})
    for attempt in range(1, retries + 1):
        try:
            return client.chat.completions.create(
                model=p["model"],
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_prompt}],
                temperature=p["temperature"], max_tokens=p["max_tokens"],
                response_format={"type": "json_object"},
            )
        except Exception as e:
            if attempt == retries:
                raise
            # Нарастающий бэкофф 10с→30с; при rate-limit (429) ждём дольше — сервис перегружен.
            is_429 = "429" in str(e) or "rate" in str(e).lower()
            wait = (60 if is_429 else 0) + [10, 30, 30][min(attempt - 1, 2)]
            print(f"    ⚠️ LLM error ({agent}){' [429]' if is_429 else ''}: {e} — retry {attempt}/{retries} через {wait}с")
            time.sleep(wait)
