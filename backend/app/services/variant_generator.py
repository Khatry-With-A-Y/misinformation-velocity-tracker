"""
Gemini variant generator — the engine that produces the mutation tree + velocity.

Given a root claim, it generates N synthetic variants, each with:
  - text (paraphrase / exaggeration / translation / number distortion)
  - platform + timestamp + author (spread metadata)
  - mutation_type
  - parent_index -> ground-truth lineage hint (stored as expected_parent_id)

Neither of the real datasets contains platform+timestamp+parent structure,
so this is the only source of the tree + velocity chart.
"""
import json
from datetime import UTC, datetime, timedelta

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_PROMPT = """You simulate how a single misinformation claim spreads and mutates
across public platforms in Nepal.

ROOT CLAIM:
{claim}

Generate exactly {n} variants that plausibly evolved from this claim as it spread.
Vary language across English, Nepali (Devanagari), Romanized Nepali, and mixed text.

Return ONLY a JSON array. Each element MUST have these exact keys:
{{
  "text": "the variant wording",
  "language": "en | ne | romanized | mixed",
  "platform": "facebook | tiktok | x | youtube | whatsapp",
  "author": "a plausible display name or handle",
  "day_offset": integer >= 0 (days after the root first appeared),
  "mutation_type": "paraphrase | exaggeration | translation | number_distortion",
  "parent_index": -1 for a direct child of the root, otherwise the 0-based index
                  of an EARLIER variant in this same array it mutated from
}}

Rules:
- Order the array by day_offset ascending.
- parent_index must always reference an earlier element (smaller index) or -1.
- Keep claims realistic for Nepal (health, election, government, finance topics).
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=20))
def _call_gemini(claim: str, n: int) -> list[dict]:
    resp = _client.models.generate_content(
        model=settings.GENERATION_MODEL,
        contents=_PROMPT.format(claim=claim, n=n),
        config=types.GenerateContentConfig(
            temperature=0.9,
            response_mime_type="application/json",
        ),
    )
    data = json.loads(resp.text)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of variants")
    return data


def generate_variants(claim: str, n: int = None,
                      base_time: datetime = None) -> list[dict]:
    """
    Return a list of variant dicts ready to be embedded + inserted.
    Each dict carries a temporary `_parent_index` used to wire
    expected_parent_id after the rows get real ids.
    """
    n = n or settings.VARIANTS_PER_ROOT
    base_time = base_time or datetime.now(UTC) - timedelta(days=14)

    raw = _call_gemini(claim, n)
    out = []
    for item in raw:
        try:
            offset = int(item.get("day_offset", 0))
        except (TypeError, ValueError):
            offset = 0
        out.append({
            "text": item["text"],
            "language": item.get("language"),
            "platform": item.get("platform"),
            "author": item.get("author"),
            "ts": (base_time + timedelta(days=offset)).isoformat(),
            "mutation_type": item.get("mutation_type"),
            "_parent_index": item.get("parent_index", -1),
            "source": "synthetic:variant_generator",
        })
    return out
