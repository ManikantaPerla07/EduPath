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

    def test_scenario_1_beginner_off_by_one_range_misconception(self):
        """Scenario 1: Beginner with an off-by-one range misconception."""
        profile = build_adaptive_teaching_profile(
            retrieved_chunks=self.chunks,
            topic_progress=[self.make_progress("not_assessed")],
            learner_profile={"proficiency_level": "beginner", "explanation_style": "step_by_step"},
            misconceptions=[{
                "misconception_code": "off_by_one_range",
                "short_description": "Believing range(1, 5) counts up to and includes 5",
                "corrective_explanation": "In Python range(start, stop) is stop-exclusive.",
            }],
        )
        self.assertEqual(profile["level"], "beginner")
        self.assertIn("FEW-SHOT TEACHING DEMONSTRATIONS FOR BEGINNER LEVEL", profile["few_shot_section"])
        self.assertIn("off_by_one_range", profile["few_shot_section"])

    def test_scenario_2_intermediate_mutating_list_during_iteration(self):
        """Scenario 2: Intermediate learner who mutates a list during iteration."""
        profile = build_adaptive_teaching_profile(
            retrieved_chunks=self.chunks,
            topic_progress=[self.make_progress("developing")],
            learner_profile={"proficiency_level": "intermediate", "explanation_style": "example_first"},
            misconceptions=[{
                "misconception_code": "list_mutation_during_iteration",
                "short_description": "Modifying list length during for-in iteration",
                "corrective_explanation": "Never mutate a list while iterating; iterate over a copy or use comprehension.",
            }],
        )
        self.assertEqual(profile["level"], "guided_practice")
        self.assertIn("FEW-SHOT TEACHING DEMONSTRATIONS FOR INTERMEDIATE LEVEL", profile["few_shot_section"])
        self.assertIn("list_mutation_during_iteration", profile["few_shot_section"])

    def test_scenario_3_advanced_mutable_default_argument(self):
        """Scenario 3: Advanced learner with a mutable default argument misconception."""
        profile = build_adaptive_teaching_profile(
            retrieved_chunks=self.chunks,
            topic_progress=[self.make_progress("candidate_for_mastery")],
            learner_profile={"proficiency_level": "advanced", "explanation_style": "simple"},
            misconceptions=[{
                "misconception_code": "mutable_default_argument",
                "short_description": "Default arguments evaluated once at function definition",
                "corrective_explanation": "Use def f(val=None): if val is None: val = [] to prevent shared mutable state.",
            }],
        )
        self.assertEqual(profile["level"], "advanced_application")
        self.assertIn("FEW-SHOT TEACHING DEMONSTRATIONS FOR ADVANCED LEVEL", profile["few_shot_section"])
        self.assertIn("mutable_default_argument", profile["few_shot_section"])

    def test_scenario_4_learner_without_prior_progress(self):
        """Scenario 4: Learner without prior progress defaults gracefully to declared proficiency baseline."""
        profile = build_adaptive_teaching_profile(
            retrieved_chunks=self.chunks,
            topic_progress=[],
            learner_profile=None,
            misconceptions=[],
        )
        self.assertEqual(profile["level"], "beginner")
        self.assertEqual(profile["mastery_status"], "not_assessed")
        self.assertIn("FEW-SHOT TEACHING DEMONSTRATIONS FOR BEGINNER LEVEL", profile["few_shot_section"])

    def test_scenario_5_demonstrated_topic_mastery_overrides_declared_proficiency(self):
        """Scenario 5: Demonstrated topic mastery takes priority over self-declared proficiency."""
        profile = build_adaptive_teaching_profile(
            retrieved_chunks=self.chunks,
            topic_progress=[self.make_progress("needs_revision")],
            learner_profile={"proficiency_level": "advanced"},  # Learner self-declared advanced
            misconceptions=[],
        )
        # Topic mastery 'needs_revision' takes priority -> maps to foundational_revision
        self.assertEqual(profile["level"], "foundational_revision")
        self.assertEqual(profile["mastery_status"], "needs_revision")
        self.assertEqual(profile["declared_proficiency"], "advanced")
        self.assertIn("FEW-SHOT TEACHING DEMONSTRATIONS FOR BEGINNER LEVEL", profile["few_shot_section"])

    def test_distinct_explanation_styles_at_all_three_levels(self):
        """Verify that the same question produces meaningfully different explanation styles across levels."""
        p_beg = build_adaptive_teaching_profile(self.chunks, [self.make_progress("needs_revision")])
        p_int = build_adaptive_teaching_profile(self.chunks, [self.make_progress("developing")])
        p_adv = build_adaptive_teaching_profile(self.chunks, [self.make_progress("candidate_for_mastery")])

        self.assertNotEqual(p_beg["instruction"], p_int["instruction"])
        self.assertNotEqual(p_int["instruction"], p_adv["instruction"])
        self.assertNotEqual(p_beg["level"], p_int["level"])
        self.assertNotEqual(p_int["level"], p_adv["level"])


if __name__ == "__main__":
    unittest.main()
