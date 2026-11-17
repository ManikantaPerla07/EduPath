# EduPath Pre-Deployment Master Verification Checklist

**Course:** CSE473 — Major Project\
**Initiative:** Google Solution Challenge\
**Sustainable Development Goal:** UN SDG 4 — Quality Education\
**Project Group:** G22 | **Lead Developer:** Perla Manikanta\
**Runtime Environment:** Windows 11, PowerShell, Python 3.11.9, Neon PostgreSQL + pgvector\
**Development Branch:** `feature/unify-langchain-retrieval` (Not yet merged into `main`)\
**Automated Tests:** 615 passed, 77 subtests passed in 7.88s (100% passing, 0 failures)\
**Compilation:** 0 errors across all modules (`python -m compileall -q -x "\.venv" .`)\
**Retrieval Benchmark:** 18 queries, 100% test coverage, Mean Reciprocal Rank (MRR) = 0.963

---

## 1. Deployment Decision: READY FOR MANUAL DEPLOYMENT (NO-GO FOR AUTOMATIC)

In strict accordance with project rules, **automatic public deployment has NOT been initiated**. The application code, services, database migrations, security controls, and documentation are verified and present as modified and untracked files in the working tree on branch `feature/unify-langchain-retrieval` (unstaged; `git diff --cached` is empty) for user review and subsequent manual deployment to Streamlit Community Cloud.

---

## 2. CSE473 Assignment Requirements Matrix

