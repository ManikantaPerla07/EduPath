
"""Unit tests for the educational document-ingestion service."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

import psycopg

from services.document_service import (
    DocumentIngestionError,
    ingest_document,
)
from services.text_processing_service import TextChunk


USER_ID = "11111111-1111-4111-8111-111111111111"
COURSE_ID = UUID("22222222-2222-4222-8222-222222222222")
DOCUMENT_ID = UUID("33333333-3333-4333-8333-333333333333")
TOPIC_ID = UUID("44444444-4444-4444-8444-444444444444")

SAMPLE_CHUNKS = [
    TextChunk(
        chunk_index=0,
        page_number=None,
        start_char=0,
        end_char=16,
        content="Python functions",
        metadata={
            "source_name": "python.txt",
            "source_type": "txt",
        },
    )
]


def make_connection(cursor):
    """Create a mocked Psycopg connection and cursor context."""

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    cursor_context.__exit__.return_value = False

    connection.cursor.return_value = cursor_context

    return connection


def make_cursor(fetch_results=None):
    cursor = MagicMock()

    if fetch_results is not None:
        cursor.fetchone.side_effect = fetch_results

    return cursor


class DocumentIngestionValidationTests(unittest.TestCase):

    def test_invalid_user_id_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_document(
                user_id="invalid",
                course_slug="python-basics",
                file_name="python.txt",
                file_data=b"Python functions",
                source_title="Python Notes",
                source_license="Original",
                rights_basis="original",
            )

    def test_empty_course_slug_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                " ",
                "python.txt",
                b"Python",
                "Python Notes",
                "Original",
                "original",
            )

    def test_empty_source_title_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.txt",
                b"Python",
                " ",
                "Original",
                "original",
            )

    def test_empty_source_license_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.txt",
                b"Python",
                "Python Notes",
                "",
                "original",
            )

    def test_invalid_rights_basis_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.txt",
                b"Python",
                "Python Notes",
                "Original",
                "unknown",
            )

    def test_rejects_file_path(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "folder/python.txt",
                b"Python",
                "Python Notes",
                "Original",
                "original",
            )

    def test_rejects_unsupported_file_extension(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.docx",
                b"Python",
                "Python Notes",
                "Original",
                "original",
            )

    def test_rejects_empty_file(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.txt",
                b"",
                "Python Notes",
                "Original",
                "original",
            )

    def test_rejects_file_larger_than_five_mb(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.txt",
                b"x" * (5 * 1024 * 1024 + 1),
                "Python Notes",
                "Original",
                "original",
            )

    def test_invalid_topic_slug_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_document(
                USER_ID,
                "python-basics",
                "python.txt",
                b"Python",
                "Python Notes",
                "Original",
                "original",
                topic_slug=" ",
            )


    def test_non_bytes_file_is_rejected_before_database_access(self):
        with (
            patch(
                "services.document_service.load_database_url"
            ) as load_url,
            patch(
                "services.document_service.process_document"
            ) as process,
        ):
            with self.assertRaises(ValueError):
                ingest_document(
                    user_id=USER_ID,
                    course_slug="python-basics",
                    file_name="python.txt",
                    file_data="Python",
                    source_title="Python Notes",
                    source_license="Original",
                    rights_basis="original",
                )

            load_url.assert_not_called()
            process.assert_not_called()



class DocumentIngestionDatabaseTests(unittest.TestCase):

    def _valid_arguments(self):
        return {
            "user_id": USER_ID,
            "course_slug": "python-basics",
            "file_name": "python.txt",
            "file_data": b"Python functions",
            "source_title": "Python Notes",
            "source_license": "Original",
            "rights_basis": "original",
        }

    def _run_with_mocks(
        self,
        connections,
        fetch_results=None,
        chunks=SAMPLE_CHUNKS,
    ):
        first_cursor = make_cursor(fetch_results)
        first_connection = make_connection(first_cursor)

        chunk_cursor = make_cursor([(DOCUMENT_ID,)])
        chunk_connection = make_connection(chunk_cursor)

        connections_to_use = [first_connection, chunk_connection]

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=chunks,
            ),
            patch(
                "services.document_service.psycopg.connect",
                side_effect=connections_to_use,
            ) as connect,
        ):
            result = ingest_document(**self._valid_arguments())

        return result, first_cursor, chunk_cursor, connect

    def test_successful_ingestion_saves_document_and_chunks(self):
        first_cursor = make_cursor([
            ("admin",),
            (COURSE_ID,),
            (DOCUMENT_ID,),
        ])
        first_connection = make_connection(first_cursor)

        chunk_cursor = make_cursor([(DOCUMENT_ID,)])
        chunk_connection = make_connection(chunk_cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                side_effect=[first_connection, chunk_connection],
            ) as connect,
        ):
            result = ingest_document(**self._valid_arguments())

        self.assertEqual(result["document_id"], str(DOCUMENT_ID))
        self.assertEqual(result["processing_status"], "ready")
        self.assertEqual(result["chunk_count"], 1)
        self.assertEqual(result["file_type"], "txt")
        self.assertEqual(connect.call_count, 2)

        insert_sql = first_cursor.execute.call_args_list[-1].args[0]
        self.assertIn("INSERT INTO documents", insert_sql)

        self.assertEqual(chunk_cursor.executemany.call_count, 1)

        chunk_insert_sql = (
            chunk_cursor.executemany.call_args.args[0]
        )
        self.assertIn("INSERT INTO document_chunks", chunk_insert_sql)

        self.assertIn(
            "UPDATE documents",
            chunk_cursor.execute.call_args.args[0],
        )

    def test_inactive_or_missing_uploader_is_rejected(self):
        cursor = make_cursor([None])
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(PermissionError):
                ingest_document(**self._valid_arguments())

        self.assertEqual(cursor.execute.call_count, 1)

    def test_student_cannot_upload_shared_resources(self):
        cursor = make_cursor([("student",)])
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(PermissionError):
                ingest_document(**self._valid_arguments())

        self.assertEqual(cursor.execute.call_count, 1)

    def test_unknown_course_is_rejected(self):
        cursor = make_cursor([("admin",), None])
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(ValueError):
                ingest_document(**self._valid_arguments())

    def test_topic_must_belong_to_selected_course(self):
        cursor = make_cursor([
            ("admin",),
            (COURSE_ID,),
            None,
        ])
        connection = make_connection(cursor)

        arguments = self._valid_arguments()
        arguments["topic_slug"] = "unknown-topic"

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(ValueError):
                ingest_document(**arguments)

    def test_topic_is_saved_when_valid(self):
        cursor = make_cursor([
            ("admin",),
            (COURSE_ID,),
            (TOPIC_ID,),
            (DOCUMENT_ID,),
        ])
        connection = make_connection(cursor)

        chunk_cursor = make_cursor([(DOCUMENT_ID,)])
        chunk_connection = make_connection(chunk_cursor)

        arguments = self._valid_arguments()
        arguments["topic_slug"] = "functions"

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                side_effect=[connection, chunk_connection],
            ),
        ):
            result = ingest_document(**arguments)

        self.assertEqual(result["topic_slug"], "functions")

        insert_parameters = cursor.execute.call_args.args[1]
        self.assertEqual(insert_parameters[1], TOPIC_ID)

    def test_duplicate_document_is_rejected(self):
        cursor = make_cursor([
            ("admin",),
            (COURSE_ID,),
        ])
        cursor.execute.side_effect = [
            None,
            None,
            psycopg.errors.UniqueViolation("duplicate document"),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "already been uploaded"):
                ingest_document(**self._valid_arguments())

    def test_empty_chunk_result_is_rejected(self):
        with (
            patch(
                "services.document_service.process_document",
                return_value=[],
            ),
            patch(
                "services.document_service.load_database_url"
            ) as load_url,
        ):
            with self.assertRaises(ValueError):
                ingest_document(**self._valid_arguments())

            load_url.assert_not_called()

    def test_chunk_failure_marks_document_failed(self):
        first_cursor = make_cursor([
            ("admin",),
            (COURSE_ID,),
            (DOCUMENT_ID,),
        ])
        first_connection = make_connection(first_cursor)

        chunk_cursor = make_cursor()
        chunk_cursor.executemany.side_effect = RuntimeError(
            "Simulated chunk insert failure"
        )
        chunk_connection = make_connection(chunk_cursor)

        failure_cursor = make_cursor()
        failure_connection = make_connection(failure_cursor)

        with (
            patch(
                "services.document_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.document_service.process_document",
                return_value=SAMPLE_CHUNKS,
            ),
            patch(
                "services.document_service.psycopg.connect",
                side_effect=[
                    first_connection,
                    chunk_connection,
                    failure_connection,
                ],
            ),
        ):
            with self.assertRaises(DocumentIngestionError):
                ingest_document(**self._valid_arguments())

        failure_sql = failure_cursor.execute.call_args.args[0]
        self.assertIn(
            "processing_status = 'failed'",
            failure_sql,
        )

        failure_parameters = (
            failure_cursor.execute.call_args.args[1]
        )
        self.assertIn("RuntimeError", failure_parameters[0])

    def test_processing_failure_does_not_open_database(self):
        with (
            patch(
                "services.document_service.process_document",
                side_effect=ValueError("Invalid PDF"),
            ),
            patch(
                "services.document_service.load_database_url"
            ) as load_url,
            patch(
                "services.document_service.psycopg.connect"
            ) as connect,
        ):
            with self.assertRaises(ValueError):
                ingest_document(**self._valid_arguments())

            load_url.assert_not_called()
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
