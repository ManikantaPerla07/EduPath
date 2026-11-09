from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from services.assessment_service import (
    build_learner_question,
    load_database_url,
)
from services.adaptive_question_service import (
    MAX_ADAPTIVE_QUESTIONS,
    select_next_adaptive_question,
)
from services.grading_service import grade_mcq_answer
from services.progress_service import refresh_learner_topic_progress




def _parse_uuid(value: Any, field_name: str) -> UUID:
    """Validate and convert a value into a UUID."""

    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"A valid {field_name} is required.")


def normalize_adaptive_answer(answer: Any) -> str:
    """Validate and normalize an MCQ answer to A, B, C, or D."""

    if not isinstance(answer, str):
        raise ValueError("Answer must be a letter from A to D.")

    normalized = answer.strip().upper()

    if normalized not in {"A", "B", "C", "D"}:
        raise ValueError("Answer must be a letter from A to D.")

    return normalized


def _load_topic_progress(cursor, learner_id: UUID, course_id: UUID):
    """Retrieve current mastery status for every course topic."""

    cursor.execute(
        """
        SELECT
            t.topic_slug,
            COALESCE(lp.mastery_status, 'not_assessed'),
            t.sequence_number
        FROM topics AS t
        LEFT JOIN learner_topic_progress AS lp
            ON lp.topic_id = t.topic_id
           AND lp.user_id = %s
        WHERE t.course_id = %s
        ORDER BY t.sequence_number;
        """,
        (learner_id, course_id),
    )

    return [
        {
            "topic_slug": row[0],
            "mastery_status": row[1],
            "sequence_order": row[2],
        }
        for row in cursor.fetchall()
    ]


def _load_question_candidates(cursor, course_id: UUID):
    """Load active question-bank records for dynamic selection."""

    cursor.execute(
        """
        SELECT
            qb.question_id,
            qb.question_code,
            qb.question_type,
            qb.question_text,
            qb.options,
            qb.correct_answer,
            qb.explanation,
            qb.difficulty,
            t.topic_id,
            t.topic_slug,
            t.topic_name,
            t.sequence_number
        FROM question_bank AS qb
        JOIN topics AS t
            ON t.topic_id = qb.topic_id
        WHERE t.course_id = %s
          AND qb.is_active = TRUE
        ORDER BY
            t.sequence_number,
            qb.question_code;
        """,
        (course_id,),
    )

    columns = (
        "question_id",
        "question_code",
        "question_type",
        "question_text",
        "options",
        "correct_answer",
        "explanation",
        "difficulty",
        "topic_id",
        "topic_slug",
        "topic_name",
        "sequence_number",
    )

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def _load_used_question_ids(cursor, assessment_id: UUID) -> set[str]:
    """Find question-bank records already used in this session."""

    cursor.execute(
        """
        SELECT question_bank_id
        FROM assessment_items
        WHERE assessment_id = %s
          AND question_bank_id IS NOT NULL;
        """,
        (assessment_id,),
    )

    return {
        str(row[0])
        for row in cursor.fetchall()
        if row[0] is not None
    }


def _load_recent_question_ids(
    cursor,
    learner_id: UUID,
    course_id: UUID,
) -> set[str]:
    """Find the learner's 15 most recently answered questions."""

    cursor.execute(
        """
        SELECT i.question_bank_id
        FROM assessment_items AS i
        JOIN assessment_sessions AS s
            ON s.assessment_id = i.assessment_id
        JOIN assessment_responses AS r
            ON r.item_id = i.item_id
        WHERE s.user_id = %s
          AND s.course_id = %s
          AND s.status = 'submitted'
          AND i.question_bank_id IS NOT NULL
          AND r.submitted_answer IS DISTINCT FROM 'null'::jsonb
        ORDER BY
            s.submitted_at DESC,
            i.question_order DESC
        LIMIT 15;
        """,
        (learner_id, course_id),
    )

    return {
        str(row[0])
        for row in cursor.fetchall()
        if row[0] is not None
    }


