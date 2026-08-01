"""Quota-aware Docker worker for recurring bounded RSS polls."""
import random
import signal
import threading
from uuid import uuid4

from app.config import get_settings
from app.services import news_ingest
from app.utils.logger import setup_logger

settings = get_settings()
logger = setup_logger(__name__)


def _backoff(failures: int) -> float:
    base = settings.NEWS_POLL_BACKOFF_BASE_SECONDS * (2 ** max(0, failures))
    jitter = random.uniform(0, settings.NEWS_POLL_JITTER_SECONDS)
    return min(settings.NEWS_POLL_BACKOFF_MAX_SECONDS, base + jitter)


def run_cycle(owner: str, failures: int = 0) -> float:
    """Run one leased cycle and return seconds until the next attempt."""
    normal_delay = settings.NEWS_POLL_INTERVAL_MINUTES * 60
    try:
        counters = news_ingest.run_poll("worker", owner)
        logger.info("Automatic news poll completed: %s", counters)
        return normal_delay
    except news_ingest.PollAlreadyRunning:
        logger.info("Automatic news poll skipped because another run owns the lease")
        return normal_delay
    except Exception:
        delay = _backoff(failures)
        logger.warning(
            "Automatic news poll failed; retrying in %.0f seconds", delay,
            exc_info=True,
        )
        return delay


def main() -> None:
    stop = threading.Event()

    def request_stop(*_args) -> None:
        logger.info("News poller stopping")
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    owner = f"news-poller:{uuid4().hex}"
    logger.info(
        "News poller starting with %s minute interval",
        settings.NEWS_POLL_INTERVAL_MINUTES,
    )
    if stop.wait(settings.NEWS_POLL_STARTUP_DELAY_SECONDS):
        return

    failures = 0
    normal_delay = settings.NEWS_POLL_INTERVAL_MINUTES * 60
    while not stop.is_set():
        delay = run_cycle(owner, failures)
        failures = failures + 1 if delay != normal_delay else 0
        stop.wait(delay)


if __name__ == "__main__":
    main()