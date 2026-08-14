from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        UniqueConstraint(
            "fingerprint",
            name="uq_jobs_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ---------------------------------------------------------
    # SOURCE INFORMATION
    # ---------------------------------------------------------

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    source_job_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # ---------------------------------------------------------
    # JOB INFORMATION
    # ---------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ---------------------------------------------------------
    # ANALYSIS
    # ---------------------------------------------------------

    match_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    eligibility_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    recommendation: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    risk_severity: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    risk_flags: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Store the detailed analysis so we don't have to
    # recalculate it every time the dashboard loads.

    analysis: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ---------------------------------------------------------
    # TIMESTAMPS
    # ---------------------------------------------------------

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )