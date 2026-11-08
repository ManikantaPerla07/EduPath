"""Tests for grounded EduPath answer generation."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.answer_generation_service import (
    AnswerGenerationError,
    GENERATION_MODEL,
    FALLBACK_GENERATION_MODEL,
    INSUFFICIENT_EVIDENCE_MESSAGE,
    answer_question,
    generate_grounded_answer,
)


def make_chunk(**overrides):
    """Create a realistic retrieved educational chunk."""

    chunk = {
        "chunk_id": "chunk-001",
        "document_id": "document-001",
        "source_title": "Python Variables Notes",
        "file_name": "variables.md",
        "source_license": "Original",
        "rights_basis": "original",
        "course_slug": "python-basics",
        "topic_slug": "variables-data-types",
        "topic_name": "Introduction, Variables and Data Types",
        "page_number": None,
        "chunk_index": 0,
        "content": (
            "Python variables are created when a value is assigned. "
            "Python is dynamically typed, so a variable can refer to "
            "values of different types."
        ),
        "similarity": 0.6534,
    }

    chunk.update(overrides)

    return chunk


def make_client(
    response_text="A variable stores a value. [S1]"
):
    """Create a mocked Gemini client."""

    client = Mock()

    client.models.generate_content.return_value = SimpleNamespace(
        text=response_text
    )

    return client


class GroundedAnswerValidationTests(unittest.TestCase):

    def test_rejects_empty_question(self):
        with self.assertRaises(ValueError):
            generate_grounded_answer(
                "  ",
                [make_chunk()],
            )

    def test_rejects_non_string_question(self):
        with self.assertRaises(ValueError):
            generate_grounded_answer(
                None,
                [make_chunk()],
            )

    def test_rejects_question_over_maximum_length(self):
        with self.assertRaises(ValueError):
            generate_grounded_answer(
                "x" * 2001,
                [make_chunk()],
            )

    def test_rejects_non_list_retrieved_chunks(self):
        with self.assertRaises(ValueError):
            generate_grounded_answer(
                "What is a variable?",
                None,
            )

    def test_rejects_chunk_without_content(self):
        with self.assertRaises(ValueError):
            generate_grounded_answer(
                "What is a variable?",
                [make_chunk(content="   ")],
            )


class GroundedAnswerGenerationTests(unittest.TestCase):

    def test_empty_retrieval_abstains_without_calling_gemini(self):
        client = make_client()

        result = generate_grounded_answer(
            "What is a Python variable?",
            [],
            client=client,
        )

        self.assertTrue(result["insufficient_evidence"])
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["retrieved_count"], 0)
        self.assertEqual(result["reason"], "no_retrieved_evidence")
        self.assertEqual(
            result["answer"],
            INSUFFICIENT_EVIDENCE_MESSAGE,
        )

        client.models.generate_content.assert_not_called()

    def test_returns_answer_with_verified_source_metadata(self):
        client = make_client(
            "Python creates variables when values are assigned. [S1]"
        )

        result = generate_grounded_answer(
            "How are variables created?",
            [make_chunk()],
            client=client,
        )

        self.assertFalse(result["insufficient_evidence"])
        self.assertEqual(result["model"], GENERATION_MODEL)
        self.assertIn("[S1]", result["answer"])
        self.assertEqual(len(result["citations"]), 1)

        citation = result["citations"][0]

        self.assertEqual(citation["source_id"], "S1")
        self.assertEqual(citation["document_id"], "document-001")
        self.assertEqual(citation["chunk_id"], "chunk-001")
        self.assertEqual(citation["file_name"], "variables.md")
        self.assertEqual(
            citation["topic_slug"],
            "variables-data-types",
        )

    def test_returns_only_sources_actually_cited(self):
        second_chunk = make_chunk(
            chunk_id="chunk-002",
            document_id="document-002",
            source_title="Python Data Types Notes",
            file_name="data-types.md",
        )

        client = make_client(
            "Python is dynamically typed. [S2]"
        )

        result = generate_grounded_answer(
            "What does dynamically typed mean?",
            [make_chunk(), second_chunk],
            client=client,
        )

        self.assertFalse(result["insufficient_evidence"])

        self.assertEqual(
            [item["source_id"] for item in result["citations"]],
            ["S2"],
        )

        self.assertEqual(
            result["citations"][0]["document_id"],
            "document-002",
        )

    def test_model_insufficient_evidence_response_is_respected(self):
        client = make_client("INSUFFICIENT_EVIDENCE")

        result = generate_grounded_answer(
            "What is quantum computing?",
            [make_chunk()],
            client=client,
        )

        self.assertTrue(result["insufficient_evidence"])
        self.assertEqual(result["citations"], [])
        self.assertEqual(
            result["reason"],
            "model_found_insufficient_evidence",
        )
        self.assertEqual(
            result["answer"],
            INSUFFICIENT_EVIDENCE_MESSAGE,
        )

    def test_rejects_answer_with_unknown_citation(self):
        client = make_client(
            "Python variables store values. [S1] [S99]"
        )

        result = generate_grounded_answer(
            "What is a variable?",
            [make_chunk()],
            client=client,
        )

        self.assertTrue(result["insufficient_evidence"])
        self.assertEqual(result["citations"], [])
        self.assertEqual(
            result["reason"],
            "answer_contains_unknown_citations",
        )

    def test_rejects_answer_without_citations(self):
        client = make_client(
            "A variable stores a value."
        )

        result = generate_grounded_answer(
            "What is a variable?",
            [make_chunk()],
            client=client,
        )

        self.assertTrue(result["insufficient_evidence"])
        self.assertEqual(result["citations"], [])
        self.assertEqual(
            result["reason"],
            "answer_missing_citations",
        )

    def test_wraps_gemini_api_error(self):
        client = make_client()

        client.models.generate_content.side_effect = RuntimeError(
            "Simulated API failure"
        )

        with self.assertRaises(AnswerGenerationError):
            generate_grounded_answer(
                "What is a variable?",
                [make_chunk()],
                client=client,
            )

    def test_rejects_empty_gemini_response(self):
        client = make_client("")

        with self.assertRaises(AnswerGenerationError):
            generate_grounded_answer(
                "What is a variable?",
                [make_chunk()],
                client=client,
            )

    def test_model_receives_system_instructions_and_source_context(self):
        client = make_client()

        generate_grounded_answer(
            "What is a variable?",
            [make_chunk()],
            client=client,
        )

        call = client.models.generate_content.call_args

        self.assertEqual(
            call.kwargs["model"],
            GENERATION_MODEL,
        )

        self.assertIn(
            "LEARNER QUESTION",
            call.kwargs["contents"],
        )

        self.assertIn(
            "Python Variables Notes",
            call.kwargs["contents"],
        )

        self.assertIn(
            "untrusted reference data",
            call.kwargs["config"].system_instruction,
        )

    def test_falls_back_when_primary_model_is_temporarily_unavailable(self):
        client = make_client()

        primary_error = RuntimeError(
            "Temporary service overload"
        )
        primary_error.code = 503

        client.models.generate_content.side_effect = [
            primary_error,
            SimpleNamespace(
                text=(
                    "A variable can refer to values "
                    "of different types. [S1]"
                )
            ),
        ]

        result = generate_grounded_answer(
            "What happens when a variable gets a new value?",
            [make_chunk()],
            client=client,
        )

        self.assertFalse(result["insufficient_evidence"])

        self.assertEqual(
            result["model"],
            FALLBACK_GENERATION_MODEL,
        )

        self.assertEqual(
            len(result["citations"]),
            1,
        )

        self.assertEqual(
            client.models.generate_content.call_count,
            2,
        )

        calls = client.models.generate_content.call_args_list

        self.assertEqual(
            calls[0].kwargs["model"],
            GENERATION_MODEL,
        )

        self.assertEqual(
            calls[1].kwargs["model"],
            FALLBACK_GENERATION_MODEL,
        )

    def test_does_not_fallback_for_non_retryable_error(self):
        client = make_client()

        invalid_request_error = RuntimeError(
            "Invalid request"
        )
        invalid_request_error.code = 400

        client.models.generate_content.side_effect = (
            invalid_request_error
        )

        with self.assertRaises(AnswerGenerationError):
            generate_grounded_answer(
                "What is a variable?",
                [make_chunk()],
                client=client,
            )

        self.assertEqual(
            client.models.generate_content.call_count,
            1,
        )

    def test_fallback_failure_raises_generation_error(self):
        client = make_client()

        primary_error = RuntimeError(
            "Primary model unavailable"
        )
        primary_error.code = 503

        fallback_error = RuntimeError(
            "Fallback model failed"
        )
        fallback_error.code = 503

        client.models.generate_content.side_effect = [
            primary_error,
            fallback_error,
        ]

        with self.assertRaises(AnswerGenerationError):
            generate_grounded_answer(
                "What is a variable?",
                [make_chunk()],
                client=client,
            )

        self.assertEqual(
            client.models.generate_content.call_count,
            2,
        )


class AnswerQuestionOrchestrationTests(unittest.TestCase):

    @patch(
        "services.answer_generation_service.generate_grounded_answer"
    )
    @patch(
        "services.answer_generation_service.search_knowledge_base"
    )
    def test_retrieves_chunks_then_generates_answer(
        self,
        mock_search,
        mock_generate,
    ):
        chunks = [make_chunk()]

        expected = {
            "answer": "A variable stores a value. [S1]",
            "insufficient_evidence": False,
            "citations": [],
            "retrieved_count": 1,
            "model": GENERATION_MODEL,
            "reason": None,
        }

        mock_search.return_value = chunks
        mock_generate.return_value = expected

        result = answer_question(
            question="What is a variable?",
            course_slug="python-basics",
            topic_slug="variables-data-types",
            limit=3,
        )

        mock_search.assert_called_once_with(
            query="What is a variable?",
            course_slug="python-basics",
            topic_slug="variables-data-types",
            limit=3,
            client=None,
        )

        mock_generate.assert_called_once_with(
            question="What is a variable?",
            retrieved_chunks=chunks,
            client=None,
        )

        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()