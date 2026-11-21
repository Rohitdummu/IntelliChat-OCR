
import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ClaimReview(Base):

    __tablename__ = "claim_reviews"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    claim_id = Column(
        String(36),
        ForeignKey("claims.id"),
        nullable=False,
        index=True
    )

    action = Column(
        String(30),
        nullable=False
    )

    reviewer = Column(
        String(150),
        nullable=False
    )

    comments = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    claim = relationship(
        "Claim",
        back_populates="reviews"
    )
