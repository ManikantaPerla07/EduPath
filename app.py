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
from ui.tutor_feedback import render_tutor_feedback
from ui.agent_telemetry import render_agent_telemetry
from ui.theme import apply_theme, render_page_header


st.set_page_config(
    page_title="EduPath | Personalized Tutoring",
    page_icon="🎓",
    layout="wide",
)

apply_theme()


class GoogleSessionExpired(Exception):
    """Raised when the Google identity token has expired."""


def login_screen():
    """Display a polished, responsive Google sign-in experience."""

    with st.container(key="edupath_login_layout"):
        left, right = st.columns(
            [1.15, 0.85],
            gap="large",
            vertical_alignment="center",
        )

        with left:
            st.markdown(
                """
                <div class="edupath-login-wrap">
                    <div class="edupath-brand-mark">E</div>
                    <div class="edupath-login-kicker">PERSONALIZED PYTHON LEARNING</div>
                    <h1 class="edupath-login-title">
                        Learn with a plan.<br>Grow with every step.
                    </h1>
                    <p class="edupath-login-copy">
                        A focused learning space that brings together guided
                        explanations, adaptive practice, and a study plan shaped
                        around your progress.
                    </p>
                    <div class="edupath-login-points">
                        <span>Guided AI tutoring</span>
                        <span>Adaptive assessments</span>
                        <span>Personalized study plans</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            with st.container(border=True, key="edupath_login_card"):
                st.markdown(
                    '<div class="edupath-eyebrow">WELCOME TO EDUPATH</div>',
                    unsafe_allow_html=True,
                )
                st.header("Sign in to continue")
                st.write(
                    "Use your Google account to access your learning dashboard, "
                    "tutor conversations, assessments, and saved progress."
                )
                st.button(
                    "Continue with Google",
                    on_click=st.login,
                    type="primary",
                    width="stretch",
                )
                st.caption(
                    "Your learning activity is saved to your private EduPath account."
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


def render_sidebar_signout() -> None:
    """Render a consistently styled sign-out action in the sidebar."""

    with st.sidebar.container(key="edupath_sidebar_signout"):
        st.button(
            "Sign out",
            key="edupath_sidebar_signout_button",
            on_click=logout_user,
            type="secondary",
            width="stretch",
        )


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
        # Streamlit keeps its identity cookie until st.logout() is called.
        # Clear learner-specific state and return directly to the branded
        # sign-in screen instead of leaving the user on a blocked page.
        clear_edupath_session()
        st.logout()
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
            width="stretch",
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

            except PermissionError:
                st.error(
                    "This EduPath account is inactive. "
                    "Please contact an administrator."
                )

            except (ValueError, psycopg.Error):
                st.error(
                    "We could not save your confirmation. "
                    "Please try again."
                )

    st.divider()
    st.button(
        "Sign out",
        on_click=logout_user,
        width="stretch",
    )


def navigate_to_assessment():
    """Navigate to the Python assessment page."""

    st.session_state["edupath_navigation"] = "Python Assessment"


def navigate_to_study_plan():
    """Navigate to the personalized study-plan page."""

    st.session_state["edupath_navigation"] = "Study Plan"


def select_workspace_page(page: str) -> None:
    """Persist the selected workspace page before Streamlit reruns."""

    st.session_state["edupath_navigation"] = page


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



def render_workspace_content(
    learner: dict,
    selected_page: str,
    learner_name: str,
) -> None:
    """Render one workspace page inside the shared page-content slot."""

    if selected_page == "AI Tutor":
        render_tutor(learner)
        return

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

    if selected_page == "AI Tutor Feedback":
        if learner.get("role") != "admin":
            st.error("An active administrator account is required.")
            return
        render_tutor_feedback(learner)
        return

    if selected_page == "AI Tutor Operations":
        if learner.get("role") != "admin":
            st.error("An active administrator account is required.")
            return
        render_agent_telemetry(learner)
        return

    render_page_header(
        "LEARNER WORKSPACE",
        f"Welcome back, {learner_name}",
        "Your Python learning journey, progress, and next steps in one place.",
    )

    st.markdown(
        f"""
        <div class="edupath-dashboard-hero">
            <div class="eyebrow">YOUR FEATURED COURSE</div>
            <h2>Build a strong foundation in Python.</h2>
            <p>
                Learn core programming concepts through guided explanations,
                focused practice, and a study plan informed by your progress.
            </p>
            <div class="edupath-hero-stats">
                <span class="edupath-hero-stat">9 learning topics</span>
                <span class="edupath-hero-stat">27 assessment questions</span>
                <span class="edupath-hero-stat">Personalized study guidance</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")
    action_columns = st.columns(2)

    with action_columns[0]:
        st.button(
            "Start Python assessment",
            type="primary",
            width="stretch",
            on_click=navigate_to_assessment,
        )

    with action_columns[1]:
        st.button(
            "View my study plan",
            width="stretch",
            on_click=navigate_to_study_plan,
        )

    if st.session_state.pop("edupath_open_assessment", False):
        st.session_state["edupath_navigation"] = "Python Assessment"
        st.rerun()

    st.divider()
    render_learning_progress(learner)

    st.divider()
    st.subheader("Your learning profile")
    st.caption("Your saved preferences and daily learning target.")

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



def home_screen(learner):
    """Display the learner dashboard and role-aware application navigation."""

    learner_name = learner.get("display_name") or "Learner"

    st.sidebar.markdown(
        """
        <div class="edupath-sidebar-brand">
            <div class="edupath-brand-mark">E</div>
            <div>
                <div class="edupath-sidebar-name">EduPath</div>
                <div class="edupath-sidebar-subtitle">Personal learning space</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    navigation_options = [
        "Dashboard",
        "AI Tutor",
        "Python Assessment",
        "Study Plan",
    ]

    if learner.get("role") == "admin":
        navigation_options.extend(
            [
                "Knowledge Management",
                "AI Tutor Feedback",
                "AI Tutor Operations",
            ]
        )

    st.session_state.setdefault("edupath_navigation", "Dashboard")
    if st.session_state["edupath_navigation"] not in navigation_options:
        st.session_state["edupath_navigation"] = "Dashboard"

    with st.sidebar.container(key="edupath_sidebar_nav"):
        st.caption("Workspace")
        for page in navigation_options:
            page_key = (
                "edupath_nav_"
                + page.lower().replace(" ", "_")
            )
            st.button(
                page,
                key=page_key,
                type=(
                    "primary"
                    if st.session_state["edupath_navigation"] == page
                    else "secondary"
                ),
                width="stretch",
                on_click=select_workspace_page,
                args=(page,),
            )

    selected_page = st.session_state["edupath_navigation"]

    st.sidebar.divider()

    with st.sidebar.container(key="edupath_sidebar_account_details"):
        if learner.get("email"):
            st.caption(f"Signed in as {learner['email']}")

        role_label = (
            "Administrator"
            if learner.get("role") == "admin"
            else "Learner"
        )
        st.caption(f"Account type · {role_label}")

    render_sidebar_signout()

    previous_page = st.session_state.get("edupath_last_navigation")
    navigation_changed = previous_page != selected_page
    st.session_state["edupath_last_navigation"] = selected_page

    # All workspace pages share one placeholder. Clear it before rendering so
    # slow database calls cannot leave the previous page visible underneath.
    page_container = st.empty()
    page_container.empty()

    with page_container.container():
        if navigation_changed:
            with st.spinner(f"Opening {selected_page}..."):
                render_workspace_content(
                    learner=learner,
                    selected_page=selected_page,
                    learner_name=learner_name,
                )
        else:
            render_workspace_content(
                learner=learner,
                selected_page=selected_page,
                learner_name=learner_name,
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
        render_sidebar_signout()
        st.stop()

    if not course_available:
        st.title("🎓 EduPath")
        st.info(
            "Python Programming is currently being prepared by the "
            "EduPath team. Learner access will be available after the "
            "course and its approved learning resources are published."
        )
        render_sidebar_signout()
        st.stop()

home_screen(learner)
