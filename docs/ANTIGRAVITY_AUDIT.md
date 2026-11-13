# EduPath — Engineering Audit & Verification Report
**Date:** November 14, 2026\
**Project:** EduPath — Personalized Tutoring Agent\
**Academic Context:** CSE473 Major Project (UN SDG 4: Quality Education)\
**Lead Developer:** Perla Manikanta\
**Local Path:** `C:\Users\Mani\EduPath`\
**Current Branch:** `feature/unify-langchain-retrieval`\
**Runtime Environment:** Windows 11, PowerShell, Python 3.11.9, Neon PostgreSQL + pgvector

---

## 1. Executive Summary
This audit provides an authoritative baseline of the EduPath repository as inspected, implemented, polished, and verified in accordance with the Master Execution Specification. EduPath is a production-grade, knowledge-grounded AI tutoring agent for Beginner Python Programming that dynamically adapts to individual student mastery, explains concepts through few-shot exemplars across three difficulty levels (both deterministic offline and live Gemini API generation), evaluates subjective explanations against four-dimensional rubrics, and grounds all factual responses in verified curriculum knowledge-base documents (11 active ready documents, 47 embedded chunks using gemini-embedding-2).

---

## 2. Verified Repository Baseline

| Component | Target / Decision | Status | Verification Evidence |
|---|---|---|---|
| **Python Runtime** | Python 3.11.9 (Validated) | Verified | `.venv\Scripts\python.exe --version` -> `Python 3.11.9` |
| **Frontend Framework** | Streamlit (Python monolith) | Verified | Tested in `app.py`, `ui/` |
| **Relational Database** | Neon PostgreSQL (`neondb`) | Verified | 6 migrations applied in `database/migrations/` |
| **Vector Database** | Neon pgvector (`vector(768)`) | Verified | Verified in `document_chunks` table |
| **LLM Orchestration** | LangChain & LangGraph | Verified | `agents/tutor_graph.py`, `services/answer_generation_service.py` |
| **Grounded Retrieval** | RAG over curriculum chunks (47 embedded chunks) | Verified | 18-query golden benchmark: 100% Hit@5, MRR 0.963 |
| **Automated Test Suite** | Pytest | Verified | **569 passed, 77 subtests passed** (0 failures in 9.31s) |
| **Static Code Quality** | `compileall` & `git diff --check` | Verified | 0 compile errors, 0 whitespace errors |
| **Operating Budget** | ₹0 Target | Verified | Free-tier Gemini Flash + Neon Serverless + Streamlit Cloud |

---

## 3. Detailed Component Audit

### 3.1 Course Structure & Learning Topics (9/9 Covered)
1. Variables and Data Types
2. Operators and Expressions
3. Conditional Statements
4. Loops
5. Functions
6. Lists and Tuples
7. Dictionaries and Sets
8. Strings
9. Basic Problem-Solving

### 3.2 Question Bank & Adaptive Assessments
- **Deterministic Question Bank:** 27 seeded, verified multiple-choice questions (3 per topic: Easy, Medium, Hard).
- **Assessment Modes:**
  1. *Diagnostic Assessment:* Course-wide benchmark across all topics.
  2. *Adaptive Practice:* 5-question dynamic session adapting question selection to student accuracy.
  3. *Targeted Revision:* Prioritizes weaker topics (`accuracy < 50%`) with prerequisite remediation.
- **Grading & Scoring:** Deterministic server-side evaluation (`services/grading_service.py`). Protected answer keys are never sent to the browser.
- **Study Plan Handoff:** Assessment completion screen provides a direct `"Update Study Plan with Results"` handoff button navigating learners to refresh their schedule.

### 3.3 Learner Profile & Preference Management
- **Profile Management:** `services/learner_service.py` functions: `get_learner_profile` and `update_learner_profile` with active user checks (`FOR SHARE`) and parameterized queries.
- **UI Interface:** `ui/learner_profile.py` page accessible from navigation tab.
- **Editable Attributes:** Proficiency level (`beginner`, `intermediate`, `advanced`), explanation style (`simple`, `step_by_step`, `example_first`), daily study minutes (10–180), preferred language, learning goal.

### 3.4 Few-Shot Personalization Across 3 Difficulty Levels
- **Exemplar Engine:** `services/few_shot_prompting_service.py` with version-controlled exemplars.
- **Demonstration:** `demonstrations/few_shot_adaptation_demo.py` supports:
  1. *Offline Mode (Default):* Deterministic curated exemplars for immediate presentation.
  2. *Live Mode (`--live`):* Real Gemini API generation using retrieved curriculum source chunks, few-shot prompt injection, and citation validation (`[S1]`, `[S2]`).
- **Prompt Integration:** Integrated with `services/adaptive_learning_service.py` and `services/answer_generation_service.py`.

### 3.5 Conversational Tutor & Subjective Evaluation
- **Action Chips:** In `ui/tutor.py`, `💡 Get a Hint`, `✍️ Test Understanding`, and `🔍 Explain with Analogy` chips inject tailored scaffolding prompts into the conversation.
- **Subjective Explanation Rubric Module:** Embedded expander in `ui/tutor.py` allows authenticated learners to submit freeform explanations evaluated across:
  - Conceptual Accuracy (40%)
  - Reasoning & Logic (30%)
  - Edge Cases & Gotchas (15%)
  - Clarity of Expression (15%)
  - Automated regex misconception diagnosis (off-by-one in range, mutating lists during loops, `=` vs `==`).
  - Strict security guardrail: Formative practice does not alter authoritative database mastery records.

### 3.6 Academic Experiments (All 10 Practicals Verified)
All 10 practicals located in `experiments/` run cleanly with exit code 0:
1. `01_tokenization_attention`: Token IDs, Q/K/V projections, scaled dot-product attention heatmap.
2. `02_prompt_engineering`: Zero-shot, Few-shot, Structured, and Chain-of-Thought comparison.
3. `03_goal_based_agent`: Deterministic educational grid world agent with BFS path planning.
4. `04_lora_finetuning`: Layer-level NumPy LoRA optimization (50 gradient steps, 92.3% loss drop) + theoretical parameter reduction for 7B models.
5. `05_q_learning`: Tabular Q-learning with potential-based reward shaping ($F = \gamma \Phi(s') - \Phi(s)$).
6. `06_faiss`: Vector search with IndexFlatL2, IndexFlatIP, and automatic NumPy fallback engine.
7. `07_multi_agent`: Collaborative Planner, Reviewer, and Coordinator agents with message passing.
8. `08_rag`: Full RAG pipeline with chunking, cosine search, citations `[S1]`, and abstention.
9. `09_react_agent`: Multi-tool ReAct loop for student diagnostic recommendations.
10. `10_safety_evaluation`: 7-category adversarial safety test harness (100% pass rate).

---

## 4. Verification Checkpoint
- Git Status: On `feature/unify-langchain-retrieval`. No user work discarded.
- Test Suite: **569 passed, 77 subtests passed** in 9.31 seconds.
- Code Compilation: 0 errors across all modules.
- Code Formatting: 0 whitespace errors on `git diff --check`.
- Retrieval Evaluation: 18-query benchmark confirmed at 100% coverage and 0.963 MRR.
- Security Invariants: Multi-tenant isolation verified, no secrets or credentials committed.
