from pathlib import Path
import tomllib

import psycopg
from psycopg.types.json import Jsonb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

COURSE_SLUG = "python-basics"

# Each question has a unique code, four options and one answer.
QUESTIONS = [

    # ==========================================
    # 1. VARIABLES AND DATA TYPES
    # ==========================================

    {
        "code": "PY-VAR-E-001",
        "topic": "variables-data-types",
        "difficulty": "easy",
        "question": "What is the output?\n\nx = 10\nprint(type(x).__name__)",
        "options": ["A. str", "B. int", "C. float", "D. bool"],
        "answer": "B",
        "explanation": "10 is an integer, so Python identifies its type as int."
    },
    {
        "code": "PY-VAR-M-001",
        "topic": "variables-data-types",
        "difficulty": "medium",
        "question": "What is the output?\n\nvalue = 5\nvalue = 'five'\nprint(type(value).__name__)",
        "options": ["A. int", "B. str", "C. bool", "D. float"],
        "answer": "B",
        "explanation": "Python allows dynamic typing. The variable now refers to a string."
    },
    {
        "code": "PY-VAR-H-001",
        "topic": "variables-data-types",
        "difficulty": "hard",
        "question": "What is the output?\n\na = 10\nb = a\na = 20\nprint(b)",
        "options": ["A. 10", "B. 20", "C. None", "D. Error"],
        "answer": "A",
        "explanation": "b initially refers to the integer object 10. Reassigning a does not change b."
    },

    # ==========================================
    # 2. OPERATORS AND EXPRESSIONS
    # ==========================================

    {
        "code": "PY-OP-E-001",
        "topic": "operators",
        "difficulty": "easy",
        "question": "What is the result of 7 // 2?",
        "options": ["A. 3.5", "B. 4", "C. 3", "D. 2"],
        "answer": "C",
        "explanation": "The // operator performs floor division. The result is 3."
    },
    {
        "code": "PY-OP-M-001",
        "topic": "operators",
        "difficulty": "medium",
        "question": "What is the output?\n\nprint(2 ** 3 ** 2)",
        "options": ["A. 64", "B. 512", "C. 256", "D. 36"],
        "answer": "B",
        "explanation": "Exponentiation is right-associative: 2 ** (3 ** 2) = 2 ** 9 = 512."
    },
    {
        "code": "PY-OP-H-001",
        "topic": "operators",
        "difficulty": "hard",
        "question": "What is the output?\n\nprint(10 % 3 + 2 * 4)",
        "options": ["A. 12", "B. 9", "C. 16", "D. 8"],
        "answer": "B",
        "explanation": "Multiplication and modulo are evaluated before addition: 1 + 8 = 9."
    },

    # ==========================================
    # 3. CONDITIONAL STATEMENTS
    # ==========================================

    {
        "code": "PY-CON-E-001",
        "topic": "conditionals",
        "difficulty": "easy",
        "question": "What is the output?\n\nx = 7\nif x > 5:\n    print('High')\nelse:\n    print('Low')",
        "options": ["A. High", "B. Low", "C. True", "D. Error"],
        "answer": "A",
        "explanation": "7 is greater than 5, so the if block executes."
    },
    {
        "code": "PY-CON-M-001",
        "topic": "conditionals",
        "difficulty": "medium",
        "question": "What is the output?\n\nscore = 70\nif score > 70:\n    print('Excellent')\nelif score >= 70:\n    print('Pass')\nelse:\n    print('Fail')",
        "options": ["A. Excellent", "B. Pass", "C. Fail", "D. Error"],
        "answer": "B",
        "explanation": "The first condition is false, but score >= 70 is true."
    },
    {
        "code": "PY-CON-H-001",
        "topic": "conditionals",
        "difficulty": "hard",
        "question": "What is the output?\n\nx = 8\nresult = 'A' if x >= 9 else 'B' if x >= 7 else 'C'\nprint(result)",
        "options": ["A. A", "B. B", "C. C", "D. Error"],
        "answer": "B",
        "explanation": "The first condition is false and the second is true, so B is selected."
    },

    # ==========================================
    # 4. LOOPS
    # ==========================================

    {
        "code": "PY-LOOP-E-001",
        "topic": "loops",
        "difficulty": "easy",
        "question": "What is the output?\n\nfor i in range(3):\n    print(i, end=' ')",
        "options": ["A. 1 2 3", "B. 0 1 2", "C. 0 1 2 3", "D. 3 2 1"],
        "answer": "B",
        "explanation": "range(3) generates 0, 1 and 2."
    },
    {
        "code": "PY-LOOP-M-001",
        "topic": "loops",
        "difficulty": "medium",
        "question": "What is the output?\n\nfor i in range(2, 7, 2):\n    print(i, end=' ')",
        "options": ["A. 2 4 6", "B. 2 4 6 8", "C. 1 3 5", "D. 2 3 4 5 6"],
        "answer": "A",
        "explanation": "The range starts at 2, increases by 2 and stops before 7."
    },
    {
        "code": "PY-LOOP-H-001",
        "topic": "loops",
        "difficulty": "hard",
        "question": "What is the output?\n\ncount = 0\nfor i in range(3):\n    for j in range(i):\n        count += 1\nprint(count)",
        "options": ["A. 2", "B. 3", "C. 6", "D. 9"],
        "answer": "B",
        "explanation": "The inner loop runs 0, 1 and 2 times respectively. Total executions = 3."
    },

    # ==========================================
    # 5. FUNCTIONS
    # ==========================================

    {
        "code": "PY-FUN-E-001",
        "topic": "functions",
        "difficulty": "easy",
        "question": "What is the output?\n\ndef greet():\n    return 'Hi'\n\nprint(greet())",
        "options": ["A. greet", "B. None", "C. Hi", "D. Error"],
        "answer": "C",
        "explanation": "The function returns the string Hi, which print displays."
    },
    {
        "code": "PY-FUN-M-001",
        "topic": "functions",
        "difficulty": "medium",
        "question": "What is the output?\n\ndef multiply(x, y=2):\n    return x * y\n\nprint(multiply(3))",
        "options": ["A. 3", "B. 5", "C. 6", "D. Error"],
        "answer": "C",
        "explanation": "The default value of y is 2, so 3 * 2 = 6."
    },
    {
        "code": "PY-FUN-H-001",
        "topic": "functions",
        "difficulty": "hard",
        "question": "What is the output?\n\ndef add(item, items=[]):\n    items.append(item)\n    return items\n\nprint(add(1))\nprint(add(2))",
        "options": [
            "A. [1] followed by [2]",
            "B. [1] followed by [1, 2]",
            "C. [1, 2] followed by [1, 2]",
            "D. Error"
        ],
        "answer": "B",
        "explanation": "The mutable default list is created once and reused across calls. This is a common Python function pitfall."
    },

    # ==========================================
    # 6. LISTS AND TUPLES
    # ==========================================

    {
        "code": "PY-LIST-E-001",
        "topic": "lists-tuples",
        "difficulty": "easy",
        "question": "What is the output?\n\nnumbers = [10, 20, 30]\nprint(numbers[1])",
        "options": ["A. 10", "B. 20", "C. 30", "D. 1"],
        "answer": "B",
        "explanation": "Python lists use zero-based indexing. Index 1 refers to 20."
    },
    {
        "code": "PY-LIST-M-001",
        "topic": "lists-tuples",
        "difficulty": "medium",
        "question": "What is the output?\n\nnumbers = [1, 2, 3, 4]\nprint(numbers[1:3])",
        "options": ["A. [1, 2]", "B. [2, 3]", "C. [2, 3, 4]", "D. [1, 2, 3]"],
        "answer": "B",
        "explanation": "The slice includes index 1 but excludes index 3."
    },
    {
        "code": "PY-LIST-H-001",
        "topic": "lists-tuples",
        "difficulty": "hard",
        "question": "What is the output?\n\nnumbers = [1, 2]\nother = numbers\nother.append(3)\nprint(numbers)",
        "options": ["A. [1, 2]", "B. [1, 2, 3]", "C. [3]", "D. Error"],
        "answer": "B",
        "explanation": "Both variables refer to the same mutable list object. Appending through other also changes numbers."
    },

    # ==========================================
    # 7. DICTIONARIES AND SETS
    # ==========================================

    {
        "code": "PY-DICT-E-001",
        "topic": "dictionaries-sets",
        "difficulty": "easy",
        "question": "What is the output?\n\nstudent = {'name': 'Mani'}\nprint(student['name'])",
        "options": ["A. student", "B. name", "C. Mani", "D. Error"],
        "answer": "C",
        "explanation": "Dictionary keys are used to retrieve their corresponding values."
    },
    {
        "code": "PY-DICT-M-001",
        "topic": "dictionaries-sets",
        "difficulty": "medium",
        "question": "What is the output?\n\nvalues = {1, 2, 2, 3, 1}\nprint(len(values))",
        "options": ["A. 5", "B. 4", "C. 3", "D. 2"],
        "answer": "C",
        "explanation": "Sets store unique elements. The duplicates are removed."
    },
    {
        "code": "PY-DICT-H-001",
        "topic": "dictionaries-sets",
        "difficulty": "hard",
        "question": "What is the output?\n\nscores = {'a': 3}\nresult = scores.get('b', 2) + scores['a']\nprint(result)",
        "options": ["A. 2", "B. 3", "C. 5", "D. KeyError"],
        "answer": "C",
        "explanation": "get('b', 2) returns the default value 2. Adding scores['a'] gives 5."
    },

    # ==========================================
    # 8. STRINGS
    # ==========================================

    {
        "code": "PY-STR-E-001",
        "topic": "strings",
        "difficulty": "easy",
        "question": "What is the output?\n\nword = 'Python'\nprint(len(word))",
        "options": ["A. 5", "B. 6", "C. 7", "D. 8"],
        "answer": "B",
        "explanation": "Python contains six characters."
    },
    {
        "code": "PY-STR-M-001",
        "topic": "strings",
        "difficulty": "medium",
        "question": "What is the output?\n\nword = 'python'\nprint(word[1:4])",
        "options": ["A. pyt", "B. yth", "C. tho", "D. ytho"],
        "answer": "B",
        "explanation": "Slicing begins at index 1 and stops before index 4."
    },
    {
        "code": "PY-STR-H-001",
        "topic": "strings",
        "difficulty": "hard",
        "question": "What is the output?\n\nword = 'cat'\nnew_word = word.replace('c', 'b')\nprint(word, new_word)",
        "options": [
            "A. bat bat",
            "B. cat bat",
            "C. bat cat",
            "D. Error"
        ],
        "answer": "B",
        "explanation": "Strings are immutable. replace returns a new string without modifying the original."
    },

    # ==========================================
    # 9. BASIC PROBLEM SOLVING
    # ==========================================

    {
        "code": "PY-PROB-E-001",
        "topic": "problem-solving",
        "difficulty": "easy",
        "question": "What is the output?\n\nnumbers = [4, 9, 2]\nprint(max(numbers))",
        "options": ["A. 2", "B. 4", "C. 9", "D. 15"],
        "answer": "C",
        "explanation": "The max function returns the largest item in the list."
    },
    {
        "code": "PY-PROB-M-001",
        "topic": "problem-solving",
        "difficulty": "medium",
        "question": "What is the output?\n\nnumbers = [1, 2, 2, 3, 3, 3]\nprint(len(set(numbers)))",
        "options": ["A. 6", "B. 4", "C. 3", "D. 2"],
        "answer": "C",
        "explanation": "Converting the list to a set removes duplicates. Three unique values remain."
    },
    {
        "code": "PY-PROB-H-001",
        "topic": "problem-solving",
        "difficulty": "hard",
        "question": "What is the output?\n\nnumbers = [4, 2, 4, 3]\nunique = []\n\nfor value in numbers:\n    if value not in unique:\n        unique.append(value)\n\nprint(unique)",
        "options": [
            "A. [4, 2, 4, 3]",
            "B. [2, 3, 4]",
            "C. [4, 2, 3]",
            "D. [4, 4, 2, 3]"
        ],
        "answer": "C",
        "explanation": "The loop adds each value only if it is not already present. The first occurrence order is preserved."
    },
]


