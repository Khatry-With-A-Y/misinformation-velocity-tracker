-- ============================================================
-- Misinformation Velocity Tracker — Supabase schema
-- Run this once in the Supabase SQL editor.
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
alter table public.variants enable row level security;
alter table public.variants force row level security;
alter table public.claim_submissions enable row level security;
alter table public.claim_submissions force row level security;

drop policy if exists claims_public_read on public.claims;
create policy claims_public_read on public.claims
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
    p_match_threshold double precision default 0.85,
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
