-- ============================================================
-- Misinformation Velocity Tracker — Supabase schema
-- Run this in the Supabase SQL editor. Safe to re-run:
-- every statement is idempotent.
-- ============================================================

-- pgvector extension (Supabase ships it, just enable it)
create extension if not exists vector;

-- ------------------------------------------------------------
-- claims: one row per canonical/root claim (the "topic")
-- ------------------------------------------------------------
create table if not exists claims (
    id            uuid primary key default gen_random_uuid(),
    canonical     text not null,               -- normalized core factual claim
    domain        text,                         -- health | election | government | finance | other
    language      text,                         -- en | ne | romanized | mixed
    label         text,                         -- REAL | FAKE | UNVERIFIED
    verdict       text,
    rationale     text,
    source        text,                         -- which dataset/loader produced it
    created_at    timestamptz default now()
);

alter table claims add column if not exists domain text;
alter table claims add column if not exists language text;
alter table claims add column if not exists label text;
alter table claims add column if not exists verdict text;
alter table claims add column if not exists rationale text;
alter table claims add column if not exists source text;
alter table claims add column if not exists created_at timestamptz default now();

-- ------------------------------------------------------------
-- claim_assessments: structured truth/provenance metadata.
-- A claim may have multiple assessments over time; consumers use the
-- most recent assessment for a tier when presenting rankings.
-- ------------------------------------------------------------
create table if not exists claim_assessments (
    id              uuid primary key default gen_random_uuid(),
    claim_id        uuid not null references claims(id) on delete cascade,
    tier            text not null,
    verdict         text not null,
    confidence      numeric,
    rationale       text,
    model           text,
    assessed_at     timestamptz not null default now(),
    evidence_url    text,
    evidence_title  text,
    source          text,
    constraint claim_assessments_tier_check
        check (tier in ('VERIFIED_FALSE', 'AI_FLAGGED', 'UNVERIFIED')),
    constraint claim_assessments_confidence_check
        check (confidence is null or (confidence >= 0 and confidence <= 1))
);

alter table claim_assessments add column if not exists claim_id uuid references claims(id) on delete cascade;
alter table claim_assessments add column if not exists tier text;
alter table claim_assessments add column if not exists verdict text;
alter table claim_assessments add column if not exists confidence numeric;
alter table claim_assessments add column if not exists rationale text;
alter table claim_assessments add column if not exists model text;
alter table claim_assessments add column if not exists assessed_at timestamptz default now();
alter table claim_assessments add column if not exists evidence_url text;
alter table claim_assessments add column if not exists evidence_title text;
alter table claim_assessments add column if not exists source text;

-- ------------------------------------------------------------
-- variants: individual posts/appearances of a claim across
-- platforms + time. This is what the mutation tree & velocity
-- chart are built from.
-- ------------------------------------------------------------
create table if not exists variants (
    id                 uuid primary key default gen_random_uuid(),
    claim_id           uuid references claims(id) on delete cascade,
    text               text not null,
    embedding          vector(768),             -- keep in sync with EMBEDDING_DIM
    platform           text,                    -- facebook | tiktok | x | youtube | whatsapp | submission
    author             text,
    ts                 timestamptz,             -- when this variant appeared (drives velocity)
    parent_id          uuid references variants(id) on delete set null, -- reconstructed lineage
    expected_parent_id uuid,                    -- ground-truth hint (validation only, not shown)
    mutation_type      text,                    -- paraphrase | exaggeration | translation | number_distortion | original
    -- evidence / verdict fields (from NepOOC + MisDetect)
    verdict            text,
    rationale          text,
    confidence         numeric,
    evidence_url       text,
    evidence_title     text,
    entities           text[],
    language           text,
    source             text,                    -- dataset/loader origin
    created_at         timestamptz default now()
);

alter table variants add column if not exists embedding vector(768);
alter table variants add column if not exists platform text;
alter table variants add column if not exists author text;
alter table variants add column if not exists ts timestamptz;
alter table variants add column if not exists parent_id uuid references variants(id) on delete set null;
alter table variants add column if not exists expected_parent_id uuid;
alter table variants add column if not exists mutation_type text;
alter table variants add column if not exists verdict text;
alter table variants add column if not exists rationale text;
alter table variants add column if not exists confidence numeric;
alter table variants add column if not exists evidence_url text;
alter table variants add column if not exists evidence_title text;
alter table variants add column if not exists entities text[];
alter table variants add column if not exists language text;
alter table variants add column if not exists source text;
alter table variants add column if not exists created_at timestamptz default now();

