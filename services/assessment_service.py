from pathlib import Path
import tomllib
from typing import Any

import psycopg
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def load_database_url() -> str:
    """Load the database connection string from local secrets."""

    with SECRETS_FILE.open("rb") as file:
        secrets = tomllib.load(file)

    database_url = secrets.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    return database_url


def fetch_question_records(
    course_slug: str,
    topic_slug: str | None = None,
    difficulty: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch active questions for an assessment.

    This is a backend-only function. Its records include answer keys
    and must never be sent directly to the learner interface.
    """

    if not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    if topic_slug is not None and not topic_slug.strip():
        raise ValueError("Topic slug cannot be empty.")

    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        raise ValueError("Difficulty must be easy, medium, or hard.")

    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
    ):
        raise ValueError("Limit must be a positive integer.")

    conditions = [
        "c.course_slug = %s",
        "qb.is_active = TRUE",
    ]
    parameters = [course_slug]

    if topic_slug is not None:
        conditions.append("t.topic_slug = %s")
        parameters.append(topic_slug)

    if difficulty is not None:
        conditions.append("qb.difficulty = %s")
        parameters.append(difficulty)

    query = f"""
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
        JOIN courses AS c
          ON c.course_id = t.course_id
        WHERE {" AND ".join(conditions)}
        ORDER BY
            t.sequence_number,
            CASE qb.difficulty
                WHEN 'easy' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'hard' THEN 3
            END,
            qb.question_code
    """

    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchall()


def build_learner_question(
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the safe question payload returned to the learner.

    Uses an allowlist so answer keys and explanations cannot leak.
    """

    return {
        "question_id": str(record["question_id"]),
        "question_code": record["question_code"],
        "question_type": record["question_type"],
        "question_text": record["question_text"],
        "options": record["options"],
        "difficulty": record["difficulty"],
        "topic": {
            "slug": record["topic_slug"],
            "name": record["topic_name"],
        },
    }
