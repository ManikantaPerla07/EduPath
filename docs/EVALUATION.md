# Evaluation & Benchmarking Report — EduPath
**System:** EduPath — Personalized Tutoring Agent\
**Academic Project:** CSE473 Major Project\
**Author:** Perla Manikanta

---

## 1. Evaluation Methodology
EduPath employs a four-tiered evaluation framework to distinguish between code correctness, information retrieval quality, AI generative faithfulness, and agent tool-routing reliability.

---

## 2. Software Test Suite Verification
- **Test Framework:** Pytest 8.x
- **Execution Date:** November 14, 2026
- **Command:** `python -m pytest -q`
- **Result:** **562 passed, 77 subtests passed** (0 failures).
- **Failures / Errors:** 0.

### Test Coverage Highlights:
- `test_learner_service.py`: Google identity claim validation, profile retrieval, profile updates.
- `test_assessment_submission_service.py`: Server-side grading, answer key protection, transactional writes.
- `test_progress_service.py`: Topic progress aggregation, evidence damping factor, mastery thresholds.
- `test_study_plan_service.py`: Topological sorting, prerequisite preservation, study schedule generation.
- `test_few_shot_prompting_service.py`: Level-adaptive exemplar injection across Beginner, Intermediate, and Advanced tiers.
- `test_subjective_evaluation_service.py`: Rubric weights, misconception detection, penalty calculations.
- `test_tutor_graph.py`: LangGraph StateGraph validation, context resolution, tool routing, checkpointing.
- `test_answer_generation_service.py`: Grounding constraints, citation validation, abstention logic.

---

## 3. RAG Retrieval Benchmark (18-Query Golden Dataset)
- **Dataset File:** `evaluation/retrieval_golden_queries.json`
- **Benchmark Runner:** `evaluation/run_retrieval_evaluation.py`
- **Scope:** 18 curated technical queries across all 9 Python course topics (2 queries per topic).
- **Report File:** `retrieval-evaluation.json`

### Verified Retrieval Performance:
| Evaluation Metric | Measured Benchmark Value |
|---|---:|
| **Total Golden Queries** | 18 |
| **Queries Returning Results** | 18 / 18 |
| **Retrieval Coverage** | **100.0%** |
| **Mean Reciprocal Rank (MRR)** | **0.963** |
| **Hit@1** | **94.4%** |
| **Precision@1** | **94.4%** |
| **Hit@3** | **100.0%** |
| **Precision@3** | **94.4%** |
| **Hit@5** | **100.0%** |
| **Precision@5** | **91.1%** |

### Per-Topic Coverage:
All 9 topics achieved **100% Hit@5**:
1. Variables and Data Types: 100%
2. Operators and Expressions: 100%
3. Conditional Statements: 100%
4. Loops: 100%
5. Functions: 100%
6. Lists and Tuples: 100%
7. Dictionaries and Sets: 100%
8. Strings: 100%
9. Basic Problem-Solving: 100%

---

## 4. AI Guardrails & Safety Benchmark
- **Test File:** `experiments/10_safety_evaluation/experiment.py`
- **Test Set:** 7 adversarial and boundary cases across 7 threat vectors:
  - Supported Evidence Utilization: PASS
  - Out-of-Domain Abstention: PASS
  - Fabricated Citation Rejection (`[S99]`): PASS
  - Direct Prompt Injection Defense: PASS
  - Indirect Document Instruction Defense: PASS
  - Cross-Tenant Data Isolation: PASS
  - Server-Side Code Execution Refusal: PASS
- **Pass Rate:** **100.0% (7/7 Passed)**.

---

## 5. Human Learning Pilot Protocol (Pending Deployment)
- **Status:** Protocol prepared for voluntary consenting adult participants (18+).
- **Design:** Pre-test diagnostic assessment $\to$ 3 days of guided adaptive tutoring on weak topics $\to$ post-test evaluation.
- **Ethics & Integrity:** No learner improvement metrics or participant counts are fabricated. Real-world learning gains will be measured strictly following human participant pilot execution.
