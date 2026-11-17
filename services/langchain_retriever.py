"""LangChain retriever adapter for EduPath's Neon pgvector database."""

import logging
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from services.retrieval_service import (
    search_knowledge_base,
    search_knowledge_base_lexical,
)

logger = logging.getLogger(__name__)


class NeonPgVectorRetriever(BaseRetriever):
    """Expose EduPath's existing pgvector search as a LangChain retriever."""

    course_slug: str
    topic_slug: str | None = None
    limit: int = 5
    client: Any | None = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """Retrieve relevant course chunks and return LangChain Documents."""

        try:
            retrieved_chunks = search_knowledge_base(
                query=query,
                course_slug=self.course_slug,
                topic_slug=self.topic_slug,
                limit=self.limit,
                client=self.client,
            )
        except Exception as exc:
            logger.warning(
                "Semantic retrieval failed (%s: %s); falling back to lexical search.",
                type(exc).__name__,
                exc,
            )
            retrieved_chunks = search_knowledge_base_lexical(
                query=query,
                course_slug=self.course_slug,
                topic_slug=self.topic_slug,
                limit=self.limit,
            )

        documents = []

        for chunk in retrieved_chunks:
            content = chunk.get("content")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    "Retrieved chunks must contain non-empty text."
                )

            metadata = {
                key: value
                for key, value in chunk.items()
                if key != "content"
            }

            documents.append(
                Document(
                    page_content=content,
                    metadata=metadata,
                )
            )

        return documents


def documents_to_chunks(
    documents: list[Document],
) -> list[dict[str, Any]]:
    """Convert LangChain Documents back to EduPath's existing chunk format."""

    chunks = []

    for document in documents:
        if not isinstance(document, Document):
            raise TypeError(
                "Every retrieved item must be a LangChain Document."
            )

        chunks.append(
            {
                "content": document.page_content,
                **document.metadata,
            }
        )

    return chunks

def retrieve_course_chunks(
    query: str,
    course_slug: str,
    topic_slug: str | None = None,
    limit: int = 5,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Retrieve course chunks through the LangChain retriever."""

    retriever = NeonPgVectorRetriever(
        course_slug=course_slug,
        topic_slug=topic_slug,
        limit=limit,
        client=client,
    )

    documents = retriever.invoke(query)

    return documents_to_chunks(documents)