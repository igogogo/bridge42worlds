# -*- coding: utf-8 -*-
"""Формулы внутри абзацев — в LaTeX, чтобы KaTeX их рисовал, а не строка вида «ℓ_r ≍ τ^{1/2}».

Владелец 09.09: «по тексту есть формулы не в латехе, надо поправить, чтобы было красиво».
Тексты написаны с одной нотацией на всех пяти языках, поэтому замены общие. Порядок
важен: длинные фрагменты раньше коротких, иначе «u_θ» внутри «|u_θ|, |u_z| ≍ …» сломает
длинную замену. Строчные формулы берём в \\( … \\): доллары в прозе встречаются, а
скобки нет.

Не трогаем: заголовки, однострочники, аннотации (идут в карточки, поиск и вектор, где
KaTeX нет) и поле formulas (там LaTeX уже).
"""
import re

def _m(s):
    # «0<h<1/100» в HTML читается как начало тега <h…>: браузер съедал хвост формулы вместе
    # с куском абзаца (поймано 09.09 на разделе «Методы»). Внутри формул < и > пишем
    # командами KaTeX, которые тегами не выглядят.
    s = s.replace("<", "\\lt ").replace(">", "\\gt ")
    return "\\(" + s + "\\)"

PAIRS = [
    # уравнение и остаток
    ("∂_t u + (u·∇)u − νΔu + ∇p = f, ∇·u = 0, u(·,0) = 0",
     _m(r"\partial_t u+(u\cdot\nabla)u-\nu\Delta u+\nabla p=f,\ \nabla\cdot u=0,\ u(\cdot,0)=0")),
    ("R(u,p) = ∂_t u + (u·∇)u − Δu + ∇p", _m(r"R(u,p)=\partial_t u+(u\cdot\nabla)u-\Delta u+\nabla p")),
    # теорема
    ("f ∈ C_c^∞(R³×(0,∞); R³)", _m(r"f\in C_c^\infty(\mathbb R^3\times(0,\infty);\mathbb R^3)")),
    ("f ∈ C_c^∞(R³×(0,∞))", _m(r"f\in C_c^\infty(\mathbb R^3\times(0,\infty))")),
    ("f ∈ C_c^∞", _m(r"f\in C_c^\infty")),
    ("supp u(·,t) ∪ supp p(·,t) ⊂ K", _m(r"\operatorname{supp}u(\cdot,t)\cup\operatorname{supp}p(\cdot,t)\subset K")),
    ("sup_{0≤t<1}‖u(t)‖_{L²} < ∞", _m(r"\sup_{0\le t<1}\|u(t)\|_{L^2}<\infty")),
    ("limsup_{t↑1}‖u(t)‖_{L^∞} = ∞", _m(r"\limsup_{t\uparrow1}\|u(t)\|_{L^\infty}=\infty")),
    ("sup_t‖u(t)‖_{L²} < ∞", _m(r"\sup_t\|u(t)\|_{L^2}<\infty")),
    ("‖u(t)‖_{L^∞} → ∞", _m(r"\|u(t)\|_{L^\infty}\to\infty")),
    ("‖u(t)‖_∞ → ∞", _m(r"\|u(t)\|_\infty\to\infty")),
    ("sup‖u‖_{L²} < ∞", _m(r"\sup\|u\|_{L^2}<\infty")),
    ("L^∞_t L³_x", _m(r"L^\infty_t L^3_x")),
    ("T³ = R³/Z³", _m(r"\mathbb T^3=\mathbb R^3/\mathbb Z^3")),
    ("R³×[0,∞)", _m(r"\mathbb R^3\times[0,\infty)")),
    ("R³×[0,1)", _m(r"\mathbb R^3\times[0,1)")),
    ("K ⊂ R³", _m(r"K\subset\mathbb R^3")),
    # масштабы
    ("ℓ_r ≍ τ^{1/2}, ℓ_z ≍ τ^{1/2−h}, 0 < h < 1/100",
     _m(r"\ell_r\asymp\tau^{1/2},\ \ell_z\asymp\tau^{1/2-h},\ 0<h<1/100")),
    ("|u_θ|, |u_z| ≍ τ^{−1/2−h}, |u_r| = O(τ^{−1/2})",
     _m(r"|u_\theta|,\,|u_z|\asymp\tau^{-1/2-h},\ |u_r|=O(\tau^{-1/2})")),
    ("|u_r|/ℓ_r, |u_z|/ℓ_z, ν/ℓ_r²", _m(r"|u_r|/\ell_r,\ |u_z|/\ell_z,\ \nu/\ell_r^2")),
    ("ℓ_r/ℓ_z ≍ τ^h → 0", _m(r"\ell_r/\ell_z\asymp\tau^{h}\to0")),
    ("ℓ_r ≍ τ^{1/2}", _m(r"\ell_r\asymp\tau^{1/2}")),
    ("ℓ_z ≍ τ^{1/2−h}", _m(r"\ell_z\asymp\tau^{1/2-h}")),
    ("Re_θ ≍ τ^{−h} → ∞", _m(r"\mathrm{Re}_\theta\asymp\tau^{-h}\to\infty")),
    ("Re_θ ~ τ^{−h} → ∞", _m(r"\mathrm{Re}_\theta\sim\tau^{-h}\to\infty")),
    ("Re_r = O(1)", _m(r"\mathrm{Re}_r=O(1)")),
    ("≍ τ^{1/2−3h} → 0", _m(r"\asymp\tau^{1/2-3h}\to0")),
    ("≍ τ^{3/2−h}", _m(r"\asymp\tau^{3/2-h}")),
    ("≍ τ^{−1/2−h}", _m(r"\asymp\tau^{-1/2-h}")),
    ("≍ τ^{1/2−h}", _m(r"\asymp\tau^{1/2-h}")),
    ("≍ τ^{1/2}", _m(r"\asymp\tau^{1/2}")),
    ("≍ τ^{−1}", _m(r"\asymp\tau^{-1}")),
    ("~τ^{1/2−3h}", _m(r"\sim\tau^{1/2-3h}")), ("~ τ^{1/2−3h}", _m(r"\sim\tau^{1/2-3h}")),
    ("~τ^{3/2−h}", _m(r"\sim\tau^{3/2-h}")), ("~ τ^{3/2−h}", _m(r"\sim\tau^{3/2-h}")),
    ("~τ^{−1/2−h}", _m(r"\sim\tau^{-1/2-h}")), ("~ τ^{−1/2−h}", _m(r"\sim\tau^{-1/2-h}")),
    ("~τ^{1/2−h}", _m(r"\sim\tau^{1/2-h}")), ("~ τ^{1/2−h}", _m(r"\sim\tau^{1/2-h}")),
    ("~τ^{1/2}", _m(r"\sim\tau^{1/2}")), ("~ τ^{1/2}", _m(r"\sim\tau^{1/2}")),
    ("~ τ^{−h} → ∞", _m(r"\sim\tau^{-h}\to\infty")),
    ("τ^{2h}", _m(r"\tau^{2h}")),
    ("τ^{−1}", _m(r"\tau^{-1}")),
    ("τ = 1 − t", _m(r"\tau=1-t")),
    ("u_z(r,0,t) ≠ 0", _m(r"u_z(r,0,t)\neq0")),
    ("h < 1/100", _m(r"h<1/100")),
    ("∝ k²", _m(r"\propto k^2")),
    ("r·u_θ", _m(r"r\,u_\theta")),
    ("ν > 0", _m(r"\nu>0")),
    ("t ↑ 1", _m(r"t\uparrow1")),
    ("t → 1", _m(r"t\to1")),
    ("t = 1", _m(r"t=1")),
    ("z = 0", _m(r"z=0")),
    ("u_θ", _m(r"u_\theta")),
    ("u_z", _m(r"u_z")),
    ("u_r", _m(r"u_r")),
    ("Re_θ", _m(r"\mathrm{Re}_\theta")),
    ("Re_r", _m(r"\mathrm{Re}_r")),
    ("(u_B, p_B)", _m(r"(u_B,p_B)")),
]
# одиночные буквы-параметры в прозе: τ, ν — только как отдельные слова
_SINGLE = [(re.compile(r"(?<![\w\\{^_])τ(?![\w^_{])"), _m(r"\tau")),
           (re.compile(r"(?<![\w\\{^_])ν(?![\w^_{])"), _m(r"\nu"))]

