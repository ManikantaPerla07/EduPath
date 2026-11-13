"""Learner profile viewing and editing UI for EduPath."""

import streamlit as st
import psycopg

from services.learner_service import (
    get_learner_profile,
    update_learner_profile,
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

            # Update cached session state
            for key in ("proficiency_level", "explanation_style", "daily_study_minutes", "preferred_language", "learning_goal"):
                if key in updated:
                    learner[key] = updated[key]
            st.session_state["edupath_learner"] = learner

            st.success("Your learning preferences have been saved successfully!")
            st.rerun()

        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
        except psycopg.Error:
            st.error("Could not save your preferences due to a database error. Please try again.")
