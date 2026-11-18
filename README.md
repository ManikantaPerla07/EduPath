<div align="center">

<a href="https://edupath-perla-demo.streamlit.app/">
  <img src="https://raw.githubusercontent.com/ManikantaPerla07/EduPath/feature/unify-langchain-retrieval/docs/assets/edupath-banner.svg" alt="EduPath — Personalized AI Learning Space" width="100%">
</a>

<h2>Personalized learning, grounded answers, measurable progress.</h2>

<p>
  An AI-powered Python learning companion that combines learner-aware tutoring,
  retrieval-augmented generation, adaptive practice, and personalized study planning.
</p>

<p>
  <a href="https://edupath-perla-demo.streamlit.app/">
    <img src="https://img.shields.io/badge/Launch-Live_Demo-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Launch live demo">
  </a>
  <a href="https://github.com/ManikantaPerla07/EduPath/tree/feature/unify-langchain-retrieval">
    <img src="https://img.shields.io/badge/Explore-Source_Code-181717?style=for-the-badge&logo=github&logoColor=white" alt="Source code">
  </a>
  <a href="https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/ARCHITECTURE.md">
    <img src="https://img.shields.io/badge/Architecture-View_Docs-5965E8?style=for-the-badge" alt="Architecture documentation">
  </a>
</p>

<p>
  <a href="https://github.com/ManikantaPerla07/EduPath/stargazers"><img src="https://img.shields.io/github/stars/ManikantaPerla07/EduPath?style=social" alt="GitHub stars"></a>
  <a href="https://github.com/ManikantaPerla07/EduPath/network/members"><img src="https://img.shields.io/github/forks/ManikantaPerla07/EduPath?style=social" alt="GitHub forks"></a>
  <a href="https://img.shields.io/github/last-commit/ManikantaPerla07/EduPath/feature/unify-langchain-retrieval"><img src="https://img.shields.io/github/last-commit/ManikantaPerla07/EduPath/feature/unify-langchain-retrieval?label=last%20update" alt="Last update"></a>
  <a href="https://github.com/ManikantaPerla07/EduPath/issues"><img src="https://img.shields.io/github/issues/ManikantaPerla07/EduPath?label=open%20issues" alt="Open issues"></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/LangChain-Orchestration-1C3C3C?logo=chainlink&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/LangGraph-Agent_Workflow-1C3C3C" alt="LangGraph">
  <img src="https://img.shields.io/badge/Google_Gemini-LLM-4285F4?logo=google&logoColor=white" alt="Google Gemini">
  <img src="https://img.shields.io/badge/Groq-Model_Failover-F55036" alt="Groq">
  <img src="https://img.shields.io/badge/Neon-PostgreSQL-00E599?logo=neon&logoColor=black" alt="Neon PostgreSQL">
  <img src="https://img.shields.io/badge/pgvector-Semantic_Search-2F6F8F" alt="pgvector">
  <img src="https://img.shields.io/badge/Hosting-Streamlit_Community_Cloud-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit Community Cloud">
</p>

</div>

