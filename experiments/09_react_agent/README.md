# Practical 09: ReAct (Reasoning + Acting) Agent with External Tools
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Static question-answering systems cannot answer dynamic learner questions such as *"What should I study next?"* because the answer depends on real-time database state (recent quiz attempts, accuracy thresholds, and prerequisite graphs). The **ReAct (Reasoning + Acting)** framework interleaves language reasoning with discrete tool invocations to collect live facts before synthesizing an answer.

### Learning Objectives:
1. Implement the ReAct cycle:
   $$\text{Thought}_t \to \text{Action}_t \to \text{Observation}_t \to \text{Thought}_{t+1} \to \dots \to \text{Final Answer}$$
2. Chain multiple tools in sequential dependency order.
3. Enforce strict sandboxing: read-only access, identity binding, and JSON input/output schema validation.

---

## 2. ReAct Execution Flowchart
```
  [Learner Query: "What should I study next?"]
                       │
                       ▼
                 ┌───────────┐
                 │ Thought 1 │  "Need learner's progress"
                 └─────┬─────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Action 1  │  get_learner_progress()
                 └─────┬─────┘
                       │
                       ▼
               ┌───────────────┐
               │ Observation 1 │  Loops accuracy: 33.3%, attempts: 6
               └───────┬───────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Thought 2 │  "Compute authoritative mastery"
                 └─────┬─────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Action 2  │  compute_mastery_status()
                 └─────┬─────┘
                       │
                       ▼
               ┌───────────────┐
               │ Observation 2 │  Status: 'needs_revision'
               └───────┬───────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Thought 3 │  "Check prerequisites for Loops"
                 └─────┬─────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Action 3  │  get_topic_prerequisites("loops")
                 └─────┬─────┘
                       │
                       ▼
               ┌───────────────┐
               │ Observation 3 │  Prerequisites: [Conditionals, Operators]
               └───────┬───────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Thought 4 │  "Synthesize targeted recommendation"
                 └─────┬─────┘
                       │
                       ▼
        [Final Personalized Actionable Response]
```

---

## 3. How to Run
```bash
python experiments/09_react_agent/experiment.py
```
Self-contained, pure Python.

---

## 4. Key Results & Trace Analysis
- The agent executed 3 sequential tool iterations:
  1. `get_learner_progress` revealed a 33.3% accuracy rate on Python Loops.
  2. `compute_mastery_status` authoritatively evaluated the record as `needs_revision`.
  3. `get_topic_prerequisites` mapped the cognitive blockers to *Conditional Statements* and *Operators*.
- The final response directed the learner to revise prerequisites rather than blindly repeating failed loop questions.

---

## 5. Security Invariants & Production Connection
In production EduPath:
- `agents/learner_tools.py` defines tools (`get_my_learning_progress`, `get_my_study_plan`).
- **Security Rule 1:** The LLM is NEVER allowed to specify `user_id`; identity is injected strictly by server-side graph state (`runtime.state["user_id"]`).
- **Security Rule 2:** Tools are read-only.
- **Security Rule 3:** No arbitrary SQL generation or shell execution is permitted.

---

## 6. Interview Preparation Q&A
- **Q: How does ReAct prevent hallucinations compared to Direct Chain-of-Thought?**\
  *A:* Direct CoT relies exclusively on static parametric weights in the model. If memory or internal knowledge is fuzzy, intermediate reasoning steps will hallucinate. ReAct grounds intermediate steps by executing deterministic environment tools, feeding verified external observations back into the context window.
- **Q: What stops an infinite loop if a tool repeatedly returns errors?**\
  *A:* Production systems enforce a maximum iteration limit (`max_iterations = 5` in LangGraph) and structured error handling that flags unrecoverable tool failures and routes to a graceful fallback answer node.
