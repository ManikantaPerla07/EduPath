
"""Generate retrieval embeddings using Google's Gemini Embedding 2."""

from uuid import UUID

import psycopg

from services.assessment_service import load_database_url
from services.secret_config import load_secret

from pathlib import Path
import math
from typing import Any

from google import genai


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 768


class EmbeddingServiceError(RuntimeError):
    """Raised when an embedding response is invalid or unavailable."""


def load_gemini_api_key() -> str:
    """Load the Gemini API key from local or hosted Streamlit secrets."""
    return load_secret("GEMINI_API_KEY", SECRETS_FILE)


def prepare_document_input(
    content: str,
    title: str | None = None,
) -> str:
    """Format a document using Gemini Embedding 2 retrieval structure."""

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Document content cannot be empty.")

    if title is not None and not isinstance(title, str):
        raise ValueError("Document title must be a string or None.")

    clean_title = title.strip() if title and title.strip() else "none"

    return f"title: {clean_title} | text: {content.strip()}"


def prepare_query_input(query: str) -> str:
    """Format a learner question for question-answering retrieval."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    return f"task: question answering | query: {query.strip()}"


def validate_embedding(values: Any) -> list[float]:
    """Validate and normalize an embedding response to Python floats."""

    if not isinstance(values, (list, tuple)):
        raise EmbeddingServiceError(
            "Gemini returned an invalid embedding representation."
        )

    if len(values) != EMBEDDING_DIMENSIONS:
        raise EmbeddingServiceError(
            f"Expected {EMBEDDING_DIMENSIONS} embedding dimensions, "
            f"received {len(values)}."
        )

    validated = []

    for value in values:
        if isinstance(value, bool):
            raise EmbeddingServiceError(
                "Embedding values must be numeric."
            )

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise EmbeddingServiceError(
                "Gemini returned a non-numeric embedding value."
            ) from error

        if not math.isfinite(number):
            raise EmbeddingServiceError(
                "Embedding values must be finite numbers."
            )

        validated.append(number)

    return validated


def _create_client():
    """Create a Gemini client without exposing credentials."""

    return genai.Client(api_key=load_gemini_api_key())


def _generate_embedding(
    prepared_text: str,
    client=None,
) -> list[float]:
    """Generate and validate exactly one embedding."""

    if client is None:
        client = _create_client()

    try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=prepared_text,
            config={
                "output_dimensionality": EMBEDDING_DIMENSIONS,
            },
        )
    except Exception as error:
        raise EmbeddingServiceError(
            "The Gemini embedding request failed."
        ) from error

    embeddings = getattr(response, "embeddings", None)

    if not isinstance(embeddings, (list, tuple)) or not embeddings:
        raise EmbeddingServiceError(
            "Gemini returned no embeddings."
        )

    if len(embeddings) != 1:
        raise EmbeddingServiceError(
            "Expected exactly one embedding for the supplied text."
        )

    values = getattr(embeddings[0], "values", None)

    return validate_embedding(values)


def generate_document_embedding(
    content: str,
    title: str | None = None,
    client=None,
) -> list[float]:
    """Generate one retrieval embedding for an educational chunk."""

    prepared_text = prepare_document_input(
        content=content,
        title=title,
    )

    return _generate_embedding(
        prepared_text=prepared_text,
        client=client,
    )


def generate_query_embedding(
    query: str,
    client=None,
) -> list[float]:
    """Generate one question-answering retrieval embedding."""

    prepared_text = prepare_query_input(query)

    return _generate_embedding(
        prepared_text=prepared_text,
        client=client,
    )

def embed_pending_document_chunks(
    document_id: str,
    client=None,
) -> dict[str, Any]:
    """Generate and persist embeddings for a ready document.

    Only chunks without an embedding are processed. The text is retrieved
    directly from Neon, ensuring each vector represents its stored chunk.

    Each completed vector is saved independently. If a later API request
    fails, already saved vectors remain available and a retry processes
    only the remaining chunks.
    """

    try:
        parsed_document_id = UUID(str(document_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid document ID is required.") from None

    database_url = load_database_url()

    # Retrieve source metadata and pending chunk content.
    with psycopg.connect(
        database_url,
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT source_title, processing_status
                FROM documents
                WHERE document_id = %s;
                """,
                (parsed_document_id,),
            )

            document = cursor.fetchone()

            if document is None:
                raise ValueError("The requested document was not found.")

            source_title, processing_status = document

            if processing_status != "ready":
                raise ValueError(
                    "Only documents with ready processing status "
                    "can be embedded."
                )

            cursor.execute(
                """
                SELECT
                    COUNT(*)::INTEGER,
                    COUNT(*) FILTER (
                        WHERE embedding IS NOT NULL
                    )::INTEGER
                FROM document_chunks
                WHERE document_id = %s;
                """,
                (parsed_document_id,),
            )

            counts = cursor.fetchone()

            if counts is None:
                raise EmbeddingServiceError(
                    "Unable to retrieve document chunk counts."
                )

            total_chunks, existing_embeddings = counts

            if total_chunks < 1:
                raise EmbeddingServiceError(
                    "The document does not contain any chunks."
                )

            cursor.execute(
                """
                SELECT chunk_id, content
                FROM document_chunks
                WHERE document_id = %s
                  AND embedding IS NULL
                ORDER BY chunk_index;
                """,
                (parsed_document_id,),
            )

            pending_chunks = cursor.fetchall()

    if not pending_chunks:
        return {
            "document_id": str(parsed_document_id),
            "model": EMBEDDING_MODEL,
            "total_chunks": total_chunks,
            "already_embedded": existing_embeddings,
            "pending_at_start": 0,
            "embeddings_saved": 0,
            "skipped_due_to_concurrent_update": 0,
        }

    # Import lazily because the LangChain adapter wraps this module's
    # generate_document_embedding() function.
    from services.langchain_embeddings import EduPathGeminiEmbeddings

    # Create one API client and one LangChain embedding adapter for this
    # document. Both are reused across all pending chunks.
    embedding_client = client if client is not None else _create_client()
    embeddings = EduPathGeminiEmbeddings(
        client=embedding_client,
        document_title=source_title,
    )

    saved_count = 0
    skipped_count = 0

    for chunk_id, content in pending_chunks:

        vector = embeddings.embed_documents([content])[0]

        # Convert validated numeric values to pgvector's text format.
        vector_literal = (
            "[" + ",".join(repr(value) for value in vector) + "]"
        )

        # Persist each vector independently.
        with psycopg.connect(
            database_url,
            connect_timeout=20,
        ) as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE document_chunks
                    SET embedding = %s::vector,
                        embedding_model = %s
                    WHERE chunk_id = %s
                      AND document_id = %s
                      AND embedding IS NULL
                    RETURNING chunk_id;
                    """,
                    (
                        vector_literal,
                        EMBEDDING_MODEL,
                        chunk_id,
                        parsed_document_id,
                    ),
                )

                updated_row = cursor.fetchone()

                if updated_row is None:
                    # Another worker may have embedded this chunk.
                    skipped_count += 1
                else:
                    saved_count += 1

    return {
        "document_id": str(parsed_document_id),
        "model": EMBEDDING_MODEL,
        "total_chunks": total_chunks,
        "already_embedded": existing_embeddings,
        "pending_at_start": len(pending_chunks),
        "embeddings_saved": saved_count,
        "skipped_due_to_concurrent_update": skipped_count,
    }
