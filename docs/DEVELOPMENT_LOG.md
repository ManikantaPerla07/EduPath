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

## 2026-11-08 — Personalized Study Plan and Activity Completion

- Created `services/study_plan_service.py` for deterministic, learner-specific study-plan generation.
- Implemented topic prioritization using assessment performance, mastery status, learning goals, and prerequisite relationships.
- Generated personalized schedules using the learner's available daily study time.
- Persisted study plans and scheduled activities in Neon PostgreSQL.
- Implemented retrieval of active and completed study plans.
- Added ownership and learner eligibility validation for activity updates.
- Implemented activity completion, reopening, and status persistence.
- Automatically marks a plan completed when all activities are completed.
- Automatically restores the active plan status when an activity is reopened.
- Added live completion percentage, completed activity count, and remaining activity count to the UI.
- Created the modular Streamlit study-plan interface in `ui/study_plan.py`.
- Integrated the Study Plan page into application navigation.
- Created `tests/test_study_plan_service.py` with 33 tests.
- Verified activity completion and reopening through the Streamlit interface.
- Verified saved activity statuses and plan completion in Neon PostgreSQL.
- Verified the final completed plan contains 9 activities, all completed.
- Ran Python compilation successfully.
- All 110 tests across the complete project test suite passed.
- Result: Personalized study-plan generation and activity completion successfully integrated and locally verified.

## 2026-11-08 - RAG Knowledge Base and Grounded Tutor

- Created `services/text_processing_service.py` for PDF, TXT, and Markdown extraction, text normalization, and page-aware chunking.
- Created `services/document_service.py` for validated educational document ingestion and admin-only shared resource uploads.
- Added database migration `003_document_chunks.sql` with document chunk metadata and 768-dimensional pgvector embeddings.
- Updated the migration runner and verified the expected 18 application tables.
- Created `services/embedding_service.py` using Gemini Embedding 2 with 768-dimensional embeddings.
- Implemented pending-chunk embedding storage with retry-safe processing and protection against duplicate embedding requests.
- Created `services/retrieval_service.py` for semantic search using Neon PostgreSQL and pgvector cosine similarity.
- Added course and topic filtering and source metadata retrieval for educational citations.
- Created `services/answer_generation_service.py` for grounded educational answers using Gemini 3.8 Flash.
- Added Gemini 3.5 Flash Lite fallback for temporary HTTP 500, 502, 503, and 504 server errors.
- Implemented insufficient-evidence handling, citation identifier validation, and source metadata mapping.
- Added tests for document extraction, ingestion, embeddings, vector storage, semantic retrieval, answer generation, and fallback handling.
- Added a sanitized synthetic Python learning resource for end-to-end verification.
- Successfully generated and stored a 768-dimensional Gemini embedding in Neon.
- Verified idempotent embedding processing for an already embedded document.
- Successfully executed a real semantic retrieval request against Neon.
- Successfully generated a grounded tutor response using Gemini 3.8 Flash and verified its citation against the retrieved source.
- OCR for scanned documents remains unsupported; documents without extractable text are rejected.
- All 232 project tests passed.
- Result: Document ingestion, embedding, semantic retrieval, and grounded answer generation successfully tested and integrated at the service level.

## 2026-11-08 - Persistent Chat Service

- Created `services/chat_service.py` for persistent learner conversations.
- Implemented chat-session creation and learner-owned session listing.
- Implemented ownership-checked session and message retrieval.
- Added chronological conversation history retrieval.
- Implemented user and assistant message persistence.
- Persisted assistant citation metadata using PostgreSQL JSONB.
- Updated chat-session activity timestamps when messages are saved.
- Added automatic conversation titles from the first learner message when no title exists.
- Implemented conversation renaming and deletion.
- Used the existing unique LangGraph thread identifier for future agent integration.
- Enforced learner ownership checks for session reads, writes, renaming, and deletion.
- Created `tests/test_chat_service.py` with 25 unit tests.
- Verified real Neon session creation, message persistence, chronological history retrieval, citation persistence, renaming, and deletion.
- Confirmed temporary integration-test conversations were cleaned up.
- No database migration was required.
- All 257 project tests passed.
- Result: Persistent chat service successfully tested with mocked operations and a real Neon PostgreSQL integration test.

