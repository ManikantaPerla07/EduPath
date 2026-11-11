"""Tests for the AI Tutor answer-feedback interface."""

import unittest
from unittest.mock import patch

from ui import tutor


MESSAGE_ID = "33333333-3333-4333-8333-333333333333"
USER_ID = "ea181992-f802-4528-ae24-10b7e198d8a2"


class TutorFeedbackUITests(unittest.TestCase):

    def test_positive_feedback_is_saved(self):
        message = {
            "message_id": MESSAGE_ID,
            "role": "assistant",
            "feedback": None,
        }

        with (
            patch.object(tutor.st, "session_state", {}),
            patch.object(tutor.st, "feedback", return_value=1),
            patch.object(tutor.st, "caption"),
            patch("ui.tutor.save_chat_feedback") as save_feedback,
        ):
            tutor._render_message_feedback(USER_ID, message)

        save_feedback.assert_called_once_with(
            user_id=USER_ID,
            message_id=MESSAGE_ID,
            is_helpful=True,
        )
        self.assertIs(message["feedback"], True)

    def test_zero_rating_is_saved_as_negative_feedback(self):
        message = {
            "message_id": MESSAGE_ID,
            "role": "assistant",
            "feedback": None,
        }

        with (
            patch.object(tutor.st, "session_state", {}),
            patch.object(tutor.st, "feedback", return_value=0),
            patch.object(tutor.st, "caption"),
            patch("ui.tutor.save_chat_feedback") as save_feedback,
        ):
            tutor._render_message_feedback(USER_ID, message)

        save_feedback.assert_called_once_with(
            user_id=USER_ID,
            message_id=MESSAGE_ID,
            is_helpful=False,
        )
        self.assertIs(message["feedback"], False)

    def test_existing_rating_is_restored_without_duplicate_write(self):
        message = {
            "message_id": MESSAGE_ID,
            "role": "assistant",
            "feedback": False,
        }
        state = {}

        with (
            patch.object(tutor.st, "session_state", state),
            patch.object(tutor.st, "feedback", return_value=0),
            patch.object(tutor.st, "caption"),
            patch("ui.tutor.save_chat_feedback") as save_feedback,
        ):
            tutor._render_message_feedback(USER_ID, message)

        self.assertEqual(
            state[f"edupath_tutor_feedback_{MESSAGE_ID}"],
            0,
        )
        save_feedback.assert_not_called()

    def test_changed_rating_updates_previous_feedback(self):
        message = {
            "message_id": MESSAGE_ID,
            "role": "assistant",
            "feedback": False,
        }
        state = {f"edupath_tutor_feedback_{MESSAGE_ID}": 0}

        with (
            patch.object(tutor.st, "session_state", state),
            patch.object(tutor.st, "feedback", return_value=1),
            patch.object(tutor.st, "caption"),
            patch("ui.tutor.save_chat_feedback") as save_feedback,
        ):
            tutor._render_message_feedback(USER_ID, message)

        save_feedback.assert_called_once_with(
            user_id=USER_ID,
            message_id=MESSAGE_ID,
            is_helpful=True,
        )
        self.assertIs(message["feedback"], True)

    def test_non_assistant_message_does_not_render_feedback(self):
        message = {
            "message_id": MESSAGE_ID,
            "role": "user",
            "feedback": None,
        }

        with patch.object(tutor.st, "feedback") as feedback_widget:
            tutor._render_message_feedback(USER_ID, message)

        feedback_widget.assert_not_called()


if __name__ == "__main__":
    unittest.main()
