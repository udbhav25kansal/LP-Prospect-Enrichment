from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_normalized: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True
    )
    org_type: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100))
    is_calibration_anchor: Mapped[bool] = mapped_column(Boolean, default=False)

    contacts = relationship("Contact", back_populates="organization")
    enrichment_results = relationship("EnrichmentResult", back_populates="organization")
    scores = relationship("Score", back_populates="organization")
    validation_flags = relationship("ValidationFlag", back_populates="organization")