-- ------------------------------------------------------------
-- claim_submissions: private ownership and quota ledger.
-- User UUIDs intentionally live outside the public corpus.
-- ------------------------------------------------------------
create table if not exists claim_submissions (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references auth.users(id) on delete cascade,
    variant_id    uuid not null unique references variants(id) on delete cascade,
    submitted_at  timestamptz not null default now()
);

alter table claim_submissions add column if not exists user_id uuid;
alter table claim_submissions add column if not exists variant_id uuid;
alter table claim_submissions add column if not exists submitted_at timestamptz default now();

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'claim_submissions_user_id_fkey'
          and conrelid = 'public.claim_submissions'::regclass
    ) then
        alter table public.claim_submissions
            add constraint claim_submissions_user_id_fkey
            foreign key (user_id) references auth.users(id) on delete cascade;
    end if;
    if not exists (
        select 1 from pg_constraint
        where conname = 'claim_submissions_variant_id_fkey'
          and conrelid = 'public.claim_submissions'::regclass
    ) then
        alter table public.claim_submissions
            add constraint claim_submissions_variant_id_fkey
            foreign key (variant_id) references public.variants(id) on delete cascade;
    end if;
end
$$;

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------
create index if not exists variants_claim_id_idx on variants(claim_id);
create index if not exists variants_ts_idx on variants(ts);
create index if not exists variants_ts_claim_id_idx on variants(ts, claim_id);
create index if not exists claims_source_created_at_idx on claims(source, created_at desc);
create index if not exists claim_assessments_claim_tier_time_idx
    on claim_assessments(claim_id, tier, assessed_at desc);
create index if not exists claim_assessments_tier_time_idx
    on claim_assessments(tier, assessed_at desc);
create unique index if not exists claim_submissions_variant_id_idx
    on claim_submissions(variant_id);
create index if not exists claim_submissions_user_time_idx
    on claim_submissions(user_id, submitted_at desc);

-- Approximate nearest-neighbour index for similarity search.
-- (Create AFTER bulk load for best build performance.)
create index if not exists variants_embedding_idx
    on variants using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ------------------------------------------------------------
