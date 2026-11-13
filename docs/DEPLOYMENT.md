# Deployment Guide — Streamlit Community Cloud & Neon
**Target Platform:** Streamlit Community Cloud (Free Tier)\
**Database:** Neon Serverless PostgreSQL (`neondb`)\
**LLM API:** Google Gemini API (Free Tier)\
**Budget Objective:** ₹0\
**Author:** Perla Manikanta

---

## 1. Hosting Architecture
EduPath is deployed as a single-repository web application connected to serverless backends:
- **Application Host:** Streamlit Community Cloud
- **Repository:** `ManikantaPerla07/EduPath`
- **Main Branch:** `main` (merged from `feature/unify-langchain-retrieval`)
- **Entrypoint:** `app.py`
- **Runtime:** Python 3.11.9 / 3.12 compatible

---

## 2. Secrets Configuration (`.streamlit/secrets.toml`)
Configure these secrets in the Streamlit Cloud dashboard (**never commit `.streamlit/secrets.toml` to Git**):

```toml
# PostgreSQL Connection (Neon Serverless SSL connection string)
DATABASE_URL = "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Google Gemini API Key
GEMINI_API_KEY = "AIzaSy..."

# Streamlit Auth / Google OIDC Configuration
[auth]
redirect_uri = "https://your-edupath-app.streamlit.app/oauth2callback"
cookie_secret = "GENERATE_A_SECURE_RANDOM_32_CHAR_STRING"
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

---

## 3. Deployment Pre-Flight Checklist

### Database Pre-requisites (Neon SQL Editor):
1. Confirm migrations `001` through `006` are applied:
   ```sql
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
   ```
2. Verify `pgvector` extension is active:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```
3. Verify Python course is published:
   ```sql
   SELECT course_slug, is_published FROM courses WHERE course_slug = 'python-basics';
   ```

### Google Cloud Console (OAuth Configuration):
1. Open [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).
2. Add your Streamlit Cloud URL to **Authorized JavaScript origins**:
   `https://your-edupath-app.streamlit.app`
3. Add the callback URL to **Authorized redirect URIs**:
   `https://your-edupath-app.streamlit.app/oauth2callback`

---

## 4. Free-Tier Quota & Cost Management
- **Gemini Free Tier:** 15 Requests Per Minute (RPM), 1,500 Requests Per Day (RPD).
- **Graceful Quota Handling:** If `gemini-3.8-flash` hits rate limits, the system catches retryable 429 errors and routes to `gemini-3.5-flash-lite`.
- **Neon Sleep Mode:** Free Neon databases suspend after 5 minutes of inactivity. EduPath connections use `connect_timeout=20` to allow automatic compute wake-up without crashing.
