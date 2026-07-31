"""
Orchestrator: load all datasets + generate variants into Supabase.

Pipeline per claim:
  1. insert claim -> claim_id
  2. collect variant rows (real from datasets, synthetic from generator)
  3. embed every variant text (Gemini)
  4. insert variants -> real ids
  5. wire expected_parent_id from the generator's ground-truth hints
  6. reconstruct parent_id from similarity + time (the demo mutation tree)

Usage (run from the backend/ directory):
  python -m app.data.load_all --all
  python -m app.data.load_all --chhatramani --generate
  python -m app.data.load_all --nepoc --misdetect
"""
import argparse
from datetime import UTC, datetime, timedelta

from app.core import supabase as db
from app.services import embeddings
from app.services.tree import reconstruct_parents
from app.services.variant_generator import generate_variants
from app.config import get_settings

from app.data.loaders import chhatramani, misdetect, nepoc

settings = get_settings()


# ---- variant row helpers -------------------------------------------------

_VARIANT_COLUMNS = {
    "text", "embedding", "platform", "author", "ts", "expected_parent_id",
    "mutation_type", "verdict", "rationale", "confidence",
    "evidence_url", "evidence_title", "entities", "source", "language",
}


def _clean_variant(v: dict, claim_id: str) -> dict:
    """Keep only DB columns + attach claim_id. Drops helper keys like _parent_index."""
    row = {k: v[k] for k in v if k in _VARIANT_COLUMNS}
    row["claim_id"] = claim_id
    row.setdefault("language", None)
    return row


def _coerce_timestamp(value) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return None


def _normalize_variant_times(variants: list[dict], base_time: datetime) -> None:
    """Ensure every variant has a timestamp so tree/velocity APIs stay useful."""
    for i, variant in enumerate(variants):
        variant["ts"] = _coerce_timestamp(variant.get("ts"))
        if not variant["ts"]:
            variant["ts"] = (base_time + timedelta(minutes=i * 30)).isoformat()


def _persist_claim_group(claim: dict, variants: list[dict],
                         synthetic_hints: list[int] = None) -> None:
    """Embed + insert one claim and its variants, then rebuild lineage."""
    claim_id = db.insert_claim(**claim)

    texts = [v["text"] for v in variants]
    vecs = embeddings.embed_batch(texts)
    for v, vec in zip(variants, vecs):
        v["embedding"] = vec

    rows = [_clean_variant(v, claim_id) for v in variants]
    inserted = db.insert_variants(rows)
    ids = [r["id"] for r in inserted]

    # Re-attach locally computed embeddings + ts (insert preserves order),
    # since Supabase returns the vector column as a string, not a float list.
    for r, v, vec in zip(inserted, variants, vecs):
        r["embedding"] = vec
        r["ts"] = v.get("ts")

    # 5. ground-truth parent hints (synthetic only) -> expected_parent_id
    if synthetic_hints:
        for idx, hint in enumerate(synthetic_hints):
            if hint is not None and hint >= 0 and hint < len(ids):
                db.get_client().table("variants").update(
                    {"expected_parent_id": ids[hint]}
                ).eq("id", ids[idx]).execute()

    # 6. reconstruct parent_id from embeddings + timestamps
    reconstruct_parents(inserted)


# ---- per-source drivers --------------------------------------------------

