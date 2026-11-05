from pathlib import Path
import tomllib
import psycopg


def load_database_url():
    """Read the database URL from local Streamlit secrets."""

    project_root = Path(__file__).resolve().parents[1]
    secrets_path = project_root / ".streamlit" / "secrets.toml"

    if not secrets_path.exists():
        raise FileNotFoundError("secrets.toml file was not found.")

    with secrets_path.open("rb") as file:
        secrets = tomllib.load(file)

    database_url = secrets.get("DATABASE_URL")

    if not database_url or "PASTE_" in database_url:
        raise ValueError("DATABASE_URL is missing or invalid.")

    return database_url


def test_connection():
    """Connect to Neon and verify PostgreSQL and pgvector."""

    try:
        database_url = load_database_url()

        with psycopg.connect(
            database_url,
            connect_timeout=15
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_setting('server_version');
                """)

                database, username, version = cursor.fetchone()

                cursor.execute("""
                    SELECT extversion
                    FROM pg_extension
                    WHERE extname = %s;
                """, ("vector",))

                vector_result = cursor.fetchone()

        print("\n========== EDUPATH DATABASE CHECK ==========")

        print("PostgreSQL connection : SUCCESS")
        print("Database name         :", database)
        print("Database user         :", username)
        print("PostgreSQL version    :", version)

        if vector_result:
            print("pgvector              : INSTALLED")
            print("pgvector version      :", vector_result[0])
        else:
            print("pgvector              : NOT INSTALLED")

        print("\nDatabase connection test completed.")

    except Exception as error:
        print("\nDATABASE CONNECTION FAILED")
        print("Error type:", type(error).__name__)
        print("Details:", error)


if __name__ == "__main__":
    test_connection()
