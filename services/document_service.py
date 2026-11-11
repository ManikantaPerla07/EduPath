
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


def _require_active_admin(cursor, user_id: UUID) -> None:
    """Require an active administrator for knowledge-management operations."""

    cursor.execute(
        """
        SELECT role
        FROM users
        WHERE user_id = %s
          AND is_active = TRUE;
        """,
        (user_id,),
    )
    row = cursor.fetchone()

    if row is None or row[0] != "admin":
        raise PermissionError(
            "An active administrator account is required "
            "to manage educational resources."
        )


def list_admin_courses(user_id: str) -> list[dict[str, Any]]:
    """List courses visible to an authenticated administrator."""

    admin_id = _validate_user_id(user_id)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT course_slug, course_name, is_published
                FROM courses
                ORDER BY course_name, course_slug;
                """
            )
            rows = cursor.fetchall()

    return [
        {
            "course_slug": row[0],
            "course_name": row[1],
            "is_published": row[2],
        }
        for row in rows
    ]


def list_admin_course_topics(
    user_id: str,
    course_slug: str,
) -> list[dict[str, Any]]:
    """List topics for a course after verifying administrator access."""

    admin_id = _validate_user_id(user_id)
    course_slug = _validate_required_text(course_slug, "Course slug")

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT
                    t.topic_slug,
                    t.topic_name,
                    t.sequence_number
                FROM topics AS t
                JOIN courses AS c
                    ON c.course_id = t.course_id
                WHERE c.course_slug = %s
                ORDER BY t.sequence_number, t.topic_name;
                """,
                (course_slug,),
            )
            rows = cursor.fetchall()

    return [
        {
            "topic_slug": row[0],
            "topic_name": row[1],
            "sequence_number": row[2],
        }
        for row in rows
    ]


