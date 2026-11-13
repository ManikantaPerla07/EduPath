# Interview Prep: LangGraph StateGraph & Checkpointing
**EduPath Technical Component:** Stateful Agent Orchestration, Conditional Routing, PostgreSQL Checkpointer\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
While LangChain provides linear chains, **LangGraph** models cyclic stateful agent workflows as directed graphs:
- **State Schema:** `TypedDict` containing all mutable conversation state (`TutorGraphState`).
- **Nodes:** Python functions that receive state and return incremental updates.
- **Edges:** Deterministic transitions (`graph.add_edge("validate", "resolve")`).
- **Conditional Edges:** Branching functions that decide the next node dynamically based on state values (e.g., routing to `learner_tools` vs `retrieve_context`).
- **Checkpointer:** Persists thread state to PostgreSQL so conversations resume seamlessly after server restarts.

---

## 2. Production Code Reference
- StateGraph definition: `agents/tutor_graph.py` (lines 450-505)
- PostgreSQL checkpointer: `services/langgraph_checkpoint_service.py`
- ToolNode binding: `agents/tutor_graph.py` (lines 465-475)

---

## 3. Simplified 15-Minute StateGraph Implementation
```python
# interview_preparation/langgraph/simple_graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class SimpleState(TypedDict):
    question: str
    is_personal: bool
    answer: str

def validate_node(state: SimpleState):
    return {"question": state["question"].strip()}

def route_decision(state: SimpleState) -> str:
    if state.get("is_personal", False):
        return "personal_node"
    return "course_node"

def personal_node(state: SimpleState):
    return {"answer": f"Here is your personal progress for {state['question']}."}

def course_node(state: SimpleState):
    return {"answer": f"Here is the Python concept explanation for {state['question']}."}

# Build and compile graph
builder = StateGraph(SimpleState)
builder.add_node("validate", validate_node)
builder.add_node("personal_node", personal_node)
builder.add_node("course_node", course_node)

builder.add_edge(START, "validate")
builder.add_conditional_edges("validate", route_decision, {
    "personal_node": "personal_node",
    "course_node": "course_node",
})
builder.add_edge("personal_node", END)
builder.add_edge("course_node", END)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"question": "loops", "is_personal": True})
    print("Graph Output:", result["answer"])
    assert "personal progress" in result["answer"]
    print("✅ LangGraph interview demo passed.")
```

---

## 4. Mock Interview Questions
- **Q: Why use LangGraph instead of a standard while loop for agent execution?**\
  *A:* LangGraph formalizes execution as an inspectable DAG with clear checkpoint hooks. It natively supports time-travel debugging, persistent conversational state across distributed workers, human-in-the-loop approvals, and structured failure recovery.
- **Q: How does PostgreSQL checkpointing work in EduPath?**\
  *A:* `langgraph-checkpoint-postgres` writes a snapshot of the serialized graph state to the `checkpoints` table after each node execution, keyed by `thread_id`. When a student returns, the graph is instantiated from the last verified checkpoint rather than starting from scratch.
