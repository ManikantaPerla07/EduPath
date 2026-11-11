
"""Persistent, learner-owned chat session and message operations."""

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from services.assessment_service import load_database_url
from services.langgraph_checkpoint_service import (
    delete_langgraph_thread_checkpoints,
)


DEFAULT_SESSION_LIMIT = 50
MAX_SESSION_LIMIT = 100
DEFAULT_MESSAGE_LIMIT = 100
MAX_MESSAGE_LIMIT = 500
MAX_MESSAGE_LENGTH = 20000
MAX_TITLE_LENGTH = 120
MAX_CITATIONS = 10
CHAT_RATE_LIMIT_WINDOW_MINUTES = 10
MAX_USER_QUESTIONS_PER_WINDOW = 20


class ChatRateLimitError(Exception):
    """Raised when a learner exceeds the rolling chat-question limit."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        wait_minutes = max(1, (self.retry_after_seconds + 59) // 60)
        super().__init__(
            "You have reached the limit of "
            f"{MAX_USER_QUESTIONS_PER_WINDOW} questions every "
            f"{CHAT_RATE_LIMIT_WINDOW_MINUTES} minutes. "
            f"Please try again in about {wait_minutes} minute(s)."
        )


def _validate_uuid(value: str | UUID, field_name: str) -> UUID:
    """Validate and normalize a UUID argument."""

    if isinstance(value, UUID):
        return value

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a valid UUID.")

    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID.") from exc


def _validate_course_slug(course_slug: str) -> str:
    """Validate a course slug."""

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    return course_slug.strip()


def _validate_limit(
    limit: int,
    minimum: int,
    maximum: int,
    field_name: str = "Limit",
) -> int:
    """Validate a bounded integer limit."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not minimum <= limit <= maximum
    ):
        raise ValueError(
            f"{field_name} must be between {minimum} and {maximum}."
        )

    return limit


def _validate_title(title: str) -> str:
    """Validate a conversation title."""

    if not isinstance(title, str):
        raise ValueError("Chat title must be a string.")

    title = title.strip()

    if not title:
        raise ValueError("Chat title cannot be empty.")

    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(
            f"Chat title cannot exceed {MAX_TITLE_LENGTH} characters."
        )

    return title


def _validate_message(
    role: str,
    content: str,
) -> tuple[str, str]:
    """Validate the message role and content."""

    if not isinstance(role, str) or role not in {"user", "assistant"}:
        raise ValueError("Message role must be user or assistant.")

    if not isinstance(content, str):
        raise ValueError("Message content must be a string.")

    content = content.strip()

    if not content:
        raise ValueError("Message content cannot be empty.")

    if len(content) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message cannot exceed {MAX_MESSAGE_LENGTH} characters."
        )

    return role, content


def _validate_citations(citations: list[dict[str, Any]] | None) -> list:
    """Validate citations before storing them in JSONB."""

    if citations is None:
        return []

    if not isinstance(citations, list):
        raise ValueError("Citations must be provided as a list.")

    if len(citations) > MAX_CITATIONS:
        raise ValueError(
            f"A message cannot contain more than {MAX_CITATIONS} citations."
        )

    for citation in citations:
        if not isinstance(citation, Mapping):
            raise ValueError("Each citation must be a mapping.")

    try:
        # Ensure that citation data can safely be stored as JSON.
        normalized = json.loads(
            json.dumps(citations, ensure_ascii=False)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Citations must contain valid JSON data.") from exc

    return normalized


def _session_from_row(row: tuple) -> dict[str, Any]:
    """Convert a chat session database row into a dictionary."""

    return {
        "session_id": str(row[0]),
        "user_id": str(row[1]),
        "course_id": str(row[2]),
        "thread_id": str(row[3]),
        "title": row[4],
        "created_at": row[5],
        "last_activity_at": row[6],
    }


def _message_from_row(row: tuple) -> dict[str, Any]:
    """Convert a chat message database row into a dictionary."""

    return {
        "message_id": str(row[0]),
        "session_id": str(row[1]),
        "role": row[2],
        "content": row[3],
        "citations": row[4] or [],
        "created_at": row[5],
        "feedback": row[6] if len(row) > 6 else None,
    }


def create_chat_session(
    user_id: str | UUID,
    course_slug: str,
    title: str | None = None,
) -> dict[str, Any]:
    """
    Create a chat session for an active learner and an existing course.

    The thread_id is generated by PostgreSQL and can later be used by
    LangGraph as its conversation thread identifier.
    """

    user_uuid = _validate_uuid(user_id, "User ID")
    course_slug = _validate_course_slug(course_slug)

    if title is not None:
        title = _validate_title(title)

    query = """
        INSERT INTO chat_sessions (
            user_id,
            course_id,
            title
        )
        SELECT
            u.user_id,
            c.course_id,
            %s
        FROM users AS u
        CROSS JOIN courses AS c
        WHERE u.user_id = %s
          AND u.is_active = TRUE
          AND c.course_slug = %s
        RETURNING
            session_id,
            user_id,
            course_id,
            thread_id,
            title,
            created_at,
            last_activity_at;
    """

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (title, user_uuid, course_slug),
            )
            row = cursor.fetchone()

    if row is None:
        raise ValueError(
            "An active learner and the requested course are required."
        )

    return _session_from_row(row)



