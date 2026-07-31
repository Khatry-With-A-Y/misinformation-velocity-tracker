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
-- Indexes
-- ------------------------------------------------------------
create index if not exists variants_claim_id_idx on variants(claim_id);
create index if not exists variants_ts_idx on variants(ts);

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
as $$
    select
        v.id,
        v.claim_id,
        v.text,
        v.platform,
        v.ts,
        1 - (v.embedding <=> query_embedding) as similarity
    from variants v
    where v.embedding is not null
      and 1 - (v.embedding <=> query_embedding) > match_threshold
    order by v.embedding <=> query_embedding
    limit match_count;
$$;
