# EduPath Deployment & Release Verification

**Course:** CSE473 — Major Project\
**Initiative:** Google Solution Challenge\
**Sustainable Development Goal:** UN SDG 4 — Quality Education\
**Project Group:** G22 | **Lead Developer:** Perla Manikanta\
**Runtime Environment:** Windows 11, PowerShell, Python 3.11.9, Neon PostgreSQL + pgvector\
**Deployed implementation branch:** `feature/unify-langchain-retrieval` (the default `main` branch remains a separate, older snapshot)\
**Automated Tests:** 639 tests passed, 0 failures (local regression run, November 18, 2026)\
**Compilation:** 0 errors across all modules (`python -m compileall -q -x "\.venv" .`)\
**Retrieval Benchmark:** 18 queries, 100% test coverage, Mean Reciprocal Rank (MRR) = 0.963

---

## 1. Deployment Status: LIVE — USER-CONFIRMED

The application is deployed on **Streamlit Community Cloud** from the `feature/unify-langchain-retrieval` branch and the user confirmed that the hosted application opens and works.

- **Live URL:** https://edupath-perla-demo.streamlit.app/
- **Repository:** https://github.com/ManikantaPerla07/EduPath
- **Deployed branch:** `feature/unify-langchain-retrieval`
- **Entrypoint:** `app.py`
- **Database:** Neon PostgreSQL (`neondb`); migrations `001`–`007` applied and schema verified.
- **Secrets:** configured in Streamlit Community Cloud; no populated secrets file is stored in Git.

The default GitHub branch `main` has a polished repository landing-page README, but it has **not** been merged with the deployed implementation branch. The live application and detailed implementation documentation are maintained on `feature/unify-langchain-retrieval`.

This checklist records the deployed release state. A successful hosted deployment does not guarantee continuous availability: database sleep/wake, hosting availability, and free-tier AI provider quotas can affect individual requests.

---

## 2. CSE473 Assignment Requirements Matrix

| Requirement | Implementation Component | Evidence / Test Reference | Status |
| :--- | :--- | :--- | :---: |
| **Few-Shot Personalization** | [services/few_shot_prompting_service.py](../services/few_shot_prompting_service.py) | `select_personalized_few_shot_exemplars()` incorporates declared proficiency, topic mastery, and active student misconceptions into prompt context. | **COMPLETED** |
| **Controlled Misconception Catalogue** | [services/misconception_service.py](../services/misconception_service.py) | 8 stable codes (`off_by_one_range`, `assignment_vs_equality`, `list_mutation_during_iteration`, `return_vs_print`, etc.) with corrective explanations and remedial exemplars. | **COMPLETED** |
| **Connected Feedback Loop** | [ui/tutor.py](../ui/tutor.py) & [services/subjective_evaluation_service.py](../services/subjective_evaluation_service.py) | Learner submits explanation $\to$ Evaluated against 4-part rubric $\to$ Misconceptions diagnosed and recorded $\to$ Next tutor turn injects targeted remedial demonstration. | **COMPLETED** |
| **Three-Level Demonstration** | [demonstrations/few_shot_adaptation_demo.py](../demonstrations/few_shot_adaptation_demo.py) | Generates Beginner, Intermediate, and Advanced responses to the exact same question. Live Gemini mode (`--live`) uses real Neon database retrieval; fails diagnostically if DB is unreachable. | **COMPLETED** |
| **OpenStax Dataset Compliance** | [docs/OPENSTAX_DATASET_AND_PERMISSION.md](../docs/OPENSTAX_DATASET_AND_PERMISSION.md) | Audited Rice University OpenStax AI terms; confirmed written permission requirement; drafted permission application; external reading link provided in UI; zero unauthorized text ingested. | **BLOCKED ON PERMISSION** |

---

## 3. Seven Canonical Application Modules

