"""Отметка «я жив» для фоновых сторожей (очередь заказов, сторож почты).

Зачем. Оба процесса держатся задачей планировщика и делают полезное молча: когда всё
хорошо, они ничего не пишут и ничем себя не проявляют. Значит упавший процесс выглядит
ровно как спокойный — и узнаём мы о его смерти от обиженного автора, чьё письмо никто
не прочитал (условие архитектора 2026-08-01).

Отметка кладётся в KV, а проверяет её cron-Worker вместе с ежедневной сводкой: он и так
просыпается каждый день и умеет писать в наш канал. Отдельного наблюдателя заводить
незачем — он сам стал бы третьим процессом, за которым нужно следить.

Ключ живёт втрое дольше обещанного периода: если отметка исчезла совсем, это тоже
молчание, и Worker увидит отсутствие ключа так же, как устаревший.
"""
import os
import requests

KV_NAMESPACE = os.environ.get("KV_TOKENS_ID", "bf89cc7963304948a6a7aeeb0a06e43d")


def beat(name, ttl_seconds=6 * 3600):
    """Отмечает, что процесс `name` жив. Никогда не роняет вызывающего: сторож, упавший
    из-за неотправленной отметки, — это ровно та беда, от которой отметка защищает."""
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        return False
    try:
        import time
        requests.put(
            f"https://api.cloudflare.com/client/v4/accounts/{acc}"
            f"/storage/kv/namespaces/{KV_NAMESPACE}/values/hb:{name}",
            headers={"Authorization": f"Bearer {tok}"},
            files={"value": (None, str(int(time.time() * 1000))),
                   "metadata": (None, "{}")},
            timeout=20)
        return True
    except Exception:
        return False
