import uuid
from sqlalchemy import Column, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


def _uuid():
    return str(uuid.uuid4())


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=_uuid)
    project = Column(String, nullable=False)
    variant_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    results = relationship(
        "RunScenarioResult",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RunScenarioResult(Base):
    __tablename__ = "run_scenario_results"

    id = Column(String, primary_key=True, default=_uuid)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    scenario_id = Column(String, nullable=False)
    variant_id = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    latency_ms = Column(Float, nullable=False)
    judge_model = Column(String, nullable=False)

    run = relationship("Run", back_populates="results")
