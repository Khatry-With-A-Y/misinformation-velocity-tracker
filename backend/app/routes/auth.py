"""Authentication routes backed by Supabase Auth.

The frontend posts to /api/auth/login and /api/auth/register and expects a
`{ access_token, token_type }` response. We proxy those to Supabase Auth so
the returned access token is a valid Supabase JWT (verified by get_current_user).
"""
import time

from fastapi import APIRouter, Depends, HTTPException
from gotrue.errors import AuthApiError, AuthRetryableError

from app.core.supabase import get_anon_client, get_current_user
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    Token,
    UserResponse,
)
from app.utils.logger import setup_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = setup_logger(__name__)


@router.post("/register", response_model=RegisterResponse)
async def register(data: RegisterRequest):
    payload = {
        "email": data.email,
        "password": data.password,
        "options": {"data": {"username": data.username}},
    }
    res = None
    # Supabase Auth calls can time out transiently; retry retryable errors once.
    for attempt in range(2):
        try:
            res = get_anon_client().auth.sign_up(payload)
            break
        except AuthRetryableError:
            logger.warning("Supabase sign-up timed out (attempt %d)", attempt + 1)
            if attempt == 1:
                raise HTTPException(
                    status_code=503,
                    detail="Authentication service is temporarily unavailable. Please try again.",
                )
            time.sleep(1)
        except AuthApiError as exc:
            message = str(exc)
            code = str(getattr(exc, "code", ""))
            if code == "user_already_exists" or "already registered" in message.lower():
                logger.info("Registration rejected for an existing account")
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists. Please log in.",
                )
            logger.warning("Supabase rejected registration: %s", message)
            raise HTTPException(status_code=400, detail=message)
        except Exception:
            logger.exception("Registration failed")
            raise HTTPException(
                status_code=502,
                detail="Authentication service could not process the registration.",
            )

    session = getattr(res, "session", None)
    if session and getattr(session, "access_token", None):
        return RegisterResponse(status="ok", access_token=session.access_token)
    # Email confirmation may be required -> no session yet; ask the client to log in.
    return RegisterResponse(
        status="confirmation_required",
        message="Registration received. Please confirm your email, then log in.",
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
