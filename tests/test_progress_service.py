
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from services.progress_service import (
    calculate_topic_progress,
    refresh_learner_topic_progress,
    fetch_learner_topic_progress,
)


class ProgressCalculationTests(unittest.TestCase):

    def test_zero_attempts(self):
        result = calculate_topic_progress(0, 0)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("0.00"),
        )
        self.assertEqual(
            result["mastery_score"],
            Decimal("0.00"),
        )
        self.assertEqual(
            result["mastery_status"],
            "not_assessed",
        )

    def test_one_correct_attempt_has_limited_mastery(self):
        result = calculate_topic_progress(1, 1)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("100.00"),
        )
        self.assertEqual(
            result["mastery_score"],
            Decimal("20.00"),
        )
        self.assertEqual(
            result["mastery_status"],
            "developing",
        )

    def test_two_attempts_are_not_enough_for_mastery(self):
        result = calculate_topic_progress(2, 2)

        self.assertEqual(
            result["mastery_score"],
            Decimal("40.00"),
        )
        self.assertEqual(
            result["mastery_status"],
            "developing",
        )

    def test_low_accuracy_requires_revision(self):
        result = calculate_topic_progress(3, 1)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("33.33"),
        )
        self.assertEqual(
            result["mastery_status"],
            "needs_revision",
        )

    def test_exactly_fifty_percent_is_developing(self):
        result = calculate_topic_progress(4, 2)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("50.00"),
        )
        self.assertEqual(
            result["mastery_status"],
            "developing",
        )

    def test_eighty_percent_with_five_attempts_is_candidate_for_mastery(self):
        result = calculate_topic_progress(5, 4)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("80.00"),
        )
        self.assertEqual(
            result["mastery_score"],
            Decimal("80.00"),
        )
        self.assertEqual(
            result["mastery_status"],
            "candidate_for_mastery",
        )

    def test_below_eighty_percent_is_not_candidate_for_mastery(self):
        result = calculate_topic_progress(5, 3)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("60.00"),
        )
        self.assertEqual(
            result["mastery_status"],
            "developing",
        )

    def test_mastery_score_is_capped_at_accuracy(self):
        result = calculate_topic_progress(10, 9)

        self.assertEqual(
            result["accuracy_percent"],
            Decimal("90.00"),
        )
        self.assertEqual(
            result["mastery_score"],
            Decimal("90.00"),
        )

    def test_negative_attempts_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_topic_progress(-1, 0)

    def test_boolean_attempts_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_topic_progress(True, 1)

    def test_correct_answers_cannot_exceed_attempts(self):
        with self.assertRaises(ValueError):
            calculate_topic_progress(2, 3)

    def test_negative_correct_answers_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_topic_progress(3, -1)

    def test_boolean_correct_answers_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_topic_progress(2, True)


class ProgressDatabaseTests(unittest.TestCase):

    def setUp(self):
        self.user_id = uuid4()

        self.topic_ids = [
            uuid4(),
            uuid4(),
            uuid4(),
        ]

        self.attempt_date = datetime.now(timezone.utc)

    def make_cursor(self, topic_rows):
        cursor = MagicMock()
        cursor.fetchall.return_value = topic_rows
        return cursor

    def test_refresh_updates_every_course_topic(self):
        topic_rows = [
            (
                self.topic_ids[0],
                3,
                1,
                self.attempt_date,
            ),
            (
                self.topic_ids[1],
                0,
                0,
                None,
            ),
            (
                self.topic_ids[2],
                5,
                4,
                self.attempt_date,
            ),
        ]

        cursor = self.make_cursor(topic_rows)

        results = refresh_learner_topic_progress(
            cursor=cursor,
            user_id=str(self.user_id),
            course_slug="python-basics",
        )

        self.assertEqual(len(results), 3)

        # Topic 1: three attempts and one correct answer.
        self.assertEqual(
            results[0]["total_attempts"],
            3,
        )
        self.assertEqual(
            results[0]["correct_answers"],
            1,
        )
        self.assertEqual(
            results[0]["mastery_status"],
            "needs_revision",
        )

        # Topic 2: no submitted attempts.
        self.assertEqual(
            results[1]["total_attempts"],
            0,
        )
        self.assertEqual(
            results[1]["mastery_status"],
            "not_assessed",
        )

        # Topic 3: four correct out of five attempts.
        self.assertEqual(
            results[2]["mastery_status"],
            "candidate_for_mastery",
        )

        # One aggregate query and three progress upserts.
        self.assertEqual(
            cursor.execute.call_count,
            4,
        )

        for call in cursor.execute.call_args_list[1:]:
            self.assertIn(
                "ON CONFLICT (user_id, topic_id)",
                call.args[0],
            )

    def test_refresh_uses_aggregate_results_for_upsert(self):
        topic_rows = [
            (
                self.topic_ids[0],
                5,
                4,
                self.attempt_date,
            ),
        ]

        cursor = self.make_cursor(topic_rows)

        refresh_learner_topic_progress(
            cursor=cursor,
            user_id=str(self.user_id),
            course_slug="python-basics",
        )

        insert_parameters = (
            cursor.execute.call_args_list[1].args[1]
        )

        self.assertEqual(
            insert_parameters[0],
            self.user_id,
        )
        self.assertEqual(
            insert_parameters[1],
            self.topic_ids[0],
        )
        self.assertEqual(
            insert_parameters[2],
            5,
        )
        self.assertEqual(
            insert_parameters[3],
            4,
        )
        self.assertEqual(
            insert_parameters[4],
            Decimal("80.00"),
        )
        self.assertEqual(
            insert_parameters[5],
            Decimal("80.00"),
        )
        self.assertEqual(
            insert_parameters[6],
            "candidate_for_mastery",
        )

    def test_refresh_rejects_course_without_topics(self):
        cursor = self.make_cursor([])

        with self.assertRaises(ValueError):
            refresh_learner_topic_progress(
                cursor=cursor,
                user_id=str(self.user_id),
                course_slug="python-basics",
            )

        self.assertEqual(
            cursor.execute.call_count,
            1,
        )

    def test_refresh_rejects_invalid_user_id(self):
        cursor = self.make_cursor([])

        with self.assertRaises(ValueError):
            refresh_learner_topic_progress(
                cursor=cursor,
                user_id="invalid-id",
                course_slug="python-basics",
            )

        cursor.execute.assert_not_called()

    def test_refresh_rejects_empty_course_slug(self):
        cursor = self.make_cursor([])

        with self.assertRaises(ValueError):
            refresh_learner_topic_progress(
                cursor=cursor,
                user_id=str(self.user_id),
                course_slug=" ",
            )

        cursor.execute.assert_not_called()


