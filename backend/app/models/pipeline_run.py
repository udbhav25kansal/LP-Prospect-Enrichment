from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PipelineRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pipeline_runs"

    started_at: Mapped[datetime | None] = mapped_column(DateTime())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_orgs: Mapped[int] = mapped_column(Integer, default=0)
    processed_orgs: Mapped[int] = mapped_column(Integer, default=0)
    failed_orgs: Mapped[int] = mapped_column(Integer, default=0)
    source_filename: Mapped[str | None] = mapped_column(String(255))
    config_snapshot: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    activity_log: Mapped[list | None] = mapped_column(JSON, default=list)

    contacts = relationship("Contact", back_populates="pipeline_run")
    enrichment_results = relationship("EnrichmentResult", back_populates="pipeline_run")
    scores = relationship("Score", back_populates="pipeline_run")
    validation_flags = relationship("ValidationFlag", back_populates="pipeline_run")
    cost_logs = relationship("APICostLog", back_populates="pipeline_run")
