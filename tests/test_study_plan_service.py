import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.study_plan_service import (
    build_study_plan_items,
    fetch_active_study_plan,
    generate_study_plan,
    order_topics_for_study_plan,
    update_study_plan_item_status,
)


def make_topic(
    topic_id=None,
    slug="variables-data-types",
    name="Variables and Data Types",
    sequence=1,
    status="not_assessed",
    attempts=0,
    correct=0,
    accuracy=Decimal("0.00"),
    prerequisites=None,
    description="Python variables and data types",
):
    return {
        "topic_id": topic_id or uuid4(),
        "topic_slug": slug,
        "topic_name": name,
        "description": description,
        "sequence_number": sequence,
        "total_attempts": attempts,
        "correct_answers": correct,
        "accuracy_percent": accuracy,
        "mastery_score": Decimal("0.00"),
        "mastery_status": status,
        "prerequisite_ids": prerequisites or [],
    }


class StudyPlanOrderingTests(unittest.TestCase):

    def test_weak_topic_is_prioritized_among_available_topics(self):
        developing = make_topic(
            slug="operators",
            name="Operators",
            sequence=1,
            status="developing",
            attempts=2,
            correct=1,
            accuracy=Decimal("50.00"),
        )
        needs_revision = make_topic(
            slug="variables-data-types",
            name="Variables and Data Types",
            sequence=2,
            status="needs_revision",
            attempts=3,
            correct=1,
            accuracy=Decimal("33.33"),
        )

        ordered = order_topics_for_study_plan(
            [developing, needs_revision]
        )

        self.assertEqual(
            ordered[0]["topic_name"],
            "Variables and Data Types",
        )

    def test_prerequisite_is_always_before_dependent_topic(self):
        prerequisite = make_topic(
            slug="variables-data-types",
            name="Variables and Data Types",
            sequence=1,
            status="developing",
        )
        dependent = make_topic(
            slug="operators",
            name="Operators",
            sequence=2,
            status="needs_revision",
            prerequisites=[prerequisite["topic_id"]],
        )

        ordered = order_topics_for_study_plan(
            [dependent, prerequisite]
        )

        self.assertEqual(
            [topic["topic_name"] for topic in ordered],
            ["Variables and Data Types", "Operators"],
        )

    def test_learning_goal_breaks_priority_ties(self):
        variables = make_topic(
            slug="variables-data-types",
            name="Variables and Data Types",
            sequence=1,
            status="developing",
        )
        loops = make_topic(
            slug="loops",
            name="Loops",
            sequence=2,
            status="developing",
            description="For and while loops",
        )

        ordered = order_topics_for_study_plan(
            [variables, loops],
            learning_goal="Improve my understanding of loops",
        )

        self.assertEqual(ordered[0]["topic_name"], "Loops")

    def test_missing_prerequisite_is_rejected(self):
        topic = make_topic(prerequisites=[uuid4()])

        with self.assertRaisesRegex(ValueError, "outside the selected course"):
            order_topics_for_study_plan([topic])

    def test_prerequisite_cycle_is_rejected(self):
        first_id = uuid4()
        second_id = uuid4()
        first = make_topic(
            topic_id=first_id,
            name="First",
            prerequisites=[second_id],
        )
        second = make_topic(
            topic_id=second_id,
            slug="second",
            name="Second",
            sequence=2,
            prerequisites=[first_id],
        )

        with self.assertRaisesRegex(ValueError, "contains a cycle"):
            order_topics_for_study_plan([first, second])

    def test_empty_topic_list_is_rejected(self):
        with self.assertRaises(ValueError):
            order_topics_for_study_plan([])


