"""Regression tests for learner access to published course content."""

import unittest
from unittest.mock import MagicMock, patch

from services.assessment_service import fetch_question_records


class PublishedCourseQuestionAccessTests(unittest.TestCase):

    def test_question_queries_require_a_published_course(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = cursor
        connection.cursor.return_value = cursor_context

        with (
            patch(
                "services.assessment_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.assessment_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            records = fetch_question_records("python-basics")

        self.assertEqual(records, [])
        sql, parameters = cursor.execute.call_args.args
        self.assertIn("c.is_published = TRUE", sql)
        self.assertEqual(parameters, ["python-basics"])


if __name__ == "__main__":
    unittest.main()
