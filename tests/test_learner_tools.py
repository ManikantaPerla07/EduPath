"""Tests for the authenticated, read-only learner data tools."""

import json
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from agents.learner_tools import (
    get_my_learning_progress,
    get_my_study_plan,
)


USER_ID = "ea181992-f802-4528-ae24-10b7e198d8a2"
COURSE_SLUG = "python-basics"


def make_runtime(state=None):
    """Create a small ToolRuntime-compatible test double."""

    return SimpleNamespace(
        state=state
        if state is not None
        else {
            "user_id": USER_ID,
            "course_slug": COURSE_SLUG,
        }
    )


class LearnerToolSchemaTests(unittest.TestCase):

    def test_model_cannot_supply_learner_or_course_identifiers(self):
        self.assertEqual(get_my_learning_progress.args, {})
        self.assertEqual(get_my_study_plan.args, {})

    def test_tools_are_read_only_and_have_expected_names(self):
        self.assertEqual(
            get_my_learning_progress.name,
            "get_my_learning_progress",
        )
        self.assertEqual(
            get_my_study_plan.name,
            "get_my_study_plan",
        )


class LearningProgressToolTests(unittest.TestCase):

    @patch("agents.learner_tools.fetch_learner_topic_progress")
    def test_uses_authenticated_state_and_returns_allowlisted_progress(
        self,
        fetch_progress,
    ):
        fetch_progress.return_value = [
            {
                "topic_slug": "variables-data-types",
                "topic_name": "Variables and Data Types",
                "total_attempts": 5,
                "correct_answers": 4,
                "accuracy_percent": Decimal("80.00"),
                "mastery_score": Decimal("80.00"),
                "mastery_status": "candidate_for_mastery",
                "last_attempted_at": datetime(
                    2026, 11, 10, 9, 30, tzinfo=timezone.utc
                ),
                "user_id": "must-not-be-exposed",
                "internal_note": "must-not-be-exposed",
            }
        ]

        output = get_my_learning_progress.func(make_runtime())
        payload = json.loads(output)

        fetch_progress.assert_called_once_with(
            user_id=USER_ID,
            course_slug=COURSE_SLUG,
        )
        self.assertEqual(payload["topic_count"], 1)
        self.assertEqual(
            payload["topics"][0]["accuracy_percent"],
            80.0,
        )
        self.assertEqual(
            payload["topics"][0]["last_attempted_at"],
            "2026-11-10T09:30:00+00:00",
        )
        self.assertNotIn("user_id", output)
        self.assertNotIn("internal_note", output)


class StudyPlanToolTests(unittest.TestCase):

    @patch("agents.learner_tools.fetch_active_study_plan")
    def test_returns_plan_summary_and_activity_details(self, fetch_plan):
        fetch_plan.return_value = {
            "title": "Python Foundations",
            "status": "active",
            "start_date": date(2026, 11, 10),
            "end_date": date(2026, 11, 19),
            "items": [
                {
                    "topic_name": "Variables and Data Types",
                    "topic_slug": "variables-data-types",
                    "activity_type": "revision",
                    "scheduled_date": date(2026, 11, 11),
                    "estimated_minutes": 20,
                    "status": "completed",
                    "recommendation_reason": "Review your earlier attempts.",
                    "plan_item_id": "private-id",
                },
                {
                    "topic_name": "Conditional Statements",
                    "topic_slug": "conditional-statements",
                    "activity_type": "practice",
                    "scheduled_date": date(2026, 11, 12),
                    "estimated_minutes": 25,
                    "status": "pending",
                    "recommendation_reason": "Build on the prerequisites.",
                },
            ],
        }

        output = get_my_study_plan.func(make_runtime())
        payload = json.loads(output)

        fetch_plan.assert_called_once_with(
            user_id=USER_ID,
            course_slug=COURSE_SLUG,
        )
        self.assertTrue(payload["found"])
        self.assertEqual(payload["completion_percent"], 50.0)
        self.assertEqual(payload["activity_counts"]["completed"], 1)
        self.assertEqual(payload["activity_counts"]["pending"], 1)
        self.assertEqual(
            payload["activities"][0]["scheduled_date"],
            "2026-11-11",
        )
        self.assertNotIn("private-id", output)
        self.assertNotIn("plan_item_id", output)

    @patch("agents.learner_tools.fetch_active_study_plan", return_value=None)
    def test_reports_when_no_study_plan_exists(self, fetch_plan):
        payload = json.loads(
            get_my_study_plan.func(make_runtime())
        )

        fetch_plan.assert_called_once_with(
            user_id=USER_ID,
            course_slug=COURSE_SLUG,
        )
        self.assertFalse(payload["found"])
        self.assertEqual(
            payload["message"],
            "No current study plan was found.",
        )


class LearnerToolScopeTests(unittest.TestCase):

    def test_progress_tool_rejects_missing_authenticated_user(self):
        with self.assertRaisesRegex(
            ValueError,
            "Authenticated learner context is unavailable",
        ):
            get_my_learning_progress.func(
                make_runtime({"course_slug": COURSE_SLUG})
            )

    def test_study_plan_tool_rejects_missing_course(self):
        with self.assertRaisesRegex(
            ValueError,
            "Course context is unavailable",
        ):
            get_my_study_plan.func(
                make_runtime({"user_id": USER_ID})
            )


if __name__ == "__main__":
    unittest.main()
