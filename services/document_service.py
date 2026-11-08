
"""Admin-controlled ingestion of educational documents into Neon."""

from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from services.assessment_service import load_database_url
from services.text_processing_service import (
    MAX_DOCUMENT_BYTES,
    process_document,
)


_ALLOWED_RIGHTS_BASES = {
    "original",
    "public_domain",
    "open_license",
    "permission_obtained",
    "user_has_rights",
}

_ALLOWED_FILE_TYPES = {"pdf", "txt", "md"}


class DocumentIngestionError(RuntimeError):
    """Raised when an educational document cannot be ingested."""


def _validate_user_id(user_id: str) -> UUID:
    """Validate and normalize the uploader's UUID."""

    try:
        return UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid uploader user ID is required.") from None


def _validate_required_text(value: str, field_name: str) -> str:
    """Validate required metadata text."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required.")

    return value.strip()


def _validate_file_name(file_name: str) -> tuple[str, str]:
    """Validate a safe filename and determine its file type."""

    file_name = _validate_required_text(file_name, "File name")

    if (
        "/" in file_name
        or "\\" in file_name
        or "\x00" in file_name
        or file_name in {".", ".."}
    ):
        raise ValueError("Only a file name, not a file path, is accepted.")

    file_type = Path(file_name).suffix.lower().lstrip(".")

    if file_type not in _ALLOWED_FILE_TYPES:
        raise ValueError("File must be a PDF, TXT, or Markdown document.")

    return file_name, file_type


def _validate_file_data(file_data: bytes) -> bytes:
    """Validate document bytes and the database file-size limit."""

    if not isinstance(file_data, (bytes, bytearray, memoryview)):
        raise ValueError("Document content must be bytes.")

    file_data = bytes(file_data)

    if not file_data:
        raise ValueError("Document content cannot be empty.")

    if len(file_data) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 5 MB size limit.")

    return file_data


def _mark_document_failed(
    database_url: str,
    document_id: UUID,
    error: Exception,
) -> None:
    """Record a safe processing error without exposing SQL details."""

    safe_message = (
        f"Chunk persistence failed: {type(error).__name__}"
    )[:500]

    with psycopg.connect(
        database_url,
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET processing_status = 'failed',
                    error_message = %s
                WHERE document_id = %s
                  AND processing_status = 'processing';
                """,
                (safe_message, document_id),
            )


