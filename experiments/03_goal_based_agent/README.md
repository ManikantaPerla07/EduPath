# Practical 03: Goal-Based Agent in an Educational State Space
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
A simple reflex agent acts only on current percepts without foresight, which fails in sequential curriculum environments where prerequisite dependencies must be met before reaching an advanced topic. A **Goal-Based Agent** combines state representations with an explicit target goal to formulate multi-step plans.

### Learning Objectives:
1. Define the formal PEAS model (Performance measure, Environment, Actuators, Sensors).
2. Formulate state representations and discrete action transition models.
3. Implement goal-directed path search (BFS) avoiding prerequisite blockers.
4. Execute the perception-deliberation-action cycle to termination.

---

## 2. PEAS Specification for EduPath Learning Navigation
- **Performance Measure:** Minimum learning steps to master target concept without encountering unmet prerequisite blockers.
- **Environment:** $5 \times 5$ curriculum grid where states correspond to concept nodes and blocked cells represent locked/unmet prerequisites.
- **Actuators:** Directional transitions `UP`, `DOWN`, `LEFT`, `RIGHT`.
- **Sensors:** Current coordinate position, boundary detectors, goal proximity detector.

---

## 3. How to Run
```bash
python experiments/03_goal_based_agent/experiment.py
```
Self-contained, pure Python.

---

## 4. Key Results & Trace
- **Start State:** `(0, 0)` (Variables)
- **Goal State:** `(2, 4)` (Functions)
- **Obstacles:** Prerequisite barriers at `(1,1)`, `(1,2)`, `(2,3)`, `(3,1)`
- **Generated Plan:** 6 actions (`RIGHT -> RIGHT -> RIGHT -> DOWN -> RIGHT -> DOWN`)
- **Execution:** Successfully navigates around prerequisite blockers and halts on goal arrival.

---

## 5. Connection to Production EduPath
In production EduPath:
- `services/study_plan_service.py` functions as a goal-directed curriculum planner: it performs a topological sort over the Directed Acyclic Graph (DAG) of topic prerequisites (`topic_prerequisites` table in PostgreSQL), prioritizing weak topics and goal keywords before scheduling dependent topics.

---

## 6. Interview Preparation Q&A
- **Q: What distinguishes a Goal-Based Agent from a Utility-Based Agent?**\
  *A:* A Goal-Based Agent operates with a binary success criterion (goal achieved vs not achieved). A Utility-Based Agent incorporates continuous preferences (a utility function $U(s)$) that balances trade-offs, such as learning speed versus cognitive load.
- **Q: Why is BFS guaranteed to find the shortest path in this state space?**\
  *A:* Because every state transition in the grid has uniform unit edge cost ($c=1$). BFS expands nodes frontier-by-frontier, ensuring that the first time the goal state is popped from the queue, it is reached via the minimum number of transitions.
