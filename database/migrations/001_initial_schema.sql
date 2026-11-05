-- ============================================
-- EduPath Initial Database Schema
-- Migration: 001
-- PostgreSQL + pgvector
-- ============================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. USERS
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oidc_issuer TEXT NOT NULL,
    oidc_subject TEXT NOT NULL,
    email TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'student'
        CHECK (role IN ('student', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (oidc_issuer, oidc_subject)
);

-- 2. LEARNER PROFILES
CREATE TABLE learner_profiles (
    user_id UUID PRIMARY KEY
        REFERENCES users(user_id) ON DELETE CASCADE,
    learning_goal TEXT,
    proficiency_level TEXT DEFAULT 'beginner'
        CHECK (proficiency_level IN
        ('beginner', 'intermediate', 'advanced')),
    preferred_language TEXT DEFAULT 'English',
    explanation_style TEXT DEFAULT 'step_by_step'
        CHECK (explanation_style IN
        ('simple', 'step_by_step', 'example_first')),
    daily_study_minutes INTEGER DEFAULT 45
        CHECK (daily_study_minutes BETWEEN 10 AND 600),
    adult_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. COURSES
CREATE TABLE courses (
    course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_slug TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    description TEXT,
    difficulty_level TEXT DEFAULT 'beginner',
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. TOPICS
CREATE TABLE topics (
    topic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL
        REFERENCES courses(course_id),
    topic_slug TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    description TEXT,
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    estimated_minutes INTEGER CHECK (estimated_minutes > 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (course_id, topic_slug),
    UNIQUE (topic_id, course_id)
);

-- 5. TOPIC PREREQUISITES
CREATE TABLE topic_prerequisites (
    topic_id UUID NOT NULL,
    prerequisite_topic_id UUID NOT NULL,
    course_id UUID NOT NULL,
    PRIMARY KEY (topic_id, prerequisite_topic_id),
    CHECK (topic_id <> prerequisite_topic_id),
    FOREIGN KEY (topic_id, course_id)
        REFERENCES topics(topic_id, course_id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_topic_id, course_id)
        REFERENCES topics(topic_id, course_id) ON DELETE CASCADE
);

-- 6. QUESTION BANK
CREATE TABLE question_bank (
    question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES topics(topic_id),
    question_type TEXT NOT NULL DEFAULT 'mcq'
        CHECK (question_type IN ('mcq')),
    question_text TEXT NOT NULL,
    options JSONB NOT NULL
        CHECK (jsonb_typeof(options) = 'array'),
    correct_answer JSONB NOT NULL,
    explanation TEXT,
    difficulty TEXT NOT NULL DEFAULT 'easy'
        CHECK (difficulty IN ('easy', 'medium', 'hard')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. ASSESSMENT SESSIONS
CREATE TABLE assessment_sessions (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id),
    topic_id UUID,
    assessment_type TEXT NOT NULL
        CHECK (assessment_type IN
        ('diagnostic', 'practice', 'revision')),
    status TEXT NOT NULL DEFAULT 'in_progress'
        CHECK (status IN
        ('in_progress', 'submitted', 'abandoned')),
    score_percent NUMERIC(5,2)
        CHECK (score_percent BETWEEN 0 AND 100),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    UNIQUE (assessment_id, course_id),
    FOREIGN KEY (topic_id, course_id)
        REFERENCES topics(topic_id, course_id)
);

-- 8. ASSESSMENT ITEMS
CREATE TABLE assessment_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL,
    course_id UUID NOT NULL,
    question_bank_id UUID
        REFERENCES question_bank(question_id) ON DELETE SET NULL,
    topic_id UUID NOT NULL,
    question_text TEXT NOT NULL,
    options JSONB NOT NULL
        CHECK (jsonb_typeof(options) = 'array'),
    answer_key JSONB NOT NULL,
    explanation TEXT,
    difficulty TEXT NOT NULL DEFAULT 'easy'
        CHECK (difficulty IN ('easy', 'medium', 'hard')),
    points NUMERIC(6,2) NOT NULL DEFAULT 1 CHECK (points > 0),
    question_order INTEGER NOT NULL CHECK (question_order > 0),
    UNIQUE (assessment_id, question_order),
    FOREIGN KEY (assessment_id, course_id)
        REFERENCES assessment_sessions(assessment_id, course_id)
        ON DELETE CASCADE,
    FOREIGN KEY (topic_id, course_id)
        REFERENCES topics(topic_id, course_id)
);

-- 9. ASSESSMENT RESPONSES
CREATE TABLE assessment_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL UNIQUE
        REFERENCES assessment_items(item_id) ON DELETE CASCADE,
    submitted_answer JSONB NOT NULL,
    is_correct BOOLEAN NOT NULL,
    awarded_points NUMERIC(6,2) NOT NULL DEFAULT 0
        CHECK (awarded_points >= 0),
    feedback TEXT,
    answered_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. STUDY PLANS
CREATE TABLE study_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id),
    title TEXT NOT NULL,
    status TEXT DEFAULT 'draft'
        CHECK (status IN
        ('draft', 'active', 'completed', 'archived')),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (plan_id, course_id),
    CHECK (end_date IS NULL OR start_date IS NULL
           OR end_date >= start_date)
);

-- 11. STUDY PLAN ITEMS
CREATE TABLE study_plan_items (
    plan_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL,
    course_id UUID NOT NULL,
    topic_id UUID NOT NULL,
    activity_type TEXT NOT NULL,
    scheduled_date DATE,
    estimated_minutes INTEGER CHECK
        (estimated_minutes IS NULL OR estimated_minutes > 0),
    status TEXT DEFAULT 'pending'
        CHECK (status IN
        ('pending', 'in_progress', 'completed', 'skipped')),
    recommendation_reason TEXT,
    sequence_number INTEGER NOT NULL,
    UNIQUE (plan_id, sequence_number),
    FOREIGN KEY (plan_id, course_id)
        REFERENCES study_plans(plan_id, course_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id, course_id)
        REFERENCES topics(topic_id, course_id)
);

-- 12. LEARNER TOPIC PROGRESS
CREATE TABLE learner_topic_progress (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(topic_id),
    total_attempts INTEGER DEFAULT 0 CHECK (total_attempts >= 0),
    correct_answers INTEGER DEFAULT 0 CHECK (correct_answers >= 0),
    accuracy_percent NUMERIC(5,2) DEFAULT 0
        CHECK (accuracy_percent BETWEEN 0 AND 100),
    hints_used INTEGER DEFAULT 0 CHECK (hints_used >= 0),
    mastery_score NUMERIC(5,2) DEFAULT 0
        CHECK (mastery_score BETWEEN 0 AND 100),
    mastery_status TEXT DEFAULT 'not_assessed'
        CHECK (mastery_status IN
        ('not_assessed', 'needs_revision',
         'developing', 'candidate_for_mastery')),
    last_attempted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, topic_id),
    CHECK (correct_answers <= total_attempts)
);

-- 13. CHAT SESSIONS
CREATE TABLE chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id),
    thread_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. CHAT MESSAGES
