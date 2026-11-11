# EduPath — Personalized Tutoring Agent

EduPath is an AI-powered learning platform for beginner Python programming. It combines a grounded AI tutor, adaptive assessments, learner progress tracking, and personalized study planning in a Streamlit application.

## What EduPath does

- **Google sign-in and learner onboarding:** authenticates learners and stores learner profiles in PostgreSQL.
- **AI Tutor:** answers questions using course material retrieved through retrieval-augmented generation (RAG), with citations where available.
- **LangGraph agent workflow:** orchestrates contextual question resolution, grounded retrieval, progress-aware teaching, and answer generation. For authenticated chat sessions, Gemini can select read-only tools for the learner's own progress or study plan; learner identity and course scope are injected by the application, not chosen by the model.
- **Diagnostic assessment:** provides a 27-question Python assessment covering nine topics.
- **Adaptive Practice and Targeted Revision:** presents questions one at a time, gives immediate feedback, and adjusts the preferred difficulty of the next question based on the previous answer.
- **Learning progress:** tracks attempts, accuracy, and topic mastery status.
- **Personalized study plan:** schedules learning, practice, revision, and spaced-review activities based on assessment evidence, prerequisites, learning goals, and available study time.
- **Persistent conversations and plans:** stores learner chat history, study-plan activity status, and per-chat LangGraph checkpoints in Neon. Deleting a conversation also deletes its checkpoint state.

## Technology stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Language | Python 3.11 |
| AI model and embeddings | Google Gemini (`google-genai`, exposed through LangChain adapters) |
| LLM prompts and runnable chains | LangChain |
| Agent orchestration | LangGraph with Neon-backed PostgreSQL checkpoints |
| Document processing | pypdf plus page-aware LangChain loader and text splitter |
| Retrieval | RAG, Gemini Embedding 2, PostgreSQL pgvector |
| Database | PostgreSQL (Neon) |
| Authentication | Google OpenID Connect through Streamlit authentication |
| Tests | pytest |

## Architecture overview

```text
Learner
  |
  v
Streamlit application (app.py)
  |
  +----------------------+-----------------------+
  |                      |                       |
  v                      v                       v
AI Tutor             Assessment              Study Plan
  |                      |                       |
  v                      v                       v
LangGraph             Adaptive              Progress and
Tutor workflow        assessment            study-plan services
  |
  v
Retrieval service
  |
  v
Gemini embeddings <--> PostgreSQL / Neon + pgvector
  |
  v
Grounded response with citations (when available)
```

## Repository structure

```text
EduPath/
├── agents/                 # LangGraph tutor workflow and read-only learner tools
├── database/
│   ├── migrations/         # Versioned PostgreSQL migrations
│   ├── run_migrations.py
│   ├── seed_course.py
│   └── seed_questions.py
├── docs/
│   └── DEVELOPMENT_LOG.md  # Implementation milestones and decisions
├── rag/                    # Retrieval-related modules
├── sample_documents/       # Sample Python learning material
├── services/
│   ├── langchain_document_processing.py # Page-aware LangChain loader/splitter
│   ├── langchain_embeddings.py          # Gemini Embedding 2 adapter
│   ├── langchain_retriever.py           # Neon pgvector retriever adapter
│   └── ...                              # Application and domain services
├── tests/                  # Automated tests
├── ui/                     # Streamlit learner interfaces
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── app.py
├── requirements.txt
└── requirements-dev.txt
```

## Requirements

- Python 3.11
- Git
- PostgreSQL database with the `pgvector` extension (Neon is used by this project)
- Google Gemini API key
- Google OAuth/OIDC client credentials

## Run locally (Windows PowerShell)

### 1. Clone the repository

```powershell
git clone https://github.com/ManikantaPerla07/EduPath.git
cd EduPath
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 4. Configure secrets

Copy the example file and edit the new local file:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Fill in the placeholders in `.streamlit/secrets.toml` with your own values. The required top-level settings are `DATABASE_URL` and `GEMINI_API_KEY`. The `[auth]` section contains the Google OIDC settings used by `st.login()`.

Generate a cookie secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

For local sign-in, configure the Google OAuth client's authorized redirect URI as:

```text
http://localhost:8501/oauth2callback
```

**Never commit `.streamlit/secrets.toml`.** It is excluded by `.gitignore`. Only the placeholder file `secrets.toml.example` belongs in Git.

### 5. Initialize the database

Run the application schema migrations and initialize LangGraph's managed PostgreSQL checkpoint tables:

```powershell
python database\run_migrations.py
```

The migration command also initializes the checkpoint tables maintained by
`langgraph-checkpoint-postgres`. Re-running it is safe; the package applies
only its pending checkpoint-table migrations.

Create or update the Python course and its topic prerequisites:

```powershell
python database\seed_course.py
```

Seed and validate the Python question bank:

```powershell
python database\seed_questions.py
```

Run these commands only against the intended development or demo database. The course seed script creates the course with `is_published = FALSE`; the current learner UI uses the fixed `python-basics` course slug and does not currently provide a course-publishing administration screen. Verify the intended course-access policy before making a public deployment.

### 6. Start the app

```powershell
python -m streamlit run app.py
```

Streamlit normally opens the application at `http://localhost:8501`.

## Run tests

From the repository root with the virtual environment activated:

```powershell
python -m pytest -q
python -m compileall -q services tests
git diff --check
```

The most recent recorded verification during development was **356 passed, 19 subtests passed**. Re-run the tests after changes; this number is a historical result, not a guarantee for future code revisions.

## Deploy to Streamlit Community Cloud

Deployment has not been confirmed yet. These are preparation steps; a successful live deployment still requires valid credentials, a reachable database, and OAuth configuration.

1. Push the project to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub repository.
3. Select the `main` branch and set `app.py` as the main file.
4. In the app's deployment settings, configure the same required secrets as in `.streamlit/secrets.toml.example`.
5. Set `[auth].redirect_uri` to the deployed app's callback URL, for example `https://YOUR-APP-NAME.streamlit.app/oauth2callback`.
6. Add that exact URL to the Google OAuth client's authorized redirect URIs.
7. Verify sign-in, database connectivity, tutoring, assessments, progress, and study-plan workflows in the deployed app.

Keep all credentials in Streamlit's secrets settings. Do not commit or share a populated `secrets.toml` file.

## Current scope and limitations

The current MVP focuses on beginner Python programming, with nine topics and a seeded question bank of 27 multiple-choice questions (nine easy, nine medium, and nine hard). It is a learner-facing application; a general-purpose instructor or course-authoring administration interface is not included.

## Development history

See [docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md) for the milestone-by-milestone development record, implementation notes, and historical test results.

## License

No open-source license has been selected for this repository yet. Do not assume reuse rights beyond applicable copyright law until a license is added.
