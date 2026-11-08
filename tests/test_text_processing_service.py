
"""Tests for educational document extraction and text chunking."""

from io import BytesIO
import unittest

from pypdf import PdfWriter

from services.text_processing_service import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    MAX_DOCUMENT_BYTES,
    DocumentProcessingError,
    ExtractedPage,
    chunk_extracted_pages,
    extract_document_pages,
    normalize_text,
    process_document,
)


def build_test_pdf(page_texts):
    """Build a small valid PDF containing selectable text.

    This avoids requiring an additional PDF-generation dependency.
    """

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
            "BT\n"
            "/F1 12 Tf\n"
            "40 200 Td\n"
            f"({escaped_text}) Tj\n"
            "ET\n"
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

    output.extend(
        f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    )
    output.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        output.extend(
            f"{offset:010d} 00000 n \n".encode("ascii")
        )

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )

    return bytes(output)


def build_encrypted_pdf():
    """Build a password-protected PDF."""

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("test-password")

    output = BytesIO()
    writer.write(output)

    return output.getvalue()


class TextNormalizationTests(unittest.TestCase):

    def test_normalizes_line_endings(self):
        text = "First line\r\nSecond line\rThird line"

        self.assertEqual(
            normalize_text(text),
            "First line\nSecond line\nThird line",
        )

    def test_reduces_excessive_blank_lines(self):
        text = "First paragraph\n\n\n\nSecond paragraph"

        self.assertEqual(
            normalize_text(text),
            "First paragraph\n\nSecond paragraph",
        )

    def test_removes_null_characters(self):
        self.assertEqual(
            normalize_text("Python\x00 programming"),
            "Python programming",
        )

    def test_preserves_python_indentation(self):
        text = "def hello():\n    print('Hello')"

        self.assertEqual(
            normalize_text(text),
            text,
        )

    def test_strips_outer_whitespace(self):
        self.assertEqual(
            normalize_text("  Python programming  \n"),
            "Python programming",
        )

    def test_rejects_non_string_input(self):
        with self.assertRaises(DocumentProcessingError):
            normalize_text(b"Python")


class DocumentExtractionTests(unittest.TestCase):

    def test_extracts_text_document(self):
        content = b"Python is a programming language."

        pages = extract_document_pages(
            content,
            "python.txt",
        )

        self.assertEqual(len(pages), 1)
        self.assertIsNone(pages[0].page_number)
        self.assertEqual(
            pages[0].text,
            "Python is a programming language.",
        )

    def test_extracts_markdown_document(self):
        content = b"# Python\n\nPython supports functions."

        pages = extract_document_pages(
            content,
            "python.md",
        )

        self.assertEqual(len(pages), 1)
        self.assertIn("# Python", pages[0].text)

    def test_supports_utf8_bom(self):
        content = b"\xef\xbb\xbfPython programming"

        pages = extract_document_pages(
            content,
            "python.txt",
        )

        self.assertEqual(
            pages[0].text,
            "Python programming",
        )

    def test_extracts_multiple_pdf_pages(self):
        pdf_data = build_test_pdf([
            "Introduction to Python",
            "Variables and data types",
        ])

        pages = extract_document_pages(
            pdf_data,
            "python.pdf",
        )

        self.assertEqual(len(pages), 2)
        self.assertEqual(
            [page.page_number for page in pages],
            [1, 2],
        )
        self.assertIn("Introduction to Python", pages[0].text)
        self.assertIn("Variables and data types", pages[1].text)

    def test_rejects_empty_document_bytes(self):
        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(b"", "python.txt")

    def test_rejects_whitespace_only_document(self):
        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                b"   \n\n  ",
                "python.txt",
            )

    def test_rejects_invalid_utf8(self):
        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                b"\xff\xfe\xfa",
                "python.txt",
            )

    def test_rejects_file_larger_than_limit(self):
        content = b"a" * (MAX_DOCUMENT_BYTES + 1)

        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                content,
                "large.txt",
            )

    def test_rejects_unsupported_file_type(self):
        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                b"Python",
                "python.docx",
            )

    def test_rejects_extension_mismatch(self):
        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                b"Python",
                "python.txt",
                file_type="md",
            )

    def test_rejects_malformed_pdf(self):
        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                b"This is not a PDF",
                "broken.pdf",
            )

    def test_rejects_pdf_without_extractable_text(self):
        pdf_data = build_test_pdf([""])

        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                pdf_data,
                "blank.pdf",
            )

    def test_rejects_encrypted_pdf(self):
        pdf_data = build_encrypted_pdf()

        with self.assertRaises(DocumentProcessingError):
            extract_document_pages(
                pdf_data,
                "encrypted.pdf",
            )


