"""Tests for administrator-only educational document management services."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.document_service import (
    list_admin_courses,
    list_admin_course_topics,
    list_course_documents,
    retry_document_processing,
)
from services.text_processing_service import TextChunk


ADMIN_ID = "11111111-1111-4111-8111-111111111111"
COURSE_ID = UUID("22222222-2222-4222-8222-222222222222")
DOCUMENT_ID = UUID("33333333-3333-4333-8333-333333333333")


def make_connection(cursor):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    cursor_context.__exit__.return_value = False

    connection.cursor.return_value = cursor_context
    return connection


def make_cursor(fetchone=None, fetchall=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    return cursor


class AdminDocumentListingTests(unittest.TestCase):

    def test_lists_courses_only_after_admin_authorization(self):
        cursor = make_cursor(
            fetchone=("admin",),
            fetchall=[
                ("python-basics", "Python Programming", False),
            ],
        )
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            courses = list_admin_courses(ADMIN_ID)

        self.assertEqual(
            courses,
            [{
                "course_slug": "python-basics",
                "course_name": "Python Programming",
                "is_published": False,
            }],
        )
        self.assertEqual(cursor.execute.call_count, 2)

    def test_student_cannot_list_admin_courses(self):
        cursor = make_cursor(fetchone=("student",))
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(PermissionError):
                list_admin_courses(ADMIN_ID)

        self.assertEqual(cursor.execute.call_count, 1)

    def test_lists_course_topics_in_curriculum_order(self):
        cursor = make_cursor(
            fetchone=("admin",),
            fetchall=[
                ("variables-data-types", "Variables and Data Types", 1),
                ("operators-expressions", "Operators and Expressions", 2),
            ],
        )
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            topics = list_admin_course_topics(
                ADMIN_ID,
                "python-basics",
            )

        self.assertEqual(len(topics), 2)
        self.assertEqual(topics[0]["sequence_number"], 1)
        self.assertEqual(topics[1]["topic_slug"], "operators-expressions")

    def test_lists_document_status_without_returning_file_bytes(self):
        from datetime import datetime, timezone

        created_at = datetime(2026, 11, 11, tzinfo=timezone.utc)
        row = (
            str(DOCUMENT_ID),
            "python-notes.pdf",
            "pdf",
            1024,
            "Python Notes",
            "CC BY 4.0",
            "open_license",
            "ready",
            None,
            created_at,
            created_at,
            None,
            "Variables and Data Types",
            8,
            5,
        )
        cursor = make_cursor(
            fetchone=("admin",),
            fetchall=[row],
        )
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            documents = list_course_documents(
                ADMIN_ID,
                "python-basics",
            )

        self.assertEqual(documents[0]["chunk_count"], 8)
        self.assertEqual(documents[0]["embedded_chunk_count"], 5)
        self.assertEqual(documents[0]["processing_status"], "ready")
        query = cursor.execute.call_args_list[-1].args[0]
        self.assertNotIn("file_data", query)
        self.assertNotIn("dc.content", query)

    def test_invalid_user_id_is_rejected_before_database_access(self):
        with (
            patch("services.document_service.load_database_url") as load_url,
            patch("services.document_service.psycopg.connect") as connect,
        ):
            with self.assertRaises(ValueError):
                list_admin_courses("not-a-uuid")

            load_url.assert_not_called()
            connect.assert_not_called()

    def test_empty_course_slug_is_rejected(self):
        with patch("services.document_service.psycopg.connect") as connect:
            with self.assertRaises(ValueError):
                list_course_documents(ADMIN_ID, " ")

            connect.assert_not_called()


class DocumentArchivalTests(unittest.TestCase):

    def test_archiving_last_searchable_resource_unpublishes_course(self):
        from datetime import datetime, timezone
        from services.document_service import archive_course_document

        archived_at = datetime(2026, 11, 11, tzinfo=timezone.utc)
        cursor = make_cursor()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, "ready", None),
            (archived_at,),
            (True,),
            (0,),
        ]
        cursor.rowcount = 1
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            result = archive_course_document(
                ADMIN_ID,
                str(DOCUMENT_ID),
            )

        self.assertTrue(result["archived"])
        self.assertTrue(result["changed"])
        self.assertTrue(result["course_unpublished"])
        statements = [
            call.args[0]
            for call in cursor.execute.call_args_list
        ]
        self.assertTrue(
            any("SET archived_at = NOW()" in sql for sql in statements)
        )
        self.assertTrue(
            any(
                "SET is_published = FALSE" in sql
                for sql in statements
            )
        )
        self.assertFalse(
            any("DELETE FROM documents" in sql for sql in statements)
        )

    def test_archiving_one_of_multiple_resources_keeps_course_published(self):
        from datetime import datetime, timezone
        from services.document_service import archive_course_document

        cursor = make_cursor()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, "ready", None),
            (datetime(2026, 11, 11, tzinfo=timezone.utc),),
            (True,),
            (1,),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            result = archive_course_document(
                ADMIN_ID,
                str(DOCUMENT_ID),
            )

        self.assertFalse(result["course_unpublished"])
        self.assertFalse(
            any(
                "SET is_published = FALSE" in call.args[0]
                for call in cursor.execute.call_args_list
            )
        )

    def test_archiving_processing_document_is_rejected(self):
        from services.document_service import archive_course_document

        cursor = make_cursor()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, "processing", None),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "while it is processing"):
                archive_course_document(ADMIN_ID, str(DOCUMENT_ID))

    def test_student_cannot_archive_documents(self):
        from services.document_service import archive_course_document

        cursor = make_cursor(fetchone=("student",))
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(PermissionError):
                archive_course_document(ADMIN_ID, str(DOCUMENT_ID))

        self.assertEqual(cursor.execute.call_count, 1)

    def test_restoring_preserves_chunks_and_embeddings(self):
        from datetime import datetime, timezone
        from services.document_service import restore_course_document

        cursor = make_cursor()
        cursor.fetchone.side_effect = [
            ("admin",),
            (
                "ready",
                datetime(2026, 11, 11, tzinfo=timezone.utc),
            ),
            (DOCUMENT_ID,),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            result = restore_course_document(
                ADMIN_ID,
                str(DOCUMENT_ID),
            )

        self.assertFalse(result["archived"])
        self.assertTrue(result["changed"])
        statements = [
            call.args[0]
            for call in cursor.execute.call_args_list
        ]
        self.assertTrue(
            any("SET archived_at = NULL" in sql for sql in statements)
        )
        self.assertFalse(
            any("DELETE FROM document_chunks" in sql for sql in statements)
        )


class FailedDocumentRetryTests(unittest.TestCase):

    def test_retries_failed_document_and_replaces_chunks_atomically(self):
        first_cursor = make_cursor(fetchone=("admin",))
        first_cursor.fetchone.side_effect = [
            ("admin",),
            (
                "python.txt",
                "txt",
                b"Python variables",
                "Python Notes",
                "failed",
                None,
            ),
        ]
        first_connection = make_connection(first_cursor)

        second_cursor = make_cursor(fetchone=(DOCUMENT_ID,))
        second_connection = make_connection(second_cursor)

        chunks = [
            TextChunk(
                chunk_index=0,
                page_number=None,
                start_char=0,
                end_char=16,
                content="Python variables",
                metadata={"source_name": "python.txt"},
            )
        ]

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=chunks,
            ) as process,
            patch(
                "services.document_service.psycopg.connect",
                side_effect=[first_connection, second_connection],
            ) as connect,
        ):
            result = retry_document_processing(
                ADMIN_ID,
                str(DOCUMENT_ID),
            )

        self.assertEqual(result["processing_status"], "ready")
        self.assertEqual(result["chunk_count"], 1)
        process.assert_called_once_with(
            file_data=b"Python variables",
            file_name="python.txt",
            file_type="txt",
        )
        self.assertEqual(connect.call_count, 2)
        self.assertIn(
            "DELETE FROM document_chunks",
            second_cursor.execute.call_args_list[0].args[0],
        )
        self.assertEqual(second_cursor.executemany.call_count, 1)

    def test_failed_reprocessing_preserves_failed_status(self):
        from services.document_service import DocumentIngestionError

        first_cursor = make_cursor()
        first_cursor.fetchone.side_effect = [
            ("admin",),
            ("python.txt", "txt", b"bad stored text", "Notes", "failed", None),
        ]
        first_connection = make_connection(first_cursor)

        failure_cursor = make_cursor()
        failure_connection = make_connection(failure_cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                side_effect=ValueError("Invalid stored document"),
            ),
            patch(
                "services.document_service.psycopg.connect",
                side_effect=[first_connection, failure_connection],
            ),
        ):
            with self.assertRaises(DocumentIngestionError):
                retry_document_processing(
                    ADMIN_ID,
                    str(DOCUMENT_ID),
                )

        failure_sql = failure_cursor.execute.call_args.args[0]
        self.assertIn("processing_status = 'failed'", failure_sql)
        self.assertIn("ValueError", failure_cursor.execute.call_args.args[1][0])

    def test_rejects_non_failed_document(self):
        cursor = make_cursor()
        cursor.fetchone.side_effect = [
            ("admin",),
            ("python.txt", "txt", b"Python", "Notes", "ready", None),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
            patch("services.document_service.process_document") as process,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Only failed documents",
            ):
                retry_document_processing(
                    ADMIN_ID,
                    str(DOCUMENT_ID),
                )

            process.assert_not_called()

    def test_rejects_student_before_loading_document(self):
        cursor = make_cursor(fetchone=("student",))
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
            patch("services.document_service.process_document") as process,
        ):
            with self.assertRaises(PermissionError):
                retry_document_processing(
                    ADMIN_ID,
                    str(DOCUMENT_ID),
                )

            process.assert_not_called()

    def test_invalid_document_id_is_rejected_before_database_access(self):
        with (
            patch("services.document_service.load_database_url") as load_url,
            patch("services.document_service.psycopg.connect") as connect,
        ):
            with self.assertRaises(ValueError):
                retry_document_processing(ADMIN_ID, "invalid")

            load_url.assert_not_called()
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
