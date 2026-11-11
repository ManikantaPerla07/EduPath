"""LangChain loader and page-aware splitter for EduPath document ingestion."""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter

from services.text_processing_service import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    ExtractedPage,
    chunk_extracted_pages,
    extract_document_pages,
)


class EduPathDocumentLoader(BaseLoader):
    """Load an uploaded EduPath document into one LangChain Document per page.

    Extraction remains delegated to EduPath's validated PDF/TXT/Markdown
    parser so existing normalization, file-size checks, and PDF page numbers
    remain unchanged.
    """

    def __init__(
        self,
        file_data: bytes,
        file_name: str,
        file_type: str | None = None,
    ) -> None:
        self.file_data = file_data
        self.file_name = file_name
        self.file_type = file_type

    def lazy_load(self) -> Iterator[Document]:
        """Yield one LangChain Document for each extracted page."""

        pages = extract_document_pages(
            file_data=self.file_data,
            file_name=self.file_name,
            file_type=self.file_type,
        )

        resolved_file_type = (
            self.file_type.strip().lower()
            if isinstance(self.file_type, str)
            else Path(self.file_name).suffix.lower().lstrip(".")
        )

        for page in pages:
            yield Document(
                page_content=page.text,
                metadata={
                    "source": self.file_name,
                    "source_name": self.file_name,
                    "file_name": self.file_name,
                    "source_type": resolved_file_type,
                    "file_type": resolved_file_type,
                    "page_number": page.page_number,
                },
            )


class EduPathPageAwareTextSplitter(TextSplitter):
    """LangChain TextSplitter that preserves EduPath's existing chunk rules.

    Each input Document represents one page. Pages are split independently,
    preventing a chunk from crossing a PDF page boundary. EduPath's original
    chunker remains responsible for natural boundaries, overlap, and exact
    character offsets.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        # Reuse the established validation rules, including rejecting overlap
        # equal to chunk size.
        chunk_extracted_pages(
            pages=[],
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strip_whitespace=True,
        )

    def split_text(self, text: str) -> list[str]:
        """Split plain text using EduPath's established chunking policy."""

        chunks = chunk_extracted_pages(
            pages=[ExtractedPage(page_number=None, text=text)],
            chunk_size=self._chunk_size,
            overlap=self._chunk_overlap,
        )
        return [chunk.content for chunk in chunks]

    def split_documents(
        self,
        documents: Iterable[Document],
    ) -> list[Document]:
        """Split page Documents while retaining source and offset metadata."""

        split_documents: list[Document] = []
        chunk_indexes: dict[tuple[str | None, str | None], int] = {}

        for document in documents:
            if not isinstance(document, Document):
                raise TypeError(
                    "Every item to split must be a LangChain Document."
                )

            metadata = dict(document.metadata)
            source_name = metadata.get(
                "source_name",
                metadata.get("source", metadata.get("file_name")),
            )
            source_type = metadata.get(
                "source_type",
                metadata.get("file_type"),
            )

            if source_name is not None and not isinstance(source_name, str):
                raise ValueError("Document source name must be a string.")
            if source_type is not None and not isinstance(source_type, str):
                raise ValueError("Document source type must be a string.")

            source_key = (source_name, source_type)
            page = ExtractedPage(
                page_number=metadata.get("page_number"),
                text=document.page_content,
            )
            chunks = chunk_extracted_pages(
                pages=[page],
                chunk_size=self._chunk_size,
                overlap=self._chunk_overlap,
                source_name=source_name,
                source_type=source_type,
            )

            next_chunk_index = chunk_indexes.get(source_key, 0)

            for chunk in chunks:
                chunk_metadata: dict[str, Any] = {
                    **metadata,
                    **chunk.metadata,
                    "chunk_index": next_chunk_index,
                    "page_number": chunk.page_number,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                }
                split_documents.append(
                    Document(
                        page_content=chunk.content,
                        metadata=chunk_metadata,
                    )
                )
                next_chunk_index += 1

            chunk_indexes[source_key] = next_chunk_index

        return split_documents


def process_document_with_langchain(
    file_data: bytes,
    file_name: str,
    file_type: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """Run EduPath document ingestion through LangChain loader/splitter APIs.

    Returns LangChain Documents. The caller can map these to EduPath's stable
    TextChunk model for persistence without changing the database schema.
    """

    loader = EduPathDocumentLoader(
        file_data=file_data,
        file_name=file_name,
        file_type=file_type,
    )
    page_documents = loader.load()

    splitter = EduPathPageAwareTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
    )
    return splitter.split_documents(page_documents)