## 2026-11-08 - Streamlit AI Tutor and Conversation Management

- Created `ui/tutor.py` for the authenticated conversational AI Tutor.
- Integrated AI Tutor into the existing Streamlit sidebar navigation.
- Connected the Tutor interface to the persistent chat service and grounded RAG answer-generation pipeline.
- Implemented new conversations and recent conversation selection.
- Added chronological conversation history restoration from Neon PostgreSQL.
- Displayed assistant answers with expandable source citation details.
- Added conversation renaming and deletion with explicit confirmation.
- Reloaded the saved transcript after successful responses to prevent duplicate message rendering.
- Fixed PostgreSQL parameter type inference in optional course filtering in `list_chat_sessions`.
- Added a regression test for conversation listing without a course filter.
- Verified real learner questions and grounded Gemini responses through the Streamlit interface.
- Verified that multiple user and assistant messages and citations persist after browser refresh.
- Verified conversation creation, switching, renaming, and deletion against Neon PostgreSQL.
- Confirmed that deleting a conversation preserves other conversations.
- All 258 project tests passed.
- Result: The first functional, persistent Streamlit AI Tutor interface successfully integrated and locally verified.

## 2026-11-08 - LangGraph Tutor Workflow Integration

- Added `langgraph>=1.0,<2.0` to runtime requirements.
- Created `requirements-dev.txt` for development and test dependencies, including pytest.
- Created the `agents` package and `agents/tutor_graph.py`.
- Implemented graph input validation for learner questions, course slugs, topic slugs, and retrieval limits.
- Added semantic retrieval and conditional routing based on whether educational source chunks were found.
- Reused the existing grounded answer-generation service and its verified citation metadata.
- Added a safe abstention path when retrieval returns no evidence.
- Integrated `run_tutor_graph()` into the Streamlit AI Tutor.
- Created `tests/test_tutor_graph.py` with five tests for successful retrieval, abstention, input validation, and dependency injection.
- Verified the Tutor interface displays generated answers and expandable source citations.
- Verified Python compilation and Git whitespace checks.
- No database migration was required; Neon remains the source of truth for persisted conversations.
- All 264 project tests passed, with 19 subtests passed.
- Result: LangGraph-based tutoring workflow successfully integrated and locally verified.

## 2026-11-08 - Conversation-Aware AI Tutoring

- Updated chat-history retrieval to select the most recent requested messages while returning them in chronological order.
- Added regression assertions for recent-message selection and chronological presentation.
- Created `services/conversation_context_service.py` to resolve contextual follow-up questions into standalone retrieval queries.
- Added bounded conversation context using at most 10 recent messages and an 8,000-character total history budget.
- Treated previous conversation messages as untrusted context, not factual educational evidence or instructions.
- Reused Gemini generation models and the existing temporary-server-error fallback for context resolution.
- Extended the LangGraph state and added a conversation-context resolution node before semantic retrieval.
- Kept grounded answer generation and citation validation connected to approved retrieved course chunks.
- Updated the Streamlit Tutor to load recent history before saving the current learner question.
- Passed previous conversation messages into the LangGraph workflow without changing the original saved transcript.
- Added eight conversation-context service tests and three LangGraph context-integration tests.
- Verified contextual follow-up behavior in Streamlit using a Python-variable question and a reference-based follow-up.
- Verified Python compilation and Git whitespace checks.
- No database migration or new paid service was required; Neon remains the conversation store.
- All 275 project tests passed, with 19 subtests passed.
- Result: Conversation-aware, source-grounded follow-up tutoring successfully integrated and locally verified.

## 2026-11-09 — Progress-Based Adaptive Tutoring

- Added `services/adaptive_learning_service.py` to map learner topic mastery
  statuses to deterministic teaching guidance.
- Selected the most relevant retrieved topic and matched it with the learner's
  topic progress to determine the teaching approach.
