import math
import time

import psycopg
import streamlit as st

from services.learner_service import (
    get_or_create_learner,
    confirm_adult_status,
)
from services.progress_service import fetch_learner_topic_progress
from services.course_service import is_course_published
from ui.assessment import render_assessment
from ui.study_plan import render_study_plan
from ui.tutor import render_tutor
from ui.knowledge_management import render_knowledge_management


st.set_page_config(
    page_title="EduPath | Personalized Tutoring",
    page_icon="🎓",
    layout="centered",
)


class GoogleSessionExpired(Exception):
    """Raised when the Google identity token has expired."""


def login_screen():
    """Display the Google login screen."""

    st.title("🎓 EduPath")
    st.subheader("Your Personalized Tutoring Agent")

    st.write(
        "Learn Python step by step with personalized explanations, "
        "assessments, and study guidance."
    )

    st.divider()
    st.info("Sign in with your Google account to continue.")

    st.button(
        "Continue with Google",
        on_click=st.login,
        type="primary",
        use_container_width=True,
    )


def get_authenticated_google_claims():
    """Validate Google token timestamps and return required identity claims."""

    issued_at = st.user.get("iat")
    expires_at = st.user.get("exp")
    valid_timestamp_types = (int, float)

    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, valid_timestamp_types)
        or not math.isfinite(issued_at)
    ):
        raise ValueError("Invalid Google identity token.")

    if (
        isinstance(expires_at, bool)
        or not isinstance(expires_at, valid_timestamp_types)
        or not math.isfinite(expires_at)
    ):
        raise ValueError("Invalid Google identity token.")

    current_time = time.time()

    if expires_at <= issued_at:
        raise ValueError("Invalid Google token timestamps.")

    if issued_at > current_time + 60:
        raise ValueError("Invalid Google token issuance time.")

    if expires_at <= current_time:
        raise GoogleSessionExpired

    # Only pass the identity fields required by the learner service.
    return {
        "iss": st.user.get("iss"),
        "sub": st.user.get("sub"),
        "email": st.user.get("email"),
        "email_verified": st.user.get("email_verified", False),
        "name": st.user.get("name"),
    }


def clear_edupath_session():
    """Clear EduPath-specific session data."""

    for key in list(st.session_state.keys()):
        if key.startswith("edupath_"):
            del st.session_state[key]


def logout_user():
    """Clear learner data before signing out of Google."""

    clear_edupath_session()
    st.logout()


def load_authenticated_learner():
    """Load and cache the authenticated learner for up to 60 seconds."""

    try:
        claims = get_authenticated_google_claims()
        identity_key = (claims["iss"], claims["sub"])

        # Clear previous learner data if another Google account signs in.
        stored_identity = st.session_state.get("edupath_google_identity")

        if stored_identity != identity_key:
            clear_edupath_session()
            st.session_state["edupath_google_identity"] = identity_key

        cached_learner = st.session_state.get("edupath_learner")
        cached_at = st.session_state.get("edupath_learner_cached_at")

        if (
            cached_learner is not None
            and cached_at is not None
            and time.monotonic() - cached_at < 60
        ):
            return cached_learner

        learner = get_or_create_learner(claims)
        st.session_state["edupath_learner"] = learner
        st.session_state["edupath_learner_cached_at"] = time.monotonic()

        return learner

    except GoogleSessionExpired:
        st.warning(
            "Your Google sign-in session has expired. "
            "Please sign in again."
        )
        st.button(
            "Sign out and sign in again",
            on_click=logout_user,
        )
        st.stop()

    except PermissionError as error:
        st.error(str(error))
        st.button("Sign out", on_click=logout_user)
        st.stop()

    except (ValueError, RuntimeError):
        st.error(
            "We could not verify your Google identity or load "
            "your learner account. Please sign out and try again."
        )
        st.button("Sign out", on_click=logout_user)
        st.stop()

    except psycopg.Error:
        st.error(
            "We could not connect to your learner account. "
            "Please try again."
        )
        if st.button("Retry"):
            st.rerun()
        st.button("Sign out", on_click=logout_user)
        st.stop()


