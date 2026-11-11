
"""Streamlit interface for the EduPath conversational AI tutor."""

import logging

import psycopg
import streamlit as st

from agents.tutor_graph import run_tutor_graph
from services.answer_generation_service import AnswerGenerationError
from services.conversation_context_service import (
    MAX_CONTEXT_HISTORY_MESSAGES,
    ConversationContextError,
)
from services.chat_service import (
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    list_chat_sessions,
    rename_chat_session,
    save_chat_message,
)


logger = logging.getLogger(__name__)


COURSE_SLUG = "python-basics"
MAX_HISTORY_MESSAGES = 500
MAX_TITLE_LENGTH = 120

CURRENT_SESSION_KEY = "edupath_tutor_session_id"
NEW_CHAT_KEY = "edupath_tutor_new_chat"
INITIALIZED_KEY = "edupath_tutor_initialized"
SELECTOR_PREFIX = "edupath_tutor_session_selector_"


def _session_label(session: dict) -> str:
    """Return a readable conversation label."""

    title = session.get("title")

    if isinstance(title, str) and title.strip():
        return title.strip()

    return "Untitled conversation"


def _clear_selector_state() -> None:
    """Clear old conversation selector widget state."""

    for key in list(st.session_state.keys()):
        if key.startswith(SELECTOR_PREFIX):
            st.session_state.pop(key, None)


def _render_citations(citations: list[dict]) -> None:
    """Display source metadata attached to an assistant response."""

    if not citations:
        return

    with st.expander(
        f"Sources ({len(citations)})",
        expanded=False,
    ):
        for index, citation in enumerate(citations):

            source_id = citation.get("source_id", "Source")
            title = citation.get("source_title") or "Untitled source"

            st.markdown(f"**[{source_id}] {title}**")

            topic = citation.get("topic_name")
            if topic:
                st.caption(f"Topic: {topic}")

            file_name = citation.get("file_name")
            if file_name:
                st.caption(f"File: {file_name}")

            page_number = citation.get("page_number")
            if page_number is not None:
                st.caption(f"Page: {page_number}")

            similarity = citation.get("similarity")
            if isinstance(similarity, (float, int)) and not isinstance(
                similarity, bool
            ):
                st.caption(
                    f"Retrieval similarity: {similarity:.3f}"
                )

            if index < len(citations) - 1:
                st.divider()


def _render_saved_message(message: dict) -> None:
    """Render a saved learner or assistant message."""

    role = message["role"]

    with st.chat_message(role):
        st.markdown(message["content"])

        if role == "assistant":
            _render_citations(message.get("citations") or [])


def _load_sessions(user_id: str) -> list[dict]:
    """Load conversations belonging to the authenticated learner."""

    return list_chat_sessions(
        user_id=user_id,
        course_slug=COURSE_SLUG,
        limit=50,
    )


def _start_new_chat() -> None:
    """Switch the Tutor to a new conversation."""

    st.session_state[CURRENT_SESSION_KEY] = None
    st.session_state[NEW_CHAT_KEY] = True

    _clear_selector_state()
    st.rerun()


def _return_to_recent_chats(sessions: list[dict]) -> None:
    """Leave new-chat mode and select the most recent conversation."""

    st.session_state[NEW_CHAT_KEY] = False
    st.session_state[CURRENT_SESSION_KEY] = (
        sessions[0]["session_id"] if sessions else None
    )

    _clear_selector_state()
    st.rerun()


def _render_conversation_selector(
    sessions: list[dict],
) -> str | None:
    """Render the recent-conversation selector."""

    if not sessions:
        return None

    session_ids = [
        session["session_id"]
        for session in sessions
    ]

    current_session_id = st.session_state.get(CURRENT_SESSION_KEY)

    if current_session_id not in session_ids:
        current_session_id = session_ids[0]
        st.session_state[CURRENT_SESSION_KEY] = current_session_id

    title_lookup = {
        session["session_id"]: _session_label(session)
        for session in sessions
    }

    # Generate a new widget key when the conversation list changes.
    selector_signature = (
        f"{len(sessions)}_"
        f"{sessions[0]['session_id']}"
    )
    selector_key = f"{SELECTOR_PREFIX}{selector_signature}"

    selected_session_id = st.selectbox(
        "Recent conversations",
        options=session_ids,
        index=session_ids.index(current_session_id),
        format_func=lambda session_id: title_lookup.get(
            session_id,
            "Untitled conversation",
        ),
        key=selector_key,
    )

    st.session_state[CURRENT_SESSION_KEY] = selected_session_id
    st.session_state[NEW_CHAT_KEY] = False

    return selected_session_id


