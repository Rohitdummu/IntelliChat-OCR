
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)

    filename = Column(String(255), nullable=False)

    blob_name = Column(String(500), unique=True, nullable=False)

    status = Column(
        String(30),
        default="uploaded",
        nullable=False
    )

    analysis_result = Column(JSON, nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    structured_result = Column(JSON, nullable=True)

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
    
    claim = relationship(
        "Claim",
        back_populates="documents"
    )
