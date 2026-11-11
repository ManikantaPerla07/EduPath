
"""Semantic retrieval of educational chunks using Neon pgvector."""

from typing import Any

import psycopg

from services.assessment_service import load_database_url
from services.embedding_service import EMBEDDING_MODEL
from services.langchain_embeddings import EduPathGeminiEmbeddings


MIN_SEARCH_LIMIT = 1
MAX_SEARCH_LIMIT = 20


def _validate_search_inputs(
    query: str,
    course_slug: str,
    topic_slug: str | None,
    limit: int,
) -> None:
    """Validate learner search inputs before making API requests."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    if topic_slug is not None and (
        not isinstance(topic_slug, str) or not topic_slug.strip()
    ):
        raise ValueError("Topic slug cannot be empty.")

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not MIN_SEARCH_LIMIT <= limit <= MAX_SEARCH_LIMIT
    ):
        raise ValueError(
            f"Search limit must be an integer between "
            f"{MIN_SEARCH_LIMIT} and {MAX_SEARCH_LIMIT}."
        )


def _vector_to_literal(values: list[float]) -> str:
    """Convert a validated embedding into pgvector text format."""

    return "[" + ",".join(repr(float(value)) for value in values) + "]"


def search_knowledge_base(
    query: str,
    course_slug: str,
    topic_slug: str | None = None,
    limit: int = 5,
    client=None,
) -> list[dict[str, Any]]:
    """Retrieve the most relevant educational chunks.

    The learner query is embedded using Gemini Embedding 2.
    Neon ranks stored chunks using cosine distance.

    Only chunks from ready documents with the configured embedding
    model are eligible for retrieval.

    Optionally restrict retrieval to one course topic.
    """

    _validate_search_inputs(
        query=query,
        course_slug=course_slug,
        topic_slug=topic_slug,
        limit=limit,
    )

    embeddings = EduPathGeminiEmbeddings(client=client)
    query_vector = embeddings.embed_query(query)

    vector_literal = _vector_to_literal(query_vector)
    database_url = load_database_url()

    sql = """
        SELECT
            dc.chunk_id,
            d.document_id,
            d.source_title,
            d.file_name,
            d.source_license,
            d.rights_basis,
            c.course_slug,
            t.topic_slug,
            t.topic_name,
            dc.page_number,
            dc.chunk_index,
            dc.content,
            1 - (dc.embedding <=> %s::vector) AS similarity,
            dc.embedding_model
        FROM document_chunks AS dc
        JOIN documents AS d
            ON d.document_id = dc.document_id
        JOIN courses AS c
            ON c.course_id = d.course_id
        LEFT JOIN topics AS t
            ON t.topic_id = d.topic_id
           AND t.course_id = d.course_id
        WHERE d.processing_status = 'ready'
          AND dc.embedding IS NOT NULL
          AND dc.embedding_model = %s
          AND c.course_slug = %s
    """

    parameters: list[Any] = [
        vector_literal,
        EMBEDDING_MODEL,
        course_slug.strip(),
    ]

    if topic_slug is not None:
        sql += """
          AND t.topic_slug = %s
        """
        parameters.append(topic_slug.strip())

    sql += """
        ORDER BY
            dc.embedding <=> %s::vector ASC,
            d.document_id ASC,
            dc.chunk_index ASC
        LIMIT %s;
    """

    parameters.extend([
        vector_literal,
        limit,
    ])

    with psycopg.connect(
        database_url,
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:

            cursor.execute(sql, parameters)
            rows = cursor.fetchall()

    results = []

    for row in rows:
        results.append({
            "chunk_id": str(row[0]),
            "document_id": str(row[1]),
            "source_title": row[2],
            "file_name": row[3],
            "source_license": row[4],
            "rights_basis": row[5],
            "course_slug": row[6],
            "topic_slug": row[7],
            "topic_name": row[8],
            "page_number": row[9],
            "chunk_index": row[10],
            "content": row[11],
            "similarity": float(row[12]),
            "embedding_model": row[13],
        })

    return results