def _render_conversation_settings(
    user_id: str,
    session: dict,
) -> None:
    """Render rename and delete controls for an owned conversation."""

    session_id = session["session_id"]
    current_title = _session_label(session)

    with st.expander("Conversation settings"):

        with st.form(
            key=f"edupath_rename_form_{session_id}"
        ):
            new_title = st.text_input(
                "Conversation title",
                value=current_title,
                max_chars=MAX_TITLE_LENGTH,
            )

            rename_submitted = st.form_submit_button(
                "Save title",
                use_container_width=True,
            )

        if rename_submitted:
            try:
                if new_title.strip() == current_title:
                    st.info("The title has not changed.")
                else:
                    rename_chat_session(
                        user_id=user_id,
                        session_id=session_id,
                        title=new_title,
                    )
                    st.success("Conversation renamed.")
                    st.rerun()

            except ValueError as exc:
                st.error(str(exc))

            except (LookupError, psycopg.Error):
                st.error(
                    "We could not rename this conversation. "
                    "Please try again."
                )

        st.divider()

        confirmation_key = (
            f"edupath_confirm_delete_{session_id}"
        )

        confirmed = st.checkbox(
            "I understand that deleting this conversation "
            "also deletes its saved messages.",
            key=confirmation_key,
        )

        if st.button(
            "Delete conversation",
            key=f"edupath_delete_button_{session_id}",
            type="secondary",
            disabled=not confirmed,
            use_container_width=True,
        ):
            try:
                deleted = delete_chat_session(
                    user_id=user_id,
                    session_id=session_id,
                )

                if deleted:
                    st.session_state[CURRENT_SESSION_KEY] = None
                    st.session_state[NEW_CHAT_KEY] = False
                    st.session_state.pop(confirmation_key, None)

                    _clear_selector_state()
                    st.rerun()

                st.warning(
                    "This conversation was not found or is no longer available."
                )

            except (ValueError, LookupError, psycopg.Error):
                st.error(
                    "We could not delete this conversation. "
                    "Please try again."
                )


def _render_conversation_controls(
    user_id: str,
    sessions: list[dict],
) -> str | None:
    """Render new-chat, recent-chat and conversation settings controls."""

    is_new_chat = st.session_state.get(NEW_CHAT_KEY, False)

    if is_new_chat:

        if sessions:
            if st.button(
                "← Return to recent conversations",
                key="edupath_tutor_return_recent",
            ):
                _return_to_recent_chats(sessions)

        st.caption("New conversation")
        return None

    columns = st.columns([1, 2])

    with columns[0]:
        if st.button(
            "＋ New chat",
            key="edupath_tutor_new_chat_button",
            use_container_width=True,
        ):
            _start_new_chat()

    with columns[1]:
        selected_session_id = _render_conversation_selector(
            sessions
        )

    if selected_session_id is not None:
        selected_session = next(
            session
            for session in sessions
            if session["session_id"] == selected_session_id
        )

        st.caption(
            f"Conversation: {_session_label(selected_session)}"
        )

        _render_conversation_settings(
            user_id=user_id,
            session=selected_session,
        )

    return selected_session_id


def _render_conversation_history(
    user_id: str,
    session_id: str | None,
) -> None:
    """Reload and render the selected conversation from PostgreSQL."""

    if session_id is None:
        st.info(
            "Ask your first Python question below to start a conversation."
        )
        return

    messages = get_chat_messages(
        user_id=user_id,
        session_id=session_id,
        limit=MAX_HISTORY_MESSAGES,
    )

    if not messages:
        st.info(
            "This conversation is empty. Ask your first question below."
        )
        return

    for message in messages:
        _render_saved_message(message)


