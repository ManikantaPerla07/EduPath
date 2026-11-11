"""Tests for administrator-only aggregate AI Tutor run insights."""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.agent_telemetry_insights_service import (
    DEFAULT_TREND_DAYS,
    get_agent_run_summary,
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


class AgentTelemetryInsightsValidationTests(unittest.TestCase):

    def test_rejects_invalid_admin_id(self):
        with self.assertRaises(ValueError):
            get_agent_run_summary("not-a-uuid", "python-basics")

    def test_rejects_empty_course_slug(self):
        with self.assertRaises(ValueError):
            get_agent_run_summary(ADMIN_ID, " ")

    def test_rejects_invalid_trend_window(self):
        for days in (0, -1, 91, True, 1.5):
            with self.subTest(days=days):
                with self.assertRaises(ValueError):
                    get_agent_run_summary(
                        ADMIN_ID,
                        "python-basics",
                        days=days,
                    )


class AgentTelemetryInsightsDatabaseTests(unittest.TestCase):

    @patch(
        "services.agent_telemetry_insights_service.load_database_url",
        return_value="test-db",
    )
    @patch("services.agent_telemetry_insights_service.psycopg.connect")
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
            (42, 30, 5, 2, 2, 3, 1250.0),
        ]
        cursor.fetchall.return_value = [
            (today - timedelta(days=1), 2, 1, 1, 0, 0, 0, 950.0),
            (today, 3, 2, 0, 1, 0, 0, 1100.0),
        ]

        result = get_agent_run_summary(
            ADMIN_ID,
            "python-basics",
            days=14,
        )

        self.assertEqual(result["total_runs"], 42)
        self.assertEqual(result["completed_runs"], 30)
        self.assertEqual(result["failed_runs"], 5)
        self.assertEqual(result["running_runs"], 2)
        self.assertEqual(result["stale_runs"], 2)
        self.assertEqual(result["stopped_runs"], 3)
        self.assertEqual(
            result["average_completed_duration_ms"],
            1250.0,
        )
        self.assertAlmostEqual(
            result["completed_share_percent"],
            (30 / 38) * 100,
        )
        self.assertAlmostEqual(
            result["failure_rate_percent"],
            (5 / 38) * 100,
        )
        self.assertEqual(len(result["trend"]), 2)
        self.assertEqual(result["trend"][0]["total_runs"], 2)
        self.assertEqual(result["trend"][0]["stale_runs"], 0)
        self.assertEqual(result["trend"][1]["completed_runs"], 2)
        self.assertEqual(result["trend"][1]["running_runs"], 1)

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertEqual(
            cursor.execute.call_args_list[0].args[1],
            (UUID(ADMIN_ID),),
        )
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            ("python-basics", 14),
        )
        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (14, "python-basics"),
        )

        summary_sql = cursor.execute.call_args_list[1].args[0]
        trend_sql = cursor.execute.call_args_list[2].args[0]
        self.assertIn("ar.status = 'completed'", summary_sql)
        self.assertIn("INTERVAL '15 minutes'", summary_sql)
        self.assertIn("INTERVAL '15 minutes'", trend_sql)
        self.assertIn("generate_series", trend_sql)
        for private_field in (
            "ar.user_id",
            "ar.node_sequence",
            "ar.error_code",
            "cm.content",
        ):
            self.assertNotIn(private_field, summary_sql)
            self.assertNotIn(private_field, trend_sql)

    @patch(
        "services.agent_telemetry_insights_service.load_database_url",
        return_value="test-db",
    )
    @patch("services.agent_telemetry_insights_service.psycopg.connect")
    def test_rejects_student_before_reading_run_metrics(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.return_value = ("student",)

        with self.assertRaises(PermissionError):
            get_agent_run_summary(
                ADMIN_ID,
                "python-basics",
            )

        self.assertEqual(cursor.execute.call_count, 1)

    @patch(
        "services.agent_telemetry_insights_service.load_database_url",
        return_value="test-db",
    )
    @patch("services.agent_telemetry_insights_service.psycopg.connect")
    def test_handles_course_with_no_runs(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            ("admin",),
            (0, 0, 0, 0, 0, 0, None),
        ]
        cursor.fetchall.return_value = []

        result = get_agent_run_summary(
            ADMIN_ID,
            "python-basics",
        )

        self.assertEqual(result["total_runs"], 0)
        self.assertEqual(result["completed_runs"], 0)
        self.assertIsNone(result["average_completed_duration_ms"])
        self.assertIsNone(result["completed_share_percent"])
        self.assertIsNone(result["failure_rate_percent"])
        self.assertEqual(result["trend"], [])

    @patch(
        "services.agent_telemetry_insights_service.load_database_url",
        return_value="test-db",
    )
    @patch("services.agent_telemetry_insights_service.psycopg.connect")
    def test_uses_default_daily_window(
        self,
        mock_connect,
        mock_database_url,
    ):
        connection, cursor = make_database()
        mock_connect.return_value = connection
        cursor.fetchone.side_effect = [
            ("admin",),
            (0, 0, 0, 0, 0, 0, None),
        ]
        cursor.fetchall.return_value = []

        get_agent_run_summary(
            ADMIN_ID,
            "python-basics",
        )

        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (DEFAULT_TREND_DAYS, "python-basics"),
        )


if __name__ == "__main__":
    unittest.main()
