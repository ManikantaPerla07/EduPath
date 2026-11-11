"""Deterministic, learner-specific study-plan generation and retrieval."""

from __future__ import annotations

import heapq
import math
import re
from datetime import date, datetime, timedelta
from typing import Any, Mapping
from uuid import UUID

import psycopg

from services.assessment_service import load_database_url


MIN_PLAN_DAYS = 1
MAX_PLAN_DAYS = 30
MIN_DAILY_MINUTES = 10
MAX_DAILY_MINUTES = 600
MIN_ACTIVITY_MINUTES = 10

_STATUS_PRIORITY = {
    "needs_revision": 0,
    "developing": 1,
    "not_assessed": 2,
    "candidate_for_mastery": 3,
}

_GOAL_STOP_WORDS = {
    "a", "an", "and", "are", "be", "for", "from", "i", "in",
    "into", "learn", "learning", "me", "my", "of", "on", "python",
    "study", "the", "to", "want", "with",
}


def _parse_user_id(user_id: str) -> UUID:
    """Validate and normalize a learner UUID."""

    try:
        return UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.") from None


def _parse_start_date(value: date | str | None) -> date:
    """Return a date from a date object, ISO string, or today's date."""

    if value is None:
        return date.today()

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("Start date must use YYYY-MM-DD format.") from None

    raise ValueError("Start date must be a date or YYYY-MM-DD string.")


def _validate_plan_settings(
    days: int,
    daily_minutes: int | None,
) -> None:
    if (
        isinstance(days, bool)
        or not isinstance(days, int)
        or not MIN_PLAN_DAYS <= days <= MAX_PLAN_DAYS
    ):
        raise ValueError(
            f"Plan duration must be an integer between "
            f"{MIN_PLAN_DAYS} and {MAX_PLAN_DAYS} days."
        )

    if daily_minutes is not None and (
        isinstance(daily_minutes, bool)
        or not isinstance(daily_minutes, int)
        or not MIN_DAILY_MINUTES <= daily_minutes <= MAX_DAILY_MINUTES
    ):
        raise ValueError(
            f"Daily study time must be an integer between "
            f"{MIN_DAILY_MINUTES} and {MAX_DAILY_MINUTES} minutes."
        )


def _goal_tokens(learning_goal: str | None) -> set[str]:
    if not learning_goal:
        return set()

    return {
        token
        for token in re.findall(r"[a-z0-9]+", learning_goal.lower())
        if token not in _GOAL_STOP_WORDS and len(token) > 1
    }


def _topic_goal_tokens(topic: Mapping[str, Any]) -> set[str]:
    searchable = " ".join(
        str(topic.get(field) or "")
        for field in ("topic_slug", "topic_name", "description")
    )
    return set(re.findall(r"[a-z0-9]+", searchable.lower()))


def order_topics_for_study_plan(
    topics: list[dict[str, Any]],
    learning_goal: str | None = None,
) -> list[dict[str, Any]]:
    """Topologically order topics, prioritizing weak and goal-relevant topics.

    A topic is never placed before one of its prerequisites. Among topics
    whose prerequisites are already placed, the order is:
    needs revision, developing, not assessed, candidate for mastery;
    learning-goal keyword matches break ties, followed by course sequence.
    """

    if not topics:
        raise ValueError("At least one course topic is required.")

    topic_by_id: dict[str, dict[str, Any]] = {}
    for topic in topics:
        topic_id = str(topic.get("topic_id", ""))
        if not topic_id:
            raise ValueError("Every topic must have a topic ID.")
        if topic_id in topic_by_id:
            raise ValueError("Duplicate topic IDs were supplied.")
        topic_by_id[topic_id] = topic

    goal_words = _goal_tokens(learning_goal)
    prerequisites: dict[str, set[str]] = {}
    dependents: dict[str, list[str]] = {topic_id: [] for topic_id in topic_by_id}

    for topic_id, topic in topic_by_id.items():
        prerequisite_ids = {
            str(value) for value in (topic.get("prerequisite_ids") or [])
        }
        missing = prerequisite_ids - topic_by_id.keys()
        if missing:
            raise ValueError(
                "A topic references a prerequisite outside the selected course."
            )

        prerequisites[topic_id] = prerequisite_ids
        for prerequisite_id in prerequisite_ids:
            dependents[prerequisite_id].append(topic_id)

    def priority(topic_id: str) -> tuple[int, int, int, str]:
        topic = topic_by_id[topic_id]
        status_priority = _STATUS_PRIORITY.get(
            topic.get("mastery_status"),
            _STATUS_PRIORITY["developing"],
        )
        goal_match_priority = 0 if goal_words & _topic_goal_tokens(topic) else 1
        try:
            sequence = int(topic.get("sequence_number", 0))
        except (TypeError, ValueError):
            raise ValueError("Topic sequence numbers must be integers.") from None
        return status_priority, goal_match_priority, sequence, topic_id

    indegree = {
        topic_id: len(prerequisite_ids)
        for topic_id, prerequisite_ids in prerequisites.items()
    }

    available = [
        priority(topic_id)
        for topic_id, degree in indegree.items()
        if degree == 0
    ]
    heapq.heapify(available)

    ordered: list[dict[str, Any]] = []
    while available:
        _, _, _, topic_id = heapq.heappop(available)
        ordered.append(topic_by_id[topic_id])

        for dependent_id in dependents[topic_id]:
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                heapq.heappush(available, priority(dependent_id))

    if len(ordered) != len(topics):
        raise ValueError("The course prerequisite graph contains a cycle.")

    return ordered