def list_course_documents(
    user_id: str,
    course_slug: str,
) -> list[dict[str, Any]]:
    """List document metadata and chunk/embedding status for one course.

    Original file bytes and chunk contents are never returned to the UI.
    """

    admin_id = _validate_user_id(user_id)
    course_slug = _validate_required_text(course_slug, "Course slug")

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT
                    d.document_id::TEXT,
                    d.file_name,
                    d.file_sha256,
                    d.file_type,
                    d.file_size_bytes,
                    d.source_title,
                    d.source_license,
                    d.rights_basis,
                    d.processing_status,
                    d.error_message,
                    d.created_at,
                    d.processed_at,
                    d.archived_at,
                    t.topic_slug,
                    t.topic_name,
                    COUNT(dc.chunk_id)::INTEGER AS chunk_count,
                    COUNT(dc.chunk_id) FILTER (
                        WHERE dc.embedding IS NOT NULL
                    )::INTEGER AS embedded_chunk_count
                FROM documents AS d
                JOIN courses AS c
                    ON c.course_id = d.course_id
                LEFT JOIN topics AS t
                    ON t.topic_id = d.topic_id
                   AND t.course_id = d.course_id
                LEFT JOIN document_chunks AS dc
                    ON dc.document_id = d.document_id
                WHERE c.course_slug = %s
                GROUP BY
                    d.document_id,
                    d.file_name,
                    d.file_type,
                    d.file_size_bytes,
                    d.source_title,
                    d.source_license,
                    d.rights_basis,
                    d.processing_status,
                    d.error_message,
                    d.created_at,
                    d.processed_at,
                    d.archived_at,
                    t.topic_slug,
                    t.topic_name
                ORDER BY d.created_at DESC, d.file_name;
                """,
                (course_slug,),
            )
            rows = cursor.fetchall()

    return [
        {
            "document_id": row[0],
            "file_name": row[1],
            "file_sha256": row[2],
            "file_type": row[3],
            "file_size_bytes": row[4],
            "source_title": row[5],
            "source_license": row[6],
            "rights_basis": row[7],
            "processing_status": row[8],
            "error_message": row[9],
            "created_at": row[10],
            "processed_at": row[11],
            "archived_at": row[12],
            "topic_slug": row[13],
            "topic_name": row[14],
            "chunk_count": row[15],
            "embedded_chunk_count": row[16],
        }
        for row in rows
    ]


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


def retry_document_processing(
    user_id: str,
    document_id: str,
) -> dict[str, Any]:
    """Re-extract and rechunk a failed document using its stored original bytes.

    Only active administrators can retry. Chunk replacement and the transition
    to ready happen in one transaction. If processing fails, the document
    remains visibly failed with a safe error summary.
    """

    admin_id = _validate_user_id(user_id)

    try:
        parsed_document_id = UUID(str(document_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid document ID is required.") from None

    database_url = load_database_url()

    with psycopg.connect(
        database_url,
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT
                    file_name,
                    file_type,
                    file_data,
                    source_title,
                    processing_status,
                    archived_at
                FROM documents
                WHERE document_id = %s
                FOR UPDATE;
                """,
                (parsed_document_id,),
            )
            row = cursor.fetchone()

            if row is None:
                raise LookupError("The requested document was not found.")

            (
                file_name,
                file_type,
                file_data,
                source_title,
                status,
                archived_at,
            ) = row

            if archived_at is not None:
                raise ValueError(
                    "Archived documents must be restored before reprocessing."
                )

            if status != "failed":
                raise ValueError(
                    "Only failed documents can be reprocessed."
                )

            cursor.execute(
                """
                UPDATE documents
                SET processing_status = 'processing',
                    error_message = NULL
                WHERE document_id = %s
                  AND processing_status = 'failed';
                """,
                (parsed_document_id,),
            )

    try:
        chunks = process_document(
            file_data=file_data,
            file_name=file_name,
            file_type=file_type,
        )

        if not chunks:
            raise DocumentIngestionError(
                "The stored document did not produce any text chunks."
            )

        with psycopg.connect(
            database_url,
            connect_timeout=20,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = %s;
                    """,
                    (parsed_document_id,),
                )

                chunk_rows = [
                    (
                        parsed_document_id,
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
                    (parsed_document_id,),
                )

                if cursor.fetchone() is None:
                    raise DocumentIngestionError(
                        "The document could not be marked as ready."
                    )

    except Exception as error:
        try:
            _mark_document_failed(
                database_url=database_url,
                document_id=parsed_document_id,
                error=error,
            )
        except Exception as status_error:
            raise DocumentIngestionError(
                "Document retry failed, and its status could not be updated."
            ) from status_error

        raise DocumentIngestionError(
            "Document retry failed. The document remains marked as failed."
        ) from error

    return {
        "document_id": str(parsed_document_id),
        "processing_status": "ready",
        "chunk_count": len(chunks),
        "page_count": len({
            chunk.page_number
            for chunk in chunks
            if chunk.page_number is not None
        }) or (1 if file_type in {"txt", "md"} else 0),
    }

def archive_course_document(
    user_id: str,
    document_id: str,
) -> dict[str, Any]:
    """Soft-archive a document without deleting its file or chunk history.

    If this was the last fully embedded active resource for a published
    course, the same transaction unpublishes the course to prevent learners
    receiving an apparently available course with no searchable source.
    """

    admin_id = _validate_user_id(user_id)

    try:
        parsed_document_id = UUID(str(document_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid document ID is required.") from None

    course_unpublished = False

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT course_id, processing_status, archived_at
                FROM documents
                WHERE document_id = %s
                FOR UPDATE;
                """,
                (parsed_document_id,),
            )
            document = cursor.fetchone()

            if document is None:
                raise LookupError("The requested document was not found.")

            course_id, processing_status, archived_at = document

            if processing_status == "processing":
                raise ValueError(
                    "A document cannot be archived while it is processing."
                )

            if archived_at is not None:
                return {
                    "document_id": str(parsed_document_id),
                    "archived": True,
                    "changed": False,
                    "course_unpublished": False,
                }

            cursor.execute(
                """
                UPDATE documents
                SET archived_at = NOW()
                WHERE document_id = %s
                  AND archived_at IS NULL
                RETURNING archived_at;
                """,
                (parsed_document_id,),
            )
            if cursor.fetchone() is None:
                raise RuntimeError("The document could not be archived.")

            cursor.execute(
                """
                SELECT is_published
                FROM courses
                WHERE course_id = %s
                FOR UPDATE;
                """,
                (course_id,),
            )
            course = cursor.fetchone()

            if course is None:
                raise LookupError("The document's course was not found.")

            if course[0]:
                cursor.execute(
                    """
                    SELECT COUNT(*)::INTEGER
                    FROM (
                        SELECT d.document_id
                        FROM documents AS d
                        LEFT JOIN document_chunks AS dc
                            ON dc.document_id = d.document_id
                        WHERE d.course_id = %s
                          AND d.archived_at IS NULL
                          AND d.processing_status = 'ready'
                        GROUP BY d.document_id
                        HAVING COUNT(dc.chunk_id) > 0
                           AND COUNT(dc.embedding) = COUNT(dc.chunk_id)
                    ) AS searchable_documents;
                    """,
                    (course_id,),
                )
                remaining_searchable = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT
                        COUNT(*)::INTEGER AS topic_count,
                        COUNT(*) FILTER (
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM documents AS topic_document
                                LEFT JOIN document_chunks AS topic_chunk
                                    ON topic_chunk.document_id =
                                        topic_document.document_id
                                WHERE topic_document.course_id = t.course_id
                                  AND topic_document.topic_id = t.topic_id
                                  AND topic_document.archived_at IS NULL
                                  AND topic_document.processing_status = 'ready'
                                GROUP BY topic_document.document_id
                                HAVING COUNT(topic_chunk.chunk_id) > 0
                                   AND COUNT(topic_chunk.embedding) =
                                       COUNT(topic_chunk.chunk_id)
                            )
                        )::INTEGER AS uncovered_topic_count
                    FROM topics AS t
                    WHERE t.course_id = %s;
                    """,
                    (course_id,),
                )
                topic_coverage = cursor.fetchone()
                topic_count, uncovered_topic_count = topic_coverage

                if (
                    remaining_searchable < 1
                    or topic_count < 1
                    or uncovered_topic_count > 0
                ):
                    cursor.execute(
                        """
                        UPDATE courses
                        SET is_published = FALSE,
                            updated_at = NOW()
                        WHERE course_id = %s
                          AND is_published = TRUE;
                        """,
                        (course_id,),
                    )
                    course_unpublished = cursor.rowcount == 1

    return {
        "document_id": str(parsed_document_id),
        "archived": True,
        "changed": True,
        "course_unpublished": course_unpublished,
    }


def restore_course_document(
    user_id: str,
    document_id: str,
) -> dict[str, Any]:
    """Restore an archived document while leaving course publication unchanged."""

    admin_id = _validate_user_id(user_id)

    try:
        parsed_document_id = UUID(str(document_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid document ID is required.") from None

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT processing_status, archived_at
                FROM documents
                WHERE document_id = %s
                FOR UPDATE;
                """,
                (parsed_document_id,),
            )
            document = cursor.fetchone()

            if document is None:
                raise LookupError("The requested document was not found.")

            processing_status, archived_at = document

            if processing_status == "processing":
                raise ValueError(
                    "A document cannot be restored while it is processing."
                )

            if archived_at is None:
                return {
                    "document_id": str(parsed_document_id),
                    "archived": False,
                    "changed": False,
                }

            cursor.execute(
                """
                UPDATE documents
                SET archived_at = NULL
                WHERE document_id = %s
                  AND archived_at IS NOT NULL
                RETURNING document_id;
                """,
                (parsed_document_id,),
            )

            if cursor.fetchone() is None:
                raise RuntimeError("The document could not be restored.")

    return {
        "document_id": str(parsed_document_id),
        "archived": False,
        "changed": True,
    }
