#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает папку-комплект для того, кто будет презентовать. Всё в HTML, ни одного .md.

Владелец 13 августа: «никаких md, должно быть представлено в виде html, там же ссылка
на презентацию, причём тут лежат рядом; ссылки, если есть, должны быть в одном каталоге,
чтобы я свернул и отправил тому, кто будет презентовать».

Собирается папка `kit/`: туда копируются готовые HTML-страницы и рендерятся в HTML все
документы, которые до сих пор были markdown. Внутри только относительные ссылки, поэтому
папку можно заархивировать и отдать — она откроется на любой машине без интернета.

ПОЧЕМУ СВОЙ РЕНДЕРЕР, А НЕ БИБЛИОТЕКА. Нужен ровно тот набор разметки, который есть
в наших документах — заголовки, таблицы, списки, код, выделение, ссылки, цитаты,
разделители. Это сорок строк. Ставить зависимость ради сорока строк и потом объяснять
её тому, кто откроет папку через год, — плохой размен.

    python build_kit.py            собрать kit/
    python build_kit.py --check    проверить, что все ссылки внутри разрешаются
"""
import argparse
import html
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
KIT = ROOT / "kit"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Что копируем как есть и что рендерим. Имена в комплекте — латиницей: папка поедет
# архивом на чужую машину, а кириллица в именах файлов внутри zip ломается регулярно.
COPY = {
    "portal.html": "portal.html",
    "deck-en.html": "deck-en.html",
    "схема-решения.html": "diagram.html",
}
RENDER = [
    ("deck-en-notes.md", "deck-notes.html", "Speaker Notes & Technical Reference",
     "Сопроводительный текст к презентации: по слайду что говорить, техническая "
     "подкладка, ожидаемые вопросы"),
    ("ПЛАТФОРМА.md", "platform.html", "Платформа: архитектуры, отрасли, словарь",
     "Четыре архитектуры развития, применимость по отраслям, словарь понятий"),
    ("МАШИНА-ЗНАНИЙ.md", "machine.html", "Машина знаний: разворот цели",
     "Три механизма поиска, метод шахмат, контур обратной связи"),
    ("ДОСЬЕ-ВСТРЕЧА.md", "dossier.html", "Досье к встрече",
     "Спецификация дообучения, сценарии применения, трудные вопросы"),
    ("КОНЦЕПЦИЯ.md", "concept.html", "Концепция",
     "Первый концептуальный документ проекта"),
]

CSS = """
:root{--paper:#EEEFEC;--card:#FFF;--ink:#141A1E;--dim:#5B6870;--brand:#0B5A54;
  --brand-soft:#DCEAE6;--signal:#9E4418;--signal-soft:#F5E5DA;--rule:#D8D9D3;--shade:#E5E7E2}
@media (prefers-color-scheme:dark){:root{--paper:#12171A;--card:#171D21;--ink:#E4E7E5;
  --dim:#93A0A6;--brand:#5FBFAF;--brand-soft:#16302C;--signal:#D98254;
  --signal-soft:#2E1F18;--rule:#2A3237;--shade:#1B2226}}
:root[data-theme=dark]{--paper:#12171A;--card:#171D21;--ink:#E4E7E5;--dim:#93A0A6;
  --brand:#5FBFAF;--brand-soft:#16302C;--signal:#D98254;--signal-soft:#2E1F18;
  --rule:#2A3237;--shade:#1B2226}
:root[data-theme=light]{--paper:#EEEFEC;--card:#FFF;--ink:#141A1E;--dim:#5B6870;
  --brand:#0B5A54;--brand-soft:#DCEAE6;--signal:#9E4418;--signal-soft:#F5E5DA;
  --rule:#D8D9D3;--shade:#E5E7E2}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);padding:0 24px 80px;
  font:16.5px/1.62 Georgia,"Iowan Old Style","Times New Roman",serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto}
h1,h2,h3,h4,th,.back,.eyebrow{font-family:"Segoe UI",-apple-system,system-ui,sans-serif}
.back{display:inline-block;margin:26px 0 0;font-size:13.5px;color:var(--brand);
  text-decoration:none;letter-spacing:.02em}
.back:hover{text-decoration:underline}
.eyebrow{font-size:11.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--brand);
  font-weight:700;margin:30px 0 10px}
h1{font-size:38px;line-height:1.08;letter-spacing:-.02em;margin:0 0 14px;font-weight:750;
  text-wrap:balance}
h2{font-size:25px;line-height:1.2;letter-spacing:-.015em;margin:38px 0 12px;
  padding-top:20px;border-top:1px solid var(--rule);text-wrap:balance;font-weight:700}
h3{font-size:18.5px;margin:26px 0 9px;font-weight:700;letter-spacing:-.008em}
h4{font-size:15.5px;margin:20px 0 7px;color:var(--brand);font-weight:700}
p,li{max-width:72ch}
p{margin:0 0 13px}
ul,ol{padding-left:22px;margin:0 0 14px}
li{margin-bottom:7px}
a{color:var(--brand);text-underline-offset:2px}
strong,b{font-weight:700}
em{font-style:italic}
code{font-family:"Cascadia Mono",Consolas,ui-monospace,monospace;font-size:.87em;
  background:var(--shade);padding:1px 5px;border-radius:3px}
pre{background:var(--card);border:1px solid var(--rule);border-left:3px solid var(--brand);
  padding:14px 17px;overflow-x:auto;font-size:13.5px;line-height:1.5;margin:0 0 16px}
pre code{background:none;padding:0}
blockquote{margin:0 0 16px;padding:2px 0 2px 18px;border-left:3px solid var(--signal);
  color:var(--dim);font-style:italic}
hr{border:none;border-top:1px solid var(--rule);margin:30px 0}
.scroll{overflow-x:auto;margin:0 0 18px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--rule);
  font-size:14.5px;line-height:1.5;font-family:"Segoe UI",system-ui,sans-serif;min-width:540px}
th,td{padding:9px 14px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:top}
th{background:var(--shade);font-size:11px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--dim);font-weight:700}
tr:last-child td{border-bottom:none}
td b{color:var(--ink)}
header.doc{padding:34px 0 8px;border-bottom:1px solid var(--rule);margin-bottom:18px}
.sub{font-size:17px;color:var(--dim);line-height:1.5;max-width:64ch;margin:0}
footer{margin-top:46px;padding-top:18px;border-top:1px solid var(--rule);
  font-size:13px;color:var(--dim)}
@media (max-width:640px){h1{font-size:29px}h2{font-size:21px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""


def inline(t):
    """Строчная разметка. Порядок важен: код первым, иначе его содержимое разметится."""
    out, stash = [], []

    def keep(m):
        stash.append(m.group(1))
        return f"\x00{len(stash)-1}\x00"

    t = re.sub(r"`([^`]+)`", keep, t)
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"(?<!\w)(https?://[^\s<>()]+)", r'<a href="\1">\1</a>', t)
    t = re.sub(r"\x00(\d+)\x00",
               lambda m: "<code>" + html.escape(stash[int(m.group(1))], quote=False) + "</code>", t)
    return t


def render(md):
    """Markdown → HTML. Ровно то, что встречается в наших документах."""
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        # код блоком
        if ln.startswith("```"):
            j = i + 1
            buf = []
            while j < n and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            i = j + 1
            continue
        # таблица: строка с | и следующая из дефисов
        if "|" in ln and i + 1 < n and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            j = i + 2
            rows = []
            while j < n and "|" in lines[j] and lines[j].strip():
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            t = ['<div class="scroll"><table><thead><tr>']
            t += [f"<th>{inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            i = j
            continue
        # заголовки
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        # разделитель
        if re.match(r"^\s*(---+|\*\*\*+)\s*$", ln):
            out.append("<hr>")
            i += 1
            continue
        # цитата
        if ln.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append("<blockquote>" + inline(" ".join(buf)) + "</blockquote>")
            continue
        # списки
        m = re.match(r"^\s*([-*·]|\d+\.)\s+(.*)$", ln)
        if m:
            ordered = bool(re.match(r"^\s*\d+\.", ln))
            tag = "ol" if ordered else "ul"
            items = []
            while i < n:
                mm = re.match(r"^\s*(?:[-*·]|\d+\.)\s+(.*)$", lines[i])
                if mm:
                    items.append(mm.group(1))
                    i += 1
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        # пустая
        if not ln.strip():
            i += 1
            continue
        # абзац
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|```|>|\s*(?:[-*·]|\d+\.)\s|\s*(?:---+|\*\*\*+)\s*$)", lines[i]) \
                and not ("|" in lines[i] and i + 1 < n and
                         re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1])):
            buf.append(lines[i])
            i += 1
        if buf:
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<a class="back" href="index.html">← ко всем материалам</a>
<header class="doc">
  <p class="eyebrow">Машина открытий · материалы</p>
  <h1>{title}</h1>
  <p class="sub">{sub}</p>
</header>
{body}
<footer>
  <p><a class="back" href="index.html" style="margin:0">← ко всем материалам</a></p>
  <p>Машина открытий · bridge42worlds · август 2026</p>
</footer>
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not args.check:
        if KIT.exists():
            shutil.rmtree(KIT)
        KIT.mkdir()
        # Внутри комплекта не должно остаться ни одного .md: портал ссылается на них
        # в разделе «файлы», и на чужой машине такие ссылки ведут в пустоту.
        # Заменяем на отрисованные страницы прямо при копировании.
        MDMAP = {"deck-en-notes.md": "deck-notes.html", "ПЛАТФОРМА.md": "platform.html",
                 "МАШИНА-ЗНАНИЙ.md": "machine.html", "ДОСЬЕ-ВСТРЕЧА.md": "dossier.html",
                 "КОНЦЕПЦИЯ.md": "concept.html", "схема-решения.html": "diagram.html"}
        for src, dst in COPY.items():
            body = (ROOT / src).read_text(encoding="utf-8")
            for a, b in MDMAP.items():
                body = body.replace(f'href="{a}"', f'href="{b}"')
                body = body.replace(f"<code>{a}</code>", f"<code>{b}</code>")
            (KIT / dst).write_text(body, encoding="utf-8")
            left = [a for a in MDMAP if a.endswith(".md") and a in body]
            print(f"  скопировано  {src}  →  kit/{dst}"
                  + (f"   ⚠ упоминания .md: {left}" if left else ""))
        for src, dst, title, sub in RENDER:
            md = (ROOT / src).read_text(encoding="utf-8")
            (KIT / dst).write_text(
                PAGE.format(title=html.escape(title), sub=html.escape(sub),
                            css=CSS, body=render(md)), encoding="utf-8")
            print(f"  отрисовано   {src}  →  kit/{dst}  ({len(md):,} знаков)")
        shutil.copy2(ROOT / "kit-index.html", KIT / "index.html")
        print("  скопировано  kit-index.html  →  kit/index.html")

    # проверка: все ли ссылки внутри папки разрешаются
    import urllib.parse
    bad, tot = [], 0
    for f in sorted(KIT.glob("*.html")):
        s = f.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#][^"]*)"', s):
            if href.startswith(("http", "mailto")):
                continue
            tot += 1
            target = KIT / urllib.parse.unquote(href.split("#")[0])
            if not target.exists():
                bad.append(f"{f.name} → {href}")
    print(f"\nвнутренних ссылок: {tot} · битых: {len(bad)}")
    for b in bad:
        print("  !!", b)
    files = sorted(KIT.glob("*"))
    size = sum(x.stat().st_size for x in files)
    print(f"файлов в комплекте: {len(files)} · {size/1e6:.2f} МБ")
    print(f"папка: {KIT}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
