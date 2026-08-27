# -*- coding: utf-8 -*-
"""Карточки понятий → Vectorize: вектор реестра переезжает в облако.

ГДЕ КАКОЙ ВЕКТОР ЖИВЁТ (вопрос владельца 26 августа «а вектор тут где»):

    статьи      Vectorize, индекс b42-articles — уже в проде: на нём /api/search
                и похожие. «Статья — готовый вектор» уже правда.
    карточки    только ЛОКАЛЬНО (b42-ml/data/concept-cards.f16). На них посчитаны
    понятий     переразметка v2, суперпонятия, сверка кандидатов — но всё это
                работает, пока открыт ноутбук. Этот файл закрывает разрыв.

ЗАЧЕМ КАРТОЧКИ В ОБЛАКЕ. Три вещи начинают работать без локальной матрицы:

  1. Живой механизм НА ПОТОКЕ: новая статья при заливке уже получает вектор — воркер
     спрашивает Vectorize «ближайшие понятия из пространства concepts» и размечает
     её на лету. Локальный пересчёт остаётся для массовых прогонов.
  2. Сверка кандидатов (concept_harvest --match) из любого места, не только с машины,
     где лежит b42-ml.
  3. Поиск по смыслу сможет находить и понятия, не только статьи: «замёрзшая вода
     быстрее горячей» → страница парадокса Мпембы, а не только статьи о нём.

ПРОСТРАНСТВО concepts В ТОМ ЖЕ ИНДЕКСЕ. Не отдельный индекс: bge-m3 один, размерность
одна, а пространства имён в Vectorize ровно для этого — статьи лежат в "ours",
понятия лягут в "concepts". Запрос с фильтром по пространству не путает одно с другим.

МЕСТО: 1222 карточки × 1024 измерения = 1.25 млн — на порядок меньше статей.

Дельты нет намеренно: карточки меняются только волнами (сейчас их 1222, следующая
правка — когда доименуются группы или дорастут кандидаты), полная перезаливка стоит
три вызова и секунды. Дельта здесь была бы кодом ради кода.

ЗАПУСК:  python tools/concepts_to_vectorize.py          показать, что зальётся
         python tools/concepts_to_vectorize.py --apply  залить (под общим замком)
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
INDEX = os.environ.get("VECTORIZE_INDEX", "b42-articles")
NAMESPACE = "concepts"
UPSERT_BATCH = 500


def env():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        raise SystemExit("нет CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN в .env")
    return f"https://api.cloudflare.com/client/v4/accounts/{acc}", tok


def load_cards():
    sys.path.insert(0, str(ML))
    import concepts_super as cs
    cids, CV = cs.load_cards()
    # Класс берём из ЖИВОГО реестра, а не из v3: v3 — вход прошлой волны, и
    # родившихся после неё там нет вовсе. Константы и статистика уезжали бы в
    # облако классом «понятие», и фильтр поиска по классу их не находил.
    live = ROOT / "data" / "concepts-live.json"
    if live.exists():
        reg = json.loads(live.read_text(encoding="utf-8"))["concepts"]
    else:
        reg = json.loads((ML / "data" / "concepts-v3.json").read_text(encoding="utf-8"))["concepts"]
    return cids, CV, reg


def main():
    ap = argparse.ArgumentParser(description="Векторы карточек понятий → Vectorize")
    ap.add_argument("--apply", action="store_true", help="залить (без флага — показать)")
    a = ap.parse_args()

    cids, CV, reg = load_cards()
    print(f"карточек {len(cids)} × {CV.shape[1]} измерений "
          f"= {len(cids) * CV.shape[1] / 1e6:.2f} млн · пространство «{NAMESPACE}» "
          f"в индексе {INDEX}")
    if not a.apply:
        print("сверка — ничего не заливается; --apply зальёт (под общим замком)")
        return 0

    # Заливка в облако — прогон; замок общий, как у любой заливки.
    try:
        from tools.freeze import guard
        guard("заливка векторов понятий")
    except ImportError:
        pass

    import requests
    base, tok = env()
    headers = {"Authorization": f"Bearer {tok}"}
    sess = requests.Session()
    sent = 0
    for s in range(0, len(cids), UPSERT_BATCH):
        chunk = range(s, min(s + UPSERT_BATCH, len(cids)))
        # NDJSON, как того требует upsert; метаданные держим крошечными — kind
        # пригодится фильтру («только методы»), больше ничего вектору знать не надо.
        lines = []
        for i in chunk:
            cid = cids[i]
            lines.append(json.dumps({
                "id": f"c:{cid}",
                "values": [round(float(x), 5) for x in CV[i]],
                "namespace": NAMESPACE,
                "metadata": {"kind": (reg.get(cid) or {}).get("kind") or "concept"},
            }, ensure_ascii=False))
        body = "\n".join(lines).encode("utf-8")
        for attempt in range(5):
            r = sess.post(f"{base}/vectorize/v2/indexes/{INDEX}/upsert",
                          headers={**headers, "Content-Type": "application/x-ndjson"},
                          data=body, timeout=180)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(2 ** attempt * 2, 30))
                continue
            r.raise_for_status()
            break
        sent += len(lines)
        print(f"  залито {sent}/{len(cids)}")
    print("✅ пространство «concepts» обновлено")
    return 0


if __name__ == "__main__":
    sys.exit(main())