class ProgressRetrievalTests(unittest.TestCase):

    USER_ID = "123e4567-e89b-12d3-a456-426614174000"
    COURSE_SLUG = "python-basics"

    def _mock_database(self, rows):
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = rows

        return connection, cursor

    def test_fetch_returns_topic_progress_rows(self):
        expected_rows = [
            {
                "topic_id": "topic-001",
                "topic_slug": "variables-data-types",
                "topic_name": "Variables and Data Types",
                "sequence_order": 1,
                "total_attempts": 3,
                "correct_answers": 1,
                "accuracy_percent": 33.33,
                "hints_used": 0,
                "mastery_score": 20.00,
                "mastery_status": "needs_revision",
                "last_attempted_at": None,
            }
        ]

        connection, cursor = self._mock_database(expected_rows)

        with patch(
            "services.progress_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.progress_service.load_database_url",
            return_value="postgresql://test",
        ):
            result = fetch_learner_topic_progress(
                self.USER_ID,
                self.COURSE_SLUG,
            )

        self.assertEqual(result, expected_rows)
        cursor.fetchall.assert_called_once()

    def test_fetch_uses_correct_database_parameters(self):
        connection, cursor = self._mock_database([])

        with patch(
            "services.progress_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.progress_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(ValueError):
                fetch_learner_topic_progress(
                    self.USER_ID,
                    self.COURSE_SLUG,
                )

        query_parameters = cursor.execute.call_args.args[1]

        self.assertEqual(
            query_parameters,
            (self.COURSE_SLUG, UUID(self.USER_ID)),
        )

    def test_fetch_rejects_invalid_user_id(self):
        with patch(
            "services.progress_service.psycopg.connect"
        ) as mock_connect:
            with self.assertRaises(ValueError):
                fetch_learner_topic_progress(
                    "invalid-user-id",
                    self.COURSE_SLUG,
                )

        mock_connect.assert_not_called()

    def test_fetch_rejects_empty_course_slug(self):
        with patch(
            "services.progress_service.psycopg.connect"
        ) as mock_connect:
            with self.assertRaises(ValueError):
                fetch_learner_topic_progress(
                    self.USER_ID,
                    "",
                )

        mock_connect.assert_not_called()

    def test_fetch_rejects_missing_learner_or_course(self):
        connection, cursor = self._mock_database([])

        with patch(
            "services.progress_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.progress_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(ValueError):
                fetch_learner_topic_progress(
                    self.USER_ID,
                    self.COURSE_SLUG,
                )

        cursor.fetchall.assert_called_once()

    def test_fetch_query_includes_topics_without_saved_progress(self):
        connection, cursor = self._mock_database([])

        with patch(
            "services.progress_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.progress_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(ValueError):
                fetch_learner_topic_progress(
                    self.USER_ID,
                    self.COURSE_SLUG,
                )

        sql = cursor.execute.call_args.args[0].lower()

        self.assertIn(
            "left join learner_topic_progress",
            sql,
        )
        self.assertIn(
            "coalesce",
            sql,
        )


if __name__ == "__main__":
    unittest.main()
