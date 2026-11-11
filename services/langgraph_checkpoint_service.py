"""PostgreSQL checkpoint persistence for EduPath's LangGraph tutor."""

from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import dict_row

from services.assessment_service import load_database_url


def _build_checkpointer(connection) -> PostgresSaver:
    """Create a saver that only deserializes LangGraph's safe built-in types."""

    serializer = JsonPlusSerializer(allowed_msgpack_modules=None)
    return PostgresSaver(
        connection,
        serde=serializer,
    )


@contextmanager
def open_langgraph_checkpointer(
    database_url: str | None = None,
) -> Iterator[PostgresSaver]:
    """Open a short-lived, secure Postgres checkpointer connection.

    The connection uses Psycopg 3's dictionary row factory and autocommit,
    both required by PostgresSaver. Checkpoint tables are initialized by
    database.run_migrations, not on every learner request.
    """

    connection_string = database_url or load_database_url()

    with psycopg.connect(
        connection_string,
        connect_timeout=20,
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        yield _build_checkpointer(connection)


def delete_langgraph_thread_checkpoints(
    thread_id: str | UUID,
    database_url: str | None = None,
) -> None:
    """Delete all saved graph checkpoints and pending writes for one chat."""

    try:
        normalized_thread_id = str(UUID(str(thread_id)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid LangGraph thread ID is required.") from None

    with open_langgraph_checkpointer(database_url) as checkpointer:
        checkpointer.delete_thread(normalized_thread_id)
