from collections import defaultdict
from collections.abc import Mapping
from typing import Any


VALID_MASTERY_STATUSES = {
    "not_assessed",
    "needs_revision",
    "developing",
    "candidate_for_mastery",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

MAX_ADAPTIVE_QUESTIONS = 5

# Topics needing revision are prioritized first.
# Untouched topics come next so learners do not miss new material.
STATUS_PRIORITY = {
    "needs_revision": 0,
    "not_assessed": 1,
    "developing": 2,
    "candidate_for_mastery": 3,
}

# Preferred difficulty, followed by fallback difficulties.
DIFFICULTY_PREFERENCE = {
    "not_assessed": ("easy", "medium", "hard"),
    "needs_revision": ("easy", "medium", "hard"),
    "developing": ("medium", "easy", "hard"),
    "candidate_for_mastery": ("hard", "medium", "easy"),
}


def _validate_question_count(question_count: int) -> None:
    """Require a positive integer question count."""

    if (
        isinstance(question_count, bool)
        or not isinstance(question_count, int)
        or question_count <= 0
    ):
        raise ValueError("Question count must be a positive integer.")


def _validate_inputs(
    questions: list[Mapping[str, Any]],
    topic_progress: list[Mapping[str, Any]],
    recently_attempted_question_ids: set[str],
) -> None:
    """Validate the question bank and learner progress inputs."""

    if not isinstance(questions, list):
        raise ValueError("Questions must be provided as a list.")

    if not isinstance(topic_progress, list):
        raise ValueError("Topic progress must be provided as a list.")

    if not isinstance(recently_attempted_question_ids, set):
        raise ValueError("Recently attempted question IDs must be a set.")

    for question in questions:
        if not isinstance(question, Mapping):
            raise ValueError("Each question must be a mapping.")

        required_fields = {
            "question_id",
            "topic_slug",
            "difficulty",
        }

        if not required_fields.issubset(question.keys()):
            raise ValueError("A question is missing required fields.")

        if (
            not isinstance(question["topic_slug"], str)
            or not question["topic_slug"].strip()
            or not isinstance(question["difficulty"], str)
            or not question["difficulty"].strip()
        ):
            raise ValueError("Question topic and difficulty must be non-empty strings.")

        question_id = question["question_id"]

        if (
            question_id is None
            or isinstance(question_id, bool)
            or not str(question_id).strip()
        ):
            raise ValueError("Question ID must be valid.")

        if question["difficulty"] not in VALID_DIFFICULTIES:
            raise ValueError("A question has an invalid difficulty.")

    for progress in topic_progress:
        if not isinstance(progress, Mapping):
            raise ValueError("Each topic progress record must be a mapping.")

        topic_slug = progress.get("topic_slug")
        mastery_status = progress.get("mastery_status")

        if not isinstance(topic_slug, str) or not topic_slug.strip():
            raise ValueError("Topic progress is missing a valid topic slug.")

        if mastery_status not in VALID_MASTERY_STATUSES:
            raise ValueError("Topic progress has an invalid mastery status.")


def _get_sequence_order(value: Any, default: int) -> int:
    """Return a usable topic sequence number."""

    if isinstance(value, bool):
        return default

    try:
        sequence_order = int(value)
    except (TypeError, ValueError, OverflowError):
        return default

    return sequence_order if sequence_order > 0 else default


def _sort_topic_questions(
    questions: list[Mapping[str, Any]],
    mastery_status: str,
) -> list[Mapping[str, Any]]:
    """Sort a topic's questions by preferred difficulty."""

    difficulty_order = {
        difficulty: index
        for index, difficulty in enumerate(
            DIFFICULTY_PREFERENCE[mastery_status]
        )
    }

    return sorted(
        questions,
        key=lambda question: (
            difficulty_order[question["difficulty"]],
            str(question.get("question_code", question["question_id"])),
            str(question["question_id"]),
        ),
    )


def _take_round_robin(
    groups: list[list[Mapping[str, Any]]],
    selected: list[dict[str, Any]],
    question_count: int,
    selected_ids: set[str],
) -> None:
    """Take one question per topic per round until the target is reached."""

    positions = [0] * len(groups)

    while len(selected) < question_count:
        added_in_round = False

        for index, group in enumerate(groups):
            if len(selected) >= question_count:
                break

            position = positions[index]

            if position >= len(group):
                continue

            question = group[position]
            positions[index] += 1

            question_id = str(question["question_id"])

            if question_id in selected_ids:
                continue

            selected.append(dict(question))
            selected_ids.add(question_id)
            added_in_round = True

        if not added_in_round:
            break


def select_adaptive_questions(
    questions: list[Mapping[str, Any]],
    topic_progress: list[Mapping[str, Any]],
    recently_attempted_question_ids: set[str] | None = None,
    question_count: int = 5,
) -> list[dict[str, Any]]:
    """
    Select questions using learner topic mastery and recent attempts.

    Selection behavior:
    1. Prioritize topics needing revision.
    2. Include untouched topics before stronger topics.
    3. Select difficulty according to each topic's mastery status.
    4. Spread questions across topics before selecting another from
       an already represented topic.
    5. Avoid recently attempted questions while fresh alternatives
       are available.
    6. Reuse previously attempted questions only when necessary.

    The original question records are not modified.
    """

    _validate_question_count(question_count)

    if recently_attempted_question_ids is None:
        recently_attempted_question_ids = set()

    _validate_inputs(
        questions,
        topic_progress,
        recently_attempted_question_ids,
    )

    if not questions:
        return []

    progress_by_topic = {
        progress["topic_slug"]: progress
        for progress in topic_progress
    }

    recently_attempted_ids = {
        str(question_id)
        for question_id in recently_attempted_question_ids
    }

    questions_by_topic = defaultdict(list)

    # Keep question IDs unique even if duplicate records are supplied.
    seen_question_ids = set()

    for question in questions:
        question_id = str(question["question_id"])

        if question_id in seen_question_ids:
            continue

        seen_question_ids.add(question_id)
        questions_by_topic[question["topic_slug"]].append(question)

    topic_metadata = []

    for topic_slug, topic_questions in questions_by_topic.items():
        progress = progress_by_topic.get(topic_slug, {})

        mastery_status = progress.get(
            "mastery_status",
            "not_assessed",
        )

        question_sequence = min(
            (
                _get_sequence_order(
                    question.get("sequence_number"),
                    999999,
                )
                for question in topic_questions
            ),
            default=999999,
        )

        sequence_order = _get_sequence_order(
            progress.get("sequence_order"),
            question_sequence,
        )

        topic_metadata.append({
            "topic_slug": topic_slug,
            "mastery_status": mastery_status,
            "sequence_order": sequence_order,
            "questions": topic_questions,
        })

    # Sort topics by mastery priority, then course sequence.
    topic_metadata.sort(
        key=lambda topic: (
            STATUS_PRIORITY[topic["mastery_status"]],
            topic["sequence_order"],
            topic["topic_slug"],
        )
    )

    fresh_groups = []
    recently_attempted_groups = []

    for topic in topic_metadata:
        mastery_status = topic["mastery_status"]

        ordered_questions = _sort_topic_questions(
            topic["questions"],
            mastery_status,
        )

        fresh_questions = [
            question
            for question in ordered_questions
            if str(question["question_id"])
            not in recently_attempted_ids
        ]

        attempted_questions = [
            question
            for question in ordered_questions
            if str(question["question_id"])
            in recently_attempted_ids
        ]

        fresh_groups.append(fresh_questions)
        recently_attempted_groups.append(attempted_questions)

    selected = []
    selected_ids = set()

    # Use fresh questions across all topics first.
    _take_round_robin(
        fresh_groups,
        selected,
        question_count,
        selected_ids,
    )

    # Reuse recent questions only when fresh options are insufficient.
    if len(selected) < question_count:
        _take_round_robin(
            recently_attempted_groups,
            selected,
            question_count,
            selected_ids,
        )

    return selected

DIFFICULTY_LEVELS = ("easy", "medium", "hard")


def adjust_next_difficulty(
    current_difficulty: str,
    is_correct: bool,
) -> str:
    """Increase difficulty after a correct answer and decrease it otherwise."""

    if current_difficulty not in VALID_DIFFICULTIES:
        raise ValueError("Invalid current difficulty.")

    if not isinstance(is_correct, bool):
        raise ValueError("Correctness must be a boolean value.")

    current_index = DIFFICULTY_LEVELS.index(current_difficulty)

    if is_correct:
        next_index = min(current_index + 1, len(DIFFICULTY_LEVELS) - 1)
    else:
        next_index = max(current_index - 1, 0)

    return DIFFICULTY_LEVELS[next_index]


def _difficulty_fallback_order(target_difficulty: str) -> tuple[str, ...]:
    """Return the target difficulty followed by nearby alternatives."""

    if target_difficulty == "easy":
        return ("easy", "medium", "hard")

    if target_difficulty == "medium":
        return ("medium", "easy", "hard")

    if target_difficulty == "hard":
        return ("hard", "medium", "easy")

    raise ValueError("Invalid target difficulty.")


def select_next_adaptive_question(
    questions: list[Mapping[str, Any]],
    topic_progress: list[Mapping[str, Any]],
    used_question_ids: set[str],
    recently_attempted_question_ids: set[str],
    last_topic_slug: str,
    last_difficulty: str,
    last_answer_correct: bool,
) -> dict[str, Any] | None:
    """
    Select one unused question after the learner answers the previous one.

    The current topic is preferred. Its next difficulty is adjusted from the
    latest answer. If that topic has no unused questions, selection moves to
    the next topic using the learner's mastery priority.

    Recently attempted questions are avoided when a fresh alternative exists.
    Questions already used in this assessment are never selected again.
    """

    if not isinstance(used_question_ids, set):
        raise ValueError("Used question IDs must be provided as a set.")

    if not isinstance(recently_attempted_question_ids, set):
        raise ValueError(
            "Recently attempted question IDs must be provided as a set."
        )

    if not isinstance(last_topic_slug, str) or not last_topic_slug.strip():
        raise ValueError("A valid previous topic slug is required.")

    if last_difficulty not in VALID_DIFFICULTIES:
        raise ValueError("Invalid previous question difficulty.")

    if not isinstance(last_answer_correct, bool):
        raise ValueError("Previous answer correctness must be boolean.")

    _validate_inputs(
        questions,
        topic_progress,
        set(str(item) for item in recently_attempted_question_ids),
    )

    if not questions:
        return None

    used_ids = {str(item) for item in used_question_ids}
    recent_ids = {
        str(item) for item in recently_attempted_question_ids
    }

    progress_by_topic = {
        item["topic_slug"]: item
        for item in topic_progress
    }

    questions_by_topic = defaultdict(list)
    seen_ids = set()

    for question in questions:
        question_id = str(question["question_id"])

        if question_id in seen_ids or question_id in used_ids:
            continue

        seen_ids.add(question_id)
        questions_by_topic[question["topic_slug"]].append(question)

    # The previous topic gets first preference.
    ordered_topics = []

    if questions_by_topic.get(last_topic_slug):
        ordered_topics.append(last_topic_slug)

    remaining_topics = [
        topic_slug
        for topic_slug in questions_by_topic
        if topic_slug != last_topic_slug
    ]

    def topic_priority(topic_slug: str) -> tuple:
        progress = progress_by_topic.get(topic_slug, {})
        status = progress.get("mastery_status", "not_assessed")

        if status not in VALID_MASTERY_STATUSES:
            status = "not_assessed"

        sequence = _get_sequence_order(
            progress.get("sequence_order"),
            999999,
        )

        return (
            STATUS_PRIORITY[status],
            sequence,
            topic_slug,
        )

    ordered_topics.extend(sorted(remaining_topics, key=topic_priority))

    # Build candidates using difficulty preferences for each topic.
    candidate_groups = []

    for topic_slug in ordered_topics:
        topic_questions = questions_by_topic[topic_slug]

        if topic_slug == last_topic_slug:
            target = adjust_next_difficulty(
                last_difficulty,
                last_answer_correct,
            )
            difficulty_order = _difficulty_fallback_order(target)
        else:
            progress = progress_by_topic.get(topic_slug, {})
            status = progress.get("mastery_status", "not_assessed")

            if status not in VALID_MASTERY_STATUSES:
                status = "not_assessed"

            difficulty_order = DIFFICULTY_PREFERENCE[status]

        ordered_questions = []

        for difficulty in difficulty_order:
            matching = [
                question
                for question in topic_questions
                if question["difficulty"] == difficulty
            ]

            matching.sort(
                key=lambda question: (
                    str(question.get("question_code", "")),
                    str(question["question_id"]),
                )
            )

            ordered_questions.extend(matching)

        if ordered_questions:
            candidate_groups.append(ordered_questions)

    # Prefer questions not recently attempted across the available choices.
    fresh_candidates = [
        question
        for group in candidate_groups
        for question in group
        if str(question["question_id"]) not in recent_ids
    ]

    if fresh_candidates:
        return dict(fresh_candidates[0])

    # If every unused candidate was attempted previously, reuse one.
    for group in candidate_groups:
        if group:
            return dict(group[0])

    return None
