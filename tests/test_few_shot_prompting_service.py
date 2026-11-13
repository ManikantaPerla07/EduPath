"""Tests for the few-shot personalization and exemplar service."""

import unittest

from services.few_shot_prompting_service import (
    FEW_SHOT_EXEMPLARS,
    format_few_shot_prompt_section,
    get_few_shot_exemplars,
)


class FewShotPromptingServiceTests(unittest.TestCase):

    def test_exemplars_contain_all_three_levels(self):
        self.assertIn("beginner", FEW_SHOT_EXEMPLARS)
        self.assertIn("intermediate", FEW_SHOT_EXEMPLARS)
        self.assertIn("advanced", FEW_SHOT_EXEMPLARS)

    def test_each_exemplar_has_required_keys(self):
        required_keys = {
            "topic",
            "concept",
            "level",
            "common_mistake",
            "sample_question",
            "demonstration_response",
        }
        for level, exemplars in FEW_SHOT_EXEMPLARS.items():
            self.assertGreater(len(exemplars), 0, f"Level {level} has no exemplars.")
            for ex in exemplars:
                self.assertTrue(
                    required_keys.issubset(ex.keys()),
                    f"Exemplar missing required keys in {level}: {ex.keys()}",
                )

    def test_get_few_shot_exemplars_normalization(self):
        beginner_ex = get_few_shot_exemplars("beginner")
        self.assertEqual(beginner_ex[0]["level"], "beginner")

        # Status alias mapping
        revision_ex = get_few_shot_exemplars("needs_revision")
        self.assertEqual(revision_ex[0]["level"], "beginner")

        developing_ex = get_few_shot_exemplars("developing")
        self.assertEqual(developing_ex[0]["level"], "intermediate")

        mastery_ex = get_few_shot_exemplars("candidate_for_mastery")
        self.assertEqual(mastery_ex[0]["level"], "advanced")

    def test_format_few_shot_prompt_section(self):
        section = format_few_shot_prompt_section("beginner")
        self.assertIn("FEW-SHOT TEACHING DEMONSTRATIONS FOR BEGINNER LEVEL", section)
        self.assertIn("Learner Misconception Addressed", section)
        self.assertIn("Tutor Response Style", section)

    def test_three_levels_have_distinct_pedagogical_traits(self):
        beg_sec = format_few_shot_prompt_section("beginner")
        int_sec = format_few_shot_prompt_section("intermediate")
        adv_sec = format_few_shot_prompt_section("advanced")

        # Beginner should have analogies/friendly terms
        self.assertTrue("Analogy" in beg_sec or "Hint" in beg_sec)

        # Intermediate should have execution/pitfalls
        self.assertTrue("Pitfall" in int_sec or "Execution" in int_sec or "Exercise" in int_sec)

        # Advanced should mention deep concepts like Iterator/Protocol/Complexity
        self.assertTrue("Iterator Protocol" in adv_sec or "Challenge" in adv_sec)


if __name__ == "__main__":
    unittest.main()
