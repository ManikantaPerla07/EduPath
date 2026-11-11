"""Tests for EduPath's secure LangGraph PostgreSQL checkpoint service."""

import unittest
from unittest.mock import ANY, MagicMock, patch
from uuid import UUID

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from services.langgraph_checkpoint_service import (
    delete_langgraph_thread_checkpoints,
    open_langgraph_checkpointer,
)


THREAD_ID = UUID("22222222-2222-4222-8222-222222222222")


class LangGraphCheckpointServiceTests(unittest.TestCase):

    @patch("services.langgraph_checkpoint_service.PostgresSaver")
    @patch("services.langgraph_checkpoint_service.psycopg.connect")
    def test_opens_autocommit_dictionary_row_connection(
        self,
        mock_connect,
        mock_saver_class,
    ):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.__exit__.return_value = False
        mock_connect.return_value = connection

        expected_saver = MagicMock()
        mock_saver_class.return_value = expected_saver

        with open_langgraph_checkpointer("postgresql://test") as checkpointer:
            self.assertIs(checkpointer, expected_saver)

        mock_connect.assert_called_once_with(
            "postgresql://test",
            connect_timeout=20,
            autocommit=True,
            row_factory=ANY,
        )

        saver_arguments = mock_saver_class.call_args.kwargs
        self.assertIs(mock_saver_class.call_args.args[0], connection)
        serializer = saver_arguments["serde"]
        self.assertIsInstance(serializer, JsonPlusSerializer)
        self.assertIsNone(serializer._allowed_msgpack_modules)

    @patch("services.langgraph_checkpoint_service.open_langgraph_checkpointer")
    def test_deletes_all_checkpoints_for_the_normalized_thread(
        self,
        mock_open_checkpointer,
    ):
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
        with self.assertRaisesRegex(ValueError, "valid LangGraph thread ID"):
            delete_langgraph_thread_checkpoints("not-a-uuid")

        mock_open_checkpointer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
