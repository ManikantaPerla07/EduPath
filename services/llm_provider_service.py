"""Unified multi-LLM provider service for EduPath.

Supports Google Gemini as primary LLM and Groq as secondary failover provider,
with extensible provider registry, strict retryability error classification,
detailed attempt telemetry, and honest provider/model attribution.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
import logging
import time
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from services.embedding_service import SECRETS_FILE, load_gemini_api_key
from services.gemini_error_utils import (
    RETRYABLE_GEMINI_STATUS_CODES,
    _exception_chain,
    is_retryable_gemini_error,
)
from services.secret_config import load_secret

logger = logging.getLogger(__name__)

# Provider identifiers
PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ = "groq"

# Supported models per provider
GEMINI_PRIMARY_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODEL = "gemini-3.5-flash-lite"

GROQ_PRIMARY_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"

# Priority ordered candidates: Gemini primary -> Gemini fallback -> Groq primary -> Groq fallback
DEFAULT_CANDIDATE_CHAIN: list[tuple[str, str]] = [
    (PROVIDER_GEMINI, GEMINI_PRIMARY_MODEL),
    (PROVIDER_GEMINI, GEMINI_FALLBACK_MODEL),
    (PROVIDER_GROQ, GROQ_PRIMARY_MODEL),
    (PROVIDER_GROQ, GROQ_FALLBACK_MODEL),
]

# HTTP status codes that are retryable across any LLM provider
RETRYABLE_HTTP_STATUS_CODES = frozenset(
    RETRYABLE_GEMINI_STATUS_CODES | {429, 524}
)


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider fails permanently or non-retryably."""


class GenerationResult(tuple):
    """A 2-tuple (answer, model_name) with additional provider metadata.

    Subclasses tuple to guarantee 100% backward-compatibility with code
    expecting `answer, model_name = _generate(...)`.
    """

    def __new__(
        cls,
        answer: str,
        model_name: str,
        provider: str = PROVIDER_GEMINI,
        elapsed_seconds: float = 0.0,
        attempts: list[dict[str, Any]] | None = None,
    ):
        return super().__new__(cls, (answer, model_name))

    def __init__(
        self,
        answer: str,
        model_name: str,
        provider: str = PROVIDER_GEMINI,
        elapsed_seconds: float = 0.0,
        attempts: list[dict[str, Any]] | None = None,
    ):
        self.answer = answer
        self.model_name = model_name
        self.provider = provider
        self.elapsed_seconds = elapsed_seconds
        self.attempts = attempts or []


def load_groq_api_key() -> str | None:
    """Load the Groq API key from Streamlit secrets if configured."""
    try:
        return load_secret("GROQ_API_KEY", SECRETS_FILE)
    except Exception:
        return None


