"""Supabase integration: scoped clients, loader helpers, and JWT auth.

The service-role client is reserved for offline loaders. JWT verification uses
the Supabase project's JWT secret so the frontend
can authenticate with a Supabase access token.
"""
import threading
from typing import Optional

import httpx

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import create_client, Client

from app.config import get_settings

settings = get_settings()

_service_client: Optional[Client] = None
_anon_client: Optional[Client] = None
_client_lock = threading.Lock()


class IngestionError(RuntimeError):
    """Stable base error for atomic ingestion failures."""


class IngestionAuthError(IngestionError):
    """The database rejected the caller identity."""


class IngestionRateLimitError(IngestionError):
    """The caller exhausted their configured ingestion quota."""


def get_client() -> Client:
    """Return the privileged client reserved for offline dataset loaders."""
    global _service_client
    if _service_client is None:
        with _client_lock:
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
    """Return the public read/auth client that is subject to RLS."""
    global _anon_client
    if _anon_client is None:
        with _client_lock:
            if _anon_client is None:
                key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY
                if not settings.SUPABASE_URL or not key:
                    raise RuntimeError(
                        "SUPABASE_URL / SUPABASE_ANON_KEY are not configured."
                    )
                _anon_client = create_client(settings.SUPABASE_URL, key)
    return _anon_client


def create_user_client(access_token: str) -> Client:
    """Create a request-scoped RLS client carrying the caller's JWT."""
    if not access_token:
        raise IngestionAuthError("Authentication is required")
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY are not configured.")
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client


def ingest_claim_atomic(access_token: str, payload: dict) -> dict:
    """Invoke the authenticated database transaction and normalize its errors."""
    try:
        response = create_user_client(access_token).rpc(
            "ingest_claim_atomic", payload
        ).execute()
    except Exception as exc:
        message = str(exc)
        if "INGEST_RATE_LIMITED" in message:
            raise IngestionRateLimitError("Submission rate limit exceeded") from exc
        if "INGEST_UNAUTHORIZED" in message or "JWT" in message.upper():
            raise IngestionAuthError("Authentication is invalid") from exc
        raise IngestionError("Claim ingestion failed") from exc
    if not response.data:
        raise IngestionError("Claim ingestion returned no result")
    return response.data[0]


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

security = HTTPBearer(auto_error=False)

_jwks_cache: Optional[dict] = None
_jwks_lock = threading.Lock()


def _get_jwks(force_refresh: bool = False) -> dict:
    """Fetch (and cache) the Supabase project's public JWKS for asymmetric JWTs."""
    global _jwks_cache
    if _jwks_cache is None or force_refresh:
        with _jwks_lock:
            if _jwks_cache is None or force_refresh:
                url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
                resp = httpx.get(url, timeout=10)
                resp.raise_for_status()
                _jwks_cache = resp.json()
    return _jwks_cache


def _find_jwk(kid: Optional[str]) -> Optional[dict]:
    for refresh in (False, True):
        keys = _get_jwks(force_refresh=refresh).get("keys", [])
        for key in keys:
            if kid is None or key.get("kid") == kid:
                return key
    return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Verify a Supabase access token and return its decoded payload."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    alg = header.get("alg", "HS256")
    try:
        if alg == "HS256":
            # Legacy Supabase shared-secret signing.
            if not settings.SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status_code=500, detail="SUPABASE_JWT_SECRET not configured"
                )
            key = settings.SUPABASE_JWT_SECRET
        else:
            # Current Supabase asymmetric signing (e.g. ES256): verify via JWKS.
            key = _find_jwk(header.get("kid"))
            if key is None:
                raise HTTPException(
                    status_code=401, detail="Invalid authentication token"
                )
        payload = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated",
        )
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception:
        # JWKS fetch failures etc. should not leak internals.
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token missing subject")
    return payload
