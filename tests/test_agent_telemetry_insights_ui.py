"""Tests for the administrator AI Tutor operations page."""

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from ui.agent_telemetry import render_agent_telemetry


class AgentTelemetryUITests(unittest.TestCase):

    @patch("ui.agent_telemetry.get_agent_run_summary")
    @patch("ui.agent_telemetry.st.error")
    def test_student_is_rejected_before_metrics_query(
        self,
        show_error,
        get_summary,
    ):
        render_agent_telemetry({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "student",
        })

        show_error.assert_called_once()
        get_summary.assert_not_called()

    @patch("ui.agent_telemetry.get_agent_run_summary")
    @patch("ui.agent_telemetry.st.error")
    def test_database_authorization_is_reported(
        self,
        show_error,
        get_summary,
    ):
        get_summary.side_effect = PermissionError("Not an admin")

        render_agent_telemetry({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "admin",
        })

        show_error.assert_called_once_with(
            "An active administrator account is required."
        )

    @patch("ui.agent_telemetry.get_agent_run_summary")
    @patch("ui.agent_telemetry.st.dataframe")
    @patch("ui.agent_telemetry.st.columns")
    def test_admin_sees_aggregate_run_metrics_and_daily_trend(
        self,
        make_columns,
        show_dataframe,
        get_summary,
    ):
        status_columns = [MagicMock() for _ in range(5)]
        health_columns = [MagicMock() for _ in range(3)]
        make_columns.side_effect = [status_columns, health_columns]

        get_summary.return_value = {
            "total_runs": 42,
            "completed_runs": 30,
            "failed_runs": 5,
            "running_runs": 4,
            "stopped_runs": 3,
            "average_completed_duration_ms": 1250.0,
            "completed_share_percent": 78.947368,
            "failure_rate_percent": 13.157894,
            "trend": [
                {
                    "date": date(2026, 11, 11),
                    "total_runs": 3,
                    "completed_runs": 2,
                    "failed_runs": 0,
                    "running_runs": 1,
                    "stopped_runs": 0,
                    "average_completed_duration_ms": 1100.0,
                }
            ],
        }

        render_agent_telemetry({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "admin",
        })

        get_summary.assert_called_once_with(
            user_id="11111111-1111-4111-8111-111111111111",
            course_slug="python-basics",
            days=14,
        )
        status_columns[0].metric.assert_called_once_with("Total runs", 42)
        status_columns[2].metric.assert_called_once_with("Failed", 5)
        health_columns[0].metric.assert_called_once()
        health_columns[1].metric.assert_called_once()
        health_columns[2].metric.assert_called_once()
        show_dataframe.assert_called_once_with(
            [
                {
                    "Date": "11 Nov 2026",
                    "Total": 3,
                    "Completed": 2,
                    "Failed": 0,
                    "Running": 1,
                    "Stopped": 0,
                    "Avg. completed duration": "1.10 s",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    def test_duration_formatter_handles_missing_and_short_values(self):
        from ui.agent_telemetry import _format_duration

        self.assertEqual(_format_duration(None), "—")
        self.assertEqual(_format_duration(875), "875 ms")
        self.assertEqual(_format_duration(1250), "1.25 s")


if __name__ == "__main__":
    unittest.main()