def _build_adaptive_result(
    cursor,
    assessment_id: UUID,
    learner_id: UUID,
    course_slug: str,
) -> dict[str, Any]:
    """Build the final result and finalize the assessment transaction."""

    cursor.execute(
        """
        SELECT
            i.item_id,
            i.topic_id,
            i.question_text,
            i.options,
            i.answer_key,
            i.difficulty,
            i.points,
            r.submitted_answer,
            r.is_correct,
            r.awarded_points,
            r.feedback
        FROM assessment_items AS i
        JOIN assessment_responses AS r
            ON r.item_id = i.item_id
        WHERE i.assessment_id = %s
        ORDER BY i.question_order;
        """,
        (assessment_id,),
    )

    rows = cursor.fetchall()

    if not rows:
        raise RuntimeError("Assessment contains no submitted answers.")

    records = []

    for row in rows:
        (
            item_id,
            topic_id,
            question_text,
            options,
            correct_answer,
            difficulty,
            points,
            submitted_answer,
            is_correct,
            awarded_points,
            feedback,
        ) = row

        records.append({
            "item_id": str(item_id),
            "topic_id": str(topic_id),
            "question_text": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "submitted_answer": submitted_answer,
            "is_correct": is_correct,
            "difficulty": difficulty,
            "points": points,
            "awarded_points": awarded_points,
            "explanation": feedback,
        })

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

    score_percent = (
        awarded_points / total_points * Decimal("100")
    ).quantize(Decimal("0.01"))

    correct_count = sum(
        1 for record in records if record["is_correct"]
    )

    result = {
        "assessment_id": str(assessment_id),
        "status": "submitted",
        "total_questions": len(records),
        "correct_answers": correct_count,
        "incorrect_answers": len(records) - correct_count,
        "unanswered_questions": 0,
        "total_points": total_points,
        "awarded_points": awarded_points,
        "score_percent": score_percent,
        "questions": records,
    }

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
        (score_percent, assessment_id, learner_id),
    )

    if cursor.fetchone() is None:
        raise RuntimeError("Unable to finalize adaptive assessment.")

    # Only finalized assessments contribute to permanent progress.
    refresh_learner_topic_progress(
        cursor=cursor,
        user_id=str(learner_id),
        course_slug=course_slug,
    )

    return result


