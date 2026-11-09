import unittest

from ui.assessment import (
    _get_answer_letter,
    _answer_state_key,
    _get_option_text,
)


class AssessmentUITests(unittest.TestCase):

    def test_convert_option_a(self):
        self.assertEqual(_get_answer_letter("A. High"), "A")

    def test_convert_option_b(self):
        self.assertEqual(_get_answer_letter("B. Low"), "B")

    def test_convert_option_c(self):
        self.assertEqual(_get_answer_letter("C. True"), "C")

    def test_convert_option_d(self):
        self.assertEqual(_get_answer_letter("D. Error"), "D")

    def test_reject_invalid_option(self):
        with self.assertRaises(ValueError):
            _get_answer_letter("E. Invalid")

    def test_reject_non_string_option(self):
        with self.assertRaises(ValueError):
            _get_answer_letter(None)

    def test_generate_assessment_state_key(self):
        key = _answer_state_key("assessment-123")

        self.assertEqual(
            key,
            "edupath_answers_assessment-123",
        )

    def test_get_full_option_text(self):
        options = [
            "A. Programming language",
            "B. Web browser",
            "C. Database",
            "D. Operating system",
        ]

        self.assertEqual(
            _get_option_text(options, "B"),
            "B. Web browser",
        )

    def test_fallback_for_missing_option(self):
        options = ["A. High", "B. Low"]

        self.assertEqual(
            _get_option_text(options, "C"),
            "C",
        )


if __name__ == "__main__":
    unittest.main()

class AssessmentModeTests(unittest.TestCase):

    def test_diagnostic_keeps_original_question_selection(self):
        from ui.assessment import _assessment_start_options

        self.assertEqual(
            _assessment_start_options("diagnostic"),
            {"assessment_type": "diagnostic"},
        )

    def test_practice_requests_five_adaptive_questions(self):
        from ui.assessment import _assessment_start_options

        self.assertEqual(
            _assessment_start_options("practice"),
            {
                "assessment_type": "practice",
                "question_count": 5,
            },
        )

    def test_revision_requests_five_adaptive_questions(self):
        from ui.assessment import _assessment_start_options

        self.assertEqual(
            _assessment_start_options("revision"),
            {
                "assessment_type": "revision",
                "question_count": 5,
            },
        )

    def test_unknown_assessment_mode_is_rejected(self):
        from ui.assessment import _assessment_start_options

        with self.assertRaises(ValueError):
            _assessment_start_options("exam")

class AssessmentModeLabelTests(unittest.TestCase):

    def test_diagnostic_label(self):
        from ui.assessment import _assessment_mode_label

        self.assertEqual(
            _assessment_mode_label("diagnostic"),
            "Diagnostic Assessment",
        )

    def test_practice_label(self):
        from ui.assessment import _assessment_mode_label

        self.assertEqual(
            _assessment_mode_label("practice"),
            "Adaptive Practice",
        )

    def test_revision_label(self):
        from ui.assessment import _assessment_mode_label

        self.assertEqual(
            _assessment_mode_label("revision"),
            "Targeted Revision",
        )

    def test_unknown_mode_is_rejected(self):
        from ui.assessment import _assessment_mode_label

        with self.assertRaises(ValueError):
            _assessment_mode_label("unknown")

class AssessmentModeLabelTests(unittest.TestCase):

    def test_diagnostic_label(self):
        from ui.assessment import _assessment_mode_label

        self.assertEqual(
            _assessment_mode_label("diagnostic"),
            "Diagnostic Assessment",
        )

    def test_practice_label(self):
        from ui.assessment import _assessment_mode_label

        self.assertEqual(
            _assessment_mode_label("practice"),
            "Adaptive Practice",
        )

    def test_revision_label(self):
        from ui.assessment import _assessment_mode_label

        self.assertEqual(
            _assessment_mode_label("revision"),
            "Targeted Revision",
        )

    def test_unknown_mode_is_rejected(self):
        from ui.assessment import _assessment_mode_label

        with self.assertRaises(ValueError):
            _assessment_mode_label("unknown")
