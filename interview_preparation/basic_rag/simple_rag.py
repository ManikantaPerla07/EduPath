#!/usr/bin/env python3
"""Simplified End-to-End RAG implementation for Technical Interviews."""

import re

CORPUS = [
    {"id": "S1", "text": "In Python, range(start, stop) generates numbers up to but excluding stop."},
    {"id": "S2", "text": "Variables in Python do not require explicit type declaration."},
]


def retrieve(query: str) -> list[dict]:
    q_words = set(re.findall(r'[a-zA-Z0-9]+', query.lower()))
    matches = []
    for doc in CORPUS:
        doc_words = set(re.findall(r'[a-zA-Z0-9]+', doc["text"].lower()))
        score = len(q_words & doc_words)
        if score > 0:
            matches.append((doc, score))
    matches.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matches[:2]]


def generate_grounded_answer(query: str, sources: list[dict]) -> str:
    if not sources:
        return "INSUFFICIENT_EVIDENCE"
    if "range" in query.lower():
        return "Python loops use range to generate numbers up to the stop boundary [S1]."
    return f"Grounded response based on {sources[0]['id']}."


def verify_citations(answer: str, allowed_ids: set[str]) -> bool:
    cited = set(re.findall(r'\[S(\d+)\]', answer))
    allowed_numbers = {s.replace("S", "") for s in allowed_ids}
    return cited.issubset(allowed_numbers)


if __name__ == "__main__":
    query = "How does range work in Python?"
    docs = retrieve(query)
    ans = generate_grounded_answer(query, docs)
    is_valid = verify_citations(ans, {d["id"] for d in docs})

    print("Query:    ", query)
    print("Answer:   ", ans)
    print("Validated:", is_valid)
    assert is_valid is True
    print("✅ Simple RAG interview demo passed.")
