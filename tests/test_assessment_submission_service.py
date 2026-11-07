import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assessment_submission_service import submit_assessment


class AssessmentSubmissionServiceTests(unittest.TestCase):

    def setUp(self):
        self.user_id = uuid4()
        self.assessment_id = uuid4()

        self.item_ids = [
            uuid4(),
            uuid4(),
            uuid4(),
        ]

        self.topic_ids = [
            uuid4(),
            uuid4(),
            uuid4(),
        ]

        self.questions = [
            (
                self.item_ids[0],
                self.topic_ids[0],
                "What is Python?",
                ["A. Programming language", "B. Browser",
                 "C. Database", "D. Operating system"],
                "A",
                "Python is a programming language.",
                "easy",
                Decimal("1"),
            ),
            (
                self.item_ids[1],
                self.topic_ids[1],
                "Which keyword defines a function?",
                ["A. class", "B. def", "C. func", "D. function"],
                "B",
                "The def keyword defines a function.",
                "medium",
                Decimal("1"),
            ),
            (
                self.item_ids[2],
                self.topic_ids[2],
                "Which value represents True?",
                ["A. 0", "B. None", "C. True", "D. False"],
                "C",
                "True is Python's boolean true value.",
                "easy",
                Decimal("1"),
            ),
        ]

    def make_database_mock(
        self,
        fetchone_results,
        question_rows=None,
    ):
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = connection

        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchone.side_effect = fetchone_results
        cursor.fetchall.return_value = question_rows or []

        return connection, cursor

    def call_service(
        self,
        connection,
        answers=None,
        user_id=None,
        assessment_id=None,
    ):
        with patch(
            "services.assessment_submission_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.assessment_submission_service.load_database_url",
            return_value="postgresql://test",
        ):
            return submit_assessment(
                user_id=str(user_id or self.user_id),
                assessment_id=str(assessment_id or self.assessment_id),
                answers={} if answers is None else answers,
            )

    def test_invalid_user_id(self):
        with patch(
            "services.assessment_submission_service.psycopg.connect"
        ) as database:
            with self.assertRaises(ValueError):
                submit_assessment(
                    user_id="invalid-id",
                    assessment_id=str(self.assessment_id),
                    answers={},
                )

        database.assert_not_called()

    def test_answers_must_be_mapping(self):
        with patch(
            "services.assessment_submission_service.psycopg.connect"
        ) as database:
            with self.assertRaises(ValueError):
                submit_assessment(
                    user_id=str(self.user_id),
                    assessment_id=str(self.assessment_id),
                    answers=["A", "B"],
                )

        database.assert_not_called()

    def test_assessment_ownership_is_verified(self):
        connection, cursor = self.make_database_mock([None])

        with self.assertRaises(PermissionError):
            self.call_service(connection)

        self.assertEqual(cursor.execute.call_count, 1)

        executed_sql = cursor.execute.call_args[0][0]

        self.assertIn("user_id = %s", executed_sql)
        self.assertIn("FOR UPDATE", executed_sql)

    def test_unknown_question_id_is_rejected(self):
        connection, cursor = self.make_database_mock(
            [
                (self.assessment_id, "in_progress", None),
            ],
            self.questions,
        )

        with self.assertRaises(ValueError):
            self.call_service(
                connection,
                answers={str(uuid4()): "A"},
            )

        # No response insert should happen for an unknown item.
        insert_calls = [
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]

        self.assertEqual(len(insert_calls), 0)

    def test_successful_submission_calculates_score(self):
        fetchone_results = [
            (self.assessment_id, "in_progress", None),
            (uuid4(),),
            (uuid4(),),
            (uuid4(),),
            (self.assessment_id,),
        ]

        connection, cursor = self.make_database_mock(
            fetchone_results,
            self.questions,
        )

        answers = {
            str(self.item_ids[0]): "a",
            str(self.item_ids[1]): "D",
            # Third question intentionally unanswered.
        }

        result = self.call_service(
            connection,
            answers=answers,
        )

        self.assertEqual(result["status"], "submitted")
        self.assertEqual(result["total_questions"], 3)
        self.assertEqual(result["correct_answers"], 1)
        self.assertEqual(result["incorrect_answers"], 1)
        self.assertEqual(result["unanswered_questions"], 1)

        self.assertEqual(result["total_points"], Decimal("3"))
        self.assertEqual(result["awarded_points"], Decimal("1"))
        self.assertEqual(result["score_percent"], Decimal("33.33"))

        self.assertTrue(result["questions"][0]["is_correct"])
        self.assertFalse(result["questions"][1]["is_correct"])
        self.assertIsNone(
            result["questions"][2]["submitted_answer"]
        )

        self.assertIn(
            "Python is a programming language.",
            result["questions"][0]["explanation"],
        )

        insert_calls = [
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]

        self.assertEqual(len(insert_calls), 3)

        # Verify that an unanswered response is saved as JSON null.
        self.assertIsNone(
            insert_calls[2].args[1][1].obj
        )

        # Verify that the assessment is finalized.
        update_calls = [
            call
            for call in cursor.execute.call_args_list
            if "UPDATE assessment_sessions" in call.args[0]
        ]

        self.assertEqual(len(update_calls), 1)

    def test_repeated_submission_returns_saved_result(self):
        saved_question = (
            self.item_ids[0],
            self.topic_ids[0],
            "What is Python?",
            ["A. Programming language", "B. Browser",
             "C. Database", "D. Operating system"],
            "A",
            "Python is a programming language.",
            "easy",
            Decimal("1"),
            "A",
            True,
            Decimal("1"),
        )

        connection, cursor = self.make_database_mock(
            [
                (
                    self.assessment_id,
                    "submitted",
                    Decimal("100.00"),
                ),
            ],
            [saved_question],
        )

        result = self.call_service(
            connection,
            answers={str(self.item_ids[0]): "D"},
        )

        self.assertEqual(result["status"], "submitted")
        self.assertEqual(result["correct_answers"], 1)
        self.assertEqual(result["score_percent"], Decimal("100.00"))

        # The saved response must be returned without grading again.
        self.assertEqual(cursor.execute.call_count, 2)

    def test_abandoned_assessment_cannot_be_submitted(self):
        connection, cursor = self.make_database_mock(
            [
                (
                    self.assessment_id,
                    "abandoned",
                    None,
                ),
            ]
        )

        with self.assertRaises(ValueError):
            self.call_service(connection)

        self.assertEqual(cursor.execute.call_count, 1)


if __name__ == "__main__":
    unittest.main()