def _extract_status_code(error: BaseException) -> int | None:
    """Extract integer HTTP status code if present on exception, response, or cause chain."""
    for current in _exception_chain(error):
        for attribute in ("code", "status_code", "http_status"):
            value: Any = getattr(current, attribute, None)
            if isinstance(value, int) and not isinstance(value, bool):
                return value

        response = getattr(current, "response", None)
        value = getattr(response, "status_code", None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value

    return None


def is_retryable_llm_error(error: BaseException) -> bool:
    """Classify whether an LLM error is safe to failover/retry.

    Transient server errors (500, 502, 503, 504), rate limits (429 / RESOURCE_EXHAUSTED),
    and transport timeouts/disconnects are retryable. Client-side errors (400 Bad Request,
    401, 403, prompt validation issues) are strictly NOT retryable.
    """
    for current in _exception_chain(error):
        code = _extract_status_code(current)
        if code == 400:
            return False
        if code in RETRYABLE_HTTP_STATUS_CODES:
            return True

        error_type_name = type(current).__name__
        if error_type_name in (
            "GoogleRateLimitError",
            "RateLimitError",
            "InternalServerError",
            "APITimeoutError",
            "APIConnectionError",
        ):
            return True
        if error_type_name in ("BadRequestError", "AuthenticationError", "PermissionDeniedError"):
            return False

        error_str = str(current)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            return True

    return is_retryable_gemini_error(error)


def create_chat_model(
    provider: str,
    model_name: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1200,
    timeout: float = 30.0,
) -> Any:
    """Create a LangChain chat model instance for the given provider."""
    if provider == PROVIDER_GEMINI:
        actual_model = model_name or GEMINI_PRIMARY_MODEL
        return ChatGoogleGenerativeAI(
            model=actual_model,
            google_api_key=load_gemini_api_key(),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            request_timeout=timeout,
            max_retries=0,
        )

    if provider == PROVIDER_GROQ:
        groq_key = load_groq_api_key()
        if not groq_key:
            raise LLMProviderError("GROQ_API_KEY is not configured in secrets.")

        actual_model = model_name or GROQ_PRIMARY_MODEL
        return ChatGroq(
            model=actual_model,
            groq_api_key=groq_key,
            temperature=temperature,
            max_tokens=max_output_tokens,
            request_timeout=timeout,
            max_retries=0,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


def generate_with_provider_failover(
    prompt: str,
    system_instruction: str | None = None,
    candidates: Sequence[tuple[str, str]] | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1200,
    gemini_timeout: float = 15.0,
    groq_timeout: float = 30.0,
) -> GenerationResult:
    """Generate text with automatic primary-to-secondary provider failover.

    Tries candidates in sequence. If a candidate fails with a retryable error,
    it records the failure and attempts the next candidate. If a non-retryable
    client error (400) occurs, it immediately raises LLMProviderError.
    """
    selected_candidates = list(candidates or DEFAULT_CANDIDATE_CHAIN)
    attempts: list[dict[str, Any]] = []

    prompt_messages: list[tuple[str, str]] = []
    if system_instruction:
        prompt_messages.append(("system", system_instruction))
    prompt_messages.append(("human", "{prompt}"))

    prompt_template = ChatPromptTemplate.from_messages(prompt_messages)

    for index, (provider, model_name) in enumerate(selected_candidates):
        start_time = time.perf_counter()
        timeout = gemini_timeout if provider == PROVIDER_GEMINI else groq_timeout

        # Check if provider credentials exist before trying
        if provider == PROVIDER_GROQ and not load_groq_api_key():
            attempts.append({
                "provider": provider,
                "model": model_name,
                "status": "skipped",
                "reason": "GROQ_API_KEY not configured",
            })
            continue

        try:
            model = create_chat_model(
                provider=provider,
                model_name=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                timeout=timeout,
            )

            chain = prompt_template | model | StrOutputParser()
            answer = chain.invoke({"prompt": prompt})

            elapsed = round(time.perf_counter() - start_time, 3)
            attempts.append({
                "provider": provider,
                "model": model_name,
                "status": "ok",
                "elapsed_seconds": elapsed,
            })

            return GenerationResult(
                answer=answer,
                model_name=model_name,
                provider=provider,
                elapsed_seconds=elapsed,
                attempts=attempts,
            )

        except Exception as exc:
            elapsed = round(time.perf_counter() - start_time, 3)
            error_msg = str(exc)
            sanitized_error = error_msg[:200]
            status_code = _extract_status_code(exc)

            attempts.append({
                "provider": provider,
                "model": model_name,
                "status": "failed",
                "elapsed_seconds": elapsed,
                "error_type": type(exc).__name__,
                "status_code": status_code,
                "sanitized_error": sanitized_error,
            })

            # Check retryability
            if not is_retryable_llm_error(exc):
                logger.error(
                    "Non-retryable client error on %s/%s: %s (code=%s)",
                    provider,
                    model_name,
                    sanitized_error,
                    status_code,
                )
                raise LLMProviderError(
                    f"Non-retryable client error on {provider}/{model_name}: {sanitized_error}"
                ) from exc

            logger.warning(
                "Retryable error on %s/%s after %.2fs (%s: %s); failing over to next candidate.",
                provider,
                model_name,
                elapsed,
                type(exc).__name__,
                sanitized_error,
            )

    # All candidates exhausted
    raise LLMProviderError(
        f"All LLM candidates exhausted. Attempts: {attempts}"
    )


def execute_tool_router_with_failover(
    retrieval_query: str,
    tools: list[Any],
    system_instruction: str,
    tool_model: Any | None = None,
    candidates: Sequence[tuple[str, str]] | None = None,
    gemini_timeout: float = 15.0,
    groq_timeout: float = 30.0,
) -> tuple[Any, str, str, list[dict[str, Any]]]:
    """Execute learner tool routing with automatic provider failover.

    Returns:
        tuple of (decision_ai_message, model_used, provider_used, attempts_log)
    """
    # If a custom mock model is injected (e.g. in tests), use it directly
    if tool_model is not None:
        model_with_tools = tool_model.bind_tools(tools)
        decision = model_with_tools.invoke(
            [
                SystemMessage(content=system_instruction),
                HumanMessage(content=retrieval_query),
            ]
        )
        return decision, "injected_tool_model", "test", []

    selected_candidates = list(candidates or DEFAULT_CANDIDATE_CHAIN)
    attempts: list[dict[str, Any]] = []

    for index, (provider, model_name) in enumerate(selected_candidates):
        start_time = time.perf_counter()
        timeout = gemini_timeout if provider == PROVIDER_GEMINI else groq_timeout

        if provider == PROVIDER_GROQ and not load_groq_api_key():
            attempts.append({
                "provider": provider,
                "model": model_name,
                "status": "skipped",
                "reason": "GROQ_API_KEY not configured",
            })
            continue

        try:
            chat_model = create_chat_model(
                provider=provider,
                model_name=model_name,
                temperature=0.0,
                max_output_tokens=1024,
                timeout=timeout,
            )
            model_with_tools = chat_model.bind_tools(tools)
            decision = model_with_tools.invoke(
                [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=retrieval_query),
                ]
            )

            elapsed = round(time.perf_counter() - start_time, 3)
            attempts.append({
                "provider": provider,
                "model": model_name,
                "status": "ok",
                "elapsed_seconds": elapsed,
            })
            return decision, model_name, provider, attempts

        except Exception as exc:
            elapsed = round(time.perf_counter() - start_time, 3)
            status_code = _extract_status_code(exc)
            sanitized_error = str(exc)[:200]

            attempts.append({
                "provider": provider,
                "model": model_name,
                "status": "failed",
                "elapsed_seconds": elapsed,
                "error_type": type(exc).__name__,
                "status_code": status_code,
                "sanitized_error": sanitized_error,
            })

            if not is_retryable_llm_error(exc):
                raise LLMProviderError(
                    f"Non-retryable error in tool routing on {provider}/{model_name}: {sanitized_error}"
                ) from exc

            logger.warning(
                "Tool router candidate %s/%s failed with retryable error (%s); trying next.",
                provider,
                model_name,
                type(exc).__name__,
            )

    raise LLMProviderError(
        f"All tool routing LLM candidates exhausted. Attempts: {attempts}"
    )
