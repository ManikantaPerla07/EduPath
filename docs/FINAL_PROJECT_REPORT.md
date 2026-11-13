# Final Major Project Report — EduPath: Personalized Tutoring Agent
**Course:** CSE473 — Major Project\
**Initiative:** Google Solution Challenge\
**Sustainable Development Goal:** UN SDG 4 — Quality Education\
**Project Group:** G22\
**Lead Developer:** Perla Manikanta\
**Institution:** Academic Evaluation Submission

---

## 1. Abstract
The democratization of quality education requires instructional systems capable of addressing the heterogeneous needs of individual students. Conventional digital learning platforms present uniform curricula, leading to high dropout rates and persistent learning gaps. This project presents **EduPath**, an intelligent tutoring system for Beginner Python Programming that combines stateful agent orchestration (LangGraph), semantic vector retrieval (`pgvector` over 11 verified curriculum documents with 47 chunks embedded via `gemini-embedding-2`), deterministic prerequisite planning, and in-context few-shot demonstration learning. EduPath continuously models learner understanding from assessment evidence, dynamically calibrates explanation depth across three proficiency tiers, and enforces strict factual grounding with source-attributed citations. Operating under a strict ₹0 budget target on serverless cloud infrastructure, EduPath demonstrates how personalized tutoring can be deployed sustainably to underserved learners worldwide.

---

## 2. Problem Statement & Motivation
Underserved schools lack access to personalized tutoring. In typical classrooms, student-to-teacher ratios exceed 40:1, making individualized instruction impractical. Commercial AI chatbots fail as educational companions because they act as general question-answering machines: they do not model prerequisite knowledge, they frequently hallucinate incorrect programming syntax, and they provide identical answers regardless of whether the learner is a complete novice or an advanced student.

EduPath addresses this gap by creating a closed-loop pedagogical cycle:
$$\text{Assess} \to \text{Diagnose} \to \text{Plan} \to \text{Teach (Few-Shot)} \to \text{Evaluate} \to \text{Adapt}$$

---

## 3. System Architecture & Key Innovations

1. **Modular Python Monolith:** Built using Streamlit, eliminating dual-language frontend/backend overhead and maintaining rapid reactivity.
2. **Deterministic-Probabilistic Hybrid Architecture:**
   - *Deterministic Layer (Python & PostgreSQL):* Authoritative grading, prerequisite topological sorting, mastery score calculations, and database access authorization.
   - *Probabilistic Layer (LangChain & Gemini):* Natural language explanation generation, conversational empathy, and few-shot pedagogical adaptation.
3. **Few-Shot In-Context Adaptation:** Curated exemplars demonstrating level-specific tone, misconception addressing, and progressive practice challenges across Beginner, Intermediate, and Advanced tiers. Verifiable both offline (deterministic) and live via Gemini API.
4. **Knowledge-Grounded RAG:** 768-dimensional vector search using Neon `pgvector 0.8.6` over 47 chunked curriculum documents embedded with `gemini-embedding-2`, enforcing automated citation verification (`[S1]`, `[S2]`) and out-of-domain abstention (`INSUFFICIENT_EVIDENCE`).
5. **Conversational Scaffolding & Action Chips:** Built-in interactive guidance chips (`💡 Get a Hint`, `✍️ Test Understanding`, `🔍 Explain with Analogy`) and an integrated four-dimensional rubric self-assessment module for subjective conceptual explanations.
6. **Stateful LangGraph Checkpointing:** Persistent session checkpoints stored in PostgreSQL, allowing multi-turn conversations to survive application restarts.

---

## 4. Academic Practicals & Rigorous Engineering Distinctions

All 10 academic practicals have been implemented and verified in `experiments/`. To maintain academic rigor and transparency, the following technical distinctions are explicitly documented:

| Practical Concept | Academic Experiment Implementation | Production EduPath Implementation |
|---|---|---|
| **LoRA Fine-Tuning (EXP-04)** | Layer-level NumPy gradient descent optimization on $W_0 + \frac{\alpha}{r}(B \cdot A)$ with $92.3\%$ loss drop and theoretical parameter derivation for 7B models. *No full 7B model is trained on GPU.* | In-context few-shot prompting via Gemini 2.5/3.5, avoiding heavy GPU hosting costs while achieving level-adapted explanations. |
| **Vector Similarity (EXP-06)** | Standalone simulation with automatic NumPy fallback (`IndexFlatL2`, `IndexFlatIP`) over 28 sentences to ensure zero-cost Windows compatibility. | Persistent **Neon PostgreSQL with `pgvector 0.8.6`** executing cosine distance queries (`<=>`) over 768-dim embeddings (`gemini-embedding-2`) with ACID relational filtering. |
| **RAG Pipeline (EXP-08)** | In-memory lexical TF-IDF bag-of-words retrieval over 7 OpenStax loop chunks with citation tagging and similarity thresholding. | Dense neural embedding retrieval using Google `gemini-embedding-2` (768 dimensions) across 47 chunks of original EduPath educational notes in Neon PostgreSQL. |
| **ReAct Agent (EXP-09)** | Deterministic programmatic trace of the `Thought -> Action -> Observation` cycle executing sandboxed Python functions. | Stateful LangGraph workflow with typed graph state, database checkpointing, and deterministic guardrails. |
| **Safety Evaluation (EXP-10)** | 7 test cases evaluating prompt injection, hallucinated citation rejection (`[S99]`), cross-user data isolation, and code execution prevention. | Comprehensive server-side validation, parameterized SQL queries (`psycopg`), and untrusted data demarcation in prompts. |

---

## 5. Production Knowledge-Base Inventory (Audited)

A direct read-only SQL audit of the configured Neon PostgreSQL development database confirms:
- **Active Ready Documents:** 11 documents covering all 9 course topics.
- **Total Ready Chunks:** 47 chunks.
- **Total Embedded Chunks:** 47 chunks (100% embedded).
- **Active Embedding Model:** `gemini-embedding-2` (768 dimensions).
- **Rights & Licensing:** All 11 documents are original educational notes authored for the EduPath project (`rights_basis = 'original'`). OpenStax serves as an external academic reference source and for standalone experiment excerpts, but was not bulk-ingested into production tables.

---

## 6. Experimental Results & Verification Summary

- **Software Suite:** 569 automated tests passed, 77 subtests passed (0 failures) in under 10 seconds.
- **RAG Retrieval Quality:** 100% retrieval coverage on 18-query golden benchmark, Mean Reciprocal Rank (MRR) of 0.963, 94.4% Hit@1, and 100% Hit@5 across all 9 course topics.
- **Academic Practicals:** Completed all 10 CSE473 practical deliverables with zero external GPU requirements.
- **Few-Shot Demonstration:** Successfully verified in both deterministic offline mode and live Gemini API generation (`--live`) with verified source citations.
- **Subjective Rubric Evaluation:** Formative evaluation across Conceptual Accuracy (40%), Reasoning & Logic (30%), Edge Cases (15%), and Clarity (15%), complete with automated misconception alerts and server authorization.

---

## 7. Conclusion & Future Work

EduPath proves that personalized, adaptive, and trustworthy AI tutoring can be realized on a ₹0 budget without compromising pedagogical rigor or security. Future enhancements will extend the curriculum DAG to Data Structures and Algorithms and conduct formal empirical learning-gain pilots with consenting adult cohorts.
