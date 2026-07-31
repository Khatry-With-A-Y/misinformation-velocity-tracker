# Misinformation Velocity Tracker

> Track how a claim spreads and mutates across public platforms in Nepal — not just whether a single message looks suspicious.

The Misinformation Velocity Tracker is a tool for **journalists and fact-checkers**. Instead of checking one message in isolation, it reconstructs how a claim propagates over time, how its wording evolves ("mutates") across platforms, how fast it travels (**velocity**), and gives a **verdict + priority score** so newsrooms know what to debunk first.

---

## Summary

Most misinformation tools answer *"is this message a scam?"*. This project answers a more useful question for media professionals:

> *"Where did this claim come from, how is it changing, how fast is it spreading, and how urgent is it?"*

Paste or seed a claim → the pipeline finds its variants, builds a **mutation tree**, plots a **velocity-over-time** chart, breaks spread down **by platform**, and produces an **explainable verdict** routed through trusted Nepali sources — all with full **Nepali + English** support (Devanagari, Romanized Nepali, and mixed text).

---

## Features

- **Claim ingestion** — paste text, upload an image/screenshot, or seed from monitored/curated sources.
- **Mutation tree** — reconstructs claim lineage (parent → child variants) from embedding similarity + timestamps.
- **Velocity chart** — variants-per-time-bucket shows how fast a claim is spreading.
- **Platform breakdown** — see where a claim lives (Facebook, TikTok, X, YouTube, WhatsApp submissions).
- **Similarity search** — multilingual `pgvector` cosine search finds variants of the same claim.
- **Domain-based Source Router** — maps claim domain (health, election, government, finance) to trusted Nepali sources.
- **Explainable verdict card** — verdict + rationale + confidence + fact-check evidence URLs, with a *"Unverified – needs human review"* fallback.
- **Priority / risk score** — weighted formula (velocity × reach × domain-sensitivity × verdict-confidence) to triage what to debunk first.
- **Nepali + English** — multilingual embeddings + LLM reasoning handle Devanagari, Romanized Nepali, English, and mixed text.
- **Live submission form** — a "Report a claim" box writes into the same pipeline (the WhatsApp story, without scraping private groups).

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend / API** | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| **Database** | [Supabase](https://supabase.com/) Postgres + [`pgvector`](https://github.com/pgvector/pgvector) |
| **Auth / Storage / Realtime** | Supabase Auth, Storage, Realtime |
| **AI — embeddings** | Google Gemini `gemini-embedding-001` (multilingual) |
| **AI — reasoning / extraction** | Google Gemini `gemini-1.5-flash` |
| **Vector search** | `pgvector` cosine similarity via Supabase RPC (`match_variants`) |
| **Frontend** | React + Vite + Tailwind CSS |
| **Graph visualization** | React Flow (mutation tree) |
| **Charts** | Recharts (velocity + platform breakdown) |
| **Data pipeline** | `datasets`, `pandas`, `tenacity` |

---

## Architecture


flowchart TD
    A[Ingest claim: text / image / seed row] --> B[Gemini: extract core claim + domain]
    B --> C[Gemini embedding -> vector]
    C --> D[pgvector similarity search in Supabase]
    D --> E[Cluster variants + build mutation tree by time + similarity]
    E --> F[Compute velocity + platform reach + priority score]
    F --> G[Source Router: domain -> trusted sources -> Gemini verdict]
    G --> H[React dashboard: tree + velocity chart + verdict]


The data is **seeded** from real Nepali fact-check datasets, but the analysis (embeddings, clustering, tree reconstruction, velocity) is **100% real**.

---

## Datasets

Root claims and verdicts draw on **real Nepali fact-check datasets**; spread dynamics (platform, timing, mutation lineage) are reconstructed by the pipeline and augmented with live submissions.

| Dataset | Role |
|---|---|
| [`theonlysanjeev/nepal-ooc-misinformation`](https://huggingface.co/datasets/theonlysanjeev/nepal-ooc-misinformation) (NepOOC) | Real `posted_date` (velocity slice) + fact-check `article_url` evidence + entities |
| [`cair-nepal/MisDetect-CAIR`](https://huggingface.co/datasets/cair-nepal/MisDetect-CAIR) | `rationale` + `claim_type` + confidence for the verdict card (MIT licensed) |
| [`chhatramani/nepali-fake-news-dataset-v1`](https://huggingface.co/datasets/chhatramani/nepali-fake-news-dataset-v1) | Labeled Nepali (Devanagari) root claims by domain |
| **Gemini variant generator** | Synthetic variants w/ platform + timestamp + parent hints — the engine of the mutation tree + velocity |

> Confirm the NepOOC license before redistributing it in a public repo/demo.

---

## Project Structure

```
.
├── backend/
│   ├── config.py            # env-based configuration
│   ├── db.py                # Supabase client + insert helpers
│   ├── embeddings.py        # Gemini multilingual embeddings
│   ├── variant_generator.py # synthetic variant engine (tree + velocity fuel)
│   ├── tree.py              # parent/lineage reconstruction
│   ├── load_all.py          # dataset loader orchestrator (CLI)
│   ├── loaders/             # per-dataset loaders (nepoc, misdetect, chhatramani)
│   ├── schema.sql           # Supabase schema (claims, variants, match_variants RPC)
│   ├── requirements.txt
│   └── .env.example
└── frontend/                # React + Vite + Tailwind dashboard
```

---

## Getting the project started

### Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com/) project
- A [Google Gemini](https://ai.google.dev/) API key

### 1. Set up Supabase

Create a project, then run [`backend/schema.sql`](backend/schema.sql) once in the Supabase SQL editor. It enables `pgvector`, creates the `claims` + `variants` tables, indexes, and the `match_variants` similarity RPC.

### 2. Configure the backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

Fill in `.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Load the data

```bash
# everything: real datasets + synthetic variant generation
python load_all.py --all

# or pick sources
python load_all.py --chhatramani --generate   # Nepali roots + synthetic tree
python load_all.py --nepoc --misdetect         # real dates + verdict slice
```

### 4. Run the frontend

```bash
cd ../frontend
npm install
npm run dev
```

---

## Loader CLI

| Command | What it does |
|---|---|
| `python load_all.py --all` | Runs every loader + variant generation |
| `python load_all.py --chhatramani --generate` | Loads Nepali root claims and generates synthetic variants (mutation tree) |
| `python load_all.py --nepoc` | Loads NepOOC real dates + fact-check evidence |
| `python load_all.py --misdetect` | Loads a labeled MisDetect verdict/rationale slice |


---

## Roadmap

- Speech-to-text ingestion (Whisper) for WhatsApp voice notes
- Live platform connectors (Facebook Graph, YouTube Data API)
- Supabase Realtime auto-refreshing dashboard
- Redis / background workers for scheduled monitoring
- Journalist authentication + saved investigations

---

## Security Notes

- Never ship the Supabase **service-role** key to the frontend — it's server-side only (loaders/API).
- Keep API keys in `.env` (git-ignored), never hardcoded or committed.

---
## Team 

Utsab Pandit (Leader)
Shaswat Khatry (Co-leader)
Pritesh Raj Chaudhary
Tejash Shrestha




