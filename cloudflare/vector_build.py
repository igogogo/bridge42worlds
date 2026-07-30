"""Строит смысловой индекс статей: эмбеддинги через Workers AI → Vectorize.

Зачем. Обычный поиск ищет совпадение слов, а в науке одно и то же называют по-разному:
«разлёт галактик» и «расширение Вселенной» — один предмет, ни одного общего слова. Вектор
сравнивает смысл, поэтому читатель находит статью, не зная нашего термина.

Один вектор на статью, не по вектору на язык. Причина арифметическая: бесплатная норма
Vectorize — 5 млн хранимых измерений. 1980 статей × 1024 = 2,0 млн, влезаем с запасом;
четыре языка дали бы 8,1 млн и не влезли. Модель `bge-m3` кросс-язычная — запрос по-арабски
находит русский текст, проверено на живых запросах (см. отчёты/devops.md).

Текст для вектора берём русский (язык-источник, всегда заполнен): заголовок + одной строкой +
аннотация + теги. Заголовок весит больше, поэтому идёт первым и не обрезается.

Дельта по md5, как у публикации и бэкапа: пересчитываем только то, что изменилось —
эмбеддинги стоят «нейронов», гонять весь корпус на каждый прогон незачем.

Запуск:
    python cloudflare/vector_build.py            # догнать изменившееся
    python cloudflare/vector_build.py --all      # пересчитать всё заново
"""
import os, sys, json, hashlib, argparse, time
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
MANIFEST = ROOT / "cloudflare" / ".vector-manifest.json"
INDEX = os.environ.get("VECTORIZE_INDEX", "b42-articles")
MODEL = "@cf/baai/bge-m3"
EMBED_BATCH = 50          # столько текстов за один вызов модели
UPSERT_BATCH = 500        # столько векторов за одну запись в Vectorize


def api_base():
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    return f"https://api.cloudflare.com/client/v4/accounts/{acc}"


def article_text(a):
    """Что именно сравниваем по смыслу. Заголовок первым — он самый плотный по смыслу."""
    parts = [a.get("title") or "", a.get("oneliner") or "", (a.get("abstract") or "")[:1200]]
    tags = a.get("tags") or []
    if tags:
        parts.append(" ".join(str(t) for t in tags))
    return "\n".join(p for p in parts if p).strip()


def embed(texts, session, headers):
    """Workers AI. При 429/5xx ждём и повторяем — модель общая на аккаунт, бывает занята."""
    for attempt in range(6):
        r = session.post(f"{api_base()}/ai/run/{MODEL}", headers=headers,
                         json={"text": texts}, timeout=120)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(2 ** attempt, 30))
            continue
        r.raise_for_status()
        d = r.json()
        if not d.get("success"):
            raise RuntimeError(f"Workers AI: {d.get('errors')}")
        return d["result"]["data"]
    raise RuntimeError("Workers AI недоступна после 6 попыток")


def upsert(vectors, session, headers):
    """Vectorize принимает NDJSON — по вектору на строку."""
    body = "\n".join(json.dumps(v, ensure_ascii=False) for v in vectors).encode("utf-8")
    r = session.post(f"{api_base()}/vectorize/v2/indexes/{INDEX}/upsert",
                     headers={**headers, "Content-Type": "application/x-ndjson"},
                     data=body, timeout=180)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(f"Vectorize: {d.get('errors')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="пересчитать весь корпус")
    args = ap.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print("нет CLOUDFLARE_API_TOKEN. Стоп.")
        return 1
    headers = {"Authorization": f"Bearer {token}"}
    session = requests.Session()

    idx = ROOT / "lang" / "ru" / "articles-index.json"
    if not idx.exists():
        print(f"нет {idx} — сначала нужен собранный индекс статей. Стоп.")
        return 1
    articles = json.loads(idx.read_text(encoding="utf-8"))

    old = {} if args.all else (
        json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {})
    new, todo = {}, []
    for a in articles:
        aid = a.get("id")
        if not aid:
            continue
        text = article_text(a)
        if not text:
            continue
        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        new[aid] = h
        if old.get(aid) != h:
            todo.append((aid, text, a))
    print(f"статей: {len(new)} | к пересчёту: {len(todo)}")
    if not todo:
        print("✅ смысловой индекс уже актуален.")
        return 0

    done = 0
    for i in range(0, len(todo), EMBED_BATCH):
        chunk = todo[i:i + EMBED_BATCH]
        vecs = embed([t for _, t, _ in chunk], session, headers)
        batch = []
        for (aid, _, a), v in zip(chunk, vecs):
            batch.append({
                "id": aid,
                "values": v,
                # Метаданные нужны, чтобы отдать результат поиска без похода в другой индекс.
                "metadata": {
                    "title": (a.get("title") or "")[:400],
                    "url": a.get("url") or "",
                    "date": a.get("date") or "",
                    "primary_category": a.get("primary_category") or "",
                },
            })
        for j in range(0, len(batch), UPSERT_BATCH):
            upsert(batch[j:j + UPSERT_BATCH], session, headers)
        done += len(chunk)
        if done % 250 < EMBED_BATCH:
            print(f"  посчитано {done}/{len(todo)}")

    MANIFEST.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    print(f"✅ смысловой индекс обновлён: {done} статей.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
