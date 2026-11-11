from pathlib import Path
import sys
import unittest
from uuid import uuid4
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.assessment_session_service import start_assessment


class TestAssessmentSessionService(unittest.TestCase):

    def test_invalid_user_id(self):
        with self.assertRaisesRegex(ValueError, "valid learner"):
            start_assessment("not-a-uuid", "python-basics")

    def test_invalid_assessment_type(self):
        with self.assertRaisesRegex(ValueError, "Invalid assessment type"):
            start_assessment(
                str(uuid4()),
                "python-basics",
                assessment_type="exam",
            )

    def test_empty_course_slug(self):
        with self.assertRaisesRegex(ValueError, "Course slug"):
            start_assessment(str(uuid4()), "")

    def test_empty_topic_slug(self):
        with self.assertRaisesRegex(ValueError, "Topic slug"):
            start_assessment(
                str(uuid4()),
                "python-basics",
                topic_slug=" ",
            )

    @patch(
        "services.assessment_session_service.fetch_question_records",
        return_value=[],
    )
    def test_no_available_questions(self, mock_fetch):
        from unittest.mock import MagicMock

        user_id = str(uuid4())
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (user_id,),
            ("22222222-2222-4222-8222-222222222222", True),
        ]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = cursor
        connection.cursor.return_value = cursor_context

        with (
            patch(
                "services.assessment_session_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.assessment_session_service.load_database_url",
                return_value="postgresql://test",
            ),
        ):
            with self.assertRaisesRegex(ValueError, "No active questions"):
                start_assessment(
                    user_id,
                    "python-basics",
                )

        mock_fetch.assert_called_once()
        learner_access_sql = cursor.execute.call_args_list[0].args[0]
        self.assertIn("is_active = TRUE", learner_access_sql)
        self.assertIn("FOR SHARE", learner_access_sql)

    @patch("services.assessment_session_service.fetch_question_records")
    def test_unpublished_course_is_rejected_before_question_selection(
        self,
        fetch_questions,
    ):
        from unittest.mock import MagicMock

        from services.assessment_service import load_database_url

        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("11111111-1111-4111-8111-111111111111",),
            ("22222222-2222-4222-8222-222222222222", False),
        ]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = cursor
        connection.cursor.return_value = cursor_context

        with (
            patch(
                "services.assessment_session_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.assessment_session_service.load_database_url",
                return_value="postgresql://test",
            ),
        ):
            with self.assertRaisesRegex(
                PermissionError,
                "not currently available",
            ):
                start_assessment(
                    "11111111-1111-4111-8111-111111111111",
                    "python-basics",
                )

        fetch_questions.assert_not_called()
        self.assertEqual(cursor.execute.call_count, 2)
        learner_access_sql = cursor.execute.call_args_list[0].args[0]
        self.assertIn("FOR SHARE", learner_access_sql)

    def test_nonexistent_learner_is_rejected(self):
        # Use a random UUID. No fake learner account is inserted.
        with self.assertRaisesRegex(
            ValueError,
            "No active learner account found",
        ):
            start_assessment(
                str(uuid4()),
                "python-basics",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
