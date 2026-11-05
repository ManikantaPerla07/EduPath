from pathlib import Path
import sys
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.assessment_service import (
    fetch_question_records,
    build_learner_question,
)


def run_checks():
    print("\n========== ASSESSMENT SERVICE TEST ==========")

    # 1. Fetch all active Python questions.
    records = fetch_question_records("python-basics")
    assert len(records) == 27, f"Expected 27, got {len(records)}"
    print("All questions fetched: PASS (27)")

    # 2. Check difficulty distribution.
    difficulty_counts = Counter(
        record["difficulty"] for record in records
    )
    assert difficulty_counts == {
        "easy": 9,
        "medium": 9,
        "hard": 9,
    }
    print("Difficulty distribution: PASS")

    # 3. Check that every topic has three questions.
    topic_counts = Counter(
        record["topic_slug"] for record in records
    )
    assert len(topic_counts) == 9
    assert all(count == 3 for count in topic_counts.values())
    print("Topic distribution: PASS (9 topics, 3 each)")

    # 4. Test topic filtering.
    loop_questions = fetch_question_records(
        "python-basics",
        topic_slug="loops",
    )
    assert len(loop_questions) == 3
    print("Topic filter: PASS")

    # 5. Test difficulty filtering.
    medium_questions = fetch_question_records(
        "python-basics",
        difficulty="medium",
    )
    assert len(medium_questions) == 9
    print("Difficulty filter: PASS")

    # 6. Test combined filtering.
    result = fetch_question_records(
        "python-basics",
        topic_slug="loops",
        difficulty="hard",
    )
    assert len(result) == 1
    print("Combined filter: PASS")

    # 7. Test result limit.
    limited_questions = fetch_question_records(
        "python-basics",
        limit=5,
    )
    assert len(limited_questions) == 5
    print("Question limit: PASS")

    # 8. Check that private answer information is not exposed.
    private_fields = {
        "correct_answer",
        "answer_key",
        "explanation",
    }

    for record in records:
        public_question = build_learner_question(record)

        assert not private_fields.intersection(public_question.keys())
        assert len(public_question["options"]) == 4
        assert "correct_answer" not in public_question
        assert "explanation" not in public_question

    print("Answer-key protection: PASS")
    print("Four options per question: PASS")

    # 9. Check invalid input handling.
    try:
        fetch_question_records(
            "python-basics",
            difficulty="expert",
        )
        raise AssertionError("Invalid difficulty was accepted.")
    except ValueError:
        print("Invalid difficulty validation: PASS")

    print("\nALL ASSESSMENT SERVICE CHECKS PASSED.")


if __name__ == "__main__":
    run_checks()
