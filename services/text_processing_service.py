
"""Extract educational text and split it into source-traceable chunks."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024

SUPPORTED_FILE_TYPES = {"pdf", "txt", "md"}


class DocumentProcessingError(ValueError):
    """Raised when a source document cannot be processed."""


@dataclass(frozen=True)
class ExtractedPage:
    """Normalized text extracted from one page or text document."""

    page_number: int | None
    text: str


@dataclass(frozen=True)
class TextChunk:
    """A text segment with offsets and source metadata."""

    chunk_index: int
    page_number: int | None
    start_char: int
    end_char: int
    content: str
    metadata: dict[str, Any]


def normalize_text(text: str) -> str:
    """Normalize line endings and excessive blank lines.

    Python indentation is preserved.
    """

    if not isinstance(text, str):
        raise DocumentProcessingError("Document text must be a string.")

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _resolve_file_type(
    file_name: str,
    file_type: str | None,
) -> str:
    """Validate the supported document type."""

    if not isinstance(file_name, str) or not file_name.strip():
        raise DocumentProcessingError("A valid file name is required.")

    extension = Path(file_name).suffix.lower().lstrip(".")

    if file_type is None:
        resolved = extension
    else:
        if not isinstance(file_type, str):
            raise DocumentProcessingError("File type must be a string.")
        resolved = file_type.strip().lower()

    if resolved not in SUPPORTED_FILE_TYPES:
        raise DocumentProcessingError(
            "Supported document types are PDF, TXT, and Markdown."
        )

    if extension and extension != resolved:
        raise DocumentProcessingError(
            "The file name extension does not match the supplied file type."
        )

    return resolved


def extract_document_pages(
    file_data: bytes,
    file_name: str,
    file_type: str | None = None,
) -> list[ExtractedPage]:
    """Extract normalized text while retaining PDF page numbers.

    TXT and Markdown files are represented as one text source with
    page_number=None. Character offsets are relative to normalized
    extracted text within each page.
    """

    if not isinstance(file_data, (bytes, bytearray, memoryview)):
        raise DocumentProcessingError("Document content must be bytes.")

    file_data = bytes(file_data)

    if not file_data:
        raise DocumentProcessingError("The uploaded document is empty.")

    if len(file_data) > MAX_DOCUMENT_BYTES:
        raise DocumentProcessingError(
            "The document exceeds the 5 MB processing limit."
        )

    resolved_type = _resolve_file_type(file_name, file_type)

    if resolved_type in {"txt", "md"}:
        try:
            raw_text = file_data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentProcessingError(
                "The text document must use UTF-8 encoding."
            ) from error

        text = normalize_text(raw_text)

        if not text:
            raise DocumentProcessingError(
                "No readable text was found in the document."
            )

        return [ExtractedPage(page_number=None, text=text)]

    try:
        reader = PdfReader(BytesIO(file_data), strict=False)

        if reader.is_encrypted:
            raise DocumentProcessingError(
                "Password-protected PDFs are not supported."
            )

        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = normalize_text(page.extract_text() or "")

            if page_text:
                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=page_text,
                    )
                )

    except DocumentProcessingError:
        raise
    except Exception as error:
        raise DocumentProcessingError(
            "Unable to read or extract text from the PDF."
        ) from error

    if not pages:
        raise DocumentProcessingError(
            "No extractable text was found in the PDF. "
            "Scanned PDFs require OCR, which is not supported yet."
        )

    return pages


def _find_chunk_end(
    text: str,
    start: int,
    chunk_size: int,
) -> int:
    """Prefer natural text boundaries without exceeding chunk_size."""

    hard_end = min(start + chunk_size, len(text))

    if hard_end == len(text):
        return hard_end

    minimum_boundary = start + max(1, chunk_size // 2)

    separators = ("\n\n", "\n", ". ", " ")

    candidates = []

    for separator in separators:
        position = text.rfind(
            separator,
            minimum_boundary,
            hard_end,
        )

        if position >= minimum_boundary:
            candidates.append(position + len(separator))

    return max(candidates) if candidates else hard_end


def chunk_extracted_pages(
    pages: list[ExtractedPage],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    source_name: str | None = None,
    source_type: str | None = None,
) -> list[TextChunk]:
    """Split extracted pages into overlapping, source-traceable chunks.

    Chunks never cross PDF page boundaries. Character offsets refer to
    normalized text on the corresponding page, or the entire text file.
    """

    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise DocumentProcessingError("Chunk size must be an integer.")

    if chunk_size < 1:
        raise DocumentProcessingError("Chunk size must be positive.")

    if isinstance(overlap, bool) or not isinstance(overlap, int):
        raise DocumentProcessingError("Chunk overlap must be an integer.")

    if overlap < 0 or overlap >= chunk_size:
        raise DocumentProcessingError(
            "Overlap must be at least zero and smaller than chunk size."
        )

    if not isinstance(pages, list):
        raise DocumentProcessingError("Pages must be supplied as a list.")

    chunks = []

    for page in pages:
        if not isinstance(page, ExtractedPage):
            raise DocumentProcessingError(
                "Every page must be an ExtractedPage instance."
            )

        text = normalize_text(page.text)

        if not text:
            continue

        start = 0

        while start < len(text):
            end = _find_chunk_end(text, start, chunk_size)

            raw_content = text[start:end]
            content = raw_content.strip()

            if content:
                leading_whitespace = (
                    len(raw_content) - len(raw_content.lstrip())
                )
                trailing_whitespace = (
                    len(raw_content) - len(raw_content.rstrip())
                )

                actual_start = start + leading_whitespace
                actual_end = end - trailing_whitespace

                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        page_number=page.page_number,
                        start_char=actual_start,
                        end_char=actual_end,
                        content=content,
                        metadata={
                            "source_name": source_name,
                            "source_type": source_type,
                        },
                    )
                )

            if end >= len(text):
                break

            next_start = max(
                start + 1,
                actual_end - overlap,
            )

            while next_start < len(text) and text[next_start].isspace():
                next_start += 1

            if next_start <= start:
                next_start = end

            start = next_start

    return chunks


def process_document(
    file_data: bytes,
    file_name: str,
    file_type: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    """Extract and chunk one educational document."""

    resolved_type = _resolve_file_type(file_name, file_type)

    # Import lazily to avoid a module cycle: the LangChain adapter reuses
    # this module's established extraction and chunking functions.
    from services.langchain_document_processing import (
        process_document_with_langchain,
    )

    langchain_chunks = process_document_with_langchain(
        file_data=file_data,
        file_name=file_name,
        file_type=resolved_type,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    return [
        TextChunk(
            chunk_index=document.metadata["chunk_index"],
            page_number=document.metadata["page_number"],
            start_char=document.metadata["start_char"],
            end_char=document.metadata["end_char"],
            content=document.page_content,
            metadata={
                "source_name": file_name,
                "source_type": resolved_type,
            },
        )
        for document in langchain_chunks
    ]
