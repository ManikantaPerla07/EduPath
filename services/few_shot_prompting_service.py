"""Few-shot personalization service demonstrating level- and mistake-adaptive tutoring.

This module fulfills the core CSE473 requirement:
"Build a tutor that adapts its explanation style using a few examples of a
student's level/mistakes (few-shot), and show it adjusts across 2–3 difficulty levels."

It provides curated, version-controlled exemplars across three distinct levels:
1. Beginner: Simple analogies, short sentences, gentle hints, elementary practice.
2. Intermediate: Technical syntax, step-by-step logic, common error patterns, worked code.
3. Advanced: Deeper computational model, iterator/underlying mechanics, edge cases, challenge problem.
"""

from typing import Any


FEW_SHOT_EXEMPLARS: dict[str, list[dict[str, Any]]] = {
    "beginner": [
        {
            "topic": "Loops & Iteration",
            "concept": "for loop in range()",
            "level": "beginner",
            "common_mistake": "Off-by-one error: believing range(1, 5) counts to 5 including 5.",
            "sample_question": "How does a for loop work with range in Python?",
            "demonstration_response": (
                "Think of a for loop like an automated checklist or an assembly line [S1]. "
                "Each time the loop runs, it picks up the next item and does a task with it.\n\n"
                "**Analogy:** Imagine a chef making 4 pancakes. You tell the chef to count from 1 up to (but stopping before) 5.\n\n"
                "```python\n"
                "for count in range(1, 5):\n"
                "    print(f'Pancake #{count}')\n"
                "```\n\n"
                "**Common Gotcha:** Notice that `range(1, 5)` stops right before 5! It outputs 1, 2, 3, and 4 [S1].\n\n"
                "**Hint:** The second number in `range(start, stop)` is always the stop line you don't cross.\n\n"
                "**Quick Practice:** What will `range(1, 4)` print? Try it out!"
            ),
        },
        {
            "topic": "Variables and Data Types",
            "concept": "Variable Assignment vs Equality",
            "level": "beginner",
            "common_mistake": "Confusing assignment (=) with equality comparison (==).",
            "sample_question": "Why does x = 5 give an error when I try to check if x is 5?",
            "demonstration_response": (
                "In Python, a single equals sign `=` is like putting a label on a storage box [S1]. "
                "It means: 'Store this value into the box'.\n\n"
                "If you want to ask Python 'Are these two things equal?', you must use two equals signs `==` [S1].\n\n"
                "```python\n"
                "x = 5       # Action: Put 5 into box x\n"
                "if x == 5:  # Question: Is the value in box x equal to 5?\n"
                "    print('Yes, x is 5!')\n"
                "```\n\n"
                "**Guided Hint:** Remember: single `=` gives a value; double `==` asks a question.\n\n"
                "**Quick Practice:** Which symbol would you use to test if `score` is 100?"
            ),
        },
    ],
    "intermediate": [
        {
            "topic": "Loops & Iteration",
            "concept": "for loop with range() and indexing",
            "level": "intermediate",
            "common_mistake": "Using range(len(items)) instead of iterating over elements directly, or modifying a list during iteration.",
            "sample_question": "How does a for loop work with range in Python?",
            "demonstration_response": (
                "In Python, a `for` loop iterates over items produced by an iterable [S1]. "
                "The `range([start], stop[, step])` function returns an immutable sequence of integers [S1].\n\n"
                "**Execution Mechanics:**\n"
                "1. `range(start, stop, step)` generates integers starting at `start`.\n"
                "2. It increments by `step` on each iteration until the next value equals or exceeds `stop`.\n"
                "3. In each iteration, the loop variable is assigned the next sequence element.\n\n"
                "```python\n"
                "numbers = [10, 20, 30, 40]\n"
                "# Pythonic direct iteration:\n"
                "for num in numbers:\n"
                "    print(num * 2)\n\n"
                "# When index is needed, prefer enumerate over range(len()):\n"
                "for idx, num in enumerate(numbers):\n"
                "    print(f'Index {idx}: {num}')\n"
                "```\n\n"
                "**Common Pitfall:** Never call `.remove()` or `.append()` on a list while iterating over it directly; use a list comprehension or copy instead.\n\n"
                "**Exercise:** Write a loop using `range()` that prints all even numbers between 10 and 20 (inclusive) in reverse order."
            ),
        },
        {
            "topic": "Functions",
            "concept": "Return values vs Print statements",
            "level": "intermediate",
            "common_mistake": "Printing inside a function instead of returning a value, resulting in NoneType errors downstream.",
            "sample_question": "Why is my function result None when I try to save it to a variable?",
            "demonstration_response": (
                "A common distinction in Python functions is the difference between side-effects (`print()`) "
                "and caller communication (`return`) [S1].\n\n"
                "When a function does not encounter an explicit `return` statement, Python implicitly returns `None` [S1].\n\n"
                "```python\n"
                "# Problematic: Only prints, returns None\n"
                "def calculate_tax(amount):\n"
                "    print(amount * 0.1)\n\n"
                "total = calculate_tax(100)  # total is now None!\n\n"
                "# Correct: Returns the value to caller\n"
                "def calculate_tax(amount):\n"
                "    return amount * 0.1\n\n"
                "total = calculate_tax(100)  # total is 10.0\n"
                "```\n\n"
                "**Exercise:** Refactor a function that checks if a number is prime so that it returns a boolean (`True`/`False`) rather than printing."
            ),
        },
    ],
    "advanced": [
        {
            "topic": "Loops & Iteration",
            "concept": "Iterable and Iterator Protocol under for loops",
            "level": "advanced",
            "common_mistake": "Misunderstanding iterator exhaustion, memory consumption of large sequences, and generator semantics.",
            "sample_question": "How does a for loop work with range in Python?",
            "demonstration_response": (
                "Under the hood, Python's `for` loop implements the **Iterator Protocol** [S1]. "
                "When executing `for x in obj:`, Python calls `iter(obj)` to obtain an iterator, then repeatedly invokes `next()` on it until `StopIteration` is raised [S1].\n\n"
                "**Range Object Characteristics:**\n"
                "- `range` in Python 3 is a lazy sequence type, taking $O(1)$ memory regardless of size ($10^6$ vs $10^9$).\n"
                "- It supports $O(1)$ `__contains__` membership testing and indexing via arithmetic rather than table storage.\n\n"
                "```python\n"
                "# Equivalent protocol under the hood:\n"
                "iterator = iter(range(3))\n"
                "while True:\n"
                "    try:\n"
                "        val = next(iterator)\n"
                "        print(val)\n"
                "    except StopIteration:\n"
                "        break\n"
                "```\n\n"
                "**Edge Case / Deep Question:** What happens if you define a custom class implementing `__iter__` that returns `self` without defining `__next__`? "
                "Implement a memory-efficient generator that yields Fibonacci numbers up to $N$ with $O(1)$ auxiliary space."
            ),
        },
        {
            "topic": "Data Structures",
            "concept": "Mutability and Default Arguments",
            "level": "advanced",
            "common_mistake": "Using mutable default arguments (e.g. def fn(arg=[])) which bind once at function definition time.",
            "sample_question": "Why does my default list parameter keep growing across different function calls?",
            "demonstration_response": (
                "In Python, default parameter values are evaluated once when the function definition statement is executed, "
                "not each time the function is called [S1].\n\n"
                "If the default is a mutable object (such as a `list` or `dict`), mutations across calls persist in the function's `__defaults__` tuple [S1].\n\n"
                "```python\n"
                "# Anti-pattern: Shared mutable state\n"
                "def append_item(val, target=[]):\n"
                "    target.append(val)\n"
                "    return target\n\n"
                "# Idiomatic solution: Sentinel None idiom\n"
                "def append_item(val, target=None):\n"
                "    if target is None:\n"
                "        target = []\n"
                "    target.append(val)\n"
                "    return target\n"
                "```\n\n"
                "**Challenge:** Inspect `append_item.__defaults__` in the REPL across multiple invocations to verify the binding object ID."
            ),
        },
    ],
}


