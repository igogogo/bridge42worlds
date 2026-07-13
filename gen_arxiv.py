#!/usr/bin/env python3
"""Слой arXiv/PDF: получение статей за день, лицензия, скачивание/парсинг PDF,
отсечение списка литературы (References), извлечение подписей к рисункам.

Чистый листовой модуль (только requests / xml / pypdf), без зависимостей от рендера.
"""

import time
import re
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from pypdf import PdfReader

BULK_DIR = Path("data/arxiv-bulk")


def _get_with_retry(url, params=None, timeout=30, retries=3):
    """arXiv отдаёт то 429 (перегрузка), то просто зависший коннект без ответа — раньше
    ЛЮБАЯ из этих ошибок валила весь батч (напр. на 13-й день из 31 в диапазоне). Тот же
    нарастающий бэкофф, что и у common.chat() для LLM-вызовов."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 429 and attempt < retries:
                wait = 60 + [10, 30][min(attempt - 1, 1)]
                print(f"  ⚠️ arXiv 429 (перегрузка) — retry {attempt}/{retries} через {wait}с")
                time.sleep(wait)
                continue
            return r
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise
            wait = [10, 30, 30][min(attempt - 1, 2)]
            print(f"  ⚠️ arXiv connection error: {e} — retry {attempt}/{retries} через {wait}с")
            time.sleep(wait)


def _category_pattern(category):
    """arXiv 'cat:X.*' — wildcard-совпадение по префиксу подкатегорий, 'cat:X' — точное имя."""
    if category.endswith(".*"):
        prefix = re.escape(category[:-2])
        return re.compile(rf'^{prefix}(\..+)?$')
    return re.compile(rf'^{re.escape(category)}$')


def _matches_category(cats, pattern):
    return any(pattern.match(c) for c in cats)


def _author_name(parsed):
    last, first, suffix = (parsed + ["", "", ""])[:3]
    name = f"{first} {last}".strip()
    return f"{name} {suffix}".strip() if suffix else name


def fetch_arxiv_local(date_str, category="astro-ph.*"):
    """Ищет статьи за день в локальном чанке (data/arxiv-bulk/{YYYY-MM}.jsonl,
    см. arxiv_bulk_chunk.py) — обходит rate-limit живого arXiv API для
    исторических диапазонов. Возвращает None, если чанк за этот месяц не скачан
    (тогда fetch_arxiv() падает на живой API), иначе список статей (может быть пустым)."""
    chunk = BULK_DIR / f"{date_str[:7]}.jsonl"
    if not chunk.exists():
        return None
    pattern = _category_pattern(category)
    articles = []
    with chunk.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("published") != date_str:
                continue
            cats = d.get("categories") or []
            if not _matches_category(cats, pattern):
                continue
            articles.append({
                "id": d.get("id"),
                "title": d.get("title", ""),
                "summary": d.get("abstract", ""),
                "authors": [_author_name(a) for a in d.get("authors_parsed") or []],
                "published": d.get("published", ""),
                "categories": cats,
                "primary_category": cats[0] if cats else "",
            })
    print(f"  📦 Локальный кэш: {len(articles)} статей")
    return articles


# ── arXiv ──
def fetch_arxiv(date_str, category="astro-ph.*"):
    local = fetch_arxiv_local(date_str, category)
    if local is not None:
        return local
    f = f"{date_str.replace('-', '')}0000"
    t = f"{date_str.replace('-', '')}2359"
    url = "http://es.arxiv.org/api/query"
    params = {
        "search_query": f"cat:{category} AND submittedDate:[{f} TO {t}]",
        "start": 0, "max_results": 200,
        "sortBy": "submittedDate", "sortOrder": "descending"
    }
    try:
        r = _get_with_retry(url, params=params, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"  ❌ arXiv API: не удалось получить ответ после ретраев ({e})")
        return []
    Path(f"temp/{date_str}").mkdir(parents=True, exist_ok=True)
    Path(f"temp/{date_str}/arxiv-api.xml").write_text(r.text, encoding="utf-8")

    if not r.text or r.status_code != 200:
        print(f"  ❌ arXiv API error: status {r.status_code}")
        return []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    articles = []
    for e in root.findall("atom:entry", ns):
        try:
            aid = e.find("atom:id", ns).text.split("/abs/")[-1]
            cats = list(dict.fromkeys(
                c.get("term") for c in e.findall("atom:category", ns) if c.get("term")))
            primary = e.find("arxiv:primary_category", ns)
            primary_cat = primary.get("term", "") if primary is not None else (cats[0] if cats else "")
            articles.append({
                "id": aid,
                "title": e.find("atom:title", ns).text.strip().replace("\n", " "),
                "summary": e.find("atom:summary", ns).text.strip().replace("\n", " "),
                "authors": [a.find("atom:name", ns).text for a in e.findall("atom:author", ns)],
                "published": e.find("atom:published", ns).text,
                "categories": cats,
                "primary_category": primary_cat,
            })
        except Exception:
            pass
    print(f"  ✅ Found: {len(articles)} articles")
    return articles


# ── License ──
def get_license(arxiv_id):
    try:
        r = _get_with_retry("http://es.arxiv.org/oai2", params={
            "verb": "GetRecord", "identifier": f"oai:arXiv.org:{arxiv_id}", "metadataPrefix": "arXiv"
        }, timeout=10)
        return r.text
    except requests.exceptions.RequestException:
        return None


def is_allowed_license(xml_text):
    if not xml_text:
        return False, None
    try:
        root = ET.fromstring(xml_text)
        lic = root.find(".//{http://arxiv.org/OAI/arXiv/}license")
        if lic is None:
            return False, None
        lic_url = lic.text
        allowed = ["by/4.0", "by-sa/4.0", "zero/1.0", "nonexclusive-distrib/1.0"]
        return any(a in lic_url for a in allowed), lic_url
    except Exception:
        return False, None


# ── PDF ──
def download_pdf(aid):
    p = Path(f"temp/{aid}.pdf")
    p.parent.mkdir(exist_ok=True)
    if not p.exists():
        p.write_bytes(requests.get(f"https://arxiv.org/pdf/{aid}.pdf", timeout=60).content)
    return p


def parse_pdf(path):
    # Берём ВЕСЬ текст статьи (без ограничения по числу страниц) — модели скармливаем полностью.
    try:
        r = PdfReader(str(path))
        t = ""
        imgs = []
        for pg in r.pages:
            pt = pg.extract_text()
            if pt:
                t += pt + "\n"
            try:
                for img in pg.images:
                    imgs.append(img.data)
            except Exception:
                pass
        return t, imgs
    except Exception:
        return "", []


# Заголовок списка литературы: строка вида "References"/"REFERENCES"/"Bibliography".
REF_HEADING = re.compile(
    r'\n[ \t]*(?:\d+[.\)]?[ \t]*)?(?:References?|REFERENCES|Bibliography|BIBLIOGRAPHY|References and Notes)[ \t]*\n')
ARXIV_ID_RE = re.compile(r'ar[Xx]iv:\s*(\d{4}\.\d{4,5})')


def split_references(text):
    """Отделяет список литературы (References/Bibliography) от тела статьи.
    Возвращает (body, references). Заголовок ищем в ПОСЛЕДНЕЙ части документа и режем по
    ПОСЛЕДНЕМУ совпадению — чтобы упоминание 'references' в тексте не обрезало тело раньше времени.
    Список литературы ест до ~20% токенов и для генерации статьи бесполезен."""
    cut = None
    for m in REF_HEADING.finditer(text):
        if m.start() > len(text) * 0.4:  # только во второй половине — там реальный список в конце статьи
            cut = m
    if cut:
        return text[:cut.start()].rstrip(), text[cut.end():].strip()
    return text, ""


def extract_ref_arxiv_ids(references):
    """arXiv id цитируемых работ из списка литературы — на будущее для привязки к релевантным статьям."""
    return list(dict.fromkeys(m.group(1) for m in ARXIV_ID_RE.finditer(references or "")))


def clean_article_text(text):
    """Тело статьи БЕЗ списка литературы и голых URL — то, что уходит в промт."""
    body, _ = split_references(text)
    return re.sub(r'https?://\S+', '', body)


def extract_captions(text, limit=12):
    """Достаёт подписи к рисункам из текста PDF ('Figure N: ...' / 'Fig. N. ...').
    Возвращает список подписей по возрастанию номера рисунка — для сопоставления с картинками по порядку."""
    caps = {}
    for m in re.finditer(r'(?:Figure|Fig)\.?\s*(\d{1,3})\s*[\.:]\s*([^\n]{10,300})', text):
        n = int(m.group(1))
        cap = re.sub(r'\s+', ' ', m.group(2)).strip()
        if n not in caps and len(cap) > 12:
            caps[n] = cap
    return [caps[n] for n in sorted(caps)][:limit]
