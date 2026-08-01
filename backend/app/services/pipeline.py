"""End-to-end claim pipeline used by the API.

ingest -> extract core claim + domain (Gemini) -> embed -> store in Supabase
-> reconstruct lineage -> serve mutation tree / velocity / platform breakdown
-> suggest research destinations without treating them as evidence.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

from google import genai
from google.genai import types

from app.config import get_settings
from app.core import supabase as db
from app.services import embeddings
from app.services.source_router import research_resources_for
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_ALLOWED_DOMAINS = {"health", "election", "government", "finance", "education", "other"}
_ALLOWED_LANGUAGES = {"en", "ne", "romanized", "mixed"}
_SUBMISSION_VERDICT = "UNVERIFIED"
_SUBMISSION_RATIONALE = (
    "No claim-specific evidence has been inspected; human verification is required."
)

_EXTRACT_PROMPT = """You are helping fact-checkers in Nepal.
Given a raw message (Nepali Devanagari, Romanized Nepali, English, or mixed),
extract its core factual claim and classify its topic and language. Do not
assess whether the claim is true or false.

IMPORTANT: Always translate the canonical claim into English regardless of the
input language. This ensures that semantically identical claims in different
languages (e.g. "Tato pani le dengue hunchha" and "Drinking hot water cures
dengue fever") produce the same canonical form.

MESSAGE:
{text}

Return ONLY JSON with these exact keys:
{{
  "canonical": "the normalized core factual claim translated into English",
  "domain": "health | election | government | finance | education | other",
  "language": "en | ne | romanized | mixed"
}}"""


def _extract(text: str) -> dict:
    """Extract and validate non-verdict claim metadata via Gemini."""
    try:
        resp = _client.models.generate_content(
            model=settings.GENERATION_MODEL,
            contents=_EXTRACT_PROMPT.format(text=text[:4000]),
            config=types.GenerateContentConfig(
                temperature=0.2, response_mime_type="application/json"
            ),
        )
        data = json.loads(resp.text)
        if isinstance(data, dict):
            canonical = data.get("canonical")
            if isinstance(canonical, str) and canonical.strip():
                domain = str(data.get("domain", "other")).lower()
                language = str(data.get("language", "mixed")).lower()
                return {
                    "canonical": canonical.strip()[:1000],
                    "domain": domain if domain in _ALLOWED_DOMAINS else "other",
                    "language": (
                        language if language in _ALLOWED_LANGUAGES else "mixed"
                    ),
                }
    except Exception:
        logger.warning("Claim extraction via Gemini failed; falling back to raw text", exc_info=True)
    # Graceful fallback: treat the raw text as the unverified claim.
    return {
        "canonical": text.strip()[:1000],
        "domain": "other",
        "language": "mixed",
    }


def ingest_claim(
    text: str,
    access_token: str,
    *,
    match_threshold: float = 0.85,
    match_window_days: int = 3650,
    rate_limit: int = 10,
    rate_window_minutes: int = 60,
) -> dict:
    """Ingest a raw submission without issuing an unsupported factual verdict."""
    info = _extract(text)
    now = datetime.now(timezone.utc).isoformat()
    embedding = embeddings.embed_text(info["canonical"])
    ingestion = db.ingest_claim_atomic(access_token, {
        "p_text": text.strip(),
        "p_canonical": info["canonical"],
        "p_domain": info["domain"],
        "p_language": info["language"],
        "p_embedding": embedding,
        "p_platform": "submission",
        "p_ts": now,
        "p_match_threshold": match_threshold,
        "p_match_window_days": match_window_days,
        "p_rate_limit": rate_limit,
        "p_rate_window_minutes": rate_window_minutes,
    })

    return {
        "id": ingestion["claim_id"],
        "variant_id": ingestion["variant_id"],
        "parent_id": ingestion.get("parent_id"),
        "matched": ingestion["matched"],
        "similarity": ingestion.get("similarity"),
        "canonical": info["canonical"],
        "domain": info.get("domain"),
        "language": info.get("language"),
        "label": _SUBMISSION_VERDICT,
        "verdict": _SUBMISSION_VERDICT,
        "rationale": _SUBMISSION_RATIONALE,
        "research_resources": research_resources_for(info.get("domain")),
        "variant_count": ingestion["variant_count"],
    }


def list_claims(limit: int = 100, page: int | None = None, query: str | None = None,
                source: str | None = None, domain: str | None = None,
                language: str | None = None, tier: str | None = None,
                period: str | None = None,
                platform: str | None = None) -> list[dict] | dict:
    """Return bounded tracked-claim context with an opt-in page envelope."""
    offset = ((page or 1) - 1) * limit
    result = db.get_anon_client().rpc("claim_list_context", {
        "p_limit": limit,
        "p_offset": offset,
        "p_query": query,
        "p_source": source,
        "p_domain": domain,
        "p_language": language,
        "p_tier": tier.upper() if tier else None,
        "p_period": period,
        "p_platform": platform,
    }).execute()
    payload = result.data or {"items": [], "total": 0}
    items = payload.get("items") or []
    if page is None:
        return items
    total = int(payload.get("total") or 0)
    return {
        "items": items,
        "total": total,
        "next_cursor": str(page + 1) if offset + len(items) < total else None,
    }


def _fetch_variants(claim_id: str) -> list[dict]:
    res = (
        db.get_anon_client()
        .table("variants")
        .select(
            "id,text,platform,ts,parent_id,mutation_type,language,source,"
            "confidence,evidence_url,evidence_title"
        )
        .eq("claim_id", claim_id)
        .execute()
    )
    return res.data or []


def get_tree(claim_id: str) -> dict:
    """Build a React-Flow-friendly mutation tree for a claim."""
    variants = _fetch_variants(claim_id)
    ids = {v["id"] for v in variants}
    nodes, edges = [], []
    for v in variants:
        text = v.get("text") or ""
        nodes.append({
            "id": v["id"],
            "label": text[:80] + ("…" if len(text) > 80 else ""),
            "text": text,
            "platform": v.get("platform"),
            "ts": v.get("ts"),
            "mutation_type": v.get("mutation_type"),
            "language": v.get("language"),
            "source": v.get("source"),
            "confidence": v.get("confidence"),
            "evidence_url": v.get("evidence_url"),
            "evidence_title": v.get("evidence_title"),
        })
        parent = v.get("parent_id")
        if parent and parent in ids:
            edges.append({"source": parent, "target": v["id"]})
    return {"nodes": nodes, "edges": edges}


def _parse_day(ts) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(
            str(ts).replace("Z", "+00:00")
        ).date().isoformat()
    except ValueError:
        return None


def get_velocity(claim_id: str) -> list[dict]:
    """Count variants per day -> velocity-over-time line chart."""
    variants = _fetch_variants(claim_id)
    buckets: dict[str, int] = defaultdict(int)
    for v in variants:
        day = _parse_day(v.get("ts"))
        if day:
            buckets[day] += 1
    return [{"bucket": d, "count": buckets[d]} for d in sorted(buckets)]


def get_platforms(claim_id: str) -> list[dict]:
    """Count variants per platform -> platform breakdown chart."""
    variants = _fetch_variants(claim_id)
    counts = Counter(v.get("platform") or "unknown" for v in variants)
    return [{"platform": p, "count": c} for p, c in counts.most_common()]
