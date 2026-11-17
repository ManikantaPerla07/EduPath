"""Learner profile viewing and editing UI for EduPath."""

import streamlit as st
import psycopg

from services.learner_service import (
    get_learner_profile,
    update_learner_profile,
    set_ai_consent,
    delete_learner_account,
    VALID_PROFICIENCY_LEVELS,
    VALID_EXPLANATION_STYLES,
)
from ui.theme import render_page_header


def render_learner_profile(learner: dict) -> None:
    """Render the learner's profile and interactive preference management."""

    render_page_header(
        "MY ACCOUNT",
        "Learner Profile",
        "Customize your learning experience, proficiency level, study schedule, and explanation preferences.",
    )

    user_id = str(learner["user_id"])

    try:
        current_profile = get_learner_profile(user_id)
    except Exception:
        current_profile = learner

    db_consent = bool(current_profile.get("ai_consent", False))
    consent_key = f"edupath_ai_consent_{user_id}"
    sync_key = f"edupath_ai_consent_synced_db_{user_id}"

    # Initialize or synchronize session state from authoritative database value
    # whenever entering the profile or if the database state changes.
    if sync_key not in st.session_state or st.session_state.get(sync_key) != db_consent:
        st.session_state[consent_key] = db_consent
        st.session_state[sync_key] = db_consent

    proficiency = current_profile.get("proficiency_level") or "beginner"
    explanation_style = current_profile.get("explanation_style") or "step_by_step"
    daily_minutes = int(current_profile.get("daily_study_minutes") or 45)
    preferred_lang = current_profile.get("preferred_language") or "English"
    learning_goal = current_profile.get("learning_goal") or ""

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Level", proficiency.title())
    col2.metric("Daily Target", f"{daily_minutes} mins")
    col3.metric("Style", explanation_style.replace("_", " ").title())

    st.divider()
    st.subheader("Edit Learning Preferences")
    st.caption("EduPath adapts tutor explanations, assessment difficulty, and study plans based on these settings.")

    proficiency_options = ["beginner", "intermediate", "advanced"]
    explanation_options = ["simple", "step_by_step", "example_first"]

    prof_index = proficiency_options.index(proficiency) if proficiency in proficiency_options else 0
    expl_index = explanation_options.index(explanation_style) if explanation_style in explanation_options else 1

    with st.form("edupath_learner_profile_form"):
        new_prof = st.selectbox(
            "Proficiency Level",
            options=proficiency_options,
            index=prof_index,
            format_func=lambda x: {
                "beginner": "Beginner — Simple analogies, gentle pace, core concepts",
                "intermediate": "Intermediate — Code-first, step-by-step logic, common errors",
                "advanced": "Advanced — Deep reasoning, edge cases, algorithmic challenges",
            }.get(x, x.title()),
            help="Determines the default explanation depth and question difficulty.",
        )

        new_style = st.selectbox(
            "Preferred Explanation Style",
            options=explanation_options,
            index=expl_index,
            format_func=lambda x: {
                "simple": "Simple — Straightforward, analogy-focused, accessible",
                "step_by_step": "Step by Step — Structured walkthroughs, numbered steps",
                "example_first": "Example First — Worked code snippet before conceptual theory",
            }.get(x, x.title()),
            help="Shapes how the AI Tutor constructs explanations.",
        )

        new_minutes = st.slider(
            "Daily Study Availability (minutes)",
            min_value=10,
            max_value=180,
            value=min(max(daily_minutes, 10), 180),
            step=5,
            help="Used to schedule activities across your personalized study plan.",
        )

        new_language = st.text_input(
            "Preferred Language",
            value=preferred_lang,
            max_chars=50,
            help="Language in which you prefer explanations.",
        )

        new_goal = st.text_area(
            "Learning Goal",
            value=learning_goal,
            max_chars=500,
            placeholder="e.g., Master Python loops and functions for college exams and build small automation scripts.",
            help="Keywords from your goal help prioritize relevant study plan topics.",
        )

        st.markdown("#### Generative AI Privacy Notice & Consent")
        st.caption(
            "EduPath uses Google Gemini (primary) and Groq (secondary failover) to answer questions and evaluate practice responses. "
            "Under Google's unpaid API terms, prompts may be reviewed and used to train Google models; Groq does not train on customer inputs but may retain logs up to 30 days for safety. "
            "Your email address, personal name, and credentials are **never transmitted** to any provider. "
            "To preserve Python code syntax and decorators without automated regex disruption, "
            "never enter real passwords, API keys, phone numbers, or sensitive personal data into tutor prompts."
        )
        ai_consent_val = st.checkbox(
            "I consent to processing my educational questions with Generative AI (Google Gemini & Groq failover)",
            value=bool(st.session_state.get(consent_key, db_consent)),
            key=consent_key,
            help="Declining AI consent restricts tutoring features while preserving access to assessments, learning analytics, learning resources, and study materials.",
        )

        submitted = st.form_submit_button(
            "Save Profile Changes",
            type="primary",
            width="stretch",
        )

    if submitted:
        try:
            updated = update_learner_profile(
                user_id=user_id,
                proficiency_level=new_prof,
                explanation_style=new_style,
                daily_study_minutes=new_minutes,
                preferred_language=new_language,
                learning_goal=new_goal,
            )
            consent_to_persist = bool(ai_consent_val)
            set_ai_consent(user_id=user_id, consent=consent_to_persist)

            # Reload fresh profile directly from PostgreSQL to verify persistence
            fresh_profile = get_learner_profile(user_id)
            persisted_consent = bool(fresh_profile.get("ai_consent", False))
            if persisted_consent != consent_to_persist:
                raise RuntimeError("Consent update could not be verified in the database.")

            # Update cached session state (never modify widget key consent_key during this run!)
            for key in ("proficiency_level", "explanation_style", "daily_study_minutes", "preferred_language", "learning_goal"):
                if key in updated:
                    learner[key] = updated[key]
            learner["ai_consent"] = persisted_consent
            st.session_state["edupath_learner"] = learner
            st.session_state[sync_key] = persisted_consent

            st.success("Your learning preferences have been saved successfully!")
            st.rerun()

        except (ValueError, PermissionError, RuntimeError) as exc:
            st.error(str(exc))
        except psycopg.Error:
            st.error("Could not save your preferences due to a database error. Please try again.")

    st.divider()
    with st.expander("⚠️ Account Data & Privacy Controls", expanded=False):
        st.markdown("#### Permanent Account Deletion")
        st.write(
            "Permanently delete your EduPath account and all associated data, including "
            "saved profile preferences, assessment attempts, mastery scores, study plans, "
            "chat sessions, and formative misconception records. This action is irreversible."
        )
        confirm_text = st.text_input(
            "Type DELETE to confirm permanent account deletion:",
            key="edupath_delete_account_input",
        )
        if st.button("Permanently Delete My EduPath Account", type="primary", key="edupath_delete_account_btn"):
            if confirm_text.strip() == "DELETE":
                try:
                    deleted = delete_learner_account(user_id)
                    if deleted:
                        st.session_state.clear()
                        st.success("Your account and all associated data have been permanently deleted.")
                        st.rerun()
                    else:
                        st.error("Unable to delete account. Please try again.")
                except Exception as exc:
                    st.error(f"Error during account deletion: {exc}")
            else:
                st.warning("Please type 'DELETE' in all capital letters to confirm account deletion.")
