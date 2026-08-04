# -*- coding: utf-8 -*-
"""Общие утилиты. Все скрипты запускаются из папки scripts/: python NN_name.py
Данные ищутся в ../data (пакет) или C:\\server (оригинал)."""
import os, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = [os.path.join(HERE, "..", "data"), r"C:\server"]
DATA = next(p for p in CAND if os.path.isdir(p))
FIG  = os.path.join(HERE, "..", "figures")

LSB = 4.0 / 32768          # масштаб прошивки SCALE_4G, g на счёт
STATIC_DEVS = ["58_E6_C5_14_2C_0C", "58_E6_C5_14_64_E8"]   # агенты 0 и 1
ROT_CARRIERS = ["58_E6_C5_14_36_D8", "58_E6_C5_14_6C_D0",
                "58_E6_C5_15_7A_A4", "58_E6_C5_15_87_44"]

def files_of(series, dev="*"):
    """Все csv файлы устройства dev в серии (bin не нужны — csv эквивалентен)."""
    return sorted(glob.glob(os.path.join(DATA, series, "csv", "**", f"{dev}.csv"),
                            recursive=True))

def load_g(series, dev, lo=None, hi=None):
    """Все значения g устройства за серию. Формат CSV:
    agent_id,prime,g,timestamp_us,checked_since ; g = модуль вектора."""
    gs = []
    for f in files_of(series, dev):
        a = np.genfromtxt(f, delimiter=",", skip_header=1, usecols=(2,))
        gs.append(np.atleast_1d(a))
    g = np.concatenate(gs) if gs else np.array([])
    if lo is not None:
        g = g[(g > lo) & (g < hi)]
    return g

def stick_R(g, step=256, phase=47):
    """Метрика залипания: фазовая когерентность счётов с решёткой step/phase.
    R=0 — нет структуры; z = R*sqrt(n) — значимость в сигмах."""
    c = g / LSB
    Z = np.mean(np.exp(2j * np.pi * (c - phase) / step))
    return abs(Z), abs(Z) * np.sqrt(g.size)

def residual_spectrum(g, pmin=0.004, pmax=0.06, step=0.0005, smooth=0.02):
    """Фурье остатка гистограммы после вычитания гладкой формы.
    Возвращает (периоды, мощность/фон)."""
    mu = np.median(g)
    nb = 1000
    bins = mu - 0.25 + step * np.arange(nb + 1)
    h, _ = np.histogram(g, bins=bins)
    k = int(smooth / step)
    sm = np.convolve(h, np.ones(k) / k, mode="same")
    r = h - sm; r = r - r.mean()
    F = np.abs(np.fft.rfft(r)) ** 2
    fr = np.fft.rfftfreq(nb, d=step)
    sel = (fr >= 1 / pmax) & (fr <= 1 / pmin)
    return 1 / fr[sel], F[sel] / F[sel].mean()
