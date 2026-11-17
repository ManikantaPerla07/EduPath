"""Controlled Misconception Catalogue & Formative Diagnosis Service.

Fulfills Phase B2 requirements:
- Controlled catalogue using stable, documented codes.
- Structured diagnostic results (code, topic, description, correction, confidence, timestamp).
- Learner-scoped storage with server-side authenticated authorization.
- Formative guidance separate from authoritative assessment mastery.
"""

from collections.abc import Mapping
from datetime import datetime, timezone
import re
from typing import Any
from uuid import UUID

import psycopg

from services.assessment_service import load_database_url


# ==============================================================================
# 1. Controlled Misconception Catalogue (Stable Codes)
# ==============================================================================

MISCONCEPTION_CATALOGUE: dict[str, dict[str, Any]] = {
    "off_by_one_range": {
        "code": "off_by_one_range",
        "topic": "Loops & Iteration",
        "topic_slug": "loops",
        "short_description": "Believing upper bound in range() is inclusive.",
        "corrective_explanation": "range(start, stop) stops strictly before stop. The stop boundary is always exclusive.",
        "patterns": [
            r"range\(.*5\).*includes\s+5",
            r"range\(1,\s*5\).*(1 to 5|includes? 5)",
            r"range\([0-9]+,\s*([0-9]+)\).*ends\s+at\s+\1\b",
            r"stop\s+value\s+is\s+included",
        ],
        "remedial_exemplar": {
            "topic": "Loops & Iteration",
            "concept": "Boundary exclusion in range()",
            "level": "beginner",
            "common_mistake": "Believing range(start, stop) includes the stop number.",
            "sample_question": "Why didn't my loop print 5 when I used range(1, 5)?",
            "demonstration_response": (
                "In Python, the `stop` parameter in `range(start, stop)` is strictly exclusive [S1]. "
                "Think of it like a fence or speed limit: you can run right up to it, but you cannot cross or touch it.\n\n"
                "```python\n"
                "# range(1, 5) produces: 1, 2, 3, 4\n"
                "for i in range(1, 5):\n"
                "    print(i)\n"
                "```\n\n"
                "**Quick Rule:** If you want 5 to be included, you must set the stop value to 6: `range(1, 6)` [S1].\n\n"
                "**Quick Practice:** What range call would you write to count from 1 to 10 inclusive?"
            ),
        },
    },
    "assignment_vs_equality": {
        "code": "assignment_vs_equality",
        "topic": "Variables and Data Types",
        "topic_slug": "variables",
        "short_description": "Confusing assignment operator (=) with equality comparison operator (==).",
        "corrective_explanation": "A single equals sign = assigns a value to a variable; a double equals == evaluates whether two expressions are equal.",
        "patterns": [
            r"if\s+[a-zA-Z_]\w*\s*=\s*[^=]",
            r"check\s+(if\s+)?(it|value|variable)\s+is\s+=\s+",
            r"single\s+=\s+(checks|tests|compares)",
        ],
        "remedial_exemplar": {
            "topic": "Variables and Data Types",
            "concept": "Assignment (=) vs Equality (==)",
            "level": "beginner",
            "common_mistake": "Using a single = inside an if statement or equality test.",
            "sample_question": "Why does if x = 5 cause a SyntaxError?",
            "demonstration_response": (
                "Python keeps assigning values and testing values strictly separate [S1].\n\n"
                "- Single `=` is an **assignment command**: it stores the right side into the left-side name.\n"
                "- Double `==` is a **comparison question**: it asks 'Are these two sides equal?' and evaluates to `True` or `False` [S1].\n\n"
                "```python\n"
                "x = 5       # Action: Store 5 into x\n"
                "if x == 5:  # Question: Does x currently equal 5?\n"
                "    print('Matched!')\n"
                "```\n\n"
                "**Quick Hint:** If you are asking a question in an `if` block, always use double `==`."
            ),
        },
    },
    "list_mutation_during_iteration": {
        "code": "list_mutation_during_iteration",
        "topic": "Data Structures",
        "topic_slug": "data-structures",
        "short_description": "Mutating a collection (e.g. .remove() or .append()) while directly iterating over it.",
        "corrective_explanation": "Modifying a sequence during active iteration shifts internal index pointers and causes skipped or duplicated elements. Iterate over a slice copy or use a list comprehension.",
        "patterns": [
            r"remove\(.*\).*inside.*for",
            r"modify\s+(the\s+)?list\s+while\s+looping",
            r"del\s+.*inside\s+(a\s+)?for",
        ],
        "remedial_exemplar": {
            "topic": "Data Structures",
            "concept": "Safe sequence iteration",
            "level": "intermediate",
            "common_mistake": "Calling .remove() or .append() on a list while iterating over it.",
            "sample_question": "Why did my loop skip numbers when I called items.remove(x)?",
            "demonstration_response": (
                "When you loop over a list, Python maintains an internal index pointer (0, 1, 2...) [S1]. "
                "If you remove an element during the loop, all subsequent elements shift left, causing the next item to slide into the current position and be skipped!\n\n"
                "```python\n"
                "# Unsafe:\n"
                "items = [1, 2, 2, 3]\n"
                "# Safe alternative 1: Iterate over a shallow copy\n"
                "for x in items[:]:\n"
                "    if x == 2:\n"
                "        items.remove(x)\n\n"
                "# Safe alternative 2 (Pythonic): List comprehension\n"
                "items = [x for x in items if x != 2]\n"
                "```\n\n"
                "**Exercise:** Refactor a loop that removes negative numbers from a list using a list comprehension."
            ),
        },
    },
    "return_vs_print": {
        "code": "return_vs_print",
        "topic": "Functions",
        "topic_slug": "functions",
        "short_description": "Using print() instead of return inside a function, causing NoneType return values.",
        "corrective_explanation": "print() displays text to the console as a side effect; return transfers data back to the calling expression.",
        "patterns": [
            r"print\s+(instead\s+of|gives\s+back)\s+return",
            r"function\s+returns\s+none\s+because\s+print",
            r"print\s+sends\s+the\s+value\s+back",
        ],
        "remedial_exemplar": {
            "topic": "Functions",
            "concept": "Function Return Values vs Console Output",
            "level": "intermediate",
            "common_mistake": "Printing a result instead of returning it, causing variable assignments to hold None.",
            "sample_question": "Why is my variable None after calling my add function?",
            "demonstration_response": (
                "There is a fundamental difference between **printing** a value and **returning** a value [S1].\n\n"
                "- `print()` is a **side-effect**: it displays characters on the monitor, but produces no value for code.\n"
                "- `return` is a **data transfer**: it delivers the result back to the line of code that called the function [S1].\n\n"
                "```python\n"
                "def add_wrong(a, b):\n"
                "    print(a + b)  # Shows on screen, but returns None implicitly!\n\n"
                "def add_right(a, b):\n"
                "    return a + b  # Returns the sum to caller\n\n"
                "result = add_right(3, 4)  # result is now 7\n"
                "```\n\n"
                "**Practice:** Write a function `square(n)` that returns $n^2$ so that `val = square(5)` stores 25."
            ),
        },
    },
    "mutable_default_argument": {
        "code": "mutable_default_argument",
        "topic": "Functions",
        "topic_slug": "functions",
        "short_description": "Using a mutable object (like a list or dict) as a default parameter value.",
        "corrective_explanation": "Default parameter values are evaluated once at function definition time. Mutations across calls persist in the function's __defaults__ tuple. Use None as a sentinel.",
        "patterns": [
            r"def\s+\w+\(.*\w+\s*=\s*\[\s*\]\)",
            r"def\s+\w+\(.*\w+\s*=\s*\{\s*\}\)",
            r"default\s+list\s+grows\s+across\s+calls",
        ],
        "remedial_exemplar": {
            "topic": "Functions",
            "concept": "Default Argument Evaluation Semantics",
            "level": "advanced",
            "common_mistake": "Binding a mutable collection as a default parameter.",
            "sample_question": "Why does my default list remember items from previous function calls?",
            "demonstration_response": (
                "In Python, default arguments are evaluated **once** when the `def` statement executes, not on each invocation [S1]. "
                "If the default is a mutable container (`list`, `dict`), all calls without an explicit argument share the identical container instance.\n\n"
                "```python\n"
                "# The Sentinel Pattern (Best Practice):\n"
                "def add_item(item, container=None):\n"
                "    if container is None:\n"
                "        container = []\n"
                "    container.append(item)\n"
                "    return container\n"
                "```\n\n"
                "**Exercise:** Explain why `id(container)` remains identical across invocations when using `container=[]`."
            ),
        },
    },
    "zero_based_indexing": {
        "code": "zero_based_indexing",
        "topic": "Data Structures",
        "topic_slug": "data-structures",
        "short_description": "Believing the first element of a sequence is at index 1 instead of index 0.",
        "corrective_explanation": "Python sequences use zero-based indexing; the first element is at index 0 and the last element is at index len - 1.",
        "patterns": [
            r"first\s+element\s+is\s+(at\s+)?index\s+1\b",
            r"index\s+1\s+is\s+the\s+first",
        ],
        "remedial_exemplar": {
            "topic": "Data Structures",
            "concept": "Zero-Based Indexing in Python",
            "level": "beginner",
            "common_mistake": "Attempting to access the first element with [1].",
            "sample_question": "Why did items[1] return the second item instead of the first?",
            "demonstration_response": (
                "Python sequences (lists, strings, tuples) use **zero-based indexing** [S1]. "
                "The index represents the offset (distance) from the start of the collection:\n\n"
                "- Offset 0 steps: `items[0]` (1st element)\n"
                "- Offset 1 step: `items[1]` (2nd element)\n\n"
                "```python\n"
                "fruits = ['apple', 'banana', 'cherry']\n"
                "print(fruits[0])  # 'apple' (First item)\n"
                "print(fruits[1])  # 'banana' (Second item)\n"
                "```\n\n"
                "**Quick Practice:** What is the index of the third element in a list?"
            ),
        },
    },
    "string_immutability": {
        "code": "string_immutability",
        "topic": "Variables and Data Types",
        "topic_slug": "variables",
        "short_description": "Attempting in-place item assignment on strings (e.g. s[0] = 'a').",
        "corrective_explanation": "Python strings are immutable. You cannot modify individual characters in-place; create a new string with slicing or concatenation.",
        "patterns": [
            r"s\[\d+\]\s*=\s*",
            r"change\s+a\s+character\s+in\s+string\s+directly",
            r"string\s+item\s+assignment",
        ],
        "remedial_exemplar": {
            "topic": "Variables and Data Types",
            "concept": "String Immutability",
            "level": "intermediate",
            "common_mistake": "Assigning to an index of a string: `s[0] = 'X'`.",
            "sample_question": "Why do I get 'TypeError: str object does not support item assignment'?",
            "demonstration_response": (
                "Strings in Python are **immutable**: once created in memory, their contents cannot be altered [S1].\n\n"
                "To modify a string, you construct a new string using slicing or string methods:\n\n"
                "```python\n"
                "text = 'hello'\n"
                "# text[0] = 'H'  # Raises TypeError!\n\n"
                "# Correct: Build a new string\n"
                "text = 'H' + text[1:]  # 'Hello'\n"
                "```\n\n"
                "**Exercise:** Use string slicing to replace the last character of any non-empty string with `'!'`."
            ),
        },
    },
    "variable_scope_leak": {
        "code": "variable_scope_leak",
        "topic": "Functions",
        "topic_slug": "functions",
        "short_description": "Expecting local variables defined inside a function to be accessible globally.",
        "corrective_explanation": "Variables defined within a function belong to that function's local scope and cease to exist once execution finishes.",
        "patterns": [
            r"access\s+local\s+variable\s+outside",
            r"variable\s+inside\s+function\s+is\s+global",
            r"nameerror.*variable\s+defined\s+in\s+function",
        ],
        "remedial_exemplar": {
            "topic": "Functions",
            "concept": "Local vs Global Scope",
            "level": "intermediate",
            "common_mistake": "Trying to read a variable created inside a function from global scope.",
            "sample_question": "Why is my variable not recognized after calling the function where it was created?",
            "demonstration_response": (
                "In Python, variables created inside a function belong to the **local scope** of that function call [S1]. "
                "When the function finishes running, its local scope is destroyed.\n\n"
                "```python\n"
                "def calculate():\n"
                "    secret_val = 42\n"
                "    return secret_val\n\n"
                "total = calculate()\n"
                "# print(secret_val)  # Raises NameError: name 'secret_val' is not defined!\n"
                "print(total)         # 42 (Accessible because it was returned)\n"
                "```\n\n"
                "**Rule:** To make data available outside a function, explicitly `return` it."
            ),
        },
    },
}


