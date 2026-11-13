# Interview Prep: ReAct Pattern & Agent Tools
**EduPath Technical Component:** Read-Only Learner Tools, Sandboxed Execution, ToolNode\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
The **ReAct (Reasoning + Acting)** pattern equips the LLM with live external capabilities:
- **Thought:** The model articulates a plan or reasoning goal.
- **Action:** The model calls a defined tool with structured arguments.
- **Observation:** The application executes the tool and injects the output back into the message transcript.
- **Final Answer:** The model summarizes findings for the user.

---

## 2. Production Code Reference
- Tool definitions: `agents/learner_tools.py` (`get_my_learning_progress`, `get_my_study_plan`)
- Tool Router Prompt: `agents/tutor_graph.py` (lines 63-90)
- LangGraph ToolNode: `agents/tutor_graph.py` (lines 465-475)

---

## 3. Simplified 15-Minute ReAct Demo
```python
# interview_preparation/react_agent/simple_react.py
import json

def get_my_learning_progress(user_id: str) -> str:
    """Read-only tool: fetches learner scores."""
    return json.dumps({"topic": "loops", "accuracy": 40.0, "status": "needs_revision"})

def run_react_turn(query: str, user_id: str) -> str:
    # 1. Thought
    thought = "User asked about progress; calling get_my_learning_progress."
    # 2. Action
    observation = get_my_learning_progress(user_id)
    # 3. Final Answer
    data = json.loads(observation)
    return f"You currently have {data['accuracy']}% accuracy in {data['topic']}, which {data['status'].replace('_', ' ')}."

if __name__ == "__main__":
    resp = run_react_turn("How am I doing in loops?", "user_123")
    print(resp)
    assert "40.0%" in resp
    print("✅ ReAct interview demo passed.")
```

---

## 4. Mock Interview Questions
- **Q: How does EduPath prevent the model from calling unauthorized administrative tools?**\
  *A:* Tools are strictly whitelisted at graph compilation time (`ToolNode([get_my_learning_progress, get_my_study_plan])`). Unregistered tool names are rejected by LangGraph before execution.
- **Q: Why are database writes prohibited in EduPath's conversational tools?**\
  *A:* LLM outputs are inherently probabilistic. Allowing the conversational model to execute mutations directly against authoritative tables creates risks of accidental data destruction, unauthorized grade changes, or race conditions. All mutations are restricted to deterministic server-side workflows.
