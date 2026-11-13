# CSE473 Academic Practicals & Experiments Portfolio
**Course:** CSE473 Major Project\
**Student Developer:** Perla Manikanta\
**Project:** EduPath — Personalized Tutoring Agent\
**Initiative & SDG:** Google Solution Challenge | UN SDG 4 (Quality Education)

---

## 1. Overview of All 10 Practicals
Each experiment is self-contained in the `experiments/` directory, complete with executable code, documentation, theoretical formulation, and reproducible output logs. All experiments execute deterministically in the local virtual environment (`.venv`) with zero heavyweight external GPU or paid cloud API dependencies.

| Practical ID | Directory | Core Concept | Execution Status | Key Output Metric |
|---|---|---|---|---|
| **EXP-01** | `experiments/01_tokenization_attention/` | Token IDs & Scaled Dot-Product Attention Map | Verified | ASCII Attention Heatmap & Normalized Weights |
| **EXP-02** | `experiments/02_prompt_engineering/` | Zero-Shot vs Few-Shot vs Structured vs CoT | Verified | 4-way Comparative Pedagogical Rubric (1-5) |
| **EXP-03** | `experiments/03_goal_based_agent/` | Goal-Directed Navigation with Prerequisite Obstacles | Verified | BFS Path Finding (6 optimal steps) |
| **EXP-04** | `experiments/04_lora_finetuning/` | Parameter-Efficient Fine-Tuning (LoRA $\Delta W = B \cdot A$) | Verified | 99.2% Parameter Reduction & 92.3% Loss Drop |
| **EXP-05** | `experiments/05_q_learning/` | Q-Learning with Potential-Based Reward Shaping | Verified | Convergence in 12 steps (Ng et al. 1999) |
| **EXP-06** | `experiments/06_faiss/` | FAISS IndexFlatL2 & IndexFlatIP Vector Search | Verified | Top-K Retrieval on Python Curriculum |
| **EXP-07** | `experiments/07_multi_agent/` | Collaborative Multi-Agent System (Planner & Reviewer) | Verified | 4-Turn Critique & Prerequisite Revision Loop |
| **EXP-08** | `experiments/08_rag/` | End-to-End RAG Pipeline with Overlap & Abstention | Verified | Grounded Citation `[S1]` & `INSUFFICIENT_EVIDENCE` |
| **EXP-09** | `experiments/09_react_agent/` | ReAct (Reasoning + Acting) Multi-Tool Execution | Verified | 3-Step Chained Diagnostic Trace |
| **EXP-10** | `experiments/10_safety_evaluation/` | AI Safety Guardrails & Adversarial Attack Evaluation | Verified | 100% Pass Rate across 7 Threat Vectors |

---

## 2. Academic Distinctions & Engineering Realities

To maintain absolute academic honesty and rigor in evaluation, the following engineering distinctions differentiate the pedagogical experiments from full-scale production infrastructure:

### 2.1 NumPy Layer-Level LoRA Optimization vs. Full Hugging Face PEFT Model Fine-Tuning
- **In EXP-04 (Experiment):** A custom `LoRALinearLayer` implemented in pure NumPy simulates low-rank adaptation on a single projection layer. Base weights $W_0 \in \mathbb{R}^{4 \times 8}$ remain strictly frozen ($0.0000$ change), while adapter matrices $B \in \mathbb{R}^{4 \times 2}$ and $A \in \mathbb{R}^{2 \times 8}$ are optimized via 50 gradient descent steps, reducing MSE loss from $0.2868$ to $0.0221$ ($92.29\%$ drop). Analytical equations demonstrate that for a 7B Transformer ($d=4096, 32$ layers, rank $r=16$), LoRA reduces $2.147$ billion attention weights to $16.78$ million adapter parameters ($99.22\%$ parameter savings).
- **In Industry / Full PEFT:** Training an actual 7B model requires multi-GPU infrastructure, PyTorch, Hugging Face `transformers` and `peft`, 16-bit or 4-bit quantization (QLoRA), and distributed data loaders. **A 7B model is not instantiated or trained on GPU in this project**; the practical provides a mathematically exact layer-level gradient descent simulation and parameter scaling analysis.

