from sqlalchemy import String, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ValidationFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "validation_flags"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    score_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scores.id"), nullable=False
    )
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id"), nullable=False
    )

    flag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    organization = relationship("Organization", back_populates="validation_flags")
    score = relationship("Score", back_populates="validation_flags")
    pipeline_run = relationship("PipelineRun", back_populates="validation_flags")
