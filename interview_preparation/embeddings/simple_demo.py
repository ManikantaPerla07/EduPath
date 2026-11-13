#!/usr/bin/env python3
"""Simplified Embedding & Cosine Similarity Demo for Technical Interviews."""

import math


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


if __name__ == "__main__":
    v_for_loop = [0.9, 0.8, 0.1, 0.2]
    v_while_loop = [0.85, 0.75, 0.2, 0.15]
    v_unrelated = [0.05, 0.1, 0.9, 0.8]

    sim_loops = cosine_similarity(v_for_loop, v_while_loop)
    sim_unrelated = cosine_similarity(v_for_loop, v_unrelated)

    print(f"Cosine Similarity (For Loop vs While Loop): {sim_loops:.4f}")
    print(f"Cosine Similarity (For Loop vs Pancakes):   {sim_unrelated:.4f}")
    assert sim_loops > sim_unrelated
    print("✅ Embedding demonstration passed successfully.")
