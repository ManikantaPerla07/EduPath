import psycopg
import streamlit as st

from services.assessment_session_service import start_assessment
from services.assessment_submission_service import submit_assessment


COURSE_SLUG = "python-basics"


def _get_answer_letter(option: str) -> str:
    """Convert an option such as 'A. High' into its answer letter."""

    if not isinstance(option, str):
        raise ValueError("Invalid answer option.")

    letter = option.partition(".")[0].strip().upper()

    if letter not in {"A", "B", "C", "D"}:
        raise ValueError("Invalid answer option.")

    return letter


def _answer_state_key(assessment_id: str) -> str:
    """Generate a unique session-state key for assessment answers."""

    return f"edupath_answers_{assessment_id}"


def _save_selected_answer(
    assessment_id: str,
    item_id: str,
    widget_key: str,
) -> None:
    """Save the selected option before the assessment fragment reruns."""

    selected_option = st.session_state.get(widget_key)

    state_key = _answer_state_key(assessment_id)

    saved_answers = st.session_state.setdefault(state_key, {})

    if selected_option is None:
        saved_answers.pop(item_id, None)
    else:
        saved_answers[item_id] = selected_option


def _change_question(step: int) -> None:
    """Move to the previous or next question."""

    assessment = st.session_state.get("edupath_active_assessment")

    if assessment is None:
        return

    total_questions = len(assessment["questions"])

    current_index = st.session_state.get(
        "edupath_current_question", 0
    )

    st.session_state["edupath_current_question"] = max(
        0,
        min(current_index + step, total_questions - 1),
    )


def _start_diagnostic(learner: dict) -> None:
    """Create a new diagnostic assessment in the database."""

    try:
        with st.spinner("Preparing your Python assessment..."):

            assessment = start_assessment(
                user_id=learner["user_id"],
                course_slug=COURSE_SLUG,
                assessment_type="diagnostic",
            )

        st.session_state["edupath_active_assessment"] = assessment
        st.session_state["edupath_current_question"] = 0

        st.session_state[
            _answer_state_key(assessment["assessment_id"])
        ] = {}

        st.session_state.pop("edupath_assessment_result", None)

        # Refresh only this assessment fragment.
        st.rerun(scope="fragment")

    except (ValueError, PermissionError) as error:
        st.error(str(error))

    except psycopg.Error:
        st.error(
            "Unable to create your assessment. "
            "Please check your database connection and try again."
        )


def _render_question(assessment: dict) -> None:
    """Display one question and its four options."""

    questions = assessment["questions"]
    total_questions = len(questions)

    if total_questions == 0:
        st.error("This assessment contains no questions.")
        return

    current_index = st.session_state.get(
        "edupath_current_question", 0
    )

    current_index = max(
        0,
        min(current_index, total_questions - 1),
    )

    question = questions[current_index]

    assessment_id = assessment["assessment_id"]
    item_id = question["item_id"]

    state_key = _answer_state_key(assessment_id)

    saved_answers = st.session_state.setdefault(state_key, {})

    widget_key = f"edupath_option_{assessment_id}_{item_id}"

    saved_option = saved_answers.get(item_id)

    # Restore a previously selected option when revisiting a question.
    if widget_key not in st.session_state and saved_option is not None:
        st.session_state[widget_key] = saved_option

    # Question progress.
    st.progress(
        (current_index + 1) / total_questions,
        text=f"Question {current_index + 1} of {total_questions}",
    )

    st.caption(
        f"Topic: {question['topic']['name']} | "
        f"Difficulty: {question['difficulty'].title()}"
    )

    st.subheader(question["question_text"])

    options = question["options"]

    if not isinstance(options, list) or len(options) != 4:
        st.error("This question has an invalid option format.")
        return

    # Display learner-safe options. No answer keys are exposed.
    st.radio(
        "Choose one answer:",
        options=options,
        index=None,
        key=widget_key,
        on_change=_save_selected_answer,
        args=(assessment_id, item_id, widget_key),
    )

    st.caption(
        f"Answered: {len(saved_answers)} / {total_questions}"
    )

    st.divider()

    previous_col, next_col = st.columns(2)

    with previous_col:
        st.button(
            "← Previous",
            disabled=current_index == 0,
            use_container_width=True,
            on_click=_change_question,
            args=(-1,),
        )

    with next_col:
        st.button(
            "Next →",
            disabled=current_index == total_questions - 1,
            use_container_width=True,
            on_click=_change_question,
            args=(1,),
        )

    if current_index == total_questions - 1:

        st.info(
            "You have reached the final question. "
            "Review your answers before submitting."
        )

        if st.button(
            "Submit assessment",
            type="primary",
            use_container_width=True,
        ):
            _submit_current_assessment(assessment)


