"""Кладёт в KV краткое содержание статей — контекст для бота-исследователя (/api/ask).

Зачем отдельный шаг. Бот отвечает СТРОГО по нашим материалам, значит Worker должен эти
материалы прочитать. Взять их ему неоткуда: `data.json` живёт на диске машины, в публикацию
не попадает, а тянуть в Worker шеститимегабайтный индекс на каждый вопрос — безумие.
Поэтому раскладываем заранее: по ключу на пару (статья, язык).

Почему KV, а не метаданные вектора. Метаданные Vectorize возвращаются при КАЖДОМ поиске,
и класть туда четыре аннотации значит платить за их пересылку на каждый запрос читателя,
включая те, где до ответа бота дело не дойдёт. KV читается только когда бот реально
собирает контекст — по одному ключу на статью из пятёрки.

Объём: ~2000 статей × 4 языка ≈ 8 тысяч ключей по килобайту. Пишем пачками, дельтой по md5.

Запуск:
    python cloudflare/context_build.py                     # догнать изменившееся
    python cloudflare/context_build.py --all               # переписать всё
    B42_DATA_ROOT=C:\\...\\bridge42worlds python ...        # если данные в другой папке
"""
import os, sys, json, hashlib, argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATA_ROOT = Path(os.environ.get("B42_DATA_ROOT") or ROOT)
MANIFEST = ROOT / "cloudflare" / ".context-manifest.json"
KV_NAMESPACE = os.environ.get("KV_TOKENS_ID", "bf89cc7963304948a6a7aeeb0a06e43d")
LANGS = ("ru", "en", "es", "ar")
BULK = 5000          # столько пар за один запрос (предел Cloudflare — 10 000)


def api(path):
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    return f"https://api.cloudflare.com/client/v4/accounts/{acc}{path}"


def pick_abstract(data, lang):
    """Берём готовую аннотацию нужного языка. Переводить нечего — она уже написана
    на всех четырёх, это главная причина, по которой контекст дешёвый."""
    ab = data.get("abstract")
    if not isinstance(ab, dict):
        return ""
    v = ab.get(lang)
    if isinstance(v, dict):
        v = v.get("advanced") or v.get("popular") or v.get("simple")
    return str(v or "").strip()


def title_of(data, lang):
    t = data.get("title")
    if isinstance(t, dict):
        return str(t.get(lang) or t.get("ru") or "").strip()
    return str(t or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="переписать весь корпус")
    args = ap.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print("нет CLOUDFLARE_API_TOKEN. Стоп.")
        return 1
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    old = {} if args.all else (
        json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {})
    new, pairs = {}, []
    skipped = 0

    for p in sorted(DATA_ROOT.glob("lang/ru/archive/*/*/data.json")):
        aid = p.parent.name
        day = p.parent.parent.name
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            skipped += 1
            continue
        for lang in LANGS:
            text = pick_abstract(d, lang)
            if not text:
                continue
            rec = {
                "title": title_of(d, lang),
                "text": text[:2000],
                "url": f"/lang/{lang}/archive/{day}/{aid}/",
                "date": day,
            }
            body = json.dumps(rec, ensure_ascii=False)
            key = f"ctx:{aid}:{lang}"
            h = hashlib.md5(body.encode("utf-8")).hexdigest()
            new[key] = h
            if old.get(key) != h:
                pairs.append({"key": key, "value": body})

    print(f"ключей всего: {len(new)} | к записи: {len(pairs)}" +
          (f" | нечитаемых файлов: {skipped}" if skipped else ""))
    if not pairs:
        print("✅ контекст уже актуален.")
        return 0

    for i in range(0, len(pairs), BULK):
        chunk = pairs[i:i + BULK]
        r = requests.put(api(f"/storage/kv/namespaces/{KV_NAMESPACE}/bulk"),
                         headers=H, json=chunk, timeout=180)
        d = r.json()
        if not d.get("success"):
            raise RuntimeError(f"KV: {d.get('errors')}")
        print(f"  записано {min(i + BULK, len(pairs))}/{len(pairs)}")

    MANIFEST.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    print(f"✅ контекст разложен: {len(pairs)} ключей обновлено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
