"""Staged news ingestion: fetch -> stage -> claim gate -> promote.

Flow per poll (manual, bounded):
  1. fetch normalized items from configured RSS sources (no AI)
  2. deduplicate against news_articles by url_hash BEFORE any AI call
  3. stage new items as status='pending'
  4. gate each headline with a news-only extraction prompt (is_claim)
  5. promote factual claims via the service-role ingest_external_claim_atomic
     RPC using the same matching settings as user submissions

Fail-closed: any extraction/embedding/promotion failure marks the article
'failed' (never promoted). Gemini quota exhaustion (429) leaves the article
'pending' (retryable on a later poll) and aborts the poll so the route can
surface HTTP 429.

This module intentionally does NOT touch app.services.pipeline: the user
submission path keeps its raw-text fallback, which would be wrong here.
"""
import json
import os
import socket
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from app.config import get_settings
from app.core import supabase as db
from app.services import embeddings
from app.services.news_sources import FeedItem, get_sources
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_ALLOWED_DOMAINS = {"health", "election", "government", "finance", "education", "other"}
_ALLOWED_LANGUAGES = {"en", "ne", "romanized", "mixed"}

# News-only prompt: unlike pipeline._EXTRACT_PROMPT it must decide whether the
# headline asserts a checkable factual claim at all, and there is NO raw-text
# fallback — failures are handled fail-closed by the caller.
_NEWS_EXTRACT_PROMPT = """You are helping fact-checkers in Nepal triage news headlines.
Given ONE news headline, decide whether it asserts a specific, checkable
factual claim about the world.

NOT factual claims: questions, opinion or editorial teasers, live-blog or
photo-feature titles, event announcements, horoscopes, sports fixtures,
weather bulletins, and vague statements with no checkable assertion.

If it is a claim, restate exactly what the headline asserts. Preserve the
asserted meaning precisely: never negate it, soften it, or judge whether it
is true or false.

HEADLINE:
{text}

Return ONLY JSON with these exact keys:
{{
  "is_claim": true or false,
  "canonical": "the asserted factual claim translated into English, or an empty string if is_claim is false",
  "domain": "health | election | government | finance | education | other",
  "language": "en | ne | romanized | mixed"
}}"""

_FALSEHOOD_ASSESSMENT_PROMPT = """You are a cautious misinformation triage assistant.
Assess the factual claim below using only broadly established knowledge. This
is an automated signal, not a fact-check. If evidence is uncertain, current,
political, predictive, or requires browsing, do not flag it as likely false.

CLAIM: {claim}

Return ONLY JSON with these exact keys:
{{
  "likely_false": true or false,
  "confidence": a number from 0 to 1,
  "rationale": "a concise explanation of the assessment and its uncertainty"
}}"""


class NewsExtractionError(RuntimeError):
    """The gate response was malformed; the article must not be promoted."""


class NewsAssessmentError(RuntimeError):
    """The optional truth-assessment response was malformed."""


class PollAlreadyRunning(RuntimeError):
    """A manual or worker poll currently owns the durable lease."""


def _default_owner() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"


def _acquire_poll_lease(owner: str, trigger: str) -> str | None:
    result = db.get_client().rpc("acquire_news_poll_lease", {
        "p_owner": owner,
        "p_trigger": trigger,
        "p_lease_seconds": settings.NEWS_POLL_LEASE_SECONDS,
    }).execute()
    rows = result.data or []
    row = rows[0] if isinstance(rows, list) and rows else rows
    if not isinstance(row, dict) or not row.get("acquired"):
        return None
    return str(row["run_id"])


def _finish_poll_run(run_id: str, owner: str, status: str,
                     counters: dict, error_summary: str | None = None) -> None:
    db.get_client().rpc("finish_news_poll_run", {
        "p_run_id": run_id,
        "p_owner": owner,
        "p_status": status,
        "p_counters": counters,
        "p_error_summary": error_summary,
    }).execute()


