from pathlib import Path
import tomllib
import psycopg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

with SECRETS_FILE.open("rb") as file:
    database_url = tomllib.load(file)["DATABASE_URL"]

with psycopg.connect(database_url, connect_timeout=20) as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                t.topic_slug,
                COUNT(q.question_code) FILTER (
                    WHERE q.is_active = TRUE
                ) AS total,
                COUNT(q.question_code) FILTER (
                    WHERE q.is_active = TRUE AND q.difficulty = 'easy'
                ) AS easy,
                COUNT(q.question_code) FILTER (
                    WHERE q.is_active = TRUE AND q.difficulty = 'medium'
                ) AS medium,
                COUNT(q.question_code) FILTER (
                    WHERE q.is_active = TRUE AND q.difficulty = 'hard'
                ) AS hard
            FROM courses AS c
            JOIN topics AS t ON t.course_id = c.course_id
            LEFT JOIN question_bank AS q ON q.topic_id = t.topic_id
            WHERE c.course_slug = %s
            GROUP BY t.topic_slug
            ORDER BY t.topic_slug;
            """,
            ("python-basics",)
        )

        rows = cursor.fetchall()

        print("\n========== TOPIC-WISE QUESTION AUDIT ==========")
        for row in rows:
            print(
                f"{row[0]:25} Total: {row[1]} | "
                f"Easy: {row[2]} | Medium: {row[3]} | Hard: {row[4]}"
            )

        cursor.execute(
            """
            SELECT question_code, COUNT(*)
            FROM question_bank
            GROUP BY question_code
            HAVING COUNT(*) > 1;
            """
        )
        duplicates = cursor.fetchall()

        total = sum(row[1] for row in rows)
        valid_topics = (
            len(rows) == 9
            and all(row[1:] == (3, 1, 1, 1) for row in rows)
        )

        print("\nTotal active questions:", total)
        print("Duplicate question codes:", len(duplicates))
        print("Topic distribution:", "PASS" if valid_topics else "FAIL")

        if total == 27 and valid_topics and not duplicates:
            print("\nQUESTION BANK DATABASE AUDIT: SUCCESS")
        else:
            print("\nQUESTION BANK DATABASE AUDIT: FAILED")
            raise SystemExit(1)
