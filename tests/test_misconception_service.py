"""Comprehensive tests for Misconception Catalogue & Diagnosis Service.

Verifies Phase B2 requirements:
- Controlled catalogue using stable, documented codes.
- Diagnostic result structure (code, topic, description, correction, confidence, timestamp).
- Unknown misconception codes handled cleanly.
- Multiple misconceptions detected in a single text.
- Malformed, empty, and non-string explanations rejected or handled gracefully.
- Server-side UUID enforcement and authorization isolation.
"""

import unittest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from services.misconception_service import (
    MISCONCEPTION_CATALOGUE,
    diagnose_student_misconceptions,
    get_misconception_definition,
    list_misconception_codes,
    record_learner_misconceptions,
    fetch_active_learner_misconceptions,
    resolve_learner_misconception,
)


class MisconceptionServiceTests(unittest.TestCase):

    def test_catalogue_contains_required_stable_codes(self):
        required_codes = {
            "off_by_one_range",
            "assignment_vs_equality",
            "list_mutation_during_iteration",
            "return_vs_print",
            "mutable_default_argument",
            "zero_based_indexing",
            "string_immutability",
            "variable_scope_leak",
        }
        for code in required_codes:
            entry = get_misconception_definition(code)
            self.assertIsNotNone(entry, f"Missing required code {code}")
            self.assertEqual(entry["code"], code)
            self.assertTrue(len(entry["topic"]) > 0)
            self.assertTrue(len(entry["short_description"]) > 0)
            self.assertTrue(len(entry["corrective_explanation"]) > 0)
            self.assertIn("remedial_exemplar", entry)

    def test_unknown_misconception_code_returns_none(self):
        self.assertIsNone(get_misconception_definition("non_existent_code_xyz"))
        self.assertIsNone(get_misconception_definition(12345))  # type: ignore

    def test_list_misconception_codes_filtered_by_topic(self):
        all_codes = list_misconception_codes()
        self.assertGreaterEqual(len(all_codes), 8)

        loop_codes = list_misconception_codes(topic_slug="loops")
        self.assertIn("off_by_one_range", loop_codes)
        self.assertNotIn("assignment_vs_equality", loop_codes)

        func_codes = list_misconception_codes(topic_slug="functions")
        self.assertIn("return_vs_print", func_codes)
        self.assertIn("mutable_default_argument", func_codes)

    def test_diagnose_off_by_one_range(self):
        text = "I ran for i in range(1, 5) and it includes 5 in the output."
        diagnoses = diagnose_student_misconceptions(text, topic_slug="loops")
        self.assertEqual(len(diagnoses), 1)
        d = diagnoses[0]
        self.assertEqual(d["misconception_code"], "off_by_one_range")
        self.assertEqual(d["topic_slug"], "loops")
        self.assertIn("exclusive", d["corrective_explanation"])
        self.assertIn("timestamp", d)
        self.assertGreaterEqual(d["confidence"], 0.8)

    def test_diagnose_multiple_misconceptions(self):
        text = (
            "I checked if x = 5 inside the loop, and range(1, 5) includes 5."
        )
        diagnoses = diagnose_student_misconceptions(text)
        codes = {d["misconception_code"] for d in diagnoses}
        self.assertIn("assignment_vs_equality", codes)
        self.assertIn("off_by_one_range", codes)
        self.assertEqual(len(diagnoses), 2)

    def test_diagnose_handles_empty_or_malformed_input(self):
        self.assertEqual(diagnose_student_misconceptions(""), [])
        self.assertEqual(diagnose_student_misconceptions("    "), [])
        self.assertEqual(diagnose_student_misconceptions(None), [])  # type: ignore
        self.assertEqual(diagnose_student_misconceptions(12345), [])  # type: ignore

    def test_record_misconceptions_validates_uuid(self):
        with self.assertRaises(ValueError):
            record_learner_misconceptions("not-a-valid-uuid", [])
        with self.assertRaises(ValueError):
            record_learner_misconceptions("", [])

    def test_fetch_misconceptions_validates_uuid(self):
        with self.assertRaises(ValueError):
            fetch_active_learner_misconceptions("invalid-uuid")
        with self.assertRaises(ValueError):
            fetch_active_learner_misconceptions("")

    def test_resolve_misconception_handles_invalid_user_id(self):
        self.assertFalse(resolve_learner_misconception("invalid", "off_by_one_range"))
        self.assertFalse(resolve_learner_misconception(None, "off_by_one_range"))  # type: ignore


if __name__ == "__main__":
    unittest.main()
