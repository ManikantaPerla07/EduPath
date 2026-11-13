
"""Streamlit interface for the EduPath conversational AI tutor."""

import logging

import psycopg
import streamlit as st

from ui.theme import render_page_header

from agents.tutor_graph import run_tutor_graph
from services.agent_telemetry_service import AgentRunAlreadyActiveError
from services.answer_generation_service import AnswerGenerationError
from services.conversation_context_service import (
    MAX_CONTEXT_HISTORY_MESSAGES,
    ConversationContextError,
)
from services.chat_service import (
    ChatRateLimitError,
    ChatSessionBusyError,
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    list_chat_sessions,
    rename_chat_session,
    save_chat_feedback,
    save_chat_message,
)
from services.subjective_evaluation_service import evaluate_subjective_explanation


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


def _render_message_feedback(
    user_id: str,
    message: dict,
) -> None:
    """Render and persist a learner rating for an assistant response."""

    if message.get("role") != "assistant":
        return

    message_id = message.get("message_id")
    if not isinstance(message_id, str) or not message_id:
        return

    feedback_key = f"edupath_tutor_feedback_{message_id}"
    saved_rating = message.get("feedback")

    # Restore the persisted rating when this message is first rendered
    # in the current Streamlit session.
    if (
        feedback_key not in st.session_state
        and isinstance(saved_rating, bool)
    ):
        st.session_state[feedback_key] = (
            1 if saved_rating else 0
        )

    st.caption("Was this response helpful?")
    selected_rating = st.feedback(
        "thumbs",
        key=feedback_key,
    )

    if selected_rating not in (0, 1):
        return

    is_helpful = selected_rating == 1

    # Do not write the same rating on every Streamlit rerun.
    if saved_rating is is_helpful:
        return

    try:
        save_chat_feedback(
            user_id=user_id,
            message_id=message_id,
            is_helpful=is_helpful,
        )
        message["feedback"] = is_helpful
        st.caption("Thanks for your feedback.")

    except (ValueError, LookupError, psycopg.Error):
        logger.exception(
            "Could not save AI Tutor feedback for message %s.",
            message_id,
        )
        st.caption(
            "We could not save your feedback. Please try again."
        )


def _render_saved_message(
    message: dict,
    user_id: str,
) -> None:
    """Render a saved learner or assistant message."""

    role = message["role"]

    with st.chat_message(role):
        st.markdown(message["content"])

        if role == "assistant":
            _render_citations(message.get("citations") or [])
            _render_message_feedback(
                user_id=user_id,
                message=message,
            )


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
                width="stretch",
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
            width="stretch",
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

            except ChatSessionBusyError as exc:
                st.warning(str(exc))

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
            width="stretch",
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
        _render_saved_message(
            message=message,
            user_id=user_id,
        )


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

    except ChatRateLimitError as exc:
        st.warning(str(exc))
        return

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

    except AgentRunAlreadyActiveError as exc:
        st.warning(str(exc))
        return

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


SUBJECTIVE_PRACTICE_TOPICS = {
    "loops_boundary": {
        "title": "Loops: range(start, stop) Boundary Mechanics",
        "topic_slug": "loops",
        "question": "Explain how range(start, stop) works in a Python for loop. What numbers does range(1, 5) produce and why?",
        "reference_answer": (
            "In Python, a for loop iterates through sequences. range(start, stop) generates integers "
            "beginning at start and stopping strictly before stop. The upper bound is exclusive, so "
            "range(1, 5) yields 1, 2, 3, and 4. To include 5, the stop bound must be 6."
        ),
    },
    "equality_vs_assignment": {
        "title": "Variables: Assignment (=) vs Equality (==)",
        "topic_slug": "variables",
        "question": "What is the difference between single equals (=) and double equals (==) in Python?",
        "reference_answer": (
            "In Python, single equals = is the assignment operator used to store a value into a variable. "
            "Double equals == is a comparison operator that checks whether two values are equal and returns "
            "a boolean True or False."
        ),
    },
    "list_mutation": {
        "title": "Data Structures: Mutating Lists During Iteration",
        "topic_slug": "loops",
        "question": "Why is it dangerous to remove items from a list while iterating over it in a for loop?",
        "reference_answer": (
            "Removing items from a list while iterating directly mutates the collection in-place and shifts index "
            "pointers. This causes the loop iterator to skip elements or trigger index errors. "
            "Instead, iterate over a shallow copy or use a list comprehension."
        ),
    },
}