def run_chhatramani(with_generation: bool, limit: int = None) -> None:
    roots = chhatramani.load_root_claims(limit=limit)
    base = datetime.now(UTC) - timedelta(days=21)
    for i, claim in enumerate(roots):
        claim_base = base + timedelta(hours=i * 3)
        # the root itself is the first variant
        root_variant = {
            "text": claim["canonical"],
            "platform": "facebook",
            "ts": claim_base.isoformat(),
            "mutation_type": "original",
            "source": claim["source"],
            "verdict": claim.get("verdict") or claim.get("label"),
            "rationale": claim.get("rationale"),
            "language": claim.get("language"),
        }
        variants = [root_variant]
        hints = [None]

        if with_generation:
            gen = generate_variants(claim["canonical"], base_time=claim_base)
            for g in gen:
                parent_index = g.pop("_parent_index")
                # Gemini indexes synthetic parents within the generated array.
                # Persisted rows include the real root at index 0, so direct
                # children map to the root and generated parents shift by one.
                hints.append(0 if parent_index is None or parent_index < 0 else parent_index + 1)
                variants.append(g)

        _persist_claim_group(claim, variants, synthetic_hints=hints)
        print(f"[chhatramani] claim {i+1}/{len(roots)} -> {len(variants)} variants")


def run_nepoc() -> None:
    groups = nepoc.load_claims_with_variants(limit_claims=settings.NEPOC_CLAIM_GROUPS)
    for i, g in enumerate(groups):
        _normalize_variant_times(g["variants"], datetime.now(UTC) - timedelta(days=14))
        _persist_claim_group(g["claim"], g["variants"])
        print(f"[nepoc] claim {i+1}/{len(groups)}")


def run_misdetect() -> None:
    groups = misdetect.load_verdict_slice()
    for i, g in enumerate(groups):
        _normalize_variant_times(g["variants"], datetime.now(UTC) - timedelta(days=7))
        _persist_claim_group(g["claim"], g["variants"])
    print(f"[misdetect] inserted {len(groups)} verdict rows")


def preview_loaders(include_generation: bool = False) -> None:
    """Load and summarize datasets without Supabase writes or Gemini embeddings."""
    groups = []
    nepoc_groups = nepoc.load_claims_with_variants(limit_claims=5)
    misdetect_groups = misdetect.load_verdict_slice(rows_per_domain=2)
    chhatramani_roots = chhatramani.load_root_claims(limit=5)
    groups.extend(nepoc_groups)
    groups.extend(misdetect_groups)
    groups.extend({"claim": claim, "variants": [{"text": claim["canonical"]}]} for claim in chhatramani_roots)
    if include_generation:
        print("[preview] synthetic generation is skipped in preview mode to avoid Gemini writes/calls")
    print(f"[preview] normalized {len(groups)} claim groups")
    for source in (nepoc.DATASET_ID, misdetect.DATASET_ID, chhatramani.DATASET_ID):
        source_groups = [g for g in groups if g["claim"].get("source") == source]
        variant_count = sum(len(g["variants"]) for g in source_groups)
        print(f"[preview] {source}: {len(source_groups)} claims, {variant_count} variants")


# ---- CLI -----------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Load datasets into Supabase")
    p.add_argument("--all", action="store_true", help="run every loader + generation")
    p.add_argument("--chhatramani", action="store_true", help="Nepali root claims")
    p.add_argument("--generate", action="store_true",
                   help="generate synthetic variants for root claims (tree fuel)")
    p.add_argument("--nepoc", action="store_true", help="NepOOC real dates + evidence")
    p.add_argument("--misdetect", action="store_true", help="MisDetect verdict slice")
    p.add_argument("--preview", action="store_true",
                   help="load and summarize small dataset slices without Supabase/Gemini writes")
    p.add_argument("--limit", type=int,
                   help="override the configured root-claim limit for chhatramani runs")
    args = p.parse_args()

    if args.preview:
        preview_loaders(include_generation=args.generate)
        return

    if args.all:
        run_nepoc()
        run_misdetect()
        run_chhatramani(with_generation=True, limit=args.limit)
        return

    if not any([args.chhatramani, args.nepoc, args.misdetect]):
        p.error("Nothing selected. Use --all or one of the loader flags.")

    if args.nepoc:
        run_nepoc()
    if args.misdetect:
        run_misdetect()
    if args.chhatramani:
        run_chhatramani(with_generation=args.generate, limit=args.limit)


if __name__ == "__main__":
    main()
