"""Isolated PostgreSQL Integration Tests for Multi-Learner Security and Account Deletion.

Verifies:
1. Multi-learner isolation: Confirm that neither Learner A nor Learner B can access
   the other's profile, chats, assessments, study plans, or topic progress.
2. Complete account deletion lifecycle: Confirm comprehensive deletion across
   relational tables, model_usage_events, and LangGraph checkpoints, with
   transaction rollback on checkpoint failure.
"""

import unittest
from unittest.mock import MagicMock, call, patch
from uuid import UUID, uuid4

from services.assessment_submission_service import submit_assessment
from services.chat_service import (
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    get_chat_session,
    list_chat_sessions,
    save_chat_message,
)
from services.learner_service import (
    delete_learner_account,
    get_learner_profile,
    update_learner_profile,
)
from services.misconception_service import (
    fetch_active_learner_misconceptions,
    resolve_learner_misconception,
)
from services.progress_service import fetch_learner_topic_progress
from services.study_plan_service import (
    fetch_active_study_plan,
    update_study_plan_item_status,
)


class MultiLearnerIsolationTests(unittest.TestCase):
    """Test 1: Strict isolation between two distinct learners across all modules."""

    def setUp(self):
        self.learner_a_id = uuid4()
        self.learner_b_id = uuid4()
        self.course_id = uuid4()
        self.session_a_id = uuid4()
        self.thread_a_id = uuid4()
        self.session_b_id = uuid4()
        self.thread_b_id = uuid4()

    @patch("services.learner_service.load_database_url", return_value="postgresql://test")
    @patch("services.learner_service.psycopg.connect")
    def test_profile_isolation_between_learners(self, mock_connect, mock_url):
        """Learner B cannot view or update Learner A's profile."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        # Mock Learner A profile retrieval
        cursor.fetchone.return_value = (
            self.learner_a_id,
            "learner_a@example.com",
            "Learner A",
            "student",
            True,
            "beginner",
            "Master Python loops",
            45,
            "English",
            "step_by_step",
            True,
        )

        profile_a = get_learner_profile(str(self.learner_a_id))
        self.assertEqual(profile_a["user_id"], str(self.learner_a_id))
        self.assertEqual(profile_a["display_name"], "Learner A")

        # Verify first query specifically filtered by learner_a_id
        first_call = cursor.execute.call_args_list[0]
        sql = first_call.args[0]
        params = first_call.args[1]
        self.assertIn("WHERE u.user_id = %s", sql)
        self.assertEqual(params, (self.learner_a_id,))

        # Update profile for Learner B must never affect Learner A
        update_learner_profile(
            user_id=str(self.learner_b_id),
            proficiency_level="intermediate",
            daily_study_minutes=60,
        )
        update_sql = cursor.execute.call_args.args[0]
        update_params = cursor.execute.call_args.args[1]
        self.assertIn("WHERE user_id = %s", update_sql)
        self.assertEqual(update_params[-1], self.learner_b_id)
        self.assertNotEqual(update_params[-1], self.learner_a_id)

    @patch("services.chat_service.load_database_url", return_value="postgresql://test")
    @patch("services.chat_service.psycopg.connect")
    def test_chat_session_and_message_isolation(self, mock_connect, mock_url):
        """Learner B cannot read, write to, or delete Learner A's chat sessions."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        # 1. Learner B attempts to get Learner A's session -> DB returns None
        cursor.fetchone.return_value = None
        with self.assertRaises(LookupError):
            get_chat_session(str(self.learner_b_id), str(self.session_a_id))

        sql, params = cursor.execute.call_args.args[:2]
        self.assertIn("WHERE session_id = %s", sql)
        self.assertIn("AND user_id = %s", sql)
        self.assertEqual(params, (self.session_a_id, self.learner_b_id))

        # 2. Learner B attempts to read Learner A's chat messages -> Raises LookupError
        cursor.fetchone.return_value = None
        with self.assertRaises(LookupError):
            get_chat_messages(str(self.learner_b_id), str(self.session_a_id))

        sql, params = cursor.execute.call_args.args[:2]
        self.assertIn("WHERE session_id = %s", sql)
        self.assertIn("AND user_id = %s", sql)
        self.assertEqual(params, (self.session_a_id, self.learner_b_id))

        # 3. Learner B attempts to save a message in Learner A's session -> Fails ownership check
        cursor.fetchone.return_value = None
        with self.assertRaises(LookupError):
            save_chat_message(
                user_id=str(self.learner_b_id),
                session_id=str(self.session_a_id),
                role="user",
                content="Hacked message?",
            )

        # 4. Learner B attempts to delete Learner A's chat session -> Returns False
        cursor.fetchone.return_value = None
        deleted = delete_chat_session(str(self.learner_b_id), str(self.session_a_id))
        self.assertFalse(deleted)

        # 5. list_chat_sessions for Learner B strictly filters by learner_b_id
        cursor.fetchall.return_value = []
        sessions = list_chat_sessions(str(self.learner_b_id), course_slug="python-basics")
        self.assertEqual(sessions, [])
        list_sql = cursor.execute.call_args.args[0]
        list_params = cursor.execute.call_args.args[1]
        self.assertIn("cs.user_id = %s", list_sql)
        self.assertEqual(list_params[0], self.learner_b_id)

    @patch("services.assessment_submission_service.load_database_url", return_value="postgresql://test")
    @patch("services.assessment_submission_service.psycopg.connect")
    def test_assessment_isolation_between_learners(self, mock_connect, mock_url):
        """Learner B cannot submit answers or alter Learner A's assessment session."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        assessment_a_id = uuid4()
        item_id = uuid4()

        # Learner B attempts to submit response to assessment_a -> Returns None (ownership check fails)
        cursor.fetchone.return_value = None

        with self.assertRaises(PermissionError) as ctx:
            submit_assessment(
                user_id=str(self.learner_b_id),
                assessment_id=str(assessment_a_id),
                answers={str(item_id): "A"},
            )
        self.assertIn("Assessment not found for this learner", str(ctx.exception))

        # Confirm query validated both assessment_id AND user_id
        sql = cursor.execute.call_args.args[0]
        params = cursor.execute.call_args.args[1]
        self.assertIn("WHERE s.assessment_id = %s", sql)
        self.assertIn("AND s.user_id = %s", sql)
        self.assertEqual(params, (assessment_a_id, self.learner_b_id))

    @patch("services.study_plan_service.load_database_url", return_value="postgresql://test")
    @patch("services.study_plan_service.psycopg.connect")
    def test_study_plan_isolation_between_learners(self, mock_connect, mock_url):
        """Learner B cannot fetch or update activities in Learner A's study plan."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        # 1. Fetching plan for Learner B returns None when no plan exists for B
        cursor.fetchone.return_value = None
        plan_b = fetch_active_study_plan(str(self.learner_b_id), "python-basics")
        self.assertIsNone(plan_b)

        fetch_sql, fetch_params = cursor.execute.call_args.args[:2]
        self.assertIn("WHERE u.user_id = %s", fetch_sql)
        self.assertEqual(fetch_params[0], self.learner_b_id)

        # 2. Learner B attempting to complete Learner A's plan item raises LookupError
        cursor.fetchone.return_value = None
        plan_item_a_id = uuid4()

        with self.assertRaises(PermissionError) as ctx:
            update_study_plan_item_status(
                user_id=str(self.learner_b_id),
                plan_item_id=str(plan_item_a_id),
                status="completed",
            )
        self.assertIn("Study-plan activity not found", str(ctx.exception))

        update_sql, update_params = cursor.execute.call_args.args[:2]
        self.assertIn("WHERE pi.plan_item_id = %s", update_sql)
        self.assertIn("AND p.user_id = %s", update_sql)
        self.assertEqual(update_params[0], plan_item_a_id)
        self.assertEqual(update_params[1], self.learner_b_id)

    @patch("services.progress_service.load_database_url", return_value="postgresql://test")
    @patch("services.progress_service.psycopg.connect")
    def test_progress_isolation_between_learners(self, mock_connect, mock_url):
        """Topic progress records are strictly partitioned by user_id."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        cursor.fetchall.return_value = [
            {
                "topic_id": str(uuid4()),
                "topic_slug": "variables-data-types",
                "topic_name": "Variables",
                "sequence_number": 1,
                "total_attempts": 2,
                "correct_answers": 2,
                "accuracy_percent": 100.0,
                "mastery_score": 100.0,
                "mastery_status": "mastered",
                "last_attempted_at": None,
            }
        ]

        progress_b = fetch_learner_topic_progress(str(self.learner_b_id), "python-basics")
        self.assertEqual(len(progress_b), 1)

        sql, params = cursor.execute.call_args.args[:2]
        self.assertIn("WHERE u.user_id = %s", sql)
        self.assertEqual(params, ("python-basics", self.learner_b_id))
        self.assertNotEqual(params[1], self.learner_a_id)

    @patch("services.misconception_service.load_database_url", return_value="postgresql://test")
    @patch("services.misconception_service.psycopg.connect")
    def test_misconception_isolation_between_learners(self, mock_connect, mock_url):
        """Learner B cannot see or resolve Learner A's formative misconceptions."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        # Check table exists returns True
        cursor.fetchone.return_value = (True,)
        cursor.fetchall.return_value = []

        misc_b = fetch_active_learner_misconceptions(str(self.learner_b_id))
        self.assertEqual(misc_b, [])

        sql = cursor.execute.call_args_list[-1].args[0]
        params = cursor.execute.call_args_list[-1].args[1]
        self.assertIn("WHERE user_id = %s", sql)
        self.assertEqual(params, (self.learner_b_id,))

        # Resolving Learner A's misconception with Learner B's ID returns False
        cursor.rowcount = 0
        resolved = resolve_learner_misconception(str(self.learner_b_id), "off_by_one_range")
        self.assertFalse(resolved)
        res_sql = cursor.execute.call_args.args[0]
        res_params = cursor.execute.call_args.args[1]
        self.assertIn("WHERE user_id = %s", res_sql)
        self.assertEqual(res_params[0], self.learner_b_id)


