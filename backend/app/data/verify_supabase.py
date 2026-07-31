"""Verify Supabase schema objects and a minimal claim/variant insert.

Usage (run from the backend container or backend/ directory):
  python -m app.data.verify_supabase
"""
from datetime import datetime, timezone

from postgrest.exceptions import APIError

from app.config import get_settings
from app.core import supabase as db


def _embedding() -> list[float]:
    return [0.0] * get_settings().EMBEDDING_DIM


def _assert_schema(client) -> None:
    client.table("claims").select("id,canonical,domain,language,label,verdict,rationale,source,created_at").limit(1).execute()
    client.table(
        "variants"
    ).select(
        "id,claim_id,text,embedding,platform,ts,parent_id,expected_parent_id,mutation_type,verdict,rationale,source,language,created_at"
    ).limit(1).execute()
    client.rpc(
        "match_variants",
        {
            "query_embedding": _embedding(),
            "match_threshold": 1.1,
            "match_count": 1,
        },
    ).execute()


def _assert_insert_round_trip(client) -> None:
    claim_id = None
    variant_id = None
    try:
        claim_id = db.insert_claim(
            canonical="Supabase schema verification claim",
            domain="other",
            language="en",
            label="UNVERIFIED",
            verdict="UNVERIFIED",
            rationale="Inserted by the schema verification script.",
            source="schema_verification",
        )
        inserted = db.insert_variants([
            {
                "claim_id": claim_id,
                "text": "Supabase schema verification variant",
                "embedding": _embedding(),
                "platform": "submission",
                "ts": datetime.now(timezone.utc).isoformat(),
                "mutation_type": "original",
                "verdict": "UNVERIFIED",
                "rationale": "Inserted by the schema verification script.",
                "source": "schema_verification",
                "language": "en",
            }
        ])
        variant_id = inserted[0]["id"]

        claim = client.table("claims").select("id").eq("id", claim_id).single().execute()
        variant = client.table("variants").select("id,claim_id").eq("id", variant_id).single().execute()
        if not claim.data or not variant.data or variant.data["claim_id"] != claim_id:
            raise RuntimeError("Inserted verification rows could not be read back.")
    finally:
        if variant_id:
            client.table("variants").delete().eq("id", variant_id).execute()
        if claim_id:
            client.table("claims").delete().eq("id", claim_id).execute()


def main() -> None:
    client = db.get_client()
    try:
        _assert_schema(client)
        _assert_insert_round_trip(client)
    except APIError as e:
        raise RuntimeError(
            "Supabase verification failed. Re-run backend/schema.sql in the Supabase SQL editor, "
            "then run this command again. Original error: "
            f"{e}"
        ) from e
    print("Supabase schema verification passed: claims, variants, match_variants, vector(768), and insert round trip are working.")


if __name__ == "__main__":
    main()