def _activity_for_topic(topic: Mapping[str, Any]) -> tuple[str, str]:
    """Choose an activity and an explainable reason from learner evidence."""

    attempts = int(topic.get("total_attempts") or 0)
    accuracy = float(topic.get("accuracy_percent") or 0)
    status = topic.get("mastery_status") or "not_assessed"

    if status == "needs_revision":
        return (
            "revision",
            f"Your previous accuracy was {accuracy:.1f}% across {attempts} "
            "answered question(s). Review this topic before progressing.",
        )

    if status == "candidate_for_mastery":
        return (
            "spaced_review",
            f"Your current evidence is {accuracy:.1f}% accuracy across "
            f"{attempts} answered question(s). Use a spaced review to retain it.",
        )

    if status == "developing":
        return (
            "practice",
            f"You have started this topic and currently have {accuracy:.1f}% "
            "accuracy. Focused practice will strengthen your understanding.",
        )

    if status == "not_assessed":
        return (
            "learn",
            "No submitted assessment attempts are recorded for this topic. "
            "Start with the core concepts and examples.",
        )

    raise ValueError(f"Unsupported topic mastery status: {status}")


def build_study_plan_items(
    topics: list[dict[str, Any]],
    start_date: date,
    days: int,
    daily_minutes: int,
    learning_goal: str | None = None,
) -> dict[str, Any]:
    """Build a schedule without database access.

    Every course topic gets one activity. Activities are spread across the
    requested horizon. When the daily budget is small, the horizon is extended
    so each scheduled activity can receive at least ten minutes.
    """

    _validate_plan_settings(days, daily_minutes)
    plan_start = _parse_start_date(start_date)
    ordered_topics = order_topics_for_study_plan(topics, learning_goal)

    maximum_activities_per_day = max(
        1,
        daily_minutes // MIN_ACTIVITY_MINUTES,
    )
    effective_days = max(
        days,
        math.ceil(len(ordered_topics) / maximum_activities_per_day),
    )

    # Distribute activities evenly across the effective plan duration.
    scheduled_groups: dict[date, list[dict[str, Any]]] = {}
    for index, topic in enumerate(ordered_topics):
        day_offset = (index * effective_days) // len(ordered_topics)
        scheduled_date = plan_start + timedelta(days=day_offset)
        scheduled_groups.setdefault(scheduled_date, []).append(topic)

    goal_words = _goal_tokens(learning_goal)
    names_by_id = {
        str(topic["topic_id"]): topic.get("topic_name") or "another topic"
        for topic in ordered_topics
    }

    items: list[dict[str, Any]] = []
    for index, topic in enumerate(ordered_topics, start=1):
        scheduled_date = plan_start + timedelta(
            days=((index - 1) * effective_days) // len(ordered_topics)
        )
        same_day_count = len(scheduled_groups[scheduled_date])
        estimated_minutes = daily_minutes // same_day_count

        activity_type, reason = _activity_for_topic(topic)

        prerequisite_names = [
            names_by_id[str(prerequisite_id)]
            for prerequisite_id in (topic.get("prerequisite_ids") or [])
        ]
        if prerequisite_names:
            reason += (
                " Prerequisite topics are scheduled earlier: "
                + ", ".join(sorted(prerequisite_names))
                + "."
            )

        if goal_words & _topic_goal_tokens(topic):
            reason += " This topic also matches keywords in your stated learning goal."

        items.append({
            "topic_id": UUID(str(topic["topic_id"])),
            "topic_slug": topic.get("topic_slug"),
            "topic_name": topic.get("topic_name"),
            "activity_type": activity_type,
            "scheduled_date": scheduled_date,
            "estimated_minutes": estimated_minutes,
            "recommendation_reason": reason,
            "sequence_number": index,
            "status": "pending",
        })

    return {
        "start_date": plan_start,
        "end_date": plan_start + timedelta(days=effective_days - 1),
        "duration_days": effective_days,
        "daily_study_minutes": daily_minutes,
        "items": items,
    }