class StudyPlanBuilderTests(unittest.TestCase):

    START_DATE = date(2026, 11, 8)

    def test_builds_one_activity_for_each_topic(self):
        topics = [
            make_topic(sequence=index, name=f"Topic {index}")
            for index in range(1, 10)
        ]

        result = build_study_plan_items(
            topics=topics,
            start_date=self.START_DATE,
            days=7,
            daily_minutes=45,
        )

        self.assertEqual(len(result["items"]), 9)
        self.assertEqual(result["duration_days"], 7)
        self.assertEqual(result["start_date"], self.START_DATE)
        self.assertEqual(result["end_date"], date(2026, 11, 14))

    def test_daily_activity_time_does_not_exceed_daily_target(self):
        topics = [
            make_topic(sequence=index, name=f"Topic {index}")
            for index in range(1, 10)
        ]

        result = build_study_plan_items(
            topics=topics,
            start_date=self.START_DATE,
            days=7,
            daily_minutes=45,
        )

        minutes_by_day = {}
        for item in result["items"]:
            scheduled = item["scheduled_date"]
            minutes_by_day[scheduled] = (
                minutes_by_day.get(scheduled, 0)
                + item["estimated_minutes"]
            )

        self.assertTrue(
            all(total <= 45 for total in minutes_by_day.values())
        )
        self.assertTrue(
            all(item["estimated_minutes"] >= 10 for item in result["items"])
        )

    def test_small_daily_budget_extends_plan_duration(self):
        topics = [
            make_topic(sequence=index, name=f"Topic {index}")
            for index in range(1, 4)
        ]

        result = build_study_plan_items(
            topics=topics,
            start_date=self.START_DATE,
            days=2,
            daily_minutes=10,
        )

        self.assertEqual(result["duration_days"], 3)
        self.assertEqual(result["end_date"], date(2026, 11, 10))
        self.assertTrue(
            all(item["estimated_minutes"] == 10 for item in result["items"])
        )

    def test_needs_revision_topic_gets_revision_activity(self):
        topic = make_topic(
            status="needs_revision",
            attempts=3,
            correct=1,
            accuracy=Decimal("33.33"),
        )

        result = build_study_plan_items(
            [topic], self.START_DATE, 7, 45
        )

        self.assertEqual(result["items"][0]["activity_type"], "revision")
        self.assertIn("33.3%", result["items"][0]["recommendation_reason"])

    def test_developing_topic_gets_practice_activity(self):
        topic = make_topic(
            status="developing",
            attempts=2,
            correct=1,
            accuracy=Decimal("50.00"),
        )

        result = build_study_plan_items(
            [topic], self.START_DATE, 7, 45
        )

        self.assertEqual(result["items"][0]["activity_type"], "practice")

    def test_not_assessed_topic_gets_learning_activity(self):
        topic = make_topic(status="not_assessed")

        result = build_study_plan_items(
            [topic], self.START_DATE, 7, 45
        )

        self.assertEqual(result["items"][0]["activity_type"], "learn")

    def test_mastery_candidate_gets_spaced_review(self):
        topic = make_topic(
            status="candidate_for_mastery",
            attempts=5,
            correct=4,
            accuracy=Decimal("80.00"),
        )

        result = build_study_plan_items(
            [topic], self.START_DATE, 7, 45
        )

        self.assertEqual(
            result["items"][0]["activity_type"],
            "spaced_review",
        )

    def test_invalid_duration_is_rejected(self):
        topic = make_topic()

        with self.assertRaises(ValueError):
            build_study_plan_items(
                [topic], self.START_DATE, True, 45
            )

    def test_invalid_daily_minutes_are_rejected(self):
        topic = make_topic()

        with self.assertRaises(ValueError):
            build_study_plan_items(
                [topic], self.START_DATE, 7, 9
            )

    def test_invalid_start_date_is_rejected(self):
        topic = make_topic()

        with self.assertRaises(ValueError):
            build_study_plan_items(
                [topic], "not-a-date", 7, 45
            )


