#!/usr/bin/env python3
"""
Experiment 07: Collaborative Multi-Agent System (Planner, Reviewer, Coordinator)
CSE473 — Academic Practical (UN SDG 4 / EduPath Major Project)

Objectives:
1. Demonstrate multi-agent collaboration with specialized autonomous roles:
   - Planner Agent: Decomposes a coarse learning objective into sequential milestones.
   - Reviewer Agent: Audits proposed milestones against prerequisite rules and educational rigor.
   - Coordinator Agent: Manages message bus, triggers revisions, and outputs the final certified plan.
2. Implement typed message-passing between agents with structured JSON payloads.
3. Show iterative agent feedback loop: Initial Proposal -> Review Critique -> Revised Plan -> Approval.
"""

from dataclasses import dataclass, asdict
import json
from typing import Any


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    message_type: str  # "PROPOSAL", "CRITIQUE", "REVISION", "APPROVAL"
    payload: dict[str, Any]


class PlannerAgent:
    """Specialized in curriculum goal decomposition."""

    NAME = "CurriculumPlanner"

    def plan(self, learning_goal: str) -> list[dict[str, Any]]:
        # Initial draft proposal (deliberately missing prerequisite check on range)
        return [
            {"step": 1, "topic": "While Loops", "activity": "Write countdown loop", "estimated_minutes": 20},
            {"step": 2, "topic": "Nested Loops", "activity": "Print 2D multiplication table", "estimated_minutes": 35},
            {"step": 3, "topic": "Loop Optimization", "activity": "Benchmark list comprehension vs for loop", "estimated_minutes": 25},
        ]

    def revise(self, original_plan: list[dict[str, Any]], critique: str) -> list[dict[str, Any]]:
        # Incorporate reviewer feedback: insert fundamental for-loop prerequisite first
        return [
            {"step": 1, "topic": "Variables & Conditionals Check", "activity": "Quick diagnostic quiz", "estimated_minutes": 10},
            {"step": 2, "topic": "Basic for loop & range()", "activity": "Iterate over collections and sequences", "estimated_minutes": 20},
            {"step": 3, "topic": "While Loops & Sentinel Values", "activity": "Handle user input loops with break/continue", "estimated_minutes": 25},
            {"step": 4, "topic": "Nested Loops & Comprehensions", "activity": "2D grid traversal and list comprehensions", "estimated_minutes": 30},
        ]


class ReviewerAgent:
    """Specialized in pedagogical audit and prerequisite verification."""

    NAME = "PedagogicalReviewer"

    PREREQUISITES = {
        "While Loops": ["Variables", "Conditionals"],
        "Nested Loops": ["Basic for loop & range()", "While Loops"],
        "Loop Optimization": ["Nested Loops", "Functions"],
    }

    def review(self, proposed_plan: list[dict[str, Any]]) -> tuple[bool, str]:
        topics = [p["topic"] for p in proposed_plan]

        # Audit: Did they introduce Nested Loops before Basic for loop?
        if "Nested Loops" in topics and "Basic for loop & range()" not in topics:
            critique = (
                "REJECTED: The proposed plan introduces 'Nested Loops' without covering "
                "the foundational 'Basic for loop & range()' prerequisite first. "
                "Also, jumping directly to while loops may cause infinite loop bugs for beginners."
            )
            return False, critique

        return True, "APPROVED: Prerequisite order is sound, difficulty progresses smoothly."


class CoordinatorAgent:
    """Orchestrates communication, logs message bus, and issues final certification."""

    NAME = "Coordinator"

    def __init__(self):
        self.planner = PlannerAgent()
        self.reviewer = ReviewerAgent()
        self.message_bus: list[AgentMessage] = []

    def dispatch(self, msg: AgentMessage):
        self.message_bus.append(msg)
        print(f"[{msg.sender} -> {msg.recipient}] ({msg.message_type}):")
        if "critique" in msg.payload:
            print(f"  Feedback: {msg.payload['critique']}")
        elif "plan" in msg.payload:
            for item in msg.payload["plan"]:
                print(f"  Step {item['step']}: {item['topic']} ({item['estimated_minutes']}m) - {item['activity']}")
        print()

    def coordinate_curriculum_design(self, goal: str) -> list[dict[str, Any]]:
        print(f"--- Coordinating Learning Plan for Goal: '{goal}' ---\n")

        # Turn 1: Planner creates draft
        initial_plan = self.planner.plan(goal)
        self.dispatch(AgentMessage(
            sender=self.planner.NAME,
            recipient=self.reviewer.NAME,
            message_type="PROPOSAL",
            payload={"plan": initial_plan},
        ))

        # Turn 2: Reviewer audits draft
        is_approved, critique = self.reviewer.review(initial_plan)
        self.dispatch(AgentMessage(
            sender=self.reviewer.NAME,
            recipient=self.planner.NAME,
            message_type="CRITIQUE" if not is_approved else "APPROVAL",
            payload={"critique": critique, "approved": is_approved},
        ))

        # Turn 3: Planner incorporates critique into revised plan
        if not is_approved:
            revised_plan = self.planner.revise(initial_plan, critique)
            self.dispatch(AgentMessage(
                sender=self.planner.NAME,
                recipient=self.reviewer.NAME,
                message_type="REVISION",
                payload={"plan": revised_plan},
            ))

            # Turn 4: Reviewer second audit
            second_approved, second_critique = self.reviewer.review(revised_plan)
            self.dispatch(AgentMessage(
                sender=self.reviewer.NAME,
                recipient=self.NAME,
                message_type="APPROVAL" if second_approved else "CRITIQUE",
                payload={"critique": second_critique, "approved": second_approved},
            ))
            final_plan = revised_plan
        else:
            final_plan = initial_plan

        return final_plan


def run_experiment():
    print("=" * 75)
    print("EXPERIMENT 07: TWO-AGENT COLLABORATION (PLANNER & REVIEWER)")
    print("=" * 75)

    coordinator = CoordinatorAgent()
    target_goal = "Master Python Loops and Iterations for Beginner College Students"
    final_plan = coordinator.coordinate_curriculum_design(target_goal)

    print("=" * 75)
    print("FINAL CERTIFIED LEARNING PLAN:")
    total_minutes = sum(p["estimated_minutes"] for p in final_plan)
    for p in final_plan:
        print(f"  Step {p['step']}: {p['topic']:<32} | {p['estimated_minutes']} min | {p['activity']}")
    print(f"\nTotal Curriculum Time: {total_minutes} minutes")
    print(f"Total Inter-Agent Messages Exchanged: {len(coordinator.message_bus)}")
    print("=" * 75)
    print("✅ Experiment 07 completed successfully.")


if __name__ == "__main__":
    run_experiment()
