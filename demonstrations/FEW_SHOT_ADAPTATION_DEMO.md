# EduPath — Few-Shot Personalization Across 3 Difficulty Levels
## Demonstration Deliverable for CSE473 Major Project (UN SDG 4)

### 1. Assignment Context & Requirement
The official allocation for **EduPath — Personalized Tutoring Agent** states:
> *"Build a tutor that adapts its explanation style using a few examples of a student's level/mistakes (few-shot), and show it adjusts across 2–3 difficulty levels."*

EduPath implements this via **in-context few-shot demonstration learning**, combining:
1. **Dynamic Mastery Detection**: Evaluates learner assessment attempts and accuracy from Neon PostgreSQL.
2. **Teaching Strategy Mapping**: Selects pedagogical strategy (`beginner`, `intermediate`, `advanced`).
3. **Curated Few-Shot Demonstrations**: Injects curated exemplars illustrating how to address specific misconceptions and calibrate explanation depth.

---

### 2. Side-by-Side Demonstration of Identical Concept
**Query:** *"How does a for loop work with range in Python?"*

#### Level 1: Beginner (Foundational & Analogy-Driven)
- **Target Persona:** Novice learner needing concrete mental models.
- **Common Misconception Addressed:** Believing `range(1, 5)` includes `5` (off-by-one).
- **Explanation:**
  > Think of a for loop like an automated checklist or an assembly line [S1]. Each time the loop runs, it picks up the next item and does a task with it.
  >
  > **Analogy:** Imagine a chef making 4 pancakes. You tell the chef to count from 1 up to (but stopping before) 5.
  > ```python
  > for count in range(1, 5):
  >     print(f"Pancake #{count}")
  > ```
  > **Common Gotcha:** Notice that `range(1, 5)` stops right before 5! It outputs 1, 2, 3, and 4 [S1].
  > **Hint:** The second number in `range(start, stop)` is always the stop line you don't cross.
  > **Quick Practice:** What will `range(1, 4)` print? Try it out!

---

#### Level 2: Intermediate (Syntax & Execution Flow)
- **Target Persona:** Developing programmer with basic knowledge, needing syntax precision.
- **Common Misconception Addressed:** Mutating sequences during iteration or using `range(len())` anti-patterns.
- **Explanation:**
  > In Python, a `for` loop iterates over items produced by an iterable [S1]. The `range([start], stop[, step])` function returns an immutable sequence of integers [S1].
  >
  > **Execution Mechanics:**
  > 1. `range(start, stop, step)` generates integers starting at `start`.
  > 2. It increments by `step` on each iteration until the next value equals or exceeds `stop`.
  > 3. In each iteration, the loop variable is assigned the next sequence element.
  > ```python
  > numbers = [10, 20, 30, 40]
  > # Pythonic direct iteration:
  > for num in numbers:
  >     print(num * 2)
  >
  > # When index is needed, prefer enumerate over range(len()):
  > for idx, num in enumerate(numbers):
  >     print(f"Index {idx}: {num}")
  > ```
  > **Common Pitfall:** Never call `.remove()` or `.append()` on a list while iterating over it directly.
  > **Exercise:** Write a loop using `range()` that prints all even numbers between 10 and 20 (inclusive) in reverse order.

---

#### Level 3: Advanced (Underlying Architecture & Edge Cases)
- **Target Persona:** Mastery candidate ready for systems-level mechanics.
- **Common Misconception Addressed:** Treating range as in-memory list; iterator exhaustion subtleties.
- **Explanation:**
  > Under the hood, Python's `for` loop implements the **Iterator Protocol** [S1]. When executing `for x in obj:`, Python calls `iter(obj)` to obtain an iterator, then repeatedly invokes `next()` on it until `StopIteration` is raised [S1].
  >
  > **Range Object Characteristics:**
  > - `range` in Python 3 is a lazy sequence type, taking $O(1)$ memory regardless of size ($10^6$ vs $10^9$).
  > - It supports $O(1)$ `__contains__` membership testing and indexing via arithmetic rather than table storage.
  > ```python
  > iterator = iter(range(3))
  > while True:
  >     try:
  >         val = next(iterator)
  >         print(val)
  >     except StopIteration:
  >         break
  > ```
  > **Edge Case / Challenge:** What happens if you define a custom class implementing `__iter__` that returns `self` without defining `__next__`? Implement a memory-efficient generator that yields Fibonacci numbers up to $N$ with $O(1)$ auxiliary space.

---

### 3. Comparison Matrix
| Pedagogical Dimension | Beginner (Level 1) | Intermediate (Level 2) | Advanced (Level 3) |
|---|---|---|---|
| **Core Metaphor** | Chef making pancakes | Sequence generator | Iterator protocol (`iter()` / `next()`) |
| **Code Structure** | 4-line print loop | Multi-line with `enumerate` | Low-level `while` + `StopIteration` |
| **Misconception Focus** | Off-by-one boundary | Mutating collection in-flight | Memory overhead & lazy evaluation |
| **Practice Challenge** | Predict `range(1, 4)` | Reverse sequence with step | $O(1)$ space Fibonacci generator |
| **Theoretical Depth** | Intuitive stop-line | Step arithmetic & indexing | Time & space complexity |

---

### 4. Reproducibility
To run this demonstration at any time:
```bash
python demonstrations/few_shot_adaptation_demo.py
```
No external API keys or network connection required.
