"""Дочищает девять мест, где русский перемешан с формулой.

Их не стал отдавать модели: там LaTeX вперемешку с текстом, и автоперевод рискует поломать
разметку. Перевод выписан вручную, формулы не тронуты.
"""
import json
from pathlib import Path

ROOT = Path("data/theory/courses")

# файл → язык → путь (список ключей/индексов) → новое значение
FIX = [
    ("nuclear/03-energy.json", "es", ["example", "law"],
     r"$E = N \cdot Q$, donde $N = \dfrac{m}{M}N_A$"),

    ("oscillations/03-resonance.json", "en", ["memo", "keyIdeas", 0, "title"],
     r"$A(\omega)$ peaks near $\omega \approx \omega_0$"),
    ("oscillations/03-resonance.json", "en", ["memo", "keyIdeas", 0, "text"],
     r"$A(\omega)$ peaks near $\omega \approx \omega_0$; without friction it would be infinite"),
    ("oscillations/03-resonance.json", "en", ["memo", "keyIdeas", 1, "title"],
     r"Quality factor $Q = \omega_0/2\gamma$"),
    ("oscillations/03-resonance.json", "en", ["memo", "keyIdeas", 2, "title"],
     r"The relative width of the peak equals $1/Q$"),

    ("quantum/01-quanta.json", "en", ["example", "law"],
     r"$h\nu = A_{\text{out}} + E_{\text{kin}}$; it is convenient to work in electronvolts "
     r"via $E[\text{eV}] = 1240/\lambda[\text{nm}]$"),

    ("quantum/03-uncertainty.json", "es", ["example", "law"],
     r"$\Delta p \approx \hbar/\Delta x$; a energías altas $E \approx pc$"),
    ("quantum/03-uncertainty.json", "ar", ["example", "law"],
     r"$\Delta p \approx \hbar/\Delta x$؛ عند الطاقات العالية $E \approx pc$"),
]

# Арабский ответ про сжатие: внутри остались русские «объясн»/«ение» как пример предсказуемости
# текста. Пример работает только на русском, поэтому меняем на арабскую пару.
AR_ENTROPY = ("entropy/03-information.json", "ar", ["curiosities", "items", 1, "answer"],
              ("объясн", "توضي"), ("ение", "ح"))


def get_set(node, path, value):
    for k in path[:-1]:
        node = node[k]
    old = node[path[-1]]
    node[path[-1]] = value
    return old


def main():
    changed = 0
    for rel, lang, path, value in FIX:
        f = ROOT / rel
        d = json.loads(f.read_text(encoding="utf-8"))
        old = get_set(d[lang], path, value)
        if old != value:
            changed += 1
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"  {rel} [{lang}] {'.'.join(map(str, path))}")

    rel, lang, path, *pairs = AR_ENTROPY
    f = ROOT / rel
    d = json.loads(f.read_text(encoding="utf-8"))
    node = d[lang]
    for k in path[:-1]:
        node = node[k]
    s = node[path[-1]]
    new = s
    for src, dst in pairs:
        new = new.replace(src, dst)
    if new != s:
        node[path[-1]] = new
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed += 1
        print(f"  {rel} [{lang}] {'.'.join(map(str, path))}")
    print("ИСПРАВЛЕНО:", changed)


if __name__ == "__main__":
    main()
