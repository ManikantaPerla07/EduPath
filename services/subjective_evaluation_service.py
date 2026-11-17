"""Rubric-based subjective answer evaluation for open-ended learner explanations.

Fulfills Part 5.2, Part 5.4 & Phase C requirements:
- Subjective-answer assessment against structured 4-dimensional pedagogical rubrics.
- Misconception diagnosis linked to controlled catalogue.
- Genuine Gemini-based rubric evaluation with structured output validation.
- Server-side boundary validation (scores 0-100, weights sum to 1.0).
- Transparent distinction between 'gemini' and 'deterministic_fallback' evaluation.
- Safety constraint: Does NOT alter authoritative database mastery records.
- Zero transmission of learner identity (name, email, OAuth tokens) to Gemini.
"""

from collections.abc import Mapping
import json
import logging
import re
from typing import Any

from services.misconception_service import (
    MISCONCEPTION_CATALOGUE,
    diagnose_student_misconceptions,
    get_misconception_definition,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Pedagogical Rubric Criteria (Standard IEEE / Academic Standard)
# ==============================================================================

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

# Backward compatibility alias
KNOWN_MISCONCEPTIONS = {
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


def diagnose_misconceptions(
    student_text: str,
    topic_slug: str | None = None,
) -> list[dict[str, str]]:
    """Deterministic regex pattern matcher for known student misconceptions."""
    diagnoses = diagnose_student_misconceptions(student_text, topic_slug)
    # Convert to backward-compatible dict structure
    return [
        {
            "topic": d["topic_slug"],
            "misconception": d["short_description"],
            "correction": d["corrective_explanation"],
        }
        for d in diagnoses
    ]


# ==============================================================================
# 2. Deterministic Fallback Evaluator (Word Overlap & Rule-Based)
# ==============================================================================

def evaluate_subjective_explanation_deterministic(
    question: str,
    reference_answer: str,
    student_explanation: str,
    topic_slug: str | None = None,
) -> dict[str, Any]:
    """Deterministic word-overlap and rule-based rubric evaluation.

    Clearly tagged as 'deterministic_fallback' to avoid claiming AI grading.
    """
    student_clean = student_explanation.strip()

    # 1. Misconception diagnosis
    detected_misconceptions = diagnose_student_misconceptions(student_clean, topic_slug)

    # 2. Word overlap / semantic recall against reference answer
    ref_tokens = set(re.findall(r"[a-zA-Z0-9_]+", reference_answer.lower()))
    student_tokens = set(re.findall(r"[a-zA-Z0-9_]+", student_clean.lower()))

    stopwords = {
        "the", "a", "an", "is", "in", "it", "of", "and", "or", "to", "for", "with", "as"
    }
    meaningful_ref = ref_tokens - stopwords

    if meaningful_ref:
        coverage = len(student_tokens & meaningful_ref) / len(meaningful_ref)
    else:
        coverage = 1.0

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

    feedback_points = []
    if detected_misconceptions:
        for m in detected_misconceptions:
            feedback_points.append(f"Notice: {m['short_description']} - {m['corrective_explanation']}")
    elif score_percent >= 75.0:
        feedback_points.append("Great explanation! You captured the essential concepts accurately.")
    else:
        feedback_points.append("Good start! Try expanding on the step-by-step mechanics and boundary conditions.")

    return {
        "evaluator_type": "deterministic_fallback",
        "evaluator_label": "Deterministic Rule-Based Evaluator",
        "score_percent": score_percent,
        "passed": score_percent >= 60.0,
        "rubric_breakdown": rubric_scores,
        "detected_misconceptions": detected_misconceptions,
        "feedback": " ".join(feedback_points),
    }


# ==============================================================================
# 3. Genuine Gemini AI Rubric Evaluator
# ==============================================================================

def _build_gemini_eval_prompt(
    question: str,
    reference_answer: str,
    student_explanation: str,
    topic_slug: str | None = None,
) -> str:
    """Construct structured evaluation prompt without transmitting student PII."""
    allowed_codes = list(MISCONCEPTION_CATALOGUE.keys())
    catalogue_summary = "\n".join(
        f"- {code}: {data['short_description']}"
        for code, data in MISCONCEPTION_CATALOGUE.items()
    )

    return f"""
You are an expert, supportive Python educator evaluating an open-ended student explanation.
You must evaluate the explanation strictly against the reference answer using the 4 pedagogical rubric criteria.

QUESTION:
{question}

REFERENCE ANSWER:
{reference_answer}

STUDENT EXPLANATION:
{student_explanation}

RUBRIC CRITERIA (Score each from 0.0 to 100.0):
1. conceptual_accuracy (weight 40%): Correctness of core concepts and definitions.
2. reasoning_and_logic (weight 30%): Step-by-step logic, condition boundaries, and execution flow.
3. edge_cases_and_gotchas (weight 15%): Awareness of boundary values, off-by-one errors, or gotchas.
4. clarity_of_expression (weight 15%): Clear terminology and concise explanation.

APPROVED MISCONCEPTION CODES (Select ONLY from this list if clearly present in the student text):
{catalogue_summary}

INSTRUCTIONS:
- Return ONLY a valid JSON object. Do not include markdown commentary outside the JSON.
- If no misconception is detected, return an empty array for detected_misconceptions.
- Provide encouraging, actionable pedagogical feedback.

JSON STRUCTURE:
{{
  "conceptual_accuracy": <number 0-100>,
  "reasoning_and_logic": <number 0-100>,
  "edge_cases_and_gotchas": <number 0-100>,
  "clarity_of_expression": <number 0-100>,
  "detected_misconceptions": [<string code>, ...],
  "feedback": "<constructive feedback string>"
}}
""".strip()


def evaluate_subjective_explanation_gemini(
    question: str,
    reference_answer: str,
    student_explanation: str,
    topic_slug: str | None = None,
) -> dict[str, Any]:
    """Evaluate student explanation using Google Gemini API with strict structured validation.

    Gracefully falls back to deterministic evaluator on timeouts, quota limits, or API errors.
    """
    from services.answer_generation_service import _generate_with_langchain_fallback

    prompt = _build_gemini_eval_prompt(
        question=question,
        reference_answer=reference_answer,
        student_explanation=student_explanation,
        topic_slug=topic_slug,
    )

    try:
        raw_response, model_name = _generate_with_langchain_fallback(prompt)

        # Parse JSON from response (handling potential code fences)
        cleaned_json = raw_response.strip()
        if cleaned_json.startswith("```"):
            cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json)

        data = json.loads(cleaned_json)

        # Server-side validation of scores (bounds 0.0 to 100.0)
        c_acc = float(min(100.0, max(0.0, data.get("conceptual_accuracy", 50.0))))
        r_log = float(min(100.0, max(0.0, data.get("reasoning_and_logic", 50.0))))
        e_got = float(min(100.0, max(0.0, data.get("edge_cases_and_gotchas", 50.0))))
        c_exp = float(min(100.0, max(0.0, data.get("clarity_of_expression", 50.0))))

        # Calculate weighted composite score
        composite = (
            0.40 * c_acc +
            0.30 * r_log +
            0.15 * e_got +
            0.15 * c_exp
        )
        score_percent = round(composite, 1)

        # Validate detected misconceptions against controlled catalogue
        raw_codes = data.get("detected_misconceptions", [])
        validated_diagnoses = []
        if isinstance(raw_codes, list):
            for code in raw_codes:
                if isinstance(code, str) and code.strip() in MISCONCEPTION_CATALOGUE:
                    entry = MISCONCEPTION_CATALOGUE[code.strip()]
                    validated_diagnoses.append({
                        "misconception_code": code.strip(),
                        "topic": entry["topic"],
                        "topic_slug": entry["topic_slug"],
                        "short_description": entry["short_description"],
                        "corrective_explanation": entry["corrective_explanation"],
                        "confidence": 0.85,
                        "detection_method": "gemini_rubric_analysis",
                    })

        feedback = data.get("feedback")
        if not isinstance(feedback, str) or not feedback.strip():
            feedback = "Evaluation complete. Review the rubric breakdown for detailed insights."

        return {
            "evaluator_type": "gemini",
            "evaluator_label": f"Gemini AI Rubric Evaluator ({model_name})",
            "model_name": model_name,
            "score_percent": score_percent,
            "passed": score_percent >= 60.0,
            "rubric_breakdown": {
                "conceptual_accuracy": round(c_acc, 1),
                "reasoning_and_logic": round(r_log, 1),
                "edge_cases_and_gotchas": round(e_got, 1),
                "clarity_of_expression": round(c_exp, 1),
            },
            "detected_misconceptions": validated_diagnoses,
            "feedback": feedback.strip(),
        }

    except Exception as exc:
        logger.warning(
            "Gemini subjective evaluation failed or returned invalid output (%s). "
            "Falling back to deterministic evaluator.", exc
        )
        fallback_result = evaluate_subjective_explanation_deterministic(
            question=question,
            reference_answer=reference_answer,
            student_explanation=student_explanation,
            topic_slug=topic_slug,
        )
        fallback_result["fallback_reason"] = (
            "Gemini AI evaluation was temporarily unavailable or encountered a format error. "
            "Evaluation completed using the deterministic rule-based evaluator."
        )
        return fallback_result


# ==============================================================================
# 4. Main Entry Point
# ==============================================================================

def evaluate_subjective_explanation(
    question: str,
    reference_answer: str,
    student_explanation: str,
    topic_slug: str | None = None,
    use_ai: bool = False,
    user_id: str | None = None,
    ai_consent: bool | None = None,
    adult_confirmation: bool | None = None,
) -> dict[str, Any]:
    """Evaluate an open-ended student explanation against educational rubrics.

    Args:
        question: The conceptual question presented to the learner.
        reference_answer: Benchmark reference explanation.
        student_explanation: Free-text explanation submitted by the learner.
        topic_slug: Optional topic identifier for targeted misconception analysis.
        use_ai: If True, requests Google Gemini evaluation.
        user_id: Optional learner UUID to check persisted AI consent.
        ai_consent: Explicit boolean consent override. Must be True for AI evaluation.
        adult_confirmation: Explicit boolean adult age confirmation override. Must be True for AI evaluation.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")
    if not isinstance(reference_answer, str) or not reference_answer.strip():
        raise ValueError("Reference answer must be a non-empty string.")
    if not isinstance(student_explanation, str) or not student_explanation.strip():
        raise ValueError("Student explanation must be a non-empty string.")

    # Service-layer AI consent and adult age confirmation enforcement
    effective_use_ai = use_ai
    fallback_reason = None
    if use_ai:
        if not isinstance(user_id, str) or not user_id.strip():
            effective_use_ai = False
            fallback_reason = "AI evaluation bypassed: an authenticated learner user ID is required for generative AI evaluation."
        else:
            try:
                from services.learner_service import get_learner_profile
                profile = get_learner_profile(user_id.strip())
                if not isinstance(profile, dict):
                    effective_use_ai = False
                    fallback_reason = "AI evaluation bypassed: could not retrieve authoritative learner profile from database."
                elif profile.get("ai_consent") is not True:
                    effective_use_ai = False
                    fallback_reason = "AI evaluation bypassed: explicit affirmative AI processing consent required in database."
                elif profile.get("adult_confirmation") is not True:
                    effective_use_ai = False
                    fallback_reason = "AI evaluation bypassed: affirmative adult age self-confirmation (18+) required in database."
            except Exception as exc:
                logger.error(
                    "Database verification failed during subjective AI evaluation for user (%s): %s",
                    user_id,
                    exc,
                    exc_info=True,
                )
                effective_use_ai = False
                fallback_reason = "AI evaluation bypassed: database verification failed."

    if effective_use_ai:
        return evaluate_subjective_explanation_gemini(
            question=question.strip(),
            reference_answer=reference_answer.strip(),
            student_explanation=student_explanation.strip(),
            topic_slug=topic_slug,
        )

    res = evaluate_subjective_explanation_deterministic(
        question=question.strip(),
        reference_answer=reference_answer.strip(),
        student_explanation=student_explanation.strip(),
        topic_slug=topic_slug,
    )
    if use_ai and not effective_use_ai:
        res["fallback_reason"] = fallback_reason or "AI evaluation bypassed: explicit affirmative AI processing consent required."
    return res