class StudyPlanDatabaseTests(unittest.TestCase):

    USER_ID = "123e4567-e89b-12d3-a456-426614174000"
    COURSE_SLUG = "python-basics"
    COURSE_ID = uuid4()
    PLAN_ID = uuid4()

    def setUp(self):
        self.topic_one_id = uuid4()
        self.topic_two_id = uuid4()
        self.item_one_id = uuid4()
        self.item_two_id = uuid4()
        self.created_at = datetime(2026, 11, 8, tzinfo=timezone.utc)

    def _mock_database(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        return connection, cursor

    def _topic_rows(self):
        return [
            (
                self.topic_one_id,
                "variables-data-types",
                "Variables and Data Types",
                "Python variables",
                1,
                3,
                1,
                Decimal("33.33"),
                Decimal("20.00"),
                "needs_revision",
                [],
            ),
            (
                self.topic_two_id,
                "operators",
                "Operators",
                "Python operators",
                2,
                2,
                1,
                Decimal("50.00"),
                Decimal("20.00"),
                "developing",
                [self.topic_one_id],
            ),
        ]

    def test_generate_persists_plan_and_topic_activities(self):
        connection, cursor = self._mock_database()
        cursor.fetchone.side_effect = [
            (
                self.COURSE_ID,
                "Python Programming",
                "Prepare for Python interviews",
                45,
            ),
            (self.PLAN_ID, "active", self.created_at),
            (self.item_one_id,),
            (self.item_two_id,),
        ]
        cursor.fetchall.return_value = self._topic_rows()

        with patch(
            "services.study_plan_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.study_plan_service.load_database_url",
            return_value="postgresql://test",
        ):
            result = generate_study_plan(
                user_id=self.USER_ID,
                course_slug=self.COURSE_SLUG,
                days=7,
                start_date=date(2026, 11, 8),
            )

        self.assertEqual(result["plan_id"], str(self.PLAN_ID))
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["daily_study_minutes"], 45)
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(
            result["items"][0]["activity_type"],
            "revision",
        )
        self.assertEqual(
            result["items"][1]["activity_type"],
            "practice",
        )
        self.assertEqual(cursor.execute.call_count, 6)

        executed_sql = [
            call.args[0].lower()
            for call in cursor.execute.call_args_list
        ]
        self.assertIn("c.is_published = true", executed_sql[0])
        self.assertIn("FOR UPDATE OF u, lp, c", executed_sql[0])
        self.assertTrue(
            any("update study_plans" in sql for sql in executed_sql)
        )
        self.assertTrue(
            any("insert into study_plans" in sql for sql in executed_sql)
        )
        self.assertEqual(
            sum("insert into study_plan_items" in sql for sql in executed_sql),
            2,
        )

    def test_generate_rejects_unconfirmed_or_inactive_learner(self):
        connection, cursor = self._mock_database()
        cursor.fetchone.return_value = None

        with patch(
            "services.study_plan_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.study_plan_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(PermissionError):
                generate_study_plan(
                    self.USER_ID,
                    self.COURSE_SLUG,
                )

        self.assertEqual(cursor.execute.call_count, 1)

    def test_generate_rejects_course_without_topics(self):
        connection, cursor = self._mock_database()
        cursor.fetchone.return_value = (
            self.COURSE_ID,
            "Python Programming",
            None,
            45,
        )
        cursor.fetchall.return_value = []

        with patch(
            "services.study_plan_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.study_plan_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaisesRegex(ValueError, "no learning topics"):
                generate_study_plan(
                    self.USER_ID,
                    self.COURSE_SLUG,
                )

        # No existing plan is archived when topic selection fails.
        self.assertFalse(
            any(
                "update study_plans" in call.args[0].lower()
                for call in cursor.execute.call_args_list
            )
        )

    def test_generate_rejects_invalid_user_id_before_database_access(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                generate_study_plan("invalid-id", self.COURSE_SLUG)

        connect.assert_not_called()

    def test_generate_rejects_empty_course_slug_before_database_access(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                generate_study_plan(self.USER_ID, " ")

        connect.assert_not_called()

    def test_fetch_returns_active_plan_and_items(self):
        connection, cursor = self._mock_database()
        cursor.fetchone.return_value = (
            self.PLAN_ID,
            "Python Programming — Personalized Study Plan",
            "active",
            date(2026, 11, 8),
            date(2026, 11, 14),
            self.created_at,
            self.COURSE_SLUG,
        )
        cursor.fetchall.return_value = [
            (
                self.item_one_id,
                self.topic_one_id,
                "variables-data-types",
                "Variables and Data Types",
                "revision",
                date(2026, 11, 8),
                45,
                "pending",
                "Review this topic.",
                1,
            )
        ]

        with patch(
            "services.study_plan_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.study_plan_service.load_database_url",
            return_value="postgresql://test",
        ):
            result = fetch_active_study_plan(
                self.USER_ID,
                self.COURSE_SLUG,
            )

        self.assertEqual(result["plan_id"], str(self.PLAN_ID))
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(
            result["items"][0]["activity_type"],
            "revision",
        )
        self.assertEqual(cursor.execute.call_count, 2)
        self.assertIn(
            "c.is_published = TRUE",
            cursor.execute.call_args_list[0].args[0],
        )

    def test_fetch_returns_none_when_no_active_plan_exists(self):
        connection, cursor = self._mock_database()
        cursor.fetchone.return_value = None

        with patch(
            "services.study_plan_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.study_plan_service.load_database_url",
            return_value="postgresql://test",
        ):
            result = fetch_active_study_plan(
                self.USER_ID,
                self.COURSE_SLUG,
            )

        self.assertIsNone(result)
        cursor.execute.assert_called_once()

    def test_fetch_rejects_invalid_user_id(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                fetch_active_study_plan("bad-id", self.COURSE_SLUG)

        connect.assert_not_called()

    def test_fetch_rejects_empty_course_slug(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                fetch_active_study_plan(self.USER_ID, " ")

        connect.assert_not_called()


class StudyPlanActivityStatusTests(unittest.TestCase):

    USER_ID = "123e4567-e89b-12d3-a456-426614174000"
    ITEM_ID = "223e4567-e89b-12d3-a456-426614174000"
    PLAN_ID = uuid4()

    def _mock_database(self, fetchone_results):
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.side_effect = fetchone_results
        return connection, cursor

    def _call(self, cursor, status="completed"):
        connection = cursor._test_connection
        with patch(
            "services.study_plan_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.study_plan_service.load_database_url",
            return_value="postgresql://test",
        ):
            return update_study_plan_item_status(
                self.USER_ID,
                self.ITEM_ID,
                status,
            )

    def test_mark_activity_completed_updates_plan_counts(self):
        connection, cursor = self._mock_database([
            (self.PLAN_ID, "pending"),
            (uuid4(),),
            (9, 1),
            ("active",),
        ])
        cursor._test_connection = connection

        result = self._call(cursor)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["plan_status"], "active")
        self.assertEqual(result["total_activities"], 9)
        self.assertEqual(result["completed_activities"], 1)
        self.assertEqual(result["completion_percent"], 11.11)
        self.assertEqual(cursor.execute.call_count, 4)

    def test_completing_last_activity_completes_plan(self):
        connection, cursor = self._mock_database([
            (self.PLAN_ID, "pending"),
            (uuid4(),),
            (9, 9),
            ("completed",),
        ])
        cursor._test_connection = connection

        result = self._call(cursor)

        self.assertEqual(result["plan_status"], "completed")
        self.assertEqual(result["completion_percent"], 100.0)

    def test_reopening_activity_reactivates_completed_plan(self):
        connection, cursor = self._mock_database([
            (self.PLAN_ID, "completed"),
            (uuid4(),),
            (9, 8),
            ("active",),
        ])
        cursor._test_connection = connection

        result = self._call(cursor, status="pending")

        self.assertEqual(result["previous_status"], "completed")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["plan_status"], "active")
        self.assertEqual(result["completion_percent"], 88.89)

    def test_activity_must_belong_to_active_or_completed_learner_plan(self):
        connection, cursor = self._mock_database([None])
        cursor._test_connection = connection

        with self.assertRaises(PermissionError):
            self._call(cursor)

        self.assertEqual(cursor.execute.call_count, 1)
        self.assertIn(
            "c.is_published = TRUE",
            cursor.execute.call_args.args[0],
        )
        self.assertIn(
            "FOR UPDATE OF pi, p, u, c",
            cursor.execute.call_args.args[0],
        )

    def test_invalid_user_id_is_rejected_before_database_access(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                update_study_plan_item_status(
                    "invalid-user",
                    self.ITEM_ID,
                    "completed",
                )
        connect.assert_not_called()

    def test_invalid_item_id_is_rejected_before_database_access(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                update_study_plan_item_status(
                    self.USER_ID,
                    "invalid-item",
                    "completed",
                )
        connect.assert_not_called()

    def test_invalid_status_is_rejected_before_database_access(self):
        with patch(
            "services.study_plan_service.psycopg.connect"
        ) as connect:
            with self.assertRaises(ValueError):
                update_study_plan_item_status(
                    self.USER_ID,
                    self.ITEM_ID,
                    "done",
                )
        connect.assert_not_called()

    def test_progress_percent_uses_completed_count(self):
        connection, cursor = self._mock_database([
            (self.PLAN_ID, "pending"),
            (uuid4(),),
            (9, 4),
            ("active",),
        ])
        cursor._test_connection = connection

        result = self._call(cursor)

        self.assertEqual(result["completion_percent"], 44.44)




if __name__ == "__main__":
    unittest.main()
