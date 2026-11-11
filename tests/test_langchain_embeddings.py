"""Tests for EduPath's LangChain embedding adapter."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.embeddings import Embeddings

from services.langchain_embeddings import EduPathGeminiEmbeddings


class EduPathGeminiEmbeddingsTests(unittest.TestCase):

    def test_implements_langchain_embeddings_interface(self):
        adapter = EduPathGeminiEmbeddings()

        self.assertIsInstance(adapter, Embeddings)

    @patch("services.langchain_embeddings.generate_document_embedding")
    def test_embeds_documents_using_existing_document_service(
        self,
        generate_document,
    ):
        first_vector = [0.1] * 768
        second_vector = [0.2] * 768
        generate_document.side_effect = [first_vector, second_vector]
        fake_client = MagicMock()

        adapter = EduPathGeminiEmbeddings(
            client=fake_client,
            document_title="Python Basics",
        )

        result = adapter.embed_documents(
            ["Variables store values.", "Python uses indentation."]
        )

        self.assertEqual(result, [first_vector, second_vector])
        self.assertEqual(generate_document.call_count, 2)
        generate_document.assert_any_call(
            content="Variables store values.",
            title="Python Basics",
            client=fake_client,
        )
        generate_document.assert_any_call(
            content="Python uses indentation.",
            title="Python Basics",
            client=fake_client,
        )

    @patch("services.langchain_embeddings.generate_query_embedding")
    def test_embeds_query_using_existing_query_service(
        self,
        generate_query,
    ):
        expected_vector = [0.3] * 768
        generate_query.return_value = expected_vector
        fake_client = MagicMock()

        adapter = EduPathGeminiEmbeddings(client=fake_client)

        result = adapter.embed_query("What is a Python variable?")

        self.assertEqual(result, expected_vector)
        generate_query.assert_called_once_with(
            query="What is a Python variable?",
            client=fake_client,
        )

    @patch("services.langchain_embeddings.generate_document_embedding")
    def test_empty_document_list_returns_empty_list_without_api_calls(
        self,
        generate_document,
    ):
        adapter = EduPathGeminiEmbeddings()

        self.assertEqual(adapter.embed_documents([]), [])
        generate_document.assert_not_called()

    @patch("services.langchain_embeddings.generate_document_embedding")
    def test_rejects_non_list_document_input(
        self,
        generate_document,
    ):
        adapter = EduPathGeminiEmbeddings()

        with self.assertRaisesRegex(
            ValueError,
            "provided as a list",
        ):
            adapter.embed_documents("not a list")

        generate_document.assert_not_called()

    @patch("services.langchain_embeddings.generate_query_embedding")
    def test_async_query_embedding_uses_langchain_default_adapter(
        self,
        generate_query,
    ):
        expected_vector = [0.4] * 768
        generate_query.return_value = expected_vector

        adapter = EduPathGeminiEmbeddings()

        result = asyncio.run(adapter.aembed_query("Explain variables"))

        self.assertEqual(result, expected_vector)
        generate_query.assert_called_once_with(
            query="Explain variables",
            client=None,
        )

    @patch("services.langchain_embeddings.generate_document_embedding")
    def test_async_document_embedding_uses_langchain_default_adapter(
        self,
        generate_document,
    ):
        expected_vector = [0.5] * 768
        generate_document.return_value = expected_vector

        adapter = EduPathGeminiEmbeddings(
            document_title="Python Basics"
        )

        result = asyncio.run(
            adapter.aembed_documents(["Variables store values."])
        )

        self.assertEqual(result, [expected_vector])
        generate_document.assert_called_once_with(
            content="Variables store values.",
            title="Python Basics",
            client=None,
        )


if __name__ == "__main__":
    unittest.main()
