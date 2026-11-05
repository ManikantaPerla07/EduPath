from pathlib import Path
import hashlib
import re
import tomllib

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"

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
    """Load the Neon connection string."""

    if not SECRETS_FILE.exists():
        raise FileNotFoundError("secrets.toml was not found.")

    with SECRETS_FILE.open("rb") as file:
        secrets = tomllib.load(file)

    database_url = secrets.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    return database_url


def calculate_checksum(sql):
    """Calculate a stable checksum for a migration."""

    return hashlib.sha256(
        sql.encode("utf-8")
    ).hexdigest()


def get_migration_files():
    """Find and sort all migration files."""

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not files:
        raise FileNotFoundError(
            "No SQL migration files were found."
        )

    for file in files:
        if not re.fullmatch(
            r"\d{3}_[a-z0-9_]+",
            file.stem
        ):
            raise ValueError(
                f"Invalid migration filename: {file.name}"
            )

    return files


def create_migration_history(connection):
    """Create migration tracking table if necessary."""

    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)


def apply_migration(connection, migration_file):
    """Apply one migration if it has not already been applied."""

    migration_name = migration_file.stem

    migration_sql = migration_file.read_text(
        encoding="utf-8-sig"
    )

    checksum = calculate_checksum(migration_sql)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT checksum
            FROM schema_migrations
            WHERE version = %s;
            """,
            (migration_name,)
        )

        existing = cursor.fetchone()

    if existing:

        if existing[0] != checksum:
            raise RuntimeError(
                f"Checksum mismatch: {migration_name}. "
                "Do not edit an already-applied migration."
            )

        print(f"[SKIPPED] {migration_name}: Already applied.")
        return "skipped"

    print(f"[RUNNING] {migration_name}")

    # Each migration executes in its own transaction.
    with connection.transaction():

        with connection.cursor() as cursor:

            cursor.execute(
                migration_sql,
                prepare=False
            )

            cursor.execute(
                """
                INSERT INTO schema_migrations (
                    version,
                    checksum
                )
                VALUES (%s, %s);
                """,
                (migration_name, checksum)
            )

    print(f"[APPLIED] {migration_name}")
    return "applied"


def verify_database(connection):
    """Verify application tables and question identifiers."""

    with connection.cursor() as cursor:

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

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'question_bank'
                  AND column_name = 'question_code'
            );
            """
        )

        question_code_exists = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = 'public.question_bank'::regclass
                  AND conname = 'uq_question_bank_code'
                  AND contype = 'u'
            );
            """
        )

        unique_constraint_exists = cursor.fetchone()[0]

        if not question_code_exists:
            raise RuntimeError(
                "question_code column is missing."
            )

        if not unique_constraint_exists:
            raise RuntimeError(
                "Question code unique constraint is missing."
            )

    return len(existing_tables)


def run_migrations():
    """Execute all pending migrations in sequence."""

    migration_files = get_migration_files()

    database_url = load_database_url()

    results = {
        "applied": 0,
        "skipped": 0,
    }

    # Autocommit allows each migration to use its
    # own explicit transaction.
    with psycopg.connect(
        database_url,
        connect_timeout=20,
        autocommit=True
    ) as connection:

        create_migration_history(connection)

        for migration_file in migration_files:

            status = apply_migration(
                connection,
                migration_file
            )

            results[status] += 1

        table_count = verify_database(connection)

    print("\n========== EDUPATH MIGRATION REPORT ==========")

    print("Database connection :", "SUCCESS")
    print("Total migrations    :", len(migration_files))
    print("New migrations      :", results["applied"])
    print("Already applied     :", results["skipped"])
    print("Application tables  :", table_count)
    print("Schema verification :", "SUCCESS")

    print("\nAll migrations completed successfully.")


if __name__ == "__main__":

    try:
        run_migrations()

    except Exception as error:

        print("\nMIGRATION FAILED")
        print("Error type:", type(error).__name__)
        print("Details:", str(error))

        raise SystemExit(1)
