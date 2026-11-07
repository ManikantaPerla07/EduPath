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

        self.course_slug = "python-basics"

        self.questions = [
            (
                self.item_ids[0],
                self.topic_ids[0],
                "What is Python?",
                [
                    "A. Programming language",
                    "B. Browser",
                    "C. Database",
                    "D. Operating system",
                ],
                "A",
                "Python is a programming language.",
                "easy",
                Decimal("1"),
            ),
            (
                self.item_ids[1],
                self.topic_ids[1],
                "Which keyword defines a function?",
                [
                    "A. class",
                    "B. def",
                    "C. func",
                    "D. function",
                ],
                "B",
                "The def keyword defines a function.",
                "medium",
                Decimal("1"),
            ),
            (
                self.item_ids[2],
                self.topic_ids[2],
                "Which value represents True?",
                [
                    "A. 0",
                    "B. None",
                    "C. True",
                    "D. False",
                ],
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

        # Simulate psycopg connection and cursor context managers.
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
        progress_refresh=None,
    ):
        if progress_refresh is None:
            progress_refresh = MagicMock(return_value=[])

        with patch(
            "services.assessment_submission_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.assessment_submission_service.load_database_url",
            return_value="postgresql://test",
        ), patch(
            "services.assessment_submission_service.refresh_learner_topic_progress",
            new=progress_refresh,
        ):
            return submit_assessment(
                user_id=str(user_id or self.user_id),
                assessment_id=str(assessment_id or self.assessment_id),
                answers={} if answers is None else answers,
            )

    def make_in_progress_session(self):
        return (
            self.assessment_id,
            "in_progress",
            None,
            self.course_slug,
        )

    def make_submitted_session(self):
        return (
            self.assessment_id,
            "submitted",
            Decimal("100.00"),
            self.course_slug,
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

    def test_invalid_assessment_id(self):
        with patch(
            "services.assessment_submission_service.psycopg.connect"
        ) as database:
            with self.assertRaises(ValueError):
                submit_assessment(
                    user_id=str(self.user_id),
                    assessment_id="invalid-id",
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
            [self.make_in_progress_session()],
            self.questions,
        )

        with self.assertRaises(ValueError):
            self.call_service(
                connection,
                answers={str(uuid4()): "A"},
            )

        # No response should be inserted for an unknown question.
        insert_calls = [
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]

        self.assertEqual(len(insert_calls), 0)

    def test_successful_submission_calculates_score(self):
        fetchone_results = [
            self.make_in_progress_session(),
            (uuid4(),),
            (uuid4(),),
            (uuid4(),),
            (self.assessment_id,),
        ]

        connection, cursor = self.make_database_mock(
            fetchone_results,
            self.questions,
        )

        progress_refresh = MagicMock(return_value=[])

        answers = {
            str(self.item_ids[0]): "a",
            str(self.item_ids[1]): "D",
            # Third question is intentionally unanswered.
        }

        result = self.call_service(
            connection,
            answers=answers,
            progress_refresh=progress_refresh,
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

        # Verify that three responses were saved.
        insert_calls = [
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]

        self.assertEqual(len(insert_calls), 3)

        # Verify that unanswered responses are saved as JSON null.
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

        # Verify that progress is refreshed in the same transaction.
        progress_refresh.assert_called_once_with(
            cursor=cursor,
            user_id=str(self.user_id),
            course_slug=self.course_slug,
        )

    def test_repeated_submission_returns_saved_result(self):
        saved_question = (
            self.item_ids[0],
            self.topic_ids[0],
            "What is Python?",
            [
                "A. Programming language",
                "B. Browser",
                "C. Database",
                "D. Operating system",
            ],
            "A",
            "Python is a programming language.",
            "easy",
            Decimal("1"),
            "A",
            True,
            Decimal("1"),
        )

        connection, cursor = self.make_database_mock(
            [self.make_submitted_session()],
            [saved_question],
        )

        progress_refresh = MagicMock(return_value=[])

        result = self.call_service(
            connection,
            answers={str(self.item_ids[0]): "D"},
            progress_refresh=progress_refresh,
        )

        self.assertEqual(result["status"], "submitted")
        self.assertEqual(result["correct_answers"], 1)
        self.assertEqual(
            result["score_percent"],
            Decimal("100.00"),
        )

        # An already submitted assessment must not be graded again.
        self.assertEqual(cursor.execute.call_count, 2)

        insert_calls = [
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]

        self.assertEqual(len(insert_calls), 0)

        # Existing submissions can still refresh historical progress.
        progress_refresh.assert_called_once_with(
            cursor=cursor,
            user_id=str(self.user_id),
            course_slug=self.course_slug,
        )

    def test_abandoned_assessment_cannot_be_submitted(self):
        connection, cursor = self.make_database_mock(
            [
                (
                    self.assessment_id,
                    "abandoned",
                    None,
                    self.course_slug,
                ),
            ]
        )

        progress_refresh = MagicMock(return_value=[])

        with self.assertRaises(ValueError):
            self.call_service(
                connection,
                progress_refresh=progress_refresh,
            )

        self.assertEqual(cursor.execute.call_count, 1)
        progress_refresh.assert_not_called()

    def test_progress_failure_propagates_through_transaction(self):
        fetchone_results = [
            self.make_in_progress_session(),
            (uuid4(),),
            (uuid4(),),
            (uuid4(),),
            (self.assessment_id,),
        ]

        connection, cursor = self.make_database_mock(
            fetchone_results,
            self.questions,
        )

        progress_refresh = MagicMock(
            side_effect=RuntimeError("Progress update failed.")
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Progress update failed",
        ):
            self.call_service(
                connection,
                answers={
                    str(self.item_ids[0]): "A",
                    str(self.item_ids[1]): "B",
                    str(self.item_ids[2]): "C",
                },
                progress_refresh=progress_refresh,
            )

        progress_refresh.assert_called_once()

        # The database transaction context receives the exception.
        # Psycopg will roll back the transaction when it exits.
        connection.__exit__.assert_called_once()

        exit_exception = connection.__exit__.call_args.args[0]

        self.assertIs(exit_exception, RuntimeError)

        # Verify all answer inserts were attempted before progress failed.
        insert_calls = [
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]

        self.assertEqual(len(insert_calls), 3)


if __name__ == "__main__":
    unittest.main()
