"""Course-level orchestration for resumable Gemini document embeddings."""

from typing import Any, Callable

from services.document_service import list_course_documents
from services.embedding_service import (
    create_embedding_client,
    embed_pending_document_chunks,
)


ProgressCallback = Callable[[int, int, str], None]


def embed_pending_course_documents(
    user_id: str,
    course_slug: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Embed all currently pending, active, ready documents in one course.

    The existing document worker persists every vector independently. This
    coordinator therefore remains safe to rerun: completed chunks are skipped,
    and a failed document does not prevent other documents from being tried.

    Administrator authorization is rechecked through the document inventory
    service before each document is processed. A permission failure aborts the
    batch immediately, while ordinary document/API failures are summarized.
    """

    documents = list_course_documents(user_id, course_slug)
    pending_documents = [
        document
        for document in documents
        if document.get("archived_at") is None
        and document.get("processing_status") == "ready"
        and int(document.get("chunk_count") or 0)
        > int(document.get("embedded_chunk_count") or 0)
    ]

    pending_chunks_before = sum(
        max(
            0,
            int(document.get("chunk_count") or 0)
            - int(document.get("embedded_chunk_count") or 0),
        )
        for document in pending_documents
    )

    if total_documents == 0:
        return {
            "course_slug": course_slug,
            "documents_considered": 0,
            "documents_completed": 0,
            "documents_failed": 0,
            "documents_skipped": 0,
            "chunks_pending_at_start": 0,
            "chunks_saved": 0,
            "chunks_skipped_due_to_concurrent_update": 0,
            "resources": [],
        }

    # Validate credentials and create one client before starting. A missing
    # key should stop the batch once, not produce one failure per document.
    embedding_client = create_embedding_client()

    results: list[dict[str, Any]] = []
    chunks_saved = 0
    chunks_skipped = 0
    documents_completed = 0
    documents_failed = 0
    documents_skipped = 0
    total_documents = len(pending_documents)

    for index, document in enumerate(pending_documents, start=1):
        document_id = str(document["document_id"])
        source_title = str(
            document.get("source_title")
            or document.get("file_name")
            or document_id
        )

        try:
            # Re-read the inventory before each document. This both confirms
            # the administrator is still active and avoids processing a file
            # that was archived or completed by another worker meanwhile.
            current_documents = list_course_documents(user_id, course_slug)
            current = next(
                (
                    item
                    for item in current_documents
                    if str(item.get("document_id")) == document_id
                ),
                None,
            )

            if (
                current is None
                or current.get("archived_at") is not None
                or current.get("processing_status") != "ready"
            ):
                documents_skipped += 1
                results.append({
                    "document_id": document_id,
                    "source_title": source_title,
                    "status": "skipped",
                    "chunks_saved": 0,
                    "error_type": None,
                })
            elif int(current.get("chunk_count") or 0) <= int(
                current.get("embedded_chunk_count") or 0
            ):
                documents_skipped += 1
                results.append({
                    "document_id": document_id,
                    "source_title": source_title,
                    "status": "already_complete",
                    "chunks_saved": 0,
                    "error_type": None,
                })
            else:
                embedding_result = embed_pending_document_chunks(
                    document_id,
                    client=embedding_client,
                )
                saved = int(embedding_result.get("embeddings_saved") or 0)
                skipped = int(
                    embedding_result.get("skipped_due_to_concurrent_update") or 0
                )
                chunks_saved += saved
                chunks_skipped += skipped

                pending_after = (
                    int(embedding_result.get("total_chunks") or 0)
                    - int(embedding_result.get("already_embedded") or 0)
                    - saved
                    - skipped
                )
                if pending_after <= 0:
                    documents_completed += 1
                    status = "completed"
                else:
                    # This can occur if another worker changed the resource
                    # while the job was running. It remains resumable.
                    documents_failed += 1
                    status = "incomplete"

                results.append({
                    "document_id": document_id,
                    "source_title": source_title,
                    "status": status,
                    "chunks_saved": saved,
                    "chunks_pending": max(0, pending_after),
                    "error_type": None,
                })

        except PermissionError:
            # Do not keep processing after the administrator loses access.
            raise
        except Exception as error:
            documents_failed += 1
            results.append({
                "document_id": document_id,
                "source_title": source_title,
                "status": "failed",
                "chunks_saved": 0,
                "error_type": type(error).__name__,
            })

        if progress_callback is not None:
            progress_callback(index, total_documents, source_title)

    return {
        "course_slug": course_slug,
        "documents_considered": total_documents,
        "documents_completed": documents_completed,
        "documents_failed": documents_failed,
        "documents_skipped": documents_skipped,
        "chunks_pending_at_start": pending_chunks_before,
        "chunks_saved": chunks_saved,
        "chunks_skipped_due_to_concurrent_update": chunks_skipped,
        "resources": results,
    }
