import streamlit as st


st.set_page_config(
    page_title="EduPath | Personalized Tutoring",
    page_icon="🎓",
    layout="centered",
)


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


def home_screen():
    """Display the page after successful Google authentication."""

    st.title("🎓 Welcome to EduPath!")

    learner_name = st.user.get("name", "Learner")
    learner_email = st.user.get("email", "Email unavailable")

    st.success(f"Successfully signed in, {learner_name}!")

    st.caption(f"Google account: {learner_email}")

    st.divider()

    st.subheader("Your learning journey starts here")

    st.write(
        "Google authentication is working. "
        "Your learner profile and Python assessments "
        "will be connected in the next development step."
    )

    st.button(
        "Sign out",
        on_click=st.logout,
        use_container_width=True,
    )


if st.user.is_logged_in:
    home_screen()
else:
    login_screen()
