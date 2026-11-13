# Product Requirements Document (PRD) — EduPath
**Document Version:** 1.0\
**Project:** EduPath — Personalized Tutoring Agent\
**Initiative:** UN SDG 4 — Quality Education\
**Academic Course:** CSE473 Major Project\
**Author:** Perla Manikanta (Group G22)

---

## 1. Executive Summary
Conventional computer science education tools frequently provide uniform, static content that fails to accommodate learners with varying levels of preparation. Underprepared learners face cognitive overload when explanations assume implicit prerequisites, while advanced learners face disengagement from repetitive explanations. **EduPath** addresses this challenge through an intelligent, knowledge-grounded tutoring agent for Beginner Python Programming that continuously evaluates learner mastery, tailors explanation depth using few-shot exemplars across three difficulty levels, and grounds all technical instruction in verified, authoritative curriculum resources with source citations.

---

## 2. Problem Statement
The official allocation assignment defines the problem statement:
> *"Underserved schools lack access to personalized tutoring. Build a tutor that adapts its explanation style using a few examples of a student's level/mistakes (few-shot), and show it adjusts across 2–3 difficulty levels."*

Students struggle with:
1. Identifying conceptual misconceptions (e.g., 0-indexing vs cardinality, assignment vs equality).
2. Receiving feedback calibrated to their specific level of proficiency.
3. Structuring sequential study plans that prioritize prerequisite knowledge gaps.

---

## 3. Product Vision & Target Audience
- **Product Vision:** A free, accessible, and grounded AI learning companion that functions as a personal teacher rather than a general-purpose chat interface.
- **Target Audience:** College-level adult learners (18+) studying beginner computer science and Python programming.
- **Operating Constraint:** Zero-cost architecture (₹0 budget target) leveraging free-tier cloud resources.

---

## 4. Key Personas
1. **Struggling Learner:** Needs foundational revision, intuitive analogies, small step-by-step code snippets, and reassurance.
2. **Independent / Developing Learner:** Understands core syntax, needs worked examples, step-by-step logic tracing, and common gotchas.
3. **Advanced Learner:** Grasps concepts rapidly, benefits from underlying system mechanics (iterator protocols, memory models), and challenging edge-case problems.

---

## 5. Functional Requirements (Scope V1)
- **FR-01 (Authentication & Onboarding):** Google OIDC authentication via Streamlit, adult confirmation check, and persistent profile creation.
- **FR-02 (Learner Profile Management):** User-configurable proficiency level, explanation style, daily study availability, preferred language, and learning goals.
- **FR-03 (Diagnostic & Adaptive Assessment):**
  - Diagnostic mode covering all 9 Python topics.
  - Adaptive practice mode selecting 5 questions based on learner history.
  - Targeted revision mode focusing on topics with $<50\%$ accuracy.
- **FR-04 (Evidence-Based Progress Tracking):** Real-time aggregation of attempts, accuracy, and mastery scores; automatic classification into *not_assessed*, *needs_revision*, *developing*, or *candidate_for_mastery*.
- **FR-05 (Personalized Study Planning):** Topological prerequisite scheduling prioritizing weak topics and goal keywords.
- **FR-06 (AI Tutor with Few-Shot Adaptation):**
  - Retrieval-Augmented Generation grounded in verified course knowledge-base chunks.
  - Dynamic few-shot exemplars adjusting explanations across Beginner, Intermediate, and Advanced tiers.
  - Strict citation enforcement (`[S1]`, `[S2]`).
  - Automatic abstention (`INSUFFICIENT_EVIDENCE`) when queries fall outside curriculum evidence.
- **FR-07 (Learner Data Tools):** LangGraph tool-calling nodes allowing the tutor to securely inspect the learner's own scores and study activities.
- **FR-08 (Administrator Knowledge Management):** Upload, process, chunk, embed, archive, and publish curriculum documents and textbooks.

---

## 6. Non-Functional Requirements
- **NFR-01 (Operating Budget):** ₹0 hosting target. No paid tier upgrades or automatic billing.
- **NFR-02 (Security & Isolation):** Strict multi-tenant data boundaries. No student Python code execution on the server.
- **NFR-03 (Reliability):** Transient error handling with automatic fallback model (`gemini-3.8-flash` $\to$ `gemini-3.5-flash-lite`).
- **NFR-04 (Traceability):** Every factual statement must cite an approved course excerpt.

---

## 7. Future Scope (Post-V1)
- Multi-course expansion (Data Structures, Web Development).
- Voice-enabled tutoring dialogue.
- Collaborative peer study rooms.
