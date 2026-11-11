"""Tests for classifying retryable Gemini failures."""

import unittest

from services.gemini_error_utils import (
    RETRYABLE_GEMINI_STATUS_CODES,
    is_retryable_gemini_error,
)


class GeminiErrorClassificationTests(unittest.TestCase):

    def test_retryable_server_status_codes_are_recognized(self):
        for status_code in RETRYABLE_GEMINI_STATUS_CODES:
            with self.subTest(status_code=status_code):
                error = RuntimeError("Temporary server failure")
                error.code = status_code
                self.assertTrue(is_retryable_gemini_error(error))

    def test_status_code_attribute_is_supported(self):
        error = RuntimeError("Temporary server failure")
        error.status_code = 503

        self.assertTrue(is_retryable_gemini_error(error))

    def test_response_status_code_is_supported(self):
        error = RuntimeError("Temporary server failure")
        error.response = type(
            "Response",
            (),
            {"status_code": 504},
        )()

        self.assertTrue(is_retryable_gemini_error(error))

    def test_retryable_status_in_cause_chain_is_recognized(self):
        underlying = RuntimeError("Service unavailable")
        underlying.code = 503

        try:
            raise underlying
        except RuntimeError as cause:
            try:
                raise RuntimeError("SDK wrapper") from cause
            except RuntimeError as wrapped:
                self.assertTrue(is_retryable_gemini_error(wrapped))

    def test_http_transport_interruption_is_recognized(self):
        remote_protocol_error = type(
            "RemoteProtocolError",
            (Exception,),
            {"__module__": "httpx"},
        )

        self.assertTrue(
            is_retryable_gemini_error(
                remote_protocol_error("Server disconnected")
            )
        )

    def test_nested_http_transport_interruption_is_recognized(self):
        remote_protocol_error = type(
            "RemoteProtocolError",
            (Exception,),
            {"__module__": "httpcore2"},
        )

        try:
            raise remote_protocol_error("Server disconnected")
        except Exception as cause:
            try:
                raise RuntimeError("SDK wrapper") from cause
            except RuntimeError as wrapped:
                self.assertTrue(is_retryable_gemini_error(wrapped))

    def test_client_errors_are_not_retryable(self):
        for status_code in (400, 401, 403, 404, 429):
            with self.subTest(status_code=status_code):
                error = RuntimeError("Client error")
                error.code = status_code
                self.assertFalse(is_retryable_gemini_error(error))

    def test_unclassified_errors_are_not_retryable(self):
        self.assertFalse(
            is_retryable_gemini_error(
                RuntimeError("Invalid model configuration")
            )
        )


if __name__ == "__main__":
    unittest.main()