class TextChunkingTests(unittest.TestCase):

    def test_default_chunk_settings(self):
        self.assertEqual(DEFAULT_CHUNK_SIZE, 1000)
        self.assertEqual(DEFAULT_CHUNK_OVERLAP, 150)

    def test_creates_multiple_chunks(self):
        text = "A" * 25

        chunks = chunk_extracted_pages(
            [ExtractedPage(None, text)],
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(len(chunks), 3)

    def test_chunks_have_correct_character_offsets(self):
        text = "A" * 25

        chunks = chunk_extracted_pages(
            [ExtractedPage(None, text)],
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(
            [(chunk.start_char, chunk.end_char) for chunk in chunks],
            [(0, 10), (8, 18), (16, 25)],
        )

    def test_chunks_have_expected_overlap(self):
        text = "A" * 25

        chunks = chunk_extracted_pages(
            [ExtractedPage(None, text)],
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(
            chunks[0].content[-2:],
            chunks[1].content[:2],
        )

        self.assertEqual(
            chunks[1].content[-2:],
            chunks[2].content[:2],
        )

    def test_zero_overlap_creates_contiguous_chunks(self):
        text = "A" * 20

        chunks = chunk_extracted_pages(
            [ExtractedPage(None, text)],
            chunk_size=10,
            overlap=0,
        )

        self.assertEqual(
            [(chunk.start_char, chunk.end_char) for chunk in chunks],
            [(0, 10), (10, 20)],
        )

    def test_chunk_indexes_are_sequential(self):
        chunks = chunk_extracted_pages(
            [ExtractedPage(None, "A" * 25)],
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(
            [chunk.chunk_index for chunk in chunks],
            [0, 1, 2],
        )

    def test_chunks_preserve_source_metadata(self):
        chunks = chunk_extracted_pages(
            [ExtractedPage(None, "Python functions")],
            source_name="python.md",
            source_type="md",
        )

        self.assertEqual(
            chunks[0].metadata,
            {
                "source_name": "python.md",
                "source_type": "md",
            },
        )

    def test_chunks_preserve_pdf_page_numbers(self):
        pages = [
            ExtractedPage(1, "A" * 12),
            ExtractedPage(2, "B" * 7),
        ]

        chunks = chunk_extracted_pages(
            pages,
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(
            [chunk.page_number for chunk in chunks],
            [1, 1, 2],
        )

    def test_chunks_do_not_cross_page_boundaries(self):
        pages = [
            ExtractedPage(1, "First page content"),
            ExtractedPage(2, "Second page content"),
        ]

        chunks = chunk_extracted_pages(
            pages,
            chunk_size=100,
            overlap=10,
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].content, "First page content")
        self.assertEqual(chunks[1].content, "Second page content")

    def test_skips_empty_pages(self):
        pages = [
            ExtractedPage(1, ""),
            ExtractedPage(2, "Python content"),
        ]

        chunks = chunk_extracted_pages(pages)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 2)

    def test_empty_page_list_returns_no_chunks(self):
        self.assertEqual(
            chunk_extracted_pages([]),
            [],
        )

    def test_rejects_invalid_chunk_size(self):
        for size in (0, -1, True, 1.5):
            with self.subTest(size=size):
                with self.assertRaises(DocumentProcessingError):
                    chunk_extracted_pages(
                        [ExtractedPage(None, "Python")],
                        chunk_size=size,
                        overlap=0,
                    )

    def test_rejects_invalid_overlap(self):
        for overlap in (-1, 10, True, 1.5):
            with self.subTest(overlap=overlap):
                with self.assertRaises(DocumentProcessingError):
                    chunk_extracted_pages(
                        [ExtractedPage(None, "Python")],
                        chunk_size=10,
                        overlap=overlap,
                    )

    def test_rejects_non_list_pages(self):
        with self.assertRaises(DocumentProcessingError):
            chunk_extracted_pages(None)

    def test_rejects_invalid_page_object(self):
        with self.assertRaises(DocumentProcessingError):
            chunk_extracted_pages(["Python"])


class DocumentPipelineTests(unittest.TestCase):

    def test_process_document_extracts_and_chunks_text(self):
        text = "A" * 25

        chunks = process_document(
            file_data=text.encode("utf-8"),
            file_name="python.txt",
            chunk_size=10,
            overlap=2,
        )

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].start_char, 0)
        self.assertEqual(chunks[0].end_char, 10)
        self.assertEqual(
            chunks[0].metadata["source_name"],
            "python.txt",
        )
        self.assertEqual(
            chunks[0].metadata["source_type"],
            "txt",
        )

    def test_process_document_accepts_markdown(self):
        chunks = process_document(
            file_data=b"# Python\n\nLearn functions.",
            file_name="notes.md",
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0].metadata["source_type"],
            "md",
        )

    def test_process_document_accepts_pdf(self):
        pdf_data = build_test_pdf(["Python functions"])

        chunks = process_document(
            file_data=pdf_data,
            file_name="python.pdf",
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 1)


if __name__ == "__main__":
    unittest.main()
