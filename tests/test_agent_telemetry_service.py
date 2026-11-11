"""Tests for privacy-conscious agent run lifecycle telemetry."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.agent_telemetry_service import (
    MAX_ACTIVE_RUN_MINUTES,
    AgentRunAlreadyActiveError,
    finish_agent_run,
    start_agent_run,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
RUN_ID = UUID("33333333-3333-4333-8333-333333333333")


def make_database():
    connection = MagicMock()
    cursor = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False
    return connection, cursor


class AgentTelemetryValidationTests(unittest.TestCase):

    def test_start_rejects_invalid_user_id(self):
        with self.assertRaises(ValueError):
            start_agent_run("not-a-uuid")

    def test_start_rejects_invalid_session_id(self):
        with self.assertRaises(ValueError):
            start_agent_run(str(USER_ID), "not-a-uuid")

    def test_finish_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            finish_agent_run(
                USER_ID,
                RUN_ID,
                "running",
                100,
            )

    def test_finish_requires_error_code_for_failed_run(self):
        with self.assertRaises(ValueError):
            finish_agent_run(
                USER_ID,
                RUN_ID,
                "failed",
                100,
            )

    def test_finish_rejects_error_message_as_error_code(self):
        with self.assertRaises(ValueError):
            finish_agent_run(
                USER_ID,
                RUN_ID,
                "failed",
                100,
                error_code="API key failed: secret-value",
            )

    def test_finish_rejects_arbitrary_node_payloads(self):
        with self.assertRaises(ValueError):
            finish_agent_run(
                USER_ID,
                RUN_ID,
                "completed",
                100,
                node_sequence=["retrieve_context", {"prompt": "private"}],
            )

    def test_finish_rejects_invalid_duration(self):
        for duration in (-1, True, 86_400_001, 1.5):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    finish_agent_run(
                        USER_ID,
                        RUN_ID,
                        "completed",
                        duration,
                    )


class AgentTelemetryDatabaseTests(unittest.TestCase):

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_starts_run_for_active_learner_and_owned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (SESSION_ID,),
            None,
            (RUN_ID,),
        ]

        result = start_agent_run(USER_ID, SESSION_ID)

        self.assertEqual(result, RUN_ID)
        self.assertEqual(cursor.execute.call_count, 4)

        lock_sql, lock_parameters = cursor.execute.call_args_list[0].args
        expire_sql, expire_parameters = cursor.execute.call_args_list[1].args
        active_sql, active_parameters = cursor.execute.call_args_list[2].args
        insert_sql, insert_parameters = cursor.execute.call_args_list[3].args

        self.assertIn("u.is_active = TRUE", lock_sql)
        self.assertIn("FOR UPDATE OF u, cs", lock_sql)
        self.assertEqual(lock_parameters, (SESSION_ID, USER_ID))
        self.assertIn("SET", expire_sql)
        self.assertIn("status = 'stopped'", expire_sql)
        self.assertIn("statement_timestamp()", expire_sql)
        self.assertEqual(
            expire_parameters,
            (SESSION_ID, MAX_ACTIVE_RUN_MINUTES),
        )
        self.assertIn("status = 'running'", active_sql)
        self.assertEqual(active_parameters, (SESSION_ID,))
        self.assertIn("INSERT INTO agent_runs", insert_sql)
        self.assertEqual(
            insert_parameters,
            (USER_ID, SESSION_ID, "adaptive_tutor"),
        )

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_rejects_second_running_request_for_same_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (SESSION_ID,),
            (RUN_ID,),
        ]

        with self.assertRaises(AgentRunAlreadyActiveError):
            start_agent_run(USER_ID, SESSION_ID)

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertNotIn(
            "INSERT INTO agent_runs",
            cursor.execute.call_args.args[0],
        )

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_rejects_unowned_session_before_stale_run_cleanup(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            start_agent_run(USER_ID, SESSION_ID)

        cursor.execute.assert_called_once()
        self.assertIn("FOR UPDATE OF u, cs", cursor.execute.call_args.args[0])

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_start_rejects_inactive_learner_or_unowned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            start_agent_run(USER_ID, SESSION_ID)

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_finishes_owned_running_agent_run(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = (RUN_ID,)

        result = finish_agent_run(
            USER_ID,
            RUN_ID,
            "completed",
            456,
            node_sequence=["validate_input", "retrieve_context"],
        )

        self.assertTrue(result)
        query, parameters = cursor.execute.call_args.args
        self.assertIn("status = 'running'", query)
        self.assertIn("AND user_id = %s", query)
        self.assertEqual(parameters[0], "completed")
        self.assertEqual(parameters[1], 456)
        self.assertEqual(parameters[3], None)
        self.assertEqual(parameters[4], RUN_ID)
        self.assertEqual(parameters[5], USER_ID)

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_failed_run_stores_only_exception_class_code(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = (RUN_ID,)

        result = finish_agent_run(
            USER_ID,
            RUN_ID,
            "failed",
            123,
            error_code="AnswerGenerationError",
        )

        self.assertTrue(result)
        parameters = cursor.execute.call_args.args[1]
        self.assertEqual(parameters[3], "AnswerGenerationError")

    @patch("services.agent_telemetry_service.load_database_url", return_value="test-db")
    @patch("services.agent_telemetry_service.psycopg.connect")
    def test_returns_false_when_run_is_not_owned_or_already_finished(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        result = finish_agent_run(
            USER_ID,
            RUN_ID,
            "completed",
            123,
        )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
