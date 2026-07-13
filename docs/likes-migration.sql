-- bridge42worlds · ПОЛНЫЙ скрипт обновления таблицы реакций
-- ─────────────────────────────────────────────────────────────────────────────
-- Сервис:  Supabase (Postgres 15+), проект gyfdyfbuolnciaqxgybx
--          (js/likes.js: SUPABASE_URL = https://gyfdyfbuolnciaqxgybx.supabase.co,
--           таблица public.likes, вставка insert({ article_id, reaction }), счёт по article_id+reaction).
--
-- Что делает этот скрипт (идемпотентно, можно гонять повторно):
--   1) reaction         — тип реакции: like | dislike | superlike (по умолч. like, старые строки = like)
--   2) version/lang/base_id — автовычисляемые из article_id ("{arxiv_id}_{lang}_{version}",
--      напр. "2607.00565v1_ru_popular"); arxiv_id/коды языков/версий без '_', разбор надёжен.
--   3) индексы под аналитику и группировки
--
-- Идея: одна строка = одна реакция-событие; счёт = count по (article_id, reaction).
-- Защита пока клиентская (anon-key + localStorage), без RLS/rate-limit — отдельная задача (TODO.md).
-- ─────────────────────────────────────────────────────────────────────────────

-- 1) Тип реакции ─────────────────────────────────────────────────────────────
alter table public.likes
  add column if not exists reaction text not null default 'like';

-- ограничение допустимых значений (снимаем старое, если было, и ставим заново)
alter table public.likes drop constraint if exists likes_reaction_chk;
alter table public.likes
  add constraint likes_reaction_chk check (reaction in ('like', 'dislike', 'superlike'));

-- 2) Автовычисляемые колонки версия/язык/базовый-id ──────────────────────────
alter table public.likes
  add column if not exists version text
    generated always as (
      case when array_length(string_to_array(article_id, '_'), 1) >= 3
           then split_part(article_id, '_', -1) end
    ) stored,
  add column if not exists lang text
    generated always as (
      case when array_length(string_to_array(article_id, '_'), 1) >= 3
           then split_part(article_id, '_', -2) end
    ) stored,
  add column if not exists base_id text
    generated always as (
      case when array_length(string_to_array(article_id, '_'), 1) >= 3
           then regexp_replace(article_id, '_[^_]+_[^_]+$', '')
           else article_id end
    ) stored;

-- 3) Индексы ─────────────────────────────────────────────────────────────────
create index if not exists likes_reaction_idx         on public.likes (reaction);
create index if not exists likes_article_reaction_idx on public.likes (article_id, reaction);
create index if not exists likes_version_idx          on public.likes (version);
create index if not exists likes_lang_idx             on public.likes (lang);
create index if not exists likes_base_id_idx          on public.likes (base_id);

-- 4) Проверка (выполни после миграции) ───────────────────────────────────────
--   -- реакции по статье/языку/версии:
--   select base_id, lang, version, reaction, count(*) AS n
--   from public.likes group by base_id, lang, version, reaction order by n desc;
--
--   -- сводка по типам реакций:      select reaction, count(*) from public.likes group by reaction;
--   -- реакции по языкам:            select lang, reaction, count(*) from public.likes group by lang, reaction;
-- ─────────────────────────────────────────────────────────────────────────────
