# Interview Prep: Embeddings & Vector Similarity
**EduPath Technical Component:** Gemini Embedding 2, 768-dim Vectors, Cosine Math\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
Text embeddings map variable-length strings to dense numerical vectors in $\mathbb{R}^d$ such that semantically related concepts reside near each other in latent space.
- **Model:** Google Gemini Embedding 2 (`gemini-embedding-2`).
- **Dimension:** $d = 768$.
- **Distance Formula:**
  $$\text{Cosine Similarity}(u, v) = \frac{\sum_{i=1}^d u_i v_i}{\sqrt{\sum_{i=1}^d u_i^2} \cdot \sqrt{\sum_{i=1}^d v_i^2}}$$

---

## 2. Simplified 15-Minute Implementation
```python
# interview_preparation/embeddings/simple_demo.py
import math

def dot_product(v1: list[float], v2: list[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))

def vector_norm(v: list[float]) -> float:
    return math.sqrt(sum(a * a for a in v))

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    norm1 = vector_norm(v1)
    norm2 = vector_norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product(v1, v2) / (norm1 * norm2)

if __name__ == "__main__":
    # Simulated 4-dimensional embeddings
    v_for_loop   = [0.9, 0.8, 0.1, 0.2]
    v_while_loop = [0.85, 0.75, 0.2, 0.15]
    v_pancakes   = [0.05, 0.1, 0.9, 0.8]

    sim_loops = cosine_similarity(v_for_loop, v_while_loop)
    sim_unrelated = cosine_similarity(v_for_loop, v_pancakes)

    print(f"Similarity (for_loop vs while_loop): {sim_loops:.4f}")
    print(f"Similarity (for_loop vs pancakes):   {sim_unrelated:.4f}")
    assert sim_loops > sim_unrelated
    print("✅ Embeddings cosine test passed.")
```

---

## 3. Mock Interview Questions
- **Q: Why does EduPath normalize vectors before computing Inner Product in FAISS?**\
  *A:* Because $\langle \hat{u}, \hat{v} \rangle = \frac{u \cdot v}{\|u\| \|v\|} = \cos(\theta)$. When vectors are unit normalized, inner product is identical to cosine similarity, enabling hardware-accelerated BLAS dot product routines.
- **Q: What happens if an embedding dimension mismatch occurs (e.g., 1536 vs 768)?**\
  *A:* pgvector will raise a `vector dimension mismatch` SQL error because the column is strictly defined as `vector(768)`. EduPath asserts vector dimensionality at generation time in `services/embedding_service.py`.
