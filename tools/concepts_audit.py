# -*- coding: utf-8 -*-
"""Аудит реестра понятий → concepts-audit.html (шаг A2 плана, смотр владельца).

Владелец 27.08: «всё привели к балансу? проверили внутренние связи? насытили
математикой, законами? по всему прошлись?» — отчёт отвечает цифрами:

  · классы и баланс (где мало: математика, законы, константы)
  · сироты (0 статей) и малоопорные
  · изолированные в графе и без соседей
  · кандидаты на слияние (карточки ≥0.90 и пулы пересекаются)
  · омонимы (карточки ≥0.90, пулы не пересекаются — НЕ сливать)
  · покрытие статей разметкой
  · рекомендации к шагу A4 (целевое насыщение)

Локально и бесплатно; читает live, матрицу карточек и снимок графа.

    python tools/concepts_audit.py
"""
import html as H
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
OUT = ROOT / "concepts-audit.html"


def main():
    import numpy as np
    live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
    C = live["concepts"]
    # Снимка графа может не быть (первый запуск, свежая копия) — аудит обязан
    # выжить: секции связности тогда просто пустые (поймано сквозным прогоном
    # в песочнице 27.08, шаг 10 падал FileNotFoundError).
    gp = ROOT / "data/concepts-graph.json"
    graph = (json.loads(gp.read_text(encoding="utf-8")) if gp.exists()
             else {"nodes": [], "edges": [], "groups": []})
    ids = (ML / "data/concept-cards.ids").read_text(encoding="utf-8").split()
    V = np.fromfile(ML / "data/concept-cards.f16", dtype=np.float16) \
        .reshape(len(ids), -1).astype(np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9

    def name(cid):
        return (C.get(cid, {}).get("names") or {}).get("ru") or cid.replace("_", " ")

    # ── классы ──
    kinds = Counter(v.get("kind", "?") for v in C.values())
    LOW = {"math": 200, "law": 200, "constant": 60, "theorem": 80,
           "principle": 60, "statistics": 150}

    # ── опора ──
    orphans = sorted([c for c, v in C.items() if not v.get("articles")],
                     key=lambda c: C[c].get("kind", ""))
    n_orph = len(orphans)

    # ── связность графа (снимок свежий, понятия без формул) ──
    idx_g = {nd["id"]: i for i, nd in enumerate(graph["nodes"])}
    adjc = defaultdict(int)
    # ребро может нести четвёртый элемент — тип связи по знанию
    for _e in graph["edges"]:
        a, b, w = _e[0], _e[1], _e[2]
        adjc[a] += 1
        adjc[b] += 1
    isolated = [nd["id"] for i, nd in enumerate(graph["nodes"])
                if nd["kind"] != "formula" and not adjc[i] and nd["n"] > 0]
    # Связи по знанию — третий источник (tools/link_weaving.py), и он живёт своим
    # файлом, а не полем related. Без него аудит показывает связность хуже, чем
    # она есть: у понятия может не быть ни одного соседа «по весу» и при этом
    # стоять сказанное отношение — «входит в», «описывает». Такое понятие не
    # одиноко, и записывать его в список на дорост — значит гнать модель второй
    # раз за тем, что уже найдено.
    kn_p = ROOT / "data" / "concept-links-knowledge.json"
    try:
        kn = json.loads(kn_p.read_text(encoding="utf-8")) if kn_p.exists() else {}
    except Exception:
        kn = {}
    kn_n = sum(len(v) for v in kn.values())

    # ── имена-двойники ──
    # Проверка по векторной близости карточек их не ловит: у двух понятий с одним
    # именем карточки бывают разные, а читателю видно ровно имя. На странице LIGO
    # это выглядело как заикание — «измеряет → эхо гравитационных волн» дважды, и
    # ссылки вели на разные страницы с одинаковым заголовком.
    by_name = defaultdict(list)
    for c, v in C.items():
        nm_ru = (v.get("names") or {}).get("ru")
        if nm_ru:
            by_name[nm_ru].append(c)
    twins = sorted(((nm, ids) for nm, ids in by_name.items() if len(ids) > 1),
                   key=lambda t: -len(t[1]))
    no_related = [c for c, v in C.items()
                  if not v.get("related") and v.get("articles") and c not in kn]

    # ── слияния и омонимы: пары карточек ≥0.90 ──
    pool = {c: set(v.get("articles") or []) for c, v in C.items()}
    S = V @ V.T
    np.fill_diagonal(S, -1)
    ii, jj = np.where(S >= 0.90)
    merge, homon = [], []
    seen = set()
    for i, j in zip(ii, jj):
        if i > j:
            continue
        a, b = ids[i], ids[j]
        if (a, b) in seen:
            continue
        seen.add((a, b))
        A, B = pool.get(a, set()), pool.get(b, set())
        jac = len(A & B) / max(1, len(A | B))
        row = (a, b, float(S[i, j]), jac, len(A), len(B))
        if jac >= 0.30:
            merge.append(row)
        elif jac < 0.05:
            homon.append(row)
    merge.sort(key=lambda r: -r[2])
    homon.sort(key=lambda r: -r[2])

    # ── степени связности: рёбра к узлам (владелец: «3–5 к одному в целом») ──
    deg_c = Counter()
    concept_idx = [i for i, nd in enumerate(graph["nodes"]) if nd["kind"] != "formula"]
    for i in concept_idx:
        deg_c[min(adjc[i], 13)] += 1
    n_cn = len(concept_idx)
    n_ce = sum(1 for a, b, w in ((e[0], e[1], e[2]) for e in graph["edges"])
               if graph["nodes"][a]["kind"] != "formula"
               and graph["nodes"][b]["kind"] != "formula")
    ratio = n_ce / max(1, n_cn)
    zero_link = sum(1 for i in concept_idx if not adjc[i])

    # ── внутригрупповая целостность (group_integrity --audit) ──
    gi_p = ROOT / "data" / "group-integrity.json"
    gi = json.loads(gi_p.read_text(encoding="utf-8")) if gi_p.exists() else {}

    # ── покрытие статей ──
    per_art = Counter()
    for c, v in C.items():
        for a in v.get("articles") or []:
            per_art[a] += 1
    n_arts = len(per_art)
    depth = Counter()
    for a, n in per_art.items():
        depth["<5"] += n < 5
        depth["5-9"] += 5 <= n <= 9
        depth["10-19"] += 10 <= n <= 19
        depth["20+"] += n >= 20

    # ── HTML ──
    def sec(title, body):
        return f"<h2>{title}</h2>{body}"

    def bar_table(counter, low=None):
        mx = max(counter.values()) or 1
        rows = []
        for k, n in counter.most_common():
            warn = low and n < low.get(k, 0)
            note = (f" <span class='warn'>мало — цель ~{low[k]}</span>"
                    if warn else "")
            rows.append(
                f"<tr><td>{k}{note}</td><td class='bar'><i style='width:"
                f"{max(2, n * 100 // mx)}%'></i></td>"
                f"<td class='num'>{n}</td></tr>")
        return "<table>" + "".join(rows) + "</table>"

    def clist(items, cap=40):
        chips = " ".join(
            f"<a href='/lang/ru/concepts/{H.escape(c)}.html'>{H.escape(name(c))}</a>"
            for c in items[:cap])
        more = f" <span class='dim'>… +{len(items) - cap}</span>" if len(items) > cap else ""
        return f"<div class='chips'>{chips}{more}</div>"

    def pair_rows(rows, cap=30):
        out = []
        for a, b, cos, jac, na, nb in rows[:cap]:
            out.append(
                f"<tr><td>{H.escape(name(a))} <span class='dim'>({na} ст.)</span></td>"
                f"<td>{H.escape(name(b))} <span class='dim'>({nb} ст.)</span></td>"
                f"<td class='num'>{cos:.3f}</td><td class='num'>{jac:.2f}</td></tr>")
        more = (f"<tr><td colspan=4 class='dim'>… ещё {len(rows) - cap} пар</td></tr>"
                if len(rows) > cap else "")
        return ("<table><tr><th>понятие А</th><th>понятие Б</th>"
                "<th>карточки</th><th>пулы</th></tr>" + "".join(out) + more + "</table>")

    kind_html = bar_table(kinds, LOW)
    body = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Аудит реестра понятий — bridge42worlds</title>
<link rel="stylesheet" href="/css/style.css">
<style>
body {{ max-width: 860px; padding-bottom: 70px; }}
h1 {{ font-size: 24px; margin: 26px 0 4px; }}
h2 {{ font-size: 16px; margin: 30px 0 8px; }}
.sub {{ color: var(--soft); font-size: 13px; margin-bottom: 8px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
/* на телефоне таблицы прокручиваются сами, а не растягивают страницу */
@media (max-width: 720px) {{ table {{ display: block; overflow-x: auto; }} }}
td, th {{ padding: 3px 10px 3px 0; border-bottom: 1px solid var(--hairline);
  text-align: left; }}
th {{ font-family: var(--mono); font-size: 10.5px; color: var(--soft);
  text-transform: uppercase; }}
.bar {{ width: 45%; }}
.bar i {{ display: block; height: 11px; background: var(--cyan); opacity: .45;
  border-radius: 3px; }}
.num {{ font-family: var(--mono); text-align: right; }}
.warn {{ color: #b3541b; font-size: 11px; font-family: var(--mono); }}
.dim {{ color: var(--soft); font-size: 11.5px; }}
.chips a {{ display: inline-block; margin: 2px 4px 2px 0; padding: 2px 9px;
  border: 1px solid var(--hairline); border-radius: 999px; font-size: 11.5px;
  color: var(--muted); text-decoration: none; }}
.chips a:hover {{ color: var(--link); border-color: var(--link); }}
.cards {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0; }}
.card {{ flex: 1; min-width: 120px; background: var(--surface);
  border: 1px solid var(--hairline); border-radius: var(--radius-sm);
  padding: 10px 13px; }}
.card b {{ font-size: 21px; display: block; }}
.card span {{ color: var(--soft); font-size: 11.5px; }}
.reco {{ background: var(--surface); border: 1px dashed var(--hairline);
  border-radius: var(--radius-sm); padding: 12px 16px; font-size: 13px;
  line-height: 1.6; }}
</style></head><body>
<h1>Аудит реестра понятий</h1>
<div class="sub">Шаг A2 плана · снимок после пересчёта связности ·
{len(C)} понятий · 642 формулы · <a href="/lang/ru/concepts/graph.html">граф</a> ·
<a href="/concepts-review.html">смотровая</a></div>

<div class="cards">
<div class="card"><b>{len(C)}</b><span>понятий в реестре</span></div>
<div class="card"><b>{sum(1 for v in C.values() if v.get('supers'))}</b><span>в группах (50 именованных)</span></div>
<div class="card"><b>{sum(1 for v in C.values() if v.get('related'))}</b><span>с соседями по весу</span></div>
<div class="card"><b>{kn_n:,}</b><span>связей по знанию у {len(kn)}</span></div>
<div class="card"><b>{len(graph['edges']):,}</b><span>рёбер в графе</span></div>
<div class="card"><b>{n_arts}</b><span>статей с разметкой</span></div>
</div>

{sec("Классы и баланс", kind_html)}
{sec(f"Сироты — {n_orph} понятий без статей",
     "<div class='sub'>Родились с опорой, но переразметка не подтвердила ни одной статьи. "
     "Кандидаты на чистку или на пересчёт порога.</div>" + clist(orphans))}
{sec(f"Без соседей — {len(no_related)} (при живых статьях)",
     "<div class='sub'>Связи с весом не набрались; вырастут при пороге ниже или это "
     "узкие темы.</div>" + clist(no_related))}
{sec(f"Изолированные в графе — {len(isolated)}",
     "<div class='sub'>Ни одного ребра с ≥2 общими статьями.</div>" + clist(isolated))}
{sec(f"Имена-двойники — {len(twins)}",
     ("<div class='sub'>Разные понятия с одним русским именем. Векторная проверка их "
      "не видит — карточки могут быть разными, а читателю видно имя: два одинаковых "
      "заголовка в облаке и повтор в связях. Решать по одному: слить, переименовать "
      "или оставить (бывают настоящие омонимы).</div><table>"
      + "".join(f"<tr><td>{H.escape(nm)}</td><td>{H.escape(', '.join(ids))}</td></tr>"
                for nm, ids in twins[:60]) + "</table>"))}
{sec(f"Кандидаты на слияние — {len(merge)} пар",
     "<div class='sub'>Карточки ≥0.90 И пулы статей пересекаются ≥0.30 — почти наверняка "
     "дубль; сливать с алиасом.</div>" + pair_rows(merge))}
{sec(f"Омонимы и «всегда вместе» — {len(homon)} пар",
     "<div class='sub'>Карточки ≥0.90, но пулы НЕ пересекаются — это РАЗНЫЕ понятия, "
     "не сливать.</div>" + pair_rows(homon, 12))}
{sec(f"Связность: {n_ce:,} рёбер на {n_cn:,} понятий — {ratio:.1f} : 1",
     f"<div class='sub'>Пропорция в отображаемом графе (топ-12 рёбер на узел, "
     f"≥2 общих статей); полная ткань связей плотнее. Понятий с нулём связей "
     f"в графе: <b>{zero_link}</b> — после векторного запасного слоя цель 0.</div>"
     + bar_table(Counter({('свыше 12' if k == 13 else str(k)) + ' рёбер': v
                          for k, v in deg_c.items()})))}
{sec(f"Внутригрупповая целостность — {sum(1 for g in gi.values() if g.get('skeleton_holes'))} групп с дырами скелета",
     ("<div class='sub'>Скелет области: law · math · statistics · method · constant. "
      "Структурные сироты держат группы — их не трогаем.</div>"
      + "<table><tr><th>группа</th><th>понятий</th><th>дыры скелета</th>"
        "<th>связность внутри</th><th>структурные сироты</th></tr>"
      + "".join(
          f"<tr><td>{H.escape(g['label'][:42])}</td><td class='num'>{g['n']}</td>"
          f"<td>{', '.join(g['skeleton_holes']) or '—'}</td>"
          f"<td class='num'>{int(g['connected_share'] * 100)}%</td>"
          f"<td class='num'>{len(g['structural_orphans'])}</td></tr>"
          for g in sorted(gi.values(), key=lambda g: -len(g['skeleton_holes']))[:20])
      + "</table>") if gi else
     "<div class='sub'>отчёт групп ещё не собран (group_integrity --audit)</div>")}
{sec("Покрытие статей разметкой",
     bar_table(Counter({k: depth[k] for k in ('<5', '5-9', '10-19', '20+')})))}

<h2>Рекомендации к шагу A4</h2>
<div class="reco">
1. <b>Донасыщение классов</b>: math ({kinds.get('math', 0)}), law ({kinds.get('law', 0)}),
constant ({kinds.get('constant', 0)}) — целевая добыча промптом «выдай законы/математику/константы
из этих статей» по разделам с формулами; через то же сито рождения. Оценка: +200–400 понятий, ~$1–2.<br>
2. <b>Слияния</b>: {len(merge)} пар выше — дистилляция порогом по паре, проигравший в алиасы.<br>
3. <b>Сироты</b>: {n_orph} — снять с витрины до подтверждения статьями или удалить мусорные.<br>
4. <b>Статьи с бедной разметкой</b> (&lt;5 понятий): {depth['<5']} — добор вторым проходом добычи.
</div>
</body></html>"""
    OUT.write_text(body, encoding="utf-8")
    print(f"✅ аудит → {OUT.name}")
    print(f"   классы-дыры: math {kinds.get('math', 0)}, law {kinds.get('law', 0)}, "
          f"constant {kinds.get('constant', 0)}")
    print(f"   сироты {n_orph} · без соседей {len(no_related)} · изолированные {len(isolated)}")
    print(f"   слияния {len(merge)} пар · омонимы {len(homon)} пар · "
          f"имена-двойники {len(twins)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
