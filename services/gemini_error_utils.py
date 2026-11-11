"""Shared classification for transient Gemini API failures."""

from collections.abc import Iterator
from typing import Any


RETRYABLE_GEMINI_STATUS_CODES = frozenset({500, 502, 503, 504})

_RETRYABLE_TRANSPORT_ERROR_NAMES = frozenset({
    "ConnectError",
    "ConnectTimeout",
    "NetworkError",
    "PoolTimeout",
    "ProtocolError",
    "ReadError",
    "ReadTimeout",
    "RemoteProtocolError",
    "TimeoutException",
    "TransportError",
    "WriteError",
    "WriteTimeout",
})
_HTTP_TRANSPORT_MODULES = frozenset({
    "httpcore",
    "httpcore2",
    "httpx",
    "httpx2",
})


def _exception_chain(error: BaseException) -> Iterator[BaseException]:
    """Yield an exception and its causal/context chain without duplicates."""

    pending = [error]
    visited: set[int] = set()

    while pending:
        current = pending.pop(0)

        if id(current) in visited:
            continue

        visited.add(id(current))
        yield current

        cause = current.__cause__
        context = current.__context__

        if cause is not None:
            pending.append(cause)

        if context is not None:
            pending.append(context)


def _status_code(error: BaseException) -> int | None:
    """Extract an HTTP status exposed by common SDK exception shapes."""

    for attribute in ("code", "status_code"):
        value: Any = getattr(error, attribute, None)

        if isinstance(value, int) and not isinstance(value, bool):
            return value

    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)

    if isinstance(value, int) and not isinstance(value, bool):
        return value

    return None


def is_retryable_gemini_error(error: BaseException) -> bool:
    """Return whether a Gemini failure is safe to retry on a fallback model.

    Temporary server responses and recognized HTTP transport interruptions
    are retryable. Authentication, permission, invalid-request, and other
    client-side errors are deliberately not retryable.
    """

    for current in _exception_chain(error):
        if _status_code(current) in RETRYABLE_GEMINI_STATUS_CODES:
            return True

        module_root = type(current).__module__.split(".", maxsplit=1)[0]
        if (
            module_root in _HTTP_TRANSPORT_MODULES
            and type(current).__name__ in _RETRYABLE_TRANSPORT_ERROR_NAMES
        ):
            return True

    return False
