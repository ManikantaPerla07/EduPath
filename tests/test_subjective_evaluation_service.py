"""Tests for the subjective rubric evaluation service."""

import unittest

from services.subjective_evaluation_service import (
    diagnose_misconceptions,
    evaluate_subjective_explanation,
    RUBRIC_CRITERIA,
)


class SubjectiveEvaluationServiceTests(unittest.TestCase):

    def test_rubric_weights_sum_to_one(self):
        total_weight = sum(c["weight"] for c in RUBRIC_CRITERIA.values())
        self.assertAlmostEqual(total_weight, 1.0, places=5)

    def test_diagnose_loop_misconception_off_by_one(self):
        text = "I think range(0, 5) includes 5 because 5 is written inside the parentheses."
        detected = diagnose_misconceptions(text, topic_slug="loops")
        self.assertEqual(len(detected), 1)
        self.assertIn("inclusive", detected[0]["misconception"])

    def test_diagnose_variable_misconception_assignment(self):
        text = "In an if statement, you write if x = 5 to check if x is 5."
        detected = diagnose_misconceptions(text, topic_slug="variables")
        self.assertEqual(len(detected), 1)
        self.assertIn("equality", detected[0]["misconception"])

    def test_evaluate_subjective_valid_explanation(self):
        q = "How does range work in Python?"
        ref = "range(start, stop) generates numbers starting from start up to but excluding stop."
        student = "range generates numbers starting from start and stops right before the stop boundary."
        result = evaluate_subjective_explanation(q, ref, student, topic_slug="loops")

        self.assertGreaterEqual(result["score_percent"], 60.0)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["detected_misconceptions"]), 0)
        self.assertIn("Great explanation", result["feedback"])

    def test_evaluate_subjective_penalizes_misconception(self):
        q = "How does range work in Python?"
        ref = "range(start, stop) generates numbers starting from start up to but excluding stop."
        student = "range(0, 5) includes 5 and loops 6 times."
        result = evaluate_subjective_explanation(q, ref, student, topic_slug="loops")

        self.assertGreater(len(result["detected_misconceptions"]), 0)
        self.assertIn("range(start, stop) stops strictly before stop", result["feedback"])

    def test_rejects_empty_inputs(self):
        with self.assertRaises(ValueError):
            evaluate_subjective_explanation("", "ref", "student")
        with self.assertRaises(ValueError):
            evaluate_subjective_explanation("q", "", "student")
        with self.assertRaises(ValueError):
            evaluate_subjective_explanation("q", "ref", "")


if __name__ == "__main__":
    unittest.main()