def adult_confirmation_screen(learner):
    """Request explicit confirmation that the learner is at least 18."""

    st.title("🎓 Welcome to EduPath!")
    learner_name = learner["display_name"] or "Learner"
    st.subheader(f"Hello, {learner_name}!")

    st.write(
        "Before continuing, please confirm that you meet "
        "EduPath's age requirement."
    )
    st.info(
        "EduPath currently supports learners who are "
        "18 years of age or older."
    )

    with st.form("adult_confirmation_form"):
        confirmed = st.checkbox(
            "I confirm that I am 18 years of age or older."
        )
        submitted = st.form_submit_button(
            "Continue to EduPath",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not confirmed:
            st.error(
                "You must confirm that you are at least 18 "
                "to continue."
            )
        else:
            try:
                confirm_adult_status(learner["user_id"])

                # Reload the learner so the saved confirmation is reflected.
                st.session_state.pop("edupath_learner", None)
                st.session_state.pop("edupath_learner_cached_at", None)

                st.success("Age confirmation saved successfully.")
                st.rerun()

            except (ValueError, psycopg.Error):
                st.error(
                    "We could not save your confirmation. "
                    "Please try again."
                )

    st.divider()
    st.button(
        "Sign out",
        on_click=logout_user,
        use_container_width=True,
    )


def navigate_to_assessment():
    """Navigate to the Python assessment page."""

    st.session_state["edupath_navigation"] = "Python Assessment"


def navigate_to_study_plan():
    """Navigate to the personalized study-plan page."""

    st.session_state["edupath_navigation"] = "Study Plan"


def _format_mastery_status(status):
    """Convert the stored progress status into a readable label."""

    labels = {
        "not_assessed": "Not assessed",
        "needs_revision": "Needs revision",
        "developing": "Developing",
        "candidate_for_mastery": "Candidate for mastery",
    }

    return labels.get(status, "Unknown status")


def render_learning_progress(learner):
    """Display the authenticated learner's progress across Python topics."""

    st.header("Your Python topic progress")
    st.caption(
        "Progress is based on submitted assessments. Unanswered questions "
        "are not counted as attempts."
    )

    try:
        topic_progress = fetch_learner_topic_progress(
            user_id=str(learner["user_id"]),
            course_slug="python-basics",
        )
    except (ValueError, RuntimeError, psycopg.Error):
        st.error(
            "We could not load your topic progress right now. "
            "Please refresh the page and try again."
        )
        return

    if not topic_progress:
        st.info(
            "Your topic progress will appear here after your first "
            "submitted assessment."
        )
        return

    total_attempts = sum(
        int(topic.get("total_attempts") or 0)
        for topic in topic_progress
    )
    total_correct = sum(
        int(topic.get("correct_answers") or 0)
        for topic in topic_progress
    )
    assessed_topics = sum(
        int(topic.get("total_attempts") or 0) > 0
        for topic in topic_progress
    )
    candidate_topics = sum(
        topic.get("mastery_status") == "candidate_for_mastery"
        for topic in topic_progress
    )

    overall_accuracy = (
        (total_correct / total_attempts) * 100
        if total_attempts > 0
        else 0.0
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric(
        "Topics assessed",
        f"{assessed_topics}/{len(topic_progress)}",
    )
    metric_columns[1].metric(
        "Questions answered",
        total_attempts,
    )
    metric_columns[2].metric(
        "Overall accuracy",
        f"{overall_accuracy:.1f}%",
    )

    st.caption(
        f"{candidate_topics} topic(s) currently qualify as candidates for "
        "mastery based on the available assessment evidence."
    )
    st.divider()

    for topic in topic_progress:
        topic_name = topic.get("topic_name") or "Untitled topic"
        sequence = topic.get("sequence_order") or "—"
        attempts = int(topic.get("total_attempts") or 0)
        correct = int(topic.get("correct_answers") or 0)
        accuracy = float(topic.get("accuracy_percent") or 0)
        mastery = float(topic.get("mastery_score") or 0)
        status = _format_mastery_status(topic.get("mastery_status"))

        with st.container(border=True):
            st.markdown(f"**{sequence}. {topic_name}**")
            st.caption(status)

            detail_columns = st.columns(3)
            detail_columns[0].metric("Attempts", attempts)
            detail_columns[1].metric("Correct", f"{correct}/{attempts}")
            detail_columns[2].metric("Accuracy", f"{accuracy:.1f}%")

            safe_mastery = max(0.0, min(mastery, 100.0))
            st.progress(
                safe_mastery / 100.0,
                text=f"Mastery evidence score: {safe_mastery:.1f}%",
            )


def home_screen(learner):
    """Display the authenticated learner dashboard and navigation."""

    learner_name = learner["display_name"] or "Learner"

    # Sidebar navigation.
    st.sidebar.title("🎓 EduPath")
    st.sidebar.caption("Personalized Tutoring Agent")
    st.sidebar.divider()

    navigation_options = [
        "Dashboard",
        "AI Tutor",
        "Python Assessment",
        "Study Plan",
    ]

    if learner.get("role") == "admin":
        navigation_options.append("Knowledge Management")

    selected_page = st.sidebar.radio(
        "Navigation",
        options=navigation_options,
        key="edupath_navigation",
    )

    st.sidebar.divider()

    if learner["email"]:
        st.sidebar.caption(f"Signed in as {learner['email']}")

    st.sidebar.button(
        "Sign out",
        on_click=logout_user,
        use_container_width=True,
    )
    # Open the AI Tutor interface.
    if selected_page == "AI Tutor":
        render_tutor(learner)
        return

    # Open the assessment interface.
    if selected_page == "Python Assessment":
        render_assessment(learner)
        return

    if selected_page == "Study Plan":
        render_study_plan(learner)
        return

    if selected_page == "Knowledge Management":
        if learner.get("role") != "admin":
            st.error("An active administrator account is required.")
            return
        render_knowledge_management(learner)
        return

    # Main learner dashboard.
    st.title("🎓 EduPath")
    st.subheader(f"Welcome, {learner_name}!")
    st.success("Your learner account is connected successfully.")

    st.divider()
    st.header("Your learning journey")

    st.write(
        "Welcome to your personalized Python learning environment. "
        "Start by evaluating your current Python knowledge."
    )

    st.subheader("Python Programming")
    st.write(
        "Assess your understanding of variables, operators, "
        "conditionals, loops, functions, collections, strings "
        "and problem solving."
    )

    st.info(
        "Your diagnostic assessment contains 27 multiple-choice "
        "questions covering all nine Python topics."
    )

    st.button(
        "Explore Python Assessment →",
        type="primary",
        use_container_width=True,
        on_click=navigate_to_assessment,
    )

    st.button(
        "Create or view your study plan →",
        use_container_width=True,
        on_click=navigate_to_study_plan,
    )

    if st.session_state.pop("edupath_open_assessment", False):
        st.session_state["edupath_navigation"] = "Python Assessment"
        st.rerun()

    st.divider()
    render_learning_progress(learner)

    st.divider()
    st.subheader("Your learning profile")

    with st.expander("View profile details"):
        col1, col2 = st.columns(2)

        col1.metric(
            "Proficiency",
            learner["proficiency_level"].title(),
        )
        col2.metric(
            "Daily study target",
            f"{learner['daily_study_minutes']} min",
        )

        st.write(
            f"**Preferred language:** {learner['preferred_language']}"
        )
        st.write(
            f"**Explanation style:** "
            f"{learner['explanation_style'].replace('_', ' ').title()}"
        )


# ---------------------------------------------------------
# Main application flow
# ---------------------------------------------------------

if not st.user.is_logged_in:
    login_screen()
    st.stop()

learner = load_authenticated_learner()

if not learner["adult_confirmation"]:
    adult_confirmation_screen(learner)
    st.stop()

if learner.get("role") != "admin":
    try:
        course_available = is_course_published("python-basics")
    except Exception:
        st.error(
            "We could not verify course availability. Please try again later."
        )
        st.stop()

    if not course_available:
        st.title("🎓 EduPath")
        st.info(
            "Python Programming is currently being prepared by the "
            "EduPath team. Learner access will be available after the "
            "course and its approved learning resources are published."
        )
        st.stop()

home_screen(learner)
