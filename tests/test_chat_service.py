
"""Tests for EduPath persistent chat operations."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.agent_telemetry_service import MAX_ACTIVE_RUN_MINUTES
from services.chat_service import (
    CHAT_RATE_LIMIT_WINDOW_MINUTES,
    MAX_USER_QUESTIONS_PER_WINDOW,
    ChatRateLimitError,
    ChatSessionBusyError,
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    get_chat_session,
    list_chat_sessions,
    rename_chat_session,
    save_chat_feedback,
    save_chat_message,
)


USER_ID = UUID("ea181992-f802-4528-ae24-10b7e198d8a2")
SESSION_ID = UUID("11111111-1111-4111-8111-111111111111")
COURSE_ID = UUID("13740e10-d727-4b6d-9e7c-61774bb72913")
THREAD_ID = UUID("22222222-2222-4222-8222-222222222222")
MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")

NOW = datetime.now(timezone.utc)


def session_row():
    return (
        SESSION_ID,
        USER_ID,
        COURSE_ID,
        THREAD_ID,
        None,
        NOW,
        NOW,
    )


def message_row():
    return (
        MESSAGE_ID,
        SESSION_ID,
        "user",
        "What is a Python variable?",
        [],
        NOW,
    )


def make_database():
    """Create a mocked Psycopg connection and cursor."""

    connection = MagicMock()
    cursor = MagicMock()

    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    return connection, cursor


class ChatValidationTests(unittest.TestCase):

    def test_create_rejects_invalid_user_id(self):
        with self.assertRaises(ValueError):
            create_chat_session("not-a-uuid", "python-basics")

    def test_create_rejects_empty_course_slug(self):
        with self.assertRaises(ValueError):
            create_chat_session(str(USER_ID), " ")

    def test_create_rejects_empty_title(self):
        with self.assertRaises(ValueError):
            create_chat_session(
                str(USER_ID),
                "python-basics",
                title=" ",
            )

    def test_create_rejects_title_over_limit(self):
        with self.assertRaises(ValueError):
            create_chat_session(
                str(USER_ID),
                "python-basics",
                title="x" * (MAX_TITLE_LENGTH + 1),
            )

    def test_list_rejects_invalid_limit(self):
        for invalid_limit in (0, -1, 101, True, 1.5):
            with self.subTest(limit=invalid_limit):
                with self.assertRaises(ValueError):
                    list_chat_sessions(
                        str(USER_ID),
                        limit=invalid_limit,
                    )

    def test_get_rejects_invalid_session_id(self):
        with self.assertRaises(ValueError):
            get_chat_session(str(USER_ID), "invalid")

    def test_message_rejects_invalid_role(self):
        with self.assertRaises(ValueError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "system",
                "You are an assistant.",
            )

    def test_message_rejects_empty_content(self):
        with self.assertRaises(ValueError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "user",
                "   ",
            )

    def test_message_rejects_content_over_limit(self):
        with self.assertRaises(ValueError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "user",
                "x" * (MAX_MESSAGE_LENGTH + 1),
            )

    def test_message_rejects_non_list_citations(self):
        with self.assertRaises(ValueError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "assistant",
                "Here is the answer.",
                citations={"source": "S1"},
            )

    def test_message_rejects_non_mapping_citation(self):
        with self.assertRaises(ValueError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "assistant",
                "Here is the answer.",
                citations=["S1"],
            )

    def test_feedback_rejects_non_boolean_rating(self):
        for rating in (0, 1, "helpful", None):
            with self.subTest(rating=rating):
                with self.assertRaises(ValueError):
                    save_chat_feedback(
                        str(USER_ID),
                        str(MESSAGE_ID),
                        rating,
                    )

    def test_feedback_rejects_invalid_message_id(self):
        with self.assertRaises(ValueError):
            save_chat_feedback(
                str(USER_ID),
                "not-a-uuid",
                True,
            )


class ChatDatabaseTests(unittest.TestCase):


    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_lists_sessions_without_course_filter(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        cursor.fetchall.return_value = [
            (*session_row(), "python-basics", 2)
        ]

        result = list_chat_sessions(
            str(USER_ID),
            course_slug=None,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["session_id"], str(SESSION_ID))
        self.assertEqual(result[0]["message_count"], 2)

        sql, parameters = cursor.execute.call_args.args

        self.assertNotIn("c.course_slug = %s", sql)
        self.assertEqual(parameters, (USER_ID, 50))


    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_creates_chat_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = session_row()

        result = create_chat_session(
            str(USER_ID),
            "python-basics",
        )

        self.assertEqual(result["session_id"], str(SESSION_ID))
        self.assertEqual(result["user_id"], str(USER_ID))
        self.assertEqual(result["course_id"], str(COURSE_ID))
        self.assertEqual(result["thread_id"], str(THREAD_ID))

        sql = cursor.execute.call_args.args[0]
        self.assertIn("u.is_active = TRUE", sql)
        self.assertIn("FOR SHARE OF u", sql)
        self.assertIn("c.course_slug = %s", sql)

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_create_rejects_missing_or_inactive_user_or_course(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(ValueError):
            create_chat_session(
                str(USER_ID),
                "python-basics",
            )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_lists_only_learner_sessions(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        cursor.fetchall.return_value = [
            (*session_row(), "python-basics", 4)
        ]

        result = list_chat_sessions(
            str(USER_ID),
            course_slug="python-basics",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["session_id"], str(SESSION_ID))
        self.assertEqual(result[0]["course_slug"], "python-basics")
        self.assertEqual(result[0]["message_count"], 4)

        parameters = cursor.execute.call_args.args[1]
        self.assertEqual(parameters[0], USER_ID)

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_get_session_returns_owned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = session_row()

        result = get_chat_session(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertEqual(result["session_id"], str(SESSION_ID))
        self.assertEqual(result["thread_id"], str(THREAD_ID))

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_get_session_rejects_session_not_owned_by_user(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            get_chat_session(
                str(USER_ID),
                str(SESSION_ID),
            )

        sql = cursor.execute.call_args.args[0]
        self.assertIn("AND user_id = %s", sql)

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_get_messages_returns_chronological_rows(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        cursor.fetchone.return_value = (SESSION_ID,)
        cursor.fetchall.return_value = [message_row()]

        result = get_chat_messages(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(
            result[0]["content"],
            "What is a Python variable?",
        )

        second_query = cursor.execute.call_args_list[1].args[0]
        self.assertIn("ORDER BY created_at DESC, message_id DESC", second_query)
        self.assertIn("LIMIT %s", second_query)
        self.assertIn(
            "recent_messages.created_at ASC",
            second_query,
        )
        self.assertIn("chat_message_feedback", second_query)
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            (SESSION_ID, 100, USER_ID),
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_get_messages_rejects_unowned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            get_chat_messages(
                str(USER_ID),
                str(SESSION_ID),
            )

        cursor.execute.assert_called_once()

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_get_messages_includes_saved_feedback(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = (SESSION_ID,)
        cursor.fetchall.return_value = [(*message_row(), False)]

        result = get_chat_messages(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertIs(result[0]["feedback"], False)
        query, parameters = cursor.execute.call_args_list[1].args
        self.assertIn("feedback.user_id = %s", query)
        self.assertEqual(parameters, (SESSION_ID, 100, USER_ID))


    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_saves_or_updates_feedback_for_owned_assistant_message(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (USER_ID,),
            (
                MESSAGE_ID,
                USER_ID,
                True,
                NOW,
                NOW,
            ),
        ]

        result = save_chat_feedback(
            str(USER_ID),
            str(MESSAGE_ID),
            True,
        )

        self.assertEqual(result["message_id"], str(MESSAGE_ID))
        self.assertEqual(result["user_id"], str(USER_ID))
        self.assertIs(result["is_helpful"], True)

        self.assertEqual(cursor.execute.call_count, 2)
        lock_query = cursor.execute.call_args_list[0].args[0]
        query, parameters = cursor.execute.call_args_list[1].args
        self.assertIn("is_active = TRUE", lock_query)
        self.assertIn("FOR SHARE", lock_query)
        self.assertIn("cm.role = 'assistant'", query)
        self.assertIn("cs.user_id = %s", query)
        self.assertIn("ON CONFLICT (message_id) DO UPDATE", query)
        self.assertIn(
            "WHERE chat_message_feedback.user_id = EXCLUDED.user_id",
            query,
        )
        self.assertEqual(parameters, (True, MESSAGE_ID, USER_ID))


    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_feedback_rejects_inactive_account_before_insert(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaisesRegex(
            LookupError,
            "active learner account",
        ):
            save_chat_feedback(
                str(USER_ID),
                str(MESSAGE_ID),
                True,
            )

        cursor.execute.assert_called_once()
        self.assertIn(
            "is_active = TRUE",
            cursor.execute.call_args.args[0],
        )
        self.assertIn(
            "FOR SHARE",
            cursor.execute.call_args.args[0],
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_feedback_rejects_unowned_or_non_assistant_message(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [(USER_ID,), None]

        with self.assertRaises(LookupError):
            save_chat_feedback(
                str(USER_ID),
                str(MESSAGE_ID),
                False,
            )

        self.assertEqual(cursor.execute.call_count, 2)
        lock_query = cursor.execute.call_args_list[0].args[0]
        query, parameters = cursor.execute.call_args_list[1].args
        self.assertIn("is_active = TRUE", lock_query)
        self.assertIn("FOR SHARE", lock_query)
        self.assertIn("cs.user_id = %s", query)
        self.assertIn("cm.role = 'assistant'", query)
        self.assertEqual(parameters, (False, MESSAGE_ID, USER_ID))


    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_saves_user_message_and_updates_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        cursor.fetchone.side_effect = [
            (SESSION_ID,),
            (0, 1),
            message_row(),
        ]

        result = save_chat_message(
            str(USER_ID),
            str(SESSION_ID),
            "user",
            "What is a Python variable?",
        )

        self.assertEqual(result["message_id"], str(MESSAGE_ID))
        self.assertEqual(result["role"], "user")
        self.assertEqual(result["citations"], [])

        self.assertEqual(cursor.execute.call_count, 4)

        account_session_lock_sql = cursor.execute.call_args_list[0].args[0]
        rate_limit_sql = cursor.execute.call_args_list[1].args[0]
        insert_sql = cursor.execute.call_args_list[2].args[0]
        update_sql = cursor.execute.call_args_list[3].args[0]

        self.assertIn("FROM users AS u", account_session_lock_sql)
        self.assertIn("u.is_active = TRUE", account_session_lock_sql)
        self.assertIn("FOR UPDATE OF u, cs", account_session_lock_sql)
        self.assertIn("COUNT(*)::INTEGER", rate_limit_sql)
        self.assertIn("created_at >=", rate_limit_sql)
        self.assertIn("statement_timestamp()", rate_limit_sql)
        self.assertIn("INSERT INTO chat_messages", insert_sql)
        self.assertIn("last_activity_at = NOW()", update_sql)
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            (
                CHAT_RATE_LIMIT_WINDOW_MINUTES,
                USER_ID,
                CHAT_RATE_LIMIT_WINDOW_MINUTES,
            ),
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_rejects_user_question_when_rolling_limit_is_reached(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (SESSION_ID,),
            (MAX_USER_QUESTIONS_PER_WINDOW, 125),
        ]

        with self.assertRaises(ChatRateLimitError) as context:
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "user",
                "Another Python question",
            )

        self.assertEqual(context.exception.retry_after_seconds, 125)
        self.assertIn("20 questions every 10 minutes", str(context.exception))
        self.assertEqual(cursor.execute.call_count, 2)
        executed_sql = [
            call.args[0]
            for call in cursor.execute.call_args_list
        ]
        self.assertFalse(
            any("INSERT INTO chat_messages" in query for query in executed_sql)
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_rejects_inactive_learner_before_session_access(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "user",
                "Hello",
            )

        cursor.execute.assert_called_once()
        self.assertIn("u.is_active = TRUE", cursor.execute.call_args.args[0])
        self.assertIn("FOR UPDATE OF u, cs", cursor.execute.call_args.args[0])

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_saves_assistant_citations(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        assistant_row = (
            MESSAGE_ID,
            SESSION_ID,
            "assistant",
            "Python variables store values. [S1]",
            [
                {
                    "source_id": "S1",
                    "source_title": "Python Variables Notes",
                }
            ],
            NOW,
        )

        cursor.fetchone.side_effect = [
            (SESSION_ID,),
            assistant_row,
        ]

        result = save_chat_message(
            str(USER_ID),
            str(SESSION_ID),
            "assistant",
            "Python variables store values. [S1]",
            citations=assistant_row[4],
        )

        self.assertEqual(result["role"], "assistant")
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(
            result["citations"][0]["source_id"],
            "S1",
        )
        self.assertEqual(cursor.execute.call_count, 2)
        assistant_write_sql = [
            call.args[0]
            for call in cursor.execute.call_args_list
        ]
        self.assertIn("FROM users AS u", assistant_write_sql[0])
        self.assertIn("u.is_active = TRUE", assistant_write_sql[0])
        self.assertIn("FOR UPDATE OF u, cs", assistant_write_sql[0])
        self.assertFalse(
            any("COUNT(*)::INTEGER" in query for query in assistant_write_sql)
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_rejects_assistant_reply_after_account_deactivation(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaisesRegex(
            LookupError,
            "active learner account",
        ):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "assistant",
                "A generated response",
            )

        cursor.execute.assert_called_once()
        self.assertIn(
            "u.is_active = TRUE",
            cursor.execute.call_args.args[0],
        )
        self.assertIn(
            "FOR UPDATE OF u, cs",
            cursor.execute.call_args.args[0],
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_save_rejects_unowned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            save_chat_message(
                str(USER_ID),
                str(SESSION_ID),
                "user",
                "Hello",
            )

        self.assertEqual(cursor.execute.call_count, 1)
        self.assertIn(
            "FOR UPDATE OF u, cs",
            cursor.execute.call_args.args[0],
        )
        self.assertIn(
            "u.is_active = TRUE",
            cursor.execute.call_args.args[0],
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_renames_owned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        renamed_row = (
            SESSION_ID,
            USER_ID,
            COURSE_ID,
            THREAD_ID,
            "Python variables help",
            NOW,
            NOW,
        )

        cursor.fetchone.side_effect = [
            (SESSION_ID,),
            renamed_row,
        ]

        result = rename_chat_session(
            str(USER_ID),
            str(SESSION_ID),
            "Python variables help",
        )

        self.assertEqual(result["title"], "Python variables help")
        self.assertEqual(cursor.execute.call_count, 2)
        lock_query = cursor.execute.call_args_list[0].args[0]
        update_query = cursor.execute.call_args_list[1].args[0]
        self.assertIn("u.is_active = TRUE", lock_query)
        self.assertIn("FOR UPDATE OF u, cs", lock_query)
        self.assertIn("AND user_id = %s", update_query)

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_rename_rejects_inactive_account(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaisesRegex(LookupError, "active learner account"):
            rename_chat_session(
                str(USER_ID),
                str(SESSION_ID),
                "New title",
            )

        cursor.execute.assert_called_once()
        self.assertIn("u.is_active = TRUE", cursor.execute.call_args.args[0])

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_rename_rejects_unowned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            rename_chat_session(
                str(USER_ID),
                str(SESSION_ID),
                "New title",
            )

    @patch("services.chat_service.delete_langgraph_thread_checkpoints")
    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_deletes_owned_session_and_checkpoints(
        self,
        mock_connect,
        mock_database_url,
        mock_delete_checkpoints,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (THREAD_ID,),
            None,
            (SESSION_ID,),
        ]

        result = delete_chat_session(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertTrue(result)
        mock_delete_checkpoints.assert_called_once_with(
            thread_id=THREAD_ID,
            database_url="test-db",
        )
        self.assertEqual(cursor.execute.call_count, 4)
        initial_lock_query = cursor.execute.call_args_list[0].args[0]
        self.assertIn("SELECT cs.thread_id", initial_lock_query)
        self.assertIn("JOIN users AS u", initial_lock_query)
        self.assertIn("u.is_active = TRUE", initial_lock_query)
        self.assertIn("FOR UPDATE OF u, cs", initial_lock_query)
        self.assertIn(
            "UPDATE agent_runs",
            cursor.execute.call_args_list[1].args[0],
        )
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            (SESSION_ID, MAX_ACTIVE_RUN_MINUTES),
        )
        active_run_query = cursor.execute.call_args_list[2].args[0]
        self.assertIn("SELECT run_id", active_run_query)
        self.assertIn("status = 'running'", active_run_query)
        self.assertIn("statement_timestamp()", active_run_query)
        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (SESSION_ID, MAX_ACTIVE_RUN_MINUTES),
        )
        self.assertIn(
            "DELETE FROM chat_sessions",
            cursor.execute.call_args_list[3].args[0],
        )
        self.assertIn(
            "AND user_id = %s",
            cursor.execute.call_args_list[3].args[0],
        )

    @patch("services.chat_service.delete_langgraph_thread_checkpoints")
    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_delete_is_blocked_while_tutor_run_is_active(
        self,
        mock_connect,
        mock_database_url,
        mock_delete_checkpoints,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (THREAD_ID,),
            (UUID("44444444-4444-4444-8444-444444444444"),),
        ]

        with self.assertRaisesRegex(
            ChatSessionBusyError,
            "currently generating a response",
        ):
            delete_chat_session(
                str(USER_ID),
                str(SESSION_ID),
            )

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertIn(
            "SELECT thread_id",
            cursor.execute.call_args_list[0].args[0],
        )
        self.assertIn(
            "UPDATE agent_runs",
            cursor.execute.call_args_list[1].args[0],
        )
        active_run_query = cursor.execute.call_args_list[2].args[0]
        self.assertIn("SELECT run_id", active_run_query)
        self.assertIn("started_at >=", active_run_query)
        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (SESSION_ID, MAX_ACTIVE_RUN_MINUTES),
        )
        self.assertFalse(
            any(
                "DELETE FROM chat_sessions" in call.args[0]
                for call in cursor.execute.call_args_list
            )
        )
        mock_delete_checkpoints.assert_not_called()

    @patch("services.chat_service.delete_langgraph_thread_checkpoints")
    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_delete_rejects_inactive_account(
        self,
        mock_connect,
        mock_database_url,
        mock_delete_checkpoints,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        result = delete_chat_session(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertFalse(result)
        cursor.execute.assert_called_once()
        self.assertIn("u.is_active = TRUE", cursor.execute.call_args.args[0])
        mock_delete_checkpoints.assert_not_called()

    @patch("services.chat_service.delete_langgraph_thread_checkpoints")
    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_delete_returns_false_for_unowned_session(
        self,
        mock_connect,
        mock_database_url,
        mock_delete_checkpoints,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        result = delete_chat_session(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertFalse(result)
        cursor.execute.assert_called_once()
        mock_delete_checkpoints.assert_not_called()

    @patch(
        "services.chat_service.delete_langgraph_thread_checkpoints",
        side_effect=RuntimeError("Checkpoint store unavailable"),
    )
    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_does_not_delete_chat_when_checkpoint_cleanup_fails(
        self,
        mock_connect,
        mock_database_url,
        mock_delete_checkpoints,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            (THREAD_ID,),
            None,
        ]

        with self.assertRaisesRegex(
            RuntimeError,
            "Checkpoint store unavailable",
        ):
            delete_chat_session(
                str(USER_ID),
                str(SESSION_ID),
            )

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertIn(
            "SELECT thread_id",
            cursor.execute.call_args_list[0].args[0],
        )
        self.assertIn(
            "UPDATE agent_runs",
            cursor.execute.call_args_list[1].args[0],
        )
        self.assertIn(
            "SELECT run_id",
            cursor.execute.call_args_list[2].args[0],
        )


if __name__ == "__main__":
    unittest.main()
