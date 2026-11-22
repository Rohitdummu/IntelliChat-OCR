
import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Document(Base):

    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "document_group_id",
            "version",
            name="uq_document_group_version"
        ),
    )

    id = Column(
        String(36),
        primary_key=True,
        index=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    blob_name = Column(
        String(500),
        unique=True,
        nullable=False
    )

    status = Column(
        String(30),
        default="uploaded",
        nullable=False
    )

    analysis_result = Column(JSON, nullable=True)

    structured_result = Column(JSON, nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    claim_id = Column(
        String(36),
        ForeignKey("claims.id"),
        nullable=True,
        index=True
    )

    document_type = Column(
        String(50),
        nullable=True
    )

    # Document version tracking
    document_group_id = Column(
        String(36),
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        index=True
    )

    version = Column(
        Integer,
        default=1,
        nullable=False
    )

    previous_document_id = Column(
        String(36),
        ForeignKey("documents.id"),
        nullable=True,
        index=True
    )

    # Review and resubmission tracking
    review_status = Column(
        String(30),
        default="not_reviewed",
        nullable=False
    )

    resubmission_reason = Column(
        Text,
        nullable=True
    )

    # Claim relationship
    claim = relationship(
        "Claim",
        back_populates="documents"
    )

    # Self-referencing document version relationship
    previous_version = relationship(
        "Document",
        remote_side=[id],
        back_populates="next_versions",
        foreign_keys=[previous_document_id]
    )

    next_versions = relationship(
        "Document",
        back_populates="previous_version",
        foreign_keys=[previous_document_id]
    )
