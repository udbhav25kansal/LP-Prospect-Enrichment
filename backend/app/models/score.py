from datetime import datetime

from sqlalchemy import String, Numeric, Boolean, Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Score(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scores"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id"), nullable=False
    )
    enrichment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrichment_results.id"), nullable=False
    )

    d1_sector_fit: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    d1_confidence: Mapped[str | None] = mapped_column(String(10))
    d1_reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    d2_relationship: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)

    d3_halo_value: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    d3_confidence: Mapped[str | None] = mapped_column(String(10))
    d3_reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    d4_emerging_fit: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    d4_confidence: Mapped[str | None] = mapped_column(String(10))
    d4_reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    composite_score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)

    check_size_min: Mapped[int | None] = mapped_column(BigInteger)
    check_size_max: Mapped[int | None] = mapped_column(BigInteger)

    is_lp_not_gp: Mapped[bool | None] = mapped_column(Boolean)
    org_type_assessment: Mapped[str | None] = mapped_column(String(100))

    used_default_scores: Mapped[bool] = mapped_column(Boolean, default=False)

    scored_at: Mapped[datetime | None] = mapped_column(DateTime())

    organization = relationship("Organization", back_populates="scores")
    pipeline_run = relationship("PipelineRun", back_populates="scores")
    enrichment = relationship("EnrichmentResult", back_populates="score")
    validation_flags = relationship("ValidationFlag", back_populates="score")