def load_database_url():
    """Load the Neon connection string."""

    with SECRETS_FILE.open("rb") as file:
        secrets = tomllib.load(file)

    database_url = secrets.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    return database_url


def load_topic_ids(cursor):
    """Retrieve topic IDs for the Python course."""

    cursor.execute(
        """
        SELECT t.topic_slug, t.topic_id
        FROM topics AS t
        JOIN courses AS c
          ON c.course_id = t.course_id
        WHERE c.course_slug = %s;
        """,
        (COURSE_SLUG,)
    )

    return {
        slug: topic_id
        for slug, topic_id in cursor.fetchall()
    }


def validate_questions(topic_ids):
    """Check the seed dataset before inserting it."""

    if len(QUESTIONS) != 27:
        raise ValueError("Expected exactly 27 questions.")

    codes = [question["code"] for question in QUESTIONS]

    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate question codes found.")

    expected_counts = {
        "easy": 9,
        "medium": 9,
        "hard": 9,
    }

    actual_counts = {
        difficulty: sum(
            q["difficulty"] == difficulty
            for q in QUESTIONS
        )
        for difficulty in expected_counts
    }

    if actual_counts != expected_counts:
        raise ValueError("Difficulty distribution is incorrect.")

    for question in QUESTIONS:

        if question["topic"] not in topic_ids:
            raise ValueError(
                f"Unknown topic: {question['topic']}"
            )

        if len(question["options"]) != 4:
            raise ValueError(
                f"Question must have four options: {question['code']}"
            )

        if question["answer"] not in {"A", "B", "C", "D"}:
            raise ValueError(
                f"Invalid correct answer: {question['code']}"
            )


