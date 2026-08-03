import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk


@dataclass
class SearchResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    distance: float


class VectorStore(ABC):
    @abstractmethod
    def add(
        self,
        document_id: uuid.UUID,
        chunks: List[str],
        embeddings: List[List[float]],
        organization_id: Optional[uuid.UUID],
        personal_owner_id: Optional[uuid.UUID],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        organization_id: Optional[uuid.UUID],
        personal_owner_id: Optional[uuid.UUID],
        top_k: int = 5,
    ) -> List[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_document(self, document_id: uuid.UUID) -> None:
        raise NotImplementedError


class PgVectorStore(VectorStore):
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        document_id: uuid.UUID,
        chunks: List[str],
        embeddings: List[List[float]],
        organization_id: Optional[uuid.UUID],
        personal_owner_id: Optional[uuid.UUID],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")

        for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = Chunk(
                document_id=document_id,
                organization_id=organization_id,
                personal_owner_id=personal_owner_id,
                chunk_index=index,
                content=content,
                embedding=embedding,
            )
            self.db.add(chunk)

        self.db.commit()

    def search(
        self,
        query_embedding: List[float],
        organization_id: Optional[uuid.UUID],
        personal_owner_id: Optional[uuid.UUID],
        top_k: int = 5,
    ) -> List[SearchResult]:
        distance_expr = Chunk.embedding.cosine_distance(query_embedding).label("distance")

        query = (
            select(Chunk, distance_expr)
            .order_by(distance_expr)
            .limit(top_k)
        )

        if organization_id is not None:
            query = query.where(Chunk.organization_id == organization_id)
        elif personal_owner_id is not None:
            query = query.where(Chunk.personal_owner_id == personal_owner_id)
        else:
            raise ValueError(
                "Either organization_id or personal_owner_id must be provided"
            )

        rows = self.db.execute(query).all()

        return [
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                distance=float(distance),
            )
            for chunk, distance in rows
        ]

    def delete_by_document(self, document_id: uuid.UUID) -> None:
        self.db.query(Chunk).filter(
            Chunk.document_id == document_id
        ).delete()

        self.db.commit()


def get_vector_store(db: Session) -> VectorStore:
    return PgVectorStore(db)