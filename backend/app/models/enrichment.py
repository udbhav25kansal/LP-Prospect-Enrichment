from datetime import datetime

from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EnrichmentResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "enrichment_results"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id"), nullable=False
    )

    aum_raw: Mapped[str | None] = mapped_column(String(200))
    aum_parsed: Mapped[int | None] = mapped_column()
    investment_mandates: Mapped[list | None] = mapped_column(JSON)
    fund_allocations: Mapped[list | None] = mapped_column(JSON)
    sustainability_focus: Mapped[str | None] = mapped_column(Text)
    emerging_manager_evidence: Mapped[str | None] = mapped_column(Text)
    is_capital_allocator: Mapped[bool | None] = mapped_column(Boolean)
    gp_service_provider_signals: Mapped[list | None] = mapped_column(JSON)
    brand_recognition: Mapped[str | None] = mapped_column(String(20))
    key_findings_summary: Mapped[str | None] = mapped_column(Text)

    tavily_raw_results: Mapped[dict | None] = mapped_column(JSON)
    claude_raw_response: Mapped[str | None] = mapped_column(Text)
    search_queries_used: Mapped[list | None] = mapped_column(JSON)

    # Citation tracking
    sources: Mapped[list | None] = mapped_column(JSON)  # [{index, title, url}, ...]
    field_citations: Mapped[dict | None] = mapped_column(JSON)  # {field: [source_indices]}

    # Deep research
    gemini_raw_response: Mapped[dict | None] = mapped_column(JSON)
    deep_research_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)

    enrichment_status: Mapped[str] = mapped_column(String(20), default="pending")
    data_quality: Mapped[str | None] = mapped_column(String(10))
    error_message: Mapped[str | None] = mapped_column(Text)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime())

    organization = relationship("Organization", back_populates="enrichment_results")
    pipeline_run = relationship("PipelineRun", back_populates="enrichment_results")
    score = relationship("Score", back_populates="enrichment", uselist=False)
