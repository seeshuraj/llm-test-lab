"""
Epic 4 — Dataset Versioning
============================
Routes:
  POST   /datasets              Save (or no-op if unchanged) a named YAML dataset
  GET    /datasets?project=X    List all versions for a project
  GET    /datasets/{id}         Fetch a specific version
  GET    /datasets/{id}/diff    Line-diff this version vs its parent

Versioning logic:
  Each (project, name) dataset has a version chain. On save:
    1. Hash the submitted YAML (SHA-256).
    2. Fetch the latest version for (project, name).
    3. If hash matches → return existing version (idempotent, no new row).
    4. If hash differs (or no prior version) → insert new row, set
       parent_version_id = latest.id.

This gives a full, immutable audit trail of every dataset change, and
allows runs to reference the exact dataset version they were evaluated on.
"""

from __future__ import annotations

import difflib
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .db import get_db
from .models import ScenarioDataset, User

router = APIRouter(tags=["datasets"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class DatasetSaveRequest(BaseModel):
    project: str
    name: str          # logical name, e.g. "rag-scenarios"
    yaml_content: str  # raw YAML string


class DatasetVersionOut(BaseModel):
    id: str
    project: str
    name: str
    version_hash: str
    created_at: datetime
    parent_version_id: Optional[str]
    # yaml_content omitted from list responses for bandwidth

    model_config = {"from_attributes": True}


class DatasetDetailOut(DatasetVersionOut):
    yaml_content: str


class DatasetDiffOut(BaseModel):
    id: str
    parent_id: Optional[str]
    diff_lines: list[str]   # unified diff lines (empty if no parent)
    unchanged: bool         # True when diff is empty (should only happen if hash collision)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _latest_version(
    db: AsyncSession, project: str, name: str
) -> Optional[ScenarioDataset]:
    """Return the most recently created version for (project, name), or None."""
    result = await db.execute(
        select(ScenarioDataset)
        .where(ScenarioDataset.project == project, ScenarioDataset.name == name)
        .order_by(desc(ScenarioDataset.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=DatasetDetailOut, status_code=201)
async def save_dataset(
    body: DatasetSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a scenario YAML dataset. Creates a new version only if the content
    has changed since the last save (content-addressed via SHA-256).

    Returns the existing version when content is unchanged (HTTP 201 still,
    so CI scripts don't need to distinguish — the returned `id` is stable).
    """
    new_hash = _sha256(body.yaml_content)

    latest = await _latest_version(db, body.project, body.name)

    # Idempotent: same content → return existing version
    if latest and latest.version_hash == new_hash:
        return latest

    dataset = ScenarioDataset(
        id=str(uuid.uuid4()),
        project=body.project,
        name=body.name,
        version_hash=new_hash,
        yaml_content=body.yaml_content,
        created_at=datetime.now(timezone.utc),
        parent_version_id=latest.id if latest else None,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("", response_model=list[DatasetVersionOut])
async def list_datasets(
    project: str = Query(..., description="Filter by project name"),
    name: Optional[str] = Query(None, description="Filter by dataset name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all dataset versions for a project, newest first.
    Optionally filter by dataset name to see the version history of one dataset.
    """
    stmt = (
        select(ScenarioDataset)
        .where(ScenarioDataset.project == project)
        .order_by(desc(ScenarioDataset.created_at))
    )
    if name:
        stmt = stmt.where(ScenarioDataset.name == name)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetDetailOut)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a specific dataset version including full YAML content."""
    dataset = await db.get(ScenarioDataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    return dataset


@router.get("/{dataset_id}/diff", response_model=DatasetDiffOut)
async def diff_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return a unified diff of this version vs its parent.

    - If this is the first version (no parent), diff_lines contains all lines
      as additions and `parent_id` is null.
    - Diff lines follow the unified diff format:
        '--- previous'  / '+++ current'
        '@@ ... @@'
        '-removed line'
        '+added line'
        ' context line'
    """
    dataset = await db.get(ScenarioDataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    parent: Optional[ScenarioDataset] = None
    if dataset.parent_version_id:
        parent = await db.get(ScenarioDataset, dataset.parent_version_id)

    if parent is None:
        # First version — show all lines as additions
        diff_lines = ["+" + line for line in dataset.yaml_content.splitlines()]
        return DatasetDiffOut(
            id=dataset.id,
            parent_id=None,
            diff_lines=diff_lines,
            unchanged=False,
        )

    # Compute unified diff
    a_lines = parent.yaml_content.splitlines(keepends=True)
    b_lines = dataset.yaml_content.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            a_lines,
            b_lines,
            fromfile=f"{dataset.name}@{parent.version_hash[:8]}",
            tofile=f"{dataset.name}@{dataset.version_hash[:8]}",
            lineterm="",
        )
    )

    return DatasetDiffOut(
        id=dataset.id,
        parent_id=parent.id,
        diff_lines=diff,
        unchanged=len(diff) == 0,
    )
