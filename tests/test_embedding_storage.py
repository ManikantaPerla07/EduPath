
"""Tests for persisting Gemini embeddings in Neon."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.embedding_service import (
    EMBEDDING_MODEL,
    EmbeddingServiceError,
    embed_pending_document_chunks,
)


DOCUMENT_ID = "c22584d4-e1af-4ab7-9570-61fe79b61505"
CHUNK_ID = UUID("9489bf2f-88e2-4b07-8bc3-332ca4e0862b")

SOURCE_TITLE = "Python Variables and Data Types"
CHUNK_CONTENT = "Python variables store data."


def make_connection(cursor):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    cursor_context.__exit__.return_value = False

    connection.cursor.return_value = cursor_context
    return connection


class EmbeddingStorageTests(unittest.TestCase):

    def test_invalid_document_id_is_rejected(self):
        with patch(
            "services.embedding_service.load_database_url"
        ) as load_url:
            with self.assertRaises(ValueError):
                embed_pending_document_chunks("invalid-id")

            load_url.assert_not_called()

    def test_missing_document_is_rejected(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        connection = make_connection(cursor)

        with (
            patch(
                "services.embedding_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.embedding_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.embedding_service._create_client"
            ) as create_client,
        ):
            with self.assertRaises(ValueError):
                embed_pending_document_chunks(DOCUMENT_ID)

            create_client.assert_not_called()

    def test_non_ready_document_is_rejected(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (SOURCE_TITLE, "processing")
        connection = make_connection(cursor)

        with (
            patch(
                "services.embedding_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.embedding_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(ValueError):
                embed_pending_document_chunks(DOCUMENT_ID)

        self.assertEqual(cursor.execute.call_count, 1)

    def test_saves_embedding_for_stored_chunk(self):
        fetch_cursor = MagicMock()
        fetch_cursor.fetchone.side_effect = [
            (SOURCE_TITLE, "ready"),
            (1, 0),
        ]
        fetch_cursor.fetchall.return_value = [
            (CHUNK_ID, CHUNK_CONTENT),
        ]
        fetch_connection = make_connection(fetch_cursor)

        save_cursor = MagicMock()
        save_cursor.fetchone.return_value = (CHUNK_ID,)
        save_connection = make_connection(save_cursor)

        fake_client = MagicMock()
        vector = [0.01] * 768

        with (
            patch(
                "services.embedding_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.embedding_service.psycopg.connect",
                side_effect=[
                    fetch_connection,
                    save_connection,
                ],
            ),
            patch(
                "services.langchain_embeddings.generate_document_embedding",
                return_value=vector,
            ) as generate,
        ):
            result = embed_pending_document_chunks(
                DOCUMENT_ID,
                client=fake_client,
            )

        generate.assert_called_once_with(
            content=CHUNK_CONTENT,
            title=SOURCE_TITLE,
            client=fake_client,
        )

        self.assertEqual(result["embeddings_saved"], 1)
        self.assertEqual(result["total_chunks"], 1)
        self.assertEqual(result["model"], EMBEDDING_MODEL)

        update_sql = save_cursor.execute.call_args.args[0]
        update_parameters = save_cursor.execute.call_args.args[1]

        self.assertIn("embedding = %s::vector", update_sql)
        self.assertEqual(update_parameters[0].count(","), 767)
        self.assertEqual(update_parameters[1], EMBEDDING_MODEL)
        self.assertEqual(update_parameters[2], CHUNK_ID)

    def test_skips_already_embedded_chunks(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (SOURCE_TITLE, "ready"),
            (1, 1),
        ]
        cursor.fetchall.return_value = []
        connection = make_connection(cursor)

        with (
            patch(
                "services.embedding_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.embedding_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.embedding_service._create_client"
            ) as create_client,
        ):
            result = embed_pending_document_chunks(DOCUMENT_ID)

        self.assertEqual(result["embeddings_saved"], 0)
        self.assertEqual(result["already_embedded"], 1)
        self.assertEqual(result["pending_at_start"], 0)
        create_client.assert_not_called()

    def test_concurrent_update_is_counted_as_skipped(self):
        fetch_cursor = MagicMock()
        fetch_cursor.fetchone.side_effect = [
            (SOURCE_TITLE, "ready"),
            (1, 0),
        ]
        fetch_cursor.fetchall.return_value = [
            (CHUNK_ID, CHUNK_CONTENT),
        ]
        fetch_connection = make_connection(fetch_cursor)

        save_cursor = MagicMock()
        save_cursor.fetchone.return_value = None
        save_connection = make_connection(save_cursor)

        fake_client = MagicMock()

        with (
            patch(
                "services.embedding_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.embedding_service.psycopg.connect",
                side_effect=[
                    fetch_connection,
                    save_connection,
                ],
            ),
            patch(
                "services.langchain_embeddings.generate_document_embedding",
                return_value=[0.01] * 768,
            ),
        ):
            result = embed_pending_document_chunks(
                DOCUMENT_ID,
                client=fake_client,
            )

        self.assertEqual(result["embeddings_saved"], 0)
        self.assertEqual(
            result["skipped_due_to_concurrent_update"],
            1,
        )

    def test_api_failure_does_not_save_embedding(self):
        fetch_cursor = MagicMock()
        fetch_cursor.fetchone.side_effect = [
            (SOURCE_TITLE, "ready"),
            (1, 0),
        ]
        fetch_cursor.fetchall.return_value = [
            (CHUNK_ID, CHUNK_CONTENT),
        ]
        fetch_connection = make_connection(fetch_cursor)

        fake_client = MagicMock()

        with (
            patch(
                "services.embedding_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.embedding_service.psycopg.connect",
                return_value=fetch_connection,
            ),
            patch(
                "services.langchain_embeddings.generate_document_embedding",
                side_effect=EmbeddingServiceError("API failure"),
            ),
        ):
            with self.assertRaises(EmbeddingServiceError):
                embed_pending_document_chunks(
                    DOCUMENT_ID,
                    client=fake_client,
                )

        self.assertEqual(fake_client.mock_calls, [])

    def test_invalid_document_id_does_not_call_database(self):
        with (
            patch(
                "services.embedding_service.load_database_url"
            ) as load_url,
            patch(
                "services.embedding_service.psycopg.connect"
            ) as connect,
        ):
            with self.assertRaises(ValueError):
                embed_pending_document_chunks("not-a-uuid")

            load_url.assert_not_called()
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
