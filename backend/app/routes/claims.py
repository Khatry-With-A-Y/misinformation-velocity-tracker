"""Claim ingestion + public mutation-tree / velocity / platform endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from google.genai.errors import ClientError

from app.config import get_settings
from app.core.supabase import (
    IngestionAuthError,
    IngestionRateLimitError,
    get_current_user,
    security,
)

from app.schemas.claims import (
    ClaimSummary,
    ClaimPage,
    IngestRequest,
    IngestResponse,
    TreeResponse,
    VelocityPoint,
    PlatformCount,
)
from app.services import pipeline
from app.utils.logger import setup_logger

router = APIRouter(prefix="/claims", tags=["claims"])
logger = setup_logger(__name__)
settings = get_settings()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    req: IngestRequest,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    logger.info("Ingesting claim submission")
    try:
        return pipeline.ingest_claim(
            req.text,
            credentials.credentials,
            match_threshold=settings.CLAIM_MATCH_THRESHOLD,
            match_window_days=settings.CLAIM_MATCH_WINDOW_DAYS,
            rate_limit=settings.CLAIM_RATE_LIMIT,
            rate_window_minutes=settings.CLAIM_RATE_WINDOW_MINUTES,
        )
    except IngestionAuthError:
        raise HTTPException(status_code=401, detail="Authentication invalid")
    except IngestionRateLimitError:
        raise HTTPException(status_code=429, detail="Submission rate limit exceeded")
    except ClientError as exc:
        if exc.code == 429:
            logger.warning("Gemini quota exhausted during ingest")
            raise HTTPException(
                status_code=429,
                detail="AI analysis quota exceeded. Please try again in a few minutes.",
            )
        logger.exception("Gemini API error during ingest")
        raise HTTPException(status_code=502, detail="Upstream AI service error")
    except Exception:
        logger.exception("Ingest failed for authenticated user")
        raise HTTPException(status_code=500, detail="Claim ingestion failed")


@router.get("", response_model=list[ClaimSummary] | ClaimPage)
async def list_claims(
    limit: int = Query(default=100, ge=1, le=100),
    page: int | None = Query(default=None, ge=1),
    query: str | None = Query(default=None, max_length=200),
    source: str | None = None,
    domain: str | None = None,
    language: str | None = None,
    tier: str | None = Query(
        default=None, pattern="^(verified_false|ai_flagged|unverified)$"
    ),
    period: str | None = Query(default=None, pattern="^(day|week|month|year)$"),
    platform: str | None = Query(default=None, max_length=100),
):
    try:
        return pipeline.list_claims(
            limit, page, query, source, domain, language, tier, period, platform
        )
    except Exception:
        logger.exception("list_claims failed")
        raise HTTPException(status_code=500, detail="Unable to list claims")


@router.get("/{claim_id}/tree", response_model=TreeResponse)
async def claim_tree(claim_id: str):
    try:
        return pipeline.get_tree(claim_id)
    except Exception:
        logger.exception("tree failed")
        raise HTTPException(status_code=500, detail="Unable to load claim tree")


@router.get("/{claim_id}/velocity", response_model=list[VelocityPoint])
async def claim_velocity(claim_id: str):
    try:
        return pipeline.get_velocity(claim_id)
    except Exception:
        logger.exception("velocity failed")
        raise HTTPException(status_code=500, detail="Unable to load claim velocity")


@router.get("/{claim_id}/platforms", response_model=list[PlatformCount])
async def claim_platforms(claim_id: str):
    try:
        return pipeline.get_platforms(claim_id)
    except Exception:
        logger.exception("platforms failed")
        raise HTTPException(status_code=500, detail="Unable to load claim platforms")
