"""Tests for EduPath's page-aware LangChain document pipeline."""

import unittest
from io import BytesIO

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter
from pypdf import PdfWriter

from services.langchain_document_processing import (
    EduPathDocumentLoader,
    EduPathPageAwareTextSplitter,
    process_document_with_langchain,
)
from services.text_processing_service import DocumentProcessingError


def build_test_pdf(page_texts: list[str]) -> bytes:
    """Build a small text PDF for extraction tests."""

    writer = PdfWriter()
    for text in page_texts:
        writer.add_blank_page(width=300, height=300)
        page = writer.pages[-1]
        page.insert_text if hasattr(page, "insert_text") else None

    # pypdf does not create text content on blank pages, so use a minimal
    # text-bearing PDF through its public text extraction fixture path.
    # Tests below exercise page behavior using an in-memory reader fixture.
    raise NotImplementedError("Use TXT loader tests for now.")


class EduPathDocumentLoaderTests(unittest.TestCase):

    def test_loader_implements_langchain_base_loader(self):
        loader = EduPathDocumentLoader(
            file_data=b"Python variables store values.",
            file_name="variables.txt",
        )
        self.assertIsInstance(loader, BaseLoader)

    def test_loads_text_as_langchain_document(self):
        loader = EduPathDocumentLoader(
            file_data=b"Python variables store values.",
            file_name="variables.txt",
        )

        documents = loader.load()

        self.assertEqual(len(documents), 1)
        self.assertIsInstance(documents[0], Document)
        self.assertEqual(
            documents[0].page_content,
            "Python variables store values.",
        )
        self.assertEqual(
            documents[0].metadata,
            {
                "source": "variables.txt",
                "source_name": "variables.txt",
                "file_name": "variables.txt",
                "source_type": "txt",
                "file_type": "txt",
                "page_number": None,
            },
        )

    def test_loader_preserves_markdown_content(self):
        loader = EduPathDocumentLoader(
            file_data=b"# Python\n\nLearn functions.",
            file_name="notes.md",
        )

        documents = loader.load()

        self.assertEqual(len(documents), 1)
        self.assertEqual(
            documents[0].page_content,
            "# Python\n\nLearn functions.",
        )
        self.assertEqual(documents[0].metadata["source_type"], "md")

    def test_loader_reuses_existing_file_validation(self):
        loader = EduPathDocumentLoader(
            file_data=b"Unsupported content",
            file_name="notes.csv",
        )

        with self.assertRaises(DocumentProcessingError):
            loader.load()


class EduPathPageAwareTextSplitterTests(unittest.TestCase):

    def test_splitter_implements_langchain_text_splitter(self):
        splitter = EduPathPageAwareTextSplitter(
            chunk_size=10,
            chunk_overlap=2,
        )
        self.assertIsInstance(splitter, TextSplitter)

    def test_split_text_matches_existing_edupath_chunk_boundaries(self):
        splitter = EduPathPageAwareTextSplitter(
            chunk_size=10,
            chunk_overlap=2,
        )

        chunks = splitter.split_text("A" * 25)

        self.assertEqual(
            chunks,
            ["A" * 10, "A" * 10, "A" * 9],
        )

    def test_split_documents_preserves_offsets_and_metadata(self):
        splitter = EduPathPageAwareTextSplitter(
            chunk_size=10,
            chunk_overlap=2,
        )
        source = Document(
            page_content="A" * 25,
            metadata={
                "source": "python.txt",
                "source_name": "python.txt",
                "source_type": "txt",
                "page_number": None,
            },
        )

        chunks = splitter.split_documents([source])

        self.assertEqual(len(chunks), 3)
        self.assertEqual(
            [
                (
                    chunk.metadata["start_char"],
                    chunk.metadata["end_char"],
                )
                for chunk in chunks
            ],
            [(0, 10), (8, 18), (16, 25)],
        )
        self.assertEqual(
            [chunk.metadata["chunk_index"] for chunk in chunks],
            [0, 1, 2],
        )
        self.assertTrue(
            all(chunk.metadata["source"] == "python.txt" for chunk in chunks)
        )

    def test_split_documents_keeps_pdf_pages_separate(self):
        splitter = EduPathPageAwareTextSplitter(
            chunk_size=10,
            chunk_overlap=2,
        )
        source_documents = [
            Document(
                page_content="A" * 12,
                metadata={
                    "source_name": "python.pdf",
                    "source_type": "pdf",
                    "page_number": 1,
                },
            ),
            Document(
                page_content="B" * 7,
                metadata={
                    "source_name": "python.pdf",
                    "source_type": "pdf",
                    "page_number": 2,
                },
            ),
        ]

        chunks = splitter.split_documents(source_documents)

        self.assertEqual(
            [chunk.metadata["page_number"] for chunk in chunks],
            [1, 1, 2],
        )
        self.assertEqual(
            [chunk.metadata["chunk_index"] for chunk in chunks],
            [0, 1, 2],
        )
        self.assertEqual(
            [
                (
                    chunk.metadata["start_char"],
                    chunk.metadata["end_char"],
                )
                for chunk in chunks
            ],
            [(0, 10), (8, 12), (0, 7)],
        )
        self.assertEqual(
            [chunk.page_content for chunk in chunks],
            ["A" * 10, "A" * 4, "B" * 7],
        )

    def test_rejects_non_document_items(self):
        splitter = EduPathPageAwareTextSplitter(
            chunk_size=10,
            chunk_overlap=2,
        )

        with self.assertRaisesRegex(TypeError, "LangChain Document"):
            splitter.split_documents(["not a document"])

    def test_rejects_invalid_chunk_configuration(self):
        for chunk_size, overlap in ((0, 0), (10, 10), (10, -1)):
            with self.subTest(chunk_size=chunk_size, overlap=overlap):
                with self.assertRaises(DocumentProcessingError):
                    EduPathPageAwareTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=overlap,
                    )


class LangChainDocumentPipelineTests(unittest.TestCase):

    def test_processes_text_using_loader_and_splitter(self):
        chunks = process_document_with_langchain(
            file_data=("A" * 25).encode("utf-8"),
            file_name="python.txt",
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(isinstance(chunk, Document) for chunk in chunks))
        self.assertEqual(
            [chunk.metadata["chunk_index"] for chunk in chunks],
            [0, 1, 2],
        )
        self.assertEqual(
            [chunk.metadata["start_char"] for chunk in chunks],
            [0, 8, 16],
        )
        self.assertEqual(
            [chunk.metadata["end_char"] for chunk in chunks],
            [10, 18, 25],
        )
        self.assertTrue(
            all(chunk.metadata["source_type"] == "txt" for chunk in chunks)
        )


if __name__ == "__main__":
    unittest.main()
