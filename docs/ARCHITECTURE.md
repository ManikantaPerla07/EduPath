# System Architecture & Technical Design — EduPath
**System:** EduPath — Personalized Tutoring Agent\
**Academic Project:** CSE473 Major Project\
**Author:** Perla Manikanta

---

## 1. High-Level Architectural Overview
EduPath is structured as a **modular Python monolith**. It avoids unnecessary microservice complexity, API gateways, or dual-language runtimes, adhering strictly to the project's **₹0 budget principle**.

```mermaid
flowchart TD
    User([Learner Browser]) <-->|HTTPS / WebSockets| UI[Streamlit UI Presentation Layer]

    subgraph UI_Layer [Streamlit Application]
        UI --> Nav[Navigation Router]
        Nav --> P_Dash[Dashboard]
        Nav --> P_Prof[Learner Profile]
        Nav --> P_Tutor[AI Tutor Chat]
        Nav --> P_Assess[Assessments]
        Nav --> P_Plan[Study Plan]
        Nav --> P_Admin[Knowledge Management]
    end

    subgraph Service_Layer [Core Service Layer]
        P_Prof --> S_Learn[Learner Service]
        P_Assess --> S_Assess[Assessment & Grading Services]
        P_Plan --> S_Plan[Study Plan Service]
        S_Assess --> S_Prog[Progress Service]
        S_Prog --> S_Adapt[Adaptive Learning Service]
        P_Admin --> S_Doc[Document & Embedding Services]
    end

    subgraph Agent_Layer [LangGraph Orchestration & RAG]
        P_Tutor --> Graph[Tutor StateGraph Engine]
        Graph --> Node_Val[validate_input]
        Node_Val --> Node_Res[resolve_context]
        Node_Res --> Node_Tools{decide_learner_tools}
        Node_Tools -->|Personal Query| Tool_Node[Learner Tools Execution]
        Node_Tools -->|Course Query| Node_Ret[retrieve_context]
        Node_Ret --> Node_Adapt[adapt_teaching]
        Node_Adapt --> FewShot[Few-Shot Exemplars]
        FewShot --> Node_Ans[generate_answer]
        Node_Ret -->|No Chunks| Node_Abs[abstain]
    end

    subgraph Data_Layer [Neon PostgreSQL Database]
        S_Learn <--> Rel_DB[(PostgreSQL Relational Tables)]
        S_Assess <--> Rel_DB
        S_Plan <--> Rel_DB
        S_Prog <--> Rel_DB
        Node_Ret <--> Vec_DB[(pgvector document_chunks)]
        Graph <--> Checkpoints[(LangGraph Checkpoint Tables)]
    end

    subgraph Cloud_AI [Google Cloud AI]
        S_Doc <-->|Generate Embeddings 768d| Gem_Emb[Gemini Embedding 2]
        Node_Ans <-->|Grounded Prompting| Gem_Chat[Gemini 3.8 Flash / 3.5 Lite]
    end
```

---

## 2. LangGraph StateGraph Workflow
The tutoring conversation is orchestrated via a stateful `StateGraph` in `agents/tutor_graph.py`:

```mermaid
stateDiagram-v2
    [*] --> validate_input
    validate_input --> resolve_context

    state "decide_learner_tools (Gemini)" as decide_tools
    resolve_context --> decide_tools

    decide_tools --> learner_tools: Tool calls emitted
    decide_tools --> retrieve_context: No tool calls needed

    learner_tools --> collect_learner_context
    collect_learner_context --> generate_answer

    state "retrieve_context (pgvector)" as retrieve_context
    retrieve_context --> adapt_teaching: Chunks found
    retrieve_context --> abstain: No chunks & no learner context

    adapt_teaching --> generate_answer: Guidance + Few-Shot Exemplars attached
    generate_answer --> [*]
    abstain --> [*]
```

### Node Responsibilities:
1. `validate_input`: Verifies length ($L \le 2000$), presence of non-empty text, and sanitizes strings.
2. `resolve_context`: Uses recent conversation history to convert ambiguous follow-ups (e.g. *"Can you give an example of that?"*) into standalone search queries.
3. `decide_learner_tools`: Binds read-only tools (`get_my_learning_progress`, `get_my_study_plan`) and lets Gemini route personal questions.
4. `retrieve_context`: Queries `document_chunks` via `NeonPgVectorRetriever` using cosine distance (`<=>`).
5. `adapt_teaching`: Inspects learner topic progress and injects targeted few-shot exemplars from `services/few_shot_prompting_service.py`.
6. `generate_answer`: Executes grounded prompt template with citation parser `[S1]`, `[S2]`.
7. `abstain`: Returns safe fallback `INSUFFICIENT_EVIDENCE` when evidence is missing.

---

## 3. Memory Architecture
EduPath maintains two strictly decoupled memory tiers:
1. **Short-Term Conversational Memory:**
   - Thread checkpoints managed by `langgraph-checkpoint-postgres` in `checkpoints` and `checkpoint_writes` tables.
   - Allows multi-turn conversation restoration across browser refreshes.
2. **Long-Term Learner Knowledge State:**
   - Authoritative relational schema in Neon PostgreSQL:
     - `learner_profiles`: Learning goals, proficiency tier, daily schedule.
     - `learner_topic_progress`: Historical attempts, correct answers, accuracy, mastery scores.
     - `study_plans` & `study_plan_items`: Sequenced learning activities.
     - `chat_messages`: Persisted learner and assistant transcripts with citation metadata.

---

## 4. Grounded RAG Pipeline Architecture
```mermaid
sequenceDiagram
    autonumber
    actor Learner
    participant UI as Streamlit UI
    participant Graph as LangGraph Agent
    participant Ret as Neon pgvector
    participant LLM as Google Gemini

    Learner->>UI: Submits question ("How does range work?")
    UI->>Graph: Invokes run_tutor_graph()
    Graph->>Ret: Cosine search over document_chunks
    Ret-->>Graph: Returns Top-K relevant chunks with metadata
    Graph->>Graph: Injects Few-Shot Exemplars matching learner level
    Graph->>LLM: Formulates grounded prompt with [S1], [S2] constraints
    LLM-->>Graph: Generates response with citations
    Graph->>Graph: Validates cited IDs against allowed lookup
    Graph-->>UI: Returns verified answer + citation cards
    UI-->>Learner: Renders interactive response with expandable sources
```