def generate_study_plan(
    user_id: str,
    course_slug: str,
    days: int = 7,
    daily_minutes: int | None = None,
    start_date: date | str | None = None,
) -> dict[str, Any]:
    """Generate and persist a personalized active study plan.

    The learner's saved daily study target is used unless an explicit,
    validated override is supplied. Any previous active plan for this
    learner/course is archived in the same transaction.
    """

    learner_id = _parse_user_id(user_id)
    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")
    course_slug = course_slug.strip()

    _validate_plan_settings(days, daily_minutes)
    plan_start = _parse_start_date(start_date)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            # Lock the learner account and profile so account deactivation
            # and concurrent plan generation serialize through this transaction.
            cursor.execute(
                """
                SELECT
                    c.course_id,
                    c.course_name,
                    lp.learning_goal,
                    lp.daily_study_minutes
                FROM users AS u
                JOIN learner_profiles AS lp
                    ON lp.user_id = u.user_id
                JOIN courses AS c
                    ON c.course_slug = %s
                WHERE u.user_id = %s
                  AND u.is_active = TRUE
                  AND lp.adult_confirmation = TRUE
                  AND c.is_published = TRUE
                FOR UPDATE OF u, lp, c;
                """,
                (course_slug, learner_id),
            )
            learner_course = cursor.fetchone()

            if learner_course is None:
                raise PermissionError(
                    "An active, adult-confirmed learner and valid course are required."
                )

            course_id, course_name, learning_goal, profile_daily_minutes = (
                learner_course
            )
            selected_daily_minutes = (
                (profile_daily_minutes if profile_daily_minutes is not None else 45)
                if daily_minutes is None
                else daily_minutes
            )
            _validate_plan_settings(days, selected_daily_minutes)

            cursor.execute(
                """
                SELECT
                    t.topic_id,
                    t.topic_slug,
                    t.topic_name,
                    t.description,
                    t.sequence_number,
                    COALESCE(lp.total_attempts, 0),
                    COALESCE(lp.correct_answers, 0),
                    COALESCE(lp.accuracy_percent, 0),
                    COALESCE(lp.mastery_score, 0),
                    COALESCE(lp.mastery_status, 'not_assessed'),
                    ARRAY(
                        SELECT tp.prerequisite_topic_id
                        FROM topic_prerequisites AS tp
                        WHERE tp.topic_id = t.topic_id
                          AND tp.course_id = t.course_id
                    ) AS prerequisite_ids
                FROM topics AS t
                LEFT JOIN learner_topic_progress AS lp
                    ON lp.topic_id = t.topic_id
                   AND lp.user_id = %s
                WHERE t.course_id = %s
                ORDER BY t.sequence_number;
                """,
                (learner_id, course_id),
            )
            topic_rows = cursor.fetchall()

            if not topic_rows:
                raise ValueError("The selected course has no learning topics.")

            topics = []
            for row in topic_rows:
                (
                    topic_id,
                    topic_slug,
                    topic_name,
                    description,
                    sequence_number,
                    total_attempts,
                    correct_answers,
                    accuracy_percent,
                    mastery_score,
                    mastery_status,
                    prerequisite_ids,
                ) = row
                topics.append({
                    "topic_id": topic_id,
                    "topic_slug": topic_slug,
                    "topic_name": topic_name,
                    "description": description,
                    "sequence_number": sequence_number,
                    "total_attempts": total_attempts,
                    "correct_answers": correct_answers,
                    "accuracy_percent": accuracy_percent,
                    "mastery_score": mastery_score,
                    "mastery_status": mastery_status,
                    "prerequisite_ids": prerequisite_ids or [],
                })

            schedule = build_study_plan_items(
                topics=topics,
                start_date=plan_start,
                days=days,
                daily_minutes=selected_daily_minutes,
                learning_goal=learning_goal,
            )

            title = f"{course_name} — Personalized Study Plan"

            # Keep only one active plan per learner/course in normal use.
            cursor.execute(
                """
                UPDATE study_plans
                SET status = 'archived'
                WHERE user_id = %s
                  AND course_id = %s
                  AND status = 'active';
                """,
                (learner_id, course_id),
            )

            cursor.execute(
                """
                INSERT INTO study_plans (
                    user_id,
                    course_id,
                    title,
                    status,
                    start_date,
                    end_date
                )
                VALUES (%s, %s, %s, 'active', %s, %s)
                RETURNING plan_id, status, created_at;
                """,
                (
                    learner_id,
                    course_id,
                    title,
                    schedule["start_date"],
                    schedule["end_date"],
                ),
            )
            plan_row = cursor.fetchone()
            if plan_row is None:
                raise RuntimeError("Unable to create the study plan.")

            plan_id, plan_status, created_at = plan_row
            saved_items = []

            for item in schedule["items"]:
                cursor.execute(
                    """
                    INSERT INTO study_plan_items (
                        plan_id,
                        course_id,
                        topic_id,
                        activity_type,
                        scheduled_date,
                        estimated_minutes,
                        status,
                        recommendation_reason,
                        sequence_number
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
                    RETURNING plan_item_id;
                    """,
                    (
                        plan_id,
                        course_id,
                        item["topic_id"],
                        item["activity_type"],
                        item["scheduled_date"],
                        item["estimated_minutes"],
                        item["recommendation_reason"],
                        item["sequence_number"],
                    ),
                )
                item_row = cursor.fetchone()
                if item_row is None:
                    raise RuntimeError("Unable to save a study-plan activity.")

                saved_items.append({
                    **item,
                    "plan_item_id": str(item_row[0]),
                })

    return {
        "plan_id": str(plan_id),
        "course_slug": course_slug,
        "title": title,
        "status": plan_status,
        "start_date": schedule["start_date"],
        "end_date": schedule["end_date"],
        "duration_days": schedule["duration_days"],
        "daily_study_minutes": schedule["daily_study_minutes"],
        "created_at": created_at,
        "items": saved_items,
    }


