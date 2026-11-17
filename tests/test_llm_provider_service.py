"""Tests for EduPath's unified multi-LLM provider service."""

import unittest
from unittest.mock import MagicMock, call, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from services.llm_provider_service import (
    DEFAULT_CANDIDATE_CHAIN,
    GEMINI_FALLBACK_MODEL,
    GEMINI_PRIMARY_MODEL,
    GROQ_FALLBACK_MODEL,
    GROQ_PRIMARY_MODEL,
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    GenerationResult,
    LLMProviderError,
    create_chat_model,
    execute_tool_router_with_failover,
    generate_with_provider_failover,
    is_retryable_llm_error,
)


class LLMErrorClassificationTests(unittest.TestCase):
    """Test retryability classification across Gemini and Groq error shapes."""

    def test_client_error_400_is_strictly_not_retryable(self):
        err = RuntimeError("Bad request syntax")
        err.code = 400
        self.assertFalse(is_retryable_llm_error(err))

    def test_auth_error_401_403_is_not_retryable(self):
        err = RuntimeError("Permission denied")
        err.status_code = 403
        self.assertFalse(is_retryable_llm_error(err))

    def test_rate_limit_429_is_retryable(self):
        err = RuntimeError("Rate limit exceeded")
        err.code = 429
        self.assertTrue(is_retryable_llm_error(err))

    def test_server_errors_500_502_503_504_are_retryable(self):
        for code in (500, 502, 503, 504, 524):
            err = RuntimeError(f"Server error {code}")
            err.code = code
            self.assertTrue(is_retryable_llm_error(err))

    def test_transport_timeout_is_retryable(self):
        timeout_error = type(
            "ConnectTimeout",
            (Exception,),
            {"__module__": "httpx"},
        )("Connection timed out after 30s")
        self.assertTrue(is_retryable_llm_error(timeout_error))

    def test_nested_exception_chain_detects_server_error(self):
        root = RuntimeError("Top level message")
        cause = RuntimeError("Underlying 503")
        cause.code = 503
        root.__cause__ = cause
        self.assertTrue(is_retryable_llm_error(root))


class GenerationResultTupleTests(unittest.TestCase):
    """Verify GenerationResult behaves as a backward-compatible 2-tuple."""

    def test_tuple_unpacking_and_metadata(self):
        result = GenerationResult(
            answer="Python is high-level. [S1]",
            model_name="openai/gpt-oss-120b",
            provider=PROVIDER_GROQ,
            elapsed_seconds=1.23,
            attempts=[{"provider": "gemini", "status": "failed"}],
        )

        # Unpack as standard 2-tuple (answer, model_name)
        ans, model = result
        self.assertEqual(ans, "Python is high-level. [S1]")
        self.assertEqual(model, "openai/gpt-oss-120b")
        self.assertEqual(len(result), 2)
        self.assertTrue(isinstance(result, tuple))

        # Metadata attributes
        self.assertEqual(result.provider, PROVIDER_GROQ)
        self.assertEqual(result.elapsed_seconds, 1.23)
        self.assertEqual(len(result.attempts), 1)


class LLMModelFactoryTests(unittest.TestCase):
    """Verify chat model instantiation for supported providers."""

    @patch("services.llm_provider_service.load_gemini_api_key", return_value="test-gemini-key")
    def test_creates_gemini_chat_model(self, mock_key):
        model = create_chat_model(
            provider=PROVIDER_GEMINI,
            model_name=GEMINI_PRIMARY_MODEL,
        )
        self.assertEqual(type(model).__name__, "ChatGoogleGenerativeAI")
        mock_key.assert_called_once()

    @patch("services.llm_provider_service.load_groq_api_key", return_value="test-groq-key")
    def test_creates_groq_chat_model(self, mock_key):
        model = create_chat_model(
            provider=PROVIDER_GROQ,
            model_name=GROQ_PRIMARY_MODEL,
        )
        self.assertEqual(type(model).__name__, "ChatGroq")
        mock_key.assert_called_once()

    def test_unsupported_provider_raises_error(self):
        with self.assertRaises(ValueError):
            create_chat_model(provider="unknown_provider")


