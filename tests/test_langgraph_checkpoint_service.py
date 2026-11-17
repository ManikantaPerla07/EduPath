"""Tests for EduPath's resilient LangGraph PostgreSQL checkpoint service."""

import logging
import unittest
from unittest.mock import ANY, MagicMock, patch
from uuid import UUID

import psycopg
from langgraph.checkpoint.base import (
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from services.langgraph_checkpoint_service import (
    ResilientPostgresSaver,
    _build_checkpointer,
    delete_langgraph_thread_checkpoints,
    open_langgraph_checkpointer,
)

THREAD_ID = UUID("22222222-2222-4222-8222-222222222222")


class LangGraphCheckpointServiceTests(unittest.TestCase):
    """Test connection pooling, resilient retry, and lifecycle management."""

    @patch("services.langgraph_checkpoint_service.ConnectionPool")
    @patch("services.langgraph_checkpoint_service._build_checkpointer")
    def test_opens_pooled_resilient_connection(
        self,
        mock_build_checkpointer,
        mock_pool_class,
    ):
        """open_langgraph_checkpointer must initialize a ConnectionPool with health check and keepalives."""
        mock_pool = MagicMock()
        mock_pool.__enter__.return_value = mock_pool
        mock_pool.__exit__.return_value = False
        mock_pool_class.return_value = mock_pool

        expected_saver = MagicMock()
        mock_build_checkpointer.return_value = expected_saver

        with open_langgraph_checkpointer("postgresql://test-db") as checkpointer:
            self.assertIs(checkpointer, expected_saver)

        mock_pool_class.assert_called_once_with(
            conninfo="postgresql://test-db",
            min_size=1,
            max_size=4,
            timeout=30.0,
            max_idle=300.0,
            check=mock_pool_class.check_connection,
            kwargs={
                "connect_timeout": 20,
                "autocommit": True,
                "row_factory": dict_row,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        )
        mock_build_checkpointer.assert_called_once_with(mock_pool)

    def test_build_checkpointer_configures_resilient_saver_and_safe_serializer(self):
        """_build_checkpointer must instantiate ResilientPostgresSaver with safe JsonPlusSerializer."""
        mock_pool = MagicMock()
        saver = _build_checkpointer(mock_pool)

        self.assertIsInstance(saver, ResilientPostgresSaver)
        self.assertIs(saver.conn, mock_pool)
        self.assertIsInstance(saver.serde, JsonPlusSerializer)
        self.assertIsNone(saver.serde._allowed_msgpack_modules)

    @patch("services.langgraph_checkpoint_service.open_langgraph_checkpointer")
    def test_deletes_all_checkpoints_for_the_normalized_thread(
        self,
        mock_open_checkpointer,
    ):
        """delete_langgraph_thread_checkpoints must normalize UUID and delete thread."""
        checkpointer = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = checkpointer
        context.__exit__.return_value = False
        mock_open_checkpointer.return_value = context

        delete_langgraph_thread_checkpoints(THREAD_ID)

        mock_open_checkpointer.assert_called_once_with(None)
        checkpointer.delete_thread.assert_called_once_with(str(THREAD_ID))

    @patch("services.langgraph_checkpoint_service.open_langgraph_checkpointer")
    def test_rejects_invalid_thread_id_before_opening_database(
        self,
        mock_open_checkpointer,
    ):
        """Invalid thread IDs must be rejected before touching database connections."""
        with self.assertRaisesRegex(ValueError, "valid LangGraph thread ID"):
            delete_langgraph_thread_checkpoints("invalid-thread-not-a-uuid")

        mock_open_checkpointer.assert_not_called()

    def test_resilient_saver_put_writes_recovers_from_transient_operational_error(self):
        """put_writes must transparently retry when encountering a transient psycopg.OperationalError."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_ns": ""}}
        writes = [("messages", ["hello"])]

        with patch.object(
            PostgresSaver,
            "put_writes",
            side_effect=[psycopg.OperationalError("SSL connection has been closed unexpectedly"), None],
        ) as mock_super_put_writes:
            with self.assertLogs("services.langgraph_checkpoint_service", level="WARNING") as log_ctx:
                saver.put_writes(config, writes, "task-1", task_path="")

            self.assertEqual(mock_super_put_writes.call_count, 2)
            self.assertTrue(any("Transient PostgreSQL OperationalError" in msg for msg in log_ctx.output))

    def test_resilient_saver_put_writes_propagates_persistent_operational_error(self):
        """put_writes must raise OperationalError if retry fails, never suppressing fatal errors."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_ns": ""}}

        with patch.object(
            PostgresSaver,
            "put_writes",
            side_effect=[
                psycopg.OperationalError("SSL connection dropped 1"),
                psycopg.OperationalError("SSL connection dropped 2"),
            ],
        ):
            with self.assertRaises(psycopg.OperationalError):
                saver.put_writes(config, [], "task-1")

    def test_resilient_saver_put_recovers_from_transient_operational_error(self):
        """put must retry when encountering a transient psycopg.OperationalError."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_ns": ""}}
        checkpoint: Checkpoint = {"v": 1, "id": "cp-1", "ts": "2026-11-15T00:00:00Z", "channel_values": {}, "channel_versions": {}, "versions_seen": {}}
        metadata: CheckpointMetadata = {"source": "input", "step": 1, "writes": {}, "parents": {}}
        expected_config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_id": "cp-1"}}

        with patch.object(
            PostgresSaver,
            "put",
            side_effect=[
                psycopg.OperationalError("consuming input failed: SSL connection has been closed unexpectedly"),
                expected_config,
            ],
        ) as mock_super_put:
            res = saver.put(config, checkpoint, metadata, {})
            self.assertEqual(res, expected_config)
            self.assertEqual(mock_super_put.call_count, 2)

    def test_resilient_saver_put_propagates_persistent_operational_error(self):
        """put must raise OperationalError if retry fails."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_ns": ""}}
        checkpoint: Checkpoint = {"v": 1, "id": "cp-1", "ts": "2026-11-15T00:00:00Z", "channel_values": {}, "channel_versions": {}, "versions_seen": {}}

        with patch.object(
            PostgresSaver,
            "put",
            side_effect=[
                psycopg.OperationalError("SSL closed 1"),
                psycopg.OperationalError("SSL closed 2"),
            ],
        ):
            with self.assertRaises(psycopg.OperationalError):
                saver.put(config, checkpoint, {}, {})

    def test_resilient_saver_get_tuple_recovers_from_transient_operational_error(self):
        """get_tuple must retry when encountering a transient psycopg.OperationalError."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_ns": ""}}
        expected_tuple = MagicMock(spec=CheckpointTuple)

        with patch.object(
            PostgresSaver,
            "get_tuple",
            side_effect=[
                psycopg.OperationalError("consuming input failed: SSL connection closed"),
                expected_tuple,
            ],
        ) as mock_super_get_tuple:
            res = saver.get_tuple(config)
            self.assertIs(res, expected_tuple)
            self.assertEqual(mock_super_get_tuple.call_count, 2)

    def test_resilient_saver_get_tuple_propagates_persistent_operational_error(self):
        """get_tuple must raise OperationalError if retry fails."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID), "checkpoint_ns": ""}}

        with patch.object(
            PostgresSaver,
            "get_tuple",
            side_effect=[
                psycopg.OperationalError("Fatal SSL 1"),
                psycopg.OperationalError("Fatal SSL 2"),
            ],
        ):
            with self.assertRaises(psycopg.OperationalError):
                saver.get_tuple(config)

    def test_postgres_checkpoint_writes_and_reads(self):
        """Verify checkpoint put, put_writes, and get_tuple delegation through ResilientPostgresSaver."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID)}}
        checkpoint: Checkpoint = {"v": 1, "id": "cp-123", "ts": "2026-11-15T00:00:00Z", "channel_values": {"msg": "hi"}, "channel_versions": {}, "versions_seen": {}}
        metadata: CheckpointMetadata = {"source": "loop", "step": 1, "writes": {}, "parents": {}}

        mock_tuple = CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
            pending_writes=[],
        )

        with patch.object(PostgresSaver, "put", return_value={"configurable": {"checkpoint_id": "cp-123"}}) as mock_put, \
             patch.object(PostgresSaver, "put_writes") as mock_put_writes, \
             patch.object(PostgresSaver, "get_tuple", return_value=mock_tuple) as mock_get_tuple:

            # 1. Put checkpoint
            returned_config = saver.put(config, checkpoint, metadata, {})
            self.assertEqual(returned_config, {"configurable": {"checkpoint_id": "cp-123"}})
            mock_put.assert_called_once_with(config, checkpoint, metadata, {})

            # 2. Put writes
            saver.put_writes(config, [("msg", "response")], "task-1", task_path="")
            mock_put_writes.assert_called_once_with(config, [("msg", "response")], "task-1", task_path="")

            # 3. Read checkpoint tuple
            loaded_tuple = saver.get_tuple(config)
            self.assertEqual(loaded_tuple, mock_tuple)
            mock_get_tuple.assert_called_once_with(config)

    def test_consecutive_tutor_requests_lifecycle(self):
        """Consecutive tutor interactions on the same thread maintain state continuity and clean pooling."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        thread_config = {"configurable": {"thread_id": str(THREAD_ID)}}

        # Simulate Request 1: initial user question
        cp1: Checkpoint = {"v": 1, "id": "cp-1", "ts": "2026-11-15T00:00:00Z", "channel_values": {"messages": ["q1"]}, "channel_versions": {}, "versions_seen": {}}
        meta1: CheckpointMetadata = {"source": "input", "step": 1, "writes": {}, "parents": {}}
        tuple1 = CheckpointTuple(config=thread_config, checkpoint=cp1, metadata=meta1, parent_config=None, pending_writes=[])

        # Simulate Request 2: follow-up user question
        cp2: Checkpoint = {"v": 1, "id": "cp-2", "ts": "2026-11-15T00:01:00Z", "channel_values": {"messages": ["q1", "a1", "q2"]}, "channel_versions": {}, "versions_seen": {}}
        meta2: CheckpointMetadata = {"source": "input", "step": 2, "writes": {}, "parents": {}}
        tuple2 = CheckpointTuple(config=thread_config, checkpoint=cp2, metadata=meta2, parent_config=thread_config, pending_writes=[])

        with patch.object(PostgresSaver, "get_tuple", side_effect=[None, tuple1, tuple2]) as mock_get_tuple, \
             patch.object(PostgresSaver, "put", side_effect=[
                 {"configurable": {"checkpoint_id": "cp-1"}},
                 {"configurable": {"checkpoint_id": "cp-2"}},
             ]) as mock_put, \
             patch.object(PostgresSaver, "put_writes") as mock_put_writes:

            # --- Turn 1 ---
            initial_state = saver.get_tuple(thread_config)
            self.assertIsNone(initial_state)

            saver.put(thread_config, cp1, meta1, {})
            saver.put_writes(thread_config, [("messages", "a1")], "task-1")

            # --- Turn 2 (consecutive request) ---
            prior_state = saver.get_tuple(thread_config)
            self.assertIsNotNone(prior_state)
            self.assertEqual(prior_state.checkpoint["channel_values"]["messages"], ["q1"])

            saver.put(thread_config, cp2, meta2, {})
            saver.put_writes(thread_config, [("messages", "a2")], "task-2")

            final_state = saver.get_tuple(thread_config)
            self.assertEqual(final_state.checkpoint["channel_values"]["messages"], ["q1", "a1", "q2"])

            self.assertEqual(mock_get_tuple.call_count, 3)
            self.assertEqual(mock_put.call_count, 2)
            self.assertEqual(mock_put_writes.call_count, 2)

    def test_connection_recovery_on_idle_disconnect(self):
        """Simulate pool detecting an idle disconnect and saver retrying to recover successfully."""
        mock_pool = MagicMock()
        saver = ResilientPostgresSaver(mock_pool)
        config = {"configurable": {"thread_id": str(THREAD_ID)}}
        writes = [("messages", ["answer"])]

        # Simulate first write fails with SSL closed, but retry succeeds because pool provided fresh connection
        call_count = 0

        def flaky_put_writes(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise psycopg.OperationalError("SSL connection has been closed unexpectedly")
            return None

        with patch.object(PostgresSaver, "put_writes", side_effect=flaky_put_writes):
            saver.put_writes(config, writes, "task-1")

        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()
