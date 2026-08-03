import uuid
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_org_admin, require_org_member, get_current_user
from app.models.document import Document, DocumentStatus
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.schemas.document import DocumentOut
from app.core.file_validation import validate_upload
from app.core.storage import get_storage, FileStorage
from app.core.text_extraction import extract_text, ExtractionError
from app.core.chunking import chunk_text
from app.core.embedding import get_embedding_provider
from app.core.vector_store import get_vector_store
from app.schemas.search import SearchRequest, SearchResultOut

router = APIRouter(prefix="/api/organizations", tags=["documents"])


def _process_extraction(document: Document, file_bytes: bytes, db: Session) -> None:
    """Extract text, then chunk + embed + store vectors.
    status=ready only once the document is genuinely searchable end-to-end;
    a failure at either stage leaves status=failed with a clear reason."""
    try:
        text = extract_text(file_bytes, document.content_type)
        document.extracted_text = text
    except ExtractionError as e:
        document.failure_reason = str(e)
        document.status = DocumentStatus.failed
        db.add(document)
        db.commit()
        db.refresh(document)
        return

    try:
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No chunks produced from extracted text")

        provider = get_embedding_provider()
        embeddings = provider.embed_texts(chunks)

        store = get_vector_store(db)
        store.add(
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
            organization_id=document.organization_id,
            personal_owner_id=document.personal_owner_id,
        )

        document.status = DocumentStatus.ready
    except Exception as e:
        document.failure_reason = f"Embedding failed: {e}"
        document.status = DocumentStatus.failed

    db.add(document)
    db.commit()
    db.refresh(document)


@router.post(
    "/{org_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_organization_document(
    org_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_org_admin),
    storage: FileStorage = Depends(get_storage),
):
    file_bytes = await file.read()

    validate_upload(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(file_bytes),
    )

    storage_path = storage.save(file_bytes, file.filename)

    new_document = Document(
        organization_id=org_id,
        personal_owner_id=None,
        uploaded_by=membership.user_id,
        filename=file.filename,
        storage_path=storage_path,
        content_type=file.content_type,
        size_bytes=len(file_bytes),
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    _process_extraction(new_document, file_bytes, db)

    return new_document


@router.get(
    "/{org_id}/documents",
    response_model=List[DocumentOut],
)
def list_organization_documents(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_org_member),
):
    documents = (
        db.query(Document)
        .filter(Document.organization_id == org_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return documents


@router.post(
    "/{org_id}/documents/search",
    response_model=List[SearchResultOut],
)
def search_organization_documents(
    org_id: uuid.UUID,
    search_in: SearchRequest,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_org_member),
):
    provider = get_embedding_provider()
    query_embedding = provider.embed_texts([search_in.query])[0]

    store = get_vector_store(db)
    results = store.search(
        query_embedding=query_embedding,
        organization_id=org_id,
        personal_owner_id=None,
        top_k=search_in.top_k,
    )

    return [
        SearchResultOut(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            content=r.content,
            distance=r.distance,
        )
        for r in results
    ]

@router.delete(
    "/{org_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organization_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_org_admin),
    storage: FileStorage = Depends(get_storage),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == org_id,
        )
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this organization",
        )

    storage.delete(document.storage_path)
    db.delete(document)  # chunks are removed automatically via ON DELETE CASCADE
    db.commit()

    return None


personal_router = APIRouter(prefix="/api/personal", tags=["documents"])


@personal_router.post(
    "/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_personal_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: FileStorage = Depends(get_storage),
):
    file_bytes = await file.read()

    validate_upload(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(file_bytes),
    )

    storage_path = storage.save(file_bytes, file.filename)

    new_document = Document(
        organization_id=None,
        personal_owner_id=current_user.id,
        uploaded_by=current_user.id,
        filename=file.filename,
        storage_path=storage_path,
        content_type=file.content_type,
        size_bytes=len(file_bytes),
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    _process_extraction(new_document, file_bytes, db)

    return new_document


@personal_router.get(
    "/documents",
    response_model=List[DocumentOut],
)
def list_personal_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    documents = (
        db.query(Document)
        .filter(Document.personal_owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return documents


@personal_router.post(
    "/documents/search",
    response_model=List[SearchResultOut],
)
def search_personal_documents(
    search_in: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = get_embedding_provider()
    query_embedding = provider.embed_texts([search_in.query])[0]

    store = get_vector_store(db)
    results = store.search(
        query_embedding=query_embedding,
        organization_id=None,
        personal_owner_id=current_user.id,
        top_k=search_in.top_k,
    )

    return [
        SearchResultOut(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            content=r.content,
            distance=r.distance,
        )
        for r in results
    ]

@personal_router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_personal_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: FileStorage = Depends(get_storage),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.personal_owner_id == current_user.id,
        )
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    storage.delete(document.storage_path)
    db.delete(document)  # chunks are removed automatically via ON DELETE CASCADE
    db.commit()

    return None