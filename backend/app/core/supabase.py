"""Supabase integration: clients, insert helpers, and JWT auth dependency.

The service-role client is used server-side by the loaders and privileged API
calls. JWT verification uses the Supabase project's JWT secret so the frontend
can authenticate with a Supabase access token.
"""
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import create_client, Client

from app.config import get_settings

settings = get_settings()

_service_client: Optional[Client] = None
_anon_client: Optional[Client] = None


def get_client() -> Client:
    """Singleton Supabase client using the service-role key (server-side only)."""
    global _service_client
    if _service_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_SERVICE_KEY are not configured. "
                "Copy backend/.env.example to backend/.env and fill them in."
            )
        _service_client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
        )
    return _service_client


def get_anon_client() -> Client:
    """Singleton Supabase client using the anon key (auth: sign-up / sign-in)."""
    global _anon_client
    if _anon_client is None:
        key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY
        if not settings.SUPABASE_URL or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY are not configured.")
        _anon_client = create_client(settings.SUPABASE_URL, key)
    return _anon_client


# ---- insert helpers used by the loaders / pipeline -----------------------

def insert_claim(canonical: str, domain: str = None, language: str = None,
                 label: str = None, source: str = None,
                 verdict: str = None, rationale: str = None) -> str:
    """Insert a claim and return its id."""
    res = get_client().table("claims").insert({
        "canonical": canonical,
        "domain": domain,
        "language": language,
        "label": label,
        "verdict": verdict or label,
        "rationale": rationale,
        "source": source,
    }).execute()
    return res.data[0]["id"]


def insert_variants(rows: list[dict]) -> list[dict]:
    """Bulk insert variant rows. Returns inserted rows (with ids)."""
    if not rows:
        return []
    res = get_client().table("variants").insert(rows).execute()
    return res.data


def update_variant_parent(variant_id: str, parent_id: str) -> None:
    """Set the reconstructed parent_id for a variant."""
    get_client().table("variants").update(
        {"parent_id": parent_id}
    ).eq("id", variant_id).execute()


# ---- JWT auth dependency -------------------------------------------------

security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify a Supabase access token and return its decoded payload."""
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET not configured")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token missing subject")
    return payload
