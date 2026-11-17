"""PostgreSQL checkpoint persistence for EduPath's LangGraph tutor."""

import logging
from contextlib import contextmanager
from typing import Any, Iterator, Sequence
from uuid import UUID

import psycopg
from langgraph.checkpoint.base import (
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langchain_core.runnables import RunnableConfig
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from services.assessment_service import load_database_url

logger = logging.getLogger(__name__)


class ResilientPostgresSaver(PostgresSaver):
    """PostgresSaver subclass with proactive recovery for transient SSL/socket drops.

    Serverless PostgreSQL engines (such as Neon) terminate idle connections during long
    model generations (e.g., 10-30s). When backed by a ConnectionPool with health checks,
    this saver catches transient psycopg.OperationalError and transparently retries the
    checkpoint operation on a freshly established connection before raising.
    """

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        try:
            super().put_writes(config, writes, task_id, task_path=task_path)
        except psycopg.OperationalError as exc:
            logger.warning(
                "Transient PostgreSQL OperationalError during checkpoint put_writes; retrying with fresh connection: %s",
                exc,
            )
            super().put_writes(config, writes, task_id, task_path=task_path)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        try:
            return super().put(config, checkpoint, metadata, new_versions)
        except psycopg.OperationalError as exc:
            logger.warning(
                "Transient PostgreSQL OperationalError during checkpoint put; retrying with fresh connection: %s",
                exc,
            )
            return super().put(config, checkpoint, metadata, new_versions)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        try:
            return super().get_tuple(config)
        except psycopg.OperationalError as exc:
            logger.warning(
                "Transient PostgreSQL OperationalError during checkpoint get_tuple; retrying with fresh connection: %s",
                exc,
            )
            return super().get_tuple(config)


def _build_checkpointer(connection_or_pool) -> PostgresSaver:
    """Create a resilient saver that only deserializes LangGraph's safe built-in types."""

    serializer = JsonPlusSerializer(allowed_msgpack_modules=None)
    return ResilientPostgresSaver(
        connection_or_pool,
        serde=serializer,
    )


@contextmanager
def open_langgraph_checkpointer(
    database_url: str | None = None,
) -> Iterator[PostgresSaver]:
    """Open a resilient, pooled Postgres checkpointer connection.

    Uses psycopg_pool.ConnectionPool with autocommit, dictionary row factory,
    TCP keepalives, and proactive connection health checks (check_connection).
    This ensures idle connections dropped by serverless Neon SSL timeouts are
    automatically detected and replaced before put_writes() or get_tuple().
    """

    connection_string = database_url or load_database_url()

    with ConnectionPool(
        conninfo=connection_string,
        min_size=1,
        max_size=4,
        timeout=30.0,
        max_idle=300.0,
        check=ConnectionPool.check_connection,
        kwargs={
            "connect_timeout": 20,
            "autocommit": True,
            "row_factory": dict_row,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    ) as pool:
        yield _build_checkpointer(pool)


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
