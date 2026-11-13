# Practical 07: Collaborative Multi-Agent System (Planner & Reviewer)
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
A single monolithic prompt attempting to formulate and validate complex curricula often exhibits confirmation bias, glossing over subtle prerequisite gaps. Decomposing the system into specialized collaborative agents with adversarial audit roles increases reliability, transparency, and pedagogical safety.

### Learning Objectives:
1. Model distinct agent personae with clear role boundaries (Planner vs Reviewer vs Coordinator).
2. Establish formal typed message passing (`AgentMessage` with schema validation).
3. Demonstrate self-correction through critique and revision loops.
4. Synthesize multi-agent outputs into an actionable learning plan.

---

## 2. Multi-Agent Architecture
```
    [User Goal Request]
             │
             ▼
      ┌──────────────┐
      │ Coordinator  │
      └──────┬───────┘
             │ Dispatches Goal
             ▼
      ┌──────────────┐   Draft Plan   ┌──────────────┐
      │   Planner    ├───────────────►│   Reviewer   │
      │    Agent     │◄───────────────┤    Agent     │
      └──────────────┘    Critique    └──────┬───────┘
                                             │ Approved
                                             ▼
                                      ┌──────────────┐
                                      │ Final Output │
                                      └──────────────┘
```

---

## 3. How to Run
```bash
python experiments/07_multi_agent/experiment.py
```
Self-contained, pure Python.

---

## 4. Key Results & Observations
- In the initial proposal, the Planner prematurely scheduled *Nested Loops* without including *Basic for loop & range()*.
- The Reviewer agent caught the prerequisite violation and rejected the draft with specific pedagogical rationale.
- The Planner incorporated the feedback in Turn 3, prepending a diagnostic check and sequence fundamentals.
- The Reviewer approved the revised curriculum in Turn 4, achieving convergence in 4 communication steps.

---

## 5. Distinction from Production Architecture
- **In EduPath Production:** The runtime utilizes a single consolidated **LangGraph** StateGraph workflow (`agents/tutor_graph.py`). Combining the workflow into specialized graph nodes (`validate_input` $\to$ `resolve_context` $\to$ `decide_learner_tools` $\to$ `retrieve_context` $\to$ `adapt_teaching` $\to$ `generate_answer`) achieves the separation of concerns without incurring the latency and cost of multiple independent LLM calls.
- This practical isolates multi-agent message-passing principles for educational research.

---

## 6. Interview Preparation Q&A
- **Q: What is the primary failure mode of uncoordinated multi-agent loops?**\
  *A:* Infinite critique-revision oscillations (deadlocks) where agent A and agent B cannot agree on subjective criteria. Practical multi-agent coordinators prevent this by enforcing a hard upper bound on turns (e.g. `max_revisions = 3`) and fallback mediation heuristics.
- **Q: How does LangGraph model agent workflows compared to decentralized multi-agent messaging?**\
  *A:* LangGraph represents the workflow as a cyclic state machine with a centralized shared state (`TutorGraphState`), deterministic routing functions (conditional edges), and checkpointed persistence, eliminating network serialization overhead and message loss.
