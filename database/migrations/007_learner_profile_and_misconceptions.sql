-- ============================================================
-- EduPath Learner Profile Extensions and Misconception Records
-- Migration: 007
-- Forward-only schema extension for CSE473 Major Project
-- ============================================================

-- 1. Learner Profile Lifecycle & Privacy Consent Extensions
-- Schema audit note:
-- - adult_confirmation was established in 001_initial_schema.sql (BOOLEAN NOT NULL DEFAULT FALSE).
--   No redundant 'adult_confirmed' column is introduced; existing self-declarations are preserved.
-- - learning_goal was established in 001_initial_schema.sql (TEXT). Preserved with IF NOT EXISTS.
-- - ai_consent strictly defaults to FALSE (opt-in affirmative action required; no silent enrollment).
-- - onboarding_completed strictly defaults to FALSE (learners complete setup affirmatively).
ALTER TABLE learner_profiles
ADD COLUMN IF NOT EXISTS learning_goal TEXT DEFAULT 'Master Python fundamentals';

ALTER TABLE learner_profiles
ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE learner_profiles
ADD COLUMN IF NOT EXISTS ai_consent BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE learner_profiles
ADD COLUMN IF NOT EXISTS ai_consent_granted_at TIMESTAMPTZ DEFAULT NULL;

-- 2. Structured Learner Misconception Records
-- Retains formative diagnostic evidence tied to authenticated learner ID.
-- Enforces foreign-key ownership with CASCADE delete upon account deletion.
CREATE TABLE IF NOT EXISTS learner_misconceptions (
    misconception_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    misconception_code VARCHAR(100) NOT NULL,
    topic_slug VARCHAR(100) NOT NULL,
    short_description TEXT NOT NULL,
    corrective_explanation TEXT NOT NULL,
    detection_method VARCHAR(50) NOT NULL DEFAULT 'rule_based',
    confidence_score NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    diagnosed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ DEFAULT NULL
);

-- Fast lookup of active misconceptions for personalized tutor prompts
CREATE INDEX IF NOT EXISTS idx_learner_misconceptions_user_topic
ON learner_misconceptions(user_id, topic_slug, is_active);

CREATE INDEX IF NOT EXISTS idx_learner_misconceptions_code
ON learner_misconceptions(misconception_code);
