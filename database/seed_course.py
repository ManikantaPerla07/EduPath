from pathlib import Path
import tomllib

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SECRETS_FILE = (
    PROJECT_ROOT / ".streamlit" / "secrets.toml"
)


COURSE = {
    "course_slug": "python-basics",
    "course_name": "Python Programming",
    "description": (
        "A beginner-friendly Python programming course "
        "covering fundamentals and basic problem solving."
    ),
    "difficulty_level": "beginner",
}


TOPICS = [
    {
        "slug": "variables-data-types",
        "name": "Introduction, Variables and Data Types",
        "description": "Python introduction, variables and basic data types.",
        "sequence": 1,
        "minutes": 45,
    },
    {
        "slug": "operators",
        "name": "Operators and Expressions",
        "description": "Arithmetic, comparison, logical and assignment operators.",
        "sequence": 2,
        "minutes": 45,
    },
    {
        "slug": "conditionals",
        "name": "Conditional Statements",
        "description": "if, elif, else and decision-making.",
        "sequence": 3,
        "minutes": 60,
    },
    {
        "slug": "loops",
        "name": "Loops",
        "description": "For loops, while loops, break and continue.",
        "sequence": 4,
        "minutes": 90,
    },
    {
        "slug": "functions",
        "name": "Functions",
        "description": "Function definition, arguments and return values.",
        "sequence": 5,
        "minutes": 90,
    },
    {
        "slug": "lists-tuples",
        "name": "Lists and Tuples",
        "description": "Python sequences, indexing and common operations.",
        "sequence": 6,
        "minutes": 75,
    },
    {
        "slug": "dictionaries-sets",
        "name": "Dictionaries and Sets",
        "description": "Key-value storage, dictionary operations and sets.",
        "sequence": 7,
        "minutes": 75,
    },
    {
        "slug": "strings",
        "name": "Strings",
        "description": "String manipulation, methods and formatting.",
        "sequence": 8,
        "minutes": 60,
    },
    {
        "slug": "problem-solving",
        "name": "Basic Problem Solving",
        "description": "Applying Python fundamentals to programming problems.",
        "sequence": 9,
        "minutes": 120,
    },
]


PREREQUISITES = {
    "operators": ["variables-data-types"],
    "conditionals": ["operators"],
    "loops": ["conditionals"],
    "functions": ["conditionals"],
    "lists-tuples": ["loops"],
    "dictionaries-sets": ["lists-tuples"],
    "strings": ["variables-data-types"],
    "problem-solving": [
        "functions",
        "lists-tuples",
        "dictionaries-sets",
        "strings",
    ],
}


def load_database_url():
    """Read the Neon connection string."""

    if not SECRETS_FILE.exists():
        raise FileNotFoundError(
            "Local secrets.toml was not found."
        )

    with SECRETS_FILE.open("rb") as file:
        secrets = tomllib.load(file)

    database_url = secrets.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    return database_url


def create_or_get_course(cursor):
    """Insert the course or update its existing record."""

    cursor.execute(
        """
        INSERT INTO courses (
            course_slug,
            course_name,
            description,
            difficulty_level,
            is_published
        )
        VALUES (%s, %s, %s, %s, FALSE)

        ON CONFLICT (course_slug)
        DO UPDATE SET
            course_name = EXCLUDED.course_name,
            description = EXCLUDED.description,
            difficulty_level = EXCLUDED.difficulty_level

        RETURNING course_id;
        """,
        (
            COURSE["course_slug"],
            COURSE["course_name"],
            COURSE["description"],
            COURSE["difficulty_level"],
        ),
    )

    return cursor.fetchone()[0]


def create_or_get_topics(cursor, course_id):
    """Insert topics and collect their database IDs."""

    topic_ids = {}

    for topic in TOPICS:

        cursor.execute(
            """
            INSERT INTO topics (
                course_id,
                topic_slug,
                topic_name,
                description,
                sequence_number,
                estimated_minutes
            )
            VALUES (%s, %s, %s, %s, %s, %s)

            ON CONFLICT (course_id, topic_slug)
            DO UPDATE SET
                topic_name = EXCLUDED.topic_name,
                description = EXCLUDED.description,
                sequence_number = EXCLUDED.sequence_number,
                estimated_minutes = EXCLUDED.estimated_minutes

            RETURNING topic_id;
            """,
            (
                course_id,
                topic["slug"],
                topic["name"],
                topic["description"],
                topic["sequence"],
                topic["minutes"],
            ),
        )

        topic_ids[topic["slug"]] = cursor.fetchone()[0]

    return topic_ids


def create_prerequisites(cursor, course_id, topic_ids):
    """Insert topic dependency relationships."""

    inserted_count = 0

    for topic_slug, prerequisite_slugs in PREREQUISITES.items():

        topic_id = topic_ids[topic_slug]

        for prerequisite_slug in prerequisite_slugs:

            prerequisite_id = topic_ids[prerequisite_slug]

            cursor.execute(
                """
                INSERT INTO topic_prerequisites (
                    topic_id,
                    prerequisite_topic_id,
                    course_id
                )
                VALUES (%s, %s, %s)

                ON CONFLICT (
                    topic_id,
                    prerequisite_topic_id
                )
                DO NOTHING;
                """,
                (
                    topic_id,
                    prerequisite_id,
                    course_id,
                ),
            )

            inserted_count += cursor.rowcount

    return inserted_count


def seed_course():
    """Initialize Python course and its learning structure."""

    database_url = load_database_url()

    with psycopg.connect(
        database_url,
        connect_timeout=20,
    ) as connection:

        with connection.cursor() as cursor:

            course_id = create_or_get_course(cursor)

            topic_ids = create_or_get_topics(
                cursor,
                course_id,
            )

            inserted_count = create_prerequisites(
                cursor,
                course_id,
                topic_ids,
            )

            cursor.execute(
                """
                SELECT
                    sequence_number,
                    topic_name
                FROM topics
                WHERE course_id = %s
                ORDER BY sequence_number;
                """,
                (course_id,),
            )

            saved_topics = cursor.fetchall()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM topic_prerequisites
                WHERE course_id = %s;
                """,
                (course_id,),
            )

            prerequisite_count = cursor.fetchone()[0]

    print("\n========== EDUPATH COURSE SEED REPORT ==========")

    print("Course              :", COURSE["course_name"])
    print("Course ID           :", course_id)
    print("Topics saved        :", len(saved_topics))
    print("New prerequisites  :", inserted_count)
    print("Total prerequisites:", prerequisite_count)

    print("\nCourse topics:")

    for sequence, name in saved_topics:
        print(f"  {sequence}. {name}")

    print("\nCourse initialization successful!")


if __name__ == "__main__":
    try:
        seed_course()

    except Exception as error:
        print("\nCOURSE SEED FAILED")
        print("Error type:", type(error).__name__)
        print("Details:", str(error))
