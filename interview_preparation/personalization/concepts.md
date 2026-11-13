# Interview Prep: Few-Shot Personalization Across 3 Difficulty Levels
**EduPath Technical Component:** In-Context Demonstration Learning, Level-Specific Exemplars, Misconception Adaptation\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
The core requirement of the CSE473 allocation is:
> *"Build a tutor that adapts its explanation style using a few examples of a student's level/mistakes (few-shot), and show it adjusts across 2–3 difficulty levels."*

EduPath fulfills this without fine-tuning by injecting **curated few-shot exemplars** into the system prompt:
- **Beginner:** Employs analogies (e.g. chef making pancakes), short sentences, 3-line code example, guided hint, and easy check.
- **Intermediate:** Technical syntax walkthrough, step-by-step loop trace, common pitfalls (e.g., mutating list during iteration), and moderate exercise.
- **Advanced:** Explores underlying mechanics (Python Iterator Protocol `iter()`/`next()`), time/space complexity ($O(1)$ range memory), edge cases, and challenge problems.

---

## 2. Production Code Reference
- Exemplar repository: `services/few_shot_prompting_service.py`
- Demonstration script: `demonstrations/few_shot_adaptation_demo.py`
- Prompt injection: `services/adaptive_learning_service.py` and `services/answer_generation_service.py`

---

## 3. Simplified 15-Minute Implementation
```python
# interview_preparation/personalization/simple_personalization.py

EXEMPLARS = {
    "beginner": {
        "analogy": "Like an oven timer counting ticks.",
        "code": "for i in range(1, 4): print(i)",
        "hint": "The stop number is never printed!",
    },
    "advanced": {
        "analogy": "Implements the Iterator Protocol under PEP 234.",
        "code": "it = iter(range(3)); print(next(it))",
        "hint": "range objects consume O(1) auxiliary space.",
    }
}

def get_teaching_style(mastery_status: str) -> dict:
    level = "beginner" if mastery_status in ("not_assessed", "needs_revision") else "advanced"
    return EXEMPLARS[level]

if __name__ == "__main__":
    style_struggling = get_teaching_style("needs_revision")
    assert "oven timer" in style_struggling["analogy"]

    style_mastery = get_teaching_style("candidate_for_mastery")
    assert "Iterator Protocol" in style_mastery["analogy"]
    print("✅ Few-shot personalization interview demo passed.")
```

---

## 4. Mock Interview Questions
- **Q: Why is Few-Shot prompting preferred over LoRA fine-tuning for this deployment?**\
  *A:* Few-shot in-context learning incurs zero training compute costs, requires no GPU VRAM, adapts instantly at inference time based on real-time database state, and eliminates risk of catastrophic forgetting across general conversational tasks.
- **Q: How does EduPath ensure few-shot exemplars do not leak private student data?**\
  *A:* Exemplars are version-controlled, synthetic pedagogical archetypes stored in code (`services/few_shot_prompting_service.py`). Actual learner account data is NEVER copied into reusable prompts.
