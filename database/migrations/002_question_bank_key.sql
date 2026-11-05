-- EduPath Migration 002
-- Add stable question identifiers

ALTER TABLE question_bank
ADD COLUMN question_code TEXT;

-- Preserve any existing question records.
UPDATE question_bank
SET question_code = 'LEGACY-' || question_id::TEXT
WHERE question_code IS NULL;

ALTER TABLE question_bank
ALTER COLUMN question_code SET NOT NULL;

ALTER TABLE question_bank
ADD CONSTRAINT uq_question_bank_code
UNIQUE (question_code);

ALTER TABLE question_bank
ADD CONSTRAINT chk_question_bank_code
CHECK (question_code ~ '^[A-Z0-9_-]+$');
