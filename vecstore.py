#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Хранилище векторов: двоичный float16 вместо JSON.

ЗАЧЕМ. Пилот на одном месяце arXiv (28 985 аннотаций) занял 297 МБ в JSONL — это
10,5 КБ на вектор там, где хватает двух. На все 3,12 млн вышло бы 32 ГБ при 44 ГБ
свободных на машине владельца: карта заняла бы три четверти диска.

    JSONL          32 ГБ
    float32        12,8 ГБ
    float16        6,4 ГБ   ← берём это

ПОЧЕМУ ПОЛОВИННАЯ ТОЧНОСТЬ НЕ ВРЕДИТ. Векторы нормированы, косинус между ними —
скалярное произведение. Переход на float16 меняет его в четвёртом знаке после запятой,
а все наши решения принимаются на сотых (пороги 0,55–0,65, разрывы между «своё»
и «чужое» — десятые). Проверка этого утверждения — в `--check`, не на веру.

ФОРМАТ. Два файла рядом:
    <имя>.f16   — матрица N×1024, подряд, без заголовка
    <имя>.ids   — идентификаторы, по одному на строку, в том же порядке
Читается одной строкой в numpy и кладётся в память целиком: 6,4 ГБ float16 при
16 ГБ ОЗУ — впритык, поэтому предусмотрено чтение кусками (`memmap`).

