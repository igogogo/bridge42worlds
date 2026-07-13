-- bridge42worlds · таблица обратной связи (для правки промтов по отзывам читателей)
-- ─────────────────────────────────────────────────────────────────────────────
-- Сервис: Supabase (Postgres 15+), проект gyfdyfbuolnciaqxgybx.
-- Клиент (js/likes.js): insert({ article_id, options, comment }).
--   article_id — составной "{arxiv_id}_{lang}_{version}" (как в likes) → знаем версию и язык отзыва.
--   options    — выбранные чипы (["Хорошо читается","Многовато",...]).
--   comment    — необязательный свободный комментарий.
-- Идемпотентно, можно гонять повторно.
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists public.feedback (
  id          bigint generated always as identity primary key,
  article_id  text not null,
  options     text[] not null default '{}',
  comment     text,
  created_at  timestamptz not null default now(),
  -- автовычисляемые срезы (как в likes): версия/язык/базовый-id
  version text generated always as (
    case when array_length(string_to_array(article_id, '_'), 1) >= 3
         then split_part(article_id, '_', -1) end) stored,
  lang text generated always as (
    case when array_length(string_to_array(article_id, '_'), 1) >= 3
         then split_part(article_id, '_', -2) end) stored,
  base_id text generated always as (
    case when array_length(string_to_array(article_id, '_'), 1) >= 3
         then regexp_replace(article_id, '_[^_]+_[^_]+$', '')
         else article_id end) stored
);

create index if not exists feedback_article_idx on public.feedback (article_id);
create index if not exists feedback_version_idx on public.feedback (version);
create index if not exists feedback_lang_idx    on public.feedback (lang);
create index if not exists feedback_created_idx on public.feedback (created_at);

-- RLS: разрешить анонимные вставки и чтение агрегатов (как у likes — anon-key).
-- ⚠️ Включи RLS и политики в Supabase UI, либо раскомментируй ниже (осторожно с открытым insert):
-- alter table public.feedback enable row level security;
-- create policy feedback_insert_anon on public.feedback for insert to anon with check (true);
-- create policy feedback_select_anon on public.feedback for select to anon using (true);

-- Аналитика для правки промтов:
--   -- частота чипов по версии:
--   select version, unnest(options) as opt, count(*) n
--   from public.feedback group by version, opt order by n desc;
--   -- свежие комментарии:
--   select created_at, lang, version, comment from public.feedback
--   where comment is not null and comment <> '' order by created_at desc limit 50;
-- ─────────────────────────────────────────────────────────────────────────────
