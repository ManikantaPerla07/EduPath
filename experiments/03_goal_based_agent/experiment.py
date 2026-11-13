#!/usr/bin/env python3
"""
Experiment 03: Goal-Based Agent in a Deterministic Educational Grid Environment
CSE473 — Academic Practical (UN SDG 4 / EduPath Major Project)

Objectives:
1. Define formal agent architecture:
   - State Space S: (row, col) coordinates representing learning mastery stages.
   - Action Space A: {Up, Down, Left, Right} navigation moves.
   - Percept: Current location, obstacle feedback, distance to goal.
   - Goal Formulation G: Specific target concept node (e.g., Target Topic: 'Functions').
2. Implement Goal-Directed Planning (Breadth-First Search / A* Search).
3. Demonstrate perception-deliberation-action execution cycle until goal achievement.
"""

from collections import deque
from typing import NamedTuple


class State(NamedTuple):
    r: int
    c: int


class GoalBasedAgent:
    """A goal-directed agent with explicit state modeling, goal testing, and planning."""

    GRID_SIZE = 5
    # Obstacles represent prerequisite blockers or unassessed prerequisites
    OBSTACLES = {State(1, 1), State(1, 2), State(2, 3), State(3, 1)}

    ACTIONS = {
        "UP": State(-1, 0),
        "DOWN": State(1, 0),
        "LEFT": State(0, -1),
        "RIGHT": State(0, 1),
    }

    TOPIC_LABELS = {
        State(0, 0): "Variables",
        State(0, 2): "Operators",
        State(0, 4): "Conditionals",
        State(2, 0): "Loops",
        State(2, 4): "Functions (GOAL)",
        State(4, 4): "Dictionaries",
    }

    def __init__(self, initial_state: State, goal_state: State):
        self.current_state = initial_state
        self.goal_state = goal_state
        self.history: list[State] = [initial_state]
        self.plan: list[str] = []

    def is_valid(self, s: State) -> bool:
        """Check grid boundaries and obstacle collisions."""
        return (
            0 <= s.r < self.GRID_SIZE
            and 0 <= s.c < self.GRID_SIZE
            and s not in self.OBSTACLES
        )

    def formulate_plan(self) -> list[str]:
        """Breadth-First Search (BFS) for optimal path to the goal."""
        queue: deque[tuple[State, list[str]]] = deque([(self.current_state, [])])
        visited = {self.current_state}

        while queue:
            curr, path = queue.popleft()

            if curr == self.goal_state:
                self.plan = path
                return path

            for action_name, delta in self.ACTIONS.items():
                next_state = State(curr.r + delta.r, curr.c + delta.c)
                if self.is_valid(next_state) and next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [action_name]))

        return []

    def step(self) -> bool:
        """Execute one planned action towards the goal."""
        if not self.plan:
            return True  # Done or stuck

        next_action = self.plan.pop(0)
        delta = self.ACTIONS[next_action]
        self.current_state = State(self.current_state.r + delta.r, self.current_state.c + delta.c)
        self.history.append(self.current_state)
        return self.current_state == self.goal_state

    def render(self):
        """Render ASCII grid map."""
        print("\n  " + "  ".join(str(c) for c in range(self.GRID_SIZE)))
        for r in range(self.GRID_SIZE):
            row_str = f"{r} "
            for c in range(self.GRID_SIZE):
                s = State(r, c)
                if s == self.current_state:
                    ch = "🤖"  # Agent
                elif s == self.goal_state:
                    ch = "🎯"  # Goal
                elif s in self.OBSTACLES:
                    ch = "🧱"  # Blocker
                elif s in self.history:
                    ch = "··"  # Path
                else:
                    ch = "⬜"  # Open
                row_str += f"{ch:<3}"
            print(row_str)


def run_experiment():
    print("=" * 75)
    print("EXPERIMENT 03: GOAL-BASED AGENT IN AN EDUCATIONAL TOPIC SPACE")
    print("=" * 75)

    start_state = State(0, 0)
    target_state = State(2, 4)

    agent = GoalBasedAgent(initial_state=start_state, goal_state=target_state)

    print(f"Agent Start: {start_state} ({agent.TOPIC_LABELS.get(start_state, 'Start')})")
    print(f"Agent Goal:  {target_state} ({agent.TOPIC_LABELS.get(target_state, 'Goal')})")
    print(f"Obstacles (Unmet Prerequisites): {list(agent.OBSTACLES)}\n")

    print("Phase 1: Deliberation & Planning (BFS Search)...")
    plan = agent.formulate_plan()
    print(f"Generated Optimal Plan ({len(plan)} actions): {' -> '.join(plan)}\n")

    print("Initial Environment State:")
    agent.render()

    print("\nPhase 2: Execution Trace...")
    step_num = 1
    while agent.plan:
        action = agent.plan[0]
        reached = agent.step()
        print(f"Step {step_num}: Action={action} -> Current Position={agent.current_state}")
        step_num += 1

    print("\nFinal State (Goal Achieved!):")
    agent.render()

    print("\n" + "=" * 75)
    print(f"Goal Reached: {agent.current_state == agent.goal_state}")
    print(f"Total Trajectory Length: {len(agent.history) - 1} steps")
    print("✅ Experiment 03 completed successfully.")


if __name__ == "__main__":
    run_experiment()
