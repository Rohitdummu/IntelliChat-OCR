from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Claim(Base):

    __tablename__ = "claims"

    id = Column(
        String(36),
        primary_key=True,
        index=True
    )

    claim_number = Column(
        String(40),
        unique=True,
        nullable=False,
        index=True
    )

    insured_person_name = Column(
        String(150),
        nullable=False
    )

    policy_number = Column(
        String(100),
        nullable=False,
        index=True
    )

    patient_name = Column(
        String(150),
        nullable=True
    )

    hospital_name = Column(
        String(255),
        nullable=True
    )

    status = Column(
        String(30),
        default="awaiting_documents",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    validation_result = Column(JSON, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # One claim can have multiple documents
    documents = relationship(
        "Document",
        back_populates="claim"
    )

    reviews = relationship(
        "ClaimReview",
        back_populates="claim",
        cascade="all, delete-orphan"
    )