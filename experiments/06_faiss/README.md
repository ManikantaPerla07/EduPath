# Practical 06: Vector Embeddings and FAISS Similarity Search
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Retrieval-Augmented Generation (RAG) relies on sub-linear vector search to identify curriculum-relevant document excerpts from thousands of candidates. Facebook AI Similarity Search (FAISS) is the industry standard for fast, dense vector indexing and retrieval.

### Learning Objectives:
1. Understand vector distance metrics: Euclidean ($L_2$) distance vs Cosine Inner Product ($IP$).
2. Implement and test `IndexFlatL2` and `IndexFlatIP`.
3. Normalize vectors to prove that Inner Product on unit vectors is mathematically identical to Cosine Similarity:
   $$\langle \hat{u}, \hat{v} \rangle = \frac{u \cdot v}{\|u\| \|v\|} = \cos(\theta)$$
4. Contrast in-memory indexing (FAISS) with relational vector extensions (Neon `pgvector`).

---

## 2. FAISS Index Types
- **IndexFlatL2:** Exact brute-force search over $L_2$ Euclidean distance:
  $$d(q, v) = \sum_{i=1}^d (q_i - v_i)^2$$
- **IndexFlatIP:** Exact brute-force search over Inner Product:
  $$\text{score}(q, v) = \sum_{i=1}^d q_i \cdot v_i$$
  When vectors $q$ and $v$ are $L_2$-normalized ($\|q\|_2 = \|v\|_2 = 1$), the inner product equals cosine similarity.

---

## 3. How to Run
```bash
python experiments/06_faiss/experiment.py
```
- Can run with native `faiss-cpu` / `scikit-learn` if installed.
- Includes a pure-Python/NumPy fallback engine guaranteeing execution in any environment.

---

## 4. Key Results & Observations
- In both $L_2$ and Cosine queries, queries like *"What is a list in Python?"* reliably retrieve the exact definition:\
  *`"A list is an ordered, mutable collection of items in Python."`*
- Normalization ensures scores lie within $[-1.0, 1.0]$, preventing vector length from skewing relevance scores.

---

## 5. Architectural Distinction: FAISS vs Neon pgvector
| Architectural Dimension | FAISS (Academic Experiment) | Neon pgvector (Production EduPath) |
|---|---|---|
| **Storage Medium** | Ephemeral RAM / Disk dump | Persistent ACID relational database |
| **Relational Joins** | No (requires separate metadata store) | Yes (`JOIN topics ON ... JOIN courses ...`) |
| **Row-Level Security** | Custom application logic | Native SQL authorization |
| **Hardware** | Optimized for CPU SIMD / AVX2 / GPUs | Managed cloud PostgreSQL extension |
| **Use Case in EduPath** | Benchmark & offline indexing | Real-time chat & retrieval serving |

---

## 6. Interview Preparation Q&A
- **Q: Why does EduPath use pgvector in production instead of FAISS?**\
  *A:* EduPath requires ACID transactional integrity, multi-tenant learner isolation, and compound queries that filter by `course_slug`, `topic_slug`, and `archived_at IS NULL` simultaneously. In pgvector, vector similarity is evaluated directly inside the SQL query planner alongside relational predicates, eliminating separate vector-to-metadata synchronization pipelines.
- **Q: What is the time complexity of IndexFlatL2 versus an IVF (Inverted File) index?**\
  *A:* `IndexFlatL2` performs exhaustive brute-force search with $O(N \cdot d)$ complexity, guaranteeing 100% recall. An `IndexIVFFlat` clusters vectors into $k$ Voronoi cells, reducing query complexity to $O(\frac{N}{k} \cdot d \cdot \text{nprobe})$ at the cost of approximate recall (ANN).
