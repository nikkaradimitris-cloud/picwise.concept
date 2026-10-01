-- PicWise query log for the NLU training loop (see src/picwise_app/query_log_sink.py).
-- Run once in the Supabase SQL editor of the project PicWise should write to.
-- Holds no personal data: no IP, user agent or session.

create table if not exists public.picwise_query_log (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    "timestamp" text,
    query text not null,
    source_page text,
    resolver_state text,
    understood_concept text,
    understood_by_correction boolean not null default false,
    choices_rendered boolean not null default false
);

create index if not exists picwise_query_log_created_at_idx
    on public.picwise_query_log (created_at desc);

-- Row level security on, with no policies: the anon and authenticated keys can neither
-- read nor write. The site writes with the service_role key, which bypasses RLS and
-- must only ever be set as a server-side environment variable.
alter table public.picwise_query_log enable row level security;