- Extended grounded answer generation with optional teaching guidance.
  Guidance controls explanation depth, pacing, and practice difficulty only;
  retrieved knowledge sources remain the factual authority.
- Added an `adapt_teaching` node to the LangGraph tutoring workflow.
  Adaptation runs only when relevant knowledge chunks are retrieved.
- Passed the authenticated learner ID from the Streamlit tutor UI into the graph.
- Persisted the personalization approach in assistant messages so it remains
  visible when conversation history is reloaded.
- Refactored question processing so the saved Neon transcript is the single
  source used to render conversation messages.
- Improved conversation-context resolution: standalone questions are preserved
  without unnecessary rewriting, while questions containing contextual
  references can still use conversation history.
- Added tests for adaptive profiles, answer-generation guidance, graph
  integration, and standalone-question preservation.
- Verified the complete test suite: 295 passed, 19 subtests passed.
- Verified Python compilation and `git diff --check`.
- No database migration was required.

## 2026-11-09 — Adaptive Practice and Assessment

- Added `services/adaptive_question_service.py` for progress-based question
  selection using learner topic mastery.
- Prioritized topics needing revision, followed by unassessed topics and
  topics with stronger progress.
- Mapped mastery statuses to preferred question difficulty:
  easy for unassessed and revision topics, medium for developing topics,
  and hard for mastery candidates.
- Spread question selection across topics before selecting additional
  questions from previously represented topics.
- Avoided the learner's 15 most recently answered question-bank items when
  fresh alternatives were available; reused questions when necessary.
- Integrated adaptive selection into `start_assessment()` for practice and
  revision sessions.
- Preserved the original diagnostic assessment behavior and full question-bank
  selection.
- Added five-question Adaptive Practice and Targeted Revision modes to the
  Streamlit assessment interface.
- Added assessment-mode labels to the active question screen.
- Preserved safe learner question payloads through the existing
  `build_learner_question()` allowlist and assessment question snapshots.
- Added unit and integration tests for adaptive selection, session creation,
  assessment modes, and mode labels.
- Verified the live Diagnostic screen displays 27 questions and the live
  Adaptive Practice screen displays 5 questions.
- Verified the complete project test suite: 319 passed, 19 subtests passed.
- Verified Python compilation and `git diff --check`.
- No database migration was required.

## 2026-11-09 - Dynamic Adaptive Assessments

- Changed Adaptive Practice and Targeted Revision sessions to start with
  only their first question while retaining a five-question target.
- Added `services/adaptive_assessment_service.py` to grade each submitted
  answer against the server-side assessment snapshot.
- Added incremental response persistence, session ownership checks, and
  session locking so an answer cannot be submitted twice or against
  another learner's assessment.
- Added dynamic next-question selection based on the previous answer:
  correct answers prefer a higher difficulty, while incorrect answers
  prefer a lower difficulty.
- Prioritized the current topic when eligible questions remain, with
  fallback to other topics and available difficulty levels.
- Prevented question reuse within the current adaptive session and
  continued avoiding recently attempted questions when alternatives exist.
- Finalized adaptive sessions after five answers or when no unused
  eligible questions remain, then refreshed learner topic progress.
- Updated the Streamlit interface to show one adaptive question at a time,
  immediate correctness feedback, explanations, and the next selected
  question.
- Preserved Diagnostic Assessment's existing navigation and batch
  submission workflow.
- Added tests for difficulty transitions, question selection, answer
  validation, incremental submission, and session finalization.
- Manually verified Adaptive Practice and Targeted Revision through the
  Streamlit interface, including question progression and final results.
- Manually verified that Diagnostic Assessment still displays 27 questions
  with Previous and Next navigation.
- Verified the full project test suite: 353 passed, 19 subtests passed.
- Verified Python compilation and `git diff --check`.
- No database migration was required.

## 2026-11-09 - Local and Hosted Secret Configuration

- Added a shared secret loader supporting local Streamlit secrets and
  Streamlit-hosted runtime secrets.
