from datetime import datetime, timedelta, timezone
import os
import bcrypt
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from .db import get_db, AsyncSessionLocal
from . import models

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-to-a-random-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Alias used by main.py
def get_password_hash(password: str) -> str:
    return hash_password(password)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict | str) -> str:
    """Accept either a dict ({"sub": user_id}) or a bare user_id string."""
    if isinstance(data, dict):
        user_id = data.get("sub", "")
    else:
        user_id = data
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


async def _update_key_last_used(key_id: str) -> None:
    """Fire-and-forget: update last_used_at in a fresh session."""
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(models.ApiKey).where(models.ApiKey.id == key_id)
            )
            key = res.scalars().first()
            if key:
                key.last_used_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as e:
        print(f"[auth] last_used_at update failed (non-fatal): {e}")


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_token = auth_header[7:].strip()
    if not raw_token:
        raise credentials_exception

    # -------------------------------------------------------------------------
    # Path A: API key (prefix ltk_) — used by CLI / CI
    # -------------------------------------------------------------------------
    if raw_token.startswith("ltk_"):
        prefix = raw_token[:12]

        res = await db.execute(
            select(models.ApiKey).where(
                models.ApiKey.revoked.is_(False),
                models.ApiKey.key_prefix == prefix,
            )
        )
        candidates = res.scalars().all()

        if not candidates:
            res2 = await db.execute(
                select(models.ApiKey).where(
                    models.ApiKey.revoked.is_(False),
                    models.ApiKey.key_prefix.is_(None),
                )
            )
            candidates = res2.scalars().all()

        matched_key = None
        for k in candidates:
            try:
                if bcrypt.checkpw(raw_token.encode("utf-8"), k.key_hash.encode("utf-8")):
                    matched_key = k
                    break
            except Exception:
                continue

        if not matched_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "API key not found or revoked. "
                    "Generate a new key at Settings \u2192 API Keys in the LLM Test Lab dashboard."
                ),
                headers={"WWW-Authenticate": "Bearer"},
            )

        import asyncio
        asyncio.create_task(_update_key_last_used(matched_key.id))

        user_res = await db.execute(
            select(models.User).where(models.User.id == matched_key.user_id)
        )
        user = user_res.scalars().first()
        if not user:
            raise credentials_exception
        return user

    # -------------------------------------------------------------------------
    # Path B: JWT — used by the web dashboard
    # -------------------------------------------------------------------------
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalars().first()
    if user is None:
        raise credentials_exception
    return user


# Stub for main.py import — actual API key auth is handled inside get_current_user
async def verify_api_key(api_key: str, db: AsyncSession) -> models.User:
    raise NotImplementedError("Use get_current_user directly")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(models.User).where(models.User.email == req.email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=req.email,
        hashed_password=hash_password(req.password),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(models.User).where(models.User.email == username))
    user = res.scalars().first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=create_access_token(user.id))
