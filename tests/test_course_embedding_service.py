"""Tests for the resumable course-level embedding coordinator."""

import unittest
from unittest.mock import call, patch

from services.course_embedding_service import (
    embed_pending_course_documents,
)


USER_ID = "11111111-1111-4111-8111-111111111111"
COURSE_SLUG = "python-basics"


def document(document_id, title, chunks, embedded=0, archived_at=None, status="ready"):
    return {
        "document_id": document_id,
        "source_title": title,
        "file_name": f"{document_id}.md",
        "processing_status": status,
        "archived_at": archived_at,
        "chunk_count": chunks,
        "embedded_chunk_count": embedded,
    }


class CourseEmbeddingCoordinatorTests(unittest.TestCase):

    @patch("services.course_embedding_service.embed_pending_document_chunks")
    @patch("services.course_embedding_service.list_course_documents")
    def test_processes_every_pending_document_and_aggregates_counts(
        self,
        list_documents,
        embed_document,
    ):
        documents = [
            document("doc-a", "Python Basics", 3, 1),
            document("doc-b", "Python Loops", 2, 0),
            document("doc-done", "Already complete", 1, 1),
            document("doc-archived", "Archived", 4, 0, archived_at="archived"),
            document("doc-processing", "Processing", 2, 0, status="processing"),
        ]
        list_documents.return_value = documents
        embed_document.side_effect = [
            {
                "total_chunks": 3,
                "already_embedded": 1,
                "embeddings_saved": 2,
                "skipped_due_to_concurrent_update": 0,
            },
            {
                "total_chunks": 2,
                "already_embedded": 0,
                "embeddings_saved": 2,
                "skipped_due_to_concurrent_update": 0,
            },
        ]
        progress = []

        with patch(
            "services.course_embedding_service.create_embedding_client",
            return_value="shared-client",
        ) as create_client:
            result = embed_pending_course_documents(
                USER_ID,
                COURSE_SLUG,
                progress_callback=lambda current, total, title: progress.append(
                    (current, total, title)
                ),
            )

        create_client.assert_called_once_with()
        self.assertEqual(result["documents_considered"], 2)
        self.assertEqual(result["documents_completed"], 2)
        self.assertEqual(result["documents_failed"], 0)
        self.assertEqual(result["documents_skipped"], 0)
        self.assertEqual(result["chunks_pending_at_start"], 4)
        self.assertEqual(result["chunks_saved"], 4)
        self.assertEqual(
            embed_document.call_args_list,
            [
                call("doc-a", client="shared-client"),
                call("doc-b", client="shared-client"),
            ],
        )
        self.assertEqual(
            progress,
            [(1, 2, "Python Basics"), (2, 2, "Python Loops")],
        )

    @patch("services.course_embedding_service.embed_pending_document_chunks")
    @patch("services.course_embedding_service.list_course_documents")
    def test_continues_after_one_document_failure(
        self,
        list_documents,
        embed_document,
    ):
        docs = [
            document("doc-a", "Python Operators", 2),
            document("doc-b", "Python Conditionals", 3),
        ]
        list_documents.side_effect = [docs, docs, docs]
        embed_document.side_effect = [
            RuntimeError("provider unavailable"),
            {
                "total_chunks": 3,
                "already_embedded": 0,
                "embeddings_saved": 3,
                "skipped_due_to_concurrent_update": 0,
            },
        ]

        with patch(
            "services.course_embedding_service.create_embedding_client",
            return_value="shared-client",
        ):
            result = embed_pending_course_documents(USER_ID, COURSE_SLUG)

        self.assertEqual(result["documents_failed"], 1)
        self.assertEqual(result["documents_completed"], 1)
        self.assertEqual(result["chunks_saved"], 3)
        self.assertEqual(result["resources"][0]["error_type"], "RuntimeError")
        self.assertEqual(embed_document.call_count, 2)

    @patch("services.course_embedding_service.embed_pending_document_chunks")
    @patch("services.course_embedding_service.list_course_documents")
    def test_skips_documents_completed_or_archived_by_another_worker(
        self,
        list_documents,
        embed_document,
    ):
        initial = [document("doc-a", "Python Lists", 2)]
        refreshed = [
            document("doc-a", "Python Lists", 2, embedded=2)
        ]
        list_documents.side_effect = [initial, refreshed]

        with patch(
            "services.course_embedding_service.create_embedding_client",
            return_value="shared-client",
        ):
            result = embed_pending_course_documents(USER_ID, COURSE_SLUG)

        self.assertEqual(result["documents_skipped"], 1)
        self.assertEqual(result["resources"][0]["status"], "already_complete")
        embed_document.assert_not_called()

    @patch("services.course_embedding_service.embed_pending_document_chunks")
    @patch("services.course_embedding_service.list_course_documents")
    def test_aborts_if_admin_access_is_lost_mid_batch(
        self,
        list_documents,
        embed_document,
    ):
        docs = [
            document("doc-a", "Python Functions", 2),
            document("doc-b", "Python Strings", 2),
        ]
        list_documents.side_effect = [
            docs,
            docs,
            PermissionError("Admin access revoked"),
        ]

        with patch(
            "services.course_embedding_service.create_embedding_client",
            return_value="shared-client",
        ):
            with self.assertRaises(PermissionError):
                embed_pending_course_documents(USER_ID, COURSE_SLUG)

        embed_document.assert_called_once_with(
            "doc-a",
            client="shared-client",
        )

    @patch("services.course_embedding_service.embed_pending_document_chunks")
    @patch("services.course_embedding_service.list_course_documents")
    def test_no_pending_documents_does_not_call_embedding_provider(
        self,
        list_documents,
        embed_document,
    ):
        list_documents.return_value = [
            document("doc-done", "Python Strings", 2, embedded=2),
            document("doc-archived", "Old note", 1, archived_at="archived"),
        ]

        with patch(
            "services.course_embedding_service.create_embedding_client"
        ) as create_client:
            result = embed_pending_course_documents(USER_ID, COURSE_SLUG)

        create_client.assert_not_called()
        self.assertEqual(result["documents_considered"], 0)
        self.assertEqual(result["chunks_pending_at_start"], 0)
        self.assertEqual(result["chunks_saved"], 0)
        embed_document.assert_not_called()


if __name__ == "__main__":
    unittest.main()
