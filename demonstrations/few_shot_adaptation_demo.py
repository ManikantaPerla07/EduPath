#!/usr/bin/env python3
"""
EduPath Few-Shot Adaptation Demonstration
Academic Requirement: CSE473 Major Project - UN SDG 4 (Quality Education)

Demonstrates how EduPath adapts explanation depth, code examples, progressive hints,
and practice difficulty across 3 difficulty levels for the EXACT SAME question:
"How does a for loop work with range in Python?"

Supports:
1. Deterministic offline demonstration (instant, version-controlled curated exemplars).
2. Live Gemini API generation via --live flag (grounded with curriculum sources and citation validation).
"""

import argparse
import logging
from pathlib import Path
import sys
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.few_shot_prompting_service import (
    FEW_SHOT_EXEMPLARS,
    format_few_shot_prompt_section,
    get_few_shot_exemplars,
)

logger = logging.getLogger(__name__)

TARGET_QUESTION = "How does a for loop work with range in Python?"

REFERENCE_EDUCATIONAL_CHUNKS = [
    {
        "chunk_id": "chunk-loops-01",
        "title": "EduPath Reference Notes: Loops and Iteration",
        "topic_name": "Loops & Iteration",
        "topic_slug": "loops",
        "content": (
            "A for loop in Python iterates over the elements of an iterable or sequence [S1]. "
            "The range([start], stop[, step]) function generates an immutable sequence of integers. "
            "range(stop) starts at 0 and increments by 1, stopping before the stop integer. "
            "The upper bound is always non-inclusive. range(1, 5) yields 1, 2, 3, and 4."
        ),
        "similarity": 0.92,
    },
    {
        "chunk_id": "chunk-loops-02",
        "title": "EduPath Reference Notes: Iterator Protocol",
        "topic_name": "Loops & Iteration",
        "topic_slug": "loops",
        "content": (
            "Under the hood, Python for loops obtain an iterator using iter() and call next() "
            "repeatedly until StopIteration is raised [S2]. The range sequence produces numbers on demand "
            "with O(1) memory usage regardless of the sequence length."
        ),
        "similarity": 0.85,
    },
]

LEVEL_INSTRUCTIONS = {
    "beginner": (
        "Teach this concept from the fundamentals. Define technical terms simply, "
        "explain one idea at a time, use an everyday analogy, and include one small beginner-friendly example. "
        "Finish with one short practice check."
    ),
    "intermediate": (
        "Use a structured explanation with clear intermediate steps and syntax mechanics. "
        "Include a worked code example with enumerate or step arguments, mention gotchas, "
        "and suggest one short independent practice exercise."
    ),
    "advanced": (
        "Use a rigorous computational approach. Recap essentials briefly, then explore the underlying "
        "iterator protocol, memory complexity, or edge cases. Finish with one challenging practice problem."
    ),
}


def _retrieve_sources_for_demo(query: str) -> list[dict[str, Any]]:
    """Attempt live database retrieval if available, otherwise return verified reference chunks."""
    try:
        from services.retrieval_service import search_knowledge_base
        chunks = search_knowledge_base(
            query=query,
            course_slug="python-basics",
            topic_slug="loops",
            limit=3,
        )
        if chunks:
            return chunks
    except Exception as exc:
        logger.debug("Database retrieval unavailable for demonstration (%s); using verified reference chunks.", exc)

    return REFERENCE_EDUCATIONAL_CHUNKS


