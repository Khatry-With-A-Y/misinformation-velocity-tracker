"""Claim ingestion + public mutation-tree / velocity / platform endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import get_settings
from app.core.supabase import (
    IngestionAuthError,
    IngestionRateLimitError,
    get_current_user,
    security,
)

from app.schemas.claims import (
    ClaimSummary,
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
    except Exception:
        logger.exception("Ingest failed for authenticated user")
        raise HTTPException(status_code=500, detail="Claim ingestion failed")


@router.get("", response_model=list[ClaimSummary])
async def list_claims():
    try:
        return pipeline.list_claims()
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
