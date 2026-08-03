import io
from docx import Document as DocxDocument
from pypdf import PdfReader


class ExtractionError(Exception):
    """Raised when text cannot be extracted from a document."""
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(text_parts).strip()
    except Exception as e:
        raise ExtractionError(f"Failed to read PDF: {e}")

    if not text:
        raise ExtractionError(
            "No extractable text found in PDF (it may be scanned/image-based)."
        )

    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        raise ExtractionError(f"Failed to read DOCX: {e}")

    if not text:
        raise ExtractionError("No extractable text found in DOCX.")

    return text


def extract_text_from_txt(file_bytes: bytes) -> str:
    try:
        # utf-8-sig removes BOM characters like ï»¿
        text = file_bytes.decode("utf-8-sig").strip()
    except UnicodeDecodeError as e:
        raise ExtractionError(f"Failed to decode TXT as UTF-8: {e}")

    if not text:
        raise ExtractionError("TXT file contains no text.")

    return text


EXTRACTORS = {
    "application/pdf": extract_text_from_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_text_from_docx,
    "text/plain": extract_text_from_txt,
}


def extract_text(file_bytes: bytes, content_type: str) -> str:
    extractor = EXTRACTORS.get(content_type)

    if extractor is None:
        raise ExtractionError(
            f"No extractor available for content type '{content_type}'."
        )

    return extractor(file_bytes)