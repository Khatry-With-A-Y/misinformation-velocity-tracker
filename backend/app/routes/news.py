"""Manual news polling endpoints (admin-token protected)."""
import secrets
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from google.genai.errors import ClientError

from app.config import get_settings
from app.services import news_ingest
from app.utils.logger import setup_logger

router = APIRouter(prefix="/news", tags=["news"])
logger = setup_logger(__name__)
settings = get_settings()


def _require_admin(token: Optional[str]) -> None:
    """503 when polling is unconfigured, 401 on a wrong/missing token."""
    if not settings.NEWS_ADMIN_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="News polling is disabled: NEWS_ADMIN_TOKEN is not configured",
        )
    if not token or not secrets.compare_digest(token, settings.NEWS_ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/poll")
def poll(x_admin_token: Optional[str] = Header(default=None)):
    """Run one bounded poll: fetch, stage, gate, and promote headlines."""
    _require_admin(x_admin_token)
    logger.info("Manual news poll triggered")
    try:
        return news_ingest.run_poll("manual")
    except news_ingest.PollAlreadyRunning:
        raise HTTPException(status_code=409, detail="A news poll is already running")
    except ClientError as exc:
        if exc.code == 429:
            logger.warning("Gemini quota exhausted during news poll")
            raise HTTPException(
                status_code=429,
                detail="AI analysis quota exceeded. Staged articles stay "
                       "retryable; try again in a few minutes.",
            )
        logger.exception("Gemini API error during news poll")
        raise HTTPException(status_code=502, detail="Upstream AI service error")
    except Exception:
        logger.exception("News poll failed")
        raise HTTPException(status_code=500, detail="News poll failed")


@router.get("/sources")
def sources():
    """List the configured RSS feeds."""
    return [
        {"name": name, "url": url}
        for name, url in settings.NEWS_FEEDS.items()
    ]


@router.get("/status")
def status():
    """Expose a safe freshness summary for ordinary dashboard users."""
    try:
        return news_ingest.get_poll_status()
    except Exception:
        logger.exception("News status failed")
        raise HTTPException(status_code=503, detail="News status is unavailable")
