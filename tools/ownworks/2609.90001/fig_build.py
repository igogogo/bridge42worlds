# -*- coding: utf-8 -*-
"""Наша схема механизма взрыва: сечение вихря-иглы и вид сверху. SVG на пяти языках.

Рисунок наш, не авторский: у работы лицензии нет, чужие рисунки не берём (правило 02.09),
а схему конструкции нарисовать самим и полезнее — на ней подписаны части доказательства:
ядро-игла, приток по спирали, отток вдоль оси, кольцо с импульсами, тепловая внешность.

    python fig_build.py <папка статьи>
"""
import sys
import math
import pathlib

L = {
    "ru": {"axis": "ось", "core": "ядро-игла: сжимается\nи разгоняется", "inflow": "приток по спирали",
           "out": "отток вдоль оси", "ann": "кольцо: импульсы двух семей\nдают недостающее напряжение",
           "ext": "снаружи: чистое вращение,\nсилы не нужно", "top": "вид сверху", "side": "сечение через ось",
           "pulse": "импульс = кольцо вокруг оси", "shrink": "радиус ~ τ½, высота ~ τ½⁻ʰ"},
    "en": {"axis": "axis", "core": "needle core: contracts\nand speeds up", "inflow": "spiral inflow",
           "out": "axial outflow", "ann": "annulus: two pulse families\nsupply the missing stress",
           "ext": "exterior: pure rotation,\nno force needed", "top": "top view", "side": "section through the axis",
           "pulse": "pulse = a ring around the axis", "shrink": "radius ~ τ½, height ~ τ½⁻ʰ"},
    "es": {"axis": "eje", "core": "núcleo-aguja: se contrae\ny se acelera", "inflow": "entrada en espiral",
           "out": "salida axial", "ann": "anillo: dos familias de pulsos\naportan la tensión que falta",
           "ext": "exterior: rotación pura,\nsin fuerza", "top": "vista superior", "side": "sección por el eje",
           "pulse": "pulso = anillo alrededor del eje", "shrink": "radio ~ τ½, altura ~ τ½⁻ʰ"},
    "ar": {"axis": "المحور", "core": "نواة إبرية: تنكمش\nوتتسارع", "inflow": "تدفق حلزوني للداخل",
           "out": "خروج على طول المحور", "ann": "الحلقة: عائلتان من النبضات\nتوفّران الإجهاد الناقص",
           "ext": "الخارج: دوران محض،\nلا حاجة لقوة", "top": "منظر علوي", "side": "مقطع عبر المحور",
           "pulse": "النبضة = حلقة حول المحور", "shrink": "نصف القطر ~ τ½، الارتفاع ~ τ½⁻ʰ"},
    "fr": {"axis": "axe", "core": "cœur-aiguille : se contracte\net accélère", "inflow": "entrée en spirale",
           "out": "sortie axiale", "ann": "anneau : deux familles d'impulsions\nfournissent la contrainte manquante",
           "ext": "extérieur : rotation pure,\nsans force", "top": "vue de dessus", "side": "coupe par l'axe",
           "pulse": "impulsion = anneau autour de l'axe", "shrink": "rayon ~ τ½, hauteur ~ τ½⁻ʰ"},
}

OCHRE, CYAN, INK, MUTE, PALE = "#c8842a", "#2a9db0", "#1f1f1f", "#7a7a7a", "#e9e4dc"
W, H = 960, 540


def text(x, y, s, size=13, fill=INK, anchor="start", weight="normal", italic=False):
    lines = s.split("\n")
    out = []
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x}" y="{y + i * (size + 3)}" font-size="{size}" fill="{fill}" '
                   f'text-anchor="{anchor}" font-weight="{weight}"'
                   f'{" font-style=\"italic\"" if italic else ""}>{ln}</text>')
    return "\n".join(out)


def arrow_defs():
    return ('<defs>'
            f'<marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker>'
            f'<marker id="ac" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{CYAN}"/></marker>'
            f'<marker id="am" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTE}"/></marker>'
            '</defs>')