def _submit_current_assessment(assessment: dict) -> None:
    """Convert selected options into letters and submit the assessment."""

    assessment_id = assessment["assessment_id"]

    state_key = _answer_state_key(assessment_id)

    saved_answers = st.session_state.get(state_key, {})

    answers = {}

    try:
        for item_id, selected_option in saved_answers.items():
            answers[item_id] = _get_answer_letter(selected_option)

        with st.spinner("Grading your assessment..."):

            result = submit_assessment(
                user_id=st.session_state[
                    "edupath_authenticated_user_id"
                ],
                assessment_id=assessment_id,
                answers=answers,
            )

        st.session_state["edupath_assessment_result"] = result

        st.session_state.pop("edupath_active_assessment", None)

        # Show results without rerunning Google authentication or the dashboard.
        st.rerun(scope="fragment")

    except (ValueError, PermissionError) as error:
        st.error(str(error))

    except (RuntimeError, psycopg.Error):
        st.error(
            "We couldn't submit your assessment. "
            "Please check your connection and try again."
        )


def _get_option_text(options: list, answer_letter: str) -> str:
    """Return the full option text corresponding to an answer letter."""

    prefix = f"{answer_letter}."

    for option in options:
        if isinstance(option, str) and option.startswith(prefix):
            return option

    return answer_letter


def _render_results(result: dict) -> None:
    """Display the submitted assessment score and explanations."""

    st.title("Assessment Results")

    st.metric(
        "Your score",
        f"{result['score_percent']:.2f}%",
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Correct", result["correct_answers"])
    col2.metric("Incorrect", result["incorrect_answers"])
    col3.metric("Unanswered", result["unanswered_questions"])

    st.caption(
        f"Awarded {result['awarded_points']} "
        f"out of {result['total_points']} points."
    )

    st.divider()

    st.subheader("Review your answers")

    for index, question in enumerate(result["questions"], start=1):

        with st.expander(
            f"Question {index}: {question['question_text']}"
        ):

            for option in question["options"]:
                st.write(option)

            submitted_answer = question["submitted_answer"]
            correct_answer = question["correct_answer"]

            if submitted_answer is None:
                submitted_text = "Not answered"
            else:
                submitted_text = _get_option_text(
                    question["options"],
                    submitted_answer,
                )

            correct_text = _get_option_text(
                question["options"],
                correct_answer,
            )

            st.write(f"**Your answer:** {submitted_text}")
            st.write(f"**Correct answer:** {correct_text}")

            if question["is_correct"]:
                st.success("Correct answer!")

            elif submitted_answer is None:
                st.warning("You did not answer this question.")

            else:
                st.error("Incorrect answer.")

            if question["explanation"]:
                st.info(
                    f"**Explanation:** {question['explanation']}"
                )

    st.divider()

    if st.button(
        "Start another diagnostic assessment",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.pop("edupath_assessment_result", None)
        st.session_state.pop("edupath_active_assessment", None)
        st.session_state.pop("edupath_current_question", None)

        # Return to the assessment introduction.
        st.rerun(scope="fragment")


@st.fragment
def render_assessment(learner: dict) -> None:
    """
    Render the assessment independently from the main application.

    Navigation and answer interactions rerun only this fragment.
    """

    st.session_state["edupath_authenticated_user_id"] = learner["user_id"]

    result = st.session_state.get("edupath_assessment_result")

    if result is not None:
        _render_results(result)
        return

    assessment = st.session_state.get("edupath_active_assessment")

    if assessment is not None:
        _render_question(assessment)
        return

    st.header("Python Programming")

    st.subheader("Diagnostic Assessment")

    st.write(
        "Test your current Python knowledge across variables, "
        "operators, conditionals, loops, functions, collections, "
        "strings, and problem solving."
    )

    st.info(
        "Your diagnostic assessment contains 27 multiple-choice "
        "questions. You can navigate between questions and leave "
        "questions unanswered."
    )

    if st.button(
        "Start diagnostic assessment",
        type="primary",
        use_container_width=True,
    ):
        _start_diagnostic(learner)