def seed_questions():
    """Insert or update all 27 Python MCQs."""

    database_url = load_database_url()

    with psycopg.connect(
        database_url,
        connect_timeout=20
    ) as connection:

        with connection.cursor() as cursor:

            topic_ids = load_topic_ids(cursor)

            validate_questions(topic_ids)

            for question in QUESTIONS:

                cursor.execute(
                    """
                    INSERT INTO question_bank (
                        question_code,
                        topic_id,
                        question_type,
                        question_text,
                        options,
                        correct_answer,
                        explanation,
                        difficulty,
                        is_active
                    )
                    VALUES (
                        %s, %s, 'mcq', %s, %s, %s, %s, %s, TRUE
                    )

                    ON CONFLICT (question_code)
                    DO UPDATE SET
                        topic_id = EXCLUDED.topic_id,
                        question_type = EXCLUDED.question_type,
                        question_text = EXCLUDED.question_text,
                        options = EXCLUDED.options,
                        correct_answer = EXCLUDED.correct_answer,
                        explanation = EXCLUDED.explanation,
                        difficulty = EXCLUDED.difficulty,
                        is_active = TRUE;
                    """,
                    (
                        question["code"],
                        topic_ids[question["topic"]],
                        question["question"],
                        Jsonb(question["options"]),
                        Jsonb(question["answer"]),
                        question["explanation"],
                        question["difficulty"],
                    )
                )

            cursor.execute(
                """
                SELECT
                    qb.difficulty,
                    COUNT(*)
                FROM question_bank AS qb
                JOIN topics AS t
                  ON t.topic_id = qb.topic_id
                JOIN courses AS c
                  ON c.course_id = t.course_id
                WHERE c.course_slug = %s
                  AND qb.is_active = TRUE
                GROUP BY qb.difficulty
                ORDER BY qb.difficulty;
                """,
                (COURSE_SLUG,)
            )

            distribution = dict(cursor.fetchall())

            total_questions = sum(distribution.values())

            if total_questions != 27:
                raise RuntimeError(
                    f"Expected 27 questions, found {total_questions}."
                )

            if distribution != {
                "easy": 9,
                "medium": 9,
                "hard": 9,
            }:
                raise RuntimeError(
                    f"Incorrect question distribution: {distribution}"
                )

    print("\n========== EDUPATH QUESTION BANK REPORT ==========")
    print("Course              : Python Programming")
    print("Questions processed :", len(QUESTIONS))
    print("Total active questions:", total_questions)
    print("Easy                :", distribution["easy"])
    print("Medium              :", distribution["medium"])
    print("Hard                :", distribution["hard"])
    print("Question validation : SUCCESS")
    print("\nQuestion bank initialized successfully.")


if __name__ == "__main__":

    try:
        seed_questions()

    except Exception as error:
        print("\nQUESTION BANK SEED FAILED")
        print("Error type:", type(error).__name__)
        print("Details:", str(error))
        raise SystemExit(1)
