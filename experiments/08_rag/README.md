# Practical 08: End-to-End Retrieval-Augmented Generation (RAG) Architecture
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Standard LLMs hallucinate plausible-sounding falsehoods, invent non-existent APIs, and fabricate source references when asked technical questions outside their training distribution. Retrieval-Augmented Generation (RAG) mitigates this by restricting the model to factual context retrieved dynamically from approved educational textbooks (e.g., OpenStax).

### Learning Objectives:
1. Implement the complete end-to-end RAG lifecycle:
   $$\text{Raw Documents} \to \text{Overlapping Chunks} \to \text{Embeddings} \to \text{Vector Index} \to \text{Top-}k \text{ Retrieval} \to \text{Grounded Generation}$$
2. Implement citation tagging with exact source anchors (`[S1]`, `[S2]`).
3. Enforce strict abstention behavior (`INSUFFICIENT_EVIDENCE`) when retrieved cosine similarity falls below the relevance threshold.

---

## 2. Pipeline Stages
```
  [Educational Notes]
         │
         ▼
  ┌──────────────┐
  │ 1. Chunking  │  Sliding window (30 words, 10 overlap)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ 2. Embedding │  Vector representation + normalization
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ 3. Indexing  │  Cosine similarity search index
  └──────┬───────┘
         │
  [Query]│
     ▼   ▼
  ┌──────────────┐
  │ 4. Retrieval │  Threshold check: sim > 0.25
  └──────┬───────┘
         ├──────────────────────────────┐
         │ sim >= 0.25                  │ sim < 0.25 (Out of domain)
         ▼                              ▼
  ┌──────────────┐               ┌──────────────┐
  │ 5. Synthesis │               │ 6. Abstain   │
  │  Grounded    │               │ INSUFFICIENT │
  │ [S1], [S2]   │               │   EVIDENCE   │
  └──────────────┘               └──────────────┘
```

---

## 3. How to Run
```bash
python experiments/08_rag/experiment.py
```
Self-contained, pure Python.

---

## 4. Key Results & Observations
- In-domain query: *"What does range(4) produce in a for loop?"*\
  $\to$ Retrieved 2 relevant chunks (`similarity = 0.424, 0.346`).\
  $\to$ Produced grounded explanation citing `[S1]` and `[S2]`.
- Out-of-domain query: *"What is quantum entanglement in physics?"*\
  $\to$ Zero chunks passed the $0.25$ similarity threshold.\
  $\to$ The system cleanly executed the abstention path: `INSUFFICIENT_EVIDENCE`.

---

## 5. Connection to Production EduPath
In production EduPath:
- Ingestion occurs via `services/document_service.py` (PDF, TXT, MD parser).
- Chunking is performed by `services/langchain_document_processing.py` using `RecursiveCharacterTextSplitter`.
- Embeddings use Google Gemini Embedding 2 ($d=768$) stored in Neon PostgreSQL `document_chunks` table with `pgvector`.
- Retrieval runs through `services/langchain_retriever.py` with SQL cosine distance (`<=>`).
- Grounded generation and citation verification run in `services/answer_generation_service.py`.

---

## 6. Interview Preparation Q&A
- **Q: Why is chunk overlap necessary in RAG?**\
  *A:* Chunk overlap prevents semantic boundary truncation: if an important definition or concept is split across the exact boundary between chunk $i$ and chunk $i+1$, isolated chunks may lose grammatical coherence. Overlap ensures critical transition phrases appear intact in at least one chunk.
- **Q: What is the risk of answering when retrieval similarity is low?**\
  *A:* Low similarity indicates that the knowledge base does not cover the query. Forcing the LLM to generate an answer from irrelevant context leads to hallucination, citation mismatch, or misleading advice. A well-engineered RAG pipeline must have an explicit abstention threshold.