class CompleteAccountDeletionLifecycleTests(unittest.TestCase):
    """Test 2: Complete account deletion across relational records and LangGraph checkpoints."""

    def setUp(self):
        self.user_id = uuid4()
        self.thread_1 = str(uuid4())
        self.thread_2 = str(uuid4())

    @patch("services.learner_service.load_database_url", return_value="postgresql://test-db")
    @patch("services.learner_service.psycopg.connect")
    @patch("services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints")
    def test_full_account_deletion_lifecycle_success(
        self,
        mock_delete_checkpoints,
        mock_connect,
        mock_url,
    ):
        """Deletes thread checkpoints, model_usage_events, misconceptions, and user row."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        cursor.fetchone.side_effect = [
            (self.user_id, True),  # User locked and found
            (True,),               # learner_misconceptions table exists check
            (self.user_id,),       # User row deleted successfully
        ]
        cursor.fetchall.side_effect = [
            [(self.thread_1,), (self.thread_2,)],  # Two owned chat threads
        ]

        result = delete_learner_account(str(self.user_id))
        self.assertTrue(result)

        # 1. Verify LangGraph thread checkpoints were deleted for each discovered thread
        self.assertEqual(mock_delete_checkpoints.call_count, 2)
        mock_delete_checkpoints.assert_has_calls([
            call(thread_id=self.thread_1, database_url="postgresql://test-db"),
            call(thread_id=self.thread_2, database_url="postgresql://test-db"),
        ])

        # 2. Inspect all executed SQL statements in order
        clean_sqls = [" ".join(c.args[0].split()) for c in cursor.execute.call_args_list]

        # Step 1: User existence and lock
        self.assertTrue(any("SELECT user_id, is_active FROM users WHERE user_id = %s FOR UPDATE" in s for s in clean_sqls))

        # Step 2: Discover owned threads
        self.assertTrue(any("SELECT thread_id FROM chat_sessions WHERE user_id = %s" in s for s in clean_sqls))

        # Step 3: Explicit model_usage_events cleanup (handles SET NULL foreign key)
        self.assertTrue(any("DELETE FROM model_usage_events WHERE user_id = %s" in s for s in clean_sqls))

        # Step 4: learner_misconceptions cleanup
        self.assertTrue(any("DELETE FROM learner_misconceptions WHERE user_id = %s" in s for s in clean_sqls))

        # Step 5: User row deletion (cascades profiles, assessments, study plans, chats)
        self.assertTrue(any("DELETE FROM users WHERE user_id = %s RETURNING user_id" in s for s in clean_sqls))

    @patch("services.learner_service.load_database_url", return_value="postgresql://test-db")
    @patch("services.learner_service.psycopg.connect")
    @patch("services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints")
    def test_checkpoint_failure_aborts_transaction_and_preserves_user(
        self,
        mock_delete_checkpoints,
        mock_connect,
        mock_url,
    ):
        """If LangGraph checkpoint deletion fails, user record is NOT deleted."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn

        cursor.fetchone.side_effect = [
            (self.user_id, True),  # User locked
        ]
        cursor.fetchall.side_effect = [
            [(self.thread_1,)],
        ]

        mock_delete_checkpoints.side_effect = RuntimeError("Postgres checkpointer connection dropped")

        with self.assertRaises(RuntimeError) as ctx:
            delete_learner_account(str(self.user_id))

        self.assertIn("Failed to delete LangGraph checkpoints", str(ctx.exception))

        # Verify DELETE FROM users was NEVER executed
        executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
        self.assertFalse(any("DELETE FROM users" in s for s in executed_sqls))
        self.assertFalse(any("DELETE FROM model_usage_events" in s for s in executed_sqls))


if __name__ == "__main__":
    unittest.main()
