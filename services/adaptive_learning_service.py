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
    learner_profile: dict[str, Any] | None = None,
    misconceptions: list[dict[str, Any]] | list[str] | None = None,
) -> dict[str, Any]:
    """Select teaching guidance from highest-ranked retrieved topic and learner profile.

    Adheres strictly to the Phase B1 selection policy:
    1. When topic mastery indicates 'needs_revision', prioritize foundational explanations.
    2. When mastery indicates 'developing', use intermediate guided explanations.
    3. When mastery indicates 'candidate_for_mastery', use advanced explanations.
    4. When topic performance is unavailable/not_assessed, use declared proficiency as baseline.
    5. Apply preferred language and explanation style as presentation preferences.
    6. Known learner misconceptions inject targeted corrective exemplars into few-shot context.
    7. Never allow declared proficiency or misconceptions to override factual course evidence.
    """
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

    declared_proficiency = None
    preferred_language = None
    explanation_style = None
    if isinstance(learner_profile, Mapping):
        declared_proficiency = learner_profile.get("proficiency_level")
        preferred_language = learner_profile.get("preferred_language")
        explanation_style = learner_profile.get("explanation_style")

    if selected_progress is None or selected_progress.get("mastery_status") == "not_assessed":
        # Topic mastery unavailable: use declared proficiency baseline
        if declared_proficiency == "advanced":
            strategy = dict(TEACHING_STRATEGIES["candidate_for_mastery"])
            mastery_status = "not_assessed"
        elif declared_proficiency == "intermediate":
            strategy = dict(TEACHING_STRATEGIES["developing"])
            mastery_status = "not_assessed"
        else:
            strategy = dict(DEFAULT_TEACHING_GUIDANCE)
            mastery_status = "not_assessed"
        topic_name = None
    else:
        mastery_status = selected_progress.get("mastery_status")
        if mastery_status not in TEACHING_STRATEGIES:
            raise ValueError("Learner topic mastery status is invalid.")
        strategy = dict(TEACHING_STRATEGIES[mastery_status])
        topic_name = selected_progress.get("topic_name")
        if topic_name is not None and not isinstance(topic_name, str):
            raise ValueError("Topic name must be a string or None.")

    # Apply presentation preferences (style and language) without overriding facts
    custom_instructions = [strategy["instruction"]]
    if explanation_style and explanation_style.strip():
        custom_instructions.append(
            f"Presentation style preference: The learner prefers {explanation_style.strip()} explanations."
        )
    if preferred_language and preferred_language.strip() and preferred_language.strip().lower() != "english":
        custom_instructions.append(
            f"Language preference: Respond in {preferred_language.strip()}, keeping all Python code and syntax in English."
        )
    effective_instruction = " ".join(custom_instructions)

    # Format few-shot section with level, declared proficiency, mastery, and misconceptions
    few_shot_section = format_few_shot_prompt_section(
        level=strategy["level"],
        declared_proficiency=declared_proficiency,
        topic_mastery=mastery_status,
        misconceptions=misconceptions,
        preferred_style=explanation_style,
        preferred_language=preferred_language,
    )

    return {
        "topic_slug": primary_topic_slug,
        "topic_name": topic_name,
        "mastery_status": mastery_status,
        "declared_proficiency": declared_proficiency,
        "level": strategy["level"],
        "label": strategy["label"],
        "instruction": effective_instruction,
        "few_shot_section": few_shot_section,
    }


def get_learner_teaching_profile(
    user_id: str | None,
    course_slug: str,
    retrieved_chunks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Load learner progress, profile preferences, and misconceptions to derive teaching guidance.

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

    learner_profile = None
    active_misconceptions = []
    try:
        from services.learner_service import get_learner_profile
        learner_profile = get_learner_profile(user_id=user_id)
    except Exception:
        pass

    try:
        from services.misconception_service import fetch_active_learner_misconceptions
        active_misconceptions = fetch_active_learner_misconceptions(user_id=user_id)
    except Exception:
        pass

    return build_adaptive_teaching_profile(
        retrieved_chunks=retrieved_chunks,
        topic_progress=topic_progress,
        learner_profile=learner_profile,
        misconceptions=active_misconceptions,
    )
