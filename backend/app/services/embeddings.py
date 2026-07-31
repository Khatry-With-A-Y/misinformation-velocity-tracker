"""Gemini multilingual embeddings (handles English, Devanagari, Romanized Nepali)."""
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()
_client = genai.Client(api_key=settings.GEMINI_API_KEY)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=20))
def embed_text(text: str) -> list[float]:
    """Return an embedding vector for a single piece of text."""
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
