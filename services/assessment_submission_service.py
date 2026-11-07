from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from services.assessment_service import load_database_url
from services.grading_service import grade_mcq_answer
from services.progress_service import refresh_learner_topic_progress


def _parse_uuid(value: Any, field_name: str) -> UUID:
    """Validate and convert a value into a UUID."""

    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"A valid {field_name} is required.")


def _build_result(
    assessment_id: UUID,
    records: list[dict[str, Any]],
    saved_score: Decimal | None = None,
) -> dict[str, Any]:
    """Build a learner-facing result after assessment submission."""

    total_questions = len(records)

    if total_questions == 0:
        raise RuntimeError("Assessment contains no questions.")

    total_points = sum(
        (record["points"] for record in records),
        Decimal("0"),
    )

    awarded_points = sum(
        (record["awarded_points"] for record in records),
        Decimal("0"),
    )

    if total_points <= 0:
        raise RuntimeError("Assessment has no valid total points.")

    calculated_score = (
        awarded_points / total_points * Decimal("100")
    ).quantize(Decimal("0.01"))

    correct_count = sum(
        1 for record in records if record["is_correct"]
    )

    unanswered_count = sum(
        1
        for record in records
        if record["submitted_answer"] is None
    )

    return {
        "assessment_id": str(assessment_id),
        "status": "submitted",
        "total_questions": total_questions,
        "correct_answers": correct_count,
        "incorrect_answers": (
            total_questions - correct_count - unanswered_count
        ),
        "unanswered_questions": unanswered_count,
        "total_points": total_points,
        "awarded_points": awarded_points,
        "score_percent": (
            saved_score
            if saved_score is not None
            else calculated_score
        ),
        "questions": records,
    }


def _load_saved_result(
    cursor,
    assessment_id: UUID,
    saved_score: Decimal | None,
) -> dict[str, Any]:
    """
    Retrieve an already-submitted result.

    This makes repeated submission requests safe.
    """

    cursor.execute(
        """
        SELECT
            i.item_id,
            i.topic_id,
            i.question_text,
            i.options,
            i.answer_key,
            i.explanation,
            i.difficulty,
            i.points,
            r.submitted_answer,
            r.is_correct,
            r.awarded_points
        FROM assessment_items AS i
        LEFT JOIN assessment_responses AS r
            ON r.item_id = i.item_id
        WHERE i.assessment_id = %s
        ORDER BY i.question_order;
        """,
        (assessment_id,),
    )

    rows = cursor.fetchall()

    if not rows:
        raise RuntimeError("Assessment contains no questions.")

    records = []

    for row in rows:
        (
            item_id,
            topic_id,
            question_text,
            options,
            correct_answer,
            explanation,
            difficulty,
            points,
            submitted_answer,
            is_correct,
            awarded_points,
        ) = row

        if is_correct is None or awarded_points is None:
            raise RuntimeError(
                "Submitted assessment has incomplete saved responses."
            )

        records.append({
            "item_id": str(item_id),
            "topic_id": str(topic_id),
            "question_text": question_text,
            "options": options,
            "submitted_answer": submitted_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "points": points,
            "awarded_points": awarded_points,
            "difficulty": difficulty,
            "explanation": explanation,
        })

    return _build_result(
        assessment_id,
        records,
        saved_score=saved_score,
    )


