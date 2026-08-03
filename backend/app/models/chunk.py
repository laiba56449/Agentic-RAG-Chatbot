import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base import Base

EMBEDDING_DIMENSIONS = 384  # sentence-transformers/all-MiniLM-L6-v2 output size


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint(
            "(organization_id IS NOT NULL AND personal_owner_id IS NULL) OR "
            "(organization_id IS NULL AND personal_owner_id IS NOT NULL)",
            name="ck_chunk_single_owner",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Denormalized tenant tags — copied from the parent Document at embedding time,
    # so isolation filtering never requires a join back to documents.
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    personal_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    chunk_index = Column(Integer, nullable=False)  # position within the document, 0-based
    content = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())