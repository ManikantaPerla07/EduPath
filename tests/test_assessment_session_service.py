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
        with self.assertRaisesRegex(ValueError, "No active questions"):
            start_assessment(
                str(uuid4()),
                "python-basics",
            )

        mock_fetch.assert_called_once()

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
