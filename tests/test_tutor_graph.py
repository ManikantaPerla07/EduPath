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



    def test_resolves_follow_up_before_retrieval(self):
        history = [
            {"role": "user", "content": "What is a Python variable?"},
            {
                "role": "assistant",
                "content": "A variable refers to a value.",
            },
        ]

        resolved_query = (
            "Explain Python variable reassignment with an example."
        )

        expected_result = {
            "answer": "A variable can refer to a new value. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        chunks = [{"chunk_id": "chunk-1", "content": "Python variables."}]

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question"
            ) as resolve,
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            resolve.return_value = resolved_query
            retrieve.return_value = chunks
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="Explain that with an example.",
                course_slug="python-basics",
                conversation_history=history,
            )

        self.assertEqual(result, expected_result)

        resolve.assert_called_once_with(
            question="Explain that with an example.",
            conversation_history=history,
            client=None,
        )

        retrieve.assert_called_once_with(
            query=resolved_query,
            course_slug="python-basics",
            topic_slug=None,
            limit=5,
            client=None,
        )

        generate.assert_called_once_with(
            question=resolved_query,
            retrieved_chunks=chunks,
            client=None,
        )

    def test_passes_empty_history_for_a_new_conversation(self):
        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ) as resolve,
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = []
            generate.return_value = {
                "answer": "Insufficient evidence.",
                "insufficient_evidence": True,
                "citations": [],
                "retrieved_count": 0,
                "model": "test-model",
                "reason": "no_retrieved_evidence",
            }

            run_tutor_graph(
                question="What is Python?",
                course_slug="python-basics",
            )

        resolve.assert_called_once_with(
            question="What is Python?",
            conversation_history=[],
            client=None,
        )

        retrieve.assert_called_once_with(
            query="What is Python?",
            course_slug="python-basics",
            topic_slug=None,
            limit=5,
            client=None,
        )

    def test_rejects_invalid_history_before_context_resolution(self):
        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question"
            ) as resolve,
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Conversation history must be a list.",
            ):
                run_tutor_graph(
                    question="Explain that.",
                    course_slug="python-basics",
                    conversation_history="invalid",
                )

            resolve.assert_not_called()
            retrieve.assert_not_called()



    def test_loads_learner_progress_and_passes_teaching_guidance(self):
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        history = [
            {"role": "user", "content": "What are Python variables?"},
        ]

        chunks = [
            {
                "chunk_id": "chunk-1",
                "topic_slug": "variables-data-types",
                "content": "Python variables store references to values.",
            }
        ]

        teaching_profile = {
            "topic_slug": "variables-data-types",
            "topic_name": "Variables and Data Types",
            "mastery_status": "needs_revision",
            "level": "foundational_revision",
            "label": "Foundational revision",
            "instruction": "Break the concept into small steps.",
        }

        expected_result = {
            "answer": "A variable refers to a value. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
            "teaching_profile": teaching_profile,
        }

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch(
                "agents.tutor_graph.get_learner_teaching_profile"
            ) as get_profile,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = chunks
            get_profile.return_value = teaching_profile
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="What are Python variables?",
                course_slug="python-basics",
                conversation_history=history,
                user_id=user_id,
            )

        self.assertEqual(result, expected_result)

        get_profile.assert_called_once_with(
            user_id=user_id,
            course_slug="python-basics",
            retrieved_chunks=chunks,
        )

        generate.assert_called_once_with(
            question="What are Python variables?",
            retrieved_chunks=chunks,
            client=None,
            teaching_guidance=teaching_profile,
        )

    def test_skips_progress_lookup_when_retrieval_finds_no_sources(self):
        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            patch("agents.tutor_graph.search_knowledge_base") as retrieve,
            patch(
                "agents.tutor_graph.get_learner_teaching_profile"
            ) as get_profile,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = []
            generate.return_value = {
                "answer": "Insufficient evidence.",
                "insufficient_evidence": True,
                "citations": [],
                "retrieved_count": 0,
                "model": "test-model",
                "reason": "no_retrieved_evidence",
            }

            result = run_tutor_graph(
                question="What is an unknown topic?",
                course_slug="python-basics",
                user_id="123e4567-e89b-12d3-a456-426614174000",
            )

        self.assertTrue(result["insufficient_evidence"])
        get_profile.assert_not_called()
        generate.assert_called_once_with(
            question="What is an unknown topic?",
            retrieved_chunks=[],
            client=None,
        )

    def test_rejects_invalid_learner_id_before_context_resolution(self):
        with patch(
            "agents.tutor_graph.resolve_contextual_question"
        ) as resolve:
            with self.assertRaisesRegex(
                ValueError,
                "Learner user ID must be a non-empty string.",
            ):
                run_tutor_graph(
                    question="What is Python?",
                    course_slug="python-basics",
                    user_id="   ",
                )

            resolve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
