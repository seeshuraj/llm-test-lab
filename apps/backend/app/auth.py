from datetime import datetime, timedelta, timezone
import os
import bcrypt
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from .db import get_db
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


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


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

    # Extract raw token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    raw_token = ""
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]

    # --- Try API key first (prefix: ltk_) ---
    if raw_token.startswith("ltk_"):
        res = await db.execute(
            select(models.ApiKey).where(
                models.ApiKey.revoked == False
            )
        )
        all_keys = res.scalars().all()
        matched_key = None
        for k in all_keys:
            if bcrypt.checkpw(raw_token.encode("utf-8"), k.key_hash.encode("utf-8")):
                matched_key = k
                break
        if not matched_key:
            raise credentials_exception
        # Update last_used_at
        matched_key.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        # Load user
        user_res = await db.execute(select(models.User).where(models.User.id == matched_key.user_id))
        user = user_res.scalars().first()
        if not user:
            raise credentials_exception
        return user

    # --- Fall back to JWT ---
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
