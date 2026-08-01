"""Re-process all existing claims and variants through the updated pipeline.

This script:
1. Fetches all variants from the database
2. Re-extracts canonical forms (now translated to English)
3. Re-embeds the new canonical text
4. Updates the variant embeddings and claim canonical text
5. Re-links variants that now match existing claims

Usage (from backend/):
    python -m scripts.reprocess_claims [--dry-run]

Or via Docker:
    docker compose exec backend python -m scripts.reprocess_claims
"""
import argparse
import sys
import time
from collections import defaultdict

# Ensure app modules are importable
sys.path.insert(0, "/app")

from app.config import get_settings
from app.core.supabase import get_client
from app.services.embeddings import embed_text
from app.services.pipeline import _extract

settings = get_settings()


def reprocess(dry_run: bool = False):
    client = get_client()

    # 1. Fetch all variants
    print("Fetching all variants...")
    variants = client.table("variants").select("id, text, claim_id, embedding").execute().data
    print(f"Found {len(variants)} variants to reprocess.")

    if not variants:
        print("Nothing to reprocess.")
        return

    # 2. Fetch all claims
    print("Fetching all claims...")
    claims = client.table("claims").select("id, canonical, domain, language").execute().data
    claims_by_id = {c["id"]: c for c in claims}
    print(f"Found {len(claims)} claims.")

    # 3. Re-extract and re-embed each variant
    updated_variants = []
    for i, v in enumerate(variants):
        raw_text = v["text"]
        print(f"\n[{i+1}/{len(variants)}] Processing variant {v['id'][:8]}...")
        print(f"  Original text: {raw_text[:80]}...")

        try:
            info = _extract(raw_text)
            print(f"  New canonical: {info['canonical'][:80]}...")

            embedding = embed_text(info["canonical"])
            updated_variants.append({
                "variant_id": v["id"],
                "claim_id": v["claim_id"],
                "new_canonical": info["canonical"],
                "new_domain": info["domain"],
                "new_language": info["language"],
                "new_embedding": embedding,
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Rate limit: small delay between API calls
        if (i + 1) % 5 == 0:
            print("  (pausing 2s for rate limits...)")
            time.sleep(2)

    if dry_run:
        print(f"\n=== DRY RUN: Would update {len(updated_variants)} variants ===")
        for uv in updated_variants:
            print(f"  Variant {uv['variant_id'][:8]}: canonical = {uv['new_canonical'][:60]}...")
        return

    # 4. Group variants by new canonical to merge duplicate claims
    print("\n=== Updating database ===")

    # First, update all variant embeddings
    for uv in updated_variants:
        print(f"  Updating variant {uv['variant_id'][:8]} embedding...")
        client.table("variants").update({
            "embedding": uv["new_embedding"],
        }).eq("id", uv["variant_id"]).execute()

    # Update claim canonical text, domain, language
    claims_updated = set()
    for uv in updated_variants:
        cid = uv["claim_id"]
        if cid and cid not in claims_updated:
            print(f"  Updating claim {cid[:8]} canonical to: {uv['new_canonical'][:60]}...")
            client.table("claims").update({
                "canonical": uv["new_canonical"],
                "domain": uv["new_domain"],
                "language": uv["new_language"],
            }).eq("id", cid).execute()
            claims_updated.add(cid)

    # 5. Now try to merge claims that have the same canonical form
    print("\n=== Checking for mergeable claims ===")
    # Re-fetch claims after updates
    claims = client.table("claims").select("id, canonical").execute().data
    canonical_groups = defaultdict(list)
    for c in claims:
        canonical_groups[c["canonical"].strip().lower()].append(c["id"])

    merged = 0
    for canonical, ids in canonical_groups.items():
        if len(ids) > 1:
            keep_id = ids[0]
            for merge_id in ids[1:]:
                print(f"  Merging claim {merge_id[:8]} into {keep_id[:8]} (canonical: {canonical[:50]}...)")
                # Move variants from merge_id to keep_id
                client.table("variants").update({
                    "claim_id": keep_id
                }).eq("claim_id", merge_id).execute()
                # Move claim_submissions if any
                # Delete the duplicate claim
                client.table("claims").delete().eq("id", merge_id).execute()
                merged += 1

    print(f"\n=== Done! Updated {len(updated_variants)} variants, merged {merged} duplicate claims ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-process all claims through updated pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without modifying the database")
    args = parser.parse_args()
    reprocess(dry_run=args.dry_run)