# внутри уже поставленной формулы вторая замена не должна сработать: защищаем \( … \)
_PROTECT = re.compile(r"\\\(.*?\\\)")


def _outside(text, fn):
    """Применить fn только к кускам вне \\( … \\): формулы, уже поставленные прежними
    заменами, не трогаем — иначе «u_z» внутри готовой формулы ставилось второй раз."""
    parts = _PROTECT.split(text)
    kept = _PROTECT.findall(text)
    return "".join(fn(p) + (kept[i] if i < len(kept) else "") for i, p in enumerate(parts))


def latexify(text):
    if not isinstance(text, str) or not text:
        return text
    for a, b in PAIRS:
        text = _outside(text, lambda s, a=a, b=b: s.replace(a, b))
    for rx, rep in _SINGLE:
        text = _outside(text, lambda s, rx=rx, rep=rep: rx.sub(rep, s))
    return text


TEXT_FIELDS = ("text", "description", "context", "methods", "results", "implications",
               "future_development", "impact_on", "next_steps", "key_problems_connection", "fun_fact")


def latexify_tier(d):
    d = dict(d)
    for k in TEXT_FIELDS:
        if k in d:
            # Абзацы в исходниках начинаются с «**Подзаголовок.**» — привычка markdown;
            # генератор жирного не знает и печатает звёздочки как есть (владелец 09.09).
            # Снимаем их: ведущая фраза с точкой читается как подзаголовок и без выделения.
            d[k] = latexify(d[k].replace("**", ""))
    if isinstance(d.get("key_numbers"), dict):
        d["key_numbers"] = {k: latexify(v) for k, v in d["key_numbers"].items()}
    return d
