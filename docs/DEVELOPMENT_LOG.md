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

## 2026-11-07 — Google Authentication and Neon Integration

- Integrated Google authentication with the learner registration service.
- Added authenticated Google OIDC identity extraction to `app.py`.
- Added identity token timestamp validation.
- Connected first-time and returning learner sign-ins to Neon PostgreSQL.
- Implemented automatic learner account and profile retrieval.
- Added an explicit 18+ confirmation screen.
- Saved adult confirmation to the learner profile.
- Added the authenticated learner dashboard.
- Verified real Google sign-in and dashboard access.
- Verified Neon contains one learner account and one linked profile.
- Verified the learner account is active and adult confirmation is saved.
- Rechecked account and profile counts: one user, one profile, one linked account.
- Result: Local Google authentication and Neon learner registration integration successfully tested.

## 2026-11-07 — Assessment Submission Service

- Created `services/assessment_submission_service.py`.
- Implemented assessment ownership verification.
- Added assessment session locking during submission.
- Implemented grading using saved assessment question snapshots.
- Reused the existing MCQ grading service.
- Added validation against unknown question item IDs.
- Saved learner responses and awarded points in PostgreSQL.
- Implemented score percentage and question-level result calculation.
- Added handling for unanswered questions.
- Finalized submitted assessment sessions transactionally.
- Added safe retrieval of previously submitted results.
- Created `tests/test_assessment_submission_service.py` with 7 unit tests.
- Verified ownership protection, grading, scoring, unanswered questions, repeated submissions, and abandoned assessment rejection.
- All 42 tests across the complete project test suite passed.
- Result: Assessment submission service successfully tested with mocked database operations.
- Streamlit assessment interface and live assessment submission testing remain pending.

## 2026-11-08 — Assessment UI and Navigation Optimization

- Created the modular Streamlit assessment interface in `ui/assessment.py`.
- Added Python diagnostic assessment introduction.
- Implemented one-question-at-a-time navigation.
- Added answer selection and session-state preservation.
- Added assessment progress indicator.
- Integrated assessment submission and results display.
- Added question-level answer review and explanations.
- Connected the assessment interface to the learner dashboard.
- Fixed dashboard-to-assessment navigation using a Streamlit callback.
- Added Streamlit fragment-based assessment rendering.
- Optimized question navigation to avoid full application reruns.
- Added learner caching with a 60-second refresh interval.
- Added session cleanup during sign-out.
- Created `tests/test_assessment_ui.py` with 9 tests.
- Verified dashboard and assessment navigation in the browser.
- Verified answer preservation and improved navigation responsiveness.
- All 51 project tests passed.
- Result: Assessment frontend successfully integrated and locally tested.

## 2026-11-08 — Learner Topic Progress and Dashboard

- Created `services/progress_service.py`.
- Implemented topic accuracy and mastery score calculations.
- Added evidence-based mastery status classification.
- Added learner progress aggregation from submitted assessments.
- Excluded unanswered questions from attempt and accuracy calculations.
- Implemented idempotent learner-topic progress upserts.
- Added learner-specific topic progress retrieval.
- Included topics without existing progress records.
- Integrated automatic progress updates into assessment submission.
- Ensured progress updates occur within the assessment submission transaction.
- Added historical progress refresh when retrieving previously submitted results.
- Created `tests/test_progress_service.py` with 24 unit tests.
- Extended assessment submission tests to verify progress integration and transaction rollback.
- Integrated topic progress into the authenticated Streamlit dashboard.
- Displayed progress summaries and individual progress cards for all nine Python topics.
- Verified real learner progress against Neon PostgreSQL.
- Verified all nine topic cards in the running Streamlit application.
- Verified 7 of 9 topics assessed, 16 answered questions, and 18.8% overall answered-question accuracy.
- All 77 tests across the complete project test suite passed.
- Result: Learner topic progress service and dashboard successfully integrated and locally verified.
