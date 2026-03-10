from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Contact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contacts"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    pipeline_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id")
    )
    contact_name: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(500))
    contact_status: Mapped[str | None] = mapped_column(String(50))
    relationship_depth: Mapped[int] = mapped_column(Integer, nullable=False)

    organization = relationship("Organization", back_populates="contacts")
    pipeline_run = relationship("PipelineRun", back_populates="contacts")