def get_few_shot_exemplars(level: str) -> list[dict[str, Any]]:
    """Retrieve curated exemplars for a normalized difficulty level.

    Supported levels:
    - beginner (also mapped from not_assessed, needs_revision)
    - intermediate (also mapped from developing)
    - advanced (also mapped from candidate_for_mastery)
    """
    normalized_level = level.lower().strip()
    mapping = {
        "not_assessed": "beginner",
        "needs_revision": "beginner",
        "beginner": "beginner",
        "foundational_revision": "beginner",
        "developing": "intermediate",
        "guided_practice": "intermediate",
        "intermediate": "intermediate",
        "candidate_for_mastery": "advanced",
        "advanced_application": "advanced",
        "advanced": "advanced",
    }
    key = mapping.get(normalized_level, "beginner")
    return FEW_SHOT_EXEMPLARS.get(key, FEW_SHOT_EXEMPLARS["beginner"])


def format_few_shot_prompt_section(level: str) -> str:
    """Format few-shot exemplars as structured prompt context for the LLM."""
    exemplars = get_few_shot_exemplars(level)
    normalized_level = exemplars[0]["level"].upper() if exemplars else "BEGINNER"

    formatted_examples = []
    for idx, ex in enumerate(exemplars, start=1):
        formatted_examples.append(
            f"--- EXEMPLAR {idx} ({normalized_level} LEVEL) ---\n"
            f"Topic: {ex['topic']}\n"
            f"Learner Misconception Addressed: {ex['common_mistake']}\n"
            f"Learner Query: {ex['sample_question']}\n"
            f"Tutor Response Style:\n{ex['demonstration_response']}\n"
        )

    return (
        f"FEW-SHOT TEACHING DEMONSTRATIONS FOR {normalized_level} LEVEL:\n"
        f"Notice how the tutor in these demonstrations adapts vocabulary, explanation depth, "
        f"hint structure, and practice questions to address learner level and common misconceptions.\n\n"
        + "\n".join(formatted_examples)
    )
