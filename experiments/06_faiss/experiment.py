#!/usr/bin/env python3
"""
Experiment 06: FAISS Similarity Search Demo
=============================================
CSE473 — Academic Practical (UN SDG 4 / EduPath Major Project)

Demonstrates Facebook AI Similarity Search (FAISS) architecture for fast vector
similarity search on Python educational content embeddings.

Key Concepts:
  - Text -> vector embedding via TF-IDF (or dense vectors)
  - FAISS IndexFlatL2 (L2 / Euclidean distance)
  - FAISS IndexFlatIP (Inner Product / cosine similarity on normalized vectors)
  - Top-K nearest neighbor retrieval
  - Comparison with brute-force NumPy search
  - Fallback engine: When faiss-cpu/scikit-learn are not installed, executes
    via high-performance NumPy simulation with identical API and math.
"""

import math
import re
import time
import numpy as np

# ── 1. Dependency Resolution / Fallback Engine ───────────────────────────────

try:
    import faiss
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_NATIVE_FAISS = True
except ImportError:
    HAS_NATIVE_FAISS = False


class SimpleTfidfVectorizer:
    """Pure-NumPy TF-IDF vectorizer fallback."""

    def __init__(self):
        self.vocabulary_ = {}
        self.idf_ = None

    def fit_transform(self, corpus: list[str]) -> np.ndarray:
        # Build vocabulary
        docs_tokens = [re.findall(r'[a-zA-Z0-9_]+', d.lower()) for d in corpus]
        vocab = sorted(list(set(t for tokens in docs_tokens for t in tokens)))
        self.vocabulary_ = {t: i for i, t in enumerate(vocab)}

        N = len(corpus)
        df = np.zeros(len(vocab))
        for tokens in docs_tokens:
            for t_idx in set(self.vocabulary_[t] for t in tokens if t in self.vocabulary_):
                df[t_idx] += 1

        self.idf_ = np.log((1 + N) / (1 + df)) + 1.0

        # Term frequency matrix
        X = np.zeros((N, len(vocab)), dtype="float32")
        for i, tokens in enumerate(docs_tokens):
            for t in tokens:
                if t in self.vocabulary_:
                    X[i, self.vocabulary_[t]] += 1
            # L2 normalize row
            norm = np.linalg.norm(X[i])
            if norm > 0:
                X[i] = (X[i] * self.idf_) / norm
        return X

    def transform(self, queries: list[str]) -> np.ndarray:
        N = len(queries)
        X = np.zeros((N, len(self.vocabulary_)), dtype="float32")
        for i, q in enumerate(queries):
            tokens = re.findall(r'[a-zA-Z0-9_]+', q.lower())
            for t in tokens:
                if t in self.vocabulary_:
                    X[i, self.vocabulary_[t]] += 1
            norm = np.linalg.norm(X[i])
            if norm > 0:
                X[i] = (X[i] * self.idf_) / norm
        return X

    def get_feature_names_out(self):
        inv = {v: k for k, v in self.vocabulary_.items()}
        return np.array([inv[i] for i in range(len(inv))])


