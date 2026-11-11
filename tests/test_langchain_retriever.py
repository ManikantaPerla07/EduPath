"""Tests for EduPath's LangChain Neon pgvector retriever."""

import unittest
from unittest.mock import patch

from langchain_core.documents import Document

from services.langchain_retriever import (
    NeonPgVectorRetriever,
    documents_to_chunks,
)


def make_chunk():
    """Create a realistic retrieved course chunk."""

    return {
        "chunk_id": "chunk-001",
        "document_id": "document-001",
        "source_title": "Python Variables Notes",
        "file_name": "variables.md",
        "source_license": "Original",
        "rights_basis": "original",
        "course_slug": "python-basics",
        "topic_slug": "variables-data-types",
        "topic_name": "Variables and Data Types",
        "page_number": 1,
        "chunk_index": 0,
        "content": "Python variables are created when a value is assigned.",
        "similarity": 0.85,
        "embedding_model": "gemini-embedding-2",
    }


class NeonPgVectorRetrieverTests(unittest.TestCase):

    @patch("services.langchain_retriever.search_knowledge_base")
    def test_invoke_returns_langchain_documents(self, mock_search):
        mock_search.return_value = [make_chunk()]

        retriever = NeonPgVectorRetriever(
            course_slug="python-basics",
            topic_slug="variables-data-types",
            limit=3,
        )

        documents = retriever.invoke(
            "How are Python variables created?"
        )

        mock_search.assert_called_once_with(
            query="How are Python variables created?",
            course_slug="python-basics",
            topic_slug="variables-data-types",
            limit=3,
            client=None,
        )

        self.assertEqual(len(documents), 1)
        self.assertIsInstance(documents[0], Document)

        self.assertEqual(
            documents[0].page_content,
            "Python variables are created when a value is assigned.",
        )

        self.assertEqual(
            documents[0].metadata["chunk_id"],
            "chunk-001",
        )

        self.assertEqual(
            documents[0].metadata["document_id"],
            "document-001",
        )

        self.assertEqual(
            documents[0].metadata["embedding_model"],
            "gemini-embedding-2",
        )

        self.assertEqual(
            documents[0].metadata["similarity"],
            0.85,
        )

    @patch("services.langchain_retriever.search_knowledge_base")
    def test_returns_empty_list_when_no_chunks_are_found(
        self,
        mock_search,
    ):
        mock_search.return_value = []

        retriever = NeonPgVectorRetriever(
            course_slug="python-basics",
        )

        documents = retriever.invoke("Unknown topic")

        self.assertEqual(documents, [])

    @patch("services.langchain_retriever.search_knowledge_base")
    def test_rejects_chunks_with_empty_content(self, mock_search):
        chunk = make_chunk()
        chunk["content"] = "   "

        mock_search.return_value = [chunk]

        retriever = NeonPgVectorRetriever(
            course_slug="python-basics",
        )

        with self.assertRaisesRegex(
            ValueError,
            "non-empty text",
        ):
            retriever.invoke("What is a variable?")

    def test_converts_documents_back_to_original_chunk_format(self):
        original_chunk = make_chunk()

        document = Document(
            page_content=original_chunk["content"],
            metadata={
                key: value
                for key, value in original_chunk.items()
                if key != "content"
            },
        )

        converted = documents_to_chunks([document])

        self.assertEqual(converted, [original_chunk])

    def test_rejects_non_document_items(self):
        with self.assertRaises(TypeError):
            documents_to_chunks(["not a document"])


if __name__ == "__main__":
    unittest.main()