| Module | UI View / Service Reference | Verification Evidence | Status |
| :--- | :--- | :--- | :---: |
| **1. Dashboard** | [app.py](../app.py) (`home_screen`) | Displays genuine learner progress, active study plan status, and assessment metrics without fabricated progress. | **COMPLETED** |
| **2. Learner Profile** | [ui/learner_profile.py](../ui/learner_profile.py) | Configures proficiency level, learning goal, daily study minutes, preferred language, explanation style, AI consent toggle, and account deletion. | **COMPLETED** |
| **3. AI Tutor** | [ui/tutor.py](../ui/tutor.py) & [agents/tutor_graph.py](../agents/tutor_graph.py) | Persistent multi-turn conversations via LangGraph, read-only learner tools, grounded RAG citations (`[S1]`), progressive hints, and subjective practice check. | **COMPLETED** |
| **4. Python Assessment** | [ui/assessment.py](../ui/assessment.py) & [services/adaptive_assessment_service.py](../services/adaptive_assessment_service.py) | 9-topic diagnostic and adaptive practice quizzes, server-side grading, evidence damping factor, and authoritative mastery calculations. | **COMPLETED** |
| **5. Personalized Study Plan** | [ui/study_plan.py](../ui/study_plan.py) & [services/study_plan_service.py](../services/study_plan_service.py) | Topologically ordered topic sequence respecting prerequisites, prioritizing weak areas, with user-confirmed refresh capability. | **COMPLETED** |
| **6. Learning Analytics** | [ui/learning_analytics.py](../ui/learning_analytics.py) | Dedicated learner analytics showing actual quiz history, topic mastery matrix, formative misconception log, and tutor feedback history. | **COMPLETED** |
| **7. Learning Resources** | [ui/learning_resources.py](../ui/learning_resources.py) | Displays 11 approved and published course documents with licensing/rights metadata, plus external OpenStax textbook reference link. | **COMPLETED** |

---

## 4. Ten Academic Experiments (EXP-01 through EXP-10)

All 10 experiments execute with exit code 0 using standalone Python/NumPy engines:

| Experiment | Title | Core Computation | Execution Result |
| :---: | :--- | :--- | :---: |
| **EXP-01** | Tokenization & Attention | Scaled dot-product attention: $\text{softmax}(QK^T/\sqrt{d_k})V$ | **PASS** |
| **EXP-02** | Prompt Engineering | Zero-Shot vs Few-Shot vs Structured vs CoT (with optional `--live` Gemini mode) | **PASS** |
| **EXP-03** | Goal-Based Agent | BFS state-space search over prerequisite DAG finding shortest path | **PASS** |
| **EXP-04** | LoRA Fine-Tuning | Low-Rank Adaptation: $W = W_0 + \frac{\alpha}{r}BA$ (honest NumPy layer adapter) | **PASS** |
| **EXP-05** | Q-Learning Curriculum | Tabular $\epsilon$-greedy reinforcement learning with potential-based reward shaping | **PASS** |
| **EXP-06** | FAISS Vector Search | Native FAISS (`IndexFlatIP`, `IndexFlatL2`) with documented Windows NumPy fallback | **PASS** |
| **EXP-07** | Multi-Agent Orchestration | Message-passing between Planner, Critic, and Tutor role-specialized agents | **PASS** |
| **EXP-08** | Grounded RAG Architecture | Lexical TF-IDF baseline over illustrative synthetic notes vs dense production RAG | **PASS** |
| **EXP-09** | ReAct Agent | Thought-Action-Observation loop with sandboxed read-only tools and loop limits | **PASS** |
| **EXP-10** | Safety Evaluation | 12 adversarial test cases (injection, jailbreak, exfiltration, RCE prohibition) | **PASS (12/12, 100%)** |

---

## 5. Security, Privacy & Guardrails Audit

