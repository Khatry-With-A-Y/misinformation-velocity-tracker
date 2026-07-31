"""Auth schemas (Supabase-backed)."""
from typing import Optional
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Register result: a session token, or a pending email-confirmation status."""
    status: str = "ok"
    message: Optional[str] = None
    access_token: Optional[str] = None
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    username: Optional[str] = None
