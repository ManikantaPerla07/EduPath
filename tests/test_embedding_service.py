
"""Tests for Gemini Embedding 2 request preparation and validation."""

from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.embedding_service import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EmbeddingServiceError,
    generate_document_embedding,
    generate_query_embedding,
    load_gemini_api_key,
    prepare_document_input,
    prepare_query_input,
    validate_embedding,
)


def make_client(values=None, embeddings_count=1):
    """Create a mocked Gemini client response."""

    if values is None:
        values = [0.01] * EMBEDDING_DIMENSIONS

    response = SimpleNamespace(
        embeddings=[
            SimpleNamespace(values=values)
            for _ in range(embeddings_count)
        ]
    )

    client = MagicMock()
    client.models.embed_content.return_value = response

    return client


class EmbeddingInputPreparationTests(unittest.TestCase):

    def test_prepares_document_with_title(self):
        result = prepare_document_input(
            "Python variables store data.",
            "Python Basics",
        )

        self.assertEqual(
            result,
            "title: Python Basics | text: Python variables store data.",
        )

    def test_prepares_document_without_title(self):
        result = prepare_document_input(
            "Python variables store data.",
        )

        self.assertEqual(
            result,
            "title: none | text: Python variables store data.",
        )

    def test_trims_document_content_and_title(self):
        result = prepare_document_input(
            "  Python variables  ",
            "  Python Basics  ",
        )

        self.assertEqual(
            result,
            "title: Python Basics | text: Python variables",
        )

    def test_prepares_question_answering_query(self):
        result = prepare_query_input(
            "What is a Python variable?",
        )

        self.assertEqual(
            result,
            "task: question answering | query: "
            "What is a Python variable?",
        )

    def test_rejects_empty_document(self):
        with self.assertRaises(ValueError):
            prepare_document_input(" ")

    def test_rejects_non_string_document(self):
        with self.assertRaises(ValueError):
            prepare_document_input(123)

    def test_rejects_non_string_title(self):
        with self.assertRaises(ValueError):
            prepare_document_input("Python", 123)

    def test_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            prepare_query_input(" ")

    def test_rejects_non_string_query(self):
        with self.assertRaises(ValueError):
            prepare_query_input(None)


class EmbeddingValidationTests(unittest.TestCase):

    def test_accepts_valid_768_dimensional_embedding(self):
        values = [0.01] * EMBEDDING_DIMENSIONS

        result = validate_embedding(values)

        self.assertEqual(len(result), 768)
        self.assertTrue(all(isinstance(value, float) for value in result))

    def test_converts_integer_values_to_floats(self):
        result = validate_embedding([1] * EMBEDDING_DIMENSIONS)

        self.assertEqual(result[0], 1.0)
        self.assertIsInstance(result[0], float)

    def test_rejects_wrong_dimensions(self):
        with self.assertRaises(EmbeddingServiceError):
            validate_embedding([0.01] * 767)

    def test_rejects_empty_embedding(self):
        with self.assertRaises(EmbeddingServiceError):
            validate_embedding([])

    def test_rejects_non_list_embedding(self):
        with self.assertRaises(EmbeddingServiceError):
            validate_embedding("invalid")

    def test_rejects_boolean_values(self):
        values = [0.01] * 768
        values[0] = True

        with self.assertRaises(EmbeddingServiceError):
            validate_embedding(values)

    def test_rejects_nan(self):
        values = [0.01] * 768
        values[0] = float("nan")

        with self.assertRaises(EmbeddingServiceError):
            validate_embedding(values)

    def test_rejects_infinity(self):
        values = [0.01] * 768
        values[0] = float("inf")

        with self.assertRaises(EmbeddingServiceError):
            validate_embedding(values)


class GeminiEmbeddingRequestTests(unittest.TestCase):

    def test_document_embedding_uses_correct_model_and_dimensions(self):
        client = make_client()

        result = generate_document_embedding(
            "Python variables store data.",
            title="Python Basics",
            client=client,
        )

        self.assertEqual(len(result), 768)

        client.models.embed_content.assert_called_once_with(
            model=EMBEDDING_MODEL,
            contents="title: Python Basics | text: "
            "Python variables store data.",
            config={"output_dimensionality": 768},
        )

    def test_query_embedding_uses_question_answering_prefix(self):
        client = make_client()

        result = generate_query_embedding(
            "What is a Python variable?",
            client=client,
        )

        self.assertEqual(len(result), 768)

        call = client.models.embed_content.call_args

        self.assertEqual(
            call.kwargs["contents"],
            "task: question answering | query: "
            "What is a Python variable?",
        )

        self.assertEqual(
            call.kwargs["model"],
            EMBEDDING_MODEL,
        )

    def test_empty_response_is_rejected(self):
        client = make_client()
        client.models.embed_content.return_value.embeddings = []

        with self.assertRaises(EmbeddingServiceError):
            generate_document_embedding(
                "Python variables",
                client=client,
            )

    def test_multiple_embeddings_are_rejected(self):
        client = make_client(embeddings_count=2)

        with self.assertRaises(EmbeddingServiceError):
            generate_document_embedding(
                "Python variables",
                client=client,
            )

    def test_api_failure_is_wrapped(self):
        client = MagicMock()
        client.models.embed_content.side_effect = RuntimeError(
            "Simulated API failure"
        )

        with self.assertRaises(EmbeddingServiceError):
            generate_document_embedding(
                "Python variables",
                client=client,
            )

    def test_document_validation_precedes_api_call(self):
        client = make_client()

        with self.assertRaises(ValueError):
            generate_document_embedding(
                "",
                client=client,
            )

        client.models.embed_content.assert_not_called()

    def test_query_validation_precedes_api_call(self):
        client = make_client()

        with self.assertRaises(ValueError):
            generate_query_embedding(
                "",
                client=client,
            )

        client.models.embed_content.assert_not_called()


class GeminiSecretTests(unittest.TestCase):

    def test_loads_api_key_from_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            secrets_file = Path(directory) / "secrets.toml"
            secrets_file.write_text(
                'GEMINI_API_KEY = "test-key-value"\n',
                encoding="utf-8",
            )

            with patch(
                "services.embedding_service.SECRETS_FILE",
                secrets_file,
            ):
                self.assertEqual(
                    load_gemini_api_key(),
                    "test-key-value",
                )

    def test_missing_secret_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_file = Path(directory) / "missing.toml"

            with patch(
                "services.embedding_service.SECRETS_FILE",
                missing_file,
            ):
                with self.assertRaises(FileNotFoundError):
                    load_gemini_api_key()

    def test_missing_api_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            secrets_file = Path(directory) / "secrets.toml"
            secrets_file.write_text(
                'DATABASE_URL = "postgresql://example"\n',
                encoding="utf-8",
            )

            with patch(
                "services.embedding_service.SECRETS_FILE",
                secrets_file,
            ):
                with self.assertRaises(ValueError):
                    load_gemini_api_key()


if __name__ == "__main__":
    unittest.main()
