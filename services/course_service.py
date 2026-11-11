"""Course publication and learner access lifecycle services."""

from typing import Any
from uuid import UUID

import psycopg

from services.assessment_service import load_database_url


def _validate_course_slug(course_slug: str) -> str:
    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")
    return course_slug.strip()


def _validate_user_id(user_id: str) -> UUID:
    try:
        return UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid administrator user ID is required.") from None


def _require_active_admin(cursor, user_id: UUID) -> None:
    cursor.execute(
        """
        SELECT role
        FROM users
        WHERE user_id = %s
          AND is_active = TRUE;
        """,
        (user_id,),
    )
    user = cursor.fetchone()

    if user is None or user[0] != "admin":
        raise PermissionError(
            "An active administrator account is required "
            "to manage course publication."
        )


def _publication_readiness(cursor, course_id: UUID) -> dict[str, int]:
    """Count the minimum content prerequisites for publishing a course."""

    cursor.execute(
        """
        SELECT COUNT(*)::INTEGER
        FROM topics
        WHERE course_id = %s;
        """,
        (course_id,),
    )
    topic_count = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)::INTEGER
        FROM question_bank AS qb
        JOIN topics AS t
            ON t.topic_id = qb.topic_id
        WHERE t.course_id = %s
          AND qb.is_active = TRUE;
        """,
        (course_id,),
    )
    active_question_count = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)::INTEGER
        FROM (
            SELECT d.document_id
            FROM documents AS d
            LEFT JOIN document_chunks AS dc
                ON dc.document_id = d.document_id
            WHERE d.course_id = %s
              AND d.archived_at IS NULL
              AND d.processing_status = 'ready'
            GROUP BY d.document_id
            HAVING COUNT(dc.chunk_id) > 0
               AND COUNT(dc.embedding) = COUNT(dc.chunk_id)
        ) AS fully_embedded_documents;
        """,
        (course_id,),
    )
    fully_embedded_document_count = cursor.fetchone()[0]

    return {
        "topic_count": topic_count,
        "active_question_count": active_question_count,
        "fully_embedded_document_count": fully_embedded_document_count,
    }


def get_admin_course_publication_status(
    user_id: str,
    course_slug: str,
) -> dict[str, Any]:
    """Return publication state and readiness counts for an active admin."""

    admin_id = _validate_user_id(user_id)
    course_slug = _validate_course_slug(course_slug)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT course_id, course_name, is_published
                FROM courses
                WHERE course_slug = %s;
                """,
                (course_slug,),
            )
            course = cursor.fetchone()

            if course is None:
                raise LookupError("The requested course was not found.")

            course_id, course_name, is_published = course
            readiness = _publication_readiness(cursor, course_id)

    return {
        "course_slug": course_slug,
        "course_name": course_name,
        "is_published": bool(is_published),
        **readiness,
        "ready_to_publish": (
            readiness["topic_count"] > 0
            and readiness["active_question_count"] > 0
            and readiness["fully_embedded_document_count"] > 0
        ),
    }


def set_course_publication_status(
    user_id: str,
    course_slug: str,
    is_published: bool,
) -> dict[str, Any]:
    """Publish or unpublish a course after checking administrator access.

    Publishing requires at least one topic, one active assessment question,
    and one active ready document whose every chunk has a stored embedding.
    """

    admin_id = _validate_user_id(user_id)
    course_slug = _validate_course_slug(course_slug)

    if not isinstance(is_published, bool):
        raise ValueError("Course publication status must be a boolean.")

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            _require_active_admin(cursor, admin_id)
            cursor.execute(
                """
                SELECT course_id, is_published
                FROM courses
                WHERE course_slug = %s
                FOR UPDATE;
                """,
                (course_slug,),
            )
            course = cursor.fetchone()

            if course is None:
                raise LookupError("The requested course was not found.")

            course_id, current_status = course

            if is_published:
                readiness = _publication_readiness(cursor, course_id)
                missing = []

                if readiness["topic_count"] < 1:
                    missing.append("at least one learning topic")
                if readiness["active_question_count"] < 1:
                    missing.append("at least one active assessment question")
                if readiness["fully_embedded_document_count"] < 1:
                    missing.append(
                        "at least one ready resource with all embeddings stored"
                    )

                if missing:
                    raise ValueError(
                        "Course cannot be published yet. Add "
                        + ", ".join(missing)
                        + "."
                    )

            cursor.execute(
                """
                UPDATE courses
                SET is_published = %s,
                    updated_at = NOW()
                WHERE course_id = %s
                RETURNING is_published;
                """,
                (is_published, course_id),
            )
            updated = cursor.fetchone()

            if updated is None:
                raise RuntimeError("Course publication status was not saved.")

    return {
        "course_slug": course_slug,
        "is_published": bool(updated[0]),
        "changed": bool(current_status) != is_published,
    }


def is_course_published(course_slug: str) -> bool:
    """Return whether the requested course is published for learner access."""

    course_slug = _validate_course_slug(course_slug)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT is_published
                FROM courses
                WHERE course_slug = %s;
                """,
                (course_slug,),
            )
            row = cursor.fetchone()

    if row is None:
        raise LookupError("The requested course was not found.")

    return bool(row[0])