def list_chat_sessions(
    user_id: str | UUID,
    course_slug: str | None = None,
    limit: int = DEFAULT_SESSION_LIMIT,
) -> list[dict[str, Any]]:
    """List chat sessions belonging only to the specified learner."""

    user_uuid = _validate_uuid(user_id, "User ID")

    limit = _validate_limit(
        limit,
        1,
        MAX_SESSION_LIMIT,
        "Session limit",
    )

    if course_slug is not None:
        course_slug = _validate_course_slug(course_slug)

    # Build optional filters without passing an untyped NULL to PostgreSQL.
    filters = ["cs.user_id = %s"]
    parameters = [user_uuid]

    if course_slug is not None:
        filters.append("c.course_slug = %s")
        parameters.append(course_slug)

    where_clause = " AND ".join(filters)

    query = f"""
        SELECT
            cs.session_id,
            cs.user_id,
            cs.course_id,
            cs.thread_id,
            cs.title,
            cs.created_at,
            cs.last_activity_at,
            c.course_slug,
            COUNT(cm.message_id) AS message_count
        FROM chat_sessions AS cs
        JOIN courses AS c
          ON c.course_id = cs.course_id
        LEFT JOIN chat_messages AS cm
          ON cm.session_id = cs.session_id
        WHERE {where_clause}
        GROUP BY
            cs.session_id,
            cs.user_id,
            cs.course_id,
            cs.thread_id,
            cs.title,
            cs.created_at,
            cs.last_activity_at,
            c.course_slug
        ORDER BY cs.last_activity_at DESC
        LIMIT %s;
    """

    parameters.append(limit)

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            rows = cursor.fetchall()

    return [
        {
            **_session_from_row(row[:7]),
            "course_slug": row[7],
            "message_count": row[8],
        }
        for row in rows
    ]



def get_chat_session(
    user_id: str | UUID,
    session_id: str | UUID,
) -> dict[str, Any]:
    """Fetch one session only when it belongs to the learner."""

    user_uuid = _validate_uuid(user_id, "User ID")
    session_uuid = _validate_uuid(session_id, "Session ID")

    query = """
        SELECT
            session_id,
            user_id,
            course_id,
            thread_id,
            title,
            created_at,
            last_activity_at
        FROM chat_sessions
        WHERE session_id = %s
          AND user_id = %s;
    """

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (session_uuid, user_uuid))
            row = cursor.fetchone()

    if row is None:
        raise LookupError("Chat session was not found.")

    return _session_from_row(row)


