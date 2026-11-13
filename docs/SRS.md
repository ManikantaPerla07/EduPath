# Software Requirements Specification (SRS) — EduPath
**System:** EduPath — Personalized Tutoring Agent\
**Standard:** IEEE 830-1998 Aligned\
**Academic Project:** CSE473 Major Project\
**Author:** Perla Manikanta

---

## 1. Introduction
### 1.1 Purpose
This specification details the complete functional, technical, and interface requirements for the **EduPath Personalized Tutoring Agent**.

### 1.2 Scope
EduPath is a modular Python web application built using Streamlit, LangChain, LangGraph, and Neon PostgreSQL + pgvector, integrated with Google Gemini LLM API.

---

## 2. Overall Description
### 2.1 Product Perspective
EduPath is a self-contained monolith consisting of:
- **Presentation Layer:** Streamlit multi-page reactive UI.
- **Service Layer:** Python modules for grading, progress calculation, curriculum planning, and retrieval.
- **Orchestration Layer:** LangGraph state graph managing conversational turns, tool routing, and PostgreSQL checkpoints.
- **Data Layer:** Neon Serverless PostgreSQL with `pgvector` for 768-dimensional vector embeddings.

### 2.2 User Roles
- **Student / Learner:** Authenticated adult user who interacts with the AI tutor, takes assessments, tracks progress, and follows study plans.
- **Administrator:** Elevated user who manages the knowledge base, uploads textbook PDFs, executes batch embeddings, and audits agent telemetry.

---

## 3. Specific Requirements

### 3.1 Functional Requirements Matrix
| Requirement ID | Module | Description | Inputs | Expected Output | Error Handling |
|---|---|---|---|---|---|
| **REQ-AUTH-01** | Authentication | Validate Google OIDC claims. | `iss`, `sub`, `email`, `iat`, `exp` | Authenticated session row in `users` | Raise `GoogleSessionExpired` or redirect to login. |
| **REQ-AUTH-02** | Onboarding | Record explicit adult age confirmation (18+). | Form submit boolean | `adult_confirmation = True` in DB | Prevent access until confirmed. |
| **REQ-PROF-01** | Learner Profile | Retrieve learner preferences. | `user_id` | Profile dictionary | Raise `ValueError` if user not found. |
| **REQ-PROF-02** | Learner Profile | Update preferences with schema validation. | `proficiency_level`, `daily_minutes`, etc. | Updated profile row | Raise `ValueError` on constraint violation. |
| **REQ-ASSESS-01** | Assessment | Seed & fetch 27 active multiple-choice questions. | `course_slug`, optional `topic_slug` | List of questions without answer keys | Raise `ValueError` if course empty. |
| **REQ-ASSESS-02** | Assessment | Grade student responses server-side. | `assessment_id`, submitted choices map | Graded items, score percent, feedback | Reject tampering; transactional write. |
| **REQ-PROG-01** | Progress | Calculate topic mastery from submitted attempts. | `total_attempts`, `correct_answers` | Accuracy, mastery score, status | Return zero progress on 0 attempts. |
| **REQ-PLAN-01** | Study Plan | Topologically sort topics prioritizing weak areas. | Course topic DAG, learner progress | Scheduled study plan items | Raise `ValueError` on cyclic graph. |
| **REQ-RAG-01** | Retrieval | Semantic similarity search using pgvector. | `query`, `course_slug`, `limit` | Ranked chunk list with similarity scores | Return empty list on low relevance. |
| **REQ-TUTOR-01** | Tutor Agent | Orchestrate grounded conversational turn. | Learner question, chat history | Grounded response with citations `[S1]` | Abstain (`INSUFFICIENT_EVIDENCE`) if ungrounded. |
| **REQ-FEWSHOT-01**| Few-Shot | Inject level-specific exemplars into prompt. | Learner mastery status | Curated few-shot demonstrations | Default to beginner exemplar. |

---

## 4. External Interface Requirements
- **Google OAuth 2.0 / OIDC:** Hosted Streamlit auth endpoint.
- **Google Gemini API:** `gemini-3.8-flash` (primary generation), `gemini-3.5-flash-lite` (fallback), `gemini-embedding-2` (768-dim vectors).
- **Neon PostgreSQL:** Secure SSL connection string over port 5432 using `psycopg` binary.

---

## 5. Security & Safety Constraints
- **SEC-01:** Answer keys and explanations reside exclusively in PostgreSQL; client UI only receives questions and options.
- **SEC-02:** Zero server-side execution of student Python code.
- **SEC-03:** LangGraph checkpoint threads and tools enforce ownership: `user_id` is derived from authenticated session claims, never accepted from user input.
