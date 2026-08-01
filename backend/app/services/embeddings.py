"""Gemini multilingual embeddings (handles English, Devanagari, Romanized Nepali)."""
from functools import lru_cache

from google import genai
from google.genai.errors import ClientError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()
_client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _is_retryable_error(exception: BaseException) -> bool:
    """Retry only rate limits (429) and transient server errors (500/503)."""
    if isinstance(exception, ClientError):
        return exception.code in (429, 500, 503)
    return False


@lru_cache(maxsize=1024)
@retry(
    retry=retry_if_exception(_is_retryable_error),
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=60),
    reraise=True,
)
def embed_text(text: str) -> list[float]:
    """Return an embedding vector for a single piece of text (cached)."""
    resp = _client.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": settings.EMBEDDING_DIM},
    )
    return list(resp.embeddings[0].values)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Falls back to per-item on batch failure."""
    if not texts:
        return []
    try:
        resp = _client.models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=texts,
            config={"output_dimensionality": settings.EMBEDDING_DIM},
        )
        return [list(e.values) for e in resp.embeddings]
    except Exception:
        return [embed_text(t) for t in texts]
