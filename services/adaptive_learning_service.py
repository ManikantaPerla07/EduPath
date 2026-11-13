"""Create personalized teaching guidance from existing learner progress."""

from collections.abc import Mapping
from typing import Any

from services.progress_service import fetch_learner_topic_progress
from services.few_shot_prompting_service import format_few_shot_prompt_section


TEACHING_STRATEGIES = {
    "not_assessed": {
        "level": "beginner",
        "label": "Beginner-friendly learning",
        "instruction": (
            "Teach this concept from the fundamentals. "
            "Define technical terms simply, explain one idea at a time, "
            "and include one small beginner-friendly example. "
            "Do not assume prior knowledge."
        ),
    },
    "needs_revision": {
        "level": "foundational_revision",
        "label": "Foundational revision",
        "instruction": (
            "Use a supportive revision-focused teaching approach. "
            "Break the concept into small steps, revisit relevant "
            "fundamentals, explain the reasoning behind each step, "
            "and include a simple worked example. Finish with one "
            "short guided practice question."
        ),
    },
    "developing": {
        "level": "guided_practice",
        "label": "Guided practice",
        "instruction": (
            "Use a structured explanation with clear intermediate steps. "
            "Connect the concept to previously learned ideas where "
            "appropriate, include a worked example, and suggest one "
            "short independent practice exercise."
        ),
    },
    "candidate_for_mastery": {
        "level": "advanced_application",
        "label": "Advanced application",
        "instruction": (
            "Use a more challenging teaching approach. Briefly recap "
            "essential fundamentals, then explore deeper applications "
            "or edge cases when supported by the approved sources. "
            "Finish with one challenging practice problem."
        ),
    },
}


DEFAULT_TEACHING_GUIDANCE = TEACHING_STRATEGIES["not_assessed"]


def build_adaptive_teaching_profile(
    retrieved_chunks: list[dict[str, Any]],
    topic_progress: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select teaching guidance from the highest-ranked retrieved topic."""

    if not isinstance(retrieved_chunks, list):
        raise ValueError("Retrieved chunks must be a list.")

    if not isinstance(topic_progress, list):
        raise ValueError("Topic progress must be a list.")

    primary_topic_slug = None

    # Retrieval results are ranked by relevance. Use the first topic
    # represented in those results as the primary learning topic.
    for chunk in retrieved_chunks:
        if not isinstance(chunk, Mapping):
            raise ValueError("Every retrieved chunk must be a mapping.")

        topic_slug = chunk.get("topic_slug")

        if topic_slug is not None:
            if not isinstance(topic_slug, str) or not topic_slug.strip():
                raise ValueError("Retrieved topic slug is invalid.")

            primary_topic_slug = topic_slug.strip()
            break

    selected_progress = None

    if primary_topic_slug is not None:
        for record in topic_progress:
            if not isinstance(record, Mapping):
                raise ValueError("Every progress record must be a mapping.")

            if record.get("topic_slug") == primary_topic_slug:
                selected_progress = record
                break

    if selected_progress is None:
        strategy = DEFAULT_TEACHING_GUIDANCE

        return {
            "topic_slug": primary_topic_slug,
            "topic_name": None,
            "mastery_status": "not_assessed",
            "few_shot_section": format_few_shot_prompt_section(strategy["level"]),
            **strategy,
        }

    mastery_status = selected_progress.get("mastery_status")

    if mastery_status not in TEACHING_STRATEGIES:
        raise ValueError("Learner topic mastery status is invalid.")

    strategy = TEACHING_STRATEGIES[mastery_status]

    topic_name = selected_progress.get("topic_name")

    if topic_name is not None and not isinstance(topic_name, str):
        raise ValueError("Topic name must be a string or None.")

    return {
        "topic_slug": primary_topic_slug,
        "topic_name": topic_name,
        "mastery_status": mastery_status,
        "few_shot_section": format_few_shot_prompt_section(strategy["level"]),
        **strategy,
    }


def get_learner_teaching_profile(
    user_id: str | None,
    course_slug: str,
    retrieved_chunks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Load learner progress and derive teaching guidance.

    When no learner ID is supplied, return None. This preserves the
    ability to run the tutoring graph without learner-specific data.
    """

    if user_id is None:
        return None

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Learner user ID must be a non-empty string.")

    topic_progress = fetch_learner_topic_progress(
        user_id=user_id,
        course_slug=course_slug,
    )

    return build_adaptive_teaching_profile(
        retrieved_chunks=retrieved_chunks,
        topic_progress=topic_progress,
    )