def run_demonstration(live: bool = False) -> dict[str, Any]:
    """Run the multi-level personalization demonstration.

    Args:
        live: If True, calls live Gemini API; falls back to deterministic exemplars if unavailable.

    Returns:
        Dictionary containing demonstration results per level and execution metadata.
    """
    mode_label = "LIVE GEMINI API GENERATION" if live else "DETERMINISTIC CURATED EXEMPLARS (OFFLINE)"
    print("=" * 78)
    print("🎓 EDUPATH — FEW-SHOT MULTI-LEVEL PERSONALIZATION DEMONSTRATION")
    print("Assignment Requirement: Adjust explanation style across 2-3 difficulty levels")
    print("Domain: Beginner Python Programming")
    print(f"Target Query: '{TARGET_QUESTION}'")
    print(f"Execution Mode: {mode_label}")
    print("=" * 78)
    print()

    levels = ["beginner", "intermediate", "advanced"]
    results: dict[str, Any] = {
        "target_question": TARGET_QUESTION,
        "mode": "live" if live else "offline",
        "levels": {},
    }

    chunks = _retrieve_sources_for_demo(TARGET_QUESTION) if live else []

    for level in levels:
        print("-" * 78)
        print(f"📌 LEVEL: {level.upper()}")
        persona = (
            "Novice learner needing analogies and gentle pace"
            if level == "beginner"
            else "Student with basic coding knowledge needing syntax precision"
            if level == "intermediate"
            else "Proficient learner ready for internal mechanics and complexity"
        )
        print(f"Target Learner Persona: {persona}")

        level_success = False
        if live:
            try:
                from services.answer_generation_service import generate_grounded_answer

                few_shot_prompt = format_few_shot_prompt_section(level)
                guidance = {
                    "level": level,
                    "instruction": LEVEL_INSTRUCTIONS[level],
                    "few_shot_section": few_shot_prompt,
                }

                live_res = generate_grounded_answer(
                    question=TARGET_QUESTION,
                    retrieved_chunks=chunks,
                    teaching_guidance=guidance,
                )

                model_name = live_res.get("model", "gemini")
                citations = live_res.get("citations", [])
                answer = live_res.get("answer", "")

                print(f"Generation Engine: Live Gemini Model ({model_name}) | Citations Verified: {len(citations)}")
                print("-" * 78)
                print(answer)
                print()

                results["levels"][level] = {
                    "source": "live_gemini",
                    "model": model_name,
                    "answer": answer,
                    "citations": citations,
                }
                level_success = True

            except Exception as exc:
                print(f"⚠️ Live Gemini generation failed ({exc}); gracefully falling back to deterministic exemplar.")
                level_success = False

        if not level_success:
            exemplars = get_few_shot_exemplars(level)
            loop_ex = next(ex for ex in exemplars if "Loops" in ex["topic"])
            print(f"Generation Engine: Deterministic Curated Exemplar | Misconception Addressed: {loop_ex['common_mistake']}")
            print("-" * 78)
            print(loop_ex["demonstration_response"])
            print()

            results["levels"][level] = {
                "source": "curated_exemplar",
                "answer": loop_ex["demonstration_response"],
                "misconception": loop_ex["common_mistake"],
            }

    print("=" * 78)
    print("📊 COMPARATIVE PEDAGOGICAL ANALYSIS")
    print("=" * 78)
    print(f"{'Dimension':<25} | {'Beginner (Level 1)':<20} | {'Intermediate (Level 2)':<25} | {'Advanced (Level 3)'}")
    print("-" * 105)
    print(f"{'Core Analogy / Metaphor':<25} | {'Chef making pancakes':<20} | {'Sequence generator':<25} | {'Iterator protocol (__iter__ / __next__)'}")
    print(f"{'Code Complexity':<25} | {'4 lines, print only':<20} | {'List & enumerate demo':<25} | {'while/StopIteration translation'}")
    print(f"{'Misconception Handled':<25} | {'Off-by-one (stops at 4)':<20} | {'Mutating list in loop':<25} | {'Memory consumption & lazy evaluation'}")
    print(f"{'Practice Task Difficulty':<25} | {'Predict range(1, 4)':<20} | {'Even numbers in reverse':<25} | {'O(1) space Fibonacci generator'}")
    print(f"{'Theoretical Depth':<25} | {'Stop-line concept':<20} | {'Step parameter arithmetic':<25} | {'Time & space complexity (O(1))'}")
    print("=" * 78)
    if not live:
        print("💡 TIP: To generate live responses from Gemini, run: python demonstrations/few_shot_adaptation_demo.py --live")
    print("✅ Demonstration completed successfully.")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="EduPath Few-Shot Personalization Demonstration")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the live Gemini API using current model configuration and retrieved sources.",
    )
    args = parser.parse_args()
    run_demonstration(live=args.live)


if __name__ == "__main__":
    main()
