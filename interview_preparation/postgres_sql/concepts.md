# Interview Prep: PostgreSQL, Transactions, and pgvector
**EduPath Technical Component:** Neon Database Schema, Migrations, Vector Distance Queries\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
EduPath relies on Neon PostgreSQL for all relational and semantic vector storage:
- **ACID Transactions:** `with connection.cursor() as cursor` ensures automatic `COMMIT` on success and `ROLLBACK` on exception.
- **FOR UPDATE / FOR SHARE Locks:** Prevents race conditions during concurrent assessment submissions and profile edits.
- **pgvector Cosine Operator (`<=>`):** Computes cosine distance:
  $$\text{Cosine Distance} = 1 - \frac{u \cdot v}{\|u\| \|v\|}$$
  Ordering by `<=>` in ascending order retrieves the closest semantic vectors.

---

## 2. Production Code Reference
- Relational schema: `database/migrations/001_initial_schema.sql`
- Vector schema: `database/migrations/003_document_chunks.sql`
- Vector search query: `services/retrieval_service.py` (lines 140-185)

---

## 3. Simplified 15-Minute SQL Implementation
```sql
-- interview_preparation/postgres_sql/exercises.sql

-- 1. Create pgvector table
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE interview_chunks (
    chunk_id SERIAL PRIMARY KEY,
    topic_name TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768)
);

-- 2. Semantic Search Query (Cosine Distance)
SELECT
    chunk_id,
    topic_name,
    content,
    1 - (embedding <=> %s::vector) AS cosine_similarity
FROM interview_chunks
WHERE topic_name = %s
ORDER BY embedding <=> %s::vector ASC
LIMIT 5;

-- 3. Atomic Progress Update with Upsert (ON CONFLICT)
INSERT INTO learner_topic_progress (user_id, topic_id, total_attempts, correct_answers, accuracy_percent)
VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 5, 4, 80.0)
ON CONFLICT (user_id, topic_id)
DO UPDATE SET
    total_attempts = EXCLUDED.total_attempts,
    correct_answers = EXCLUDED.correct_answers,
    accuracy_percent = EXCLUDED.accuracy_percent,
    updated_at = NOW();
```

---

## 4. Mock Interview Questions
- **Q: What is the difference between `<=>`, `<->`, and `<#>` operators in pgvector?**\
  *A:*\
  - `<=>` is Cosine Distance ($1 - \cos(\theta)$).
  - `<->` is Euclidean ($L_2$) Distance ($\sqrt{\sum (u_i - v_i)^2}$).
  - `<#>` is Negative Inner Product ($- u \cdot v$).
- **Q: Why does EduPath use `ON CONFLICT (user_id, topic_id) DO UPDATE`?**\
  *A:* It provides an atomic upsert (insert or update). Without upsert, checking for an existing row and then performing an insert or update creates a race condition under concurrent requests, risking duplicate key violations or lost updates.
