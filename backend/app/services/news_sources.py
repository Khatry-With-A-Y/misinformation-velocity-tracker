"""Pluggable news sources: fetch RSS feeds and normalize entries.

No AI calls happen here. Each entry becomes a typed FeedItem whose
normalized URL + sha256 hash powers durable deduplication in the
news_articles staging table. Per-source failures are isolated: a broken
feed logs a warning and yields no items instead of failing the poll.
"""
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser

from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Tracking parameters stripped before hashing so the same article shared
# through different campaigns deduplicates to one row.
_TRACKING_PARAMS = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid"}
_TRACKING_PREFIXES = ("utm_",)

# Separators used by aggregators for " - Publisher" title suffixes.
_TITLE_SUFFIX_SEPARATORS = (" - ", " — ", " | ")


@dataclass(frozen=True)
class FeedItem:
    """One normalized feed entry, ready for staging."""
    title: str
    url: str
    url_hash: str
    published_at: str  # ISO 8601, falls back to fetch time
    source_name: str


def normalize_url(url: str) -> str:
    """Lowercase scheme/host, drop fragments and tracking parameters."""
    parts = urlsplit((url or "").strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS
        and not key.lower().startswith(_TRACKING_PREFIXES)
    ]
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path,
        urlencode(query),
        "",  # fragment removed
    ))


def hash_url(url: str) -> str:
    """Stable sha256 over the normalized URL (deduplication key)."""
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def clean_title(title: str) -> str:
    """Collapse whitespace and strip a trailing ' - Publisher' style suffix.

    Conservative: the suffix is removed only when it is short, digit-free,
    and clearly separated, so hyphenated headlines survive intact.
    """
    cleaned = " ".join((title or "").split())
    for sep in _TITLE_SUFFIX_SEPARATORS:
        if sep in cleaned:
            head, _, tail = cleaned.rpartition(sep)
            if head and len(head) > len(tail) and 0 < len(tail) <= 40 \
                    and len(tail.split()) <= 5 \
                    and not any(ch.isdigit() for ch in tail):
                cleaned = head.strip()
            break
    return cleaned


def _entry_timestamp(entry) -> str:
    """Entry publish time as ISO 8601; malformed/missing dates fall back to now."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = entry.get(attr)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=UTC).isoformat()
            except (TypeError, ValueError):
                continue
    return datetime.now(UTC).isoformat()


class RSSNewsSource:
    """A single configured RSS feed. fetch() never raises."""

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def fetch(self, limit: int | None = None) -> list[FeedItem]:
        """Return normalized items; an unreachable/malformed feed returns []."""
        try:
            parsed = feedparser.parse(self.url)
        except Exception:
            logger.warning("RSS fetch failed for %s", self.name, exc_info=True)
            return []
        entries = list(getattr(parsed, "entries", None) or [])
        if not entries:
            logger.warning(
                "RSS feed %s returned no entries (bozo=%s)",
                self.name, getattr(parsed, "bozo", False),
            )
            return []
        if limit is not None:
            entries = entries[:limit]

        items: list[FeedItem] = []
        for entry in entries:
            link = (entry.get("link") or "").strip()
            title = clean_title(entry.get("title") or "")
            if not link or not title:
                continue
            items.append(FeedItem(
                title=title,
                url=normalize_url(link),
                url_hash=hash_url(link),
                published_at=_entry_timestamp(entry),
                source_name=self.name,
            ))
        return items


def get_sources() -> list[RSSNewsSource]:
    """Instantiate a source per configured NEWS_FEEDS entry."""
    return [
        RSSNewsSource(name, url)
        for name, url in get_settings().NEWS_FEEDS.items()
    ]
