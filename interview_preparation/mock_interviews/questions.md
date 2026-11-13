# Comprehensive Mock Interview Q&A — EduPath Major Project
**Course:** CSE473 Major Project\
**Author:** Perla Manikanta

---

### Category 1: System Architecture & Technologies
1. **Q: Walk me through the high-level architecture of EduPath.**\
   *A:* EduPath is a modular Python monolith built with Streamlit for reactive frontend UI, Python service modules for business logic, LangChain and LangGraph for agent orchestration, and Neon Serverless PostgreSQL with pgvector for relational data and 768-dimensional vector storage. Calls to Google Gemini provide language generation and embeddings under a ₹0 operating target.

2. **Q: Why was Streamlit chosen over React + FastAPI?**\
   *A:* Streamlit provides single-language Python reactivity, native session state management, built-in Google OIDC support, and free zero-configuration hosting on Streamlit Community Cloud. For an educational AI companion, eliminating cross-language serialization and dual deployment overhead permitted maximum focus on AI grounding and pedagogical adaptation.

3. **Q: How does EduPath maintain a ₹0 budget?**\
   *A:* By utilizing Google Gemini's free-tier API quotas (15 RPM / 1,500 RPD), Neon's free serverless PostgreSQL tier with automatic idle sleep, and Streamlit Community Cloud free hosting. All experimental ML packages (torch, faiss) are isolated from production requirements.

---

### Category 2: Agent Orchestration & LangGraph
4. **Q: What is the role of LangGraph in EduPath?**\
   *A:* LangGraph coordinates the multi-step tutoring workflow as a directed `StateGraph`. It manages state transitions between input validation, context resolution, tool routing, vector retrieval, few-shot teaching guidance, and response generation, while persisting thread checkpoints to PostgreSQL.

5. **Q: How does the agent decide when to call a tool versus searching the curriculum?**\
   *A:* In `agents/tutor_graph.py`, the `decide_learner_tools` node presents Gemini with read-only tools (`get_my_learning_progress`, `get_my_study_plan`). If the student asks about personal scores or schedules, the model emits a tool call. If they ask a Python concept question, it routes directly to RAG retrieval over course curriculum chunks.

6. **Q: How does EduPath prevent unauthorized access in agent tools?**\
   *A:* Tools read the learner's `user_id` strictly from server-controlled graph state (`runtime.state["user_id"]`), which originates from verified Google OIDC session claims. The LLM is never given a parameter to specify or forge a user ID.

---

### Category 3: RAG & Vector Search
7. **Q: How does EduPath implement Grounded RAG?**\
   *A:* Course documents are split into overlapping chunks and embedded into 768-dimensional vectors using Gemini Embedding 2. Chunks are stored in the `document_chunks` table in Neon PostgreSQL. During queries, pgvector executes cosine distance search (`<=>`). Retrieved chunks are tagged `[S1]`, `[S2]` and provided to the model under strict instructions prohibiting external facts.

8. **Q: How does EduPath verify source citations?**\
   *A:* `services/answer_generation_service.py` extracts citations via regular expressions and verifies each against an allowlist of chunk IDs supplied for that turn. If the model invents a citation (e.g. `[S99]`), the guardrail drops the response and returns `INSUFFICIENT_EVIDENCE`.

9. **Q: What were the results of the 18-query retrieval benchmark?**\
   *A:* EduPath achieved 100% retrieval coverage, a Mean Reciprocal Rank (MRR) of 0.963, 94.4% Hit@1, and 100% Hit@5 across all 9 Python course topics.

---

### Category 4: Personalization & Pedagogical Adaptation
10. **Q: How does EduPath fulfill the assignment's few-shot personalization requirement?**\
    *A:* `services/few_shot_prompting_service.py` maintains curated exemplars across Beginner, Intermediate, and Advanced tiers. When a student's mastery record indicates revision or novice status, beginner exemplars (with analogies, gentle pace, and short code) are injected into the prompt. For developing or advanced students, intermediate or advanced exemplars (with execution traces, gotchas, or iterator mechanics) are injected.

11. **Q: How does EduPath generate personalized study plans?**\
    *A:* `services/study_plan_service.py` performs a topological sort over the topic prerequisite DAG in PostgreSQL. Topics where the student scored $<50\%$ are prioritized for revision before dependent topics, and daily study minutes are calibrated to the learner's profile.

---

### Category 5: AI Safety & System Reliability
12. **Q: How does EduPath prevent Remote Code Execution (RCE)?**\
    *A:* The application never executes student-generated Python code on the server (`eval()` and `exec()` are strictly banned). All coding exercises are evaluated via conceptual multiple-choice items and deterministic server-side option keys.

13. **Q: How does EduPath handle Google Gemini API rate limits?**\
    *A:* `services/answer_generation_service.py` catches retryable 429 status codes and automatically falls back from the primary model (`gemini-3.8-flash`) to the lightweight fallback model (`gemini-3.5-flash-lite`).
