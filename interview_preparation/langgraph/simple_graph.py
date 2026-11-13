#!/usr/bin/env python3
"""Simplified LangGraph StateGraph Demo for Technical Interviews."""

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
    return {"answer": f"Here is your personal progress for '{state['question']}'."}


def course_node(state: SimpleState):
    return {"answer": f"Here is the Python concept explanation for '{state['question']}'."}


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
    res_personal = graph.invoke({"question": "loops", "is_personal": True})
    print("Personal Route:", res_personal["answer"])
    assert "personal progress" in res_personal["answer"]

    res_course = graph.invoke({"question": "functions", "is_personal": False})
    print("Course Route:  ", res_course["answer"])
    assert "concept explanation" in res_course["answer"]

    print("✅ LangGraph interview test passed.")