# ==============================================================================
# 2. Diagnostic Functions
# ==============================================================================

def get_misconception_definition(code: str) -> dict[str, Any] | None:
    """Retrieve metadata for a stable misconception code."""
    if not isinstance(code, str):
        return None
    return MISCONCEPTION_CATALOGUE.get(code.strip())


def list_misconception_codes(topic_slug: str | None = None) -> list[str]:
    """List all registered misconception codes, optionally filtered by topic."""
    if topic_slug is None:
        return sorted(MISCONCEPTION_CATALOGUE.keys())
    slug_clean = topic_slug.strip().lower()
    return sorted(
        code for code, data in MISCONCEPTION_CATALOGUE.items()
        if data.get("topic_slug", "").lower() == slug_clean
    )


def diagnose_student_misconceptions(
    student_text: str,
    topic_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Diagnose misconceptions from student explanation or answer text.

    Returns structured diagnostic results adhering to Phase B2 schema.
    """
    if not isinstance(student_text, str) or not student_text.strip():
        return []

    text = student_text.strip()
    text_lower = text.lower()
    diagnoses: list[dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine candidate catalogue items
    if topic_slug:
        topic_clean = topic_slug.strip().lower()
        candidates = [
            (code, data) for code, data in MISCONCEPTION_CATALOGUE.items()
            if data.get("topic_slug", "").lower() == topic_clean
        ]
        # If no specific topic match, check all candidates
        if not candidates:
            candidates = list(MISCONCEPTION_CATALOGUE.items())
    else:
        candidates = list(MISCONCEPTION_CATALOGUE.items())

    for code, entry in candidates:
        matched = False
        for pattern in entry.get("patterns", []):
            if re.search(pattern, text_lower, re.IGNORECASE):
                matched = True
                break

        if matched:
            diagnoses.append({
                "misconception_code": code,
                "topic": entry["topic"],
                "topic_slug": entry["topic_slug"],
                "short_description": entry["short_description"],
                "corrective_explanation": entry["corrective_explanation"],
                "confidence": 0.90,
                "detection_method": "catalogue_rule_based",
                "timestamp": now_iso,
            })

    return diagnoses


# ==============================================================================
# 3. Learner-Scoped Persistence (Server-Side Authenticated)
# ==============================================================================

def record_learner_misconceptions(
    user_id: str,
    diagnoses: list[dict[str, Any]],
) -> list[str]:
    """Persist formative misconception diagnoses tied to authenticated learner ID.

    Guarantees:
    - user_id is validated as server-side UUID.
    - Operates in transactional isolation.
    - Does NOT modify official assessment mastery records.
    - Gracefully skips DB write if migration table not yet created.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Learner user ID must be a non-empty string.")

    try:
        learner_uuid = UUID(user_id.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid learner user ID: {user_id}") from exc

    if not diagnoses:
        return []

    recorded_ids: list[str] = []

    try:
        with psycopg.connect(load_database_url(), connect_timeout=10) as conn:
            with conn.cursor() as cursor:
                # Check table existence defensively
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'learner_misconceptions'
                    );
                    """
                )
                if not cursor.fetchone()[0]:
                    return []

                for d in diagnoses:
                    code = d.get("misconception_code")
                    if not code or code not in MISCONCEPTION_CATALOGUE:
                        continue

                    entry = MISCONCEPTION_CATALOGUE[code]
                    cursor.execute(
                        """
                        INSERT INTO learner_misconceptions (
                            user_id,
                            misconception_code,
                            topic_slug,
                            short_description,
                            corrective_explanation,
                            detection_method,
                            confidence_score,
                            is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                        RETURNING misconception_record_id;
                        """,
                        (
                            learner_uuid,
                            code,
                            entry["topic_slug"],
                            entry["short_description"],
                            entry["corrective_explanation"],
                            d.get("detection_method", "catalogue_rule_based"),
                            float(d.get("confidence", 0.90)),
                        ),
                    )
                    row = cursor.fetchone()
                    if row:
                        recorded_ids.append(str(row[0]))
    except Exception:
        # DB unreachable or table not present; formative persistence is non-blocking
        pass

    return recorded_ids


def fetch_active_learner_misconceptions(
    user_id: str,
    topic_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve active misconceptions for an authenticated learner.

    Enforces server-side authorization: only the specified user's records are returned.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Learner user ID must be a non-empty string.")

    try:
        learner_uuid = UUID(user_id.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid learner user ID: {user_id}") from exc

    try:
        with psycopg.connect(load_database_url(), connect_timeout=10) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'learner_misconceptions'
                    );
                    """
                )
                if not cursor.fetchone()[0]:
                    return []

                if topic_slug:
                    cursor.execute(
                        """
                        SELECT
                            misconception_record_id,
                            misconception_code,
                            topic_slug,
                            short_description,
                            corrective_explanation,
                            detection_method,
                            confidence_score,
                            COALESCE(diagnosed_at, detected_at) AS diagnosed_at
                        FROM learner_misconceptions
                        WHERE user_id = %s
                          AND topic_slug = %s
                          AND is_active = TRUE
                        ORDER BY COALESCE(diagnosed_at, detected_at) DESC
                        LIMIT 10;
                        """,
                        (learner_uuid, topic_slug.strip().lower()),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            misconception_record_id,
                            misconception_code,
                            topic_slug,
                            short_description,
                            corrective_explanation,
                            detection_method,
                            confidence_score,
                            COALESCE(diagnosed_at, detected_at) AS diagnosed_at
                        FROM learner_misconceptions
                        WHERE user_id = %s
                          AND is_active = TRUE
                        ORDER BY COALESCE(diagnosed_at, detected_at) DESC
                        LIMIT 15;
                        """,
                        (learner_uuid,),
                    )

                results = []
                for row in cursor.fetchall():
                    timestamp_iso = row[7].isoformat() if row[7] else None
                    results.append({
                        "misconception_record_id": str(row[0]),
                        "misconception_code": row[1],
                        "topic_slug": row[2],
                        "short_description": row[3],
                        "corrective_explanation": row[4],
                        "detection_method": row[5],
                        "confidence": float(row[6]),
                        "timestamp": timestamp_iso,
                        "diagnosed_at": timestamp_iso,
                        "detected_at": timestamp_iso,
                    })
                return results
    except Exception:
        return []


def resolve_learner_misconception(
    user_id: str,
    misconception_code: str,
) -> bool:
    """Mark a misconception as resolved after successful corrective practice."""
    if not isinstance(user_id, str) or not isinstance(misconception_code, str):
        return False

    try:
        learner_uuid = UUID(user_id.strip())
    except ValueError:
        return False

    try:
        with psycopg.connect(load_database_url(), connect_timeout=10) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE learner_misconceptions
                    SET is_active = FALSE,
                        resolved_at = NOW()
                    WHERE user_id = %s
                      AND misconception_code = %s
                      AND is_active = TRUE;
                    """,
                    (learner_uuid, misconception_code.strip()),
                )
                return cursor.rowcount > 0
    except Exception:
        return False
