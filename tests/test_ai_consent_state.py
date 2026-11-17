"""Automated tests for AI consent UI state, session lifecycle, and backend gating.

Verifies:
1. Database consent FALSE displays unchecked in the UI (even if stale state was present).
2. Database consent TRUE displays checked in the UI.
3. Logout and session clearing deletes consent widget keys from st.session_state.
4. Saving unrelated profile preferences does not grant AI consent.
5. Revoking consent sets ai_consent to FALSE and clears ai_consent_granted_at to NULL.
6. AI calls (Tutor Graph and Subjective Evaluation) remain strictly blocked when consent is FALSE.
7. Explicit user submission to grant consent properly persists True.
"""

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import streamlit as st

from app import clear_edupath_session
from ui.learner_profile import render_learner_profile
from services.learner_service import set_ai_consent
from agents.tutor_graph import run_tutor_graph
from services.subjective_evaluation_service import evaluate_subjective_explanation


class AIConsentUIStateTests(unittest.TestCase):
    """Test UI initialization, key stability, and session synchronization."""

    def setUp(self):
        self.user_id = str(uuid4())
        self.consent_key = f"edupath_ai_consent_{self.user_id}"
        self.sync_key = f"edupath_ai_consent_synced_db_{self.user_id}"
        self.learner = {
            "user_id": self.user_id,
            "display_name": "Test Learner",
            "proficiency_level": "beginner",
            "explanation_style": "step_by_step",
            "daily_study_minutes": 45,
            "preferred_language": "English",
            "learning_goal": "Learn Python",
            "adult_confirmation": True,
            "role": "student",
        }
        clear_edupath_session()

    def tearDown(self):
        clear_edupath_session()

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.st.checkbox")
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=False)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox")
    @patch("ui.learner_profile.st.slider")
    @patch("ui.learner_profile.st.text_input")
    @patch("ui.learner_profile.st.text_area")
    @patch("ui.learner_profile.render_page_header")
    def test_database_consent_false_displays_unchecked(
        self,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_get_profile,
    ):
        """Database consent FALSE must initialize checkbox to False, overriding any stale session state."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        mock_get_profile.return_value = {
            **self.learner,
            "ai_consent": False,
            "ai_consent_granted_at": None,
        }
        # Simulate stale True in session state from a previous session or glitch
        st.session_state[self.consent_key] = True

        render_learner_profile(self.learner)

        # Checkbox key in session_state must have been reset to False
        self.assertFalse(st.session_state[self.consent_key])
        self.assertFalse(st.session_state[self.sync_key])

        # st.checkbox must be called with value=False and the stable key
        mock_checkbox.assert_called_once()
        _, kwargs = mock_checkbox.call_args
        self.assertFalse(kwargs["value"])
        self.assertEqual(kwargs["key"], self.consent_key)

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.st.checkbox")
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=False)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox")
    @patch("ui.learner_profile.st.slider")
    @patch("ui.learner_profile.st.text_input")
    @patch("ui.learner_profile.st.text_area")
    @patch("ui.learner_profile.render_page_header")
    def test_database_consent_true_displays_checked(
        self,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_get_profile,
    ):
        """Database consent TRUE must initialize checkbox to True."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        mock_get_profile.return_value = {
            **self.learner,
            "ai_consent": True,
            "ai_consent_granted_at": "2026-11-14T10:00:00Z",
        }
        # Stale False in session state
        st.session_state[self.consent_key] = False

        render_learner_profile(self.learner)

        self.assertTrue(st.session_state[self.consent_key])
        self.assertTrue(st.session_state[self.sync_key])

        mock_checkbox.assert_called_once()
        _, kwargs = mock_checkbox.call_args
        self.assertTrue(kwargs["value"])
        self.assertEqual(kwargs["key"], self.consent_key)

    def test_logout_clears_consent_widget_state(self):
        """clear_edupath_session must purge all user-specific consent keys."""
        st.session_state[self.consent_key] = True
        st.session_state[self.sync_key] = True
        st.session_state["edupath_learner"] = self.learner
        st.session_state["unrelated_external_key"] = "keep_me"

        clear_edupath_session()

        self.assertNotIn(self.consent_key, st.session_state)
        self.assertNotIn(self.sync_key, st.session_state)
        self.assertNotIn("edupath_learner", st.session_state)
        self.assertIn("unrelated_external_key", st.session_state)

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.update_learner_profile")
    @patch("ui.learner_profile.set_ai_consent")
    @patch("ui.learner_profile.st.checkbox", return_value=False)
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=True)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox", side_effect=["intermediate", "step_by_step"])
    @patch("ui.learner_profile.st.slider", return_value=60)
    @patch("ui.learner_profile.st.text_input", return_value="English")
    @patch("ui.learner_profile.st.text_area", return_value="Goal")
    @patch("ui.learner_profile.render_page_header")
    @patch("ui.learner_profile.st.rerun")
    def test_saving_unrelated_preferences_does_not_grant_consent(
        self,
        mock_rerun,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_set_ai_consent,
        mock_update_profile,
        mock_get_profile,
    ):
        """Updating proficiency or study target with consent unchecked must persist consent=False."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        mock_get_profile.return_value = {
            **self.learner,
            "ai_consent": False,
            "ai_consent_granted_at": None,
        }
        mock_update_profile.return_value = {
            "proficiency_level": "intermediate",
            "daily_study_minutes": 60,
        }

        render_learner_profile(self.learner)

        # set_ai_consent must be called with False
        mock_set_ai_consent.assert_called_once_with(user_id=self.user_id, consent=False)
        self.assertFalse(self.learner.get("ai_consent"))
        self.assertFalse(st.session_state[self.consent_key])
        mock_rerun.assert_called_once()

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.update_learner_profile")
    @patch("ui.learner_profile.set_ai_consent")
    @patch("ui.learner_profile.st.checkbox", return_value=True)
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=True)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox", side_effect=["beginner", "step_by_step"])
    @patch("ui.learner_profile.st.slider", return_value=45)
    @patch("ui.learner_profile.st.text_input", return_value="English")
    @patch("ui.learner_profile.st.text_area", return_value="Goal")
    @patch("ui.learner_profile.render_page_header")
    @patch("ui.learner_profile.st.rerun")
    @patch("ui.learner_profile.st.success")
    def test_user_actively_granting_consent_persists_true(
        self,
        mock_success,
        mock_rerun,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_set_ai_consent,
        mock_update_profile,
        mock_get_profile,
    ):
        """When user checks the box and submits, consent=True is persisted and verified."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        # First call loads initial DB state (False); second call verifies reload from PostgreSQL (True)
        mock_get_profile.side_effect = [
            {**self.learner, "ai_consent": False, "ai_consent_granted_at": None},
            {**self.learner, "ai_consent": True, "ai_consent_granted_at": "2026-11-15T00:00:00Z"},
        ]
        mock_update_profile.return_value = {}

        render_learner_profile(self.learner)

        mock_set_ai_consent.assert_called_once_with(user_id=self.user_id, consent=True)
        self.assertTrue(self.learner.get("ai_consent"))
        self.assertTrue(st.session_state[self.sync_key])
        mock_success.assert_called_once()
        mock_rerun.assert_called_once()

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.update_learner_profile")
    @patch("ui.learner_profile.set_ai_consent")
    @patch("ui.learner_profile.st.checkbox", return_value=False)
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=True)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox", side_effect=["beginner", "step_by_step"])
    @patch("ui.learner_profile.st.slider", return_value=45)
    @patch("ui.learner_profile.st.text_input", return_value="English")
    @patch("ui.learner_profile.st.text_area", return_value="Goal")
    @patch("ui.learner_profile.render_page_header")
    @patch("ui.learner_profile.st.rerun")
    @patch("ui.learner_profile.st.success")
    def test_user_actively_revoking_consent_persists_false(
        self,
        mock_success,
        mock_rerun,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_set_ai_consent,
        mock_update_profile,
        mock_get_profile,
    ):
        """When user unchecks the box and submits, consent=False is persisted and timestamp cleared."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        # First call loads initial DB state (True); second call verifies reload from PostgreSQL (False)
        mock_get_profile.side_effect = [
            {**self.learner, "ai_consent": True, "ai_consent_granted_at": "2026-11-14T00:00:00Z"},
            {**self.learner, "ai_consent": False, "ai_consent_granted_at": None},
        ]
        mock_update_profile.return_value = {}

        render_learner_profile(self.learner)

        mock_set_ai_consent.assert_called_once_with(user_id=self.user_id, consent=False)
        self.assertFalse(self.learner.get("ai_consent"))
        self.assertFalse(st.session_state[self.sync_key])
        mock_success.assert_called_once()
        mock_rerun.assert_called_once()

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.update_learner_profile")
    @patch("ui.learner_profile.set_ai_consent")
    @patch("ui.learner_profile.st.checkbox", return_value=True)
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=True)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox", side_effect=["advanced", "example_first"])
    @patch("ui.learner_profile.st.slider", return_value=90)
    @patch("ui.learner_profile.st.text_input", return_value="English")
    @patch("ui.learner_profile.st.text_area", return_value="Goal")
    @patch("ui.learner_profile.render_page_header")
    @patch("ui.learner_profile.st.rerun")
    @patch("ui.learner_profile.st.success")
    def test_profile_save_without_consent_changes(
        self,
        mock_success,
        mock_rerun,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_set_ai_consent,
        mock_update_profile,
        mock_get_profile,
    ):
        """Saving profile changes with unchanged consent updates preferences without altering consent."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        profile_data = {
            **self.learner,
            "ai_consent": True,
            "ai_consent_granted_at": "2026-11-14T10:00:00Z",
            "proficiency_level": "beginner",
            "daily_study_minutes": 45,
        }
        mock_get_profile.side_effect = [
            profile_data,
            {**profile_data, "proficiency_level": "advanced", "daily_study_minutes": 90},
        ]
        mock_update_profile.return_value = {
            "proficiency_level": "advanced",
            "daily_study_minutes": 90,
        }

        render_learner_profile(self.learner)

        mock_set_ai_consent.assert_called_once_with(user_id=self.user_id, consent=True)
        self.assertEqual(self.learner.get("proficiency_level"), "advanced")
        self.assertEqual(self.learner.get("daily_study_minutes"), 90)
        self.assertTrue(self.learner.get("ai_consent"))
        mock_success.assert_called_once()
        mock_rerun.assert_called_once()

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.update_learner_profile")
    @patch("ui.learner_profile.set_ai_consent")
    @patch("ui.learner_profile.st.checkbox", return_value=True)
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=True)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox", side_effect=["beginner", "step_by_step"])
    @patch("ui.learner_profile.st.slider", return_value=45)
    @patch("ui.learner_profile.st.text_input", return_value="English")
    @patch("ui.learner_profile.st.text_area", return_value="Goal")
    @patch("ui.learner_profile.render_page_header")
    @patch("ui.learner_profile.st.error")
    @patch("ui.learner_profile.st.success")
    @patch("ui.learner_profile.st.rerun")
    def test_database_update_verification_failure_shows_error(
        self,
        mock_rerun,
        mock_success,
        mock_error,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_checkbox,
        mock_set_ai_consent,
        mock_update_profile,
        mock_get_profile,
    ):
        """If reloaded database profile does not match saved consent, show error and never show success."""
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        # Both calls return False, simulating an update failure or rollback
        mock_get_profile.return_value = {
            **self.learner,
            "ai_consent": False,
            "ai_consent_granted_at": None,
        }
        mock_update_profile.return_value = {}

        render_learner_profile(self.learner)

        mock_set_ai_consent.assert_called_once_with(user_id=self.user_id, consent=True)
        mock_error.assert_called_once()
        self.assertIn("could not be verified", mock_error.call_args.args[0].lower())
        mock_success.assert_not_called()
        mock_rerun.assert_not_called()

    @patch("ui.learner_profile.get_learner_profile")
    @patch("ui.learner_profile.update_learner_profile")
    @patch("ui.learner_profile.set_ai_consent")
    @patch("ui.learner_profile.st.form")
    @patch("ui.learner_profile.st.form_submit_button", return_value=True)
    @patch("ui.learner_profile.st.columns")
    @patch("ui.learner_profile.st.selectbox", side_effect=["beginner", "step_by_step"])
    @patch("ui.learner_profile.st.slider", return_value=45)
    @patch("ui.learner_profile.st.text_input", return_value="English")
    @patch("ui.learner_profile.st.text_area", return_value="Goal")
    @patch("ui.learner_profile.render_page_header")
    @patch("ui.learner_profile.st.rerun")
    @patch("ui.learner_profile.st.success")
    def test_checkbox_submission_does_not_mutate_instantiated_widget_key(
        self,
        mock_success,
        mock_rerun,
        mock_header,
        mock_textarea,
        mock_textinput,
        mock_slider,
        mock_selectbox,
        mock_columns,
        mock_submit,
        mock_form,
        mock_set_ai_consent,
        mock_update_profile,
        mock_get_profile,
    ):
        """Verify that after checkbox instantiation, st.session_state[consent_key] is not modified.

        In Streamlit, modifying st.session_state[key] after the widget with that key is
        instantiated raises StreamlitWidgetAlreadyInstantiatedError.
        """
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_form.return_value.__enter__.return_value = MagicMock()
        mock_get_profile.side_effect = [
            {**self.learner, "ai_consent": False, "ai_consent_granted_at": None},
            {**self.learner, "ai_consent": True, "ai_consent_granted_at": "2026-11-15T00:00:00Z"},
        ]
        mock_update_profile.return_value = {}

        # Wrap st.session_state.__setitem__ to detect if consent_key is written to after checkbox instantiation
        widget_instantiated = False
        forbidden_write_detected = False

        original_setitem = st.session_state.__class__.__setitem__

        def tracking_setitem(key, value):
            nonlocal forbidden_write_detected
            if widget_instantiated and key == self.consent_key:
                forbidden_write_detected = True
            return original_setitem(st.session_state, key, value)

        def mock_checkbox_impl(*args, **kwargs):
            nonlocal widget_instantiated
            widget_instantiated = True
            return True

        with patch.object(st.session_state.__class__, "__setitem__", side_effect=tracking_setitem):
            with patch("ui.learner_profile.st.checkbox", side_effect=mock_checkbox_impl):
                render_learner_profile(self.learner)

        self.assertFalse(
            forbidden_write_detected,
            "st.session_state[consent_key] was modified after widget instantiation, which triggers StreamlitWidgetAlreadyInstantiatedError",
        )
        mock_success.assert_called_once()


