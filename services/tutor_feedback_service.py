"""Administrator-only aggregate insights for AI Tutor answer feedback."""

from typing import Any
from uuid import UUID

import psycopg

from services.assessment_service import load_database_url


DEFAULT_TREND_DAYS = 14
MAX_TREND_DAYS = 90


def _validate_admin_id(user_id: str) -> UUID:
    """Validate the authenticated administrator identifier."""

    try:
        return UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid administrator user ID is required.") from None


def _validate_course_slug(course_slug: str) -> str:
    """Validate a course slug."""

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")
    return course_slug.strip()


def _validate_days(days: int) -> int:
    """Validate a bounded daily trend window."""

    if (
        isinstance(days, bool)
        or not isinstance(days, int)
        or not 1 <= days <= MAX_TREND_DAYS
    ):
        raise ValueError(
            f"Trend days must be between 1 and {MAX_TREND_DAYS}."
        )
    return days


def get_tutor_feedback_summary(
    user_id: str,
    course_slug: str,
    days: int = DEFAULT_TREND_DAYS,
) -> dict[str, Any]:
    """
    Return privacy-preserving aggregate answer-feedback metrics.

    The active administrator role is verified in PostgreSQL. Results contain
    only course-level counts, percentages, and daily aggregates—never learner
    identifiers, conversation text, or individual feedback records.
    """

    admin_uuid = _validate_admin_id(user_id)
    course_slug = _validate_course_slug(course_slug)
    days = _validate_days(days)

    summary_query = """
        SELECT
            COUNT(cm.message_id)::INTEGER AS assistant_answer_count,
            COUNT(feedback.message_id)::INTEGER AS rated_answer_count,
            COUNT(feedback.message_id) FILTER (
                WHERE feedback.is_helpful IS TRUE
            )::INTEGER AS helpful_count,
            COUNT(feedback.message_id) FILTER (
                WHERE feedback.is_helpful IS FALSE
            )::INTEGER AS not_helpful_count
        FROM courses AS c
        JOIN chat_sessions AS cs
          ON cs.course_id = c.course_id
        JOIN chat_messages AS cm
          ON cm.session_id = cs.session_id
         AND cm.role = 'assistant'
        LEFT JOIN chat_message_feedback AS feedback
          ON feedback.message_id = cm.message_id
        WHERE c.course_slug = %s;
    """

    trend_query = """
        SELECT
            day_bucket.day_start::DATE AS report_date,
            COUNT(feedback.message_id) FILTER (
                WHERE c.course_id IS NOT NULL
            )::INTEGER AS rated_count,
            COUNT(feedback.message_id) FILTER (
                WHERE c.course_id IS NOT NULL
                  AND feedback.is_helpful IS TRUE
            )::INTEGER AS helpful_count,
            COUNT(feedback.message_id) FILTER (
                WHERE c.course_id IS NOT NULL
                  AND feedback.is_helpful IS FALSE
            )::INTEGER AS not_helpful_count
        FROM generate_series(
            CURRENT_DATE - (%s - 1),
            CURRENT_DATE,
            INTERVAL '1 day'
        ) AS day_bucket(day_start)
        LEFT JOIN chat_message_feedback AS feedback
          ON feedback.created_at >= day_bucket.day_start
         AND feedback.created_at < day_bucket.day_start + INTERVAL '1 day'
        LEFT JOIN chat_messages AS cm
          ON cm.message_id = feedback.message_id
         AND cm.role = 'assistant'
        LEFT JOIN chat_sessions AS cs
          ON cs.session_id = cm.session_id
        LEFT JOIN courses AS c
          ON c.course_id = cs.course_id
         AND c.course_slug = %s
        GROUP BY day_bucket.day_start
        ORDER BY day_bucket.day_start;
    """

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT role
                FROM users
                WHERE user_id = %s
                  AND is_active = TRUE;
                """,
                (admin_uuid,),
            )
            admin = cursor.fetchone()

            if admin is None or admin[0] != "admin":
                raise PermissionError(
                    "An active administrator account is required "
                    "to view AI Tutor feedback insights."
                )

            cursor.execute(summary_query, (course_slug,))
            summary_row = cursor.fetchone()

            if summary_row is None:
                raise LookupError("Tutor feedback summary is unavailable.")

            cursor.execute(
                trend_query,
                (days, course_slug),
            )
            trend_rows = cursor.fetchall()

    assistant_answers = int(summary_row[0] or 0)
    rated_answers = int(summary_row[1] or 0)
    helpful_count = int(summary_row[2] or 0)
    not_helpful_count = int(summary_row[3] or 0)

    rating_coverage = (
        (rated_answers / assistant_answers) * 100
        if assistant_answers
        else None
    )
    helpful_rate = (
        (helpful_count / rated_answers) * 100
        if rated_answers
        else None
    )

    return {
        "course_slug": course_slug,
        "assistant_answer_count": assistant_answers,
        "rated_answer_count": rated_answers,
        "helpful_count": helpful_count,
        "not_helpful_count": not_helpful_count,
        "rating_coverage_percent": rating_coverage,
        "helpful_percent": helpful_rate,
        "trend": [
            {
                "date": row[0],
                "rated_count": int(row[1] or 0),
                "helpful_count": int(row[2] or 0),
                "not_helpful_count": int(row[3] or 0),
            }
            for row in trend_rows
        ],
    }
