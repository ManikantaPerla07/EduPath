"""Tests for the LangGraph-based EduPath tutor workflow."""

import unittest
from unittest.mock import patch

from agents.tutor_graph import run_tutor_graph


class TestTutorGraph(unittest.TestCase):

    def test_generates_answer_when_retrieval_finds_sources(self):
        chunks = [
            {
                "chunk_id": "chunk-1",
                "content": "Variables store values in Python.",
            }
        ]

        expected_result = {
            "answer": "Variables store values. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        with (
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = chunks
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="What is a variable?",
                course_slug="python-basics",
            )

        self.assertEqual(result, expected_result)

        retrieve.assert_called_once_with(
            query="What is a variable?",
            course_slug="python-basics",
            topic_slug=None,
            limit=5,
            client=None,
        )

        generate.assert_called_once_with(
            question="What is a variable?",
            retrieved_chunks=chunks,
            client=None,
        )

    def test_uses_abstention_path_when_retrieval_finds_no_sources(self):
        expected_result = {
            "answer": "Insufficient approved course material.",
            "insufficient_evidence": True,
            "citations": [],
            "retrieved_count": 0,
            "model": "test-model",
            "reason": "no_retrieved_evidence",
        }

        with (
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = []
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="Explain an unknown topic.",
                course_slug="python-basics",
            )

        self.assertEqual(result, expected_result)

        generate.assert_called_once_with(
            question="Explain an unknown topic.",
            retrieved_chunks=[],
            client=None,
        )

    def test_rejects_empty_question_before_retrieval(self):
        with patch("agents.tutor_graph.search_knowledge_base") as retrieve:
            with self.assertRaisesRegex(
                ValueError,
                "Question cannot be empty.",
            ):
                run_tutor_graph(
                    question="   ",
                    course_slug="python-basics",
                )

            retrieve.assert_not_called()

    def test_rejects_invalid_search_limit_before_retrieval(self):
        with patch("agents.tutor_graph.search_knowledge_base") as retrieve:
            with self.assertRaisesRegex(
                ValueError,
                "Search limit must be an integer",
            ):
                run_tutor_graph(
                    question="What is Python?",
                    course_slug="python-basics",
                    limit=0,
                )

            retrieve.assert_not_called()

    def test_passes_topic_limit_and_client_to_existing_services(self):
        chunks = [{"chunk_id": "chunk-2", "content": "Python lists."}]
        expected_result = {
            "answer": "A list stores multiple values. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        fake_client = object()

        with (
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = chunks
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="What is a list?",
                course_slug="python-basics",
                topic_slug="lists",
                limit=3,
                client=fake_client,
            )

        self.assertEqual(result, expected_result)

        retrieve.assert_called_once_with(
            query="What is a list?",
            course_slug="python-basics",
            topic_slug="lists",
            limit=3,
            client=fake_client,
        )

        generate.assert_called_once_with(
            question="What is a list?",
            retrieved_chunks=chunks,
            client=fake_client,
        )


if __name__ == "__main__":
    unittest.main()