def submit_assessment(
    user_id: str,
    assessment_id: str,
    answers: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Grade and finalize an assessment.

    Security:
    - Checks that the assessment belongs to the learner.
    - Locks the assessment session during submission.
    - Reads correct answers from saved question snapshots.
    - Rejects unknown question IDs.
    - Prevents modification after submission.
    - Returns previously saved results on repeated requests.

    Missing answers are treated as unanswered questions.
    """

    learner_id = _parse_uuid(user_id, "learner user ID")
    session_id = _parse_uuid(assessment_id, "assessment ID")

    if not isinstance(answers, Mapping):
        raise ValueError("Answers must be provided as a mapping.")

    normalized_answers = {}

    for raw_item_id, answer in answers.items():
        item_id = _parse_uuid(raw_item_id, "question item ID")

        if item_id in normalized_answers:
            raise ValueError("Duplicate question item IDs were supplied.")

        normalized_answers[item_id] = answer

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:

        with connection.cursor() as cursor:

            # Lock and verify the session.
            # A different learner cannot submit this assessment.
            cursor.execute(
                """
                SELECT
                    s.assessment_id,
                    s.status,
                    s.score_percent,
                    c.course_slug
                FROM assessment_sessions AS s
                JOIN courses AS c
                    ON c.course_id = s.course_id
                WHERE s.assessment_id = %s
                  AND s.user_id = %s
                FOR UPDATE OF s;
                """,
                (session_id, learner_id),
            )

            session = cursor.fetchone()

            if session is None:
                raise PermissionError(
                    "Assessment not found for this learner."
                )

            _, status, saved_score, course_slug = session

            # Repeated requests return the previously saved result.
            if status == "submitted":
                result = _load_saved_result(
                    cursor,
                    session_id,
                    saved_score,
                )

                # Recalculate progress from all submitted assessments.
                refresh_learner_topic_progress(
                    cursor=cursor,
                    user_id=str(learner_id),
                    course_slug=course_slug,
                )

                return result

            if status != "in_progress":
                raise ValueError(
                    "This assessment is not available for submission."
                )

            # Read answer keys from the assessment snapshots.
            cursor.execute(
                """
                SELECT
                    item_id,
                    topic_id,
                    question_text,
                    options,
                    answer_key,
                    explanation,
                    difficulty,
                    points
                FROM assessment_items
                WHERE assessment_id = %s
                ORDER BY question_order;
                """,
                (session_id,),
            )

            question_rows = cursor.fetchall()

            if not question_rows:
                raise RuntimeError(
                    "Assessment contains no questions."
                )

            valid_item_ids = {
                row[0] for row in question_rows
            }

            # Reject answers belonging to another assessment.
            unknown_ids = (
                set(normalized_answers) - valid_item_ids
            )

            if unknown_ids:
                raise ValueError(
                    "One or more submitted question IDs "
                    "do not belong to this assessment."
                )

            result_records = []

            # Grade each question and save its response.
            for row in question_rows:

                (
                    item_id,
                    topic_id,
                    question_text,
                    options,
                    correct_answer,
                    explanation,
                    difficulty,
                    points,
                ) = row

                raw_answer = normalized_answers.get(item_id)

                # Normalize answers before saving.
                if isinstance(raw_answer, str):
                    submitted_answer = (
                        raw_answer.strip().upper() or None
                    )
                else:
                    submitted_answer = raw_answer

                # Reuse the existing MCQ grading service.
                grade = grade_mcq_answer(
                    correct_answer=correct_answer,
                    submitted_answer=submitted_answer,
                    points=points,
                    explanation=explanation,
                )

                cursor.execute(
                    """
                    INSERT INTO assessment_responses (
                        item_id,
                        submitted_answer,
                        is_correct,
                        awarded_points,
                        feedback
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING response_id;
                    """,
                    (
                        item_id,
                        Jsonb(submitted_answer),
                        grade["is_correct"],
                        grade["awarded_points"],
                        grade["explanation"],
                    ),
                )

                if cursor.fetchone() is None:
                    raise RuntimeError(
                        "Unable to save assessment response."
                    )

                result_records.append({
                    "item_id": str(item_id),
                    "topic_id": str(topic_id),
                    "question_text": question_text,
                    "options": options,
                    "submitted_answer": submitted_answer,
                    "correct_answer": correct_answer,
                    "is_correct": grade["is_correct"],
                    "points": points,
                    "awarded_points": grade["awarded_points"],
                    "difficulty": difficulty,
                    "explanation": grade["explanation"],
                })

            # Calculate the final score.
            result = _build_result(
                session_id,
                result_records,
            )

            # Finalize the assessment session.
            cursor.execute(
                """
                UPDATE assessment_sessions
                SET status = 'submitted',
                    score_percent = %s,
                    submitted_at = NOW()
                WHERE assessment_id = %s
                  AND user_id = %s
                  AND status = 'in_progress'
                RETURNING assessment_id;
                """,
                (
                    result["score_percent"],
                    session_id,
                    learner_id,
                ),
            )

            if cursor.fetchone() is None:
                raise RuntimeError(
                    "Unable to finalize assessment."
                )
                        # Update all topic progress records in the same transaction.
            refresh_learner_topic_progress(
                cursor=cursor,
                user_id=str(learner_id),
                course_slug=course_slug,
            )

    # The transaction commits only after all responses and
    # the final assessment status have been saved successfully.
    return result
