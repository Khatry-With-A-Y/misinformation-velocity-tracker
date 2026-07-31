"""
Mutation-tree reconstruction.

For a set of variants belonging to one claim, each variant's parent is the
earliest, most-similar EARLIER variant (cosine similarity over embeddings
above a threshold). This yields a believable tree in a few lines of Python
and is the core of the "mutation tree" visual.
"""
from datetime import datetime

from app.core import supabase as db

SIMILARITY_THRESHOLD = 0.55


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _parse_ts(v: dict) -> datetime:
    ts = v.get("ts")
    if not ts:
        return datetime.max
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.max


def reconstruct_parents(inserted_variants: list[dict]) -> None:
    """
    Given inserted variant rows (must include id, ts, embedding), compute and
    persist parent_id for each. Rows without a timestamp are treated as roots.
    """
    variants = [v for v in inserted_variants if v.get("embedding")]
    if len(variants) < 2:
        return

    ordered = sorted(variants, key=_parse_ts)

    for i, child in enumerate(ordered):
        best_parent = None
        best_sim = SIMILARITY_THRESHOLD
        for j in range(i):
            parent = ordered[j]
            sim = _cosine(child["embedding"], parent["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_parent = parent
        if best_parent is not None:
            db.update_variant_parent(child["id"], best_parent["id"])