CREATE TABLE chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL
        REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(citations) = 'array'),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. DOCUMENT REGISTRY
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    topic_id UUID,
    uploaded_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'txt', 'md')),
    file_size_bytes BIGINT NOT NULL
        CHECK (file_size_bytes BETWEEN 1 AND 5242880),
    file_data BYTEA NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL
        CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
    source_title TEXT NOT NULL,
    source_license TEXT NOT NULL,
    rights_basis TEXT NOT NULL
        CHECK (rights_basis IN
        ('original', 'public_domain', 'open_license',
         'permission_obtained', 'user_has_rights')),
    processing_status TEXT DEFAULT 'uploaded'
        CHECK (processing_status IN
        ('uploaded', 'processing', 'ready', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (topic_id, course_id)
        REFERENCES topics(topic_id, course_id),
    UNIQUE (course_id, file_sha256),
    CHECK (octet_length(file_data) = file_size_bytes)
);

-- 16. AGENT RUNS
CREATE TABLE agent_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    session_id UUID
        REFERENCES chat_sessions(session_id) ON DELETE SET NULL,
    workflow_name TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN
        ('running', 'completed', 'failed', 'stopped')),
    node_sequence JSONB DEFAULT '[]'::jsonb,
    duration_ms INTEGER,
    error_code TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 17. MODEL USAGE EVENTS
CREATE TABLE model_usage_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    run_id UUID REFERENCES agent_runs(run_id) ON DELETE SET NULL,
    model_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens INTEGER DEFAULT 0 CHECK (output_tokens >= 0),
    latency_ms INTEGER,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_topics_course
ON topics(course_id, sequence_number);

CREATE INDEX idx_topic_prerequisites
ON topic_prerequisites(prerequisite_topic_id);

CREATE INDEX idx_questions_topic
ON question_bank(topic_id, difficulty)
WHERE is_active = TRUE;

CREATE INDEX idx_assessments_user
ON assessment_sessions(user_id, started_at DESC);

CREATE INDEX idx_assessment_items_session
ON assessment_items(assessment_id);

CREATE INDEX idx_progress_user
ON learner_topic_progress(user_id, mastery_status);

CREATE INDEX idx_study_plans_user
ON study_plans(user_id, course_id, status);

CREATE INDEX idx_study_items_plan
ON study_plan_items(plan_id, sequence_number);

CREATE INDEX idx_chat_sessions_user
ON chat_sessions(user_id, last_activity_at DESC);

CREATE INDEX idx_chat_messages_session
ON chat_messages(session_id, created_at);

CREATE INDEX idx_documents_course
ON documents(course_id, processing_status);

CREATE INDEX idx_agent_runs_user
ON agent_runs(user_id, started_at DESC);

CREATE INDEX idx_model_usage_user
ON model_usage_events(user_id, created_at DESC);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON learner_profiles
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_courses_updated_at
BEFORE UPDATE ON courses
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_study_plans_updated_at
BEFORE UPDATE ON study_plans
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_learner_progress_updated_at
BEFORE UPDATE ON learner_topic_progress
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