-- RPC: cosine-similarity search used by the pipeline / API.
-- Returns the most similar variants to a query embedding.
-- ------------------------------------------------------------
create or replace function match_variants(
    query_embedding vector(768),
    match_threshold float default 0.75,
    match_count int default 20
)
returns table (
    id uuid,
    claim_id uuid,
    text text,
    platform text,
    ts timestamptz,
    similarity float
)
language sql stable
set search_path = ''
as $$
    select
        v.id,
        v.claim_id,
        v.text,
        v.platform,
        v.ts,
        1 - (v.embedding OPERATOR(extensions.<=>) query_embedding) as similarity
    from public.variants v
    where v.embedding is not null
      and 1 - (v.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
    order by v.embedding OPERATOR(extensions.<=>) query_embedding
    limit match_count;
$$;

-- ------------------------------------------------------------
-- Public corpus security boundary.
-- Corpus rows are readable by everyone but writable only through
-- privileged loader access or the authenticated ingestion RPC.
-- ------------------------------------------------------------
alter table public.claims enable row level security;
alter table public.claims force row level security;
alter table public.claim_assessments enable row level security;
alter table public.claim_assessments force row level security;
alter table public.variants enable row level security;
alter table public.variants force row level security;
alter table public.claim_submissions enable row level security;
alter table public.claim_submissions force row level security;

drop policy if exists claims_public_read on public.claims;
create policy claims_public_read on public.claims
    for select to anon, authenticated using (true);

drop policy if exists claim_assessments_public_read on public.claim_assessments;
create policy claim_assessments_public_read on public.claim_assessments
    for select to anon, authenticated using (true);

drop policy if exists variants_public_read on public.variants;
create policy variants_public_read on public.variants
    for select to anon, authenticated using (true);

revoke all on table public.claims from anon, authenticated;
revoke all on table public.variants from anon, authenticated;
grant select on table public.claims to anon, authenticated;
grant select on table public.variants to anon, authenticated;

revoke all on table public.claim_submissions from anon, authenticated;
revoke all on table public.claim_submissions from public;

grant all on table public.claims to service_role;
grant all on table public.variants to service_role;
grant all on table public.claim_submissions to service_role;

revoke all on function public.match_variants(vector, float, int) from public;
revoke all on function public.match_variants(vector, float, int) from anon, authenticated;
grant execute on function public.match_variants(vector, float, int) to service_role;

-- ------------------------------------------------------------
-- Authenticated atomic ingestion. Matching and insertion share one
-- transaction and lock, so concurrent equivalent submissions cannot
-- create duplicate roots.
-- ------------------------------------------------------------
create or replace function public.ingest_claim_atomic(
    p_text text,
    p_canonical text,
    p_domain text,
    p_language text,
    p_embedding vector(768),
    p_platform text default 'submission',
    p_ts timestamptz default now(),
    p_match_threshold double precision default 0.55,
    p_match_window_days integer default 3650,
    p_rate_limit integer default 10,
    p_rate_window_minutes integer default 60
)
returns table (
    claim_id uuid,
    variant_id uuid,
    parent_id uuid,
    matched boolean,
    similarity double precision,
    variant_count bigint
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_claim_id uuid;
    v_variant_id uuid;
    v_parent_id uuid;
    v_similarity double precision;
    v_matched boolean := false;
    v_variant_count bigint;
begin
    if v_user_id is null then
        raise exception using errcode = 'P0001', message = 'INGEST_UNAUTHORIZED';
    end if;
    if p_text is null or length(btrim(p_text)) = 0 or length(p_text) > 4000 then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_TEXT';
    end if;
    if p_canonical is null or length(btrim(p_canonical)) = 0
       or length(p_canonical) > 1000 then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_CANONICAL';
    end if;
    if p_domain not in ('health', 'election', 'government', 'finance', 'education', 'other')
       or p_language not in ('en', 'ne', 'romanized', 'mixed') then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_CLASSIFICATION';
    end if;
    -- The vector(768) argument type rejects any other dimension before entry.
    if p_embedding is null then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_EMBEDDING';
    end if;
    if p_match_threshold < 0 or p_match_threshold > 1
       or p_match_window_days < 1 or p_rate_limit < 1
       or p_rate_window_minutes < 1 then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_LIMITS';
    end if;

    -- Serialize the nearest-match/create decision. This favors correctness over
    -- write throughput and prevents concurrent first submissions from splitting.
    perform pg_advisory_xact_lock(hashtext('public.ingest_claim_atomic'));

    if (
        select count(*)
        from public.claim_submissions s
        where s.user_id = v_user_id
          and s.submitted_at >= now() - make_interval(mins => p_rate_window_minutes)
    ) >= p_rate_limit then
        raise exception using errcode = 'P0001', message = 'INGEST_RATE_LIMITED';
    end if;

    select v.claim_id, v.id, 1 - (v.embedding OPERATOR(extensions.<=>) p_embedding)
    into v_claim_id, v_parent_id, v_similarity
    from public.variants v
    where v.embedding is not null
      and v.created_at >= now() - make_interval(days => p_match_window_days)
      and 1 - (v.embedding OPERATOR(extensions.<=>) p_embedding) >= p_match_threshold
    order by v.embedding OPERATOR(extensions.<=>) p_embedding, v.created_at, v.id
    limit 1;

    if v_claim_id is null then
        insert into public.claims (
            canonical, domain, language, label, verdict, rationale, source
        ) values (
            btrim(p_canonical), p_domain, p_language, 'UNVERIFIED', 'UNVERIFIED',
            'No claim-specific evidence has been inspected; human verification is required.',
            'submission'
        )
        returning id into v_claim_id;
    else
        v_matched := true;
    end if;

    insert into public.variants (
        claim_id, text, embedding, platform, ts, parent_id, mutation_type,
        verdict, rationale, source, language
    ) values (
        v_claim_id, btrim(p_text), p_embedding, coalesce(nullif(p_platform, ''), 'submission'),
        coalesce(p_ts, now()), v_parent_id,
        case when v_matched then 'paraphrase' else 'original' end,
        'UNVERIFIED',
        'No claim-specific evidence has been inspected; human verification is required.',
        'submission', p_language
    )
    returning id into v_variant_id;

    insert into public.claim_submissions (user_id, variant_id)
    values (v_user_id, v_variant_id);

    select count(*) into v_variant_count
    from public.variants v where v.claim_id = v_claim_id;

    return query select v_claim_id, v_variant_id, v_parent_id, v_matched,
        v_similarity, v_variant_count;
end
$$;

revoke all on function public.ingest_claim_atomic(
    text, text, text, text, vector, text, timestamptz,
    double precision, integer, integer, integer
) from public, anon;
grant execute on function public.ingest_claim_atomic(
    text, text, text, text, vector, text, timestamptz,
    double precision, integer, integer, integer
) to authenticated;

-- ------------------------------------------------------------
-- news_articles: durable staging for external RSS ingestion.
-- Every fetched article lands here BEFORE any AI work; the unique
-- url_hash makes deduplication survive restarts. Only extracted
-- factual claims are promoted into the claims/variants graph.
-- status: pending | promoted | skipped | failed
-- ------------------------------------------------------------
create table if not exists news_articles (
    id            uuid primary key default gen_random_uuid(),
    url           text not null,
    url_hash      text not null unique,
    title         text not null,
    source_name   text,
    published_at  timestamptz,
    fetched_at    timestamptz not null default now(),
    status        text not null default 'pending',
    claim_id      uuid references claims(id) on delete set null,
    variant_id    uuid references variants(id) on delete set null,
    error         text
);

alter table news_articles add column if not exists url text;
alter table news_articles add column if not exists url_hash text;
alter table news_articles add column if not exists title text;
alter table news_articles add column if not exists source_name text;
alter table news_articles add column if not exists published_at timestamptz;
alter table news_articles add column if not exists fetched_at timestamptz default now();
alter table news_articles add column if not exists status text default 'pending';
alter table news_articles add column if not exists claim_id uuid references claims(id) on delete set null;
alter table news_articles add column if not exists variant_id uuid references variants(id) on delete set null;
alter table news_articles add column if not exists error text;

create unique index if not exists news_articles_url_hash_idx on news_articles(url_hash);
create index if not exists news_articles_status_idx on news_articles(status);
create index if not exists news_articles_fetched_at_idx on news_articles(fetched_at desc);

-- Staging table is server-side only: no anon/authenticated access.
-- service_role bypasses RLS, so the backend poller can read/write freely.
alter table public.news_articles enable row level security;
alter table public.news_articles force row level security;

revoke all on table public.news_articles from anon, authenticated;
revoke all on table public.news_articles from public;
grant all on table public.news_articles to service_role;

-- ------------------------------------------------------------
-- news_poll_runs: durable poll history and expiring overlap lease.
-- A row with status='running' and a future lease_expires_at owns the
-- singleton poll lease. Atomic RPCs below serialize worker/manual runs.
-- ------------------------------------------------------------
create table if not exists news_poll_runs (
    id                uuid primary key default gen_random_uuid(),
    owner_id          text not null,
    trigger           text not null,
    status            text not null default 'running',
    started_at        timestamptz not null default now(),
    completed_at      timestamptz,
    lease_expires_at  timestamptz not null,
    counters          jsonb not null default '{}'::jsonb,
    error_summary     text,
    constraint news_poll_runs_trigger_check
        check (trigger in ('worker', 'manual')),
    constraint news_poll_runs_status_check
        check (status in ('running', 'succeeded', 'failed', 'quota_delayed'))
);

alter table news_poll_runs add column if not exists owner_id text;
alter table news_poll_runs add column if not exists trigger text;
alter table news_poll_runs add column if not exists status text default 'running';
alter table news_poll_runs add column if not exists started_at timestamptz default now();
alter table news_poll_runs add column if not exists completed_at timestamptz;
alter table news_poll_runs add column if not exists lease_expires_at timestamptz;
alter table news_poll_runs add column if not exists counters jsonb default '{}'::jsonb;
alter table news_poll_runs add column if not exists error_summary text;

create index if not exists news_poll_runs_started_at_idx
    on news_poll_runs(started_at desc);
create index if not exists news_poll_runs_status_completed_idx
    on news_poll_runs(status, completed_at desc);

alter table public.news_poll_runs enable row level security;
alter table public.news_poll_runs force row level security;
revoke all on table public.news_poll_runs from public, anon, authenticated;
grant all on table public.news_poll_runs to service_role;

create or replace function public.acquire_news_poll_lease(
    p_owner text,
    p_trigger text,
    p_lease_seconds integer default 1800
)
returns table (acquired boolean, run_id uuid, lease_expires_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_active record;
    v_run_id uuid;
    v_expires_at timestamptz;
begin
    if nullif(btrim(p_owner), '') is null
       or p_trigger not in ('worker', 'manual')
       or p_lease_seconds < 60 or p_lease_seconds > 86400 then
        raise exception 'Invalid news poll lease request' using errcode = '22023';
    end if;

    perform pg_advisory_xact_lock(hashtext('public.news_poll_lease'));

    update public.news_poll_runs as r
    set status = 'failed',
        completed_at = now(),
        error_summary = 'Poll lease expired before completion'
    where r.status = 'running' and r.lease_expires_at <= now();

    select r.id, r.lease_expires_at
    into v_active
    from public.news_poll_runs r
    where r.status = 'running' and r.lease_expires_at > now()
    order by r.started_at desc
    limit 1;

    if found then
        return query select false, v_active.id, v_active.lease_expires_at;
        return;
    end if;

    v_expires_at := now() + make_interval(secs => p_lease_seconds);
    insert into public.news_poll_runs (owner_id, trigger, lease_expires_at)
    values (btrim(p_owner), p_trigger, v_expires_at)
    returning id into v_run_id;

    return query select true, v_run_id, v_expires_at;
end
$$;

create or replace function public.finish_news_poll_run(
    p_run_id uuid,
    p_owner text,
    p_status text,
    p_counters jsonb default '{}'::jsonb,
    p_error_summary text default null
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_updated integer;
begin
    if p_status not in ('succeeded', 'failed', 'quota_delayed') then
        raise exception 'Invalid terminal poll status' using errcode = '22023';
    end if;

    update public.news_poll_runs
    set status = p_status,
        completed_at = now(),
        counters = coalesce(p_counters, '{}'::jsonb),
        error_summary = left(p_error_summary, 500)
    where id = p_run_id and owner_id = p_owner and status = 'running';
    get diagnostics v_updated = row_count;
    return v_updated = 1;
end
$$;

revoke all on function public.acquire_news_poll_lease(text, text, integer)
    from public, anon, authenticated;
revoke all on function public.finish_news_poll_run(uuid, text, text, jsonb, text)
    from public, anon, authenticated;
grant execute on function public.acquire_news_poll_lease(text, text, integer)
    to service_role;
grant execute on function public.finish_news_poll_run(uuid, text, text, jsonb, text)
    to service_role;

-- ------------------------------------------------------------
-- Bounded tracked-claim context for dashboard discovery.
-- Assessment and variant aggregates are selected once per claim so the
-- browser never needs one analytics request per list row.
-- ------------------------------------------------------------
create or replace function public.claim_list_context(
    p_limit integer default 50,
    p_offset integer default 0,
    p_query text default null,
    p_source text default null,
    p_domain text default null,
    p_language text default null,
    p_tier text default null,
    p_period text default null,
    p_platform text default null
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = public
as $$
declare
    v_window interval;
    v_now timestamptz := now();
    v_result jsonb;
begin
    if p_limit < 1 or p_limit > 100 or p_offset < 0 then
        raise exception 'invalid pagination';
    end if;
    if p_tier is not null and p_tier not in
        ('VERIFIED_FALSE', 'AI_FLAGGED', 'UNVERIFIED') then
        raise exception 'invalid tier';
    end if;
    v_window := case coalesce(p_period, 'week')
        when 'day' then interval '1 day'
        when 'week' then interval '7 days'
        when 'month' then interval '1 month'
        when 'year' then interval '1 year'
        else null
    end;
    if v_window is null then raise exception 'invalid period'; end if;

    with latest_assessment as (
        select distinct on (a.claim_id) a.*
        from claim_assessments a
        order by a.claim_id, a.assessed_at desc, a.id desc
    ), eligible as (
        select c.id, c.canonical, c.domain, c.language, c.label, c.source,
               c.created_at,
               coalesce(a.tier, 'UNVERIFIED') tier,
               coalesce(a.verdict, c.verdict, 'UNVERIFIED') verdict,
               coalesce(a.rationale, c.rationale) rationale,
               a.confidence, a.assessed_at, a.evidence_url, a.evidence_title
        from claims c
        left join latest_assessment a on a.claim_id = c.id
        where (p_query is null or c.canonical ilike '%' || p_query || '%')
          and (p_source is null or c.source = p_source)
          and (p_domain is null or c.domain = p_domain)
          and (p_language is null or c.language = p_language)
          and (p_tier is null or coalesce(a.tier, 'UNVERIFIED') = p_tier)
          and (p_platform is null or exists (
              select 1 from variants vp
              where vp.claim_id = c.id and vp.platform = p_platform
          ))
          and (p_period is null or exists (
              select 1 from variants vr
              where vr.claim_id = c.id
                and vr.ts >= v_now - v_window and vr.ts <= v_now
          ))
    ), enriched as (
        select e.*,
               coalesce(s.variant_count, 0)::integer variant_count,
               s.first_seen, s.last_seen,
               coalesce(s.current_count, 0)::integer current_count,
               coalesce(s.previous_count, 0)::integer previous_count,
               tp.top_platform
        from eligible e
        left join lateral (
            select count(*) variant_count, min(v.ts) first_seen, max(v.ts) last_seen,
                   count(*) filter (
                       where v.ts >= v_now - v_window and v.ts <= v_now
                   ) current_count,
                   count(*) filter (
                       where v.ts >= v_now - v_window - v_window
                         and v.ts < v_now - v_window
                   ) previous_count
            from variants v where v.claim_id = e.id
        ) s on true
        left join lateral (
            select coalesce(nullif(v.platform, ''), 'unknown') top_platform
            from variants v where v.claim_id = e.id
            group by coalesce(nullif(v.platform, ''), 'unknown')
            order by count(*) desc,
                     coalesce(nullif(v.platform, ''), 'unknown') asc
            limit 1
        ) tp on true
    ), page_rows as (
        select * from enriched
        order by last_seen desc nulls last, created_at desc nulls last, id desc
        limit p_limit offset p_offset
    )
    select jsonb_build_object(
        'items', coalesce((
            select jsonb_agg(to_jsonb(p) order by p.last_seen desc nulls last,
                p.created_at desc nulls last, p.id desc)
            from page_rows p
        ), '[]'::jsonb),
        'total', (select count(*) from enriched)
    ) into v_result;
    return v_result;
end
$$;

grant execute on function public.claim_list_context(
    integer, integer, text, text, text, text, text, text, text
) to anon, authenticated;

-- Make newly created RPC signatures visible to PostgREST immediately.
notify pgrst, 'reload schema';

-- ------------------------------------------------------------
-- External (service-role-only) atomic ingestion for promoted news
-- claims. Mirrors public.ingest_claim_atomic above — same validation,
-- same nearest-match/create/insert logic, and CRITICALLY the same
-- advisory lock key — minus auth.uid(), rate limiting, and the
-- claim_submissions write.
--
-- NOTE ON DUPLICATION: any change to the matching/insert logic in
-- public.ingest_claim_atomic MUST be mirrored here (and vice versa).
-- The two functions intentionally share the advisory lock key
-- hashtext('public.ingest_claim_atomic') so concurrent user
-- submissions and news promotions serialize together and cannot
-- split one claim into duplicate roots.
-- ------------------------------------------------------------
create or replace function public.ingest_external_claim_atomic(
    p_text text,
    p_canonical text,
    p_domain text,
    p_language text,
    p_embedding vector(768),
    p_platform text default 'news',
    p_source text default 'news',
    p_ts timestamptz default now(),
    p_match_threshold double precision default 0.55,
    p_match_window_days integer default 3650
)
returns table (
    claim_id uuid,
    variant_id uuid,
    parent_id uuid,
    matched boolean,
    similarity double precision,
    variant_count bigint
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_claim_id uuid;
    v_variant_id uuid;
    v_parent_id uuid;
    v_similarity double precision;
    v_matched boolean := false;
    v_variant_count bigint;
begin
    if p_text is null or length(btrim(p_text)) = 0 or length(p_text) > 4000 then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_TEXT';
    end if;
    if p_canonical is null or length(btrim(p_canonical)) = 0
       or length(p_canonical) > 1000 then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_CANONICAL';
    end if;
    if p_domain not in ('health', 'election', 'government', 'finance', 'education', 'other')
       or p_language not in ('en', 'ne', 'romanized', 'mixed') then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_CLASSIFICATION';
    end if;
    -- The vector(768) argument type rejects any other dimension before entry.
    if p_embedding is null then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_EMBEDDING';
    end if;
    if p_match_threshold < 0 or p_match_threshold > 1
       or p_match_window_days < 1 then
        raise exception using errcode = '22023', message = 'INGEST_INVALID_LIMITS';
    end if;

    -- Same lock key as public.ingest_claim_atomic: user submissions and
    -- news promotions must serialize together (see NOTE ON DUPLICATION).
    perform pg_advisory_xact_lock(hashtext('public.ingest_claim_atomic'));

    select v.claim_id, v.id, 1 - (v.embedding OPERATOR(extensions.<=>) p_embedding)
    into v_claim_id, v_parent_id, v_similarity
    from public.variants v
    where v.embedding is not null
      and v.created_at >= now() - make_interval(days => p_match_window_days)
      and 1 - (v.embedding OPERATOR(extensions.<=>) p_embedding) >= p_match_threshold
    order by v.embedding OPERATOR(extensions.<=>) p_embedding, v.created_at, v.id
    limit 1;

    if v_claim_id is null then
        insert into public.claims (
            canonical, domain, language, label, verdict, rationale, source
        ) values (
            btrim(p_canonical), p_domain, p_language, 'UNVERIFIED', 'UNVERIFIED',
            'No claim-specific evidence has been inspected; human verification is required.',
            coalesce(nullif(p_source, ''), 'news')
        )
        returning id into v_claim_id;
    else
        v_matched := true;
    end if;

    insert into public.variants (
        claim_id, text, embedding, platform, ts, parent_id, mutation_type,
        verdict, rationale, source, language
    ) values (
        v_claim_id, btrim(p_text), p_embedding, coalesce(nullif(p_platform, ''), 'news'),
        coalesce(p_ts, now()), v_parent_id,
        case when v_matched then 'paraphrase' else 'original' end,
        'UNVERIFIED',
        'No claim-specific evidence has been inspected; human verification is required.',
        coalesce(nullif(p_source, ''), 'news'), p_language
    )
    returning id into v_variant_id;

    select count(*) into v_variant_count
    from public.variants v where v.claim_id = v_claim_id;

    return query select v_claim_id, v_variant_id, v_parent_id, v_matched,
        v_similarity, v_variant_count;
end
$$;

revoke all on function public.ingest_external_claim_atomic(
    text, text, text, text, vector, text, text, timestamptz,
    double precision, integer
) from public, anon, authenticated;
grant execute on function public.ingest_external_claim_atomic(
    text, text, text, text, vector, text, text, timestamptz,
    double precision, integer
) to service_role;

-- ------------------------------------------------------------
-- Windowed rankings and claim-detail analytics.
-- Counts always represent observed variant timestamps, never audience reach.
-- ------------------------------------------------------------
create or replace function public.claim_rankings(
    p_period text,
    p_tier text,
    p_limit integer default 20
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = public
as $$
declare
    v_window interval;
    v_now timestamptz := now();
    v_result jsonb;
begin
    v_window := case p_period
        when 'day' then interval '1 day'
        when 'week' then interval '7 days'
        when 'month' then interval '1 month'
        when 'year' then interval '1 year'
        else null
    end;
    if v_window is null then raise exception 'invalid period'; end if;
    if p_tier not in ('VERIFIED_FALSE', 'AI_FLAGGED') then
        raise exception 'invalid tier';
    end if;

    with latest_assessment as (
        select distinct on (a.claim_id) a.*
        from claim_assessments a
        where a.tier = p_tier
        order by a.claim_id, a.assessed_at desc
    ), activity as (
        select c.id, c.canonical, c.domain, c.language, c.source,
               a.tier, a.verdict, a.confidence, a.rationale, a.model,
               a.assessed_at, a.evidence_url, a.evidence_title,
               count(v.id) filter (where v.ts >= v_now - v_window and v.ts <= v_now) current_count,
               count(v.id) filter (where v.ts >= v_now - v_window - v_window and v.ts < v_now - v_window) previous_count,
               min(v.ts) first_seen, max(v.ts) last_seen
        from latest_assessment a
        join claims c on c.id = a.claim_id
        left join variants v on v.claim_id = c.id
        group by c.id, a.id, a.tier, a.verdict, a.confidence, a.rationale,
                 a.model, a.assessed_at, a.evidence_url, a.evidence_title
    )
    select coalesce(jsonb_agg(to_jsonb(r) order by r.current_count desc,
        r.percent_change desc nulls last, r.last_seen desc nulls last), '[]'::jsonb)
    into v_result
    from (
        select *, case when previous_count = 0 then null
            else round(((current_count - previous_count)::numeric / previous_count) * 100, 1)
            end percent_change
        from activity
        where current_count > 0
        order by current_count desc, percent_change desc nulls last, last_seen desc nulls last
        limit greatest(1, least(p_limit, 100))
    ) r;
    return v_result;
end;
$$;

create or replace function public.claim_spread_analytics(
    p_claim_id uuid,
    p_period text
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = public
as $$
declare
    v_window interval;
    v_now timestamptz := now();
    v_start timestamptz;
    v_result jsonb;
begin
    v_window := case p_period
        when 'day' then interval '1 day'
        when 'week' then interval '7 days'
        when 'month' then interval '1 month'
        when 'year' then interval '1 year'
        else null
    end;
    if v_window is null then raise exception 'invalid period'; end if;
    v_start := v_now - v_window;

    with selected as (
        select * from variants where claim_id = p_claim_id
    ), daily as (
        select date_trunc('day', ts)::date as bucket_day,
               count(*)::integer as observed_count
        from selected where ts >= v_start and ts <= v_now group by 1 order by 1
    ), timeline as (
        select bucket_day, observed_count,
               sum(observed_count) over (order by bucket_day)::integer as cumulative_count
        from daily
    ), distributions as (
        select
          (select coalesce(jsonb_agg(jsonb_build_object('label', platform_name, 'count', item_count)), '[]'::jsonb)
           from (select coalesce(platform, 'unknown') as platform_name, count(*)::integer as item_count from selected group by 1 order by 2 desc) x) platforms,
          (select coalesce(jsonb_agg(jsonb_build_object('label', language_name, 'count', item_count)), '[]'::jsonb)
           from (select coalesce(language, 'unknown') as language_name, count(*)::integer as item_count from selected group by 1 order by 2 desc) x) languages,
          (select coalesce(jsonb_agg(jsonb_build_object('label', mutation_name, 'count', item_count)), '[]'::jsonb)
           from (select coalesce(mutation_type, 'unknown') as mutation_name, count(*)::integer as item_count from selected group by 1 order by 2 desc) x) mutations
    )
    select jsonb_build_object(
        'summary', jsonb_build_object(
            'first_seen', min(s.ts), 'last_seen', max(s.ts),
            'observed_variants', count(s.id),
            'current_count', count(s.id) filter (where s.ts >= v_start and s.ts <= v_now),
            'previous_count', count(s.id) filter (where s.ts >= v_start - v_window and s.ts < v_start),
            'top_platform', (select platform from (select coalesce(platform, 'unknown') platform, count(*) n from selected group by 1 order by n desc limit 1) p)
        ),
        'timeline', (select coalesce(jsonb_agg(jsonb_build_object(
            'date', bucket_day, 'count', observed_count,
            'cumulative', cumulative_count
        ) order by bucket_day), '[]'::jsonb) from timeline),
        'platforms', d.platforms, 'languages', d.languages, 'mutations', d.mutations,
        'top_variants', (select coalesce(jsonb_agg(to_jsonb(t)), '[]'::jsonb) from (select id, text, platform, language, mutation_type, ts, source, confidence, evidence_url, evidence_title from selected order by ts desc nulls last limit 20) t)
    ) into v_result
    from selected s cross join distributions d
    group by d.platforms, d.languages, d.mutations;
    return coalesce(v_result, jsonb_build_object('summary', jsonb_build_object('observed_variants', 0, 'current_count', 0, 'previous_count', 0), 'timeline', '[]'::jsonb, 'platforms', '[]'::jsonb, 'languages', '[]'::jsonb, 'mutations', '[]'::jsonb, 'top_variants', '[]'::jsonb));
end;
$$;

grant execute on function public.claim_rankings(text, text, integer) to anon, authenticated, service_role;
grant execute on function public.claim_spread_analytics(uuid, text) to anon, authenticated, service_role;
