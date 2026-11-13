#!/usr/bin/env python3
"""
Python Fundamentals Interview Coding Exercises
Self-contained, 15-minute reproducible exercises based on EduPath service logic.
"""

# Exercise 1: Robust Input Validator
def validate_daily_minutes(minutes: int) -> int:
    """Validate daily study minutes (10 - 600) rejecting booleans."""
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        raise ValueError("Minutes must be an integer, not a boolean or string.")
    if not (10 <= minutes <= 600):
        raise ValueError("Minutes must be between 10 and 600.")
    return minutes


# Exercise 2: Keyword Token Extractor
def extract_goal_tokens(goal_str: str) -> set[str]:
    """Extract non-trivial lowercase keyword tokens from student learning goal."""
    import re
    stop_words = {"i", "want", "to", "learn", "and", "the", "a", "in", "for", "with"}
    tokens = re.findall(r'[a-z0-9]+', goal_str.lower())
    return {t for t in tokens if t not in stop_words and len(t) > 1}


# Exercise 3: Safe Dictionary Reducer
def compute_accuracy(total_attempts: int, correct_answers: int) -> float:
    """Compute rounded accuracy percentage handling division by zero."""
    if total_attempts <= 0:
        return 0.0
    return round((correct_answers / total_attempts) * 100.0, 2)


if __name__ == "__main__":
    assert validate_daily_minutes(45) == 45
    try:
        validate_daily_minutes(True)
        assert False, "Should have rejected boolean!"
    except ValueError:
        pass

    goal = "I want to learn Python loops and recursion"
    tokens = extract_goal_tokens(goal)
    assert "loops" in tokens and "recursion" in tokens and "want" not in tokens

    assert compute_accuracy(5, 4) == 80.0
    assert compute_accuracy(0, 0) == 0.0
    print("✅ All Python fundamentals exercises passed successfully.")
