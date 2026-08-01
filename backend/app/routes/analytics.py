"""Public, bounded spread rankings and claim analytics."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.supabase import get_anon_client
from app.schemas.claims import ClaimAnalytics, Period, RankingItem
from app.utils.logger import setup_logger

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = setup_logger(__name__)


@router.get("/rankings", response_model=list[RankingItem])
async def rankings(
    period: Period = "week",
    tier: str = Query(default="verified_false", pattern="^(verified_false|ai_flagged)$"),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        result = get_anon_client().rpc("claim_rankings", {
            "p_period": period,
            "p_tier": tier.upper(),
            "p_limit": limit,
        }).execute()
        return result.data or []
    except Exception:
        logger.exception("rankings failed")
        raise HTTPException(status_code=500, detail="Unable to load rankings")


@router.get("/claims/{claim_id}", response_model=ClaimAnalytics)
async def claim_analytics(claim_id: UUID, period: Period = "week"):
    try:
        result = get_anon_client().rpc("claim_spread_analytics", {
            "p_claim_id": str(claim_id),
            "p_period": period,
        }).execute()
        return result.data
    except Exception:
        logger.exception("claim analytics failed")
        raise HTTPException(status_code=500, detail="Unable to load claim analytics")