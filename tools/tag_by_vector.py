"""Теги и законы ПО СМЫСЛУ, а не по списку в промпте.

Владелец 2026-08-04: «давай уходить от передачи облака тегов в промпт — у нас теперь есть
вектор, можно загнать теги, законы и их описания в вектор и индексировать ими напрямую,
перестроить логику привязки. И главный тег, кажется, можно получить из вектора».

Зачем — замер, а не ощущение. В архиве 363 тега, и:
  · 179 из них НЕ проставлены ни одной статье — половина словаря мертва;
  · на десять самых частых приходится 45% всех проставлений;
  · медицинских тегов в ходу практически нет.
Причина в механизме: мы отдаём модели список из 363 названий и просим выбрать. Модель
берёт знакомое и частое (спектроскопия, энтропия, чёрные дыры), редкое и точное не берёт
никогда — «безопаснее» назвать общее. Так теряется структура: была астрофизика — стала
астрофизика, а фрактал, перколяция и фазовый переход стоят пустые.

Здесь другое: у каждого тега есть человеческое описание (name + mini + практическое
применение), у каждой статьи — свой текст. Сравниваем СМЫСЛЫ и берём ближайшие. Привязка
становится воспроизводимой (один и тот же текст всегда получит те же теги) и одинаковой
для всех языков.

ЧЕМ СРАВНИВАЕМ (замена 2026-08-10, ML). Первая версия мерила совпадение СЛОВ (TF-IDF) —
это была заплатка, и её граница честно названа архитектором: на коротких текстах она
дала статье про акселерометры тег «большие языковые модели», потому что там и там
встретились «модель», «данные», «измерение». Теперь по умолчанию сравниваются СМЫСЛЫ:
bge-m3 через DeepInfra, 1024 числа на текст, та же модель, что и в поиске по сайту.
Прежний движок никуда не делся и включается флагом — на нём удобно видеть, что изменилось.

Что дала замена на корпусе в 3251 статью:
  · у статьи про МРТ и нейросети было `spectroscopy · dark_matter, standard_model`,
    стало `deep_learning_in_medical_imaging · brain_cancer_detection`;
  · законы: 66% статей получали «лучшее из плохого» → 39% получают закон, остальным пусто;
  · ожили 150 мёртвых тегов из 157.
Цена: разметка перестала быть бесплатной. Весь корпус — около $0,13, повторный прогон
бесплатен (векторы лежат в data/tagvec-cache.jsonl по отпечатку текста).

    python tools/tag_by_vector.py --check          сверить с нынешними тегами, ничего не менять
    python tools/tag_by_vector.py --show 2607.123  что предложит для одной статьи
    python tools/tag_by_vector.py --check --engine tfidf   как было до замены
    python tools/tag_by_vector.py --apply          записать в data.json (поле tags_vec)

ВАЖНО: --apply пишет в ОТДЕЛЬНОЕ поле tags_vec, не трогая нынешние теги. Сначала смотрим,
что получилось, потом решаем, переключать ли на них ленту.
"""
import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
# .env лежит в главной папке проекта: в git его нет, в рабочем дереве ML — тоже.
MAIN_REPO = Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
MARK = re.compile(r"\[(?:tag|scientist|law):[^\]]+\]|\[/(?:tag|scientist|law)\]")
# Сами статьи и справочники (`lang/**`) в git не лежат — они пересобираемые, см. .gitignore.
# В рабочем дереве ML их поэтому нет вовсе. Данные берём из главной папки, код — отсюда:
# иначе инструмент запускается только из одной папки на машине, и любая ветка слепа.
SRC = ROOT if (ROOT / "lang/ru/data/tags.json").exists() else MAIN_REPO
MAX_CHARS = 6000

