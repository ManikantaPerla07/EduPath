"""LangChain embedding interface backed by EduPath's Gemini service."""

from typing import Any

from langchain_core.embeddings import Embeddings

from services.embedding_service import (
    generate_document_embedding,
    generate_query_embedding,
)


class EduPathGeminiEmbeddings(Embeddings):
    """Expose EduPath's validated Gemini Embedding 2 service to LangChain.

    The existing service owns Gemini Embedding 2 input formatting, API calls,
    dimensionality checks, and error normalization. This adapter only provides
    LangChain's standard embedding interface.
    """

    def __init__(
        self,
        client: Any | None = None,
        document_title: str | None = None,
    ) -> None:
        self.client = client
        self.document_title = document_title

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents using EduPath's document-specific input format."""

        if not isinstance(texts, list):
            raise ValueError("Document texts must be provided as a list.")

        return [
            generate_document_embedding(
                content=text,
                title=self.document_title,
                client=self.client,
            )
            for text in texts
        ]

    def embed_query(self, text: str) -> list[float]:
        """Embed one search query using EduPath's QA-specific input format."""

        return generate_query_embedding(
            query=text,
            client=self.client,
        )
