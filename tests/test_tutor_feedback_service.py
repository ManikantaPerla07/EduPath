"""Tests for administrator-only aggregate Tutor feedback insights."""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.tutor_feedback_service import (
    DEFAULT_TREND_DAYS,
    get_tutor_feedback_summary,
)


ADMIN_ID = "11111111-1111-4111-8111-111111111111"


def make_database():
    connection = MagicMock()
    cursor = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False
    return connection, cursor


class TutorFeedbackValidationTests(unittest.TestCase):

    def test_rejects_invalid_admin_id(self):
        with self.assertRaises(ValueError):
            get_tutor_feedback_summary("not-a-uuid", "python-basics")

    def test_rejects_empty_course_slug(self):
        with self.assertRaises(ValueError):
            get_tutor_feedback_summary(ADMIN_ID, " ")

    def test_rejects_invalid_trend_window(self):
        for days in (0, -1, 91, True, 1.5):
            with self.subTest(days=days):
                with self.assertRaises(ValueError):
                    get_tutor_feedback_summary(
                        ADMIN_ID,
                        "python-basics",
                        days=days,
                    )


class TutorFeedbackDatabaseTests(unittest.TestCase):

    @patch("services.tutor_feedback_service.load_database_url", return_value="test-db")
    @patch("services.tutor_feedback_service.psycopg.connect")
    def test_returns_aggregate_metrics_and_daily_trend(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        today = date.today()
        cursor.fetchone.side_effect = [
            ("admin",),
            (20, 12, 9, 3),
        ]
        cursor.fetchall.return_value = [
            (today - timedelta(days=1), 2, 1, 1),
            (today, 3, 3, 0),
        ]

        result = get_tutor_feedback_summary(
            ADMIN_ID,
            "python-basics",
            days=14,
        )

        self.assertEqual(result["assistant_answer_count"], 20)
        self.assertEqual(result["rated_answer_count"], 12)
        self.assertEqual(result["helpful_count"], 9)
        self.assertEqual(result["not_helpful_count"], 3)
        self.assertEqual(result["rating_coverage_percent"], 60.0)
        self.assertEqual(result["helpful_percent"], 75.0)
        self.assertEqual(len(result["trend"]), 2)
        self.assertEqual(result["trend"][0]["rated_count"], 2)
        self.assertEqual(result["trend"][1]["helpful_count"], 3)

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertEqual(
            cursor.execute.call_args_list[0].args[1],
            (UUID(ADMIN_ID),),
        )
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            ("python-basics",),
        )
        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (14, "python-basics"),
        )

        summary_sql = cursor.execute.call_args_list[1].args[0]
        trend_sql = cursor.execute.call_args_list[2].args[0]
        self.assertIn("cm.role = 'assistant'", summary_sql)
        self.assertIn("generate_series", trend_sql)
        self.assertNotIn("cm.content", summary_sql)
        self.assertNotIn("cs.user_id", summary_sql)

    @patch("services.tutor_feedback_service.load_database_url", return_value="test-db")
    @patch("services.tutor_feedback_service.psycopg.connect")
    def test_rejects_student_before_reading_feedback(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = ("student",)

        with self.assertRaises(PermissionError):
            get_tutor_feedback_summary(
                ADMIN_ID,
                "python-basics",
            )

        self.assertEqual(cursor.execute.call_count, 1)

    @patch("services.tutor_feedback_service.load_database_url", return_value="test-db")
    @patch("services.tutor_feedback_service.psycopg.connect")
    def test_handles_course_with_no_feedback(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            ("admin",),
            (0, 0, 0, 0),
        ]
        cursor.fetchall.return_value = []

        result = get_tutor_feedback_summary(
            ADMIN_ID,
            "python-basics",
        )

        self.assertEqual(result["assistant_answer_count"], 0)
        self.assertEqual(result["rated_answer_count"], 0)
        self.assertIsNone(result["rating_coverage_percent"])
        self.assertIsNone(result["helpful_percent"])
        self.assertEqual(result["trend"], [])

    @patch("services.tutor_feedback_service.load_database_url", return_value="test-db")
    @patch("services.tutor_feedback_service.psycopg.connect")
    def test_uses_default_daily_window(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            ("admin",),
            (0, 0, 0, 0),
        ]
        cursor.fetchall.return_value = []

        get_tutor_feedback_summary(
            ADMIN_ID,
            "python-basics",
        )

        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (DEFAULT_TREND_DAYS, "python-basics"),
        )


if __name__ == "__main__":
    unittest.main()
