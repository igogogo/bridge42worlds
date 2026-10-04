# -*- coding: utf-8 -*-
"""Отсечка недоступных хостов на один прогон.

04.10: полный разбор простоял 15 минут без единой строки в журнале — ERDDAP coastwatch.pfeg.noaa.gov
перестал отвечать (соединение висело в SYN), а oisst.build ждал по 300 секунд на каждый из 14 боксов
подряд, и буи TAO с того же сервера — ещё по 120 секунд на станцию: около часа ожидания ради хвостов,
которые и так лежат в кэше. Теперь хост, не ответивший по СЕТИ (нет соединения, таймаут), помечается, и
следующие запросы к нему в этом прогоне отказывают сразу; потребитель берёт сохранённое и пишет ошибку.
Ответ сервера с ошибкой (HTTP 4xx/5xx) хост не помечает: сервер жив, не нашлось что-то одно.
"""
import socket
import urllib.error
from urllib.parse import urlparse

_DOWN = {}


def host_of(url):
    return urlparse(url).hostname or ""


def is_down(url):
    """Причина, по которой хост помечен в этом прогоне, или None."""
    return _DOWN.get(host_of(url))


def mark(url, e):
    """Запомнить сетевую беду хоста. HTTPError — ответ сервера, хост жив: не помечаем."""
    if isinstance(e, urllib.error.HTTPError):
        return
    if isinstance(e, (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError)):
        _DOWN[host_of(url)] = str(e)[:120] or e.__class__.__name__


def guard(url):
    """Отказать сразу, если хост уже не ответил в этом прогоне."""
    why = is_down(url)
    if why:
        raise RuntimeError(f"{host_of(url)} did not answer earlier in this run ({why})")