Нарочно без своего формата с заголовками и версиями: чем проще, тем дольше проживёт.
"""
import json, pathlib, sys, argparse
import numpy as np

DIM = 1024


def save(path, ids, vecs):
    """vecs — список списков или numpy-массив N×1024. Нормирует и пишет float16."""
    a = np.asarray(vecs, dtype=np.float32)
    if a.ndim != 2 or a.shape[1] != DIM:
        raise ValueError(f"ожидалась матрица N×{DIM}, пришло {a.shape}")
    n = np.linalg.norm(a, axis=1, keepdims=True)
    n[n == 0] = 1.0
    a = (a / n).astype(np.float16)
    p = pathlib.Path(path)
    p.with_suffix(".f16").write_bytes(a.tobytes())
    p.with_suffix(".ids").write_text("\n".join(map(str, ids)), encoding="utf-8")
    return a.shape


def load(path, mmap=False):
    """Вернуть (ids, matrix). mmap=True — не тянуть в память целиком."""
    p = pathlib.Path(path)
    ids = p.with_suffix(".ids").read_text(encoding="utf-8").splitlines()
    if mmap:
        m = np.memmap(p.with_suffix(".f16"), dtype=np.float16, mode="r")
    else:
        m = np.frombuffer(p.with_suffix(".f16").read_bytes(), dtype=np.float16)
    return ids, m.reshape(len(ids), DIM)


def append(path, ids, vecs):
    """Дописать в конец. Нужен для полей, которые не помещаются в память ЦЕЛИКОМ.

    save() собирает всю матрицу и пишет одним куском — на 3,13 млн работ это 6,4 ГБ
    в оперативной памяти и промежуточный JSONL на тридцать гигабайт, которого просто
    некуда положить. Здесь тот же формат, но растёт по кускам, и прогон можно
    прервать и продолжить: файлы .f16 и .ids всегда согласованы по длине.
    """
    a = np.asarray(vecs, dtype=np.float32)
    if a.ndim != 2 or a.shape[1] != DIM:
        raise ValueError(f"ожидалась матрица N×{DIM}, пришло {a.shape}")
    n = np.linalg.norm(a, axis=1, keepdims=True)
    n[n == 0] = 1.0
    a = (a / n).astype(np.float16)
    p = pathlib.Path(path)
    with p.with_suffix(".f16").open("ab") as f:
        f.write(a.tobytes())
    with p.with_suffix(".ids").open("a", encoding="utf-8") as f:
        f.write("".join(f"{i}\n" for i in ids))
    return a.shape


def done_ids(path):
    """Что уже посчитано. Читаем ТОЛЬКО .ids — их пара мегабайт против гигабайтов
    векторов; ради проверки «продолжаем с какого места» тянуть векторы незачем."""
    p = pathlib.Path(path).with_suffix(".ids")
    if not p.exists():
        return []
    return p.read_text(encoding="utf-8").split("\n")[:-1] or []


def repair(path):
    """Согласовать .f16 и .ids после обрыва посреди записи.

    Прогон на десять часов будет прерван — питанием, сном машины, чем угодно.
    Если обрыв пришёлся на середину append(), в .f16 окажется больше или меньше
    строк, чем в .ids, и файл станет молча непригоден: reshape разложит числа
    со сдвигом, и все векторы после точки обрыва будут чужими. Поэтому длину
    сверяем и лишний хвост отрезаем — ПО МЕНЬШЕМУ из двух.
    """
    p = pathlib.Path(path)
    fp, ip = p.with_suffix(".f16"), p.with_suffix(".ids")
    if not (fp.exists() and ip.exists()):
        return 0
    n_vec = fp.stat().st_size // (DIM * 2)
    ids = ip.read_text(encoding="utf-8").split("\n")[:-1]
    n = min(n_vec, len(ids))
    if n_vec != len(ids):
        with fp.open("r+b") as f:
            f.truncate(n * DIM * 2)
        ip.write_text("".join(f"{i}\n" for i in ids[:n]), encoding="utf-8")
        print(f"починено: было векторов {n_vec}, идентификаторов {len(ids)}, стало {n}")
    return n


def from_jsonl(src, dst):
    ids, vecs = [], []
    for line in pathlib.Path(src).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ids.append(r["id"])
        vecs.append(r["vec"])
    shape = save(dst, ids, vecs)
    s_old = pathlib.Path(src).stat().st_size
    s_new = (pathlib.Path(dst).with_suffix(".f16").stat().st_size
             + pathlib.Path(dst).with_suffix(".ids").stat().st_size)
    print(f"{src} → {dst}: {shape[0]} векторов")
    print(f"  было {s_old/1024/1024:.1f} МБ, стало {s_new/1024/1024:.1f} МБ "
          f"(в {s_old/max(1,s_new):.1f} раза меньше)")
    return ids, vecs


def check(src, dst):
    """ПРОВЕРКА ДО ДОВЕРИЯ: сколько теряет косинус от половинной точности.

    Не «должно быть нормально», а число: максимальное и среднее расхождение
    на тысяче случайных пар. Если разойдётся в сотых — формат менять нельзя.
    """
    ids32, vecs32 = [], []
    for line in pathlib.Path(src).read_text(encoding="utf-8").splitlines()[:2000]:
        if line.strip():
            r = json.loads(line)
            ids32.append(r["id"]); vecs32.append(r["vec"])
    a32 = np.asarray(vecs32, dtype=np.float32)
    a32 /= np.linalg.norm(a32, axis=1, keepdims=True)
    a16 = a32.astype(np.float16).astype(np.float32)

    rng = np.random.default_rng(42)
    i = rng.integers(0, len(a32), 1000)
    j = rng.integers(0, len(a32), 1000)
    c32 = np.einsum("ij,ij->i", a32[i], a32[j])
    c16 = np.einsum("ij,ij->i", a16[i], a16[j])
    d = np.abs(c32 - c16)
    print(f"расхождение косинуса float32 → float16 на 1000 пар:")
    print(f"  среднее {d.mean():.6f}   максимум {d.max():.6f}")
    print(f"  для сравнения: наши пороги стоят на 0,55–0,65, разрывы между "
          f"«своё» и «чужое» — десятые")
    verdict = "БЕЗОПАСНО" if d.max() < 0.001 else "ОСТОРОЖНО: расхождение заметное"
    print(f"  вердикт: {verdict}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-jsonl")
    ap.add_argument("--to")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check and a.from_jsonl:
        check(a.from_jsonl, a.to or "")
    elif a.from_jsonl and a.to:
        from_jsonl(a.from_jsonl, a.to)
    else:
        ap.print_help()
