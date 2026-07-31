"""Claim ingestion + mutation-tree / velocity / platform endpoints."""
from fastapi import APIRouter, HTTPException

from app.schemas.claims import (
    IngestRequest,
    TreeResponse,
    VelocityPoint,
    PlatformCount,
)
from app.services import pipeline
from app.utils.logger import setup_logger

router = APIRouter(prefix="/claims", tags=["claims"])
logger = setup_logger(__name__)


@router.post("/ingest")
async def ingest(req: IngestRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    logger.info("Ingesting claim submission")
    try:
        return pipeline.ingest_claim(req.text)
    except Exception as e:  # surface config/DB errors cleanly to the client
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_claims():
    try:
        return pipeline.list_claims()
    except Exception as e:
        logger.error(f"list_claims failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{claim_id}/tree", response_model=TreeResponse)
async def claim_tree(claim_id: str):
    try:
        return pipeline.get_tree(claim_id)
    except Exception as e:
        logger.error(f"tree failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{claim_id}/velocity", response_model=list[VelocityPoint])
async def claim_velocity(claim_id: str):
    try:
        return pipeline.get_velocity(claim_id)
    except Exception as e:
        logger.error(f"velocity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{claim_id}/platforms", response_model=list[PlatformCount])
async def claim_platforms(claim_id: str):
    try:
        return pipeline.get_platforms(claim_id)
    except Exception as e:
        logger.error(f"platforms failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
