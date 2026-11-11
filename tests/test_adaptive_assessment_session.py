import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assessment_session_service import start_assessment


def make_question(topic_slug, difficulty, topic_id, question_id):
    return {
        "question_id": question_id,
        "question_code": f"{topic_slug}-{difficulty}",
        "question_type": "mcq",
        "question_text": f"Test question for {topic_slug} ({difficulty})",
        "options": ["A. First", "B. Second", "C. Third", "D. Fourth"],
        "correct_answer": "A",
        "explanation": "Test explanation.",
        "difficulty": difficulty,
        "topic_id": topic_id,
        "topic_slug": topic_slug,
        "topic_name": topic_slug.title(),
        "sequence_number": 1 if topic_slug == "variables" else 2,
    }


class AdaptiveAssessmentSessionTests(unittest.TestCase):

    def setUp(self):
        self.user_id = uuid4()
        self.course_id = uuid4()
        self.assessment_id = uuid4()

        self.variable_topic_id = uuid4()
        self.loop_topic_id = uuid4()

        self.questions = []

        for topic_slug, topic_id in [
            ("variables", self.variable_topic_id),
            ("loops", self.loop_topic_id),
        ]:
            for difficulty in ("easy", "medium", "hard"):
                self.questions.append(
                    make_question(
                        topic_slug,
                        difficulty,
                        topic_id,
                        uuid4(),
                    )
                )

        self.connection = MagicMock()
        self.cursor = MagicMock()

        self.connection.__enter__.return_value = self.connection
        self.connection.cursor.return_value.__enter__.return_value = (
            self.cursor
        )

        self.cursor.__enter__.return_value = self.cursor

        item_count = 6
        self.item_ids = [uuid4() for _ in range(item_count)]

        self.cursor.fetchone.side_effect = [
            (self.user_id,),
            (self.course_id, True),
            (self.assessment_id,),
            *[(item_id,) for item_id in self.item_ids],
        ]

    def call_service(self, assessment_type, question_count=5):
        with (
            patch(
                "services.assessment_session_service.psycopg.connect",
                return_value=self.connection,
            ),
            patch(
                "services.assessment_session_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.assessment_session_service.fetch_question_records",
                return_value=self.questions,
            ),
        ):
            return start_assessment(
                user_id=str(self.user_id),
                course_slug="python-basics",
                assessment_type=assessment_type,
                question_count=question_count,
            )

    def test_practice_session_uses_adaptive_selection(self):
        self.cursor.fetchall.side_effect = [
            [
                ("variables", "needs_revision", 1),
                ("loops", "developing", 2),
            ],
            [],
        ]

        result = self.call_service("practice", question_count=5)

        self.assertEqual(result["assessment_type"], "practice")
        self.assertEqual(result["total_questions"], 5)
        self.assertEqual(len(result["questions"]), 1)

        selected_topics = {
            question["topic"]["slug"]
            for question in result["questions"]
        }

        self.assertEqual(selected_topics, {"variables"})

        selected_difficulties = {
            question["difficulty"]
            for question in result["questions"]
        }

        self.assertEqual(selected_difficulties, {"easy"})

        self.assertEqual(self.cursor.fetchall.call_count, 2)

        executed_sql = [
            call.args[0].lower()
            for call in self.cursor.execute.call_args_list
        ]

        self.assertTrue(
            any("learner_topic_progress" in sql for sql in executed_sql)
        )

        self.assertTrue(
            any("assessment_responses" in sql for sql in executed_sql)
        )

    def test_revision_session_uses_adaptive_selection(self):
        self.cursor.fetchall.side_effect = [
            [
                ("variables", "needs_revision", 1),
                ("loops", "developing", 2),
            ],
            [],
        ]

        result = self.call_service("revision", question_count=5)

        self.assertEqual(result["assessment_type"], "revision")
        self.assertEqual(result["total_questions"], 5)
        self.assertEqual(len(result["questions"]), 1)
        self.assertEqual(
            {
                question["difficulty"]
                for question in result["questions"]
            },
            {"easy"},
        )

    def test_diagnostic_session_keeps_original_selection_behavior(self):
        result = self.call_service("diagnostic")

        self.assertEqual(result["assessment_type"], "diagnostic")
        self.assertEqual(result["total_questions"], 6)

        # Diagnostic assessments must not load adaptive progress
        # or recent question history.
        self.cursor.fetchall.assert_not_called()

        executed_sql = [
            call.args[0].lower()
            for call in self.cursor.execute.call_args_list
        ]

        self.assertFalse(
            any("learner_topic_progress" in sql for sql in executed_sql)
        )

        self.assertFalse(
            any("assessment_responses" in sql for sql in executed_sql)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
