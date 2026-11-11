-- ============================================
-- EduPath assistant-message feedback
-- Migration: 005
-- ============================================

CREATE TABLE chat_message_feedback (
    message_id UUID PRIMARY KEY
        REFERENCES chat_messages(message_id) ON DELETE CASCADE,
    user_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    is_helpful BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_message_feedback_user
ON chat_message_feedback(user_id, updated_at DESC);

CREATE TRIGGER trg_chat_message_feedback_updated_at
BEFORE UPDATE ON chat_message_feedback
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
