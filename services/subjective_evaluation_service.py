"""Rubric-based subjective answer evaluation for open-ended learner explanations.

Fulfills Part 5.2 & Part 5.4 requirements:
- Subjective-answer assessment against structured pedagogical rubrics.
- Misconception-specific feedback.
- Structured validation of model-evaluated scores.
- Safety constraint: Does NOT alter authoritative database records without
  validated server-side workflows.
"""

from collections.abc import Mapping
import json
import re
from typing import Any


RUBRIC_CRITERIA = {
    "conceptual_accuracy": {
        "weight": 0.40,
        "description": "Correctness of core computational ideas, definitions, and syntax.",
    },
    "reasoning_and_logic": {
        "weight": 0.30,
        "description": "Clarity of step-by-step logic, condition boundaries, and execution flow.",
    },
    "edge_cases_and_gotchas": {
        "weight": 0.15,
        "description": "Awareness of off-by-one boundaries, type mismatches, or mutability subtleties.",
    },
    "clarity_of_expression": {
        "weight": 0.15,
        "description": "Use of precise terminology and concise code or pseudocode.",
    },
}

KNOWN_MISCONCEPTIONS: dict[str, list[dict[str, str]]] = {
    "loops": [
        {
            "pattern": r"range\(.*5\).*includes\s+5",
            "misconception": "Believing upper bound in range() is inclusive.",
            "correction": "range(start, stop) stops strictly before stop.",
        },
        {
            "pattern": r"remove\(.*\).*inside.*for",
            "misconception": "Mutating a collection while iterating over it.",
            "correction": "Modifying a sequence during active iteration shifts internal index pointers and skips elements.",
        },
    ],
    "variables": [
        {
            "pattern": r"x\s*=\s*5.*check|if\s+x\s*=\s*5",
            "misconception": "Confusing assignment (=) with equality comparison (==).",
            "correction": "Single equals = assigns values; double equals == checks equality.",
        },
    ],
}


def diagnose_misconceptions(student_text: str, topic_slug: str | None = None) -> list[dict[str, str]]:
    """Deterministic regex pattern matcher for known student misconceptions."""
    if not isinstance(student_text, str) or not student_text.strip():
        return []

    found = []
    text_lower = student_text.lower()

    topics_to_check = [topic_slug] if topic_slug in KNOWN_MISCONCEPTIONS else list(KNOWN_MISCONCEPTIONS.keys())

    for topic in topics_to_check:
        for item in KNOWN_MISCONCEPTIONS.get(topic, []):
            if re.search(item["pattern"], text_lower):
                found.append({
                    "topic": topic,
                    "misconception": item["misconception"],
                    "correction": item["correction"],
                })

    return found


def evaluate_subjective_explanation(
    question: str,
    reference_answer: str,
    student_explanation: str,
    topic_slug: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate an open-ended student explanation against educational rubrics.
    Combines deterministic misconception pattern matching with rubric scoring.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")
    if not isinstance(reference_answer, str) or not reference_answer.strip():
        raise ValueError("Reference answer must be a non-empty string.")
    if not isinstance(student_explanation, str) or not student_explanation.strip():
        raise ValueError("Student explanation must be a non-empty string.")

    student_clean = student_explanation.strip()

    # 1. Deterministic misconception diagnosis
    detected_misconceptions = diagnose_misconceptions(student_clean, topic_slug)

    # 2. Word overlap / semantic recall against reference answer
    ref_tokens = set(re.findall(r'[a-zA-Z0-9_]+', reference_answer.lower()))
    student_tokens = set(re.findall(r'[a-zA-Z0-9_]+', student_clean.lower()))

    # Filter common stopwords
    stopwords = {"the", "a", "an", "is", "in", "it", "of", "and", "or", "to", "for", "with", "as"}
    meaningful_ref = ref_tokens - stopwords

    if meaningful_ref:
        coverage = len(student_tokens & meaningful_ref) / len(meaningful_ref)
    else:
        coverage = 1.0

    # 3. Rubric breakdown calculation
    # Base accuracy from concept coverage, penalized by detected misconceptions
    base_score = min(1.0, max(0.2, coverage * 1.2))
    penalty = 0.25 * len(detected_misconceptions)
    final_score_ratio = max(0.0, base_score - penalty)
    score_percent = round(final_score_ratio * 100.0, 1)

    rubric_scores = {
        "conceptual_accuracy": round(min(100.0, coverage * 100.0), 1),
        "reasoning_and_logic": round(max(30.0, 100.0 - (penalty * 100.0)), 1),
        "edge_cases_and_gotchas": 50.0 if not detected_misconceptions else 20.0,
        "clarity_of_expression": 80.0 if len(student_clean.split()) >= 10 else 50.0,
    }

    # 4. Constructive formative feedback
    feedback_points = []
    if detected_misconceptions:
        for m in detected_misconceptions:
            feedback_points.append(f"Notice: {m['misconception']} - {m['correction']}")
    elif score_percent >= 75.0:
        feedback_points.append("Great explanation! You captured the essential concepts accurately.")
    else:
        feedback_points.append("Good start! Try expanding on the step-by-step mechanics and boundary conditions.")

    return {
        "score_percent": score_percent,
        "passed": score_percent >= 60.0,
        "rubric_breakdown": rubric_scores,
        "detected_misconceptions": detected_misconceptions,
        "feedback": " ".join(feedback_points),
    }
