import math
import time

import psycopg
import streamlit as st

from services.learner_service import (
    get_or_create_learner,
    confirm_adult_status,
)

from ui.assessment import render_assessment


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
    """
    Read identity claims from Streamlit's authenticated Google session.

    Validate the ID token's issued-at and expiry timestamps before
    using its identity information.
    """

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
    """
    Retrieve the learner once per browser session.

    Reuse the cached learner during normal navigation.
    Refresh the database record every 60 seconds.
    """

    try:
        # Read the currently authenticated Google identity.
        claims = get_authenticated_google_claims()

        identity_key = (
            claims["iss"],
            claims["sub"],
        )

        # Clear previous learner data if another Google account signs in.
        stored_identity = st.session_state.get(
            "edupath_google_identity"
        )

        if stored_identity != identity_key:
            clear_edupath_session()

            st.session_state["edupath_google_identity"] = identity_key

        # Retrieve the previously cached learner.
        cached_learner = st.session_state.get(
            "edupath_learner"
        )

        cached_at = st.session_state.get(
            "edupath_learner_cached_at"
        )

        # Reuse the account for 60 seconds without another Neon query.
        if (
            cached_learner is not None
            and cached_at is not None
            and time.monotonic() - cached_at < 60
        ):
            return cached_learner

        # Cache expired or first login: retrieve account from Neon.
        learner = get_or_create_learner(claims)

        st.session_state["edupath_learner"] = learner

        st.session_state["edupath_learner_cached_at"] = (
            time.monotonic()
        )

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

def home_screen(learner):
    """Display the authenticated learner dashboard and navigation."""

    learner_name = learner["display_name"] or "Learner"

    # Sidebar navigation.
    st.sidebar.title("🎓 EduPath")
    st.sidebar.caption("Personalized Tutoring Agent")
    st.sidebar.divider()

    selected_page = st.sidebar.radio(
        "Navigation",
        options=[
            "Dashboard",
            "Python Assessment",
        ],
        key="edupath_navigation",
    )

    st.sidebar.divider()

    if learner["email"]:
        st.sidebar.caption(f"Signed in as {learner['email']}")

    st.sidebar.button(
        "Sign out",
        on_click=st.logout,
        use_container_width=True,
    )

    # Open the assessment interface.
    if selected_page == "Python Assessment":
        render_assessment(learner)
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
    if st.session_state.pop("edupath_open_assessment", False):
        st.session_state["edupath_navigation"] = "Python Assessment"
        st.rerun()

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


home_screen(learner)
