from pathlib import Path
import hashlib
import tomllib

import psycopg


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

MIGRATION_FILE = (
    PROJECT_ROOT
    / "database"
    / "migrations"
    / "001_initial_schema.sql"
)

MIGRATION_NAME = "001_initial_schema"


EXPECTED_TABLES = {
    "users",
    "learner_profiles",
    "courses",
    "topics",
    "topic_prerequisites",
    "question_bank",
    "assessment_sessions",
    "assessment_items",
    "assessment_responses",
    "study_plans",
    "study_plan_items",
    "learner_topic_progress",
    "chat_sessions",
    "chat_messages",
    "documents",
    "agent_runs",
    "model_usage_events",
}


def load_database_url():
    """Load the Neon connection string securely."""

    if not SECRETS_FILE.exists():
        raise FileNotFoundError(
            "Streamlit secrets.toml was not found."
        )

    with SECRETS_FILE.open("rb") as file:
        secrets = tomllib.load(file)

    database_url = secrets.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    return database_url


def apply_migration():
    """Apply the initial migration exactly once."""

    if not MIGRATION_FILE.exists():
        raise FileNotFoundError(
            "Initial SQL migration file was not found."
        )

    migration_sql = MIGRATION_FILE.read_text(
        encoding="utf-8-sig"
    )

    checksum = hashlib.sha256(
        migration_sql.encode("utf-8")
    ).hexdigest()

    database_url = load_database_url()

    with psycopg.connect(
        database_url,
        connect_timeout=20
    ) as connection:

        with connection.cursor() as cursor:

            # Create migration history table.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            # Check whether this migration was applied.
            cursor.execute(
                """
                SELECT checksum
                FROM schema_migrations
                WHERE version = %s;
                """,
                (MIGRATION_NAME,)
            )

            existing = cursor.fetchone()

            if existing:
                if existing[0] != checksum:
                    raise RuntimeError(
                        "Migration file changed after application. "
                        "Create a new migration instead."
                    )

                print("Migration already applied.")

            else:
                print("Applying initial database migration...")

                # Execute all DDL statements together.
                cursor.execute(
                    migration_sql,
                    prepare=False
                )

                # Record successful migration.
                cursor.execute(
                    """
                    INSERT INTO schema_migrations
                    (version, checksum)
                    VALUES (%s, %s);
                    """,
                    (MIGRATION_NAME, checksum)
                )

                print("Migration executed successfully.")

            # Verify expected application tables.
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                  AND table_name = ANY(%s)
                ORDER BY table_name;
                """,
                (sorted(EXPECTED_TABLES),)
            )

            existing_tables = {
                row[0] for row in cursor.fetchall()
            }

            missing_tables = EXPECTED_TABLES - existing_tables

            if missing_tables:
                raise RuntimeError(
                    f"Missing tables: {sorted(missing_tables)}"
                )

    print("\n========== EDUPATH MIGRATION REPORT ==========")
    print("Database connection : SUCCESS")
    print("Migration           :", MIGRATION_NAME)
    print("Migration status    : APPLIED")
    print("Application tables  :", len(existing_tables))
    print("Schema verification : SUCCESS")

    print("\nAll expected application tables:")
    for table in sorted(existing_tables):
        print("  [OK]", table)

    print("\nDatabase migration completed successfully!")


if __name__ == "__main__":
    try:
        apply_migration()

    except Exception as error:
        print("\nMIGRATION FAILED")
        print("Error type:", type(error).__name__)
        print("Details:", str(error))
        print("\nNo partial transaction should be committed.")