class AIConsentDatabaseAndGatingTests(unittest.TestCase):
    """Test database persistence semantics, timestamp clearing, and strict AI gating."""

    def setUp(self):
        self.user_id = uuid4()
        self.thread_id = str(uuid4())

    def test_revocation_clears_the_consent_timestamp(self):
        """set_ai_consent(user_id, False) sets ai_consent=False and clears granted timestamp."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",)]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            set_ai_consent(str(self.user_id), False)

            self.assertEqual(cursor.execute.call_count, 2)
            update_sql = cursor.execute.call_args_list[1].args[0]
            params = cursor.execute.call_args_list[1].args[1]

            self.assertIn("ai_consent = %s", update_sql)
            self.assertIn("ai_consent_granted_at = CASE WHEN %s THEN NOW() ELSE NULL END", update_sql)
            # Both consent and the CASE condition must be False, clearing timestamp to NULL
            self.assertEqual(params, (False, False, self.user_id))

    def test_tutor_graph_blocked_when_consent_is_false(self):
        """run_tutor_graph must raise PermissionError and never invoke Gemini/Groq when consent is False in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work in Python?",
                    course_slug="python-basics",
                    user_id=str(self.user_id),
                    session_id=self.thread_id,
                    ai_consent=True,  # Caller-supplied True is safely overridden by DB check
                )
            self.assertIn("affirmative consent", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_subjective_evaluation_blocked_when_consent_is_false(self):
        """evaluate_subjective_explanation must bypass Gemini and fall back to deterministic when consent is False."""
        with patch(
            "services.subjective_evaluation_service.evaluate_subjective_explanation_gemini"
        ) as mock_gemini, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            result = evaluate_subjective_explanation(
                question="Why is range(1, 5) stopping at 4?",
                reference_answer="In Python range(start, stop) the stop value is exclusive.",
                student_explanation="range(1, 5) generates 1, 2, 3, 4, but not 5.",
                topic_slug="loops",
                user_id=str(self.user_id),
                ai_consent=True,  # Caller-supplied True is safely overridden by DB check
                adult_confirmation=True,
                use_ai=True,
            )
            mock_gemini.assert_not_called()
            self.assertEqual(result["evaluator_type"], "deterministic_fallback")
            self.assertIn("consent", result.get("fallback_reason", "").lower())


if __name__ == "__main__":
    unittest.main()