# Пороги отсечки, свои для каждого движка — это разные шкалы, а не разная строгость.
# У TF-IDF совпадение слов даёт 0,02–0,26; у эмбеддингов любые два научных текста уже
# похожи, и шкала живёт в 0,50–0,88. Одного числа на оба движка быть не может.
#
# Порог закона 0,62 — замер 2026-08-10, не подбор на глаз. Взяли 189 статей, у которых
# лучший тег заведомо не про физику (нейросети, белки, алгоритмы), и 3062 остальных.
# Сколько статей «без закона» всё же получают закон:
#     порог 0,55 → 51%   0,58 → 25%   0,60 → 15%   0,62 → 10%   0,65 → 4%
# При 0,62 закон остаётся у 39% корпуса, а ложных срабатываний вчетверо меньше, чем
# при 0,58. Дальше 0,65 выигрыш в точности мелкий, а теряется треть настоящих привязок.
#
# Порог тега 0,54 — низкий намеренно. Отбор тегов держит не он, а поправка на хабность
# (--hub, см. hubness()): при 0,58 против 0,54 разница ровно 0,06 тега на статью, зато
# 0,58 срезает точные попадания на волосок — `natural_language_processing` получил 0,577
# в статье про многоязычные модели, будучи одним из самых характерных её тегов (+0,158
# сверх обычного). Две планки подряд с одной работой — это не строгость, а лотерея.
DEFAULTS = {
    "tfidf": {"tag": 0.045, "law": 0.055},
    "vec": {"tag": 0.54, "law": 0.62},
}



# Пишем ФАЙЛ ТОЛЬКО ЕСЛИ СОДЕРЖИМОЕ ИЗМЕНИЛОСЬ.
#
# Найдено 15 августа, когда Cloudflare упёрся в предел бесплатного тарифа: 103 574
# запроса в сутки при 12 живых читателях. Причина оказалась не в ботах как таковых.
# Этот прогон переписывал ВСЕ 5 245 data.json каждую ночь — даже те, где ни один байт
# не поменялся. Дата правки файла обновлялась, карта сайта честно сообщала поисковикам
# «изменились все 5 168 страниц», и роботы каждый день переобходили весь сайт заново.
# Мы сами себе делали трафик и сами за него собирались платить.
#
# Сравнение содержимого стоит одну сериализацию на файл. Оно чинит сразу три вещи:
# честный lastmod (роботы ходят за изменившимся), меньшую дельту выкладки и
# правдивое «когда правили статью» в самом архиве.
def _save_if_changed(path, data, indent=1):
    new = json.dumps(data, ensure_ascii=False, indent=indent)
    try:
        if path.read_text(encoding="utf-8") == new:
            return False
    except Exception:
        pass
    path.write_text(new, encoding="utf-8")
    return True


def registry():
    """Единый реестр понятий — источник правды с 18 августа.

    Тексты понятий он не хранит и не должен: описание пишется на языке, а реестр
    один на все языки. Поэтому текст по-прежнему берётся из витрины (tags.json,
    laws.json), а реестр решает, КАКИЕ понятия существуют и какого они вида.

    Зачем это здесь. Разметка ставила идентификаторы из витрины, а витрина
    генерируется и отстаёт: понятие, склеенное в реестре, в ней ещё двоится.
    Без сверки с реестром разметка продолжала бы ставить исчезнувший идентификатор,
    и починка справочника откатывалась бы следующим же ночным прогоном.
    """
    import json as _json
    for base in (ROOT, MAIN_REPO):
        p = base / "data" / "concepts.json"
        if p.exists():
            return _json.loads(p.read_text(encoding="utf-8")).get("concepts", {})
    return {}


def tag_texts():
    """Тег как ТЕКСТ: название + простое объяснение + практическое применение.
    Голого названия мало — «энтропия» и «фрактал» одним словом ничем не отличаются для
    сравнения смыслов. Описание даёт тегу собственное смысловое поле."""
    d = json.loads((SRC / "lang/ru/data/tags.json").read_text(encoding="utf-8"))
    reg = registry()
    dropped = 0
    ids, texts = [], []
    for tid, v in d.items():
        if not isinstance(v, dict):
            continue
        parts = [v.get("name", ""), v.get("mini", ""), v.get("practical_application", ""),
                 v.get("description_popular", ""), v.get("description_simple", "")]
        t = " ".join(p for p in parts if p)
        if len(t) < 40:
            continue
        # Нет в реестре — значит понятие склеено или удалено. Ставить его нельзя.
        if reg and tid not in reg:
            dropped += 1
            continue
        ids.append(tid)
        texts.append(t)
    if dropped:
        print(f"  из витрины отброшено {dropped} понятий, которых нет в реестре")
    return ids, texts, d


