"""Tests for the administrator AI Tutor feedback insights page."""

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from ui.tutor_feedback import render_tutor_feedback


class TutorFeedbackInsightsUITests(unittest.TestCase):

    @patch("ui.tutor_feedback.get_tutor_feedback_summary")
    @patch("ui.tutor_feedback.st.error")
    def test_student_is_rejected_before_metrics_query(
        self,
        show_error,
        get_summary,
    ):
        render_tutor_feedback({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "student",
        })

        show_error.assert_called_once()
        get_summary.assert_not_called()

    @patch("ui.tutor_feedback.get_tutor_feedback_summary")
    @patch("ui.tutor_feedback.st.error")
    def test_database_authorization_is_reported(
        self,
        show_error,
        get_summary,
    ):
        get_summary.side_effect = PermissionError("Not an admin")

        render_tutor_feedback({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "admin",
        })

        show_error.assert_called_once_with(
            "An active administrator account is required."
        )

    @patch("ui.tutor_feedback.get_tutor_feedback_summary")
    @patch("ui.tutor_feedback.st.dataframe")
    @patch("ui.tutor_feedback.st.columns")
    def test_admin_sees_aggregate_metrics_and_daily_trend(
        self,
        make_columns,
        show_dataframe,
        get_summary,
    ):
        metric_columns = [MagicMock() for _ in range(4)]
        rate_columns = [MagicMock() for _ in range(2)]
        make_columns.side_effect = [metric_columns, rate_columns]

        get_summary.return_value = {
            "assistant_answer_count": 20,
            "rated_answer_count": 12,
            "helpful_count": 9,
            "not_helpful_count": 3,
            "rating_coverage_percent": 60.0,
            "helpful_percent": 75.0,
            "trend": [
                {
                    "date": date(2026, 11, 11),
                    "rated_count": 3,
                    "helpful_count": 2,
                    "not_helpful_count": 1,
                }
            ],
        }

        render_tutor_feedback({
            "user_id": "11111111-1111-4111-8111-111111111111",
            "role": "admin",
        })

        get_summary.assert_called_once_with(
            user_id="11111111-1111-4111-8111-111111111111",
            course_slug="python-basics",
            days=14,
        )
        metric_columns[0].metric.assert_called_once_with(
            "Assistant answers",
            20,
        )
        metric_columns[3].metric.assert_called_once_with(
            "Not helpful",
            3,
        )
        rate_columns[0].metric.assert_called_once()
        rate_columns[1].metric.assert_called_once()
        show_dataframe.assert_called_once_with(
            [
                {
                    "Date": "11 Nov 2026",
                    "Ratings": 3,
                    "Helpful": 2,
                    "Not helpful": 1,
                }
            ],
            width="stretch",
            height="content",
            hide_index=True,
        )


if __name__ == "__main__":
    unittest.main()
