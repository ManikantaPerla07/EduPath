# Deployment Guide — Streamlit Community Cloud & Neon
**Target Platform:** Streamlit Community Cloud (Free Tier)\
**Database:** Neon Serverless PostgreSQL (`neondb`)\
**LLM API:** Google Gemini API (Free Tier)\
**Budget Objective:** ₹0\
**Author:** Perla Manikanta

---

## 1. Hosting Architecture
EduPath is designed to deploy to Streamlit Community Cloud connected to serverless backends:
- **Application Host:** Streamlit Community Cloud (Manual deployment target)
- **Repository:** `ManikantaPerla07/EduPath`
- **Target Branch:** `main` (currently developed in the working tree on branch `feature/unify-langchain-retrieval`; not yet merged into `main`)
- **Entrypoint:** `app.py`
- **Runtime:** Python 3.11.9 / 3.12 compatible

---

## 2. Secrets Configuration (`.streamlit/secrets.toml`)
Configure these secrets in the Streamlit Cloud dashboard (**never commit `.streamlit/secrets.toml` to Git**):

```toml
# PostgreSQL Connection (Neon Serverless SSL connection string)
DATABASE_URL = "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Google Gemini API Key (Primary LLM & Vector Embeddings)
GEMINI_API_KEY = "AIzaSy..."

# Groq API Key (Secondary Failover LLM)
GROQ_API_KEY = "gsk_..."

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
- **Gemini Multi-Dimensional Quotas:** Quotas on Google AI Studio / Gemini API are enforced across three distinct dimensions rather than a single universal limit:
  - **Requests Per Minute (RPM):** Typically 15 RPM for standard flash models, though specific model and tier limits vary.
  - **Tokens Per Minute (TPM):** E.g., up to 1,000,000 TPM for flash tiers.
  - **Requests Per Day (RPD):** Typically 1,500 RPD for free-tier projects.
  - *Recommendation:* Always check your project-specific active quotas in the **Google AI Studio / Google Cloud Console Quotas & System Limits** dashboard.
- **Multi-Provider Failover & Availability Realism:** If `gemini-3.8-flash` encounters server timeouts (`504`), rate limits (`429`), or transient unavailability, the system attempts `gemini-3.5-flash-lite`, and automatically fails over to Groq (`openai/gpt-oss-120b` and `openai/gpt-oss-20b`). While this multi-provider redundancy substantially enhances system resilience at ₹0 operating cost, it **does not guarantee uninterrupted zero-cost availability**, as Groq free-tier endpoints are independently subject to their own rate limits (RPM, TPM, RPD) and service capacity limits. If both providers exhaust quotas concurrently, EduPath cleanly surfaces a polite rate-limiting advisory to the learner.
- **₹0 Operating Budget:** Designed to operate on free-tier quotas requiring zero paid billing.
- **Neon Sleep Mode:** Free Neon databases suspend after 5 minutes of inactivity. EduPath connections use `connect_timeout=20` to allow automatic compute wake-up without crashing.

---

## 5. Migration 007 Safe Rollback Procedure
If migration `007_learner_profile_and_misconceptions` must ever be reversed on Neon:
> [!NOTE]
> Dependency verification: No views or foreign key constraints in migrations 001–007 reference `learner_misconceptions`. Therefore, `CASCADE` is strictly omitted from the table deletion.

```sql
BEGIN;

-- 1. Drop performance indexes and misconceptions table (no CASCADE required)
DROP INDEX IF EXISTS idx_learner_misconceptions_code;
DROP INDEX IF EXISTS idx_learner_misconceptions_user_topic;
DROP TABLE IF EXISTS learner_misconceptions;

-- 2. Revert extended columns on learner_profiles
ALTER TABLE learner_profiles DROP COLUMN IF EXISTS ai_consent_granted_at;
ALTER TABLE learner_profiles DROP COLUMN IF EXISTS ai_consent;
ALTER TABLE learner_profiles DROP COLUMN IF EXISTS onboarding_completed;

-- 3. Delete migration record from tracking table
DELETE FROM schema_migrations
WHERE version = '007_learner_profile_and_misconceptions';

COMMIT;
```
