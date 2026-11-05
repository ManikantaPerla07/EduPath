from pathlib import Path
import sys
import unittest
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.grading_service import grade_mcq_answer


class TestGradingService(unittest.TestCase):

    def test_correct_answer(self):
        result = grade_mcq_answer("B", "B")
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["awarded_points"], Decimal("1"))

    def test_case_insensitive_answer(self):
        result = grade_mcq_answer("B", " b ")
        self.assertTrue(result["is_correct"])

    def test_incorrect_answer(self):
        result = grade_mcq_answer("B", "A")
        self.assertFalse(result["is_correct"])
        self.assertEqual(result["awarded_points"], Decimal("0"))

    def test_unanswered_question(self):
        result = grade_mcq_answer("B", None)
        self.assertFalse(result["is_correct"])
        self.assertEqual(result["awarded_points"], Decimal("0"))

    def test_empty_answer(self):
        result = grade_mcq_answer("B", "")
        self.assertFalse(result["is_correct"])
        self.assertEqual(result["awarded_points"], Decimal("0"))

    def test_custom_points(self):
        result = grade_mcq_answer("C", "C", Decimal("2.5"))
        self.assertEqual(result["awarded_points"], Decimal("2.5"))

    def test_explanation_returned_after_grading(self):
        result = grade_mcq_answer(
            "B",
            "A",
            explanation="Option B is correct because 10 is an integer."
        )
        self.assertEqual(
            result["explanation"],
            "Option B is correct because 10 is an integer."
        )

    def test_invalid_answer_key(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("E", "B")

    def test_invalid_submitted_answer(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("B", "E")

    def test_non_string_submitted_answer(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("B", 2)

    def test_zero_points(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("B", "B", 0)

    def test_negative_points(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("B", "B", -1)

    def test_invalid_points(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("B", "B", "invalid")

    def test_boolean_points(self):
        with self.assertRaises(ValueError):
            grade_mcq_answer("B", "B", True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