def _render_subjective_practice_expander(user_id: str) -> None:
    """Render the rubric-based subjective explanation practice module."""
    if not isinstance(user_id, str) or not user_id.strip():
        return

    with st.expander("📝 Conceptual Self-Assessment (Rubric-Based AI Evaluation)", expanded=False):
        st.markdown(
            "Test your understanding by writing an explanation in your own words. "
            "EduPath evaluates your reasoning across a **four-dimensional pedagogical rubric** "
            "and diagnoses common conceptual misconceptions."
        )

        selected_key = st.selectbox(
            "Choose a core Python concept to explain:",
            options=list(SUBJECTIVE_PRACTICE_TOPICS.keys()),
            format_func=lambda k: SUBJECTIVE_PRACTICE_TOPICS[k]["title"],
            key="edupath_subjective_topic_select",
        )
        selected_topic = SUBJECTIVE_PRACTICE_TOPICS[selected_key]

        st.info(f"**Prompt:** {selected_topic['question']}")

        student_explanation = st.text_area(
            "Your explanation:",
            height=120,
            placeholder="Type your explanation here. Include steps, analogies, or syntax rules...",
            key=f"edupath_subj_text_{selected_key}",
        )

        if st.button("Evaluate My Explanation", key=f"edupath_subj_submit_{selected_key}", type="primary"):
            if not student_explanation or not student_explanation.strip():
                st.warning("Please enter your explanation before submitting.")
                return

            try:
                eval_result = evaluate_subjective_explanation(
                    question=selected_topic["question"],
                    reference_answer=selected_topic["reference_answer"],
                    student_explanation=student_explanation.strip(),
                    topic_slug=selected_topic["topic_slug"],
                )

                score = eval_result["score_percent"]
                passed = eval_result["passed"]
                rubric = eval_result["rubric_breakdown"]
                misconceptions = eval_result["detected_misconceptions"]
                feedback = eval_result["feedback"]

                st.markdown("---")
                if passed:
                    st.success(f"### 🎉 Overall Score: {score}% — Strong Conceptual Understanding")
                else:
                    st.warning(f"### ⚠️ Overall Score: {score}% — Developing Conceptual Understanding")

                st.markdown("#### 📊 Pedagogical Rubric Breakdown")
                r_col1, r_col2, r_col3, r_col4 = st.columns(4)
                r_col1.metric("Conceptual Accuracy (40%)", f"{rubric['conceptual_accuracy']}%")
                r_col2.metric("Reasoning & Logic (30%)", f"{rubric['reasoning_and_logic']}%")
                r_col3.metric("Edge Cases & Gotchas (15%)", f"{rubric['edge_cases_and_gotchas']}%")
                r_col4.metric("Clarity of Expression (15%)", f"{rubric['clarity_of_expression']}%")

                if misconceptions:
                    st.error("#### ⚠️ Detected Conceptual Misconception(s)")
                    for m in misconceptions:
                        st.markdown(f"- **Misconception:** {m['misconception']}\n  - **Correction:** {m['correction']}")

                st.info(f"💡 **Constructive Formative Feedback:**\n\n{feedback}")

                st.caption(
                    "🔒 *Server-side authorization verified. Note: This rubric assessment is formative and "
                    "designed for self-evaluation. It does not alter your official mastery records.*"
                )

            except Exception as exc:
                logger.exception("Subjective evaluation failed: %s", exc)
                st.error("Could not evaluate your explanation. Please try again.")


def render_tutor(learner: dict) -> None:
    """Render the authenticated learner's conversational AI Tutor."""

    render_page_header(
        "LEARNING ASSISTANT",
        "Your AI Tutor",
        "Explore Python concepts step by step with explanations grounded in "
        "your approved course materials and source-linked citations.",
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

    _render_subjective_practice_expander(user_id=user_id)

    quick_prompt = None
    if selected_session_id is not None:
        chip_col1, chip_col2, chip_col3 = st.columns(3)
        with chip_col1:
            if st.button("💡 Get a Hint", key="edupath_hint_chip", width="stretch", help="Request a progressive hint without revealing the full solution"):
                quick_prompt = "Can you give me a progressive hint on what we're discussing without giving away the full answer?"
        with chip_col2:
            if st.button("✍️ Test Understanding", key="edupath_practice_chip", width="stretch", help="Request a quick exercise or question to test yourself"):
                quick_prompt = "Could you give me a short practice question or code puzzle to test my understanding of this concept?"
        with chip_col3:
            if st.button("🔍 Explain with Analogy", key="edupath_analogy_chip", width="stretch", help="Request an everyday analogy"):
                quick_prompt = "Can you explain this concept using a simple everyday analogy and a small code example?"

    input_question = st.chat_input(
        "Ask your Python question...",
        max_chars=2000,
    )

    question = quick_prompt or input_question

    if question and question.strip():
        _process_question(
            user_id=user_id,
            session_id=selected_session_id,
            question=question.strip(),
        )
