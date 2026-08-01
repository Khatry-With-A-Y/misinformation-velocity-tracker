# Misinformation Velocity Tracker

A full-stack platform that detects, traces, and visualizes how misinformation
mutates and spreads across platforms. Users (or an automated news poller) submit
a claim; the backend extracts and embeds it, matches it against known variants,
reconstructs a **mutation tree**, computes its **spread velocity**, and returns
an **explainable verdict**. The frontend renders this as an interactive
dashboard — mutation graph, velocity timeline, platform breakdown, and live
claim ranking.

## Quick Summary

- **Problem:** misinformation spreads by mutating — small wording changes across
  platforms make it hard to see that many "different" claims are really the
  same rumor evolving.
- **Solution:** ingest a claim, embed it with Gemini, match it against stored
  variants with pgvector similarity search, and rebuild the mutation
  lineage (who copied/changed what, and when).
- **Output:** a public dashboard showing the mutation tree, how fast a claim is
  spreading (velocity), which platforms it appears on, and a verdict with
  supporting evidence from trusted Nepali sources.

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | React 19 + TypeScript + Vite | Dashboard UI, routing, data fetching |
| Frontend | Tailwind CSS 4 + Radix UI | Styling and accessible UI primitives |
| Frontend | React Flow | Renders the interactive mutation tree graph |
| Frontend | Recharts | Velocity timeline and platform breakdown charts |
| Frontend | React Router | Client-side routing (dashboard, auth pages) |
| Backend | FastAPI (Python) | REST API under `/api`, request validation, CORS |
| Backend | Pydantic / pydantic-settings | Request/response schemas and typed config |
| Backend | Google Gemini (`google-genai`) | Multilingual text embeddings + claim extraction |
| Backend | feedparser | RSS polling for real-time news ingestion |
| Backend | pandas / datasets (Hugging Face) | Loading and normalizing seed claim datasets |
| Database | Supabase (PostgreSQL) | Primary data store: claims, variants, users |
| Database | pgvector | Vector similarity search over claim/variant embeddings |
| Database | Supabase Auth | Optional user sign-up/sign-in (JWT-based) |
| Infra | Docker Compose | Orchestrates `backend`, `news-poller`, and `frontend` services |

### How each part is used

- **Frontend (React + Vite):** talks to the backend over `VITE_API_URL`
  (`http://localhost:8000` in Docker Compose). It renders the public
  `/dashboard` where claims can be submitted and explored: `MutationExplorer`
  draws the mutation tree with React Flow, `SpreadTimeline` charts velocity
  with Recharts, and `BreakdownPanels`/`RankingTable` show platform and claim
  rankings. Auth pages exist for optional Supabase-backed login, but the core
  flow is usable without signing in.
- **Backend (FastAPI):** exposes the `/api` routes that back the dashboard.
  `routes/claims.py` handles ingest, tree, velocity, and platform breakdown;
  `routes/news.py` and `workers/news_poller.py` continuously pull real news via
  RSS and feed it through the same pipeline; `routes/auth.py` proxies to
  Supabase Auth. `services/pipeline.py` orchestrates extraction → embedding
  (`services/embeddings.py`, Gemini) → variant matching → tree reconstruction
  (`services/tree.py`) for every ingested claim.
- **Database (Supabase/PostgreSQL + pgvector):** stores `claims` and `variants`
  tables (see `backend/schema.sql`), with `pgvector` embeddings and a
  `match_variants` RPC used for nearest-neighbor similarity search that links a
  new claim to its mutation ancestors. Supabase also provides authentication
  (JWT) via the anon/service-role keys, and dataset loaders in
  `backend/app/data/` seed it with real claim data from Hugging Face datasets
  (NepOOC, MisDetect, Chhatramani) for demo purposes.

## Project Structure

```
Overclocked/
├── docker-compose.yml       # orchestrates backend, news-poller, frontend
├── backend/                 # FastAPI service (see backend/README.md)
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, routers under /api
│   │   ├── config/          # pydantic-settings (Supabase + Gemini + limits)
│   │   ├── core/supabase.py # Supabase clients + insert helpers + JWT auth
│   │   ├── routes/          # health, auth, claims, news, analytics
│   │   ├── schemas/         # pydantic request/response models
│   │   ├── services/        # embeddings, variant generation, tree, pipeline
│   │   ├── data/            # dataset loaders + Supabase verification script
│   │   └── workers/         # background news poller
│   ├── schema.sql           # claims + variants (pgvector) + match_variants RPC
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/                 # React + Vite dashboard
    ├── src/
    │   ├── components/dashboard/ # mutation tree, timeline, rankings, filters
    │   ├── components/ui/         # shared UI primitives (buttons, cards, etc.)
    │   ├── features/auth/         # optional login/register forms
    │   ├── features/health/       # backend health/loading states
    │   ├── context/               # app + auth React contexts
    │   ├── hooks/                 # health status, loading state hooks
    │   └── lib/api.ts             # API client
    ├── package.json
    └── Dockerfile
```

## API Overview

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

Full endpoint list, including news and analytics routes, is discoverable via
the interactive Swagger docs at `http://localhost:8000/docs` once the backend
is running.

## Installation & Setup

### Prerequisites

- Docker and Docker Compose
- A [Supabase](https://supabase.com) project (for database + auth)
- A Google Gemini API key (for embeddings)

### 1. Create the Supabase project

Run `backend/schema.sql` in the Supabase SQL editor. This enables `pgvector`
and creates/updates the `claims`/`variants` tables plus the `match_variants` RPC.

### 2. Configure environment variables

```powershell
Copy-Item backend/.env.example backend/.env
# edit backend/.env: SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY,
#                    SUPABASE_JWT_SECRET, GEMINI_API_KEY
```

> `EMBEDDING_DIM` in `backend/.env` must match the `vector(768)` size in `schema.sql`.

Copy the frontend env file as well if you need to customize the API URL:

```powershell
Copy-Item frontend/.env.example frontend/.env
```

### 3. Build and run everything with Docker Compose

From the project root:

```powershell
docker compose build --no-cache
docker compose up
```

This starts three services:

- `backend` — FastAPI on `http://localhost:8000` (Swagger UI at `/docs`)
- `news-poller` — background worker that continuously ingests real news via RSS
- `frontend` — React dashboard on `http://localhost:5173`

Open `http://localhost:5173/dashboard` — it's public by design for demo/hackathon
usability, no sign-in required for the core claim-analysis flow.

### 4. Verify the Supabase schema

```powershell
docker compose exec backend python -m app.data.verify_supabase
```

If this reports a missing column, re-run `schema.sql` in the Supabase SQL
editor and run the check again. It confirms `claims`, `variants`,
`match_variants`, `vector(768)`, and a minimal insert-read-cleanup round trip.

### 5. Seed sample datasets (optional)

```powershell
docker compose exec backend python -m app.data.load_all --preview              # validate normalization only
docker compose exec backend python -m app.data.load_all --all --replace-source # restore all dataset slices
docker compose exec backend python -m app.data.load_all --nepoc                # real Nepal dates + evidence
docker compose exec backend python -m app.data.load_all --misdetect            # verdict/rationale slice
docker compose exec backend python -m app.data.load_all --chhatramani --generate # roots + synthetic mutation tree
```

`--replace-source` deletes only claims owned by each selected Hugging Face
dataset before reloading it; demo, user-submitted, and realtime news records
are preserved. Synthetic Chhatramani variants are generated only when
`--generate` is supplied, since generation consumes Gemini quota.

### Running without Docker (optional)

**Backend:**

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```powershell
cd frontend
npm install
npm run dev
```
