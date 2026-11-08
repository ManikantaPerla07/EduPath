
"""Tests for semantic retrieval using Neon pgvector."""

import unittest
from unittest.mock import MagicMock, patch

from services.embedding_service import EMBEDDING_MODEL
from services.retrieval_service import search_knowledge_base


QUERY_VECTOR = [0.01] * 768

CHUNK_ID = "9489bf2f-88e2-4b07-8bc3-332ca4e0862b"
DOCUMENT_ID = "c22584d4-e1af-4ab7-9570-61fe79b61505"

SAMPLE_ROW = (
    CHUNK_ID,
    DOCUMENT_ID,
    "EduPath Python Variables",
    "python_variables_intro_sanitized.md",
    "Original educational material created for EduPath",
    "original",
    "python-basics",
    "variables-data-types",
    "Variables and Data Types",
    None,
    0,
    "Python variables are used to store data.",
    0.87,
    EMBEDDING_MODEL,
)


def make_database_connection(rows):
    """Create a mocked Psycopg connection."""

    cursor = MagicMock()
    cursor.fetchall.return_value = rows

    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    cursor_context.__exit__.return_value = False

    connection = MagicMock()
    connection.cursor.return_value = cursor_context
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    return connection, cursor


class RetrievalValidationTests(unittest.TestCase):

    def _assert_invalid_without_api_call(self, **kwargs):
        with (
            patch(
                "services.retrieval_service.generate_query_embedding"
            ) as generate,
            patch(
                "services.retrieval_service.load_database_url"
            ) as load_url,
        ):
            with self.assertRaises(ValueError):
                search_knowledge_base(**kwargs)

            generate.assert_not_called()
            load_url.assert_not_called()

    def test_rejects_empty_query(self):
        self._assert_invalid_without_api_call(
            query=" ",
            course_slug="python-basics",
        )

    def test_rejects_non_string_query(self):
        self._assert_invalid_without_api_call(
            query=None,
            course_slug="python-basics",
        )

    def test_rejects_empty_course_slug(self):
        self._assert_invalid_without_api_call(
            query="What is a variable?",
            course_slug=" ",
        )

    def test_rejects_empty_topic_slug(self):
        self._assert_invalid_without_api_call(
            query="What is a variable?",
            course_slug="python-basics",
            topic_slug=" ",
        )

    def test_rejects_invalid_limits(self):
        for limit in (0, -1, 21, True, 1.5, "5"):
            with self.subTest(limit=limit):
                self._assert_invalid_without_api_call(
                    query="What is a variable?",
                    course_slug="python-basics",
                    limit=limit,
                )


class RetrievalDatabaseTests(unittest.TestCase):

    def test_returns_matching_educational_chunks(self):
        connection, cursor = make_database_connection([SAMPLE_ROW])

        fake_client = MagicMock()

        with (
            patch(
                "services.retrieval_service.generate_query_embedding",
                return_value=QUERY_VECTOR,
            ) as generate,
            patch(
                "services.retrieval_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.retrieval_service.psycopg.connect",
                return_value=connection,
            ) as connect,
        ):
            results = search_knowledge_base(
                query="What is a variable?",
                course_slug="python-basics",
                client=fake_client,
            )

        generate.assert_called_once_with(
            query="What is a variable?",
            client=fake_client,
        )

        connect.assert_called_once_with(
            "postgresql://test",
            connect_timeout=20,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], CHUNK_ID)
        self.assertEqual(results[0]["document_id"], DOCUMENT_ID)
        self.assertEqual(
            results[0]["source_title"],
            "EduPath Python Variables",
        )
        self.assertEqual(
            results[0]["topic_slug"],
            "variables-data-types",
        )
        self.assertEqual(
            results[0]["content"],
            "Python variables are used to store data.",
        )
        self.assertAlmostEqual(results[0]["similarity"], 0.87)
        self.assertEqual(
            results[0]["embedding_model"],
            EMBEDDING_MODEL,
        )

        sql, parameters = cursor.execute.call_args.args

        self.assertIn("<=>", sql)
        self.assertIn("processing_status = 'ready'", sql)
        self.assertIn("embedding IS NOT NULL", sql)
        self.assertIn("embedding_model = %s", sql)
        self.assertIn("ORDER BY", sql)

        self.assertEqual(parameters[1], EMBEDDING_MODEL)
        self.assertEqual(parameters[2], "python-basics")
        self.assertEqual(parameters[-1], 5)

    def test_topic_filter_is_applied(self):
        connection, cursor = make_database_connection([SAMPLE_ROW])

        with (
            patch(
                "services.retrieval_service.generate_query_embedding",
                return_value=QUERY_VECTOR,
            ),
            patch(
                "services.retrieval_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.retrieval_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            results = search_knowledge_base(
                query="What is a variable?",
                course_slug="python-basics",
                topic_slug="variables-data-types",
                limit=3,
            )

        sql, parameters = cursor.execute.call_args.args

        self.assertIn("t.topic_slug = %s", sql)
        self.assertIn("variables-data-types", parameters)
        self.assertEqual(parameters[-1], 3)
        self.assertEqual(len(results), 1)

    def test_search_without_topic_does_not_add_topic_filter(self):
        connection, cursor = make_database_connection([])

        with (
            patch(
                "services.retrieval_service.generate_query_embedding",
                return_value=QUERY_VECTOR,
            ),
            patch(
                "services.retrieval_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.retrieval_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            results = search_knowledge_base(
                query="Explain Python variables",
                course_slug="python-basics",
            )

        sql, _ = cursor.execute.call_args.args

        self.assertNotIn("t.topic_slug = %s", sql)
        self.assertEqual(results, [])

    def test_returns_empty_list_when_no_chunks_match(self):
        connection, _ = make_database_connection([])

        with (
            patch(
                "services.retrieval_service.generate_query_embedding",
                return_value=QUERY_VECTOR,
            ),
            patch(
                "services.retrieval_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.retrieval_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            results = search_knowledge_base(
                query="Explain Python decorators",
                course_slug="python-basics",
            )

        self.assertEqual(results, [])

    def test_database_is_not_accessed_when_embedding_fails(self):
        with (
            patch(
                "services.retrieval_service.generate_query_embedding",
                side_effect=RuntimeError("Embedding service unavailable"),
            ),
            patch(
                "services.retrieval_service.load_database_url"
            ) as load_url,
            patch(
                "services.retrieval_service.psycopg.connect"
            ) as connect,
        ):
            with self.assertRaises(RuntimeError):
                search_knowledge_base(
                    query="What is a variable?",
                    course_slug="python-basics",
                )

            load_url.assert_not_called()
            connect.assert_not_called()

    def test_result_includes_source_and_citation_metadata(self):
        connection, _ = make_database_connection([SAMPLE_ROW])

        with (
            patch(
                "services.retrieval_service.generate_query_embedding",
                return_value=QUERY_VECTOR,
            ),
            patch(
                "services.retrieval_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.retrieval_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            results = search_knowledge_base(
                query="What are variables?",
                course_slug="python-basics",
            )

        result = results[0]

        self.assertIn("source_title", result)
        self.assertIn("file_name", result)
        self.assertIn("page_number", result)
        self.assertIn("topic_name", result)
        self.assertIn("content", result)
        self.assertIn("similarity", result)


if __name__ == "__main__":
    unittest.main()
