# Misinformation Velocity Tracker — Backend (FastAPI + Supabase)

FastAPI service that powers claim ingestion, the mutation tree, velocity, and
the explainable verdict. Structure follows a clean `app/` layout (adapted from
the `fastapi-react-starter`), with Supabase as the database + auth provider
(adapted from `fastapi-supabase-starter`) and the dataset/AI pipeline folded in.

## Layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, routers under /api
│   ├── config/config.py        # pydantic-settings (Supabase + Gemini + limits)
│   ├── core/supabase.py        # Supabase clients + insert helpers + JWT auth
│   ├── routes/
│   │   ├── health.py           # GET /api/health
│   │   ├── auth.py             # Supabase sign-up / sign-in / me
│   │   └── claims.py           # ingest + tree + velocity + platforms
│   ├── schemas/                # pydantic request/response models
│   ├── services/
│   │   ├── embeddings.py       # Gemini multilingual embeddings
│   │   ├── variant_generator.py# synthetic variants (tree + velocity fuel)
│   │   ├── tree.py             # mutation-tree reconstruction
│   │   ├── source_router.py    # domain -> trusted Nepali sources
│   │   └── pipeline.py         # ingest/tree/velocity/platforms orchestration
│   ├── data/
│   │   ├── loaders/            # nepoc / misdetect / chhatramani + common
│   │   ├── load_all.py         # dataset loader orchestrator (CLI)
│   │   └── verify_supabase.py  # schema + insert round-trip check
│   └── utils/logger.py
├── schema.sql                  # claims + variants (pgvector) + match_variants RPC
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | health check |
| POST | `/api/auth/register` | Supabase sign-up → `{ access_token }` |
| POST | `/api/auth/login` | Supabase sign-in → `{ access_token }` |
| GET | `/api/auth/me` | current user (Bearer token) |
| POST | `/api/claims/ingest` | `{ text }` → extract + embed + store + verdict |
| GET | `/api/claims` | list recent claims |
| GET | `/api/claims/{id}/tree` | mutation tree `{ nodes, edges }` |
| GET | `/api/claims/{id}/velocity` | variants-per-day `[{ bucket, count }]` |
| GET | `/api/claims/{id}/platforms` | platform breakdown `[{ platform, count }]` |

## Demo auth model

- The dashboard is intentionally public for hackathon/demo usability: open
  `http://localhost:5173/dashboard` without signing in to use the core claim
  analysis flow.
- No default logins exist in this repository. Do not expect a built-in demo
  email or password.
- Optional accounts are still supported through the Supabase-backed
  `POST /api/auth/register` and `POST /api/auth/login` routes when Supabase Auth
  is configured for the environment.
- Backend auth routes are retained for future private features, but the current
  claim ingestion, list, tree, velocity, and platform endpoints remain public.

## Setup

1. **Create a Supabase project**, then run `schema.sql` in the SQL editor
   (enables `pgvector`, creates/updates tables + the `match_variants` RPC).
2. **Configure env:**
   ```powershell
   Copy-Item .env.example .env
   # edit .env: SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY,
   #            SUPABASE_JWT_SECRET, GEMINI_API_KEY
   ```
   > `EMBEDDING_DIM` must match the `vector(768)` size in `schema.sql`.
3. **Build and run the API with Docker Compose:**
   ```powershell
   docker compose build --no-cache
   docker compose up
   ```
   Swagger UI: http://localhost:8000/docs

4. **Verify Supabase schema and basic inserts:**
   ```powershell
   docker compose exec backend python -m app.data.verify_supabase
   ```
   If this reports a missing column, re-run `schema.sql` in the Supabase SQL editor and run the check again.
   The check confirms `claims`, `variants`, `match_variants`, `vector(768)`, and a minimal claim/variant insert-read-cleanup round trip.

## Seed the datasets

Run from the `backend/` directory:

```powershell
docker compose exec backend python -m app.data.load_all --preview              # validate dataset normalization only
docker compose exec backend python -m app.data.load_all --all --replace-source # safely restore all dataset slices
docker compose exec backend python -m app.data.load_all --nepoc                # real Nepal dates + evidence
docker compose exec backend python -m app.data.load_all --misdetect            # verdict/rationale slice
docker compose exec backend python -m app.data.load_all --chhatramani --generate # roots + synthetic mutation tree
```

`--replace-source` deletes only claims owned by each selected Hugging Face
dataset before reloading it. Demo, user-submitted, and realtime news records are
preserved. Synthetic Chhatramani variants are generated only when `--generate`
is explicitly supplied because generation consumes additional Gemini quota.

The **datasets provide credibility** (real Nepali claims, dates, verdicts); the
**variant generator provides the spread structure** (platform, timestamp,
parent lineage) that the mutation tree and velocity chart are built from.

## Notes

- Loaders tolerate column-name variance (`app/data/loaders/common.py`).
- Keep `NEPOC_CLAIM_GROUPS` / `MISDETECT_ROWS_PER_DOMAIN` /
  `CHHATRAMANI_ROOT_CLAIMS` small — a demo needs a believable graph, not scale.
  If `--misdetect` reports hundreds of rows, lower `MISDETECT_ROWS_PER_DOMAIN`
  in `backend/.env`; Docker Compose loads the real `.env` value over the code default.
- The **service-role key** bypasses RLS — keep `.env` server-side, never ship
  it to the frontend. Auth uses the **anon key**.
- Confirm the **NepOOC license** before redistributing its rows publicly.
- Tests: `pytest` (a health smoke test is included).