- Updated database and Gemini credential loading to use the shared loader.
- Preserved local secrets-file support for development.
- Added tests for local loading, hosted loading, and missing credentials.
- Updated the existing missing-secret test for the new fallback behavior.
- Verified the complete test suite: 356 passed, 19 subtests passed.
- Verified Python compilation and `git diff --check`.

## 2026-11-11 — Gemini Tool-Router Fallback and Transport Resilience

- Added shared Gemini error classification for temporary HTTP 500, 502, 503,
  and 504 responses, including recognized HTTPX/HTTPCore transport failures
  such as remote protocol disconnects and request timeouts.
- Extended learner-tool routing to try the configured primary model first and
  use Gemini 3.5 Flash Lite when the primary request fails transiently.
- Kept fallback bounded to one alternate model; authentication, permission,
  and invalid-request errors do not trigger a model switch.
- Preserved explicit model injection for deterministic graph tests.
- Reused the shared retry classification in both direct Google Gen AI and
  LangChain answer-generation fallback paths.
- Added tests for status-code extraction, wrapped transport exceptions,
  non-retryable client errors, learner-tool fallback selection, and bounded
  routing behavior.
- Automated test execution on the developer's local Windows environment is
  pending after pulling this milestone. Live Gemini tool-calling verification
  is also pending; a simple authenticated Gemini 3.5 Flash Lite text request
  previously returned HTTP 200.

## 2026-11-11 — Gemini Router Fallback Verification

- Added shared transient-error classification for HTTP 500, 502, 503 and 504
  responses and recognized HTTPX/HTTPCore transport interruptions.
- Added one bounded fallback attempt from Gemini 3.8 Flash to Gemini 3.5
  Flash Lite for learner-tool routing.
- Reused the same error classification for direct Google Gen AI and
  LangChain answer-generation paths.
- Added regression tests for transport failures, wrapped exceptions,
  non-retryable client errors, and bounded fallback behavior.
- Developer verified the focused suite: 60 passed, 9 subtests passed.
- Developer verified the full suite: 421 passed, 31 subtests passed.
- Python compilation and `git diff --check` succeeded.
- Manually verified a successful AI Tutor response to
  "What is in my study plan?" in Streamlit. The answer displayed the
  saved completed plan, 9 of 9 completed activities, and 100% completion.
- The UI identified Gemini 3.8 Flash as the answer-generation model.
  The live tool-router model was not separately instrumented, so the
  manual test confirms the successful learner-data answer, not which
  router model handled that request.
- No database migration was required.

## 2026-11-11 — Administrator Knowledge Management (Implementation in Progress)

- Added active-administrator checks to course, topic, document inventory,
  and failed-document retry service operations.
- Added a document inventory query that reports extraction status,
  text chunk counts, and embedded chunk counts without returning original
  file bytes or chunk contents.
- Added reprocessing for failed PDF, TXT and Markdown documents using the
  original file bytes already stored in Neon.
- Chunk replacement and the transition back to ready occur in one
  PostgreSQL transaction. Failed retries retain a visible failed status.
- Added the Streamlit Knowledge Management page for administrators:
  document upload, course/topic association, license and rights metadata,
  document inventory, embedding generation, and failed extraction retry.
- Added the Knowledge Management navigation item only for users whose
  persisted role is administrator. Backend service operations independently
  enforce administrator authorization.
- Added service and UI tests for authorization, inventory metadata,
  embedding status display, and failed-document retry.
- No database migration or new paid service was required.
- Local automated test execution and live administrator UI verification
  are pending after the developer pulls this milestone.
- Course publication controls, resource deletion/archival, and instructor
  analytics remain outside this implementation slice.

## 2026-11-11 — Course Publication and Safe Resource Archival

- Added migration `004_document_archival.sql` with nullable
  `documents.archived_at` and an active-course index. Archival preserves
  uploaded bytes, extracted chunks, embeddings and source metadata.
- Added course publication services with active-administrator authorization.
  Publishing requires at least one topic, at least one active assessment
  question, and one ready, non-archived document whose chunks all have
  embeddings.
- Added administrator publication readiness metrics and publish/unpublish
  controls to Knowledge Management.