> **Current source branch:** [feature/unify-langchain-retrieval](https://github.com/ManikantaPerla07/EduPath/tree/feature/unify-langchain-retrieval)  
> The live demo is deployed from this branch. Use it when cloning the current implementation.

---

## ✨ What is EduPath?

**EduPath** is a personalized AI tutoring platform, currently focused on beginner Python programming. It brings together a source-grounded AI tutor, diagnostic and adaptive assessments, learner progress analytics, misconception tracking, and prerequisite-aware study planning.

Traditional learning platforms often deliver the same explanation and practice sequence to every learner. EduPath instead uses a learner's preferences and assessment evidence to adapt explanations, identify weaker topics, and recommend a practical next step.

**Core idea:** make learning adaptive while keeping factual tutoring answers traceable to approved learning resources.

## 📌 Project snapshot

<table>
  <tr>
    <td align="center" width="25%">
      <h2>9</h2>
      <b>Python topics</b><br>
      <sub>Structured beginner curriculum</sub>
    </td>
    <td align="center" width="25%">
      <h2>27</h2>
      <b>Assessment questions</b><br>
      <sub>Diagnostic question bank</sub>
    </td>
    <td align="center" width="25%">
      <h2>3</h2>
      <b>Teaching levels</b><br>
      <sub>Beginner · Intermediate · Advanced</sub>
    </td>
    <td align="center" width="25%">
      <h2>18</h2>
      <b>Retrieval test queries</b><br>
      <sub>Two per Python topic</sub>
    </td>
  </tr>
</table>

## 🚀 Feature highlights

### 1. Learner-aware personalization
- **Learner profile:** save proficiency, preferred explanation style, language, learning goals, and daily study availability.
- **Diagnostic assessment:** establish a baseline across the nine Python topics using the 27-question bank.
- **Adaptive practice:** select practice questions using topic mastery and recent attempts.
- **Targeted revision:** prioritize weaker topics and adjust practice difficulty.
- **Progress analytics:** track attempts, accuracy, topic-level evidence, and learning status.
- **Personalized study plans:** organize learning, practice, and revision around prerequisites, goals, and available time.

### 2. Grounded AI tutoring with RAG
- **Semantic retrieval:** retrieve relevant course chunks from Neon PostgreSQL using Gemini Embedding 2 vectors stored in pgvector.
- **Source-linked explanations:** provide citations tied to the retrieved material.
- **Citation validation:** accept only source identifiers available to the current response.
- **Evidence-aware abstention:** return an insufficient-evidence response when approved course material cannot support an answer.
- **Adaptive teaching:** vary explanation depth and examples for beginner, intermediate, and advanced learners.

### 3. Agentic orchestration with LangGraph
- Resolve conversation context before answering follow-up questions.
- Route learner-specific questions to read-only progress and study-plan tools.
- Retrieve course evidence for curriculum questions.
- Combine learner context, retrieved sources, and teaching-level examples before answer generation.
- Persist conversation checkpoints in PostgreSQL.

### 4. Multi-provider model resilience
- **Primary generation:** Google Gemini.
- **Model fallback:** try an alternate Gemini model for eligible transient failures.
- **Secondary provider:** Groq provides another generation path when configured and eligible for failover.
- **Provider attribution:** record and surface which provider/model generated the response.

### 5. Learning memory and knowledge management
- Persistent chat history and LangGraph checkpoints.
- Learner-specific misconception records to guide future revision.
- Tutor answer feedback and course-level operational insights.
- Administrator workflow to upload PDF, TXT, and Markdown resources, map resources to topics, inspect extraction/chunking/embedding status, retry processing, archive resources, and review publication readiness.

### 6. Privacy and responsible AI
- Explicit AI consent is required before learner content is sent to external model providers; consent defaults to denied.
- Adult self-confirmation is required for the intended 18+ audience. It is a self-attestation, not third-party age verification.
- Learner access is scoped using authenticated identity and application/service-layer authorization.
- Learner-submitted Python code is not executed on the server.
- Retrieved documents and learner inputs are treated as untrusted data, not system instructions.

## 🧭 How the learner journey works

1. **Sign in** with Google and set learning preferences.
2. **Take a diagnostic** to establish a starting point across the Python topics.
3. **Review progress** to understand topic-level attempts and accuracy.
4. **Follow a study plan** shaped by prerequisites, learning goals, and available time.
5. **Ask the AI Tutor** for explanations grounded in approved course resources.
6. **Practice and improve** through adaptive questions, targeted revision, and misconception feedback.

## 🏗️ System architecture

EduPath is a modular Python application. Streamlit provides the learner and administrator interfaces; deterministic Python services handle grading, authorization, planning, and persistence; LangGraph coordinates the tutoring workflow.

~~~mermaid
flowchart TD
    Learner([Learner]) --> UI[Streamlit application]
    UI --> Auth[Google OIDC and learner profile]
    UI --> Assess[Diagnostic and adaptive assessment]
    UI --> Plan[Personalized study plan]
    UI --> Tutor[AI Tutor]
    Assess --> Progress[Progress and misconception services]
    Plan --> Progress

    Tutor --> Graph[LangGraph tutor workflow]
    Graph --> Context[Context resolution]
    Context -->|Learner-specific question| Tools[Read-only learner tools]
    Tools --> DB[(Neon PostgreSQL)]
    Context -->|Course question| Retrieval[Course retrieval]
    Retrieval --> Vector[(pgvector document chunks)]
    Retrieval --> Adapt[Few-shot teaching adaptation]
    Adapt --> Gemini[Gemini generation]
    Gemini -.->|Eligible transient failure| Groq[Groq secondary provider]
    Gemini --> Guard[Citation validation and abstention]
    Groq --> Guard
    Guard --> UI

    Auth --> DB
    Assess --> DB
    Plan --> DB
    Progress --> DB
    Graph <--> Checkpoints[(LangGraph checkpoints)]
~~~

### Technology stack

| Layer | Technologies |
|---|---|
| Application and UI | Python 3.11, Streamlit |
| LLM orchestration | LangChain, LangGraph |
| Primary generation | Google Gemini |
| Secondary generation | Groq |
| Embeddings | Gemini Embedding 2, 768 dimensions |
| Retrieval | RAG, cosine similarity, PostgreSQL pgvector |
| Database and memory | Neon PostgreSQL, LangGraph PostgreSQL checkpointer |
| Authentication | Google OpenID Connect through Streamlit authentication |
| Document processing | pypdf, LangChain text splitters/loaders |
| Testing | Python unittest suite |
| Hosting | Streamlit Community Cloud |

## 📊 Retrieval evaluation

The repository contains a repeatable **18-query golden benchmark**: two curated queries for each of the nine Python topics. The evaluator checks whether retrieved chunks match the expected topic metadata.

<div align="center">
  <img src="https://img.shields.io/badge/Retrieval_Coverage-100.0%25-239B56?style=for-the-badge" alt="Retrieval coverage 100%">
  <img src="https://img.shields.io/badge/MRR-0.963-2874A6?style=for-the-badge" alt="MRR 0.963">
  <img src="https://img.shields.io/badge/Hit%401-94.4%25-7D3C98?style=for-the-badge" alt="Hit at 1 94.4%">
  <img src="https://img.shields.io/badge/Hit%405-100%25-239B56?style=for-the-badge" alt="Hit at 5 100%">
</div>

| Metric | Result |
|---|---:|
| Golden queries | 18 |
| Queries returning results | 18 / 18 |
| Retrieval coverage | **100.0%** |
| Mean Reciprocal Rank (MRR) | **0.963** |
| Hit@1 | **94.4%** |
| Hit@3 | **100.0%** |
| Hit@5 | **100.0%** |

**How to interpret these numbers:** a retrieved chunk is considered relevant when its topic slug matches the query's expected topic. This is a small retrieval-alignment benchmark; it does **not** measure answer factuality, citation faithfulness, teaching quality, or learner outcomes.

- [Evaluation methodology](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/EVALUATION.md)
- [Golden query set](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/evaluation/retrieval_golden_queries.json)
- [Machine-readable benchmark report](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/retrieval-evaluation.json)

### Software and safety checks

<img src="https://img.shields.io/badge/Unit_Tests-639_passed-239B56?style=flat" alt="639 unit tests passed">
<img src="https://img.shields.io/badge/Safety_Scenarios-7%2F7_passed-239B56?style=flat" alt="7 of 7 safety scenarios passed">

The latest recorded local regression run completed **639 tests with zero failures on November 18, 2026**. The repository's safety experiment also reports 7 of 7 defined boundary/adversarial scenarios passing. These are project test results—not a hosted CI status, independent security audit, or proof of real-world learning gains.

Run the test suite locally:

~~~powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q app.py ui services agents tests
git diff --check
~~~

## 🌐 Live application

<div align="center">

[![Open EduPath](https://img.shields.io/badge/OPEN_EDUPATH-Launch_the_live_app-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://edupath-perla-demo.streamlit.app/)

**https://edupath-perla-demo.streamlit.app/**

</div>

The hosted demo uses Google sign-in, Neon PostgreSQL, and configured Gemini/Groq credentials. AI tutoring requires explicit learner consent. Provider availability and free-tier quotas can change; a free-tier setup does not guarantee uninterrupted service.

## 💻 Run locally

### Prerequisites

- Python 3.11 and Git
- PostgreSQL with the pgvector extension (Neon is used by the hosted project)
- Google Gemini API key
- Google OAuth/OIDC credentials for sign-in
- Groq API key for secondary-provider failover (optional but recommended)

### 1. Clone the implementation branch

~~~powershell
git clone --branch feature/unify-langchain-retrieval --single-branch https://github.com/ManikantaPerla07/EduPath.git
cd EduPath
~~~

### 2. Create an environment and install dependencies

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
~~~

### 3. Configure local secrets

~~~powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
~~~

Edit the local **.streamlit/secrets.toml** file with your own credentials:

~~~toml
DATABASE_URL = "YOUR_DEVELOPMENT_DATABASE_URL"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GROQ_API_KEY = "YOUR_GROQ_API_KEY"

[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "GENERATE_A_RANDOM_SECRET"
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
~~~

Generate a cookie secret:

~~~powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
~~~

Add **http://localhost:8501/oauth2callback** to the Google OAuth client's authorized redirect URIs.

### 4. Initialize a development database

Use a **separate development database**, never the production database used by the live demo.

~~~powershell
python database\run_migrations.py
python database\seed_course.py
python database\seed_questions.py
~~~

Review and process approved course resources through **Knowledge Management**, generate embeddings, verify topic coverage, and publish the course only after its publication requirements are met.

### 5. Start EduPath

~~~powershell
python -m streamlit run app.py
~~~

Open **http://localhost:8501**.

> **Credential safety:** Never commit your populated .streamlit/secrets.toml file, API keys, OAuth secrets, or database passwords. The real secrets file is excluded by .gitignore; only the placeholder example belongs in Git.

## 🗂️ Repository structure

~~~text
EduPath/
├── agents/                 # LangGraph tutor workflow and learner tools
├── database/               # PostgreSQL migrations and seed scripts
├── demonstrations/         # Few-shot teaching demonstrations
├── docs/                   # Product, architecture, security and user docs
├── evaluation/             # Golden queries and retrieval evaluator
├── experiments/            # CSE473 practicals and safety evaluation
├── interview_preparation/  # Viva and technical interview preparation
├── rag/                    # Retrieval-related modules
├── sample_documents/       # Original Python learning resources
├── services/               # Learner, retrieval, LLM and persistence services
├── tests/                  # Automated test suite
├── ui/                     # Learner and administrator interfaces
├── .streamlit/             # Streamlit configuration and secrets example
├── app.py
├── requirements.txt
└── requirements-dev.txt
~~~

## 📚 Documentation

| Guide | Description |
|---|---|
| [Product requirements](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/PRD.md) | Product vision, learner needs, scope |
| [System architecture](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/ARCHITECTURE.md) | Application layers, LangGraph and persistence |
| [API and workflows](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/API_AND_WORKFLOWS.md) | Service interfaces and end-to-end flows |
| [Database design](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/DATABASE.md) | PostgreSQL schema and relationships |
| [Security and privacy](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/SECURITY.md) | Consent, authorization, and data handling |
| [Evaluation](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/EVALUATION.md) | Retrieval benchmark and evaluation limits |
| [Academic experiments](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/EXPERIMENTS.md) | CSE473 practicals and implementation notes |
| [Deployment guide](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/DEPLOYMENT.md) | Streamlit Community Cloud and Neon |
| [User guide](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/USER_GUIDE.md) | Learner and administrator workflows |
| [Pre-deployment checklist](https://github.com/ManikantaPerla07/EduPath/blob/feature/unify-langchain-retrieval/docs/PRE_DEPLOYMENT_CHECKLIST.md) | Release and operational checks |

## 🛣️ Roadmap

- [ ] Expand beyond the introductory Python course.
- [ ] Broaden retrieval and answer-quality evaluation with larger, independently reviewed datasets.
- [ ] Run a voluntary adult learner pilot and measure learning outcomes before making effectiveness claims.
- [ ] Add richer instructor and course-authoring workflows.
- [ ] Explore voice-based tutoring and collaborative learning.

## 🔭 More projects

Explore other projects by the author:

| Project | Focus |
|---|---|
| [MediMind](https://github.com/ManikantaPerla07/MediMind-medical-QA-system) | Medical question answering with BERT, Flan-T5, retrieval, and FastAPI/React |
| [AI Surveillance System](https://github.com/ManikantaPerla07/AI-Surveillance-System) | Real-time YOLOv8 detection, threat scoring, and event alerts |
| [Zero-Shot Industrial Defect Detection](https://github.com/ManikantaPerla07/zero-shot-industrial-defect-detection) | PatchCore anomaly detection and CLIP zero-shot comparison |
| [Developer portfolio](https://personal-portfolio-tk11.vercel.app/) | Projects, technical skills, education, and contact |

## 👨‍💻 About

**EduPath** is a CSE473 academic major project built by **Perla Manikanta**.

- GitHub: [@ManikantaPerla07](https://github.com/ManikantaPerla07)
- Portfolio: [personal-portfolio-tk11.vercel.app](https://personal-portfolio-tk11.vercel.app/)
- Repository: [ManikantaPerla07/EduPath](https://github.com/ManikantaPerla07/EduPath)

---

<div align="center">

### Learn with evidence. Improve with feedback. Progress with a plan.

If EduPath is useful, consider giving the repository a ⭐.

</div>
