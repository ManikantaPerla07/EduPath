# EduPath Development Log

## Milestone 1: Project and Database Initialization

Date: 2026-11-05

### Environment
- Python: 3.11.9
- Git: 2.56.0
- Psycopg: 3.3.8
- Virtual environment: .venv

### Database
- Provider: Neon
- Database: neondb
- PostgreSQL: 18.6
- pgvector: 0.8.6

### Completed
- Initialized Git repository on main branch.
- Created project directory structure.
- Created Python virtual environment.
- Configured .gitignore.
- Created project README.
- Created Streamlit configuration.
- Verified Python-to-Neon connection.
- Created initial SQL migration.
- Implemented migration runner.
- Successfully applied 001_initial_schema.
- Verified all 17 application tables.

### Next Milestone
Insert the initial Python course, topics and prerequisite relationships.

## Milestone 2: Python Course Initialization

Date: 2026-11-05

### Completed
- Created an idempotent Python course seeding script.
- Initialized Python Programming course.
- Inserted nine learning topics.
- Created eleven topic prerequisite relationships.
- Verified database records.
- Tested duplicate-safe execution.

### Idempotency Verification
- Executed the Python course seed script a second time.
- Confirmed that all nine topics remained unchanged.
- Confirmed zero duplicate prerequisite insertions.
- Verified all eleven prerequisite relationships remained intact.
- Confirmed repeatable database initialization.

## Milestone 3: Versioned Database Migrations

### Completed
- Added stable question identifiers.
- Created migration 002.
- Upgraded the migration runner to discover SQL files.
- Added migration checksum verification.
- Added individual migration transactions.
- Verified existing migration skipping.
- Verified question code uniqueness constraint.
- Tested repeated migration execution.

## Milestone 3: Versioned Database Migrations

### Completed
- Added stable question identifiers.
- Created migration 002.
- Upgraded the migration runner to discover SQL files.
- Added migration checksum verification.
- Added individual migration transactions.
- Verified existing migration skipping.
- Verified question code uniqueness constraint.
- Tested repeated migration execution.
