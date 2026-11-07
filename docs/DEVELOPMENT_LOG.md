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

## 2026-11-05 — MCQ Grading Service

- Created `services/grading_service.py` with reusable MCQ grading logic.
- Implemented case-insensitive answer comparison.
- Added support for unanswered questions and custom question points.
- Used Decimal arithmetic for reliable score calculation.
- Added validation for answer keys, submitted answers, and points.
- Ensured explanations are returned as part of the post-submission grading result.
- Created `tests/test_grading_service.py` with 14 unit tests.
- Result: All 14 grading service tests passed.

## 2026-11-05 — Assessment Session Service

- Created `services/assessment_session_service.py`.
- Implemented learner ID, course, topic, and assessment-type validation.
- Added active learner account verification.
- Implemented assessment session creation and question snapshot insertion.
- Used database transactions so incomplete session creation is rolled back.
- Kept answer keys in backend database records and excluded them from learner-facing payloads.
- Created `tests/test_assessment_session_service.py` with 6 tests.
- Verified validation, empty question handling, and rejection of nonexistent learners.
- Result: All 6 assessment session service tests passed.
- Successful session creation remains pending authenticated learner integration.

## 2026-11-07 — Google Authentication

- Added Streamlit to project dependencies with authentication support.
- Created the initial EduPath Streamlit application in `app.py`.
- Configured Google OAuth using Streamlit built-in authentication.
- Created a separate Google Cloud project and Web application OAuth client.
- Configured the local authentication secrets securely.
- Fixed UTF-8 BOM in `.streamlit/config.toml`.
- Verified Google sign-in and sign-out successfully.
- Verified authenticated learner name and email display.
- Confirmed `.streamlit/secrets.toml` remains excluded from Git.
- Result: Local Google authentication flow successfully tested.
- Database learner registration remains pending.

## 2026-11-07 — Learner Registration Service

- Created `services/learner_service.py`.
- Implemented Google OIDC identity extraction and validation.
- Used issuer and subject as the unique learner identity.
- Implemented automatic learner account creation and retrieval.
- Added inactive-account protection without modifying disabled accounts.
- Added idempotent learner profile creation.
- Preserved existing learner preferences during subsequent sign-ins.
- Ensured new profiles start with adult_confirmation=False.
- Implemented explicit adult confirmation handling.
- Created `tests/test_learner_service.py` with 15 unit tests.
- Verified registration, identity validation, existing profiles, inactive accounts, and adult confirmation.
- All 35 tests across the complete project test suite passed.
- Result: Learner registration service successfully tested with mocked database operations.
- Integration with the authenticated Streamlit application remains pending.