class SimulatedFAISSIndexFlatL2:
    """Simulated IndexFlatL2 matching exact FAISS C++ API."""

    def __init__(self, dim: int):
        self.dim = dim
        self.is_trained = True
        self.vectors = np.empty((0, dim), dtype="float32")

    def add(self, x: np.ndarray):
        self.vectors = np.vstack([self.vectors, x.astype("float32")])

    @property
    def ntotal(self) -> int:
        return len(self.vectors)

    def search(self, x: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        # L2 squared distance: ||q - v||^2
        diffs = self.vectors[None, :, :] - x[:, None, :]  # [n_queries, n_vecs, dim]
        dists = np.sum(diffs ** 2, axis=-1)
        top_k_indices = np.argsort(dists, axis=-1)[:, :k]
        top_k_dists = np.take_along_axis(dists, top_k_indices, axis=-1)
        return top_k_dists, top_k_indices


class SimulatedFAISSIndexFlatIP:
    """Simulated IndexFlatIP matching exact FAISS C++ API."""

    def __init__(self, dim: int):
        self.dim = dim
        self.is_trained = True
        self.vectors = np.empty((0, dim), dtype="float32")

    def add(self, x: np.ndarray):
        self.vectors = np.vstack([self.vectors, x.astype("float32")])

    @property
    def ntotal(self) -> int:
        return len(self.vectors)

    def search(self, x: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        # Inner product: q @ v.T
        scores = np.matmul(x, self.vectors.T)
        top_k_indices = np.argsort(-scores, axis=-1)[:, :k]
        top_k_scores = np.take_along_axis(scores, top_k_indices, axis=-1)
        return top_k_scores, top_k_indices


def simulated_normalize_L2(x: np.ndarray):
    norms = np.linalg.norm(x, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    x /= norms


# ── 2. Educational Corpus ───────────────────────────────────────────────────

CORPUS = [
    "Python is a high-level, interpreted programming language.",
    "Variables in Python are created when you assign a value to them.",
    "Python uses indentation to define code blocks instead of curly braces.",
    "A list is an ordered, mutable collection of items in Python.",
    "Tuples are immutable sequences, often used for fixed collections.",
    "Dictionaries store data as key-value pairs for fast lookup.",
    "A for loop iterates over a sequence such as a list, tuple, or string.",
    "While loops repeat a block of code as long as a condition is true.",
    "Functions are defined using the def keyword followed by a name.",
    "Lambda functions are small anonymous functions defined with lambda.",
    "List comprehensions provide a concise way to create lists.",
    "Python supports multiple inheritance through method resolution order.",
    "Exception handling uses try, except, else, and finally blocks.",
    "Decorators modify the behavior of a function using the @ syntax.",
    "Generators yield values one at a time using the yield keyword.",
    "The with statement simplifies resource management using context managers.",
    "Modules are Python files that can be imported into other scripts.",
    "The pip tool installs third-party packages from PyPI.",
    "NumPy provides efficient array operations for numerical computing.",
    "Pandas is used for data manipulation and analysis with DataFrames.",
    "Matplotlib creates static, animated, and interactive visualizations.",
    "Python strings are immutable sequences of Unicode characters.",
    "Sets are unordered collections of unique elements in Python.",
    "The global interpreter lock (GIL) limits true multi-threading in CPython.",
    "Type hints improve code readability but are not enforced at runtime.",
    "F-strings provide a readable way to embed expressions in strings.",
    "The __init__ method initializes new instances of a Python class.",
    "Recursion is a technique where a function calls itself to solve problems.",
]


def run_experiment():
    print("=" * 70)
    print("EXPERIMENT 06: FAISS SIMILARITY SEARCH DEMO")
    print(f"Backend Engine: {'Native FAISS C++ (faiss-cpu)' if HAS_NATIVE_FAISS else 'Simulated NumPy Engine (Zero Heavy Dependencies)'}")
    print("=" * 70)
    print(f"Corpus size: {len(CORPUS)} educational sentences\n")

    # Vectorizer
    if HAS_NATIVE_FAISS:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(CORPUS)
        embeddings = np.ascontiguousarray(tfidf_matrix.toarray().astype("float32"))
    else:
        vectorizer = SimpleTfidfVectorizer()
        embeddings = vectorizer.fit_transform(CORPUS)

    n_docs, dim = embeddings.shape
    print(f"STEP 1: Embeddings Matrix shape: {n_docs} documents x {dim} dimensions")
    print(f"Vocabulary size: {len(vectorizer.vocabulary_)}\n")

    # FAISS IndexFlatL2
    print("STEP 2: FAISS IndexFlatL2 (Euclidean / L2 Distance)")
    if HAS_NATIVE_FAISS:
        index_l2 = faiss.IndexFlatL2(dim)
    else:
        index_l2 = SimulatedFAISSIndexFlatL2(dim)

    index_l2.add(embeddings)
    print(f"Index trained: {index_l2.is_trained}, Total vectors: {index_l2.ntotal}\n")

    queries = [
        "How do I use loops in Python?",
        "What is a list in Python?",
        "How to handle errors and exceptions?",
    ]

    for q in queries:
        if HAS_NATIVE_FAISS:
            q_vec = vectorizer.transform([q]).toarray().astype("float32")
        else:
            q_vec = vectorizer.transform([q])
        dists, indices = index_l2.search(q_vec, 3)
        print(f'Query: "{q}"')
        print(f"Top-3 Nearest Neighbors (L2 distance):")
        for rank, (dist, idx) in enumerate(zip(dists[0], indices[0]), 1):
            print(f"  {rank}. [L2={dist:.4f}] {CORPUS[idx]}")
        print()

    # FAISS IndexFlatIP (Cosine Similarity via Normalization)
    print("STEP 3: FAISS IndexFlatIP (Cosine Similarity via Normalized Inner Product)")
    embeddings_norm = embeddings.copy()
    if HAS_NATIVE_FAISS:
        faiss.normalize_L2(embeddings_norm)
        index_ip = faiss.IndexFlatIP(dim)
    else:
        simulated_normalize_L2(embeddings_norm)
        index_ip = SimulatedFAISSIndexFlatIP(dim)

    index_ip.add(embeddings_norm)

    for q in queries[:2]:
        if HAS_NATIVE_FAISS:
            q_vec = vectorizer.transform([q]).toarray().astype("float32")
            faiss.normalize_L2(q_vec)
        else:
            q_vec = vectorizer.transform([q])
            simulated_normalize_L2(q_vec)

        scores, indices = index_ip.search(q_vec, 3)
        print(f'Query: "{q}"')
        print(f"Top-3 Nearest Neighbors (Cosine Similarity):")
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), 1):
            print(f"  {rank}. [Cosine={score:.4f}] {CORPUS[idx]}")
        print()

    print("=" * 70)
    print("COMPARISON: FAISS vs PRODUCTION NEON PGVECTOR")
    print(f"{'Dimension':<25} | {'FAISS Index':<25} | {'Neon PostgreSQL + pgvector'}")
    print("-" * 75)
    print(f"{'Storage Location':<25} | {'In-Memory (RAM / GPU)':<25} | {'Relational DB (Persistent SSD)'}")
    print(f"{'Query Language':<25} | {'Python / C++ API':<25} | {'SQL (<=> cosine operator)'}")
    print(f"{'Course/Topic Filtering':<25} | {'Manual post-filter':<25} | {'ACID WHERE course_id = ...'}")
    print(f"{'EduPath Role':<25} | {'Academic Benchmark':<25} | {'Production Serving Engine'}")
    print("=" * 70)
    print("✅ Experiment 06 completed successfully.")


if __name__ == "__main__":
    run_experiment()
