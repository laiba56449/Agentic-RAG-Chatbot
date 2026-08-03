import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    Enum,
    Integer,
    CheckConstraint,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "(organization_id IS NOT NULL AND personal_owner_id IS NULL) OR "
            "(organization_id IS NULL AND personal_owner_id IS NOT NULL)",
            name="ck_document_single_owner",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
    )

    personal_owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)

    status = Column(
        Enum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.uploaded,
    )

    extracted_text = Column(Text, nullable=True)
    failure_reason = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )