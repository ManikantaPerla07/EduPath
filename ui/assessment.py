import psycopg
import streamlit as st

from ui.theme import render_page_header

from services.assessment_session_service import start_assessment
from services.assessment_submission_service import submit_assessment
from services.adaptive_assessment_service import submit_adaptive_answer
from services.adaptive_question_service import (
    MAX_ADAPTIVE_QUESTIONS,
)


COURSE_SLUG = "python-basics"


ADAPTIVE_QUESTION_COUNT = MAX_ADAPTIVE_QUESTIONS


def _assessment_start_options(assessment_type: str) -> dict:
    """Return the supported session options for an assessment mode."""

    if assessment_type == "diagnostic":
        return {"assessment_type": "diagnostic"}

    if assessment_type in {"practice", "revision"}:
        return {
            "assessment_type": assessment_type,
            "question_count": ADAPTIVE_QUESTION_COUNT,
        }

    raise ValueError("Invalid assessment type.")




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


def _assessment_mode_label(assessment_type: str) -> str:
    """Return the learner-facing label for an assessment mode."""

    labels = {
        "diagnostic": "Diagnostic Assessment",
        "practice": "Adaptive Practice",
        "revision": "Targeted Revision",
    }

    try:
        return labels[assessment_type]
    except (KeyError, TypeError):
        raise ValueError("Invalid assessment type.")


def _start_assessment(
    learner: dict,
    assessment_type: str,
) -> None:
    """Create an assessment session for the selected learning mode."""

    try:
        options = _assessment_start_options(assessment_type)

        with st.spinner("Preparing your Python assessment..."):
            assessment = start_assessment(
                user_id=learner["user_id"],
                course_slug=COURSE_SLUG,
                **options,
            )

        st.session_state["edupath_active_assessment"] = assessment
        st.session_state["edupath_current_question"] = 0

        st.session_state[
            _answer_state_key(assessment["assessment_id"])
        ] = {}

        st.session_state.pop("edupath_assessment_result", None)

        st.rerun(scope="fragment")

    except (ValueError, PermissionError) as error:
        st.error(str(error))

    except psycopg.Error:
        st.error(
            "Unable to create your assessment. "
            "Please check your database connection and try again."
        )


def _start_diagnostic(learner: dict) -> None:
    """Preserve the existing diagnostic-assessment entry point."""

    _start_assessment(learner, "diagnostic")



def _submit_adaptive_current_answer(
    assessment: dict,
    question: dict,
    selected_option: str | None,
) -> None:
    """Grade one adaptive answer and request the next question."""

    if selected_option is None:
        st.warning("Please select an answer before continuing.")
        return

    assessment_id = assessment["assessment_id"]
    item_id = question["item_id"]

    try:
        answer = _get_answer_letter(selected_option)

        with st.spinner("Checking your answer and adapting the next question..."):
            result = submit_adaptive_answer(
                user_id=st.session_state[
                    "edupath_authenticated_user_id"
                ],
                assessment_id=assessment_id,
                item_id=item_id,
                answer=answer,
            )

        if result.get("status") == "in_progress":
            next_question = result.get("next_question")

            if not isinstance(next_question, dict):
                raise RuntimeError(
                    "The assessment service did not return the next question."
                )

            updated_assessment = dict(assessment)
            updated_assessment["questions"] = [next_question]
            updated_assessment["total_questions"] = result.get(
                "total_questions",
                ADAPTIVE_QUESTION_COUNT,
            )
            updated_assessment["answered_questions"] = result[
                "answered_questions"
            ]
            updated_assessment["last_answer_feedback"] = result.get(
                "last_answer_feedback"
            )

            st.session_state["edupath_active_assessment"] = (
                updated_assessment
            )
            st.session_state["edupath_current_question"] = 0

        elif result.get("status") == "submitted":
            st.session_state["edupath_assessment_result"] = result
            st.session_state.pop("edupath_active_assessment", None)

        else:
            raise RuntimeError(
                "The assessment service returned an unexpected status."
            )

        st.rerun(scope="fragment")

    except (ValueError, PermissionError) as error:
        st.error(str(error))

    except (RuntimeError, psycopg.Error):
        st.error(
            "We couldn't submit your answer. "
            "Please check your connection and try again."
        )


