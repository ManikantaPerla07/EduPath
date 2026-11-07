import math
import time

import psycopg
import streamlit as st

from services.learner_service import (
    get_or_create_learner,
    confirm_adult_status,
)


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


def load_authenticated_learner():
    """Create or retrieve the learner using authenticated Google claims."""

    try:
        claims = get_authenticated_google_claims()
        return get_or_create_learner(claims)

    except GoogleSessionExpired:
        st.warning(
            "Your Google sign-in session has expired. "
            "Please sign in again."
        )
        st.button(
            "Sign out and sign in again",
            on_click=st.logout,
        )
        st.stop()

    except PermissionError as error:
        st.error(str(error))
        st.button("Sign out", on_click=st.logout)
        st.stop()

    except (ValueError, RuntimeError):
        st.error(
            "We could not verify your Google identity or load "
            "your learner account. Please sign out and try again."
        )
        st.button("Sign out", on_click=st.logout)
        st.stop()

    except psycopg.Error:
        st.error(
            "We could not connect to your learner account. "
            "Please try again."
        )

        if st.button("Retry"):
            st.rerun()

        st.button("Sign out", on_click=st.logout)
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
        on_click=st.logout,
        use_container_width=True,
    )


def home_screen(learner):
    """Display the authenticated learner dashboard."""

    st.title("🎓 EduPath")

    learner_name = learner["display_name"] or "Learner"

    st.subheader(f"Welcome, {learner_name}!")

    if learner["email"]:
        st.caption(f"Signed in as {learner['email']}")

    st.divider()

    st.success("Your learner account is connected successfully.")

    st.subheader("Your learning journey starts here")

    st.write(
        "Your Python learning profile is ready. "
        "Personalized tutoring, assessments, and study planning "
        "will be available through your EduPath dashboard."
    )

    with st.expander("Your learning profile"):

        st.write(
            f"**Proficiency:** {learner['proficiency_level'].title()}"
        )

        st.write(
            f"**Preferred language:** {learner['preferred_language']}"
        )

        st.write(
            f"**Explanation style:** "
            f"{learner['explanation_style'].replace('_', ' ').title()}"
        )

        st.write(
            f"**Daily study target:** "
            f"{learner['daily_study_minutes']} minutes"
        )

    st.divider()

    st.button(
        "Sign out",
        on_click=st.logout,
        use_container_width=True,
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
