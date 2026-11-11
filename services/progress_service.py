
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from services.assessment_service import load_database_url


MIN_REVISION_ATTEMPTS = 3
MIN_MASTERY_ATTEMPTS = 5

MASTERY_ACCURACY_THRESHOLD = Decimal("80")
REVISION_ACCURACY_THRESHOLD = Decimal("50")


def calculate_topic_progress(
    total_attempts: int,
    correct_answers: int,
) -> dict[str, Any]:
    """
    Calculate topic accuracy, mastery score, and mastery status.

    Unanswered questions must not be included in total_attempts.
    """

    if (
        isinstance(total_attempts, bool)
        or not isinstance(total_attempts, int)
        or total_attempts < 0
    ):
        raise ValueError(
            "Total attempts must be a non-negative integer."
        )

    if (
        isinstance(correct_answers, bool)
        or not isinstance(correct_answers, int)
        or correct_answers < 0
        or correct_answers > total_attempts
    ):
        raise ValueError(
            "Correct answers must be between zero and total attempts."
        )

    if total_attempts == 0:
        return {
            "total_attempts": 0,
            "correct_answers": 0,
            "accuracy_percent": Decimal("0.00"),
            "mastery_score": Decimal("0.00"),
            "mastery_status": "not_assessed",
        }

    accuracy = (
        Decimal(correct_answers)
        / Decimal(total_attempts)
        * Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    # Reduce mastery when there is insufficient assessment evidence.
    evidence_factor = min(
        Decimal(total_attempts) / Decimal(MIN_MASTERY_ATTEMPTS),
        Decimal("1"),
    )

    mastery_score = (
        accuracy * evidence_factor
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    if (
        total_attempts >= MIN_REVISION_ATTEMPTS
        and accuracy < REVISION_ACCURACY_THRESHOLD
    ):
        mastery_status = "needs_revision"

    elif (
        total_attempts >= MIN_MASTERY_ATTEMPTS
        and accuracy >= MASTERY_ACCURACY_THRESHOLD
    ):
        mastery_status = "candidate_for_mastery"

    else:
        mastery_status = "developing"

    return {
        "total_attempts": total_attempts,
        "correct_answers": correct_answers,
        "accuracy_percent": accuracy,
        "mastery_score": mastery_score,
        "mastery_status": mastery_status,
    }


def refresh_learner_topic_progress(
    cursor,
    user_id: str,
    course_slug: str,
) -> list[dict[str, Any]]:
    """
    Recalculate and save progress for every topic in a course.

    Reads only submitted assessments belonging to this learner.

    The cursor must belong to the caller's active database transaction.
    Progress changes therefore commit or roll back together with
    the assessment submission.
    """

    try:
        learner_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.")

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    course_slug = course_slug.strip()

    # Aggregate submitted assessment responses by topic.
    # JSONB null represents an unanswered question.
    # Unanswered questions are excluded from attempts.
    cursor.execute(
        """
        WITH topic_results AS (
            SELECT
                i.topic_id,

                COUNT(*) FILTER (
                    WHERE r.response_id IS NOT NULL
                      AND r.submitted_answer
                          IS DISTINCT FROM 'null'::jsonb
                )::INTEGER AS total_attempts,

                COUNT(*) FILTER (
                    WHERE r.response_id IS NOT NULL
                      AND r.submitted_answer
                          IS DISTINCT FROM 'null'::jsonb
                      AND r.is_correct = TRUE
                )::INTEGER AS correct_answers,

                MAX(s.submitted_at) FILTER (
                    WHERE r.response_id IS NOT NULL
                      AND r.submitted_answer
                          IS DISTINCT FROM 'null'::jsonb
                ) AS last_attempted_at

            FROM assessment_items AS i

            JOIN assessment_sessions AS s
                ON s.assessment_id = i.assessment_id

            JOIN courses AS assessment_course
                ON assessment_course.course_id = s.course_id

            LEFT JOIN assessment_responses AS r
                ON r.item_id = i.item_id

            WHERE s.user_id = %s
              AND s.status = 'submitted'
              AND assessment_course.course_slug = %s

            GROUP BY i.topic_id
        )

        SELECT
            t.topic_id,
            COALESCE(tr.total_attempts, 0),
            COALESCE(tr.correct_answers, 0),
            tr.last_attempted_at

        FROM topics AS t

        JOIN courses AS c
            ON c.course_id = t.course_id

        LEFT JOIN topic_results AS tr
            ON tr.topic_id = t.topic_id

        WHERE c.course_slug = %s

        ORDER BY t.sequence_number;
        """,
        (
            learner_id,
            course_slug,
            course_slug,
        ),
    )

    topic_rows = cursor.fetchall()

    if not topic_rows:
        raise ValueError(
            "Course not found or no learning topics are available."
        )

    updated_topics = []

    for (
        topic_id,
        total_attempts,
        correct_answers,
        last_attempted_at,
    ) in topic_rows:

        progress = calculate_topic_progress(
            total_attempts=total_attempts,
            correct_answers=correct_answers,
        )

        # Insert progress or update the existing learner-topic record.
        cursor.execute(
            """
            INSERT INTO learner_topic_progress (
                user_id,
                topic_id,
                total_attempts,
                correct_answers,
                accuracy_percent,
                mastery_score,
                mastery_status,
                last_attempted_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )

            ON CONFLICT (user_id, topic_id)
            DO UPDATE SET
                total_attempts = EXCLUDED.total_attempts,
                correct_answers = EXCLUDED.correct_answers,
                accuracy_percent = EXCLUDED.accuracy_percent,
                mastery_score = EXCLUDED.mastery_score,
                mastery_status = EXCLUDED.mastery_status,
                last_attempted_at = EXCLUDED.last_attempted_at,
                updated_at = NOW();
            """,
            (
                learner_id,
                topic_id,
                progress["total_attempts"],
                progress["correct_answers"],
                progress["accuracy_percent"],
                progress["mastery_score"],
                progress["mastery_status"],
                last_attempted_at,
            ),
        )

        updated_topics.append({
            "topic_id": str(topic_id),
            **progress,
            "last_attempted_at": last_attempted_at,
        })

    return updated_topics


def fetch_learner_topic_progress(
    user_id: str,
    course_slug: str,
) -> list[dict[str, Any]]:
    """
    Retrieve all topic progress records for an active learner.

    Topics without saved progress are included with zero values.
    Only the requested learner's records are returned.
    """

    try:
        learner_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.")

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    course_slug = course_slug.strip()

    query = """
        SELECT
            t.topic_id,
            t.topic_slug,
            t.topic_name,
            t.sequence_number AS sequence_order,

            COALESCE(
                lp.total_attempts, 0
            ) AS total_attempts,

            COALESCE(
                lp.correct_answers, 0
            ) AS correct_answers,

            COALESCE(
                lp.accuracy_percent, 0
            ) AS accuracy_percent,

            COALESCE(
                lp.hints_used, 0
            ) AS hints_used,

            COALESCE(
                lp.mastery_score, 0
            ) AS mastery_score,

            COALESCE(
                lp.mastery_status, 'not_assessed'
            ) AS mastery_status,

            lp.last_attempted_at

        FROM users AS u

        JOIN courses AS c
            ON c.course_slug = %s

        JOIN topics AS t
            ON t.course_id = c.course_id

        LEFT JOIN learner_topic_progress AS lp
            ON lp.user_id = u.user_id
           AND lp.topic_id = t.topic_id

        WHERE u.user_id = %s
          AND u.is_active = TRUE
          AND (
              c.is_published = TRUE
              OR u.role = 'admin'
          )

        ORDER BY t.sequence_number;
    """

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (course_slug, learner_id),
            )

            progress_records = cursor.fetchall()

    if not progress_records:
        raise ValueError(
            "No active learner or course progress was found."
        )

    return progress_records
