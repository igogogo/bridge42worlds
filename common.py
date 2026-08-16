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
import threading
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


def write_json_atomic(path, obj, indent=2):
    """Записать JSON так, чтобы читатель никогда не увидел половину файла.

    Зачем. 14 августа главная не показала ни одной статьи на всех пяти языках: полный
    индекс уехал в облако обрезанным — 7,3 МБ вместо 10,9, JSON рвался на середине.
    Причина не в облаке и не в сети: файл открыли на запись, а другой процесс в этот же
    момент его прочитал и залил как есть. Обычный write_text именно так и работает —
    сначала обнуляет файл, потом наполняет, и между этими двумя мгновениями файл
    существует неполным.

    Как здесь. Пишем во временный файл рядом и переименовываем поверх целевого:
    переименование в пределах одного диска атомарно и на Windows, и на Linux. Читатель
    в любой момент видит либо старый файл целиком, либо новый целиком — третьего нет.

    Замок сборки эту беду закрывает лишь наполовину: он останавливает НАШИ процессы,
    а атомарная запись не зависит от того, кто и когда читает.

    indent=None означает компактный JSON без пробелов — так пишутся файлы, у которых
    важен вес (индекс поиска, карты аналитики). Форматирование сохраняем как было:
    смена стиля записи раздула бы дельту выкладки на все файлы разом.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (json.dumps(obj, ensure_ascii=False, indent=indent) if indent is not None
            else json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


_STYLE_CORE = None


def style_core():
    """Общий блок правил стиля — ЕДИНСТВЕННЫЙ экземпляр (ТЗ контент-менеджера 2026-07-27, §2).
    Промпты уровней содержат только отличия уровня, а тон/запреты/приёмы живут здесь."""
    global _STYLE_CORE
    if _STYLE_CORE is None:
        p = Path("data/prompts/_style-core.txt")
        _STYLE_CORE = p.read_text(encoding="utf-8").strip() if p.exists() else ""
    return _STYLE_CORE


def load_prompt(name):
    """Читает промт из data/prompts/{name}.txt (без .txt в имени).
    Плейсхолдер {style_core} заменяется общим блоком правил — так редакции не расходятся."""
    text = Path(f"data/prompts/{name}.txt").read_text(encoding="utf-8")
    if "{style_core}" in text:
        text = text.replace("{style_core}", style_core())
    return text


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


class PeakHourError(RuntimeError):
    """Попытка жечь DeepSeek в пиковые (×2 цена) часы без явного разрешения."""


# Юзер 2026-07-24: «вставь в код, чтобы не проверять руками — в часы пик давай ошибку или подтверждение».
# Подтверждение в неинтерактивном прогоне = переменная окружения ALLOW_PEAK=1 (осознанно разрешаю пик).
_PEAK_WARNED = False


def guard_peak(context=""):
    # 2026-07-30: пиковых цен у v4 НЕТ — подтверждено оплатой (экспорт владельца:
    # вызовы в «пиковое» время списаны по тому же прайсу $0.435/M, отдельной строки
    # с наценкой в биллинге не появилось). Стражи окон оставлены в коде на случай,
    # если DeepSeek вернёт тарифные окна: включаются B42_PEAK_ENFORCE=1.
    if os.environ.get("B42_PEAK_ENFORCE") != "1":
        return
    """Страж пиковых часов перед вызовами API. В пик — стоп с понятной ошибкой (PeakHourError),
    если не выставлен ALLOW_PEAK=1. Вне пика — тихо пропускает (один раз пишет, сколько часов дешёвого
    окна осталось, чтобы было видно приближение пика). Вызывается из chat() — единой точки всех вызовов."""
    global _PEAK_WARNED
    is_peak, h = deepseek_peak_status()
    if is_peak:
        if os.environ.get("ALLOW_PEAK") == "1":
            if not _PEAK_WARNED:
                print("⚠️ ПИКОВЫЕ часы DeepSeek (×2 цена), но ALLOW_PEAK=1 — продолжаю осознанно.")
                _PEAK_WARNED = True
            return
        raise PeakHourError(
            f"Сейчас ПИКОВЫЕ часы DeepSeek (цена ×2){' — ' + context if context else ''}. "
            f"Остановлено, чтобы не переплатить. Дождись дешёвого окна (пик Пекин 9-12 и 14-18, "
            f"т.е. локально 04-07 и 09-13) ИЛИ запусти с ALLOW_PEAK=1, если реально надо сейчас.")
    if not _PEAK_WARNED:
        print(f"💰 DeepSeek: дешёвое окно, до следующего пика ~{h:.1f} ч.")
        _PEAK_WARNED = True


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
    return _fix_escapes(t)


_LATIN_RE = re.compile(r"[a-zA-Z]")


def _fix_escapes(t):
    """Чинит обратные слэши так, чтобы json.loads не падал и не портил LaTeX.

    Раньше здесь стояла одна регулярка `\\\\(?!["\\\\/bfnrtu])`. Она закрывала простой случай
    («80\\%»), но промахивалась на двух других, и оба стоили нам статей:

    1. ДВА СЛЭША. В «\\\\frac» она видела первый слэш, следующим символом был слэш — эскейп
       валидный, пропускаем; потом второй слэш перед «f» — тоже валидный (\\f). Формально
       верно, а на деле json превращал это в подачу страницы посреди формулы.
    2. LATEX, ПОХОЖИЙ НА ЭСКЕЙП. «\\beta», «\\nu», «\\rho», «\\times», «\\frac» неотличимы от
       \\b \\n \\r \\t \\f — json их принимал и молча вставлял управляющий символ вместо буквы.
       А «\\upsilon» и вовсе роняло разбор: после \\u обязаны идти четыре шестнадцатеричные
       цифры, «psil» ими не являются — это и есть тот самый «Invalid \\escape» из журнала,
       из-за которого 2026-08-06 не переводились французские статьи с формулами.

    Отличаем эскейп от команды по следующему символу: у LaTeX-команды \\nu после «n» идёт
    ЛАТИНСКАЯ буква, у настоящего переноса — что угодно другое. Именно латинская: проверка
    на «любую букву» ломала «\\nстрока» — перенос строки перед кириллицей встречается в наших
    текстах постоянно, а LaTeX-команд кириллицей не бывает."""
    out = []
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        nxt = t[i + 1] if i + 1 < n else ""
        if nxt == "\\":                                     # уже экранированный слэш — не трогаем
            out.append("\\\\")
            i += 2
        elif nxt == "u" and re.match(r"[0-9a-fA-F]{4}", t[i + 2:i + 6]):
            out.append(t[i:i + 6])                          # настоящий \uXXXX
            i += 6
        elif nxt in '"/' or (nxt in "bfnrt" and not _LATIN_RE.match(t[i + 2:i + 3])):
            out.append(c + nxt)                             # настоящий эскейп
            i += 2
        else:                                               # \% \, \beta \nu \upsilon …
            out.append("\\\\")
            i += 1
    return "".join(out)


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


# К чему относятся вызовы прямо сейчас — попадает в каждую строку журнала расхода.
# Без этого себестоимость статьи посчитать НЕЛЬЗЯ, а не «трудно»: имя агента говорит,
# ЧТО делали, но не для чего. 2026-08-02 сверка показала, чем это кончается — в цену
# новых экспрессов попал догон французского по старым статьям, и отчёт выдал 12 центов
# за экспресс вместо девяти, сделав его почти равным полной. Решение «ежедневно только
# экспресс» принималось как раз по этим числам.
#
# Метка ПО ПОТОКАМ, а не одна на процесс: статьи готовятся в несколько потоков сразу
# (ThreadPoolExecutor в process_day), и общая метка приписала бы вызовы одной статьи
# другой — тем вернее, чем больше потоков.
_job = threading.local()


def job_tags():
    return getattr(_job, "tags", None) or {}


def job(**tags):
    """Пометить вызовы своего потока: `with job(article="2607.12345", kind="экспресс")`."""
    class _Job:
        def __enter__(self):
            self.was = job_tags()
            _job.tags = {**self.was, **{k: v for k, v in tags.items() if v is not None}}

        def __exit__(self, *exc):
            _job.tags = self.was
            return False
    return _Job()


def chat(agent, user_prompt, retries=3, system=None, **overrides):
    """Вызов LLM по ИМЕНИ АГЕНТА (модель/температура/max_tokens из config.agents).
    overrides позволяет точечно переопределить (напр. max_tokens) в конкретном вызове.
    Ретраи — сетевой сбой не должен терять статью.

    system — своя системная роль для этого вызова. Заведено 2026-07-30 для переводов:
    требование «пиши на языке X» жило только в user-тексте, и модель его теряла —
    отсюда ретраи по 2-3 раза (каждый — полная цена). Инструкция про язык вывода
    обязана жить в системной роли (тот же урок, что с суб-агентами)."""
    if client is None:
        raise RuntimeError("DEEPSEEK_API_KEY не задан — операция с API невозможна")
    guard_peak(f"агент {agent}")  # стоп в пиковые часы, если не ALLOW_PEAK=1 (защита от переплаты ×2)
    p = agent_cfg(agent)
    p.update({k: v for k, v in overrides.items() if v is not None})
    for attempt in range(1, retries + 1):
        try:
            _resp = client.chat.completions.create(
                model=p["model"],
                messages=[{"role": "system", "content": system or SYSTEM_PROMPT},
                          {"role": "user", "content": user_prompt}],
                temperature=p["temperature"], max_tokens=p["max_tokens"],
                response_format={"type": "json_object"},
                # Рассуждения ВЫКЛЮЧЕНЫ (замер 2026-08-02, решение владельца).
                # Мы платим за них по цене вывода, а читатель их не видит никогда.
                # На одной карточке: с рассуждениями $0.00711 и ПУСТОЙ ответ (8000 токенов
                # ушли в размышления, до текста не дошло), без них — $0.00035 и готовый
                # текст за 6 секунд. Разница в 21 раз на ровном месте.
                # Отдельная ловушка: у дорогой модели reasoning_effort="low" по документации
                # маппится в "high" — экономного режима у неё нет, только выключать целиком.
                # Вернуть рассуждения = убрать этот extra_body (для задач, где нужен разбор,
                # а не изложение: отбор статей, оценка новизны).
                extra_body={"thinking": {"type": "disabled"}},
            )
            # Журнал расхода (замер экономики, 2026-07-30): каждый вызов — строка jsonl.
            # По нему раскладывается цена статьи по шагам; сумма калибруется по балансу.
            try:
                u = getattr(_resp, "usage", None)
                if u is not None:
                    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "agent": agent,
                           "model": p["model"],
                           "prompt": getattr(u, "prompt_tokens", 0),
                           "completion": getattr(u, "completion_tokens", 0),
                           "cache_hit": getattr(u, "prompt_cache_hit_tokens", 0),
                           "cache_miss": getattr(u, "prompt_cache_miss_tokens", 0)}
                    rec.update(job_tags())
                    with open("data/usage-log.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + chr(10))
            except Exception:
                pass
            return _resp
        except Exception as e:
            if attempt == retries:
                raise
            # Нарастающий бэкофф 10с→30с; при rate-limit (429) ждём дольше — сервис перегружен.
            is_429 = "429" in str(e) or "rate" in str(e).lower()
            wait = (60 if is_429 else 0) + [10, 30, 30][min(attempt - 1, 2)]
            print(f"    ⚠️ LLM error ({agent}){' [429]' if is_429 else ''}: {e} — retry {attempt}/{retries} через {wait}с")
            time.sleep(wait)