def _process_question(
    user_id: str,
    session_id: str | None,
    question: str,
) -> None:
    """
    Save a learner question, generate a grounded answer,
    save its citations, and reload the transcript.
    """

    # Create a session only when the first question is submitted.
    if session_id is None:
        try:
            session = create_chat_session(
                user_id=user_id,
                course_slug=COURSE_SLUG,
            )

            session_id = session["session_id"]

            st.session_state[CURRENT_SESSION_KEY] = session_id
            st.session_state[NEW_CHAT_KEY] = False

        except (ValueError, LookupError, psycopg.Error):
            st.error(
                "We could not create your conversation. "
                "Please try again."
            )
            return

    # Load recent conversation history before saving the current question.
    conversation_history = []

    if session_id is not None:
        try:
            conversation_history = get_chat_messages(
                user_id=user_id,
                session_id=session_id,
                limit=MAX_CONTEXT_HISTORY_MESSAGES,
            )

        except (ValueError, LookupError, psycopg.Error):
            st.error(
                "We could not load the recent conversation context. "
                "Your question was not submitted. Please try again."
            )
            return

    # Save the learner's message only after previous history is loaded.
    try:
        saved_user_message = save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=question,
        )

    except (ValueError, LookupError, psycopg.Error):
        st.error(
            "Your question could not be saved. Please try again."
        )
        return

    # Generate and save the assistant's answer.
    # The saved transcript will be the only source used for rendering.
    try:
        with st.spinner("EduPath is preparing your explanation..."):
            result = run_tutor_graph(
                question=question,
                course_slug=COURSE_SLUG,
                limit=5,
                conversation_history=conversation_history,
                user_id=user_id,
                session_id=session_id,
            )

        answer = result["answer"]
        citations = result["citations"]

        if result["insufficient_evidence"]:
            answer += (
                "\n\n"
                "*The approved learning materials did not contain "
                "enough evidence for this question.*"
            )
        elif result.get("model"):
            answer += f"\n\n*Generated with {result['model']}.*"

        teaching_profile = result.get("teaching_profile")

        if isinstance(teaching_profile, dict):
            teaching_label = teaching_profile.get("label")
            mastery_status = teaching_profile.get("mastery_status")

            if (
                isinstance(teaching_label, str)
                and isinstance(mastery_status, str)
            ):
                readable_status = mastery_status.replace("_", " ")
                answer += (
                    "\n\n---\n\n"
                    f"*Personalized approach: {teaching_label} "
                    f"- {readable_status}*"
                )

        save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=answer,
            citations=citations,
        )

    except (AnswerGenerationError, ConversationContextError):
        logger.exception(
            "Tutor request failed during model or conversation-context processing."
        )
        st.error(
            "The Tutor could not process your question right now. "
            "Your question has been saved. Please try again shortly."
        )
        return

    except (ValueError, LookupError, RuntimeError, psycopg.Error):
        logger.exception(
            "Tutor request failed during validation, graph execution, or database access."
        )
        st.error(
            "We encountered a problem while processing your question. "
            "Please try again."
        )
        return

    # Reload the saved transcript from PostgreSQL.
    # This prevents duplicate rendering across Streamlit reruns.
    st.rerun()


def render_tutor(learner: dict) -> None:
    """Render the authenticated learner's conversational AI Tutor."""

    st.title("Your AI Tutor")

    st.write(
        "Ask questions about Python, explore concepts step by step, "
        "and receive explanations grounded in your approved course materials."
    )

    st.caption(
        "EduPath retrieves relevant Python learning resources and "
        "provides explanations with source-linked citations."
    )

    user_id = str(learner["user_id"])

    # Load only this learner's saved conversations.
    try:
        sessions = _load_sessions(user_id)

    except (ValueError, RuntimeError, psycopg.Error):
        st.error(
            "We could not load your conversations. "
            "Please refresh and try again."
        )
        return

    # Initialize the selected conversation on first visit.
    if not st.session_state.get(INITIALIZED_KEY, False):
        st.session_state[CURRENT_SESSION_KEY] = (
            sessions[0]["session_id"] if sessions else None
        )
        st.session_state[NEW_CHAT_KEY] = False
        st.session_state[INITIALIZED_KEY] = True

    current_session_id = st.session_state.get(CURRENT_SESSION_KEY)

    available_session_ids = {
        session["session_id"] for session in sessions
    }

    # Recover when the selected session no longer exists.
    if (
        current_session_id is not None
        and current_session_id not in available_session_ids
    ):
        current_session_id = (
            sessions[0]["session_id"] if sessions else None
        )
        st.session_state[CURRENT_SESSION_KEY] = current_session_id

    selected_session_id = _render_conversation_controls(
        user_id=user_id,
        sessions=sessions,
    )

    if st.session_state.get(NEW_CHAT_KEY, False):
        selected_session_id = None
    elif selected_session_id is None:
        selected_session_id = st.session_state.get(CURRENT_SESSION_KEY)

    st.divider()

    # Restore the full saved conversation before accepting a new question.
    try:
        _render_conversation_history(
            user_id=user_id,
            session_id=selected_session_id,
        )

    except (ValueError, LookupError, RuntimeError, psycopg.Error):
        st.error(
            "We could not load this conversation. "
            "Please select another conversation or start a new chat."
        )
        return

    question = st.chat_input(
        "Ask your Python question...",
        max_chars=2000,
    )

    if question and question.strip():
        _process_question(
            user_id=user_id,
            session_id=selected_session_id,
            question=question.strip(),
        )