- Added archive and restore actions with explicit archival confirmation.
  Archived resources are excluded from learner RAG retrieval and cannot be
  embedded or retried until restored.
- Archiving the last fully embedded active resource automatically unpublishes
  an already-published course in the same database transaction.
- Added learner access checks for application entry, assessment question
  selection/session creation, topic progress, study-plan generation and
  retrieval. Existing assessment submissions are not forcibly discarded.
- Added tests for publication readiness, admin authorization, archive/restore,
  automatic unpublishing, archived embedding rejection and published-course
  access filters.
- Developer applied migration 004 successfully to Neon on November 11,
  2026. The migration report confirmed all four application migrations,
  18 application tables, LangGraph checkpoints ready, and schema verification
  successful.
- The first focused/full test run reported 450 passed, 31 subtests passed,
  and four failures. Three were outdated adaptive-assessment test fixtures
  that did not include the newly queried publication flag; one expected an
  earlier readiness-error phrase. The fixtures and readiness message have
  been corrected in follow-up commits. Final regression verification remains
  pending.
- Course publication readiness is a minimum technical gate. Administrators
  must still review actual topic coverage and source rights before publication.
- No external service or paid dependency was added.

## 2026-11-11 — Python Knowledge-Base Topic Coverage

- Extended course publication readiness from a course-wide resource count to
  topic-specific coverage across the existing Python curriculum.
- A topic is covered only when it has at least one non-archived, ready,
  topic-assigned resource and every extracted chunk in that resource has an
  embedding stored.
- Course-wide resources remain visible in the inventory and count toward the
  overall resource count, but do not substitute for topic-specific coverage.
- Added topic coverage counts, uncovered topic identifiers, resource counts,
  and embedded-versus-total chunk counts to the administrator publication
  readiness response.
- Updated Knowledge Management to show a coverage progress bar and a
  topic-by-topic list identifying covered topics, incomplete embeddings,
  and topics still needing resources.
- Strengthened archive lifecycle protection: archiving a resource now
  rechecks every topic's coverage. A published course is automatically
  unpublished if any topic loses its last fully embedded resource, even when
  a course-wide resource remains.
- Added eight original Markdown learning notes for Operators, Conditionals,
  Loops, Functions, Lists and Tuples, Dictionaries and Sets, Strings, and
  Basic Problem Solving. The existing Variables and Data Types note remains.
- Added `sample_documents/README.md` with the nine-topic mapping and manual
  upload instructions. Sample files are not automatically inserted into Neon.
- Added `tests/test_sample_learning_resources.py` to verify that every
  curriculum topic maps to a Markdown file with Python examples, practice
  questions, and key points.
- A repository content audit confirmed all nine files and their upload-guide
  mappings satisfy those structural checks. This is a documentation structure
  check, not a factual or pedagogical review.
- Updated README to describe the topic-specific publishing requirement and
  sample resource library.
- No new database migration or dependency is required for topic coverage.
  Migration 004 remains the current schema version.
- Local automated verification and administrator UI review are pending after
  the developer pulls this milestone. The previous developer-verified full
  test suite was 454 passed, 31 subtests passed.
- Topic coverage is a technical ingestion/completeness measure, not an
  automated evaluation of factual accuracy or pedagogical quality. The
  administrator must still review source rights and educational content.

## Milestone: Persistent AI Tutor Answer Feedback

Date: 2026-11-11

### Completed
- Added database migration 005 for one feedback record per assistant message.
- Added learner-scoped feedback persistence to the chat service.
- The database write verifies that the message is an assistant response in a conversation owned by the authenticated learner.
- Added an upsert so a learner can change a previous thumbs-up/down rating without creating duplicate records.
- Included saved feedback in chronological chat-history retrieval.
- Added a thumbs-up/down control beneath each assistant response in the Tutor transcript.
- Restored previously saved ratings when messages are reopened.
- Added the feedback table to the migration runner's required-schema verification list.
- Added dedicated UI tests for positive/negative ratings, restoring saved feedback, changing a prior rating, and suppressing feedback controls on learner messages.
- Updated the README and added service tests for validation, ownership, assistant-role enforcement, retrieval and rating updates.

