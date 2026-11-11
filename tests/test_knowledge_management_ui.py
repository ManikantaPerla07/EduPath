"""Tests for the administrator knowledge-management interface."""

import unittest
from unittest.mock import patch

from ui.knowledge_management import (
    _embedding_status,
    _format_file_size,
    render_knowledge_management,
)


class KnowledgeManagementFormattingTests(unittest.TestCase):

    def test_embedding_status_for_complete_document(self):
        self.assertEqual(
            _embedding_status({
                "chunk_count": 8,
                "embedded_chunk_count": 8,
            }),
            "Complete",
        )

    def test_embedding_status_for_pending_document(self):
        self.assertEqual(
            _embedding_status({
                "chunk_count": 8,
                "embedded_chunk_count": 0,
            }),
            "Pending (8 chunks)",
        )

    def test_embedding_status_for_partially_embedded_document(self):
        self.assertEqual(
            _embedding_status({
                "chunk_count": 8,
                "embedded_chunk_count": 3,
            }),
            "Partial (3/8)",
        )

    def test_embedding_status_for_document_without_chunks(self):
        self.assertEqual(
            _embedding_status({
                "chunk_count": 0,
                "embedded_chunk_count": 0,
            }),
            "No chunks",
        )

    def test_formats_file_size_in_megabytes(self):
        self.assertEqual(_format_file_size(1048576), "1.00 MB")


class KnowledgeManagementAccessTests(unittest.TestCase):

    @patch("ui.knowledge_management.st.error")
    @patch("ui.knowledge_management.list_admin_courses")
    def test_student_is_rejected_before_admin_catalog_query(
        self,
        list_courses,
        show_error,
    ):
        render_knowledge_management({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "student",
        })

        show_error.assert_called_once()
        list_courses.assert_not_called()

    @patch("ui.knowledge_management.st.error")
    @patch("ui.knowledge_management.list_admin_courses")
    def test_missing_authenticated_user_id_is_rejected(
        self,
        list_courses,
        show_error,
    ):
        render_knowledge_management({"role": "admin"})

        show_error.assert_called_once()
        list_courses.assert_not_called()


if __name__ == "__main__":
    unittest.main()