def _render_question(assessment: dict) -> None:
    """Display an assessment question and its four options."""

    questions = assessment["questions"]

    if not questions:
        st.error("This assessment contains no questions.")
        return

    assessment_type = assessment["assessment_type"]
    is_adaptive = assessment_type in {"practice", "revision"}

    # Adaptive sessions load only their current question.
    # Diagnostic sessions retain their complete question list.
    if is_adaptive:
        total_questions = assessment.get(
            "total_questions",
            ADAPTIVE_QUESTION_COUNT,
        )
        answered_count = assessment.get("answered_questions", 0)
        current_index = 0
        question_number = answered_count + 1
    else:
        total_questions = len(questions)
        answered_count = len(
            st.session_state.get(
                _answer_state_key(assessment["assessment_id"]),
                {},
            )
        )
        current_index = st.session_state.get(
            "edupath_current_question", 0
        )
        current_index = max(
            0,
            min(current_index, total_questions - 1),
        )
        question_number = current_index + 1

    if total_questions <= 0:
        st.error("This assessment contains no questions.")
        return

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

    st.caption(
        f"{_assessment_mode_label(assessment_type)} | "
        f"{total_questions} questions"
    )

    st.progress(
        min(question_number / total_questions, 1.0),
        text=f"Question {question_number} of {total_questions}",
    )

    # Show feedback from the previously submitted adaptive question.
    if is_adaptive:
        previous_feedback = assessment.get("last_answer_feedback")

        if isinstance(previous_feedback, dict):
            if previous_feedback.get("is_correct"):
                st.success("Your previous answer was correct!")
            else:
                st.warning("Your previous answer was incorrect.")

            explanation = previous_feedback.get("explanation")

            if explanation:
                st.info(f"**Explanation:** {explanation}")

    st.caption(
        f"Topic: {question['topic']['name']} | "
        f"Difficulty: {question['difficulty'].title()}"
    )

    st.subheader(question["question_text"])

    options = question["options"]

    if not isinstance(options, list) or len(options) != 4:
        st.error("This question has an invalid option format.")
        return

    st.radio(
        "Choose one answer:",
        options=options,
        index=None,
        key=widget_key,
        on_change=_save_selected_answer,
        args=(assessment_id, item_id, widget_key),
    )

    if is_adaptive:
        st.caption(
            f"Answered: {answered_count} / {total_questions}"
        )

        st.divider()

        if st.button(
            "Submit answer",
            type="primary",
            width="stretch",
            key=f"edupath_submit_adaptive_{assessment_id}_{item_id}",
        ):
            selected_option = st.session_state.get(widget_key)

            _submit_adaptive_current_answer(
                assessment,
                question,
                selected_option,
            )

        return

    # Diagnostic navigation and batch submission remain unchanged.
    st.caption(
        f"Answered: {len(saved_answers)} / {total_questions}"
    )

    st.divider()

    previous_col, next_col = st.columns(2)

    with previous_col:
        st.button(
            "Previous",
            disabled=current_index == 0,
            width="stretch",
            on_click=_change_question,
            args=(-1,),
        )

    with next_col:
        st.button(
            "Next",
            disabled=current_index == total_questions - 1,
            width="stretch",
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
            width="stretch",
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
        "Start another assessment",
        type="primary",
        width="stretch",
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

    render_page_header(
        "ASSESSMENTS",
        "Python programming",
        "Choose the assessment mode that best supports your next learning step.",
    )

    diagnostic_col, practice_col, revision_col = st.columns(3)

    with diagnostic_col:
        with st.container(border=True, key="edupath_diagnostic_card"):
            st.subheader("Diagnostic")
            st.caption(
                "Check your current Python knowledge across all course topics."
            )
            st.info(
                "Uses the full available question bank. "
                "It does not adapt question selection to previous performance."
            )

            if st.button(
                "Start diagnostic",
                width="stretch",
                type="primary",
                key="edupath_start_diagnostic",
            ):
                _start_assessment(learner, "diagnostic")

    with practice_col:
        with st.container(border=True, key="edupath_adaptive_practice_card"):
            st.subheader("Adaptive Practice")
            st.caption(
                "Practise using questions selected from your learning progress."
            )
            st.info(
                "Five questions selected using topic mastery and recent attempts."
            )

            if st.button(
                "Start practice",
                width="stretch",
                key="edupath_start_practice",
            ):
                _start_assessment(learner, "practice")

    with revision_col:
        with st.container(border=True, key="edupath_targeted_revision_card"):
            st.subheader("Targeted Revision")
            st.caption(
                "Give additional attention to topics where you need improvement."
            )
            st.info(
                "Prioritizes weaker topics and adapts question difficulty."
            )

            if st.button(
                "Start revision",
                width="stretch",
                key="edupath_start_revision",
            ):
                _start_assessment(learner, "revision")