### Verification status
- Automated feedback tests have been added but have not yet been run in the local environment.
- Apply migration 005 by running the existing migration runner after pulling this commit.
- The nine sample learning resources remain unuploaded; final RAG corpus ingestion and live retrieval validation remain deferred to the final integration phase.

## Milestone: Administrator AI Tutor Feedback Insights

Date: 2026-11-11

### Completed
- Added an admin-only feedback analytics service for the published Python course's saved assistant-answer ratings.
- Added active-administrator authorization checks directly in PostgreSQL before reading metrics.
- Added overall assistant-answer count, rated-answer count, helpful and not-helpful totals, rating coverage, and helpful-rating share.
- Added a 14-day daily aggregate trend, including days with no ratings.
- Kept the report privacy-preserving: no learner IDs, message contents, or individual feedback rows are returned to the UI.
- Added an administrator-only AI Tutor Feedback navigation page.
- Added service and UI tests for authorization, empty feedback, aggregation, trend rendering, and input validation.
- Updated README feature and repository-structure documentation.

### Verification status
- Tests for this milestone have been added but have not yet been run in the local environment.
- The latest user-verified full-suite result before this milestone was 469 passed and 53 subtests passed.
- The nine sample learning resources remain unuploaded; final RAG corpus ingestion and live retrieval validation remain deferred to the final integration phase.

## Milestone: Golden-Query RAG Retrieval Evaluation

Date: 2026-11-11

### Completed
- Added 18 original golden queries covering all nine Python course topics, with two questions assigned to each topic.
- Added a retrieval evaluation service that searches course-wide without passing the expected topic as a filter.
- Added Hit@K, Precision@K, Mean Reciprocal Rank (MRR), retrieval coverage, and per-topic metrics.
- Added a command-line runner with readable output and optional JSON report export.
- Added benchmark documentation describing metric definitions, limitations, and final-phase execution.
- Added automated tests for the dataset, input validation, ranking metrics, course-wide search behavior, empty retrieval, and malformed retrieval results.
- Updated README with the evaluation workflow and final-integration requirement.

### Verification status
- The benchmark and metric tests have been added but have not yet been run in the local environment.
- The live evaluator has intentionally not been executed. It requires all nine approved resources to be uploaded, embedded, reviewed, and the Python course published. It makes one Gemini query-embedding request per golden query and performs read-only pgvector searches.
- This benchmark measures expected-topic retrieval alignment only. It does not establish factual correctness, answer faithfulness, citation correctness, or teaching quality.
- The latest user-verified full-suite baseline before this milestone was 479 passed and 58 subtests passed on November 11, 2026.

## Milestone: Authenticated AI Tutor Run Telemetry

Date: 2026-11-11

### Completed
- Added a telemetry service that creates and completes records in the existing `agent_runs` table.
- Persistent Tutor runs are associated with the authenticated user and the owned chat session.
- Successful runs store completion status and elapsed time; failed runs store status, elapsed time, and a validated exception-class code.
- Telemetry writes are best-effort. A telemetry database failure does not prevent a Tutor response or replace the original graph exception.
- Kept run telemetry content-free: no prompts, generated answers, retrieved excerpts, or learner profile data are written to the run record.
- Added tests for validation, active-user/session ownership, status transitions, error-code minimization, and resilience when telemetry writes fail.
- Updated README with the new observability behavior.

### Scope and verification
- This milestone currently records authenticated persistent chat-run lifecycle only. It does not yet populate `model_usage_events`; provider token usage is not consistently available from both direct Gemini and LangChain paths, so token counts will not be fabricated as zero-valued measurements.
- Per-node execution traces and a UI dashboard for run metrics are not included in this first pass.
- Tests have been added but have not yet been run in the local environment.
- The latest user-verified full-suite baseline before this milestone was 492 passed and 68 subtests passed on November 11, 2026.
- The nine sample learning resources remain unuploaded; final RAG ingestion and live evaluation remain deferred to the final integration phase.
