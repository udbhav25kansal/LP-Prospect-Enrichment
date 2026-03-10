from sqlalchemy import String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class APICostLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "api_cost_logs"

    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id"), nullable=False
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id")
    )

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)

    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    search_credits: Mapped[int | None] = mapped_column(Integer)

    estimated_cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 6), nullable=False
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    pipeline_run = relationship("PipelineRun", back_populates="cost_logs")
