
"""Tests for EduPath persistent chat operations."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    get_chat_session,
    list_chat_sessions,
    rename_chat_session,
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
        self.assertIn("ORDER BY created_at ASC", second_query)

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
    def test_saves_user_message_and_updates_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection

        cursor.fetchone.side_effect = [
            (SESSION_ID,),
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

        self.assertEqual(cursor.execute.call_count, 3)

        insert_sql = cursor.execute.call_args_list[1].args[0]
        update_sql = cursor.execute.call_args_list[2].args[0]

        self.assertIn("INSERT INTO chat_messages", insert_sql)
        self.assertIn("last_activity_at = NOW()", update_sql)

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

        cursor.execute.assert_called_once()
        self.assertIn(
            "FOR UPDATE",
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

        cursor.fetchone.return_value = renamed_row

        result = rename_chat_session(
            str(USER_ID),
            str(SESSION_ID),
            "Python variables help",
        )

        self.assertEqual(result["title"], "Python variables help")
        self.assertIn(
            "AND user_id = %s",
            cursor.execute.call_args.args[0],
        )

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

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_deletes_owned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = (SESSION_ID,)

        result = delete_chat_session(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertTrue(result)
        self.assertIn(
            "DELETE FROM chat_sessions",
            cursor.execute.call_args.args[0],
        )
        self.assertIn(
            "AND user_id = %s",
            cursor.execute.call_args.args[0],
        )

    @patch("services.chat_service.load_database_url", return_value="test-db")
    @patch("services.chat_service.psycopg.connect")
    def test_delete_returns_false_for_unowned_session(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = None

        result = delete_chat_session(
            str(USER_ID),
            str(SESSION_ID),
        )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
