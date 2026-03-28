import secrets
import bcrypt
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from .db import get_db
from .auth import get_current_user
from .models import ApiKey, User

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateKeyRequest(BaseModel):
    name: str  # e.g. "CI / GitHub Actions"


class CreateKeyResponse(BaseModel):
    id: str
    name: str
    key: str          # raw key — shown ONCE, never stored in plain text
    key_prefix: str
    created_at: datetime


class KeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=CreateKeyResponse)
async def create_api_key(
    req: CreateKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new long-lived API key. The raw key is shown once — store it securely."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Key name cannot be empty")

    # Generate a 40-char random key with ltk_ prefix
    raw_key = "ltk_" + secrets.token_urlsafe(40)
    key_prefix = raw_key[:12]  # e.g. ltk_AbCdEfGh
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    api_key = ApiKey(
        user_id=current_user.id,
        name=req.name.strip(),
        key_hash=key_hash,
        key_prefix=key_prefix,
        created_at=datetime.now(timezone.utc),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return CreateKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,   # shown once
        key_prefix=key_prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=List[KeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
    )
    return res.scalars().all()


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    )
    key = res.scalars().first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.revoked = True
    await db.commit()
