from decimal import Decimal, InvalidOperation
from typing import Any


VALID_ANSWERS = {"A", "B", "C", "D"}


def grade_mcq_answer(
    correct_answer: Any,
    submitted_answer: Any,
    points: Decimal | int | float = Decimal("1"),
    explanation: str | None = None,
) -> dict[str, Any]:
    """
    Grade one MCQ answer.

    Unanswered questions receive zero points.
    Explanations are returned only as part of the grading result,
    after answer submission.
    """

    # Validate the stored answer key.
    if not isinstance(correct_answer, str):
        raise ValueError("Correct answer must be a string.")

    correct_answer = correct_answer.strip().upper()

    if correct_answer not in VALID_ANSWERS:
        raise ValueError("Invalid answer key.")

    # Validate and normalize the learner's answer.
    if submitted_answer is None or (
        isinstance(submitted_answer, str)
        and not submitted_answer.strip()
    ):
        submitted_answer = None

    elif isinstance(submitted_answer, str):
        submitted_answer = submitted_answer.strip().upper()

        if submitted_answer not in VALID_ANSWERS:
            raise ValueError("Submitted answer must be A, B, C, or D.")

    else:
        raise ValueError("Submitted answer must be a string or None.")

    # Validate question points.
    if isinstance(points, bool):
        raise ValueError("Points must be a positive number.")

    try:
        points = Decimal(str(points))
    except (InvalidOperation, ValueError):
        raise ValueError("Points must be a valid number.")

    if not points.is_finite() or points <= 0:
        raise ValueError("Points must be a positive finite number.")

    # Compare answers and calculate marks.
    is_correct = submitted_answer == correct_answer

    awarded_points = points if is_correct else Decimal("0")

    return {
        "is_correct": is_correct,
        "awarded_points": awarded_points,
        "explanation": explanation,
    }
