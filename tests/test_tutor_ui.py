"""Tests for rate-limit handling in the authenticated Tutor UI."""

import unittest
from unittest.mock import patch

from services.chat_service import ChatRateLimitError
from services.agent_telemetry_service import AgentRunAlreadyActiveError
from ui.tutor import _process_question


USER_ID = "11111111-1111-4111-8111-111111111111"
SESSION_ID = "22222222-2222-4222-8222-222222222222"


class TutorRateLimitUITests(unittest.TestCase):

    @patch("ui.tutor.run_tutor_graph")
    @patch("ui.tutor.st.warning")
    @patch("ui.tutor.save_chat_message")
    @patch("ui.tutor.get_chat_messages", return_value=[])
    @patch("ui.tutor.run_tutor_graph")
    @patch("ui.tutor.st.warning")
    @patch("ui.tutor.save_chat_message")
    @patch("ui.tutor.get_chat_messages", return_value=[])
    def test_active_conversation_warning_is_displayed(
        self,
        get_messages,
        save_message,
        show_warning,
        run_graph,
    ):
        run_graph.side_effect = AgentRunAlreadyActiveError(
            "A response is already being generated for this conversation."
        )

        _process_question(
            user_id=USER_ID,
            session_id=SESSION_ID,
            question="Explain Python lists.",
        )

        self.assertEqual(save_message.call_count, 1)
        self.assertEqual(save_message.call_args.kwargs["role"], "user")
        show_warning.assert_called_once()
        self.assertIn(
            "already being generated",
            show_warning.call_args.args[0],
        )
        run_graph.assert_called_once()
        get_messages.assert_called_once()

    def test_rate_limit_is_displayed_without_calling_model(
        self,
        get_messages,
        save_message,
        show_warning,
        run_graph,
    ):
        save_message.side_effect = ChatRateLimitError(85)

        _process_question(
            user_id=USER_ID,
            session_id=SESSION_ID,
            question="Explain Python variables.",
        )

        show_warning.assert_called_once()
        self.assertIn(
            "20 questions every 10 minutes",
            show_warning.call_args.args[0],
        )
        get_messages.assert_called_once()
        save_message.assert_called_once()
        run_graph.assert_not_called()


if __name__ == "__main__":
    unittest.main()