1. **Zero Student Code Execution:** Absolute prohibition on executing student Python code on the server (`eval`, `exec`, or subprocesses). Conceptual verification handled exclusively via deterministic multiple-choice keys and structured text rubrics.
2. **PII Protection & Gemini Minimization:** Student email addresses, real names, OAuth tokens, and database credentials are **never transmitted** to Google Gemini. Read-only learner tools return only scores and activity schedules.
3. **AI Consent Notice & Default:** Generative AI consent strictly defaults to `FALSE` (no silent opt-in). Learners must affirmatively opt in. First-use consent card in AI Tutor and Learner Profile explains what is sent to Google Gemini (minimal programming questions and curriculum excerpts only; zero PII). When consent is declined, all non-AI features (Dashboard, Assessments, Learning Analytics, Learning Resources) remain accessible.
4. **Application-Level Authorization:** Access control is enforced at the application/service layer via authenticated server-side `user_id` validation. PostgreSQL Row-Level Security (RLS) policies are not configured on Neon; EduPath relies on strict server-side parameterized session scoping.
5. **Account Deletion Completeness:** Comprehensive `delete_learner_account()` sequence locks user row, discovers all owned `thread_id`s, cleans up LangGraph thread checkpoints and writes via `delete_langgraph_thread_checkpoints`, removes user telemetry and misconceptions, and cascades user record deletion. If checkpoint cleanup fails, transaction aborts without falsely reporting success.
6. **Adult Self-Confirmation:** `adult_confirmation` preserved from `001_initial_schema.sql` (default FALSE). Clarified as self-declaration required before accessing curriculum; does not represent independent identity verification.
7. **Secrets Hygiene:** `.env` and `.streamlit/secrets.toml` are excluded in `.gitignore`. Verified: 0 API keys or database URLs tracked or staged in Git. Template maintained in [.streamlit/secrets.toml.example](../.streamlit/secrets.toml.example).
8. **Budget Target & Quotas:** Operating budget target remains ₹0 by operating within model-specific free-tier quotas (monitoring RPM, TPM, and RPD in the Google AI Studio / Google Cloud Console dashboard) and Groq free-tier limits. Multi-provider failover provides redundancy during transient outages but does not guarantee uninterrupted availability if both providers exhaust free-tier quotas simultaneously. Neon serverless operates under its free tier with automatic idle sleep.

---

## 6. Forward-Only Database Migrations

- `001_initial_schema.sql`: Core relational tables and pgvector extension.
- `002_question_bank_key.sql`: Unique constraints on question bank items.
- `003_document_chunks.sql`: Vector chunking and embedding tables.
- `004_document_archival.sql`: Soft archival timestamp support.
- `005_chat_message_feedback.sql`: Learner rating and feedback table.
- `006_chat_and_tutor_run_indexes.sql`: Performance indexes on chat messages and agent runs.
- `007_learner_profile_and_misconceptions.sql`: `learning_goal`, `onboarding_completed`, `ai_consent` columns and `learner_misconceptions` table.

> [!NOTE]
> Migration `007_learner_profile_and_misconceptions` **has been applied to the production Neon database**. The migration runner reported successful application and schema verification; the recorded database checksum was subsequently confirmed to match the local migration file. Do not rerun it manually or alter the migration record.

---

## 7. Post-Deployment Operational Checks

The following checks are useful after a code change, provider configuration change, or hosted incident:

1. **Confirm the deployed revision:** Streamlit Community Cloud should be connected to `feature/unify-langchain-retrieval` with `app.py` as its entrypoint.
2. **Check secrets without exposing them:** verify that `DATABASE_URL`, `GEMINI_API_KEY`, `GROQ_API_KEY` (if used), and the `[auth]` configuration are present in Streamlit Cloud Secrets. Never paste values into issues, README files, logs, or screenshots.
3. **Verify Google OAuth:** the configured redirect URI must match `https://edupath-perla-demo.streamlit.app/oauth2callback` and the authorized redirect URI in Google Cloud Console.
4. **Smoke-test the live app:** sign in, open the dashboard, confirm learner profile and consent state, test assessment and study-plan pages, then send a simple AI Tutor question only for an account that has affirmatively granted AI consent.
5. **Check persistence:** confirm that a new conversation survives refresh and that the latest messages/checkpoints are stored.
6. **Monitor provider quotas:** Gemini and Groq have separate limits and terms. Failover does not guarantee availability if both providers are unavailable or have exhausted quotas.
7. **Protect production data:** do not run seed scripts, destructive migration rollbacks, or test fixtures against the live database. Use a separate development database for schema and data tests.