def run_poll(trigger: str, owner: str | None = None) -> dict:
    """Own the durable lease lifecycle around one bounded article poll."""
    poll_owner = owner or _default_owner()
    run_id = _acquire_poll_lease(poll_owner, trigger)
    if run_id is None:
        raise PollAlreadyRunning("A news poll is already in progress")
    try:
        counters = poll_once()
    except ClientError as exc:
        if exc.code == 429:
            _finish_poll_run(
                run_id, poll_owner, "quota_delayed", {},
                "AI quota delayed processing",
            )
        else:
            _finish_poll_run(
                run_id, poll_owner, "failed", {}, "Upstream AI service failed"
            )
        raise
    except Exception:
        _finish_poll_run(run_id, poll_owner, "failed", {}, "News poll failed")
        raise
    _finish_poll_run(run_id, poll_owner, "succeeded", counters)
    return counters


def _row(query) -> dict | None:
    data = query.execute().data or []
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def _staging_count(client, status: str) -> int:
    result = client.table("news_articles").select(
        "id", count="exact"
    ).eq("status", status).limit(1).execute()
    return int(result.count or 0)


def get_poll_status(now: datetime | None = None) -> dict:
    """Return a public, read-only freshness snapshot without secret details."""
    client = db.get_client()
    current_time = now or datetime.now(UTC)
    fields = (
        "id,status,trigger,started_at,completed_at,lease_expires_at,counters,"
        "error_summary"
    )
    latest = _row(
        client.table("news_poll_runs").select(fields)
        .order("started_at", desc=True).limit(1)
    )
    last_success = _row(
        client.table("news_poll_runs").select("completed_at")
        .eq("status", "succeeded").order("completed_at", desc=True).limit(1)
    )
    success_at = last_success.get("completed_at") if last_success else None
    success_time = None
    if success_at:
        try:
            success_time = datetime.fromisoformat(success_at.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            success_time = None
    interval = timedelta(minutes=settings.NEWS_POLL_INTERVAL_MINUTES)
    next_expected = success_time + interval if success_time else None
    stale = success_time is None or current_time > success_time + interval * 2
    latest_status = latest.get("status") if latest else None
    if latest_status == "running":
        state = "polling"
    elif latest_status == "quota_delayed":
        state = "quota_delayed"
    elif latest_status == "failed":
        state = "error"
    elif stale:
        state = "stale"
    else:
        state = "fresh"
    safe_latest = None
    if latest:
        safe_latest = {
            key: latest.get(key)
            for key in (
                "status", "trigger", "started_at", "completed_at",
                "lease_expires_at", "counters", "error_summary",
            )
        }
    return {
        "state": state,
        "stale": stale,
        "last_success_at": success_at,
        "next_expected_at": next_expected.isoformat() if next_expected else None,
        "latest_run": safe_latest,
        "staging": {
            "pending": _staging_count(client, "pending"),
            "failed": _staging_count(client, "failed"),
        },
        "sources": [
            {"name": name, "url": url} for name, url in settings.NEWS_FEEDS.items()
        ],
    }


def _extract_news_claim(title: str) -> dict:
    """Classify one headline. Raises on ANY failure (fail closed).

    ClientError propagates unchanged so the poll loop can distinguish
    quota exhaustion (429) from other upstream errors.
    """
    resp = _client.models.generate_content(
        model=settings.GENERATION_MODEL,
        contents=_NEWS_EXTRACT_PROMPT.format(text=title[:1000]),
        config=types.GenerateContentConfig(
            temperature=0.1, response_mime_type="application/json"
        ),
    )
    try:
        data = json.loads(resp.text)
    except (TypeError, ValueError) as exc:
        raise NewsExtractionError("Gate returned non-JSON output") from exc
    if not isinstance(data, dict) or not isinstance(data.get("is_claim"), bool):
        raise NewsExtractionError("Gate response missing boolean is_claim")

    if not data["is_claim"]:
        return {"is_claim": False}

    canonical = data.get("canonical")
    if not isinstance(canonical, str) or not canonical.strip():
        raise NewsExtractionError("Gate flagged a claim but gave no canonical")
    domain = str(data.get("domain", "other")).lower()
    language = str(data.get("language", "mixed")).lower()
    return {
        "is_claim": True,
        "canonical": canonical.strip()[:1000],
        "domain": domain if domain in _ALLOWED_DOMAINS else "other",
        "language": language if language in _ALLOWED_LANGUAGES else "mixed",
    }


def _assess_falsehood(canonical: str) -> dict:
    """Return a structured AI signal; callers handle failures as unverified."""
    resp = _client.models.generate_content(
        model=settings.GENERATION_MODEL,
        contents=_FALSEHOOD_ASSESSMENT_PROMPT.format(claim=canonical[:1000]),
        config=types.GenerateContentConfig(
            temperature=0.0, response_mime_type="application/json"
        ),
    )
    try:
        data = json.loads(resp.text)
        likely_false = data["likely_false"]
        confidence = float(data["confidence"])
        rationale = str(data["rationale"]).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise NewsAssessmentError("Assessment returned malformed JSON") from exc
    if not isinstance(likely_false, bool) or not 0 <= confidence <= 1 or not rationale:
        raise NewsAssessmentError("Assessment fields are invalid")
    return {
        "likely_false": likely_false,
        "confidence": confidence,
        "rationale": rationale[:2000],
    }


def _persist_assessment(client, claim_id: str, source: str,
                        assessment: dict | None, error: str | None = None) -> str:
    existing = client.table("claim_assessments").select("id").eq(
        "claim_id", claim_id
    ).eq("tier", "VERIFIED_FALSE").limit(1).execute().data
    if isinstance(existing, list) and existing:
        return "VERIFIED_FALSE"
    flagged = bool(
        assessment
        and assessment["likely_false"]
        and assessment["confidence"] >= settings.NEWS_AI_FLAG_THRESHOLD
    )
    row = {
        "claim_id": claim_id,
        "tier": "AI_FLAGGED" if flagged else "UNVERIFIED",
        "verdict": "LIKELY_FALSE" if flagged else "UNVERIFIED",
        "confidence": assessment.get("confidence") if assessment else None,
        "rationale": assessment.get("rationale") if assessment else error,
        "model": settings.GENERATION_MODEL,
        "source": source,
    }
    client.table("claim_assessments").insert(row).execute()
    return row["tier"]


def _set_status(client, article_id: str, status: str, *,
                error: str | None = None, claim_id: str | None = None,
                variant_id: str | None = None) -> None:
    client.table("news_articles").update({
        "status": status,
        "error": error,
        "claim_id": claim_id,
        "variant_id": variant_id,
    }).eq("id", article_id).execute()


def _promote(item: FeedItem, info: dict) -> dict:
    """Embed the canonical and run the external atomic ingestion RPC."""
    embedding = embeddings.embed_text(info["canonical"])
    return db.ingest_external_claim_atomic({
        "p_text": item.title,
        "p_canonical": info["canonical"],
        "p_domain": info["domain"],
        "p_language": info["language"],
        "p_embedding": embedding,
        "p_platform": "news",
        "p_source": item.source_name,
        "p_ts": item.published_at,
        "p_match_threshold": settings.CLAIM_MATCH_THRESHOLD,
        "p_match_window_days": settings.CLAIM_MATCH_WINDOW_DAYS,
    })


def _process_article(client, article_id: str, item: FeedItem,
                     counters: dict) -> None:
    """Gate + promote one staged article, recording its final status.

    Re-raises ClientError 429 after keeping the article 'pending' so the
    poll aborts and the caller surfaces HTTP 429.
    """
    try:
        info = _extract_news_claim(item.title)
        if not info["is_claim"]:
            _set_status(client, article_id, "skipped",
                        error="Headline is not a checkable factual claim")
            counters["skipped_non_claims"] += 1
            return
        ingestion = _promote(item, info)
    except ClientError as exc:
        if exc.code == 429:
            # Retryable: stays 'pending' so a later poll reprocesses it.
            client.table("news_articles").update({
                "error": "Gemini quota exhausted; retry on a later poll",
            }).eq("id", article_id).execute()
            raise
        logger.warning("Gemini error %s for article %s", exc.code, article_id)
        _set_status(client, article_id, "failed",
                    error=f"Gemini API error {exc.code}")
        counters["failed"] += 1
        return
    except Exception as exc:
        logger.warning("News promotion failed for %s", article_id, exc_info=True)
        _set_status(client, article_id, "failed", error=str(exc)[:500])
        counters["failed"] += 1
        return

    try:
        assessment = _assess_falsehood(info["canonical"])
        tier = _persist_assessment(
            client, ingestion["claim_id"], item.source_name, assessment
        )
        counter = {
            "AI_FLAGGED": "ai_flagged",
            "VERIFIED_FALSE": "verified_matches",
        }.get(tier, "unverified")
        counters[counter] += 1
    except Exception as exc:
        logger.warning("Optional news assessment failed for %s", article_id)
        try:
            _persist_assessment(
                client, ingestion["claim_id"], item.source_name, None,
                error="Automatic assessment unavailable",
            )
        except Exception:
            logger.warning("Could not persist unverified assessment", exc_info=True)
        counters["unverified"] += 1

    _set_status(client, article_id, "promoted",
                claim_id=ingestion.get("claim_id"),
                variant_id=ingestion.get("variant_id"))
    counters["promoted"] += 1


def poll_once(max_items: int | None = None) -> dict:
    """Run one bounded poll and return the summary counters.

    Response contract: fetched / new / duplicates / skipped_non_claims /
    promoted / failed.
    """
    limit = max_items if max_items is not None else settings.NEWS_MAX_ITEMS_PER_POLL
    counters = {
        "fetched": 0,
        "new": 0,
        "duplicates": 0,
        "skipped_non_claims": 0,
        "promoted": 0,
        "failed": 0,
        "ai_flagged": 0,
        "unverified": 0,
        "verified_matches": 0,
    }

    # 1. Fetch everything first (no AI, per-source failures isolated).
    items: list[FeedItem] = []
    seen_hashes: set[str] = set()
    for source in get_sources():
        for item in source.fetch():
            counters["fetched"] += 1
            if item.url_hash in seen_hashes:
                counters["duplicates"] += 1
                continue
            seen_hashes.add(item.url_hash)
            items.append(item)

    if not items:
        return counters

    # 2. Durable dedup: one query for all hashes BEFORE any AI call.
    client = db.get_client()
    existing = client.table("news_articles") \
        .select("id,url_hash,status") \
        .in_("url_hash", [i.url_hash for i in items]) \
        .execute().data or []
    by_hash = {row["url_hash"]: row for row in existing}

    # 3. Build the bounded processing queue; stage new items as 'pending'.
    queue: list[tuple[str, FeedItem]] = []
    for item in items:
        row = by_hash.get(item.url_hash)
        if row is not None and row.get("status") != "pending":
            counters["duplicates"] += 1
            continue
        if len(queue) >= limit:
            # Not staged: the next poll fetches and processes it.
            continue
        if row is not None:
            # Quota-interrupted leftover: retry without re-staging.
            article_id = row["id"]
        else:
            try:
                inserted = client.table("news_articles").insert({
                    "url": item.url,
                    "url_hash": item.url_hash,
                    "title": item.title,
                    "source_name": item.source_name,
                    "published_at": item.published_at,
                    "status": "pending",
                }).execute()
                article_id = inserted.data[0]["id"]
            except Exception as exc:
                if "23505" in str(exc) or "duplicate" in str(exc).lower():
                    # Lost a staging race with a concurrent poll.
                    counters["duplicates"] += 1
                    continue
                raise
        counters["new"] += 1
        queue.append((article_id, item))

    # 4. Sequential gate + promote (keeps Gemini usage predictable).
    for article_id, item in queue:
        _process_article(client, article_id, item, counters)

    logger.info("News poll finished: %s", counters)
    return counters
