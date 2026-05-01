import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Billing
    is_pro: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    runs: Mapped[list["Run"]] = relationship("Run", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")


class ScenarioDataset(Base):
    """
    A versioned snapshot of a scenarios YAML dataset.

    Each time the YAML content changes for a (project, name) pair, a new
    ScenarioDataset row is created and its parent_version_id points to the
    previous version, forming a linked-list version chain.

    version_hash: SHA-256 of yaml_content (hex). Two rows with the same hash
    have identical content — saves are idempotent on unchanged YAML.
    """
    __tablename__ = "scenario_datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version_hash: Mapped[str] = mapped_column(String, nullable=False)
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    parent_version_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("scenario_datasets.id"), nullable=True
    )

    parent: Mapped[Optional["ScenarioDataset"]] = relationship(
        "ScenarioDataset", remote_side="ScenarioDataset.id", foreign_keys=[parent_version_id]
    )
    runs: Mapped[list["Run"]] = relationship("Run", back_populates="dataset_version")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project: Mapped[str] = mapped_column(String, nullable=False)
    variant_name: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    run_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    scenarios_yaml: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    app_endpoint_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dataset_version_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("scenario_datasets.id"), nullable=True
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

    user: Mapped["User"] = relationship("User", back_populates="runs")
    results: Mapped[list["RunScenarioResult"]] = relationship(
        "RunScenarioResult", back_populates="run", cascade="all, delete-orphan"
    )
    dataset_version: Mapped[Optional["ScenarioDataset"]] = relationship(
        "ScenarioDataset", back_populates="runs"
    )


class RunScenarioResult(Base):
    __tablename__ = "run_scenario_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String, nullable=False)
    variant_id: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    judge_model: Mapped[str] = mapped_column(String, nullable=False)
    rag_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    run: Mapped["Run"] = relationship("Run", back_populates="results")
