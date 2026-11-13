#!/usr/bin/env python3
"""
Experiment 01: Text Tokenization and Scaled Dot-Product Attention Visualization
CSE473 — Academic Practical (UN SDG 4 / EduPath Major Project)

Objectives:
1. Understand tokenization and vocabulary mapping (text -> token IDs -> embeddings).
2. Implement scaled dot-product attention from scratch using pure Python and NumPy:
       Attention(Q, K, V) = softmax( (Q * K^T) / sqrt(d_k) ) * V
3. Visualize self-attention weights in terminal (ASCII heatmap) and output numerical attention matrices.
"""

import math
import numpy as np


def simple_tokenize(text: str) -> list[str]:
    """Basic subword/whitespace tokenizer with punctuation separation."""
    import re
    cleaned = re.sub(r'([.,!?;:])', r' \1 ', text)
    return [t for t in cleaned.strip().split() if t]


def build_vocabulary(tokens: list[str]) -> tuple[dict[str, int], dict[int, str]]:
    """Build bidirectional token <-> ID mapping."""
    unique_tokens = sorted(list(set(tokens)))
    token_to_id = {t: i for i, t in enumerate(unique_tokens)}
    id_to_token = {i: t for i, t in enumerate(unique_tokens)}
    return token_to_id, id_to_token


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Numerically stable softmax."""
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / np.sum(e_x, axis=axis, keepdims=True)


def scaled_dot_product_attention(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute Scaled Dot-Product Attention:
        Attention(Q, K, V) = softmax( (Q @ K.T) / sqrt(d_k) ) @ V

    Q: [seq_len, d_k]
    K: [seq_len, d_k]
    V: [seq_len, d_v]
    """
    d_k = Q.shape[-1]
    scores = np.matmul(Q, K.T) / math.sqrt(d_k)
    weights = softmax(scores, axis=-1)
    output = np.matmul(weights, V)
    return output, weights


def render_ascii_heatmap(tokens: list[str], weights: np.ndarray):
    """Render an ASCII attention map in terminal."""
    header = f"{'':<12}" + "".join(f"{t[:8]:>10}" for t in tokens)
    print(header)
    print("-" * len(header))
    for i, t_i in enumerate(tokens):
        row = f"{t_i[:10]:<12}"
        for j in range(len(tokens)):
            w = weights[i, j]
            # Use ASCII density blocks
            if w > 0.4:
                block = f"[{w:.2f}]"
            elif w > 0.2:
                block = f" {w:.2f} "
            elif w > 0.1:
                block = f"  .{w*100:.0f}  "
            else:
                block = f"  ---  "
            row += f"{block:>10}"
        print(row)


def run_experiment():
    print("=" * 75)
    print("EXPERIMENT 01: TOKENIZATION & ATTENTION MECHANISM VISUALIZATION")
    print("=" * 75)

    sample_sentence = "EduPath teaches Python loops step by step."
    print(f"Sample Educational Text: '{sample_sentence}'\n")

    # 1. Tokenization
    tokens = simple_tokenize(sample_sentence)
    token_to_id, id_to_token = build_vocabulary(tokens)
    token_ids = [token_to_id[t] for t in tokens]

    print("Step 1: Tokenization and Vocabulary Mapping")
    print(f"Tokens:     {tokens}")
    print(f"Token IDs:  {token_ids}")
    print(f"Vocab Size: {len(token_to_id)}\n")

    # 2. Embedding simulation (dim = 4)
    np.random.seed(42)
    embedding_dim = 4
    seq_len = len(tokens)

    # Initialize random embeddings for demonstration
    embeddings = np.random.randn(seq_len, embedding_dim)

    # 3. Query, Key, Value linear projections (dim = 4)
    W_q = np.random.randn(embedding_dim, embedding_dim) * 0.5
    W_k = np.random.randn(embedding_dim, embedding_dim) * 0.5
    W_v = np.random.randn(embedding_dim, embedding_dim) * 0.5

    Q = np.matmul(embeddings, W_q)
    K = np.matmul(embeddings, W_k)
    V = np.matmul(embeddings, W_v)

    print("Step 2: Linear Projections into Q, K, V space")
    print(f"Sequence Length: {seq_len}, Embedding Dimension: {embedding_dim}")
    print(f"Q shape: {Q.shape}, K shape: {K.shape}, V shape: {V.shape}\n")

    # 4. Scaled Dot-Product Attention
    output, weights = scaled_dot_product_attention(Q, K, V)

    print("Step 3: Scaled Dot-Product Attention Weights")
    print("Formula: Softmax( (Q * K^T) / sqrt(d_k) )\n")
    render_ascii_heatmap(tokens, weights)

    print("\nStep 4: Output Context Vectors (Attention @ V)")
    print(f"Context vector representation for token '{tokens[0]}':")
    print(np.round(output[0], 4))

    print("\nInterpretation:")
    print("Each row shows how much attention a query token pays to every key token in the sentence.")
    print("Row sums = 1.0 (Softmax normalized).")
    for i, t in enumerate(tokens):
        assert math.isclose(np.sum(weights[i]), 1.0, rel_tol=1e-5), "Weights must sum to 1"

    print("\n" + "=" * 75)
    print("✅ Experiment 01 completed successfully.")


if __name__ == "__main__":
    run_experiment()
