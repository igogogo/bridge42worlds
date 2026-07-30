"""Доменные облака тегов: статья видит в промпте словарь СВОЕЙ области, а не весь список.

Зачем. Словарь закрытый: модель обязана выбрать теги из присланного списка. Список
собирался под астрофизику (233 тега, из них astrophysics 53, а на всю биологию 28 и
на информатику ноль), и биологической статье просто нечего выбрать — она берёт ближайший
физический тег. Это не ошибка модели, это ошибка входных данных.

Как. По разделам arXiv статьи определяем домены, отдаём теги этих доменов плюс сквозное
ядро (методы, приборы, математика) — они применимы в любой области. Если доменов не
опознали, отдаём весь список: лучше широкий словарь, чем пустой.

Побочный выигрыш — цена: список тегов уходит в промпт advanced на каждой статье,
и физическая статья больше не платит за биологические теги.
"""

# Раздел arXiv (то, что до точки) → домен нашего словаря. Держать в паре с полем domain
# в lang/ru/data/tags-list.json: домена, которого нет в словаре, здесь быть не должно.
DOMAIN_BY_GROUP = {
    "astro-ph": ("astrophysics", "cosmology", "relativity_gravity"),
    "gr-qc": ("relativity_gravity", "cosmology", "astrophysics"),
    "hep-th": ("particles_nuclear", "quantum", "relativity_gravity"),
    "hep-ph": ("particles_nuclear", "quantum"),
    "hep-ex": ("particles_nuclear",),
    "nucl-th": ("particles_nuclear",),
    "nucl-ex": ("particles_nuclear",),
    "quant-ph": ("quantum", "electromagnetism_optics"),
    "cond-mat": ("chemistry_materials", "quantum", "thermo_stat"),
    "physics": ("electromagnetism_optics", "thermo_stat", "chemistry_materials"),
    "math": ("mathematics",),
    "math-ph": ("mathematics", "quantum"),
    "nlin": ("mathematics", "thermo_stat"),
    "stat": ("mathematics",),
    "cs": ("computer_science", "mathematics"),
    "eess": ("engineering", "electromagnetism_optics"),
    "q-bio": ("biology", "genomics", "neuroscience", "medicine", "bioengineering"),
    "q-fin": ("economics_finance", "mathematics"),
    "econ": ("economics_finance",),
}

# Сквозное ядро: методы, приборы и математика нужны статье любой области —
# «численное моделирование», «спектроскопия», «машинное обучение» не принадлежат физике.
UNIVERSAL_DOMAINS = ("instruments_methods", "mathematics")

# Ниже этого числа тегов облако не сужаем: модели не из чего выбирать, и она начнёт
# натягивать далёкие теги — ровно та беда, от которой уходим.
MIN_CLOUD = 40


def domains_for(categories):
    """Разделы arXiv статьи → домены словаря (порядок не важен, дубли схлопываются)."""
    out = set()
    for category in categories or []:
        group = str(category).split(".")[0].strip()
        out.update(DOMAIN_BY_GROUP.get(group, ()))
    return out


def cloud_for(article, tags_input):
    """Список тегов для промпта этой статьи. Возвращает исходный список без изменений,
    если сузить не получилось — пустой словарь хуже широкого."""
    categories = list(article.get("categories") or [])
    primary = article.get("primary_category")
    if primary:
        categories.insert(0, primary)
    wanted = domains_for(categories)
    if not wanted:
        return tags_input
    wanted.update(UNIVERSAL_DOMAINS)
    cloud = [t for t in tags_input if t.get("domain") in wanted]
    return cloud if len(cloud) >= MIN_CLOUD else tags_input


def describe(article, tags_input):
    """Строка для лога: во что превратился словарь у этой статьи."""
    cloud = cloud_for(article, tags_input)
    if len(cloud) == len(tags_input):
        return f"облако тегов: весь словарь ({len(tags_input)})"
    domains = sorted(domains_for(list(article.get("categories") or []) +
                                 [article.get("primary_category") or ""]) | set(UNIVERSAL_DOMAINS))
    return f"облако тегов: {len(cloud)} из {len(tags_input)} — {', '.join(domains)}"