def law_texts():
    """Закон как ТЕКСТ: имя, формулировка, объяснение, где встречается.

    Владелец 2026-08-09: «мы даже напрямую размечать и теги, и законы для статьи, а не
    тянуть законы из тегов, так?». Да — и это заметно точнее. Сейчас закон приклеивается
    к статье, если у них совпал ХОТЯ БЫ ОДИН тег: у закона излучения Планка стоит тег
    «спектроскопия», и он цепляется к любой статье, где спектроскопия хоть упомянута.
    Смысловое сравнение так не ошибается: у закона есть собственное описание, у статьи —
    свой текст, и меряются они напрямую, без посредника-тега.
    """
    d = json.loads((SRC / "lang/ru/data/laws.json").read_text(encoding="utf-8"))
    reg = registry()
    dropped = 0
    ids, texts = [], []
    for lid, v in d.items():
        if not isinstance(v, dict):
            continue
        parts = [v.get("name", ""), v.get("statement", ""), v.get("mini", ""),
                 v.get("description_popular", ""), v.get("description_simple", ""),
                 v.get("where_met", ""), v.get("practical_application", "")]
        s = " ".join(x for x in parts if x)
        if len(s) < 40:
            continue
        if reg and lid not in reg:
            dropped += 1
            continue
        ids.append(lid)
        texts.append(s)
    return ids, texts, d