### 2.2 NumPy Vector-Search Fallback vs. Native FAISS
- **In EXP-06 (Experiment):** The script attempts to import native `faiss`. To maintain zero-dependency Windows execution without requiring C++ compilers or platform-specific wheels, it automatically activates the built-in `SimulatedFAISSIndexFlatL2` and `SimulatedFAISSIndexFlatIP` NumPy fallback. It indexes 28 educational sentences (187-dimensional term frequency vectors) and computes exact L2 distance and Cosine inner products.
- **In Production EduPath:** Vector storage and similarity retrieval are handled by **Neon PostgreSQL with `pgvector 0.8.6`** using Google `gemini-embedding-2` (768 dimensions) with ACID transactions and SQL relational filtering (`WHERE course_id = ... AND c.is_published = TRUE`).

### 2.3 TF-IDF Lexical RAG vs. Production Dense Neural-Embedding RAG
- **In EXP-08 (Experiment):** Retrieval is computed using a pure Python bag-of-words Term Frequency-Inverse Document Frequency (TF-IDF) sparse vectorizer over 7 chunks created from 3 OpenStax notes. It demonstrates chunking, citation tagging (`[S1]`, `[S2]`), and domain boundary enforcement (`INSUFFICIENT_EVIDENCE` when similarity $< 0.25$).
- **In Production EduPath:** Dense semantic retrieval uses continuous 768-dimensional neural vector embeddings (`gemini-embedding-2`), allowing semantic matching even when queries share no exact vocabulary keywords with the source textbook.

### 2.4 Deterministic Tool Chaining vs. LLM-Driven ReAct
- **In EXP-09 (Experiment):** The ReAct trace demonstrates the canonical `Thought -> Action -> Observation -> Final Answer` loop (Yao et al., 2022). The 3 tool executions (`get_learner_progress`, `compute_mastery_status`, `get_topic_prerequisites`) execute authentic Python functions with JSON schema validation and read-only authorization. However, the sequence is executed deterministically in Python rather than letting an external LLM dynamically pick tools at runtime.
- **In Production EduPath:** The tutoring workflow is orchestrated via **LangGraph stateful graph nodes** (`retrieve_context`, `generate_answer`, `format_teaching_guidance`), ensuring robust determinism and preventing uncontrolled agent loops.

### 2.5 Independent Experiment Dataset vs. Production Knowledge-Base Sources
- **In Experiments (EXP-01 through EXP-10):** Standalone pedagogical experiments use self-contained educational snippet dictionaries (e.g., sample OpenStax loop excerpts in `experiments/08_rag/` and `safety_test_cases.json` in `experiments/10_safety_evaluation/`). OpenStax serves as an external open educational resource for experimental benchmarking.
- **In Production Knowledge Base:** The production Neon PostgreSQL database contains **11 active, ready curriculum documents** and **47 retrievable chunks**, 100% embedded using Google `gemini-embedding-2` (768 dimensions) via `pgvector 0.8.6`. All 11 documents are original, verified educational notes authored specifically for the EduPath project (`source_license = 'Original — EduPath project'`, `rights_basis = 'original'`). OpenStax textbooks were evaluated as reference literature but were never bulk-ingested into the production database.

---

## 3. Running All Experiments
To execute any experiment from the repository root:
```powershell
.venv\Scripts\python.exe experiments/<directory_name>/experiment.py
```
For example:
```powershell
.venv\Scripts\python.exe experiments/04_lora_finetuning/experiment.py
.venv\Scripts\python.exe experiments/06_faiss/experiment.py
.venv\Scripts\python.exe experiments/08_rag/experiment.py
.venv\Scripts\python.exe experiments/09_react_agent/experiment.py
.venv\Scripts\python.exe experiments/10_safety_evaluation/experiment.py
```
All 10 experiments execute with exit code 0.
