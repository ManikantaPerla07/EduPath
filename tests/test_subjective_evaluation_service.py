"""Tests for the subjective rubric evaluation service."""

import unittest
from unittest.mock import patch

from services.subjective_evaluation_service import (
    diagnose_misconceptions,
    evaluate_subjective_explanation,
    RUBRIC_CRITERIA,
)


class SubjectiveEvaluationServiceTests(unittest.TestCase):

    USER_ID = "123e4567-e89b-12d3-a456-426614174000"

    def setUp(self):
        self.profile_patcher = patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": True},
        )
        self.profile_patcher.start()

    def tearDown(self):
        self.profile_patcher.stop()

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

    @patch("services.answer_generation_service._generate_with_langchain_fallback")
    def test_gemini_evaluator_valid_response(self, mock_gen):
        mock_gen.return_value = (
            '{"conceptual_accuracy": 90.0, "reasoning_and_logic": 85.0, "edge_cases_and_gotchas": 80.0, "clarity_of_expression": 95.0, "detected_misconceptions": [], "feedback": "Excellent reasoning!"}',
            "gemini-3.8-flash"
        )
        q = "Explain Python for loop"
        ref = "Loops iterate over an iterable sequence."
        student = "A for loop steps through items produced by an iterable sequence one by one."
        result = evaluate_subjective_explanation(
            q, ref, student, use_ai=True, user_id=self.USER_ID
        )

        self.assertEqual(result["evaluator_type"], "gemini")
        self.assertIn("gemini-3.8-flash", result["evaluator_label"])
        # 0.4*90 + 0.3*85 + 0.15*80 + 0.15*95 = 36 + 25.5 + 12 + 14.25 = 87.75 -> 87.8
        self.assertAlmostEqual(result["score_percent"], 87.8, places=1)
        self.assertTrue(result["passed"])
        self.assertEqual(result["detected_misconceptions"], [])
        self.assertEqual(result["feedback"], "Excellent reasoning!")

    @patch("services.answer_generation_service._generate_with_langchain_fallback")
    def test_gemini_evaluator_clamps_out_of_bound_scores(self, mock_gen):
        mock_gen.return_value = (
            '{"conceptual_accuracy": 150.0, "reasoning_and_logic": -20.0, "edge_cases_and_gotchas": 50.0, "clarity_of_expression": 50.0, "detected_misconceptions": ["off_by_one_range"], "feedback": "Good attempt"}',
            "gemini-3.8-flash"
        )
        result = evaluate_subjective_explanation(
            "q", "ref", "student", use_ai=True, user_id=self.USER_ID
        )
        breakdown = result["rubric_breakdown"]
        self.assertEqual(breakdown["conceptual_accuracy"], 100.0)
        self.assertEqual(breakdown["reasoning_and_logic"], 0.0)
        self.assertEqual(len(result["detected_misconceptions"]), 1)
        self.assertEqual(result["detected_misconceptions"][0]["misconception_code"], "off_by_one_range")

    @patch("services.answer_generation_service._generate_with_langchain_fallback")
    def test_gemini_evaluator_filters_unknown_misconceptions(self, mock_gen):
        mock_gen.return_value = (
            '{"conceptual_accuracy": 70.0, "reasoning_and_logic": 70.0, "edge_cases_and_gotchas": 70.0, "clarity_of_expression": 70.0, "detected_misconceptions": ["hallucinated_code_xyz", "off_by_one_range"], "feedback": "Check bounds"}',
            "gemini-3.8-flash"
        )
        result = evaluate_subjective_explanation(
            "q", "ref", "student", use_ai=True, user_id=self.USER_ID
        )
        detected_codes = [m["misconception_code"] for m in result["detected_misconceptions"]]
        self.assertIn("off_by_one_range", detected_codes)
        self.assertNotIn("hallucinated_code_xyz", detected_codes)

    @patch("services.answer_generation_service._generate_with_langchain_fallback")
    def test_gemini_evaluator_falls_back_on_api_error(self, mock_gen):
        mock_gen.side_effect = RuntimeError("429 Resource Exhausted")
        result = evaluate_subjective_explanation(
            "How does range work?",
            "range(start, stop) generates numbers excluding stop.",
            "range(0, 5) includes 5.",
            topic_slug="loops",
            use_ai=True,
            user_id=self.USER_ID,
        )
        self.assertEqual(result["evaluator_type"], "deterministic_fallback")
        self.assertIn("fallback_reason", result)
        self.assertIn("Notice:", result["feedback"])

    @patch("services.answer_generation_service._generate_with_langchain_fallback")
    def test_gemini_evaluator_falls_back_on_invalid_json(self, mock_gen):
        mock_gen.return_value = ("Sorry, I cannot grade this in JSON format.", "gemini-3.8-flash")
        result = evaluate_subjective_explanation(
            "q", "ref", "student", use_ai=True, user_id=self.USER_ID
        )
        self.assertEqual(result["evaluator_type"], "deterministic_fallback")
        self.assertIn("fallback_reason", result)

    def test_evaluator_blocks_when_user_id_missing(self):
        """Missing or blank user_id must block AI evaluation and fallback deterministically."""
        res_none = evaluate_subjective_explanation("q", "ref", "student", use_ai=True, user_id=None)
        self.assertEqual(res_none["evaluator_type"], "deterministic_fallback")
        self.assertIn("user id", res_none.get("fallback_reason", "").lower())

        res_blank = evaluate_subjective_explanation("q", "ref", "student", use_ai=True, user_id="   ")
        self.assertEqual(res_blank["evaluator_type"], "deterministic_fallback")
        self.assertIn("user id", res_blank.get("fallback_reason", "").lower())

    def test_evaluator_blocks_when_db_consent_false_even_if_supplied_true(self):
        """Authoritative DB consent=False blocks AI even if caller supplies True."""
        with patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            res = evaluate_subjective_explanation(
                "q", "ref", "student", use_ai=True, user_id=self.USER_ID, ai_consent=True
            )
            self.assertEqual(res["evaluator_type"], "deterministic_fallback")
            self.assertIn("consent", res.get("fallback_reason", "").lower())

    @patch("services.subjective_evaluation_service.evaluate_subjective_explanation_gemini")
    def test_evaluator_proceeds_when_db_consent_true_even_if_supplied_false(self, mock_gemini):
        """Authoritative DB consent=True allows AI even if caller supplies stale False."""
        mock_gemini.return_value = {"evaluator_type": "gemini", "score_percent": 90.0}
        with patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": True},
        ):
            res = evaluate_subjective_explanation(
                "q", "ref", "student", use_ai=True, user_id=self.USER_ID, ai_consent=False
            )
            self.assertEqual(res["evaluator_type"], "gemini")
            mock_gemini.assert_called_once()

    def test_evaluator_blocks_when_db_adult_confirmation_false_even_if_supplied_true(self):
        """Authoritative DB adult_confirmation=False blocks AI even if caller supplies True."""
        with patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": False},
        ):
            res = evaluate_subjective_explanation(
                "q", "ref", "student", use_ai=True, user_id=self.USER_ID, adult_confirmation=True
            )
            self.assertEqual(res["evaluator_type"], "deterministic_fallback")
            self.assertIn("adult", res.get("fallback_reason", "").lower())

    def test_evaluator_blocks_when_db_lookup_fails(self):
        """Database lookup exception blocks AI evaluation and routes deterministically."""
        with patch(
            "services.learner_service.get_learner_profile",
            side_effect=RuntimeError("Database connection lost"),
        ):
            res = evaluate_subjective_explanation(
                "q", "ref", "student", use_ai=True, user_id=self.USER_ID
            )
            self.assertEqual(res["evaluator_type"], "deterministic_fallback")
            self.assertIn("database verification failed", res.get("fallback_reason", "").lower())

    def test_evaluator_blocks_when_consent_revoked_in_db_despite_stale_session(self):
        """Simulate consent revoked in DB while session still has True: must BLOCK."""
        with patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            res = evaluate_subjective_explanation(
                "q", "ref", "student", use_ai=True, user_id=self.USER_ID, ai_consent=True
            )
            self.assertEqual(res["evaluator_type"], "deterministic_fallback")
            self.assertIn("consent", res.get("fallback_reason", "").lower())


if __name__ == "__main__":
    unittest.main()