def side_view(t, ox, oy):
    """Сечение r–z: игла на оси, приток, отток, кольцо с импульсами, внешность."""
    s = []
    cx, cy = ox + 220, oy + 250
    # ось
    s.append(f'<line x1="{cx}" y1="{oy + 20}" x2="{cx}" y2="{oy + 480}" stroke="{MUTE}" stroke-width="1.2" stroke-dasharray="4 4"/>')
    s.append(text(cx + 6, oy + 32, t["axis"], 12, MUTE, italic=True))
    # игла-ядро (вытянутый эллипс) — три момента времени, всё уже и длиннее
    for k, (rx, ry, op) in enumerate([(46, 120, .18), (30, 150, .32), (16, 185, .95)]):
        s.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{OCHRE}" fill-opacity="{op}" stroke="{OCHRE}" stroke-opacity="{min(1, op + .3)}" stroke-width="1.2"/>')
    # отток вдоль оси
    for sgn in (-1, 1):
        y0, y1 = cy + sgn * 60, cy + sgn * 205
        s.append(f'<line x1="{cx}" y1="{y0}" x2="{cx}" y2="{y1}" stroke="{OCHRE}" stroke-width="3" marker-end="url(#ao)"/>')
    s.append(text(cx + 14, cy - 190, t["out"], 12, OCHRE))
    # приток к оси у средней плоскости: изогнутые стрелки с двух сторон
    for sgn in (-1, 1):
        x0 = cx + sgn * 150
        s.append(f'<path d="M{x0},{cy - 26} Q{cx + sgn * 80},{cy - 40} {cx + sgn * 22},{cy - 6}" fill="none" stroke="{OCHRE}" stroke-width="2.4" marker-end="url(#ao)"/>')
        s.append(f'<path d="M{x0},{cy + 26} Q{cx + sgn * 80},{cy + 40} {cx + sgn * 22},{cy + 6}" fill="none" stroke="{OCHRE}" stroke-width="2.4" marker-end="url(#ao)"/>')
    s.append(text(cx + 60, cy + 66, t["inflow"], 12, OCHRE))
    s.append(text(cx - 175, cy - 232, t["core"], 12, OCHRE, weight="600"))
    s.append(text(cx - 175, cy - 200, t["shrink"], 11, MUTE))
    # кольцо с импульсами: две семьи (цвета) по обе стороны, парами σ=±1
    for sgn in (-1, 1):
        xr = cx + sgn * 52
        for j, yy in enumerate((cy - 150, cy - 95, cy - 40, cy + 15, cy + 70, cy + 125)):
            col = CYAN if j % 2 == 0 else OCHRE
            s.append(f'<ellipse cx="{xr}" cy="{yy}" rx="9" ry="14" fill="none" stroke="{col}" stroke-width="1.6"/>')
            s.append(f'<ellipse cx="{xr + sgn * 20}" cy="{yy + 12}" rx="9" ry="14" fill="none" stroke="{col}" stroke-width="1.6" stroke-dasharray="3 2"/>')
    s.append(text(cx + 118, cy - 130, t["ann"], 12, CYAN))
    # внешность: тонкие дуги вращения, затухающие с радиусом
    for k, xr in enumerate((cx + 200, cx + 235, cx + 270)):
        for sgn in (-1, 1):
            xx = cx + sgn * (xr - cx)
            s.append(f'<line x1="{xx}" y1="{cy - 120 + k * 15}" x2="{xx}" y2="{cy + 120 - k * 15}" stroke="{MUTE}" stroke-width="{1.6 - k * .4}" stroke-opacity="{.7 - k * .18}"/>')
    s.append(text(cx + 150, cy + 175, t["ext"], 12, MUTE))
    s.append(text(ox + 20, oy + 500, t["side"], 12, MUTE, italic=True))
    return "\n".join(s)


def top_view(t, ox, oy):
    """Вид сверху r–θ: спиральный приток, ядро, кольца импульсов, внешность."""
    s = []
    cx, cy = ox + 210, oy + 250
    # внешние окружности вращения
    for k, rr in enumerate((190, 165, 140)):
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="{MUTE}" stroke-width="{1.4 - k * .3}" stroke-opacity="{.55 - k * .12}"/>')
    # кольца импульсов (полные кольца вокруг оси): две семьи
    s.append(f'<circle cx="{cx}" cy="{cy}" r="88" fill="none" stroke="{CYAN}" stroke-width="2" stroke-dasharray="10 6"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="72" fill="none" stroke="{OCHRE}" stroke-width="2" stroke-dasharray="6 5"/>')
    s.append(text(cx + 96, cy - 84, t["pulse"], 11, CYAN))
    # спираль притока
    pts = []
    for i in range(0, 260):
        a = i / 260 * 2 * math.pi * 2.2
        r = 175 - i * (175 - 20) / 260
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    s.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{OCHRE}" stroke-width="2.2" marker-end="url(#ao)"/>')
    # ядро
    s.append(f'<circle cx="{cx}" cy="{cy}" r="14" fill="{OCHRE}" fill-opacity=".95"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="#fff"/>')
    s.append(text(cx + 22, cy - 150, t["inflow"], 12, OCHRE))
    s.append(text(cx - 195, cy + 215, t["ext"], 12, MUTE))
    s.append(text(ox + 20, oy + 500, t["top"], 12, MUTE, italic=True))
    return "\n".join(s)


def build(lang):
    t = L[lang]
    rtl = ' direction="rtl"' if lang == "ar" else ""
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="Georgia, \'Times New Roman\', serif"{rtl}>',
            arrow_defs(),
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="{PALE}" rx="10"/>',
            f'<rect x="10" y="10" width="{W - 20}" height="{H - 20}" fill="#fffdf9" rx="8"/>',
            f'<line x1="{W // 2}" y1="24" x2="{W // 2}" y2="{H - 24}" stroke="{PALE}" stroke-width="2"/>',
            side_view(t, 20, 10), top_view(t, W // 2 + 20, 10),
            '</svg>']
    return "\n".join(body)


if __name__ == "__main__":
    folder = pathlib.Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    for lang in L:
        (folder / f"fig-1.{lang}.svg").write_text(build(lang), encoding="utf-8")
    (folder / "fig-1.svg").write_text(build("en"), encoding="utf-8")
    print("рисунков:", len(L) + 1, "→", folder)
