# Interview Prep: Adaptive Assessment & Mastery Calculations
**EduPath Technical Component:** Evidence Damping Factor, Mastery States, Server-Side Grading\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
EduPath replaces subjective AI evaluation with deterministic psychometric rules:
- **Accuracy:** $\text{Accuracy} = \frac{\text{Correct Answers}}{\text{Total Attempts}} \times 100$
- **Evidence Damping Factor:** Prevents a student who gets 1 question right from claiming 100% mastery:
  $$\text{Evidence Factor} = \min\left(\frac{\text{Total Attempts}}{5}, 1.0\right)$$
  $$\text{Mastery Score} = \text{Accuracy} \times \text{Evidence Factor}$$
- **Classification States:**
  - `not_assessed`: 0 attempts.
  - `needs_revision`: $\ge 3$ attempts and $\text{Accuracy} < 50\%$.
  - `candidate_for_mastery`: $\ge 5$ attempts and $\text{Accuracy} \ge 80\%$.
  - `developing`: intermediate progress.

---

## 2. Production Code Reference
- Mastery calculation: `services/progress_service.py` (lines 19-100)
- Server-side grading: `services/grading_service.py`
- Adaptive question selection: `services/adaptive_question_service.py`

---

## 3. Simplified 15-Minute Implementation
```python
# interview_preparation/adaptive_assessment/simple_assessment.py

def calculate_mastery(attempts: int, correct: int) -> dict:
    if attempts <= 0:
        return {"accuracy": 0.0, "mastery_score": 0.0, "status": "not_assessed"}

    accuracy = (correct / attempts) * 100.0
    evidence_factor = min(attempts / 5.0, 1.0)
    mastery_score = accuracy * evidence_factor

    if attempts >= 3 and accuracy < 50.0:
        status = "needs_revision"
    elif attempts >= 5 and accuracy >= 80.0:
        status = "candidate_for_mastery"
    else:
        status = "developing"

    return {
        "accuracy": round(accuracy, 2),
        "mastery_score": round(mastery_score, 2),
        "status": status
    }

if __name__ == "__main__":
    # Test cases
    p1 = calculate_mastery(1, 1)  # 100% accuracy but low evidence factor (0.2) -> mastery 20%
    assert p1["mastery_score"] == 20.0 and p1["status"] == "developing"

    p2 = calculate_mastery(5, 4)  # 80% accuracy with full evidence (1.0) -> candidate for mastery
    assert p2["mastery_score"] == 80.0 and p2["status"] == "candidate_for_mastery"

    p3 = calculate_mastery(4, 1)  # 25% accuracy across 4 attempts -> needs revision
    assert p3["status"] == "needs_revision"

    print("✅ Adaptive assessment interview test passed.")
```

---

## 4. Mock Interview Questions
- **Q: Why does EduPath use an Evidence Factor in mastery score calculation?**\
  *A:* To avoid small-sample bias. If a student answers a single question correctly, their naive accuracy is 100%. Multiplying by $\min(\text{attempts}/5, 1.0)$ dampens the score until at least 5 assessment attempts provide statistically reliable evidence.
- **Q: How does the Adaptive Practice session adjust difficulty during a quiz?**\
  *A:* After each question is submitted, `services/adaptive_assessment_service.py` checks correctness. If correct, the system selects an unattempted question at a higher difficulty (Easy $\to$ Medium $\to$ Hard). If incorrect, it down-shifts difficulty or tests a prerequisite topic.
