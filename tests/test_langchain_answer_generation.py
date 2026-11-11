"""Tests for EduPath's LangChain Gemini answer-generation pipeline."""

import unittest
from unittest.mock import patch

from langchain_core.runnables import RunnableLambda

from services.answer_generation_service import (
    AnswerGenerationError,
    FALLBACK_GENERATION_MODEL,
    GENERATION_MODEL,
    SYSTEM_INSTRUCTION,
    generate_grounded_answer,
)


def make_chunk():
    """Create a representative retrieved course chunk."""

    return {
        "chunk_id": "chunk-001",
        "document_id": "document-001",
        "source_title": "Python Variables Notes",
        "file_name": "variables.md",
        "source_license": "Original",
        "rights_basis": "original",
        "course_slug": "python-basics",
        "topic_slug": "variables-data-types",
        "topic_name": "Variables and Data Types",
        "page_number": 1,
        "chunk_index": 0,
        "content": "Python variables are created when a value is assigned.",
        "similarity": 0.85,
    }


class LangChainAnswerGenerationTests(unittest.TestCase):

    @patch(
        "services.answer_generation_service.load_gemini_api_key",
        return_value="test-api-key",
    )
    @patch("services.answer_generation_service.ChatGoogleGenerativeAI")
    def test_generates_grounded_answer_using_langchain(
        self,
        mock_model_factory,
        mock_load_key,
    ):
        captured = {}

        def fake_model(prompt_value):
            captured["messages"] = prompt_value.to_messages()
            return "Python variables are created by assignment. [S1]"

        mock_model_factory.return_value = RunnableLambda(fake_model)

        result = generate_grounded_answer(
            question="How are Python variables created?",
            retrieved_chunks=[make_chunk()],
        )

        self.assertFalse(result["insufficient_evidence"])
        self.assertEqual(result["model"], GENERATION_MODEL)
        self.assertIn("[S1]", result["answer"])
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(
            result["citations"][0]["document_id"],
            "document-001",
        )

        mock_load_key.assert_called_once()

        mock_model_factory.assert_called_once_with(
            model=GENERATION_MODEL,
            google_api_key="test-api-key",
            temperature=0.2,
            max_output_tokens=1200,
            max_retries=1,
        )

        self.assertEqual(
            captured["messages"][0].content,
            SYSTEM_INSTRUCTION,
        )
        self.assertIn(
            "How are Python variables created?",
            captured["messages"][1].content,
        )

    @patch(
        "services.answer_generation_service.load_gemini_api_key",
        return_value="test-api-key",
    )
    @patch("services.answer_generation_service.ChatGoogleGenerativeAI")
    def test_uses_fallback_after_temporary_server_error(
        self,
        mock_model_factory,
        mock_load_key,
    ):
        def fail_with_server_error(_):
            error = RuntimeError("Temporary service unavailable")
            error.code = 503
            raise error

        primary_model = RunnableLambda(fail_with_server_error)

        fallback_model = RunnableLambda(
            lambda _: "A variable refers to a value. [S1]"
        )

        mock_model_factory.side_effect = [
            primary_model,
            fallback_model,
        ]

        result = generate_grounded_answer(
            question="What is a variable?",
            retrieved_chunks=[make_chunk()],
        )

        self.assertFalse(result["insufficient_evidence"])
        self.assertEqual(
            result["model"],
            FALLBACK_GENERATION_MODEL,
        )
        self.assertEqual(
            mock_model_factory.call_count,
            2,
        )
        self.assertEqual(
            mock_load_key.call_count,
            2,
        )

    @patch(
        "services.answer_generation_service.load_gemini_api_key",
        return_value="test-api-key",
    )
    @patch("services.answer_generation_service.ChatGoogleGenerativeAI")
    def test_does_not_retry_non_retryable_error(
        self,
        mock_model_factory,
        mock_load_key,
    ):
        def fail_with_client_error(_):
            error = RuntimeError("Invalid request")
            error.code = 400
            raise error

        mock_model_factory.return_value = RunnableLambda(
            fail_with_client_error
        )

        with self.assertRaises(AnswerGenerationError):
            generate_grounded_answer(
                question="What is a variable?",
                retrieved_chunks=[make_chunk()],
            )

        mock_model_factory.assert_called_once()
        mock_load_key.assert_called_once()


if __name__ == "__main__":
    unittest.main()