| Requirement | Implementation Component | Evidence / Test Reference | Status |
| :--- | :--- | :--- | :---: |
| **Few-Shot Personalization** | [services/few_shot_prompting_service.py](file:///c:/Users/Mani/EduPath/services/few_shot_prompting_service.py) | `select_personalized_few_shot_exemplars()` incorporates declared proficiency, topic mastery, and active student misconceptions into prompt context. | **COMPLETED** |
| **Controlled Misconception Catalogue** | [services/misconception_service.py](file:///c:/Users/Mani/EduPath/services/misconception_service.py) | 8 stable codes (`off_by_one_range`, `assignment_vs_equality`, `list_mutation_during_iteration`, `return_vs_print`, etc.) with corrective explanations and remedial exemplars. | **COMPLETED** |
| **Connected Feedback Loop** | [ui/tutor.py](file:///c:/Users/Mani/EduPath/ui/tutor.py) & [services/subjective_evaluation_service.py](file:///c:/Users/Mani/EduPath/services/subjective_evaluation_service.py) | Learner submits explanation $\to$ Evaluated against 4-part rubric $\to$ Misconceptions diagnosed and recorded $\to$ Next tutor turn injects targeted remedial demonstration. | **COMPLETED** |
| **Three-Level Demonstration** | [demonstrations/few_shot_adaptation_demo.py](file:///c:/Users/Mani/EduPath/demonstrations/few_shot_adaptation_demo.py) | Generates Beginner, Intermediate, and Advanced responses to the exact same question. Live Gemini mode (`--live`) uses real Neon database retrieval; fails diagnostically if DB is unreachable. | **COMPLETED** |
| **OpenStax Dataset Compliance** | [docs/OPENSTAX_DATASET_AND_PERMISSION.md](file:///c:/Users/Mani/EduPath/docs/OPENSTAX_DATASET_AND_PERMISSION.md) | Audited Rice University OpenStax AI terms; confirmed written permission requirement; drafted permission application; external reading link provided in UI; zero unauthorized text ingested. | **BLOCKED ON PERMISSION** |

---

## 3. Seven Canonical Application Modules

| Module | UI View / Service Reference | Verification Evidence | Status |
| :--- | :--- | :--- | :---: |
| **1. Dashboard** | [app.py](file:///c:/Users/Mani/EduPath/app.py) (`home_screen`) | Displays genuine learner progress, active study plan status, and assessment metrics without fabricated progress. | **COMPLETED** |
| **2. Learner Profile** | [ui/learner_profile.py](file:///c:/Users/Mani/EduPath/ui/learner_profile.py) | Configures proficiency level, learning goal, daily study minutes, preferred language, explanation style, AI consent toggle, and account deletion. | **COMPLETED** |
| **3. AI Tutor** | [ui/tutor.py](file:///c:/Users/Mani/EduPath/ui/tutor.py) & [agents/tutor_graph.py](file:///c:/Users/Mani/EduPath/agents/tutor_graph.py) | Persistent multi-turn conversations via LangGraph, read-only learner tools, grounded RAG citations (`[S1]`), progressive hints, and subjective practice check. | **COMPLETED** |
| **4. Python Assessment** | [ui/assessment.py](file:///c:/Users/Mani/EduPath/ui/assessment.py) & [services/adaptive_assessment_service.py](file:///c:/Users/Mani/EduPath/services/adaptive_assessment_service.py) | 9-topic diagnostic and adaptive practice quizzes, server-side grading, evidence damping factor, and authoritative mastery calculations. | **COMPLETED** |
| **5. Personalized Study Plan** | [ui/study_plan.py](file:///c:/Users/Mani/EduPath/ui/study_plan.py) & [services/study_plan_service.py](file:///c:/Users/Mani/EduPath/services/study_plan_service.py) | Topologically ordered topic sequence respecting prerequisites, prioritizing weak areas, with user-confirmed refresh capability. | **COMPLETED** |
| **6. Learning Analytics** | [ui/learning_analytics.py](file:///c:/Users/Mani/EduPath/ui/learning_analytics.py) | Dedicated learner analytics showing actual quiz history, topic mastery matrix, formative misconception log, and tutor feedback history. | **COMPLETED** |
| **7. Learning Resources** | [ui/learning_resources.py](file:///c:/Users/Mani/EduPath/ui/learning_resources.py) | Displays 11 approved and published course documents with licensing/rights metadata, plus external OpenStax textbook reference link. | **COMPLETED** |

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
7. **Secrets Hygiene:** `.env` and `.streamlit/secrets.toml` are excluded in `.gitignore`. Verified: 0 API keys or database URLs tracked or staged in Git. Template maintained in [.streamlit/secrets.toml.example](file:///c:/Users/Mani/EduPath/.streamlit/secrets.toml.example).
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
> In accordance with project rules, migration `007` has **NOT been automatically executed against the production Neon database**. It is saved in [database/migrations/007_learner_profile_and_misconceptions.sql](file:///c:/Users/Mani/EduPath/database/migrations/007_learner_profile_and_misconceptions.sql) for user review and manual execution.

---

## 7. Exact Remaining Manual Actions for Deployment

When ready to deploy publicly to Streamlit Community Cloud:
1. **Review Working Tree & Stage Changes:** Inspect `git status`, stage the verified modified and untracked files (`git add ...`), and verify `git diff --cached` on branch `feature/unify-langchain-retrieval`.
2. **Commit Changes:** `git commit -m "Complete all EduPath assignment requirements and pre-deployment deliverables"`
3. **Run Forward Migration (Required for Generative AI Features):** Migration `007` is a required pre-deployment database step for enabling the Gemini-powered AI Tutor, as persistent affirmative AI consent and formative misconception tracking depend on its schema. If migration `007` is not applied, EduPath operates safely in non-AI mode. Execute migration `007` against Neon using `python database/run_migrations.py`.
4. **Deploy on Streamlit Community Cloud:**
   - Repository: `ManikantaPerla07/EduPath`
   - Branch: `feature/unify-langchain-retrieval`
   - Main file path: `app.py`
   - Paste environment secrets (`DATABASE_URL`, `GEMINI_API_KEY`, Google OAuth client secrets) into the Streamlit Cloud Secrets dashboard using [.streamlit/secrets.toml.example](file:///c:/Users/Mani/EduPath/.streamlit/secrets.toml.example) as the template.