class LLMProviderFailoverTests(unittest.TestCase):
    """Test primary-to-secondary failover and telemetry."""

    @patch("services.llm_provider_service.load_groq_api_key", return_value="test-groq-key")
    @patch("services.llm_provider_service.load_gemini_api_key", return_value="test-gemini-key")
    @patch("services.llm_provider_service.create_chat_model")
    def test_succeeds_on_primary_gemini(self, mock_factory, mock_gem_key, mock_groq_key):
        primary_mock = RunnableLambda(lambda _: "Primary Gemini answer")
        mock_factory.return_value = primary_mock

        result = generate_with_provider_failover("What is Python?")

        self.assertEqual(result.answer, "Primary Gemini answer")
        self.assertEqual(result.provider, PROVIDER_GEMINI)
        self.assertEqual(result.model_name, GEMINI_PRIMARY_MODEL)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0]["status"], "ok")

    @patch("services.llm_provider_service.load_groq_api_key", return_value="test-groq-key")
    @patch("services.llm_provider_service.load_gemini_api_key", return_value="test-gemini-key")
    @patch("services.llm_provider_service.create_chat_model")
    def test_fails_over_to_gemini_fallback_on_transient_error(
        self,
        mock_factory,
        mock_gem_key,
        mock_groq_key,
    ):
        err_503 = RuntimeError("Service Unavailable")
        err_503.code = 503

        primary_mock = RunnableLambda(MagicMock(side_effect=err_503))
        fallback_mock = RunnableLambda(lambda _: "Gemini fallback answer")

        mock_factory.side_effect = [primary_mock, fallback_mock]

        result = generate_with_provider_failover("What is Python?")

        self.assertEqual(result.answer, "Gemini fallback answer")
        self.assertEqual(result.provider, PROVIDER_GEMINI)
        self.assertEqual(result.model_name, GEMINI_FALLBACK_MODEL)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[0]["status"], "failed")
        self.assertEqual(result.attempts[1]["status"], "ok")

    @patch("services.llm_provider_service.load_groq_api_key", return_value="test-groq-key")
    @patch("services.llm_provider_service.load_gemini_api_key", return_value="test-gemini-key")
    @patch("services.llm_provider_service.create_chat_model")
    def test_fails_over_to_groq_when_all_gemini_models_fail(
        self,
        mock_factory,
        mock_gem_key,
        mock_groq_key,
    ):
        err_504 = RuntimeError("Gateway Timeout / Deadline Exceeded")
        err_504.code = 504

        gemini_1 = RunnableLambda(MagicMock(side_effect=err_504))
        gemini_2 = RunnableLambda(MagicMock(side_effect=err_504))
        groq_primary = RunnableLambda(lambda _: "Groq 120b answer [S1]")

        mock_factory.side_effect = [gemini_1, gemini_2, groq_primary]

        result = generate_with_provider_failover("What is Python?")

        self.assertEqual(result.answer, "Groq 120b answer [S1]")
        self.assertEqual(result.provider, PROVIDER_GROQ)
        self.assertEqual(result.model_name, GROQ_PRIMARY_MODEL)
        self.assertEqual(len(result.attempts), 3)
        self.assertEqual(result.attempts[0]["provider"], PROVIDER_GEMINI)
        self.assertEqual(result.attempts[0]["status"], "failed")
        self.assertEqual(result.attempts[1]["provider"], PROVIDER_GEMINI)
        self.assertEqual(result.attempts[1]["status"], "failed")
        self.assertEqual(result.attempts[2]["provider"], PROVIDER_GROQ)
        self.assertEqual(result.attempts[2]["status"], "ok")

    @patch("services.llm_provider_service.load_groq_api_key", return_value="test-groq-key")
    @patch("services.llm_provider_service.load_gemini_api_key", return_value="test-gemini-key")
    @patch("services.llm_provider_service.create_chat_model")
    def test_client_error_400_halts_immediately_without_groq_failover(
        self,
        mock_factory,
        mock_gem_key,
        mock_groq_key,
    ):
        err_400 = RuntimeError("Invalid argument / Bad Request")
        err_400.code = 400

        mock_factory.return_value = RunnableLambda(MagicMock(side_effect=err_400))

        with self.assertRaises(LLMProviderError):
            generate_with_provider_failover("Bad question")

        mock_factory.assert_called_once()


if __name__ == "__main__":
    unittest.main()
