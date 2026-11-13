# Interview Prep: Python Fundamentals
**EduPath Technical Component:** Core Service Logic, Typing, Exception Hierarchy\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
In EduPath, Python fundamentals govern every server-side service:
- Custom Exception Hierarchies (`AnswerGenerationError`, `ChatRateLimitError`, `AgentRunAlreadyActiveError`) for clean error propagation.
- Data structures (Dictionaries, Sets, Tuples) for fast lookup of prerequisites and options.
- Context Managers (`with psycopg.connect(...)`) for deterministic database connection cleanup.
- Decorators and Type Annotations (`Mapping[str, Any]`, `UUID`) for static analysis.

---

## 2. Production Code Reference
- Exception definitions: `services/answer_generation_service.py` (lines 80-85)
- Context managers & locks: `services/learner_service.py` (lines 94-105)
- Set operations: `services/study_plan_service.py` (lines 92-100)

---

## 3. Simplified 15-Minute Interview Implementation
```python
# interview_preparation/python_fundamentals/simplified_python.py

class EduPathError(Exception):
    """Base exception for EduPath domain errors."""
    pass

class RateLimitError(EduPathError):
    """Raised when request frequency exceeds allowed threshold."""
    pass

def validate_and_parse_user_claims(claims: dict) -> dict:
    """Validates required authentication claims from OIDC mapping."""
    if not isinstance(claims, dict):
        raise TypeError("Claims must be a dictionary.")

    required_fields = ["sub", "email"]
    for field in required_fields:
        if field not in claims or not claims[field]:
            raise ValueError(f"Missing required claim: {field}")

    return {
        "user_id": claims["sub"].strip(),
        "email": claims["email"].strip().lower(),
        "is_verified": bool(claims.get("email_verified", False))
    }

if __name__ == "__main__":
    sample = {"sub": "google_123", "email": "STUDENT@EXAMPLE.COM", "email_verified": True}
    parsed = validate_and_parse_user_claims(sample)
    print("Parsed user:", parsed)
    assert parsed["email"] == "student@example.com"
    print("✓ Python fundamentals test passed.")
```

---

## 4. Common Coding Bugs & Edge Cases
1. **Mutable Default Arguments:** `def func(items=[])` creates a shared list across calls. Always use `def func(items=None): if items is None: items = []`.
2. **KeyError in Dictionary Lookups:** Use `.get(key, default)` or explicit membership checks `if key in d:`.
3. **Boolean Subclass of Integer:** In Python, `isinstance(True, int)` evaluates to `True`! In validation, always check `if isinstance(val, bool) or not isinstance(val, int): raise ValueError()`.

---

## 5. Mock Interview Questions
- **Q: Why is `isinstance(val, bool)` checked before `isinstance(val, int)` in EduPath validation?**\
  *A:* In Python, `bool` is a subclass of `int` (`issubclass(bool, int) == True`). If you check `if isinstance(True, int)`, Python returns `True`, allowing boolean values like `True` to pass integer checks unless explicitly filtered out first.
- **Q: How do Python context managers work under the hood?**\
  *A:* Context managers implement `__enter__()` and `__exit__(exc_type, exc_val, exc_tb)`. When entered via `with`, `__enter__` returns the resource. When exiting (even if an exception occurs), `__exit__` is guaranteed to execute, enabling safe rollback and socket closure.
