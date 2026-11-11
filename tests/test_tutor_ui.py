"""Tests for request-limit and concurrent-run handling in the Tutor UI."""

import unittest
from unittest.mock import patch

from services.agent_telemetry_service import AgentRunAlreadyActiveError
from services.chat_service import ChatRateLimitError, ChatSessionBusyError
from ui.tutor import _process_question, _render_conversation_settings


USER_ID = "11111111-1111-4111-8111-111111111111"
SESSION_ID = "22222222-2222-4222-8222-222222222222"


class TutorRequestProtectionUITests(unittest.TestCase):

    @patch("ui.tutor.run_tutor_graph")
    @patch("ui.tutor.st.warning")
    @patch("ui.tutor.save_chat_message")
    @patch("ui.tutor.get_chat_messages", return_value=[])
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


class TutorConversationDeletionUITests(unittest.TestCase):

    @patch("ui.tutor.st.error")
    @patch("ui.tutor.st.warning")
    @patch("ui.tutor.delete_chat_session")
    @patch("ui.tutor.st.button", return_value=True)
    @patch("ui.tutor.st.checkbox", return_value=True)
    @patch("ui.tutor.st.form_submit_button", return_value=False)
    @patch("ui.tutor.st.form")
    @patch("ui.tutor.st.expander")
    def test_active_run_displays_warning_and_keeps_conversation(
        self,
        mock_expander,
        mock_form,
        mock_form_submit,
        mock_checkbox,
        mock_button,
        mock_delete,
        show_warning,
        show_error,
    ):
        mock_delete.side_effect = ChatSessionBusyError(
            "This conversation is currently generating a response. "
            "Wait for the response to finish before deleting it."
        )

        _render_conversation_settings(
            user_id=USER_ID,
            session={
                "session_id": SESSION_ID,
                "title": "Python variables",
            },
        )

        mock_delete.assert_called_once_with(
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        show_warning.assert_called_once()
        self.assertIn(
            "currently generating a response",
            show_warning.call_args.args[0],
        )
        show_error.assert_not_called()



if __name__ == "__main__":
    unittest.main()
