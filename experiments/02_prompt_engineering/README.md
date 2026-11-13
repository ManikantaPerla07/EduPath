# Practical 02: Zero-Shot, Few-Shot, and Chain-of-Thought Prompting Comparison
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Generative LLMs exhibit vastly different tutoring behaviors depending on how prompts are engineered. A naive zero-shot prompt produces terse factual answers without pedagogical scaffolding. In contrast, few-shot and structured prompts guide the model to adopt empathy, use analogies, anticipate common student bugs, and generate practice problems.

### Learning Objectives:
1. Compare 4 prompt engineering paradigms on an identical Python student question:
   - **Zero-Shot:** Minimal instruction.
   - **Few-Shot:** In-context exemplars demonstrating desired tone and practice checks.
   - **Structured:** Role definitions, negative constraints, and explicit Markdown schema.
   - **Chain-of-Thought (CoT):** Step-by-step cognitive diagnosis before generating student response.
2. Quantitatively score responses on Clarity, Misconception Diagnosis, Structural Compliance, and Scaffolding.

---

## 2. Experimental Setup
- **Target Student Query:**\
  *"Why does my loop print 0, 1, 2, 3, 4 when I wrote range(5)? I wanted it to count to 5!"*
- **Criteria Evaluated (1.0 to 5.0 scale):**
  - **Clarity:** Readability for a beginner without unnecessary jargon.
  - **Misconception Depth:** Identification of 0-indexing vs cardinality.
  - **Structure Compliance:** Adherence to output formatting instructions.
  - **Scaffolding / Practice:** Inclusion of guided hints or follow-up exercises.

---

## 3. How to Run
```bash
python experiments/02_prompt_engineering/experiment.py
```
Self-contained, deterministic script with pure Python.

---

## 4. Key Observations & Comparison Matrix
| Prompting Strategy | Clarity | Misconception Diagnosis | Structural Compliance | Scaffolding / Practice |
|---|---|---|---|---|
| **Zero-Shot** | 3.0 | 2.0 | 2.5 | 1.0 |
| **Few-Shot** | 4.0 | 3.5 | 4.0 | 4.5 |
| **Structured** | 4.5 | 4.0 | 5.0 | 5.0 |
| **Chain-of-Thought** | 4.8 | 5.0 | 4.5 | 4.0 |

### Insights:
- **Zero-Shot** simply answered the mechanics (`range(1, 6)`) without explaining why the student got confused.
- **Few-Shot** successfully transferred stylistic patterns from the exemplars (e.g., adding an analogy and closing with a practice check).
- **Structured Prompting** guaranteed clean UI rendering via markdown sections.
- **Chain-of-Thought** correctly separated the teacher's internal diagnosis (cardinality vs 1-indexed endpoint) from the explanation given to the student.

---

## 5. Connection to Production EduPath
In production EduPath:
- `services/few_shot_prompting_service.py` provides curated few-shot exemplars tailored to the learner's mastery status (`beginner`, `intermediate`, `advanced`).
- `services/answer_generation_service.py` enforces structured prompt constraints (groundedness in approved curriculum excerpts, citation formats `[S1]`, no hallucinated code execution).

---

## 6. Interview Preparation Q&A
- **Q: Why does Few-Shot prompting outperform Zero-Shot in educational AI?**\
  *A:* LLMs have vast distribution priors; few-shot exemplars act as conditioning vectors in latent space, steering the model towards the target style, conversational format, and pedagogical depth without parameter updates.
- **Q: What is the risk of exposing Chain-of-Thought traces directly to students?**\
  *A:* Exposing internal chain-of-thought can confuse students with internal diagnostic meta-language, increase cognitive load, and potentially reveal private system instructions or ungrounded speculative reasoning. EduPath hides internal graph state and outputs only the curated response.