def get_chat_messages(
    user_id: str | UUID,
    session_id: str | UUID,
    limit: int = DEFAULT_MESSAGE_LIMIT,
) -> list[dict[str, Any]]:
    """Retrieve chronological messages from a learner-owned session."""

    user_uuid = _validate_uuid(user_id, "User ID")
    session_uuid = _validate_uuid(session_id, "Session ID")
    limit = _validate_limit(
        limit,
        1,
        MAX_MESSAGE_LIMIT,
        "Message limit",
    )

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT session_id
                FROM chat_sessions
                WHERE session_id = %s
                  AND user_id = %s;
                """,
                (session_uuid, user_uuid),
            )

            if cursor.fetchone() is None:
                raise LookupError("Chat session was not found.")

            cursor.execute(
                """
                SELECT
                    recent_messages.message_id,
                    recent_messages.session_id,
                    recent_messages.role,
                    recent_messages.content,
                    recent_messages.citations,
                    recent_messages.created_at,
                    feedback.is_helpful
                FROM (
                    SELECT
                        message_id,
                        session_id,
                        role,
                        content,
                        citations,
                        created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at DESC, message_id DESC
                    LIMIT %s
                ) AS recent_messages
                LEFT JOIN chat_message_feedback AS feedback
                  ON feedback.message_id = recent_messages.message_id
                 AND feedback.user_id = %s
                ORDER BY
                    recent_messages.created_at ASC,
                    recent_messages.message_id ASC;
                """,
                (session_uuid, limit, user_uuid),
            )

            rows = cursor.fetchall()

    return [_message_from_row(row) for row in rows]


def save_chat_message(
    user_id: str | UUID,
    session_id: str | UUID,
    role: str,
    content: str,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Save a user or assistant message to a learner-owned session.

    Learner questions additionally lock the active user row and enforce the
    rolling account-level question limit before insertion. Ownership checks,
    message insertion, and activity updates remain transactional.
    """

    user_uuid = _validate_uuid(user_id, "User ID")
    session_uuid = _validate_uuid(session_id, "Session ID")

    role, content = _validate_message(role, content)
    citations = _validate_citations(citations)

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:

            if role == "user":
                # Lock the learner row so concurrent submissions from the
                # same account cannot all pass the rate check simultaneously.
                cursor.execute(
                    """
                    SELECT user_id
                    FROM users
                    WHERE user_id = %s
                      AND is_active = TRUE
                    FOR UPDATE;
                    """,
                    (user_uuid,),
                )

                if cursor.fetchone() is None:
                    raise LookupError(
                        "An active learner account is required."
                    )

            cursor.execute(
                """
                SELECT session_id
                FROM chat_sessions
                WHERE session_id = %s
                  AND user_id = %s
                FOR UPDATE;
                """,
                (session_uuid, user_uuid),
            )

            if cursor.fetchone() is None:
                raise LookupError("Chat session was not found.")

            if role == "user":
                cursor.execute(
                    """
                    SELECT
                        COUNT(*)::INTEGER,
                        GREATEST(
                            1,
                            CEIL(
                                EXTRACT(
                                    EPOCH FROM (
                                        MIN(cm.created_at)
                                        + (%s * INTERVAL '1 minute')
                                        - statement_timestamp()
                                    )
                                )
                            )::INTEGER
                        ) AS retry_after_seconds
                    FROM chat_messages AS cm
                    JOIN chat_sessions AS cs
                      ON cs.session_id = cm.session_id
                    WHERE cs.user_id = %s
                      AND cm.role = 'user'
                      AND cm.created_at >= (
                          statement_timestamp() - (%s * INTERVAL '1 minute')
                      );
                    """,
                    (
                        CHAT_RATE_LIMIT_WINDOW_MINUTES,
                        user_uuid,
                        CHAT_RATE_LIMIT_WINDOW_MINUTES,
                    ),
                )
                rate_row = cursor.fetchone()

                if rate_row is None:
                    raise RuntimeError(
                        "The chat rate-limit query returned no result."
                    )

                recent_question_count = int(rate_row[0] or 0)

                if recent_question_count >= MAX_USER_QUESTIONS_PER_WINDOW:
                    retry_after_seconds = int(
                        rate_row[1] or CHAT_RATE_LIMIT_WINDOW_MINUTES * 60
                    )
                    raise ChatRateLimitError(retry_after_seconds)

            cursor.execute(
                """
                INSERT INTO chat_messages (
                    session_id,
                    role,
                    content,
                    citations
                )
                VALUES (%s, %s, %s, %s)
                RETURNING
                    message_id,
                    session_id,
                    role,
                    content,
                    citations,
                    created_at;
                """,
                (
                    session_uuid,
                    role,
                    content,
                    Jsonb(citations),
                ),
            )

            row = cursor.fetchone()

            cursor.execute(
                """
                UPDATE chat_sessions
                SET
                    last_activity_at = NOW(),
                    title = CASE
                        WHEN (
                            title IS NULL
                            OR BTRIM(title) = ''
                        ) AND %s = 'user'
                        THEN LEFT(%s, %s)
                        ELSE title
                    END
                WHERE session_id = %s
                  AND user_id = %s;
                """,
                (
                    role,
                    content,
                    MAX_TITLE_LENGTH,
                    session_uuid,
                    user_uuid,
                ),
            )

    return _message_from_row(row)


