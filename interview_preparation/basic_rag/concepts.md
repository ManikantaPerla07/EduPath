# Interview Prep: Retrieval-Augmented Generation (RAG)
**EduPath Technical Component:** Curriculum Knowledge-Base Ingestion (11 original resources, 47 embedded chunks), pgvector Semantic Search, Citation Guardrails\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
RAG connects non-parametric document memory with parametric LLM reasoning:
1. **Extraction & Chunking:** Ingest curriculum documents and notes $\to$ Split into semantic chunks with sliding-window overlap.
2. **Indexing:** Store 768-dim embeddings in `document_chunks`.
3. **Retrieval:** Fetch Top-$K$ chunks based on cosine distance.
4. **Prompt Assembly:** Tag chunks with source anchors `[S1]`, `[S2]`.
5. **Grounded Generation & Citation Verification:** Synthesize answer citing `[S1]` and verify no unknown citation IDs exist.

---

## 2. Production Code Reference
- Chunking: `services/langchain_document_processing.py`
- LangChain Retriever: `services/langchain_retriever.py`
- Grounded Prompting & Citation Regex: `services/answer_generation_service.py`

---

## 3. Simplified 15-Minute RAG Implementation
```python
# interview_preparation/basic_rag/simple_rag.py
import re

CORPUS = [
    {"id": "S1", "text": "In Python, range(start, stop) generates numbers up to but excluding stop."},
    {"id": "S2", "text": "Variables in Python do not require explicit type declaration."},
]

def retrieve(query: str) -> list[dict]:
    # Simple word overlap retrieval
    q_words = set(query.lower().split())
    matches = []
    for doc in CORPUS:
        doc_words = set(doc["text"].lower().split())
        score = len(q_words & doc_words)
        if score > 0:
            matches.append((doc, score))
    matches.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matches[:2]]

def generate_grounded_answer(query: str, sources: list[dict]) -> str:
    if not sources:
        return "INSUFFICIENT_EVIDENCE"
    context = " ".join(f"[{s['id']}] {s['text']}" for s in sources)
    # Simulated model response
    if "range" in query:
        return "Python loops use range to generate numbers up to the stop boundary [S1]."
    return f"Grounded response based on {sources[0]['id']}."

def verify_citations(answer: str, allowed_ids: set[str]) -> bool:
    cited = set(re.findall(r'\[S(\d+)\]', answer))
    allowed_numbers = {s.replace("S", "") for s in allowed_ids}
    return cited.issubset(allowed_numbers)

if __name__ == "__main__":
    q = "How does range work in Python?"
    docs = retrieve(q)
    ans = generate_grounded_answer(q, docs)
    is_valid = verify_citations(ans, {d["id"] for d in docs})
    print("Answer:", ans)
    print("Citations Validated:", is_valid)
    assert is_valid is True
    print("✅ Basic RAG test passed.")
```

---

## 4. Mock Interview Questions
- **Q: How does EduPath handle queries where no textbook excerpt contains the answer?**\
  *A:* When retrieved cosine similarity falls below the relevance threshold (or zero chunks are returned), EduPath bypasses model generation and returns `INSUFFICIENT_EVIDENCE`. This prevents hallucinations on out-of-curriculum questions.
- **Q: What is the purpose of the `rights_basis` metadata field in the `documents` table?**\
  *A:* EduPath records intellectual property metadata (`rights_basis = 'original'`, `source_license = 'Original — EduPath project'`) for all 11 production documents, and supports open educational licenses (`open_license`, `Creative Commons`) for external academic reference materials to guarantee intellectual property and fair educational reuse standards.
