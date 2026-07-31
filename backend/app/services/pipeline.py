"""End-to-end claim pipeline used by the API.

ingest -> extract core claim + domain (Gemini) -> embed -> store in Supabase
-> reconstruct lineage -> serve mutation tree / velocity / platform breakdown
-> explainable verdict routed through trusted sources.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from google import genai
from google.genai import types

from app.config import get_settings
from app.core import supabase as db
from app.services import embeddings
from app.services.source_router import sources_for
from app.services.tree import reconstruct_parents

settings = get_settings()
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_EXTRACT_PROMPT = """You are helping fact-checkers in Nepal.
Given a raw message (Nepali Devanagari, Romanized Nepali, English, or mixed),
extract its core factual claim and classify it.

MESSAGE:
{text}

Return ONLY JSON with these exact keys:
{{
  "canonical": "the normalized core factual claim in the message's main language",
  "domain": "health | election | government | finance | education | other",
  "language": "en | ne | romanized | mixed",
  "verdict": "FAKE | REAL | UNVERIFIED",
  "rationale": "one short sentence explaining the verdict; if unsure use UNVERIFIED"
}}"""


def _extract(text: str) -> dict:
    """Extract the canonical claim + domain + tentative verdict via Gemini."""
    try:
        resp = _client.models.generate_content(
            model=settings.GENERATION_MODEL,
            contents=_EXTRACT_PROMPT.format(text=text[:4000]),
            config=types.GenerateContentConfig(
                temperature=0.2, response_mime_type="application/json"
            ),
        )
        data = json.loads(resp.text)
        if isinstance(data, dict) and data.get("canonical"):
            return data
    except Exception:
        pass
    # Graceful fallback: treat the raw text as the claim, needs human review.
    return {
        "canonical": text.strip()[:1000],
        "domain": "other",
        "language": "mixed",
        "verdict": "UNVERIFIED",
        "rationale": "Automatic extraction unavailable — needs human review.",
    }


def ingest_claim(text: str) -> dict:
    """Ingest a raw submission and return a claim summary + verdict card."""
    info = _extract(text)
    claim_id = db.insert_claim(
        canonical=info["canonical"],
        domain=info.get("domain"),
        language=info.get("language"),
        label=info.get("verdict"),
        source="submission",
    )

    now = datetime.now(timezone.utc).isoformat()
    variant = {
        "claim_id": claim_id,
        "text": text.strip()[:2000],
        "embedding": embeddings.embed_text(info["canonical"]),
        "platform": "submission",
        "ts": now,
        "mutation_type": "original",
        "verdict": info.get("verdict"),
        "rationale": info.get("rationale"),
        "source": "submission",
        "language": info.get("language"),
    }
    inserted = db.insert_variants([variant])
    for r in inserted:
        r["embedding"] = variant["embedding"]
        r["ts"] = now
    reconstruct_parents(inserted)

    return {
        "id": claim_id,
        "canonical": info["canonical"],
        "domain": info.get("domain"),
        "language": info.get("language"),
        "label": info.get("verdict"),
        "verdict": info.get("verdict"),
        "rationale": info.get("rationale"),
        "sources": sources_for(info.get("domain")),
        "variant_count": 1,
    }


def list_claims(limit: int = 100) -> list[dict]:
    """Return recent claims (most recent first)."""
    res = (
        db.get_client()
        .table("claims")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def _fetch_variants(claim_id: str) -> list[dict]:
    res = (
        db.get_client()
        .table("variants")
        .select("id,text,platform,ts,parent_id,mutation_type")
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
            "platform": v.get("platform"),
            "ts": v.get("ts"),
            "mutation_type": v.get("mutation_type"),
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