def fetch_active_study_plan(
    user_id: str,
    course_slug: str,
) -> dict[str, Any] | None:
    """Retrieve the active study plan and its ordered activities."""

    learner_id = _parse_user_id(user_id)
    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")
    course_slug = course_slug.strip()

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.plan_id,
                    p.title,
                    p.status,
                    p.start_date,
                    p.end_date,
                    p.created_at,
                    c.course_slug
                FROM users AS u
                JOIN learner_profiles AS lp
                    ON lp.user_id = u.user_id
                JOIN study_plans AS p
                    ON p.user_id = u.user_id
                JOIN courses AS c
                    ON c.course_id = p.course_id
                WHERE u.user_id = %s
                  AND u.is_active = TRUE
                  AND lp.adult_confirmation = TRUE
                  AND c.course_slug = %s
                  AND (
                      c.is_published = TRUE
                      OR u.role = 'admin'
                  )
                  AND p.status IN ('active', 'completed')
                ORDER BY p.created_at DESC
                LIMIT 1;
                """,
                (learner_id, course_slug),
            )
            plan_row = cursor.fetchone()

            if plan_row is None:
                return None

            (
                plan_id,
                title,
                status,
                start_date,
                end_date,
                created_at,
                saved_course_slug,
            ) = plan_row

            cursor.execute(
                """
                SELECT
                    pi.plan_item_id,
                    pi.topic_id,
                    t.topic_slug,
                    t.topic_name,
                    pi.activity_type,
                    pi.scheduled_date,
                    pi.estimated_minutes,
                    pi.status,
                    pi.recommendation_reason,
                    pi.sequence_number
                FROM study_plan_items AS pi
                JOIN topics AS t
                    ON t.topic_id = pi.topic_id
                   AND t.course_id = pi.course_id
                WHERE pi.plan_id = %s
                ORDER BY pi.sequence_number;
                """,
                (plan_id,),
            )
            item_rows = cursor.fetchall()

    items = [
        {
            "plan_item_id": str(row[0]),
            "topic_id": str(row[1]),
            "topic_slug": row[2],
            "topic_name": row[3],
            "activity_type": row[4],
            "scheduled_date": row[5],
            "estimated_minutes": row[6],
            "status": row[7],
            "recommendation_reason": row[8],
            "sequence_number": row[9],
        }
        for row in item_rows
    ]

    return {
        "plan_id": str(plan_id),
        "course_slug": saved_course_slug,
        "title": title,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "created_at": created_at,
        "items": items,
    }


def update_study_plan_item_status(
    user_id: str,
    plan_item_id: str,
    status: str,
) -> dict[str, Any]:
    """Update one activity for its authenticated learner.

    Only activities in the learner's active or completed plan can be changed.
    A plan is marked completed when every activity is completed, and returns
    to active if a completed activity is reopened. The operation is atomic.
    """

    learner_id = _parse_user_id(user_id)

    try:
        item_id = UUID(str(plan_item_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid study-plan item ID is required.") from None

    allowed_statuses = {"pending", "in_progress", "completed", "skipped"}
    if not isinstance(status, str) or status not in allowed_statuses:
        raise ValueError(
            "Activity status must be pending, in_progress, completed, or skipped."
        )

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            # Lock the learner account, item, parent plan, and course while
            # verifying access. Account deactivation must not race this update.
            cursor.execute(
                """
                SELECT
                    p.plan_id,
                    pi.status
                FROM study_plan_items AS pi
                JOIN study_plans AS p
                    ON p.plan_id = pi.plan_id
                   AND p.course_id = pi.course_id
                JOIN users AS u
                    ON u.user_id = p.user_id
                JOIN learner_profiles AS lp
                    ON lp.user_id = u.user_id
                JOIN courses AS c
                    ON c.course_id = p.course_id
                WHERE pi.plan_item_id = %s
                  AND p.user_id = %s
                  AND p.status IN ('active', 'completed')
                  AND u.is_active = TRUE
                  AND lp.adult_confirmation = TRUE
                  AND c.is_published = TRUE
                FOR UPDATE OF pi, p, u, c;
                """,
                (item_id, learner_id),
            )
            item_row = cursor.fetchone()

            if item_row is None:
                raise PermissionError(
                    "Study-plan activity not found or not available to this learner."
                )

            plan_id, previous_status = item_row

            cursor.execute(
                """
                UPDATE study_plan_items
                SET status = %s
                WHERE plan_item_id = %s
                  AND plan_id = %s
                RETURNING plan_item_id;
                """,
                (status, item_id, plan_id),
            )
            updated_row = cursor.fetchone()
            if updated_row is None:
                raise RuntimeError("Unable to update the study-plan activity.")

            cursor.execute(
                """
                SELECT
                    COUNT(*)::INTEGER AS total_activities,
                    COUNT(*) FILTER (WHERE status = 'completed')::INTEGER
                        AS completed_activities
                FROM study_plan_items
                WHERE plan_id = %s;
                """,
                (plan_id,),
            )
            counts = cursor.fetchone()
            if counts is None or counts[0] < 1:
                raise RuntimeError("The study plan contains no activities.")

            total_activities, completed_activities = counts
            plan_status = (
                "completed"
                if completed_activities == total_activities
                else "active"
            )

            cursor.execute(
                """
                UPDATE study_plans
                SET status = %s
                WHERE plan_id = %s
                  AND status IN ('active', 'completed')
                RETURNING status;
                """,
                (plan_status, plan_id),
            )
            plan_row = cursor.fetchone()
            if plan_row is None:
                raise RuntimeError("Unable to update the study-plan status.")

    return {
        "plan_id": str(plan_id),
        "plan_item_id": str(item_id),
        "previous_status": previous_status,
        "status": status,
        "plan_status": plan_status,
        "total_activities": total_activities,
        "completed_activities": completed_activities,
        "completion_percent": round(
            completed_activities / total_activities * 100,
            2,
        ),
    }
