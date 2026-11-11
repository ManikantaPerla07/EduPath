-- ============================================
-- EduPath chat and Tutor run query indexes
-- Migration: 006
-- ============================================

-- The account-wide question limit filters recent learner messages by
-- created_at and joins each message to its owning chat session.
CREATE INDEX idx_chat_messages_user_created_at
ON chat_messages(created_at, session_id)
WHERE role = 'user';

-- Persistent Tutor start and conversation deletion both check for a running
-- reservation by session_id. Keep the partial index limited to live runs.
CREATE INDEX idx_agent_runs_active_session
ON agent_runs(session_id, started_at DESC)
WHERE status = 'running';