def save_chat_feedback(
    user_id: str | UUID,
    message_id: str | UUID,
    is_helpful: bool,
) -> dict[str, Any]:
    """
    Save or update feedback on an assistant message owned by the learner.

    The INSERT ... SELECT checks message role and session ownership in the
    same statement as the upsert, so another learner cannot rate the message.
    """

    user_uuid = _validate_uuid(user_id, "User ID")
    message_uuid = _validate_uuid(message_id, "Message ID")

    if not isinstance(is_helpful, bool):
        raise ValueError("Feedback rating must be a boolean.")

    query = """
        INSERT INTO chat_message_feedback (
            message_id,
            user_id,
            is_helpful
        )
        SELECT
            cm.message_id,
            cs.user_id,
            %s
        FROM chat_messages AS cm
        JOIN chat_sessions AS cs
          ON cs.session_id = cm.session_id
        WHERE cm.message_id = %s
          AND cs.user_id = %s
          AND cm.role = 'assistant'
        ON CONFLICT (message_id) DO UPDATE
        SET
            is_helpful = EXCLUDED.is_helpful,
            updated_at = NOW()
        WHERE chat_message_feedback.user_id = EXCLUDED.user_id
        RETURNING
            message_id,
            user_id,
            is_helpful,
            created_at,
            updated_at;
    """

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (is_helpful, message_uuid, user_uuid),
            )
            row = cursor.fetchone()

    if row is None:
        raise LookupError("Assistant message was not found.")

    return {
        "message_id": str(row[0]),
        "user_id": str(row[1]),
        "is_helpful": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }


def rename_chat_session(
    user_id: str | UUID,
    session_id: str | UUID,
    title: str,
) -> dict[str, Any]:
    """Rename a session only when it belongs to the learner."""

    user_uuid = _validate_uuid(user_id, "User ID")
    session_uuid = _validate_uuid(session_id, "Session ID")
    title = _validate_title(title)

    query = """
        UPDATE chat_sessions
        SET title = %s
        WHERE session_id = %s
          AND user_id = %s
        RETURNING
            session_id,
            user_id,
            course_id,
            thread_id,
            title,
            created_at,
            last_activity_at;
    """

    with psycopg.connect(load_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (title, session_uuid, user_uuid),
            )
            row = cursor.fetchone()

    if row is None:
        raise LookupError("Chat session was not found.")

    return _session_from_row(row)


def delete_chat_session(
    user_id: str | UUID,
    session_id: str | UUID,
) -> bool:
    """
    Delete an owned conversation and its LangGraph checkpoints.

    Checkpoints are deleted before the session row. If checkpoint cleanup
    fails, the chat transcript remains available rather than leaving hidden
    graph state behind after a successful-looking deletion.
    """

    user_uuid = _validate_uuid(user_id, "User ID")
    session_uuid = _validate_uuid(session_id, "Session ID")
    database_url = load_database_url()

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT thread_id
                FROM chat_sessions
                WHERE session_id = %s
                  AND user_id = %s
                FOR UPDATE;
                """,
                (session_uuid, user_uuid),
            )
            session_row = cursor.fetchone()

            if session_row is None:
                return False

            delete_langgraph_thread_checkpoints(
                thread_id=session_row[0],
                database_url=database_url,
            )

            cursor.execute(
                """
                DELETE FROM chat_sessions
                WHERE session_id = %s
                  AND user_id = %s
                RETURNING session_id;
                """,
                (session_uuid, user_uuid),
            )
            deleted_row = cursor.fetchone()

    return deleted_row is not None
