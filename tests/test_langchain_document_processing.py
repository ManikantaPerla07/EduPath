"""Tests for EduPath's page-aware LangChain document pipeline."""

import unittest

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter

from services.langchain_document_processing import (
    EduPathDocumentLoader,
    EduPathPageAwareTextSplitter,
    process_document_with_langchain,
)
from services.text_processing_service import DocumentProcessingError


def build_test_pdf(page_texts: list[str]) -> bytes:
    """Build a small valid PDF containing selectable text."""

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        None,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_references = []

    for page_index, text in enumerate(page_texts):
        page_object_number = 4 + page_index * 2
        content_object_number = page_object_number + 1
        page_references.append(f"{page_object_number} 0 R".encode())

        escaped_text = (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        stream = (
            "BT\n/F1 12 Tf\n40 200 Td\n"
            f"({escaped_text}) Tj\nET\n"
        ).encode("ascii")

        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        ).encode("ascii")
        content_object = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )
        objects.extend([page_object, content_object])

    kids = b" ".join(page_references)
    objects[1] = (
        f"<< /Type /Pages /Kids [{kids.decode()}] "
        f"/Count {len(page_texts)} >>"
    ).encode("ascii")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


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

    def test_loader_preserves_pdf_page_numbers(self):
        loader = EduPathDocumentLoader(
            file_data=build_test_pdf(["First PDF page", "Second PDF page"]),
            file_name="python.pdf",
        )

        documents = loader.load()

        self.assertEqual(
            [document.page_content for document in documents],
            ["First PDF page", "Second PDF page"],
        )
        self.assertEqual(
            [document.metadata["page_number"] for document in documents],
            [1, 2],
        )
        self.assertTrue(
            all(document.metadata["source_type"] == "pdf"
                for document in documents)
        )

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

        self.assertEqual(chunks, ["A" * 10, "A" * 10, "A" * 9])

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

    def test_processes_pdf_without_crossing_page_boundaries(self):
        chunks = process_document_with_langchain(
            file_data=build_test_pdf(["First PDF page", "Second PDF page"]),
            file_name="python.pdf",
            chunk_size=100,
            overlap=10,
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(
            [chunk.metadata["page_number"] for chunk in chunks],
            [1, 2],
        )
        self.assertEqual(
            [chunk.page_content for chunk in chunks],
            ["First PDF page", "Second PDF page"],
        )


if __name__ == "__main__":
    unittest.main()
