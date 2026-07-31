### Audit result

The codebase is small and readable, with sensible separation between routes, services, schemas, loaders, and database integration. However, several issues prevent it from reliably delivering its stated purpose.

### Critical findings

1. **Submissions never join an existing claim tree** — `pipeline.ingest_claim()` always inserts a new claim and one variant (`backend/app/services/pipeline.py:65-105`). The `match_variants` RPC is never called. Repeated versions of the same claim therefore create separate one-node trees instead of tracking spread.

2. **The “verdict” is unsupported AI output** — `_extract()` asks Gemini to declare `FAKE`, `REAL`, or `UNVERIFIED` without retrieving evidence (`pipeline.py:23-52`). `sources_for()` only returns generic links; it does not inspect them. Presenting this as an explainable fact-check risks confidently generating misinformation.

3. **Database access bypasses all user authorization** — claim routes are unauthenticated and use the service-role Supabase client (`routes/claims.py`, `core/supabase.py:22-34`). Anyone reaching the API can ingest and enumerate data. No rate limiting or ownership model exists.

4. **Supabase tables have no RLS policies** — `schema.sql` does not enable row-level security. Depending on Supabase grants, direct anon access may expose or permit modification of data.

### High-priority bugs

5. **Partial writes leave orphan claims** — the claim is committed before embedding and variant insertion (`pipeline.py:68-89`). Gemini or Supabase failure leaves a claim with no variant because there is no transaction or cleanup.

6. **Claim rationale is silently discarded** — `ingest_claim()` does not pass `rationale` to `insert_claim()` (`pipeline.py:68-74`), although it returns the rationale to the caller. Reloading the claim loses that explanation.

7. **Internal errors leak to clients** — claim endpoints return `detail=str(e)` (`routes/claims.py:24-62`), potentially exposing database, configuration, or provider details.

8. **Blocking I/O inside async endpoints** — synchronous Supabase and Gemini calls run directly inside `async` route handlers. Under load, one slow external request blocks the event loop.

9. **Authentication assumptions are brittle** — JWT validation is hard-coded to `HS256` and a shared secret (`core/supabase.py:93-98`). It cannot handle projects configured with asymmetric signing keys/JWKS and lacks explicit issuer validation.

### Data and algorithm issues

10. `_cosine()` silently truncates mismatched vectors through `zip()` (`services/tree.py:16-24`) instead of rejecting invalid dimensions.
11. Equal timestamps can create arbitrary lineage based on insertion order; invalid timestamps sort last and can become parents of other invalid-timestamp rows.
12. The similarity reconstruction performs `O(n² × dimensions)` work and executes one database update per edge.
13. Generated `parent_index` values are insufficiently validated; forward/self references can be stored as expected parents (`load_all.py:97-102`).
14. `expected_parent_id` has no foreign key, unlike `parent_id` (`schema.sql:46`).
15. Schema columns lack useful constraints: `claim_id` is nullable, labels/domains/platforms are unrestricted, and timestamps/identifiers have no validation.
16. `list_claims()` claims to provide summaries but does not calculate `variant_count`; the declared `ClaimSummary` model is unused.
17. Tree, velocity, and platform endpoints return empty success responses for nonexistent claim IDs instead of `404`.
18. Dataset loads and seeding are not idempotent, so reruns create duplicates.

### Maintainability and operations

- The README says a health smoke test exists, but there are **no test files**. Core extraction, lineage, normalization, authentication, and failure recovery are untested.
- `API_PREFIX` exists but routers hard-code `/api`; many database/JWT settings are unused (`config.py`).
- AI clients are initialized at import time even when keys are absent, making local tests and health-only deployments fragile.
- The Docker image runs production traffic with `--reload`, mounts source code, runs as root, and installs compilers/runtime build dependencies in the final image.
- The health endpoint checks only the process, not required Supabase/Gemini readiness.
- Broad exception swallowing in `_extract()` and `embed_batch()` hides provider and parsing failures.
- Logger setup removes handlers repeatedly and leaves propagation enabled, which may duplicate output under Uvicorn.
- API request sizes, password length, generated AI fields, and configured numeric limits are not bounded or validated.

### Recommended order

1. Make ingestion match existing variants/claims before inserting, then append to the matched claim.
2. Stop treating an LLM classification as a factual verdict; retrieve and cite evidence or return `UNVERIFIED`.
3. Add authentication/authorization, rate limiting, RLS, and sanitized error handling.
4. Make claim-plus-variant persistence transactional or compensate on failure.
5. Add unit tests for normalization/tree logic and API tests for auth, ingestion, missing IDs, and provider failures.
6. Add schema constraints, deduplication, pagination, and indexes such as `(claim_id, ts)`.
7. Move blocking provider calls to synchronous endpoints/threadpool or adopt async clients.
8. Harden the container and separate liveness from dependency readiness.

No files were modified and no external-service tests were run; this was a static review of all source, configuration, schema, and documentation files.