def ingest_document(
    user_id: str,
    course_slug: str,
    file_name: str,
    file_data: bytes,
    source_title: str,
    source_license: str,
    rights_basis: str,
    topic_slug: str | None = None,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> dict[str, Any]:
    """Store an approved document and its extracted text chunks.

    Only active admin users can add shared educational resources.

    The original document is first recorded with processing status.
    All chunks are inserted in a separate transaction. The document
    becomes ready only after every chunk has been saved successfully.
    """

    uploader_id = _validate_user_id(user_id)

    course_slug = _validate_required_text(
        course_slug,
        "Course slug",
    )

    file_name, file_type = _validate_file_name(file_name)
    file_data = _validate_file_data(file_data)

    source_title = _validate_required_text(
        source_title,
        "Source title",
    )

    source_license = _validate_required_text(
        source_license,
        "Source license",
    )

    if not isinstance(rights_basis, str):
        raise ValueError("A valid rights basis is required.")

    rights_basis = rights_basis.strip()

    if rights_basis not in _ALLOWED_RIGHTS_BASES:
        raise ValueError(
            "Rights basis must be original, public_domain, "
            "open_license, permission_obtained, or user_has_rights."
        )

    if topic_slug is not None:
        topic_slug = _validate_required_text(
            topic_slug,
            "Topic slug",
        )

    file_hash = sha256(file_data).hexdigest()

    # Extraction and chunking happen before opening a database transaction.
    chunks = process_document(
        file_data=file_data,
        file_name=file_name,
        file_type=file_type,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    if not chunks:
        raise ValueError("The document did not produce any text chunks.")

    database_url = load_database_url()

    document_id = None
    course_id = None
    topic_id = None

    # Transaction 1: verify permissions and save the original document.
    try:
        with psycopg.connect(
            database_url,
            connect_timeout=20,
        ) as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT role
                    FROM users
                    WHERE user_id = %s
                      AND is_active = TRUE
                    FOR SHARE;
                    """,
                    (uploader_id,),
                )
                uploader = cursor.fetchone()

                if uploader is None:
                    raise PermissionError(
                        "An active uploader account is required."
                    )

                if uploader[0] != "admin":
                    raise PermissionError(
                        "Only active administrators can upload "
                        "shared educational resources."
                    )

                cursor.execute(
                    """
                    SELECT course_id
                    FROM courses
                    WHERE course_slug = %s;
                    """,
                    (course_slug,),
                )
                course = cursor.fetchone()

                if course is None:
                    raise ValueError("The selected course was not found.")

                course_id = course[0]

                if topic_slug is not None:
                    cursor.execute(
                        """
                        SELECT topic_id
                        FROM topics
                        WHERE course_id = %s
                          AND topic_slug = %s;
                        """,
                        (course_id, topic_slug),
                    )
                    topic = cursor.fetchone()

                    if topic is None:
                        raise ValueError(
                            "The selected topic does not belong "
                            "to the selected course."
                        )

                    topic_id = topic[0]

                cursor.execute(
                    """
                    INSERT INTO documents (
                        course_id,
                        topic_id,
                        uploaded_by,
                        file_name,
                        file_type,
                        file_size_bytes,
                        file_data,
                        file_sha256,
                        source_title,
                        source_license,
                        rights_basis,
                        processing_status
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, 'processing'
                    )
                    RETURNING document_id;
                    """,
                    (
                        course_id,
                        topic_id,
                        uploader_id,
                        file_name,
                        file_type,
                        len(file_data),
                        file_data,
                        file_hash,
                        source_title,
                        source_license,
                        rights_basis,
                    ),
                )

                document_row = cursor.fetchone()

                if document_row is None:
                    raise DocumentIngestionError(
                        "The document could not be registered."
                    )

                document_id = document_row[0]

    except psycopg.errors.UniqueViolation as error:
        raise ValueError(
            "This document has already been uploaded to this course."
        ) from error

    # Transaction 2: insert every chunk and mark the document ready.
    try:
        with psycopg.connect(
            database_url,
            connect_timeout=20,
        ) as connection:
            with connection.cursor() as cursor:

                chunk_rows = [
                    (
                        document_id,
                        chunk.chunk_index,
                        chunk.page_number,
                        chunk.start_char,
                        chunk.end_char,
                        chunk.content,
                        Jsonb(chunk.metadata),
                    )
                    for chunk in chunks
                ]

                cursor.executemany(
                    """
                    INSERT INTO document_chunks (
                        document_id,
                        chunk_index,
                        page_number,
                        start_char,
                        end_char,
                        content,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    chunk_rows,
                )

                cursor.execute(
                    """
                    UPDATE documents
                    SET processing_status = 'ready',
                        error_message = NULL,
                        processed_at = NOW()
                    WHERE document_id = %s
                      AND processing_status = 'processing'
                    RETURNING document_id;
                    """,
                    (document_id,),
                )

                ready_row = cursor.fetchone()

                if ready_row is None:
                    raise DocumentIngestionError(
                        "The document could not be marked as ready."
                    )

    except Exception as error:
        try:
            _mark_document_failed(
                database_url=database_url,
                document_id=document_id,
                error=error,
            )
        except Exception as status_error:
            raise DocumentIngestionError(
                "Chunk persistence failed, and the document status "
                "could not be updated."
            ) from status_error

        raise DocumentIngestionError(
            "The document was registered, but its chunks could "
            "not be saved. Its processing status was marked failed."
        ) from error

    return {
        "document_id": str(document_id),
        "course_slug": course_slug,
        "topic_slug": topic_slug,
        "file_name": file_name,
        "file_type": file_type,
        "file_size_bytes": len(file_data),
        "file_sha256": file_hash,
        "source_title": source_title,
        "source_license": source_license,
        "rights_basis": rights_basis,
        "processing_status": "ready",
        "chunk_count": len(chunks),
        "page_count": len({
            chunk.page_number
            for chunk in chunks
            if chunk.page_number is not None
        }) or (1 if file_type in {"txt", "md"} else 0),
    }
