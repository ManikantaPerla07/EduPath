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


VALID_ASSESSMENT_TYPES = {"diagnostic", "practice", "revision"}


def start_assessment(
    user_id: str,
    course_slug: str,
    assessment_type: str = "diagnostic",
    topic_slug: str | None = None,
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
                SELECT course_id
                FROM courses
                WHERE course_slug = %s;
                """,
                (course_slug,),
            )

            course_row = cursor.fetchone()

            if course_row is None:
                raise ValueError("Course not found.")

            course_id = course_row[0]

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
        "total_questions": len(learner_questions),
        "questions": learner_questions,
    }
