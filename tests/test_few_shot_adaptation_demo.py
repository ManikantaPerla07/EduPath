"""Unit tests for the few-shot adaptation demonstration module."""

import unittest
from unittest.mock import MagicMock, patch

from demonstrations.few_shot_adaptation_demo import (
    REFERENCE_EDUCATIONAL_CHUNKS,
    TARGET_QUESTION,
    _retrieve_sources_for_demo,
    run_demonstration,
)


class FewShotAdaptationDemoTests(unittest.TestCase):

    def test_offline_demonstration_returns_all_three_levels(self):
        """Offline demonstration must return beginner, intermediate, and advanced levels."""
        res = run_demonstration(live=False)

        self.assertEqual(res["mode"], "offline")
        self.assertEqual(res["target_question"], TARGET_QUESTION)
        self.assertIn("beginner", res["levels"])
        self.assertIn("intermediate", res["levels"])
        self.assertIn("advanced", res["levels"])

        for level in ("beginner", "intermediate", "advanced"):
            lvl_data = res["levels"][level]
            self.assertEqual(lvl_data["source"], "curated_exemplar")
            self.assertTrue(len(lvl_data["answer"]) > 50)
            self.assertTrue(isinstance(lvl_data["misconception"], str))

    @patch("services.answer_generation_service.generate_grounded_answer")
    def test_live_demonstration_calls_generation_service(self, mock_generate):
        """Live demonstration must invoke generate_grounded_answer for each level."""
        mock_generate.return_value = {
            "answer": "A for loop repeats actions [S1].",
            "model": "gemini-3.5-flash-lite",
            "citations": [{"source_id": "S1"}],
        }

        res = run_demonstration(live=True)

        self.assertEqual(res["mode"], "live")
        self.assertEqual(mock_generate.call_count, 3)

        for level in ("beginner", "intermediate", "advanced"):
            lvl_data = res["levels"][level]
            self.assertEqual(lvl_data["source"], "live_gemini")
            self.assertEqual(lvl_data["model"], "gemini-3.5-flash-lite")
            self.assertEqual(lvl_data["answer"], "A for loop repeats actions [S1].")
            self.assertEqual(len(lvl_data["citations"]), 1)

    @patch("services.answer_generation_service.generate_grounded_answer")
    def test_live_demonstration_falls_back_gracefully_on_error(self, mock_generate):
        """When live API fails, it must fall back to curated exemplars without crashing."""
        mock_generate.side_effect = RuntimeError("Quota exhausted or network down")

        res = run_demonstration(live=True)

        # Mode was requested as live, but each level fell back to curated_exemplar
        self.assertEqual(res["mode"], "live")
        for level in ("beginner", "intermediate", "advanced"):
            lvl_data = res["levels"][level]
            self.assertEqual(lvl_data["source"], "curated_exemplar")
            self.assertTrue(len(lvl_data["answer"]) > 50)

    @patch("services.retrieval_service.search_knowledge_base")
    def test_retrieve_sources_uses_reference_chunks_on_database_error(self, mock_search):
        """If search_knowledge_base fails, it returns the verified reference chunks."""
        mock_search.side_effect = Exception("DB connection refused")

        chunks = _retrieve_sources_for_demo(TARGET_QUESTION)
        self.assertEqual(chunks, REFERENCE_EDUCATIONAL_CHUNKS)
        self.assertTrue(len(chunks) >= 2)


if __name__ == "__main__":
    unittest.main()
