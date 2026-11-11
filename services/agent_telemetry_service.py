"""Privacy-conscious lifecycle tracking for authenticated EduPath agent runs."""

import re
from typing import Sequence
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from services.assessment_service import load_database_url


WORKFLOW_NAME = "adaptive_tutor"
ALLOWED_RUN_STATUSES = {"completed", "failed", "stopped"}
MAX_NODE_NAMES = 50
MAX_NODE_NAME_LENGTH = 80
MAX_ERROR_CODE_LENGTH = 80
MAX_DURATION_MS = 86_400_000
_ERROR_CODE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")


def _validate_uuid(value: str | UUID, field_name: str) -> UUID:
    """Validate and normalize a UUID."""

    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a valid UUID.")
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID.") from exc


def _validate_workflow_name(workflow_name: str) -> str:
    """Validate a short non-sensitive workflow identifier."""

    if (
        not isinstance(workflow_name, str)
        or not workflow_name.strip()
        or len(workflow_name.strip()) > MAX_NODE_NAME_LENGTH
    ):
        raise ValueError("Workflow name must be a non-empty short string.")
    return workflow_name.strip()


def _validate_node_sequence(
    node_sequence: Sequence[str] | None,
) -> list[str]:
    """Validate node labels without accepting arbitrary payloads."""

    if node_sequence is None:
        return []
    if (
        not isinstance(node_sequence, Sequence)
        or isinstance(node_sequence, (str, bytes))
    ):
        raise ValueError("Node sequence must be a list of node names.")
    if len(node_sequence) > MAX_NODE_NAMES:
        raise ValueError(
            f"Node sequence cannot exceed {MAX_NODE_NAMES} entries."
        )

    normalized = []
    for node_name in node_sequence:
        if (
            not isinstance(node_name, str)
            or not node_name.strip()
            or len(node_name.strip()) > MAX_NODE_NAME_LENGTH
        ):
            raise ValueError("Each node name must be a short non-empty string.")
        normalized.append(node_name.strip())
    return normalized


def _validate_duration(duration_ms: int) -> int:
    """Validate a non-negative duration bounded to one day."""

    if (
        isinstance(duration_ms, bool)
        or not isinstance(duration_ms, int)
        or not 0 <= duration_ms <= MAX_DURATION_MS
    ):
        raise ValueError(
            f"Duration must be an integer between 0 and {MAX_DURATION_MS}."
        )
    return duration_ms


def _validate_error_code(error_code: str | None) -> str | None:
    """Accept only an exception-class-style code, never an error message."""

    if error_code is None:
        return None
    if (
        not isinstance(error_code, str)
        or not _ERROR_CODE_PATTERN.fullmatch(error_code)
        or len(error_code) > MAX_ERROR_CODE_LENGTH
    ):
        raise ValueError("Error code must be a short identifier.")
    return error_code


def start_agent_run(
    user_id: str | UUID,
    session_id: str | UUID | None = None,
    workflow_name: str = WORKFLOW_NAME,
) -> UUID:
    """
    Start an authenticated agent-run record.

    When a chat session is supplied, ownership is verified in the same INSERT
    statement. No prompt, answer, or learner profile data is persisted here.
    """

    user_uuid = _validate_uuid(user_id, "User ID")
    session_uuid = (
        _validate_uuid(session_id, "Session ID")
        if session_id is not None
        else None
    )
    workflow_name = _validate_workflow_name(workflow_name)

    query = """
        INSERT INTO agent_runs (
            user_id,
            session_id,
            workflow_name,
            status
        )
        SELECT
            u.user_id,
            cs.session_id,
            %s,
            'running'
        FROM users AS u
        LEFT JOIN chat_sessions AS cs
          ON cs.session_id = %s::uuid
         AND cs.user_id = u.user_id
        WHERE u.user_id = %s
          AND u.is_active = TRUE
          AND (%s::uuid IS NULL OR cs.session_id IS NOT NULL)
        RETURNING run_id;
    """

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    workflow_name,
                    session_uuid,
                    user_uuid,
                    session_uuid,
                ),
            )
            row = cursor.fetchone()

    if row is None:
        raise LookupError(
            "An active learner and an owned chat session are required."
        )
    return row[0]


def finish_agent_run(
    user_id: str | UUID,
    run_id: str | UUID,
    status: str,
    duration_ms: int,
    node_sequence: Sequence[str] | None = None,
    error_code: str | None = None,
) -> bool:
    """
    Finish one of the learner's running agent records.

    Failure details are stored only as a validated exception-class code.
    """

    user_uuid = _validate_uuid(user_id, "User ID")
    run_uuid = _validate_uuid(run_id, "Run ID")

    if not isinstance(status, str) or status not in ALLOWED_RUN_STATUSES:
        raise ValueError("Agent run status must be completed, failed, or stopped.")

    duration_ms = _validate_duration(duration_ms)
    node_sequence = _validate_node_sequence(node_sequence)
    error_code = _validate_error_code(error_code)

    if status == "failed" and error_code is None:
        raise ValueError("A failed agent run requires an error code.")
    if status != "failed" and error_code is not None:
        raise ValueError("Only failed agent runs may contain an error code.")

    query = """
        UPDATE agent_runs
        SET
            status = %s,
            duration_ms = %s,
            node_sequence = %s,
            error_code = %s,
            completed_at = NOW()
        WHERE run_id = %s
          AND user_id = %s
          AND status = 'running'
        RETURNING run_id;
    """

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    status,
                    duration_ms,
                    Jsonb(node_sequence),
                    error_code,
                    run_uuid,
                    user_uuid,
                ),
            )
            row = cursor.fetchone()

    return row is not None
