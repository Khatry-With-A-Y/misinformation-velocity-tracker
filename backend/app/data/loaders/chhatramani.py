"""
Loader: chhatramani/nepali-fake-news-dataset-v1

Role: Nepali (Devanagari) ROOT claims by domain. These seed the claims table
and are handed to the variant generator to build the mutation tree + velocity.
"""
from datasets import load_dataset

from app.config import get_settings
from app.data.loaders.common import first_present, normalize_domain, normalize_label

settings = get_settings()

DATASET_ID = "chhatramani/nepali-fake-news-dataset-v1"


def load_root_claims(limit: int = None) -> list[dict]:
    """
    Return up to `limit` root claims as dicts:
      {canonical, domain, language, label, source}
    Only FAKE items are preferred (they're the ones worth tracking spread of),
    falling back to any labeled row if there aren't enough.
    """
    limit = limit or settings.CHHATRAMANI_ROOT_CLAIMS
    ds = load_dataset(DATASET_ID, split="train")

    fake, other = [], []
    for row in ds:
        text = first_present(row, "headline", "full_text", "body", "text", "title")
        if not text:
            continue
        claim = {
            "canonical": str(text).strip()[:1000],
            "domain": normalize_domain(first_present(row, "category", "domain")),
            "language": "ne",
            "label": normalize_label(first_present(row, "label")),
            "verdict": normalize_label(first_present(row, "label")),
            "rationale": first_present(row, "summary", "description", "rationale"),
            "source": DATASET_ID,
        }
        (fake if claim["label"] == "FAKE" else other).append(claim)

    selected = (fake + other)[:limit]
    print(f"[chhatramani] selected {len(selected)} root claims "
          f"({len(fake)} FAKE available)")
    return selected
