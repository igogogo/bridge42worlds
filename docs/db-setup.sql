-- bridge42worlds · ПОЛНАЯ ПЕРЕСБОРКА БД С НУЛЯ (destructive)
-- ═════════════════════════════════════════════════════════════════════════════
-- Сервис: Supabase (Postgres 15+), проект gyfdyfbuolnciaqxgybx.
-- ⚠️ DROP удаляет ВСЕ существующие данные (старые лайки будут потеряны — это осознанно).
-- Запусти целиком в Supabase → SQL Editor. Идемпотентно (можно гонять повторно).
--
-- Модель:
--   likes     — реакции: like | dislike | superlike (1 строка = 1 реакция-событие, счёт = count)
--   feedback  — обратная связь: чипы (options) + опциональный comment (для правки промтов)
--   article_id везде = "{arxiv_id}_{lang}_{version}", напр. "2607.00565v1_ru_popular".
--   version/lang/base_id — автовычисляются из article_id (STORED, индексируемы).
-- ═════════════════════════════════════════════════════════════════════════════

drop table if exists public.likes    cascade;
drop table if exists public.feedback cascade;

-- ── Реакции ──────────────────────────────────────────────────────────────────
create table public.likes (
  id          bigint generated always as identity primary key,
  article_id  text not null,
  reaction    text not null default 'like' check (reaction in ('like', 'dislike', 'superlike')),
  created_at  timestamptz not null default now(),
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
create index likes_article_reaction_idx on public.likes (article_id, reaction);
create index likes_reaction_idx          on public.likes (reaction);
create index likes_version_idx           on public.likes (version);
create index likes_lang_idx              on public.likes (lang);
create index likes_base_id_idx           on public.likes (base_id);

-- ── Обратная связь ───────────────────────────────────────────────────────────
create table public.feedback (
  id          bigint generated always as identity primary key,
  article_id  text not null,
  options     text[] not null default '{}',   -- выбранные чипы
  comment     text,                            -- ручной комментарий (необязательный)
  created_at  timestamptz not null default now(),
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
create index feedback_article_idx on public.feedback (article_id);
create index feedback_version_idx on public.feedback (version);
create index feedback_lang_idx    on public.feedback (lang);
create index feedback_created_idx on public.feedback (created_at);

-- ── Доступ анонимному клиенту (anon-key) ─────────────────────────────────────
-- Включаем RLS и открываем insert + select для anon (реакции/фидбэк — публичные).
-- (Без RLS таблица тоже доступна anon в Supabase, но с RLS + политиками — явно и правильно.)
alter table public.likes    enable row level security;
alter table public.feedback enable row level security;

create policy likes_insert_anon    on public.likes    for insert to anon with check (true);
create policy likes_select_anon    on public.likes    for select to anon using (true);
create policy feedback_insert_anon on public.feedback for insert to anon with check (true);
create policy feedback_select_anon on public.feedback for select to anon using (true);

-- ── Проверка/аналитика ───────────────────────────────────────────────────────
--   select reaction, count(*) from public.likes group by reaction;
--   select base_id, lang, version, reaction, count(*) n from public.likes
--     group by base_id, lang, version, reaction order by n desc;
--   select version, unnest(options) opt, count(*) n from public.feedback group by version, opt order by n desc;
--   select created_at, lang, version, comment from public.feedback
--     where comment is not null and comment <> '' order by created_at desc limit 50;
-- ═════════════════════════════════════════════════════════════════════════════