def submit_adaptive_answer(
    user_id: str,
    assessment_id: str,
    item_id: str,
    answer: Any,
) -> dict[str, Any]:
    """
    Grade and save one adaptive answer, then select the next question.

    The session row is locked throughout the transaction. This prevents
    concurrent requests from submitting the same pending question twice.
    """

    learner_id = _parse_uuid(user_id, "learner user ID")
    session_id = _parse_uuid(assessment_id, "assessment ID")
    question_item_id = _parse_uuid(item_id, "question item ID")

    normalized_answer = normalize_adaptive_answer(answer)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:

        with connection.cursor() as cursor:

            # Verify learner ownership and serialize submissions.
            cursor.execute(
                """
                SELECT
                    s.assessment_id,
                    s.status,
                    s.assessment_type,
                    s.course_id,
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

            (
                _,
                status,
                assessment_type,
                course_id,
                course_slug,
            ) = session

            if assessment_type not in {"practice", "revision"}:
                raise ValueError(
                    "Individual answer submission is only available "
                    "for adaptive assessments."
                )

            if status != "in_progress":
                raise ValueError(
                    "This adaptive assessment is no longer active."
                )

            # Read only the pending question in this learner's session.
            cursor.execute(
                """
                SELECT
                    i.question_bank_id,
                    i.topic_id,
                    i.question_text,
                    i.options,
                    i.answer_key,
                    i.explanation,
                    i.difficulty,
                    i.points,
                    t.topic_slug
                FROM assessment_items AS i
                JOIN topics AS t
                    ON t.topic_id = i.topic_id
                WHERE i.assessment_id = %s
                  AND i.item_id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM assessment_responses AS r
                      WHERE r.item_id = i.item_id
                  )
                FOR UPDATE OF i;
                """,
                (session_id, question_item_id),
            )

            question = cursor.fetchone()

            if question is None:
                raise ValueError(
                    "Question is not pending in this assessment."
                )

            (
                question_bank_id,
                topic_id,
                question_text,
                options,
                correct_answer,
                explanation,
                difficulty,
                points,
                topic_slug,
            ) = question

            # Reuse EduPath's existing grading rules.
            grade = grade_mcq_answer(
                correct_answer=correct_answer,
                submitted_answer=normalized_answer,
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
                    question_item_id,
                    Jsonb(normalized_answer),
                    grade["is_correct"],
                    grade["awarded_points"],
                    grade["explanation"],
                ),
            )

            if cursor.fetchone() is None:
                raise RuntimeError("Unable to save adaptive answer.")

            # Count the completed answers in this session.
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM assessment_items AS i
                JOIN assessment_responses AS r
                    ON r.item_id = i.item_id
                WHERE i.assessment_id = %s;
                """,
                (session_id,),
            )

            answered_count = cursor.fetchone()[0]

            feedback = {
                "is_correct": grade["is_correct"],
                "explanation": grade["explanation"],
                "difficulty": difficulty,
            }

            # Stop after the configured limit.
            if answered_count >= MAX_ADAPTIVE_QUESTIONS:
                result = _build_adaptive_result(
                    cursor,
                    session_id,
                    learner_id,
                    course_slug,
                )

                result["last_answer_feedback"] = feedback
                return result

            topic_progress = _load_topic_progress(
                cursor,
                learner_id,
                course_id,
            )

            candidates = _load_question_candidates(
                cursor,
                course_id,
            )

            used_ids = _load_used_question_ids(
                cursor,
                session_id,
            )

            recent_ids = _load_recent_question_ids(
                cursor,
                learner_id,
                course_id,
            )

            next_record = select_next_adaptive_question(
                questions=candidates,
                topic_progress=topic_progress,
                used_question_ids=used_ids,
                recently_attempted_question_ids=recent_ids,
                last_topic_slug=topic_slug,
                last_difficulty=difficulty,
                last_answer_correct=grade["is_correct"],
            )

            # If the question bank is exhausted, finish the shorter session.
            if next_record is None:
                result = _build_adaptive_result(
                    cursor,
                    session_id,
                    learner_id,
                    course_slug,
                )

                result["last_answer_feedback"] = feedback
                return result

            next_order = answered_count + 1

            cursor.execute(
                """
                INSERT INTO assessment_items (
                    assessment_id,
                    course_id,
                    question_bank_id,
                    topic_id,
                    question_text,
                    options,
                    answer_key,
                    explanation,
                    difficulty,
                    points,
                    question_order
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                RETURNING item_id;
                """,
                (
                    session_id,
                    course_id,
                    next_record["question_id"],
                    next_record["topic_id"],
                    next_record["question_text"],
                    Jsonb(next_record["options"]),
                    Jsonb(next_record["correct_answer"]),
                    next_record["explanation"],
                    next_record["difficulty"],
                    Decimal("1"),
                    next_order,
                ),
            )

            next_item_row = cursor.fetchone()

            if next_item_row is None:
                raise RuntimeError("Unable to create the next question.")

            public_question = build_learner_question(next_record)
            public_question.pop("question_id", None)
            public_question["item_id"] = str(next_item_row[0])

            return {
                "assessment_id": str(session_id),
                "status": "in_progress",
                "answered_questions": answered_count,
                "total_questions": MAX_ADAPTIVE_QUESTIONS,
                "last_answer_feedback": feedback,
                "next_question": public_question,
            }