def article_texts():
    ids, texts, meta = [], [], {}
    for p in sorted((SRC / "lang/ru/archive").glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        v = (d.get("popular", {}) or {}).get("ru") or (d.get("simple", {}) or {}).get("ru") or {}
        if not isinstance(v, dict) or not v.get("title"):
            continue
        t = MARK.sub(" ", " ".join(str(v.get(k, "")) for k in ("title", "description", "text")))
        if len(t) < 200:
            continue
        ids.append(p.parent.name)
        texts.append(t)
        meta[p.parent.name] = {"title": v["title"], "tags": v.get("extra_tags", []),
                               "main": v.get("main_tag", ""), "path": p}
    return ids, texts, meta


def matrices(texts_by_kind, engine, all_texts):
    """Тексты → матрицы, которыми можно мерить близость. Два движка, один интерфейс.

    `tfidf` — заплатка архитектора: совпадение слов. `vec` — смысл: bge-m3, 1024 числа
    на текст. Разница не косметическая. TF-IDF считает похожими тексты с общими словами,
    поэтому на коротком описании он дал статье про акселерометры тег «большие языковые
    модели»: там и там встретилось «модель», «данные», «измерение». Эмбеддинг сравнивает
    смыслы и такой ошибки не делает — но стоит денег и требует сети.

    Возвращает матрицы, УЖЕ приведённые к единичной длине, поэтому скалярное произведение
    строк — это косинус. Один способ измерения на оба движка, чтобы дальше по коду не
    приходилось помнить, чем именно посчитано.
    """
    import numpy as np
    if engine == "tfidf":
        from sklearn.feature_extraction.text import TfidfVectorizer
        # Общее словарное пространство: теги и статьи должны меряться одной линейкой,
        # поэтому обучаем на объединении, а не на каждом корпусе отдельно.
        vec = TfidfVectorizer(min_df=2, max_df=0.5, sublinear_tf=True,
                              token_pattern=r"(?u)\b\w[\w-]{2,}\b")
        vec.fit(all_texts)
        # TF-IDF у sklearn уже нормирован по строкам, приводить нечего.
        return [vec.transform(t) for t in texts_by_kind]

    sys.path.insert(0, str(ROOT))
    from embeddings_build import embed_cached, load_env
    key = load_env(MAIN_REPO).get("DEEPINFRA_API_KEY", "")
    if not key:
        sys.exit("нет DEEPINFRA_API_KEY в .env главной папки — эмбеддинги не посчитать")
    (ROOT / "data").mkdir(exist_ok=True)
    out = []
    for texts, label in zip(texts_by_kind, ("теги", "законы", "статьи")):
        # Обрезка на входе: у модели предел контекста, а у нас попадаются статьи
        # на десятки тысяч знаков. Смысл текста задаётся началом, хвост его не меняет.
        cut = [" ".join(t.split())[:MAX_CHARS] for t in texts]
        m = np.asarray(embed_cached(cut, key, ROOT / "data/tagvec-cache.jsonl", label),
                       dtype=np.float32)
        m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
        out.append(m)
    return out


def sim_rows(A, T, lo, hi):
    """Близость строк A[lo:hi] ко всем строкам T — одинаково для обоих движков."""
    import numpy as np
    if hasattr(A, "toarray"):
        from sklearn.metrics.pairwise import linear_kernel
        return linear_kernel(A[lo:hi], T)
    return np.asarray(A[lo:hi] @ T.T)


def pick(row, top, thr, hub_thr, hub):
    """Кого оставить из кандидатов одной статьи. Одно место на все решения об отборе.

    Первый кандидат берётся ВСЕГДА, даже если не дотянул до порога: статья без единого
    тега выпадает из ленты и из всех связей, такой цены у строгости нет (на пороге 0,58
    без этого правила 120 статей из 3251 остались бы пустыми). Остальные обязаны пройти
    обе планки — обычную и поправку на хабность, см. hubness().
    """
    import numpy as np
    order = np.argsort(row)[::-1]
    out = [int(order[0])]
    for j in order[1:top]:
        if row[j] < thr:
            continue
        if hub is not None and row[j] - hub[j] < hub_thr:
            continue
        out.append(int(j))
    return out


def hubness(A, T, engine):
    """Насколько каждый тег близок ВООБЩЕ КО ВСЕМУ. Лечим болезнь многомерных пространств.

    В пространстве на 1024 измерения заводятся «хабы» — точки, оказывающиеся соседями
    чуть ли не всех остальных. Замер 2026-08-10: `instanton`, `squeezed_state` и
    `quintessence` имеют среднюю близость к корпусу 0,546–0,543 против медианных 0,475 —
    и лезли в пятые-шестые теги статей, где их нет и близко (квантовый эффект Мпембы,
    статья про заряд). Это не смысл, это геометрия.

    Что с этим делать — тоже замер, а не вкус. Полное вычитание хабности (S − hub) чинит
    хвост, но ломает голову: главным тегом статьи про гравитационные волны становятся
    `antennas`, у статьи про чёрные дыры — `critical_point`. И разделение «есть закон /
    нет закона» падает с AUC 0,787 до 0,676. Причина в том, что `black_hole` —
    хаб ЗАКОННЫЙ: три четверти корпуса про астрофизику, и центральность здесь правда.
    Поэтому порядок берём по сырому косинусу, а поправка работает только вторым фильтром
    на хвост: тег со второго места обязан быть ближе к статье не только вообще, но и
    СВЕРХ своей обычной близости. Хабы после этого срезаны вчетверо (263 → 37 статей
    у `instanton`), главные теги остались на месте.
    """
    import numpy as np
    if engine != "vec":
        return None
    return np.asarray(A @ T.T).mean(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--engine", choices=("vec", "tfidf"), default="vec",
                    help="vec — эмбеддинги bge-m3 (по умолчанию); tfidf — прежняя заплатка")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--min", type=float, default=None)
    # Порог для законов ВЫШЕ, чем для тегов, и это не придирка.
    #
    # Тег найдётся у любой статьи: словарь тегов покрывает всё, чем мы занимаемся.
    # А физического закона для статьи про языковые модели просто НЕ СУЩЕСТВУЕТ — и вектор
    # это честно показывает числами 0.026–0.033 против 0.124 у настоящего попадания.
    # Без порога он всё равно выдаст лучшее из плохого: преобразования Лоренца и принцип
    # Паули в статье про трансформеры (проверено 2026-08-09). Пустая колонка честнее.
    ap.add_argument("--min-law", type=float, default=None)
    ap.add_argument("--top-law", type=int, default=4)
    # Вторая планка для хвоста — поправка на хабность, см. hubness(). Только для vec:
    # у TF-IDF своей болезни хабов нет, а шкала другая, и 0.12 там отрезало бы всё.
    ap.add_argument("--hub", type=float, default=0.12)
    args = ap.parse_args()

    # Пороги у движков разные, и это не настройка, а разные шкалы. У TF-IDF совпадение
    # слов даёт числа 0,02–0,13; у эмбеддингов любые два научных текста уже похожи, и
    # шкала живёт заметно выше. Общего числа тут быть не может, поэтому по умолчанию
    # берётся порог своего движка (замер — ниже, в комментарии у DEFAULTS).
    if args.min is None:
        args.min = DEFAULTS[args.engine]["tag"]
    if args.min_law is None:
        args.min_law = DEFAULTS[args.engine]["law"]

    import numpy as np

    tids, ttexts, tdict = tag_texts()
    lids, ltexts, ldict = law_texts()
    aids, atexts, ameta = article_texts()
    print(f"тегов с описанием: {len(tids)} · законов: {len(lids)} · статей: {len(aids)}")
    print(f"движок: {args.engine} · порог тега {args.min} · порог закона {args.min_law}")

    T, L, A = matrices([ttexts, ltexts, atexts], args.engine, ttexts + ltexts + atexts)
    n_articles = A.shape[0]
    hub_t = hubness(A, T, args.engine)
    hub_l = hubness(A, L, args.engine)

    if args.show:
        i = aids.index(args.show) if args.show in aids else None
        if i is None:
            print("статья не найдена")
            return 1
        sim = sim_rows(A, T, i, i + 1)[0]
        keep = set(pick(sim, args.top, args.min, args.hub, hub_t))
        print(f"\n{ameta[aids[i]]['title']}")
        print(f"  сейчас:   {ameta[aids[i]]['main']} · {', '.join(ameta[aids[i]]['tags'][:5])}")
        # Показываем и отсеянных — иначе не видно, ЧТО именно отсекает порог, и любой
        # спор о его величине идёт вслепую. Галочка слева = тег попадёт в статью.
        print("  по смыслу:  (✓ — берём)")
        for j in np.argsort(sim)[::-1][:args.top]:
            h = f"  сверх обычного {sim[j] - hub_t[j]:+.3f}" if hub_t is not None else ""
            print(f"   {'✓' if j in keep else ' '} {sim[j]:.3f}  {tids[j]}"
                  f"  ({tdict[tids[j]].get('name', '')}){h}")
        lsim = sim_rows(A, L, i, i + 1)[0]
        lkeep = set(pick(lsim, args.top_law, args.min_law, args.hub, hub_l))
        # У законов первый кандидат НЕ берётся даром: закона может не быть вовсе.
        lkeep = {j for j in lkeep if lsim[j] >= args.min_law}
        print("  законы по смыслу:")
        for j in np.argsort(lsim)[::-1][:args.top_law]:
            print(f"   {'✓' if j in lkeep else ' '} {lsim[j]:.3f}  {lids[j]}"
                  f"  ({ldict[lids[j]].get('name', '')})")
        return 0

    # массовая привязка
    revived = set()
    now_used = set()
    got = {}
    CH = 300
    top_scores = []
    for s in range(0, n_articles, CH):
        sim = sim_rows(A, T, s, s + CH)
        for i, row in enumerate(sim):
            top_scores.append(float(row.max()))
            aid = aids[s + i]
            picked = [tids[j] for j in pick(row, args.top, args.min, args.hub, hub_t)]
            got[aid] = picked
            now_used.update(ameta[aid]["tags"] + [ameta[aid]["main"]])
            revived.update(picked)

    # Законы — тем же способом и той же линейкой, но со своим порогом. И без поблажки
    # первому кандидату: тег есть у каждой статьи, закон — нет, пустая колонка честнее.
    laws_got, with_laws = {}, 0
    law_scores = []
    for s in range(0, n_articles, CH):
        sim = sim_rows(A, L, s, s + CH)
        for i, row in enumerate(sim):
            law_scores.append(float(row.max()))
            aid = aids[s + i]
            picked = [lids[j] for j in pick(row, args.top_law, args.min_law, args.hub, hub_l)
                      if row[j] >= args.min_law]
            laws_got[aid] = picked
            if picked:
                with_laws += 1
    # Шкала движка — числом, а не на глаз. Порог берётся отсюда: если лучший тег у 95%
    # статей выше 0,58, то отсечка 0,50 не отсекает ничего, и колонка «пусто» не работает.
    def spread(name, xs):
        xs = sorted(xs)
        q = lambda p: xs[min(int(len(xs) * p), len(xs) - 1)]
        print(f"  лучший {name}: p5 {q(.05):.3f} · медиана {q(.5):.3f} · "
              f"p95 {q(.95):.3f} · max {xs[-1]:.3f}")
    print("\nшкала движка (близость лучшего кандидата к статье):")
    spread("тег  ", top_scores)
    spread("закон", law_scores)

    print("")
    print(f"законы: статей с законами {with_laws} из {len(aids)} "
          f"({with_laws * 100 // max(len(aids), 1)}%), у остальных честно пусто")
    used_laws = set()
    for v in laws_got.values():
        used_laws.update(v)
    print(f"   законов в ходу: {len(used_laws)} из {len(ldict)}")

    old_dead = set(tdict) - now_used
    new_dead = set(tdict) - revived
    print(f"\nбыло тегов без единой статьи: {len(old_dead)} из {len(tdict)}")
    print(f"стало по смысловой привязке:   {len(new_dead)} из {len(tdict)}")
    print(f"ожили: {len(old_dead - new_dead)} тегов")
    ex = sorted(old_dead - new_dead)[:12]
    print("например:", ex)

    # Реестр понятий: источник связи «понятие → его учёные».
    _REG = json.loads((ROOT / "data" / "concepts.json").read_text(encoding="utf-8"))["concepts"]         if (ROOT / "data" / "concepts.json").exists() else {}
    if args.apply:
        n = 0
        for aid, tags in got.items():
            p = ameta[aid]["path"]
            d = json.loads(p.read_text(encoding="utf-8"))
            # Пишем во ВСЕ языки, а не только в русский.
            #
            # Теги и законы — идентификаторы, они общие для всех языков: страница сама
            # подставит перевод названия. Записав только в русский, мы получили бы сайт,
            # где русская версия статьи размечена по смыслу, а английская и арабская —
            # по-старому, из промпта. Один и тот же материал с разными связями в разных
            # языках — худший вид расхождения: его никто не заметит.
            # Учёные — ВЫВОДИМ, а не спрашиваем у модели (владелец 2026-08-18: «учёные
            # должны быть связаны с законами автоматом, это отдельный процесс»). В реестре
            # понятий у 466 из 536 записей есть свои учёные, и закон знает своих авторов
            # точнее, чем модель, которой в промпт кладут список из 201 имени. Берём
            # объединение по назначенным законам и тегам, режем до шести: страница с
            # двадцатью именами не связь, а шум.
            sci = []
            for cid in list(laws_got.get(aid, [])) + list(tags):
                for name in (_REG.get(cid, {}).get("scientists") or []):
                    if name not in sci:
                        sci.append(name)
            sci = sci[:6]
            for tier in ("simple", "popular", "advanced"):
                for _lang in ("ru", "en", "es", "ar", "fr"):
                    v = d.get(tier, {}).get(_lang)
                    if isinstance(v, dict):
                        v["tags_vec"] = tags
                        v["laws_vec"] = laws_got.get(aid, [])
                        v["scientists_vec"] = sci
                v = d.get(tier, {}).get("ru")
                if isinstance(v, dict):
                    v["tags_vec"] = tags
                    # Законы кладём рядом и тем же способом. Раньше они выводились из
                    # тегов — закон цеплялся к статье по одному общему тегу, и закон
                    # излучения Планка приклеивался ко всему, где упомянута спектроскопия.
                    v["laws_vec"] = laws_got.get(aid, [])
            if _save_if_changed(p, d):
                n += 1
        print(f"\nзаписано в tags_vec: {n} статей (нынешние теги не тронуты)")
    else:
        print("\nэто сверка — ничего не записано; --apply запишет в поле tags_vec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
