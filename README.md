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
- **Administrator Knowledge Management:** active administrators can upload PDF, TXT and Markdown resources, associate them with course topics, inspect extraction/chunk/embedding status, retry failed extraction, and generate missing embeddings. Administrative operations re-check the account role in PostgreSQL.

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
├── ui/                     # Streamlit learner and administrator interfaces
│   ├── knowledge_management.py # Admin-only resource upload and processing status
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

Run these commands only against the intended development or demo database. The course seed script creates the course with `is_published = FALSE`. The learner UI uses the fixed `python-basics` course slug. An active administrator must review its resources and explicitly publish it through Knowledge Management before student accounts can access the course.

### 6. Grant an administrator role for local resource management

New accounts receive the `student` role. A trusted database operator must explicitly promote an existing account before the **Knowledge Management** navigation item appears. There is no self-service role assignment in the learner UI.

First, find the exact account in the Neon SQL Editor:

```sql
SELECT user_id, email, role, is_active
FROM users
WHERE LOWER(email) = LOWER('your-google-email@example.com')
  AND email_verified = TRUE
  AND is_active = TRUE;
```

After verifying that the result is exactly the intended account, promote that exact UUID:

```sql
UPDATE users
SET role = 'admin',
    updated_at = NOW()
WHERE user_id = 'paste-the-verified-user-uuid'
  AND is_active = TRUE
RETURNING user_id, email, role;
```

Sign out and sign in again. The Knowledge Management page and its document operations independently verify the active administrator role in PostgreSQL.

### 7. Prepare and publish the Python course

Open **Knowledge Management** as an administrator. Upload approved resources for the Python Programming course, associate them with the relevant topics, and use **Generate missing embeddings** until each resource intended for retrieval is fully embedded.

The publication control checks that the course has at least one topic, at least one active assessment question, and at least one active ready resource with all of its chunk embeddings stored. This is a minimum technical readiness check, not a guarantee of complete topic coverage; review the inventory and ensure every taught topic has adequate approved material before publishing.

Publishing enables learner access to the course. Unpublishing pauses learner access to the course's dashboard, assessments, progress, study plan, and tutor retrieval. Existing assessment submissions can still be completed. Archiving a resource preserves its file and chunks but excludes it from retrieval. If the last fully embedded active resource is archived, EduPath automatically unpublishes the course. Restoring a resource does not automatically republish the course.

### 8. Start the app

```powershell
python -m streamlit run app.py
```

Streamlit normally opens the application at `http://localhost:8501`.

## Run tests

From the repository root with the virtual environment activated:

```powershell
python -m pytest -q
python -m compileall -q agents services ui tests
git diff --check
```

The latest developer-verified baseline before the administrator Knowledge Management milestone was **421 passed, 31 subtests passed** on November 11, 2026. Re-run the suite after pulling later commits; this is a historical result, not a guarantee for subsequent code revisions.

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

The current MVP focuses on beginner Python programming, with nine topics and a seeded question bank of 27 multiple-choice questions (nine easy, nine medium, and nine hard). The current administrator interface covers shared document ingestion, processing status and embedding recovery. Course authoring, course publication controls, resource deletion/archival, and general-purpose instructor analytics are not included yet.

## Development history

See [docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md) for the milestone-by-milestone development record, implementation notes, and historical test results.

## License

No open-source license has been selected for this repository yet. Do not assume reuse rights beyond applicable copyright law until a license is added.
