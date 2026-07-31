"""Authentication routes backed by Supabase Auth.

The frontend posts to /api/auth/login and /api/auth/register and expects a
`{ access_token, token_type }` response. We proxy those to Supabase Auth so
the returned access token is a valid Supabase JWT (verified by get_current_user).
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_anon_client, get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, Token, UserResponse
from app.utils.logger import setup_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = setup_logger(__name__)


@router.post("/register", response_model=Token)
async def register(data: RegisterRequest):
    try:
        res = get_anon_client().auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {"data": {"username": data.username}},
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    session = getattr(res, "session", None)
    if session and getattr(session, "access_token", None):
        return Token(access_token=session.access_token)
    # Email confirmation may be required -> no session yet; ask the client to log in.
    raise HTTPException(
        status_code=202,
        detail="Registration received. Please confirm your email, then log in.",
    )


@router.post("/login", response_model=Token)
async def login(data: LoginRequest):
    try:
        res = get_anon_client().auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    session = getattr(res, "session", None)
    if not session or not getattr(session, "access_token", None):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return Token(access_token=session.access_token)


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    meta = user.get("user_metadata") or {}
    return UserResponse(
        id=user.get("sub"),
        email=user.get("email"),
        username=meta.get("username"),
    )
