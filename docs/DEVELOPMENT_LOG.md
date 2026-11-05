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

## 2026-11-05 — Python Question Bank

- Created `database/seed_questions.py` to initialize the Python Programming MCQ bank.
- Added 27 MCQs across 9 topics, with 1 easy, 1 medium, and 1 hard question per topic.
- Used stable question codes and PostgreSQL upserts to make seeding repeatable.
- Executed the seeding script twice successfully; the database retained exactly 27 active questions.
- Created `database/verify_question_bank.py` to audit topic-wise distribution and duplicate question codes.
- Verified all 9 topics, the 27-question total, the expected difficulty distribution, and zero duplicate codes.
- Result: Question bank initialization and database audit passed.

## 2026-11-05 — Assessment Question Selection Service

- Created `services/assessment_service.py` for retrieving active assessment questions from PostgreSQL.
- Implemented course, topic, difficulty, and result-limit filtering.
- Added input validation for course, topic, difficulty, and limit.
- Implemented `build_learner_question()` using an allowlist to prevent answer-key and explanation leakage.
- Created `tests/test_assessment_service.py`.
- Verified all 27 questions, topic and difficulty distributions, filtering, and answer-key protection.
- Result: All assessment service checks passed.
