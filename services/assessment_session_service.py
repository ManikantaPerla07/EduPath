from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from services.assessment_service import (
    load_database_url,
    fetch_question_records,
    build_learner_question,
)
from services.adaptive_question_service import (
    MAX_ADAPTIVE_QUESTIONS,
    select_adaptive_questions,
)


VALID_ASSESSMENT_TYPES = {"diagnostic", "practice", "revision"}


def start_assessment(
    user_id: str,
    course_slug: str,
    assessment_type: str = "diagnostic",
    topic_slug: str | None = None,
    question_count: int = 5,
) -> dict[str, Any]:
    """
    Create an assessment session and snapshot its questions.

    Answer keys are stored in the database but never returned
    in the learner-facing question payload.
    """

    # 1. Validate learner ID.
    try:
        learner_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.")

    # 2. Validate assessment details.
    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    if assessment_type not in VALID_ASSESSMENT_TYPES:
        raise ValueError("Invalid assessment type.")

    if assessment_type in {"practice", "revision"}:
        if (
            isinstance(question_count, bool)
            or not isinstance(question_count, int)
            or question_count != MAX_ADAPTIVE_QUESTIONS
        ):
            raise ValueError(
                f"Adaptive assessments must contain "
                f"{MAX_ADAPTIVE_QUESTIONS} questions."
            )

    if topic_slug is not None:
        if not isinstance(topic_slug, str) or not topic_slug.strip():
            raise ValueError("Topic slug cannot be empty.")

    # 3. Fetch questions from the question bank.
    records = fetch_question_records(
        course_slug=course_slug,
        topic_slug=topic_slug,
    )

    if not records:
        raise ValueError("No active questions found for this assessment.")

    selected_topic_id = records[0]["topic_id"] if topic_slug else None

    if selected_topic_id is not None:
        if any(
            record["topic_id"] != selected_topic_id
            for record in records
        ):
            raise ValueError("Assessment questions must belong to one topic.")

    learner_questions = []

    # 4. Create the session and question snapshots atomically.
    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:

        with connection.cursor() as cursor:

            # Verify that the learner exists and is active.
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s
                  AND is_active = TRUE;
                """,
                (learner_id,),
            )

            if cursor.fetchone() is None:
                raise ValueError(
                    "No active learner account found. Sign in first."
                )

            # Find the course.
            cursor.execute(
                """
                SELECT course_id, is_published
                FROM courses
                WHERE course_slug = %s;
                """,
                (course_slug,),
            )

            course_row = cursor.fetchone()

            if course_row is None:
                raise ValueError("Course not found.")

            course_id, is_published = course_row

            if not is_published:
                raise PermissionError(
                    "This course is not currently available to learners."
                )

            # Practice and revision assessments adapt to learner progress.
            # Diagnostic assessments deliberately retain the original
            # full-question-bank behavior.
            if assessment_type in {"practice", "revision"}:

                # Load mastery status for every topic in this course.
                cursor.execute(
                    """
                    SELECT
                        t.topic_slug,
                        COALESCE(
                            lp.mastery_status,
                            'not_assessed'
                        ) AS mastery_status,
                        t.sequence_number AS sequence_order
                    FROM topics AS t
                    LEFT JOIN learner_topic_progress AS lp
                        ON lp.topic_id = t.topic_id
                       AND lp.user_id = %s
                    WHERE t.course_id = %s
                    ORDER BY t.sequence_number;
                    """,
                    (learner_id, course_id),
                )

                progress_rows = cursor.fetchall()

                topic_progress = [
                    {
                        "topic_slug": row[0],
                        "mastery_status": row[1],
                        "sequence_order": row[2],
                    }
                    for row in progress_rows
                ]

                # Collect recently answered questions from submitted sessions.
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
                      AND r.submitted_answer
                          IS DISTINCT FROM 'null'::jsonb
                    ORDER BY
                        s.submitted_at DESC,
                        i.question_order DESC
                    LIMIT 15;
                    """,
                    (learner_id, course_id),
                )

                recent_rows = cursor.fetchall()

                recently_attempted_ids = {
                    str(row[0])
                    for row in recent_rows
                    if row[0] is not None
                }

                records = select_adaptive_questions(
                    questions=records,
                    topic_progress=topic_progress,
                    recently_attempted_question_ids=recently_attempted_ids,
                    # Snapshot only the first question. Remaining
                    # questions are selected after each graded answer.
                    question_count=1,
                )

                if not records:
                    raise ValueError(
                        "No suitable questions are currently available."
                    )

            # Create the assessment session.
            cursor.execute(
                """
                INSERT INTO assessment_sessions (
                    user_id,
                    course_id,
                    topic_id,
                    assessment_type
                )
                VALUES (%s, %s, %s, %s)
                RETURNING assessment_id;
                """,
                (
                    learner_id,
                    course_id,
                    selected_topic_id,
                    assessment_type,
                ),
            )

            assessment_id = cursor.fetchone()[0]

            # Copy each question into the assessment.
            for order, record in enumerate(records, start=1):

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
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING item_id;
                    """,
                    (
                        assessment_id,
                        course_id,
                        record["question_id"],
                        record["topic_id"],
                        record["question_text"],
                        Jsonb(record["options"]),
                        Jsonb(record["correct_answer"]),
                        record["explanation"],
                        record["difficulty"],
                        Decimal("1"),
                        order,
                    ),
                )

                item_id = cursor.fetchone()[0]

                # Build a safe payload for the learner.
                public_question = build_learner_question(record)
                public_question.pop("question_id", None)
                public_question["item_id"] = str(item_id)

                learner_questions.append(public_question)

    # The database transaction commits only after all inserts succeed.
    return {
        "assessment_id": str(assessment_id),
        "assessment_type": assessment_type,
        "status": "in_progress",
        "total_questions": (
            question_count
            if assessment_type in {"practice", "revision"}
            else len(learner_questions)
        ),
        "questions": learner_questions,
    }
