"""Read-only learner data tools for the authenticated EduPath tutor."""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
import json
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from services.progress_service import fetch_learner_topic_progress
from services.study_plan_service import fetch_active_study_plan


def _json_default(value: Any) -> Any:
    """Serialize database values without losing date or decimal meaning."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


def _learner_scope(runtime: ToolRuntime) -> tuple[str, str]:
    """Read authenticated learner scope from server-controlled graph state."""

    state = runtime.state

    if not isinstance(state, Mapping):
        raise ValueError("Authenticated learner context is unavailable.")

    user_id = state.get("user_id")
    course_slug = state.get("course_slug")

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Authenticated learner context is unavailable.")

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course context is unavailable.")

    return user_id.strip(), course_slug.strip()


@tool
def get_my_learning_progress(runtime: ToolRuntime) -> str:
    """Get the authenticated learner's topic attempts, accuracy, and mastery.

    Use this only when the learner asks about their own learning performance,
    scores, completed practice, topic accuracy, or mastery. The learner and
    course identifiers are supplied securely by EduPath.
    """

    user_id, course_slug = _learner_scope(runtime)
    records = fetch_learner_topic_progress(
        user_id=user_id,
        course_slug=course_slug,
    )

    topics = [
        {
            "topic_slug": record["topic_slug"],
            "topic_name": record["topic_name"],
            "total_attempts": record["total_attempts"],
            "correct_answers": record["correct_answers"],
            "accuracy_percent": record["accuracy_percent"],
            "mastery_score": record["mastery_score"],
            "mastery_status": record["mastery_status"],
            "last_attempted_at": record["last_attempted_at"],
        }
        for record in records
    ]

    return json.dumps(
        {
            "course_slug": course_slug,
            "topic_count": len(topics),
            "topics": topics,
        },
        default=_json_default,
        ensure_ascii=False,
    )


@tool
def get_my_study_plan(runtime: ToolRuntime) -> str:
    """Get the authenticated learner's current study plan and activities.

    Use this only when the learner asks about their own study plan, schedule,
    upcoming learning activities, or pending revision tasks. The learner and
    course identifiers are supplied securely by EduPath.
    """

    user_id, course_slug = _learner_scope(runtime)
    plan = fetch_active_study_plan(
        user_id=user_id,
        course_slug=course_slug,
    )

    if plan is None:
        return json.dumps(
            {
                "found": False,
                "course_slug": course_slug,
                "message": "No current study plan was found.",
            }
        )

    items = plan.get("items") or []
    counts = {
        status: sum(1 for item in items if item.get("status") == status)
        for status in ("pending", "in_progress", "completed", "skipped")
    }
    total_items = len(items)
    completed_items = counts["completed"]
    completion_percent = (
        round(completed_items / total_items * 100, 1)
        if total_items
        else 0.0
    )

    activities = [
        {
            "topic_name": item["topic_name"],
            "topic_slug": item["topic_slug"],
            "activity_type": item["activity_type"],
            "scheduled_date": item["scheduled_date"],
            "estimated_minutes": item["estimated_minutes"],
            "status": item["status"],
            "recommendation_reason": item["recommendation_reason"],
        }
        for item in items[:20]
    ]

    summary = {
        "found": True,
        "course_slug": course_slug,
        "title": plan["title"],
        "status": plan["status"],
        "start_date": plan["start_date"],
        "end_date": plan["end_date"],
        "completion_percent": completion_percent,
        "activity_counts": counts,
        "total_activities": total_items,
        "activities": activities,
        "activities_truncated": total_items > len(activities),
    }

    return json.dumps(
        summary,
        default=_json_default,
        ensure_ascii=False,
    )
