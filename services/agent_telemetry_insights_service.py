"""Administrator-only aggregate insights for AI Tutor run telemetry."""

from typing import Any
from uuid import UUID

import psycopg

from services.assessment_service import load_database_url


DEFAULT_TREND_DAYS = 14
MAX_TREND_DAYS = 90
STALE_RUN_MINUTES = 15


def _validate_admin_id(user_id: str) -> UUID:
    """Validate the authenticated administrator identifier."""

    try:
        return UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid administrator user ID is required.") from None


def _validate_course_slug(course_slug: str) -> str:
    """Validate the course slug."""

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


def get_agent_run_summary(
    user_id: str,
    course_slug: str,
    days: int = DEFAULT_TREND_DAYS,
) -> dict[str, Any]:
    """
    Return privacy-preserving aggregate run metrics for one course.

    The active administrator role is checked in PostgreSQL before metrics are
    queried. The result contains only counts, percentages, durations, and
    daily aggregates—never learner IDs, session IDs, node traces, error
    details, prompts, or generated answers.
    """

    admin_uuid = _validate_admin_id(user_id)
    course_slug = _validate_course_slug(course_slug)
    days = _validate_days(days)

    summary_query = f"""
        SELECT
            COUNT(ar.run_id)::INTEGER AS total_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'completed'
            )::INTEGER AS completed_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'failed'
            )::INTEGER AS failed_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'running'
                  AND ar.started_at >= NOW() - INTERVAL '{STALE_RUN_MINUTES} minutes'
            )::INTEGER AS running_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'running'
                  AND ar.started_at < NOW() - INTERVAL '{STALE_RUN_MINUTES} minutes'
            )::INTEGER AS stale_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'stopped'
            )::INTEGER AS stopped_runs,
            AVG(ar.duration_ms) FILTER (
                WHERE ar.status = 'completed'
                  AND ar.duration_ms IS NOT NULL
            )::DOUBLE PRECISION AS average_completed_duration_ms
        FROM courses AS c
        JOIN chat_sessions AS cs
          ON cs.course_id = c.course_id
        JOIN agent_runs AS ar
          ON ar.session_id = cs.session_id
        WHERE c.course_slug = %s
          AND ar.started_at >= CURRENT_DATE - (%s - 1)
          AND ar.started_at < CURRENT_DATE + INTERVAL '1 day';
    """

    trend_query = f"""
        SELECT
            day_bucket.day_start::DATE AS report_date,
            COUNT(ar.run_id)::INTEGER AS total_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'completed'
            )::INTEGER AS completed_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'failed'
            )::INTEGER AS failed_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'running'
            )::INTEGER AS running_runs,
            COUNT(ar.run_id) FILTER (
                WHERE ar.status = 'stopped'
            )::INTEGER AS stopped_runs,
            AVG(ar.duration_ms) FILTER (
                WHERE ar.status = 'completed'
                  AND ar.duration_ms IS NOT NULL
            )::DOUBLE PRECISION AS average_completed_duration_ms
        FROM generate_series(
            CURRENT_DATE - (%s - 1),
            CURRENT_DATE,
            INTERVAL '1 day'
        ) AS day_bucket(day_start)
        LEFT JOIN courses AS c
          ON c.course_slug = %s
        LEFT JOIN chat_sessions AS cs
          ON cs.course_id = c.course_id
        LEFT JOIN agent_runs AS ar
          ON ar.session_id = cs.session_id
         AND ar.started_at >= day_bucket.day_start
         AND ar.started_at < day_bucket.day_start + INTERVAL '1 day'
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
                    "to view AI Tutor run insights."
                )

            cursor.execute(summary_query, (course_slug, days))
            summary_row = cursor.fetchone()

            if summary_row is None:
                raise LookupError("AI Tutor run summary is unavailable.")

            cursor.execute(trend_query, (days, course_slug))
            trend_rows = cursor.fetchall()

    total_runs = int(summary_row[0] or 0)
    completed_runs = int(summary_row[1] or 0)
    failed_runs = int(summary_row[2] or 0)
    running_runs = int(summary_row[3] or 0)
    stale_runs = int(summary_row[4] or 0)
    stopped_runs = int(summary_row[5] or 0)
    average_duration = (
        float(summary_row[6])
        if summary_row[6] is not None
        else None
    )

    finished_runs = completed_runs + failed_runs + stopped_runs
    completed_share = (
        (completed_runs / finished_runs) * 100
        if finished_runs
        else None
    )
    failure_rate = (
        (failed_runs / finished_runs) * 100
        if finished_runs
        else None
    )

    return {
        "course_slug": course_slug,
        "days": days,
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "running_runs": running_runs,
        "stale_runs": stale_runs,
        "stopped_runs": stopped_runs,
        "average_completed_duration_ms": average_duration,
        "completed_share_percent": completed_share,
        "failure_rate_percent": failure_rate,
        "trend": [
            {
                "date": row[0],
                "total_runs": int(row[1] or 0),
                "completed_runs": int(row[2] or 0),
                "failed_runs": int(row[3] or 0),
                "running_runs": int(row[4] or 0),
                "stale_runs": int(row[5] or 0),
                "stopped_runs": int(row[6] or 0),
                "average_completed_duration_ms": (
                    float(row[7]) if row[7] is not None else None
                ),
            }
            for row in trend_rows
        ],
    }
