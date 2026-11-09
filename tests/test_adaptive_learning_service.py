"""Tests for progress-based adaptive teaching guidance."""

import unittest
from unittest.mock import patch

from services.adaptive_learning_service import (
    TEACHING_STRATEGIES,
    build_adaptive_teaching_profile,
    get_learner_teaching_profile,
)


class AdaptiveTeachingProfileTests(unittest.TestCase):

    def setUp(self):
        self.chunks = [
            {
                "chunk_id": "chunk-1",
                "topic_slug": "variables-data-types",
            }
        ]

    def make_progress(self, status):
        return {
            "topic_slug": "variables-data-types",
            "topic_name": "Variables and Data Types",
            "total_attempts": 5,
            "correct_answers": 4,
            "accuracy_percent": 80.0,
            "mastery_score": 80.0,
            "mastery_status": status,
        }

    def test_not_assessed_uses_beginner_guidance(self):
        profile = build_adaptive_teaching_profile(
            self.chunks,
            [self.make_progress("not_assessed")],
        )

        self.assertEqual(profile["level"], "beginner")
        self.assertEqual(profile["mastery_status"], "not_assessed")
        self.assertIn("fundamentals", profile["instruction"])

    def test_needs_revision_uses_step_by_step_guidance(self):
        profile = build_adaptive_teaching_profile(
            self.chunks,
            [self.make_progress("needs_revision")],
        )

        self.assertEqual(profile["level"], "foundational_revision")
        self.assertIn("small steps", profile["instruction"])
        self.assertIn("worked example", profile["instruction"])

    def test_developing_uses_guided_practice(self):
        profile = build_adaptive_teaching_profile(
            self.chunks,
            [self.make_progress("developing")],
        )

        self.assertEqual(profile["level"], "guided_practice")
        self.assertIn("independent practice", profile["instruction"])

    def test_candidate_for_mastery_uses_advanced_guidance(self):
        profile = build_adaptive_teaching_profile(
            self.chunks,
            [self.make_progress("candidate_for_mastery")],
        )

        self.assertEqual(profile["level"], "advanced_application")
        self.assertIn("challenging", profile["instruction"])

    def test_uses_highest_ranked_retrieved_topic(self):
        chunks = [
            {"topic_slug": "variables-data-types"},
            {"topic_slug": "python-functions"},
        ]

        progress = [
            {
                **self.make_progress("candidate_for_mastery"),
                "topic_slug": "python-functions",
            },
            self.make_progress("needs_revision"),
        ]

        profile = build_adaptive_teaching_profile(chunks, progress)

        self.assertEqual(
            profile["topic_slug"],
            "variables-data-types",
        )
        self.assertEqual(
            profile["mastery_status"],
            "needs_revision",
        )

    def test_missing_topic_progress_uses_beginner_default(self):
        profile = build_adaptive_teaching_profile(
            self.chunks,
            [],
        )

        self.assertEqual(profile["mastery_status"], "not_assessed")
        self.assertEqual(profile["level"], "beginner")

    def test_chunks_without_topic_use_beginner_default(self):
        profile = build_adaptive_teaching_profile(
            [{"chunk_id": "chunk-1", "topic_slug": None}],
            [self.make_progress("candidate_for_mastery")],
        )

        self.assertIsNone(profile["topic_slug"])
        self.assertEqual(profile["mastery_status"], "not_assessed")

    def test_rejects_unknown_mastery_status(self):
        with self.assertRaisesRegex(ValueError, "mastery status"):
            build_adaptive_teaching_profile(
                self.chunks,
                [self.make_progress("unknown_status")],
            )

    def test_rejects_invalid_progress_input(self):
        with self.assertRaises(ValueError):
            build_adaptive_teaching_profile(self.chunks, "invalid")

    def test_without_user_id_does_not_query_database(self):
        with patch(
            "services.adaptive_learning_service.fetch_learner_topic_progress"
        ) as fetch:
            profile = get_learner_teaching_profile(
                user_id=None,
                course_slug="python-basics",
                retrieved_chunks=self.chunks,
            )

        self.assertIsNone(profile)
        fetch.assert_not_called()

    def test_fetches_progress_for_the_current_learner(self):
        records = [self.make_progress("developing")]

        with patch(
            "services.adaptive_learning_service.fetch_learner_topic_progress",
            return_value=records,
        ) as fetch:
            profile = get_learner_teaching_profile(
                user_id="123e4567-e89b-12d3-a456-426614174000",
                course_slug="python-basics",
                retrieved_chunks=self.chunks,
            )

        fetch.assert_called_once_with(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            course_slug="python-basics",
        )
        self.assertEqual(profile["mastery_status"], "developing")

    def test_teaching_rules_cover_all_existing_mastery_states(self):
        self.assertEqual(
            set(TEACHING_STRATEGIES),
            {
                "not_assessed",
                "needs_revision",
                "developing",
                "candidate_for_mastery",
            },
        )


if __name__ == "__main__":
    unittest.main()
